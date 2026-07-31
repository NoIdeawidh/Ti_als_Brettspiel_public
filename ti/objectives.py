"""Public objectives.

An objective is a named condition over the board state.  One objective is
revealed per round; in the status phase every player who fulfils a revealed
objective scores it once.  Adding a new objective (or a house rule variant)
only means appending an entry to :data:`OBJECTIVE_DECK`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ti.models import Board, Player


Requirement = Callable[["Board", "Player"], bool]


@dataclass(frozen=True)
class Objective:
    id: str
    name: str
    desc: str
    vp: int
    requirement: Requirement

    def is_fulfilled(self, board: "Board", player: "Player") -> bool:
        return self.requirement(board, player)

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "desc": self.desc, "vp": self.vp}


def _planet_count(board: "Board", player: "Player") -> int:
    return len(board.planets_of(player.name))


def _controls_mecatol(board: "Board", player: "Player") -> bool:
    from ti.setup import MECATOL_ID

    system = board.get(MECATOL_ID)
    return bool(system) and any(p.controller == player.name for p in system.planets)


def _fleet_size(board: "Board", player: "Player") -> int:
    return len([u for u in board.units_of(player.name) if u.is_ship])


def _total_resources(board: "Board", player: "Player") -> int:
    return sum(p.resources for p in board.planets_of(player.name))


def _total_influence(board: "Board", player: "Player") -> int:
    return sum(p.influence for p in board.planets_of(player.name))


def _systems_with_ships(board: "Board", player: "Player") -> int:
    return len([s for s in board.systems if s.units_of(player.name)])


OBJECTIVE_DECK: List[Objective] = [
    Objective(
        "expand_borders",
        "Grenzen erweitern",
        "Kontrolliere mindestens 3 Planeten",
        1,
        lambda board, player: _planet_count(board, player) >= 3,
    ),
    Objective(
        "corporate_growth",
        "Wirtschaftsmacht",
        "Kontrolliere Planeten mit zusammen mindestens 6 Ressourcen",
        1,
        lambda board, player: _total_resources(board, player) >= 6,
    ),
    Objective(
        "diplomatic_weight",
        "Diplomatisches Gewicht",
        "Kontrolliere Planeten mit zusammen mindestens 6 Einfluss",
        1,
        lambda board, player: _total_influence(board, player) >= 6,
    ),
    Objective(
        "armada",
        "Armada",
        "Habe mindestens 6 Schiffe im Spiel",
        1,
        lambda board, player: _fleet_size(board, player) >= 6,
    ),
    Objective(
        "sprawling_fleet",
        "Weit verstreute Flotte",
        "Habe Schiffe in mindestens 3 Systemen",
        1,
        lambda board, player: _systems_with_ships(board, player) >= 3,
    ),
    Objective(
        "seat_of_the_empire",
        "Thron des Imperiums",
        "Kontrolliere Mecatol Rex",
        2,
        _controls_mecatol,
    ),
    Objective(
        "galactic_power",
        "Galaktische Vormacht",
        "Kontrolliere mindestens 6 Planeten",
        2,
        lambda board, player: _planet_count(board, player) >= 6,
    ),
]

OBJECTIVES: Dict[str, Objective] = {o.id: o for o in OBJECTIVE_DECK}


def get_objective(objective_id: str) -> Optional[Objective]:
    return OBJECTIVES.get(objective_id)
