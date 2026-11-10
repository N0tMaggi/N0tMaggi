from __future__ import annotations

from pathlib import Path

from build_card import ADVANCE, LINE_MID, THEMES
from build_pacman import CANVAS_W, CHASER_COLOR, bitmap, loop, mix, sprite_path, validate_smil

ROOT = Path(__file__).resolve().parent.parent

PX = 3
GAP = 14
SLOT_W = CANVAS_W / 3
BUTTON_W = (CANVAS_W - 2 * GAP) / 3
HEIGHT = 20 * PX
LABEL_FONT = 18
ICON_GAP = 12
OUTLINE_MIX = 0.18

assert BUTTON_W % PX == 0, "the button must be a whole number of pixels wide"

MONITOR = """
##########
#........#
#.#......#
#..#.....#
#.#......#
#........#
##########
....##....
..######..
"""

MONITOR_CURSOR = """
..........
..........
..........
..........
....###...
..........
..........
..........
..........
"""

GLOBE = """
...####...
.##.##.##.
#..#..#..#
##########
#..#..#..#
##########
#..#..#..#
.##.##.##.
...####...
"""

HEART = """
.##...##.
####.####
#########
#########
.#######.
..#####..
...###...
....#....
"""

CURSOR_BLINK = 1.06
HOP_EVERY = 2.0
BEAT_EVERY = 1.2


def path(art: str) -> str:
    return sprite_path(bitmap(art), PX, PX)


def twitch(offsets: list[tuple[int, int]], times: list[float], dur: float) -> str:
    values = ";".join(f"{dx * PX},{dy * PX}" for dx, dy in offsets)
    return (f'<animateTransform attributeName="transform" type="translate" '
            f'values="{values}" keyTimes="{";".join(f"{t:g}" for t in times)}" dur="{dur}s" '
            f'calcMode="discrete" repeatCount="indefinite"/>')


def monitor() -> str:
    return (f'<path d="{path(MONITOR)}"/>'
            f'<path d="{path(MONITOR_CURSOR)}">{loop("opacity", ["1", "0"], CURSOR_BLINK)}</path>')


def globe() -> str:
    hop = twitch([(0, 0), (0, -1), (0, 0)], [0, 0.8, 0.9], HOP_EVERY)
    return f'<g>{hop}<path d="{path(GLOBE)}"/></g>'


def heart() -> str:
    beat = (f'<animateTransform attributeName="transform" type="scale" '
            f'values="1;1.2;1;1.2;1" keyTimes="0;0.1;0.2;0.3;0.4" dur="{BEAT_EVERY}s" '
            f'calcMode="discrete" repeatCount="indefinite"/>')
    return f'<g>{beat}<path d="{path(HEART)}"/></g>'


LINKS = (
    ("portfolio", "PORTFOLIO", "key", monitor),
    ("website", "MAGGI.DEV", "value", globe),
    ("femboy", "ISAFEMBOY.GAY", "pink", heart),
)


def stepped(x: float, y: float, w: float, h: float) -> str:
    return (f"M{x + PX:g} {y:g}h{w - 2 * PX:g}v{PX}h{PX}v{h - 2 * PX:g}h{-PX}v{PX}"
            f"h{-(w - 2 * PX):g}v{-PX}h{-PX}v{-(h - 2 * PX):g}h{PX}z")


def build(theme: str, slot: int) -> str:
    c = THEMES[theme]
    _, label, accent_key, icon = LINKS[slot]
    accent = CHASER_COLOR[theme] if accent_key == "pink" else c[accent_key]

    x = slot * GAP / 3
    icon_w = 10 * PX
    label_w = len(label) * LABEL_FONT * ADVANCE
    left = x + (BUTTON_W - icon_w - ICON_GAP - label_w) / 2

    mid = (PX + HEIGHT - 2 * PX) / 2

    return f"""<?xml version='1.0' encoding='UTF-8'?>
<svg xmlns="http://www.w3.org/2000/svg" width="{SLOT_W:.3f}px" height="{HEIGHT}px"
     viewBox="0 0 {SLOT_W:.3f} {HEIGHT}" font-family="ConsolasFallback,Consolas,Menlo,monospace">
<style>
@font-face {{
  src: local('Consolas'), local('Consolas Bold');
  font-family: 'ConsolasFallback';
  font-display: swap;
  size-adjust: 109%;
}}
text {{white-space: pre;}}
.px {{shape-rendering: crispEdges;}}
</style>
<g class="px">
<path d="{stepped(x, 0, BUTTON_W, HEIGHT)}" fill="{mix(c['bg'], c['fg'], OUTLINE_MIX)}"/>
<path d="{stepped(x + PX, PX, BUTTON_W - 2 * PX, HEIGHT - 2 * PX)}" fill="{c['bg']}"/>
<rect x="{x + 2 * PX:g}" y="{HEIGHT - 2 * PX}" width="{BUTTON_W - 4 * PX:g}" height="{PX}" fill="{accent}"/>
<g fill="{accent}" transform="translate({left + icon_w / 2:.2f},{mid:g})">{icon()}</g>
</g>
<text x="{left + icon_w + ICON_GAP:.2f}" y="{mid + LINE_MID * LABEL_FONT:.2f}" font-size="{LABEL_FONT}px" fill="{c['fg']}">{label}</text>
</svg>
"""


def main() -> None:
    print(f"row      : {CANVAS_W}px = 3 x {BUTTON_W:g}px buttons + 2 x {GAP}px gaps")
    for theme in THEMES:
        for slot, (name, *_) in enumerate(LINKS):
            svg = build(theme, slot)
            checked = validate_smil(svg)
            out = ROOT / f"link_{name}_{theme}.svg"
            out.write_text(svg, encoding="utf-8")
            print(f"wrote {out.name} ({out.stat().st_size:,} bytes, {checked} animations validated)")


if __name__ == "__main__":
    main()
