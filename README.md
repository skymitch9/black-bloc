# Black Bloc

The Discord moderation and community bot for **Black in a Flash!** — built to
replace Carl-bot, YAGPDB, Birthday Bot and Modmail with one bot and one
dashboard. Python 3.12 + `discord.py` (gateway bot, one always-on process),
SQLite for state, FastAPI serving a staff dashboard from the same process.
Hosted on Fly.io; the dashboard lives at https://blackbloc.heygabi.ai
(Discord sign-in; staff = the roles that can see the staff channel).

## What it does today

**35 slash commands, a 17-page dashboard, and 14 cogs**, covering:

- **Moderation** — warn/timeout/kick/ban with a case book, automod
  (mention-spam armed, the rest log-only, shadow mode first), honeypot
  channels, modmail (channel-per-ticket with transcripts).
- **Community** — event proposals with staff review and Discord Scheduled
  Events, birthdays (per-member midnight), role menus with approval gating and
  time-limited grants, temporary voice channels with an owner control panel,
  polls (native Discord polls wrapped, plus an anonymous panel), feature
  requests (`/request` + a dashboard board), member timezone store.
- **Content** — go-live announcements (Discord presence + Twitch polling for
  linked channels, opt-out honored), real conversation when @-mentioned (a
  three-tier answer ladder: editable intents free, then Groq, then Claude
  Haiku with server knowledge, personas, and a hard monthly spend cap),
  configurable emoji skin tone.
- **Operations** — every action logged to a searchable Logs page with
  per-feature levels, every setting editable from both `/settings` and the
  dashboard, per-feature shadow/on modes, health page with loop monitoring.

The bot currently runs in **TEST_MODE**: it speaks only in its test channel and
DMs until the staged cutover (per-feature shadow → watch → on) completes.

## Run it locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env      # then fill in DISCORD_TOKEN and DEV_GUILD_ID
pytest                           # ~2.6k tests, no network needed (CI runs them on every push)
python -m black_bloc
```

Dashboard against fake data (no bot needed): `node site/mock/server.mjs` →
http://127.0.0.1:8788. `node site/mock/check.mjs` verifies every page against
the API contract.

## The docs

`docs/README.md` is the map. Start there; `docs/TODO.md` is what's active,
`docs/access/` is how to operate it (setup, deploy, recovery, runbook),
`docs/info/` is how it works and why (architecture, per-phase designs, the
review checklist). Secrets appear in docs by NAME only, never value.

## Contributing (house rules, enforced in review)

- **Near-zero comments in code.** Explanations live in
  `docs/info/code-notes.md`, keyed by `path:line`. One-line docstrings at most.
- **Tests mirror the package**: `black_bloc/x/y.py` → `tests/x/test_y.py`.
  One test file per source file; `pytest -q` and `ruff check .` green before
  every commit.
- **Every user-facing refusal is words** — what happened, what it needs, how
  to get it. Never a bare status code.
- **Every decision is configurable both ways**: a settings-registry key (or a
  slash path AND a dashboard control). Never hard-code a decided default.
- **TEST_MODE is sacred**: `black_bloc/guard.py` confines the bot to its test
  channel; never weaken it, never post elsewhere while it's on.
- Config comes only from `black_bloc/config.py` (pydantic-settings + `.env`);
  nothing else reads the environment.
