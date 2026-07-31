"""Serialisable domain model of a game.

Every model implements ``to_dict``/``from_dict`` so that a full game can be
persisted or sent to the frontend without any additional mapping layer.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

from ti.hexmap import Hex
from ti.units import UNIT_TYPES, UnitType, get_unit_type

_uid_counter = itertools.count(1)


def next_uid(prefix: str = "u") -> str:
    return f"{prefix}{next(_uid_counter)}"


@dataclass
class Unit:
    uid: str
    type_name: str
    owner: str

    @property
    def unit_type(self) -> UnitType:
        return get_unit_type(self.type_name)

    @property
    def combat(self) -> int:
        return self.unit_type.combat

    @property
    def move(self) -> int:
        return self.unit_type.move

    @property
    def capacity(self) -> int:
        return self.unit_type.capacity

    @property
    def is_ship(self) -> bool:
        return self.unit_type.ship

    def to_dict(self) -> dict:
        return {
            "uid": self.uid,
            "type": self.type_name,
            "owner": self.owner,
            "combat": self.combat,
            "move": self.move,
            "capacity": self.capacity,
        }

    @staticmethod
    def from_dict(data: dict) -> "Unit":
        return Unit(
            uid=data["uid"],
            type_name=data.get("type") or data["type_name"],
            owner=data["owner"],
        )

    @staticmethod
    def create(type_name: str, owner: str) -> "Unit":
        if type_name not in UNIT_TYPES:
            raise ValueError(f"Unknown unit type: {type_name}")
        return Unit(next_uid(f"{owner[:3].lower()}-"), type_name, owner)


@dataclass
class Planet:
    name: str
    resources: int = 0
    influence: int = 0
    controller: Optional[str] = None
    home: bool = False

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "resources": self.resources,
            "influence": self.influence,
            "controller": self.controller,
            "home": self.home,
        }

    @staticmethod
    def from_dict(data: dict) -> "Planet":
        return Planet(
            name=data["name"],
            resources=data.get("resources", 0),
            influence=data.get("influence", 0),
            controller=data.get("controller"),
            home=data.get("home", False),
        )


@dataclass
class System:
    id: str
    hex: Hex
    planets: List[Planet] = field(default_factory=list)
    ships: Dict[str, List[Unit]] = field(default_factory=dict)
    anomaly: Optional[str] = None

    @property
    def name(self) -> str:
        return self.planets[0].name if self.planets else self.id

    def units_of(self, player_name: str) -> List[Unit]:
        return self.ships.get(player_name, [])

    def add_units(self, player_name: str, units: Iterable[Unit]) -> None:
        self.ships.setdefault(player_name, []).extend(units)

    def remove_units(self, player_name: str, uids: Iterable[str]) -> List[Unit]:
        uid_set = set(uids)
        remaining, removed = [], []
        for unit in self.ships.get(player_name, []):
            (removed if unit.uid in uid_set else remaining).append(unit)
        self.ships[player_name] = remaining
        return removed

    def occupants(self) -> List[str]:
        return [name for name, units in self.ships.items() if units]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "hex": self.hex.to_dict(),
            "anomaly": self.anomaly,
            "planets": [p.to_dict() for p in self.planets],
            "ships": {
                name: [u.to_dict() for u in units]
                for name, units in self.ships.items()
            },
        }

    @staticmethod
    def from_dict(data: dict) -> "System":
        return System(
            id=data["id"],
            hex=Hex.from_dict(data["hex"]),
            planets=[Planet.from_dict(p) for p in data.get("planets", [])],
            ships={
                name: [Unit.from_dict(u) for u in units]
                for name, units in (data.get("ships") or {}).items()
            },
            anomaly=data.get("anomaly"),
        )


@dataclass
class Player:
    name: str
    faction: str = "Federation"
    color: str = "#3498db"
    resources: int = 3
    influence: int = 1
    vp: int = 0
    strategy_card: Optional[int] = None
    passed: bool = False

    def to_dict(self, board: Optional["Board"] = None) -> dict:
        data = {
            "name": self.name,
            "faction": self.faction,
            "color": self.color,
            "resources": self.resources,
            "influence": self.influence,
            "vp": self.vp,
            "strategy_card": self.strategy_card,
            "passed": self.passed,
        }
        if board is not None:
            data["planets"] = [p.name for p in board.planets_of(self.name)]
            data["ships"] = [u.to_dict() for u in board.units_of(self.name)]
        return data

    @staticmethod
    def from_dict(data: dict) -> "Player":
        return Player(
            name=data["name"],
            faction=data.get("faction", "Federation"),
            color=data.get("color", "#3498db"),
            resources=data.get("resources", 3),
            influence=data.get("influence", 1),
            vp=data.get("vp", 0),
            strategy_card=data.get("strategy_card"),
            passed=data.get("passed", False),
        )


@dataclass
class Board:
    systems: List[System] = field(default_factory=list)

    def get(self, system_id: str) -> Optional[System]:
        for system in self.systems:
            if system.id == system_id:
                return system
        return None

    def require(self, system_id: str) -> System:
        system = self.get(system_id)
        if system is None:
            raise KeyError(f"Unknown system: {system_id}")
        return system

    def at(self, hex_: Hex) -> Optional[System]:
        for system in self.systems:
            if system.hex == hex_:
                return system
        return None

    def distance(self, src_id: str, dst_id: str) -> int:
        return self.require(src_id).hex.distance(self.require(dst_id).hex)

    def neighbors(self, system_id: str) -> List[System]:
        system = self.require(system_id)
        found = [self.at(h) for h in system.hex.neighbors()]
        return [s for s in found if s is not None]

    def planets_of(self, player_name: str) -> List[Planet]:
        return [
            planet
            for system in self.systems
            for planet in system.planets
            if planet.controller == player_name
        ]

    def units_of(self, player_name: str) -> List[Unit]:
        return [
            unit for system in self.systems for unit in system.units_of(player_name)
        ]

    def home_system(self, player_name: str) -> Optional[System]:
        for system in self.systems:
            if any(p.home and p.controller == player_name for p in system.planets):
                return system
        return None

    def to_dict(self) -> List[dict]:
        return [s.to_dict() for s in self.systems]

    @staticmethod
    def from_dict(data: Iterable[dict]) -> "Board":
        return Board([System.from_dict(s) for s in data])
