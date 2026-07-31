"""Rule enforcement for player actions.

The engine validates and applies a single action against the board.  It never
decides *whose* turn it is - that is the responsibility of :mod:`ti.phases`.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from ti.combat import (
    assign_hits,
    resolve_ground_combat,
    resolve_space_combat,
    roll_dice,
)
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
    def invade(
        self,
        player: str,
        system_id: str,
        planet_name: str,
        unit_uids: Optional[Sequence[str]] = None,
    ) -> ActionResult:
        """Land ground forces on a planet, fighting its garrison if needed."""
        try:
            system = self.board.require(system_id)
        except KeyError as exc:
            return ActionResult(False, str(exc))

        planet = self._find_planet(system, planet_name)
        if planet is None:
            return ActionResult(False, f"Unknown planet: {planet_name}")
        if planet.controller == player:
            return ActionResult(False, "Planet is already under your control")
        if [n for n in system.occupants() if n != player]:
            return ActionResult(False, "Enemy ships still block the system")

        ground_forces = [u for u in system.units_of(player) if not u.is_ship]
        landing = self._select_units(ground_forces, unit_uids)
        if not landing:
            return ActionResult(
                False, "No ground forces available in this system"
            )

        previous = planet.controller
        system.remove_units(player, [u.uid for u in landing])
        bombardment = self._planetary_defence(planet, landing)
        landing = [u for u in landing if u.uid not in set(bombardment["losses"])]
        if not landing:
            return ActionResult(
                True,
                f"{player} lost the landing party to planetary defences",
                {
                    "planet": planet.name,
                    "captured": False,
                    "previous_controller": previous,
                    "planetary_defence": bombardment,
                },
            )

        report = resolve_ground_combat(planet, player, landing, self.rng)

        if report["captured"]:
            planet.structures.clear()
        else:
            survivors = [u for u in landing if u.uid in report["surviving_attackers"]]
            system.add_units(player, survivors)

        message = (
            f"{player} took control of {planet.name}"
            if report["captured"]
            else f"{player} failed to capture {planet.name}"
        )
        return ActionResult(
            True,
            message,
            {
                "planet": planet.name,
                "captured": report["captured"],
                "previous_controller": previous,
                "planetary_defence": bombardment,
                "ground_combat": report,
            },
        )

    def _planetary_defence(self, planet: Planet, landing: List[Unit]) -> dict:
        """PDS structures fire at the landing party before ground combat."""
        defences = [u for u in planet.structures if u.combat > 0]
        if not defences:
            return {"hits": 0, "losses": []}
        roll = roll_dice(defences, self.rng)
        losses = assign_hits(list(landing), int(roll["hits"]))
        return {"hits": roll["hits"], "losses": [u.uid for u in losses]}

    # ------------------------------------------------------------ production
    def production_capacity(self, player: str, system: System) -> int:
        capacity = 0
        for planet in system.planets:
            if planet.controller != player:
                continue
            capacity += 2
            capacity += sum(
                get_unit_type(u.type_name).production
                for u in planet.structures_of(player)
            )
        return capacity

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

        if any(get_unit_type(name).structure for name in unit_types):
            return ActionResult(
                False, "Structures are built with the 'build' action"
            )

        units = [Unit.create(name, player) for name in unit_types]
        ships = [u for u in units if u.is_ship]
        ground = [u for u in units if not u.is_ship]
        system.add_units(player, ships)
        if ground:
            home = next(p for p in system.planets if p.controller == player)
            home.ground_forces.extend(ground)
        return ActionResult(
            True,
            f"{player} produced {len(units)} unit(s) in {system.id}",
            {"cost": cost, "produced": [u.to_dict() for u in units]},
        )

    # ------------------------------------------------------------ buildings
    def build(
        self, player: str, system_id: str, planet_name: str, structure: str, budget: int
    ) -> ActionResult:
        """Place a structure on a controlled planet."""
        try:
            system = self.board.require(system_id)
        except KeyError as exc:
            return ActionResult(False, str(exc))

        planet = self._find_planet(system, planet_name)
        if planet is None:
            return ActionResult(False, f"Unknown planet: {planet_name}")
        if planet.controller != player:
            return ActionResult(False, "You do not control this planet")

        try:
            unit_type = get_unit_type(structure)
        except ValueError as exc:
            return ActionResult(False, str(exc))
        if not unit_type.structure:
            return ActionResult(False, f"{structure} is not a structure")
        if any(u.type_name == structure for u in planet.structures):
            return ActionResult(False, f"{planet.name} already has a {structure}")
        if unit_type.cost > budget:
            return ActionResult(
                False,
                f"Not enough resources: need {unit_type.cost}, have {budget}",
            )

        planet.structures.append(Unit.create(structure, player))
        return ActionResult(
            True,
            f"{player} built a {structure} on {planet.name}",
            {"cost": unit_type.cost, "planet": planet.name, "structure": structure},
        )

    @staticmethod
    def _find_planet(system: System, planet_name: str) -> Optional[Planet]:
        for planet in system.planets:
            if planet.name == planet_name:
                return planet
        return None
