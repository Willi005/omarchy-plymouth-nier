# Limine bootloader theme — design

Date: 2026-08-26. Status: approved, implementing.

## Goal

The Limine boot menu is the one screen in the boot chain still wearing Omarchy's
stock Tokyo Night palette. It appears immediately before the Plymouth LUKS
prompt, so the mismatch is visible as a hard cut. This brings it into the same
NieR bone palette and composition language as the boot and shutdown screens.

## What Limine can and cannot do

Established by reading `common/menu.c` and `common/lib/gterm.c` (trunk), by
`strings`/`objdump` on the shipped `BOOTX64.EFI` 12.5.2, and — decisively — by
booting Limine under QEMU with the real config (see Verification).

Available:

- `wallpaper` — BMP/PNG/JPEG/QOI, full screen. **Multiple `wallpaper` lines are
  allowed and Limine picks one at random per boot** (`config_get_value(config,
  rand32() % wallpaper_count, "WALLPAPER")`).
- `term_background` in `TTRRGGBB`. `colour_blend()` computes
  `alpha = 255 - A(fg)`, so **`TT=00` is opaque and `TT=FF` is fully
  transparent** — the doc's "TT stands for transparency" is literal, and the
  summary reading of "alpha" is backwards.
- 16-colour palette, `term_margin` (default 64), `term_margin_gradient`
  (default 4), `interface_branding`, `interface_help_hidden`.
- `term_font_scale` up to 8, nearest-neighbour.

Not available:

- Any animation.
- **Antialiased text.** `term_font` requires a CP437 bitmap and Limine
  "assumes all fonts are of width 8" — one byte per glyph row. The terminal is
  a 1-bit blitter. There is no smooth-text option at any setting.
- Moving or restyling the entry tree; it is drawn by `menu.c`.

Two corrections to earlier assumptions, both found by disassembly then confirmed
in QEMU:

- The `┌─┤ %s ├─┐` frame in the binary belongs to the **editor**, not the menu.
  The menu draws no box; entries float, and `interface_branding` is printed
  centred on its own row.
- The menu block is centred on **both** axes by Limine itself:
  `(cols - max_tree_len - 3)/2` and `(rows - max_tree_height)/2`. No config
  needed, and no config can override it.

## Decision

**Variant B, "terminal desnudo"**, chosen from three offered on an interactive
simulator (artifact `9e95ffba-1fdf-4faa-a1dd-2f9372cfd21d`): flat ground, bone
palette, four corner brackets, help visible, no ghost word and no katakana
field. The user's reasoning: with a bare ground the 8-px glyph limit stops
mattering, because there is no artwork whose detail could be lost.

Consequence: Limine's **built-in font** is kept. A custom 8x16 face derived from
JetBrains Mono was considered and rejected — at 8 px wide the letterforms are
gone anyway, and Limine's VGA face is hand-tuned for that cell.

The random-wallpaper trick is therefore not used either: with no glyph field
there is nothing to vary between boots. It stays documented for a future
variant.

## Composition

Corner brackets only, never a traced rectangle — the same shape as the login
HUD (`build-theme.py: make_bracket`, eight L-arms, 2 px thick, opacity 0.28).

All geometry is a **fraction of the screen's shorter side**, not a pixel count,
so the proportion holds from 1366x768 to 3840x2160:

| quantity | value |
|---|---|
| bracket inset | `min(W,H) * 0.030` |
| bracket arm | `min(W,H) * 0.065` |
| bracket thickness | `max(2, min(W,H) * 0.0028)` |
| bracket colour | bone `#CFC9B0` at 30% over ground `#050505` |
| `term_margin` | not set — Limine's default (64) |
| `term_font_scale` | not set — Limine's default (1x1) |

**Nothing about the text layer is derived from the panel size.** Two attempts to
compute `term_font_scale` from the detected resolution both failed, the second
one surviving all the way to a real boot: `/sys/class/drm` reports the *panel's*
mode, but the menu runs at whatever GOP mode Limine picks when
`interface_resolution` is unset, and the two need not match. On this machine the
result was text far too large. The menu's own mode cannot be read back from a
booted system, so the text layer keeps Limine's defaults, exactly as the stock
Omarchy config does. Only the wallpaper is rendered per-resolution, and it is
`stretched`, so it adapts to whatever mode is chosen.

## Configuration

A delimited, managed block in the global header of `/boot/limine.conf`:

```
### >>> omarchy-nier >>>
interface_branding: OMARCHY
interface_branding_color: CFC9B0
interface_help_color: 55503F
interface_help_color_bright: 8C8770
wallpaper: boot():/omarchy-nier/bg.png
wallpaper_style: stretched
term_background: FF000000
term_foreground: CFC9B0
term_background_bright: 00050505
term_foreground_bright: FAFCFB
term_palette: 050505;B0563F;55503F;8C8770;4A4638;55503F;55503F;CFC9B0
term_palette_bright: 4A4638;B0563F;8C8770;CFC9B0;55503F;8C8770;8C8770;FAFCFB
term_margin: <computed>
term_margin_gradient: 0
term_font_scale: <computed>
### <<< omarchy-nier <<<
```

Palette index 6 (cyan) is deliberately set to chrome: `menu.c` prints an entry's
`comment:` as `\e[36m`, and QEMU confirmed that string renders at the bottom of
the screen above the countdown, not beside the entry.

`timeout` and `default_entry` are **never touched** — those are boot behaviour,
not theme.

## Ownership and rollback

- Generator and assets are packaged under `/usr/share/omarchy-plymouth-nier/limine/`,
  owned by pacman.
- A scriptlet copies `bg.png` onto the ESP and rewrites only the global header of
  `limine.conf`, above the first entry line. Boot entries stay the property of
  `limine-entry-tool`.
- The original header is preserved at `/boot/limine.conf.omarchy-nier.bak` on
  first apply; revert restores it. Second safety net: the stock header also
  ships at `/usr/share/omarchy/default/limine/limine.conf`.
- No re-enrolment is needed: `ENABLE_ENROLL_LIMINE_CONFIG` is unset on this
  system. Secure Boot is disabled, so the wallpaper needs no blake2b hash —
  under Secure Boot it would be silently skipped rather than panic.

## Verification

New capability this round: **Limine runs under QEMU with OVMF**, so this screen
can be seen before it is committed. This is the first screen in the project that
was ever previewed for real; Plymouth's cannot be.

```
qemu-system-x86_64 -machine q35 -m 512 \
  -drive if=pflash,format=raw,readonly=on,file=/usr/share/edk2/x64/OVMF_CODE.4m.fd \
  -drive if=pflash,format=raw,file=vars.fd \
  -drive file=fat:rw:esp,format=raw \
  -vga none -device VGA,xres=2880,yres=1800,vgamem_mb=64 \
  -display none -monitor stdio
```
with `screendump out.ppm` piped to the monitor.

Confirmed at 1920x1080 and 2880x1800: PNG wallpaper loads, `TT=FF` transparency
works, palette lands, brackets sit correctly, tree and reverse-video selection
render as modelled, both help rows and the comment footer appear.

**What QEMU cannot answer, and this bit back once:** the resolution is handed to
it on the command line (`xres=`/`yres=`), so any conclusion that depends on the
screen mode is circular. It validates composition, palette, transparency,
brackets and that the config parses. It says nothing about which GOP mode the
real firmware picks — which is why the derived `term_font_scale` looked correct
in a screenshot and was wrong on the machine.

It also cannot say how a real panel scales a non-native `interface_resolution`.
That idea is shelved — it only mattered as a route to softer text, which
variant B makes moot.

## Out of scope

Custom bitmap font; random per-boot wallpapers; the other `GetMode()` screens;
`interface_resolution` tricks. All recorded in the vault for later.
