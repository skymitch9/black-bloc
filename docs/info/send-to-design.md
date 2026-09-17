# Send to… — a staff move that turns a request into an event, an event into a request, and a ticket into either with the member's say-so

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **DESIGN, dispatching to Opus 2026-09-17 14:5x as
> branch `send-to`** (v127). **Last verified: 2026-09-17 14:52** against `main` `9ef0dc5`: `requests.create_request(guild,
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

*(the build agent writes here what it had to do differently, dated)*
