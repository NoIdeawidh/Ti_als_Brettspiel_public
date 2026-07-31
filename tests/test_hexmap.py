from ti.hexmap import Hex, home_positions, ring, spiral


def test_neighbors_are_distance_one():
    origin = Hex(0, 0)
    assert len(origin.neighbors()) == 6
    assert all(origin.distance(n) == 1 for n in origin.neighbors())


def test_ring_sizes():
    assert ring(0) == [Hex(0, 0)]
    assert len(ring(1)) == 6
    assert len(ring(3)) == 18
    assert all(Hex(0, 0).distance(h) == 3 for h in ring(3))


def test_spiral_contains_unique_hexes():
    hexes = list(spiral(2))
    assert len(hexes) == len(set(hexes)) == 1 + 6 + 12


def test_home_positions_are_distinct():
    homes = home_positions(4)
    assert len(homes) == len(set(homes)) == 4
