import pytest

from ti.action_cards import ACTION_CARD_LIST
from ti.game import Game
from ti.phases import Phase


@pytest.fixture
def game():
    game = Game.create(["Alice", "Bob"], seed=13)
    game.apply_action("Alice", {"type": "select_strategy", "card_id": 1})
    game.apply_action("Bob", {"type": "select_strategy", "card_id": 6})
    return game


def end_round(game):
    while game.turns.phase == Phase.ACTION:
        game.apply_action(game.turns.current_player, {"type": "pass"})


def test_every_player_draws_one_card_per_round(game):
    assert all(not p.action_cards for p in game.players)

    end_round(game)

    assert all(len(p.action_cards) == 1 for p in game.players)


def test_card_effect_is_applied_and_card_is_discarded(game):
    alice = game.get_player("Alice")
    alice.action_cards = ["industrial_initiative"]
    resources = alice.resources

    result = game.apply_action(
        "Alice", {"type": "play_action_card", "card": "industrial_initiative"}
    )

    assert result.ok
    assert alice.resources == resources + 2
    assert alice.action_cards == []
    assert game.action_discard == ["industrial_initiative"]


def test_targeted_card_needs_a_valid_target(game):
    alice, bob = game.players
    alice.action_cards = ["insubordination", "insubordination"]
    tokens = bob.command_tokens

    assert not game.apply_action(
        "Alice", {"type": "play_action_card", "card": "insubordination"}
    ).ok
    assert alice.action_cards == ["insubordination", "insubordination"]

    assert game.apply_action(
        "Alice",
        {"type": "play_action_card", "card": "insubordination", "target": "Bob"},
    ).ok
    assert bob.command_tokens == tokens - 1


def test_cards_not_in_hand_are_rejected(game):
    assert not game.apply_action(
        "Alice", {"type": "play_action_card", "card": "war_funding"}
    ).ok
    assert not game.apply_action(
        "Alice", {"type": "play_action_card", "card": "does_not_exist"}
    ).ok


def test_unexpected_action_allows_a_second_primary(game):
    alice = game.get_player("Alice")
    alice.action_cards = ["unexpected_action"]
    game.apply_action("Alice", {"type": "play_strategy"})

    game.apply_action(
        "Alice", {"type": "play_action_card", "card": "unexpected_action"}
    )

    assert game.played_cards == []
    assert game.apply_action("Alice", {"type": "play_strategy"}).ok


def test_deck_reshuffles_from_the_discard_pile(game):
    alice = game.get_player("Alice")
    game.action_deck = []
    game.action_discard = ["war_funding"]

    assert game.draw_action_card(alice) == "war_funding"
    assert game.action_discard == []
    assert game.draw_action_card(alice) is None


def test_hand_survives_serialisation(game):
    game.get_player("Alice").action_cards = ["war_funding"]

    restored = Game.from_dict(game.to_dict())
    assert restored.get_player("Alice").action_cards == ["war_funding"]
    assert len(restored.to_dict()["action_cards"]) == len(ACTION_CARD_LIST)
