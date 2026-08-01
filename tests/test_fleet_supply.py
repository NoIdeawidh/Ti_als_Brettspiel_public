import pytest

from ti.game import Game
from ti.hexmap import Hex
from ti.models import DEFAULT_FLEET_SUPPLY, Board, System, Unit


def system_with(player: str, count: int, unit: str = "Cruiser") -> System:
    system = System(id="a", hex=Hex(0, 0))
    system.add_units(player, [Unit.create(unit, player) for _ in range(count)])
    return system


def test_move_is_blocked_when_the_fleet_supply_is_full():
    src = system_with("Alice", 2)
    dst = System(id="b", hex=Hex(1, 0))
    dst.add_units("Alice", [Unit.create("Cruiser", "Alice") for _ in range(3)])
    game = Game([], Board([src, dst]), seed=1)

    result = game.engine.move("Alice", "a", "b", fleet_supply=4)

    assert not result.ok
    assert "Fleet supply 4" in result.message


def test_fighters_do_not_count_against_the_supply():
    src = system_with("Alice", 3, unit="Fighter")
    src.add_units("Alice", [Unit.create("Carrier", "Alice")])
    dst = System(id="b", hex=Hex(1, 0))
    dst.add_units("Alice", [Unit.create("Cruiser", "Alice") for _ in range(3)])
    game = Game([], Board([src, dst]), seed=1)

    assert game.engine.move("Alice", "a", "b", fleet_supply=4).ok


def test_production_respects_the_supply():
    game = Game.create(["Alice", "Bob"], seed=7)
    alice = game.get_player("Alice")
    alice.resources = 20
    alice.fleet_supply = 2
    game.apply_action("Alice", {"type": "select_strategy", "card_id": 1})
    game.apply_action("Bob", {"type": "select_strategy", "card_id": 6})
    home = game.board.home_system("Alice")

    result = game.apply_action(
        "Alice",
        {"type": "produce", "system": home.id, "units": ["Cruiser"]},
    )

    assert not result.ok
    assert "Fleet supply" in result.message


def test_warfare_raises_the_fleet_supply():
    game = Game.create(["Alice", "Bob"], seed=7)
    game.apply_action("Alice", {"type": "select_strategy", "card_id": 6})
    game.apply_action("Bob", {"type": "select_strategy", "card_id": 1})
    game.apply_action("Bob", {"type": "end_turn"})

    game.apply_action("Alice", {"type": "play_strategy"})

    assert game.get_player("Alice").fleet_supply == DEFAULT_FLEET_SUPPLY + 1


def test_fleet_supply_survives_serialisation():
    game = Game.create(["Alice", "Bob"], seed=7)
    game.get_player("Alice").fleet_supply = 6

    restored = Game.from_dict(game.to_dict())
    assert restored.get_player("Alice").fleet_supply == 6
