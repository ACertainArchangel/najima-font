"""Shared data for the pentagram alphabet: segment geometry and letter table.

Numbering: inner pentagon 1-5 clockwise from the top edge; outer edges 6-15
clockwise starting with the left side of the top point. Point triangle k is
{k, 2k+4, 2k+5}. Coordinates are on a unit star (outer radius 1, centre 0,0).
Rotation is in degrees, positive = counterclockwise.
"""
import math

# letter: (segments, rotation_deg). Empty list = no candidate yet.
LETTERS = {
    "A": ([6, 5, 13, 7, 2, 10, 1], 0),
    "B": ([2, 8, 9, 3, 10, 11], 18),
    "C": ([1, 5, 4, 3], 0),
    "D": ([2, 8, 9], -18),
    "E": ([13, 12, 15, 14], -18),
    "F": ([13, 5, 4, 1], 18),
    "G": ([1, 5, 4, 11, 10, 3], 0),
    "H": ([5, 13, 4, 3, 2, 10], 0),
    "I": ([6, 5, 13], 18),
    "J": ([7, 2, 3, 4], 0),
    "K": ([13, 5, 4, 1, 6], 18),
    "L": ([6, 5, 4], 18),
    "M": ([13, 4, 3, 10], 0),
    "N": ([13, 4, 11, 10], 0),
    "O": ([1, 2, 3, 4, 5], 0),
    "P": ([1, 2, 3, 4, 5, 13], 18),
    "Q": ([1, 2, 3, 4, 5, 10], 0),
    "R": ([13, 5, 1, 2, 3, 4, 11], 0),
    "S": ([6, 1, 2, 3, 4], -18),
    "T": ([13, 5, 15, 1], 18),
    "U": ([5, 4, 3, 2], 0),
    "V": ([13, 12], 36),
    "W": ([13, 4, 3, 10], 180),
    "X": ([14, 4, 11, 9, 3, 12], 0),
    "Y": ([4, 3, 12], 0),
    "Z": ([8, 9, 3, 11], 18),
}

def _pt(angle_deg, r):
    a = math.radians(angle_deg)
    return (r * math.cos(a), r * math.sin(a))


def build_segments():
    r_in = math.sin(math.radians(18)) / math.sin(math.radians(54))  # ~0.382
    T, R, BR, BL, L = (_pt(a, 1.0) for a in (90, 18, -54, -126, 162))
    IUL, IUR, ILR, IB, ILL = (_pt(a, r_in) for a in (126, 54, -18, -90, 198))
    return {
        1: (IUL, IUR), 2: (IUR, ILR), 3: (ILR, IB), 4: (IB, ILL), 5: (ILL, IUL),
        6: (IUL, T), 7: (T, IUR), 8: (IUR, R), 9: (R, ILR), 10: (ILR, BR),
        11: (BR, IB), 12: (IB, BL), 13: (BL, ILL), 14: (ILL, L), 15: (L, IUL),
    }


SEGMENTS = build_segments()


def rotate(p, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return (p[0] * c - p[1] * s, p[0] * s + p[1] * c)
