# Event rooms — the event's posts live in its own room, staff get a Delete button, test rooms go 5 minutes after the end

> **Audience:** the build agent, then whoever maintains `black_bloc/events.py` / `cogs/community/events.py`.
> **Status:** 📐 DESIGN, TRACKED — written 2026-09-11 09:50 from the owner's 09:12 ask and his three answers
> (09:14 A · 09:31 B · 09:34 B). **Last verified: 2026-09-11 09:45** against `3d11e52` (v109 live): every
> function and key named below was read in the source that morning; nothing here has met Discord.
> Extends [`events-panel-design.md`](events-panel-design.md) (the panel, card and moves are unchanged) and
> the retention rules in [`where-picker-design.md`](where-picker-design.md) follow-up 3.

## The ask, verbatim (owner, 2026-09-11 09:12)

> In the channels how about we have the bot post an additional message for deleting the channel that only
> staff can press. I thought we had decided a newly generated room would go away after 5 minutes of
> creation. We can instead use the bot button I just mentioned to delete it and then have it 5 minutes
> after event ends. Also if we're making channels now don't have the event stuff post in the spam channel
> have the event stuff post in the actual channel like a real event would.

Three questions, asked one at a time, all answered:

| # | Question | Answer |
|---|---|---|
| 1 | "The actual channel" = the event's own room, or the real announcements channel? | **A — the event's own room** |
| 2 | "5 minutes after the event ends" — for real events too, or test mode only? | **B — test mode only**; live rooms keep `events_channel_retention_days` |
| 3 | Pressing **Delete this room** — delete only, or delete + settle the event? | **B — delete + settle**: an open event is cancelled with a DM'd reason; done/denied left alone |

## Why the posts land in the spam channel today (measured 09:40)

`make_review_channel` (`events.py:1460`) creates the room inside `events_category_id` (or the test
category) but **never calls `guard.own_channel(room)`** — every other channel-making feature does
(`polls.py:1519`, `tempvoice.py:445/2369`, `modmail.py:1263`, `raidtrain.py:2275`). So while the test
guard is installed `guard.allows_channel(room)` is False, `card_channel` (`events.py:1040`) redirects the
review card to `TEST_CHANNEL_ID`, and `post_to_announce` (`events.py:1235`) only ever targets
`events_announce_channel_id`, whose default is the test-spam channel. The room is a renamed shell.
`owned_channel_ids` is in-memory (`guard.py:45`) — a restart forgets every owned room unless something
re-owns them on ready, which `tempvoice.py:2360-2369` does in its reconcile and events does not.

## Part 1 — the event's posts go to its own room

### A. Own the room

- `make_review_channel` calls `guard.own_channel(room)` right after `create_text_channel` succeeds
  (guard may be None — `getattr(bot, "guard", None)` as everywhere else).
- `reconcile_events` (`cogs/community/events.py:1545`, runs on ready and every 5 min) re-owns every
  room of a row whose `review_channel_id` resolves, for rows in `OPEN_STATUSES` **and** `SWEPT_STATUSES`
  (a done room still has to be deletable by the button in test mode). Rows whose channel no longer
  resolves: `set_review(db, id, None, review_message_id, card_channel_id)` once and log
  `event.room_forgotten` `{event_id, channel_id}` — that closes finding (h) on `TODO.md` (dead ids kept).
- `_sweep_finished` and the Delete button call `guard.disown_channel(channel)` after a successful delete
  (the listener `on_guild_channel_delete` disowns too, so a hand-deleted room is forgotten as well).

Effect: with the guard on, the review card lands in the room (`card_channel` now returns it), and the
room passes `allows_channel`, so the posts below may go there. **TEST_MODE stays exactly as it is** — the
guard still refuses every channel the bot did not make; nothing new reaches the spam channel or anywhere
public.

### B. Where the event's posts go — a key, both ways

New enum key **`events_posts_where`** (group Events, help text in words like its neighbours):

| value | announce (on approve) | go-live ping | ended post | cancelled/denied note |
|---|---|---|---|---|
| `room` **(default — owner answer 1)** | the review room | the review room | the review room | the review room |
| `announce` | `events_announce_channel_id` (today's behaviour) | announce channel | — (never existed) | edit of the announcement (today) |
| `both` | both | both | room | both |

Implementation: one new helper `post_to_room(bot, guild, row, text, embed, kind)` in `events.py` beside
`post_to_announce`, same shape and same log kinds with a `_room` suffix (`event.announce_room`,
`event.go_live_room`, `event.ended_room`, `event.would_announce_room {reason}`, `event.announce_room_failed`).
It resolves `guild.get_channel(row["review_channel_id"])`, refuses in the log (never raises) when the row
has no room, when `events_mode != "on"`, or when the guard refuses the channel. The two existing callers
(`apply_decision` `events.py:1399`, `_go_live` `cogs/community/events.py:1485`) become one call each to a
new `post_event(bot, guild, row, text, embed, kind)` that reads `events_posts_where` and fans out; the
announce-channel message id keeps going to `set_announced` (so `edit_announcement` still works); the room
post's id is not stored (the room is deleted with the event — nothing to edit later).

- **Ended post** (new): `_finish` posts `ENDED_TEXT = "**{title}** has ended. Thanks for coming."` to the
  room when the value is `room` or `both`. No ping role on the ended post.
- **Cancelled / denied in the room**: `cancel_event` and `apply_decision(DENIED)` post one line to the room
  (`CANCELLED_ANNOUNCEMENT` already exists at `events.py:565`; denied uses the existing DM_DENIED wording
  minus the "Your event" address) when the value includes the room. The announce-channel edit stays.
- `mentions(ping_role_id)` applies to the room's announce and go-live exactly as to the channel's.

### C. What does NOT change

The review card, its buttons, `TRANSITIONS`, the scheduled event, the DMs, the website — untouched.
`events_announce_channel_id` keeps its meaning; a server that wants public announcements sets `announce`
or `both` on the Settings page or through `/event` ▸ Settings (which gains the value under the existing
`ModeSelect` row — a second `discord.ui.Select`, three options, same `change_settings` path).

## Part 2 — the staff **Delete this room** button

### A. The message

Right after `post_review_card` succeeds (and only when the card actually went to the room — i.e. the
target is the room, not the test channel), the bot posts one more message in the room:

> This room is Black Bloc's — it goes away on its own **{when}**. Staff can remove it sooner.

with one danger button **Delete this room**, `custom_id = event:{id}:delete_room`, a persistent
`DynamicItem` on the existing `DECISION_TEMPLATE` (extend the alternation to
`approve|deny|delete_room`, so the one `bot.add_dynamic_items` registration covers it). `{when}` is
`ROOM_GOES_MINUTES = "{n} minutes after it ends"` while the guard is on, else
`ROOM_GOES_DAYS = "{n} days after it ends"`, read from the two retention keys at post time (a stale
number on an old message is acceptable: the sweep, not the message, is the truth).

Store nothing new for it: the button's custom id carries the event id, and the room is the interaction's
own channel. **No schema change** (stays 34).

### B. The gate — in words, never a bare status

Reuse `decision_context` (`cogs/community/events.py:255`): guard refusal, `require_staff`, database, row.
New enum key **`events_room_delete_who`**, values `staff` (default) | `approver` — `approver` means the
role in the new role key **`events_approver_role_id`** (blank falls back to staff, mirroring
`applications_approver_role_id` at `settings_store.py:1044-1046`). A member who is neither gets the
standard `store.staff_refusal` sentence. The button is rendered for everyone (the room is staff + host
only, so the host sees it); pressing it as the host answers in words:
`ROOM_DELETE_NOT_STAFF = "Only staff can remove this room. If you want your event called off, use **Call it off** on `/event`."`

### C. The confirm step

Pressing it opens a modal `RoomDeleteModal` (title **"Remove this room?"**) with one optional paragraph
field, `label="A line the host is sent (if the event is still open)"`, `max_length=CANCEL_NOTE_LIMIT`.
Submit runs, under `event_lock`:

1. `fresh = get_event` — if `fresh["review_channel_id"] != interaction.channel_id`, answer
   `ROOM_NOT_THIS_EVENT` and stop (the button was moved or the row was re-pointed).
2. If `fresh["status"] in OPEN_STATUSES`: `cancel_event(bot, guild, fresh, "room_deleted", by=staff.id,
   note=<modal text>)`. Add `"room_deleted": "staff removed its room"` to `CANCEL_WHY` so the DM reads
   *"…has been cancelled — staff removed its room. The reason given was: …"*. Doing the cancel **first**
   is what keeps `on_guild_channel_delete` from cancelling it a second time with `review_channel_deleted`
   (it only fires for `OPEN_STATUSES`).
3. Delete the channel with `reason=ROOM_DELETED_BY.format(event_id=…, who=staff)`; guard refusal
   (`allows_place` False) logs `event.would_delete_channel` with `{"by": staff.id}` and answers
   `ROOM_DELETE_REFUSED_TEST` in words; a network error logs `event.room_delete_failed` and answers
   `ROOM_DELETE_FAILED` ("Discord would not remove it just now — nothing else was changed" — but note
   the cancel in step 2 HAS happened; say so in that sentence when it did).
4. `set_review(db, id, None, review_message_id, card_channel_id)`, `guard.disown_channel`, log
   `event.channel_deleted {event_id, channel_id, by: staff.id, cancelled: bool}` — the SAME kind the sweep
   logs, with `by` distinguishing the press from the sweep.
5. The interaction is answered ephemerally BEFORE the delete (the channel is about to vanish, and a reply
   into a deleted channel raises): `defer(ephemeral=True)` on modal submit, then
   `followup.send(ROOM_DELETED_SAID)` — if the followup fails because the room is gone, swallow and log at
   debug; the action log row is the record.

### D. The website

The Events page's event card gets the same move as a button, **Remove its room**, shown only when the row
has a `review_channel_id` and the viewer is staff — it calls a new `POST /api/events/{id}/room/delete`
with `{note}` that runs the identical function (one canonical implementation in `events.py`,
`delete_room(bot, guild, row, by, note, via=VIA_SITE)`), logging with `via`. The mock (`site/mock/`) gains
the route and `contract.json` counts it. Refusals come back as the same sentences.

## Part 3 — retention

Nothing changes in the numbers — owner answer 2. `events_test_retention_minutes` (default 5) already
governs "after it ends" while the guard is on and `events_channel_retention_days` (7) live;
`swept_anchor` already counts a DONE room from `ends_at`. Two things do change:

- The sweep **owns/disowns** as in Part 1A, and logs `event.room_forgotten` once when the channel has
  already gone (today it `continue`s silently and the row keeps the id forever).
- The Settings page help for both keys says what the Delete button is for: *"Staff can remove a room
  sooner with **Delete this room** in the room itself."*

## Keys (all in `settings_store.py`, all reachable from the Settings page and `/settings` — checklist 33)

| key | type | default | bounds / values |
|---|---|---|---|
| `events_posts_where` | enum | `room` | `room` · `announce` · `both` |
| `events_room_delete_who` | enum | `staff` | `staff` · `approver` |
| `events_approver_role_id` | role | blank | blank → staff |
| `events_room_notice` | bool | `true` | false = do not post the Delete message (the sweep still runs) |

Keys 202 → **206**. Schema stays 34. `SETTINGS_KEYS` in `events.py:1771` gains the four so the `/event`
Settings sub-panel lists them; `site/mock/contract.json` core-settings count unchanged (these are not
core).

## Tests (mirror the package)

`tests/test_events.py` — `post_event` fan-out for each of the three values (announce only, room only,
both) with the guard present and absent; `delete_room` cancels an OPEN row first and not a DONE/DENIED
one; the listener does not double-cancel; guard refusal logs `would_delete_channel` with `by`; the
network failure path leaves the cancel in place and says so; `CANCEL_WHY["room_deleted"]` wording.
`tests/cogs/community/test_events.py` — the button renders in the room, the host's press is refused in
words, staff's press opens the modal, submit follows steps 1–5, reconcile re-owns rooms on ready and logs
`room_forgotten` once for a dead id, `_finish` posts the ended line to the room. Site: the new route in
`tests/site/…` beside the other event routes, plus the mock contract check.

## Sweeps for the owner (rows 351+ in `docs/access/sweeps.md`)

351 propose + approve an event in test mode → the card AND the "goes away" message appear IN the room, not
in spam · 352 the go-live ping lands in the room at the start · 353 the ended line lands at the end and
the room vanishes 5 min later (`event.channel_deleted`, no `by`) · 354 press Delete as the host → refused
in words · 355 press as staff on an open event → modal → room gone, host DM'd with the note,
`event.cancelled` + `event.channel_deleted {by}` · 356 press on a done event → room gone, no DM, status
unchanged · 357 restart the bot mid-event → the room still accepts the ended post (re-owned on ready) ·
358 Settings page shows the four keys and flipping `events_posts_where` to `both` puts the next announce
in spam as well.

## Deviations

(filled by the build agent — anything the code does differently from the above, with the reason)
