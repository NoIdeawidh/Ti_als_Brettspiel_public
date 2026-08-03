import pytest

from ti.agenda import AGAINST, FOR, research_surcharge, tally, token_bonus
from ti.game import Game
from ti.phases import Phase
from ti.setup import MECATOL_ID


def start_round(game):
    for index in range(len(game.players)):
        game.apply_action(
            game.turns.current_player, {"type": "select_strategy", "card_id": index + 1}
        )


def take_mecatol(game, player_name):
    mecatol = game.board.get(MECATOL_ID)
    for planet in mecatol.planets:
        planet.controller = player_name


def end_round(game):
    while game.turns.phase == Phase.ACTION:
        game.apply_action(game.turns.current_player, {"type": "pass"})


@pytest.fixture
def game():
    game = Game.create(["Alice", "Bob"], seed=7)
    start_round(game)
    return game


def agenda_phase(game, agenda_id):
    """Force a specific agenda to be revealed after the status phase."""
    take_mecatol(game, "Alice")
    game.agenda_deck = [agenda_id]
    end_round(game)
    assert game.turns.phase == Phase.AGENDA
    assert game.active_agenda == agenda_id


def test_agenda_phase_only_after_custodian(game):
    end_round(game)
    assert game.turns.phase == Phase.STRATEGY
    assert game.active_agenda is None


def test_law_is_enacted_and_changes_research_cost(game):
    agenda_phase(game, "anti_intellectual_revolution")
    alice, bob = game.players
    alice.influence, bob.influence = 5, 5

    assert game.apply_action(
        alice.name, {"type": "vote", "outcome": FOR, "influence": 4}
    ).ok
    assert game.turns.phase == Phase.AGENDA
    assert game.apply_action(
        bob.name, {"type": "vote", "outcome": AGAINST, "influence": 2}
    ).ok

    assert game.laws == {"anti_intellectual_revolution": FOR}
    assert alice.influence == 1
    assert game.turns.phase == Phase.STRATEGY

    start_round(game)
    player = game.get_player(game.turns.current_player)
    player.resources = 4
    result = game.apply_action(
        player.name, {"type": "research", "technology": "plasma_scoring"}
    )
    assert result.ok, result.message
    assert result.data["cost"] == 4
    assert player.resources == 0


def test_directive_resolves_immediately(game):
    agenda_phase(game, "classified_document_leaks")
    alice, bob = game.players
    alice.influence, bob.influence = 5, 5
    before = bob.vp

    game.apply_action(alice.name, {"type": "vote", "outcome": "Bob", "influence": 3})
    game.apply_action(bob.name, {"type": "vote", "outcome": "Bob", "influence": 1})

    assert bob.vp == before + 1
    assert game.laws == {}
    assert game.active_agenda is None


def test_vote_validation(game):
    agenda_phase(game, "mutiny")
    alice = game.players[0]
    alice.influence = 2

    assert not game.apply_action(
        alice.name, {"type": "vote", "outcome": "Vielleicht", "influence": 1}
    ).ok
    assert not game.apply_action(
        alice.name, {"type": "vote", "outcome": FOR, "influence": 5}
    ).ok
    assert game.apply_action(
        alice.name, {"type": "vote", "outcome": FOR, "influence": 1}
    ).ok
    assert not game.apply_action(
        alice.name, {"type": "vote", "outcome": FOR, "influence": 1}
    ).ok


def test_speaker_breaks_ties(game):
    agenda_phase(game, "fleet_regulations")
    alice, bob = game.players
    alice.influence, bob.influence = 3, 3
    assert game.turns.speaker == "Alice"

    game.apply_action(alice.name, {"type": "vote", "outcome": FOR, "influence": 2})
    game.apply_action(bob.name, {"type": "vote", "outcome": AGAINST, "influence": 2})
    assert game.laws == {"fleet_regulations": FOR}

    assert tally(
        {"a": {"outcome": FOR, "influence": 1}, "b": {"outcome": AGAINST, "influence": 3}},
        [FOR],
    ) == AGAINST


def test_agenda_state_survives_serialisation(game):
    agenda_phase(game, "minister_of_industry")
    alice = game.players[0]
    alice.influence = 4
    game.apply_action(alice.name, {"type": "vote", "outcome": "Alice", "influence": 2})

    restored = Game.from_dict(game.to_dict())
    assert restored.active_agenda == "minister_of_industry"
    assert restored.votes["Alice"]["influence"] == 2
    assert restored.turns.phase == Phase.AGENDA


def test_shared_research_lowers_the_research_cost():
    assert research_surcharge({"shared_research": FOR}) == -1
    assert research_surcharge({"shared_research": AGAINST}) == 0


def test_minister_of_war_grants_an_extra_token_per_round():
    assert token_bonus({"minister_of_war": "Alice"}, "Alice") == 1
    assert token_bonus({"minister_of_war": "Alice"}, "Bob") == 0
