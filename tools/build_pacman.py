from __future__ import annotations

import datetime as dt
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from build_card import ADVANCE, THEMES

ROOT = Path(__file__).resolve().parent.parent
CALENDAR_SRC = ROOT / "cache" / "calendar.json"

U = 2
CELL = 14
PITCH = 18
RADIUS = 3
CANVAS_W = 1018
MARGIN = 15
LABEL_COL = 38
HEADER_FONT = 14
LABEL_FONT = 12

LEVEL_MIX = (0.10, 0.30, 0.50, 0.72, 1.0)

STEP = 0.075
INTRO = 1.5
OUTRO = 1.8
EAT_AHEAD = 5
CHOMP = 0.24

CAST = (
    (5, "blink", 0.34),
    (8, "wave", 0.30),
    (11, "hop", 0.38),
)
TRAIL = tuple(lag for lag, _, _ in CAST)
WAVE = 0.28
BLINK_EVERY = 2.4

MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
WEEKDAYS = {1: "Mon", 3: "Wed", 5: "Fri"}

PAC_OPEN = """
..#####..
.######..
######...
#####....
#####....
#####....
######...
.######..
..#####..
"""
PAC_HALF = """
..#####..
.#######.
#########
#######..
#####....
#######..
#########
.#######.
..#####..
"""
PAC_SHUT = """
..#####..
.#######.
#########
#########
#########
#########
#########
.#######.
..#####..
"""
PUP_BODY = """
....########....
.##.########.##.
###.#..##..#.###
###.########.###
.##.###..###.##.
....########....
...##########...
...##########...
................
................
"""
PUP_TAIL_DOWN = """
................
................
................
................
................
................
.............##.
................
................
................
"""
PUP_TAIL_UP = """
................
................
................
................
...............#
..............#.
................
................
................
................
"""
PUP_LEGS_A = """
................
................
................
................
................
................
................
................
...##.#..#.##...
...##......##...
"""
PUP_LEGS_B = """
................
................
................
................
................
................
................
................
...##.#..#.##...
......#..#......
"""
PUP_LIDS = """
................
................
.....##..##.....
................
................
................
................
................
................
................
"""
PUP_PX = (1.5, 1.5)

CHASER_COLOR = {"dark": "#f2bd8a", "light": "#7a3f14"}


def bitmap(art: str) -> list[str]:
    return [r for r in art.strip("\n").split("\n") if r]


def sprite_path(rows: list[str], pw: float = U, ph: float = U) -> str:
    h, w = len(rows), max(len(r) for r in rows)
    x0, y0 = -w * pw / 2, -h * ph / 2
    d = []
    for y, row in enumerate(rows):
        x = 0
        while x < len(row):
            if row[x] != "#":
                x += 1
                continue
            run = x
            while run < len(row) and row[run] == "#":
                run += 1
            d.append(f"M{x0 + x * pw:g} {y0 + y * ph:g}h{(run - x) * pw:g}v{ph:g}h{-(run - x) * pw:g}z")
            x = run
    return "".join(d)


def mix(a: str, b: str, t: float) -> str:
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(ca, cb))


class Timeline:

    def __init__(self, weeks: int, left: float, top: float) -> None:
        self.left, self.top = left, top
        self.speed = PITCH / STEP

        pts = []
        for r in range(7):
            cols = (0, weeks - 1) if r % 2 == 0 else (weeks - 1, 0)
            pts += [(self.cx(cols[0]), self.cy(r)), (self.cx(cols[1]), self.cy(r))]
        pts.append((CANVAS_W + (max(TRAIL) + 2) * PITCH, self.cy(6)))
        self.points = pts

        self.dist = [0.0]
        for a, b in zip(pts, pts[1:]):
            self.dist.append(self.dist[-1] + abs(b[0] - a[0]) + abs(b[1] - a[1]))

        self.done = INTRO + (self.dist[-1] + max(TRAIL) * PITCH) / self.speed
        self.total = self.done + OUTRO

    def cx(self, col: int) -> float:
        return self.left + col * PITCH + CELL / 2

    def cy(self, row: int) -> float:
        return self.top + row * PITCH + CELL / 2

    def k(self, t: float) -> str:
        return f"{min(max(t / self.total, 0.0), 1.0):.5f}"

    def eat_time(self, col: int, row: int) -> float:
        seg = row * 2
        s = self.dist[seg] + abs(self.cx(col) - self.points[seg][0])
        return INTRO + max(0.0, s - EAT_AHEAD) / self.speed

    def motion(self, lag_cells: int = 0):
        lag = lag_cells * PITCH
        start = (self.points[0][0] - lag, self.points[0][1])
        route = [start] + self.points
        dist = [0.0] + [d + lag for d in self.dist]

        keys = [(0.0, start)]
        for d, p in zip(dist, route):
            t = INTRO + d / self.speed
            if (t, p) != keys[-1]:
                keys.append((t, p))

        heads = []
        for (t, a), (_, b) in zip(keys, keys[1:]):
            if a != b:
                heads.append((t, 0 if b[0] > a[0] else 180 if b[0] < a[0] else 90))
        heads[0] = (0.0, heads[0][1])
        return keys, heads


def anim_translate(tl: Timeline, keys) -> str:
    last = keys[-1][1]
    values = ";".join(f"{x:g},{y:g}" for _, (x, y) in keys) + f";{last[0]:g},{last[1]:g}"
    times = ";".join(tl.k(t) for t, _ in keys) + ";1"
    return (f'<animateTransform attributeName="transform" type="translate" '
            f'values="{values}" keyTimes="{times}" dur="{tl.total:.3f}s" '
            f'repeatCount="indefinite"/>')


def anim_discrete(tl: Timeline, attr: str, values: list[str], times: list[float]) -> str:
    return (f'<animate attributeName="{attr}" values="{";".join(values)}" '
            f'keyTimes="{";".join(tl.k(t) for t in times)}" dur="{tl.total:.3f}s" '
            f'calcMode="discrete" repeatCount="indefinite"/>')


def loop(attr: str, values: list[str], dur: float) -> str:
    n = len(values)
    keys = ";".join(f"{i / n:.4f}" for i in range(n))
    return (f'<animate attributeName="{attr}" values="{";".join(values)}" '
            f'keyTimes="{keys}" dur="{dur}s" calcMode="discrete" repeatCount="indefinite"/>')


def load_calendar() -> dict:
    if not CALENDAR_SRC.exists():
        raise SystemExit(f"{CALENDAR_SRC} missing -- run tools/fetch_stats.py first")
    return json.loads(CALENDAR_SRC.read_text(encoding="utf-8"))


def month_labels(weeks: list[list]) -> list[tuple[int, str]]:
    labels, last = [], None
    for i, week in enumerate(weeks):
        day = next((d for d in week if d), None)
        if not day:
            continue
        m = dt.date.fromisoformat(day["date"]).month
        if m != last:
            labels.append((i, MONTHS[m - 1]))
            last = m
    return [lab for j, lab in enumerate(labels)
            if j + 1 == len(labels) or labels[j + 1][0] - lab[0] >= 3]


def build(theme: str, cal: dict) -> str:
    c = THEMES[theme]
    weeks = cal["weeks"]
    ramp = [mix(c["bg"], c["value"], t) for t in LEVEL_MIX]

    left = MARGIN + LABEL_COL
    header_y = MARGIN + HEADER_FONT
    months_y = header_y + 26
    top = months_y + 8
    grid_bottom = top + 6 * PITCH + CELL
    legend_y = grid_bottom + 24
    height = legend_y + MARGIN

    tl = Timeline(len(weeks), left, top)
    cells: list[str] = []
    sprites: list[str] = []

    base = []
    for col, week in enumerate(weeks):
        for row, day in enumerate(week):
            if day:
                base.append(f'<use href="#d" x="{left + col * PITCH:g}" y="{top + row * PITCH:g}"/>')
    cells.append(f'<g fill="{ramp[0]}">{"".join(base)}</g>')

    eaten: list[tuple[float, int]] = []
    for col, week in enumerate(weeks):
        for row, day in enumerate(week):
            if not day or not day["level"]:
                continue
            t = tl.eat_time(col, row)
            eaten.append((t, day["count"]))
            cells.append(
                f'<use href="#d" x="{left + col * PITCH:g}" y="{top + row * PITCH:g}" '
                f'fill="{ramp[day["level"]]}">'
                f'{anim_discrete(tl, "visibility", ["visible", "hidden"], [0.0, t])}</use>'
            )

    layer = {name: sprite_path(bitmap(art), *PUP_PX) for name, art in (
        ("body", PUP_BODY), ("arms_down", PUP_TAIL_DOWN), ("arms_up", PUP_TAIL_UP),
        ("legs_a", PUP_LEGS_A), ("legs_b", PUP_LEGS_B), ("lids", PUP_LIDS),
    )}

    def flip(a: str, b: str, dur: float) -> str:
        return (f'<path d="{layer[a]}">{loop("opacity", ["1", "0"], dur)}</path>'
                f'<path d="{layer[b]}" opacity="0">{loop("opacity", ["0", "1"], dur)}</path>')

    for lag, trait, stride in CAST:
        keys, _ = tl.motion(lag)
        parts = [f'<path d="{layer["body"]}"/>', flip("legs_a", "legs_b", stride)]
        parts.append(flip("arms_down", "arms_up", WAVE) if trait == "wave"
                     else f'<path d="{layer["arms_down"]}"/>')
        if trait == "blink":
            parts.append(
                f'<path d="{layer["lids"]}" opacity="0"><animate attributeName="opacity" '
                f'values="0;1;0" keyTimes="0;0.93;0.98" dur="{BLINK_EVERY}s" '
                f'calcMode="discrete" repeatCount="indefinite"/></path>'
            )
        body = "".join(parts)
        if trait == "hop":
            body = (f'<g><animateTransform attributeName="transform" type="translate" '
                    f'values="0,0;0,{-PUP_PX[1]:g}" keyTimes="0;0.5" dur="{stride}s" '
                    f'calcMode="discrete" repeatCount="indefinite"/>{body}</g>')
        sprites.append(f'<g>{anim_translate(tl, keys)}<g fill="{CHASER_COLOR[theme]}">{body}</g></g>')

    keys, heads = tl.motion(0)
    rot = (f'<animateTransform attributeName="transform" type="rotate" '
           f'values="{";".join(str(h) for _, h in heads)}" '
           f'keyTimes="{";".join(tl.k(t) for t, _ in heads)}" dur="{tl.total:.3f}s" '
           f'calcMode="discrete" repeatCount="indefinite"/>')
    idle = anim_discrete(tl, "visibility", ["visible", "hidden"], [0.0, INTRO])
    moving = anim_discrete(tl, "visibility", ["hidden", "visible"], [0.0, INTRO])
    frames = "".join(
        f'<path d="{sprite_path(bitmap(art))}">'
        f'{loop("opacity", [str(v) for v in vis], CHOMP)}</path>'
        for art, vis in ((PAC_OPEN, (1, 0, 0, 0)), (PAC_HALF, (0, 1, 0, 1)), (PAC_SHUT, (0, 0, 1, 0)))
    )
    sprites.append(
        f'<g>{anim_translate(tl, keys)}<g fill="{c["key"]}">{rot}'
        f'<g>{idle}<path d="{sprite_path(bitmap(PAC_OPEN))}"/></g>'
        f'<g visibility="hidden">{moving}{frames}</g></g></g>'
    )

    eaten.sort()
    steps, score = [(0.0, 0)], 0
    for t, count in eaten:
        if count:
            score += count
            steps.append((t, score))
    width = len(f"{cal['total']:,}")
    number = []
    for i, (t, value) in enumerate(steps):
        nxt = steps[i + 1][0] if i + 1 < len(steps) else None
        if i == 0:
            vals, times = ["visible", "hidden"], [0.0, nxt]
        elif nxt is None:
            vals, times = ["hidden", "visible"], [0.0, t]
        else:
            vals, times = ["hidden", "visible", "hidden"], [0.0, t, nxt]
        number.append(
            f'<tspan x="{MARGIN:g}" visibility="{"visible" if i == 0 else "hidden"}">'
            f'{anim_discrete(tl, "visibility", vals, times)}{value:>{width},}</tspan>'
        )
    words_x = MARGIN + width * HEADER_FONT * ADVANCE

    months = "".join(f'<text x="{left + col * PITCH:g}" y="{months_y:g}">{name}</text>'
                     for col, name in month_labels(weeks))
    days = "".join(f'<text x="{MARGIN:g}" y="{tl.cy(row) + LABEL_FONT * 0.35:g}">{name}</text>'
                   for row, name in WEEKDAYS.items())

    grid_right = left + (len(weeks) - 1) * PITCH + CELL
    more_w = 4 * LABEL_FONT * ADVANCE
    swatch_x = grid_right - more_w - 6 - (5 * PITCH - (PITCH - CELL))
    swatches = "".join(f'<rect x="{swatch_x + i * PITCH:g}" y="{legend_y - CELL + 3:g}" '
                       f'width="{CELL}" height="{CELL}" rx="{RADIUS}" fill="{ramp[i]}"/>'
                       for i in range(5))

    return f"""<?xml version='1.0' encoding='UTF-8'?>
<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_W}px" height="{height:g}px"
     font-family="ConsolasFallback,Consolas,Menlo,monospace">
<style>
@font-face {{
  src: local('Consolas'), local('Consolas Bold');
  font-family: 'ConsolasFallback';
  font-display: swap;
  size-adjust: 109%;
}}
text, tspan {{white-space: pre;}}
.px {{shape-rendering: crispEdges;}}
</style>
<defs><rect id="d" width="{CELL}" height="{CELL}" rx="{RADIUS}"/></defs>
<rect width="{CANVAS_W}px" height="{height:g}px" fill="{c['bg']}" rx="15"/>
<text y="{header_y:g}" font-size="{HEADER_FONT}px" fill="{c['fg']}">{"".join(number)}</text>
<text x="{words_x:g}" y="{header_y:g}" font-size="{HEADER_FONT}px" fill="{c['fg']}"> contributions in the last year</text>
<g font-size="{LABEL_FONT}px" fill="{c['dots']}">{months}{days}
<text x="{swatch_x - 6:g}" y="{legend_y:g}" text-anchor="end">Less</text>
<text x="{grid_right - more_w:g}" y="{legend_y:g}">More</text>
</g>
{swatches}
{"".join(cells)}
<g class="px">{"".join(sprites)}</g>
</svg>
"""


def validate_smil(svg: str) -> int:
    root = ET.fromstring(svg.split("?>", 1)[1])
    count = 0
    for el in root.iter():
        tag = el.tag.split("}")[-1]
        if tag not in ("animate", "animateTransform") or "keyTimes" not in el.attrib:
            continue
        count += 1
        keys = [float(k) for k in el.get("keyTimes").split(";")]
        values = el.get("values").split(";")
        where = f"{tag} {el.get('attributeName')} ({len(values)} values)"
        if len(keys) != len(values):
            raise SystemExit(f"{where}: {len(keys)} keyTimes for {len(values)} values")
        if keys[0] != 0:
            raise SystemExit(f"{where}: first keyTime is {keys[0]}, must be 0")
        if any(b < a for a, b in zip(keys, keys[1:])):
            raise SystemExit(f"{where}: keyTimes decrease")
        if keys[-1] > 1:
            raise SystemExit(f"{where}: keyTime {keys[-1]} past 1")
        if el.get("calcMode", "linear") != "discrete" and keys[-1] != 1:
            raise SystemExit(f"{where}: interpolated animation must end at keyTime 1")
        if re.search(r"nan|inf", el.get("values"), re.I):
            raise SystemExit(f"{where}: non-finite value")
    return count


def main() -> None:
    cal = load_calendar()
    days = sum(1 for w in cal["weeks"] for d in w if d)
    print(f"calendar : {len(cal['weeks'])} weeks, {days} days, {cal['total']} contributions")
    for name in THEMES:
        svg = build(name, cal)
        checked = validate_smil(svg)
        out = ROOT / f"pacman_{name}.svg"
        out.write_text(svg, encoding="utf-8")
        print(f"wrote {out.name} ({out.stat().st_size:,} bytes, {checked} animations validated)")


if __name__ == "__main__":
    main()
