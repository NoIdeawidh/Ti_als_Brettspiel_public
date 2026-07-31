import pytest

from server import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(save_dir=tmp_path)
    app.config.update(TESTING=True)
    with app.test_client() as client:
        yield client


def create_game(client):
    response = client.post("/api/create", json={"players": ["Alice", "Bob"], "seed": 1})
    assert response.status_code == 200
    return response.get_json()["game_id"]


def test_create_and_state(client):
    game_id = create_game(client)
    state = client.get(f"/api/state?game_id={game_id}").get_json()
    assert state["ok"]
    assert len(state["players"]) == 2
    assert state["phase"] == "strategy"
    assert state["turn"]["current_player"] == "Alice"


def test_create_rejects_duplicate_names(client):
    response = client.post("/api/create", json={"players": ["Alice", "Alice"]})
    assert response.status_code == 400
    assert not response.get_json()["ok"]


def test_unknown_game_returns_404(client):
    assert client.get("/api/state?game_id=nope").status_code == 404


def test_action_endpoint_and_persistence(client, tmp_path):
    game_id = create_game(client)
    response = client.post(
        "/api/action",
        json={
            "game_id": game_id,
            "player": "Alice",
            "action": {"type": "select_strategy", "card_id": 3},
        },
    )
    assert response.get_json()["ok"]
    assert (tmp_path / f"{game_id}.json").exists()

    listed = client.get("/api/games").get_json()["games"]
    assert any(g["game_id"] == game_id for g in listed)


def test_meta_endpoints(client):
    assert client.get("/api/unit_types").get_json()["unit_types"]
    assert len(client.get("/api/strategy_cards").get_json()["cards"]) == 8
