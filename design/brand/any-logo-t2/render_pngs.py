#!/usr/bin/env python3
"""Render crisp transparent PNGs + Windows ICO + macOS ICNS from any-logo-master.svg.

Uses headless Edge/Chromium via Playwright for accurate SVG rasterisation, then PIL
for downscaling and container packaging. Re-run after any change to the SVG masters.
"""
from __future__ import annotations

import asyncio
import io
import os
import re

from PIL import Image
from playwright.async_api import async_playwright

KIT_DIR = os.path.dirname(os.path.abspath(__file__))
PNG_DIR = os.path.join(KIT_DIR, "png")
SIZES = (16, 24, 32, 48, 64, 128, 192, 256, 512, 1024)
MASTER = os.path.join(KIT_DIR, "any-logo-master.svg")
RENDER = 1024  # rasterise once at the largest size, Lanczos-downscale the rest


async def render_master_png() -> bytes:
    svg = open(MASTER, encoding="utf-8").read()
    svg = re.sub(r'width="256" height="256"', f'width="{RENDER}" height="{RENDER}"', svg, count=1)
    html = (
        '<html><body style="margin:0;background:transparent">'
        + svg
        + "</body></html>"
    )
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(channel="msedge")
        except Exception:
            browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": RENDER, "height": RENDER})
        await page.set_content(html)
        await page.wait_for_timeout(250)
        data = await page.screenshot(omit_background=True)
        await browser.close()
    return data


def main() -> None:
    os.makedirs(PNG_DIR, exist_ok=True)
    raw = asyncio.run(render_master_png())
    base = Image.open(io.BytesIO(raw)).convert("RGBA")
    if base.size != (RENDER, RENDER):
        base = base.crop((0, 0, RENDER, RENDER))
    for size in SIZES:
        img = base if size == RENDER else base.resize((size, size), Image.LANCZOS)
        out = os.path.join(PNG_DIR, f"any-logo-{size}.png")
        img.save(out)
        print("wrote", out)
    ico_sizes = [(s, s) for s in (16, 24, 32, 48, 64, 128, 256)]
    base.save(os.path.join(KIT_DIR, "icon.ico"), sizes=ico_sizes)
    print("wrote icon.ico")
    base.save(os.path.join(KIT_DIR, "icon.icns"), sizes=[(s, s) for s in (16, 32, 64, 128, 256, 512, 1024)])
    print("wrote icon.icns")


if __name__ == "__main__":
    main()
