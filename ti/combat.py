"""Dice based space combat resolution.

Combat runs in rounds: both sides roll their dice simultaneously, hits are
assigned to the cheapest units first and the fight continues until only one
side (or nobody) has ships left.
"""

from __future__ import annotations

import random
from typing import Dict, List, Optional, Sequence

from ti.models import System, Unit

MAX_COMBAT_ROUNDS = 20


def roll_dice(units: Sequence[Unit], rng: random.Random) -> Dict[str, object]:
    """Roll all combat dice for ``units`` and return rolls plus hit count."""
    rolls: List[dict] = []
    hits = 0
    for unit in units:
        unit_type = unit.unit_type
        for _ in range(max(1, unit_type.dice)):
            value = rng.randint(1, 10)
            hit = value <= unit_type.combat
            hits += 1 if hit else 0
            rolls.append(
                {
                    "uid": unit.uid,
                    "type": unit.type_name,
                    "combat": unit_type.combat,
                    "roll": value,
                    "hit": hit,
                }
            )
    return {"rolls": rolls, "hits": hits}


def assign_hits(units: List[Unit], hits: int) -> List[Unit]:
    """Return the units destroyed by ``hits``; cheapest units die first."""
    if hits <= 0 or not units:
        return []
    order = sorted(units, key=lambda u: (u.unit_type.cost, u.unit_type.combat))
    return order[:hits]


def resolve_space_combat(
    system: System,
    attacker: str,
    defender: str,
    rng: random.Random,
) -> dict:
    """Fight out a space combat inside ``system`` and mutate it in place."""
    rounds: List[dict] = []
    for round_number in range(1, MAX_COMBAT_ROUNDS + 1):
        attacker_units = list(system.units_of(attacker))
        defender_units = list(system.units_of(defender))
        if not attacker_units or not defender_units:
            break

        attacker_roll = roll_dice(attacker_units, rng)
        defender_roll = roll_dice(defender_units, rng)

        attacker_losses = assign_hits(attacker_units, int(defender_roll["hits"]))
        defender_losses = assign_hits(defender_units, int(attacker_roll["hits"]))

        system.remove_units(attacker, [u.uid for u in attacker_losses])
        system.remove_units(defender, [u.uid for u in defender_losses])

        rounds.append(
            {
                "round": round_number,
                "attacker_rolls": attacker_roll["rolls"],
                "defender_rolls": defender_roll["rolls"],
                "attacker_hits": attacker_roll["hits"],
                "defender_hits": defender_roll["hits"],
                "attacker_losses": [u.uid for u in attacker_losses],
                "defender_losses": [u.uid for u in defender_losses],
            }
        )

    winner = _winner(system, attacker, defender)
    return {
        "system": system.id,
        "attacker": attacker,
        "defender": defender,
        "rounds": rounds,
        "winner": winner,
    }


def _winner(system: System, attacker: str, defender: str) -> Optional[str]:
    attacker_alive = bool(system.units_of(attacker))
    defender_alive = bool(system.units_of(defender))
    if attacker_alive and not defender_alive:
        return attacker
    if defender_alive and not attacker_alive:
        return defender
    return None
