"""Export the AnY ∀ identity to SVG, ICO, and web/app icon sizes.

Vector geometry matches website/assets/logo.svg; no fonts or network required.
"""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
WEBSITE_ASSETS = ROOT / "website" / "assets"
TAURI_ICON = ROOT / "desktop_tauri" / "src-tauri" / "icons" / "icon.ico"
TAURI_ICNS = ROOT / "desktop_tauri" / "src-tauri" / "icons" / "icon.icns"

INK = "#141413"
PAPER = "#FAF9F5"
DARK_PAPER = "#EFECE6"
SIZE = 1024

MARK_PATH = "M8 11H15L24 29H40L49 11H56L35 55H29Z M27 35H37L32 46Z"
OUTER_POLY = [(8, 11), (15, 11), (24, 29), (40, 29), (49, 11), (56, 11), (35, 55), (29, 55)]
INNER_POLY = [(27, 35), (37, 35), (32, 46)]


def svg(app_icon: bool = False, mono: bool = False, dark: bool = False) -> str:
    """Build an SVG string for the sharp ∀ mark."""
    if app_icon:
        bg = f'<rect width="64" height="64" rx="14" fill="{INK}"/>'
        body = f'<g transform="translate(8 8) scale(.75)"><path fill-rule="evenodd" d="{MARK_PATH}" fill="{PAPER}"/></g>'
        return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><title>AnY</title>{bg}{body}</svg>\n'
    fill = "currentColor" if mono else (DARK_PAPER if dark else INK)
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        f'<title>AnY</title><path fill-rule="evenodd" d="{MARK_PATH}" fill="{fill}"/>'
        "</svg>\n"
    )


def render_app_icon() -> Image.Image:
    """Render the supersampled 1024x1024 rounded app icon matching logo-app.svg."""
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    radius = SIZE * (14 / 64)
    draw.rounded_rectangle((0, 0, SIZE - 1, SIZE - 1), radius, fill=INK)

    mask = Image.new("L", (SIZE, SIZE), 0)
    mask_draw = ImageDraw.Draw(mask)
    scale = 0.75 * (SIZE / 64)
    offset = 8 * (SIZE / 64)
    outer_pts = [(offset + x * scale, offset + y * scale) for x, y in OUTER_POLY]
    inner_pts = [(offset + x * scale, offset + y * scale) for x, y in INNER_POLY]
    mask_draw.polygon(outer_pts, fill=255)
    mask_draw.polygon(inner_pts, fill=0)

    fg = Image.new("RGBA", (SIZE, SIZE), PAPER)
    im.paste(fg, (0, 0), mask)
    return im


def main() -> None:
    STATIC.mkdir(exist_ok=True)
    WEBSITE_ASSETS.mkdir(parents=True, exist_ok=True)
    TAURI_ICON.parent.mkdir(parents=True, exist_ok=True)

    for name, content in (
        ("logo.svg", svg()),
        ("logo-app.svg", svg(app_icon=True)),
        ("logo-dark.svg", svg(dark=True)),
        ("logo-mono.svg", svg(mono=True)),
    ):
        (STATIC / name).write_text(content, encoding="utf-8")

    im = render_app_icon()
    ico_sizes = [(n, n) for n in (16, 24, 32, 48, 64, 128, 256)]
    ico_source = im.resize((256, 256), Image.Resampling.LANCZOS)
    ico_source.save(ROOT / "roundtable.ico", sizes=ico_sizes)
    TAURI_ICON.write_bytes((ROOT / "roundtable.ico").read_bytes())

    im.save(ROOT / "roundtable.icns", format="ICNS")
    TAURI_ICNS.write_bytes((ROOT / "roundtable.icns").read_bytes())

    im.resize((512, 512), Image.Resampling.LANCZOS).save(ROOT / "roundtable_preview.png")
    icon_192 = im.resize((192, 192), Image.Resampling.LANCZOS)
    icon_192.save(STATIC / "icon-192.png")
    (WEBSITE_ASSETS / "icon-192.png").write_bytes((STATIC / "icon-192.png").read_bytes())
    print("Generated AnY ∀ SVG, Windows ICO, macOS ICNS, and web icon assets.")


if __name__ == "__main__":
    main()
