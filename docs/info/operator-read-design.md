# Operator read token — how a Claude session sees live state

> **Audience:** Claude sessions first, the owner second. **Status:** TRACKED —
> secret NAMES only, never values.
> Last verified: **2026-09-03** — written by the build that landed it, against its
> own branch. Measured here: `ruff check .` clean, `pytest -q -n auto` **3710
> passed** (3697 on `main` before), and `scripts/read.ps1` exercised on all three
> of its branches — no token, a wrong token against the LIVE app (it answered
> `not_signed_in`, which is the proof that an unconfigured server is unchanged),
> and `/health`.
> ⚠️ **NOT verified:** nothing here has run with `OPERATOR_READ_TOKEN` actually
> set on the live app — the owner mints it (`access/operator-read.md`), and until
> he does, the whole feature is inert in production. No `web.operator.read` line
> has ever been seen on the real Logs page; no rate limit has been hit by a real
> client; the `logs.js` pill was not opened in a browser.

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
| Too many guesses from one IP | `429` `slow_down` | The existing `SLOW_DOWN` sentence, unchanged — *That is more sign-in attempts than Black Bloc will take in a minute…* |
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
3. **A token is consumed on every bearer request, not only on a mismatch.**
   `TokenBucket` has no peek, and a peek-then-take would be two homes for one
   decision. At 30/minute the cost to a legitimate session is nothing.
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
