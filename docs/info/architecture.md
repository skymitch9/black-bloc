# Architecture

> **Audience:** Claude sessions and the owner. **Status:** TRACKED (owner, 2026-08-31 — was
> local-only until then).
> Last verified: **2026-09-19** — the docs staleness pass after the **TEST_MODE lift**.
> ⚠️ **The fact table was carrying two figures that were simply WRONG, and one of them
> contradicted the history table three rows below it.** Re-measured by import in this tree, off
> `main` `ffea17e` (**v141 LIVE**):
> **`storage/db.py:SCHEMA_VERSION` = 45** (the table said **44** — while its own *How the counts
> moved* row for v141 already said 45);
> **`../deploys.log` = 140 lines**, last `2e48d7c` v141 (the table said **138**);
> `len(settings_store.KEY_TYPES)` = **277** (the figure was right but was still labelled *"on
> branch `youtube-uploads-removal`"* — that branch merged as v139 and the number is `main`'s);
> `len(bot.COGS)` = **22** ✅; `tests/test_bot.py:TOP_LEVEL_NOW` = **32** ✅;
> `settings_store.namespace_of` over `KEY_TYPES` = **25** groups ✅;
> `settings_store.FEATURES == logkinds.FEATURES` = **21** ✅.
> **Two DUPLICATE rows were deleted from the fact table** — a second *Setting groups* and a
> second *Features*, the latter reading **20** against the first's **21**, so the table
> disagreed with itself about the same number in the same table.
> **The Shape tree named 20 modules fewer than the package holds** and is redrawn:
> `forums.py`, `frontdoor.py`, `guides.py`, `handoff.py`, `minutes.py`, `minutes_audio.py`,
> `minutes_session.py`, `pings_onboarding.py`, `posted.py`, `posts.py`, `shadow.py`,
> `spawned.py`, `api/tools/{frontdoor,guides,minutes,posts}.py` and
> `cogs/community/{frontdoor,minutes,posts}.py` were all absent; `loops.py` named only
> `wait_ready` and not `Reconciler` (v141); `command_errors.py` did not mention `record()`
> (v131); `storage/db.py` was annotated *"SCHEMA_VERSION 44 on branch `minutes`"*;
> `guard.py` did not say the flag is off in production; and the site block said **17 pages**
> where disk holds **20**.
> ⚠️ **NOT verified today:** `pytest` was **not** run (the Tests row is the v141 deploy gate's
> figure, off `deploys.log`); `node site/mock/check.mjs` was **not** run (it needs a listening
> mock — the Mock row is the 2026-09-18 reading and is labelled as such); the *prose* below the
> tree (the rules, the library table, the API section) was **not** re-traced to the code; the
> tree's per-file annotations beyond the ones listed above are still the 2026-08-31 reading; and
> nothing here met Discord, the Fly console or a browser — `/health` was the only live thing read
> (`ok:true, ready:true, guilds:1, personality_pool_version:1`).
> Before that, **2026-09-18** — **three fact-table rows and two tree annotations**, on branch
> `youtube-uploads-removal` (cut from `main` `9bc1982`, NOT merged and NOT deployed; design
> `info/youtube-uploads-removal-design.md`). Re-measured by import and by running the thing in that
> worktree: registry keys **284 → 277** (`len(settings_store.KEY_TYPES)`, before and after — the seven
> `youtube_*` upload keys), mock **20 pages / 187 → 186 routes / 24 core settings** (`node
> site/mock/check.mjs` re-RUN against a mock on a spare port, not quoted), tests **6811 → 6723**
> collected, **6808 → 6720** passed + 3 skipped (`pytest -n 8`, forward and under `BB_REVERSE=1`).
> The `cogs/content/youtube.py` and `api/tools/youtube.py` lines in the Shape tree were rewritten:
> the uploads sweep is gone and the cog is the LIVE probe plus the channel links.
> ⚠️ **Nothing else on this page was re-checked then**, and ⚠️ the rows describe a BRANCH.
> Before that, **2026-09-17** — **two fact-table rows only**, on branch `boot-status` (cut from
> `main` `5ceea19`, NOT merged and NOT deployed): registry keys re-measured by import in that
> worktree, **280** (277 at v132), and the mock line re-RUN rather than quoted —
> `node site/mock/check.mjs` answered *20 pages, 186 routes, **24** core settings, all keys
> present*. Namespaces still **25**. ⚠️ **Nothing else on this page was re-checked then**, and
> ⚠️ the two rows describe a BRANCH — `main` reads 277 / 21 until it merges. Before that,
> **2026-09-16 09:10** — the fact table only, at the GUIDES landing (v111): schema **35**, keys **212** (from the v111 gate and the G1 report), features **19**, groups **24**, mock **18 pages / 160 routes**, tests **5703**, deploys **108**; new modules `black_bloc/guides.py`, `api/tools/guides.py`, `site/public/guides.html` + `assets/page-guides.js`, `scripts/release_json.py` — the Shape tree below was NOT redrawn for them. Before that, **2026-09-11 08:30** — docs-wide staleness pass on `main` at `1d090e5`. **Re-measured by import/command in a worktree of `main`:** cogs **19** (`len(bot.COGS)`), schema **34** (`db.SCHEMA_VERSION`), registry keys **202** (`len(settings_store.KEY_TYPES)`), features **18** (`settings_store.FEATURES == logkinds.FEATURES`), setting groups **23**, deploys **107** lines last `73e2e44` v108. **Read off disk:** `black_bloc/api/`, `black_bloc/api/tools/`, `black_bloc/cogs/**`, `site/public/*.html` (17). What that FIXED: the v92 fact table (keys 189 → **202**; schema "34 on `where-picker`, 33 on `main`" → **34 on `main`**; mock 149 → **150** routes; deploys 91/v92 → **107**/v108), the `storage/db.py` tree annotation (`SCHEMA_VERSION 22` → **34**), and three cogs + three `api/tools/` routers + three `api/` modules the Shape tree did not name. ⚠️ **NOT checked:** the prose below the tree (rules, library table, API section) still not re-traced to the code; the tree's per-file annotations beyond the ones named here; the mock line was taken from the v108 gate on `deploys.log`, not re-run; nothing here met Discord, and no browser rendered anything. Before that, **2026-09-11 00:38** (the follow-up 4 paragraph: ✅ LIVE v108 00:37, merge `73e2e44` — keys measured by the live `/api/settings` — **202**; tests and the mock line from the v108 gate — **5546** passed, *17 pages, 150 routes, 14 core settings, all keys present*; the link check itself probed live at the review; nothing here met Discord; nothing else re-measured) — earlier **2026-09-10 23:45** (the follow-ups 2+3 paragraph: keys measured by the live `/api/settings` — 199; tests and the mock line from the v107 gate — 5502 passed, 17 pages / 150 routes; nothing else re-measured) — earlier **2026-09-10 17:45** (the Where follow-up paragraph: keys and schema measured by import on the branch, tests and the mock line from the v106 gate — 5473 passed, 198 keys answered by the live `/api/settings`; nothing else re-measured) — earlier **2026-09-10 16:40** (the raid-train calendar-name paragraph: keys measured by import, tests and mock routes from the gate; nothing else re-measured) — earlier **2026-09-10 16:02** (the v100 paragraph: keys and schema measured by import, tests from the gate; nothing else re-measured) — earlier **2026-09-05**: every figure below re-MEASURED on the ENGINEERING SWEEP 3
> branch off `main` at `6af0ba0` (v92) by running the thing, not by reading a doc: the tree is
> built the way `tests/test_bot.py` builds it (load all `bot.py:COGS`, then `tree.get_commands()`),
> `SCHEMA_VERSION` is imported from `black_bloc/storage/db.py`, and the site figures come from
> `node site/mock/check.mjs` against `site/mock/server.mjs`.
>
> **2026-09-20 (Co-streaming — one announcement naming both platforms, branch `costream` off
> `main` `64ccfbc`; design `info/costream-design.md`; ⚠️ BUILT, NOT MERGED, NOT DEPLOYED, nothing
> has met Discord):** schema **45 → 46** (measured: `SCHEMA_VERSION`) — `golive_sessions` gains
> `also_source`, `also_url`, `also_platform` and `also_started_at`, all `TEXT` and all nullable,
> through `ADDED_COLUMNS` only, so ⚠️ **migrate-before-deploy is automatic here**: `Database.connect`
> applies them as it applies every column before them, and there is no backfill — an existing open
> session simply has four nulls and behaves exactly as it does today. Registry keys **277 → 280**
> (measured: `len(settings_store.KEY_TYPES)`) — `golive_costream_mode` (enum `off`/`on`, ships
> **on**), `golive_costream_template` and `golive_costream_author`, both text and both validated by
> `checked_costream` against the seven placeholders the fill knows (`{name} {game} {title} {url}
> {platform} {also_url} {also_platform}`). Setting groups **unchanged at 25** and features
> **unchanged at 21** — the three keys sit in the `golive` namespace the prefix already gives them.
> Two log kinds: `golive.costream_added` (IMPORTANT — it rewrote a post members are reading) and
> `golive.costream_dropped` (routine); `HEADS` already maps `golive` to the `golive` feature, so
> nothing moved there. Mock **unchanged at 20 pages / 186 routes** — the change is three keys on the
> existing `/api/golive/sessions` row, not a route. Tests **6757 → 6796**. ⚠️ **No new module:** the
> render lives in `black_bloc/golive.py` beside `render` and `ended_render`, and the three moves
> (`add_platform`, `drop_platform`, the unchanged end) are methods on the go-live cog, so the
> YouTube cog still renders nothing.
>
> **2026-09-17 (Move an open event's room into the forum, branch `events-move-to-forum` off
> `90252a6`; design `info/events-forum-design.md` §H; ⚠️ BUILT, NOT MERGED, NOT DEPLOYED, nothing
> has met Discord):** schema **unchanged at 45** (measured: `SCHEMA_VERSION`) — the move re-points
> the four columns schema 45 already has, so **no migration and no backfill**. Registry keys
> **282 → 283** (measured: `len(settings_store.KEY_TYPES)`) — `events_moved_line` text, the one
> line the old room hears, `{post}` its only placeholder, validated by `checked_moved_line` and
> rendered with a fall-back to the default (checklist 17). Mock **unchanged at 20 pages / 187
> routes** — ⚠️ the real API serves **188**: `POST /api/events/{event_id}/forum` is deliberately
> NOT a `contract.json` row because `check.mjs` reseeds before every entry and a fresh seed has no
> forum (deviation §H-4); it is exercised by a bespoke `checkEventsMove()` pass and by
> `tests/api/tools/test_events.py`. Tests **6755 → 6793**. ⚠️ **No new module.**
> `events.remove_place` is the deletion extracted out of `delete_room` — the guard check, the
> delete, the disown and nothing decided about the row — so `events.move_room_to_forum` can remove
> a room **without** settling the event and without clearing the `review_channel_id` it has just
> pointed at the new post. The order is load-bearing: the post is opened and the row re-pointed
> BEFORE the room goes, so `on_guild_channel_delete` finds no row for the old id and cannot cancel
> the event behind the move. `events.may_move_to_forum` is what a DOOR renders on (an open room,
> forum mode, a forum set); the function itself does not read the mode, so staff keep the final
> say. One new log kind, `event.room_moved` (ROUTINE, `{event_id, from, to, via}`), plus
> `event.moved_line_failed`. The Discord door is the `/event` panel's own event card — ⚠️ the
> Delete card §H named cannot carry it (deviation §H-2) — and the website door is the events
> page's queue row. `DECISION_TEMPLATE` grows a fifth action, `move_forum`. Before that:
> **2026-09-17 (Events as a forum under BlackMail, branch `events-forum` off `a7399b0`; design
> `info/events-forum-design.md`; ⚠️ BUILT, NOT MERGED, NOT DEPLOYED, nothing has met Discord):**
> schema **44 → 45** (measured: `SCHEMA_VERSION`) — `events` gains `review_kind TEXT` through
> `ADDED_COLUMNS`, nullable, and a NULL reads as `room`, so no backfill. Registry keys **+2**
> (`events_review_mode` enum room/forum default **room**, `events_forum_channel_id` channel blank —
> both events group by prefix); mock **20 pages / 187 routes** (`POST /api/events/forum`, the twin
> of `POST /api/requests/forum`); tests **6696 → 6755**. ⚠️ **One new module,
> `black_bloc/forums.py`** — the forum helpers requests and events now share (`tag_named`,
> `forum_tags`, `forum_overwrites`, `AUTO_ARCHIVE_MINUTES` 1440); both requests modules import it
> rather than keeping a second copy. In forum mode `events.open_review_post` replaces
> `make_review_channel` AND `post_review_card` (a forum post is created WITH its first message), and
> `events.review_place` is the ONE resolver every `guild.get_channel(row["review_channel_id"])` site
> now goes through — a post is `guild.get_thread` then `bot.get_channel`, claimed for the guard on
> every read (the v120 lesson). `events.PLACE_WORDS` is one vocabulary per kind, so `delete_room`
> and the **Delete this post** button are the same code with different sentences. The forum wears
> **six** tags — one per `STATUSES` entry, `live` included — looked up BY NAME, never by an id in a
> key. Seven new log kinds: `event.forum_made`, `event.forum_failed`, `event.forum_forgotten`,
> `event.post_failed`, `event.post_skipped_test_mode`, `event.post_archived`, `event.retag_failed`.
> ⚠️ `events_review_mode` ships **room** and the forum key is blank, so every path here is
> unreachable until the owner makes the forum and flips the mode. Before that:
> **2026-09-17 (Errors — every failure on the site's Logs page, and a Try again that keeps the
> member's place, branch `errors` off `e7093d7`; design `info/errors-design.md`; ⚠️ BUILT, NOT
> MERGED, NOT DEPLOYED, nothing has met Discord):** schema **unchanged** — no migration and no
> backfill. Registry keys **+4**, all under `core` through `CORE_KEYS` (`error_sentence` text,
> `error_retry_label` text **Try again**, `error_retry_minutes` int 1–30 **10**,
> `error_retry_expired` text) — `namespace_of` would otherwise have invented an `error` group and
> `settings_panel.groups()` is at Discord's cap of 25. ⚠️ **No new module** — `command_errors.py`
> grows `record()`, `offer()` and `RetryView`, and `panels.Panel` grows an `again` move with a
> `render_again` property. **One new log-kind family: `error.command` / `error.panel` /
> `error.modal` / `error.button`, all IMPORTANT, under `HEADS["error"] = "core"`** — the first
> family whose rows are written by the error handler rather than by a feature, so the site's Logs
> page can show staff a failure nobody reported. Row details are `where` / `error` / `message`
> (truncated to 200, an `HTTPException` reduced to Discord's own code + text) / `step` (the
> innermost `black_bloc/**` frame) / `interaction` (a command name or a custom id) and ⚠️ **never
> a member's words**. The Logs page gains one `LOG_FEATURES` entry that narrows by the `error.`
> KIND prefix rather than by feature; `site/mock` and `contract.json` mirror the four keys. Tests
> **6456 → 6479**.
>
> **2026-09-17 (Send to… — staff hand-offs between requests, events and modmail tickets, branch
> `send-to` off `8a27840`; ⚠️ BUILT, NOT MERGED, NOT DEPLOYED, nothing has met Discord):**
> schema **42 → 43** (measured: `SCHEMA_VERSION`) — `requests.moved_to`, `events.moved_to` and
> `modmail_tickets.moved_to`, all `TEXT` and all NULL, through the additive `ADDED_COLUMNS` /
> PRAGMA pattern, no backfill. ⚠️ **Migrate before deploy.** Registry keys **254 → 256**
> (`handoff_mode` enum off/on **on**, `handoff_confirm_hours` int 1–168 **24** — both filed under
> the `request` namespace through `NAMESPACE_OVERRIDE`, because `settings_panel.groups()` is at
> Discord's cap of 25 and a 26th would be silently dropped off `/settings`); mock **19 pages, 180
> routes**, 15 core settings (no new route — `moved_to` / `moved_word` join the existing request
> and event rows). ⚠️ **One new module, `black_bloc/handoff.py`** — the trail vocabulary, the
> wording, the refusals and the five moves, with every cog import function-local so the requests
> cog can import it back. `requests.STATUSES` gains a final **`moved`** (no transition reaches it,
> so only a hand-off writes it) with a seventh forum tag; `events.CANCEL_WHY` gains `handed_off`;
> `modmail.card_buttons` gains two moves behind a member's DM'd confirmation whose wording lives
> in the confirm embed itself. Log kinds: five `handoff.<from>_to_<to>` (IMPORTANT) plus
> `handoff.asked` / `handoff.refused` (ROUTINE), all under `HEADS["handoff"] = "request"`; tests
> **6304 → 6404**. Before that:
>
> **2026-09-17 (Blackmail — modmail and requests as FORUM channels, and the ticket button under the rules, branch `blackmail-threads` off `905982b`; ⚠️ BUILT, NOT MERGED, NOT DEPLOYED, nothing has met Discord):**
> schema **40 → 41** (measured: `SCHEMA_VERSION`) — `requests` gains `thread_id INTEGER` through the
> additive `ADDED_COLUMNS` / PRAGMA pattern, no backfill. ⚠️ **The number is written as though the
> polls build has already taken 40**; if that build does not land, `black_bloc/storage/db.py:11` and
> `tests/storage/test_db.py:16` are the two lines that carry it. Registry keys **227 → 231**
> (`modmail_forum_channel_id` channel blank, `modmail_forum_tags` bool **true**,
> `modmail_panel_follows_post` text **`welcome`** / `none`, `request_forum_channel_id` channel blank);
> mock **19 pages, 175 → 177 routes**, 14 core settings (`POST /api/modmail/forum`,
> `POST /api/requests/forum`). ⚠️ **No new module.** `modmail_mode` gains a third value, **`forum`**,
> under which a ticket is a post made by `ForumChannel.create_thread` (a `ThreadWithMessage` in
> discord.py 2.7.1 — measured off the installed library) and the whole existing thread path carries
> every reply, note, close and transcript. Tags are `ForumTag` objects looked up **by name** on the
> forum's own `available_tags`, never by a stored id. Setup on `/modmail` gains **Forum channel…** and
> **Make the forum**; `/request`'s panel and both dashboard pages gain the same **Make the forum**.
> Under `TEST_MODE` a forum is made outside the test category (creation is not something the guard
> sees, and the reply says so) and the guard CLAIMS it — the modmail sweep re-claims it every five
> minutes while `modmail_mode` is `forum`, because a claim dies with the process that made it. New
> log kinds: `modmail.forum_made` / `.forum_failed` / `.forum_forgotten` / `.panel_below_post`, and
> `request.forum_made` / `.forum_failed` / `.forum_forgotten`. Tests **5998 → 6058**, both orders.
> Before that:
>
> **2026-09-11 (Event rooms — the event's posts live in its own room and staff get a Delete button, branch `event-rooms` off `bd0b31d`; ⚠️ BUILT, NOT MERGED, NOT DEPLOYED, nothing has met Discord):**
> schema **unchanged at 34** — no migration and no backfill; registry keys **202 → 206** (`events_posts_where` enum room/announce/both default **room**, `events_room_delete_who` enum staff/approver default **staff**, `events_approver_role_id` role blank→staff, `events_room_notice` bool **true** — all events group by prefix); mock routes **150 → 151** (`POST /api/events/{event_id}/room/delete`). ⚠️ **No new module.** `make_review_channel` now calls `guard.own_channel`, which is the whole reason the posts move: the room joins the guard's owned set, so `card_channel` stops redirecting the review card to the test channel and the new `events.post_to_room` may speak there — `TEST_MODE` itself is untouched and still refuses every channel Black Bloc did not make. `events.post_event` fans the announce and go-live posts out over the two doors, and the room additionally gets the ended, cancelled and denied lines; only the announce channel's message id is stored (the room is deleted with the event). `events.delete_room` is the one canonical removal, reached from the persistent **Delete this room** button (`DECISION_TEMPLATE` grew a third action) and from the website route with `via=VIA_WEBSITE`; it cancels an open event FIRST so `on_guild_channel_delete` cannot settle it twice, and it cannot hold `event_lock` because `cancel_event` takes that same non-reentrant lock. Reconcile re-owns every room it can still see and `forget_room` clears a swept row's dead `review_channel_id` once (`event.room_forgotten`, TODO finding (h)). Five new log kinds by shape (`event.*_room`, `event.would_*_room`, `event.*_room_failed`) plus `event.room_forgotten`, `event.room_notice_failed`, `event.room_delete_failed`; tests **5546 → 5593**. Before that:
>
> **2026-09-11 (Where follow-up 4 — a shorthand becomes a link and the link is tried first, ✅ LIVE v108 00:37, merge `73e2e44` of `where-smart`):**
> schema **unchanged at 34** — no migration and no backfill; registry keys **199 → 202** (`events_where_link_aliases` text with a `where_alias_table` checker, `events_where_link_check` enum off/warn/refuse default **warn**, `events_where_link_check_seconds` int 1–3 default **2** — all events group by prefix); mock routes unchanged at **150**; ⚠️ **one new module, `black_bloc/linkcheck.py`** — the first outbound HTTP in the events path, `LINK_OK` / `LINK_MISSING` / `LINK_UNREACHABLE` from one GET with a browser UA, redirects followed and the body never read, with `fetch` injected the `groq.py` way so no test reaches the network. `events.where_link` also learns bare hosts (render-time, so rows stored before this build become links with no migration) and the new `events.where_typed` turns `ttv/skyaiva` / `yt @skyaiva` into the href at ENTRY, in `WhereModal.on_submit` and in the website's `checked_where`. `EventDraft.where_note` carries a warn-mode note on the draft's Where line only — never on the row, the card or the announcement; no new log kind (the check logs at `debug`); tests **5502 → 5546**. Before that:

> **2026-09-10 (Where follow-ups 2+3 — a typed link looks like a link, test rooms go in minutes, branch `where-links` off `8adbc75`, merged `ac43a20`, ✅ LIVE v107 23:41):**
> schema **unchanged at 34** — no migration; registry keys **198 → 199** (`events_test_retention_minutes`, int, events group by prefix, default 5, 1–1440; read only while `bot.guard is not None`); mock routes unchanged at **150**; no new module and no new log kind — `events.where_link` / `where_shown` / `where_line(linked=)` render a typed http(s) location as a masked link on the draft and the card, `cogs/community/events.add_open_link` adds a `ButtonStyle.link` **Open link** button to the review card only (the draft never gets it: Submit takes the row's fifth slot), `knowledge.event_where` and the scheduled event's description keep the bare url, and `events.swept_anchor` counts a DENIED / CANCELLED room from `decided_at` (then `ends_at`, then `created_at`); tests **5473 → 5502**. Before that:
> **2026-09-10 (the Where follow-up — a channel AND a link, branch `where-link` off `ebe0ead`, merged `6c10b9d`, ✅ LIVE v106 17:41):**
> schema **unchanged at 34** (measured: `SCHEMA_VERSION`) — no migration and no backfill, because `location`
> already existed and simply now carries the typed link for the two channel kinds as well as the place for
> `other`; registry keys **197 → 198** (measured: `len(KEY_TYPES)` — `events_where_link_in_description`, a bool
> filed in the `events` group by prefix, so **23** groups still); mock routes unchanged at **150** (checked:
> *17 pages, 150 routes, 14 core settings, all keys present*); no new module and no new log kind — the append
> is `events.described_with_where`, read once inside `create_scheduled_event`; tests **5453 → 5473**. Before
> that:
> **2026-09-10 (the "Where?" picker, merge `3205c0f`, v105 17:09):**
> schema **33 → 34** (measured: `SCHEMA_VERSION`) — `events` gains `where_kind TEXT` and
> `where_channel_id INTEGER`, both nullable, both `ALTER TABLE` entries in `ADDED_COLUMNS`, no backfill
> (a row with a `location` and no kind already reads as the `other` kind); registry keys **unchanged** —
> the design says there is nothing to decide, so no group count moved either; mock routes unchanged at
> **150**; no new module (the `Where` type and its readers live in `black_bloc/events.py`, the panel in
> `cogs/community/events.py`); one new log kind `event.where_channel_gone`; tests **5403 → 5453**. Before that:
> **2026-09-10 (the raid train's calendar name, branch `raidtrain-name`):** schema unchanged at **33**;
> registry keys **196 → 197** (measured: `len(KEY_TYPES)` — `raidtrain_scheduled_name_template`, filed in the
> `raidtrain` group by prefix, so **23** groups still); mock routes unchanged at **150**; no new module —
> `events.scheduled_name` grew a `fallback=` keyword so raid trains fall back to the plain title rather than
> to the events wording; tests **5395 → 5403**. Before that:
> **2026-09-10 (the "When?" picker `1f35f28`, v100):** schema unchanged at **33** (measured: `SCHEMA_VERSION`); registry
> keys **191 → 196** (measured: `len(KEY_TYPES)` — `default_timezone`, `timezone_choices`, `time_step_minutes`,
> `events_default_minutes`, `events_scheduled_name_template`, all filed in the `events` group by `NAMESPACE_OVERRIDE`,
> so **23** groups still); mock routes unchanged at **150**; new leaf module `black_bloc/when_picker.py` (the shared
> Day/Hour/Minute/Duration selects, `WhenDraft`, `ZonePanel`), used by `cogs/community/events.py` and
> `cogs/content/raidtrain.py`; `EventModal`, `TrainModal`, `Events.submit` gone; tests **5286 → 5395**. Before that:
> **2026-09-06 (loop guard `689eff5`, v97; operator bucket `deaae68`, v98; operator read bound `88e0242`, v99):**
> schema unchanged at **33**; registry keys unchanged at **191**; mock routes unchanged at **150**; new leaf module
> `black_bloc/loops.py` (`wait_ready`, called by all fourteen `before_loop`s); `auth.py:operator_session` reorders
> compare-then-bucket (v98) and then charges the shared 300/min read bucket on the operator identity (v99) — the
> read-bucket names and `_bucket` now live in `auth.py`, `writes.py` re-exports them; tests **5267 → 5277 → 5279 →
> 5286**; `tests/live/` green against v98 and v99 (58 passed / 1 skipped — the count lives in
> `../access/testing.md`, which owns it). Before that:
> **2026-09-06 (logs buttons `42d2e6e` + recurrence create from the website `c915ade`, v96):** schema unchanged at **33**; registry keys **189 → 191** (`logs_count`, `logs_important_only` — a new `logs` group, **23** groups); mock routes **149 → 150** (`POST /api/polls/recurrences`); new module `black_bloc/logs_panel.py`; tests **5226 → 5267**. Before that:
> **2026-09-06 (saved poll drafts, merged `8405bea`, v94):** schema **32 → 33** (`poll_drafts`)
> and registry keys **187 → 189** (`poll_drafts`, `poll_draft_days`), both re-measured by
> importing them. Nothing else in this table moved — no cog, no command, no feature, and the
> mock still reads 17 pages / 149 routes / 14 core settings.
>
> **2026-09-17 (MEETING MINUTES — the prototype, branch `minutes` off `d739726`; ✅ MERGED `41a9f26`, LIVE as v132 `82c3467` 18:32; nothing has met Discord — `minutes_mode` ships **off**):**
> cogs **21 → 22** (`cogs/community/minutes.py`), top-level slash commands **31 → 32**
> (`/minutes`, staff-locked and `HIDDEN_WHEN_OFF`), schema **43 → 44** (measured:
> `SCHEMA_VERSION`) — `meetings` and `meeting_lines`, new tables through the `SCHEMA`
> bootstrap, with a PARTIAL UNIQUE INDEX `meetings_one_open ON meetings(guild_id) WHERE
> ended_at IS NULL` so one guild can only have one meeting open. ⚠️ **Migrate before
> deploy.** Registry keys **262 → 273** (ten `minutes_*` plus `minutes_log_level`), features
> **20 → 21**, setting groups **still 25** — every minutes key is `NAMESPACE_OVERRIDE`'d onto
> **`events`**, because `settings_panel.groups()` is at Discord's cap of 25 and a 26th would be
> silently dropped off `/settings`; `events` therefore reaches **33** keys and joins `chat` and
> `modmail` as a group with a **Find…** path. Mock **19 → 20 pages, 180 → 186 routes**, 17
> core settings. ⚠️ **Four new modules:** `black_bloc/minutes_audio.py` (the pure sink —
> per-speaker 48 kHz stereo PCM in, one 16 kHz mono WAV per speaker per
> `minutes_chunk_seconds` out, audio dropped the moment a chunk is handed off),
> `black_bloc/minutes.py` (the refusals, the transcript, the notes, the staff moves),
> `black_bloc/minutes_session.py` (one meeting's runtime: the queue, the Whisper worker, how it
> ends) and `black_bloc/api/tools/minutes.py`; plus `site/public/minutes.html` +
> `assets/page-minutes.js`. `groq.py` gains `WhisperClient`. **The image gained `libopus0`**
> (`Dockerfile`) and the package gained `discord.py[voice]` + `discord-ext-voice-recv`; see
> [`minutes-design.md`](minutes-design.md) § Deviations for why ffmpeg was NOT added. Log
> kinds: twelve `minutes.*`, four of them with a `web.` spelling.
>
> | What | v148 (`main`, 2026-09-20) | Where it is measured |
> |---|---|---|
> | Cogs | **23** (`cogs/content/spotlight.py` at v148; 22 at v132 `minutes`; 21 at v125) | `bot.py:COGS` |
> | Top-level slash commands | **33** — 17 staff-locked, 16 member-visible (`/test` at v146; `/minutes` at v132; `/ask` at v125; `/modmail` became member-visible at v114). ⚠️ **33 on branch `selftest-boot`** — 17 staff-locked once `/test` lands (`info/selftest-design.md` §K, 2026-09-20); NOT merged, so `main` still reads 32 | `tree.get_commands()`, pinned by `tests/test_bot.py:TOP_LEVEL_NOW` |
> | `app_commands.Group`s | **0** | ⚠️ every group retired by the panel waves |
> | Schema version | **48** (v148, the three `spotlight_*` tables; 47 at v146 `selftest_runs.keep_minutes`, 46 at v143). ⚠️ **49 on branch `posts-versions`** | `storage/db.py:SCHEMA_VERSION` |
> | Registry keys | **290** on `main` at v148 (nine `spotlight_*`, all in the golive group, which passed the 25-cap and gained the Find box; 281 at v143) — **25 namespaces**. ⚠️ **292 on branch `posts-versions`** (`posts_versions_keep`, `posts_versions_summary_chars`, both in the posts group) | `len(settings_store.KEY_TYPES)` |
> | Setting groups | **25** — the `/settings` group select's cap; the next namespace needs a `Find…` path | `settings_store.namespace_of` over `KEY_TYPES` |
> | Features (log-level keys) | **21** (minutes v132, guides v111, posts v113) | `settings_store.FEATURES` == `logkinds.FEATURES` |
> | Mock contract | **20 pages / 186 routes / 24 core settings** — measured on branch `youtube-uploads-removal`, which is **v139** and merged (187 on `main` at v138, minus `GET /api/youtube/videos`) (21 core at v133) (17/150 at v108; was 149 routes at v92). ⚠️ **Not re-run 2026-09-19** — `check.mjs` needs `server.mjs` listening; `ls site/public/*.html` was re-counted off disk and is **20** | `node site/mock/check.mjs` — last RUN **2026-09-20 on branch `posts-versions`**, port 8796: `check: ok - 20 pages, 192 routes, 24 core settings, all keys present`. ⚠️ That 192 is the BRANCH's (`main` is 190): `POST /api/posts/{slug}/reset` is gone and the three `…/versions…` routes arrived |
> | Tests | **6920** (+3 skipped where the receive extension is absent — **KI-31**). ⚠️ **6950 on branch `posts-versions`**, both orders | the v148 deploy gate |
> | Deploys | **147** lines, last `f73d3a7` (v148) at 2026-09-20 18:23 | `../deploys.log` |
>
> ⚠️ **The command count is the figure that has been wrong most often, and the reason is that
> it FELL.** The panel waves (owner rule, 2026-09-03: one command per feature opens a panel)
> retired every `app_commands.Group` and every sub-command with it, so a doc quoting a
> pre-panel figure reads as *more* commands than exist. The only trustworthy number is
> `tests/test_bot.py:TOP_LEVEL_NOW`, which the suite asserts on every run.
>
> **How the counts moved** — one row per reading, so a stale figure is visible as history
> rather than as a competing claim. Everything before v92 was measured on the branch named,
> not on `main`:
>
> | Reading | Cogs | Commands | Schema | Routes | Tests |
> |---|---|---|---|---|---|
> | Phase 16 branch | 16 | 39 | 22 | 116 | 2865 |
> | Phase 18 branch | 17 | 41 | 24 | 123 | — |
> | Phase 19 branch | 17 | 41 | 25 | 126 | — |
> | 17→18→19 on `main`, 2026-09-03 | 19 | 44 | 25 | 136 | 3238 |
> | Phase 15 (F14) branch, 2026-09-02 | 15 | 37 | 21 | 111 | 2714 |
> | v92 `6af0ba0`, 2026-09-05 | 19 | 29 | 32 | 149 | 5186 |
> | **v148 `f73d3a7`, 2026-09-20** | **23** | **33** | **48** | **190** | **6920** |
> | **v147 `32ec6a4`, 2026-09-20** | **22** | **33** | **47** | **186** | **6818** |
> | **v146 `6652b25`, 2026-09-20** | **22** | **33** | **47** | **186** | **6818** |
> | **v145 `ac7b1a1`, 2026-09-20** | **22** | **32** | **46** | **186** | **6800** |
> | **v144 `c18f2cd`, 2026-09-20** | **22** | **32** | **46** | **186** | **6800** |
> | **v143 `84e33fa`, 2026-09-20** | **22** | **32** | **46** | **186** | **6800** |
> | **v142 `6a6f8e4`, 2026-09-20** | **22** | **32** | **45** | **186** | **6757** |
> | **v141 `2e48d7c`, 2026-09-18** | **22** | **32** | **45** | **186** | **6757** |
> | **v140 `413f939`, 2026-09-18** | **22** | **32** | **45** | **186** | **6720** |
> | **v139 `fad4e50`, 2026-09-18** | **22** | **32** | **45** | **186** | **6720** |
> | **v138 `9e2298c`, 2026-09-17** | **22** | **32** | **45** | **187** | **6808** |
> | **v137 `a16f5e5`, 2026-09-17** | **22** | **32** | **45** | **187** | **6793** |
> | **v136 `bb94a92`, 2026-09-17** | **22** | **32** | **45** | **187** | **6755** |
> | **v135 `2dd8fcd`, 2026-09-17** | **22** | **32** | **44** | **186** | **6696** |
> | **v134 `79fcef8`, 2026-09-17** | **22** | **32** | **44** | **186** | **6689** |
> | **v133 `b20e4dc`, 2026-09-17** | **22** | **32** | **44** | **186** | **6670** |
> | **v132 `82c3467`, 2026-09-17** | **22** | **32** | **44** | **186** | **6649** |
> | **v131 `709defe`, 2026-09-17** | **21** | **31** | **43** | **180** | **6479** |
> | **v130 `d739726`, 2026-09-17** | **21** | **31** | **43** | **180** | **6456** |
> | **v129 `60958ec`, 2026-09-17** | **21** | **31** | **43** | **180** | **6455** |
> | **v128 `a0fa7f3`, 2026-09-17** | **21** | **31** | **43** | **180** | **6406** |
> | **v127 `de91282`, 2026-09-17** | **21** | **31** | **42** | **180** | **6305** |
> | **v126 `e537b2c`, 2026-09-17** | **21** | **31** | **42** | **180** | **6304** |
> | **v125 `e8042a5`, 2026-09-17** | **21** | **31** | **42** | **180** | **6247** |
> | **v124 `9733d69`, 2026-09-17** | **20** | **30** | **42** | **178** | **6166** |
> | **v123 `2f1c609`, 2026-09-17** | **20** | **30** | **42** | **178** | **6223** |
> | **v122 `672c608`, 2026-09-17** | **20** | **30** | **41** | **178** | **6196** |
> | **v121 `9f003d5`, 2026-09-17** | **20** | **30** | **41** | **178** | **6175** |
> | **v120 `768f76a`, 2026-09-17** | **20** | **30** | **41** | **178** | **6144** |
> | **v119 `8040a81`, 2026-09-17** | **20** | **30** | **41** | **178** | **6144** |
> | **v118 `3fe05ef`, 2026-09-17** | **20** | **30** | **40** | **176** | **6086** |
> | **v117 `7d5d6ad`, 2026-09-17** | **20** | **30** | **39** | **176** | **6037** |
> | **v116 `29c77b6`, 2026-09-17** | **20** | **30** | **39** | **175** | **5986** |
> | **v115 `64b69ce`, 2026-09-16** | **20** | **30** | **38** | **171** | **5889** |
> | **v114 `c279676`, 2026-09-16** | **20** | **30** | **38** | **170** | **5880** |
> | **v113 `4d60f68`, 2026-09-16** | **20** | **30** | **37** | **168** | **5833** |
> | **v111 `67aee7e`, 2026-09-16** | **19** | **29** | **35** | **160** | **5703** |
> | **v108 `73e2e44`, 2026-09-11** | **19** | **29** | **34** | **150** | **5546** |
>
> ⚠️ **NOT verified today:** the *prose* below the tree (the rules, the library table, the API
> section) was not re-traced to the code; the Shape tree's per-file annotations (last verified
> 2026-08-31); and nothing here was checked against the running bot or a browser. What is
> shipped but never exercised by a person is tracked per feature in
> [`../access/sweeps.md`](../access/sweeps.md) — that file is the one home for "shipped but
> never clicked", and this header must not grow a second copy.
>
> 📦 **The five stacked per-branch paragraphs this header used to carry, and the historical
> build-order narrative under them, are archived whole at
> [`../archive/architecture-header-2026-09-05.md`](../archive/architecture-header-2026-09-05.md)**
> with a retirement banner. They contradicted each other and the repo; the table above is what
> replaced them.

## Shape

```
black_bloc/
├── app.py            ← THE RUN BUTTON. Settings → logging → bot → run. Nothing else, ever.
├── errors.py         ← exit-code policy (2 config, 3 login/intents) + the asyncio run loop
├── bot.py            ← BlackBlocBot lifecycle ONLY: __init__, setup_hook, close, on_ready + COGS
├── intents.py        ← build_intents(): the three privileged intents
├── invite.py         ← INVITE_PERMISSIONS + invite_url(bot)
├── command_sync.py   ← sync_dev_guild(): dev-guild slash-command sync, 403 handling
├── command_errors.py ← the tree error handler: any unhandled slash-command failure answers with a
│                       sentence — plus `record()` / `offer()` / `RetryView` (v131), which write
│                       the IMPORTANT `error.command|panel|modal|button` row and put **Try again**
│                       under it. ⚠️ `record` never raises, and never carries a member's words
├── guard.py          ← TestModeGuard: the TEST_MODE gate (send + edit HTTP layer, interaction_check)
│                     └ `allows_place` also allows a channel Black Bloc MADE (v117, 2026-09-17)
│                     └ `rehearse_in` allows the rehearsal home too (v129, 2026-09-17)
│                     └ ⚠️ NOT INSTALLED IN PRODUCTION since 2026-09-18 16:08 — `bot.py:71` only
│                       builds it when `settings.test_mode`, so `bot.guard` is None on Fly.
│                       The module stays for a future rehearsal; `.env.example` still ships
│                       TEST_MODE=true, so a LOCAL run is still guarded
├── shadow.py         ← the rehearsal home: `channel_id` (shadow_channel_id, else the guard's
│                       channel, else log_channel_id) and `channel_ids` — where a *_mode=shadow
│                       copy goes now that the guard is gone (v129)
├── posted.py         ← one posted-and-kept-current message: the post/edit/take-down path the
│                       front door and the ticket button share, and `duplicates_near`, which
│                       reads the last five minutes and logs `*.duplicate_seen` rather than
│                       posting a third (v141 — never deletes, fails open)
├── frontdoor.py      ← the pure half of the front door: the three-button embed, the wording
│                       keys, off/shadow/on (v125, shadow added v141)
├── spawned.py        ← the staff allow every channel Black Bloc makes carries (v121)
├── posts.py          ← the welcome/rules message: the row, the hash, the shadow copy (v113)
├── forums.py         ← the forum helpers requests AND events share — `tag_named`, `forum_tags`,
│                       `forum_overwrites`, AUTO_ARCHIVE_MINUTES (v136). One home, two callers
├── handoff.py        ← Send to…: the request/event/ticket hand-off trail, wording, refusals (v128)
├── guides.py         ← the guide rows, steps, faults, facts and media behind guides.html (v111)
├── minutes.py        ← meeting minutes: the refusals, the transcript, the notes, the staff moves
├── minutes_audio.py  ← the voice-receive sink: per-speaker 48 kHz stereo in, 16 kHz mono WAV out.
│                       ⚠️ the ONLY importer of the pre-release extension, and never at module
│                       level — KI-31
├── minutes_session.py ← one meeting's runtime: the queue, the Whisper worker, how it ends
├── pings_onboarding.py ← the two Community onboarding prompts the bot keeps in step (v116)
├── config.py         ← Settings (pydantic-settings). THE ONLY reader of the environment / .env
├── settings_store.py ← per-guild settings on SQLite + the staff check. The ONLY way features read config
├── actionlog.py      ← log_action(): one DB row always, one embed to the log channel when it can
├── twitch.py         ← Helix client: app token, get_streams, get_users. HTTP is injectable, so tests are offline
├── golive.py         ← pure go-live logic: extract_stream, render, should_announce, role filters
├── youtube_live.py   ← pure live-detection logic: the /live page parser ("isLive" + the canonical
│                      watch id), the videos.list confirm parser, the miss counter, the StreamInfo
│                      the go-live path is handed (v126, `info/youtube-live-design.md`)
├── timezones.py      ← per-member zone store, the autocomplete filter, HammerTime stamps
├── events.py         ← pure event logic: slugs, durations, the status machine, the one card
├── birthdays.py      ← pure birthday logic: local midnight, ages, the colour, the import matcher
├── modmail.py        ← pure modmail logic: the topic, the three embeds, the transcript, the byte-safe cut
├── automod.py        ← pure rule engine: the rule book, the windows, the verdict
├── modcases.py       ← the shared mod-case store: the row, the one card, the DM policy, the modlog post
├── presence.py       ← the bot's own face: the About Me (application description) and the
│                       "Cookout attendees: N" custom status. Pure formatters + two appliers
├── polls.py          ← F15: pure poll logic — kinds, date slots, the close/reminder clock, results
├── requests.py       ← F18: pure request logic — the status machine, auto-approval, the card
├── chat.py           ← F10: @-mention intent classification and the reply, one seam: reply_for()
├── chat_data.py      ← the data intents behind chat (live / next / birthdays / count / roles / tz)
├── pings.py          ← F14: the opt-in ping roles — the fan-role store, the Events-role set-up,
│                       the 25-per-menu Streamer pings panels, and the one role add/remove wrapper
├── rolegrants.py     ← F16/Phase 9: time-limited role grants and the expiry/reconcile logic
├── rolemenu_panels.py ← posting and un-posting role-menu panels when rolemenu_mode flips
├── command_visibility.py ← hides a feature's slash commands while the feature is off (re-syncs)
├── logkinds.py       ← ⚠️ THE ONE HOME for log-kind classification: important vs routine, and
│                       `via_of()` (Discord vs website) which stamps every action-log row
├── emoji.py          ← skin-tone application for the bot's own emoji (emoji_skin_tone)
├── prefix.py         ← no_prefix_commands: the bot answers no text prefix (slash only)
├── panels.py         ← ⚠️ THE PANEL LIBRARY every feature's one command opens (wave 0 of the
│                       panels program): Panel, retire, answer, still_staff, still_allowed,
│                       db_ready, capped_placeholder, panel_minutes, confirm, opened, KEEP_IT,
│                       NoteModal. A panel that re-implements one of these is the bug
├── logs_panel.py     ← the Logs button's list + its Show more / Important only knobs
├── settings_panel.py ← the pure half of /settings: the groups, the typed key cards, the editors
├── selftest.py       ← the self-test registry (config · panel · read · send) and run()/purge
├── selftest_panels.py ← the Discord half of the self-test: the panel and its cards
├── when_picker.py    ← the shared Day/Hour/Minute/How-long selects, WhenDraft, ZonePanel
├── linkcheck.py      ← ⚠️ the ONLY outbound HTTP in the events path: one bounded GET that tries
│                       a typed link before it is kept (LINK_OK / MISSING / UNREACHABLE)
├── loops.py          ← two things. `wait_ready`, behind every `before_loop` so a failure reaches
│                       `@loop.error` (KI-24, v97) — and `Reconciler` (v141): one asyncio.Lock per
│                       cog with the state read INSIDE it, `skip_if_recent` on the `on_ready` path
│                       only. ⚠️ A reconcile that POSTS must go through it — checklist item 37,
│                       traced to the boot that doubled the front door at the TEST_MODE lift
├── applications.py   ← Phase 19: pure application logic — the forms, the statuses, the roster
├── raidtrain.py      ← Phase 18: pure train logic — slots, claims, the lineup, the reminder clock
├── rolemenus.py      ← F16: pure role-menu logic, shared by the cog and the website
├── honeypot.py       ← F9: pure trap logic (built at the /honeypot panel; neither existed before)
├── tempvoice.py      ← F8: the temp-voice state machine and the owner control-post button table
├── chat_memory.py    ← Phase 17: the profile store and the opt-out list
├── chat_distil.py    ← Phase 17: the hourly distillation — never on the reply path
├── chat_check.py     ← the chat door: cooldown, mode, manners, the spend fuses
├── chat_panel.py     ← the pure half of /chat: Personality, Knowledge, Settings
├── chat_llm.py       ← the model ladder and the spend ledger (microdollars, month_start)
├── llm.py / groq.py  ← the two clients. HTTP injectable, so no test reaches the network
├── knowledge.py      ← GABI-style knowledge ingestion + lexical search behind chat
├── personas.py       ← the voice stack: roster, graph, drift constants, the shared clauses,
│                       fed by personality_pool.json (synced from catalog-platform)
├── directory.py      ← the channel directory the chat prompt gets: the visible-channel list,
│                       the hidden/archive categories, and the "name no channel at all" fallback
├── dbsnapshot.py     ← a consistent snapshot of the live database, for the nightly backup pull
├── personality_pool.json ← the SKELETON shared with GABI (see personality-pool-design.md)
├── data/             ← shipped package data (`pyproject.toml` → package-data)
│   └── birthday_import_2026-08-05.json  ← the 39-row Birthday Bot export, seed for the daily import loop
├── logging_setup.py
├── cogs/
│   ├── core.py       ← /ping, /about, /help, /settings — always loaded
│   ├── presence.py   ← the About Me on `on_ready`, the member-count status (10-min loop +
│   │                   a 5-second debounce on join/leave), /presence apply
│   ├── community/    ← one cog per community feature
│   │   ├── role_menus.py  ← F16: /rolemenu + persistent select panels + staff assign + approvals
│   │   ├── tempvoice.py   ← F8: join-to-create voice channels, the owner control post, and
│   │   │                    /voice — ONE command, one panel (both groups retired). The pure
│   │   │                    state machine and button table live in `black_bloc/tempvoice.py`
│   │   ├── events.py      ← F4/F5: /event — ONE command, one panel (the `timezone` group is
│   │   │                    retired); review channels, Approve/Deny, go-live. The shared DB
│   │   │                    and move layer lives in `black_bloc/events.py`, not here
│   │   ├── birthdays.py   ← F6: the five-minute sweep, the /birthday panel, the day role, the daily import
│   │   ├── polls.py       ← F15: /poll on native Discord polls + Black Bloc's own panel, /poll recur
│   │   ├── requests.py    ← F18: /request, the member intake, the pending-features board
│   │   ├── frontdoor.py   ← the posted front door + /ask (v125): three buttons onto the ticket,
│   │   │                    request and event flows. Its reconcile goes through
│   │   │                    `loops.Reconciler` (v141). `frontdoor_mode` off/shadow/on
│   │   ├── posts.py       ← the welcome/rules message and /posts (v113); `posts_mode` shadow
│   │   ├── minutes.py     ← the meeting-minutes prototype and /minutes (v132). ⚠️ ships OFF
│   │   │                    (`minutes_mode`), staff-only, and the command is hidden
│   │   └── applications.py ← Phase 19: /apply — ONE command, one panel (both groups retired);
│   │                        the forms, the queue, approve/deny/remove, the roster
│   ├── moderation/   ← one cog per moderation feature
│   │   ├── honeypot.py    ← F9: the trap channel, delete + ban, shadow first
│   │   ├── modmail.py     ← F11: inbound DM → ticket channel or private thread, the /modmail panel, the sticky ticket card, /reply, transcript
│   │   ├── automod.py     ← F7: the message listener, the Apply-now button, /automod
│   │   └── modcmds.py     ← F7: /warn /timeout /untimeout /kick /ban /unban /purge + the /mod panel
│   └── content/      ← one cog per content feature
│       ├── golive.py ← F1/F2: presence listener, Twitch poller, the /golive panel
│       ├── chat.py   ← F10: the @-mention listener, cooldown, modmail routing, /chat
│       ├── pings.py  ← F14: /pings — ONE command, one ephemeral panel (wave 2). Member half:
│       │                follow/stop-following selects, the Events toggle(s), the fan button.
│       │                Staff half: Streamers…, Set up the Events role, Settings, Logs
│       ├── chat_memory.py ← Phase 17: the hourly distillation sweep and /memory — ONE command,
│       │                    one member panel. The pure half is `chat_distil.py`
│       ├── raidtrain.py ← Phase 18: /raidtrain — ONE command, one panel (both slots retired);
│       │                  slots, claims, the lineup post, the 30-minute reminder DM
│       └── youtube.py ← F3: the channel LINKS and /youtube, ONE command that opens a panel for
│                        members and staff alike (2026-09-03; /uploads is retired), plus the
│                        LIVE probe (v126) — its only loop reads each linked channel's /live
│                        page and calls the go-live cog's go_live/end_live with
│                        source=youtube, so the announcement is go-live's, not its own.
│                        YOUTUBE_API_KEY is optional (it names the live video and resolves
│                        an @handle). ⚠️ The UPLOADS half was removed 2026-09-18 —
│                        `info/youtube-uploads-removal-design.md`
├── storage/db.py     ← aiosqlite connection + schema bootstrap (SCHEMA_VERSION **45** on `main`,
│                       re-imported 2026-09-19 — this said "44 on branch `minutes`", and that
│                       branch shipped as v132 two versions before 45 arrived at v136)
└── api/             ← the dashboard API, one router per surface (API_ENABLED)
    ├── server.py    ← create_app: /health (public), security headers, routers, then site/ at /
    ├── auth.py      ← Discord OAuth2 + the signed session cookie. The site's ONLY gate.
    │                  Also the operator read token and both rate buckets
    ├── sessions.py  ← the signed-cookie session store behind auth.py
    ├── costs.py     ← /api/costs: the chat spend ledger, hosting cost, secret presence (names only)
    ├── selftest_api.py ← /api/selftest — run, list, read one, purge one. The self-test's web door
    ├── status.py    ← /api/status + /api/actions — READ-ONLY, staff-gated
    ├── writes.py    ← THE SHARED WRITE SIDE: staff + one rate-limit bucket per bot, the guard's
    │                  409, the guild/database checks, and the `web.<area>.<verb>` audit line
    ├── names.py     ← the resolver every table uses. CACHE ONLY — no fetch_* call anywhere in it
    ├── ref.py       ← /api/ref/{channels,roles,members,names} — the pickers' data
    ├── settings_api.py ← /api/settings + /api/settings/audit. Owns NAMESPACE_OVERRIDE
    ├── assets.py    ← the cache-busting asset stamp (?v=…) and the no-store headers
    └── tools/       ← ONE ROUTER PER FEATURE TAB; each calls the cog's own plain helpers,
        │              never a second copy of the rule
        ├── mod.py        ← cases, the action bar, the rule book
        ├── modmail.py    ← tickets, replies, closes, snippets, blocks
        ├── events.py     ← the approval queue: approve / deny / cancel
        ├── golive.py     ← links, opt-outs, recent sessions
        ├── youtube.py    ← F3: the channel links and the live probe's own status (the videos
        │                    route went with the uploads half, 2026-09-18)
        ├── pings.py      ← F14: the streamer table, staff create/remove, the Events-role set-up
        ├── rolemenus.py  ← menus, options, post
        ├── birthdays.py  ← the list, set / remove, and the Birthday Bot import
        ├── honeypot.py   ← hits, Ban-now, setup
        ├── tempvoice.py  ← the live channel list, setup / repair
        ├── polls.py      ← the poll list, create, end / cancel, results
        ├── requests.py   ← the requests board + the member-only routes (the one non-staff gate)
        ├── chat.py       ← the editable intents and lines, the manners settings
        ├── chat_memory.py ← Phase 17: the stored preference profiles and the opt-out list
        ├── applications.py ← Phase 19: forms, questions, the queue, approve/deny/remove, the roster
        ├── raidtrain.py  ← Phase 18: trains, slots, claims, the lineup post
        ├── frontdoor.py  ← the Front door card on the modmail page (v125)
        ├── posts.py      ← the Posts page: the body, the preview, Post it / Take it down (v113)
        ├── guides.py     ← the Guides hub: read, edit in place, mark stale, replace a screenshot (v111)
        ├── minutes.py    ← the Minutes page (v132) — like the cog, inert while `minutes_mode` is off
        ├── members.py    ← the Members tab: the roster, roles, grant chips
        └── roles.py      ← timed role grants: list, extend, end now
site/                 ← THE DASHBOARD (8a status page, 8b tabs). Static, no build step, COMMITTED
├── README.md         ← the developer-facing half (committed; `docs/access/site.md` is the runbook)
├── mock/             ← the contract's EXECUTABLE form. Node's own `http`, no dependency
│   ├── server.mjs    ← serves site/public AND /api/* on one origin, as the real deployment does.
│   │                   MOCK_TEST_MODE defaults ON, so refusals are what a developer meets first
│   ├── contract.json ← ⚠️ THE ONE HOME for every route's shape, derived from the pages'
│   │                   own property accesses. Read by BOTH halves of the contract check
│   └── check.mjs     ← fetches every page and every route from the mock and asserts contract.json
└── public/
    ├── index.html    ← Overview; <meta name="api-origin"> is EMPTY = "the origin I came from"
    ├── {moderation,automod,modmail,events,golive,rolemenus,birthdays,tempvoice,honeypot,
    │    polls,chat,requests,members,settings,audit,health,posts,guides,minutes}.html
    │                   ← the other nineteen tabs (**20** pages total, `ls site/public/*.html`
    │                   counted on disk 2026-09-19; this block said 17, the 2026-09-11 reading,
    │                   and missed `posts.html` v113, `guides.html` v111 and `minutes.html`
    │                   v132). Each is an empty shell: #tabnav + #dash, filled by its page
    │                   module. The nav is built from ONE array in app.js, never twenty
    │                   hand-written copies
    └── assets/
        ├── api.js    ← the ONLY fetch. Outage vs refusal, the name cache, the ref caches
        ├── app.js    ← the shell: the tab list, the five permission states, start()/reload()
        ├── ui.js     ← the widgets. createElement + textContent only; nothing assigns innerHTML
        ├── page-*.js ← one module per tab, each exporting nothing and calling start()
        ├── labels.js ← ⚠️ the one home for every settings key's human sentence
        ├── logs.js   ← the shared Logs list every page embeds
        ├── discordmd.js ← the Discord-markdown PREVIEW (v113). Escapes HTML first, never
        │                  emits an anchor. Fixtures: `site/mock/discordmd.test.mjs`
        ├── clipmd.js ← the paste CONVERTER (v140): a Google-Docs rich clipboard → Discord
        │                markdown, a tag tokeniser + tree walk with **no `DOMParser`**, so
        │                `site/mock/clipmd.test.mjs` runs the same code under plain node.
        │                ⚠️ Site only — a Discord modal never sees the clipboard
        ├── shell.js / layout.js / theme.js / palette.js / icons.js / motion.js /
        │   permission-ux.js ← the restyle's shared chrome
        └── site.css  ← ours, beside a SNAPSHOT of the estate theme + fonts
                        (`estate-theme.css`, `status-shell.css`, `fonts/`)
tests/                ← everything runs OFFLINE; no test needs a token or the gateway
└── api/test_contract.py ← runs contract.json against the REAL routers with fakes, so the
                           mock and the bot cannot answer different shapes
```

⚠️ **The two halves of Phase 8b were built blind against
[`phase8b-design.md`](phase8b-design.md) and had never met.** The contract fixes
the JSON only for `/api/ref/*` and `/api/settings`; everywhere else the pages
guessed and the routers guessed, and they disagreed on nine routes. The fix is
`site/mock/contract.json` plus the two checkers that read it — the shape now has
one home, and a page and a router cannot drift apart without one of them going
red. `api.js`'s `listOf()` stays as deliberate slack on top of that.

⚠️ **Option A: one app, one origin, no Cloudflare Pages.** `server.py` mounts
`site/public` with `StaticFiles(html=True)` at `/` **after** the routers, so
`/health` and `/api/*` win and everything else is a file. There is no
`wrangler.toml`, no Pages project and **no CORS middleware** — a same-origin
`fetch` needs none. `SITE_ORIGIN` is the single hostname value (the OAuth
redirect base, where sign-in returns, and whether the cookies get `Secure`);
`SITE_ROOT` is the directory served. See
[`../access/site.md`](../access/site.md).

Two module-level facts worth knowing before adding a feature: config knobs go
through `settings_store.py` (a row in its registry, never a new `.env` field
per feature), and anything a feature does to a member or a channel goes
through `actionlog.py:log_action`. See [`phase1-design.md`](phase1-design.md)
and [`phase2-design.md`](phase2-design.md).

A feature that decides something keeps the decision in a **pure module** and
the Discord plumbing in the cog — `golive.py` next to `cogs/content/golive.py`
is the pattern; `events.py` next to `cogs/community/events.py` repeats it,
`birthdays.py` next to `cogs/community/birthdays.py` repeats it again, and so
does `modmail.py` next to `cogs/moderation/modmail.py`.
It is what lets the announcement wording, the debounce, the role filters, the
channel-name rules and the event status machine be tested with no gateway and
no network.

`tzdata` is a **runtime dependency**, not a convenience: Windows ships no
zone database, so without it `zoneinfo.available_timezones()` is empty and
every zone lookup and every event start fails — `timezones.py:31`'s
`available_timezones()` is what feeds the `My time zone` picker on the `/event` panel (the
`/timezone` command itself retired with the events panel in v64). Pinning it in
`pyproject.toml` makes the Windows developer machine and the Linux container
resolve the same zones from the same data.

The source carries near-zero comments (rule 0 below); the explanations live in
[`code-notes.md`](code-notes.md), keyed by `path:line`.

## The rules that shape it

0. **Near-zero comments in code (owner rule, 2026-08-26).** The source does
   not explain itself in comments; [`code-notes.md`](code-notes.md) does,
   keyed by `path:line`. A comment survives only where the code would
   *mislead* without it (a `type: ignore`, a deliberate no-op), one line.
   Docstrings: one line or none. When you find yourself writing a paragraph
   above a function, it goes in `code-notes.md` with a link to the line.
1. **The entrypoint is a run button (owner rule, 2026-08-26).** `app.py`
   wires settings → logging → bot and starts it; nothing else. `bot.py` is
   lifecycle only (intents, cog list, setup/close). Every behaviour — sync,
   invite URL, error mapping, guards — is its own module with helpers. A
   feature that "just needs a line in app.py" is in the wrong place.
2. **One cog per feature.** A cog is a class in its own module under
   `cogs/community/`, `cogs/moderation/` or `cogs/content/` with `async def setup(bot)`, registered
   by adding its dotted path to `bot.py:COGS`. Cogs talk to the DB through
   `bot.db`, to config through `bot.settings`. Cogs do not import each other;
   shared logic goes in a plain module the cogs both import.
3. **Slash commands first.** `app_commands` are the user surface. The text
   prefix exists for emergencies (works even when command sync is broken).
4. **One config owner.** `config.py` is the only place `os.environ`/`.env` is
   read. Add a field there with a default; document it in `.env.example`.
5. **Schema changes are migrations, not edits.** `storage/db.py:SCHEMA` is
   additive (`CREATE TABLE IF NOT EXISTS`, `CREATE … INDEX IF NOT EXISTS`).
   A **new column** on an existing table is a row in
   `storage/db.py:ADDED_COLUMNS`, applied by `Database.connect` as an
   `ALTER TABLE … ADD COLUMN` guarded by a `PRAGMA table_info` check — never
   a rewrite of a `CREATE TABLE` that has already run somewhere. Neither
   needs a version bump, because both are idempotent on any existing file;
   `SCHEMA_VERSION` moves when a change cannot be expressed that way, and the
   first such change introduces numbered migrations keyed on
   `schema_meta.schema_version`.
   ⚠️ **One exception exists and it is the only one: Phase 6's `mod_cases`
   rebuild** (`storage/db.py:296` and `:306`), which drops the table's two
   indexes, renames it aside, lets the schema script recreate it with a
   nullable `user_id`, copies the rows back and drops the husk. It is NOT a
   numbered migration because it does not need one: it is guarded by a
   `PRAGMA table_info` check that returns immediately when the constraint was
   never there, so it is idempotent on every file including a fresh one. Read
   it as the shape a bounded rewrite must take — guarded, bounded, and
   re-runnable — not as permission to edit a `CREATE TABLE` in place. A change
   that cannot be written this way is still the one that starts numbered
   migrations.
6. **Nothing in tests needs Discord.** Bot construction and cog loading work
   offline (`tests/test_bot.py` proves it). Anything that needs the gateway is
   a manual smoke test in `access/setup.md` §3, labelled as such.
7. **Tests mirror the package, one file per source file (owner rule,
   2026-08-26).** `black_bloc/<path>/<name>.py` ↔ `tests/<path>/test_<name>.py`
   — same folder shape, so a test is always one hop from its subject. No
   flat pile of test files. `conftest.py` stays at `tests/` root. pytest runs
   with `--import-mode=importlib` so same-named test files in different
   folders coexist without `__init__.py` files.
8. **Only bot code is committed (owner rule, 2026-08-26).** Research tooling
   (scans, scrapers, one-off inventories) and their tests never enter git;
   they live under `scripts/scan/` (gitignored).

## Why these libraries

| Choice | Over | Because |
|---|---|---|
| `discord.py` 2.x | hikari, nextcord, pycord | Largest ecosystem, first-party slash commands, cogs = natural feature unit; no estate Python bot to match |
| FastAPI (optional) | Flask | Same asyncio loop as the bot → routes read bot state directly, no thread/IPC. Flask would need both |
| SQLite via aiosqlite | Postgres | One process, one file, no service to run or pay for. Revisit at a second process or real write volume |
| pydantic-settings | hand-rolled `os.environ` | Typed, validated, `.env` for free, one owner |

## How the optional API runs

`bot.setup_hook` creates `start_api(bot)` as a background task on the same
loop; `uvicorn.Server.serve()` is awaited there. `bot.close()` cancels it.
Off by default and localhost-only in `.env`; **on and bound to `0.0.0.0` on
Fly**, where `[http_service]` exposes it. Since Phase 8a it is the config
site's back end: `api/auth.py` gates everything except `/health` behind a
Discord-OAuth session, and `api/status.py` serves the read-only status page.
Being in the bot's own process is what lets a route read live gateway state
and the same SQLite file with no IPC.

⚠️ **`auto_stop_machines`, `auto_start_machines` and `min_machines_running` in
`fly.toml` are load-bearing**, not tuning: the machine that answers HTTP is the
machine holding the outbound gateway websocket, and Fly's default
auto-stop-on-idle would kill it. An idle HTTP service is not an idle bot
([`hosting.md`](hosting.md)).

## Runtime model

One process, one persistent outbound websocket to the Discord gateway. That
single fact decides hosting — see [`hosting.md`](hosting.md).
