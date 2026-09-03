# Requests, third pass — embeds, "what was built", "how to test", the site link

**Audience:** the builder and the reviewer. **Status:** TRACKED · **DESIGN — not
built.** Owner's ask 2026-09-03 ~00:50 (verbatim in `../TODO.md`, "🔧 Open
engineering items"). **Last verified: 2026-09-03** against `black_bloc/requests.py`,
`cogs/community/requests.py`, `api/tools/requests.py`, `site/public/assets/page-requests.js`
at `40fbfc4`. Extends [`requests-states-design.md`](requests-states-design.md); the
state machine grows ONE state (`review`, owner decision 2026-09-03 ~01:00, below).
⚠️ **Build order:** AFTER the double-logging fix on `../TODO.md` lands — both touch
`cogs/community/requests.py` and `api/tools/requests.py`.

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
| "a link to the request on the website" | New per-request URL `{origin}/requests#r-{id}`; a link button on every card |
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
`{bot.settings.origin}/requests#r-{id}`. `what` clamps at 256 in the title-ish field
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

## Deviations

(the builder fills this)
