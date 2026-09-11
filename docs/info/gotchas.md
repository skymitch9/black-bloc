# Gotchas — traps that cost real time

> **Audience:** Claude sessions and the owner. **Status:** TRACKED (owner,
> 2026-08-31 — was local-only until then; secret NAMES only).
> Last verified: **2026-09-11 08:40** — docs-wide staleness pass. **What was checked:** every
> path, symbol and cross-reference each entry names, read off `main` at `1d090e5` —
> `intents.py:8–9`, `api/server.py:206 start_api`, `tests/conftest.py:55–56` and `:237–240`,
> `command_visibility.py`, `../KNOWN_ISSUES.md` KI-1/KI-2, `../access/deploy.md` §4 and its
> "Pause the bot" row. **What that FIXED:** the intents entry said `bot.py` asks for them
> (it is `intents.py:build_intents`); the OneDrive entry cited KI-1 as if open (**CLOSED
> 2026-09-01** — `DATABASE_PATH` now points outside OneDrive); the bare `access/…` prose
> paths are now real `../access/…` links; the mojibake detector was re-run (**0** hits
> outside this file's own examples). **One entry ADDED:** the `deploy.ps1` xdist hang, five
> recorded incidents on `../deploys.log` (v97–v100, v103) that had no home here. ⚠️ **NOT re-tested:** every entry's underlying
> behaviour — none of these traps was re-triggered, so each *(anticipated)* one is still
> library knowledge and each incident one is still a 2026-08/09 reading. Nothing here met
> Discord or a browser.
> Before that, **2026-08-26** (STATUS line only re-checked 2026-08-31; no
> entry below was re-tested). Entries marked *(anticipated)* come from
> library knowledge, not from an incident here; promote them to a dated
> incident the first time one bites.

## Login fails with `PrivilegedIntentsRequired` *(anticipated)*

`intents.py:build_intents` (called from `bot.py`) requests `members` and
`message_content` — `intents.py:8–9`. Both are **privileged**:
they must ALSO be toggled on in the Developer Portal (Bot → Privileged Gateway
Intents). Code alone cannot grant them. Symptom is the bot dying seconds after
start with that exception name in the log.

## A new slash command "isn't there" *(anticipated)*

- With `DEV_GUILD_ID` set: commands are copied and synced to that guild at
  startup — restart the bot, then **fully restart the Discord client** (Ctrl+R)
  if the picker is stale.
- Without it: nothing syncs. Global sync is not wired up on purpose (KI-2);
  add a `DEV_GUILD_ID` while developing.
- Syncing is rate-limited. Rapid restart loops produce 429s and a slow start.
  That is Discord, not a bug.

## SQLite inside a OneDrive folder *(anticipated; FIXED 2026-09-01, keep it that way)*

`data/black_bloc.sqlite3` and its `-wal`/`-shm` sidecars under
`OneDrive/Documents/...` can hit "database is locked" while OneDrive uploads
mid-write. ✅ **[KI-1](../KNOWN_ISSUES.md) is CLOSED** — the local `.env` `DATABASE_PATH`
points outside OneDrive and the old file under `data/` is inert; the hosted deployment
always used the Fly volume at `/data` and was never affected. The trap is still live for
anyone who clears `DATABASE_PATH` or clones fresh, which is why this entry stays.

## Ctrl+C with `API_ENABLED=true` *(anticipated, UNVERIFIED)*

uvicorn installs its own SIGINT handler while `serve()` runs and re-raises the
signal after the API shuts down. Expected behaviour: first Ctrl+C stops the API
and then the bot; if the bot ever appears to ignore Ctrl+C with the API on,
this is where to look (`black_bloc/api/server.py:start_api`).

## `pytest` picks up your real `.env` *(prevented, keep it that way)*

`Settings` reads `.env` from the CWD by default. Tests pass `_env_file=None`
(`tests/conftest.py`) and clear `DISCORD_TOKEN`. Any new test that builds
`Settings` directly must do the same or it will silently test against the
developer's real token.

## Bash heredocs in this environment (incident, 2026-08-26)

A single `bash -c` with many `cat > file <<'EOF'` blocks failed to parse
("unexpected EOF while looking for matching `''`") and — because bash parses
the whole string first — **wrote nothing at all**, including the `mkdir`
that preceded the heredocs. Write files with the Write tool, or one heredoc
per command, and check `find . -type f` before assuming anything landed.

## Two bots answering everything twice (incident-class, prevented 2026-08-26)

The Fly machine runs 24/7. Starting `python -m black_bloc` locally while it is
up means two gateway sessions on the same token — every command answered
twice, every announcement posted twice. Stop the Fly machine first
([`../access/deploy.md`](../access/deploy.md), "Pause the bot"). Same reason `fly deploy` must carry
`--ha=false`.

## Bash tool dies with `EPERM: uv_spawn bash.exe` = Windows Defender "ClickFix" (incident, 2026-08-26)

Two Bash calls in a row failed to spawn (`EPERM: operation not permitted,
uv_spawn 'C:\Program Files\Git\bin\bash.exe'`) while PowerShell kept working.
`Get-MpThreatDetection` showed why: Defender flagged the **command line
itself** as `Trojan:Win32/ClickFix.DCW!MTB` (severity 5) at 17:15:54 and
17:16:51 and blocked the spawn. The resource was `CmdLine:` — the tool's own
wrapper (`bash.exe -c "source <snapshot> && … && eval '<command>'"`) around a
long multi-file Python heredoc with `>>` redirects and a `git commit … &&
git push` chain. That shape matches the "paste this into Run" social-
engineering pattern the ClickFix signature hunts. No file was quarantined
(`bash.exe` and the snapshot were intact; `IsActive: False`).

**Avoid the trigger, do not add an exclusion:** keep Bash commands short;
put multi-file edits in a script file (Write tool → `python <file>`), and run
git via PowerShell if Bash is being blocked. Re-check `git status` before
assuming a blocked command did nothing — both times it had done nothing.
The owner is told whenever Defender fires on a session command — it is a
security event on his machine even when the cause is benign.

## Fly trial stops the machine after 5 minutes (incident, 2026-08-26)

With no credit card on the Fly account, every machine is killed 5 minutes
after start: `Trial machine stopping. To run for longer than 5m0s, add a
credit card by visiting https://fly.io/trial`. The bot looked deployed and
logged in, and was dead by the time the owner tried `/ping`. Symptom in
`fly status`: `stopped` a few minutes after `started`. Fix is on the owner's
side (card on file), then `flyctl machine start <id>`. Side-finding: the
shutdown log shows SIGINT → `Main child exited normally with code: 0`, so
graceful shutdown of the bot works.

## `flyctl secrets import` rejects "\ufeffKEY" (incident, 2026-08-26)

Piping Python's stdout into `flyctl secrets import` from the PowerShell tool
prepends a UTF-8 BOM to the first line, and Fly refuses the key name. The
deploy that followed started the bot with Twitch enrichment OFF (the
designed graceful path — the log said so). Fix: write an ASCII temp file and
redirect it via `cmd /c "flyctl … < file"` ([`../access/deploy.md`](../access/deploy.md) §4).

## Discord's API returns Cloudflare 403 error 1010 to Python's default User-Agent (incident, 2026-08-26)

A plain `urllib` call to `discord.com/api` got `403 error code: 1010` — Cloudflare's WAF rejecting the `Python-urllib` UA, not Discord judging the request. Same call with `User-Agent: DiscordBot (https://github.com/skymitch9/black-bloc, 0.1.0)` succeeded. discord.py and aiohttp inside the bot set their own UA; only hand-rolled scripts hit this. It cost one false 'secret invalid' reading.


## A worktree cut BEFORE its spec was committed has no spec (incident, 2026-09-01)

The 14a builder's worktree was branched from main at a commit made minutes
before `phase14-design.md` landed — its brief named a spec file its own tree
did not contain. It recovered by reading the shared checkout read-only, but the
rule for the conductor is: **commit the design doc to main FIRST, then dispatch
the worktree builders.** A dispatch that references any repo file must be cut
from a commit that contains it.

## `deploy.ps1` hangs mid-pytest with every xdist worker idle (incidents ×5, 2026-09-06 and 2026-09-10)

Recorded on `../deploys.log` at v94, v97, v98, v99 and v100 (re-read 2026-09-11 — the v103 line
says *no hang*; an earlier version of this entry miscounted it). The
deploy gate's `pytest -n auto` stops making progress and sits there: **33 idle pythons, log
untouched for 72 s, CPU flat over 20 s.** Two shapes were seen — a hang at *spawn* (the two
morning ones) and a hang at **81–92 % of the run** (the rest). It is not a failing test and
it is not stoppable from the console.

**What got past it, every time:** kill the process tree, then re-run the deploy **through
the PowerShell tool with output redirected to a file** (`*> file`) rather than detached.
The retry passed the gate in 26–30 s on each occasion. The count and the threshold that
would make it worth chasing live in [`../KNOWN_ISSUES.md`](../KNOWN_ISSUES.md) **KI-26**. ⚠️ **Do not conclude the suite is
broken** — the same commit's tests pass forward and under `BB_REVERSE=1` on the retry. Cause
never established; it is the retry, not a fix.

## A doc suddenly reads `â€”` and `âš ï¸` everywhere = it was written back double-encoded (incident, 2026-09-03)

`docs/DONE.md` at `31b1689` (the Phase 16 landing) carried **333** mojibake
sequences — every em dash, arrow and ⚠️ in the whole file, not just the new
entry — and nobody noticed for a day because `git diff` showed only the
appended lines. Cause, by shape: the file was read as cp1252 and written back
as UTF-8 (a PowerShell `Get-Content`/`Set-Content` round-trip without
`-Encoding utf8` does exactly this on Windows PowerShell 5.1). Detect with
`grep -rc 'â€' docs --include=*.md | grep -v ':0'` — the only hits allowed
are this entry's own examples. Repair: take
the last clean commit's body verbatim and re-apply only the new entry (done
2026-09-03; proven lossless with `git diff <clean> -- docs/DONE.md` showing
additions only). When editing docs from Python on Windows, pass
`encoding="utf-8"` on BOTH the read and the write; from PowerShell, prefer
not to — use the Edit tool or Python.
