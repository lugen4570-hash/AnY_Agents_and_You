#!/usr/bin/env python3
"""Build the complete production AnY T2 logo kit (SVG masters, mono variants, README)."""
from __future__ import annotations

import os
import sys
from typing import List, Tuple

Point = Tuple[float, float]
Poly = List[Point]

KIT_DIR = os.path.dirname(os.path.abspath(__file__))
R5_DIR = os.path.abspath(os.path.join(KIT_DIR, "..", "ay-experiments", "round5-penrose-gloss"))
R6_DIR = os.path.abspath(os.path.join(KIT_DIR, "..", "ay-experiments", "round6-penrose-glass"))
R7_DIR = os.path.abspath(os.path.join(KIT_DIR, "..", "ay-experiments", "round7-clean-penrose"))

for d in (R5_DIR, R6_DIR, R7_DIR):
    if d not in sys.path:
        sys.path.insert(0, d)

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
    clip_halfplane,
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
from build_round6 import high_gloss_and_penrose_defs, silvered_glass_defs_and_bg  # noqa: E402
from build_round7 import (  # noqa: E402
    A_APEX_Y,
    A_BOT,
    P_LI_RI,
    P_TOP,
    W_A,
    Y_TOP,
    a_li,
    a_lo,
    a_ri,
    a_ro,
    build_pure_penrose_a,
)

T2_GLASS_CFG = {
    "silver_bg": ["#F0F4F8", "#D4DCE5", "#B0BDCB", "#E2EAF2", "#BAC6D4"],
    "rim_outer": ["#F2F7FA", "#B8C6D4", "#718294"],
    "rim_inner": ["#B7D0DC", "#E0ECF2", "#8AA2B5"],
    "double_bevel": True,
}

B_TOP = 103.0
B_BOT = 121.0
DX_Y = 10.0
DY_Y = 8.0
DX_A = 4.0
DY_A = 3.0


def build_t2_emblem_layers(include_mirror_shadow: bool) -> str:
    """Return the complete T2 Y+A emblem groups (optional through-glass mirror shadow)."""
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
    walls = extrude_walls(y_poly, DX_Y, DY_Y)
    wall_fill = {"right": "url(#bc-wall-right)", "bot": "#090B0F", "inner": "url(#bc-wall-inner)"}

    y_stem_hub = (CX, 177.3)
    y_foot_hub = (CX, 208.0)
    y_arm_hub_l = (0.5 * (y_out_l(Y_CROTCH) + y_in_l(Y_CROTCH)), Y_CROTCH)
    y_arm_hub_r = (0.5 * (y_out_r(Y_CROTCH) + y_in_r(Y_CROTCH)), Y_CROTCH)

    cap_h = 3.8
    y_l_cap: Poly = [
        (y_out_l(Y_TOP), Y_TOP),
        (y_in_l(Y_TOP), Y_TOP),
        (y_in_l(Y_TOP) - 1.6, Y_TOP + cap_h),
        (y_out_l(Y_TOP) + 1.9, Y_TOP + cap_h),
    ]
    y_r_cap: Poly = [
        (y_in_r(Y_TOP), Y_TOP),
        (y_out_r(Y_TOP), Y_TOP),
        (y_out_r(Y_TOP) - 1.9, Y_TOP + cap_h),
        (y_in_r(Y_TOP) + 1.6, Y_TOP + cap_h),
    ]
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

    st_l: Poly = [
        (y_out_l(Y_TOP + cap_h) + 4.5, Y_TOP + cap_h),
        (y_out_l(Y_TOP + cap_h) + 10.0, Y_TOP + cap_h),
        (y_out_l(166.0) + 10.0, 166.0),
        (y_out_l(166.0) + 4.5, 166.0),
    ]
    stair_r_poly: Poly = [
        (y_in_r(Y_TOP + cap_h) + 4.5, Y_TOP + cap_h),
        (y_in_r(Y_TOP + cap_h) + 10.0, Y_TOP + cap_h),
        (y_in_r(154.0) + 10.0, 154.0),
        (y_in_r(154.0) + 4.5, 154.0),
    ]

    a_svg, a_back_d, geom = build_pure_penrose_a(B_TOP, B_BOT, with_walls=True, dx_a=DX_A, dy_a=DY_A)

    y_l_zone: Poly = [(y_out_l(Y_TOP), Y_TOP), (y_in_l(Y_TOP), Y_TOP), (CX, Y_CROTCH), (CX, Y_STEM), (STEM_L, Y_STEM)]
    y_l_inner_wall: Poly = [(y_in_l(Y_TOP), Y_TOP), (CX, Y_CROTCH), (CX + DX_Y, Y_CROTCH + DY_Y), (y_in_l(Y_TOP) + DX_Y, Y_TOP + DY_Y)]
    y_r_zone: Poly = [(y_in_r(Y_TOP), Y_TOP), (y_out_r(Y_TOP), Y_TOP), (STEM_R, Y_STEM), (CX, Y_STEM), (CX, Y_CROTCH)]

    sh_a_on_y = []
    for ap in (geom["left_leg"], geom["full_bar"]):
        shifted = translate(ap, 5.5 + DX_A, 6.0 + DY_A)
        for yz in (y_l_zone, y_l_inner_wall, y_r_zone):
            c = clip_convex(shifted, yz)
            if len(c) >= 3 and abs(poly_area(c)) > 18.0:
                sh_a_on_y.append(c)

    bridge_clip_r: Poly = [(CX, 84.0), (242.0, 84.0), (242.0, 168.0), (CX, 168.0)]
    br_r_inner = clip_convex(y_r_inner, bridge_clip_r)
    br_r_outer = clip_convex(y_r_outer, bridge_clip_r)
    br_r_glint = clip_convex(y_r_inner_glint, bridge_clip_r)
    br_r_outer_glint = clip_convex(y_r_outer_glint, bridge_clip_r)
    y_r_outer_wall: Poly = [
        (y_out_r(Y_TOP), Y_TOP),
        (y_out_r(Y_TOP) + DX_Y, Y_TOP + DY_Y),
        (STEM_R + DX_Y, Y_STEM + DY_Y),
        (STEM_R, Y_STEM),
    ]
    br_r_wall = clip_convex(y_r_outer_wall, bridge_clip_r)
    br_r_stair = clip_convex(stair_r_poly, bridge_clip_r)

    y_r_arm_with_wall: Poly = [
        (y_in_r(Y_TOP), Y_TOP),
        (y_out_r(Y_TOP), Y_TOP),
        (y_out_r(Y_TOP) + DX_Y, Y_TOP + DY_Y),
        (STEM_R + DX_Y, Y_STEM + DY_Y),
        (STEM_R, Y_STEM),
        (CX, Y_CROTCH),
    ]
    y_r_bridge_shadow_src = clip_convex(y_r_arm_with_wall, bridge_clip_r)
    sh_y_on_a = []
    for off in ((-4.5, -4.0), (5.5, 5.5)):
        c1 = clip_convex(translate(y_r_bridge_shadow_src, *off), geom["right_leg"])
        if len(c1) >= 3 and abs(poly_area(c1)) > 16.0:
            sh_y_on_a.append(c1)

    mirror_sh_group = ""
    if include_mirror_shadow:
        y_mirror_sh = (
            f'<path fill="#4F5E6D" fill-opacity="0.22" d="{path_d(translate(y_poly, DX_Y + 6.0, DY_Y + 8.5))}"/>'
            f'<path fill="#414F5D" fill-opacity="0.14" d="{path_d(translate(y_poly, DX_Y + 3.0, DY_Y + 4.5))}"/>'
            f'<path fill="#4F5E6D" fill-opacity="0.18" fill-rule="evenodd" d="{a_back_d}" transform="translate({fmt(DX_A + 6.0)} {fmt(DY_A + 8.5)})"/>'
        )
        mirror_sh_group = f'\n    <g id="through-glass-mirror-shadow">\n      {y_mirror_sh}\n    </g>'

    return f"""{mirror_sh_group}
    <g id="y-3d-walls">
      {''.join(f'<path fill="{wall_fill[k]}" d="{path_d(q)}"/>' for k, q in walls)}
    </g>
    <g id="y-glossy-front">
      <path fill="#181C22" d="{path_d(y_poly)}"/>
      <path fill="url(#bc-bright)" d="{path_d(y_l_outer)}"/>
      <path fill="url(#bc-deep)" d="{path_d(y_l_inner)}"/>
      <path fill="url(#bc-bright)" d="{path_d(y_r_inner)}"/>
      <path fill="url(#bc-deep)" d="{path_d(y_r_outer)}"/>
      <path fill="#C7D2DE" fill-opacity="0.45" d="{path_d(st_l)}"/>
      <path fill="#C7D2DE" fill-opacity="0.42" d="{path_d(stair_r_poly)}"/>
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
    </g>"""


def write_master_svg() -> str:
    t_defs, t_bg = silvered_glass_defs_and_bg(T2_GLASS_CFG)
    cx_off, cy_off = -DX_Y * 0.42, -DY_Y * 0.42
    layers = build_t2_emblem_layers(include_mirror_shadow=True)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256" role="img" aria-labelledby="title">
  <title id="title">AnY</title>
  <defs>
    {t_defs}
    {high_gloss_and_penrose_defs()}
  </defs>
  {t_bg}
  <g id="emblem" transform="translate(128 126) scale(0.79) translate({fmt(-128 + cx_off)} {fmt(-127 + cy_off)})">{layers}
  </g>
</svg>'''
    out = os.path.join(KIT_DIR, "any-logo-master.svg")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(svg + "\n")
    return out


def write_transparent_svg() -> str:
    layers = build_t2_emblem_layers(include_mirror_shadow=False)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256" role="img" aria-labelledby="title">
  <title id="title">AnY</title>
  <defs>
    {high_gloss_and_penrose_defs()}
  </defs>
  <g id="emblem" transform="translate(128 128) scale(0.96) translate(-133 -130)">{layers}
  </g>
</svg>'''
    out = os.path.join(KIT_DIR, "any-logo-transparent.svg")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(svg + "\n")
    return out


def build_mono_paths() -> str:
    """Build true 1-color interlocking Y + A silhouette with clean transparent crossing gaps (zero white knockouts)."""
    gap_h = 5.2  # horizontal gap corresponding to ~4.5px perpendicular clearance along 60-degree edges

    # Upper-left Y arm (kept strictly left of A left outer edge - gap)
    y_arm_l: Poly = [(y_out_l(Y_TOP), Y_TOP), (y_in_l(Y_TOP), Y_TOP), (CX, Y_CROTCH), (STEM_L, Y_STEM)]
    y_arm_l_upper = clip_halfplane(y_arm_l, -1.0, -1.0 / S3, CX + A_APEX_Y / S3 - gap_h)

    # Lower-inner left shoulder of Y (below A crossbar & right of A inner-left edge + gap)
    y_arm_l_lower = clip_halfplane(
        clip_halfplane(y_arm_l, 1.0, 1.0 / S3, -(CX + A_APEX_Y / S3 + W_A + gap_h)),
        0.0,
        1.0,
        -(B_BOT + 3.0),
    )

    # Continuous Y right arm + stem + pedestal foot
    y_right_and_stem: Poly = [
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
        (CX, Y_CROTCH),
    ]

    # Upper A (sharp 60-degree apex, left leg + bar + upper right leg clipped strictly left of Y right inner edge - gap)
    # y_in_r(y) = CX + (Y_CROTCH - y)/S3 -> x <= CX + (Y_CROTCH - y)/S3 - gap_h
    u_a = W_A * 0.5
    p_apex_r_seam = (CX + u_a, A_APEX_Y + u_a * S3)
    p_apex_l_seam = (CX - u_a, A_APEX_Y + u_a * S3)
    hp_yr_l = (-1.0, -1.0 / S3, CX + Y_CROTCH / S3 - gap_h)
    a_left_leg: Poly = [P_TOP, p_apex_r_seam, P_LI_RI, (a_li(A_BOT), A_BOT), (a_lo(A_BOT), A_BOT)]
    a_upper_right: Poly = [
        P_TOP,
        (a_ro(B_BOT + 18.0), B_BOT + 18.0),
        (a_ri(B_BOT + 18.0), B_BOT + 18.0),
        P_LI_RI,
        p_apex_l_seam,
    ]
    a_upper_right_clipped = clip_halfplane(a_upper_right, *hp_yr_l)
    a_crossbar_raw: Poly = [(a_lm_x := a_lo(B_TOP) + W_A * 0.5, B_TOP), (a_ro(B_TOP), B_TOP), (a_ro(B_BOT), B_BOT), (a_lo(B_BOT) + W_A * 0.5, B_BOT)]
    _ = a_lm_x
    a_crossbar_clipped = clip_halfplane(a_crossbar_raw, *hp_yr_l)

    # Lower right gold foot of A emerging cleanly right of Y right outer edge + gap
    # y_out_r(y) = CX + (Y_CROTCH - y)/S3 + 30 -> x >= CX + (Y_CROTCH - y)/S3 + 30 + gap_h
    a_lower_right_raw: Poly = [(a_ri(118.0), 118.0), (a_ro(118.0), 118.0), (a_ro(A_BOT), A_BOT), (a_ri(A_BOT), A_BOT)]
    a_lower_right_foot = clip_halfplane(a_lower_right_raw, 1.0, 1.0 / S3, -(CX + Y_CROTCH / S3 + 30.0 + gap_h))

    parts: List[Poly] = [
        y_arm_l_upper,
        y_arm_l_lower,
        y_right_and_stem,
        a_left_leg,
        a_upper_right_clipped,
        a_crossbar_clipped,
        a_lower_right_foot,
    ]
    return " ".join(path_d(p) for p in parts if len(p) >= 3 and abs(poly_area(p)) > 16.0)


def write_mono_svgs() -> Tuple[str, str]:
    d = build_mono_paths()
    outputs = []
    for fname, fill_hex in (("any-logo-mono-black.svg", "#14191F"), ("any-logo-mono-white.svg", "#F3F2E7")):
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256" role="img" aria-labelledby="title">
  <title id="title">AnY</title>
  <g transform="translate(128 128) scale(0.96) translate(-128 -126)">
    <path fill="{fill_hex}" d="{d}"/>
  </g>
</svg>'''
        out = os.path.join(KIT_DIR, fname)
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(svg + "\n")
        outputs.append(out)
    return outputs[0], outputs[1]


def write_readme() -> str:
    content = """# AnY Logo T2 Production Kit

Approved variant: **Round 7 `T2`** (`t2-penrose-sapphireglass.svg`).

## SVG Masters
- `any-logo-master.svg` — Full T2 emblem on sapphire-crystal double-bevel silvered-glass plaque (`static/logo-collaboration.svg`, `static/logo-app.svg`).
- `any-logo-transparent.svg` — Full-color 3D Penrose Gold `A` + Stepped Liquid Black-Chrome `Y` without the glass plaque (`viewBox="0 0 256 256"`).
- `any-logo-mono-black.svg` — True 1-color vector mark (`#14191F`) with geometric over-under crossing gaps for light/print surfaces.
- `any-logo-mono-white.svg` — True 1-color reversed vector mark (`#F3F2E7`) for dark surfaces.

## Raster & Desktop App Icons
- `png/any-logo-{16,24,32,48,64,128,192,256,512,1024}.png` — Crisp headless-rendered transparent RGBA PNGs from `any-logo-master.svg`.
- `icon.ico` — Multi-resolution Windows icon (`16, 24, 32, 48, 64, 128, 256`) synced to `desktop_tauri/src-tauri/icons/icon.ico`.
- `icon.icns` — macOS bundle icon (`1024` master) synced to `desktop_tauri/src-tauri/icons/icon.icns`.

## Core Palette
- Liquid Black-Chrome `Y`: `#E6EEF6` (specular) -> `#647385` -> `#191F27` -> `#0B0E13`
- 18K Penrose Gold `A`: `#FAF1C4` (bright fold) / `#E4A832` (mid fold) / `#482703` (deep bronze fold)
- Sapphire Silvered Glass: `#F0F4F8` -> `#D4DCE5` -> `#B0BDCB`, bevel rim `#F2F7FA` / `#B7D0DC` / `#718294`
"""
    out = os.path.join(KIT_DIR, "README.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(content)
    return out


def main() -> None:
    os.makedirs(os.path.join(KIT_DIR, "png"), exist_ok=True)
    m = write_master_svg()
    t = write_transparent_svg()
    mb, mw = write_mono_svgs()
    rd = write_readme()
    print("Generated T2 kit files:")
    for p in (m, t, mb, mw, rd):
        print(" ", p)


if __name__ == "__main__":
    main()
