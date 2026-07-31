import pytest

from ti.game import Game
from ti.tech import TECHNOLOGIES, missing_prerequisites, upgrades_of
from ti.units import get_unit_type


@pytest.fixture
def game():
    game = Game.create(["Alice", "Bob"], seed=13)
    for index in range(len(game.players)):
        game.apply_action(
            game.turns.current_player, {"type": "select_strategy", "card_id": index + 1}
        )
    return game


def current(game):
    return game.get_player(game.turns.current_player)


def test_prerequisites_block_research(game):
    player = current(game)
    player.resources = 20
    result = game.apply_action(player.name, {"type": "research", "technology": "cruiser_ii"})
    assert not result.ok
    assert "prerequisites" in result.message

    assert missing_prerequisites(TECHNOLOGIES["cruiser_ii"], ["plasma_scoring"])


def test_research_costs_resources_and_a_token(game):
    player = current(game)
    player.resources = 5
    tokens = player.command_tokens
    result = game.apply_action(
        player.name, {"type": "research", "technology": "plasma_scoring"}
    )
    assert result.ok, result.message
    assert player.resources == 3
    assert player.command_tokens == tokens - 1
    assert player.technologies == ["plasma_scoring"]

    again = game.apply_action(
        player.name, {"type": "research", "technology": "plasma_scoring"}
    )
    assert not again.ok


def test_unit_upgrade_replaces_existing_and_new_units(game):
    player = current(game)
    player.resources = 20
    home = game.board.home_system(player.name)
    assert game.apply_action(
        player.name, {"type": "research", "technology": "antimass_deflectors"}
    ).ok
    result = game.apply_action(
        player.name, {"type": "research", "technology": "carrier_ii"}
    )
    assert result.ok, result.message
    assert result.data["upgraded_units"] == 1

    carriers = [u for u in home.units_of(player.name) if u.type_name == "Carrier II"]
    assert carriers and carriers[0].capacity == 6

    assert game.apply_action(
        player.name,
        {"type": "produce", "system": home.id, "units": ["Carrier"]},
    ).ok
    assert len([u for u in home.units_of(player.name) if u.type_name == "Carrier II"]) == 2


def test_structure_upgrade_applies_to_build_action(game):
    player = current(game)
    player.resources = 20
    home = game.board.home_system(player.name)
    planet = home.planets[0]
    assert game.apply_action(
        player.name, {"type": "research", "technology": "sarween_tools"}
    ).ok
    assert game.apply_action(
        player.name, {"type": "research", "technology": "space_dock_ii"}
    ).ok
    assert game.apply_action(
        player.name,
        {
            "type": "build",
            "system": home.id,
            "planet": planet.name,
            "structure": "Space Dock",
        },
    ).ok
    assert [u.type_name for u in planet.structures] == ["Space Dock II"]
    assert game.engine.production_capacity(player.name, home) == 7

    duplicate = game.apply_action(
        player.name,
        {
            "type": "build",
            "system": home.id,
            "planet": planet.name,
            "structure": "Space Dock",
        },
    )
    assert not duplicate.ok


def test_technologies_survive_serialisation(game):
    player = current(game)
    player.resources = 20
    game.apply_action(player.name, {"type": "research", "technology": "neural_motivator"})
    restored = Game.from_dict(game.to_dict())
    assert restored.get_player(player.name).technologies == ["neural_motivator"]
    assert upgrades_of(["carrier_ii"]) == {"Carrier": "Carrier II"}
    assert get_unit_type("Carrier II").base_name == "Carrier"


def test_upgraded_units_require_research(game):
    player = current(game)
    player.resources = 20
    home = game.board.home_system(player.name)
    result = game.apply_action(
        player.name, {"type": "produce", "system": home.id, "units": ["Cruiser II"]}
    )
    assert not result.ok
    assert "Not researched" in result.message
