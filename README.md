# omarchy-plymouth-nier

A NieR:Automata-flavoured theme for the whole [Omarchy](https://omarchy.org)
boot chain: the Limine bootloader menu, the screen that asks for the LUKS
passphrase at power-on, and the farewell screen at shutdown.

Bone `#CFC9B0` on near-black. A very dim ステム ghost word breathing behind a
field of katakana that swap on their own timers, a vertical シ ス テ ム column,
HUD corner brackets, a welcome line and a thin segmented password rule. Typed
characters appear as a katakana that cycles briefly and then resolves to a
solid mark. A rejected key tears the screen apart; an accepted one fades
everything away and leaves a single progress line along the bottom edge.

Everything visible is a pre-rendered PNG, so nothing depends on font
resolution inside the initramfs.

The bootloader menu that precedes it is a plain 1-bit character grid, so it
gets the restrained version of the same language: flat ground, the bone
palette, and four corner brackets. See
[The bootloader menu](#the-bootloader-menu).

## Install

On Arch / Omarchy:

```bash
git clone https://github.com/Willi005/omarchy-plymouth-nier
cd omarchy-plymouth-nier
makepkg -si
```

Nothing to edit first — configuration lives in `/etc/omarchy-plymouth-nier.conf`
and is changed afterwards, see [Configuring it](#configuring-it).

### Or from the pacman repository

Real `pacman -S`, and updates arrive with `-Syu`. Import the signing key, then
add the repository:

```bash
curl -fsSL https://github.com/Willi005/omarchy-plymouth-nier/releases/download/repo/omarchy-nier-signing-key.asc \
    | sudo pacman-key --add -
sudo pacman-key --lsign-key 281082D757EF8AD66E7EB3BCA62334C0AAACC7D1
```

```ini
# /etc/pacman.conf
[omarchy-nier]
SigLevel = Required DatabaseOptional
Server = https://github.com/Willi005/omarchy-plymouth-nier/releases/download/repo
```

```bash
sudo pacman -Sy omarchy-plymouth-nier
```

The prebuilt package carries artwork rasterised for one panel, and Plymouth's
only scaler is nearest-neighbour, so on a different screen it would look wrong.
The installer notices — the package records what it was built for — and
regenerates on the spot when ImageMagick and the fonts are present, saying so
clearly when they are not. That is why the source build above is the primary
route.

**Not on the AUR yet.** Arch disabled new AUR registrations in June 2026 after a
malware campaign hit ~1,500 packages, and paused all AUR pushes on 1 August
after a third wave. The `aur/` directory here holds a ready-to-push PKGBUILD and
`.SRCINFO`; publishing is one command away from the day the service reopens.

That generates the assets, installs them to
`/usr/share/plymouth/themes/omarchy-minimal`, forces `DeviceScale=1`, sets the
default theme and rebuilds the boot image. It then themes the Limine menu:
the wallpaper is copied onto the ESP and a delimited block is spliced into the
global header of `limine.conf`. Boot entries are never touched, and no
initramfs rebuild is needed for that part — Limine reads its config at boot.

If a previous copy was installed by hand, pacman will refuse to overwrite
files it does not own. Take ownership once with:

```bash
makepkg -s
sudo pacman -U --overwrite '/usr/share/plymouth/themes/omarchy-minimal/*' \
    omarchy-plymouth-nier-*.pkg.tar.zst
```

Anywhere else: `sudo ./install.sh`.

## Roll back

`sudo pacman -R omarchy-plymouth-nier` undoes everything: it restores the stock
Plymouth theme, rebuilds the boot image, puts back the original `limine.conf`
header and removes the wallpaper. By hand:

```bash
sudo plymouth-set-default-theme omarchy && sudo mkinitcpio -P
sudo cp /boot/limine.conf.omarchy-nier.bak /boot/limine.conf   # see note
sudo rm -rf /boot/omarchy-nier
```

The stock Plymouth theme at `/usr/share/plymouth/themes/omarchy/` is never
modified. The `.bak` holds the whole file as it was at first install, so if
boot entries have changed since, copy only its header — everything above the
first line starting with `/`. The package's own revert does exactly that.

## Configuring it

Everything lives in one file, `/etc/omarchy-plymouth-nier.conf`, which pacman
preserves across upgrades (you get a `.pacnew` when the defaults change).

```bash
sudo $EDITOR /etc/omarchy-plymouth-nier.conf
sudo omarchy-nier-reconfigure --dry-run    # what would change
sudo omarchy-nier-reconfigure              # do it
```

Nothing takes effect on its own: every value is baked into pre-rendered images,
because Plymouth's only scaler is nearest-neighbour. Changing a colour means
re-rasterising the theme, which is what that command does. It regenerates into a
temporary directory and swaps the result in only once every step has succeeded,
so a config that fails to build leaves the working theme untouched.

**Palette** — shared by all three screens, so one change retints the boot menu
and the Plymouth screens together.

| key | default | what it is |
|---|---|---|
| `BONE` | `#CFC9B0` | everything the eye is meant to read |
| `DIM` | `#4A4638` | the ghost word, and nothing else |
| `CHROME` | `#55503F` | secondary text: the hint, the menu's help rows |
| `RUST` | `#B0563F` | the only chromatic note, and only on a rejected key |
| `GROUND` | `#050505` | the near-black behind everything |

**The ambient field**

| key | default | what it is |
|---|---|---|
| `GLYPHS` | `20` | loose katakana scattered across the screen |
| `STACKS` | `6` | short vertical piles, kept to the outer thirds |
| `STACK_MIN` / `STACK_MAX` | `2` / `6` | how tall a pile gets, picked at random |
| `ALPHABET` | 45 katakana | the pool the field draws from |
| `COLUMN` | empty | the vertical column; empty derives it from `GHOST_WORD` |
| `GHOST_WORD` | `システム` | the large word breathing behind everything |
| `GHOST_MAX_WIDTH` | `0.62` | ceiling on its width, as a fraction of the screen |
| `FIELD` | `on` | `off` removes glyphs, stacks **and** the column |

**Composition and text**

| key | default | what it is |
|---|---|---|
| `SCALE` | `0.70` | global size factor; artwork and layout scale as one |
| `NAME` | account's real name | who gets greeted |
| `WELCOME` / `GOODBYE` | `Welcome, {name}` | templates carrying `{name}` |
| `HINT` | `TYPE A PASSWORD · …` | the bottom line, hidden once you type |
| `RESOLUTION` | `auto` | the panel the artwork is rasterised for |

**The Limine boot menu**

| key | default | what it is |
|---|---|---|
| `BRANDING` | `OMARCHY` | the line centred at the top of the menu |
| `BRACKET_INSET` / `BRACKET_ARM` | `0.030` / `0.065` | corner brackets, as fractions of the shorter side |
| `MENU_HELP` | `on` | Limine's two help rows |

Every key also works as an environment variable prefixed `NIER_`, which wins
over the file — handy for trying something without editing anything:

```bash
NIER_FIELD=off NIER_SCALE=1.0 sudo omarchy-nier-reconfigure --dry-run
```

Validation fails loudly and names the offending key rather than rendering with a
silently substituted value:

```
config error: BONE='CFC9B0' is not #RRGGBB or #RGB
config error: STACK_MIN (8) is greater than STACK_MAX (4)
```

An unknown key only warns, so a config from a newer version does not break an
older install.

**One known cost:** after reconfiguring, `pacman -Qkk` reports the theme files
as altered. They are generated files owned by the package; this is inherent, not
a bug.

`auto` reads the preferred mode of the largest connected display from
`/sys/class/drm`, which works with no session running. The artwork has to be
rendered in real pixels for the target screen — see trap 1 below — so this is
not something the theme can adapt to at boot. Layout is expressed as
fractions of the window, so the composition holds its proportions; only the
asset sizes change. Verified at 1366x768, 1920x1080, 2880x1800 and 3840x2160.

Builds are reproducible: rebuilding the same config twice yields
byte-identical assets.

The composition as a whole is scaled by `SCALE` at the top of
`build-theme.py`, which drives both the asset pointsizes and the layout
ratios, so it shrinks or grows as one piece rather than drifting apart.

## Four things that will bite you

These were each found by disassembling Plymouth, and each one silently
produced a wrong screen before it was understood.

**1. `Image.Scale` is nearest-neighbour.** `ply_pixel_buffer_resize` contains
exactly two `mulsd` — the x/y step ratios — and no per-pixel blending at all.
Scaling antialiased artwork visibly destroys it. Every asset here is rendered
at its exact final pixel size; the only images scaled at runtime are
flat-colour tiles, where that sampling is lossless.

**2. `DeviceScale=1` is mandatory.** `ply_guess_device_scale` computes
`DPI = width*254/(10*(width_mm+1))` and picks device scale 2 above 96 DPI.
A 2880x1800 panel measuring 310x200 mm is 235 DPI, so Plymouth would hand the
theme a 1440x900 logical window and upscale every image 2x — with the sampler
above. plymouthd reads no `conf.d`, so the installer edits
`/etc/plymouth/plymouthd.conf` in place. That file belongs to the `plymouth`
package but is in its backup array, so the setting survives upgrades and you
get a `.pacnew` instead.

**3. A bare assignment inside a function writes through to a global of the
same name.** If the name is not already a global it stays local to the call;
function parameters are always local. This made the entire ambient field
invisible once glyph creation moved into a helper, because the helper wrote to
a hash that had never been assigned at top level and was discarded on return.
Arrays are pre-declared at top level for exactly this reason.

**4. Plymouth never says "wrong password".** plymouthd has one
`update_display()` that picks display_password / display_normal from its
pending-request queue, and `plymouth ask-for-password --command=...` simply
re-issues the request when the command exits non-zero. So a correct key gives
`password -> normal` and a wrong one gives `password -> normal -> password`.
The theme cannot decide at Enter time; it sits in a verifying state and
resolves later.

What tells it the key was accepted is that **`ask-for-password` pauses boot
progress while it asks** (its `--dont-pause-progress` flag turns that off, and
the encrypt hook does not pass it). While paused, `ply_progress` freezes both
the percentage and the elapsed time, yet plymouthd keeps calling the theme
every 33 ms with those frozen values. Progress standing still *is* the key
being checked; progress moving again *is* the key having been accepted. Two
earlier attempts — counting frames, then reading `ply_progress_get_time` —
both failed, because argon2 starves the frame timer and the pause freezes that
clock. For reference this machine's header is argon2id with 9 iterations over
1 GiB and takes **15.8 s** to reject a key.

## The bootloader menu

Limine's menu is not a graphics engine. It is a character grid with a 16-colour
palette and one full-screen wallpaper behind it, and three of its properties
decide the whole design:

**It cannot draw antialiased text.** `term_font` wants a CP437 bitmap and
Limine "assumes all fonts are of width 8" — one byte per glyph row. The
terminal is a 1-bit blitter. There is no smooth-text setting at any resolution,
which is why the theme keeps Limine's built-in font and puts no artwork behind
the text: with a bare ground, the 8-pixel limit has nothing to spoil.

**`term_background` is `TTRRGGBB` where `TT=00` is opaque and `TT=FF` is fully
transparent** — the reverse of the usual ARGB convention. `colour_blend()` in
`common/lib/gterm.c` computes `alpha = 255 - A(fg)`, and Limine's own default
`0x00000000` is opaque black. The theme uses `FF000000` so the wallpaper shows
through every cell.

**The menu centres itself.** `(cols - max_tree_len - 3)/2` and
`(rows - max_tree_height)/2` in `common/menu.c`. There is nothing to configure
and nothing that can override it. The `┌─┤ … ├─┐` frame you will find in the
binary belongs to the *editor*, not the menu — entries float, and
`interface_branding` gets its own centred row.

**Do not derive the text layer from the panel size.** `/sys/class/drm` reports
the *panel's* mode, but the menu runs at whatever GOP mode Limine picks when
`interface_resolution` is unset, and the two need not match. Computing
`term_font_scale` from the detected resolution produced text far too large on
real hardware while looking correct in a QEMU screenshot — QEMU's resolution is
given on the command line, so that check was circular. The menu's own mode
cannot be read back from a booted system either. The theme therefore sets
neither `term_font_scale` nor `term_margin` and keeps Limine's defaults, as the
stock Omarchy config did. Only the wallpaper is per-resolution, and it is
`stretched`.

One capability left unused: `wallpaper` may appear several times and Limine
picks one at random per boot. With a bare ground there is nothing to vary, but
it is the only route to variation on this screen.

### Previewing it

Unlike Plymouth, this screen **can** be seen before you commit it — Limine is
an ordinary EFI binary and boots in a VM. `tools/README.md` has the recipe.
It verifies composition, palette, transparency, brackets and that the config
parses; it cannot tell you which GOP mode real firmware will pick.

## Verifying a change without rebooting

See `tools/README.md`. Short version: `plyparse` runs Plymouth's real parser,
`plyrun` actually executes the theme script against stubs and reads its globals
back, and both should be pointed at the script unpacked from the built boot
image rather than the copy in `/usr/share`.

**Never start `plymouthd` from a running session** to preview the theme. It
grabs the console regardless of renderer and leaves the machine with no
working keyboard.

## Layout

```
build-theme.py                  generates every Plymouth asset, the script and the metadata
build-limine.py                 generates the Limine wallpaper and config block
nierconf.py                     one config loader for both, with validation
theme.conf                      installed as /etc/omarchy-plymouth-nier.conf
omarchy-nier-reconfigure        regenerates everything after a config change
limine-splice.sh                the limine.conf splice, shared by all three installers
aur/                            AUR-flavoured PKGBUILD and .SRCINFO, plus sync.sh
CLAUDE.md                       working notes: the traps, and how to verify a change
docs/                           design specs
PKGBUILD                        Arch package; builds assets at package time
omarchy-plymouth-nier.install   pacman scriptlet: DeviceScale, set-default-theme,
                                mkinitcpio, and the limine.conf splice
install.sh                      same thing without pacman; sources the scriptlet
                                so the two paths cannot drift apart
tools/                          plyparse, plyrun, assertions, HTML previews
```

## License

MIT.
