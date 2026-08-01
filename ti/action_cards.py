"""Action cards.

Every player draws one card per status phase and may play cards from hand
during their turn.  A card is a name plus an ``effect`` that changes the game
state and returns a log message, so new cards (or house rules) are appended
here without touching the game loop.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ti.game import Game
    from ti.models import Player

Effect = Callable[["Game", "Player", dict], str]

HAND_LIMIT = 7
"""Cards above this limit are discarded at the end of the status phase."""


@dataclass(frozen=True)
class ActionCard:
    id: str
    name: str
    desc: str
    effect: Effect
    needs_target: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "desc": self.desc,
            "needs_target": self.needs_target,
        }


def _reinforcements(game: "Game", player: "Player", action: dict) -> str:
    from ti.agenda import token_maximum
    from ti.game import MAX_COMMAND_TOKENS

    player.command_tokens = min(
        token_maximum(game.laws, MAX_COMMAND_TOKENS), player.command_tokens + 2
    )
    return f"{player.name} gained command tokens"


def _war_funding(game: "Game", player: "Player", action: dict) -> str:
    player.trade_goods += 3
    return f"{player.name} gained 3 trade goods"


def _industrial_initiative(game: "Game", player: "Player", action: dict) -> str:
    player.resources += 2
    return f"{player.name} gained 2 resources"


def _political_stability(game: "Game", player: "Player", action: dict) -> str:
    player.influence += 2
    return f"{player.name} gained 2 influence"


def _unexpected_action(game: "Game", player: "Player", action: dict) -> str:
    """Refresh the own strategy card so its primary ability can be used again."""
    if player.strategy_card in game.played_cards:
        game.played_cards.remove(player.strategy_card)
    return f"{player.name} refreshed their strategy card"


def _insubordination(game: "Game", player: "Player", action: dict) -> str:
    target = game.get_player(str(action.get("target", "")))
    if target is None or target is player:
        raise ValueError("Unknown target player")
    target.command_tokens = max(0, target.command_tokens - 1)
    return f"{target.name} lost a command token"


def _economic_espionage(game: "Game", player: "Player", action: dict) -> str:
    target = game.get_player(str(action.get("target", "")))
    if target is None or target is player:
        raise ValueError("Unknown target player")
    stolen = min(1, target.trade_goods)
    target.trade_goods -= stolen
    player.trade_goods += stolen
    return f"{player.name} stole {stolen} trade goods from {target.name}"


ACTION_CARD_LIST: List[ActionCard] = [
    ActionCard(
        "reinforcements",
        "Verstärkung",
        "Erhalte 2 Kommandotoken",
        _reinforcements,
    ),
    ActionCard(
        "war_funding",
        "Kriegskredite",
        "Erhalte 3 Handelsgüter",
        _war_funding,
    ),
    ActionCard(
        "industrial_initiative",
        "Industrieoffensive",
        "Erhalte 2 Ressourcen",
        _industrial_initiative,
    ),
    ActionCard(
        "political_stability",
        "Politische Stabilität",
        "Erhalte 2 Einfluss",
        _political_stability,
    ),
    ActionCard(
        "unexpected_action",
        "Unerwarteter Schachzug",
        "Bereite deine Strategiekarte erneut vor",
        _unexpected_action,
    ),
    ActionCard(
        "insubordination",
        "Befehlsverweigerung",
        "Ein Mitspieler verliert ein Kommandotoken",
        _insubordination,
        needs_target=True,
    ),
    ActionCard(
        "economic_espionage",
        "Wirtschaftsspionage",
        "Stiehl einem Mitspieler ein Handelsgut",
        _economic_espionage,
        needs_target=True,
    ),
]

ACTION_CARDS: Dict[str, ActionCard] = {c.id: c for c in ACTION_CARD_LIST}


def get_action_card(card_id: Optional[str]) -> Optional[ActionCard]:
    if card_id is None:
        return None
    return ACTION_CARDS.get(card_id)
