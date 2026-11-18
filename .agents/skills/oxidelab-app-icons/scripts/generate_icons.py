#!/usr/bin/env python3
"""Generate OxideLab macOS/Windows/Linux app icons and 12 variants from an SVG."""

from __future__ import annotations

import argparse
import re
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
RENDER_SWIFT = SKILL_DIR / "render_svg.swift"
REPO_ROOT = SKILL_DIR.parents[3]
ICON_DIR = REPO_ROOT / "crates/oxideterm-gpui-app/resources/icons"
VARIANTS_DIR = ICON_DIR / "variants"

SQUIRCLE_SIZE = 848.0

COLORS = {
    "orange": "#EA580C",
    "blue": "#2B82F6",
    "graphite": "#121316",
    "green": "#16A34A",
    "purple": "#7C3AED",
    "pink": "#F472B6",
}

VARIANTS: dict[str, tuple[str, str, str | None]] = {
    "default": ("#FBFBFD", COLORS["orange"], "#E5E7EB"),
    "white-blue": ("#FBFBFD", COLORS["blue"], "#E5E7EB"),
    "white-graphite": ("#FBFBFD", COLORS["graphite"], "#E5E7EB"),
    "white-green": ("#FBFBFD", COLORS["green"], "#E5E7EB"),
    "white-purple": ("#FBFBFD", COLORS["purple"], "#E5E7EB"),
    "white-pink": ("#FBFBFD", COLORS["pink"], "#E5E7EB"),
    "filled-orange": (COLORS["orange"], "#FFFFFF", None),
    "filled-blue": (COLORS["blue"], "#FFFFFF", None),
    "filled-graphite": (COLORS["graphite"], "#FFFFFF", None),
    "filled-green": (COLORS["green"], "#FFFFFF", None),
    "filled-purple": (COLORS["purple"], "#FFFFFF", None),
    "filled-pink": (COLORS["pink"], "#FFFFFF", None),
}


def compile_renderer(tmp_dir: Path) -> Path:
    binary = tmp_dir / "render_svg"
    subprocess.run(["swiftc", str(RENDER_SWIFT), "-o", str(binary)], check=True)
    return binary


def extract_svg_inner(svg_text: str) -> tuple[str, str]:
    vb_match = re.search(r'viewBox="([^"]+)"', svg_text)
    view_box = vb_match.group(1) if vb_match else "0 0 1024 1024"

    # Strip XML declaration, DOCTYPE, outer <svg ...> and </svg>, and hard-coded fills
    # so the foreground color can be inherited from the wrapping <g fill="...">.
    inner = re.sub(r"<\?xml[^>]*\?>", "", svg_text)
    inner = re.sub(r"<!DOCTYPE[^>]*>", "", inner)
    inner = re.sub(r"^.*?<svg[^>]*>", "", inner, count=1, flags=re.DOTALL)
    inner = re.sub(r"</svg>\s*$", "", inner, count=1, flags=re.DOTALL)
    inner = re.sub(r'\s+fill="[^"]*"', "", inner)
    return view_box, inner.strip()


def measure_bounds(renderer: Path, svg_inner: str, view_box: str, tmp_dir: Path) -> tuple[float, float, float, float]:
    probe_svg = tmp_dir / "_probe.svg"
    probe_svg.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_box}">\n'
        f'  <g fill="#000000">{svg_inner}</g>\n'
        f"</svg>\n",
        encoding="utf-8",
    )
    out = subprocess.check_output([str(renderer), "--bounds", str(probe_svg)], text=True).strip()
    cx, cy, w, h = map(float, out.split())
    return cx, cy, w, h


def build_squircle_svg(
    svg_inner: str,
    view_box: str,
    cx: float,
    cy: float,
    scale: float,
    bg: str,
    fg: str,
    stroke: str | None,
) -> str:
    stroke_attr = f' stroke="{stroke}" stroke-width="4"' if stroke else ""
    # Normalize the source viewBox onto a 1024x1024 probe space, then center & scale.
    vb_parts = [float(x) for x in view_box.replace(",", " ").split()]
    vx, vy, vw, vh = vb_parts if len(vb_parts) == 4 else (0.0, 0.0, 1024.0, 1024.0)
    norm = 1024.0 / max(vw, vh)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024">\n'
        f'  <rect x="88" y="88" width="848" height="848" rx="192" fill="{bg}"{stroke_attr}/>\n'
        f'  <g transform="translate(512 512) scale({scale:.5f}) translate({-cx:.2f} {-cy:.2f}) '
        f'scale({norm:.6f}) translate({-vx:.2f} {-vy:.2f})" fill="{fg}">\n'
        f"    {svg_inner}\n"
        f"  </g>\n"
        f"</svg>\n"
    )


def resize_png(src: Path, dst: Path, size: int) -> None:
    subprocess.run(
        ["sips", "-z", str(size), str(size), str(src), "--out", str(dst)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def write_ico_from_png(src_1024: Path, out_ico: Path, tmp_dir: Path) -> None:
    sizes = [16, 32, 48, 64, 128, 256]
    png_blobs: list[tuple[int, bytes]] = []
    for sz in sizes:
        p = tmp_dir / f"ico_{sz}.png"
        resize_png(src_1024, p, sz)
        png_blobs.append((sz, p.read_bytes()))

    header = struct.pack("<HHH", 0, 1, len(png_blobs))
    offset = 6 + 16 * len(png_blobs)
    entries = []
    for sz, blob in png_blobs:
        dim = 0 if sz >= 256 else sz
        entries.append(struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(blob), offset))
        offset += len(blob)

    out_ico.write_bytes(header + b"".join(entries) + b"".join(b for _, b in png_blobs))


def write_icns_from_png(src_1024: Path, out_icns: Path, tmp_dir: Path) -> None:
    iconset = tmp_dir / "AppIcon.iconset"
    iconset.mkdir(parents=True, exist_ok=True)
    specs = [
        ("icon_16x16.png", 16),
        ("icon_16x16@2x.png", 32),
        ("icon_32x32.png", 32),
        ("icon_32x32@2x.png", 64),
        ("icon_128x128.png", 128),
        ("icon_128x128@2x.png", 256),
        ("icon_256x256.png", 256),
        ("icon_256x256@2x.png", 512),
        ("icon_512x512.png", 512),
        ("icon_512x512@2x.png", 1024),
    ]
    for name, sz in specs:
        resize_png(src_1024, iconset / name, sz)
    subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(out_icns)], check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate OxideLab app icons from an SVG.")
    parser.add_argument("--svg", required=True, type=Path, help="Path to source SVG mark")
    parser.add_argument(
        "--ratio",
        type=float,
        default=0.65,
        help="Target ratio of the mark's max dimension to the 848px squircle (default: 0.65)",
    )
    args = parser.parse_args()

    svg_text = args.svg.read_text(encoding="utf-8")
    view_box, svg_inner = extract_svg_inner(svg_text)

    (ICON_DIR / "oxide-mark.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_box}" fill="#fff">\n'
        f"  {svg_inner}\n"
        f"</svg>\n",
        encoding="utf-8",
    )

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        renderer = compile_renderer(tmp_dir)
        cx, cy, w, h = measure_bounds(renderer, svg_inner, view_box, tmp_dir)
        scale = (SQUIRCLE_SIZE * args.ratio) / max(w, h)

        for name, (bg, fg, stroke) in VARIANTS.items():
            svg_file = tmp_dir / f"{name}.svg"
            svg_file.write_text(
                build_squircle_svg(svg_inner, view_box, cx, cy, scale, bg, fg, stroke),
                encoding="utf-8",
            )
            png_1024 = tmp_dir / f"{name}_1024.png"
            subprocess.run([str(renderer), str(svg_file), str(png_1024), "1024"], check=True)

            out_png = VARIANTS_DIR / f"{name}.png"
            resize_png(png_1024, out_png, 512)

            out_ico = VARIANTS_DIR / f"{name}.ico"
            write_ico_from_png(png_1024, out_ico, tmp_dir)

            if name == "default":
                shutil.copy2(out_png, ICON_DIR / "icon.png")
                shutil.copy2(out_ico, ICON_DIR / "icon.ico")
                write_icns_from_png(png_1024, ICON_DIR / "icon.icns", tmp_dir)
                for sz, fname in [
                    (32, "32x32.png"),
                    (64, "64x64.png"),
                    (128, "128x128.png"),
                    (256, "128x128@2x.png"),
                ]:
                    resize_png(png_1024, ICON_DIR / fname, sz)

    print(f"Generated OxideLab icons from {args.svg} (ratio={args.ratio}, bounds=({cx:.1f},{cy:.1f},{w:.0f}x{h:.0f})).")


if __name__ == "__main__":
    main()
