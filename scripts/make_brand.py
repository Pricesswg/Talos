#!/usr/bin/env python3
"""Generate the brand assets.

Pure standard library: a PNG is a handful of chunks around a zlib stream, and
pulling in an imaging dependency to draw one rounded square and one letter
would be a poor trade. Rendered at 4x and box-filtered down, which is all the
antialiasing a mark this simple needs.

The mark is a bronze-to-teal rounded square with a slab-serif T: bronze for
Talos, the bronze guardian; teal because that is the panel's accent, and an
icon that shares the interface's colour is recognisable in a sidebar.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

SIZE = 256
SS = 4  # supersampling factor
BRONZE = (154, 107, 52)
TEAL = (22, 105, 127)
INK = (247, 244, 238)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "custom_components" / "talos" / "brand"


def write_png(path: Path, width: int, height: int, pixels: list[list[tuple[int, int, int, int]]]) -> None:
    raw = bytearray()
    for row in pixels:
        raw.append(0)  # filter type 0: none
        for r, g, b, a in row:
            raw += bytes((r, g, b, a))

    def chunk(tag: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + tag
            + payload
            + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
        )

    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)  # 8-bit RGBA
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )


def rounded_square(x: float, y: float, size: float, radius: float) -> bool:
    if x < radius and y < radius:
        return (x - radius) ** 2 + (y - radius) ** 2 <= radius**2
    if x > size - radius and y < radius:
        return (x - (size - radius)) ** 2 + (y - radius) ** 2 <= radius**2
    if x < radius and y > size - radius:
        return (x - radius) ** 2 + (y - (size - radius)) ** 2 <= radius**2
    if x > size - radius and y > size - radius:
        return (x - (size - radius)) ** 2 + (y - (size - radius)) ** 2 <= radius**2
    return True


def mark(canvas: int) -> list[list[tuple[int, int, int, int]]]:
    """Draw the mark at `canvas` pixels square, unfiltered."""
    radius = canvas * 0.22
    # Slab-serif T, in fractions of the canvas.
    bar = (0.235, 0.293, 0.765, 0.391)          # crossbar
    stem = (0.451, 0.293, 0.549, 0.723)         # stem
    foot = (0.371, 0.684, 0.629, 0.723)         # bottom serif
    drops = [(0.235, 0.391, 0.293, 0.430), (0.707, 0.391, 0.765, 0.430)]

    def inside(box: tuple[float, float, float, float], px: float, py: float) -> bool:
        x0, y0, x1, y1 = (v * canvas for v in box)
        return x0 <= px <= x1 and y0 <= py <= y1

    rows = []
    for py in range(canvas):
        row = []
        for px in range(canvas):
            if not rounded_square(px, py, canvas, radius):
                row.append((0, 0, 0, 0))
                continue
            # Diagonal gradient: bronze at the top-left, teal at the bottom-right.
            t = (px + py) / (2 * canvas)
            base = tuple(round(BRONZE[i] + (TEAL[i] - BRONZE[i]) * t) for i in range(3))
            letter = (
                inside(bar, px, py)
                or inside(stem, px, py)
                or inside(foot, px, py)
                or any(inside(drop, px, py) for drop in drops)
            )
            row.append((*(INK if letter else base), 255))
        rows.append(row)
    return rows


def downsample(rows, factor: int):
    size = len(rows) // factor
    out = []
    for y in range(size):
        row = []
        for x in range(size):
            r = g = b = a = 0
            for dy in range(factor):
                for dx in range(factor):
                    pr, pg, pb, pa = rows[y * factor + dy][x * factor + dx]
                    # Premultiply so transparent corners do not darken the edge.
                    r += pr * pa; g += pg * pa; b += pb * pa; a += pa
            if a:
                row.append((round(r / a), round(g / a), round(b / a), round(a / (factor * factor))))
            else:
                row.append((0, 0, 0, 0))
        out.append(row)
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    icon = downsample(mark(SIZE * SS), SS)
    write_png(OUT / "icon.png", SIZE, SIZE, icon)

    # The logo is the same mark on a transparent field, 2:1 as the brands
    # repository expects for a horizontal asset.
    width, height = SIZE * 2, SIZE
    offset = (width - SIZE) // 2
    logo = [
        [icon[y][x - offset] if offset <= x < offset + SIZE else (0, 0, 0, 0) for x in range(width)]
        for y in range(height)
    ]
    write_png(OUT / "logo.png", width, height, logo)

    for name in ("icon.png", "logo.png"):
        print(f"{OUT / name}: {(OUT / name).stat().st_size} byte")


if __name__ == "__main__":
    main()
