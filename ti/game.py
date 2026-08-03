"""Aggregate game object: state, action dispatch and round flow."""

from __future__ import annotations

import random
import uuid
from typing import Dict, List, Optional, Sequence

from ti.agenda import (
    AGENDA_LIST,
    ELECT_PLAYER,
    get_agenda,
    income_bonus,
    research_surcharge,
    tally,
    token_maximum,
)
from ti.action_cards import (
    ACTION_CARD_LIST,
    HAND_LIMIT,
    get_action_card,
)
from ti.cards import STRATEGY_CARD_LIST, CardEffect, get_card
from ti.engine import ActionResult, Engine
from ti.factions import FACTION_LIST, combat_bonus
from ti.models import Board, Player
from ti.objectives import OBJECTIVE_DECK, SECRET_DECK, get_objective
from ti.phases import Phase, TurnManager
from ti.setup import MECATOL_ID, new_game_state
from ti.tech import (
    TECHNOLOGY_LIST,
    get_technology,
    missing_prerequisites,
    upgrades_of,
)
from ti.units import UNIT_TYPES

VICTORY_POINTS_TO_WIN = 10
COMMAND_TOKENS_PER_ROUND = 2
MAX_COMMAND_TOKENS = 8
TOKEN_COST = {"move": 1, "produce": 1, "build": 1, "research": 1, "follow": 1}
"""Activation cost per action type; actions not listed here are free."""
OFF_TURN_ACTIONS = {"trade"}
"""Actions that any player may take, not only the one whose turn it is."""
CUSTODIAN_VP = 1
"""One-off reward for the first player to take Mecatol Rex."""
SECRETS_PER_PLAYER = 2
"""Secret objectives a player holds; a scored one is replaced from the deck."""


class Game:
    def __init__(
        self,
        players: Sequence[Player],
        board: Board,
        seed: int,
        rng: Optional[random.Random] = None,
        game_id: Optional[str] = None,
    ) -> None:
        self.id = game_id or str(uuid.uuid4())
        self.players: List[Player] = list(players)
        self.board = board
        self.seed = seed
        self.rng = rng or random.Random(seed)
        self.engine = Engine(
            board,
            self.rng,
            {p.name: combat_bonus(p.faction) for p in self.players},
        )
        self.turns = TurnManager([p.name for p in self.players])
        self.history: List[str] = [f"Game created seed={seed}"]
        self.version = 0
        """Increases with every logged change; clients poll it to detect updates."""
        self.winner: Optional[str] = None
        self.objective_deck: List[str] = [o.id for o in OBJECTIVE_DECK]
        self.rng.shuffle(self.objective_deck)
        self.revealed_objectives: List[str] = []
        self.scored_objectives: Dict[str, List[str]] = {}
        self.custodian: Optional[str] = None
        self.agenda_deck: List[str] = [a.id for a in AGENDA_LIST]
        self.rng.shuffle(self.agenda_deck)
        self.active_agenda: Optional[str] = None
        self.votes: Dict[str, dict] = {}
        self.laws: Dict[str, str] = {}
        """Enacted laws mapped to their outcome (or the elected player)."""
        self.played_cards: List[int] = []
        self.followers: Dict[int, List[str]] = {}
        """Players who already used the secondary ability of a played card."""
        self.action_deck: List[str] = [c.id for c in ACTION_CARD_LIST]
        self.rng.shuffle(self.action_deck)
        self.action_discard: List[str] = []
        self.secret_deck: List[str] = [o.id for o in SECRET_DECK]
        self.rng.shuffle(self.secret_deck)
        for player in self.players:
            self.deal_secrets(player)
        self.reveal_objective()

    # ------------------------------------------------------------ factories
    @classmethod
    def create(
        cls,
        raw_players: Sequence[object],
        factions: Optional[Dict[str, str]] = None,
        seed: Optional[int] = None,
    ) -> "Game":
        players, board, seed, rng = new_game_state(raw_players, factions, seed)
        return cls(players, board, seed, rng)

    # -------------------------------------------------------------- helpers
    @property
    def round(self) -> int:
        return self.turns.round

    def get_player(self, name: str) -> Optional[Player]:
        for player in self.players:
            if player.name == name:
                return player
        return None

    def get_system(self, system_id: str):
        return self.board.get(system_id)

    def available_strategy_cards(self) -> List[int]:
        taken = {p.strategy_card for p in self.players if p.strategy_card}
        return [c.id for c in STRATEGY_CARD_LIST if c.id not in taken]

    def reveal_objective(self) -> Optional[str]:
        if not self.objective_deck:
            return None
        objective_id = self.objective_deck.pop(0)
        self.revealed_objectives.append(objective_id)
        self.scored_objectives.setdefault(objective_id, [])
        objective = get_objective(objective_id)
        if objective:
            self.log(f"New objective revealed: {objective.name}")
        return objective_id

    def deal_secrets(self, player: Player) -> None:
        """Top the player's hand up to :data:`SECRETS_PER_PLAYER` secrets."""
        taken = {
            objective_id
            for other in self.players
            for objective_id in other.secret_objectives + other.scored_secrets
        }
        while len(player.secret_objectives) < SECRETS_PER_PLAYER and self.secret_deck:
            objective_id = self.secret_deck.pop(0)
            if objective_id in taken:
                continue
            player.secret_objectives.append(objective_id)

    def log(self, message: str) -> None:
        self.history.append(f"[R{self.turns.round}] {message}")
        self.version += 1

    # --------------------------------------------------------------- action
    def apply_action(self, player_name: str, action: dict) -> ActionResult:
        player = self.get_player(player_name)
        if player is None:
            return ActionResult(False, f"Unknown player: {player_name}")
        if self.turns.phase == Phase.FINISHED:
            return ActionResult(False, f"Game is over, {self.winner} won")

        action_type = (action or {}).get("type")
        handlers = {
            "select_strategy": self._action_select_strategy,
            "move": self._action_move,
            "produce": self._action_produce,
            "build": self._action_build,
            "research": self._action_research,
            "vote": self._action_vote,
            "trade": self._action_trade,
            "play_action_card": self._action_play_action_card,
            "play_strategy": self._action_play_strategy,
            "follow": self._action_follow,
            "invade": self._action_invade,
            "end_turn": self._action_end_turn,
            "pass": self._action_pass,
        }
        handler = handlers.get(action_type)
        if handler is None:
            return ActionResult(False, f"Unknown action: {action_type}")

        guard = self._check_turn(player, action_type)
        if guard is not None:
            return guard

        cost = TOKEN_COST.get(action_type, 0)
        if cost and player.command_tokens < cost:
            return ActionResult(
                False, "No command tokens left - end the turn or pass"
            )

        result = handler(player, action or {})
        if result.ok:
            player.command_tokens -= cost
            self.log(result.message)
            self._maybe_resolve_agenda()
        return result

    def _check_turn(self, player: Player, action_type: str) -> Optional[ActionResult]:
        expected_phase = {
            "select_strategy": Phase.STRATEGY,
            "vote": Phase.AGENDA,
        }.get(action_type, Phase.ACTION)
        if self.turns.phase != expected_phase:
            return ActionResult(
                False,
                f"Action '{action_type}' not allowed in phase '{self.turns.phase}'",
            )
        if expected_phase == Phase.AGENDA or action_type in OFF_TURN_ACTIONS:
            return None
        if self.turns.current_player != player.name:
            return ActionResult(
                False, f"It is {self.turns.current_player}'s turn"
            )
        return None

    # ------------------------------------------------------------- handlers
    def _action_select_strategy(self, player: Player, action: dict) -> ActionResult:
        card = get_card(action.get("card_id", 0))
        if card is None:
            return ActionResult(False, "Unknown strategy card")
        if card.id not in self.available_strategy_cards():
            return ActionResult(False, f"Card {card.name} is already taken")

        player.strategy_card = card.id
        self.turns.strategy_picked()
        if self.turns.phase == Phase.ACTION:
            self.turns.begin_action_phase(
                {p.name: p.strategy_card or 99 for p in self.players}
            )
        return ActionResult(
            True,
            f"{player.name} chose {card.name}",
            {"card": card.to_dict()},
        )

    def _apply_effect(self, player: Player, effect: CardEffect) -> None:
        player.resources += effect.resources
        player.trade_goods += effect.trade_goods
        player.influence += effect.influence
        player.vp += effect.vp
        player.command_tokens = min(
            token_maximum(self.laws, MAX_COMMAND_TOKENS),
            player.command_tokens + effect.tokens,
        )
        player.free_research += effect.free_research
        player.free_structures += effect.free_structures
        player.fleet_supply += effect.fleet_supply
        for _ in range(effect.action_cards):
            self.draw_action_card(player)

    def _action_play_strategy(self, player: Player, action: dict) -> ActionResult:
        card = get_card(player.strategy_card) if player.strategy_card else None
        if card is None:
            return ActionResult(False, f"{player.name} has no strategy card")
        if card.id in self.played_cards:
            return ActionResult(False, f"{card.name} was already played this round")

        self.played_cards.append(card.id)
        self.followers.setdefault(card.id, [])
        self._apply_effect(player, card.primary)
        return ActionResult(
            True,
            f"{player.name} played {card.name} ({card.primary.describe()})",
            {"card": card.to_dict(), "effect": card.primary.to_dict()},
        )

    def _action_follow(self, player: Player, action: dict) -> ActionResult:
        card = get_card(action.get("card_id", 0))
        if card is None:
            return ActionResult(False, "Unknown strategy card")
        if card.id not in self.played_cards:
            return ActionResult(False, f"{card.name} has not been played yet")
        if player.strategy_card == card.id:
            return ActionResult(False, "The card holder uses the primary ability")
        followers = self.followers.setdefault(card.id, [])
        if player.name in followers:
            return ActionResult(False, f"{player.name} already followed {card.name}")

        followers.append(player.name)
        self._apply_effect(player, card.secondary)
        return ActionResult(
            True,
            f"{player.name} followed {card.name} ({card.secondary.describe()})",
            {"card": card.to_dict(), "effect": card.secondary.to_dict()},
        )

    def _action_trade(self, player: Player, action: dict) -> ActionResult:
        """Hand trade goods to another player to settle a negotiated deal."""
        partner = self.get_player(str(action.get("partner", "")))
        if partner is None or partner.name == player.name:
            return ActionResult(False, "Unknown trade partner")
        amount = int(action.get("trade_goods", 0))
        if amount <= 0:
            return ActionResult(False, "Trade goods must be positive")
        if amount > player.trade_goods:
            return ActionResult(
                False,
                f"Not enough trade goods: need {amount}, have {player.trade_goods}",
            )

        player.trade_goods -= amount
        partner.trade_goods += amount
        return ActionResult(
            True,
            f"{player.name} gave {amount} trade goods to {partner.name}",
            {"partner": partner.name, "trade_goods": amount},
        )

    def draw_action_card(self, player: Player) -> Optional[str]:
        if not self.action_deck and self.action_discard:
            self.action_deck = self.action_discard
            self.action_discard = []
            self.rng.shuffle(self.action_deck)
        if not self.action_deck:
            return None
        card_id = self.action_deck.pop(0)
        player.action_cards.append(card_id)
        return card_id

    def _action_play_action_card(self, player: Player, action: dict) -> ActionResult:
        card = get_action_card(action.get("card"))
        if card is None:
            return ActionResult(False, "Unknown action card")
        if card.id not in player.action_cards:
            return ActionResult(False, f"{player.name} does not hold {card.name}")

        try:
            message = card.effect(self, player, action)
        except ValueError as exc:
            return ActionResult(False, str(exc))

        player.action_cards.remove(card.id)
        self.action_discard.append(card.id)
        return ActionResult(
            True,
            f"{player.name} played {card.name}: {message}",
            {"card": card.to_dict()},
        )

    def _action_move(self, player: Player, action: dict) -> ActionResult:
        return self.engine.move(
            player.name,
            action.get("from"),
            action.get("to"),
            action.get("units"),
            player.technologies,
            player.fleet_supply,
        )

    def _action_research(self, player: Player, action: dict) -> ActionResult:
        technology = get_technology(action.get("technology"))
        if technology is None:
            return ActionResult(False, "Unknown technology")
        if technology.id in player.technologies:
            return ActionResult(False, f"{technology.name} is already researched")

        missing = missing_prerequisites(technology, player.technologies)
        if missing:
            needed = ", ".join(f"{count}x {color}" for color, count in missing.items())
            return ActionResult(False, f"Missing prerequisites: {needed}")
        cost = technology.cost + research_surcharge(self.laws)
        if player.free_research:
            cost = 0
        if cost > player.budget:
            return ActionResult(
                False,
                f"Not enough resources: need {cost}, have {player.budget}",
            )

        if player.free_research:
            player.free_research -= 1
        player.spend(cost)
        player.technologies.append(technology.id)
        upgraded = 0
        if technology.upgrade:
            upgraded = self._apply_upgrade(player.name, *technology.upgrade)
        return ActionResult(
            True,
            f"{player.name} researched {technology.name}",
            {
                "technology": technology.to_dict(),
                "cost": cost,
                "upgraded_units": upgraded,
            },
        )

    def _apply_upgrade(self, player_name: str, base: str, upgraded: str) -> int:
        """Replace every unit of the base type the player owns with the upgrade."""
        count = 0
        for system in self.board.systems:
            groups = [system.units_of(player_name)]
            for planet in system.planets:
                groups.append(planet.garrison_of(player_name))
                groups.append(planet.structures_of(player_name))
            for group in groups:
                for unit in group:
                    if unit.type_name == base:
                        unit.type_name = upgraded
                        count += 1
        return count

    def unit_type_for(self, player: Player, unit_type: str) -> str:
        """Map a requested unit type to the player's researched variant."""
        return upgrades_of(player.technologies).get(unit_type, unit_type)

    def _unresearched(self, player: Player, unit_types: Sequence[str]) -> List[str]:
        available = set(upgrades_of(player.technologies).values())
        return [
            name
            for name in unit_types
            if name in UNIT_TYPES
            and UNIT_TYPES[name].base_type
            and name not in available
        ]

    def _action_produce(self, player: Player, action: dict) -> ActionResult:
        requested = action.get("units") or []
        missing = self._unresearched(player, requested)
        if missing:
            return ActionResult(False, f"Not researched: {', '.join(missing)}")
        units = [self.unit_type_for(player, name) for name in requested]
        result = self.engine.produce(
            player.name,
            action.get("system"),
            units,
            player.budget,
            player.fleet_supply,
        )
        if result.ok:
            player.spend(int(result.data.get("cost", 0)))
        return result

    def _action_build(self, player: Player, action: dict) -> ActionResult:
        missing = self._unresearched(player, [action.get("structure") or ""])
        if missing:
            return ActionResult(False, f"Not researched: {', '.join(missing)}")
        free = player.free_structures > 0
        result = self.engine.build(
            player.name,
            action.get("system"),
            action.get("planet"),
            self.unit_type_for(player, action.get("structure") or ""),
            player.budget,
            free=free,
        )
        if result.ok:
            if free:
                player.free_structures -= 1
            else:
                player.spend(int(result.data.get("cost", 0)))
        return result

    def _action_invade(self, player: Player, action: dict) -> ActionResult:
        return self.engine.invade(
            player.name,
            action.get("system"),
            action.get("planet"),
            action.get("units"),
        )

    def _action_end_turn(self, player: Player, action: dict) -> ActionResult:
        self.turns.advance_turn()
        self._maybe_run_status_phase()
        return ActionResult(True, f"{player.name} ended the turn")

    def _action_pass(self, player: Player, action: dict) -> ActionResult:
        player.passed = True
        self.turns.mark_passed(player.name)
        self._maybe_run_status_phase()
        return ActionResult(True, f"{player.name} passed")

    # --------------------------------------------------------- agenda phase
    def reveal_agenda(self) -> Optional[str]:
        if not self.agenda_deck:
            return None
        self.active_agenda = self.agenda_deck.pop(0)
        self.votes = {}
        agenda = get_agenda(self.active_agenda)
        if agenda:
            self.log(f"Agenda revealed: {agenda.name}")
        return self.active_agenda

    def agenda_outcomes(self) -> List[str]:
        agenda = get_agenda(self.active_agenda)
        if agenda is None:
            return []
        if agenda.election == ELECT_PLAYER:
            return [p.name for p in self.players]
        return list(agenda.outcomes)

    def _action_vote(self, player: Player, action: dict) -> ActionResult:
        agenda = get_agenda(self.active_agenda)
        if agenda is None:
            return ActionResult(False, "No agenda is being voted on")
        if player.name in self.votes:
            return ActionResult(False, f"{player.name} already voted")

        outcome = action.get("outcome")
        if outcome not in self.agenda_outcomes():
            return ActionResult(False, f"Invalid outcome: {outcome}")
        influence = int(action.get("influence", 0))
        if influence < 0:
            return ActionResult(False, "Influence cannot be negative")
        if influence > player.influence:
            return ActionResult(
                False,
                f"Not enough influence: need {influence}, have {player.influence}",
            )

        player.influence -= influence
        self.votes[player.name] = {"outcome": outcome, "influence": influence}
        return ActionResult(
            True,
            f"{player.name} voted {influence} influence for '{outcome}'",
            {"agenda": agenda.id, "outcome": outcome, "influence": influence},
        )

    def _maybe_resolve_agenda(self) -> None:
        if self.turns.phase == Phase.AGENDA and len(self.votes) >= len(self.players):
            self.resolve_agenda()

    def resolve_agenda(self) -> None:
        agenda = get_agenda(self.active_agenda)
        if agenda is None:
            return
        speaker = self.turns.speaker
        tiebreak = [self.votes[speaker]["outcome"]] if speaker in self.votes else []
        outcome = tally(self.votes, tiebreak) or self.agenda_outcomes()[0]
        if agenda.kind == "law":
            self.laws[agenda.id] = outcome
            self.log(f"{agenda.name} enacted with '{outcome}'")
        else:
            self.log(f"{agenda.name}: {agenda.resolve(self.players, outcome)}")
        self.active_agenda = None
        self.votes = {}
        self._begin_next_round()

    # --------------------------------------------------------- status phase
    def _maybe_run_status_phase(self) -> None:
        if self.turns.phase != Phase.STATUS:
            return
        self.run_status_phase()

    def run_status_phase(self) -> None:
        for player in self.players:
            income = sum(p.resources for p in self.board.planets_of(player.name))
            influence = sum(p.influence for p in self.board.planets_of(player.name))
            player.resources += income + income_bonus(self.laws, player.name)
            player.influence += influence

            scored = self._score_victory_points(player)
            if scored:
                self.log(f"{player.name} scored {scored} victory point(s)")

            player.command_tokens = min(
                token_maximum(self.laws, MAX_COMMAND_TOKENS),
                player.command_tokens + COMMAND_TOKENS_PER_ROUND,
            )
            player.strategy_card = None
            player.passed = False
            self.draw_action_card(player)
            while len(player.action_cards) > HAND_LIMIT:
                self.action_discard.append(player.action_cards.pop(0))

        leader = max(self.players, key=lambda p: p.vp, default=None)
        if leader is not None and leader.vp >= VICTORY_POINTS_TO_WIN:
            self.winner = leader.name
            self.turns.finish()
            self.log(f"{leader.name} won the game with {leader.vp} victory points")
            return

        if self.custodian is not None and self.agenda_deck:
            self.turns.begin_agenda_phase()
            self.reveal_agenda()
            return

        self._begin_next_round()

    def _begin_next_round(self) -> None:
        self.played_cards = []
        self.followers = {}
        self.turns.begin_next_round()
        self.reveal_objective()
        self.log("New round started")

    def _score_victory_points(self, player: Player) -> int:
        scored = (
            self._score_custodian(player)
            + self._score_objectives(player)
            + self._score_secret(player)
        )
        player.vp += scored
        return scored

    def _score_custodian(self, player: Player) -> int:
        """The first player ever to hold Mecatol Rex gets a one-off bonus."""
        if self.custodian is not None:
            return 0
        mecatol = self.board.get(MECATOL_ID)
        if not mecatol or not any(p.controller == player.name for p in mecatol.planets):
            return 0
        self.custodian = player.name
        self.log(f"{player.name} became custodian of Mecatol Rex")
        return CUSTODIAN_VP

    def _score_secret(self, player: Player) -> int:
        """At most one secret objective per status phase."""
        for objective_id in list(player.secret_objectives):
            objective = get_objective(objective_id)
            if objective is None or not objective.is_fulfilled(self.board, player):
                continue
            player.secret_objectives.remove(objective_id)
            player.scored_secrets.append(objective_id)
            self.deal_secrets(player)
            self.log(f"{player.name} scored secret objective '{objective.name}'")
            return objective.vp
        return 0

    def _score_objectives(self, player: Player) -> int:
        scored = 0
        for objective_id in self.revealed_objectives:
            objective = get_objective(objective_id)
            holders = self.scored_objectives.setdefault(objective_id, [])
            if objective is None or player.name in holders:
                continue
            if objective.is_fulfilled(self.board, player):
                holders.append(player.name)
                scored += objective.vp
                self.log(f"{player.name} scored objective '{objective.name}'")
        return scored

    # ---------------------------------------------------------------- state
    def to_dict(self) -> dict:
        return {
            "ok": True,
            "game_id": self.id,
            "seed": self.seed,
            "round": self.turns.round,
            "phase": self.turns.phase,
            "turn": self.turns.to_dict(),
            "winner": self.winner,
            "strategy_cards": {c.id: c.to_dict() for c in STRATEGY_CARD_LIST},
            "available_strategy_cards": [
                c.to_dict()
                for c in STRATEGY_CARD_LIST
                if c.id in self.available_strategy_cards()
            ],
            "players": [p.to_dict(self.board) for p in self.players],
            "systems": self.board.to_dict(),
            "objectives": [
                dict(
                    get_objective(oid).to_dict(),
                    scored_by=list(self.scored_objectives.get(oid, [])),
                )
                for oid in self.revealed_objectives
                if get_objective(oid)
            ],
            "objective_deck": list(self.objective_deck),
            "secret_deck": list(self.secret_deck),
            "action_deck": list(self.action_deck),
            "action_discard": list(self.action_discard),
            "action_cards": {c.id: c.to_dict() for c in ACTION_CARD_LIST},
            "factions": [f.to_dict() for f in FACTION_LIST],
            "secret_objectives": {
                o.id: o.to_dict() for o in SECRET_DECK
            },
            "technologies": [t.to_dict() for t in TECHNOLOGY_LIST],
            "custodian": self.custodian,
            "played_cards": list(self.played_cards),
            "followers": {str(k): list(v) for k, v in self.followers.items()},
            "agenda": (
                dict(
                    get_agenda(self.active_agenda).to_dict(),
                    outcomes=self.agenda_outcomes(),
                    votes=dict(self.votes),
                )
                if get_agenda(self.active_agenda)
                else None
            ),
            "agenda_deck": list(self.agenda_deck),
            "laws": dict(self.laws),
            "history": self.history,
            "version": self.version,
        }

    def view_for(self, viewer: Optional[str]) -> dict:
        """Serialised state with everything hidden that ``viewer`` may not see.

        Other players keep only the number of their secret objectives and
        action cards, and the face down decks are reduced to their size.
        """
        state = self.to_dict()
        for player in state["players"]:
            if player["name"] == viewer:
                continue
            player["hidden_secret_objectives"] = len(player["secret_objectives"])
            player["hidden_action_cards"] = len(player["action_cards"])
            player["secret_objectives"] = []
            player["action_cards"] = []
        for deck in ("secret_deck", "objective_deck", "action_deck"):
            state[f"{deck}_size"] = len(state[deck])
            state[deck] = []
        return state

    @staticmethod
    def from_dict(data: dict) -> "Game":
        players = [Player.from_dict(p) for p in data["players"]]
        board = Board.from_dict(data["systems"])
        game = Game(
            players,
            board,
            int(data.get("seed", 0)),
            game_id=data.get("game_id"),
        )
        game.turns = TurnManager.from_dict(
            data.get("turn", {}), [p.name for p in players]
        )
        game.revealed_objectives = [o["id"] for o in data.get("objectives", [])]
        game.scored_objectives = {
            o["id"]: list(o.get("scored_by", [])) for o in data.get("objectives", [])
        }
        game.objective_deck = list(data.get("objective_deck", []))
        game.secret_deck = list(data.get("secret_deck", []))
        game.action_deck = list(data.get("action_deck", []))
        game.action_discard = list(data.get("action_discard", []))
        game.custodian = data.get("custodian")
        game.version = int(data.get("version", 0))
        game.played_cards = [int(c) for c in data.get("played_cards", [])]
        game.followers = {
            int(k): list(v) for k, v in (data.get("followers") or {}).items()
        }
        agenda = data.get("agenda")
        game.active_agenda = agenda["id"] if agenda else None
        game.votes = dict(agenda.get("votes", {})) if agenda else {}
        game.agenda_deck = list(data.get("agenda_deck", []))
        game.laws = dict(data.get("laws", {}))
        game.history = list(data.get("history", []))
        game.winner = data.get("winner")
        return game
