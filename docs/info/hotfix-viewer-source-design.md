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
