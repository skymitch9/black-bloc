# Local setup and first run

> **Audience:** Claude sessions and the owner. **Status:** LOCAL ONLY (gitignored 2026-08-26).
> Last verified: **2026-08-26** — §1, §3 and §4 executed that day in a fresh
> `.venv` on Windows 11 / Python 3.12.10; §2 was walked through by the owner
> the same afternoon (the bot logged in). ⚠️ The exact portal button labels in
> §2 were not re-checked by Claude — the owner followed them successfully.

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

## ⚠️ Test policy — owner rule, 2026-08-26

> "we will only test in here until we're ready. never use another channel
> except for you're allowed to be dm'd to test too"

| | |
|---|---|
| Server | *Black in a Flash!* — `DEV_GUILD_ID=1073710702776299640` |
| The ONLY channel | `#mute-me-bot-test-spam` — `TEST_CHANNEL_ID=1542316174472380517` |
| Also allowed | DMs to the bot |
| Enforced by | `black_bloc/guard.py` while `TEST_MODE=true` (default). Sends elsewhere raise `TestModeViolation`; commands elsewhere get an ephemeral "test mode" reply |
| Lifting it | `TEST_MODE=false` — **only when the owner says so**, never as a side effect of a feature |

Feature code must also respect it for side effects the gate cannot see
(bans, channel edits, events): check `bot.guard.allows_channel(id)` first.

## 3. First start

```powershell
python -m black_bloc
```

Expected log lines, in order: `TEST MODE ON ...`, `database ready at ...`,
`invite URL: ...`, `loaded cog black_bloc.cogs.core`, `synced 2 app commands
to dev guild ...`, `logged in as Black Bloc#... ; 1 guild(s)`. Then `/ping`
and `/about` **in `#mute-me-bot-test-spam`**. Both reply ephemerally.

With no token, the process exits **2** and prints one line saying so — that is
the designed behaviour, not a crash.

## 4. Everyday commands

| Task | Command |
|---|---|
| Tests | `pytest` |
| Lint | `ruff check .` (`ruff check --fix .` to auto-fix imports etc.) |
| Run | `python -m black_bloc` (Ctrl+C stops it cleanly) |
| Turn the API on | `.env`: `API_ENABLED=true` → <http://127.0.0.1:8080/health> |
