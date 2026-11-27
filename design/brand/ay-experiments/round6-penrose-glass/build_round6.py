#!/usr/bin/env python3
"""Generate Round 6: Elevated Slim-Leg Penrose A + Thick Extended Crossbar + Silvered-Glass Plaque.

Variants:
  S1: s1-penrose-weave-glass.svg     - 4-crossing Escher/Penrose weave + wide bar + mineral silvered glass
  S2: s2-penrose-tribar-mirror.svg   - Classic 2-crossing Penrose Tri-Bar + flush bar + cool mirror glass
  S3: s3-penrose-escher-crystal.svg  - 4-crossing Escher weave + 3D extruded A & Y beams + crystal silver glass
"""
from __future__ import annotations

import math
import os
import sys
from typing import Dict, List, Tuple

Point = Tuple[float, float]
Poly = List[Point]

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
R5_DIR = os.path.abspath(os.path.join(OUT_DIR, "..", "round5-penrose-gloss"))
sys.path.insert(0, R5_DIR)
from build_round5 import (  # noqa: E402
    CX,
    FOOT_L,
    FOOT_R,
    S3,
    STEM_L,
    STEM_R,
    W_Y,
    Y_CROTCH,
    Y_FOOT_BOT,
    Y_FOOT_TOP,
    Y_STEM,
    clip_convex,
    clip_halfplane,
    extrude_walls,
    fmt,
    path_d,
    poly_area,
    rounded_rect_d,
    translate,
    y_full_poly,
    y_in_l,
    y_in_r,
    y_mid_l,
    y_mid_r,
    y_out_l,
    y_out_r,
)

# Elevated Y top slightly to balance elevated A
Y_TOP = 38.0

# Elevated, slim-leg, thick-crossbar Penrose A constants
A_APEX_Y = 52.0
A_BOT = 162.0
W_A = 14.5
U_A = W_A * 0.5  # 7.25

P_TOP: Point = (CX, A_APEX_Y)
P_LM_RO: Point = (CX + U_A * 0.5, A_APEX_Y + U_A * S3 * 0.5)
P_LI_RM: Point = (CX + U_A * 0.5, A_APEX_Y + 1.5 * U_A * S3)
P_LI_RI: Point = (CX, A_APEX_Y + 2.0 * U_A * S3)


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


def strip_along(p1: Point, p2: Point, half_w: float) -> Poly:
    """Return thin crisp quad strip centered on segment p1->p2 (zero SVG stroke)."""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    ln = math.hypot(dx, dy)
    if ln < 1e-6:
        return []
    nx, ny = -dy / ln * half_w, dx / ln * half_w
    return [(p1[0] + nx, p1[1] + ny), (p2[0] + nx, p2[1] + ny), (p2[0] - nx, p2[1] - ny), (p1[0] - nx, p1[1] - ny)]


def silvered_glass_defs_and_bg(cfg: Dict[str, object]) -> Tuple[str, str]:
    """Build thick beveled crystal glass over a brushed/polished silver mirror backing."""
    s_stops = cfg["silver_bg"]
    rim_o = cfg["rim_outer"]
    rim_i = cfg["rim_inner"]
    thick_inner = bool(cfg.get("double_bevel", False))

    r_out = rounded_rect_d(0, 0, 256, 256, 56)
    r_mid = rounded_rect_d(2.5, 2.5, 251, 251, 53.5, ccw=True)
    outer_ring_d = r_out + " " + r_mid

    r_mid_cw = rounded_rect_d(2.5, 2.5, 251, 251, 53.5)
    in_off = 6.8 if thick_inner else 5.5
    r_in_ccw = rounded_rect_d(in_off, in_off, 256 - 2 * in_off, 256 - 2 * in_off, 56 - in_off, ccw=True)
    inner_ring_d = r_mid_cw + " " + r_in_ccw

    # Full-span diagonal glass surface glare stripes (no mid-canvas horizontal cutoffs!)
    glare_band_1: Poly = [(0.0, 0.0), (146.0, 0.0), (0.0, 206.0)]
    glare_band_2: Poly = [(164.0, 0.0), (196.0, 0.0), (16.0, 256.0), (0.0, 256.0), (0.0, 232.0)]
    defs = f"""
    <linearGradient id="silver-mirror" x1="14" y1="8" x2="242" y2="248" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="{s_stops[0]}"/>
      <stop offset="0.26" stop-color="{s_stops[1]}"/>
      <stop offset="0.52" stop-color="{s_stops[2]}"/>
      <stop offset="0.74" stop-color="{s_stops[3]}"/>
      <stop offset="1" stop-color="{s_stops[4]}"/>
    </linearGradient>
    <linearGradient id="glass-rim-outer" x1="12" y1="10" x2="244" y2="246" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="{rim_o[0]}"/>
      <stop offset="0.5" stop-color="{rim_o[1]}"/>
      <stop offset="1" stop-color="{rim_o[2]}"/>
    </linearGradient>
    <linearGradient id="glass-rim-inner" x1="16" y1="16" x2="240" y2="240" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="{rim_i[0]}"/>
      <stop offset="0.5" stop-color="{rim_i[1]}"/>
      <stop offset="1" stop-color="{rim_i[2]}"/>
    </linearGradient>
    <linearGradient id="glass-glare" x1="12" y1="12" x2="180" y2="190" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#F2F6FA" stop-opacity="0.46"/>
      <stop offset="0.55" stop-color="#EBF2F7" stop-opacity="0.16"/>
      <stop offset="1" stop-color="#DCE5EE" stop-opacity="0.0"/>
    </linearGradient>
    <clipPath id="glass-face-clip">
      <rect x="{in_off:g}" y="{in_off:g}" width="{256 - 2 * in_off:g}" height="{256 - 2 * in_off:g}" rx="{56 - in_off:g}"/>
    </clipPath>"""

    bg = f"""
  <g id="silvered-glass-plaque">
    <!-- Rear brushed/polished silver mirror backing -->
    <rect x="0" y="0" width="256" height="256" rx="56" fill="url(#silver-mirror)"/>
    <!-- Front-surface crystal glass reflection sheen clipped to inner bevel -->
    <g clip-path="url(#glass-face-clip)">
      <path fill="url(#glass-glare)" d="{path_d(glare_band_1)}"/>
      <path fill="#F2F6FA" fill-opacity="0.20" d="{path_d(glare_band_2)}"/>
    </g>
    <!-- Thick mineral glass chamfered edge refraction rings -->
    <path fill="url(#glass-rim-inner)" fill-rule="evenodd" d="{inner_ring_d}"/>
    <path fill="url(#glass-rim-outer)" fill-rule="evenodd" d="{outer_ring_d}"/>
  </g>"""
    return defs, bg


def high_gloss_and_penrose_defs() -> str:
    return """
    <!-- Liquid black-chrome Y gradients -->
    <linearGradient id="bc-bright" x1="24" y1="34" x2="215" y2="215" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#E6EEF6"/>
      <stop offset="0.16" stop-color="#8E9BAB"/>
      <stop offset="0.40" stop-color="#191F27"/>
      <stop offset="0.58" stop-color="#647385"/>
      <stop offset="0.78" stop-color="#12161C"/>
      <stop offset="1" stop-color="#38424F"/>
    </linearGradient>
    <linearGradient id="bc-deep" x1="95" y1="38" x2="230" y2="215" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#4B5665"/>
      <stop offset="0.32" stop-color="#161B22"/>
      <stop offset="0.58" stop-color="#394452"/>
      <stop offset="0.85" stop-color="#0C0F14"/>
      <stop offset="1" stop-color="#1A2028"/>
    </linearGradient>
    <linearGradient id="bc-wall-right" x1="120" y1="38" x2="235" y2="220" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#909DAB"/>
      <stop offset="0.28" stop-color="#2B323D"/>
      <stop offset="0.55" stop-color="#5E6B7C"/>
      <stop offset="0.82" stop-color="#13171E"/>
      <stop offset="1" stop-color="#242B35"/>
    </linearGradient>
    <linearGradient id="bc-wall-inner" x1="55" y1="38" x2="132" y2="165" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#A8B5C4"/>
      <stop offset="0.45" stop-color="#424D5C"/>
      <stop offset="1" stop-color="#181E26"/>
    </linearGradient>
    <linearGradient id="bc-stem-l" x1="100" y1="168" x2="128" y2="215" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#9CA8B7"/>
      <stop offset="0.38" stop-color="#343C48"/>
      <stop offset="0.72" stop-color="#4D5868"/>
      <stop offset="1" stop-color="#151920"/>
    </linearGradient>
    <linearGradient id="bc-stem-r" x1="128" y1="168" x2="156" y2="215" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#444F5D"/>
      <stop offset="0.52" stop-color="#171C23"/>
      <stop offset="1" stop-color="#0B0E13"/>
    </linearGradient>

    <!-- Ultra-contrast 3-tone Penrose 18K Gold gradients -->
    <linearGradient id="gold-bright" x1="54" y1="52" x2="195" y2="132" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#FAF1C4"/>
      <stop offset="0.30" stop-color="#F4CF6C"/>
      <stop offset="0.56" stop-color="#E4B33A"/>
      <stop offset="0.78" stop-color="#F7DF8E"/>
      <stop offset="1" stop-color="#CE9722"/>
    </linearGradient>
    <linearGradient id="gold-mid" x1="78" y1="58" x2="192" y2="164" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#E4A832"/>
      <stop offset="0.45" stop-color="#BC7E14"/>
      <stop offset="0.75" stop-color="#CE8F1E"/>
      <stop offset="1" stop-color="#945D08"/>
    </linearGradient>
    <linearGradient id="gold-deep" x1="60" y1="104" x2="200" y2="164" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#704207"/>
      <stop offset="0.48" stop-color="#482703"/>
      <stop offset="0.78" stop-color="#5E3505"/>
      <stop offset="1" stop-color="#341B02"/>
    </linearGradient>"""


def build_elevated_penrose_a(
    b_top: float,
    b_bot: float,
    bar_ext: float,
    with_walls: bool = False,
    dx_a: float = 0.0,
    dy_a: float = 0.0,
) -> Tuple[str, str, Dict[str, object]]:
    """Build elevated slim-leg Penrose A with thick extended horizontal beam.

    Returns (a_svg, a_backing_path_d, geometry_dict_for_bridges_and_shadows).
    """
    b_mid = 0.5 * (b_top + b_bot)
    # 60-degree outer bar bounds parallel to Y arms
    x_bar_l = lambda y: y_out_l(y) - bar_ext
    x_bar_r = lambda y: y_out_r(y) + bar_ext

    # Complete backing silhouette (evenodd)
    a_back_d = (
        f"M{fmt(P_TOP[0])} {fmt(P_TOP[1])}"
        f"L{fmt(a_ro(b_top))} {fmt(b_top)}"
        f"H{fmt(x_bar_r(b_top))}"
        f"L{fmt(x_bar_r(b_bot))} {fmt(b_bot)}"
        f"H{fmt(a_ro(b_bot))}"
        f"L{fmt(a_ro(A_BOT))} {fmt(A_BOT)}"
        f"H{fmt(a_ri(A_BOT))}"
        f"L{fmt(a_ri(b_bot))} {fmt(b_bot)}"
        f"H{fmt(a_li(b_bot))}"
        f"L{fmt(a_li(A_BOT))} {fmt(A_BOT)}"
        f"H{fmt(a_lo(A_BOT))} "
        f"L{fmt(a_lo(b_bot))} {fmt(b_bot)}"
        f"H{fmt(x_bar_l(b_bot))}"
        f"L{fmt(x_bar_l(b_top))} {fmt(b_top)}"
        f"H{fmt(a_lo(b_top))}Z "
        f"M{fmt(P_LI_RI[0])} {fmt(P_LI_RI[1])}"
        f"L{fmt(a_li(b_top))} {fmt(b_top)}"
        f"H{fmt(a_ri(b_top))}Z"
    )

    # Ribbon 1 (Brightest Gold): Outer Left Leg (L_o..L_m) + Left Bar Extension Top + Inner Bar Top (B_TOP..B_MID) + Right Bar Extension Top
    r1_main: Poly = [
        P_TOP,
        P_LM_RO,
        (a_lm(b_top), b_top),
        (a_ri(b_top), b_top),
        (a_ri(b_mid), b_mid),
        (a_lm(b_mid), b_mid),
        (a_lm(A_BOT), A_BOT),
        (a_lo(A_BOT), A_BOT),
        (a_lo(b_mid), b_mid),
        (x_bar_l(b_mid), b_mid),
        (x_bar_l(b_top), b_top),
        (a_lo(b_top), b_top),
    ]
    r1_ext_r: Poly = [
        (a_ro(b_top), b_top),
        (x_bar_r(b_top), b_top),
        (x_bar_r(b_mid), b_mid),
        (a_ro(b_mid), b_mid),
    ]

    # Ribbon 2 (Rich 18K Mid-Gold): Outer Right Leg (R_m..R_o) folding over Apex into Inner Left Leg (L_m..L_i) + lower inner-left leg
    r2_main: Poly = [
        P_LM_RO,
        (a_ro(A_BOT), A_BOT),
        (a_rm(A_BOT), A_BOT),
        P_LI_RM,
        (a_li(b_top), b_top),
        (a_lm(b_top), b_top),
    ]
    r2_foot_l: Poly = [
        (a_lm(b_bot), b_bot),
        (a_li(b_bot), b_bot),
        (a_li(A_BOT), A_BOT),
        (a_lm(A_BOT), A_BOT),
    ]

    # Ribbon 3 (Deep Espresso-Bronze Shadow): Bottom Bar (B_MID..B_BOT) folding into Inner Right Leg (R_i..R_m) + Left & Right Bar Extensions Bottom
    r3_main: Poly = [
        P_LI_RM,
        (a_rm(A_BOT), A_BOT),
        (a_ri(A_BOT), A_BOT),
        (a_ri(b_bot), b_bot),
        (a_lm(b_bot), b_bot),
        (a_lm(b_mid), b_mid),
        (a_ri(b_mid), b_mid),
        P_LI_RI,
    ]
    r3_ext_l: Poly = [
        (x_bar_l(b_mid), b_mid),
        (a_lo(b_mid), b_mid),
        (a_lo(b_bot), b_bot),
        (x_bar_l(b_bot), b_bot),
    ]
    r3_ext_r: Poly = [
        (a_ro(b_mid), b_mid),
        (x_bar_r(b_mid), b_mid),
        (x_bar_r(b_bot), b_bot),
        (a_ro(b_bot), b_bot),
    ]

    # Crisp Penrose miter fold crease lines (dark bronze creases + specular gold knife-edge highlights)
    dark_creases = [
        strip_along(P_LM_RO, (a_lm(b_top), b_top), 0.55),
        strip_along((a_lm(b_mid), b_mid), (a_lm(A_BOT), A_BOT), 0.55),
        strip_along(P_LI_RM, (a_rm(A_BOT), A_BOT), 0.6),
        strip_along((x_bar_l(b_mid), b_mid), (a_lm(b_mid), b_mid), 0.6),
        strip_along((a_lm(b_mid), b_mid), (a_ri(b_mid), b_mid), 0.65),
        strip_along((a_ro(b_mid), b_mid), (x_bar_r(b_mid), b_mid), 0.6),
        strip_along((a_lo(b_top), b_top), (a_lo(b_bot), b_bot), 0.55),
        strip_along((a_ro(b_top), b_top), (a_ro(b_bot), b_bot), 0.55),
    ]
    glints = [
        [P_TOP, (P_TOP[0] + 1.0, P_TOP[1] + 1.7), (a_lo(A_BOT) + 1.9, A_BOT), (a_lo(A_BOT), A_BOT)],
        [(x_bar_l(b_top), b_top), (a_lo(b_top), b_top), (a_lo(b_top) - 0.9, b_top + 1.6), (x_bar_l(b_top) + 0.9, b_top + 1.6)],
        [(a_lm(b_top), b_top), (a_ri(b_top), b_top), (a_ri(b_top) + 0.9, b_top + 1.6), (a_lm(b_top) - 0.9, b_top + 1.6)],
        [(a_ro(b_top), b_top), (x_bar_r(b_top), b_top), (x_bar_r(b_top) + 0.9, b_top + 1.6), (a_ro(b_top) - 0.9, b_top + 1.6)],
    ]

    walls_svg = ""
    if with_walls:
        a_outer_poly: Poly = [
            P_TOP,
            (a_ro(b_top), b_top),
            (x_bar_r(b_top), b_top),
            (x_bar_r(b_bot), b_bot),
            (a_ro(b_bot), b_bot),
            (a_ro(A_BOT), A_BOT),
            (a_ri(A_BOT), A_BOT),
            (a_ri(b_bot), b_bot),
            (a_li(b_bot), b_bot),
            (a_li(A_BOT), A_BOT),
            (a_lo(A_BOT), A_BOT),
            (a_lo(b_bot), b_bot),
            (x_bar_l(b_bot), b_bot),
            (x_bar_l(b_top), b_top),
            (a_lo(b_top), b_top),
        ]
        walls = extrude_walls(a_outer_poly, dx_a, dy_a)
        wall_fills = {"right": "#7C4E09", "bot": "#4B2B03", "inner": "#966313"}
        walls_svg = "".join(f'<path fill="{wall_fills[k]}" d="{path_d(q)}"/>' for k, q in walls)
        hole: Poly = [P_LI_RI, (a_ri(b_top), b_top), (a_li(b_top), b_top)]
        hl_raw: Poly = [P_LI_RI, (a_li(b_top), b_top), (a_li(b_top) + dx_a, b_top + dy_a), (P_LI_RI[0] + dx_a, P_LI_RI[1] + dy_a)]
        hl_clip = clip_convex(hl_raw, hole)
        if len(hl_clip) >= 3 and abs(poly_area(hl_clip)) > 8.0:
            walls_svg += f'<path fill="#633A05" d="{path_d(hl_clip)}"/>'

    a_svg = f"""
  <g id="a-penrose-gold">
    {walls_svg}
    <path fill="#B67F18" fill-rule="evenodd" d="{a_back_d}"/>
    <path fill="url(#gold-deep)" d="{path_d(r3_main)}"/>
    <path fill="url(#gold-deep)" d="{path_d(r3_ext_l)}"/>
    <path fill="url(#gold-deep)" d="{path_d(r3_ext_r)}"/>
    <path fill="url(#gold-mid)" d="{path_d(r2_main)}"/>
    <path fill="url(#gold-mid)" d="{path_d(r2_foot_l)}"/>
    <path fill="url(#gold-bright)" d="{path_d(r1_main)}"/>
    <path fill="url(#gold-bright)" d="{path_d(r1_ext_r)}"/>
    {''.join(f'<path fill="#381D02" fill-opacity="0.72" d="{path_d(c)}"/>' for c in dark_creases if len(c) >= 3)}
    {''.join(f'<path fill="#FAF3CC" fill-opacity="0.88" d="{path_d(g)}"/>' for g in glints)}
  </g>"""

    # Convex parts for accurate shadow clipping
    left_leg_c: Poly = [P_TOP, (P_TOP[0] + W_A, P_TOP[1]), (a_li(A_BOT), A_BOT), (a_lo(A_BOT), A_BOT)]
    right_leg_c: Poly = [(P_TOP[0] - W_A, P_TOP[1]), P_TOP, (a_ro(A_BOT), A_BOT), (a_ri(A_BOT), A_BOT)]
    full_bar_c: Poly = [(x_bar_l(b_top), b_top), (x_bar_r(b_top), b_top), (x_bar_r(b_bot), b_bot), (x_bar_l(b_bot), b_bot)]
    right_bar_c: Poly = [(a_li(b_top), b_top), (x_bar_r(b_top), b_top), (x_bar_r(b_bot), b_bot), (a_li(b_bot), b_bot)]
    left_ext_bar_c: Poly = [(x_bar_l(b_top), b_top), (a_lo(b_top), b_top), (a_lo(b_bot), b_bot), (x_bar_l(b_bot), b_bot)]

    geom = {
        "b_top": b_top,
        "b_bot": b_bot,
        "left_leg": left_leg_c,
        "right_leg": right_leg_c,
        "full_bar": full_bar_c,
        "right_bar": right_bar_c,
        "left_ext_bar": left_ext_bar_c,
        "x_bar_l": x_bar_l,
        "x_bar_r": x_bar_r,
    }
    return a_svg, a_back_d, geom


def build_variant(
    filename: str,
    title: str,
    glass_cfg: Dict[str, object],
    b_top: float,
    b_bot: float,
    bar_ext: float,
    dx_y: float,
    dy_y: float,
    four_crossing: bool,
    stepped_y: bool,
    extrude_a: bool,
) -> str:
    # Build Y geometry
    y_poly: Poly = [
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
    walls = extrude_walls(y_poly, dx_y, dy_y)
    wall_fill = {"right": "url(#bc-wall-right)", "bot": "#090B0F", "inner": "url(#bc-wall-inner)"}

    y_stem_hub = (CX, 177.3)
    y_foot_hub = (CX, 208.0)
    y_arm_hub_l = (0.5 * (y_out_l(Y_CROTCH) + y_in_l(Y_CROTCH)), Y_CROTCH)
    y_arm_hub_r = (0.5 * (y_out_r(Y_CROTCH) + y_in_r(Y_CROTCH)), Y_CROTCH)

    cap_h = 3.8 if stepped_y else 3.5
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

    y_l_glint: Poly = [(y_out_l(Y_TOP), Y_TOP), (y_out_l(Y_TOP) + 2.4, Y_TOP + cap_h), (STEM_L + 2.2, Y_STEM), (STEM_L, Y_STEM)]
    y_r_inner_glint: Poly = [(y_in_r(Y_TOP), Y_TOP), (y_in_r(Y_TOP) + 2.4, Y_TOP + cap_h), (CX + 2.4, Y_CROTCH), (CX, Y_CROTCH)]
    y_r_outer_glint: Poly = [(y_out_r(Y_TOP) - 2.0, Y_TOP + cap_h), (y_out_r(Y_TOP), Y_TOP), (STEM_R, Y_STEM), (STEM_R - 2.0, Y_STEM)]

    # Optional stepped ledges for S3
    stair_l_svg, stair_r_poly, st_l = "", [], []
    if stepped_y:
        st_l = [
            (y_out_l(Y_TOP + cap_h) + 4.5, Y_TOP + cap_h),
            (y_out_l(Y_TOP + cap_h) + 10.0, Y_TOP + cap_h),
            (y_out_l(166.0) + 10.0, 166.0),
            (y_out_l(166.0) + 4.5, 166.0),
        ]
        stair_r_poly = [
            (y_in_r(Y_TOP + cap_h) + 4.5, Y_TOP + cap_h),
            (y_in_r(Y_TOP + cap_h) + 10.0, Y_TOP + cap_h),
            (y_in_r(154.0) + 10.0, 154.0),
            (y_in_r(154.0) + 4.5, 154.0),
        ]
        stair_l_svg = f'<path fill="#C7D2DE" fill-opacity="0.45" d="{path_d(st_l)}"/>'

    dx_a, dy_a = (4.5, 3.5) if extrude_a else (0.0, 0.0)
    a_svg, a_back_d, geom = build_elevated_penrose_a(b_top, b_bot, bar_ext, with_walls=extrude_a, dx_a=dx_a, dy_a=dy_a)

    # Left & Right Y arm zones for shadow clipping
    y_l_zone: Poly = [(y_out_l(Y_TOP), Y_TOP), (y_in_l(Y_TOP), Y_TOP), (CX, Y_CROTCH), (CX, Y_STEM), (STEM_L, Y_STEM)]
    y_l_inner_wall: Poly = [(y_in_l(Y_TOP), Y_TOP), (CX, Y_CROTCH), (CX + dx_y, Y_CROTCH + dy_y), (y_in_l(Y_TOP) + dx_y, Y_TOP + dy_y)]
    y_r_zone: Poly = [(y_in_r(Y_TOP), Y_TOP), (y_out_r(Y_TOP), Y_TOP), (STEM_R, Y_STEM), (CX, Y_STEM), (CX, Y_CROTCH)]

    # Cast shadows of A onto Y:
    # Left leg always casts shadow on Y left arm; Right extended crossbar casts shadow on Y right arm below b_bot!
    sh_a_on_y = []
    for ap in (geom["left_leg"], geom["right_bar"] if four_crossing else geom["full_bar"]):
        shifted = translate(ap, 5.5 + dx_a, 6.0 + dy_a)
        for yz in (y_l_zone, y_l_inner_wall, y_r_zone):
            c = clip_convex(shifted, yz)
            if len(c) >= 3 and abs(poly_area(c)) > 18.0:
                sh_a_on_y.append(c)

    # Right crossing: Y right arm OVER A right leg (strictly y >= b_bot if four_crossing, else y >= 86)
    br_y_start = b_bot if four_crossing else 86.0
    bridge_clip_r: Poly = [(CX, br_y_start), (242.0, br_y_start), (242.0, 168.0), (CX, 168.0)]
    br_r_inner = clip_convex(y_r_inner, bridge_clip_r)
    br_r_outer = clip_convex(y_r_outer, bridge_clip_r)
    br_r_glint = clip_convex(y_r_inner_glint, bridge_clip_r)
    br_r_outer_glint = clip_convex(y_r_outer_glint, bridge_clip_r)
    y_r_outer_wall: Poly = [(y_out_r(Y_TOP), Y_TOP), (y_out_r(Y_TOP) + dx_y, Y_TOP + dy_y), (STEM_R + dx_y, Y_STEM + dy_y), (STEM_R, Y_STEM)]
    br_r_wall = clip_convex(y_r_outer_wall, bridge_clip_r)
    br_r_stair = clip_convex(stair_r_poly, bridge_clip_r) if stepped_y else []

    # Shadows cast by Y right bridge onto A right leg
    y_r_arm_with_wall: Poly = [(y_in_r(Y_TOP), Y_TOP), (y_out_r(Y_TOP), Y_TOP), (y_out_r(Y_TOP) + dx_y, Y_TOP + dy_y),
                               (STEM_R + dx_y, Y_STEM + dy_y), (STEM_R, Y_STEM), (CX, Y_CROTCH)]
    y_r_bridge_shadow_src = clip_convex(y_r_arm_with_wall, bridge_clip_r)
    sh_y_on_a = []
    for off in ((-4.5, -4.0), (5.5, 5.5)):
        c1 = clip_convex(translate(y_r_bridge_shadow_src, *off), geom["right_leg"])
        if len(c1) >= 3 and abs(poly_area(c1)) > 16.0:
            sh_y_on_a.append(c1)

    # Left crossing 4-way weave: Y left arm bridges OVER A's extended left crossbar (strictly x <= a_lo(y))!
    left_bridge_svg = ""
    if four_crossing:
        # Halfplane keeping x <= a_lo(y): (x - (CX - (y - A_APEX_Y)/S3)) <= 0 -> -x - y/S3 + (CX + A_APEX_Y/S3) >= 0
        hp_a = -1.0
        hp_b = -1.0 / S3
        hp_c = CX + A_APEX_Y / S3
        band_l: Poly = [(36.0, b_top - 4.0), (128.0, b_top - 4.0), (128.0, b_bot + 4.0), (36.0, b_bot + 4.0)]
        br_l_outer = clip_halfplane(clip_convex(y_l_outer, band_l), hp_a, hp_b, hp_c)
        br_l_inner = clip_halfplane(clip_convex(y_l_inner, band_l), hp_a, hp_b, hp_c)
        br_l_glint = clip_halfplane(clip_convex(y_l_glint, band_l), hp_a, hp_b, hp_c)
        br_l_stair = clip_halfplane(clip_convex(st_l, band_l), hp_a, hp_b, hp_c) if stepped_y and len(st_l) >= 3 else []
        # Cast shadow from Y left bridge onto A's extended left crossbar
        sh_yl_on_bar = []
        y_l_bridge_src = clip_halfplane(clip_convex(y_l_zone, band_l), hp_a, hp_b, hp_c)
        if len(y_l_bridge_src) >= 3:
            for off in ((-5.0, -3.0), (4.5, 4.5)):
                c = clip_convex(translate(y_l_bridge_src, *off), geom["left_ext_bar"])
                if len(c) >= 3 and abs(poly_area(c)) > 14.0:
                    sh_yl_on_bar.append(c)

        left_bridge_svg = f"""
    <g id="shadow-y-left-over-bar">
      {''.join(f'<path fill="#3D2202" fill-opacity="0.72" d="{path_d(c)}"/>' for c in sh_yl_on_bar)}
    </g>
    <g id="y-left-bridge-over-bar">
      {f'<path fill="url(#bc-bright)" d="{path_d(br_l_outer)}"/>' if len(br_l_outer) >= 3 else ''}
      {f'<path fill="url(#bc-deep)" d="{path_d(br_l_inner)}"/>' if len(br_l_inner) >= 3 else ''}
      {f'<path fill="#C7D2DE" fill-opacity="0.45" d="{path_d(br_l_stair)}"/>' if len(br_l_stair) >= 3 else ''}
      {f'<path fill="#E4EBF2" fill-opacity="0.72" d="{path_d(br_l_glint)}"/>' if len(br_l_glint) >= 3 else ''}
    </g>"""

    # Through-glass offset shadow projected onto the rear silver mirror plate (+6.0, +8.5)
    y_mirror_sh = (
        f'<path fill="#4F5E6D" fill-opacity="0.22" d="{path_d(translate(y_poly, dx_y + 6.0, dy_y + 8.5))}"/>'
        f'<path fill="#414F5D" fill-opacity="0.14" d="{path_d(translate(y_poly, dx_y + 3.0, dy_y + 4.5))}"/>'
        f'<path fill="#4F5E6D" fill-opacity="0.18" fill-rule="evenodd" d="{a_back_d}" transform="translate({fmt(dx_a + 6.0)} {fmt(dy_a + 8.5)})"/>'
    )

    t_defs, t_bg = silvered_glass_defs_and_bg(glass_cfg)
    cx_off, cy_off = -dx_y * 0.42, -dy_y * 0.42

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256" role="img" aria-labelledby="title">
  <title id="title">{title}</title>
  <defs>
    {t_defs}
    {high_gloss_and_penrose_defs()}
  </defs>
  {t_bg}
  <g id="emblem" transform="translate(128 126) scale(0.79) translate({fmt(-128 + cx_off)} {fmt(-127 + cy_off)})">
    <g id="through-glass-mirror-shadow">
      {y_mirror_sh}
    </g>
    <g id="y-3d-walls">
      {''.join(f'<path fill="{wall_fill[k]}" d="{path_d(q)}"/>' for k, q in walls)}
    </g>
    <g id="y-glossy-front">
      <path fill="#181C22" d="{path_d(y_poly)}"/>
      <path fill="url(#bc-bright)" d="{path_d(y_l_outer)}"/>
      <path fill="url(#bc-deep)" d="{path_d(y_l_inner)}"/>
      <path fill="url(#bc-bright)" d="{path_d(y_r_inner)}"/>
      <path fill="url(#bc-deep)" d="{path_d(y_r_outer)}"/>
      {stair_l_svg}
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
      {''.join(f'<path fill="#06080B" fill-opacity="0.75" d="{path_d(c)}"/>' for c in sh_a_on_y)}
    </g>
    {a_svg}
    {left_bridge_svg}
    <g id="shadow-y-right-over-a">
      {''.join(f'<path fill="#3D2202" fill-opacity="0.74" d="{path_d(c)}"/>' for c in sh_y_on_a)}
    </g>
    <g id="y-right-3d-bridge">
      {f'<path fill="url(#bc-wall-right)" d="{path_d(br_r_wall)}"/>' if len(br_r_wall) >= 3 else ''}
      {f'<path fill="url(#bc-bright)" d="{path_d(br_r_inner)}"/>' if len(br_r_inner) >= 3 else ''}
      {f'<path fill="url(#bc-deep)" d="{path_d(br_r_outer)}"/>' if len(br_r_outer) >= 3 else ''}
      {f'<path fill="#C7D2DE" fill-opacity="0.42" d="{path_d(br_r_stair)}"/>' if len(br_r_stair) >= 3 else ''}
      {f'<path fill="#DCE4EC" fill-opacity="0.68" d="{path_d(br_r_glint)}"/>' if len(br_r_glint) >= 3 else ''}
      {f'<path fill="#CFD8E3" fill-opacity="0.58" d="{path_d(br_r_outer_glint)}"/>' if len(br_r_outer_glint) >= 3 else ''}
    </g>
  </g>
</svg>'''
    out = os.path.join(OUT_DIR, filename)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(svg + "\n")
    return out


def main() -> None:
    glass_mineral = {
        "silver_bg": ["#EDF1F5", "#D0D7DF", "#ADB8C4", "#DFE6ED", "#B9C4CF"],
        "rim_outer": ["#F2F6F9", "#BAC5D0", "#768594"],
        "rim_inner": ["#B8CCD6", "#DCE7EE", "#8EA1B2"],
        "double_bevel": False,
    }
    glass_sapphire_mirror = {
        "silver_bg": ["#EFF3F7", "#D6DEE7", "#A3B1C0", "#E7EDF3", "#B5C2CF"],
        "rim_outer": ["#F2F7FA", "#B8C7D4", "#6E8091"],
        "rim_inner": ["#9BBBD0", "#CBE0EC", "#7594A8"],
        "double_bevel": False,
    }
    glass_crystal_thick = {
        "silver_bg": ["#EBEEF2", "#CBD3DC", "#9BA7B4", "#DCE3EB", "#ACB7C3"],
        "rim_outer": ["#F2F5F8", "#B5C0CC", "#687685"],
        "rim_inner": ["#AEC2CE", "#DDE7EE", "#7C8E9E"],
        "double_bevel": True,
    }

    print("Wrote", build_variant(
        "s1-penrose-weave-glass.svg",
        "AnY · 彭罗斯四交织 × 镀银玻璃",
        glass_mineral,
        b_top=104.0, b_bot=122.0, bar_ext=11.0,
        dx_y=9.0, dy_y=7.0,
        four_crossing=True, stepped_y=False, extrude_a=False,
    ))
    print("Wrote", build_variant(
        "s2-penrose-tribar-mirror.svg",
        "AnY · 彭罗斯三折环 × 蓝调镜面玻",
        glass_sapphire_mirror,
        b_top=104.0, b_bot=122.0, bar_ext=2.5,
        dx_y=8.0, dy_y=6.5,
        four_crossing=False, stepped_y=False, extrude_a=False,
    ))
    print("Wrote", build_variant(
        "s3-penrose-escher-crystal.svg",
        "AnY · 埃舍尔立体锁 × 厚晶镀银牌",
        glass_crystal_thick,
        b_top=103.0, b_bot=122.0, bar_ext=13.0,
        dx_y=10.0, dy_y=8.0,
        four_crossing=True, stepped_y=True, extrude_a=True,
    ))


if __name__ == "__main__":
    main()
