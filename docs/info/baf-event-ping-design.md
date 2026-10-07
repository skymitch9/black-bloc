# BaF event ping — one Marathon-role ping per show-day on a BaF event

> **Audience:** the conductor, reviewers, and the next session touching marathon reminders, the Marathon role, the
> thread controls or the Marathon tracker. **Status:** TRACKED · ~~🔨 BUILT on branch `baf-event-ping` (off `main`
> `2c2a256b`), NOT merged, NOT deployed~~ the per-show-day build below is **on `main` (`47df98d7`) and, per the
> conductor's brief of 2026-10-06, live as v208** (not re-measured by this pass); 🔨 the whole-event change is
> **BUILT on branch `baf-event-whole`, NOT merged, NOT deployed.** `SCHEMA_VERSION` **unchanged (89)** — three nullable columns through
> `ADDED_COLUMNS`. Registry keys **867 → 906** (+30 by the build, +9 by the review fixes). Routes unchanged
> (`check.mjs`: *25 pages, 312 routes*); two payloads gained fields and `PATCH /api/marathons/{id}` takes one
> more. Log kinds **+5** (4 by the build, 1 by the review fixes).
> ⚠️ **AMENDED 2026-10-06 by the review-fix pass** — twelve findings of an independent review, each in
> [Review fixes 2026-10-06](#review-fixes-2026-10-06) at the foot; sections A–D and the decisions below are
> edited in place, superseded text struck. Two decisions were REVERSED by the conductor that day: decision 5
> (a per-run mention now counts as the day's ping) and the marathon-wide answer to the question (it is per
> show-day now).
> ⚠️ **AMENDED AGAIN 2026-10-06 — measured by the whole event** (branch `baf-event-whole`, off `main` `47df98d7`
> = v208 live; NOT merged, NOT deployed): the owner's answer to *by day or by event?* —
> *"measure by whole event even if its multiple days"*. The judgement and the question are the MARATHON's now;
> the ping is still one per show-day. Sections A, B, C and E are rewritten in place with the per-day text
> struck; the whole change, its decisions and what was not verified are in
> [Measured by the whole event 2026-10-06](#measured-by-the-whole-event-2026-10-06) at the foot. Registry keys
> **932 → 931**; log kinds unchanged; `SCHEMA_VERSION` unchanged (89), no new column.
> ⚠️ **AMENDED A THIRD TIME 2026-10-06 — review fixes of the whole-event change** (same branch, commit
> `c32f9988`; NOT merged, NOT deployed): seven findings of an independent review, no blocker, each in
> [Review fixes (whole event) 2026-10-06](#review-fixes-whole-event-2026-10-06) at the foot; sections A–D are
> edited in place, superseded text struck. Registry keys **931 → 937** (four renamed, six added); log kinds
> **+1** (`marathon.baf_event_no_baf_run`, routine); `SCHEMA_VERSION` unchanged (89), no new column; one more
> field on `PATCH /api/marathons/{id}` (`baf_event_answer`). **Verified by that pass, 2026-10-06 Phoenix:** the
> whole suite (`-n 8`: **11,855 passed, 3 skipped**), `ruff check .` clean, `node site/mock/check.mjs` against a
> mock started from the worktree on `MOCK_PORT=8806` (*25 pages, 315 routes, 108 core settings, all keys
> present*), all 13 `site/mock/*.test.mjs` exiting 0, and the mock's clear route called over HTTP. No browser,
> no Discord, no live database.
> **Verified by the whole-event pass, 2026-10-06 Phoenix, on the branch's own code:** the whole suite (`-n 8`:
> **11,822 passed, 3 skipped**; the same command on `main` `47df98d7` first: 11,799 passed, 3 skipped),
> `ruff check .` clean, `node site/mock/check.mjs` against a mock started from the worktree on `MOCK_PORT=8805`
> (*25 pages, 315 routes, 108 core settings, all keys present*), all 13 `site/mock/*.test.mjs` exiting 0. No
> browser, no Discord, no live database — see the last section.
> **Re-verified by that pass, 2026-10-06 Phoenix:** the whole suite (`-n 8`: 11,630 passed, 3 skipped, 1 failed —
> the date-fused `tests/test_pb_moves.py::test_unmatch_lets_the_automatic_match_come_back_and_block_does_not`,
> already fixed on `main` and not touched here), `ruff check .` clean, `node site/mock/check.mjs` against a mock
> started from the worktree on `MOCK_PORT=8804` (*25 pages, 312 routes, 108 core settings, all keys present*) and
> all 13 `site/mock/*.test.mjs` exiting 0. No browser was opened by that pass.
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

## A. Is this marathon a BaF event?

~~Is this show-day a BaF event? — judged per show-day.~~ **Reversed by the owner 2026-10-06** (*"measure by whole
event even if its multiple days"*, branch `baf-event-whole`): the answer is worked out ONCE for the marathon,
over every run that counts, and every show-day takes it.

`black_bloc/marathon_baf_event.py:judgement_of` → `judge` (pure) answers **yes**, **no** or **unsure** with one
reason, in this order:

| # | Rule | Answer · reason |
|---|---|---|
| 1 | The marathon's switch, `marathons.baf_event` (NULL follow / 1 yes / 0 no) — beats everything | yes or no · `staff` |
| 2 | **The answer to the marathon's question** — staff pressed it (section B). It stands whatever the schedule becomes **and whatever the show's NAME becomes**: a marathon renamed *Black in a Flash: Soul Train* after Leads pressed No still reads No, because rule 2 is read before rule 3. The switch, or clearing the answer (section C), is how staff change it | yes or no · `leads` |
| 3 | The show's name **starts with** a name in `marathon_baf_event_names` **on whole words** — capitals, spaces and punctuation set aside, so *Black in a Flash: Soul Train* and *BlackInAFlash* match and *Black in a Flashback* and *Not Black in a Flash* do not (review fix 6). ~~contains a name~~ | yes · `name` |
| 4 | Every run of the **event** has a BaF **runner**, and the event has at least `marathon_baf_event_min_runs` runs | yes · `all_runs` (fewer: no · `few_runs`) |
| 5 | The share of the **event's** runs with a BaF runner is at least `marathon_baf_event_ask_percent` and under 100 | unsure · `share` — **or yes · `acted`** once the bot already gave a day of this marathon its own one ping because rule 3 or 4 said yes (below) |
| 6 | Otherwise | no · `mixed` (`no_runs` when no run is on the schedule) |

- **Which runs count:** every run that is on a show-day — not dropped, and with a planned start. It is the same
  rule the per-day share used (`marathon_overlay.chains` leaves both kinds out), so the event's count is the sum
  of what its days show. A dropped run and a run the source has given no time are not counted.
- **A BaF runner** is a matched person whose part is *runner* and who counts (`has_runner`). A BaF host or
  commentator never makes a run a BaF run **for this judgement**, whatever `marathon_hosts_count_as_ours` says.
  (The CARRIER of the ping is a different test — any run that gets a heads-up — see decision 10.)
- **The show's name** is the marathon's name, and for a `gdq_hotfix` marathon also the show part of its
  `source_ref` (`black-in-a-flash/2026-10-06`), so a staff rename does not lose rule 3.
- **A show-day** is `marathon_overlay.chains` (three hours with nothing on starts a new one) — the early-start
  guard's day. It decides only WHEN the ping goes (section D), never whether the marathon is a BaF event.
- **Unsure is treated as no** until staff answer — ~~always~~ **unless the bot already ACTED on a yes
  (review fix 1, 2026-10-06, the conductor's decision).** When the marathon holds a show-day's OWN ping record
  (not a `per_run` one, not a `missed` one; `sent` or `unconfirmed`) whose `reason` is a rule — `name`,
  `all_runs`, or `acted` itself — an unsure reading stays **yes · `acted`** (`marathon_baf_event.acted`,
  applied inside `judge`). The bot decided and announced on it; a re-read that adds one outside run must not
  turn every remaining day into per-run pings. The question is **still asked** (`undecided` is true for both
  `share` and `acted`), and the event's line says why it reads yes meanwhile: *12 of 13 runs have a BaF runner
  now; it was a BaF event when a day's one mention went out, so it stays one until staff answer. Staff were
  asked in the thread and have not answered.* A Leads **No** then applies from that moment: days already
  pinged stay closed (a day's own record always closes it), later days go per run. A Leads **Yes** changes
  nothing but the reason.
- ⚠️ **A drop UNDER the ask percent still reads NO at once, acted or not** — that is the owner's stated rule
  (*75 % up to under 100 % asks; under it is not a BaF event*). 15 of 15 with day 1 pinged, then six outside
  runs added → 15 of 21 → **no · `mixed`**, nothing asked, the remaining days ping per run. Only the switch or
  an answer already given holds a yes there.
- **A record whose reason is `leads` or `staff` never makes the reading stick**: the bot acted on what staff
  said, and when staff take that back (the switch to follow, the answer cleared) the rules decide alone.
- **Nothing published, nobody matched:** no run on the schedule reads **no · `no_runs`**; runs with nobody of ours
  matched yet read **no · `mixed`** (*0 of 12 runs have a BaF runner*). Unsure needs at least one BaF runner
  (`marathon_baf_event_ask_percent` is 1 at the least), so the question is never asked on nothing, and the
  missed-ping row still waits on `may_be_matched`.

## B. Asking Leads — one question per marathon

~~One question per show-day; its answer is that day's alone (review fix 2).~~ **Reversed by the owner 2026-10-06**
(*"measure by whole event even if its multiple days"*, branch `baf-event-whole`). Review fix 2 answered a real
defect — one answer about day 2 silently re-deciding day 1 — but the defect was that the QUESTION was about a day
while the answer was the marathon's. Now both are the marathon's: the question names the event and gives the
event's count, so its answer is about what it covers.

On the minute tick (`cogs/content/marathon_baf_event.py:sync` → `ask_if_unsure` → `ask_about`, with the marathon's
lock held), while the marathon's switch follows the schedule, the event is unsure and a show-day is still to come:
**one message in the marathon's staff thread, once per marathon**. The words are `marathon_baf_event_ask_text`
(*Is **SS4C** a BaF event? 12 of its 15 runs have a BaF runner.*), with two persistent buttons (`AskButton`,
custom id `marathon:bafevent:{id}:{yes|no}`, registered in `Marathons.cog_load`; the button finds its question by
the message it sits on).

~~Once per marathon … one message … the answer is the marathon's.~~ ~~**Reversed by the conductor 2026-10-06 (review
fix 2):** one marathon-level answer silently re-decided every day~~ — and that reversal is itself reversed, above.

- **Where the answer lives.** `marathons.baf_event_ask` is a JSON **list**; the event's own record is flagged
  `event: true`: `{event, runs, starts_at, ends_at, baf, asked_at, tries, message_id, channel_id, text, answer,
  answered_by, answered_at}` (and `claimed` / `failed_at` / `reason` / `gave_up` / `blocked` while no message is
  up). `runs` and the hours are the whole event's and are read only to tell whether the schedule changed since a
  failed try (`same_schedule`); the answer is the marathon's whatever its runs become, so **a re-read, a re-time,
  an added run or re-made rows cannot lose it** — nothing is matched to a day any more.
- **A record from the per-day build (v208)** has no `event` flag. An **answered** one is read as the event's
  answer; when several disagree, **the latest one given** (`answered_at`; with no stamp, the last in the list).
  It is never dropped and never asked again. An **unanswered** one is kept, does not count as the event's
  question (the event's own is still asked once), and a press on its buttons is an answer like any other.
- **The answer stands until the switch says otherwise, or staff clear it (section C).** It applies to every
  show-day, and only while the switch says *follow*. A schedule change that moves the share — to 100 %, or under the ask percent — does not re-ask and
  does not undo it; the line says so (*staff answered the question in the thread (15 of 15 runs have a BaF
  runner); the answer stands until the BaF event switch changes it*). Pressing the question's button **never
  changes the marathon's switch**. The buttons stay, so the answer can be changed there.
- **Never twice:** a record holding a message id is never asked again, whatever the schedule does later and
  whether or not it was answered. **One exception since review fix 3 (2026-10-06): after staff CLEAR the
  answer**, the cleared record (flagged `cleared`, with `cleared_by` / `cleared_at`) is no longer the event's
  question, so if the rules then read unsure the tick posts **one fresh question** — a new record, itself never
  asked twice. Each clear allows one; nothing else re-asks.
- **The Leads role** (`marathon_baf_event_ask_role_id`) is mentioned in front (`AllowedMentions` for that one
  role) **only when the Marathon-role mention could actually go out** — the ping verdict mentions (review
  fix 11). With the marathon's ping switch off, no role picked, a key off or a rehearsal, the question is still
  posted (its answer drives the badge and the lines) and mentions nobody. ~~only while `marathon_mode` is on~~
- **A post that fails** writes `marathon.baf_event_ask_failed` (`try`, `gave_up`) and is tried again after 10
  minutes, then 20; **the third failure is the last** (`gave_up: true`) — three rows, not one every ten minutes
  for ever (review fix 5). It starts over when the event's runs change or staff move the switch. The event's line
  then says *The question could not be posted in the thread, so answer with the BaF event switch.*
- **A claim nothing followed** (the bot stopped between the claim and the post) is treated as a failed try after
  the same gap and asked again (review fix 4). ~~reads as asked~~ A duplicate question is cheap; one never asked
  costs the decision.
- **Nowhere to ask** (no thread in the current home, the thread gone, the guard): the record is marked
  `blocked` and the line says *There is no thread to ask in, so answer with the BaF event switch.* (review fix 8).
- **A press** is staff-gated (`still_staff`, the standing worded refusal), defers, and goes through
  `set_answer`. ~~The question is edited~~ **Every question message the marathon still holds** (the event's,
  an older per-day one, one whose answer was cleared) is edited to its own words plus the ONE thing that
  stands — `marathon_baf_event_answered` (*who* answered *what*, for the latest answer) or
  `marathon_baf_event_cleared` (*who cleared the answer*) — by `note_questions` (review fix 7). Two messages can
  no longer each say a different *X answered*. The edits mention nobody; a message that is gone is skipped and
  the others are still edited.

## C. The staff switch and the question's answer — two writers, one scope

~~The staff switch and the day's answer — two writers, two scopes.~~ Both are the marathon's since 2026-10-06
(the owner's whole-event decision); the switch still beats the answer.

`set_baf_event(bot, guild, actor, marathon, given, *, via, by)` takes follow / yes / no (or None / True / False),
writes `marathons.baf_event`, logs **`marathon.baf_event_set`** (`web.` from the site) with `from`, `to`, `via`
and `by`, drops any question record that never got posted (so a given-up question is tried again) and re-renders
the thread controls. **Follow means: the question's answer if there is one, else the rules** — and since
review fix 2 every door SAYS so: `judgement_of(found, own=False)` is the judgement with only the switch set
aside (~~the rules-only answer~~), and it feeds `worked_out`, the drawer's follow choice and the thread's
follow button.

`clear_answer(bot, guild, actor, marathon, *, via)` (review fix 3) takes the answer off every record that holds
one (`without_answers`), flags those records `cleared`, logs **`marathon.baf_event_set`** with `from` (the
answer that stood), `to: follow`, `by: question`, **`cleared: true`**, `via`, edits every question message to
*who cleared the answer*, re-renders the controls and answers *The answer was cleared, so **marathon** is
(what it reads now) now.* With no answer stored it changes nothing and says so. The marathon's switch is left
as it stands. `set_question_answer` is the site's wrapper: `clear` is the only word it takes.
~~edits the question if one is up~~ (the switch is not an answer to the question).

`set_answer(bot, guild, actor, marathon, message_id, yes, *, via)` ~~`set_day_answer` — one show-day~~ writes
`answer` on the question's record, logs the same kind with `by: question` (~~and `day`~~ — there is no day any
more), edits the question, re-renders the controls. A press on a message the bot holds no question for is refused
in words (`no_baf_question`).

| Door | What it is |
|---|---|
| Thread controls | three buttons in a row of their own (`marathon:controls:{id}:baf:{follow|yes|no}`), the one that stands lit and not pressable; **a fourth, *Clear the answer* (`…:baf:clear`), only while an answer to the question is stored**; the follow button reads *BaF event: follow the schedule (answer)* or, while an answer stands, *BaF event: follow the answer (answer)* — the answer in brackets is what following gives right now; under the ping switch's line, one line for the event and one per show-day for its ping |
| Marathon drawer ▸ Settings | *BaF event*: *Follow the schedule (what following gives)* — or *Follow the answer (…)* while a Leads answer stands — / Yes / No, the same lines under it, and a *Clear the answer* button while an answer stands (`ask` is `answered`) |
| `PATCH /api/marathons/{id}` | `baf_event`: `"follow"` / `"yes"` / `"no"` (or null / true / false); anything else is refused in words (`bad_baf_event`). **`baf_event_answer`: `"clear"`**; anything else is refused in words (`bad_baf_event_answer`) |
| The question's buttons | yes / no, for the whole event |

**The event's line says where its answer came from:** *the BaF event switch says so* (`staff`), *staff answered
the question in the thread … the answer stands until the BaF event switch changes it* (`leads`), or the rule that
decided (`name`, `all_runs`, `share`, `few_runs`, `mixed`, `no_runs`, and `acted` — section A).

`GET /api/marathons/{id}` answers `baf_event` — **the event once, then the days' pings**: `own`, `choice`,
`answer`, `reason` (and their words), `runs`, `baf` (the event's count), `worked_out` (~~the answer ignoring
staff~~ **what choosing follow would give: the judgement with only the switch set aside, so `reason` is `leads`
when it is the answer to the question** — review fix 2), `asked`, `ask` (null / `pending` / `failed` / `nowhere` / `answered`), `line` (the event's one line),
`ping_minutes`, `ping_fell_back`, `days[]` (each: `starts_at`, `runs`, `baf` — that day's own count — `over`,
`governed`, `ping`, `no_ping` — null or one of the three causes — `pinged` (with `sent` and `per_run`),
`carrier`, `line`), `lines[]` (the event's line first, then the days'), `all_governed`. ~~each day: `answer`,
`reason`, `ask`~~ — a day has no answer of its own.

**A day's `ping` is one of eight words**, and every one but two has a line (`marathon_baf_event_day_line`,
*day: what the ping did or will do*):

| `ping` | When | The day's line |
|---|---|---|
| `will` | a BaF event, a carrier is left | `_ping_will` (+ `_ping_fallback`) |
| `done` | the day's ping is stored and confirmed | `_ping_done` |
| `unconfirmed` | a claim nothing confirmed | `_ping_unconfirmed` |
| `no_baf_run` | a BaF event's day with nobody of ours on any run | `_ping_no_run` — *No BaF run is on that day…* |
| `nobody_to_name` | everybody on its BaF runs opted out | `_ping_nobody` |
| `marks_spent` | every heads-up has gone | `_ping_none` |
| `per_run` | the marathon is not a BaF event (or not decided): the per-run rule decides | none — the ping switch's own line (`role_ping.line`) is that line |
| `off` | a BaF event, but the Marathon role is not mentioned at all | none — the ping switch's line or the switch itself says why |

## D. The ping

> **Since 2026-10-06 (whole event):** this section is unchanged but for one reading — *a BaF event day* is a
> show-day of a marathon that is a BaF event, and where a row says *the day is / is not a BaF event* it is the
> MARATHON's answer the day takes. A day of a BaF event with no BaF run on it has nothing to carry the ping
> (`no_baf_run`); a day of a marathon that is not a BaF event keeps the per-run rule even when every run that
> day is ours.

On a BaF event day the Marathon role is mentioned **once**: on the public copy of the
`marathon_baf_event_ping_minutes` (120) heads-up of the day's first BaF run. `Marathons._post_reminder` asks
`heads_up_role` for every heads-up; the rule itself is `marathon_baf_event.plan` (pure):

| The day | This heads-up | Marathon role |
|---|---|---|
| has its own stored ping | any | never — `baf_event_pinged` |
| is a BaF event and had a **per-run mention** stored earlier | any | never — `baf_event_pinged` (review fix 1) |
| is not a BaF event | the `marathon_ping_minutes` one | as before (per run) — and the mention is stored, flagged `per_run` |
| is a BaF event | the **carrier's** heads-up at or under the mark | **yes, once** |
| is a BaF event | any other (a later run, a 15-minute one, a host block's) | never — `baf_event_day` |

- **The carrier** is the day's first run, by planned start, that is still coming up, is ours, has somebody to
  name publicly (not everyone opted out), and has a mark at or under the ping mark still unsent. So the 2-hour
  heads-up of the first run carries it; **late (answer 5a)** the first run's next heads-up does; a first run
  already live or done hands it to the next BaF run's next heads-up.
- **Once is a stored fact.** `marathons.baf_event_pings` is a JSON list of `{run_id, game, mark, at, runs,
  starts_at, ends_at, reason, sent, message_id, channel_id}` (+ `per_run`, `host`, `unconfirmed`, `missed`,
  `because`). The record is written as a **claim before the send**; when the public copy went out with the role
  it is marked `sent`, otherwise the claim is given back and the next heads-up may carry it.
- **A per-run mention counts (review fix 1).** Every Marathon-role mention the per-run rule sends on a show-day
  — a run's `marathon_ping_minutes` heads-up, and a host block's — is stored the same way, flagged `per_run`. A
  `per_run` record **closes the day only while the day is a BaF event**: a mixed day still mentions the role on
  every BaF run exactly as on `main`, and nothing it posts changes; the moment the day becomes a BaF event (Leads
  answer late, the switch, a re-read) the earlier mention IS that day's one ping and the line reads *was
  mentioned once, on the heads-up 15 minutes before **Game 1***. A host block's mention is written by the tick
  from the block's own stored post (`note_host_pings`, flagged `host`), so `marathon_host_highlights.py` is not
  touched.
- **A claim nothing marked sent (review fix 3).** The bot stopped between the claim and the send, or between the
  send and the bookkeeping. The day stays closed — never two — and the next tick settles it from what the run
  itself remembers posting at that mark (`marathon_runs.reminder_posts`, `reconcile` → `proof_of`): a public copy
  whose head carries the role → marked `sent`; an entry with no public copy → the claim is given back and a later
  heads-up carries the ping; no entry at all (or a public copy without the role) → left closed, flagged
  `unconfirmed`, and **one** IMPORTANT `marathon.baf_event_ping_unconfirmed` row. Until it is confirmed the line
  says *may have been mentioned … the bot stopped before it could confirm it*, never *was mentioned*.
- **A record covers a day** when it names one of the day's runs; **or, only when none of its runs is on any day
  any more** (the source re-made its rows), the ONE day whose planned hours it overlaps most (review fix 9).
  ~~or their planned hours overlap~~ — with overlapping estimates across a calendar cut (run 1 18:00–00:30 in day
  A, run 2 from 00:00 in day B) plain overlap read day B as already pinged. A re-timed, an edited-in-place, a
  dropped-and-returned or a re-made first run all still read as pinged.
- **The other direction:** a day with **its own** record gets no Marathon role on any later heads-up, whatever
  the judgement says now. A day that stops being a BaF event before its ping goes back to the per-run rule — and
  so does a day closed only by a `per_run` record, since on a day that is not a BaF event the per-run rule is
  the rule.
- **Nothing left:** a BaF event day with no carrier, from the moment its ping would have gone, gets one
  ~~`marathon.baf_event_no_ping`~~ row (stored as a `missed` record so it is written once; a missed record never
  blocks a later ping). **Two kinds since review fix 5 of the whole-event pass (2026-10-06):** a day with no BaF
  run (`no_baf_run`) writes the ROUTINE **`marathon.baf_event_no_baf_run`** — on a whole-event marathon an
  outside day is ordinary and nothing staff can fix — while `nobody_to_name` and `marks_spent` keep the
  IMPORTANT `marathon.baf_event_no_ping` (staff can fix those). **The row is written the first time the tick
  sees the day cannot be pinged, also when that is after the day is over** (~~only between the day's last run
  starting and all of its runs being done~~), and never twice. `because` is one of three words, each with its
  own line (review fix 7):

  | `because` | When | The line (`marathon_baf_event_…`) |
  |---|---|---|
  | `no_baf_run` | no run of the day has anybody of ours | `ping_no_run` — *No BaF run is left that day…* |
  | `nobody_to_name` | BaF runs still have heads-ups left, but everybody on them opted out of public posts | `ping_nobody` — *Nobody on that day's BaF runs can be named publicly…* |
  | `marks_spent` | every heads-up of the day's BaF runs has been posted, or their runs have started | `ping_none` — *Every heads-up of that day's BaF runs has gone…* |

  The row is **not** written for `no_baf_run` while a run nobody of ours is on has not started yet — a match can
  still bring a heads-up that carries the ping (a name-rule day whose runners are not matched yet).
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

**What staff read.** Under the ping switch's own line: **one line for the event** — `marathon_baf_event_line`,
*\*\*marathon\*\* is answer — reason.*, plus what became of the question while it is not decided — then **one
line per show-day still to come whose ping the day's rule governs** (three at most; the last one when all are
over): `marathon_baf_event_day_line`, *day: what the ping did or will do*. ~~one line per show-day: *day: answer
— reason.* followed by the ping~~ (struck 2026-10-06: a day has no answer of its own). When every day shown is
governed, the per-run line (*The public heads-up 15 minutes before a BaF run…*) is left out. The drawer shows
the same lines, the event's with one `baf of runs` badge (the event's count).

## E. The tracker page

`/schedule.html`: each run with a BaF runner carries a **BaF run** badge (`rows[].baf_run`), a BaF event carries
one **BaF event** badge in the head (the sheet's `baf_event` = `{answer, reason}`), and *What the bot posts
next* marks the role on the heads-up that will carry it (`marathon_baf_event.predicts`). ~~a BaF event day
carries the badge in the head and on its day chip (`days[].baf_event`)~~ — struck 2026-10-06: the answer is the
marathon's, so it is drawn once and no day chip repeats it.

## Storage, keys, kinds — before → after

| | Before | After |
|---|---|---|
| Schema | 89 | **89**; `ADDED_COLUMNS`: `marathons.baf_event INTEGER`, `marathons.baf_event_ask TEXT`, `marathons.baf_event_pings TEXT` (all NULL, mirrored to `marathons_archive` at boot) |
| Registry keys | 867 | **906** — five decisions (`marathon_baf_event_names`, `_min_runs` 1–50, `_ask_percent` 1–100, `_ping_minutes` 1–1440, `_ask_role_id`) and thirty-four words (`marathon_baf_event_*`, `marathon_controls_baf_*`), all in the Marathons group. The build made 897; the review fixes added nine words: `_reason_leads`, `_ping_unconfirmed`, `_ping_no_run`, `_ping_nobody`, `_ask_pending`, `_ask_failed`, `_ask_nowhere`, `_day_set_said`, `_day_same_said`, and re-worded the defaults of `_ask_text`, `_reason_staff`, `_reason_share`, `_ping_none` |
| Registry keys (review fixes of the whole event, 2026-10-06) | 931 | **937** — RENAMED so a value stored before the re-wording is ignored at load: `marathon_baf_event_ask_text` → `marathon_baf_event_question`, `marathon_baf_event_line` → `marathon_baf_event_answer_line`, `marathon_baf_event_reason_leads` → `marathon_baf_event_reason_answered`, `marathon_baf_event_ping_no_run` → `marathon_baf_event_ping_no_baf_run`. ADDED: `marathon_baf_event_reason_acted`, `marathon_baf_event_cleared`, `marathon_baf_event_cleared_said`, `marathon_baf_event_no_answer_said`, `marathon_controls_baf_follow_answer`, `marathon_controls_baf_clear`. `marathon_controls_baf_follow` now takes `{answer}` |
| Log kinds (the same pass) | — | **+1**: routine `marathon.baf_event_no_baf_run`; `marathon.baf_event_no_ping` stays IMPORTANT for `nobody_to_name` and `marks_spent`; `marathon.baf_event_set` carries `cleared: true` when the answer was cleared |
| Thread controls (the same pass) | 10 | **10 or 11**: the BaF row holds three buttons, four while an answer to the question is stored |
| Registry keys (whole event, 2026-10-06) | 932 | **931** — `marathon_baf_event_day_line` added; `marathon_baf_event_day_set_said` and `marathon_baf_event_day_same_said` retired (a stored value is ignored at load, like any key the registry no longer has); defaults re-worded: `_ask_text`, `_line`, `_reason_leads`, `_ping_no_run` |
| Log kinds | — | routine `marathon.baf_event_set` (`web.` from the site; `day` when it is one day's answer), `marathon.baf_event_asked`; IMPORTANT `marathon.baf_event_no_ping`, `marathon.baf_event_ask_failed` (by suffix; `try`, `gave_up`), **`marathon.baf_event_ping_unconfirmed`** (review fix 3) |
| Role-ping reasons | 11 | **13**: `baf_event_day`, `baf_event_pinged` |
| Thread controls | 7 buttons (6 + the tracker link) | **10**: three more in row 4 |
| Persistent items | — | `AskButton` |
| Routes | 312 | 312 |

## Decisions made beyond the brief

1. **The claim is written before the send**, and given back when the public copy did not carry the role. The
   brief said *written with the send*; before it is the only order that makes a second ping impossible.
2. **A day is matched to its record by run ids, and by planned hours only when the record's runs are on no day
   any more**, not by a date key. ~~by run ids OR overlapping planned hours~~ — narrowed 2026-10-06 (review fix
   9): plain overlap closed a neighbouring calendar day when two estimates overlapped across the cut.
3. **A show that runs past 24 hours without a three-hour gap is one show-day per calendar date** in the server's
   zone (`default_timezone`), so a non-stop two-day BaF marathon pings once each day.
4. **The carrier must have somebody to name publicly.** A first run whose people are all opted out is passed over.
5. ~~**A day that was pinged per run before it became a BaF event still gets its one ping** at the next heads-up
   (answer 5a read literally); after that it is silent.~~ **REVERSED by the conductor, 2026-10-06 (the review-fix
   commit after `4c522e31`): a per-run Marathon-role mention already sent on a show-day counts as that day's
   ping once the day is a BaF event.** Why it flipped: the owner's rule is ONE role ping per event day. With the
   old reading a day at 75 % (unsure, so treated as no) pinged the role on Game 1's 15-minute heads-up, Leads
   pressed Yes fifteen minutes later, and Game 2's 15-minute heads-up became the carrier — two role pings on one
   BaF event day. Answer 5a (*learn late → ping once at the next heads-up*) is about a day that has not pinged
   yet; it never asked for a second. Do not flip this back without the owner.
6. **A rehearsal** (`marathon_mode` not `on`) posts the question with no role mention, and never claims a day (the
   Marathon role is never mentioned in a rehearsal — the older Deviation 1). Widened 2026-10-06 (review fix 11):
   the question mentions nobody whenever the Marathon role could not be mentioned, a rehearsal being one case.
7. **The question's buttons stay after an answer**~~, and setting the switch from any door edits the question~~.
   ~~Since 2026-10-06 (review fix 2) a question is about one show-day and only its own buttons edit it.~~ Since
   the whole-event change the same day a question is about the marathon; ~~still only its own buttons edit
   it~~ **an answer or a clear, from any question's buttons or either door, edits EVERY question message the
   marathon holds to the same standing line** (review fix 7 of the whole-event pass).
8. **The question is not edited when the schedule itself settles the matter** (the ~~day~~ event becomes 100 % or
   drops under the share); it stays as asked, and an answer already given to it stands (section B).
9. **`marathon.baf_event_no_ping` is written only when the role would otherwise have been mentioned** — a marathon
   whose ping switch is off logs nothing.
10. ~~**A BaF event with only BaF hosts gets no Marathon-role ping**: no run is ours, so nothing carries it~~ —
    **true only with `marathon_hosts_count_as_ours` OFF** (corrected 2026-10-06, review fix 10; the behaviour is
    unchanged). The carrier is any upcoming run that gets a heads-up (`mt.is_ours`), so with that key ON a run
    with only a BaF host counts as ours and **does** carry the day's ping; with it off (or the host marked
    `counts: false`) nothing carries it and the line says *No BaF run is left that day*. A host BLOCK's own
    heads-up is quiet on a BaF event day either way. Pinned by
    `test_a_host_only_first_run_carries_the_ping_while_hosts_count_as_ours`.
11. ~~**The thread controls and the drawer carry a line for every show-day, BaF event or not.**~~ **Struck
    2026-10-06 (whole event, `baf-event-whole`):** they carry ONE line for the event, BaF event or not, and a
    line per show-day only where the day's own ping rule governs. A day's line used to repeat the answer; the
    answer is the marathon's now, and on a marathon that is not a BaF event the ping switch's line already says
    what every day does.
12. **The switch on the thread is three buttons, not one cycling button** — each carries its target.
13. **`/event`'s marathon card has no BaF event move**; the thread controls are the Discord door.
14. **The mock reads a marathon as one show-day** and seeds marathon 60 with a staff *yes* so the marks can be seen.

## What is NOT built

- ~~No un-ask: the answer is changed with the question's buttons or overridden by the switch, never cleared.~~
  **Built 2026-10-06 (review fix 3 of the whole-event pass):** *Clear the answer* on the thread controls and in
  the drawer; section C.
  ~~no second question per marathon; no per-day staff answer (the answer is the marathon's)~~ — ~~both built
  2026-10-06 (review fix 2). There is no per-day control on the site or the thread controls: the per-day door is
  the question.~~ Both un-built again the same day by the owner's whole-event decision: one question per
  marathon, no per-day answer anywhere.
- No way to say *this one day of a BaF event is not ours*: a day with no BaF run simply has nothing to carry
  the ping; a day with a BaF run pings.
- No taking back of a ping, and no editing of a posted heads-up's role.
- The live highlight, the shoutout, the runner's ping-me role and the channel's role are untouched.
- The tracker's *What the bot posts next* in the **mock** does not model the carrier.
- Nothing in `marathon_announce.py`, `marathon_public.py` or `marathon_runner_posts.py` was changed.

## What was NOT verified

- A real ping, a real Leads notification, a real button press, a real restart.
- The live migration and every live key; `marathon_baf_event_ask_role_id` is blank until staff pick the role.
- The Settings page's thirty new rows in a browser (`check.mjs` says all keys are present; nothing drew them).
- A BaF event day that crosses a schedule read which re-keys its runs, against a real source.
- **Added by the review-fix pass, 2026-10-06:** nothing here ran against Discord either. NOT exercised: a real
  crash between the claim and the send (the tests write the stranded claim by hand, or raise from the fake
  thread); a real source re-keying a day that holds an answer (the tests re-time it and re-make ids in the pure
  layer); the Settings page drawing the nine new rows (`check.mjs` only says the keys are present); the mock's
  drawer in a browser after the re-wording.

## Review fixes 2026-10-06

An independent review of `4c522e31` found twelve things. Each was reproduced by a test that failed first (finding
10 is a doc correction; its test pins the behaviour and passed before). Tests are in
`tests/cogs/content/test_marathon_baf_event.py` (**cog**), `tests/test_marathon_baf_event.py` (**pure**) and
`tests/test_marathon_thread_controls.py`.

| # | Finding | What changed | Pinned by |
|---|---|---|---|
| 1 | **BLOCKER.** A day could carry two role pings when Leads answered late: the per-run branch stored nothing, so a day that became a BaF event after a per-run mention still got a carrier | `heads_up_role` stores every per-run mention as a claim flagged `per_run` and `settle` settles it the same way; `pinged(..., yes=)` lets a `per_run` record close the day only while the judgement is yes (`plan`, `quiet_reason`, `predicts`, `day_states` all go through `closed`). A host block's mention is stored by the tick (`note_host_pings`). **Decision 5 reversed** | cog `test_leads_answering_yes_after_a_per_run_ping_brings_no_second_ping`, `test_yes_then_no_then_yes_around_a_per_run_ping_never_adds_a_ping`, `test_a_host_blocks_role_mention_counts_once_the_day_is_a_baf_event`, `test_a_day_that_is_not_a_baf_event_posts_what_main_posts` (both ways against one golden); pure `test_a_per_run_mention_closes_the_day_only_once_it_is_a_baf_event`, `test_a_days_own_ping_is_read_before_a_per_run_one` |
| 2 | One marathon-level answer re-decided every day | The question is per show-day, its answer stored on that day's record in `baf_event_ask` (a list now) and read by `judge(said=)` after the switch and before the rules; `set_day_answer` is its writer; each unsure day is asked once; the switch no longer edits a question | cog `test_a_no_for_one_day_leaves_every_other_day_alone`, `test_each_unsure_day_gets_its_own_question_once_and_its_own_answer`, `test_the_switch_beats_a_days_answer_and_follow_gives_it_back`, `test_a_days_answer_survives_the_day_being_re_timed`; pure `test_a_days_own_answer_decides_that_day_only_and_the_switch_beats_it`, `test_a_days_own_answer_survives_a_re_read_that_re_keys_its_runs`, `test_the_question_records_round_trip_and_a_broken_column_reads_as_none` |
| 3 | A claim stranded before the send made the line say *was mentioned* and logged nothing | Third worded state (`marathon_baf_event_ping_unconfirmed`); `reconcile` on the next tick: role in the stored public copy's head → sent; entry with no public copy → given back; otherwise closed, flagged, one `marathon.baf_event_ping_unconfirmed` row | cog `test_a_claim_nothing_confirms_says_so_once_and_keeps_the_day_closed`, `test_a_claim_whose_heads_up_never_went_public_is_given_back`, `test_a_claim_whose_public_copy_carries_the_role_is_marked_sent`; pure `test_an_unsent_claim_is_confirmed_from_what_its_run_remembers_posting` |
| 4 | An ask-claim with no message never aged out | `may_ask`: a claim nothing followed is a failed try once the retry gap has passed | cog `test_a_question_claimed_and_never_posted_is_asked_after_the_retry_gap` |
| 5 | A question that can never post retried every 10 minutes for ever, one IMPORTANT row each time | Back-off 10 → 20 minutes, three tries, the third row carries `gave_up`; the line says so and points at the switch; a schedule change or a switch move starts it over | cog `test_a_question_that_never_posts_backs_off_and_stops_after_three_tries`, `test_setting_the_switch_back_to_follow_lets_a_given_up_question_be_asked` |
| 6 | The name match was a substring of folded text | `opens_with`: whole words, from the start of the show's name. ⚠️ A builder's call inside the conductor's *whole-word* instruction: plain whole-word containment would still read *Not Black in a Flash* as yes, which the finding names as wrong, so the match is anchored at the start. A show called *X presents Black in a Flash* is therefore NOT matched by name (its runs, the question or the switch decide) | pure `test_a_show_name_matches_on_whole_words_from_its_start` (the four names), `test_the_shows_name_makes_it_a_baf_event_whatever_its_runs` |
| 7 | *No heads-up is left* was said for three causes, and the no-ping row fired for a day whose runners were not matched yet | `no_carrier` → `no_baf_run` / `nobody_to_name` / `marks_spent`, one line each; `note_missed` waits on `may_be_matched` | pure `test_why_nothing_carries_the_ping_is_one_of_three_causes`; cog `test_a_day_whose_runners_are_not_matched_yet_writes_no_missed_row`, `test_nothing_left_that_day_pings_nobody_and_one_row_says_so` |
| 8 | An unsure day whose question could not be posted read *staff have not answered* | `ask_about` stores `blocked`; the line says there is no thread to ask in; the share reason no longer claims staff were asked (`ask_pending` says it only while a question is up) | cog `test_an_unsure_day_with_no_thread_to_ask_in_says_so` |
| 9 | Coverage leaked across the calendar cut when estimates overlapped | `covers`: run ids first; hours only when the record's runs are on no day, and then only the one best-overlapping day | pure `test_a_ping_never_closes_the_next_calendar_day_when_the_estimates_overlap`, `test_a_re_keyed_day_is_still_its_own_and_never_its_neighbours` |
| 10 | Decision 10 was true only with `marathon_hosts_count_as_ours` off | Doc corrected in place; behaviour kept | pure `test_a_host_only_first_run_carries_the_ping_while_hosts_count_as_ours` |
| 11 | Leads were pinged even when the Marathon role could never be mentioned | The Leads role is mentioned only when the ping verdict mentions; the question is still posted | cog `test_leads_are_not_mentioned_when_the_marathon_role_could_not_be` |
| 12 | `FOLLOW` / `YES` / `NO` lived in two modules | `marathon_thread_controls` imports them (and `CHOICES`) from `marathon_baf_event` | `tests/test_marathon_thread_controls.py::test_the_three_baf_event_answers_have_one_home` |

**Decisions made in this pass** (beyond what the review asked):

1. **A host block's role mention counts too** (finding 1). It is the per-run rule's mention on that day; without
   it a host block at 15 minutes followed by a late *yes* gave two pings (the test's `as_before` half shows it).
2. **A per-run claim nothing confirms** closes the day only while the day is a BaF event, and its
   `ping_unconfirmed` row is written only then — on a mixed day it changes nothing and says nothing.
3. **A public copy WITHOUT the role under an unsent claim is not proof either way**, so it is treated like no
   entry: closed, one row.
4. **The no-thread state is stored** (`blocked` on the day's record) so the drawer and the thread line read it
   without reaching Discord.
5. **A day's answer is logged under `marathon.baf_event_set`** with `day`, not under a new kind.
6. **The marathon's switch also clears question records that never got posted**, which is how staff re-arm a
   given-up question.
7. **Default words changed:** `_reason_staff` *the BaF event switch says so*, `_reason_share` no longer says
   staff have not answered, `_ping_none` names its cause, `_ask_text` names the day first.

**The proof that a day that is not a BaF event is unchanged** is now a test:
`test_a_day_that_is_not_a_baf_event_posts_what_main_posts` runs one mixed day twice — once with `heads_up_role`,
`settle` and `sync` replaced by what `main` does, once as built — and holds both to the same text, mentions and
row fields. What it does not cover: the staff thread's controls message, which carries the BaF switch and lines
on every marathon by design.

## Measured by the whole event 2026-10-06

Branch `baf-event-whole`, off `main` `47df98d7` (v208, live). NOT merged, NOT deployed.

**The owner, asked *do we measure by day or by event?*, verbatim:** *"measure by whole event even if its multiple
days"*.

### The rule

1. **The judgement is made once for the marathon**, over every run on a show-day (not dropped, with a planned
   start — the rule the per-day share used): the staff switch → the answer to the question → the show's name →
   every run has a BaF runner and there are at least `marathon_baf_event_min_runs` → the share is at least
   `marathon_baf_event_ask_percent` and under 100 (**unsure**) → otherwise no. Every show-day takes it.
2. **Leads are asked once per marathon, about the event**, with the event's count. The answer covers every day.
3. **The ping is unchanged**: once per show-day (*"once per event day"*), on that day's first BaF run at the 2-hour
   heads-up, with everything section D says.

### What changed, what did not

| | v208 (per show-day) | Now (whole event) |
|---|---|---|
| The judgement | each show-day by its own runs | once, over all the marathon's runs; each day takes it |
| 3 days, 5/5 · 5/5 · 2/5 | days 1–2 BaF events, day 3 not, nothing asked | **12 of 15 → unsure → one question**; after *Yes* each day pings once, day 3 on its first BaF run |
| 3 days, 5/5 · 0/13 · 1/11 | day 1 a BaF event (one ping at 2 hours) | **6 of 29 → not a BaF event**; day 1 pings per run at 15 minutes exactly as a mixed day does |
| 2 days of one all-ours run each | neither is an event (`few_runs`) | 2 of 2 → a BaF event (`min_runs` is the event's) |
| The question | one per unsure show-day, naming the day | one per marathon, naming the event |
| Its answer | that day's | the marathon's; stands until the switch changes it |
| `baf_event_ask` | one record per day, matched to its day by `covers` | the event's record flagged `event`; nothing matched to a day |
| Staff's lines | *day: answer — reason. ping* per day | *marathon is answer — reason.* once, then *day: ping* per governed day |
| Tracker | badge in the head and on each BaF event day's chip | one badge in the head (`baf_event` on the sheet) |
| **The ping** | once per BaF event day | **the same** — `plan`, `carrier`, `covers`, `pinged`, `reconcile`, `note_host_pings`, `note_missed`, `settle`, `claim_day` are untouched but for reading the marathon's answer |
| Ask-once, the claim that ages out, back-off, three tries, the worded failures, the Leads mention only when the Marathon role could be mentioned, persistent staff-gated buttons | built by the review-fix pass | **kept**, per marathon |
| A marathon that is not a BaF event | posts what `main` posts | **the same** — `test_a_day_that_is_not_a_baf_event_posts_what_main_posts` is unchanged and green, and `test_an_all_ours_day_of_an_event_that_is_not_baf_posts_what_a_mixed_day_posts` holds the new common case to the same rule both ways |
| `marathon_announce.py`, `marathon_public.py`, `marathon_runner_posts.py`, the schema | — | not touched; `SCHEMA_VERSION` 89, no new column |

### Keys, kinds, payloads

- **Registry keys 932 → 931.** Added `marathon_baf_event_day_line` (*{day}: {ping}*). Retired
  `marathon_baf_event_day_set_said` and `marathon_baf_event_day_same_said` — answering the question says what the
  switch says (`_set_said` / `_same_said`); a value stored under a retired key is ignored at load
  (`SettingsStore.load` → *settings ignored*). Re-worded defaults: `_ask_text` (no `{day}`), `_line` (`{marathon}`,
  no `{day}`), `_reason_leads` (takes `{baf}` `{runs}` and says the answer stands), `_ping_no_run` (*is on that
  day*). ~~A value staff stored for `_ask_text` or `_line` that still uses `{day}` will not fill and falls back to
  the shipped words (checklist 17) — pinned.~~ **Superseded the same day (review fix 6 of the whole-event
  pass):** the fallback only caught a stored value that FAILED to fill — *staff answered for this day* has no
  field and rendered as it stood — so all four keys were RENAMED and a value stored under an old name is
  ignored at load.
- **Log kinds: none added, none removed.** `marathon.baf_event_asked`, `marathon.baf_event_ask_failed` and the
  question's `marathon.baf_event_set` row no longer carry `day`; `runs` and `baf` are the event's. The
  reminded rows' `baf_event_day` is unchanged.
- **`GET /api/marathons/{id}`** `baf_event`: the event once (`runs`, `baf`, `ask`, `line` are new at the top),
  `days[]` lose `answer` / `reason` / `ask` and gain `ping`; `lines[]` starts with the event's line.
  **`GET /api/marathons/{id}/schedule`**: `baf_event` moves from each `days[]` row to the sheet. `contract.json`
  holds both shapes for the mock and the routers.

### Decisions made in this pass

1. **Which runs count: the ones on a show-day** (not dropped, with a planned start). Counting untimed runs too
   would make the event's count disagree with the sum of its days, and a run with no time can carry no ping.
2. **The Leads answer sits after the switch and BEFORE the name and the runs**, and stands when the schedule
   later reaches 100 % or drops under the ask percent. Looked for a reason that is wrong and kept it: undoing an
   explicit staff answer because a re-read moved a count would be the bot overruling staff silently; the line
   shows the count as it is now beside the answer and names the switch as the way to change it.
3. **A per-day record from v208 is told from the event's by the `event` flag.** Answered: it is the event's
   answer, the latest one given winning. Unanswered: kept, but not the event's question — the per-day question's
   words count one day, so the event's own question is still asked once. A press on the old one's buttons is
   taken as an answer for the event (there is no other meaning left for it), and the reply says so in the event's
   words.
4. **One line for the event, day lines only where the day's ping is governed.** On a marathon that is not a BaF
   event (or not decided) there is no day line: the ping switch's line already says what every day does, and a
   line per day repeating it would be a fact with no value. `days[].ping` still carries every state.
5. ~~**A day of a BaF event with no BaF run still gets the one `marathon.baf_event_no_ping` row** (`no_baf_run`),
   once every run of that day has started — the behaviour is section D's, unchanged. ⚠️ That row is IMPORTANT and
   this case is common now (an 80 % event with one outside day); whether it should be quieter is the conductor's
   call, not made here.~~ **Decided by the conductor 2026-10-06 (review fix 5 of the whole-event pass, commit
   `c32f9988`):** that day writes the ROUTINE `marathon.baf_event_no_baf_run` instead — a 12-of-15 event with
   two outside days wrote two IMPORTANT rows about nothing staff could fix.
6. **The tracker's day chips no longer say *BaF event*.** The answer is the marathon's, so the head carries it
   once.
7. **A press is told *already that answer* against the answer that stands**, not against the pressed record, so
   two questions (an old per-day one and the event's) cannot each claim a different current answer.
8. **The mock's `all_governed` is false for a marathon with no runs**, as the bot's is.

### Tests seen failing before the change

**Pure** (`tests/test_marathon_baf_event.py`, run against the old module — 7 failed):

- `test_twelve_of_fifteen_over_three_days_is_one_unsure_event_not_two_sure_days`
- `test_fifteen_of_fifteen_over_three_days_is_a_baf_event_with_a_carrier_each_day` (on the count, 5 of 5 a day
  against 15 of 15, and on `Reading.rows` not existing; its carriers were already right)
- `test_an_all_ours_day_inside_a_mostly_outside_event_is_left_to_the_per_run_rule`
- `test_min_runs_is_counted_over_the_event_not_over_a_day`
- `test_a_dropped_run_and_a_run_with_no_planned_start_are_not_counted_in_the_event`
- `test_a_per_day_answer_from_before_is_read_as_the_events_answer`
- `test_when_per_day_answers_disagree_the_latest_one_given_is_the_events`

**Cog** (`tests/cogs/content/test_marathon_baf_event.py`, run in a throwaway worktree of `47df98d7` — 18 failed,
41 passed). The ones that pin new behaviour:

- `test_twelve_of_fifteen_over_three_days_asks_once_about_the_event_then_pings_each_day` (no question was asked)
- `test_an_all_ours_day_of_an_event_that_is_not_baf_posts_what_a_mixed_day_posts[branch]` (Game 1's 2-hour
  heads-up carried the role; the `[as_main]` half passed there, so the golden is `main`'s)
- `test_a_day_of_a_baf_event_with_no_baf_run_gets_no_ping_and_its_line_says_so`
- `test_a_per_day_answer_stored_before_is_the_events_answer_and_is_never_asked_again` (a question was posted)
- `test_per_day_answers_that_disagree_read_as_the_latest_one_given`
- `test_an_unanswered_per_day_question_is_kept_and_the_event_is_still_asked_once`
- `test_a_no_stands_when_the_schedule_later_becomes_all_ours`
- `test_two_days_at_the_share_get_one_question_and_one_answer_between_them`
- `test_a_no_to_the_question_is_the_answer_for_every_day_of_the_event`

`test_fifteen_of_fifteen_over_three_days_asks_nothing_and_pings_once_a_day` and
`test_a_marathon_with_no_schedule_yet_is_not_an_event_and_asks_and_logs_nothing` failed there only on the new
payload fields and words — their behaviour was already right, as expected. The rest of the 18 are older tests
whose expected words changed. `test_words_staff_stored_for_the_per_day_question_fall_back_to_the_shipped_ones`
was written after the change and never seen failing. Passing before and after, pinning what must not move: the
name rule's tests, `test_the_staff_answer_beats_every_rule_both_ways`, `test_every_run_with_a_baf_runner_is_a_baf_event`,
`test_one_all_baf_run_is_too_few_to_be_an_event`, and every section-D test.

### What was NOT verified

- Nothing ran against Discord: no real question, no real button press, no real ping, no restart.
- The live database: whether `marathons.baf_event_ask` holds any per-day record today was not read. The read
  path for one is pinned by tests with hand-written records, not by a real v208 row.
- The live settings: whether staff stored `_ask_text` or `_line` with `{day}` was not read (the fallback is
  pinned).
- No browser: the drawer's re-drawn lines and the tracker's head badge were checked through the mock's JSON,
  `check.mjs` and the site tests only.
- The mock still reads a marathon as one show-day; a multi-day drawer was not drawn anywhere.

## Review fixes (whole event) 2026-10-06

An independent review of `af1cbd76` found seven things and no blocker. Code and tests: commit `c32f9988` on
`baf-event-whole`. Tests are in `tests/cogs/content/test_marathon_baf_event.py` (**cog**),
`tests/test_marathon_baf_event.py` (**pure**), `tests/test_marathon_thread_controls.py` (**controls**) and
`tests/api/tools/test_marathons.py` (**api**). *Seen failing* means: the new test files were run against a
throwaway worktree of `af1cbd76` before the fix.

| # | Finding | What changed | Pinned by · seen failing before? |
|---|---|---|---|
| 1 | **Mid-event cliff.** A yes event that a re-read moved to unsure pinged per run until Leads answered: 15/15 over three days, day 1 pinged at two hours, one outside run added to day 2 → 15/16 → Game 6's AND Game 7's 15-minute heads-ups both carried the role | `judge(acted=)`: an unsure reading stays **yes · `acted`** once the marathon holds a day's own ping record whose reason is a rule (`marathon_baf_event.acted`). The question is still asked (`undecided`), the line says why. A Leads No applies from then on; under the ask percent it reads no at once (section A) | cog `test_an_event_already_announced_as_baf_keeps_one_ping_a_day_while_leads_are_asked` — **yes**, with exactly the finding's `[Game 1 120, Game 6 15, Game 7 15]`; cog `test_a_no_after_the_days_ping_leaves_that_day_closed_and_later_days_per_run` — **yes**; cog `test_an_announced_event_that_drops_under_the_ask_percent_reads_no_at_once` — passed before (pins the owner's rule); pure `test_an_unsure_reading_stays_yes_only_once_a_rule_made_the_bot_ping_a_day` — **yes** for the four kept cases, the five not-kept cases passed before (among them: a marathon that never acted on a yes still treats unsure as no); pure `test_an_event_the_bot_acted_on_still_reads_no_under_the_ask_percent_and_takes_a_leads_no` — **yes** |
| 2 | The drawer's *Follow the schedule (…)* showed the rules-only answer while following gives the Leads answer: unsure 3/4, Leads Yes, switch No → *Follow the schedule (not decided)*, and pressing it gave *a BaF event — staff answered…* | `judgement_of(own=False)` sets only the switch aside. `worked_out`, the drawer's follow choice and the thread's follow button all read it; the drawer says *Follow the answer (…)* and the thread *BaF event: follow the answer (…)* (`marathon_controls_baf_follow_answer`) while a Leads answer stands | cog `test_the_follow_choice_says_what_following_gives_and_that_it_is_the_answer` — **yes** (`('unsure', 'share') == ('yes', 'leads')`); pure `test_following_is_the_judgement_with_only_the_switch_set_aside` — **yes**; api `test_patch_clears_the_questions_answer_and_follow_says_what_following_gives` — not run before (it needs the new route) |
| 3 | No way to CLEAR a Leads answer | `clear_answer`, one writer behind the thread's fourth button (only while an answer is stored) and `PATCH … baf_event_answer: "clear"` (the drawer's *Clear the answer*); logged under `marathon.baf_event_set` with `cleared`; every question edited to *who cleared the answer*; one fresh question may follow | cog `test_staff_clear_the_answer_from_the_thread_and_the_question_is_asked_once_more`, `test_a_cleared_answer_gives_the_name_and_the_runs_back_the_say`; pure `test_clearing_takes_every_answer_off_and_the_cleared_record_is_not_the_question`; controls `test_a_stored_answer_adds_a_clear_button_and_follow_says_it_follows_the_answer`; the api test above — all **failed before, on the missing writer / argument** (a new move has no earlier behaviour to fail on) |
| 4 | The doc did not say the Leads answer also stands whatever the show's NAME becomes | Section A, rule 2's row | pure `test_a_leads_no_stands_whatever_the_show_is_renamed_to` — passed before (the behaviour was already so; the doc was the defect) |
| 5 | `marathon.baf_event_no_ping` is IMPORTANT and `no_baf_run` is ordinary now; and the row was only written between the day's last run starting and all runs being done | The kind is split: `marathon.baf_event_no_baf_run` (ROUTINE in `logkinds.py`) for a day with no BaF run, `marathon.baf_event_no_ping` (IMPORTANT) for `nobody_to_name` and `marks_spent`. `note_missed` no longer skips a day that is over | cog `test_a_day_with_no_baf_run_is_a_routine_row_written_once_even_after_the_day_is_over` — **yes**: before, three ticks after the day was over wrote NO row of either kind (checked by asking the old code for a `no_ping` row: `[] == ['no_baf_run']`); the two older no-run tests now expect the routine kind |
| 6 | A STORED old value of a re-worded key rendered stale words (*…is a BaF event — staff answered for this day.*) | No mechanism versions a stored value, so the four keys whose meaning changed on this branch are RENAMED (`SettingsStore.load` ignores a key the registry no longer has) | cog `test_a_value_stored_under_a_re_worded_keys_old_name_is_not_read` — **yes**: the stale stored question (*Is that day ours?*) was posted |
| 7 | Two live questions were each edited with their own *X answered* while only the latest counts | `note_questions` edits every question message the marathon holds to the one standing line, on an answer and on a clear | cog `test_every_question_the_marathon_holds_says_the_one_answer_that_stands` — **yes** (the older message was left untouched); cog `test_a_question_message_that_is_gone_does_not_stop_the_others_being_edited` — passed before (it guards the new loop: one failed edit must not stop the rest) |

### The thread controls' BaF row, as it renders

Rows 0–1 are the older switches and the tracker link, placed by Discord (seven or eight buttons plus the link).
Row 4 is the BaF row; five is Discord's limit for a row.

| State | Row 4 |
|---|---|
| No answer stored (the switch on follow, yes or no) | **3**: *BaF event: follow the schedule (what following gives)* · *BaF event: yes* · *BaF event: no* — the standing one lit and not pressable |
| An answer to the question is stored (whatever the switch says) | **4**: *BaF event: follow the answer (the answer)* · *BaF event: yes* · *BaF event: no* · *Clear the answer* |

### Decisions made in this pass

1. **What counts as *acted*:** a day's own ping record that is `sent` or `unconfirmed`, not `per_run`, not
   `missed`, with reason `name`, `all_runs` or `acted`. A claim still in flight does not count (it may be given
   back); an `unconfirmed` one does (the day is closed on it, and the role may have been mentioned). `acted` is
   itself a rule reason so day 2's ping, made while the reading stuck, keeps it sticking if day 1's rows are
   re-made.
2. **Each clear allows ONE fresh question, not one per marathon for ever.** The brief said *asked again ONCE (a
   fresh record)*; read as: a clear re-arms the question once. A second clear re-arms it once more — staff
   pressed twice. Nothing but a clear re-asks.
3. **A cleared record keeps its buttons.** A press on a question whose answer was cleared is an answer like any
   other (it takes the `cleared` flag off that record). There is no other meaning left for those buttons, and
   refusing them would be a dead control.
4. **The clear button shows whenever an answer is STORED**, also while the switch overrides it — the stored
   decision is what the move reverses.
5. **Clearing leaves the switch alone.** *Clear* then reads what the switch says, and under follow what the name
   and the runs say (or `acted`).
6. **The follow button on the thread carries the answer in brackets** (`{answer}` on both follow keys). The
   brief asked for the same truth on the thread; a button has no second line to put it on.
7. **Renamed, not versioned.** `marathon_baf_event_question`, `_answer_line`, `_reason_answered`,
   `_ping_no_baf_run`. ⚠️ A value staff stored under an old name on the live bot since v208 is dropped at the
   next boot (it shows once in the log as *settings ignored*) and the shipped words are used; staff re-enter it
   under the new row if they still want it.
8. **The mock holds an answer as `baf_answer`** and seeds marathon 31 (*Fastest Furs Fall Fest 2026*) with a
   *no*, so the drawer's *Follow the answer (…)* and *Clear the answer* can be seen locally. It has no ping
   records, so it never reads `acted`.
9. **Not changed:** a switch move to follow still answers *is worked out from the schedule now*
   (`marathon_baf_event_word_follow`) even while a Leads answer stands. The follow CHOICE says the truth
   everywhere since fix 2; that reply was not in the findings and is left for the conductor.

### What was NOT verified by this pass

- Nothing ran against Discord: no real fourth button, no real edit of two question messages, no real restart.
- No browser: the drawer's *Follow the answer (…)* label and *Clear the answer* button were exercised through
  the mock's JSON and its `PATCH` over HTTP, `node --check`, `check.mjs` and the site tests — not drawn.
- The live settings: whether staff stored a value under any of the four renamed keys was not read.
- The live database: no `baf_event_ask` or `baf_event_pings` row was read.
- `contract.json` has no route entry for a `PATCH` with `baf_event` or `baf_event_answer` (it had none for
  `baf_event` before either), so `check.mjs` does not call the clear route; the api test does, against the real
  router with fakes.
- `acted` across a real source that re-keys a pinged day's runs (the record is matched by `covers`, pinned in
  the pure layer only).
