"""Static unit definitions.

Keeping unit stats in one table makes it easy to add new unit types or to
override them later with faction specific or house rule variants.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class UnitType:
    name: str
    cost: int
    combat: int
    """Dice result needed *or lower* to score a hit (d10)."""
    dice: int = 1
    move: int = 0
    capacity: int = 0
    ship: bool = True
    structure: bool = False
    """Structures are built on a planet and never move."""
    production: int = 0
    """Extra units this structure allows to be produced in its system."""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "cost": self.cost,
            "combat": self.combat,
            "dice": self.dice,
            "move": self.move,
            "capacity": self.capacity,
            "ship": self.ship,
            "structure": self.structure,
            "production": self.production,
        }


UNIT_TYPES: Dict[str, UnitType] = {
    u.name: u
    for u in [
        UnitType("Fighter", cost=1, combat=1, move=0, capacity=0),
        UnitType("Carrier", cost=3, combat=1, move=1, capacity=4),
        UnitType("Destroyer", cost=1, combat=2, move=2),
        UnitType("Cruiser", cost=2, combat=2, move=2),
        UnitType("Dreadnought", cost=4, combat=3, move=1, capacity=1),
        UnitType("Flagship", cost=8, combat=5, dice=2, move=1, capacity=3),
        UnitType("Infantry", cost=1, combat=2, move=0, ship=False),
        UnitType(
            "Space Dock",
            cost=4,
            combat=0,
            ship=False,
            structure=True,
            production=3,
        ),
        UnitType("PDS", cost=2, combat=3, ship=False, structure=True),
    ]
}

STRUCTURE_TYPES = [u for u in UNIT_TYPES.values() if u.structure]

DEFAULT_START_UNITS = ["Carrier", "Cruiser", "Fighter", "Fighter"]


def get_unit_type(name: str) -> UnitType:
    try:
        return UNIT_TYPES[name]
    except KeyError as exc:  # pragma: no cover - defensive
        raise ValueError(f"Unknown unit type: {name}") from exc
