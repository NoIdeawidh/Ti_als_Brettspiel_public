import random

import pytest

from ti.engine import Engine
from ti.game import Game
from ti.hexmap import Hex
from ti.models import Board, Planet, System, Unit


@pytest.fixture
def board():
    planet = Planet("Test", controller="Alice")
    system = System(id="s_test", hex=Hex(0, 0), planets=[planet])
    return Board([system])


def test_space_dock_raises_production_capacity(board):
    engine = Engine(board, random.Random(1))
    system = board.require("s_test")
    assert engine.production_capacity("Alice", system) == 2

    result = engine.build("Alice", "s_test", "Test", "Space Dock", budget=10)
    assert result.ok, result.message
    assert engine.production_capacity("Alice", system) == 5


def test_structures_cannot_be_produced_or_duplicated(board):
    engine = Engine(board, random.Random(1))
    assert engine.build("Alice", "s_test", "Test", "PDS", budget=10).ok
    duplicate = engine.build("Alice", "s_test", "Test", "PDS", budget=10)
    assert not duplicate.ok
    produced = engine.produce("Alice", "s_test", ["PDS"], budget=10)
    assert not produced.ok
    assert "build" in produced.message


def test_build_requires_control_and_resources(board):
    engine = Engine(board, random.Random(1))
    board.require("s_test").planets[0].controller = "Bob"
    assert not engine.build("Alice", "s_test", "Test", "PDS", budget=10).ok
    board.require("s_test").planets[0].controller = "Alice"
    assert not engine.build("Alice", "s_test", "Test", "PDS", budget=1).ok


def test_pds_fires_at_the_landing_party(board):
    system = board.require("s_test")
    planet = system.planets[0]
    planet.controller = "Bob"
    planet.structures = [Unit.create("PDS", "Bob") for _ in range(4)]
    planet.ground_forces = [Unit.create("Infantry", "Bob")]
    system.add_units("Alice", [Unit.create("Infantry", "Alice")])

    engine = Engine(board, random.Random(2))
    result = engine.invade("Alice", "s_test", "Test")
    assert result.ok
    assert result.data["planetary_defence"]["hits"] >= 0
    assert not result.data["captured"] or not planet.structures


def test_build_action_costs_resources_and_a_token():
    game = Game.create(["Alice", "Bob"], seed=5)
    for index in range(len(game.players)):
        game.apply_action(
            game.turns.current_player, {"type": "select_strategy", "card_id": index + 1}
        )
    name = game.turns.current_player
    player = game.get_player(name)
    player.resources = 5
    tokens = player.command_tokens
    home = game.board.home_system(name)

    result = game.apply_action(
        name,
        {
            "type": "build",
            "system": home.id,
            "planet": home.planets[0].name,
            "structure": "Space Dock",
        },
    )
    assert result.ok, result.message
    assert player.resources == 1
    assert player.command_tokens == tokens - 1
