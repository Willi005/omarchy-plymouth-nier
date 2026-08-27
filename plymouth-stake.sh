# Keep Plymouth pointed at this theme, and put it back when something takes it.
#
# Sourced by the pacman scriptlet, by install.sh and by the two pacman hooks,
# so the rules for what /etc/plymouth/plymouthd.conf must say live in one
# place. It only defines variables and functions: sourcing has no side effects.
#
# Why this file exists
# --------------------
# omarchy-settings ships an "etc-overrides" mechanism whose post_install and
# post_upgrade scriptlet runs an unconditional
#
#     cp -f /usr/share/omarchy/etc-overrides/plymouth-plymouthd.conf \
#           /etc/plymouth/plymouthd.conf
#
# and its own comment is explicit about the consequence: "these cp -f's are
# intentionally destructive on every install/upgrade [...] Users who customize
# /etc/plymouth/plymouthd.conf (theme switch) WILL have their changes reset to
# Omarchy defaults each time omarchy-settings is upgraded."
#
# That override file is two lines, [Daemon] and Theme=omarchy. So every
# `omarchy update` that bumps omarchy-settings hands the LUKS prompt and the
# shutdown screen back to the stock theme AND drops DeviceScale=1, and the
# initramfs rebuild later in the same transaction bakes it in. Nothing warns
# about it -- the screens simply revert on the next boot.
#
# The bootloader menu survives that, which is the tell: it is spliced into
# limine.conf on the ESP, a file the override never touches.

_theme=${_theme:-omarchy-minimal}
_conf=${_conf:-/etc/plymouth/plymouthd.conf}

# Written by nier_stake_claim when it had to repair the config, read by
# nier_stake_rebuild to decide whether the boot image still needs rebuilding.
# /run is a tmpfs, so a stamp can never survive into a later boot and be
# mistaken for a fresh one.
_stake_stamp=/run/omarchy-plymouth-nier.staked

# Where a rebuilt boot image lands. Overridable so the rebuild decision can be
# exercised against a scratch tree instead of the real ESP.
_stake_boot_dirs=${_stake_boot_dirs:-"/boot /efi"}

# DeviceScale=1 is not cosmetic. Plymouth guesses a HiDPI device scale from
# DPI = width*254/(10*(width_mm+1)) and picks 2 above 96 DPI. On a 2880x1800
# 310x200mm panel that is 235 DPI, so it would halve the logical window to
# 1440x900 and upscale every image 2x with the same nearest-neighbour sampler
# used by Image.Scale -- the whole composition twice its intended size and
# visibly destroyed. plymouthd reads no conf.d, and this file belongs to the
# plymouth package, so it is edited in place rather than shipped.
_ensure_device_scale() {
    if [ ! -f "$_conf" ]; then
        printf '[Daemon]\nDeviceScale=1\n' > "$_conf"
        return
    fi
    if grep -q '^[[:space:]]*DeviceScale[[:space:]]*=' "$_conf"; then
        sed -i 's/^[[:space:]]*DeviceScale[[:space:]]*=.*/DeviceScale=1/' "$_conf"
    elif grep -q '^\[Daemon\]' "$_conf"; then
        sed -i '0,/^\[Daemon\]/s//[Daemon]\nDeviceScale=1/' "$_conf"
    else
        printf '[Daemon]\nDeviceScale=1\n' >> "$_conf"
    fi
}

# True when the config already names this theme and carries DeviceScale=1.
# Both are checked, because the override drops the second even in the case
# where a user had already pointed Theme back at us by hand.
_stake_is_intact() {
    [ -d "/usr/share/plymouth/themes/$_theme" ] || return 0
    [ -f "$_conf" ] || return 1
    grep -q "^[[:space:]]*Theme[[:space:]]*=[[:space:]]*$_theme[[:space:]]*$" "$_conf" || return 1
    grep -q '^[[:space:]]*DeviceScale[[:space:]]*=[[:space:]]*1[[:space:]]*$' "$_conf" || return 1
    return 0
}

# How the boot image is rebuilt depends on the bootloader setup, and getting
# this wrong leaves the theme installed but never shown.
#
# On a Limine + Unified Kernel Image system there are no mkinitcpio presets at
# all: /etc/mkinitcpio.d is empty and `mkinitcpio -P` fails outright with "No
# presets found". Worse, the mkinitcpio on PATH there is an interactive
# wrapper from limine-mkinitcpio-hook that prompts before doing anything --
# never acceptable from a scriptlet -- and a scriptlet's PATH does not include
# /usr/local/bin anyway, so it would silently hit the real binary and fail.
_rebuild_boot_image() {
    if [ -x /usr/bin/limine-mkinitcpio ]; then
        echo ":: rebuilding the boot image (limine-mkinitcpio)..."
        /usr/bin/limine-mkinitcpio
    elif ls /etc/mkinitcpio.d/*.preset >/dev/null 2>&1; then
        echo ":: rebuilding the boot image (mkinitcpio -P)..."
        /usr/bin/mkinitcpio -P
    else
        cat <<'WARN'
:: WARNING: could not work out how to rebuild the boot image.
::          The theme is installed and set as the default, but the passphrase
::          prompt will keep using the old one until the initramfs is
::          regenerated. Run whatever your bootloader needs.
WARN
    fi
}

# ---------------------------------------------------------------------------
# The two halves of the pacman hook.
#
# They are split because the repair has to happen BEFORE the initramfs is
# rebuilt and the rebuild decision has to happen AFTER. pacman runs
# PostTransaction hooks in filename order, so 85- lands ahead of
# 90-mkinitcpio-install.hook and 99- behind it.

# Repair the config if something reset it, and record that we did.
nier_stake_claim() {
    _stake_is_intact && return 0

    echo ":: /etc/plymouth/plymouthd.conf was reset; restoring the $_theme theme"
    plymouth-set-default-theme "$_theme" || return 1
    _ensure_device_scale
    : > "$_stake_stamp" 2>/dev/null || true
}

# Rebuild only if nothing else in this transaction already did it. A rebuild
# writes the boot image, so a boot image newer than the stamp means
# 90-mkinitcpio-install.hook ran after the repair and already picked the theme
# up; rebuilding again would cost a minute for an identical result.
nier_stake_rebuild() {
    [ -f "$_stake_stamp" ] || return 0

    # The stamp is the -newer reference, so it has to outlive the test.
    if _stake_boot_image_is_current; then
        rm -f "$_stake_stamp"
        echo ":: the boot image was already rebuilt in this transaction"
        return 0
    fi
    rm -f "$_stake_stamp"
    _rebuild_boot_image
}

# Newest boot image wins: a UKI on the ESP, or a classic initramfs in /boot.
# Unreadable or absent means "assume stale" -- a needless rebuild is a minute
# wasted, a skipped one is a reverted boot screen.
_stake_boot_image_is_current() {
    [ -f "$_stake_stamp" ] || return 1
    # shellcheck disable=SC2086 -- deliberately word-split into paths
    find $_stake_boot_dirs -xdev \
         \( -name '*.efi' -o -name 'initramfs-*.img' \) \
         -newer "$_stake_stamp" -print -quit 2>/dev/null | grep -q .
}
