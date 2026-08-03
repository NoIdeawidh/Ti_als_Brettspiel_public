"""Public and secret objectives.

An objective is a named condition over the board state.  One public objective
is revealed per round; in the status phase every player who fulfils a revealed
objective scores it once.  Secret objectives (:data:`SECRET_DECK`) are dealt to
individual players and score only for their holder.  Adding a new objective (or
a house rule variant) only means appending an entry to the matching deck.
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
    Objective(
        "industrial_base",
        "Industrielle Basis",
        "Habe mindestens 2 Bauwerke im Spiel",
        1,
        lambda board, player: _structure_count(board, player) >= 2,
    ),
    Objective(
        "research_program",
        "Forschungsprogramm",
        "Besitze mindestens 2 Technologien",
        1,
        lambda board, player: len(player.technologies) >= 2,
    ),
    Objective(
        "standing_army",
        "Stehendes Heer",
        "Habe mindestens 4 Bodentruppen auf eigenen Planeten",
        1,
        lambda board, player: _ground_forces(board, player) >= 4,
    ),
    Objective(
        "deep_space_presence",
        "Tiefenraumpräsenz",
        "Habe Schiffe in mindestens 5 Systemen",
        2,
        lambda board, player: _systems_with_ships(board, player) >= 5,
    ),
]


def _structure_count(board: "Board", player: "Player") -> int:
    return sum(
        len(planet.structures_of(player.name))
        for planet in board.planets_of(player.name)
    )


def _ground_forces(board: "Board", player: "Player") -> int:
    return sum(
        len(planet.garrison_of(player.name))
        for planet in board.planets_of(player.name)
    )


def _foreign_home_planets(board: "Board", player: "Player") -> int:
    """Home planets under the player's control besides their own."""
    own = board.home_system(player.name)
    own_names = {p.name for p in own.planets} if own else set()
    return len(
        [
            planet
            for planet in board.planets_of(player.name)
            if planet.home and planet.name not in own_names
        ]
    )


def _occupied_planets(board: "Board", player: "Player") -> int:
    return len(
        [p for p in board.planets_of(player.name) if p.garrison_of(player.name)]
    )


def _largest_fleet(board: "Board", player: "Player") -> int:
    return max(
        (len([u for u in s.units_of(player.name) if u.is_ship]) for s in board.systems),
        default=0,
    )


def _fortified_planets(board: "Board", player: "Player") -> int:
    return len(
        [
            planet
            for planet in board.planets_of(player.name)
            if len({u.type_name for u in planet.structures_of(player.name)}) >= 2
        ]
    )


SECRET_DECK: List[Objective] = [
    Objective(
        "throne_claim",
        "Anspruch auf den Thron",
        "Kontrolliere Mecatol Rex",
        1,
        _controls_mecatol,
    ),
    Objective(
        "foreign_flag",
        "Fremde Flagge",
        "Kontrolliere einen fremden Heimatplaneten",
        2,
        lambda board, player: _foreign_home_planets(board, player) >= 1,
    ),
    Objective(
        "iron_fist",
        "Eiserne Faust",
        "Halte Bodentruppen auf mindestens 3 Planeten",
        1,
        lambda board, player: _occupied_planets(board, player) >= 3,
    ),
    Objective(
        "shadow_fleet",
        "Schattenflotte",
        "Habe mindestens 4 Schiffe in einem System",
        1,
        lambda board, player: _largest_fleet(board, player) >= 4,
    ),
    Objective(
        "fortress_world",
        "Festungswelt",
        "Habe zwei verschiedene Bauwerke auf einem Planeten",
        1,
        lambda board, player: _fortified_planets(board, player) >= 1,
    ),
    Objective(
        "tech_supremacy",
        "Technologische Vormacht",
        "Besitze mindestens 4 Technologien",
        1,
        lambda board, player: len(player.technologies) >= 4,
    ),
    Objective(
        "war_chest",
        "Kriegskasse",
        "Habe mindestens 10 Ressourcen",
        1,
        lambda board, player: player.resources >= 10,
    ),
]

OBJECTIVES: Dict[str, Objective] = {
    o.id: o for o in list(OBJECTIVE_DECK) + list(SECRET_DECK)
}


def get_objective(objective_id: str) -> Optional[Objective]:
    return OBJECTIVES.get(objective_id)
