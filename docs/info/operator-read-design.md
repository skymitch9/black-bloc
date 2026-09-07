# Operator read token — how a Claude session sees live state

> **Audience:** Claude sessions first, the owner second. **Status:** TRACKED —
> secret NAMES only, never values.
> Last verified: **2026-09-06** — `OPERATOR_READ_TOKEN` was minted and the live
> suite run against the deployed app for the FIRST time at 13:55 (v97). What it
> found, and what changed because of it, is the dated note at the foot; the two
> superseded claims in the 2026-09-03 header below are marked where they sit.
> Measured on branch `operator-bucket`: `ruff check .` clean, `pytest -q -n auto`
> **5279 passed** both orders (5277 before). ⚠️ **NOT verified on this branch:**
> the live suite — a worktree holds no token, so `pytest -m live` has not run
> against the fix.
>
> Before that, **2026-09-03** — written by the build that landed it, against its
> own branch. Measured here: `ruff check .` clean, `pytest -q -n auto` **3710
> passed** (3697 on `main` before), and `scripts/read.ps1` exercised on all three
> of its branches — no token, a wrong token against the LIVE app (it answered
> `not_signed_in`, which is the proof that an unconfigured server is unchanged),
> and `/health`.
> **2026-09-06 13:54 — FIRST LIVE RUN.** The owner minted the token (Q5, "A") and v97 carried it
> live. Measured: `scripts/read.ps1 -Path /api/requests` answered the JSON; one `web.operator.read`
> row per read with `via: operator` and `path=…` (read back through `/api/actions?kind=web.operator.read`);
> `pytest -m live` **20 passed / 38 failed / 1 skipped** — the failures are two defects, on TODO for v98:
> the guess bucket (decision 6) charges MATCHING tokens too, so a 60-path sweep 429s after ~30, and its
> sentence says *sign-in attempts*; and the write-refusal test meets `cross_site` before the operator gate.
> ⚠️ Still NOT verified: the `logs.js` pill was not opened in a browser (sweep row 103's Logs-page half).

## Why

Owner, 2026-09-03 14:24: *"Make apis that you can access so you can see things.
Or use my explicit permission to check it."*

Until now, a session that wanted to know what the bot actually holds — which
requests are open, what a setting is set to, what the last fifty log lines say —
had one route: `flyctl ssh console` into the machine and query SQLite by hand.
The permission classifier blocks that about half the time, and the half it blocks
is not predictable, so a read that should cost one command costs a negotiation.

The dashboard already serves every one of those answers as JSON, to a browser
holding a staff cookie. The whole feature is: **let a session present a secret
instead of a cookie, and refuse it anything but a look.**

## The decisions

| # | Decision | Why this and not the other thing |
|---|---|---|
| 1 | **One secret, `OPERATOR_READ_TOKEN`, sent as `Authorization: Bearer`** | No new endpoints and no second auth system — the same JSON the dashboard reads, through the same routers. A header is what a script can send; a cookie is what a browser can. |
| 2 | **Unset = the door does not exist** | With no token configured the bearer is ignored entirely and the request falls through to the cookie path unchanged. A server that has never heard of this feature behaves exactly as it did before it landed — verified live, see the header. |
| 3 | **Shorter than 32 characters = unset, with a warning at load** | Same rule and same wording style as `SESSION_SECRET`. A typo must not leave a guessable door open, and it must say so out loud rather than failing silently. |
| 4 | **GET and HEAD only; every other method is 403 in words** | The method is the whole permission model. It is checked in one place, before any route body runs, so a write route cannot forget it. |
| 5 | **`hmac.compare_digest`, on UTF-8 bytes** | Constant time, and the byte form is what stops a non-ASCII header being a `TypeError` (the same trap `state_matches` was fixed for). |
| 6 | **A per-IP `TokenBucket`, 30 a minute** | A guess costs something. The numbers are the login limiter's shape with a rate that suits a human-driven session rather than a sign-in. Its own bucket, so guessing here cannot lock anybody out of signing in. |
| 7 | **No `sessions` row** | The operator identity is not a session: there is nobody to sign out, nothing to revoke per-device, and `sessions.alive` is skipped. Revocation is `flyctl secrets unset`, which is immediate and total. |
| 8 | **The identity is `staff: True`, `member: False`, `operator: True`** | It carries the SAME keys `current_session` returns, so `staff_dependency` admits it to every staff GET and no consumer needs to know it exists. `member: False` is deliberate: `/api/requests/mine` is a person's own list, and the operator is not a person. |
| 9 | **One `web.operator.read` row per request, details `{path, via}`** | Checklist 34. It is written from the dependency, once per request (`request.state` guards a route whose gate runs twice, e.g. `/api/members`), never from route code — so a new GET route is logged the day it is added. |
| 10 | **`via` gets a third word, `operator`** | The Logs page already answers "who did this" with Discord / Website. A read by a session is neither, and rendering it as one would be a lie. |
| 11 | **Routine, on the `core` feature** | `feature_of("web.operator.read")` falls through to `core` because `operator` is not in `HEADS` — no table entry needed, and `core_log_level` governs whether Discord echoes it. It is in `ROUTINE`, so at the default level Discord stays quiet and the DB row is still always written. |
| 12 | **The ON/OFF is the secret itself — no settings key for it** | Deliberate, and this row is the documentation checklist 33 asks for. A key that could re-open a door the owner had unset would be a worse switch than the secret; `flyctl secrets unset` is the off switch and it cannot be undone from inside the app. |
| 13 | **`operator_read_log` (core, default `true`) IS a registry key** | The one decision the secret does not make: whether a read leaves a line. It reaches the Settings page and `/settings set-value` for free by being in the registry. False reads the same data and writes nothing. |

## The refusal words

Every one is a sentence: what happened, what it needs, how to get it.

| When | Status / error | What it says |
|---|---|---|
| The token does not match | `401` `bad_operator_token` | *That operator token is not the one this server holds, so nothing was read. It is the OPERATOR_READ_TOKEN secret rather than a sign-in, so no account is locked out — check the copy in BLACK_BLOC_OPERATOR_TOKEN, and ask the owner to set a fresh one if it has been rotated (docs/access/operator-read.md).* |
| Too many **wrong** tokens from one IP | `429` `slow_down` | Its own sentence, `OPERATOR_SLOW_DOWN` — *That is more wrong operator tokens from this address than Black Bloc will take in a minute, so nothing was read. It is the OPERATOR_READ_TOKEN secret rather than a sign-in, so no account is locked out and signing in still works — wait a minute, then send the token the mint command set (docs/access/operator-read.md).* ⚠️ A **matching** token never reaches this row; see the 2026-09-06 note at the foot |
| A good token on a write | `403` `operator_read_only` | *The operator token can only look, never change, so nothing was done and nothing was logged as a change. Make this change on the dashboard or in Discord, where a person signs for it.* |
| No token configured | — | Nothing of its own: the request falls through and gets whatever the cookie path would have said (`not_signed_in`, and so on). |

`scripts/read.ps1` prints the `message` field of any non-2xx, so what a person
sees in the terminal is one of these sentences, never a status code or a trace.

## Why this is safe

- **Read-only by METHOD, decided in one place.** `GET`/`HEAD` is checked in
  `operator_session`, before `current_session` returns and therefore before any
  route body, any dependency that follows it, or `WebActor` exists. A test
  monkeypatches `WebActor` to fail on construction and PUTs with a valid token:
  the refusal arrives first.
- **Verified by grep that no `/api` GET or HEAD route writes.** An AST walk of
  every `@router.get`/`@router.head` under `black_bloc/api/`, following
  same-module helpers, found **no** write on any route that consults
  `current_session`. See the finding below for the two that do write and are not
  reachable this way.
- **Constant-time compare on bytes**, so neither timing nor a non-ASCII header
  is an oracle.
- **Per-IP bucket** on the guesses, on the bot object rather than the router, so
  the limit is one limit however many routers a guess is aimed at.
- **No session row**, so there is no state to steal, replay or forget to revoke.
  The off switch is the secret, and `flyctl secrets unset` is total.
- **The secret never reaches a log row.** The `web.operator.read` details are
  `{"path": …, "via": "operator"}` and nothing else; the refusal sentence names
  the secret but never carries a value; `secret_rows` on the Costs page reports
  set/unset by name, and its test asserts no value can reach it.
- **A refused token writes nothing at all** — the row is written only after the
  compare and the method check both pass.

## The finding this build did NOT fix

`GET /api/auth/login` and `GET /api/auth/callback` DO write — a state cookie and
a `sessions` row respectively. They are GETs by Discord's OAuth design, not by
ours. **Neither calls `current_session`**, so the operator identity never reaches
them and a bearer sent to either is ignored entirely: the request is an ordinary
unauthenticated OAuth step. They are reported here rather than changed.

## Deviations

1. **The Via word is `Operator token`, not `the operator token`.** The brief gave
   both the literal string and the instruction to match the style of the existing
   words. `VIA_WORDS` renders into a pill on the Logs page beside `Discord` and
   `Website`, and into `via {word}` in a Discord log line; a lower-case article in
   that column reads as a bug. `via Operator token` was chosen.
2. **A dedicated bucket at 30/minute rather than reusing `LOGIN_RATE` (10).** The
   brief allowed either. Ten a minute is a sign-in rate, not a reading rate, and
   sharing the login bucket would let guessing here lock a person out of signing
   in. `OPERATOR_RATE` is exported so the test names the number rather than
   repeating it.
3. ⚠️ **SUPERSEDED 2026-09-06 — see the note at the foot.** It read: *a token is
   consumed on every bearer request, not only on a mismatch; `TokenBucket` has no
   peek, and a peek-then-take would be two homes for one decision. At 30/minute
   the cost to a legitimate session is nothing.* The first live run showed the
   cost to a legitimate session is not nothing: the read sweep is ~60 paths and
   429'd after thirty. Only a mismatch charges the bucket now.
4. **`SESSION_SECRET_MIN` is reused as the operator minimum** rather than getting
   a second constant. One fact, one home; the name says `SESSION` and the note in
   `code-notes.md` says why it is shared.
5. **A cross-site write carrying a bearer is refused earlier, and differently.**
   `server.py`'s `same_site_writes` middleware runs before any dependency, so a
   PUT with a bearer and no same-origin header gets `403 cross_site`, not
   `403 operator_read_only`. Both are refusals in words and both leave the write
   undone; the middleware is not weakened to make the message tidier.
6. **`operator_read_log` was added to `CORE_KEYS`.** `namespace_of` reads the
   first word of a key, which would have put it in a namespace of its own called
   `operator`. The brief asked for `core`, and `CORE_KEYS` is how a key that does
   not start with `core_` gets there.

## 2026-09-06 — what the first live run found

Written on branch `operator-bucket` off `main` at `6216e97` (v97 live). The
token was minted and the live suite run for the first time on 2026-09-06 13:55,
against the deployed app. Two things the build could not have known:

### 1. The guess bucket was charging good tokens

`operator_session` took a bucket token **before** comparing, so every bearer —
matching or not — spent one of the 30-a-minute per-IP tokens. The live read
sweep (`tests/live/test_reads.py::test_every_read_the_pages_make_answers…`, one
case per GET in `contract.json`, about sixty of them) hit `429` after thirty.
Decision 6 says *a guess costs something*; a WRONG token is a guess and a right
one is not, so the ordering was the bug and the decision was right.

**The ordering now, and why it leaks nothing.** The compare is still first and
still `hmac.compare_digest` on UTF-8 bytes. Only the mismatch branch reads
`client_ip`, takes the bucket and refuses — `429 slow_down` when the bucket is
empty, `401 bad_operator_token` when it is not. A matching token never calls
`operator_bucket_for`, so on a server nobody has guessed at, the bucket object is
never even built. The only thing an attacker learns from `429` versus `401` is
that the bucket is empty, which he emptied himself; both answers mean *wrong
token*, and neither is reachable with a right one. The compare itself is
constant time, so no byte-level oracle exists either way. ⚠️ The honest caveat:
a mismatch now does slightly MORE work than a match (a header read, a dict
update, a log line), so the two paths differ in wall-clock time — but that
distinction is already public in the status code, and it is not a per-byte
signal.

### 2. An exhausted bucket does NOT block a right token — deliberate

The bucket is **per IP**, so a shared address (an office, a VPN exit, a Fly
region) means one person's guessing could otherwise lock a real operator out.
Taking decision 6 at its word — the bucket exists to *price guesses* — a correct
token is proof the caller is not guessing, so it passes while that IP is out of
guesses. Nothing is weakened: wrong tokens from that IP keep getting `429` and
still cannot be burned without limit, which is the whole property the bucket was
for. `tests/api/test_auth.py::test_a_right_token_still_reads_while_that_ip_is_out_of_guesses`
pins it, and `…::test_the_right_operator_token_never_costs_a_bucket_token` reads
forty times in a minute and asserts the bucket was never created.

### 3. The 429 sentence is the operator's own, not the sign-in one

`SLOW_DOWN` says *"That is more sign-in attempts than Black Bloc will take in a
minute"*. On a token read that names the wrong cause — there was no sign-in
attempt, and a reader chasing a locked account is chasing nothing.
`OPERATOR_SLOW_DOWN` says what happened (too many wrong operator tokens from
this address), what it is about (the `OPERATOR_READ_TOKEN` secret, not an
account, and signing in still works), and what to do (wait a minute, send the
token the mint command set). The refusal table above carries the new row and so
does `../access/operator-read.md`.

### 4. The live write-refusal tests were watching the wrong gate

`tests/live/test_selftest.py::test_the_operator_token_can_read_the_runs_but_never_start_one`
asserted `operator_read_only` on `POST /api/selftest`, but the live host answered
`403 cross_site` first: `server.py`'s `same_site_writes` middleware runs before
any dependency, exactly as Deviation 5 above says it does. Both are refusals in
words and both leave the write undone, so nothing was broken — but the test's
point is that the OPERATOR gate refuses writes, and it was never reaching it.
The two write tests (the other is in `tests/live/test_refusals.py`) now send the
dashboard's own headers through `conftest.same_site_headers()`. The middleware
is still not weakened.

⚠️ **Deviation:** `same_site_headers()` sends **both** `origin` (derived from
`BLACK_BLOC_LIVE_URL`) and `sec-fetch-site: same-origin`, where the brief asked
for the Origin alone. A real browser sends both, `same_site` accepts either, and
the Origin path needs `BLACK_BLOC_LIVE_URL` to match `settings.origin`
character for character — which this branch could not verify, having no token.
Sending both means a hostname that differs by a trailing slash or a `www.`
cannot silently put the test back on the wrong gate.

⚠️ **NOT verified here:** nothing on this branch has met the live host. A
worktree has no operator token, so `pytest -m live` was not run; the conductor
runs it after the deploy. Measured on the branch: `ruff check .` clean, and
`pytest -q -n auto` **5279 passed** forward and with `BB_REVERSE=1` (5277 on
`main` before; the two new ones are the bucket tests above).

## 2026-09-06 19:35 — the operator read bound (design for branch `operator-read-bound`)

> Written by the conductor against `main` at `571e581` (v98 live). Owner decision 19:30, verbatim
> *"Do a"* — the first of the two fix shapes named on `TODO.md`: hang the read limiter on the operator
> identity where the operator is admitted. Every `path:name` below was read in that tree.

### What exists

- `api/writes.py:read_bucket_for` — ONE per-bot `TokenBucket(READ_RATE=300, READ_WINDOW_SECONDS=60)`
  keyed by identity, charged only inside `writes.py:reader_dependency` (`take(str(who["id"]))`, else
  `429 slow_down` with `TOO_MANY_READS`). `reader_dependency` is used by `api/ref.py` wholesale and by
  the `reader`-taking routes of `status.py`, `costs.py`, `tools/chat.py`, `tools/chat_memory.py`,
  `tools/members.py`, `tools/mod.py`, `tools/requests.py`. Everything gated by `auth.py:staff_dependency`
  ALONE (`/api/settings`, `/api/selftest`, most of `status.py`, every tools router's plain GETs) has no
  per-identity read bound.
- `api/auth.py:operator_session` — admits the operator with `dict(OPERATOR_WHO)` (`id == "0"`) after the
  compare, the `READ_METHODS` check and `note_operator_read`. Since v98 a right token touches no bucket
  at all, so an operator loop on a `staff_dependency`-only route is bounded only by the server.
- Import direction: `writes.py` imports from `auth.py`; `auth.py` must not import `writes.py`.

### Rules

1. **One bucket, one home.** Move `READ_RATE`, `READ_WINDOW_SECONDS`, `READ_BUCKET_ATTR`, `TOO_MANY_READS`
   and `read_bucket_for` from `writes.py` into `auth.py` (beside `operator_bucket_for`, which already has
   the same shape); `writes.py` imports them back and keeps re-exporting the names in `__all__`, so every
   existing import (`from .writes import READ_RATE` in tests, if any — grep) still resolves. No second
   `TokenBucket` for reads anywhere.
2. **Charge the operator where it is admitted.** In `operator_session`, after the `READ_METHODS` check and
   BEFORE `note_operator_read`: `if not read_bucket_for(bot).take(OPERATOR_WHO["id"]): raise Refused(429,
   "slow_down", TOO_MANY_READS)`. Order matters: a refused read logs no `web.operator.read` row (the
   docstring on `note_operator_read` promises "never one for a refused token"; extend it to a refused
   read). The key is the operator IDENTITY, not the IP — a staff member's own reads and the operator's
   never drain each other, and two operator terminals share one budget, which is the point.
3. **Charge each read once.** `reader_dependency` must not charge the operator a second time on the
   routes that use it: skip the `take` when `who["id"] == OPERATOR_WHO["id"]` (compare against the
   constant, never a literal `"0"`). A staff session is charged there exactly as today.
4. **The sentence is `TOO_MANY_READS`, reused.** It names the cause correctly (*more of this than Black
   Bloc will look up in a minute*) and says nothing is wrong with the account, which is true of the
   token too. If the build finds *open the page again* misleads a terminal reader, add ONE clause to the
   existing sentence rather than a second constant — one refusal, one sentence.
5. **No new setting, no new log kind.** The rate is the existing `READ_RATE` and the decision to bound
   reads was made when `reader_dependency` was written; checklist 33 asks nothing new, and a rate-limited
   read is logged (`log.warning`, like `reader_dependency`), never an `action_log` row (34).
6. **The guess bucket is untouched.** `operator_bucket_for` still prices wrong tokens per IP; this adds
   the right-token bound that v98 deliberately removed from it. The two are different questions (is this
   caller guessing? / is this caller reading too much?) and stay two buckets.

### Tests (mirror the package)

`tests/api/test_auth.py`: 301 right-token reads in one minute → the 301st is `429 slow_down` with
`TOO_MANY_READS`, and NO `web.operator.read` row is written for it (count rows: 300); the bucket key is
`OPERATOR_WHO["id"]` (a staff session's 300 reads in the same minute do not touch the operator's budget,
and vice versa); a right token on a `reader_dependency` route (`/api/ref/roles` is the cheapest) costs
ONE token per request, not two. `tests/api/test_writes.py`: `reader_dependency` still charges a staff
session; the moved names import from both modules. Do NOT add a live test — 300 reads against the real
host is not a test anyone should run on every push; `pytest -m live` must stay at 58 passed / 1 skipped.

### Prove before merge, and the sweep row

`ruff` clean; full suite `-n auto` forward and `BB_REVERSE=1` (5279 + yours — say the number); `node
site/mock/check.mjs` ok (routes stay 150 — say so); `python -m black_bloc` NOT booted in a worktree — say
so. One sweep row lettered `RB-a` in `docs/access/sweeps.md`: from a terminal, 301 `scripts/read.ps1
-Path /api/status` calls inside one minute → the 301st prints the `TOO_MANY_READS` sentence, and the Logs
page shows exactly 300 `web.operator.read` lines for that minute. Code notes: `# Operator read bound` at
the foot of `code-notes.md`, keyed by name. Refusal tables in this file (§ *The refusal words*) and in
`../access/operator-read.md` gain the row. Add a `### Deviations` under this section for anything that
differed, and why. The conductor writes `TODO.md` / `DONE.md` / `deploys.log` / `architecture.md`.
