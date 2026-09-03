# Requests, third pass — embeds, "what was built", "how to test", the site link

> ⚠️ **2026-09-03: slash paths superseded by the panel** — `/request` is now ONE
> command that opens an interactive panel; see [`requests-panel-design.md`](requests-panel-design.md).
> The embed builder (`request_embed`, the seven looks) this document designed is unchanged
> and is exactly what the panel's card reuses.

**Audience:** the builder and the reviewer. **Status:** TRACKED · ✅ **SHIPPED — merge
`355d6e9` + anchor fix `70a6720`, deployed `70a6720` 2026-09-03 06:34; the landing one-off
at the foot was RUN at 06:41 (#1, #2 `done → review`; #3 `hold`)** — see the
`## Deviations` list (14). Owner's ask 2026-09-03
~00:50 (verbatim in `../TODO.md`, "🔧 Open engineering items"). **Last verified:
2026-09-03** against `black_bloc/requests.py`, `cogs/community/requests.py`,
`api/tools/requests.py`, `site/public/assets/page-requests.js` as built (3260 tests,
ruff clean, `check.mjs` 17 pages / 139 routes; the page rendered against the mock).
Live: boot log clean (schema 26 added four columns), `/requests.html` renders with
Ready to check 2 / On hold 1 / Done 0 and no console errors. ⚠️ **NOT verified:** any
card by eye in Discord — the one-off posts nothing; the first real staff move posts the
first card. Slash paths and the DM look are on the sweep list. Extends
[`requests-states-design.md`](requests-states-design.md); the
state machine grows ONE state (`review`, owner decision 2026-09-03 ~01:00, below).
**Build order:** the double-logging fix landed as `df393ab` (2026-09-03) — cut the build
from that or later. ⚠️ Both of the files above now take `via`: `apply_decision` and
`resume_request` log ONE row through `logkinds.kind_via`, routes pass `via=VIA_WEBSITE`
and never `note()` a second line (checklist item **34**; the AST guard in
`tests/test_logkinds.py` fails the build if a route does). The new moves (`ready`,
`accept`, `sendback`) follow the same shape — one shared function, `via` keyword-only,
`request.review` / `request.sent_back` through `kind_via`.

## The owner's two decisions (2026-09-03, one at a time)

1. Asked "is 'what was built' required on Done?", the owner answered with a
   question: *"Do we need an acceptance pending so a staffer can check if
   something is done?"* → yes: a **`review`** state ("ready to check").
2. "Yes, build it that way" — `in_progress → review → done`; **built + how-to-test
   are required to ENTER review**; Accept / Send back; whether the accepter must
   be a different staffer is a setting, **default off**.

## The machine, third pass

```
open ──► in_progress ──► review ──► done          (final)
  │           │            │  └─ send back ─► in_progress (note required)
  ├───────────┴────────────┴──► hold             (reason REQUIRED; remembers held_from)
  └───────────┴────────────┴──► declined         (final; reason REQUIRED; also from hold)
withdrawn = the requester's own final state (from open or hold only — not from review)
```

| From \ To | in_progress | review | done | hold | declined | withdrawn |
|---|---|---|---|---|---|---|
| **open** | staff | — | — | staff | staff | requester |
| **in_progress** | — | staff (`built` required, `how_to_test` optional) | — | staff | staff | — |
| **review** | staff "send back" (note required) | — | staff "accept" | staff | staff | — |
| **hold** | resume → `held_from` (may be `review`) | | | | staff | requester |
| done / declined / withdrawn | final | | | | | |

Still ONE data table (`TRANSITIONS`) in `black_bloc/requests.py`; `checked_move`
grows the two new required-text rules beside `REASON_NEEDED`. `done` is reachable
ONLY from `review`, so every done card has substance. `request_review_by_other`
(bool, default off): when on, `accept` by the staffer recorded in `ready_by`
refuses in words ("someone else on staff has to check this one").

**Landing data step (owner, 2026-09-03 ~03:55: "Move the 2 done ones to ready to
check, leave the other as hold"):** the migration itself moves nothing, but at
landing the conductor moves **#1 (raid trains) and #2 (applications)** from `done`
to `review` by a one-off on the live database (`done → review` is not a staff move
and must not become one): `status='review'`, `ready_by` = the owner, `done_at`
cleared, `built` = the one-line shipped note already in each row's `notes`,
`how_to_test` = a pointer to the owner's sweep rows (`docs/access/sweeps.md` 48–52
for #1, 53–57 for #2 — those rows ARE the how-to-test). Then the review card posts
for each. **#3 stays `hold`.** Verify afterwards on `/api/requests`.

## Why

The three request flips at the 17/18/19 landing were the first real traffic through
the notifications, and they read as bare one-liners: `Request **#1** from <@…> is done:
…`. The owner wants each one to be a proper Discord embed that says what was built,
how to try it, and where the request lives on the site — and the same card at filing
time so a request is confirmed in public the moment it exists.

## What the owner asked for, mapped

| Owner's words | Design |
|---|---|
| "a standard appealing template … one of the discord info boxes" | ONE embed builder, `request_embed(bot, guild, row, move)`, used by the channel post AND the DM — one rendering, one home |
| "a description" | The request's `what` (title) and `why` (body) |
| "how to test the feature" | New column `how_to_test`, filled by staff when marking the request **ready to check**; shown on the review and done cards when non-empty |
| "a short explanation of what was built" | New column `built`, **required** to enter `review`; shown on the review and done cards |
| "an acceptance pending so a staffer can check" | The `review` state: Accept → done, Send back → in_progress with a note |
| "a link to the request on the website" | New per-request URL `{origin}/requests.html#r-{id}`; a link button on every card |
| "post that same request link in discord … a message at the start" | The filing card, to `request_notify_channel_id` (already the filing channel) |
| "once at the end when done. Also one for the in hold or declined states" | A card on every staff move, to `request_status_channel_id` (falls back to the notify channel, as today) — done / hold / declined, **and in_progress / review / sent back** (one template covers them all, and the owner can turn any move's card off — settings below) |

## Storage — schema 26

`requests` gains four nullable columns:

| Column | Filled when | Limit |
|---|---|---|
| `built TEXT NULL` | the move into `review` (site dialog, `/request ready` modal) — required | 1000 |
| `how_to_test TEXT NULL` | same, optional | 1000 |
| `ready_by INTEGER NULL` | the staffer who moved it into `review` (for `request_review_by_other`) | — |
| `sent_back_reason TEXT NULL` | the move review → in_progress (required); cleared on the next move into `review` | 500 |

`built` / `how_to_test` are editable afterwards on the review and done cards (site) —
a typo in "how to test" must not need a state change to fix. Migration adds the
columns; no backfill.

## The embed — one builder, seven looks

`black_bloc/requests.py:request_embed(row, *, move, origin, guild)` returns a
`discord.Embed`:

| Move | Title | Colour | Fields |
|---|---|---|---|
| filed | `New request #N` | blurple `0x5865F2` | Asked for · Why · Requested by · Due (if set) |
| in_progress | `Request #N is being worked on` | amber `0xFEE75C` | Asked for · Requested by · Assignee (if set) |
| review | `Request #N is ready to check 🔎` | teal `0x1ABC9C` | Asked for · **What was built** · **How to test** (if given) · Marked ready by · Requested by |
| sent_back | `Request #N was sent back` | orange `0xE67E22` | Asked for · What needs doing (the note) · Sent back by · Marked ready by |
| done | `Request #N is done ✅` | green `0x57F287` | Asked for · **What was built** · **How to test** (if given) · Accepted by · Requested by |
| hold | `Request #N is on hold` | grey `0x99AAB5` | Asked for · Why it is waiting (the reason) · Was (`held_from`) · Requested by |
| declined | `Request #N was declined` | red `0xED4245` | Asked for · Why (the reason) · Requested by |

`sent_back` is a card look, not a state — the row is `in_progress` again; the move
is told apart by `was == review`. Log kinds: `request.review` and `request.sent_back`
(both IMPORTANT — staff have something to do), beside the existing `request.done` /
`hold` / `declined`.

**Who gets the DM:** the requester on in_progress / done / hold / declined (as
today, gated by `request_dm_on_decision`); the staffer in `ready_by` on `sent_back`.
Nobody is DM'd on `review` — it is staff-facing; the channel card is its notice.

Every card: footer `Black Bloc · requests`, timestamp = the move time, and a
`discord.ui.View` with one **link button** "Open on the site" →
`{bot.settings.origin}/requests.html#r-{id}`. `what` clamps at 256 in the title-ish field
and 1024 in any field body (Discord's cap — `events.clamp`). Mentions stay
`AllowedMentions.none()`. Colours are data (`EMBED_COLOURS: dict[str, int]`) not
five literals.

The **DM** is the same embed (the requester gets the card, not a paraphrase of it),
sent through the existing `dm()` — `send(embed=…, view=…)`; the plain-text `DM_*`
strings go. The **channel** line is the same embed through `post_line` (which grows
an `embed=`/`view=` path; `line` stays for the log-only fallback text). TEST_MODE
behaviour is unchanged: the guard still blocks any channel but the test one and
logs `request.notify_skipped_test_mode`.

## The site link

`page-requests.js`: every card gets `id="r-{id}"`. On load, if `location.hash`
is `#r-N`: if the card is on the page, scroll to it and flash it (one CSS class,
`is-linked`, 2 s); if it is NOT on the current page (pager, or a member who only
sees `/mine`), fetch it — staff via `GET /api/requests/N`, members via `/mine` —
and render it as a pinned card above the sections with a "Back to all" dismiss.
Not found / not allowed → the page's usual empty-state wording, never a bare
status (global rule).

## The moves, on both surfaces (checklist 33 — a slash path AND a site control)

| Move | Site (Requests page) | Slash |
|---|---|---|
| in_progress → review | **Ready to check** button on the board card → dialog: "What was built" (required) + "How to test it" | `/request ready <id>` → modal, same two fields |
| review → done | **Accept** button on the review card | `/request accept <id>` |
| review → in_progress | **Send back** button → dialog: "What needs doing" (required) | `/request sendback <id> <note>` |
| edit built / how_to_test | inline on the review and done cards (`POST …/status` with only those fields — `set_fields` already handles partial saves) | — (site only; say so in `/request ready`'s description) |

Routes: `POST /api/requests/{id}/ready {built, how_to_test}`, `POST …/accept`,
`POST …/sendback {reason}`; `POST …/status` accepts `built` / `how_to_test` as
plain fields and refuses `status:"done"` from anywhere but `review` in words (the
`TRANSITIONS` table does that already once `done` is only in `review`'s set).
`/request set status:done` from `in_progress` answers in words that `/request ready`
is the way. Validation lives with `checked_move` in `black_bloc/requests.py`, the
one place a move is judged — a required-but-empty `built` or send-back note refuses
in words, exactly as a missing hold reason does today (`REASON_NEEDED`).

The page gets a **Ready to check** section between the board and Done (review
cards: built, how-to-test, who marked it ready, Accept / Send back / Hold /
Decline). The status filter and CSV export learn the new state; `STATUS_WORDS`
says "ready to check".

## Settings (checklist 33 — every decision configurable both ways)

| Key | Type | Default | Meaning |
|---|---|---|---|
| `request_channel_moves` | multi-enum of `filed,in_progress,review,sent_back,done,hold,declined` | all seven | which moves post a card to the channel |
| `request_review_by_other` | bool | **off** (owner, 2026-09-03) | when on, the staffer in `ready_by` cannot accept their own review |

Both in `settings_store.py` (registry, `KEY_TYPES`, descriptions), `labels.js`,
the mock `contract.json`, and the exact-key-set test. `request_dm_on_decision`
keeps gating the requester's DM.

## Tests (mirror the package)

`tests/test_requests.py`: the new `TRANSITIONS` rows (done only from review;
withdraw not from review; resume back to review), one test per card look asserting
title/colour/fields and the link URL, the required-text rules;
`tests/cogs/community/test_requests.py`: channel post carries `embed` + `view`, DM
carries the same embed, `ready_by` DM on send back, TEST_MODE still skips and logs,
`request_review_by_other` refuses in words; `tests/api/tools/test_requests.py`: the
three new routes, `status:"done"` refused from in_progress, edit of
`built`/`how_to_test` on review and done rows; `tests/storage/test_db.py`: schema 26
columns; `site/mock/check.mjs` contract for the new state, fields, routes and keys.

## §J — the measurement before the build

Post one card of each move to the test channel from a scratch script and screenshot
it: the owner's "appealing" is judged by eye, and a field that wraps badly (a long
`why`) is found here, not after deploy. Record what changed in the `## Deviations`
foot.

## §J — what the measurement actually changed

Written by the build agent, 2026-09-03. §J was run as
`scripts/scan/embed_preview.py` (gitignored, NOT committed): it builds one card of
each of the seven looks from a row whose `why`, `built`, `how_to_test`,
`sent_back_reason` and `decline_reason` are each ~900 characters, prints every
`to_dict()`, and asserts the caps and the link URL. **Nothing was posted to
Discord** — the conductor posts the real cards.

| Look | Whole embed | Fields |
|---|---|---|
| filed | 1211 | 4 |
| in_progress | 209 | 3 |
| review | 2004 | 5 |
| sent_back | 718 | 4 |
| done | 1990 | 5 |
| hold | 794 | 4 |
| declined | 764 | 3 |

Discord's caps are 256 (title), 1024 (field value) and 6000 (whole embed). The
worst look is **a third of the total cap**, so nothing needed reshaping — the
per-field `clamp(…, 1024)` this document asked for is what keeps it there, and
removing it fails `test_no_card_field_or_title_can_outgrow_what_discord_will_take`
(proved by mutation, not by reading).

⚠️ **The one thing §J caught is not about Discord at all**: the review title's 🔎
and the footer's `·` raise `UnicodeEncodeError` on a cp1252 Windows console, which
looks exactly like a builder fault and is not one. The script reconfigures stdout
to UTF-8; anybody re-running it on Windows needs that line.

## Deviations — where the build departed from this document, and why

Written by the build agent, 2026-09-03. Everything not listed here was built as
specified.

1. **`hold` can go to `review`, which this document's table leaves blank.** The
   table says "resume → `held_from` (may be `review`)", and `resume_target` only
   returns `held_from` when it is in `TRANSITIONS[HOLD]` — so leaving `review` out
   would have silently resumed a held review row into `in_progress`. It is in.
   Side effect: `/request set status:review` is legal from `hold`, which is
   harmless because `built` is still required to enter review.
2. **`checked_move` raises a DIFFERENT sentence for `done` than the table's
   generic one.** `DONE_NEEDS_A_CHECK` fires when the row is `open`,
   `in_progress` or `hold` and names `/request ready <id>`, `/request accept <id>`
   and the site's Ready-to-check button. A `declined` or `withdrawn` row still
   gets the "is where a request finishes" sentence, because pointing somebody at
   the ready step there would be a lie.
3. **`request_channel_moves` needed a new registry TYPE, `enums`.** The registry
   had `enum` (one of) and `channels`/`roles` (a list of ids) but nothing for "any
   of these words". `coerce_value` validates against `KEY_CHOICES` and returns the
   set in the registry's own order (so the stored value is stable), `parse_value`
   splits a comma list for `/settings set-value`, `display_value` says "none of
   them" for an empty one, and `ui.js:control` draws a checkbox per choice.
   ⚠️ `cogs/core.py:VALUE_KEYS` had to learn `enums` too, or the key would have
   been dashboard-only — the exact half of checklist 33 that matters.
4. **`request_review_by_other` is judged inside `apply_decision`, not inside
   `accept`.** Putting it in the wrapper would have left
   `POST /{id}/status {status:"done"}` as a way around it. One judge, one place.
5. **`sent_back` is derived, never stored.** `look_of(was, status)` returns it when
   `in_progress` is arrived at from `review`; the log kind, the card look and the
   DM recipient all read that one function. This is why `apply_decision` logs
   `f"request.{look}"` and not `f"request.{wanted}"` — `tests/test_logkinds.py`'s
   `KNOWN_DYNAMIC` key moved with it.
6. **`tell_requester` is now `tell_person`**, because on `sent_back` the person
   told is the staffer in `ready_by`, not the requester. `person_told` is the one
   place that decides which. The `ready_by` DM is NOT gated by
   `request_dm_on_decision` — that key is described as the requester's switch, and
   silently widening it to staff notices would be a second meaning for one key.
7. **The card carries an author line with the server's name.** The plain `DM_*`
   strings said "on **{guild}**" and the embed's field table has nowhere for it,
   so a DM'd card would not have said which server it came from. `guild=None`
   leaves the author line off entirely.
8. **`post_line` keeps its name and its `line` argument, and the line is never
   sent.** The embed is the message (`content` is `None`); `line` is what the
   server log names when a post is skipped by the guard or refused by Discord, so
   `move_line` survives as the one-line plain form.
9. **`set_status` builds its UPDATE from a dict instead of one fixed statement.**
   Five columns now have per-move rules (`held_from`, `decline_reason`, `done_at`,
   `ready_by`, `sent_back_reason`) and the "leave this one alone" cases were
   already being faked with `COALESCE`. A column with no rule for a move is simply
   not in the statement.
10. **The requests page's `done` MOVE button is gone**, not hidden. `MOVES` no
    longer has a `done` entry, so a Done button cannot be drawn from `row.moves`
    on any card; the review card's Accept is its own button, and its `moves` are
    filtered down to hold and decline.
11. **Editing `built`/`how_to_test` on a done card is allowed.** The document says
    "editable afterwards on the review and done cards", and `POST …/status` with
    only those fields does it — it leaves ONE `web.request.updated` row and moves
    nothing.
12. ⚠️ **A defect found on the way, fixed in its own commit and NOT part of this
    design: `site/public/assets/labels.js` had not parsed since `7b1c592`.** The
    Phase 19 merge pasted the applications labels after the `LABELS` object's
    closing brace, so **every dashboard page rendered blank**. `node --check` on
    `labels.js` at `43eb17b` reproduces it. Fixed by moving the block inside the
    object and merging the two `NAMESPACES` lists (which also restores the
    `raidtrain_` prefix trim the duplicate had dropped).
13. **The mock's `/accept` and `/sendback` read the row AFTER the move.**
    JavaScript evaluates `{ request: askRow(row), message: askDecide(row, …) }`
    left to right, so the pre-existing `/hold`, `/decline` and `/status` entries
    answer with the state the row was in. Only the two new routes were changed;
    the older three are left as found and are noted here so the next person is not
    surprised by them.
14. **The card link is `{origin}/requests.html#r-N`, not `/requests#r-N`** —
    a defect in THIS document, found by the conductor at the merge (2026-09-03
    06:19): the dashboard is a `StaticFiles(html=True)` mount and live `/requests`
    answered `{"detail":"Not Found"}`. `REQUEST_ANCHOR` now takes the page name
    from `logkinds.FEATURE_PAGES["request"]`, the same table the log embeds link
    through, so the two cannot drift. Fixed on `main` after the merge, before the
    deploy; the URL tests, the page/CSS comments and this document's two mentions
    were rewritten with it.

## The landing data step — the exact one-off (conductor's, NOT run here)

Owner, 2026-09-03 ~03:55: *"Move the 2 done ones to ready to check, leave the
other as hold"*. `done → review` is not a staff move and must not become one, so
this is a one-off against the live database. ⚠️ **Run it only after the deploy
that carries schema 26**, or the four columns do not exist yet. The image has no
`sqlite3` CLI, so it is a single Python statement:

```sh
fly ssh console -a black-bloc -C "python3 -c \"
import sqlite3
db = sqlite3.connect('/data/black_bloc.sqlite3')
db.row_factory = sqlite3.Row
how = {1: 'The sweep rows in docs/access/sweeps.md, rows 48-52.',
       2: 'The sweep rows in docs/access/sweeps.md, rows 53-57.'}
for row in db.execute('SELECT id, notes, decided_by FROM requests WHERE id IN (1,2)').fetchall():
    db.execute(
        'UPDATE requests SET status=?, ready_by=?, done_at=NULL, built=?, how_to_test=?, '
        'sent_back_reason=NULL WHERE id=? AND status=?',
        ('review', row['decided_by'], row['notes'], how[row['id']], row['id'], 'done'))
db.commit()
print([dict(r) for r in db.execute('SELECT id,status,ready_by,built,how_to_test,done_at FROM requests WHERE id IN (1,2,3)')])
\""
```

- ⚠️ **`ready_by` is read from each row's own `decided_by` column**, which is the
  staffer who last moved it — the owner, on both, since he marked them done at the
  17/18/19 landing. Nothing is hard-coded, and the `print` at the end is the
  verification: two rows `review` with a non-null `ready_by` and a null `done_at`.
- `built` is each row's existing `notes` — the one-line shipped note already
  there.
- **#3 is untouched** and stays `hold`; the `SELECT` at the end includes it so its
  status can be eyeballed in the same output.
- `AND status='done'` makes the statement safe to run twice: a second run matches
  nothing.
- Afterwards, check `/api/requests` and post the two review cards (a staff move on
  each, or the conductor's own call).
