"""Dice based space combat resolution.

Combat runs in rounds: both sides roll their dice simultaneously, hits are
assigned to the cheapest units first and the fight continues until only one
side (or nobody) has ships left.
"""

from __future__ import annotations

import random
from typing import Dict, List, Optional, Sequence

from ti.models import Planet, System, Unit

MAX_COMBAT_ROUNDS = 20


def roll_dice(
    units: Sequence[Unit], rng: random.Random, bonus: int = 0
) -> Dict[str, object]:
    """Roll all combat dice for ``units`` and return rolls plus hit count."""
    rolls: List[dict] = []
    hits = 0
    for unit in units:
        unit_type = unit.unit_type
        combat = max(1, min(10, unit_type.combat + bonus))
        for _ in range(max(1, unit_type.dice)):
            value = rng.randint(1, 10)
            hit = value <= combat
            hits += 1 if hit else 0
            rolls.append(
                {
                    "uid": unit.uid,
                    "type": unit.type_name,
                    "combat": combat,
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
    bonuses: Optional[Dict[str, int]] = None,
) -> dict:
    """Fight out a space combat inside ``system`` and mutate it in place."""
    rounds: List[dict] = []
    for round_number in range(1, MAX_COMBAT_ROUNDS + 1):
        attacker_units = list(system.units_of(attacker))
        defender_units = list(system.units_of(defender))
        if not attacker_units or not defender_units:
            break

        bonus = bonuses or {}
        attacker_roll = roll_dice(attacker_units, rng, bonus.get(attacker, 0))
        defender_roll = roll_dice(defender_units, rng, bonus.get(defender, 0))

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


def resolve_ground_combat(
    planet: Planet,
    attacker: str,
    attacker_units: List[Unit],
    rng: random.Random,
    bonuses: Optional[Dict[str, int]] = None,
) -> dict:
    """Fight over ``planet``; surviving attackers stay on the planet.

    ``attacker_units`` are the ground forces landed by ``attacker``; the
    defenders are the units already stationed on the planet.
    """
    defender = planet.defender()
    landing = list(attacker_units)
    rounds: List[dict] = []

    for round_number in range(1, MAX_COMBAT_ROUNDS + 1):
        defenders = list(planet.ground_forces)
        if not landing or not defenders:
            break

        bonus = bonuses or {}
        attacker_roll = roll_dice(landing, rng, bonus.get(attacker, 0))
        defender_roll = roll_dice(
            defenders, rng, bonus.get(defender, 0) if defender else 0
        )

        attacker_losses = assign_hits(landing, int(defender_roll["hits"]))
        defender_losses = assign_hits(defenders, int(attacker_roll["hits"]))

        lost = {u.uid for u in attacker_losses}
        landing = [u for u in landing if u.uid not in lost]
        killed = {u.uid for u in defender_losses}
        planet.ground_forces = [u for u in planet.ground_forces if u.uid not in killed]

        rounds.append(
            {
                "round": round_number,
                "attacker_hits": attacker_roll["hits"],
                "defender_hits": defender_roll["hits"],
                "attacker_losses": sorted(lost),
                "defender_losses": sorted(killed),
            }
        )

    captured = bool(landing) and not planet.ground_forces
    if captured:
        planet.ground_forces = landing
        planet.controller = attacker

    return {
        "planet": planet.name,
        "attacker": attacker,
        "defender": defender,
        "rounds": rounds,
        "captured": captured,
        "surviving_attackers": [u.uid for u in landing],
    }


def _winner(system: System, attacker: str, defender: str) -> Optional[str]:
    attacker_alive = bool(system.units_of(attacker))
    defender_alive = bool(system.units_of(defender))
    if attacker_alive and not defender_alive:
        return attacker
    if defender_alive and not attacker_alive:
        return defender
    return None
