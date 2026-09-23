# Deploying to Fly.io

> **Audience:** Claude sessions and the owner. **Status:** TRACKED (owner,
> 2026-08-31 — was local-only until then; secret NAMES only).
> Last verified: **2026-09-22 23:2x — the gate's pytest step only** (branch `gate-names`, not merged or deployed):
> `-n 16`, `-rfE`, the junit file, `FAILED TESTS:` and the 120 s timeout, measured in
> [*The gate's pytest step*](#the-gates-pytest-step----n-16--rfe-a-junit-file-and-a-120-s-timeout-2026-09-22). ⚠️ No real deploy
> gate has run the new script yet. Before that, **2026-09-22 — the deploys.log COUNT row and the node-fixture COUNT only, at the
> v155 ritual.** [`../deploys.log`](../deploys.log) now records **154 deploys** (counted
> 2026-09-22 with `grep -c .`), the last **v155** `a285afc7` at **2026-09-22 13:35** — this page had
> said *107 / v108*, forty-six releases ago. The gate's node half is **six** fixture files, not the
> "five" this page said in one place and "three" in another: `discordmd`, `labels`, `clipmd`,
> `golive-join`, `layout` and **`discordmock`** (read off `scripts/deploy.ps1` and confirmed by the
> v155 run's own output). ⚠️ **NOTHING else on this page was re-checked at that pass** — no command
> body below was re-run by hand, the `fly.toml` block was not re-read, and the *5,546 tests in 40 s*
> figure below is still the 2026-09-11 reading (the v155 gate ran **7,316 passed + 3 skipped in
> 45 s**). The v155 deploy itself ran through `.\scripts\deploy.ps1` DETACHED exactly as described
> below and behaved as described: gate green on the FIRST run, `release.json` written and committed
> after the gate, push, `flyctl deploy`, skeleton line appended.
> Before that, **2026-09-21 — the *move the live mirror* step only, which is RETIRED**
> (owner, 12:2x, verbatim: *"We don't need the preview pages anymore"*). The mock's `LIVE_ROOT`
> live mirror and its `/preview/` door are **deleted from `site/mock/server.mjs`** (branch
> `no-previews`, merge `4dd9f649`), ✅ **shipped as part of v154 (2026-09-21 20:08)** — so there is
> nothing to move after a deploy and the mock's start line is
> `MOCK_PORT=8797 node site/mock/server.mjs`. ⚠️ **Nothing else on this page was re-checked at
> that pass** — no deploy was run, no command body below was re-run, and nothing touched Fly,
> Discord or a browser. Before that, **2026-09-20 (evening), the ORDER of `scripts/deploy.ps1` only** — the
> `release.json` write and its `Release vN: release.json` commit have MOVED to after every gate,
> immediately before `git push` (branch `small-fixes`, fix 3 of 4; see *Where `release.json` is
> written* below). ⚠️ **Nothing else on this page was re-checked at that pass.** ✅ **2026-09-20 23:32 — the new order SHIPPED v150** (`575dde2`); the measurement is under *Where `release.json` is written* below. Before that,
> **2026-09-11 08:35** — re-read against `fly.toml` and
> `scripts/deploy.ps1`. 🔴 **One real error fixed:** this file said *"`fly.toml` has no
> `[http_service]` on purpose"*, which has been false since the dashboard went live —
> `fly.toml` **has** an `[http_service]` block, and the three settings in it
> (`auto_stop_machines = false`, `auto_start_machines = false`,
> `min_machines_running = 1`) are what keep Fly from stopping the machine that holds the
> gateway websocket. The old sentence would have led someone to *delete* the block. The
> **redeploy** path is now heavily exercised: [`../deploys.log`](../deploys.log) records
> **154 deploys** (counted 2026-09-22; 107 on 2026-09-11, 37 on 2026-08-31), the last **v155**
> `a285afc7` at **2026-09-22 13:35**. The gate in `scripts/deploy.ps1` was re-read line by line and
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
# Dockerfile build ships what is on disk). It runs ruff -> the full test suite (-n 16, -rfE,
# a junit file; a red run prints FAILED TESTS: one nodeid per line - 2026-09-22)
# -> an ES-module parse of every site/public/assets/*.js (the labels.js incident: plain
# `node --check` parses a .js file as CommonJS and PASSED the file that blanked every
# dashboard page) -> node site/mock/check.mjs -> the five node fixture files, each its own
# REFUSED line: site/mock/discordmd.test.mjs (the preview renderer), labels.test.mjs (what a
# key and a channel are CALLED), clipmd.test.mjs (the post editor's paste converter),
# golive-join.test.mjs (the go-live streamers join) and layout.test.mjs (which dashboard
# column a section lands in) -> WRITES AND COMMITS site/public/assets/release.json
# -> git push origin main -> flyctl deploy, then appends a
# SKELETON line to docs/deploys.log that you must EDIT (what shipped; verified: what
# was checked) and commit. Escape hatch BLACKBLOC_SKIP_GATE=1 - emergencies only.
.\scripts\deploy.ps1
flyctl logs --app black-bloc --no-tail        # boot log: cogs loaded, "commands synced"
flyctl releases --app black-bloc              # a NEW version number = it landed
```

### Where `release.json` is written — LAST, after every gate (changed 2026-09-20)

The order inside `scripts/deploy.ps1` is now:

| # | Step | Why there |
|---|---|---|
| 1 | Read the last `docs/deploys.log` line, check its commit exists, diff `<that commit>..HEAD` | A refusal that costs nothing, so it comes before the 40-second suite. It only READS. |
| 2 | **Refuse a dirty tree** | A Dockerfile build ships what is on disk. |
| 3 | **The gate** — ruff, `pytest -n 16` (was `-n auto` until 2026-09-22), the ES-module parse, `check.mjs`, the five node fixture files | Nothing here reads `release.json`. |
| 4 | **Write `site/public/assets/release.json` and commit it** as `Release vN: release.json` | Every gate has passed, so this is the last thing that can add a commit. |
| 5 | `git push origin main` → `flyctl deploy` → the `deploys.log` skeleton line | The push carries the release commit, so the file ships inside the image exactly as before. |

🔴 **It used to be step 0**, written and committed before the check-clean and the gate — so a
refused gate left a `Release vN: release.json` commit sitting on `main`'s branch tip that had to
be dropped before the retry, and a second refusal left a second one. **Three of them were dropped
by hand landing v111.** Now a refused gate leaves the tree exactly as it found it and the retry is
just `.\scripts\deploy.ps1` again.

⚠️ **What this does NOT change:** the file's contents, the commit message, the escape hatch, and
the fact that the deploy pushes one more commit than you wrote. ⚠️ **What could still go wrong:**
`release_json.py` failing now costs a full gate run before you hear about it (it refuses in words
and nothing is pushed). ✅ **MEASURED 2026-09-20 23:32, v150.** The release commit `575dde2` (*Release v150: release.json*, 23:31:16) is the branch tip — written AFTER the gate (`7118 passed, 3 skipped`) and after the last content commit (`3d65025`, 23:29:32) — and `git push` carried it; the `deploys.log` line is 23:32:23. This was the **second** run of the new order. ⚠️ **Still NOT measured: a gate REFUSAL under the new order** — nothing has been refused since the move, and a refusal leaving the tree clean is the whole point of the change.

### ~~After every deploy: move the live mirror~~ — RETIRED 2026-09-21, there is no mirror

⚠️ **Nothing happens to the mock after a deploy any more.** It serves the WORKING TREE at the normal
URLs, always: `MOCK_PORT=8797 node site/mock/server.mjs`. Owner, 2026-09-21 12:2x: *"We don't need
the preview pages anymore"* — `LIVE_ROOT`, `realChanged`, `whereFrom`, the `/preview/` route and the
`/preview/assets/` rewrite are **deleted** from `site/mock/server.mjs` (branch `no-previews`), so a
branch is reviewed at its normal URL and `/preview/<page>.html` is a 404.

~~`site/mock/server.mjs` with `LIVE_ROOT=C:/lcw/bb-live` serves the deployed release at normal URLs
and the working tree under `/preview/` (adopted 2026-09-20, the owner's "the pages that are live now
should be under the normal url"). `C:/lcw/bb-live` is a DETACHED worktree; after each deploy move it
to the release the log line names, then restart the mock: `git -C C:/lcw/bb-live checkout --detach
<release>`.~~ The `C:/lcw/bb-live` worktree itself is the conductor's to remove
(`git worktree remove C:/lcw/bb-live`) — it was left in place by this change.

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

### The gate's pytest step — `-n 16`, `-rfE`, a junit file and a 120 s timeout (2026-09-22)

Changed on branch `gate-names` (KI-26 / KI-32 / KI-35 / KI-37). The step is now:

```powershell
& .venv/Scripts/python -m pytest -q -n 16 -rfE "--junitxml=$env:TEMP\black-bloc-gate\gate-junit.xml"
```

- **`-rfE`** puts every failed and errored nodeid in pytest's short summary.
- **The junit file** is deleted before the run and rewritten by it. On a non-zero exit the script prints
  `FAILED TESTS:` with one nodeid per line read from the file, then `(junit: <path>)`, and only THEN refuses —
  the refusal itself is unchanged. No file at all means pytest itself was killed (KI-37); the block says so.
  Reading it by hand is in [`testing.md`](testing.md).
- **`pytest-timeout`** (`timeout = 120`, `timeout_method = "thread"` in `pyproject.toml`) kills any test that runs
  120 s. Under xdist that ends as `worker 'gwN' crashed while running '<nodeid>'`, a named failure with exit 1,
  instead of idle workers for ever. `thread` is the only method that works on Windows (`signal` needs `SIGALRM`);
  measured with a sync `time.sleep` and an async `asyncio.sleep` hang, both named, run 7.6 s at `timeout=5`.
- **`-n 16`**, not `-n auto` (32 workers on this 32-logical-core machine). Measured 2026-09-22 22:2x–23:2x from the
  worktree, `-p no:cacheprovider`, the shell's `.env` names scrubbed, output to a file, 4–5 other agents' suites on
  the machine throughout. "Hung" = every worker (or one) blocked until the 120 s timeout named it.

| Tree | `-n auto` | `-n 16` | `-n 8` |
|---|---|---|---|
| Before the loopback fix (`920de1c8`) | **2 of 6 green**: 52 s, 41 s; hung 361 s (3.9 GB free at start), 173 s, 183 s, 168 s | **3 of 3 green**: 41, 62, 61 s | **11 of 14 green**: 91, 86 s + 9 hang-watch runs 68–102 s; hung 210, 206, 229 s |
| After the loopback fix (`f10b1553`) | **3 of 3 green**: 46, 46, 42 s | **5 of 5 green**: 61, 45, 56, 45, 46 s (the last two are the final configuration, no hang-watch) | **2 of 3 green**: 76, 72 s; one worker hung 177 s (a different shape — KI-26 note) |

  Why 16: with the port leak fixed, `-n 8` is ~60 % slower than auto (over the 25 % bar set for this change), `-n 16` is ~13 %
  slower (mean 51 s against 45 s) and halves the processes the OS must hold (KI-37; ⚠️ the RAM saved was not
  measured), and it does not change with the machine.
- **The loopback fix** (`tests/loopback.py`, loaded by `-p tests.loopback` in `addopts`) is what the old hangs were:
  see KI-26's 2026-09-22 note. It is why the "before" row hangs and the "after" row does not.

### ⚠️ "The deploy printed nothing after *Waiting for depot builder*" — run it DETACHED

> **2026-09-22 (branch `gate-names`):** the pytest step is now `-n 16 -rfE --junitxml=…` with a 120 s per-test
> timeout, **45–61 s** wall on the fixed tree (table above) — the whole script is still ~3–4 minutes and this
> gotcha's detach rule is unchanged. A red gate now prints `FAILED TESTS:` in the detached log before `REFUSED`, so
> `Get-Content $log -Tail 20` shows the names.


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
