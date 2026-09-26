# The marathon drawer, lightened — a two-line header, People as the body, settings folded, one moves bar

> ✅ **2026-09-25 — LIVE as v166 19:30** (merge `213fe142`; release commit `b06d4f1d`; boot `database ready` 02:30:22Z, `logged in` 02:30:27Z, no Traceback, `/health` 65 ms — `deploys.log`'s v166 line). No browser opened the live drawer; sweeps `ML-a`…`ML-d` are the owner's.
>
> 🔨 **BUILT 2026-09-25 on branch `marathon-drawer-lite` (worktree `C:/lcw/bb-marathon-drawer-lite`), NOT MERGED, NOT DEPLOYED** — see *Deviations* and *What was NOT verified* at the foot.

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

*(build agent, branch `marathon-drawer-lite`, 2026-09-25 — 🔨 BUILT, NOT MERGED, NOT DEPLOYED; commits `d8a962a7` (site),
`7e3108f5` (panel), `9798ce99` (the next strip's spacing), then docs.)*

1. **Measured drawer height (`.drawer-body` scrollHeight, AGDQ 2027, mock, everything at its default fold):**
   **1400 px: 2177 → 1290 px (−41 %)**; **390 px: 3438 → 2516 px (−27 %)**; visible text lines 123 → 107 (the day folds
   are unchanged and are most of what is left). With one BaF line and Settings both opened: 1650 px at 1400.
2. **One Save sends only what changed.** The Event select no longer saves on change (it did in the Event card); it waits
   for the one Save with the channel and the interval. A PATCH carrying an unchanged field would re-run that field's
   side effects, so unchanged fields are left out; with nothing changed Save says *Nothing changed, so nothing was
   saved.* The route applies fields one after another — if a later field is refused, an earlier one has already landed
   (the redraw shows the truth). No new route.
3. **The event's state and its move sit inside Settings**, under the Event select: *APPROVED Event #5 Open ↗ · Unlink* /
   *Waiting for the schedule… · Unlink* / *No event. · Make an event now*. The header shows the event only when one is
   linked (per §A); the moves had to live somewhere, and Settings is where the event is decided.
4. **Header dates** read `Fri 25 Sep 14:00 – Sun 27 Sep 23:00` in the guild's zone (the People answer's `timezone`, the
   same one the day folds use) — new pure `datesWords`. The list table still uses the old `datesOf`.
5. **Channel as a link** goes to `golive.html#streamers`, not its row (no per-row anchor exists). A channel gone from
   Go-live puts *its channel is gone from Go-live* (warn) in that place; the full sentence stays inside Settings.
6. **The next-event strip** (an over marathon's *After this one…* with Add it / Not this one / Look again) sits right
   under the two header lines, not in Settings — a decision for staff is never folded (`marathon-ux` Deviation 3).
7. **The People card keeps its *People* title and the *BaF · N* / *The schedule* heads**; only the intro sentence went.
   The BaF line's part word (*runner*, *runner, host*, *on commentary*) sits at the right end. At 390 px a person with two
   runs wraps to three lines (name, then the chips) — still one row that opens.
8. **Words retired from `marathon-words.js`:** `countsLine`, `postsLines`, `drawerCards` and the `CARD_SCHEDULE / EVENT /
   CHANNEL / POSTS` constants; `drawerParts`, `headerReading`, `headerCounts`, `postsLine`, `datesWords` added, all
   node-tested. `readingLine` stays (the warn sentence).
9. **CSS** in `site/public/assets/site.css`'s marathon block (`.mx-head`, `.mx-head-quiet`, `.mx-dot`, `.mx-next`,
   `.mx-settings`, `.mx-posts`, the `details.mx-person` rules replacing the old flex card). The brief listed JS files
   only; the look needed these. `event-drawer` may touch `site.css` too — expect a trivial merge.
10. **Panel (§C):** `card_header` gives `phase · dates · [source](url)` then `last read · next read · N run(s), M BaF ·
    every N min (own gap only) · Event #N — status (linked or waiting only) · twitch.tv/login`; then the BaF run lines
    (the *Runs* head went); then `**Posts:** …`. Gone: the *Runs*/*Event*/*Channel* heads, the *Event mode:* line
    (`marathon_events.EVENT_MODE_LINE` removed — the Event mode select shows the choice) and the POLL_SAVED sentence on
    the card. Buttons unchanged. Three tests rewritten to the new shape.
11. **Commit shape**: one site commit (header, BaF lines, Settings, posts, moves together — they share `marathonDrawer`),
    one panel commit, one spacing fix, one docs commit — not the five boundaries the brief listed.

## What was NOT verified

- **Nothing met Discord.** The panel card was checked only by the test suite (embed text and the buttons drawn).
- **Rendered** in `chrome-headless-shell` 149.0.7827.22 over raw CDP against this worktree's mock (`MOCK_PORT=8804`),
  dark theme only, zero console errors on every render: `#marathon-1` before/after at 1400 and 390, `#marathon-2`
  (over, with the next strip), `#marathon-3` (paused, failed read — the warn sentence in the header), `#marathon-4`.
  **Pressed:** Save with the interval 45 and again blank (drawer and foldout stayed open; *AGDQ 2027 is re-read on the
  default gap again.*); a BaF line's **Spotlight…** ▸ **Spotlight them** (the line stayed open and read *Spotlit until …
  · Open on Go-live ↗ · Stop spotlighting*). **Not pressed:** Save with the Event select or the channel changed, Save
  with nothing changed, Unlink / Make an event now in Settings, Refresh the board, Read it now, Pause, Remove, Stop
  spotlighting, the *feed* and channel links. Their routes are unchanged and `check.mjs` still passes.
- **Light theme, a browser zone other than the guild's, and a GDQ-sized schedule** were not rendered.
- **The merge with `event-drawer`** (parallel, `page-events.js` + possibly `site.css`) was not tried.
