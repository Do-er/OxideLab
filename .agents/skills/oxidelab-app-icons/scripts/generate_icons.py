#!/usr/bin/env python3
"""Generate OxideLab macOS/Windows/Linux app icons and 12 variants from an SVG.

Two toolchains, identical outputs semantics:

- macOS (sanctioned): the bundled Swift renderer (AppKit/CoreSVG), `sips`, and
  `iconutil`. Renders one 1024px master per composition and downsizes with sips.
- Windows/Linux (portable): `resvg` renders each target size straight from the
  vector composition, so no lossy downscaling happens at all. Pillow is used
  only to measure the probe's alpha bounding box, and the ICO/ICNS containers
  are packed in pure Python.

The source SVG is a monochrome mark; the script composes it onto the transparent
1024x1024 canvas with a rounded plate and per-variant colors.
"""

from __future__ import annotations

import argparse
import platform
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

IS_MACOS = platform.system() == "Darwin"

SQUIRCLE_SIZE = 848.0
# Corner radius scales with the plate so a fuller ICO plate keeps the same squircle shape.
PLATE_CORNER_RATIO = 192.0 / 848.0

# The Swift --bounds mode measures inside a 1024x1024 bitmap; the portable path
# must replicate that exact probe geometry to keep scales consistent.
PROBE_SIZE = 1024
# Swift counts pixels with alphaComponent > 0.01, i.e. 8-bit alpha >= 3.
PROBE_ALPHA_THRESHOLD = 2

ICO_SIZES = [16, 32, 48, 64, 128, 256]
ICNS_SIZES = [16, 32, 64, 128, 256, 512, 1024]
# chunk type -> pixel size; duplicates (32/256/512) mirror what iconutil emits
# for 1x and @2x iconset entries, all backed by PNG data.
ICNS_CHUNKS = [
    ("ic04", 16),
    ("ic11", 32),
    ("ic05", 32),
    ("ic12", 64),
    ("ic07", 128),
    ("ic13", 256),
    ("ic08", 256),
    ("ic14", 512),
    ("ic09", 512),
    ("ic10", 1024),
]
LINUX_PNG_SIZES = [
    (32, "32x32.png"),
    (64, "64x64.png"),
    (128, "128x128.png"),
    (256, "128x128@2x.png"),
]

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


def build_squircle_svg(
    svg_inner: str,
    view_box: str,
    cx: float,
    cy: float,
    scale: float,
    bg: str,
    fg: str,
    stroke: str | None,
    plate_size: float = SQUIRCLE_SIZE,
) -> str:
    stroke_attr = f' stroke="{stroke}" stroke-width="4"' if stroke else ""
    # Keep the plate centered; a fuller plate only shrinks the transparent margin.
    plate_x = (1024.0 - plate_size) / 2.0
    plate_rx = plate_size * PLATE_CORNER_RATIO
    # Normalize the source viewBox onto a 1024x1024 probe space, then center & scale.
    vb_parts = [float(x) for x in view_box.replace(",", " ").split()]
    vx, vy, vw, vh = vb_parts if len(vb_parts) == 4 else (0.0, 0.0, 1024.0, 1024.0)
    norm = 1024.0 / max(vw, vh)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024">\n'
        f'  <rect x="{plate_x:.2f}" y="{plate_x:.2f}" width="{plate_size:.2f}" height="{plate_size:.2f}" '
        f'rx="{plate_rx:.2f}" fill="{bg}"{stroke_attr}/>\n'
        f'  <g transform="translate(512 512) scale({scale:.5f}) translate({-cx:.2f} {-cy:.2f}) '
        f'scale({norm:.6f}) translate({-vx:.2f} {-vy:.2f})" fill="{fg}">\n'
        f"    {svg_inner}\n"
        f"  </g>\n"
        f"</svg>\n"
    )


# ---------------------------------------------------------------------------
# macOS native toolchain (AppKit/CoreSVG renderer, sips, iconutil)
# ---------------------------------------------------------------------------


def compile_renderer(tmp_dir: Path) -> Path:
    binary = tmp_dir / "render_svg"
    subprocess.run(["swiftc", str(RENDER_SWIFT), "-o", str(binary)], check=True)
    return binary


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


def resize_png(src: Path, dst: Path, size: int) -> None:
    subprocess.run(
        ["sips", "-z", str(size), str(size), str(src), "--out", str(dst)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def pack_ico(png_blobs: list[tuple[int, bytes]]) -> bytes:
    header = struct.pack("<HHH", 0, 1, len(png_blobs))
    offset = 6 + 16 * len(png_blobs)
    entries = []
    for sz, blob in png_blobs:
        dim = 0 if sz >= 256 else sz
        entries.append(struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(blob), offset))
        offset += len(blob)
    return header + b"".join(entries) + b"".join(b for _, b in png_blobs)


def write_ico_from_png(src_1024: Path, out_ico: Path, tmp_dir: Path) -> None:
    png_blobs: list[tuple[int, bytes]] = []
    for sz in ICO_SIZES:
        p = tmp_dir / f"ico_{sz}.png"
        resize_png(src_1024, p, sz)
        png_blobs.append((sz, p.read_bytes()))
    out_ico.write_bytes(pack_ico(png_blobs))


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


def generate_native(
    args: argparse.Namespace,
    renderer: Path,
    tmp_dir: Path,
    svg_inner: str,
    view_box: str,
    cx: float,
    cy: float,
    scale: float,
    ico_plate: float,
    ico_scale: float,
    separate_ico: bool,
) -> None:
    for name, (bg, fg, stroke) in VARIANTS.items():
        svg_file = tmp_dir / f"{name}.svg"
        svg_file.write_text(
            build_squircle_svg(svg_inner, view_box, cx, cy, scale, bg, fg, stroke, args.plate),
            encoding="utf-8",
        )
        png_1024 = tmp_dir / f"{name}_1024.png"
        subprocess.run([str(renderer), str(svg_file), str(png_1024), "1024"], check=True)

        out_png = VARIANTS_DIR / f"{name}.png"
        resize_png(png_1024, out_png, 512)

        # ICO targets render their own composition when either ICO knob differs,
        # so a fuller plate or a larger mark never changes the shared PNG/ICNS sources.
        ico_png_1024 = png_1024
        if separate_ico:
            ico_svg_file = tmp_dir / f"{name}_ico.svg"
            ico_svg_file.write_text(
                build_squircle_svg(
                    svg_inner, view_box, cx, cy, ico_scale, bg, fg, stroke, ico_plate
                ),
                encoding="utf-8",
            )
            ico_png_1024 = tmp_dir / f"{name}_ico_1024.png"
            subprocess.run(
                [str(renderer), str(ico_svg_file), str(ico_png_1024), "1024"], check=True
            )

        out_ico = VARIANTS_DIR / f"{name}.ico"
        write_ico_from_png(ico_png_1024, out_ico, tmp_dir)

        if name == "default":
            shutil.copy2(out_png, ICON_DIR / "icon.png")
            shutil.copy2(out_ico, ICON_DIR / "icon.ico")
            write_icns_from_png(png_1024, ICON_DIR / "icon.icns", tmp_dir)
            for sz, fname in LINUX_PNG_SIZES:
                resize_png(png_1024, ICON_DIR / fname, sz)


# ---------------------------------------------------------------------------
# Portable toolchain (resvg + Pillow, Windows/Linux)
# ---------------------------------------------------------------------------


def require_resvg() -> str:
    resvg = shutil.which("resvg")
    if not resvg:
        raise SystemExit(
            "resvg is required for icon generation on this platform. "
            "Install it with `cargo install resvg` or a distribution package."
        )
    return resvg


def require_pillow() -> None:
    try:
        import PIL  # noqa: F401
    except ImportError as error:
        raise SystemExit(
            "Pillow is required for icon generation on this platform: "
            "python -m pip install pillow"
        ) from error


def render_resvg(resvg: str, svg_file: Path, out_png: Path, size: int) -> Path:
    # Compositions always use a square 1024 viewBox, so width/height fit exactly.
    subprocess.run(
        [resvg, "--width", str(size), "--height", str(size), str(svg_file), str(out_png)],
        check=True,
    )
    return out_png


def measure_bounds_portable(
    resvg: str, svg_inner: str, view_box: str, tmp_dir: Path
) -> tuple[float, float, float, float]:
    """Measure like the Swift --bounds mode: stretch the whole viewBox onto a
    1024x1024 bitmap and report the visible bbox in stretched pixels."""
    from PIL import Image

    vb_parts = [float(x) for x in view_box.replace(",", " ").split()]
    vx, vy, vw, vh = vb_parts if len(vb_parts) == 4 else (0.0, 0.0, 1024.0, 1024.0)
    probe_svg = tmp_dir / "_probe.svg"
    probe_svg.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {PROBE_SIZE} {PROBE_SIZE}">\n'
        f'  <g fill="#000000" transform="scale({PROBE_SIZE / vw:.6f} {PROBE_SIZE / vh:.6f}) '
        f'translate({-vx:.2f} {-vy:.2f})">\n{svg_inner}\n  </g>\n</svg>\n',
        encoding="utf-8",
    )
    probe_png = tmp_dir / "_probe.png"
    render_resvg(resvg, probe_svg, probe_png, PROBE_SIZE)

    alpha = Image.open(probe_png).convert("RGBA").getchannel("A")
    bbox = alpha.point(lambda v: 255 if v > PROBE_ALPHA_THRESHOLD else 0).getbbox()
    if bbox is None:
        raise SystemExit("SVG contains no visible pixels")
    min_x, min_y, max_x, max_y = bbox[0], bbox[1], bbox[2] - 1, bbox[3] - 1
    cx = (min_x + max_x) / 2.0
    cy = (min_y + max_y) / 2.0
    return cx, cy, float(max_x - min_x + 1), float(max_y - min_y + 1)


def pack_icns(size_pngs: dict[int, bytes]) -> bytes:
    chunks = []
    for type_code, size in ICNS_CHUNKS:
        png = size_pngs[size]
        chunks.append(type_code.encode("ascii") + struct.pack(">I", 8 + len(png)) + png)
    body = b"".join(chunks)
    return b"icns" + struct.pack(">I", 8 + len(body)) + body


def generate_portable(
    args: argparse.Namespace,
    resvg: str,
    tmp_dir: Path,
    svg_inner: str,
    view_box: str,
    cx: float,
    cy: float,
    scale: float,
    ico_plate: float,
    ico_scale: float,
    separate_ico: bool,
) -> None:
    for name, (bg, fg, stroke) in VARIANTS.items():
        # PNG/ICNS/Linux targets always come from the main composition; ICO layers
        # switch to their own composition only when --ico-plate/--ico-ratio differ.
        main_sizes = {512} | {sz for sz, _ in LINUX_PNG_SIZES} | set(ICNS_SIZES)
        ico_sizes = set(ICO_SIZES)
        if not separate_ico:
            main_sizes |= ico_sizes

        main_svg = tmp_dir / f"{name}.svg"
        main_svg.write_text(
            build_squircle_svg(svg_inner, view_box, cx, cy, scale, bg, fg, stroke, args.plate),
            encoding="utf-8",
        )
        main_renders = {
            size: render_resvg(resvg, main_svg, tmp_dir / f"{name}_{size}.png", size)
            for size in sorted(main_sizes)
        }

        if separate_ico:
            ico_svg = tmp_dir / f"{name}_ico.svg"
            ico_svg.write_text(
                build_squircle_svg(
                    svg_inner, view_box, cx, cy, ico_scale, bg, fg, stroke, ico_plate
                ),
                encoding="utf-8",
            )
            ico_renders = {
                size: render_resvg(resvg, ico_svg, tmp_dir / f"{name}_ico_{size}.png", size)
                for size in sorted(ico_sizes)
            }
        else:
            ico_renders = {size: main_renders[size] for size in ico_sizes}

        out_png = VARIANTS_DIR / f"{name}.png"
        shutil.copyfile(main_renders[512], out_png)
        out_ico = VARIANTS_DIR / f"{name}.ico"
        out_ico.write_bytes(pack_ico([(sz, ico_renders[sz].read_bytes()) for sz in ICO_SIZES]))

        if name == "default":
            shutil.copyfile(out_png, ICON_DIR / "icon.png")
            shutil.copyfile(out_ico, ICON_DIR / "icon.ico")
            (ICON_DIR / "icon.icns").write_bytes(
                pack_icns({sz: main_renders[sz].read_bytes() for sz in ICNS_SIZES})
            )
            for sz, fname in LINUX_PNG_SIZES:
                shutil.copyfile(main_renders[sz], ICON_DIR / fname)


# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate OxideLab app icons from an SVG.")
    parser.add_argument("--svg", required=True, type=Path, help="Path to source SVG mark")
    parser.add_argument(
        "--plate",
        type=float,
        default=SQUIRCLE_SIZE,
        help="Plate side length on the 1024 canvas for all outputs (default: 848, the "
        "spec squircle)",
    )
    parser.add_argument(
        "--ratio",
        type=float,
        default=0.65,
        help="Target ratio of the mark's max dimension to its plate (default: 0.65)",
    )
    parser.add_argument(
        "--ico-plate",
        type=float,
        default=None,
        help="Plate side length for ICO outputs only; defaults to --plate",
    )
    parser.add_argument(
        "--ico-ratio",
        type=float,
        default=None,
        help="Mark-to-plate ratio for ICO outputs only; defaults to --ratio",
    )
    args = parser.parse_args()

    ico_plate = args.ico_plate if args.ico_plate is not None else args.plate
    ico_ratio = args.ico_ratio if args.ico_ratio is not None else args.ratio
    for label, size in (("--plate", args.plate), ("--ico-plate", ico_plate)):
        if not 0 < size <= 1024:
            raise SystemExit(f"{label} must be within (0, 1024], got {size}")

    # Fresh checkouts may run this before any packaged resource layout exists.
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    VARIANTS_DIR.mkdir(parents=True, exist_ok=True)

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
        if IS_MACOS:
            renderer = compile_renderer(tmp_dir)
            cx, cy, w, h = measure_bounds(renderer, svg_inner, view_box, tmp_dir)
            toolchain = "native macOS toolchain"
        else:
            resvg = require_resvg()
            require_pillow()
            cx, cy, w, h = measure_bounds_portable(resvg, svg_inner, view_box, tmp_dir)
            toolchain = "resvg+Pillow"

        scale = (args.plate * args.ratio) / max(w, h)
        # ICO outputs get their own plate and mark ratio only when explicitly
        # overridden; otherwise every target shares one composition.
        ico_scale = (ico_plate * ico_ratio) / max(w, h)
        separate_ico = ico_plate != args.plate or ico_ratio != args.ratio

        if IS_MACOS:
            generate_native(
                args,
                renderer,
                tmp_dir,
                svg_inner,
                view_box,
                cx,
                cy,
                scale,
                ico_plate,
                ico_scale,
                separate_ico,
            )
        else:
            generate_portable(
                args,
                resvg,
                tmp_dir,
                svg_inner,
                view_box,
                cx,
                cy,
                scale,
                ico_plate,
                ico_scale,
                separate_ico,
            )

    print(
        f"Generated OxideLab icons from {args.svg} via {toolchain} "
        f"(plate={args.plate:g}, ratio={args.ratio:g}, ico_plate={ico_plate:g}, "
        f"ico_ratio={ico_ratio:g}, bounds=({cx:.1f},{cy:.1f},{w:.0f}x{h:.0f}))."
    )


if __name__ == "__main__":
    main()
