# The marathon drawer, lightened — a two-line header, People as the body, settings folded, one moves bar

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **DESIGN (Fable, 2026-09-25 18:1x Phoenix),
> dispatched to Opus as branch `marathon-drawer-lite`** off `main` `ac4e79e2` (v165 live; v166 merged, undeployed;
> `event-drawer` building in parallel on `page-events.js` — this build touches `marathons-section.js` and
> `marathon-words.js` only, plus docs). **Last verified: 2026-09-25 18:1x** — by LOOKING in Chrome on the mock
> (`http://localhost:8797/events.html#marathon-1`, AGDQ 2027, three screens tall): **Schedule** card (a source line, a
> reading line, a counts line, the *Re-read every* field with its own help line, **Read it now**), **People** (an intro
> sentence; the BaF block at THREE lines per person — name/@/login/part, the run chips, *matched by their Twitch link ·
> Spotlight…*; then *THE SCHEDULE* with a filter box and the day foldouts — those are compact and right), **Event** card
> (badge line, a select, a help sentence), **The channel** card (a select, a two-line help, the ping-window line, **Save
> the channel**), **Posts** card (the board line + button, the counts line), then **Pause** / **Remove**. Code:
> `site/public/assets/marathons-section.js` (`drawerCards`, `scheduleCard`, `peopleCard`, `eventCard`, `channelCard`,
> `postsCard` — names as the `marathon-ux` / `marathon-people` builds left them), `marathon-words.js` (`readingLine`,
> `BAF`), `ui.js` (`foldout`, `card`, `field`, `textAction`, `chip`). ⚠️ Secret NAMES only.

## The ask, verbatim (owner, 2026-09-25 18:1x Phoenix)

*"The whole modal for a marathon is a lot, can we rework it"*

## A. The shape — five things, in this order, most of them one line

1. **The header block** (replaces the Schedule card): two lines under the title.
   - line 1: `ON NOW` · `Fri 25 Sep 12:59 – Sat 27 Sep 09:59` · **GDQ tracker ↗** (the schedule link) · *feed* (when a
     feed made it — a link to that feed's drawer).
   - line 2, quiet: `read 24 min ago · next in 6 min` · `16 runs · 5 BaF` · `Event #5 approved ↗` (when one exists,
     else nothing) · `gamesdonequick` (the channel, as a link to its Go-live row) — and, when the schedule cannot be read,
     the warn-tone reason INSTEAD of the reading words (the `readingLine` helper already has both).
   - No field, no help lines, no counts card. The cadence words (*every 30 min while it is near…*) go to the Settings
     foldout's help.
2. **People** — the body, unchanged in structure, lighter per person:
   - the intro sentence goes (the foldout titles say what the blocks are);
   - the BaF block is **one line per person**: avatar · display name · `@discord` · the run chips (the on-now one lit,
     done dimmed) · a small *runner* / *host* word — and the line is a **row that opens** (the same `<details>` the slots
     use): open, it shows `twitch.tv/login`, *matched by their Twitch link* / *linked by staff*, **Unlink**, **Spotlight…**
     / *Spotlit until … · Stop spotlighting*. Closed by default.
   - the day foldouts and slot rows stay exactly as built (they are the right density); the filter box stays above them.
3. **Settings** — ONE shut `foldout` titled *Settings for this marathon* holding, as plain `field()` rows with one-line
   helps: **Event** (the mode select), **Airs on** (the channel select + the ping-window line), **Re-read every** (the
   minutes field), and one **Save** for the three. The two-line and three-line help paragraphs go; each key's full
   help stays on the Settings page where it already is.
4. **Posts** — one quiet line, no card: *Board pinned in #announcements · 2 reminders · 1 shoutout · [Refresh the board]*
   (a `textAction`), or *No board yet*.
5. **The moves bar**, last: **Read it now** · **Pause** / **Resume** · **Remove** (danger, confirm).

Every write keeps the drawer open and redraws it (the existing helper). Deep links, the People routes, Spotlight…,
Link to a member…, the slot view — all unchanged in function.

## B. Why this and not tabs

Tabs would hide the schedule behind a click; the drawer's job is the people and the days, so they stay in view and
everything else shrinks to a line or folds. Measured on the mock: the drawer's fixed chrome (everything that is not a
person or a slot) drops from about 40 lines to about 8.

## C. `/event` ▸ Marathons… mirrors it

The picked-marathon card's lines: the two header lines first (state · dates · source · reading · counts · event ·
channel), then the BaF lines, then the buttons as today. The settings moves stay where they are (Event mode…, Re-read
every…, the channel). No new moves.

## D. Words, keys, tests, docs, gate

Page words are constants; no keys, routes or schema. `node --check`, the node tests (`marathon-words.test.mjs` if a
word moved), `check.mjs`, a headless render of `#marathon-1` at 1400 and 390 px with zero console errors — LOOK, and
put the before/after height in Deviations. `ruff` + one `pytest -n 8` for the panel change. Docs: `code-notes.md`;
this doc's foot; `docs/info/README.md` (one row); one dated line at the top of `marathon-ux-design.md` and
`marathon-people-design.md`; `sweeps.md` rows `ML-a…` (a: a marathon opens on two header lines and People; b: a BaF
line opens to its moves; c: Settings is shut and Save keeps the drawer open; d: the moves bar is last). NOT `TODO.md` /
`DONE.md` / `deploys.log` / `KNOWN_ISSUES.md`.

## Deviations

*(the build agent writes this)*

## What was NOT verified

*(the build agent writes this)*
