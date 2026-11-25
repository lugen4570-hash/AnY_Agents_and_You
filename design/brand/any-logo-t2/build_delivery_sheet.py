#!/usr/bin/env python3
"""Build the final T2 delivery & verification sheet."""
from __future__ import annotations

import os
import sys

KIT_DIR = os.path.dirname(os.path.abspath(__file__))
R6_DIR = os.path.abspath(os.path.join(KIT_DIR, "..", "ay-experiments", "round6-penrose-glass"))
sys.path.insert(0, R6_DIR)

from build_round6_boards import BASE_CSS, load_inline_svg, load_wordmark  # noqa: E402

CSS = """
.page{width:1600px;padding:34px 48px 36px}
.row1{display:grid;grid-template-columns:1.1fr 1.1fr 0.9fr 0.9fr 0.9fr;gap:16px;margin-bottom:18px}
.tile{background:#FFFFFF;border:1.5px solid #DCE6E0;border-radius:16px;padding:16px;display:flex;flex-direction:column;gap:10px}
.tile h3{font-size:13.5px;font-weight:750;color:#18302B}
.tile small{font-size:11.5px;color:#526B65}
.box{height:190px;border-radius:12px;display:flex;align-items:center;justify-content:center;border:1px solid #DCE6E0}
.box.lt{background:#F2F7F4}
.box.dk{background:#142328;border-color:#233940}
.box.chk{background:repeating-conic-gradient(#E8EFEA 0% 25%,#F7FAF8 0% 50%) 50% / 16px 16px}
.box svg{width:154px;height:154px;display:block}
.row2{display:grid;grid-template-columns:1.2fr 1.0fr;gap:18px}
.panel{background:#FFFFFF;border:1.5px solid #DCE6E0;border-radius:16px;padding:18px 22px;display:flex;flex-direction:column;gap:12px}
.panel h3{font-size:14px;font-weight:750;color:#18302B}
.sizes{display:flex;align-items:flex-end;gap:24px;padding:10px 14px;background:#F2F7F4;border-radius:12px}
.sz{display:flex;flex-direction:column;align-items:center;gap:6px;font-size:11.5px;font-weight:650;color:#526B65}
.s192 svg{width:128px;height:128px;display:block}
.s64 svg{width:64px;height:64px;display:block}
.s32 svg{width:32px;height:32px;display:block}
.s16 svg{width:16px;height:16px;display:block}
.lockups{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.lk{border-radius:12px;padding:14px 16px;display:flex;align-items:center;justify-content:space-between;border:1px solid #DCE6E0}
.lk.lt{background:#F2F7F4;color:#18302B}
.lk.dk{background:#142328;border-color:#233940;color:#F3F2E7}
.lk-brand{display:flex;align-items:center;gap:10px}
.lk-brand svg.ico{width:28px;height:28px;display:block}
.lk-brand svg.wm-svg{height:20px;width:auto;display:block}
.lk span{font-size:11.5px;opacity:0.75;font-weight:600}
.files{font-size:12px;color:#3E5851;line-height:1.6}
"""


def main() -> None:
    master = os.path.join(KIT_DIR, "any-logo-master.svg")
    trans = os.path.join(KIT_DIR, "any-logo-transparent.svg")
    mono_b = os.path.join(KIT_DIR, "any-logo-mono-black.svg")
    mono_w = os.path.join(KIT_DIR, "any-logo-mono-white.svg")

    html = (
        """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<title>AnY T2 Final Delivery Sheet</title>
<style>
"""
        + BASE_CSS
        + CSS
        + """
</style>
</head>
<body>
<main class="page">
  <header class="hdr">
    <div>
      <h1>AnY 客户端 Logo 正式定稿交付单（T2 蓝晶镀银玻璃版）</h1>
      <p>全套生产矢量（主徽标 / 去底透明版 / 单色黑白版）、16–1024px 透明 PNG、Windows .ico 与 macOS .icns 已导出并同步客户端</p>
    </div>
    <div class="hdr-meta">
      <span class="pill">定稿：Round 7 T2</span>
      <span class="pill">static/ &amp; src-tauri/icons/ 已同步</span>
    </div>
  </header>
  <section class="row1">
    <div class="tile"><h3>Master · 浅色工作台</h3><div class="box lt">"""
        + load_inline_svg(master, "m-lt")
        + """</div><small>any-logo-master.svg on #F2F7F4</small></div>
    <div class="tile"><h3>Master · 深色工作台</h3><div class="box dk">"""
        + load_inline_svg(master, "m-dk")
        + """</div><small>any-logo-master.svg on #142328</small></div>
    <div class="tile"><h3>Transparent · 无底板徽标</h3><div class="box chk">"""
        + load_inline_svg(trans, "tr")
        + """</div><small>any-logo-transparent.svg</small></div>
    <div class="tile"><h3>Mono Black · 单色深墨</h3><div class="box lt">"""
        + load_inline_svg(mono_b, "mb")
        + """</div><small>any-logo-mono-black.svg (100/100)</small></div>
    <div class="tile"><h3>Mono White · 单色反白</h3><div class="box dk">"""
        + load_inline_svg(mono_w, "mw")
        + """</div><small>any-logo-mono-white.svg (100/100)</small></div>
  </section>
  <section class="row2">
    <div class="panel">
      <h3>多尺寸缩略验证（192px PWA / 64px / 32px / 16px Favicon）</h3>
      <div class="sizes">
        <div class="sz s192">"""
        + load_inline_svg(master, "s192")
        + """<span>192px (icon-192.png)</span></div>
        <div class="sz s64">"""
        + load_inline_svg(master, "s64")
        + """<span>64px</span></div>
        <div class="sz s32">"""
        + load_inline_svg(master, "s32")
        + """<span>32px</span></div>
        <div class="sz s16">"""
        + load_inline_svg(master, "s16")
        + """<span>16px</span></div>
      </div>
    </div>
    <div class="panel">
      <h3>客户端侧栏 Lockup（28px）与已同步文件清单</h3>
      <div class="lockups">
        <div class="lk lt"><div class="lk-brand">"""
        + load_inline_svg(master, "lk-lt", "ico")
        + load_wordmark("#18302B", "wm-lt")
        + """</div><span>Light Sidebar 28px</span></div>
        <div class="lk dk"><div class="lk-brand">"""
        + load_inline_svg(master, "lk-dk", "ico")
        + load_wordmark("#F3F2E7", "wm-dk")
        + """</div><span>Dark Sidebar 28px</span></div>
      </div>
      <div class="files">
        <b>已更新生产文件：</b>static/logo-collaboration.svg · static/logo-app.svg · static/icon-192.png · desktop_tauri/src-tauri/icons/icon.ico (16–256) · desktop_tauri/src-tauri/icons/icon.icns (1024)
      </div>
    </div>
  </section>
</main>
</body>
</html>"""
    )
    out = os.path.join(KIT_DIR, "delivery-sheet.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html)
    print("Wrote", out)


if __name__ == "__main__":
    main()
