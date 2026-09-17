# Send to… — a staff move that turns a request into an event, an event into a request, and a ticket into either with the member's say-so

> **Audience:** the build agent and reviewers. **Status:** TRACKED · ✅ **LIVE as v128** — merge `5a17466`, release `a0fa7f3`, deployed **2026-09-17 16:09** Phoenix; schema 43; `handoff_mode` on; the `## Deviations` foot is the truth where it departs from the body; sweeps **543–553** are the owner's. Was: ✅ BUILT on branch `send-to` off `main` `8a27840`. Read the
> `## Deviations` foot BEFORE the sections above: eighteen things differ from what is written here, and
> deviations **1–4** are the ones that matter (a public press opens the draft with no intermediate card; `moved_to`
> carries three shapes; nothing sweeps the 24 hours, the read decides; the asked wording lives in the confirm
> embed and is read back off it). Schema **42 → 43** (`requests.moved_to`, `events.moved_to`,
> `modmail_tickets.moved_to`) — ⚠️ **migrate before deploy.** Registry **254 → 256**; `pytest -n auto`
> **6304 → 6404**, both orders; mock **19 pages / 180 routes**. ⚠️ `handoff_mode` ships **on**, so every
> surface changes the moment this merges. Sweeps rows `ST-a`…`ST-k`. **Last verified: 2026-09-17 14:52** against `main` `9ef0dc5`: `requests.create_request(guild,
> user_id, what, why, due_on…)`, `STATUSES` (`open, in_progress, review, hold, done, declined, withdrawn`),
> `events.create_event(guild, requester_id, title, description, where, starts_at…)`, `PENDING / DENIED / CANCELLED`,
> the event draft (`cogs/community/events.py` `open_draft` / `render_draft` / `ProposeButton`), the request post's
> buttons (`blackmail-threads-design.md` §F, `PostMoveButton` + `move_pressed`), the ticket card (`modmail-doors-design.md`),
> `settings_panel.groups()` / `SELECT_LIMIT` 25. ⚠️ Secret NAMES only.

## Owner asks, verbatim (2026-09-17, 12:4x–14:5x)

*"…maybe a staff button to redirect one of them to a different experience. For instance if someone request an event I
want to be able to label it as an event and then it gets swept up in our event workflow experience and becomes an event
and no longer a request. The only weird one is turning a modmail into a request or event"* → (A) the front door shipped
(v125) → *"whats waiting for my word"* → *"do all 3"*.

## A. The moves — one helper, three surfaces

**Home:** `black_bloc/handoff.py` (pure: the trail rows, the wording) + the moves on the three cogs. One rule for
every hand-off: **the new thing is filed in the MEMBER's name, the old thing closes as *moved* with a link both ways,
and the member is told by DM.** Nothing is copied twice; nothing is deleted.

| From → to | Where staff press it | What happens |
|---|---|---|
| **Request → event** | the request's forum post (§F's button row) and the `/request` panel's staff card: **Send to events…** | opens the EVENT DRAFT for staff, pre-filled: title = `what`, description = `why` (+ a first line *"Filed as request #N by @member"*), proposer = the requester (the draft's `requester_id`), the When picker blank (staff picks). **Submit** creates the event through `create_event` exactly as `/event` does (review room, approvers…), then closes the request as **`moved`** (a new final status; `moved_to = "event:<id>"`), archives its post with a **moved** tag and one line *"→ event #N"*, DMs the member *"Your request #N is now event #M — staff will review it there"*. Cancel on the draft leaves the request untouched |
| **Event → request** | the event's review room card: **Not an event — make it a request** | `create_request(what = title, why = description)` in the requester's name (`source = event`), then the event is **cancelled** with `moved_to = "request:<id>"` (the existing cancel path + DM, reason text *"filed as request #N instead"*); the room's card gains the link; nothing else the cancel does changes |
| **Ticket → request / event** | the ticket card's staff row: **Make this a request…** / **Make this an event…** | ⚠️ a ticket is private. The bot DMs the member a CONFIRM card: *"Staff would like to file your ticket #T as a request/event in your name: `<title>`. Everyone on staff will see it. [Yes, file it] [No, keep it private]"* — the title and body come from a staff modal at the press (default: the ticket's subject and first message, editable). **Yes** files it (request or event draft handed to staff as above) and posts the link into the ticket; **No** posts *"@member said no"* into the ticket and nothing is filed; no answer in `handoff_confirm_hours` (24) = no. The ticket stays open either way — closing it is staff's own move |
| **Request → ticket** | the request's post / panel card: **Open a ticket with them…** | the existing staff door (`open_a_ticket(source=staff)`, behind `modmail_open_with_button` — the door is used regardless of that key here, since a hand-off is a staff decision, but say so); the ticket's first staff message quotes the request; the request stays as it is (a ticket beside a request is a conversation, not a move) |

**Trail.** Migration schema 42 → **43**: `requests.moved_to TEXT`, `events.moved_to TEXT`, `modmail_tickets.moved_to
TEXT` (all NULL); `requests.STATUSES` gains **`moved`** (final; no transitions out; a tag `moved` in the requests
forum — Setup adds it to an existing forum on the next reconcile, checklist 26); the site's request row shows *moved
→ event #M* with a link; the events page shows *moved → request #N* on a cancelled-by-hand-off event. `handoff.py`
writes every hand-off as ONE log row `handoff.<from>_to_<to>` with both ids.

**Keys.** `handoff_mode` — enum off/on, **on** (*"on draws the Send to… moves for staff; off hides them and refuses a
stale press in words"*); `handoff_confirm_hours` — int 1–168, **24** (*"how long a member has to answer a
make-this-a-request/event DM before it counts as no"*). Registry + mock rows + labels. ⚠️ **No new settings
namespace** — file both under `request` (the cap is full: see §C).

**Refusals.** Every press is staff-gated (`still_staff`, the §F pattern); a member's press says what it needs. A
request already final refuses *"#N is already <status>"*. An event already decided refuses likewise. A ticket with a
confirm pending refuses *"already asked @member — waiting until <when>"*.

## B. Tests (mirror the package)

`tests/test_handoff.py` (pure); `tests/cogs/community/test_requests.py` (request → event: the draft opens pre-filled
for staff, submit files the event AND closes the request as moved with the trail, the post is tagged + archived, the
DM; cancel leaves it; a final request refuses); `tests/cogs/community/test_events.py` (event → request); `tests/cogs/
moderation/test_modmail.py` (the confirm DM, yes / no / timeout, the ticket lines; the request→ticket door);
`tests/storage/test_db.py` (the migration on a 42 file); `tests/test_settings_store.py`. Both orders.

## C. Folded in: the settings-group cap guard

`tests/test_settings_panel.py::test_the_settings_groups_fit_the_select` — `assert len(settings_panel.groups()) <=
settings_panel.SELECT_LIMIT` with a message naming the 26th group, so the next namespace fails the gate instead of
silently dropping `youtube` off `/settings` ▸ A setting group… (found by the front-door build, v125). One test, no
code change; a code-note line beside `groups()` saying why.

## D. Docs

`code-notes.md`; this doc's `## Deviations`; `requests-panel-design.md`, `blackmail-threads-design.md` §F,
`modmail-doors-design.md`, the events design (strike what changes, checklist 35); the requests / events / modmail
guides in `guides_seed.json` (a staff fault line each: *"Somebody filed the wrong thing → Send to…"*); `sweeps.md`
rows `ST-a…`; `architecture.md` schema line (43). NOT `TODO.md` / `DONE.md` / `deploys.log`.

## Deviations

> Written by the build, **2026-09-17**, on branch `send-to` off `main` `8a27840` (v126).
> Everything below is a place the build did NOT do what §A–§D says, and why. ⚠️ **Nothing here
> has met Discord**: no boot, no token, no button pressed in a client, no DM sent, no deploy,
> and `TEST_MODE` was never flipped. The whole verification is `pytest -n auto`
> (**6304 → 6404**, green forward and under `BB_REVERSE=1`), `ruff check .` (clean), the
> ES-module parse of all 32 `site/public/assets/*.js`, `node site/mock/check.mjs`
> (*19 pages, 180 routes, 15 core settings, all keys present*), `node site/mock/discordmd.test.mjs`
> and `node site/mock/labels.test.mjs`. **No browser rendered either page**, real or mock.

1. ⚠️ **A press on a PUBLIC post opens the draft with NO intermediate card, which is one press
   better than `front-door-design.md` deviation 1 — and it is the same fact about the library,
   read the other way.** That deviation had to answer a posted press with a one-button ephemeral
   because `ProposeButton.callback` → `open_draft` → `panels.opened` → `interaction.response.defer()`
   is a `deferred_message_update` for a component, so `render_draft`'s `edit_original_response`
   would have drawn one staffer's half-filled draft over the front door for the whole channel.
   **Deferring `ephemeral=True, thinking=True` FIRST re-points `edit_original_response` at the new
   ephemeral**, so `open_request_draft` can call `render_draft` straight away and the post is never
   touched. `opened_here(interaction, on_post)` already encoded exactly that split for the §F move
   buttons, so the hand-off asks the same function rather than a second one. The front door could
   adopt the same shape if anybody wants the extra press back.

2. ⚠️ **`moved_to` carries THREE shapes, not one — because the design allows exactly three
   columns and a pending question needs more state than "where it went".** `kind:id` is the trail
   §A asks for; `asked:kind:<iso>` is a question in flight with its own deadline; `yes:event` is
   the member having agreed while staff still owe a date. A fourth column for the pending ask
   would have been a fourth column. `read_trail` reads all three and answers `None` for anything
   else, so a cell written by hand cannot crash a card.

3. ⚠️ **Nothing sweeps the 24 hours. The READ decides.** §A says *"no answer in
   `handoff_confirm_hours` (24) = no"*. A loop would have been a second place deciding the same
   thing, and the state is not stuck — it is simply stale. `expired()` is asked on every read: a
   member's late press answers *"no longer waiting"*, and a fresh staff press is allowed because
   `waiting_on` answers `None`. The consequence worth knowing: **a lapsed question leaves its
   `asked:` cell in the row** until the next hand-off overwrites it. It is inert, and the ticket
   card does not mention it.

4. ⚠️ **The asked wording lives in the confirm EMBED and is read back off it.** Following from 2
   and 3: the title and body staff typed have to survive a DM round-trip of up to a week and a
   restart, with no column to put them in. So the DM card carries them as two named fields, and
   **Yes** reads them back off `interaction.message.embeds[0]`; the ticket's **Make the event…**
   line carries the same card for the same reason. A member cannot edit a bot's embed, and this
   also makes it impossible to show them one thing and file another. A press whose card is missing
   answers *"no longer waiting"* rather than filing a blank.

5. **Ticket → event does not file an event on Yes; it hands staff the draft, as §A's own
   parenthesis says.** *"Yes files it (request or event draft handed to staff as above)"* cannot
   mean an event row, because `create_event` needs a `starts_at` and the member has not been asked
   for one. So Yes writes `yes:event`, posts the card into the ticket with **Make the event…**, and
   the trail (`event:<id>`, the log row, the `→ event #N` line) is written when the draft is
   SUBMITTED. The member's say-so and the date are two different questions for two different
   people.

6. **A hand-off's DM replaces the proposer's "Submitted on…" DM rather than joining it.** That DM
   is addressed to whoever proposed the event; on a hand-off that is the member, and they are
   already being sent the real sentence. Sending the staffer a *you proposed this* DM as well
   would have been the second message about one act. `submit_draft` skips it only when
   `from_request` or `from_ticket` is set.

7. **Event → request needed a new `CANCEL_WHY` word, `handed_off`.** §A says *"the existing cancel
   path + DM, reason text 'filed as request #N instead'"*, and the existing path is used
   unchanged — scheduled event, announcement edit, room notice, channel rename, DM. But
   `CANCEL_WHY_DEFAULT` reads *"either you or a member of staff called it off"*, which is untrue
   here; the note goes in the *"The reason given was:"* clause and cannot replace the sentence
   before it. The reason word is also what keeps the hand-off OUT of `ROOM_QUIET_REASONS`, so the
   room still hears the cancellation, which is §A's *"nothing else the cancel does changes"*.

8. **An event with no description files a request whose `why` reads *"(filed from event #N)"*.**
   `requests.why` is `NOT NULL` and the filing modal makes it required, so a description-less
   event would otherwise have written an empty string into the column whose whole job is to say
   why. It is the shape `ADOPTED_WHY` already uses for a hand-made forum post with no body.

9. **`moved` is a LOOK as well as a status, but it is NOT on `request_channel_moves`.** The card
   has to re-render on the post (colour, title, a **Now** field), so `moved` joins `LOOKS`,
   `EMBED_*` and `MOVE_LINE`. It is deliberately absent from `REQUEST_CARD_MOVES`: the hand-off
   writes ONE plain line, `→ event #N`, and a second card saying the same thing is the duplicate
   surface the docs standard warns about. `channel_moves`' no-key fallback had to drop it too
   (`CHANNEL_LOOKS`), or a server that never touched the key would have got both.

10. **`post_line` grew a `content=` keyword rather than gaining a second guarded sender.** It is
    the one place a request line meets the guard, the `request.notify_skipped_test_mode` row and
    the `request.notify_failed` row; it had only ever sent an embed because every caller had one.

11. ⚠️ **`black_bloc/handoff.py` imports the cogs INSIDE its functions.** `cogs/community/requests.py`
    imports `handoff` at module level for its refusal text, so a module-level `from .cogs…` here
    would close the circle. Every cog import in the module is function-local, which is the shape
    `black_bloc/modmail.py:ticket_label` already uses for `panels.option_label`. The pure half
    (vocabulary, clock, wording, refusals) has no such import and is what `tests/test_handoff.py`
    exercises without a bot.

12. **The trail's SITE half is two fields and two lines, not a new route.** §A asks for *"the
    site's request row shows moved → event #M with a link"* and the same on the events page.
    `moved_to` / `moved_word` join the existing `request_row` and `event_row` (and the mock's
    `askRow` / `eventRow`, and thirteen contract key lists); the requests page renders *Moved →
    event #12* with an **open it** link and the event card a **Now** line. ⚠️ **The link goes to
    the PAGE, not the row** — `events.html` has no per-event anchor to match `requests.html`'s
    `#r-<id>`, and a `#e-<id>` nothing renders would be a link that silently does nothing.

13. **`review_view` gained a keyword and a one-line factory rather than reading the store itself.**
    `submit_event` takes a one-argument view factory, so `handoff_review_view(bot, guild)` reads
    `handoff_mode` once and closes over it. The pure `review_view(event_id, *, handoff=False)`
    stays testable both ways with no fakes — the shape `door_buttons(open_with=…)` already uses.

14. **`open_a_ticket` gained `check_toggle: bool = True`.** §A says the request → ticket door is
    used *"regardless of that key … but say so"*. This is the saying so: one parameter, defaulting
    to today's behaviour, bypassed at exactly one call site. `modmail_open_with_button` still
    hides the `/modmail` root's own button, which is what it was asked for
    (`modmail-doors-design.md`, *Hide toggle (v117)*).

15. **`deliver_dm` / `ticket_dm` gained a `view`.** The confirm card's two buttons have to arrive
    in the DM and every other DM this cog sends is an embed. `**extra` keeps the call
    byte-identical when there is no view.

16. **`panel_card_buttons` computes Back's row instead of fixing it at 2.** Four moves plus two
    hand-offs plus Back is seven and Discord takes five to a row, so the moves keep their own row
    from `card_buttons` and Back goes one below the last one used. The panel is unchanged when the
    key is off.

17. **Two new ROUTINE log kinds beyond §A's "one row per hand-off".** `handoff.asked` and
    `handoff.refused` are not hand-offs — nothing moved — but a question sent to a member and a
    member's no are both things an auditor needs to see, and silence there would be the thing
    `logkinds`' classification tests exist to stop. The five `handoff.<from>_to_<to>` kinds are
    IMPORTANT and are still exactly one row each.

18. **The group-cap guard (§C) names the group that WOULD have been dropped**, rather than only
    counting. `test_the_settings_groups_fit_the_select` prints `sorted(found[SELECT_LIMIT:])` and
    points at `NAMESPACE_OVERRIDE`, so the next feature is told what to do as well as what broke.
    The existing `test_chat_is_the_only_group_over_the_cap…` is untouched: it asks a different
    question (which group needs **Find a setting…**).

### What was NOT verified

- **Nothing met Discord.** No boot, no token, no draft opened, no confirm DM sent, no button
  pressed in a client. `TEST_MODE` was never flipped and nothing was deployed. Every sweep row
  `ST-a`…`ST-k` in `../access/sweeps.md` is still unrun.
- **The migration was not run against a copy of the live database.**
  `tests/storage/test_db.py::test_a_schema_42_file_gains_the_three_moved_to_columns_all_empty`
  drops the three columns from a fresh file, rewinds `schema_version` to 42 and reconnects, which
  is the same ALTER through the same pattern — but the live file was not touched.
- **No `DynamicItem` has survived a real restart.** `PostHandoffButton`, `ConfirmDoor` and
  `MakeTheEventButton` are each rebuilt from their own custom id in a test, and a test asserts the
  two `request:` templates cannot match each other's ids — all with fakes.
- **No browser saw either page**, real or mock; the site half was exercised only by
  `node site/mock/check.mjs` and the ES-module parse.
- **The DM path is proved with a fake `send`.** A real member's DM privacy settings, and what
  Discord does to a view on a DM whose bot has been restarted, are both untested here.
- **`handoff_mode` ships ON**, so every surface changes the moment this merges. That is what the
  design asked for; it is named here because it is the one thing that is not behind a flip.

19. **Found after the fourth piece (`4af32c4`):** the `/modmail` panel's copy of the ticket card (`panel_card_buttons`) never knew about practice tickets, and `ticket_dm` returns `None` for a practice ticket — the same value a delivered DM returns — so a hand-off pressed there would have said *"@them has been asked by DM"* with nobody asked and written the `asked:` cell. `refusal_for_ticket` now answers in words on the MOVE, whichever button table drew it; a test pins it. Found by reading, not by a test.
