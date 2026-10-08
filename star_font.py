"""Build a TrueType font from the pentagram alphabet and set text in it.

    python star_font.py                      # build Najma.ttf + render the poem
    python star_font.py "text here" out.png  # build Najma.ttf + render your text

Needs fontTools and Pillow. Letter shapes come from star_alphabet.LETTERS, so
edit them there and rerun.

Glyph construction: every segment becomes a flat-ended rectangle, and every node
where two or more segments meet gets a convex "joint" filling the outer side of
the corner (a bevel join). The pieces overlap, all wound the same way, so the
nonzero fill rule renders them as one solid shape. The OVERLAP_SIMPLE flag is
set on each glyph so renderers know the overlap is intentional.
"""
import math
import sys
from pathlib import Path

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from PIL import Image, ImageDraw, ImageFont

from star_alphabet import LETTERS, SEGMENTS, rotate

FAMILY = "Najma"
UPM = 1000
STAR_SCALE = 400          # outer radius of the star in font units
STROKE = 80               # stroke width in font units
SIDE_BEARING = 60
SPACE_WIDTH = 300
BASELINE_OFFSET = STAR_SCALE * math.cos(math.radians(36))  # bottom tips sit on y=0

OVERLAP_SIMPLE = 0x40


# ---------------------------------------------------------------- geometry

class Polygon:
    """A convex polygon in font units, kept clockwise (TrueType outer contour)."""

    def __init__(self, points):
        pts = [(round(x), round(y)) for x, y in points]
        if self._signed_area(pts) > 0:
            pts.reverse()
        self.points = pts

    @staticmethod
    def _signed_area(pts):
        return sum(x1 * y2 - x2 * y1
                   for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1])) / 2

    def is_degenerate(self):
        return len(set(self.points)) < 3 or abs(self._signed_area(self.points)) < 1

    def shifted(self, dx):
        shifted = Polygon([])
        shifted.points = [(x + dx, y) for x, y in self.points]
        return shifted


def convex_hull(points):
    pts = sorted(set(points))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


class StrokeOutliner:
    """Turns a set of line segments into overlapping convex polygons."""

    JOIN_OVERLAP = 2  # font units each joined end is extended, to avoid seams

    def __init__(self, width):
        self.half = width / 2

    def outline(self, lines):
        degree = {}
        for a, b in lines:
            for p in (a, b):
                degree[self._key(p)] = degree.get(self._key(p), 0) + 1

        polygons, corners_at = [], {}
        for a, b in lines:
            dx, dy = b[0] - a[0], b[1] - a[1]
            length = math.hypot(dx, dy)
            ux, uy = dx / length, dy / length
            nx, ny = -uy * self.half, ux * self.half
            ext_a = self.JOIN_OVERLAP if degree[self._key(a)] > 1 else 0
            ext_b = self.JOIN_OVERLAP if degree[self._key(b)] > 1 else 0
            a2 = (a[0] - ux * ext_a, a[1] - uy * ext_a)
            b2 = (b[0] + ux * ext_b, b[1] + uy * ext_b)
            polygons.append(Polygon([
                (a2[0] + nx, a2[1] + ny), (b2[0] + nx, b2[1] + ny),
                (b2[0] - nx, b2[1] - ny), (a2[0] - nx, a2[1] - ny)]))
            for p in (a, b):
                corners_at.setdefault(self._key(p), [p]).extend(
                    [(p[0] + nx, p[1] + ny), (p[0] - nx, p[1] - ny)])

        for key, pts in corners_at.items():
            if degree[key] > 1:
                joint = Polygon(convex_hull(pts))
                if not joint.is_degenerate():
                    polygons.append(joint)
        return [p for p in polygons if not p.is_degenerate()]

    @staticmethod
    def _key(p):
        return (round(p[0], 3), round(p[1], 3))


# ---------------------------------------------------------------- glyphs

class GlyphShape:
    def __init__(self, polygons, advance=None):
        self.polygons = polygons
        self._advance = advance

    @classmethod
    def from_lines(cls, lines, outliner):
        polygons = outliner.outline(lines)
        xs = [x for poly in polygons for x, _ in poly.points]
        dx = SIDE_BEARING - min(xs)
        shifted = [poly.shifted(dx) for poly in polygons]
        return cls(shifted, advance=max(xs) - min(xs) + 2 * SIDE_BEARING)

    @property
    def advance(self):
        return self._advance

    @property
    def lsb(self):
        xs = [x for poly in self.polygons for x, _ in poly.points]
        return min(xs) if xs else 0

    def y_extent(self):
        ys = [y for poly in self.polygons for _, y in poly.points]
        return (min(ys), max(ys)) if ys else (0, 0)

    def to_ttglyph(self):
        pen = TTGlyphPen(None)
        for poly in self.polygons:
            pen.moveTo(poly.points[0])
            for pt in poly.points[1:]:
                pen.lineTo(pt)
            pen.closePath()
        glyph = pen.glyph()
        if self.polygons:
            glyph.flags[0] |= OVERLAP_SIMPLE
        return glyph


def star_point(p, rotation):
    x, y = rotate(p, rotation)
    return (x * STAR_SCALE, y * STAR_SCALE + BASELINE_OFFSET)


def letter_lines(segments, rotation):
    return [tuple(star_point(p, rotation) for p in SEGMENTS[n]) for n in segments]


def small_pentagon(cx, cy, r):
    return Polygon([(cx + r * math.cos(math.radians(90 + 72 * i)),
                     cy + r * math.sin(math.radians(90 + 72 * i))) for i in range(5)])


def punctuation(outliner):
    dot_r = STROKE * 0.8
    period = GlyphShape([small_pentagon(0, dot_r, dot_r)])
    comma_tail = outliner.outline([((0, dot_r), (-dot_r * 0.9, -dot_r * 2.2))])
    comma = GlyphShape([small_pentagon(0, dot_r, dot_r)] + comma_tail)
    hyphen = letter_lines([1], 0)
    top = BASELINE_OFFSET + STAR_SCALE
    apostrophe = [((0, top), (-STROKE * 0.8, top - STROKE * 3))]

    shapes = {
        "period": _normalised(period),
        "comma": _normalised(comma),
        "hyphen": GlyphShape.from_lines(hyphen, outliner),
        "quotesingle": GlyphShape.from_lines(apostrophe, outliner),
    }
    return shapes


def _normalised(shape):
    xs = [x for poly in shape.polygons for x, _ in poly.points]
    dx = SIDE_BEARING - min(xs)
    return GlyphShape([p.shifted(dx) for p in shape.polygons],
                      advance=max(xs) - min(xs) + 2 * SIDE_BEARING)


def notdef_shape():
    w, h, t = 400, 700, 40
    outer = Polygon([(50, 0), (50 + w, 0), (50 + w, h), (50, h)])
    inner = Polygon([(50 + t, t), (50 + t, h - t), (50 + w - t, h - t), (50 + w - t, t)])
    inner.points.reverse()  # counterclockwise = hole
    return GlyphShape([outer, inner], advance=w + 100)


# ---------------------------------------------------------------- font

class StarFontBuilder:
    def __init__(self, letters):
        self.letters = letters
        self.outliner = StrokeOutliner(STROKE)

    def build(self, path):
        shapes = {".notdef": notdef_shape(), "space": GlyphShape([], advance=SPACE_WIDTH)}
        cmap = {ord(" "): "space"}

        for letter, (segments, rotation) in self.letters.items():
            if not segments:
                continue
            shapes[letter] = GlyphShape.from_lines(letter_lines(segments, rotation),
                                                   self.outliner)
            cmap[ord(letter)] = letter
            cmap[ord(letter.lower())] = letter

        shapes.update(punctuation(self.outliner))
        cmap.update({ord("."): "period", ord(","): "comma", ord("-"): "hyphen",
                     ord("'"): "quotesingle", 0x2019: "quotesingle"})

        y_min = min(s.y_extent()[0] for s in shapes.values())
        y_max = max(s.y_extent()[1] for s in shapes.values())
        ascent, descent = y_max + 40, y_min - 40

        fb = FontBuilder(UPM, isTTF=True)
        fb.setupGlyphOrder(list(shapes))
        fb.setupCharacterMap(cmap)
        fb.setupGlyf({name: s.to_ttglyph() for name, s in shapes.items()})
        fb.setupHorizontalMetrics({name: (round(s.advance), round(s.lsb))
                                   for name, s in shapes.items()})
        fb.setupHorizontalHeader(ascent=ascent, descent=descent)
        fb.setupNameTable({"familyName": FAMILY, "styleName": "Regular"})
        fb.setupOS2(sTypoAscender=ascent, sTypoDescender=descent, sTypoLineGap=200,
                    usWinAscent=ascent, usWinDescent=-descent,
                    sCapHeight=y_max, sxHeight=round(BASELINE_OFFSET))
        fb.setupPost()
        fb.save(path)
        return path


# ---------------------------------------------------------------- rendering

POEM_TITLE = "Morocco"
POEM = """Red as the clay walls of Marrakech at dusk,
the medina folds its alleys like a held breath.
Spice smoke climbs where the souk lanterns burn,
saffron, cumin, and the mint of poured tea.
The Atlas keeps its snow above the palms,
and the Sahara writes its dunes in wind.
In Chefchaouen the doors wear the colour of sea,
in Fes the tanneries hold every dye of dawn.
A green star rests on a field of red,
five points to hold a country together."""

BACKGROUND = (12, 12, 12)
RED = (193, 39, 45)
GREEN = (0, 98, 51)


def render(font_path, title, body, out_path, size=64, margin=90):
    title_font = ImageFont.truetype(str(font_path), int(size * 1.9))
    body_font = ImageFont.truetype(str(font_path), size)
    lines = body.splitlines()
    line_h = int(size * 1.45)
    title_h = int(size * 1.9 * 1.4) if title else 0

    width = int(max([body_font.getlength(l) for l in lines]
                    + [title_font.getlength(title)])) + 2 * margin
    height = 2 * margin + title_h + line_h * len(lines)

    img = Image.new("RGB", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(img)
    draw.text((margin, margin), title, font=title_font, fill=GREEN)
    y = margin + title_h
    for line in lines:
        draw.text((margin, y), line, font=body_font, fill=RED)
        y += line_h
    img.save(out_path)
    return out_path


def main(argv):
    here = Path(__file__).parent
    font_path = StarFontBuilder(LETTERS).build(here / f"{FAMILY}.ttf")
    print(f"wrote {font_path}")
    if len(argv) >= 1:
        out = argv[1] if len(argv) > 1 else "text.png"
        print("wrote", render(font_path, "", argv[0], out))
    else:
        print("wrote", render(font_path, POEM_TITLE, POEM, here / "morocco_poem.png"))


if __name__ == "__main__":
    main(sys.argv[1:])
