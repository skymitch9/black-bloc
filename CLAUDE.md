# Black Bloc — first-ten-minutes gotcha sheet

Thin on purpose. The living state is in `docs/` — **read `docs/README.md`,
`docs/TODO.md`, `docs/KNOWN_ISSUES.md` first**, every session (global rule).

- Python 3.12, venv at `.venv`. `pip install -e ".[dev]"`, `pytest`, `python -m black_bloc`.
- ⚠️ **CODE STYLE (owner, 2026-08-26): near-zero comments in code.** Explanations
  live in `docs/info/code-notes.md`, keyed by `path:line`, not in the source. One-line
  docstrings at most. `black_bloc/app.py` is a bare "run button"; `bot.py` is lifecycle
  only; every behaviour is its own module with helpers. Features are cogs under
  `black_bloc/cogs/` (`community/`, `moderation/`, `content/`), registered in `bot.py:COGS`.
  `code-notes.md` was re-keyed 2026-08-31 (header line says against which commit);
  when in doubt trust the anchor text in each note over the number, and re-key
  after every merge (the standing merge-order rule).
- Config comes ONLY from `black_bloc/config.py` (pydantic-settings, `.env`). Nothing
  else reads `os.environ`.
- Secrets: `.env` is gitignored; token custody is the Discord Developer Portal.
  Docs carry secret NAMES only.
- ✅ **TEST MODE LIFTED by the owner 2026-09-18 16:08** (`flyctl secrets set TEST_MODE=false`, cutover step P5; the
  bot now speaks wherever its settings point). The 2026-08-26 test policy (speak only in `#blackbloc-logs` + DMs, enforced by
  `black_bloc/guard.py` under `TEST_MODE=true`) is RETIRED for production; the guard code stays for any future rehearsal.
  Still true: never flip `TEST_MODE` yourself — it is the owner's switch both ways — and shadow modes per feature
  (`*_mode = shadow`) still route rehearsal copies to `shadow_channel_id`.
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
- `docs/` is **TRACKED** (owner, 2026-08-31: "actually lets keep it tracked" — `1eb8870`
  also dropped it from `.gitignore`; this retires the 2026-08-26 local-only rule). A clone
  has it, so ⚠️ **secret NAMES only under `docs/`, never values.**
  Every ask goes on `docs/TODO.md` the moment it is mentioned;
  finished items MOVE whole to `docs/DONE.md` in the session they land.
- Owner rule: on a Fable session, builds go to `model: 'opus'` subagents; Fable plans,
  briefs and reviews. Every build/review brief points at `docs/info/review-checklist.md`
  (35 items traced to real findings here) and the phase's `docs/info/phaseN-design.md`.
- ⚠️ **Minimise slash commands, maximise interactive windows (owner, 2026-09-03: "Let's try and
  minimize slash commands and maximize interactive windows").** One command per feature opens an
  ephemeral panel (embed + buttons + selects + modals); moves are buttons that render only when
  valid, never a status menu with two spellings of the same move. Requests is the pattern
  (`docs/info/requests-panel-design.md`); the rest of the app follows, feature by feature.
- ⚠️ **Staff always get the final say and the permission (owner, 2026-09-03: "Always give staff final
  say and permission").** Every stored decision has a staff move that reverses or overrides it (with a
  DM'd reason where a person is affected). Never design a terminal state staff cannot leave; never ask
  whether staff may act — gate it on staff/approver role and build it.
- ⚠️ **Every word the bot posts is editable on the site (owner, 2026-09-17: "lets make sure all the stuff in the
  need something ticket block is editable on the site, make that a standing black bloc rule").** A heading, a line, a
  button label, a note, a template — each is a settings key (registry + mock row + label) that the Settings page and
  the feature's own page can change, never a string only the code knows. The front door (`frontdoor_title`,
  `frontdoor_text`, the three labels, `rehearsal_note`) is the pattern; a posted copy re-renders when its words change.
- ⚠️ **Every decision is configurable BOTH ways (owner, 2026-08-27).** A default decided in chat lives in the
  settings registry (`settings_store.py`) so the Settings page and `/settings set-value` both reach it; per-item
  choices have a slash path AND a dashboard editor. Never hard-code a decided default. Checklist item 33.
