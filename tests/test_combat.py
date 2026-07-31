import random

from ti.combat import assign_hits, resolve_ground_combat, resolve_space_combat
from ti.hexmap import Hex
from ti.models import Planet, System, Unit


def make_system(units_a, units_b):
    system = System(id="s_test", hex=Hex(0, 0))
    system.add_units("A", [Unit.create(t, "A") for t in units_a])
    system.add_units("B", [Unit.create(t, "B") for t in units_b])
    return system


def test_assign_hits_kills_cheapest_first():
    units = [Unit.create("Dreadnought", "A"), Unit.create("Fighter", "A")]
    losses = assign_hits(units, 1)
    assert [u.type_name for u in losses] == ["Fighter"]


def test_combat_ends_with_single_survivor_side():
    system = make_system(["Dreadnought", "Cruiser"], ["Fighter"])
    report = resolve_space_combat(system, "A", "B", random.Random(1))
    assert report["rounds"]
    alive_a = bool(system.units_of("A"))
    alive_b = bool(system.units_of("B"))
    assert not (alive_a and alive_b)
    assert report["winner"] in {"A", "B", None}


def test_combat_is_deterministic_for_same_seed():
    first = resolve_space_combat(
        make_system(["Cruiser"], ["Cruiser"]), "A", "B", random.Random(7)
    )
    second = resolve_space_combat(
        make_system(["Cruiser"], ["Cruiser"]), "A", "B", random.Random(7)
    )
    assert first["winner"] == second["winner"]
    assert len(first["rounds"]) == len(second["rounds"])


def test_ground_combat_captures_empty_planet():
    planet = Planet("Test", controller="B")
    landing = [Unit.create("Infantry", "A")]
    report = resolve_ground_combat(planet, "A", landing, random.Random(3))
    assert report["captured"]
    assert planet.controller == "A"
    assert [u.uid for u in planet.ground_forces] == [landing[0].uid]


def test_ground_combat_against_overwhelming_garrison():
    planet = Planet("Test", controller="Neutral")
    planet.ground_forces = [Unit.create("Infantry", "Neutral") for _ in range(8)]
    report = resolve_ground_combat(planet, "A", [Unit.create("Infantry", "A")], random.Random(3))
    assert not report["captured"]
    assert planet.controller == "Neutral"
