# Splice the theme's block into the Limine bootloader config.
#
# Sourced by three callers -- the pacman scriptlet, install.sh and
# omarchy-nier-reconfigure -- so there is one implementation and the three
# paths cannot drift apart. It only defines variables and functions, so
# sourcing it has no side effects.
#
# limine.conf is a global header followed by boot entries, every entry
# starting at column 0 with a slash. Only the header is ever rewritten:
# entries belong to limine-entry-tool and limine-snapper-sync.

_share=${_share:-/usr/share/omarchy-plymouth-nier/limine}

_nier_owned='interface_branding|interface_branding_colou?r|interface_help_colou?r|interface_help_colou?r_bright|interface_help_hidden|wallpaper|wallpaper_style|backdrop|term_background|term_foreground|term_background_bright|term_foreground_bright|term_palette|term_palette_bright|term_margin|term_margin_gradient|term_font|term_font_size|term_font_scale|term_font_spacing'

# limine.conf is one global header followed by entries; every entry line starts
# at column 0 with a slash. Splitting there keeps limine-entry-tool's territory
# untouched.
_nier_header() { awk '/^\// { exit } { print }' "$1"; }
_nier_body()   { awk 'f || /^\// { f = 1; print }' "$1"; }

# Drops a previously managed block, every key this theme owns, and -- the part
# a plain grep gets wrong -- the comment lines that introduce those keys, so
# reverting does not leave "# Terminal colors (Tokyo Night palette)" hanging
# over nothing. Comments and blanks are buffered until the next real key
# decides whether they belong to something that survives.
_nier_strip() {
    awk -v owned="$_nier_owned" '
        /^### >>> omarchy-nier >>>/ { skip = 1; next }
        /^### <<< omarchy-nier <<</ { skip = 0; next }
        skip { next }
        /^[[:space:]]*(#|$)/ { buf[++nb] = $0; next }
        {
            key = $0
            sub(/^[[:space:]]*/, "", key)
            sub(/[[:space:]]*:.*$/, "", key)
            if (key ~ "^(" owned ")$") { nb = 0; next }
            for (i = 1; i <= nb; i++) print buf[i]
            nb = 0
            print
        }
        END { for (i = 1; i <= nb; i++) print buf[i] }
    ' | cat -s | awk '{ l[NR] = $0 } NF { last = NR } END {
            for (i = 1; i <= last; i++) print l[i]
        }'
}

# Writes to a temporary file on the same filesystem and renames, so a failure
# halfway through can never leave a half-written bootloader config.
_nier_write() {
    local conf=$1 tmp
    tmp=$(mktemp "$conf.nier.XXXXXX") || return 1
    cat > "$tmp" || { rm -f "$tmp"; return 1; }
    chmod 644 "$tmp" 2>/dev/null || true
    mv -f "$tmp" "$conf"
}

nier_apply() {
    local conf=$1 block=$2 backup="$1.omarchy-nier.bak"
    [ -f "$backup" ] || cp -p "$conf" "$backup" || return 1
    { _nier_header "$conf" | _nier_strip; echo; cat "$block"; echo; \
      _nier_body "$conf"; } \
        | _nier_write "$conf"
}

nier_revert() {
    local conf=$1 backup="$1.omarchy-nier.bak"
    if [ -f "$backup" ]; then
        # Header from the backup, entries from the live file: boot entries may
        # have changed since the theme was applied and must not be rolled back.
        { _nier_header "$backup"; _nier_body "$conf"; } | _nier_write "$conf" \
            && rm -f "$backup"
    else
        { _nier_header "$conf" | _nier_strip; _nier_body "$conf"; } | _nier_write "$conf"
    fi
}

# ESP_PATH from /etc/default/limine wins; otherwise probe the usual mounts.
# limine-entry-tool searches the same list.
_nier_esp() {
    local configured="" candidate
    if [ -r /etc/default/limine ]; then
        configured=$(. /etc/default/limine 2>/dev/null; printf '%s' "$ESP_PATH")
    fi
    for candidate in "$configured" /boot /efi /boot/efi /limine; do
        [ -n "$candidate" ] && [ -f "$candidate/limine.conf" ] && {
            printf '%s' "$candidate"; return 0; }
    done
    return 1
}

# Enrolling embeds a checksum of limine.conf into the Limine binary, and a
# system with it on will refuse to boot after any edit until it is redone.
# It is off by default, but silently skipping this on a system that has it on
# would be the one way this package could stop a machine from booting.
_nier_reenroll() {
    grep -rqs '^[[:space:]]*ENABLE_ENROLL_LIMINE_CONFIG=[\"'"'"']*yes' \
        /etc/default/limine /etc/limine-entry-tool.d/ 2>/dev/null || return 0
    [ -x /usr/bin/limine-enroll-config ] || return 0
    echo ":: re-enrolling the Limine config checksum..."
    /usr/bin/limine-enroll-config || echo ":: WARNING: re-enrolment failed; run limine-enroll-config by hand before rebooting."
}

_apply_limine() {
    local esp conf
    if ! esp=$(_nier_esp); then
        echo ":: WARNING: no limine.conf found on any ESP -- boot menu left alone."
        return 0
    fi
    conf="$esp/limine.conf"
    mkdir -p "$esp/omarchy-nier" || return 0
    # cp rather than install: the ESP is vfat and does not carry unix modes.
    cp -f "$_share/bg.png" "$esp/omarchy-nier/bg.png" || return 0
    if nier_apply "$conf" "$_share/limine-block.conf"; then
        echo ":: themed the Limine boot menu ($conf)"
        _nier_reenroll
    else
        echo ":: WARNING: could not rewrite $conf -- boot menu left alone."
    fi
}

_revert_limine() {
    local esp conf
    esp=$(_nier_esp) || return 0
    conf="$esp/limine.conf"
    nier_revert "$conf" && echo ":: restored the stock Limine boot menu"
    rm -f "$esp/omarchy-nier/bg.png"
    rmdir "$esp/omarchy-nier" 2>/dev/null || true
    _nier_reenroll
}
