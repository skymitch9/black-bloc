# Runbook — day-to-day operation of Black Bloc

> **Audience:** the owner (also away from the machine) and Claude sessions. **Status:** TRACKED
> (owner, 2026-08-31 — permanently; the purge-vs-keep question is settled, `docs/` stays in git).
> Secret NAMES only. Last verified: **2026-09-19** — the docs staleness pass after the
> **TEST_MODE lift**. Re-measured off `main` `ffea17e`, which **IS** the live shape (**v141**,
> release `2e48d7c`, deployed 2026-09-18 16:55): `SCHEMA_VERSION` **45** (said 34),
> `len(bot.COGS)` **22** (said 19), `tests/test_bot.py:TOP_LEVEL_NOW` **32** with zero groups
> (said 29), `len(settings_store.KEY_TYPES)` **277** (said 202), `../deploys.log` **140** lines
> last **v141** (said 107 / v108). ⚠️ **The *Test policy* row was the most dangerous stale line
> in this file** — it told an operator the bot speaks only in `#blackbloc-logs`, and it has not
> since 2026-09-18 16:08; the failure table's *"expected until TEST_MODE is lifted"* row went
> with it, and the boot-sequence and secrets paragraphs still described the removed YouTube
> uploads half (v139). ⚠️ **NOT re-measured today:** the flyctl commands, the machine/volume ids,
> the rest of the failure table and the laptop/phone steps — still the 2026-08-27 reading;
> `site/mock/contract.json` was **not** re-run (the mock needs a listening server); nothing ran
> against live Discord or a browser, and `/health` was the only live thing read (it answered
> `ok:true, ready:true, guilds:1` on 2026-09-19). Before that,
> **2026-09-11 08:35** — re-measured off `main` `1d090e5`, which
> **IS** the live shape (**v108**, merge `73e2e44`, deployed 2026-09-11 00:37): `SCHEMA_VERSION`
> **34**, `bot.py:COGS` **19**, **29** top-level slash commands with **zero** groups left, **202**
> registry keys, `site/mock/contract.json` **17 pages / 150 routes**, `pytest -n auto` **5,546
> passed**. The GitHub row and the laptop section were corrected: the repo has been **PUBLIC since
> 2026-09-10 20:06**, and `docs/` is tracked **permanently**, not "temporarily". ⚠️ **NOT
> re-measured today:** the flyctl commands, the machine/volume ids, the failure table and the
> laptop steps — those are still the 2026-08-27 reading; the phone-side steps (Discord app) are
> what the owner did, not measured by Claude; and nothing in this pass ran against the live Fly
> app, live Discord or a browser (the boot line below is what the last deploy's log showed, not a
> boot taken today). Before that, **2026-09-02** — measured on the **Phase 16** branch
> (`SCHEMA_VERSION` = 22; 17 pages / 116 routes; 16 cogs and 39 top-level commands).

## Where everything is

| Thing | Where |
|---|---|
| Bot process | Fly.io app `black-bloc`, machine `85e744c4d959d8`, region `lax`, volume `black_bloc_data` at `/data` |
| Database | SQLite `/data/black_bloc.sqlite3` on that volume (schema **45** — `black_bloc/storage/db.py:SCHEMA_VERSION`, measured 2026-09-19; it said 34, the 2026-09-11 reading. Landmarks on the way: 17 `sessions`, 18 `polls.vote_scheme`, 19 `golive_sessions.live_role_id`, 20 the Phase-14 chat tables, 30 the modmail ticket card, 31 the self-test, 34 `events.where_kind` + `where_channel_id`, 41 `requests.thread_id`, 43 the `moved_to` trail, 44 `meetings` + `meeting_lines`, 45 `events.review_kind`). Migrations are additive-only |
| Dashboard | https://blackbloc.heygabi.ai (same Fly app; Discord sign-in; staff roles = roles that can see `#blackbloc-logs`) |
| Health | https://blackbloc.heygabi.ai/health (public JSON: `ok`, `ready`, `guilds`, `latency_ms`) — and the dashboard's **Health** tab (loops, last 50 actions) |
| Logs | `flyctl logs --app black-bloc --no-tail` (below), the dashboard **Logs/Audit** tab, and `/<feature> logs` in Discord (Phase 12, live since 2026-08-27 18:38) |
| Test policy | ✅ **LIFTED 2026-09-18 16:08** — `TEST_MODE=false` on Fly (the owner's own `flyctl`, cutover **P5**). The bot speaks **wherever its settings point it**; the brake is each feature's own `*_mode`, and `shadow` sends the rehearsal copy to `shadow_channel_id` (`#welcome-test`). Events, requests and modmail are LIVE to members. ⚠️ Flipping `TEST_MODE` is the owner's, in **both** directions — never Claude. Was, until that moment: *`TEST_MODE=true`: the bot speaks only in `#blackbloc-logs` + DMs + the temp-voice channels it created* |
| Code | GitHub `skymitch9/black-bloc` — 🔴 **PUBLIC since 2026-09-10 20:06** (so Actions run again; `.env.enc` was purged from history first and is gitignored). `docs/` is tracked, so **never write a secret VALUE under `docs/`**. Branch `main`; every deploy line in [`../deploys.log`](../deploys.log) (**140** lines, last **v141**, counted 2026-09-19; it said 107 / v108) |

## The flyctl binary
The Claude session shells never have `flyctl` on PATH. Always spell it out:

```
"$LOCALAPPDATA/Microsoft/WinGet/Packages/Fly-io.flyctl_Microsoft.Winget.Source_8wekyb3d8bbwe/flyctl.exe"
```
(`winget install --id Fly-io.flyctl` on a new machine; then `flyctl auth login` in an interactive shell.)

## Agent worktrees on this machine (since 2026-09-06)
`.claude/` in this checkout is a Windows **junction** → `C:\lcw\onedrive-excluded\black_bot_baf\.claude`
(made 2026-09-06 ~00:20 alongside the same move for every sibling repo, so agent worktrees and
session state stay out of OneDrive; not in git, and the 13 older `worktree-agent-*` folders live
under the target). ⚠️ The Agent tool's own `isolation: "worktree"` REFUSES a junction
("`.claude` is a symlink"). Do not remove the junction — dispatch without isolation and have the
agent make its own worktree outside the checkout, the `C:/lcw/pool` precedent:

```
git -C <checkout> worktree add C:/lcw/<name> -b <branch> <sha>
```

The `.venv` stays in the main checkout; the agent confirms `import black_bloc` resolves to its
worktree before running pytest. Remove with `git worktree remove C:/lcw/<name>` after the merge.
Measured 2026-09-06 07:15 (first dispatch that hit the refusal: fixture-scope half A).

## Deploy (owner-authorised for Claude, 2026-08-27; MECHANICALLY GATED since 2026-09-02)
```
powershell -File scripts\deploy.ps1     # THE deploy path. Refuses a dirty tree or a red gate.
curl -s https://blackbloc.heygabi.ai/health
<flyctl> logs --app black-bloc --no-tail | grep -i "logged in\|synced\|error\|traceback" | tail
```
`deploy.ps1` runs ruff + pytest + `check.mjs`, pushes, deploys, and appends a
`deploys.log` skeleton line — EDIT that line (what shipped / what was verified)
and commit it. Escape hatch for a genuine emergency only: `BLACKBLOC_SKIP_GATE=1`.
Incident that made it a script: 2026-09-01, an ungated `;`-chain deployed on a red
suite. GitHub Actions (`.github/workflows/ci.yml`) also proves every push
independently — a red ✗ on main is a stop-everything signal.
A deploy restarts the bot (~10 s offline); expect one Fly proxy "refused connection" line in that window.
⚠️ **"the script died at `git push` with NativeCommandError but the push landed"** (2026-09-02,
Phase 16): PowerShell 5.1 + `$ErrorActionPreference = "Stop"` throws on anything git writes
to stderr — including the harmless `To https://github.com/…` progress line — so the run
stopped before `flyctl`. Fixed by routing the push through `cmd /c "… 2>&1"`. If it recurs
for another native command in the script, that is the cause; check `origin/main` before
assuming the push failed, then rerun the script (the gate reruns; it is idempotent).
It DID recur, 2026-09-11 09:27, on `flyctl` itself: the v109 run died on flyctl's first
stderr line (`==> Verifying app config`) with no release made (`releases` still said v108).
Same fix, same line shape — flyctl now runs through `cmd /c "... 2>&1"` too. If a third
native command is ever added to the script, wrap it the same way from the start.

## Restart / stop / start
```
<flyctl> machine restart 85e744c4d959d8 --app black-bloc
<flyctl> machine stop    85e744c4d959d8 --app black-bloc     # bot offline, site offline
<flyctl> machine start   85e744c4d959d8 --app black-bloc
```

## Roll back
Every deploy is a commit in `deploys.log`. To roll back: `git checkout <good commit> -- .` is NOT the way
(dirty tree); instead `git revert <bad merge> -m 1` (or `git reset --hard <good>` on a throwaway branch),
push, deploy. Schema migrations are additive-only, so an older build runs against a newer database.

## Reading the logs
```
<flyctl> logs --app black-bloc --no-tail | tail -50
<flyctl> logs --app black-bloc --no-tail | grep -i "error\|traceback"
<flyctl> logs --app black-bloc --no-tail | grep "database:"      # migrations on boot
```
Boot sequence to expect: `database ready` → `loaded cog …` ×**22** → `synced **32** app commands` → `logged in as
Black_Bloc#6132` → `birthdays: the daily import …` → `chat: seeded N intent(s)` (first boot per guild only).
(⚠️ **The counts said 19 / 29 until 2026-09-19** — that was the v108 reading; **22** is
`len(bot.COGS)` and **32** is `tests/test_bot.py:TOP_LEVEL_NOW`, both measured at v141. There is
**no `TEST MODE ON` line** on the deployed bot any more.)
⚠️ **The "no `YOUTUBE_API_KEY`, so uploads run on the public feed alone" line is GONE** — the
uploads half was removed at **v139** (2026-09-18 10:05,
[`../info/youtube-uploads-removal-design.md`](../info/youtube-uploads-removal-design.md)), and
the key IS set (2026-09-17 18:03). What a v139+ boot logs instead is one
`settings ignored: youtube_mode` line for the orphaned stored row — **that** is the normal state,
not a fault. KI-11 is CLOSED as moot.

## Secrets (names; custody in [`RECOVERY.md`](RECOVERY.md))
`DISCORD_TOKEN`, `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`, `SESSION_SECRET`, `POLL_VOTE_SECRET` (⚠️ losing it makes polls created under it unvotable — they refuse in words rather than double-count), `ANTHROPIC_API_KEY` + `GROQ_API_KEY` (chat LLM tiers, Phase 14 — unset means those tiers don't exist, never an error), `TWITCH_CLIENT_ID`,
`TWITCH_CLIENT_SECRET`, `YOUTUBE_API_KEY` (⚠️ **re-written 2026-09-19** — it said *"F3 upload
posts — OPTIONAL and not yet minted"*, and both halves of that are false: it was **minted
2026-09-17** and set on Fly 18:03, and there are no upload posts since **v139**. What it buys now
is the LIVE half — one `search.list` per broadcast to name the video, plus the `@handle` lookup;
unset, a live announcement links the channel's own `/live` page with the title *Live now*, which
is the designed keyless shape — **KI-30**, not KI-11), `TEST_MODE` (⚠️ **`false` on Fly since
2026-09-18 16:08**), `TEST_CHANNEL_ID` (⚠️ **whatever its value, it gates
nothing now** — `bot.guard` is `None` when `TEST_MODE` is false, so the id is inert; the
channel `#blackbloc-logs` is still where the self-test posts and where the log channel points,
but that is the `selftest_channel_id` / `log_channel_id` **settings keys**, not this secret.
⚠️ Whether the secret is still set on Fly was **not** checked — `flyctl secrets list` is the
answer),
`DEV_GUILD_ID`, `DATABASE_PATH`, and `OPERATOR_READ_TOKEN` (read-only API access for a session —
Fly-only, never in `.env`; [`operator-read.md`](operator-read.md)).
Set on Fly with `<flyctl> secrets set NAME=value --app black-bloc` (each set restarts the machine);
importing many: write an ASCII file and `cmd /c "<flyctl> secrets import --app black-bloc < file"` — a
PowerShell pipe adds a BOM and the first key is rejected as `﻿KEY`.

## Common failures and what they mean
| Symptom | Cause | Fix |
|---|---|---|
| Dashboard looks old / broken layout after a deploy | (fixed 2026-08-27) assets now stamped `?v=` + `no-cache`; if it recurs, hard-reload once | — |
| "This is for staff" on the dashboard | your roles cannot see `staff_channel_id` (⚠️ this row said *"the test channel"*, which is what that key pointed at before the cutover — **P3** re-points it at the real staff channel) | ask an Admin for the role; the page names the roles |
| `/rolemenu` missing from the slash list | `rolemenu_mode` is off (commands hide when off) | Dashboard → Role menus → switch on |
| A panel/announcement never appears, and the log shows `would_*` | ⚠️ **NOT test mode any more** (lifted 2026-09-18 16:08) — a `would_*` row now means the FEATURE's own mode is `shadow`, so the copy went to `shadow_channel_id` (`#welcome-test`) instead | look at `#welcome-test` first; if the wording is right, flip that feature's mode to `on` (Settings page, or its own panel). The cutover ladder is [`../info/cutover-plan.md`](../info/cutover-plan.md) §2 |
| A panel/announcement never appears and there is **no** log row at all | the feature's channel key is blank, or its mode is `off` | check the key on https://blackbloc.heygabi.ai/settings.html — after the lift several channel keys were deliberately cleared by hand (2026-09-18 16:1x) |
| `tempvoice.panel_failed` in the log | the Bots role lacks Send Messages in that voice channel | grant it |
| `role.changed_by_hand` has no actor | the Bots role lacks View Audit Log | grant it |
| Fly proxy `PU03 unreachable worker host` once | the 6-second restart gap | ignore unless it persists |
| `429` on startup sync | too many restarts in a short time (KI-2) | wait a few minutes |

## Local run (for testing without Fly)
```
.venv/Scripts/python -m black_bloc          # needs .env; TEST_MODE=true is still the LOCAL default
                                            # (.env.example ships it true) — production is false
node site/mock/server.mjs                   # dashboard against fake data on http://127.0.0.1:8788
```
Stop a leftover mock server on Windows: find the `node` PID on the port (`Get-NetTCPConnection -LocalPort 8788`) and `Stop-Process`.

## Docs bookkeeping
`scripts/doctools/move_done.py "<heading>" <note-file> "<TODO line prefix>" [...]` moves TODO items whole
into DONE with a landing note (append-only, newest first). Every ask goes on `TODO.md` the moment it is
mentioned; finished items move in the session they land.

⚠️ **"The merge commit vanished" → `git pull --rebase` flattens `--no-ff` merges.** Twice on
2026-09-05/06 a build was merged with `git merge --no-ff`, docs were written naming the merge sha, and
the pre-push `git pull --rebase --autostash` replayed the branch commits linearly (new shas, no merge
commit) — the docs then pointed at a commit nobody has. Push the merge FIRST (`git push` right after
`git merge`, before any docs commit), or pull with `--rebase-merges`. Content is never lost; only the
shas the docs cite.

## Laptop from scratch (what you need while away)
You do NOT need `.env` to deploy — secrets live on Fly. You need it only to run the bot locally.

```
git clone https://github.com/skymitch9/black-bloc.git && cd black-bloc
winget install --id Fly-io.flyctl        # then, in a NEW terminal: flyctl auth login (browser)
python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"      # tests fake their own tokens
node --version                            # for site/mock/check.mjs (Node 20+)
```
Deploy = the block under **Deploy** above (`git pull` first). `docs/` is tracked **permanently**
(owner, 2026-08-31), so the whole doc tree comes with the clone — and since the repo went public
on 2026-09-10, so does everyone else's.

**`.env` on another machine — 🔐 the 1Password vault `Black Bloc` is the master
(2026-09-02):** on the laptop, open 1Password (the vault syncs to it), copy
`.env.example` to `.env`, and paste each of the nine secret values from its
bare-titled vault item. Sharing that vault + repo access fully onboards a dev.
FALLBACK (offline / no 1Password): `sh scripts/env-lock.sh` on the main machine
(passphrase prompt — yours alone), carry `.env.enc` to the laptop by hand (it is gitignored — the repo
is public since 2026-09-10, and the old copies were purged from history); laptop runs
`sh scripts/env-unlock.sh`. ⚠️ On the owner's machines `sh` is NOT on PATH —
use `& "C:\Program Files\Git\bin\bash.exe" scripts/env-lock.sh`. After any
rotation: vault item first, then `.env`, then Fly, then (optionally) a fresh
`.env.enc`.
Variable NAMES in `.env` — the authority is the tracked `.env.example`, **21 names** (counted
2026-09-11): `DISCORD_TOKEN DISCORD_CLIENT_ID DISCORD_CLIENT_SECRET SESSION_SECRET POLL_VOTE_SECRET
TWITCH_CLIENT_ID TWITCH_CLIENT_SECRET YOUTUBE_API_KEY ANTHROPIC_API_KEY GROQ_API_KEY DEV_GUILD_ID
TEST_MODE TEST_CHANNEL_ID DATABASE_PATH API_ENABLED API_HOST API_PORT SITE_ORIGIN SITE_ROOT
COMMAND_PREFIX LOG_LEVEL`. (`YOUTUBE_API_KEY` has no vault item yet — it has never been minted;
the nine secret values are the ones the vault holds.)
⚠️ Two names `black_bloc/config.py` reads are **absent from `.env.example`** and so are easy to
miss on a rebuild: **`OPERATOR_READ_TOKEN`** (never in `.env` by design — it lives in `fly secrets`
plus the operator PC's own environment, [`operator-read.md`](operator-read.md)) and
**`SESSION_COOKIE_SAMESITE`** (`lax` or `strict`, defaults to `lax`).
