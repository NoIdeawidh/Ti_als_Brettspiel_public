"""Simple opponents for single player games.

A bot is an ordinary player whose actions are chosen by :func:`next_action`.
The policy only produces regular actions, so bots are bound by exactly the
same rules as human players and new rules apply to them automatically.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from ti.models import Player, Unit
from ti.phases import Phase
from ti.units import get_unit_type

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ti.game import Game

MAX_BOT_ACTIONS = 200
"""Safety net so a broken policy cannot loop forever."""

PRODUCTION_ORDER = ["Cruiser", "Carrier", "Infantry", "Fighter"]
"""Units a bot tries to build, most valuable first."""

STRUCTURE_ORDER = ["Space Dock", "PDS"]
"""Structures a bot places when Construction granted free ones."""


def next_action(game: "Game", player: Player) -> Optional[dict]:
    """The action the bot wants to take now, or ``None`` to stay idle."""
    if game.turns.phase == Phase.STRATEGY:
        return _pick_strategy(game)
    if game.turns.phase == Phase.AGENDA:
        return _vote(game, player)
    if game.turns.phase != Phase.ACTION:
        return None
    return (
        _play_strategy(game, player)
        or _invade(game, player)
        or _build(game, player)
        or _produce(game, player)
        or _advance(game, player)
        or {"type": "pass"}
    )


def act_for_bots(game: "Game") -> List[str]:
    """Let every bot act until a human player is to move again."""
    messages: List[str] = []
    for _ in range(MAX_BOT_ACTIONS):
        player = _bot_to_act(game)
        if player is None:
            return messages
        action = next_action(game, player)
        if action is None:
            return messages
        result = game.apply_action(player.name, action)
        messages.append(result.message)
        if not result.ok:
            # A rejected action would repeat forever; hand the turn over.
            for fallback in ({"type": "end_turn"}, {"type": "pass"}):
                answer = game.apply_action(player.name, fallback)
                messages.append(answer.message)
                if answer.ok:
                    break
            else:
                return messages
    return messages


def _bot_to_act(game: "Game") -> Optional[Player]:
    if game.turns.phase == Phase.AGENDA:
        return next(
            (
                p
                for p in game.players
                if p.is_bot and p.name not in game.votes
            ),
            None,
        )
    current = game.turns.current_player
    if current is None:
        return None
    player = game.get_player(current)
    return player if player is not None and player.is_bot else None


def _pick_strategy(game: "Game") -> Optional[dict]:
    available = game.available_strategy_cards()
    if not available:
        return None
    return {"type": "select_strategy", "card_id": available[0]}


def _vote(game: "Game", player: Player) -> Optional[dict]:
    outcomes = game.agenda_outcomes()
    if not outcomes:
        return None
    own = player.name if player.name in outcomes else outcomes[0]
    return {
        "type": "vote",
        "outcome": own,
        "influence": min(1, player.influence),
    }


def _play_strategy(game: "Game", player: Player) -> Optional[dict]:
    if player.strategy_card and player.strategy_card not in game.played_cards:
        return {"type": "play_strategy"}
    return None


def _invade(game: "Game", player: Player) -> Optional[dict]:
    if player.command_tokens < 1:
        return None
    for system in game.board.systems:
        troops = [u for u in system.units_of(player.name) if not u.is_ship]
        if not troops:
            continue
        for planet in system.planets:
            if planet.controller != player.name:
                return {
                    "type": "invade",
                    "system": system.id,
                    "planet": planet.name,
                }
    return None


def _build(game: "Game", player: Player) -> Optional[dict]:
    """Spend free structures from Construction while they last."""
    if player.command_tokens < 1 or player.free_structures < 1:
        return None
    for system in game.board.systems:
        for planet in system.planets:
            if planet.controller != player.name:
                continue
            existing = {
                get_unit_type(u.type_name).base_name for u in planet.structures
            }
            for structure in STRUCTURE_ORDER:
                if structure not in existing:
                    return {
                        "type": "build",
                        "system": system.id,
                        "planet": planet.name,
                        "structure": structure,
                    }
    return None


def _produce(game: "Game", player: Player) -> Optional[dict]:
    if player.command_tokens < 1:
        return None
    system = game.board.home_system(player.name)
    if system is None:
        return None
    for unit in PRODUCTION_ORDER:
        name = game.unit_type_for(player, unit)
        if get_unit_type(name).cost <= player.budget:
            return {"type": "produce", "system": system.id, "units": [name]}
    return None


def _advance(game: "Game", player: Player) -> Optional[dict]:
    """Move a fleet towards the nearest system the bot does not control yet."""
    if player.command_tokens < 1:
        return None
    for source in game.board.systems:
        units = _travel_group(source.units_of(player.name))
        if not units:
            continue
        for target in game.board.neighbors(source.id):
            if any(p.controller != player.name for p in target.planets):
                return {
                    "type": "move",
                    "from": source.id,
                    "to": target.id,
                    "units": [u.uid for u in units],
                }
    return None


def _travel_group(units: List[Unit]) -> List[Unit]:
    """Moving ships plus as many passengers as they can carry."""
    ships = [u for u in units if u.is_ship and u.move]
    if not ships:
        return []
    capacity = sum(u.capacity for u in ships)
    passengers = [u for u in units if not u.move][:capacity]
    return ships + passengers
