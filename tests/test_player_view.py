import pytest

from ti.game import Game
from server import create_app


@pytest.fixture
def game():
    game = Game.create(["Alice", "Bob"], seed=5)
    game.get_player("Bob").action_cards.append("war_funding")
    return game


def player_in(state: dict, name: str) -> dict:
    return next(p for p in state["players"] if p["name"] == name)


def test_view_keeps_own_hidden_information(game):
    state = game.view_for("Alice")
    alice = player_in(state, "Alice")

    assert alice["secret_objectives"] == game.get_player("Alice").secret_objectives
    assert "hidden_secret_objectives" not in alice


def test_view_hides_other_players_cards(game):
    bob = player_in(game.view_for("Alice"), "Bob")

    assert bob["secret_objectives"] == []
    assert bob["action_cards"] == []
    assert bob["hidden_secret_objectives"] == len(
        game.get_player("Bob").secret_objectives
    )
    assert bob["hidden_action_cards"] == 1


def test_view_replaces_face_down_decks_with_their_size(game):
    state = game.view_for("Alice")

    assert state["secret_deck"] == []
    assert state["secret_deck_size"] == len(game.secret_deck)
    assert state["action_deck_size"] == len(game.action_deck)


def test_full_state_is_unchanged(game):
    game.view_for("Alice")

    assert game.to_dict()["secret_deck"] == game.secret_deck


def test_state_endpoint_redacts_for_the_given_player(tmp_path, game):
    app = create_app(tmp_path)
    app.config["GAME_STORE"].add(game)
    client = app.test_client()

    response = client.get(f"/api/state?game_id={game.id}&player=Alice")

    assert player_in(response.get_json(), "Bob")["action_cards"] == []
