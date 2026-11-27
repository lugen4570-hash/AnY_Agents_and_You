# AnY Logo T2 Production Kit

Approved variant: **Round 7 `T2`** (`t2-penrose-sapphireglass.svg`), with the 2026-11 revision:
the gold `A` is vertically squashed (x0.85) and the interlock is flipped - the A's RIGHT leg
now crosses in front of the Y's right arm while the Y's LEFT arm bridges over the A's left leg.
Transparent/master centering uses the letterform front-face axis `(128, 125.3)`, not the
wall-inclusive bounding box. Rebuild with `build_t2_kit.py` then `render_pngs.py`, and sync:
`static/logo-collaboration.svg`, `static/logo-app.svg`, `static/logo.svg`, `static/logo-dark.svg`,
`website/assets/logo.svg` (master); `static/logo-mark.svg`, `website/assets/t2-emblem.svg` (transparent);
`static/icon-192.png`, `website/assets/icon-192.png` (png 192); `desktop_tauri/src-tauri/icons/` (ico/icns).

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
