# Black Bloc — docs map

> **Audience:** Claude sessions first, the owner second. **Status:** TRACKED
> — `docs/` is in git and pushed (owner, 2026-08-31: "actually lets keep it
> tracked", commit `1eb8870`, which also dropped `docs/` from `.gitignore`).
> This retires the 2026-08-26 local-only rule, under which the tree was
> gitignored and purged from GitHub history. ⚠️ A clone now carries this tree,
> so: **secret NAMES only, never values.** See `access/RECOVERY.md`.
> Last verified: **2026-09-23 16:2x — the bot's version and two counts only**, at the v162 docs ritual: the bot is at **v162** (deployed 2026-09-23 16:20 Phoenix, release commit `4e6e4e4c`; [`deploys.log`](deploys.log) is the authority, 161 lines). `ls docs/info/*.md` now **113** (`chat-review-loop-design.md`), `ls docs/access/*.md` still **12**, the site **22** pages. One dated line added under *Where the bot stands*. ⚠️ **NOT re-checked:** that block's mode table and every other figure; nothing met a browser.
> Before that, **2026-09-23 15:1x — the bot's version and two counts only**, at the v160 + v161 docs ritual: the bot is at **v161** (deployed 2026-09-23 15:03 Phoenix, release commit `c8d2403d`; v160 the `foldout` hotfix at 14:20, `d7cda292`; [`deploys.log`](deploys.log) is the authority, 160 lines). `ls docs/info/*.md` still **112**, `ls docs/access/*.md` still **12**, the site **22** pages. One dated line added under *Where the bot stands*. ⚠️ **NOT re-checked:** that block's mode table and every other figure; nothing met a browser.
> Before that, **2026-09-23 14:1x — the bot's version and two counts only**, at the v158 + v159 docs ritual: the bot is at
> **v159** (deployed 2026-09-23 14:07 Phoenix, release commit `c54f14a8`; v158 at 12:51, `3dec2518`; [`deploys.log`](deploys.log) is the
> authority, 158 lines). `ls docs/info/*.md` now **112**, `ls docs/access/*.md` still **12**, the site **22** pages
> (`ls site/public/*.html`, `channels.html` new). One dated line added under *Where the bot stands*. ⚠️ **NOT re-checked:**
> that block's mode table and every other figure; nothing met a browser.
> Before that, **2026-09-23 — one count only**, at the loose-ends docs pass: `ls docs/info/*.md` still **108**; one dated
> line added under *Where the bot stands* (its mode table NOT re-read). Before that, **2026-09-23 04:3x — the bot's version and two counts only**, at the v157 docs ritual: the bot is at **v157**
> (deployed 2026-09-23 04:21 Phoenix, release commit `e9ecd0d0`; [`deploys.log`](deploys.log) is the authority, 156 lines).
> `ls docs/info/*.md` now **108** (`panels-orphaned-click-design.md` landed with v157), `ls docs/access/*.md` still **12**.
> ⚠️ **NOT re-checked:** the *Where the bot stands* block and every other figure; nothing met a browser.
> Before that, **2026-09-22 21:2x — the bot's version only**, at the v156 docs ritual: the bot is at **v156**
> (deployed 2026-09-22 21:18 Phoenix, release commit `4fb69e00`; [`deploys.log`](deploys.log) is the authority).
> `ls docs/info/*.md` still **107**, `ls docs/access/*.md` still **12**. ⚠️ **NOT re-checked:** the *Where the bot
> stands* block and every other figure; nothing met live Discord or a browser.
> Before that, **2026-09-22 — ONE number only**, at the v155 docs ritual: `ls docs/info/*.md`
> returns **107** (106 beside the index; the tree paragraph below said 105, counted 2026-09-21,
> before `spotlight-dates-design.md` landed). `ls docs/access/*.md` still returns **12** (11 beside
> its index), unchanged. ⚠️ **NOT re-checked at that pass:** the *Where the bot stands* block below,
> whose live mode values are still the conductor's 2026-09-18 report and which states no figure that
> v155 moved; nothing in the pass met live Discord or a browser. The bot itself is at **v155**
> (deployed 2026-09-22 13:35 Phoenix; [`deploys.log`](deploys.log) is the authority).
> Before that, **2026-09-19** — a docs-wide staleness pass after the TEST_MODE lift
> (owner: *"update all docs using opus and then im gonna swap"*), measured off `main`
> at `ffea17e`, which is **v141 LIVE**: `len(settings_store.KEY_TYPES)` (**277**),
> `storage/db.py:SCHEMA_VERSION` (**45**), `len(bot.COGS)` (**22**),
> `tests/test_bot.py:TOP_LEVEL_NOW` (**32**), `settings_store.namespace_of` over
> `KEY_TYPES` (**25** groups), `settings_store.FEATURES == logkinds.FEATURES`
> (**21**), `docs/deploys.log` (**140** lines, last = v141), `git ls-files docs`
> (**119** files), `ls docs/info/*.md` (**89** beside the index — this page said 88),
> `ls docs/access/*.md` (**11** beside the index — this page said 10),
> `ls site/public/*.html` (**20**). ⚠️ **NOT checked:** `pytest` was **not** run (the
> test figure below is the v141 deploy gate's, off `deploys.log`); `node
> site/mock/check.mjs` was **not** run (it needs a mock listening); nothing met live
> Discord, no browser rendered a page, and `python -m black_bloc` was not booted.
> Before that, **2026-09-11 08:32** — a docs-wide staleness pass (owner: "Update
> all docs"), re-measured off `main` at `1d090e5`, which is **v108 LIVE** (merge
> `73e2e44` of `where-smart`, deployed 2026-09-11 00:37): `pytest -n auto`
> (**5,546 passed**, 40 s), `SCHEMA_VERSION` (**34**), `len(settings_store.KEY_TYPES)`
> (**202** registry keys), `bot.py:COGS` (**19 cogs**), the command tree built the way
> `tests/test_bot.py` does (**29** top-level commands, **29** leaves, **zero**
> `app_commands.Group`s left), `site/mock/contract.json` (**17 pages / 150 routes /
> 115 action kinds**), `docs/deploys.log` (**107 lines**, last = v108),
> `git ls-files docs` (**94 files**), `ls site/public/*.html` (**17**).
> ⚠️ **NOT checked:** anything against the live bot or the live dashboard **in a
> browser**; no Discord button was pressed and `python -m black_bloc` was not booted
> (a worktree holds no token); the mock's *live* check (`node site/mock/check.mjs`
> needs `site/mock/server.mjs` running — the 17/150 figures were read out of
> `contract.json`, which is what both halves read); `info/code-notes.md`'s `path:line`
> keys; the `archive/` dumps' contents; and the per-item wording of
> `info/review-checklist.md`. Before that,
> **2026-09-02** — re-measured on the Phase 15 (F14) branch,
> which was then NOT merged and NOT deployed: `pytest` (**2714 tests**),
> `node site/mock/check.mjs` (**17 pages / 111 routes**),
> `ruff check black_bloc tests site` (clean), `SCHEMA_VERSION` (**21**),
> `bot.py:COGS` (**15 cogs**, **37** top-level slash commands). Before that,
> 2026-08-31 — a docs-wide staleness audit measured against
> the repo: `git log` / `deploys.log` (37 deploys, last `8036918` at 2026-08-27
> 20:15), `pytest --co` (**2158 tests**), `node site/mock/check.mjs` (**17
> pages / 89 routes**), `SCHEMA_VERSION` (**16**), `bot.py:COGS` (**14 cogs**).
>
> 📐 **The rules for this tree — filing, formatting, when to move things — live
> in [`DOCS_STANDARD.md`](DOCS_STANDARD.md) (§9 is the only project-specific
> part).** Read once; do not restate elsewhere.

**What this project is:** *Black Bloc*, a Discord **moderation and content**
bot. Python 3.12 + `discord.py` (gateway bot, one always-on process), SQLite
for state, and a FastAPI companion that serves both the API and the dashboard
from **one** hostname — https://blackbloc.heygabi.ai (`API_ENABLED=true` in
`fly.toml`; it was "optional, off by default" until Phase 8a). Separate from the
estate's other bot (GABI, in `catalog-platform`, which is a Cloudflare Worker
using the HTTP-interactions model — a different animal; see `info/hosting.md`
for why).

---

## The tree

| File | Question it answers | Read when |
|---|---|---|
| [`TODO.md`](TODO.md) | What is active, blocked, or waiting on the owner? | **Every session, first** |
| [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md) | Is this wrong on purpose? | **Before fixing anything** |
| [`DONE.md`](DONE.md) | Was this solved before, and why that way? | When something feels familiar |
| [`access/`](access/README.md) | How do I run / deploy / reach / recover it? | Operating it |
| [`info/`](info/README.md) | How does it work, and why built this way? | Changing it |
| [`archive/`](archive/README.md) | What did this look like before? | Rarely |
| [`DOCS_STANDARD.md`](DOCS_STANDARD.md) | What shape must this tree keep? | Before adding a doc |
| [`deploys.log`](deploys.log) | What is live, and when did it ship? | Before any deploy or rollback |

⚠️ **Everything under `docs/` is reachable from this table.** The eight rows above
are the *whole* top level (nothing else may live there — `DOCS_STANDARD.md` §1).
The individual files in `access/` (**11** beside its index) and `info/` (**106**
beside its index — re-counted **2026-09-22** at the v155 ritual, `ls docs/info/*.md` returns 107 including the index; it was 105 on 2026-09-21 at the v151 ritual, before `spotlight-dates-design.md` landed, and 89 on 2026-09-19. `access/` is unchanged at 11. The `mock-direction-a/` folder is beside them)
are listed by their own indexes, [`access/README.md`](access/README.md) and
[`info/README.md`](info/README.md), not here — this page does not duplicate an
index (§7). `archive/` holds the retired docs and the one-off `current-bots/`
dumps, indexed by [`archive/README.md`](archive/README.md).

## Where the bot stands right now (2026-09-19)

**2026-09-23 16:2x:** v162 live (three merges: banter gets banter — small talk carries no notes; a popup-picked channel, role or member mention matches its note like the typed name; weak replies land in a review queue on the Chat page, tagged by the cheap model, approved by staff with one click — the queue empty at boot; schema 58, 418 keys; see [`DONE.md`](DONE.md) 2026-09-23 v162); the mode table below was NOT re-read.

**2026-09-23 15:1x:** v161 live (one merge: channel reach — a channel members reach through a role they pick is told to the bot, staff override per channel, The Basement on the ignore list; told 31 of 94, was 24), after the v160 hotfix at 14:20 that made the Chat page render again (see [`DONE.md`](DONE.md) 2026-09-23 v161 / v160); the mode table below was NOT re-read.

**2026-09-23 14:1x:** v159 live (four merges: channel catalog, post today's birthdays, the Channels page, personality tones; v158 at 12:51 was the Birthdays Change button) — the drafts seed and the tone bodies verified live at boot, and the chat voice is `cookout`, so no tone is heard yet (see [`DONE.md`](DONE.md) 2026-09-23 v159); the mode table below was NOT re-read.

**2026-09-23:** v157 live; spotlight + YouTube channel rows verified live at boot (see [`DONE.md`](DONE.md) 2026-09-23); the mode table below was NOT re-read.

✅ **`TEST_MODE` is OFF since 2026-09-18 16:08** — the owner ran
`flyctl secrets set TEST_MODE=false` (cutover step **P5**,
[`info/cutover-plan.md`](info/cutover-plan.md)). The 2026-08-26 test policy — *the bot
speaks only in `#blackbloc-logs` and DMs* — **is history**; `black_bloc/guard.py` is
still in the tree but is not installed in production. Any doc sentence below that reads
"while test mode is on" describes what WAS true; the dated notes say when it stopped.

**What holds the bot back now is per-feature modes, not the guard:**

| State | Features |
|---|---|
| **LIVE to members** | events (`events_mode`), requests (`request_mode`), modmail (`modmail_enabled`) — owner, 2026-09-18 17:1x: *"its live and people can use it"* |
| **`shadow`** — the rehearsal copy goes to `shadow_channel_id` (`#welcome-test`), nothing to the real channel | `frontdoor_mode` (set 2026-09-18 16:57, aimed at `#welcome`), `golive_mode`, `poll_mode`, `birthday_mode`, `tempvoice_mode`, `honeypot_mode`, `automod_mode` |

⚠️ **Never flip `TEST_MODE` yourself — it is the owner's switch, both ways.**
⚠️ **These live values were reported by the conductor on 2026-09-18, not re-read here** —
the Settings page needs a Discord sign-in. https://blackbloc.heygabi.ai/settings.html is
the one place they can be read for certain.

## Ten-second orientation

- **Run it:** [`access/setup.md`](access/setup.md) — venv, `.env`, Developer
  Portal steps, `python -m black_bloc`.
- **Host it:** [`info/hosting.md`](info/hosting.md) has the decision and the
  trade-off; [`access/deploy.md`](access/deploy.md) has the Fly.io runbook.
- **Extend it:** [`info/architecture.md`](info/architecture.md) — where a new
  feature goes (a cog under `black_bloc/cogs/moderation/` or `content/`).
- **Traps:** [`info/gotchas.md`](info/gotchas.md) — privileged intents,
  command-sync rate limits, SQLite inside a OneDrive folder.
