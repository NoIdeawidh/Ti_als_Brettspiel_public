"""Backwards compatible re-export; the implementation lives in :mod:`ti.combat`."""

from ti.combat import assign_hits, resolve_space_combat, roll_dice

__all__ = ["resolve_space_combat", "roll_dice", "assign_hits"]
