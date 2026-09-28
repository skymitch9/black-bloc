# Marathon hosts — scan them per marathon, spotlight them, give them events; and a pairing can fix someone's Twitch channel

> 🔨 **BUILT 2026-09-28 on branch `marathon-host-spotlight` (worktree `C:/lcw/bb-marathon-host-spotlight`, off `main`
> `aba4ca00`), NOT MERGED, NOT DEPLOYED.** Commits `e831e982` (Python), `7511e9b6` (site, mock, contract), then docs.
>
> **Audience:** the conductor, reviewers, and the next session touching marathon people, hosts, spotlights or run
> events. **Status:** TRACKED. **Last verified: 2026-09-28** — against the branch's own code by the suite
> (`tests/test_marathon_hosts.py`, `tests/cogs/content/test_marathon_hosts.py`, the JR tests at the foot of
> `tests/cogs/content/test_marathon_people.py`, the schema-81 test in `tests/storage/test_db.py`, the new API and
> thread-control tests), `node site/mock/check.mjs` on `MOCK_PORT=8911` (*22 pages, 286 routes, 26 core settings, all
> keys present*) and a scripted walk of the mock (below). ⚠️ **NOT checked:** anything against Discord, a browser, the
> live database or its migration, the live marathons 9 and 10. Secret NAMES only.

## The asks, verbatim (owner, 2026-09-28)

1. *"We probably also want to scan for host, that way if a BaF person is hosting we can choose to spotlight that.
   basically a clone of the runner spotlight but its a host spotlight too. make it optional to scan and spotlight for.
   that way we do runners scanned and shown by default and then we decide if we want events for them. for host we can
   choose to check for host and then we can follow the if we want to show them and then if we want events for them"*
2. *"for gdqueer JR is a Baf member juniorsm is discord name, https://www.twitch.tv/junior_sm is twitch. looks like the
   schedule has a typo in it but ive confirmed with JR that its the their run"*

Deadlines: Hidden Heroes (hosted by anarchy) Fri 2026-10-02 16:00 Phoenix; JR's GDQueer run Sat 2026-10-03 12:50
Phoenix.

## As built

### 1. Scan hosts, per marathon

- **`marathons.scan_hosts INTEGER`** — NULL follows `marathon_scan_hosts_default` (the `hotfix-picker` key, still
  **off**), 1 / 0 is this marathon's own answer. `Marathons.rematch` reads it through `marathon_hosts.scans_hosts`, so
  a host counts as BaF (pairing, Twitch link) only on a marathon that scans. `marathon_match_hosts` still gates hosts
  AND commentators as before; commentators ignore this switch.
- **Doors (both ways):** the drawer's *Settings for this marathon* ▸ **Scan hosts** (*Follow the setting (off)* /
  *On* / *Off*, saved by `PATCH /api/marathons/{id}` `{"scan_hosts": true|false|null|"follow"}`); the thread
  controls' sixth button **Scan hosts: off · turn on** / **on · turn off** (custom id `marathon:controls:{id}:hosts:
  {on|off}`). One writer: `cogs/content/marathon_hosts.set_switch` — under the marathon lock it writes the column,
  rematches, re-syncs run and host events and the board, logs `marathon.scan_hosts_set` (`from`, `to` = the stored
  answer, `on` = what it means now), and re-renders the thread controls. A word it does not know is refused in words
  (`bad_switch`, 422).
- `GET /api/marathons/{id}` answers `scan_hosts: {own, on, default}` (same for `host_events`).
- With scanning on, a BaF host sits in the People card's BaF block with **host** in their parts (nothing new drawn —
  the parts were already there).

### 2. Host spotlight — the same Spotlight…

`cogs/content/marathon_people.spotlight_runner` was already person-generic (it spotlights an entry of
`people_state`, whatever their part). What changed: when the person **only hosts** the runs in the window (the whole
BaF block span, or the one slot), the note is **`marathon_spotlight_host_note_template`** (*{name} hosting
{marathon}*); anyone who runs keeps *{name} at {marathon}*. The window is the existing rule over the runs the person is
on — for a host, their hosted runs: first − `marathon_spotlight_lead_hours` → last end + `marathon_spotlight_slack_hours`.
Same `marathon_spotlights` bookkeeping, same **Stop spotlighting**, same `marathon.runner_spotlit` kind with
`hosting: true` in its details. It works for a host whether or not the marathon scans hosts (an unscanned host is in
*the schedule*, not the BaF block — the same as spotlighting any runner who is not BaF).

### 3. BaF host events

- **`marathons.host_events INTEGER`** (NULL follows **`marathon_host_events_default`**, bool, **off**) and
  **`marathons.host_event_ids TEXT`** (JSON `{user_id: event_id}`).
- **Doors:** drawer ▸ **BaF host events** (Follow / On / Off) and the thread controls' seventh button **BaF host
  events: off · turn on**; same writer `set_switch`, kind `marathon.host_events_set`.
- **`sync_host_events`** (called by `sync_runs` — every schedule read, pairing change and switch — under the marathon
  lock): while the marathon is active, its host events are on AND it scans hosts, each BaF host
  (`marathon_hosts.hosted`: a person with `part == host` and a `user_id`, dropped runs left out) gets **one** event
  from their first hosted run's start to their last hosted run's end, made through the run events' own door
  (`marathon_events.event_from`: approved at once, or into the review when `marathon_run_events_reviewed` is on or
  marathon posts are not `on`). Title `marathon_host_event_title_template` (*{member} hosts {marathon}*), description
  `marathon_host_event_description_template` (*{member} hosts {runs} run(s) on {marathon}: {games}. Read from the
  schedule; times follow it.*), Where = the marathon's channel, else the host's own login, else the schedule page.
  Re-dated when the span moves (`marathon.host_event_redated`); called off (`marathon.host_event_cancelled`) when the
  person stops hosting (`not_host`), when the switch goes off (`switched_off`, only while
  `marathon_run_event_cancel_on_leave` is on — else the pointer is dropped and the event left), and when the
  marathon is removed or archived (`marathon_removed`, through `cancel_every_run_event`). A failure is
  `marathon.host_event_failed` (IMPORTANT by suffix).
- **Runner events are unchanged** except one narrowing — see Deviation 5.

### 4. A pairing's Twitch fix

- **`marathon_people.twitch_login TEXT`** (nullable). `marathon.match_people` looks the pairing up by name first (as
  before); when that pairing carries a login it REPLACES the schedule's login on the stored run person, and the
  schedule's own is kept beside it as `sheet_login`. Everything that reads a run person's `login` therefore uses the
  fix: Spotlight… (the Go-live row is `twitch.tv/junior_sm`), the runner posts' and run events' links
  (`mt.run_url`, `run_logins`), a host event's Where, matching by a Go-live link (the link is looked up by the fixed
  login), the People card, and the Hotfix tracker (it calls `match_people` too). Clearing it gives the sheet's back at
  the same rematch (`sheet_login` is read as the source of truth). An **everywhere** pairing's fix applies on every
  schedule, and setting it re-matches every active marathon at once.
- **Doors:** `POST /api/marathons/{id}/people` takes an optional `twitch_login` (a name, `@name` or a twitch.tv link;
  omitted = keep the pairing's current fix when re-linking; `""` = none); **`PATCH /api/marathons/{id}/people/
  {pairing_id}` `{"twitch_login": …}`** sets or clears it and answers the People board. The site: *Link to a
  member…* has a *Twitch name (optional)* field; a person decided by a pairing has **Twitch name…** beside
  **Unlink**; the row reads **twitch.tv/junior_sm (fixed from twitch.tv/Jr)**. Discord: the People panel's slot view
  shows **Twitch name…** for a person decided by a pairing → a one-field modal (blank = the schedule's). One writer:
  `cogs/content/marathon.set_pairing_login` → `marathon.pairing_login_set` (`from`, `to`, `everywhere`).
- A name that is not a Twitch login is refused in words: *"**junior sm!** is not a Twitch channel name (letters,
  digits and _, up to 25, or the channel's twitch.tv link), so nothing was changed."* (`bad_twitch`, 422).

### Keys (12, all Marathons group: registry + mock row + label)

`marathon_host_events_default` (bool, off) · `marathon_spotlight_host_note_template` · `marathon_host_event_title_template`
· `marathon_host_event_description_template` · `marathon_controls_hosts_on` / `_off` · `marathon_controls_host_events_on`
/ `_off` · `marathon_scan_hosts_on_said` / `_off_said` · `marathon_host_events_on_said` / `_off_said`. No ping key was
added or turned on; host events post nothing to a channel themselves (an approved event announces the way every
approved event does).

### Log kinds (7 new, routine unless said)

`marathon.scan_hosts_set`, `marathon.host_events_set`, `marathon.pairing_login_set`, `marathon.host_event_made`,
`marathon.host_event_cancelled`, `marathon.host_event_redated`; `marathon.host_event_failed` (IMPORTANT by suffix).

### Counts

Schema **81 → 82** · registry keys **701 → 713** · routes **+1** (`PATCH /api/marathons/{id}/people/{pairing_id}`;
`check.mjs` *22 pages, 286 routes*) · new modules `black_bloc/marathon_hosts.py` (pure) and
`black_bloc/cogs/content/marathon_hosts.py` (not a cog; `bot.py:COGS` unchanged).

## Deviations

1. **Host events live in a JSON column on the marathon, not a table.** `marathons.host_event_ids` archives and
   restores with the marathon row for free; a table would have needed its own archive twin and delete paths. One row
   per marathon, a handful of hosts — no query needs it indexed.
2. **Host events are independent of the event mode.** The brief said "wherever the marathon has a switch for making
   events for OUR RUNNERS, add the matching switch for OUR HOSTS": the runners' switch is the *runs* half of
   `event_mode` (the thread's **BaF run events** button); hosts got their own switch rather than a fifth mode word, so
   *None / Marathon / Runs / Both* keep their meaning and neither switch moves the other. It needs the marathon to scan
   hosts; with scanning off there is no BaF host to give an event to.
3. **No per-host staff move** (no *Unlink* / *Make it now* per host event). Staff final say is the switch, and the
   event's own Cancel on the Events page: a host event staff cancelled stays pointed at and is **never re-made** while
   that person still hosts (the pointer is kept; only an event that is gone from the database is forgotten).
4. **The Twitch fix is a property of the pairing.** A person matched only by a Go-live link or the Discord-name rule
   has no pairing to carry it, so staff link them first (*Link to a member…* takes the Twitch name in the same form).
   The fix is applied whether or not that person's part is being matched (a host's fix shows even with Scan hosts
   off) — it is a fact about the person, not about who counts.
5. ⚠️ **Behaviour change for run events: a run whose only BaF person is a HOST no longer gets a run event on its
   own** (`marathon_events.makeable` now asks `marathon_hosts.is_runner_run`). Before this, with host scanning on, a
   hosted run became "ours" and `runs`/`both` mode made it an event — which would have given Hidden Heroes one event
   per run anarchy hosts on top of any host event. A run event that already exists on such a run is NOT called off
   (the cancel rule is still "nobody of ours is left"), and **Make it now** on that run still works (staff final say).
6. ~~⚠️ **Everything else that follows "a run of ours" is unchanged, so Scan hosts ON makes every run the host is on
   "ours"**: the board lines, one runner post per run in the marathon's thread, reminders (and the public reminder
   copy while `marathon_public_reminders` is on), shoutouts and public highlights — each naming the host with the
   `marathon_part_host` word. That is the `hotfix-picker` rule for a scanned host, not new here, but it is what the
   conductor's live action (Scan hosts ON for Hidden Heroes) will set off; see the live check.~~
   **REVERSED 2026-09-28 by the owner (*"Do the small change first, HH isn't today"* — spotlight only), branch
   `host-spotlight-only` `ce1b090d`:** a scanned BaF host is shown, can be spotlit and gets host events, but a run is
   ours only because a BaF person RUNS it. The old rule is `marathon_hosts_count_as_ours` (default off). Why it
   flipped: Hidden Heroes' three runs are other people's — the old rule would have posted, reminded, shouted and
   highlighted runs nobody from BaF runs. See *Spotlight only* at the foot of this doc.
7. **The Hotfix show picker and feed tracker still read the global `marathon_scan_hosts_default`**: a show block they
   judge has no marathon row yet, so there is no per-marathon answer to read.
8. **The thread controls now carry seven buttons** (two rows; Discord lays them out five a row). The `/event` card
   got no button — it is already full; the site drawer, the thread and the two global defaults are the doors.
9. **The spotlight log kind stays `marathon.runner_spotlit`** for a host, with `hosting: true`; a new kind would have
   split one move across two filters on the Logs page.
10. **Stop spotlighting finds a row made before a fix**: if someone was spotlit under the sheet's login and the fix
    came after, *Stop spotlighting* falls back to the remembered sheet login, so the row is not stranded.
11. **The member-facing Discord BaF line shows only the fixed login**, not *(fixed from …)* — that note is staff
    chrome, drawn on the site and in the staff slot view's Twitch line.
12. **Refusal and answer sentences for the fix and the switches' bad word are constants** (staff chrome, the repo's
    convention for refusals); the switches' *on/off* answers are keys (the ping switch's precedent).

## What was NOT verified

- ⚠️ **Nothing met Discord.** The two new thread-control buttons, the People panel's **Twitch name…** button and
  modal, and every event a host switch makes were exercised against the suite's fakes only.
- ⚠️ **No browser.** The drawer's two new switch fields, the Link form's Twitch field, **Twitch name…** and the
  *(fixed from …)* text were never rendered; `node --input-type=module --check` parses every asset and `check.mjs`
  proves the routes' shapes against the mock.
- **The mock walk** (`MOCK_PORT=8911`, scripted fetches): Scan hosts on → `{own: true, on: true}` and the said line;
  BaF host events on; a bad word → 422 `bad_switch`; pairing *Bluekandy* with `https://twitch.tv/Blue_Fixed` → the
  card reads `twitch.tv/blue_fixed (fixed from twitch.tv/bluekandy)`; `no good` → 422 `bad_twitch`; clearing → back
  to `bluekandy`. **Not walked in the mock:** a host-only Spotlight… (the mock's only BaF host, Rivet, also runs), the
  mock's host-event dates.
- **The live migration (schema 82)** has not run; the live marathons 9 and 10, their pairings and whether anarchy's
  sheet row carries a Twitch link were not read.
- **A GDQ-sized schedule** was not timed; `set_pairing_login` on an everywhere pairing rematches every active marathon
  in one request.

## Live check after merge + deploy (the conductor's two live actions, then the owner's sweeps `HS-a…HS-f`)

⚠️ Migrate before deploy is automatic here (four `ADDED_COLUMNS` through the bootstrap; the boot log names them).

1. ~~**Before Scan hosts ON for Hidden Heroes (marathon 10)** — read Deviation 6: every run anarchy hosts becomes a
   BaF run (a runner post each in its thread, reminders, and the public reminder copy if `marathon_public_reminders`
   is on). If that is not wanted for a hosting-only show, decide it before pressing.~~ **Decided 2026-09-28: spotlight
   only** (`host-spotlight-only`) — once that branch is live, Scan hosts ON posts nothing for anarchy's hosted runs
   while `marathon_hosts_count_as_ours` stays off. Merge + deploy it BEFORE pressing.
2. **Scan hosts ON for Hidden Heroes (marathon 10)** — either the thread's **Scan hosts: off · turn on**, or Events ▸
   Hidden Heroes ▸ *Settings for this marathon* ▸ **Scan hosts** *On* ▸ Save, or
   `PATCH /api/marathons/10 {"scan_hosts": true}`. Expect *"**Hidden Heroes** scans its hosts now…"*, and the People
   card's BaF block gains **anarchy** with *host* (needs the every-schedule pairing `anarchy` → @anarchyasf from
   `HF-g`; check it exists). If anarchy's row says *no Twitch channel*, set **Twitch name…** on that pairing first.
3. **Spotlight… on anarchy** (BaF block) → a Go-live channel row for anarchy's login, note *anarchy hosting Hidden
   Heroes*, ending 2 h after the last hosted run; *Spotlit until …* on the row.
4. **JR's override on GDQueer (marathon 9)** — Events ▸ GDQueer ▸ People ▸ **Jr** (BaF, *linked by staff*) ▸
   **Twitch name…** ▸ `junior_sm` ▸ Save; or the slot view in Discord ▸ **Twitch name…**; or
   `PATCH /api/marathons/9/people/{JR's pairing id} {"twitch_login": "junior_sm"}`. Expect *"**jr** is
   **twitch.tv/junior_sm** everywhere Black Bloc uses their channel now."*; the row reads **twitch.tv/junior_sm (fixed
   from twitch.tv/Jr)**; **Spotlight…** then makes a row for `junior_sm`, never `jr`. A `marathon.pairing_login_set` row
   is on the Logs page.

## Spotlight only — hosts never make a run ours (owner 2026-09-28)

> **BUILT 2026-09-28 on branch `host-spotlight-only` (worktree `C:/lcw/bb-host-spotlight-only`, off `main`
> `c8e075bb`), NOT MERGED, NOT DEPLOYED.** Commit `ce1b090d` (Python, mock, site words, tests), then docs.
> **Last verified: 2026-09-28** by the suite and `node site/mock/check.mjs` on `MOCK_PORT=8913`; nothing met Discord,
> a browser or the live database.

**The ask:** the conductor asked *"all of that, or spotlight only?"* about Deviation 6; the owner, 15:5x: *"Do the
small change first, HH isn't today"* — spotlight only.

**As built:**

- **`marathon_hosts_count_as_ours`** (bool, **off**; Marathons group, registry + mock row + label, listed right after
  `marathon_scan_hosts_default`; the drawer's Scan hosts help names it). Off: a run is ours only because a BaF person
  runs it (commentators are not hosts and keep following `marathon_match_hosts`). On: the `hotfix-picker` rule
  returns — a scanned BaF host makes the run ours.
- **One decision point.** `mt.match_people(..., hosts_count=)` marks a matched host `"counts": False` when hosts do
  not count; `mt.ours` skips that person. Every "run of ours" reader goes through `mt.ours` / `mt.is_ours` /
  `mt.member_ids`, so all of these now follow runners only with no change of their own: the `ours` counts (API
  marathon/list/refresh answers, the card's BaF line, the People card's day counts, `counts_of`), the board and its
  lines, runner posts in the marathon thread, reminders and the public reminder copy, shoutouts (automatic and
  **Shout it now** via `run_moves`), public highlights (`marathon_public.postable`), run events and their cancel rule
  (Deviation 5's `is_runner_run` is unchanged and still stops host-only run events even with the key on),
  `marathon.run_matched` logging, *what's next for me*, and the run-details payloads.
- **Unchanged on purpose:** the People card still shows the host in the BaF block marked *host* (it reads `user_id`,
  which the host keeps); **Spotlight…** on a host works as before; host events follow `host_events` + scan hosts and
  never read the key; the Hotfix feed's person tracking (`marathon_hotfix`) calls `match_people` without the argument
  and still tracks a show because anarchy hosts it (gated by `marathon_scan_hosts_default`, as before); near-miss is
  about unmatched names and never read "ours". No Go-live repost path decides BaF-ness outside `mt.ours` (searched).
- **When it takes effect:** at the marathon's next rematch — every schedule read, a pairing change, a Scan hosts
  press. A run stored before the deploy carries no flag and counts until that rematch (one read on an active
  marathon). Flipping the key has no settings hook either; it lands at the next read.
- **Mock:** `marathonCounts` mirrors `mt.ours`; `marathonRematch` writes the flag; the seed's run 7 (Rivet hosting)
  starts flagged, so AGDQ 2027's run 7 now reads *ours: false* while Rivet stays ✦BaF on it. No payload shape
  changed (`person_row` never sends `counts`; the mock strips it), so `contract.json` is untouched.

**Counts:** registry keys **713 → 714** (measured: `len(settings_store.KEY_TYPES)`); schema unchanged (82); routes
unchanged (`check.mjs`: *22 pages, 286 routes, 26 core settings, all keys present*).

**Tests:** `tests/test_marathon.py` (the flag and `ours` both ways; a runner counts either way);
`tests/cogs/content/test_marathon_hosts.py` — a Hidden-Heroes-shaped show (Titanfall 2, VHOLUME, SPRAWL zero, anarchy
hosting all three, paired everywhere, Scan hosts on, the clock at the 15-minute reminder): anarchy ✦BaF *host*,
`counts_of` = (3, 0), no runner post / reminder / public reminder, no **Shout it now**, no highlight, Spotlight… makes
the host row; the key on → (3, 3), posts and reminders return; key off again → back to 0 at the rematch; Sky's run is
the same both ways; host events follow their switch both ways. Five older tests that asserted the old rule now set
the key on (they still prove it).

**What was NOT verified:** nothing met Discord or a browser; the live marathons 9 and 10 and their stored runs were
not read; the one-rematch lag on stored runs was reasoned from the code, not measured live.
