import random

from ti.combat import assign_hits, resolve_space_combat
from ti.hexmap import Hex
from ti.models import System, Unit


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
