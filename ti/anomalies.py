"""Anomalies and wormholes.

Anomalies restrict or modify movement, wormholes create extra adjacencies
between distant systems.  Both are pure data on :class:`~ti.models.System`,
so new map features are added here instead of in the movement rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

ASTEROID_FIELD = "asteroid_field"
NEBULA = "nebula"
SUPERNOVA = "supernova"
GRAVITY_RIFT = "gravity_rift"

WORMHOLE_ALPHA = "alpha"
WORMHOLE_BETA = "beta"


@dataclass(frozen=True)
class Anomaly:
    id: str
    name: str
    desc: str
    required_technology: Optional[str] = None
    """Without this technology the system cannot be entered."""
    passable: bool = True
    """A blocked system can never be entered."""
    movement_bonus: int = 0
    """Added to the movement range of ships leaving the system."""
    defender_combat_bonus: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "desc": self.desc,
            "required_technology": self.required_technology,
            "passable": self.passable,
            "movement_bonus": self.movement_bonus,
            "defender_combat_bonus": self.defender_combat_bonus,
        }


ANOMALY_LIST: List[Anomaly] = [
    Anomaly(
        ASTEROID_FIELD,
        "Asteroidenfeld",
        "Nur mit Antimass Deflectors befahrbar",
        required_technology="antimass_deflectors",
    ),
    Anomaly(
        NEBULA,
        "Nebel",
        "Verteidiger kämpfen mit +1",
        defender_combat_bonus=1,
    ),
    Anomaly(
        SUPERNOVA,
        "Supernova",
        "Unpassierbar",
        passable=False,
    ),
    Anomaly(
        GRAVITY_RIFT,
        "Gravitationsriss",
        "Schiffe von hier bewegen sich ein Feld weiter",
        movement_bonus=1,
    ),
]

ANOMALIES: Dict[str, Anomaly] = {a.id: a for a in ANOMALY_LIST}

WORMHOLES: Tuple[str, ...] = (WORMHOLE_ALPHA, WORMHOLE_BETA)


def get_anomaly(anomaly_id: Optional[str]) -> Optional[Anomaly]:
    if anomaly_id is None:
        return None
    return ANOMALIES.get(anomaly_id)


def entry_blocker(
    anomaly_id: Optional[str], technologies: Tuple[str, ...]
) -> Optional[str]:
    """Reason why the system cannot be entered, or ``None`` if it can."""
    anomaly = get_anomaly(anomaly_id)
    if anomaly is None:
        return None
    if not anomaly.passable:
        return f"{anomaly.name} kann nicht befahren werden"
    if anomaly.required_technology and anomaly.required_technology not in technologies:
        return f"{anomaly.name} erfordert {anomaly.required_technology}"
    return None


def movement_bonus(anomaly_id: Optional[str]) -> int:
    anomaly = get_anomaly(anomaly_id)
    return anomaly.movement_bonus if anomaly else 0


def defender_combat_bonus(anomaly_id: Optional[str]) -> int:
    anomaly = get_anomaly(anomaly_id)
    return anomaly.defender_combat_bonus if anomaly else 0
