"""Backwards compatible re-export; the implementation lives in :mod:`ti.game`."""

from ti.game import VICTORY_POINTS_TO_WIN, Game

__all__ = ["Game", "VICTORY_POINTS_TO_WIN"]
