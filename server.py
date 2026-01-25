from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import uuid

from game import Game

# -----------------------
# App Setup
# -----------------------
app = Flask(__name__, static_folder=".")
CORS(app)

# -----------------------
# Game Manager
# -----------------------
class GameManager:
    def __init__(self):
        self.games = {}

    def create_game(self, players):
        gid = str(uuid.uuid4())
        self.games[gid] = Game(players)
        return gid

    def get_game(self, gid):
        return self.games.get(gid)


gm = GameManager()

# -----------------------
# Static Pages
# -----------------------
@app.route("/")
def lobby():
    return send_from_directory(".", "lobby.html")

@app.route("/game")
def game_page():
    return send_from_directory(".", "index.html")

# -----------------------
# API ROUTES
# -----------------------

@app.route("/api/create", methods=["POST"])
def api_create():
    data = request.json or {}
    players = data.get("players", ["Player 1", "Player 2"])
    gid = gm.create_game(players)
    return jsonify({"ok": True, "game_id": gid})


@app.route("/api/state", methods=["GET"])
def api_state():
    gid = request.args.get("game_id")
    game = gm.get_game(gid)
    if not game:
        return jsonify({"ok": False, "error": "game not found"})
    return jsonify({"ok": True, **game.to_dict()})


@app.route("/api/move", methods=["POST"])
def api_move():
    data = request.json or {}
    game = gm.get_game(data.get("game_id"))
    if not game:
        return jsonify({"ok": False, "error": "game not found"})

    result = game.api_move(
        player=data.get("player"),
        action=data.get("action")
    )
    return jsonify(result)


@app.route("/api/produce", methods=["POST"])
def api_produce():
    data = request.json or {}
    game = gm.get_game(data.get("game_id"))
    if not game:
        return jsonify({"ok": False, "error": "game not found"})

    ok = game.produce(
        player=data.get("player"),
        unit_type=data.get("unit_type"),
        system_id=data.get("system_id")
    )
    return jsonify({"ok": ok})


@app.route("/api/space_combat/get", methods=["POST"])
def api_get_combat():
    data = request.json or {}
    game = gm.get_game(data.get("game_id"))
    if not game:
        return jsonify({"ok": False})

    combat = game.pending_combats.get(data.get("system_id"))
    return jsonify({"ok": True, "combat": combat})


@app.route("/api/space_combat/resolve", methods=["POST"])
def api_resolve_combat():
    data = request.json or {}
    game = gm.get_game(data.get("game_id"))
    if not game:
        return jsonify({"ok": False})

    result = game.api_apply_combat_assignments(
        system_id=data.get("system_id"),
        attacker_losses=data.get("attacker_losses", []),
        defender_losses=data.get("defender_losses", [])
    )
    return jsonify(result)


@app.route("/api/next_round", methods=["POST"])
def api_next_round():
    data = request.json or {}
    game = gm.get_game(data.get("game_id"))
    if not game:
        return jsonify({"ok": False})

    game.next_round()
    return jsonify({"ok": True})


# -----------------------
# Entry Point
# -----------------------
if __name__ == "__main__":
    app.run(debug=True)
