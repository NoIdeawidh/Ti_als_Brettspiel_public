import pytest

from ti.cards import get_card
from ti.game import Game
from ti.phases import Phase


@pytest.fixture
def game():
    game = Game.create(["Alice", "Bob"], seed=3)
    game.apply_action("Alice", {"type": "select_strategy", "card_id": 1})
    game.apply_action("Bob", {"type": "select_strategy", "card_id": 4})
    return game


def test_selection_alone_grants_nothing(game):
    alice = game.get_player("Alice")
    assert alice.strategy_card == 1
    assert (alice.resources, alice.influence, alice.command_tokens) == (3, 1, 3)
    assert game.played_cards == []


def test_primary_ability_is_used_by_the_holder(game):
    alice = game.get_player("Alice")
    leadership = get_card(1)

    result = game.apply_action("Alice", {"type": "play_strategy"})

    assert result.ok
    assert alice.influence == 1 + leadership.primary.influence
    assert alice.command_tokens == 3 + leadership.primary.tokens
    assert game.played_cards == [1]
    assert not game.apply_action("Alice", {"type": "play_strategy"}).ok


def test_secondary_ability_costs_a_token_and_works_once(game):
    bob = game.get_player("Bob")
    game.apply_action("Alice", {"type": "play_strategy"})
    game.apply_action("Alice", {"type": "end_turn"})
    tokens = bob.command_tokens

    assert game.apply_action("Bob", {"type": "follow", "card_id": 1}).ok
    assert bob.command_tokens == tokens - 1 + get_card(1).secondary.tokens
    assert game.followers[1] == ["Bob"]
    assert not game.apply_action("Bob", {"type": "follow", "card_id": 1}).ok


def test_following_requires_a_played_card_and_a_foreign_card(game):
    game.apply_action("Alice", {"type": "play_strategy"})

    assert not game.apply_action("Alice", {"type": "follow", "card_id": 1}).ok
    assert not game.apply_action("Alice", {"type": "follow", "card_id": 4}).ok
    assert not game.apply_action("Alice", {"type": "follow", "card_id": 99}).ok


def test_played_cards_reset_each_round(game):
    game.apply_action("Alice", {"type": "play_strategy"})
    while game.turns.phase == Phase.ACTION:
        game.apply_action(game.turns.current_player, {"type": "pass"})

    assert game.turns.phase == Phase.STRATEGY
    assert game.played_cards == []
    assert game.followers == {}


def test_play_state_survives_serialisation(game):
    game.apply_action("Alice", {"type": "play_strategy"})
    game.apply_action("Alice", {"type": "end_turn"})
    game.apply_action("Bob", {"type": "follow", "card_id": 1})

    restored = Game.from_dict(game.to_dict())
    assert restored.played_cards == [1]
    assert restored.followers == {1: ["Bob"]}
