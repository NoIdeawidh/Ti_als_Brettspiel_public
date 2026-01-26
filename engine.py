import random

class Engine:
    def __init__(self, game):
        self.game = game

    def move(self, player_name, src_id, dst_id):
        src = self.game.get_system(src_id)
        dst = self.game.get_system(dst_id)

        if not src or not dst:
            return False, "Invalid system"

        ships = src["ships"].get(player_name, [])
        if not ships:
            return False, "No ships to move"

        # move ALL ships for now
        src["ships"][player_name] = []
        dst["ships"].setdefault(player_name, []).extend(ships)

        self.game.history.append(
            f"{player_name} moved {len(ships)} ships from {src_id} to {dst_id}"
        )

        self._check_combat(dst_id)
        return True, "Move successful"

    def _check_combat(self, system_id):
        sys = self.game.get_system(system_id)
        owners = [p for p, u in sys["ships"].items() if u]

        if len(owners) > 1:
            self.game.pending_combats[system_id] = owners

    def resolve_combats(self):
        for system_id, owners in list(self.game.pending_combats.items()):
            sys = self.game.get_system(system_id)

            # very simple combat: random winner weighted by ship count
            pools = {}
            for owner in owners:
                pools[owner] = len(sys["ships"].get(owner, []))

            winner = random.choices(
                list(pools.keys()),
                weights=list(pools.values())
            )[0]

            for owner in list(sys["ships"].keys()):
                if owner != winner:
                    sys["ships"][owner] = []

            self.game.history.append(
                f"Combat at {system_id}: {winner} won"
            )

            del self.game.pending_combats[system_id]
