"""Galaxy and player setup."""

from __future__ import annotations

import random
from typing import Dict, List, Optional, Sequence, Tuple

from ti.anomalies import ANOMALY_LIST, WORMHOLES
from ti.factions import DEFAULT_FACTION, get_faction
from ti.hexmap import Hex, home_positions, ring
from ti.models import Board, Planet, Player, System, Unit
from ti.units import DEFAULT_START_UNITS

DEFAULT_COLORS = [
    "#3498db",
    "#e74c3c",
    "#2ecc71",
    "#f1c40f",
    "#9b59b6",
    "#1abc9c",
]

MECATOL_ID = "s_mec"
GALAXY_RADIUS = 3
NEUTRAL = "Neutral"
HOME_GROUND_FORCES = 2
MECATOL_GARRISON = 3
START_TRANSPORTED_INFANTRY = 2
ANOMALY_CHANCE = 0.2
"""Share of empty systems that receive an anomaly."""


def _system_id(hex_: Hex) -> str:
    return f"s_{hex_.q}_{hex_.r}".replace("-", "m")


def build_players(raw_players: Sequence[object], factions: Optional[Dict[str, str]] = None) -> List[Player]:
    factions = factions or {}
    players: List[Player] = []
    for index, raw in enumerate(raw_players):
        if isinstance(raw, dict):
            name = raw["name"]
            faction = raw.get("faction") or factions.get(name) or DEFAULT_FACTION
            color = raw.get("color") or DEFAULT_COLORS[index % len(DEFAULT_COLORS)]
        else:
            name = str(raw)
            faction = factions.get(name, DEFAULT_FACTION)
            color = DEFAULT_COLORS[index % len(DEFAULT_COLORS)]
        players.append(_apply_faction(Player(name=name, faction=faction, color=color)))
    _reject_duplicates([p.name for p in players])
    return players


def _apply_faction(player: Player) -> Player:
    """Add the faction's starting bonus to a freshly created player."""
    faction = get_faction(player.faction)
    if faction is None:
        return player
    player.resources += faction.resources
    player.influence += faction.influence
    player.trade_goods += faction.trade_goods
    player.command_tokens += faction.command_tokens
    player.technologies.extend(faction.technologies)
    return player


def _reject_duplicates(names: Sequence[str]) -> None:
    if len(set(names)) != len(names):
        raise ValueError("Player names must be unique")


def build_board(players: Sequence[Player], rng: random.Random) -> Board:
    """Create a hex galaxy: Mecatol Rex in the centre, home systems outside."""
    systems: List[System] = [
        System(
            id=MECATOL_ID,
            hex=Hex(0, 0),
            planets=[_mecatol_rex()],
        )
    ]

    homes = home_positions(len(players), radius=GALAXY_RADIUS)
    home_hexes = set(homes)
    for player, hex_ in zip(players, homes):
        home_planet = Planet(
            f"{player.name} Prime",
            resources=2,
            influence=1,
            controller=player.name,
            home=True,
        )
        home_planet.ground_forces = [
            Unit.create("Infantry", player.name) for _ in range(HOME_GROUND_FORCES)
        ]
        system = System(id=_system_id(hex_), hex=hex_, planets=[home_planet])
        system.add_units(
            player.name,
            [Unit.create(name, player.name) for name in DEFAULT_START_UNITS]
            + [
                Unit.create("Infantry", player.name)
                for _ in range(START_TRANSPORTED_INFANTRY)
            ]
            + [Unit.create(name, player.name) for name in _faction_units(player)],
        )
        systems.append(system)

    systems.extend(_neutral_systems(home_hexes, rng))
    return Board(systems)


def _faction_units(player: Player) -> Tuple[str, ...]:
    faction = get_faction(player.faction)
    return faction.units if faction else ()


def _neutral_systems(home_hexes, rng: random.Random) -> List[System]:
    """Fill the galaxy with neutral planet and empty systems."""
    systems: List[System] = []
    index = 0
    for radius in range(1, GALAXY_RADIUS + 1):
        for hex_ in ring(radius):
            if hex_ in home_hexes:
                continue
            index += 1
            if rng.random() < 0.55:
                resources, influence = rng.choice([(1, 1), (2, 0), (0, 2), (3, 1)])
                planet = Planet(
                    f"Planet {index:02d}", resources=resources, influence=influence
                )
                planet.ground_forces = [
                    Unit.create("Infantry", NEUTRAL)
                    for _ in range(rng.randint(0, 2))
                ]
                planets = [planet]
            else:
                planets = []
            system = System(id=_system_id(hex_), hex=hex_, planets=planets)
            if not planets and rng.random() < ANOMALY_CHANCE:
                system.anomaly = rng.choice(ANOMALY_LIST).id
            systems.append(system)
    _place_wormholes(systems, rng)
    return systems


def _place_wormholes(systems: List[System], rng: random.Random) -> None:
    """Give each wormhole type a pair of otherwise unremarkable systems."""
    candidates = [s for s in systems if not s.anomaly and not s.planets]
    for wormhole in WORMHOLES:
        if len(candidates) < 2:
            return
        for system in rng.sample(candidates, 2):
            system.wormhole = wormhole
            candidates.remove(system)


def _mecatol_rex() -> Planet:
    planet = Planet("Mecatol Rex", resources=1, influence=6)
    planet.ground_forces = [
        Unit.create("Infantry", NEUTRAL) for _ in range(MECATOL_GARRISON)
    ]
    return planet


def new_game_state(
    raw_players: Sequence[object],
    factions: Optional[Dict[str, str]] = None,
    seed: Optional[int] = None,
) -> Tuple[List[Player], Board, int, random.Random]:
    seed = random.randint(0, 999999) if seed is None else int(seed)
    rng = random.Random(seed)
    players = build_players(raw_players, factions)
    if not players:
        raise ValueError("At least one player is required")
    board = build_board(players, rng)
    return players, board, seed, rng
