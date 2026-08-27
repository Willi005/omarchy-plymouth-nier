#!/usr/bin/env python3
"""Build the omarchy-minimal Plymouth theme: assets plus the theme script.

Everything visible is pre-rendered at its exact final pixel size, because
Plymouth's Image.Scale is nearest-neighbour (verified by disassembling
ply_pixel_buffer_resize) and destroys antialiased artwork. That is also why
this has to run on, or at least know about, the machine it is for: the
artwork is sized in real pixels, so it is regenerated per screen rather than
scaled at boot.

The generated sizes assume the boot window is the panel's native resolution,
which requires DeviceScale=1 in /etc/plymouth/plymouthd.conf. Without that,
Plymouth's HiDPI heuristic (DPI = width*254/(10*(width_mm+1)) > 96) picks
device scale 2, halves the logical window and upscales every image 2x.

Settings come from nierconf, which reads /etc/omarchy-plymouth-nier.conf when
it exists and theme.conf next to this file otherwise, with NIER_<KEY> in the
environment beating both.

Usage: build-theme.py <output-dir>
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nierconf

HERE = Path(__file__).resolve().parent
CONF = nierconf.load()

# The composition was designed on a 1800px-tall screen; every pointsize below
# is in pixels for that height and gets multiplied by RES for the real one.
DESIGN_HEIGHT = 1800


def font_file(family, needle, package):
    """Resolve a family to a real font file, since paths differ per distro.

    fc-match always answers with *something*, so the family it actually
    matched has to be checked or the theme would silently render in a
    substitute face.
    """
    try:
        out = subprocess.run(["fc-match", "-f", "%{file}\t%{family}", family],
                             check=True, capture_output=True, text=True).stdout
    except (OSError, subprocess.CalledProcessError):
        sys.exit("fc-match not available — install fontconfig")
    path, _, families = out.partition("\t")
    if not path or needle.lower() not in families.lower():
        sys.exit(f"font {family!r} not installed — install {package}")
    return path


CJK = font_file("Noto Sans CJK JP", "Noto Sans CJK", "noto-fonts-cjk")
JB = font_file("JetBrainsMono Nerd Font", "JetBrainsMono",
               "ttf-jetbrains-mono-nerd")

# The whole palette is shared with the Limine menu, so one change retints
# every screen in the boot chain rather than letting them drift apart.
BONE = CONF["BONE"]       # everything the eye should read
DIM = CONF["DIM"]         # ghost word only
CHROME = CONF["CHROME"]   # bottom hint, secondary labels
RUST = CONF["RUST"]       # the only chromatic note, and only on a rejected key

KATA = CONF["ALPHABET"]
COLUMN_CHARS = CONF.column      # derived from GHOST_WORD unless set explicitly
RATIO = 1.2308                  # glyph box / pointsize

W, H = CONF.resolution
RES = H / DESIGN_HEIGHT

NAME = CONF["NAME"]
GHOST_WORD = CONF["GHOST_WORD"]

# Global size factor. It applies to the artwork AND to the layout ratios in
# the script below, so the whole composition scales as one piece.
SCALE = CONF.frac("SCALE")

# Everything below is "pixels on a DESIGN_HEIGHT-tall screen" times RES.
_S = SCALE * RES

AMBIENT_BOXES = tuple(round(b * _S) for b in (43, 56, 69))
HIT_BOX = round(41 * _S)      # typed-character glitch glyph
COLUMN_BOX = round(106 * _S)  # vertical column at the right
GHOST_POINTSIZE = round(432 * _S)
GHOST_MAX_WIDTH = CONF.frac("GHOST_MAX_WIDTH")
GHOST_SS = 3           # supersample factor for the ghost word only
GHOST_BLUR = "0x0.7"   # was 0x1.4; the supersample no longer needs it to hide edges
WELCOME_POINTSIZE = round(58 * _S)
HINT_POINTSIZE = round(27 * _S)
HINT_KERNING = round(6 * _S)
DOT_BOX = round(13 * _S)
STATUS_POINTSIZE = round(30 * _S)   # ACCESS DENIED / VERIFYING KEY
STATUS_KERNING = round(10 * _S)
ATT_POINTSIZE = round(25 * _S)      # ATTEMPT NN, one step down
ATT_KERNING = round(8 * _S)
MAX_ATTEMPT_LABEL = 9                  # attempts past this reuse the last label


def magick(*args):
    args = [str(a) for a in args]
    # -strip drops the creation timestamp ImageMagick bakes into every PNG, so
    # rebuilding the theme yields byte-identical assets instead of 206 files
    # that all "changed".
    subprocess.run(["magick", *args[:-1], "-strip", args[-1]], check=True)


def glyph(ch, box, out, color=BONE):
    magick("-background", "none", "-fill", color, "-font", CJK,
           "-pointsize", round(box / RATIO), "label:" + ch,
           "-gravity", "center", "-extent", f"{box}x{box}", out)


def build_assets(d: Path):
    for b, box in enumerate(AMBIENT_BOXES):
        for i, ch in enumerate(KATA):
            glyph(ch, box, d / f"a{b}_{i:02d}.png")
    for i, ch in enumerate(KATA):
        glyph(ch, HIT_BOX, d / f"hit_{i:02d}.png")
    for n, ch in enumerate(COLUMN_CHARS):
        glyph(ch, COLUMN_BOX, d / f"col_{n}.png")

    # Ghost word: ~60% of the screen width, blur baked in (no filters at
    # boot). Rendered at GHOST_SS x the final pointsize and brought down with
    # Lanczos, which resolves the thin strokes of システム far better than
    # rasterising straight to the target size; the softening blur is then only
    # what the design calls for rather than a way to hide aliasing. The
    # downsample is forced to the exact 1x dimensions so the size is unchanged.
    probe = d / "ghost_probe.png"
    points = GHOST_POINTSIZE
    magick("-background", "none", "-fill", DIM, "-font", CJK,
           "-pointsize", points, "label:" + GHOST_WORD, probe)
    gw, gh = (int(n) for n in subprocess.run(
        ["identify", "-format", "%w %h", str(probe)],
        check=True, capture_output=True, text=True).stdout.split())

    # The pointsize is derived from screen height, so on a wider aspect ratio
    # or a longer word the ghost could run past the edges. Pull it back in.
    limit = W * GHOST_MAX_WIDTH
    if gw > limit:
        points = max(1, round(points * limit / gw))
        magick("-background", "none", "-fill", DIM, "-font", CJK,
               "-pointsize", points, "label:" + GHOST_WORD, probe)
        gw, gh = (int(n) for n in subprocess.run(
            ["identify", "-format", "%w %h", str(probe)],
            check=True, capture_output=True, text=True).stdout.split())
    probe.unlink()

    magick("-background", "none", "-fill", DIM, "-font", CJK,
           "-pointsize", points * GHOST_SS, "label:" + GHOST_WORD,
           "-filter", "Lanczos", "-resize", f"{gw}x{gh}!",
           "-blur", GHOST_BLUR, d / "ghost.png")

    magick("-background", "none", "-fill", BONE, "-font", JB,
           "-pointsize", WELCOME_POINTSIZE, f"label:{CONF['WELCOME'].format(name=NAME)}",
           d / "welcome.png")

    magick("-background", "none", "-fill", CHROME, "-font", JB,
           "-kerning", HINT_KERNING, "-pointsize", HINT_POINTSIZE,
           f"label:{CONF['HINT']}", d / "hint.png")

    # Shutdown screen: farewell line plus a small status label.
    magick("-background", "none", "-fill", BONE, "-font", JB,
           "-pointsize", WELCOME_POINTSIZE, f"label:{CONF['GOODBYE'].format(name=NAME)}",
           d / "goodbye.png")

    magick("-background", "none", "-fill", CHROME, "-font", JB,
           "-kerning", HINT_KERNING, "-pointsize", HINT_POINTSIZE,
           "label:SYSTEM OFFLINE", d / "offline.png")

    # Rejected-key labels. ACCESS DENIED is rendered twice, identical except
    # for colour: Plymouth cannot tint a sprite, so the rust-to-bone decay is
    # a crossfade between two stacked sprites of the same pixel size.
    for name, colour in (("denied_rust", RUST), ("denied_bone", BONE)):
        magick("-background", "none", "-fill", colour, "-font", JB,
               "-kerning", STATUS_KERNING, "-pointsize", STATUS_POINTSIZE,
               "label:ACCESS DENIED", d / f"{name}.png")

    magick("-background", "none", "-fill", CHROME, "-font", JB,
           "-kerning", STATUS_KERNING, "-pointsize", STATUS_POINTSIZE,
           "label:VERIFYING KEY", d / "verifying.png")

    for n in range(1, MAX_ATTEMPT_LABEL + 1):
        magick("-background", "none", "-fill", CHROME, "-font", JB,
               "-kerning", ATT_KERNING, "-pointsize", ATT_POINTSIZE,
               f"label:ATTEMPT {n:02d}", d / f"att_{n:02d}.png")

    # Flat tiles: nearest-neighbour scaling is lossless on solid colour, so
    # these are the only images the script is allowed to resize.
    magick("-size", f"{DOT_BOX}x{DOT_BOX}", "xc:" + BONE, d / "dot.png")
    magick("-size", "8x8", "xc:" + BONE, d / "line.png")
    magick("-size", "8x8", "xc:" + RUST, d / "line_rust.png")


def image_loads():
    lines = []
    for b in range(len(AMBIENT_BOXES)):
        for i in range(len(KATA)):
            lines.append(f'glyph.a{b}[{i}] = Image("a{b}_{i:02d}.png");')
        lines.append("")
    for i in range(len(KATA)):
        lines.append(f'glyph.hit[{i}] = Image("hit_{i:02d}.png");')
    lines.append("")
    for n in range(len(COLUMN_CHARS)):
        lines.append(f'column.image[{n}] = Image("col_{n}.png");')
    lines.append("")
    lines.append("att.image = [];")
    for n in range(1, MAX_ATTEMPT_LABEL + 1):
        lines.append(f'att.image[{n - 1}] = Image("att_{n:02d}.png");')
    return "\n".join(lines)


def build_script(d: Path):
    body = SCRIPT.replace("@IMAGES@", image_loads())
    body = body.replace("@GLYPH_COUNT@", str(len(KATA)))
    body = body.replace("@BOX0@", str(AMBIENT_BOXES[0]))
    body = body.replace("@BOX1@", str(AMBIENT_BOXES[1]))
    body = body.replace("@BOX2@", str(AMBIENT_BOXES[2]))
    for name, base in (("WELCOME_DY", 0.055), ("LINE_DY", 0.045),
                       ("LINE_W", 0.24), ("DOT_SPACING", 0.0206),
                       ("DOT_DY", 0.028), ("BR_W", 0.30), ("BR_H", 0.20),
                       ("BYE_DY", 0.028), ("RULE_DY", 0.012),
                       ("LABEL_DY", 0.040), ("STATUS_DY", 0.062),
                       ("ATT_DY", 0.030)):
        body = body.replace(f"@{name}@", f"{base * SCALE:.5f}")
    body = body.replace("@LINE_H@", str(max(2, round(3 * SCALE))))

    # FIELD=off empties both loops rather than hiding their sprites: the
    # glyphs are never created, so nothing is drawn and nothing is loaded.
    on = CONF.flag("FIELD")
    body = body.replace("@LOOSE@", str(CONF.count("GLYPHS") if on else 0))
    body = body.replace("@STACKS@", str(CONF.count("STACKS") if on else 0))
    body = body.replace("@STACK_MIN@", str(CONF.count("STACK_MIN")))
    # Math.Random() is [0,1), so the span has to be one past the difference
    # for STACK_MAX itself to be reachable.
    # The vertical column belongs to the ambient field, so FIELD=off drops it
    # too -- verified with plyrun, which caught it still rendering.
    body = body.replace("@COLUMN@", str(len(COLUMN_CHARS) if on else 0))
    body = body.replace("@STACK_SPAN@",
                        str(CONF.count("STACK_MAX") - CONF.count("STACK_MIN") + 1))
    # Plymouth cannot read a colour from anywhere but a literal, and this is
    # the one place a colour is not baked into a PNG.
    r, g, b = (int(BONE[i:i + 2], 16) / 255 for i in (1, 3, 5))
    body = body.replace("@BONE_R@", f"{r:.3f}").replace("@BONE_G@", f"{g:.3f}")
    body = body.replace("@BONE_B@", f"{b:.3f}")
    body = body.replace("@MAX_ATT@", str(MAX_ATTEMPT_LABEL))
    (d / "omarchy.script").write_text(body)
    # A prebuilt package carries one resolution's artwork, and on another panel
    # it looks wrong. Recording it lets the installer notice and regenerate.
    (d / "built-for").write_text(f"{W}x{H}\n")


SCRIPT = r'''# Omarchy Minimal — NieR-inspired LUKS unlock screen.
#
# Every visible asset is pre-rendered at its exact final pixel size and
# NOTHING antialiased is resized at runtime: Plymouth's Image.Scale is
# nearest-neighbour, so scaling artwork visibly destroys it. The only images
# still scaled are flat-colour tiles, where that sampling is lossless.
#
# This assumes DeviceScale=1 in /etc/plymouth/plymouthd.conf. Otherwise
# Plymouth's HiDPI heuristic halves the logical window and upscales every
# image 2x, which makes the whole composition twice its intended size.
#
# Composition, back to front:
#   1. ghost word (システム), very dim, breathing
#   2. ambient katakana: loose glyphs plus short vertical stacks, each
#      character breathing and swapping on its own timer
#   3. vertical katakana column (システム) at the right
#   4. HUD brackets, welcome line, password underline, bottom hint
#   5. typed characters: a katakana that cycles briefly, then resolves
#   6. after unlock everything fades out and only the progress line remains

Window.SetBackgroundTopColor(0.020, 0.020, 0.020);
Window.SetBackgroundBottomColor(0.020, 0.020, 0.020);

global.W = Window.GetWidth();
global.H = Window.GetHeight();
global.cx = global.W / 2;
global.cy = global.H * 0.47;

# Shutdown and reboot get a plain farewell screen instead of the katakana
# field. Plymouth.GetMode() reports "shutdown"/"reboot" there.
global.mode = Plymouth.GetMode();
global.shutdown = 0;
if (global.mode == "shutdown") global.shutdown = 1;
if (global.mode == "reboot") global.shutdown = 1;

global.glyph_count = @GLYPH_COUNT@;
global.loose_count = @LOOSE@;
global.stack_count = @STACKS@;
global.max_bullets = 21;

global.fps = 50.0;
global.frame = 0;

global.password_shown = 0;
global.unlock_frame = 0;
global.max_progress = 0.0;

global.ui_alpha = 0.0;
global.field_dim = 1.0;
global.shown = 0;

# Plymouth never says "wrong password". plymouthd has a single update_display()
# that picks display_password / display_normal from its pending-request queue,
# and `plymouth ask-for-password --command=...` (what the encrypt hook runs)
# simply re-issues the request when cryptsetup exits non-zero. So the sequence
# is: password -> Enter -> normal -> (silence) -> password again, if rejected.
# The screen therefore has to sit in a verifying state and only then resolve.
#
#   state 0 = prompt, 1 = verifying, 3 = unlocked
global.state = 0;
global.typed_any = 0;      # bullets went above zero during this attempt
global.attempts = 0;
global.verify_frame = 0;

# Measured on this machine: the LUKS header is argon2id with 9 iterations over
# 1 GiB, and a rejected passphrase takes 15.8 s to come back. Committing to
# "unlocked" any earlier than that would start the unlock fade on every wrong
# password. A late rejection is still handled — it just snaps back.
# How the theme learns the key was accepted.
#
# `plymouth ask-for-password` PAUSES boot progress for as long as it is
# asking — that is what its --dont-pause-progress flag turns off, and the
# encrypt hook does not pass it. While paused, ply_progress freezes both the
# percentage and the elapsed time, but plymouthd keeps calling this theme's
# boot-progress function every 33 ms with those frozen values.
#
# So: progress standing still IS the key being checked, and progress starting
# to move again IS the key having been accepted. That is an exact signal, not
# a guess, and it replaces the frame counter (starved by argon2) and the
# 17 s wall-clock timer (frozen by this very pause) that came before it.
global.verify_t = -1;         # the frozen clock value when verifying began
global.frozen = 0;            # consecutive ticks with the clock standing still
global.frozen_needed = 15;    # ~0.5 s of proven freeze before trusting it
global.resume_secs = 0.35;    # movement past this means a real resume
global.verify_secs = 17.0;    # fallback if progress was never paused at all
global.verify_commit = 880;   # frame-counted backstop, last resort

global.denying = 0;
global.deny_frame = 0;
global.deny_frames = 80.0;    # 1.6 s
global.decay = 0.0;
global.tearing = 0;
global.tear_frames = 22.0;
global.tear_k = 0.0;
global.shard_frames = 26.0;
global.shard_count = 0;
global.jx = 0;
global.seg_count = 7;
global.max_att = @MAX_ATT@;

fun mod(a, b) {
  return a - Math.Int(a / b) * b;
}

#----------------------------------------- Images ------------------------------

@IMAGES@

#----------------------------------------- Ambient glyphs ----------------------

# One flat list holds both the loose glyphs and the glyphs inside the vertical
# stacks: every entry breathes and swaps independently, so they only differ in
# how their positions were chosen.
global.slot = 0;

# These MUST exist before add_glyph runs. A bare identifier first assigned
# inside a function creates a hash LOCAL to that call, which is silently
# discarded on return — that is exactly what made the whole ambient field
# invisible once glyph creation moved into a helper. Verified with plyrun.
amb.bucket = [];
amb.index = [];
amb.x = [];
amb.y = [];
amb.phase = [];
amb.speed = [];
amb.swap = [];
amb.sprite = [];

fun add_glyph(bucket, x, y) {
  i = global.slot;
  amb.bucket[i] = bucket;
  amb.index[i] = Math.Int(Math.Random() * global.glyph_count);
  amb.phase[i] = Math.Random() * 2 * Math.Pi;
  amb.speed[i] = 0.15 + Math.Random() * 0.30;
  amb.swap[i] = Math.Int(70 + Math.Random() * 320);

  # Bucket lookup is inlined rather than wrapped in a function returning an
  # image: a silent null would mean an invisible field.
  if (bucket == 0) start_image = glyph.a0[amb.index[i]];
  if (bucket == 1) start_image = glyph.a1[amb.index[i]];
  if (bucket == 2) start_image = glyph.a2[amb.index[i]];

  amb.x[i] = Math.Int(x);
  amb.y[i] = Math.Int(y);
  amb.sprite[i] = Sprite(start_image);
  amb.sprite[i].SetPosition(amb.x[i], amb.y[i], 10);
  amb.sprite[i].SetOpacity(0);
  global.slot++;
}

# Loose glyphs, scattered anywhere.
if (global.shutdown == 0) {
  for (i = 0; i < global.loose_count; i++) {
    add_glyph(Math.Int(Math.Random() * 3),
              Math.Random() * (global.W - 70),
              Math.Random() * (global.H - 70));
  }
}

# Short vertical stacks of 2-6 glyphs, kept to the outer bands so they never
# crowd the login block in the middle.
if (global.shutdown == 1) global.stack_count = 0;

for (s = 0; s < global.stack_count; s++) {
  bucket = Math.Int(Math.Random() * 3);
  if (bucket == 0) box = @BOX0@;
  if (bucket == 1) box = @BOX1@;
  if (bucket == 2) box = @BOX2@;

  len = Math.Int(@STACK_MIN@ + Math.Random() * @STACK_SPAN@);
  step = Math.Int(box * 0.92);

  if (Math.Random() < 0.5) {
    sx = global.W * (0.03 + Math.Random() * 0.27);
  } else {
    sx = global.W * (0.62 + Math.Random() * 0.33);
  }
  sy = Math.Random() * (global.H - len * step - 20);

  for (n = 0; n < len; n++) {
    add_glyph(bucket, sx, sy + n * step);
  }
}

global.amb_count = global.slot;

#----------------------------------------- Ghost word --------------------------

ghost.image = Image("ghost.png");
ghost.sprite = Sprite(ghost.image);
global.ghost_x = Math.Int(global.cx - ghost.image.GetWidth() / 2);
global.ghost_y = Math.Int(global.cy - ghost.image.GetHeight() / 2);
ghost.sprite.SetPosition(global.ghost_x, global.ghost_y, 5);
ghost.sprite.SetOpacity(0);

#----------------------------------------- Katakana column ---------------------

global.column_count = @COLUMN@;
global.col_box = column.image[0].GetHeight();
column.step = Math.Int(global.col_box * 0.82);
column.top = global.cy - (global.column_count - 1) * column.step / 2;

column.by = [];
global.col_x = Math.Int(global.W * 0.80 - global.col_box / 2);

for (i = 0; i < global.column_count; i++) {
  column.sprite[i] = Sprite(column.image[i]);
  column.by[i] = Math.Int(column.top + i * column.step - global.col_box / 2);
  column.sprite[i].SetPosition(global.col_x, column.by[i], 10);
  column.sprite[i].SetOpacity(0);
}

#----------------------------------------- Welcome, line, hint -----------------

line.source = Image("line.png");

line.rust_source = Image("line_rust.png");

welcome.image = Image("welcome.png");
welcome.sprite = Sprite(welcome.image);
global.welcome_x = Math.Int(global.cx - welcome.image.GetWidth() / 2);
global.welcome_y =
  Math.Int(global.cy - global.H * @WELCOME_DY@ - welcome.image.GetHeight() / 2);
welcome.sprite.SetPosition(global.welcome_x, global.welcome_y, 10001);
welcome.sprite.SetOpacity(0);

global.line_width = Math.Int(global.W * @LINE_W@);
global.line_y = Math.Int(global.cy + global.H * @LINE_DY@);
global.line_x0 = Math.Int(global.cx - global.line_width / 2);

# The underline is seven abutting pieces rather than one bar. Idle they tile
# exactly (each piece runs to where the next one starts, so no seam) and read
# as a single rule; on a rejected key each piece slides on its own and the
# gaps that open are what makes the line look broken instead of just blinked.
# Every piece carries a rust twin at the same spot for the colour crossfade.
seg.x = [];
seg.w = [];
seg.j = [];
seg.k = [];
seg.bone = [];
seg.rust = [];

for (i = 0; i < global.seg_count; i++) {
  a = Math.Int(global.line_x0 + global.line_width * i / global.seg_count);
  b = Math.Int(global.line_x0 + global.line_width * (i + 1) / global.seg_count);
  seg.x[i] = a;
  seg.w[i] = b - a;
  seg.j[i] = 0;
  seg.k[i] = 0;

  seg.bone[i] = Sprite(line.source.Scale(seg.w[i], @LINE_H@));
  seg.bone[i].SetPosition(a, global.line_y, 10001);
  seg.bone[i].SetOpacity(0);

  seg.rust[i] = Sprite(line.rust_source.Scale(seg.w[i], @LINE_H@));
  seg.rust[i].SetPosition(a, global.line_y, 10002);
  seg.rust[i].SetOpacity(0);
}

# Indeterminate scanner that sweeps the rule while the key is checked. It
# never claims a percentage, because nothing here knows one.
global.sweep_w = Math.Int(global.line_width * 0.22);
sweep.sprite = Sprite(line.source.Scale(global.sweep_w, @LINE_H@));
sweep.sprite.SetPosition(global.line_x0, global.line_y, 10003);
sweep.sprite.SetOpacity(0);

hint.image = Image("hint.png");
hint.sprite = Sprite(hint.image);
hint.sprite.SetPosition(
  Math.Int(global.cx - hint.image.GetWidth() / 2),
  Math.Int(global.H - global.H * 0.034 - hint.image.GetHeight()),
  10001);
hint.sprite.SetOpacity(0);

#----------------------------------------- HUD brackets ------------------------

global.br_w = Math.Int(global.W * @BR_W@);
global.br_h = Math.Int(global.H * @BR_H@);
global.br_arm = Math.Int(Math.Min(global.br_w, global.br_h) * 0.07);

bracket.x0 = global.cx - global.br_w / 2;
bracket.x1 = global.cx + global.br_w / 2;
bracket.y0 = Math.Int(global.cy - global.br_h / 2);
bracket.y1 = Math.Int(global.cy + global.br_h / 2);

# ex/ey is the corner's outward direction: on a rejected key the brackets are
# shoved away from the middle instead of resized, which would need a fresh
# Image.Scale every frame.
bracket.bx = [];
bracket.by = [];
bracket.ex = [];
bracket.ey = [];
global.br_push = Math.Int(global.br_w * 0.015);

fun make_bracket(slot, x, y, w, h, ex, ey) {
  bracket.bx[slot] = Math.Int(x);
  bracket.by[slot] = Math.Int(y);
  bracket.ex[slot] = ex * global.br_push;
  bracket.ey[slot] = ey * global.br_push;
  bracket.sprite[slot] = Sprite(line.source.Scale(w, h));
  bracket.sprite[slot].SetPosition(bracket.bx[slot], bracket.by[slot], 10001);
  bracket.sprite[slot].SetOpacity(0);
}

make_bracket(0, bracket.x0, bracket.y0, global.br_arm, 2, -1, -1);
make_bracket(1, bracket.x0, bracket.y0, 2, global.br_arm, -1, -1);
make_bracket(2, bracket.x1 - global.br_arm, bracket.y0, global.br_arm, 2, 1, -1);
make_bracket(3, bracket.x1 - 2, bracket.y0, 2, global.br_arm, 1, -1);
make_bracket(4, bracket.x0, bracket.y1 - 2, global.br_arm, 2, -1, 1);
make_bracket(5, bracket.x0, bracket.y1 - global.br_arm, 2, global.br_arm, -1, 1);
make_bracket(6, bracket.x1 - global.br_arm, bracket.y1 - 2, global.br_arm, 2, 1, 1);
make_bracket(7, bracket.x1 - 2, bracket.y1 - global.br_arm, 2, global.br_arm, 1, 1);
global.bracket_count = 8;

#----------------------------------------- Typed characters --------------------

dot.square = Image("dot.png");
global.dot_box = dot.square.GetWidth();
global.hit_box = glyph.hit[0].GetWidth();
global.dot_spacing = Math.Int(global.H * @DOT_SPACING@);
global.dot_y = Math.Int(global.line_y - global.H * @DOT_DY@);

#----------------------------------------- Rejected key ------------------------

# The marks already on screen when a key is rejected are thrown off the line
# and burn out. They need sprites of their own: the rejection is detected by a
# fresh password request arriving, which immediately resets the real dot row
# to zero, so the shards cannot borrow those sprites.
shard.x = [];
shard.y = [];
shard.vx = [];
shard.vy = [];
shard.sprite = [];

for (i = 0; i < global.max_bullets; i++) {
  shard.x[i] = 0;
  shard.y[i] = 0;
  shard.vx[i] = 0;
  shard.vy[i] = 0;
  shard.sprite[i] = Sprite(dot.square);
  shard.sprite[i].SetOpacity(0);
}

# Three horizontal bands that get displaced during the first frames of the
# rejection. In the HTML model this is a per-pixel tear; here it is per-sprite,
# so a sprite straddling a band edge moves whole.
tear.y0 = [];
tear.y1 = [];
tear.dx = [];

for (i = 0; i < 3; i++) {
  tear.y0[i] = 0;
  tear.y1[i] = 0;
  tear.dx[i] = 0;
}

global.status_y = Math.Int(global.line_y + global.H * @STATUS_DY@);
global.att_y = Math.Int(global.status_y + global.H * @ATT_DY@);

den.rust_image = Image("denied_rust.png");
den.bone_image = Image("denied_bone.png");
global.den_x = Math.Int(global.cx - den.rust_image.GetWidth() / 2);

den.rust = Sprite(den.rust_image);
den.rust.SetPosition(global.den_x, global.status_y, 10002);
den.rust.SetOpacity(0);

den.bone = Sprite(den.bone_image);
den.bone.SetPosition(global.den_x, global.status_y, 10001);
den.bone.SetOpacity(0);

att.sprite = Sprite();
att.sprite.SetPosition(global.cx, global.att_y, 10001);
att.sprite.SetOpacity(0);

ver.image = Image("verifying.png");
ver.sprite = Sprite(ver.image);
ver.sprite.SetPosition(
  Math.Int(global.cx - ver.image.GetWidth() / 2), global.status_y, 10001);
ver.sprite.SetOpacity(0);

#----------------------------------------- Farewell (shutdown) -----------------

global.bye_alpha = 0;

bye.image = Image("goodbye.png");
bye.sprite = Sprite(bye.image);
bye.sprite.SetPosition(
  Math.Int(global.cx - bye.image.GetWidth() / 2),
  Math.Int(global.cy - global.H * @BYE_DY@ - bye.image.GetHeight() / 2),
  10001);
bye.sprite.SetOpacity(0);

global.rule_y = Math.Int(global.cy + global.H * @RULE_DY@);
bye.rule = Sprite(line.source.Scale(global.line_width, 2));
bye.rule.SetPosition(global.cx - global.line_width / 2, global.rule_y, 10001);
bye.rule.SetOpacity(0);

off.image = Image("offline.png");
off.sprite = Sprite(off.image);
off.sprite.SetPosition(
  Math.Int(global.cx - off.image.GetWidth() / 2),
  Math.Int(global.rule_y + global.H * @LABEL_DY@ - off.image.GetHeight() / 2),
  10001);
off.sprite.SetOpacity(0);

#----------------------------------------- Progress ----------------------------

progress.sprite = Sprite();
progress.sprite.SetPosition(0, global.H - 2, 1);
progress.sprite.SetOpacity(0);

message_sprite = Sprite();
message_sprite.SetPosition(10, 10, 10005);

#----------------------------------------- Helpers -----------------------------

fun hide_password_ui() {
  global.shown = 0;
  for (i = 0; dot.sprite[i]; i++) {
    dot.sprite[i].SetOpacity(0);
  }
}

fun place_dots(count) {
  group = (count - 1) * global.dot_spacing;
  start = global.cx - group / 2;

  for (i = 0; i < count; i++) {
    if (!dot.sprite[i]) {
      dot.sprite[i] = Sprite();
    }
    # Slots past the previous count are newly typed characters, so they start
    # their resolve animation now. Existing slots keep theirs.
    if (i >= global.shown) {
      dot.born[i] = global.frame;
      dot.state[i] = -1;
    }
    dot.x[i] = Math.Int(start + i * global.dot_spacing);
  }

  for (i = count; dot.sprite[i]; i++) {
    dot.sprite[i].SetOpacity(0);
  }
}

fun update_dots() {
  for (i = 0; i < global.shown; i++) {
    age = global.frame - dot.born[i];

    if (age < 11) {
      pick = Math.Int(mod(Math.Int(age / 2) + i * 7, global.glyph_count));
      if (dot.state[i] != pick) {
        dot.sprite[i].SetImage(glyph.hit[pick]);
        dot.state[i] = pick;
      }
      dot.sprite[i].SetPosition(
        dot.x[i] - global.hit_box / 2,
        global.dot_y - global.hit_box / 2,
        10002);
    } else {
      if (dot.state[i] != -2) {
        dot.sprite[i].SetImage(dot.square);
        dot.state[i] = -2;
      }
      dot.sprite[i].SetPosition(
        dot.x[i] - global.dot_box / 2,
        global.dot_y - global.dot_box / 2,
        10002);
    }
    if (global.state == 1) {
      dot.sprite[i].SetOpacity(0.9 * 0.55 * global.ui_alpha);
    } else {
      dot.sprite[i].SetOpacity(0.9 * global.ui_alpha);
    }
  }
}

# Displacement for a sprite sitting at y, while the tear is active.
fun tear_dx(y) {
  td = 0;
  if (global.tearing == 1) {
    for (tb = 0; tb < 3; tb++) {
      if (y >= tear.y0[tb]) {
        if (y < tear.y1[tb]) td = tear.dx[tb];
      }
    }
  }
  return td * global.tear_k;
}

# Only run while the tear is on: repositioning the whole field every frame of
# a normal boot would be pure waste.
fun tear_field() {
  for (ti = 0; ti < global.amb_count; ti++) {
    amb.sprite[ti].SetPosition(
      Math.Int(amb.x[ti] + tear_dx(amb.y[ti])), amb.y[ti], 10);
  }
  ghost.sprite.SetPosition(
    Math.Int(global.ghost_x + tear_dx(global.cy)), global.ghost_y, 5);
  for (ti = 0; ti < global.column_count; ti++) {
    column.sprite[ti].SetPosition(
      Math.Int(global.col_x + tear_dx(column.by[ti])), column.by[ti], 10);
  }
}

# The login block shakes for the whole rejection, not just the tear window.
# With decay and jx both at zero this puts everything back on its base spot,
# so it doubles as the restore pass.
fun place_login() {
  pdx = global.jx + tear_dx(global.cy);

  welcome.sprite.SetPosition(
    Math.Int(global.welcome_x + pdx), global.welcome_y, 10001);

  for (pi = 0; pi < global.seg_count; pi++) {
    pox = seg.j[pi] * global.W * 0.028 * global.decay;
    poy = seg.k[pi] * 8 * global.decay;
    ppx = Math.Int(seg.x[pi] + pox + pdx);
    ppy = Math.Int(global.line_y + poy);
    seg.bone[pi].SetPosition(ppx, ppy, 10001);
    seg.rust[pi].SetPosition(ppx, ppy, 10002);
  }

  for (pi = 0; pi < global.bracket_count; pi++) {
    bracket.sprite[pi].SetPosition(
      Math.Int(bracket.bx[pi] + bracket.ex[pi] * global.decay + pdx),
      Math.Int(bracket.by[pi] + bracket.ey[pi] * global.decay),
      10001);
  }

  den.rust.SetPosition(Math.Int(global.den_x + pdx), global.status_y, 10002);
  den.bone.SetPosition(Math.Int(global.den_x + pdx), global.status_y, 10001);
}

fun start_denial() {
  global.attempts++;
  global.denying = 1;
  global.deny_frame = global.frame;
  global.tearing = 1;
  global.tear_k = 1;
  global.typed_any = 0;
  global.state = 0;

  # The key was rejected, so the loading bar it started is a lie now: drop it
  # and let the next attempt grow a fresh one.
  global.verify_t = -1;
  global.frozen = 0;
  global.max_progress = 0.0;
  progress.sprite.SetOpacity(0);

  # Snapshot the marks before the incoming request clears the dot row.
  global.shard_count = global.shown;
  for (si = 0; si < global.shard_count; si++) {
    shard.x[si] = dot.x[si];
    shard.y[si] = global.dot_y;
    shard.vx[si] = (Math.Random() - 0.5) * global.W * 0.0032;
    shard.vy[si] = (Math.Random() - 0.70) * global.H * 0.0026;
  }

  for (si = 0; si < global.seg_count; si++) {
    seg.j[si] = (Math.Random() - 0.5) * 2;
    seg.k[si] = (Math.Random() - 0.5) * 2;
  }

  for (si = 0; si < 3; si++) {
    sby = global.H * (0.18 + Math.Random() * 0.60);
    tear.y0[si] = sby;
    tear.y1[si] = sby + global.H * (0.02 + Math.Random() * 0.05);
    tear.dx[si] = (Math.Random() - 0.5) * global.W * 0.060;
  }

  sn = global.attempts;
  if (sn > global.max_att) sn = global.max_att;
  att.sprite.SetImage(att.image[sn - 1]);
  att.sprite.SetPosition(
    Math.Int(global.cx - att.image[sn - 1].GetWidth() / 2),
    global.att_y, 10001);
}

fun denial_frame() {
  dage = global.frame - global.deny_frame;

  dd = 1 - dage / global.deny_frames;
  if (dd < 0) dd = 0;
  global.decay = dd * dd * dd;

  global.tear_k = 1 - dage / global.tear_frames;
  if (global.tear_k <= 0) {
    global.tear_k = 0;
    if (global.tearing == 1) {
      global.tearing = 0;
      tear_field();          # one pass with zero displacement puts it back
    }
  }
  if (global.tearing == 1) tear_field();

  global.jx = (Math.Random() - 0.5) * global.W * 0.0126 * global.decay;

  if (dage < global.shard_frames) {
    dsa = 1 - dage / global.shard_frames;
    for (di = 0; di < global.shard_count; di++) {
      dsx = shard.x[di] + shard.vx[di] * dage + global.jx;
      dsy = shard.y[di] + shard.vy[di] * dage + 0.03 * dage * dage;
      shard.sprite[di].SetPosition(
        Math.Int(dsx - global.dot_box / 2),
        Math.Int(dsy - global.dot_box / 2), 10002);
      shard.sprite[di].SetOpacity(0.9 * dsa);
    }
  } else {
    for (di = 0; di < global.shard_count; di++) {
      shard.sprite[di].SetOpacity(0);
    }
    global.shard_count = 0;
  }

  if (dage >= global.deny_frames) {
    global.denying = 0;
    global.decay = 0;
    global.jx = 0;
  }

  place_login();
}

fun commit_unlock() {
  global.state = 3;
  global.unlock_frame = global.frame;
  global.ui_alpha = 1.0;
}

fun update_progress(value) {
  if (value > global.max_progress) {
    global.max_progress = value;
    width = Math.Int(global.W * value);
    if (width < 1) width = 1;
    progress.sprite.SetImage(line.source.Scale(width, 2));
    progress.sprite.SetOpacity(0.75);
  }
}

#----------------------------------------- Frame loop --------------------------

fun shutdown_frame() {
  t = global.frame / global.fps;

  k = global.frame / 45.0;
  if (k > 1) k = 1;
  breath = 0.94 + 0.06 * (Math.Cos(t * 0.7) + 1) / 2;
  global.bye_alpha = 0.92 * k * breath;

  bye.sprite.SetOpacity(global.bye_alpha);
  bye.rule.SetOpacity(0.30 * k);
  off.sprite.SetOpacity(0.85 * k);

  for (i = 0; i < global.bracket_count; i++) {
    bracket.sprite[i].SetOpacity(0.28 * k);
  }
}

fun refresh_callback() {
  global.frame++;

  if (global.shutdown == 1) {
    shutdown_frame();
    return 0;
  }

  t = global.frame / global.fps;

  # Nothing has rejected the key within the window a rejection would have
  # arrived in, so treat it as accepted.
  # Backstop only. The real commit happens in progress_callback, on the
  # wall clock; this fires only if boot progress somehow stops arriving.
  if (global.state == 1) {
    if (global.frame - global.verify_frame >= global.verify_commit) {
      commit_unlock();
    }
  }

  # After a correct passphrase everything fades away, leaving only the
  # progress line.
  if (global.state == 3) {
    k = (global.frame - global.unlock_frame) / 25.0;
    if (k > 1) k = 1;
    global.ui_alpha = 1 - k;
    global.field_dim = 1 - k;
  } else {
    global.field_dim = 1;
    if (global.state == 1) global.ui_alpha = 0.82;
  }

  if (global.denying == 1) {
    denial_frame();
    # the field flares while the rejection plays
    global.field_dim = 1 + 1.2 * global.decay;
  }

  for (i = 0; i < global.amb_count; i++) {
    if (mod(global.frame, amb.swap[i]) < 1) {
      amb.index[i] = Math.Int(Math.Random() * global.glyph_count);
      if (amb.bucket[i] == 0) swap_image = glyph.a0[amb.index[i]];
      if (amb.bucket[i] == 1) swap_image = glyph.a1[amb.index[i]];
      if (amb.bucket[i] == 2) swap_image = glyph.a2[amb.index[i]];
      amb.sprite[i].SetImage(swap_image);
    }
    b = (Math.Cos(t * amb.speed[i] + amb.phase[i]) + 1) / 2;
    amb.sprite[i].SetOpacity((0.13 + b * 0.23) * global.field_dim);
  }

  gb = (Math.Cos(t * 0.12) + 1) / 2;
  ghost.sprite.SetOpacity((0.30 + gb * 0.10) * global.field_dim);

  for (i = 0; i < global.column_count; i++) {
    cb = (Math.Cos(t * 0.3 + i * 0.7) + 1) / 2;
    column.sprite[i].SetOpacity((0.10 + cb * 0.06) * global.field_dim);
  }

  welcome.sprite.SetOpacity(0.92 * global.ui_alpha);

  if (global.shown > 0) {
    base = 0.55;
  } else {
    base = 0.30;
  }

  # Once a key has been rejected the standing notice takes over the hint's job.
  if (global.shown > 0 || global.attempts > 0) {
    hint.sprite.SetOpacity(0);
  } else {
    hint.sprite.SetOpacity(0.85 * global.ui_alpha);
  }

  tot = base * global.ui_alpha + 0.35 * global.decay;
  if (tot > 1) tot = 1;
  for (i = 0; i < global.seg_count; i++) {
    seg.rust[i].SetOpacity(tot * global.decay);
    seg.bone[i].SetOpacity(tot * (1 - global.decay));
  }

  for (i = 0; i < global.bracket_count; i++) {
    ba = 0.28 * global.ui_alpha + 0.45 * global.decay;
    if (ba > 1) ba = 1;
    bracket.sprite[i].SetOpacity(ba);
  }

  # Verifying: the scanner sweeps the rule and back, ~4.4 s per round trip.
  if (global.state == 1) {
    vage = global.frame - global.verify_frame;
    vk = vage / 9.0;
    if (vk > 1) vk = 1;
    ver.sprite.SetOpacity(0.9 * vk);

    sp = mod(vage, 220) / 220.0;
    if (sp > 0.5) sp = 1 - sp;
    sp = sp * 2;
    sweep.sprite.SetPosition(
      Math.Int(global.line_x0 + sp * (global.line_width - global.sweep_w)),
      global.line_y, 10003);
    sweep.sprite.SetOpacity(0.80 * global.ui_alpha);
  } else {
    ver.sprite.SetOpacity(0);
    sweep.sprite.SetOpacity(0);
  }

  # ACCESS DENIED: loud and strobing through the rejection, then a quiet
  # standing notice until the next keystroke.
  if (global.attempts > 0 && global.shown == 0) {
    if (global.denying == 1) {
      da = 0.35 + 0.6 * global.decay;
      if (global.decay > 0.35) {
        if (Math.Random() < 0.18) da = da * 0.25;
      }
    } else {
      da = 0.34;
    }
    da = da * global.ui_alpha;
    den.rust.SetOpacity(da * global.decay);
    den.bone.SetOpacity(da * (1 - global.decay));
    att.sprite.SetOpacity(0.55 * global.ui_alpha);
  } else {
    den.rust.SetOpacity(0);
    den.bone.SetOpacity(0);
    att.sprite.SetOpacity(0);
  }

  update_dots();
}

Plymouth.SetRefreshFunction(refresh_callback);

#----------------------------------------- Callbacks ---------------------------

fun display_normal_callback() {
  # A submitted answer drops the entry and brings the display back to normal
  # while cryptsetup chews on it. That is the verifying beat — NOT an unlock:
  # a rejection looks identical from here and only announces itself later, by
  # a fresh password request.
  if (global.typed_any == 1 && global.state == 0) {
    global.state = 1;
    global.verify_frame = global.frame;
    global.verify_t = -1;      # re-anchored by the next progress tick
    global.frozen = 0;
    global.typed_any = 0;
    return 0;
  }

  if (global.state == 0) {
    global.ui_alpha = 0.0;
    hide_password_ui();
  }
}

fun display_password_callback(prompt, bullets) {
  global.password_shown = 1;

  # Being asked again after a key was submitted is the only signal Plymouth
  # gives that the key was wrong.
  if (global.state == 1 || global.state == 3) {
    start_denial();
  }

  global.state = 0;
  global.ui_alpha = 1.0;

  count = bullets;
  if (count > global.max_bullets) count = global.max_bullets;
  if (count > 0) global.typed_any = 1;

  place_dots(count);
  global.shown = count;
}

Plymouth.SetDisplayNormalFunction(display_normal_callback);
Plymouth.SetDisplayPasswordFunction(display_password_callback);

fun progress_callback(duration, value) {
  if (global.shutdown == 1) return 0;

  if (global.state == 1) {
    if (global.verify_t < 0) {
      global.verify_t = duration;
      global.frozen = 0;
    }

    moved = duration - global.verify_t;
    if (moved < 0.02) global.frozen++;

    if (global.frozen >= global.frozen_needed) {
      # The clock was demonstrably frozen, so it is the password pause. Its
      # resuming means ask-for-password finished, i.e. the key was accepted.
      if (moved >= global.resume_secs) commit_unlock();
    } else {
      # Progress was never paused on this system; fall back to waiting out
      # the measured argon2 time.
      if (moved >= global.verify_secs) commit_unlock();
    }
  }

  # Only after the key is accepted. Drawing it while verifying showed a
  # frozen sliver of a bar on every attempt, including rejected ones.
  if (global.state == 3) {
    update_progress(value);
  }
}

Plymouth.SetBootProgressFunction(progress_callback);

fun display_message_callback(text) {
  message = Image.Text(text, @BONE_R@, @BONE_G@, @BONE_B@);
  message_sprite.SetImage(message);
  message_sprite.SetOpacity(1);
}

fun hide_message_callback(text) {
  message_sprite.SetOpacity(0);
}

Plymouth.SetDisplayMessageFunction(display_message_callback);
Plymouth.SetHideMessageFunction(hide_message_callback);
'''

METADATA = """[Plymouth Theme]
Name=Omarchy Minimal
Description=NieR-inspired minimal unlock screen: katakana field, ghost word, thin password line.
ModuleName=script

[script]
ImageDir=/usr/share/plymouth/themes/omarchy-minimal
ScriptFile=/usr/share/plymouth/themes/omarchy-minimal/omarchy.script
ConsoleLogBackgroundColor=0x050505
MonospaceFont=JetBrainsMono Nerd Font 22
Font=JetBrainsMono Nerd Font 32
"""


def main():
    if len(sys.argv) < 2:
        sys.exit(f"usage: {sys.argv[0]} <output-dir>")
    d = Path(sys.argv[1])
    d.mkdir(parents=True, exist_ok=True)
    if not any(d.glob("a0_*.png")):
        build_assets(d)
    build_script(d)
    (d / "omarchy-minimal.plymouth").write_text(METADATA)
    print(f"theme built in {d}: {len(list(d.iterdir()))} files")


if __name__ == "__main__":
    main()
