"""Aggregate game object: state, action dispatch and round flow."""

from __future__ import annotations

import random
import uuid
from typing import Dict, List, Optional, Sequence

from ti.cards import STRATEGY_CARD_LIST, get_card
from ti.engine import ActionResult, Engine
from ti.models import Board, Player
from ti.phases import Phase, TurnManager
from ti.setup import MECATOL_ID, new_game_state

VICTORY_POINTS_TO_WIN = 10


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
        self.engine = Engine(board, self.rng)
        self.turns = TurnManager([p.name for p in self.players])
        self.history: List[str] = [f"Game created seed={seed}"]
        self.winner: Optional[str] = None

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

    def log(self, message: str) -> None:
        self.history.append(f"[R{self.turns.round}] {message}")

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

        result = handler(player, action or {})
        if result.ok:
            self.log(result.message)
        return result

    def _check_turn(self, player: Player, action_type: str) -> Optional[ActionResult]:
        expected_phase = (
            Phase.STRATEGY if action_type == "select_strategy" else Phase.ACTION
        )
        if self.turns.phase != expected_phase:
            return ActionResult(
                False,
                f"Action '{action_type}' not allowed in phase '{self.turns.phase}'",
            )
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
        player.resources += card.bonus_resources
        player.influence += card.bonus_influence
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

    def _action_move(self, player: Player, action: dict) -> ActionResult:
        return self.engine.move(
            player.name,
            action.get("from"),
            action.get("to"),
            action.get("units"),
        )

    def _action_produce(self, player: Player, action: dict) -> ActionResult:
        units = action.get("units") or []
        result = self.engine.produce(
            player.name, action.get("system"), units, player.resources
        )
        if result.ok:
            player.resources -= int(result.data.get("cost", 0))
        return result

    def _action_invade(self, player: Player, action: dict) -> ActionResult:
        return self.engine.invade(
            player.name, action.get("system"), action.get("planet")
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

    # --------------------------------------------------------- status phase
    def _maybe_run_status_phase(self) -> None:
        if self.turns.phase != Phase.STATUS:
            return
        self.run_status_phase()

    def run_status_phase(self) -> None:
        for player in self.players:
            income = sum(p.resources for p in self.board.planets_of(player.name))
            influence = sum(p.influence for p in self.board.planets_of(player.name))
            player.resources += income
            player.influence += influence

            scored = self._score_victory_points(player)
            if scored:
                self.log(f"{player.name} scored {scored} victory point(s)")

            player.strategy_card = None
            player.passed = False

        leader = max(self.players, key=lambda p: p.vp, default=None)
        if leader is not None and leader.vp >= VICTORY_POINTS_TO_WIN:
            self.winner = leader.name
            self.turns.finish()
            self.log(f"{leader.name} won the game with {leader.vp} victory points")
            return

        self.turns.begin_next_round()
        self.log("New round started")

    def _score_victory_points(self, player: Player) -> int:
        scored = 0
        mecatol = self.board.get(MECATOL_ID)
        if mecatol and any(p.controller == player.name for p in mecatol.planets):
            scored += 1
        card = get_card(player.strategy_card) if player.strategy_card else None
        if card:
            scored += card.bonus_vp
        player.vp += scored
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
            "available_strategy_cards": [
                c.to_dict()
                for c in STRATEGY_CARD_LIST
                if c.id in self.available_strategy_cards()
            ],
            "players": [p.to_dict(self.board) for p in self.players],
            "systems": self.board.to_dict(),
            "history": self.history,
        }

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
        game.history = list(data.get("history", []))
        game.winner = data.get("winner")
        return game
