"""Static unit definitions.

Keeping unit stats in one table makes it easy to add new unit types or to
override them later with faction specific or house rule variants.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


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
    base_type: Optional[str] = None
    """Set on upgraded types; upgrades replace their base type on the board."""

    @property
    def base_name(self) -> str:
        return self.base_type or self.name

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
            "base_type": self.base_type,
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
        UnitType("Fighter II", cost=1, combat=2, move=2, base_type="Fighter"),
        UnitType("Carrier II", cost=3, combat=1, move=2, capacity=6, base_type="Carrier"),
        UnitType(
            "Cruiser II", cost=2, combat=3, move=3, capacity=1, base_type="Cruiser"
        ),
        UnitType(
            "Dreadnought II",
            cost=4,
            combat=4,
            move=2,
            capacity=1,
            base_type="Dreadnought",
        ),
        UnitType(
            "Infantry II", cost=1, combat=3, move=0, ship=False, base_type="Infantry"
        ),
        UnitType(
            "Space Dock II",
            cost=4,
            combat=0,
            ship=False,
            structure=True,
            production=5,
            base_type="Space Dock",
        ),
        UnitType(
            "PDS II",
            cost=2,
            combat=4,
            dice=2,
            ship=False,
            structure=True,
            base_type="PDS",
        ),
    ]
}

STRUCTURE_TYPES = [u for u in UNIT_TYPES.values() if u.structure]

DEFAULT_START_UNITS = ["Carrier", "Cruiser", "Fighter", "Fighter"]


def get_unit_type(name: str) -> UnitType:
    try:
        return UNIT_TYPES[name]
    except KeyError as exc:  # pragma: no cover - defensive
        raise ValueError(f"Unknown unit type: {name}") from exc
