"""Round structure and turn order.

A round consists of three phases:

``strategy``  every player picks a strategy card in speaker order
``action``    players take turns in initiative order until everybody passed
``status``    scoring/cleanup, the speaker token moves on and a new round starts

The turn manager only tracks *who may act*; the effects of actions live in
:mod:`ti.engine` and :mod:`ti.game`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


class Phase:
    STRATEGY = "strategy"
    ACTION = "action"
    STATUS = "status"
    FINISHED = "finished"


@dataclass
class TurnManager:
    player_names: List[str]
    round: int = 1
    phase: str = Phase.STRATEGY
    speaker_index: int = 0
    turn_index: int = 0
    order: List[str] = field(default_factory=list)
    passed: List[str] = field(default_factory=list)

    # ------------------------------------------------------------- strategy
    def strategy_order(self) -> List[str]:
        count = len(self.player_names)
        return [
            self.player_names[(self.speaker_index + i) % count] for i in range(count)
        ]

    @property
    def speaker(self) -> Optional[str]:
        if not self.player_names:
            return None
        return self.player_names[self.speaker_index % len(self.player_names)]

    @property
    def current_player(self) -> Optional[str]:
        if self.phase == Phase.STRATEGY:
            order = self.strategy_order()
            if self.turn_index < len(order):
                return order[self.turn_index]
            return None
        if self.phase == Phase.ACTION and self.order:
            return self.order[self.turn_index % len(self.order)]
        return None

    def strategy_picked(self) -> None:
        """Advance the strategy phase after a player picked a card."""
        self.turn_index += 1
        if self.turn_index >= len(self.player_names):
            self.begin_action_phase()

    def begin_action_phase(self, initiative: Optional[Dict[str, int]] = None) -> None:
        initiative = initiative or {}
        self.order = sorted(
            self.player_names,
            key=lambda name: (initiative.get(name, 99), self.player_names.index(name)),
        )
        self.phase = Phase.ACTION
        self.turn_index = 0
        self.passed = []

    # --------------------------------------------------------------- action
    def active_players(self) -> List[str]:
        return [name for name in self.order if name not in self.passed]

    def advance_turn(self) -> None:
        if not self.order:
            return
        for step in range(1, len(self.order) + 1):
            candidate = self.order[(self.turn_index + step) % len(self.order)]
            if candidate not in self.passed:
                self.turn_index = (self.turn_index + step) % len(self.order)
                return
        self.phase = Phase.STATUS

    def mark_passed(self, player: str) -> None:
        if player not in self.passed:
            self.passed.append(player)
        if len(self.passed) >= len(self.order):
            self.phase = Phase.STATUS
        else:
            self.advance_turn()

    # --------------------------------------------------------------- status
    def begin_next_round(self) -> None:
        self.round += 1
        self.phase = Phase.STRATEGY
        self.speaker_index = (
            (self.speaker_index + 1) % len(self.player_names)
            if self.player_names
            else 0
        )
        self.turn_index = 0
        self.order = []
        self.passed = []

    def finish(self) -> None:
        self.phase = Phase.FINISHED

    # ---------------------------------------------------------------- state
    def to_dict(self) -> dict:
        return {
            "round": self.round,
            "phase": self.phase,
            "speaker": self.speaker,
            "current_player": self.current_player,
            "order": list(self.order),
            "passed": list(self.passed),
        }

    @staticmethod
    def from_dict(data: dict, player_names: List[str]) -> "TurnManager":
        manager = TurnManager(player_names)
        manager.round = data.get("round", 1)
        manager.phase = data.get("phase", Phase.STRATEGY)
        manager.order = list(data.get("order", []))
        manager.passed = list(data.get("passed", []))
        speaker = data.get("speaker")
        if speaker in player_names:
            manager.speaker_index = player_names.index(speaker)
        current = data.get("current_player")
        reference = manager.order if manager.phase == Phase.ACTION else manager.strategy_order()
        if current in reference:
            manager.turn_index = reference.index(current)
        return manager
