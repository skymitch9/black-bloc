# Marathon Runner/Host announcements — one switch per marathon, an opt-out per person, hosts posted per host block

> ⚠️ **2026-10-06 — announce-overrides (branch `announce-overrides`, 🔨 BUILT, NOT MERGED):** **§1's *On: every BaF runner and every BaF host is announced* is REVERSED for hosts** — a host is announced only while the marathon's new **Host announcements** switch is on (default **off**, `marathon_host_announcements_default`) or a run says so; the BaF announcements switch stays the master over both. **§2's *opted out = no public post at all on that marathon* now yields to a run's own yes**, and the runner post carries per-person buttons beside the whole-marathon one, whose default labels are reworded (*Opt out of every run on this marathon*). **§3's `{member}` renders `<@id>`** unless the person is written without an @. See [`announce-overrides-design.md`](announce-overrides-design.md).

> ⚠️ **2026-09-28 — people-unify (branch `people-unify`, 🔨 BUILT, NOT MERGED):** the switch is now called **BaF announcements** (label defaults reworded; behaviour unchanged); **Scan hosts is gone** (§4 and the table row below are superseded — hosts are always found); the thread controls carry SIX buttons, not eight (Scan hosts and BaF host events removed; their old ids answer in words). See [`people-unify-design.md`](people-unify-design.md).

> 🔨 **BUILT 2026-09-28 on branch `marathon-announcements` (worktree `C:/lcw/bb-marathon-announcements`, off `main`
> `1d5d017d`; v192 live), NOT MERGED, NOT DEPLOYED.** Code commit `5a60c782`, then docs.
>
> **Audience:** the conductor, reviewers, and the next session touching marathon reminders, highlights, hosts, the
> runner post's button, the thread controls or the People card. **Status:** TRACKED. **Last verified: 2026-09-28** —
> against the branch's own code by the suite (`tests/test_marathon_announce.py`,
> `tests/cogs/content/test_marathon_announce.py`, `tests/test_marathon_host_highlights.py`,
> `tests/cogs/content/test_marathon_host_highlights.py`, `tests/cogs/content/test_marathon_public.py`,
> `tests/cogs/content/test_marathon_public_reminders.py`, the People slot test, the API and contract tests, the schema-84
> test in `tests/storage/test_db.py`), and `node site/mock/check.mjs` on `MOCK_PORT=8919` (*22 pages, 288 routes, 26
> core settings, all keys present*). ⚠️ **NOT checked:** anything against Discord, a browser, the live database or its
> migration, the live settings. Secret NAMES only.

## The ask, verbatim (owner, 2026-09-28 21:1x Phoenix)

*"make host match runner completely, 15 mins before their time slot, 2 hours before their timeslot. host will be in
multiple slots so dont reannouce until their is a break in a host block. if someone is oped in they get no post at all.
Though maybe we should make a button to opt in all BaF Runners and Host and then the individual controls for opting out
runners. so a new button says Runner/Host Annoucements, and then the button that gets posted by each found highlighted
run saus opt out of highlight. also i change my mind we scan host automatically too. make it a direct mirror of runner
except we consider the time blocks i mentioned before."*

The conductor's reading, stated to the owner: *"opted in they get no post"* = **opted OUT**; the 24-hour post of an
earlier proposal is dropped. Then (21:2x, verbatim): *"so we do 3, 24 hours, 2 hours, 15 minutes"* — the conductor set
`marathon_reminder_minutes` = `1440, 120, 15` live. **Nothing here hard-codes a mark**: runners and host blocks follow
whatever that key holds (plus `marathon_ping_minutes`, as before). And (21:4x, verbatim): *"did we edit all of the stuff
in the marathon post to update the new options and runners/host"* — the messages already posted are re-rendered, never
re-sent (§ 5).

## As built

### 1. The per-marathon switch — **Runner/Host announcements**

- **`marathons.announcements INTEGER`** — NULL follows the new guild key **`marathon_announcements_default`** (bool,
  **on**, so today's everyone-is-announced behaviour continues); 1 / 0 is this marathon's own answer. Pure reader
  `marathon_announce.announces`, cog reader `cogs/content/marathon_announce.announces`.
- **On:** ~~every BaF runner and every BaF host of the marathon is announced publicly.~~ *(reversed for hosts 2026-10-06, `announce-overrides`: every BaF runner; a BaF host only while Host announcements is on or a run says so — the owner's "host pings out by default".)* **Off:** nobody on that marathon
  gets a public reminder or a highlight. The staff thread is untouched either way (its reminders, runner posts,
  shoutouts still post).
- **How it sits with the other switches:**

  | Switch | Scope | Gates |
  |---|---|---|
  | `marathon_public_reminders` (guild, on) | every marathon | the public copy of every reminder — **the global master** for reminders; unchanged |
  | **Runner/Host announcements** (per marathon) | one marathon | its public reminders AND highlights, runners and hosts |
  | Auto-highlight (`public_highlight`, per marathon) | one marathon | whether a highlight is posted at all when a run / host block goes live |
  | `marathon_host_highlights` (guild, on) | every marathon | hosts only — the host master, kept |
  | ~~Scan hosts (per marathon, default now **on**)~~ *(retired 2026-09-28, `people-unify` — hosts always found)* | ~~one marathon~~ | ~~whether hosts are BaF at all~~ |
  | a person's opt-out (per marathon) | one person on one marathon | every public post naming them |

  A reminder goes public only when `marathon_public_reminders` AND the marathon's switch are on and someone on it is not
  opted out; a highlight only when Auto-highlight AND the marathon's switch are on and someone is not opted out.
- **Doors, one writer.** `cogs/content/marathon_hosts.set_switch` (the Scan hosts / host events writer, a third
  `which` = `mh.ANNOUNCE`): logs `marathon.announcements_set` (`from`, `to`, `on`, `via`), re-renders the thread
  controls, answers `marathon_announcements_on_said` / `_off_said`. Reached by the **eighth thread-controls button**
  (`marathon:controls:{id}:announce:{on|off}`, labels `marathon_controls_announcements_on` / `_off`), the drawer's
  *Settings for this marathon* ▸ **Runner/Host announcements** (*Follow the setting (on)* / *On* / *Off*) and
  **`PATCH /api/marathons/{id}`** `{"announcements": true|false|null|"follow"}`. `GET /api/marathons/{id}` answers
  `announcements: {own, on, default}`.
- **Checklist 38:** the switch going off stops NEW posts; a highlight already up follows its run / block to *done*
  (tested for runners and hosts).

### 2. The per-person opt-out

- **Storage: `marathons.announce_opt_out TEXT`** — a JSON list of user ids on the marathon row (not a table and not
  `marathon_people`: a pairing can be *everywhere* and a host may not be paired on this marathon at all; the host
  bookkeeping's precedent — archives and restores with the row).
- **Opted out = no public post at all on that marathon:** no reminder at any mark, no highlight. On a run or block with
  two BaF people and one opted out, the post goes out naming only the other (and the reminder's watch link is
  recomputed without the opted-out person's Twitch).
- **One writer, `cogs/content/marathon_announce.set_opt_out`** (under the marathon lock). It posts nothing. It refuses in
  words a word it does not know (422 `bad_opt`) and an id that is not a BaF runner or BaF host of the marathon (404
  `not_baf`). On a change it logs `marathon.announce_opted_out` / `marathon.announce_opted_in` (`members`, `via`), then:
  an **opt-out takes down** every highlight (runner or host) that now names nobody — the decision stored first, the
  message edited to `marathon_public_removed`, never deleted; an **opt-in puts back IN PLACE** (an edit, never a new
  post) each of their highlights that was taken down while its run / block is not over. Then `sync_board` re-renders the
  runner posts' buttons. Answers `marathon_announce_opted_out_said` / `_opted_in_said`.
- **Doors (staff final say both ways):**
  - **The button on each runner post** in the staff thread — **Opt out of highlight** / **Opt back in**
    (`marathon_public_button_opt_out` / `_opt_in`), custom id `marathon:highlight:{marathon_id}:{run_id}:{optout|optin}`
    (`HighlightButton`, persistent, staff-gated). It toggles every BaF person on that run; it reads *Opt back in* only
    while all of them are out.
  - **The People slot view** (`/event` ▸ a marathon ▸ **People…** ▸ a slot ▸ a BaF person, runner or host) — the same
    two words, same writer.
  - **The site's People card** — the BaF row and a BaF person's slot line show **Opt out of highlight** (confirm) or
    *Opted out of public posts* + **Opt back in**; **`POST` / `DELETE /api/marathons/{id}/people/{user_id}/opt-out`**
    (the answer is the People board + `message`). The board's BaF rows carry **`opted_out`** (bool; null for non-BaF).
- **Buttons posted before this build** (`…:post` / `…:remove`) keep answering: the template still matches them and
  `marathon_public.move_of` maps **Highlight → Opt back in** and **Remove the highlight → Opt out**. They are replaced by
  the new button on the first sync after boot (§ 5).

### 3. Hosts mirror runners, per HOST BLOCK

- **The block** (`marathon_host_highlights.blocks`): in schedule order, a BaF host's block runs on across the runs they
  host AND runs with no host listed (GDQ's *The Checkpoint*); a run someone else hosts ends it; dropped runs are off the
  schedule. Hosts whose blocks cover exactly the same runs share ONE block (one post naming both — the runner
  convention); co-hosts whose spans differ get a block each. A Hotfix show hosted throughout is one block. Pinned on
  `tests/fixtures/marathon/gdq_sgdq2026_runs.json`: JRisJunior 2–4, TheKingsPride 5 → *The Checkpoint* → 7, Quacksilver
  8–10 — three blocks.
- **Reminders:** the runner's public reminder (`marathon_public_reminder_template`, rendered by the runner's own
  `reminder_text` → `mt.run_fields`, `{member}` = the block's BaF hosts, `{part}` = `marathon_part_host`) at **every
  `marathon_reminder_minutes` mark** (and `marathon_ping_minutes`) measured from the **block's first run**, in
  `marathon_reminder_channel_id` — the runner's `mt.due_marks` (latest due mark wins, anything past
  `marathon_reminder_stale_minutes` is skipped and logged, never posted late) and `mt.rearmed` (a block that moves later
  forgets the marks ahead). **Nothing is posted per run inside the block.** `{game}` / `{category}` / `{when}` are the
  block's FIRST run's (the template has no list field; see Deviations).
- **Highlight:** with Auto-highlight on, ONE highlight (`marathon_public_template`, the runner's renderer) when the block
  goes live (any of its runs going live — `Marathons.advance` or staff **Mark live**), never again once tried or taken
  down; edited in place as the block moves: *coming up* → *on now* (from the first live run until the last is done, so
  also between runs) → *done* after its last run.
- **Never pings:** every host send and edit is `AllowedMentions.none()`, no role prefix. `{member}` renders `<@id>`.
- **Bookkeeping — `marathons.host_highlight_posts`** (schema 83, re-keyed, no data migration): per block
  `{start_run_id, runs, hosts, message_id, channel_id, removed, tried, marks}`. A record is the block's when it starts
  where the block starts, else when it shares a host and a run — so a block that grows, shrinks or moves keeps its post
  and marks. `marks` and `tried` are saved BEFORE the send → a restart never double-posts (tested with a second cog
  instance).
- **A per-run record from `host-highlights-per-run`** (v192, the one just shipped) reads as a one-run block keyed by its
  run (`records` → `_record`). If it said `reminded`, every mark already behind the block's start counts as sent (no
  second 15-minute copy); a post of it that is up is claimed by its block and **edited** into the block's words (tested).
  **What this build found:** only in tests — the live column was not read. By the brief, anarchy's per-run 15-minute
  heads-ups were due Fri 15:45 at the earliest and Auto-highlight is off on Hidden Heroes, so the live column is expected
  empty.
- **Shadow** routes like runners (`marathon_public` rehearsal home, the note naming the real channel); logs
  `marathon.would_remind_host` / `would_post_host_highlight` / `would_edit_host_highlight`.
- **Skips are logged** `marathon.host_reminder_skipped` with `because`: `late`, `public_reminders_off`,
  `announcements_off`, `opted_out`. The runner's public copy logs `marathon.public_reminder_skipped` with
  `announcements_off` / `opted_out` beside the existing `same_channel`.

### 4. ~~Scan hosts automatic~~ — superseded 2026-09-28 by `people-unify`: there is no Scan hosts switch at all

`marathon_scan_hosts_default` now defaults **on** in the registry (and the mock). Every marathon whose own Scan hosts is
NULL scans its hosts. Hosts still never make a run ours (`marathon_hosts_count_as_ours` stays off). The conductor also
sets it live after deploy (a stored `false` would override the new default).

### 5. What is already posted picks up the new state (owner 21:4x)

No new message; the existing re-render paths, all tested as EDITS of a pre-existing message after a restart
(`test_after_the_upgrade_the_posted_controls_and_runner_post_are_edited_not_resent`,
`test_a_host_post_already_up_from_the_last_build_is_edited_in_place`):

- **Thread controls:** `sync_controls` → `refresh_controls` on the first tick of every tracked marathon; its cache is
  empty after a boot, so the pinned message is edited once to the eight buttons (incl. the v190 Scan hosts / BaF host
  events and the new Runner/Host announcements).
- **Runner posts:** `sync_board` → `sync_posts`: after a boot each post is fetched and its shown button compared
  (`marathon_public.shown_button`); an old `:post` / `:remove` button differs from the new `:optout` / `:optin`, so the
  post is edited once. This runs where `follow` runs — active marathons within `marathon_lead_days` (GDQueer and Hidden
  Heroes are). A post on a marathon further out keeps its old button until it comes near; that button still answers as
  the toggle.
- **Host posts already up** (none expected live): `sync_host_highlights` after a boot fetches and compares with
  `endswith`, and edits into the block's words.

### Keys (Marathons group: registry + mock row + label)

Added **9**: `marathon_announcements_default` (bool, on), `marathon_controls_announcements_on` / `_off`,
`marathon_announcements_on_said` / `_off_said`, `marathon_public_button_opt_out` / `_opt_in`,
`marathon_announce_opted_out_said` / `_opted_in_said`. Removed **8** (the manual Highlight press is gone):
`marathon_public_button_post` / `_remove`, `marathon_public_posted_said`, `_removed_said`, `_already_up`, `_not_up`,
`_no_channel`, `_failed` — a stored value for any of them is ignored at load (`settings ignored:` log line), nothing
breaks. Changed default: `marathon_scan_hosts_default` → **on**. Re-described: `marathon_host_highlights`,
`marathon_public_reminders`, `marathon_public_removed`, `marathon_public_auto_off_said` (its default no longer mentions
the Highlight button). The two refusals (`bad_opt`, `not_baf`) are module constants (staff chrome, the host switches'
precedent); the site's button words are site chrome constants in `marathons-section.js`.

### Log kinds

Routine `marathon.announcements_set`, `marathon.announce_opted_out`, `marathon.announce_opted_in` (+ `web.` twins via
`kind_via`); the host / runner highlight and reminder kinds are unchanged, with new `because` values on the skips and
`because: opted_in` on a restored runner highlight. Web `web.marathon.host_highlight_posted` / `_restored` / `_removed`
/ `_failed` are gone with their routes (the Discord-side `marathon.host_highlight_removed` / `_restored` remain, written
by the opt-out / opt-in).

### Counts (measured on the branch)

Schema **83 → 84** (`SCHEMA_VERSION`; `marathons.announcements`, `marathons.announce_opt_out` through `ADDED_COLUMNS`,
mirrored to `marathons_archive` at boot). Registry keys **715 → 716** (`len(settings_store.KEY_TYPES)`). Routes
unchanged in number: `POST`/`DELETE …/people/{user_id}/host-highlight` replaced by `POST`/`DELETE
…/people/{user_id}/opt-out` (`check.mjs`: *22 pages, 288 routes*). New modules `black_bloc/marathon_announce.py` (pure)
and `black_bloc/cogs/content/marathon_announce.py` (not a cog; `bot.py:COGS` unchanged).

## Deviations

1. **The manual Highlight press is retired, runner and host alike.** The brief made the runner post's button an
   opt-out that *"never posts anything itself"*; mirroring that, the host's **Post host highlight** / **Take it down**
   (site and slot view) and the `host-highlight` routes are gone. A highlight now comes only from Auto-highlight; staff
   take one down by opting the person out and put it back by opting them in. `marathon_public.post_highlight` stays (the
   auto path uses it).
2. **The runner post's button toggles EVERY BaF person on the run** (one button per run, as before); it reads *Opt back
   in* only while all of them are out. Per-person control of a shared run is the People slot view / site.
3. **A mark that passes while someone is opted out (or the switch is off, or public reminders are off) is consumed, not
   saved for later** — opting back in resumes at the NEXT mark, never a late catch-up (the brief's *"posts resume at the
   next mark"*). For runners the mark is consumed anyway (the staff copy still posts).
4. **Opt-in puts a taken-down highlight back in place only while its run / block is not over**; an opt-in after the
   live moment does not post a highlight that was never posted (the button never posts).
5. **The taken-down line still names who it was posted for** (`marathon_public_removed`, *Staff took down the highlight
   for **{runner}**…*) — the key is staff-editable if the owner wants it nameless.
6. **`{game}` in a block's posts is the block's FIRST run's game** (with its category and time); the runner template
   has no list field, and a list would pair one category with many games.
7. **The block's highlight fires when ANY of its runs goes live** (not only the first), once — so a first run that is
   skipped, or staff **Mark live** on a later run, still gives the block its one highlight.
8. **Co-hosts share a block only when their spans cover the same runs**; otherwise each host has their own posts.
9. **Scan hosts on by default also widens the Hotfix feed's person tracking** — `marathon_hotfix_track_people` counts a
   paired BaF HOST only while `marathon_scan_hosts_default` is on, so shows a BaF person hosts are now tracked (the
   `hotfix-picker` rule, unchanged in code).
10. **The switch reuses the Scan hosts writer** (`marathon_hosts.set_switch`, a third `which`) rather than a new one —
    one canonical nullable-switch writer.
11. **Where a runner or host is opted out on a shared post, the post names the rest** rather than skipping the run.

## What was NOT verified

- ⚠️ **Nothing met Discord**: the eight-button pinned control message (two action rows) was not seen rendered; the
  opt-out press on a real runner post; the re-render of the live runner posts and controls after the deploy; a real
  public post in #upcoming-events.
- ⚠️ **No browser**: the drawer's new switch and the People card's opt buttons were not rendered (`node
  --input-type=module --check` parses every asset; `check.mjs` proves the route shapes on the mock).
- **The live database was not read**: `host_highlight_posts` on Hidden Heroes, whether any per-run record exists, the
  live stored `marathon_scan_hosts_default` / `marathon_reminder_minutes` / `marathon_reminder_stale_minutes`, GDQueer's
  own Scan hosts and whether it has a BaF host.
- **The live migration (schema 84)** has not run; every marathon will read `announcements` NULL (follow: on) and nobody
  opted out.
- **Timing against a real stream**: when a block goes *done* follows the last run's state — without a stream signal the
  schedule alone ends a live run at its end + `marathon_late_grace_minutes` (90) — reasoned from `mt.advance`, not
  observed.

## Friday walk-through — Hidden Heroes (marathon 10), Phoenix (UTC−7, no DST)

Runs from the Hotfix sheet: Titanfall 2 Fri 2026-10-02 16:00–17:25, VHOLUME 17:25–18:00, SPRAWL zero 18:00–18:50;
anarchy hosts all three → **one block**, 16:00–18:50. Live settings measured by the conductor: marks `1440, 120, 15`,
`marathon_ping_minutes` 15, Auto-highlight OFF on Hidden Heroes, Hidden Heroes' own Scan hosts ON, reminder channel
#upcoming-events. Assumes the deploy lands before Thu 16:00 and nobody is opted out.

| When (Phoenix) | What |
|---|---|
| first tick after the deploy | Hidden Heroes' pinned control message EDITED to eight buttons, the last *Runner/Host announcements: on · turn off*. No public post. |
| **Thu 2026-10-01 16:00** | ONE post in #upcoming-events: *@anarchy hosts **Titanfall 2** (Any%) on **Hidden Heroes** <in 1 day> …* (the runner reminder's words, host part word). Logs ▸ `marathon.host_reminded` `mark` 1440, `runs` = the three. No role ping. |
| **Fri 14:00** | the same, `mark` 120. |
| **Fri 15:45** | the same, `mark` 15. |
| Fri 17:10, 17:45 | NOTHING (no per-run posts inside the block). |
| throughout | no runner post / reminder / shoutout / highlight for the three runs (BaF count 0). |
| if Auto-highlight is turned ON before 16:00 | ONE highlight at ≈16:00 (*…hosts **Titanfall 2** … · on now …*), still *on now* between runs, edited to *done* after SPRAWL zero is done (18:50 + up to the 90-min grace without a stream signal). |
| if anarchy is opted out | nothing at all (skips logged `because: opted_out`); **Opt back in** → the next mark posts. |
| if the marathon's Runner/Host announcements is Off | nothing at all (`because: announcements_off`). |

If the deploy lands later than Thu 16:30 (the 30-minute stale window), the 24-hour post is skipped (logged `late`) and
the 14:00 and 15:45 posts still go.

## GDQueer walk-through — a BaF runner (marathon 9), Phoenix

JR (juniorsm) runs **Denshattack!** Sat 2026-10-03 12:50; The_Mathcat runs **Ring Racers** Sun 10-04 11:43. Runners are
unchanged: the public copy at every mark, per run, in #upcoming-events (the staff thread gets its own copy as before).

| When (Phoenix) | What |
|---|---|
| Fri 10-02 12:50 · Sat 10:50 · Sat 12:35 | JR's three public reminders for Denshattack! (`mark` 1440 / 120 / 15; the 15-minute one carries the role ping only if GDQueer's *Ping the marathon role* is on). |
| Sat 10-03 11:43 · Sun 09:43 · Sun 11:28 | The_Mathcat's three for Ring Racers. |
| the runner post in GDQueer's thread | reads **Opt out of highlight**; pressing it → *JR is opted out of GDQueer's public posts…*, the button becomes **Opt back in**, and JR's remaining marks post nothing publicly (the thread copy still does). |
| highlight | none — Auto-highlight is off on GDQueer. |
| hosts | GDQueer follows the Scan hosts default, now on: a paired BaF host there would get block posts too (not verified live). |

## Follow-up 2026-10-05 — one copy of a reminder, the public one

Owner, verbatim: *"why is the annoucement timing post, posting in upcming events and in the event in marathons"* → *"keep only the upcoming events copy"*.

- New key `marathon_thread_reminders` (bool, **off**). `Marathons._post_reminder` now sends the public copy FIRST and returns when it went out; the copy in the marathon's own thread is sent only when the key is on, or when no public copy went out.
- No public copy means any of: `marathon_public_reminders` off, the marathon's announcements switch off, every runner opted out, the reminder channel is the thread's own channel (`same_channel`), no reminder channel, or the send failed. In each the thread copy posts as before, so a mark is never silent.
- The same-channel check reads the thread's place from `_place` before anything is sent — the same id `_send` used to hand back.
- A public-only reminder writes `marathon.public_reminded` and NO `marathon.reminded` row; the run remembers `{posted: true, public: {...}}` with no `staff` copy, which the edit-in-place follower already handles (it walks the copies that exist).
- Host heads-ups were always public-only (`marathon_host_highlights.heads_up`); nothing changed there.
- NOT changed: the dropped-run words, shoutouts, runner posts and the near-miss posts still go in the thread.

