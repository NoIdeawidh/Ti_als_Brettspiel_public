"""Galaxy and player setup."""

from __future__ import annotations

import random
from typing import Dict, List, Optional, Sequence, Tuple

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


def _system_id(hex_: Hex) -> str:
    return f"s_{hex_.q}_{hex_.r}".replace("-", "m")


def build_players(raw_players: Sequence[object], factions: Optional[Dict[str, str]] = None) -> List[Player]:
    factions = factions or {}
    players: List[Player] = []
    for index, raw in enumerate(raw_players):
        if isinstance(raw, dict):
            name = raw["name"]
            faction = raw.get("faction") or factions.get(name) or "Federation"
            color = raw.get("color") or DEFAULT_COLORS[index % len(DEFAULT_COLORS)]
        else:
            name = str(raw)
            faction = factions.get(name, "Federation")
            color = DEFAULT_COLORS[index % len(DEFAULT_COLORS)]
        players.append(Player(name=name, faction=faction, color=color))
    _reject_duplicates([p.name for p in players])
    return players


def _reject_duplicates(names: Sequence[str]) -> None:
    if len(set(names)) != len(names):
        raise ValueError("Player names must be unique")


def build_board(players: Sequence[Player], rng: random.Random) -> Board:
    """Create a hex galaxy: Mecatol Rex in the centre, home systems outside."""
    systems: List[System] = [
        System(
            id=MECATOL_ID,
            hex=Hex(0, 0),
            planets=[Planet("Mecatol Rex", resources=1, influence=6)],
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
        system = System(id=_system_id(hex_), hex=hex_, planets=[home_planet])
        system.add_units(
            player.name,
            [Unit.create(name, player.name) for name in DEFAULT_START_UNITS],
        )
        systems.append(system)

    systems.extend(_neutral_systems(home_hexes, rng))
    return Board(systems)


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
                planets = [
                    Planet(f"Planet {index:02d}", resources=resources, influence=influence)
                ]
            else:
                planets = []
            systems.append(System(id=_system_id(hex_), hex=hex_, planets=planets))
    return systems


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
