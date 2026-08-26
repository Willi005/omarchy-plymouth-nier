# omarchy-plymouth-nier

A NieR:Automata-flavoured Plymouth theme for [Omarchy](https://omarchy.org):
the screen that asks for the LUKS passphrase at power-on, and the farewell
screen at shutdown.

Bone `#CFC9B0` on near-black. A very dim ステム ghost word breathing behind a
field of katakana that swap on their own timers, a vertical シ ス テ ム column,
HUD corner brackets, a welcome line and a thin segmented password rule. Typed
characters appear as a katakana that cycles briefly and then resolves to a
solid mark. A rejected key tears the screen apart; an accepted one fades
everything away and leaves a single progress line along the bottom edge.

Everything visible is a pre-rendered PNG, so nothing depends on font
resolution inside the initramfs.

## Install

On Arch / Omarchy:

```bash
git clone https://github.com/Willi005/omarchy-plymouth-nier
cd omarchy-plymouth-nier
$EDITOR theme.conf        # at minimum, put your own name in it
makepkg -si
```

That generates the 206 assets, installs them to
`/usr/share/plymouth/themes/omarchy-minimal`, forces `DeviceScale=1`, sets the
default theme and rebuilds the boot image.

If a previous copy was installed by hand, pacman will refuse to overwrite
files it does not own. Take ownership once with:

```bash
makepkg -s
sudo pacman -U --overwrite '/usr/share/plymouth/themes/omarchy-minimal/*' \
    omarchy-plymouth-nier-*.pkg.tar.zst
```

Anywhere else: `sudo ./install.sh`.

## Roll back

```bash
sudo plymouth-set-default-theme omarchy && sudo mkinitcpio -P
```

The stock theme at `/usr/share/plymouth/themes/omarchy/` is never modified.
Removing the package does this for you.

## Making it yours

Edit `theme.conf` and rebuild. Every key also works as an environment
variable, which wins over the file:

| key | default | what it does |
|---|---|---|
| `NAME` | the account's real name, else its login name | `Welcome, <NAME>` and `Goodbye, <NAME>` |
| `RESOLUTION` | `auto` | panel size the assets are rendered for |
| `GHOST_WORD` | `システム` | the large word breathing behind everything |

```bash
PLYMOUTH_NAME="Ada" makepkg -sif
```

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
build-theme.py                  generates every asset, the theme script and the metadata
theme.conf                      name, target resolution, background word
CLAUDE.md                       working notes: the traps, and how to verify a change
PKGBUILD                        Arch package; builds assets at package time
omarchy-plymouth-nier.install   pacman scriptlet: DeviceScale, set-default-theme, mkinitcpio
install.sh                      same thing without pacman
tools/                          plyparse, plyrun, assertions, HTML previews
```

## License

MIT.
