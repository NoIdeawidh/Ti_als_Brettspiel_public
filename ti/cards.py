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
    action_cards: int = 0
    """Action cards drawn from the shared deck."""
    free_research: int = 0
    """Technologies the player may research without paying resources."""
    fleet_supply: int = 0
    """Permanent increase of the ships allowed in a single system."""
    free_structures: int = 0
    """Structures the player may build without paying resources."""
    trade_goods_others: int = 0
    """Trade goods every *other* player receives."""
    score_objective: bool = False
    """Allows scoring a revealed public objective outside the status phase."""
    vp_holding_mecatol: int = 0
    """Victory points granted only while the player holds Mecatol Rex."""

    def to_dict(self) -> dict:
        return {
            "resources": self.resources,
            "trade_goods": self.trade_goods,
            "influence": self.influence,
            "tokens": self.tokens,
            "vp": self.vp,
            "action_cards": self.action_cards,
            "free_research": self.free_research,
            "fleet_supply": self.fleet_supply,
            "free_structures": self.free_structures,
            "trade_goods_others": self.trade_goods_others,
            "score_objective": self.score_objective,
            "vp_holding_mecatol": self.vp_holding_mecatol,
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
        if self.action_cards:
            parts.append(f"{self.action_cards} Aktionskarte(n)")
        if self.free_research:
            parts.append(f"{self.free_research} kostenlose Forschung")
        if self.fleet_supply:
            parts.append(f"{self.fleet_supply} Flottenkapazität")
        if self.free_structures:
            parts.append(f"{self.free_structures} kostenlose(s) Bauwerk(e)")
        if self.trade_goods_others:
            parts.append(
                f"{self.trade_goods_others} Handelsgüter für alle anderen"
            )
        if self.score_objective:
            parts.append("ein öffentliches Ziel werten")
        if self.vp_holding_mecatol:
            parts.append(
                f"{self.vp_holding_mecatol} Siegpunkt(e) bei Mecatol Rex"
            )
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
        primary=CardEffect(influence=2, action_cards=2),
        secondary=CardEffect(action_cards=1),
    ),
    StrategyCard(
        4,
        "Construction",
        "Bauwerke ohne Kosten",
        primary=CardEffect(free_structures=2),
        secondary=CardEffect(free_structures=1),
    ),
    StrategyCard(
        5,
        "Trade",
        "Handelsgewinne",
        primary=CardEffect(trade_goods=3, trade_goods_others=1),
        secondary=CardEffect(trade_goods=1),
    ),
    StrategyCard(
        6,
        "Warfare",
        "Kriegsvorbereitung",
        primary=CardEffect(tokens=1, fleet_supply=1),
        secondary=CardEffect(tokens=1),
    ),
    StrategyCard(
        7,
        "Technology",
        "Forschungsmittel",
        primary=CardEffect(free_research=2),
        secondary=CardEffect(free_research=1),
    ),
    StrategyCard(
        8,
        "Imperial",
        "Ziel werten, Siegpunkt für Mecatol Rex",
        primary=CardEffect(score_objective=True, vp_holding_mecatol=1),
        secondary=CardEffect(influence=2),
    ),
]

STRATEGY_CARDS: Dict[int, StrategyCard] = {c.id: c for c in STRATEGY_CARD_LIST}


def get_card(card_id: int) -> Optional[StrategyCard]:
    return STRATEGY_CARDS.get(int(card_id))
