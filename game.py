import uuid
from engine import Engine

class Game:
    def __init__(self, players, systems, seed):
        self.id = str(uuid.uuid4())
        self.players = players
        self.systems = systems
        self.seed = seed
        self.round = 0
        self.history = [f"Game created seed={seed}"]
        self.pending_combats = {}
        self.engine = Engine(self)

    def get_system(self, sid):
        for s in self.systems:
            if s["id"] == sid:
                return s
        return None

    def apply_action(self, player, action):
        if action["type"] == "move":
            ok, msg = self.engine.move(
                player,
                action["from"],
                action["to"]
            )
            if ok:
                self.engine.resolve_combats()
            return ok, msg

        return False, "Unknown action"

    def to_dict(self):
        return {
            "ok": True,
            "round": self.round,
            "seed": self.seed,
            "players": self.players,
            "systems": self.systems,
            "history": self.history,
            "pending_combats": self.pending_combats
        }
