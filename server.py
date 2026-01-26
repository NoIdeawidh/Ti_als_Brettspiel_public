from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import random

from game import Game

app = Flask(__name__, static_folder="static", static_url_path="/static")
CORS(app)

games = {}

@app.route("/")
def lobby():
    return send_from_directory(".", "lobby.html")

@app.route("/game")
def game_page():
    return send_from_directory(".", "index.html")

@app.route("/api/create", methods=["POST"])
def create_game():
    try:
        data = request.get_json(force=True)

        raw_players = data.get("players", [])
        factions_map = data.get("factionsMap", {})

        players = []
        for p in raw_players:
            name = p["name"] if isinstance(p, dict) else p

            players.append({
                "name": name,
                "faction": factions_map.get(name, "Federation"),
                "resources": 3,
                "influence": 1,
                "planets": [],
                "ships": [],
                "strategy_card": None,
                "vp": 0
            })

        # --- SYSTEM SETUP ---
        systems = [
            {
                "id": "s_mec",
                "planets": [{
                    "name": "Mecatol Rex",
                    "resources": 0,
                    "influence": 6,
                    "controller": None,
                    "home": False
                }],
                "ships": {}
            }
        ]

        for p in players:
            sid = f"s_{p['name'].lower()[:5]}"
            home_planet = p["name"] + " Prime"

            p["planets"].append(home_planet)

            systems.append({
                "id": sid,
                "planets": [{
                    "name": home_planet,
                    "resources": 2,
                    "influence": 1,
                    "controller": p["name"],
                    "home": True
                }],
                "ships": {
                    p["name"]: [
                        {
                            "uid": f"{p['name']}-carrier",
                            "type": "Carrier",
                            "combat": 1,
                            "owner": p["name"]
                        },
                        {
                            "uid": f"{p['name']}-cruiser",
                            "type": "Cruiser",
                            "combat": 2,
                            "owner": p["name"]
                        }
                    ]
                }
            })

        g = Game(players, systems, random.randint(0, 999999))
        games[g.id] = g

        return jsonify({
            "ok": True,
            "game_id": g.id
        })

    except Exception as e:
        # 🔥 ABSOLUT KRITISCH FÜR DEBUG
        print("CREATE GAME ERROR:", repr(e))
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500


@app.route("/api/state")
def state():
    gid = request.args.get("game_id")
    g = games.get(gid)
    if not g:
        return jsonify({"ok": False, "error": "game not found"})
    return jsonify(g.to_dict())


@app.route("/api/move", methods=["POST"])
def move():
    data = request.json
    g = games.get(data.get("game_id"))
    if not g:
        return jsonify({"ok": False, "error": "game not found"})

    ok, msg = g.apply_action(
        data.get("player"),
        data.get("action")
    )

    return jsonify({"ok": ok, "msg": msg})


if __name__ == "__main__":
    app.run(debug=True)
