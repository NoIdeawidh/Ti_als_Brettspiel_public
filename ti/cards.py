"""Strategy cards.

``initiative`` defines the turn order in the action phase.  Every card carries
two effects: the *primary* one is used by the card holder with the
``play_strategy`` action, the weaker *secondary* one can be followed by every
other player once, at the price of a command token.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class CardEffect:
    resources: int = 0
    trade_goods: int = 0
    influence: int = 0
    tokens: int = 0
    vp: int = 0

    def to_dict(self) -> dict:
        return {
            "resources": self.resources,
            "trade_goods": self.trade_goods,
            "influence": self.influence,
            "tokens": self.tokens,
            "vp": self.vp,
        }

    def describe(self) -> str:
        parts = []
        if self.resources:
            parts.append(f"{self.resources} Ressourcen")
        if self.trade_goods:
            parts.append(f"{self.trade_goods} Handelsgüter")
        if self.influence:
            parts.append(f"{self.influence} Einfluss")
        if self.tokens:
            parts.append(f"{self.tokens} Kommandotoken")
        if self.vp:
            parts.append(f"{self.vp} Siegpunkt(e)")
        return ", ".join(parts) or "kein Effekt"


@dataclass(frozen=True)
class StrategyCard:
    id: int
    name: str
    desc: str
    primary: CardEffect = CardEffect()
    secondary: CardEffect = CardEffect()

    @property
    def initiative(self) -> int:
        return self.id

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "desc": self.desc,
            "initiative": self.initiative,
            "primary": self.primary.to_dict(),
            "secondary": self.secondary.to_dict(),
        }


STRATEGY_CARD_LIST: List[StrategyCard] = [
    StrategyCard(
        1,
        "Leadership",
        "Kommandotoken und Einfluss",
        primary=CardEffect(influence=2, tokens=3),
        secondary=CardEffect(tokens=1),
    ),
    StrategyCard(
        2,
        "Diplomacy",
        "Diplomatischer Einfluss",
        primary=CardEffect(influence=1),
        secondary=CardEffect(influence=1),
    ),
    StrategyCard(
        3,
        "Politics",
        "Politische Einflussnahme",
        primary=CardEffect(influence=2),
        secondary=CardEffect(influence=1),
    ),
    StrategyCard(
        4,
        "Construction",
        "Mittel für Bauwerke",
        primary=CardEffect(resources=2),
        secondary=CardEffect(resources=1),
    ),
    StrategyCard(
        5,
        "Trade",
        "Handelsgewinne",
        primary=CardEffect(trade_goods=3),
        secondary=CardEffect(trade_goods=1),
    ),
    StrategyCard(
        6,
        "Warfare",
        "Kriegsvorbereitung",
        primary=CardEffect(resources=1, tokens=1),
        secondary=CardEffect(tokens=1),
    ),
    StrategyCard(
        7,
        "Technology",
        "Forschungsmittel",
        primary=CardEffect(resources=2),
        secondary=CardEffect(resources=1),
    ),
    StrategyCard(
        8,
        "Imperial",
        "Siegpunkt oder Sprecherwirkung",
        primary=CardEffect(vp=1),
        secondary=CardEffect(influence=2),
    ),
]

STRATEGY_CARDS: Dict[int, StrategyCard] = {c.id: c for c in STRATEGY_CARD_LIST}


def get_card(card_id: int) -> Optional[StrategyCard]:
    return STRATEGY_CARDS.get(int(card_id))
