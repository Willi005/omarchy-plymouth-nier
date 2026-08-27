#!/usr/bin/env python3
"""Render the Limine boot-menu theme: a wallpaper and a config block.

Limine's menu is a 1-bit character grid, so the only artwork it can show is a
full-screen image behind the text. Variant B puts nothing there but the ground
colour and four corner brackets -- the same L-shapes the Plymouth login draws,
never a traced rectangle.

Every measurement is a fraction of the screen's shorter side rather than a
pixel count, so the proportion survives from 1366x768 to 3840x2160.

Run:  python3 build-limine.py <outdir>
Emits: bg.png, limine-block.conf
"""

import glob
import os
import struct
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent

GROUND = (0x05, 0x05, 0x05)   # NieR near-black
BONE = (0xCF, 0xC9, 0xB0)     # everything the eye should read
BRACKET_ALPHA = 0.30          # matches the login HUD's 0.28, plus a hair

# --- proportions, all against min(W, H) --------------------------------------
INSET = 0.030
ARM = 0.065
THICK = 0.0028

# NOTHING about the text layer is derived from the panel size, deliberately.
# /sys/class/drm reports the PANEL's mode, but the menu runs at whatever GOP
# mode Limine picks when interface_resolution is unset -- which is not
# necessarily the same, and cannot be observed from a booted system. Deriving
# term_font_scale from the panel produced text far too large on the real
# firmware. The text layer therefore uses Limine's own defaults (scale 1x1,
# margin 64), exactly as the stock Omarchy config does. Only the wallpaper is
# rendered per-resolution, and it is stretched, so it adapts either way.


def load_conf():
    conf = {}
    path = HERE / "theme.conf"
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            conf[k.strip()] = v.strip()
    for key in ("RESOLUTION", "BRANDING"):
        env = os.environ.get("LIMINE_" + key) or os.environ.get("PLYMOUTH_" + key)
        if env:
            conf[key] = env
    return conf


CONF = load_conf()


def detect_resolution():
    """Preferred mode of the largest connected display, straight from DRM.

    Same source build-theme.py uses: /sys/class/drm/*/modes needs no session,
    which matters because this runs from a package build.
    """
    best = None
    for path in sorted(glob.glob("/sys/class/drm/*/modes")):
        try:
            first = open(path).readline().strip()
        except OSError:
            continue
        if "x" not in first:
            continue
        try:
            w, h = (int(n) for n in first.split("x", 1))
        except ValueError:
            continue
        if best is None or w * h > best[0] * best[1]:
            best = (w, h)
    return best


def resolution():
    want = CONF.get("RESOLUTION", "auto").lower()
    if want and want != "auto":
        try:
            return tuple(int(n) for n in want.split("x", 1))
        except ValueError:
            sys.exit(f"theme.conf: RESOLUTION must be auto or WxH, got {want!r}")
    found = detect_resolution()
    if found:
        return found
    print("warning: no connected display found in /sys/class/drm; assuming "
          "1920x1080. Set RESOLUTION in theme.conf if that is wrong.",
          file=sys.stderr)
    return 1920, 1080


def blend(fg, bg, alpha):
    return tuple(round(f * alpha + b * (1 - alpha)) for f, b in zip(fg, bg))


def write_png(path, width, height, rows):
    """Minimal RGB8 PNG. Avoids a runtime dependency on ImageMagick for what
    is, after all, a flat field with eight rectangles on it."""
    raw = b"".join(b"\x00" + bytes(row) for row in rows)

    def chunk(tag, data):
        body = tag + data
        return (struct.pack(">I", len(data)) + body
                + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF))

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    Path(path).write_bytes(png)


def wallpaper(width, height, out):
    short = min(width, height)
    inset = round(short * INSET)
    arm = round(short * ARM)
    thick = max(2, round(short * THICK))
    ink = blend(BONE, GROUND, BRACKET_ALPHA)

    rows = [bytearray(bytes(GROUND) * width) for _ in range(height)]

    def rect(x, y, w, h):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(width, x + w), min(height, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        span = bytes(ink) * (x1 - x0)
        for yy in range(y0, y1):
            rows[yy][x0 * 3:x1 * 3] = span

    x0, y0 = inset, inset
    x1, y1 = width - inset, height - inset
    for cx, cy, sx, sy in ((x0, y0, 1, 1), (x1, y0, -1, 1),
                           (x0, y1, 1, -1), (x1, y1, -1, -1)):
        # horizontal arm, then vertical arm: an L per corner, never joined up
        rect(cx if sx > 0 else cx - arm, cy if sy > 0 else cy - thick, arm, thick)
        rect(cx if sx > 0 else cx - thick, cy if sy > 0 else cy - arm, thick, arm)

    write_png(out, width, height, rows)
    return inset, arm, thick


BLOCK = """\
### >>> omarchy-nier >>>
### Generated by build-limine.py for {width}x{height}. Edit nothing between the
### markers by hand -- the package rewrites this whole block on upgrade.
interface_branding: {branding}
interface_branding_color: CFC9B0
interface_help_color: 55503F
interface_help_color_bright: 8C8770

wallpaper: boot():/omarchy-nier/bg.png
wallpaper_style: stretched

### TT=FF is fully transparent: colour_blend() in gterm.c computes
### alpha = 255 - A(fg), so the wallpaper shows through every cell.
term_background: FF000000
term_foreground: CFC9B0
term_background_bright: 00050505
term_foreground_bright: FAFCFB

### Index 6 (cyan) is deliberately chrome: menu.c prints an entry's comment as
### \\e[36m, and it lands at the bottom of the screen above the countdown.
term_palette: 050505;B0563F;55503F;8C8770;4A4638;55503F;55503F;CFC9B0
term_palette_bright: 4A4638;B0563F;8C8770;CFC9B0;55503F;8C8770;8C8770;FAFCFB

### No term_font_scale and no term_margin on purpose: see build-limine.py.
### The menu's own resolution is not the panel's and cannot be read from a
### booted system, so the text layer keeps Limine's defaults.
term_margin_gradient: 0
### <<< omarchy-nier <<<
"""


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)

    width, height = resolution()
    branding = CONF.get("BRANDING") or "OMARCHY"

    inset, arm, thick = wallpaper(width, height, out / "bg.png")
    (out / "limine-block.conf").write_text(BLOCK.format(
        width=width, height=height, branding=branding))

    size = (out / "bg.png").stat().st_size
    print(f"{width}x{height}  bg.png {size} B  brackets inset={inset} "
          f"arm={arm} thick={thick}  text layer: Limine defaults")


if __name__ == "__main__":
    main()
