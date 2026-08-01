import pytest

from ti.game import Game


@pytest.fixture
def game():
    game = Game.create(["Alice", "Bob"], seed=7)
    game.apply_action("Alice", {"type": "select_strategy", "card_id": 5})
    game.apply_action("Bob", {"type": "select_strategy", "card_id": 6})
    return game


def test_trade_card_yields_trade_goods(game):
    alice = game.get_player("Alice")
    resources = alice.resources

    game.apply_action("Alice", {"type": "play_strategy"})

    assert alice.trade_goods == 3
    assert alice.resources == resources
    assert alice.budget == resources + 3


def test_trade_goods_pay_what_resources_cannot(game):
    alice = game.get_player("Alice")
    alice.resources = 1
    alice.trade_goods = 3

    result = game.apply_action(
        "Alice", {"type": "research", "technology": "antimass_deflectors"}
    )

    assert result.ok
    assert alice.resources == 0
    assert alice.trade_goods == 2


def test_production_falls_back_to_trade_goods(game):
    alice = game.get_player("Alice")
    alice.resources = 0
    alice.trade_goods = 3
    system = game.board.home_system("Alice")

    result = game.apply_action(
        "Alice", {"type": "produce", "system": system.id, "units": ["Carrier"]}
    )

    assert result.ok
    assert (alice.resources, alice.trade_goods) == (0, 0)


def test_trade_goods_can_be_given_away(game):
    alice, bob = game.players
    alice.trade_goods = 2

    assert game.apply_action(
        "Alice", {"type": "trade", "partner": "Bob", "trade_goods": 2}
    ).ok
    assert (alice.trade_goods, bob.trade_goods) == (0, 2)


def test_trade_validation(game):
    alice = game.get_player("Alice")
    alice.trade_goods = 1

    assert not game.apply_action(
        "Alice", {"type": "trade", "partner": "Carol", "trade_goods": 1}
    ).ok
    assert not game.apply_action(
        "Alice", {"type": "trade", "partner": "Alice", "trade_goods": 1}
    ).ok
    assert not game.apply_action(
        "Alice", {"type": "trade", "partner": "Bob", "trade_goods": 0}
    ).ok
    assert not game.apply_action(
        "Alice", {"type": "trade", "partner": "Bob", "trade_goods": 5}
    ).ok
    assert alice.trade_goods == 1


def test_trade_goods_survive_serialisation(game):
    game.get_player("Alice").trade_goods = 4

    restored = Game.from_dict(game.to_dict())
    assert restored.get_player("Alice").trade_goods == 4
