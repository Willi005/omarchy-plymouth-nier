# Customizing

Quick reference for the handful of things people actually change. The
exhaustive key-by-key docs are in
[README.md § Configuring it](README.md#configuring-it); this is the cheat
sheet.

Every change to the boot theme needs a rebuild — nothing takes effect on its
own, because every value is baked into a pre-rendered image:

```bash
sudo $EDITOR /etc/omarchy-plymouth-nier.conf
sudo omarchy-nier-reconfigure
```

## Switch the palette

`/etc/omarchy-plymouth-nier.conf` ships four palette blocks. Exactly one
should be uncommented — comment the active one, uncomment the one you want:

```
# --- BLACK ------------------------------------------------------- ACTIVE ---
BONE=#CFC9B0
...
# --- FLEXOKI LIGHT ---------------------------------------------------------
# BONE=#100F0F
...
```

Preview any of them first without touching your config, in a browser:
`tools/preview-arranque.html` (LUKS prompt) and `tools/preview-apagado.html`
(shutdown) both have a palette picker.

## The progress bar's colour and thickness

```
PROGRESS=#CFC9B0
PROGRESS_HEIGHT=2
```

The bar draws at 0.75 opacity, so the colour you see is a blend with
`GROUND`, not the raw value — check the *composited* contrast, not the
swatch. On a light palette, 2px reads as a faint tint rather than a bar;
the shipped light blocks raise `PROGRESS_HEIGHT` to 6.

## The shutdown farewell timing

```
GOODBYE_FADE=0.25
```

Seconds for the farewell message to fade in. There's no universally correct
value — it depends on how long your machine's screen stays alive after the
shutdown splash appears. A laptop that shuts down slowly can use a slow fade;
a desktop that cuts the monitor signal in under a second needs a fast one, or
the farewell never finishes appearing before the screen goes dark. If yours
shows nothing but black on shutdown, this is almost certainly why — try
`GOODBYE_FADE=0` first, which shows it at full opacity from the first frame.

## The greeting name and text

```
NAME=
WELCOME=Welcome, {name}
GOODBYE=Goodbye, {name}
```

Empty `NAME` derives it from your account's real name (GECOS field), falling
back to your login name. Set it explicitly if that's wrong, or if you're
building a package for someone else.

## Try something without saving it

Every key also works as an environment variable, prefixed `NIER_`, which
wins over the file for that one run:

```bash
NIER_FIELD=off NIER_GOODBYE_FADE=0 sudo omarchy-nier-reconfigure --dry-run
```

## The desktop themes' colours and icons

Nier Black and Flexoki Light Alt (`desktop-themes/themes/`) are ordinary
Omarchy themes — edit `colors.toml` the way you would for any Omarchy theme,
then re-apply it:

```bash
omarchy theme set "Nier Black"
```

Two things specific to these themes, both generated rather than hand-edited:

```bash
cd desktop-themes
python3 build-gtk.py       # regenerate gtk.css from colors.toml
python3 build-previews.py  # regenerate preview.png (needs chromium or brave)
```

`icons.theme` picks the desktop's folder icon colour (`Yaru-wartybrown` on
both, chosen by measuring against each theme's accent — see
[desktop-themes/README.md § The file manager](desktop-themes/README.md#the-file-manager)).
If you change a theme's accent significantly, it's worth re-measuring which
Yaru variant is closest rather than assuming the old pick still fits.

If you edited a live install rather than the git checkout, rebuild the
package afterward so the change survives an upgrade:

```bash
cd desktop-themes && makepkg -si
```

## Full reference

- [README.md § Configuring it](README.md#configuring-it) — every key, with
  the reasoning behind defaults and contrast ratios
- [desktop-themes/README.md](desktop-themes/README.md) — why the desktop
  package is structured the way it is
- `tools/preview-arranque.html`, `preview-apagado.html`,
  `preview-bootloader.html` — interactive palette previews, no rebuild needed
