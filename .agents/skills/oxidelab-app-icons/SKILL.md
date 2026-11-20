---
name: oxidelab-app-icons
description: Generate all OxideLab macOS, Windows, Linux, and 11 runtime variant app icons from a single monochrome SVG mark, preserving transparent squircle corners and verifying compilation. Use when replacing or updating the application icon from an SVG file.
---

# OxideLab App Icon Generator

Generate the full cross-platform icon suite (`icon.icns`, `icon.ico`, multi-size PNGs, `oxide-mark.svg`, and all 11 `variants/*.{png,ico}`) from a single monochrome SVG file.

## Prerequisites & Rules

1. Read `.agents/rules/app_icon_palette.md` to confirm the current 6-color palette and `AppIconVariant` file mappings.
2. macOS uses the native toolchain (`swiftc` with `AppKit/CoreSVG`, `sips`, `iconutil` — never `qlmanage`, which fills white corners). Windows/Linux use `resvg` (`cargo install resvg`) plus `Pillow` (`python -m pip install pillow`); every PNG layer is rasterized directly at its target size, so no lossy downscaling happens.

## Workflow

1. **Generate icons from the source SVG.** The committed set corresponds to:
   ```bash
   python3 .agents/skills/oxidelab-app-icons/scripts/generate_icons.py \
     --svg crates/oxideterm-gpui-app/resources/icons/oxide-mark.svg \
     --plate 848 --ratio 0.80 --ico-plate 1024 --ico-ratio 0.80
   ```
   `--plate` / `--ratio` re-proportion every output at once; `--ico-plate` / `--ico-ratio` override ICO only. The ICO override above is **required**, not decorative: PNG/ICNS use the `848` squircle while Windows ICOs use a full-canvas `1024` plate, and omitting it shrinks every Windows icon by that margin. `--plate 960` (≈94% canvas coverage) restores the legacy fuller plate on every target.
   The script automatically:
   - Measures the visible pixel bounding box of the SVG and centers it inside the `1024×1024` transparent squircle.
   - Updates `crates/oxideterm-gpui-app/resources/icons/oxide-mark.svg`.
   - Renders the 11 selectable skins (`variants/*.png` at 512×512 and multi-size `variants/*.ico`).
   - Exports `icon.icns`, `icon.ico`, `icon.png`, `32x32.png`, `64x64.png`, `128x128.png`, and `128x128@2x.png` from the `default` entry, which is the packaged application icon rather than a skin and therefore has no `variants/` copy. That makes `default` the installer, shortcut and Dock/taskbar appearance, so regenerating with a different `default` foreground changes what users see during install.

2. **Visually verify**:
   - Inspect `crates/oxideterm-gpui-app/resources/icons/icon.png` and `variants/filled-orange.png` (and `filled-pink.png` if modified) to confirm centering, scale, and transparent squircle corners.
   - If the icon palette itself changed, confirm the change landed by diffing: only the `default`-derived files and the variant you intended should differ. A full regeneration on an unchanged palette must reproduce every file byte for byte.

3. **Compile check**:
   - Run `cargo check -p oxideterm-gpui-app` to ensure `include_bytes!` and `include_str!` icon paths compile cleanly.
