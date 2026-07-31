import pytest

from ti.game import SECRETS_PER_PLAYER, Game
from ti.objectives import SECRET_DECK, get_objective
from ti.phases import Phase


@pytest.fixture
def game():
    game = Game.create(["Alice", "Bob"], seed=11)
    for index in range(len(game.players)):
        game.apply_action(
            game.turns.current_player, {"type": "select_strategy", "card_id": index + 1}
        )
    return game


def end_round(game):
    while game.turns.phase == Phase.ACTION:
        game.apply_action(game.turns.current_player, {"type": "pass"})


def test_every_player_starts_with_distinct_secrets(game):
    hands = [p.secret_objectives for p in game.players]
    assert all(len(hand) == SECRETS_PER_PLAYER for hand in hands)
    assert len(set(hands[0]) | set(hands[1])) == 2 * SECRETS_PER_PLAYER
    assert all(get_objective(oid) for hand in hands for oid in hand)


def test_secret_scores_once_and_is_replaced(game):
    alice = game.players[0]
    alice.secret_objectives = ["war_chest", "shadow_fleet"]
    alice.resources = 12
    before = alice.vp

    end_round(game)

    assert alice.scored_secrets == ["war_chest"]
    assert alice.vp == before + get_objective("war_chest").vp
    assert len(alice.secret_objectives) == SECRETS_PER_PLAYER
    assert "war_chest" not in alice.secret_objectives


def test_only_one_secret_per_status_phase(game):
    alice = game.players[0]
    alice.secret_objectives = ["war_chest", "tech_supremacy"]
    alice.resources = 12
    alice.technologies = ["a", "b", "c", "d"]
    game.secret_deck = []

    end_round(game)

    assert len(alice.scored_secrets) == 1
    assert alice.secret_objectives == ["tech_supremacy"]


def test_secrets_are_not_scored_by_other_players(game):
    alice, bob = game.players
    alice.secret_objectives = ["war_chest"]
    bob.secret_objectives = []
    bob.resources = 20
    game.secret_deck = []

    end_round(game)

    assert bob.scored_secrets == []
    assert alice.scored_secrets == []


def test_secrets_survive_serialisation(game):
    alice = game.players[0]
    alice.secret_objectives = ["fortress_world"]
    alice.scored_secrets = ["throne_claim"]

    restored = Game.from_dict(game.to_dict())
    player = restored.get_player("Alice")
    assert player.scored_secrets == ["throne_claim"]
    assert "fortress_world" in player.secret_objectives
    assert len(restored.to_dict()["secret_objectives"]) == len(SECRET_DECK)
