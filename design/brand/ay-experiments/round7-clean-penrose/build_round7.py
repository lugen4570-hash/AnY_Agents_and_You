#!/usr/bin/env python3
"""Generate Round 7: Pure Expanded Penrose A (No Protruding Bar) + Liquid Black-Chrome Y + Silvered-Glass Plaque.

Variants:
  T1: t1-penrose-silverglass.svg    - Expanded slim-leg pure Penrose A + thicker natural bar + mineral silvered glass
  T2: t2-penrose-sapphireglass.svg  - 3D extruded pure Penrose A + thicker bar + stepped glossy Y + sapphire crystal glass
"""
from __future__ import annotations

import html
import os
import sys
from typing import Dict, List, Tuple

Point = Tuple[float, float]
Poly = List[Point]

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
R5_DIR = os.path.abspath(os.path.join(OUT_DIR, "..", "round5-penrose-gloss"))
R6_DIR = os.path.abspath(os.path.join(OUT_DIR, "..", "round6-penrose-glass"))
sys.path.insert(0, R5_DIR)
sys.path.insert(0, R6_DIR)

from build_round5 import (  # noqa: E402
    CX,
    FOOT_L,
    FOOT_R,
    S3,
    STEM_L,
    STEM_R,
    Y_CROTCH,
    Y_FOOT_BOT,
    Y_FOOT_TOP,
    Y_STEM,
    clip_convex,
    extrude_walls,
    fmt,
    path_d,
    poly_area,
    translate,
    y_in_l,
    y_in_r,
    y_mid_l,
    y_mid_r,
    y_out_l,
    y_out_r,
)
from build_round6 import (  # noqa: E402
    high_gloss_and_penrose_defs,
    silvered_glass_defs_and_bg,
    strip_along,
)

# Y top edge sits high so the expanded A stands comfortably inside Y's cradle
Y_TOP = 38.0

# Expanded, upward-shifted, slim-leg Penrose A constants (strictly pure A, zero protruding bar wings)
A_APEX_Y = 44.0
A_BOT = 166.0
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


def build_pure_penrose_a(
    b_top: float,
    b_bot: float,
    with_walls: bool = False,
    dx_a: float = 0.0,
    dy_a: float = 0.0,
    squash: float = 1.0,
    squash_cy: float = 105.0,
) -> Tuple[str, str, Dict[str, object]]:
    """Build pure expanded Penrose A whose thick horizontal crossbar stays strictly inside A's legs.

    ``squash`` vertically compresses the finished letterform around ``squash_cy``
    (1.0 keeps the original proportions); x positions are untouched, so the legs steepen.
    """
    b_mid = 0.5 * (b_top + b_bot)

    # Complete clean-edge A backing silhouette (evenodd) as polygon pair
    back_outer: Poly = [
        P_TOP,
        (a_ro(A_BOT), A_BOT),
        (a_ri(A_BOT), A_BOT),
        (a_ri(b_bot), b_bot),
        (a_li(b_bot), b_bot),
        (a_li(A_BOT), A_BOT),
        (a_lo(A_BOT), A_BOT),
    ]
    back_hole: Poly = [
        P_LI_RI,
        (a_li(b_top), b_top),
        (a_ri(b_top), b_top),
    ]

    def sq_pt(p: Point) -> Point:
        return (p[0], squash_cy + (p[1] - squash_cy) * squash)

    def sqd(poly: Poly) -> str:
        if squash == 1.0:
            return path_d(poly)
        return path_d([sq_pt(p) for p in poly])

    # Ribbon 1 (Brightest Gold): Outer Left Leg (L_o..L_m) folding cleanly into Top Crossbar (B_TOP..B_MID)
    r1_main: Poly = [
        P_TOP,
        P_LM_RO,
        (a_lm(b_top), b_top),
        (a_ri(b_top), b_top),
        (a_ri(b_mid), b_mid),
        (a_lm(b_mid), b_mid),
        (a_lm(A_BOT), A_BOT),
        (a_lo(A_BOT), A_BOT),
    ]

    # Ribbon 2 (Rich 18K Mid-Gold): Outer Right Leg (R_m..R_o) folding over Apex into Upper Inner Left Leg + Left Foot Inner
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

    # Ribbon 3 (Deep Espresso-Bronze Shadow): Inner Right Leg (R_i..R_m) folding into Bottom Crossbar (B_MID..B_BOT)
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

    # Crisp Penrose miter fold crease seams & under-tuck step edges (strictly interior, zero wing cuts)
    dark_creases = [
        strip_along(P_LM_RO, (a_lm(b_top), b_top), 0.55),
        strip_along((a_lm(b_mid), b_mid), (a_lm(A_BOT), A_BOT), 0.55),
        strip_along(P_LI_RM, (a_rm(A_BOT), A_BOT), 0.6),
        strip_along((a_lm(b_mid), b_mid), (a_ri(b_mid), b_mid), 0.65),
        strip_along((a_lm(b_mid), b_mid), (a_lm(b_bot), b_bot), 0.55),
        strip_along((a_ri(b_top), b_top), (a_ri(b_mid), b_mid), 0.55),
    ]
    glints = [
        [P_TOP, (P_TOP[0] + 1.0, P_TOP[1] + 1.7), (a_lo(A_BOT) + 1.9, A_BOT), (a_lo(A_BOT), A_BOT)],
        [(a_lm(b_top), b_top), (a_ri(b_top), b_top), (a_ri(b_top) + 0.9, b_top + 1.6), (a_lm(b_top) - 0.9, b_top + 1.6)],
    ]

    walls_svg = ""
    if with_walls:
        a_outer_poly: Poly = [
            P_TOP,
            (a_ro(A_BOT), A_BOT),
            (a_ri(A_BOT), A_BOT),
            (a_ri(b_bot), b_bot),
            (a_li(b_bot), b_bot),
            (a_li(A_BOT), A_BOT),
            (a_lo(A_BOT), A_BOT),
        ]
        walls = extrude_walls(a_outer_poly, dx_a, dy_a)
        wall_fills = {"right": "#7C4E09", "bot": "#4B2B03", "inner": "#966313"}
        walls_svg = "".join(f'<path fill="{wall_fills[k]}" d="{sqd(q)}"/>' for k, q in walls)
        hole: Poly = [P_LI_RI, (a_ri(b_top), b_top), (a_li(b_top), b_top)]
        hl_raw: Poly = [
            P_LI_RI,
            (a_li(b_top), b_top),
            (a_li(b_top) + dx_a, b_top + dy_a),
            (P_LI_RI[0] + dx_a, P_LI_RI[1] + dy_a),
        ]
        hl_clip = clip_convex(hl_raw, hole)
        if len(hl_clip) >= 3 and abs(poly_area(hl_clip)) > 8.0:
            walls_svg += f'<path fill="#633A05" d="{sqd(hl_clip)}"/>'

    a_back_d = sqd(back_outer) + " " + sqd(back_hole)

    a_svg = f"""
  <g id="a-penrose-gold">
    {walls_svg}
    <path fill="#B67F18" fill-rule="evenodd" d="{a_back_d}"/>
    <path fill="url(#gold-deep)" d="{sqd(r3_main)}"/>
    <path fill="url(#gold-mid)" d="{sqd(r2_main)}"/>
    <path fill="url(#gold-mid)" d="{sqd(r2_foot_l)}"/>
    <path fill="url(#gold-bright)" d="{sqd(r1_main)}"/>
    {''.join(f'<path fill="#381D02" fill-opacity="0.72" d="{sqd(c)}"/>' for c in dark_creases if len(c) >= 3)}
    {''.join(f'<path fill="#FAF3CC" fill-opacity="0.88" d="{sqd(g)}"/>' for g in glints)}
  </g>"""

    left_leg_c: Poly = [P_TOP, (P_TOP[0] + W_A, P_TOP[1]), (a_li(A_BOT), A_BOT), (a_lo(A_BOT), A_BOT)]
    right_leg_c: Poly = [(P_TOP[0] - W_A, P_TOP[1]), P_TOP, (a_ro(A_BOT), A_BOT), (a_ri(A_BOT), A_BOT)]
    full_bar_c: Poly = [(a_lo(b_top), b_top), (a_ro(b_top), b_top), (a_ro(b_bot), b_bot), (a_lo(b_bot), b_bot)]

    geom = {
        "left_leg": [sq_pt(p) for p in left_leg_c],
        "right_leg": [sq_pt(p) for p in right_leg_c],
        "full_bar": [sq_pt(p) for p in full_bar_c],
    }
    return a_svg, a_back_d, geom


def build_variant(
    filename: str,
    title: str,
    glass_cfg: Dict[str, object],
    b_top: float,
    b_bot: float,
    dx_y: float,
    dy_y: float,
    stepped_y: bool,
    extrude_a: bool,
) -> str:
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

    stair_l_svg, stair_r_svg, stair_r_poly = "", "", []
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
        stair_r_svg = f'<path fill="#C7D2DE" fill-opacity="0.42" d="{path_d(stair_r_poly)}"/>'

    dx_a, dy_a = (4.0, 3.0) if extrude_a else (0.0, 0.0)
    a_svg, a_back_d, geom = build_pure_penrose_a(b_top, b_bot, with_walls=extrude_a, dx_a=dx_a, dy_a=dy_a)

    # Left & Right Y arm zones for cast-shadow clipping (A left leg & bar pass OVER Y left arm)
    y_l_zone: Poly = [(y_out_l(Y_TOP), Y_TOP), (y_in_l(Y_TOP), Y_TOP), (CX, Y_CROTCH), (CX, Y_STEM), (STEM_L, Y_STEM)]
    y_l_inner_wall: Poly = [(y_in_l(Y_TOP), Y_TOP), (CX, Y_CROTCH), (CX + dx_y, Y_CROTCH + dy_y), (y_in_l(Y_TOP) + dx_y, Y_TOP + dy_y)]
    y_r_zone: Poly = [(y_in_r(Y_TOP), Y_TOP), (y_out_r(Y_TOP), Y_TOP), (STEM_R, Y_STEM), (CX, Y_STEM), (CX, Y_CROTCH)]

    sh_a_on_y = []
    for ap in (geom["left_leg"], geom["full_bar"]):
        shifted = translate(ap, 5.5 + dx_a, 6.0 + dy_a)
        for yz in (y_l_zone, y_l_inner_wall, y_r_zone):
            c = clip_convex(shifted, yz)
            if len(c) >= 3 and abs(poly_area(c)) > 18.0:
                sh_a_on_y.append(c)

    # Classic clean over-under interlocking: Y right arm bridges OVER A right leg (y = 84..168)
    bridge_clip_r: Poly = [(CX, 84.0), (242.0, 84.0), (242.0, 168.0), (CX, 168.0)]
    br_r_inner = clip_convex(y_r_inner, bridge_clip_r)
    br_r_outer = clip_convex(y_r_outer, bridge_clip_r)
    br_r_glint = clip_convex(y_r_inner_glint, bridge_clip_r)
    br_r_outer_glint = clip_convex(y_r_outer_glint, bridge_clip_r)
    y_r_outer_wall: Poly = [
        (y_out_r(Y_TOP), Y_TOP),
        (y_out_r(Y_TOP) + dx_y, Y_TOP + dy_y),
        (STEM_R + dx_y, Y_STEM + dy_y),
        (STEM_R, Y_STEM),
    ]
    br_r_wall = clip_convex(y_r_outer_wall, bridge_clip_r)
    br_r_stair = clip_convex(stair_r_poly, bridge_clip_r) if stepped_y else []

    # Shadows cast by Y right bridge onto A right leg
    y_r_arm_with_wall: Poly = [
        (y_in_r(Y_TOP), Y_TOP),
        (y_out_r(Y_TOP), Y_TOP),
        (y_out_r(Y_TOP) + dx_y, Y_TOP + dy_y),
        (STEM_R + dx_y, Y_STEM + dy_y),
        (STEM_R, Y_STEM),
        (CX, Y_CROTCH),
    ]
    y_r_bridge_shadow_src = clip_convex(y_r_arm_with_wall, bridge_clip_r)
    sh_y_on_a = []
    for off in ((-4.5, -4.0), (5.5, 5.5)):
        c1 = clip_convex(translate(y_r_bridge_shadow_src, *off), geom["right_leg"])
        if len(c1) >= 3 and abs(poly_area(c1)) > 16.0:
            sh_y_on_a.append(c1)

    # Through-glass offset shadow projected onto the rear silver mirror plate (+6.0, +8.5)
    y_mirror_sh = (
        f'<path fill="#4F5E6D" fill-opacity="0.22" d="{path_d(translate(y_poly, dx_y + 6.0, dy_y + 8.5))}"/>'
        f'<path fill="#414F5D" fill-opacity="0.14" d="{path_d(translate(y_poly, dx_y + 3.0, dy_y + 4.5))}"/>'
        f'<path fill="#4F5E6D" fill-opacity="0.18" fill-rule="evenodd" d="{a_back_d}" transform="translate({fmt(dx_a + 6.0)} {fmt(dy_a + 8.5)})"/>'
    )

    t_defs, t_bg = silvered_glass_defs_and_bg(glass_cfg)
    cx_off, cy_off = -dx_y * 0.42, -dy_y * 0.42

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256" role="img" aria-labelledby="title">
  <title id="title">{html.escape(title)}</title>
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
      {stair_r_svg}
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
    glass_sapphire = {
        "silver_bg": ["#F0F4F8", "#D4DCE5", "#B0BDCB", "#E2EAF2", "#BAC6D4"],
        "rim_outer": ["#F2F7FA", "#B8C6D4", "#718294"],
        "rim_inner": ["#B7D0DC", "#E0ECF2", "#8AA2B5"],
        "double_bevel": True,
    }

    build_variant(
        "t1-penrose-silverglass.svg",
        "AnY Logo T1 - Pure Expanded Penrose A on Liquid Black-Chrome Y & Mineral Silvered Glass",
        glass_mineral,
        b_top=104.0,
        b_bot=121.0,
        dx_y=9.0,
        dy_y=7.0,
        stepped_y=False,
        extrude_a=False,
    )
    build_variant(
        "t2-penrose-sapphireglass.svg",
        "AnY Logo T2 - Extruded Expanded Penrose A on Stepped Black-Chrome Y & Sapphire Crystal Glass",
        glass_sapphire,
        b_top=103.0,
        b_bot=121.0,
        dx_y=10.0,
        dy_y=8.0,
        stepped_y=True,
        extrude_a=True,
    )
    print("Generated Round 7 SVGs in", OUT_DIR)


if __name__ == "__main__":
    main()
