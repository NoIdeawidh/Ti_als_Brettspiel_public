"""Core package for the Twilight Imperium board game implementation.

Module overview:
    hexmap   -- axial hex coordinates, adjacency and map generation
    units    -- static unit definitions (cost, combat value, movement, capacity)
    models   -- serialisable domain model (Unit, Planet, System, Player, Board)
    combat   -- dice based space combat resolution
    engine   -- rule enforcement for player actions (move, produce, ...)
    phases   -- round structure and turn order
    game     -- aggregate object tying everything together
"""

from ti.game import Game

__all__ = ["Game"]
