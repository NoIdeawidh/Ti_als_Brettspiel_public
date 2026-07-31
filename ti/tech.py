"""Technologies.

A technology has a colour, a cost and prerequisites expressed as "owns at
least N technologies of colour X".  Unit upgrades are modelled as a mapping
from a base unit type to an upgraded one, so the combat rules keep working on
plain :class:`~ti.units.UnitType` data and never need to know about research.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

BLUE = "blue"
GREEN = "green"
RED = "red"
YELLOW = "yellow"


@dataclass(frozen=True)
class Technology:
    id: str
    name: str
    color: str
    cost: int
    desc: str
    prerequisites: Dict[str, int] = field(default_factory=dict)
    """Required number of already owned technologies per colour."""
    upgrade: Optional[Tuple[str, str]] = None
    """``(base unit type, upgraded unit type)`` if this technology is an upgrade."""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "cost": self.cost,
            "desc": self.desc,
            "prerequisites": dict(self.prerequisites),
            "upgrade": list(self.upgrade) if self.upgrade else None,
        }


TECHNOLOGY_LIST: List[Technology] = [
    Technology(
        "antimass_deflectors",
        "Antimass Deflectors",
        BLUE,
        cost=2,
        desc="Grundlagenforschung für Antriebe",
    ),
    Technology(
        "neural_motivator",
        "Neural Motivator",
        GREEN,
        cost=2,
        desc="Grundlagenforschung für Biotechnik",
    ),
    Technology(
        "plasma_scoring",
        "Plasma Scoring",
        RED,
        cost=2,
        desc="Grundlagenforschung für Waffensysteme",
    ),
    Technology(
        "sarween_tools",
        "Sarween Tools",
        YELLOW,
        cost=2,
        desc="Grundlagenforschung für Fertigung",
    ),
    Technology(
        "fighter_ii",
        "Fighter II",
        BLUE,
        cost=4,
        desc="Jäger bewegen sich selbstständig und treffen besser",
        prerequisites={BLUE: 1},
        upgrade=("Fighter", "Fighter II"),
    ),
    Technology(
        "carrier_ii",
        "Carrier II",
        BLUE,
        cost=4,
        desc="Träger sind schneller und laden mehr",
        prerequisites={BLUE: 1},
        upgrade=("Carrier", "Carrier II"),
    ),
    Technology(
        "infantry_ii",
        "Infantry II",
        GREEN,
        cost=4,
        desc="Infanterie kämpft am Boden stärker",
        prerequisites={GREEN: 1},
        upgrade=("Infantry", "Infantry II"),
    ),
    Technology(
        "pds_ii",
        "PDS II",
        RED,
        cost=4,
        desc="Planetare Abwehr trifft härter",
        prerequisites={RED: 1},
        upgrade=("PDS", "PDS II"),
    ),
    Technology(
        "space_dock_ii",
        "Space Dock II",
        YELLOW,
        cost=4,
        desc="Werften produzieren mehr Einheiten",
        prerequisites={YELLOW: 1},
        upgrade=("Space Dock", "Space Dock II"),
    ),
    Technology(
        "cruiser_ii",
        "Cruiser II",
        RED,
        cost=6,
        desc="Kreuzer werden schneller, stärker und transportfähig",
        prerequisites={RED: 1, BLUE: 1, YELLOW: 1},
        upgrade=("Cruiser", "Cruiser II"),
    ),
    Technology(
        "dreadnought_ii",
        "Dreadnought II",
        RED,
        cost=6,
        desc="Dreadnoughts werden schneller und stärker",
        prerequisites={RED: 1, BLUE: 1},
        upgrade=("Dreadnought", "Dreadnought II"),
    ),
]

TECHNOLOGIES: Dict[str, Technology] = {t.id: t for t in TECHNOLOGY_LIST}


def get_technology(tech_id: Optional[str]) -> Optional[Technology]:
    return TECHNOLOGIES.get(tech_id or "")


def owned_colors(tech_ids: Sequence[str]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for tech_id in tech_ids:
        tech = get_technology(tech_id)
        if tech:
            counts[tech.color] = counts.get(tech.color, 0) + 1
    return counts


def missing_prerequisites(
    technology: Technology, tech_ids: Sequence[str]
) -> Dict[str, int]:
    """Colours (and how many) the player is still short of."""
    counts = owned_colors(tech_ids)
    return {
        color: needed - counts.get(color, 0)
        for color, needed in technology.prerequisites.items()
        if counts.get(color, 0) < needed
    }


def upgrades_of(tech_ids: Sequence[str]) -> Dict[str, str]:
    """Mapping base unit type -> upgraded unit type for the owned technologies."""
    upgrades: Dict[str, str] = {}
    for tech_id in tech_ids:
        tech = get_technology(tech_id)
        if tech and tech.upgrade:
            base, upgraded = tech.upgrade
            upgrades[base] = upgraded
    return upgrades
