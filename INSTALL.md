# Installing

Two independent packages. Install either, or both.

| Package | What it touches | Depends on your panel? |
|---|---|---|
| `omarchy-plymouth-nier` | Limine menu, LUKS prompt, shutdown screen | **Yes** |
| `omarchy-nier-themes` | Desktop: Nier Black, Flexoki Light Alt | No |

## Quick start

```bash
git clone https://github.com/Willi005/omarchy-plymouth-nier
cd omarchy-plymouth-nier

makepkg -si                        # boot chain: Limine, LUKS, shutdown
cd desktop-themes && makepkg -si   # desktop: the two themes
```

That's it. `makepkg -si` installs its own build dependencies and rasterises the
artwork for **this machine's panel** — no separate setup step, and no need to
pre-install anything. You'll be asked for your sudo password a couple of times.

Why build from source rather than grab the prebuilt package: see
[Why build rather than install the binary](#why-build-rather-than-install-the-binary)
below. Short version — it sidesteps the one thing that can go wrong.

## Match another machine's config

The whole boot theme is one file. If you already have it configured elsewhere,
copy it over instead of editing by hand:

```bash
sudo cp /path/to/omarchy-plymouth-nier.conf /etc/
sudo omarchy-nier-reconfigure
```

Otherwise, the package installs with the **black** palette active. To switch
to a light one, comment the `BLACK` block in `/etc/omarchy-plymouth-nier.conf`
and uncomment `YORHA LIGHT` or `FLEXOKI LIGHT`:

```bash
sudo $EDITOR /etc/omarchy-plymouth-nier.conf
sudo omarchy-nier-reconfigure --dry-run    # see what would change
sudo omarchy-nier-reconfigure              # apply it
```

Full key reference: [README.md § Configuring it](README.md#configuring-it).
Quick cheat sheet: [CUSTOMIZING.md](CUSTOMIZING.md).

## Pick a desktop theme

```bash
omarchy theme set "Nier Black"          # or "Flexoki Light Alt"
```

`omarchy-nier-themes status` shows what got linked into
`~/.config/omarchy/themes/`.

## Reboot

The Limine menu themes immediately. The LUKS prompt and the shutdown screen
only render on a **real power cycle** — suspend doesn't trigger either: the
disk stays decrypted and mounted, so there is no LUKS prompt to show, and no
shutdown sequence runs.

## What you'll see

- **Limine menu**, themed at power-on.
- **LUKS prompt**: password field, a field of ambient katakana, a greeting
  with your name. After the correct key, a progress line along the bottom.
- **On shutdown**: a farewell message.
- **On the desktop**: terminal, btop, the browser and the file manager
  following the palette.

The greeting name comes from your account's GECOS field. If that's empty or
wrong on this machine, set it explicitly with `NAME=` in the config.

## Verify it worked

Short version — full checklist in [VERIFY.md](VERIFY.md):

```bash
cat /usr/share/omarchy-plymouth-nier/built-for   # should say THIS machine's resolution
sudo grep -c '>>> omarchy-nier' /boot/limine.conf   # should be 1
omarchy-nier-themes status                       # two symlinks, two hooks, gtk.css
```

## Why build rather than install the binary

The boot package **bakes the artwork into PNGs sized for one exact panel**,
because Plymouth's only scaler is nearest-neighbour and destroys anything it
resizes (see [README.md](README.md#five-things-that-will-bite-you), point 1).
The prebuilt package in the pacman repository below is built for one specific
machine's panel.

On a different resolution, that package still works, but the installer has to
notice the mismatch and regenerate on the spot — which needs the build tools
already installed, and only warns if they aren't. Building from source sidesteps
that: `makepkg` installs those tools itself and generates for the right panel
the first time, every time.

The desktop themes are pure data and don't depend on the screen at all, so this
doesn't apply to them — building or installing the binary is equivalent there.

## Get updates with `pacman -Syu` instead

Only worth doing if you don't want to re-run `makepkg` for every update. Once
per machine:

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
sudo pacman -Sy
sudo pacman -S omarchy-plymouth-nier omarchy-nier-themes
```

Same caveat as above applies to updates of the boot package: if this machine's
panel differs from the one the release was built for, the scriptlet needs
`python`, `imagemagick`, `fontconfig`, `noto-fonts-cjk` and
`ttf-jetbrains-mono-nerd` already installed to regenerate automatically.

**Not on the AUR yet** — see [README.md](README.md#install) for why.

## Without pacman

```bash
sudo ./install.sh
```

Does the same as the boot package's scriptlet without registering anything
with pacman. There's no equivalent for the desktop themes; those are
pacman-only, since the whole point is the symlink trick described in
[desktop-themes/README.md](desktop-themes/README.md).

## Troubleshooting

**The file manager still shows old colours.** GTK apps read their stylesheet
at startup. Close the window and reopen it. This covers GTK4/libadwaita only
(Nautilus and most current GNOME apps) — GTK3 apps stay on stock Adwaita. See
[desktop-themes/README.md § The file manager](desktop-themes/README.md#the-file-manager).

**A theme doesn't show up in `omarchy theme list`.** The linker refuses to
touch a real directory that's already at the target — on purpose, so it never
destroys anything — and says so instead of failing silently:

```bash
omarchy-nier-themes link --force   # moves it aside to ~/.config/omarchy/nier-themes-backup/
```

**A new config key doesn't show up after upgrading.** `theme.conf` is a
`backup=` file, so pacman never overwrites a copy you've edited — it leaves a
`.pacnew` next to it instead. Diff the two and merge by hand:

```bash
diff <(grep -vE '^\s*#|^\s*$' /etc/omarchy-plymouth-nier.conf) \
     <(grep -vE '^\s*#|^\s*$' /etc/omarchy-plymouth-nier.conf.pacnew)
```

**The shutdown screen is just black.** Almost certainly `GOODBYE_FADE` fading
in too slowly for how fast this machine shuts down — see
[CUSTOMIZING.md](CUSTOMIZING.md#the-shutdown-farewell-timing).

**Screen brightness flashes at power-on.** Not something either package fixes
— `systemd-backlight` can't restore your saved brightness until the encrypted
disk is open, which is after the LUKS prompt, not before it. Out of scope by
design; see [README.md](README.md#five-things-that-will-bite-you).

**The theme reverted after `omarchy update`.** See
[README.md, point 5](README.md#five-things-that-will-bite-you).

## Uninstall

```bash
sudo pacman -R omarchy-nier-themes      # removes symlinks, hooks, and the gtk.css
sudo pacman -R omarchy-plymouth-nier    # stock Plymouth theme, image rebuilt, Limine restored
```

The desktop package cleans up its own symlinks and stylesheet in
`pre_remove`. A theme that was active when you remove the package stays
applied — Omarchy copies a theme into its own staging directory the moment
you set it — it's just no longer offered afterward. Full detail in
[README.md § Roll back](README.md#roll-back).
