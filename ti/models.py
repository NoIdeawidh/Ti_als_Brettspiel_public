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

DEFAULT_FLEET_SUPPLY = 4
"""Non-fighter ships a player may keep in a single system."""


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

    @property
    def counts_against_fleet(self) -> bool:
        """Fighters ride along with the fleet and need no supply of their own."""
        return self.is_ship and self.unit_type.base_name != "Fighter"

    def to_dict(self) -> dict:
        return {
            "uid": self.uid,
            "type": self.type_name,
            "owner": self.owner,
            "combat": self.combat,
            "move": self.move,
            "capacity": self.capacity,
            "ship": self.is_ship,
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
    ground_forces: List[Unit] = field(default_factory=list)
    """Units stationed on the planet; their owner defends against invasions."""
    structures: List[Unit] = field(default_factory=list)
    """Immobile buildings (Space Dock, PDS) owned by the planet controller."""

    def garrison_of(self, owner: Optional[str]) -> List[Unit]:
        return [u for u in self.ground_forces if u.owner == owner]

    def structures_of(self, owner: Optional[str]) -> List[Unit]:
        return [u for u in self.structures if u.owner == owner]

    def defender(self) -> Optional[str]:
        return self.ground_forces[0].owner if self.ground_forces else None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "resources": self.resources,
            "influence": self.influence,
            "controller": self.controller,
            "home": self.home,
            "ground_forces": [u.to_dict() for u in self.ground_forces],
            "structures": [u.to_dict() for u in self.structures],
        }

    @staticmethod
    def from_dict(data: dict) -> "Planet":
        return Planet(
            name=data["name"],
            resources=data.get("resources", 0),
            influence=data.get("influence", 0),
            controller=data.get("controller"),
            home=data.get("home", False),
            ground_forces=[Unit.from_dict(u) for u in data.get("ground_forces", [])],
            structures=[Unit.from_dict(u) for u in data.get("structures", [])],
        )


@dataclass
class System:
    id: str
    hex: Hex
    planets: List[Planet] = field(default_factory=list)
    ships: Dict[str, List[Unit]] = field(default_factory=dict)
    anomaly: Optional[str] = None
    wormhole: Optional[str] = None
    """Systems sharing a wormhole are adjacent regardless of their distance."""

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
            "wormhole": self.wormhole,
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
            wormhole=data.get("wormhole"),
        )


@dataclass
class Player:
    name: str
    faction: str = "Federation"
    color: str = "#3498db"
    resources: int = 3
    influence: int = 1
    vp: int = 0
    command_tokens: int = 3
    """Each activation (move/produce) costs one token; refreshed every round."""
    strategy_card: Optional[int] = None
    passed: bool = False
    technologies: List[str] = field(default_factory=list)
    """Researched technology ids; unit upgrades are derived from them."""
    action_cards: List[str] = field(default_factory=list)
    """Action cards in hand; one is drawn per status phase."""
    free_research: int = 0
    """Technologies that may be researched without paying resources."""
    is_bot: bool = False
    """Bots are played by :mod:`ti.bot` and follow the same rules."""
    fleet_supply: int = DEFAULT_FLEET_SUPPLY
    """Maximum number of non-fighter ships the player may keep in one system."""
    trade_goods: int = 0
    """Universal currency: spent after resources and tradeable between players."""
    secret_objectives: List[str] = field(default_factory=list)
    """Secret objectives in hand; they score only for this player."""
    scored_secrets: List[str] = field(default_factory=list)

    @property
    def budget(self) -> int:
        """Everything the player can spend on units, structures and research."""
        return self.resources + self.trade_goods

    def spend(self, amount: int) -> None:
        """Pay from resources first, trade goods cover the rest."""
        from_resources = min(self.resources, amount)
        self.resources -= from_resources
        self.trade_goods -= amount - from_resources

    def to_dict(self, board: Optional["Board"] = None) -> dict:
        data = {
            "name": self.name,
            "faction": self.faction,
            "color": self.color,
            "resources": self.resources,
            "influence": self.influence,
            "vp": self.vp,
            "command_tokens": self.command_tokens,
            "strategy_card": self.strategy_card,
            "passed": self.passed,
            "technologies": list(self.technologies),
            "trade_goods": self.trade_goods,
            "action_cards": list(self.action_cards),
            "free_research": self.free_research,
            "fleet_supply": self.fleet_supply,
            "is_bot": self.is_bot,
            "secret_objectives": list(self.secret_objectives),
            "scored_secrets": list(self.scored_secrets),
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
            command_tokens=data.get("command_tokens", 3),
            strategy_card=data.get("strategy_card"),
            passed=data.get("passed", False),
            technologies=list(data.get("technologies", [])),
            trade_goods=data.get("trade_goods", 0),
            action_cards=list(data.get("action_cards", [])),
            free_research=data.get("free_research", 0),
            fleet_supply=data.get("fleet_supply", DEFAULT_FLEET_SUPPLY),
            is_bot=data.get("is_bot", False),
            secret_objectives=list(data.get("secret_objectives", [])),
            scored_secrets=list(data.get("scored_secrets", [])),
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
        """Jumps between two systems; wormholes count as a single jump."""
        src, dst = self.require(src_id), self.require(dst_id)
        if not any(s.wormhole for s in self.systems):
            return src.hex.distance(dst.hex)

        seen = {src.id}
        frontier = [src]
        steps = 0
        while frontier:
            if any(system.id == dst.id for system in frontier):
                return steps
            steps += 1
            next_frontier: List[System] = []
            for system in frontier:
                for neighbour in self.neighbors(system.id):
                    if neighbour.id not in seen:
                        seen.add(neighbour.id)
                        next_frontier.append(neighbour)
            frontier = next_frontier
        return src.hex.distance(dst.hex)

    def neighbors(self, system_id: str) -> List[System]:
        system = self.require(system_id)
        found = [self.at(h) for h in system.hex.neighbors()]
        neighbours = [s for s in found if s is not None]
        if system.wormhole:
            neighbours.extend(
                s
                for s in self.systems
                if s.id != system.id and s.wormhole == system.wormhole
            )
        return neighbours

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
