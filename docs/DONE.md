# Black Bloc — DONE (dated archive, newest first, append only)

> **Audience:** Claude sessions and the owner. **Status:** TRACKED (owner,
> 2026-08-31 — was local-only until then; secret NAMES only).
> Last verified: **2026-09-19** — the HEADER only, by the docs staleness pass after the
> TEST_MODE lift. Measured while here: the file was **4,423 lines** before this pass's own entry
> was added (it said 3,964). ⚠️ **The line count of this file cannot be stated inside this file
> without being wrong the moment it is written** — 4,423 is the figure as the pass found it, and
> `wc -l docs/DONE.md` is the only current answer. The newest
> entry is **2026-09-19 (the docs pass below)** and the one under it is **2026-09-18 (v141,
> merge `d6c271d`)**, which matches the last line of [`deploys.log`](deploys.log) — the header
> said the newest was 2026-09-11 / v108, ten releases ago. Both links in this header resolve.
> The entries below are an append-only archive and were deliberately NOT re-verified or edited;
> a wrong one gets a superseding entry, never a correction in place. ⚠️ **NOT checked:** any
> individual entry's facts, and nothing in this pass met live Discord or a browser.
> Before that, **2026-09-11 08:32** — the HEADER only, on the same terms.
> Before that, **2026-08-31** — the HEADER only, on the same terms.
>
> Entries are moved here WHOLE from [`TODO.md`](TODO.md), never summarised, and
> never edited afterwards. A wrong entry gets a superseding one above it.

## 2026-09-20 — v149 (19:28): the owner's go-live review, posts version history, the previews hub, the boot-reconcile fix and the local lower environment

**v149 (release `ccce091`, 6967 tests + 3 skipped, schema 48 → **49**, keys 290 → **293**, routes 190 → **192**).** Four builds and a review session in one deploy, all rendered on the local mock before it (the owner's asks 18:4x–19:2x, each verbatim on the moved items below):

- **Go-live page** (conductor, page-golive.js + site.css): a **Kept forever** chip and the strip's Spotlight cell counting kept vs expiring; every badge in the Streamers grid in the posts page's `cell-kind` wrapper plus one reusable rule (`.grid-row > .badge { justify-self: start }`) so a bare badge never stretches to its cell; `golive_end_author` edits in a three-row textarea; the two wording previews drawn by `discordmd.renderPreview` as an embed card, re-rendered on every keystroke; **Add a ping role…** in the row drawer (an `ask()` modal → `POST /api/pings/streamers`, the `/pings` door in place); **Spotlight this channel…** in a member's drawer (the same form as the toolbar's, their login filled in); **Expires** and **Opted out** as columns of their own; seven fractional columns; Add a streamer + Spotlight a channel in the Streamers toolbar; **Link them** on Recent streams for a presence-only streamer (one confirm → the same link route by the URL's shape).
- **Posts version history** (Opus, 416k, `posts-versions-design.md`, fifteen deviations): `post_versions` (append-only, backfilled one row per existing post at this boot), `record_version` with its four write rules, `restore_version`; `reset_post` / Put the original back / `/reset` gone on both doors; the Versions foldout (View → drawer, Use this version → confirm → restore) as ONE module both the page and its preview draw; Post it saves a dirty editor first; the Discord Versions… sub-panel; keys `posts_versions_keep` (0 = all) and `posts_versions_summary_chars`; kinds `post.restored` / `post.versions_trimmed`; the `shipped` chip is EARNED (compared to `posts_seed.json`). Sweeps **644–651**.
- **The boot fix** (Opus, 251k + 272k, `golive-boot-sweep-design.md`, sixteen deviations): 🔴 `bot.py:setup_hook` loads every cog before IDENTIFY, so `self.bot.guilds` is empty at `cog_load` and **the v141 boot reconcile had iterated nothing on the real bot since it shipped** — a session left open by a restart was closed only by `age_out_sessions` twelve hours later; now the boot pass runs from `on_ready` and the `cog_load` pass does not stamp the `Reconciler` when it saw no guilds; the same fix in `spotlight.py` (guard falsified, then kept); `sweep_presences()` walks every member's Discord presence at boot through the same `_go_live` door; one `golive.boot_swept` row per guild per boot with counts; key `golive_boot_sweep` (true). Sweeps **652–656**.
- **The previews hub** `/previews` with **What is coming** / **Live today** doors on every card (a Go-live card too), the posts preview's columns (Post · Status · Channel · Last saved, left-aligned).
- **The local lower environment:** `site/mock/server.mjs` takes `LIVE_ROOT` (a detached worktree at the deployed release, `C:/lcw/bb-live`): normal URLs serve the deployed site, `/preview/<page>` the working tree's page on its own assets (`/preview/assets/` rewrite). Measured byte-identical to the live site's script for v148. The deploy ritual moves the worktree to each release.

⚠️ What met Discord at this deploy: only the boot itself (the boot log). Nothing else has met a real client — the sweeps are the proof. Verified: boot log: 'database: gave 1 post(s) a first saved version' (the backfill, on the live database), every cog loaded, logged in, no Traceback; /health ready=true latency 65 ms; the FIRST real golive.boot_swept row, read on the Logs page 19:3x — sessions_kept=2, sessions_closed=0, sessions_dropped=0, swept=True, members_walked=123, members_cached=True, presence_found=2, presence_announced=0, presence_skipped={'open_session': 2} — so the boot pass now sees the guild (123 members walked), kept both live sessions and announced nobody twice.

**The four TODO items, moved whole:**

- 📡 **GO-LIVE BOOT RECONCILE — on start-up, check every linked streamer's real status and make the latest go-live post about them true** (owner, 2026-09-20 17:5x, verbatim: *"also for go live detection, have the bot check all the channels with status and taht are linked on start up and make sure the most recent post regarding them in the golive channel is accurate so we dont miss people during reboots"*). Today's boot reconcile (`golive.py:reconcile_open_sessions` under `loops.Reconciler`, v141) walks the OPEN sessions only — it re-checks each side is still live and closes / promotes (so (c) below already exists) — but it never asks who is live with NO session, which is exactly the person who went live while the bot was down. **Design written 18:0x: `info/golive-boot-sweep-design.md`** — measured that the Twitch poller's first tick and the YouTube sweep ALREADY announce anyone live with no session at boot, and the reconcile already closes (past tense) anyone who ended during the downtime; the real miss is PRESENCE-ONLY streamers (no link), because Discord replays no presences at boot — so the build is a `sweep_presences()` boot pass through the same `_go_live` door, a `golive.boot_swept` log row with counts, key `golive_boot_sweep`, and a test PROVING each of the five already-right rows. **Dispatched to Opus 18:3x as branch `boot-sweep`; landed 19:0x (`4b967f3`, 251k, fifteen deviations, 6936 tests both orders, KI-26's fifteenth sighting).** 🔴 **THE FINDING (deviation 0): §A row 3/4/5 were FALSE on the real bot** — `bot.py:setup_hook` loads every cog before IDENTIFY, so `self.bot.guilds` is EMPTY at `cog_load`, and the v141 boot reconcile has iterated nothing since it shipped; a session left open by a restart was closed only by `age_out_sessions` twelve hours later or the member's next presence change. Fixed: the boot pass runs from `on_ready`, and the `cog_load` pass no longer stamps the `Reconciler` when it saw no guilds (else the 60-second skip threw the real pass away). ⚠️ `cogs/content/spotlight.py` has the identical shape (v148) — the same fix landed on the same branch 19:2x (`70fd6e3`, guard falsified then kept; 6937 tests). **Merged into `main` `76b0a6a` 19:3x, NOT deployed** — ships as v149 with the rest on the owner's go. ⚠️ Not audited: `frontdoor.py`, `modmail.py`, `events.py` hold the same `cog_load` + `on_ready` Reconciler pair (they POST rather than sweep, and their 2026-09-18 incident was a DOUBLE post, so their `cog_load` pass evidently saw guilds — different timing, same shape; worth one look). Superseded sketch: one boot pass per guild that (a) asks Helix `get_streams` for every linked Twitch login in one batched call and the YouTube probe for every linked channel, (b) for each person live with NO open session → announce as a normal go-live (with the cooldown honoured so a bounce does not re-ping), (c) for each open session whose person is NOT live → the end path (past-tense edit / delete per `golive_end_mode`), (d) for each open session still live → touch nothing; logs one `golive.boot_reconciled` row with the counts; `golive_boot_reconcile` mode key (off / shadow / on) so it is configurable both ways; a test per branch. Status: logged, design queued behind spotlight.
  ↳ **LIVE as v149 19:28** (release `ccce091`).

- 🎛️ **THE OWNER'S GO-LIVE REVIEW — four asks** (2026-09-20 18:4x, on the local mock, verbatim: *"we need to have a way to see whos in the forever section. the deleted by hand yellow box for rivet is oversized, fix that box size. for the what the car'd top line says box make that a text box the same size as the annoucement. also can we do live renders for the previews? live show what it would look like in discord as a preview. a dynmaic mock?"*). (1) a **Kept forever** filter chip on the Streamers list (spotlight rows with no expiry) and the strip's Spotlight cell counting kept vs expiring; (2) the Ping-role cell's *deleted by hand* badge stretches to the cell — size it to its text; (3) *What the card's top line says* becomes a textarea the same size as the announcement's; (4) a LIVE DISCORD-LOOK PREVIEW of the announcement as the wording is typed — the page already reads `/api/golive/preview` (the bot's own render) — make it re-render on input (debounced) and draw it with the `discordmd.js` message renderer the posts editor uses, so it looks like Discord; the same construct then serves every preview page ("a dynamic mock"). Status: all four DONE on the local mock 18:5x (conductor, `page-golive.js` + two `site.css` rules): (1) a **Kept forever** chip and the strip's Spotlight cell now reads *N channel(s) with no member · K kept for ever · E expiring*; (2) the badge is wrapped so the grid cell no longer stretches it; (3) `golive_end_author` edits in a three-row textarea like the template; (4) the two wording previews are drawn by `discordmd.renderPreview` as an embed card (the top line from the bot's own `/api/golive/preview` answer, the body re-rendered on every keystroke, roles by name) — a Discord-look live render. Known cosmetic: the sample body says *Casey* while the bot's head says the signed-in name. Awaiting the owner's look before it deploys.
  ↳ **LIVE as v149 19:28** (release `ccce091`).

- 🔔 **GO-LIVE ROW DRAWER — an Add-a-ping button that sets the ping role up in place** (owner, 2026-09-20 18:5x, verbatim: *"when we click a streamer channel we need a button to add ping, and this should open a modal or something connected to /pings so that can be set up here without having to page away."*). The row drawer's Ping-role group gains **Add a ping role** when the member has none, opening a dialog on the same page that calls the pings routes the `/pings` panel uses (role name, colour if the route takes one, who it pings), then the row and drawer re-render. Built on the mock 19:0x: **Add a ping role…** in the drawer's Ping-role group (members only, never a channel-only row) opens an `ask()` modal — pick an existing role or leave it to make one, the name it will get is shown from `pings_fan_role_template` — then `POST /api/pings/streamers`, the same door /pings uses; the row re-renders. **19:0x, next ask, verbatim: *"we need a new column for expiration, I want the kept forever and opted out to be their own column."*** → the Streamers table gains **Expires** (spotlight rows: *kept for ever* / *until 30 Sep*) and **Opted out** as columns of their own, out of Announced — done on the mock 19:1x (eight cells, the Streamers grid has its own column template; Announced now says only *live now* / *ready*). 19:0x, verbatim: *"for go live lets not crowd the right side, space them out evenly within reason"* → the seven columns share the row in fractions (Member a little wider), nothing fixed-width but the chevron. 19:1x, verbatim: *"on go live page the add streamer button should be in the streamers section, or its too far away"* → **Add a streamer** and **Spotlight a channel** move from the page head into the Streamers section's toolbar beside the search box (as New post did on posts). 19:1x: *"deleted by hand box is too long by a lot and this seems to be true of live now and opt out too. use the same box size and template as the post page. maybe make that box a style and apply it as reusable."* → every badge cell in the Streamers grid is the posts page's `cell-kind` wrapper, and one reusable rule (`.grid-row > .badge { justify-self: start }`) stops a bare badge stretching to its grid cell anywhere. 19:2x: *"i see there is a spotlight button, very good keep that, also add a spot light button when i click a streamer and the panel pops up"* → the row drawer gains **Spotlight this channel…** for a member with a Twitch link and no spotlight row yet — the same form as Spotlight a channel with the login already filled (bump every N hours, pin, keep / days). Awaiting the owner's look before it deploys. 19:2x, verbatim: *"lets also add a way to add a link button to the go live history so we can easily link discord users to their streams as a quick opt in."* → each Recent-streams row whose member has no Twitch/YouTube link gets a **Link them** button — the row already knows who and where, so it confirms in one dialog and calls the same link route as Add a streamer (Twitch or YouTube by the URL's shape); linked members and spotlight rows show a dash. Built on the mock 19:3x (the mock gained a presence-only seed stream by Moth so the button has a row).
  ↳ **LIVE as v149 19:28** (release `ccce091`).

- 🪞 **THE LOCAL MOCK BECOMES A REAL LOWER ENVIRONMENT — normal URLs show what is LIVE, `/preview/<page>` shows what is coming** (owner, 2026-09-20 19:0x, verbatim: *"why is only posts under the preview page, go live and any of page should also be under the /preview url. and the pages that are live now should be under the normal url."*). Build: `site/mock/server.mjs` takes `LIVE_ROOT` (a git worktree checked out at the deployed release, `C:/lcw/bb-live`); every path NOT under `/preview` (pages, assets) is served from `LIVE_ROOT/site/public`; `/preview/<page>.html` serves the working tree's `preview/<page>.html` if one exists, else the working tree's real `<page>.html`; `/preview/assets/*` serves the working tree's assets and a page served under `/preview/` has its `/assets/` links rewritten to `/preview/assets/` so it runs the coming code; `/previews/` (the hub) is working-tree too, and its cards read **Open the preview** → `/preview/<page>.html` for EVERY page and **Today's page** → `/<page>.html`. The deploy ritual moves `C:/lcw/bb-live` to each new release. **Built 19:2x** — `LIVE_ROOT=C:/lcw/bb-live` (a detached worktree at the deployed release; the deploy ritual moves it), measured: `/golive.html` serves v148's page and assets, `/preview/golive.html` the working tree's with its asset links rewritten to `/preview/assets/`, `/previews/` the hub with **What is coming** / **Live today** doors on every card. Start it with `MOCK_PORT=8797 LIVE_ROOT=C:/lcw/bb-live node site/mock/server.mjs`.
  ↳ **LIVE as v149 19:28** (release `ccce091`).

## 2026-09-20 — Spotlight: Twitch channels with nobody here behind them (v148, 18:23) — plus the posts preview's columns

**v148 (release `f73d3a7`, merge `e7f54c9`, 486k Opus, `spotlight-design.md` + eighteen deviations):** owner: *"we have a twitch channel gamesdonequick, it 1 needs to be tracked even though its not in the discord … bumped in the go live channel every x (default 4) hours … add and remove people from this list and with an expiration date … pin channels so … GamesDoneQuick can be always in the list while the rest get purged … staff managed and approved … also pin those streams in the go live channel for the duration"*. Shipped: `spotlight_channels` / `spotlight_sessions` / `spotlight_bumps` (schema 47 → **48**, bootstrap tables, no `ADDED_COLUMNS`); `black_bloc/spotlight.py` (pure) + `cogs/content/spotlight.py` (cog **23**: a five-minute Helix poll over every row's login in one batched call, borrowing the go-live cog's client; announce through the SAME `render` / `announcement_embed` with a `name=` so the card names the channel, not *Someone*; pinned when the row says so; a bump every `bump_hours` measured from `last_bump_at or started_at`; the end unpins, edits past tense per `golive_end_mode`, deletes the bumps when `spotlight_bump_cleanup`; expiry ends an open session first, then deletes the row; a kept row never expires; boot reconcile under `loops.Reconciler`); nine keys `spotlight_*` (281 → **290**, all in the golive group, which passes the 25-cap and gains the Find box); fourteen `golive.spotlight_*` kinds (+ `golive.would_spotlight_announce` in shadow); routes `GET/POST/PATCH/DELETE /api/golive/spotlight[/{id}]`, `POST …/{id}/bump`, `POST /api/events/{id}/spotlight` (186 → **190** in the contract; the last two outside it by choice); the Go-live page: a channel-only ROW in Streamers with a *channel only* badge and *spotlight · kept / until …*, a Spotlight chip, a Spotlight group in the row drawer, **Spotlight a channel** beside Add a streamer, a fourth mode cell in the strip; `/golive` ▸ **Spotlight…** (staff) with buttons that render only when valid; **Spotlight this stream** as the sixth action on an approved event's card whose Where is a twitch.tv link, and a cancelled event expires its row. `golive-join.js` takes a sixth payload; its every-key-lands-once fixture was two behind (36 → 48, measured by import). Tests 6818 → **6920** both orders; sweeps **637–643**. ⚠️ Nothing met Discord or Helix: no spotlight announced, pinned, bumped or expired outside the suite; the migration met the live database only at this deploy; no browser rendered the page before the merge — the conductor rendered it on the mock after. Verified: boot log: the spotlight cog loaded, logged in, no Traceback; /health ready=true; the Go-live page rendered on the local mock after the merge (a Spotlight strip cell in shadow, a GamesDoneQuick Live-now card with spotlight badges, three channel-only Streamers rows, the Spotlight chip and the Spotlight a channel button; zero console errors); the first gate run's one red test was KI-32, green alone and on the re-run.

**Rode along:** the posts preview's columns are Post · Channel · **Status** (centred) · Last saved and **New post** sits in The posts toolbar (owner's walk, finding 4), rendered on the local mock before the deploy.

**The TODO item, moved whole:**

- ✨ **SPOTLIGHT — track Twitch channels that are not Discord members (GamesDoneQuick), bump the go-live channel every N hours while they stream, pin for the duration, staff-curated with expiry and keep-forever** (owner, 2026-09-20 16:5x, verbatim: *"we have a twitch channel gamesdonequick, it 1 needs to be tracked even though its not in the discord. It's an org channel not a person so it cant be in the discord. Also a few times a year they run 24 hours marathons. and other times they run marathons that last most of the day. I want them to get bumped in the go live channel every x (default 4) hours to remind people that the important marathon is still going on. I also want a way to add and remove people from this list and with an expiration date. That way we can highligh other marathons too. I also want a way to pin channels so while others will expire and have to be reinputted, certain reoccuring channels like GamesDoneQuick can be always in the list while the rest get purged after a set amount of time. i think this should be a website only feature but if you think we could do this organically in discord without it being confusing to manage we can have it there too. This list needs to be staff managed and approved. I imagine end users will submit an event and then the staff of the discord will set this up for the duration of their event. lets also pin those streams in the go live channel for the duration of their event when this option is triggered."*). Designed 17:0x as [`info/spotlight-design.md`](info/spotlight-design.md): a *kept* row vs an *expiring* row, a *pinned* message (the ask uses "pin" for both); `spotlight_channels` + `spotlight_sessions` (schema **47** — `costream` takes 46), a Helix `get_streams` poll every 5 min (no presence for a non-member), the announcement through go-live's own render + pinned, a bump message every `spotlight_bump_hours` (4) from `spotlight_bump_template`, the end unpins + edits past tense + deletes the bumps, expiry on the same tick, nine `spotlight_*` keys under golive, cog 23; doors: channel-only ROWS in the v142 Streamers list (one subject, one place) + a Spotlight group in the row drawer + *a channel with no member* on Add a streamer, and a small `/golive` ▸ Spotlight… sub-panel; the member path is an approved event with a twitch link → staff press **Spotlight this stream** (expires at the event's end + 2 h; a cancelled event expires it). Dispatched to Opus 17:23 as branch `spotlight` (`C:/lcw/bb-spotlight`, cut from `origin/main` after the costream fast-forward). Landed 18:2x (`10d2be1`, 486k Opus, eighteen deviations — schema **48** not 47 because `selftest-boot` took 47 while it built; the shadow kind is `golive.would_spotlight_announce`; the bump wording says *so far* because `tidy()` eats a dangling *in*), merged `e7f54c9`, **LIVE as v148 18:23** (release `f73d3a7`). `spotlight_mode` ships **shadow**. Sweeps **637–643**. Two named follow-ups: the events PAGE row has no Spotlight button yet (the route and the card do), and the bump + event-spotlight routes sit outside `contract.json` by choice.

## 2026-09-20 — The boot self-test follows test mode, and `/test` for staff (v146, 18:06)

**v146 (release `6652b25`, merge `0f006ea`, 222k Opus, `selftest-design.md` §K + seven deviations):** owner: *"i think now that we're no longer in test mode, we don't need to have black bloc post every panel in logs. Let's leave that as a default when in test mode and then a /test command that spews out all the panels for staff only. PRIORITY TASK"*. Measured cause: `selftest_on_boot` defaulted `true` whatever `TEST_MODE` said, so every boot since the 2026-09-18 lift posted the self-test's 18 cards into `#blackbloc-logs` and purged them a minute later. Shipped: the key's DEFAULT is now `settings.test_mode` (`SELFTEST_ON_BOOT_DEFAULT` deleted — a rehearsal that must remember to switch the self-test back on proves nothing; the key stays a bool in core, one Settings change either way); **`/test`** in `cogs/core.py` — staff-locked (`default_permissions`, then the same guild → `require_staff` → `db_up` order as `/settings`), optional `where` (a channel for this run) and `keep` (minutes, validated by the registry's own bounds and refusal sentence, not `app_commands.Range`), the SAME `selftest.run` as the other three doors; deviation 1 is the one that matters: **`keep` lives on the run ROW** (`selftest_runs.keep_minutes`, schema 46 → **47**) because the purge is a 60-second loop with no `Run` in hand — in memory the option would have looked like it worked and then not; `NO_CHANNEL` answered before the run starts; the `/settings` button and the boot line read the same `minutes_of`. Verified, not assumed: the purge finds an overridden run's cards by the ids it wrote down (a test posts into the other channel and asserts the bulk delete lands there and nowhere else); one incidental fix — `waiting_messages`'s `ORDER BY id` became `ORDER BY m.id` after the join. Tests 6800 → **6818** both orders; commands 32 → **33**; sweeps **633–636**. ⚠️ Nothing met Discord: no `/test` typed, no card posted, no live purge; the migration ran on the live database only at this deploy (boot log). Verified: boot log: logged in, NO selftest: line (the boot no longer runs it), no Traceback; /health ready=true latency 65 ms; the live Settings API reads selftest_on_boot value false / default false with the new help sentence, so no stored row overrides the default.

**The TODO item, moved whole:**

- 🧪 **PRIORITY — THE BOOT SELF-TEST STOPS SPAMMING THE LOGS CHANNEL NOW THAT TEST MODE IS OFF; `/test` FOR STAFF** (owner, 2026-09-20 17:3x, verbatim: *"i think now that we're no longer in test mode, we don't need to have black bloc post every panel in logs. Let's leave that as a default when in test mode and then a /test command that spews out all the panels for staff only. PRIORITY TASK"*). What he is seeing: `selftest_on_boot` defaults **true** whatever `TEST_MODE` says, so every boot posts the self-test's 18 panel cards into `#blackbloc-logs` (`selftest_channel_id` unset → the test channel) and purges them a minute later. Design: `docs/info/selftest-design.md` **§K** — the key's DEFAULT follows test mode (`default()` branch: true under `TEST_MODE`, false otherwise; the key stays, so either way is one Settings change); a new staff-only `/test` slash command (the owner asked for it by name, so the minimise-slash rule yields) runs the SAME `selftest.run` with two optional arguments, `where` (a channel; default = the self-test channel) and `keep` (minutes before the purge; default = `selftest_purge_minutes`), answers ephemerally with the counts, and the `/settings` ▸ Run the self-test button stays. Dispatched to Opus as branch `selftest-boot` (`C:/lcw/bb-selftest-boot`). Landed 18:0x (`c0fca1a`, 222k Opus, seven deviations — the keep lives on the row: schema **47**), merged `0f006ea`, **LIVE as v146 18:06** (release `6652b25`). No stored `selftest_on_boot` row existed (the Settings API read value false / default false after the deploy), so nothing needed clearing. Sweeps **633–636**.

## 2026-09-20 — Co-streaming: one announcement for both platforms (v143, 17:24) — plus the Streamers-open fix and the request filed wording

**v143 (release `84e33fa`, merge `a195df5`, 346k Opus, `costream-design.md`, eighteen deviations):** owner: *"when someone is co streaming I would like the message to say this person is streaming on twitch and youtube, have the twitch stream first and only link preview the twitch stream. if someone is streaming on one and adds the other i want to edit the previous message to reflect both are live. It would be silly to suppress one of the live avenues someone is on"*. Shipped: `golive_sessions` gains `also_source` / `also_url` / `also_platform` / `also_started_at` (schema 45 → **46**, `ADDED_COLUMNS`, applied at boot); `add_platform` edits the announced message into the co-stream wording (`golive_costream_template` / `golive_costream_author`, both keys, one validator; Twitch always first whichever came first; `{also_url}` wrapped by the FILL so no template edit can un-suppress it; `{url}` filled bare as today — measured) with no cooldown check, no send and no new ping (`again_render` keeps whatever mention the message already carries); `drop_platform` when one side ends — the `also` side clears, the primary ending PROMOTES the other (game and title kept: one person, one thing, two places), the session stays open; the end fires only when neither side is live (`open_session_on` finds a session by either side; the reconcile checks each side); the YouTube hand-off joins instead of holding back (`youtube.live_seen` `because: joined_session`); `golive_costream_mode` ON by default, OFF = v135 exactly (three v135 tests now set it off by name); two kinds `golive.costream_added` (important) / `golive.costream_dropped`; the sessions route + contract + mock (the mock's row 12 is a co-stream). Keys 277 → 280 (+ `request_filed_line` = **281**); tests 6757 → **6800** both orders; sweeps **627–632**. ⚠️ Nothing met Discord: whether Discord suppresses `<…>` and whether an edit re-pings are library knowledge; five of six sweeps need a person live on both platforms at once. KI-26 fired twice on this build, both on `> file` runs (sightings twelve and thirteen). Verified: boot log shows the three also_* columns added, golive cog loaded, logged in, no Traceback; /health ready=true latency 62 ms (17:25).

**Rode along:** the Go-live page's Streamers list now opens on arrival (`4b1731d` — seen shut in the v142 render), and **the request filed answer** (owner: *"We dont need to allude to some cryptic site"*) is the key `request_filed_line`, default *"Filed as **#{request_id}** — Request has been received. You will get a DM every time the status is updated."*

**The two TODO items, moved whole:**

- 🎥 **CO-STREAMING — one announcement naming both platforms, Twitch first, edited in place when the second one starts** (owner, 2026-09-20 16:1x, verbatim: *"also for when someone is co streaming I would like the message to say this person is streaming on twitch and youtube, have the twitch stream first and only link preview the twitch stream. if someone is streaming on one and adds the other i want to edit the previous message to reflect both are live. It would be silly to suppress one of the live avenues someone is on"*). Today (v135) the second platform is held back — `youtube.live_seen` with `announced false, because open_session:twitch` — which is exactly the suppression he means. A BOT build (Python), separate from the go-live page rebuild: designed as [`info/costream-design.md`](info/costream-design.md) — one session, two platforms (`also_*` columns, schema 45 → 46), `add_platform` edits the announcement in place (Twitch first, only the Twitch link previews — the fill wraps the other in `<…>` itself), `drop_platform` when one side ends (the primary ending PROMOTES the other; the session ends only when neither is live), three keys under golive with `golive_costream_mode` on, two log kinds; dispatched to Opus 16:2x as branch `costream` (`C:/lcw/bb-costream`) in parallel with the page build (whose join already expects the new fields). Status: build in flight.

- 💬 **REQUESTS — the filed answer no longer alludes to "the site"** (owner, 2026-09-20 17:0x, verbatim: *"when I make a request, it says as a response: Filed as #11 — staff will see it on the site. You will get a DM every time it moves. We dont need to allude to some cryptic site. Filed as #11 — Request has been recieved. You will get a DM every time status is updated."*). DONE on main 17:1x (conductor, no agent): the sentence was a constant in `requests.py`; it is now the key **`request_filed_line`** (request namespace) with his wording as the default — *"Filed as **#{request_id}** — Request has been received. You will get a DM every time the status is updated."* — editable on the Settings page, `{request_id}` the only placeholder (a validator refuses any other), read at answer time. One routine call: *received* spelled the dictionary way. Rides v143. Status: done, awaiting the deploy.

## 2026-09-20 — The Go-live page rebuilt (v142, 17:02) — twelve sections become five, one list of people across both platforms

**v142 (release `6a6f8e4`, merge `e88573d`, 376k Opus, `golive-page-design.md` — Fable's five rulings + seventeen deviations):** owner: *"on the golive page the youtube and twitch experiences are basically different experiences, this is crap. can we redesign this page to have less menus and a more unified experience? do a mock or fake page first"* → the mock (two rounds, the second inside the real shell) → *"okay i like that mock, make it happen"*. Shipped, front-end only (no route, schema, key, log kind or Python; `contract.json` diff zero): a header strip (live count, the Twitch / YouTube / ping-role mode switches with their own notices, set-up count, watch cadence, a pressable warning cell when the ping-role setup is incomplete); **Live now** cards, both platforms on one card; **Streamers** — ONE row per member from a pure `joinStreamers` over five payloads (a ping role with no link still gets a row; two open sessions are one row; the co-stream fields land as `live: 'both'`), search + five chips, each row a `button.grid-row` with a chevron opening `ui.js:openDrawer` (the moderation page's construct — deviation 1: the side drawer, not the mock's inline panel, because it already existed and the audit said copy it) holding the four groups of moves with today's routes and confirmation bodies verbatim; **Add a streamer** in the page head — one form, routed by shape, an ambiguous value refused in words; **The announcement** with Twitch / YouTube preview chips; **Recent streams** unchanged; **Everything else** — five drawers holding all 36 keys of the three namespaces (a test asserts each lands exactly once; a catch-all takes any key nobody placed) plus the two setup cards, and one Log drawer holding the three `logsSection` nodes behind chips. `site.css` +79 lines; `golive-join.test.mjs` joins the gate + CI. Tests unchanged at **6757**; sweeps **621–626**. ⚠️ KI-26 fired at 87 % on a `> file` run (sighting eleven; the killed xdist run's exit code read 0 — the log said `node down`; read the log, not the code). Verified: boot clean (17:0x), /health ready, /assets/golive-join.js served; the page RENDERED in the browser at 17:0x — the seven-cell strip (Live right now 4, Twitch announcements shadow, YouTube announcements on, Ping roles off, Set up, Watching every 5 min, the Set-up warning cell), four Live-now cards, Recent streams, no console errors on a tracked reload; clicking a Streamers row opened the side drawer with the four groups (Twitch / YouTube / Ping role / Announcements) and the real moves (Unlink · Link their channel · Give them a ping role · Hide · Opt them out). ONE defect seen: the Streamers list arrived SHUT between two open sections (the layout opens only the first) — fixed on main at 4b1731d (open: true), rides v143. Not pressed: any move in the drawer, the search, the chips (rows 621–626 are the owner's).

**The TODO item, moved whole:**

- 📡 **BUILD THE NEW GO-LIVE PAGE** (owner, 2026-09-20 16:0x, verbatim: *"okay i like that mock, make it happen"*, after two rounds on the mock <https://claude.ai/artifact/VGiR2jgHui9E4D9MbCKyw6>). Designed as [`info/golive-page-design.md`](info/golive-page-design.md): twelve sections → five; one `Streamers` row per member joining Twitch + YouTube + opt-out + ping role; one announcement wording with a platform toggle; five closed drawers for the 36 settings keys and one log with chips. ⚠️ **Front-end only — every field is already fetched by today's `load()`; no route, no schema, no key, no log kind, no Python.** A new pure module `assets/golive-join.js` + `site/mock/golive-join.test.mjs` in the gate is where the platforms meet, and a test asserts every key of the three namespaces lands in exactly one drawer (so the next key added cannot vanish). Staff-only page, `golive_mode` shadow, so the blast radius is staff. This is stage 3 of the [UX audit](info/ux-audit-design.md) done for one page, and it sets the row-opens-a-drawer pattern that answers Pop's finding. ✅ **REVIEWED by Fable 16:1x — all five calls stand** (two with additions: the Ping-roles drawer's summary names the two setup cards and the strip warns when setup is incomplete; *Live now* as section + chip is named as the deliberate exception) — **DISPATCHED to Opus 16:1x as branch `golive-page`** (`C:/lcw/bb-golive-page`), the mock's own HTML handed to the builder as the spec. Status: build in flight.

## 2026-09-19 — The docs staleness pass landed (20:3x) — hand-off ready

Owner: *"update all docs using opus and then im gonna swap"*. Opus pass in commits `0d2367d` → `5c2294b` (19 files; the pass's own DONE entry below lists each). Conductor follow-ups 20:3x: `CLAUDE.md`'s checklist count 35 → **37** (the one root-level file the pass could not touch); memory `black-bloc-test-mode-off` written and indexed; the superseded test-channel memory marked. The next session starts from `docs/README.md` → `docs/TODO.md`'s resume block → `docs/KNOWN_ISSUES.md`.

**The TODO item, moved whole:**

- 📚 **DOCS STALENESS PASS after the lift, then a session hand-off** (owner, 2026-09-19 20:0x, verbatim: *"update all docs using opus and then im gonna swap"*). Dispatched to Opus 20:1x: every doc that still describes test mode as on gets a dated note; the uploads-removal, the ten v132–v141 landings and the fact table re-verified; the indexes' status words matched to the files; KI-5 marked moot; one DONE entry for the pass. The conductor updates the memory files and the resume block after it lands. Status: ✅ **LANDED 2026-09-19** — the entry is at the top of [`DONE.md`](DONE.md) with every file touched; the one-line summary is at the top of the 🔁 resume block above. Findings handed back rather than fixed: `CLAUDE.md` says the review checklist has **35** items and it has **37** (that file is outside a docs-only pass); `/api/youtube/status` is **not** anonymously readable any more (it answers `not_signed_in`), so a session cannot read the live YouTube state without a Discord cookie.

## 2026-09-19 — Docs staleness pass after the TEST_MODE lift (no code, no deploy)

**Owner, 2026-09-19 20:0x, verbatim: *"update all docs using opus and then im gonna swap"*.** A
docs-only pass over the whole tree so a cold session can start from `docs/` alone: every doc that
still described test mode as ON got a dated note (never a rewrite of history — what was true is
kept, marked with when it stopped, and followed by what is true now), the ten v132–v141 landings
were reconciled against the repo, and the two indexes were checked both ways by script.

**Measured off `main` `ffea17e` (v141 LIVE), by import and off disk:** `len(KEY_TYPES)` **277** ·
`SCHEMA_VERSION` **45** · `len(bot.COGS)` **22** · `tests/test_bot.py:TOP_LEVEL_NOW` **32** ·
`namespace_of` over `KEY_TYPES` **25** groups · `FEATURES == logkinds.FEATURES` **21** ·
`deploys.log` **140** lines, last `2e48d7c` v141 · `git ls-files docs` **119** ·
`ls docs/info/*.md` **90** (89 + index) · `ls docs/access/*.md` **12** (11 + index) ·
`ls site/public/*.html` **20** · sweeps max row **620** · `review-checklist.md` **37** items ·
`.env.example` ships `TEST_MODE=true` and `bot.py:69–72` builds the guard only when it is set,
so `bot.guard` is `None` on Fly · `cogs/community/events.py:2182` proves
`events_test_retention_minutes` was guard-gated and is therefore inert now. Live: `/health`
answered `ok:true, ready:true, guilds:1, personality_pool_version:1`.

⚠️ **NOT verified:** `pytest` was not run (the 6,757 figure is the v141 deploy gate's, off
`deploys.log`); `node site/mock/check.mjs` was not run (it needs a listening mock, so 20 pages /
186 routes stays the 2026-09-18 reading); no live SETTING was read — the Settings page needs a
Discord sign-in, so every `*_mode` value quoted is the conductor's 2026-09-18 reading; nothing
met Discord and no browser rendered a page.

🔴 **Two findings handed back rather than fixed.** (1) `CLAUDE.md` says the review checklist has
**35** items and it has **37** — that file is outside a docs-only pass. (2)
**`/api/youtube/status` is no longer anonymously readable** — it answered `not_signed_in` on
2026-09-19, where it was read in a browser without a cookie at the v139 boot; `/health` is now
the only live endpoint a session can read unaided, which matters for every future "check the
live state" instruction.

**Three contradictions between docs, each resolved onto one owner:**

- **The deploy count** lived in `architecture.md`'s fact table (**138**, wrong), in
  `access/README.md` (**107**), in `access/runbook.md` (**107**) and in `info/hosting.md`
  (**107**). It is **140**. `architecture.md` owns it; the other three now say the number and
  link there.
- **Secret rotation.** `access/RECOVERY.md` carried a 🔴 open gap saying all 21 names in
  `.env.example` were due rotation, while `DONE.md`'s own 2026-09-18 entry recorded the owner
  closing it (the `.env.enc` purge, 2026-09-10 16:55, preceded the visibility flip at 20:06, so
  the file was never in a public history). A recovery doc asserting an open security gap the
  owner has ruled on is the worst kind of stale. `DONE.md` owns the DECISION; `RECOVERY.md`
  owns the CUSTODY, and its row now says both.
- **The review-checklist count** disagreed three ways: `CLAUDE.md` **35**, `info/README.md`
  **35**, the file itself **37**. `review-checklist.md` owns it; `info/README.md` corrected,
  `CLAUDE.md` handed back.

**Every file touched, one line each:**

| File | What changed |
|---|---|
| `README.md` | Last-verified re-measured; `access/` 10 → **11** and `info/` 88 → **89** beside their indexes; a new **Where the bot stands right now** block — test mode OFF since 2026-09-18 16:08, which features are live to members, which are `shadow` |
| `KNOWN_ISSUES.md` | Header re-dated; **KI-5 MOOT** (banner, body kept); **KI-8**'s "every panel outside `TEST_CHANNEL_ID`" clause marked history, entry itself unaffected; **KI-20** — the defect did not move but members can now meet it; **KI-26** — ⚠️ **both of its own triggers are MET** (a `> file` hang, count 10), the session is owed not optional; **KI-30** — "the fix is on branch `youtube-live-fix`" corrected to LIVE v133/v135, and the live `youtube_live_mode` is `on` though the default ships off |
| `TODO.md` | The dated pass line at the top of the 🔁 resume block (the block itself untouched); the docs-pass item marked LANDED with its two hand-backs; the standing build brief no longer says "TEST_MODE confined"; checklist 33 → 37, sweeps 37 → 620 |
| `DONE.md` | This entry; header re-measured (4,423 lines, newest entry v141 — it said 3,964 / v108) |
| `access/README.md` | Index re-checked both ways by script (12 files, 11 rows, no duplicates, nothing unlisted); deploy row 107/v108 → **140/v141**; sweeps row 1–350 → **1–620** |
| `access/setup.md` | The **Test policy** box marked LIFTED with what replaced it, and kept as the LOCAL shape (`.env.example` still ships `TEST_MODE=true` — verified); first-start cogs 19 → **22**, commands 29 → **32**, no `TEST MODE ON` line on the deployed bot; gate tests 5,546 → **6,757** |
| `access/testing.md` | The live-in-Discord layer's *"staff, in the test channel"* corrected — the self-test posts where `selftest_channel_id` points; hermetic 5,986 → **6,757 + 3 skipped**; header states nothing here was RUN and the live-suite numbers are 2026-09-06 |
| `access/runbook.md` | ⚠️ **The most dangerous stale line in the tree** — the *Test policy* row told an operator the bot speaks only in `#blackbloc-logs`; the *"A panel never appears → expected until TEST_MODE is lifted"* row split into the two things it can mean now; the boot line's YouTube-uploads sentence retired (v139) and `YOUTUBE_API_KEY` rewritten (it said *OPTIONAL and not yet minted*, both false); schema 34 → **45**, cogs → **22**, commands → **32**, deploys → **140** |
| `access/RECOVERY.md` | The rotation gap **CLOSED** with the measurement behind it; `git ls-files docs` 94 → **119**; a warning that a rebuild restoring `TEST_MODE=true` would look exactly like a broken restore |
| `access/OWNER_GUIDE.md` | *"Everything still runs in test mode"* and *"most things there are expected in test mode"* both replaced; the modmail card, the go-live panel line and `events_test_retention_minutes` each say what they mean now; the header flags that this page's COUNTS were not re-checked |
| `access/site.md` | Three *"409 while `TEST_MODE` is on"* claims superseded; `MOCK_TEST_MODE` still defaults on but no longer *"matches the bot's real state"*; pages 18/19 → **20** off disk, routes pointed at `architecture.md` |
| `info/README.md` | **Four duplicate rows removed** (polls-shadow ×3, golive-end ×2, staff-reach ×2 — the stale one every time); **`posted-strings-events-design.md` added**, it had no row at all; five statuses overtaken by landing fixed (posts-paste → LIVE v140, cutover-plan → STARTED, architecture → v141, checklist → 37, gotchas → ten) |
| `info/architecture.md` | ⚠️ **Two fact-table figures were WRONG** — schema **44 → 45** (it contradicted its own v141 history row) and deploys **138 → 140**; two contradictory duplicate rows deleted (Features read 20 against 21); keys 277 re-labelled from a merged branch to `main`; the Shape tree gained **20 modules it had never named** plus `loops.Reconciler`, `command_errors.record`, `clipmd.js`, and says `guard.py` is not installed in production; `storage/db.py` and the 17-pages block fixed |
| `info/cutover-plan.md` | The Status line said NOT STARTED while P5's own row said taken; row 3c (YouTube uploads) struck; **P4z records what ACTUALLY happened at the lift** — the doubled front door — against what it predicted, and names its one wrong sentence; rows 7 and 9 marked taken; P2 still not done and P5 went ahead anyway; §4 rewritten as the current state |
| `info/gotchas.md` | The xdist hang is **×10, not ×5**, and the tenth was on the `> file` run this entry recommends — the retry is no longer a guarantee; kill by tree, never by image name |
| `info/feature-list.md` | The **Test policy** cross-cutting bullet and *"owner verifies in the test channel"* retired; **F3**'s uploads half struck with where it went; counts pointed at `architecture.md` |
| `info/hosting.md` | Deploys 107 → **140**, and now links `architecture.md` rather than competing with it; the hosting DECISION is unchanged by the lift |
| `info/review-checklist.md` | ⚠️ **A brief may no longer tell a build agent "TEST_MODE will catch it"** — anything that posts ships `shadow`; count re-counted at **37** |
| `info/rehearsal-home-design.md` | A banner saying the guard is gone and **this feature is now the only brake**, with the front door's 2026-09-18 16:57 flip as the proof; ⚠️ do not clear `shadow_channel_id`; the "under `TEST_MODE` today" table dated to before the lift |

**Not touched, deliberately:** `black_bloc/`, `site/`, `tests/`, `scripts/`, `CLAUDE.md`, the
`~/.claude/.../memory/` files (the conductor's), `deploys.log`, and every `archive/` and
`phase*-design.md` doc that describes a design as it stood at its own date.

## 2026-09-18 — v141 (16:55): the boot double-post fixed, and the front door gains shadow mode

**v141 (release `2e48d7c`, merge `d6c271d`; two builds, 230k + 278k Opus).**

**The incident (16:08, the boot after the owner's TEST_MODE lift):** the front door posted twice in `#welcome` and a second ticket button appeared — three reconciles start at boot (`cog_load`, `on_ready`, the loop's first tick) with no lock, two ran within a second, both read "no message id" before either wrote one. Taken down by hand at 16:1x (the channel keys cleared, the messages deleted; `log_channel_id` re-set — its default went blank with the flag). **Fix (`boot-reconcile-once`):** `black_bloc/loops.py:Reconciler` — one `asyncio.Lock` per cog, the reconcile's state read INSIDE it, a 60 s window `on_ready` skips on, the loop's tick never skips; the front door, the modmail ticket panel and events reconcile through it, `on_post_published` under the same lock with `stamp=False`; the doubled `event.room_forgotten` row (v110's finding) fixed by the same lock; `posted.duplicates_near` reads the last five minutes before a post and writes ONE important `frontdoor.duplicate_seen` / `modmail.panel_duplicate_seen` row instead of a third message (never deletes — staff final say; fails open; blind beside a healthy door). The regression tests reproduce the incident exactly against the unlocked path. Review-checklist item **37**. Sweeps **616–617**.

**Shadow mode (`frontdoor-shadow`; owner 16:1x: *"okay now that we're in live shadow mode is even more important, i dont want it to post in welcome yet"* → *"lets have that in shadow mode"*):** `frontdoor_mode` off / **shadow** / on (default on): shadow takes the real door down (`frontdoor.taken_down`, the channel remembered), posts and keeps the rehearsal copy in `shadow_channel_id` with `rehearsal_note` naming the real channel, `/ask` answers, and the ticket button follows the door (down wherever it is) while `frontdoor_replaces_ticket_button`; on → shadow and shadow → on swap the two; the `/ask` staff footer and the modmail page's Front door card say the mode in words. S1: the button's rehearsal copy is NOT posted in the home (the door's own Ask-staff button is the ticket door; the home shows exactly what `#welcome` will). No new key. Sweeps **618–620** (619 is the cutover row itself). Tests 6720 → **6757** both orders. ⚠️ KI-26 sighting nine was the first on a `> file` run. Verified: boot clean at 16:55:30 (no reconcile posted anything — the door's channel was still blank), /health ready; the shadow flip itself (frontdoor_mode → shadow, frontdoor_channel_id → #welcome) was set on the settings API right after and checked by token — see the TODO's next line.

**The three TODO items, moved whole:**

- 🚨 **INCIDENT at the test-mode lift (2026-09-18 16:08): the front door posted TWICE in `#welcome`, and a second ticket button too** (measured by token + the action log 16:09: `modmail.panel_posted` ×2 at 23:08:28.110 / .589Z, `frontdoor.posted` ×2 at .529 / 29.352Z, one `frontdoor.ticket_button_hidden` for the FIRST button only — three bot messages sit in `#welcome`: door 1550644709138108427, door 1550644711646302299, ticket button 1550644708227944461). Why: `cogs/community/frontdoor.py` runs `reconcile()` from `cog_load`, from `on_ready` AND from the loop's first tick, with no lock — two ran within a second, each posted a door before either had written `frontdoor_message_id`; the modmail panel cog has the same shape (`on_ready` + loop). Same defect class as the doubled `event.room_forgotten` row (v110). Fix dispatching to Opus (branch `boot-reconcile-once`): an `asyncio.Lock` per cog around the reconcile, the stored id re-read after the lock is taken, `on_ready` skipping when a reconcile ran in the last minute, a test that runs two reconciles concurrently and asserts one post. Cleanup: the orphan door and the untracked button deleted by token once the tracked ids are read from `/api/settings`. Status: fix dispatching; cleanup in progress.

- 🚪 **FRONT DOOR (and the ticket button) NEED A SHADOW MODE — the owner does not want them in `#welcome` yet** (owner, 2026-09-18 16:1x, verbatim: *"okay now that we're in live shadow mode is even more important, i dont want it to post in welcome yet"* → *"lets have that in shadow mode"*). Measured: `frontdoor_mode` is off/on only, so the 16:08 boot posted the real door in `#welcome` the moment test mode went. DONE by hand 16:1x: `frontdoor_channel_id` and `modmail_panel_channel_id` cleared (DELETE on the settings API — a blank posts nothing, `/ask` still works), the three messages deleted by token, `log_channel_id` re-set to `#blackbloc-logs` (its default became blank when test mode went — measured on `/api/settings`). BUILD dispatched to Opus (branch `frontdoor-shadow`): `frontdoor_mode` gains **shadow** (the rehearsal copy with `rehearsal_note` goes to `shadow_channel_id` and nothing to the real channel; the real one is taken down on the flip; the ticket button follows the door's mode — `modmail_panel` shadows with it); default stays `on`; the owner sets shadow + re-points `frontdoor_channel_id` at `#welcome` after the deploy. Status: hand fix done; build in flight.

- 🔎 **`event.room_forgotten` is logged TWICE per row at boot (v110, 17:14:45Z, events 2 and 3).** Both `on_ready`'s reconcile and `_reconcile_loop`'s first tick read the swept rows before either wrote the cleared id. Harmless (two identical log rows once per restart, the id is cleared once) — fix is a single reconcile at boot or a `review_channel_id` re-read before the write; bundle into the next events build, not worth a deploy alone.

## 2026-09-18 — The post editor keeps formatting on paste (v140, 16:38)

**v140 (release `413f939`, merge `698f33a`, 208k Opus, `posts-paste-design.md`, eleven deviations):** owner: *"whats actually wrong is the formatting was lost when copying from google drive"* → *"2 but do it now"*. Why: a Discord modal and a browser textarea take the clipboard's plain text; Google Docs keeps headings, bold, bullets and links in its rich flavour. Shipped (site only, no Python): `site/public/assets/clipmd.js` — a dependency-free regex tokeniser + tree walk turning a rich-clipboard fragment into Discord markdown (bold / italic / underline / strike / code, `<h1>`–`<h3>` and Docs' styled-paragraph headings by size or class, nested bullets and numbers, masked links, blank lines between blocks, scripts / styles / images dropped; four Google-Docs traps pinned by fixture: the `font-weight:normal` guid wrapper, the underline Docs puts inside its own links, the `<p>` inside every `<li>`, styled-`<p>` headings); the posts page's body editor converts on `paste` when a rich flavour exists and differs from the plain text, inserts through `execCommand('insertText')` so Ctrl+Z works, shows a dismissable note and a **Paste keeps formatting** hint; `clipmd.test.mjs` joins `deploy.ps1` and CI. ⚠️ The `/posts` Discord modal still loses formatting and always will — a modal never sees the clipboard. ⚠️ No real Google Docs clipboard has been pasted by anyone yet — row 613 is that proof. KI-26 fired once more in the build (sighting nine). Tests unchanged at 6720; sweeps **613–615**. Verified: boot clean at 16:38:26 (no front door or ticket button posted this time — both channel keys are blank), /health ready, self-test 116/116, and the live site serves /assets/clipmd.js (200). No real Google Docs paste yet — row 613 is the owner's.

**The TODO item, moved whole:**

- 📋 **POSTS — formatting is lost when a post is pasted from Google Docs** (owner, 2026-09-18 16:0x, verbatim: *"whats actually wrong is the formatting was lost when copying from google drive"* — the welcome post, edited through `/posts` 15:58). Why: a Discord modal field and a browser textarea both take the clipboard's PLAIN text; Google Docs' headings, bold, bullets and links live in its rich-text (`text/html`) flavour, so they never arrive. Two fixes: (a) NOW, one-off — read the Google Doc through the Drive connector, convert it to Discord markdown by hand, and set the post body on the posts page; (b) BUILD (small, site only) — the posts page's body editor listens for `paste`, reads `clipboardData.getData('text/html')` when present, and converts headings → `## `, bold → `**`, italics → `*`, bullets → `- `, numbered → `1.`, links → `[text](url)`, with the plain text as the fallback; a **Paste keeps formatting** note on the editor and a preview through the existing `discordmd` renderer. Owner 16:0x: *"2 but do it now"* → (b) dispatched to Opus 16:0x as branch `posts-paste` (`C:/lcw/bb-posts-paste`), over the budget line at his word; (a) not needed once (b) lands — he re-pastes. Status: build in flight.

## 2026-09-18 — The YouTube UPLOADS half removed (v139, 10:05) — links and live detection stay

**v139 (release `fad4e50`, merge `72733e5`, 485k Opus, `youtube-uploads-removal-design.md`, sixteen deviations):** owner: *"the youtube uploader we should just fully trash"* (after *"i dont super care for uploads right now"* and the measurement that YouTube's RSS feed endpoint answers 404 for every channel from every address — 20/20 failures 2026-09-17 21:07). Removed: the feed poll loop and sweep, the seed-on-link, the upload announcement and its fan-role ping, the Atom parser + `youtube_feed.xml`, seven keys (`youtube_mode`, `_channel_id`, `_ping_role_id`, `_ping_fan_roles`, `_announce_shorts`, `_template`, `_poll_minutes`), `GET /api/youtube/videos`, six routine log kinds, the `/youtube` Setup sub-panel, the page's sweep card + recent-uploads table; `/youtube` now hides when `youtube_live_mode` is off; the channel TITLE (which came from the feed) now comes from one `channels.list` (1 unit) at link time with a key, else the `UC…` id; `FEATURE_LABELS["youtube"]` = *YouTube*; the guide's step rewritten. Kept: `youtube_links`, link / unlink both doors, the DM on a staff unlink, the whole LIVE half (untouched, KI-30 still WATCHING). `youtube_videos` orphaned, not dropped — schema stays 45. KI-11 / KI-12 / KI-13 → CLOSED (moot); `phase16-design.md` retired in place. Keys 284 → **277**; routes 187 → **186**; tests 6808 → **6720** both orders (−88, four added that assert the removal); `BEFORE_LOOPS` 20 → 19; sweeps **609–612**. Verified: boot clean (logged in 10:05:49, the youtube cog loaded, one 'settings ignored: youtube_mode' line for the orphaned stored row — as designed — and no feed warning for the first time since v131), /health ready; /api/youtube/status read in the browser 10:07: `api_key_set true, links 1, live_mode on, live_minutes 5, live_end_misses 2, live_running true, last_probe_at 17:05:49Z, probed 1, quota_today 0, botcheck false, live_now 0, reading_live 0` — the nine upload fields absent, the live half probing (row 611 done; and the wall was NOT served on this probe, so the bot-check is intermittent, not constant — noted for KI-30).

**The TODO item, moved whole:**

- 🗑️ **TRASH THE YOUTUBE UPLOADER (owner, 2026-09-18 09:2x, verbatim: "the youtube uploader we should just fully trash")** — the uploads half of the YouTube feature goes (the feed poll, the seed, the upload announcement, its keys, its panel lines, its site bits, KI-11/12/13 closed as moot); the LINKS and the LIVE half stay (live detection reads the `/live` page + the Data API, not the feed). Designed as [`info/youtube-uploads-removal-design.md`](info/youtube-uploads-removal-design.md), dispatched to Opus 09:22 as branch `youtube-uploads-removal` (`C:/lcw/bb-yt-removal`); status: build in flight. Was: the feed answered 404 for every channel from Fly and from home (measured 2026-09-17 18:4x–21:07: 20/20 failures, KI-12 had it at half). Status: designing.

## 2026-09-18 — The repo is PUBLIC and Actions run (closed 09:2x; the owner's "make it public, go" found it already done)

Measured 2026-09-18 09:2x: `gh repo view` reads **PUBLIC**; `.env.enc` is absent from every remote branch (the two commits that carried it, `66eea8b` and `8e81a03`, are reachable from nothing — dangling in the local clone only, gone at the next prune); `.gitignore` ignores it and `env-lock.sh` says to keep it outside the repo; CI runs on every push to `main` (five runs listed for the night of 2026-09-17, three green — ⚠️ two were CANCELLED at 20 minutes, the workflow's own timeout, which looks like KI-26's stall reaching CI; watched, not fixed). **Superseded 2026-09-18 17:1x:** no rotation is needed — the purge (2026-09-10 16:55, force-pushed) happened BEFORE the visibility flip, so the encrypted file was never in a PUBLIC history; the two commits that carried it are dangling in the local clone only. (Was: rotating the secrets named in `.env.example` (21 names) if he has not, because the encrypted file was in a public history for a window — the value was AES-256 with 600k PBKDF2 iterations, so the exposure is the passphrase's strength.

**The TODO item, moved whole:**

- 🔴 **Make the repo public so Actions run again (owner, 2026-09-10 16:48, verbatim: "Make the repo public so we can run actions again"; 16:52: "Do b").** History scan before flipping: no `.env` ever committed, no token-shaped values in any commit, docs carry secret NAMES only — but `.env.enc` (the OpenSSL-encrypted copy of the whole `.env`, `scripts/env-lock.sh`) sat in the tree and in 2 commits. Owner chose **(b)**: purge `.env.enc` from history (fresh clone + `git filter-repo --invert-paths --path .env.enc`, force-push), stop tracking it (`.gitignore` un-negated; `env-lock.sh` + owner guide / runbook / RECOVERY say the `.enc` lives OUTSIDE the repo now), THEN `gh repo edit --visibility public`, THEN the owner rotates every secret named in `.env.example` (**21** names — measured 2026-09-11 08:50; the earlier "22" was a miscount — plus `OPERATOR_READ_TOKEN`, which `config.py` reads but `.env.example` omits, if it was ever set in `.env`) because the encrypted file must be treated as exposed. Local main is reset to the rewritten `origin/main` (tree clean, verified); the in-flight `where-picker` worktree branch is rebased onto the new main at landing (`git rebase --onto`), it never touched `.env.enc`. Status: purge DONE 16:55 (force-pushed, local reset, `.env.enc` ignored — commit `7d9120c`); the visibility flip itself was blocked for Claude by the permission classifier and handed to the owner: `! gh repo edit skymitch9/black-bloc --visibility public --accept-visibility-change-consequences` — the owner's `!` run at 18:00 did not take (still PRIVATE); at the owner's word ("Can you run it", 20:06) Claude ran the same command: **PUBLIC 20:06**, and the re-run of CI `34547769123` went GREEN in 3 m 1 s (the private-repo runs had died in 3 s on GitHub's billing block) — Actions run again. ⚠️ CI warns `actions/checkout@v4` / `setup-node@v4` / `setup-python@v5` are forced onto Node 24 — bump when convenient. REMAINING: rotate the 21 names in `.env.example` (+ `OPERATOR_READ_TOKEN` if set) (old commit `8e81a03` stays fetchable by SHA on GitHub until GC — GitHub Support can purge). Moves to DONE once public + rotated.

## 2026-09-17 — The YouTube key's 1Password item (23:38, no build)

`op item create` for **YOUTUBE_API_KEY — Black Bloc (YouTube Data API v3)** in vault **Black Bloc** (API Credential; hostname the Google Cloud console; notes name the `black-bloc` project, the Fly secret name and the rotation path), the value read from `.env` inside the command and never printed; the owner approved the app prompt (the two earlier attempts had timed out waiting for it). Custody: 1Password (vault Black Bloc) + Fly secret `YOUTUBE_API_KEY` + the gitignored `.env`; the console re-mints it.

**The TODO item, moved whole:**

- 🔑 **YOUTUBE LIVE switched on + the API key** (owner, 2026-09-17 17:5x, verbatim: *"lets turn on youtube live, and how do i add an api key for youtube. can you open a new tab and start working on getting that key for me"* → *"b, this project has a chance to grow and if i need to add billers in the future i dont want it connected to my existing work"* → *"do a /youtube for pop https://www.youtube.com/channel/UC7ydYSU1nZOHB7nVV-As_XA"*). Done 17:5x: `youtube_live_mode` → **on**; Pawpette's channel linked through the website (`POST /api/youtube/links`, `UC7ydYSU1nZOHB7nVV-As_XA`); a separate Google Cloud project **Black Bloc** (`black-bloc`) made in the owner's signed-in console and the YouTube Data API v3 enabled there. ⚠️ The key VALUE is the owner's: Credentials ▸ Create credentials ▸ API key (restrict to the YouTube Data API), then `flyctl secrets set YOUTUBE_API_KEY=… --app black-bloc` from his own terminal (the `!` prefix) — the session never handles the value. **18:03:** the owner put the key in `.env` under the wrong NAME (`youtube_key`) — renamed to `YOUTUBE_API_KEY` and set on Fly from the file without printing it (the bot restarted); the 1Password item (`Black Bloc` vault, bare-titled `YOUTUBE_API_KEY`) needs the owner to approve the app's authorization prompt — `op item create` timed out waiting. The Estate-vault split the owner raised at 18:0x goes to ANOTHER session, at his word. Status: key live on Fly; the vault item waits on his approval click.

## 2026-09-17 — The Where picker's typing direction (v138, 23:11)

**v138 (release `9e2298c`, merge `6f5dd72`, 204k Opus, `where-picker-design.md` follow-up 5, seven deviations):** owner: *"when i made an event it didnt show all the channels in the discord, just a few, why is that"* → measured 22:3x: 136 eligible channels, Discord's native `ChannelSelect` shows its first page (~25) until the member types → three options offered → *"A. have it be a clear direction, if you do not see your channel start typing the channel name and it should appear"*. Shipped: `events_where_hint` (text, `events`, blankable — a blank draws nothing), default the owner's sentence; rendered as the Where panel's last description line directly above the picker and, in italics, on the draft's Where line while nothing is picked; re-read on every render so a Settings-page edit shows on the next open. Keys 283 → **284**; tests 6793 → **6808** both orders; sweep **608**. ⚠️ KI-26 fired once in the build (sighting eight). Verified: boot clean (logged in 23:11:09), /health ready; the live /api/settings serves events_where_hint under events with the owner's sentence as its value and default (registry 284 keys). The line on the Where panel itself is row 608 — the owner's eye on the next /event.

**The TODO item, moved whole:**

- 💬 **EVENT DRAFT — a clear direction on the Where panel: "If you do not see your channel, start typing the channel name and it should appear"** (owner, 2026-09-17 22:4x, picking option A of three: *"A. have it be a clear direction, if you do not see your channel start typing the channel name and it should appear"*). Why: Discord's native channel select shows ~25 of the guild's 136 eligible channels until the member types (measured 22:3x). Build: one text key `events_where_hint` (default the owner's sentence, editable on the site; blank hides the line) rendered on the Where panel above the picker and on the draft's Where line when nothing is picked; dispatched to Opus 22:40 as branch `events-where-hint` (`C:/lcw/bb-where-hint`). Status: build in flight.

## 2026-09-17 — MOVE TO THE FORUM: an open event's room becomes a post (v137, 23:00)

**v137 (release `a16f5e5`, merge `43ec005`, 366k Opus, `events-forum-design.md` §H, eleven deviations):** owner: *"#pending-ds-poison-meter-pt-what-day-it-was convert this channel into a thread into events"* — event #1, pending, its room made before v136 (v136 leaves open rooms as rooms on purpose). Shipped: `move_room_to_forum` — opens the post as Propose does in forum mode (opening line + review card + Approve / Deny / make-a-request, tagged by the event's CURRENT status, the Delete-this-post card), re-points the row (`review_kind` post, thread + starter ids), leaves `events_moved_line` (a key: *"This event now lives in its own post: {post}. This room is being removed."*) as the room's last line, deletes the room WITHOUT settling (a shared `remove_place` extraction — §H-1), one `event.room_moved` row naming the old room id (the room's messages cannot be carried over — Discord has no move); refusals in words (already a post, settled, no room, no forum → Make the forum, the guard, Discord's Create Posts, a host pressing it). Doors: **Move to the forum** on the `/event` panel's event card (⚠️ §H-2: the room's Delete card was posted before v136 and a posted message keeps its components — nothing re-renders it, so the `/event` card, drawn fresh each time, carries the button) and on the events page's queue rows behind a confirm (`POST /api/events/{event_id}/forum`, not a contract row — §H-4 — covered by a bespoke check + ten route tests). No schema change. Keys 282 → **283**; tests 6755 → **6793** both orders; sweeps **603–607**. Verified: boot clean (logged in 23:00:11), /health ready; Move to the forum pressed on the events page 23:0x for event #5 (the pending 'What Day It Was') → POST /api/events/5/forum 200; by token the forum holds post 'What Day It Was · 2026-10-03' (1550386189759156336) tagged pending with the opening line + card + Approve / Deny / Not an event — make it a request and the Delete-this-post card, and the old room no longer exists (row 603 done); a member-made 'Bot Stuff · 2026-09-18' post already sat in the forum from the owner's own test (row 597 done by him).

**The TODO item, moved whole:**

- ➡️ **MOVE AN OPEN EVENT'S ROOM INTO THE EVENTS FORUM — a staff move, room → post** (owner, 2026-09-17 22:1x, verbatim: *"#pending-ds-poison-meter-pt-what-day-it-was convert this channel into a thread into events"* — event #1 *What Day It Was*, pending, proposed by [DS Poison Meter] PT, its room made before v136). v136 leaves open rooms as rooms on purpose (design §C); this adds **Move to the forum** for exactly that: a staff button on the room's Delete card + **Move to the forum** on the site's event card (`POST /api/events/{id}/forum`), which opens the post as Propose would in forum mode (card + decision buttons, tag by status), re-points the row (`review_channel_id` = thread, `review_kind` = post), posts one line in the old room naming the post, and deletes the room (the event's messages so far stay in Discord's past — named). Refused in words when the forum is not set / the event is settled / already a post. Designed as §H of `info/events-forum-design.md`, dispatched to Opus 22:12 as branch `events-move-to-forum` (`C:/lcw/bb-events-move`). Status: build in flight. Meanwhile (22:08–22:11): the events forum was MADE (`#events` 1550372982566686802 under BlackMail, six tags) and `events_review_mode` flipped to **forum** on the events page — every NEW event is a post from now.

## 2026-09-17 — Answered: the event draft's Where picker "showed only a few channels" (22:3x, no build)

Owner: *"it has everything from welcome to oppertunities, and then join to create a channel"*. Measured by token 22:3x: the guild has **136** channels of the kinds the picker allows (95 text, 41 voice, 0 stage); in server order `#welcome` … `#opportunities` are the first **22** text channels, and Join To Create is an early voice channel — exactly Discord's FIRST PAGE of a native channel select (~25 entries, positions interleaved across kinds). The picker is `discord.ui.ChannelSelect` (`cogs/community/events.py:1064`), chosen so there is no 25-option cap — Discord shows the rest as you type. Nothing to build; the answer given: type part of the name. Not changed: the type filter (voice / stage / text — no announcement channels, forums or threads).

**The TODO item, moved whole:**

- 🔎 **EVENT DRAFT — the Where picker showed only a few channels** (owner, 2026-09-17 22:1x, verbatim: *"when i made an event it didnt show all the channels in the discord, just a few, why is that"*). Being measured against `WhereSelect` (`cogs/community/events.py:1064`, a `discord.ui.ChannelSelect` — Discord's own picker, no 25-option cap, but filtered by `channel_types` and by what the PRESSER can see). Status: answering.

## 2026-09-17 — EVENTS AS A FORUM under BlackMail, one post per event (v136, 22:07) — ships in room mode until the owner flips it

**v136 (release `bb94a92`, merge `32f4827`, 376k Opus, `events-forum-design.md`, fifteen deviations):** owner: *"can we have events also go down into the Black Mail section, and make a thread channel like we have for request and modmail"*. Shipped: `events_review_mode` (room / **forum**, ships room) and `events_forum_channel_id`; **Make the forum** on the events page and on `/event` ▸ Settings ▸ Rooms… ▸ Forum… makes `#events` as a forum under the BlackMail category with the category's overwrites + the bot's and SIX tags named after the event statuses (pending, approved, live, denied, done, cancelled — deviation 1: `live` was missing from the design's list); in forum mode Propose opens one post per event (`Title · date`, the opening line + the review card + Approve / Deny / Not an event — make it a request, a second card with **Delete this post**), the host is NOT in the post (staff-side like requests and modmail; DMs as today), decisions re-tag, denied / cancelled / done posts are ARCHIVED and never deleted by retention (`event.post_archived`), under TEST_MODE a post is deleted 5 minutes after the end like a room; `review_kind` ('room' / 'post') — schema 44 → **45** through `ADDED_COLUMNS`; `review_place` resolves rooms and posts everywhere; ⚠️ an archived post leaves discord.py's thread cache, so an unresolvable post is NOT a miss (deviation 3 — otherwise every event proposed more than a day ahead would have been cancelled), deletion comes from `on_thread_delete`; a guard-refused forum refuses in words (no test-channel fall-back — the post equivalent would have stored the FORUM as the room and offered it to Delete); `black_bloc/forums.py` shared with requests. NOT built: hand-made posts adopted as events; the events vocabulary is still constants, not keys (deviation 10 → the ✍️ audit). Keys 280 → **282**; routes 186 → **187** (`POST /api/events/forum`); tests 6696 → **6755** both orders; sweeps **596–602**. Verified: boot log clean (logged in 22:07:41, no traceback — the schema-45 column applied silently as ADDED_COLUMNS does), /health ready; Make the forum pressed on the events page 22:08 → POST /api/events/forum 200 and the guild lists forum #events 1550372982566686802 under BlackMail with the six tags (pending, approved, denied, live, done, cancelled) read by token; the reply names test mode and the claim. NOT yet: a post — that needs a proposed event after the mode flip (rows 597–602).

**The TODO item, moved whole:**

- 🗓️ **EVENTS AS A FORUM UNDER BLACKMAIL — one post per event, like requests and modmail** (owner, 2026-09-17 21:2x, verbatim: *"can we have events also go down into the Black Mail section, and make a thread channel like we have for request and modmail"*). Designed as [`info/events-forum-design.md`](info/events-forum-design.md) (`events_review_mode` room/forum, `events_forum_channel_id`, Make the forum under BlackMail, one post per event with the card + decision buttons, tags by status, `review_kind` column → schema 45, posts archived not deleted, the host hears by DM — staff-side like requests/modmail) and dispatched to Opus 21:22 as branch `events-forum` (`C:/lcw/bb-events-forum`). Status: build in flight.

## 2026-09-17 — YOUTUBE LIVE: the silent open-session path now leaves a row (v135, 19:11)

**v135 (release `2dd8fcd`, merge `4b1db3f`, 174k Opus, `youtube-live-design.md` deviations 24–26):** found by the conductor verifying v133 on the live bot: the probe read Pawpette live behind the wall (`live=True, video_id=None, botcheck=True`, run inside the Fly container) and correctly did not announce — her Twitch session #139 was open — but that branch wrote nothing, so `live_now 0` / `quota 0` / no `youtube.*` row made a working probe look like one that never ran. Shipped: the open-session branch writes ONE routine `youtube.live_seen` (or `would_live_seen` in shadow) row on the transition, `announced: false`, `because: open_session:<source>`; both rows come from one `live_seen_details()` builder and the announcing row now says `announced: true`; `live_health` gains `reading_live` (channels the probe reads as live) beside `live_now` (YouTube-source sessions) on the panel, the API and the Go-live card. Named, not fixed: a stream that changes id without going offline writes no second row. Tests 6689 → **6696** both orders; sweeps **594–595** (need a streamer live on Twitch and YouTube at once). Verified: on the live bot one second after the v135 boot (19:11:12) the Logs page carries row #8100 youtube.live_seen for Pawpette — video_id None, botcheck True, mode on, announced False, because open_session:twitch — exactly the row this build exists for; boot log clean, /health ready.

**The TODO item, moved whole:**

- 👁️ **YOUTUBE LIVE — a probe that reads a channel live while their Twitch session is already open leaves NO row, and `live_now` counts only YouTube-source sessions** (conductor, 2026-09-17 18:5x, found verifying v133: Pawpette's probe read live=True behind the wall, but `_live_now` returned at `_any_open_session` — her Twitch session #139 — writing nothing, so the site said `live_now 0`, `quota 0` and the owner could not tell the fix worked). Fix dispatching to Opus (branch `youtube-live-seen`): the open-session path writes a ROUTINE `youtube.live_seen` row with `announced: false` and `because: open_session:<source>` (once per stream, not per probe); `live_health` gains `reading_live` = the channels the probe currently reads as live (from `live_video`), shown beside `live_now` on the panel / API / Go-live card. Status: fix in flight.

## 2026-09-17 — BOOT STATUS: red while it restarts, green when it is ready (v134, 19:01)

**v134 (release `79fcef8`, merge `6421c0f`, 221k Opus, `boot-status-design.md`, five deviations):** owner: *"when the bot is restarting can we set its status to red and have the status message say im currently restarting and booting and then turn green again when its ready to accept request in discord status? is that a fair ask or is that not gonna work"* → fair, with one floor: a presence exists only while the bot is CONNECTED, so the seconds between the old process stopping and the new one connecting read grey/offline (Discord's, not ours). Shipped: `BlackBlocBot.__init__` hands `status=dnd` + `CustomActivity(boot_status_text)` to discord.py so the IDENTIFY carries it from the first connect (`setup_hook` re-reads the stored sentence once the database is open and assigns the public `status` / `activity` setters — `change_presence` is impossible before `connect()`); `presence.update_status` passes `status=online` with the head count in the SAME call (never a green bot still saying "restarting"), plus `go_green` for a ready bot that cannot read a head count; `close` flips to DND + `shutdown_status_text` best-effort for the last second. Three core keys: `boot_status_mode` (on), `boot_status_text` *"Restarting and booting — back in a moment"*, `shutdown_status_text` *"Restarting — back in a moment"*. Keys 277 → **280**, core settings 21 → **24**; tests 6670 → **6689** both orders; sweeps **591–593**. Gotcha filed: `Client.activity` strips `name` on the second read (`create_activity` pops it). Verified: boot log clean (presence cog loaded, logged in 19:01:17, 11 s after the old process's shutdown line) + /health ready; ⚠️ the red → green flip itself was NOT seen from here (no gateway view) — row 591 is the owner's eye on the next deploy.

**The TODO item, moved whole:**

- 🟥 **BOOT STATUS — red "restarting" while the bot boots, green when ready** (owner, 2026-09-17 18:0x, verbatim: *"when the bot is restarting can we set its status to red and have the status message say im currently restarting and booting and then turn green again when its ready to accept request in discord status? is that a fair ask or is that not gonna work"*). Fair, with one limit: a presence exists only while the bot is CONNECTED, so the seconds between the old process stopping and the new one connecting show grey/offline, not red; from the first connect until the cogs and the database are ready it can be **Do Not Disturb + "restarting — back in a moment"**, then online with the usual status; before a planned shutdown it can flip to DND "restarting…" for the last second. Keys for both sentences (`boot_status_mode` on, `boot_status_text`, `shutdown_status_text`, all under core). Small build → dispatched to Opus 18:39 as branch `boot-status` (`C:/lcw/bb-boot-status`): DND + the boot sentence in the IDENTIFY, online + the usual count in ONE `change_presence` at ready, DND + the shutdown sentence in `close`. Status: build in flight.

## 2026-09-17 — YOUTUBE LIVE behind the datacenter bot-check page (v133, 18:44) — KI-30's first sighting, fixed the same evening

**v133 (release `b20e4dc`, merge `858feeb`, 215k Opus, `youtube-live-design.md` deviations 15–23):** owner: *"also verify if all the youtube stuff worked"* → measured 18:14–18:20: `youtube_live_mode` on, the key set, Pawpette linked, two probes without error — and `live_now` 0 while she was live. From a home machine the `/live` page carries `"isLive":true` and the canonical `watch?v=` id; **from the Fly machine YouTube serves its *Sign in to confirm you're not a bot* page** — `"isLive":true` survives (absent for an offline channel), the canonical link does not, and ~180 unrelated `"videoId"`s follow, so the old fallback would have named a stranger's video. oEmbed on `/live` is 404 everywhere; `embed/live_stream` carries no id. Shipped: `read_page` takes the id ONLY from the canonical link (the fallback is gone) and reports `botcheck`; the cog routes on `probe.live` — *live, id unknown* is its own path: with a key ONE `search.list(part=id, channelId, eventType=live, type=video, maxResults=1)` (100 units) on the transition, remembered so the next probe searches nothing (a day with one channel live once = **101 units** of 10,000), then the 1-unit confirm and the ordinary card; without a key the card links the channel's own `/live` page titled *Live now* with no thumbnail; `youtube.live_id_searched` (routine) + `youtube.live_search_failed` (important); `is_live_now` answers `probe.live` so a restart mid-stream does not end the session; `quota_today` counts units; `botcheck` on the `/youtube` panel, `/api/youtube/status` and the Go-live page's **How live streams are spotted** card. Two hand-written fixtures from the measured markers (no real wall page is in the repo). KI-30 rewritten: WATCHING → the sighting, the fix, what would still break it (the wall dropping `isLive` too would ring no bell). Tests 6649 → **6670** both orders; sweeps **586–590** (Fly-only). Verified live: the bot's own probe_live, run inside the Fly container 18:5x, read Pawpette as live=True / video_id=None / botcheck=True (the wall page: isLive once, canonical href="undefined"); the site's status showed botcheck true, probed 2, quota 0, live_now 0 — nothing announced because her TWITCH go-live session #139 was still open (the one-announcement-per-person rule), and that path writes no row, so the probe's success was invisible — follow-up dispatched.

**The TODO item, moved whole:**

- 📡 **YOUTUBE LIVE — the probe misreads from Fly's address (KI-30's first sighting, day one)** (owner, 2026-09-17 18:1x: *"also verify if all the youtube stuff worked"*). Measured 18:14–18:20: `youtube_live_mode` on, Pawpette linked, the key set, two probes ran with no error — and `live_now` stayed 0 while she WAS live (`Routing a NG+ Speedrun`). From this machine the `/live` page carries `"isLive":true` + the canonical `watch?v=` id; **from the Fly machine YouTube serves a *Sign in to confirm you're not a bot* page** that still says `"isLive":true` (0 for an offline channel — the signal survives) but has NO canonical link and ~180 unrelated `"videoId"`s, so the bot's id is wrong or missing and nothing is announced. oEmbed on `/live` is 404 everywhere; the embed live-stream page carries nothing. Fix dispatched to Opus (branch `youtube-live-fix`): live = `isLive` (as now); the id ONLY from the canonical link; when live without an id → with a key ONE `search.list(channelId, eventType=live, type=video, maxResults=1)` (100 units, on the transition only) then the 1-unit confirm; without a key announce the `/live` URL itself (a valid link) titled *Live now*; `youtube.live_seen` written either way; KI-30 rewritten with the measured shape. Her uploads FEED also answers 404 (uploads only; not the live path). Status: fix in flight.

## 2026-09-17 — MEETING MINUTES, the prototype (v132, 18:32) — voice receive proved, ships OFF

**v132 (release `82c3467`, merge `41a9f26`, 540k Opus against 200–300k, `minutes-design.md`, ten deviations):** owner: *"how hard would it be to have a meeting minutes bot? … Maybe a full transcript that later gets processed into a concise set of notes."* → *"start building the prototype thats fine, we will keep this feature off for a while and just test it until we're absolutely sure its ready"*. The spike passed: `discord-ext-voice-recv` 0.5.2a179 (a pre-release — `pyproject.toml` names it; its `audioop` import pins the image to Python 3.12, **KI-31**) installs and decodes real Opus on 3.12.10 / discord.py 2.7.1; the Fly image gained `libopus0` and NOT ffmpeg. Shipped: `/minutes` (staff-only, `HIDDEN_WHEN_OFF`) — Start / Stop / Where notes go… / Logs / the site link; per-speaker 16 kHz mono WAV chunks every `minutes_chunk_seconds` (60) → Groq Whisper → `meeting_lines`; Stop by button, everybody leaving, *stop notes* in chat, or `minutes_max_hours` (3); the notes through `llm.py` with `minutes_prompt` → an embed + the transcript as a `.txt`, under the guard's landing in TEST_MODE; the Minutes page (`minutes.html`, six routes: edit / post again / write again / delete); eleven keys under **events** (the 25-cap → events reaches 33 with a Find box); schema 43 → **44** (`meetings` with a partial unique index — one open meeting per guild — and `meeting_lines`); log feature `minutes` (twelve kinds). Keys 266 → **277**; tests 6479 → **6649** (+3 skipped where the extension is absent) both orders; cogs 22, commands 32; sweeps **572–585**. Verified: boot log — every cog loaded, `/minutes` hidden in the guild, `/health` ready. ⚠️ Nothing has met Discord: no voice channel joined, no audio received, no chunk reached Groq — row **572** (the Meeting Room join) is the owner's.

**The TODO item, moved whole:**

- 🎙️ **MEETING MINUTES — a command that has the bot join a voice meeting, record, transcribe, and write concise notes** (owner, 2026-09-17 17:0x, verbatim: *"how hard would it be to have a meeting minutes bot? I want a command so if we're having an important meeting and i want the bot to be able join and take notes. Maybe a full transcript that later gets processed into a concise set of notes."*). Assessment given 17:1x: voice RECEIVE needs a third-party extension, opus/ffmpeg in the Fly image, per-speaker streams → Groq Whisper (the key exists) → the bot's LLM for the notes. **Owner 17:2x: "start building the prototype thats fine, we will keep this feature off for a while and just test it until we're absolutely sure its ready"** → designed as [`info/minutes-design.md`](info/minutes-design.md) (the receive spike FIRST, then `/minutes` staff-only, `minutes_mode` off, schema 43 → 44, the Minutes page); dispatching to Opus as branch `minutes` (v131). Status: prototype build dispatching.

## 2026-09-17 — ERRORS on the site's Logs page + Try again (v131, 18:12) — and v130, the zone-picker crash every new member hit

**v130 (17:27, release `d739726`, `479fe29`, conductor):** owner: *"there is an error on event creation the bot just posted in discord. do we have a lot of that and why?"* → measured: `ZonePanel failed` / `InteractionResponded` — `panels.opened` deferred unconditionally and the event draft's zone picker handed the same interaction to `open_draft`, which opened it again; it fired for EVERY member whose first Propose had to ask for a time zone (two mods in `#welcome-test`, 17:15 and 17:24 — the owner's *"timezone stuff seems to be a reoccuring issue with multiple people"*). `opened` defers only when not already answered; three tests that reused one interaction across presses start the press fresh.

**v131 (release `709defe`, merge `64684d6`, 340k Opus against 200–300k, `errors-design.md`, seven deviations):** owner: *"it should prompt them to try again and not just kick them out and make them start over. deep dive this"* + *"was that logged on the discord site? it should be if not so other staff that aren't us can view the error logs and assist"*. Measured: errors went to the Python log only (Fly's 100-line window) and the member got one sentence with a stale card and no way back. Shipped: `command_errors.record` — every command / panel / modal / button failure is an IMPORTANT `error.<surface>` action-log row (where, error type, message ≤200 chars, the innermost repo frame as `file:line`, the interaction; never a member's words — a test fills a modal with a private sentence and asserts none of it lands), the Logs page's **Errors** chip narrows by kind prefix; **Try again** — `Panel` takes an `again` move and the error sentence carries one button that re-renders the panel the member was on with their answers kept (the event draft + its zone step go where Back goes, since the zone is already stored; requests; every modmail surface; every settings card) — sixteen other panels keep the plain sentence on purpose until checklist item **36** makes each build add its own; four core keys (`error_sentence`, `error_retry_label`, `error_retry_minutes` 10, `error_retry_expired`). Keys 262 → **266**; tests 6455 → **6479** both orders; sweeps **565–571**. ⚠️ Nothing met Discord; the Logs page's chip is proved by test only.

**The two TODO items, moved whole:**

- 🐛 **Event draft: the timezone picker's second defer** (owner, 2026-09-17 17:1x: *"there is an error on event creation the bot just posted in discord. do we have a lot of that and why?"*). Measured in the Fly log: ONE traceback in the 100-line window (17:15, `ZonePanel failed`, `InteractionResponded` at `open_draft`); the action log carries no event failures. Cause: `panels.opened` deferred unconditionally, and the zone picker hands the same interaction to `open_draft` which opens it again — every member with no stored timezone hit it on their first Propose (pre-existing since the when-picker; the mods' first presses in `#welcome-test` found it). Fixed in `panels.opened` (defer only when not already answered), one test; **v130 LIVE 17:27** (`d739726`). Owner 17:2x: *"timezone stuff seems to be a reoccuring issue with multiple people when trying to use the events"* — this WAS the recurrence: the crash fired for every member whose first Propose had to ask for a time zone. Status: DONE-in-place, move at the next landing.

- 🚨 **ERRORS — every command error on the site's Logs page, and a Try-again that keeps the member's place** (owner, 2026-09-17 17:2x, verbatim: *"I also want to know how that experiences effects the end users, it should prompt them to try again and not just kick them out and make them start over. deep dive this"* and *"was that logged on the discord site? it should be if not so other staff that aren't us can view the error logs and assist"*). Measured: `command_errors.report` writes the traceback to the Python log only (Fly's 100-line window) and answers the member with one sentence (*"Black Bloc hit an error running that command; it has been logged. Try again, and tell a Lead if it keeps happening."*) — no action-log row, so the site's Logs page never shows it; the member's panel stays on screen but stale, with no button back. Design + Opus build queued: an `error.*` action-log row per failure (important, the exception type + message + the failing step, no member words), a Logs-page filter, and a **Try again** button on the error sentence that re-renders the panel the member was on with their answers kept. Designed as [`info/errors-design.md`](info/errors-design.md); dispatching to Opus as branch `errors` (beside `minutes`). Status: build dispatching.

## 2026-09-17 — THE REHEARSAL HOME: the rules post and the front door in `#welcome-test` for the mods (v129, 17:00)

Owner, 16:1x, verbatim: *"put the new ticket button and the rules post the bot will be making in a welcome test channel in the basement category. I want the mods to test stuff for me and review what the rules output will look like"* → *"ping me when welcome test is ready"*. `#welcome-test` made under The Basement by the token (staff-visible, `#blackbloc-logs`' overwrites). Under `TEST_MODE` the bot could only speak in its log channel and the channels it made, and the door and the ticket button only wrote would-rows — so the build (release `60958ec`, merge `7badc43`, 366k Opus against 200–350k, `rehearsal-home-design.md`, nine deviations): `shadow_channel_id` (core, blank = the guard's channel) is where EVERY rehearsal goes; `shadow.py` is the one home (`settings_store` aliases its key names — the import goes the other way round); the guard gains `rehearse_in` — **speaking only**, seeded at boot and moved by a `store.on_change` hook, never `own_channel` (which would have widened deletion and slash commands too); the front door and the ticket button post REAL rehearsal copies (their dynamic buttons work) with a `rehearsal_note` line above the embed, kept by their reconciles (moved when the key moves, edited when the wording changes, taken down with the mode, re-posted if deleted by hand), the door under the welcome copy and the ticket button taken down while the door is up. Keys 256 → **262**; core settings 15 → 17; tests 6406 → **6455** both orders; sweeps **554–564**. After the boot: the key set 17:01, **Post it** moved the rules copy (the old copy in `#blackbloc-logs` stranded by design and deleted by hand — deviation 5), and the door's copy arrived on the hook's sweep within the minute — read back by the token at 17:01: the pinned rules post, then *Need something?* with its three buttons. The owner was pinged at 17:0x.

**The TODO item, moved whole:**

- 🧪 **WELCOME REHEARSAL — the rules post and the front door in a `#welcome-test` channel in The Basement, for the mods to review** (owner, 2026-09-17 16:1x, verbatim: *"put the new ticket button and the rules post the bot will be making in a welcome test channel in the basement category. I want the mods to test stuff for me and review what the rules output will look like"*). The channel made 16:1x by the token (`#welcome-test`, The Basement, overwrites cloned from `#blackbloc-logs` — staff see it). ⚠️ Under `TEST_MODE` the bot may only speak in the guard's channel and channels it made, and today's rehearsals (the posts shadow copy) go to the guard's channel while the front door and the ticket button only write would-rows. Design: a `shadow_channel_id` key — where every rehearsal goes (posts, the front door, the ticket button, polls in shadow), default blank = the guard's channel; the guard allows it; the front door and the ticket button gain a real rehearsal copy there. Designed as [`info/rehearsal-home-design.md`](info/rehearsal-home-design.md); dispatched to Opus 16:2x as branch `rehearsal-home` (v129, est. 200–350k). **v129 LIVE 17:00** (release `60958ec`, merge `7badc43`, 366k Opus, nine deviations); `shadow_channel_id` → `#welcome-test` set 17:01; **Post it** pressed → the rules copy moved there (new shadow message `1550295672014635079`), the stranded copy in `#blackbloc-logs` deleted by the token (deviation 5's hand step); the front door's and the ticket button's copies follow on the next sweep (≤5 min). Status: watching the sweep, then the mods.

## 2026-09-17 — SEND TO…: staff hand-offs between requests, events and tickets (v128, 16:09) — and v127, the guide-seeding hotfix

**v127 (15:01, release `de91282`, `6c3f8de`, conductor):** the `front-door` guide seeded at v125 never reached the live app — `Core._seed_guides` ran `seed_guides` only for a guild with no guides at all. It now runs on every guides tick (idempotent by slug, `guide.seeded` with the count); the guide appeared on the first tick and its picture went up at 15:03. Then the day's v125–v127 deploys marked five pictures stale; an Opus re-shoot landed four (media 37–40, the `/modmail` mock redrawn for a v127 field rename) and withheld `/golive` (two live streamers named) → owner *"b"* → drawn by the conductor (media/41). Every picture current, stale 0.

**v128 (release `a0fa7f3`, merge `5a17466`, 617k Opus against 300–450k, `send-to-design.md`, eighteen deviations + one found after):** owner: *"…a staff button to redirect one of them to a different experience… if someone request an event I want to be able to label it as an event and then it gets swept up in our event workflow… The only weird one is turning a modmail into a request or event"* → (A) shipped v125 → *"do all 3"*. `black_bloc/handoff.py` — one implementation, four moves: **request → event** (Send to events… on the post and the panel card opens the pre-filled event draft for staff; Submit files the event in the MEMBER's name, the request closes as **`moved`** with `moved_to = event:<id>`, its post tagged + archived, the member DMed; Back leaves it); **event → request** (Not an event — make it a request: `create_request` in the requester's name, the event cancelled as `handed_off`, the room card carries *Now: request #N*); **ticket → request / event** (a staff modal, then a CONFIRM card DMed to the member — Yes files it in their name, No files nothing and staff may ask again, no answer in `handoff_confirm_hours` (24) counts as No, decided on the read, the wording read back off the embed; a dateless event hands staff the draft instead); **request → ticket** (the staff door, the request untouched). ⚠️ **Migration** schema 42 → **43** (`moved_to` on `requests`, `events`, `modmail_tickets`). ⚠️ A press on a PUBLIC post opens the draft ephemerally with no intermediate card — the deferred-thinking trick (front-door deviation 1 read the other way). `handoff_mode` (on), `handoff_confirm_hours` (24), both under the `request` group — the `/settings` group select is at its 25-cap, now GUARDED by `tests/test_settings_panel.py::test_the_settings_groups_fit_the_select` (§C, found by the front-door build). A defect found after the fourth piece: the `/modmail` panel's copy of the ticket card would have "asked" a practice ticket's nobody — refused in words now. Keys 254 → **256**; tests 6304 → **6406** both orders; sweeps **543–553**. ⚠️ Nothing met Discord; row 544 proves the public post stays untouched.

**The TODO item, moved whole:**

- 🔀 **TRIAGE — requests, events and modmail are confusing to tell apart; a staff move that sends one to another workflow** (owner, 2026-09-17 12:4x, verbatim: *"Request/event/modmail / All are pretty similar and confusing to separate as a user. How hard would it be to build a filter to help sort them? Or maybe a staff button to redirect one of them to a different experience / For instance if someone request an event I want to be able to label it as an event and then it gets swept up in our event workflow experience and becomes an event and no longer a request / The only weird one is turning a modmail into a request or event"*). Assessment given 12:5x (see the reply of that minute): (A) a triage front door, (B) staff **Send to…** conversions with a `moved_to` trail on each table; question put to the owner which first → *"Explain to me how a works…"* → *"Do it"* (12:5x): **(A) designed** as [`info/front-door-design.md`](info/front-door-design.md) (a posted message + `/ask`, three buttons that open the existing ticket / request / event flows, `frontdoor_*` keys, one door per channel), dispatching to Opus as branch `front-door` (v124, behind `request-forum-adopt`); (B) the Send-to moves and the modmail DM confirmation stay queued for after. **(A) LIVE as v125 14:38** (release `e8042a5`, merge `ae6eecb`, 458k Opus, thirteen deviations, `info/front-door-design.md`; `frontdoor_channel_id` → #welcome set after the boot — under TEST_MODE the door sits in `#blackbloc-logs`; the door posted itself there at 14:38 with its three buttons, read back by the token). **(B) still queued:** design the Send-to moves (request↔event with a `moved_to` trail; modmail behind a DM confirmation). **Owner 14:5x: "do all 3"** → (B) designed as [`info/send-to-design.md`](info/send-to-design.md) (request → event through the pre-filled draft, event → request, ticket → either behind a DM confirmation, request → ticket through the staff door; a `moved` status + `moved_to` trail, schema 42 → 43; the settings-group cap guard folded in as §C); dispatching to Opus as branch `send-to` (v127). The `front-door` guide's picture: the conductor shot the self-test's card 14:57 (`scripts/scan/shots/v125-card-frontdoor.png`) but the guide was NOT on the live app — `Core._seed_guides` only seeded a guild with zero guides, so a guide added to the seed later never appeared (fixed `6c3f8de`, **v127 LIVE 15:01**, release `de91282`; the guide appeared on the first tick and the picture was uploaded 15:03 through the editor, `source: capture`, v125; `selftest_purge_minutes` back to 1). Status: (B) build in flight; the picture DONE. **Re-shoot dispatched 15:0x** (Opus with the browser): today's v125–v127 deploys marked FIVE pictures stale through `release.json` (request-file, voice-room, feature-modes, modmail-ticket [mock], golive-announce) — the owner's rule, re-shot each release a feature changes. **Landed 15:1x:** 4 of 5 (media 37–40, `modmail-ticket` mock redrawn for a v127 field rename); `golive-announce` WITHHELD — the card now names two live streamers (LiftedSenses, Pawpette); stale 1. Fork put 15:1x: (a) re-shoot when nobody is live, (b) draw a mock. Also found: the real `/modmail` card is clean again (no open ticket) — the mock could go back to a capture on the owner's word. **Owner 15:2x: "b"** → the conductor draws the `/golive` mock (`scripts/scan/shots/golive-mock.html`, two invented streamers live). Drawn from the v121 capture's layout, two invented streamers (Chadwick Boseman on Twitch, Zendaya on YouTube), uploaded 15:2x as `a drawn illustration`, v127. Status: DONE — every picture current; move at the next landing.

## 2026-09-17 — YOUTUBE LIVE: a quota-free poller that catches a linked channel going live (v126, 14:45)

Owner: *"pawpette is currently live on youtube, it didnt seem to grab that, would we have needed to have her opt in for youtube or what needed to change?"* — measured: the bot had caught her at 13:13 through her TWITCH link (`golive.would_announce`, shadow); a YouTube stream was caught only by Discord's Streaming status → *"can we do a youtube grabber for live? is that possible? i dont super care for uploads right now since so many different people post"*. Shipped (release `e537b2c`, merge `99c307c`, 377k Opus against 200–350k, `youtube-live-design.md`, fourteen deviations, **KI-30**): `black_bloc/youtube_live.py` reads each linked channel's `/live` page every `youtube_live_poll_minutes` (5) for `"isLive":true`, `"isUpcoming":true` (upcoming wins — a premiere is never announced), the canonical `watch?v=` id, and a READABILITY marker (`ytInitialData`) so "offline" and "the page changed shape" are told apart — measured against one real page (Lofi Girl, 1.26 MB, the markers present; the Data API never called); on a sighting one 1-unit `videos.list` confirm when a key exists (else the card reads *Live now*, `something`, the public thumbnail, *via YouTube*); the poller calls go-live's own `go_live` / `end_live` with `source=youtube`, so the announcement, the ping prefix, the past-tense rewrite, the streamer list, the cooldown and the role filters are all go-live's and `golive_mode` decides posting; `youtube_live_end_misses` (2) quiet probes end it, an UNREACHABLE probe never counts; `youtube_live_mode` off/shadow/on (**off**); the `/youtube` panel's **Live streams are…** select + seven health lines, the Go-live page's *How live streams are spotted* card, nine status fields, three log kinds. Keys 250 → **254**; tests 6247 → **6304** both orders; sweeps **534–542**. ⚠️ The confirm path is proved by fixtures only; nothing met Discord. ⚠️ **The owner flips the mode**, and a streamer's YouTube channel must be linked through `/youtube` to be watched.

**The TODO item, moved whole:**

- 📡 **YOUTUBE LIVE — a poller that catches a linked channel going live** (owner, 2026-09-17 13:3x, verbatim: *"pawpette is currently live on youtube, it didnt seem to grab that, would we have needed to have her opt in for youtube or what needed to change?"* → measured: the bot caught her at 13:13 through her TWITCH link only (`golive.would_announce`, shadow); YouTube live is caught only by Discord's Streaming status → *"can we do a youtube grabber for live? is that possible? i dont super care for uploads right now since so many different people post"*). Designed as [`info/youtube-live-design.md`](info/youtube-live-design.md): a quota-free `/live` page probe + one 1-unit confirm per detection, feeding the go-live path as `source=youtube` (so shadow, the ending rewrite, the streamer list all apply); the linked channels are the list (no new opt-in); `youtube_live_mode` off/shadow/on; KI-30 for the scrape's fragility. Dispatching to Opus as branch `youtube-live` (v126). Status: build dispatching.

## 2026-09-17 — THE FRONT DOOR: one message and one command that route a member to a ticket, a request or an event (v125, 14:38) — and the shadow-room hotfix

**The front door (release `e8042a5`, merge `ae6eecb`, 458k Opus against 250–400k, `front-door-design.md`, thirteen deviations):** owner: *"Request/event/modmail — All are pretty similar and confusing to separate as a user. How hard would it be to build a filter to help sort them?…"* → (A) a front door / (B) Send-to moves → *"Explain to me how a works — How does a user start this experience? With a slash command or would we put a button"* → both → *"Do it"*. Shipped: a posted message (*Need something?* + three buttons: Ask staff privately / Request something / Propose an event) kept by its own reconcile like the ticket button, following the welcome post, ONE door per channel (the ticket button's message is taken down when the door lands in its channel — two lines in `Modmail._repanel` stop the two reconcilers fighting; `frontdoor_replaces_ticket_button`); `/ask`, the same three buttons as an ephemeral panel; each press opens the EXISTING flow (modmail's modal; `FileButton` and `ProposeButton` subclassed with their callbacks inherited — zero edits in the requests files); ⚠️ on the POSTED door the event button hands off through a one-button private card first, because a component's `defer()` would draw the member's draft over the public message. `black_bloc/posted.py` (three helpers the ticket button now delegates to); eleven `frontdoor_*` keys filed under the **modmail** group — 🔴 the `/settings` group select was measured at exactly its 25-cap and a 26th namespace would have silently dropped `youtube` (a follow-up guard is owed: nothing asserts `len(groups()) <= SELECT_LIMIT`); the mock's own namespace table had drifted and is now guarded by a contract test; self-test card `panel.ask` (18 → 19 doors); a member guide `front-door` (guides 17 → 18, picture slot empty until the next capture). Keys 240 → **250**; mock 19 pages / **180** routes; cogs **21**, commands **31**; tests 6166 → **6247** both orders; sweeps **524–533**. `frontdoor_channel_id` → #welcome set after the boot; under TEST_MODE the door sits in `#blackbloc-logs` (the door posted itself there at 14:38 with its three buttons, read back by the token).

**The shadow-room hotfix (`005d1ef`, conductor):** owner: *"can members still see the rooms staff spawn from it"* — measured yes: a room started from the hidden lobby's overwrites, then `allow_join` gave the allowed role its view back. While the mode is shadow the mask is applied to the ROOM after the allows; one test. The first v125 deploy run stalled at 25% of pytest (KI-26, **ten**; killed by tree — ⚠️ the kill also caught the `youtube-live` build's concurrent run, which retried) and left a `Release v125` commit, reset before the retry.
## 2026-09-17 — TEMP VOICE SHADOW: the lobby hidden until switched on, then synced by the bot (v124, 14:11) — and the permission audit of the bot's channels

**v124 (release `9733d69`, merge `211b378`, 293k Opus against 150–250k, `tempvoice-shadow-design.md`, eight deviations):** owner: *"i had to manually make join to create not visible to members or everyone, let this mean that the feature is in shadow mode with whatever rules it had before. when shadow mode turns off set member visibility back to on and also do a sync of the permissions of the category"* — after the conductor's v117 report had called the moved lobby staff-only when it carried the Member role's view + connect allow (`creator_overwrites` adds the allowed role; the owner denied Member view by hand at 13:1x). `tempvoice_mode` gains **shadow**: the reconcile (`on_ready`, the five-minute loop, Setup/repair) masks view for `@everyone` and the allowed role on every lobby (allows kept, no edit when already hidden, one `tempvoice.lobby_hidden`); the flip shadow → on runs Discord's own **Sync** with the category, then re-applies the allowed role + the bot + staff reach in one edit (`tempvoice.lobby_shown`); noticed by a `settings_store.on_change` hook AND the reconcile's last-seen mode, one `apply_mode`; a refused edit is `tempvoice.lobby_failed`, never a raise; `/voice`'s two-state toggle became a **Mode…** card with a three-way select; `makes_rooms` is the one predicate (shadow spawns rooms; `/voice` stays visible). ⚠️ `may_act_in` is NOT asked by the hide/show — the lobby is neither owned nor in the test category, and the guard never gated `channel.edit`. Cutover **P5a is a switch** now. Tests 6223 → **6166** both orders (the `mode_on` parametrize dimension went, −80, +23 new); sweeps **516–523**. `tempvoice_mode` set to shadow at 14:11; the lobby read back unchanged (already hidden). KI-26 fired twice in this build (nine).

**The permission audit (owner, 13:2x: *"Do a check of any channel or category the bot has made and make sure the permissions sync / Especially blackmail which should mimic the mod mail category…unless it doesn't include staff roles then fix that"*):** `scripts/scan/perm_audit.py` (gitignored) — BlackMail mimicked ModMail but carried one of the two staff roles; **Leads added** with Aunties / Uncles' bits; the three children re-synced (the forums keep the bot member's own allow). The standing-sweep idea was declined (*"nah we shouldnt need to constantly sweep, this should be good"*).

**The two TODO items, moved whole:**

- 🎚️ **TEMP VOICE — a shadow mode: the lobby hidden from members, un-hidden + synced by the bot when switched on** (owner, 2026-09-17 13:1x, verbatim: *"i had to manually make join to create not visible to members or everyone, let this mean that the feature is in shadow mode with whatever rules it had before. when shadow mode turns off set member visibility back to on and also do a sync of the permissions of the category"*). ⚠️ The conductor's v117 report said the moved lobby was staff-only; measured 13:18 it carried a Member **view + connect allow** (`creator_overwrites` adds the allowed role), so members could see it — the owner set Member view → DENY by hand. Designed as [`info/tempvoice-shadow-design.md`](info/tempvoice-shadow-design.md) (`tempvoice_mode` gains `shadow`; the reconcile keeps @everyone + the allowed role denied while shadow; the flip to `on` runs Discord's Sync then re-applies the allows; P5a rewritten); dispatching to Opus as branch `tempvoice-shadow` (v125). After the deploy the conductor sets `tempvoice_mode` = shadow. Status: build dispatching.

- 🔐 **PERMISSION AUDIT of the bot's channels** (owner, 2026-09-17 13:2x, verbatim: *"Do a check of any channel or category the bot has made and make sure the permissions sync / Especially blackmail which should mimic the mod mail category above for permissions unless it doesn't include staff roles then fix that"*). **Done 13:22** by `scripts/scan/perm_audit.py` (gitignored; dry run then `--apply`): BlackMail mimicked ModMail exactly (Aunties / Uncles allow `117824`, @everyone deny view) but carried only ONE of the two staff roles — **Leads added** with the same bits; its three children (`#modmail-log`, the `modmail` and `requests` forums) re-synced to the category, keeping the bot member's own allow on the forums; ticket and request posts are threads and inherit. Report-only: the lobby (owner-hidden, the shadow build owns it), the test category's children (`#the-main-table`, `#event-heads-up`, `#carlbot-logs`, `#bot-control` match; `#join-log`, Meeting Room, `#the-adult-table`, `#baf-power-quotes` have their own overwrites — not the bot's channels). Follow-up idea declined by the owner 13:2x (*"nah we shouldnt need to constantly sweep, this should be good"*) — no standing sync. Status: done-in-place, move at the next landing.

## 2026-09-17 — A post started by hand in the requests forum becomes a request (v123, 13:15)

Owner: *"If someone makes a thread in the request area, does that link to a request"* → no, the bot only listened for the forum being deleted → *"Make it so we don't create a gap but it'll be hopefully under utilized"*. Shipped (release `2f1c609`, merge `a562583`, 326k Opus against 150–250k, `blackmail-threads-design.md` §G, twelve deviations): `on_thread_create` in the keyed forum files a request on the starter's behalf (title → `what`, first message → `why`), keeps the post as the request's own (`thread_id`), replies the card + the staff move buttons into it, tags it `open`, DMs the filer; somebody `request_who_can_file` excludes gets ONE reply in words (the post is never deleted); `request_mode` off is answered too; idempotent under a per-cog lock + the row check + the author check (the race against the bot's own `open_forum_post`); `request_forum_adopts_posts` (default on). ⚠️ **Migration** schema 41 → **42**: `requests.source` (`panel` for every old row, `forum` only from this door). `via = forum` needed a new `VIA_FORUM` word — `actionlog.stamped` rewrites any unknown via to `discord` — and its two hand-copied JS twins; a pre-existing gap noticed on the way past: `VIA_BOOT` is still missing from both JS via tables (a dash on the Logs page for a boot-time self-test row). Keys 239 → **240**; tests 6196 → **6223** both orders; sweeps **507–515**. ⚠️ Nothing met Discord — no post was started by hand in the live forum; row 515 (the Via column) is the one that proves the new word end to end.

**The TODO item, moved whole:**

- 🧷 **REQUEST FORUM — a post started by hand becomes a request** (owner, 2026-09-17 12:4x, verbatim: *"If someone makes a thread in the request area, does that link to a request"* → no → *"Make it so we don't create a gap but it'll be hopefully under utilized"*). Designed as §G of [`info/blackmail-threads-design.md`](info/blackmail-threads-design.md) (`on_thread_create` in the keyed forum → a row filed by the starter, the card + buttons replied in the post, `request_forum_adopts_posts` default on); dispatching to Opus as branch `request-forum-adopt`, lands as v123. Status: build dispatching.

## 2026-09-17 — REQUEST POSTS carry the staff moves (v122, 12:38) — and the HOMES + PICTURES day closed

**v122 (release `672c608`, merge `68ff768`, 287k Opus, `blackmail-threads-design.md` §F, ten deviations):** owner: *"On the request thread there aren't buttons to edit it or anything / Why is that"* → the moves lived on `/request` and the website by design → *"Yes I want staff, mainly me to be able to interact with request in discord too"*. Every request's forum post now carries the status's move buttons under the card, drawn for everybody and gated on the press (a member's press is refused in words naming the staff role), the site link beside them; `notify_move` re-draws them as the request moves and a decision leaves only the link before the archive. `PostMoveButton` is a `DynamicItem` (`request:<id>:<move>`, registered at `cog_load`) so a post is pressable across restarts; ⚠️ the panel's `CardMoveButton` stays a separate plain item on purpose — discord.py 2.7.1's `ViewStore.remove_view` drops a dynamic template from the process-wide registry whenever a view holding it is stopped, and the panel stops its view on every re-render, so one dynamic class on both surfaces would have silently killed every post's buttons at the first Back; both classes call one `move_pressed`. `request_post_buttons` (default true). KI-29 is one surface wider (a withdrawn post keeps its moves). Keys 238 → **239**; tests 6175 → **6196** both orders; sweeps **499–506**. Test request #9 filed after the boot.

**The HOMES item, closed today:** every feature points at its real channel while `TEST_MODE` stays on (go-live → `#live-now`, no ping role; role menus → `#roles`; birthdays → `#general-chat`; events/raid trains → `#upcoming-events`, raid trains shadow; staff = `#the-main-table`; polls → `#announcements` in shadow; modmail → BlackMail's forum, transcripts → its `#modmail-log`; requests → BlackMail's `#requests` forum; the ticket button → `#welcome`; mod cases stay in `#blackbloc-logs`), and every guide picture re-shot at v121 (16 captures + the birthday and `/modmail` mocks; stale 0).

**The two TODO items, moved whole:**

- 🔘 **REQUEST POSTS — staff move buttons on the forum post itself?** (owner, 2026-09-17 12:1x, verbatim: *"On the request thread there aren't buttons to edit it or anything / Why is that"*). Measured: by design the channel/DM card is the embed + one **Open on the site** link (`requests.site_view`); the interactive staff card (pick up / hold / ready / done / decline / send back) lives on `/request` ▸ Pick a request… and on the website. Fork put 12:1x: (a) the post's first message carries the staff moves (staff-gated, same code path as the panel, the site link beneath), (b) keep. **Owner 12:1x: "Yes I want staff, mainly me to be able to interact with request in discord too"** → (a); designed as §F of [`info/blackmail-threads-design.md`](info/blackmail-threads-design.md) (`request_post_buttons`, the panel's own `CardMoveButton` as a `DynamicItem` on the post); dispatching to Opus as branch `request-post-buttons`, lands as v122. Status: build dispatching.

- 🏠 **HOMES — point every feature at its real channel while TEST_MODE stays on, then re-shoot the guide pictures** (owner, 2026-09-17 00:3x, verbatim: *"We need new screenshots and to start setting the bot to use the right channels for things. So let's stay in shadow mode but start setting homes / For instance go live will post in go live channel"*). Two halves. **(1) Homes:** every `channel`-kind key in the registry (`golive_channel_id` → `#live-now`, `birthday_channel_id`, `events_announce_channel_id`, `poll_channel_id`, `modmail_*`, `request_*`, `raidtrain_channel_id`, the posts' `welcome` target, …) set on https://blackbloc.heygabi.ai/settings.html as the owner, obvious names by Claude, the rest one question at a time. **Answered 08:5x:** birthdays → *"wherever birthdays get posted now"* = `#return-of-the-gen`, which is `1411816390414962700` = **`#general-chat` today** (renamed since the 2026-08-26 scan; `scripts/scan/deep_birthday.py` pins the id) — `birthday_channel_id` set 08:58, birthdays are shadow so nothing posts. **09:0x, prompt boxes (owner asked for them):** events/raid-train announce → **#upcoming-events** `1147289379493118033` (*"make sure it's editable so staff can change it"* — it is the key `events_announce_channel_id`, Settings ▸ events), raid trains → **shadow** because they borrow that channel; staff channel → **#the-main-table** `1094709109841989753` (its viewers now count as staff — measured below); polls → a NEW ask, its own item (🗳️ below), `poll_channel_id` left on the log channel until that build lands. **Box 2, 09:0x:** requests → a NEW ask (🧵 below), `request_notify_channel_id` left on the log channel; the Open-a-ticket button → **#welcome** `1285369365071527997` (*"make sure we can change it. I want it posted right after the rules"* — `modmail_panel_channel_id` set; the ORDER — the button's message posted after the welcome/rules post — is in the 🧵 item); mod cases → keep `#blackbloc-logs`. ⚠️ The guard still refuses any send outside `#blackbloc-logs` while `TEST_MODE=true` (`guard.py:gated_send_message` raises, it does not redirect), so a feature whose mode is **on** and whose home is real would ERROR, not post — every feature pointed at a real home must be **off** or **shadow** first, and `log_channel_id` / `selftest_channel_id` stay on `#blackbloc-logs`. **(2) Pictures:** press **Mark every screenshot stale…** on the hub, then the capture session per `access/guides-capture.md` (needs the dashboard signed in — the owner's click — and Discord web signed in); the cards will still carry the *in shadow* line, which is what the owner asked for ("stay in shadow mode"); P7 in `info/cutover-plan.md` re-shoots them once more when the modes flip. **Verified on the live app 09:17 (GET /api/settings):** golive → `#live-now`, ping role none, role menus → `#roles`, birthdays → `#general-chat`, events/raid trains → `#upcoming-events` (raid trains shadow), staff = `#the-main-table`, modmail category → BlackMail, ticket button → `#welcome`; still on `#blackbloc-logs`: polls, requests, mod cases (kept), the transcripts channel (the owner's click). **Pictures re-shot 12:07** (capture session, Opus with the browser, 16 of 17: media 19–34, `shot_release: v121`, stale 17 → **1**; birthday kept as the drawn mock; `request-file` shot with four request TITLES visible — test rows, no names, flagged; `modmail-ticket` withheld because the card named the owner's own open test ticket — **owner 12:1x: "C"** → drawn as a mock by the conductor (`scripts/scan/shots/modmail-mock.html`, the v121 forum-mode inbox with invented tickets for Chadwick Boseman and Halle Berry), uploaded as **media/35**, `source: mock`, v121; **stale count 0 at 12:15**. Polls/requests homes are set (polls #announcements shadow; requests → the BlackMail forum). Status: **DONE — move at the next landing.**

## 2026-09-17 — STAFF REACH on every bot-made channel, the New-ticket card, a category on every channel picker, the ended wording's editor (v121, 11:41) — and the v120 requests-forum hotfix (11:02)

**v120 (release `768f76a`, `4c92a0b`, conductor, no agent):** the owner's *"Make 1 mod mail and 1 request as test so we can see how they work"* found that test request #6 made NO forum post — under `TEST_MODE` the requests cog claimed its posts for the guard but never the forum, so `open_forum_post` refused and every request was `request.notify_skipped_test_mode`. `forum_of` now claims the keyed forum on every read (the key is the deliberate act, as `modmail_mode = forum` is for modmail); the test that pinned the refusal was flipped. Request #7 then became a post; refiled as **#8** without the filer's name at the owner's word (*"Edit it to not say by Claude"* — there is no edit route, so withdraw + refile; #7's post archived by hand, the KI-29 gap in the flesh). The test modmail is the owner's own DM.

**v121 (release `9f003d5`, merge `129bf70`, 415k Opus against 300–450k, `staff-reach-design.md`, twenty deviations):** owner asks *"for voice channels or any spawned channels make sure the permissions aren't above the aunties/uncles. They need to be able to delete channels too manually"*, *"In black mail add a mod mail log like the other mod mail channel set has… recreate all of those features"*, *"All channel drop-selects should include a category for less confusion"*, *"i see how to edit the go live but not how to edit the eding stream message"*. §A `black_bloc/spawned.py` `staff_reach` — every staff role gets view + manage channels (+ connect for voice) LAST on the lobby, every room, event rooms and ticket channels (`spawned_channels_staff_reach`, default on); ⚠️ the design's measurement was half wrong — `join_roles` had given staff view + connect on temp voice since 2026-08-26, so what §A adds there is **manage channels**. §B `log_open` — the incumbent ModMail log's one card, **New ticket**, posted to the transcripts channel the moment a ticket opens through any door (`modmail_log_on_open`, default on; would-row under the guard; never raises); ⚠️ until the transcripts channel points at BlackMail the card lands in `#blackbloc-logs`. §C `channelLabel` moved to `labels.js` and reads `# name · Category` for every picker (settings rows, polls, posts, role menus, modmail, the events Where control — `site/mock/labels.test.mjs` joined the gate and CI); the Go-live page's **Once the stream is over** editor beside the live one with the same save bar, placeholders and as-you-type preview, `templateEditor` gained `onSaved`; **KI-28 CLOSED** — the Discord key modal's `TextInput` is required only for keys outside `TEXT_MAY_BE_BLANK`. Keys 236 → **238**; mock 19 pages / 178 routes / **15** core settings; tests 6144 → **6175** both orders; sweeps **487–498**. ⚠️ Nothing met Discord; the live Settings page was seen reading `# modmail-log · BlackMail` / `· ModMail` at 11:42 — the owner's own confusion case, told apart.

**The three TODO items, moved whole:**

- 🛡️ **SPAWNED CHANNELS — never above the aunties/uncles; staff must be able to delete them by hand** (owner, 2026-09-17 08:3x, verbatim: *"Also for voice channels or any spawned channels make sure the permissions aren't above the aunties/uncles. They need to be able to delete channels too manually"*). Every channel the bot makes (temp voice rooms, the lobby, event rooms, ticket channels, the BlackMail set) carries an explicit allow for the staff role(s) — view, connect, manage channels — so a hidden or locked room is still reachable and deletable by that role in Discord's own UI; a key names the role(s). Cross-feature, so it is its own small design + build after the lobby build lands (same file). **08:3x measured:** *Aunties / Uncles* = `1073711363337236601`, guild-wide Manage Channels + Manage Roles, and it IS the bot's staff role (it views `#blackbloc-logs`); temp voice rooms carry NO staff allow, so a **hidden** room is invisible to that role and cannot be deleted by hand — event rooms and ticket channels do allow staff view. Designed as §A of [`info/staff-reach-design.md`](info/staff-reach-design.md) (`spawned_channels_staff_reach`, default true, one helper in `black_bloc/spawned.py`), build queued behind `tempvoice-lobby`. Status: design written, build queued.

- 🔎 **Channel dropdowns on the site show a bare name — two `modmail-log`s were indistinguishable** (found 2026-09-17 09:3x when the owner picked the wrong one). **Owner rule 09:3x, verbatim: *"Yes good fix. All channel drop-selects should include a category for less confusion."*** — every channel picker on the site (settings rows, the polls **Where**, the posts target, the guides editor, any `channelSelect` caller) shows `#name · Category`; a channel with no category shows the name alone. `site/public/assets/ui.js` `channelLabel` should read `#modmail-log · BlackMail` (the category after a middle dot, like Discord's own picker); `/api/ref/channels` already carries `parent_id`. Fold into the staff-reach build (`spawned.py` brief) — one function, one test in `site/mock`'s checks if any cover labels.

- ✍️ **Go-live page — the ENDED wording needs the same editor as the live one** (owner, 2026-09-17 10:0x: *"looking at the settings page for black bloc, i see how to edit the go live but not how to edit the eding stream message"*). Measured: the live template has a full-width editor under **Announcement wording**; the end template and the card's top line are one-line rows inside the **Settings** group on the right (`What the announcement says once the stream is over`, `What the card's top line says once the stream is over`), truncated at ~30 characters, and on settings.html the whole Go-live group is a collapsed accordion. Fix: a second editor block **Once the stream is over** beside the live one (same `templateEditor`, both keys, the placeholder list with `{duration}`), the Wording card directly under both; the two settings rows stay (one fact, one home — the editor writes the same key). Fold into the staff-reach / site build (v119).

## 2026-09-17 — BLACKMAIL: modmail and requests as forum channels, the ticket button under the rules, the log channel, the hidden door (v119, 10:51)

Owner, 08:3x–09:0x, verbatim: *"Let's also make a second modmail section for black bloc called Blackmail for viewing tickets, it should have same permission sets as a normal mod mail section just this alternate name. It's what we'll use once mod mail is gone"* → *"In black mail add a mod mail log like the other mod mail channel set has. Scan that channel and make sure we recreate all of those features"* → (prompt box) *"Can we add a section to blackmail called request and have each request make a thread. Better yet have request be one of those thread channels. Same for the mod mail. Let's have mod mail be one of those thread channels so it doesn't grow to infinite length"* → *"It'll be in the welcome but make sure we can change it. I want it posted right after the rules"* → *"Make it BlackMail"*.

**Discord-side by the token, 08:3x (gitignored one-offs):** the **BlackMail** category `1550166808869478420` (overwrites cloned from ModMail: Aunties / Uncles see it, @everyone does not) with `#modmail-log` `1550167775694037075` cloned from the incumbent's log; `modmail_category_id` and `modmail_log_channel_id` point at them (the owner picked the wrong of two same-named logs first — the dropdown fix is TODO 🔎). The incumbent log was measured to carry ONE shape (a **New Ticket** embed, footer `name | id`) — the New-ticket-on-open card is §B of `staff-reach-design.md`, the next build.

**The build (517k Opus against 350–500k, merge `85d88d3`, `blackmail-threads-design.md`, fourteen deviations):** "one of those thread channels" read as a Discord **Forum** (no Community feature needed — measured off the guild's `features`). `modmail_mode` gains **`forum`**: one post per ticket, the starter message is the staff line (the dossier card cannot exist before the ticket row — deviation 1), open/closed tags made by **Setup ▸ Make the forum** (Discord and the website, one path), closing tags + archives + locks the post; ⚠️ under `TEST_MODE` the guard must CLAIM the forum and every post (a claim dies with the process, so the five-minute sweep re-claims — only while the mode is `forum`; the window before the first sweep is refused in words); `may_remove` accepts an owned parent. Requests: `request_forum_channel_id`, one post per request, **six** tags (the design named five — *ready to check* was missing for the review state), moves go into the post, a decision tags + archives; ⚠️ a WITHDRAWN request's post keeps its tag (KI-29). The ticket button stays directly under the welcome post: `modmail_panel_follows_post` (`welcome` | `none`), the order decided by comparing snowflakes, `posts.publish_post` dispatches `post_published` so the button re-posts at once. `PANEL_LINES` no longer names the retired subcommand. Also folded at the merge: `posts.shadow_channel_id(s)` delegate to `black_bloc/shadow.py` (polls deviation 3). ⚠️ **Migration**: schema 40 → **41** (`requests.thread_id`). Keys 232 → **236**; mock 19 pages / **178** routes; tests 6086 → **6144** both orders; sweeps **471–486**. Right after the boot the website's **Make the forum** made both forums under BlackMail — the ticket forum `1550202827270520832` and the requests forum `1550202828469837864` (their keys written by the press) — and `modmail_mode` was set to **forum**.

**The three TODO items, moved whole:**

- 🧵 **BLACKMAIL — requests and modmail as thread channels, so nothing grows without end; the ticket button right after the rules** (owner, 2026-09-17 09:0x in a prompt box, verbatim: *"Can we add a section to blackmail called request and have each request make a thread. Better yet have request be one of those thread channels. Same for the mod mail. Let's have mod mail be one of those thread channels so it doesn't grow to infinite length"*; and on the ticket button: *"It'll be in the welcome but make sure we can change it. I want it posted right after the rules"*). To settle in the design: whether "one of those thread channels" is a **Forum** channel (every post is a thread) or a text channel with private threads (`modmail_mode` = `thread` today, `modmail_staff_channel_id`); requests get the same shape under BlackMail (`#requests`, one thread per request, the card in the thread, `request_notify_channel_id` → it); the posted ticket button is placed directly under the welcome post (the posts feature's `welcome` — post order = rules first, button second, re-posted after a rules re-post if the owner wants it kept adjacent). Designed as [`info/blackmail-threads-design.md`](info/blackmail-threads-design.md) — read as **Forum** channels (one post per ticket / request, tags, nothing scrolls forever); `modmail_mode` gains `forum`, `request_forum_channel_id`, Setup makes both forums under BlackMail, the ticket button re-posts under the welcome post; schema 40 → 41 (behind polls — whoever merges second renumbers); folds the PANEL_LINES defect. **Dispatched 09:2x** to Opus, worktree `C:/lcw/bb-blackmail-threads`, branch `blackmail-threads`, est. 350–500k. Status: build in flight.

- 📜 **BLACKMAIL — a modmail log channel like the incumbent ModMail set has, and feature parity with what that log carries** (owner, 2026-09-17 08:3x, verbatim: *"In black mail add a mod mail log like the other mod mail channel set has. Scan that channel and make sure we recreate all of those features"*). Steps: list the incumbent **ModMail** category's channels + overwrites; make the matching log channel under **BlackMail** (`1550166808869478420`) with the same overwrites; read the incumbent log's recent posts (shapes only — what it logs: opened / closed / claimed / transcript / notes…, never the members' words into docs) and compare against Black Bloc's `modmail_log_channel_id` behaviour (`docs/info/modmail-*-design.md`); gaps become a design + build. ⚠️ Pointing `modmail_log_channel_id` at the new channel while `TEST_MODE` is on makes every transcript post hit the guard — it stays on `#blackbloc-logs` until the cutover unless the owner says otherwise. **08:3x:** scanned — the incumbent's log carries ONE shape (a **New Ticket** embed, footer `name | user id`; six of them, nothing else); **BlackMail ▸ `#modmail-log`** made as `1550167775694037075` with the incumbent log's overwrites. `modmail_log_channel_id`: the owner picked it 09:3x but the dropdown showed TWO `modmail-log`s with no category and he got the incumbent's (`1442613059704066108`); corrected 09:34 to BlackMail's `1550167775694037075` (a PUT that went through this time; verified by GET). Safe under TEST_MODE (`post_transcript` writes a would-row). Parity = a New-ticket card on open: designed as §B of [`info/staff-reach-design.md`](info/staff-reach-design.md), build queued behind `modmail-hide`. Status: design written, build queued.

- 🔎 **Small defect found by the hide-toggle build (2026-09-17 09:2x):** `cogs/moderation/modmail.py` `PANEL_LINES` still tells staff to run `/settings set-value modmail_panel_title` — that subcommand retired at v84 (checklist 33 says never name it). One string + one test assertion; fold into the next modmail build (the 🧵 thread-channels item).

## 2026-09-17 — POLLS SHADOW: a rehearsal mode, the draft opens on the default channel, pinned while open, #announcements by default (v118, 10:11)

Owner, 09:0x in a prompt box, verbatim: *"Can we add a shadow mode? Maybe when a poll is to be made we have a drop down of what channel it should be posted to? Also we should pin the poll for its duration. Also let's default to announcements but in shadow it always post to logs channel with a message saying because it's in shadow mode."* Shipped (release `3fe05ef`, merge `9c51541`, 305k Opus against 200–350k): `poll_mode` gains **shadow** — the REAL poll (panel or native, thread and all) posts into the guard's channel / `log_channel_id` under `poll_shadow_note` (*"Posted here because polls are in shadow — it would have gone to {channel}"*), the row keeps its intended `channel_id` and gains `shadow_message_id` (⚠️ **migration**, schema 39 → **40**, the three-edit `ADDED_COLUMNS` shape this repo uses — no `migrate_x_to_y` functions exist); votes, reminders, close and results work on the rehearsal copy through `where_it_went` / `hunting_grounds`; `poll_pin` (default true) pins on post and unpins on close AND cancel, reading `message.pinned` so a setting flipped mid-poll strands nothing; the Discord draft's **Where** select (it already existed — the design's "no channel pick" row was wrong and was corrected in place) now opens on `poll_channel_id`, shows it, and renders only for those `poll_who_can_create` allows; `black_bloc/shadow.py` is the shared shadow-home helper (`posts.py` still carries its own copy — a test pins the two equal until the BlackMail build's merge folds it). Keys 230 → **232**; tests 6037 → **6086** both orders; sweeps **458–470**. After the boot: `poll_mode` → shadow, `poll_channel_id` → `#announcements` `1285381774876344340`. ⚠️ Nothing met Discord — no poll posted, no pin taken; the pin-notice deletion is unproven against the real API (row 462). The build's `taskkill /F /IM python.exe` during a KI-26 scare killed every python on the machine once; the other build's run survived or re-ran.

**The TODO item, moved whole:**

- 🗳️ **POLLS — a shadow mode, a per-poll channel pick, pinned for the poll's length, default #announcements** (owner, 2026-09-17 09:0x in a prompt box, verbatim: *"Can we add a shadow mode? Maybe when a poll is to be made we have a drop down of what channel it should be posted to? Also we should pin the poll for its duration. Also let's default to announcements but in shadow it always post to logs channel with a message saying because it's in shadow mode."*). `poll_mode` gains **shadow** (the real poll posts into `log_channel_id`/the guard's channel with one line saying it is there because polls are in shadow — the posts feature's shape); the `/poll` draft and the site's create form gain a channel dropdown (default `poll_channel_id`, which defaults to **#announcements** `1285381774876344340`); the poll message is pinned when posted and unpinned when it closes (keys: `poll_pin` bool default true). Designed as [`info/polls-shadow-design.md`](info/polls-shadow-design.md) (schema 39 → 40, `shadow_message_id`); **dispatched 09:2x** to Opus, worktree `C:/lcw/bb-polls-shadow`, branch `polls-shadow`, est. 200–350k. Status: build in flight.

## 2026-09-17 — v117: the lobby in the main voice area, the Open-a-ticket-with door hidden behind a toggle, the go-live announcement rewritten in the past tense (deployed 09:53)

Three Opus builds in one morning, dispatched from four owner asks (08:2x–08:4x), merged as they landed, shipped together as release `7d5d6ad` (gate 6037 passed; boot `TEST MODE ON` with the new wording, `database ready`, `synced 30`, `logged in`; `/health` ready 09:53). Nothing pressed in Discord after the boot except the two go-live SAMPLES the owner asked for, posted into `#blackbloc-logs` by a gitignored one-off (`scripts/scan/post_golive_sample.py`, his real Twitch game and title, the ended one with a sample length).

**Lobby (196k Opus, merge `255974c`, `voice-panel-design.md` § Lobby in the main voice area):** owner: *"Let's capitalize the first letter of each word in join to create channel / Let's move it up to the main voice channel area but keep its visibility staff only, when we swap off shadow mode it should become visible to whatever permissions inherit from the voice group"*, then *"Do a, would the spawned channels be visible to everyone?"*. Renamed `Join To Create A Channel` (Discord + `tempvoice_creator_name`); `guard.allows_place` now also allows a channel the bot owns (the pinned test flipped); a written-down lobby may spawn anywhere (`may_spawn_from` — the conductor's TODO finding had said the rooms would be undeletable; measured, they would not have been SPAWNED at all, `may_act_in` refused first); rooms copy the LOBBY's overwrites (`tempvoice_room_overwrites`, default `lobby`) so a staff-only lobby makes staff-only rooms; `repair_creator_channel` left refusing on purpose (Setup would rewrite the lobby from its category — cutover row **P5a** says sync from Discord, never Setup). Moved after the boot: parent *Voice Channels* `1073710703518683144`, position 0, six overwrites kept.

**Hide toggle (237k, `modmail-doors-design.md` § Hide toggle):** owner: *"Let's keep but hide the open a ticket with option on the bot. Toggleable of course."* `modmail_open_with_button` (bool, default off); three stale windows refused in words (a panel already open, a picker on screen, a modal mid-fill — the last is the only gate a ticket could slip past); the refusal names the key and both doors back. Also that morning, Discord-side by the token: the **BlackMail** category (`1550166808869478420`, overwrites cloned from ModMail; the owner's casing) with `#modmail-log` (`1550167775694037075`); `modmail_category_id` and `modmail_log_channel_id` point at them (the owner picked the wrong of two same-named logs first — the dropdown fix is TODO 🔎). Sweep rows 422 / 428–430 now say to turn the key on first.

**Go-live end (400k against 150–250k, merge `65f0931`, `golive-end-design.md`, thirteen deviations):** owner: *"can we update the message of a stream once it's over / So it's past tense indicating its ended? Make this editable of course"* → shown both wordings → *"Do a, we have time so let's make sure we do it right."* `golive_end_template` (default `**{name}** was streaming **{game}** — the stream has ended. {url}`, placeholders + `{duration}`), `golive_end_author` (`{name} was live on {platform}`), `golive_end_keep_mention` (false — the owner's *"Let's not tag a role when a stream goes live"*, and `golive_ping_role_id` was cleared the same minute), `GET /api/golive/preview` through the real renderers, the **Wording** card on the Go-live page with its rewrite/suffix button; `golive_end_mode` flipped to **edit** by the conductor after the boot (safe: `golive_mode` is shadow). Gap left open as **KI-28**: a BLANK template cannot be set from Discord's `/settings` modal (`TextInput` required=True; Clear restores the default) — the dashboard can. Keys 226 → **230**; mock 19 pages / **176** routes; tests 5986 → **6037**. Sweep rows **449–457**.

**The four TODO items, moved whole:**

- 🎙️ **TEMP-VOICE LOBBY — rename to `Join To Create Channel`, move it up to the main voice area, staff-only until shadow mode ends** (owner, 2026-09-17 08:2x, verbatim: *"Let's capitalize the first letter of each word in join to create channel / Let's move it up to the main voice channel area but keep its visibility staff only, when we swap off shadow mode it should become visible to whatever permissions inherit from the voice group"*). Discord-side channel edits by the bot token (a `scripts/scan/` one-off, not bot code): name, `parent_id` = the main voice category, overwrites copied from the staff area so only staff see it; the tempvoice reconciler must not move it back. The un-hiding at the cutover is a row under P5 in `info/cutover-plan.md` (sync the lobby's permissions with its category) unless the owner wants the bot to do it itself when `TEST_MODE` lifts. **Done 08:3x:** renamed to `Join To Create A Channel` on Discord and in `tempvoice_creator_name` (the lobby is tracked by id in `tempvoice_creator_ids`, so the rename is safe). ⚠️ **The move is blocked by the guard while `TEST_MODE` is on:** a spawned channel is made in the LOBBY's category (`cogs/community/tempvoice.py` `create_voice_channel(category=creator.category)`), and `guard.allows_place` lets the bot delete only inside the test channel's category — `tests/test_guard.py::test_owning_a_channel_does_not_widen_where_channels_may_be_deleted` pins that on purpose — so a lobby in *Voice Channels* would spawn rooms the bot can never clean up, visible to everyone. ⚠️ **Corrected by the build 09:0x:** it would have spawned NOTHING — `_maybe_create` asks the cog's own `may_act_in(lobby)` first; the build added `may_spawn_from` (a lobby written in `tempvoice_creator_ids` may spawn anywhere; the room is owned the instant it exists). Fork put to the owner 08:3x: (a) move now + let the guard delete channels the bot made itself (v117, reverses that rule for owned channels only), (b) move now + `tempvoice_mode` off until the cutover, (c) move at the cutover. **Owner 08:3x: "Do a, would the spawned channels be visible to everyone?"** — answer: today a room copies the CATEGORY's overwrites (`owner_overwrites(category=creator.category)`), not the lobby's, so in *Voice Channels* it would be visible to everyone the category shows; the build makes rooms copy the LOBBY's overwrites (key `tempvoice_room_overwrites`, `lobby`|`category`, default `lobby`), so a staff-only lobby spawns staff-only rooms until the cutover syncs the lobby to its category. Dispatched to Opus 08:3x as branch `tempvoice-lobby` (guard: `allows_place` also allows channels the bot owns; the pinned test flips), lands with the modmail toggle as v117; the Discord move (parent → *Voice Channels* `1073710703518683144`, overwrites kept) happens AFTER v117 boots. **LANDED 09:1x:** 196k Opus (est. 100–200k), 5986 → 5991 tests both orders, keys 226; reviewed (the guard clause is one line; `may_spawn_from` = a written-down lobby or the old place rule; `repair` left refusing on purpose — P5a says never press Setup to sync); **merged `255974c`** on main, pushed, NOT deployed — waits for `modmail-hide` and `golive-end` to ship as one v117. Status: merged, deploy pending.

- 🎟️ **MODMAIL — hide *Open a ticket with…* behind a toggle, and a `BlackMail` category for Black Bloc's tickets** (owner, 2026-09-17 08:3x, verbatim: *"Let's keep but hide the open a ticket with option on the bot. Toggleable of course. / Let's also make a second modmail section for black bloc called BlackMail for viewing tickets, it should have same permission sets as a normal mod mail section just this alternate name. It's what we'll use once mod mail is gone"*). (1) A bool key (default off) that draws or hides the staff **Open a ticket with…** button on `/modmail`; the code stays. (2) A Discord category **BlackMail** cloned from the incumbent **ModMail** category's overwrites (`1442613057628012594`, which is `MODMAIL_CATEGORY_ID`, a CONSTANT in `settings_store.py` — it becomes a `channel`-kind key so the Settings page can point Black Bloc's ticket channels at BlackMail; the constant is the default until the owner flips it). **08:3x:** `modmail_category_id` was ALREADY a key (default the constant); **BlackMail** made on Discord as `1550166808869478420` (`scripts/scan/blackmail_category.py`, overwrites cloned from ModMail: the staff role sees it, @everyone does not) and the key pointed at it; the hide toggle (`modmail_open_with_button`, bool, default off) dispatched to Opus 08:3x as branch `modmail-hide`. **LANDED 09:2x:** 237k Opus (est. 100–180k), 5986 → 5993 tests both orders, three stale windows gated (the press, the pick, the modal submit), refusal names the key; reviewed, **merged** on main, NOT deployed — ships as v117 with the lobby build and `golive-end`. At the landing ritual: sweep rows **422, 428–430** must say *turn `modmail_open_with_button` on first*. Status: merged, deploy pending.

- 📺 **GO-LIVE — edit the announcement to past tense once the stream ends, editable wording** (owner, 2026-09-17 08:3x, verbatim: *"For the golive channel, can we update the message of a stream once it's over / So it's past tense indicating its ended? Make this editable of course / Show me our current message and what it could look like after the stream has ended"*). **Measured 08:4x:** ALREADY BUILT as `golive_end_mode` (off | edit, live **off**) + `golive_end_suffix` (` — stream ended`): *edit* appends the suffix to the text and turns the card's author line to *"was live on Twitch"* with *· stream ended* in the footer — but the sentence itself stays present tense ("is currently streaming … — stream ended") and the card's verb is a constant (`golive.ENDED_VERB`), not a key. Rendered both with the server's own template for the owner. Fork put 08:4x: (a) a `golive_end_template` (full past-tense rewrite, same placeholders; blank = today's suffix) + `golive_end_author` for the card's line, then end mode → edit; (b) just flip end mode to edit with the suffix as is. **Owner 08:4x: "Do a, we have time so let's make sure we do it right."** → design `info/golive-end-design.md`, Opus build on branch `golive-end` (golive files only — no overlap with the two builds in flight). **Dispatched 08:4x** to Opus, worktree `C:/lcw/bb-golive-end`, branch `golive-end` off `fb1600b`, est. 150–250k (three keys, `ended_render`, `{duration}`, `GET /api/golive/preview`, a Wording card on golive.html). Status: build in flight (third of three). **Then (owner 08:5x, verbatim: *"Once everything is done, post a sample of both in the black bloc logs channel after all the testing menus delete themselves. So I can review them. Use my skyaiva channel"*):** after v117 boots and the self-test's cards purge (1 min), a gitignored one-off `scripts/scan/post_golive_sample.py` renders the LIVE and the ENDED announcement (text + card) for `https://twitch.tv/skyaiva` through the real `golive.render` / `ended_render` / `announcement_embed` / `ended_embed` with the guild's saved keys (game/title read from Helix's channel info so they are his real ones, duration a sample `2 h 10 min`) and posts both into `#blackbloc-logs` by the bot token, labelled *sample — live* / *sample — ended*; nothing else pinged, nothing edited. If the owner wants this as a standing staff move (*Post a sample here* on the panel), that is a follow-up.

- 🔕 **GO-LIVE — no role tag on a go-live for now** (owner, 2026-09-17 08:4x, verbatim: *"Let's not tag a role when a stream goes live. We'll end up tagging the related fan group but not yet."*). `golive_ping_role_id` (was the Events role `1550153505237635173`) → blank on the Settings page; the fan-role prefix is pings' (`pings_mode` off). **Cleared 08:4x** (`DELETE /api/settings/golive_ping_role_id` → `cleared: true`, value null; a PUT of null or '' is refused by design — the API's clear is the DELETE). Status: DONE-in-place, move at the next landing.

## 2026-09-17 — PINGS, REMADE: a streamer list fed by going live, lazy fan roles, raid trains wired in, Community onboarding kept in step, role menus retiring (v116, 00:28)

**Owner, 2026-09-16, verbatim:** 16:4x *"lets turn off the pings stuff, make the guide staff only. We want to work on the pings experience more"* → 22:2x *"let's first go over what it does before we add to it"* → *"Should we combine with the raid train list?"* → *"A wire in pings / Also for roles can we start a listener, each time someone goes live their added to a streamer list / Then a user can opt into a streamer role? … We're moving to a discord community server so that will handle some role stuff. / We need this system to work with"* → *"Yes that was the final part. Community and role prompts"* → *"Our role menus will probably retire to use discords to turn them off for now"* → forks F-PR1/2/3 all **A** → *"A"* (build now).

**What shipped (release `29c77b6`, merge `f420d3a`):** schema 38 → **39** (`streamers` + `golive_fan_roles.unworn_since`); `pings.saw_streaming` from `_go_live_once` and the Helix poller — anyone Discord shows streaming lands on the list at their first go-live, linked or not, above the announcement opt-out and the ignore role (deviation 1 — one staff press hides them); **Take me off the streamer list / Put me back**; fan roles made on the FIRST FOLLOW (`pings_fan_role_creation` = `follow`, default) and pruned after `pings_empty_role_days` (30) unworn, never a worn one; the list pruned after `pings_streamer_stale_days` (90); raid trains: the *"the train moves"* line mentions the on-air streamer's fan role and the new self-serve raid-train role, `allowed_mentions` exactly those, **Set up the raid-train role** beside the Events one; the panel is *what pings you* — events / go-lives / raid trains toggles, Follow over the LIST, stop moves whatever the mode; **Community onboarding**: `pings_onboarding.reconcile` keeps two prompts (*What should ping you?* and *Which streamers?*, capped by the key `pings_onboarding_option_cap`, default 25) in step on the sweep and after any role change, writes only on a diff, never touches a foreign prompt or `enabled`, refuses in words without `COMMUNITY`; the site's Go-live page gains the streamer table (hide / restore) and the Onboarding card; the `pings-follow` guide's seed rewritten. **Role menus:** `rolemenu_mode` off since 2026-09-16 22:4x; the §C6 check found the command HIDDEN with the mode off (so Grants were unreachable) and hand-outs refused — fixed first: `/rolemenu` is `NEVER_HIDDEN`, **Hand roles out…** draws whenever a menu has options. Keys 220 → **225**; mock **19 pages / 175 routes**; tests 5889 → **5986** both orders. Eighteen deviations at the design's foot; the headline: **Discord publishes no onboarding limits anywhere the build could reach** (the library carries no constants; the endpoint needs Manage Server + Manage Roles per its docstring), so the cap is a key to raise when the number is known, and `edit_onboarding` re-numbers prompts by position, so the diff compares titles and roles, never ids. Cost **630k** Opus against 250–350k ×2.

**Measured at the landing:** gate green, `/health` ready, the boot log read; nothing pressed in Discord. ⚠️ **Every onboarding path is proved against fakes only** — the server is not a Community server; sweep rows **442–445** are the only real proof and cannot be pressed until it is. `pings_mode` stays **off** until the owner turns it on; the `pings-follow` guide needs **Reset the whole guide** then (the seed refresh only touches step text) and its audience set back to member. Design: [`info/pings-remake-design.md`](info/pings-remake-design.md).

**The two TODO items, moved whole:**

- 🔔 **PINGS — off, and the experience to be reworked (owner, 2026-09-16 16:5x, verbatim: "lets turn off the pings stuff, make the guide staff only. We want to work on the pings experience more").** Done the same minute from the owner's signed-in dashboard session (audited Via: Website): `pings_mode` **on → off** (so `/pings` hides within a minute, the Events toggle and fan roles stop being offered; unfollowing still works by design) and the `pings-follow` guide's audience **member → staff** (it leaves the member hub and `/help`'s links). ⏳ **Waiting on the owner:** what "work on the pings experience more" should become — no design until he says what he wants changed. 22:2x the owner asked *"Should we combine with the raid train list?"* → assessment given (wire pings INTO raid trains — fan roles on the train's "moves" posts and a raid-train opt-in on the pings panel — rather than folding the train LIST into `/pings`); → **owner 22:2x, verbatim: "A wire in pings / Also for roles can we start a listener, each time someone goes live their added to a streamer list / Then a user can opt into a streamer role? / To give some caveats to this whole system. / We're moving to a discord community server so that will handle some role stuff. / We need this system to work with"** (the message ends there — asked him to finish it). DECIDED so far: (a) wire pings INTO raid trains; a go-live LISTENER that adds every streamer seen live to a streamer list, from which a member opts into that streamer's role (the role made lazily on the first follow); the whole thing must fit a **Discord Community server** (onboarding prompts hand out roles) — → **22:4x, owner: "Yes that was the final part. Community and role prompts"** — the system must work WITH Discord's Community onboarding and its role prompts. Design `info/pings-remake-design.md` WRITTEN 22:5x — forks F-PR1/F-PR2/F-PR3 ALL DECIDED (a) by 22:52; **owner 22:5x "A" → DISPATCHED 22:56** to Opus, worktree `C:/lcw/bb-pings-remake`, branch `pings-remake` off `337d22a`, est. 250–350k ×2; `discord.py` 2.7.1 has `Guild.onboarding()` / `edit_onboarding()`, so the bot can keep a prompt in step (limits being verified against the API docs).

- 🔁 **ROLE MENUS → retire in favour of Discord's Community onboarding (owner, 2026-09-16 22:4x, verbatim: "Our role menus will probably retire to use discords to turn them off for now").** `rolemenu_mode` set **off** the same minute from the owner's dashboard session (hides `/rolemenu`; under TEST_MODE the un-post of any panel outside `#blackbloc-logs` is a `would_unpost` row, so nothing in `#roles` moves). The retirement itself is part of the pings-remake design (`info/pings-remake-design.md`): which menus become onboarding prompts, what the bot keeps in step, and what is simply deleted. Not built.

## 2026-09-16 — Guides: Mark every screenshot stale — the cutover's trigger for re-shooting every picture (v115, 19:15)

Owner, 15:5x, verbatim: *"we need to update all screen shots once shadow mode is off to not have that message and to not have the old channel"*. Every v111 capture shows the *in shadow* line and the old channel name, and neither a settings flip nor a rename is a deploy, so `release.json` could never mark them. Shipped (release `64b69ce`, merge `79fd644`): `guides.mark_all_stale` (marks every unmarked picture of the guild, returns the count — no log row of its own, so the route's `note()` is the one row, checklist 34), `POST /api/guides/stale/all` (staff + `guides_who_edits`, an optional reason, `web.guide.shots_stale` with `features: ["all"]` and the count — written even at 0, which tells "already done" from "never pressed"), and **Mark every screenshot stale…** on the hub's *Screenshots to re-shoot* block, behind a confirm with a reason box; the block is now drawn for staff whatever the count, because zero stale is exactly the state the cutover presses it in. Mock 170 → **171** routes; tests 5880 → **5889** both orders. Seen on the mock in a browser: the confirm, the count sentence, the pill, and the second press answering *"Every screenshot was already marked."* Cost **223k** Opus against 80–140k. Cutover row **P7** now names the button; the capture runbook §1 says when to press it. Sweep row **434**. Seven deviations under `### Mark-all-stale` in [`info/guides-design.md`](info/guides-design.md).

**The TODO item, moved whole:**

- 📸 **Re-shoot every guide screenshot at the cutover (owner, 2026-09-16 15:5x, verbatim: "we need to update all screen shots once shadow mode is off to not have that message and to not have the old channel").** All 16 v111 captures show *in shadow* and the old channel name; they cannot auto-stale (the modes and the rename are not a deploy). Cutover-plan row **P7** owns the when; this line owns the HOW: a staff **Mark every screenshot stale** move (`POST /api/guides/stale/all`, one loop over `guide_media`, one `guide.shots_stale` row, a button on the hub's staff line — small, main-loop or Opus) so the runbook's stale list becomes the whole job; until it exists, `UPDATE guide_media SET stale = 1` by hand on the volume.

## 2026-09-16 — MODMAIL DOORS: a member half of `/modmail`, a posted Open-a-ticket button, staff opening a ticket with a member (v114, 18:38)

**Owner asks, verbatim:** 16:1x *"is there a way for a user to do /modmail to start a mod mail? can we also have a channel where the modmail can be started with a ticket button like some bots have. do research on that and then get back to me"* → research ([`info/modmail-doors-research.md`](info/modmail-doors-research.md), Sonnet, 141k) → 16:3x *"let mods also be able to make a modmail with /modmail make it a button"* → *"basically for modmail, anyone can make it, if youre a staff when you do a /modmail you see more than just create and a modal with header and comment and stuff, you also see the other settings"*.

**What shipped (release `c279676`, merge `04de842`):** three doors onto the same ticket and the same card. `/modmail` is member-visible now (`/help` no longer marks it staff; description *"Open a ticket with the moderators, or run the inbox"*); the first row is the same for everybody — **Open a ticket** → a two-field modal (what it is about · what is happening) → the paragraph becomes the ticket's first inbound row through the DM path — or the line naming the ticket already open; staff see that row and then the inbox they had, plus **Open a ticket with…** (a `UserSelect`; the paragraph goes to the member as the first staff reply; the card reads *opened by staff · @who*). A posted **Open a ticket** message (`TicketButton`, a persistent item registered at `cog_load`) placed from `/modmail` ▸ **Ticket button…**, moved, taken down, re-posted by the reconciler if deleted by hand; every reply to a press ephemeral, so nobody in the channel learns who pressed. ⚠️ **A migration:** schema 37 → **38** — `modmail_tickets` gains `source` (`dm` for every old row) and `opened_by`; the design's §A had assumed a source column existed (it did not — `SOURCES` was the reply vocabulary). Keys 215 → **220** (`modmail_member_command` true, `modmail_panel_channel_id`, `modmail_panel_message_id` as TEXT — a snowflake does not survive a JavaScript number, and an `int` key sat falsely "changed" on every load, the third of that family, `modmail_panel_title`, `modmail_panel_text`); mock **19 pages / 170 routes**; tests 5833 → **5880** both orders. **The `deliver_dm` finding:** it returns a reason and raises nothing, so a ticket opened for a member with DMs shut opens, keeps the words, logs `modmail.dm_failed`, says so in the ticket, and the card now reads *the last reply did not reach them*. Fifteen deviations at the design's foot. `modmail-panel-design.md` §B's "no member half" struck and rewritten. Cost **508k** Opus against 180–260k.

**Measured at the landing:** gate green, `/health` ready, the boot log read; nothing pressed in Discord. Sweep rows **419–433** are the owner's; **419** (a non-staff account runs `/modmail`) and **431** (a member with DMs shut) decide whether this shipped.

**The TODO item, moved whole:**

- 🔎 **MODMAIL DOORS — research first (owner, 2026-09-16 16:1x, verbatim: "is there a way for a user to do /modmail to start a mod mail? can we also have a channel where the modmail can be started with a ticket button like some bots have. do research on that and then get back to me").** Today the ONLY door is a DM to the bot (`/modmail` is staff-only). Research DONE 16:30 → `info/modmail-doors-research.md` (Sonnet, ~26 min); proposal put to the owner 16:3x → **owner 16:3x, verbatim "let mods also be able to make a modmail with /modmail make it a button"** = go, plus a third door (staff open a ticket WITH a member from the `/modmail` root). Design `info/modmail-doors-design.md` WRITTEN 16:35; **dispatch QUEUED behind the Posts merge** (shared files), est. 180–260k. Research covered: how Ticket Tool / Tickets / ModMail-style bots do the button panel (button → modal → private thread or channel, categories, one open ticket per member, close + transcript), what Discord itself offers, and how it maps onto our channel/thread modes and the sticky card → a proposal to the owner, then a design doc if he says go.

## 2026-09-16 — POSTS: the welcome and rules message, written on the website, rehearsed in #blackbloc-logs, posted and edited in place by the bot (v113, 17:36)

**Owner asks, verbatim:** 13:5x *"in the welcome channel there is a post there by Carl-bot that xontain the rules and the welcome message, We will be taking over that task. on the site we need a text box and preview window so the staff can update the rules on the website and have the bot post them"*; 15:4x *"lets have all the test work go to blackbloc-logs until we're ready to go live, another shadow mode"*.

**What shipped (release `4d60f68`; merges `440c0c6` base + `34b86a5` shadow):** schema 35 → **37** (`posts`: slug, title, channel, body, plain/embed, pin, `message_id`, `shadow_message_id`, `posted_hash`, `seed_hash`); `black_bloc/posts.py` (save / publish / take down / reset / reconcile, one `render_message`, caps 2000 plain / 4096 embed refused in words with the count, an over-long title REFUSED not clipped, `allowed_mentions` = only mentionable roles the body names); `posts_seed.json` = **Carl's `#welcome` text verbatim** from the 2026-08-26 archive, aimed at `#welcome`, never posted by the seed; `api/tools/posts.py` (8 routes); `cogs/community/posts.py` + the `/posts` staff panel (30th command, hidden when `off`); `site/public/posts.html` + `page-posts.js` + **`discordmd.js`** (the site's first markdown renderer — HTML escaped first, links never anchors, mentions by name, `#` headers only in plain style; its own Node test in the deploy gate and CI); **`posts_mode` off / shadow / on, default shadow** — shadow sends and edits the REAL message in the guard's channel (`#blackbloc-logs`) whatever the post names, `on` posts to the post's channel and removes the shadow copy, `off` refuses in the module (closing a hole the base build had); keys 212 → **215** (`posts_mode`, `posts_panel_minutes`, `posts_log_level`; the `/settings` group select is now at **25 namespaces exactly** — the cap); mock **19 pages / 168 routes**; tests 5703 → **5833** in both orders. Deviations: 10 (base) + 14 (shadow) at the design's foot — notably `posted_where` instead of a second hash, and the shadow copy hunted across the guard's, the test and the log channels because the cutover lifts the guard before the mode flips. Cost **569k + 367k** Opus (the base over its 300–420k band). **Refused correctly:** the base builder declined the shadow change I sent mid-flight; it became its own brief.

**Measured at the landing:** gate green, `/health` ready, the boot log read for `post.seeded`; nothing pressed in Discord. Cutover row 11 rewritten: the rehearsal happens BEFORE `TEST_MODE` is lifted, the flip to `on` is the go-live, and Carl's message `1285806434050768927` is the owner's to delete. Sweep rows **390–418** are the owner's. Design: [`info/posts-design.md`](info/posts-design.md).

**The TODO item, moved whole:**

- 🔨 **WELCOME + RULES POST TAKEOVER (owner, 2026-09-16 13:5x, verbatim: "in the welcome channel there is a post there by Carl-bot that xontain the rules and the welcome message, We will be taking over that task. on the site we need a text box and preview window so the staff can update the rules on the website and have the bot post them").** Status: design `info/posts-design.md` WRITTEN 15:40 (forks F-P1–F-P3 decided (a) under the autonomy rule; the seed is Carl's text verbatim from the archive) → owner 15:4x: "lets have all the test work go to blackbloc-logs until we're ready to go live, another shadow mode" → `posts_mode` off/shadow/on, default shadow, shadow posts the real message into `#blackbloc-logs` (clarified to the agent mid-flight, design §C7/§C9 edited per checklist 35) → Opus build LANDED and MERGED `440c0c6` 16:33 (569k; 5810 tests; 19 pages / 168 routes; ten deviations at the doc's foot; the builder REFUSED the shadow change mid-flight — right call) → shadow follow-up DISPATCHED 16:35 as its own brief (`C:/lcw/bb-posts-shadow`) → review, merge, deploy v113, docs ritual. Shape: staff-edited posts (welcome, rules) with a text box + live Discord-markdown preview on the site, the bot posting ONE message per post and EDITING it in place afterwards; TEST_MODE keeps every post inside `#blackbloc-logs` until the cutover.

## 2026-09-16 — …and then `#blackbloc-logs`: the underscore came out (13:1x)

Owner, verbatim: *"Remove the _ blackbloc-logs"* — minutes after the `#black_bloc-logs` rename below. Renamed again through the bot's token, read back as **`blackbloc-logs`**; the same sweep replaced the interim name in the same 32 files (118 occurrences); the mock's single `TEST_CHANNEL_NAME` constant changed in one place, which is what it was made for. `DONE.md`, `deploys.log` and `archive/` keep both older names as history. The id is unchanged; no deploy.

## 2026-09-16 — The test channel is `#black_bloc-logs` (was `#mute-me-bot-test-spam`), renamed on Discord and swept out of every living doc (13:1x)

Owner, verbatim: *"Let's change the name of the mute me spam channel now / Let's change it to Black_bloc-logs / Also make sure we do a deep scan and update that channel name everywhere in our internal / Maybe also get a channel name variable or something if we've hard coded it more than once?"* Done: the channel was renamed through the bot's own token (`PATCH /channels/{id}`, audit reason on it) and read back as **`black_bloc-logs`** — Discord lowercases the leading B; the id (`TEST_CHANNEL_ID`, `log_channel_id`, …) did not change, so **nothing in the bot moved and no deploy was needed**. **Measured before the sweep:** `black_bloc/` and `site/public/` carried the name **zero** times (the bot renders the mention from the id — nothing to variable-ise there); the mock had it **four** times → now ONE `TEST_CHANNEL_NAME` constant in `site/mock/server.mjs`; the tests **15** times (fixtures mirroring the mock, now the new name); the living docs **121** occurrences over 32 files, all replaced (`sweeps.md` alone 56). **Deliberately untouched, as history:** `DONE.md` (19), `deploys.log`, `archive/` (9), the `mock-direction-a` artboard. `node site/mock/check.mjs` and the six touched test files green after; `ruff` clean. The 2026-08-26 plan had said `#black-block-logs` — the owner's spelling today is the one that stands.

## 2026-09-16 — Guides: the first screenshot population, 16 of 17 root cards shot from the owner's browser (10:06)

Owner: *"a, also im ready to do self capture"* (raise the self-test purge for the run) → *"you open discord and run the captures ill facilitate from here"* → *"we need to make sure no chats that arent with the bot or channels not whats trying to be shown off are visible. wouldn't want to leak mod stuff"* → *"Clicked"* (the dashboard sign-in, the one press only the owner can make; the first run stopped there correctly, `ee63c30`). An Opus session in Claude in Chrome then ran [`access/guides-capture.md`](access/guides-capture.md) end to end: `selftest_purge_minutes` **1 → 30 → 1** (read back from `/api/settings`), self-test run **#28** from the Health page (109 ok, 24 cards), each root card shot as the card's OWN painted box with `zoom` + `save_to_disk` (no Pillow), every file looked at before upload and two deleted for catching a neighbour's line, uploaded through **Replace screenshot…** — **16 guides** at v111 (`media/1`–`16`), `birthday-set` **withheld** because the card itself prints five members' next birthdays. Runbook corrected in **`7fbb3e2`** (drilled end to end; panels are components-v2 containers not embeds; Discord will not paginate for a script; the crop recipe; `file_upload` needs a file under the repo — `scripts/scan/shots/`, gitignored). Found outside guides: the Settings page's false "1 change pending" on `chat_memory_model` (on `TODO.md`). Cost: **139k + (resumed) Opus** for the two runs. Nothing was pressed in Discord.

## 2026-09-16 — GUIDES: one web page per goal, staff-editable, real captures marked stale per release, `/help` guide links (v111, 09:07)

**Owner ask, 2026-09-15 21:2x, verbatim:** *"we need guides on how to use each feature. I dont want just readmes, and i dont want more menus, maybe we augment help a bit. What I think we really need is webpages with guides/photos/dynamic information about how to achieve something"* → *"dont build yet jusy mock"* → four decisions one at a time (server-level access; real captures re-shot when the feature changed; a small guide link per `/help` line; layout A) → *"write the design doc … every part of it is editable by the staff. wording more than screen shots. As little fluff text as possible, just very empirical almost ikea like steps"* → *"You can screenshot discord in browser mode no? If not make mocks"* → forks F-G1 **A** (no Discord editing door), F-G2 **a** (Something's off files a request), F-G3 **a** (members see member guides only) → 2026-09-16 06:5x *"do it all"*.

**What shipped (release `67aee7e`, merges `cad1abc` G1 core + `307b759` G2 pages):** schema 34 → **35** (`guides`, `guide_steps`, `guide_faults`, `guide_facts`, `guide_media`, `guide_releases`); `black_bloc/guides.py` (rows, the warn-only IKEA linter, nine probes, `resolve_facts`, `FEATURE_PATHS`, `reconcile_releases`, `links_for`, the seed loader) and `black_bloc/guides_seed.json` (**17** guides written by the conductor off `access/sweeps.md`, seeded once per guild, `seed_do`/`seed_expect` refreshed on later boots, never a staff edit overwritten); `api/tools/guides.py` (hub, one guide with live facts, whole-guide `PUT`, new/delete/reset, base64 media upload ≤ 2 MB / 1600 px read from the header without Pillow, member-gated media with `private, max-age=86400` + ETag, `/stale`, `/confirmed`) behind a new `writes.member_read_dependency` so a guide read never spends a member's ten writes a minute; `/help` gains a masked `[guide](url)` clause on the ten member commands and one **All the guides** link button (longest page 1843 of 1900); six keys `guides_mode` / `guides_who_edits` / `guides_help_links` / `guides_show_facts` / `guides_fault_files_request` / `guides_log_level` (registry 206 → **212**, groups 23 → **24**); `site/public/guides.html` + `assets/page-guides.js` (the hub with a Right-now strip and filter chips, the guide with steps/pictures/EXPECT/faults/rail, the in-place editor with the docked save bar, Put the original back, Replace screenshot…, Publish/Unpublish, Reset, New guide, the two foot buttons); the rail paints **Requests AND Guides** for a non-staff member; Ctrl K lists guides; `scripts/deploy.ps1` writes `site/public/assets/release.json` (`{release, commit, changed_features}` off `FEATURE_PATHS`) so the boot marks older shots of a changed feature **stale**; `scripts/backup_db.ps1` pulls `/data/guides/` beside the snapshot; `docs/access/guides-capture.md` (the session's capture runbook — 🔴 never drilled). Mock **18 pages / 160 routes**; tests 5588 → **5703** (+115), green in both orders under a clean environment.

**Measured at the landing:** gate `5703 passed`, `check: ok - 18 pages, 160 routes, 14 core settings`; boot `database ready` 16:07:02Z, `synced 29`, `logged in`, selftest **109 ok, 0 failed**; the live action log carries `guide.seeded count=17` and `guide.shots_stale release=v111 features=['core','guides'] count=0`; `/api/guides/stale` → `count: 0`; `/health` ready 09:07. Costs: G1 **478k** Opus (est. 200–280k), G2 **469k** Opus (est. 220–320k) — both over their bands, both multi-layer, as the checklist's table predicts.

**The gate refused THREE times before it passed, none of them the code:** (1) my own `deploy-v111.log` sat untracked in the tree (the log now goes to the scratchpad); (2) nine "no key" tests failed because this session's shell exports the real `.env` names and the deploy's child process inherits them; (3) one more of the same family read `DEV_GUILD_ID`. Fixed by clearing every bot-shaped name in the deploy process (`gotchas.md`). Each refusal left a `Release v111: release.json` commit behind that had to be reset — TODO follow-up (1).

**Design and decisions:** [`info/guides-design.md`](info/guides-design.md) (A–G, the G1 and G2 `## Deviations` feet — 14 + 13 departures, the ones that matter: the unique index is per audience because the seed has a member and a staff guide for `/event`; `/help` links member guides only; uploads are base64 in JSON because the site refuses non-JSON writes; seeding runs on the loop's first tick; Pillow is not a dependency; the hub strip reads `GET /api/guides` because `/api/status` is staff-only). The mock the owner reacted to: https://claude.ai/artifact/C6MGnYLSdSyDHL42y729YA. Review links: https://blackbloc.heygabi.ai/guides.html · https://blackbloc.heygabi.ai/guides.html#golive-announce · `/help` in `#mute-me-bot-test-spam`. Sweep rows **360–389** are the owner's; **388–389** wait on a deploy that touches a feature's files and on the first capture session. **KI-27** records the F-G1 waiver.

**The TODO item, moved whole:**

- 📖 **GUIDES — web pages per goal, with screenshots and live values (owner, 2026-09-15 21:2x, verbatim: "we need guides on how to use each feature. I dont want just readmes, and i dont want more menus, maybe we augment help a bit. What I think we really need is webpages with guides/photos/dynamic information about how to achieve something"; then "dont build yet jusy mock").** Status: **MOCK ONLY, nothing built** — design canvas https://claude.ai/artifact/C6MGnYLSdSyDHL42y729YA (hub, one guide page for go-live, phone view, augmented `/help`, one low-fi alternate). Shape mocked: a `Guides` entry in the site nav; one page per GOAL not per command; steps in the panels' own button words (source = `access/sweeps.md` rows); a screenshot per step; a **Right now** card read from the bot (feature mode, channel, cooldown); the settings keys that change it; an "If it did not post" table; a "Something's off" foot that files a `/request`. `/help` keeps its list and gains a guide link per line + one link button (no new menu). Open owner questions, one at a time: ~~Q1 public pages vs staff-only~~ **DECIDED 2026-09-15 21:3x, owner verbatim "lets make guides only server level access"** — read as: Discord sign-in, any member of the server, nobody outside it (not public, not staff-only); ~~Q2 real captured screenshots vs drawn panels~~ **DECIDED 2026-09-15, owner verbatim "real captures, re-shot each release if something about that feature changes"** — so a capture step keyed per feature, re-run only when that feature's files changed since the last shoot; **refined 21:5x, owner: "You can screenshot discord in browser mode no? If not make mocks" → the capture is a Claude-in-Chrome session over the self-test's posted cards, mocks only for unreachable screens (design §C4);** ~~Q3 `/help` link-per-line or button only~~ **DECIDED 2026-09-15, owner verbatim "small guide link"** — a guide link on every command line plus the one "All the guides" button, the list otherwise unchanged; ~~Q4 layout A vs B~~ **DECIDED 2026-09-15, owner verbatim "i like A"** — a screenshot under each step; the sticky-picture alternate is dropped from the canvas. **All four answered; `info/guides-design.md` WRITTEN 2026-09-15 21:48 (owner 21:5x: "write the design doc … every part of it is editable by the staff. wording more than screen shots … ikea like steps") — NOT dispatched.** **F-G1 DECIDED "A"** (no Discord editing door), **F-G2 DECIDED "a"** (files a request), **F-G3 DECIDED "a"** (member guides only, 2026-09-16 06:53). Nothing waits on the owner. NEXT, on the owner's word: the conductor writes the seed copy (§C11, 17 guides off `sweeps.md` in the IKEA voice), then dispatch G1 core → G2 pages (Opus, 200–280k + 220–320k). Design doc to write once decided: `info/guides-design.md`. Sources for the copy already exist: `access/sweeps.md` ("Do this / Expect" per feature), `settings_store.KEY_HELP`, `logkinds.FEATURE_PAGES`.

## 2026-09-11 — Docs-pass findings (a)–(h): every finding the "Update all docs" landing raised is closed (last one 11:39, `f4b17e5`, no deploy)

Moved WHOLE from `TODO.md` at 11:50. The 09:20 docs pass (entry below) surfaced eight findings; two needed the
owner and were asked ONE AT A TIME, six were engineering. In landing order: **(h)** closed by v110 10:14
(`event.room_forgotten` fired for events 1–3 on boot); **(a)** owner 10:33 *"Restore it"* → `cb612da` 10:45,
§B/§C/§D/§F/§I/§J of `pings-panel-design.md` back verbatim from `8426b1a^` after verifying all 21 control
labels still exist in `cogs/content/pings.py` / `pings.py`, §A/§E/§G/§H archived, `OWNER_GUIDE.md` gained its
missing `/pings` row and `feature-list.md` F14 its fix; **(b)** owner 10:50 *"A discord is fine"* → KI-25
`WAIVED` `b401e61`, phase-8 decision 3 bannered; **(c)** KI-26 `WATCHING` + **(f)** BOMs stripped from six
phase docs + **(g)** `theme.js` comment → `7fd7c35` 10:55 (measuring `deploys.log` corrected the hang list to
v94/v97/v98/v99/v100 — the first draft had said v97–v100 + v103); **(d)** review-checklist item 35 →
`0f0282e` 11:00; **(e)** the inline refs → `f4b17e5` 11:39, Opus agent 178k against a 100–150k estimate.

**(e) in detail, because the number in the finding was wrong and the tool's refusal rate is the story:** the
docs pass had counted 883 inline `` `path:N` `` refs in 413 rows; the agent measured **542 in 447 rows** (606
backticked `:N` in rows minus 7 clock times, 43 extra column-1 keys, 14 in frozen `(GONE)` rows) and did not
chase the 883. The gitignored `scripts/scan/rekey_code_notes.py` gained a pass over column 2 (`INLINE_RE`,
`external()`, `inline_path()`, `resolve_inline()`, `--no-inline`) that reuses the column-1 machinery and can
only see offsets past the row's first `|`, so column 1 is structurally untouched. Result: **123 moved, 11
already right, 367 unresolved and left exactly as they were, 26 gone (number kept, no `(GONE)` written in
prose), 15 external (discord.py `app_commands/tree.py`)**. Why 367: the agent's first drafts moved 190 then
110 and hand-sampling killed both (`db.py:387` "PRAGMA foreign_keys=ON" was landing on an unrelated
`REFERENCES … ON DELETE CASCADE` line on word overlap); measured properly, each ref had a **median of 4
distinct verified targets depending on which base commit you assume**, and only 61 of 520 were unanimous.
The accepted rule: the note must name a construct the target file actually defines, the anchor must still
carry it at the chosen base, the mapping must be verified, and the answer must resolve to itself (an
oscillation is refused — which is also what makes the second `--write` a no-op; idempotence verified, third
dry run `moved: 0`). Conductor spot-check: `cogs/content/golive.py:636` = `cog_unload`,
`cogs/community/role_menus.py:680` = `post_panel`, `rolemenu_panels.py:171` = `install` — all as the notes
say. BOM intact, 0 CRLF, 6435 lines and 3474 `|` rows before and after, 114/114 in the diff, only `:N`
digits changed (asserted at write time). Two column-1 keys also moved in the same run (`theme.js:86→87`
after `7fd7c35`, `settings_store.py:1859→2027`). **Residue filed on `TODO.md`:** 32 prose refs outside
tables, 43 second keys in multi-key cells, all `.css` refs, and one doubted move (`server.mjs:2879→4164`,
should be ~4387 — and that note's claim is stale too). NOT verified: no note's content was checked for
truth; ~112 of the 123 moves rest on the tool's rule, not on eyes; nothing met Discord or a browser.

The original item, whole:

- 🔧 **Docs-pass findings still open (from the 2026-09-11 "Update all docs" landing, `DONE.md` same date) — owner questions go ONE AT A TIME, after the event-rooms questions above.** ⏳ OWNER: (a) ~~🔴 `docs/info/pings-panel-design.md` lost its design body at `8426b1a` (408 → 140 lines; the foot still cites §C/§E/§F/§H/§J) — restore it or archive the husk~~ ✅ **DONE 2026-09-11 10:45 (owner 10:33: "Restore it")** — §B/§C/§D/§F/§I/§J restored verbatim (21 control labels re-checked against the code), §A/§E/§G/§H archived to `archive/pings-panel-design-prebuild-2026-09-03.md`; the check also found `OWNER_GUIDE.md` had NO `/pings` row (added) and `feature-list.md` F14 still said `/pingroles setup` (fixed); (b) ~~the phase-8 owner decision 3 (2026-08-26: Google SSO for the owner + a `user_identities` table) was never wired — still wanted, or drop it?~~ ✅ **DROPPED 2026-09-11 10:50 (owner: "A discord is fine")** — KI-25 `WAIVED`, phase-8 doc banner; **both owner questions answered**; ENGINEERING (no owner needed): (c) ~~`deploy.ps1` has hung at xdist five times (v97–v100, v103-attempt-1) with every worker idle — needs a `KNOWN_ISSUES.md` WATCHING entry~~ ✅ **KI-26 `WATCHING` filed 10:55** (the five were v94/v97/v98/v99/v100 off `deploys.log`, not v103; cause still open; threshold: a hang on a foreground `*> file` run, or 10 total); (d) DECIDED bullets that outlived their reversal — fork I-A2 and the automod/chat/birthdays/role-menus "does not vanish when off" bullets were reversed at v78 with the reversal recorded only in a commit message (slices D/F annotated them) ✅ **the rule is checklist item 35, 11:00** (`review-checklist.md`; `CLAUDE.md` count 34 → 35); (e) ~~883 inline `` `path:N` `` cross-references inside `code-notes.md` note prose (413 rows) were not re-keyed — `scripts/scan/rekey_code_notes.py` can, one Sonnet sweep~~ ✅ **RE-KEYED 11:39, `f4b17e5`** (Opus, 178k — the tool gained an inline pass; the 883/413 count did not reproduce: 542 refs in 447 rows; 123 moved, 367 left because no base commit gave a verified answer, 26 gone, 15 discord.py; 32 prose refs outside tables + 43 second keys in multi-key rows remain — filed); (f) ~~six phase docs (8, 8b, 9, 10, 11, 12) carry a UTF-8 BOM the others do not — strip in one commit~~ ✅ **stripped 10:55**; (g) ~~`site/public/assets/theme.js:50` cites `docs/info/estate-themes.md`, which exists only in catalog-platform~~ ✅ **comment now says catalog-platform's, 10:55** (ships with the next deploy; comment-only); (h) ~~a denied event's row keeps its `review_channel_id` after the room is gone (events 1, 2, 3 on the live DB, 09:10) and the sweep is silent when the room is already missing — clear the id and log once~~ **CLOSED by v110 10:14** — `event.room_forgotten` fired for events 1–3 on the v110 boot (`DONE.md` 2026-09-11 Event rooms). DONE at the landing: `.env.example` gained `OPERATOR_READ_TOKEN` + `SESSION_COOKIE_SAMESITE` (23 names); every live `/settings set-value` mention (OWNER_GUIDE 119–120, sweeps 342/348, applications-panel-design 394/438) now names the `/settings` panel path; `requests.py` refusals → v109.

## 2026-09-11 — Event rooms: the event's posts live in its OWN room, staff get a Delete this room button, test rooms go 5 minutes after the end (v110, 10:14)

Moved WHOLE from `TODO.md` at 10:20. Owner ask 09:12, three questions asked one at a time — **Q1 A** (the
posts go to the event's OWN room, not the announce channel), **Q2 B** (5 minutes after the end is TEST MODE
ONLY — `events_test_retention_minutes` while the guard is on; live keeps `events_channel_retention_days`),
**Q3 B** (Delete = delete + settle: an open event is cancelled with a DM'd reason, done/denied left alone).
Design `docs/info/events-rooms-design.md` 09:50 (`bd0b31d`); Opus build in `C:/lcw/bb-rooms`, branch
`event-rooms`, dispatched 09:55, landed 10:08 at **399k** against a 250–350k estimate; merged `--no-ff`
`9c6201d`; gate 5593 passed + `check.mjs` 17 pages / 151 routes; **v110 live 10:14**, boot `database ready`
+ `synced 29` 17:14Z, `/health` ready, `/api/settings` 206 keys with defaults room / staff / blank / true.

**Root cause of "the event stuff posts in the spam channel":** `make_review_channel` never called
`guard.own_channel` (polls, tempvoice, modmail and raidtrain all do), so `card_channel` redirected the
card and `post_to_announce` only ever aimed at the announce channel. Fixed by owning the room at creation
and re-owning on every reconcile pass (the owned set is in memory and lost on restart).

**What shipped:** `black_bloc/events.py` +351 (`post_to_room`, `post_event` fan-out by
`events_posts_where`, `delete_room(bot, guild, row, *, by, note, via)` — cancels first with reason
`room_deleted` so `on_guild_channel_delete` does not double-cancel, a guard refusal logs
`event.would_delete_channel`; `own_room` / `disown_room` / `room_of`, `may_delete_room`, `ROOM_*` strings,
`CANCEL_WHY["room_deleted"]`); `cogs/community/events.py` +278 (`DELETE_ROOM`, `ask_to_delete_room`,
`RoomDeleteModal`, `decision_context(..., staff=True)`, reconcile re-own / forget, a `/event` ▸ Settings ▸
**Rooms…** page for the four keys); `DECISION_TEMPLATE` gains `delete_room`; `logkinds.py`
(`event.{announce,go_live,ended,cancelled,denied}_room` + `would_*_room` + `*_room_failed`,
`event.room_forgotten`, `event.room_notice_failed`, `event.room_delete_failed`,
`web.event.channel_deleted`); site `POST /api/events/{id}/room/delete` with `{note}`, `Refused(409,
"no_room" / "room_kept")`, a **Remove its room** control on `events.html`; four keys 202 → **206**
(`events_posts_where` room · `events_room_delete_who` staff · `events_approver_role_id` blank →
staff · `events_room_notice` true); schema stays 34; +47 tests to **5593**; sweep rows **351–359**.

**Deviations the agent recorded (11, all in the design doc):** the spec's `event_lock` around
`delete_room` would have deadlocked (`cancel_event` takes the same non-reentrant lock) — built without it,
the status change is still atomic inside `cancel_event`; `room_forgotten` is logged by the SWEEP only, an
open row keeps its id so the two-consecutive-misses rule (checklist 32) still decides cancels; the four
keys got their own **Rooms…** page (Discord's five-row cap); cancelled / denied room lines are skipped for
the four "room already missing" reasons; `VIA_SITE` in the spec is `VIA_WEBSITE`; fan-out tests live
beside the cog's fakes. Finding (h) of the docs pass (dead `review_channel_id` on events 1–3) closed by
this landing — `room_forgotten` fired for all three on the v110 boot, **twice each** (`on_ready` vs the
loop's first tick, filed on `TODO.md`). Not verified: nothing here has met Discord; `events.html` /
`settings.html` not opened in a browser.

The original item, whole:

- 🆕 **Event rooms: a staff Delete button, deletion 5 minutes after the end, and the event's posts in its own channel (owner, 2026-09-11 09:12, verbatim: "In the channels how about we have the bot post an additional message for deleting the channel that only staff can press. I thought we had decided a newly generated room would go away after 5 minutes of creation. We can instead use the bot button I just mentioned to delete it and then have it 5 minutes after event ends. Also if we're making channels now don't have the event stuff post in the spam channel have the event stuff post in the actual channel like a real event would.").** Context measured 09:10: event 4 (`Cool kids club`, approved 08:30, 09:30–11:30) keeps `approved-sky-cool-kids-club` until it ends because the sweep (`events.py:_sweep_finished`, every 5 min) only removes rooms of done/denied/called-off events — `events_test_retention_minutes` (5) after they settle in test mode, `events_channel_retention_days` (7) live; `events_announce_channel_id` is the test-spam channel by default, which is why "event stuff" lands there. Three parts: (1) the bot posts one more message in every review room with a **Delete this room** button that only staff can press (staff/approver gate, confirm step, logs `event.channel_deleted` with the presser) — **DECIDED 09:34 (owner answer to question 3 of 3: **B**): delete + settle** — pressing it also cancels an open event with a DM'd reason; done/denied events are left as they are. All three answered; design written `docs/info/events-rooms-design.md` 09:50 (four keys 202 → 206, schema stays 34, no retention change); **BUILT 2026-09-11 10:08 on branch `event-rooms` (worktree `C:/lcw/bb-rooms`, off `bd0b31d`) — pushed, ⚠️ NOT merged, NOT deployed, and nothing in it has met Discord.** Four commits: `3d7e200` parts 1+2 (own the room, `post_to_room`/`post_event` fan-out, the **Delete this room** button + `delete_room`, `event.room_forgotten`), `7a14e88` the website (`POST /api/events/{id}/room/delete`, **Remove its room**, mock routes 150 → 151), then the docs. Keys **202 → 206**, schema **34**, tests **5546 → 5593** (`-n auto`, 28 s), `ruff check .` clean, `node site/mock/check.mjs` green (*17 pages, 151 routes, 14 core settings*). Eleven deviations are in the design's `## Deviations` foot — the load-bearing one: `delete_room` cannot hold `event_lock` (`cancel_event` takes the same non-reentrant lock, so the design's ordering deadlocks). Owner sweeps **351–359**. NEXT: merge `--no-ff`, gate, deploy, re-key `code-notes.md`, remove the worktree + branch; (2) the automatic deletion becomes **5 minutes after the event ends** (staff use the button to go earlier) — DECIDED 09:31 (owner answer to question 2 of 3: **B**): TEST MODE ONLY — `events_test_retention_minutes` stays the after-end figure while `bot.guard` is on; live events keep `events_channel_retention_days` (7) as their own key; (3) the event's announce / go-live / ended posts go to "the actual channel like a real event would" — **DECIDED 09:14 (owner: "A"): the event's OWN ROOM** — announce card, go-live ping and the ended post land in the review room itself, not the announce channel; test mode untouched. Design after the answers; Opus build; every default a settings key (checklist 33).

## 2026-09-11 — Update all docs: every tracked doc re-verified against v108 by six parallel agents, code-notes re-keyed whole (landed 09:20, no deploy — plus the `requests.py` refusal fix it found, v109)

Moved WHOLE from `TODO.md` at 09:20. Six Opus agents in worktrees `C:/lcw/bb-docs-a…f`, branches
`docs-a…f` off `1d090e5`, disjoint slices, merged `--no-ff` into main in landing order — A `03ae7bc`
(232k; top level + `access/`, 15 files), D `e853fb4` (306k; panel designs 1, 12 files), B `6cf4da7`
(267k; `info/` reference docs, 18 files), C `3224783` (297k; phase designs 1–19, 20 files), F `c2e4e7a`
(355k; panel designs 2, 16 files), E `70df888` (277k; `code-notes.md` re-keyed: 1895 line keys checked,
1334 moved, 50 marked `(GONE)`, 488 of 522 name-keyed rows converted to line+name; measured anchor
quality 94 → 1256 of 2330 keys on a line that names what the row names; held-out accuracy 83% for rows
with no quotable anchor). Every header now carries `Last verified: 2026-09-11 HH:MM` with what was
measured and what was NOT (nothing in this pass met Discord or a browser; `node site/mock/check.mjs`
was not run end to end — counts come from `site/mock/contract.json`). Conductor-side fixes on main at
the merges: `CLAUDE.md` checklist count 33 → 34 (`328eff2`), sweeps row 252 self-test purge 5 → 1 minute,
TODO F4 names its retired commands, secret-rotation count 22 → **21** (measured off `.env.example`),
Where-picker sweep heading 329–335 → 329–350, raid-train name key struck from the When follow-ups
(shipped v104) (`84a183d`), the re-key debt line cleared. Worst rot found (all fixed on the branches):
`hosting.md` said `fly.toml` has no `[http_service]` and "none of it has been deployed"; `deploy.md`,
`RECOVERY.md` ("private"), `site.md` ("nothing has been run") stated falsehoods; `feature-list.md`
had six rows "not merged" for work live a week; `info/README.md` had 14 rows landing had overtaken;
`where-picker-design.md`'s own top header still said NOT merged for all four Where builds; 13 phase
docs said `LOCAL ONLY`/`DESIGN`; `settings-panel-design.md` said both builds undeployed (v83/v84);
`requests-states-design.md` named a key that never existed (`request_dms_on_decision`).

**Corrections to earlier entries (this file is append-only, so they live here):** the 2026-09-03
Phase 17 entry and `deploys.log` line 54 say "9 `chat_memory_*` keys" — the landing added **8**;
`chat_memory_log_level` was in the design table and never built (memory logs under `chat_log_level`).
Measured 08:51 off `settings_store.KEY_TYPES`.

**Findings that outgrew a docs fix** (the owner is asked ONE AT A TIME; open ones stay on `TODO.md`):
(1) 🔴 `docs/info/pings-panel-design.md` lost its design body at `8426b1a` (408 → 140 lines; the foot
still cites §C/§E/§F/§H/§J) — restore from `git show 8426b1a^:docs/info/pings-panel-design.md` or
archive; (2) DECIDED bullets outlive their reversal — fork I-A2 and the automod/chat/birthdays/
role-menus "does not vanish when off" bullets were reversed at v78 with the reversal only in a commit
message; (3) `.env.example` omits `OPERATOR_READ_TOKEN` and `SESSION_COOKIE_SAMESITE`, which
`config.py` reads; (4) `deploy.ps1` has hung at xdist five times (v97–v100, v103) with no
`KNOWN_ISSUES.md` entry — filed in `gotchas.md` with the retry, cause unestablished; (5) the phase-8
owner decision 3 (2026-08-26) — Google SSO for the owner + a `user_identities` table — was never wired
and nothing tracks it; (6) six phase docs (8, 8b, 9, 10, 11, 12) carry a UTF-8 BOM; (7) 883 inline
`` `path:N` `` cross-references inside note prose (413 rows of `code-notes.md`) were not re-keyed —
the tool can, one more sweep; (8) `site/public/assets/theme.js:50` cites `docs/info/estate-themes.md`,
which exists only in catalog-platform; (9) `OWNER_GUIDE.md:120` still tells the reader to use
`/settings set-value` (retired v84). **Fixed in code, not just docs:** `black_bloc/requests.py` had
three refusal sentences still sending people to `/request ready` / `/request accept` / `/request set`
(gone since 2026-09-03 — a member following them got Discord's "unknown command"); they now name the
card buttons (`00b0d45`, ships as **v109**). Not verified: nothing in this pass met Discord or a browser.

The original item, whole:

- 🆕 **Update all docs (owner, 2026-09-11 08:22, verbatim: "Update all docs").** A docs-wide staleness pass, the 2026-08-31 audit (`d87ee84`) done again against the v108 state. Ground truth measured 08:25 on `main` `f3ae743` (v108 live 00:37): schema **34**, registry keys **202**, `bot.py:COGS` **19**, **29** top-level slash commands and 29 leaves (no groups left — `about apply automod ban birthday chat event golive help honeypot kick memory mod modmail ping pings poll purge raidtrain reply request rolemenu settings timeout unban untimeout voice warn youtube`), tests **5546**, mock *17 pages / 150 routes / 14 core settings*, sweep rows 1–**350**, KI-1…**KI-24**, `deploys.log` 107 lines. Of 84 tracked docs, headers older than 2026-09-06 number ~60 (the phase 1–19 designs say 2026-08-26/27/09-02; `docs/README.md` still says schema 21 / 2714 tests / 37 commands / 15 cogs; `access/README.md` 08-31; `feature-list.md` 08-26; `gotchas.md` 08-26; `setup.md` 08-26). Plan: five Opus agents in their own worktrees, disjoint file slices — (A) top level + `access/`, (B) `info/` reference docs, (C) phase designs, (D) panel/feature designs, (E) `code-notes.md` line-diff re-key of the five listed debt ranges — each verifying every stated fact against the repo or the live system, refreshing headers with what was and was NOT checked, retiring nothing without a dated banner; Fable merges and reports. Dispatched 08:26 as SIX Opus agents (D split into D = panel designs 1 and F = panel designs 2), each in `C:/lcw/bb-docs-<letter>` on branch `docs-<letter>` off `1d090e5`. Landing (merges `--no-ff` into main, in order): A `03ae7bc` (232k; 15 files), D `e853fb4` (306k; 12 files), B `6cf4da7` (267k; 18 files); C, F, E in flight at 08:50. Agent findings that outgrew a docs fix are collected at the merge and go to the owner ONE AT A TIME (pings-panel-design.md lost its design body at `8426b1a`; DECIDED bullets outliving their reversal; `.env.example` omits `OPERATOR_READ_TOKEN` / `SESSION_COOKIE_SAMESITE`; `deploy.ps1` xdist hang ×5 with no KI entry; `theme.js:50` cites a doc that exists only in catalog-platform). Small conductor-side fixes made on main at the merge: `CLAUDE.md` checklist count 33 → 34, sweeps row 252 purge minutes 5 → 1, F4 row above names its retired commands, the 22 → 21 secret-name count.

## 2026-09-11 — Events: a SHORTHAND becomes a link (bare hosts, alias table) and the link is tried once before it is kept (v108, 00:37)

Moved whole from `TODO.md` 2026-09-11 00:38, in the session the work landed.

- 🆕 **Events: a SHORTHAND becomes a link, and the link is tried first (owner, 2026-09-10 23:5x, verbatim: "Can we do some smart work to make it a link / Like twitch.tv/skyaiva or ttv/skyaiva or yt skyaiva / We go and make those into links / Maybe even curl them first?").** Follow-up 2 only knows `https://`, `http://` and `www.`. Designed 2026-09-11 00:01 as `## Follow-up 4` on `info/where-picker-design.md`: (A) a bare host (`twitch.tv/skyaiva`) is a link at render time in `where_link`, so old rows render too; an alias + handle (`ttv/skyaiva`, `yt skyaiva`, `yt @skyaiva`) is normalised ONCE at entry by `where_typed` (modal + website door) against a staff-editable table `events_where_link_aliases` (text key, events group, `alias=https://host/{handle}` entries, default ttv/twitch/yt/youtube/kick/tiktok/ig/instagram/x/twitter/discord); the stored `location` is the full href so everything v107 built applies. (B) new `black_bloc/linkcheck.py` — one bounded GET with a browser UA, injectable `fetch`; keys `events_where_link_check` (enum off/warn/refuse, default **warn**) and `events_where_link_check_seconds` (1–3, default 2); `warn` keeps the link and puts a ⚠️ note on the draft's Where line (`EventDraft.where_note`, never stored), `refuse` answers the modal in words. ⚠️ twitch.tv answers 200 for any name (SPA) — a wrong Twitch name passes; YouTube 404s. Schema stays 34. Opus build dispatched 00:02 on branch `where-smart` (worktree `C:/lcw/bb-where-smart`, off `9fc3a33`), landed 00:29 at **244k** (est. 150–220k; commits `6e81d83` A, `a876540` B, `af63b63` + `dea4739` docs, 18 files +1001/−22, tests 5502 → 5546 both orders, keys 199 → 202, schema 34). **Review (Fable, 00:30–00:35): code read clean; the one path no test can run — the real `aiohttp_status` — was probed live from the worktree against every default alias host with a real and a made-up handle.** Measured: twitch.tv, kick.com, tiktok.com, instagram.com, x.com and discord.gg answer **200 for ANY name** (single-page apps), youtube.com/@… answers **404 for a missing handle** and 200 for a real one, a dead host is `unreachable` in 0.02 s, kick.com timed out once at 2 s on a cold probe and answered in 0.14 s after — so the check catches a typo'd host and a wrong YouTube handle and nothing else, and `youtube.com/@skyaiva` itself is a 404 (that handle does not exist). **One review fix (`1d9a515`):** x.com sends a response header longer than aiohttp's 8190-byte default, so every X link raised `ClientResponseError: 400, Got more than 8190 bytes` and read as "did not answer" — `aiohttp_status` now builds its session with `max_line_size` / `max_field_size` = `HEADER_BYTES` 65536 (re-probed: x.com `ok` in 0.28 s). H16 rewritten as measured, H17 added, owner guide + sweep row 347 carry the measured caveat, code-note added. **LANDED — v108 LIVE 00:37** (merge `73e2e44` of `where-smart` 00:35, deploy gate 5546 passed + mock ok, releases v108 complete, boot 07:37:15Z, synced 29, `/health` ready, `/api/settings` **202** keys with the three new ones at their defaults). ⚠️ Never seen in Discord — sweep rows **343–350** are the owner's, and H15 stands: the 3-second modal budget with a live link is untested (if "This interaction failed" appears on a slow link: `events_where_link_check_seconds` → 1, then `events_where_link_check` → off). Worktree + branch removed.


## 2026-09-10 — Events: a typed link LOOKS like a link (masked + Open link button), and test rooms go after five minutes with denied rooms counted from the decision (v107, 23:41)

Moved whole from `TODO.md` 2026-09-10 23:44, in the session the work landed.

- 🆕 **Events: the typed link should LOOK like a link in `/event` (owner, 2026-09-10 18:03, verbatim: "Is there a way to make them look like links in the events slash").** Today a typed `https://twitch.tv/…` beside a channel renders as raw text in the draft (`draft_lines`, an embed description) and the card's Where field (`events.py:324`, an embed field) — Discord auto-links a bare URL there, but it shows the whole `https://…` string. Two cheap moves, both embed-safe: (A) `where_line` renders a URL as a masked link `[twitch.tv/mitchland](https://twitch.tv/mitchland)` (host + path, no scheme) — draft and card; button labels stay plain words (`where_said`) because a button label cannot carry a link; the scheduled event's description keeps the bare URL (safest there). (B) a link-style **Open link** button on the card (`discord.ButtonStyle.link, url=…`, the `SITE_BUTTON` pattern at `cogs/community/events.py:299`), rendered only when the text parses as http(s). Owner ~23:09: **"Do A + B"** → designed as `## Follow-up 2` on `info/where-picker-design.md` (`cc4b301`); Opus build dispatched 23:12 together with Follow-up 3 (est. 120–180k for both) — landed 239k, commits `a8a1210` (FU2) + `0e765d5` (FU3) + `9d48922` (docs) on `where-links` off `8adbc75`. **Review (Fable, 23:36): one change — the build also put an Open link button on the DRAFT while its row had a slot, displaced by Submit once the draft was complete; a control that appears only while the draft is incomplete and vanishes when it is ready was dropped (`2386050`, two draft tests → one). Draft = masked line only; card = masked line + Open link button. ✅ LANDED as v107 23:41** — merge `ac43a20` (`--no-ff`), gate 5502 passed + mock ok 17/150, keys 198 → **199**, schema unchanged 34; boot `database ready` 06:41:34Z, `synced 29`, selftest 107 ok 0 failed, `/health` ready, live `/api/settings` answers 199 keys; design § Follow-up 2 + deviations G1–G11 on `info/where-picker-design.md`; sweep rows **338–340** are the owner's (never seen in Discord). Worktree `C:/lcw/bb-where-links` + branch removed.
- 🆕 **Events: delete the test review channels, and a denied event's channel timer (owner, 2026-09-10 ~23:00, verbatim: "Can you delete the channels we made for testing events" / "Also for a denied event do we have a timer before it's auto deleted?").** Measured 23:05 against the live guild (read-only `scripts/scan/list_event_channels.py`, gitignored): event 1 'Test' (cancelled 2026-08-27) — its channel is ALREADY GONE; event 2 'Super Hero' (denied 18:01 today) — `#denied-sky-super-hero` (`1547757986091503706`, The Basement); event 3 'Sky' (still pending) — `#pending-sky-sky` (`1547774797792936016`, The Basement). The timer: `events_channel_retention_days` (live 7, default 7, 1–365) — `_sweep_finished` deletes a DONE/DENIED/CANCELLED event's review channel once `now - ends_at >= days`. Two findings: (a) it counts from the event's scheduled END, not from `decided_at`, so a denied proposal for next month keeps its room until a month + 7 days — denied/cancelled should count from the decision; (b) CORRECTED 23:10: test rooms ARE swept — the guard allows deletes inside the test channel's category, which is where review rooms go under TEST_MODE (`events.py:905`), so event 1's room went 7 days after its end; what the owner wants is minutes, not days, while testing. **Owner ~23:09: "Yes delete all of them / These are my test channels" — DELETED 23:09** (`#denied-sky-super-hero`, `#pending-sky-sky`; one-off `scripts/scan/delete_event_test_rooms.py` with a name guard, gitignored; event 3 will show cancelled at the bot's next pass). **Owner ~23:09, verbatim: "For test ones let's delete them after 5 minutes"** → designed as `## Follow-up 3` on `info/where-picker-design.md` (`cc4b301`): new key `events_test_retention_minutes` (default 5, 1–1440) used while the guard is installed, and (a) fixed in both modes — denied/cancelled anchor on `decided_at`. Bundled with the links build (Follow-up 2) as ONE Opus dispatch, two commits — `0e765d5`: `DECIDED_STATUSES`, `swept_anchor` (decided rows anchor on `decided_at`, then `ends_at`, then `created_at`; a row with none stands), `_sweep_finished` uses `testing = guard is not None` → `timedelta(minutes=…)` and logs `kept_minutes` / `kept_days`; `guard.py` and `would_delete_channel` untouched; the reconcile loop runs every 5 minutes so "5 minutes" lands 5–10. **✅ LANDED as v107 23:41** (merge `ac43a20`; key `events_test_retention_minutes` live, int, events group, default 5, 1–1440; verified on the live `/api/settings`); sweep rows **341–342** are the owner's — 341 needs ten minutes of real waiting.

## 2026-09-10 — Events: a channel AND a link beside it, the link appended to the scheduled event's description (v106, 17:41)

- 🆕 **Events: a channel AND a link together, the link appended to the description (owner, 2026-09-10 17:12, verbatim: "We need an easy way to set a voice or text channel for an event with the same where box for Twitch or something as optional / We then can append the link in the description of the event").** v105 made Where an either/or: a channel OR a typed place. Wanted: pick the voice/text channel as the place, AND (optionally) type a link in the same box — the link is appended to the event's description (the card, the announcement and the scheduled event's description), so a voice-channel event can still point at the Twitch stream. Design to write as a `## Follow-up` on `info/where-picker-design.md`: `Where.text` stops being exclusive with `channel_id` (schema unchanged — `location` already holds the text beside the two channel columns), the WherePanel's modal becomes `Link or place (optional)` and stays available with a channel set, the draft/card Where line reads `<#id> · <link>`, `scheduled_place` keeps the channel kinds and `create_scheduled_event` appends the link to the description; the website shows the link box always, not only for `— somewhere else —`. Status: filed 17:14; design next, then an Opus build (est. 100–150k). **Update 2026-09-10 17:28 — 🔨 BUILT on branch `where-link` off `main` at `ebe0ead`, commits `08173b7` + `2cfbdbe`, ⚠️ NOT merged, NOT deployed, NOT pushed.** Schema unchanged at **34** (no migration); registry keys **197 → 198** (`events_where_link_in_description`, events, bool, default true — checklist 33 on the owner's chat decision); tests **5453 → 5473** forward and `BB_REVERSE=1`; `ruff check black_bloc tests` clean; mock *ok - 17 pages, 150 routes, 14 core settings, all keys present*. ⚠️ **Nothing has met Discord** — no test can click a Discord button, no bot was booted (a worktree holds no token), and TEST_MODE makes no scheduled event, so the appended description itself is UNVERIFIED and waits on the lift with sweep row 335. No browser rendered the events page. Departures are the `## Follow-up deviations` foot of `info/where-picker-design.md`; owner sweeps are rows **336–337**. The merge and the MOVE to DONE are the conductor's. **LANDED 2026-09-10 17:41 as v106** — merge `6c10b9d` (`--no-ff` of `where-link`, three commits `08173b7` `2cfbdbe` `1add90c`, the third the docs foot); gate 5473 passed 30.3 s + mock ok; boot `database ready` 00:40:11Z, `synced 29`, selftest 107 ok 0 failed, purge in 1 min; `/health` ready; `/api/settings` events group answers `events_where_link_in_description` bool value True default True, 198 keys; `/api/events` rows carry `location` beside `where_kind`. Fable review before the merge found no blocker: the one risk (`page-events.js` reading `querySelector('.field-help')`) was cleared against `ui.js:727 field()`, which always renders the help `<p>` when help text is given. Agent cost 209k against a 100–150k estimate. Worktree `C:/lcw/bb-where-link` and branch removed. ⚠️ Still never seen in Discord — rows 335–337 are the owner's, 335 needs TEST_MODE lifted.

## 2026-09-10 — Events: a real "Where" — voice/stage/text channel or a typed place (v105, 17:09)

- 🆕 **Events: a real "Where" (owner, 2026-09-10 16:11, verbatim: "We also need to add the where section like a real discord event for text channel or voice channel or other if they want to use a twitch link or something").** Today `location` is one free-text box on the Title & details modal and the scheduled event is always Discord's *external* kind with that text as its location. Wanted: the draft panel gets a **Where** move like Discord's own create-event dialog — a **voice channel** (the scheduled event becomes a voice-channel event, members get the Join button), a **text channel** (Discord has no text-channel event kind, so it stays *external* with the channel mention as the location and the announcement links the channel), or **Other** (a typed place or link — a Twitch URL — as now). Design to write: `info/where-picker-design.md` — a `WherePanel` in the same shape as `ZonePanel` (a channel select, capped 25, plus `Other — type it…`), `events` rows gain `where_kind` + `where_channel_id` (schema 33 → 34), `create_scheduled_event` picks `entity_type` from `where_kind`, the card's **Where** line renders a mention or the text, the website's event form gets the same three-way choice (checklist 33), `/raidtrain` unchanged unless asked. Status: filed 16:12; ✅ design written 16:13 (`info/where-picker-design.md`); 🔨 **BUILT 2026-09-10 on branch `where-picker`** off `a47e43a` in worktree `C:/lcw/bb-where-picker` — five commits, schema **33 → 34**, tests **5395 → 5444**, `ruff check` clean, mock still *17 pages, 150 routes, 14 core settings*, 10 deviations at the design's foot, sweep rows **329–335** (335 needs TEST_MODE lifted). ⚠️ **NOT merged, NOT deployed, never seen in Discord** — the conductor merges and deploys; two suite failures on that branch (`test_running_the_self_test_answers_the_counts_and_names_every_failure`, `test_the_self_test_card_says_what_it_will_do_before_it_has_ever_run`) are PRE-EXISTING at `a47e43a` and already fixed on main by `f9f5339`. Registry keys unchanged — checklist 33 says there is nothing to decide here. ✅ **LANDED 2026-09-10 17:09 as v105** — rebased onto the rewritten main (`git rebase --onto main a47e43a`, four docs conflicts resolved by keeping both header paragraphs), merged `--no-ff` as `3205c0f`, gate ruff + **5453** passed (5403 + 50) + mock *17 pages, 150 routes*, boot 17:09 selftest 107/0, `/api/events` answers `where_kind`/`where_channel_id`/`where_label`; record on `deploys.log`. Worktree + branch removed. ⚠️ Still NOT seen in Discord (sweep rows 329–334 are the owner's; 335 waits on TEST_MODE); the site `<select>` was not rendered in a browser. Follow-up ask filed the same minute (17:12): channel AND link together — see the 🆕 item on TODO.

## 2026-09-10 — Raid train's calendar name stays the title, editable on the dashboard (v104, 16:44)

- 🔧 **Raid train's calendar name: stays the plain title, but editable on the dashboard (owner, 2026-09-10 16:28, verbatim: "Leave raid train as it is now but let it be changeable on the dashboard").** Answers the open question from the When-picker landing (should a raid train's scheduled event also get ` Feat. BaF`?): NO by default. New settings key `raidtrain_scheduled_name_template` (text, default `{title}` — today's behaviour exactly, `cogs/content/raidtrain.py:2305` names the event `clamp(train["title"], TITLE_LIMIT)`), validated by the same `checked_name_template` as `events_scheduled_name_template` (must contain `{title}`, no other braces), rendered through the shared `events.scheduled_name(template, title)` so a template that will not render falls back to the plain title. Registry (`KEY_TYPES`, description, default, coerce map, namespace `raidtrain` by prefix), `site/mock/server.mjs` row, tests mirroring `settings_store` + `raidtrain`, `docs/info/architecture.md` key count 196 → 197, sweep row. Owner review: https://blackbloc.heygabi.ai/settings.html → Raid train group → `raidtrain_scheduled_name_template`. Status: filed 16:29; Opus build landed 16:41 (152k against a 60–100k estimate — it also wrote the four scheduled-event tests raid trains never had); merged `b320031`; **v104 LIVE 16:44**; live `/api/settings` answers `{title}` at default; tests 5395 → 5403; sweep row 328 is the owner's (TEST_MODE). NOT verified: the Settings page rendering (Discord sign-in), a real train's calendar event.

Closes the open question from the When-picker landing (should a raid train's event also get ` Feat. BaF`?): no by default, one key to change it. Review: https://blackbloc.heygabi.ai/settings.html → Raid train → `raidtrain_scheduled_name_template`.

## 2026-09-10 — Self-test posts last 60 s, not 5 min (v103, 16:24)

- 🔧 **Self-test posts last 60 s, not 5 min (owner, 2026-09-10 16:13, verbatim: "Also the test stuff posted each deployment should last 60s instead since it's mainly for you and not me / It's an automated test to make sure every command works and nothing errors.").** One knob: `selftest_purge_minutes` (int 1–1440) whose registry default was 5 — `SELFTEST_PURGE_MINUTES_DEFAULT = 1` now (checklist 33: still editable on the Settings page and `/settings set-value`), mirrored in `site/mock/server.mjs`, three tests, `info/selftest-design.md`, `access/OWNER_GUIDE.md` row 104. `purge_loop` ticks every 60 s so a 1-minute setting deletes within 60–120 s. **v103 LIVE 16:24** (`a47e43a` + `f9f5339`): boot line reads `purge in 1 min` (23:24:13Z), so the default bit and no guild override exists. Gate refused the first run — two more tests asserted `5 minute(s)` (my grep for `purge_minutes` missed them); fixed and re-run. NOT verified: the purge tick after this boot; the Settings page showing 1.

**Where the number lives:** `black_bloc/settings_store.py` `SELFTEST_PURGE_MINUTES_DEFAULT`, still a settings key editable on https://blackbloc.heygabi.ai/settings.html and via `/settings set-value` (checklist 33). `docs/info/selftest-design.md` records both values with their dates.

## 2026-09-10 — The "When?" picker landed as merge `1f35f28` (branch `when-picker`), shipping as v100 — `/event` Propose and `/raidtrain` Start are draft panels with dropdowns, a modal that never refuses, a zone dropdown, and `{title} Feat. BaF` as the calendar name. Deploy verification recorded on `deploys.log`.

**Asked (moved whole from `TODO.md` → Open engineering items):** 🔧 **`/event` propose form — three UX asks (owner, 2026-09-10 ~15:00, verbatim: "A few bad experiences right away using /events I apparently made an error and the form went away to be refilled We also need to solve this auto select timezone thing or at least make it a dropdown Same for time and date Can we get drop down there too").** Seen: he typed `2026-09-11` as the start, the modal refused it ("not a date Black Bloc can read … YYYY-MM-DD HH:MM …") and everything typed was gone. (1) **An invalid entry must not throw the form away** — a modal-submit cannot be answered with another modal, so the refusal answers ephemerally with a **Try again** button that re-opens `EventModal` pre-filled (`TextInput.default`) from what was typed; (2) **time zone as a dropdown**, defaulting to the member's stored zone, else the guild default (Discord gives a bot no user zone, so "auto" = remembered; `DEFAULT_TZ` is hard-coded `America/Phoenix` in `timezones.py` — becomes a settings key, checklist 33); (3) **date and time as dropdowns** — Discord modals cap at 5 components and selects at 25 options, so this is a two-step propose (text modal → ephemeral "When?" panel with day / hour / minute / zone selects and Submit / Back) or selects-in-modal via `ui.Label` (discord.py 2.7.1 has it) with trimmed fields. **DECIDED 2026-09-10 15:08–15:10 — Q1 "A" (draft panel + text modal, dropdowns on the panel, modals never refuse, Submit renders only when valid), Q2 "Yes, same build" (`/raidtrain` Start too).** Design: [`info/when-picker-design.md`](info/when-picker-design.md) — shared `black_bloc/when_picker.py`, `ZonePanel` dropdown (24 zones + `Other — type it`), four settings keys (`default_timezone`, `timezone_choices`, `time_step_minutes`, `events_default_minutes`). **+ (4) the scheduled event's NAME (owner, 15:11: "Can we make it also say '{Event Name} Feat. BaF' when it post the discord events after" / 15:12: "Also make that standard name format something changeable on the website") — key `events_scheduled_name_template`, default `{title} Feat. BaF`, editable on the Settings page's Events group and by `/settings set-value`; design §5b, same build.** Status: **Opus build dispatched 2026-09-10 15:15 in worktree `C:/lcw/bb-when-picker`, branch `when-picker` (est. 250–350k); lands as v100.** Left for later (design D4): the website's Events / Raid-train create forms still take a typed `YYYY-MM-DD HH:MM` — a `datetime-local` input + zone select there is its own small item.

**Landed 15:52 (Opus build, 385,813 tokens / 228 calls / 38 min against a 250–350k estimate; commits `446f191` module+tests, `567d33b` keys+fallback, `6c0768d` events draft panel + `ZonePanel` + calendar name, `869e57a` raidtrain draft panel, `580774a` docs; merged `--no-ff` as `1f35f28`):** new `black_bloc/when_picker.py` (`WhenDraft`, `DaySelect`/`HourSelect`/`MinuteSelect`/`DurationSelect`, `LaterModal`, `ZonePanel`, `DURATIONS`, `SELECT_CAP=25`, `DAY_COUNT=24`, `ZONE_COUNT=24`); `cogs/community/events.py:EventDraftPanel` and `cogs/content/raidtrain.py:TrainDraftPanel` with Submit/Start rendered only when `draft_check` passes; `events.scheduled_name(template, title)` renders then clamps to `EVENT_NAME_LIMIT`, and a template that will not `.format` logs a warning and falls back to the default; five keys in the Events group via `NAMESPACE_OVERRIDE` — `default_timezone` (America/Phoenix), `timezone_choices` (24 IANA names, unknown names dropped, an all-unknown list refused), `time_step_minutes` (5–60, default 15), `events_default_minutes` (5–10080, replaces the hard-coded `DEFAULT_DURATION_MINUTES` in its two named places), `events_scheduled_name_template` (`{title} Feat. BaF`) — 191 → **196**, all on the Settings page and `/settings set-value`; `timezones.get_timezone(db, user_id, fallback)` re-validates the fallback with `is_known`. Removed: `EventModal`, `Events.submit` (D7), `TrainModal` (D9 — it had NEVER worked: built as `TrainModal(view, …)` and its `on_submit` called a `submit_train` no class defines, and no test caught it). Twelve deviations D1–D12 at the foot of `info/when-picker-design.md`. +109 tests (5286 → **5395**, forward and `BB_REVERSE=1`); ruff clean; mock 17/150/14; `code-notes.md` got a by-NAME section and a 203-key line-diff re-key at the merge.

**Deploy:** **v100 LIVE 2026-09-10 16:00** — the 15:55 detached run deadlocked at 82% of pytest with every worker idle (fourth hang of this shape; the log sat untouched 72 s and the workers' CPU moved 0.016 s in 20 s), tree killed, the 15:58 retry via the PowerShell tool with `*> file` passed the gate (ruff, 5395 in 27.63 s, mock) and shipped; releases v100 complete; boot `database ready` 23:00:02Z, `synced 29`; `/health` ready guilds=1 latency 62. **NOT verified:** anything in a Discord client (rows 323–327 are the owner's), the live Settings page's Events group, the calendar name itself (TEST_MODE makes no scheduled event; row 327 waits on the lift), the selftest line (not yet in the log at 16:01). **Left open (on TODO as the follow-ups item):** D4 website forms; the owner's call on a raid-train ` Feat. BaF` suffix; the by-anchor pass of the two `# Events` code-notes sections.

## 2026-09-07 — Music bot scrapped (owner, 15:10) — request #3 is closed, not paused; a monthly feasibility check replaces it

**Owner, verbatim:** *"3 scrap this whole project, until we find a reliable way to do this let's be done with me. Maybe set up a monthly research task to look into if it's doable in a stable way."* — item 3 of the 2026-09-07 15:06 pending list (the Spotify decision). Nothing was ever built. The recurring check lives in `TODO.md` under *Waiting on the owner* (next check 2026-10-07; findings go to `info/music-source-research.md` when the first pass runs).

⚠️ **Not done here:** request #3's own row in the bot (Requests page, status `on hold`) is a staff write; the operator token is read-only, so it stays `on hold` until staff move it on https://blackbloc.heygabi.ai/requests.html — the owner said "be done with me", so this is recorded, not asked.

**Moved whole from `TODO.md`:**

- ✅ **DECIDED 2026-09-03 14:22 — SKIPPED (owner: "still would be YouTube? Let's skip it then.
  Back to the backlog dungeon with the music bot").** Request #3 stays on **hold**; nothing
  is built. Original: **Spotify for the music bot (owner, 2026-09-03 ~13:55: "Check if we can do
  Spotify for the music bot")** — request #3 (PT, on hold). Checked the same
  afternoon: **not as a source.** Spotify's Web API exposes no audio stream (it
  only controls a signed-in user's own Spotify client), its developer terms name
  Discord bots as not permitted, the 30-second `preview_url` was pulled for new
  apps 2024-11-27, and since 2025-05 an app needs 250k monthly users before it
  leaves development mode. What every surviving music bot does instead:
  **accept Spotify links** (track / album / playlist), resolve them to titles via
  the metadata endpoints (client-credentials, still open in dev mode), and play
  the matching audio from YouTube / SoundCloud (Lavalink + the LavaSrc plugin is
  the standard stack; needs a Java sidecar — a second Fly app — and YouTube
  increasingly blocks datacenter IPs, so that source needs its own care). Owner
  decision pending: "Spotify links in, audio from elsewhere" is buildable; native
  Spotify playback is not.

## 2026-09-06 — Operator read bound landed as merge `88e0242` (branch `operator-read-bound`), shipping as v99 — the right token is now bounded by the dashboard's own 300/min read bucket, on the operator identity

**Asked (moved whole from `TODO.md`'s wave-1 residual bullet):** **Added 2026-09-06 14:32 (v98 build's finding, not fixed):** routes gated by `staff_dependency`
  alone (`/api/settings`, `/api/selftest`, most of `status.py`) have no per-identity read bound for the
  operator identity (`who["id"] == "0"`) — `writes.py:reader_dependency`'s 300/min bucket covers `ref.py`
  wholesale and only the `reader`-taking routes of `status.py`/`costs.py`. The operator's own guess bucket
  no longer touches right tokens (by design), so an operator read loop on those routes is bounded only by
  the server. Fix shape: hang the read limiter on the operator identity in `auth.py:note_operator_read`, or
  give `staff_dependency` the same `reader` bucket — one bucket, one home (checklist 33 asks nothing: the
  rate is the existing `READ_RATE`). **✅ DECIDED 2026-09-06 19:30, owner verbatim *"Do a"* — the first shape; design appended to `info/operator-read-design.md` (§ *the operator read bound*); Opus build dispatched ~19:40 in worktree `C:/lcw/bb-read-bound`, branch `operator-read-bound` off `571e581` → v99.**

**Landed 20:00 (Opus build, 158k against 60–100k, 66 calls, 11.5 min; commits `c6f7594` code+tests,
`3a7ad78` docs):** `auth.py:operator_session` now runs compare → `READ_METHODS` → **`read_bucket_for(bot).take(OPERATOR_WHO["id"])`
→ `429 slow_down` / `TOO_MANY_READS`** → `note_operator_read`, so a good-token write is refused `403` without
spending a read token and a refused read leaves no `web.operator.read` row. `writes.py:reader_dependency`
returns early for the operator (by the constant, never `"0"`), so one request costs one token whichever gate
the route uses; staff are charged there exactly as before. `READ_RATE`, `READ_WINDOW_SECONDS`,
`READ_BUCKET_ATTR`, `TOO_MANY_READS`, `read_bucket_for` and (deviation 1) `_bucket` moved into `auth.py`;
`writes.py` imports them back and re-exports. The sentence took Rule 4's clause: *"…open the page, or send
the read, again."* +7 tests (5279 → **5286**, both orders): the 300-read flood proves the bound is 300 not 30
and counts exactly 300 rows, then drains the operator's key a minute ahead (deviation 3: the 301st read is
NOT refused — 300 `TestClient` reads take 0.7 s and the bucket refills 5 a second); staff buckets untouched
by the operator's flood and the reverse; a read refused by the read bucket never builds the guess bucket;
`writes.read_bucket_for is auth.read_bucket_for`. No schema, key, route or log-kind change; mock 17/150/14.
Design + `### Deviations` at the foot of `info/operator-read-design.md`; refusal-table rows in both
operator-read docs; code-notes `# Operator read bound`.

**Deploy:** the 19:52 `deploy.ps1` run **deadlocked at 81% of the pytest gate** — all 33 xdist workers idle
at zero CPU for four minutes, a THIRD hang shape today (the 10:42 / 13:45 / 14:09 hangs were at worker
spawn); killed the tree, the 19:59 retry (PowerShell tool, `*> file`, background) passed the gate in 26 s and
shipped. v99 boot: `database ready` 03:00:51Z, `synced 29`, selftest 107 ok / 0 failed, `/health` ready
guilds=1 latency 64. `docs/deploys.log` line filled.

**Live run:** `pytest -m live` against v99 = **58 passed / 1 skipped** (unchanged, as the design required).
**Sweep row 322 (was `RB-a`) drilled twice by Claude:** 400 reads at 25 concurrent, 2.3 s → **308 × 200,
92 × 429** with the `TOO_MANY_READS` sentence, first refusal at read 312 (300 + eight refilled); the
PowerShell 5.1 `HttpClient` recipe from the owner's own shell, 1.2 s → 305 / 95; the right token read again a
minute later. ⚠️ **The build's sweep recipe was wrong and was replaced at the merge:** a serial
`Invoke-RestMethod` loop "to 320" runs at 7–10 a second against a 5-a-second refill and never trips; the row
now fires the reads at once.

**Not verified:** the Logs page held **309** `web.operator.read` rows for the burst's 308 answers — one
EXTRA (a refusal cannot write one; most likely an edge-proxy-retried `GET`), cause not established. Row 322
by a PERSON (Claude's drill is not the owner's eye on the Logs page). Rows 320 and 321's sign-in half remain
the owner's.

## 2026-09-06 — Operator bucket fix landed as merge `deaae68` (branch `operator-bucket`), shipping as v98 — the live suite's first green run (58 passed / 1 skipped). Deploy verification recorded on `deploys.log`.

**Asked (moved whole from the TODO resume header, where it was recorded 13:55):** `pytest -m live` after the
first operator read ever: 20 passed / 38 failed / 1 skipped, and the failures are two findings, not the door:
(1) 🔴 `auth.py:operator_session` charges the 30-a-minute per-IP bucket on EVERY bearer, matching or not, so
the 60-path read sweep 429s after ~30 — the design's intent (decision 6, *"a guess costs something"*) is that
a WRONG token is a guess; charge on mismatch only, and give the operator 429 its own sentence (today it says
*"more sign-in attempts"*, which mislabels the cause); (2) `tests/live/test_selftest.py::…never_start_one`
expects `operator_read_only` but the live host answers `cross_site` — `server.py:117`'s origin check refuses
the POST before the operator gate does (still a 403 in words; the test must send the dashboard `Origin` so
the operator gate is the one that answers, or accept either). Build dispatched ~14:05 (Opus, worktree
`C:/lcw/bb-operator-bucket`, branch `operator-bucket`) → v98; then re-run `pytest -m live`, record the count
in `access/testing.md`, sweep row 103, retire the three NOT-verified headers.

**Landed:** the Opus build (129k / 69 calls / 10 min against 60–100k) as `7c1c830` + `1cc5447`, merged
`deaae68` 14:05 after three doc-header conflicts (both sides had retired the same "never minted" headers;
main's measured lines kept). `operator_session` compares first, constant-time, and everything else lives
inside the mismatch branch: bucket `take` → `429 slow_down` with the new `OPERATOR_SLOW_DOWN` sentence, else
`401 bad_operator_token`. A right token never builds the bucket (tested by attribute absence) and still reads
while its address is out of guesses — deliberate, written as a Deviation in
`info/operator-read-design.md`: the bucket is per IP and a correct token is proof the caller is not guessing.
Past 30 wrong tokens the 401 is unreachable (429 every time), so ignoring the limit buys no extra guesses.
Live tests send `conftest.same_site_headers()` (Origin from `BLACK_BLOC_LIVE_URL` + `sec-fetch-site:
same-origin`; both, because `same_site()` accepts either and Origin-only needs a character-exact host);
`test_refusals` tightened from `(403, 415)` to `403` + `operator_read_only`. +2 tests to **5279**.
**Deploy:** the 14:09 foreground `deploy.ps1` run HUNG at xdist spawn (third time today; 33 idle pythons,
Stop-Process denied); the 14:19 retry via the PowerShell tool with `*> file` got through and shipped
v98 14:22 (boot `database ready` 21:21:57Z, `synced 29`, `/health` ready).
**Live run against v98:** 27 failed at first — a THIRD finding, test-side: `test_reads.py` ignored the
contract's `shape`, and `/api/requests/mine` rightly refuses the operator identity as `not_a_member`. Fixed
on main (`rows_of` reads `list`/`map`/`namespaces` the way `check.mjs` does; the sweep accepts that one
403) → **58 passed / 1 skipped**, recorded in `access/testing.md`. Sweep rows **320–321**. Gap flagged by
the build, not fixed: routes gated by `staff_dependency` alone have no per-identity read bound for the
operator (the 300/min `reader_dependency` bucket covers `ref.py` and parts of `status.py`/`costs.py` only)
— on TODO as a residual.
**Not verified:** rows 320 (31 wrong tokens by hand) and 321's dashboard-sign-in half; the Logs-page half
of row 103 (by eye).

## 2026-09-06 — Loop guard (KI-24) and two small gates landed as merge `689eff5` (branch `loop-guard`), shipping as v97 — deploy verification recorded on `deploys.log`. Owner decision Q4, verbatim "Build it a".

**Asked:** Q4 of the five owner questions of 2026-09-06 — KI-24 (a `before_loop` failure bypasses
`@loop.error`, filed by engineering sweep 3 as `WATCHING`): (a) build the guard, bundled with the two
report-only findings beside it, or (b) leave it. Owner 11:48: *"Build it a"*. Design
`docs/info/loop-guard-design.md` (`16bd8c2`); Opus agent in worktree `C:/lcw/bb-loop-guard`,
170k / 92 calls / 15.5 min against an 80–140k estimate; six branch commits `e4a3efa` → `59c5aec`;
21 files, +370/−60; tests 5267 → 5277 both orders; ruff clean; mock 17/150/14 unchanged.

- **The guard:** one new leaf module `black_bloc/loops.py:wait_ready(bot, failed) -> bool` awaits
  `bot.wait_until_ready()` and hands any `Exception` (never `CancelledError`, a `BaseException`) to the
  loop's own `@loop.error` handler, so a `before_loop` failure records `last_error`, logs, and
  `restart()`s exactly as a body failure does. All fourteen `before_loop`s across thirteen cogs call
  it; `raidtrain._before_sweep` and `youtube._before_poller` read the bool before `_retime()`. Two AST
  guards in `tests/test_loops.py` keep every `before_loop` on the helper, and a test against a REAL
  `discord.ext.tasks.Loop` whose `wait_until_ready` raises once proves the restart: `restart()` from
  inside `before_loop` works because the library yields at `await asyncio.sleep(0)`
  (`discord/ext/tasks/__init__.py:220`, its own comment says *allows canceling in before_loop*) and
  the done-callback starts it again.
- **Found on the way:** `golive.py:poller` had NO `@loop.error` handler at all (its body swallowed
  its own errors) — it gained `_poller_stopped` in its siblings' shape; and `Core._purge_failed` was
  the one handler of fourteen that did not restart (KI-24's "every loop restarts" was true of
  thirteen) — it restarts now.
- **Gate 1:** `Core.cog_load` no longer starts `purge_loop` on a bot with no database
  (`getattr(self.bot.db, "is_connected", False)`), like every other db-backed loop.
- **Gate 2:** `POST /api/polls` (`poll_create`) refuses `409 polls_off` with the cog's own `POLLS_OFF`
  before any row is written, the shape the recurrence route beside it already used — the 🔴 finding
  from the recur-web report (a staffer could make a poll from the website while `/poll` said polls were
  off) is closed.
- **No new settings key** (checklist 33: no decision a Lead would change), **no new log kind**
  (checklist 34). KI-24 replaced with a CLOSED stub in `KNOWN_ISSUES.md` pointing at the design.
- Sweep rows **315–319** (were `LG-a`–`LG-e`): the Health page shows every loop running after the
  deploy; polls off → the dashboard's create form refuses in a sentence; polls on → the ordinary path
  is unchanged.

**Not verified:** nothing has met live Discord; the restart is proved in-process against a real
`Loop`, not against a gateway; the Health page was not opened by the build (row 315 is that check).

## 2026-09-06 — Logs buttons (merge `42d2e6e`, branch `logs-buttons`) and Create-a-recurring-poll from the website (merge `c915ade`, branch `recur-web`) landed together, shipping as v96 — deploy verification recorded on `deploys.log`. Owner decisions Q2 "2. A", Q3 "3. B".

> **Landed 2026-09-06 11:36 Phoenix**, both merges pushed BEFORE this docs commit. Two Opus agents in
> parallel, hand-made worktrees off `b428236`: `C:/lcw/bb-logs-buttons` (244k / 185 calls / 30 min against
> 120–180k) and `C:/lcw/bb-recur-web` (274k / 147 calls / 34 min against 150–220k) — both over estimate,
> both by the tests (+24 and +15). The only merge conflicts were the two agents appending sections to the
> foot of `sweeps.md` and `code-notes.md`; both sides kept. Gate on `main` after both: ruff clean,
> **5226 → 5267** green forward and `BB_REVERSE=1` (29.5 s / 30.2 s), mock `ok - 17 pages, 150 routes,
> 14 core settings`. Sweep rows **305–309** (were `LB-a`–`LB-e`) and **310–314** (were `RW-a`–`RW-e`).
> Registry keys **189 → 191**, settings groups **22 → 23** (a new `logs` group), mock routes **149 → 150**,
> schema unchanged at 33.

- **Q3 — the Logs button's two knobs, as buttons (owner: "3. B", buttons ON the list rather than a modal
  first).** `black_bloc/logs_panel.py` (`LogsPanel(Panel)`, `MORE`/`ONLY_IMPORTANT`/`EVERYTHING`,
  `buttons_for`, `refresh`, `panel_for`); `actionlog.send_logs` — still the one body behind all 18 call
  sites (an AST guard asserts they pass only the feature) — builds the panel and sends it with `view=`;
  each press edits the SAME ephemeral message with `allowed_mentions=none()`; **Show more** is not drawn at
  `LOGS_MAX` or when the last read came back short; the toggle's label is the move it would make; staff
  and the database are re-asked on every press (row 290 precedent); timeout through `Panel` on the
  existing `settings_panel_minutes` key (no third key — a test asserts `logs_panel_minutes` is absent).
  Keys `logs_count` (int 10, `LOGS_MIN`..`LOGS_MAX`) and `logs_important_only` (bool False) in
  `settings_store.py` with `KEY_HELP` + `labels.js` + mock `SETTING_SPECS` + `contract.json` min/max —
  they open a **Logs** section on settings.html and under `/settings` ▸ *A setting group…*. Ten deviations
  in `docs/info/logs-buttons-design.md` § Deviations, two worth knowing: the agent had to edit
  `contract.json` (fenced off for the other agent) because a bounded key cannot exist without its
  min/max rows there; three cog tests that asserted "Logs did not re-render the panel" read a fake
  attribute their harness also set inside `original_response()`, which `send_logs` now calls so a
  timed-out list can disable itself — re-expressed, behaviour unchanged. `LOGS_MIN/MAX/DEFAULT` moved into
  `settings_store.py`; `recent_lines` split into `lines_for`.
- **Q2 — create a recurring poll from the website (owner: "2. A", a dashboard form rather than
  Discord-only).** `POST /api/polls/recurrences` in `api/tools/polls.py`: `_wanted_cadence` proves the
  cadence (`cadence_trouble`, `cadence_token`, `next_occurrence`) BEFORE any row exists, so a bad one
  leaves no poll behind (a guard broken on purpose failed four tests on the row count); then the shared
  `_asked_for` (extracted from `poll_create`, no behaviour change) → `store_poll(status=RECURRING,
  via=VIA_WEBSITE)` → the cog's own `save_recurrence(..., actor_for(...), via=VIA_WEBSITE)` — ONE
  `poll.recur_created` row with `via: website`. Gates: **no `poll_recurring` key exists**; the cog gates
  on `polls_are_on` + `may_create` + staff, so the route adds `409 polls_off` (`POLLS_OFF`) beside the
  router's `staff_dependency`, plus the test-channel refusal, plus a gate the design did not name — a
  DATE poll cannot recur (`RECUR_NOT_A_DATE`, 400, and the page hides the block for that kind). The page:
  `createForm` gains a **Repeat** select directly under the Channel/Ping/Voters/Results/Thread row; only
  the field that applies is drawn (weekday / day-of-month / neither); the button relabels to *Save the
  repeating poll*; the outcome lands on the Repeating section and the form clears; tz defaults by being
  BLANK so `timezones.DEFAULT_TZ` stays the one home (no new key — no new decision, checklist 33). The
  agent drove the page half in a real browser against the mock. Eight deviations in
  `docs/info/recurrence-web-create-design.md` § Deviations. Mock mirrors the visible refusals but not
  `next_occurrence` (`next_at = daysAhead(1)`, the resume route's existing simplification).
- **Reported by the agents, NOT fixed (now on TODO):** 🔴 `POST /api/polls` (one-off create) does not
  check `poll_mode` — a staffer can create a poll from the website while polls are off in Discord; the
  new route gates it, the old one was deliberately left alone. The `logs` namespace makes **23** settings
  groups against `/settings`' 25-option select cap. Mock `state.pollRecurrences` seeds ids 4/5 inside
  `state.polls`' id space (no collision, one table in the bot). Chrome `computer left_click` by ref landed
  off-screen on polls.html (button rect at `x = -90`) — `javascript_tool` clicked it.
- **v94/v95 note (supersedes the DONE entry below and the 10:58 TODO header):** v94 was deployed by the
  OWNER at 11:13 (Fly v94, `b428236`) after the session's detached run hung; he ran the script twice, so
  Fly **v95 is the same commit** 72 s later. Both boots: `database ready`, `synced 29`, `selftest 107 ok 0
  failed`, `/health` ready. There is NO "migration to 33" log line to look for — `db.py` logs only when a
  migration adds a column; a new table is silent. The hung PIDs (19840 powershell / 67456 python, started
  10:42:49) were still alive at 11:37; the v96 detached run passed its gate in 27.9 s, so the hang was a
  one-off, cause unknown.

## 2026-09-06 — Saved poll drafts landed as merge `8405bea` (branch `poll-drafts`, schema 32 → 33, shipped as v94 — deploy verification recorded on `deploys.log`). Owner decision Q1: "B but only save 1 draft per person max".

> **Landed 2026-09-06 10:45 Phoenix.** Opus, hand-made worktree `C:/lcw/bb-poll-drafts` off `9cd79d6`,
> 358k tokens / 146 calls / 32 min against a 250–400k estimate. Merge pushed BEFORE the docs commit
> (runbook gotcha honoured). Gate on the main checkout: ruff clean, **5187 → 5226** tests green forward
> and `BB_REVERSE=1` (26.3 s / 29.9 s), mock `ok - 17 pages, 149 routes, 14 core settings`. Sweep rows
> **300–304** (were `PD-a`–`PD-e`) in `docs/access/sweeps.md`; design + nine recorded deviations in
> `docs/info/poll-drafts-design.md` § Deviations; notes in `code-notes.md` § *Saved poll drafts*.
> ⚠️ First detached `scripts/deploy.ps1` run HUNG at 92% of its pytest gate (32 idle workers, 11+ min,
> before push/flyctl); the same command passed in the session shell in 26.7 s — environmental, see TODO.

- **What it is:** a member can press **Save for later** on the `/poll` create preview; the draft lives in its
  own `poll_drafts` table keyed `PRIMARY KEY (guild_id, user_id)` — one per person per guild, enforced by
  the schema, a second save REPLACES (button says so). **Resume draft** on the main panel reopens the
  preview; **Post it** from a resumed draft deletes the draft row in the SAME transaction as the poll
  insert and the one `poll.created` log row carries `from_draft: true` (checklist 34). **Discard draft**
  (danger, confirm). Staff: `Saved drafts…` select → card → **Discard** → reason modal → DM to the member
  through the test-mode guard; staff cannot post or edit another's draft. `draft` LEFT the poll state
  machine (`STATUSES`/`OPEN_STATUSES`/`TRANSITIONS`/`COLOURS`/`CARD_BUTTONS`; `polls.status DEFAULT
  'draft'` stays — SQLite has no ALTER COLUMN — and is unreachable). Keys `poll_drafts` (bool, True) and
  `poll_draft_days` (int, 14, 0 = never, max 365) registered both ways with labels; expiry runs inside the
  existing polls archive sweep (`_expire_drafts`, one `poll.draft_expired` row per drop, nothing while
  drafts are off). Log kinds `poll.draft_saved` / `draft_expired` ROUTINE, `poll.draft_discarded` IMPORTANT.
- **Why the deviations:** Discord's five-buttons-per-row cap — a staff panel's row 0 was already full, so
  `Resume`/`Save`/`Discard` sit on row 4 and the site link moved 3 → 4; `poll_draft_days` is the fifth and
  last field the `Numbers…` modal can hold. "Saved." is an ephemeral sentence, not a panel footer, because
  `Panel.on_timeout` overwrites the footer. `Save`/`Resume` render only for somebody who may CREATE.
  `from_json` also replaces wrong-typed values (a bad payload must not raise inside a callback).
- **Recurrence path (design §8):** `Save for later` is simply not rendered once a draft is repeating.
- **Reported, not fixed:** `site/mock/server.mjs:2986` still lists `'draft'` in `POLL_STATUSES` and `:3303`
  treats it as open — mock-only copy, check passes either way. Nothing here has met live Discord yet.

## 2026-09-06 — Fixture-scope sweep, half B landed as merge `348b98e` (branch `fixture-scope-half-b`; NOT deployed — test-only, v93 stays live). All seven measurement-pass decisions settled.

> **Landed 2026-09-06 09:35–09:40 Phoenix.** Opus, hand-made worktree `C:/lcw/bb-fixtures-b`, 203k tokens /
> 127 tool calls / 50 min against a 250–400k estimate. The owner's decision 2 (2026-09-05, "Yes"): one
> module-scoped `db` fixture in `tests/conftest.py`, connected once per module and REWOUND per test —
> `take`/`put` MOVED from `tests/api/conftest.py` (which now imports them), the rewind widened to put the
> schema back (`test_golive` drops the unique open-session index on purpose; `put` compares `sqlite_master`
> to the snapshot and re-runs stored DDL, rows deleted before the repair so an index never rebuilds over
> duplicates; `sqlite_sequence` is in the row snapshot so ids restart at 1). **All 35 per-file `db`
> fixtures deleted, 0 kept** — every one was the plain pattern; the 13 tests in 8 files that `await
> db.close()` to prove the "cannot reach its own database" sentence are handled by the shared fixture
> reconnecting when it finds the database closed. Commits `b8d4eab` B1, `99f76ee`/`572071c`/`6d69763`/
> `298c8cb` B2 by folder, `1fe17e8` B3, `4c81a93` docs. **5187 tests, none added or deleted**, `ruff`
> clean; gate on main 28.2 s forward / 28.7 s reversed on `-n auto`; the agent measured 55.0 → 26.0 s
> `-n auto` (−53 %), 462 → 110 s serial (−76 %), `tests/cogs` 29.0 → 12.1 s; reversed serial green too.
> Combined with half A (`e24e6b7`): the gate here went **88.7 s (v93) → 28.2 s** on the same machine.
>
> **The presence reversed-serial failure half A found was not a fixture problem:** `discord.py`'s
> `load_extension` builds a NEW module object and hangs it on `sys.modules`, so after
> `tests/test_selftest_panels.py:live` loads all 19 cogs, `black_bloc.cogs.presence` is no longer the
> object `tests/cogs/test_presence.py` imported from, and its `monkeypatch.setattr` patches a module the
> running cog no longer lives in. Fixed test-side: an autouse fixture in `tests/conftest.py` restores the
> collection-time cog modules after every test. Nothing under `black_bloc/` touched — the production
> behaviour is discord.py's and correct for a real bot. Also corrected: half A's note that a conftest is
> not importable by name — under `--import-mode=importlib` pytest registers `tests.conftest` in
> `sys.modules` before the api conftest imports, verified with a probe.
> ⚠️ **Beyond the brief, NOT fixed:** eleven test files still build a `Database` inline (listed in the
> profile § *Half B — measured* and on `TODO.md`). ⚠️ **NOT verified:** coverage, `tests/live/`,
> anything live; per-fixture microbenchmarks not re-measured — the wall-clock table is the measurement.

## 2026-09-06 — Fixture-scope sweep, half A landed on main at `e24e6b7` (linear — the `--no-ff` merge was flattened by `git pull --rebase`; six commits, content identical) (branch `fixture-scope-half-a`; NOT deployed — test-only, v93 stays live)

> **Landed 2026-09-06 08:36–08:50 Phoenix.** Opus, hand-made worktree `C:/lcw/bb-fixtures-a` (the first
> build after `.claude/` became a junction — `docs/access/runbook.md` § *Agent worktrees on this machine*),
> 302k tokens / 174 tool calls / 81 min against a 120–180k estimate. The owner's decisions 1, 3, 4 and 5
> from the test-suite measurement pass (`docs/info/test-suite-profile.md`, all answered "Yes" one at a
> time on 2026-09-05): `adeb214` contract seed built once per module and rewound per entry with a
> by-name read guard; `52b9a81` api app + database module-scoped, rewound per test, `fresh_*` chain kept;
> `a5c7a28` the one true duplicate deleted; `a7f6a52` the three assertionless tests assert what they
> were proving; `4c3a4c2` `BB_REVERSE=1` reverses collection (kept as the order guard) and the three leaks
> it found are shut (`web.db = None` from an unreachable-database test, in-place writes to
> `web.settings`, the contract seed's non-row marks); `e24e6b7` docs. **5188 → 5187 tests**, `ruff` clean,
> green forward and reversed on `-n auto` at the gate on main; the agent measured 105.17 s → 52.14 s
> (−50 %) on its machine, the gate here read 88.7 s (v93, throwaway worktree) → 54.4 s. No file under
> `black_bloc/` or `site/` changed, so no deploy line and no mock check.
>
> Where the brief did not survive contact: the 149 contract routes CANNOT share one seed — `contract.json`
> runs mutually exclusive transitions on the same seeded ids (48 of 149 failed built as briefed), and
> splitting them means editing `site/`, off-limits — so the seed is built once and REWOUND from a row copy,
> every route still starting on the seed exactly as written; the accepted independence trade was never
> taken. sqlite `backup` was unusable (37 "destination database is in use" — helpers leave cursors open);
> `take`/`put` on the live connection replaced it. The read guard caught `GET /api/chat/personality`
> writing on a read (fills the trope pool on first read — the seed now takes that first read).
> ⚠️ **Found beyond the brief, NOT fixed:** `tests/cogs/test_presence.py` has two tests
> (`test_reapply_presence_says_so_when_the_status_could_not_be_set`,
> `test_someone_joining_or_leaving_refreshes_the_count_once`) failing under reversed SERIAL collection —
> **the same two fail at v93**, so it pre-dates this branch; the file alone passes both ways (cross-file
> dependence). Handed to half B. ⚠️ **NOT verified:** coverage, `tests/live/`, anything live; decision 2
> (half B) untouched — the 46 cog `db` fixtures are as they were. The 140 pytest warnings are pre-existing
> (v93 throwaway worktree: 140).

## 2026-09-05 — Engineering sweep 3 landed as v93 (merge of `worktree-agent-ab52a6d7c53bc1ecb` at `9fddad1`, deployed `09ff46b`)

> **Landed 2026-09-05 21:49–22:00 Phoenix.** Opus, own worktree, 277k tokens / 198 tool calls / 46 min
> against a 100–150k estimate — the overrun was item 5, briefed as "one loop, 14–26 lines" and measured
> at **143 tracebacks / 1716 stderr lines per deploy**, bisected to `tests/test_selftest_panels.py`'s
> `live` fixture (the only one that connects the database AND loads all 19 cogs, so every `cog_load`
> started a real `tasks.loop` against a never-logged-in client); one `monkeypatch.setattr(tasks.Loop,
> "start", …)` in that fixture takes the whole suite's stderr to **0 lines**. Five items, all closed, six
> commits; **5186 → 5188 tests, none lost**; `ruff check .` clean; mock `17 pages, 149 routes, 14 core
> settings`. Owner sweep rows **295–299** (were `ES3-a`–`ES3-e`); code notes in `docs/info/code-notes.md`
> § *Engineering sweep 3*, keyed by name. Three guards broken on purpose and seen to fail, reverted.
>
> Beyond the brief: `"Keep it"` had **thirteen** sites in twelve modules, not nine (two inline `no=` in
> birthdays, `polls.DELETE_KEEP_BUTTON`, `modmail.SNIPPET_NO_MOVE`) — all `panels.KEEP_IT` now, with an
> AST guard; a sibling guard pins seven library helpers no cog may re-define (`panel_minutes` /
> `site_page_url` / `option_label` excluded on purpose — 13 and 9 modules bind their own key, they are
> the binding not copies); `architecture.md`'s header is ONE measured table (19 cogs, 29 commands, 0
> groups, schema 32, 187 keys, 18 features, 17/149/14) plus a how-the-counts-moved table, the old header
> retired whole to `docs/archive/architecture-header-2026-09-05.md` — the first doc ever retired into
> that folder; **KI-24 filed** (`before_loop` is awaited outside the `try` whose `except` reaches
> `@loop.error`, read from discord.py source, never observed live). Deploy gate: **v92's `.err` had 225
> tracebacks, v93's has 0** (its 217 lines are Docker build progress); the gate's `-n auto` suite ran in
> 87 s against 336 s on `-n 4`.
> ⚠️ **NOT verified at the merge:** nothing met live Discord or the dashboard beyond boot; rows 295–299
> are the owner's. Boot verification is on the v93 line in `deploys.log`.

### Sweep-2 residual bullet, moved whole from `TODO.md` (the four items sweep 3 closed are inside it; the still-open remainder is re-listed there under the same heading)

- **Wave-1 review findings — what is still open after ENGINEERING SWEEP 2 (v92, 2026-09-05; the
  full bullet with the nine closed items moved whole to `DONE.md`, "Engineering sweep 2 landed as
  v92"):** polls' `draft` status is never written (`DRAFT` sits in `STATUSES`/`TRANSITIONS`/`COLOURS`
  but only the in-memory `PollDraft` preview holds it — decide: drop it or make a saved draft real) and
  there is no create-recurrence web route (Discord-only; decide whether the dashboard should get one);
  `architecture.md`'s "current" command counts are stale (a ⚠️ line names the real figures); every
  panel's **Logs** button drops `count` / `important_only` (wave 1 shape — a modal if wanted back);
  **from the wave-3 design docs (2026-09-04):** ~~the website can set `automod_mode=on` past the arming
  refusal~~ — **was ALREADY CLOSED at v84 `675f233`** (`api/settings_api.py:gated_writers` hands
  `automod_mode`, `honeypot_mode`, `honeypot_exempt_role_ids` to the cog's own move) when sweep 2
  carried it forward; struck 2026-09-05 21:05, nothing to do; `rolemenu_log_level`'s registration site was not read
  line-by-line (generated by the log-level family). **New from sweep 2 (report-only):** 13 registry
  keys have no `labels.js` sentence — pinned by name in `tests/test_settings_store.py:NO_LABEL_YET`
  (`birthday_panel_lookup`, `birthday_panel_next_for_members`, `chat_daily_turns`, `chat_llm_mode`,
  `chat_monthly_cap_usd`, `chat_person_hourly_turns`, `chat_personality`, `chat_simple_model`,
  `event_panel_own_list`, `personality_pool_peer_url`, `personality_pool_sync`, `poll_creator_may_end`,
  `request_panel_own_list`) — each needs a sentence someone decides on, then comes off the list;
  `KEEP_IT = "Keep it"` has eight homes (checklist-15 candidate for a `panels.KEEP_IT`);
  `golive.py:db_up` is a byte-for-byte copy of `panels.db_up` — fold at the next golive touch.

## 2026-09-05 — Engineering sweep 2 landed as v92 (merge of `worktree-agent-a979d5d8b2c1fe2f5` at `f866e98`)

> **Landed 2026-09-05 20:35–20:50 Phoenix.** Opus, own worktree, 349k tokens / 287 tool calls / 48 min
> against a 300–450k estimate. Nine items, all closed, twelve commits; **5177 → 5186 tests, none lost**;
> `ruff check .` clean; mock `17 pages, 149 routes, 14 core settings`. Owner sweep rows **287–294**
> (were `ES2-a`–`ES2-h`); code notes in `docs/info/code-notes.md` § *Engineering sweep 2*, keyed by name.
> Every new guard was broken on purpose once and seen to fail (four breakages, each reverted).
>
> What it found beyond the brief: `panels.opened(staff=False)` folded **103** inline defer+db_ready pairs
> across **nine** cogs (`polls` and `golive` were never on the leftover list); **27** re-renders lacked
> `allowed_mentions`, not just `requests.py`'s four (latent — Discord does not resolve mentions inside
> an embed — but checklist 11 now has no exceptions); the three withdraw/cancel cards are on
> `panels.confirm`, six one-off Button classes gone; `events.confirm_cancel` re-asks `may_cancel`
> (`cancel_for` checked the status transition but never ownership); `/birthday set|optout` (6 sites)
> and `/poll create` were the same stale-name class as `/request create` — `tests/test_chat.py` had
> been pinning the bug; three of the four `/role revoke` homes were already fixed by the role-menus
> build; the five double-logged form writes were ALREADY fixed — what was stale was
> `KNOWN_DYNAMIC["api/writes.py::kind"]`, which listed **12 kinds no route writes**, now derived from
> the AST (14 kinds); the via audit found exactly three shared functions without `via` —
> `events.rename_channel`, `polls.post_poll`, `polls.send_review_card` — all consequence rows with no
> actor, so they are a named `VIA_NOT_NEEDED` table with a reason each and a test; the mock already had
> all 18 `*_panel_minutes` labels and `ROLE_MENUS_OFF` no longer drifted (a test now reads the JS
> literal back); the Logs guarantee is `logged == FEATURES` (18) by equality, plus a check that no
> `send_logs` sits under an `app_commands` decorator. `role_menus.py:answer` needed nothing (v88 fold).
> ⚠️ **NOT verified at the merge:** nothing met live Discord or the live dashboard; rows 287–294 are
> the owner's. Boot verification is on the v92 line in `deploys.log`.

### Wave-1 review findings bullet AND the via-labelling gap bullet, moved whole from `TODO.md` (the still-open parts of the first were re-listed there under the same heading; the second is closed: `cancel_train` already took `via`, and the full audit found three functions, all consequence rows, now a named `VIA_NOT_NEEDED` table)

- **Wave-1 review findings, small, fold into the next build that touches each file (Fable
  review 2026-09-03 13:50–14:05):** `requests.py` re-renders lack `allowed_mentions`;
  `LOG_LEVEL_COMMANDS` help still says "`/birthday logs`" / "`/request logs`"; five form writes
  are logged twice (cog and API); `role_menus.py:392` re-implements `panels.answer()`;
  `chat.py:483–488` and `personas.py:75` still say `/request create` / `/request list`
  (`tests/test_chat.py:158` pins it) and `code-notes.md:3451` has the same stale name;
  `NO_ANNOUNCE_CHANNEL` is dead in `events.py`; events `confirm_cancel` Yes button does not
  re-run `may_cancel` (trusts the panel's opener pin); polls: `draft` status never written, no
  create-recurrence web route, (`OWNER_GUIDE.md` polls row added at the v65 landing). From the
  applications build (2026-09-03 14:55): `tests/test_bot.py::test_every_feature_group_has_a_logs_command`
  shrinks with every panel wave (each deletes a `LOGS_GROUPS` entry) — re-express the guarantee
  against the panels' **Logs** button before it covers nothing; `role_menus.py:answer()` is still a
  byte-for-byte copy of `panels.answer`; `architecture.md`'s "current" command counts are stale
  (a ⚠️ line names the real figures); `applications.py:NOT_YOUR_APPLICATION` / `NO_REVIEW_CHANNEL`
  look dead; `OWNER_GUIDE.md` restates the sweeps count (95) instead of linking — two homes for one
  number. From the golive build (2026-09-03 17:05, Fable review): the four earlier `*_panel_minutes`
  keys (event/poll/birthday/request) have no label in `site/public/assets/labels.js` or
  `site/mock/server.mjs` (memory and golive do); every panel's **Logs** button drops `count` /
  `important_only` (wave 1 shape — a modal if wanted back). From the pings build (2026-09-03 18:25,
  Fable review): ~~`pings.panel_buttons` only offers **Take my ping role away** while `pings_mode` is on~~
  **DECIDED (a) + FIXED 2026-09-05 14:35 (owner: "a for pings")** — the drop button renders whenever the
  member holds a role, mode on or off; `pings.py:panel_buttons` + one test, rides with v86; the
  youtube cog keeps its own `site_page_url` (returns `""` where `panels.site_page_url` returns `None`)
  — fold it at the next youtube touch; `code-notes.md` pings keys are anchored to the branch, not
  `a5ad521` — re-key at the next merge. **From the wave-3 design docs (2026-09-04 09:21–09:33,
  REPORT-not-fix until their builds):** the website can set `automod_mode=on` through the generic
  settings API, which validates against `KEY_CHOICES` only — neither arming refusal applies on the web
  path, so a guild with no resolved staff can be armed from the dashboard (`KNOWN_ISSUES` candidate;
  the fix is wiring `set_mode` into the settings route, a settings-API pass, not a panel change);
  `LOG_LEVEL_COMMANDS["pings"] = "pingroles"` (`settings_store.py`) names a wave-2-retired command and
  every other `LOG_LEVEL_COMMANDS` row goes stale as its panel lands — re-express against the Logs
  button; `/role revoke` is named in four places (`applications.py`, `OWNER_GUIDE.md:86`, `sweeps.md:254`,
  `applications-panel-design.md:130`) and has NEVER existed — the role-menus build's `End it now` makes
  it real; `site/mock/server.mjs:63`'s copy of `ROLE_MENUS_OFF` has already drifted from the real string;
  `panels-program.md` §3 undercounts role menus (17 → 18); `rolemenu_log_level`'s registration site was
  not read line-by-line (generated by the log-level family) — the build confirms it.

- **Via-labelling gap: `raidtrain.cancel_train` logs one row but calls a website cancel
  Via = Discord** (found by the double-logging build, 2026-09-03 — see `DONE.md` that
  date). Not a double post, so out of that fix's scope. Audit every shared function a
  route calls that does NOT yet take `via` (start from the `kind_via` call sites and the
  `tests/test_logkinds.py` AST walk's `SHARED` map), thread `via=` through, and add each
  to `tests/api/conftest.py:one_web_row`. Small; fold into the next requests/raid-train
  build rather than dispatching on its own.

## 2026-09-05 19:50 — Member requests review: closed, every request already dispositioned

> Moved whole from `TODO.md` at the v91 landing. Nothing was left to review: #1 (raid trains) shipped as
> Phases 17–19 and Pawpette marked it done; #2 (Twitch Team form) shipped as `/apply` (v66) and was
> exercised and approved by Pawpette; #3 (music bot) is on `hold` by the owner's 2026-09-03 14:22 call
> (Spotify cannot be a source); #4 was a test. The Requests page shows the same four states. The item as it
> stood:

- **Review the incoming member requests (owner, 2026-09-02 ~19:55: "we got some
  request in our /request features lets review them").** Read what has landed
  via `/request` (Requests page, `/api/requests`), present them to the owner one
  at a time, record each decision (accept → a TODO item; decline → the reason)
  and close them out on the Requests page. **Live read 2026-09-03 14:25 (`requests` table via
  `flyctl ssh`, owner-authorised): #1 done (Pawpette marked it), #2 review (→ done when `/apply`
  ships, v66), #3 hold (Spotify skipped 14:22), #4 "Do" done (a test).** Three in (all staff-filed →
  auto-approved, unassigned): #1 Pawpette — raid-train scheduler replacing
  r3dlabs.com (owner: "can we capture all the features of this tool" →
  [`info/raid-train-capture.md`](info/raid-train-capture.md), full inventory
  bucketed); #2 Pawpette — Twitch Team application form via the bot, staff
  approval; #3 PT — built-in music bot for the lounge/cowork voice channels.

## 2026-09-05 — Personality pool, both halves LIVE (Black Bloc v90 `7c59eb1` + v91 `604226f`; GABI `de4ef63`, deployment `755cfd54`); KI-23 closed

> **Landed 2026-09-05 19:33–19:45 Phoenix.** GABI's half (catalog-platform `feature/personality-pool`,
> Opus, 186k against an 80–120k estimate) was rebased onto that repo's main, deployed by the owner
> himself (`755cfd54`, 13 s after the session's identical `519eb2c8`), and fast-forwarded onto
> catalog-platform `main` as `cb4f779`. Verified live: `GET https://discord.heygabi.ai/api/health` →
> `gabi_personality_pool_version: 1` and the eleven tropes in the manifest's order. Black Bloc then
> re-synced (`synced_from: catalog-platform@de4ef63` — the first sync that ever succeeded) and shipped
> **v91** `604226f`: `check_pool` compares GABI's roster BY NAME, IN ORDER (the first cut did `int()` on
> an array — it would have raised the moment she answered); `sync_personality_pool.py` stamps the main
> checkout's name from `--git-common-dir` (a worktree stamped `pool@sha`) and copies the canonical's
> bytes plus one key, so the two files differ by the `synced_from` line only. v91 boot: `selftest: 107 ok,
> 0 failed` with GABI answering, so `pool.in_step_with_gabi` ran the compare path and passed.
> ⚠️ **NOT verified:** the check's exact sentence (*"GABI lists the same 11, in the same order"*) — the
> log row lives behind Discord sign-in and `fly ssh` was refused, so it is inferred from 107/0 plus the
> live health read; sweep row 284 is the owner's by-eye read of it. Nobody has talked to GABI since
> (voice byte-identical by design, §5.1).

### KI-23, moved whole from `KNOWN_ISSUES.md` (closed: both numbers it named arrived — the health field answers `1`, the sync script exits 0)

## KI-23 — The shared personality manifest has no canonical to sync from yet — `BLOCKED`

**Symptom.** `black_bloc/personality_pool.json` is **hand-built from GABI's
`personality.ts`**, and `python scripts/sync_personality_pool.py` exits 1 every time with
*"the canonical personality manifest is not at …"*. The canonical file
(`catalog-platform/apps/discord-worker/src/personality-pool.json`) does not exist: the GABI
half of `info/personality-pool-design.md` §5.1 is a later build. The self-test check
`pool.in_step_with_gabi` therefore reports *"GABI does not say its pool version yet"* — a
pass, not a comparison — so **nothing is actually verifying that the two bots' rosters agree**
today. Added 2026-09-05 by the Black Bloc half's own build, from its own state, not an
incident.

**Status:** `BLOCKED` — on the GABI half.

**Why tolerated.** It is the landing order the design chose on purpose (§8): Black Bloc first,
so no order of shipping can produce a red self-test. The two rosters were **measured identical
this session** — eleven names in the same order, the same graph, the same drift constants —
so the drift being unmonitored is a risk about the future, not a defect today. The refusal is
loud (exit 1, a sentence naming the fix), which is what the CLI-quirk rule asks for; the
failure mode this entry rules out is a script that prints success over a stale copy.

**What would change it:** the GABI half landing. Concretely, **two numbers**:
`GET https://discord.heygabi.ai/api/health` answering `gabi_personality_pool_version`, and
`scripts/sync_personality_pool.py` exiting **0**. On that day, run step 5 of
[`access/personality-pool.md`](access/personality-pool.md) and this entry closes.

### TODO item 4, moved whole

4. **Global personality pool** — one trope store shared across estate bots
   (Black Bloc's `personality_tropes` + GABI's `personality.ts` unify). This is
   an ESTATE design spanning two repos: design doc first, likely a small shared
   store + sync convention; coordinate with catalog-platform docs.
   **DESIGN WRITTEN 2026-09-05 16:5x** → [`info/personality-pool-design.md`](info/personality-pool-design.md):
   share the SKELETON (roster, graph, drift constants, clause templates in one
   canonical `personality-pool.json` in catalog-platform), keep the SKIN (each
   bot's voice bodies); Black Bloc boot SYNC (never touches staff's `enabled`),
   two settings, health field, one self-test check that reads GABI's health
   route so drift is visible. Measured today: roster + graph identical, voices
   deliberately different, `personality.ts` untouched since the port. Forks
   F-P1–F-P3 ✅ ALL DECIDED (a) by the owner 16:41–16:43 — READY TO BUILD once
   v88/v89 land (all touch nearby files). Two Opus builds:
   Black Bloc half (est. 150–220k) THEN GABI half (80–120k). ⚠️ The
   catalog-platform TODO pointer is NOT yet written — that tree was in use by
   another session at 16:37 (`821cd26` + a dirty `deploys.log`); the GABI-half
   brief carries it.
   **Black Bloc half ✅ LIVE as v90 `7c59eb1` 2026-09-05 19:00** (288k; selftest 107 ok, `/health` says `personality_pool_version: 1`) — manifest + derived `personas.py` + `sync_tropes`/`sync_pool` +
   two core settings + `/health` field + `pool.in_step_with_gabi` self-test check +
   `scripts/sync_personality_pool.py` + runbook [`access/personality-pool.md`](access/personality-pool.md)
   + sweep rows 280–286. Schema unchanged at 32. GABI half still to build.
   **GABI half ✅ LIVE 2026-09-05 19:33** (catalog-platform `de4ef63`, deployment `755cfd54`, main
   `cb4f779`; 1247 → 1260 tests, typecheck clean). **Black Bloc v91 `604226f` 19:38** closes the loop
   (roster compare by name, byte-for-byte sync). Design's §8 landing order held: no order of shipping
   produced a red self-test.

## 2026-09-05 — Engineering sweep landed as v89 (merge of `worktree-agent-accb69989b295c889` at `243dc0f`)

Outcome: seven commits, 481k tokens (estimate was 250–350k). KI-21 closed (its own entry is below this one, written on the branch); schema **32** adds `action_log_by_kind (guild_id, kind, id)` and `checks_of` filters `run_id` in SQL (5,300 → 106 rows parsed; 8.5 → 3.1 ms at 55k rows, ⚠️ 3.4 → 4.2 ms at 5.3k — the bigger measurement decided it); a check-runner that RAISES now records itself (`selftest.finish_quietly`); the operator-log toggle re-asks Manage Server; the mock's `contract.json` gains a `settings` block read by both `tests/api/test_contract.py` and `check.mjs` (14 false `max: 1440` claims removed per KI-20, `youtube_poll_minutes` `min: 5`, 16 registry keys that had no mock row); `test_every_log_level_names_a_command_that_still_exists` guards `LOG_LEVEL_COMMANDS` by name. Sweep rows 276–279 (were `ES1`–`ES4`). Verified at the landing: ruff clean, **5139** passed, `check.mjs` ok (17 pages / 149 routes / 12 core settings), boot 01:16:08Z `synced 29`, `selftest: 106 ok, 0 failed` 01:16:34Z, no traceback. **NOT verified:** nothing on the live dashboard or by a person in Discord — rows 276–279 are unswept. The two `TODO.md` items that closed whole, moved as they stood (B1–B4 and A1–A2 are struck inside their still-open parent items and stay there):

- ~~🔧 **`LOG_LEVEL_COMMANDS` is stale for eight features (report from the automod build, 2026-09-04):**
  `settings_store.py` still names `tempvoice` (now `voice`), `events` (now `event`), `poll`, `birthday`,
  `golive`, `request`, `applications` (now `/apply`) and `pings` (`pingroles`, retired) as the command that
  reads each log level — every one of those became a panel's **Logs** button. One pass: re-express the help
  text against the Logs button per feature and re-express
  `tests/test_bot.py::test_every_feature_group_has_a_logs_command` (already on the small-findings list) against
  the same thing before it covers nothing.~~ **ALREADY DONE, then GUARDED `83920bc`.** ⚠️ **Both halves had
  already landed and this item was stale:** the v84 (`/settings` panel) build corrected `LOG_LEVEL_COMMANDS`
  for all eighteen features and rewrote `log_level_help` to say "`/<command>` ▸ **Logs**", and the same build
  re-expressed the test as
  `tests/test_bot.py::test_every_features_logs_is_a_panel_button_and_no_group_is_left_to_hold_one`. Verified by
  reading the code, not assumed. What this sweep added is the guard that stops it happening a ninth time:
  `test_every_log_level_names_a_command_that_still_exists` loads the whole tree and fails **by name** on any
  row of `LOG_LEVEL_COMMANDS` that names a command Discord no longer has. Sweep row 279.
- ~~🔧 **Settings-API gate pass (KI-21, 2026-09-04):** the generic PUT in `api/settings_api.py` validates
  against `KEY_CHOICES` only, so the website can set `automod_mode=on` past both of the panel's arming
  refusals. Route the write through `cogs/moderation/automod.py:set_mode` with `via=website` (the youtube and
  pings routes already call their cog's shared moves), then audit every other key that has a cog-side gate
  for the same gap.~~ **DONE `675f233` + `49370a6`** — see the `/settings` leftovers item above. ⚠️ **One
  premise in this item was wrong and is worth recording:** *no* route called a cog's `set_mode` before this
  build. The youtube and pings routes call their cog's shared moves for **link / unlink / setup**, never for a
  mode — every mode in the app was written through the generic settings PUT, which is exactly why the gap
  existed. Audit result: `automod_mode`, `honeypot_mode` and `honeypot_exempt_role_ids` are the only three
  writes with a cog-side gate; the other sixteen `*_mode` keys have nothing to share.

## 2026-09-05 — Confirm/opened fold (v88, merge of `worktree-agent-a1f44401815e31ccf` at `794d3aa`)

Outcome: one `panels.confirm` card builder + `confirm_items` (with `yes_style`, because role menus' seed confirm is blue on purpose) + `panels.opened(interaction, *, staff=True)`; 8 confirm copies (11 cards — the survey found an eighth in `tempvoice.py` the item never listed) and 7 `opened()` copies + chat's 14 inline triplets folded; 12 one-off Button classes and 5 `CONFIRM_TITLE` constants gone; 5110 → 5122 tests; 12 commits; agent cost 309k against a 150–250k estimate. Deployed 17:33, boot verified (`synced 29`, `selftest: 106 ok, 0 failed`). Left on purpose: the three withdraw/cancel cards (events, requests, applications) — different shape and they edit without `allowed_mentions`; they fold once that small finding lands. Still open (reported, not done): the staffless `defer`+`db_ready` pair inline in seven cogs. Sweep rows 262–275 are the owner's check-out. The item as it stood:

- 🔧 **Confirm-helper fold — BUILT 2026-09-05 on `worktree-agent-a1f44401815e31ccf`, NOT merged, NOT deployed.**
  Two helpers landed in `black_bloc/panels.py` with 11 new tests in `tests/test_panels.py` (`9cb96ea`):
  `confirm(interaction, view, embed, items, previous, *, question, title)` with `confirm_items(...)` /
  `ConfirmButton`, and `opened(interaction, *, staff=True)`. **5110 tests before, 5122 after; ruff clean;
  no behaviour change** (no test changed an assertion). Checklist 15/17.
  **The confirm copies:**
  ~~`cogs/content/chat_memory.py:open_confirm`~~ `0597087` ·
  ~~`cogs/community/birthdays.py:open_confirm` (+ its six Button classes, three call sites)~~ `17dc187` ·
  ~~`cogs/content/youtube.py:open_confirm`~~ `4a56e2e` ·
  ~~`cogs/content/pings.py:open_confirm` + `open_card_confirm`~~ `5bd9978` ·
  ~~`cogs/moderation/automod.py:build_confirm`/`open_confirm`~~ `863a58c` (the pure
  `black_bloc/automod.py:confirm_buttons` stays — it is the move TABLE, not a copy of the card) ·
  ~~`cogs/content/chat.py` `RemoveYesButton`/`KeepItButton`~~ `3438d4d` ·
  ~~`cogs/community/role_menus.py:confirm`~~ `5508e9f` (what is left is `confirm_panel`, which only carries
  the previous card's place) · ~~`cogs/community/tempvoice.py:build_forget_confirm`~~ `714a04c` — an
  **EIGHTH copy this item never listed**, found by the survey.
  **LEFT, on purpose — `cogs/community/events.py:open_cancel_confirm`, `cogs/community/requests.py:open_withdraw_confirm`
  and `cogs/community/applications.py`'s withdraw card.** They are a different shape (the card IS the question,
  no `Are you sure?` field, and the Yes button carries the row id), and all three edit **without
  `allowed_mentions`** where `panels.confirm` always passes `AllowedMentions.none()` — folding them would have
  been a behaviour change inside a refactor. They fold trivially once the standing small finding
  "`requests.py` re-renders lack `allowed_mentions`" (above) lands: `question=""` and one `confirm_items` each.
  **The `opened` copies:** ~~`cogs/core.py`~~ ~~`cogs/moderation/automod.py`~~ ~~`.../honeypot.py`~~
  ~~`.../modcmds.py`~~ ~~`.../modmail.py`~~ ~~`cogs/community/role_menus.py:ready` (renamed at 27 call sites)~~
  all `7d1ddfd`; ~~the 14 inline repeats in `cogs/content/chat.py`~~ `5b20bed`.
  `cogs/content/raidtrain.py:opened` KEPT as a one-line delegation to `panel_opened(..., staff=False)` rather
  than adding the keyword at ~30 call sites — the triplet itself is gone.
  **Still open, reported not done:** the `defer` + `db_ready` PAIR (the same triplet with no staff gate) is
  still written inline in `chat_memory.py`, `youtube.py`, `pings.py`, `birthdays.py`, `events.py`,
  `requests.py` and `applications.py` — `opened(interaction, staff=False)` covers it, but it was outside
  this sweep's brief. Docs landed with the work: `code-notes.md` § *Confirm/opened fold* (five notes above
  re-keyed), `panels-program.md` §4 *What the library gained after wave 0*, `access/sweeps.md` rows
  rows 262–275 (were `CF1`–`CF14`). ⚠️ **Nothing was run against live Discord and `python -m black_bloc` was not booted**
  (no token in a worktree); the sweep rows are the check-out.
## 2026-09-05 — KI-21 closed: the website gets the SAME verdict the panel does (engineering sweep, `worktree-agent-accb69989b295c889`, NOT yet merged)

**Outcome.** Two commits. **(1)** `PUT`/`DELETE /api/settings/{key}` now write through
`cogs/core.py:set_key` / `clear_key` with `via=VIA_WEBSITE` and note nothing of their own; the
shared writers build the head with `logkinds.kind_via`, so the kinds on the wire
(`web.settings.set` / `web.settings.clear`) are unchanged and the audit reader needed no edit.
The one behaviour kept by hand: `clear_key` refuses a key with no stored row (409
`nothing_stored`) where the route has always answered 200 with `cleared: false`, and the page
reads that flag — so that one code stays a 200 and every other refusal is raised.
**(2)** The gate pass. `api/settings_api.py:gated_writers()` is a table of the keys a cog
guards; the `PUT` validates with `coerce_value` and then hands the write to the cog's own move
instead of `set_key`. **Audited 2026-09-05 against every `*_mode` key in the registry** (and every
list key with a cog-side move): `automod_mode` → `automod.set_mode`, `honeypot_mode` →
`honeypot.set_mode`, `honeypot_exempt_role_ids` → `honeypot.set_exempt_roles`. **Those three are
the only writes in the app with a cog-side gate** — `golive`, `youtube`, `pings`, `tempvoice`,
`events`, `birthday`, `poll`, `request`, `chat`, `chat_llm`, `chat_memory`, `rolemenu`,
`raidtrain`, `applications`, `modmail` and `modmail_enabled` each have a `set_mode` that writes
and logs with no verdict to share, so they go through `set_key` exactly as before.
`automod.set_mode` was changed to return an `Outcome` (honeypot's shape already) so the website
can tell a refusal from a save; its one panel caller reads `outcome.message`. **NOT verified:**
nothing here has been exercised against the live dashboard. Review, once it lands:
https://blackbloc.heygabi.ai/automod.html (Mode → **on** while the staff channel is the test
channel now refuses in a sentence) and https://blackbloc.heygabi.ai/honeypot.html (same, and the
exempt-roles editor now leaves a `web.honeypot.exempt_set` row on
https://blackbloc.heygabi.ai/audit.html#logs). The entry, moved WHOLE out of `KNOWN_ISSUES.md`:

### KI-21 — The website can arm automod (and the honeypot) past the arming refusals — `ACCEPTED`

**Symptom.** `/automod` (the wave-3 panel, v74) never offers `on` while `staff_channel_id` is
still the test channel or the guild resolves no staff role, and `set_mode` refuses the same two
ways (`cogs/moderation/automod.py:arming_refusal`, read by both the select and the verdict). The
dashboard's Automod page flips the same key through the generic settings route
(`api/settings_api.py`), which validates against `KEY_CHOICES` only — `on` is a listed choice, so
the PUT lands, `automod_mode` becomes `on`, and a guild with no reachable staff channel or staff
role is armed from the website with neither refusal consulted. Found by the design doc's read of the
route (2026-09-04), not by an incident. **Widened 2026-09-05 (v79):** `/honeypot`'s panel has the same
shape — `on` is absent from its mode picker while no staff role resolves and
`cogs/moderation/honeypot.py:arming_refusal` refuses it — and the dashboard writes `honeypot_mode`
through the same generic route, so the trap can be armed from the website with nobody exempt. The
route also rewrites `honeypot_exempt_role_ids` directly, so a website edit of the exempt list leaves
**no `honeypot.exempt_set` row at all**, where the panel's one write leaves exactly one.

**Why tolerated.** The route is behind the dashboard's staff sign-in, so the person doing it is
already staff; the two refusals exist to stop a *misconfigured* guild going live, not a hostile one,
and the misconfiguration they guard (staff channel = test channel) is the TEST_MODE posture the owner
is running on purpose. Fixing it is a settings-API pass (route `set_mode` through the cog's own
function so the web door and the Discord door share one verdict, then the same for every other key
with a cog-side gate), not a panel change, and it belongs with the `LOG_LEVEL_COMMANDS` and
confirm-helper sweeps rather than in the wave-3 landings.

**What would change it.** The settings-API pass on `TODO.md` (wire `automod_mode` and `honeypot_mode`
writes through each cog's `set_mode`, and `honeypot_exempt_role_ids` through `set_exempt_roles`, all
with `via=website`), or **1 report** of a guild armed from the website while the Discord panel was
refusing — today's number is **0**.

## 2026-09-05 — The self-test (wave 5): the bot proving itself at every boot, and cleaning up after itself (v86, merge of `worktree-agent-a4aa5efd43f249ba6` + `abac65d` + `ad5b614`)

**Outcome (Fable review + merge 2026-09-05 15:15, deployed ~15:35):** `black_bloc/selftest.py` — a `Check` registry
(`config.<key>` 35 · `panel.<command>` 18 · `read.<path>` 47 · `send.<feature>` 6 = **106 checks, 24 real messages**)
on ONE `run()` = `begin()` + `finish()`, three doors (boot line `selftest: N ok, M failed, K messages posted (purge in
5 min)`; `/settings` ▸ **Self-test…** with Run / Purge now / Logs; `POST /api/selftest` staff-only + `GET` list/one +
`POST …/purge`), tables `selftest_runs` + `selftest_messages` (schema 30 → 31, additive), `purge_loop` every 60 s
deleting every posted message after `selftest_purge_minutes` (5; boot purges leftovers FIRST), log feature **Test**
(`selftest.*`, level `off`, excluded from the Logs page's default view via `default_view_clause`, shown under the
**Test** chip), Health-page card, four `core` keys (`selftest_on_boot` true · `selftest_channel_id` = the test channel ·
`selftest_purge_minutes` 1–1440 · `selftest_log_level`), `tests/live/` (`-m live`, env NAMES `BLACK_BLOC_LIVE_URL` /
`BLACK_BLOC_LIVE_TOKEN` / `BLACK_BLOC_LIVE_SESSION`), `docs/access/testing.md`. Tree stays 29 / zero Groups.
Deviations, all recorded in the design's `## Build deviations` foot: 18 panels not 29 (eleven commands open no
panel); `read.*` walks the app's own route table because `contract.json` is not in the Docker image; the operator
token reads the door but cannot start a run; and a real defect fixed on the way — an unknown `/api` path answered
Starlette's bare `{"detail": "Not Found"}`, now a sentence. `guard.py` RAISES on a non-test channel, so a mis-pointed
`selftest_channel_id` fails its check in words and nothing is misrecorded. **One defect the deploy's own suite run
caught** (1 in ~2 full runs): `finish()` cleared the busy flag only in its `finally`, after the `selftest.finished`
row was logged, so a `GET` in that gap saw `finished_at` set and `running: true` — the flag now clears in the same
breath as `close_run` (`ad5b614`). Rides along: pings fork (a) (`fcc4523` — **Take my ping role away** renders
whenever the member holds a role, mode on or off). Sweep rows **252–261** (`ST1`–`ST10`); owner-guide row **Make the
bot test itself**. Agent cost **515k** (est. 300–450k). 5109 tests. Also landed in this entry: the owner walked
sweeps **232–251** by eye and the Logs page on a phone 2026-09-05 15:19 (verbatim "1 and 2 are good"), nothing
reported wrong. **NOT verified:** no person has run it; `tests/live/` has never hit the deployed host
(`OPERATOR_READ_TOKEN` is not set on Fly); the boot line is the one live measurement, in `deploys.log`: **the first live run said `104 ok, 2 failed, 24 messages posted`** — both failures were the READ CHECK being wrong about lookups (`/api/ref/names` answers `{}` for no ids; `/api/applications/roster` refuses in words for no form), fixed the same hour as **v87** (`_takes_a_query`: a lookup answering nothing, or refusing in words, for nothing picked passes). Review:
https://blackbloc.heygabi.ai/health.html#sect-selftest · https://blackbloc.heygabi.ai/audit.html#logs (**Test** chip) ·
`/settings` ▸ **Self-test…** in `#mute-me-bot-test-spam`. The two items, moved WHOLE:

- ✅ **DECIDED 2026-09-05 14:02 — owner: "do a but after 5 minutes purge the discord chat of all test,
  keep the logs on the website tho under test"** → option (a) + a five-minute purge of every message the
  test posts + a **Test** view on the website's Logs page. Design: [`info/selftest-design.md`](info/selftest-design.md).
  **BUILDING** — see the engineering item below. Original: **Owner 2026-09-05 13:52, verbatim: "test it all, can we build api test and endpoints"** — logged the
  moment it was said; ONE clarifying question asked 13:56. Conductor's reading, proposed
  as the recommended option: a **self-test door** (`POST /api/selftest` for staff + `/settings` ▸ **Run
  the self-test**, and the same check at every boot logging one line) that, inside the running bot and
  against the REAL guild, renders every panel's root card, runs every dashboard read, and checks every
  configured channel/role still resolves with the permissions each feature needs — sending nothing; plus
  a **`tests/live/`** pytest suite against the deployed API (skipped unless `BLACK_BLOC_LIVE_URL` and the
  operator token's env NAME are set) that round-trips every route on marked test records. What no API
  can do: synthesise a Discord click — button/modal handlers stay under the 5002 pytest fakes; only the
  layout in the Discord client needs a person. Waiting on the owner's answer before designing.

- 🔧 **Self-test + `tests/live/` (owner 2026-09-05 13:52 → decided 14:02, design `info/selftest-design.md`):** `black_bloc/selftest.py` registry of checks (config keys resolve with permissions · every one of the 29 panels' root cards posted live · every website GET in-process · scheduled senders' embeds), three doors on ONE `run()` (boot log line `selftest: N ok, M failed`, `/settings` ▸ **Run the self-test**, `POST /api/selftest` + `GET` list/one + `POST …/purge`), `selftest_runs` + `selftest_messages` tables (schema 30 → 31), `purge_loop` deleting every posted message after `selftest_purge_minutes` (default 5; boot tick purges leftovers first), log feature **Test** (`selftest.*` kinds, level default off, EXCLUDED from the Logs page's default view, shown under the **Test** filter), Health-page Self-test card with a Run button, settings keys `selftest_on_boot` / `selftest_channel_id` / `selftest_purge_minutes` (core group, both doors), mock routes + check.mjs, `tests/live/` (`-m live`, skipped without `BLACK_BLOC_LIVE_URL` + `BLACK_BLOC_LIVE_TOKEN`), `docs/access/testing.md`. No new command — tree stays 29 / zero Groups. Sweep rows `ST1`–`STn`, numbered at the merge after the `ML` rows. **DISPATCHED 14:03 2026-09-05** (Opus, own worktree off `main`; est. 300–450k — a multi-layer build; commit at clean boundaries in the order engine → doors → website → panel wiring → live suite). Usage before dispatch session 32% / weekly 23% / Fable 21%, read 14:02.

## 2026-09-05 — Modmail follow-up: **A ticket…** and the ticket card ON the panel, plus the Logs page on a phone (v85, merge of `worktree-agent-ad2fc0f5aad473c19` + `430114c`)

**Outcome (Fable review + merge 2026-09-05 ~14:40):** all seven leftovers landed — `picked_values` has ONE home
(`panels.py`), the four dead leftovers are gone, `_card_later` writes a `modmail.card_failed` row when the sticky
card's background move raises, and the `/modmail` root carries **A ticket…** (row 0, only with ≥1 open ticket) whose
card is the SAME `card_embed()` the sticky card uses over **Reply · Reply as Staff · Private note · Close… · Back**.
The four card moves take an optional `previous` so the panel's copy redraws in place and the channel card stays the
refresher's. Sweep rows 245–251 (`ML1`–`ML7`); design doc re-keyed. Agent cost 316k (est. 80–120k). 5020 tests.
The Logs page fix (`430114c`) rides along: at ≤900px each `.log-table` row becomes a labelled card via
`td::before { content: attr(data-label) }` (label written by the shared `table()` builder in `ui.js`), the topbar
sheds the kbd hint and user name at ≤700px; desktop untouched (verified in an emulated 390px iframe against the
mock, desktop pixel-identical). Review: `/modmail` → **A ticket…** in `#mute-me-bot-test-spam`;
https://blackbloc.heygabi.ai/audit.html on a phone. The two items, moved WHOLE:

- 🔧 **Logs page on mobile (owner 2026-09-05 14:10, verbatim: "check the audit page, it doesn't line up well on mobile but make sure it lines up well on web"):** `site/public/audit.html` + `assets/logs.js` / `site.css` — measure at a phone width, fix the mobile layout without moving the desktop one. Fable, main loop (CSS only; the self-test build touches `audit.html` for the Test filter, so keep the change in `site.css` to avoid a conflict).
- 🔧 **Modmail leftovers after Build B (handed over at the v82 landing, 2026-09-05):** (1) **the panel-side `A ticket…`
  select / ticket card** in the `/modmail` panel (`docs/info/modmail-panel-design.md` §B S5, §C) is UNBUILT — it fell between
  Build A and Build B; a small Opus follow-up (est. 80–120k) once `/settings` lands; (2) `picked_values` has two copies
  (`polls.py`, `black_bloc/modmail.py`) — one home in `panels.py`; (3) `NO_CATEGORY`/`NOT_A_CATEGORY` are dead strings in
  `cogs/moderation/modmail.py`; (4) `Modmail._post_transcript` / `_remove_place` are unreferenced Build-A wrappers;
  (5) an exception inside `refresh_card` is WARNING-logged with no `modmail.card_failed` row (silent failure ≠ success,
  checklist); (6) re-key the design doc's `path:line` anchors for `modmail.py`; (7) the card's 2 s/8 s debounce has never
  been measured against a real channel — sweep 222 is the measurement.
  **DISPATCHED 13:50 2026-09-05** (Opus, own worktree off `6212380`; all seven items in scope, sweep rows lettered
  `ML1`–`MLn`, numbered after 244 at the merge; est. 80–120k, expect ~200k). Usage before dispatch session 24% /
  weekly 22% / Fable 20%, read 13:48.

## 2026-09-05 — `/settings` panel: the LAST panel; `/settings show|set|set-role|set-value|clear` and the `presence` Group retire — 29 slots, ZERO Groups (Build 1 v83 `57a878d`, Build 2 v84 `ce97de0`)

Moved WHOLE from `TODO.md` at the Build 2 landing (13:45). Build 1 on `worktree-agent-a3e6ccbead5a90537` (Opus, 349k,
merged `9a7c87e`, v83 12:53); Build 2 on `worktree-agent-a56c7b5137d9a609d` (Opus, 411k, four commits off `57a878d`,
merged `ce97de0`, v84 13:44, boot 20:44:37Z `synced 29`). Design: `docs/info/settings-panel-design.md`; sweeps
231–244; forks F-S1–F-S5 all (a), decided by the conductor under the owner's "keep going with queue, don't wait for
me" (10:31). **This closes the panels program**: every feature is one command opening a panel and the tree holds no
`app_commands.Group`. Nothing exercised in Discord by a person. Leftovers stayed on `TODO.md` as "`/settings`
leftovers after Build 2".

Also recorded the same afternoon: **Pawpette exercised the Twitch Team application form and approved it** (owner,
13:45: "she did a test and approved it") — the first rows of the applications feature run by a person (sweeps 53–57).

- 🆕 **`/settings` panel — the LAST panel, retires the last two Groups (owner, 2026-09-05 06:46 "Okay ship both with
  your suggestions"; design `info/settings-panel-design.md`, landed 07:34, keyed against `0304c4d`).** End state
  **29 slots, ZERO groups**: the `settings` Group and its five subcommands (`show`, `set-value`, `set-channel`,
  `set-role`, `clear`) become one staff-only panel; the `presence` Group folds in as `How Black Bloc looks…`.
  Est. 380–450k Opus, SPLIT: Build 1 = `black_bloc/settings_panel.py` + tests, the `namespace_of` move,
  `set_key`/`clear_key`/`reapply_presence`, the two registry keys (150–190k); Build 2 = the panel, the `/presence`
  retirement, `tests/cogs/test_core.py`'s settings half, the string + doc sweep (230–280k), off Build 1's merge.
  **Forks F-S1–F-S5 DECIDED by the conductor on the design's recommendation, all (a), 2026-09-05 12:04, under the
  owner's standing order (10:31: "Keep going with queue don't wait for me")** — each reverses in one place, the
  owner may reverse any of them by eye: F-S1 `set-value` does NOT survive (all five go in one commit); F-S2
  `Put the default back` confirms on `staff_channel_id` only; F-S3 the four core channel/role keys +
  `operator_read_log` need `manage_guild`, behind new bool `settings_core_keys_admin_only` (default true);
  F-S4 presence lives on `/settings`, `presence` Group retires; F-S5 a `Log levels…` sub-panel over the 17
  `<feature>_log_level` keys. The design's five REPORTED defects fold into the build (no subcommand checks the db;
  `sweeps.md` row 16 names a `/settings logs` that never existed; code-notes says the clearable list is 11 — it is 34;
  `LOG_LEVEL_COMMANDS` wrong in 11 of 13 rows; `namespace_of`'s six singleton groups — report, one rename pass of
  its own). ⚠️ The design was keyed against `0304c4d` (tree 36); `main` is now `cad3bbc` (tree **30**, schema 30,
  4739 tests, sweeps to 230) — the build re-measures every `path:line` and pins **29**, not the doc's numbers.
  **Honeypot forks F-H1/F-H2/F-H3 (built as (a) at v79, "owner confirmation pending") are CONFIRMED as built by
  the conductor under the same order, 12:04** — the reversal recipe stays in `info/honeypot-panel-design.md` §K.
  **Build 1 DISPATCHED 12:08** (Opus, own worktree off `34331ec`; pure module + tests, `namespace_of` move, shared
  writers, two registry keys; est. 150–190k). Usage before dispatch session 2% / weekly 17% / Fable 17%, read 12:07
  (the session reset had landed). Build 2 dispatches off Build 1's merge.
  ⚠️ **BUILD 1 IS BUILT — not merged, not deployed, nothing has met live Discord.**
  `worktree-agent-a3e6ccbead5a90537`, rebased onto `01c4ed3`, five commits: the `namespace_of` move into
  `settings_store` (`tests/api/test_settings_api.py` byte-identical and green — the proof); the two registry keys with
  their `labels.js` + mock rows and store tests; `black_bloc/settings_panel.py` + `tests/test_settings_panel.py`
  (221 tests); `set_key`/`clear_key`/`reapply_presence` + the new `SettingsStore.is_stored`; docs.
  **4973 tests pass** (4739 before, +234), ruff clean, mock **17 pages / 146 routes unchanged**, labels.js parses.
  **Nothing was retired — top-level stays 30, measured.** ⚠️ **The design's counts were stale and are now corrected in
  its foot:** the registry is **179** keys (the doc says 175) and `tests/test_bot.py` pins **30** (the doc says 36), so
  Build 2 pins **29** off 30. Thirteen deviations, three MORE reported-not-fixed defects (the mock's phantom
  `max: 1440` on every `*_panel_minutes` row; the mock's `CORE_KEYS` being three entries where the API has six;
  `birthdays.py:428` emitting `settings.clear` with no `via`) and two website-only sweep rows (`SB1`, `SB2`) are in
  `info/settings-panel-design.md` → `## Build 1 deviations`. ⚠️ **All twelve of §H's sweep rows S1–S12 belong to
  Build 2** — Build 1 changes nothing a person sees in Discord.
  **Build 1 LANDED 12:50 (349k Opus): merged clean as `9a7c87e`; the wall-clock race it surfaced in
  `tests/api/test_writes.py::drain_reads` fixed on `main` (`57a878d`, drained against a clock a minute ahead);
  4973 tests; v83 LIVE 12:53 (`57a878d`, boot 19:53:32Z, `synced 30`).** Build 2 DISPATCHED 12:51 off `57a878d`
  (usage before dispatch session 5% / weekly 18% / Fable 17%, read 12:47).
  **Build 2 LANDED 13:45 (411k Opus — est. 230–280k, the ~1.5–2× pattern again): four commits, 31 files, +2046/−528;
  merged clean as `ce97de0` (no conflicts); 5002 tests, ruff clean, mock 17/146; `S1`–`S12` numbered **231–242**
  and Build 1's `SB1`/`SB2` copied into `sweeps.md` as **243–244**; guide count 230 → 244. Fable review: every write
  goes through `set_key`/`clear_key` (one write, one row), every move re-asks staff + db, the core-key picks re-ask
  `manage_guild` at the move, refusals are sentences. Sixteen deviations in the design's `## Build 2 deviations`
  foot — notably the layer-1/2 split was not expressible (a tree cannot hold a Group and a command both named
  `settings`), `test_command_visibility.py` needed a real edit (it imported the deleted `VALUE_KEYS`),
  `LOGS_GROUPS` was already `{}` so `test_every_feature_group_has_a_logs_command` had been asserting nothing, and
  `panels-program.md` / `feature-list.md` were left stale (own 🔧 item below).
  **v84 LIVE 13:44 (`ce97de0`)** — boot 20:44:37Z database ready, **`synced 29`**, no traceback; nothing opened in
  Discord by a person. **The panels program's end state is reached: 29 slots, zero `app_commands.Group`s.**
  This item moves WHOLE to `DONE.md`.

## 2026-09-05 — Second slash-command audit: every command listed, six merge proposals decided one at a time

Moved WHOLE from `TODO.md` 12:04. The audit ran in the main loop 2026-09-04 20:50–2026-09-05 06:46; its six
proposals (`/case`+`/cases` → `/mod`; honeypot → one; `/modmail` panel; the ticket card; presence into
`/settings`; `/settings` panel) were each decided by the owner and their records live in the modmail-panel entry
below (Proposals 1–6) and the `/mod` entry. Everything it proposed is shipped except `/settings`, which is its own
`TODO.md` item now.

- 🆕 **Second slash-command audit — list EVERY `/` command, then propose merges (owner, 2026-09-04
  clock read 20:50 after the asks: "Let's run another audit on all the slash commands and then propose what can be combined to
  minimize commands" · then: "Make sure you output all the / commands in this audit, I want a list
  of all of them").** Fable, main loop, no agent: build the real tree the way
  `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits` does (`BlackBlocBot` +
  `COGS`), walk `tree.get_commands()` INCLUDING every Group's children, and the report carries the
  complete list — 36 top-level (pinned in `tests/test_bot.py`) and every subcommand — before any
  proposal. Then propose merges one decision at a time (owner rule), with a count of how many
  remain. Candidates already named by the owner, below; the audit adds the rest.

## 2026-09-05 — Modmail panel, both halves: `/modmail` is one command (Build A, v80) and every ticket carries a sticky staff card (Build B, v82, `f42a591`)

Moved WHOLE from `TODO.md` at the Build B landing (10:27). Build A on `worktree-agent-afdd9e23bbaf59be8`
(Opus, 392k, v80 `b926d9d`); Build B on `worktree-agent-a4bebd98196e3ca14` (Opus, ≈465k incl. the `ca67bb5` fix, six
commits off `6e5a550`), reviewed by Fable, merged `f60ab1f`, deployed v82 10:27 (boot 17:27:37Z, `synced 30`,
schema 29 → 30). Design: `docs/info/modmail-panel-design.md`; sweeps 200–207 (A) and 219–230 (B); forks F-M1–F-M8 all (a).
Nothing exercised in Discord by a person. Leftovers stayed on `TODO.md` as "Modmail leftovers after Build B".

- 🆕 **Ticket / modmail commands → maybe one (owner, 2026-09-04, clock read 20:50 after the ask: "All ticket stuff maybe?").**
  Today: the `modmail` Group (`logs`, `block`, `unblock`, `blocked`, `mode`, `forget`) plus FOUR
  top-level ticket commands used INSIDE a ticket — `/reply`, `/areply`, `/note`, `/close`
  (`modmail.py:1131–1243`). The "maybe" is the owner's: the in-ticket four are typed mid-conversation
  with text arguments, which a panel handles with modals but costs a click. The audit proposes the
  split (a `/modmail` panel for the Group; the in-ticket four either stay, or become buttons on a
  pinned ticket card) and the owner decides.
  **Proposal 4 of 6 DECIDED (owner, 2026-09-04, "Yes"):** the `/modmail` group becomes ONE panel — root
  card = `status`; Setup… (channel selects + channels/threads mode select, replaces `settings`/`mode`),
  Blocked… (list, user select → Unblock, Block someone = user select + reason modal), Snippets… (list,
  Add modal, select → Remove — the whole `/snippet` group folds in), Forget (renders only when pointed),
  Logs. 11 subcommands over two slots → one; 36 → 33 with proposals 2–3. Est. 300–380k Opus.
  **Proposal 5 of 6 DECIDED (owner, 2026-09-05 06:25, "B"):** every ticket
  gets a PINNED staff card (member, opened-when, block state) with Reply (modal: text + snippet select),
  Reply as Staff, Private note, Close… (reason modal + silent toggle). **`/reply` stays bare** (the one
  typed constantly); `/areply`, `/note`, `/close` retire into the card. 36 → 30 with everything so far.
  **Proposal 6 of 6 DECIDED (owner, 2026-09-05 06:27, "Yes that's fine"):** `/presence apply`
  folds into the `/settings` panel as a Re-apply presence button (one slot freed); **`/settings` stays a
  group for now** (the escape hatch every panel points at; `<key>` autocompletes ~80 keys) — its own
  panel design comes AFTER the hide-when-off build, which adds a key. **Audit result: 36 → 29 slots;
  the only group left is `/settings`.** Build sequence: honeypot → `/mod` → modmail (+ snippets + ticket
  card) → presence-into-settings (folds into whichever build touches `cogs/core.py` first).
  **Owner, 2026-09-05 06:36: "Maybe /reply could be a menu. Walk me through that one again and through
  /settings. Start the rest in the meantime"** — proposal 5 reopened (`/reply` as a button/menu too) and a
  `/settings` panel walk-through requested; both answered one at a time, decisions land here.
  **`/reply` DECIDED (owner, 2026-09-05 06:41: "I think we do the both… We should have the buttons always
  appear to click reply at the bottom of a channel but also a /reply so they can just start typing a
  response"):** the staff card (Reply / Reply as Staff / Private note / Close…) is RE-POSTED at the bottom
  of the ticket after every member message so the buttons are always the last thing in the channel (the
  previous card's view is stopped, `ui/view.py` gotcha), AND `/reply` stays a bare command. `/areply`,
  `/note`, `/close` still retire into the card. Tickets are one channel each by default (`modmail_mode`
  `channel`; `thread` is the other choice) — the card works the same in a thread.
  **AMENDED + `/settings` DECIDED (owner, 2026-09-05 06:46: "Okay ship both with your suggestions"):**
  (1) the card is a STICKY message — on each member message the old card is deleted and a fresh one posted,
  so exactly one card exists, always last, one in the transcript; (2) the reply style is a SETTING
  `modmail_reply_style` (`buttons` / `typing relays` / `both`, default `both`) — in `both`/`typing`,
  a plain message typed by staff in the ticket relays to the member; (3) the staff panel carries **Try a
  fake ticket** — a practice ticket in the test channel with a fake member the owner "speaks as" from a
  button, so all three styles get tried under test mode, no throwaway mock; (4) `/settings` becomes the
  cross-cutting panel (option (a)): root shows every feature's mode read-only with "open `/x` to change",
  cards for the keys with no feature panel (staff/lead roles, log channel, `hide_commands_when_off`,
  panel-minutes, presence + Re-apply presence), Logs; `show`/`set`/`set-role`/`set-value`/`clear` retire —
  29 slots, ZERO groups. Sequence: hide-when-off (in flight) → honeypot → `/mod` → modmail → `/settings`.
  **DISPATCHED 06:48: three Opus DESIGN agents in parallel** (read-only on code, one file each in the main
  tree, no commits): `info/honeypot-panel-design.md`, `info/mod-panel-design.md`,
  `info/modmail-panel-design.md`; usage at dispatch session 8% / weekly 7% / Fable 8%, read 06:46. The
  `/settings` design waits for modmail's keys to settle. Fable reviews each against §2, then forks to the
  owner one at a time, then builds in wave order.
  **DISPATCHED 06:36:** the hide-when-off build (Opus, own worktree off `cc18993`; usage at dispatch session 1% /
  weekly 5% / Fable 6%, read 06:25). Honeypot / `/mod` / modmail designs follow.
  **LANDED 06:55 (185k Opus): hide-when-off MERGED to `main` as `0fcbac2` + `e00c9bf`** — 14 features hide,
  not 15: Fable kept `/memory`'s carve-out (fork I-M1 "open it"; memory off deletes nothing and the site is
  staff-only, so the panel is a member's only door to their own notes, KI-14). Owner can flip it back with one
  line. 4539 tests, ruff clean. ⚠️ **v78 NOT YET DEPLOYED** — `deploy.ps1` refuses untracked files and the
  design agents write into the main tree; deploy the moment their docs are committed. Usage after landing
  session 12% / weekly 8% / Fable 8%, read 06:55.
  **LANDED 06:59 (287k Opus): `info/mod-panel-design.md` written and committed** — `/mod [member]`, staff
  only, list → case card with Edit reason / Add a note / Void (Restore) / Jump to case # / Logs; `/case`,
  `/cases`, `mod` group retire (36 → 34); migration schema 28 → 29 (six nullable `mod_cases` columns);
  est. 340–420k Opus (280–340k if the site's four moves wait). Five defects REPORTED not fixed (bare
  `mod.purged`/`mod.purge_failed` kinds, dead `CASE_KINDS`, dead `_audit`/`_failed`, site Notes chip matches
  nothing, a code-notes claim about `/untimeout`/`/unban` gating that a test disproves). Forks F-M1/F-M2/F-M3
  go to the owner one at a time (§J). Usage after landing session 13% / weekly 8% / Fable 9%, read 06:59.
  **LANDED 07:00 (197k Opus): `info/honeypot-panel-design.md` written and committed** — `/honeypot`, staff
  only; the group + exempt sub-group + seven leaves retire; NEW `black_bloc/honeypot.py` + `tests/test_honeypot.py`
  (the feature has no pure module today); new kind `honeypot.exempt_set` (`honeypot.exempt` is taken), and
  retiring `exempt_add`/`exempt_remove` must also drop them from `logkinds.ROUTINE` or the dead-entry test fails;
  `honeypot_mode` STAYS in `HIDDEN_WHEN_OFF` (defaults to shadow, not off). Reported not fixed: the site writes
  `honeypot_mode`/`honeypot_exempt_role_ids` through the generic settings API, bypassing the arming refusal. Est.
  320–380k Opus. Forks F-H1/F-H2/F-H3 (§I) go to the owner one at a time after `/mod`'s. Usage after landing
  session 14% / weekly 8% / Fable 9%, read 07:00.
  **LANDED 07:02 (252k Opus): `info/modmail-panel-design.md` written and committed** — 1017 lines. Sticky
  card jumps on every write into the ticket; `modmail_reply_style` gate already exists at `_staff_message`
  (`buttons` is the only new value); practice ticket = private thread on the test channel claimed with
  `guard.own_channel`, real tickets never claimed; migration schema → +1 (`card_message_id`, `practice` on
  `modmail_tickets`) — ⚠️ the `/mod` design ALSO claims 28 → 29, so whichever builds second takes 30.
  Findings: a successful reply and `/note` write NO log row today; four kinds spelled differently by the two
  doors (`modmail.unblocked` IMPORTANT vs web `modmail.unblock` ROUTINE). Est. 480–600k as one agent —
  SPLIT recommended: A = panel + extractions + kind rename (230–290k, 36 → 35), B = migration + sticky card +
  ticket card + practice ticket + retire `/areply` `/note` `/close` (270–330k, 35 → 32). Seven forks (§I)
  go to the owner one at a time after `/mod`'s and honeypot's. Usage after landing session 15% / weekly 8% /
  Fable 9%, read 07:02. **All four agents landed; v78 deploy next.**
  **v78 LIVE 07:05 (`baede2a`)** — hide-when-off shipped; boot verified, live log `35 command(s) in guild; hidden:
  raidtrain`. Item moved WHOLE to `DONE.md`.
  **Owner 07:05: "F-M1 yes"** → **F-M1 = (a)** voided cases always listed, struck through. **Owner 07:05: "Do as
  much in parallel sub agents as possible"** → **DISPATCHED 07:07, two Opus builds in parallel, own worktrees
  off `932f34e`** (usage at dispatch session 16% / weekly 8% / Fable 9%, read 07:06): (1) **honeypot panel** —
  forks F-H1/F-H2/F-H3 built on the design's recommendation (all (a)), each reversible in a small local change,
  owner confirmation pending; sweep rows lettered `H1…`; (2) **modmail Build A** (panel + extractions + kind
  rename + five route `note()` deletions + `modmail_panel_minutes`; `/snippet` retires, 36 → 35; NO migration,
  NO sticky card, none of F-M1–F-M8); sweep rows lettered `MA1…`. Next: F-M2 and F-M3 to the owner, then the
  `/mod` build; modmail Build B (after A merges) carries the migration — takes schema 30 if `/mod` takes 29;
  its seven forks go to the owner one at a time before it starts.
  **Owner 07:10 "A" → F-M2 = (a)** (voided warns stop counting toward the threshold). **Owner 07:14 "A" →
  F-M3 = (a)** (the site gets the four case moves in this build). **DISPATCHED 07:16: the `/mod` build** (Opus, own
  worktree off `97531cc`; takes schema 29; sweep rows lettered `C1…`; est. 340–420k; usage at dispatch session
  22% / weekly 9% / Fable 10%, read 07:15). THREE builds in flight: honeypot, modmail A, `/mod`.
  **DISPATCHED 07:18: the `/settings` DESIGN** (Opus, own worktree off `0304c4d` this time so the main tree stays
  deployable; writes and commits `info/settings-panel-design.md` on its branch; usage at dispatch read 07:15 as
  above). Modmail Build B's seven forks go to the owner one at a time now, so B can dispatch the moment A merges.
  **LANDED 07:33 (314k Opus): the honeypot panel** — merged clean as `fa845a6` (4593 tests, ruff clean, 36 → 36
  measured); sweep rows `H1`–`H12` numbered **188–199** at the merge, guide count 187 → 199; KI-21 widened to
  cover the honeypot's generic-route bypass (arming refusal skipped, exempt list rewritten with no
  `honeypot.exempt_set` row). Forks F-H1/F-H2/F-H3 built as (a) — still to be confirmed with the owner one at
  a time, after modmail B's seven. Usage after landing session 34% / weekly 12% / Fable 11%, read 07:33.
  **LANDED 07:34 (264k Opus): `info/settings-panel-design.md` written and committed** (merged `361eaa2`) —
  `/settings` one staff-only command; the group and five subcommands retire; sixteen read-only mode lines;
  **Turn a feature back on…** off `hidden_names`; group → key editor over all 175 registry keys (measured;
  supersedes `panels-program.md`'s "~120"); `Put the default back` widened to every key; `/presence` folds in
  under F-S4(a) → **29 slots, zero groups**. Est. 380–450k, split Build 1 (150–190k) / Build 2 (230–280k);
  ⚠️ dispatch only after all three wave-4 builds merge. Five forks F-S1…F-S5 (§ forks) go to the owner one at
  a time after modmail B's and honeypot's; the five defects reported (no `/settings` subcommand checks the
  database; `sweeps.md:150` names a `/settings logs` that never existed; `LOG_LEVEL_COMMANDS` wrong in 11 of
  13 rows after wave 4) fold into the build. **v79 deploy started 07:36** (honeypot panel + the design doc).
  **v79 LIVE 07:39 (`361eaa2`)** — honeypot panel shipped; boot verified 14:39:15Z, synced 36, no traceback. The
  honeypot item moved WHOLE to `DONE.md`. Sweeps 188–199 are the owner's.
  **LANDED 07:46 (392k Opus): modmail Build A** — reviewed sound; merged as `b926d9d` beside the honeypot merge
  (eight conflicts: both `panel_minutes` blocks kept in `settings_store`, `LOGS_GROUPS` down to `mod`, both
  labels/mock rows, both program rows, both guide rows, both code-notes sections); 4625 tests, ruff clean,
  **36 → 35 measured**; sweep rows `MA1`–`MA8` numbered **200–207** at the merge, guide count 199 → 207.
  **v80 LIVE 07:54 (`b926d9d`)** — boot verified 14:54:28Z, `synced 35`, no traceback; nothing opened in
  Discord. This item STAYS until Build B (sticky card, migration, `modmail_reply_style`, practice ticket,
  `/areply` `/note` `/close` retire) — B dispatches once forks 1–7 are answered. Usage
  after landing session 42% / weekly 14% / Fable 13%, read 07:54.
  **Forks, one at a time (owner 2026-09-05 09:06):** F-M1 card-jump = **(a) every write** ✅; F-M3 typed-reply
  echo = **(a) unchanged** ✅; F-M4 practice transcript = **(a) filed, marked PRACTICE** ✅; F-M5 `/reply`
  keeps `ticket:` = **(a)** ✅; F-M6 real tickets not claimed = **(a)** ✅; F-M7 snippet combines in one modal = **(a)** ✅; F-M8 Reply as Staff
  stays a button = **(a)** ✅. **All seven answered (a). Build B DISPATCHED 09:21** (Opus, own worktree off `6e5a550`, est. 270–330k; five commit layers, migration 29 → 30, tree 33 → 30 expected, sweep rows lettered `MB1`–`MBn`). Usage before dispatch session 53% / weekly 16% / Fable 15%, read 09:15. Each fork got a push
  notification (global rule, same day).
  **LANDED 08:00 (429k Opus): the `/mod` cases panel** — reviewed sound (atomic void/restore with a 409 each way,
  one write one row through four shared extractions, website routes gated by `writer()`); merged as `a90f416`
  beside the two earlier merges (nine conflicts; `LOG_LEVEL_COMMANDS` loses `mod` and `honeypot`, `LOGS_GROUPS`
  is empty, the tree pin is **33** — the branch measured 34 off a 36 base and `main` already had modmail A's
  −1); 4686 tests, ruff clean, mock check 17 pages / 146 routes; sweep rows `C1`–`C11` numbered **208–218**,
  guide count 207 → 218; KI-22 (bare `mod.purged` kinds) kept above KI-21. **v81 LIVE 08:09 (`a90f416`)** —
  boot 15:08:59Z database ready (schema 29 — no migration line is logged, so the only evidence it ran is that
  the bot came up), `synced 33`, no traceback; nothing opened in Discord. The `/case` + `/cases` item moved
  WHOLE to `DONE.md`. Handed to the conductor by the build: `panels.NoteModal` cannot prefill (one line,
  three other modals want it); `CASE_KINDS` is imported by nothing; the site's Notes chip matches zero rows.
  ALL THREE wave-4 builds are merged — the `/settings` build may dispatch once its forks F-S1–F-S5 are
  answered. Usage after landing session 44% / weekly 14% / Fable 13%, read 08:00.
  **BUILD B BUILT 2026-09-05 on `worktree-agent-a4bebd98196e3ca14` off `6e5a550` — NOT MERGED, NOT
  DEPLOYED, awaiting the conductor's review.** Five commits, one per layer: (1) schema **29 → 30**
  (`modmail_tickets.card_message_id`, `.practice`) — ⚠️ **migrate before deploy**, and the migration was
  RUN against a real schema-29 file built by `main`'s own `db.py`, not reasoned about; (2) the sticky
  ticket card (a persistent `DynamicItem` with **Reply · Reply as Staff · Private note · Close…**),
  `bump_card` with its 2 s/8 s debounce on the bot, the reconciler's third job, and the `add_note` /
  `reply_body` extractions; (3) `modmail_reply_style` (`buttons`/`typing`/`both`, default `both`) gating
  the relay that `_staff_message` already had; (4) the practice ticket — a claimed private thread on the
  test channel where nobody is ever DMed, which is how F-M8's reply-style choice gets made; (5) the
  retirement of `/areply` `/note` `/close` into the card — **33 → 30, measured** — with the doc, string and
  site sweep. `/reply` keeps `ticket:` (F-M5). Verified: `pytest` **4738**, `ruff` clean,
  `node site/mock/check.mjs` **17 pages / 146 routes, unchanged**. ⚠️ **NOT verified: anything against live
  Discord** — no boot, no card posted, no practice thread made, no DM seen. Sweep rows lettered
  `MB1`–`MB12` for the conductor to number. Handed to the conductor: `picked_values` is now a second copy
  (`polls.py` and `modmail.py`) and wants hoisting into `panels.py`; the card's debounce numbers have never
  been measured against a real channel.
  **LANDED 10:27 (≈465k Opus incl. one fix): modmail Build B** — Fable review found one real defect (a write landing
  while the card was mid-post was dropped, so the card was not last) → fixed on the branch as `ca67bb5` with a dirty flag
  and a re-loop, test proven to fail on the old code; merged clean (no conflicts) as `f60ab1f`; `MB1`–`MB12` numbered
  **219–230**, guide count 218 → 230; 4739 tests, ruff clean, mock check 17 pages / 146 routes.
  **v82 LIVE 10:27 (`f42a591`)** — boot 17:27:37Z database ready (schema 30 — no migration line is logged), `synced 30`,
  no traceback; nothing opened in Discord. This item moves WHOLE to `DONE.md`. Handed to the conductor by the build and
  the review (now their own 🔧 item below): the panel-side **A ticket…** select / ticket card in the `/modmail` panel (design
  §B S5, §C) fell between Build A and Build B and is UNBUILT; `picked_values` is copied in `polls.py` and
  `black_bloc/modmail.py`; `NO_CATEGORY`/`NOT_A_CATEGORY` are dead in the cog; `Modmail._post_transcript` /
  `_remove_place` are unreferenced Build-A wrappers; an exception inside `refresh_card` is only WARNING-logged with no
  `modmail.card_failed` row; the design doc's `path:line` keys for `modmail.py` are stale.

## 2026-09-05 — Mod cases panel: `/mod [member]` is one command over the case record; `/case`, `/cases` and `/mod logs` retire (v81, `a90f416`)

Moved WHOLE from `TODO.md` at the landing (08:12). Built on `worktree-agent-ab5740f777a3dfd80`
(Opus, 429k, six commits off `97531cc`), reviewed by Fable, merged `a90f416`, deployed v81 08:09
(boot 15:08:59Z, `synced 33`, schema 28 → 29). Design: `docs/info/mod-panel-design.md`; sweeps 208–218;
forks F-M1/F-M2/F-M3 all (a). Nothing exercised in Discord by a person.

- 🆕 **`/case` + `/cases` → one panel (owner, 2026-09-04, clock read 20:50 after the ask: "Also we have case and cases for slash
  commands Let's combine those menus too").** Today `modcmds.py:696` `/case` shows one case and
  `modcmds.py:723` `/cases` lists a member's; the panel shape is `/cases [member]` → list with a
  select that opens the one-case card (moves on the card per the moderation panel design, staff
  final say). Folds into the second audit's proposals; one build, own design doc.
  **DECIDED (owner, 2026-09-04, audit proposal 2 of 6, "Yes"):** `/cases [member]` — no member = the
  server's newest cases, paged ‹ ›; a select opens the one-case card (kind, who, when, reason, note) with
  Edit reason, Add note, Void this case (reason required, DM'd); a Jump to case #… button (id modal)
  replaces `/case <id>`, which retires. 36 → 35 slots. Est. 200–260k Opus.
  **Proposal 3 of 6 DECIDED (owner, 2026-09-04, "Yes"):** the panel is spelled **`/mod [member]`** —
  the `/mod` group (only `logs`) folds in as a Logs button, so `/case`, `/cases` and the `/mod` group
  collapse into ONE `/mod`; 36 → 34 slots. The seven bare actions (`/warn`, `/timeout`, `/untimeout`,
  `/kick`, `/ban`, `/unban`, `/purge`) STAY bare — typed mid-incident with autocompleted arguments, a
  panel would be three clicks slower at the wrong moment.

## 2026-09-05 — Honeypot panel: `/honeypot` is one command, seven subcommands become controls (v79, `361eaa2`)

**Landing:** Opus build in its own worktree (314k), merged clean `fa845a6`, landing edits `aebcc02` (sweep rows
`H1`–`H12` numbered 188–199, guide count 187 → 199, KI-21 widened to the honeypot's generic-route bypass),
deployed `361eaa2` as v79 at 07:39 together with `info/settings-panel-design.md` (`361eaa2` is the design's
merge commit). 4593 tests, ruff clean, `check.mjs` 17 pages / 142 routes, `commands synced` 36 → 36 measured (a
Group was already one slot). Boot verified from the Fly log: database ready 14:39:15Z, synced 36, `/raidtrain`
hidden, logged in 14:39:19Z, no traceback. **NOT verified:** the panel opened in Discord, a trap created, a role
picked, a modal submitted, whether a real client submits an EMPTY `min_values=0` RoleSelect (**Exempt nobody** is
the fallback that makes that safe), the dashboard Settings row for `honeypot_panel_minutes`. Forks F-H1/F-H2/F-H3
were built on the design's recommendation, all (a), each reversible in one small local change (design doc
§ Build deviations) — the owner's confirmation is still owed, one at a time. What was built, in full, is the
design doc's `## Build deviations` foot and `docs/access/sweeps.md` rows 188–199. Review: `/honeypot` in
`#mute-me-bot-test-spam`; https://blackbloc.heygabi.ai/honeypot.html is unchanged.

**The item, moved whole from `TODO.md`:**

- 🆕 **Honeypot → ONE slash command (owner, 2026-09-04, clock read 20:50 after the ask: "All of honeypot should be 1 slash
  commands Let's combine").** Today `honeypot.py:417` is a Group (`logs`, `setup`, `status`, `mode`,
  `forget`) with a nested `exempt` group (`add`, `remove`) — 7 subcommands. Becomes `/honeypot` →
  panel: status card, Setup…, mode select, Exempt roles (role select), Forget, Logs — the wave-3
  shape (`info/panels-program.md`). Folds into the second audit; one build, own design doc.
  **DECIDED (owner, 2026-09-04, audit proposal 1 of 6, "Yes"):** root card = today's `status`; buttons
  Setup… (name modal), mode select, Exempt roles (role multi-select replaces `exempt add`/`remove`),
  Forget (renders only when a trap is recorded), Logs. Est. 250–320k Opus. Design doc next, then build.

## 2026-09-05 — Hide commands when off: a feature turned off on the portal takes its `/command` with it (v78, `baede2a`)

**Landing:** Opus build in its own worktree (185k), merged `0fcbac2`, conductor's carve-out commit `e00c9bf`,
deployed v78 07:05 Phoenix. Live proof in the boot log: `35 command(s) in guild; hidden: raidtrain` — the one
mode that is `off` on the live guild lost its command on the first sync. **14 features hide, not the 15 the
build first shipped: `/memory` keeps fork I-M1 ("open it", 2026-09-03)** — memory off deletes nothing and the
site is staff-only, so the panel is a member's only door to notes held about them (KI-14); hiding it would have
left members no way in. New bool `hide_commands_when_off` (default true) reachable from the Settings page and
`/settings set-value`; `/help` names how many are hidden and both ways back; one `commands.visibility` row per
sync naming hidden + shown again. `NEVER_HIDDEN` = settings, help, about, ping. Sweeps 183–187; rows 53, 108,
130, 174 rewritten. NOT verified at landing: a portal flip re-syncing within 60 s, the dashboard row, the `/help`
note as rendered. Design: `docs/info/code-notes.md` § *Hide commands when off*.

**The item, moved whole from `TODO.md`:**

- 🆕 **A feature turned OFF on the web portal hides its /command (owner, 2026-09-04 20:45: "Can we expand
  the app so if we turn a feature off on the web portal the /command is hidden? Like I want to turn off
  YouTube videos for now. Can we have that make the /youtube command not appear until it turns back on").**
  Measured 20:45: the mechanism EXISTS — `black_bloc/command_visibility.py` removes a top-level command
  from the dev guild's tree whenever a key in `HIDDEN_WHEN_OFF` reads `off`, debounced 5 s / re-synced at
  most once a minute, and it is wired to `store.on_change`, so the portal's Settings page already
  triggers it (`api/settings_api.py` writes through `store.set`). The table only names `rolemenu_mode` and
  `request_mode` (the role-menus build deletes the first). **The build:** the table grows to every mode key
  whose choices include `off` → its top-level command — golive, youtube, pings, tempvoice → `voice`,
  honeypot, events → `event`, poll, birthday, automod, rolemenu, request, chat, chat_memory → `memory`,
  raidtrain, applications → `apply` (modmail has no off; `settings`, `help`, `about` never hide);
  `shadow` is NOT off (youtube is `shadow` today — the owner sets it `off` on the portal and the command
  goes). Configurable both ways (33): one new bool key `hide_commands_when_off` (default **true**)
  that the Settings page and `/settings set-value` reach; `hidden_names` reads it. ⚠️ **Trade-off to
  say out loud:** with a command hidden, staff turn the feature back on from the portal or
  `/settings set-value <feature>_mode on`, not from the panel — the panels program's P9 "mode-off panel
  still opens and says so" survives only for the ≤60 s sync lag. `/help` already follows `hidden_names`.
  Tests: `tests/test_command_visibility.py` (the role-menus build re-pointed it at `request_mode`),
  `tests/test_settings_store.py`, `labels.js` row, `feature-list.md`, OWNER_GUIDE, a sweeps row, code-notes.
  **Order: AFTER the role-menus merge (v77)** — that branch edits `command_visibility.py` and its test.
  Est. 120–180k Opus, one build, then v78.

## 2026-09-04 — Role menus panel: `/rolemenu` is one window (wave 3 FOURTH and LAST landing, v77, `43312b9`)

Release **v77** (`43312b9`, 20:51; `deploys.log` line 76). Merge `--no-ff` of
`worktree-agent-ace2086f9f7cfa541` — **four commits off `4523118`** (`8cdbdd3`, `12b296b`,
`18b132c`, `05a9a87`). Built by one Opus agent for **529k against a 420–500k estimate** (dispatched
16:03 in parallel with raidtrain, landed second at 16:53), Fable-reviewed **approve**. Design:
`info/role-menus-panel-design.md` (header flipped to SHIPPED; its `## Deviations` foot lists 14).

**What it is.** The `rolemenu` and `role` staff groups' eighteen leaf subcommands are retired for
ONE staff `/rolemenu` that opens an ephemeral panel: the root lists the menus (a select picks one)
and a Lead sees **Setup…**, **Grants…** and **Logs** plus the mode select; a menu card (row 0
exactly five) carries **Add a role**, **Hand roles out**, **Post it**, **Edit** (F-R3 (a) — an edit
re-posts a posted menu) and the waiting-on-staff sub-panel (F-R1 (a) — the pending-requests queue
lives in the panel); the grant card carries **Extend** and **End it now**, which makes the phantom
`/role revoke` (named in four docs, never built) real; F-R2 (a) — a grant with no end date is `0 =
never`. **The owner's §I-amend Grants audit** is built: `active_grants`, `grant_order`, `time_left`
and `grant_lines` in the pure `black_bloc/rolemenus.py`, soonest-ending first, no-end-date LAST,
`AUDIT_MAX` 25. Grant/extend were reconciled from two divergent implementations (cog inline vs
`roles.py`) into one — and `tests/api/tools/test_roles.py` is UNCHANGED, which is the proof the
reconciliation did not move the site. Seven bare log kinds gained `kind_via`; `web.rolemenu.*` was
renamed `web.role_menu.*` with `HEADS["rolemenu"]` kept so old rows still label. `guarded()` keeps
`guard.allows_channel` on every role-changing move (TEST_MODE holds). `role_menus.option_label`
collides by name with `panels.option_label` — import aliased. New key `rolemenu_panel_minutes`
(int, 10). `HIDDEN_WHEN_OFF["rolemenu_mode"]` deleted (hiding the command hid the only way on; the
table now names `request_mode` alone — the hide-when-off item on the TODO grows it back on purpose,
behind a bool). `commands synced` **37 → 36, measured at boot**.

**The merge.** **Eight append-shaped conflicts**, every one resolved both-sides HEAD-then-branch
(`settings_store.py` block + default, `tests/test_settings_store.py`, `tests/test_bot.py` — three
group asserts kept and the pin set 37 → **36** —, `OWNER_GUIDE.md` — the branch's `/rolemenu` row
added above "Test something", count 172 → **182** —, `site/mock/server.mjs`, `labels.js`,
`code-notes.md` foot, `sweeps.md` — branch header first, newest first). The branch wrote its sweep
rows as **`M1`–`M10`, letters on purpose**, and the conductor numbered them **173–182** at the merge,
after raidtrain's 163–172. The design doc's deviation 13 was updated to say so. `docs/info/code-notes.md`'s
`# Role menus panel (wave 3)` section was re-keyed to the merge. **4465 → 4529 tests.**

**Review findings, non-blocking, deferred to the fold sweep:** `ready()` is another cog-local copy
of the opened/confirm triplet (seventh confirm copy overall); the `test_every_feature_group_has_a_logs_command`
re-expression is still on the TODO.

**Verified:** ruff clean; 4529 passed; boot clean at 03:51:09Z (`database ready` / `synced 36` /
`logged in`, no Traceback). **NOT verified:** `/rolemenu` was not opened in Discord — no menu posted,
no role handed out or ended, the Grants audit was not opened, `rolemenu_mode`'s state was not read.
Sweeps **173–182** are the owner's to run, in `#mute-me-bot-test-spam`, as a Lead.

**With this landing WAVE 3 is COMPLETE and the panels program is DONE** — the program item follows,
moved whole from `TODO.md`.

---

## 2026-09-04 — Panels over slash commands — the program (waves 1–3 COMPLETE with v77; moved whole from `TODO.md`)

Moved WHOLE, unedited, from `docs/TODO.md` at the v77 landing (20:54). The status paragraphs inside it
are the running record, newest at the bottom of each wave; every landing it names has its own entry above.

- 🆕 **Panels over slash commands — the rest of the app (owner, 2026-09-03: "then carry it
  through the rest of the app"; confirmed ~11:25: "do the change to all / commands. I like
  how request works").** Audit every command group (44 commands synced; `cogs/core.py:88`
  lists them) and convert each feature to one command + panel the same way: `/event`,
  `/poll`, `/raidtrain(s)`, `/applications`, `/voice`, `/twitch`, `/birthday`, `/memory`,
  `/settings`, the moderation set. One feature per build, requests as the template
  (`info/requests-panel-design.md`); each gets its own design doc with the button table per
  state. Scope is now ALL commands — the sequence is the conductor's to plan, the design
  calls still go to the owner one at a time. Status: **PLANNED** (2026-09-03 11:10) — the
  program is written: [`info/panels-program.md`](info/panels-program.md) (§2 the 17
  invariants every panel inherits from `/request`, §3 the measured inventory — ~177
  subcommands over 44 top-level commands → ~21 commands, §4 **wave 0 = extract
  `black_bloc/panels.py` from the requests cog** so the three review defects cannot recur
  seventeen times, §5 four waves, §6 the three owner forks: F1 mod commands, F2 modmail's
  in-thread `/reply` set, F3 `/settings`). **Wave 0 is MERGED** (`1861923`, 2026-09-03 ~11:50:
  `black_bloc/panels.py` + `tests/test_panels.py`, 26 tests, the requests cog now inherits
  `Panel`; 160k Opus / 20 min; `code-notes.md` re-keyed at the merge) **and LIVE in v60**
  (2026-09-03 11:39; the wave-0 record itself is in `DONE.md` that date). **Wave 1 design
  docs IN FLIGHT** (owner "Build all, keep going", 2026-09-03 ~12:40): three Opus design
  agents writing `info/events-panel-design.md`, `info/polls-panel-design.md`,
  `info/birthdays-panel-design.md` (sweep rows reserved: events from 73, polls from 80,
  birthdays from 87; 66–72 belong to the two feature builds). `applications-panel-design.md`
  waits until `feat/applications-no-role` lands — its cog is being rewritten. **All three
  LANDED and REVIEWED against §2** (2026-09-03 ~12:15; 171k / 185k / 197k Opus). The
  staff-final-say rule settled three of five forks in-doc (polls `denied → open`, events
  `denied → approved` + a DM'd cancel note, no draft rows). F-B1 DECIDED 12:20 (keep today's behaviour: member lookup on, creator may end own poll).
  **The fourth wave-1 design exists:** [`info/applications-panel-design.md`](info/applications-panel-design.md)
  (2026-09-03, written against `9891f71` after the no-role merge — 17 subcommands over two groups
  collapse into one member-visible command; sweep rows 94–102; `denied`/`removed` → `approved`
  and the member's own list settled by the standing rules). Forks: **I-A1 DECIDED 13:35 — the
  command is `/apply`** ("it's gamer lingo"; the `applications` Group goes); **I-A2 DECIDED 13:47 —
  "Visible"** (`/apply` stays when the mode is off; the `HIDDEN_WHEN_OFF` entry goes); **I-A3 DECIDED
  14:12 — "Build the question sub panel"** (§C's Questions sub-panel as designed). Applications
  build landed 14:55 (401k), merged `853776c`, **live in v66 15:00** (43 → 42 commands). **WAVE 1
  COMPLETE** — four landings in `DONE.md` 2026-09-03. Waves 2–4 remain (§5 of the program).
  **Wave 2 design docs ALL LANDED 15:50–15:54** (five Opus design agents, one file each:
  `info/golive-panel-design.md` 205k, `info/voice-panel-design.md` 210k, `info/youtube-panel-design.md`
  192k, `info/pings-panel-design.md` 199k, `info/memory-panel-design.md` 204k — ⚠️ the 60k estimate was
  off 3×; calibrate design docs at ~200k). Golive REVIEWED against §2 15:52 (consistent: 4 rows in caps,
  member/staff split, one function per move with `via`, one key, no Settings sub-panel with the reason).
  The other four await Fable review. **All eight owner forks DECIDED 16:10–16:15 (owner asked for them
  rapid-fire in one form, 16:05 — a one-time exception to one-at-a-time):** golive I1 = **`/golive`**;
  golive I2 = **build the staff `Streamers…` sub-panel**; voice F1 = **leave the in-channel control post
  as it is**; pings I1 = **keep today's — a streamer may always take their own ping role away**; pings
  I2 = **two Events toggles when the two keys differ, one when they agree**; youtube F-Y1 = **keep
  `/youtube` and `/golive` separate**; youtube F-Y2 = **flip `youtube_mode` to shadow at the panel's
  landing** (operational, the conductor does it via the site); memory I-M1 = **open it — `/memory`
  stays visible with the mode off, the Forget controls keep working**. Builds in worktrees in cost
  order: memory → golive → youtube (230–300k) → pings (300–360k) → voice (420–480k); each brief
  carries its decided forks. **Memory LANDED 16:42 (329k — the 120–180k estimate was 2× off; a
  wave-2 build is ~2× its estimate, calibrate the rest up), merged `cb941d9`, live in v68 `cb941d9`
  16:48** (3710 → 3744 tests, 42 commands) — landing entry in `DONE.md` 2026-09-03; sweeps
  104–108 are the owner's to run (`chat_memory_mode` is still off live, so 104–107 need it on plus
  a conversation first). **Golive LANDED 17:05 (464k against a 230–300k estimate — again ~2×; four commits off `8cbe453`),
  Fable-reviewed approve, merged `0aeed72` (four append-only conflicts with the memory merge), live in
  v70 17:25** (3750 → 3796 tests, `commands synced` **42 → 41 measured at boot**) — landing entry in
  `DONE.md` 2026-09-03; sweeps 109–117 are the owner's to run. **Youtube LANDED 17:10 (371k against a
  180–250k estimate — ~2× again; three commits off `ea252bd`), Fable-reviewed approve, merged `b764757`
  (six append-only conflicts with the golive merge; its sweeps rows renumbered 130–137 → 118–125), live in
  v71 17:37** (3796 → 3872 tests, `commands synced` **41 → 40 measured at boot**), **F-Y2 done 17:42**
  (`youtube_mode` off → shadow on the Go-live page, PUT logged 00:42:53Z) — landing entry in `DONE.md`
  2026-09-03; sweeps 118–125 are the owner's to run. **Pings LANDED 18:25 (379k against a 300–360k
  estimate; four commits off `85e14c4`), Fable-reviewed approve with one merge-time fix, merged `a5ad521`
  (clean, no conflicts), live in v72 18:30** (3872 → 4050 tests, `commands synced` **40 → 39 measured at
  boot**) — landing entry in `DONE.md` 2026-09-03; sweeps 126–134 and the rewritten 38–42 are the owner's
  to run. **Voice is the last wave-2 panel** — F1 RE-CONFIRMED by the owner 21:20 ("Leave it as is" = (a),
  the in-channel control post stays untouched); design Fable-reviewed against §2 21:25 (consistent on
  P1–P17; drift since it was measured, carried in the brief: 39 → 38 commands not 42 → 41, sweeps start
  at **135** not 104, `panels.site_page_url(origin, "tempvoice")` now exists so no copy, `panel_minutes`
  takes a key, `voice_panel_minutes` also gets its `labels.js` + `server.mjs` label like golive/pings).
  **Voice LANDED 21:55 (385k against a 420–480k estimate — the first to land UNDER; five commits off
  `2854d74`), Fable-reviewed approve with one merge-time fold (`clamped` into `panels.py`), merged
  `4d64b36` (clean, no conflicts), live in v73 22:08** (4050 → 4265 tests, `commands synced` **39 → 38
  measured at boot**) — landing entry in `DONE.md` 2026-09-03; sweeps 135–143 are the owner's to run.
  **WAVE 2 COMPLETE.** Owner 2026-09-04 09:05 "Keep going" → **wave-3 design docs DISPATCHED 09:15**
  (four Opus agents in parallel, one doc each — `info/raidtrain-panel-design.md`,
  `info/role-menus-panel-design.md`, `info/chat-panel-design.md`, `info/automod-panel-design.md` —
  ~200k each, read-only on code, no commits). **All four LANDED 09:21–09:33 and Fable-reviewed APPROVE**
  (raidtrain 595 lines / 250k; role menus 622 / 230k; chat 533 / 241k; automod 626 / 209k — see the
  `info/README.md` rows). `commands synced` after all four: 38 → **36** (raidtrain −1, role menus −1, chat and
  automod 0). **Conductor prep DONE 09:50:** `still_allowed(interaction, ok, refusal)` is on `main` in
  `panels.py` (raidtrain §F), `still_staff` is a two-line call to it, three tests in `tests/test_panels.py`,
  code-note at `panels.py:31` — wave-3 builds branch from this commit or later and USE it, never copy it; the
  numbers-modal validator (role menus §F) and the confirm helper (automod §F, youtube `open_confirm` + pings
  deviation 8 + automod = three copies) are FOLDED AT MERGE, not pre-built. **13 forks go to the owner ONE AT
  A TIME, in this order:** raidtrain F-R1/F-R2/F-R3 · role menus F-R1/F-R2/F-R3 · chat F-C1/F-C2/F-C3/F-C4 ·
  automod F-A1/F-A2/F-A3 (every recommendation is (a); chat F-C3 recommends NO confirm on the money
  switch while automod F-A1 recommends a confirm on arming — different reasons, both stated). Answers are
  recorded here as they come — **DECIDED 2026-09-04 between 09:32 and 15:08 Phoenix (the clock was read at those two ends, not per
  answer — earlier per-answer stamps here were inferred and have been removed):** raidtrain F-R1 = (a) no lineup-post button ("Leave it"); F-R2 = (a) upcoming trains only in the picker; F-R3 = (a) one claim select, no
  next-open-hour button — RAIDTRAIN FULLY DECIDED. Role menus F-R1 = (a) build the Waiting-on-staff
  sub-panel; F-R2 = (a) `0` days = no end date **PLUS an owner amendment to the design
  (verbatim: "let's have an audit menu that shows durations of active roles")** — the `Grants…` sub-panel
  opens as an AUDIT of every active timed role in the guild (member · role · time left / end date, or
  `no end date`; soonest-ending first; 25-capped with `capped_placeholder`), and the "Whose roles?"
  `UserSelect` NARROWS that list rather than being the only way in; the embed body lists them as lines so
  the count is readable even when the select is capped. Goes in the role-menus build brief as §I-amend.
  F-R3 = (a) every edit re-renders the posted panel in place — ROLE MENUS FULLY DECIDED.
  Chat F-C1 = (a) read-only numbers + one `Limits…` modal for all five; F-C2 = (a) `Edit…` on the note
  card; F-C3 = (a) one click to turn chat on, no confirm — the spend cap is the brake;
  F-C4 = (a) both mood-pool guards on both doors, one implementation in `chat_panel.py` — CHAT FULLY
  DECIDED. Automod F-A1 = (a) confirm before arming, `automod_arm_needs_confirm` default true; F-A2 = (a) one
  prefilled paragraph field for bad words, over-4000 says use the website; F-A3 = (a) no controls for
  `automod_warn_threshold` / `mod_dm_on_action`, read-only lines pointing at the Moderation page —
  **ALL 13 FORKS DECIDED, every one (a), plus the role-menus Grants audit amendment. Builds may start.**
  Then builds in cost order (automod ~300–360k, chat ~300–360k, raidtrain
  380–450k, role menus 420–500k), each Opus in its own worktree off `main`, layer-boundary commits, sweeps
  numbered from 144 at build time; usage read before each dispatch; weekly cut-off 90%.
  **DISPATCHED 2026-09-04 15:10 Phoenix: automod AND chat builds IN PARALLEL** (Opus, own worktrees
  off `5db58fb`; usage at dispatch session 2% / weekly 0% / Fable 1% — the weekly had reset with a "50% higher
  through September 13" boost on the page). **Automod LANDED (370k against a 300–360k estimate; three
  commits off `5db58fb`), Fable-reviewed approve with one merge-time relabel (the Settings toggle says what it
  will do), merged `0b1b2bf` (clean, no conflicts), live in v74 15:45** (4265 → 4332 tests, `commands synced`
  **38 → 38 measured at boot**) — landing entry in `DONE.md` 2026-09-04; sweeps 144–154 are the owner's to run.
  **Chat LANDED (441k against 300–360k; five commits off `5db58fb`), Fable-reviewed approve, merged
  `251dd14` (five append-shaped conflicts against automod, all resolved HEAD-then-branch; sweeps `C1`–`C8`
  numbered 155–162 at the merge), live in v75 15:58** (4332 → 4402 tests, `commands synced` **38 → 38
  measured at boot**) — landing entry in `DONE.md` 2026-09-04; sweeps 155–162 are the owner's to run.
  **Raidtrain LANDED (473k against 380–450k; four commits off `4523118`), Fable-reviewed approve, merged
  `2dd2689` (clean, no conflicts; sweeps 163–172 numbered on the branch; owner-guide count 162 → 172),
  live in v76 16:56** (4402 → 4465 tests, `commands synced` **38 → 37 measured at boot**) — landing entry
  in `DONE.md` 2026-09-04; sweeps 163–172 are the owner's to run; `raidtrain_mode` still off.
  **Role menus LANDED 16:53 (529k against 420–500k; four commits off `4523118`), Fable-reviewed approve
  (§I-amend Grants audit built: `active_grants`/`grant_lines` in the pure module, soonest-ending first,
  no-end-date last, 25-cap; `tests/api/tools/test_roles.py` unchanged is the proof the reconciliation did
  not move the site; `web.rolemenu.*` → `web.role_menu.*` kinds renamed, `HEADS["rolemenu"]` kept), merged
  `43312b9` (eight append-shaped conflicts, all resolved both-sides; `M1`–`M10` → sweeps 173–182;
  owner-guide count 172 → 182; `tests/test_bot.py` pin 37 → 36), live in v77 20:51** (4465 → 4529 tests,
  `commands synced` **37 → 36 measured at boot**) — landing entry in `DONE.md` 2026-09-04; sweeps 173–182 are
  the owner's to run. **WAVE 3 COMPLETE — the panels program's 17 features are all one command + panel.**
  DISPATCHED 2026-09-04 16:03 Phoenix: raidtrain AND role menus builds IN PARALLEL (Opus, own worktrees
  off `251dd14`; usage at dispatch session 12% / weekly 3% / Fable 3%; raidtrain numbers sweeps from 163 with
  digits, role menus writes `M1…` and the conductor assigns digits at the merge, as chat did; both pin
  `tests/test_bot.py` at what THEIR branch measures — 37 each — and the conductor reconciles to 36 at the
  second merge; role menus carries the owner's §I-amend Grants audit). If this session dies: `git worktree list` /
  `git branch --list 'worktree-agent-*'` finds a branch; merge only one whose FINAL commit is a doc/string
  sweep with a passing full suite.
  Events I2 DECIDED 12:40 (`/timezone` retired).
  **Wave-1 builds all landed 13:40–13:50** (birthdays merged `58974e1`; events on
  `worktree-agent-a448c7ab780ed3c2b`, polls on `worktree-agent-aa735ab092d13477d`, both under Fable
  review); the applications build follows once I-A3 is answered. Merge in wave order, re-key
  `code-notes.md` per merge, deploy per landing. ⚠️ The v63 deploy REFUSED at the gate 13:52 on the
  rate-limit flake — fixed by freezing the clock in the test (`code-notes.md` →
  `tests/api/test_settings_api.py:221`), three `-n auto` runs green; **v63 live 13:58, v64
  (events, `e670542`) live 14:05** — both landings recorded in `DONE.md` 2026-09-03. Polls merged
  `27452ac` (3644 tests), **live in v65** (`d13e1a4`, 14:14) — landing entry in `DONE.md`.

---

## 2026-09-04 — Raid train panel: `/raidtrain` is one window (wave 3 THIRD landing, v76, `2dd2689`)

Release **v76** (`2dd2689`, 16:56; `deploys.log` line 75). Merge `--no-ff` of
`worktree-agent-aba5d44f8e27a8e28` — **four commits off `4523118`** (`3e54d52` the pure half,
`f584676` the cog and the shared functions, `4bb059c` the routes and the tests, `656e771` the
doc sweep). Built by one Opus agent for **473k against a 380–450k estimate** (dispatched 16:03
in parallel with role menus, landed first), Fable-reviewed **approve**. Design:
`info/raidtrain-panel-design.md` (header flipped to SHIPPED; its `## Deviations` foot lists 14).

**What it is.** The `raidtrains` staff group and the `raidtrain` member group's fifteen leaf
subcommands are retired for ONE member-visible `/raidtrain` that opens an ephemeral panel: the
root lists the upcoming trains (a select picks one; F-R2 (a) — past trains stay on the site), a
Lead sees **Setup…**, **Logs** and the mode select; a train card shows the lineup with **Take a
slot** (one claim select, F-R3 (a) — `may_claim` is the ONE place the who-may-take rule lives,
read by the select's options and by the refusal), **Give back**, **Mine**, and for organizers
**Put in**, **Take somebody off**, **Swap**, **Lock the lineup** / **Open it for sign-ups** and
**Call it off** (a reason is required, through `NoteModal`). No lineup-post button (F-R1 (a)).
Every move is an async shared function in `cogs/content/raidtrain.py` carrying `via`
(`claim_slot`, `release_slot`, `assign_slot`, `unassign_slot`, `swap_slots`, `move_train`,
`create_and_publish`, `set_mode`, `save_setup`), each writing ONE `log_action(kind_via(...))`
row; `api/tools/raidtrain.py` calls the same functions with `via=VIA_WEBSITE` through
`answered(outcome)` → `Refused(status, code, message)`, so the recorded Via-labelling gap is
closed and **`web.raidtrain.cancel` is written for the first time**. `Outcome` and `refusal`
moved UP into `black_bloc/panels.py` (`chat_panel.py` now imports them from there — the fold
the chat landing asked for, done here). New key `raidtrain_panel_minutes` (int, 10) in its own
`settings_store` block. `commands synced` **38 → 37, measured at boot**.

**The merge.** Clean — no conflicts (role menus was still on its branch). The branch numbered
its sweep rows **163–172** with digits (it was told chat's 155–162 were fixed); the conductor
moved the `OWNER_GUIDE.md` count 162 → 172. `docs/info/code-notes.md`'s `# Raidtrain panel
(wave 3)` section was re-keyed to the merge. **4402 → 4465 tests.** Deviations worth knowing
(the foot has all 14): the card's buttons and selects are split into `card_buttons` /
`card_selects` so the lineup row stays ≤5; **Take somebody off** is gated on open/locked;
option labels are plain `%H:%M UTC` (no markdown inside a select option); `NOBODY_THERE` stays
in the cog; `move_train` covers live AND done; `FEATURE_OFF` was deleted; the `phase18-design.md`
superseded banner (which wrongly described `/golive`/`/twitch`) and `cutover-plan.md:45` were
fixed in passing; the optional labels/mock rider was skipped.

**Review findings, non-blocking, deferred to the fold sweep:** `opened()` is a SECOND cog-local
copy (automod has the first; chat inlines the triplet 14×); and
`tests/test_bot.py::test_every_feature_group_has_a_logs_command` now covers five groups only —
already on the TODO to re-express against the panels' Logs button.

**Verified:** ruff clean; 4465 passed; boot clean at 23:56:13Z (`database ready` / `synced 37`
/ `logged in`, no Traceback). **NOT verified:** `/raidtrain` was not opened in Discord — no
hour claimed, no train cancelled from the site, no DM sent; `raidtrain_mode` is still **off**
everywhere, so row 163 (the panel with the mode off) is the first thing the owner sees. Sweeps
**163–172** are the owner's to run, in `#mute-me-bot-test-spam`, as a Lead.

---

## 2026-09-04 — Chat panel: `/chat` is one window (wave 3 SECOND landing, v75, `251dd14`)

Release **v75** (`251dd14`, 15:58; `deploys.log` line 74). Merge `--no-ff` of
`worktree-agent-ab33797d235cf0d96` — **five commits off `5db58fb`** (`d08994d` the pure half
`black_bloc/chat_panel.py`, `99dd8d5` the cog, `e4304e1` the logkinds table, `b0b62b1` a note
card keeping the filter words, `1767109` the doc sweep). Built by one Opus agent for **441k
against a 300–360k estimate** (dispatched 15:10 in parallel with automod, landed second),
Fable-reviewed **approve**. Design: `info/chat-panel-design.md` (header flipped to SHIPPED).

**What it is.** The `chat` group's eight leaf subcommands are retired for ONE staff-only
`/chat` that opens an ephemeral panel: the status block at the root (mode, the two tiers, the
turns and money — hidden by `chat_status_admin_only` for non-administrators — and the notes
count), then **Personality…** (the voice select and the two mood selects), **Knowledge…** (the
note picker, **Write one down…**, **Edit…**, **Remove** behind a confirm, **Find…**),
**Settings** (read-only numbers plus **Limits…**), the two mode toggles and **Logs**. The
forks landed as decided, every one (a): **F-C1** Settings WRITES through one five-field
`LimitsModal` (five is Discord's ceiling); **F-C2** a note is edited in the SAME
`NoteFieldsModal` prefilled; **F-C3** turning the models on is one press — the monthly cap is
the brake; **F-C4** the two mood-pool guards moved onto the Discord door, and the ONE place
they live is `chat_panel.mood_options` / `mood_refusal`, read by both the select (which never
offers a move the function would refuse) and `set_mood` itself. Every move is an async shared
function in `black_bloc/chat_panel.py` carrying `via`; `api/tools/chat.py` now calls the same
functions with `via=VIA_WEBSITE`, which is how the two doors stay one implementation
(checklist 15/17). New key `chat_panel_minutes` (int, 10) in its own `settings_store` block;
log kinds `chat.mode` and `chat.settings` classify ROUTINE; the chat row left `LOGS_GROUPS`.
`commands synced` **38 → 38, measured at boot** (a group already counted as one slot).

**The merge.** Five conflicts, all append-shaped, because both wave-3 branches appended at the
same anchors: `settings_store.py` (three hunks — the first two interleaved the automod and chat
KEY_HELP blocks around a shared help-text tail, resolved by splitting them back into two whole
blocks, automod first; the defaults hunk keeps all three `if key ==` lines), `labels.js`,
`tests/test_settings_store.py`, `sweeps.md` and `code-notes.md` (HEAD then branch, byte for
byte). The branch wrote its sweep rows as `C1`–`C8` on purpose — two builds numbering from 144
concurrently — and the conductor numbered them **155–162** at the merge and moved the
`OWNER_GUIDE.md` count 154 → 162. `docs/info/code-notes.md`'s `# Chat panel (wave 3)` section
was re-keyed to the merge. **4332 → 4402 tests** (`tests/test_chat_panel.py` is new;
`tests/cogs/content/test_chat.py` rewritten around the panel).

**Review finding, non-blocking, deferred to the fold sweep:** the `still_staff` / `defer` /
`db_ready` triplet is repeated **14×** in `cogs/content/chat.py` where automod has a cog-local
`opened()` helper — fold an `opened()` into `black_bloc/panels.py` in the same sweep as the
confirm helper, of which this build adds the **sixth** copy (`RemoveYesButton` / `KeepItButton`).
Cosmetic, not acted on: the **Settings** button lacks the ellipsis every other sub-panel
opener carries.

**Verified:** ruff clean; 4402 passed; boot clean at 22:58:25Z (`database ready` / `synced 38`
/ `logged in`, no Traceback). **NOT verified:** `/chat` was not opened in Discord — no note
written, no model called, no mood moved, the Limits modal not submitted, and the website chat
page not exercised after its routes moved onto `chat_panel`. Sweeps **155–162** are the
owner's to run, in `#mute-me-bot-test-spam`, as a Lead.

## 2026-09-04 — Automod panel: `/automod` is one window (wave 3 FIRST landing, v74, `0b1b2bf`)

Release **v74** (`0b1b2bf`, 15:45; `deploys.log` line 73). Merge `--no-ff` of
`worktree-agent-ae7bb4ba9c5540ad4` (Opus build, **370k** against a 300–360k estimate; three commits off
`5db58fb`: `8c5bee9` pure module, `d0fa2c9` cog, `220cacc` docs) after Fable review — approve with one
merge-time relabel: the Settings toggle read "Arming asks twice" / "Arming is one press" (the current
state) and now reads **Stop asking before arming** / **Ask before arming** (what it will do — the
standing button rule). **Clean merge, no conflicts.** The eight `/automod` leaf subcommands became one
staff panel: the pure `black_bloc/automod.py` holds the tables (`PANEL_MOVES`, `card_buttons`,
`root_buttons`, `settings_buttons`, `confirm_buttons`, `mode_options(current, may_arm)`,
`needs_confirm`, `rule_field_labels`, `exempt_options`, `typed`, `panel_minutes`, `arm_needs_confirm`;
`_as_words` learned newlines so the Words… modal matches the site's textarea) and the cog routes every
press through `opened()` (still_staff + defer + db_ready) to `run_rule` / `run_mode` / `run_exempt` /
`run_settings`; `arming_refusal` is read by both the mode select (so `on` is never offered while it
would be refused) and `set_mode` (so offer and verdict cannot disagree); the confirm card sits behind
`automod_arm_needs_confirm` (default true, owner fork F-A1 = a) and going quieter is one press;
bad words is one prefilled paragraph field, over 4000 chars says use the website (F-A2 = a);
`automod_warn_threshold` / `mod_dm_on_action` are read-only lines pointing at the Moderation page
(F-A3 = a). Enforcement untouched — `punish`, `do_delete`, `do_timeout`, `_answer_for` byte-identical.
Deviations at the design doc's foot (a Settings sub-panel exists, for the two new keys' Discord door —
checklist 33). Keys `automod_panel_minutes` (10) and `automod_arm_needs_confirm` (true) with their
`labels.js` + `server.mjs` rows; `LOG_LEVEL_COMMANDS["automod"]` and the `LOGS_GROUPS` automod row
retired. Verified: boot clean (22:45:04Z database ready / **synced 38** (38 → 38 as measured) /
22:45:08Z logged in, no Traceback), ruff clean, **4332 tests** (4265 + 67, none lost). NOT verified:
`/automod` has not been opened in Discord, no button pressed, no rule or exemption changed, no message
judged — sweeps 144–154 (`access/sweeps.md`) are the owner's. Review link: `/automod` in
`#mute-me-bot-test-spam`; the site's Automod page is unchanged at
<https://blackbloc.heygabi.ai/automod.html>. Deferred to their own items on `TODO.md`: the confirm
helper is now FIVE copies (memory, birthdays, youtube, pings, automod `build_confirm`/`confirm_buttons`)
— a fold sweep, not a merge-time edit; the settings-API-can-arm defect is **KI-21**; `LOG_LEVEL_COMMANDS`
is stale for eight features. The chat build was in flight in its own worktree when this shipped.

## 2026-09-03 — Voice panel: `/voice` is one window (wave 2 COMPLETE, v73, `4d64b36`)

Release **v73** (`4d64b36`, 22:08; `deploys.log` line 72). Merge `--no-ff` of
`worktree-agent-a386d425f5527fe95` (Opus build, **385k** against a 420–480k estimate — the first wave-2
build to land UNDER its estimate; five commits off `2854d74`: `128c716`, `492fe16`, `1f7fedd`, `c35fac6`,
`377dbcb`) after Fable review — approve, no defect; one merge-time fold per the build's own deviation 8:
`clamped()` and `DESCRIPTION_LIMIT` now live once in `black_bloc/panels.py` and the copies in the pings
and tempvoice cogs are gone. **Clean merge, no conflicts.** The 22 `/voice` + `/tempvoice` subcommands
became one ephemeral panel: the pure `black_bloc/tempvoice.py` holds the state table
(`panel_state` → blocked/none/owner/orphan/guest, `card_buttons`, `people_controls`, `undo_options`,
`named_regions` = 25 so no select is capped) and the cog's `VoicePanel` routes every press to the
existing `do_*` helpers (`act_on_own` re-reads ownership on every press, `ready_to_move` defers +
`db_ready`); staff moves (Setup, Forget a lobby…, join-to-create on/off, Logs, the staff card's
Hand it over… with a DM to the new owner) re-ask `still_staff` on every press; the in-channel control
post is untouched (owner fork F1 = "Leave it as is"). 13 deviations at the design doc's foot, all
P-consistent (Forget a lobby lists stored ids only — a stray cannot be forgotten, so it is not offered).
Key `voice_panel_minutes` (10) with its `labels.js` + `server.mjs` rows. Verified: boot clean
(05:08:39Z database ready / **synced 38** (39 → 38 as measured) / 05:08:43Z logged in, no
Traceback), ruff clean, **4265 tests** (4050 + 215, none lost). NOT verified: `/voice` has not been
opened in Discord, no button pressed, no channel renamed/locked/moved, no DM sent — sweeps 135–143
(`access/sweeps.md`) are the owner's. Review link: `/voice` in `#mute-me-bot-test-spam`. Cost note for
the calibration table: memory 329k, golive 464k, youtube 371k, pings 379k, voice 385k — the ~2× pattern
held for the first two and not the last three.

## 2026-09-03 — Decision: YouTube lives stay with `/golive`; uploads stay on shadow (no build)

Owner asked at 17:59 to announce a linked channel *going live* on YouTube by default and make
"every upload" an opt-in switch, off by default. Fable's read: the uploads sweep deliberately skips
live broadcasts (`cogs/content/youtube.py` `_skipped` → "live") because `/golive` already announces
YouTube lives from Discord presence (`golive.py` `platform_of`), and without `YOUTUBE_API_KEY` (not
set on Fly, measured 18:00) the public feed cannot tell a live from an upload (phase 16 D6). Told
that, the owner withdrew it at 18:05: **do not add live detection to `/youtube`; keep `youtube_mode`
on shadow for now; going on is a staff decision** — which it already is (Setup on the `/youtube`
panel and the Go-live page switch are both staff-gated). Nothing changed in code or settings;
`youtube_mode` is `shadow` since 17:42 (F-Y2). If uploads are ever wanted on, staff flip the switch;
if YouTube lives ever need catching without presence, that is the withdrawn design plus the API key.

## 2026-09-03 — Pings panel: `/pings` is one window (wave 2, v72, `a5ad521`)

Release **v72** (`a5ad521`, 18:30; `deploys.log` line 71). Merge `--no-ff` of
`worktree-agent-a86e71fd801362ca2` (Opus build, **379k** against a 300–360k estimate — the first wave-2
build to land near its estimate; four commits off `85e14c4`: `ec1a54e` extractions, `cb73075` the cog,
`13450dd` strings and docs, `cf70ec8` the checklist sweep) after Fable review — approve, one defect fixed
at the merge: `run_settings` appended the Names… modal's "Saved. A streamer's ping role will be called…"
echo even when `save_settings` had refused a value, so a failed save read as a success; the echo now
follows only a `SETTINGS_SAVED` answer. **Clean merge, no conflicts** (the branch was cut after golive
and youtube were both in). Verified: boot clean (01:30:29Z database ready / **synced 39** / 01:30:33Z
logged in), ruff clean, **4050 tests** (3872 + 178, none lost). This deploy also applied the staged
`OPERATOR_READ_TOKEN` (see the entry below). NOT verified: `/pings` has not been opened in Discord, no
button pressed, no select submitted, no role moved — sweeps 126–134 and the rewritten 38–42
(`access/sweeps.md`) are the owner's. Whether a real Discord client submits an EMPTY `RoleSelect`
(`min_values=0`) is the one open question; both paths are built (the confirm button also means "make
one"), so either answer works.

What shipped. `/pings` is a single member-visible command opening an ephemeral panel; the `pingroles`
group and the twelve `pings`/`pingroles` subcommands are retired — both decided forks built as decided
(**I1 = (a)** a streamer may always take their own ping role away, whatever `pings_fan_role_creation`
says; **I2 = (b)** one Events toggle while the go-live and event keys agree or either is unset, two
labelled toggles once they point at different roles). Members: **Follow a streamer…** / **Stop
following…** selects (25-capped, the placeholder says so), the Events toggle(s), **Start my own ping
role** (only when they stream and creation is not staff-only), **Take my ping role away** behind
**Keep it / Yes, take it away**, **Refresh**; unfollowing is never mode-gated. Staff: **Streamers…**
(lines with follower counts, a streamer picker to a card with **Remove their ping role** behind a
confirm and **Make the role again** when Discord no longer has the role, **Give somebody a ping role…**
user-select into the shared role-pick step), **Set up the Events role** (the same role-pick step:
`RoleSelect` `min_values=0`, empty means make one), **Settings** (mode / who may start one / on-unlink
selects, a delete-too toggle, **Names…** modal for the Events role name, the streamer template and the
panel minutes — the template is echoed as it will RENDER, checklist 17), **Logs**, **Open on the site**.
The button table is `panel_buttons(PanelState, staff=)` in `black_bloc/pings.py`, proved as data by a
128-case parametrised test (deviation 1: a composing function over a NamedTuple, not a dict, because I2
makes the events half variable-length). New shared moves `follow_streamer`, `set_event_pings`,
`start_own_fan_role(streams=)`, `stop_own_fan_role`, `save_settings` (validates every key with
`coerce_value` before the first write; new `pings.settings` log kind), `notification_lines`,
`streamer_lines`, `counts_of`, `template_preview`. `panels.site_page_url(origin, feature)` is now the one
home; applications/polls/events/golive/requests delegate, the youtube cog's copy deliberately left
(returns `""` and uses its own `SITE_PAGE` — folding it would change a just-landed file). Key
`pings_panel_minutes` (10), checklist 33; a second `LABEL_LIMIT = 100` deleted (checklist 15); two test
doubles repaired (`FakeGuild.create_role` reused ids after a deletion). Design
[`info/pings-panel-design.md`](info/pings-panel-design.md) (seventeen deviations at its foot);
`OWNER_GUIDE.md` 125 → 134 rows; `code-notes.md` pings keys point by anchor on the branch (NOT re-keyed
against `a5ad521`). Review link: `/pings` in `#mute-me-bot-test-spam`; the Go-live tab of
https://blackbloc.heygabi.ai/golive.html shows the same ping roles.

## 2026-09-03 — Operator read token: minted, deployed, door verified (v72)

Code shipped in v67 `285b5e3` (16:04; the build record is the entry below). The mint was blocked twice
by the permission classifier (the `flyctl secrets set` command at 16:15; the session editing
`~/.claude/settings.json` at 16:30), so at 17:55 the owner ordered the session to do both ("Do this:
\scripts\mint-operator-token.ps1 in ~/.claude/settings.json, then say retry"): the rule
`PowerShell(.\scripts\mint-operator-token.ps1:*)` went under `permissions.allow`, the script ran at
17:56 (python mints, `flyctl secrets set --stage`, HKCU `BLACK_BLOC_OPERATOR_TOKEN`; value never
printed), `flyctl secrets list` showed **Staged** (digest 6158ac0c…). v72 (`a5ad521`, 18:30) applied it —
**Deployed** — and the door was measured at 18:31: `GET /api/settings` with the bearer **200**, the same
request anonymous **401**; `/api/health` is not a route (404 — the health door is `/health`). NOT
verified: the `web.operator.read` Core log row (`operator_read_log`) was not looked for. Runbook:
`access/operator-read.md`. History as it stood in `TODO.md` at landing:


- **Operator read token — MINTED 17:56, STAGED, goes live at the next deploy (the pings release);
  moves to `DONE.md` once a bearer read is verified live.** (Code live v67 `285b5e3` 16:04; the build
  record is in `DONE.md` 2026-09-03.) 17:55 the owner ordered the session to add the rule itself
  ("Do this: \scripts\mint-operator-token.ps1 in ~/.claude/settings.json, then say retry") — rule added,
  script ran, `flyctl secrets list` shows `OPERATOR_READ_TOKEN` **Staged** (digest 6158ac0c…),
  `BLACK_BLOC_OPERATOR_TOKEN` set for the user (64 chars), value never printed. Verify after the
  deploy: `/api/health` with the bearer answers, and `operator_read_log` writes one Core row. History: The blind mint (`docs/access/operator-read.md`, one command: python mints,
  `flyctl secrets set --stage`, HKCU `BLACK_BLOC_OPERATOR_TOKEN`, value never printed) was approved by
  the owner 16:00 ("Yes") but the permission classifier BLOCKED the command at 16:15. Owner chose the
  permission-rule route (16:30: "Add a permission rule for flyctl secrets set … and tell me to retry");
  the classifier ALSO blocked the session editing `~/.claude/settings.json`, so the owner adds the rule
  himself — `PowerShell(.\scripts\mint-operator-token.ps1:*)` under `permissions.allow` — then the
  session retries `.\scripts\mint-operator-token.ps1` (the mint wrapped as a script so a rule has a
  stable prefix to match; `access/operator-read.md`). Until the secret is set the door does not exist
  (`/health` + a bearer answer `not_signed_in`, verified live by the builder). `--stage` means it
  applies at the NEXT deploy — v68.

## 2026-09-03 — YouTube panel: `/youtube` is one window (wave 2, v71, `b764757`)

Release **v71** (`b764757`, 17:37; `deploys.log` line 70). Merge `--no-ff` of
`worktree-agent-a74823f4d9293d080` (Opus build, **371k** against a 180–250k estimate — the third wave-2
build to run ~2× its estimate; three commits off `ea252bd`: code `7809b57`, tests `7f800cb`, docs) after
Fable review — approve, no blocking defect (one path per move with `via`; `LinkRefused` keeps the site's
400/409; `still_staff` gates every non-mine path; the DM'd reason is a key; both keys registered). Six
merge conflicts, every one an append-only collision with the golive merge (`personas.py` both panel
lines; `settings_store.py` both key blocks; `phase16-design.md` both SUPERSEDED banners; `sweeps.md` —
the branch wrote its rows as 130–137 because golive had reserved 109–129, so they were **renumbered to
118–125 at the merge** and row 47's cross-reference with them; `OWNER_GUIDE.md` 125 rows; `code-notes.md`
header). Both branches had pinned `tests/test_bot.py` at 41 for their own drop; together it is **40**, so
the test now says 40. Verified: boot clean (00:37:42Z database ready / **synced 40** / 00:37:45Z logged
in), ruff clean, **3872 tests** (3796 + 76, none lost). **F-Y2 done 17:42**: `youtube_mode` flipped
off → shadow from the Go-live page's "Whether the bot posts new YouTube uploads" switch — `PUT
/api/settings/youtube_mode 200` on Fly at 00:42:53Z, `/api/settings` reads `shadow`. (The first two
attempts, clicked by accessibility ref, never reached the switch's handler and the tree then misreported
"on" as pressed — the value was checked at the API before and after, and a real DOM click did it.) NOT
verified: `/youtube` has not been opened in Discord, no button pressed, no modal submitted, nothing
fetched from YouTube — sweeps 118–125 (`access/sweeps.md`) are the owner's.

What shipped. `/youtube` is a single member-visible command opening an ephemeral panel; the `youtube`
and `uploads` groups and their nine subcommands are retired — both decided forks built as decided
(**F-Y1 = `/youtube` and `/golive` stay separate**, **F-Y2 = shadow at landing, by the conductor on the
site**, owner 16:15). Members: **Link my channel** (one-line modal; **Relink** afterwards, prefilled) and
**Unlink** behind a **Keep it / Yes, forget it** confirm, from a `card_buttons(linked, mine, staff)`
table keyed `(mine, linked)`. Staff: the health block inline (`health_lines` — sweep running, last good
sweep, last error, counts, API key set or not), the linked list as lines beside a linked-member picker
(deviation 3), **Link for somebody**, **Relink for / Unlink for** on their card (the unlink DMs the
member the reason via `tell_unlinked` when `youtube_unlink_dms_them` is true — a member unlinking their
own is never DMed), **Setup** (upload channel, ping role, off/shadow/on select, words, numbers, and a
**Forget…** view with Back — deviation 4) and **Logs**. One function per move with `via`
(`link_channel/unlink_channel/set_mode/save_setup`) serves BOTH doors: `api/tools/youtube.py` now calls
them with `via=VIA_WEBSITE`; `link_channel` raises `LinkRefused(status=, code=)` and returns
`(said, row, counted)` so the site keeps its exact 400/409 bodies without a second YouTube resolve
(deviation 1); `save_setup` validates every value with `coerce_value` before writing any (deviation 9);
`YouTubeError` carries a `network` flag decided at the raise site (deviation 7). Keys
`youtube_panel_minutes` (10) and `youtube_unlink_dms_them` (true), checklist 33. §K finding 1 fixed
because checklist 10 forced it (a link whose feed did not answer no longer claims "0 counted as seen");
findings 2, 3, 4, 6 reported and left, 5 moot. Design
[`info/youtube-panel-design.md`](info/youtube-panel-design.md) (eleven deviations at its foot);
`OWNER_GUIDE.md` and `code-notes.md` youtube keys point by anchor on the branch (NOT re-keyed against
`b764757` — anchor text is authoritative). Review link: `/youtube` in `#mute-me-bot-test-spam`; the
YouTube uploads section of https://blackbloc.heygabi.ai/golive.html shows the switch on shadow.

## 2026-09-03 — Go-live panel: `/golive` is one window (wave 2, v70, `0aeed72`)

Release **v70** (`0aeed72`, 17:25; `deploys.log` line 69). Merge `--no-ff` of
`worktree-agent-a87a00d41b8dc47d1` (Opus build, **464k** against a 230–300k estimate — the second wave-2
build to run ~2× its estimate; four commits off `8cbe453`: code, tests, the cross-feature string sweep,
docs) after Fable review — approve, no blocking defect. Four merge conflicts, every one an append-only
collision with the memory merge (`settings_store.py` both `*_panel_minutes` blocks; `sweeps.md` memory
rows 104–108 then golive rows 109–117 — the numbering held, nothing renumbered; `OWNER_GUIDE.md` 117 rows
plus the golive row; `code-notes.md` header, both sentences kept). Verified: boot clean (00:25:01Z
database ready / **synced 41** — the 42 → 41 drop the build measured through `tests/test_bot.py` is now
measured at a real boot / 00:25:05Z logged in), ruff clean, **3796 tests** (3750 + 46, none lost). NOT
verified: `/golive` has not been opened in Discord, no button pressed, no Helix call made —
sweeps 109–117 (`access/sweeps.md`) are the owner's.

What shipped. `/golive` is a single member-visible command opening an ephemeral panel; the `golive` and
`twitch` groups and their eight subcommands (`/twitch link`, `/twitch unlink`, `/golive optout`,
`/golive optin`, `/golive status`, `/golive mode`, `/golive test`, `/golive logs`) are retired — both
decided forks built as decided (**I1 = `/golive`**, **I2 = the staff `Streamers…` sub-panel**, owner
16:10). Members: **Link my Twitch channel** (one-line modal; **Change my channel** afterwards,
prefilled), **Unlink**, and exactly one of **Stop announcing my streams** / **Announce my streams
again** from a `panel_buttons(linked, opted_out, staff)` table proved by a parametrised test. Staff: the
whole of the old status embed inline (mode, stream end, channel, cooldown, twitch polling, last good
poll, last poll error, counts, who is live now — in test mode the channel line SAYS when
`golive_channel_id` is not the test channel), **Logs**, **Streamers…** (unlink or opt out somebody else,
the same moves the Go-live page makes), **Preview an announcement…** (ephemeral, never pings, never
posts) and an **off / shadow / on** select. One function per move with `via`
(`link_channel/unlink_channel/opt_out/opt_in/set_mode`) serves BOTH doors: `api/tools/golive.py` now calls
them with `via=VIA_WEBSITE`, so the fan-role step (`pings.maybe_auto_create` / `pings.on_streamer_left`)
finally runs on the website too — it was the configured behaviour the site was quietly not honouring
(deviation 3). `checked` now means *a Helix lookup confirmed the channel* (`twitch_user_id is not None`);
the old `helix is None` expression would have written `checked: true` into `action_log` beside a route
body saying `false` — found by `tests/api/tools/test_golive.py`, not by reading (deviation 1). One key
`golive_panel_minutes` (default 10, checklist 33; `labels.js` entry). Design
[`info/golive-panel-design.md`](info/golive-panel-design.md) (eight deviations at its foot); rows 12,
19, 31, 49 of `sweeps.md` and the Phase 2 appendix rewritten in place; `OWNER_GUIDE.md` gains the
"Link your Twitch" row; `code-notes.md` golive keys re-pointed by anchor on the branch (NOT re-keyed
against `0aeed72` yet — anchor text is authoritative). Findings left open, small: the Logs button loses
`/golive logs`'s `count`/`important_only` (same as every wave-1 panel; a modal if wanted back); the
four earlier `*_panel_minutes` keys (event/poll/birthday/request) still lack `labels.js` /
`site/mock/server.mjs` labels (🔧 in `TODO.md`). Review link: `/golive` in `#mute-me-bot-test-spam`.

## 2026-09-03 — The request card is the Discord record of a move (v69, `5a97a19`)

Release **v69** (`5a97a19`, 17:14; `deploys.log` line 68). Built in the main loop — one flag
through three files. Verified: boot clean (00:13:53Z database ready / synced 42 / 00:13:57Z
logged in). NOT verified: no request moved in Discord after the deploy — the proof is accepting
one in `#mute-me-bot-test-spam` and seeing the card alone. The item, whole:

- 🆕 **The request card is the official Discord close format, not the raw `request.done`
  box (owner, 2026-09-03 ~17:00, with a screenshot of `#mute-me-bot-test-spam`: "I don't want
  the request.done part in discord I want the other box as the official close format").**
  Diagnosis: the raw box is the action-log mirror (`log_channel_id`, `request_log_level`
  default `important`, `request.done` in `IMPORTANT`); the green card is the request's own
  status post (`notify_move` → `request_status_channel_id`/`request_notify_channel_id`). Both
  were pointed at the test channel, so every move showed twice. Design: `log_action(...,
  carded=True)` skips the raw embed at `important` when the caller is posting its own card
  (`requests.card_will_post` = move enabled in `request_channel_moves` AND a status channel
  set); the DB row and the Logs page are untouched; `request_log_level = all` still restores
  the raw line beside the card (configurable both ways, checklist 33); `notify=True` still
  outranks it. Status: **BUILT in the main loop ~17:10** (Fable, small) — `logkinds.should_post`,
  `actionlog.log_action`, `requests.card_will_post`, the cog's `apply_decision` /
  `resume_request` / `ask_check`; +6 tests (3750); **SHIPPED v69 `5a97a19` 17:14**.

## 2026-09-03 — Memory panel: `/memory` is one window (wave 2, v68, `cb941d9`)

Release **v68** (`cb941d9`, 16:48; `deploys.log` line 67). Merge `--no-ff` of
`worktree-agent-aaaa13e778f0ba65a` (Opus build, **329k** against a 120–180k estimate — wave-2 builds
run ~2× their estimate; five commits off `8cbe453`) as `cb941d9` after Fable review — no blocking
defect. `/memory` is a single command opening an ephemeral panel: every fact numbered (`Fact` layer in
`chat_memory.py`: name, notes, threads, DM-learned lines marked), a `Forget one of these…` select
capped at 25 that re-reads the line by text before dropping it (a distillation can land between render
and click → `PROFILE_MOVED`, nothing wrong is ever dropped), `Forget by words…` modal only above the
cap, `Forget everything` and `Stop remembering me` behind an Are-you-sure, `Remember me again`,
`Refresh`. Moves come from the fact count, never the consent, so the forget controls work with
`chat_memory_mode` off — **fork I-M1 = OPEN IT** (owner 16:12), the `HIDDEN_WHEN_OFF` entry for
`memory` removed. The web Forget now routes through the cog's `forget_profile(via=)` so both doors are
one write + one log row (checklist 34; the route's hand-built `web.` kind is gone and the logkinds AST
guard now asserts zero unchecked computed kinds). `db_up` moved from `applications.py` into
`panels.py` (checklist 17). One key `memory_panel_minutes` (default 10, checklist 33; labels.js
entry). Every re-render carries `allowed_mentions=none()`. 3710 → **3744 tests**, ruff clean, `commands
synced` 42 (the group was already one slot). Design
[`info/memory-panel-design.md`](info/memory-panel-design.md) (fifteen deviations at its foot); sweep
rows 104–108 (`access/sweeps.md`); `OWNER_GUIDE.md` sweeps count corrected 95 → 108 (two builds
stale). Verified: boot log 23:47:54Z database ready, 23:47:55Z synced 42 app commands, 23:47:58Z logged in, no Traceback. **NOT verified:** nothing opened in Discord — the five sweep rows
are the owner's; `chat_memory_mode` is off live so 104–107 need it on plus a conversation first.
Findings left for the next touch of each file: `api/tools/chat_memory.py` `CONTENTS_ARE_PRIVATE` and
its mock copy still name `/settings set chat_memory_staff_view full` (a subcommand that takes a
channel); four wave-1 `_panel_minutes` keys still lack a `labels.js` entry; five wave-1 panels edit
without `allowed_mentions`.

## 2026-09-03 — Operator read token: the session's read-only door (v67, `285b5e3`)

Release **v67** (`285b5e3`, 16:04; `deploys.log` line 66). Merge `--no-ff` of
`worktree-agent-aa960a4c8635193e0` (Opus build, 268k, four commits off `c790efb`) after Fable review —
no blocking defect: `operator_session` runs before the cookie path and returns `None` when no bearer is
offered or none is configured (an unconfigured server is byte-for-byte today's behaviour, verified live
by the builder: `/health` + a bearer answered `not_signed_in`); `hmac.compare_digest` on the token; a
dedicated 30/min bucket per client IP consumed on every bearer request; GET/HEAD only, anything else
`403 operator_read_only` in words; one `web.operator.read` Core row per request guarded by
`request.state.operator_noted` (checklist 34) and switchable by `operator_read_log` (bool, default true,
`CORE_KEYS` 5 → 6, registry 162 → 163 — checklist 33); the identity is `{"id": "0", "name": "operator",
"staff": True, "member": False}` so `/api/requests/mine` is deliberately unreadable. Third Via word
**Operator token** (`VIA_WORDS`, a Logs-page pill). `scripts/read.ps1 -Path /api/…` is the one command a
session reads live state with (env var, falling back to the HKCU User variable so a long-running parent
shell sees a fresh mint). 3697 → **3710 tests**, ruff clean; `commands synced` 42 unchanged. Design
[`info/operator-read-design.md`](info/operator-read-design.md) (six deviations at its foot), access
[`access/operator-read.md`](access/operator-read.md); sweep row 103; `RECOVERY.md` names the secret.
The builder's GET-route audit: no `current_session` GET writes; the two OAuth GETs never see the bearer.
Verified: boot log 23:04:42Z database ready + synced 42, 23:04:46Z logged in, no Traceback. **NOT
verified / NOT done: the secret is not set.** The owner approved the blind mint 16:00 ("Yes"); the
permission classifier blocked the command at 16:15, so the mint moved back to `TODO.md` as owed. The
door does not exist live until `OPERATOR_READ_TOKEN` is set AND the next deploy runs (`--stage`).

The item as it stood on `TODO.md`, moved whole:

> 🆕 **Operator read access for the session (owner, 2026-09-03 14:24: "Make apis that you can
> access so you can see things. Or use my explicit permission to check it").** Today a live
> read means `flyctl ssh console` + SQLite, which the permission classifier blocks about half
> the time. Proposed (awaiting owner yes/no): one `OPERATOR_READ_TOKEN` (Fly secret, name only
> here) accepted as a bearer on GET-only `/api/*` — the same JSON the dashboard reads, no new
> endpoints, no writes; every use logged with Via: operator; rate-limited like a session.
> ~40k Opus build. Interim: the owner's explicit permission in chat, then retry the `flyctl ssh`
> read. **DECIDED YES (owner, 2026-09-03 15:07: "Yes do it") — build DISPATCHED 15:10** (Opus,
> own worktree; design in the brief → `info/operator-read-design.md`; access doc
> `access/operator-read.md`; the token is minted and set by the owner, never seen by a session).

## 2026-09-03 — Panels wave 1 COMPLETE, fourth landing: `/apply` is one command (v66, `853776c`)

Release **v66** (`853776c`, 15:00; `deploys.log` line 65). Merge `--no-ff` of
`worktree-agent-abf063b9177e02f17` (Opus build, 401k, nine commits) after Fable review — no blocking
defect: every staff move `still_staff` → defer → `db_ready`, member moves and Back buttons re-render
against the actor, the persistent card buttons still pass `may_decide`, one log row per write
asserted by count. Two doc conflicts (`OWNER_GUIDE.md`, the design header), both sides kept;
**3697 tests** green under `-n auto`; `commands synced` **43 → 42** on the boot log — the Group
drop §B predicted. All three owner forks built as decided: **I-A1 `/apply`** ("gamer lingo",
13:35), **I-A2 Visible** (`HIDDEN_WHEN_OFF["applications_mode"]` gone, the off-panel says so in
words, 13:47), **I-A3 the Questions sub-panel** (select → Edit / Remove, plus Add; reorder stays
on the site, 14:12). Both the `apply` and `applications` groups and their seventeen subcommands
are gone; `denied` / `removed` gained the `Approve after all` / `Put them back on the list` exit
(staff final say). Design: [`info/applications-panel-design.md`](info/applications-panel-design.md)
(15 deviations at its foot — headline: `update_form` clears four id columns from the `NO_ROLE`
sentinel, a `db_up` gate for reads before a defer). Sweep rows 94–102; rows 53–57 and 69–72
rewritten. Keys `applications_panel_minutes` / `applications_panel_own_list`. Site: two label
strings on https://blackbloc.heygabi.ai/rolemenus.html#applications. Verified: boot log 22:00:05Z
database ready + synced 42, 22:00:08Z logged in, no Traceback. NOT verified: nothing by eye in
Discord; the empty-select submit edge (§C) is still unverified on every panel that has one.

**Wave 1 is complete** — `/birthday` v63, `/event` v64, `/poll` v65, `/apply` v66, all in one
afternoon (13:58–15:00), 44 → 42 commands, 3442 → 3697 tests. The panels program item stays on
`TODO.md` for waves 2–4 (`info/panels-program.md` §5). Filed request #2 (Twitch Team form via the
bot) is what this landing delivers; it sits in *review* on the Requests page for the owner to mark
done.

## 2026-09-03 — Panels wave 1, third landing: `/poll` is one command (v65, `d13e1a4`)

Release **v65** (`d13e1a4`, 14:14; `deploys.log` line 64). LANDING entry — the panels item stays
on `TODO.md` until applications lands. Merge `--no-ff` `27452ac` of `worktree-agent-aa735ab092d13477d`
(Opus build, 458k). Four conflicts against the events landing (`settings_store.py`, `sweeps.md`,
`info/README.md`, `code-notes.md`), every one resolved by keeping both sides; 3644 tests green
under `-n auto`. Fable review at pattern level found no blocking defect (`still_staff` 9 sites,
defer 15, `db_ready` 10, `retire` 5, `allowed_mentions` 11, `log_action` 30; the `LATER_KINDS`
deviation is not a regression). Notes on `TODO.md`: `draft` status is never written, no
create-recurrence web route. What shipped: `/poll` opens one panel (Create · Find # · Refresh, plus
Settings · Logs for staff); create is a two-step modal → preview, nothing written until **Post it**;
picking a poll IS the results card with End / Cancel / Approve / Deny rendered only when valid;
a denied poll keeps **Post it anyway** (staff final say); recurrence cards run the same code as the
dashboard. `commands synced` **43 unchanged** (`/poll` was already one slot). Design:
[`info/polls-panel-design.md`](info/polls-panel-design.md) (9 deviations at its foot). Sweep rows
80–86 (rows 6, 8, 9, 27 rewritten). Keys `poll_panel_minutes` / `poll_creator_may_end` on
https://blackbloc.heygabi.ai/settings.html. Verified: boot log 21:14:17Z database ready, 21:14:18Z
synced 43 app commands, 21:14:23Z logged in, no Traceback/Error. NOT verified: nothing by eye in
Discord or on polls.html.

## 2026-09-03 — Panels wave 1, second landing: `/event` is one command, `/timezone` retired (v64, `e670542`)

Release **v64** (`e670542`, 14:05; `deploys.log` line 63). LANDING entry — the panels item stays
on `TODO.md` until polls and applications land. Merge `--no-ff` of `worktree-agent-a448c7ab780ed3c2b`
(= `feat/events-panel`; Opus build, 433k). Six merge conflicts against the birthdays landing
(`settings_store.py`, `tests/test_bot.py`, `OWNER_GUIDE.md`, `sweeps.md`, `architecture.md`,
`code-notes.md`), every one resolved by keeping both branches' blocks; 3560 tests green under
`-n auto` before the commit. Fable review found no blocking defect — the one note: the
`confirm_cancel` Yes button trusts the panel's opener pin instead of re-running `may_cancel`
(on `TODO.md`). What shipped: `/event` opens the member panel (Propose, `My time zone` modal,
`Call one off…`) or the staff panel; the whole `/timezone` group is gone, the program's first
real `commands synced` drop (44 → 43); the shared layer moved to `black_bloc/events.py`
(`apply_decision`, `cancel_for` — which now also renames the review channel — `card_buttons`,
`option_label`, `list_lines`). Design: [`info/events-panel-design.md`](info/events-panel-design.md).
Sweep rows 73–79. Keys `event_panel_minutes` / `event_panel_own_list` on
https://blackbloc.heygabi.ai/settings.html. Verified: boot log 21:05:00Z database ready,
21:05:01Z synced 43 app commands, 21:05:04Z logged in, no Traceback/Error. NOT verified: nothing
by eye in Discord or on events.html.

## 2026-09-03 — Panels wave 1, first landing: `/birthday` is one command (v63, `616adb3`)

Release **v63** (`616adb3`, 13:58; `deploys.log` line 62). This is a LANDING entry, not a
move — the panels item stays on `TODO.md` until events, polls and applications have landed
too. Merge `--no-ff` `58974e1` of `worktree-agent-a19bdce15408f8243` (Opus build, 412k; Fable
review found no defect: `still_staff` before every `defer()`, `db_ready` after, `retire(previous)`
on every re-render, `allowed_mentions=none()` on every send, one `log_action` per write with the
kinds unchanged, `DateModal` reads its prefill before acknowledging so the modal can follow).
Design: [`info/birthdays-panel-design.md`](info/birthdays-panel-design.md) (14 deviations at its
foot). Sweep rows 87–93. Keys `birthday_panel_minutes` / `birthday_panel_next_for_members` /
`birthday_panel_lookup` on https://blackbloc.heygabi.ai/settings.html.

**The gate refused the first attempt (13:52)** on
`tests/api/test_settings_api.py::test_writes_are_rate_limited_per_session` — the wall-clock flake
both wave-1 build agents had reported: `TokenBucket` refills one token a second, so sixty PUTs
that take over a second under `-n auto` let the sixty-first through. Fixed in `616adb3` by
stubbing `auth.time` to one instant for that test (`code-notes.md` →
`tests/api/test_settings_api.py:221`); three consecutive whole-suite runs green before the redeploy.
Verified: boot log 20:58:15Z database ready, 20:58:16Z synced 44 app commands, 20:58:20Z logged
in, no Traceback/Error. NOT verified: nothing by eye in Discord or on settings.html.

## 2026-09-03 — Applications without a role: keep a list instead (v62, `9891f71`, schema 28)

Release **v62** (`9891f71`, 12:48; `deploys.log` line 61). Merge `--no-ff` of `feat/applications-no-role` after `feat/requests-check` (`SCHEMA_VERSION` 27 → 28 resolved at the merge); Fable review found no defect and reworded `REMOVE_IS_FOR_LISTS` (a `/role revoke` ends the grant, the approval stays on record — nothing in the revoke path touches `applications`). 3442 tests, ruff clean. Boot log 19:47:59Z: `rebuilding application_forms so a form may have no role` (the C1 rebuild ran on the live DB), logged in 19:48:03Z, no errors. ⚠️ NOT verified by eye: owner sweeps 69–72. The 🔧 item moved here whole:

- 🆕 **Applications without a role — "let's have the bot store the info!" (owner, 2026-09-03
  ~12:10, relaying a member's Discord question verbatim: "is there a way for the twitch team
  app to be done without a role? if not we may wanna think of adding a stream team role (which
  might just be a good reference point to see who's applied and who would need to show up on
  the team page)" → owner: "we can do no role and have the bot store the information or … a
  temporary role … let's have the bot store the info! that way we can check the site and the
  official team page").** Measured at `46e3ba4`: **not possible today** —
  `application_forms.role_id` is `NOT NULL` (`storage/db.py:576`), `/applications create`
  takes `role: discord.Role` as a required option (`cogs/community/applications.py:877`), and
  `_hand_over` (`:461`) always grants. The applications themselves ARE already stored
  (`applications` table: answers, status, who decided, when), so the roster exists in the DB
  today — what is missing is (1) a form that grants nothing, (2) a roster on the site to
  compare with the official Twitch team page. Design: `info/applications-no-role-design.md`
  — role optional on create/edit (slash AND dashboard editor, checklist 33), schema **28**
  makes `role_id` nullable (SQLite table rebuild, the `mod_cases` precedent at
  `db.py:660–664`), approve on a role-less form skips `_hand_over` and the "hand it over with
  `/role grant`" fallbacks and DMs `approved_text` + `next_step` as today, an **Approved
  roster** per form in the Applications section of the Role menus page (name · approved when
  · Twitch login from `golive_links` when linked, so it reads against twitch.tv/team/…) with
  a plain-text copy. Status: **BUILDABLE** (2026-09-03 ~12:20) —
  [`info/applications-no-role-design.md`](info/applications-no-role-design.md) written: role
  optional per form (slash `role`/`no_role` on edit + the dashboard editor's "No role — keep a
  list"); roster = approved applications, one home; new terminal status `removed` with a DM'd
  reason (the only way off a no-role list — D2); `GET /api/applications/roster`, `POST
  /{id}/remove`, roster foldout per form with Twitch login + Copy as text; one setting
  `applications_roster_shows_left` (default true). ⚠️ Gotcha caught in design: the table
  rebuild must run BEFORE `PRAGMA foreign_keys=ON` or `DROP TABLE application_forms`
  cascade-deletes every question (§C1). Different cog from the "ask them to check" item, so
  the two builds can run beside each other; both bump `SCHEMA_VERSION` — second to merge
  re-keys. Owner answered the one question 2026-09-03 ~12:30: **"Always give staff final say
  and permission"** — staff removal stays in, and the sentence is now a `CLAUDE.md` rule.
  Then "Build all, keep going" → Opus build dispatched on `feat/applications-no-role`
  (2026-09-03 ~12:35), beside `feat/requests-check` — which merged first (`44170f4`, v61,
  schema 27). **BUILT** on that branch (2026-09-03,
  four commits, `SCHEMA_VERSION` 28): 3414 tests pass, ruff clean, `check.mjs` 17 pages /
  141 routes; five deviations at the foot of the design doc. ⚠️ **NOT merged, NOT deployed,
  and not exercised against Discord or the live site** — `access/sweeps.md` rows **69–72**
  are the owner's by-eye checks. Still open: merge (whichever of the two branches lands
  second re-keys `SCHEMA_VERSION` and `code-notes.md`), deploy, then the sweep. This item
  moves whole to `DONE.md` when it is live, not before.

**SHIPPED** 2026-09-03 12:48 in v62. Design: [`info/applications-no-role-design.md`](info/applications-no-role-design.md) (five build deviations at its foot). Review link: https://blackbloc.heygabi.ai/rolemenus.html#applications

## 2026-09-03 — Requests sixth pass: "Ask them to check" (v61, `44170f4`)

Release **v61** (`44170f4`, 12:29; `deploys.log` line 60). The 🔧 item moved here whole:

- 🆕 **"We also need a way to ping the requester from the request app. I want to have it
  message the requesters to check the work." (owner, 2026-09-03 11:15).** A staff move on the
  request card (panel AND the site's request card — one shared function, one log row) that
  tells the person who asked that the work is ready for THEM to try: a DM built from the same
  `request_embed` (built + how-to-test filled in) with a sentence asking them to check it and
  say so, falling back to a mention in the request channel when their DMs are closed. Which
  states offer it, whether it is its own state or a flag on `review`, and the fallback are
  design calls — the owner said "Keep building", so no fork went to him. Status:
  **BUILDABLE** (2026-09-03 ~12:05) — [`info/requests-check-design.md`](info/requests-check-design.md)
  written: an ACTION on the review card, not a state (§B); `check_asked` look + DM, channel
  ping fallback (`request_check_fallback_channel`, default on), `request_check_on_ready`
  (default off), schema 27, `POST /api/requests/{id}/check`; six owner-flippable calls in §D.
  Owner 2026-09-03 ~12:30: "Build all, keep going" → Opus build dispatched on
  `feat/requests-check` from `main` ≥ `fbb1191` (~12:35), beside `feat/applications-no-role`.
  Status: **BUILT, not merged, not deployed** (2026-09-03, branch `feat/requests-check`, four
  commits) — `ask_check` shared by the panel button and `POST /api/requests/{id}/check`, the
  `check_asked` card, the channel-ping fallback, both settings, schema 27, 28 new tests
  (3399 pass, ruff clean, mock 17 pages / **140** routes). Owner checks are sweeps
  [66–68](access/sweeps.md). ⚠️ Both this branch and `feat/applications-no-role` bump
  `SCHEMA_VERSION` to 27 — whichever merges second re-keys to 28. Nothing here has been seen
  in live Discord or on the deployed site.
  **SHIPPED** (2026-09-03 12:29, v61 `44170f4`): merged first, so this one kept schema **27**
  and the applications build already carries 28. Fable review found one defect — `moment()`
  stamped the DM'd check card with `decided_at` (the ready time) instead of `check_asked_at` —
  fixed at the merge with a column map and a test line. 3399 tests in the gate, release 15 s
  after exit, boot log 19:29Z clean (synced 44 commands). By eye NOT done: sweeps 66–68 are the
  owner's.

## 2026-09-03 — Panels wave 0 (`black_bloc/panels.py`) and the deploy gate that fits inside a tool call

Landed together in release **v60** (`46e3ba4`, 11:39; `deploys.log` line 59). Three things,
two of them 🔧 items moved here whole below.

**Wave 0 of the panels program** (`info/panels-program.md` §4): `black_bloc/panels.py` extracted
from the requests cog so the three fourth-pass review defects (a replaced view never stopped;
`on_timeout` editing through a stale token; staff not re-checked before a move) live in ONE
place before seventeen panels inherit them. `Panel(AnswersErrors, discord.ui.View)` with
`interaction_check`, `on_timeout` guarded by `self.replaced`, the `went_quiet` footer;
`NoteModal` storing its callback as `takes_note` (NOT `on_submit`, which would shadow
`Modal.on_submit`); `answer`, `still_staff`, `retire`, `db_ready`, `capped_placeholder`,
`panel_minutes(store, guild_id, key)`. The requests cog re-based on it — `RequestView(Panel)`,
`NoteModal(PanelNoteModal)` — behaviour identical, 163 requests tests unchanged, 26 new in
`tests/test_panels.py`. Built by Opus on `feat/panels-library` in a worktree (160k / 20 min),
Fable-reviewed (no defect; five deviations from the brief all accepted), merged `1861923`
~11:50. `code-notes.md` third- and fourth-pass sections re-keyed by ANCHOR at the merge, seven
rows now pointing into `panels.py` with "was … until wave 0" notes.

- 🆕 **"Let's fix that" (owner, 2026-09-03 ~11:25) — `scripts/deploy.ps1` outruns the
  10-minute tool ceiling.** Measured the same morning: pytest alone took **8:27** for 3345
  tests (single process on a 32-core machine), so the wrapper was killed during the image
  build and the orphaned `flyctl deploy` hung at "Waiting for depot builder" with a dead
  stdout pipe; no release was made. Fix in two halves: (1) **`pytest-xdist`** in the dev
  extras and `-n auto` in `deploy.ps1` — the tests are SQLite-per-`tmp_path`, so they should
  parallelise; measure the wall time and that the count is still 3345; (2) a
  `docs/access/deploy.md` gotcha titled for the symptom ("the deploy printed nothing after
  Waiting for depot builder") saying to run the script detached (`Start-Process … -PassThru`)
  and watch the pid, never inside a tool call with a ceiling. Status: **BUILT, awaiting the
  deploy that proves it** (2026-09-03 ~11:55) — (2) landed in `06ace58`'s neighbour that
  morning; (1) measured: `-n auto` on the 32-logical-core machine runs **3371 tests in 54 s**
  (was 8:27 for 3345), count holds; `pytest-xdist>=3.6` in the dev extras, `-n auto` in
  `deploy.ps1`. Moves to DONE when a deploy has run through the new gate.
  **→ PROVED 11:39: the v60 deploy ran the whole script in 2:50 wall (pytest 1:22 inside the
  gate beside the image build), still launched detached per the gotcha.**

- 🆕 **A defect this build found and fixed on the way, worth knowing about
  separately: `site/public/assets/labels.js` had not parsed since `7b1c592`**, so
  `LABELS` never loaded and **every dashboard page rendered blank**. The Phase 19 merge
  pasted the applications labels after the `LABELS` object's closing brace. Fixed on
  `feat/requests-third-pass` as its own commit (`1d7d84d`), shipped in the third-pass
  deploy 2026-09-03. ⚠️ **Nothing in the test suite reads `labels.js`.** Measured
  2026-09-03 06:40: `node --check site/public/assets/labels.js` **PASSES the broken
  file** — a `.js` path is parsed as CommonJS, where the stray `key: 'value'` lines are
  legal labels; the browser loads it as an ES module and dies at `labels.js:160
  SyntaxError: Unexpected token ':'`. The guard that catches it is the module parse:
  copy to `.mjs` and `node --check` that, or `node --input-type=module --check <
  labels.js`. Add it to `deploy.ps1` beside ruff, pytest and `check.mjs` — for EVERY
  `site/public/assets/*.js` (they are all modules). Small, own commit; not done in the
  build because it is a deploy-pipeline change and the build had no brief for one.
  **BUILT 2026-09-03 ~11:50**: `deploy.ps1` now runs `node --input-type=module --check <
  file` over every asset after pytest; proved on a scratch file with the Phase 19 shape
  (module parse exit 1, plain `--check` exit 0) and clean on all 29 current assets. Moves
  to DONE with the "Let's fix that" item once a deploy has run through the gate.
  **→ the v60 gate ran it over all 29 assets, green.** Gotcha for the next person: piping
  `node --check` into `findstr` masks the exit code (shows 0) — redirect to `>nul 2>&1`
  when proving a guard by hand.

## 2026-09-03 — Requests, fifth pass: the panel's own list is staff-only; the done card stops posting

Two owner orders minutes after the fourth pass deployed (`ba5cb99`, 10:04), both moved here
whole (the items are reproduced below). **Both were already settings or became one**, so
each goes back the other way from the Settings page or `/settings set-value` (checklist 33).

**1. "We need to make the view request thing staff only" (~10:10).** One clarifying
question; the owner picked "Viewing requests on the panel". Members keep `File a request`
and `Take one back…` (the withdraw select is still built from their own rows), but the
embed no longer lists their own requests unless the new **`request_panel_own_list`**
(bool, default **off**) is on; staff see their own list whatever the key says. Opus built
it on `feat/requests-panel-own-list` (`dd7c788` code, `bda45da` docs) — gate at
`cogs/community/requests.py:511` `if staff or panel_shows_own_list(store, guild.id):`,
helper `requests.py:477`, registry `settings_store.py:877/898/1307`; no wording was added
for the hidden list (the intro still reads honestly; deviation 12 in
`info/requests-panel-design.md` says why). Three existing tests asserted the overturned
behaviour and were rewritten to turn the key on. The build also corrected sweep rows 14–15
(not 58–64 as the brief guessed), added row 65, and fixed two stale doc lines it was already
editing (OWNER_GUIDE's "42 rows", feature-list F18 "not yet merged"). Merge **`c4420cc`**.
Cost: 152k Opus tokens, 18 minutes.

**2. "Let's suppress the request.done box in discord, it's redundant information. This
should be in website logs only" (~10:17).** Located in a few greps: the done card was
already gated by `request_channel_moves` (`requests.py:521` `posts_a_card`, third pass) and
the live DB held **no** stored `request_*` row (measured over `flyctl ssh`), so the whole
fix is the DEFAULT: `REQUEST_CARD_DEFAULT` = every move but `done` (`settings_store.py:870`,
`:1302`); the choices still list all seven so `done` can be ticked back on — a single edited
tuple would have made the Settings checkbox and `/settings set-value` REFUSE it. The
requester's DM on done is untouched (it goes to the asker, not the channel). Done on `main`
after the merge by the conductor (a default flip, not a build), shipped in the same deploy.
Deviation 15 in `info/requests-embeds-design.md`; sweep row 62 amended.

**Proof:** ruff clean; 3345 tests on the branch, the full suite re-run by `deploy.ps1`
(`deploys.log` has the count); `check.mjs` 17 pages / 139 routes, site untouched.
⚠️ **NOT verified by eye in Discord** — no panel opened, no Accept pressed. The owner's sweep
is rows 14–15 (member sees no list), 62 (Accept posts no channel card), 65 (the key puts
the list back).

**The TODO items, whole:**

- 🆕 **"We need to make the view request thing staff only" (owner, 2026-09-03 ~10:10, minutes
  after the panel deploy `ba5cb99`).** Clarified ~10:12 — the owner picked "Viewing requests
  on the panel": members keep `File a request` and `Take one back…`, but the list of their
  own requests in the panel embed becomes staff-only (staff see everything as now). The
  site's request reads were already staff-only (`api/writes.py:126` `reader_dependency`
  wraps `staff_dependency`; only `/mine` is a member route). Per checklist 33 the gate is a
  setting, **`request_panel_own_list`** (bool, default **off**), so the Settings page and
  `/settings set-value` can put the list back. Build: Opus, branch
  `feat/requests-panel-own-list`, worktree `.claude/worktrees/agent-own-list`; the brief
  also asks for design-doc deviation 12, code-notes rows, OWNER_GUIDE / feature-list /
  sweeps corrections. Status: **BUILDING** (dispatched 10:15) → landed, see below.

- 🆕 **"Let's suppress the request.done box in discord, it's redundant information. This
  should be in website logs only" (owner, 2026-09-03 ~10:17).** The done card the bot posts
  to Discord when a request is accepted duplicates the website log row. Locating the poster
  and confirming which message is meant; configurable both ways (checklist 33) — a setting
  that defaults to off, so the card can come back. Status: **LOCATING** → located and landed, see below.

## 2026-09-03 — Requests, fourth pass: `/request` is ONE command that opens a panel

Moved whole from `TODO.md` (the item is reproduced below the summary). Owner's ask ~06:50
("The flow seems tough, and request set and request ready seem overlapping"), then the
standing direction ~06:55 ("minimize slash commands and maximize interactive windows …
Request first") — now a `CLAUDE.md` rule and the pattern for every later feature. Design:
[`info/requests-panel-design.md`](info/requests-panel-design.md) (11 deviations — 9–11 are
the reviewer's findings). **Sonnet 5 built it** on `feat/requests-panel` (`7b4d120`,
`4743b01`, `39dfe17`) after Opus returned 529 Overloaded four times (07:44–08:35, nothing
written each time); Fable reviewed; **Opus fixed the three findings** (`79548c1`,
`7aaf24a`); merge **`ba5cb99`**, deployed the same commit — see `deploys.log`.

**What shipped.** `/request` is a single command, no subcommands: one ephemeral message,
an embed plus a `discord.ui.View`. Members see their own requests, `File a request` (the
existing modal — hidden, with a line saying why, when filing is staff-only or requests are
off), `Refresh`, `Open on the site`, and a "Take one back…" select with a Yes/Keep confirm.
Staff additionally see a counts line, a "Pick a request…" select over the open statuses
(capped at 25, placeholder "25 of N — the rest are on the site"), and `Logs`. Picking a
request renders the card — the SAME `request_embed` the channel and DMs get — with ONLY
the moves valid from its state as buttons (open: Pick up / Hold / Decline; in progress:
Ready to check / Hold / Decline; ready to check: Accept (only when `may_accept`) / Send
back / Hold / Decline; on hold: Resume / Decline; final states: none, the footer says so)
plus `Back`. Every move calls the shared function that already existed (`apply_decision`,
`mark_ready`, `accept`, `send_back`, `resume_request`), `via` at its Discord default —
the panel never writes a row or a log line itself. `withdraw_request` was extracted so the
panel's confirm and the site's withdraw route are one implementation with one log row
(`kind_via`). New setting `request_panel_minutes` (int, default **10**). `commands synced`
stays **44** — a `Group` was already one top-level slot (deviation 7 corrected the design's
"drops by nine"). 3338 tests, ruff clean, `check.mjs` 17 pages / 139 routes.

**Review findings, all fixed before merge (verified against the installed discord.py, not
reasoned).** F1: `ViewStore.add_view` (`ui/view.py:940–968`) overwrites the message's view
without stopping the old one, so a replaced panel's timeout would later overwrite the live
card with a disabled stale one — now `retire()` stops the previous view before every
replacing edit. F2: the "gone quiet" footer could not be written at the old default of 15
minutes (an `InteractionMessage` token dies at 15, and non-rendering clicks refresh the
timeout without refreshing the token) — buttons would have died silently; now `on_timeout`
edits through the freshest interaction's token, the default is 10, and the help text says
15+ loses the footer (KI-20 names it). F3: the ten subcommands called `require_staff` on
every call, the panel only at render — `still_staff` now re-asks before every move and
modal submit. The build's deviation 2 ("only the last view reaches on_timeout") was wrong
and is marked superseded. The reviewer's own suggested guard (`is_finished()` in
`on_timeout`) was also wrong — `_dispatch_timeout` marks the view finished BEFORE calling
`on_timeout` — the fix agent measured it and used an explicit `replaced` flag instead.

⚠️ **NOT verified:** anything by eye in Discord — no panel has been opened live. The
owner's sweep is `access/sweeps.md` rows 58–64: `/request` in `#mute-me-bot-test-spam`,
pick #1, Accept — that posts the first done card.

**The TODO item, whole:**

- 🆕 **Simplify the request slash flow — owner, 2026-09-03 ~06:50, verbatim: "The flow
  seems tough, and request set and request ready seem overlapping."** Measured: after the
  third pass `/request` has TEN subcommands and two ways to make most moves —
  `set status:review` vs `ready`, `set status:done` vs `accept`, `set status:hold` vs
  `hold`, `set status:in_progress` (from review) vs `sendback` (`cogs/community/requests.py:631–778`,
  `STAFF_STATUSES` is every reachable status). Proposal put to the owner: ONE mover,
  `/request set`, with `review` opening the built/how-to-test modal, `done` from review =
  accept, `in_progress` from review requiring the note (= send back); delete `ready`,
  `accept`, `sendback`, `hold`, `resume`. Site buttons unchanged. **Owner ~06:55, going
  further:** *"Let's also have /request open a menu maybe. Let's try and minimize slash
  commands and maximize interactive windows"* → *"Let's start this process with request
  then carry it through the rest of the app. Request first."* Decided: `/request` becomes
  ONE command that opens an ephemeral panel (embed + buttons + selects + modals); the nine
  subcommands go. Design → [`info/requests-panel-design.md`](info/requests-panel-design.md);
  rule added to `CLAUDE.md`. Status: **BUILDING** (Opus, `feat/requests-panel`, cut from
  `3e18e4a`), 2026-09-03 ~07:05.

## 2026-09-03 — Requests, third pass: the review state, the embeds and the site link

Moved whole from `TODO.md` (the item is reproduced below the summary). Owner's ask
~00:50, two decisions ~01:00 (the `review` state; "Yes, build it that way"), the data
order ~03:55 ("Move the 2 done ones to ready to check, leave the other as hold"). Opus
build on `feat/requests-third-pass` (12 commits, `2fac43b` … `c6064f9`), merge
**`355d6e9`**, conductor's post-merge anchor fix **`70a6720`**, deployed **`70a6720`**
2026-09-03 06:34 — see `deploys.log`. Design and its 14 deviations:
[`info/requests-embeds-design.md`](info/requests-embeds-design.md).

**What shipped.** The state machine grows `review` ("ready to check"):
`open → in_progress → review → done`, `done` reachable ONLY from `review`, `built`
required to enter it, Accept moves it to `done`, Send back (note required) returns it to
`in_progress` — a LOOK, not a state, remembered in `sent_back_reason`. `hold` / `declined`
stay side states. Every request notification is ONE embed builder (`request_embed`, seven
looks) used by the channel line and the requester DM, with a link button to
`{origin}/requests.html#r-N`. Schema 26: `requests.built` / `how_to_test` / `ready_by` /
`sent_back_reason`, nullable, no backfill. Settings: `request_channel_moves` (a new
`enums` registry type — which moves post to the channel) and `request_review_by_other`
(default off — the accepter need not differ from the person who marked it ready).
Routes `POST /api/requests/{id}/ready|accept|sendback`, slash `/request
ready|accept|sendback`, log kinds `request.review` / `request.sent_back` (IMPORTANT),
one row per web write through `kind_via` (checklist 34). Requests page: a Ready-to-check
section with editors for built / how-to-test, per-card `#r-N` anchors that open the
section they land in. 3310 tests, ruff clean, `check.mjs` 17 pages / 139 routes.

**Found on the way.** `site/public/assets/labels.js` had not parsed since the Phase 19
merge `7b1c592` — every dashboard page rendered BLANK from 00:31 to 06:34. Fixed in
`1d7d84d`; the guard that would have caught it is an open TODO item (the module parse,
not `node --check`). And the design's own link, `/requests#r-N`, 404s on the static
mount — deviation 14, `REQUEST_ANCHOR` now takes the page from `logkinds.FEATURE_PAGES`.

**Landing data step, run 06:41 against the live volume:** #1 and #2 `done → review`
(`ready_by` = the staffer who had marked them done, `done_at` null, `built` = the old
decision note, `how_to_test` = the sweep rows 48–52 / 53–57); #3 untouched, `hold`.
Verified on https://blackbloc.heygabi.ai/requests.html: Ready to check 2, On hold 1,
Done 0, no console errors. ⚠️ **NOT verified:** any card by eye in Discord — the one-off
posts nothing; the first real staff move (an Accept on #1, say) posts the first card to
`#mute-me-bot-test-spam`. The slash paths and the DM look are on the sweep list.

**The TODO item, whole:**

- 🆕 **Request notifications as embeds, with "what was built" + "how to test" + a site
  link — owner, 2026-09-03 ~00:50, verbatim: "We probably should also add how to test the
  feature and a short explanation of what was built too. Also let's get a standard
  appealing template for the output. Maybe use one of the discord info boxes with a
  description, how to test if applicable, and a link to the request on the website. When
  someone makes a request we should also post that same request link in discord too. So a
  message at the start to confirm task is made and then once at the end when done. Also
  one for the in hold or declined states."** Today every request line is plain text
  (`black_bloc/requests.py:149–159` `NOTIFY_*`, `:132–147` `DM_*`) and no per-request URL
  exists (`page-requests.js` renders cards with no anchor). Design →
  [`info/requests-embeds-design.md`](info/requests-embeds-design.md). Touches the same
  files as the double-logging fix, which merged as `df393ab` (`DONE.md` 2026-09-03) —
  the build cuts from that or later and follows checklist item 34 (pass `via`, never
  a second `note()`). Owner decisions 2026-09-03 ~01:00: asked whether "what was built" is required
  on Done, he answered *"Do we need an acceptance pending so a staffer can check if
  something is done?"* → a **`review` ("ready to check") state**, `in_progress → review →
  done`, built + how-to-test required to enter review, Accept / Send back,
  `request_review_by_other` default off ("Yes, build it that way"). Owner ~03:55:
  *"Move the 2 done ones to ready to check, leave the other as hold"* → not possible
  until `review` exists (`done` is final today); recorded as the build's LANDING DATA
  STEP in the design (#1 and #2 `done → review` by a one-off on the live DB, #3 stays
  `hold`). Status: ⚠️ **BUILT on `feat/requests-third-pass`, 2026-09-03 — NOT merged,
  NOT deployed, and the landing data step NOT run.** 3260 tests pass, ruff clean,
  `check.mjs` 17 pages / 139 routes, and the page was rendered against the mock; nothing
  has been verified against live Discord or the live dashboard. What is left for the
  conductor, in order: **(1)** merge and deploy (schema 26 migrates on boot — four
  nullable columns, no backfill); **(2)** run the landing one-off in the design doc's
  `## Deviations` foot (#1 and #2 `done → review`, #3 untouched) — it is idempotent and
  was dry-run against a throwaway schema-26 file, but it must run AFTER the deploy;
  **(3)** post one card of each of the seven looks to `#mute-me-bot-test-spam` and judge
  "appealing" by eye — §J measured the shapes (worst look 2004 of Discord's 6000) but
  nobody has seen one rendered. Move this item WHOLE to `DONE.md` at landing.

## 2026-09-03 — One web write leaves one log row (owner bug report, the same night as the 17/18/19 landing)

Moved whole from `TODO.md`. Owner ~00:40, on seeing the three request flips in the
test channel: *"The app double posted all messages with a web.request and a request"*.
Root-caused in the main loop (AST survey, 8 route files), owner chose "All 8
features" over requests-only at ~00:43, Opus build in a worktree, merge **`df393ab`**
(branch `fix/web-write-double-log`: `5f7cc1e` code, `19d2f7d` docs), deployed the
same morning — see `deploys.log`.

**What was wrong.** A dashboard write went through a shared bot function that
already logged the event, and the route then `note()`d a `web.<kind>` line on top
of it. One click left TWO `action_log` rows and posted TWO embeds. `logkinds.bare()`
collapsed the pair for *classification*, so nothing ever noticed; it surfaced now
because `request.done/hold/declined` are IMPORTANT and post at the default level,
and tonight was the first real traffic through the site. Present in 8 route files —
requests, events, honeypot, mod, modmail, polls, rolemenus, tempvoice — across 20
shared functions; it pre-dated Phase 17 (`f7199a5` already had it).

**The fix.** One canonical `logkinds.kind_via(kind, via)` (`bare()` read backwards)
replaced SIX hand-built `f"{WEB}."` heads (`pings.head` deleted; `rolemenu_panels`,
`applications` ×2, `role_menus`, `tempvoice.panel_log`). Every shared function a
route calls takes keyword-only `via: str = VIA_DISCORD`, logs one row through
`kind_via`, and records `details["via"]`. Each route passes `via=VIA_WEBSITE` and
its redundant `note()` is gone. Slash commands take the default and are unaffected.
`note()` survives only where the route is the sole logger (`web.request.filed` /
`updated`, comments, withdraw, raid-train and role-menu CRUD); bot-emitted
consequences (`request.dm_failed`, `modmail.place_kept`) keep their bare kinds.
**Three survey hits were false positives and kept deliberately:** `rename_channel`
and `send_reply` log only failures, so `web.event.edited` and `web.modmail.reply`
are the route's own lines; `staff_assign` already took `via`.

**Consequences.** Where the shared kind differed from the note kind the web row now
carries the shared one (`web.event.cancelled`, `web.honeypot.banned`,
`web.mod.warned/timed_out/…`, `web.automod.rule`, `web.poll.closed`, …). Eight
now-unemitted `ROUTINE` entries were removed — the repo's own
`test_no_classification_entry_is_dead` required it; historical rows keep their
kinds and `honeypot.ban` old rows now read *important* — **KI-19**. Two rows move
page: automod rule changes and Apply-now now land on the Automod log, matching what
the Discord button already produced.

**Guarded so it cannot come back:** checklist item **34**, plus an AST walk in
`tests/test_logkinds.py` (`test_a_route_never_notes_an_event_its_shared_path_already_logged`)
that fails if a route both calls a shared logger and notes the same bare kind —
proven by re-introducing the defect, which failed by name — a "no second
head-builder" test, and a `via`-default test. `tests/api/conftest.py:one_web_row`
asserts exactly one `web.*` row per route write; the old tests asserted both kinds
were *present*, which is precisely what a double post looks like.

**Measured:** 3244 tests (was 3238), `ruff` clean, mock 17 pages / 136 routes; the
mock and `contract.json` emitted the old kind strings and were updated in the same
commit (`check.mjs` only tests emitted ⊆ listed, so a stale mock passes silently).
**NOT verified** by the build: anything against live Discord or the live dashboard.
**Still open:** `raidtrain.cancel_train` logs one row but labels a web cancel
Via = Discord — a Via-labelling gap, not a double post (on `TODO.md`).

The item as it stood on `TODO.md`:

- 🔴 **Every web write through a shared path logs TWICE — owner, 2026-09-03 ~00:40,
  verbatim: "The app double posted all messages with a web.request and a request".**
  Seen on the three request flips at the 17/18/19 landing: each produced a
  `request.done` embed (from `apply_decision`, `cogs/community/requests.py:220`) AND a
  `web.request.done` embed (from the route's own `note()`, `api/tools/requests.py:273`).
  `logkinds.bare()` already calls the two "the same event, logged from two places"
  but only for classification — nothing dedups the post or the row. Surveyed
  2026-09-03 (scratchpad `survey_double_log.py`, AST walk): the same shape is in
  **8 route files** — events (`apply_decision`/`cancel_event`/`rename_channel`),
  honeypot, mod (`_punish` ×6, case apply, rule), modmail (reply/close), polls
  (create/decide/end/cancel), requests (decide/resume/status), rolemenus
  (`staff_assign`), tempvoice — plus roles per the `bare()` docstring. Pre-dates
  Phase 17 (`f7199a5` already had it); it surfaced now because `request.done/hold/
  declined` are IMPORTANT and post at the default level. Fix = the convention the
  newer code already uses (`pings.py:head(via)`, `rolemenu_panels.note(via=)`,
  applications): the shared path takes `via`, logs ONE row with the `web.` head
  when `via == VIA_WEBSITE`, and the route drops its second `note()`. Status:
  **waiting on the owner's go-ahead for the 8-file sweep** (recommended) vs
  requests-only.

## 2026-09-03 — Phases 17/18/19: chat memory + requests state machine, raid trains, applications — NEXT WAVE items 3, 6, 7

Moved whole from `TODO.md`. The three phases were **built in parallel** by three Opus
worktree builders (owner 2026-09-02 22:25: "Can we start doing some of this in parallel?")
under §K of each design — shared files append-only, pre-assigned schema numbers 23/24/25,
merge order 17 → 18 → 19, the reviewer resolves. Phase 17 (`info/phase17-design.md` +
`info/requests-states-design.md`, branch tip `44f4a9b`) merged `6d61994`; Phase 18
(`info/phase18-design.md`, tip `8999d6e`) merged `0bb3835`; Phase 19
(`info/phase19-design.md`, tip `dcba425`, ~575k tokens) merged `7b1c592`. Conflicts were
all additive (the `SCHEMA` foot, `SCHEMA_VERSION`, registry defaults, log kinds, COGS,
the mock contract — `contract.json` had to be merged structurally because keep-both
produced invalid JSON; `tests/storage/test_db.py`'s two schema-22 upgrade tests were
rebuilt verbatim from both branches after the textual merge interleaved them). Merged tree:
**3238 tests**, ruff clean, 17 pages / 136 routes, 19 cogs, 44 commands, 17 features,
schema **25**. **Deployed `7b1c592` 2026-09-03 00:31 Phoenix** via `scripts/deploy.ps1`.
Verified live: boot log at 07:31:27Z shows **19 cogs** loaded incl. `content.chat_memory`, `content.raidtrain`, `community.applications`; **44 app commands synced**; `/memory` and `/apply` hidden by command visibility (both modes off); logged in; birthdays import ran; no error or traceback line. NOT verified: the schema number on the live volume (the boot log does not print it), any dashboard section in a browser.
All three modes ship **off** (`chat_memory_mode`, `raidtrain_mode`, `applications_mode`).
Findings worth keeping: Phase 17's §J measured 29/29 distillations parseable on
`openai/gpt-oss-120b` (median 0.77 s) and moved `/memory` out of the staff-only `/chat`
group (deviation 1 of 6); Phase 18's §J found Phase 4's calendar helper NOT reusable — it
writes to the `events` table — so `raidtrain_scheduled_event` ships `false` with a
creator of its own (D13); Phase 19 found `change_roles` is module-level and remembers its
own edits, so the reconciler never reports an approval as by-hand and `role_menus.py` was
never touched (9 deviations at the foot of its design). Requests ride-along: the owner's
state machine landed as data (`TRANSITIONS`), `hold` remembers `held_from` and resume
returns there (a request held from `open` resumes into `in_progress`, because resuming IS
starting work — noted in the design's Deviations), `pending`/`approved`/`planned` migrated
to `open`, `request_auto_approve_staff` retired (owner: "Even a staff request can be bad"),
requester DM + `request_status_channel_id` line on every staff move. At landing: request
#1 and #2 → `done` (DM to Pawpette), #3 → `hold` with the owner's note. Residuals
KI-14 … KI-18. Owner's sweep rows 48–57 open. ⚠️ NOT verified: any of the three features
against live Discord — no profile distilled, no train posted, no form filled. Also this
session: `DONE.md` had been double-encoded whole by the Phase 16 landing commit `31b1689`
(333 mojibake sequences) — repaired by rebuilding it from `0229da0` plus the Phase 16 entry,
proven lossless (27 additions, 0 removals against `0229da0`).

- NEXT WAVE item 3, verbatim:
3. **Chat long-term memory** — GABI-style distilled member profiles (her design:
   cheap-model distillation when a conversation goes quiet, ≤2KB per person,
   injected as a memory block; see `catalog-platform` gabi-memory-design.md).
   Privacy decisions needed from the owner BEFORE building (what is remembered,
   member opt-out, retention). **DRAFT DESIGN 2026-09-02 17:10 →
   [`info/phase17-design.md`](info/phase17-design.md)**: tier 1 already
   exists (`chat_window`); adds schema 23 profiles distilled on the hourly
   sweep, `/chat memory`, a Memory section on the Chat page. ✅ **ALL FIVE
   DECIDED 2026-09-02 17:20–18:38, one at a time** (D1 opt-out · D2
   preferences with a written definition · D3 180 d, no raw archive · D4
   separate DM/server scopes · D5 counts only) — **BUILDABLE**; builder
   dispatches after Phase 16 (schema 23 follows 22).
- NEXT WAVE items 6 and 7 (with the requests ride-along), verbatim:
6. **Raid trains (member request #1, Pawpette)** — owner 2026-09-02 20:10:
   "build, also start wave 6" then "i want memory starting first". So: Phase 17
   memory dispatches first (schema 23), raid trains = **Phase 18, schema 24**.
   **DESIGNED 2026-09-02 22:30 → [`info/phase18-design.md`](info/phase18-design.md)**
   (from [`info/raid-train-capture.md`](info/raid-train-capture.md): ASKED +
   FIT buckets; LATER stays later; 15 decisions as 13 `raidtrain_*` keys).
   **Owner 2026-09-02 22:25: "Can we start doing some of this in parallel?"
   → Phase 18 builds BESIDE Phase 17** (Phases 5/6/7 precedent: shared files
   append-only, §K of the design; merge order 17 → 18, reviewer resolves).
   Request #1 set to `in_progress`, priority 2, with the decision note, on the
   Requests page; flips to `done` at landing (DM to Pawpette).
7. **Twitch Team application form (member request #2, Pawpette)** — owner
   2026-09-02 20:14: "build next" → **Phase 19**. **DESIGNED 2026-09-02 22:40
   → [`info/phase19-design.md`](info/phase19-design.md)** as general
   *applications* (staff-defined forms, ≤5 questions, grant a role on
   approve; the Team form is the first one the owner creates — nothing
   Team-specific hard-coded); schema 25; the twitch.tv invite stays a named
   team-owner click (`owner_user_id` + `next_step` per form). Builds **in
   parallel** with 17/18 (§K; merge order 17 → 18 → 19). Request #2 set to
   `in_progress`; flips to `done` at landing (DM to Pawpette).
   ✅ **BUILT 2026-09-02 23:27** on branch `worktree-agent-aecc5822942fd3a56`
   (8 commits `f0fa493`…`dcba425`, builder ~575k tokens; 2989 green at
   `3ff5bb2`, +2 single-test commits after; check.mjs 17 pages / 126 routes;
   9 deviations listed at the foot of the design). **Reviewed by Fable 23:35:
   mergeable** — waits its turn behind 17 and 18. Merge conflicts expected
   only on `SCHEMA_VERSION` + the foot of `SCHEMA` in `storage/db.py`.
   **Ride-along (owner 2026-09-02 20:19: "when a request finishes can we
   message the channel and dm the person who made the request saying its
   done"):** the DM half EXISTS (`DM_DONE`, gated by `request_dms_on_decision`);
   the channel half does not — `notify()` only posts `NOTIFY_LINE` at filing.
   Add a done line ("Request **#N** from @who is done: what", no pings) posted
   to `request_done_channel_id` (new key, blank = falls back to
   `request_notify_channel_id`), a `request_done_template` key, guard-checked,
   `request.done_notify_failed` logged on failure. Registry sync points
   (labels.js, mock server, exact-key-set test).
   **Plus (owner 2026-09-02 20:27, request #3 music bot: "put this one in
   pending/hold … make sure we dm the person and post it chat that we marked
   something as hold and why"):** there is NO hold state — staff moves are
   forward-only (approved/planned/in_progress/done/declined; the API refused
   `pending` in words). **Owner redesigned the state machine 2026-09-02
   20:33 (verbatim): "add a new status for open and then change pending to
   hold. so it goes from open -> planned -> in prog -> done with hold and
   declined as side states. Declined is a final state like done and hold can
   be anywhere in the process. we should also mark what state it was
   previously for my own sake."** Then 20:36: **"lets also get rid of planned
   since we'll hold or decline anything no need for planned."** So:
   - **Main line:** `open` (a request arrives here; replaces `pending`) →
     `in_progress` → `done` (final). Nothing else on the line.
   - **Side states:** `hold` — from `open` or `in_progress`, reason
     REQUIRED, stores **`held_from`** (shown on the page and in the DM;
     "resume" returns it there by default, staff may pick the other);
     `declined` — final, reason required, from `open`, `in_progress` or
     `hold`. `withdrawn` stays (requester's own final state, from `open` or
     `hold`).
   - **`approved` AND `planned` are RETIRED.** Starting work = the
     `open → in_progress` move. `requests_auto_approve` loses its meaning
     (there is no approve step) — Claude's reading: retire the key too;
     every filing, staff or not, arrives `open`. Data migration in schema
     23: `pending → open`, `approved → open`, `planned → open`
     (`in_progress`/`done`/`declined`/`withdrawn` unchanged).
   - **Notifications on EVERY staff move** (in_progress, hold, done,
     declined): requester DM + channel post, reason/note in the text, no
     pings; guard-checked; failures logged. Today only
     approve/decline/done DM and nothing posts to a channel after filing.
   - Touch list: `requests.py` (`STATUSES`, `STATUS_WORDS`, `DM_TEXT`,
     transitions table — encode the machine as data, one place), the cog,
     `api/tools/requests.py`, Requests page (filter, status control, held_from
     badge, resume button), `/request set` choices, mock contract,
     settings registry (drop `requests_auto_approve`;
     `request_status_channel_id` + `request_status_template`), tests.
   **Must ship BEFORE the first request lands (Phase 18) — folded into the
   Phase 17 builder brief** as a bounded add-on. At landing: flip #3 to
   `hold` with the owner's note so PT gets the DM (the channel post stays
   TEST_MODE-blocked until the lift).
   Meanwhile #3 sits `approved` with the note "ON HOLD (owner, 2026-09-02):
   youtube player is currently unreliable. Will do further research on this."
   ⚠️ **Owner rule 2026-09-02 20:14: every accepted request stays
   `in_progress` on the Requests page until it ships; flipping it to `done`
   is part of that phase's landing ritual.**

## 2026-09-02 — Phase 16: YouTube uploads (F3), NEXT WAVE item 2

Moved whole from `TODO.md`. Designed 17:05 (`25a9411`, `info/phase16-design.md`),
built by one Opus worktree builder (~505k tokens, four clean-boundary commits
`79508de` `a743577` `ded574f` `4e36858`; §J measured first — no ETag ever served,
Shorts free from the `/shorts/` link, feed answers ~50% → KI-11/12/13), Fable-reviewed
against the design + checklist, merged `7295f61`, **deployed `049881b` 22:18
Phoenix** via `scripts/deploy.ps1` (2865 tests, ruff clean, 17 pages / 116 routes).
The first deploy run died at `git push` on a PowerShell-5.1 stderr quirk after the
push had landed — fixed in `049881b` (`cmd /c … 2>&1`), gotcha in `access/runbook.md`,
gate rerun in full. Verified live: boot log shows 16 cogs incl. `content.youtube` (feed-only notice — no key), 39 app commands synced, logged in, no error/traceback lines. âš ï¸ NOT verified: any real YouTube
channel (`youtube_mode` ships off; no channel linked; no API key minted), the Go-live
page section in a browser. Residuals accepted at review: no retry backoff on the feed
sweep (KI-12 covers the miss rate); the cog floors the poll interval at 1 min while
the registry says 5.

- NEXT WAVE item 2, verbatim: **F3 — YouTube upload announcements**: go-live via YouTube presence already
   works (sweeps row 4); this adds NEW-UPLOAD posts, which needs the YouTube
   Data API (owner mints an API key — free quota) + a channel-link store like
   `/twitch link` + a poll loop like the Twitch one. **DESIGNED 2026-09-02
   17:05 → [`info/phase16-design.md`](info/phase16-design.md)**: the public
   Atom feed is the primary source (NO key needed); `YOUTUBE_API_KEY` is an
   optional upgrade (handle resolution, live/Shorts classification) — the owner
   may mint one at their pace. Ten defaults taken as settings keys. Builder
   dispatches after Phase 15 lands (schema 22 follows 21).
- Feature-table row, verbatim: | F3 | **YouTube** — *maybe* | Go-live via YouTube presence WORKS (sweeps row 4); uploads = 🚀 NEXT WAVE item 2. | next wave |

## 2026-09-02 — Phase 15: ping roles (F14), NEXT WAVE item 1

Moved whole from `TODO.md`. Designed 16:45 (`d293193`, `info/phase15-design.md`),
built by one Opus worktree builder 16:50–17:35 (509k tokens, four clean-boundary
commits `55990db` `68e422a` `37407bd` `4357c1d`), Fable-reviewed against the design +
checklist, merged `c577b06`, **deployed `d777f57` 17:43 Phoenix** via the gated
`scripts/deploy.ps1` (2714 tests, ruff clean, 17 pages / 111 routes). Verified live:
boot log shows 15 cogs incl. `content.pings`, the Ping roles section (7 keys) on
Settings and the Pings section on the Go-live page both render; `pings_mode` flipped
**on** from the dashboard 17:47 (persisted across reload). ⚠️ NOT verified: any live
Discord role create/assign/delete, the two-role ping prefix on a real announcement —
those are the owner's sweep. Builder's four deviations accepted at review: self-serve
follow/unfollow logged routine (role-menu precedent); no `pings.would_*` kinds (off
means refuse-in-words, nothing to emit); `/pingroles setup` works while the mode is
off (so it can be prepared before the flip); `_fill_menu` clears before re-adding
(`add_option` preserves position). Residual: the old process logged `asyncio:
Unclosed client session` at shutdown during the rolling deploy — pre-existing, not
from this build; watch.

- NEXT WAVE item 1, verbatim: **F14 — ping roles** (the last unbuilt item from the original 2026-08-26 list):
   an opt-in **Events** role pinged on go-live/event announcements, and
   **per-streamer favourite roles** ("people that want to see SuperNamu only …
   can get her pings") wired into announcements + the role menus. Everything it
   needs exists: role menus (incl. approval/staff modes), `golive_ping_role_id`
   / `events_ping_role_id`, the announcement paths. **DESIGNED 2026-09-02 16:45
   → [`info/phase15-design.md`](info/phase15-design.md)**; the seven small
   decisions (who creates a fan role, its name, one Events role for both feeds,
   keep-on-unlink, delete-on-remove, mode off at deploy, three opt-in surfaces)
   were taken with defaults and are ALL settings keys, so the owner flips them
   on the dashboard rather than in chat. **Opus worktree builder dispatched
   2026-09-02 ~16:50.**
- Feature-table row, verbatim: | F14 | **Ping roles** (owner, 2026-08-26): an opt-in **Events** role for go-live/event pings, and **favourite-streamer roles** — per-streamer opt-in pings ("people that want to see SuperNamu only … can get her pings"). Wire into F1/F5 announcements and the role menus. | 🚀 NEXT WAVE item 1 |

## 2026-09-01 — The chat-hardening wave: an afternoon of live findings, one deploy

Moved whole from `TODO.md` (every bullet below was a live finding the owner or a member
made while talking to the newly-enabled LLM chat; all landed in `1ab76f8`, deployed
2026-09-01 19:01 Phoenix — three Opus builds: who-has `cf11cdc` ~212k, guardrails
`ed2710c` ~436k/7 items, four-pack merge ~418k/4 items; **2606 tests**, 17 pages /
107 routes; verified after deploy: /health ok, 35 commands synced, **the re-run ingest
kept all 6 leaked rows out (0 returned) and wrote 36 role-holder notes**):

- **STATUS 2026-09-01 ~17:5x: who-has (`cf11cdc`) and the full guardrails package (`ed2710c`, 2567 tests) are MERGED on main, NOT deployed** — ⚠️ deploy still held until the follow-up four-pack (tier threshold + self-knowledge + Costs card + persona play-tune, **Opus builder dispatched ~17:55**) lands, then ONE deploy ships the whole day. Guardrails highlights at review: the ingest filter is enforced by signature (no path skips it, fails closed), the reply guard fails OPEN (a crash never turns an answer into silence), the no-ping hole did not exist (measured), 24 commands locked below Aunties/Uncles + 11 visible with runtime gates, all four new keys render-proven on both pages.

- **Owner 2026-09-01 ~15:0x, verbatim: "the bot cant currently find roles, I want the bot to know who has what role so it can help escalate. so I can say hey @black_bloc tell me who's a lead or a mentor or something"** → a `who_has` DATA intent (deterministic, live gateway cache, display names never pings, ≤25 listed, staff-role answers end with the escalate pointer) + role-holder sections in the daily knowledge ingest for roles ≤25 humans so the Haiku tier grounds odd phrasings. Status: **Opus builder dispatched ~15:10 in a worktree.** (Same session, earlier: `/chat status` admin-locked behind `chat_status_admin_only` `45176ed`; managed role renamed `role_black_bloc` via the API — both live.)

- **Owner 2026-09-01 ~15:2x: the bot invented `#black-support-hub` in a live reply** ("make sure it references real channels, this was a great call by the bot to do this though"), then ~15:3x: "i think we need to read the desc of every channel and use that to help guide the bot". ⚠️ Also the first confirmed LIVE model conversations. Fix (queued behind the in-flight who-has builder — same files): (1) a **channel directory on EVERY model call** (both tiers): name + trimmed topic from the live gateway cache, ⚠️ PUBLIC channels only (@everyone-visible — never leak staff/private names into member answers), byte-capped, positioned cacheably in the system stack; (2) persona-core rule: point people only at directory channels; name no channel/role/member absent from directory, grounding or the conversation; (3) deterministic post-check backstop — unknown `#channel` tokens swapped for `chat_home_channel_id` (new key, channel, blank default = de-channel the sentence gracefully) and logged (`chat.reply_channel_fixed`, routine) so hallucination frequency is measurable; (4) 🔴 **MEASURED 2026-09-01 ~15:45 — the ingest takes EVERY text channel with a topic** (`knowledge.py:373`, no visibility or category filter): `#black-support-hub` turned out to be REAL but in the `archive` category (the bot recommended a dead channel it faithfully read), and **five incumbent-Modmail ticket channels leaked in with topics carrying member ids** — a privacy leak into LLM grounding. Immediate mitigation done: the 6 rows deleted from the live DB (re-ingest would return them in ~24h; the fix must land first). The fix: ingest AND the per-call directory take only channels @everyone can view, excluding categories whose name contains "archive" and the modmail category, plus a `chat_ignore_categories` key (both doors) for anything else; the who-has intent gets the same scoping. (5) **Owner 2026-09-01 ~16:0x (live exchange: "im looking for a mod can I trust @Pawpette" → the bot claimed not to know and suggested "ping @Admin"): member-trust answers by the CANONICAL staff check** ("can we check by permission levels" → `store.is_staff`, the one rule everything else uses — Lead qualifies): (a) a deterministic member-lookup intent — "is @X a mod / can I trust @X" answers from live roles + is_staff ("Pawpette holds Lead — yes, staff, they can help"); (b) every LLM call is grounded with the roles + staff-status of any members the message mentions; (c) the post-check guard covers invented @role suggestions like channels; (d) "looking for a mod" joins the modmail-route triggers so it never reaches the model at all. (6) **Owner 2026-09-01 ~16:1x, verbatim: "also need to not let it ping roles too often. maybe i'll have it output 2 online people for a role if someone ask. so if i ask for an admin or a lead output Pawpette and PT because they have the roles. dont @ them though, let the user do that part"** → (a) chat replies send with `allowed_mentions` stripped (roles/everyone/users) so the bot can NEVER ping from a conversational answer — transport-layer, not prompt; (b) escalation-shaped asks name up to `chat_escalation_names` (new int key, default **2**, both doors) ONLINE holders of the relevant staff role as plain display names, the user does the @-ing; none online → say so + modmail pointer; full-roster "who has X" keeps the complete no-ping list. (7) **Owner ~16:2x: "let the bot ping roles if an aunties/uncles or higher initiates it"** → the allowed-mentions strip gets a staff exception: when the INITIATOR passes the canonical `is_staff` (Aunties/Uncles is its floor), role mentions go through in the reply; `@everyone`/`@here` never do for anyone; gated by `chat_staff_can_ping_roles` (new bool key, default on, both doors). Owner decision open, no rush: which channel `chat_home_channel_id` should point at. Status: **queued behind the who-has builder.**

- **Owner 2026-09-01 ~16:4x: "the groq web portal says 0 api calls have been made using the key"** → MEASURED on the live ledger: 8 calls, ALL `anthropic/important/ok`, zero Groq attempts, zero errors (~$0.01 total). Root cause: `tier_for`'s "any knowledge hit → IMPORTANT" rule + the search's OR-fallback ≈ everything matches something in 29 server notes, so the simple tier is never chosen. Fix: only a STRONG hit (AND-pass / score threshold) counts toward tier promotion; weak hits still ride as grounding without upgrading the call. Status: **queued behind the in-flight guardrails builder (same files); small enough for a Fable-reviewed direct change when it lands.**

- **Owner 2026-09-01 ~16:5x (live): "i want to host an event, can you show me how to do that" → the bot said "hit up @Admin"** instead of naming its own `/event create` ("meh didnt pull up the event form"). The bot has no knowledge of its own features. Fix (same follow-up build as the tier threshold): (a) deterministic intents for the self-service features — host/create an event → `/event create` + the review flow in one sentence; file a request → `/request`; link Twitch → `/twitch link`; set a birthday; pick roles (the role menus); (b) a compact "what Black Bloc itself can do" block (the /help content, member-visible commands only) in the system stack on every model call — stable, cacheable — so novel phrasings land on its own commands instead of "ask staff". Status: **queued with the tier-threshold fix.**

- **Owner 2026-09-01 ~17:0x: "on the dashboard somewhere can put a cost breakdown for the hosting, apis keys, models, etc. so we can track spend"** → a **Costs card on the Health page** as THE one home for money: measured LLM spend from the ledger (month-to-date + per provider/model, Groq shown at $0.00 on free tier), hosting as a configured `cost_hosting_usd` key (Fly exposes no billing without a token on the machine — same risk class as the parked deploy button; owner fills it from the invoice, both doors), the free-tier items named ($0), and the secret inventory by NAME + set/unset. The Chat page's Spend section repoints its dollar figure here (link) and keeps tier liveness — one number, one home. Status: **queued in the follow-up build (tier threshold + self-knowledge + costs).**

- **Live 2026-09-01 ~16:50 (member PT): "who is the strongest DBZ character" → the bot deflected** ("way outside my wheelhouse… you'd get better arguments in #off-topic… Who's your pick?") and the member called it out ("have the bot at least pick a character"). Persona bug, not knowledge: the cookout core over-weights "I'm just here for the cookout" into topic-dodging. Fix (persona core text, follow-up build): fun/opinion questions get a REAL answer — take a pick, give one playful reason, in voice; never bounce the question back as the whole reply; channel redirects become an aside, not the answer; deflection reserved for things it should not do. (Noted: it named real channels this time — the pattern held even before the directory ships.) Status: **queued in the follow-up build.**

**The finding that explained everything:** the four-pack builder measured that the
bot's own `<@mention>` token entered the knowledge search, so the strict AND-pass
could never match a real @-mention and EVERY live call fell to the loose OR pass →
`any hit → IMPORTANT` was unconditional → 9/9 calls billed Haiku, Groq never chosen.
Fixed by stripping the mention before search + a strong-hit rule (AND-pass + title-
weight score + whole-word terms). Also in the wave: /chat status admin-locked
(`45176ed`), the managed role renamed `role_black_bloc`, and the live purge of the 6
leaked knowledge rows ahead of the fix. **NOT verified: no real model has read the
new persona rules or FEATURES block** — the owner's retest is the measurement.

## 2026-09-01 — Phase 14: the bot can really talk (three tiers, knowledge, personas — shipped dormant)

Moved whole from `TODO.md`:

- **Owner 2026-09-01 ~11:00, verbatim: "lets do the parked items"** → F10 chat step 3 un-parked. Four decisions taken one at a time (§0 of the design): three tiers ("can we do a mix of 1 and 3 to help save token cost?" → intents free / "groq/llama for simple things and then Haiku for more important things" / "We'll do a context ingestion like we did for Gabi"), cap "$20/month", personality "start with 1 [Cookout] but port over all the other personalities too. we can start building a global personality pool". GABI survey (Opus explore, catalog-platform) fed the design: lexical-not-vector knowledge, deterministic routing before any model call, independent fuses, worded refusals, affirmative-only gates. Design = `info/phase14-design.md`. Status: **14a (core+bot) and 14b (dashboard) Opus builders dispatched ~11:30 in parallel worktrees; ships with `chat_llm_mode off`.**

**Landed as merge `a49e77d`, deployed 13:21 Phoenix** (`deploys.log`; verified: `/health`
ok, chat cog loaded, 35 commands, logged in 20:21:23Z). Three Opus builds: **14a**
(~473k, 8 commits): schema **20** (knowledge_sections/personality_tropes/chat_window/
llm_ledger), `llm.py` (anthropic SDK, Haiku 4.5, 400 max_tokens, prices pinned) +
`groq.py` (aiohttp, `chat_simple_model` default llama-3.3-70b-versatile), `tier_for`
(one pure function: knowledge hit / long question / live conversation / staff topic →
IMPORTANT; important never falls back to the cheap model), knowledge store + lexical
port + daily server ingest + `/chat knowledge`, personas (core + cookout + 11 GABI
tropes as data with provenance; drift derived not stored), fuses (20/person/hr,
200/day, $-cap vs ledger; cap 0 = zero calls by pinned test), 6 registry keys, wired
behind affirmative-only `chat_llm_mode`. **14b** (~383k, 3 commits): 9 staff-gated
`/api/chat` routes (tier liveness measured mode→key→cap, refusals in sentences),
the Chat page's Knowledge/Personality/Spend sections, contract to **17 pages / 106
routes**. **Integration** (~227k, 4 commits): 14b's stand-in store deleted and routes
repointed at 14a's canonical modules; `UNIQUE(guild_id, source, title)` index added
(ingest writes INSERT OR IGNORE against duplicate channel names); persona mode
collapsed onto the `chat_personality` registry key (website switch-off now busts the
trope cache — a real bug the stand-in hid); one base kind per decision (`web.` head
tells the doors apart); mock registers all 13 chat keys with enum choices derived
from the pool; two auto-merge defects fixed (duplicated ROUTINE entries, split kind
names). `cozy` vs `cosy`: checked against GABI's `personality.ts` — canonical key and
label are `cozy`; 14a was right. **2451 tests** (+186 net), ruff clean, check.mjs
17/106. **NOT verified: no real model call has EVER been made by this code** — both
keys are unset everywhere; the first `/chat status` after the owner's switch-on is
the first real cost figure. Owner go-live steps on TODO; sweeps rows 33–35.
Peer README rewrite + deploy-button decisions landed the same morning (see TODO
session log): README `91b3ab7`, deploy button stays parked.

## 2026-09-01 — Go-live hardening, requester-in-channel, the settings audit, nightly backups

Moved whole from `TODO.md`:

- **F4 follow-ups (owner, 2026-08-26):** (a) add the requesting user to their
  own event channel so they can post updates / answer mod questions — or show
  them a ticket page on the F12 site; (b) the approver-roles / event-category /
  create-scheduled-event toggle all become F12 site settings.
- **F5 follow-ups (owner, 2026-08-26):** announce channel + ping role editable
  in the options menu now and on the F12 site later.
- **Go-live follow-ups from the review fixer (2026-08-26):** (a) `live_role_added`
  is a 0/1 flag — store the role *id* so a mid-stream change of
  `golive_live_role_id` cannot strand the old role; (b) session age-out only ticks
  when Twitch creds exist (the poller) — add a creds-independent tick; (c) a failed
  Helix live-check leaves a session open (age-out is the backstop). None block shadow.

**Landed as merge `5f22c20`, deployed 2026-09-01 09:16 Phoenix** (Opus ~242k, four
commits; 2265 tests, ruff, 17/98 green; migration `added golive_sessions.live_role_id`
seen in the Fly logs). (a) schema **19**: the session stores the role id that was
actually added; removal reads it first, legacy rows fall back to the setting.
(b) was a REAL gap with a different root than written: the sweep body already ran
pre-Helix-check, but `cog_load` only STARTED the poller when creds existed — now it
starts unconditionally and `/golive status` says "the sweep still runs and still ages
sessions out" on a credential-less deploy. (c) `golive.poll_degraded` (routine) after
exactly 3 consecutive TwitchErrors — one line per outage naming failures + open
sessions; nothing is closed on a failed check. (F4a) requesters get an explicit
view/send/history overwrite on their own review channel, surviving renames (verified
by reading `rename_channel`, tested through a `done-` rename); access deliberately
stays after decision. (F4b/F5) **audit result: all five toggles already existed** as
registry keys reachable both ways (`staff_channel_id`, `events_category_id`,
`events_create_scheduled`, `events_announce_channel_id`, `events_ping_role_id`) —
nothing was missing; one nuance: the category is set on Discord via `/event settings
category:` because generic `/settings set` takes text channels only. **Same deploy:**
`black_bloc/dbsnapshot.py` shipped and the **nightly backup went end-to-end**
(scheduled task "BlackBloc DB backup", daily 04:00; test pull 311,296 bytes, "ok" in
`backup.log`) — RECOVERY's backup gap CLOSED with the machine-state residual recorded.
**NOT verified live:** no real role add/remove, no real credential-less deploy, no
real Twitch outage, no requester has posted in a review channel. Owner sweep rows
31–32.

## 2026-08-31 — Owner bug report: empty Requests queues said "null"

Owner, ~13:20, verbatim: *"https://blackbloc.heygabi.ai/requests.html it says null
since 0 records, fix this up to say something about this particular queue being
empty"* → measured in the owner's own browser (screenshot): each empty queue showed
its correct per-queue sentence ("Nothing is waiting on an answer…") **plus the
literal word `null`** and a dead `Previous · Page 1 · 0 shown · Next` row. Root
cause: `page-requests.js:footFor` returned `null` and `body.append(null)` renders
the WORD — the exact trap the file's own line-365 note documents for
`replaceChildren`; the call sites didn't filter. Fix `d2516aa`, deployed 13:28:
`footFor` returns an empty fragment (covers staff + member views), and
`ui.js:pager` renders nothing on page 1 with zero shown and no more pages (all
pages benefit). **Verified live by screenshot after deploy** — sentences only, no
null, no dead pager. 2257 tests, ruff, `check.mjs` 17/98 all green.

## 2026-08-31 — Restyle R2 live: the site wears Black Bloc

Moved whole from `TODO.md`:

- **Site restyle R2 — the skin** (R1 is LIVE `0c49257`, see `DONE.md`; brief =
  `info/site-restyle-design.md`): the "Black Bloc" theme dark+light as the new
  default (existing 5 themes stay), wordmark + display face, the sentence-voice
  copy pass (C's group names and labels), table toolbar/drawer furniture, Ctrl+K
  command palette, show-keys toggle. Status: **R2 Opus builder dispatched
  2026-08-31 ~12:35 in a worktree.**

**Landed as merge `c334922`, deployed 13:14 Phoenix** (Opus ~417k, 8 commits
`a28caef`..`090a593`; 2257 tests, ruff clean, 17 pages / 98 routes). What shipped:
the **Black Bloc theme** as default (`data-default-theme="blackbloc"` on all 17
pages; a stored choice still wins) with a measured contrast table — worst ratio
**4.51**, four §4C palette values darkened to clear 4.5, danger deliberately the
one COLD hue so Ban never wears the warmth; **Bangers** wordmark + page titles
(already on disk, OFL — Bricolage would have needed vendoring) via a
`--bb-title-font`/`--bb-chrome-font` split that leaves the six estate themes
untouched; **sentence-voice pass** — group captions "Runs the server / Runs the
cookout / The desk", all 90 labels rewritten (key set byte-identical), the
Overview TODAY sentence with each clause a link (it REPLACED the "Needs a human"
card — one fact, one home); **table furniture** — toolbars, ⓘ heads,
"Showing 1–N of M" feet (which absorbed four duplicate counters), a Cases
right-hand drawer (native dialog; Requests renders cards, no drawer — the
brief's escape hatch), plus two found defects fixed (opaque `--et-transit-bg`
was blacking out every theme's modal backdrop and the mobile scrim → `--bb-scrim`);
**Ctrl+K palette** (`palette.js`) over pages/settings-by-label-and-key/actions,
exercised end-to-end (anchor jump needs `behavior:'auto'` — smooth scroll gets
cancelled by the next layout); **Show keys** toggle, per-browser, no flash,
palette still finds hidden keys. Rendered: all 17 pages × both modes (34
screenshots), Cyberpunk + Discord regression-checked. Deviations accepted by
Fable at merge: seven themes in the dropdown (discord was already a sixth),
Bangers, no Requests drawer, TODAY replacing the card, `estate-theme.css`/
`theme.js` edited with precedent. **Verified live after deploy:** `/health` ok,
35 commands synced, `palette.js` 200, blackbloc default on the live index.
**NOT verified:** no real member-only session, no narrow viewport, no real-API
browser pass; contrast computed from hexes. Owner sweep rows 28–30. Known
cosmetic: "RUNS THE COOKOUT" wraps in Cyberpunk's rail (its own type scale) —
owner's call, on TODO.

## 2026-08-31 — code-notes.md re-keyed: 1215 of 1817 anchors were wrong

Moved whole from `TODO.md`:

- **`code-notes.md` re-key** — measured 2026-08-31: 88 files / 22,333 insertions
  since the last re-key (`666dd8e`); 4 of 4 spot-checked `bot.py` keys miss.
  A build-sized diff-driven pass (the file carries a red warning meanwhile).
  Three more builds appended sections today — re-key covers through `ef8a7a1`.
  Status: **re-key Opus agent dispatched 2026-08-31 ~12:35, editing in place,
  uncommitted for Fable review.**

**Landed `b22d44b`** (Opus ~274k): 1817 in-scope keys checked, **1215 updated**, 590
already correct, 12 GONE (marked in place with section banners, constructs deleted by
later phases — the pager guard, `classify` in chat, four mock fixtures, two retired CSS
rules, cyberpunk's neon `--et-info` pair, the golive preview command). Method: one base
commit fitted per section, keys mapped base→HEAD only along diff-equal lines, residue
anchor-hunted; two path-resolution bugs in the file's own reference style found and
fixed; two automated anchor-jump passes tried and REJECTED on dry-run evidence (clearly
wrong jumps beat no jumps). Cold 20-key samples: 45% exact before repair → **70% exact /
80% usable at delivery**, found misses then repaired (all were stale before `666dd8e`).
Integrity: 1629/1632 final keys land on a real construct line, 0 out of range. Residue
recorded in the file: 3 keys too vague to place confidently (`ui.js:415`, `bot.py:41`
deliberate, `birthdays.py:423`), and the false cyberpunk-accent note superseded in place
by Fable. CLAUDE.md's KNOWN-STALE warning replaced with the re-key rule.

## 2026-08-31 — KI-6/KI-9 closed and restyle R1 live in one deploy

Moved whole from `TODO.md` (both dispatched ~11:45 in parallel worktrees, merged and
deployed together as `0c49257` at ~12:20 Phoenix; `deploys.log` has the two lines —
the secret-set restart and the deploy; **2257 tests**, ruff clean, 17 pages / 98 routes):

- **KI-6 / KI-9 thresholds CROSSED by Phase 13** (found by the docs audit
  2026-08-31): the dashboard now admits any signed-in guild member, so KI-6's
  ">1 site user" trigger (sessions table + a per-session id in the cookie +
  revocation on logout) and KI-9's (HMAC poll-vote hashing with a
  `POLL_VOTE_SECRET`) are due. Status: **Opus builder dispatched 2026-08-31 ~11:45 in a worktree** (schema 17 sessions + per-poll hash scheme; expect a one-time sign-out for site users at deploy).
- **Site restyle R1** (of the R1 + R2 item; owner decisions 2026-08-31, all six
  taken; brief = `info/site-restyle-design.md`): R1 shell — grouped nav + icons,
  width-filling grid, docked dirty save bar, human labels. R2 stays on TODO.

**KI-6** (`90afc3e`, Opus ~219k for both security items): schema 17 `sessions` table,
`sid` in the signed cookie, live check on every authenticated request (30 s in-process
verdict cache, bounded 4096; logout poisons the cache BEFORE the DB write), logout
revokes. Old cookies = one-time sign-out at deploy (sweeps row 25). Documented
fail-open: DB down → signature + expiry only, because every data route already
refuses via `require_db`. **KI-9** (`272ea66`): schema 18 `polls.vote_scheme` stored
per poll at creation — an open poll NEVER changes scheme (no double votes); new polls
use HMAC-SHA256 keyed by `POLL_VOTE_SECRET` (via `config.py` only; minted and set on
Fly + `.env` by the session ~12:15, value never displayed); a keyed poll with the
secret missing refuses in words, never double-counts; unset secret = old scheme + one
startup warning, never a broken deploy. Deliberately NOT a registry key (a MAC key
the dashboard can show is not a MAC key) — recorded against checklist 33.
KNOWN_ISSUES: both entries superseded → CLOSED with residuals recorded.

**R1** (`b6a1fb3`→`87108ec`, Opus ~323k): the builder first measured that the top bar,
4-group rail and settingsEditor/saveBar plumbing had ALREADY shipped 2026-08-27
(`666dd8e`) — the restyle brief's "nothing built yet" was stale; corrected. Newly
built: one SVG-sprite icon per nav item (`icons.js`, currentColor, 3.46–10.69:1
across all 12 theme/mode pairs), width-filling 2-up grid (`layout.js`; tables go
full-width), docked dirty save bar everywhere `settingsEditor` runs (per-field
Save/Clear gone; ⌫ reset per row), `labels.js` with **90/90 registry keys** mapped
(checked programmatically against `settings_store.py`), empty-cell `—` / sentence +
action empty states, 24px title cap — plus a found-by-measuring shell bug: the docked
bar sat OFF-SCREEN in 5 of 6 themes (`grid-template-rows` auto vs `minmax(0,1fr)`),
invisible in the one theme being tested. All 17 pages rendered in Chrome against the
mock, zero console errors; permission machine / pager / search / section memory
re-checked live. **Verified live after deploy:** `/health` ok, 35 commands synced,
`added polls.vote_scheme` migration in the Fly logs, sessions table + vote_scheme
present on the live DB, R1 assets serving 200. **NOT verified:** no real browser has
signed in since the deploy (the one-time sign-out has not been SEEN), no anonymous
poll exists to prove an `hmac` row, the sub-1100px single-column layout was verified
by forcing the media query, not a narrow window. Owner sweep rows 25–27.

## 2026-08-31 — DB backup drilled: the first dated drill line in RECOVERY.md

Moved whole from `TODO.md`:

- **DB backup drill** (RECOVERY gap re-opened by the docs audit 2026-08-31):
  the live volume now holds real rows (38 birthdays + settings + cases) and
  RECOVERY.md's own threshold — "the first table with real data" — has passed.
  Need: a dump path off the Fly volume (`flyctl ssh sftp` or a scheduled
  export), drilled once, documented in `access/RECOVERY.md`.

**Landed 2026-08-31 ~11:35 Phoenix, run by Fable from the session:** consistent
snapshot via `sqlite3.backup()` on the machine (no sqlite3 CLI in the image —
python3 does it; a raw copy of the live WAL-mode file can tear), pulled with
`flyctl ssh sftp get` to `%USERPROFILE%\black-bloc-backups\backup-2026-08-31.sqlite3`
(290,816 bytes), **verified by opening it**: 30 tables, birthdays 38, chat_intents 15,
settings 6; drill file removed from the volume after. Procedure + three gotchas
(MSYS path rewriting, the bogus "handle is invalid" exit, never store a backup in
the tracked repo) written into `access/RECOVERY.md`, whose header now carries its
first dated drill line. **Residual, owned by the RECOVERY gap table:** the pull is
manual — nothing schedules it yet.

## 2026-08-31 — B4–B8: the last five audit leftovers, live

The 2026-08-27 site-feature audit's open tail (`info/site-feature-audit.md` §2), queued for
the post-reset resume and dispatched the morning the owner returned ("lets get started with
whats left on our todo list", ~10:13). One Opus builder (~485k), one commit per item off
`7b7840b`, merged `3cae955`, **deployed 11:32 Phoenix** (`deploys.log`); verified live:
`/health` ok, 35 commands synced, logged in 18:31:58Z. **2227 tests** (+65), ruff clean,
`check.mjs` 17 pages / **98 routes** (+9).

- **B4** `4f0f399` — temp-voice rooms get Rename / Cap / Lock / Hide on the dashboard.
  `do_rename`/`do_limit`/`do_privacy` refactored off `Interaction` onto a `Doer` NamedTuple
  (client, guild, user, via) that an Interaction already satisfies — panel and `/voice` call
  sites unchanged, ONE implementation; helpers return `Said` (a str carrying `ok`) so the API
  can pick 200 vs a refusal. Place-gated by `may_act_in` (test mode = only rooms in the test
  category, `409` in words). Skipped on purpose: region + kick (each needs a per-row picker;
  nothing blocks adding them).
- **B5** `47628b7` — `POST /api/rolemenus/{name}/unpost` + an Un-post button + **`/rolemenu
  unpost`** in Discord (checklist 33). Goes through `rolemenu_panels.unpost`, NOT
  `clear_message` (which would forget the id and leave the panel live — the KI-8 trap);
  guard asked twice to tell `409 test_mode` from `409 panel_stuck`; `note()` gained `via` so
  website panel actions log under a `web.` head (also fixes the same residual on `move_panel`).
- **B6** `2c65db0` — `POST /api/rolemenus/seed` + Seed defaults button; `created`/`skipped`
  as lists; `seed_summary` is the one wording both surfaces show; never rewrites an existing
  menu. New kind `role_menu.seeded` (routine).
- **B7** `d8f44c7` — staff assign from the site (`POST /api/rolemenus/{name}/assign`).
  `staff_assign` = the select callback's body lifted whole; the extraction fixed a
  checklist-12 ordering bug (the select answered the clicker BEFORE writing `role_grants` +
  the action line, so a failed reply ate the record). `role_diff` untouched — only menu-owned
  roles ever move. Deliberately NO test-mode refusal (roles aren't a channel; `/rolemenu
  assign` behaves identically today). Deviation: the form offers every menu with roles, not
  only `staff`-mode ones, matching the slash command; options labelled `name — mode`.
- **B8** `379b0c1` — `GET/PUT /api/events/{id}`: detail card + "Change it" for
  pending/approved events. `checked_fields` = the modal's whole validation chain shared, so
  the two doors cannot drift; the body names its IANA zone (browser zone shown above the
  field, staffer's `/timezone` as fallback); review channel renames via the guard-aware
  helper; an already-posted announcement or scheduled event keeps its old details and
  `notes` says so in words. New kind `event.edited` (routine).

**NOT verified live:** nothing ran against real Discord — no room renamed, no panel
deleted, no role granted, no event edited, no page rendered in a browser (contract + parse
checks only). Owner sweep = `access/sweeps.md` rows 21–24. Builder process notes worth
keeping: `pytest | tail` returns tail's exit code (check the summary line), and editing
source during a background full-suite run produces spurious `test_logkinds` failures.

## 2026-08-31 — Post-trip bookkeeping sweep: landed 2026-08-26/27 items moved off TODO

Moved whole from `TODO.md` (every item below was verified shipped by the 2026-08-31 docs
audit — ancestors of the live `8036918` per `git merge-base`, or otherwise measured; the
residual owner checks were consolidated into `access/sweeps.md` rows 18–20 and its new
phase-script appendix, which is now the ONE home for un-exercised items). Entries whose
text also appears inside the Phase 12/13 landing entries below are superseded by these
fresher copies (statuses advanced to DEPLOYED). The round-1 findings section and the
detailed phase click-scripts moved to `access/sweeps.md` rather than here, since their
only open half is owner verification. Standing rules moved here (90%-weekly stop,
configurable-both-ways) remain IN FORCE via memory / `CLAUDE.md` / checklist 33 — the
move only records that the *task* of establishing them is done:

### Owner test sweep — round 1 findings (2026-08-26 ~22:55) — moved whole

Four findings, all four **fixed on `main`, committed, and since DEPLOYED**:
`8fe0677` (temp voice) and `9d948ca` (role menus + `/twitch link`) — both are
ancestors of the live commit `8036918` (verified 2026-08-31 with
`git merge-base --is-ancestor`), so all four fixes have been live since
2026-08-27 at the latest. 817 tests passed at the time (the suite is now
**2158**). The still-open half — live re-verification by a person — is
`access/sweeps.md` row 19 (showall / twitch-link picker / lobby repair) and the
Loops row check.

| # | Owner's words | Fixed by | Residual owner check |
|---|---|---|---|
| 1 | *"we need a /rolemenu showall to display all role menus"* | `9d948ca` — `/rolemenu showall`, chunked at 1900 chars, ephemeral, no pings | run it (sweeps row 19) |
| 2 | *"for /twitch link it should say channel name not login, login sounds more concerning"* | `9d948ca` — parameter renamed to `channel`, no user-facing sentence says *login* | re-read the picker (sweeps row 19) |
| 3 | *"it made a locked channel i cant get into. its just a lock icon."* | `8fe0677` — explicit overwrites (allowed role + resolved staff + the bot), and `/tempvoice setup` now REPAIRS the lobby it already has | `/tempvoice setup` says **repaired**, lobby renamed, Member + staff connect (sweeps row 19) |
| 4 | 8a merge left `TempVoice._reconcile_loop` with no `@loop.error` and no health | `8fe0677` — handler + `last_ok_at`/`last_error` + `loop_health()` | status page Loops row shows `_reconcile_loop` |

⚠️ **Root cause of the `join` name, measured not guessed:** nothing in the cog
truncates a channel name. `channel_name` is the only string handling in the file
and is not on the setup path; the command's `name` parameter introspects as
optional with default `None` (`Command._params["name"].required is False`), so an
unsupplied name renders the full default. The only way to get `join` is Discord
having sent `name: join` — a value typed into the optional field. The fix is
therefore a real setting (`tempvoice_creator_name`) plus a repair path, not a
truncation bug fix: there was no truncation to fix.

### The moved bullets

- **Owner 2026-08-27 ~08:40, verbatim: "It's still not quite the look and
  feel I want. Can you research some other bot sites for inspiration and then
  make a mock"** → (1) research agent: Carl.gg, MEE6, Dyno, YAGPDB, Wick,
  ProBot, Sapphire dashboards — layouts, nav, module cards, colour, density,
  toggles → `info/dashboard-inspiration.md` with 2–3 candidate directions
  — **LANDED 2026-08-27:** [`info/dashboard-inspiration.md`](info/dashboard-inspiration.md)
  (11 sites surveyed; Carl, YAGPDB, Discord, Linear, Vercel/Geist and the
  Cloudflare dashboard read live, the rest marketing-only; three directions
  — A "Discord-native", B "Ops console", C "Cookout" — with dark+light
  palettes, self-hostable type stacks and ASCII wireframes; recommendation =
  A's shell + B's tables, mock A and C). **The four owner questions DECIDED
  2026-08-31 ~10:30 (asked one at a time): direction = "I want a A/C hybrid" ·
  "Both, dark default" · "Keep all 5 themes" · nav "Icons + text".** Step (3)
  unblocked: Fable writes the restyle brief (`info/site-restyle-design.md`),
  build queued AFTER the B4–B8 builder lands (both touch `site/`);
  (2) a design-canvas mock (artboards: Overview, a feature page, Settings) in
  the candidate directions for the owner to react to — **LANDED 2026-08-27 ~09:35:** canvas https://claude.ai/code/artifact/ad76df70-49f4-4fcd-a66a-07c8969d0ddd (A + C × Overview/Moderation/Settings, 1440×900, dark only; working `.dc.html` files live in the session scratchpad `mock/`, not the repo); (3) the winner becomes
  the site restyle brief (estate theme snapshot may be replaced — owner's
  call; site stays disconnected from heygabi).

- **Owner 2026-08-27 ~06:35, three asks (verbatim).** Asks (1) the site URL in
  the bot's bio and (2) the "Cookout attendees" status **landed 2026-08-27 —
  moved whole to [`DONE.md`](DONE.md)**. Still open: (3) "The ux is a lot of input boxes per
  page, maybe some page treeing and side tabs to make each page less dense,
  some search stuff, sections that condense" → batch 5 UX pass: per-page left
  sub-navigation (tree), collapsible sections (collapsed by default except
  the first), a search box on every table and on Settings, remember last tab
  + open sections, denser → grouped cards.

- **Owner 2026-08-27 ~06:30 on the dashboard, verbatim: "Website looks okay,
  ui good with options maybe slightly better ux".** → a UX pass (batch 5),
  aimed once the owner names what felt clunky (tabs / forms & saving / tables
  & filtering / sign-in). Candidate improvements regardless: remember the last
  tab, loading skeletons instead of blank tiles, inline save feedback next to
  the field, table search boxes, sticky nav, keyboard focus order, mobile
  layout check.

- **Owner 2026-08-27 ~06:00, verbatim: "would like a way to save a channels
  changed details so the next time the same user makes one it keeps their old
  name and set up".** Measured: already implemented for name, limit, lock,
  hide (+ bitrate in `6b75c11`) via `tempvoice_prefs` — saved on each change,
  re-applied in `_create_for`. **Batch 4:** also remember `region` and the
  permitted/banned member lists (TempVoice does), re-apply on spawn; `/voice
  info` shows what is remembered; `/voice reset` clears it. Owner confirmed
  `/help` and `/tempvoice status` work (2026-08-27 ~06:00).

- **Site sign-in VERIFIED by the owner 2026-08-26 ~23:00** ("i went to the site
  and i now see a health dashboard") — 8a fully closed.

- **8b MERGED and reconciled into `main` 2026-08-27** — `178fe69` (API) then
  `6bf4669` (pages), then one reconcile commit. **1105 tests, ruff clean**, and
  `node site/mock/check.mjs` reports 13 pages / 49 routes with every key the
  pages read present. ✅ **DEPLOYED since** — `178fe69` is an ancestor of the live
  commit `8036918` (2026-08-27 20:15); 8b first shipped in `5da62b3` at
  2026-08-27 06:14. *(Was "NOT pushed, NOT deployed"; corrected by the docs
  audit 2026-08-31. The mock now reports **17 pages / 89 routes**, not 13/49.)*
  Batch 3 (below) also merged.
  ⚠️ **NOT verified: any page against the real API in a browser** — only
  against the mock, whose shapes are now checked against the same table
  (`site/mock/contract.json`) the routers are. Nothing has run against live
  Discord. Open items from the reconcile:
  - **Nine shape mismatches were found and fixed** (see `DONE.md`); the fix that
    matters longest is `site/mock/contract.json` + the two checkers, because
    without it the next shape change drifts the same way silently.
  - `modlog`, `mod` and `carl` settings keys now serve in the **`automod`**
    namespace via `settings_api.py:NAMESPACE_OVERRIDE`. A new moderation key
    with a new prefix needs a line there or it grows its own one-key group.
  - Was: **8b dispatched 2026-08-26 ~23:05** (owner: "the who category … we need
    to resolve that to discord username. same with target … health can get
    shoved to a different tab but we need all the moderation tool menus"):
    design + API/page contract in `info/phase8b-design.md`; Builder A (API) and
    Builder B (pages, with a Node mock server) in parallel worktrees.

- **Test-sweep batch 4 LANDED on `main` 2026-08-27 and is DEPLOYED** (`47634b8` is an ancestor of the live `8036918`; verified 2026-08-31 — was "NOT pushed and NOT deployed")
  — three commits, all three owner asks done, **1173 tests, ruff clean,
  `node site/mock/check.mjs` clean**:
  - `47634b8` — **the incumbent bot and the parity tool are gone** (owner: "Carl
    bot has no actions or setup, lets remove the mentions and parity to it").
    `/automod parity`, `GET /api/mod/parity`, the dashboard's parity card, the
    mock route, the contract entry and the `carl_modlog_channel_id` setting all
    removed; `/rolemenu seed-from-carl` is now **`/rolemenu seed-defaults`** (the
    seed data is untouched). `grep -ri carl black_bloc site` is **empty**. The
    automod rules are unchanged — mention-spam armed, the rest log-only — and the
    **cut-over criterion is now the owner's judgement from the shadow log**
    (`info/feature-list.md`, F7). ⚠️ `SettingsStore.load` now ignores a stored
    row whose key has left the registry and warns once, so the live volume's
    `carl_modlog_channel_id` row cannot crash a start.
  - `7b487cf` — **temp voice remembers the whole set-up** (owner: "would like a
    way to save a channels changed details so the next time the same user makes
    one it keeps their old name and set up"). Schema **11**: `tempvoice_prefs`
    gains `region`, `permitted_ids` and `banned_ids` beside name/limit/lock/
    hidden/bitrate. `/voice info` now also lists what is remembered, and
    **`/voice reset`** forgets it.
  - `6f45299` — **favicon**. `site/public/favicon.ico` (a hand-written 32×32 ICO)
    plus a `<link rel="icon">` on all thirteen pages, so the `GET /favicon.ico
    404` on every page load stops.
  - ⚠️ **Owner test after the deploy:** `/rolemenu seed-defaults` (the old name is
    gone from the picker), `/automod status` (no parity line), then in a temp
    channel `/voice permit @someone` + `/voice ban @someone-else` + `/voice
    region us-west` → leave so it deletes → re-join the lobby and check the new
    channel has the same region and the same two people set; `/voice info` shows
    both halves; `/voice reset` clears it. And the dashboard tab icon.

- **Batch 3 MERGED into `main` `6b75c11` 2026-08-27** (see `DONE.md`) — the panel
  now posts into the test channel and `/voice` exists. **1134 tests, ruff clean,
  `node site/mock/check.mjs` clean.** ✅ **DEPLOYED** — `6b75c11` is an ancestor of
  the live `8036918` (verified 2026-08-31; was "NOT pushed, NOT deployed"). Still
  to do: review the merged `tempvoice.py`, then the
  owner tests the panel in `#mute-me-bot-test-spam` (press Rename and Lock from
  there — the click has to find its way back to the voice channel) and
  `/voice info` / `/voice bitrate` / `/voice region`. Owner also had the stale
  `🍯-do-not-post-here` trap deleted (2026-08-26 23:33) — `/honeypot setup`
  recreates it.

- **Test-sweep batch 2 FIXED on `main` and DEPLOYED** (was "NOT pushed and NOT
  deployed"; corrected by the docs audit 2026-08-31 — it is in the live
  `8036918`, and the owner confirmed `/help` works 2026-08-27 ~06:00) (see
  `DONE.md`, 2026-08-27): `/help` and temp-voice lobby adoption. Still to do:
  (a) run `/help` and `/help filter:temp` and check
  the `(staff)` marks, (b) run `/tempvoice status` — it should name any lobby it
  is not keeping track of — and `/tempvoice setup`, which should say it **took
  it over** rather than making a second channel.

- **Test-sweep findings, batch 1 (owner, 2026-08-26 ~22:55) — fixer dispatched:**
  (1) "we need a /rolemenu showall to display all role menus"; (2) "/twitch
  link it should say channel name not login, login sounds more concerning";
  (3) "it made a locked channel i cant get into. its just a lock icon" —
  measured: `/tempvoice setup` made a voice channel named **"join"** (name
  truncated) inheriting *The Basement*'s overwrites (`@everyone` deny connect;
  staff roles have view+manage but no connect) → nobody can connect. Fix =
  full name + explicit view/connect allows for the allowed role and staff on
  creator and spawned channels, and `setup` repairs in place. (4) TempVoice
  loop health + `@loop.error` (from the 8a merge).

- **OAuth redirect `https://black-bloc.fly.dev/api/auth/callback` saved by the owner 2026-08-26 21:38; `DISCORD_CLIENT_SECRET` in `.env` validated against Discord (client-credentials token issued).**

- **Decisions made autonomously 2026-08-26 ~21:20 (owner may overturn):**
  (a) `/untimeout` and `/unban` are refused while TEST_MODE, like the other
  destructive commands — lifting a punishment changes the live server and is
  access-increasing (global rule: confirm access-increasing actions); (b)
  `/settings show` is chunked to stay under Discord's 2000-char limit (43 keys
  after Phase 7); (c) Phase 8a dispatched in parallel since `wrangler login`
  landed. All three are in the Phase 6/8a fix or build briefs.

- **Q14 DECIDED 2026-08-26 ~21:55 — Option A:** the Fly app serves the site
  itself under ONE hostname (`blackbloc.heygabi.ai` → CNAME to
  `black-bloc.fly.dev`, DNS-only); no Cloudflare Pages; cookie stays
  `SameSite=Lax`. Owner's words: "seems cut and dry". Done on Fly 2026-08-26 ~22:00: cert requested
  (`flyctl certs add blackbloc.heygabi.ai`), IPs allocated (shared v4
  `66.241.125.10`, v6 `2a09:8280:1::17c:d6fb:0`). **Owner actions:** (1)
  Cloudflare DNS, proxy OFF: `A blackbloc → 66.241.125.10` and `AAAA blackbloc
  → 2a09:8280:1::17c:d6fb:0` (or `CNAME blackbloc → 3ppe323.black-bloc.fly.dev`);
  (2) Developer Portal → OAuth2 → add redirect
  `https://blackbloc.heygabi.ai/api/auth/callback` (keep the fly.dev one).
  **DONE 2026-08-26 ~22:25:** both DNS records added via the Cloudflare
  dashboard (Claude drove it; the owner's password-manager popup blocked
  keystrokes so values were set via form_input), public DNS resolves the A
  record, second OAuth redirect added by the owner. Remaining: `flyctl certs
  check blackbloc.heygabi.ai --app black-bloc` must say verified before the
  8a deploy (auto-validates once Fly sees the records). Known trade-off: if the bot process is down the page is
  down too (B would have shown an "API unreachable" notice) — accepted.

- **Follow-up from the 8a merge:** `TempVoice._reconcile_loop` records no loop
  health and has no `@loop.error` handler (checklist 28 gap on main) — add it.
  `site/README.md` points at the gitignored `docs/access/site.md` — either inline
  the deploy steps or accept.

- **Phase 8a unblocked (2026-08-26 21:10):** owner ran `npx wrangler login`
  (Cloudflare account `nbaslamking@gmail.com`, Node v24.11.1); `wrangler
  whoami` works from the session. 8a = read-only status page on Cloudflare
  Pages at `blackbloc.heygabi.ai` (design: `info/phase8-design.md`) — dispatch
  after Phase 7 merges, or earlier if the core queue stalls. Creating the Pages
  project + the DNS record happens at deploy time.

- **Fly secrets gotcha (2026-08-26):** piping python output into `flyctl secrets
  import` from PowerShell prepends a UTF-8 BOM to the first key name ("\ufeffTWITCH_…
  is not a valid secret name"). Write an ASCII temp file and redirect it with
  `cmd /c "flyctl … < file"`. → move to `access/deploy.md` (done below) and gotchas.

- **Back up `docs/` off this machine** — it is local-only now (RECOVERY gap).

- **Bot access RESOLVED 2026-08-26 ~18:00:** owner gave `Black_Bloc` the `Bots`
  role (carries Administrator — owner accepted: "it'll need to do moderation
  roles eventually"). Rescan then read 128/128 channels.

- **Role menus (new feature row needed at design time):** Carl's 5 reaction-role
  panels with measured emoji→role maps are in `archive/current-bots/discord-scan-2026-08-26.md`
  §D (gotchas: skin-tone emoji in text vs plain in reactions; 🧑‍🍳 is a ZWJ
  sequence). YAGPDB has NO role menus despite "7 role commands" on its dashboard.

- **Owner 2026-08-27 ~12:09, verbatim: "Stop at 90 weekly so we can save some headroom"** → project rule: no new agent dispatch at ≥ 90% weekly (global rule says 93); builds in flight land, nothing new starts; saved to memory. Status: **in force (weekly 83% at 12:02).**

- **Owner 2026-08-27 ~17:27, verbatim: "im getting on a plane tomorrow morning (friday and im not back until sunday night after reset) so we have wiffle"** → the 90% weekly stop is lifted for THIS window only (owner away Fri 08-28 → Sun 08-30 night; weekly resets Sun 16:00): spend the remainder on 12b now (parallel with 12a); at the Sunday reset, a one-shot wake-up resumes with the audit leftovers B4–B8 (temp-voice per-room actions, role-menu un-post/seed/staff-assign, event detail/edit) unless the owner has said otherwise. The 90 rule returns after the reset. Status: **12b dispatched 17:28 in parallel; Sunday 16:05 wake-up scheduled.**

- **Owner 2026-08-27 ~17:33, verbatim: "yes start keeping the docs up to date every task and creating our normal set of access docs. temporarily committ the docs folder so i can use it while away, and any scripts i'll need"** → `docs/` force-added and pushed as a TEMPORARY exception to the local-only rule (secret scan clean: names only); `access/runbook.md` + `access/sweeps.md` added; `scripts/doctools/move_done.py` committed (the folder was `scripts/docs/` until `7b7840b`, 2026-08-31 — it tripped the session-start docs-shape hook). Status: **committed + pushed 17:35. ✅ RESOLVED 2026-08-31: the owner chose to KEEP `docs/` tracked permanently** ("actually lets keep it tracked", `1eb8870`, which also dropped `docs/` from `.gitignore`); no history purge. The temporary exception is now the rule — see `DOCS_STANDARD.md` §9.

- **Owner 2026-08-27 ~17:37, verbatim: "committ anything i'll need. also i probably need a copy of the .env on my laptop… can we store the .env in a firebase or something safely and then write it to a local file with a script?"** → decided: no Firebase (a service-account key is a second secret to protect); `scripts/env-lock.sh` / `scripts/env-unlock.sh` (OpenSSL AES-256-CBC + PBKDF2, passphrase-only) committed; `.env.enc` allowed by `.gitignore`; the owner runs `lock` in their own terminal and commits `.env.enc` — Claude never handles the values. Laptop checklist in `access/runbook.md`. Status: **scripts + docs committed 17:40; the owner runs `sh scripts/env-lock.sh` and commits `.env.enc` before leaving.**

- **Usage 18:03 Phoenix: weekly 90% (session 16, Fable 33).** The 90 stop is reached; per the owner's away-window override the four in-flight builds (12a, 12b, 13a, 13b) land and get merged/tested/deployed; NOTHING NEW is dispatched before the Sunday 16:00 reset. Expect weekly ~94–96 after they land; merges/deploys are cheap. If a build dies on a limit: its commits survive in `.claude/worktrees/`, `git worktree list` shows them; resume from the Sunday wake-up.

- **Owner 2026-08-27 ~18:17, verbatim: "lets mute all the would calls too, keep that in discord logs"** → read as: every `would_*` (shadow) kind is ROUTINE — never posted to the Discord log channel under the default `important` level, always kept in the DB / website Logs / `/… logs`. Matches the Phase 12 design; pinned to 12a explicitly. (`all` per feature still shows them in Discord for a test sweep.) Status: **confirmed to 12a 18:18.**

- **Defect found by 13b (18:25), Sunday: the pager scroll-to-top does not work.** `ui.js:pager` — `#dash` `replaceChildren` resets the scroller to 0 before the helper runs, so its "already at the top" early return always fires; the page lands at the top of the PAGE, not the list (11b's "25923 → 276.67" does not reproduce). Fix: scroll AFTER the new rows render (requestAnimationFrame / after `onPage` resolves) to the list block's top minus the top bar, unconditionally. Affects Polls, Chat, Members, Requests. Also from 13b: outcome sentences render `**bold**` literally (one shared fix in `ui.js:run`); `foldout()` had no CSS since 10b (13b styled it); Requests page owes `await logsSection('request')` once 12b is merged. Owner 18:31: "fixs the defects now" → Status: **LANDED in `a4e7fcd`** on the integration branch (off `main` @ `16c5781`), after `641e53b` merged 13b. All three: `ui.js:pager` now scrolls unconditionally AFTER the rows render — two rAFs racing a 60 ms timer, because rAF does not fire in a backgrounded tab at all (measured: Requests 9340 → 930 with the list top at 8.18px, against 938.18px unfixed; Members and Polls likewise); `**bold**` becomes `<strong>` through `ui.js:boldParts` in `notice()`'s `say`, text nodes only, never innerHTML; `await logsSection('request')` is at the foot of the Requests staff view. `foldout()`'s CSS came in with 13b's own commit. **DEPLOYED** — shipped in `8036918`, live 2026-08-27 20:15 (`deploys.log`); status line corrected by the docs audit 2026-08-31. Not yet exercised by a person: see `access/sweeps.md` rows 14–17.

- **Owner 2026-08-27 ~18:28, verbatim: "no you're correct, just mak sure all decisions we make here can be configured in dashboard and with bot"** → (1) confirms the `would_*` muting reading; (2) standing rule: every decision is a registry key or has both a slash path and a dashboard control — added to `CLAUDE.md`, review-checklist item 33, and memory. Status: **rule in force; audit of existing decisions = every `*_mode`, `*_log_level`, poll/request/chat keys are registry keys; per-item fields have both paths (9a `/rolemenu edit` + 9b editor; 10 `/poll create` + create form; 13 `/request set` + board).**

- **Owner 2026-08-27 ~18:52, verbatim: "yes lets be done when this lands, we'll save the last 9% for bugs"** → after the integration build lands: merge, test, deploy, docs, STOP. The remaining weekly budget (~9%) is reserved for bug fixes only until the Sunday 16:00 reset; the Sunday wake-up (B4–B8 on fresh budget) stays scheduled. Status: **in force.**

- **Owner 2026-08-27 ~18:51, verbatim: "also in the logs we should add how someone has set a setting, if they set it in discord or on the website"** → the settings audit + Logs rows show **Via: Discord / website** — derived today from the kind prefix (`web.settings.set` vs `settings.set`), and made explicit as `details.via` on every write path (`/settings set-value` → discord, `settings_api` → website); `/… logs` lines carry it too. Status: **LANDED** on the integration branch. `logkinds.via_of` is the one home (recorded word wins, `web.` head decides the rest); `actionlog.log_action` stamps `details['via']` on EVERY row so no writer can forget, and the two settings doors pass it explicitly as well. `GET /api/actions` rows, the CSV and the Settings audit rows all carry `via`; the Logs table and the Settings audit table have a **Via** column; `/… logs` lines end `· via Discord` outside the 100-character cap. ⚠️ Residual, accepted: a website path that logs a BARE feature kind (`apply_decision`) reads Discord, with its `web.` twin beside it reading Website — settings have no such pair. **DEPLOYED** — shipped in `8036918`, live 2026-08-27 20:15 (`deploys.log`); status line corrected by the docs audit 2026-08-31. Not yet exercised by a person: see `access/sweeps.md` rows 14–17.

## 2026-08-27 — Phase 13: Requests (/request, member sign-in, the Requests page) + integration night fixes

Moved whole from `TODO.md`:

- **Owner 2026-08-27 ~17:42, verbatim: "we should also make a /request command so we can stop using the google doc, also put it on the website"** → F18 Requests: a `/request` slash (modal) that replaces the Google doc members currently fill, stored in the DB, listed/triaged on a dashboard **Requests** page (status open / accepted / done / declined, assignee, notes, reply to the member), with the same review pattern as events/role requests. **Owner ~17:46: "its just the initial doc that I gave you, its an idea on paper, we should make our request form more robust for sure. no need for name just collect who ask, get the what, the why, and a due date if needed. review can be on the site but its its a mod or higher auto approve it. have it go to a pending features list"** → F18 = feature-request intake: `/request` modal (What, Why, Due date optional; requester recorded automatically), status pending → approved → planned → in progress → done / declined; a mod-or-higher requester is auto-approved; dashboard **Requests** page = the pending-features list (filters, assignee, notes, decide, DM the requester). Design `info/phase13-design.md`. Status: **owner "just send them now… so when we get back we can go to work" (17:52) → 13a + 13b dispatched 17:53 in parallel off `40b7782` (weekly 89; owner override for the away window).**
- **Owner 2026-08-27 ~17:53, verbatim: "also let people put request on the dashboard too"** → the dashboard admits ANY signed-in guild member: non-staff land on a member-only **Requests** view (file a request, see and withdraw their own) with the staff nav hidden; staff keep the full dashboard; every other API route stays staff-gated. Relayed to 13a (auth: member sessions, `GET /api/requests/mine`, `POST /api/requests` member-gated + rate-limited) and 13b (member mode of the page, shell hides staff nav, gate copy). Status: **relayed 17:54 to both in-flight builders.**
- **Defect found by 13b (18:25), Sunday: the pager scroll-to-top does not work.** `ui.js:pager` — `#dash` `replaceChildren` resets the scroller to 0 before the helper runs, so its "already at the top" early return always fires; the page lands at the top of the PAGE, not the list (11b's "25923 → 276.67" does not reproduce). Fix: scroll AFTER the new rows render (requestAnimationFrame / after `onPage` resolves) to the list block's top minus the top bar, unconditionally. Affects Polls, Chat, Members, Requests. Also from 13b: outcome sentences render `**bold**` literally (one shared fix in `ui.js:run`); `foldout()` had no CSS since 10b (13b styled it); Requests page owes `await logsSection('request')` once 12b is merged. Owner 18:31: "fixs the defects now" → Status: **TONIGHT, immediately after 12a/13a land and the four branches are merged (the fix touches `ui.js`, which 12b and 13b also change) — one small Opus build: pager scroll after render, `**bold**` rendering in outcome sentences, `logsSection('request')` on the Requests page; then deploy.**
- **Owner 2026-08-27 ~18:50, verbatim: "also the cyber punk theme on the dashboard hs strayed more from cyber punk and way more ito neon. copy the ones we use on other gabi platforms and tighten that up, we look like a neon circus out here."** → restore the estate's Cyberpunk palette (the values the other gabi sites use = the pre-neon block in `estate-theme.css` before commit `b936b96`), keeping the later nav-head / level-field tokens; drop the magenta headings and the extra neons; keep blue/cyan lead only where the estate has it. Status: **LANDED in `f10260d`.** `git diff b936b96^` over `estate-theme.css` is now nothing but the later `--et-nav-head-*` tokens and the note; cyan leads, yellow wears the headings and the wordmark, magenta is danger only, `--et-info` inherits the accent again, and `--et-focus-ring` was re-derived to cyan. ⚠️ Two LIGHT-mode contrast figures are below 4.5:1 (accent 4.46 on the page ground, heading 3.54) — they are the estate's own values and the neon set beat both; recorded, not quietly improved. **Still to deploy.**
- **Owner 2026-08-27 ~18:51, verbatim: "also in the logs we should add how someone has set a setting, if they set it in discord or on the website"** → the settings audit + Logs rows show **Via: Discord / website** — derived today from the kind prefix (`web.settings.set` vs `settings.set`), and made explicit as `details.via` on every write path (`/settings set-value` → discord, `settings_api` → website); `/… logs` lines carry it too. Status: **in tonight's defect-fix build.**

**Landed as Phase 13 + the integration night** (`info/phase13-design.md`): 13a merge `7343a03` (Opus ~424k, +130 tests; `/request create|list|withdraw|set`, schema 16, five `request_*` keys, `writes.member_dependency` on exactly three routes with a 10/min bucket, `auth/me` gains `member`), 13b built on its branch (Opus ~359k) and merged by the integration build `8036918` (Opus ~494k; 31 conflict hunks reconciled — the real router won the contract; 13b's 30-row fixture and member gating kept in the mock; `app.js`/`shell.js` kept both 12b's Logs and 13b's Requests). Same merge: request kinds classified + `request_log_level` (13th) + `/request logs`; command tree pinned at 35; pager now lands on the list (measured: Requests 9340→930 with the list top at 8 px; note rAF never fires in a background tab — a 60 ms backstop is what actually ran); `**bold**` rendered via text nodes; Logs section on Requests; **Cyberpunk restored to the estate palette** (`git diff b936b96^` on the theme file = only the later nav-head tokens; light-mode accent 4.46 and heading 3.54 are the estate's own sub-AA values, kept on purpose); **Via** column (Discord / Website) on settings audit rows, Logs rows and `/settings logs`, from `details.via` on every write path with the kind prefix as fallback. `main` 2158 tests + ruff green; `check.mjs` 17 pages / 89 routes. Deployed 20:15 Phoenix by Claude (`deploys.log`); **verified live:** 35 commands synced, logged in 03:14:49Z, `/health` ok, Requests page rendered signed in. Accepted residual (code-notes): a website decision that also logs a bare feature kind (`request.approved` beside `web.request.approved`) shows the bare twin as "Discord" — settings themselves are correct. **NOT verified live:** no `/request` filed by a person, no member (non-staff) sign-in seen, no DM, no `/request logs`; pager only measured in a backgrounded tab. Owner sweep in `access/sweeps.md`.

## 2026-08-27 — Phase 12: Logs — quiet Discord, loud website, /… logs everywhere

Moved whole from `TODO.md`:

- **Owner 2026-08-27 ~17:14, verbatim: "i think we need to pipe a lot of the logs to the website and a logs command per function and keep the discord spam to a minimum"** → Phase 12 "Logs": (1) every action still lands in the DB (the action log already does) but the Discord log channel only gets **important** kinds — a per-feature `<feature>_log_level` (`off` / `important` / `all`, default **important**) with "important" = acted on a member (warn/timeout/kick/ban/role grant/approve/deny/expire) or FAILED; shadow `would_*`, housekeeping (imports with 0, panel reposts, reminders, sweeps, `chat.*`, `poll.created`) stay off Discord; (2) website: a per-feature **Logs** section on every feature page (recent actions by kind prefix, search, kind chips, pager) + a global Logs page (all kinds, actor/target filters, CSV export) — the Audit tab becomes that page; (3) slash `/<feature> logs [count]` (ephemeral, last N from the DB) on every feature group. **Decision (owner ~17:17): "a is fine, also any approvals need to make notifications still"** → default "important" = acted on a member OR failed; and every approval REQUEST (role requests, poll reviews, event proposals) still posts its card/ping to its approval channel regardless of log level — those are notifications, not log lines, and are never filtered. Status: **owner "send it now" (17:23, weekly 88 — overriding the reset hold) → 12a dispatched 17:24 off `0090fd8`; 12b when 12a lands if weekly < 90, else after the Sunday 16:00 reset.**
- **Owner 2026-08-27 ~18:17, verbatim: "lets mute all the would calls too, keep that in discord logs"** → read as: every `would_*` (shadow) kind is ROUTINE — never posted to the Discord log channel under the default `important` level, always kept in the DB / website Logs / `/… logs`. Matches the Phase 12 design; pinned to 12a explicitly. (`all` per feature still shows them in Discord for a test sweep.) Status: **confirmed to 12a 18:18.**

**Landed as Phase 12** (`info/phase12-design.md`): 12a merge `07fcea2` (Opus ~471k, +76 tests) and 12b merge `5fd44ae` (Opus ~365k), built in parallel on the owner's away-window override (weekly 89→91); mock-file conflicts resolved for the real router; `main` 2017 tests + ruff green; `check.mjs` 16 pages / 81 routes. Deployed 18:38 Phoenix by Claude (`deploys.log`); **verified live:** 34 commands synced (`/mod`, `/chat` new), logged in 01:38:07Z, `/health` ok; Logs page and per-page sections seen on the mock. **What shipped:** `black_bloc/logkinds.py` — 269 emitted kinds classified, 88 important / 181 routine, a test that fails on any unclassified new kind; every `.would_` kind routine BY RULE (owner 18:17); twelve `<feature>_log_level` keys (off/important/all, default important; `mod_log_level` namespaced to automod); the gate in `log_action` (row always written; Discord line only when `should_post` or `notify=True`; approval cards untouched — tested with `rolemenu_log_level = off`); `/<feature> logs [count] [important_only]` on twelve groups (per-guild top-level count 34/100, `/voice` 18/25); `GET /api/actions` gains feature/q/since/until/important/actor/target, paging, `kinds`, per-row `feature`/`important`/`summary`, 5000-row scan cap reported in `notes`, `export.csv` (not in the contract by design); dashboard `assets/logs.js:logsSection` on twelve pages + Settings, the Audit tab renamed **Logs** (file name kept), Overview's Last actions important-only, a 390 px overflow fix. Side effects worth knowing: `core` and `chat` have NO important kinds so they are silent on Discord by default; `golive` drops to failures only; a web approval can log two important lines (`web.poll.approved` + `poll.approved`) — pre-existing. 12a also re-keyed ~540 stale `path:line` references in code-notes (1045/1046 verified). **NOT verified live:** no Discord line has been observed suppressed or posted under the gate; no `/… logs` run in Discord; owner sweep = flip `golive_log_level` all → `/golive test` → back to important → `/golive test`, and `/golive logs`.

## 2026-08-27 — Phase 11: Chat 2 — editable intents and lines, data intents, routing, manners, the Chat page

Moved whole from `TODO.md`:

- **Owner 2026-08-27 ~14:12, verbatim: "yes lets do all of those,"** (F10 step 2, after being shown the canned lines and five suggestions) → build, in order, as one phase (`info/phase11-design.md` to write): (1) **Chat page** on the dashboard: intents with their trigger words and lines, add/edit/remove lines and whole intents (stored in a `chat_intents`/`chat_lines` table seeded from today's `chat.py` tables; the code table becomes the fallback); (2) **data intents**: who is live (open go-live sessions), what is next (next approved event with a HammerTime stamp), birthdays (next few), how many of us (attendee count), my roles (menus the member can pick from), what time is that for me (F4 timezone conversion); (3) **routing**: "I need a mod" / "help me" → opens or explains modmail; (4) **manners**: `chat_ignore_channels` setting, optional emoji reaction instead of a reply to a bare greeting (`chat_greeting_reaction` on/off); (5) later: the real conversation backend behind `reply_for`, persona prompt built from the lines. Status: **owner "Do it" (~15:55) → 11a dispatched 16:09 off `ebf99a2`; owner "Dispatch anyway" (16:18, weekly 87 — overriding the headroom hold) → 11b dispatched 16:19 in parallel off `ebf99a2`, building against the design's routes + its own mock entries; contract/mock conflicts expected at merge.**

**Landed as Phase 11** (`info/phase11-design.md`): 11a merge `dc4985c` (storage schema 15 `chat_intents`/`chat_lines` with a `slot` column filled/empty/attendee, per-guild seed of 15 intents with the code tables as fallback, classification over guild rows, six data intents, `need_a_mod` routing, manners settings, `/api/chat` eight routes; Opus ~399k, +122 tests) and 11b merge `e03176b` (the Chat page — Try it, per-intent cards with trigger chips and inline lines, New intent, settings section; Opus ~299k) built IN PARALLEL on the owner's "Dispatch anyway" (weekly 87→88); the two halves met on a six-point contract clarification relayed mid-build (`tokens` per intent, `message` on writes, settings row shape, bool manners keys, route precedence for "help me", contract fixture ids). Conflicts at merge: exactly the two mock files, resolved contract = 11a's (router truth), `server.mjs` = 11b's (page-validated) + one action-kind rename to `web.chat.line_deleted`. `main` 1941 tests + ruff green; `check.mjs` 16 pages / 80 routes after the mock `try` gained `slot`. Deployed 17:05 Phoenix by Claude (`deploys.log`); **verified live:** chat cog loaded, `chat: seeded 15 intent(s) for guild …` in the Fly logs, 32 commands synced, `/health` ok. Deviations recorded in code-notes: `reply_for` is now a coroutine (data intents read the DB) with `answer_for` beneath it as the step-3 seam; `GET /api/chat/intents` seeds a guild that has none (a write on a read, so the page is never blank); built-ins cannot be deleted, only disabled. **NOT verified live:** no @-mention answered from an edited line yet, no data intent asked in the server, no 👋🏿 reaction, no staff-channel route note; `time_for_me`'s bare "7pm = Phoenix" assumption untested on a person. Owner sweep: `@Black Bloc how many of us`, `who's live`, `what's next`; edit a greeting on /chat.html and say hi.

## 2026-08-27 — Phase 10: polls (native Discord polls wrapped, panel surface, recurring, Polls tab)

Moved whole from `TODO.md`:

- **Owner 2026-08-27 ~10:46, verbatim: "can we also have a poll app, copy polly or any other popular polling app in discrd"** → feature **F15 Polls** (already on the feature list as "Future (found)"). Step 1: research agent (Polly, Easypoll, Simple Poll, Discord native polls via discord.py `Poll`) → `info/polls-research.md` with a feature matrix and a recommended design; step 2: owner decisions one at a time; step 3: `info/phase9-design.md` + build (shadow-free feature, but test-channel only under TEST_MODE). **Research LANDED 10:58** → [`info/polls-research.md`](info/polls-research.md): Polly is a Slack/Teams product, not a Discord app — the Discord equivalents are EasyPoll / Simple Poll; Discord NATIVE polls (10 answers, 1 h–32 d, multi-select, live bars) are the free voting surface and discord.py 2.7.1 + our intents already support them; the paid features everywhere are the wrapper (scheduling, recurrence, reminders, history, export, dashboard) which Black Bloc already has patterns for; typed answers are affordable via 2.7.1's modal CheckboxGroup/RadioGroup except DATES (no picker anywhere in Discord → generated slots). Test-mode gap: `poll.end()` and interaction-response sends bypass the guard — the cog must check by hand. Build = two slices (9a native ~250–350k, 9b wrapper ~200–300k). ⏸ **15 owner decisions in §7, to be asked one at a time; first: answer types in v1.** Status: **all 15 decisions taken 12:16 (see the decisions entry below); design doc + build after Phase 9 lands.**
- **Owner 2026-08-27 ~10:49, verbatim: "also in that poll let them set a data type for the box so if they pick date or checkbox etc it changes how the poll functions"** → poll creation has a per-poll (or per-option) answer TYPE that changes the mechanics: choice (single), checkbox (multi-select), date / date-range (availability, When2meet-style), free text, number / rating scale, yes-no. Native Discord polls only cover choice + multi-select; the other types need Black Bloc's own buttons/modals/select menus. Folded into the F15 research + design. Status: **relayed to the research agent.**
- **Polls (F15) — owner decisions, 2026-08-27:** D1 answer types in v1 → **single choice, checkbox, yes/no, rating scale, date/availability** (free text, number, ranked = v2) — "Yes go with your rec" (~11:46). D2 who may create → **staff only** ("Staff only", ~11:53). D3 staff review before posting → **no by default, but a switch (`poll_review_mode` off/on) changeable from both `/poll settings` and the dashboard** ("Make polls need approval as no but should be editable in the bot and the ui", ~12:02). D4 default duration → **24 h**, per-poll override, 32 d ceiling ("24h", ~12:03). D5 anonymous votes → **the poll creator chooses per poll (anonymous on/off at creation)**; when on, the poll runs on Black Bloc's own panel (native polls expose voters) and the UI says so ("Let poll creator set if anonymous is allowed", ~12:04). D6 results visibility → **creator chooses per poll, default live**; "hide until close" forces the panel (native cannot hide) ("Also set by creator live by default", ~12:05). D7 channel → **the channel the command was run in**; `poll_channel_id` as the dashboard-create default ("Yes channel it was created in", ~12:06). D8 ping on open → **none by default; `poll_ping_role_id` setting + per-poll override** ("Yes your call", ~12:07). D9 reminder → **60 min before close, in the poll's channel, no ping; `poll_reminder_minutes`, 0 = off** ("Yes", ~12:08). D10 recurring polls in v1 → **yes, staff-only, daily/weekly/monthly** ("Yes", ~12:10). D11 weighted votes → **no** ("No", ~12:11). D12 reopen closed polls → **no** ("No", ~12:12). D13 auto-thread → **off by default, `poll_auto_thread` setting** ("Your call", ~12:13). D14 results retention + export → **after 365 days a poll is ARCHIVED, not deleted: the summary (question, options, totals, close date) is kept forever; per-vote rows may be dropped at archive time; archived polls sit in a collapsed "Archive" section on the dashboard with export still available; `poll_archive_days` default 365** ("Maybe not forever but like a year" then "Or we archive after a year but keep it", ~12:15). CSV export yes. D15 priority → **after the current phase; not urgent** ("Your call, it's not an urgent feature", ~12:16). **All 15 decided → design [`info/phase10-design.md`](info/phase10-design.md). Owner 13:37: "do polls" → 10a builder dispatched 13:38 off `6e08223`. **10a LANDED 2026-08-27** on branch `worktree-agent-aa83500e6aae1280f`, four commits `033e1c7` → `a0fe975` → `d3d1234` → `09d8654`: storage (schema 14, four tables), the pure module + ten settings keys, the cog (`/poll create|end|cancel|results|list|settings`, the review switch, the last-call + close + archive loop, the raw vote listeners) and the staff-gated API + contract + mock. `pytest -q` 1738 passed (1596 before), `ruff` clean, `check.mjs` 14 pages / 68 routes clean. ⚠️ **Not merged and nothing has run against Discord — no poll has ever been posted by this code.** ⚠️ **The `<t:…>`-in-an-answer-label question is STILL OPEN**: the library sends the label unescaped and the docs say nothing, so only a posted poll can settle it — 10b must post one in the test channel first. **10b still to do:** the panel surface (anonymous, hide-until-close, > 10 date slots, free text / number), recurrence, `POST /api/polls`, the dashboard tab (`polls.html` + `page-polls.js` + the nav entry) and the pager scroll-to-top from the 14:01 ask.**
- **Polls status 14:47:** **10a LIVE in `3eb7e4f`** (1738 tests, schema 14, 32 commands synced; no poll posted yet — owner sweep: `/poll create` each kind in the test channel, vote, `/poll end`, results embed). **10b dispatched 14:47 off `3eb7e4f`** (panel surface, date kind, recurring, `POST /api/polls` + dashboard tab, pager scroll-to-top). ⚠️ open: `<t:…>` inside a native answer label — 10b posts one test poll (message id in its report) for the owner to look at; `poll_date_labels` setting flips the label style either way.
- **Owner 2026-08-27 ~14:01, verbatim: "for each page that has pagination make sure on hitting next page it scrolls back to the top of the list"** → every pager (Moderation cases, Members, Audit, Health last-50 if paged, Modmail tickets, Role menus Requests/Timed roles, Birthdays by month if paged, Polls in 10b) scrolls the table/list top edge into view (`scrollIntoView({block: "start"})` on the table-block, minus the top bar height) after Previous/Next/page change, once the new rows have rendered; one shared helper in `ui.js` (the pager component) so every page gets it. Status: **queued into the 10b site build (10a owns no pages; 10b owns `site/`).**

**Landed as Phase 10** (`info/phase10-design.md`; design from `info/polls-research.md` + the 15 owner decisions taken one at a time): 10a merge `3eb7e4f` (storage schema 14, `black_bloc/polls.py`, the cog, the 5-min loop, raw vote listeners, review switch, results history, archive job, API; Opus ~391k, +142 tests) deployed 14:45; 10b merge `ebf99a2` (panel surface for anonymous / hide-until-close / date slots > 10, `kind:date` with generated slots, `/poll recur` daily/weekly/monthly, `POST /api/polls` + the **Polls** tab as the 15th page with create form / open / pending / closed / archive / recurring / CSV export, and the shared pager scroll-to-top from the 14:01 ask; Opus ~513k, +81 tests) deployed 15:44. `main` 1819 tests + ruff green; `check.mjs` 15 pages / 72 routes; 32 commands synced. **Measured:** discord.py 2.7.1 dispatches only the RAW poll-vote events reliably (non-raw need a cached message) — the cog listens raw only; the `guild_polls`/`dm_polls` intents were already on; the API stores `<t:…>` inside an answer label unescaped (test poll message `1542651824950218792` in the test channel) — **whether the client renders it is still for the owner's eyes**, so date labels default to plain text with `poll_date_labels` to flip; `RadioGroup`/`CheckboxGroup` cap at 10 options (a `Select` carries longer lists). Eleven `poll_*` settings; `poll_mode` on by default (no shadow: a poll punishes nobody); test-mode enforced by hand at every acting site because `poll.end()` and interaction responses bypass the patched send. Deviations recorded in code-notes: recurrence reuses `schedule_id` (no schema bump), `polls.auto_thread` per poll, cancelled→archived allowed, panel bars divide by distinct voters, anonymous votes stored as a per-poll truncated SHA-256 (**KI-9**). One shared CSS fix on the way: `.field > .seg { justify-self: start }` (segments had been stretching since 9b, visible on Role menus' Approval field). **NOT verified live:** no poll created by a person, no vote cast on either surface, no reminder/close/recurrence fired against Discord, no client render of the timestamp label seen, CSV never saved by a click. Owner sweep: `/poll create` each kind in the test channel; look at the test poll's first answer (renders as a date or as literal `<t:…>`?) and say which; vote; `/poll end`; results embed; dashboard Polls tab.

## 2026-08-27 — Owner verified live: @-mention replies and the go-live card

Owner, 13:59, verbatim: "we've tested @ing the bot, we tested golive we've not tested rolemenu yet". Supersedes the NOT-verified-live caveats in the entries "Black Bloc answers when @-mentioned" and "Go-live announcement is a card" above — both exercised in the real server by the owner. Still unverified live: Phase 9 role approval / timed roles / reconciliation (owner sweep pending), temp-voice panel in the voice chat, YouTube presence, daily import beyond the log line.

## 2026-08-27 — Two questions answered: no other bot imports to cron; the Live role already exists

Moved whole from `TODO.md`:

- **Owner 2026-08-27 ~09:53, verbatim: "are there any imports or stuff we're gathering from other bots as commands that we can turn into crons?"** → survey of every command that imports/gathers; answer in chat, decisions one at a time.
- **Owner 2026-08-27 ~11:24, verbatim: "also as a side feature lets add a way to dynamically assign a role like streaming when live (keep off for noww)"** → ALREADY BUILT in Phase 2: `golive_live_role_id` (F2 "optional *Live* role") — the bot adds the role when a session opens and removes it when the stream ends; it is off whenever the setting is unset (it is unset in production today). No build needed; stays off until the owner points the setting at a role. Status: **answered; nothing to do.**

**Answered, nothing to build.** (1) Imports/gathering from other bots as commands → only `/birthday import` existed (now a daily loop, see the entry above); the seven loops already cover Twitch polling, birthdays, events, presence, panels, visibility; setup/repair commands stay manual on purpose (a cron would fight the owner's deliberate deletions); F2's "scan for inactive streamers" is the one future cron-shaped item, still TBD. (2) A dynamic "streaming" role while live already exists from Phase 2 — `golive_live_role_id`, unset in production, so off exactly as asked; point it at a role in Settings to turn it on.

## 2026-08-27 — Go-live wording section owns the stream-end mode

Moved whole from `TODO.md`:

- **Follow-up found by the stream-end builder (12:39):** `site/public/assets/page-golive.js:140` previews the "once the stream ends" wording unconditionally; with `golive_end_mode` now off by default it previews an edit that will not happen. Fix: read `golive_end_mode` and show the preview only in `edit` (with a one-line "stream-end edit is off" note otherwise); `/golive status` should also print the end mode. Status: **Opus builder dispatched 13:19 off `271b42a`.**

**Landed:** merge `6e08223` (builder commits `607d268`, `2e4f58f`; Opus ~162k). `main` 1596 tests + ruff green; `check.mjs` 14 pages / 61 routes. Deployed 13:33 Phoenix by Claude (`deploys.log`); `/health` ok. The Go-live page's Announcement wording section now owns `golive_end_mode` as a segment beside "Playing a game": in `edit` the ended preview renders, in `off` one honest sentence replaces it; a missing key renders neither (checklist 10); the key is omitted from that page's accordion (one home per page) and stays on global Settings. `/golive status` prints `**stream end** — off (left as posted)` / `edit ("…")`, echoing the stored value rather than assuming. Mock gained the key and mirrors `NOT_A_FEATURE`. **NOT verified live:** the status line has not been read in a real ephemeral reply; browser check was mock-only, Chrome, Discord dark.

## 2026-08-27 — Phase 9: approval-gated role menus, timed roles, reconciliation (bot + dashboard)

Moved whole from `TODO.md`:

- **Owner 2026-08-27 ~11:12, verbatim: "todo: certain roles menus like runner-status we want to have be on approval basis, so you select a role and it pings a mod to approve it"** → role menus gain a per-menu (or per-option) **approval** mode: picking the role creates a pending request, pings the staff/approver role in the staff channel with Approve / Deny buttons (same shape as the events review queue), the member is told the outcome, the grant is logged; dashboard shows pending requests. Depends on role menus being switched back on (`rolemenu_mode` is off). Status 12:27: **9a LIVE in `a46b7ff`** (merge `e792bfa`; 1441 tests on the branch, 1565 on main; schema 13; `/rolemenu edit`, `/role grant`, `/role extend`, hourly `_expiry` loop, `on_member_update` reconciliation; withdraw = pick the pending role again). **9b pending** (dashboard: editor fields incl. per-menu channel, Requests + Timed roles sections, Members chip expiry, contract routes) — dispatch when the site polish builder lands. Owner sweep: make `runner-status` approval-gated with 7-day expiry via `/rolemenu edit`, pick it, approve, watch the DM; bot needs View Audit Log for the by-hand actor.
- **Owner 2026-08-27 ~11:16, verbatim: "we also need a recolciliation step so if someone is manually given a role it reflects on our portal and the bot knows"** → role reconciliation: (a) `on_member_update` listener records role adds/removes made by hand (audit-log actor when readable) into the role-menu/pick store and the action log; (b) a periodic sweep (hourly) diffs live guild roles against what the bot believes for every menu-managed role and fixes the record, never the member; (c) the Members page and Role menus page read the reconciled truth. Pairs with the 11:12 approval-mode ask — one role-menu design note covers both. Note: the Members tab already shows LIVE roles from the gateway cache, so manual grants are visible there today; the gap is the bot's own records. Status: **LIVE in `a46b7ff` (9a); dashboard view in 9b.**
- **Owner 2026-08-27 ~11:24, verbatim: "we also need a way for certain roles to be time limited. the same runner status roles. so we can set someone to have it for a week."** → time-limited role grants: a per-menu default duration (`expires_after` on the menu, e.g. 7 d) that staff can override when approving (and a `/role grant @user @role 7d`-style staff command + dashboard field); a `role_grants` table (member, role, granted_by, granted_at, expires_at, source: menu/approval/manual/staff); an hourly sweep removes expired roles, DMs the member, logs `role.expired`; extend/renew from the dashboard; the Members page shows "expires in N d" on the chip. Ties into the reconciliation ask (a manual grant of a timed role gets a record with no expiry unless staff set one). Status: **LIVE in `a46b7ff` (9a); dashboard Extend/End in 9b.**
- **Owner 2026-08-27 ~11:30, verbatim: "also in that same editor menu we need to be able to change which channels theyre posting in"** → the Role menus editor gets a per-menu **Channel** picker (the menu row already stores `channel_id`, set today only by `/rolemenu post`); saving a different channel on a posted menu takes the old panel down and posts it in the new channel (reuse `rolemenu_panels` reconcile), and the Post card shows the channel it will use. Status: **deferred to Phase 9b (the 9a builder is editing the role-menu files now).**
- **Role-menu approval — decisions (owner, 2026-08-27):** Q1 approval granularity → **"per menu"** (~11:20). Q2 who approves / where → **any staff role approves; requests post in a channel set by a NEW setting `rolemenu_approval_channel_id` (default = `staff_channel_id`), Approve/Deny buttons, optional ping role `rolemenu_approver_role_id` (default none)** — owner: "yes that works, just make sure we can set the channel where they post later in settings" (~11:22). Q3 pending experience → **ephemeral "Sent to staff for approval — you'll get a DM when it's decided", option shows as pending, pick again to withdraw, approve = role + DM, deny = DM with reason** (owner: "yes your choice is good", ~11:40). Q4 denial cooldown → **7 days per menu (setting), denial DM says when they can retry, staff can grant by hand any time** (owner: "yes go with suggested", ~11:41). **All four decided → design note `info/phase9-design.md`, then build.**

**Landed as Phase 9** (`info/phase9-design.md`): 9a merge `e792bfa` (bot, storage schema 13, API; Opus ~366k) deployed 12:26 in `a46b7ff`; 9b merge `271b42a` (dashboard; Opus ~416k) deployed 13:17. `main` 1592 tests + ruff green; `check.mjs` 14 pages / 61 routes. Both deploys by Claude under the owner's authorisation (`deploys.log`); `/health` ok; migration `added role_menus.retry_days` seen in the Fly logs; panels re-registered on boot. **What shipped:** per-menu `approval` / `expires_days` / `retry_days` (via `/rolemenu edit` and the dashboard editor), request cards with persistent Approve/Deny in `rolemenu_approval_channel_id` (default staff channel) + optional `rolemenu_approver_role_id` ping, pending/withdraw (pick again)/DM-on-decision, 7-day retry refusal sentence, `role_grants` for every bot-made grant with expiry, `/role grant|extend`, hourly `_expiry` loop (Health tab), `on_member_update` reconciliation (`role.changed_by_hand` with the audit-log actor when `View Audit Log` is granted) + hourly record sweep that never touches members; dashboard Requests (pending first, decided collapsed) + Timed roles (Extend / End now / Grant form) sections, sidebar pending count, per-menu **Channel** picker that moves a posted panel (`PUT /api/rolemenus/{name}` accepts `channel_id`), Members chips show "· N d" from `roles[].expires_at`. Two 9a design deviations recorded in code-notes: withdraw = pick the pending role again (a shared select cannot show per-member selection); decide-then-add ordering with `role.approve_failed` + no grant row if Discord refuses. Settings-store merge conflicts (keys added by parallel builds) resolved keep-both twice; `site.css` conflict (the level-field grid written twice) resolved for `main`'s measured version. **NOT verified live:** no request card, button press, DM, expiry or panel move has happened in the real server; the by-hand actor needs **View Audit Log** on the Bots role (unchecked); audit rows B5–B7 (un-post / seed / staff assign) remain open. Owner sweep: `/rolemenu edit runner-status approval:on expires_days:7` → pick → Approve (Discord or dashboard) → DM → `/role extend` → Members chip.

## 2026-08-27 — Stream-end edit is a setting, off by default

Moved whole from `TODO.md`:

- **Owner 2026-08-27 ~12:30, verbatim: "Let's have stream end announcement by optional and off by default"** → new setting `golive_end_mode` (off / edit), default **off**: when off the original announcement (sentence + card) is left untouched when the stream ends (the session still closes, the Live role still comes off); when `edit`, today's behaviour (suffix + "was live" card). Status 12:40: **merged `e5d890e`, deploying** — `golive_end_mode` off/edit default off; session still closes and the Live role still comes off; `api/status.py` excludes it from the feature-mode list (it names no feature).

**Landed:** merge `e5d890e` (builder commit `7e46a81`, Opus ~140k). `main` 1573 tests + ruff green. Deployed 12:42 Phoenix by Claude (`deploys.log`); `/health` ok. `golive_end_mode` enum off/edit, default **off**: at stream end the session still closes, the Live role still comes off and `golive.end` logs `"announcement": "left"`; nothing is fetched or edited unless the mode is `edit` (then byte-identical to before). Both end paths (`_end_live` and the reconcile/age-out `_close_session`) go through the one gate. Side fix: `api/status.py:mode_keys()` now excludes `golive_end_mode` (it names no feature) so the Overview would not grow a bogus "Golive_end" row. **Live behaviour change:** every guild gets the new default — set `golive_end_mode = edit` to get the old marking back. **NOT verified live** (no stream ended since deploy). Follow-up queued: the Go-live page previews the ended wording regardless of the mode (`page-golive.js:140`), and `/golive status` does not print the mode.

## 2026-08-27 — Site polish: neon Cyberpunk, sidebar headers read as headers, every field group level

Moved whole from `TODO.md`:

- **Owner 2026-08-27 ~11:08, verbatim: "the theme needs more neon blue and othe neon colors"** → assumed = the **Cyberpunk** theme (the one the owner was viewing; Discord stays the approved mock). Palette pass on `:root[data-theme="cyberpunk"]` (dark + light) in `estate-theme.css`: neon blue as the primary accent, a second/third neon (magenta, green) on ok/warn/info/pills/nav-active/focus ring, glow via `--et-focus-ring`/`--et-card-shadow`, keep contrast readable. Status: **site polish builder dispatched 11:59 (item 1).**
- **Owner 2026-08-27 ~11:27, verbatim: "for the headers on the left side on the webite, its hard to tell which ones are header and which are clickable. make the headers bigger and maybe bold"** → sidebar group headers (OVERVIEW / MODERATION / COMMUNITY / SERVER / ON THIS PAGE): bigger (body size rather than micro), bold, higher-contrast colour, more space above; clickable items stay as they are so the two read differently at a glance. Token-only (`--et-nav-head-size/-weight/-color`) so every theme follows; Discord theme deviates from the mock here ON PURPOSE (owner call). Status: **site polish builder dispatched 11:59 (item 2).**
- **Owner 2026-08-27 ~11:29, verbatim: "the editting a menu page on the website on the rolemenu has offset boxes, name, title, desc mode are not level"** → Role menus page, "New menu / Editing X" editor (`page-rolemenus.js` `editor`): the Name / Title / Description / Mode fields sit at different heights — align them on one grid row (labels above, controls level; the textarea gets the same top edge; wrap to two rows at phone width). Status: **deferred to Phase 9b (the 9a builder is editing the role-menu files now).**
- **Owner 2026-08-27 ~11:44, verbatim: "go ahead and make sure every set of text boxes that are next to each other are all level, it seems to be around when there are subtext beneath or above the box that pushes the default offline"** → site-wide: every side-by-side field group (`.field-row` / form grids in `ui.js` `field()` and the page-level forms — Role menus editor, Birthdays set form, Moderation action form, Modmail snippets/blocks, Events settings, Go-live link form) uses one shared layout: CSS grid with `grid-template-rows: auto auto auto` (label / control / help) and `align-items: start` (or subgrid where supported), so a field with help text above or below no longer pushes its control off the line of its neighbours; the control row is what aligns. Token-only. Add a mock-server check page or a test that renders each form and asserts the controls share a top edge. Supersedes the 11:29 role-menu-editor item (that becomes one instance). Status: **site polish builder dispatched 11:59 (item 3).**

**Landed:** merge `c176cd2` (builder commits `b936b96` neon, `8424c60` nav heads, `6b7ab62` level fields; Opus ~243k). `main` 1565 tests + ruff green; `check.mjs` 14 pages / 54 routes. Deployed 12:33 Phoenix by Claude (`deploys.log`); `/health` ok; Fable eyeballed Moderation + Role menus in Cyberpunk on the mock before merging. **Measured:** Cyberpunk changes confined to its two theme blocks (18 hunks between old lines 718–858) + one cyberpunk-scoped wordmark rule; contrast table in `info/code-notes.md` § "site polish" — every text role ≥ 4.5:1 in both modes, every light-mode figure better than before; accent `#3d8bff`, headings `#ff3df0`, ok `#2bff88`, yellow kept only for warn, old cyan became info. Nav heads: four new tokens at all 13 sites, each theme's head one size step above its nav item, bold. Field alignment: 19 → 28 groups measured, misaligned 12 → **0** (worst had been the Role menus editor at 40 px and modmail at 92 px); root cause `.formrow { align-items: flex-end }`; fixed at the shared `field()`/formrow grid (subgrid + explicit-rows fallback), plus the UA checkbox margin and one `.bar` offset. **NOT verified live:** only Chrome; four of twelve theme×mode pairs by eye (the rest by computed style); no label-wrap case provoked; contrast computed from hexes, not sampled pixels.

## 2026-08-27 — Stream-ended wording setting, no prefix-command noise, dark-skin emoji

Moved whole from `TODO.md`:

- **Owner 2026-08-27 ~11:53, verbatim: "Make black bloc use dark skin emotes"** → every human-gesture emoji the bot sends (wave, thumbs up, clap, raised hands, flex, pray, point, ok-hand, and people emoji) carries a skin-tone modifier — default **dark 🏿** (`U+1F3FF`), with `emoji_skin_tone` setting (none / medium-light … dark) so it can be tuned; one helper `black_bloc/emoji.py` (`toned("👋")`) used by chat lines, birthday/event/go-live/modmail copy and embeds; non-human emoji untouched. Sweep = grep every emoji literal in `black_bloc/**`. Status: **bot batch builder dispatched 11:59 (item 3).**
- **Noise in the logs (found 11:49):** `discord.ext.commands.errors.CommandNotFound: Command "hi" is not found` at 18:40:55Z — `commands.Bot` treats "@Black Bloc hi" as a prefix-command attempt (mention prefix) and logs the miss; the chat cog answers via `on_message` regardless. Fix: an `on_command_error` that swallows `CommandNotFound`, or a prefix that can never match. Status: **bot batch builder dispatched 11:59 (item 2).**

**Landed:** merge `a46b7ff` (builder commits `853aee3`, `ec7b345`, `046a54a`; Opus ~170k). `main` 1565 tests + ruff green. Deployed 12:26 Phoenix by Claude together with Phase 9a (`deploys.log`); verified: 31 commands synced, logged in 19:26:26Z, `/health` ok. (1) `golive.py:ended_text`/footer read `golive_end_suffix` — the key added by the site follow-up now has one home. (2) The "hi" noise: measured root cause — `command_prefix` was `when_mentioned_or("!")` with zero prefix commands in the tree, so every mention became a `CommandNotFound`; now `black_bloc/prefix.py:no_prefix_commands` returns `[]` and `get_context` never dispatches (`discord/ext/commands/bot.py:1319` `startswith(())` is False); reproduced both ways in tests; `settings.command_prefix` kept because modmail reads it to ignore other bots' commands. (3) Emoji: `black_bloc/emoji.py` (`SKIN_TONES`, `toned`, `toned_text`, `tone_for`, Unicode `Emoji_Modifier_Base` set) + `emoji_skin_tone` setting default **dark**; census of 47 literals found exactly ONE tone-capable output emoji (👋 in `chat.py`) — hearts, status glyphs, arrows and the user-configured role-menu emoji take no modifier by design; every chat reply passes through `toned_text` at send time so future lines get it for free. **NOT verified live:** no toned emoji seen in Discord yet (owner check = `@Black Bloc hi` → a 👋🏿 line eventually); button-label tone support is inferred from `PartialEmoji.from_str` round-tripping, not measured against the API; the modifier-base list was transcribed, not generated.

## 2026-08-27 — Dashboard: controls instead of displays, cache-busted assets, avatars, one sign-in check

Moved whole from `TODO.md`:

- **Owner 2026-08-27 ~10:31, verbatim: "on the website, in the go-live area, can we update the annoucement wording to be a changable text field instead of just a display. also audit all the ssite features. we dont want any displays showing what the bot can do, we want ways to interact and change."** → (1) Go-live page: the announcement template becomes an editable field (writes `golive_template` through the settings store, with the preview kept beside it); (2) audit of all 13 pages: every read-only "what the bot can do" panel becomes a control or goes. Audit landed → `info/site-feature-audit.md`. Status: **site follow-up builder dispatched 11:03 (items 3, 5, 8–12).**
- **Owner 2026-08-27 ~10:37, verbatim: "https://blackbloc.heygabi.ai/birthdays.html on this page make month day year all on the same line"** → the set-a-birthday form's month / day / year controls sit in one row. Status: **site follow-up builder dispatched 11:03 (item 6).**
- **Owner 2026-08-27 ~10:39, verbatim: "also every new page refresh is giving me the message, checking to see if oyure logged in, thats too much. it should happen on itial page load only"** → cache the last successful `/api/auth/me` result in `sessionStorage` (user, staff flag, checked-at); on later page loads render straight from the cache and re-verify silently in the background, showing the "checking" state only when there is no cache or the silent re-check fails (then the existing signed-out / not-staff gates take over). Never trust the cache for writes — the server still gates every call. Where: the gate text "Asking the bot whether you are signed in." (`site/public/*.html` `#gate-message`) shown until `app.js:158` `/api/auth/me` resolves. Status: **site follow-up builder dispatched 11:03.**
- **Owner 2026-08-27 ~10:41 asked what "Creator / tempvoice_creator_ids" is on the Temp voice page** → it is the list of join-to-create voice channels (the "join" lobby); the label "Creator" is unclear. Fix: human label "Join-to-create channels" with the help line "Join one of these and Black Bloc makes you your own channel" (`settings_store.py:181` help + the site label map). Status: **site follow-up builder dispatched 11:03.**
- **Owner 2026-08-27 ~10:46, verbatim: "do we even need the creator section? i dont get its usecase so lets rm it unless oyu can say why we need it"** → decision put to the owner (one question): the setting itself must exist (it is how the bot knows which voice channel is the lobby) but the dashboard section can go, with the lobby shown as one line on the Set-up card. Supersedes the 10:41 relabel note. **Owner 2026-08-27 ~10:52: "rm it."** → the Creator / `tempvoice_creator_ids` section comes off the Temp voice page; the Set-up card shows one line "Lobby: #join" with Set up / repair and Forget beside it. The setting itself stays (the bot needs it). Status: **site follow-up builder dispatched 11:03 (item 7).**
- **Found live 11:02 (Members page after the 188acf3 deploy):** (1) returning browsers rendered the page with a STALE cached `site.css` (name/username and role chips ran together, stat strip wrapped) — a hard reload fixed it: assets carry no `Cache-Control` and no version in their URLs, so every deploy shows old CSS/JS to anyone who visited before; fix = `?v=<build id>` on every asset URL + `Cache-Control: no-cache` (ETag revalidation) on `/assets`. (2) avatars are broken images: CSP `img-src 'self' data:` (`api/server.py:32`) blocks `cdn.discordapp.com`; fix = allow `https://cdn.discordapp.com https://media.discordapp.net` AND fall back to the initial letter on `img` error. Status: **site follow-up builder dispatched 11:03 (items 1–2).**
- **Site feature audit LANDED 10:50** → [`info/site-feature-audit.md`](info/site-feature-audit.md). 🔴 Found a live bug: Automod page Mode + Exemptions sections render `[object Object]` and save nothing (`page-automod.js:95,119`). The site follow-up build brief = audit A1–A8, B1–B3, B9, C1–C4, prose cuts + the queued asks (Birthdays one-line date, sign-in cache, Creator section per owner answer). B4–B8 held for a later batch.
- **Owner 2026-08-27 ~11:06, verbatim: "move the go live template from setting to the annoucement wording tab and let that be editable"** → same as the 10:31 ask; = site follow-up item 5 (audit A1 + C2): `golive_template` editor lives in "Announcement wording" with the live preview, and the row is REMOVED from the Go-live page's Settings accordion (it stays on the global Settings page). Status: **in the builder dispatched 11:03; reiterated to it.**

**Landed:** merge `a28e132` (twelve builder commits `adfb5e7`→`dab62c8`, one per item, Opus ~463k — the largest dispatch of the project; conflict in `cogs/core.py`/`tests/cogs/test_core.py` resolved by keeping `main`'s `/settings set-value` autocomplete from `8b8f792`). `main` 1425 tests + ruff green; `check.mjs` 14 pages / 54 routes. Deployed 11:55 Phoenix by Claude (`deploys.log`). **Verified live:** every asset URL carries `?v=<version>-<hash>`, assets `Cache-Control: no-cache`, HTML `no-store`, CSP `img-src` allows Discord's CDN, `/health` ok, logged in 18:56:12Z. Build id = package version + sha256 of `site/public` (not a git sha — the container has none); `?v=` cannot reach ES-module imports so `no-cache` is the real fix and the stamp the belt. Sign-in: `sessionStorage` cache, display only, server still gates every call; warm load never shows the gate (measured in the mock: `/api/auth/me` moved from first to last request). Go-live wording: textarea editor + live preview (ping role, `{platform}`, empty-game word, literal unknown tokens), omitted from that page's accordion, kept on global Settings; `golive_end_suffix` key added but `golive.py:ended_text` does NOT read it yet (next bot batch). Creator section gone; `Lobby: #… [Forget]` line via new `POST /api/tempvoice/forget` sharing `forget_creator` with the slash command (a shadowed `FORGOTTEN` constant found and renamed on the way). Audit rows A1–A8, B1–B3, B9, C1–C4 and the §4 prose cuts marked "Done in <commit>" in `info/site-feature-audit.md`; **still open there: B4** (temp-voice per-room actions, refactor first), **B5–B7** (role-menu un-post / seed / staff assign — 9b territory), **B8** (event detail/edit). **NOT verified live:** an avatar actually loading from the CDN in the browser; the gate behaviour in the real site (mock only); one Fly proxy `PU03 unreachable worker host` on `/assets/site.css` at 18:56:35Z during the restart — three follow-up fetches returned 200.

## 2026-08-27 — Black Bloc answers when @-mentioned (F10 step 1: canned intents)

Moved whole from `TODO.md`:

- **Owner 2026-08-27 ~11:33, verbatim: "we need to also add basic conversation and replies to the bot when people @ it and say hi, we can set up true covnersation"** → F10 step 1: an `@Black Bloc …` mention handler with a small intent table (greeting / thanks / how-are-you / what-can-you-do / help / unknown) and several canned lines per intent in the bot's voice, randomised, replying in-channel (guard: test channel + DMs only under TEST_MODE), per-user cooldown, `chat_mode` off/on setting (default **on** in test), logged as `chat.reply`; the handler is a single `respond(text, member) -> str | None` seam so a real conversation backend (LLM) can replace the intent table later without touching the cog. Note: message content for messages that @mention the bot arrives WITHOUT the privileged Message Content intent (builder to verify from discord.py 2.7.1). Status: **Opus builder dispatched 11:34.**

**Landed:** merge `1899f6e` (builder commits `047f48d`, `e0aa2d6`; Opus ~156k). `main` 1389 tests + ruff green. Deployed 11:48 Phoenix by Claude (`deploys.log`); verified: `loaded cog black_bloc.cogs.content.chat`, logged in 18:48:37Z. Shape: `black_bloc/chat.py` (pure: `classify`, `respond`, the `reply_for` seam for a future conversation backend) + `cogs/content/chat.py` (`on_message`: ignores bots/webhooks, needs the bot's mention, `chat_mode` on/off default on, guard checked first at debug level, per-user `chat_cooldown_seconds` default 20 stamped only after a reply lands, `reply(mention_author=False, allowed_mentions=none)`; only `insult` writes an action row `chat.insult`). Measured: a message that @mentions the bot carries `content` without the privileged intent (`discord/flags.py:1256–1262`), though `intents.py:9` already enables it for automod. Voice = first draft, 5–6 lines per intent, one emoji max, `unknown` → `/help`. **NOT verified live:** no reply has been observed in a channel yet — owner check = `@Black Bloc hi` in the test channel. Follow-up noted in TODO: `CommandNotFound: Command "hi" is not found` logged at 18:40:55Z when the owner @mentioned the bot before this shipped — the prefix-command dispatcher still treats "@bot word" as a command attempt (noise only).

## 2026-08-27 — Go-live announcement is a card: streamer, game and the game's art, no avatar

Moved whole from `TODO.md`:

- **Owner 2026-08-27 ~10:50, verbatim (with a screenshot of another bot's go-live embed — streamcord: author line "PopNoTarts is now live on Twitch!" with avatar icon, stream title as a link, a "Game" field, the game's box art as the image): "can we make our go live message show the streamer name and the game they're playing instead of their avatar"** → replace the plain-sentence post (+ Discord's link preview of the streamer) with an embed: title "{name} is now live on {platform}!", the stream title linking to the stream, a **Game** field, and the game box art (Twitch Helix `games` endpoint → `box_art_url`; YouTube: the stream thumbnail if known, else no image); the `golive_template` sentence stays as the message text above the embed. Status: **Opus builder dispatched 10:54 off `74f06b5`** — text stays the template sentence; embed = "{name} is now live on {platform}!" author (no avatar), title→stream link, Game field, box art via Helix `games` (cached) or the activity thumbnail, platform colour, end-of-stream edit; `golive_embed` bool setting (default on).

**Landed:** merge `8b8f792` (four builder commits `6a38357`→`b00521c`, Opus ~203k, reviewed by Fable: `announcement_embed` sets no `icon_url`/thumbnail anywhere). `main` 1329 tests + ruff green. Deployed 11:14 Phoenix by Claude (`deploys.log`); verified: 30 commands synced, logged in 18:14:32Z, `/health` ok. The card: author "{name} is now live on {platform}!", stream title → link, **Game** field (never blank — `GAME_FALLBACK`), image = Helix `games` box art (cached; a Helix failure degrades to no image, never blocks the post) or the presence asset; Twitch purple / YouTube red; footer names the source; end-of-stream edits the card to "was live" + "· stream ended". `golive_embed` bool (default on) restores the old sentence-only post when off. Side effect that had to land: the 26th value-typed key hit Discord's 25-choice cap on `/settings set-value`, so that command's `key` is now autocomplete (`cogs/core.py`). **NOT verified live:** the card has never rendered in the real client; the `/helix/games` shape and the `twitch:`/`youtube:` presence-asset prefixes are from docs/inference — owner check = `/golive test` (Twitch, then YouTube) in the test channel, then one real stream. Code-notes: the new section names `74f06b5` as the base; five already-keyed files moved lines and were NOT re-keyed (next docs pass).

## 2026-08-27 — Batch 7: themes restyle everything · Members tab · YouTube go-live · temp-voice panel in the voice chat

Moved whole from `TODO.md` (four owner asks, all landed in `188acf3`, deployed 11:00 Phoenix by Claude under the owner's 10:25 standing authorisation — `deploys.log`):

- **Owner 2026-08-27 ~10:18, verbatim: "make sure that the other themes work and dont just change the background color, make sure it applies to all CSS"** → audit `site.css`/`shell.js`-drawn CSS for anything the five old themes cannot override (font faces, radii, shadows, borders, control heights); every such value must go through an `--et-*` token that each theme sets. Audit 10:20 (measured live, Cyberpunk + Retro): colours and the body face switch, but cards, pills, radii, borders and the whole type scale stay Discord's — `site.css` hardcodes 64 `font-size` px, `border-radius: 4px`, 1px borders, weights/tracking. Status: **Opus builder dispatched 10:23 (Part 1 of a two-part brief, same worktree as the Members ask): tokenise everything, Discord keeps the mock values, each old theme sets its own; pass = computed-style table shows ≥4 old themes differing on face/radius/size.**
- **Owner 2026-08-27 ~10:18, verbatim: "also show server users, server user count also somewhere in the moderation area."** → a member count + a members list in the MODERATION group of the dashboard (likely a Members page or a panel on Moderation: name, joined, roles, case count). Needs an API route (`/api/members`, paginated, staff-only, from the bot's member cache). Design settled 10:22: `GET /api/members` (staff-only, search/filter/sort/paginate, cases count grouped, staff from `resolved_staff_roles`), a **Members** page under MODERATION with stat strip + B-style table, sidebar count, and a fifth **Members** stat on Moderation linking to it. Status: **Opus builder dispatched 10:23 (Part 2 of the same brief).**
- **Owner 2026-08-27 ~10:34, verbatim: "we also need to get youtube going live stuff too, go let the streaming activity work for youtube"** → the Discord streaming-activity detector (`golive.py`) must treat a YouTube stream the same as Twitch (Discord's Streaming activity carries `platform`/`url`); announce with the YouTube link; F3 in the feature list moves from "maybe" to decided. Finding 10:36: presence path is already platform-agnostic, but `_enrich` Twitch-looks-up any stream when the member has a Twitch link (can overwrite YouTube data), no `{platform}` template field, `/golive test` is Twitch-only, sessions may not store the platform. Status 10:53: **merged to main (`git log -1`), pushed, 1266 tests green on the branch; DEPLOY PENDING — ships with the temp-voice panel change in one deploy; first live check = owner runs `/golive test platform:YouTube` in the test channel.** Limitation for the owner: works only when Discord itself shows "Streaming on YouTube" (YouTube connection + activity display on). Was: (enrich only Twitch, `{platform}` field, platform on sessions/status/API, test command choice; YouTube API fallback out of scope — presence only).
- **Owner 2026-08-27 ~10:44, verbatim: "also lets move the controls for the join to create from the #test channel into the channel txt of the voice chat that was made like the other bot does it"** → the temp-voice owner control panel posts into the created voice channel's own text chat (`VoiceChannel.send`) instead of `#mute-me-bot-test-spam`; the test-mode guard gets a NARROW allowance for channels Black Bloc itself created (rows in the tempvoice table), nothing wider — this is the owner scoping the test policy, recorded here verbatim. Finding 10:39: `panel_home` already prefers the voice chat and only falls back to the test channel because the guard refuses it. Status: **Opus builder dispatched 10:40** — in-memory `owned_channel_ids` allowance on the guard (rows in `tempvoice_channels` only), restore on boot, prune on delete, interactions allowed there, copy updated.

**Landed, measured:** merges `7534d26` (themes + Members, Opus ~367k), `74f06b5` (YouTube, ~174k), `188acf3` (temp-voice panel, ~212k); `main` 1292 tests + ruff green with the venv; `check.mjs` 14 pages / 49 routes at `7534d26`. Themes: 25 tokens added at all 13 declaration sites; computed-style table shows ALL five old themes differ from Discord on font-family, radius and type size, and Discord proved unchanged by a 55-selector × 21-property diff (`info/code-notes.md` § "site — theme tokens"). Members: `GET /api/members` (search/filter/sort/paginate, cases grouped, staff from `staff_role_ids`, bots never staff), 15 tests, two real bugs caught by tests (undated members sorted first; mock's 'new' joins were 9 days old). YouTube: presence path proven platform-agnostic; `_enrich` gated by `twitch_enrichable`; `{platform}` template field; `golive_sessions.platform` column (schema 11→12, additive); a title-less stream rendered `{title}` as the platform name — fixed. Temp voice: guard `owned_channel_ids` allowance (only rows in `tempvoice_channels`), `allows_place` deliberately NOT widened, slash commands there still refused; bot grants itself view/connect/manage on spawned channels (hidden-channel lockout fixed). **Verified live after deploy:** `/health` ok, bot logged in 18:00:25Z, daily import ran, no log errors, Members page rendered signed in. **NOT verified live (owner sweep):** `/golive test platform:YouTube`; a real YouTube presence (only works when Discord itself shows "Streaming on YouTube"); a temp-voice panel appearing in a new channel's chat and a button press there — the Bots role needs Send Messages in that voice channel or the log shows `tempvoice.panel_failed`; a restart restoring old panels.

## 2026-08-27 — The dashboard is Direction A ("Discord-native"): new default theme, grouped sidebar, docked save bar

Moved whole from `TODO.md`:

- **Owner 2026-08-27 ~09:32, verbatim: "Lets go with A, keep this exact same design and implement it but make sure our existing theme selectors work"** → Direction A ("Discord-native") is the site look. Build: a new default theme `discord` (dark + light palettes from `info/dashboard-inspiration.md` §A) beside the five existing themes, the shell rebuilt to the mock (grouped sidebar, top bar with the cog, B-style tables, docked save bar, grouped settings), all token-driven so the five old themes still switch. Reference: the mock artboards are copied to `info/mock-direction-a/` (local only). Status ~10:20: **merged to main as `a60796c` (+ `666dd8e` copy fix for the daily birthday import), 1248 tests + ruff green, pushed; reviewed by Fable against the mock on the builder's mock server (Overview/Moderation/Settings match). DEPLOY PENDING — owner runs it (classifier refuses `flyctl deploy` in-session). After deploy: verify live in the Discord theme + one old theme, then move this item whole to DONE.** Polish noted, not blocking: the "On this page" sub-nav shows raw group keys (`core`, `birthday`) in lowercase; multi-select boxes (exempt roles/channels) look cramped in the 218px control slot.

**Landed:** merge `a60796c` (five builder commits `3412e40`→`e96b988`, Opus in a worktree, ~433k tokens) + `666dd8e` (Birthdays page copy no longer names the removed `/birthday import`). 1248 tests + ruff green with the venv interpreter (a first run used the system Python and failed on `discord` — run `.venv/Scripts/python -m pytest`). Reviewed by Fable against the mock on the builder's mock server: Overview/Moderation/Settings match. Deployed by the owner via `!` at 10:20 Phoenix (`deploys.log`); **verified live** signed in as the owner in the Discord theme. Mock reference kept at `info/mock-direction-a/` (local only); canvas https://claude.ai/code/artifact/ad76df70-49f4-4fcd-a66a-07c8969d0ddd (Direction A front page, Cookout parked on page 2). Deviations recorded in `info/code-notes.md` § "site restyle — Direction A": no `moderation_mode` key exists so that sidebar item has no dot; feature sub-lines use real counts or a plain sentence; stat strip counts the loaded page. **Follow-ups spun out as their own TODO items (10:18):** the old themes only repaint colours/faces under the new shell (tokenisation build), and the Members page. Polish noted, not done: "On this page" shows raw group keys in lowercase; multi-selects cramped in the 218px control slot.

## 2026-08-27 — `/birthday import` is gone; the Birthday Bot list is imported on a daily loop

Moved whole from `TODO.md`:

- **Owner 2026-08-27 ~09:39, verbatim: "lets hide the birthday import command and just put it on a daily cron. make sure you follow the A design as closely as possible"** → (1) the birthday import slash command comes off the tree and the import runs on a daily loop; (2) reinforcement for the in-flight Direction A build (brief already says pixel-exact; relayed to the builder as a narrowing note). Status ~09:52: **landed on main as `1b751b9` and pushed; 1248 tests green; DEPLOY PENDING — the deploy command was refused by the session's permission classifier twice, owner runs it (`! flyctl deploy --app black-bloc --ha=false --remote-only --yes`), then verify `/api/status` lists `_import_loop` and append `docs/deploys.log`.** Design: `/birthday import` removed, `import_rows` on a 24 h loop that also fires at startup, action logged only when something was imported, loop visible on the Health tab. Site builder was sent the "as close to A as possible" note.

**Landed:** `1b751b9` (Opus builder in a worktree, reviewed by Fable, fast-forwarded to `main`, pushed). 1248 tests green, ruff clean. Deployed by the owner via `!` at 10:00 Phoenix because the session's permission classifier refused `flyctl deploy` twice (`deploys.log`). **Verified live** in the Fly logs at 16:59:51Z: `_import_loop` ran 4 s after login — imported 0 / already 38 / ambiguous 0 / not_found 1 — so the seed is fully absorbed and only the one unmatched name remains. Loop health is on the Health tab by discovery (`tests/api/test_status.py`). Explanations: `info/code-notes.md` § "birthdays — daily import loop"; `info/phase5-design.md` Import section carries the superseded banner. **Residual:** `site/public/assets/page-birthdays.js:84` still says "The same import `/birthday import` runs" — one-line copy fix folded into the Direction A site restyle item (that builder owns `site/`).

## 2026-08-27 — Turning role menus off takes the panels down; turning it on posts them again

Moved whole from `TODO.md`:

- **Batch 6 item 3 (queued behind item 2), owner verbatim 2026-08-27 ~08:30:
  "Panels get turned off when off, I'll get the ux now, save role menu seed"**
  → OVERTURNS the "panels stay posted" default: on `rolemenu_mode` → `off`,
  delete every posted panel message (guarded delete; log `role_menu.unposted`
  per menu, keep `channel_id` so re-posting lands in the same channel, clear
  `message_id`); on → `on`, re-post every menu that had a channel (same
  persistent views), log `role_menu.reposted`. Menu rows, options and the
  seed data are NEVER touched by the switch. Driven by the same store change
  hook as item 2 (one trigger path), debounced with it.

**What landed.** One commit on `main`, **not pushed, not deployed, never run
against a live bot.** 1243 tests pass (1221 before), ruff clean,
`site/mock/check.mjs` clean (13 pages, 48 routes).

- **`black_bloc/rolemenu_panels.py`** (new) — `reconcile(bot, reposting=…)`
  matches the posted panels to the stored mode, per guild. `off` → for every
  row with a `message_id`: guard check, delete the message, `message_id =
  NULL` (the `channel_id` stays), log `role_menu.unposted`. `on` → for every
  row with a `channel_id` and no `message_id`: guard check, `post_panel` (the
  same helper `/rolemenu post` and the web route use, so the same persistent
  view and the same `set_message`), log `role_menu.reposted`.
- **The guard is checked explicitly** because `guard.py` patches
  `send_message`/`edit_message`/`delete_channel` and **not** `delete_message`
  — a panel outside the test channel is refused and logged
  `role_menu.would_unpost` / `role_menu.would_repost` (checklist 1 and 2: a
  dry run and a failure never share a log kind).
- **One failure never aborts the sweep** — `discord.NotFound` means the panel
  was already deleted by hand and the row is simply forgotten; any other
  `HTTPException`, an unreachable channel, or an unexpected exception logs
  `role_menu.unpost_failed` / `role_menu.repost_failed` and the loop carries
  on to the next menu.
- **One coalesced run per flip** — the panel work is registered as a job on
  the **existing** `VisibilitySync` debounce (`controller(bot).also(job)`,
  run after the 5 s debounce and *before* the command sync, so panels are not
  held behind the 60 s sync rate limit). An `off → on → off` burst is one run
  and the last state wins, because `reconcile` reads the stored mode at run
  time rather than at flip time.
- **`on_ready` re-runs it one way only** (`panels_on_boot`): rows still
  holding a `message_id` while the mode is `off` come down, and nothing is
  ever posted at boot — a restart must not surprise the server with panels
  nobody asked for. It is also what arms the job (`PanelSync.ready`), so a
  cold channel cache in `setup_hook` cannot log failures for panels that are
  fine.
- **Menu rows, options and the seed are untouched** by the switch — asserted
  by a test that snapshots every menu and every option around an `off`/`on`
  round trip.
- **Wording** — the Role menus tab now says *"Turning this off removes the
  posted panels and hides the /rolemenu commands; turning it on re-posts every
  menu in its channel"*; `/rolemenu mode` and its `describe`, the
  `rolemenu_mode` registry help and the mock's copy of it all say the same.

**NOT verified:** any of it against a running bot — no panel message has ever
been deleted by this code, nothing has been re-posted, no guard has refused a
real delete, and the mode has never been flipped against live Discord.

## 2026-08-27 — The `/rolemenu` commands disappear while role menus are off

Owner ask, verbatim (~08:00): *"Can we suppress the / command for rolemenu too
toggle by ui"*.

**What landed.** One commit on `main`, **not pushed, not deployed, never run
against a live bot.** 1221 tests pass (1206 before), ruff clean.

- **`black_bloc/command_visibility.py`** — a registry, `HIDDEN_WHEN_OFF =
  {"rolemenu_mode": ("rolemenu",)}`, mapping a mode key to the top-level
  command names to hide while that mode is `off`. `apply_visibility(bot)`
  removes them from the **dev-guild copy** of the tree
  (`tree.remove_command(name, guild=…)`, keeping the returned object so the
  put-back is the same `Group` with its cog binding) or re-adds them
  (`tree.add_command(command, guild=…, override=True)`), then sends **one**
  `tree.sync(guild=…)`, debounced 5 s and never more than once per 60 s
  (KI-2). Nothing changed → no sync at all.
- **`/settings` can never be hidden** (`NEVER_HIDDEN`) — it is the way back:
  `/settings set-value rolemenu_mode on`, since `/rolemenu mode` is hidden
  along with the rest of the group.
- **One trigger path** — `SettingsStore.on_change(key, callback)` (new) fires
  on every `set` **and** `clear`, so `/rolemenu mode`, `/settings set-value`
  and `PUT /api/settings/{key}` all reach the same code. `bot.py:61` registers
  it and applies once at startup, right after the initial sync.
- **`/help`** filters the tree through the registry, because hiding touches the
  guild copy and the global command would otherwise still be listed.
- **`commands.visibility`** action-log row per sync: resulting command count,
  what is hidden, and the actor who changed the setting.
- **Wording** — the dashboard's Role menus tab says the switch also hides the
  commands; `/rolemenu mode` says so as it flips; the "role menus are turned
  off" sentence now points at `/settings set-value rolemenu_mode on` rather
  than at a command that is no longer there.
- **Tests** — `tests/test_command_visibility.py` (11, all offline): a fake tree
  recording remove/add/sync; off at startup → removed + exactly one sync; on →
  untouched, no sync; three flips through the store hook → one sync; the same
  command object comes back; `/settings` never removed; the rate-limit window
  waited out; another guild ignored; no dev guild → nothing; a refused sync
  leaves the window open. One of them drives the **real** `CommandTree` with
  the real cogs loaded and only `sync` faked, which is where discord.py 2.7.1's
  `remove_command`/`add_command`/`copy_global_to` semantics are actually
  exercised. Plus two store-hook tests and two `/help` tests.

**NOT verified:** anything against a running bot or Discord — no command has
ever been removed from a live tree, no sync has been sent, nobody has clicked
the dashboard switch and watched `/rolemenu` vanish. The 5 s / 60 s figures are
asserted in tests, not measured against Discord's real rate limit.

**Moved whole from `TODO.md` § Open engineering items:**

- **Batch 6 item 2 (queued behind item 1), owner verbatim 2026-08-27 ~08:00:
  "Can we suppress the / command for rolemenu too toggle by ui"** → command
  VISIBILITY tied to the mode: when `rolemenu_mode` is `off`, remove the
  `rolemenu` group from the tree and re-sync the dev guild (rate-limit aware:
  one sync per change, debounced); when `on`, re-add + sync. Applied at startup
  from the stored mode and on every change (web toggle or `/settings
  set-value rolemenu_mode on`, which stays visible as the slash-side way back).
  Generic: a `hidden_when_off` registry so other features can opt in later.
  Log `commands.visibility` with the resulting count; `/help` reflects it.

## 2026-08-27 — Role selection turned off, with a switch to turn it back on

Owner ask, verbatim (~07:50): *"let's turn off all role selection stuff but do
it in a way we can turn it back on with ui."*

**What landed.** One commit on `main`, **not pushed, not deployed, never run
against a live bot.** 1206 tests pass, ruff clean, `site/mock/check.mjs` reports
13 pages / 48 routes with every key present.

- **`rolemenu_mode`** — a new registry enum (`off`|`on`), **default `off`**,
  appended to `KEY_TYPES` so `mode_keys()` and the Overview chips pick it up
  with no change to either. Help: *"whether members can pick roles from the
  posted panels"*.
- **While off**, the self-serve select, the staff-assign select, `/rolemenu
  post`, `assign` and `unassign` all answer with one sentence and change no
  roles; `create`, `add`, `remove`, `show`, `showall`, `list`, `delete` and
  `seed-defaults` still work, so staff prepare menus while it is off.
- **`/rolemenu mode <off|on>`** (staff) flips it and logs `role_menu.mode`.
- **Web** — a first-section On/Off switch on the Role menus tab, reading
  `/api/settings` and writing `PUT /api/settings/rolemenu_mode`, repainting its
  chip from the stored value with no reload; the Overview chip for `rolemenu`
  now links to that tab. `POST /api/rolemenus/{name}/post` answers 409 with the
  same sentence while off, and the mock mirrors it.
- **Panels are LEFT POSTED** — the deliberate choice, so turning it back on is
  instant. Recorded in `info/code-notes.md` § "The off switch" and in the tab's
  own helper text.

**NOT verified:** anything against a running bot or the real API in a browser —
only pytest, ruff and the mock's contract check. Nobody has clicked the switch.

**Moved whole from `TODO.md` § Open engineering items:**

- **Batch 6 (dispatched 2026-08-27 ~07:55), owner verbatim: "let's turn off all
  role selection stuff but do it in a way we can turn it back on with ui"** →
  `rolemenu_mode` (`off|on`, default **off**): panels answer "turned off",
  `post/assign/unassign` refuse, CRUD still works, `/rolemenu mode`, an On/Off
  switch at the top of the dashboard's Role menus tab, Overview chip. Deliberate
  choice (overturnable): posted panels stay in place so turning back on is
  instant. Owner also asked "What's in batch 6" — it was empty until this item.

## 2026-08-27 — The Health tab finds every loop by itself (KI-7 closed)

**Supersedes the "finding worth keeping" in the presence entry below**, which
recorded the gap this closes.

**What landed.** One commit on `main`, **not pushed, not deployed, never run
against a live bot.** 1195 tests pass, ruff clean.

- **`black_bloc/api/status.py`** — new `_loops(cog)` walks each cog's class MRO
  dicts and its instance dict for `discord.ext.tasks.Loop` instances and
  `getattr`s only those names, then asks `cog.loop_health(<attribute name>)` for
  the health beside each one. `dir(cog)` is still never called, so the
  property-that-raises hazard the old note named is still avoided.
- **`black_bloc/cogs/presence.py`** — `get_tasks` **deleted**. It was ours, not
  discord.py's, it was the only one in the tree, and a declaration only one of
  six cogs remembered to write is exactly the second home the discovery reader
  removes.
- **No mapping table was needed.** Every cog's `loop_health` already accepted
  its own attribute name: `Presence.status`, `GoLive.poller`,
  `Birthdays._sweep`, `Events._golive_loop` / `._reconcile_loop` (which strips
  the `_` prefix and `_loop` suffix itself), `TempVoice._reconcile_loop`,
  `Modmail._reconcile_loop`. **Seven loops, six cogs**, up from one.
- **`site/` untouched.** The per-loop shape is unchanged (`cog`, `name`,
  `running`, `failed`, `state`, `next_iteration`, `last_ok_at`, `last_error`),
  so `page-health.js`, the mock and `site/mock/contract.json` needed no edit —
  including the honest "this loop does not record its last success yet" text a
  blank `last_ok_at` still renders.
- **Tests.** `tests/api/test_status.py` now builds **real** `tasks.Loop` objects
  (a duck-typed double would no longer be found, so the old fakes would have
  passed while describing an empty page), and a parametrised test builds each
  real cog with the fake bot and asserts every loop it owns comes back from
  `/api/status` with the `last_ok_at` that cog records. A cog that grows a loop
  is one row in that table.

**NOT verified:** any of it against a running bot — no loop has ever been
discovered off a live gateway connection, and nobody has loaded the Health tab
against the real API. The residual, accepted in `KNOWN_ISSUES.md`: discovery is
by TYPE, so a loop held where `getattr` cannot reach it (in a list or a dict)
stays invisible. Nothing in the tree does that today.

## 2026-08-27 — The bot's own face: the site link in its About Me, and a "Cookout attendees" status

**The two asks, verbatim (owner, 2026-08-27 ~06:35):** (1) *"we should put the
url for the site in the bio of the bot"*; (2) *"The status of the bot should be
'Cookout attendees' then the number of server members"*. They arrived as items
(1) and (2) of a three-ask block in `TODO.md`; ask (3), the dashboard UX pass,
is still open there.

**What landed.** One commit on `main`, **not pushed, not deployed, never run
against a live bot.** 1194 tests pass (1173 + 21), ruff clean.

- **`black_bloc/presence.py`** — the decisions, with almost no Discord in them:
  `status_text` (the `Cookout attendees: 412` sentence), `bio_text`,
  `human_count` (the guild's `member_count` minus the bots the cache can see),
  `status_guild` (the dev guild, else the first cached one), and the two
  appliers `update_status` and `ensure_bio`. Everything but the two appliers is
  pure and tested with no gateway.
- **`black_bloc/cogs/presence.py`** — the plumbing: the About Me written once
  per process on `on_ready`, the status re-applied on every `on_ready`, a
  10-minute `tasks.loop` with an `@loop.error` handler that restarts it, a
  5-second debounce on `on_member_join` / `on_member_remove`, and
  `/presence apply` (staff) to put both back by hand after a settings change.
- **Two registry keys**, both `text`: `bot_bio` (default renders the owner's
  sentence over `config.py`'s `site_origin`, so the hostname keeps one home)
  and `status_prefix` (default `Cookout attendees`). Both reachable from
  `/settings set-value` and from the dashboard's Settings page under **core**.
- **Health.** The cog reports `loop_health("status")` with `last_ok_at` /
  `last_error`, and defines `get_tasks()` so `api/status.py` can find the loop.

**The finding worth keeping.** `commands.Cog` in discord.py 2.7.1 has **no
`get_tasks` method** — verified at runtime (`hasattr(commands.Cog,
"get_tasks")` is `False`). `api/status.py:90` asks every cog for one, and none
of the five other loop-owning cogs defines it, so the dashboard's Health tab
currently lists **no loops at all**. The presence cog defines its own; the rest
are an open gap, not a fixed contract.

**Verified:** `AppInfo.edit(description=…)` exists in the installed library
(`.venv/Lib/site-packages/discord/appinfo.py:299`, `description` at `:304`,
added in 2.4), and `discord.CustomActivity` is there
(`discord/activity.py:760`). `change_presence` is a gateway op, so `guard.py`
neither sees nor needs to gate it — a status is not a channel, and it is
allowed to run in test mode.

**NOT verified:** any of it against a running bot. No About Me has ever been
edited by this code, no custom status ever set, `AppInfo.edit` has never been
called for real, and the 400-character description / 128-character status
limits are read off Discord's documentation rather than measured.

## 2026-08-27 — The Phase 8b security review's nine findings, fixed in two commits

**What:** two commits on `main` over `6b75c11`. **Not pushed, not deployed,
never run against a live bot.** 1178 tests pass (1134 + 44), ruff clean, and
`node site/mock/check.mjs` reports 13 pages / 49 routes with `MOCK_TEST_MODE`
at its **default** — which it could not do before.

**`5da62b3` — the three deploy blockers.**

- **CSRF (HIGH).** There was no Origin check at all: `SameSite=lax` does not
  stop a top-level form POST, so any other site could `<form method="post">` at
  `/api/mod/ban` and the browser would attach the session cookie. A middleware
  registered first (so it runs innermost, and its own refusal still picks up the
  security headers and the access log) now requires `Sec-Fetch-Site:
  same-origin` **or** an exact `Origin` match on every non-GET/HEAD/OPTIONS
  request under `/api`, **logout included, nothing exempt** — 403 `cross_site`
  with a sentence. It also requires `Content-Type: application/json` whenever
  there is a body (415 `not_json`), so a simple form POST cannot reach a handler
  even if the origin check were ever weakened; a bodyless request (logout, every
  `DELETE`) needs none, which is what `api.js` sends.
- **Caching.** Every `/api` answer carries `Cache-Control: no-store` and
  `Pragma: no-cache`, by assignment rather than `setdefault`. The page's assets
  are untouched.
- **Config.** `SESSION_COOKIE_SAMESITE` is `lax` or `strict` and nothing else
  (`none` would have left the new middleware as the only thing between another
  site and the cookie). `SESSION_SECRET` must be ≥ 32 characters or sign-in
  stays off with a plain warning — the cookie is an HMAC over a payload carrying
  the `staff` flag. `.env.example` says both.

**`3581eea` — the input guards, the read limit and the mock.**

- `purge_days` was `int(payload.get(...) or 0)` — a 500 on the word "seven".
  Guarded parse, bounded 0–7, refused **before** the guard check so junk cannot
  first record a `mod.would_ban` case and then fail.
- Role menu `PUT` wrote the heading, then walked the options, so a bad role in
  position two left a half-written menu. The whole body is validated first now;
  a non-dict option is a 400, not an AttributeError; `description` is coerced to
  `str` before it can reach sqlite, keeping absent / `""` / value distinct.
- Discord's 256 / 4096 / 100 / 25 live in the **cog** beside the SQL, reused by
  `create_menu`, `update_menu`, `add_option` and the API. They **refuse with the
  reason**, never truncate.
- A second `TokenBucket`, 300/min per session, on `/api/ref/*`, `/api/actions`
  and `/api/mod/cases`. And `TokenBucket`'s prune was O(n) per call and outrun by
  a spoofable header — it evicts the least-recently-used key in O(1) now.
- The mock refused a modmail reply and a warn that the **real API allows**;
  `check.mjs` now asserts the six genuinely-guarded routes 409 and those two do
  not, then flips the guard off through a new non-contract `/api/mock/guard` to
  read the shapes of the routes that refuse.

**Two existing tests changed, and why.** The bucket test asserted the dict
*shrinks* after a flood — true of the old sweep, false of an eviction cap; it
asserts the cap holds and the oldest key is gone. The `showall` paging test
built one menu with 100 options, which the 25-option limit refuses; it builds
four full menus instead and still spans several messages.

**Why:** `docs/info/code-notes.md`, "Phase 8b — the security review's fixes".

**NOT verified:** any of it against live Discord, or a real browser against the
real API. The same-site check is exercised through `TestClient` only, which
sends whatever the test says rather than what Chrome would send.

## 2026-08-27 — Batch 3 merged: the panel you can press in test mode, and `/voice`

**What:** one merge commit on `main`, `6b75c11`, two parents (`65dc85c` and
`af3dd55`). **Not pushed, not deployed, never run against a live bot.** The
branch `worktree-agent-aa87571126477eb8f` was cut from `9d948ca` and carried two
commits (`91c9c0b` the panel, `af3dd55` the `/voice` group). **1134 tests pass
(1105 + 29), ruff clean, `node site/mock/check.mjs` reports 13 pages / 49 routes
with every key present.**

Moved here whole from `TODO.md`. The ask, owner verbatim (2026-08-26 ~23:40):
*"in the join to create channel, i recall that bot we're mimicking having a way
to change the details of a channel in the chat associated with the voice
channel. can you do research then implement that."* The Phase 3 panel existed
but the guard suppressed it in test mode, so nobody could press a button until
test mode was lifted.

**What landed.** The panel is now posted **into the test channel** while guarded,
with a first line naming the voice channel it controls, and its buttons work
from there — which needed a new column, `tempvoice_channels.panel_channel_id`,
because `interaction.channel_id` stopped being the answer to "which channel is
this click about". Three outcomes, three log kinds: posted in the voice chat →
nothing extra, posted in the test channel → `tempvoice.panel_elsewhere`, no test
channel to post in → `tempvoice.panel_failed`. Unban and Unpermit joined the
panel (eleven buttons now), `tempvoice_prefs` grew a `bitrate` column, and a
`/voice` group of sixteen subcommands calls the same module-level `do_*` helpers
the buttons call — one implementation per action, not two.

**The merge conflict, and how it was resolved.** Both sides had restructured
`tempvoice.py` from the same base for different reasons. `main`'s batches 1–2
and the 8b reconcile had extracted the setup path to module level so the web
could call it (`make_creator_channel`, `repair_creator_channel`,
`adopt_creator_channel`, `creator_spot`, `where_sentence`, `may_act_in`,
`join_roles`, `same_lobby_name`, `lobbies_by_name`); the branch had extracted the
*panel* path to module level so the slash commands could call it (`Target`,
`temp_channel`, `panel_row`, `panel_home`, `get_row_by_panel`, `rate_limited`,
`already_message`, `move_out`, `pick_row`, `may_use_voice`,
`guild_bitrate_ceiling`, `clamp_bitrate`, `region_choices`, `member_lists`,
`mentions`, `info_lines`, eleven `do_*` helpers, and a `panel_context` that
returns a `Target`). Both were kept. ⚠️ **The branch's own `_repair` and
`_where_sentence` were DROPPED rather than merged** — `main` had already lifted
both to module level, and keeping the branch's copies would have been a second
home for each (checklist 15). Git auto-merged everything except two hunks;
`api/tools/tempvoice.py` still imports `connected_ids`, `make_creator_channel`
and `rows_for_guild` unchanged.

**Schema 8 → 10, and 9 is used rather than skipped.** Nothing on `main` had
claimed 9 (`main` was at 8; the other live worktrees are at 8 and 5), so the
branch's numbering stands: `panel_channel_id` is 9, `tempvoice_prefs.bitrate` is
10. Both are additive through `ADDED_COLUMNS` **and** present in `SCHEMA`, so a
fresh database and a migrated one agree.

**The docs gotcha, worth keeping.** The `### F8 follow-up` block in
`info/code-notes.md` carried a banner saying to re-key it after the merge and to
*trust the anchors, not the numbers* — which turned out to be the only usable
advice, because ⚠️ **its keys matched NEITHER branch commit.** Three of thirteen
(`:194`, `:200`, `:317`) were exact against `af3dd55`; most of the rest carried a
consistent **+170** offset against it, and none matched `91c9c0b`. A diff-based
re-key therefore produced confident, wrong numbers — `panel_context`'s note
landed on `return CANNOT_EDIT`. That block was re-keyed **by anchor**, function
by function, and every key verified one at a time against the merged file. The
main F8 block, keyed honestly against `65dc85c`, mapped cleanly (114 keys moved,
4 hand-repaired). Three notes described behaviour the merge removed and were
**rewritten rather than renumbered**: `_post_panel`'s "the panel is NOT posted in
test mode", the `would_post_panel` test note, and `db.py:11`'s "bumped to 8".

## 2026-08-27 — Phase 8b merged and reconciled: the API and the pages meet

**What:** three commits on `main`, **not pushed and not deployed**. `178fe69`
merges the API branch (`worktree-agent-aa75689d2dd1f44e7`, 53 routes, the name
resolver, the settings API, and plain-helper extractions in nine cogs);
`6bf4669` merges the pages branch (`worktree-agent-a1a9c6c08baf65618`,
`site/**` only, thirteen tabs and a Node mock); the third reconciles their
shapes. **1105 tests pass, ruff clean** (831 + 223 + 51 new contract cases).

**The one merge conflict, and how it was resolved.** Both halves had rewritten
`black_bloc/cogs/community/tempvoice.py`'s setup path from the same base and for
different reasons: Builder A extracted `make_creator_channel` so the web could
call it, while `main`'s test-sweep batches 1 and 2 had grown the remembered
lobby name, the join overwrites, repair, and adoption of a lobby the bot had
lost track of. **Both were kept, in one home**: the batch work now lives *inside*
`make_creator_channel`, with `repair_creator_channel` and `adopt_creator_channel`
beside it at module level; `setup_channel` defers and delegates; `_adopt` and
`_repair` are gone; `_may_act_in` and `_join_roles` delegate to module-level
`may_act_in` / `join_roles`. The behaviour change reaches the API too:
`POST /api/tempvoice/setup` now treats `repaired` and `adopted` as **successes**,
and the branch's `already_a_lobby` 409 went with the behaviour it described.

**The real work was the shapes.** The two builders coded blind against
`info/phase8b-design.md`, which fixes the JSON only for `/api/ref/*` and
`/api/settings`. Nine routes disagreed. ⚠️ **None of them would have thrown** —
they render as an em-dash, a blank tile or a badge that never appears, which is
exactly why they needed finding on purpose rather than by looking at a page:

| Route | What differed | Fixed where |
|---|---|---|
| `GET /api/mod/parity` | API nests the counts under `report` and has no `notes`; the page read `found.agree` and `found.notes` | **both** — page reads `report.*`; the API returns the command's own `parity_lines` as `notes`, so the "test mode is on" caveat has one wording |
| `GET /api/events` | API `decided_by_id`; page read `decided_by` | site |
| `GET /api/modmail/snippets`, `/blocks` | API `by_id`; page read `by` | site |
| `GET /api/modmail/tickets[/{id}]` | API `closed_by_id`; page resolved `closed_by` | site |
| modmail message `delivered` | API sends a bool; page tested `=== 0` | site |
| `GET /api/modmail/tickets` | page had a "Messages" count column the API never sends | site — column removed |
| `GET /api/settings/audit` | API `updated_by_id`; page read `updated_by` \| `by` | site |
| `GET /api/tempvoice/channels` | API `name`; page read `channel_name` | site |
| `POST /api/mod/{warn,…}` | API has no `id`; page printed "case ${found.id ?? 'written'}" | site — shows the API's own sentence |
| `PUT /api/rolemenus/{name}` | page's mode select offered only `multiple`/`single`, so saving a **staff** menu silently downgraded it | site — `staff` added |

**Two things the API gained, because the page needed them.**
`POST /api/birthdays/import` is the "import report" the design listed for the
birthdays tab and named no route for — Builder B correctly refused to invent an
endpoint, and it exists now because the cog already had the whole import trapped
inside the slash command, so `import_rows` and `members_of` were lifted to module
level the same way A lifted nine others. And parity's `notes`, above.

**Settings namespaces (owner decision at the merge):** `modlog_channel_id`,
`mod_dm_on_action` and `carl_modlog_channel_id` were served as three one-key
namespaces of their own, because the rule is "the prefix before the first `_`".
They are moderation keys, so they are folded into **`automod`** by an explicit
map, `settings_api.py:NAMESPACE_OVERRIDE`. Builder A's argument against a hand-kept
table — it goes stale when Phase 9 adds a key — is real and is written down beside
the map; the answer is that three lines in the one module that decides namespaces
beat handing somebody a settings page with groups called `mod`, `modlog` and `carl`.

⚠️ **The fix that outlives all of the above is `site/mock/contract.json`.** For
every route, the keys the pages actually read, derived by grepping the page
modules' property accesses rather than by restating the design doc. Both halves
read that one file: `tests/api/test_contract.py` runs it against the **real**
routers with fakes (51 cases, and a route that answers `[]` **fails** — a row
shape checked against nothing is a green test that never ran), and
`site/mock/check.mjs` runs it against the mock. So a shape can no longer be right
in one half and wrong in the other unless somebody edits one and not the file
both read. The mock was rewritten to be byte-compatible: bare arrays where the
API returns bare arrays, `*_id` name fields, flat ticket detail, `web.<area>.<verb>`
action kinds (it had been teaching `web.settings_set`), and `POST /api/mock/reset`
so each check starts from the same fixture.

**Verified:** `1105 passed`, `ruff: All checks passed!`, and
`check: ok - 13 pages, 49 routes, all keys present`. The mock's refusal paths
were smoke-tested by hand (409 under `MOCK_TEST_MODE`, 403 non-staff, 401
signed out). **NOT verified:** any page in a browser against the **real** API —
only against the mock; and nothing whatsoever against live Discord. The bot was
not run, nothing was pushed, nothing was deployed, and no worktree was removed.

## 2026-08-27 — Owner test sweep round 2: `/help`, and a lobby setup can adopt

**What:** two commits on `main`, not pushed and not deployed.

`/help` (`black_bloc/cogs/core.py`) answers the owner's ask verbatim — *"we also
need a / command that vomits out every /command that can be run"*. It walks
`bot.tree.get_commands()` **and** the guild-synced copies, merged by name, so a
guild-only command cannot be missing from "every command that can be run here";
recurses through groups and subgroups; renders `/group sub — description` one per
line under a bold heading per top-level command, sorted; chunks through the shared
`pages_under_limit`, first page as the ephemeral response and the rest as
ephemeral followups with `allowed_mentions=none`. An optional `filter:` narrows by
name or description and keeps a group's heading when the group itself matches; no
match gets a sentence, not an empty message. Staff-only commands are suffixed
`(staff)`, decided by `is_staff_command` in `settings_store.py` (one home, next to
`require_staff`): it reads the command body for the `require_staff` call and
follows **one** hop into a helper it calls — which is how `/warn` and the modmail
commands, gated in `_ready`, are marked — and leaves a gate further away
**unmarked rather than guessed at**, per the owner's instruction. That was chosen
over a decorator/`extras` marker on ~50 commands in nine files because a marker
goes stale silently the first time somebody forgets it, and reading the call
cannot.

Temp voice (`black_bloc/cogs/community/tempvoice.py`) now **adopts** a lobby it
lost track of instead of making a second one: when `tempvoice_creator_ids` names
no live channel, `/tempvoice setup` looks in the target category for a voice
channel whose name equals `tempvoice_creator_name` (stripped, case-insensitive),
stores its id **before** attempting the repair (the id is the durable half; a
rename Discord refuses must not undo the adoption), logs `tempvoice.adopt` as its
own kind, and repairs it in place with a sentence saying it took it over. Extra
matches are adopted too and named with `/tempvoice forget`, reusing the repair
path's existing sentence. `/tempvoice status` now lists every voice channel in the
target category carrying the lobby name whose id is **not** in the list, with the
sentence that fixes it.

**Root cause found for the duplicate lobby (finding 2a), and what could NOT be
established:** the write path has no gap. Both the Phase 3 original (`c3bf360`)
and the current command store the new channel's id immediately after a successful
create and before the reply, and the only two code paths that remove an id are
`/tempvoice forget` and the `on_guild_channel_delete` listener, which fires only
for a channel that really was deleted. So a lobby whose id is absent is one *this
store never saw created*: made by hand, made by a bot process reading a different
database (`DATABASE_PATH` defaults to a **relative** `data/black_bloc.sqlite3`, so
a local run and the Fly volume at `/data` are two different stores — measured
2026-08-27, the repo's own `data/black_bloc.sqlite3` has no `settings` table at
all), or one whose delete event removed it. ⚠️ **Which of those happened is NOT
established** — the live store is on the Fly volume and was not readable from this
tree, and the bot was not run (owner mid-sweep). What *is* established, and is the
real defect either way: the stored id was the **only** recogniser, so any lobby
the store did not know always produced a second one. It now has a second
recogniser.

**Tests:** 831 pass, ruff clean (817 before; 14 added). Changed tests: none
rewritten — the 14 are additions. New: the rendering of `/help` asserted as a
whole list (shape, sort order, `(staff)` suffix), the filter's three cases, the
chunking, the guild-only command appearing, and ⚠️ **the only test in the suite
that builds the real bot and loads every cog**, which is what proves the one-hop
staff detection on the real tree (`/warn` gates in `modcmds._ready`). Detection
tests in `tests/test_settings_store.py` pin the **limit** as well as the successes:
a gate two calls away reads `False` on purpose. Temp voice added the pure
name-matching function, adoption instead of a second channel, a channel with
another name being left alone, the id being stored even when Discord refuses the
rename, and status naming the strays.

**NOT verified:** anything against live Discord. `/help` has never been run in the
server, no lobby has ever been adopted, and the commands are not synced until the
next deploy.

**Commits:** `c47aa6f` (`/help`), `b430eb0` (temp voice). Docs: `info/code-notes.md`
re-keyed (98 keys moved across six files, one anchor repaired by hand).

## 2026-08-26 — Owner test sweep round 1: four findings fixed (not deployed)

**What:** `8fe0677` temp voice — `/tempvoice setup` now passes explicit
overwrites built from a copy of the category's own, adding `view_channel` +
`connect` for `tempvoice_allowed_role_id` (Member), for every **resolved** staff
role and for the bot (plus `manage_channels`/`move_members`), leaving `@everyone`
exactly as the category has it; spawned channels get the same allowed-role and
staff allows on top of the owner's. The lobby's name became a setting
(`tempvoice_creator_name`, default *join to create a channel*), and setup
**repairs** an existing lobby in place instead of refusing, gated on
`_may_act_in` because a rename is a side effect `guard.py` cannot see.
`_reconcile_loop` gained an `@loop.error` handler, `last_ok_at`/`last_error`,
`loop_health()` for `api/status.py`, and two lines in `/tempvoice status`.
`9d948ca` — `/rolemenu showall` (staff, every menu + every option, chunked
through the shared `pages_under_limit`, first page as the response and the rest
as ephemeral followups, `allowed_mentions=none` on all of them); `menu_heading`
and `option_line` extracted so `show` and `showall` cannot disagree, and `show`
gained the `allowed_mentions` it was missing while printing role mentions; and
`/twitch link` renamed its parameter to `channel` with no user-facing sentence
saying *login*, internal names (`twitch_login` column, `clean_login`, the log
detail key) deliberately unchanged.

**Why the `join` name was NOT a truncation bug:** measured, not guessed — the
cog has no string handling on the setup path, and the command's `name` parameter
introspects as optional with default `None`, so an unsupplied name renders the
full default. Discord must have sent `name: join`. The fix is a setting that can
be read back and re-applied, plus a repair path.

**Tests:** 817 pass (800 → 812 → 817), ruff clean. One test changed meaning:
*setup refuses a second lobby* became *setup repairs the lobby it already has*,
because refusing is what left the owner with a broken lobby and no way back.

**NOT verified:** nothing is deployed. No Discord API call was made and the bot
was never run — the owner was mid-sweep against the live instance. Deployment and
live re-verification are tracked in `TODO.md` under the round-1 sweep table.

## 2026-08-26 — Phase 8a live: the status site at blackbloc.heygabi.ai (Option A)

**What:** worktree build (`930248d` API auth + status routers, `6b1bdb0`
site — the builder rendered every refusal state in Chrome); Opus security
review → SHIP WITH FIXES (12 findings: cross-site cookie could never work on
Pages; `live_staff` failed OPEN for members who left; three 500 paths incl.
NaN latency; no rate limit; OAuth code in the access log; "could not check"
reported as "not staff"; no security headers); owner decision Q14 = Option A
(serve the site from the Fly app under one hostname); Opus fixer (`c211715`,
`50205dd`): StaticFiles mount, `__Host-` cookies, CSP/HSTS/nosniff, per-IP
rate limit via `Fly-Client-IP`, `staff_unknown` state, no CORS; merge agent
→ `618dcd1` (no conflicts; found and fixed the loop-health reader guessing
attribute names — Events' dict would have rendered as an error — via a
`cog.loop_health(name)` contract; `open_modmail` count added; dead
`api_origin` removed; `.env.example` corrected). 800 tests. Owner did DNS
(A/AAAA, proxy off — Claude drove the Cloudflare form via `form_input` after
a password-manager popup blocked keystrokes), both OAuth redirects; Fly cert
issued by Let's Encrypt; secrets staged via a self-cleaning script.
Deployed: `/health` 200, index 200 with CSP, Uvicorn on 0.0.0.0:8080,
bot logged in.
**Why Option A:** a `SameSite=Lax` cookie does not ride a cross-site fetch,
and `SameSite=None` is already blocked by Safari/Firefox partitioning; one
hostname removes the problem and every CORS line with it.
**Verified:** offline suite; HTTP checks against the live hostname. **Not
verified:** a real Discord sign-in round-trip — the owner's sweep.

## 2026-08-26 — Phase 6 live (shadow): moderation (F7) — the seventh and last core phase

**What:** worktree build (`6437d9f`, `fa6f6e8`, `71626c5`: pure rule
engine, shared `modcases.py`, automod cog, mod commands); Opus reviewer →
SHIP WITH FIXES (23 findings, top: a fired verdict re-fired on every later
message in the window — an apology would be deleted and timed out again;
Apply-now locked on the clicker not the case; parity could agree with
itself); owner decisions applied (raw mention counting, `/untimeout`+`/unban`
gated in test mode, `/settings show` chunked, arming refused while the staff
channel is the test channel); Opus fixer (`3c2beff`, `e85d9b5`); merge agent
→ `4677597` (6 conflicts incl. a genuine add/add on `tests/cogs/test_core.py`,
merged; duration parsers in events vs modcases documented as NOT
interchangeable — minutes vs seconds). 735 tests. Deployed: `synced 27 app
commands`. Architecture rule 5 gained the bounded-idempotent-rebuild
exception for the one non-additive schema step (`mod_cases.user_id` nullable).
**Why shadow beside Carl:** `/automod parity` is the cut-over number; Carl
stays armed until Bloc-only and Carl-only are both zero for a week.
**Verified:** offline suite; Fly log. **Not verified:** any real
delete/timeout/ban; Carl's modlog format is inferred from two shapes —
first parity run must be eyeballed.

## 2026-08-26 — Phase 7 live (disabled by default): modmail (F11)

**What:** worktree build (`b111a7f`, `0d7500c`, `c4e4777`); Opus reviewer →
SHIP WITH FIXES (16 findings: `/areply` leaked the staff role *colour*; the
bot DM'd strangers while modmail was off; transcript clamp counted chars
not bytes and a failed transcript still deleted the channel; nine commands
never deferred; no loop error handler); Opus fixer (`669440f`, `2cc9c02`);
merge agent → `088b107` (5 append-only conflicts, no one-home breaks;
Phase 7 already reused `events.clamp`/`slugify`, `golive.parse_ts`,
`timezones.stamp`). 628 tests. Deployed: `synced 17 app commands`.
**Why disabled by default:** the incumbent ModMail bot holds 5 live
tickets; Black Bloc says nothing until the owner flips `modmail_enabled`.
Channel mode (like today) is the default; thread mode is a setting.
**Verified:** offline suite; Fly log. **Not verified:** any DM relay,
ticket channel, or transcript against live Discord — owner's sweep.

## 2026-08-26 — Phase 5 live: birthdays (F6) — first parallel-worktree phase

**What:** built in an isolated git worktree while Phase 4 was on `main`
(`3978163`, `4c45f17`); Opus reviewer → SHIP WITH FIXES (12 findings — a
birthday *role* was granted even in shadow; removal used the current
setting's role, not the granted one; the import searched Discord by prefix
and could not match `[Tag] Name` nicknames); Opus fixer (`149c568`,
`6793c97`): mode-gated role add, `role_added_id` column, role taken back on
remove/optout, import scores against the cached member list (no network),
`/settings clear`, `#RRGGBB` colour validation, `importlib.resources` seed;
Opus merge agent → `08b114c` (4 conflicted files, all append-only; one
genuine break — a `sqlite_master` probe for Phase 4's table — removed as
a second home). 534 tests. Deployed: `synced 11 app commands`.
**Why worktrees:** owner asked for parallelism; a Docker deploy ships the
working tree, so builders must not share `main`. Shared files are touched
append-only and schema versions are pre-assigned per phase.
**Verified:** offline suite; Fly log. **Not verified:** the import against
the real 118 members (the report will say); any real embed.

## 2026-08-26 — Phase 4 live: events (F4/F5) + review fixes

**What:** Opus builder (`10ef099` timezones + `/timezone`, `039bb25`
events logic, `839cfff` cog: 5-field modal, `pending-user-event` review
channels, DynamicItem Approve/Deny, scheduled-event creation, go-live +
reconcile loops); Opus reviewer → SHIP WITH FIXES (14 findings: bare
`ValueError` from `ScheduledEvent.cancel()` would kill the reconcile loop
for the process's life; stale events announced late with a role ping;
retention deleted channels without the guard; the announcement promised an
Interested button that may not exist); Opus fixer (`63e1d15`, `8474f14`):
end-vs-cancel by event status, `@loop.error` + health on both loops,
missed/late handling with `events_max_late_minutes`, guard now gates
`delete_channel` via `allows_place`, `announce_text` truthful, requester
DM'd on every cancel, `AnswersErrors`/`SafeDynamicItem` mixins applied
across events/honeypot/tempvoice, two-miss reconcile, DST gap detection.
450 tests. Deployed: `synced 10 app commands`.
**Why the review card posts to the test channel in test mode:** the review
channel is not the test channel; the guarded send is the only way the owner
can click Approve/Deny during the sweep — it reverts to the review channel
when the guard is gone.
**Verified:** offline suite; Fly log. **Not verified:** a real modal, a
real scheduled event, a real rename against the 2/10-min limit — owner's sweep.

## 2026-08-26 — Phase 3 live: temp voice (F8), honeypot (F9, shadow), role-menu rider (F17)

**What:** Opus builder (`c3bf360` temp voice on schema v4, `6ed9f80`
honeypot, `9319560` role rider: Carl's real emoji, `staff` mode,
`runner-status`); Opus reviewer → SHIP WITH FIXES, 15 findings (HIGH: staff
exemption ignored category-inherited permissions — a Lead could be banned by
the trap; purge-days >7 would 400 every ban; threads bypassed the trap and
system messages could ban their author); Opus fixer (`85a7978`, `808686c`):
computed-permission staff derivation (one home, refuses to arm with an
empty set, status prints the resolved count), purge clamp 0–7 via
`delete_message_seconds`, message-type filter + thread denies, log-before-
answer in all eight panel handlers, defer-before-edit, claim/transfer lock
(on the bot object — module-level locks broke under per-test loops),
5-minute reconcile loop, claim requires being connected, `voice_states`
for occupancy, `forget` commands + channel-delete listeners, shadow-hit
dedupe, place-gated deletes. 288 tests. Deployed: `synced 8 app commands`.
**Why the panel is not posted in test mode:** a temp channel is not the
test channel; the guard would raise from the HTTP layer — logged as
`would_post_panel` instead. Checklist grew to 27 items.
**Verified:** offline suite; Fly log. **Not verified:** any real voice
event, channel creation, or trap post — owner's sweep.

## 2026-08-26 — Phase 2 live in shadow: go-live feed (F1/F2) + review fixes

**What:** Opus builder (3 commits `b635320` Twitch Helix client, `b2c0b39`
go-live logic + schema v3 + 8 settings keys, `ece5e3b` cog: presence
listener, 60 s Twitch poller, 120 s end-grace, `/golive`, `/twitch`);
Opus adversarial reviewer → **SHIP WITH FIXES** (13 findings, 5 blocking
before mode `on`); Opus fixer (`a680536` + `8579f3e`): reconcile open
sessions on start, unconditional role removal via `live_role_added`,
`golive.post_failed` distinct from `would_announce`, transport errors wrapped
as `TwitchError` + a tree error handler (`command_errors.py`),
`allowed_mentions` everywhere, per-user lock + partial unique index against
double-announce, poller health in `/golive status`, duplicate-login refusal,
guard now gates `edit_message`. 162 tests, ruff clean. Deployed; `synced 6
app commands`; Twitch enrichment confirmed on after the secrets import.
**Why shadow by default:** nothing reaches `#live-now` until the owner has
compared `would_announce` lines against YAG's real posts.
**Review learnings** → `info/review-checklist.md` (20 items), now in every
brief. **Verified:** offline suite; Fly log lines. **Not verified:** any
real presence event or Helix call — on the owner's test sweep.

## 2026-08-26 — Phase 1 live: settings store, action log, role menus (F16)

**What:** Opus builder, three commits (`7190855` settings store + schema v2
+ `/settings`, `81fe783` action log, `5c528c5` role menus + Carl seed);
Fable reviewed the select handler and staff derivation; 43 tests, ruff
clean; deployed to Fly — `synced 4 app commands`, logged in 01:30:00Z.
**Why these shapes:** one settings registry with typed keys and defaults
derived from TEST_MODE so nothing hard-codes a channel; `log_action` writes
the DB row first and never raises on the embed, so the log is the record
even when Discord refuses; role menus are select-menus (not reactions) with
persistent views re-registered on startup; the diff touches only the
menu's own roles, so posting our panels beside Carl's strips nobody.
**Builder deviations accepted:** `SettingsStore(db, settings)`;
`Database.is_connected`; `guard.refusal_message()`; `@everyone` excluded
from staff; seed does not pre-check assignability. **Verified:** offline
suite + the Fly log lines. **Not verified:** any click in Discord — on the
owner's test-sweep list in `TODO.md`.

## 2026-08-26 — Incumbent survey, feature list, seven phase designs

**What:** Two Opus research agents + Fable's own dashboard walk produced the
complete picture of what the server runs: `archive/current-bots/
discord-scan-2026-08-26.md` (128/128 channels, 12,488 messages, 60 roles),
`carl-bot-dashboard-…`, `yagpdb-dashboard-…`, `birthday-bot-export-…`, and
`info/reference-bots.md` (vendor docs for TempVoice, Honeypot, YAGPDB,
Carl, Birthday Bot, Modmail + Discord platform limits). Every owner decision
Q1–Q13 was asked one at a time and recorded in `TODO.md`. Output:
`info/feature-list.md` (F1–F16, build order approved) and
`info/phase1..7-design.md`.

**Why it took a rescan:** the first scan read 4/134 channels — the bot
lacked a role with View on the categories. Owner gave it `Bots`
(Administrator; accepted because moderation-role management is coming). The
first pass's *inference* that `#live-now` was human-posted was wrong;
measured: 199/200 posts are YAGPDB. Kept as the example of why inferences
get labelled.

**Findings that changed the design:** Birthday Bot fires at each member's
own midnight (15/16 land the evening before in Phoenix); Carl has exactly
one armed automod rule; YAGPDB has no role menus; three dormant bots incl.
two earlier attempts at this project; Discord exposes no user timezone;
EventSub needs a user token (websocket) or a public callback (webhook) — so
Twitch is Helix polling as a fallback, presence is primary.

**Verified:** all counts above are from the agents' reports and the saved
captures. **Not verified:** vendor-doc claims marked "(inferred)" or
"(from memory)" inside `reference-bots.md`; the Bash-tool Defender block
was diagnosed from `Get-MpThreatDetection`, not reproduced on purpose.

## 2026-08-26 — First Fly.io deploy; `/ping` confirmed by the owner

**What:** `flyctl` installed (winget `Fly-io.flyctl`), owner logged in from a
real PowerShell window (Claude's shells are non-interactive and `auth login`
refuses them), app `black-bloc` created in org *Sky*, 1 GB volume in `lax`
(there is no `phx` region), four secrets imported via stdin, `deploy
--ha=false`. Fly log shows `logged in as Black_Bloc#6132 … 1 guild(s)` at
2026-08-27T00:14:44Z on machine `85e744c4d959d8`. The owner confirmed `/ping`
worked against the local run just before ("ping worked").

**Why `--ha=false`:** Fly's default is two machines; for a gateway bot that
is two copies answering every command. One machine, one volume.

**Why `secrets import` over `secrets set`:** the token never appears on a
command line, in shell history, or in Claude's output.

**Verified:** login from Fly (log line above); `deploys.log` entry written.
**Not verified:** `/ping` against the *hosted* instance by a human (on TODO);
the machine surviving a Fly host restart with the volume intact (needs time).

## 2026-08-26 — First live login + test-mode gate + first commit/repo

**What:** Owner created the application, token, guild ID, invite and the three
privileged-intent toggles; the bot logged in as `Black_Bloc#6132` in *Black in
a Flash!* (1 guild) with `synced 2 app commands`. The owner's test-channel rule
became `black_bloc/guard.py` (`TEST_MODE`, `TEST_CHANNEL_ID`). First commit
made and pushed to a private GitHub repo under the owner's account.

**Why it took several runs — each run found a real defect that reading the
code had not:**
1. `DEV_GUILD_ID=` blank in `.env` → pydantic refused `""` as `int | None`.
   Fix: `before` validator maps blank → `None`; config errors now exit 2 with
   one plain line (`config.py:load_settings`).
2. Not-yet-invited server → bare `403 Forbidden` traceback from `tree.sync`.
   Fix: caught, logged with the invite URL (`bot.py:setup_hook`); the invite
   URL is built from `INVITE_PERMISSIONS` and logged before the gateway step.
3. Intents off → 40-line `PrivilegedIntentsRequired` traceback. Fix: mapped to
   exit 3 with the portal step named (`app.py:main`). Same for `LoginFailure`.
Lesson recorded in `info/gotchas.md`: run it, do not reason about it.

**Verified:** login, cog load, guild command sync, test-mode banner — from the
bot's own log, 16:57 Phoenix. 13/13 tests, ruff clean.
**Not verified:** the owner invoking `/ping` (left on TODO); the guard against
a *real* out-of-channel send (unit-tested only).

## 2026-08-26 — Project scaffold, venv, docs tree

**What:** Empty folder → runnable Python package `black_bloc/` (thin
`app.py` orchestrator, `bot.py` with cog loading + dev-guild command sync,
`config.py` on pydantic-settings, `storage/db.py` on aiosqlite, optional
`api/server.py` FastAPI health endpoint run inside the bot's loop), `tests/`
(config, offline bot+cog load, DB bootstrap, API health), `Dockerfile` +
`fly.toml`, `.venv`, and the seven-piece `docs/` tree with `DOCS_STANDARD.md`
copied from the estate.

**Why these choices (the part worth keeping):**
- **`discord.py` over hikari/nextcord/pycord** — largest ecosystem, first-party
  slash-command support (`app_commands`), cogs are the natural per-feature unit,
  and the estate has no existing Python Discord code to stay consistent with.
- **FastAPI over Flask** — the bot is `asyncio`; FastAPI runs in the same loop
  and can read bot state directly. Flask would need a thread and IPC. It is
  flag-gated (`API_ENABLED`) and OFF by default because no feature needs it yet.
- **SQLite (aiosqlite) over Postgres** — one process, one file, zero services
  to run; a hosted Postgres would be the first paid dependency for a bot with
  no data yet. Revisit when there is a second process or real write volume.
- **Not Cloudflare Workers** — owner's first thought for hosting, rejected
  because a moderation bot needs gateway events (messages, joins), which need a
  persistent websocket Workers cannot hold. Full reasoning: `info/hosting.md`.

**Verified:** `pytest` → 6 passed, `ruff check` → clean, both in the fresh
`.venv` (Python 3.12.10, discord.py installed 2026-08-26); `python -m black_bloc` with
no token exits 2 with a plain-English message instead of a traceback.
**Not verified:** anything against a live Discord gateway (no token yet); the
Fly.io deploy (not run).
