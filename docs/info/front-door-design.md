# The front door — one message and one command that route a member to a ticket, a request or an event

> **Audience:** the build agent and reviewers. **Status:** TRACKED · ✅ **LIVE as v125** — merge `ae6eecb`, release `e8042a5`, deployed **2026-09-17 14:38** Phoenix; `frontdoor_channel_id` = #welcome since 14:38; sweeps **524–533** are the owner's. Was: ✅ BUILT on branch `front-door`, off `main` `0cee997` (v122); read the `## Deviations` foot before the sections above, thirteen
> things differ from what is written here. No schema change; registry **239 → 250**; mock **178 → 180 routes**;
> `pytest` **6196 → 6276**, both orders green. **Last verified: 2026-09-17 12:5x** against `main`
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
   re-takes it down) — key `frontdoor_replaces_ticket_button`, default **true**. ~~Under `TEST_MODE` the door posts
   into the guard's channel exactly as the ticket button does today.~~ ⚠️ **This sentence was wrong when
   it was written and is now true for a different reason.** At v125 the door under `TEST_MODE` wrote
   `frontdoor.would_post` and posted NOTHING (so did the ticket button). **Changed 2026-09-17 by the
   rehearsal home (v129, `info/rehearsal-home-design.md`):** while the guard refuses
   `frontdoor_channel_id` the door posts its REAL card into the rehearsal home (`shadow_channel_id`,
   blank = the guard's own channel) with one `rehearsal_note` line above it, remembered in
   `frontdoor_shadow_message_id` / `frontdoor_shadow_hash` and kept by the same reconcile — re-posted
   if deleted, edited when the wording changes, moved when the key moves, taken down when the mode goes
   off. `frontdoor.would_post` is left for the case with no rehearsal home at all.
2. **The command.** `/ask` (member-visible, `NEVER_HIDDEN` while `frontdoor_mode` is on; hidden when off per the
   hide-when-off rule) → an ephemeral panel: the same title + text + three buttons. `/help` lists it with a guide link.

## C. Keys (registry + mock rows + labels; every one on the Settings page and `/settings` ▸ A setting group…)

| Key | Kind | Default | Help |
|---|---|---|---|
| `frontdoor_mode` | enum `off`/`on` | **on** | *"off hides /ask and takes the posted door down; on posts it where it is pointed and shows /ask"* |
| `frontdoor_channel_id` | channel | blank | *"where the front-door message is posted; blank posts nothing (the /ask command still works)"* |
| `frontdoor_message_id` | text | blank | (the posted message's id, written by the bot — TEXT, a snowflake does not survive a JavaScript number) |
| `frontdoor_shadow_message_id` | text | blank | **added v129** — the rehearsal copy's id, written by the bot |
| `frontdoor_shadow_hash` | text | blank | **added v129** — what that copy is showing, so a sweep edits it only when something drawn has changed |
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

> Written by the build, **2026-09-17**, on branch `front-door` off `main` `0cee997` (v122).
> Everything below is a place the build did NOT do what §A–§E said, and why. ⚠️ **Nothing here
> has met Discord**: no boot, no token, no button pressed in a client, no DM, no deploy, and
> `TEST_MODE` was never flipped. The whole verification is `pytest -n auto` (**6196 → 6276**,
> forward and under `BB_REVERSE=1`), `ruff check .`, the ES-module parse of all 32
> `site/public/assets/*.js`, `node site/mock/check.mjs` (*19 pages, 180 routes, 15 core
> settings, all keys present*), `node site/mock/discordmd.test.mjs`, `node site/mock/labels.test.mjs`,
> and one pass over the **Front door** card on the MOCK in a browser.

1. ⚠️ **The event button on the POSTED door opens a one-button private card first, not the
   draft.** §A says each press opens the existing flow. It does — but `ProposeButton.callback`
   reaches `open_draft` → `panels.opened` → `interaction.response.defer()`, which for a component
   press is `deferred_message_update`, so `render_draft`'s `edit_original_response` edits **the
   message the button sits on**. On the ephemeral `/ask` panel that is exactly right: the panel
   becomes the draft, as it does on `/event`. On the public posted message it would draw one
   member's half-filled event draft over the front door, for the whole channel. So the posted
   **Propose an event** answers with an ephemeral `EventHandoff` card carrying the real
   `ProposeButton`, and the draft opens over THAT. One extra press, on one of three buttons, on
   one of two faces. The ticket and request doors need no such thing because a modal is already
   private. Not a decision the design could have known: it is a fact about `discord.py` 2.7.1.

2. **`frontdoor_panel_minutes` is an eleventh key.** §C's table names ten. `panels.Panel`
   takes a timeout, and KI-20 is the reason all eighteen panels own one at **10** rather than
   sharing: fifteen or more silently loses the "this panel has gone quiet" footer. Reusing
   `modmail_panel_minutes` would make one number govern two panels.

3. ⚠️ **The eleven keys are filed under the `modmail` namespace, not a `frontdoor` one — and
   the reason is a latent bug this build nearly shipped.** `settings_panel.groups()` was at
   **exactly 25** and `cogs/core.py:GroupPick` builds its select from `sp.groups()[:
   sp.SELECT_LIMIT]`, Discord's own hard cap. A 26th group would have silently dropped
   **`youtube`** off `/settings` ▸ **A setting group…** — every youtube key unreachable from
   Discord, with nothing anywhere to say so. `NAMESPACE_OVERRIDE` instead: no new group, the
   keys sit with the ticket button's (which is where the website card is and where the log
   kinds head), and `modmail` becomes the second group over 25, which is what **Find a
   setting…** exists for. ⚠️ **The cap itself is still unguarded for the NEXT feature** —
   `tests/test_settings_panel.py::test_chat_is_the_only_group_over_the_cap…` was widened to
   `["chat", "modmail"]`, but nothing yet asserts `len(groups()) <= SELECT_LIMIT`. Worth a
   `KNOWN_ISSUES` entry or a one-line guard in the next build that touches `settings_panel`.

4. **`HEADS["frontdoor"] = "modmail"`, so the door is not a `FEATURES` entry.** A feature of
   its own would mean a `frontdoor_log_level` key, a `FEATURE_PAGES` row and a Logs-page filter
   for three buttons. `modmail_log_level` governs the door's rows and they land on the Modmail
   page beside the ticket button's, which is where §C puts the card.

5. **§A's table names `open_ticket_button` as the ticket door's press path; the real one is
   `open_ticket_modal`.** `open_ticket_button` is the STAFF sub-panel that posts the ticket
   button. `TicketButton.on_click` calls `open_ticket_modal(interaction)`, and so does the
   front door — with `previous=None`, because the one caller that passes a view
   (`MoveButton(TICKET_OPEN)`) makes `run_open_ticket` redraw the **modmail** root over
   whatever raised it. A ticket opened through either face of the door therefore stores
   `source = panel`, which is true of both.

6. **The one-door-per-channel takedown clears `modmail_panel_message_id` and needs two lines
   inside `Modmail._repanel`.** §B says the ticket button's keys keep their values and the
   door's reconcile takes it down. Both halves are true, but modmail's own five-minute sweep
   would re-post the button within five minutes of every takedown — the two reconcilers would
   alternate forever, posting and deleting a message in a real channel. `_repanel` now returns
   early while `frontdoor.door_takes_over(store, guild_id)` names its channel. The CHANNEL key
   is left alone, so moving the door away or taking it down makes `door_takes_over` answer
   `None`, `_repanel` stops returning early, finds a channel with no message, and posts the
   button back on its own next sweep. Nothing new is stored to make that reversible.

7. **`black_bloc/posted.py` DID fall out cleanly, as §B hoped.** Three helpers —
   `message_is_there`, `drop_message`, `overtaken_by` — with modmail's `panel_is_there`,
   `drop_panel_message` and `post_below_button` now one-line delegates keeping their names and
   signatures, so no existing caller or test moved. `drop_message` takes the shadow kind as
   `would_kind` (the caller owns its own log vocabulary) and now **returns a bool**, which is
   what stops `hide_ticket_button` clearing a key while the guard has refused the delete.

8. **No `preview` route.** §C asks the website card for post / move / take down / **preview**.
   The preview is drawn client-side from the stored wording — heading, line and the three
   labels as disabled buttons — so it needs no round trip and cannot disagree with what the
   bot would post, because both read the same keys. Two routes, not three.

9. **The website card is on the Modmail page as §C's own second thought asks**, in a section
   renamed **Doors** (was *Ticket button*) holding the front door, the ticket button and the
   ticket forum. Both doors sit together, which is the reason §C gave for picking that page.

10. ⚠️ **`site/mock/server.mjs` keeps its own copy of `NAMESPACE_OVERRIDE`, and nothing
    compared it to the registry's.** Found in a browser, not by a test: the eleven keys drew a
    **Front door** group on the mock Settings page while the real API files them under modmail.
    The mock now carries the same table and
    `tests/api/test_contract.py::test_the_mock_groups_a_key_the_way_the_registry_does` fails
    the next time one drifts.

11. **The self-test posts the door's card as `panel.ask`** (§E asks for it so the capture
    runbook can shoot the posted message). `PANELS` is **18 → 19** and the check is built from
    the same `build_panel` the command calls, never a copy.

12. **`/help` needed no line.** It is generated from the command tree, so `/ask` appeared by
    itself; the guide link comes from the `front-door` guide's own `command` field. The
    `personas.py` member-command block is hand-written and DID need one — that file is what the
    conversational model reads, and `tests/test_personas.py` fails when a member command is
    missing from it.

13. **`docs/TODO.md`, `docs/DONE.md` and `docs/deploys.log` were not touched**, as the brief
    said. The 🔀 TRIAGE item and the landing entry are the conductor's.

### What was NOT verified

- **Nothing met Discord.** No boot, no token, no press in a client, no modal submitted, no
  message posted or deleted in a real channel. Every button, sweep and takedown is proved
  against fakes.
- **The posted door has never survived a real restart.** `DoorButton` is registered in
  `cog_load` and rebuilt from a regex match in a test; no gateway has re-delivered a press.
- **The ticket-button takeover has never run beside the real modmail cog on a live bot** —
  the test drives `Modmail._repanel` directly with the same fakes.
- **No browser saw the real site**, only `site/mock` at `127.0.0.1:8788`, signed in as staff.
  The card's *posted* state (**It is in #…** plus **Move** / **Take it down**) was **not**
  seen in the browser: the mock refuses every panel post while its guard is on, and a
  guard-off write did not survive the page's own reseed. That state is proved by
  `tests/api/tools/test_frontdoor.py` only.
- **The guide's picture slot is empty** — `front-door` is seeded with no screenshot, which
  reads exactly like a freshly re-shot one (`access/guides-capture.md` §1, the `count: 0`
  trap). The capture runbook's first-population pass is what fills it.
- **No migration was needed and none was run** — eleven registry keys, no schema change.
