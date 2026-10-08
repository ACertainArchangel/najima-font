"""Render letters built from the 15 segments of a pentagram.

Numbering: inner pentagon 1-5 clockwise from the top edge; outer edges 6-15
clockwise starting with the left side of the top point. Point triangle k is
{k, 2k+4, 2k+5}.

Edit LETTERS in star_alphabet.py, then run:  python star_letters.py [out.png|out.svg]
Rotation is in degrees, positive = counterclockwise.
"""
import math
import sys

from star_alphabet import LETTERS, SEGMENTS, rotate

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

COLS = 7
LETTER_COLOR = "#C1272D"
GHOST_COLOR = "#BBBBBB"


def draw_star(ax, segs, rotation, title):
    for n, (a, b) in SEGMENTS.items():
        (x1, y1), (x2, y2) = rotate(a, rotation), rotate(b, rotation)
        if n in segs:
            ax.plot([x1, x2], [y1, y2], color=LETTER_COLOR, lw=4,
                    solid_capstyle="round", zorder=2)
        else:
            ax.plot([x1, x2], [y1, y2], color=GHOST_COLOR, lw=0.8,
                    ls=(0, (3, 3)), zorder=1)
    ax.set_title(title, fontsize=11)
    _frame(ax)


def draw_key(ax):
    for n, (a, b) in SEGMENTS.items():
        color = "#1D9E75" if n <= 5 else "#D85A30"
        ax.plot([a[0], b[0]], [a[1], b[1]], color=color, lw=2)
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        push = -0.13 if n <= 5 else 0.14  # inner labels inward, outer outward
        d = math.hypot(mx, my) or 1
        ax.text(mx + push * mx / d, my + push * my / d, str(n),
                ha="center", va="center", fontsize=8)
    ax.set_title("key", fontsize=11)
    _frame(ax)


def _frame(ax):
    ax.set_xlim(-1.15, 1.15)
    ax.set_ylim(-1.15, 1.15)
    ax.set_aspect("equal")
    ax.axis("off")


def main(out_path="star_letters.png"):
    cells = len(LETTERS) + 1
    rows = math.ceil(cells / COLS)
    fig, axes = plt.subplots(rows, COLS, figsize=(COLS * 1.9, rows * 2.1))
    axes = [ax for row in axes for ax in row]

    draw_key(axes[0])
    for ax, (letter, (segs, rot)) in zip(axes[1:], LETTERS.items()):
        if segs:
            label = f"{letter}  ({rot:+d}°)" if rot else letter
            draw_star(ax, set(segs), rot, label)
        else:
            draw_star(ax, set(), 0, f"{letter}  —")
    for ax in axes[cells:]:
        ax.axis("off")

    fig.tight_layout()
    fig.savefig(out_path, dpi=110)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main(*sys.argv[1:2])
