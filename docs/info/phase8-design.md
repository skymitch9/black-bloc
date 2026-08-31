# Phase 8 design — the config website for mods and admins (F12)

> **Audience:** the owner (this is the acknowledgment and the plan) and the
> Phase 8 build agents. **Status:** TRACKED (2026-08-31; private repo). **Last verified:
> 2026-08-26** — the estate template inventory was read from
> `catalog-platform/sites/heygabi-home/public/` and
> `catalog-platform/docs/info/estate-themes.md` that day; the dashboard
> feature inventory is `reference-bots.md` (Carl, YAGPDB). Depends on
> Phases 1–7 having shipped their settings keys — the site is a *view* of
> those, never a second store.

## The owner's ask, verbatim (2026-08-26)

> "we're going to need to make a site so the mods and admins of this discord
> can configure the bot too. Grab all the details from other known and
> popular bots and wire up all the same stuff. We want a full functional site
> and instead of starting from scratch lets use the amazing templates we
> already have."

## Placement and why

**Phase 8, immediately after the seven core phases.** Not an afterthought:
the foundation is being laid *now* — Phase 1's settings store gives every
knob a typed key, a default, an audit row (`updated_by`, `updated_at`), and a
slash command; the site is the second client of that same store. Building
the site before the settings exist would mean building it twice.

Two milestones so it is visible early:
- **8a — read-only status page** (can go right after Phase 2): bot health,
  mode of every feature, last 50 action-log lines, open modmail count. No
  writes → no auth risk → shippable fast.
- **8b — full dashboard**: every settings page, with writes, audit, and
  role-gated access.

## What "all the same stuff" means — the page inventory

Mapped from Carl's and YAGPDB's dashboards (`reference-bots.md`) onto Black
Bloc's features. Each page = one settings namespace + its action-log slice.

| Page | Sourced from | Controls |
|---|---|---|
| **Overview** | YAG home | every feature's mode (off/shadow/on) at a glance, bot status, uptime, last deploy, quick links |
| **Go-live** | YAG Streaming | channel, template (live preview), live role, require/ignore roles, cooldown, ping role, opt-out list, Twitch links table, last 20 announcements |
| **Role menus** | Carl Reaction roles | menus table, per-menu editor (options, emoji, mode), "post/re-post" button, take-up counts |
| **Events** | *new* (nothing incumbent) | category, announce channel, ping role, create-scheduled toggle, approver roles (read-only: derived from staff channel), pending/approved queue with Approve/Deny |
| **Birthdays** | Birthday Bot dashboard | channel, template, colour, role, show-age, mode, the birthday list (paginated by month), import report |
| **Temp voice** | TempVoice dashboard | creator channels, name template, allowed role, mode, live list of spawned channels |
| **Honeypot** | Honeypot Bot / Carl Honeypot | trap channels, mode, purge days, exempt roles, hits table with "Ban now" for shadow hits |
| **Moderation** | Carl Automod + Moderation | per-rule editor (enabled, window, threshold, actions), exempt roles/channels, DM style, modlog channel, **cases table** (search by user), **parity report** |
| **Modmail** | Modmail config | mode (channel/thread), category/staff channel, log channel, enabled, snippets editor, blocks, open tickets |
| **Logging** | Carl Logging | log channel, which event kinds post embeds vs DB-only |
| **Settings audit** | *new* | every `settings.set` with who/when/before/after; revert button |
| **Access** | *new* | who can see the dashboard (derived from staff roles) and who is signed in now |

## Architecture

```
Browser ──HTTPS──▶ Cloudflare Pages (static: HTML/JS, estate theme, estate UX)
                         │  fetch /api/… with session cookie
                         ▼
               Fly app "black-bloc" — FastAPI inside the bot process (black_bloc/api/)
                         │  reads/writes the SAME SettingsStore + SQLite the bot uses
                         ▼
                    Discord (OAuth2 for login; the bot's own gateway for live data)
```

- **Front end**: a static site in this repo under `site/` (committed — it IS
  the product), deployed to **Cloudflare Pages** like the rest of the estate
  (`wrangler pages deploy site/public`, directory-deploy rules apply: clean
  tree only). It copies, verbatim, the estate assets: `estate-theme.css`,
  `theme.js` (the 5-theme dropdown), `status-shell.css`, `permission-ux.js`,
  `motion.js`, the fonts — and follows `estate-themes.md` §3a so a sixth
  theme reaches this site the same mechanical way it reaches the others.
  Plain HTML + small JS modules, no framework (same as heygabi-home);
  forms post JSON to the API.
- **API**: the existing `black_bloc/api/server.py` FastAPI app, grown into
  routers per page (`/api/settings/<ns>`, `/api/golive/links`,
  `/api/mod/cases`, …). Exposed via a Fly `[http_service]` on the same
  machine — **with `auto_stop_machines = false` and `min_machines_running =
  1`**, because the default auto-stop would kill the gateway websocket
  (`hosting.md`). CORS locked to the site's origin.
- **Auth — Discord OAuth2**, because the question the site must answer is
  "is this person a mod/admin *of this guild*", which only Discord can
  attest: scopes `identify` + `guilds.members.read`; the callback reads the
  member's roles in the guild and admits them iff they hold a staff role
  (Phase 1's `staff_role_ids` derivation — the same rule as slash commands)
  or `manage_guild`. Session = signed HttpOnly cookie, 7 days. The estate's
  `estate-auth.js` SSO remains an *option* for owner-level login later;
  Discord is the primary because mods do not have estate accounts.
  Secrets: `DISCORD_CLIENT_SECRET` (the app already exists), `SESSION_SECRET`
  — names only in docs, values in `fly secrets`.
- **Permission UX** (global rule): a non-staff visitor sees a page that says
  *"This dashboard is for the mods and admins of Black in a Flash!. Ask a
  Lead for the role."* — never a bare 403; the four causes (not signed in /
  signed in but not staff / session expired / API down) each get their own
  sentence, and an API outage is never described as a permission problem.
- **Writes**: every PUT goes through the same `SettingsStore.set(...,
  by=user_id)` the slash commands use, so the audit trail is one table; the
  bot picks up changes live (the store is in-process). No second store, no
  cache to invalidate.

## Owner decisions — DECIDED 2026-08-26 (verbatim in `TODO.md`)

1. **Hostname: `blackbloc.heygabi.ai` for now**, ported to the org's own
   domain once they pick a name. Build with the hostname as one config value
   (CORS origin, OAuth redirect, cookie domain) so the port is a settings
   change plus a DNS record, not a rebuild.
2. **Entirely disconnected from heygabi.** It shares a *domain* and nothing
   else: no `estate-auth.js`, no auth-worker, no estate status pages, no
   shared deploy scripts, no runtime dependency of any kind. The "templates"
   are **copied** assets (theme CSS/JS, fonts, permission-UX) — a snapshot,
   not a link. The §3a "mechanical theme propagation" idea is therefore
   **withdrawn** for this site: a new estate theme reaches Black Bloc only
   if someone copies it in.
3. **Login: Discord verification ONLY** for everyone — **except the owner's
   Google SSO**, which is the owner-admin of the whole domain. Concretely:
   two identity providers, Discord OAuth2 (staff) and Google OAuth2 (owner,
   allow-listed to the owner's Google account only), both first-party to
   this app. **Future:** link the owner's Discord identity to the Google SSO
   identity so both resolve to one admin (a `user_identities` table keyed
   on a local account id — design it in now, wire Google later if it slows
   8b).
4. **Who gets in:** exactly the roles that can currently see
   `#mute-me-bot-test-spam` — `Aunties / Uncles` and the roles above it.
   This is Phase 1's `staff_role_ids` derivation from `staff_channel_id`,
   so the site and the slash commands share one definition; changing the
   channel's overwrites changes both.

## Build shape (when its turn comes)

Two or three Opus builders: **API routers + auth** (one), **site shell +
theme + overview/status** (one), **feature pages** (one, possibly two).
Tests: API routes with FastAPI's test client against a temp DB; auth
role-gate matrix; a Playwright smoke is optional. Deploys: Pages for the
site (`deploys.log` line), Fly for the API.

## Not in scope

Public-facing pages (member self-service like "set my birthday" on the web)
— a later ask if wanted; everything here is staff-only.
