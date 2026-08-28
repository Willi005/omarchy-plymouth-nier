# omarchy-nier-themes

Two Omarchy desktop themes, packaged: **Nier Black** and **Flexoki Light Alt**.

Separate from `omarchy-plymouth-nier` on purpose. That one needs Plymouth and
Limine and changes nothing you see after login; this one needs Omarchy and
changes the running desktop. Either is useful without the other.

```bash
sudo pacman -U omarchy-nier-themes-*.pkg.tar.zst
omarchy theme set "Nier Black"
```

## Why a package rather than `omarchy theme install <url>`

Omarchy's own installer clones a git repo into `~/.config/omarchy/themes` and
then holds it to a deny list, dropping anything that runs code: every `*.lua`,
the terminal configs, and `vscode.json`. Flexoki Light Alt ships a `neovim.lua`
naming `kepano/flexoki-neovim` and a `vscode.json` naming a real extension, so
that path would silently lose both.

A package cannot write into a home directory, so the artwork is installed under
`/usr/share/omarchy-nier-themes` and linked into place. That turns out to be
the better route rather than a workaround, because the deny list is keyed on
exactly the shape a symlink is not:

```bash
theme_came_from_a_repo() { [[ ! -L $source && -d $source/.git ]]; }
```

Omarchy's own comment calls a symlink to the user's working copy "theirs to
fill however they like". `omarchy-theme-list` globs `-type d -o -type l`, and
nothing ever writes back into a theme directory — `omarchy theme set` copies
out of it, and the current-background pointer lives in
`~/.local/state/omarchy/current`. So package ownership is safe.

## The linker

The symlinks are made by `omarchy-nier-themes`, which the install scriptlet
runs for whoever invoked pacman.

```bash
omarchy-nier-themes status     # what is linked
omarchy-nier-themes link       # link them
omarchy-nier-themes unlink     # remove the links and the hook
```

It never destroys anything. A real directory already sitting at the target is
refused, not replaced — the install still succeeds and says so. `--force` moves
that directory to `~/.config/omarchy/nier-themes-backup/<name>-<timestamp>`
first. Note *backup*, not `<name>.bak` next to the original: Omarchy lists
every directory in the themes folder, so a sibling backup would appear in the
theme menu as a theme of its own.

`unlink` only removes a symlink that points into this package, and only removes
the hook if it still matches the shipped one.

## The theme-set hook

Flexoki Light Alt needs `dark-browser-chrome` in
`~/.config/omarchy/hooks/theme-set.d/`, which keeps the browser dark under a
light theme. It is copied rather than symlinked: Omarchy runs everything in
that directory, and a dangling symlink there would error on every theme change
once the package was gone.

## Building

No build step — it is all data.

```bash
cd desktop-themes && makepkg -f
```

The payload is two directory trees, and makepkg's source array takes files and
URLs, not directories; listing the files individually does not work either,
since local sources are staged by basename and both themes have a
`colors.toml`, a `btop.theme` and a `preview.png`. So the PKGBUILD reads out of
`$startdir`. That is why there is no `aur/` flavour here: publishing to the AUR
would mean sourcing a release tarball, the way the boot package's
`aur/sync.sh` already does.
