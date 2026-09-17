# The front door — one message and one command that route a member to a ticket, a request or an event

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **DESIGN, dispatching to Opus 2026-09-17 13:0x as
> branch `front-door`** (v124, behind `request-forum-adopt`). **Last verified: 2026-09-17 12:5x** against `main`
> `5e92e41`: the posted ticket button (`cogs/moderation/modmail.py` `TicketButton`, keys `modmail_panel_*`,
> `modmail_panel_follows_post`), the request modal (`cogs/community/requests.py` `FileButton`), the event draft
> (`cogs/community/events.py`, the **Propose** draft panel per `when-picker-design.md`), `bot.py:COGS`. ⚠️ Secret NAMES only.

## Owner asks, verbatim (2026-09-17, 12:4x–12:5x)

*"Request/event/modmail — All are pretty similar and confusing to separate as a user. How hard would it be to build a
filter to help sort them? Or maybe a staff button to redirect one of them to a different experience"* → the two
approaches (A: one front door; B: staff Send-to moves) → *"Explain to me how a works — How does a user start this
experience? With a slash command or would we put a button"* → both → *"Do it"*.

## A. What it is

One message the bot posts and keeps (like the ticket button), and one slash command, that show the same three
buttons. A press opens the EXISTING flow behind it — nothing new is built behind the buttons:

| Button (default label) | Opens | Today's code |
|---|---|---|
| **Ask staff privately** | the modmail ticket modal (two fields) → a ticket by the member's door | the posted `TicketButton`'s press path (`open_ticket_button`) |
| **Request something** | the request modal (what / why) → a request | `FileButton`'s press path |
| **Propose an event** | the event draft panel (day / time / where…) → a proposal in review | the `/event` **Propose** press path |

Each existing path keeps its own gates and refusals (member-visible or not, `request_who_can_file`, `events_mode`,
`modmail_member_command`…) — the door only routes; a refusal comes back in that feature's own words. The member
sees the three buttons whatever the gates say; a press that is refused answers in words and the door stays.

## B. The two entry points

1. **The posted message.** New cog `black_bloc/cogs/community/frontdoor.py` (pure half `black_bloc/frontdoor.py`),
   registered in `bot.py:COGS`. A persistent message with the three buttons as `DynamicItem`s (`door:<kind>`,
   registered at `cog_load`), posted / moved / taken down / re-posted-if-deleted the way the ticket button is —
   read that code and REUSE its reconcile shape (a shared helper in `black_bloc/posted.py` if it falls out cleanly;
   say so). It follows the welcome post the way the ticket button does (`frontdoor_follows_post`, default `welcome`).
   ⚠️ **One door per channel:** when the front door is posted in the channel the ticket button is in, the ticket
   button's message is taken down by the same reconcile (its keys keep their values; posting the door again
   re-takes it down) — key `frontdoor_replaces_ticket_button`, default **true**. Under `TEST_MODE` the door posts
   into the guard's channel exactly as the ticket button does today.
2. **The command.** `/ask` (member-visible, `NEVER_HIDDEN` while `frontdoor_mode` is on; hidden when off per the
   hide-when-off rule) → an ephemeral panel: the same title + text + three buttons. `/help` lists it with a guide link.

## C. Keys (registry + mock rows + labels; every one on the Settings page and `/settings` ▸ A setting group…)

| Key | Kind | Default | Help |
|---|---|---|---|
| `frontdoor_mode` | enum `off`/`on` | **on** | *"off hides /ask and takes the posted door down; on posts it where it is pointed and shows /ask"* |
| `frontdoor_channel_id` | channel | blank | *"where the front-door message is posted; blank posts nothing (the /ask command still works)"* |
| `frontdoor_message_id` | text | blank | (the posted message's id, written by the bot — TEXT, a snowflake does not survive a JavaScript number) |
| `frontdoor_title` | text | `Need something?` | *"the posted message's heading"* |
| `frontdoor_text` | text | `Pick the one that fits and Black Bloc takes it from there. Staff only see what you write.` | *"the line under the heading"* |
| `frontdoor_ticket_label` / `frontdoor_request_label` / `frontdoor_event_label` | text | `Ask staff privately` / `Request something` / `Propose an event` | the three button labels (≤ 80 chars, Discord's cap) |
| `frontdoor_follows_post` | text | `welcome` | *"the posts slug the door sits directly under; none = never re-post for that reason"* |
| `frontdoor_replaces_ticket_button` | bool | **true** | *"true takes the posted Open-a-ticket message down when the front door is posted in its channel — one door per channel"* |

A staff panel is NOT needed: the door's staff moves are on the **website** (a **Front door** card on `modmail.html`
or its own small page — pick the modmail page, beside the Ticket button card, so both doors sit together: post /
move / take down / preview) and the keys on the Settings page. `/ask` itself has no staff half.

## D. Tests (mirror the package)

`tests/test_frontdoor.py` (pure: labels, the embed text, the custom ids); `tests/cogs/community/test_frontdoor.py`:
posting / re-posting / taking down / following the welcome post; each press opens the right existing flow (assert
on the called opener, not a copy of its behaviour); a press when that feature refuses answers in that feature's
words; the ticket button is taken down when the door lands in its channel and the key is on; `/ask` hidden when
the mode is off; the dynamic items resolve from a regex match alone (restart). `tests/api/tools/test_frontdoor.py`
(or wherever the routes live): post / take down / preview for staff, refused in words for a member. Both orders.

## E. Docs

`code-notes.md`; this doc's `## Deviations`; `modmail-doors-design.md` (a note that the ticket button is one of the
door's three buttons now, checklist 35); a **member** guide `front-door` in `guides_seed.json` (three steps, IKEA
voice, picture slot on step 1 — the capture runbook shoots the posted message from the self-test, so the self-test
must post the door's card too: add it to the self-test's panel list); `/help` line; `docs/access/sweeps.md` rows
`FD-a…`; `architecture.md`'s cog count (20 → 21) and command count (30 → 31); `docs/info/README.md` row. NOT
`TODO.md` / `DONE.md` / `deploys.log`.

## Deviations

*(the build agent writes here what it had to do differently, dated)*
