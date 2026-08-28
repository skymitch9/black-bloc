# Black Bloc — docs map

> **Audience:** Claude sessions first, the owner second. **Status:** LOCAL ONLY
> — `docs/` is gitignored (owner, 2026-08-26: peers get curated docs, not this
> working tree) and was purged from GitHub history the same day. It exists on
> this machine (OneDrive-synced) and nowhere else; see `access/RECOVERY.md`.
> Secret NAMES only, never values, regardless.
> Last verified: **2026-08-26** — the day the tree was created; every file in
> it was written against the code as it stood that afternoon. ⚠️ Nothing here
> has been checked against a *deployed* bot yet, because none exists.
>
> 📐 **The rules for this tree — filing, formatting, when to move things — live
> in [`DOCS_STANDARD.md`](DOCS_STANDARD.md) (§9 is the only project-specific
> part).** Read once; do not restate elsewhere.

**What this project is:** *Black Bloc*, a Discord **moderation and content**
bot. Python 3.12 + `discord.py` (gateway bot, one always-on process), SQLite
for state, an optional FastAPI companion server. Separate from the estate's
other bot (GABI, in `catalog-platform`, which is a Cloudflare Worker using the
HTTP-interactions model — a different animal; see `info/hosting.md` for why).

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

## Ten-second orientation

- **Run it:** [`access/setup.md`](access/setup.md) — venv, `.env`, Developer
  Portal steps, `python -m black_bloc`.
- **Host it:** [`info/hosting.md`](info/hosting.md) has the decision and the
  trade-off; [`access/deploy.md`](access/deploy.md) has the Fly.io runbook.
- **Extend it:** [`info/architecture.md`](info/architecture.md) — where a new
  feature goes (a cog under `black_bloc/cogs/moderation/` or `content/`).
- **Traps:** [`info/gotchas.md`](info/gotchas.md) — privileged intents,
  command-sync rate limits, SQLite inside a OneDrive folder.
