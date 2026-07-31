"""Game storage.

Games are kept in memory and mirrored to JSON files so that a server restart
does not lose running games.  The interface is intentionally small so that a
database backed store can be dropped in later.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from ti.game import Game


class GameStore:
    def __init__(self, save_dir: Optional[Path] = None) -> None:
        self.save_dir = Path(save_dir) if save_dir else None
        self._games: Dict[str, Game] = {}
        if self.save_dir:
            self.save_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, game_id: str) -> Optional[Path]:
        return self.save_dir / f"{game_id}.json" if self.save_dir else None

    def add(self, game: Game) -> Game:
        self._games[game.id] = game
        self.save(game)
        return game

    def save(self, game: Game) -> None:
        path = self._path(game.id)
        if path is None:
            return
        path.write_text(json.dumps(game.to_dict(), indent=2), encoding="utf-8")

    def get(self, game_id: Optional[str]) -> Optional[Game]:
        if not game_id:
            return None
        game = self._games.get(game_id)
        if game is not None:
            return game
        path = self._path(game_id)
        if path and path.exists():
            game = Game.from_dict(json.loads(path.read_text(encoding="utf-8")))
            self._games[game.id] = game
            return game
        return None

    def list_games(self) -> List[dict]:
        summaries = {
            game.id: {
                "game_id": game.id,
                "round": game.round,
                "phase": game.turns.phase,
                "players": [p.name for p in game.players],
            }
            for game in self._games.values()
        }
        if self.save_dir:
            for path in sorted(self.save_dir.glob("*.json")):
                if path.stem in summaries:
                    continue
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                summaries[path.stem] = {
                    "game_id": data.get("game_id", path.stem),
                    "round": data.get("round", 0),
                    "phase": data.get("phase"),
                    "players": [p["name"] for p in data.get("players", [])],
                }
        return list(summaries.values())
