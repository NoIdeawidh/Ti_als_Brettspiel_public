"""Strategy cards.

``initiative`` defines the turn order in the action phase, ``bonus`` describes
the immediate effect that is applied when the card is played.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class StrategyCard:
    id: int
    name: str
    desc: str
    bonus_resources: int = 0
    bonus_influence: int = 0
    bonus_vp: int = 0

    @property
    def initiative(self) -> int:
        return self.id

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "desc": self.desc,
            "initiative": self.initiative,
            "bonus_resources": self.bonus_resources,
            "bonus_influence": self.bonus_influence,
            "bonus_vp": self.bonus_vp,
        }


STRATEGY_CARD_LIST: List[StrategyCard] = [
    StrategyCard(1, "Leadership", "Gain command tokens or take action", bonus_influence=2),
    StrategyCard(2, "Diplomacy", "Influence based effects", bonus_influence=1),
    StrategyCard(3, "Politics", "Agenda/Politics effects", bonus_influence=2),
    StrategyCard(4, "Construction", "Build structures/units", bonus_resources=2),
    StrategyCard(5, "Trade", "Trade / promissory mechanics", bonus_resources=3),
    StrategyCard(6, "Warfare", "Combat advantages", bonus_resources=1),
    StrategyCard(7, "Technology", "Research tech", bonus_resources=2),
    StrategyCard(8, "Imperial", "Gain VP or speaker effects", bonus_vp=1),
]

STRATEGY_CARDS: Dict[int, StrategyCard] = {c.id: c for c in STRATEGY_CARD_LIST}


def get_card(card_id: int) -> Optional[StrategyCard]:
    return STRATEGY_CARDS.get(int(card_id))
