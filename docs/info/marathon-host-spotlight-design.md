# Marathon hosts — scan them per marathon, spotlight them, give them events; and a pairing can fix someone's Twitch channel

> ⚠️ **2026-09-28 — people-unify (branch `people-unify`, 🔨 BUILT, NOT MERGED):** **§1 Scan hosts and §3 BaF host events are REVERSED** — hosts are always found (no switch, key or button; `marathons.scan_hosts` left in place, unread), and host events are one per host BLOCK under the one **BaF run/host events** switch (the runs half of `event_mode`); `marathons.host_events` is ignored. §2 (the host spotlight note) and §4 (the Twitch fix) stand. See [`people-unify-design.md`](people-unify-design.md).

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

### 1. ~~Scan hosts, per marathon~~ — REVERSED 2026-09-28 by `people-unify`: hosts are always found

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

### 3. ~~BaF host events~~ — REVERSED 2026-09-28 by `people-unify`: one event per host block under **BaF run/host events**

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
2. ~~**Host events are independent of the event mode.**~~ *(REVERSED 2026-09-28, `people-unify`: they follow the runs half of the event mode, per host block.)* The brief said "wherever the marathon has a switch for making
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

## Host highlights (owner 2026-09-28)

> ↩️ **Its BLOCK RULE came back on 2026-09-28 (branch `marathon-announcements`, `5a60c782`)** — per block, at every
> reminder mark, in the runner's templates; its four templates and its *post as soon as the block is known* did not.
>
> ⚠️ **SUPERSEDED BEFORE IT SHIPPED (2026-09-28, branch `host-highlights-per-run`, commit `30199332`)** by
> *Host highlights, per run* at the foot of this doc (checklist 35). This section was merged (`ea4c2b43`) but never
> deployed. ~~One post per contiguous hosted **block**, posted as soon as the block is known, one heads-up per block,
> four `marathon_host_*` templates~~ → one heads-up and one highlight per hosted **run**, in the runner's own
> templates and at the runner's own moments. The block rule, Deviation 1, the five-key list and the Friday table
> below are struck by that section; the bookkeeping column, shadow routing, never-ping, staff moves, routes and log
> kinds carry over as it says.

> **BUILT 2026-09-28 on branch `host-highlights` (worktree `C:/lcw/bb-host-highlights`, off `main` `c0e38353`),
> NOT MERGED, NOT DEPLOYED.** Commits `9fd9088e` (Python + tests), `b055e945` (mock, contract, site), then the
> carry-to-the-end fix and docs. **Last verified: 2026-09-28** by the suite (`tests/test_marathon_host_highlights.py`,
> `tests/cogs/content/test_marathon_host_highlights.py`, the slot-view test at the foot of
> `tests/cogs/content/test_marathon_people.py`, the route test in `tests/api/tools/test_marathons.py`, the schema-83
> test in `tests/storage/test_db.py`, the contract test's seeded host) and `node site/mock/check.mjs` on
> `MOCK_PORT=8915` (*22 pages, 288 routes, 26 core settings, all keys present*). ⚠️ Nothing met Discord, a browser or
> the live database.

**The asks, verbatim.** Owner 19:0x: *"Let's add a clause for if a host is both BaF and a host it can be shown in
upcoming events. We want to highlight all our members"*. Owner 19:1x (relayed): *"That's fine for hotfix but when it's
a GDQ event using the tracker we can pull host from there for each host specific time blocks"* — one post per
contiguous hosted block, the block rule below.

**"A host never makes a run ours" is untouched.** This is a separate path: `mt.ours` still skips `counts:false`
hosts, so hosted runs still get no runner post, reminder, shoutout, run highlight or run event (tested).

### As built

- **The block** (`marathon_host_highlights.spans`): in schedule order, a BaF host's block runs on across runs they
  host AND runs with no host listed (GDQ's *The Checkpoint*); a run someone else hosts ends it; a co-hosted run keeps
  both open; dropped runs are off the schedule. Only a host with a `user_id` counts, i.e. only while the marathon
  **scans its hosts**. Hosts come per run from the source — the GDQ tracker's `hosts` (Twitch login from
  `talent.stream`), the Hotfix sheet, Oengus/Horaro — so tracker shifts become blocks with no source-specific code.
  Pinned with the real `tests/fixtures/marathon/gdq_sgdq2026_runs.json`: JRisJunior runs 2–4 → one block;
  TheKingsPride *I Am Your Beast* → *The Checkpoint* (no host) → *Devil May Cry 5* → ONE block; Quacksilver 8–10 → one
  block; and an end-to-end cog test with a real pairing on TheKingsPride.
- **One highlight per block** in `marathon_public_channel_id` (blank → go-live, the runner highlights' resolver),
  posted by the first sync after the block is known (the marathon active, TRACKED, mode not off, Scan hosts on, the key
  on, a public channel resolving, the block not already over), then edited in place: `marathon_host_highlight_template`
  (to come) → `_live_template` (from the moment any of the block's own runs is not upcoming, until all are done) →
  `_done_template`. It rides `Marathons.sync_board`, so every door that refreshes the board moves it; an unchanged
  tick costs no Discord call (in-memory cache; after a restart one fetch + `endswith`, the runner highlights' rule).
- **One heads-up per block** in `marathon_reminder_channel_id` (blank → go-live) `marathon_ping_minutes` (15) before
  the block's first run, skipped and logged past `marathon_reminder_stale_minutes`; only while
  `marathon_public_reminders` is on. Called from `Marathons.follow` right after the runner reminders.
- **Never pings.** Every send and edit is `AllowedMentions.none()`; `{mention}` exists (the runner highlight's
  convention: it names the member without pinging) but the defaults use the bold name, as the runner highlight does.
  No role is ever prefixed — not even with the marathon's `ping_role` on.
- **Bookkeeping** — `marathons.host_highlight_posts TEXT` (JSON list; schema **82 → 83** through `ADDED_COLUMNS`,
  mirrored to `marathons_archive` at boot): per block `{user_id, runs, message_id, channel_id, removed, tried,
  reminded, name, login}`. A record belongs to a block when the host matches and they share a run, so a block that
  moves or grows keeps its post. `tried` and `reminded` are saved BEFORE the send → a restart never double-posts
  (tested with a second cog instance).
- **Shadow** routes like runner highlights: `send_public` / `edit_public` send to the `marathon_public` rehearsal home
  with the note naming the real channel; logs `marathon.would_post_host_highlight`, `would_edit_host_highlight`,
  `would_remind_host`.
- **Staff final say, both doors.** Discord: `/event` ▸ a marathon ▸ **People…** ▸ a slot ▸ the host → **Remove the
  highlight** while it is up, **Highlight in #channel** while it could be (the runner highlight button's own keys; a
  button renders only when valid). Site: the People card's BaF row (every block) and the host's slot line (that block)
  → **Post host highlight** / **Take it down** (confirm). API: **`POST` / `DELETE
  /api/marathons/{id}/people/{user_id}/host-highlight`** (optional `run_id`; the answer is the People board +
  `message`). Take down stores the decision first, then edits the post to `marathon_public_removed` and never edits it
  again; Post puts it back IN PLACE when the message is still in the channel a highlight would go to now, else posts
  anew. The People board's BaF rows carry **`host_highlight`** `{up, channel_id, can_post, blocks: [{runs, up,
  channel_id, can_post}]}` (null for anyone who hosts nothing).
- **Keys (5, Marathons group, registry + mock row + label, listed right after the host keys):**
  `marathon_host_highlights` (bool, **on**) · `marathon_host_highlight_template` · `marathon_host_highlight_live_template`
  · `marathon_host_highlight_done_template` · `marathon_host_reminder_template`. Placeholders `{name} {mention} {show}
  {when} {relative} {until} {link} {url} {games} {runs}` — `{link}` is the host's own Twitch (the pairing's fix wins,
  else the sheet/tracker login), else the marathon's watch link; `{url}` the marathon's. An unknown placeholder is
  refused in words by the Marathons words check (*"`{game}` is not something Black Bloc can fill in…"*).
- **Log kinds:** routine `marathon.host_highlight_posted`, `_edited`, `_restored`, `_removed`, `_lost`,
  `marathon.host_reminded`, `marathon.host_reminder_skipped`; shadow twins above; `marathon.host_highlight_failed`
  (`step: post | edit | remove`) and `marathon.host_reminder_failed` IMPORTANT by suffix. Web:
  `web.marathon.host_highlight_posted / _restored / _removed / _failed`.

**Counts:** schema **82 → 83** · registry keys **714 → 719** (measured: `len(settings_store.KEY_TYPES)`) · routes
**+2** (`check.mjs`: *22 pages, 288 routes*) · new modules `black_bloc/marathon_host_highlights.py` (pure) and
`black_bloc/cogs/content/marathon_host_highlights.py` (not a cog; `bot.py:COGS` unchanged).

### Deviations

1. ~~**The post goes up as soon as the block is known, not on the day.**~~ *(Reversed 2026-09-28 20:4x by the owner — per run, at the runner's moments; see the per-run section.)* "Upcoming" is a real state; with the marathon
   near and tracked, the first tick after deploy posts it. For Hidden Heroes that means **the day it deploys**, days
   before Friday. If the owner wants it later, the lever is a lead-time key (not built).
2. **A post in flight is carried to its end (checklist 38).** The key off stops NEW posts and heads-ups; Scan hosts
   off drops the hosts' `user_id`, so the block can no longer be found — the record keeps its runs, name and login
   and `left_behind` keeps editing the post to *on now* / *done* from those runs (tested both ways).
3. **A failed first post is not retried by the tick** (`tried` is set before the send). Staff's Post move retries it.
   A post deleted by hand is forgotten (`host_highlight_lost`), never re-posted by the tick — the runner rule.
4. **The staff answers reuse the runner highlight's words** (`marathon_public_posted_said`, `_removed_said`,
   `_already_up`, `_not_up`, `_no_channel`, `_failed`) and the taken-down line is `marathon_public_removed`; the
   Discord button labels are `marathon_public_button_post` / `_remove`. Fewer keys; the one oddity is the removed
   answer's *"Highlight puts it back"*, which on the site reads as the **Post host highlight** button.
5. **Bookkeeping is a JSON column on the marathon, not a table** — the host events' precedent (Deviation 1 above):
   archives and restores with the row, a handful of hosts per marathon.
6. **The site's button words are site chrome constants** (`HOST_POST`, `HOST_REMOVE`, `HOST_UP` in
   `marathons-section.js`), as *Spotlight…* is; everything the BOT posts is a key.
7. **No per-marathon switch.** The owner's default is "all members"; `marathon_host_highlights` is the guild switch
   and Scan hosts is the per-marathon one. A per-marathon "not this one" is the staff move (take it down).
8. **The not-hosting and not-scanned refusals are module constants** (staff chrome, the repo's convention for
   refusals), as the host switches' bad word is.

### What was NOT verified

- ⚠️ **Nothing met Discord** — a real post in #upcoming-events, its edits, the heads-up, the slot-view buttons.
- ⚠️ **No browser** — the People card's new buttons were never rendered; `node --input-type=module --check` parses
  every asset and `check.mjs` proves the route shapes against the mock (plus a scripted POST/DELETE walk on the
  mock: Rivet on AGDQ 2027 up → taken down; an id who hosts nothing → 404 `not_hosting`).
- **The live migration (schema 83)** has not run; Hidden Heroes' stored runs, anarchy's pairing and whether anarchy's
  sheet row carries a Twitch login were not read.
- **Timing against a real stream**: the *on now* edit follows the run's state, which with a watched channel waits for
  the title/category signal (or the 90-minute grace) — reasoned from `mt.advance`, not observed.

### ~~Live check for Friday — Hidden Heroes (marathon 10), Fri 2026-10-02, Phoenix (UTC−7)~~

> ⚠️ Struck: these block-based expectations never shipped. The per-run table is in *Host highlights, per run*.

Sweep rows **`HS-h` … `HS-l`** in `docs/access/sweeps.md`. Expected, if the first hosted run is at 16:00 Phoenix:

| When (Phoenix) | What |
|---|---|
| the first tick after deploy (Scan hosts already ON) | ONE post in #upcoming-events: **anarchy** hosts **Hidden Heroes** · <start> (in N days) until <end> · anarchy's Twitch link (or the marathon's). Logs ▸ `marathon.host_highlight_posted`. No role mention. |
| Fri 15:45 | ONE heads-up in #upcoming-events: **anarchy** is hosting **Hidden Heroes** in 15 minutes — <start>. <watch link>. Logs ▸ `marathon.host_reminded`. |
| Fri ~16:00, the first hosted run live | The SAME post edited: **anarchy** is hosting **Hidden Heroes** now, until <end> · <watch link>. |
| after the last hosted run is done | The same post: **anarchy** hosted **Hidden Heroes** · <start> · <link>. |
| throughout | No runner post / reminder / shoutout / run highlight for the three runs (the drawer's BaF count stays 0). |

## Host highlights, per run (owner 2026-09-28 20:4x)

> ⚠️ **SUPERSEDED 2026-09-28 by branch `marathon-announcements` (commit `5a60c782`, checklist 35)** — see
> [`marathon-announcements-design.md`](marathon-announcements-design.md). Owner 21:1x: *"host will be in multiple slots
> so dont reannouce until their is a break in a host block … make it a direct mirror of runner except we consider the
> time blocks"*. What changed below: ~~the unit is the run~~ → the unit is the **host BLOCK** again (the block rule of
> the section above, with *The Checkpoint* continuing a block); ~~once, at `marathon_ping_minutes` (15)~~ → **every
> `marathon_reminder_minutes` mark** from the block's first run; ~~one highlight per run~~ → one per block, at the
> block's live, edited to done after its last run; ~~staff **Highlight in #…** / **Post host highlight** / **Take it
> down**, and the `host-highlight` routes~~ → **Opt out of highlight** / **Opt back in** per person per marathon
> (`POST`/`DELETE …/people/{user_id}/opt-out`); the People board's ~~`host_highlight`~~ → `opted_out`. Kept: one
> template and one renderer with the runner (owner 20:5x), never pings, shadow routing, `tried`/marks saved before the
> send, checklist 38. The `host_highlight_posts` column is re-keyed by the block's first run; a per-run record from this
> section reads as a one-run block.

> **BUILT 2026-09-28 on branch `host-highlights-per-run` (worktree `C:/lcw/bb-host-highlights-per-run`, off `main`
> `2b6f378b`), NOT MERGED, NOT DEPLOYED.** Code commit `30199332`. **Last verified: 2026-09-28** by the suite
> (`tests/test_marathon_host_highlights.py`, `tests/cogs/content/test_marathon_host_highlights.py`, the slot-view test in
> `tests/cogs/content/test_marathon_people.py`, the route test in `tests/api/tools/test_marathons.py`, the contract
> test's seeded host) and `node site/mock/check.mjs` on `MOCK_PORT=8917`. ⚠️ Nothing met Discord, a browser or the live
> database. Replaces the block-based section above (checklist 35).

**The asks, verbatim.** Owner 20:4x: *"how soon before a run do we post that runner? lets do the same for host, then
every next line item they appear in post them again. meaning anarchy will get posted 3 times during hidden heroes"*.
Owner 20:5x: *"we can say Anarchy will be hosting Titanfall 2 at 7pm on GDQ twitch page in upcoming, the same way we'd
say, Anarchy will be running Titanfall 2 at 7pm on GDQ twitch page. make them match you know"* — one template, one
renderer, so the two can never drift.

**What a runner gets (measured by the conductor 20:4x), and so what a host now gets, per run:**

| | Runner (BaF run) | Host (a run a BaF host hosts) |
|---|---|---|
| Heads-up | the public copy of the reminder in `marathon_reminder_channel_id`, `marathon_public_reminder_template` | **the same template, the same renderer** (`marathon_public_reminders.reminder_text` → `mt.run_fields`); `{member}` = the BaF host(s), `{part}` = `marathon_part_host` (*hosts*) |
| When | every mark in `marathon_reminder_minutes` (`120, 15` by default) | **once, at `marathon_ping_minutes` (15)** — the owner's measured *"is up in 15 minutes"* copy |
| Switches | `marathon_public_reminders`; `marathon_reminder_stale_minutes` skips a late one | the same two, plus `marathon_host_highlights` (master) and the marathon's Scan hosts |
| Highlight | `marathon_public_template` in `marathon_public_channel_id`, when the run goes live with the marathon's **Auto-highlight** (`public_highlight`) on, or staff press **Highlight** | **the same template and renderer** (`marathon_public.public_text` with `people=`), at the same moment: the run's LIVE transition (`Marathons.advance`, and staff **Mark live**) with Auto-highlight on, or staff press it for that run |
| Edited | in place as the run moves / goes live / ends (`{state}`) | the same: *coming up* → *on now* → *done* |

- ~~**The unit is the run.**~~ *(reversed by `marathon-announcements` — the unit is the host block)* `marathon_host_highlights.hosted` lists every non-dropped run with at least one BaF host
  (a host with a `user_id`, i.e. only while the marathon scans its hosts). No block, no span; nothing posts days early.
- **Co-hosts follow the runner convention: ONE post per run naming every BaF host on it** (`{member}` is
  `mt.mention_line` of them, `{runner}` their names joined by `, `), exactly as a run with two BaF runners gets one
  reminder and one highlight. A non-BaF co-host is not named.
- **Hosts still never make a run ours**: `mt.ours` is untouched; the host path passes its people explicitly
  (`people=` on `mt.run_fields`, `mt.run_url`, `mrp.fields_of` / `post_text`, `mp.text_of`, `public_text`,
  `reminder_text`), so no runner post / reminder / shoutout / run event appears for a hosted run (tested: `counts_of`
  stays `(3, 0)`).
- **Never pings.** Every send and edit is `AllowedMentions.none()`, no role prefix. `{member}` renders `<@id>` as it
  does for a runner, without pinging.
- **Bookkeeping:** `marathons.host_highlight_posts` (schema **83**, unchanged) is re-keyed per run:
  `{run_id, hosts: [{user_id, name, login, part}], message_id, channel_id, removed, tried, reminded}`. `reminded` and
  `tried` are saved BEFORE the send → a restart never double-posts (tested with a second cog instance). **No data
  migration:** the block build was merged but never deployed, so the live column does not exist yet / is empty
  (reasoned from the TODO and the release history — the live database was not read); an old-shape record (no
  `run_id`) is simply ignored.
- **A run that moves later is due again** (`rearm`), as a runner's reminder is re-armed by `mt.rearmed` on a
  refresh / retime.
- **Auto-highlight is tried once per run**: `auto_wanted` needs the switch on, the run LIVE and no record that was
  tried or taken down — staff's **Remove** is never undone by the switch (the runner rule).
- **A post already up follows its run to the end** after the key or Scan hosts goes off (`left_behind` uses the
  hosts stored on the record; checklist 38).
- **Staff final say, per run, both doors, same words.** Discord slot view: **Highlight in #channel** /
  **Remove the highlight** for that slot's run. Site: the host's slot line (that run) and the BaF row (no `run_id`:
  every hosted run the move fits — Post posts the ones not up, Take it down takes down the ones up). API paths
  unchanged: `POST` / `DELETE /api/marathons/{id}/people/{user_id}/host-highlight` with optional `run_id`. The People
  board's **`host_highlight`** is now `{up, channel_id, can_post, runs: [{run_id, up, channel_id, can_post}]}` (was
  `blocks: [{runs, …}]`); `can_post` also needs the run upcoming, live or done.
- **Keys:** `marathon_host_highlights` stays (bool, on, re-described). ~~`marathon_host_highlight_template`,
  `_live_template`, `_done_template`, `marathon_host_reminder_template`~~ **removed** (never deployed → no settings
  migration) — the owner's *"make them match"*. Registry **719 → 715** (measured: `len(settings_store.KEY_TYPES)`).
- **Log kinds unchanged**; `details` now carry `run_id`, `members` (list), `hosts` (names), `game` instead of
  `member_id` / `host` / `runs`.

~~**Hidden Heroes walk-through (marathon 10, Fri 2026-10-02, Phoenix UTC−7).**~~ *(Struck: the per-run table never
ran on a Friday; the current one is in `marathon-announcements-design.md` — Thu 16:00, Fri 14:00, Fri 15:45.)* From the Hotfix sheet fixture
(`tests/fixtures/marathon/gdq_hotfix_sheet.csv` rows 26–28: the 7:00 PM ET show, 1:25 / 0:35 / 0:50): Titanfall 2
16:00–17:25, VHOLUME 17:25–18:00, SPRAWL zero 18:00–18:50 Phoenix. Auto-highlight is OFF on Hidden Heroes.

| When (Phoenix) | What |
|---|---|
| before Fri 15:45 | nothing for anarchy (no post the day it deploys) |
| Fri 15:45 | #upcoming-events: `@anarchy hosts **Titanfall 2** (Any%) on **Hidden Heroes** in 15 minutes — <16:00>. <watch link>` — `marathon.host_reminded` |
| Fri 17:10 | the same for **VHOLUME** (All Main Levels), 17:25 |
| Fri 17:45 | the same for **SPRAWL zero** (Any%), 18:00 |
| whenever staff press **Highlight in #…** / **Post host highlight** on a hosted slot | ONE highlight for that run in `marathon_public_channel_id`: `**anarchy** hosts **<game>** — <category> on **Hidden Heroes** · <when> · <state> · <link>`, then edited to *on now* / *done* |
| if Auto-highlight is turned ON beforehand | a highlight at each run's live (≈16:00, 17:25, 18:00), each edited to *done* |
| throughout | no runner post / reminder / shoutout / run highlight for the three runs; BaF count 0; no role mention |

(Times follow the runs' stored `scheduled_at`: a stream-driven retime moves them, and the heads-up with them.)

### Deviations

1. ~~**One heads-up per run, at `marathon_ping_minutes` only**~~ *(reversed by `marathon-announcements`: one per host block at every mark, as the owner asked 21:1x)* — a runner also gets a public copy at every other
   `marathon_reminder_minutes` mark (120 by default). The brief and the owner's measured example name the 15-minute
   copy; a 2-hour host copy is not built.
2. **Auto-highlight fires at the LIVE transition** (`Marathons.advance` and `mark_live`), like the runner's, not on a
   later tick — turning Auto-highlight on mid-run does not post the run already live (staff press it).
3. **The BaF-row move without `run_id`** acts on every hosted run it fits (the block build's "every block"
   semantics carried over); the slot line is the per-run door.
4. **`{member}` in the heads-up is a mention** (`<@id>`, never pinging) — the runner copy's own convention, kept so
   the two match.

### What was NOT verified

- ⚠️ **Nothing met Discord or a browser**; the People card's per-run buttons were not rendered (JS parses;
  `check.mjs` green on the mock).
- **The live DB was not read**: that `host_highlight_posts` is empty live, Hidden Heroes' stored run times, anarchy's
  pairing / Twitch login, the live `marathon_ping_minutes` / `marathon_public_reminders` / reminder channel.
- **The watch link** for Hidden Heroes (`channel_login` of the marathon, else the host's Twitch) was not resolved live.
- Timing against a real stream (the LIVE transition waits for the title/category signal or the grace) — reasoned,
  not observed.
