# BaF event ping — one Marathon-role ping per show-day on a BaF event

> **Audience:** the conductor, reviewers, and the next session touching marathon reminders, the Marathon role, the
> thread controls or the Marathon tracker. **Status:** TRACKED · 🔨 **BUILT on branch `baf-event-ping` (off `main`
> `2c2a256b`), NOT merged, NOT deployed.** `SCHEMA_VERSION` **unchanged (89)** — three nullable columns through
> `ADDED_COLUMNS`. Registry keys **867 → 897** (+30). Routes unchanged (`check.mjs`: *25 pages, 312 routes*); two
> payloads gained fields and `PATCH /api/marathons/{id}` takes one more. Log kinds **+4**.
> **Last verified: 2026-10-06 Phoenix** — against the branch's own code by its tests
> (`tests/test_marathon_baf_event.py`, `tests/cogs/content/test_marathon_baf_event.py`, the new tests in
> `tests/api/tools/test_marathons.py`, `tests/api/tools/test_marathon_schedule_page.py`,
> `tests/test_marathon_schedule_page.py`, `tests/test_settings_store.py`, `tests/storage/test_db.py`,
> `tests/test_marathon_thread_controls.py`, `tests/test_marathon_role_ping.py`,
> `tests/cogs/content/test_marathon_host_highlights.py`), the whole suite, `ruff check .`, `node site/mock/check.mjs`
> against a mock started from the worktree on `MOCK_PORT=8801`, every `site/mock/*.test.mjs`, and one look in a
> browser at the mock's tracker page and marathon drawer. The exact counts are in the build's final report.
> ⚠️ **NOT checked:** anything against Discord — no real role was pinged, no question was posted, no button was
> pressed in a real client, and **whether the Leads role is notified in a marathon thread can only be proven in
> Discord**; the live database and every live key; the live migration (three `ALTER TABLE`s at boot); the bot was
> never run. Secret NAMES only.

## How it worked before (measured on the live bot 2026-10-06)

Each BaF run gets a public heads-up at every mark of `marathon_reminder_minutes` (live: `1440, 120, 15`). The
Marathon role (`marathon_role_id`) was mentioned once on the public copy of the `marathon_ping_minutes` (15)
heads-up of **every** BaF run and of a BaF host block, when the marathon's ping switch and `marathon_role_pings`
were on ([`marathon-role-ping-design.md`](marathon-role-ping-design.md)). On a show where every run is ours that is
one role ping per run.

## The ask and the answers, verbatim (owner, 2026-10-06)

> *"BaF only events when its going to be multiple runs back to back we will only ping marathon role once per event
> day 2 hours before the start of the run. everything else stays the same."*

1. How the bot knows an event is BaF-only — **"c"**: automatic AND a staff switch. Then: *"I think we should
   @leads if an event is say 75% BaF runs maybe? basically we should try and know and ping leads if we arent
   sure."* and *"the github pages schedule, that should be marking events as BaF right? like was today marked as
   BaF"* (measured: yes — that day's marathon came from the source with the show name *Black in a Flash*).
5. Learning late — **"a"**: if the bot learns it is a BaF event after the 2-hour mark has passed, ping once at the
   next heads-up instead.

## A. Is this show-day a BaF event?

`black_bloc/marathon_baf_event.py:judge` (pure) answers **yes**, **no** or **unsure** with one reason, in this order:

| # | Rule | Answer · reason |
|---|---|---|
| 1 | The marathon's own answer, `marathons.baf_event` (NULL follow / 1 yes / 0 no) | yes or no · `staff` |
| 2 | The show's name contains a name in `marathon_baf_event_names` — capitals, spaces and punctuation set aside, so *Black in a Flash: Soul Train* matches | yes · `name` |
| 3 | Every run of the day has a BaF **runner**, and the day has at least `marathon_baf_event_min_runs` runs | yes · `all_runs` (fewer: no · `few_runs`) |
| 4 | The share of runs with a BaF runner is at least `marathon_baf_event_ask_percent` and under 100 | unsure · `share` |
| 5 | Otherwise | no · `mixed` (`no_runs` when the day is empty) |

- **A BaF runner** is a matched person whose part is *runner* and who counts (`has_runner`). A BaF host or
  commentator never makes a run a BaF run here, whatever `marathon_hosts_count_as_ours` says for other features.
- **The show's name** is the marathon's name, and for a `gdq_hotfix` marathon also the show part of its
  `source_ref` (`black-in-a-flash/2026-10-06`), so a staff rename does not lose rule 2.
- **A show-day** is `marathon_overlay.chains` (three hours with nothing on starts a new one) — the early-start
  guard's day. Dropped runs are not counted.
- **Unsure is treated as no** until staff answer.

## B. Asking Leads

Once per marathon, on the minute tick (`cogs/content/marathon_baf_event.py:sync` → `ask_if_unsure`, with the
marathon's lock held), when the marathon follows the schedule, a day still to come is unsure and the marathon has
its thread in the current home: **one message in the marathon's staff thread**, the role in
`marathon_baf_event_ask_role_id` mentioned in front (`AllowedMentions` for that one role; blank = no mention), the
words from `marathon_baf_event_ask_text`, and two persistent buttons (`AskButton`, custom id
`marathon:bafevent:{id}:{yes|no}`, registered in `Marathons.cog_load`).

- **Never twice:** `marathons.baf_event_ask` holds a claim written *before* the post, then the message. Once it
  holds a message id — or a claim with no failure — nothing is asked again, whatever the schedule does later and
  whether or not it was answered. A post that failed logs `marathon.baf_event_ask_failed` once and is tried again
  after 10 minutes.
- **A press** is staff-gated (`still_staff`, the standing worded refusal), defers, and goes through the one
  writer. The question is then edited to its own words plus `marathon_baf_event_answered` (*who* answered *what*);
  the edit mentions nobody and the buttons stay, so the answer can be changed there too.

## C. The staff switch — one writer

`set_baf_event(bot, guild, actor, marathon, given, *, via, by)` takes follow / yes / no (or None / True / False),
writes `marathons.baf_event`, logs **`marathon.baf_event_set`** (`web.` from the site) with `from`, `to`, `via` and
`by` (`question` for the buttons), edits the question if one is up, and re-renders the thread controls. Doors:

| Door | What it is |
|---|---|
| Thread controls | three buttons in a row of their own (`marathon:controls:{id}:baf:{follow|yes|no}`), the one that stands lit and not pressable; one line per show-day under the ping switch's line |
| Marathon drawer ▸ Settings | *BaF event*: Follow the schedule (*what was worked out*) / Yes / No, each show-day's line under it |
| `PATCH /api/marathons/{id}` | `baf_event`: `"follow"` / `"yes"` / `"no"` (or null / true / false); anything else is refused in words (`bad_baf_event`) |
| The question's buttons | yes / no |

`GET /api/marathons/{id}` answers `baf_event`: `own`, `choice`, `answer`, `reason` (and their words),
`worked_out` (the answer ignoring staff), `asked`, `ping_minutes`, `ping_fell_back`, `days[]` (each: `starts_at`,
`answer`, `reason`, `runs`, `baf`, `over`, `governed`, `pinged`, `carrier`, `line`), `lines[]`, `all_governed`.

## D. The ping

On a BaF event day the Marathon role is mentioned **once**: on the public copy of the
`marathon_baf_event_ping_minutes` (120) heads-up of the day's first BaF run. `Marathons._post_reminder` asks
`heads_up_role` for every heads-up; the rule itself is `marathon_baf_event.plan` (pure):

| The day | This heads-up | Marathon role |
|---|---|---|
| has a stored ping | any | never — `baf_event_pinged` |
| is not a BaF event | the `marathon_ping_minutes` one | as before (per run) |
| is a BaF event | the **carrier's** heads-up at or under the mark | **yes, once** |
| is a BaF event | any other (a later run, a 15-minute one, a host block's) | never — `baf_event_day` |

- **The carrier** is the day's first run, by planned start, that is still coming up, is ours, has somebody to
  name publicly (not everyone opted out), and has a mark at or under the ping mark still unsent. So the 2-hour
  heads-up of the first run carries it; **late (answer 5a)** the first run's next heads-up does; a first run
  already live or done hands it to the next BaF run's next heads-up.
- **Once is a stored fact.** `marathons.baf_event_pings` is a JSON list of `{run_id, game, mark, at, runs,
  starts_at, ends_at, reason, sent, message_id, channel_id}`. The record is written as a **claim before the
  send**; when the public copy went out with the role it is marked `sent`, otherwise the claim is given back and
  the next heads-up may carry it. A crash between the two leaves the claim, which closes the day — never two.
- **A record covers a day** when it names one of the day's runs or their planned hours overlap, so a re-timed, an
  edited-in-place, a dropped-and-returned or a re-made first run all still read as pinged.
- **The other direction:** a day with a record gets no Marathon role on any later heads-up, whatever the judgement
  says now. A day that stops being a BaF event before its ping goes back to the per-run rule.
- **Nothing left:** a BaF event day with no carrier, from the moment its ping would have gone, gets one
  `marathon.baf_event_no_ping` row (stored as a `missed` record so it is written once; a missed record never
  blocks a later ping).
- **The mark.** When `marathon_baf_event_ping_minutes` is not one of the reminder marks, the largest mark at or
  under it is used (else the smallest there is) and the day's line says so.
- **Everything else is unchanged:** every heads-up still posts at every mark, the runner's own ping-me role and
  the channel's role still ride the `marathon_ping_minutes` heads-up, highlights and shoutouts are untouched, the
  staff copy never carries the Marathon role, and every gate of the older verdict (the marathon's ping switch,
  `marathon_role_pings`, `marathon_reminder_pings`, public reminders, announcements, rehearsal, the role itself)
  still decides whether the role is mentioned at all.

**The rows.** `marathon.public_reminded` / `marathon.reminded` / `marathon.host_reminded` (and their twins) carry
`marathon_role` and `marathon_role_reason` as before, now also on a BaF event day's 2-hour heads-ups, plus
`baf_event_day` (the day's first planned start) whenever the day's rule decided.

**What staff read.** Under the ping switch's own line, one line per show-day still to come (three at most; the
last one when all are over): `marathon_baf_event_line` — *day: answer — reason.* — followed, on a day its rule
governs, by what the ping did or will do (`_ping_will` / `_ping_done` / `_ping_none`, `_ping_fallback`). When every
day shown is governed, the per-run line (*The public heads-up 15 minutes before a BaF run…*) is left out. The
drawer shows the same lines with a `baf of runs` badge.

## E. The tracker page

`/schedule.html`: each run with a BaF runner carries a **BaF run** badge (`rows[].baf_run`), a BaF event day carries
a **BaF event** badge in the head and on its day chip (`days[].baf_event` = `{answer, reason}`), and *What the bot
posts next* marks the role on the heads-up that will carry it (`marathon_baf_event.predicts`).

## Storage, keys, kinds — before → after

| | Before | After |
|---|---|---|
| Schema | 89 | **89**; `ADDED_COLUMNS`: `marathons.baf_event INTEGER`, `marathons.baf_event_ask TEXT`, `marathons.baf_event_pings TEXT` (all NULL, mirrored to `marathons_archive` at boot) |
| Registry keys | 867 | **897** — five decisions (`marathon_baf_event_names`, `_min_runs` 1–50, `_ask_percent` 1–100, `_ping_minutes` 1–1440, `_ask_role_id`) and twenty-five words (`marathon_baf_event_*`, `marathon_controls_baf_*`), all in the Marathons group |
| Log kinds | — | routine `marathon.baf_event_set` (`web.` from the site), `marathon.baf_event_asked`; IMPORTANT `marathon.baf_event_no_ping`, `marathon.baf_event_ask_failed` (by suffix) |
| Role-ping reasons | 11 | **13**: `baf_event_day`, `baf_event_pinged` |
| Thread controls | 7 buttons (6 + the tracker link) | **10**: three more in row 4 |
| Persistent items | — | `AskButton` |
| Routes | 312 | 312 |

## Decisions made beyond the brief

1. **The claim is written before the send**, and given back when the public copy did not carry the role. The
   brief said *written with the send*; before it is the only order that makes a second ping impossible.
2. **A day is matched to its record by run ids OR overlapping planned hours**, not by a date key.
3. **A show that runs past 24 hours without a three-hour gap is one show-day per calendar date** in the server's
   zone (`default_timezone`), so a non-stop two-day BaF marathon pings once each day.
4. **The carrier must have somebody to name publicly.** A first run whose people are all opted out is passed over.
5. **A day that was pinged per run before it became a BaF event still gets its one ping** at the next heads-up
   (answer 5a read literally); after that it is silent.
6. **A rehearsal** (`marathon_mode` not `on`) posts the question with no role mention, and never claims a day (the
   Marathon role is never mentioned in a rehearsal — the older Deviation 1).
7. **The question's buttons stay after an answer**, and setting the switch from any door edits the question.
8. **The question is not edited when the schedule itself settles the matter** (the day becomes 100 % or drops
   under the share); it stays as asked.
9. **`marathon.baf_event_no_ping` is written only when the role would otherwise have been mentioned** — a marathon
   whose ping switch is off logs nothing.
10. **A BaF event with only BaF hosts gets no Marathon-role ping**: no run is ours, so nothing carries it, and a
    host block is quiet on a BaF event day by the brief.
11. **The thread controls and the drawer carry a line for every show-day, BaF event or not.**
12. **The switch on the thread is three buttons, not one cycling button** — each carries its target.
13. **`/event`'s marathon card has no BaF event move**; the thread controls are the Discord door.
14. **The mock reads a marathon as one show-day** and seeds marathon 60 with a staff *yes* so the marks can be seen.

## What is NOT built

- No un-ask and no second question per marathon; no per-day staff answer (the answer is the marathon's).
- No taking back of a ping, and no editing of a posted heads-up's role.
- The live highlight, the shoutout, the runner's ping-me role and the channel's role are untouched.
- The tracker's *What the bot posts next* in the **mock** does not model the carrier.
- Nothing in `marathon_announce.py`, `marathon_public.py` or `marathon_runner_posts.py` was changed.

## What was NOT verified

- A real ping, a real Leads notification, a real button press, a real restart.
- The live migration and every live key; `marathon_baf_event_ask_role_id` is blank until staff pick the role.
- The Settings page's thirty new rows in a browser (`check.mjs` says all keys are present; nothing drew them).
- A BaF event day that crosses a schedule read which re-keys its runs, against a real source.
