"""Agenda phase: agendas, voting outcomes and their effects.

Agendas come in two flavours:

``directive``  resolved immediately, then discarded
``law``        stays in play; its effect is read back through the helper
               functions at the bottom of this module

Directives carry their effect as a callable over the player list so that the
game aggregate only has to tally votes and store laws, never to special-case
individual agendas.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Tuple, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ti.models import Player

FOR = "Für"
AGAINST = "Gegen"

LAW = "law"
DIRECTIVE = "directive"

ELECT_OUTCOME = "outcome"
ELECT_PLAYER = "player"

Effect = Callable[[List["Player"], str], str]


@dataclass(frozen=True)
class Agenda:
    id: str
    name: str
    desc: str
    kind: str
    election: str = ELECT_OUTCOME
    outcomes: Tuple[str, ...] = (FOR, AGAINST)
    """Possible outcomes; ignored when players are elected."""
    effect: Optional[Effect] = None
    """Immediate effect of a directive; laws take effect through the helpers."""

    def resolve(self, players: List["Player"], outcome: str) -> str:
        if self.effect is None:
            return f"{self.name}: {outcome}"
        return self.effect(players, outcome)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "desc": self.desc,
            "kind": self.kind,
            "election": self.election,
            "outcomes": list(self.outcomes),
        }


def _classified_document_leaks(players: List["Player"], outcome: str) -> str:
    for player in players:
        if player.name == outcome:
            player.vp += 1
            return f"{outcome} erhält 1 Siegpunkt"
    return f"{outcome} ist kein Spieler"


def _economic_stimulus(players: List["Player"], outcome: str) -> str:
    if outcome == FOR:
        for player in players:
            player.resources += 3
        return "Alle Spieler erhalten 3 Ressourcen"
    for player in players:
        player.influence += 1
    return "Alle Spieler erhalten 1 Einfluss"


def _mutiny(players: List["Player"], outcome: str) -> str:
    if outcome != FOR:
        for player in players:
            player.influence += 1
        return "Alle Spieler erhalten 1 Einfluss"
    if not players:
        return "Keine Spieler"
    lead = max(player.vp for player in players)
    leaders = [player for player in players if player.vp == lead and lead > 0]
    for player in leaders:
        player.vp -= 1
    if not leaders:
        return "Niemand verliert Siegpunkte"
    return f"{', '.join(p.name for p in leaders)} verliert je 1 Siegpunkt"


AGENDA_LIST: List[Agenda] = [
    Agenda(
        "anti_intellectual_revolution",
        "Anti-Intellectual Revolution",
        "Bei Annahme kostet jede Forschung 2 Ressourcen mehr",
        LAW,
    ),
    Agenda(
        "fleet_regulations",
        "Fleet Regulations",
        "Bei Annahme sinkt das Kommandotoken-Maximum auf 6",
        LAW,
    ),
    Agenda(
        "minister_of_industry",
        "Minister of Industry",
        "Der gewählte Spieler erhält jede Runde 2 zusätzliche Ressourcen",
        LAW,
        election=ELECT_PLAYER,
    ),
    Agenda(
        "classified_document_leaks",
        "Classified Document Leaks",
        "Der gewählte Spieler erhält 1 Siegpunkt",
        DIRECTIVE,
        election=ELECT_PLAYER,
        effect=_classified_document_leaks,
    ),
    Agenda(
        "economic_stimulus",
        "Economic Stimulus",
        "Bei Annahme erhalten alle 3 Ressourcen, sonst 1 Einfluss",
        DIRECTIVE,
        effect=_economic_stimulus,
    ),
    Agenda(
        "mutiny",
        "Mutiny",
        "Bei Annahme verlieren die führenden Spieler 1 Siegpunkt",
        DIRECTIVE,
        effect=_mutiny,
    ),
]

AGENDAS: Dict[str, Agenda] = {a.id: a for a in AGENDA_LIST}

RESEARCH_SURCHARGE = 2
MINISTER_INCOME = 2
RESTRICTED_TOKEN_MAXIMUM = 6


def get_agenda(agenda_id: Optional[str]) -> Optional[Agenda]:
    return AGENDAS.get(agenda_id or "")


# ------------------------------------------------------------- law effects
def research_surcharge(laws: Dict[str, str]) -> int:
    """Extra resource cost per research action."""
    if laws.get("anti_intellectual_revolution") == FOR:
        return RESEARCH_SURCHARGE
    return 0


def token_maximum(laws: Dict[str, str], default: int) -> int:
    if laws.get("fleet_regulations") == FOR:
        return min(default, RESTRICTED_TOKEN_MAXIMUM)
    return default


def income_bonus(laws: Dict[str, str], player_name: str) -> int:
    if laws.get("minister_of_industry") == player_name:
        return MINISTER_INCOME
    return 0


def tally(votes: Dict[str, dict], tiebreak: Sequence[str]) -> Optional[str]:
    """Outcome with the most influence; ties are broken in ``tiebreak`` order."""
    totals: Dict[str, int] = {}
    for vote in votes.values():
        outcome = vote["outcome"]
        totals[outcome] = totals.get(outcome, 0) + int(vote["influence"])
    if not totals:
        return None
    best = max(totals.values())
    winners = [outcome for outcome, total in totals.items() if total == best]
    for candidate in tiebreak:
        if candidate in winners:
            return candidate
    return sorted(winners)[0]
