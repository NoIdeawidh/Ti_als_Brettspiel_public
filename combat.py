# sub/combat.py
"""
Combat helpers.

- compute_space_combat_rolls: computes rolls and hits for attacker+defender.
  Considers temporary owner buffs (owner.combat_buff, default 0).
- apply_losses_to_system: removes units by UID from system & owner lists.
"""

import random

def roll_d10(rng):
    return rng.randint(1, 10)

def compute_space_combat_rolls(attacker_units, defender_units, rng):
    """
    attacker_units / defender_units: list of Unit objects
    rng: instance of random.Random (seeded in Game)
    Returns: {
      'attacker': [ {uid, type, combat, roll, hit}, ... ],
      'defender': [ ... ],
      'attacker_hits': int,
      'defender_hits': int
    }
    """
    atk_results = []
    def_results = []
    atk_hits = 0
    def_hits = 0

    for u in attacker_units:
        base = getattr(u, 'combat', 1) or 1
        owner_buff = getattr(u.owner, 'combat_buff', 0) or 0
        combat_val = base + owner_buff
        roll = roll_d10(rng)
        hit = roll <= combat_val
        atk_results.append({
            "uid": u.uid,
            "type": u.type_name,
            "combat": combat_val,
            "base_combat": base,
            "owner_buff": owner_buff,
            "roll": roll,
            "hit": hit
        })
        if hit:
            atk_hits += 1

    for u in defender_units:
        base = getattr(u, 'combat', 1) or 1
        owner_buff = getattr(u.owner, 'combat_buff', 0) or 0
        combat_val = base + owner_buff
        roll = roll_d10(rng)
        hit = roll <= combat_val
        def_results.append({
            "uid": u.uid,
            "type": u.type_name,
            "combat": combat_val,
            "base_combat": base,
            "owner_buff": owner_buff,
            "roll": roll,
            "hit": hit
        })
        if hit:
            def_hits += 1

    return {
        "attacker": atk_results,
        "defender": def_results,
        "attacker_hits": atk_hits,
        "defender_hits": def_hits
    }

def apply_losses_to_system(system, owner_player, loss_uids):
    """
    Remove units with uids in loss_uids from system.ships[owner_player] and owner_player.ships.
    Returns list of removed unit uids.
    """
    removed = []
    if owner_player not in system.ships:
        return removed
    current = system.ships.get(owner_player, [])
    remaining = []
    by_uid = {u.uid: u for u in current}
    for u in current:
        if u.uid in loss_uids:
            removed.append(u.uid)
            try:
                owner_player.ships.remove(u)
            except Exception:
                pass
        else:
            remaining.append(u)
    system.ships[owner_player] = remaining
    return removed
