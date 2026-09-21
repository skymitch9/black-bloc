# Deploying to Fly.io

> **Audience:** Claude sessions and the owner. **Status:** TRACKED (owner,
> 2026-08-31 — was local-only until then; secret NAMES only).
> Last verified: **2026-09-11 08:35** — re-read against `fly.toml` and
> `scripts/deploy.ps1`. 🔴 **One real error fixed:** this file said *"`fly.toml` has no
> `[http_service]` on purpose"*, which has been false since the dashboard went live —
> `fly.toml` **has** an `[http_service]` block, and the three settings in it
> (`auto_stop_machines = false`, `auto_start_machines = false`,
> `min_machines_running = 1`) are what keep Fly from stopping the machine that holds the
> gateway websocket. The old sentence would have led someone to *delete* the block. The
> **redeploy** path is now heavily exercised: [`../deploys.log`](../deploys.log) records
> **107 deploys** (counted 2026-09-11; was 37 on 2026-08-31), the last **v108** `73e2e44`
> at **2026-09-11 00:37**. The gate in `scripts/deploy.ps1` was re-read line by line and
> matches what is described below (`ruff check .` → `pytest -q -n auto` → an ES-module
> `node --check` of every `site/public/assets/*.js` → `site/mock/server.mjs` +
> `check.mjs` → `git push` through `cmd /c` → `flyctl deploy --ha=false --remote-only
> --yes` → the `deploys.log` skeleton line; escape hatch `BLACKBLOC_SKIP_GATE=1`).
> The suite it runs is **5,546 tests in 40 s** (measured today, `-n auto`).
> **2026-09-18, gate step only:** the chain above also runs **three** node fixture files after
> `check.mjs`, each with its own `REFUSED` line — `discordmd.test.mjs`, `labels.test.mjs` and
> (new, branch `posts-paste`) **`clipmd.test.mjs`**, the post editor's paste converter. ⚠️ Nothing
> else on this page was re-checked at that pass and no deploy was run.
> ⚠️ **NOT re-run today:** every command body below — first launch, rotate, SFTP, scale
> — and nothing in this pass touched the live Fly app, Discord or a browser. The
> first-launch sequence was RUN on 2026-08-26, in this order, and the bot logged in from
> Fly (machine `85e744c4d959d8`, region `lax`). Before that, **2026-09-03** — "Every
> later deploy" rewritten around `scripts/deploy.ps1` (the only path since 2026-09-01)
> and the detached-run gotcha added from that morning's killed deploy.
> Hosting decision: Fly.io (owner, 2026-08-26). Rationale:
> [`../info/hosting.md`](../info/hosting.md). Every deploy appends a line to
> [`../deploys.log`](../deploys.log).

## Why Fly

One always-on container running `python -m black_bloc`, holding the Discord
gateway websocket 24/7, with a small persistent disk for SQLite. The owner does
not need to be at a machine. Cost class: `shared-cpu-1x` / 256 MB ≈ $2–4/month
(Fly bills by usage; check the current pricing page, do not trust this number).

## First launch (once)

```powershell
# 1. CLI + login. The winget id is Fly-io.flyctl (NOT flyio.flyctl). New shells
#    have it on PATH as `flyctl`; a shell opened before the install does not.
#    ⚠️ The Claude session shell (Bash tool and `!`) never has it: spell out
#    "$LOCALAPPDATA/Microsoft/WinGet/Packages/Fly-io.flyctl_Microsoft.Winget.Source_8wekyb3d8bbwe/flyctl.exe".
#    Owner authorised Claude to run the deploy itself (2026-08-27).
winget install --id Fly-io.flyctl
flyctl auth login        # needs a REAL terminal window - it refuses Claude's
                         # shell and the `!` prompt ("requires an interactive
                         # terminal"). Open PowerShell and run it there.

# 2. Create the app (deterministic; `fly launch` would rewrite fly.toml)
flyctl apps create black-bloc --org personal

# 3. Persistent disk for /data (SQLite). Must be a real Fly region - there is
#    no `phx`; `lax` is the nearest to Phoenix.
flyctl volumes create black_bloc_data --app black-bloc --region lax --size 1 --yes

# 4. Secrets - NEVER into fly.toml or the image. `secrets import` reads KEY=VALUE
#    lines from stdin, so values never appear on a command line or in a log.
#    From the repo root, feed the four needed lines from .env:
# From PowerShell, DO NOT pipe python straight into flyctl: the pipeline prepends a
# UTF-8 BOM to the first key ("\ufeffDISCORD_TOKEN is not a valid secret name").
# Write an ASCII temp file and redirect it through cmd instead:
python -c "import re;open('secrets.tmp','w',encoding='ascii',newline='\n').write(''.join(l for l in open('.env',encoding='utf-8') if re.match(r'^(DISCORD_TOKEN|DEV_GUILD_ID|TEST_MODE|TEST_CHANNEL_ID|TWITCH_CLIENT_ID|TWITCH_CLIENT_SECRET)=.+',l)))"
cmd /c "flyctl secrets import --app black-bloc --stage < secrets.tmp"; Remove-Item secrets.tmp

# 5. Ship it. --ha=false is REQUIRED: the default creates two machines, which
#    is two bots answering every command twice.
flyctl deploy --app black-bloc --ha=false --remote-only --yes
flyctl logs --app black-bloc --no-tail      # expect "logged in as Black_Bloc#..."
```

🔴 **`fly.toml` DOES have an `[http_service]` — and its three settings are
load-bearing, not tuning.** (This file said the opposite until 2026-09-11; it was true
only before the dashboard went live on the same app.) The machine answering HTTP is the
machine holding the outbound gateway websocket, so Fly's default auto-stop-on-idle would
kill the bot — an idle HTTP service is not an idle bot. All three must survive every
edit:

```toml
[http_service]
  internal_port = 8080
  force_https = true
  auto_stop_machines = false
  auto_start_machines = false
  min_machines_running = 1
```

Keep `[mounts]` too (`black_bloc_data` → `/data`, where the SQLite file lives), and
never run `fly launch` — it rewrites the file.

## Every later deploy — `scripts/deploy.ps1`, nothing else

```powershell
# From the repo root, tree committed-clean (the script REFUSES a dirty tree, and a
# Dockerfile build ships what is on disk). It runs ruff -> the full test suite (-n auto)
# -> an ES-module parse of every site/public/assets/*.js (the labels.js incident: plain
# `node --check` parses a .js file as CommonJS and PASSED the file that blanked every
# dashboard page) -> node site/mock/check.mjs -> the three node fixture files, each its own
# REFUSED line: site/mock/discordmd.test.mjs (the preview renderer), labels.test.mjs (what a
# key and a channel are CALLED) and clipmd.test.mjs (the post editor's paste converter)
# -> git push origin main -> flyctl deploy, then appends a
# SKELETON line to docs/deploys.log that you must EDIT (what shipped; verified: what
# was checked) and commit. Escape hatch BLACKBLOC_SKIP_GATE=1 - emergencies only.
.\scripts\deploy.ps1
flyctl logs --app black-bloc --no-tail        # boot log: cogs loaded, "commands synced"
flyctl releases --app black-bloc              # a NEW version number = it landed
```

### ⚠️ "Nine *no key* tests fail in the gate, and only in the gate" — the shell is carrying `.env`

Measured 2026-09-20 17:3x: the v144 gate failed `test_the_inventory_says_set_or_unset_and_never_a_value`, four polls
"no key" tests, two chat, one minutes and one costs test — **nine, all of the shape "when the key is absent, say so"** — while
the same tree had passed 6800 green an hour earlier. The tool shell had inherited every name in `.env` (`ANTHROPIC_API_KEY`,
`GROQ_API_KEY`, `DISCORD_TOKEN`, all nineteen), so pydantic-settings found keys the tests assume are unset. A hand-written
regex of "bot-shaped" names had missed the AI keys. **Clear every name `config.py` declares, mechanically, before the gate:**

```powershell
$names = Select-String -Path black_bloc\config.py -Pattern '^\s+([a-z_]+)\s*:' -AllMatches |
  ForEach-Object { $_.Matches } | ForEach-Object { $_.Groups[1].Value.ToUpper() } | Sort-Object -Unique
Get-ChildItem env: | Where-Object { $names -contains $_.Name } | ForEach-Object { Remove-Item "env:$($_.Name)" }
powershell -NoProfile -File scripts\deploy.ps1 *> deploy.log
```

The gate refuses before `git push`, so a red run of this shape costs one re-run and nothing else. (Never print the values —
`Get-ChildItem env:` alone would; select the names.)

### ⚠️ "The deploy printed nothing after *Waiting for depot builder*" — run it DETACHED

The script USED to take **~10 minutes** end to end (measured 2026-09-03 morning: pytest
alone 8:27 for 3345 tests, single process). Since the same afternoon it runs pytest under
`pytest-xdist` (`-n auto`): 3371 tests in 54 s wall on the 32-logical-core machine, and the
suite has since grown to **5,546 tests — still 40 s wall** (measured 2026-09-11 08:28), so
the whole script is ~3–4 minutes and most of that is the Fly build. The
ceiling gotcha still stands — a slow builder can push it past ten. A Claude tool call has a
**10-minute ceiling**: when it kills
the wrapper mid-`flyctl deploy`, the orphaned flyctl keeps running with a dead stdout pipe,
sits at "Waiting for depot builder" indefinitely and **makes no release** — the push has
already happened, so `main` is ahead of the machine and nothing says so. Seen 2026-09-03
(pid 34312, ten minutes of silence, `flyctl releases` still on the old version).

From a Claude session, never run the script inside a tool call. Detach it and watch the pid:

```powershell
$log = "<scratchpad>\deploy.log"
$p = Start-Process powershell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File .\scripts\deploy.ps1" `
       -WorkingDirectory (Get-Location) -RedirectStandardOutput $log -RedirectStandardError "$log.err" `
       -PassThru -WindowStyle Hidden
$p.Id                     # watch this with the Monitor tool; peek with Get-Content $log -Tail 5
```

If a run was already killed: `Stop-Process` the orphaned `flyctl` (`Get-Process flyctl`),
confirm `flyctl releases` shows no new version, and relaunch detached — the tree is still
clean and the push is idempotent. A bare `flyctl deploy` by hand is NOT the fallback; it
skips the gate.

**Never run the bot locally while the Fly machine is up** - two instances
answer every command twice. Pause Fly first: `flyctl machine stop 85e744c4d959d8
--app black-bloc`, then `... start` after.

## Useful

| Need | Command |
|---|---|
| Is it up? | `fly status` |
| Live log tail | `fly logs` |
| Rotate the token | Portal → Reset Token → `fly secrets set DISCORD_TOKEN=...` (redeploys automatically) |
| Shell into the machine | `fly ssh console` |
| Copy the DB out | `fly ssh sftp get /data/black_bloc.sqlite3 .\backup.sqlite3` |
| Pause the bot | `flyctl machine stop <id> --app black-bloc` / `start` |
| Stop paying | `fly scale count 0` (keeps the app + volume), `fly apps destroy black-bloc` (does not) |

## Alternatives considered

See [`../info/hosting.md`](../info/hosting.md). Short version: Railway is
equivalent; a $4–6/mo VPS is fine but adds patching duty; Cloudflare Workers
cannot host this bot at all.
