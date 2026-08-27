# Black Bloc — first-ten-minutes gotcha sheet

Thin on purpose. The living state is in `docs/` — **read `docs/README.md`,
`docs/TODO.md`, `docs/KNOWN_ISSUES.md` first**, every session (global rule).

- Python 3.12, venv at `.venv`. `pip install -e ".[dev]"`, `pytest`, `python -m black_bloc`.
- ⚠️ **CODE STYLE (owner, 2026-08-26): near-zero comments in code.** Explanations
  live in `docs/info/code-notes.md`, keyed by `path:line`, not in the source. One-line
  docstrings at most. `black_bloc/app.py` is a bare "run button"; `bot.py` is lifecycle
  only; every behaviour is its own module with helpers. Features are cogs under
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
- `docs/` is **LOCAL ONLY** (gitignored; owner rule 2026-08-26 — peers get curated docs,
  not the working tree). It exists on the owner's machine only; never `git add -f` it.
  Every ask goes on `docs/TODO.md` the moment it is mentioned;
  finished items MOVE whole to `docs/DONE.md` in the session they land.
- Owner rule: on a Fable session, builds go to `model: 'opus'` subagents; Fable plans,
  briefs and reviews.
