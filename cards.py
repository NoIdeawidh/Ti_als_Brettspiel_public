"""Backwards compatible re-export; the implementation lives in :mod:`ti.cards`."""

from ti.cards import STRATEGY_CARD_LIST, STRATEGY_CARDS, StrategyCard, get_card

__all__ = ["STRATEGY_CARDS", "STRATEGY_CARD_LIST", "StrategyCard", "get_card"]
