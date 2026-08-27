#!/bin/bash
# Exercises plymouth-stake.sh against a scratch tree: no root, no real
# /etc/plymouth, no rebuild. Covers the decisions that decide whether the
# theme survives an `omarchy update` -- everything except the two privileged
# calls (plymouth-set-default-theme, the rebuild), which are stubbed.
set -u
HERE=$(cd "$(dirname "$0")/.." && pwd)
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then pass=$((pass+1)); printf '  ok   %-46s %s\n' "$1" "$2";
       else fail=$((fail+1)); printf '  FAIL %-46s got %s want %s\n' "$1" "$2" "$3"; fi; }

mkdir -p "$T/themes/omarchy-minimal" "$T/boot" "$T/efi"
_theme=omarchy-minimal
_conf="$T/plymouthd.conf"
_stake_boot_dirs="$T/boot $T/efi"
. "$HERE/plymouth-stake.sh"
_stake_stamp="$T/stamp"
# The real check looks in /usr/share/plymouth/themes; point it at the scratch
# tree by overriding the one line that reads it.
_stake_is_intact() {
    [ -d "$T/themes/$_theme" ] || return 0
    [ -f "$_conf" ] || return 1
    grep -q "^[[:space:]]*Theme[[:space:]]*=[[:space:]]*$_theme[[:space:]]*$" "$_conf" || return 1
    grep -q '^[[:space:]]*DeviceScale[[:space:]]*=[[:space:]]*1[[:space:]]*$' "$_conf" || return 1
    return 0
}
yn() { if "$@"; then echo yes; else echo no; fi; }

echo "-- _stake_is_intact"
rm -f "$_conf";                                   ck "no config at all"            "$(yn _stake_is_intact)" no
printf '[Daemon]\nTheme=omarchy\n' > "$_conf";    ck "what omarchy update leaves"  "$(yn _stake_is_intact)" no
printf '[Daemon]\nTheme=omarchy-minimal\n' > "$_conf"
                                                  ck "right theme, no DeviceScale" "$(yn _stake_is_intact)" no
printf '[Daemon]\nDeviceScale=1\nTheme=omarchy\n' > "$_conf"
                                                  ck "DeviceScale but stock theme" "$(yn _stake_is_intact)" no
printf '[Daemon]\nDeviceScale=1\nTheme=omarchy-minimal\n' > "$_conf"
                                                  ck "fully staked"                "$(yn _stake_is_intact)" yes
printf '[Daemon]\nDeviceScale=2\nTheme=omarchy-minimal\n' > "$_conf"
                                                  ck "DeviceScale=2 is not intact" "$(yn _stake_is_intact)" no
printf '[Daemon]\nTheme = omarchy-minimal \nDeviceScale = 1\n' > "$_conf"
                                                  ck "tolerates surrounding space" "$(yn _stake_is_intact)" yes
printf '[Daemon]\nTheme=omarchy-minimal-x\nDeviceScale=1\n' > "$_conf"
                                                  ck "no substring false positive" "$(yn _stake_is_intact)" no
rm -rf "$T/themes/omarchy-minimal"
printf '[Daemon]\nTheme=omarchy\n' > "$_conf";    ck "theme uninstalled: hands off" "$(yn _stake_is_intact)" yes
mkdir -p "$T/themes/omarchy-minimal"

echo "-- _ensure_device_scale"
printf '[Daemon]\nTheme=omarchy\n' > "$_conf"; _ensure_device_scale
        ck "inserts under [Daemon]" "$(grep -c '^DeviceScale=1$' "$_conf")" 1
        ck "keeps the Theme line"   "$(grep -c '^Theme=omarchy$' "$_conf")" 1
printf 'DeviceScale=2\n' > "$_conf"; _ensure_device_scale
        ck "rewrites a wrong value" "$(grep -c '^DeviceScale=1$' "$_conf")" 1
printf 'Foo=bar\n' > "$_conf"; _ensure_device_scale
        ck "appends when no [Daemon]" "$(grep -c '^DeviceScale=1$' "$_conf")" 1
rm -f "$_conf"; _ensure_device_scale
        ck "creates a missing file" "$(grep -c '^DeviceScale=1$' "$_conf")" 1
_ensure_device_scale; _ensure_device_scale
        ck "idempotent, no duplicates" "$(grep -c '^DeviceScale=1$' "$_conf")" 1

echo "-- nier_stake_rebuild"
rebuilt=0
_rebuild_boot_image() { rebuilt=$((rebuilt+1)); }
rm -f "$_stake_stamp"; rebuilt=0; nier_stake_rebuild >/dev/null
        ck "no stamp: does nothing" "$rebuilt" 0
: > "$_stake_stamp"; rebuilt=0; nier_stake_rebuild >/dev/null
        ck "stamp, stale image: rebuilds" "$rebuilt" 1
        ck "  and clears the stamp" "$(yn test -f "$_stake_stamp")" no
: > "$_stake_stamp"; sleep 0.02; touch "$T/efi/omarchy_linux.efi"
rebuilt=0; nier_stake_rebuild >/dev/null
        ck "image newer: skips rebuild" "$rebuilt" 0
        ck "  and clears the stamp" "$(yn test -f "$_stake_stamp")" no
touch -d '2000-01-01' "$T/efi/omarchy_linux.efi"
: > "$_stake_stamp"; rebuilt=0; nier_stake_rebuild >/dev/null
        ck "image older: rebuilds" "$rebuilt" 1
: > "$_stake_stamp"; sleep 0.02; touch "$T/boot/initramfs-linux.img"
rebuilt=0; nier_stake_rebuild >/dev/null
        ck "classic initramfs counts too" "$rebuilt" 0

echo "-- nier_stake_claim"
plymouth-set-default-theme() { printf '[Daemon]\nTheme=%s\n' "$1" > "$_conf"; }
printf '[Daemon]\nTheme=omarchy\n' > "$_conf"; rm -f "$_stake_stamp"
nier_stake_claim >/dev/null
        ck "repairs a reset config" "$(yn _stake_is_intact)" yes
        ck "  and leaves a stamp"   "$(yn test -f "$_stake_stamp")" yes
rm -f "$_stake_stamp"; nier_stake_claim >/dev/null
        ck "intact: no stamp, no work" "$(yn test -f "$_stake_stamp")" no

echo
echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
