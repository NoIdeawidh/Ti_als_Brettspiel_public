# sub/server.py
# Vollständiger Flask + Flask-SocketIO Server mit einfacher Game-Engine
import os
import json
import uuid
import random
import traceback
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, request, render_template, send_from_directory, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room

BASE = Path(__file__).resolve().parents[1]
SAVES_DIR = BASE / "saves"
SAVES_DIR.mkdir(exist_ok=True)

# Simple in-memory game manager
GAMES = {}  # game_id -> Game instance

def gen_id(prefix='g'):
    return f"{prefix}_{uuid.uuid4().hex[:10]}"

def now_iso():
    return datetime.utcnow().isoformat() + 'Z'

# --- Game model ---
class Unit:
    def __init__(self, utype, owner):
        self.uid = "u_" + uuid.uuid4().hex[:8]
        self.type = utype
        self.owner = owner

    def to_dict(self):
        return {"uid": self.uid, "type": self.type, "owner": self.owner}

class System:
    def __init__(self, sys_id, name):
        self.id = sys_id
        self.name = name
        self.ships = {}  # player -> list of Unit
        self.planets = [{"name": f"{name} Prime"}]

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "planets": self.planets,
            "ships": {p: [u.to_dict() for u in lst] for p, lst in self.ships.items()}
        }

class Game:
    def __init__(self, players=None, factions=None, seed=None):
        self.id = gen_id("g")
        self.created = now_iso()
        self.round = 1
        self.players = []  # list of player names
        self.factions = factions or {}
        if players:
            for p in players:
                self.players.append({"name": p})
        self.systems = self._init_systems()
        self.history = []
        self.pending_combats = {}  # system_id -> pending object
        self.strategies = {}  # player -> chosen card
        self.current_player = self.players[0]["name"] if self.players else None
        self.seed = seed or random.randint(0, 10_000_000)
        random.seed(self.seed)
        # place a starter unit for each player on s_mec to make tokens visible
        for p in [px["name"] for px in self.players]:
            u = Unit("Carrier", p)
            self._put_unit_in_system("s_mec", u)

    def _init_systems(self):
        items = [
            ("s_mec", "Mecatol Rex"),
            ("s_alpha", "Alpha"),
            ("s_beta", "Beta"),
            ("s_gamma", "Gamma"),
            ("s_delta", "Delta")
        ]
        return {sid: System(sid, name) for sid, name in items}

    def _put_unit_in_system(self, sys_id, unit):
        s = self.systems.get(sys_id)
        if not s: return False
        if unit.owner not in s.ships:
            s.ships[unit.owner] = []
        s.ships[unit.owner].append(unit)
        return True

    def to_dict(self):
        return {
            "game_id": self.id,
            "created": self.created,
            "round": self.round,
            "players": [p for p in (self.players or [])],
            "factions": self.factions,
            "systems": [self.systems[s].to_dict() for s in self.systems],
            "history": list(self.history),
            "pending_combats": self.pending_combats,
            "strategies": self.strategies,
            "current_player": self.current_player,
            "seed": self.seed
        }

    def find_unit(self, uid):
        for sys in self.systems.values():
            for owner, lst in sys.ships.items():
                for u in lst:
                    if u.uid == uid:
                        return sys.id, u
        return None, None

    def move_unit(self, player, uid, to_sys):
        from_sys_id, unit = self.find_unit(uid)
        if not unit:
            return {"ok": False, "error": "unit_not_found"}
        if unit.owner != player:
            return {"ok": False, "error": "not_unit_owner"}
        if to_sys not in self.systems:
            return {"ok": False, "error": "to_system_unknown"}
        if from_sys_id == to_sys:
            return {"ok": True, "moved": False}
        # remove from origin
        origin = self.systems[from_sys_id]
        origin.ships[unit.owner] = [u for u in origin.ships.get(unit.owner, []) if u.uid != uid]
        # check for enemy presence
        target = self.systems[to_sys]
        enemy_players = [p for p in target.ships.keys() if p != player and len(target.ships.get(p, []))>0]
        if enemy_players:
            # create pending combat object
            attacker_units = [unit.to_dict()]
            defender_units = []
            # copy defender units present
            for ep in enemy_players:
                defender_units += [u.to_dict() for u in target.ships.get(ep, [])]
            pending = {
                "system_id": to_sys,
                "attacker": player,
                "defender": enemy_players[0],
                "attacker_units": attacker_units,
                "defender_units": defender_units,
                # simplistic hit calculation (prototype)
                "attacker_hits": max(1, len(attacker_units)//1),
                "defender_hits": max(1, len(defender_units)//2)
            }
            self.pending_combats[to_sys] = pending
            self.history.append(f"{now_iso()} - {player} moved {unit.type} to {to_sys} — combat pending")
            return {"ok": True, "combat_pending": True, "system": to_sys}
        else:
            # no combat, place unit
            self._put_unit_in_system(to_sys, unit)
            self.history.append(f"{now_iso()} - {player} moved {unit.type} from {from_sys_id} to {to_sys}")
            return {"ok": True, "combat_pending": False, "system": to_sys}

    def resolve_combat(self, system_id, attacker_losses, defender_losses):
        if system_id not in self.pending_combats:
            return {"ok": False, "error": "no_pending_for_system"}
        pending = self.pending_combats[system_id]
        sys = self.systems.get(system_id)
        if not sys:
            return {"ok": False, "error": "system_unknown"}

        # remove units by uid from the respective owner lists
        removed = {"attacker": [], "defender": []}
        # attacker losses: the moved unit(s) belong to pending.attacker
        for uid in attacker_losses or []:
            # attackers may not yet be present as Unit instances in system (they were moved)
            # just ensure any matching uid in systems removed
            for owner, lst in list(sys.ships.items()):
                newlst = [u for u in lst if u.uid != uid]
                if len(newlst) != len(lst):
                    sys.ships[owner] = newlst
                    removed["attacker"].append(uid)
        # defender losses
        for uid in defender_losses or []:
            for owner, lst in list(sys.ships.items()):
                if owner == pending.get("defender"):
                    newlst = [u for u in lst if u.uid != uid]
                    if len(newlst) != len(lst):
                        sys.ships[owner] = newlst
                        removed["defender"].append(uid)

        # if any attacker unit still missing from target (the moved unit wasn't added), attempt to add it
        # (Note: in our simple flow the moved unit wasn't inserted automatically to allow pending logic; ensure at least attacker units get placed if not removed)
        # We'll create placeholder units for any attacker uids not removed:
        for au in pending.get("attacker_units", []):
            uid = au.get("uid")
            exists = any(u.uid == uid for lst in sys.ships.values() for u in lst)
            if not exists and uid not in removed["attacker"]:
                # create a placeholder unit with same type and owner
                nu = Unit(au.get("type","Infantry"), au.get("owner", pending.get("attacker")))
                nu.uid = uid
                self._put_unit_in_system(system_id, nu)

        # cleanup pending
        del self.pending_combats[system_id]
        self.history.append(f"{now_iso()} - Combat at {system_id} resolved; removed {removed}")
        return {"ok": True, "removed": removed}

    def produce_unit(self, player, unit_type, system_id=None):
        # place produced unit at a player's home system; for simplicity, use s_mec if no system specified
        home = system_id if system_id in self.systems else "s_mec"
        u = Unit(unit_type, player)
        self._put_unit_in_system(home, u)
        self.history.append(f"{now_iso()} - {player} produced {unit_type} at {home}")
        return {"ok": True, "uid": u.uid}

    def pick_strategy(self, player, card):
        # simple assignment, no validation for uniqueness for prototype
        self.strategies[player] = int(card)
        self.history.append(f"{now_iso()} - {player} picked strategy {card}")
        return {"ok": True}

    def save_to_file(self, filename):
        obj = self.to_dict()
        path = SAVES_DIR / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        return str(path)

    @staticmethod
    def load_from_file(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        g = Game(players=[p["name"] for p in data.get("players", [])], factions=data.get("factions", {}), seed=data.get("seed"))
        # override id and created to keep loaded meta
        g.id = data.get("game_id", gen_id("g"))
        g.created = data.get("created", now_iso())
        g.round = data.get("round", 1)
        g.history = data.get("history", [])
        g.strategies = data.get("strategies", {})
        g.current_player = data.get("current_player", g.current_player)
        # reconstruct systems and units
        # clear systems then fill from data
        g.systems = {}
        for s in data.get("systems", []):
            sys = System(s["id"], s.get("name", s["id"]))
            sys.planets = s.get("planets", sys.planets)
            for p, units in (s.get("ships") or {}).items():
                sys.ships[p] = []
                for u in units:
                    nu = Unit(u.get("type", "Infantry"), p)
                    nu.uid = u.get("uid", "u_" + uuid.uuid4().hex[:8])
                    sys.ships[p].append(nu)
            g.systems[sys.id] = sys
        return g

# --- Flask app factory and routes ---
def create_app():
    app = Flask(__name__, static_folder=str(BASE / "static"), template_folder=str(BASE / "templates"))
    app.config['SECRET_KEY'] = 'dev-key'
    app.logger.setLevel("DEBUG")

    @app.route("/")
    def index_root():
        return redirect(url_for("lobby"))

    @app.route("/lobby")
    def lobby():
        return render_template("lobby.html")

    @app.route("/game")
    def game_page():
        gid = request.args.get("game_id", "")
        return render_template("index.html", game_id=gid)

    @app.route("/static/<path:path>")
    def static_files(path):
        return send_from_directory(str(BASE / "static"), path)

    # API: create
    @app.route("/api/create", methods=["POST"])
    def api_create():
        try:
            data = request.get_json(force=True, silent=True) or {}
            players = data.get("players") or []
            factions = data.get("factions") or {}
            seed = data.get("seed", None)
            app.logger.debug("api_create payload: %s", data)
            g = Game(players=players, factions=factions, seed=seed)
            GAMES[g.id] = g
            # return initial state
            return jsonify({"ok": True, "game_id": g.id, "state": g.to_dict()})
        except Exception as e:
            tb = traceback.format_exc()
            app.logger.error(tb)
            return jsonify({"ok": False, "trace": tb}), 500

    @app.route("/api/state")
    def api_state():
        gid = request.args.get("game_id") or request.args.get("game") or request.args.get("id")
        if not gid:
            return jsonify({"ok": False, "error": "missing_game_id"}), 400
        g = GAMES.get(gid)
        if not g:
            return jsonify({"ok": False, "error": "no game"}), 404
        return jsonify(g.to_dict())

    @app.route("/api/move", methods=["POST"])
    def api_move():
        try:
            data = request.get_json(force=True, silent=True) or {}
            game_id = data.get("game_id")
            player = data.get("player")
            action = data.get("action") or {}
            if not game_id or not player or not action:
                return jsonify({"ok": False, "error": "missing_parameters"}), 400
            g = GAMES.get(game_id)
            if not g:
                return jsonify({"ok": False, "error": "game_not_found"}), 404
            # action: {type:'move', from, to, unit_uid}
            if action.get("type") != "move":
                return jsonify({"ok": False, "error": "unknown_action"}), 400
            uid = action.get("unit_uid")
            to_sys = action.get("to")
            res = g.move_unit(player, uid, to_sys)
            return jsonify(res)
        except Exception as e:
            tb = traceback.format_exc()
            app.logger.error(tb)
            return jsonify({"ok": False, "trace": tb}), 500

    @app.route("/api/space_combat/get", methods=["POST"])
    def api_space_combat_get():
        try:
            data = request.get_json(force=True, silent=True) or {}
            game_id = data.get("game_id")
            system_id = data.get("system_id")
            if not game_id or not system_id:
                return jsonify({"ok": False, "error": "missing_parameters"}), 400
            g = GAMES.get(game_id)
            if not g:
                return jsonify({"ok": False, "error": "game_not_found"}), 404
            pending = g.pending_combats.get(system_id)
            if not pending:
                return jsonify({"ok": False, "error": "no_pending"}), 404
            return jsonify({"ok": True, "pending": pending})
        except Exception as e:
            tb = traceback.format_exc()
            app.logger.error(tb)
            return jsonify({"ok": False, "trace": tb}), 500

    @app.route("/api/space_combat/resolve", methods=["POST"])
    def api_space_combat_resolve():
        try:
            data = request.get_json(force=True, silent=True) or {}
            game_id = data.get("game_id")
            system_id = data.get("system_id")
            attacker_losses = data.get("attacker_losses", [])
            defender_losses = data.get("defender_losses", [])
            if not game_id or not system_id:
                return jsonify({"ok": False, "error": "missing_parameters"}), 400
            g = GAMES.get(game_id)
            if not g:
                return jsonify({"ok": False, "error": "game_not_found"}), 404
            res = g.resolve_combat(system_id, attacker_losses, defender_losses)
            return jsonify(res)
        except Exception as e:
            tb = traceback.format_exc()
            app.logger.error(tb)
            return jsonify({"ok": False, "trace": tb}), 500

    @app.route("/api/produce", methods=["POST"])
    def api_produce():
        try:
            data = request.get_json(force=True, silent=True) or {}
            game_id = data.get("game_id")
            player = data.get("player")
            unit_type = data.get("unit_type", "Infantry")
            if not game_id or not player:
                return jsonify({"ok": False, "error": "missing_parameters"}), 400
            g = GAMES.get(game_id)
            if not g:
                return jsonify({"ok": False, "error": "game_not_found"}), 404
            res = g.produce_unit(player, unit_type)
            return jsonify(res)
        except Exception as e:
            tb = traceback.format_exc()
            app.logger.error(tb)
            return jsonify({"ok": False, "trace": tb}), 500

    @app.route("/api/strategy_pick", methods=["POST"])
    def api_strategy_pick():
        try:
            data = request.get_json(force=True, silent=True) or {}
            game_id = data.get("game_id")
            player = data.get("player")
            card = data.get("card")
            if not game_id or not player or card is None:
                return jsonify({"ok": False, "error": "missing_parameters"}), 400
            g = GAMES.get(game_id)
            if not g:
                return jsonify({"ok": False, "error": "game_not_found"}), 404
            if player not in [p["name"] for p in g.players]:
                return jsonify({"ok": False, "error": "player_not_in_game"}), 403
            res = g.pick_strategy(player, card)
            return jsonify({"ok": True, "state": g.to_dict()})
        except Exception as e:
            tb = traceback.format_exc()
            app.logger.error(tb)
            return jsonify({"ok": False, "trace": tb}), 500

    @app.route("/api/save", methods=["POST"])
    def api_save():
        try:
            data = request.get_json(force=True, silent=True) or {}
            game_id = data.get("game_id")
            name = data.get("name") or f"save_{game_id}_{int(datetime.utcnow().timestamp())}.json"
            g = GAMES.get(game_id)
            if not g:
                return jsonify({"ok": False, "error": "game_not_found"}), 404
            path = g.save_to_file(name)
            return jsonify({"ok": True, "path": path, "file": name})
        except Exception as e:
            tb = traceback.format_exc()
            app.logger.error(tb)
            return jsonify({"ok": False, "trace": tb}), 500

    @app.route("/api/list_saves")
    def api_list_saves():
        files = []
        for f in sorted(SAVES_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if f.is_file() and f.suffix == ".json":
                files.append({"file": f.name, "modified": f.stat().st_mtime})
        return jsonify({"ok": True, "saves": files})

    @app.route("/api/load", methods=["POST"])
    def api_load():
        try:
            data = request.get_json(force=True, silent=True) or {}
            file = data.get("file")
            if not file:
                return jsonify({"ok": False, "error": "missing_file"}), 400
            path = SAVES_DIR / file
            if not path.exists():
                return jsonify({"ok": False, "error": "file_not_found"}), 404
            g = Game.load_from_file(str(path))
            GAMES[g.id] = g
            return jsonify({"ok": True, "game_id": g.id, "state": g.to_dict()})
        except Exception as e:
            tb = traceback.format_exc()
            app.logger.error(tb)
            return jsonify({"ok": False, "trace": tb}), 500

    return app

# create socketio object for run.py to import
app_for_socket = create_app()
socketio = SocketIO(app_for_socket, cors_allowed_origins="*")
