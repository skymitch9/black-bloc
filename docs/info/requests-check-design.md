# Requests, sixth pass — "Ask them to check": ping the requester from the card

**Audience:** the builder and the reviewer. **Status:** TRACKED · **SHIPPED** (design
2026-09-03 ~12:00, Fable; built the same afternoon on `feat/requests-check`, merged `44170f4`
with one review fix — `moment()` now stamps the check card with `check_asked_at` — and live in
**v61** at 12:29, schema 27; see `## Deviations` at the foot, 11 of them). Owner's ask, 2026-09-03 11:15, verbatim in
`../TODO.md` ("🔧 Open engineering items"): *"We also need a way to ping the requester from the
request app. I want to have it message the requesters to check the work."* — then *"Keep
building"*, so the design calls below were made by the conductor and are listed under §D for
the owner to overturn later (each is a setting or a one-line table change).
**Last verified: 2026-09-03** — every `path:line` below was read at `46e3ba4` (v60, the wave-0
merge + gate change); the state machine, looks, card tables, settings registry, site route
shapes and the `deploys.log` line are as this doc says. ⚠️ **NOT verified:** anything against
live Discord — whether a closed-DM member's `user.send` raises `Forbidden` (assumed; the
existing `dm()` at `cogs/community/requests.py:150` already treats ANY exception as "not
told", so the fallback does not depend on which one).

Follows the pattern: [`requests-panel-design.md`](requests-panel-design.md) for the panel,
[`requests-embeds-design.md`](requests-embeds-design.md) for the one-builder cards,
[`panels-program.md`](panels-program.md) §2 for the invariants (P1–P17). Nothing here restates
them; the builder reads all three plus [`review-checklist.md`](review-checklist.md) (items 33
and 34 bite hardest here).

## A. What is wrong today (measured at `46e3ba4`)

When staff mark a request **ready to check** (`review`), **the person who asked hears
nothing.** `DM_LOOKS` (`black_bloc/requests.py:47`) is `(IN_PROGRESS, HOLD, DONE, DECLINED)`
— `review` was deliberately staff-facing (third pass: "nobody is DMed on review; it is for the
second pair of eyes"). The requester is told only at `done`, by which point it is finished.
There is no way, from the panel or the site, to say to them *"this is built — go and try it
and tell us"* — which is the owner's ask: the requester is often the only person who can say
whether it does what they meant.

## B. The decision in one paragraph

**A staff ACTION, not a state.** `Ask them to check` is a button on the **review** card (panel
AND site — one shared function, one log row). It DMs the requester a card built from the same
`request_embed` in a new look, `check_asked`, whose title is *"Request #N is ready for you to
try"* and whose fields are what / what was built / how to test / who marked it ready, with a
sentence asking them to try it and say how it went. When their DMs are closed the card is
posted in the request channel **with a real mention** (the only place this cog ever pings)
if `request_check_fallback_channel` is on (default on). It records who asked and when
(`check_asked_by`, `check_asked_at`, schema **27**) so the review and done cards show *"Asked
to check · @who · 3 minutes ago"* and staff do not ask twice by accident — asking again is
allowed, it is just visible. `request_check_on_ready` (default **off**) makes every entry
into `review` ask automatically. The request does **not** move; `review` stays `review`.

Why not a state: the state machine's states are *who holds it* (staff working / staff
checking / waiting / finished). "The requester has been asked" is a fact ABOUT the review,
not a different holder; a `checking_by_requester` state would double every review-card button
and every test for no new transition. Why not `done`: the done DM already carries built +
how-to-test (`EMBED_FIELDS[DONE]`, `requests.py:232`), so "check the work" there would be a
second copy of the same message. If the owner wants it on done too it is one tuple entry in
`CARD_BUTTONS[DONE]` plus the site bar — §D3.

## C. The pieces

### C1. `black_bloc/requests.py` (pure, no Discord I/O)

| Change | Where | Exactly |
|---|---|---|
| New look | `:44–46` | `CHECK_ASKED = "check_asked"`; `LOOKS` gains it **last** (`… HOLD, DECLINED, CHECK_ASKED`). NOT added to `DM_LOOKS` — `ask_check` sends its own DM; `tell_person` must keep ignoring it |
| Colour / title / fields | `:209–235` | `EMBED_COLOURS[CHECK_ASKED] = 0x3498DB`; `EMBED_TITLES[CHECK_ASKED] = "Request #{request_id} is ready for you to try 🙌"`; `EMBED_FIELDS[CHECK_ASKED] = ("what", "built", "how_to_test", "ready_by", "asked_by")` |
| Description line | `request_embed` `:604` | Only this look sets `embed.description`: `CHECK_ASKED_DESCRIPTION = "Try it and tell {asked_by} how it went — say what works and what does not. Staff mark it done once you are happy."` with `asked_by` = `mention(check_asked_by)` or "staff". Title/colour/fields stay table-driven; the description is a single `if look == CHECK_ASKED` — do not grow a fourth table for one row |
| The "asked" field on review + done cards | `:230`, `:232`, `:236`, `:252`, `:579` | `EMBED_FIELDS[REVIEW]` and `[DONE]` gain `"asked"` at the end; `FIELD_LABELS["asked"] = "Asked to check"`, `FIELD_LABELS["asked_by"] = "Asked by"`; both in `INLINE_FIELDS`. `field_value`: `"asked"` → `f"{mention(check_asked_by)} · <t:{unix}:R>"` when `check_asked_at` is set, else `""` (so the field is simply absent on a card nobody has asked on — `request_embed` already skips empty values); `"asked_by"` → `mention(check_asked_by)` |
| Channel one-liner | `MOVE_LINE` `:195` | `CHECK_ASKED: "Request **#{request_id}** from {who} — they have been asked to check it: {what}"` |
| Settings helpers | after `:531` | `CHECK_FALLBACK_KEY = "request_check_fallback_channel"`, `CHECK_ON_READY_KEY = "request_check_on_ready"`; `check_falls_back(store, guild_id) -> bool`, `checks_on_ready(store, guild_id) -> bool` (same shape as `review_by_other` `:530`) |
| Button | `CARD_BUTTONS[REVIEW]` `:403` | Insert `MoveButton("check", "Ask them to check", "primary")` **between** Accept and Send back. Not a modal. `may_accept` does not touch it — the first pair of eyes may still ask the requester |
| Refusal text | `NOT_READY_TO_CHECK` `:162` | Reused with `doing="ask them to check"`. ⚠️ Its last sentence is stale since the fourth pass (*"`/request ready {id}` is what puts one there"* — that subcommand no longer exists): change it to *"**Ready to check** on its card is what puts one there."* and fix the tests that assert the old wording |
| Reply strings | new | `CHECK_ASKED_DM = "Request **#{request_id}** — {who} has been asked by DM to try it."`, `CHECK_ASKED_CHANNEL = "Request **#{request_id}** — {who}'s DMs are closed, so they were pinged in the request channel instead."`, `CHECK_ASKED_NOBODY = "Request **#{request_id}** — {who}'s DMs are closed and the channel fallback is off, so nobody was told. A Lead can turn `request_check_fallback_channel` on."` |

### C2. Storage — schema 27

`black_bloc/storage/db.py`: `SCHEMA_VERSION = 27`; the `requests` table (`:496–497`
neighbourhood) gains `check_asked_by INTEGER` and `check_asked_at TEXT`; both appended to the
added-columns tuple (`:650–651` neighbourhood) so an existing file grows them on boot. A
`set_check_asked(db, request_id, who, at)` beside `set_fields`. `row_value` (`:548`) already
makes an un-migrated row read as nothing. Test: `tests/storage/test_db.py` — a schema-26
file opened at 27 has both columns and the version stamp.

### C3. The one shared function — `black_bloc/cogs/community/requests.py`

```python
async def ask_check(bot, guild, request_id, actor, *, via=VIA_DISCORD) -> tuple[str, Any]:
    """The panel's Ask-them-to-check button and the site's — the requester is told the work
    is theirs to try; the request does not move."""
```

Beside `send_back` (`:373`), same shape, same return contract `(what to say, row or None)`:

1. `get_request`; wrong guild or missing → `(NO_SUCH_REQUEST, None)`.
2. `row["status"] != REVIEW` → `(NOT_READY_TO_CHECK.format(..., doing="ask them to check"), None)`.
3. `set_check_asked(bot.db, request_id, actor.id, now_iso)`; `fresh = get_request`.
4. `embed, view = card(bot, guild, fresh, CHECK_ASKED)` (`card` `:170` — the same builder,
   so the DM carries the site link button when an origin is set).
5. `told = "dm"` if `await dm(member, embed=embed, view=view)` (`dm` `:150`; member from
   `guild.get_member(user_id) or bot.get_user(user_id)`, exactly `tell_person` `:186`).
6. Else: log `request.dm_failed` with `details={"request_id", "status": CHECK_ASKED}` (the
   existing kind, `:193`) and, if `check_falls_back(...)`, post the card in
   `status_channel_id(...)` through `post_line` with a **new keyword `ping=user_id`**: when
   set, `post_line` (`:199`) sends
   `allowed_mentions=discord.AllowedMentions(users=[discord.Object(id=ping)])` and prefixes
   `content=mention(ping)` — everything else in `post_line` (guard, missing channel,
   `NOTIFY_SKIPPED_KIND`, `NOTIFY_FAILED_KIND`) is unchanged and still applies. A returned
   message → `told = "channel"`, else `told = "nobody"`. Fallback off → `told = "nobody"`.
7. ONE `log_action(bot, guild, kind_via("request.check_asked", via), actor=actor,
   target=row["user_id"], details={"request_id", "told": told, "via": via})`. (`dm_failed`
   is a second row on failure — that is today's contract for every look, not a new one.)
8. If `posts_a_card(store, guild.id, CHECK_ASKED)` and `told != "channel"`, the plain
   (non-pinging) card goes to the channel via `notify_move` — so the same ask never posts
   twice in the channel. `MOVE_LOOKS` (`:100`) picks up the new look from `LOOKS`
   automatically.
9. Return `(CHECK_ASKED_{DM|CHANNEL|NOBODY}.format(request_id, who=mention(user_id)), fresh)`.

`MOVE_FUNCS` (`:432`) gains `"check": lambda bot, guild, rid, actor: ask_check(bot, guild, rid, actor)`;
`CardMoveButton.callback` (`:726`) needs no change — `check` is not `ready` and not
`needs_modal`, so it falls through to `run_move`, which already does `still_staff` (P5) →
`defer` → `db_ready` → `MOVE_FUNCS` → `finish_card`. The re-rendered card shows the new
"Asked to check" field.

**Auto-ask:** in `mark_ready` (`:343`), after `apply_decision` returns a row, `if fresh is not
None and checks_on_ready(bot.store, guild.id): await ask_check(bot, guild, request_id, actor, via=via)`.
Its own log row (it IS a second thing that happened); the returned text stays
`READY_SAID` — the ask's outcome is on the card.

### C4. Settings — two keys, both ways (checklist 33)

`black_bloc/settings_store.py`, appended to the requests block at `:872–903`:

| Key | Type | Default | KEY_HELP |
|---|---|---|---|
| `request_check_fallback_channel` | bool | **true** | "true to ping the person who asked in the request channel when Ask-them-to-check cannot DM them (closed DMs); false to tell staff nobody was reached and leave it there" |
| `request_check_on_ready` | bool | **false** | "true to ask the person who asked to try the work the moment a request is marked ready to check, without a staffer pressing Ask them to check" |

`REQUEST_CARD_MOVES` (`:861`) gains `"check_asked"` last; `REQUEST_CARD_DEFAULT` (`:870`)
**excludes it too** (`if move not in ("done", "check_asked")`) — the DM is the point; a channel
copy is opt-in like done. Update the `request_channel_moves` help string to list eight and say
"every one but done and check_asked". The `coerce`/`parse`/`display` branches at `:1301–1307`
need no change (they are keyed by type). Site half: `site/public/assets/labels.js:139`
neighbourhood — two new labels ("Ping in the channel when a check-DM is refused", "Ask the
requester to check automatically at ready") and the choice list the Settings page renders
from `KEY_CHOICES` needs nothing; `site/mock/server.mjs:391` — the enums row gains the eighth
choice and its default drops `done` + `check_asked` (⚠️ that mock row still says "all seven by
default" — fix it while there, it has been wrong since `a392a3f`); two mock bool rows after
it; `page-requests.js:89` lists the keys the Requests page's own settings strip shows — add
both. `tests/test_settings_store.py` (`:925–1003` pattern) — the two keys' type, default and
that `REQUEST_CARD_DEFAULT` excludes `check_asked`.

### C5. Site — route, page, mock, contract

- `black_bloc/api/tools/requests.py`: `POST /{request_id}/check` beside `/accept` (`:511`),
  identical shape — `writer`, `require_guild`, `require_db`, `_wanted`, then
  `ask_check(bot, guild, request_id, actor_for(bot, who, guild), via=VIA_WEBSITE)`; `fresh is
  None` → `Refused(409, "not_decided", said)`; **no `note()` call** (checklist 34 — the row
  comes from `kind_via`). `request_row` (`:133`) gains `check_asked_by`, `check_asked_by_name`
  (the `ready_by_name` pattern `:158`), `check_asked_at`.
- `site/public/assets/page-requests.js`: `askCheckButton(row, say, which)` modelled on
  `acceptButton` (`:544`) — label **"Ask them to check"**, tone `'quiet'`, no dialog (nothing
  to type; the reply strip says what happened via `found.message`). In `reviewCard` (`:661`)
  between Accept and Send back. An `askedChip(row)` beside `readyChip` (`:624`): `asked
  {check_asked_by_name} · {relative time}` on review AND done cards when `check_asked_at` is
  set (done cards render in the finished list — find where `readyChip` is used there and
  mirror it).
- `site/mock/server.mjs`: `route('POST', '/api/requests/:id/check')` beside `/accept`
  (`:4745`) — stamps the two fields on the row, 409 off-review, returns `{request, message}`.
- `site/mock/check.mjs:340–343`: the review walk becomes `ready → check → sendback → ready →
  accept` so the contract exercises `/check` on a review row; the route count in the
  `deploys.log` line goes 139 → **140**.

### C6. Log kinds

- `black_bloc/logkinds.py`: `request.check_asked` is **routine** (`:281–287` block, beside
  `request.resumed`) — it is a nudge, not a decision.
- `tests/test_logkinds.py`: write the kind as a string LITERAL inside `kind_via(...)` —
  `_branches` (`:272`) unwraps `kind_via` and the AST walk (`:295`) then counts both
  `request.check_asked` and `web.request.check_asked` by itself, so `KNOWN_DYNAMIC` (`:42`)
  needs nothing. `ask_check` must not build the kind from a variable. Add `request.check_asked`
  to the quiet list in `test_a_request_is_loud_only_when_it_is_answered_or_fails` (`:654`).
  The checklist-34 AST guard must still pass (no route-side `note()`).
- `labels.js` kind label: "Requester asked to check" (find the `request.resumed` label and
  add beside it).

### C7. Tests (mirror the package, one file per source file)

| File | Cases |
|---|---|
| `tests/test_requests.py` | `LOOKS` ends with `check_asked` and every look has a colour, title, field tuple; `field_value("asked")` empty when `check_asked_at` is null, `@who · <t:…:R>` when set; `request_embed(move=CHECK_ASKED)` has the description and the five fields; `CARD_BUTTONS[REVIEW]` order is accept / check / sendback / hold / decline; `card_buttons(may_accept_here=False)` keeps `check`; `NOT_READY_TO_CHECK` names the button, not the dead subcommand |
| `tests/cogs/community/test_requests.py` | `ask_check`: (a) DM lands → one `request.check_asked` row with `told=dm`, `check_asked_by/at` set, status still `review`, the DM embed title is the new one and carries the site button; (b) DM refused + fallback on → `dm_failed` row + the channel `send` got `content` with the mention and `allowed_mentions.users == [requester]`, `told=channel`; (c) DM refused + fallback off → `told=nobody`, no channel send, text names the key; (d) off-review → refused in words, no row, no DM; (e) `request_channel_moves` including `check_asked` → plain card in the channel when the DM landed, and NOT a second post when the fallback already pinged; (f) `request_check_on_ready` on → `mark_ready` produces `request.review` AND `request.check_asked` rows, one DM; off → no ask; (g) the panel: a review card renders the button, a done/in-progress card does not, pressing it as a demoted member is refused by `still_staff` with nothing written; (h) `via` travels — the row's kind is `request.check_asked` from the panel |
| `tests/api/tools/test_requests.py` | `POST /check`: 200 with `message` and the two new row fields; 409 off-review; exactly ONE `action_log` row and its kind is `kind_via("request.check_asked", VIA_WEBSITE)` |
| `tests/test_settings_store.py` | two keys; `REQUEST_CARD_MOVES` has eight; default excludes both |
| `tests/storage/test_db.py` | schema 27 migration adds the two columns |
| `tests/test_logkinds.py` | classification + the static-kinds list |

### C8. Docs the build touches

`docs/access/sweeps.md` rows **66–68** (66: press Ask them to check on a review card as
staff → the asker's DM, the card's new field, one Requests-log row; 67: same with the asker's
DMs closed → the ping in the request channel; 68: `request_check_on_ready` on → mark one
ready → the DM arrives with no button pressed); `docs/access/OWNER_GUIDE.md` row count;
`docs/info/code-notes.md` `# Requests, sixth pass` section (the description-line `if`, the
`ping=` keyword on `post_line`, why `check_asked` is not in `DM_LOOKS`, the stale-string fix);
this file's `## Deviations` foot; `docs/info/README.md` row → BUILT; `docs/TODO.md` item
status. The conductor moves the item to `DONE.md` and re-keys `code-notes.md` at the merge.

## D. Calls the owner may overturn (each is one setting or one table line)

1. **Review only, not done** — add `MoveButton("check", …)` to `CARD_BUTTONS[DONE]` and the
   site's done bar if he wants "check the work" after acceptance too.
2. **Fallback ping default ON** — `request_check_fallback_channel` flips it.
3. **Auto-ask default OFF** — `request_check_on_ready` flips it.
4. **Channel copy default OFF** — tick `check_asked` in `request_channel_moves`.
5. **Re-asking allowed, no confirm** — the card shows the last ask, so a second press is a
   choice, not an accident. If he wants a confirm: a `NoteModal`-less "Ask again?" pair like
   the withdraw buttons (P9 in `panels-program.md`).
6. **The DM's wording** — `CHECK_ASKED_DESCRIPTION`; a settings-registry text key is a
   follow-up if he wants to edit it from the site.

## E. Out of scope (listed so nobody builds it by accident)

- **Reply buttons in the requester's DM** ("Works" / "Not yet" that move the request or leave
  a comment). Real value, but it is the first *member-facing persistent view* in the app —
  needs the `Panel` timeout story rethought for a DM that may sit for days (P12: 15-minute
  token window). Its own design doc, after this lands.
- Pinging **anyone but the requester**; pinging on any look but this one.
- A requester-side "I checked it" on the site (requesters mostly have no site access).

## F. Build brief essentials (the conductor's dispatch copies these)

Branch `feat/requests-check` from `main` at or after `46e3ba4`, in a worktree. Opus. Commit
at clean boundaries (pure module + schema → cog + tests → site + mock → docs). Gate before
reporting: `ruff check .`, `pytest -q -n auto` (expect **3371 + new**), `node
--input-type=module --check < site/public/assets/page-requests.js` and `labels.js`, `node
site/mock/check.mjs` against a running `site/mock/server.mjs` (expect 17 pages / **140**
routes). TEST_MODE stays on; nothing is posted anywhere but the test channel and DMs; no
`.env` read; no `git stash`/`git add -A`; near-zero comments — explanations to `code-notes.md`.
Report: what deviated from this doc and why, what was NOT verified, and the review link
`https://blackbloc.heygabi.ai/requests.html` (a review card, once deployed).

## Deviations

*(the build appends here — number them, say what the doc said, what was done, and why)*

Built 2026-09-03 on `feat/requests-check` (four commits off `59ac96f`). 3399 tests pass (was
3371), ruff clean, mock 17 pages / 140 routes. Everything below was found by running the code.

1. ⚠️ **`BackButton` moved from action row 0 to row 1 — the doc's §C1 button insert made the
   review card SIX items wide and discord.py refuses to build it.** `build_card`
   (`cogs/community/requests.py`) put every `CardMoveButton` and `Back` on `row=0`; a review
   card already carried four moves, and the fifth plus Back is `ValueError: item would not
   fit at row 0 (6 > 5 width)` out of `discord/ui/view.py:193`. Every review card in the panel
   would have crashed on render. Back now sits on its own row below the moves, and
   `test_the_card_renders_exactly_the_buttons_the_table_says` asserts both the ≤5 cap and
   Back's row so the next move added fails loudly in a test rather than in production.
2. **`CARD_BUTTONS[REVIEW]` shipped in commit 2 with `MOVE_FUNCS`, not in commit 1 with the
   rest of the pure module.** §F's boundaries put the table in the first commit, but a table
   naming `"check"` with no `MOVE_FUNCS["check"]` behind it is a `KeyError` in `run_move` —
   the intermediate commit would have been broken. Same reason moved `logkinds.py`'s
   classification into commit 2: `test_every_emitted_kind_is_classified` fails the moment the
   cog emits a kind the module has not classified.
3. **The two settings keys shipped in commit 2 as well, not commit 3.** `SettingsStore.set`
   validates against `KEY_TYPES`, so the cog tests for the fallback and the auto-ask cannot
   set a key that is not registered yet. The registry entry belongs with the code that reads
   it; commit 3 stayed the API + site half.
4. **§C6's third bullet — "`labels.js` kind label: *Requester asked to check*" — was not
   done, because there is no such table.** Verified: `site/public/assets/labels.js` holds
   SETTINGS-key labels only (`LABELS` + `humanLabel`), and the Logs page renders a kind as its
   raw string (`logs.js:57` `kindPill`, `text: String(row.kind)`), with the filter chips built
   from the kinds a feature has actually logged. There is nowhere to put a per-kind label
   without inventing a table, which is a change to every feature's logs, not to this one. The
   two SETTINGS labels §C4 asks for were added there as specified.
5. **`ask_check` step 8 is `if told != "channel": await notify_move(...)`, without repeating
   the `posts_a_card` test the doc spells out.** `notify_move` already asks `posts_a_card`
   itself as its first line; asking twice is the same gate in two places (checklist 15). The
   behaviour is identical — the channel copy is opt-in and never doubles the ping.
6. **`mark_ready` returns the row the auto-ask left, not the row `apply_decision` returned.**
   §C3 says only that the reply text stays `READY_SAID`. It does — but `finish_card` re-renders
   the card from the returned row, and the row from before the ask has no `check_asked_at`, so
   the new "Asked to check" field would have been missing until the next refresh. It now uses
   `ask_check`'s own fresh row when the ask happened.
7. **The site chip reads "asked by X · 3 minutes ago", not §C5's "asked {check_asked_by_name}".**
   `check_asked_by_name` is the STAFFER who asked, so "asked Lead" reads as though Lead were
   the person being asked. Two extra characters remove the ambiguity.
8. **`askedChip` was added to the shared `headBlock`, not mirrored separately onto the done
   card.** §C5 says to find where `readyChip` is used in the finished list and copy it —
   `readyChip` is not used there at all; done/declined/withdrawn cards all render through
   `headBlock`, which `boardCard`, `openCard` and `heldCard` share. One call there covers the
   finished list, and rows that were never asked have no chip anyway.
9. **The mock's `REQUEST_NOT_READY` gained a `{doing}` placeholder** (via a new `notReadyToCheck`
   helper) rather than a second near-identical constant, matching `NOT_READY_TO_CHECK`'s own
   shape now that two routes refuse with it. Its stale `/request ready` sentence was fixed at
   the same time as the Python one.
10. **The `check_asked_*` fields were also added to `contract.json`'s list and single-request
    row shapes**, not only to the new route's. The page's chip reads them off list rows, so the
    contract that guards "every key the page reads" has to cover them there too.
11. **`SCHEMA_VERSION` is 27 as the doc says, and `feat/applications-no-role` claims 27 too.**
    Whichever merges second re-keys to 28 — recorded here so the merge does not have to
    rediscover it.

**Not verified** (no live Discord and no deploy from this build): the `check_asked` embed by
eye; whether a closed-DM member's `user.send` raises what `dm()` expects (it treats any
exception as "not told", so the fallback does not depend on which); the real channel ping
reaching the right person; the site button and chip on the deployed page. Those are sweeps
[66–68](../access/sweeps.md).
