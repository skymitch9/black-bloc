# Gotchas — traps that cost real time

> **Audience:** Claude sessions and the owner. **Status:** TRACKED (owner,
> 2026-08-31 — was local-only until then; secret NAMES only).
> Last verified: **2026-08-26** (STATUS line only re-checked 2026-08-31; no
> entry below was re-tested). Entries marked *(anticipated)* come from
> library knowledge, not from an incident here; promote them to a dated
> incident the first time one bites.

## Login fails with `PrivilegedIntentsRequired` *(anticipated)*

`bot.py` requests `members` and `message_content`. Both are **privileged**:
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

## SQLite inside a OneDrive folder *(anticipated, and this repo IS in one)*

`data/black_bloc.sqlite3` and its `-wal`/`-shm` sidecars under
`OneDrive/Documents/...` can hit "database is locked" while OneDrive uploads
mid-write. KI-1 in `../KNOWN_ISSUES.md`. Fix: `DATABASE_PATH` in `.env`
pointing outside OneDrive.

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
(`access/deploy.md`, "Pause the bot"). Same reason `fly deploy` must carry
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
redirect it via `cmd /c "flyctl … < file"` (`access/deploy.md` §4).

## Discord's API returns Cloudflare 403 error 1010 to Python's default User-Agent (incident, 2026-08-26)

A plain `urllib` call to `discord.com/api` got `403 error code: 1010` — Cloudflare's WAF rejecting the `Python-urllib` UA, not Discord judging the request. Same call with `User-Agent: DiscordBot (https://github.com/skymitch9/black-bloc, 0.1.0)` succeeded. discord.py and aiohttp inside the bot set their own UA; only hand-rolled scripts hit this. It cost one false 'secret invalid' reading.

