# Configurable theme + distribution — design

Date: 2026-08-27. Status: approved, implementing.

## Goal

Two things the theme needs before anyone but its author can use it: a
configuration surface wider than "your name and the Japanese word", and a way
to install it that is not "clone this and read the README".

## Distribution: the AUR is frozen

The obvious channel is unavailable. Arch disabled new AUR registrations in June
2026 after ~1,500 packages were hit by a malware campaign, reopened on 13 July,
and **paused all AUR pushes on 1 August** after a third wave; package adoption
was disabled on 30 July. Only already-verified maintainers can push. Sources:
The Register 2026-06-15, Linuxiac, omid.dev 2026-08-10.

So the plan is three channels, in order of how much trust each asks for:

1. **`git clone && makepkg -si`** — the primary path, and the standard Arch
   idiom. Works today, asks for no trust beyond reading the PKGBUILD.
2. **A personal pacman repository** on GitHub Releases, GPG-signed, added to
   `/etc/pacman.conf`. The only route that gives real `pacman -S` and picks up
   updates with `-Syu`. Aimed at the author's own machines.
3. **The AUR**, prepared now and published the day pushes reopen.

Preparing for (3) is not speculative work: a versioned tarball source with a
real `sha256sum` instead of `SKIP`, plus a committed `.SRCINFO`, is simply the
correct shape for an Arch package and makes (1) and (2) better too.

Explicitly rejected: a `curl … | bash` bootstrap. It would save two commands and
it is precisely the supply-chain shape that just froze the AUR.

### The binary-package problem

Assets are rasterised for a specific panel, because `Image.Scale` is
nearest-neighbour (see CLAUDE.md). A prebuilt package therefore carries one
resolution, and on a different panel it looks wrong.

The reconfigure command below resolves this: the package records the resolution
it was built for, and `post_install` regenerates when the local panel differs
and the tools are present, warning clearly when they are not. This is why the
binary repository is a secondary channel and the source build stays primary.

## Configuration

One file, `/etc/omarchy-plymouth-nier.conf`, installed from the repository's
`theme.conf` and listed in `backup=()` so pacman preserves edits and leaves a
`.pacnew` instead. `KEY=value`, one per line, with an environment override of
the same name prefixed `NIER_` (and `PLYMOUTH_` still honoured, so existing
invocations keep working).

Comments follow the Omarchy house style: a header paragraph saying why the file
exists, then prose per key explaining the reasoning and the trade-off rather
than restating the value.

### Keys

**Palette** — shared by both screens, so one change retints the Plymouth
screens and the Limine menu together.

`BONE` `DIM` `CHROME` `RUST` `GROUND`

`BONE` also feeds a literal RGB triple inside the Plymouth script
(`Image.Text` in `display_message_callback`), which becomes derived rather than
hand-written.

**Field**

`GLYPHS` `STACKS` `STACK_MIN` `STACK_MAX` `ALPHABET` `COLUMN` `GHOST_WORD`
`GHOST_MAX_WIDTH` `FIELD`

`FIELD=off` removes the ambient field entirely. `COLUMN` defaults to empty,
meaning "derive from `GHOST_WORD`": the fullwidth word is mapped back to
halfwidth through the alphabet using NFKC, so `システム` yields `ｼｽﾃﾑ`. Setting
it explicitly overrides that.

**Composition**

`SCALE` `NAME` `WELCOME` `GOODBYE` `HINT` `RESOLUTION` `BRANDING`
`BRACKET_INSET` `BRACKET_ARM` `MENU_HELP`

`WELCOME` and `GOODBYE` are templates carrying `{name}`.

### Validation

The loader fails loudly, naming the offending key: colours must be `#RRGGBB` or
`#RGB`; counts must be non-negative integers; `STACK_MIN` must not exceed
`STACK_MAX`; fractions must lie in their documented range. `SCALE` outside
0.2–2.0 is clamped with a warning rather than refused, because the composition
degrades gradually rather than breaking. Unknown keys warn and are ignored, so
a config from a newer version does not break an older install.

## The reconfigure command

`omarchy-nier-reconfigure` reads `/etc/omarchy-plymouth-nier.conf`, validates
it, regenerates **into a temporary directory**, and only swaps the result into
place if every step succeeded — a failed regeneration leaves the working theme
untouched. It then re-applies the Limine block and rebuilds the boot image.
`--dry-run` reports what would change and touches nothing.

It needs ImageMagick and the two font packages. Those stay `makedepends` and
gain `optdepends` entries; the command checks for them and names exactly what
to install.

`post_upgrade` re-runs it when `/etc/omarchy-plymouth-nier.conf` differs from
the shipped default, so customisation survives upgrades.

**Accepted cost:** after reconfiguring, `pacman -Qkk` reports the theme files as
altered. They are generated files owned by the package; this is inherent to the
design and is documented rather than worked around.

## Shared code

The Limine splice functions move out of the pacman scriptlet into
`/usr/share/omarchy-plymouth-nier/limine-splice.sh`, sourced by the scriptlet,
by `install.sh` and by the reconfigure command. One implementation, so the
three paths cannot drift.

Both generators read the config through one module, `nierconf.py`, rather than
each parsing the file with its own rules.

## Verification

- Clean-clone build at several distinct configurations.
- `plyparse` and `plyrun` against the script generated by each, because a bad
  config can produce a script that parses but behaves wrongly.
- The generated Limine block parses.
- Round trip: default → customised → default must produce byte-identical
  assets, which also proves the build stays reproducible.
