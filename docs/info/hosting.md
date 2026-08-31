# Hosting — why not Cloudflare, why Fly.io

> **Audience:** the owner (this is a decision doc) and Claude sessions.
> **Status:** TRACKED (owner, 2026-08-31 — was local-only until then; secret
> NAMES only). Last verified: **2026-08-31** — the *reasoning* is
> checked against how Discord's gateway and Workers work; the *prices* are
> from memory (knowledge cutoff Jan 2026), were NOT re-checked today, and must
> be confirmed on the providers' pages before anyone relies on them.
> ✅ **DECIDED and SHIPPED: Fly.io** (owner, 2026-08-26). The "PENDING the owner"
> line that stood here until 2026-08-31 was stale — the app has been running on
> Fly (`black-bloc`, machine `85e744c4d959d8`, region `lax`) since 2026-08-26,
> with 37 deploys in [`../deploys.log`](../deploys.log). Runbook:
> [`../access/deploy.md`](../access/deploy.md).

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

## What is already in the repo for this

`Dockerfile` (python:3.12-slim, no secrets baked in), `.dockerignore`,
`fly.toml` (no `[http_service]` on purpose — that would enable auto-stop and
kill the websocket; `[mounts]` for `/data`). None of it has been deployed.
