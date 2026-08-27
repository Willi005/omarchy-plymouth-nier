#!/usr/bin/env bash
# Fallback installer for systems without pacman. On Arch prefer the package:
#     makepkg -si
#
# Everything this does, the PKGBUILD's scriptlet does too.
set -euo pipefail

THEME=omarchy-minimal
DEST=/usr/share/plymouth/themes/$THEME
SHARE=/usr/share/omarchy-plymouth-nier
CONF=/etc/omarchy-plymouth-nier.conf
PLYCONF=/etc/plymouth/plymouthd.conf
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

[ "$(id -u)" -eq 0 ] || { echo "run as root: sudo $0" >&2; exit 1; }

for cmd in python3 magick plymouth-set-default-theme mkinitcpio; do
    command -v "$cmd" >/dev/null || { echo "missing: $cmd" >&2; exit 1; }
done

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

echo ":: generating assets"
python3 "$HERE/build-theme.py" "$tmp/theme"
python3 "$HERE/build-limine.py" "$tmp/limine"

echo ":: installing to $DEST"
install -dm755 "$DEST"
install -m644 -t "$DEST" "$tmp/theme/"*

echo ":: installing the Limine wallpaper and config block to $SHARE/limine"
install -dm755 "$SHARE/limine"
install -m644 -t "$SHARE/limine" "$tmp/limine/"*
install -m644 "$tmp/theme/built-for" "$SHARE/built-for"
rm -f "$DEST/built-for"

echo ":: installing the generators and omarchy-nier-reconfigure"
install -m644 -t "$SHARE" "$HERE/build-theme.py" "$HERE/build-limine.py" \
    "$HERE/nierconf.py" "$HERE/limine-splice.sh" "$HERE/plymouth-stake.sh"
install -Dm755 "$HERE/omarchy-nier-reconfigure" /usr/bin/omarchy-nier-reconfigure

# An `omarchy update` resets /etc/plymouth/plymouthd.conf to the stock theme,
# so the theme re-stakes its claim from a pacman hook afterwards. This is a
# manual install, but pacman still runs the hooks, so they belong here too.
echo ":: installing the pacman hooks that survive an omarchy update"
install -Dm755 "$HERE/omarchy-nier-stake" \
    /usr/share/libalpm/scripts/omarchy-nier-stake
install -Dm644 "$HERE/85-omarchy-plymouth-nier-claim.hook" \
    /usr/share/libalpm/hooks/85-omarchy-plymouth-nier-claim.hook
install -Dm644 "$HERE/99-omarchy-plymouth-nier-rebuild.hook" \
    /usr/share/libalpm/hooks/99-omarchy-plymouth-nier-rebuild.hook

# Sourced for _ensure_device_scale and _rebuild_boot_image, so a manual
# install and a package install agree on both.
_theme="$THEME"
_conf="$PLYCONF"
# shellcheck source=/dev/null
. "$HERE/plymouth-stake.sh"

# Never clobber a config the user has already edited.
if [ -f "$CONF" ]; then
    echo ":: keeping your existing $CONF"
else
    install -Dm644 "$HERE/theme.conf" "$CONF"
    echo ":: installed $CONF"
fi

echo ":: forcing DeviceScale=1"
plymouth-set-default-theme "$THEME"
_ensure_device_scale

echo ":: rebuilding the boot image"
# Not a bare `mkinitcpio -P`: on a Limine + UKI system there are no presets at
# all and that call fails outright. _rebuild_boot_image picks the right one.
_rebuild_boot_image

echo
echo "Done. Roll back with:"
echo "    sudo plymouth-set-default-theme omarchy && sudo mkinitcpio -P"

# The bootloader menu. The splice lives in one file that the pacman scriptlet
# and omarchy-nier-reconfigure source too, so the three paths cannot drift.
_share="$SHARE/limine"
# shellcheck source=/dev/null
. "$HERE/limine-splice.sh"
_apply_limine

cat <<MSG

:: Done. To change the palette, the glyph density, the name or the boot menu
::       branding, edit $CONF and run:
::
::           sudo omarchy-nier-reconfigure
MSG
