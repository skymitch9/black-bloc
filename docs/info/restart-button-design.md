# Restart the bot — a button on the Overview page

> **Audience:** whoever touches the restart path next, and the owner. **Status:** TRACKED ·
> **BUILT on branch `small-fixes`** (off `main` `552af36`, fix 4 of 4) · **Last verified:
> 2026-09-20** — the route, the module and the page were exercised by the suite and by a
> headless browser against `site/mock/server.mjs`. ⚠️ **NOTHING HERE HAS MET FLY OR DISCORD.**
> No process has been restarted by pressing it, no `core.restart_requested` row has been read on
> the live Logs page, and the claim that Fly starts a fresh machine on a non-zero exit is read
> off Fly's restart policy (`on-failure`, 10 retries), not measured. The sweep rows (`SF-c` in
> [`../access/sweeps.md`](../access/sweeps.md)) are how that gets checked. Secret NAMES only.

## The ask

Owner, 2026-09-18 10:4x, verbatim: *"is the website down when the bot is down? id like to have a
bot restart button on the dhasboard if not"*. Queued the same day (*"add it to the future
todos"*), designed on [`../TODO.md`](../TODO.md), built 2026-09-20.

## What it can and cannot do — the measured shape

**The dashboard is served BY the bot process.** `bot.py:setup_hook` calls `_start_api()`, which
runs uvicorn as a background task inside the same process, on one Fly machine. So:

| Case | What happens | Who fixes it |
|---|---|---|
| The bot is UP but stuck (a dead gateway, a wedged loop, a cog that stopped) | The site answers, so the button is reachable | **This button** |
| The process has crashed | The site is down with it, so no button anywhere can be pressed | Fly's restart policy: `on-failure`, 10 retries |
| The process exits CLEANLY (code 0) | Fly does **not** start it again | Nobody — which is why the button exits **non-zero** |

🔴 **The non-zero exit is the whole mechanism, not a detail.** `fly.toml`'s restart policy is
`on-failure`; a clean shutdown that returns 0 would take the bot down and leave it down.
`errors.py:EXIT_RESTART = 4` is what `restart.shut_down` hands to `bot.exit_now`.

## How it is built

| Piece | Where |
|---|---|
| The words, the permission check, the shutdown, the exit code | `black_bloc/restart.py` |
| `POST /api/bot/restart` | `black_bloc/api/bot_api.py`, registered in `api/server.py` |
| The way out of the process | `bot.py:__init__` sets `self.exit_now = os._exit` |
| The button, the confirm, the outcome | `site/public/assets/page-overview.js` (`restartCard`) |
| The lower environment's copy | `site/mock/server.mjs`, `POST /api/bot/restart` |
| The row's classification | `logkinds.py` IMPORTANT — `core.restart_requested` |

**The route, in order:** staff (the router's own dependency) → the write rate limit
(`writer_dependency`) → **Manage Server, computed from the member's `guild_permissions`** →
*can this process restart itself at all* → one `web.core.restart_requested` action-log row naming
who and how long → `restart.schedule(bot)` → answer 200 with the sentence. **Nothing is posted to
Discord.**

**The shutdown, in order:** wait `ANSWER_GRACE` (1 s) so the answer reaches the browser before
the socket serving it dies → `bot.close()` under a 10 s timeout, which is the DND-style clean
shutdown the bot already had (`bot.py:close` → `_say_shutting_down()` → cancel the visibility
task → cancel the background tasks → close the database → `super().close()`) → `exit_now(4)` in a
`finally`, so a close that raises or hangs still exits.

## Deviations

1. **There was no "Manage Server" dependency in `api/auth.py` to reuse.** The brief said to find
   the existing one; the most privileged gate that exists is `staff_dependency` /
   `writer_dependency` (staff = a staff role **or** Manage Server), and the only Manage Server
   check on the site is `api/tools/guides.py:_may_edit`, written inline for the same reason. The
   route does the same thing through `restart.manages_guild(member)` — the **computed**
   permission off the cached member, never a role name (checklist 21). Worth extracting into
   `auth.py` the second time somebody needs it; one caller is not a pattern.
2. **The button is rendered for every staffer, not only for Leads.** `/api/auth/me` carries no
   Manage Server flag, so the page cannot know; adding one is a change to a route every page
   reads. Instead the card says *"Only somebody with Manage Server can do this"* under the
   button, which is the global rule's second branch (*never hide so much that the page looks
   broken; say "this is for admins"*), and a staffer who presses it gets the refusal in words —
   never a bare 403.
3. **No contract row for `POST /api/bot/restart`, deliberately.** `tests/api/test_contract.py`
   runs every row in `site/mock/contract.json` against the REAL app and requires 200; this route
   either refuses (the fake bot has no `exit_now`) or, if it were given one, would close the
   module-scoped app the other 199 rows share. The mock route exists so the page works in the
   lower environment and `check.mjs` stays green; the route's own tests
   (`tests/api/test_bot_api.py`) cover the four answers.
4. **"Refused while a deploy is mid-flight" was DROPPED: it is not detectable from inside the
   process.** `release.json` is baked into the image and says what THIS process shipped as, not
   what is being built; `/health` is this process answering about itself; a Fly deploy is a new
   machine the running one is never told about. Nothing in the bot can see a build in flight, so
   rather than a check that is really a guess, there is none. The honest mitigation is the
   deploy's own behaviour: a deploy replaces the machine anyway, so a restart pressed during one
   is at worst redundant.
5. **`bot.exit_now` is an attribute on the bot, and its absence is a refusal.** The alternative —
   `os._exit` imported in the route — would have exited the test runner the first time a suite
   touched the route. Only `BlackBlocBot` sets it; every test double must opt in, which is why
   `test_a_bot_with_no_way_out_refuses_instead_of_pretending` exists.
6. **The 15 seconds is written twice** — `restart.DOWN_SECONDS` for the answer, `RESTART_SECONDS`
   in `page-overview.js` for the confirm, which has to name the downtime BEFORE the request is
   made. The page prefers the server's sentence once it has one (`found?.message || …`).
7. **The words are constants, not settings keys.** The every-word-editable rule (owner,
   2026-09-17) covers what the BOT POSTS; this posts nothing to Discord, and its words are a
   site control's own labels, like every other button on the dashboard.
8. **The row is stored as `web.core.restart_requested`** — the site is the only door, so it takes
   the website head like every other route-only write (checklist 34); `bare()` reduces it to
   `core.restart_requested`, which is what `logkinds.IMPORTANT` lists and what the Logs page
   filters as `core`.

## What was NOT verified

- **Fly.** No deploy, no restart, no `flyctl releases`, no machine event. The restart policy was
  read from the TODO's 2026-09-18 measurement (`on-failure`, 10 retries), not re-read today.
- **Discord.** Nothing was sent; the DND shutdown presence is `bot.close()`'s existing behaviour
  and was not watched happening.
- **The real 15 seconds.** The number is the TODO's estimate of a Fly restart, not a measurement.
- **A real browser.** Everything visible here was exercised in `chrome-headless-shell` against
  the mock: the card renders, the confirm names the downtime, the POST answers, the outcome
  sentence appears. Nobody has looked at it at a real width.
- **A staffer without Manage Server pressing it in the live site.** The refusal is covered by a
  test against the fake guild, not by a person.
