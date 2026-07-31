import pytest

from ti.game import Game
from ti.phases import Phase


@pytest.fixture
def game():
    return Game.create(["Alice", "Bob"], seed=42)


def pick_strategy_cards(game):
    for name in game.turns.strategy_order():
        card_id = game.available_strategy_cards()[0]
        result = game.apply_action(name, {"type": "select_strategy", "card_id": card_id})
        assert result.ok, result.message


def test_setup_creates_home_systems_and_units(game):
    for player in game.players:
        home = game.board.home_system(player.name)
        assert home is not None
        assert home.units_of(player.name)


def test_strategy_phase_orders_action_phase(game):
    pick_strategy_cards(game)
    assert game.turns.phase == Phase.ACTION
    assert game.turns.order == sorted(
        game.turns.order, key=lambda n: game.get_player(n).strategy_card
    )


def test_actions_are_rejected_out_of_turn(game):
    other = game.turns.strategy_order()[1]
    result = game.apply_action(other, {"type": "select_strategy", "card_id": 1})
    assert not result.ok


def test_move_requires_range(game):
    pick_strategy_cards(game)
    player = game.turns.current_player
    home = game.board.home_system(player)
    far = max(game.board.systems, key=lambda s: home.hex.distance(s.hex))
    result = game.apply_action(
        player, {"type": "move", "from": home.id, "to": far.id}
    )
    assert not result.ok
    assert "movement range" in result.message or "capacity" in result.message


def test_move_to_adjacent_system(game):
    pick_strategy_cards(game)
    player = game.turns.current_player
    home = game.board.home_system(player)
    target = game.board.neighbors(home.id)[0]
    cruiser = next(u for u in home.units_of(player) if u.type_name == "Cruiser")
    result = game.apply_action(
        player,
        {"type": "move", "from": home.id, "to": target.id, "units": [cruiser.uid]},
    )
    assert result.ok, result.message
    assert cruiser.uid in [u.uid for u in target.units_of(player)]


def test_produce_costs_resources(game):
    pick_strategy_cards(game)
    player_name = game.turns.current_player
    player = game.get_player(player_name)
    player.resources = 5
    home = game.board.home_system(player_name)
    result = game.apply_action(
        player_name,
        {"type": "produce", "system": home.id, "units": ["Destroyer"]},
    )
    assert result.ok, result.message
    assert player.resources == 4


def land_on_neighbour(game, player):
    """Move a carrier with its infantry to an adjacent planet system."""
    home = game.board.home_system(player)
    target = next(
        s for s in game.board.neighbors(home.id) if s.planets and not s.occupants()
    )
    carrier = next(u for u in home.units_of(player) if u.type_name == "Carrier")
    infantry = [u for u in home.units_of(player) if u.type_name == "Infantry"]
    assert game.apply_action(
        player,
        {
            "type": "move",
            "from": home.id,
            "to": target.id,
            "units": [carrier.uid] + [u.uid for u in infantry],
        },
    ).ok
    return target, infantry


def test_invade_undefended_planet(game):
    pick_strategy_cards(game)
    player = game.turns.current_player
    target, infantry = land_on_neighbour(game, player)
    planet = target.planets[0]
    planet.ground_forces = []
    result = game.apply_action(
        player,
        {"type": "invade", "system": target.id, "planet": planet.name},
    )
    assert result.ok and result.data["captured"], result.message
    assert planet.controller == player
    assert len(planet.ground_forces) == len(infantry)
    assert not [u for u in target.units_of(player) if u.type_name == "Infantry"]


def test_invade_without_ground_forces_fails(game):
    pick_strategy_cards(game)
    player = game.turns.current_player
    home = game.board.home_system(player)
    target = next(
        s for s in game.board.neighbors(home.id) if s.planets and not s.occupants()
    )
    cruiser = next(u for u in home.units_of(player) if u.type_name == "Cruiser")
    assert game.apply_action(
        player,
        {"type": "move", "from": home.id, "to": target.id, "units": [cruiser.uid]},
    ).ok
    result = game.apply_action(
        player,
        {"type": "invade", "system": target.id, "planet": target.planets[0].name},
    )
    assert not result.ok
    assert "ground forces" in result.message


def test_failed_invasion_returns_survivors_to_the_fleet(game):
    pick_strategy_cards(game)
    player = game.turns.current_player
    target, _ = land_on_neighbour(game, player)
    planet = target.planets[0]
    planet.ground_forces = [
        u for u in game.board.home_system(player).planets[0].ground_forces
    ]
    for unit in planet.ground_forces:
        unit.owner = "Neutral"
    planet.ground_forces *= 6  # overwhelming garrison

    result = game.apply_action(
        player, {"type": "invade", "system": target.id, "planet": planet.name}
    )
    assert result.ok
    assert not result.data["captured"]
    assert planet.controller != player


def test_command_tokens_limit_activations(game):
    pick_strategy_cards(game)
    player_name = game.turns.current_player
    player = game.get_player(player_name)
    player.command_tokens = 1
    player.resources = 9
    home = game.board.home_system(player_name)

    assert game.apply_action(
        player_name, {"type": "produce", "system": home.id, "units": ["Fighter"]}
    ).ok
    assert player.command_tokens == 0
    blocked = game.apply_action(
        player_name, {"type": "produce", "system": home.id, "units": ["Fighter"]}
    )
    assert not blocked.ok
    assert "command tokens" in blocked.message


def test_passing_everyone_starts_next_round(game):
    pick_strategy_cards(game)
    for _ in range(len(game.players)):
        current = game.turns.current_player
        assert game.apply_action(current, {"type": "pass"}).ok
    assert game.turns.round == 2
    assert game.turns.phase == Phase.STRATEGY
    assert all(p.strategy_card is None for p in game.players)


def test_status_phase_grants_income(game):
    pick_strategy_cards(game)
    before = {p.name: p.resources for p in game.players}
    for _ in range(len(game.players)):
        game.apply_action(game.turns.current_player, {"type": "pass"})
    assert all(p.resources > before[p.name] for p in game.players)


def test_serialisation_round_trip(game):
    pick_strategy_cards(game)
    restored = Game.from_dict(game.to_dict())
    assert restored.to_dict()["systems"] == game.to_dict()["systems"]
    assert restored.turns.current_player == game.turns.current_player
    assert restored.turns.phase == game.turns.phase
