# Black Bloc — TODO (active work only)

> **Audience:** Claude sessions and the owner. **Status:** TRACKED (owner,
> 2026-08-31 — was local-only until then; secret NAMES only).
> Last verified: **2026-08-31** — the docs audit re-measured every *deployment
> status* line against `deploys.log` and `git merge-base`, and the bookkeeping
> sweep the same morning then MOVED all 30 landed 2026-08-26/27 items whole to
> `DONE.md` (owner-verification residue consolidated into `access/sweeps.md`
> rows 18–20 + its phase-script appendix). What remains below is genuinely
> active or waiting.
>
> Finished items MOVE whole to [`DONE.md`](DONE.md) in the session they land.
> Accepted defects go to [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md), not here.

## 🎯 Feature asks — the first list (owner, 2026-08-26, verbatim then expanded)

Owner's words: *"Go live message for #live-now channel / Twitch activity
tracking on anyone in the discord (want an opt out, might need to scan for
people that dont have activity but tbd) / Youtube maybe / Event form
submission (someone fills out the information and the event is made in
discord) / Let form submission go to a mod review channel, make sure form uses
hammer time or normalizes timezone by user / Have bot ping when an event is
live / Birthday announcements / Opt in, cutover time / Moderation / Copy for
most moderation settings from other bots, exceptions list to be fined tuned
(pinging multiple people, role based exceptions) / Temporary voice channel —
https://tempvoice.xyz — Steal this / https://www.honeypotbot.com — Steal this /
Personality for the bot can be @d"*

Status: **BUILDING IN PARALLEL (owner, 2026-08-26 20:38: "do what you can to start working in parallel").** **EVERYTHING BUILT SO FAR IS LIVE — `8036918`, 2026-08-27 20:15 Phoenix, 2158 tests, 35 slash commands, schema 16, 17 dashboard pages / 89 routes** (all six figures re-measured 2026-08-31; this line previously read `256f43d` / 07:46 / 1195 tests / 30 commands / schema 11 / 13 tabs)**:** the seven core phases (shadow/test mode), the full dashboard, `/voice` + panel + per-user memory, `/help`, bot About Me + "Cookout attendees: N" status, parity/Carl removed, Health tab lists all 7 loops, plus Phase 9 role approvals, **Phase 10 polls, Phase 11 chat 2, Phase 12 logs and Phase 13 requests**. Owner's test sweep in progress; feedback → batches. `deploys.log` has every deploy (**37** to date, counted 2026-08-31). Phases 5, 6, 7 building in git worktrees under `.claude/worktrees/` (gitignored) on their own branches, schema versions pre-assigned 6/7/8, shared files touched append-only. **Merge order: Phase 4 fixes → deploy → merge 5 → review/fix → merge 6 → review/fix → merge 7 → review/fix; re-key `code-notes.md` after each merge; deploy from `main` only.** If a session inherits this mid-flight: `git worktree list` shows the branches; never deploy with a dirty main tree. Build order
approved (Q13): see `info/feature-list.md`. Design docs: `info/phase1-design.md`
(settings, action log, role menus), `info/phase2-design.md` (go-live feed);
later phases get theirs before dispatch.

**Autonomy (owner, 2026-08-26 18:15): "keep going and only stop building the
phases if im needed for a critical choice. I can do a big test sweep when i get
back."** So: each phase = design → Opus build → Fable review → deploy in
TEST_MODE/shadow → next phase; owner does one consolidated test sweep later.
Every phase landing gets a `DONE.md` entry and a "what to click" row in
[`access/sweeps.md`](access/sweeps.md).

**F12 website placement (owner asked 2026-08-26): Phase 8, immediately after
the seven core phases.** Phase 1's settings store + audit log and the existing
FastAPI module are built as its foundation.

**Rollout rule (owner, 2026-08-26):** Black Bloc eventually replaces ALL of
Birthday Bot, Carl-bot, Modmail and YAGPDB — "rome wasn't built in a day".
Every feature that acts on members ships **shadow/log → watch → on**, flipped
per feature, so the old bot keeps running until the new one is proven.

| # | Feature | Open questions (answers land here) | Status |
|---|---|---|---|
| F1 | **Go-live → `#live-now`** | **DECIDED 2026-08-26: BOTH** — presence for discovery of anyone, Twitch EventSub (websocket) for rich posts on linked accounts; opt-out covers both. **PRIMARY = Discord presence/activity; Twitch EventSub is the FALLBACK/enrichment** (owner, 2026-08-26). **Measured incumbent (rescan):** YAGPDB posts ~8/day, 30 distinct streamers, template `REGULATORS! Mount up! **{login}** is currently streaming **{game}**! Check it out: https://www.twitch.tv/{login}` — keep the prefix; 4/199 posts render game as `****` (no category) → need a fallback; Twitch login ≠ Discord name (`thepresidentnoir`→`twitch.tv/prez`) → `/twitch link` is mandatory; YAG re-posts on restart/category change → **debounce**. Rich card = Discord's own link preview (free). Channel topic is stale ("post your links here") — fix when F1 ships. | design |
| F2 | **Twitch activity tracking** — **DECIDED 2026-08-26: YAGPDB "Streaming"-style.** Presence-based; when a member goes live post "X is live" (+title/link) to the channel; optional *Live* role while streaming; require-role / ignore-role filters; opt-out. No stats/leaderboard. Merges with F1 (one design doc). **"Scan" DECIDED + already built 2026-09-01** (owner: "as long as they opt in with the /link"): the Twitch poller polls every linked login via Helix and announces without Discord presence — that IS the scan; opt-in = `/twitch link`, opt-out honored. | built (shadow) |
| F3 | **YouTube** — *maybe* | Go-live only, or uploads too. Parked until F1 lands. | parked |
| F4 | **Event form → Discord Scheduled Event**, via review | **DECIDED 2026-08-26 (all blanks filled):** `/event create` **modal**. **Timezone:** Discord exposes no user timezone to bots (only language locale) → entered once via `/timezone set` with city autocomplete, default = server zone (America/Phoenix). **Review = a channel per submission** (like Modmail today) under an **Events** category, named `<status>-<user>-<event>` e.g. `pending-sky-block-party` → renamed `approved-…` / `denied-…` (Discord channel names are lowercase a-z0-9-_ only, so `!` and spaces are normalised). **Approvers = anyone who can see `#mute-me-bot-test-spam`** — i.e. Aunties/Uncles, Leads, Committee, etc.; implement as "roles with View on the configured staff channel/category", not a hard-coded list. **Create a real Discord Scheduled Event: toggle, default ON.** | design |
| F5 | **Ping when an event goes live** | **DECIDED 2026-08-26:** announce in **`#live-now`** (channel set in an options menu); **role ping is a setting**, default *none* (YAG pings nobody today). See F14 for the roles. | design |
| F14 | **Ping roles** (owner, 2026-08-26): an opt-in **Events** role for go-live/event pings, and **favourite-streamer roles** — per-streamer opt-in pings ("people that want to see SuperNamu only … can get her pings"). Wire into F1/F5 announcements and the role menus. | future |
| F6 | **Birthday announcements**, opt-in, with a "cutover time" | **Seed data:** Birthday Bot export (39 rows) at `archive/current-bots/birthday-bot-export-2026-08-05.md`. **Measured incumbent (rescan, 16 posts):** channel **`#return-of-the-gen`** (`1411816390414962700`), an embed `Happy Birthday **{display_name}**!` colour `#4eefff`, no ping, no role; fires at **≈00:03 local midnight in a PER-MEMBER timezone** (UTC-4 ×8, -5 ×4, -6 ×2, -7 ×1, +1 ×1) — contradicts the bot's own "server time zone" blurb. 🔴 **Phoenix gotcha: 15 of 16 landed the evening BEFORE the birthday in Phoenix terms.** **DECIDED 2026-08-26 (Q12): per-member midnight** (uses the F4 `/timezone` store); **fallback = server midnight (America/Phoenix)** when a member has no timezone set. The `🎂` role's grantor is unknown (Birthday Bot lacks manage_roles). | design |
| F7 | **Moderation** — copy the *usual* settings from other bots; exceptions list fine-tuned later (mass pings, role-based exceptions) | **Carl's live config captured** (`archive/current-bots/carl-bot-dashboard-2026-08-26.md`): only mention-spam (5/30s → delete+warn+5-min timeout) is armed; whitelists empty; warn threshold 8 with no punishment. **YAGPDB automod measured OFF.** `#carlbot-logs`: 7 warn cases in ~2 years — quiet server, do not over-tune. **DECIDED 2026-08-26 (Q11): "follow what exists"** — reproduce Carl's live config as-is (mention-spam 5/30s → delete+warn+5-min timeout; everything else log-only), warn/timeout/kick/ban commands, modlog, exempt roles = staff set; **tune in shadow mode**, change later. | design |
| F8 | **Temporary voice channels** — replicate tempvoice.xyz | **DECIDED 2026-08-26:** one creator voice channel named **"join to create a channel"** in the existing voice-channel area, positioned **directly above "You Still Here?"** (the AFK channel — keep it above, never below); spawned channels named **`{user}'s bloc`**, placed next to the creator, deleted when empty; owner control panel (rename / limit / lock / hide / kick / ban / claim / transfer) per `info/reference-bots.md`; usable by **`Member`** to start. | design |
| F9 | **Honeypot** — replicate honeypotbot.com | **DECIDED 2026-08-26:** honeypot channel(s) at the bottom with a pinned "do not post here" notice; anything posted → **ban + purge messages**, shipped **shadow-first** (log would-ban for a week, act on nothing) then enforce. **Exempt:** all bots + anyone who can see the staff channel (same rule as F4 approvers). **Log channel:** `#mute-me-bot-test-spam` for now — the owner will **rename it to `#black-block-logs`** (spelling confirmed 2026-08-26) when the bot leaves test mode; the log channel is a setting, so the rename costs nothing. The scan found no existing honeypot channel; Carl's honeypot section is unconfigured. | design |
| F10 | **Conversation when @-mentioned** ("@'d", owner clarified 2026-08-26): when someone pings the bot it holds "some semblance of a conversation" — an LLM-backed reply. | **PARKED by owner until after core features.** Needs an LLM provider + key + a cost cap; personality/tone TBD then. | parked |
| F11 | **Modmail** (added by owner 2026-08-26 — replaces the Modmail bot) | **DECIDED 2026-08-26: do what the current bot does (channel-per-ticket in the ModMail category, topic `ModMail Channel <user-id> <channel-id>`), AND wire a second mode — private threads in one staff channel — as a setting** ("wire up the option to be in 2 channel"); the toggle is ported to the F12 website later. Reference: `info/reference-bots.md` (Modmail command table). | design |
| F13 | **Verification Bot** — **rescan result: dormant** (1 message in ~2 years, its own join notice); no use cases to port. Also found dormant: `baf#0659` (a Red-DiscordBot install, ~1 yr idle) and `Black Block#1423` — **two prior attempts at this project**. Recommend kicking all three once Black Bloc is stable (owner action; on the cleanup list). `Wordle` is a Discord built-in activity webhook (422-day streak) — leave it alone. | closed → cleanup |
| F17 | **Role-process takeover + audit** (owner, 2026-08-26: "grab all the roles and settings carl already has so we dont need to recreate them, same emojis too … audit each user and their roles so we can take over that process") | **Audit captured:** `archive/current-bots/role-audit-2026-08-26.md` — 118 humans, 7 bots, 59 roles, every member's roles, per-role counts, self-assign holders; **4 humans lack `Member`** (simonebwest, FFStreamWatcher, scrybaby, UraniumAnchor), 1 has no roles (scrybaby). Carl's panels/emojis already reproduced by `/rolemenu seed-defaults`; **fix:** Marathons must use Carl's custom emoji `<:JoyGAMING:1337948924844965931>` instead of 🎮 (do at Phase 2 review). **DECIDED 2026-08-26:** `Member` is granted by **Discord's own rules screen** (owner: "i think discord rules") — Black Bloc does not take over the gate; the 4 non-Members are for the owner to handle by hand. **YAG's 3 role-command groups become Bloc menus:** *Student/Teacher* folds into the existing `mentoring` panel (Mentor/Initiate); *Runner Status* (Runner / Live Runner / Commentator) becomes a **staff-assigned** set via a new `/rolemenu` mode `staff` (staff picks the member, not self-serve); *Rule Reader* is redundant with the Discord rules screen — dropped. "We can change later." → add to the next builder's scope (Phase 3 rider). | decided — build in Phase 3 |
| F12 | **Config website for mods/admins** — **DESIGNED 2026-08-26: `info/phase8-design.md`. Owner decisions 2026-08-26 18:30 (verbatim): "we can use blackbloc.heygabi.ai for now until the org decides on a name and then we port it to that domain … this site needs to be entirely disconnected from heygabi … discord login verification only except my google sso as the owner admin of the whole domain … we'll need to link my discord verification to my google sso in the future. only people/roles who can currently see the spam channel we're testing in should be able to get on the bot, aunties/uncles mainly and the roles above it."** Static site on Cloudflare Pages wearing the estate template (`estate-theme.css`, `theme.js` 5-theme dropdown, `permission-ux.js`, fonts from `catalog-platform/sites/heygabi-home`), Discord-OAuth login gated on the same staff-role rule as slash commands, FastAPI routers inside the bot process on Fly, 12 pages mapped from Carl/YAG dashboards onto F1–F16, one settings store + audit. **8a read-only status page can ship right after Phase 2; 8b full dashboard after Phase 7.** Owner decisions deferred to then: hostname, Discord-only vs +estate SSO, who may edit moderation rules. | designed — Phase 8 |

## 📋 Session 2026-08-31 (owner back from the trip)

- **Owner 2026-08-31 ~10:13: "read all docs and global rules, lets get started with whats left on our todo list"** → B4–B8 built and **LIVE `3cae955`, deployed 11:32 (see `DONE.md` entry + `deploys.log`)**; owner sweep rows 21–24. Next in the queue: restyle R1/R2 + the KI-6/KI-9 security build (below).
- **Owner 2026-08-31 ~10:16, verbatim: "also read all docs and verify if theyer stale or need updating too"** → full docs staleness audit vs measured repo/deploy state. Status: **LANDED — 26 files reviewed + committed `d87ee84`; the same morning's bookkeeping sweep then moved the 30 landed items to `DONE.md` and consolidated owner checks into `access/sweeps.md` (rows 18–20 + phase scripts). Follow-ups queued below: code-notes re-key, KI-6/KI-9, DB backup drill.**
- **Hook finding fixed 10:15:** `scripts/docs/` (a tooling folder holding `move_done.py`, not a docs tree) tripped the session-start docs-shape check every session → renamed to `scripts/doctools/`, runbook reference updated, committed + pushed `7b7840b`.
- **DECIDED 2026-08-31 ~10:25 (owner): `docs/` stays TRACKED permanently** ("actually lets keep it tracked", after first picking purge). The 2026-08-26 local-only rule is retired; secret NAMES only still applies. `docs/` removed from `.gitignore`; the LOCAL ONLY / TEMPORARILY TRACKED headers across docs and the CLAUDE.md line get updated in the docs-audit review pass (audit agent is mid-flight in those files).

## 📋 Session 2026-09-01

- **Owner ~09:00, verbatim: "i did thee sweep of the site and its good for now, ill keep doing the sweep and playing with akk the buttons and menus. lets get started on everything in this list. (we will kick the bots in a few weeks so no worries about that). we can do the scan for no streaming activity too as long as they opt in with the /link. I did the dashboard sign in too"** →
  (a) site sweep round 1 PASSED (sweeps rows 25/26/28 + general site; owner keeps sweeping);
  (b) **F2 scan DECIDED: opt-in via `/twitch link` — and MEASURED ALREADY BUILT**: `golive.py:poll_once` polls every linked login via Helix each cycle and announces without Discord presence; opt-out honored on the shared `_go_live_once` path (`golive.py:396`). F2 fully closed;
  (c) bot kicks in a few weeks — cutover-plan §3 records the horizon;
  (d) "get started on everything in this list" → go-live hardening a/b/c + F4 requester-in-channel + F4(b)/F5 toggle verification: **Opus builder dispatched ~09:05 in a worktree**; KI-1 CLOSED (local `DATABASE_PATH` → `C:/Users/nbasl/black-bloc-data/`, old copy left inert in `data/`); **nightly DB backup built**: `black_bloc/dbsnapshot.py` + `scripts/backup_db.ps1` + Windows scheduled task "BlackBloc DB backup" daily 04:00 (StartWhenAvailable) — end-to-end test pending the next deploy shipping the module; **`info/cutover-plan.md` drafted** (the shadow→on ladder). Restyle overrides deliberately NOT flipped (owner named none).

## ⏳ Waiting on the owner

- **Cutover, at your pace** — [`info/cutover-plan.md`](info/cutover-plan.md): prerequisites P1–P5 (channel rename, staff channel, TEST_MODE lift — the lift is yours alone), then the per-feature ladder.
- **Test sweep — the whole list lives in [`access/sweeps.md`](access/sweeps.md)** (20 rows in priority order + the detailed phase 1–8a scripts, moved there whole 2026-08-31; it is the ONE home for what a person has not yet exercised).
- ~~Twitch developer app~~ **ALREADY DONE — stale line caught by the owner
  2026-08-31 ("didnt we already connect twitch dev").** Measured: `TWITCH_CLIENT_ID`
  + `TWITCH_CLIENT_SECRET` are Deployed on Fly and present in `.env`, and the boot
  log says `twitch: app token obtained` (20:13:48Z). Nothing to do.
- **Cleanup (later, owner):** kick the dormant bots `Verification Bot`, `baf`,
  `Black Block` once Black Bloc is stable.

## 🔧 Open engineering items



- **Curated docs for peers** (owner, 2026-08-26: "give them the curated docs
  they need"). Since 2026-08-31 `docs/` is tracked, so a peer who clones gets the
  FULL working tree — the root `README.md` still describes only "an optional
  FastAPI companion server", not the 17-page dashboard. Open: whether the full
  docs tree IS the peer docs now, or `README.md` gets a proper curated rewrite.
  Ask the owner when the first peer needs it.

- **Move the SQLite file out of the OneDrive-synced tree** — KI-1.

- **Restyle look-and-feel calls the owner may still override** (each cheap):
  nav grouping (Requests under Overview, Members under Moderation — one line in
  `shell.js:GROUPS`); the TODAY strip replaced the "Needs a human" card
  (one-fact-one-home); "RUNS THE COOKOUT" wraps to two rail lines in the
  Cyberpunk theme only (its own `--et-nav-head-size`; fix = shorter caption or a
  theme override). Say the word and any of these flips.

- **Owner 2026-08-27 ~11:49, verbatim: "Probably should make a deploy button api so you can deploy for me if you can't permission"** → idea logged. Today: the owner's standing authorisation works — the last four deploys ran from the session. A deploy endpoint on the bot would need a Fly API token on the machine and a self-redeploy path; higher risk than value while the session can deploy. Status: **parked unless the classifier blocks again.**


