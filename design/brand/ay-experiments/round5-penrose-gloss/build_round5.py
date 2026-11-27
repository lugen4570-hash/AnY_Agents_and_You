#!/usr/bin/env python3
"""Generate Round 5: K1 Mist Grey + Over-Under Interlocked Penrose Impossible A & High-Gloss 3D Black-Chrome Y.

Builds 3 variants:
  P1: p1-penrose-extruded.svg  - 3D isometric extruded black-chrome Y + Penrose 3-ribbon gold A + over-under lock
  P2: p2-penrose-diamond.svg   - Tight silhouette diamond-cut Mobius/Penrose Y facets + extreme black-chrome gloss
  P3: p3-penrose-stairs.svg    - Stepped Penrose-stairs double-tiered 3D Y & extruded 3D Penrose A beams
"""
from __future__ import annotations

import math
import os
from typing import List, Sequence, Tuple

Point = Tuple[float, float]
Poly = List[Point]

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
CX = 128.0
S3 = math.sqrt(3.0)

# Master 60-degree Y skeleton
Y_TOP = 40.0
Y_STEM = 190.0
Y_FOOT_TOP = 202.0
Y_FOOT_BOT = 214.0
STEM_L = 114.0
STEM_R = 142.0
FOOT_L = 100.0
FOOT_R = 156.0
W_Y = 30.0

# Penrose 60-degree A skeleton (pointed apex miter + raised crossbar + extended feet)
A_APEX_Y = 66.0
A_BOT = 174.0
W_A = 19.0
U_A = W_A * 0.5  # 9.5 horizontal half-width per Penrose ribbon
B_TOP = 116.0
B_MID = 123.0
B_BOT = 130.0


def y_out_l(y: float) -> float:
    return STEM_L - (Y_STEM - y) / S3


def y_in_l(y: float) -> float:
    return y_out_l(y) + W_Y


def y_mid_l(y: float) -> float:
    return y_out_l(y) + W_Y * 0.5


def y_out_r(y: float) -> float:
    return 256.0 - y_out_l(y)


def y_in_r(y: float) -> float:
    return 256.0 - y_in_l(y)


def y_mid_r(y: float) -> float:
    return 256.0 - y_mid_l(y)


def a_lo(y: float) -> float:
    return CX - (y - A_APEX_Y) / S3


def a_lm(y: float) -> float:
    return a_lo(y) + U_A


def a_li(y: float) -> float:
    return a_lo(y) + W_A


def a_ro(y: float) -> float:
    return CX + (y - A_APEX_Y) / S3


def a_rm(y: float) -> float:
    return a_ro(y) - U_A


def a_ri(y: float) -> float:
    return a_ro(y) - W_A


Y_CROTCH = Y_STEM - (STEM_L + W_Y - CX) * S3  # 162.287

# Exact Penrose apex vertices
P_TOP: Point = (CX, A_APEX_Y)
P_LM_RO: Point = (CX + U_A * 0.5, A_APEX_Y + U_A * S3 * 0.5)
P_LI_RM: Point = (CX + U_A * 0.5, A_APEX_Y + 1.5 * U_A * S3)
P_LI_RI: Point = (CX, A_APEX_Y + 2.0 * U_A * S3)


def fmt(v: float) -> str:
    s = f"{v:.1f}"
    return "0" if s == "-0.0" else s[:-2] if s.endswith(".0") else s


def path_d(poly: Sequence[Point]) -> str:
    head = f"M{fmt(poly[0][0])} {fmt(poly[0][1])}"
    rest = "".join(f"L{fmt(x)} {fmt(y)}" for x, y in poly[1:])
    return f"{head}{rest}Z"


def rounded_rect_d(x: float, y: float, w: float, h: float, r: float, ccw: bool = False) -> str:
    if not ccw:
        return (
            f"M{x + r:g} {y:g} H{x + w - r:g} A{r:g} {r:g} 0 0 1 {x + w:g} {y + r:g}"
            f" V{y + h - r:g} A{r:g} {r:g} 0 0 1 {x + w - r:g} {y + h:g}"
            f" H{x + r:g} A{r:g} {r:g} 0 0 1 {x:g} {y + h - r:g}"
            f" V{y + r:g} A{r:g} {r:g} 0 0 1 {x + r:g} {y:g} Z"
        )
    return (
        f"M{x + r:g} {y:g} A{r:g} {r:g} 0 0 0 {x:g} {y + r:g}"
        f" V{y + h - r:g} A{r:g} {r:g} 0 0 0 {x + r:g} {y + h:g}"
        f" H{x + w - r:g} A{r:g} {r:g} 0 0 0 {x + w:g} {y + h - r:g}"
        f" V{y + r:g} A{r:g} {r:g} 0 0 0 {x + w - r:g} {y:g} Z"
    )


def poly_area(poly: Sequence[Point]) -> float:
    area = 0.0
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return 0.5 * area


def ensure_ccw(poly: Poly) -> Poly:
    return list(poly) if poly_area(poly) > 0 else list(reversed(poly))


def dedup_poly(poly: Poly, eps: float = 0.05) -> Poly:
    out: Poly = []
    for p in poly:
        if not out or math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > eps:
            out.append(p)
    if len(out) > 2 and math.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) <= eps:
        out.pop()
    return out


def clip_halfplane(poly: Poly, a: float, b: float, c: float) -> Poly:
    if not poly:
        return []
    out: Poly = []
    n = len(poly)
    for i in range(n):
        p1 = poly[i]
        p2 = poly[(i + 1) % n]
        d1 = a * p1[0] + b * p1[1] + c
        d2 = a * p2[0] + b * p2[1] + c
        in1 = d1 >= -1e-7
        in2 = d2 >= -1e-7
        if in1 and in2:
            out.append(p2)
        elif in1 and not in2:
            t = d1 / (d1 - d2)
            out.append((p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1])))
        elif not in1 and in2:
            t = d1 / (d1 - d2)
            out.append((p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1])))
            out.append(p2)
    return out


def clip_convex(subject: Poly, clipper: Poly) -> Poly:
    res = list(subject)
    clip_ccw = ensure_ccw(clipper)
    n = len(clip_ccw)
    for i in range(n):
        x1, y1 = clip_ccw[i]
        x2, y2 = clip_ccw[(i + 1) % n]
        a = -(y2 - y1)
        b = x2 - x1
        c = -a * x1 - b * y1
        res = clip_halfplane(res, a, b, c)
        if not res:
            return []
    return dedup_poly(res)


def translate(poly: Poly, dx: float, dy: float) -> Poly:
    return [(x + dx, y + dy) for x, y in poly]


def extrude_walls(poly: Poly, dx: float, dy: float) -> List[Tuple[str, Poly]]:
    """Return sorted (kind, quad) extrusion walls where kind in {'right', 'bot', 'inner'}."""
    pts = list(poly) if poly_area(poly) > 0 else list(reversed(poly))
    walls: List[Tuple[float, str, Poly]] = []
    n = len(pts)
    for i in range(n):
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        ex, ey = p2[0] - p1[0], p2[1] - p1[1]
        nx, ny = ey, -ex
        norm = math.hypot(nx, ny)
        if norm < 1e-6:
            continue
        nx /= norm
        ny /= norm
        dot = nx * dx + ny * dy
        if dot > 1e-4:
            if ny < -0.2:
                kind = "inner"  # facing up-right inside V-pocket (catches reflected light)
            elif ny > 0.85:
                kind = "bot"
            else:
                kind = "right"
            quad: Poly = [p1, p2, (p2[0] + dx, p2[1] + dy), (p1[0] + dx, p1[1] + dy)]
            cx_w = sum(p[0] for p in quad) * 0.25
            cy_w = sum(p[1] for p in quad) * 0.25
            depth = cx_w * dx + cy_w * dy
            walls.append((depth, kind, quad))
    walls.sort(key=lambda item: item[0], reverse=True)
    return [(kind, q) for _, kind, q in walls]


def y_full_poly() -> Poly:
    return [
        (y_out_l(Y_TOP), Y_TOP),
        (y_in_l(Y_TOP), Y_TOP),
        (CX, Y_CROTCH),
        (y_in_r(Y_TOP), Y_TOP),
        (y_out_r(Y_TOP), Y_TOP),
        (STEM_R, Y_STEM),
        (STEM_R, Y_FOOT_TOP),
        (FOOT_R, Y_FOOT_TOP),
        (FOOT_R, Y_FOOT_BOT),
        (FOOT_L, Y_FOOT_BOT),
        (FOOT_L, Y_FOOT_TOP),
        (STEM_L, Y_FOOT_TOP),
        (STEM_L, Y_STEM),
    ]


def a_backing_d() -> str:
    return (
        f"M{fmt(P_TOP[0])} {fmt(P_TOP[1])}"
        f"L{fmt(a_ro(A_BOT))} {fmt(A_BOT)}"
        f"H{fmt(a_ri(A_BOT))}"
        f"L{fmt(a_ri(B_BOT))} {fmt(B_BOT)}"
        f"H{fmt(a_li(B_BOT))}"
        f"L{fmt(a_li(A_BOT))} {fmt(A_BOT)}"
        f"H{fmt(a_lo(A_BOT))}Z "
        f"M{fmt(P_LI_RI[0])} {fmt(P_LI_RI[1])}"
        f"L{fmt(a_li(B_TOP))} {fmt(B_TOP)}"
        f"H{fmt(a_ri(B_TOP))}Z"
    )


def a_penrose_ribbons() -> Tuple[Poly, Poly, Poly, Poly]:
    """Return exact 3 Penrose L-ribbons + lower inner-left foot extension."""
    r1: Poly = [
        P_TOP,
        P_LM_RO,
        (a_lm(B_TOP), B_TOP),
        (a_ri(B_TOP), B_TOP),
        (a_ri(B_MID), B_MID),
        (a_lm(B_MID), B_MID),
        (a_lm(A_BOT), A_BOT),
        (a_lo(A_BOT), A_BOT),
    ]
    r2_main: Poly = [
        P_LM_RO,
        (a_ro(A_BOT), A_BOT),
        (a_rm(A_BOT), A_BOT),
        P_LI_RM,
        (a_li(B_TOP), B_TOP),
        (a_lm(B_TOP), B_TOP),
    ]
    r2_foot_l: Poly = [
        (a_lm(B_BOT), B_BOT),
        (a_li(B_BOT), B_BOT),
        (a_li(A_BOT), A_BOT),
        (a_lm(A_BOT), A_BOT),
    ]
    r3: Poly = [
        P_LI_RM,
        (a_rm(A_BOT), A_BOT),
        (a_ri(A_BOT), A_BOT),
        (a_ri(B_BOT), B_BOT),
        (a_lm(B_BOT), B_BOT),
        (a_lm(B_MID), B_MID),
        (a_ri(B_MID), B_MID),
        P_LI_RI,
    ]
    return r1, r2_main, r2_foot_l, r3


def a_specular_glints() -> List[Poly]:
    """Crisp machined specular gold glints (L outer edge, apex ridge, crossbar top)."""
    return [
        # Left outer sharp edge highlight
        [P_TOP, (P_TOP[0] + 1.2, P_TOP[1] + 2.1), (a_lo(A_BOT) + 2.2, A_BOT), (a_lo(A_BOT), A_BOT)],
        # Apex miter ridge highlight
        [P_TOP, P_LM_RO, (P_LM_RO[0] - 1.5, P_LM_RO[1] + 0.9), (P_TOP[0] - 0.8, P_TOP[1] + 1.5)],
        # Crossbar top edge highlight
        [(a_lm(B_TOP), B_TOP), (a_ri(B_TOP), B_TOP), (a_ri(B_TOP) + 1.0, B_TOP + 1.7), (a_lm(B_TOP) - 1.0, B_TOP + 1.7)],
    ]


def a_convex_parts_for_shadow() -> Tuple[Poly, Poly, Poly]:
    left_leg: Poly = [P_TOP, (P_TOP[0] + W_A, P_TOP[1]), (a_li(A_BOT), A_BOT), (a_lo(A_BOT), A_BOT)]
    right_leg: Poly = [(P_TOP[0] - W_A, P_TOP[1]), P_TOP, (a_ro(A_BOT), A_BOT), (a_ri(A_BOT), A_BOT)]
    crossbar: Poly = [(a_lm(B_TOP), B_TOP), (a_ri(B_TOP), B_TOP), (a_ri(B_BOT), B_BOT), (a_lm(B_BOT), B_BOT)]
    return left_leg, right_leg, crossbar


def k1_tile_defs_and_bg() -> Tuple[str, str]:
    rim_frame_d = rounded_rect_d(0, 0, 256, 256, 56) + " " + rounded_rect_d(2.5, 2.5, 251, 251, 53.5, ccw=True)
    defs = """
    <linearGradient id="tile-bg" x1="16" y1="10" x2="240" y2="246" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#E7EBEE"/>
      <stop offset="0.52" stop-color="#D5DBE0"/>
      <stop offset="1" stop-color="#C3CBD2"/>
    </linearGradient>
    <linearGradient id="tile-rim" x1="16" y1="12" x2="240" y2="244" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#F1F4F7"/>
      <stop offset="1" stop-color="#A6B0BA"/>
    </linearGradient>"""
    bg = f"""
  <g id="k1-mist-grey-tile">
    <rect x="0" y="0" width="256" height="256" rx="56" fill="url(#tile-bg)"/>
    <path fill="url(#tile-rim)" fill-rule="evenodd" d="{rim_frame_d}"/>
  </g>"""
    return defs, bg


def high_gloss_defs() -> str:
    """Shared high-luster liquid black-chrome + polished 18K gold gradients."""
    return """
    <!-- High-gloss liquid black-chrome Y gradients -->
    <linearGradient id="bc-bright" x1="24" y1="36" x2="215" y2="215" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#E4ECF4"/>
      <stop offset="0.16" stop-color="#8B98A8"/>
      <stop offset="0.40" stop-color="#191F27"/>
      <stop offset="0.58" stop-color="#606E7F"/>
      <stop offset="0.78" stop-color="#12161C"/>
      <stop offset="1" stop-color="#38424F"/>
    </linearGradient>
    <linearGradient id="bc-mid" x1="40" y1="40" x2="185" y2="205" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#758291"/>
      <stop offset="0.32" stop-color="#29303A"/>
      <stop offset="0.55" stop-color="#4A5666"/>
      <stop offset="0.80" stop-color="#13171D"/>
      <stop offset="1" stop-color="#242B35"/>
    </linearGradient>
    <linearGradient id="bc-deep" x1="95" y1="40" x2="230" y2="215" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#4A5564"/>
      <stop offset="0.32" stop-color="#171C23"/>
      <stop offset="0.58" stop-color="#384351"/>
      <stop offset="0.85" stop-color="#0D1015"/>
      <stop offset="1" stop-color="#1A2028"/>
    </linearGradient>
    <linearGradient id="bc-wall-right" x1="120" y1="40" x2="235" y2="220" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#8D9AA8"/>
      <stop offset="0.28" stop-color="#2A313C"/>
      <stop offset="0.55" stop-color="#5B6878"/>
      <stop offset="0.82" stop-color="#13171E"/>
      <stop offset="1" stop-color="#242B35"/>
    </linearGradient>
    <linearGradient id="bc-wall-inner" x1="55" y1="40" x2="132" y2="165" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#A6B3C2"/>
      <stop offset="0.45" stop-color="#404B59"/>
      <stop offset="1" stop-color="#181E26"/>
    </linearGradient>
    <linearGradient id="bc-stem-l" x1="100" y1="168" x2="128" y2="215" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#9BA7B6"/>
      <stop offset="0.38" stop-color="#343C48"/>
      <stop offset="0.72" stop-color="#4B5665"/>
      <stop offset="1" stop-color="#151920"/>
    </linearGradient>
    <linearGradient id="bc-stem-r" x1="128" y1="168" x2="156" y2="215" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#444F5D"/>
      <stop offset="0.52" stop-color="#181D24"/>
      <stop offset="1" stop-color="#0C0F14"/>
    </linearGradient>

    <!-- High-luster Penrose 18K polished gold gradients -->
    <linearGradient id="gold-bright" x1="68" y1="66" x2="155" y2="172" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#FAF0C0"/>
      <stop offset="0.28" stop-color="#F2CC68"/>
      <stop offset="0.52" stop-color="#DFAD38"/>
      <stop offset="0.72" stop-color="#F7DC88"/>
      <stop offset="1" stop-color="#C99220"/>
    </linearGradient>
    <linearGradient id="gold-mid" x1="88" y1="74" x2="184" y2="172" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#F2CA66"/>
      <stop offset="0.40" stop-color="#D49A28"/>
      <stop offset="0.70" stop-color="#E5B649"/>
      <stop offset="1" stop-color="#A87212"/>
    </linearGradient>
    <linearGradient id="gold-deep" x1="100" y1="90" x2="178" y2="172" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#B9811A"/>
      <stop offset="0.48" stop-color="#8A590C"/>
      <stop offset="0.78" stop-color="#A57016"/>
      <stop offset="1" stop-color="#6B4206"/>
    </linearGradient>"""


def penrose_a_group(with_walls: bool = False, dx_a: float = 0.0, dy_a: float = 0.0) -> str:
    r1, r2_main, r2_foot_l, r3 = a_penrose_ribbons()
    glints = a_specular_glints()
    walls_svg = ""
    if with_walls:
        # Subtle 3D metallic depth walls on A's outer right/bottom edges
        a_outer_poly: Poly = [
            P_TOP,
            (a_ro(A_BOT), A_BOT),
            (a_ri(A_BOT), A_BOT),
            (a_ri(B_BOT), B_BOT),
            (a_li(B_BOT), B_BOT),
            (a_li(A_BOT), A_BOT),
            (a_lo(A_BOT), A_BOT),
        ]
        walls = extrude_walls(a_outer_poly, dx_a, dy_a)
        wall_fills = {"right": "#8B5A0E", "bot": "#5E3905", "inner": "#9E6A16"}
        walls_svg = "".join(f'<path fill="{wall_fills[k]}" d="{path_d(q)}"/>' for k, q in walls)
        # Inner hole left wall clipped to upper counter
        hole: Poly = [P_LI_RI, (a_ri(B_TOP), B_TOP), (a_li(B_TOP), B_TOP)]
        hl_raw: Poly = [P_LI_RI, (a_li(B_TOP), B_TOP), (a_li(B_TOP) + dx_a, B_TOP + dy_a), (P_LI_RI[0] + dx_a, P_LI_RI[1] + dy_a)]
        hl_clip = clip_convex(hl_raw, hole)
        if len(hl_clip) >= 3:
            walls_svg += f'<path fill="#7A4C0A" d="{path_d(hl_clip)}"/>'

    return f"""
  <g id="a-penrose-gold">
    {walls_svg}
    <path fill="#C99322" fill-rule="evenodd" d="{a_backing_d()}"/>
    <path fill="url(#gold-deep)" d="{path_d(r3)}"/>
    <path fill="url(#gold-mid)" d="{path_d(r2_main)}"/>
    <path fill="url(#gold-mid)" d="{path_d(r2_foot_l)}"/>
    <path fill="url(#gold-bright)" d="{path_d(r1)}"/>
    {''.join(f'<path fill="#FAF0C2" d="{path_d(g)}"/>' for g in glints)}
  </g>"""


# ---------------------------------------------------------------------------
# P1: Penrose Extruded Black-Chrome (彭罗斯立体方钢)
# ---------------------------------------------------------------------------
def build_p1() -> str:
    dx, dy = 9.0, 7.0
    y_poly = y_full_poly()
    walls = extrude_walls(y_poly, dx, dy)
    wall_fill = {"right": "url(#bc-wall-right)", "bot": "#090B0F", "inner": "url(#bc-wall-inner)"}

    # Penrose planar ribbon twist across Y's crotch:
    # Left arm: outer half (bright specular) + inner half (deep obsidian)
    # Right arm (bridges over A!): inner pocket half (bright specular!) + outer half (deep obsidian!)
    # Twist occurs smoothly at stem hub (128, 177.3)
    y_stem_hub = (CX, 177.3)
    y_foot_hub = (CX, 208.0)
    y_arm_hub_l = (0.5 * (y_out_l(Y_CROTCH) + y_in_l(Y_CROTCH)), Y_CROTCH)
    y_arm_hub_r = (0.5 * (y_out_r(Y_CROTCH) + y_in_r(Y_CROTCH)), Y_CROTCH)

    cap_h = 3.5
    y_l_cap: Poly = [(y_out_l(Y_TOP), Y_TOP), (y_in_l(Y_TOP), Y_TOP), (y_in_l(Y_TOP) - 1.6, Y_TOP + cap_h), (y_out_l(Y_TOP) + 1.9, Y_TOP + cap_h)]
    y_r_cap: Poly = [(y_in_r(Y_TOP), Y_TOP), (y_out_r(Y_TOP), Y_TOP), (y_out_r(Y_TOP) - 1.9, Y_TOP + cap_h), (y_in_r(Y_TOP) + 1.6, Y_TOP + cap_h)]
    mid_cap_l = (y_mid_l(Y_TOP), Y_TOP + cap_h)
    mid_cap_r = (y_mid_r(Y_TOP), Y_TOP + cap_h)

    y_l_outer: Poly = [(y_out_l(Y_TOP), Y_TOP), mid_cap_l, y_arm_hub_l, y_stem_hub, (STEM_L, Y_STEM)]
    y_l_inner: Poly = [mid_cap_l, (y_in_l(Y_TOP), Y_TOP), (CX, Y_CROTCH), y_stem_hub, y_arm_hub_l]
    y_r_inner: Poly = [(y_in_r(Y_TOP), Y_TOP), mid_cap_r, y_arm_hub_r, y_stem_hub, (CX, Y_CROTCH)]
    y_r_outer: Poly = [mid_cap_r, (y_out_r(Y_TOP), Y_TOP), (STEM_R, Y_STEM), y_stem_hub, y_arm_hub_r]

    y_stem_l: Poly = [(STEM_L, Y_STEM), y_stem_hub, y_foot_hub, (FOOT_L, Y_FOOT_BOT), (FOOT_L, Y_FOOT_TOP), (STEM_L, Y_FOOT_TOP)]
    y_stem_r: Poly = [y_stem_hub, (STEM_R, Y_STEM), (STEM_R, Y_FOOT_TOP), (FOOT_R, Y_FOOT_TOP), (FOOT_R, Y_FOOT_BOT), y_foot_hub]
    y_foot_bot: Poly = [(FOOT_L, Y_FOOT_BOT), y_foot_hub, (FOOT_R, Y_FOOT_BOT)]

    # Razor specular silver-chrome bevel catches on Y's outer-left, right-inner, and right-outer corner ridge
    y_l_glint: Poly = [(y_out_l(Y_TOP), Y_TOP), (y_out_l(Y_TOP) + 2.4, Y_TOP + cap_h), (STEM_L + 2.2, Y_STEM), (STEM_L, Y_STEM)]
    y_r_inner_glint: Poly = [(y_in_r(Y_TOP), Y_TOP), (y_in_r(Y_TOP) + 2.4, Y_TOP + cap_h), (CX + 2.4, Y_CROTCH), (CX, Y_CROTCH)]
    y_r_outer_glint: Poly = [(y_out_r(Y_TOP) - 2.0, Y_TOP + cap_h), (y_out_r(Y_TOP), Y_TOP), (STEM_R, Y_STEM), (STEM_R - 2.0, Y_STEM)]

    # Cast shadows for over-under weave:
    # 1. Left crossing: A OVER Y (shadow cast by A_left_leg & A_cb onto Y left zone + Y inner left wall)
    y_l_zone: Poly = [(y_out_l(Y_TOP), Y_TOP), (y_in_l(Y_TOP), Y_TOP), (CX, Y_CROTCH), (CX, Y_STEM), (STEM_L, Y_STEM)]
    y_l_inner_wall: Poly = [(y_in_l(Y_TOP), Y_TOP), (CX, Y_CROTCH), (CX + dx, Y_CROTCH + dy), (y_in_l(Y_TOP) + dx, Y_TOP + dy)]
    a_leg_l, a_leg_r, a_cb = a_convex_parts_for_shadow()
    sh_a_on_y = []
    for ap in (a_leg_l, a_cb):
        shifted = translate(ap, 5.5, 6.0)
        for yz in (y_l_zone, y_l_inner_wall):
            c = clip_convex(shifted, yz)
            if len(c) >= 3 and abs(poly_area(c)) > 16.0:
                sh_a_on_y.append(c)

    # 2. Right crossing: Y OVER A (shadow cast by Y right arm + right extrusion wall onto A_right_leg & A_cb)
    y_r_arm_with_wall: Poly = [(y_in_r(Y_TOP), Y_TOP), (y_out_r(Y_TOP), Y_TOP), (y_out_r(Y_TOP) + dx, Y_TOP + dy),
                               (STEM_R + dx, Y_STEM + dy), (STEM_R, Y_STEM), (CX, Y_CROTCH)]
    sh_y_on_a = []
    for off in ((-5.0, -4.5), (5.5, 5.5)):
        c1 = clip_convex(translate(y_r_arm_with_wall, *off), a_leg_r)
        if len(c1) >= 3 and abs(poly_area(c1)) > 16.0:
            sh_y_on_a.append(c1)
    c_cb = clip_convex(translate(y_r_arm_with_wall, -5.0, -4.5), a_cb)
    if len(c_cb) >= 3 and abs(poly_area(c_cb)) > 16.0:
        sh_y_on_a.append(c_cb)

    # 3. Y Right-arm 3D Bridge over A (clipped y=94..168, includes inner bright ribbon, outer deep ribbon, glint, and outer right wall!)
    bridge_clip: Poly = [(CX, 94.0), (240.0, 94.0), (240.0, 168.0), (CX, 168.0)]
    br_r_inner = clip_convex(y_r_inner, bridge_clip)
    br_r_outer = clip_convex(y_r_outer, bridge_clip)
    br_r_glint = clip_convex(y_r_inner_glint, bridge_clip)
    br_r_outer_glint = clip_convex(y_r_outer_glint, bridge_clip)
    y_r_outer_wall: Poly = [(y_out_r(Y_TOP), Y_TOP), (y_out_r(Y_TOP) + dx, Y_TOP + dy), (STEM_R + dx, Y_STEM + dy), (STEM_R, Y_STEM)]
    br_r_wall = clip_convex(y_r_outer_wall, bridge_clip)

    # Mounted dual-step shadow of Y (with extrusion) onto K1 Mist Grey tile
    y_tile_shadow = (
        f'<path fill="#7A848E" fill-opacity="0.22" d="{path_d(translate(y_poly, dx + 4.0, dy + 5.5))}"/>'
        f'<path fill="#67717B" fill-opacity="0.16" d="{path_d(translate(y_poly, dx + 1.8, dy + 2.5))}"/>'
    )

    t_defs, t_bg = k1_tile_defs_and_bg()
    cx_off, cy_off = -dx * 0.42, -dy * 0.42

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256" role="img" aria-labelledby="title">
  <title id="title">AnY · 彭罗斯立体方钢</title>
  <defs>
    {t_defs}
    {high_gloss_defs()}
  </defs>
  {t_bg}
  <g id="emblem" transform="translate(128 126) scale(0.80) translate({fmt(-128 + cx_off)} {fmt(-127 + cy_off)})">
    {y_tile_shadow}
    <g id="y-3d-walls">
      {''.join(f'<path fill="{wall_fill[k]}" d="{path_d(q)}"/>' for k, q in walls)}
    </g>
    <g id="y-glossy-front">
      <path fill="#181C22" d="{path_d(y_poly)}"/>
      <path fill="url(#bc-bright)" d="{path_d(y_l_outer)}"/>
      <path fill="url(#bc-deep)" d="{path_d(y_l_inner)}"/>
      <path fill="url(#bc-bright)" d="{path_d(y_r_inner)}"/>
      <path fill="url(#bc-deep)" d="{path_d(y_r_outer)}"/>
      <path fill="url(#bc-stem-l)" d="{path_d(y_stem_l)}"/>
      <path fill="url(#bc-stem-r)" d="{path_d(y_stem_r)}"/>
      <path fill="#090B0E" d="{path_d(y_foot_bot)}"/>
      <path fill="#DCE4EC" d="{path_d(y_l_cap)}"/>
      <path fill="#B6C0CC" d="{path_d(y_r_cap)}"/>
      <path fill="#E4EBF2" fill-opacity="0.72" d="{path_d(y_l_glint)}"/>
      <path fill="#DCE4EC" fill-opacity="0.65" d="{path_d(y_r_inner_glint)}"/>
      <path fill="#CFD8E3" fill-opacity="0.58" d="{path_d(y_r_outer_glint)}"/>
    </g>
    <g id="shadow-a-over-y">
      {''.join(f'<path fill="#06080B" fill-opacity="0.72" d="{path_d(c)}"/>' for c in sh_a_on_y)}
    </g>
    {penrose_a_group(with_walls=False)}
    <g id="shadow-y-over-a">
      {''.join(f'<path fill="#5C3705" fill-opacity="0.68" d="{path_d(c)}"/>' for c in sh_y_on_a)}
    </g>
    <g id="y-right-3d-bridge">
      <path fill="url(#bc-wall-right)" d="{path_d(br_r_wall)}"/>
      <path fill="url(#bc-bright)" d="{path_d(br_r_inner)}"/>
      <path fill="url(#bc-deep)" d="{path_d(br_r_outer)}"/>
      <path fill="#DCE4EC" fill-opacity="0.68" d="{path_d(br_r_glint)}"/>
      <path fill="#CFD8E3" fill-opacity="0.58" d="{path_d(br_r_outer_glint)}"/>
    </g>
  </g>
</svg>'''


# ---------------------------------------------------------------------------
# P2: Mobius Diamond-Cut Black Chrome (莫比乌斯钻切)
# ---------------------------------------------------------------------------
def build_p2() -> str:
    y_poly = y_full_poly()
    # Divide each Y arm (width 30) into 3 crisp faceted ribbons:
    # Left arm:  5px bright chrome outer chamfer | 12px liquid-black specular | 13px deep obsidian mirror
    # Right arm (Penrose twist!): 13px bright liquid specular inner | 12px dark mirror mid | 5px sharp chrome outer bevel
    w_cham = 5.0
    w_mid = 12.0
    y_stem_hub = (CX, 177.3)
    y_foot_hub = (CX, 208.0)

    def xl1(y: float) -> float:
        return y_out_l(y) + w_cham

    def xl2(y: float) -> float:
        return xl1(y) + w_mid

    def xr1(y: float) -> float:
        return y_in_r(y) + 13.0

    def xr2(y: float) -> float:
        return xr1(y) + w_mid

    # Hub coordinates at y = Y_CROTCH (162.287)
    l_h1 = (xl1(Y_CROTCH), Y_CROTCH)
    l_h2 = (xl2(Y_CROTCH), Y_CROTCH)
    r_h1 = (xr1(Y_CROTCH), Y_CROTCH)
    r_h2 = (xr2(Y_CROTCH), Y_CROTCH)

    cap_h = 3.6
    y_l_cap: Poly = [(y_out_l(Y_TOP), Y_TOP), (y_in_l(Y_TOP), Y_TOP), (y_in_l(Y_TOP) - 1.6, Y_TOP + cap_h), (y_out_l(Y_TOP) + 1.9, Y_TOP + cap_h)]
    y_r_cap: Poly = [(y_in_r(Y_TOP), Y_TOP), (y_out_r(Y_TOP), Y_TOP), (y_out_r(Y_TOP) - 1.9, Y_TOP + cap_h), (y_in_r(Y_TOP) + 1.6, Y_TOP + cap_h)]

    # Left arm 3 ribbons
    y_l_cham: Poly = [(y_out_l(Y_TOP), Y_TOP), (xl1(Y_TOP) + 0.8, Y_TOP + cap_h), l_h1, (STEM_L, Y_STEM)]
    y_l_spec: Poly = [(xl1(Y_TOP) + 0.8, Y_TOP + cap_h), (xl2(Y_TOP) - 0.5, Y_TOP + cap_h), l_h2, y_stem_hub, (STEM_L, Y_STEM), l_h1]
    y_l_obs: Poly = [(xl2(Y_TOP) - 0.5, Y_TOP + cap_h), (y_in_l(Y_TOP), Y_TOP), (CX, Y_CROTCH), y_stem_hub, l_h2]

    # Right arm 3 ribbons (twisted bright-inner -> obsidian-mid -> silver-edge outer!)
    y_r_spec: Poly = [(y_in_r(Y_TOP), Y_TOP), (xr1(Y_TOP) - 0.5, Y_TOP + cap_h), r_h1, y_stem_hub, (CX, Y_CROTCH)]
    y_r_obs: Poly = [(xr1(Y_TOP) - 0.5, Y_TOP + cap_h), (xr2(Y_TOP) + 0.5, Y_TOP + cap_h), r_h2, (STEM_R, Y_STEM), y_stem_hub, r_h1]
    y_r_cham: Poly = [(xr2(Y_TOP) + 0.5, Y_TOP + cap_h), (y_out_r(Y_TOP), Y_TOP), (STEM_R, Y_STEM), r_h2]

    y_stem_l: Poly = [(STEM_L, Y_STEM), y_stem_hub, y_foot_hub, (FOOT_L, Y_FOOT_BOT), (FOOT_L, Y_FOOT_TOP), (STEM_L, Y_FOOT_TOP)]
    y_stem_r: Poly = [y_stem_hub, (STEM_R, Y_STEM), (STEM_R, Y_FOOT_TOP), (FOOT_R, Y_FOOT_TOP), (FOOT_R, Y_FOOT_BOT), y_foot_hub]
    y_foot_bot: Poly = [(FOOT_L, Y_FOOT_BOT), y_foot_hub, (FOOT_R, Y_FOOT_BOT)]

    # Crossings
    y_l_zone: Poly = [(y_out_l(Y_TOP), Y_TOP), (y_in_l(Y_TOP), Y_TOP), (CX, Y_CROTCH), (CX, Y_STEM), (STEM_L, Y_STEM)]
    y_r_zone: Poly = [(y_in_r(Y_TOP), Y_TOP), (y_out_r(Y_TOP), Y_TOP), (STEM_R, Y_STEM), (CX, Y_STEM), (CX, Y_CROTCH)]
    a_leg_l, a_leg_r, a_cb = a_convex_parts_for_shadow()

    sh_a_on_y = []
    for ap in (a_leg_l, a_cb):
        c = clip_convex(translate(ap, 5.0, 5.5), y_l_zone)
        if len(c) >= 3 and abs(poly_area(c)) > 1.0:
            sh_a_on_y.append(c)

    sh_y_on_a = []
    for off in ((-4.8, -4.2), (4.8, 4.8)):
        c1 = clip_convex(translate(y_r_zone, *off), a_leg_r)
        if len(c1) >= 3 and abs(poly_area(c1)) > 1.0:
            sh_y_on_a.append(c1)
    c_cb = clip_convex(translate(y_r_zone, -4.8, -4.2), a_cb)
    if len(c_cb) >= 3 and abs(poly_area(c_cb)) > 1.0:
        sh_y_on_a.append(c_cb)

    bridge_clip: Poly = [(CX, 94.0), (240.0, 94.0), (240.0, 168.0), (CX, 168.0)]
    br_r_spec = clip_convex(y_r_spec, bridge_clip)
    br_r_obs = clip_convex(y_r_obs, bridge_clip)
    br_r_cham = clip_convex(y_r_cham, bridge_clip)

    y_tile_shadow = (
        f'<path fill="#75808A" fill-opacity="0.24" d="{path_d(translate(y_poly, 4.0, 5.5))}"/>'
        f'<path fill="#626D78" fill-opacity="0.16" d="{path_d(translate(y_poly, 1.8, 2.5))}"/>'
    )
    t_defs, t_bg = k1_tile_defs_and_bg()

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256" role="img" aria-labelledby="title">
  <title id="title">AnY · 莫比乌斯钻切</title>
  <defs>
    {t_defs}
    {high_gloss_defs()}
    <linearGradient id="chrome-chamfer" x1="26" y1="40" x2="225" y2="195" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#EEF2F6"/>
      <stop offset="0.35" stop-color="#A8B3C0"/>
      <stop offset="0.65" stop-color="#566270"/>
      <stop offset="1" stop-color="#CBD4DF"/>
    </linearGradient>
  </defs>
  {t_bg}
  <g id="emblem" transform="translate(128 126) scale(0.82) translate(-128 -127)">
    {y_tile_shadow}
    <g id="y-diamond-chrome">
      <path fill="#14181E" d="{path_d(y_poly)}"/>
      <path fill="url(#chrome-chamfer)" d="{path_d(y_l_cham)}"/>
      <path fill="url(#bc-bright)" d="{path_d(y_l_spec)}"/>
      <path fill="url(#bc-deep)" d="{path_d(y_l_obs)}"/>
      <path fill="url(#bc-bright)" d="{path_d(y_r_spec)}"/>
      <path fill="url(#bc-deep)" d="{path_d(y_r_obs)}"/>
      <path fill="url(#chrome-chamfer)" d="{path_d(y_r_cham)}"/>
      <path fill="url(#bc-stem-l)" d="{path_d(y_stem_l)}"/>
      <path fill="url(#bc-stem-r)" d="{path_d(y_stem_r)}"/>
      <path fill="#090B0E" d="{path_d(y_foot_bot)}"/>
      <path fill="#EAEEF3" d="{path_d(y_l_cap)}"/>
      <path fill="#C4CDD8" d="{path_d(y_r_cap)}"/>
    </g>
    <g id="shadow-a-over-y">
      {''.join(f'<path fill="#06080B" fill-opacity="0.72" d="{path_d(c)}"/>' for c in sh_a_on_y)}
    </g>
    {penrose_a_group(with_walls=False)}
    <g id="shadow-y-over-a">
      {''.join(f'<path fill="#5C3705" fill-opacity="0.68" d="{path_d(c)}"/>' for c in sh_y_on_a)}
    </g>
    <g id="y-right-diamond-bridge">
      <path fill="url(#bc-bright)" d="{path_d(br_r_spec)}"/>
      <path fill="url(#bc-deep)" d="{path_d(br_r_obs)}"/>
      <path fill="url(#chrome-chamfer)" d="{path_d(br_r_cham)}"/>
    </g>
  </g>
</svg>'''


# ---------------------------------------------------------------------------
# P3: Penrose Stepped Staircase Relief (彭罗斯阶梯浮雕)
# ---------------------------------------------------------------------------
def build_p3() -> str:
    dx, dy = 10.0, 8.0
    dx_a, dy_a = 4.5, 3.5
    y_poly = y_full_poly()
    walls = extrude_walls(y_poly, dx, dy)
    wall_fill = {"right": "url(#bc-wall-right)", "bot": "#090B0F", "inner": "url(#bc-wall-inner)"}

    # Stepped architectural Penrose inner ledges on Y:
    # Inner stepped terrace along Y's left arm & right arm + two-tier pedestal base
    y_stem_hub = (CX, 177.3)
    y_foot_hub = (CX, 208.0)
    y_arm_hub_l = (0.5 * (y_out_l(Y_CROTCH) + y_in_l(Y_CROTCH)), Y_CROTCH)
    y_arm_hub_r = (0.5 * (y_out_r(Y_CROTCH) + y_in_r(Y_CROTCH)), Y_CROTCH)

    cap_h = 4.0
    y_l_cap: Poly = [(y_out_l(Y_TOP), Y_TOP), (y_in_l(Y_TOP), Y_TOP), (y_in_l(Y_TOP) - 1.8, Y_TOP + cap_h), (y_out_l(Y_TOP) + 2.1, Y_TOP + cap_h)]
    y_r_cap: Poly = [(y_in_r(Y_TOP), Y_TOP), (y_out_r(Y_TOP), Y_TOP), (y_out_r(Y_TOP) - 2.1, Y_TOP + cap_h), (y_in_r(Y_TOP) + 1.8, Y_TOP + cap_h)]
    mid_cap_l = (y_mid_l(Y_TOP), Y_TOP + cap_h)
    mid_cap_r = (y_mid_r(Y_TOP), Y_TOP + cap_h)

    y_l_outer: Poly = [(y_out_l(Y_TOP), Y_TOP), mid_cap_l, y_arm_hub_l, y_stem_hub, (STEM_L, Y_STEM)]
    y_l_inner: Poly = [mid_cap_l, (y_in_l(Y_TOP), Y_TOP), (CX, Y_CROTCH), y_stem_hub, y_arm_hub_l]
    y_r_inner: Poly = [(y_in_r(Y_TOP), Y_TOP), mid_cap_r, y_arm_hub_r, y_stem_hub, (CX, Y_CROTCH)]
    y_r_outer: Poly = [mid_cap_r, (y_out_r(Y_TOP), Y_TOP), (STEM_R, Y_STEM), y_stem_hub, y_arm_hub_r]

    # Exact 60-degree parallel stepped architectural stair ledges on Y
    y_st_l_bot = 166.0
    y_st_r_bot = 154.0
    stair_l: Poly = [
        (y_out_l(Y_TOP + cap_h) + 4.5, Y_TOP + cap_h),
        (y_out_l(Y_TOP + cap_h) + 10.0, Y_TOP + cap_h),
        (y_out_l(y_st_l_bot) + 10.0, y_st_l_bot),
        (y_out_l(y_st_l_bot) + 4.5, y_st_l_bot),
    ]
    stair_r: Poly = [
        (y_in_r(Y_TOP + cap_h) + 4.5, Y_TOP + cap_h),
        (y_in_r(Y_TOP + cap_h) + 10.0, Y_TOP + cap_h),
        (y_in_r(y_st_r_bot) + 10.0, y_st_r_bot),
        (y_in_r(y_st_r_bot) + 4.5, y_st_r_bot),
    ]
    y_r_outer_glint_p3: Poly = [(y_out_r(Y_TOP) - 2.0, Y_TOP + cap_h), (y_out_r(Y_TOP), Y_TOP), (STEM_R, Y_STEM), (STEM_R - 2.0, Y_STEM)]

    # Two-tier stepped pedestal foot
    y_stem_l: Poly = [(STEM_L, Y_STEM), y_stem_hub, y_foot_hub, (FOOT_L, Y_FOOT_BOT), (FOOT_L, Y_FOOT_TOP), (STEM_L, Y_FOOT_TOP)]
    y_stem_r: Poly = [y_stem_hub, (STEM_R, Y_STEM), (STEM_R, Y_FOOT_TOP), (FOOT_R, Y_FOOT_TOP), (FOOT_R, Y_FOOT_BOT), y_foot_hub]
    y_foot_step: Poly = [(FOOT_L + 6.0, Y_FOOT_TOP + 4.0), (FOOT_R - 6.0, Y_FOOT_TOP + 4.0), (FOOT_R - 6.0, Y_FOOT_BOT), (FOOT_L + 6.0, Y_FOOT_BOT)]
    y_foot_bot: Poly = [(FOOT_L, Y_FOOT_BOT), y_foot_hub, (FOOT_R, Y_FOOT_BOT)]

    # Penrose cross-over shadows (filter micro-slivers < 16 sq px)
    y_l_zone: Poly = [(y_out_l(Y_TOP), Y_TOP), (y_in_l(Y_TOP), Y_TOP), (CX, Y_CROTCH), (CX, Y_STEM), (STEM_L, Y_STEM)]
    y_l_inner_wall: Poly = [(y_in_l(Y_TOP), Y_TOP), (CX, Y_CROTCH), (CX + dx, Y_CROTCH + dy), (y_in_l(Y_TOP) + dx, Y_TOP + dy)]
    a_leg_l, a_leg_r, a_cb = a_convex_parts_for_shadow()

    sh_a_on_y = []
    for ap in (a_leg_l, a_cb):
        shifted = translate(ap, 6.0 + dx_a, 6.5 + dy_a)
        for yz in (y_l_zone, y_l_inner_wall):
            c = clip_convex(shifted, yz)
            if len(c) >= 3 and abs(poly_area(c)) > 16.0:
                sh_a_on_y.append(c)

    y_r_arm_with_wall: Poly = [(y_in_r(Y_TOP), Y_TOP), (y_out_r(Y_TOP), Y_TOP), (y_out_r(Y_TOP) + dx, Y_TOP + dy),
                               (STEM_R + dx, Y_STEM + dy), (STEM_R, Y_STEM), (CX, Y_CROTCH)]
    sh_y_on_a = []
    for off in ((-5.5, -4.8), (6.0, 6.0)):
        c1 = clip_convex(translate(y_r_arm_with_wall, *off), a_leg_r)
        if len(c1) >= 3 and abs(poly_area(c1)) > 16.0:
            sh_y_on_a.append(c1)
    c_cb = clip_convex(translate(y_r_arm_with_wall, -5.5, -4.8), a_cb)
    if len(c_cb) >= 3 and abs(poly_area(c_cb)) > 16.0:
        sh_y_on_a.append(c_cb)

    bridge_clip: Poly = [(CX, 94.0), (242.0, 94.0), (242.0, 168.0), (CX, 168.0)]
    br_r_inner = clip_convex(y_r_inner, bridge_clip)
    br_r_outer = clip_convex(y_r_outer, bridge_clip)
    br_r_stair = clip_convex(stair_r, bridge_clip)
    br_r_outer_glint = clip_convex(y_r_outer_glint_p3, bridge_clip)
    y_r_outer_wall: Poly = [(y_out_r(Y_TOP), Y_TOP), (y_out_r(Y_TOP) + dx, Y_TOP + dy), (STEM_R + dx, Y_STEM + dy), (STEM_R, Y_STEM)]
    br_r_wall = clip_convex(y_r_outer_wall, bridge_clip)

    y_tile_shadow = (
        f'<path fill="#78828C" fill-opacity="0.24" d="{path_d(translate(y_poly, dx + 4.5, dy + 6.0))}"/>'
        f'<path fill="#646E78" fill-opacity="0.16" d="{path_d(translate(y_poly, dx + 2.0, dy + 2.8))}"/>'
    )
    t_defs, t_bg = k1_tile_defs_and_bg()
    cx_off, cy_off = -dx * 0.44, -dy * 0.44

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256" role="img" aria-labelledby="title">
  <title id="title">AnY · 彭罗斯阶梯浮雕</title>
  <defs>
    {t_defs}
    {high_gloss_defs()}
  </defs>
  {t_bg}
  <g id="emblem" transform="translate(128 126) scale(0.79) translate({fmt(-128 + cx_off)} {fmt(-127 + cy_off)})">
    {y_tile_shadow}
    <g id="y-3d-walls">
      {''.join(f'<path fill="{wall_fill[k]}" d="{path_d(q)}"/>' for k, q in walls)}
    </g>
    <g id="y-stepped-front">
      <path fill="#181C22" d="{path_d(y_poly)}"/>
      <path fill="url(#bc-bright)" d="{path_d(y_l_outer)}"/>
      <path fill="url(#bc-deep)" d="{path_d(y_l_inner)}"/>
      <path fill="url(#bc-bright)" d="{path_d(y_r_inner)}"/>
      <path fill="url(#bc-deep)" d="{path_d(y_r_outer)}"/>
      <path fill="#C7D2DE" fill-opacity="0.45" d="{path_d(stair_l)}"/>
      <path fill="#C7D2DE" fill-opacity="0.38" d="{path_d(stair_r)}"/>
      <path fill="url(#bc-stem-l)" d="{path_d(y_stem_l)}"/>
      <path fill="url(#bc-stem-r)" d="{path_d(y_stem_r)}"/>
      <path fill="#202630" fill-opacity="0.55" d="{path_d(y_foot_step)}"/>
      <path fill="#090B0E" d="{path_d(y_foot_bot)}"/>
      <path fill="#E3EAF1" d="{path_d(y_l_cap)}"/>
      <path fill="#BAC4D0" d="{path_d(y_r_cap)}"/>
      <path fill="#CFD8E3" fill-opacity="0.58" d="{path_d(y_r_outer_glint_p3)}"/>
    </g>
    <g id="shadow-a-over-y">
      {''.join(f'<path fill="#06080B" fill-opacity="0.72" d="{path_d(c)}"/>' for c in sh_a_on_y)}
    </g>
    {penrose_a_group(with_walls=True, dx_a=dx_a, dy_a=dy_a)}
    <g id="shadow-y-over-a">
      {''.join(f'<path fill="#5C3705" fill-opacity="0.72" d="{path_d(c)}"/>' for c in sh_y_on_a)}
    </g>
    <g id="y-right-3d-bridge">
      <path fill="url(#bc-wall-right)" d="{path_d(br_r_wall)}"/>
      <path fill="url(#bc-bright)" d="{path_d(br_r_inner)}"/>
      <path fill="url(#bc-deep)" d="{path_d(br_r_outer)}"/>
      <path fill="#C7D2DE" fill-opacity="0.42" d="{path_d(br_r_stair)}"/>
      <path fill="#CFD8E3" fill-opacity="0.58" d="{path_d(br_r_outer_glint)}"/>
    </g>
  </g>
</svg>'''


def main() -> None:
    for fname, fn in [
        ("p1-penrose-extruded.svg", build_p1),
        ("p2-penrose-diamond.svg", build_p2),
        ("p3-penrose-stairs.svg", build_p3),
    ]:
        path = os.path.join(OUT_DIR, fname)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(fn() + "\n")
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
