# Black Bloc — first-ten-minutes gotcha sheet

Thin on purpose. The living state is in `docs/` — **read `docs/README.md`,
`docs/TODO.md`, `docs/KNOWN_ISSUES.md` first**, every session (global rule).

- Python 3.12, venv at `.venv`. `pip install -e ".[dev]"`, `pytest`, `python -m black_bloc`.
- `black_bloc/app.py` is the orchestrator and stays thin. Features are cogs under
  `black_bloc/cogs/` (`moderation/`, `content/`), registered in `bot.py:COGS`.
- Config comes ONLY from `black_bloc/config.py` (pydantic-settings, `.env`). Nothing
  else reads `os.environ`.
- Secrets: `.env` is gitignored; token custody is the Discord Developer Portal.
  Docs carry secret NAMES only.
- ⚠️ **TEST POLICY (owner, 2026-08-26): the bot speaks ONLY in `#mute-me-bot-test-spam`
  (`TEST_CHANNEL_ID`) and DMs until the owner lifts it.** Enforced by `black_bloc/guard.py`
  (`TEST_MODE=true`). Never flip it, never post elsewhere, brief every subagent with this.
- This is a GATEWAY bot (persistent websocket). It cannot run on Cloudflare
  Workers; hosting is an always-on container — `docs/info/hosting.md`.
- `docs/` is tracked. Every ask goes on `docs/TODO.md` the moment it is mentioned;
  finished items MOVE whole to `docs/DONE.md` in the session they land.
- Owner rule: on a Fable session, builds go to `model: 'opus'` subagents; Fable plans,
  briefs and reviews.
