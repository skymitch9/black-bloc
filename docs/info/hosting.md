# Hosting — why not Cloudflare, why Fly.io

> **Audience:** the owner (this is a decision doc) and Claude sessions.
> **Status:** TRACKED (owner, 2026-08-31 — was local-only until then; secret
> NAMES only). Last verified: **2026-09-11 08:45** — docs-wide staleness pass. **What was
> re-read off `main` at `1d090e5`:** `fly.toml`, `Dockerfile`, `scripts/deploy.ps1`,
> `../deploys.log`. **What that FIXED:** the deploy count (37 → **107**, last `73e2e44`
> v108 at 2026-09-11 00:37) and the last section, which said `fly.toml` deliberately has
> **no** `[http_service]` and that **none of it has been deployed** — both were already
> false when written and are the opposite of the truth today. ⚠️ **NOT re-checked:** the
> *prices* below are still from memory (knowledge cutoff Jan 2026) and must be confirmed on
> the providers' pages before anyone relies on them; the *reasoning* about gateway vs
> Workers was not re-derived; nothing here met Fly's console, Discord or a browser.
> Before that, **2026-08-31** — the *reasoning* was
> checked against how Discord's gateway and Workers work; the *prices* were
> from memory and not re-checked.
> ✅ **DECIDED and SHIPPED: Fly.io** (owner, 2026-08-26). The "PENDING the owner"
> line that stood here until 2026-08-31 was stale — the app has been running on
> Fly (`black-bloc`, machine `85e744c4d959d8`, region `lax`) since 2026-08-26,
> with **107** deploys in [`../deploys.log`](../deploys.log) (37 when this line was
> written). Runbook: [`../access/deploy.md`](../access/deploy.md).

## The owner's ask

> "see if we can host the bot in cloudflare or something so i dont need to be
> around to run it in a local docker" — 2026-08-26

Two requirements: **(a)** runs without the owner's machine, **(b)** Cloudflare
if possible.

## Why (b) does not fit THIS bot

Discord bots come in two shapes, and the shape is decided by what the bot
needs to *see*:

| Shape | How Discord reaches it | What it can do | What it cannot do |
|---|---|---|---|
| **HTTP interactions** (what GABI in `catalog-platform` is) | Discord POSTs each slash command / button to a URL | Respond to commands and components | See messages, joins, edits, reactions, voice — **any event that was not a user invoking the bot** |
| **Gateway** (what Black Bloc is) | The bot opens a websocket and holds it open | Everything above PLUS every server event | Run anywhere that cannot hold a connection open 24/7 |

A **moderation** bot is made of events: a message arrives and gets filtered, a
member joins and gets screened, a raid starts and gets rate-limited. Those
only exist on the gateway. Cloudflare Workers are request-driven and cannot
hold a persistent outbound websocket, so a Workers bot is HTTP-interactions
only — fine for GABI, wrong for this.

Two refinements, both checked against the cutoff, neither verified today:
- **Cloudflare Containers** (2025) are still request/alarm-driven with
  sleep-on-idle; a Durable Object could try to keep one awake, but that is a
  fight with the platform, not a fit.
- **Discord's built-in AutoMod** covers a lot of *message filtering* without
  any gateway at all, and an HTTP-interactions bot can configure it. If the
  feature asks turn out to be "slash commands + AutoMod rules + scheduled
  posts", a Workers bot in TypeScript becomes viable again. ⚠️ Re-check this
  fork when the first feature list arrives — it is the one thing that could
  flip the decision.

## Recommendation for (a): Fly.io

| Option | Always-on? | Effort | Cost class (unverified) | Verdict |
|---|---|---|---|---|
| **Fly.io** (`fly deploy` of the repo `Dockerfile`, 1 GB volume for SQLite) | Yes | Low — CLI + 5 commands (`../access/deploy.md`) | ~$2–4/mo | **Recommended** |
| Railway | Yes | Low, similar | ~$5/mo floor | Fine alternative |
| VPS (Hetzner / DigitalOcean) + Docker | Yes | Medium — you own patching, restarts, Docker | ~$4–6/mo | OK if a VPS already exists |
| Oracle Cloud free tier ARM | Yes | High — capacity lottery, ARM image quirks | $0 | Not worth the owner's time |
| Cloudflare Workers | N/A | — | — | **Cannot host a gateway bot** |
| Local Docker on the owner's PC | Only while the PC is on | — | $0 | The thing the owner is trying to stop doing |

Cloudflare can still be *part* of the picture later — a Tunnel or DNS in front
of the FastAPI dashboard — without hosting the bot process.

## What is in the repo for this (read 2026-09-11)

| File | What it actually says |
|---|---|
| `Dockerfile` | `python:3.12-slim`, **no secrets baked in** (`DISCORD_TOKEN` arrives from the host's secret store). Installs the package, copies `site/public` so one hostname serves the dashboard too, `VOLUME ["/data"]`, `CMD python -m black_bloc` |
| `fly.toml` | app `black-bloc`, `primary_region = "lax"` (nearest to Phoenix — Fly has no `phx`). `[env]` sets `DATABASE_PATH=/data/black_bloc.sqlite3`, `API_ENABLED=true`, `API_HOST=0.0.0.0`. `[mounts]` `black_bloc_data` → `/data`. `[[vm]]` `shared-cpu-1x` / 256 MB |
| `scripts/deploy.ps1` | **the one deploy path** (incident 2026-09-01: an ungated chain deployed on a red suite). Refuses a dirty tree; gate = ruff → `pytest -n auto` → every `site/public/assets/*.js` through `node --check` → `node site/mock/check.mjs` against the mock server. Escape hatch `BLACKBLOC_SKIP_GATE=1`, emergency only. Appends the `../deploys.log` line on success |

⚠️ **`fly.toml` DOES carry `[http_service]`** — this section said the opposite until
2026-09-11. It has to: the dashboard (`black_bloc/api`) is served by the same process. What
makes that safe is the three flags beside it — **`auto_stop_machines = false`,
`auto_start_machines = false`, `min_machines_running = 1`** — which are **load-bearing, not
tuning**: this machine also holds the persistent outbound gateway websocket, and Fly's
default auto-stop-on-idle would kill it. *An idle HTTP service is not an idle bot.* Never
let a later `fly launch` or a "sensible defaults" edit flip those three, and never run
`fly launch` at all — it rewrites the file. Deploy with `--ha=false`.
