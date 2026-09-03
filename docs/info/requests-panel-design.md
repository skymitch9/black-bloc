# Requests, fourth pass — `/request` is ONE command that opens a panel

**Audience:** the builder and the reviewer. **Status:** TRACKED · **BUILDABLE**, 2026-09-03.
Owner's ask ~06:50 (verbatim in `../TODO.md`, "🔧 Open engineering items"): *"The flow
seems tough, and request set and request ready seem overlapping."* → *"Let's also have
/request open a menu maybe. Let's try and minimize slash commands and maximize interactive
windows"* → *"Let's start this process with request then carry it through the rest of the
app. Request first."* **Last verified: 2026-09-03** against `black_bloc/requests.py` and
`cogs/community/requests.py` at `3e18e4a` (the third pass, deployed `70a6720`). ⚠️ This is
the PATTERN for every later feature — see the project `CLAUDE.md` rule.

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
  | `review` | `Accept` (→ done; NOT rendered when `may_accept` says this staffer may not, the embed footer says who may) · `Send back` (modal, note required) · `Hold` · `Decline` |
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

One new key in `settings_store.py`: **`request_panel_minutes`** (`int`, default **15**, the
minutes a panel stays live) — registry type, help text, default, on the Settings page and
via `/settings set-value` like every key. Nothing else here is a decision: the 25-option cap
is Discord's, the button table is the state machine.

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

(the builder appends here, numbered, with the reason)
