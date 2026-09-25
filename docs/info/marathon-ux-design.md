# The Events page, made plain — three sections, one Schedule card first in the marathon drawer, one Next up, and "BaF" where it said "ours"

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **DESIGN (Fable, 2026-09-25 16:3x Phoenix),
> dispatched to Opus as branch `marathon-ux`** off `main` (v165 live 16:15). **Last verified: 2026-09-25 16:2x** — by
> LOOKING, in Chrome against the local mock on `main` (`http://localhost:8797/events.html`, the AGDQ 2027 drawer
> `#marathon-1`): the drawer's header line is `ON NOW · 9/25/2026, 11:12:21 AM – 9/25/2026, 11:32:21 PM · GDQ tracker ·
> the schedule · last read 20m ago`, then a moves bar *Refresh now · Pause · [Re-read every ___] Save · minutes ·
> Refresh the board · Remove* whose interval field's label wraps onto two lines around the box; then **Event** (a
> badge line *Event #5 — approved*, *Added by the GDQ feed.*, an `Event` select on *Both*, a FIVE-line help paragraph,
> a second two-line paragraph about mode changes, then *Open event #5 · Unlink*); then **Runs**; **Who is who**; **The
> channel** (*Airs on* select, help, the ping-window line, *Save the channel*). On the section: a four-line intro, the
> **Feeds** card with eight controls per row (an Add/Suggest segment, an Event select, Pause, Check now, Forget
> ignored, Rename…, Move to channel…, Remove), a **Next up** card under it, then the marathon table with a *Next up*
> column of its own carrying Add it / Not this one — TWO things called Next up on one screen. Code: `site/public/assets/
> marathons-section.js` (the section, the drawer, the Feeds card — one file), `cogs/content/marathon.py` + `marathon_feeds.py`
> + `marathon_events.py` (the `/event` ▸ Marathons… cards), `site/mock/server.mjs` (the seeded rows). ⚠️ Secret NAMES only.

## The ask, verbatim (owner, 2026-09-25 16:2x Phoenix)

*"the ui is confusing now in the modal, and i dont see where we're scanning for schedules."* — then, 16:3x: *"i think
the whole events page and the marathon modal are confusing to look at."* and *"and for marathon highlights don't say
ours say BaF as the category"*.

**What is wrong, named:** (1) the thing the feature IS — a schedule the bot re-reads — has no card of its own; it is a
grey header fragment (*last read 20m ago*) and a *Refresh now* button lost in a bar. (2) The **Event** card comes
first and carries seven lines of explanation for one select. (3) The moves bar mixes a form field into a row of
buttons. (4) Two *Next up*s. (5) Eight controls on every feed row.

## A0. The page — six sections become three

Today `events.html` stacks SIX sections: Queue · Marathons (a four-line intro, the Feeds card with eight controls a row,
a Next up card, Add a marathon, the table with its own Next up column) · Settings · Marathon settings · Events log ·
Marathons log — and the *On this page* rail lists all six. After:

1. **Events** (the queue, renamed from *Queue*): one-sentence intro; the status select and the table as built. The
   sticky bar and the row moves are fine; nothing else changes here.
2. **Marathons**: one-sentence intro + the shadow badge line; the **table FIRST** (it is what staff come to read):
   *Marathon · Dates · State · BaF runs · Schedule · Event* — six columns, no Next up column (§B); then **Add a
   marathon**; then ONE strip line *N marathons have a next event waiting* when true; then a **Sources** foldout
   (`foldout()`, shut by default, titled *Where marathons come from · 2 sources · next check in 5 h 41 min*) holding
   the feed rows of §B and their open suggestions. The feeds are the plumbing; the marathons are the point.
3. **Settings and logs**: ONE section (the pattern `golive.html` uses: *Settings and logs*), whose body is the two
   settings foldouts (*Events* · *Marathons*, each the existing namespace drawer) followed by ONE log list with a
   feature chip pair **Events / Marathons** (the Logs page's chip pattern) — instead of two settings sections and two
   log sections.

The rail then reads *Events · Marathons · Settings and logs*. Deep links keep working: `#detail` (an open event),
`#marathon-<id>` (a marathon drawer), and the settings anchors the Settings page's *Find* uses (keep every existing
`id`).

## A1. "BaF", never "ours"

Everywhere a person READS the word — the *Ours* chip becomes **BaF**, the *Ours* column **BaF runs**, *3 of ours* →
**3 BaF**, *Ours next* (the `/event` ▸ Marathons… member view) → **BaF next**, *runs of ours* → **BaF runs**, the run
row highlight's label → **BaF**, the board's default templates (`marathon_board_template`, `marathon_board_line_template`,
`marathon_board_empty_line`) and the reminder / shout defaults wherever they say *ours* → **BaF** (they are keys, so
the DEFAULT changes and a stored value is left alone — say in Deviations which defaults changed), the run-event title
template default likewise, and the Discord card lines. Code names (`is_ours`, `ours`) are NOT renamed — the word a
person reads is the rule, not the identifier. One constant `BAF = "BaF"` in `black_bloc/marathon.py` and one in
`marathons-section.js`, used everywhere, so the next rename is one line.

## A. The drawer, in this order — nothing removed, everything given its place

1. **Schedule** — the first card, the answer to *where are we scanning*:
   - line 1: *Read from the **GDQ tracker** — [the schedule ↗]* (source words + the link); when a feed made it:
     *· found by the GDQ feed* on the same line.
   - line 2, the reading: *Last read 20 min ago · next read in 10 min · every 30 min while it is near, every 24 h
     when it is far* — from the row's `last_fetched_at`, the cadence the cog uses (`poll_minutes` or the key, near/far by
     `marathon_lead_days`), rendered by ONE helper `readingLine(row)`; when the last read failed: *Could not be read
     since 24 Sep 22:12 — the GDQ tracker has the event but has not published its schedule yet; read again in 10 min*
     (the row's `last_error`, already worded), in the warn tone.
   - line 3, what it holds: *11 runs · 3 BaF · 2 done · 1 on now* or *No runs yet — nothing published.*
   - the field: **Re-read every** `[ 30 ]` **minutes** — one `field()` with the label on the left, the box, the unit
     word and a quiet *blank = the default (30)* help, and **Save**; never inline in a button bar.
   - the moves: **Read it now** (the old *Refresh now*), and nothing else here.
2. **Runs** — as built, with the chips **BaF / All** (§A1), the table, the run moves.
3. **Who is who** — as built.
4. **Event** — one state line (*Event #5 — approved · [Open ↗] · Unlink* / *No event.* / *Waiting for the schedule to
   publish, then one event for the marathon.*), the `Event` select with ONE sentence of help (*Which Discord events this
   marathon makes; the setting explains the four choices.*), and **Make an event now** when the mode has none. The two
   explanation paragraphs move OUT of the drawer: the long one becomes the `marathon_event_mode_default` key's help
   text on the Settings page (it is already close to it), the mode-change one goes to `code-notes`.
5. **The channel** — as built (*Airs on*, the ping-window line, Save).
6. **Posts** — one quiet line per post the marathon owns: *Board: posted 12 min ago in #live-now [Refresh the board]*
   / *no board yet*; *Reminders: 2 sent · Shoutouts: 1* (counts from the runs); this is where *Refresh the board* lives.
7. The **moves bar**, LAST: **Pause** / **Resume** · **Remove** (danger tone, confirm). Two buttons, nothing else.

The header line keeps the state badge and the dates only.

## B. The section — one Next up, lighter rows

- The intro is the one sentence of §A0; the *Marathon posts are in shadow…* line stays.
- The feeds live in the **Sources** foldout of §A0, titled **Where marathons come from**. A feed ROW shows: Channel · Source · *every 6 h · last
  19 min ago · next in 5 h 41 min* (the same `readingLine` shape) · New events **Add / Suggest** · **Check now** ·
  **Pause**/**Resume**. Everything else — the Event select, Rename…, Move to channel…, Forget ignored (N), Remove — moves
  into a **feed drawer** the row opens (rows open drawers everywhere on this site), with the feed's own reading line
  and its open suggestions.
- **One Next up.** The marathon table LOSES its *Next up* column and its per-row Add it / Not this one. A suggestion
  from a feed renders under the feeds card as today; a suggestion from a marathon ending (the next-event build) renders
  inside THAT marathon's drawer, in the Schedule card as a last line (*When this ends: the next GDQ event is Halo Fest,
  23 Oct — Add it · Not this one · Look again*), and as the strip *N marathons have a next event waiting* above the
  table. The table's *Read* column becomes **Schedule**: *read 19 min ago* / *not published — again in 10 min* /
  *could not be read — again in 10 min* (short; the full reason is in the drawer).
- The **Add a marathon** form is unchanged.

## C. `/event` ▸ Marathons… mirrors the order

The picked marathon's card lines run: *Schedule:* (source · last read · next read · runs count) first, then *Runs*,
*Event*, *Channel*, *Posts*; the buttons keep their functions and gain the same names (*Read it now*, *Refresh the
board*). The Feeds… select's feed card shows the reading line first. No new commands, modals or moves.

## D. Words and keys

Card titles, column headings and the one-sentence helps are constants (panel and page words). The reading line's
pieces (*Last read {ago}*, *next read in {in}*, *every {n} min while it is near*, *Could not be read since {when} —
{reason}; read again in {in}*, *No runs yet — nothing published.*) are constants too — they are read on the site and
in the panel, never posted to a channel. No new keys; no schema; no routes (the API rows already carry
`last_fetched_at`, `last_error`, `poll_minutes`, the run counts — if `next_read_at` is missing from the row, add it to
`GET /api/marathons` and the contract rather than computing it twice).

## E. Tests, docs, gate

`site/mock/*.test.mjs` — a `marathons-join` or layout fixture if one exists for the section; otherwise `check.mjs` +
a headless render of `events.html` and `events.html#marathon-1` with zero console errors, and the drawer's card ORDER
asserted in a node test if the section exports its builder (make it export `drawerCards(row)` returning the titles in
order, and test that). `tests/cogs/content/test_marathon.py` for the panel card's line order. `check.mjs`, the six node
tests, `ruff`, both `pytest -n 8` orders. Docs: `code-notes.md`; this doc's foot; `docs/info/README.md` (one row);
one dated line at the top of `marathon-schedule-design.md`, `marathon-next-event-design.md`, `marathon-feeds-design.md`,
`marathon-event-modes-design.md` (the page and panel shapes moved); `sweeps.md` rows `MX-a…` (a: the page has three sections
and the rail says so; b: open a marathon → Schedule is the first card and says the source, last read, next read; c: the
interval field saves; d: the table has one Next up strip and no Next up column; e: the Sources foldout opens to the feed
rows and a row opens its drawer; f: not one *ours* is left on the page or in `/event` ▸ Marathons…, and the board's
default says BaF). NOT `TODO.md` /
`DONE.md` / `deploys.log` / `KNOWN_ISSUES.md`.

## Deviations

*(the build agent writes this)*

## What was NOT verified

*(the build agent writes this)*
