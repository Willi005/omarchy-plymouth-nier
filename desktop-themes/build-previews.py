#!/usr/bin/env python3
"""Render preview.png for each theme, in the shape Omarchy's own previews take.

The stock previews are real screenshots of a desktop: bar, editor, terminal,
btop, file manager. Reproducing that literally would mean applying each theme
to a live session, opening four apps, arranging them and grabbing the screen --
twice, on somebody's working desktop. So this composes the same layout instead,
from the theme's own colors.toml and btop.theme, and shoots it with headless
Chromium. Nothing touches the running session, and the result regenerates
whenever a palette changes.

It is a mock, not a screenshot, and it does not pretend otherwise: what it
promises is that every colour on it is a colour the theme actually specifies.

    python3 build-previews.py [theme ...]
"""

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
THEMES = HERE / "themes"

# Same 16:9 the stock previews use. They are 1800x1012; the theme menu scales
# them down, so matching the aspect matters more than the exact size.
W, H = 1800, 1012


def die(msg):
    sys.exit(f"build-previews: {msg}")


def browser():
    for name in ("chromium", "brave", "google-chrome-stable"):
        path = shutil.which(name)
        if path:
            return path
    die("no chromium/brave found to render with")


def read_colors(path):
    """Parse the handful of `key = \"value\"` lines a colors.toml holds."""
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip().strip('"')
    return out


def read_btop(path):
    """btop themes are `theme[key]="#rrggbb"` lines."""
    out = {}
    if not path.exists():
        return out
    for m in re.finditer(r'theme\[([a-z_0-9]+)\]\s*=\s*"([^"]*)"',
                         path.read_text(encoding="utf-8")):
        out[m.group(1)] = m.group(2)
    return out


def first_border_colour(value, fallback):
    """hyprland_active_border is `rgba(55503fee) rgba(cfc9b0ee) 45deg`.

    The gradient's second stop is the one that reads as the accent on screen,
    so the window outline in the mock uses that rather than the first.
    """
    stops = re.findall(r"rgba\(([0-9a-fA-F]{6})[0-9a-fA-F]{2}\)", value or "")
    if not stops:
        return fallback
    return "#" + stops[-1]


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


# --- the mock content -------------------------------------------------------
# Deliberately the same kind of material the stock previews show, so the two
# read as the same picture in different colours rather than as two designs.

TREE = ["omarchy-theme-set", "omarchy-theme-list", "omarchy-theme-bg-next",
        "omarchy-nier-themes", "omarchy-hook-install", "omarchy-pkg-add",
        "omarchy-refresh-shell", "omarchy-restart-shell", "omarchy-font-set",
        "omarchy-launch-browser", "omarchy-launch-editor", "omarchy-cmd-screenshot",
        "omarchy-capture-record", "omarchy-menu-keybindings", "omarchy-update",
        "omarchy-version", "omarchy-debug", "omarchy-install-docker"]

# (indent, [(class, text), ...])
CODE = [
    (0, [("cm", "# A directory the user wrote themselves, and a symlink to")]),
    (0, [("cm", "# their own working copy, are theirs to fill however they like.")]),
    (0, [("kw", "theme_came_from_a_repo"), ("pn", "() {")]),
    (1, [("kw", "local"), ("va", " source"), ("pn", "="), ("va", "$1")]),
    (0, []),
    (1, [("pn", "[[ ! -L "), ("va", "$source"), ("pn", " && -d "),
         ("va", "$source"), ("pn", "/.git ]]")]),
    (0, [("pn", "}")]),
    (0, []),
    (0, [("kw", "stage_installed_theme"), ("pn", "() {")]),
    (1, [("kw", "for"), ("va", " entry"), ("kw", " in"), ("st", ' "$source"/*'), ("pn", "; do")]),
    (2, [("va", "name"), ("pn", "="), ("va", "${entry##*/}")]),
    (0, []),
    (2, [("kw", "if"), ("pn", " [[ -L "), ("va", "$entry"), ("pn", " ]] || "),
         ("fn", "is_denied_installed_file"), ("st", ' "$name"'), ("pn", "; then")]),
    (3, [("kw", "case"), ("st", ' "${name,,}"'), ("kw", " in")]),
    (4, [("st", "readme* | license* | *.md"), ("pn", ") ;;")]),
    (4, [("pn", "*) "), ("va", "IGNORED_THEME_FILES"), ("pn", "+=("), ("st", '"$name"'), ("pn", ") ;;")]),
    (3, [("kw", "esac")]),
    (2, [("kw", "elif"), ("pn", " [[ -d "), ("va", "$entry"), ("pn", " ]]; then")]),
    (3, [("fn", "stage_installed_dir"), ("st", ' "$entry" "$NEXT/$name"')]),
    (2, [("kw", "else")]),
    (3, [("fn", "cp"), ("st", ' "$entry" "$NEXT/$name"')]),
    (2, [("kw", "fi")]),
    (1, [("kw", "done")]),
    (0, [("pn", "}")]),
]

LS = [("d", "backgrounds"), ("f", "btop.theme"), ("f", "colors.toml"),
      ("f", "chromium.theme"), ("f", "icons.theme"), ("x", "neovim.lua"),
      ("f", "preview.png"), ("x", "vscode.json")]

PROCS = [("chromium", "227M", "0.0"), ("quickshell", "77M", "0.4"),
         ("hyprland", "232M", "1.2"), ("chromium", "285M", "0.0"),
         ("nvim", "102M", "0.0"), ("btop", "41M", "0.6"),
         ("chromium", "511M", "0.1"), ("pipewire", "49M", "0.0"),
         ("nautilus", "196M", "0.0"), ("chromium", "238M", "0.1"),
         ("alacritty", "154M", "0.2"), ("nvim", "83M", "0.0"),
         ("systemd", "12M", "0.0"), ("plymouthd", "8M", "0.0"),
         ("chromium", "714M", "0.3"), ("gpg-agent", "6M", "0.0")]

FILES = ["Desktop", "Documents", "Downloads", "Music",
         "Pictures", "Projects", "Videos", "Vaults",
         "Code", "Games", "Notes", "Screenshots"]

# Fills the terminal pane the way a real one would be filled -- an empty
# expanse under two commands reads as a mock, which is the one thing the
# preview should not advertise about itself.
THEME_LIST = ["Catppuccin", "Everforest", "Flexoki Light", "Flexoki Light Alt",
              "Gruvbox", "Kanagawa", "Matte Black", "Nier Black",
              "Nord", "Osaka Jade", "Rose Pine", "Tokyo Night"]


def bars(seed, n, lo, hi):
    """A deterministic pseudo-random bar profile, so previews are stable."""
    out, x = [], seed
    for _ in range(n):
        x = (x * 1103515245 + 12345) & 0x7FFFFFFF
        out.append(lo + (x >> 8) % (hi - lo))
    return out


def build_html(name, c, bt):
    ground = c.get("background", "#101010")
    surface = c.get("lighter_background", ground)
    deep = c.get("dark_background", ground)
    fg = c.get("foreground", "#cccccc")
    dim = c.get("dark_foreground", fg)
    bright = c.get("bright_foreground", fg)
    accent = c.get("accent", fg)
    sel = c.get("selection", surface)
    muted = c.get("muted", dim)

    border = first_border_colour(c.get("hyprland_active_border"), accent)
    idle = first_border_colour(c.get("hyprland_inactive_border"), muted)

    kw = c.get("magenta", accent)
    st = c.get("green", accent)
    fn = c.get("cyan", accent)
    va = c.get("blue", fg)
    num = c.get("yellow", accent)
    red = c.get("red", accent)

    # btop's own gradients, so the graph in the mock is the graph you get.
    g_hi = bt.get("cpu_end", accent)
    g_mid = bt.get("cpu_mid", accent)
    g_lo = bt.get("cpu_start", muted)
    box = bt.get("proc_box", muted)
    div = bt.get("div_line", muted)

    tree_rows = "".join(
        f'<div class="row{" sel" if i == 3 else ""}">'
        f'<span class="star">*</span>{esc(t)}</div>'
        for i, t in enumerate(TREE))

    code_rows = []
    for n, (indent, spans) in enumerate(CODE, start=118):
        body = "".join(f'<span class="{cls}">{esc(txt)}</span>' for cls, txt in spans)
        pad = "&nbsp;" * (indent * 2)
        code_rows.append(f'<div class="cl"><span class="ln">{n}</span>{pad}{body}</div>')
    code_rows = "".join(code_rows)

    ls_rows = "".join(
        f'<div class="lsr"><span class="perm">'
        f'{"drwxr-xr-x" if k == "d" else "-rw-r--r--"}</span>'
        f'<span class="sz">{"-" if k == "d" else "2.6k"}</span>'
        f'<span class="{ {"d": "dn", "x": "xn", "f": "fn2"}[k] }">{esc(v)}</span></div>'
        for k, v in LS)

    cpu = bars(7, 68, 8, 60)
    mem = bars(31, 68, 4, 44)
    cpu_bars = "".join(
        f'<span class="gb" style="height:{v}px;background:'
        f'{g_hi if v > 44 else (g_mid if v > 26 else g_lo)}"></span>' for v in cpu)
    mem_bars = "".join(
        f'<span class="gb" style="height:{v}px;background:{g_mid if v > 24 else g_lo}">'
        f'</span>' for v in mem)

    core_rows = "".join(
        f'<div class="core"><span class="cn">{i}</span>'
        f'<span class="cbar"><i style="width:{p}%;background:'
        f'{g_hi if p > 70 else (g_mid if p > 40 else g_lo)}"></i></span>'
        f'<span class="cp">{p}%</span></div>'
        for i, p in enumerate(bars(99, 8, 6, 92)))

    proc_rows = "".join(
        f'<div class="pr"><span class="pn2">{esc(n)}</span>'
        f'<span class="pm">{m}</span><span class="pc">{u}</span></div>'
        for n, m, u in PROCS)

    file_rows = "".join(
        f'<div class="fi"><span class="fico"></span><span>{esc(f)}</span></div>'
        for f in FILES)

    theme_rows = "".join(
        f'<div class="tl"><span class="{"on" if t.startswith(name.split()[0]) else ""}">'
        f'{esc(t)}</span></div>' for t in THEME_LIST)

    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
html,body {{ width:{W}px; height:{H}px; overflow:hidden; }}
body {{
  background:{deep};
  font-family:"JetBrainsMono Nerd Font","JetBrains Mono",monospace;
  color:{fg}; font-size:13px; line-height:1.45;
  -webkit-font-smoothing:antialiased;
}}
.bar {{
  height:34px; display:flex; align-items:center; gap:14px;
  padding:0 16px; background:{ground}; color:{dim}; font-size:12.5px;
}}
.ws {{ display:flex; gap:9px; }}
.ws b {{ color:{accent}; font-weight:400; }}
.clock {{ margin-left:auto; margin-right:auto; color:{fg}; }}
.tray {{ display:flex; gap:11px; margin-left:auto; }}
.grid {{
  display:grid; grid-template-columns:1fr 1fr; grid-template-rows:1fr 1fr;
  gap:10px; padding:10px; height:{H - 34}px;
}}
.win {{
  background:{ground}; border:2px solid {idle}; border-radius:9px;
  overflow:hidden; display:flex; flex-direction:column;
}}
.win.active {{ border-color:{border}; }}
.tt {{
  display:flex; align-items:center; gap:10px; padding:5px 12px;
  background:{surface}; color:{dim}; font-size:11.5px;
}}
.tt .on {{ color:{accent}; }}
.pane {{ flex:1; display:flex; overflow:hidden; }}

.tree {{ width:250px; padding:6px 8px; overflow:hidden; color:{dim}; font-size:11.5px; }}
.row {{ white-space:nowrap; overflow:hidden; padding:0 4px; border-radius:3px; }}
.row.sel {{ background:{sel}; color:{bright}; }}
.star {{ color:{muted}; margin-right:7px; }}
.code {{ flex:1; padding:6px 10px; overflow:hidden; font-size:12px; }}
.cl {{ white-space:nowrap; }}
.ln {{ display:inline-block; width:34px; color:{muted}; text-align:right;
       margin-right:14px; font-size:11px; }}
.kw {{ color:{kw}; }} .st {{ color:{st}; }} .fn {{ color:{fn}; }}
.va {{ color:{va}; }} .cm {{ color:{muted}; font-style:italic; }}
.pn {{ color:{fg}; }}
.status {{
  display:flex; gap:14px; padding:3px 12px; background:{surface};
  color:{dim}; font-size:11px;
}}
.status .mode {{ color:{ground}; background:{accent}; padding:0 8px; border-radius:3px; }}

.term {{ padding:9px 12px; overflow:hidden; font-size:12px; width:100%; }}
.prompt b {{ color:{accent}; font-weight:400; }}
.prompt i {{ color:{fn}; font-style:normal; }}
.lsr {{ white-space:nowrap; }}
.perm {{ color:{muted}; margin-right:14px; }}
.sz {{ color:{dim}; display:inline-block; width:44px; }}
.dn {{ color:{va}; }} .xn {{ color:{st}; }} .fn2 {{ color:{fg}; }}
.tlist {{ columns:2; column-gap:36px; color:{dim}; }}
.tl .on {{ color:{accent}; }}

.btop {{ flex:1; padding:8px 10px; display:flex; flex-direction:column; gap:7px;
         overflow:hidden; }}
.bx {{ border:1px solid {box}; border-radius:5px; padding:5px 8px; overflow:hidden; }}
.bxt {{ color:{box}; font-size:10.5px; margin-bottom:3px; }}
.graph {{ display:flex; align-items:flex-end; gap:2px; height:62px; }}
.gb {{ flex:1; border-radius:1px; }}
.cores {{ display:grid; grid-template-columns:1fr 1fr; gap:2px 16px; }}
.core {{ display:flex; align-items:center; gap:7px; font-size:10.5px; color:{dim}; }}
.cn {{ width:12px; color:{muted}; }}
.cbar {{ flex:1; height:7px; background:{div}; border-radius:2px; overflow:hidden; }}
.cbar i {{ display:block; height:100%; }}
.cp {{ width:32px; text-align:right; }}
.procs {{ flex:1; overflow:hidden; }}
.pr {{ display:flex; font-size:11px; color:{dim}; }}
.pn2 {{ flex:1; color:{fg}; }} .pm {{ width:62px; text-align:right; }}
.pc {{ width:52px; text-align:right; color:{muted}; }}

.fm {{ flex:1; display:flex; overflow:hidden; }}
.side {{ width:200px; background:{surface}; padding:10px 12px; color:{dim};
         font-size:12px; }}
.side div {{ padding:3px 8px; border-radius:4px; }}
.side .on {{ background:{sel}; color:{bright}; }}
.main {{ flex:1; padding:12px 14px; }}
.fgrid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px 10px; }}
.fi {{ text-align:center; font-size:11.5px; color:{fg}; }}
/* A folder rather than a rounded rectangle: the tab is what makes the shape
   legible at the size the theme menu renders this. */
.fico {{ display:block; width:54px; height:42px; margin:0 auto 6px;
         background:{accent}; opacity:.85; border-radius:0 5px 5px 5px;
         position:relative; }}
.fico::before {{ content:""; position:absolute; left:0; top:-7px; width:24px;
         height:9px; background:{accent}; border-radius:4px 4px 0 0; }}
.crumb {{ color:{dim}; font-size:12px; margin-bottom:12px; }}
</style></head><body>

<div class="bar">
  <span class="ws"><b>1</b><span>2</span><span>3</span><span>4</span></span>
  <span class="clock">Friday 12:43</span>
  <span class="tray"><span>{esc(name)}</span><span>󰤨</span><span>󰂯</span><span>󰁹</span></span>
</div>

<div class="grid">
  <div class="win active">
    <div class="tt"><span class="on">1:omarchy</span><span>2:omarchy-iso</span>
      <span style="margin-left:auto">cph-fd</span></div>
    <div class="pane">
      <div class="tree">{tree_rows}</div>
      <div class="code">{code_rows}</div>
    </div>
    <div class="status"><span class="mode">NORMAL</span><span>omarchy-theme-set</span>
      <span style="margin-left:auto">20% 129:8</span></div>
  </div>

  <div class="win">
    <div class="tt"><span class="on">btop</span><span>up 3d 23:16</span></div>
    <div class="btop">
      <div class="bx"><div class="bxt">cpu</div>
        <div class="graph">{cpu_bars}</div>
        <div class="cores" style="margin-top:6px">{core_rows}</div>
      </div>
      <div class="bx"><div class="bxt">mem</div>
        <div class="graph" style="height:44px">{mem_bars}</div>
      </div>
      <div class="bx procs"><div class="bxt">proc</div>{proc_rows}</div>
    </div>
  </div>

  <div class="win">
    <div class="tt"><span class="on">alacritty</span></div>
    <div class="pane"><div class="term">
      <div class="prompt"><b>omarchy</b> <i>themes</i> ❯ ls -l</div>
      {ls_rows}
      <div class="prompt" style="margin-top:6px"><b>omarchy</b> <i>themes</i> ❯
        omarchy-nier-themes status</div>
      <div style="color:{dim}">  nier-black&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
        symlink → /usr/share/omarchy-nier-themes</div>
      <div style="color:{dim}">  flexoki-light-alt&nbsp;&nbsp;symlink →
        /usr/share/omarchy-nier-themes</div>
      <div class="prompt" style="margin-top:6px"><b>omarchy</b> <i>themes</i> ❯
        omarchy theme list</div>
      <div class="tlist">{theme_rows}</div>
      <div class="prompt" style="margin-top:6px"><b>omarchy</b> <i>themes</i> ❯ </div>
    </div></div>
  </div>

  <div class="win">
    <div class="tt"><span class="on">Files</span><span>Home</span></div>
    <div class="fm">
      <div class="side">
        <div class="on">Home</div><div>Recent</div><div>Starred</div>
        <div>Network</div><div>Trash</div><div style="margin-top:8px">Downloads</div>
        <div>Projects</div>
      </div>
      <div class="main">
        <div class="crumb">Home</div>
        <div class="fgrid">{file_rows}</div>
      </div>
    </div>
  </div>
</div>
</body></html>"""


def render(theme):
    d = THEMES / theme
    colors = d / "colors.toml"
    if not colors.exists():
        die(f"{theme}: no colors.toml")

    c = read_colors(colors)
    bt = read_btop(d / "btop.theme")
    html = build_html(theme.replace("-", " ").title(), c, bt)

    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "preview.html"
        page.write_text(html, encoding="utf-8")
        shot = Path(tmp) / "shot.png"
        subprocess.run(
            [browser(), "--headless", "--disable-gpu", "--hide-scrollbars",
             "--force-device-scale-factor=1", f"--window-size={W},{H}",
             f"--screenshot={shot}", f"--user-data-dir={tmp}/profile",
             page.as_uri()],
            check=True, capture_output=True)
        if not shot.exists():
            die(f"{theme}: the browser produced no screenshot")
        # -strip so two runs of the same palette are byte-identical.
        subprocess.run(["magick", str(shot), "-strip", str(d / "preview.png")],
                       check=True)

    size = (d / "preview.png").stat().st_size
    print(f"  {theme}: preview.png {W}x{H}, {size} B")


if __name__ == "__main__":
    wanted = sys.argv[1:] or sorted(p.name for p in THEMES.iterdir() if p.is_dir())
    for t in wanted:
        render(t)
