# -*- coding: utf-8 -*-
"""Brand palette, logo rasteriser and splash screen for the AnY terminal."""
import os
import logging
import time
from functools import lru_cache

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Center, Vertical
from textual.screen import Screen
from textual.theme import Theme
from textual.widgets import Static

logger = logging.getLogger(__name__)

INK = "#0b0e13"
PAPER = "#e6eef6"
SILVER = "#b7d0dc"
GOLD = "#e4a832"
CORAL = "#ff977a"
RED = "#ff7a85"
MINT = "#88d3b8"
MUTED_TEXT = "#a6b6c7"
AGENT_FALLBACKS = ("#8ebdf4", "#e995b4", "#9ac986", "#c8b6ff", MINT)
GOLD_HI = "#faf1c4"
GOLD_DEEP = "#bc7e14"
CHROME_HI = "#e6eef6"
CHROME_LO = "#8e9bab"
RAISED = "#12171f"

TERMINAL_THEME = Theme(
    name="any", primary=SILVER, accent=SILVER, success=MINT,
    warning=CORAL, error=RED, foreground=PAPER,
    background=INK, surface=RAISED, panel="#283442",
)

# Logo geometry in the SVG's 256-space (design/brand/any-logo-t2).
Y_POLY = ((26.2, 38), (56.2, 38), (128, 162.3), (199.8, 38), (229.8, 38), (142, 190),
          (142, 202), (156, 202), (156, 214), (100, 214), (100, 202), (114, 202), (114, 190))
A_OUTER = ((128, 44), (198.4, 166), (183.9, 166), (158, 121), (98, 121), (72.1, 166), (57.6, 166))
A_HOLE = ((128, 69.1), (108.4, 103), (147.6, 103))
BBOX = (26.2, 38.0, 229.8 - 26.2, 214 - 38.0)   # x, y, w, h


def _inside(poly, x, y):
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def _hex_rgb(value):
    return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))


def _lerp(c1, c2, t):
    return tuple(a + (b - a) * t for a, b in zip(c1, c2))


_INK_RGB = _hex_rgb(INK)
_CHROME_HI_RGB = _hex_rgb(CHROME_HI)
_CHROME_LO_RGB = _hex_rgb(CHROME_LO)
_GOLD_HI_RGB = _hex_rgb(GOLD_HI)
_GOLD_RGB = _hex_rgb(GOLD)
_GOLD_DEEP_RGB = _hex_rgb(GOLD_DEEP)
_Y_TINT = _hex_rgb("#f4f9ff")
_A_TINT = _GOLD_HI_RGB


def _gradient(shape, t):
    t = min(1.0, max(0.0, t))
    if shape == "Y":
        return _lerp(_CHROME_HI_RGB, _CHROME_LO_RGB, t)
    if t < 0.5:
        return _lerp(_GOLD_HI_RGB, _GOLD_RGB, t * 2)
    return _lerp(_GOLD_RGB, _GOLD_DEEP_RGB, (t - 0.5) * 2)


@lru_cache(maxsize=16)
def _pixels(cols, rows):
    """Sample the logo on the 2-by-4 dot grid of each terminal cell."""
    width, height = cols * 2, rows * 4
    bx, by, bw, bh = BBOX
    scale = min(width / bw, height / bh)
    ox = (width - bw * scale) / 2
    oy = (height - bh * scale) / 2
    grid = []
    for py in range(height):
        row = []
        for px in range(width):
            rs = gs = bs = 0.0
            hits = {"A": 0, "Y": 0}
            covered = 0
            for sy in range(3):
                for sx in range(3):
                    x = bx + (px + (sx + 0.5) / 3 - ox) / scale
                    y = by + (py + (sy + 0.5) / 3 - oy) / scale
                    in_y = _inside(Y_POLY, x, y)
                    in_a = _inside(A_OUTER, x, y) != _inside(A_HOLE, x, y)
                    if in_a and in_y:
                        shape = "Y" if x > 128 and 84 <= y <= 168 else "A"
                    elif in_a:
                        shape = "A"
                    elif in_y:
                        shape = "Y"
                    else:
                        continue
                    covered += 1
                    hits[shape] += 1
                    t = ((x - bx) / bw + (y - by) / bh) / 2
                    r, g, b = _gradient(shape, t)
                    rs += r
                    gs += g
                    bs += b
            coverage = covered / 9
            if covered:
                base = _lerp(_INK_RGB, (rs / covered, gs / covered, bs / covered), coverage)
                tint = _A_TINT if hits["A"] >= hits["Y"] else _Y_TINT
            else:
                base = _INK_RGB
                tint = _INK_RGB
            d = ((px + 0.5) + (py + 0.5)) / (width + height)
            row.append((base, coverage, d, tint))
        grid.append(row)
    return grid


def _style_rgb(rgb):
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(c))) for c in rgb)


def logo_art(cols, rows, *, sweep=None, reveal=1.0):
    """Rasterise the AnY mark using the finer 2-by-4 Braille dot grid."""
    grid = _pixels(cols, rows)
    art = Text()
    for line in range(rows):
        if line:
            art.append("\n")
        for col in range(cols):
            dots = 0
            colors = []
            for dy, bits in enumerate(((1, 8), (2, 16), (4, 32), (64, 128))):
                for dx, bit in enumerate(bits):
                    base, coverage, d, tint = grid[line * 4 + dy][col * 2 + dx]
                    if coverage < 0.4 or d > reveal:
                        continue
                    if sweep is not None:
                        factor = max(0.0, 1 - abs(d - sweep) / 0.06)
                        base = _lerp(base, tint, factor * 0.65)
                    dots |= bit
                    colors.append(base)
            if dots:
                color = tuple(sum(c[channel] for c in colors) / len(colors) for channel in range(3))
                art.append(chr(0x2800 + dots), style=_style_rgb(color))
            else:
                art.append(" ")
    return art


class WelcomeMark(Static):
    """Compact brand mark for the home masthead: logo art, or plain text without colour."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.compact = False

    def on_mount(self):
        self.redraw()

    def redraw(self):
        app = self.app
        if getattr(app, "no_color", False):
            self.update(Text("AnY", style="bold"))
        elif self.compact:
            self.update(Text.assemble(("A", f"bold {GOLD}"), ("n", MUTED_TEXT), ("Y", f"bold {CHROME_HI}")))
        else:
            self.update(logo_art(18, 8))

    def render(self):
        if getattr(self.app, "no_color", False):
            return Text("AnY", style="bold")
        return super().render()


class Splash(Screen):
    """Full-screen startup mark: diagonal reveal with a specular sweep, then the wordmark."""

    DURATION = 1.25

    def compose(self) -> ComposeResult:
        with Center(id="splash-center"):
            with Vertical(id="splash-box"):
                yield Static(id="splash-art")
                yield Static(id="splash-word")
                yield Static(id="splash-tag")

    def on_mount(self):
        self.started = time.monotonic()
        self.query_one("#splash-word", Static).display = False
        self.query_one("#splash-tag", Static).display = False
        self.timer = self.set_interval(1 / 30, self.tick)
        self.tick()

    def tick(self):
        try:
            t = time.monotonic() - self.started
            sweep: float | None
            if t < 0.65:
                reveal = t / 0.65
                sweep = reveal
            else:
                reveal = 1.0
                sweep = min(1.0, (t - 0.65) / 0.3) if t < 0.95 else None
            self.query_one("#splash-art", Static).update(logo_art(34, 15, sweep=sweep, reveal=reveal))
            if t >= 0.65:
                word = Text.assemble(("A", f"bold {GOLD}"), (" n ", MUTED_TEXT), ("Y", f"bold {CHROME_HI}"))
                widget = self.query_one("#splash-word", Static)
                widget.update(word)
                widget.display = True
            if t >= 0.8:
                tag = self.query_one("#splash-tag", Static)
                tag.update(Text("Agents and You", style=f"dim {MUTED_TEXT}"))
                tag.display = True
            if t >= self.DURATION:
                self.dismiss()
        except Exception:
            logger.exception("Failed to update terminal splash")

    def on_key(self, event):
        self.dismiss()

    def on_click(self, event):
        self.dismiss()

    def on_resize(self, event):
        self.tick()


def splash_enabled(app):
    if os.environ.get("ANY_NO_SPLASH"):
        return False
    if getattr(app, "no_color", False) or app.animation_level == "none":
        return False
    size = app.size
    return size.width >= 60 and size.height >= 22
