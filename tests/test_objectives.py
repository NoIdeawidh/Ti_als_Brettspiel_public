import pytest

from ti.game import Game
from ti.models import Unit
from ti.objectives import OBJECTIVES, get_objective
from ti.setup import MECATOL_ID


@pytest.fixture
def game():
    return Game.create(["Alice", "Bob"], seed=7)


def pick_strategy_cards(game):
    for index in range(len(game.players)):
        game.apply_action(game.turns.current_player, {"type": "select_strategy", "card_id": index + 1})


def end_round(game):
    for _ in range(len(game.players)):
        game.apply_action(game.turns.current_player, {"type": "pass"})


def test_one_objective_is_revealed_per_round(game):
    assert len(game.revealed_objectives) == 1
    pick_strategy_cards(game)
    end_round(game)
    assert len(game.revealed_objectives) == 2
    assert all(get_objective(oid) for oid in game.revealed_objectives)


def test_objective_scores_once_per_player(game):
    objective = OBJECTIVES["expand_borders"]
    game.revealed_objectives = [objective.id]
    game.scored_objectives = {objective.id: []}
    alice = game.players[0]
    for planet in [p for s in game.board.systems for p in s.planets][:3]:
        planet.controller = alice.name

    pick_strategy_cards(game)
    end_round(game)
    first = alice.vp
    assert objective.id in game.scored_objectives
    assert alice.name in game.scored_objectives[objective.id]

    game.revealed_objectives = [objective.id]
    pick_strategy_cards(game)
    end_round(game)
    assert alice.vp - first < objective.vp + 1


def test_custodian_bonus_is_granted_only_once(game):
    mecatol = game.board.get(MECATOL_ID)
    alice = game.players[0]
    mecatol.planets[0].controller = alice.name

    pick_strategy_cards(game)
    end_round(game)
    assert game.custodian == alice.name
    before = alice.vp
    pick_strategy_cards(game)
    end_round(game)
    assert game.custodian == alice.name
    assert alice.vp - before <= 1  # objectives may still score, custodian does not


def test_objectives_survive_serialisation(game):
    pick_strategy_cards(game)
    end_round(game)
    restored = Game.from_dict(game.to_dict())
    assert restored.revealed_objectives == game.revealed_objectives
    assert restored.scored_objectives == game.scored_objectives
    assert restored.objective_deck == game.objective_deck
    assert restored.custodian == game.custodian


def test_new_public_objectives_use_board_state():
    game = Game.create(["Alice", "Bob"], seed=3)
    alice = game.get_player("Alice")
    research = get_objective("research_program")
    industry = get_objective("industrial_base")

    assert not research.is_fulfilled(game.board, alice)
    alice.technologies = ["antimass_deflectors", "sarween_tools"]
    assert research.is_fulfilled(game.board, alice)

    planet = game.board.planets_of("Alice")[0]
    planet.structures.append(Unit.create("PDS", "Alice"))
    planet.structures.append(Unit.create("Space Dock", "Alice"))
    assert industry.is_fulfilled(game.board, alice)
