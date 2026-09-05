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
| F1 | **Go-live feed** → `#live-now` | Decided | **Discord presence is PRIMARY**; Twitch EventSub is the fallback/enrichment for linked accounts; posts with the `REGULATORS! Mount up!` prefix; opt-out | Keep YAG's wording; `/golive` → **Link my Twitch channel** (the channel name ≠ the Discord name); debounce re-posts; fallback when game is empty; rich card = Discord link preview |
| F2 | Twitch activity tracking | Decided → merged into F1 | Same detection; optional *Live* role; require/ignore role filters; no stats | "Scan for inactive streamers" still TBD |
| F3 | YouTube — go-live **and new uploads** | Go-live via presence: shipped 2026-08-27. New-upload posts (Phase 16): ✅ **SHIPPED** merge `7295f61`, live 2026-09-02 (deploy line in `../deploys.log`); `youtube_mode` ships **off**, never yet run against a live channel. `/youtube` became ONE panel on 2026-09-03 (wave 2 — both groups and all nine subcommands retired, `commands synced` 42 → 41) | Go-live: Discord presence carries the platform, so a "Streaming on YouTube" activity announces with the member's YouTube URL; `{platform}` is a template field and the session records it. Uploads: `/youtube` → **Link my channel** stores a channel id, a 10-minute sweep reads the public Atom feed, and a new entry is posted to `youtube_channel_id` (blank = the go-live channel) with the uploader's fan role pinged. Ships `youtube_mode off` | Twitch enrichment is refused for any non-Twitch stream, so a Twitch-linked member streaming on YouTube is never overwritten. ⚠️ Go-live is **presence only** — a YouTube stream Discord does not show is invisible. Uploads need NO API key: the feed names every new video and marks a Short by its `/shorts/` address (measured 2026-09-02). `YOUTUBE_API_KEY` is optional and adds two things — @handle → channel id, and telling a live broadcast apart from an upload (**KI-11**). The feed itself answers only ~50% of the time (**KI-12**) and lags a publish by up to ~25 min (**KI-13**) |
| F4 | **Event form** → review → Scheduled Event | Decided | `/event` opens ONE panel; **Propose an event** is the modal → channel `pending-<user>-<event>` under *Events* → Approve/Reject → real Discord Scheduled Event + `<t:…>` announcement | Approvers = roles that can see the staff channel; the per-member zone is the **My time zone** button on the same panel (Discord exposes no tz — `/timezone` was retired 2026-09-03); create-event toggle ON |
| F5 | Event go-live ping | Decided | Post in `#live-now` when an approved event starts; role ping is a setting (default none) | Channel + role editable in options |
| F6 | **Birthdays** | Decided | Import 39 rows; opt-in; embed `Happy Birthday **{name}**!` in `#return-of-the-gen` | Incumbent fires at each member's OWN midnight — 15/16 land the evening before in Phoenix terms. Decided: per-member midnight, server midnight (Phoenix) as fallback |
| F7 | **Moderation** | Decided | Reproduce the incumbent's live config as-is + warn/timeout/kick/ban + modlog + exempt roles; **shadow → watch → on**, tune in shadow | Only ONE rule is armed today; quiet server; no Muted role (native timeouts). ⚠️ **The parity tool was REMOVED at the owner's request, 2026-08-27** ("Carl bot has no actions or setup, lets remove the mentions and parity to it") — `/automod parity`, `GET /api/mod/parity`, the dashboard's parity card and the `carl_modlog_channel_id` setting are all gone. **The cut-over criterion is now the owner's judgement from the shadow log**, not a measured agreement count. The rules themselves are unchanged: mention-spam armed, the rest log-only. **`/automod` is ONE command that opens a panel (wave 3, 2026-09-04)** — the `automod`, `rule` and `exempt` groups and all eight leaf subcommands are retired; the top-level count does not move (38 → 38, measured), because a group already counted as one slot. The panel changes how automod is CONFIGURED and nothing about what it enforces. |
| F8 | **Temp voice** | Decided | "join to create a channel" above the AFK channel; `{user}'s bloc`; owner panel; Member-only. **`/voice` is ONE command that opens a panel (wave 2, 2026-09-03)** — the `tempvoice` and `voice` groups and all twenty-two subcommands are retired, so the top-level count dropped by one (39 → 38, measured). The per-channel control post is unchanged. | No lobby exists today — greenfield |
| F9 | **Honeypot** | Decided | Bottom channel, pinned warning; post → ban + purge, **shadow-first**; exempt = bots + staff; log to the log channel | Vendor never documents triggers/exemptions — ours are explicit |
| F10 | @-mention conversation | **Long-term memory (Phase 17) merged `6d61994`, deployed `7b1c592` 2026-09-03** — schema 23 `chat_profiles`/`chat_memory_optout`, `/memory` (one panel — wave 2, 2026-09-03; the five subcommands are retired); **`/chat` is ONE staff panel from wave 3, 2026-09-04 — the `chat` group, both nested groups and all nine leaf subcommands are retired and `commands synced` is unchanged at 38**, Memory section on the Chat page, 9 `chat_memory_*` keys, `chat_memory_mode` ships **off**, residual KI-14; **Step 1 shipped 2026-08-27** (canned intents); **step 2a shipped 2026-08-27** — editable intents and lines in storage (`chat_intents` / `chat_lines`, schema 15), classification over a guild's own rows, six data intents (live / next event / birthdays / head count / my roles / timezone), `need_a_mod` routing, four manners settings and the eight `/api/chat` routes; **step 2b (11b) built on its own branch, not merged** — the Chat page; step 3 = a real conversation backend | `black_bloc/chat.py` sorts an @-mention into one of eight intents (greeting, thanks, how_are_you, what_can_you_do, help, love, insult, unknown) and answers in the bot's voice; `chat_mode` (default on), `chat_cooldown_seconds` (default 20), `chat_ignore_channels`, `chat_greeting_reaction`, `chat_reply_in_threads` (default on) and `chat_route_ping_staff` govern it | **Next: merge 11a and 11b together** — both touched `site/mock/contract.json` and `site/mock/server.mjs`, so those two files will conflict; take 11a's real-router shapes as the truth and reconcile the mock to them. **Step 3 = a real conversation backend**, which replaces the one seam `chat.reply_for(text, member, bot)` — now a coroutine — and nothing else. Still needs provider, key and cost cap — see `code-notes.md` § *chat — @-mention replies* |
| F11 | **Modmail** | Decided | Channel-per-ticket like today **plus** a threads-in-one-channel mode as a setting. **`/modmail` is ONE command that opens a panel (wave 4, 2026-09-05, Build A)** — the whole `modmail` group (logs, block, unblock, blocked, mode, forget, status, settings) and the whole `snippet` group are retired, so the top-level count drops by one (36 → 35, measured). ⚠️ `/reply` `/areply` `/note` `/close` are untouched by Build A; the ticket card that retires three of them is Build B. `modmail_panel_minutes` (10) decides how long the panel stays live | Must keep the `=` private-staff-note workflow (or an equivalent) |
| F12 | **Config website** | Designed (`phase8-design.md`) | Cloudflare Pages site in the estate template + Discord-OAuth staff login + FastAPI routers in the bot; 12 pages mapped from Carl/YAG dashboards | 8a status page after Phase 2; 8b full dashboard after Phase 7 |
| F13 | Verification Bot use cases | Closed | dormant, nothing to port | — |
| F14 | **Ping roles** | **SHIPPED `d777f57` 2026-09-02 17:43** (merge `c577b06`); `pings_mode` flipped **on** from the dashboard the same evening; ⚠️ never run against live Discord roles yet — the owner's sweep | One opt-in **Events** role, made or reused by `/pingroles setup`, which points BOTH `golive_ping_role_id` and `events_ping_role_id` at it and puts it on a **Notifications** role menu; plus a **role per streamer** (`golive_fan_roles`, schema 21) that only their followers wear. **`/pings` is ONE command that opens a panel** (wave 2, 2026-09-03): the member half is **Follow a streamer… / Stop following…**, the Events toggle(s) and **Start my own ping role** / **Take my ping role away**; the staff half adds **Streamers… · Set up the Events role · Settings · Logs · Open on the site**. `/pingroles` and the twelve leaf subcommands are gone, `/api/pings/*` + a Pings section on the Go-live page, and auto-maintained **Streamer pings** panels (25 a select, `streamers`, `streamers-2`, …). A go-live announcement reads `<@&events> <@&fan> REGULATORS! …`, deduplicated, and the fan role is read AFTER the cooldown gate so a suppressed announcement never pings | Seven decisions are settings keys, not constants: `pings_mode` (ships **off**), `pings_log_level`, `pings_events_role_name`, `pings_fan_role_creation` (self/staff/auto), `pings_fan_role_template`, `pings_fan_role_on_unlink` (keep/delete), `pings_fan_role_delete`, plus `pings_panel_minutes` (the panel, wave 2) — [`phase15-design.md`](phase15-design.md), [`pings-panel-design.md`](pings-panel-design.md). ⚠️ **Nothing here has met a real Discord role**: role creation, panel refresh and the Manage Roles ordering are all test-suite evidence only |
| F15 | Polls | **shipped 10a+10b, 2026-08-27** | YAG reaction polls are used in `#announcements` | Native Discord polls plus a Black Bloc panel for what native cannot do. **`/poll` is ONE command that opens an interactive panel** (2026-09-03, wave 1 of [`panels-program.md`](panels-program.md) — [`polls-panel-design.md`](polls-panel-design.md)); the eleven subcommands it replaced were `create|end|cancel|results|list|settings|logs` and `recur create|list|pause|delete`; kinds single / checkbox / yes-no / rating / **date**; the panel carries anonymous votes, results-at-close and up to 25 options; review switch, last-call + close + archive loop, results embed, CSV export, and the **Polls** dashboard tab with a create form — [`phase10-design.md`](phase10-design.md), [`polls-research.md`](polls-research.md), [`code-notes.md`](code-notes.md) § *polls (10b)*. ⚠️ **Not merged, not deployed, and nobody has voted on either surface yet** — one probe poll was posted to measure `<t:…>` in an answer label and left in the test channel. v2 kinds (free text, number, ranked) are still refused by name |
| F16 | **Role menus** | Needed (found) | Replace Carl's 5 panels: pronouns, play-style, mentor/initiate, interests, event alerts — measured emoji→role maps. **`/rolemenu` is ONE staff command that opens a panel** (wave 3, 2026-09-04): the root lists the menus with **A menu… / New menu / Seed the defaults / Grants… / Waiting on staff (N)… / the mode button / Logs**, a menu's card carries every move that is currently possible, and **Grants… opens as an audit of every timed role running**, soonest to end first, with **Push it back…** and **End it now** on a grant's card. BOTH the `rolemenu` and `role` groups and all eighteen leaf subcommands are gone, so the top-level count drops 38 → 37 | Buttons/selects instead of reactions; migrate without stripping anyone's roles. `rolemenu_panel_minutes` (10) is the panel's own key. ⚠️ **`rolemenu_mode` off DOES hide `/rolemenu` again as of 2026-09-04** — the 2026-09-03 carve-out is reversed, because `/settings` can never be hidden and `/settings set-value rolemenu_mode on` is the way back (see the cross-cutting note below) — [`role-menus-panel-design.md`](role-menus-panel-design.md) |

## Cross-cutting (every feature)

- **Test policy** — everything runs inside `#mute-me-bot-test-spam` + DMs
  until the owner lifts `TEST_MODE`; side effects check `bot.guard`.
- **Rollout** — anything that acts on members ships shadow/log → watch → on,
  flipped per feature; the incumbent stays on until parity is measured.
- **Settings** — every knob named above is a stored setting with a slash
  command now and an F12 page later; no hard-coded channel/role IDs in code.
- **A feature turned off takes its `/command` with it** (owner, 2026-09-04) —
  set `<feature>_mode` to `off` on the dashboard or with
  `/settings set-value`, and within about a minute that feature's one
  top-level command disappears from Discord. Fourteen features do this:
  `/golive`, `/youtube`, `/pings`, `/voice`, `/honeypot`, `/event`, `/poll`,
  `/birthday`, `/automod`, `/rolemenu`, `/request`, `/chat`, `/raidtrain`,
  `/apply`. `/memory` is the one exception (fork I-M1, "open it"): memory off
  deletes nothing, so the panel stays as a member's door to their own notes. ⚠️ **`shadow` is not `off`** and hides nothing.
  The ways back: `<feature>_mode` → `on` (the dashboard, or
  `/settings set-value <feature>_mode on` — `/settings` can never be hidden),
  or `hide_commands_when_off` → `false`, which returns every command while the
  features stay off. `/help` says how many are missing and how to get them
  back; `modmail_mode` is `channel`/`thread` and has no off, so `/modmail`
  never hides. `command_visibility.py`, sweeps rows 183–187.
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
| F20 | **Applications** | ✅ **SHIPPED** — Phase 19 merged `7b1c592`, deployed `7b1c592` 2026-09-03; `applications_mode` ships **off** | A staff-defined form that, when approved, grants a role — the Twitch Team form is the first one the owner makes | Member request #2 (Pawpette, staff): *"Twitch Team application form to be done via bot and approved by staff"*. Schema 25 (`application_forms`, `application_questions`, `applications`); **`/apply` is ONE command that opens a panel** (2026-09-03 — both groups and their seventeen subcommands retired, `commands synced` 43 → 42; [`applications-panel-design.md`](applications-panel-design.md)); ≤5 questions (Discord's modal cap); one open application per member per form; approve grants the form's role through the same ledger the reconciler reads, with an optional expiry; the card names the human step after the approval, because the twitch.tv Team invite has no API. [`phase19-design.md`](phase19-design.md). Ships `applications_mode` **off**; never run against live Discord

## Still open

- **Q13** build-order approval · Twitch developer app credentials (owner, in progress; fallback path only).
| F19 | **Raid trains** | ✅ **SHIPPED** — Phase 18 merged `0bb3835`, deployed `7b1c592` 2026-09-03; `raidtrain_mode` ships **off** | Member request #1 (Pawpette, staff): r3dlabs.com does it, but that site needs every streamer to connect Twitch — the ask is sign-ups, slot availability, and a DM 30 minutes before your slot | A dated train split into consecutive slots, one streamer an hour, each raiding the next. Schema **24** (`raid_trains`, `raid_slots`); **`/raidtrain` is ONE member-visible command that opens a panel** (wave 3, 2026-09-04 — both groups and all fifteen subcommands retired, top-level 38 → 37): the trains coming up, **A train…** → the lineup card, **Take an hour…** / **Give back slot #N** / **My slots…** for everybody, **Start a raid train** / **Put somebody in…** / **Take somebody off…** / **Change two slots round…** / one Lock-or-Open button / **Call it off…** for organizers, and **Mode…** / **Setup…** / **Logs** / the site link for staff; one lineup post **edited in place** with a thread under it; a 5-minute sweep that auto-locks and starts a train, DMs each holder `raidtrain_reminder_minutes` before their slot (once — the stamp goes on the row BEFORE the DM), checks a holder in off the go-live signal and says "the train moves" in the thread; a **Raid trains** section on the Events page. Identity is a linked Twitch channel (`/golive` → **Link my Twitch channel**), so no member ever grants Twitch OAuth — the whole point of the request. 14 keys, no constants: `raidtrain_mode`, `_log_level`, `_organizer_role_id`, `_channel_id`, `_ping_role_id`, `_slot_minutes`, `_reminder_minutes`, `_poll_minutes`, `_require_link`, `_thread`, `_live_posts`, `_max_slots_per_member`, `_scheduled_event`, `_panel_minutes` — [`phase18-design.md`](phase18-design.md), [`raid-train-capture.md`](raid-train-capture.md). ⚠️ Never run against live Discord; residuals **KI-15** and **KI-16** |
| F18 | **Requests** | **13a shipped** 2026-08-27; **13b** (page) shipped `8036918`; **state machine** (Phase 17 ride-along) merged `6d61994`; **third pass** (embeds, the `review` state) deployed `70a6720` 2026-09-03; **fourth pass** (`/request` is ONE command that opens an interactive panel — the nine subcommands are gone) merged `ba5cb99` and deployed 2026-09-03 (`deploys.log`); **the panel's list is staff-only** (owner, 2026-09-03, `request_panel_own_list` default off) BUILT, not yet merged — [`requests-panel-design.md`](requests-panel-design.md) | The "initial doc" of ideas on paper; the owner's ask to "minimize slash commands and maximize interactive windows" | The `requests` tables and the `/api/requests` routes; the dashboard page. `/request` opens an ephemeral embed + `discord.ui.View`: File a request, Refresh, a site link, and — when withdrawable — a Take-one-back select; staff additionally get a counts line, their own list, a Pick-a-request select (capped at 25) and a Logs button. ⚠️ **Viewing requests on the panel is staff-only** (owner, 2026-09-03): a member sees no list of their own requests unless `request_panel_own_list` is turned on, and they can still file and take one back. Picking a request renders its card with only the moves valid from its status (one data table, `CARD_BUTTONS`); every move calls the same shared function the site calls. Not run against live Discord |
