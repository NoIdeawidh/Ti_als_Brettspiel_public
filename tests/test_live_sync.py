import pytest

from server import create_app
from ti.game import Game


@pytest.fixture
def game():
    game = Game.create(["Alice", "Bob"], seed=4)
    game.apply_action("Alice", {"type": "select_strategy", "card_id": 1})
    return game


@pytest.fixture
def client(tmp_path, game):
    app = create_app(tmp_path)
    app.config["GAME_STORE"].add(game)
    return app.test_client()


def test_version_grows_with_every_change(game):
    before = game.version

    game.apply_action("Bob", {"type": "select_strategy", "card_id": 6})

    assert game.version > before


def test_rejected_action_keeps_the_version(game):
    before = game.version

    assert not game.apply_action("Bob", {"type": "select_strategy", "card_id": 1}).ok
    assert game.version == before


def test_known_version_is_answered_without_the_state(client, game):
    response = client.get(f"/api/state?game_id={game.id}&since={game.version}")

    assert response.get_json() == {
        "ok": True,
        "unchanged": True,
        "version": game.version,
    }


def test_outdated_version_returns_the_full_state(client, game):
    response = client.get(f"/api/state?game_id={game.id}&since={game.version - 1}")
    data = response.get_json()

    assert data["version"] == game.version
    assert data["players"]


def test_version_survives_serialisation(game):
    restored = Game.from_dict(game.to_dict())

    assert restored.version == game.version
