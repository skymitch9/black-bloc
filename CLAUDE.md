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
- ⚠️ **Only bot code gets committed (owner, 2026-08-26).** Scan/scrape/inventory
  scripts and anything that gathers info rather than makes the bot work stay out of
  git — they live in `scripts/scan/` (gitignored). Never `git add -f` them. Same for
  tests: only tests of the bot are committed, never tests of research tooling.
- ⚠️ **Tests mirror the package (owner, 2026-08-26).** `black_bloc/x.py` →
  `tests/test_x.py`; `black_bloc/storage/db.py` → `tests/storage/test_db.py`;
  `black_bloc/cogs/moderation/foo.py` → `tests/cogs/moderation/test_foo.py`. One test
  file per source file, same folder shape, no flat pile. (`--import-mode=importlib`
  in `pyproject.toml` makes same-named files in different folders work.)
- `docs/` is **LOCAL ONLY** (gitignored; owner rule 2026-08-26 — peers get curated docs,
  not the working tree). It exists on the owner's machine only; never `git add -f` it.
  Every ask goes on `docs/TODO.md` the moment it is mentioned;
  finished items MOVE whole to `docs/DONE.md` in the session they land.
- Owner rule: on a Fable session, builds go to `model: 'opus'` subagents; Fable plans,
  briefs and reviews. Every build/review brief points at `docs/info/review-checklist.md`
  (20 items traced to real findings here) and the phase's `docs/info/phaseN-design.md`.
- ⚠️ **Every decision is configurable BOTH ways (owner, 2026-08-27).** A default decided in chat lives in the
  settings registry (`settings_store.py`) so the Settings page and `/settings set-value` both reach it; per-item
  choices have a slash path AND a dashboard editor. Never hard-code a decided default. Checklist item 33.
