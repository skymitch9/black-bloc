"""The bracket as a PNG: the site's tree, or a standings table, drawn by Pillow and nothing else."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import lru_cache
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .model import (
    BYE,
    CALLED,
    COMPLETE,
    DISPUTED,
    ELIMINATION,
    FINAL,
    GRAND,
    LOSERS,
    POOLS,
    READY,
    REPORTED,
    THIRD,
    VOID,
    WAITING,
    WINNERS,
    Bracket,
    Match,
)
from .pools import pool_parts
from .sports_shape import is_pending
from .standings import table

FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"
REGULAR = "Rajdhani-Regular.ttf"
BOLD = "Rajdhani-Bold.ttf"

BG = (23, 17, 14)
SURFACE = (36, 26, 22)
FG = (251, 243, 233)
MUTED = (192, 168, 151)
HAIRLINE = (58, 42, 34)
ACCENT = (255, 122, 24)
GOLD = (255, 201, 60)
INFO = (105, 183, 224)
WARN = (255, 201, 60)
DANGER = (244, 112, 126)
QUIET = 0.55
DONE_LINE = 0.7

WIDE = 1600
SMALL_FIELD = 8
MARGIN = 32
MOST_COL = 460
NATURAL_COL = 376
TABLE_NARROW = 1000
QUIET_STATES = (WAITING, VOID, BYE)
UNDRAWN = (BYE, VOID)
FED = (COMPLETE, BYE, VOID)
ELLIPSIS = "…"
SEP = " · "


@dataclass(frozen=True)
class Extra:
    line: str | None = None
    votes: tuple[int, int] | None = None
    held: bool = False


@dataclass(frozen=True)
class Words:
    title: str
    format: str = ""
    state: str = ""
    kind: str = ""
    champion: str = ""
    held: str = ""
    heads: tuple[str, ...] = ("#", "Name", "W-L", "Pts")
    rounds: Mapping[str, str] = field(default_factory=dict)
    pools: Mapping[int, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Node:
    key: str
    side: str
    col: int
    y: float


@dataclass(frozen=True)
class Layout:
    nodes: tuple[Node, ...]
    links: tuple[tuple[str, str], ...]
    cols: int
    height: float
    losers_top: float | None


@lru_cache(maxsize=64)
def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / (BOLD if bold else REGULAR)), size)


def blend(colour: tuple[int, int, int], amount: float, under=BG) -> tuple[int, int, int]:
    return tuple(round(b + (c - b) * amount) for c, b in zip(colour, under, strict=True))


def fitted(text: str, face: ImageFont.FreeTypeFont, room: float) -> str:
    text = " ".join(str(text or "").split())
    if room <= 0:
        return ""
    if face.getlength(text) <= room:
        return text
    low, high = 0, len(text)
    while low < high:
        mid = (low + high + 1) // 2
        if face.getlength(text[:mid].rstrip() + ELLIPSIS) <= room:
            low = mid
        else:
            high = mid - 1
    return text[:low].rstrip() + ELLIPSIS if low else ""


def drawn_sets(bracket: Bracket) -> list[Match]:
    """The page's sets: no pending feeder, and once pools are over only the final's."""
    final = any(match.phase == FINAL for match in bracket.matches.values())
    return [
        match
        for match in bracket.ordered()
        if not is_pending(match) and not (final and match.phase == POOLS)
    ]


def unplayed(sets: list[Match]) -> set[str]:
    """`unplayedSets` from bracket-layout.js: byes, void sets, and sets that bring one or none."""
    feeders: dict[str, list[tuple[Match, str]]] = {}
    for one in sets:
        for to, take in ((one.winner_to, "winner"), (one.loser_to, "loser")):
            if to:
                feeders.setdefault(to, []).append((one, take))
    fates: dict[str, str] = {}

    def fate(match: Match) -> str:
        if match.key in fates:
            return fates[match.key]
        fates[match.key] = "play"
        found = "play"
        if match.state in UNDRAWN:
            found = match.state
        elif match.state == WAITING and match.key in feeders:
            seated = sum(1 for one in (match.slot_a, match.slot_b) if one is not None)
            coming = sum(
                1
                for one, take in feeders[match.key]
                if one.state not in FED
                and (fate(one) == "play" or (fate(one) == BYE and take == "winner"))
            )
            players = seated + coming
            found = "play" if players >= 2 else BYE if players == 1 else VOID
        fates[match.key] = found
        return found

    return {one.key for one in sets if fate(one) != "play"}


def by_side(sets: list[Match], side: str) -> list[tuple[int, list[Match]]]:
    rounds: dict[int, list[Match]] = {}
    for one in sets:
        if one.side == side:
            rounds.setdefault(one.round, []).append(one)
    return [
        (round_, sorted(rounds[round_], key=lambda one: one.position)) for round_ in sorted(rounds)
    ]


def tree_rows(counts: list[int]) -> list[list[float]]:
    found: list[list[float]] = []
    for at, count in enumerate(counts):
        if at == 0:
            found.append([p + 0.5 for p in range(count)])
            continue
        before = found[at - 1]
        if count == len(before):
            found.append(list(before))
        elif count * 2 == len(before):
            found.append([(before[2 * p] + before[2 * p + 1]) / 2 for p in range(count)])
        else:
            span = len(found[0])
            found.append([(p + 0.5) * (span / max(count, 1)) for p in range(count)])
    return found


def place_side(
    rounds: list[tuple[int, list[Match]]], side: str, hidden: set[str]
) -> tuple[list[Node], int, float]:
    lead = (
        rounds[0]
        if len(rounds) > 1 and rounds[0][0] == 0 and len(rounds[0][1]) < len(rounds[1][1])
        else None
    )
    main = rounds[1:] if lead else rounds
    rows = tree_rows([len(sets) for _, sets in main])
    nodes: list[Node] = []
    early = [one for one in lead[1] if one.key not in hidden] if lead else []
    col = 1 if early else 0
    for at, (_, sets) in enumerate(main):
        shown = [(one, rows[at][p]) for p, one in enumerate(sets) if one.key not in hidden]
        if not shown:
            continue
        nodes.extend(Node(one.key, side, col, y) for one, y in shown)
        col += 1
    for at, one in enumerate(early):
        target = next((node for node in nodes if node.key == one.winner_to), None)
        y = target.y + (-0.25 if one.winner_slot == "a" else 0.25) if target else at + 0.5
        nodes.append(Node(one.key, side, 0, y))
    if not nodes:
        return ([], 0, 0.0)
    least = min(node.y for node in nodes) - 0.5
    most = max(node.y for node in nodes) + 0.5
    return ([Node(n.key, n.side, n.col, n.y - least) for n in nodes], col, most - least)


def elimination_layout(sets: list[Match]) -> Layout:
    """`eliminationLayout` from bracket-layout.js, column for column."""
    hidden = unplayed(sets)
    winners, winners_cols, winners_span = place_side(by_side(sets, WINNERS), WINNERS, hidden)
    losers, losers_cols, losers_span = place_side(by_side(sets, LOSERS), LOSERS, hidden)
    nodes = list(winners)
    losers_top = winners_span + 0.75 if losers else winners_span
    nodes.extend(Node(n.key, n.side, n.col, n.y + losers_top) for n in losers)
    height = losers_top + losers_span if losers else winners_span
    last = [n for n in winners if n.col == winners_cols - 1]
    final_y = last[0].y if last else 0.5
    grand_col = max(winners_cols, losers_cols)
    at = 0
    for _, found in by_side(sets, GRAND):
        drawn = [one for one in found if one.key not in hidden]
        if not drawn:
            continue
        nodes.extend(Node(one.key, GRAND, grand_col + at, final_y) for one in drawn)
        at += 1
    thirds = by_side(sets, THIRD)
    shown_thirds = [one for one in thirds[0][1] if one.key not in hidden] if thirds else []
    if shown_thirds:
        col = max(winners_cols - 1, 0)
        for p, one in enumerate(shown_thirds):
            nodes.append(Node(one.key, THIRD, col, height + 0.75 + p))
        height += 0.75 + len(shown_thirds)
    cols = max((n.col + 1 for n in nodes), default=0)
    keys = {n.key for n in nodes}
    links = tuple(
        (one.key, one.winner_to)
        for one in sets
        if one.winner_to and one.key in keys and one.winner_to in keys
    )
    return Layout(tuple(nodes), links, cols, max(height, 1.0), losers_top if losers else None)


@dataclass(frozen=True)
class Slot:
    name: str
    score: str
    won: bool
    lost: bool


@dataclass(frozen=True)
class Box:
    key: str
    state: str
    top: str
    held: bool
    a: Slot
    b: Slot


@dataclass(frozen=True)
class Row:
    rank: str
    name: str
    record: str
    points: str
    out: bool


@dataclass(frozen=True)
class Scene:
    """Everything a picture shows and nothing else: the fingerprint is this, hashed."""

    title: str
    subline: str
    kind: str
    champion: str
    held: str
    heads: tuple[str, ...]
    layout: Layout | None
    boxes: tuple[Box, ...]
    headings: tuple[tuple[str, int, float, str], ...]
    tables: tuple[tuple[str, tuple[Row, ...]], ...]
    count: int


def slot_of(match: Match, which: str, names: Mapping[int, str], extra: Extra | None) -> Slot:
    entrant = match.slot_a if which == "a" else match.slot_b
    decided = match.state == COMPLETE and match.winner is not None
    won = decided and match.winner == entrant
    lost = decided and entrant is not None and match.winner != entrant
    votes = extra.votes if extra is not None else None
    score = (votes[0] if which == "a" else votes[1]) if votes else None
    if score is None:
        score = match.score_a if which == "a" else match.score_b
    if match.state == COMPLETE and match.forfeit:
        shown = "W" if won else "FF"
    else:
        shown = "" if score is None else str(score)
    name = names.get(entrant, "") if entrant is not None else ""
    return Slot(str(name or ""), shown, won, lost)


def box_of(match: Match, names: Mapping[int, str], extra: Extra | None) -> Box:
    line = extra.line if extra is not None else None
    top = SEP.join(part for part in (match.key, line) if part)
    return Box(
        match.key,
        match.state,
        top,
        bool(extra and extra.held),
        slot_of(match, "a", names, extra),
        slot_of(match, "b", names, extra),
    )


def rows_of(bracket: Bracket, names: Mapping[int, str]) -> tuple[Row, ...]:
    found = table(bracket)
    if not found:
        return tuple(
            Row(str(at), str(names.get(one, "")), "0-0", "0", False)
            for at, one in enumerate(bracket.entrants, start=1)
        )
    return tuple(
        Row(
            str(row.place or ""),
            str(names.get(row.entrant, "")),
            f"{row.record.set_wins}-{row.record.set_losses}",
            str(row.record.set_wins),
            row.entrant in bracket.withdrawn,
        )
        for row in found
    )


def pool_tables(bracket: Bracket, names: Mapping[int, str], words: Words) -> list:
    return [
        (words.pools.get(number, ""), rows_of(part, names))
        for number, part in enumerate(pool_parts(bracket), start=1)
    ]


def scene(
    bracket: Bracket,
    names: Mapping[int, str],
    words: Words,
    extras: Mapping[str, Extra] | None = None,
) -> Scene:
    extras = extras or {}
    sets = drawn_sets(bracket)
    elimination = bool(sets) and all(one.side in (WINNERS, LOSERS, GRAND, THIRD) for one in sets)
    layout = None
    boxes: tuple[Box, ...] = ()
    headings: list[tuple[str, int, float, str]] = []
    tables: list = []
    if elimination and (bracket.format in ELIMINATION or bracket.plan is not None):
        layout = elimination_layout(sets)
        by_key = {one.key: one for one in sets}
        boxes = tuple(box_of(by_key[n.key], names, extras.get(n.key)) for n in layout.nodes)
        seen: set[tuple[str, int]] = set()
        for n in layout.nodes:
            if (n.side, n.col) in seen:
                continue
            seen.add((n.side, n.col))
            if n.side == LOSERS:
                top = layout.losers_top or 0.0
            elif n.side in (GRAND, THIRD):
                top = n.y - 0.5
            else:
                top = 0.0
            headings.append((n.side, n.col, top, words.rounds.get(n.key, "")))
    elif bracket.plan is not None:
        tables = pool_tables(bracket, names, words)
    else:
        tables = [("", rows_of(bracket, names))]
    return Scene(
        title=words.title,
        subline=SEP.join(part for part in (words.format, words.state) if part),
        kind=words.kind,
        champion=words.champion,
        held=words.held,
        heads=tuple(words.heads),
        layout=layout,
        boxes=boxes,
        headings=tuple(headings),
        tables=tuple(tables),
        count=len(bracket.entrants),
    )


def fingerprint(made: Scene) -> str:
    return hashlib.sha256(repr(made).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Size:
    col: int
    gap: int
    name: int
    small: int
    head: int
    box: int
    unit: int
    pad: int


def tree_size(cols: int, count: int) -> tuple[int, Size]:
    cols = max(cols, 1)
    gap = 40 if cols <= 5 else 28
    room = WIDE - 2 * MARGIN
    col = min(MOST_COL, (room - (cols - 1) * gap) // cols)
    if count < SMALL_FIELD:
        col = NATURAL_COL
    by_rounds = {1: 32, 2: 32, 3: 30, 4: 28, 5: 26, 6: 24}.get(cols, 22)
    name = max(18, min(by_rounds, col // 7))
    small = max(15, round(name * 0.72))
    pad = max(6, name // 3)
    box = pad * 2 + round(small * 1.15) + 2 * round(name * 1.15)
    unit = box + max(14, name // 2)
    width = WIDE if count >= SMALL_FIELD else 2 * MARGIN + cols * col + (cols - 1) * gap
    return width, Size(col, gap, name, small, round(small * 1.05), box, unit, pad)


def title_band(made: Scene, width: int) -> tuple[int, int]:
    big = 46 if width >= WIDE else 38
    lines = 2 + (1 if made.champion else 0)
    return big, MARGIN + big + 10 + (lines - 1) * round(big * 0.75) + 18


def draw_title(canvas: ImageDraw.ImageDraw, made: Scene, width: int, big: int) -> None:
    room = width - 2 * MARGIN
    y = MARGIN
    canvas.text(
        (MARGIN, y), fitted(made.title, font(big, True), room), font=font(big, True), fill=FG
    )
    y += big + 10
    sub = font(round(big * 0.62))
    x = MARGIN
    if made.kind:
        pill = font(round(big * 0.55), True)
        text = fitted(made.kind, pill, room / 3)
        w = pill.getlength(text) + 24
        h = round(big * 0.62) + 10
        canvas.rounded_rectangle(
            (x, y - 2, x + w, y - 2 + h), radius=h // 2, outline=ACCENT, width=2
        )
        canvas.text((x + 12, y + 1), text, font=pill, fill=ACCENT)
        x += w + 14
    canvas.text((x, y), fitted(made.subline, sub, width - MARGIN - x), font=sub, fill=MUTED)
    if made.champion:
        y += round(big * 0.75)
        face = font(round(big * 0.66), True)
        canvas.text((MARGIN, y), fitted(made.champion, face, room), font=face, fill=GOLD)


def border_of(state: str) -> tuple[int, int, int]:
    return {
        READY: blend(INFO, 0.5, HAIRLINE),
        CALLED: WARN,
        REPORTED: INFO,
        DISPUTED: DANGER,
    }.get(state, HAIRLINE)


def draw_box(
    canvas: ImageDraw.ImageDraw, box: Box, x: int, top: int, size: Size, held: str
) -> None:
    quiet = box.state in QUIET_STATES
    tone = (lambda c: blend(c, QUIET)) if quiet else (lambda c: c)
    canvas.rounded_rectangle(
        (x, top, x + size.col, top + size.box),
        radius=8,
        fill=tone(SURFACE),
        outline=tone(border_of(box.state)),
        width=2,
    )
    inner = size.col - 2 * size.pad
    small = font(size.small)
    y = top + size.pad
    tag = fitted(held, small, inner / 2) if box.held and held else ""
    tag_w = small.getlength(tag) + (8 if tag else 0)
    canvas.text(
        (x + size.pad, y), fitted(box.top, small, inner - tag_w), font=small, fill=tone(MUTED)
    )
    if tag:
        canvas.text(
            (x + size.col - size.pad - small.getlength(tag), y), tag, font=small, fill=tone(WARN)
        )
    y += round(size.small * 1.15)
    for slot in (box.a, box.b):
        face = font(size.name, slot.won)
        colour = FG if not slot.lost else MUTED
        score_w = face.getlength(slot.score) if slot.score else 0
        room = inner - score_w - (10 if score_w else 0)
        canvas.text((x + size.pad, y), fitted(slot.name, face, room), font=face, fill=tone(colour))
        if slot.score:
            canvas.text(
                (x + size.col - size.pad - score_w, y), slot.score, font=face, fill=tone(colour)
            )
        y += round(size.name * 1.15)


def render_tree(made: Scene) -> Image.Image:
    layout = made.layout
    assert layout is not None
    width, size = tree_size(layout.cols, made.count)
    big, band = title_band(made, width)
    head_room = size.head + 14
    height = band + head_room + round(layout.height * size.unit) + MARGIN
    image = Image.new("RGB", (width, height), BG)
    canvas = ImageDraw.Draw(image)
    draw_title(canvas, made, width, big)
    used = layout.cols * size.col + (layout.cols - 1) * size.gap
    left = max(MARGIN, (width - used) // 2)
    top = band + head_room

    def x_of(col: int) -> int:
        return left + col * (size.col + size.gap)

    def y_of(row: float) -> int:
        return top + round(row * size.unit)

    at = {n.key: n for n in layout.nodes}
    boxes = {one.key: one for one in made.boxes}
    for start, end in layout.links:
        a, b = at[start], at[end]
        x1, y1, x2, y2 = x_of(a.col) + size.col, y_of(a.y), x_of(b.col), y_of(b.y)
        mid = x1 + min(size.gap // 2, (x2 - x1) // 2)
        done = boxes[start].state == COMPLETE
        colour = blend(MUTED, DONE_LINE) if done else HAIRLINE
        canvas.line([(x1, y1), (mid, y1), (mid, y2), (x2, y2)], fill=colour, width=3)
    face = font(size.head, True)
    for _, col, row, text in made.headings:
        canvas.text(
            (x_of(col), y_of(row) - size.head - 10),
            fitted(text.upper(), face, size.col),
            font=face,
            fill=MUTED,
        )
    for n in layout.nodes:
        draw_box(canvas, boxes[n.key], x_of(n.col), y_of(n.y) - size.box // 2, size, made.held)
    return image


def render_tables(made: Scene) -> Image.Image:
    width = WIDE if made.count >= SMALL_FIELD else TABLE_NARROW
    big, band = title_band(made, width)
    name = 30
    row_h = 48
    head = font(22, True)
    rows = sum(len(rows) + 1 for _, rows in made.tables) + sum(1 for t, _ in made.tables if t)
    height = band + rows * row_h + len(made.tables) * 20 + MARGIN
    image = Image.new("RGB", (width, height), BG)
    canvas = ImageDraw.Draw(image)
    draw_title(canvas, made, width, big)
    room = width - 2 * MARGIN
    cols = (MARGIN, MARGIN + 80, MARGIN + room - 260, MARGIN + room - 110)
    y = band
    for heading, rows_ in made.tables:
        if heading:
            canvas.text(
                (MARGIN, y), fitted(heading, font(28, True), room), font=font(28, True), fill=FG
            )
            y += row_h
        for x, text in zip(cols, made.heads, strict=False):
            canvas.text((x, y + 12), str(text).upper(), font=head, fill=MUTED)
        y += row_h
        canvas.line([(MARGIN, y - 4), (MARGIN + room, y - 4)], fill=HAIRLINE, width=2)
        for at, row in enumerate(rows_):
            if at % 2:
                canvas.rectangle((MARGIN, y - 2, MARGIN + room, y + row_h - 6), fill=SURFACE)
            top = row.rank == "1" and not row.out
            face = font(name, top)
            colour = MUTED if row.out else FG
            canvas.text((cols[0], y + 4), row.rank, font=face, fill=GOLD if top else colour)
            canvas.text(
                (cols[1], y + 4),
                fitted(row.name, face, cols[2] - cols[1] - 20),
                font=face,
                fill=colour,
            )
            canvas.text((cols[2], y + 4), row.record, font=face, fill=colour)
            canvas.text((cols[3], y + 4), row.points, font=face, fill=colour)
            y += row_h
        y += 20
    return image


def png(image: Image.Image) -> bytes:
    out = BytesIO()
    image.save(out, format="PNG", optimize=False, compress_level=6)
    return out.getvalue()


def render(made: Scene) -> bytes:
    return png(render_tree(made) if made.layout is not None else render_tables(made))


def draw(
    bracket: Bracket,
    names: Mapping[int, str],
    *,
    words: Words,
    extras: Mapping[str, Extra] | None = None,
) -> bytes:
    return render(scene(bracket, names, words, extras))


__all__ = [
    "Extra",
    "Scene",
    "Words",
    "draw",
    "elimination_layout",
    "fingerprint",
    "render",
    "scene",
]
