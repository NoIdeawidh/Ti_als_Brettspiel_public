"""Factions and their asymmetric starting position.

A faction is a data row: extra starting commodities, starting technologies,
additional home units and a flat combat modifier.  Adding a faction (or a
house rule variant) means appending an entry here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

DEFAULT_FACTION = "Federation"


@dataclass(frozen=True)
class Faction:
    id: str
    name: str
    desc: str
    resources: int = 0
    influence: int = 0
    trade_goods: int = 0
    command_tokens: int = 0
    technologies: Tuple[str, ...] = ()
    """Technologies the faction starts with."""
    units: Tuple[str, ...] = ()
    """Additional units placed in the home system at setup."""
    combat_bonus: int = 0
    """Added to the combat value of every unit the faction owns."""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "desc": self.desc,
            "resources": self.resources,
            "influence": self.influence,
            "trade_goods": self.trade_goods,
            "command_tokens": self.command_tokens,
            "technologies": list(self.technologies),
            "units": list(self.units),
            "combat_bonus": self.combat_bonus,
        }


FACTION_LIST: List[Faction] = [
    Faction(
        "Federation",
        "Federation of Sol",
        "Ausgewogen: zusätzliche Infanterie im Heimatsystem",
        units=("Infantry", "Infantry"),
    ),
    Faction(
        "Sardakk",
        "Sardakk N'orr",
        "Kriegerisch: +1 auf alle Kampfwürfe, dafür weniger Wirtschaft",
        influence=-1,
        combat_bonus=1,
    ),
    Faction(
        "Arborec",
        "Arborec",
        "Produktiv: mehr Ressourcen und ein zusätzlicher Träger",
        resources=2,
        units=("Carrier",),
    ),
    Faction(
        "Clan",
        "Clan of Saar",
        "Händler: startet mit Handelsgütern und Antimass Deflectors",
        trade_goods=3,
        technologies=("antimass_deflectors",),
    ),
    Faction(
        "Jol-Nar",
        "Universities of Jol-Nar",
        "Forscher: zwei Starttechnologien, aber schlechtere Kampfwerte",
        technologies=("antimass_deflectors", "sarween_tools"),
        combat_bonus=-1,
    ),
]

FACTIONS: Dict[str, Faction] = {f.id: f for f in FACTION_LIST}


def get_faction(faction_id: Optional[str]) -> Optional[Faction]:
    if faction_id is None:
        return None
    return FACTIONS.get(faction_id)


def combat_bonus(faction_id: Optional[str]) -> int:
    faction = get_faction(faction_id)
    return faction.combat_bonus if faction else 0
