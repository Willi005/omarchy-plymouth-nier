#!/usr/bin/env bash
# Fallback installer for systems without pacman. On Arch prefer the package:
#     makepkg -si
#
# Everything this does, the PKGBUILD's scriptlet does too.
set -euo pipefail

THEME=omarchy-minimal
DEST=/usr/share/plymouth/themes/$THEME
CONF=/etc/plymouth/plymouthd.conf
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

[ "$(id -u)" -eq 0 ] || { echo "run as root: sudo $0" >&2; exit 1; }

for cmd in python3 magick plymouth-set-default-theme mkinitcpio; do
    command -v "$cmd" >/dev/null || { echo "missing: $cmd" >&2; exit 1; }
done

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

echo ":: generating assets"
python3 "$HERE/build-theme.py" "$tmp/theme"

echo ":: installing to $DEST"
install -dm755 "$DEST"
install -m644 -t "$DEST" "$tmp/theme/"*

echo ":: forcing DeviceScale=1"
if [ ! -f "$CONF" ]; then
    printf '[Daemon]\nDeviceScale=1\n' > "$CONF"
elif grep -q '^[[:space:]]*DeviceScale[[:space:]]*=' "$CONF"; then
    sed -i 's/^[[:space:]]*DeviceScale[[:space:]]*=.*/DeviceScale=1/' "$CONF"
elif grep -q '^\[Daemon\]' "$CONF"; then
    sed -i '0,/^\[Daemon\]/s//[Daemon]\nDeviceScale=1/' "$CONF"
else
    printf '[Daemon]\nDeviceScale=1\n' >> "$CONF"
fi

plymouth-set-default-theme "$THEME"

echo ":: rebuilding the boot image"
mkinitcpio -P

echo
echo "Done. Roll back with:"
echo "    sudo plymouth-set-default-theme omarchy && sudo mkinitcpio -P"
