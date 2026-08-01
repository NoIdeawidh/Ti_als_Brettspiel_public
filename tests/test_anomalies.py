import pytest

from ti.anomalies import (
    ASTEROID_FIELD,
    GRAVITY_RIFT,
    NEBULA,
    SUPERNOVA,
    WORMHOLE_ALPHA,
)
from ti.game import Game
from ti.hexmap import Hex
from ti.models import Board, System, Unit


def board_with(*systems: System) -> Board:
    return Board(list(systems))


def fleet(system: System, player: str, count: int = 1) -> None:
    system.add_units(player, [Unit.create("Cruiser", player) for _ in range(count)])


@pytest.fixture
def game():
    game = Game.create(["Alice", "Bob"], seed=3)
    game.apply_action("Alice", {"type": "select_strategy", "card_id": 1})
    game.apply_action("Bob", {"type": "select_strategy", "card_id": 6})
    return game


def test_supernova_cannot_be_entered(game):
    src = game.board.home_system("Alice")
    dst = next(s for s in game.board.systems if s.hex.distance(src.hex) == 1)
    dst.anomaly = SUPERNOVA

    result = game.apply_action("Alice", {"type": "move", "from": src.id, "to": dst.id})

    assert not result.ok
    assert "Supernova" in result.message


def test_asteroid_field_requires_the_matching_technology(game):
    alice = game.get_player("Alice")
    src = game.board.home_system("Alice")
    dst = next(s for s in game.board.systems if s.hex.distance(src.hex) == 1)
    dst.anomaly = ASTEROID_FIELD

    blocked = game.apply_action(
        "Alice", {"type": "move", "from": src.id, "to": dst.id}
    )
    assert not blocked.ok

    alice.technologies.append("antimass_deflectors")
    ship = next(u for u in src.units_of("Alice") if u.is_ship)
    assert game.apply_action(
        "Alice",
        {"type": "move", "from": src.id, "to": dst.id, "units": [ship.uid]},
    ).ok


def test_gravity_rift_extends_the_movement_range():
    src = System(id="a", hex=Hex(0, 0), anomaly=GRAVITY_RIFT)
    dst = System(id="b", hex=Hex(3, 0))
    board = board_with(src, dst, System(id="c", hex=Hex(1, 0)))
    fleet(src, "Alice")
    game = Game([], board, seed=1)

    assert game.engine.move("Alice", "a", "b").ok


def test_wormholes_make_distant_systems_adjacent():
    src = System(id="a", hex=Hex(0, 0), wormhole=WORMHOLE_ALPHA)
    dst = System(id="b", hex=Hex(3, 0), wormhole=WORMHOLE_ALPHA)
    board = board_with(src, dst)

    assert board.distance("a", "b") == 1
    fleet(src, "Alice")
    game = Game([], board, seed=1)
    assert game.engine.move("Alice", "a", "b").ok


def test_nebula_helps_the_defender():
    system = System(id="a", hex=Hex(0, 0), anomaly=NEBULA)
    board = board_with(system)
    game = Game([], board, seed=1)
    fleet(system, "Bob")

    assert game.engine._combat_bonuses_in(system, "Bob") == {"Bob": 1}


def test_map_features_survive_serialisation(game):
    system = game.board.systems[1]
    system.anomaly = NEBULA
    system.wormhole = WORMHOLE_ALPHA

    restored = Game.from_dict(game.to_dict())
    restored_system = restored.board.require(system.id)
    assert (restored_system.anomaly, restored_system.wormhole) == (
        NEBULA,
        WORMHOLE_ALPHA,
    )
