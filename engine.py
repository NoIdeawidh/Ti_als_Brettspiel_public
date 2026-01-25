# sub/engine.py
import os, json, uuid
from typing import Dict, Any
from .game import Game

SAVE_DIR = os.path.join(os.path.dirname(__file__), "..", "saves")
os.makedirs(SAVE_DIR, exist_ok=True)

class GameManager:
    def __init__(self):
        self.games: Dict[str, Game] = {}

    def new_gid(self):
        return "g_" + uuid.uuid4().hex[:10]

    def create_game(self, players, factions:Dict[str,str]=None, seed=None):
        gid = self.new_gid()
        g = Game(players, factions, seed=seed)
        self.games[gid] = g
        return gid

    def get_game(self, gid):
        return self.games.get(gid)

    def list_games(self):
        return list(self.games.keys())

    # Save/load to disk
    def save_game(self, gid, name=None):
        g = self.get_game(gid)
        if not g: return None
        save_obj = {"meta": {"name": name or gid}, "game": g.serialize()}
        fname = (name or gid).replace(" ","_") + "_" + gid + ".json"
        path = os.path.join(SAVE_DIR, fname)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(save_obj, f, indent=2)
        return path

    def list_saves(self):
        out=[]
        for f in os.listdir(SAVE_DIR):
            if f.endswith(".json"):
                p=os.path.join(SAVE_DIR,f)
                try:
                    with open(p,"r",encoding="utf-8") as fh:
                        meta = json.load(fh).get("meta",{})
                    out.append({"file":f, "path":p, "meta":meta})
                except:
                    continue
        return out

    def load_save(self, filename):
        p = os.path.join(SAVE_DIR, filename)
        if not os.path.exists(p): return None
        with open(p,"r",encoding="utf-8") as f:
            obj=json.load(f)
        # For now, create a fresh Game shell from serialized minimal info (prototype)
        players = [pl["name"] for pl in obj["game"].get("players",[])]
        factions = {pl["name"]:pl.get("faction","Federation") for pl in obj["game"].get("players",[])}
        g = Game(players, factions, seed=obj["game"].get("seed"))
        # Attempt to set round and basic fields
        g.round = obj["game"].get("round",0)
        g.history = obj["game"].get("history",[])[:200]
        self.games["loaded_"+uuid.uuid4().hex[:6]] = g
        gid = [k for k,v in self.games.items() if v==g][0]
        return gid
