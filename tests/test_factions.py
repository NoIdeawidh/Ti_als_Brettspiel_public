import random

from ti.combat import roll_dice
from ti.factions import FACTION_LIST, combat_bonus, get_faction
from ti.game import Game
from ti.models import Unit


def make_game(factions):
    return Game.create(
        [{"name": name, "faction": faction} for name, faction in factions.items()],
        seed=5,
    )


def test_faction_grants_its_starting_bonus():
    game = make_game({"Alice": "Clan", "Bob": "Jol-Nar"})
    alice, bob = game.players

    clan = get_faction("Clan")
    assert alice.trade_goods == clan.trade_goods
    assert alice.technologies == list(clan.technologies)
    assert bob.technologies == list(get_faction("Jol-Nar").technologies)


def test_faction_units_are_placed_in_the_home_system():
    game = make_game({"Alice": "Arborec", "Bob": "Sardakk"})
    home = game.board.home_system("Alice")
    carriers = [u for u in home.units_of("Alice") if u.type_name == "Carrier"]
    other = game.board.home_system("Bob")

    assert len(carriers) == len(
        [u for u in other.units_of("Bob") if u.type_name == "Carrier"]
    ) + 1


def test_combat_bonus_changes_the_hit_threshold():
    units = [Unit.create("Cruiser", "Alice")]
    base = roll_dice(units, random.Random(1))["rolls"][0]["combat"]

    boosted = roll_dice(units, random.Random(1), combat_bonus("Sardakk"))
    assert boosted["rolls"][0]["combat"] == base + 1

    weakened = roll_dice(units, random.Random(1), combat_bonus("Jol-Nar"))
    assert weakened["rolls"][0]["combat"] == base - 1


def test_engine_knows_the_faction_bonuses():
    game = make_game({"Alice": "Sardakk", "Bob": "Federation"})
    assert game.engine.combat_bonuses == {"Alice": 1, "Bob": 0}


def test_unknown_faction_falls_back_to_plain_start():
    game = Game.create([{"name": "Alice", "faction": "Unbekannt"}], seed=5)
    assert game.get_player("Alice").faction == "Unbekannt"
    assert game.engine.combat_bonuses == {"Alice": 0}


def test_state_exposes_the_faction_catalogue():
    state = make_game({"Alice": "Clan", "Bob": "Federation"}).to_dict()
    assert len(state["factions"]) == len(FACTION_LIST)
