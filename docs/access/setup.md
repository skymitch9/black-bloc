# Local setup and first run

> **Audience:** Claude sessions and the owner. **Status:** TRACKED (owner,
> 2026-08-31 — was local-only until then; secret NAMES only).
> Last verified: **2026-09-19** — §3's *Test policy* box re-dated (⚠️ **`TEST_MODE` is OFF in
> PRODUCTION since 2026-09-18 16:08**; the box now says what it meant and when it stopped) and
> §3's expected boot lines re-measured off `main` `ffea17e` (**v141**): `len(bot.COGS)` = **22**
> (said 19), `tests/test_bot.py:TOP_LEVEL_NOW` = **32** (said 29), and the first line is no longer
> `TEST MODE ON` on the deployed bot. §4's test figure re-read off the v141 deploy gate
> (**6,757**, said 5,546). ⚠️ **NOT run today:** nothing in this file — no venv was built,
> `python -m black_bloc` was **not** booted, `pytest` was **not** run (the 6,757 is the gate's
> number off `../deploys.log`, not a run here), `.env.example` was **not** re-counted, and no
> Developer-Portal page was opened. Before that,
> **2026-09-11 08:38** — re-read against the repo. §1's commands and §4's table
> still match `pyproject.toml` and `scripts/deploy.ps1` (`ruff check .` is what the deploy gate
> runs). §3's expected boot lines were **stale by a whole project**: a first start now loads
> **19** cogs and syncs **29** commands, not 2. `.env.example` carries **23** names since 2026-09-11 09:25 — 21, plus `OPERATOR_READ_TOKEN` and `SESSION_COOKIE_SAMESITE` added when the docs pass found `config.py` reads them (it did not
> exist in this shape in August); copying it is still the right first move. ⚠️ **NOT run today:**
> nothing in this file — no venv was built, `python -m black_bloc` was **not** booted (a worktree
> holds no token), and no Developer-Portal page was opened. The exact portal button labels in §2
> have never been re-checked by Claude; the owner followed them successfully on 2026-08-26.
> Before that, **2026-08-26** (STATUS line re-checked 2026-08-31) — §1, §3 and §4 executed that
> day in a fresh `.venv` on Windows 11 / Python 3.12.10; §2 was walked through by the owner the
> same afternoon (the bot logged in).

## 1. Environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
pytest                       # must be green before anything else
```

## 2. Create the Discord application (one-time, owner)

1. <https://discord.com/developers/applications> → **New Application** → name it *Black Bloc*.
2. **Bot** tab → **Reset Token** → copy it into `.env` as `DISCORD_TOKEN`.
   It is shown once. It goes nowhere else (not docs, not chat).
3. Same tab, **Privileged Gateway Intents** → turn ON all three: **Presence**,
   **Server Members**, **Message Content**. ⚠️ `bot.py` requests all three; if
   any is off the bot exits 3 with a message naming this step.
4. **Invite URL:** start the bot once (`python -m black_bloc`); it logs
   `invite URL: https://discord.com/oauth2/authorize?...` built from
   `bot.py:INVITE_PERMISSIONS` (scopes `bot` + `applications.commands`,
   the permission set the feature list needs — never Administrator). Widening
   a permission = edit that constant and re-invite.
5. Open that URL, pick the dev server, authorise. Until this is done the log
   shows `cannot sync commands to guild ...` and the bot sits in 0 guilds —
   that is the designed message for "not invited yet", not a crash.
6. In Discord, enable **Developer Mode** (User Settings → Advanced), right-click
   the server → **Copy Server ID** → `.env` `DEV_GUILD_ID`.

## ⚠️ Test policy — owner rule, 2026-08-26 · ✅ LIFTED 2026-09-18

✅ **The owner lifted it on 2026-09-18 16:08** — `flyctl secrets set TEST_MODE=false --app
black-bloc`, cutover step **P5** ([`../info/cutover-plan.md`](../info/cutover-plan.md)). **On the
deployed bot the table below no longer applies:** there is no guard, and Black Bloc speaks
wherever its settings point it. The brake is now each feature's own `*_mode` — `shadow` puts the
rehearsal copy in `shadow_channel_id` (`#welcome-test`) and nothing in the real channel — and
events, requests and modmail are **live to members** (owner, 2026-09-18 17:1x: *"its live and
people can use it"*). ⚠️ **Never flip `TEST_MODE` yourself, in either direction** — it is the
owner's switch, and that rule did not lift with the flag.

**`TEST_MODE` still defaults to `true` in `.env.example`**, so a LOCAL run made by following §1
is still guarded, and `black_bloc/guard.py` is still in the tree for any future rehearsal. What
follows is that local shape, and what production was until 2026-09-18 16:08:

> "we will only test in here until we're ready. never use another channel
> except for you're allowed to be dm'd to test too"

| | |
|---|---|
| Server | *Black in a Flash!* — `DEV_GUILD_ID=1073710702776299640` |
| The ONLY channel | `#blackbloc-logs` — `TEST_CHANNEL_ID=1542316174472380517` (renamed 2026-09-16; was `#mute-me-bot-test-spam`, the id survived) |
| Also allowed | DMs to the bot |
| Enforced by | `black_bloc/guard.py` while `TEST_MODE=true` (still the `.env` default). Sends elsewhere raise `TestModeViolation`; commands elsewhere get an ephemeral "test mode" reply |
| Lifting it | `TEST_MODE=false` — **only when the owner says so**, never as a side effect of a feature. Done in production 2026-09-18 16:08 |

Feature code must still respect it for side effects the gate cannot see
(bans, channel edits, events): check `bot.guard.allows_channel(id)` first — the guard object is
`None` when the flag is off, and every such call site already reads it that way.

## 3. First start

```powershell
python -m black_bloc
```

Expected log lines, in order: `TEST MODE ON ...` (**local only** — the deployed bot has had no
such line since 2026-09-18 16:08), `database ready at ...`,
`invite URL: ...`, `loaded cog black_bloc.cogs.core` and **twenty-one more**
(`bot.py:COGS` holds **22**, measured 2026-09-19; it said 19 and that was the 2026-09-11
reading), `synced 32 app commands
to dev guild ...` (**32**, `tests/test_bot.py:TOP_LEVEL_NOW`, measured 2026-09-19; it said 29),
`logged in as Black Bloc#... ; 1 guild(s)`. Then `/ping`
and `/about` — **locally, in `#blackbloc-logs`**; on the deployed bot, anywhere. Both reply
ephemerally.
(This said "loaded cog …core, synced **2** app commands" until 2026-09-11 — that was the
day-one shape, when `core` was the only cog.)

With no token, the process exits **2** and prints one line saying so — that is
the designed behaviour, not a crash.

## 4. Everyday commands

| Task | Command |
|---|---|
| Tests | `pytest` — or `pytest -q -n auto`, which is what the deploy gate runs (**6,757** passed + 3 skipped at the v141 gate, 2026-09-18 — read off [`../deploys.log`](../deploys.log), ⚠️ not re-run here; it said 5,546 in 40 s at v108). `tests/live/` is deselected by default; see [`testing.md`](testing.md) |
| Lint | `ruff check .` (`ruff check --fix .` to auto-fix imports etc.) — the same invocation `scripts/deploy.ps1` uses |
| Run | `python -m black_bloc` (Ctrl+C stops it cleanly) |
| Turn the API on | `.env`: `API_ENABLED=true` → <http://127.0.0.1:8080/health>. On Fly it is already `true` (`fly.toml` `[env]`) and serves the dashboard too |
| Look at the dashboard with no bot | `node site/mock/server.mjs` → <http://127.0.0.1:8788> ([`site.md`](site.md)) |
