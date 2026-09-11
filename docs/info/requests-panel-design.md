# Requests, fourth pass — `/request` is ONE command that opens a panel

**Audience:** the builder and the reviewer. **Status:** TRACKED · ✅ **SHIPPED — merge
`ba5cb99` (build `4743b01`, review fixes `79548c1`), deployed 2026-09-03; see `deploys.log`.**
172 new/rewritten tests
(`tests/cogs/community/test_requests.py` 51, `tests/test_requests.py` +26 pure-helper and
`withdraw_request` tests, `tests/test_settings_store.py` +1), then **17 more** for the
three review findings (`79548c1`); **3338 tests pass** (3321 before the review fixes), ruff
clean, `check.mjs` 17 pages / 139 routes, `labels.js` still parses (site untouched). Since
then, **deviation 12** (branch `feat/requests-panel-own-list`, ✅ **merged and live** — the
*fifth pass*, [`../DONE.md`](../DONE.md) *"Requests, fifth pass"*, commits `dd7c788` code /
`bda45da` docs): the
owner's *"We need to make the view request thing staff only"* — a member no longer sees
their own requests written out on the panel unless the new `request_panel_own_list` is on
(default off); **3345 tests pass**. See
`## Deviations` at the foot — 9, 10 and 11 are the reviewer's findings and what changed, 12
is the owner's change after deploy. Owner's ask ~06:50 (verbatim in `../TODO.md`, "🔧 Open
engineering items"): *"The flow
seems tough, and request set and request ready seem overlapping."* → *"Let's also have
/request open a menu maybe. Let's try and minimize slash commands and maximize interactive
windows"* → *"Let's start this process with request then carry it through the rest of the
app. Request first."* ⚠️ This is
the PATTERN for every later feature — see the project `CLAUDE.md` rule.

> ⚠️ **Since then — three things this document describes have moved on.** The design body is the
> fourth pass; read these beside it:
> - **The card's `review` row gained a fifth button, `Ask them to check`** (sixth pass, v61, merge
>   `44170f4`) — [`requests-check-design.md`](requests-check-design.md). The live
>   `requests.CARD_BUTTONS` is `open` → Pick up / Hold / Decline; `in_progress` → Ready to check /
>   Hold / Decline; `review` → **Accept / Ask them to check / Send back / Hold / Decline**; `hold` →
>   Resume / Decline; `done` / `declined` / `withdrawn` → empty. So the button table in *The request
>   card* below is the fourth-pass version.
> - **The panel machinery was extracted into `black_bloc/panels.py`** at panels wave 0 (2026-09-03,
>   [`panels-program.md`](panels-program.md)). `still_staff`, `retire`, `capped_placeholder`,
>   `panel_minutes`, `confirm` / `confirm_items` and the `Panel` base with its `last_interaction`
>   footer fallback all live there now, not in the requests cog; `RequestView` is a `Panel`
>   subclass. Deviations 9, 10 and 11 describe where those mechanisms were INVENTED — this cog —
>   and they are still the reason each exists.
> - **The slash tree shrank a long way past deviation 7's 44.** There are **29** top-level commands
>   and **29** leaves at v108 — no Groups at all (the `/settings` panel, v83/v84, retired the last
>   one).
>
> **Last verified: 2026-09-11 09:00** (the header; the body is as at the build). Measured this pass
> against `main` at `f3ae743` (v108 live): `requests.PANEL_MINUTES_KEY = "request_panel_minutes"`
> and `PANEL_OWN_LIST_KEY = "request_panel_own_list"` are both exported and both registered in
> `settings_store.py` (`KEY_TYPES` + `KEY_HELP`); `requests.panel_shows_own_list` and
> `withdraw_request` exist; `cogs/community/requests.py:build_panel` and `class RequestView(Panel)`
> exist and the cog imports `still_staff` / `retire` from `panels.py`; `CARD_BUTTONS` is the
> five-row table quoted above; KI-20 is still **WATCHING** in
> [`../KNOWN_ISSUES.md`](../KNOWN_ISSUES.md). ⚠️ **NOT verified:**
> anything against live Discord or a browser — this pass cannot reach it; a member gate, staff gate,
> component defer, or modal-from-component flow that only real Discord's dispatch would
> distinguish (`code-notes.md` says exactly which lines were checked against installed
> library source instead). Before that, **2026-09-03** against `black_bloc/requests.py` and
> `cogs/community/requests.py` at `3e18e4a` (the third pass, deployed `70a6720`).

## What is wrong today (measured)

`/request` is a group of TEN subcommands (`cogs/community/requests.py:482–784`): `create`,
`list`, `withdraw`, `set`, `ready`, `accept`, `sendback`, `hold`, `resume`, `logs`. `set`
offers every reachable status from a menu (`STAFF_STATUSES` = declined, done, hold,
in_progress, review), so four moves have two spellings: `set review` / `ready`, `set done` /
`accept`, `set hold` / `hold`, `set in_progress` (from review) / `sendback`. `set review`
cannot collect built + how-to-test, so it refuses where `ready` succeeds — the overlap is
also a trap.

## The design — one command, one panel

**`/request` is a single slash command, no subcommands.** (discord.py: a `Group` and a
command cannot share a name — the group goes; `commands synced` drops by nine.) It answers
with ONE ephemeral message: an embed plus a `discord.ui.View`. Everything the ten
subcommands did is a button, a select or a modal on that message. Members and staff get
different panels from the same command.

### The member panel (anybody)

- **Embed** "Requests": one line saying what the panel is, then the caller's own requests
  (`list_requests(user_id=caller)`, newest first, `summary_line` each, at most `LIST_PAGE`);
  "You have not asked for anything yet" when empty. Colour: `EMBED_COLOURS[FILED_LOOK]`.
  ⚠️ **The own-requests half is superseded by deviation 12** — a member sees those lines
  only when `request_panel_own_list` is on (default off); staff always see theirs.
- **Row 0 buttons:** `File a request` → the existing `RequestModal` (unchanged). `Refresh` →
  re-render. `Open on the site` → the existing `site_view` link (only when a site origin is
  configured, as today).
- **Row 1, only when the caller has a withdrawable request (`WITHDRAWABLE`):** a Select
  "Take one back…" listing them (`#id · what`); choosing one re-renders with the card and two
  buttons `Yes, take it back` / `Keep it`. Confirm calls the SAME code `withdraw` runs today
  (extract it into `withdraw_request(bot, guild, row, actor)` in `requests.py` — the cog
  path and the site path both call it; one canonical implementation).
- Gates unchanged: requests off → `REQUESTS_OFF`; database down → `DB_UNAVAILABLE`; filing
  when `everyone_may_file` is off and the caller is not staff → the modal button is NOT
  rendered and the embed says filing is for staff (never a dead button, never a bare refusal).

### The staff panel (`store.is_staff`)

The member panel plus:

- **Embed** adds a counts line — open / being worked on / ready to check / on hold — from
  `count_requests`.
- **Row 2 Select "Pick a request…":** every request in `OPEN_STATUSES`, newest first,
  **capped at 25** (Discord's option cap). Option label `#id · <STATUS_WORDS> · <what
  clamped to fit 100 chars>`. When more than 25 exist the placeholder says "25 of N — the
  rest are on the site". No open requests → the select is not rendered; the embed says so.
- **Row 3 button `Logs`** → the last ten request log lines, exactly what `/request logs`
  shows today, as a NEW ephemeral message (followup), so the panel stays.

### The request card (staff picked one)

The panel re-renders in place (`interaction.response.edit_message`) as:

- **Embed:** `request_embed(row, move=<look for the row's status>, origin, guild)` — the
  same builder and the same seven looks the channel gets; the look for a status is the
  status itself except `open → FILED_LOOK`. A card on the panel and a card in the channel
  must never be two shapes.
- **Buttons — ONLY the moves valid from the row's status**, computed from
  `moves_from(status)` plus the guards the shared functions apply, so the panel never
  offers a move the function would refuse:

  | Row status | Buttons rendered |
  |---|---|
  | `open` | `Pick up` (→ in_progress) · `Hold` (modal) · `Decline` (modal) |
  | `in_progress` | `Ready to check` (→ `ReadyModal`) · `Hold` · `Decline` |
  | `review` | `Accept` (→ done; NOT rendered when `may_accept` says this staffer may not, the embed footer says who may) · `Send back` (modal, note required) · `Hold` · `Decline` — ⚠️ **plus `Ask them to check` between Accept and Send back since v61** |
  | `hold` | `Resume` (→ `resume_target(row)`) · `Decline` |
  | `done` / `declined` / `withdrawn` | no move buttons; the card says it is final (`NO_MOVES_LEFT`) |

  Plus `Back` (to the staff panel) on every card. Button styles: the forward move is
  `primary`, `Accept` is `success`, `Decline` is `danger`, the rest `secondary`.
- **Every move calls the shared function that exists today, `via` left at its Discord
  default:** `apply_decision` (pick up, hold, decline), `mark_ready`, `accept`, `send_back`,
  `resume_request`. The panel never writes a row or logs a line itself — one canonical
  path, one log row (checklist 34). After a move the card re-renders with the new state and
  the sentence the function returned goes in the embed footer or a one-line followup.
- **Modals** (all `AnswersErrors` + `discord.ui.Modal`, one shared shape): `ReadyModal`
  (exists), `NoteModal(kind)` for send back / hold / decline with one paragraph field whose
  label names what the note is for and who is sent it (the requester for hold/decline, the
  person who marked it ready for send back). `reason` required, as the functions require.

### Lifetime

`View(timeout=<request_panel_minutes> * 60)`; on timeout every item is disabled and the
embed footer says "This panel has gone quiet — run /request again". The panel is ephemeral
and not persistent: after a bot restart its buttons answer "This interaction failed" from
Discord — accepted, the panel is a moment, not a post (a `KNOWN_ISSUES` entry, WATCHING,
"what would change it: a persistent `DynamicItem` panel if staff ask").

### Settings (checklist 33 — every decision configurable both ways)

**Two** keys in `settings_store.py`, each with a registry type, help text and a `default()`
branch, so both reach the Settings page and `/settings set-value` like every key:

| Key | Type | Default | What it decides |
|---|---|---|---|
| `request_panel_minutes` | `int` | **10** | how long the panel stays live. 15 as first built, lowered by review finding F2 / deviation 10, because the "gone quiet" footer can only be written while Discord's 15-minute interaction token is still valid |
| `request_panel_own_list` | `bool` | **False** | whether a MEMBER sees their own requests written out on the panel. Staff always see theirs. Added by deviation 12 (the owner's "make the view request thing staff only", after deploy); on, the panel is exactly what shipped in `ba5cb99` |

Nothing else here is a decision: the 25-option cap is Discord's, the button table is the
state machine.

### What goes away

The nine subcommands. `/help` reads the tree (`cogs/core.py:88`), so it follows. Every doc
that names `/request list|set|ready|accept|sendback|hold|resume|withdraw|logs|create`
(measured: `access/OWNER_GUIDE.md`, `access/sweeps.md`, `info/feature-list.md`,
`info/phase13-design.md`, `info/phase8b-design.md`, `info/requests-embeds-design.md`,
`info/requests-states-design.md`, `info/code-notes.md`) is rewritten in the same commit —
the design docs get a dated "superseded by the panel" line, not a rewrite of history.

## Tests (mirror the package)

- `tests/cogs/community/test_requests.py` — the cog: `/request` answers ephemerally with a
  panel; a member sees File + Refresh and no select; a staffer sees the select and Logs; the
  select is capped at 25 and its placeholder says so; picking a row renders the card with
  EXACTLY the buttons the table above says (parametrise over every status); each button
  calls the right shared function (mock it; assert `via` untouched) and re-renders; modals
  submit through the same functions; `may_accept` false → no Accept button; timeout disables
  every item; withdraw confirm/keep; gates (off / db down / staff-only filing).
- `tests/test_requests.py` — `withdraw_request` and any new pure helper (the status → look
  map, the option label clamp, the button table as data).
- `tests/test_settings_store.py` — the new key round-trips.
- The existing shared-function tests stay green untouched.

## §J — prove before merge

1. `python -m black_bloc` boots and `commands synced` reports the smaller count.
2. Every button in the table exists for its status and NO other (the parametrised test).
3. `ruff`, full `pytest`, `node site/mock/check.mjs`, and `node --input-type=module --check
   < site/public/assets/labels.js` (the third pass's lesson; cheap to run even though the
   site is untouched).

## Deviations

Written by the build agent, 2026-09-03. Everything not listed here was built as
specified.

1. **The card re-renders through `interaction.response.defer()` then
   `interaction.edit_original_response(...)`, not a direct
   `interaction.response.edit_message(...)`.** Every shared function a card button
   calls (`apply_decision`, `mark_ready`, `send_back`, `resume_request`,
   `withdraw_request`) writes the DB and can also post a channel card and/or send a
   DM, which occasionally runs past Discord's 3-second interaction window. Checked
   against the installed `discord/interactions.py` (checklist 29): for a component
   or modal-submit interaction, a non-`thinking` `defer()` IS a
   `deferred_message_update` — the same "update this message" contract
   `edit_message` offers, acknowledged first so the slow work gets the ~15-minute
   interaction-token window instead of 3 seconds. `code-notes.md` has the exact
   lines checked.
2. ⚠️ **Superseded by deviation 9** — the second sentence below ("only the LAST one
   nobody touches ever reaches `on_timeout`") was WRONG, and the fix is in 9. The
   first sentence (a fresh clock per render) still holds.
   **`RequestView(timeout=...)` is a fresh clock on every render, not one running
   total from when `/request` was first opened.** Each click replaces the
   displayed view with a brand-new `RequestView`; only the LAST one nobody
   touches ever reaches `on_timeout`. This reads as an inactivity timeout rather
   than a session length, is the natural result of "re-render on every move,"
   and is what `test_a_view_with_no_message_yet_does_nothing_on_timeout` and
   `test_the_view_disables_every_item_and_says_so_on_timeout` guard directly.
3. **"Requests off" and "staff-only filing" hide the File button and add one
   line to the embed; they do not refuse the whole `/request` command.**
   `request_mode` and `request_who_can_file` have only ever gated FILING (the old
   `/request create`, now `submit()`, unchanged) — listing, moving and
   withdrawing existing requests were never gated by either key. "Gates
   unchanged" is read literally: only the database being down (which breaks
   every query the panel makes) refuses the whole command, matching
   `_ready`/`_database_ready`'s behaviour everywhere else in this cog.
4. **The member's "Take one back…" select silently caps at 25 with no "N of M"
   placeholder**, unlike the staff "Pick a request…" select. The design asks
   for the capped-placeholder wording only on the staff select; a member with
   25+ open-or-held requests of their own is not a realistic case today, so the
   asymmetry is left rather than inventing a second wording nobody asked for.
5. **The interactive staff card carries no "Open on the site" link button**,
   unlike the channel/DM card. `review`'s row already renders 4 move buttons +
   `Back` — Discord's 5-per-row cap — so a site link has nowhere to go without a
   second row; the design's own button table lists no site link on the card,
   only on the top-level panel and the channel/DM cards, so this reads as
   intentional rather than an omission.
6. **Every component/modal action re-checks `bot.db.is_connected` after its own
   `defer()`** (`db_ready`), not only the top-level `/request` command. The
   design names the database-down gate once, at the command; extending the same
   check to every button/select/modal click is a small addition so a database
   dropping mid-session answers `DB_UNAVAILABLE` in words rather than raising
   into the generic `AnswersErrors` fallback.
7. **§J's own claim needed correcting, not just proving.** "`commands synced`
   reports the smaller count" (§J item 1) is not quite right: `commands synced`
   (`command_sync.py:31`, `len(bot.tree.sync(...))`) counts TOP-LEVEL commands,
   and a `Group` already counted as ONE top-level slot — turning it into a bare
   command keeps that slot, so the number is **unchanged at 44**
   (`tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits`,
   measured, not merely asserted; the tree has since shrunk to **29** top-level commands with no
   Groups left at all — the panel waves this build started did the rest). What actually drops by nine is the total
   command-tree size (the nine subcommands that no longer exist beneath
   `/request`), which is not what Discord calls "synced." `LOGS_GROUPS` in
   `tests/test_bot.py` lost its `"request": "request"` entry, since `/request`
   is no longer a `Group` with a `logs` child to find.
8. **`black_bloc/requests.py:withdraw_request` widens checklist item 34's own
   text**, which listed "withdraw" among the routes where `note()` is the sole
   logger — true when that item was written, before withdraw had a shared
   function. Extracting it (as this document asked) gives it the same
   `via`/`kind_via` shape every other move already has, and the web route's
   `note("web.request.withdrawn", …)` was deleted rather than kept, matching the
   checklist's INTENT (one write, one row) over its now-stale enumeration.
   `code-notes.md` carries the detail; `review-checklist.md` itself was left
   untouched — updating that enumeration is the reviewer's call, not this
   build's.

### The reviewer's three findings — written 2026-09-03, fixed in `79548c1`

9. **A replaced view kept its timeout clock, and firing it overwrote the live
   card with a stale disabled one (F1, supersedes deviation 2).** Every
   re-render (`render_panel`, `open_card`, `open_withdraw_confirm`,
   `finish_card`) builds a NEW `RequestView` and edits the message with it, but
   nothing stopped the view it replaced. **The library lines that prove it:**
   `discord/ui/view.py:940–968` (`ViewStore.add_view`) merely overwrites
   `_synced_message_views[message_id]` — it never touches the displaced view's
   `__timeout_task`, so that task keeps running, and when it fires
   `_dispatch_timeout` (`view.py:611–620`) calls the OLD view's `on_timeout`,
   which disabled the OLD children and edited the message with them. Deviation
   2's "only the LAST one nobody touches ever reaches `on_timeout`" was simply
   false: *every* view a member clicks past would eventually have reached it.
   **What changed:** a module-level `retire(previous)` sets `previous.replaced =
   True` and calls `previous.stop()` immediately before every re-render's edit;
   each item callback passes its own `self.view` down as `previous`, and
   `CardMoveButton` hands it to `ReadyModal`/`NoteModal` so the modal's submit
   path retires it too. `RequestModal` (filing) never re-renders and takes
   nothing. ⚠️ **The brief's belt-and-braces guard was NOT written as
   `if self.is_finished(): return`** — measured against the installed library,
   `_dispatch_timeout` sets `__stopped.set_result(True)` *before* creating the
   `on_timeout()` task (`view.py:619` then `:620`), so `is_finished()` is
   **already True inside a genuine timeout** (proved by running a real
   `discord.ui.View` with a 0.05s timeout and reading the flag from inside
   `on_timeout`). That guard would have disabled the footer entirely. The
   explicit `replaced` flag says what is actually meant and cannot be confused
   with a real expiry.
10. **The "gone quiet" footer could essentially never be written at the default
    15 minutes (F2).** `view.message` is an `InteractionMessage` bound to the
    token of the interaction that rendered it, and Discord invalidates that
    token 15 minutes after the interaction. `View._refresh_timeout`
    (`view.py:315–317`, called from `_scheduled_task` at `view.py:596–597`)
    extends the timeout on EVERY interaction with the view — including ones
    that do not re-render at all (`Logs`, opening the File/Ready/Note modals) —
    so by the time the timeout fires the message's token is at least
    `request_panel_minutes` old and usually older. At 15 the `message.edit` in
    `on_timeout` fails (caught, logged at info) practically always, and the
    buttons just die with Discord's "This interaction failed" and no footer.
    **What changed, two parts:** (a) `RequestView.interaction_check` records
    `self.last_interaction = interaction` and returns True, and `on_timeout`
    writes through `last_interaction.edit_original_response(embeds=…,
    view=self)` first, falling back to `self.message.edit(...)` when there is no
    recorded interaction *or* when the recorded one is itself refused — both
    wrapped so an `HTTPException` is logged, never raised. (b) The default of
    `request_panel_minutes` is now **10**, and its `KEY_HELP` says plainly that
    the footer can only be written while Discord's 15-minute interaction window
    is open, so 15 and above mean the buttons stop with no footer. **Nothing is
    clamped** — the owner may still set 15+; the help text is the warning, and
    `KNOWN_ISSUES` KI-20 carries the same sentence.
11. **Staff moves lost the staff check the ten subcommands had (F3).** On `main`
    every staff subcommand called `require_staff(interaction)`
    (`settings_store.py:1092`) on every invocation. The panel asked
    `store.is_staff` only when it *rendered*, so a staffer demoted while a card
    was open kept moving requests until the panel timed out. **What changed:** a
    `still_staff(interaction)` helper re-asks `interaction.client.store.is_staff`
    and, on failure, answers `store.staff_refusal(guild.id)` through the existing
    `answer()` helper (which already copes with responded/not-responded) and
    returns without moving anything. It runs in `CardMoveButton.callback` before
    any defer or modal, and at the top of `Requests.ready_submit` and
    `Requests.note_submit` before their defers. ⚠️ **`require_staff` itself was
    NOT reused**: it calls `interaction.response.send_message` directly, so it
    only works where nothing has been deferred — `still_staff` + `answer()` is
    the one shape used consistently at all three sites. `LogsButton` needed
    nothing: `send_logs` (`actionlog.py:295–297`) already calls `require_staff`
    itself, and a test now pins that.

### The owner's change after deploy — written 2026-09-03, built on `feat/requests-panel-own-list`

12. **A member no longer sees their own requests on the panel; the list is staff-only,
    behind the new `request_panel_own_list` key (default `False`).** Owner, 2026-09-03
    ~10:10, verbatim: *"We need to make the view request thing staff only"*, clarified as
    *"Viewing requests on the panel"*. **What changed:** `build_panel`
    (`cogs/community/requests.py:511`) wraps the own-request `summary_line` block and the
    `PANEL_EMPTY` line in `if staff or panel_shows_own_list(store, guild.id):`. Everything
    else is untouched — `PANEL_INTRO`, the counts line, the requests-off and
    staff-only-filing lines, `NOTHING_OPEN`, the File / Refresh / site buttons, the staff
    select and Logs. ⚠️ **`own_rows` is still fetched for every caller**, because the
    "Take one back…" select needs it to know what is withdrawable — hiding the list is a
    rendering decision, not a query one, and a member who has something withdrawable still
    gets the select and its Yes/Keep confirm.
    **The key** is `PANEL_OWN_LIST_KEY` (`requests.py:49`) with the one-line helper
    `panel_shows_own_list` (`requests.py:477`) beside `PANEL_MINUTES_KEY`/`panel_minutes`,
    registered in all three places `request_panel_minutes` is
    (`settings_store.py:876` `KEY_TYPES`, `:897` `KEY_HELP`, `:1306` `default()`), so
    checklist 33 is satisfied without a new slash command. With it on, the panel is what
    shipped in `ba5cb99`.
    ⚠️ **No "your requests are hidden" sentence was added.** For a member with the list
    off the embed is `PANEL_INTRO` alone (plus the off / staff-only-filing line when one
    applies), which reads fine: the intro's *"see where what you already asked for has got
    to"* is still true of the site link and of the "Take one back…" select, which names
    each withdrawable request by id and text. A line explaining an absence would be the
    only place in this panel that describes what it is NOT showing.
    **Three existing tests were rewritten rather than kept**, because they asserted the
    behaviour the owner overturned: `test_a_member_with_nothing_filed_is_told_so` and
    `test_a_member_sees_their_own_requests_summarised` now turn the key on (and are named
    `…_when_the_list_is_on`), and `test_the_refresh_button_re_renders_the_panel` turns it
    on too, since it proved a re-render by looking for a fresh request in the description.
    Seven new tests cover the default-off member, the flipped-on member, staff either way,
    and the helper/registry. 3345 tests pass (3338 at `ba5cb99`), ruff clean, `check.mjs`
    17 pages / 139 routes (site untouched). ⚠️ **NOT verified against live Discord** — no
    panel has been opened with the key off. **Merged and live** as the fifth pass
    ([`../DONE.md`](../DONE.md)); the branch is gone. The suite is **5546** and the mock reads
    **150 routes** at v108.
