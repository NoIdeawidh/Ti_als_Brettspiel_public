"""Rule enforcement for player actions.

The engine validates and applies a single action against the board.  It never
decides *whose* turn it is - that is the responsibility of :mod:`ti.phases`.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from ti.combat import resolve_space_combat
from ti.models import Board, Planet, System, Unit
from ti.units import get_unit_type


@dataclass
class ActionResult:
    ok: bool
    message: str
    data: Dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"ok": self.ok, "msg": self.message, **self.data}


class RuleError(Exception):
    """Raised when an action violates the rules."""


class Engine:
    def __init__(self, board: Board, rng: Optional[random.Random] = None) -> None:
        self.board = board
        self.rng = rng or random.Random()

    # ------------------------------------------------------------------ move
    def move(
        self,
        player: str,
        src_id: str,
        dst_id: str,
        unit_uids: Optional[Sequence[str]] = None,
    ) -> ActionResult:
        try:
            src = self.board.require(src_id)
            dst = self.board.require(dst_id)
        except KeyError as exc:
            return ActionResult(False, str(exc))

        if src.id == dst.id:
            return ActionResult(False, "Source and destination are identical")

        available = src.units_of(player)
        if not available:
            return ActionResult(False, "No units in the source system")

        units = self._select_units(available, unit_uids)
        if not units:
            return ActionResult(False, "No matching units to move")

        distance = src.hex.distance(dst.hex)
        try:
            self._validate_movement(units, distance)
        except RuleError as exc:
            return ActionResult(False, str(exc))

        src.remove_units(player, [u.uid for u in units])
        dst.add_units(player, units)

        result = ActionResult(
            True,
            f"{player} moved {len(units)} unit(s) from {src.id} to {dst.id}",
            {"moved": [u.uid for u in units], "distance": distance},
        )
        combat = self.resolve_combat_in(dst, attacker=player)
        if combat:
            result.data["combat"] = combat
        return result

    def _select_units(
        self, available: List[Unit], unit_uids: Optional[Sequence[str]]
    ) -> List[Unit]:
        if unit_uids is None:
            return list(available)
        wanted = set(unit_uids)
        return [u for u in available if u.uid in wanted]

    def _validate_movement(self, units: Sequence[Unit], distance: int) -> None:
        """Ships need enough movement; units without movement need transport."""
        carriers = [u for u in units if u.move > 0]
        passengers = [u for u in units if u.move == 0]

        if not carriers:
            raise RuleError("Selected units cannot move on their own")

        slowest = min(u.move for u in carriers)
        if distance > slowest:
            raise RuleError(
                f"Distance {distance} exceeds movement range {slowest}"
            )

        capacity = sum(u.capacity for u in carriers)
        if len(passengers) > capacity:
            raise RuleError(
                f"Not enough capacity: {len(passengers)} units need transport, "
                f"capacity is {capacity}"
            )

    # ---------------------------------------------------------------- combat
    def resolve_combat_in(self, system: System, attacker: str) -> Optional[dict]:
        opponents = [name for name in system.occupants() if name != attacker]
        if not opponents or not system.units_of(attacker):
            return None
        # fight opponents one after another, strongest fleet first
        report = None
        for defender in sorted(
            opponents, key=lambda n: len(system.units_of(n)), reverse=True
        ):
            if not system.units_of(attacker):
                break
            report = resolve_space_combat(system, attacker, defender, self.rng)
        return report

    # ------------------------------------------------------------- invasion
    def invade(self, player: str, system_id: str, planet_name: str) -> ActionResult:
        try:
            system = self.board.require(system_id)
        except KeyError as exc:
            return ActionResult(False, str(exc))

        planet = self._find_planet(system, planet_name)
        if planet is None:
            return ActionResult(False, f"Unknown planet: {planet_name}")
        if planet.controller == player:
            return ActionResult(False, "Planet is already under your control")
        if not system.units_of(player):
            return ActionResult(False, "You have no units in this system")
        if [n for n in system.occupants() if n != player]:
            return ActionResult(False, "Enemy ships still block the system")

        previous = planet.controller
        planet.controller = player
        return ActionResult(
            True,
            f"{player} took control of {planet.name}",
            {"planet": planet.name, "previous_controller": previous},
        )

    # ------------------------------------------------------------ production
    def production_capacity(self, player: str, system: System) -> int:
        return sum(2 for p in system.planets if p.controller == player)

    def produce(
        self, player: str, system_id: str, unit_types: Sequence[str], budget: int
    ) -> ActionResult:
        """Build units in a system; returns the resource cost in ``data``."""
        try:
            system = self.board.require(system_id)
        except KeyError as exc:
            return ActionResult(False, str(exc))

        if not any(p.controller == player for p in system.planets):
            return ActionResult(False, "You control no planet in this system")
        if [n for n in system.occupants() if n != player]:
            return ActionResult(False, "Enemy ships block production")

        capacity = self.production_capacity(player, system)
        if len(unit_types) > capacity:
            return ActionResult(
                False, f"Production capacity {capacity} exceeded"
            )

        try:
            cost = sum(get_unit_type(name).cost for name in unit_types)
        except ValueError as exc:
            return ActionResult(False, str(exc))
        if cost > budget:
            return ActionResult(
                False, f"Not enough resources: need {cost}, have {budget}"
            )

        units = [Unit.create(name, player) for name in unit_types]
        system.add_units(player, units)
        return ActionResult(
            True,
            f"{player} produced {len(units)} unit(s) in {system.id}",
            {"cost": cost, "produced": [u.to_dict() for u in units]},
        )

    @staticmethod
    def _find_planet(system: System, planet_name: str) -> Optional[Planet]:
        for planet in system.planets:
            if planet.name == planet_name:
                return planet
        return None
