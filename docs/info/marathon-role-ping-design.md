# Marathon role ping — the Marathon role on the 15-minute heads-up; a finished highlight goes past tense

> **Audience:** the conductor, reviewers, and the next session touching marathon reminders, public highlights, host
> blocks or the thread controls. **Status:** TRACKED · 🔨 **BUILT on branch `marathon-role-ping` (off `main` `322e831d`),
> NOT merged, NOT deployed.** Schema unchanged. Registry keys **706 → 720** (+14). API routes unchanged; `GET
> /api/marathons/{id}` (and the list rows, same builder) gained one field, `role_ping`. No new log kinds — existing rows
> gained fields.
> **Last verified: 2026-10-03 20:5x Phoenix** — against the branch's own code by its tests
> (`tests/test_marathon_role_ping.py`, `tests/cogs/content/test_marathon_role_ping.py`, the new blocks in
> `tests/test_marathon_public.py`, `tests/cogs/content/test_marathon_public.py`,
> `tests/cogs/content/test_marathon_host_highlights.py`, one test in `tests/api/tools/test_marathons.py`), the whole
> suite (`pytest -q -n 16 -rfE`: **9919 passed, 3 skipped**), `ruff check black_bloc tests site` clean, and
> `node site/mock/check.mjs` against a mock started from the worktree on `MOCK_PORT=8821` (*22 pages, 288 routes, 26
> core settings, all keys present*) plus the ten node test files.
> ⚠️ **NOT checked:** anything against Discord — **a real notification can only be proven in Discord** (whether the
> live Marathon role is mentionable, whether the bot holds Mention Everyone in the reminder channel, whether a member's
> phone buzzes); the live database, the live value of `marathon_mode`, `marathon_role_id`, `marathon_reminder_pings`,
> `marathon_public_reminders`; no browser rendered the drawer line or the Settings rows (the mock answered the payload;
> nothing drew it); the bot was never run. Secret NAMES only.

> ⚠️ **2026-10-06 — superseded in part by [`baf-event-ping-design.md`](baf-event-ping-design.md)** (branch
> `baf-event-ping`, NOT merged when this note was written). What changes, and nothing else on this page:
> - ~~The Marathon role rides the `marathon_ping_minutes` heads-up of every BaF run and BaF host block.~~ **On a
>   BaF event day it rides ONE heads-up** — the `marathon_baf_event_ping_minutes` (120) one of the day's first BaF
>   run, or the next one still to come — and no other that day, a host block's included. Every other day is as
>   written below. Why: the owner, 2026-10-06 — one role ping per run on a show where every run is ours was noise.
> - **Section A's table row *Any other mark (`1440`, `120`, …) — no Marathon role*** is true only off a BaF event day.
> - **Two more reasons** join the verdict's list, set at the send: `baf_event_day` (another heads-up carries the
>   day's ping) and `baf_event_pinged` (the day already had it).
> - **`status_line` / `state_of`** take the runs: the per-run line is left out when every show-day shown has its
>   one ping, and one line per show-day follows.

## The cause (measured 2026-10-03 on the live bot — `docs/TODO.md` ▸ 🔔 Chunk 4)

GDQueer's ping switch went on at 12:35:26 (`marathon.ping_role_set`), 26 minutes before a BaF member's 15-minute
reminder. That reminder and the live highlight both logged `pinged=False, roles=[]`. `Marathons._ping_roles` collects only
(1) the runner's own *ping me* role and (2) the marathon CHANNEL row's spotlight ping role through the ping-windows gate
— and the GamesDoneQuick row has no role and ping mode `never`. `marathon_role_id` was read only by the Marathon role
button block; **no post ever mentioned it.**

## The decision, verbatim (owner, 2026-10-03 20:2x Phoenix)

> *"lets do 15 for now, also on the highlights once a run has been completed can we change the text to past tense, Jr
> ran x game today on GDqueen. basically just change runs to ran and remove the ping for marathons."*

## A. Which message carries the mention, and why

**Measured first: today BOTH copies carry `_ping_roles`' roles.** `Marathons._post_reminder` sends
`ping_prefix(*roles) + text` to the staff thread with those roles allowed, and hands the same list to
`post_public_reminder`, which does the same in the public reminder channel. So with a runner's *ping me* role set, that
role is pinged twice — once in the staff-only thread. That is unchanged by this build (it is the older design's
behaviour, and nobody asked for it to move); it is recorded here because the brief asked.

**The Marathon role goes in the PUBLIC copy only, once.** The thread is staff-only: a role members hold, pinged where
they cannot read, is noise. So:

| Message | Channel | Mentions |
|---|---|---|
| Staff copy of the ping-mark reminder | the marathon's thread (or the marathon channel when it has none) | `_ping_roles` as before, **minus** the Marathon role if it happens to be one of them (`without_role`) |
| **Public copy of the ping-mark reminder** | `marathon_reminder_channel_id`, else `golive_channel_id` | `_ping_roles` as before **plus the Marathon role, once** (`with_role` de-duplicates) — text prefix `<@&…> ` and `AllowedMentions(roles=[…])`, so it notifies |
| A BaF host block's ping-mark heads-up | the same public channel | **the Marathon role, once** — unless the block opens on a BaF runner's run, whose own public copy carries it at the same minute (`runner_copy`) |
| Any other mark (`1440`, `120`, …) | both | no Marathon role |
| The live highlight, the shoutout | public / thread | no Marathon role, whatever `marathon_live_pings` says about the others |

*The ping mark* is `marathon_ping_minutes` (15). It works with the channel row on ping mode `never` and no role — the
verdict never reads the channel row.

**The verdict** (`black_bloc/marathon_role_ping.py:decide`, built per send by
`cogs/content/marathon_role_ping.py:verdict_for`) answers either the role id or ONE reason, checked in this order:

| Reason | When | What staff read under the switch |
|---|---|---|
| `switch_off` | the marathon's own ping switch is off | nothing — the switch says so |
| `role_pings_off` | `marathon_role_pings` is off | `marathon_role_ping_line_key_off` with `{key}` |
| `reminder_pings_off` | `marathon_reminder_pings` is off (it says *any role at all*) | same |
| `public_reminders_off` | `marathon_public_reminders` is off — no public copy exists | same |
| `announcements_off` | this marathon's BaF announcements are off — no public copy | `marathon_role_ping_line_announcements_off` |
| `rehearsal` | `marathon_mode` is not `on` | `marathon_role_ping_line_rehearsal` |
| `unset` | `marathon_role_id` is blank | `marathon_role_ping_line_unset` |
| `gone` | the role is not in the server any more | `marathon_role_ping_line_gone` |
| `not_mentionable` | the role is not mentionable AND the bot lacks Mention Everyone in the reminder channel (channel overwrites count; server-wide permission when the channel is unknown) | `marathon_role_ping_line_not_mentionable` |
| — (mentions) | none of the above | `marathon_role_ping_line_on` — `{role}` `{minutes}` |

Two more reasons are set at the send, not by the verdict: `no_public_copy` (the public copy was skipped or failed —
opted out, same channel, no channel, a send error) and `runner_copy` (a host block left it to the runner's copy).

**Nothing breaks when it cannot ping**: the heads-up posts without the role and the row says why.

**The rows.** `marathon.public_reminded` (and its `would_` twin, `_skipped`, `_failed`) carry `roles` — what THAT
message mentioned — and, at the ping mark, `marathon_role` (the id, or null) and `marathon_role_reason`.
`marathon.reminded` carries `roles` (the staff copy's), `public_roles` (the public copy's, `[]` when none posted),
`marathon_role` and `marathon_role_reason`. `marathon.host_reminded` gained `pinged`, `roles`, `marathon_role`,
`marathon_role_reason`. A public copy that fails to send records `pinged: false, roles: []`.

**Where staff see it.** The thread controls' pinned message gains one line while the switch is on (re-rendered by the
existing `refresh_controls` whenever what it shows changes — a setting, the role, the switch). The marathon drawer's
Settings foldout draws the same line under *Ping the marathon role* from `role_ping: {mentions, reason, line}`; the site
line names the role as `@name`, the Discord line as a mention that pings nobody (`AllowedMentions.none()`).

## B. A finished run's public highlight

**Before this build:** `sync_highlights` re-rendered the SAME `marathon_public_template` with `{state}` = *done*
(`marathon.public_highlight_edited`, `state=done`); the edit already sent `AllowedMentions.none()` and already dropped
the role prefix (`edit_public` writes the template only).

**Now, on done:** the post is re-rendered from **`marathon_public_done_template`** with `{part}` swapped for its
past-tense word and a new `{day}`:

| | Default words |
|---|---|
| Runner, before | `**JR** runs **Game** — Any% on **GDQueer** · <t:…:f> (<t:…:R>) · on now · https://twitch.tv/…` |
| Runner, after | `**JR** ran **Game** — Any% today on **GDQueer** · https://twitch.tv/…` |
| Host, before | `**JR** hosts **Game** — Any% on **GDQueer** · <t:…:f> (<t:…:R>) · on now · https://twitch.tv/…` |
| Host, after | `**JR** hosted **Game** — Any% today on **GDQueer** · https://twitch.tv/…` |

- **No role mention, nobody notified.** The edit is the template only (any `<@&…>` line in front of the original is
  gone) and `AllowedMentions.none()`. A done post that still has a role mention in front of the right words is edited
  for that alone (`marathon_public.says(done=True)`) — the older *endswith* shortcut would have left it. A highlight
  POSTED for a run already over (staff opt-in late) mentions no role either.
- **`{day}`** (`marathon_public.day_word`): measured from when the run ENDED (`marathon_runner_posts.over_at`:
  `ends_at`, else `done_at`, else `scheduled_at`; a host block: its LAST run), in the server's zone
  (`default_timezone`). While that is still today: `marathon_public_day_today` (*today*). Once the server's day has
  passed: `marathon_public_day_earlier` (*on {date}*, `{date}` = `<t:…:D>`, which Discord draws in each reader's own
  language). ⚠️ **A post that said *today* is edited ONCE more at the first sync after the server's midnight**, so it
  never claims *today* tomorrow while the marathon is still followed. **An edit that happens late** (a restart, an
  outage) uses the same rule, so a run that ended on an earlier day reads *on <date>* straight away, never *today*.
- **Posts already up at deploy time.** `stands()` in `cogs/content/marathon_public.py`: a highlight whose run was
  **over before this process first followed highlights** (`since`) AND which still ends in the words the present-tense
  template gives it is **left exactly as it is** — role line and all, no mass re-edit. A highlight that is up for a run
  that finishes AFTER the boot gets the new done wording at its done edit. A run that ended while the bot was down and
  still reads *on now* is re-worded at the next boot (it never got a done edit at all).
- The same treatment for a host block's highlight (`follow_one` → the same `stands` and `public_text`).
- **The public 15-minute heads-up copy is NOT edited on done** — it is not edited today either (no message id is
  stored for it), and it stays as posted. ⚠️ **2026-10-03 — superseded in part by [`reminder-edit-in-place-design.md`](reminder-edit-in-place-design.md):** while `marathon_reminder_on_move` is `edit` (the default) a mark that POSTED is never re-armed — its post is edited in place — and a reminder's message id IS stored now.

## The keys (14, all Marathons group: registry + mock row + label; Settings page and `/settings`)

| Key | Type | Default |
|---|---|---|
| `marathon_role_pings` | bool | **on** — the ping-mark heads-up mentions the Marathon role when the marathon's ping switch is on |
| `marathon_role_ping_line_on` | text `{role}` `{minutes}` | *The public heads-up {minutes} minutes before a BaF run mentions {role}.* |
| `marathon_role_ping_line_key_off` | text `{key}` | *The Marathon role is not mentioned: {key} is off.* |
| `marathon_role_ping_line_announcements_off` | text | *The Marathon role is not mentioned: this marathon's BaF announcements are off, so no public heads-up posts.* |
| `marathon_role_ping_line_rehearsal` | text | *The Marathon role is not mentioned while marathon posts rehearse: marathon_mode is not on, and a rehearsal copy never pings it.* |
| `marathon_role_ping_line_unset` | text | *The Marathon role is not mentioned: no role is picked in marathon_role_id.* |
| `marathon_role_ping_line_gone` | text | *The Marathon role is not mentioned: the role in marathon_role_id is no longer in this server.* |
| `marathon_role_ping_line_not_mentionable` | text `{role}` | *The Marathon role is not mentioned: {role} is not mentionable and Black Bloc may not mention every role, so a mention would notify nobody.* |
| `marathon_part_runner_done` | text | *ran* |
| `marathon_part_host_done` | text | *hosted* |
| `marathon_part_commentator_done` | text | *was on commentary* |
| `marathon_public_done_template` | text, `marathon_public_template`'s fields + `{day}` | `**{runner}** {part} **{game}** — {category} {day} on **{marathon}** · {url}` |
| `marathon_public_day_today` | text | *today* |
| `marathon_public_day_earlier` | text `{date}` | *on {date}* |

The highlight's other words have no editor of their own on the site (they are Settings-page rows), so these are too.
`marathon_ping_minutes` and `marathon_public_template` had their help text updated to say what changed.

## Deviations

1. **A rehearsal never pings the Marathon role** (`rehearsal`). In `shadow` the public copy goes to the rehearsal home,
   which members may not see; pinging a role members hold there is the noise this build exists to avoid. The other
   roles still ping in a rehearsal, as before. ⚠️ **So the Marathon role is mentioned only while `marathon_mode` is
   `on`** — the conductor must read the live value before telling the owner it will ping.
2. **`marathon_reminder_pings` off also keeps the Marathon role out** — its help says *any role at all*, and a second
   meaning for one key would be a trap.
3. **The staff copy drops the Marathon role when it is also a runner's or the channel's ping role**, so "once, in the
   public copy" holds even then. If the public copy is then skipped, that role is pinged nowhere; the row says
   `no_public_copy`.
4. **`same_channel`**: when a thread-less marathon's staff copy lands in the reminder channel itself, the public copy is
   skipped (the older Deviation 3 of `marathon-public-highlights-design.md`) and the Marathon role is NOT added to the
   staff copy; the rows say `no_public_copy`. Not built because the live marathons all have threads.
5. **A host block that opens on a BaF runner's run leaves the mention to the runner's public copy** (`runner_copy`),
   so one minute never carries two Marathon-role pings for the same slot.
6. **The `/event` marathon card does not carry the reason line** — its header is two lines mirrored from the site
   drawer's header; the line is on the thread controls and the drawer's Settings foldout, the two places the brief
   named.
7. **No stored marker says "this post has its done words"** (that would be a schema change, with two other builds in
   flight). `stands()` decides from when the run ended against when the process started. The one case it gets wrong:
   staff re-word `marathon_public_template` AFTER a run finished on the old wording and before a restart — the old
   post no longer matches, so it is re-edited into the done wording. That is the older behaviour (a template change
   re-edits every post that is up), not a regression.
8. **The staff thread's shoutout done-edit (`marathon_done_template`) still says the present-tense part word** — the
   owner's ask was the public highlight; that thread post already ends *"— that run is over"*.
9. **`{day}` rolls over with one extra edit per finished highlight at the server's midnight**, only while the marathon
   is still being followed; a marathon archived the same day keeps *today*.

## What was NOT verified

- A real ping. Whether the live Marathon role is mentionable, and whether the bot holds Mention Everyone in the
  reminder channel — `not_mentionable` on the thread controls line after the deploy is how staff would find out.
- The live `marathon_mode`, and every live key above.
- The drawer line and the Settings rows in a browser.
- The first boot after the deploy against live posts (`stands` leaving the already-done ones alone) — sweeps row
  `MR-f`.
