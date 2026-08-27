#!/usr/bin/env bash
# Generate the AUR flavour of the PKGBUILD from the canonical one.
#
# The AUR wants a package that downloads a versioned tarball with a real
# checksum, while a local `git clone && makepkg -si` wants to build the working
# tree. Rather than maintain two PKGBUILDs that quietly diverge, this rewrites
# three lines of the canonical one and regenerates .SRCINFO.
#
# Run it after bumping pkgver AND after the matching GitHub release exists,
# since the checksum is computed from the published tarball.
set -euo pipefail

HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(dirname "$HERE")
REPO=https://github.com/Willi005/omarchy-plymouth-nier

pkgver=$(grep -Po '^pkgver=\K.*' "$ROOT/PKGBUILD")
url="$REPO/archive/refs/tags/v$pkgver.tar.gz"

echo ":: fetching $url"
sum=$(curl -fsSL "$url" | sha256sum | cut -d' ' -f1)
[ -n "$sum" ] || { echo "could not checksum the tarball -- is the release published?" >&2; exit 1; }
echo ":: sha256 $sum"

python3 - "$ROOT/PKGBUILD" "$HERE/PKGBUILD" "$url" "$sum" <<'PY'
import re, sys
src, dst, url, sum_ = sys.argv[1:5]
s = open(src).read()
s = re.sub(r"^source=\([^)]*\)$",
           f'source=("$pkgname-$pkgver.tar.gz::{url}")', s, flags=re.M | re.S)
s = re.sub(r"^sha256sums=\([^)]*\)$", f"sha256sums=('{sum_}')", s, flags=re.M | re.S)
s = s.replace('_srcsub=\n', '_srcsub="/$pkgname-$pkgver"\n')
open(dst, "w").write(s)
PY

cp "$ROOT/omarchy-plymouth-nier.install" "$HERE/"
( cd "$HERE" && makepkg --printsrcinfo > .SRCINFO )
echo ":: wrote $HERE/PKGBUILD and $HERE/.SRCINFO"
echo ":: the AUR is frozen -- see the vault note before trying to push"
