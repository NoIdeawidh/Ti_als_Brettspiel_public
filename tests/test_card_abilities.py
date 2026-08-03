import pytest

from ti.game import Game


@pytest.fixture
def game():
    game = Game.create(["Alice", "Bob"], seed=11)
    game.apply_action("Alice", {"type": "select_strategy", "card_id": 3})
    game.apply_action("Bob", {"type": "select_strategy", "card_id": 7})
    return game


def test_politics_draws_action_cards(game):
    alice = game.get_player("Alice")

    game.apply_action("Alice", {"type": "play_strategy"})

    assert len(alice.action_cards) == 2


def test_technology_grants_free_research(game):
    bob = game.get_player("Bob")
    game.apply_action("Alice", {"type": "end_turn"})

    game.apply_action("Bob", {"type": "play_strategy"})
    assert bob.free_research == 2

    resources = bob.resources
    assert game.apply_action(
        "Bob", {"type": "research", "technology": "antimass_deflectors"}
    ).ok
    assert bob.resources == resources
    assert bob.free_research == 1


def test_free_research_is_consumed_once(game):
    alice = game.get_player("Alice")
    alice.free_research = 1
    alice.resources = 10

    game.apply_action("Alice", {"type": "research", "technology": "antimass_deflectors"})
    game.apply_action("Alice", {"type": "research", "technology": "neural_motivator"})

    assert alice.free_research == 0
    assert alice.resources < 10


def test_secondary_of_technology_is_a_free_research(game):
    alice = game.get_player("Alice")
    game.apply_action("Alice", {"type": "end_turn"})
    game.apply_action("Bob", {"type": "play_strategy"})
    game.apply_action("Bob", {"type": "end_turn"})

    assert game.apply_action("Alice", {"type": "follow", "card_id": 7}).ok
    assert alice.free_research == 1


def test_free_research_survives_serialisation(game):
    game.get_player("Alice").free_research = 2

    restored = Game.from_dict(game.to_dict())
    assert restored.get_player("Alice").free_research == 2


def test_construction_builds_without_resources(game):
    alice = game.get_player("Alice")
    alice.free_structures = 1
    alice.resources = 0
    alice.trade_goods = 0
    planet = game.board.planets_of("Alice")[0]
    system = next(s for s in game.board.systems if planet in s.planets)

    result = game.apply_action(
        "Alice",
        {
            "type": "build",
            "system": system.id,
            "planet": planet.name,
            "structure": "Space Dock",
        },
    )

    assert result.ok, result.message
    assert alice.free_structures == 0
    assert alice.resources == 0
    assert alice.trade_goods == 0


def test_construction_grants_free_structures():
    game = Game.create(["Alice", "Bob"], seed=11)
    game.apply_action("Alice", {"type": "select_strategy", "card_id": 4})
    game.apply_action("Bob", {"type": "select_strategy", "card_id": 7})
    alice = game.get_player("Alice")

    assert game.apply_action("Alice", {"type": "play_strategy"}).ok
    assert alice.free_structures == 2

    restored = Game.from_dict(game.to_dict())
    assert restored.get_player("Alice").free_structures == 2
