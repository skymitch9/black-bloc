# Reminder edit in place — a moved run edits its heads-up instead of posting again

> **Audience:** the conductor, reviewers, and the next session touching marathon reminders, host-block heads-ups, the
> schedule read or the stream re-time. **Status:** TRACKED · 🔨 **BUILT on branch `reminder-edit-in-place` (off `main`
> `01f04853`, then `main` `77f01b1c` — v196, the viewer source — merged INTO the branch), NOT merged to `main`, NOT
> deployed.** ⚠️ **Schema 85 → 86** (one nullable column, `marathon_runs.reminder_posts`; built as 84 → 85 and
> renumbered in the branch's merge commit, because `hotfix-viewer-source` took 85 first). Registry keys **727 → 730**
> (+3; 721 → 724 before that merge).
> API routes unchanged, no payload changed. Log kinds **+8** (four for runs, four for host blocks).
> **Last verified: 2026-10-03 Phoenix** — against the branch's own code by its tests
> (`tests/test_marathon_reminder_posts.py`, `tests/cogs/content/test_marathon_reminder_posts.py`, three tests in
> `tests/test_marathon_host_highlights.py`, three in `tests/test_settings_store.py`, one migration test in
> `tests/storage/test_db.py` — from a schema-85 file), the whole suite, `ruff check`, and `node site/mock/check.mjs` against a mock started from
> the worktree — the exact counts are in the build's final report and, after the merge, in `docs/deploys.log`.
> ⚠️ **NOT checked:** anything against Discord — no real message was edited, so whether Discord shows *(edited)*,
> whether an edit to a post that carries a role mention stays silent on a real phone, and what the real rate limit
> does to ten edits in one channel are all unmeasured; the live database and every live key; no browser rendered the
> three new Settings rows (the mock answered the payload; nothing drew it); the bot was never run. Secret NAMES only.

## How it worked before (read in code 2026-10-03, `main` `01f04853`)

For a BaF member's run in a tracked marathon the bot posts a reminder at each mark in `marathon_reminder_minutes` (plus
`marathon_ping_minutes`): one copy in the marathon's staff thread (`Marathons._post_reminder`) and one public copy
(`post_public_reminder`); a BaF host block gets a public heads-up at the same marks (`remind_hosts` → `heads_up`). The
run row keeps `reminders_sent`, a JSON list of marks; a host block keeps `marks` in its record in
`marathons.host_highlight_posts`.

When a run moved later by `marathon_move_minutes` or more (`_write_plan` on a schedule read, `signals.retime` on a
stream re-time) `mt.rearmed` forgot every mark whose moment was in the future again, so the reminder **posted again**
at the new time — and, since v195, the 15-minute one pinged the Marathon role again. A slip smaller than that posted
nothing and edited nothing. The earlier post kept its old time for ever: **no message id was stored** for a reminder
(the staff copy's id was only written to the action row).

## The decision, verbatim (owner, 2026-10-03)

Asked: *"if a run is delayed after the 15 minute warning do we make a new post at the next 15min warning or edit the
existing post?"* — answered: *"yes edit in place"*.

## What is stored

**A run:** `marathon_runs.reminder_posts` (TEXT, NULL for every run that was there before), one JSON object keyed by
mark:

```
{"15":  {"posted": true,
         "staff":  {"channel_id": …, "message_id": …, "text": "…", "head": "…", "at": "<scheduled_at shown>"},
         "public": {"channel_id": …, "message_id": …, "text": "…", "head": "…", "at": "…"}},
 "120": {"posted": false}}
```

**A host block:** the same object under `reminders` in the block's record inside `marathons.host_highlight_posts`
(no schema change — the record already carried `marks`); a block has only a `public` copy.

| Field | What it is |
|---|---|
| `posted` | a copy of this mark went out. `false` = the mark was spent without a post (skipped as stale, or every send failed) |
| `text` | the template's words as the post shows them — what the next render is compared against, so an unchanged run costs no Discord call |
| `head` | whatever stood in front of the words when it was sent: the role mentions (`<@&…> `) and, in a rehearsal, the note line. An edit writes `head + new words`, so the post reads the same |
| `at` | the `scheduled_at` the post shows — the *from* of the action row |
| `people` | on a `public` copy only, since 2026-10-06 (announce overrides, review fixes): the ids the post names. An edit can keep or lose a name and adds one only when the decision announces them; a copy with no `people` is from before the record and reads as naming everyone of ours not left out by name. The rule is `announce-overrides-design.md` ▸ *A post already up* |

The mark and its entry are written **in one UPDATE** for a skipped mark and by the re-arm (`mrem.run_fields`), so the
two never disagree. For a posted mark the mark is stored before the send (the older restart rule) and the entry right
after it; a crash in between leaves a sent mark with no entry, which reads as *posted, not editable* — the safe side.

## The rules

1. **Any change of a run's start edits every reminder already posted for it** — the schedule sheet, the setup buffer,
   a stream re-time, staff's *sheet times*, a move earlier, a 3-minute slip inside the 15-minute window. There is no
   threshold: `marathon_move_minutes` still decides what is *logged as moved* and what re-arms an unposted mark, not
   what is edited.
2. **One place does it.** `sync_reminders` (`cogs/content/marathon_reminder_posts.py`) runs in `Marathons.follow`
   after `remind` and `remind_hosts`, every minute, per marathon, under the marathon's lock. It does not care who moved
   the run: it re-renders the same template with the run's current fields and compares the words with `text`.
   Unchanged → nothing. Changed → fetch the message, one edit, store the new `text` and `at`.
3. **The edit notifies nobody.** `AllowedMentions.none()`. The `<@&…>` in front stays in the text (it is `head`), so the
   post reads as it did; an edit never re-pings, and it never adds or removes a mention.
4. **A posted mark is never re-armed.** `mrem.rearmed` in `edit` keeps every sent mark that posted; only a mark that
   was skipped or whose sends all failed (`posted: false`) is forgotten when its moment is in the future again, and it
   then fires normally at the new moment and is remembered.
5. **Only an UPCOMING run is followed** (and a DROPPED one, rule 7). Once a run is live or done its reminders stand as
   posted — *a live or done run is never moved* (`marathon-hotfix-design.md` ▸ Follow-up 2026-10-03).
6. **A whole day that shifts is bounded.** One pass makes at most `marathon_reminder_edit_limit` edits per marathon
   (10), the soonest run first and, within a run, the nearest mark first and the public copy before the staff one;
   runs before host blocks. What did not fit is still different from its stored `text`, so the next minute's pass
   takes it. N posts → exactly N edits, ⌈N / limit⌉ minutes. Each edit is two Discord calls (a fetch, a PATCH).
7. **A run taken off the schedule** (state `dropped`) has its posted reminders rewritten from
   `marathon_reminder_dropped_template`, whose `{state}` is the existing `marathon_state_dropped` (*off the schedule*)
   — the wording the board and a run's own post already use. A run that comes back is rewritten with its time again.
   A host block says so only when **every** run of it is dropped; a block that loses its first run shows the run it now
   opens on.
8. **The message is gone** — deleted by staff (`message_gone`), its channel deleted (`channel_gone`), or Discord
   refuses the edit with Forbidden (`no_permission`): one `marathon.reminder_lost` row with the reason, the id is
   forgotten, the mark stays `posted` — **no repost, no retry**.
9. **Any other failure** (a 5xx, a timeout, a channel Discord would not show just now): one
   `marathon.reminder_edit_failed` row, the id is kept, and the edit is tried again after `RETRY_AFTER` (10 minutes),
   never every minute; the row is written once per (post, wanted words).
10. **A public copy whose people have all opted out since** is left as it is (there is nobody left to name).
11. **A rehearsal** (`marathon_mode = shadow`): the copy sits in the rehearsal home with its note line in `head`; the
    edit keeps the note and the row is `marathon.would_edit_reminder`. `marathon_mode = off` edits nothing.

## Reminders already posted when this deploys

They have a sent mark and no stored id. **Decision: such a mark is *posted, not editable* — it is never re-armed and
never edited.** So for a run whose 15-minute reminder went out before the deploy and which then moves: the old post
keeps its old time and **no second post is made** (the old behaviour would have posted again). That is the one-time
cost; every reminder posted after the deploy is remembered. The same rule covers a host block's record with `marks`
and no `reminders`.

⚠️ It cannot tell a pre-deploy *posted* mark from a pre-deploy *skipped* one (both are just a number in
`reminders_sent`), so a mark that was skipped as stale before the deploy also never fires for that run. Runs read
after the deploy are unaffected.

## The time shown

`{in}` and `{when}` are both Discord timestamps (`mt.run_fields`: `<t:…:R>` and `<t:…:f>`), not literal text, so an
edited post cannot say something false like *in 15 minutes*: the edit swaps the two stamps and Discord draws *in 35
minutes* / the new clock time for each reader.

The public 15-minute copy with the default words, a run moved from 18:30 to 18:50 UTC (the test's own values):

| | Text (`test_the_edited_public_copy_reads_exactly_like_this_before_and_after`) |
|---|---|
| Before | `<@9001> runs **Super Metroid** (Any%) on **SS4C** <t:1799087400:R> — <t:1799087400:f>. https://twitch.tv/skyruns` |
| After | `<@9001> runs **Super Metroid** (Any%) on **SS4C** <t:1799088600:R> — <t:1799088600:f>. https://twitch.tv/skyruns` |
| Dropped | `<@9001> runs **Super Metroid** (Any%) on **SS4C** — off the schedule.` |

With the marathon's ping switch on, the copy was sent as `<@&5001> <@&6100> <@9001> runs …` (the runner's ping role,
then the Marathon role) and every edit keeps exactly that prefix in front of the new words
(`test_an_edit_notifies_nobody_and_keeps_the_role_mention_it_was_posted_with`).

## The keys (3, Marathons group: registry + mock row + label; Settings page and `/settings`)

| Key | Type | Default | |
|---|---|---|---|
| `marathon_reminder_on_move` | enum `edit` / `repost` | **edit** | `repost` is exactly the behaviour before: posted reminders are left alone, a move later by `marathon_move_minutes` or more re-arms every mark ahead and posts again |
| `marathon_reminder_edit_limit` | int 1–50 | **10** | edits per marathon per minute (rule 6) |
| `marathon_reminder_dropped_template` | text — the reminder fields + `{state}` | `{member} {part} **{game}** ({category}) on **{marathon}** — {state}.` | both copies and host blocks (rule 7) |

Ids are stored in both modes; in `repost` a re-armed mark's entry is dropped with the mark and the new post overwrites
it, so flipping the key later edits the newest post.

## The action rows

| Kind | Level | When | Details beyond the run's (`marathon_id` `run_id` `members` `game` …) |
|---|---|---|---|
| `marathon.reminder_edited` | routine | a copy was rewritten | `mark` `copy` (`staff` / `public`) `from` `to` `dropped` `message_id` `channel_id` |
| `marathon.would_edit_reminder` | routine (shadow) | the same, in a rehearsal | the same + `shadow_home` |
| `marathon.reminder_lost` | routine | rule 8 | the same + `reason` |
| `marathon.reminder_edit_failed` | **important** (`_failed`) | rule 9 | the same + `reason` |
| `marathon.host_reminder_edited` · `marathon.would_edit_host_reminder` · `marathon.host_reminder_lost` · `marathon.host_reminder_edit_failed` | as above | a host block's heads-up | the block's (`runs` `hosts` `members` …) + the same fields; `from` / `to` are the block's first run's start |

## Deviations

1. **The edit runs on the minute tick, not at the write.** A move is corrected within a minute of the read that
   applied it (the read and the follow share a tick; staff's *sheet times* waits for the next one). One place, every
   cause, and a restart or a failed edit heals itself — at the cost of up to a minute.
2. **Words are compared, not times.** So a change to `marathon_reminder_template` /
   `marathon_public_reminder_template`, to a part word, or to the run's game or category also rewrites the posted
   reminders of every run still UPCOMING (bounded by rule 6). That is the highlight's existing rule (a template change
   re-edits every post that is up), and it keeps *"every word is editable"* true for posts already out.
3. **`RETRY_AFTER` (10 minutes) is a constant, not a key** — it is the back-off of a failure path, not a decision
   about what members see. Say so if it should be a key.
4. **Deferred edits leave no row.** When the limit holds edits back, they happen a minute later and log then;
   `sync_reminders` answers the budget (`left`, `waiting`) for tests, nothing writes it down.
5. **A reminder posted while `on` and edited while `shadow`** is edited where it stands (the real channel) and logged
   as a would-row — the highlights' existing behaviour (`sync_highlights`), kept.
6. **`_write_plan` and `signals.retime` both still call the re-arm** (now `mrem.run_fields`); there is one re-arm
   *rule* and one *edit* place, not one move site — staff's *sheet times* writes times without re-arming, as before.
   The organisers' sheet laid over a marathon (v196, `marathon_overlay`) moves runs through `signals.retime`, so its
   moves are re-armed and edited by the same two paths; no test here drives the overlay itself.
7. **The 15-minute copy is still not edited when its run goes live or finishes** (`marathon-role-ping-design.md` B's
   last bullet stays true); only the reason changed — the id is stored now, the rule is rule 5.
8. **No site surface shows the stored ids.** `GET /api/marathons/{id}` still answers `reminders_sent` only.
9. **One test of the viewer-source build was re-seeded, not re-asserted.**
    `tests/cogs/content/test_marathon_viewer.py::test_switching_the_overlay_mid_day_snaps_the_times_once_each_way`
    seeded `reminders_sent = [15, 120]` with nothing remembered and expected the 15 to re-arm. Under this build a
    mark with nothing remembered is *posted, not editable* and is held, so the seed now says both marks were spent
    WITHOUT a post (`reminder_posts` with `posted: false`) — the case that still re-arms. Its assertions are unchanged.
10. **`host_reminder_*` are four more kinds** rather than a `host` flag on the run kinds, following
   `marathon.host_reminded` / `host_reminder_skipped` / `host_reminder_failed`.

## What was NOT verified

- A real edit in Discord: the *(edited)* mark, silence on a phone, the real rate limit for ten edits a minute in one
  channel (discord.py sleeps through a 429; the tick holds the marathon's lock while it does).
- `discord.Forbidden` from a channel fetch (as against a message edit): `find_channel` reports it as *not readable*,
  which is rule 9 (retried every 10 minutes, one row), not rule 8.
- The first boot after the deploy against live rows (pre-deploy marks staying quiet) — sweeps row `RE-e`.
- The three Settings rows in a browser.
