---
name: oxidelab-app-icons
description: Generate all OxideLab macOS, Windows, Linux, and 12 runtime variant app icons from a single monochrome SVG mark, preserving transparent squircle corners and verifying compilation. Use when replacing or updating the application icon from an SVG file.
---

# OxideLab App Icon Generator

Generate the full cross-platform icon suite (`icon.icns`, `icon.ico`, multi-size PNGs, `oxide-mark.svg`, and all 12 `variants/*.{png,ico}`) from a single monochrome SVG file.

## Prerequisites & Rules

1. Read `.agents/rules/app_icon_palette.md` to confirm the current 6-color palette and `AppIconVariant` file mappings.
2. macOS uses the native toolchain (`swiftc` with `AppKit/CoreSVG`, `sips`, `iconutil` — never `qlmanage`, which fills white corners). Windows/Linux use `resvg` (`cargo install resvg`) plus `Pillow` (`python -m pip install pillow`); every PNG layer is rasterized directly at its target size, so no lossy downscaling happens.

## Workflow

1. **Generate icons from the source SVG** (defaults: `848×848` plate with mark ratio `0.65`; `--plate` / `--ratio` re-proportion every output at once):
   ```bash
   python3 .agents/skills/oxidelab-app-icons/scripts/generate_icons.py --svg "<path-to-source.svg>" --plate 960 --ratio 0.65
   ```
   `--plate 960` (≈94% canvas coverage) restores the legacy fuller plate on every target. `--ico-plate` / `--ico-ratio` are optional ICO-only overrides (each defaults to `--plate` / `--ratio`), e.g. `--plate 848 --ico-plate 960` keeps PNG/ICNS on the spec squircle while restoring the legacy Windows ICO size.
   The script automatically:
   - Measures the visible pixel bounding box of the SVG and centers it inside the `1024×1024` transparent squircle (`rx="192"`).
   - Updates `crates/oxideterm-gpui-app/resources/icons/oxide-mark.svg`.
   - Renders all 12 variants (`variants/*.png` at 512×512 and multi-size `variants/*.ico`).
   - Exports `icon.icns`, `icon.ico`, `icon.png`, `32x32.png`, `64x64.png`, `128x128.png`, and `128x128@2x.png`.

2. **Visually verify**:
   - Inspect `crates/oxideterm-gpui-app/resources/icons/variants/default.png` and `filled-orange.png` (and `filled-pink.png` if modified) to confirm centering, scale, and transparent squircle corners.

3. **Compile check**:
   - Run `cargo check -p oxideterm-gpui-app` to ensure `include_bytes!` and `include_str!` icon paths compile cleanly.
