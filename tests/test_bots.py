import pytest

from server import create_app
from ti.bot import act_for_bots
from ti.game import Game
from ti.phases import Phase


def single_player_game(seed: int = 12) -> Game:
    return Game.create(
        [{"name": "Alice"}, {"name": "Bot 1", "bot": True}],
        seed=seed,
    )


def test_setup_marks_bot_players():
    game = single_player_game()

    assert not game.get_player("Alice").is_bot
    assert game.get_player("Bot 1").is_bot


def test_bots_pick_a_strategy_card_before_the_human():
    game = Game.create([{"name": "Bot 1", "bot": True}, {"name": "Alice"}], seed=3)

    act_for_bots(game)

    assert game.get_player("Bot 1").strategy_card is not None
    assert game.turns.current_player == "Alice"


def test_bots_take_their_action_turn():
    game = single_player_game()
    game.apply_action("Alice", {"type": "select_strategy", "card_id": 1})
    act_for_bots(game)
    assert game.turns.phase == Phase.ACTION

    game.apply_action("Alice", {"type": "end_turn"})
    act_for_bots(game)

    assert any("Bot 1" in entry for entry in game.history)


def test_bots_never_block_the_game():
    game = single_player_game()
    for _ in range(20):
        act_for_bots(game)
        current = game.turns.current_player
        if current is None or not game.get_player(current).is_bot:
            break
    else:  # pragma: no cover - only on a broken policy
        pytest.fail("bots kept the turn")

    assert game.turns.phase != Phase.FINISHED or game.winner


def test_bots_vote_in_the_agenda_phase():
    game = single_player_game()
    game.custodian = "Alice"
    game.turns.begin_agenda_phase()
    game.reveal_agenda()

    act_for_bots(game)

    assert "Bot 1" in game.votes or game.active_agenda is None


def test_action_endpoint_lets_the_bots_answer(tmp_path):
    game = single_player_game()
    app = create_app(tmp_path)
    app.config["GAME_STORE"].add(game)
    client = app.test_client()

    response = client.post(
        "/api/action",
        json={
            "game_id": game.id,
            "player": "Alice",
            "action": {"type": "select_strategy", "card_id": 1},
        },
    )

    assert response.get_json()["ok"]
    assert game.get_player("Bot 1").strategy_card is not None
