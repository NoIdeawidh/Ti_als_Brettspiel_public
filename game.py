# sub/game.py
# Kern-Game-Model: Fraktionen, Einheiten, Systeme, Combat, Produktion, Strategy, Save-Helper

from typing import List, Dict, Any, Optional
import random, uuid, json

def new_uid(prefix=None):
    return (prefix + "-" if prefix else "") + uuid.uuid4().hex[:8]

# ------------------------------
# FRANCHISE / UNITS / COSTS
# ------------------------------
FACTIONS = {
    "Arborec": {"desc":"Plant faction (prototype)", "home_bonus": {"resources":1}},
    "Sardakk": {"desc":"Combat-focused (prototype)", "combat_buff":1},
    "Federation": {"desc":"Balanced", "resources":0},
    "Clan": {"desc":"Mobility", "move_bonus":1}
}

UNIT_DEFS = {
    "Infantry": {"combat":1,"move":0,"cost":1,"space":False},
    "Cruiser": {"combat":2,"move":1,"cost":2,"space":True},
    "Carrier": {"combat":1,"move":1,"cost":3,"space":True,"capacity":4},
    "Destroyer": {"combat":3,"move":1,"cost":2,"space":True}
}

PRODUCTION_COSTS = {k: UNIT_DEFS[k]["cost"] for k in UNIT_DEFS}

# ------------------------------
# Domain Classes
# ------------------------------
class Unit:
    def __init__(self, owner: 'Player', uid: str, type_name: str):
        self.owner = owner
        self.uid = uid
        self.type_name = type_name
        ud = UNIT_DEFS.get(type_name, {})
        self.combat = ud.get("combat",1)
        self.move = ud.get("move",1)
        self.capacity = ud.get("capacity",0)
        self.space = ud.get("space", True)
        self.hits = ud.get("hits",1)

    def to_dict(self):
        return {"uid": self.uid, "type": self.type_name, "owner": self.owner.name, "combat":self.combat}

class Planet:
    def __init__(self, name:str, res:int=0, inf:int=0, home=False):
        self.name = name
        self.resources = res
        self.influence = inf
        self.home = home
        self.controller: Optional['Player'] = None

    def to_dict(self):
        return {"name":self.name,"resources":self.resources,"influence":self.influence,"home":self.home,"controller": self.controller.name if self.controller else None}

class System:
    def __init__(self, id:str, planets:Optional[List[Planet]]=None):
        self.id = id
        self.planets = planets or []
        # ships: mapping from player-name to list of Unit dicts
        self.ships: Dict[str, List[Unit]] = {}

    def to_dict(self):
        return {"id":self.id,"planets":[p.to_dict() for p in self.planets],"ships": {k:[u.to_dict() for u in v] for k,v in self.ships.items()} }

class Player:
    def __init__(self, name:str, faction:str="Federation"):
        self.name = name
        self.faction = faction
        self.resources = 0
        self.influence = 0
        self.vp = 0
        self.planets: List[Planet] = []
        self.ships: List[Unit] = []
        self.command_tokens = {"strategy":1, "fleet":2, "tactics":2}
        self.strategy_card = None
        # temporary buffs
        self.combat_buff = FACTIONS.get(faction, {}).get("combat_buff", 0)
        self.move_bonus = FACTIONS.get(faction, {}).get("move_bonus", 0)

    def to_dict(self):
        return {"name":self.name,"faction":self.faction,"resources":self.resources,"influence":self.influence,"vp":self.vp,"planets":[p.name for p in self.planets],"ships":[s.uid for s in self.ships],"strategy_card":self.strategy_card}

# ------------------------------
# Game
# ------------------------------
class Game:
    def __init__(self, players: List[str], factions: Optional[Dict[str,str]]=None, seed: Optional[int]=None):
        self.seed = seed if seed is not None else random.randrange(1<<30)
        self.rng = random.Random(self.seed)
        # players arg is list of player names
        self.players: List[Player] = []
        factions = factions or {}
        for n in players:
            fac = factions.get(n, "Federation")
            p = Player(n, faction=fac)
            self.players.append(p)
        self.systems: List[System] = []
        self.round = 0
        self.history: List[str] = []
        self._unit_index: Dict[str, Unit] = {}
        self.pending_combats: Dict[str, Dict[str,Any]] = {}
        self.init_board()
        self.init_objectives()
        self.history.append(f"Game created seed={self.seed}")

    def _index_unit(self,u:Unit):
        self._unit_index[u.uid] = u

    def find_player(self,name)->Optional[Player]:
        for p in self.players:
            if p.name==name: return p
        return None

    def init_board(self):
        # small board, with realistic looking planets later in front-end
        s0 = System("s_mec",[Planet("Mecatol Rex",res=0,inf=6)])
        s1 = System("s_alpha",[Planet("Alpha",res=2,inf=1,home=True)])
        s2 = System("s_beta",[Planet("Beta",res=1,inf=2)])
        s3 = System("s_gamma",[Planet("Gamma",res=2,inf=1)])
        self.systems = [s0,s1,s2,s3]
        # distribute homes
        for i,p in enumerate(self.players):
            idx = (i+1) % len(self.systems)
            home = self.systems[idx].planets[0]
            home.controller = p
            p.planets.append(home)
            # starting resources/influence based on planet
            p.resources = max(1, home.resources + 1)
            p.influence = max(0, home.influence)
            # Add starter ships
            c = Unit(p, new_uid(p.name+"-carrier"), "Carrier")
            r = Unit(p, new_uid(p.name+"-cruiser"), "Cruiser")
            p.ships.extend([c,r])
            self._index_unit(c); self._index_unit(r)
            self.systems[idx].ships.setdefault(p.name,[]).extend([c,r])
            self.history.append(f"Placed home {home.name} for {p.name}")

    def init_objectives(self):
        self.public_objectives = [
            {"id":"hold3","title":"Hold 3 systems","scored_by":[],"points":1},
            {"id":"mec","title":"Control Mecatol","scored_by":[],"points":1}
        ]

    # -------------------------
    # Actions
    # -------------------------
    def api_move(self, player_name:str, action:Dict[str,Any]):
        player = self.find_player(player_name)
        if not player: return {"ok":False,"err":"player not found"}
        from_id = action.get("from"); to_id = action.get("to"); uid = action.get("unit_uid")
        if not (from_id and to_id and uid): return {"ok":False,"err":"missing fields"}
        from_sys = next((s for s in self.systems if s.id==from_id), None)
        to_sys = next((s for s in self.systems if s.id==to_id), None)
        if not from_sys or not to_sys: return {"ok":False,"err":"invalid system"}
        units_here = from_sys.ships.get(player.name, [])
        unit = next((u for u in units_here if u.uid==uid), None)
        if not unit: return {"ok":False,"err":"unit not found"}
        # move validation: consume move points or tokens (simple)
        from_sys.ships[player.name].remove(unit)
        to_sys.ships.setdefault(player.name,[]).append(unit)
        self.history.append(f"{player.name} moved {unit.type_name} from {from_id} to {to_id}")
        # combat detection (first enemy in target)
        opponents = [pname for pname, listu in to_sys.ships.items() if pname!=player.name and listu]
        if opponents:
            defender_name = opponents[0]
            attacker_units = list(to_sys.ships.get(player.name,[]))
            defender_units = list(to_sys.ships.get(defender_name,[]))
            from .combat import compute_space_combat_rolls
            rolls = compute_space_combat_rolls(attacker_units, defender_units, self.rng)
            pending = {
                "system_id": to_sys.id,
                "attacker": player.name,
                "defender": defender_name,
                "attacker_units":[u.uid for u in attacker_units],
                "defender_units":[u.uid for u in defender_units],
                "rolls": rolls,
                "attacker_hits": rolls.get("attacker_hits",0),
                "defender_hits": rolls.get("defender_hits",0)
            }
            self.pending_combats[to_sys.id] = pending
            return {"ok":True,"combat_pending":True,"system": to_sys.id}
        return {"ok":True,"combat_pending":False,"system": to_sys.id}

    def api_apply_combat_assignments(self, system_id, attacker_loss_uids, defender_loss_uids):
        pending = self.pending_combats.get(system_id)
        if not pending: return {"ok":False,"err":"no pending combat"}
        # apply losses
        sys = next((s for s in self.systems if s.id==system_id), None)
        if not sys: return {"ok":False,"err":"system not found"}
        atk = pending["attacker"]; dft = pending["defender"]
        atk_hits = pending.get("attacker_hits",0); dft_hits = pending.get("defender_hits",0)
        if len(attacker_loss_uids) > atk_hits or len(defender_loss_uids)>dft_hits:
            return {"ok":False,"err":"too many losses assigned"}
        removed={"attacker":[], "defender":[]}
        # remove attacker units
        if atk in sys.ships:
            current = sys.ships.get(atk, [])
            remaining=[]
            for u in current:
                if u.uid in attacker_loss_uids:
                    removed['attacker'].append(u.uid)
                    try: self.find_player(atk).ships.remove(u)
                    except: pass
                    self._unit_index.pop(u.uid, None)
                else:
                    remaining.append(u)
            sys.ships[atk]=remaining
        if dft in sys.ships:
            current = sys.ships.get(dft, [])
            remaining=[]
            for u in current:
                if u.uid in defender_loss_uids:
                    removed['defender'].append(u.uid)
                    try: self.find_player(dft).ships.remove(u)
                    except: pass
                    self._unit_index.pop(u.uid, None)
                else:
                    remaining.append(u)
            sys.ships[dft]=remaining
        self.pending_combats.pop(system_id, None)
        self.history.append(f"Combat resolved at {system_id}: removed {removed}")
        return {"ok":True,"removed":removed}

    def produce(self, player_name:str, unit_type:str="Cruiser"):
        p = self.find_player(player_name)
        if not p: return False
        cost = PRODUCTION_COSTS.get(unit_type, 2)
        if p.resources < cost: 
            self.history.append(f"{player_name} insufficient resources for {unit_type}")
            return False
        p.resources -= cost
        new = Unit(p, new_uid(player_name+"-"+unit_type.lower()), unit_type)
        p.ships.append(new)
        # place on one of player's planets if any, else first system
        placed=False
        for s in self.systems:
            for pl in s.planets:
                if pl.controller == p:
                    s.ships.setdefault(p.name,[]).append(new)
                    placed=True
                    break
            if placed: break
        if not placed:
            self.systems[0].ships.setdefault(p.name,[]).append(new)
        self._index_unit(new)
        self.history.append(f"{player_name} produced {unit_type}")
        return True

    def set_strategy(self, player_name:str, card:int):
        p = self.find_player(player_name)
        if not p: return {"ok":False,"err":"player not found"}
        p.strategy_card = card
        # quick effects prototype
        if card == 8:
            p.vp += 1
            self.history.append(f"{p.name} picked Imperial => +1 VP")
        if card == 6:
            p.combat_buff += 1
            self.history.append(f"{p.name} picked Warfare => +1 combat buff next combat")
        return {"ok":True,"strategy":card}

    # rounds/income
    def next_round(self):
        self.round += 1
        # income
        for p in self.players:
            income = sum(pl.resources for pl in p.planets)
            p.resources += 1 + income
            self.history.append(f"{p.name} income +{1+income} -> {p.resources}")
        self.history.append(f"=== Round {self.round} ===")

    # to dict
    def to_dict(self):
        return {
            "round": self.round,
            "seed": self.seed,
            "players": [p.to_dict() for p in self.players],
            "systems":[s.to_dict() for s in self.systems],
            "history": self.history[-300:],
            "pending_combats": self.pending_combats
        }

    # persistence helpers
    def serialize(self):
        return {"seed":self.seed, "round":self.round, "players":[{"name":p.name,"faction":p.faction,"resources":p.resources,"vp":p.vp} for p in self.players], "systems":[s.to_dict() for s in self.systems], "history": self.history}

