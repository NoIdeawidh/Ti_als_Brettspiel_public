"""HTTP API and static file server.

The HTTP layer only translates JSON to engine calls - all rules live in the
:mod:`ti` package.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from ti.agenda import AGENDA_LIST
from ti.cards import STRATEGY_CARD_LIST
from ti.game import Game
from ti.objectives import OBJECTIVE_DECK
from ti.store import GameStore
from ti.tech import TECHNOLOGY_LIST
from ti.units import UNIT_TYPES

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SAVE_DIR = BASE_DIR / "saves"

log = logging.getLogger(__name__)


def create_app(save_dir: Optional[Path] = DEFAULT_SAVE_DIR) -> Flask:
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    CORS(app)
    store = GameStore(save_dir)
    app.config["GAME_STORE"] = store

    # ------------------------------------------------------------- pages
    @app.route("/")
    def lobby():
        return send_from_directory(BASE_DIR, "lobby.html")

    @app.route("/game")
    def game_page():
        return send_from_directory(BASE_DIR, "index.html")

    # -------------------------------------------------------------- meta
    @app.route("/api/unit_types")
    def unit_types():
        return jsonify({"ok": True, "unit_types": [u.to_dict() for u in UNIT_TYPES.values()]})

    @app.route("/api/strategy_cards")
    def strategy_cards():
        return jsonify({"ok": True, "cards": [c.to_dict() for c in STRATEGY_CARD_LIST]})

    @app.route("/api/objectives")
    def objectives():
        return jsonify(
            {"ok": True, "objectives": [o.to_dict() for o in OBJECTIVE_DECK]}
        )

    @app.route("/api/technologies")
    def technologies():
        return jsonify(
            {"ok": True, "technologies": [t.to_dict() for t in TECHNOLOGY_LIST]}
        )

    @app.route("/api/agendas")
    def agendas():
        return jsonify({"ok": True, "agendas": [a.to_dict() for a in AGENDA_LIST]})

    @app.route("/api/games")
    def list_games():
        return jsonify({"ok": True, "games": store.list_games()})

    # ------------------------------------------------------------- games
    @app.route("/api/create", methods=["POST"])
    def create_game():
        data = request.get_json(force=True, silent=True) or {}
        try:
            game = Game.create(
                data.get("players", []),
                data.get("factionsMap") or data.get("factions"),
                data.get("seed"),
            )
        except (ValueError, KeyError, TypeError) as exc:
            log.warning("create game failed: %r", exc)
            return jsonify({"ok": False, "error": str(exc)}), 400
        store.add(game)
        return jsonify({"ok": True, "game_id": game.id})

    @app.route("/api/state")
    def state():
        game = store.get(request.args.get("game_id"))
        if game is None:
            return jsonify({"ok": False, "error": "game not found"}), 404
        return jsonify(game.to_dict())

    @app.route("/api/action", methods=["POST"])
    def action():
        data = request.get_json(force=True, silent=True) or {}
        game = store.get(data.get("game_id"))
        if game is None:
            return jsonify({"ok": False, "error": "game not found"}), 404

        result = game.apply_action(data.get("player"), data.get("action") or {})
        if result.ok:
            store.save(game)
        return jsonify(result.to_dict())

    @app.route("/api/move", methods=["POST"])
    def move():
        """Legacy endpoint kept for older clients."""
        data = request.get_json(force=True, silent=True) or {}
        game = store.get(data.get("game_id"))
        if game is None:
            return jsonify({"ok": False, "error": "game not found"}), 404
        result = game.apply_action(data.get("player"), data.get("action") or {})
        if result.ok:
            store.save(game)
        return jsonify(result.to_dict())

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
