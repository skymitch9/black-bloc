# The front door — one message and one command that route a member to a ticket, a request or an event

> **Audience:** the build agent and reviewers. **Status:** TRACKED · ✅ **SHADOW MODE + THE RECONCILE LOCK LIVE as v141** — merge `d6c271d`,
> release `2e48d7c`, deployed **2026-09-18 16:55** Phoenix; sweeps **616–620** are the owner's (619 = the cutover); verified: boot clean at 16:55:30 (no reconcile posted anything — the door's channel was still blank), /health ready; the shadow flip itself (frontdoor_mode → shadow, frontdoor_channel_id → #welcome) was set on the settings API right after and checked by token — see the TODO's next line. Was: 🔨 built on
> branch `frontdoor-shadow` off `main` `58fb7d6`. Read [`## Shadow mode (2026-09-18)`](#shadow-mode-2026-09-18) and its own Deviations block
> before the sections above: `frontdoor_mode` now takes **off / shadow / on**. Deviation **14** (the boot double-post of 2026-09-18 16:08, fixed on `boot-reconcile-once`) is merged beside it. `pytest -n 8` **6720 → 6740 passed**
> (3 skipped), both orders; registry unchanged at **262** keys — a third enum word, not a twelfth key; no schema
> change; mock unchanged at **20 pages / 186 routes**. Before that: ✅ **LIVE as v125** — merge `ae6eecb`, release
> `e8042a5`, deployed **2026-09-17 14:38** Phoenix; `frontdoor_channel_id` = #welcome since 14:38; sweeps
> **524–533** are the owner's. Was: ✅ BUILT on branch `front-door`, off `main` `0cee997` (v122); read the `## Deviations` foot before the sections above, thirteen
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
| `frontdoor_mode` | ~~enum `off`/`on`~~ → **enum `off`/`shadow`/`on`** (2026-09-18, [`## Shadow mode`](#shadow-mode-2026-09-18)) | **on** | *"off hides /ask and takes the door down; shadow posts the rehearsal copy into shadow_channel_id with the rehearsal note and nothing into the real channel; on posts it where it is pointed"* |
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

## Shadow mode (2026-09-18)

> Built on branch `frontdoor-shadow` off `main` `58fb7d6` (**v139 live**), the afternoon
> `TEST_MODE` was lifted. ⚠️ **Not merged, not deployed, no key flipped, and nothing below has
> met Discord** — no boot, no token, no message posted or deleted in a real channel, no button
> pressed in a client. The whole verification is `pytest -n 8` (**6720 → 6740 passed**, 3
> skipped, forward and under `BB_REVERSE=1`), `ruff check .`, `node --check` over every
> `site/public/assets/*.js` and `site/mock/*.mjs`, `node site/mock/check.mjs` (*20 pages, 186
> routes, 24 core settings, all keys present*), `node site/mock/discordmd.test.mjs` and
> `node site/mock/labels.test.mjs`.

### Owner ask, verbatim (2026-09-18 16:1x)

A minute after the `TEST_MODE` lift (16:08) reconciled the real door into `#welcome`:
*"okay now that we're in live shadow mode is even more important, i dont want it to post in
welcome yet"* → *"lets have that in shadow mode"*.

The conductor cleared `frontdoor_channel_id` and `modmail_panel_channel_id` by hand and deleted
both posted messages; after this ships he sets `frontdoor_mode` = **shadow** and points
`frontdoor_channel_id` back at `#welcome`.

### S1. What the mode means

`frontdoor_mode` is `enum` **off / shadow / on**, default still **on**. Help text:
*"off hides /ask and takes the door down; shadow posts the rehearsal copy into
shadow_channel_id with the rehearsal note and nothing into the real channel; on posts it where
it is pointed."*

| | the real door (`frontdoor_channel_id`) | the rehearsal copy (`shadow_channel_id`) | `/ask` | the ticket button |
|---|---|---|---|---|
| **off** | taken down, both keys cleared | taken down | hidden (`HIDDEN_WHEN_OFF`) | its own rules |
| **shadow** | taken down if one is up — `frontdoor.taken_down`, only `frontdoor_message_id` cleared | posted and kept current, `rehearsal_note` on top naming the real channel | answers | follows the door while `frontdoor_replaces_ticket_button` |
| **on** | posted / moved / re-posted as before | taken down — `frontdoor.taken_down_shadow` | answers | its own rules (one door per channel) |

`frontdoor_channel_id` survives shadow on purpose: it is where the door is **AIMED**, it is what
the rehearsal note names, and it is what the flip to **on** posts into with no second step.

### S2. Where the decision lives

Three predicates in the pure half, one branch each in the two cogs — nothing restructured, so the
concurrent `boot-reconcile-once` branch (which wraps `reconcile()` in a lock helper) merges
textually:

| Pure (`black_bloc/frontdoor.py`) | Answers |
|---|---|
| `door_mode(store, guild_id)` | `off` / `shadow` / `on`; anything unknown reads as **off** |
| `door_is_on(...)` | the mode is **not off** — the feature switch, not the where. Shadow is on, somewhere else |
| `door_rehearses(...)` | the mode is **shadow** |
| `panel_follows_the_door(...)` | shadow **and** `frontdoor_replaces_ticket_button` — the ticket button's mode, derived, never stored |
| `door_takes_over(...)` | in shadow it answers the AIMED channel even with no message up: nothing of Black Bloc's goes in the real channel while the door rehearses |

The posting decision itself is one line in each of four places —
`frontdoor.post_door`, `FrontDoor._redoor`, `modmail.post_ticket_panel` and `Modmail._repanel` —
reading `door_rehearses(...) or (guard refuses the channel)` where each read the guard alone.
Everything behind that branch is the **existing** `TEST_MODE` rehearsal path, unchanged:
`rehearse_door`, `frontdoor_shadow_message_id`, `frontdoor_shadow_hash`, `shadow.channel_id`,
`shadow.find_copy`, `rehearsal_note`.

`start_rehearsing(bot, guild)` is the only new move: `lower_the_real_door` (drop the message,
clear `frontdoor_message_id`, log `frontdoor.taken_down` with `rehearsal: true`) followed by
`hide_ticket_button`. Coming back out of shadow needs nothing new — `_redoor`'s non-guarded
branch already calls `drop_rehearsal` and posts the real door.

### S3. Saying it in words

- **`/ask`** carries the sentence as an embed **footer**, and only for a staffer
  (`store.is_staff(actor)`): *"shadow — the door is rehearsing in #welcome-test; nothing is in
  #welcome."* A member sees the card exactly as before.
- **The Modmail page's Front door card** says the same thing, from the same three values.
- ⚠️ **These sentences are NOT settings keys**, and that is the rule rather than an exception to
  it: *every word the bot POSTS is editable on the site*. This one is never posted — it is a
  status line on an ephemeral staff panel and on a dashboard card, the same call
  `rehearsal-home-design.md` deviation 7 made for `posts.shadow_words`. The one line that IS
  posted, `rehearsal_note`, was already a key and is untouched.

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

14. ⚠️ **THE DOOR POSTED ITSELF TWICE AT THE LIFT — the boot runs THREE reconciles, and two of
    them raced** (incident 2026-09-18 16:08 Phoenix, fixed on branch `boot-reconcile-once`,
    commit `23b3994`). §D says the sweep puts a deleted door back; it does not say how many
    sweeps a boot starts. It starts three: `cog_load` runs `reconcile()` and then
    `_reconcile_loop.start()`, `on_ready` runs `reconcile()` again, and the loop's own first
    tick (after `loops.wait_ready`) is a third. **Measured on the live bot one second after the
    boot that followed the TEST_MODE lift** — `action_log` holds `modmail.panel_posted` at
    **23:08:28.110Z** (message `1550644707204407368`) and again at **23:08:28.589Z**
    (`1550644708227944461`), `frontdoor.posted` at **23:08:28.529Z** (`1550644709138108427`) and
    again at **23:08:29.352Z** (`1550644711646302299`), and exactly one
    `frontdoor.ticket_button_hidden`, for the FIRST button only. Result in `#welcome`: **two
    front doors and one orphaned ticket button**, which the conductor deleted by hand. Two
    reconciles were in flight at once, both read *"no posted message id"* before either had
    written one, and both posted. The re-read in `_redoor` was never wrong — it was simply not
    inside anything that made it happen after the other run's write.

    The fix is `black_bloc/loops.py:Reconciler`, beside `wait_ready` because it is the same
    kind of thing (a rule about how a loop behaves, one home, one copy): **one `asyncio.Lock`
    per cog**, the reconcile's state read happening INSIDE it, and a **60-second window**
    (`loops.RECENT_SECONDS`) that `on_ready` skips on. The loop's tick never skips — it is the
    sweep, and a sweep that can be talked out of running is not a sweep. `FrontDoor.reconcile`,
    `Modmail.reconcile_tickets` and `Events.reconcile_events` are now thin locked wrappers over
    a `_sweep`; `on_post_published` takes the same lock with `stamp=False`, because re-posting
    one guild's door is not a full sweep and must not close the window on one.

    The same race, in the same shape, was writing **two `event.room_forgotten` rows** for one
    event at boot (`TODO.md`'s own item) — two reconciles both read the row while its
    `review_channel_id` was still set. The lock fixes it for free, because the DB read moved
    inside the lock with everything else.

    ⚠️ **The guard that would have caught it anyway.** Before a reconcile posts, it now reads
    the room's last **five minutes** for another of the bot's own messages wearing the same
    custom-id family (`posted.duplicates_near`; `door:` for the front door,
    `modmail:ticket:<guild>` for the ticket button). If it finds one, it does **not** post a
    third: it writes one IMPORTANT `frontdoor.duplicate_seen` / `modmail.panel_duplicate_seen`
    row naming the stored id and every other id, and leaves both messages where they are.
    **It never deletes** — staff have the final say on what comes down (`CLAUDE.md`). The check
    costs one `channel.history` call and only on the rare path where something is about to be
    posted, never on the sweep that finds its door where it left it. It is deliberately
    **blind to a duplicate sitting beside a healthy door**: that path returns before the check,
    and paying for a history read every five minutes per guild to find a state the lock now
    prevents was not worth it.

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

### Deviations — the shadow-mode build (2026-09-18, branch `frontdoor-shadow`)

> Written by the Opus build off `main` `58fb7d6` (v139 live). Every line is a place the build did
> NOT do what the brief said, and why. The thirteen numbered deviations above belong to the
> ORIGINAL v125 build and are unchanged.

S1. ⚠️ **In shadow with `frontdoor_replaces_ticket_button` TRUE, the ticket button's own rehearsal
    copy is NOT posted — it comes down in the rehearsal home too.** The brief said *"its rehearsal
    copy (`modmail_panel_shadow_*`) is kept in the shadow home under the door's copy"*. That
    contradicts what is already shipped and deliberate: `rehearsal-home-design.md` §C says the door
    takes the button down **in the same channel**, "so in the rehearsal home the mods see exactly
    what `#welcome` will show: the rules post, then the front door under it". The rehearsal home IS
    that same channel — both copies land there — so `rehearsal_takes_over` / `hide_rehearsed_ticket_button`
    already remove the button's copy whenever the door's copy is up. Posting it anyway would have
    made the rehearsal show something `#welcome` never will, and the door's own **Ask staff
    privately** button IS the ticket door. With the key **false** nothing follows the door at all
    and the button keeps its own rules, which is what the brief's own gating says. Net: in shadow
    the mods review ONE message, the door.

S2. ⚠️ **The ticket button follows the door whatever channel it is in, not only the door's.**
    `hide_ticket_button` used to return early unless `door_takes_over(...) == the button's channel`
    (one door per **channel**). Under `panel_follows_the_door` that check is skipped, so a ticket
    button aimed at `#help` also comes down while the door rehearses. The owner's sentence is
    *"i dont want it to post in welcome yet"*, and a build that left a live **Open a ticket** button
    in a second public channel would be reading the letter of "one door per channel" against its
    point. `modmail_panel_channel_id` keeps its value, so the flip to **on** puts it back within
    five minutes, exactly as moving the door away does today.

S3. **No new refusal CODE — the homeless refusal is still `code="test_mode"`, with a new message.**
    `rehearse_door` returns `refusal(DOOR_NO_HOME if rehearsing else DOOR_GUARDED, "test_mode", 409)`.
    The code is an internal routing token read in two places (`post_door` and `_redoor`, to write
    `frontdoor.would_post` once per guild); changing it would have touched both plus their tests for
    no gain a person can see. ⚠️ **The word is wrong now** — in shadow with nowhere to rehearse,
    nothing is in test mode. The message a person reads is right (`DOOR_NO_HOME` names
    `shadow_channel_id` and says nothing about test mode); only the token lies. Worth renaming to
    `no_rehearsal_home` in the next build that touches this file.

S4. **A blank `frontdoor_channel_id` in shadow rehearses NOTHING, as it posts nothing when on.**
    `_redoor` still returns early with no channel stored. So the conductor's two steps after the
    deploy are both needed and in either order: set the mode to shadow, point the channel at
    `#welcome`. The staff sentence covers the in-between state in words (*"It has no channel of its
    own yet"*) rather than leaving it silent.

S5. **`door_is_on` changed MEANING rather than gaining a sibling.** It now answers "the mode is not
    off" — so shadow is on, somewhere else. Every one of its four call sites wants exactly that
    (`/ask` answers, a press on the copy opens the real flow, the sweep does not take the door down,
    `door_takes_over` still applies). A `door_is_live` beside it would have been two names for one
    question and a fifth place to forget. Its three existing assertions in `tests/test_frontdoor.py`
    still pass unchanged.

S6. **The staff line is an embed FOOTER on `/ask`, not a field or a second message.** A field would
    sit between the heading and the buttons on a card a member also sees, and the panel is already
    the one card both faces wear (`build_panel`). The footer is drawn only when `store.is_staff`
    answers true, and `door_hash` does not cover it — the posted copy is built by `door_embed`
    directly, so no footer can ever reach a real channel or drift the fingerprint.

S7. **The site reads `shadow_channel_id || log_channel_id` for the home it names.** The bot's chain
    is `shadow_channel_id` → the guard's test channel → `log_channel_id` (`black_bloc/shadow.py`),
    and with `TEST_MODE` lifted the middle link is gone. The card therefore agrees with the bot in
    every configuration that exists today. ⚠️ If `TEST_MODE` is ever turned back on, the card could
    name the log channel while the bot rehearses in the test channel — one line in
    `page-modmail.js:panelSettings` if that ever matters.

S8. **`docs/TODO.md`, `docs/DONE.md`, `docs/deploys.log` and `docs/KNOWN_ISSUES.md` were not
    touched**, as the brief said. The landing entry and the triage item are the conductor's.
**Deviation 14 (2026-09-18, `boot-reconcile-once`) adds its own NOT-verified list:**

- **The race is proved against fakes, not against a boot.** Both concurrency tests gather two
  reconciles on a channel whose `send` yields first, and both FAIL (two `frontdoor.posted`
  rows, two `modmail.panel_posted` rows) when the lock is taken out — measured by running them
  against `_sweep` directly. **No bot was booted**, no gateway delivered `on_ready`, and the
  three-reconcile boot sequence has never been watched end to end outside a test.
- **The duplicate guard has never read a real `channel.history`.** `FakeText` cannot list its
  own messages, so the two tests that exercise it attach a history of their own. The shape of
  `message.components[*].children[*].custom_id` is taken from discord.py, not from a fetched
  message, and **every failure inside `duplicates_near` is swallowed and read as "no
  duplicates"** — so on a real channel the guard fails OPEN, back to the lock.
- **The 60-second window is a constant nobody has tuned.** It exists to stop `on_ready` from
  repeating `cog_load`'s work at boot, which takes milliseconds; a gateway RESUME an hour later
  runs the reconcile as normal.
- **Nothing was merged or deployed**, and the two orphan messages the incident left were
  removed by the conductor by hand before this branch existed.
