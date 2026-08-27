"""Shared configuration for the NieR theme generators.

Both build-theme.py and build-limine.py read the same file through this module
so the two screens cannot disagree about a colour or a name. Values come from
/etc/omarchy-plymouth-nier.conf when it exists, otherwise from theme.conf next
to the generators, and an environment variable of the same name prefixed NIER_
beats both. PLYMOUTH_ is still accepted so older invocations keep working.

Validation fails loudly and names the offending key: a boot theme that renders
with a silently substituted colour is worse than one that refuses to build.
"""

import glob
import os
import pwd
import re
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
SYSTEM_CONF = Path("/etc/omarchy-plymouth-nier.conf")
LOCAL_CONF = HERE / "theme.conf"

HEX = re.compile(r"^#(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$")

DEFAULTS = {
    # palette
    "BONE": "#CFC9B0", "DIM": "#4A4638", "CHROME": "#55503F",
    "RUST": "#B0563F", "GROUND": "#050505",
    # field
    "GLYPHS": "20", "STACKS": "6", "STACK_MIN": "2", "STACK_MAX": "6",
    "ALPHABET": "ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ",
    "COLUMN": "", "GHOST_WORD": "システム", "GHOST_MAX_WIDTH": "0.62",
    "FIELD": "on", "KEEPOUT": "0.035",
    # composition
    "SCALE": "0.70", "NAME": "", "WELCOME": "Welcome, {name}",
    "GOODBYE": "Goodbye, {name}", "HINT": "TYPE A PASSWORD  ·  ENTER TO UNLOCK",
    "RESOLUTION": "auto", "BRANDING": "OMARCHY",
    "BRACKET_INSET": "0.030", "BRACKET_ARM": "0.065", "MENU_HELP": "on",
}

COLOURS = ("BONE", "DIM", "CHROME", "RUST", "GROUND")
COUNTS = ("GLYPHS", "STACKS", "STACK_MIN", "STACK_MAX")
# key -> (low, high, clamp?). Clamped values degrade gradually; the rest are
# refused, because outside their range they produce nonsense rather than
# something ugly.
FRACTIONS = {
    "GHOST_MAX_WIDTH": (0.05, 1.0, False),
    "SCALE": (0.2, 2.0, True),
    "BRACKET_INSET": (0.0, 0.2, False),
    "BRACKET_ARM": (0.0, 0.5, False),
    "KEEPOUT": (0.0, 0.25, False),
}
FLAGS = ("FIELD", "MENU_HELP")


def _die(msg):
    sys.exit(f"config error: {msg}")


def _read_file(path):
    out = {}
    if not path.exists():
        return out
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            _die(f"{path}:{n}: expected KEY=value, got {line!r}")
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip()
    return out


def _account_name():
    """Real name if the account has one, otherwise the login name.

    Prefers the invoking user over the effective one. Every path that renders
    the artwork runs privileged -- the pacman scriptlet, omarchy-nier-reconfigure
    -- so reading the effective uid would greet an empty NAME with "Welcome,
    Root", which is nobody's configuration.
    """
    uid = os.getuid()
    if uid == 0:
        for var in ("PKEXEC_UID", "SUDO_UID"):
            value = os.environ.get(var, "")
            if value.isdigit():
                uid = int(value)
                break
    try:
        entry = pwd.getpwuid(uid)
    except KeyError:
        return "there"
    gecos = (entry.pw_gecos or "").split(",")[0].strip()
    return gecos.split()[0] if gecos else entry.pw_name.capitalize()


def _detect_resolution():
    """Preferred mode of the largest connected display, straight from DRM.

    Readable with no session and no X/Wayland connection, which matters
    because this runs from a package build and from a pacman scriptlet.
    """
    best = None
    for path in sorted(glob.glob("/sys/class/drm/*/modes")):
        try:
            first = open(path).readline().strip()
        except OSError:
            continue
        try:
            w, h = (int(n) for n in first.split("x", 1))
        except ValueError:
            continue
        if best is None or w * h > best[0] * best[1]:
            best = (w, h)
    return best


class Conf(dict):
    """Validated configuration. Attribute access returns typed values."""

    def colour(self, key):
        return self[key]

    def count(self, key):
        return int(self[key])

    def frac(self, key):
        return float(self[key])

    def flag(self, key):
        return self[key] == "on"

    @property
    def resolution(self):
        want = self["RESOLUTION"].lower()
        if want != "auto":
            return tuple(int(n) for n in want.split("x", 1))
        found = _detect_resolution()
        if found:
            return found
        print("warning: no connected display found in /sys/class/drm; assuming "
              "1920x1080. Set RESOLUTION if that is wrong.", file=sys.stderr)
        return 1920, 1080

    @property
    def column(self):
        """The vertical katakana column at the right of the boot screen.

        Empty COLUMN means "derive it from GHOST_WORD": the fullwidth word is
        mapped back to halfwidth through the alphabet with NFKC, so システム
        yields ｼｽﾃﾑ and the same word appears twice, once large and once
        vertical. Anything that does not map cleanly falls back to the first
        four letters of the alphabet rather than rendering tofu.
        """
        explicit = self["COLUMN"]
        if explicit:
            return explicit
        alphabet = self["ALPHABET"]
        full_to_half = {unicodedata.normalize("NFKC", c): c for c in alphabet}
        mapped = [full_to_half.get(c) for c in self["GHOST_WORD"]]
        if mapped and all(mapped):
            return "".join(mapped)
        return alphabet[:4]


def load():
    values = dict(DEFAULTS)

    # NIER_CONF names the file outright. Without it the installed config wins
    # whenever it exists, which is right for a reconfigure on a live machine
    # and wrong for anything else: building a package for other people, or
    # running a test that means to exercise the defaults, would silently
    # inherit this machine's edits and produce a result nobody asked for.
    override = os.environ.get("NIER_CONF")
    if override:
        source = Path(override)
        if not source.exists():
            _die(f"NIER_CONF={override!r} does not exist")
    else:
        source = SYSTEM_CONF if SYSTEM_CONF.exists() else LOCAL_CONF
    from_file = _read_file(source)

    for key, value in from_file.items():
        if key not in DEFAULTS:
            print(f"warning: {source}: unknown key {key!r}, ignored. A config "
                  "from a newer version is not an error.", file=sys.stderr)
            continue
        values[key] = value

    for key in DEFAULTS:
        env = os.environ.get("NIER_" + key) or os.environ.get("PLYMOUTH_" + key)
        if env:
            values[key] = env

    # ---- validation ----------------------------------------------------
    for key in COLOURS:
        if not HEX.match(values[key]):
            _die(f"{key}={values[key]!r} is not #RRGGBB or #RGB")
        if len(values[key]) == 4:            # expand #abc to #aabbcc
            values[key] = "#" + "".join(c * 2 for c in values[key][1:])

    for key in COUNTS:
        if not values[key].lstrip("-").isdigit() or int(values[key]) < 0:
            _die(f"{key}={values[key]!r} must be a non-negative whole number")
    if int(values["STACK_MIN"]) > int(values["STACK_MAX"]):
        _die(f"STACK_MIN ({values['STACK_MIN']}) is greater than "
             f"STACK_MAX ({values['STACK_MAX']})")

    for key, (low, high, clamp) in FRACTIONS.items():
        try:
            f = float(values[key])
        except ValueError:
            _die(f"{key}={values[key]!r} must be a number")
        if not low <= f <= high:
            if not clamp:
                _die(f"{key}={f} is outside {low}..{high}")
            f = min(high, max(low, f))
            print(f"warning: {key} clamped to {f}", file=sys.stderr)
        values[key] = str(f)

    for key in FLAGS:
        values[key] = values[key].strip().lower()
        if values[key] not in ("on", "off"):
            _die(f"{key}={values[key]!r} must be on or off")

    if not values["ALPHABET"]:
        _die("ALPHABET is empty; there would be no glyphs to draw")
    if "{name}" not in values["WELCOME"] and "{name}" not in values["GOODBYE"]:
        print("warning: neither WELCOME nor GOODBYE uses {name}; NAME will not "
              "appear on screen.", file=sys.stderr)

    values["_NAME_FROM_FILE"] = values["NAME"]
    values["NAME"] = values["NAME"] or _account_name()
    conf = Conf(values)
    conf.source = source
    return conf


def fingerprint(conf):
    """A stable digest of the settings the artwork was actually rendered with.

    A prebuilt package carries one machine's answers baked into PNGs, and the
    installer already notices when the panel differs. It could not notice when
    the *config* differed, so upgrading to a package built from the defaults
    silently replaced a customised field with the stock one. Recording this
    next to the resolution closes that: same version, different settings, and
    the scriptlet regenerates instead of overwriting.

    Derived from the resolved values rather than the file, so a comment, a
    reordering or a #abc/#aabbcc rewrite does not read as a change.
    """
    import hashlib
    keys = sorted(k for k in conf if k in DEFAULTS)
    values = dict(conf)
    # NAME is the one value that is derived rather than read when the file
    # leaves it blank, and what it derives to depends on who is running. The
    # fingerprint has to mean "these settings", not "these settings as seen by
    # this user", so it uses what the file actually said.
    values["NAME"] = conf.get("_NAME_FROM_FILE", conf["NAME"])
    blob = "\n".join(f"{k}={values[k]}" for k in keys)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]
