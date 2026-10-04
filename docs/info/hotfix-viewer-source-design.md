# Hotfix viewer source — a second Hotfix source: hosts' Twitch names and the event's own schedule sheet

> **Audience:** the conductor, reviewers and the next session touching Hotfix marathons, hosts or the stream re-time.
> **Status:** TRACKED · 🔨 **BUILT on branch `hotfix-viewer-source`** (off `main` `0e74f624`; commits `5115e796`
> layer 1, `4026bca2` layer 2, `6a98799a` layer 3, then this docs commit) — **NOT merged, NOT deployed, nothing has met
> Discord or Fly.** Schema **84 → 85**, registry keys **706 → 712**, contract routes **288 → 290** (one new route, one
> more contract entry for an existing PATCH).
> **Last verified: 2026-10-03 ~20:50 Phoenix** — by the suite (`9934 passed, 3 skipped`), `node site/mock/check.mjs`
> on a mock started from the worktree (`22 pages, 290 routes, 26 core settings, all keys present`), a real browser
> render of both drawers on that mock, and **one live read with the bot's own client** (`ScheduleClient.viewer` over
> aiohttp, `BROWSER_AGENT`) from this machine — see *Measured live*.
> ⚠️ **NOT checked:** anything from Fly (KI-30's datacenter wall is untested on `ogndrahcir.github.io`,
> `script.google.com`, `gdq.gg`), anything against Discord (the seventh thread button, the re-dated events, the
> reminders), the live database and its migration, the live settings, which BaF members are actually paired or linked
> on the live server, rate limits. Secret NAMES only — there are none here.

> ⚠️ **2026-10-03 ~21:40 — merged with `main` `c2ba3251` (v195) and four review fixes applied; see *Merge + review
> fixes 2026-10-03* at the end.** Where that section and an earlier one disagree, IT wins: keys are **727**, the
> lent login no longer matches anyone by itself, commentators never make a run ours, and the *first tick* section is
> restated there. Suite on the merged tree: `10029 passed, 3 skipped`; `check.mjs`: `22 pages, 290 routes`.

## The ask, verbatim

Owner, 2026-10-03 20:0x: *"for gdq hotfix i think i found a mroe accurate source to pull form:
https://ogndrahcir.github.io/ScheduleViewer/ I don't want to overwrite the other source"* — and 20:2x, after the
comparison: *"the github link should persist as the hotfix host sheet for sometime. lets use that but have the link be
changeable on the website."*

## The three sources, and what is taken from each

| Source | What it is | What Black Bloc takes |
|---|---|---|
| **GDQ's Hotfix sheet** (`gamesdonequick.com/hotfix/schedule` → published sheet → CSV) | GDQ's weekly schedule: one show start per show-day, estimates, runners with Twitch links; the host column says the show's own name for a special event | **Unchanged, and still the roster**: which shows exist, the runs, their order, their `external_id`, the runners and their Twitch logins. [`marathon-hotfix-design.md`](marathon-hotfix-design.md) |
| **The schedule viewer** (`marathon_hotfix_viewer_url`, default `https://ogndrahcir.github.io/ScheduleViewer/` — a third party's static GitHub Pages site) | `index.html` + `js/schedule.js`: a `DATA_URL` (a Google Apps Script answering the same rows as GDQ's sheet, as JSON), a `hostLinks` table (host name → Twitch link) and footer links to each special event's own schedule | (1) the **host → Twitch login table**; (2) the **footer links**; (3) the feed's **row count**, for *Read it now* only. Its rows are NOT used as a schedule (same data as GDQ's sheet; see Deviation 2) |
| **The event's own sheet** (a footer link such as `gdq.gg/schedule/gdqueer` → a published Google Sheet → CSV) | The organisers' schedule: an explicit start per run (setup included), a host and commentators per run | For a marathon it matches: each run's **start time**, **estimate**, **hosts** and **commentators** — *the overlay* |

## Layer 1 — the link, and reading it

- **Key `marathon_hotfix_viewer_url`** (text, Marathons group). One public `https` page, at most 300 characters; **blank
  = this source is off** (`TEXT_MAY_BE_BLANK`). `checked_viewer_url` refuses, in words, `http`, a port, userinfo, a
  host with no dot, an address made of numbers (v4 or v6) and `.internal` / `.local` / `.localhost` / `.lan` / `.home` /
  `.corp`. Doors: the **Settings page**, the `/settings` panel's key card, and the **GDQ Hotfix feed's drawer**
  (Events ▸ Sources… ▸ GDQ Hotfix ▸ *Schedule viewer*: the field, **Save the link** — through
  `PUT /api/settings/marathon_hotfix_viewer_url`, the one writer — **Read it now**, and *open it ↗*). The Discord feed
  card carries a `**Viewer:**` line. Mock row, mock validator twin, label mirrored.
- **Reader `black_bloc/marathon_viewer.py`** (pure extractors + one walk). `script_urls` (the page's own `<script
  src>`, same host only, at most 3), `data_url_of`, `hosts_of` (the `hostLinks = {…}` object, pairs by regex, Twitch
  links only, through `spotlight.clean_login`, names folded by `runner_key`, at most 200), `event_links` (anchors whose
  host is `gdq.gg` or `docs.google.com`, `http` upgraded to `https`, label stripped of tags, at most 8), `sheet_of`
  (a `…/spreadsheets/[u/N/]d/e/<key>/pub[html]` link → its page and its `pub?…output=csv`, keeping a numeric `gid`),
  the Sheets-serial maths (`serial_day`, `serial_clock`, `serial_seconds`, ported from the viewer's own script: time
  and estimate serials are ALWAYS five hours ahead, whatever the season; a date is the instant converted to
  America/New_York) and `feed_rows`.
- **Trust.** The page is a third party's: everything on it is DATA. Nothing is evaluated; every extractor is a bounded
  regex with capped lengths and counts; a miss is "not found" (`None`, `{}`, `[]`), never an exception.
- **The walk and its allowlist** (`read_viewer`): page → its scripts → each footer link → each sheet's CSV → (only for
  *Read it now*) the feed. Every hop goes through `marathon_hotfix.fetch` (now taking `allow` and `site`), so the rules
  are the Hotfix reader's own: `https` only, port 443 or none, no userinfo, redirects followed by hand (at most 5) and
  **every hop checked BEFORE it is asked**, 1 MB, 20 s a request; 90 s for the whole read. `allow_for(page)` allows
  exactly: **the configured page's own host**, `script.google.com`, `gdq.gg`, `docs.google.com`, and hosts ending
  `.googleusercontent.com` (Deviation 1). A redirect anywhere else is *the Hotfix schedule viewer sent Black Bloc to
  <host>, which it does not fetch* — unfetched. A `gdq.gg` link is resolved **from its `Location` header alone**: a
  target that is not a published sheet (the GDQ tracker's `gamesdonequick.com/schedule/71`) is recorded as *goes to
  gamesdonequick.com, which is not a published Google Sheet* and never fetched — tracker events are the tracker feed's.
- **Cache and failures** (`cogs/content/marathon_viewer.viewer_of`): one copy on the cog for **five minutes**, under a
  lock; a failed read is not retried for five minutes, answers the last good copy of the SAME page, and leaves ONE
  `marathon.viewer_failed` row per distinct reason (`page`, `reason`, `kept_copy`). It never raises, so nothing here
  can fail a schedule read or a feed check; a client with no `viewer` method (the suite's fakes) reads as *no viewer*.
- **Read it now** — `POST /api/marathons/feeds/{id}/viewer-read` (staff; `cogs/content/marathon_viewer.read_now`): a
  forced read with the feed's rows counted. The answer is the feed row + `message` + `viewer` (`page, rows,
  rows_trouble, feed, hosts, events[{label, href, sheet_url}], skipped[{label, why}]`). In words: *Read the viewer: 61
  schedule row(s), 19 host(s) with Twitch names, 1 event schedule(s). **Games Done Queer** has its own schedule sheet.
  **Games Done Hitless** was not read — it goes to gamesdonequick.com, which is not a published Google Sheet.* A
  failure is 502 `unreadable` naming why; a blank link is 409 `viewer_off`; another feed is 409 `not_hotfix`. Logged
  `marathon.viewer_read` (`web.` head from the site).

## Layer 2 — hosts take their Twitch names

`Marathons.refresh` passes a Hotfix marathon's runs through `cogs/content/marathon_viewer.decorated` **before the
diff**. A `host` person the schedule gave no Twitch channel takes the viewer table's login, marked
`Person.login_from = "viewer"` (stored on the run's people as `login_from`).

- **Staff win.** `match_people` already reads *the pairing's `twitch_login` first, the schedule's second*; a lent login
  is the schedule's, so a staff-set login replaces it (`sheet_login` then shows the viewer's) and clearing the staff
  login gives the viewer's back. Tested end to end.
- **A lent login never costs a match.** The Discord-username rule used to apply only to a name with no login; it now
  also applies to a name whose login was lent by the viewer and matched nobody's Go-live link. A login the schedule
  itself gave still switches the name rule off, as before.
- **Logged** `marathon.viewer_logins` (`marathon_id`, `hosts[{name, login}]`) when a login is not already stored.
- **Viewer down:** the names the stored runs last took are used, so a host does not lose a login (and a BaF match made
  through it) for the length of an outage. **Link blank:** nothing is lent; the stored logins go at the next read.
- ⚠️ Applies to a marathon's runs only. The Hotfix **feed check and the show picker do not** read the viewer
  (Deviation 4).

## Layer 3 — the event's own schedule, laid over a Hotfix marathon

`black_bloc/marathon_overlay.py` (pure) + the same `decorated` step.

- **The sheet** (`slots_of`): columns by NAME from the header row holding a *Time…* and a *Game* cell (`Estimate`,
  `Category`, `Runner…`, `Host…`, `Commentator…`). A time is `YYYY-MM-DD at H:MMAM` read as **US Eastern wall clock**
  (the header says EST; the times are Eastern, DST included). A row with a time and no game is a separator and is left
  out. Hosts and commentators split on `,` and `&`.
- **Which sheet is a marathon's** (`fits`): their **show-days overlap** (a show-day is the Eastern date, rolling at
  6 AM, so a run past midnight stays on its day) AND **at least half of the marathon's runs are in it by title**. The
  first footer sheet that fits wins. The show's name is not compared (*GDQueer* vs *Games Done Queer*).
- **Which run is which slot** (`paired`): by **game title**, normalised (`marathon.normalise`: capitals and
  punctuation aside), in order, so a game played twice pairs twice; a title that is the other's whole-word part (six
  characters or more) counts. Then, **within one show-day and only when as many runs as slots are left**, by order. A
  run with no slot stays *loose*: it keeps GDQ's estimate and people and starts where the run before it ends. A slot
  with no run is ignored (the roster is GDQ's).
- **What is laid over** (`overlaid`): the slot's **start**, its **estimate** (GDQ's when blank), its **hosts** in place
  of GDQ's host column (kept when the slot names none) and its **commentators** (the existing `commentator` part — no
  schema needed for them). Runners, order and `external_id` stay GDQ's, so no persisted key moves.
- **The switch** — `marathons.overlay` (NULL follows **`marathon_hotfix_overlay_default`**, bool, **on**), through the
  one per-marathon switch writer `cogs/content/marathon_hosts.set_switch` (`which = "overlay"`): logs
  `marathon.overlay_set`, **re-reads the schedule at once** when the answer changed, answers
  `marathon_overlay_on_said` / `_off_said`. Doors: the drawer's *Settings for this marathon* ▸ **Event schedule**
  (Follow / On / Off — Hotfix marathons only), `PATCH /api/marathons/{id}` `{"overlay": true|false|null|"follow"}`, and
  a **seventh thread-controls button** (`marathon:controls:{id}:overlay:{on|off}`, labels
  `marathon_controls_overlay_on` / `_off`) that exists **only while a sheet matches**, so every other marathon keeps
  six. `GET /api/marathons/{id}` answers `overlay: {own, on, default, sheet}`.
- **What a marathon remembers** — `marathons.overlay_sheet` (JSON): `label, url, runs, matched, by_order, applied,
  stale`. The drawer draws it as one line under the header: *Times, hosts and commentators come from **Games Done
  Queer 📅 Oct 3-4 ↗** — 24 of 24 run(s) matched.*; off: *This event has its own schedule sheet, …, but Event schedule
  is off…*; none: *The schedule viewer links no event sheet that matches this marathon…*.
- ⚠️ **Sticky once laid over.** A read on which the sheet cannot be had — the viewer down with no copy, the footer link
  gone, the sheet no longer fitting — **keeps what the stored runs last held** (`kept`: their sheet times, estimate,
  hosts, commentators), marks the state `stale` with the reason, and logs `marathon.overlay_kept` once. Only staff
  switching it off, or blanking the viewer link, takes it off (`marathon.overlay_dropped`, `because`). The alternative
  — falling back to GDQ's stacked times — would move every run and re-arm reminders because a third party's page
  hiccupped.
- **Logs:** `marathon.overlay_applied` (first time laid over, `label, url, runs, matched`), `overlay_dropped`,
  `overlay_kept`, `overlay_set`.

### Overlay times and the stream re-time

`marathon_signals.retimed` is **untouched**. `cogs/content/marathon_signals.retime` picks
`marathon_overlay.retimed` only while the marathon's sheet is laid over (`overlay_sheet.applied`).

1. **Before a run of the show-day is seen:** every run is on the sheet's own time (`sheet_at` = the overlay's start).
2. **A run confirmed live keeps its real start** (`actual_started_at`), read after read.
3. **Every later run of that show-day** = the run before it's end (its real end when seen, else its start + estimate)
   **plus the sheet's own gap** between those two runs (the organisers' setup, 10 minutes on GDQueer). So a show 12
   minutes late is 12 minutes late down the day; a run that ends early pulls the next one in but keeps its setup.
4. A show-day is a chain; **three hours with nothing on starts a new one**, so day two is never moved by day one.

`marathon_signals.retimed` needs runs back to back (one minute of slack) to chain them; with setup between runs every
run would be its own chain and nothing after a late run would move — which is why the overlay has its own.
**Back to the sheet's times** now means the overlay's times.

## Keys

| Key | Type · default | Editable |
|---|---|---|
| `marathon_hotfix_viewer_url` | text · `https://ogndrahcir.github.io/ScheduleViewer/` (blank = off) | Settings page, `/settings`, the Hotfix feed's drawer |
| `marathon_hotfix_overlay_default` | bool · on | Settings page, `/settings` (per marathon: drawer, PATCH, thread button) |
| `marathon_controls_overlay_on` / `_off` | text · *Event schedule: on · turn off* / *…off · turn on* | Settings page, `/settings` |
| `marathon_overlay_on_said` / `_off_said` | text, `{marathon}` | Settings page, `/settings` |

## Measured live (2026-10-03 ~20:45 Phoenix, this machine, the bot's own client)

- The viewer: **61 feed rows**, **19 hosts with Twitch names**, **1 event sheet** (*Games Done Queer 📅 Oct 3-4*);
  *Games Done Hitless* skipped (tracker). The Apps Script 302s to `script.googleusercontent.com`; the sheet's CSV 307s
  to `doc-0g-3g-sheets.googleusercontent.com`; `gdq.gg/schedule/gdqueer` 307s to
  `docs.google.com/spreadsheets/u/1/d/e/…/pubhtml`.
- GDQueer against GDQ's live sheet: **24 of 24 runs matched by title — 13 of 13 on Sat 10-03, 11 of 11 on Sun 10-04**,
  none by order, none loose.
- Hosts on the organisers' sheet: sweetpeebs, chibicarrera, JRisJunior, champrul, SYDNEY J, fletchisafurry,
  Quacksilver. The viewer's table lends one of them a login (**Quacksilver → quacksilverplays**).
  **champrul** hosts Isopod + Yakuza (Sat) and Metroid Dread (Sun 23:19 ET); **JRisJunior** hosts Bombun + Kilaflow
  (Sat) and Ouendan 2 + Sayonara Wild Hearts (Sun 19:14 ET). Whether either is BaF on the live server was not read.
- The_Mathcat's Ring Racers: **19:03Z (12:03 Phoenix)** on the overlay, 18:43Z by GDQ's stacking.

## Deviations

1. **`.googleusercontent.com` is allowed as a tail, not `script.googleusercontent.com` alone.** The event sheet's CSV
   redirects to `doc-…-sheets.googleusercontent.com` (measured), the same tail the existing Hotfix reader allows.
2. **The viewer's feed is not a fallback schedule.** The brief's reader is built and tested (rows, serials), and *Read
   it now* counts the rows; nothing reads them as runs when GDQ's sheet is down. Not asked for in the build's layers.
3. **`Links/HostLinks.csv` is not read** — the script's `hostLinks` is the table the page itself uses; one home.
4. **The feed check and the show picker do not use the viewer.** A show block is still tracked for a BaF host only by
   a pairing or the name rule, as before; lending logins there would let a third party's table add marathons.
5. **Sticky overlay** (above) — the brief did not say what a vanished sheet does.
6. **Matching ignores the show's name**; dates and titles decide (above).
7. **`Person` gained `login_from`** and `match_people` one condition, so a lent login cannot cost a name match.
8. **`marathon_hotfix.fetch` gained `allow` / `site`** (defaults unchanged) rather than a second fetch walk.
   `_runs` and `marathon_signals.retimed` are untouched, for the `hotfix-setup-buffer` merge. ⚠️ **At that merge:**
   while a sheet is laid over, its times replace `_runs`' stacked ones for paired runs and `marathon_overlay.retimed`
   is the clock, so that build's buffer applies to marathons WITHOUT a sheet (and to a loose run's neighbour only
   through `_runs`). The one shared line is `cogs/content/marathon_signals.retime`'s call of `sig.retimed`.
9. **The per-marathon switch re-reads the schedule** (a network read inside a staff action); if that read fails the
   switch is stored and takes effect at the next read.
10. **`viewer_of` tolerates a client without `viewer`** — the suite's five fake clients stay as they are.
11. **No API-tools test file was extended**; the two routes are covered by the contract test (real API) and
    `check.mjs` (mock), and the shared functions by `tests/cogs/content/test_marathon_viewer.py`.
12. `ruff format` on the new files only.

## What would post at the first tick after deploy — GDQueer, Sunday 2026-10-04

⚠️ Reasoned from the code and the live sheets, NOT run against Discord or the live settings.

**Nothing new is sent because of this build by itself.** At the first schedule read of GDQueer after boot:

1. Log rows only: `marathon.overlay_applied` (24 of 24), `marathon.viewer_logins` (Quacksilver),
   `marathon.schedule_changed`, and one `marathon.member_run_moved` per BaF person on a run that moved five minutes or
   more (every Sunday run but the first moves later: +10 min at Inazuma up to +100 min at Metroid Dread).
2. Edits, never new messages: the pinned thread controls gain **Event schedule: on · turn off** (if GDQueer is
   tracked); the board and runner posts re-render with the new times and hosts; run events / host-block events are
   re-dated (if its events are on).
3. **Runs that moved later forget the marks that are in the future again** (`mt.rearmed`, the existing rule), so a
   BaF runner whose 2 h or 15 min reminder already went out gets it **again at the new time** — e.g. The_Mathcat's
   Ring Racers (11:43 → 12:03 Phoenix): a 15-minute reminder sent at 11:28 is re-sent at 11:48 if the deploy lands
   between them.
4. **Hosts newly found** — only if they are BaF on the live server (a pairing, a Go-live link, or the exact Discord
   name) and announcements are on: the existing host-block path. With `marathon_reminder_minutes` = `1440, 120, 15`
   and `marathon_reminder_stale_minutes` = 30 (registry default; the live value was not read): for **JRisJunior**'s
   Sunday block (Ouendan 2 + Sayonara, first run 16:14 Phoenix) the 24 h mark is long past → **skipped and logged**
   `marathon.host_reminder_skipped` `because: late`, never posted; the 2 h reminder posts at **14:14 Phoenix** and the
   15 min at **15:59**. For **champrul**'s Sunday block (Metroid Dread, 20:19 Phoenix): 24 h skipped the same way;
   2 h at **18:19**, 15 min at **20:04**. A mark whose moment passed less than 30 minutes before the tick posts once,
   late — the stale rule, unchanged. Saturday's blocks are over; nothing is posted for them. A host highlight posts
   when the block goes live only if Auto-highlight is on.
5. With the marathon untracked, announcements off, or neither host BaF: log rows and nothing else.

## Tests

`tests/test_marathon_viewer.py` (25 tests: extractors on the real page and script and on garbage; the serial maths incl.
DST and the midnight crossing; the walk; **six feed-redirect targets refused in words and never fetched**, a page
redirect, a sheet redirect; skipped short links; another page host; the cache; host fill),
`tests/test_marathon_overlay.py` (14 tests: the real organisers' sheet, separators, Eastern time through DST and past
midnight, garbage, 24/24 pairing, a retitled run by order, a run in one sheet and not the other, other days / other
games, the overlay, two chains, a late run moving its day by the gaps, an early end, `kept`, the state),
`tests/cogs/content/test_marathon_viewer.py` (23 tests — 74 cases across the three files: cache, blank link, failure once, read-it-now words, the feed card
line, host fill + log once, staff login wins, link blank, viewer down keeps names and the GDQ read, the overlay on
GDQueer, a BaF host and its blocks, the switch off / follow / refused, the default key off, no viewer = the old path
exactly, blanking the link, sticky, live run + later runs + a re-read, a marathon without a sheet keeps the old
clock), `tests/test_marathon.py` +1, `tests/test_settings_store.py` +2 (and the count **712**),
`tests/storage/test_db.py` +1 (a schema-84 file gains both columns, archive too),
`tests/test_marathon_thread_controls.py` +1, `tests/api/test_contract.py` (the fake's `viewer`; two contract entries).
Fixtures: `hotfix_viewer_page.html`, `hotfix_viewer_schedule.js` (first 150 lines), `hotfix_viewer_feed.json` (30 of
61 rows), `gdqueer_organisers.csv`. No test makes a network call.

## Live check after merge + deploy (the owner's; sweeps `HV-a…HV-g`)

See [`../access/sweeps.md`](../access/sweeps.md).

## Merge + review fixes 2026-10-03

**Merged `origin/main` `c2ba3251` (v195 LIVE: `hotfix-setup-buffer`, `marathon-role-ping`, 512 MB) into the branch, by
hand.** Counts on the merged tree, measured: **registry keys 727** (main's 721 + this build's 6, by import),
**schema 85** (main is 84), **contract routes 290** (main's 288 + 2). `ruff check black_bloc tests site` clean;
`pytest -q -n 16 -rfE` → `10029 passed, 3 skipped`; `check.mjs` on a worktree mock → `ok - 22 pages, 290 routes, 26
core settings, all keys present`; the ten node fixtures exit 0. ⚠️ Still NOT checked: Fly, Discord, the live database,
the live settings; the browser render was NOT repeated on the merged tree.

Conflicts and how each was resolved:

- **`cogs/content/marathon_signals.retime` BRANCHES**: a marathon whose sheet is laid over
  (`marathon_overlay.applied`) uses `marathon_overlay.retimed(rows)` — no buffer passed; every other marathon uses
  `sig.retimed(rows, setup_minutes(bot, guild.id))` exactly as main has it.
- **`marathon_sources.ScheduleClient`**: main's `hotfix_block(ref, setup_minutes=0)` and this build's `viewer()` both
  kept; `runs` / `resolve` pass `setup_minutes` through as on main (three callers in `cogs/content/marathon.py` via
  `signals.setup_for`, unchanged).
- **`tests/test_settings_store.py`**: the count is **727**. **Docs** (`sweeps.md`, `code-notes.md`): both sides kept.
- Everything else auto-merged; the role-ping status line (thread controls and drawer) is main's code untouched, beside
  the overlay button and line.

The buffer and the overlay, together: GDQ's sheet is read with `marathon_setup_minutes` (7) between runs, as on main.
While a sheet is laid over, a paired run's start is the organisers' (their own setup is already in it), so the buffer
shows only on a marathon with no sheet, with the overlay off, or on a loose run's neighbour.

The four fixes:

1. **A live or done run is never moved by the overlay's clock.** `marathon_overlay.retimed` now holds a run that is
   live or done and has no real start, exactly as `marathon_signals.retimed` does (`sig.settled`): before the first
   anchor it is skipped; after one it stays at its stored start and end and the runs after it follow from there by the
   sheet's gaps. (`_write_plan` already keeps `scheduled_at` / `ends_at` of such a row and `held_plan` already drops
   its *moved* flag — main's code.) Its `sheet_at` does take the overlay's time, silently. Tests:
   `test_marathon_overlay.py::test_a_live_or_done_run_never_seen_starting_stays_where_it_is`,
   `cogs/content/test_marathon_viewer.py::test_a_done_or_live_run_is_never_moved_when_the_overlay_is_first_laid_over`
   (a done run with a real start, a done run without, a live run without: `scheduled_at`, `ends_at`,
   `reminders_sent`, `previous_scheduled_at`, `moved_at` and `state` identical before and after; no
   `marathon.retimed` row names one first; no `marathon.member_run_moved` for them; a second retime changes nothing).
   ⚠️ "No runner-post / board edit caused by them" is proven only through those unchanged columns — no fake Discord
   edit was counted.
2. **Commentators are stored and shown, and never make a run ours — on a Hotfix marathon.** `match_people` gained
   `commentators_count`; `rematch` passes `False` for `gdq_hotfix`, so a matched commentator carries `counts: false`
   (the hosts' own mechanism) and `mt.ours` leaves them out: no reminder, highlight, runner post, run event or ping,
   and `baf_people` does not list them. They cannot auto-track a show either: the feed check never reads the overlay,
   and `marathon_hotfix.reasons_of` knows runners and hosts only. ⚠️ Scoped to Hotfix marathons on purpose: a GDQ
   tracker commentator behaves as before (`marathon_match_hosts`). **Where a commentator is shown:** the marathon's
   People card on the site and `/event` ▸ People…, on their run's slot line with the commentator part tag
   (`marathon_part_commentator`), and in the run's stored people. Test:
   `test_a_member_who_only_commentates_never_makes_a_run_ours`.
3. **A lent login never creates a match.** In `match_people`, a login lent by the viewer is NOT looked up in the
   Go-live links; such a person is matched only by a staff pairing or the exact Discord name — the rules that applied
   before the login was lent. The login is still shown and still lets staff Spotlight the host without typing it. This
   SUPERSEDES Layer 2's wording above and Deviation 7 ("matched nobody's Go-live link"). Tests:
   `test_marathon.py::test_a_login_lent_by_the_viewer_never_costs_a_name_match_and_a_staff_login_beats_it`,
   `test_a_lent_login_never_pairs_the_member_who_owns_that_channel`.
4. **The combinations**: overlay on + a run confirmed live (`…keeps_its_real_start_and_later_runs_follow_by_the_gaps`:
   10-minute sheet gaps, no 7 added); overlay off on a Hotfix marathon (`…is_on_the_buffer_clock`: 18:15 after a 1:08
   run, and 7 minutes after a late run's end); the switch off and on mid-day
   (`…snaps_the_times_once_each_way`: one `marathon.schedule_changed` per switch, none on an idle re-read, the
   15-minute mark re-armed once and never again); **Back to the sheet's times** with the overlay on
   (`…means_the_organisers_times_while_laid_over`).

### First schedule read after a deploy — GDQueer, Sunday 2026-10-04 (restated for the merged tree)

⚠️ Reasoned from the code and the two sheets as read 2026-10-03; NOT run against Discord, the live rows or the live
settings. v195 is live, so the stored times are GDQ's with 7 minutes between runs — unless the stream has already
anchored Sunday's runs, in which case only runs after the last confirmed one are placed by the sheet's gaps.

- **Saturday's 13 runs:** done → held. Nothing moves, nothing is logged as moved, no mark changes. (A Saturday run
  still `upcoming` in the database — never confirmed — would take the organisers' time; it is in the past, so every
  mark is stale and nothing posts.)
- **Sunday's 11 runs, stored → organisers' (Phoenix):** Wii Fit U 10:00 → 10:00 (0); Inazuma 10:30 → 10:33 (+3);
  Ring Racers 11:57 → 12:03 (+6); Metroid Prime 4 12:20 → 12:29 (+9); E.T. 14:17 → 14:29 (+12); Battle Chef 14:39 →
  14:54 (+15); Ouendan 2 15:56 → 16:14 (+18); Sayonara 16:53 → 17:14 (+21); Fear the Spotlight 17:50 → 18:14 (+24);
  Soul Reaver 2 18:37 → 19:04 (+27); Metroid Dread 19:49 → 20:19 (+30). **Nine count as moved** (5 minutes or more:
  Ring Racers onward); a run already live or done when the read happens is held instead.
- **Marks that re-arm:** on each moved, still-upcoming BaF run, every sent mark whose moment is in the future again
  (`mt.rearmed`). In practice only a mark sent within the run's shift before the deploy — e.g. Ring Racers' 15-minute
  reminder sent at 11:42 is sent again at 11:48 only if the read lands between 11:42 and 11:48.
- **Log rows:** `marathon.overlay_applied`, `marathon.viewer_logins` (Quacksilver), `marathon.schedule_changed`,
  `marathon.retimed` if the stream had anchored a run, one `marathon.member_run_moved` per BaF person on a moved
  upcoming run.
- **Edits, never new messages:** the thread controls gain the Event schedule button (the role-ping status line stays);
  board, runner posts and events take the new times and hosts.
- **Hosts newly found** — JRisJunior and champrul only if a staff pairing or their exact Discord name matches them
  (Quacksilver's lent login matches nobody). JRisJunior's Sunday block starts 16:14: the 24 h mark is skipped and
  logged `marathon.host_reminder_skipped` (`late`), the 2 h reminder posts 14:14, the 15 min 15:59. champrul's block
  starts 20:19: 24 h skipped, 2 h at 18:19, 15 min at 20:04. A mark less than `marathon_reminder_stale_minutes` (30 by
  default) past at the read posts once, late. Highlights only with Auto-highlight on. Commentators: nothing.
- Whether the Marathon role is pinged by any of these is main's `marathon-role-ping` rule, unchanged here and not
  re-derived.
