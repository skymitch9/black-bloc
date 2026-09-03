# Black Bloc — the full feature list

> **Audience:** the owner (to approve the shape and order) and every future
> session (as the map of what gets built). **Status:** TRACKED (owner,
> 2026-08-31 — was local-only until then; secret NAMES only).
> **Last verified: 2026-08-26 evening** — every "measured" fact below comes
> from that day's captures: `archive/current-bots/discord-scan-2026-08-26.md`
> (128/128 channels, 12,488 messages), `carl-bot-dashboard-2026-08-26.md`,
> `yagpdb-dashboard-2026-08-26.md`, `birthday-bot-export-2026-08-05.md`, and
> `info/reference-bots.md` (vendor docs). Owner decisions are dated in
> `TODO.md`.
> ⚠️ **The "nothing here is built" line that stood here until 2026-08-31 was
> false and is removed.** Measured 2026-08-31: nearly all of F1–F18 is built and
> LIVE — `docs/deploys.log` records 37 deploys, the last `8036918` at
> 2026-08-27 20:15 (35 slash commands, schema 16, 17 dashboard pages / 89
> routes, 2158 tests). The per-row **Status** column below is the authority on
> what shipped; the *incumbent* measurements in this file are still the
> 2026-08-26 captures and were NOT re-taken.

## What the server runs today, and what replaces it

| Incumbent | What it actually does here (measured) | Black Bloc feature |
|---|---|---|
| **YAGPDB** | `#live-now` go-live feed (~8/day, 30 streamers); reaction polls; timezone conversions in `#mod-central`. Automod OFF. No role menus despite the dashboard's "7 role commands". | F1, (polls → F15 future), F4's HammerTime replaces the tz habit |
| **Carl-bot** | 5 reaction-role panels in `#roles` (23 roles); modlog to `#carlbot-logs`; automod with ONE armed rule (mention-spam 5/30s); welcome text in `#welcome`; reminders. 7 warn cases in 2 years. | F16 role menus, F7 moderation |
| **ModMail** | Channel-per-user tickets; staff talk privately inside a ticket by prefixing `=`. 5 open. | F11 |
| **Birthday Bot** | Embed in `#return-of-the-gen` at each member's own midnight; 39 birthdays on file; free tier, vote-gated. | F6 |
| `Verification Bot`, `baf`, `Black Block` | Dormant (the last two are earlier attempts at this project). | none — kick later |
| `Wordle` | Discord built-in activity webhook, 422-day streak. | leave alone |

## The features

Legend — **Decided**: every design blank is filled and a design doc can be
written. **Parked**: owner deferred it. **Future**: owner asked, not yet
scoped.

| # | Feature | State | One-line shape | Key decisions / measured constraints |
|---|---|---|---|---|
| F1 | **Go-live feed** → `#live-now` | Decided | **Discord presence is PRIMARY**; Twitch EventSub is the fallback/enrichment for linked accounts; posts with the `REGULATORS! Mount up!` prefix; opt-out | Keep YAG's wording; `/twitch link` (login ≠ Discord name); debounce re-posts; fallback when game is empty; rich card = Discord link preview |
| F2 | Twitch activity tracking | Decided → merged into F1 | Same detection; optional *Live* role; require/ignore role filters; no stats | "Scan for inactive streamers" still TBD |
| F3 | YouTube go-live | Decided → shipped via presence 2026-08-27; no YouTube API fallback (no key) | Discord presence carries the platform, so a "Streaming on YouTube" activity announces with the member's YouTube URL; `{platform}` is a template field and the session records it | Twitch enrichment is refused for any non-Twitch stream, so a Twitch-linked member streaming on YouTube is never overwritten. ⚠️ **Presence only** — it needs the member's YouTube connection plus "display current activity"; a YouTube stream Discord does not show is invisible. A polling fallback (the YouTube Data API, the way Helix backs Twitch) needs an API key and a `/youtube link` command; not built |
| F4 | **Event form** → review → Scheduled Event | Decided | `/event create` modal → channel `pending-<user>-<event>` under *Events* → Approve/Reject → real Discord Scheduled Event + `<t:…>` announcement | Approvers = roles that can see the staff channel; per-user `/timezone set` (Discord exposes no tz); create-event toggle ON |
| F5 | Event go-live ping | Decided | Post in `#live-now` when an approved event starts; role ping is a setting (default none) | Channel + role editable in options |
| F6 | **Birthdays** | Decided | Import 39 rows; opt-in; embed `Happy Birthday **{name}**!` in `#return-of-the-gen` | Incumbent fires at each member's OWN midnight — 15/16 land the evening before in Phoenix terms. Decided: per-member midnight, server midnight (Phoenix) as fallback |
| F7 | **Moderation** | Decided | Reproduce the incumbent's live config as-is + warn/timeout/kick/ban + modlog + exempt roles; **shadow → watch → on**, tune in shadow | Only ONE rule is armed today; quiet server; no Muted role (native timeouts). ⚠️ **The parity tool was REMOVED at the owner's request, 2026-08-27** ("Carl bot has no actions or setup, lets remove the mentions and parity to it") — `/automod parity`, `GET /api/mod/parity`, the dashboard's parity card and the `carl_modlog_channel_id` setting are all gone. **The cut-over criterion is now the owner's judgement from the shadow log**, not a measured agreement count. The rules themselves are unchanged: mention-spam armed, the rest log-only. |
| F8 | **Temp voice** | Decided | "join to create a channel" above the AFK channel; `{user}'s bloc`; owner panel; Member-only | No lobby exists today — greenfield |
| F9 | **Honeypot** | Decided | Bottom channel, pinned warning; post → ban + purge, **shadow-first**; exempt = bots + staff; log to the log channel | Vendor never documents triggers/exemptions — ours are explicit |
| F10 | @-mention conversation | **Step 1 shipped 2026-08-27** (canned intents); **step 2a shipped 2026-08-27** — editable intents and lines in storage (`chat_intents` / `chat_lines`, schema 15), classification over a guild's own rows, six data intents (live / next event / birthdays / head count / my roles / timezone), `need_a_mod` routing, four manners settings and the eight `/api/chat` routes; **step 2b (11b) built on its own branch, not merged** — the Chat page; step 3 = a real conversation backend | `black_bloc/chat.py` sorts an @-mention into one of eight intents (greeting, thanks, how_are_you, what_can_you_do, help, love, insult, unknown) and answers in the bot's voice; `chat_mode` (default on), `chat_cooldown_seconds` (default 20), `chat_ignore_channels`, `chat_greeting_reaction`, `chat_reply_in_threads` (default on) and `chat_route_ping_staff` govern it | **Next: merge 11a and 11b together** — both touched `site/mock/contract.json` and `site/mock/server.mjs`, so those two files will conflict; take 11a's real-router shapes as the truth and reconcile the mock to them. **Step 3 = a real conversation backend**, which replaces the one seam `chat.reply_for(text, member, bot)` — now a coroutine — and nothing else. Still needs provider, key and cost cap — see `code-notes.md` § *chat — @-mention replies* |
| F11 | **Modmail** | Decided | Channel-per-ticket like today **plus** a threads-in-one-channel mode as a setting | Must keep the `=` private-staff-note workflow (or an equivalent) |
| F12 | **Config website** | Designed (`phase8-design.md`) | Cloudflare Pages site in the estate template + Discord-OAuth staff login + FastAPI routers in the bot; 12 pages mapped from Carl/YAG dashboards | 8a status page after Phase 2; 8b full dashboard after Phase 7 |
| F13 | Verification Bot use cases | Closed | dormant, nothing to port | — |
| F14 | **Ping roles** | **BUILT 2026-09-02 on the Phase 15 branch — not merged, not deployed, and never run against live Discord** | One opt-in **Events** role, made or reused by `/pingroles setup`, which points BOTH `golive_ping_role_id` and `events_ping_role_id` at it and puts it on a **Notifications** role menu; plus a **role per streamer** (`golive_fan_roles`, schema 21) that only their followers wear. `/pings follow`, `unfollow`, `list`, `events on`/`off` and `fans on`/`off` for everybody; `/pingroles setup`, `streamer add`/`remove`/`list` and `logs` for staff, `/api/pings/*` + a Pings section on the Go-live page, and auto-maintained **Streamer pings** panels (25 a select, `streamers`, `streamers-2`, …). A go-live announcement reads `<@&events> <@&fan> REGULATORS! …`, deduplicated, and the fan role is read AFTER the cooldown gate so a suppressed announcement never pings | Seven decisions are settings keys, not constants: `pings_mode` (ships **off**), `pings_log_level`, `pings_events_role_name`, `pings_fan_role_creation` (self/staff/auto), `pings_fan_role_template`, `pings_fan_role_on_unlink` (keep/delete), `pings_fan_role_delete` — [`phase15-design.md`](phase15-design.md). ⚠️ **Nothing here has met a real Discord role**: role creation, panel refresh and the Manage Roles ordering are all test-suite evidence only |
| F15 | Polls | **shipped 10a+10b, 2026-08-27** | YAG reaction polls are used in `#announcements` | Native Discord polls plus a Black Bloc panel for what native cannot do. `/poll create|end|cancel|results|list|settings` and `/poll recur create|list|pause|delete`; kinds single / checkbox / yes-no / rating / **date**; the panel carries anonymous votes, results-at-close and up to 25 options; review switch, last-call + close + archive loop, results embed, CSV export, and the **Polls** dashboard tab with a create form — [`phase10-design.md`](phase10-design.md), [`polls-research.md`](polls-research.md), [`code-notes.md`](code-notes.md) § *polls (10b)*. ⚠️ **Not merged, not deployed, and nobody has voted on either surface yet** — one probe poll was posted to measure `<t:…>` in an answer label and left in the test channel. v2 kinds (free text, number, ranked) are still refused by name |
| F16 | **Role menus** | Needed (found) | Replace Carl's 5 panels: pronouns, play-style, mentor/initiate, interests, event alerts — measured emoji→role maps | Buttons/selects instead of reactions; migrate without stripping anyone's roles |

## Cross-cutting (every feature)

- **Test policy** — everything runs inside `#mute-me-bot-test-spam` + DMs
  until the owner lifts `TEST_MODE`; side effects check `bot.guard`.
- **Rollout** — anything that acts on members ships shadow/log → watch → on,
  flipped per feature; the incumbent stays on until parity is measured.
- **Settings** — every knob named above is a stored setting with a slash
  command now and an F12 page later; no hard-coded channel/role IDs in code.
- **Logging** — one log channel (`#mute-me-bot-test-spam` now → renamed `#black-block-logs` later; it is a setting); every action the bot takes on a
  member is one line there with who/what/why.
- **Permissions** — the bot holds `Bots` (Administrator) by owner decision;
  the code still checks *its own* permission model so a future narrowing
  does not break it.
- **Code shape** — near-zero comments, `code-notes.md`, one cog per feature,
  tests mirror the package, only bot code committed.

## Proposed build order (owner to approve)

Each phase = one design doc → one Opus build agent → review → deploy in
shadow/test mode → owner verifies in the test channel.

| Phase | Features | Why this order |
|---|---|---|
| 1 | **Settings store + log channel + role menus (F16)** | Every later feature needs settings + a log channel; role menus are the most-used incumbent surface and zero-risk (no punishments) |
| 2 | **F1 go-live feed** | Highest-traffic incumbent (~8 posts/day); presence path first, EventSub second |
| 3 | **F8 temp voice + F9 honeypot** | Both greenfield — nothing to migrate, quick wins |
| 4 | **F4/F5 events** | Biggest new capability; needs the settings store |
| 5 | **F6 birthdays** | Import + one scheduled job; blocked only on Q12 |
| 6 | **F7 moderation (shadow)** | Shadow for a week, then cut over on the owner's read of the shadow log (2026-08-27: the parity tool that used to measure this was removed) |
| 7 | **F11 modmail** | Highest human-workflow risk; last of the core |
| 8 | **F12 config website** (8a status page may run after Phase 2) | Needs every feature's settings keys to exist first |
| — | F10, F14, F15, F3 | After core |

## Still open

- **Q13** build-order approval · Twitch developer app credentials (owner, in progress; fallback path only).
| F18 | **Requests** | **13a shipped** 2026-08-27 | The "initial doc" of ideas on paper | `/request create\|list\|withdraw\|set`, the `requests` tables and the `/api/requests` routes are **in (13a)**; the dashboard page is **13b**. Modal takes what, why and an optional `YYYY-MM-DD` due date, requester automatic; mod-or-higher auto-approved; [`phase13-design.md`](phase13-design.md). Not run against live Discord |
