# People unify — hosts always found, one BaF run/host events switch, one set of moves per person

> ⚠️ **2026-10-06 — announce-overrides (branch `announce-overrides`, 🔨 BUILT, NOT MERGED):** **§6's six thread-control buttons are seven** (a **Host announcements** switch sits after BaF announcements), and **§4's one set of moves per person gains two** — this run's own answer and the @ — the same for a runner and a host. Hosts are still always found; what changed is that a host is **not announced by default**. See [`announce-overrides-design.md`](announce-overrides-design.md).

> 🔨 **BUILT 2026-09-28 on branch `people-unify` (worktree `C:/lcw/bb-people-unify`, off `main` `d3916a42`; v193
> live, schema 84), NOT MERGED, NOT DEPLOYED.** Code commits `ff228b39` (Python, contract, tests) and `87694fb2` (site,
> mock), then docs.
>
> **Audience:** the conductor, reviewers, and the next session touching marathon hosts, run events, the thread controls
> or the People card. **Status:** TRACKED. **Last verified: 2026-09-28** — against the branch's own code by the suite
> (`pytest -n 16`: 9850 passed), `ruff check .`, the ten node tests `deploy.ps1` runs, `node --input-type=module --check`
> on every `site/**/*.js|mjs`, and `node site/mock/check.mjs` on `MOCK_PORT=8921` (*22 pages, 288 routes, 26 core
> settings, all keys present*) plus a scripted walk of that mock (below). ⚠️ **NOT checked:** anything against Discord,
> a browser, the live database or the live settings. Secret NAMES only.

## The asks, verbatim (owner, 2026-09-28 22:0x–22:1x Phoenix)

1. *"we dont need the scan host button anymore since it should be auto like runners"*
2. *"in fact 1 step further remove the distinction between runner and host in the ui elements, so tracking and managing
   one does them both"*
3. (22:1x, relayed by the conductor) *"that was a misclick, also combine those buttons too, BaF run/host events"* — GDQueer's
   `host_events` ON was a misclick (the conductor set it back OFF live), so no host-only mode is preserved; the one events
   switch is labelled **BaF run/host events**.

The ENGINE is unchanged on purpose: hosts are announced per host block, hosts never make a run ours
(`marathon_hosts_count_as_ours` stays off), runners are per run.

## As built

### 1. Scan hosts is gone — hosts are always found

- No per-marathon switch, no thread-controls button, no drawer field, no key. `Marathons.rematch` calls
  `mt.match_people` without `scan_hosts` (its default, True); the Hotfix tracker (`marathon_hotfix.matched_of`,
  `cogs/content/marathon_feeds.people_on_blocks`) lost the argument; `cogs/content/marathon_host_highlights.wanted` /
  `blocks_of` no longer ask. Commentators still follow `marathon_match_hosts` as before, and so does a host (the guild
  key that has always gated hosts AND commentators).
- **`marathons.scan_hosts` stays in the schema, unread** — no destructive migration. A stored 0 there changes nothing
  (tested: `test_hosts_are_found_with_no_switch_anywhere`).
- **Key retired:** `marathon_scan_hosts_default` (a stored value is ignored at load, `settings ignored:` log line).

### 2. One events switch for BaF people — **BaF run/host events**

- The switch is the **runs half of `event_mode`** (`runs` / `both`) — the thread's second button, the drawer's Event
  select, `/event` ▸ Event mode…, `PATCH {"event_mode": …}`. ON makes a run event per BaF-runner run (unchanged) AND one
  event per **host block** (`marathon_host_highlights.blocks` — the same blocks the announcements build posts by).
  `cogs/content/marathon_hosts.host_events_on(marathon)` = active AND `me.makes_run_events(mode)`.
- **`set_event_mode` now syncs host events too** (after the run events, under the same lock); its answer counts both
  (*"N run or host block event(s) made / called off"*), and `marathon.event_mode_set` carries `host_blocks` counts.
- **Per block, not per host:** `sync_host_events` claims one record per block; co-hosts on the same runs share one event
  (the title's `{member}` names both); a host with two blocks gets two events. The event runs from the block's first run
  to its last run's end, re-dated as the block moves (`marathon.host_event_redated`), called off when the block is gone
  (`not_host`) or the switch goes off (`switched_off`, only while `marathon_run_event_cancel_on_leave`), and with the
  marathon (`marathon_removed`).
- **Bookkeeping:** `marathons.host_event_ids` now holds a JSON LIST of `{event_id, runs, hosts}` per block. The v190
  shape `{user_id: event_id}` still reads: each becomes a record with no runs, claimed by that host's FIRST block and
  rewritten in the new shape at the next sync (tested: `test_a_per_host_event_from_v190_is_kept_and_claimed_by_the_first_block`).
  A block that grows, shrinks or moves keeps its record (same first run, else a shared host and run). Staff-cancelled
  events stay pointed at and are not re-made (as v190).
- **Log detail shape:** `marathon.host_event_*` now carry `members` (list) and `runs` instead of `member_id`.
- **Key retired:** `marathon_host_events_default`, and with the two switches the six label/answer keys (§ Keys).
  `marathons.host_events` stays in the schema, unread.

### 3. The migration rule (the conductor asks the owner if it matters)

**The unified switch is exactly the marathon's runner-events setting. A stored `host_events` value is ignored after the
upgrade** — no host-only carry-over (the owner's 22:1x: GDQueer's ON was a misclick). Tested on the GDQueer shape
(`host_events = 1`, `event_mode = none`): no host event, no run event; turning the one switch on makes both
(`test_gdqueers_shape_a_stored_host_events_on_with_runner_events_off_makes_nothing`).

Right after the deploy, measured by the conductor's brief (not read live here):

| Marathon | Stored | After the deploy |
|---|---|---|
| GDQueer (9) | `event_mode` none; `host_events` now OFF (was ON 22:03 by a misclick) | No run events, no host events. If a host event was made during the misclick and is still stored, the first sync after deploy calls it off (`switched_off`, the leave key is on) — expected none: v193 called it off when the conductor turned the switch off. |
| Hidden Heroes (10) | both off | No events. anarchy's one block still gets the announcements build's public reminders (unchanged). |

### 4. One set of per-person moves, one part tag

- The site's People card and the Discord slot view already offered the same moves to a runner and a host (Spotlight…,
  Stop spotlighting, Opt out of highlight / Opt back in, Twitch name…, Link / Unlink — decided by how the person was
  matched, never by their part); **no host-only button, label, section or refusal remains** (the last host-only ones —
  *Post host highlight* / *Take it down* — went with the announcements build). Tested with a runner-only, a host-only and
  a both person: identical move sets (`test_a_runner_a_host_and_both_get_one_set_of_moves_and_their_part_tag`).
- **The part tag** is the person's parts in the `marathon_part_*` keys' words joined with ` + ` — *runs*, *hosts*,
  *runs + hosts* (`marathon_hosts.part_tag`). Discord: the BaF block line and the slot line (a BaF person's slot line now
  shows their parts on the WHOLE marathon, not only this slot's). Site: `part_tag` on every People-board row
  (`GET …/people`, the archived board, the contract), shown in the BaF row and the slot line.
- **Spotlight's note:** a person who only hosts keeps `marathon_spotlight_host_note_template` (*{name} hosting
  {marathon}*); anyone who runs gets the runner note. **The host note key is KEPT** — its words are still needed.

### 5. BaF announcements

> ⚠️ **2026-10-08:** renamed **Runner announcements** and no longer a master over hosts — see [`announce-overrides-design.md` § Runner announcements 2026-10-08](announce-overrides-design.md#runner-announcements-2026-10-08).

`marathon_controls_announcements_on/_off` defaults reword to **BaF announcements: on · turn off** / **off · turn on**
(stored custom values are staff's and stay); the drawer field, the refusal (*Say on, off or follow for **BaF
announcements***) and every help text say *BaF announcements*. Behaviour unchanged.

### 6. Thread controls — six buttons, the old ids answer in words

- The controls are: Marathon event · **BaF run/host events** · Spotlight · Auto-highlight · Ping the marathon role · **BaF
  announcements**. `marathon_controls_runs_on/_off` defaults reword to **BaF run/host events: on · turn off** /
  **off · turn on**.
- **Already-posted messages are EDITED on the first tick after boot** (`sync_controls` → `refresh_controls`: the render
  cache is empty after a boot, so the pinned message is edited once to six buttons; never re-sent). Tested:
  `test_after_the_upgrade_the_posted_controls_and_runner_post_are_edited_not_resent` now asserts six buttons and no
  `:hosts:` / `:hostevents:` id.
- **Removed ids still answer** (the template still matches them; `mtc.RETIRED`): `marathon:controls:{id}:hosts:{on|off}`
  → *"The Scan hosts switch is gone — hosts are always found now, like runners, so nothing was changed."*;
  `…:hostevents:{on|off}` → *"The BaF host events switch is gone — events now follow the one **BaF run/host events**
  switch, so nothing was changed."* (refusal code `gone`, 410; nothing written; the press then re-renders the message,
  which drops the stale buttons). Tested through `press` and a real `ControlButton.on_click`.
- `PATCH /api/marathons/{id}` with `scan_hosts` / `host_events` answers the same two sentences in `message` (200, other
  fields in the same body still apply); `GET` no longer carries either.

### Keys (Marathons group: registry + mock row + label)

Removed **10**: `marathon_scan_hosts_default`, `marathon_host_events_default`, `marathon_controls_hosts_on` / `_off`,
`marathon_controls_host_events_on` / `_off`, `marathon_scan_hosts_on_said` / `_off_said`,
`marathon_host_events_on_said` / `_off_said` — a stored value for any is ignored at load. Reworded defaults:
`marathon_controls_runs_on` / `_off`, `marathon_controls_announcements_on` / `_off`. Re-described:
`marathon_hosts_count_as_ours`, `marathon_host_highlights`, `marathon_announcements_default`,
`marathon_public_reminders`, `marathon_announcements_on_said` / `_off_said`, `marathon_host_event_title_template` /
`_description_template` (now *per host block*). Registry **716 → 706** (`len(settings_store.KEY_TYPES)`). The two
retired-switch sentences are module constants (`marathon_hosts.SCAN_GONE` / `HOST_EVENTS_GONE`, staff chrome — the
refusals' convention).

### Counts (measured on the branch)

Schema **84, unchanged** (no step; `scan_hosts` and `host_events` columns left in place, unread). Registry keys **716 →
706**. Routes unchanged (`check.mjs`: *22 pages, 288 routes*). Log kinds: `marathon.scan_hosts_set` and
`marathon.host_events_set` dropped from the classification (never written now; old rows stay readable).
`bot.py:COGS` unchanged; no new module.

### The mock walk (`MOCK_PORT=8921`, scripted fetches)

`PATCH /api/marathons/1 {"scan_hosts": true, "host_events": "on"}` → both sentences, `event_mode` unchanged, no
`scan_hosts` key; `{"event_mode": "none"}` → *…now makes no event. 1 run or host block event(s) called off.*;
`{"event_mode": "runs"}` → *…one event per BaF run and per BaF host block… 5 run or host block event(s) made.*; the
People board reads *Casey: runs, Rivet: runs + hosts, Moth: is on commentary*; the events list holds one *Rivet hosts
AGDQ 2027*. Only the 8921 listener was stopped.

## Deviations

1. **The events switch is the existing runs half, not a new column.** The brief said "fold into the existing
   runner-events control"; the control IS `event_mode`'s runs half, so no schema step and no new key. The select word
   `runs` still means it (API/mock/Discord words now say *An event per BaF run and host block*).
2. **Host events are per BLOCK (the brief), not per host (v190).** A v190 per-host event is claimed by the host's first
   block and re-dated to it; the host's later blocks get new events.
3. **No carry-over for `host_events = 1`** — superseded the brief's migration rule at the owner's 22:1x (misclick).
4. **A retired button's answer is a refusal (410 `gone`)**, so the ephemeral reply reads as "nothing changed"; its words
   are constants, not keys (staff chrome — the refusals' convention; flagged against the every-word rule).
5. **The Discord slot line shows the person's parts on the whole marathon** for a BaF person (the tag), and the slot's
   own part for someone not BaF.
6. **`marathon_match_hosts` still gates hosts** (it always gated hosts and commentators together). "Always scanned"
   means no per-marathon or Scan-hosts switch; turning `marathon_match_hosts` off still stops hosts and commentators
   counting. The feeds test that asserted "not tracked until Scan hosts" now asserts that key instead.
7. **`set_event_mode` now reports cancellations while staying in runs mode** (a dropped run's event called off during
   the same sync) — the old text only reported them on leaving.

## What was NOT verified

- ⚠️ **Nothing met Discord**: the six-button control message after the edit, a real press of an old `hosts` /
  `hostevents` button, a host block event approved against Discord (every test turns `events_create_scheduled` off).
- ⚠️ **No browser**: the drawer without the two host fields and the *runs + hosts* tag were not rendered; `check.mjs`
  and the ES parse are the proof.
- **The live database was not read**: GDQueer's and Hidden Heroes' `event_mode` / `host_events` / `host_event_ids`, and
  whether the misclick left a host event stored (expected none — v193 called it off when the switch went off).
- **A tick's own sync (actor None) failing to propose** a host event in the suite's fakes is pre-existing (v190's
  per-host path behaved the same); a staff door always passes the actor.

## Live check after merge + deploy (sweeps `PU-a…PU-f`)

1. The first tick edits GDQueer's and Hidden Heroes' pinned controls to six buttons (no new message).
2. Settings ▸ Marathons: the ten keys are gone; *BaF announcements* labels read as above.
3. Events ▸ Hidden Heroes ▸ People: **anarchy** ✦BaF *hosts* with Spotlight… / Opt out of highlight — no Scan hosts
   anywhere.
4. Only if the owner wants events: Hidden Heroes ▸ Event ▸ *An event per BaF run and host block* → ONE event *anarchy
   hosts Hidden Heroes* Fri 16:00–18:50 (reviewed while `marathon_mode` is shadow — the run events' rule).
