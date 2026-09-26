# The Events page, made plain — three sections, one Schedule card first in the marathon drawer, one Next up, and "BaF" where it said "ours"

> ➕ **2026-09-25 (branch `marathon-people`, 🔨 BUILT, NOT MERGED): the drawer is now Schedule · People · Event · The channel · Posts** — *Runs* and *Who is who* fold into **People** (BaF on top, the schedule by day and slot), the *Where marathons come from* foldout became a **Sources…** drawer and the table gained a **Source** column. [`marathon-people-design.md`](marathon-people-design.md).

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

*(build agent, branch `marathon-ux`, 2026-09-25 — BUILT, not merged, not deployed)*

1. **The JS `BAF` constant lives in a new pure module, `site/public/assets/marathon-words.js`**, which
   `marathons-section.js` imports — not in `marathons-section.js` itself. Why: §E asks for the drawer's card order in a
   node test, and `marathons-section.js` touches `window`/`document` at import. The module holds `BAF`, the card
   titles, `readingLine`, `scheduleCell`, `countsLine`, `feedReading`, `sourcesTitle`, `postsLines`, `drawerCards()`;
   `site/mock/marathon-words.test.mjs` (8 tests) proves them and is wired into `ci.yml` and `deploy.ps1`.
2. **`settings_store.py` spells "BaF" literally** in the registry defaults and helps: it cannot import
   `black_bloc/marathon.py` (that module imports `settings_store`). Every other Python use goes through `mt.BAF`.
3. **The Sources foldout opens itself while a feed suggestion waits** (shut otherwise, as §A0 says). A decision
   waiting on staff must not be folded away; the foldout's title still says how many sources and when the next check is.
4. **Template DEFAULTS that changed** (registry AND mock; stored values untouched): `marathon_board_template`
   (*our people on the schedule* → *BaF on the schedule*), `marathon_board_empty_line` (*Nobody from here* → *Nobody
   from BaF*), `marathon_event_description_template` (*Our runs are boarded* → *BaF runs are boarded*). The reminder,
   shoutout, done and run-event title/description defaults never said *ours*, so they are unchanged (their HELP text
   and labels now say *BaF run*). Also renamed where people read them: the event-mode words (*An event per BaF run*),
   `/event` ▸ Marathons… member view **BaF next** / *Nobody from BaF…*, the refresh/add replies (*N of them BaF*), the
   not-shoutable and not-ours refusals, the events card's *Marathon: … — N BaF run(s)*, the events `not_ours` reason,
   the persona's description of the panel, and `labels.js`.
5. **Posts card has no "posted 12 min ago"**: the row carries no board-posted time and §D allows one row field, which
   went to `next_read_at`. The card says *Board: up (and pinned) in #channel* / *Board: none yet.*, the counts line, and
   **Refresh the board** / **Post the board**.
6. **Cadence words come from `/api/settings`**, not the row: `marathon_poll_minutes` and `marathon_far_poll_hours` are
   read once per page load (`readCadence`). `next_read_at` is the one field added (API, mock, contract) and the cog's
   `fetch_due` now uses the same `mt.next_read_at`.
7. **The next-event line in the Schedule card is prefixed *After this one:*,** not *When this ends:* — the suggestion
   only exists once the marathon IS over, so "when this ends" read wrong on the page.
8. **The event state line** shows the status badge + *Event #5* + **Open ↗** + **Unlink** on one line (not *Event #5 —
   approved*: the badge already says approved).
9. **Settings and logs** uses three `foldout()`s (Events · Marathons · Log) inside one section, the Posts/Raid-trains
   pattern; the Log holds a two-chip switch **Events / Marathons**, not an *All* chip. Old ids are kept: the section is
   `#sect-settings`, the marathons foldout `#sect-marathon-settings`, the log holders `#sect-logs-events` /
   `#sect-logs-marathon`, the Events (queue) section `#sect-queue`.
10. **The table drops the *Channel* column** (§A0 lists six columns without it); the channel is in the drawer.
11. **The feed row's name is the Channel cell**, a text action that opens the feed drawer; the drawer also lists the
    marathons the feed added (each opens its drawer) and repeats the row's open suggestions.
12. **Commit shape**: the drawer, the three sections and the feed drawer landed as one commit (`93b778fd`) — they are
    one file's rewrite (`marathons-section.js`) plus `page-events.js`; splitting would have left a half-built drawer.
13. **Panel (§C)**: the picked marathon's card now reads a head line (*phase · dates*), **Schedule:** *[GDQ tracker](link)
    · last read · next read · N run(s), N BaF*, the re-read line when set, the next-event line when over, then **Runs**,
    **Event** (+ the mode line), **Channel:**, **Posts:**. *Refresh now* is **Read it now** on the panel too. The
    staff root list line (`MARATHON_LINE`) keeps its shape with *N BaF of M*.

## What was NOT verified

- **Not against the real bot or Discord.** Every render was the local mock (`MOCK_PORT=8799`) in
  `chrome-headless-shell` 149 over raw CDP; the `/event` ▸ Marathons… card was checked only by the test suite (embed
  text), never looked at in a Discord client.
- **Not every move was pressed in the browser.** Pressed and seen: **Save** on *Re-read every* (20 → reading line said
  *every 20 min*, next read moved), opening a feed drawer from its row, opening drawers by deep link (`#marathon-1`,
  `#marathon-4`). NOT pressed: Read it now, Pause/Resume, Remove, Unlink, Make an event now, the Event select, the
  board button, feed Check now / Pause / Rename / Move / Forget ignored / Look again / Remove, Add it / Not this one.
  Their routes and payloads are unchanged from `main` (the same `send()` calls, moved), and `check.mjs` exercises the
  routes themselves.
- **Stored values with the old *ours* wording** on the live database are untouched by design; nothing checks the live
  store for them.
- **Light theme and other themes** were not rendered; only the default dark *blackbloc* theme at 1400 px and 390 px.
- **The rail count** beside *Settings and logs* shows a number the section does not set (inherited from the shared
  `mountSections` paint); not investigated.
- **`next_read_at` under a real clock**: proved by `tests/test_marathon.py::test_the_next_read_is_the_last_read_plus_the_gap_fetch_due_uses`
  and the existing `fetch_due` tests, not by watching a live tick.
