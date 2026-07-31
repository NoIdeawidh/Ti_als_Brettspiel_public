"""Axial hex coordinate helpers and galaxy generation.

The galaxy uses axial coordinates ``(q, r)`` with pointy-top hexes.
Mecatol Rex sits at the origin, home systems are placed on an outer ring.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, List, Tuple

AXIAL_DIRECTIONS: Tuple[Tuple[int, int], ...] = (
    (1, 0),
    (1, -1),
    (0, -1),
    (-1, 0),
    (-1, 1),
    (0, 1),
)


@dataclass(frozen=True)
class Hex:
    q: int
    r: int

    @property
    def s(self) -> int:
        return -self.q - self.r

    def neighbors(self) -> List["Hex"]:
        return [Hex(self.q + dq, self.r + dr) for dq, dr in AXIAL_DIRECTIONS]

    def distance(self, other: "Hex") -> int:
        return (
            abs(self.q - other.q)
            + abs(self.r - other.r)
            + abs(self.s - other.s)
        ) // 2

    def to_dict(self) -> dict:
        return {"q": self.q, "r": self.r}

    @staticmethod
    def from_dict(data: dict) -> "Hex":
        return Hex(int(data["q"]), int(data["r"]))


def ring(radius: int) -> List[Hex]:
    """All hexes at exactly ``radius`` steps from the origin."""
    if radius == 0:
        return [Hex(0, 0)]
    results: List[Hex] = []
    # start at the "south-west" corner and walk around the ring
    q, r = AXIAL_DIRECTIONS[4][0] * radius, AXIAL_DIRECTIONS[4][1] * radius
    for direction in AXIAL_DIRECTIONS:
        for _ in range(radius):
            results.append(Hex(q, r))
            q += direction[0]
            r += direction[1]
    return results


def spiral(radius: int) -> Iterator[Hex]:
    """All hexes within ``radius`` of the origin, from the centre outwards."""
    for rad in range(radius + 1):
        for hex_ in ring(rad):
            yield hex_


def pixel_position(hex_: Hex, size: float) -> Tuple[float, float]:
    """Convert an axial coordinate to pixel space (pointy-top layout)."""
    x = size * (3 ** 0.5) * (hex_.q + hex_.r / 2)
    y = size * 1.5 * hex_.r
    return x, y


def home_positions(player_count: int, radius: int = 3) -> List[Hex]:
    """Evenly distributed home system positions on the outer ring."""
    outer = ring(radius)
    if player_count <= 0:
        return []
    step = len(outer) / player_count
    return [outer[int(round(i * step)) % len(outer)] for i in range(player_count)]
