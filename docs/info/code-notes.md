# Code notes — the comments the source no longer carries

> Audience: anyone reading the source. Status: TRACKED (owner, 2026-08-31 — was local-only until then). Last verified: **2026-08-27 for the NOTES; the KEYS were re-keyed against `ef8a7a1` on 2026-08-31 — see the line below the owner rule.** The changelog that follows is historical and its dates/counts are left as written. Before that, 2026-08-27 — **the temp-voice control panel now lives in the voice channel’s own text chat** (owner ask, 2026-08-27 10:44: *“also lets move the controls for the join to create from the #test channel into the channel txt of the voice chat that was made like the other bot does it”*) added an owned-channel allowance to `black_bloc/guard.py` (`owned_channel_ids`, `own_channel`, `disown_channel`, `owns_channel`, `is_component`) and its bookkeeping to `black_bloc/cogs/community/tempvoice.py` (`own_channel` / `disown_channel` module helpers wired into `_create_for`, `_delete_channel`, `reconcile_channels` and `on_guild_channel_delete`), plus the bot’s own overwrite on a spawned channel so a **hidden** one does not lock Black Bloc out of the chat it has to post the panel into. ⚠️ `allows_place` was deliberately NOT widened — the channel-delete gate still asks only about the test channel’s own category, and the slash-command gate still refuses `/voice` outside the test channel. `black_bloc/guard.py`, `black_bloc/cogs/community/tempvoice.py`, `tests/test_guard.py` and `tests/cogs/community/test_tempvoice.py` were re-keyed from `666dd8e` **only along lines a diff calls equal** (132 keys, including the bare `` `:N` `` cross-references inside those four sections), so a mapped key is byte-identical to the line it named; **one key fell in a changed hunk and was rewritten rather than renumbered** — `tests/cogs/community/test_tempvoice.py:597`, whose note described the panel landing in the test channel. 1258 tests pass, ruff clean. NOT verified: any of it against a running bot — no panel has ever been posted into a real voice chat, no button has been pressed in one, and nobody has checked that the Bots role actually holds **Send Messages** in that category. Before that, **role-menu panels follow the mode** (owner ask, 2026-08-27 ~08:30: *"Panels get turned off when off, I'll get the ux now, save role menu seed"*, overturning the "panels stay posted" default of the change described next) added `black_bloc/rolemenu_panels.py` and its own section, `unposted_menus` / `clear_message` in `black_bloc/cogs/community/role_menus.py`, a job registry on the existing `VisibilitySync` debounce (`also` / `schedule` / `_jobs`) and two wiring lines in `black_bloc/bot.py` (`install_panels` in `setup_hook`, `panels_on_boot` in `on_ready`). `black_bloc/command_visibility.py`, `black_bloc/bot.py`, `black_bloc/cogs/community/role_menus.py`, `tests/test_bot.py` and `tests/cogs/community/test_role_menus.py` were re-keyed from `c7da174` **only along lines a diff calls equal** (48 keys, including bare `` `:N` `` cross-references), so a mapped key is byte-identical to the line it named and **none fell in a changed hunk**; `black_bloc/settings_store.py` changed wording only and did not move a line. **One note was rewritten rather than renumbered** because it described behaviour that is now the opposite: `role_menus.py:121`'s "panels are LEFT POSTED while off". Three keys that were ALREADY stale before this change were repaired by hand rather than shifted (`bot.py:56` and `tests/cogs/community/test_role_menus.py:339`/`:484` pointed at blank lines); this header line is the changelog and its historical numbers are deliberately left as they were written. 1243 tests pass, ruff clean, `site/mock/check.mjs` clean. NOT verified: any of it against a running bot — no panel message has ever been deleted by this code, nothing re-posted, no guard has refused a real delete, and the mode has never been flipped against live Discord. Before that, **command visibility** (owner ask: *"Can we suppress the / command for rolemenu too toggle by ui"*) added `black_bloc/command_visibility.py` and its `# black_bloc/command_visibility.py` section, a change hook on `SettingsStore` (`settings_store.py:693`), a `/help` filter (`cogs/core.py:112`) and one wiring line in `bot.py:65`; `black_bloc/bot.py`, `black_bloc/settings_store.py`, `black_bloc/cogs/core.py` and `black_bloc/cogs/community/role_menus.py` were re-keyed from `50a2484` **only along lines a diff calls equal** (132 keys, including bare `` `:N` `` cross-references inside those four sections), so a mapped key is byte-identical to the line it named and **none fell in a changed hunk**. ⚠️ **The `black_bloc/bot.py` section was ALSO repaired by hand: nine of its keys were already stale before this change** (they pointed at blank lines and at the line above the construct — `bot.py:20` was a blank line, not `COGS`), so each was re-pointed at the construct its note describes rather than merely shifted; the one `black_bloc/bot.py:41` mention inside this header is a HISTORICAL statement about the Phase 8a section and was deliberately left at 41. 1221 tests pass, ruff clean. NOT verified: any of it against a running bot — no command has ever been removed from a live tree, no sync has been sent to Discord, and nobody has flipped the switch on the dashboard and watched `/rolemenu` disappear. Before that, **generic loop discovery** closed KI-7: `black_bloc/api/status.py` now finds every `discord.ext.tasks.Loop` on every cog by type (`_loops`) instead of asking each cog for a `get_tasks()` that only one of them defined, so the Health tab lists **seven** loops across six cogs rather than one. `get_tasks` was deleted from `black_bloc/cogs/presence.py` (with its now-unused `typing.Any` import); `tests/api/test_status.py`, `tests/api/test_contract.py` and `tests/cogs/test_presence.py` were rewritten to build **real** `tasks.Loop` objects, and a parametrised test builds each real cog and asserts every loop it owns reaches `/api/status` with the `last_ok_at` that cog records. Every key in `api/status.py`, `cogs/presence.py`, `tests/api/test_contract.py` and every cross-reference to them was re-mapped **only along lines a diff calls equal**, so a mapped key is byte-identical to the line it names; the one key that fell in a changed hunk (`cogs/presence.py:46`, `get_tasks`) was **deleted rather than renumbered**, and two notes describing behaviour that no longer exists were rewritten: the old `status.py:153` "loops are found through `Cog.get_tasks()`" note (which also claimed TempVoice records no health — it has recorded `last_ok_at`/`last_error` and had a `@loop.error` handler since the F8 follow-up) and `tests/cogs/test_presence.py:195`. 1195 tests pass, ruff clean. `site/` and `site/mock/contract.json` were **not touched**: the per-loop shape (`cog`, `name`, `running`, `failed`, `state`, `next_iteration`, `last_ok_at`, `last_error`) is unchanged. NOT verified: any of it against a running bot — no loop has ever been discovered off a live gateway connection, and nobody has loaded the Health tab against the real API. Before that, **presence** (the owner's two asks: the site link in the bot's About Me and a "Cookout attendees: N" status) added `black_bloc/presence.py`, `black_bloc/cogs/presence.py`, the `bot_bio` and `status_prefix` registry keys and the `# Presence` section at the end of this file, and re-keyed `black_bloc/bot.py`, `black_bloc/settings_store.py` and `black_bloc/api/settings_api.py` — every key in those three files, and every prefix-less cross-reference to them, mapped only along lines a diff calls **equal**, so a mapped key is byte-identical to the line it names and nothing fell in a changed hunk. 1194 tests pass, ruff clean. NOT verified: any of it against a running bot — no About Me has ever been edited by this code, no custom status ever set, and `AppInfo.edit` has never been called for real. Before that, **test-sweep batch 4** (commits `47634b8` Carl/parity removal, `7b487cf` temp-voice memory, `6f45299` favicon) re-keyed `black_bloc/automod.py`, `black_bloc/modcases.py`, `black_bloc/settings_store.py`, `black_bloc/api/settings_api.py`, `black_bloc/api/tools/mod.py`, `black_bloc/cogs/moderation/automod.py`, `black_bloc/cogs/community/tempvoice.py`, `black_bloc/storage/db.py` and four test files from base `3581eea`, **including every inline `` `:N` `` cross-reference, every prefix-less `cogs/…:N` one and every bare `module.py:N` one** — mapped only along lines a diff calls **equal**, so a mapped key is byte-identical to the line it names; nothing fell in a changed hunk. **Eight rows were DELETED rather than renumbered** because the constructs are gone: `parse_carl_entry`, `parity_report`, `gather_parity`, `/automod parity`, `armed_verdicts_since`, `PARITY_SAME_CHANNEL`, the parity route pair and the `carl_modlog_channel_id` default. `SCHEMA_VERSION` is **11**; 1173 tests pass, ruff clean, `site/mock/check.mjs` clean. NOT verified: any of it against a running bot — no channel has ever been spawned from a remembered permit list, and nobody has loaded a page and seen the favicon. Before that, **the temp-voice panel + `/voice` merge** brought `worktree-agent-aa87571126477eb8f` into `main`, re-keying `tempvoice.py`, `storage/db.py` and `test_tempvoice.py` from `65dc85c` and folding the `### F8 follow-up` block onto the merged file. ⚠️ **That block's keys matched NEITHER branch commit** (`91c9c0b` nor `af3dd55`) — most carried a consistent +170 offset — so it was re-keyed by **anchor**, function by function, rather than by diff; every key there now names the function its note describes, verified one at a time. Three notes described behaviour the merge removed and were **rewritten rather than renumbered**: `_post_panel`'s "the panel is NOT posted in test mode" (it is, into the test channel), `test_tempvoice.py`'s `would_post_panel` test, and `db.py:11`'s "bumped to 8". `SCHEMA_VERSION` is **10**; 1134 tests pass, ruff clean, `site/mock/check.mjs` clean. NOT verified: any of this against a running bot. Before that, **the Phase 8b merge and reconciliation** brought both 8b branches into `main` (`178fe69` API, `6bf4669` pages) and then made the pages, the routers and the mock agree. It re-keyed the twelve files the merge moved — `black_bloc/api/server.py`, `black_bloc/api/status.py`, `black_bloc/cogs/community/{birthdays,events,role_menus,tempvoice}.py`, `black_bloc/cogs/content/golive.py`, `black_bloc/cogs/moderation/{automod,honeypot,modcmds,modmail}.py` and `black_bloc/modcases.py` — **plus every inline `` `:N` `` cross-reference and every prefix-less `cogs/…:N` one**, which the earlier phases' re-keying passes had to do by hand and this one did by mapping each key from **its own base commit** (`b430eb0` for the main body, `a255ab8` for the 8b-API appendix, `a661448` for the 8b-pages appendix — the same file appears under two bases, so a single base would have corrupted one of them). 281 keys moved. Each new number is not merely shifted: the mapping only follows lines a diff calls **equal**, so a mapped key is byte-identical to the line it named, and the nine that fell inside a changed hunk were reported rather than guessed and repaired by hand: `role_menus.py`'s `_edit_existing` and `automod.py`'s `_message_to_delete` / `_would_have` became module-level functions or were folded into `apply_case`; `tempvoice.py`'s `_adopt` and `_repair` are now `adopt_creator_channel` / `repair_creator_channel`; `events.py`'s `decide` moved down when `apply_decision` was extracted above it; `modmail.py`'s `dm_failed` line travelled with `send_reply` out of the cog; and two notes described behaviour that no longer exists at all (the mock's `web.settings_set` spelling, `make_creator_channel`'s create-only body) and were **rewritten rather than renumbered**. **1105 tests pass, ruff clean** (831 on `main` + 223 from the API branch + 51 new contract cases). NOT verified: any page against the **real** API in a browser — only against `site/mock/server.mjs`, whose shapes are now checked against the same table (`site/mock/contract.json`) that `tests/api/test_contract.py` checks the routers against; and nothing at all against live Discord. Before that: **test-sweep batch 2** added `/help` (`black_bloc/cogs/core.py`), `is_staff_command` (`black_bloc/settings_store.py`) and lobby adoption (`black_bloc/cogs/community/tempvoice.py`), and re-keyed those three files plus `tests/cogs/test_core.py`, `tests/test_settings_store.py` and `tests/cogs/community/test_tempvoice.py` — 98 keys moved, each new number checked against the construct it names by mapping the old line to the new one and comparing the anchor text, not by shifting an offset. One anchor did NOT survive the mapping and was repaired by hand: `tempvoice.py`'s `_repair` note, because `_adopt` was inserted directly above it and a diff maps an insertion's start, not its intent. **831 tests pass, ruff clean** (817 before, 14 added). NOT verified: any of batch 2 against live Discord — `/help` has never been run in the server, and no lobby has ever been adopted; the live settings store is on the Fly volume and could not be read from this tree, so the root cause of the duplicate lobby is reasoned from the code and labelled as such (`black_bloc/cogs/community/tempvoice.py:230`). Before that: the **Phase 6 merge into `main`** (moderation, F7) re-keyed `black_bloc/bot.py`, `black_bloc/settings_store.py`, `black_bloc/storage/db.py`, `black_bloc/cogs/core.py`, `tests/storage/test_db.py`, `tests/test_settings_store.py` and `tests/cogs/test_core.py` — the seven files Phase 6 appended to — **and every cross-reference to them from other sections**; 135 keys moved and each new number was checked against the construct it names by mapping the old line to the new one and comparing the anchor text, not by shifting an offset. ⚠️ **The Phase 6 section's keys were re-keyed too, from THREE different base commits**, because its four files finally exist in this tree: the per-file sections in the main body were keyed against the build commits (`6437d9f`, `fa6f6e8`, `71626c5`) and had been stale ever since the two adversarial-review commits moved lines under them, while the `# Phase 6 — moderation (F7)` appendix was keyed against the branch tip `e85d9b5` and every one of its keys proved **unmoved** — the four files landed byte-identical, which is the check that proves the merge did not touch them. Two anchors did NOT survive and were repaired by hand rather than renumbered: `automod.py`'s Carl-user pattern (the review deleted its bare-digit alternative, so the old note described a regex that no longer exists) and `modcases.py:dm_text` (the review added `duration_s` to its signature). `black_bloc/api/*` and `site/` keys are still deliberately untouched — those files are Phase 8a and are not in this tree. **735 tests pass, ruff clean** (628 from main plus Phase 6's 111, less the 4 `test_command_errors.py` tests both sides already shared byte-identically). NOT verified: any of moderation running against live Discord — no message has ever been deleted, no member timed out, no Carl modlog ever read, and `automod_mode` defaults **shadow**. Before that: the **Phase 7 merge into `main`** (modmail, F11, schema v8) re-keyed `black_bloc/bot.py`, `black_bloc/settings_store.py`, `black_bloc/storage/db.py`, `tests/storage/test_db.py` and `tests/test_settings_store.py`, the five files Phase 7 appended to, **and every bare cross-reference to them from other sections**; 71 keys moved and each new number was checked against the construct it names, not merely shifted. The Phase 7 section's own keys for `black_bloc/modmail.py`, `black_bloc/cogs/moderation/modmail.py` and the two modmail test files did **not** move — those four files landed unchanged — but its cross-references *out* into `cogs/community/events.py`, `cogs/community/tempvoice.py` and `cogs/moderation/honeypot.py` were badly stale, because the Phase 7 branch was cut from `d9d086a` (before Phase 5) and `events.py` had shifted by 246 lines since; all seven were re-mapped. 628 tests pass, ruff clean. NOT verified: any of modmail running against live Discord — no DM has ever been relayed, no ticket channel or private thread created, no transcript uploaded, and `modmail_enabled` defaults **false**, so the incumbent ModMail bot still holds the inbox. ⚠️ `black_bloc/bot.py:41` in the **Phase 8a** section was deliberately left alone: it describes files that do not exist in this tree (`api/auth.py`, `api/status.py`, `site/`), so re-keying it to this tree's lines would silently corrupt it for the merge that brings them in. (The same exemption used to cover the **Phase 6** keys; it no longer applies — the Phase 6 merge brought `automod.py` and `modcases.py` in, and those keys are now checked against real lines.) Before that: the **Phase 5 merge into `main`** (birthdays, F6, schema v6) re-keyed `black_bloc/settings_store.py`, `black_bloc/storage/db.py`, `black_bloc/bot.py`, `black_bloc/cogs/core.py`, `tests/storage/test_db.py` and `tests/test_settings_store.py`, because Phase 5 appended to all six; every key in them, **and every bare cross-reference to them from other sections**, was re-checked against the file after the merge and corrected here (several were already stale by 20–50 lines). The Phase 5 sections' keys for `black_bloc/birthdays.py`, `black_bloc/cogs/community/birthdays.py` and the two birthday test files were re-checked the same way; `birthdays.py` lost 13 lines when the `timezone_table_exists` probe was deleted, and the four settings-store notes that were filed under the `actionlog.py` heading were moved into the `settings_store.py` section where they belong. 534 tests pass, ruff clean. NOT verified: any of it running against live Discord — no birthday has ever been posted, no birthday role ever given, and the 39-row import has never met the real member list. Before that: the **Phase 4 adversarial-review fixes** (F1-F14, commits `63e1d15` and `8474f14`) re-keyed `black_bloc/guard.py`, `black_bloc/command_errors.py`, `black_bloc/settings_store.py`, `black_bloc/timezones.py`, `black_bloc/events.py`, `black_bloc/storage/db.py`, `black_bloc/cogs/community/events.py`, `black_bloc/cogs/community/tempvoice.py`, `black_bloc/cogs/moderation/honeypot.py` and six test files, because all of them moved; every key in those files was re-mapped from the pre-fix commit and then re-checked against the file after the last edit. NOT verified: any of it running against live Discord — no scheduled event has ever been cancelled, no announcement edited and no channel deleted by this code, and the `delete_channel` gate has never refused a real call. Before that: **Phase 4** added `black_bloc/timezones.py`, `black_bloc/events.py`, `black_bloc/cogs/community/events.py`, `tests/test_timezones.py`, `tests/test_events.py` and `tests/cogs/community/test_events.py`, and edited `black_bloc/bot.py` (one COGS line), `black_bloc/settings_store.py` (the `LIVE_NOW_CHANNEL_ID` rename, six `events_*` keys, `KEY_MAX_REASON`, `clear`), `black_bloc/storage/db.py` (v5, two tables), `tests/storage/test_db.py` and `tests/test_settings_store.py`. Every key in `settings_store.py` and `storage/db.py` below was re-checked against the file after the last edit and the ones that moved are corrected here; no line in `bot.py`, `guard.py`, `actionlog.py`, the go-live files, `tempvoice.py` or `honeypot.py` moved except `bot.py:24`'s COGS tuple, which grew by one entry without moving its own first line. NOT verified: any of Phase 4 running against live Discord — no real review channel, rename or scheduled event has ever been made by this code. Before that: Phase 3 re-keyed every line number in `bot.py`, `settings_store.py`, `storage/db.py`, `cogs/content/golive.py`, `cogs/community/role_menus.py`, `tests/storage/test_db.py`, `tests/test_settings_store.py` and `tests/cogs/community/test_role_menus.py`, because all eight were edited; the numbers here are the new ones and were re-checked against the files after the last edit. Before that, every path:line was re-checked against the file after the Phase 2 go-live review fixes (session reconciliation, live-role bookkeeping, post failures, network errors, allowed mentions, per-user locks, the guard's `edit_message` gate). Keys in `bot.py`, `guard.py`, `settings_store.py`, `storage/db.py`, `twitch.py`, `golive.py`, `cogs/content/golive.py` and their test files MOVED; the numbers here are the new ones. The Phase 3 adversarial-review fixes then re-keyed `settings_store.py`, `cogs/community/tempvoice.py`, `cogs/moderation/honeypot.py` and their three test files, because all six moved; `cogs/community/role_menus.py` changed only wording and did not move a line. Every key in those files was re-checked against the file after the last edit. NOT verified: anything running against live Discord or the real Twitch API.

Owner rule, 2026-08-26: *"i want almost 0 comments in code. I want all the
comments to be in docs with links to the code files and lines of question."*
This file is that destination. Every entry is keyed `path:line`; the line is
the **first line of the thing being explained** (the `def`, the assignment, the
`class`). Explanations answer *why*, never *what* — the code says what.

⚠️ **Line numbers rot.** Re-verify this file whenever a keyed file is edited,
and update "Last verified" above. If a line number and its quoted anchor
disagree, trust the anchor and fix the number.

> Keys re-verified against `ef8a7a1`, 2026-08-31. 1817 keys checked, 1215 updated, 12 marked GONE.

The six package `__init__.py` files (`black_bloc/cogs/`, `black_bloc/api/`,
`black_bloc/storage/`, `black_bloc/cogs/content/`, `black_bloc/cogs/moderation/`,
`black_bloc/cogs/community/`) are **empty on purpose** — package markers with
nothing to say. They are not listed below.

---

## `black_bloc/app.py` — the run button

| Key | Note |
|---|---|
| `black_bloc/app.py:9` | `main()` is the entire entrypoint and stays that way (owner rule, 2026-08-26): settings → logging → bot → run. A feature that "just needs a line in app.py" is in the wrong place — it belongs in its own module. |
| `black_bloc/app.py:12` | Logging is configured **before** `validate_test_mode()` and `require_token()` so anything those raise or emit is already going through the project's handler configuration. |
| `black_bloc/app.py:15` | `ConfigError` is the only exception app.py knows about. The exit code it maps to lives in `errors.py`, not here, so the entrypoint has no policy in it. |

## `black_bloc/errors.py` — exit-code policy and the gateway run loop

| Key | Note |
|---|---|
| `black_bloc/errors.py:11` | Three distinct outcomes on purpose: `0` clean stop (including Ctrl+C), `2` the configuration is wrong, `3` Discord refused the login. A supervisor (Fly, systemd) can then tell "a human must edit something before this will ever start" from "a restart might help". |
| `black_bloc/errors.py:14` | ⚠️ **Byte-identical to what `docs/access/setup.md` quotes.** These two sentences are the user-facing surface for the two ways a start fails; changing the wording silently desynchronises the runbook. |
| `black_bloc/errors.py:18` | Names all three privileged intents and the exact portal path, because code alone cannot grant them — see `gotchas.md`, "Login fails with `PrivilegedIntentsRequired`". |
| `black_bloc/errors.py:30` | `async with bot` guarantees `BlackBlocBot.close()` runs — cancelling the background API task and closing the SQLite connection — even when `start()` raises. |
| `black_bloc/errors.py:38` | Ctrl+C is a normal stop, not a crash: swallowed, exit `0`, no traceback. |
| `black_bloc/errors.py:43` | `PrivilegedIntentsRequired` and `LoginFailure` share exit `3`: both mean "Discord refused this token/app as configured", and both are fixed in the Developer Portal. |

## `black_bloc/intents.py`

| Key | Note |
|---|---|
| `black_bloc/intents.py:8` | All three are **privileged** intents and must ALSO be toggled on in the Developer Portal (Bot → Privileged Gateway Intents) or login fails seconds after start. Why each is requested: `members` — joins/leaves and role upkeep; `message_content` — moderation and the honeypot; `presences` — the Twitch "Streaming" activity (F1/F2). |

## `black_bloc/invite.py`

| Key | Note |
|---|---|
| `black_bloc/invite.py:5` | Sized for the first feature list (moderation, temp voice, scheduled events, announcements) — deliberately **NOT** Administrator. Widen the set here, then re-invite the bot with the new URL; a running bot does not gain permissions from a code change alone. |
| `black_bloc/invite.py:25` | `application_id` is only populated by `Client.login()`, so this assert can only fire if something calls `invite_url()` before the client has logged in. It is a programmer check, never a user-facing error. |

## `black_bloc/command_sync.py`

| Key | Note |
|---|---|
| `black_bloc/command_sync.py:14` | No `DEV_GUILD_ID` means **nothing syncs at all** — global sync is not wired up on purpose (KI-2 in `../KNOWN_ISSUES.md`). Set a `DEV_GUILD_ID` while developing or new slash commands will never appear. |
| `black_bloc/command_sync.py:19` | `copy_global_to` + a guild-scoped `sync` makes commands appear in the dev guild immediately; the Discord client may still need a full restart (Ctrl+R) to refresh a stale picker. Syncing is rate-limited — rapid restart loops produce 429s and a slow start, which is Discord, not a bug. |
| `black_bloc/command_sync.py:22` | A `403` here means Discord will not let this application write commands to that guild: the bot is not a member of it, or was invited without the `applications.commands` scope. The invite URL is logged **in the same line** so the fix is in the log. Not fatal — the bot keeps running, and the text prefix still works. |
| `black_bloc/command_sync.py:31` | The success log sits after the `try` so that only `tree.sync()` is inside it; nothing else can be mistaken for a `Forbidden`. |

## `black_bloc/command_visibility.py` — a mode that is `off` hides its slash commands

| Key | Note |
|---|---|
| `black_bloc/command_visibility.py:15` | ⚠️ **The registry IS the feature** (owner ask, 2026-08-27: *"Can we suppress the / command for rolemenu too toggle by ui"*). A feature opts in with one row — mode key → the top-level command names to hide while that mode is `off` — and nothing else in the module knows what `rolemenu` is. The alternative, a `hidden` flag on each cog, would have put the decision in ten places and left the dashboard with nothing to read. |
| `black_bloc/command_visibility.py:18` | ⚠️ **`/settings` can never be hidden, and this is the way back.** Hiding a feature's commands also hides its own `mode` subcommand, so the slash-side way to turn `rolemenu_mode` back on is `/settings set-value rolemenu_mode on`. A registry row that named `settings` would lock the owner out of Discord entirely and leave only the dashboard; the guard is enforced in `apply` **and** in `hidden_names`, because the two are read by different surfaces. |
| `black_bloc/command_visibility.py:20` | ⚠️ **Debounce then rate-limit, in that order, because command sync is rate-limited** (KI-2 in `../KNOWN_ISSUES.md`). Five seconds absorbs a staffer flipping the switch twice, or a web `PUT` racing a slash command; sixty seconds is the floor between two syncs however many changes arrive. Both are module constants rather than settings: a knob here would be a knob whose wrong value is a 429 nobody can see. |
| `black_bloc/command_visibility.py:25` | The wait is its own module-level function purely so the tests can hold every debounce open and assert what was waited for, offline. `time.monotonic` is wrapped for the same reason (`:29`) — a wall clock that moves backwards must not turn the rate-limit window into a permanent one. |
| `black_bloc/command_visibility.py:38` | Answers from the **stored mode**, not from what the tree currently holds, so `/help` (`cogs/core.py:112`) says the same thing whether or not a sync has landed yet. A tree read would have made the list disagree with the answer a member gets for the five seconds the debounce is open. |
| `black_bloc/command_visibility.py:69` | ⚠️ **One idempotent function does the whole job, and returns whether it had to change anything.** Startup and every later change call the same code, so there is no second path that could drift; a call that changes nothing (the mode is `on` and everything is present) syncs **nothing at all**, which is what keeps a restart from spending a sync it does not need. |
| `black_bloc/command_visibility.py:89` | `tree.remove_command(name, guild=…)` returns the object it removed (discord.py 2.7.1, `app_commands/tree.py:444`), and it is **kept** so the re-add is the same object rather than a rebuilt one — the `Group` carries its cog binding, and a copy would answer interactions with the wrong `self`. Removal touches only the **guild** copy: the global tree still holds the command, which is what `copy_global_to` re-seeds from on the next start. |
| `black_bloc/command_visibility.py:97` | The put-back, with a fallback: normally the kept object, but after a restart the tree was re-seeded from the globals and nothing was ever removed in this process, so the global command is re-added instead. `override=True` because `add_command` raises `CommandAlreadyRegistered` otherwise, and "already there" is the case this is called in most often. |
| `black_bloc/command_visibility.py:110` | ⚠️ **One task, however many changes arrive.** A pending task is left alone rather than cancelled and replaced: it reads the tree at sync time, so it already carries whatever the later changes did. This is what makes three flips in a row cost exactly one sync. |
| `black_bloc/command_visibility.py:147` | Failure is loud and **does not move the window**: `last_sync` is only stamped after Discord accepted the sync, so a 429 does not buy a sixty-second silence on top of the one Discord already imposed. The `commands.visibility` action-log row carries the resulting command count and who changed the setting, so "why did `/rolemenu` disappear" is answerable from the log alone. |
| `black_bloc/command_visibility.py:59` | ⚠️ **The debounce is the reusable half, not the tree editing.** A second feature reacting to the same flip (role-menu panels, `rolemenu_panels.py:172`) must coalesce with this one or an `off → on → off` burst costs three runs; `also` lets it hang a job on the run that already exists rather than build a second timer with its own five seconds. Dedupe is by identity, so a double `install` cannot double-register the same bound method. |
| `black_bloc/command_visibility.py:64` | The way in for a feature whose flip does **not** change the tree: `apply` returns `False` and schedules nothing when nothing moved, so a job that still has work to do needs its own way to ask for the run. It also carries the actor forward, because the job wants it in its own action-log rows. |
| `black_bloc/command_visibility.py:133` | ⚠️ **Jobs run after the debounce and BEFORE the sync, and a job that raises never takes the sync down with it.** Before, because the sync can be held a further sixty seconds by its own rate limit (`:20`) and a panel that should be down must not wait on a command-tree window; separately caught, because "the panels came down" and "Discord accepted the tree" are two different promises and one failing must not cancel the other (checklist 12). |
| `black_bloc/command_visibility.py:204` | ⚠️ **ONE trigger path.** `/rolemenu mode`, `/settings set-value` and `PUT /api/settings/{key}` all write through `SettingsStore.set`, so registering a change hook there (`settings_store.py:693`) covers all three and any surface added later — three call sites would have been three chances to forget one. Called from `bot.py:67`, **after** the initial sync, so the tree it edits is the one that was just seeded. |

## `black_bloc/bot.py` — lifecycle only

| Key | Note |
|---|---|
| `black_bloc/bot.py:24` | Extensions loaded at startup, **in order**. Each must expose `async def setup(bot)`. Registering a feature = adding its dotted path here; that is the whole registration mechanism (`architecture.md`, rule 2). Phase 2 added exactly one line, `cogs.content.golive`; Phase 4 added exactly one more, `cogs.community.events`; Phase 5 added `cogs.community.birthdays` at the end, and Phase 7 added `cogs.moderation.modmail` after it. Nothing else in this file changed in any of them — which is why every merge conflict here has been the same one-line append on both sides, resolved by keeping both. ⚠️ **Modmail is loaded last on purpose but the order is not load-bearing:** cogs never import each other (`architecture.md`, rule 2), so a cog that needed a particular position would already be the wrong shape. |
| `black_bloc/bot.py:42` | ⚠️ Construction must stay **offline** — no network, no token needed. `tests/test_bot.py` and `tests/test_guard.py` build a real bot object with no credentials, and that is what keeps the whole suite runnable without Discord. |
| `black_bloc/bot.py:51` | The one line `bot.py` gains for Phase 1 (`phase1-design.md`, §Scope). It takes `settings` as well as `db` because the settings registry's *defaults* are defined in terms of `TEST_MODE`/`TEST_CHANNEL_ID` — see `settings_store.py:679`. Still one line, and `bot.py` stays lifecycle-only. |
| `black_bloc/bot.py:53` | The test-mode guard is installed in `__init__`, before any cog exists and long before the gateway connects, so there is no window in which a cog could send somewhere it should not. |
| `black_bloc/bot.py:59` | The tree error handler is installed **first thing** in `setup_hook`, before the database, the cogs and the command sync — everything after it can therefore fail loudly and still reach the caller as a sentence rather than as "the application did not respond" (`command_errors.py:73`). It is one line here because `bot.py` is lifecycle only (`architecture.md`, rule 1). |
| `black_bloc/bot.py:61` | Settings are read into memory **once**, right after `db.connect()` and **before** cogs load, so a cog's `cog_load` and every command body can read a knob synchronously (`settings_store.py:826`). |
| `black_bloc/bot.py:63` | The invite URL is logged **before** the gateway connect, so it is available in the log even when the privileged-intent toggles are still off in the portal and the connect is about to fail. |
| `black_bloc/bot.py:53` | `start_api` is imported lazily so `fastapi`/`uvicorn` are only imported when `API_ENABLED=true`. The task goes on `self._background` so `close()` can cancel it. |
| `black_bloc/bot.py:88` | Shutdown order matters: cancel background tasks → close the database → defer to `discord.py`. Closing the DB before the API task is cancelled would let a live route touch a closed connection. ⚠️ `commands.Bot.close()` also unloads every cog, which is what runs `GoLive.cog_unload` (`cogs/content/golive.py:331`) and stops the Twitch poller — do not "simplify" it to `Client.close()`. |
| `black_bloc/bot.py:67` | The role-menu panels' own wiring, one line, deliberately next to visibility's: both react to `rolemenu_mode` through the same store hook and share the same debounce, and putting them side by side is what makes "two things happen on this flip" readable at the only place that knows both (`rolemenu_panels.py:172`). It registers only — nothing is posted or taken down until `on_ready` arms it. |
| `black_bloc/bot.py:85` | ⚠️ **The only thing `on_ready` does beyond logging**, and it is idempotent by design: `on_ready` fires again on every gateway RESUME, and the boot reconcile only ever takes panels down that the stored mode says should not be up (`rolemenu_panels.py:184`). |
| `black_bloc/bot.py:66` | Visibility is applied **after** `sync_dev_guild`, never before: the guild copy the registry edits is the one `copy_global_to` has just seeded, and applying first would edit a mapping the sync then overwrites. It is also what registers the store's change hook, so this single line is the whole wiring (`command_visibility.py:204`). |

## `black_bloc/rolemenu_panels.py` — the panels follow the mode

| Key | Note |
|---|---|
| `black_bloc/rolemenu_panels.py:72` | ⚠️ **The guard is checked here because `guard.py` cannot see a message DELETE.** It patches `send_message`, `edit_message` and `delete_channel` (`guard.py:140`) — not `delete_message` — so an unposting sweep would happily reach into a channel the test policy forbids. Refused work is logged `role_menu.would_unpost` and the row is left **exactly** as it was: the panel is still up, so clearing `message_id` would be a lie about the world (checklist 1, 2 and 10). |
| `black_bloc/rolemenu_panels.py:82` | `NotFound` is not a failure — somebody deleted the panel by hand and the row is simply forgotten, which is the only outcome that ends with the database agreeing with Discord. Every other `HTTPException` keeps `message_id` so the next flip tries again, and says why in `role_menu.unpost_failed` rather than sharing a kind with the dry run. |
| `black_bloc/rolemenu_panels.py:92` | Re-posting goes through `post_panel` (`cogs/community/role_menus.py:675`), the same helper `/rolemenu post` and `PUT /api/rolemenus/{name}/post` use, so the persistent view, the `custom_id` and the `set_message` write are one implementation rather than three. A `staff` menu has no panel and an option-less menu cannot legally be posted (Discord rejects `max_values=0`), so both are skipped rather than attempted and logged as failures. |
| `black_bloc/rolemenu_panels.py:117` | ⚠️ **One bad menu never ends the sweep.** The catch is `Exception`, not `HTTPException`: a row with a broken emoji or a channel object of the wrong type must cost one menu, not every menu after it. |
| `black_bloc/rolemenu_panels.py:134` | ⚠️ **The mode is read at RUN time, not at flip time**, which is what makes the coalesced run correct: an `off → on → off` burst arrives as one job and the last state wins. The sweep only ever touches `role_menus.message_id`; menu rows, options and the seed are never written by the switch (owner ask, 2026-08-27: *"save role menu seed"*). |
| `black_bloc/rolemenu_panels.py:152` | ⚠️ **The panels are disarmed until the gateway is ready.** `install` runs inside `setup_hook`, and the visibility debounce it hangs off may fire before the guild cache is warm — `bot.get_channel` would then return `None` for channels that are perfectly fine and log a row of `unpost_failed`. `panels_on_boot` (`:184`) is what arms it, from `on_ready`. |
| `black_bloc/rolemenu_panels.py:184` | ⚠️ **The boot reconcile converges ONE way.** A restart in the middle of a flip can leave panels up while the mode says `off`, and those come down. A row with a channel and no panel while the mode says `on` is left alone on purpose: only a deliberate flip posts, so a restart can never surprise the server with six panels nobody asked for. |

## `black_bloc/command_errors.py` — the answer of last resort

| Key | Note |
|---|---|
| `black_bloc/command_errors.py:27` | Answering is split out because the reply path depends on what the command already did: an interaction that has been deferred or replied to can only take a `followup`, and calling `response.send_message` on it raises a *second* exception inside the error handler. The whole thing is wrapped because the error handler is the last line — if it raises, the person sees nothing at all. |
| `black_bloc/command_errors.py:65` | ⚠️ `CheckFailure` returns early **on purpose**: `tree.interaction_check` (the test-mode guard, `guard.py:147`) has already answered the caller with its own refusal, and a second message would contradict it. Everything else is logged with a full traceback and answered with one sentence — the owner rule is that a person never sees a bare status code or a dead button. |
| `black_bloc/command_errors.py:73` | Assigned as a plain function on the *instance*, so it is called as `tree.on_error(interaction, error)` with no `self`. Installed from `bot.py:54` rather than subclassing `CommandTree`, because the bot builds its own tree and a subclass would have to be threaded through `commands.Bot.__init__`. |
| `black_bloc/command_errors.py:18` | ⚠️ **One home for "what counts as the network failing"** (review finding F11). Five places in the events cog caught `discord.HTTPException` alone, so a reset connection, a DNS failure or a timeout escaped a background loop as an unhandled traceback rather than a logged failure — the same defect the Twitch client already fixed at its own boundary (`twitch.py:96`). `ValueError` is in the tuple because `discord.py` raises a bare one for a state it will not let you change: `ScheduledEvent.cancel()` on an event that is already running (finding F1). `asyncio.TimeoutError` is the builtin `TimeoutError` on 3.11+, and therefore already an `OSError`; both are named because the two spellings appear in different libraries' documentation and a reader should not have to know they are the same class. |
| `black_bloc/command_errors.py:37` | The same two jobs `on_tree_error` does — log the traceback, answer with one sentence — split out so a UI component can reuse them. `where` is the class name rather than a command name, because a click has no command. |
| `black_bloc/command_errors.py:43` | ⚠️ **The mixin every view and modal in the project now carries** (finding F6). `View.on_error(interaction, error, item)` and `Modal.on_error(interaction, error)` differ by one argument, so `item` has a default and one class covers both; `discord.py` calls them positionally. Without it a raise inside a button callback was logged by the library and the person saw a button that did nothing at all — the dead-control failure the owner rule forbids. |
| `black_bloc/command_errors.py:52` | ⚠️ **A `DynamicItem` never reaches `View.on_error`, and that is a library fact, not a choice.** `ViewStore.schedule_dynamic_item_call` (discord.py 2.7.1, `ui/view.py:1039`) wraps the callback in its own `try/except` that logs and returns — the view's handler is never consulted. So the item catches its own, which is why subclasses implement `on_click` and not `callback`. Rename `on_click` and every dynamic button in the project goes silently back to being a dead control. |

## `black_bloc/config.py` — the only reader of the environment

| Key | Note |
|---|---|
| `black_bloc/config.py:25` | A dedicated error type so configuration problems reach the user as one readable sentence and exit `2`, never as a pydantic traceback. |
| `black_bloc/config.py:51` | Optional on purpose: with no Twitch app the go-live feed still works on Discord presence alone, and the cog says so once in the log (`cogs/content/golive.py:331`). They are `str \| None` rather than `str` so that "not configured" and "configured with an empty string" cannot be confused. |
| `black_bloc/config.py:58` | ⚠️ **Owner rule, 2026-08-26: `test_mode` defaults to `True`.** Until the owner lifts it, the bot speaks only in `TEST_CHANNEL_ID` and DMs. The default is `True` so that a missing/blank `.env` fails closed rather than open. Enforced mechanically by `guard.py`, not just documented. |
| `black_bloc/config.py:71` | `.env.example` ships `DEV_GUILD_ID=`, `TWITCH_CLIENT_ID=` and `TWITCH_CLIENT_SECRET=` with no values. A blank string must mean "unset" — without this validator a fresh copy of `.env.example` is a startup error, and a blank Twitch id would make `twitch_configured` true and start a poller that 400s every minute. |
| `black_bloc/config.py:98` | Both halves or nothing: a client id with no secret cannot mint a token, so it must not count as configured. This property is the only thing the cog checks (`cogs/content/golive.py:265`). |
| `black_bloc/config.py:122` | Checked at startup (`app.py:13`) rather than in a pydantic validator, so a test can construct the invalid combination and assert the message — see `tests/test_guard.py:178`. |
| `black_bloc/config.py:139` | Translates pydantic's `ValidationError` into a single `ConfigError` line naming the offending field(s); `app.py` prints it and exits `2`. Keyword overrides win over the environment, which is how the tests inject `_env_file=None`. |

## `black_bloc/guard.py` — the test-mode gate (⚠️ contract, do not loosen)

| Key | Note |
|---|---|
| `black_bloc/guard.py:11` | Raised, never logged-and-swallowed. A blocked send must be loud and must fail the caller — a silently dropped message looks identical to a working bot. |
| `black_bloc/guard.py:19` | **Owner rule, 2026-08-26:** *"we will only test in here until we're ready. never use another channel except for you're allowed to be dm'd to test too"*. While `TEST_MODE=true` the bot may only (a) send messages to `TEST_CHANNEL_ID` or a DM channel, and (b) answer slash commands invoked from that channel or a DM. ⚠️ **Not covered, and needing the same care in feature code:** channel/role edits, bans, event creation, webhooks. Builders call `bot.guard.allows_channel(...)` before any side effect on a channel. |
| `black_bloc/guard.py:88` | The refusal sentence lives in one method because **two** places say it now: `interaction_check` below, and the role-menu select handler (`cogs/community/role_menus.py:452`), which the HTTP gate cannot see. One fact, one home — two copies would drift the moment the test channel changes. |
| `black_bloc/guard.py:94` | `interaction.guild_id is None` **is** the DM test — DMs are allowed from any channel id, so the check returns early before comparing channels. |
| `black_bloc/guard.py:101` | The gate sits on the **HTTP layer** (`bot.http.send_message`, `bot.http.edit_message`) so every code path that ends in a channel message hits it, whether it went through `channel.send`, `message.edit`, `ctx.send` or a cog's background task. Interaction responses are a separate path, covered by `tree.interaction_check`, which runs before any command body. |
| `black_bloc/guard.py:118` | ⚠️ **Editing an existing message is a second way to speak in a channel**, and until the Phase 2 review it was ungated: the go-live end marker (`cogs/content/golive.py:561`) edits a message by id, so a session opened before the policy — or a `golive_channel_id` changed underneath it — could have written to a channel the send gate would have refused. Same shape as `gated_send_message` on purpose; two near-identical functions rather than one clever wrapper, because the log line has to name which operation was refused. |
| `black_bloc/guard.py:140` | `# type: ignore[method-assign]` — monkeypatching bound methods on the HTTP client is the *intent* here, not an accident; the ignores stay. |
| `black_bloc/guard.py:158` | Same deliberate method assignment on the command tree. `discord.py` supports overriding `interaction_check`; the type stub does not model the assignment. |
| `black_bloc/guard.py:160` | A `WARNING` at install time so **every** start log states plainly what the bot is allowed to do. Reading a log and not knowing whether the gate is on is how a test-mode rule quietly stops being enforced. |
| `black_bloc/guard.py:35` | Takes a channel object OR an id, because the two callers want different things: the HTTP gate only ever has an id, while feature code has the object and would otherwise have to remember `.id` at every call site. A value that is neither is `None`, i.e. refused — failing closed is the whole point of this file. |
| `black_bloc/guard.py:66` | The test channel's own category, read fresh every time rather than cached, because the owner can move the channel while the bot is running and a cached answer would keep authorising the old place. `None` when the test channel is not in the cache **or is not in a category at all**, and both cases mean the same thing: nothing can be proved about where anything is (finding F12). |
| `black_bloc/guard.py:70` | ⚠️ **The PLACE question, which the HTTP gate cannot answer and three cogs were each answering by hand** (`cogs/community/tempvoice.py:1643`, `cogs/moderation/honeypot.py:644`, `cogs/community/events.py:457`). Sends are gated by channel; creating, renaming and deleting a channel is gated by whether it sits in the test channel's category. One implementation here means the answer cannot drift between features, and it is a no-op once test mode is lifted because the guard is not installed at all then. |
| `black_bloc/guard.py:128` | ⚠️ **Added by review finding F3: the events retention sweep deleted channels with nothing in front of it.** A delete is invisible to the send and edit gates, and the sweep runs in a background loop where a mistake is a channel nobody can get back. The gate keys on `allows_place`, not `allows_channel`, because the channels this bot legitimately deletes — spent review channels, spent temp voice channels — are never the test channel itself, only its siblings. A channel the bot cannot see is refused: an unknown place is not a permitted one. |

## `black_bloc/logging_setup.py`

| Key | Note |
|---|---|
| `black_bloc/logging_setup.py:12` | `discord.http` logs **every** HTTP request at INFO and `discord.gateway` every heartbeat; both are noise outside debugging, so they are pinned to WARNING regardless of `LOG_LEVEL`. Raise them by hand when debugging a request or a reconnect. |

## `black_bloc/__init__.py`

| Key | Note |
|---|---|
| `black_bloc/__init__.py:1` | The version reported by `/about` (`cogs/core.py:101`) and the API `/health` (`api/server.py:24`). ⚠️ Note it is stated a second time in `pyproject.toml:3`; the two are not linked and can drift. |

## `black_bloc/__main__.py`

| Key | Note |
|---|---|
| `black_bloc/__main__.py:3` | Makes `python -m black_bloc` work. ⚠️ **Never run it locally while the Fly machine is up** — two gateway sessions on one token means every command answered twice and every announcement posted twice. Stop the Fly machine first (`../access/deploy.md`, "Pause the bot"). |

## `black_bloc/storage/db.py`

| Key | Note |
|---|---|
| `black_bloc/storage/db.py:163` | Written into `schema_meta` on every `connect()`, so the file on disk always states which schema wrote it. It is the key the first numbered migration will branch on. ⚠️ **Bumped to 10** by the temp-voice panel + `/voice` merge (2026-08-27): `tempvoice_channels.panel_channel_id` is 9 and `tempvoice_prefs.bitrate` is 10, both additive through `ADDED_COLUMNS` (`:406`). Before that Phase 7 (the four `modmail_*` tables) took it to **8**, skipping **7** on purpose — that number belonged to Phase 6, built in parallel on its own branch, so 8 was a label rather than a claim that 7 ever ran. Before that Phase 5 took it to 6 (`birthdays`) and Phase 4 to 5 (`user_timezones` and `events` in one version) and Phase 3 to 4 (the two `tempvoice_*` tables, then `honeypot_hits`); the bump is a statement about the file, not a migration — every statement below is still `IF NOT EXISTS`. ⚠️ **Deliberately unbumped after the Phase 2 review fixes**: the column and index they add are additive and idempotent, so nothing on disk needs a version to branch on. The version moves when a change cannot be expressed that way. |
| `black_bloc/storage/db.py:13` | **Additive only** (`CREATE TABLE IF NOT EXISTS`). The first non-additive change becomes a numbered migration keyed on `schema_meta.schema_version` — never an edit to a statement that has already run somewhere (`architecture.md`, rule 5). Phase 1's four tables and Phase 2's `golive_links` / `golive_optout` / `golive_sessions` are appended here for the same reason: one schema, one place, no per-feature bootstrap. ⚠️ `golive_sessions.ended_at IS NULL` **is** the "currently live" flag — the debounce and the restart behaviour both read it, so nothing may write a session row without an `ended_at` plan (`black_bloc/golive.py:285`). The partial unique index at the end of the block is what makes "one open session per member" a **database** fact rather than a hope: the presence listener and the Twitch poller can race, and `start_session` (`cogs/content/golive.py:180`) reads the integrity error as "already open". |
| `black_bloc/storage/db.py:129` | Phase 3's two tables, appended like every other (`CREATE TABLE IF NOT EXISTS`). `tempvoice_channels` is the whole restart story for temp voice: a channel with no row is not ours and is never deleted, and a row with no channel is forgotten at the next reconcile (`cogs/community/tempvoice.py:1451`). `tempvoice_prefs` is keyed by **user**, not by channel, on purpose — it is what makes the next channel someone makes come back with the name, cap, lock and hide they last chose. |
| `black_bloc/storage/db.py:406` | ⚠️ **The pattern Phase 3 follows for a new column.** `CREATE TABLE` statements that have already run somewhere are never edited (rule 5), so a column is added by naming it here and letting `_add_missing_columns` do an `ALTER TABLE … ADD COLUMN` when a `PRAGMA table_info` says it is absent. That is idempotent on a fresh file and on the live Fly volume alike, and it needs no version bump. `live_role_added` exists because "was the live role actually put on this member?" cannot be re-derived from the mode later — the mode may have changed since (`cogs/content/golive.py:610`). `events.card_channel_id` was added the same way by review finding F14: while test mode is on the review card is posted to the **test** channel while `review_channel_id` names the review channel, so a `review_message_id` with no second column is a message id nothing can look up. `birthdays.role_added_id` is Phase 5's entry, added for the same reason as `live_role_added`: which role went on somebody cannot be re-derived from the setting the next day, because the setting may have changed (`cogs/community/birthdays.py:153`). `modmail_messages.delivered` is Phase 7's, added by its own adversarial review **without** a further version bump for exactly the reason this pattern exists: it is idempotent on any file. It carries `DEFAULT 1` so every row written before the column existed reads as delivered rather than as a mystery — `field_of` (`black_bloc/modmail.py:70`) is the other half of that promise. |
| `black_bloc/storage/db.py:412` | Schema **19**, and the whole change is this one line: `golive_sessions.live_role_id` records which role a session actually put on somebody, so the 0/1 `live_role_added` above it stops being the only evidence. Additive, so an existing file gains the column with a `NULL` in every historical row and nothing has to be rewritten — the removal path treats that `NULL` as "use today's setting", which is what those rows meant when they were written (`cogs/content/golive.py:613`). |
| `black_bloc/storage/db.py:435` | ⚠️ **Runs BEFORE the schema script, and that order is the whole point.** A database written before the partial unique index existed may already hold two open sessions for one member — exactly the race the index is being added to prevent — and `CREATE UNIQUE INDEX` on such a file **fails**, which would mean a bot that will not start. Collapsing the duplicates first (keeping the newest row) turns that into a warning. |
| `black_bloc/storage/db.py:449` | Lets a caller tell "no database yet" from "database broken" **without** touching `_conn`. `RoleMenus.cog_load` (`cogs/community/role_menus.py:1377`), `GoLive.cog_load` (`cogs/content/golive.py:313`) and every go-live command (`cogs/content/golive.py:787`) need exactly that: `tests/test_bot.py` loads every cog with no `connect()` ever called, and a cog that blew up there would take the offline-construction contract with it. |
| `black_bloc/storage/db.py:453` | Raises instead of lazily connecting, so forgetting `connect()` fails at the call site with a clear message rather than opening a second, empty database. ⚠️ It **raises**, so any command body that touches `db.conn` must check `is_connected` first or the person gets a traceback instead of a sentence. |
| `black_bloc/storage/db.py:459` | Parent directories are created so `DATABASE_PATH` can point anywhere — including a fresh path outside OneDrive, which is the fix for KI-1. |
| `black_bloc/storage/db.py:462` | ⚠️ WAL mode creates `-wal`/`-shm` sidecars. Inside a OneDrive folder — **and this repo is in one** — those can hit "database is locked" while OneDrive uploads mid-write (KI-1 in `../KNOWN_ISSUES.md`). Fix: `DATABASE_PATH` in `.env` pointing outside OneDrive. |
| `black_bloc/storage/db.py:479` | Returns quietly on a fresh file: `_table_columns` on a table that does not exist yet answers with an empty set, which is also how `_add_missing_columns` tells "not created yet" from "created without the column". |
| `black_bloc/storage/db.py:163` | Phase 4's first table, keyed by **user** and not by guild: someone's time zone is a fact about them, not about a server, and asking twice because they proposed an event on a second server would be a worse bot. It stores the IANA name (`America/Phoenix`), never an offset — an offset is wrong twice a year everywhere that keeps summer time. A name this machine cannot resolve reads back as unset (`timezones.py:92`) rather than raising inside a command. |
| `black_bloc/storage/db.py:169` | The `events` table, appended like every other. ⚠️ **`status` is the whole state machine and the only thing that decides what may happen next** — the transitions live in `black_bloc/events.py:33`, and nothing writes this column without going through `can_transition` first. `review_channel_id` is what the reconciler checks against reality; `scheduled_event_id` and `announce_message_id` record what was actually done rather than what the settings say should have been done, so a cancel can undo it whatever the mode has since become (checklist 3). The index at the end is what makes the five-minute reconcile and the one-minute go-live sweep cheap: both ask "which rows in this guild are in this status, oldest first". |
| `black_bloc/storage/db.py:191` | Phase 5's table, keyed by **user** like `user_timezones` above it, for the same reason: a birthday is a fact about a person. `guild_id` is stored beside it so the sweep knows where to wish them, not to key them. ⚠️ **`last_announced_on` is the whole restart story** — it is a *local* date string, not a timestamp, so a bot that restarts every five minutes still wishes somebody once (`cogs/community/birthdays.py:395`). `opted_in` is a column rather than a deletion so an opt-out survives a re-import. `role_added` records that a role went on; **which** role went on is `role_added_id`, added additively at `:250`. |
| `black_bloc/storage/db.py:204` | Phase 7's four tables and two indexes, appended like every other. ⚠️ **`modmail_open_ticket` (`:219`) is the partial unique index that makes "one open ticket per member" a DATABASE fact**, not a hope — the per-user lock above it (`cogs/moderation/modmail.py:384`) is per-process and a burst of DMs can outrun it, so both exist (checklist 6). It is the same shape as `golive_open_session` (`:126`), for the same reason. `modmail_tickets.channel_id` is written as `0` first and filled in once the channel exists, because the channel topic has to carry the ticket id (`cogs/moderation/modmail.py:181`); the reconciler ages out a row still holding `0`. `modmail_messages` is the transcript's only durable source once a ticket channel is deleted, which is why its rows are written **before** the send, not after (`cogs/moderation/modmail.py:295`). |

## `black_bloc/api/server.py`

| Key | Note |
|---|---|
| `black_bloc/api/server.py:14` | Runs in the **same asyncio loop** as the Discord client, so routes read bot state directly — no thread, no IPC, no second process. That is the whole reason FastAPI was chosen over Flask (`architecture.md`, "Why these libraries"). |
| `black_bloc/api/server.py:15` | `docs_url`/`redoc_url` are disabled because this server has **no auth yet** (KI-3); it should not advertise its own surface. Read `../KNOWN_ISSUES.md` before binding it to anything but localhost. |
| `black_bloc/api/server.py:133` | `latency` is meaningless before the client is READY, so `/health` reports `null` rather than a misleading number. |
| `black_bloc/api/server.py:42` | ⚠️ uvicorn installs its **own** SIGINT handler while `serve()` runs and re-raises the signal after the API shuts down. Expected: the first Ctrl+C stops the API and then the bot. If the bot ever appears to ignore Ctrl+C with `API_ENABLED=true`, this line is where to look (`gotchas.md`). |

## `black_bloc/cogs/core.py`

| Key | Note |
|---|---|
| `black_bloc/cogs/core.py:25` | ⚠️ The three pickers are **derived from the registry by type**, so a new settings key appears in exactly one of them and in no other list. This is the "a non-channel key means a second `set` subcommand, not a free-text field" note from Phase 1, cashed in: Phase 2 added enum/text/int/role keys, and without the split `/settings set` would have offered a channel picker for `golive_template`. |
| `black_bloc/cogs/core.py:90` | The always-loaded cog, and the **template every other cog copies**: a `commands.Cog` subclass in its own module plus a module-level `async def setup(bot)`. Cogs reach the DB via `bot.db` and config via `bot.settings`, and never import each other (`architecture.md`, rule 2). |
| `black_bloc/cogs/core.py:95` | `ephemeral=True` on both commands: liveness checks are for the caller, and an ephemeral reply cannot clutter a channel however often it is run. |
| `black_bloc/cogs/core.py:139` | `/settings` lives in **core**, not in its own cog, because it configures the bot rather than a feature (`phase1-design.md`, §1 — "keep it simpler"). Declaring the `app_commands.Group` as a class attribute is how `discord.py` 2.x binds a group to a cog instance; it needs no registration beyond the cog itself. |
| `black_bloc/cogs/core.py:149` | Rendering goes through `settings_store.display_value` rather than a `<#…>` template here, because the registry now holds roles, numbers, an enum and free text. One fact, one home: the type table decides how a value reads, and this loop does not know the difference. |
| `black_bloc/cogs/core.py:182` | The action log call comes **after** the reply, so a log-channel problem can never delay or break the answer the person is waiting for. `log_action` swallows its own Discord failures (`actionlog.py:272`). |
| `black_bloc/cogs/core.py:224` | ⚠️ **Beyond the letter of `phase2-design.md`, and deliberate.** The design's settings table adds role, text, int and enum keys but names no command that can set them, which would have left `golive_template` and the three role filters reachable only by editing SQLite. `parse_value` accepts a raw id or a `<@&…>`/`<#…>` mention so a pasted mention works; validation still happens in `coerce_value`, so this command adds a parser, not a second rule set. |

| `black_bloc/cogs/core.py:109` | ⚠️ **`/help` — the owner's ask, verbatim: "we also need a / command that vomits out every /command that can be run" (sweep batch 2, 2026-08-26).** It reads the **tree**, never a hand-written list, so a command added to any cog appears here the day it is registered and nothing can go stale. First page through `response.send_message`, the rest through `followup.send`, all ephemeral and all `allowed_mentions=none` — the same shape `/settings show` uses (`:152`), because a command list is already past Discord's 2000 characters at 30-odd commands. |
| `black_bloc/cogs/core.py:79` | Commands are **global** and copied into the dev guild by `command_sync.py:19`, so the tree answers two different questions depending on whether it is asked with a guild. Both are asked and merged by name: a guild-only command would otherwise be missing from the list of "every command that can be run **here**". |
| `black_bloc/cogs/core.py:58` | The rendering is a pure function over command objects — no `interaction`, no bot — so the walk through groups, subgroups and the `(staff)` marking is asserted without Discord. The filter keeps a group's heading when the group's own name matches, so `/help filter:tempvoice` still says what `/tempvoice` is before listing it. |
| `black_bloc/cogs/core.py:113` | ⚠️ **`/help` filters the tree through the visibility registry, because the tree alone would still list a hidden command.** `tree_commands` merges the global commands with the guild copies (`:79`), and hiding removes the command from the **guild** copy only — the global one is still there, so a name-merge would put `/rolemenu` back in the list while nobody can run it. Reading the stored mode instead (`command_visibility.py:38`) makes `/help` agree with reality during the five seconds the debounce is open, too. |

## `black_bloc/settings_store.py` — the only way a feature reads its knobs

| Key | Note |
|---|---|
| `black_bloc/settings_store.py:50` | ⚠️ **The floor is 1 day, not 0** (review finding F3e). Zero deleted a finished event's channel on the first sweep after it ended, which is before anybody has read what happened in it — a tidy-up that destroys the record it was tidying. The old wording actively recommended it, so `KEY_MAX_REASON` lost that sentence in the same edit. |
| `black_bloc/settings_store.py:52` | How late an event may start and still be announced (review finding F2). Fifteen minutes is a restart, a rate-limit stall or a short outage; an hour is an event half over. Past it the row still goes `live` — the state must stay true — but nothing is posted and nobody is pinged, and the log says `event.announce_skipped_late` so the silence is a recorded decision rather than a missing message. |
| `black_bloc/settings_store.py:186` | The mirror of `KEY_MAX`, and it exists for exactly one key. It is separate from the `value < 0` check above it because "negative" is a type error every int setting shares, while a floor is a policy about one setting and needs its own sentence to be worth refusing for. |
| `black_bloc/settings_store.py:30` | ⚠️ **The `#live-now` id and the incumbent's exact wording, both measured** (`../archive/current-bots/discord-scan-2026-08-26.md` §G, 199 YAGPDB posts). The template is the migration promise: the same sentence the server has read for years, with `{game}` no longer able to render as `****`. Changing this string changes what every member sees — treat it as a user-facing sentence, not a constant. |
| `black_bloc/settings_store.py:41` | The four temp-voice facts that are *defaults*, so they live with the other defaults rather than in the cog (checklist 15). `MEMBER_ROLE_ID` is measured — the `Member` role from the same-day scan (`phase3-design.md`, Part A) — and it is what join-to-create checks before making anybody a channel. ⚠️ `TEMPVOICE_CREATOR_NAME` moved here from the cog in the 2026-08-26 sweep fixes and became a real setting (`tempvoice_creator_name`): the lobby on the live server was called `join`, and a name with no home cannot be checked or put back (`cogs/community/tempvoice.py:1667`). |
| `black_bloc/settings_store.py:349` | The database-is-down sentence, said by **three** cogs now (go-live, temp voice, honeypot). It moved here from `cogs/content/golive.py` in Phase 3 rather than being copied a second time: one wording, one home, and cogs never import each other (`architecture.md`, rule 2). |
| `black_bloc/settings_store.py:401` | ⚠️ **`channels`/`roles` are LIST types, and nothing in `/settings set` can reach them** — `cogs/core.py:25` builds its pickers from the exact type strings `channel`, `role`, `enum`, `int`, `text`, `bool`, so a list key is invisible there by construction. That is deliberate: `tempvoice_creator_ids` and `honeypot_channel_ids` are filled in by `/tempvoice setup` and `/honeypot setup`, which know the channel they just made. Duplicates are dropped rather than refused, so running setup twice cannot grow the list forever. |
| `black_bloc/settings_store.py:777` | A list key defaults to a **fresh** `[]` on every call, never a shared module-level list — a cog that appended to the default would otherwise change the default for every guild that has not set one. |
| `black_bloc/settings_store.py:88` | ⚠️ **The registry IS the validation.** A key not in this dict is refused by `get`, `set` and the `/settings` pickers alike, so a typo can never create a phantom setting that silently reads back `None` forever. Adding a feature knob = adding a row here plus a `KEY_HELP` line; nothing else. The type string also decides which `/settings` subcommand can reach it (`cogs/core.py:25`). |
| `black_bloc/settings_store.py:345` | Lives in this module, not in a cog, because **both** cogs say it and cogs never import each other (`architecture.md`, rule 2). Same reason as `require_staff` below. |
| `black_bloc/settings_store.py:360` | Pure on purpose: the whole type check is one testable function with no DB and no Discord. `getattr(value, "id", value)` means a `discord.TextChannel`/`Role` and a raw id are both acceptable at the call site; `isinstance(raw, bool)` is rejected explicitly in the channel, role and int branches because `bool` is an `int` in Python and `True` would otherwise be stored as channel 1. |
| `black_bloc/settings_store.py:498` | The *parser*, kept separate from the *validator* above. Discord hands a slash-command string; this turns it into the type the registry wants and then `coerce_value` decides whether it is acceptable. Two functions rather than one so the free-text path cannot grow its own, second set of rules. |
| `black_bloc/settings_store.py:521` | The mirror image of the parser: one place decides how each type reads back, so `/settings show` (`cogs/core.py:144`) and any future surface cannot disagree about whether a role renders as `<@&id>` or a bare number. |
| `black_bloc/settings_store.py:537` | ⚠️ **Staff is derived from what a role can actually SEE, not from the overwrites written on the staff channel.** The Phase 3 review found the overwrite reading returned `set()` on a real server: a staff channel that inherits its visibility from its **category**, or that is simply hidden from `@everyone` with no per-role `view_channel=True` written on it, carries no matching overwrite at all — so nobody was staff, and the honeypot's staff exemption exempted nobody. `channel.permissions_for(role)` (discord.py 2.x takes a `Member` **or** a `Role`) does the whole inheritance calculation for us. `@everyone` is still excluded deliberately — a staff channel `@everyone` can view would otherwise make the entire server staff — and **bot-managed** roles are excluded because an integration's own role sitting in the staff channel is not a person. `perms_for` is injectable purely so the test can assert inheritance without building a guild. A channel that cannot answer the question at all resolves to nobody, loudly: this runs inside a message event, where a raise is invisible. |
| `black_bloc/settings_store.py:612` | The staff gate every cog calls. It **answers the interaction itself** and returns a bool, so a command body is one `if not await require_staff(...): return` — a check that returns only a bool invites a caller to forget the reply and leave the person staring at "the application did not respond". |
| `black_bloc/settings_store.py:676` | ⚠️ **Defaults fail closed toward the test policy.** While `TEST_MODE` is on, the log, staff **and go-live** channels default to `TEST_CHANNEL_ID` — the only place the bot may speak — so an unconfigured guild cannot cause a post somewhere else; `golive_channel_id` only becomes `#live-now` once test mode is off. `golive_mode` defaults to `shadow` for the same reason: the feature computes everything and posts nothing until the owner says otherwise (`phase2-design.md`, §Modes). `log_channel_id` deliberately has **no** default once test mode is off: silently logging to some guessed channel is worse than not logging (`actionlog.py:147` warns instead). `golive_max_session_hours` defaults to **12** because it is a backstop, not a policy: a stream longer than half a day is rarer than a session row that a crash left open, and the cost of closing a real one early is one duplicate announcement after the cooldown, while the cost of never closing it is that member never being announced again (`cogs/content/golive.py:643`). Set it to `0` to turn the backstop off. ⚠️ **Phase 7's four modmail branches at the end of the chain fail closed harder than any before them**, and one of them is a deliberate `None`: `modmail_enabled` defaults **false** so the incumbent ModMail bot keeps the inbox until the owner flips it, and `modmail_category_id` returns `None` while test mode is on rather than the real category — the cog reads that as "use the test channel's own category, or refuse", because a `None` handed to `create_text_channel` is not "nowhere", it is the top level of the server, in public (`cogs/moderation/modmail.py:408`). `modmail_staff_channel_id` has **no branch here at all** and falls through to `None` on purpose: its fallback to `staff_channel_id` lives in one place in the cog (`cogs/moderation/modmail.py:395`), because a default copied into this chain would freeze whatever the staff channel was the day the key was added. |
| `black_bloc/settings_store.py:781` | Read once at startup (`bot.py:59`) into a dict keyed `(guild_id, key)`. That is what lets `get()` be **synchronous**: settings are read in command bodies, in a select handler and in a presence event, and an `await` per knob would put a database round trip in the hot path. Writes go through `set()`, which updates both DB and cache, so the two cannot drift. ⚠️ **A row whose key is no longer in the registry is SKIPPED and named once in a warning, never fatal** (owner ask, 2026-08-27, when `carl_modlog_channel_id` was retired). A retired key's row survives on the live volume long after the code that wrote it is gone, and the alternative to skipping it is either a startup crash or a phantom cache entry `get()` would refuse anyway. Unreadable JSON takes the same path, for the same reason: `load()` runs before the gateway is up, where a raise is a bot that never starts. |
| `black_bloc/settings_store.py:827` | Values are stored as **JSON**, not as text or integers, so `golive_template` (a string), `golive_cooldown_minutes` (a number) and the ids all live in one column without a schema change. `updated_by`/`updated_at` exist so "who changed this and when" is answerable from the table alone, without cross-referencing the action log. |
| `black_bloc/settings_store.py:29` | ⚠️ **Renamed from `GOLIVE_CHANNEL_ID` in Phase 4, and the rename is the point.** `#live-now` is now the default for *two* features — go-live announcements and event announcements — and a constant named after one of them would have invited a second copy of the same id for the other (checklist 15). One id, one name that is true for both callers (`:550` and `:574`). |
| `black_bloc/settings_store.py:231` | ⚠️ **The ceiling message had to stop being about bans.** The single shared sentence at `:293` explained every capped value as "Discord refuses to delete more than N days of a banned account's messages" — correct for the one key that existed, and a flat lie the moment `events_channel_retention_days` became the second. Each cap now carries its own reason; the honeypot's is byte-identical to what it was, because `tests/test_settings_store.py` and the owner both read it. |
| `black_bloc/settings_store.py:839` | ⚠️ **The missing half of the registry: a scalar setting had no way to be forgotten.** A list key drops an entry (`:293`), but `events_category_id` pointing at a category somebody deleted could only ever be re-pointed, never cleared — so `/settings show` would name a dead channel forever and `events_category` (`cogs/community/events.py:457`) could not tell "not configured" from "configured wrong". Deleting the row rather than storing a sentinel is what makes `get()` fall back to the **default** again, which is the behaviour "forget this" actually means. ⚠️ **ONE implementation, arrived at from two directions** (checklist 15): Phase 4 and Phase 5 each wrote a `clear`, and the merge kept Phase 5's, which is the strict superset — it takes `by` and **returns whether a row was actually deleted**, so a command can tell "unset" from "there was nothing to unset" rather than claiming a change that did not happen. The cache entry goes with the row, so nothing has to be reloaded. Phase 4's callers ignore the return value and are unaffected. |
| `black_bloc/settings_store.py:174` | The only per-key **maximum** in the registry, and it exists because one number can break every ban. `honeypot_purge_days` is handed to Discord as a delete window and Discord's ceiling is 7 days — 8 is not clamped by the API, it is a **400 on every single ban**, which the honeypot would log as `ban_failed` forever with nothing naming the real cause. One entry rather than a branch in `coerce_value`, so the next capped key is a row here and not another `if`. |
| `black_bloc/settings_store.py:467` | The refusal that stops the number above being set. It is a **sentence naming Discord's limit**, not "invalid value": someone typing 30 there is thinking in days of spam history and needs to be told the ceiling is not ours. `do_ban` (`cogs/moderation/honeypot.py:210`) clamps as well, because a value stored before this validator existed is still on disk. |
| `black_bloc/settings_store.py:598` | Renders the resolved staff roles for `/honeypot status`. Counting **and** naming them is the point: a count alone cannot tell "the two roles I expected" from "some integration's role", and reading that status line is how the owner checks this feature. |
| `black_bloc/settings_store.py:854` | ⚠️ **One home for "who is staff".** Every caller — `require_staff`, and so every staff slash command and the role-menu assign flow, plus the honeypot's exemption matrix — reaches staff through this pair, which is why the Phase 3 fix to the derivation landed everywhere at once. A second derivation anywhere is the bug this shape exists to prevent (checklist 15). |

| `black_bloc/settings_store.py:639` | ⚠️ **How `/help` knows a command is staff-only, and why it READS the body instead of a marker.** The gate is a call in the command body (`:566`), not a decorator, so there is nothing on the command object to look at. A `staff_only` extra or a decorator would have meant editing ~50 command definitions in nine files, and — worse — it can go **stale silently**: the next staff command added without the marker is listed as if anyone could run it. Reading `co_names` cannot go stale, because it is the actual call that gates the command. One hop is followed on purpose (`self._ready`, `decision_context`), which is how `/warn` and the modmail commands are marked; a gate two calls away is left **unmarked rather than guessed at** (owner's instruction: omit the suffix rather than guess). An explicit `extras={"staff_only": …}` still wins if a future command sets one. |
| `black_bloc/settings_store.py:659` | ⚠️ **The change hook, and the reason it lives on the store rather than on each caller.** Every surface that changes a setting — `/settings set-value`, `/rolemenu mode`, `PUT /api/settings/{key}` — goes through `set`, so one registration here is one trigger path for all of them (`command_visibility.py:204`). Callbacks may be sync or async, and a callback that raises is logged and **skipped**: a hook is a reaction to a write that has already been committed, so it must never be able to undo the write or take the next hook down with it. `clear` fires it too, with the key's *default*, because forgetting a row changes the effective value exactly as much as setting one does. |

## `black_bloc/actionlog.py` — one row and one embed, every time

| Key | Note |
|---|---|
| `black_bloc/actionlog.py:29` | Discord caps an embed field value at 1024 characters. The limit is lower than that because the JSON is wrapped in a code fence, and a log post that 400s tells nobody anything. |
| `black_bloc/actionlog.py:63` | Fields appear only for what was actually passed, so a two-argument call does not produce an embed full of "—". Pure and free of I/O, which is why the test can assert field names and order without a bot. |
| `black_bloc/actionlog.py:107` | ⚠️ **Row first, post second, and the order is the contract.** The DB row is the record of truth; the embed is a convenience for whoever is watching. Every later feature calls this for anything it does to a member or a channel (`phase1-design.md`, §2). |
|  `black_bloc/actionlog.py:154` | ⚠️ **The broad `except` is deliberate and must stay.** A 403, a deleted log channel, a `TestModeViolation` from the guard — none of them may undo or interrupt the action being logged, which has *already happened* by the time this runs. It is a `log.warning`, never a raise, and never a silent `pass`: a log channel that stopped working has to be visible in the process log. |

## `black_bloc/cogs/community/role_menus.py` — F16

| Key | Note |
|---|---|
| `black_bloc/cogs/community/role_menus.py:27` | Measured, not invented: the menus and role ids come from the same-day scan of Carl-bot's panels (`../archive/current-bots/discord-scan-2026-08-26.md` §B/§D and `yagpdb-dashboard-2026-08-26.md`), transcribed in `phase1-design.md`. ⚠️ Phase 3 replaced the 🎮 placeholder on Marathons with Carl's **real** custom emoji and added `runner-status` in `staff` mode. Seeding stays idempotent, which means a guild that already ran the Phase 1 seed keeps the placeholder: `seed` **says so** rather than rewriting options behind the owner's back (`phase3-design.md`, Part C). |
| `black_bloc/cogs/community/role_menus.py:166` | ⚠️ **Custom emoji are stored as the `<:name:id>` string and only become a `PartialEmoji` here, at render time** (checklist 14). `PartialEmoji.from_str` never raises — handed something that is not an emoji it returns a *unicode* emoji whose name is the whole string, which Discord then rejects with a 400 and takes the entire panel with it. So an id-less result is treated as no emoji at all: one option loses its picture instead of the panel failing to post. |
| `black_bloc/cogs/community/role_menus.py:473` | The staff-assigned mode: no panel, no self-serve, one ephemeral select per `/rolemenu assign`. It shares `role_diff` and `apply_diff` with the self-serve select on purpose — the "only ever touch roles this menu owns" guarantee (`:145`) is the same guarantee, and a second implementation of it would be a second chance to get it wrong. `unassign` is *not* a diff: it removes exactly what was picked, because a staffer taking Runner off somebody must not silently add the two roles they left unticked. |
| `black_bloc/cogs/community/role_menus.py:499` | The same test-policy line as the self-serve select (`:403`), for the same reason: this hands out roles to a **third party**, and a role edit is invisible to `guard.py`. |
| `black_bloc/cogs/community/role_menus.py:742` | A `staff`-mode menu has no panel to post, and the refusal names the two commands that do work instead — an owner rule: a refusal says what happened, what it needs and how to get it. |
| `black_bloc/cogs/community/role_menus.py:145` | ⚠️ **This string is a persistence key, not a label.** `discord.py` matches an incoming component interaction to a registered persistent view by `custom_id`; change the format and every panel already posted in the server goes dead with no error anywhere — the click just spins. `parse_custom_id` is its inverse and exists so the format is asserted in one test rather than assumed in five places. |
| `black_bloc/cogs/community/role_menus.py:156` | ⚠️ **The migration-safety rule in one function.** `selected & menu` and `current & menu` mean the bot only ever touches roles this menu owns: a role somebody got from Carl, from a mod, or from another panel is invisible to it. That is what makes posting our panels beside the incumbent ones safe, and it is why the three diff tests are the ones to keep if any others are ever dropped. |
| `black_bloc/cogs/community/role_menus.py:183` | Discord caps a select at 25 options, and `max_values` may not exceed the option count; `single` mode is just `max_values=1`. The floor of 1 exists because a select with `max_values=0` is rejected by the API — an empty menu is refused earlier, at `post`. |
| `black_bloc/cogs/community/role_menus.py:316` | Re-adding a role that is already on the menu **keeps its position** rather than moving it to the end, so `/rolemenu add` doubles as "rename this option" without silently reshuffling a panel people have learned the shape of. |
| `black_bloc/cogs/community/role_menus.py:434` | ⚠️ **The test-policy line that the HTTP gate cannot cover.** A role edit is not a message, so `guard.py`'s `send_message` gate never sees it, and component interactions do not run `tree.interaction_check` either — a panel posted before the policy, or dragged to another channel, would otherwise still hand out roles anywhere. Owner rule, `phase1-design.md` §"Test mode and permissions"; do not remove it when test mode is eventually lifted, it is a no-op then (`bot.guard is None`). |
| `black_bloc/cogs/community/role_menus.py:394` | `guild.id` **is** the `@everyone` role id, and `member.edit(roles=...)` must not be handed it — Discord rejects the default role in that list. The list is rebuilt whole rather than using `add_roles`/`remove_roles` so one click is one API call and one audit-log entry, not four. |
| `black_bloc/cogs/community/role_menus.py:567` | Re-registers a persistent view for every stored panel so old messages keep working across restarts — that is the entire point of `custom_id` + `timeout=None`. The `is_connected` check is not defensive noise: `tests/test_bot.py` loads every cog with **no database connected**, and that offline-construction contract (`architecture.md`, rule 6) outranks this cog. |
| `black_bloc/cogs/community/role_menus.py:635` | Unmanageable roles are refused **here, at `add` time**, with a sentence naming the fix — not at click time. A member who clicks a panel and gets a permissions lecture cannot do anything about it; the staffer configuring the menu can (`phase1-design.md`, §3). |
| `black_bloc/cogs/community/role_menus.py:767` | `defer` then `followup`, because posting the panel is a round trip to Discord and the 3-second interaction deadline is not generous. The reply carries `message.jump_url` so the staffer can check the panel without hunting for it (owner rule: anything visible ships with its link). |
| `black_bloc/cogs/community/role_menus.py:370` | Re-posting **edits the existing message** when it is still there and still in the same channel, so a panel keeps its place in the channel and its reactions history instead of leaving a trail of dead copies. A gone message is not an error — it posts fresh and stores the new ids. |
| `black_bloc/cogs/community/role_menus.py:204` | ⚠️ **One heading, one option line, three commands.** `/rolemenu show` and `/rolemenu showall` render the same two things, and before the sweep fixes `show` built both inline — so `showall` would have been a third copy of the same f-strings (checklist 15). `menu_heading` also carries **posted / not posted**, which `show` did not say at all: "is this panel actually up" is the question the owner was asking when he asked for `showall`.
| `black_bloc/cogs/community/role_menus.py:708` | Owner sweep finding: `/rolemenu showall` — every menu, its title, its mode, whether it is posted, and each option's emoji, label and role, in one command. It uses `pages_under_limit` (`modcases.py:402`, the same 1900-character chunker `/settings show` and `/case list` use) rather than a fourth private splitter, and the **first** page is the interaction response with the rest as ephemeral followups — one round trip for the common case, no `defer` needed. ⚠️ Every page carries `allowed_mentions=none`: the option lines are full of `<@&id>` role mentions, and a staff role mention pings the staff (checklist 11). `show` was missing that and got it in the same edit.
| `black_bloc/cogs/community/role_menus.py:134` | The "no menus yet" sentence said by **two** commands now (`list` and `showall`), so it is a constant rather than two literals that will drift the day the seed command is renamed.
| `black_bloc/cogs/community/role_menus.py:648` | ⚠️ **The seed is six menus, not five**, and every sentence that counts them now says so — the command description, the empty-list hint and `seed_default_menus`'s docstring all still named five after `runner-status` was added. ⚠️ **The command is `/rolemenu seed-defaults` since 2026-08-27** (owner: the incumbent is gone, so no user-facing string names it) and its description no longer counts the menus at all, which is why `tests/cogs/community/test_role_menus.py`'s "every sentence counts them" test now asks for two occurrences of "six" rather than three. `create`'s `mode` description names `staff` for the same reason: a picker offering three values while describing two is a picker people choose wrong. |

### The off switch — `rolemenu_mode` (owner ask, 2026-08-27)

> *"let's turn off all role selection stuff but do it in a way we can turn it
> back on with ui."* One enum key, default **off**, and the panels are left
> exactly where they are.

| Key | Note |
|---|---|
| `black_bloc/settings_store.py:841` | ⚠️ **`rolemenu_mode` defaults to `off`, and it is the only feature key that ships off rather than `shadow`.** There is nothing to shadow: a role menu has no "compute it and post nothing" middle state — either a click changes roles or it does not — so the two values are `off` and `on` (`:39`, `ROLEMENU_MODES`). It is appended to `KEY_TYPES` (`:183`) rather than filed beside `role_menu_channel_id`, which is what puts it in `mode_keys()` (`api/status.py:89`, every key ending `_mode`) and so on the Overview's mode chips with no change to either. The namespace it lands in is `rolemenu` (`api/settings_api.py:52`, the prefix before the first `_`) — a one-key namespace, unlike the `modlog`/`mod` ones the reconciliation folded away, because role menus are a real feature with their own tab and their own switch on it. |
| `black_bloc/cogs/community/role_menus.py:1570` | The one reader of the key, so the four refusal sites and the API's post route cannot drift about what "on" means. `bot.store.get` is synchronous (`settings_store.py:865`), which is why a component callback can ask it without an `await` in the click path. |
| `black_bloc/cogs/community/role_menus.py:1205` | ⚠️ **The refusal is answered, not swallowed.** A select whose callback returns without responding leaves the member looking at a permanent spinner (checklist 30). The sentence names both ways back — the dashboard's Role menus tab and `/rolemenu mode on` — because a member who clicks a dead panel has to be able to tell somebody *what* to turn on. Same sentence at `:1372` (the staff-assign select), `:1947` (`/rolemenu post`), `:2037` (`/rolemenu assign` and `unassign`, which share `_staff_pick`) and `api/tools/rolemenus.py:228` (the dashboard's Post button, as a 409). |
| `black_bloc/cogs/community/role_menus.py:1969` | ⚠️ **Where the check sits is deliberate: LAST, after everything else about the request has been judged.** `/rolemenu post ghost` still says there is no such menu, a `staff`-mode menu still says it has no panel, and an empty menu still says it has no roles — "role menus are off" is only said about a request that would otherwise have worked. The API's post route (`api/tools/rolemenus.py:38`) is placed the same way for the same reason, and `site/mock/server.mjs:1130` mirrors it. |
| `black_bloc/cogs/community/role_menus.py:121` | ⚠️ **Panels are TAKEN DOWN while off** — superseding the original "panels stay posted" default, which the owner overturned on 2026-08-27 (*"Panels get turned off when off"*). `rolemenu_panels.py:134` deletes them on the flip and posts them again on the way back, so this sentence is now only reached by a click that beat the sweep, or by a panel the guard refused to delete. ⚠️ `create`, `add`, `remove`, `show`, `showall`, `list`, `delete` and `seed-defaults` all keep working while off: staff prepare the menus, then flip the switch. The tab says the same in its own helper text (`site/public/assets/page-rolemenus.js:668`). |
| `black_bloc/cogs/community/role_menus.py:865` | The other half of `posted_menus` (`:429`), and the pair the mode switch reconciles between: a row with a `channel_id` and no `message_id` is a menu that **remembers where it belongs**, which is what lets turning the mode back on land the panel in the same channel without asking anybody. |
| `black_bloc/cogs/community/role_menus.py:732` | ⚠️ **The inverse of `set_message` (`:617`), and it deliberately clears only the message.** Wiping `channel_id` too would make `off` a destructive act — the menu would forget where it lived and the owner would have to pick a channel again for every menu on the way back. |
| `black_bloc/cogs/community/role_menus.py:2070` | `/rolemenu mode` is the slash half of the dashboard switch, logged as `role_menu.mode` so the audit tab shows who turned role selection on or off. Modelled on `/tempvoice mode` (`cogs/community/tempvoice.py:1766`); the reply says what happens next, because "now off" alone does not tell a Lead the panels are still up. |
| `site/public/assets/page-rolemenus.js:91` | ⚠️ **Not `settingRow`.** The automod tab renders its arming switch through the ordinary settings row (`page-automod.js:96`) and that is right for a three-value enum in a list of other keys; this is a two-value switch that has to be the first thing on the tab, so it is a card with the state as a `modeChip` and one enabled button. It writes through `saveSetting` — the same `PUT /api/settings/{key}` the Settings tab uses — so a refusal arrives as the bot's own sentence, and it repaints the chip from the **stored** value the API echoed back rather than reloading the page. |
| `site/public/assets/app.js:32` | `rolemenu` → the `rolemenus` tab, which is what makes the Overview chip for this key a link to the switch that changes it rather than a dead chip. The feature name is the key's prefix, so it is `rolemenu` and the tab is `rolemenus`; this map is the only place that knows they differ. |
| `site/mock/server.mjs:721` | The mock's feature list is now **derived** from its own `SETTING_SPECS` (every key ending `_mode`) instead of a hand-written array of seven names, which is `api/status.py:89`'s rule in the mock's own terms — adding a mode key to one half no longer needs a matching edit in the other. |
| `site/mock/check.mjs:160` | ⚠️ **The contract check has to turn role menus on before it can see the post route at all.** With the key off, `POST /api/rolemenus/{name}/post` answers 409 — which would have made the guard pass (`GUARDED`) go green for the wrong reason and the shape pass (`checkRoutes`) fail outright. `tests/api/test_contract.py`'s `seeded` fixture sets the same key for the same reason, beside `events_create_scheduled`. |

## `black_bloc/cogs/community/tempvoice.py` — F8

| Key | Note |
|---|---|
| `black_bloc/cogs/community/tempvoice.py:1189` | The panel, the member picker and both modals carry `AnswersErrors` (`command_errors.py:43`) as their FIRST base, so the mixin's `on_error` wins the MRO over `discord.ui`'s logging default. Review finding F6: a raise inside any of them used to be a library log line and a control that did nothing. |
| `black_bloc/cogs/community/tempvoice.py:28` | `now_iso`/`parse_ts` are **imported** from `golive.py` rather than copied. `golive.py` is a plain module, not a cog, so rule 2 allows it, and the alternative was a second copy of the "an unreadable timestamp counts as old" rule — the exact shape checklist 15 exists to catch. Lifting both into a shared module is a refactor that would touch go-live's tests, which Phase 3 does not. |
| `black_bloc/cogs/community/tempvoice.py:41` | An empty channel is only deleted by **reconciliation** once it is a minute old. Creation and the move-in are two API calls: a reconnect landing between them would otherwise delete a channel a member is about to appear in. The ordinary path — the last person leaves — deletes immediately and does not consult this (`:1447`). |
| `black_bloc/cogs/community/tempvoice.py:197` | ⚠️ Checklist 17, staff-editable text: `tempvoice_name_template` is set by a person, and this runs inside a voice event where a raise is invisible. A broken template renders the **default** name and says so in the log. The 100-character cut is Discord's own channel-name limit — a longer name is a 400 from the API, i.e. no channel at all. |
| `black_bloc/cogs/community/tempvoice.py:228` | ⚠️ **Positions in `discord.py` are the *sort order*, and inserting at a position pushes the existing occupant down.** So taking the AFK channel's own number is what puts the creator channel directly *above* it (owner decision, `phase3-design.md`, Part A), and a spawned channel takes the creator's number + 1. Both are pure functions purely so this can be asserted without a guild. |
| `black_bloc/cogs/community/tempvoice.py:304` | ⚠️ **A channel created with an explicit `overwrites=` dict does NOT inherit its category's.** Discord copies the category's overwrites onto a new channel only when none are given; pass a dict and that dict is the whole permission set, so a lobby made inside a locked-down category would come out **public**. Every overwrite this cog builds therefore starts from a **copy** of the category's own — a copy, because `PermissionOverwrite` is mutable and editing the live category object would change the category itself. |
| `black_bloc/cogs/community/tempvoice.py:312` | The one place "may join" is spelled out, and it is additive: `view_channel` and `connect` are set to `True` on top of whatever the category already gave that role, never as a fresh overwrite that would drop the category's other grants. `**extra` is how the bot picks up `manage_channels`/`move_members` without a second near-identical function (checklist 15). |
| `black_bloc/cogs/community/tempvoice.py:326` | ⚠️ **The fix for the owner's sweep finding "it made a locked channel i cant get into. its just a lock icon."** Measured on the live server: `/tempvoice setup` had passed **no** overwrites at all, so the lobby took the category's — `@everyone` denied `read_messages`+`connect`, and the two staff roles allowed `read_messages`/`manage_channels`/`manage_roles` but **not `connect`**. Nobody without Administrator could join the join-to-create channel, which makes the whole feature unreachable, and Discord shows exactly that as a bare lock icon. The lobby now names, explicitly: `tempvoice_allowed_role_id` (Member by default), every **resolved** staff role (`settings_store.py:878` — computed visibility, checklist 21, not written overwrites), and the bot itself. `@everyone` is left exactly as the category has it. |
| `black_bloc/cogs/community/tempvoice.py:333` | The owner's controls are an **overwrite on the channel**, not a role: nothing is granted server-wide, and it disappears with the channel. A spawned channel gets the same allowed-role and staff allows as the lobby, for the same reason — a channel staff cannot enter is a channel staff cannot moderate. `@everyone` keeps whatever the category says unless the owner's remembered prefs say locked/hidden. |
| `black_bloc/cogs/community/tempvoice.py:461` | Every panel action saves exactly the field it changed and leaves the rest alone, because the panel changes one thing at a time — a whole-row write from a rename would silently reset the cap and the lock the same person set a minute earlier. |
| `black_bloc/cogs/community/tempvoice.py:806` | ⚠️ **The gate every panel click goes through, and the only place the test policy is enforced for this cog.** Component interactions do **not** run `tree.interaction_check` (`guard.py:147`), and a channel edit is not a message, so `guard.py`'s HTTP gate cannot see one either — same hole as the role-menu select (`cogs/community/role_menus.py:452`). It answers the clicker itself and returns `None`, so every callback is one `if ... is None: return`. |
| `black_bloc/cogs/community/tempvoice.py:1281` | One persistent view registered **once** in `cog_load`, with static `custom_id`s (`tempvoice:rename`, …) and no message id: the row that says which channel a click belongs to is looked up from `interaction.channel_id` instead. That is what lets every panel ever posted keep working across restarts without re-registering one view per channel. ⚠️ Change a `custom_id` and every panel already posted goes dead with no error anywhere. |
| `black_bloc/cogs/community/tempvoice.py:1380` | `add_view` runs **before** the `is_connected` check on purpose — the panel must answer clicks even when the database is unavailable, and its answer in that case is a sentence (`settings_store.py:365`), not a dead button. |
| `black_bloc/cogs/community/tempvoice.py:1415` | Reconciliation is asked for at `cog_load` (checklist 4) **and** at `on_ready`, because `setup_hook` runs before the gateway connects and the guild cache is still empty there — a reconcile that iterates `bot.guilds` at `cog_load` alone would be a no-op on every real start. Running it again on a reconnect is harmless: it is idempotent and grace-limited (`:35`). |
| `black_bloc/cogs/community/tempvoice.py:1422` | A row whose channel is gone is forgotten; a channel nobody is in is deleted. Both are scoped to guilds the bot can currently see, so an outage that empties the cache cannot make it forget every temp channel it owns. |
| `black_bloc/cogs/community/tempvoice.py:1460` | ⚠️ **Discord first, the row second, and the lock is what makes "delete once" true.** Voice-state events arrive in bursts — two people leaving together produce two events that both see an empty channel — so the per-channel lock plus the re-read of the row inside it is the whole defence (checklist 6; there is no unique index to fall back on here, the primary key is the channel id). A delete Discord refuses **keeps** the row, so the next reconcile tries again rather than stranding a channel nobody owns. |
| `black_bloc/cogs/community/tempvoice.py:1489` | The per-**creator** lock is the other half, and it exists **to serialise joiners on purpose** — the earlier note here had the reason backwards. A burst of joins on one lobby would otherwise interleave the read of `tempvoice_prefs`, the create and the move, and two members can be moved into the same freshly-made channel. Keying it on the creator channel means one lobby's joins are handled one at a time while a *second* lobby is unaffected; the cost is that the second joiner waits for one create, which is the intended trade. |
| `black_bloc/cogs/community/tempvoice.py:1506` | Order: create → row → log → move → panel. The row is written **before** the member is moved so that a crash between the two leaves a channel the reconciler owns rather than an orphan nobody will ever delete. A move that fails is logged as `tempvoice.move_failed` and does not undo the channel — the member can simply join it. |
| `black_bloc/cogs/community/tempvoice.py:1379` | ⚠️ **SUPERSEDED 2026-08-27 — this note used to say the panel is NOT posted in test mode, and that is no longer true.** It said the send was skipped and logged as `tempvoice.would_post_panel`, which meant nobody could press a button until test mode was lifted. The panel is now posted *into the test channel* and the `would_…` kind is gone; the reasoning and the three log kinds are in the F8 follow-up block below (`:372`). Asking the guard **before** sending is what survived, and is still the point: it turns a refusal into a log line instead of a traceback inside a voice event (same shape as `cogs/content/golive.py:466`). |
| `black_bloc/cogs/community/tempvoice.py:1649` | ⚠️ **Channel creation and member moves are invisible to `guard.py`**, so the test policy is enforced here by *place*: while a guard is installed, join-to-create only ever fires for a lobby in the **test channel's own category** (owner rule, `phase3-design.md`, Part A, §Test mode). A test channel the bot cannot see means it cannot prove where it is, and the answer is no. Do not remove this when test mode is lifted — it is a no-op then (`bot.guard is None`). |
| `black_bloc/cogs/community/tempvoice.py:1652` | The same rule from the other end: `/tempvoice setup` **puts** the lobby in the test channel's category while test mode is on, so the owner can try join-to-create without the bot touching the real voice area. Going live is re-running the command with the guard off, and it then goes directly above `guild.afk_channel` — falling back to a channel *named* "You Still Here?" (the server's AFK channel by name) and, failing that, to the bottom of the voice list with a sentence saying so. |
| `black_bloc/cogs/community/tempvoice.py:288` | ⚠️ **The per-channel lock lives on the BOT** — not on the cog, and not at module level. The panel is a `discord.ui.View`: a click arrives with an `interaction` and never with a cog, so the lock has to be reachable from `interaction.client`. A module-level dict is reachable too, and was the first attempt, but it outlives the event loop and a second loop borrowing a lock made in the first raises `bound to a different event loop`. Hanging it off the bot ties its lifetime to the client that owns the loop. |
| `black_bloc/cogs/community/tempvoice.py:299` | ⚠️ **`voice_states` is the truth about who is in a voice channel; `members` is a convenience that can be empty when the member cache is cold.** Deciding "nobody is left, delete it" from `members` is how a channel full of people gets deleted after a reconnect. Every emptiness question in this file goes through here — the delete path, the reconciler, Kick, Ban and Claim. |
| `black_bloc/cogs/community/tempvoice.py:859` | Answers through `followup` once the interaction has been deferred and through `response` otherwise, so every caller writes `await answer(...)` and none of them has to know which. Without it, adding a `defer` to one handler silently breaks that handler's replies. |
| `black_bloc/cogs/community/tempvoice.py:1189` | ⚠️ **Defer first, edit the channel second.** `channel.edit` is a rate-limited round trip that regularly outruns Discord's 3-second interaction deadline, and a rename that worked but missed the deadline shows the owner "the application did not respond" (checklist 8). The same shape is in `LimitModal`, `MemberPick.callback` and `_toggle` — every path that touches the API before it answers. |
| `black_bloc/cogs/community/tempvoice.py:1237` | ⚠️ **The action log is written BEFORE the clicker is answered, in all eight panel handlers.** The answer is a network call that can fail, and a failed answer must not take the record of a real permission change with it (checklist 12: the important thing first, cosmetics last). The reviewer found the original order wrong in all eight. |
| `black_bloc/cogs/community/tempvoice.py:1155` | Transfer re-reads the row **inside** the channel lock and refuses when the owner changed since the click, because the select is an ephemeral message that can sit open for three minutes while somebody else claims the channel. Handing it to a stranger's pick would silently undo that claim. ⚠️ The rule moved out of `MemberPick._transfer` into module-level `do_transfer` by the `/voice` merge, so the Transfer button and `/voice transfer` are now one implementation of it rather than two (checklist 15). |
| `black_bloc/cogs/community/tempvoice.py:1169` | ⚠️ **Claim is the read-decide-write race in this feature** (checklist 6): two people press it on an abandoned channel and both read the same owner. The lock plus a re-read is the whole defence, and the loser is told **someone else just claimed it** rather than silently overwriting the winner. Claiming also requires the clicker to be **connected**: a member banned from the channel keeps the panel in their client, and Ban now denies `view_channel` as well as `connect` so they cannot see it either. |
| `black_bloc/cogs/community/tempvoice.py:1391` | Reconciliation runs on a **loop** as well as at `cog_load` and `on_ready`, because both of those are start-up events: a channel orphaned by a delete Discord refused, or by an event the gateway dropped, would otherwise sit there until the next restart. Repeating is safe — idempotent, grace-limited (`:35`), and scoped to guilds the bot can currently see. `cog_unload` cancels it so a reload does not leave two loops running. ⚠️ The body catches its own `Exception` and records `last_ok_at`/`last_error` (checklist 28): a sweep that failed and a sweep that ran are otherwise indistinguishable, because `is_running()` says "the timer is ticking", not "the work is working". |
| `black_bloc/cogs/community/tempvoice.py:1375` | **Phase 8a contract.** `loop_health(name)` is how `api/status.py:109` reads this cog's health without knowing its attribute names, exactly as go-live (`cogs/content/golive.py:273`) and birthdays do. It answers for `_reconcile_loop` and **only** for it — the page asks every cog about every loop name it finds, so answering for a name this cog does not own would put another feature's health on the status page. |
| `black_bloc/cogs/community/tempvoice.py:1408` | ⚠️ **This handler is the difference between a feature that stops and a feature that says it stopped** (checklist 28). discord.py re-raises a non-HTTP exception out of a `tasks.loop` and the loop is dead for the life of the process, silently — the 8a merge left this cog as the only one with a loop and no `@loop.error`, so a single bad row would have stranded every temp channel until the next deploy with nothing on the status page to show it. It records the error, logs it, and restarts the loop; `on_ready` (`:1409`) restarts it too, for the case where the restart itself could not run. |
| `black_bloc/cogs/community/tempvoice.py:1673` | ⚠️ **The lobby's name is a SETTING now** (`tempvoice_creator_name`), not a constant in this file, and that is the second half of the sweep finding: the channel on the live server was called `join`, and nothing in this code truncates a name — proven by `channel_name` (`:191`), which is the only string handling here and is not on this path at all, and by the command's own parameter, which is optional and defaults to `None`. The one way to get `join` is for Discord to have **sent** `name: join`, i.e. a value typed into the optional field. So the name gets a home that can be read back, corrected and re-applied, and a name passed to `setup` is stored rather than used once and forgotten. |
| `black_bloc/cogs/community/tempvoice.py:650` | ⚠️ **`setup` REPAIRS the lobby it already has instead of refusing** (owner, sweep 2026-08-26). Refusing was correct about the danger — two lobbies is two channels that both make temp channels, one of which nobody remembers configuring — but it left the owner with a broken lobby and no command that could fix it: `forget` only drops the id, and deleting the channel by hand was the only route back. Repair puts the name and the overwrites back **in place**, keeps the id, and names any extra lobbies with `/tempvoice forget` rather than touching them. It is gated on `may_act_in` (`:155`) like every other channel change here, because a rename is a side effect `guard.py` cannot see. |
| `black_bloc/cogs/community/tempvoice.py:1709` | The other half of that: a lobby channel that is deleted is forgotten by `on_guild_channel_delete`, and `/tempvoice forget <id>` covers the case the bot was offline for. Without either, a dead id sits in the setting forever and sends every `setup` down the repair path against a channel that is not there. |
| `black_bloc/cogs/community/tempvoice.py:1655` | The allowed role and the resolved staff roles, resolved to **role objects** because that is what an overwrite key has to be — `discord.Object` would be written as a *member* overwrite by `Guild._create_channel`, which types every non-`Role` target as a member. An allowed role id that no longer resolves is logged and left out rather than guessed at, so a deleted role cannot silently become "nobody may join". |

| `black_bloc/cogs/community/tempvoice.py:213` | ⚠️ **The second recogniser, and the fix for sweep finding 2 (owner, measured 2026-08-26 23:25): after the batch-1 deploy `/tempvoice setup` made a SECOND lobby (`1542419019099807835`) instead of repairing the `join` one (`1542410969815453767`), because that id was not in `tempvoice_creator_ids`.** The write path has no gap — both the Phase 3 original (`c3bf360`) and the current command store the new id immediately after the create and before the reply (`:737`), and the only two things that remove an id are `/tempvoice forget` and `on_guild_channel_delete` (`:1721`), which fires only for a channel that really was deleted. So a lobby the store does not know is a lobby **this store never saw created**: made by hand, made by a bot process reading a different database (`DATABASE_PATH` defaults to a *relative* `data/black_bloc.sqlite3`, so a local run and the Fly volume at `/data` are two different stores — the repo's own copy holds no `settings` table at all, measured 2026-08-27), or one whose delete event removed it. ⚠️ **The live store is on the Fly volume and could not be read from this tree, so which of those happened is NOT established** — what is established is that until now the id was the *only* recogniser, so an unknown lobby always produced a second one. Name-in-the-target-category is now the second, compared case-insensitively after stripping. |
| `black_bloc/cogs/community/tempvoice.py:692` | ⚠️ **The id is stored BEFORE the repair is attempted** (checklist 12): adopting is the durable fact and the rename is cosmetic, so a repair Discord refuses still leaves join-to-create working and `/tempvoice status` honest. Every matching channel is adopted, not just the first, because the first is then repaired and the rest are named with `/tempvoice forget` by the sentence the repair path already had (`:682`) — the alternative, adopting one and silently leaving twins unlisted, is the failure this whole note exists about. `tempvoice.adopt` is its own log kind so "took over an existing channel" can never be read as "made one". |
| `black_bloc/cogs/community/tempvoice.py:1747` | Status names every voice channel in the target category that carries the lobby's name but is **not** in the id list, with the sentence that fixes it. Checklist 9 and 10: a status command that showed only what the store knows would show a tidy list while the server had two lobbies in it, and the owner's verification method is reading this command. |

### F8 follow-up — the panel in test mode, and `/voice` (2026-08-26)

> **Merged into `main` on 2026-08-27** and these keys were folded onto the merged file the
> same day — they no longer point at the branch `worktree-agent-aa87571126477eb8f`
> (`91c9c0b`, `af3dd55`, cut from `main` at `9d948ca`). The batch-2 lobby adoption work had
> landed on `main` in parallel, so the mapping followed only lines a diff calls **equal** and
> every key here is byte-identical to the line it names. The block stays separate from the
> block above it because it is a different day's reasoning, not a different file.

| Key | Note |
|---|---|
| `black_bloc/cogs/community/tempvoice.py:1655` | ⚠️ **The panel is now POSTED while test mode is on, into the test channel, and the old `would_post_panel` is gone.** Not posting it at all was defensible for a side effect (checklist 1) but the panel is a *message*, and the whole point of the feature is that somebody presses the buttons — the owner could not try a single control until test mode was lifted. This is exactly the trade `cogs/community/events.py:477` already made for the review card: the send is still the **guarded** send, so nothing reaches a channel the policy forbids, and the first line says which voice channel it controls. Three outcomes, three log kinds: posted in the voice chat → nothing extra; posted in the test channel → `tempvoice.panel_elsewhere` carrying both ids; no test channel to post in → `tempvoice.panel_failed` with reason `no_test_channel` (checklist 2 and 10). |
| `black_bloc/cogs/community/tempvoice.py:810` | ⚠️ **The panel no longer lives in the channel it controls, so `interaction.channel_id` is no longer the answer to "which channel is this?"** Three sources, in order: the id a modal or a select was constructed with (deterministic — a modal-submit interaction is not guaranteed to carry the message it came from), the **panel message id** looked up against `tempvoice_channels.panel_message_id` (which is why `panel_channel_id` now sits beside it), and finally the chat the click came from, which is what a panel sitting in its own voice channel still resolves by. Get this wrong and a click in the test channel edits the test channel. |
| `black_bloc/cogs/community/tempvoice.py:823` | `panel_context` hands back the row **and the resolved channel object**, because every handler needs both and each one resolving it separately is the second implementation this file exists to avoid (checklist 15). A row whose channel has vanished is answered with a sentence rather than an `AttributeError` inside a button. |
| `black_bloc/cogs/community/tempvoice.py:897` | ⚠️ **One helper per action, called by the button AND by the slash command, returning the sentence rather than sending it.** The logic used to live inside the button callbacks; `/voice rename` would have been a second copy of the rename rule, and the two would have drifted the first time one of them was fixed. Each helper logs **before** it returns (checklist 12 — the action log must survive a failed reply), and the caller does the answering, which is what lets the panel answer through `followup` and a command answer through `response` with one body. |
| `black_bloc/cogs/community/tempvoice.py:876` | ⚠️ **Renaming a channel is capped by Discord at two edits per ten minutes** (checklist 24), and the refusal used to blame the bot's permissions for it — which sends somebody to a Lead to fix a permission that is already correct. A 429 now gets its own sentence naming the real limit. `discord.RateLimited` is caught alongside `HTTPException` because they are **not** related by inheritance: the library raises the former only when a `max_ratelimit_timeout` is set, and it would otherwise escape every `except HTTPException` in this file. |
| `black_bloc/cogs/community/tempvoice.py:918` | `do_privacy` takes an optional `want`, so the **button toggles** and `/voice lock` **states**. Asking for the state a channel is already in returns a sentence and spends **no** API call — a `/voice lock` on a locked channel is otherwise a silent no-op that looks identical to a failure. ⚠️ **This and `do_forget_member` (`:1001`) are the two READ-MODIFY-WRITE edits, so they take the per-channel lock (checklist 6) and the blind ones do not** — Lock followed quickly by Unlock could otherwise leave the channel locked while telling the owner it was unlocked, whereas rename, limit, bitrate, region, ban and permit are writes where last-one-wins is the right answer, and locking them would hold one owner's rename up behind another edit on the same channel. ⚠️ **The lock NARROWS this window; it does not close it:** `overwrites_for` reads discord.py's cached channel, which is refreshed by a gateway event and not by the edit call, so a second read can still be stale. The claim/transfer race is the one genuinely closed, because that one re-reads the DATABASE inside the lock (`:1180`). |
| `black_bloc/cogs/community/tempvoice.py:1007` | Unban and unpermit are one helper because they are one operation — clearing that member's own `connect`/`view_channel` back to "whatever the channel says" — and two log kinds and two sentences because they are two intentions. The overwrite is **removed entirely** only when nothing else is left on it (`PermissionOverwrite.is_empty`); one that also carries, say, a `speak` denial keeps it. Removing the whole overwrite unconditionally would quietly undo settings this feature never made. |
| `black_bloc/cogs/community/tempvoice.py:274` | ⚠️ **Which channel a `/voice` command acts on, and the order matters.** The channel you are **connected to** wins over the one you merely own, because somebody who owns two (one abandoned, one they are sitting in) means the one they are sitting in. `claim` passes `owner_only=False` and takes *only* the connected channel — claiming something you are not in is the one thing the vendor's own docs leave undefined, and our answer is no (the same rule the Claim button has always had). |
| `black_bloc/cogs/community/tempvoice.py:268` | The `/voice` group is gated on `tempvoice_allowed_role_id`, the same setting that decides who join-to-create makes a channel for — one fact, one home (checklist 15). It is deliberately not `require_staff`: these are the owner's controls for their own channel, and the panel has always let a plain member press them. |
| `black_bloc/cogs/community/tempvoice.py:1034` | ⚠️ **Discord's bitrate ceiling is per boost tier, and `guild.bitrate_limit` is a FLOAT in bits.** The command takes kbps (8–96) because that is what Discord's own UI shows, clamps to the guild's ceiling, and says so when the clamp bit — silently giving somebody 64 when they asked for 96 is the kind of thing they re-run four times. A guild object with no `bitrate_limit` (a stale cache, a fake) falls back to 96 kbps, which every server has. |
| `black_bloc/cogs/community/tempvoice.py:1059` | ⚠️ **`VOICE_REGIONS` is a STATIC list because discord.py 2.7.1 has no voice-region listing call at all** — verified by grepping the installed library for `voice_regions`/`VoiceRegion` (no hits; the helper went with the enum in 2.0). `channel.edit(rtc_region=...)` still takes an `Optional[str]`, so the feature works; only the autocomplete is guesswork. Autocomplete does not constrain what a person may type, so a region Discord has added since is still usable, and one it has retired comes back as `tempvoice.region_failed` with a sentence naming it rather than the permissions sentence. |
| `black_bloc/cogs/community/tempvoice.py:1064` | Roles and members share one overwrites dict and `discord.py` types the keys, but a **pure** function cannot ask `isinstance` about a fake — so the caller passes the guild's role ids and this skips them. That keeps "who did the owner let in by name" testable without a guild, the same reason the position maths (`:234`) is pure. |
| `black_bloc/storage/db.py` | Additive columns through the existing `ADDED_COLUMNS`/PRAGMA path, schema **8 → 11**: `tempvoice_channels.panel_channel_id` (v9, so a click can find its channel wherever the panel lives), `tempvoice_prefs.bitrate` (v10) and — v11, owner ask 2026-08-27 — `tempvoice_prefs.region`, `permitted_ids` and `banned_ids`. Every one is in `SCHEMA` as well, for a fresh database: the two have to agree or a new install differs from a migrated one. ⚠️ The two id columns hold **JSON arrays in a TEXT column**, the same shape `settings.value` uses, because a second table keyed by (owner, member) would need its own migration, its own delete path and its own reconcile for members who have left — and the list is read exactly once, at spawn. |

### Remembering the whole set-up (owner ask, 2026-08-27)

> Owner, verbatim: *"would like a way to save a channels changed details so the next
> time the same user makes one it keeps their old name and set up."* Name, limit, lock,
> hidden and bitrate were already remembered; this adds **region** and the **permitted
> and banned member lists**, and gives the memory a way out. Keys are this tree's, read
> off the file after the last edit. NOT verified: any of it against live Discord — no
> channel has ever been spawned from a remembered list by a real join.

| Key | Note |
|---|---|
| `black_bloc/cogs/community/tempvoice.py:478` | ⚠️ **`None` still means "leave this one alone", and that is why `region` stores the STRING `auto` rather than `None`.** Every field is optional and a `None` argument keeps whatever was there, so a knob whose "off" value is `None` could never be turned back off. `/voice region auto` therefore writes `"auto"`, and `_create_for` (`:1517`) reads that as "pass no `rtc_region`". |
| `black_bloc/cogs/community/tempvoice.py:534` | `/voice reset`'s whole implementation: the row is **deleted**, not blanked, so `get_prefs` goes back to `None` and every default applies again — the same reasoning as `SettingsStore.clear` (`settings_store.py:844`). It returns whether a row was really deleted, so the command can tell "forgotten" from "there was nothing to forget" instead of claiming a change that did not happen. |
| `black_bloc/cogs/community/tempvoice.py:543` | ⚠️ **The two id columns are JSON read by a function that cannot raise.** This is called from `_create_for`, inside a voice event, where a raise is invisible (the same rule as `channel_name` at `:208`) — so a hand-edited row, a truncated write or a value that is not a list at all yields an empty list and a channel with no remembered members, never a member sitting in a lobby nothing happened in. |
| `black_bloc/cogs/community/tempvoice.py:41` | The cap is `MEMBER_MEMORY_MAX` and it keeps the **newest** entries, because nothing may grow forever (checklist 5) and an owner who has permitted fifty people over a year does not want the first ten back. Adding an id always removes it first, so one member cannot appear twice, and permitting somebody who was banned clears the ban in the same write (`remember_access` at `:565` passes both lists every time). |
| `black_bloc/cogs/community/tempvoice.py:581` | ⚠️ **A remembered member is re-applied as an overwrite on the NEW channel, and a member who has left is skipped rather than guessed at.** `guild.get_member` is the only check: an id that no longer resolves is dropped silently, because a `discord.Object` key would be written as a *member* overwrite by `Guild._create_channel` anyway (`:1666` has the same trap for roles) and an id for somebody who left is not a permission decision worth keeping. The owner is skipped too — their own overwrite is already the full one `owner_overwrites` (`:344`) wrote, and a stale "banned" entry for the owner would lock them out of their own channel. |
| `black_bloc/cogs/community/tempvoice.py:1113` | `/voice info` now answers two questions, not one: **what this channel is** (read off Discord) and **what the next one will be** (read off `tempvoice_prefs`). They can differ — somebody else's `/voice transfer`, a manual edit in Discord, a permit that Discord refused — and a page that showed only the first would make "it forgot my settings" impossible to diagnose. The block ends by naming `/voice reset`, because a memory the owner cannot see the end of is a memory they cannot switch off. |
| `black_bloc/cogs/community/tempvoice.py:1796` | ⚠️ **Extracted from `_voice_target` so `/voice reset` can be gated without owning a channel.** Every other `/voice` command acts on a channel, so the guild check, the `tempvoice_allowed_role_id` check and the database check used to live inside the lookup; reset applies to a person, not a channel, and copying the three checks would have been the second implementation of the gate (checklist 15). `_voice_target` calls this first, so the two cannot disagree about who may use `/voice`. |

#### What TempVoice has, and what we did about it

Source: `reference-bots.md` §1.2–1.6 (vendor docs via `easy.tempvoice.xyz/llms.txt`;
`help.tempvoice.xyz` is 403). **Last verified: 2026-08-26**, against the vendor docs as
recorded there — not against the live TempVoice bot, which nobody ran.

| TempVoice control | Ours | Status |
|---|---|---|
| NAME / `/voice name` | Rename button, `/voice rename` | **matched** (ours is `rename`) |
| LIMIT / `/voice limit` | Limit button, `/voice limit` | **matched** |
| PRIVACY / `/voice privacy` (public / locked / hidden) | Lock and Hide buttons; `/voice lock unlock hide show` | **matched, different shape** — two independent switches instead of one three-way mode, because that is what the overwrites actually are |
| TRUST / UNTRUST | Permit / Unpermit, `/voice permit unpermit` | **matched** (renamed to words this server already uses) |
| BLOCK / UNBLOCK | Ban / Unban, `/voice ban unban` | **matched** |
| KICK | Kick button, `/voice kick` | **matched** |
| CLAIM | Claim button, `/voice claim` | **matched, and stricter** — ours needs the clicker **connected** and the owner **absent**; the vendor's condition is **(NOT DOCUMENTED)** |
| TRANSFER | Transfer button, `/voice transfer` | **matched** |
| REGION / `/voice region` | `/voice region` with autocomplete | **added** (we had nothing) — `auto` plus a static region list; see `:1479` |
| `/voice bitrate` | `/voice bitrate` 8–96 kbps | **added** (we had nothing) — clamped to the guild's boost ceiling; the vendor's range is **(NOT DOCUMENTED)** |
| `/voice info` | `/voice info` | **added** (we had nothing) — owner, cap, locked, hidden, bitrate, region, and the permitted and banned lists |
| Per-user remembered settings (name, limit, privacy) | `tempvoice_prefs` | **matched, extended** — name, limit, locked, hidden, bitrate **and, since 2026-08-27, region plus the permitted and banned member lists** (owner: "would like a way to save a channels changed details so the next time the same user makes one it keeps their old name and set up") |
| INVITE / `/voice user invite` | — | **skipped**: `permit` plus the channel mention does the same job with one fewer control |
| WAITING ROOM / `/voice waiting` | — | **skipped**: needs a join-request queue and an approval surface; it is a feature, not a button. Vote-gated even in the vendor |
| CHAT / `/voice thread` | — | **skipped**: Discord voice channels have built-in text chat now, and this feature already posts its panel there. A thread would be a second place to talk in one channel |
| DELETE / `/voice delete` | — | **skipped, deliberately**: the channel deletes itself when the last person leaves (`:1469`), and a force-delete is a control whose only use is destroying a channel other people are in — it would also race the reconciler |
| `/voice password` + top-level `/join` | — | **skipped**: a second access system running beside Discord's permissions, and the one way a member could shut a channel in a way staff cannot see |
| `/voice reset` | `/voice reset` | **added 2026-08-27** — it deletes that user's `tempvoice_prefs` row, so the next channel starts from the server's defaults. The owner asked for the memory to be wider, and a memory with no way out is a trap |
| `/voice lfp` (looking for players), `/find` | — | **skipped**: different features that happen to live in the same bot |
| Vote-gating (`claim`, `bitrate`, `waiting` need a Top.gg vote) | — | **skipped on purpose**: it is the vendor's monetisation, not a design |
| Restore Owner Settings; Ownerless mode; per-feature role toggles | one `tempvoice_allowed_role_id` gate | **partly** — one switch for the whole feature instead of a dashboard of per-feature ones |
| Name placeholders (`{OWNER_USERNAME}`, `{NUMBER}`, …) | `{user}` only | **partly**, and untouched by this change |

⚠️ **One vendor fact we could not reconcile, and did not:** the TempVoice docs say
Discord's channel-rename cooldown is **once per 5 minutes** (`faq/limits.md`), and this
repo's own review checklist item 24 says **2 per 10 minutes**. Our refusal sentence says
twice per ten minutes. Both describe roughly the same budget; **neither has been measured
against live Discord by us**, and that sentence is the one thing here a real 429 puts in
front of a person.

## `black_bloc/cogs/community/events.py` — F4/F5

| Key | Note |
|---|---|
| `black_bloc/cogs/community/events.py:83` | Checklist 9 in two dicts rather than a health class: what each loop last finished, and what it last raised. `/event settings` prints both (`black_bloc/cogs/community/events.py:1589`), because `is_running()` is not health — a loop that died three hours ago and a loop that ran a second ago are both "running" until one of them is not. |
| `black_bloc/cogs/community/events.py:106` | Names **both** halves of what test mode needs — a visible test channel AND a category around it — because review finding F12 showed they fail together and the old sentence only mentioned one of them. |
| `black_bloc/cogs/community/events.py:112` | `clamp` strips, so a title of spaces arrives as `""` and used to become a channel called `pending` with an embed that has no heading. Refused instead (review finding F14). |
| `black_bloc/cogs/community/events.py:116` | The two DST refusals, kept separate because the fixes are different: a skipped hour needs a different time, a repeated hour needs the person to say which of the two they mean. The detection is in `timezones.py:57`, not here — this file only says it in words. |
| `black_bloc/cogs/community/events.py:126` | Review finding F14: the modal never said which zone it read. A `TextInput` has no description field, so the Start box's **placeholder** carries it, and it is set per instance in `EventModal.__init__` because the zone is the requester's. `discord.py` deep-copies a modal's children per instance (`ui/modal.py:123`), so writing to `self.start` cannot leak one person's zone into the next person's modal. Placeholders cap at 100 characters and the longest IANA name is 32, so this cannot overflow. |
| `black_bloc/cogs/community/events.py:127` | What a cancelled event's public announcement is edited to say (review finding F7). |
| `black_bloc/cogs/community/events.py:170` | ⚠️ **The reason codes are for the LOG; this maps them to sentences for the person** (review finding F5). Auto-cancels told nobody at all — a proposal simply stopped existing — and `cancelled_by_<id>` is not something to send anyone. The default covers every code with no entry, so a new reason is a missing sentence rather than a crash inside a background loop. |
| `black_bloc/cogs/community/events.py:191` | Review finding F2's apology. An event whose end time had already gone by was announced as starting now; it is marked done in silence instead, and the requester is told plainly that nobody was told. Saying nothing would leave them believing it ran. |
| `black_bloc/cogs/community/events.py:340` | `card_channel_id` is written by the same call that writes the other two, so the three can never disagree about where the card is (`storage/db.py:227`). |
| `black_bloc/cogs/community/events.py:409` | Review finding F14: `_event_locks` grew one entry per event for the life of the process and never shrank. A settled event cannot be raced — `can_transition` (`black_bloc/events.py:33`) refuses every move out of a terminal status — so its lock is dropped. ⚠️ **Dropping it while it is held is safe and deliberate**: a waiter already holds a reference to the `Lock` object and is unaffected, and a click arriving after the pop makes a fresh lock that immediately finds a terminal status. |
| `black_bloc/cogs/community/events.py:503` | Returns whether the person was actually told, because "best effort" and "nobody knows" are the same thing until somebody records the difference. |
| `black_bloc/cogs/community/events.py:516` | The DM a requester is **owed** — cancelled, missed — goes through here so a closed DM is `event.dm_failed` in the action log rather than an `INFO` line nobody reads (review finding F5). The DMs that are merely nice to have still call `dm` directly. |
| `black_bloc/cogs/community/events.py:606` | The cache is empty after a restart, and an event approved before the restart is exactly the one most likely to need cancelling. `fetch_scheduled_event` is a round trip and is therefore only reached when the cache misses. |
| `black_bloc/cogs/community/events.py:618` | ⚠️ **The bug that killed the reconcile loop for the life of the process** (review finding F1). `ScheduledEvent.cancel()` raises a bare `ValueError` when the event is not `scheduled` (discord.py 2.7.1, `scheduled_event.py:296`), and only `HTTPException` was caught — so one event that had already started took the loop with it and left `/event cancel` half done. A running event is **ended** rather than cancelled, because Discord models those as different transitions; anything else it refuses is logged `event.cancel_scheduled_failed`, and under the guard nothing is touched at all and the log says `event.would_cancel_scheduled` (review finding F8, which also found this path returning silently). |
| `black_bloc/cogs/community/events.py:692` | ⚠️ **`announce_message_id` was write-only** (review finding F7): a cancelled event left a public post still advertising it, with the card still saying `approved`. Editing is a second way to speak in a channel, so it asks the guard the same way the post did (`black_bloc/cogs/community/events.py:650`) and has the same three kinds — edited, `would_edit_announcement`, `edit_announcement_failed`. `get_partial_message` avoids a fetch when the library offers one. |
| `black_bloc/cogs/community/events.py:1021` | **Phase 8a merge.** `loop_health(name)` is how the status page reads this cog's loop health without knowing its attribute names: here they are ⚠️ **dicts keyed by loop name**, and the key is the coro name with its `_` prefix and `_loop` suffix stripped — `_golive_loop` → `golive`. Handing that raw dict to a reader that expected a string is the bug this method exists to prevent: a non-empty dict is truthy, so a healthy loop rendered an error. The page asks; it never guesses (`black_bloc/api/status.py:139`). |
| `black_bloc/cogs/community/events.py:1027` | ⚠️ **A `tasks.loop` that raises does not retry — it stops, for good, silently** (review finding F1; discord.py logs it and returns). Both loops therefore register an `@error` handler that records the failure where `/event settings` will show it and calls `restart()`. `restart()` is safe from inside the handler: it schedules the restart on the task's done callback rather than re-entering the loop. |
| `black_bloc/cogs/community/events.py:1080` | ⚠️ **Three outcomes now, not one** (review finding F2). An approved event whose `ends_at` has already passed is never announced — the bot was offline, and "starting now!" for something that finished two hours ago is worse than silence. One that merely started late is capped by `events_max_late_minutes` (`settings_store.py:42`) and goes `live` quietly past it. The status moves in every case, because the row must stay true whether or not anybody was told. |
| `black_bloc/cogs/community/events.py:1115` | Runs **inside** the caller's lock — it is only ever reached from `_go_live`, which holds it — so it must not take the lock again. `approved → done` is a legal transition (`black_bloc/events.py:33`) precisely so this can exist. |
| `black_bloc/cogs/community/events.py:1177` | ⚠️ **Two consecutive misses before a cancel** (review finding F9). One reconcile pass seeing no channel is not evidence the channel is gone: a dropped gateway event, a cold cache after a reconnect or a partial outage all look identical, and the old code settled somebody's proposal on that. The note lives in memory on the cog rather than in the database on purpose — a restart should re-start the count, because a restart is exactly when the cache is least trustworthy. ⚠️ An unreadable `starts_at` is cancelled outright (review finding F10): the row could never go live, never finish and never resolve, so it would have sat `pending` for ever. |
| `black_bloc/cogs/community/events.py:1202` | ⚠️ **The action log is written BEFORE Discord is asked to undo anything** (review finding F1, checklist 12): cancelling the scheduled event is a network call that can fail, and a failed one must not take the record of the cancellation with it. Then the announcement is edited (`black_bloc/cogs/community/events.py:692`) and the requester is told why (`black_bloc/cogs/community/events.py:170`) — unless they are the one who cancelled it, which is the only case where a DM would be telling somebody what they just did. |
| `black_bloc/cogs/community/events.py:1589` | Checklist 9: last success and last error per loop, never `is_running()`. It is a list of lines rather than a string so `/event settings` splices it into the same block as everything else. |
| `black_bloc/cogs/community/events.py:79` | ⚠️ **A persistence key, matched by `discord.py` as a regex.** Same mechanism as the honeypot's Ban-now button (`cogs/moderation/honeypot.py:32`): one `add_dynamic_items` call at `cog_load` (`:1358`) revives **every** review card ever posted, with the event id carried in the `custom_id` itself. A stored persistent view would have needed one registration per event and a table of message ids. Approve and Deny share one class and one template because they share the entire path up to a single branch; two classes would have been two places to forget the staff check. Change this string and every card already in the server goes dead with no error anywhere. |
| `black_bloc/cogs/community/events.py:84` | A pending row with no review channel is normally impossible — the channel is made seconds after the row — but a process killed between the two leaves one, and nothing else would ever clean it up. The grace exists so the five-minute reconcile running *during* a submission cannot cancel an event that is halfway through being created. |
| `black_bloc/cogs/community/events.py:331` | The column name is interpolated into the SQL, and it is safe because both callers pass a module constant (`:861`), never anything a person typed. ISO-8601 UTC strings compare correctly as text, which is what lets "which events have started" be one indexed query rather than a Python loop over every row. |
| `black_bloc/cogs/community/events.py:355` | ⚠️ **`COALESCE` on the three decision columns, so a later write cannot erase who decided and why.** Going live and finishing both call this with no `decided_by`, and without the coalesce each of those would blank the deny reason and the decider recorded at approval time. `decided_at` is set only when `decided_by` is, because "when" without "who" is not worth keeping. |
| `black_bloc/cogs/community/events.py:398` | ⚠️ **The per-event lock lives on the BOT**, for the same reason temp voice's does (`cogs/community/tempvoice.py:276`): a button click arrives with an `interaction` and never with a cog, so the lock has to be reachable from `interaction.client`, and a module-level dict outlives the event loop that made it. This is the whole defence against two mods deciding at once — there is no unique index to fall back on, because the row already exists and it is the *status* that is being raced (checklist 6). Every writer re-reads the row **inside** the lock and asks `can_transition` (`black_bloc/events.py:33`); the loser is told who got there first rather than silently overwriting them. |
| `black_bloc/cogs/community/events.py:428` | The one place a stored row becomes a rendered card. Duration is derived from the two timestamps rather than stored a second time — one fact, one home — and an unreadable pair falls back to the default rather than raising inside a background loop. |
| `black_bloc/cogs/community/events.py:444` | The requester is deliberately **not** given the channel (owner decision, `phase4-design.md`; adding them is a later ask). `@everyone` is denied outright rather than left to inherit, because a review channel inheriting a public category would put every proposal in front of the whole server. The staff roles come from `settings_store.py:575` — the same computed-permission derivation the honeypot and every staff command use, so "approvers = anyone who can see the staff channel" has exactly one implementation. |
| `black_bloc/cogs/community/events.py:457` | ⚠️ **Channel creation is invisible to `guard.py`, so the test policy is enforced here by PLACE.** While a guard is installed, review channels are made in the **test channel's own category** and nowhere else — same rule as temp voice (`cogs/community/tempvoice.py:1637`) and the honeypot (`cogs/moderation/honeypot.py:310`). A test channel the bot cannot see means it cannot prove where it is, and the answer is no. ⚠️ **A test channel with no category is the same answer** (review finding F12): `category` was read without checking, so `create_text_channel(category=None)` put the review channel at the TOP level of the server — outside the very category the rule exists to confine it to, and outside anything `allows_place` would later let the bot rename or delete. Do not remove this when test mode is lifted; it is a no-op then (`bot.guard is None`). |
| `black_bloc/cogs/community/events.py:477` | ⚠️ **The one place Phase 4 deviates from what temp voice did, and deliberately.** The review card is a *message*, and the review channel is not the test channel, so `guard.py` would refuse the send — temp voice answers that by not posting its panel at all (`cogs/community/tempvoice.py:1597`). Here that would make the whole feature untestable: the Approve and Deny buttons **are** what the owner has to click. So while the guard is on, the card goes to the test channel instead — the send is still the guarded send, nothing is written anywhere the policy forbids, and the reply says plainly where it went (`:1108`). |
| `black_bloc/cogs/community/events.py:529` | ⚠️ **A rename is a side effect `guard.py` cannot see, so it asks `allows_place` first** and logs `event.would_rename` rather than doing it (review finding F3b) — a `would_…` kind, never shared with the `rename_failed` a real refusal produces (checklist 2). Renaming a channel is also **2 edits per 10 minutes** and `discord.py` sleeps through the 429 (checklist 24) — every caller defers first. It is also the last thing a decision does, after the status, the log, the scheduled event and the DM, because a rename Discord refuses must not take an approval with it; it logs `event.rename_failed` and the next status change tries again. The no-op check exists so the reconciler re-running does not spend one of those two edits saying nothing. |
| `black_bloc/cogs/community/events.py:561` | It returns the **event object** rather than its id, because the announcement needs `ScheduledEvent.url` to link it and the caller must be able to tell "made" from "not made" without a second lookup (review finding F4). ⚠️ **A real Discord scheduled event is visible to the whole server and `guard.py` cannot see it being made**, so while test mode is on it is skipped and logged `event.would_create_scheduled` (owner rule, `phase4-design.md`, §Test mode). The three outcomes never share a kind (checklist 2): made → the id on the row, refused by policy → `would_create_scheduled`, refused by Discord → `create_scheduled_failed`. `entity_type=external` is what lets an event be somewhere other than a voice channel, and Discord **requires** both an end time and a location for that type — the end time is the start plus the duration, and a requester who gave no location gets a sentence rather than a 400. |
| `black_bloc/cogs/community/events.py:650` | ⚠️ **The single guarded door to a public channel, and every refusal has its own kind.** `shadow` suppresses the post and nothing else (owner decision: the flow is staff-gated, so there is nothing to punish) → `would_announce`; a missing channel → `announce_failed`; the guard → `would_announce` with `test_mode`. Asking the guard *first* rather than letting it raise from inside the HTTP layer is the same trick as `cogs/content/golive.py:454`, for the same reason: in a background loop a `TestModeViolation` is an ugly traceback and a half-finished state. |
| `black_bloc/cogs/community/events.py:826` | ⚠️ **The order inside a decision is the contract.** Status → action log → scheduled event → announcement → the requester's DM → the rename → closing the card → answering the mod. Everything irreversible or recorded happens before anything cosmetic (checklist 12), and the answer is last because a failed answer must not take a real decision with it. All of it runs **inside** the lock, so a second mod's click finds the finished status rather than a half-applied one. |
| `black_bloc/cogs/community/events.py:908` | Deny asks for its reason in a modal, which is why the deny path cannot pre-defer: `send_modal` must itself be the response. The status is checked once before the modal opens — so nobody types a reason for an event that was approved while they were reading it — and again inside the lock after it is submitted, which is the check that actually decides. |
| `black_bloc/cogs/community/events.py:961` | ⚠️ **Five inputs, because `discord.py`'s `Modal.add_item` raises at six** — verified against the installed library at build time rather than taken from the design note, which flagged the cap as ambiguous. That cap is the whole reason there is no stream or voice picker here and location is free text (`phase4-design.md`, §The flow). The title field is `event_title` and not `title` because `discord.ui.Modal.title` is the modal's own heading. |
| `black_bloc/cogs/community/events.py:1066` | Approved-and-started rows are swept **before** live-and-finished ones, and the second query runs after the first loop has committed. That ordering is what lets an event the bot was offline for go live and then finish inside a single tick, instead of sitting `approved` forever because its end time had already passed (checklist 5). |
| `black_bloc/cogs/community/events.py:1166` | Reconciliation runs at `cog_load`, at `on_ready` **and** on a five-minute loop (checklist 4 and 25) — `setup_hook` runs before the gateway connects, so a reconcile that iterates `bot.guilds` there alone is a no-op on every real start, and a long-lived process never restarts on its own. |
| `black_bloc/cogs/community/events.py:1205` | Retention, and it reads `ends_at` rather than the decision time on purpose: a channel is kept for N days after the event **happened**, not after somebody pressed Approve. ⚠️ **Three things review finding F3 changed here, and the last one reverses what this note used to say.** It sweeps `denied-` and `cancelled-` channels as well as `done-` ones, because those were the two outcomes that piled up for ever; it asks `guard.allows_place` and logs `event.would_delete_channel` rather than deleting, because a delete in a background loop is the one mistake nobody can undo; and an unreadable `ends_at` now **KEEPS** the channel. The old convention — an unreadable timestamp counts as old — is right everywhere it means "stop waiting" (`black_bloc/golive.py:145`, `cogs/community/tempvoice.py:31`) and wrong here, because the action it licenses is destruction rather than tidying up. The floor on the setting is 1 day (`settings_store.py:41`), so "delete it the moment it ends" is no longer expressible at all. |
| `black_bloc/cogs/community/events.py:1245` | Three jobs, all of them "forget something that no longer exists" (checklist 26). A deleted **category** or a deleted **announce channel** is cleared from the settings — `SettingsStore.clear` (`settings_store.py:642`) exists for this — so `/event settings` stops naming a dead channel. A deleted **review channel** cancels its event immediately rather than waiting up to five minutes for the reconciler, which is only the backstop for the case the bot was offline. |
| `black_bloc/cogs/community/events.py:1296` | The row is written **before** the channel, so a crash between the two leaves something the reconciler owns rather than an orphan channel nobody remembers. A channel Discord refuses cancels the row in the same breath (`:1081`) — a pending event with no channel and no grace left would otherwise be cancelled minutes later by the loop, which is a worse way for the requester to find out. |
| `black_bloc/cogs/community/events.py:1398` | Returns **where the card actually went**, so the reply can say so instead of claiming a channel that has nothing in it (checklist 10). Three answers, three sentences: it is in the review channel, it is in the test channel because test mode is on, or it is nowhere and the log says why. It also **stores** that channel as `card_channel_id` (review finding F14), because otherwise the row held a `review_message_id` that does not exist in the `review_channel_id` beside it — a pair of columns that read as a fact and are one in test mode only by accident. |

## `black_bloc/cogs/moderation/honeypot.py` — F9

| Key | Note |
|---|---|
| `black_bloc/cogs/moderation/honeypot.py:377` | `SafeDynamicItem` (`command_errors.py:52`) first in the bases, and the body is `on_click` rather than `callback`, because `discord.py` swallows a dynamic item's exception itself and never reaches a view. Review finding F6: the highest-consequence button in the project — it bans somebody — was the one that could fail silently. |
| `black_bloc/cogs/moderation/honeypot.py:38` | ⚠️ **A persistence key, matched by `discord.py` as a regex.** `BanNowButton` is a `DynamicItem`, not a member of a stored view: one `add_dynamic_items` call at `cog_load` (`:411`) makes *every* Ban-now button ever posted work again after a restart, with the hit id carried in the `custom_id` itself. A plain persistent view would have needed one registration per button and a table of message ids. Change this string and every button already sitting in the log channel goes dead with no error anywhere. |
| `black_bloc/cogs/moderation/honeypot.py:110` | ⚠️ **The exemption matrix, and the only pure function in the feature — read it before changing who can be banned.** Order matters only for the log line (a staff bot reads as `bot`), but the *set* is the safety property: bots, Manage Server, anyone who can see the staff channel (`settings_store.py:359`), and the configured exempt roles. The vendor docs state no exemptions at all, so this list is ours by design (`phase3-design.md`, Part B). |
| `black_bloc/cogs/moderation/honeypot.py:174` | The burst guard. A spam bot posts five times in a second; the per-author lock (`:433`) serialises those five, and this makes the last four cost one query instead of one ban attempt each. The hit is still recorded and still logged — silence would look exactly like a broken listener. |
| `black_bloc/cogs/moderation/honeypot.py:210` | ⚠️ **A ban is invisible to `guard.py`, so the guard is asked here, and the answer while test mode is on is always no** (owner rule, `phase3-design.md`, Part B, §Test mode). It returns the *reason* rather than a bool because the three outcomes must not share a log kind: banned → `honeypot.banned`, refused by policy → `honeypot.would_ban`, refused by Discord → `honeypot.ban_failed` (checklist 2). The DM goes out **before** the ban, because a banned account cannot be DMed. |
| `black_bloc/cogs/moderation/honeypot.py:445` | The order is deliberate: exempt check → **delete** → record → ban. Deleting first in every mode but `off` is housekeeping, not punishment — nobody reading the channel should find spam sitting in it while the feature is still in shadow, and a shadow hit that kept the post visible would make the trap advertise itself. |
| `black_bloc/cogs/moderation/honeypot.py:564` | The watch-mode affordance: a shadow hit posts the content and a **Ban now** button into the log channel, so the owner converts a real catch into a real ban in one click without leaving Discord. It is skipped when there is no log channel, and skipped when the guard would refuse that channel — the button is useless if the ban behind it is refused anyway. |
| `black_bloc/cogs/moderation/honeypot.py:644` | Same test-mode shape as temp voice (`cogs/community/tempvoice.py:1640`): while the guard is on, the trap channel is created **inside the test channel's category**, and its pinned notice is not posted at all, because the notice is a message and `guard.py` would refuse it. The reply says which of the two happened rather than claiming a notice that is not there (checklist 10). |
| `black_bloc/cogs/moderation/honeypot.py:32` | ⚠️ **Only a real, human post trips the trap.** `MessageType` also covers join announcements, pins, boosts and thread-created notices, and every one of those is a message Discord posts *on behalf of* a member in the channel they acted in — banning somebody for Discord's own "so-and-so joined" line is the worst failure this feature could have. `reply` is included because a reply to the pinned notice is a real post. |
| `black_bloc/cogs/moderation/honeypot.py:33` | The shadow-mode dedupe window. A spam bot posts repeatedly; the per-author lock serialises those, `banned_already` stops the second real ban, and this stops the second **button**. Every hit is still recorded and still logged — as `honeypot.hit_recorded` rather than `honeypot.would_ban`, so the two are distinguishable at a glance (checklist 2) and the log channel does not fill with identical Ban-now buttons that all do the same thing. |
| `black_bloc/cogs/moderation/honeypot.py:76` | ⚠️ **Turning the trap `on` is refused while no staff role resolves**, and `/honeypot status` says so loudly in that state. This is the user-facing half of the derivation fix (`settings_store.py:359`): with an empty staff set the only exempt humans are those with Manage Server, so one mistyped message from a moderator is a real ban. The refusal names the setting and the command that proves it is fixed. |
| `black_bloc/cogs/moderation/honeypot.py:210` | ⚠️ **`delete_message_seconds`, not the deprecated `delete_message_days`**, and the value is clamped to Discord's 7-day ceiling here as well as in the validator (`settings_store.py:532`) — a bigger number stored before that validator existed would make **every** ban a 400. |
| `black_bloc/cogs/moderation/honeypot.py:424` | The trap catches posts in a **thread of** the trap as well as in the trap itself: a thread inherits the channel's visibility, so a bot that opens one is in exactly the same place. `parent_id` is read with `getattr` because an ordinary channel has none, and a `None` parent can never match a list of ids. Setup also denies thread creation to `@everyone` (`:593`) — this is the belt to that braces. |
| `black_bloc/cogs/moderation/honeypot.py:534` | ⚠️ **Deleting a message is a side effect `guard.py` cannot see**, so the delete asks the same place question temp voice asks (`cogs/community/tempvoice.py:1637`): while a guard is installed, the trap must be in the test channel's own category. Otherwise the answer is no and the attempt is logged as `honeypot.would_delete` — a `would_…` kind, never shared with the `delete_failed` that a real refusal produces. |
| `black_bloc/cogs/moderation/honeypot.py:648` | `/honeypot status` prints the **resolved** staff roles, by name and count, because that is how the owner checks the exemption is real. A count of zero while the mode is `on` gets the warning line rather than a blank: silence there reads as "no exemptions configured", which is exactly the state that bans a moderator. |
| `black_bloc/cogs/moderation/honeypot.py:727` | A trap channel that is deleted is forgotten automatically, and `/honeypot forget <id>` covers the case the bot was offline for. `setup` refuses a second trap while the first still exists (`:593`), so without a way to forget a dead id the command would be blocked forever. |

## `black_bloc/twitch.py` — the Helix client

| Key | Note |
|---|---|
| `black_bloc/twitch.py:93` | ⚠️ **`request` is the seam that keeps the test suite offline** (owner rule: no test ever calls the real Twitch API). It is a callable `(method, url, *, headers, params, data) -> (status, payload)`; the default is the aiohttp implementation below, and `tests/test_twitch.py:15` passes a fake that replays canned responses. Injecting a *callable* rather than a *session* means the fake is fifteen lines instead of a stack of async context managers. |
| `black_bloc/twitch.py:101` | `aiohttp` is imported inside the method, not at module import: the client object is constructed during `cog_load` even when there are no credentials, and nothing should pay for an import the feature may never use. The session is created lazily and re-created if it was closed, so `close()` is safe to call twice. The 15-second total timeout is on the **session**, so it covers connect and read together — without it aiohttp waits forever, and a poller tick that never returns is a `tasks.loop` that silently stops ticking. |
| `black_bloc/twitch.py:125` | ⚠️ **Every network failure leaves this module as a `TwitchError`, and that is the contract the callers are written to.** Before the Phase 2 review a DNS failure, a reset connection or a timeout escaped as `aiohttp.ClientError`/`OSError` past the `except TwitchError` in the cog (`cogs/content/golive.py:109`, `:648`) — killing the poller for good, or a slash command with no answer. `OSError` is in the tuple because it is the parent of the socket errors aiohttp does not always wrap. |
| `black_bloc/twitch.py:133` | The app token is **cached for the process**. Twitch client-credentials tokens last ~60 days; re-minting one per request would be both slow and a good way to get rate-limited. Expiry is handled by the 401 path below rather than by trusting `expires_in`, because a clock skew or a revoked app makes the stated lifetime a lie. |
| `black_bloc/twitch.py:157` | ⚠️ **One retry, and only on 401.** Clearing the cached token and calling once more is the whole refresh mechanism; a 500 or a 429 is *not* retried here, because a poller that runs every 60 seconds will try again by itself and a retry loop inside the client would multiply a Twitch outage into a rate-limit ban. |
| `black_bloc/twitch.py:177` | Helix caps `user_login` at 100 per call, so the batching is a hard API limit rather than politeness (`phase2-design.md`, §Detection). An offline login is simply **absent** from the response — there is no "live: false" row — which is why the poller compares sets rather than reading a field. |

## `black_bloc/golive.py` — the decisions, with no Discord in them

| Key | Note |
|---|---|
| `black_bloc/golive.py:64` | Matches `discord.Streaming` **and** any activity whose `type` is `streaming`. Both are needed: the library only builds a `Streaming` object for activities it recognises as such, while a client sending a custom or partial activity arrives as a plain `Activity` with the right type. Missing the second form would silently drop go-lives from some clients. |
| `black_bloc/golive.py:100` | ⚠️ **The field names are `discord.py`'s, not Discord's.** On `discord.Streaming`, `.game` is the *category* (the gateway's `state`) and `.details`/`.name` is the *stream title*; a generic `Activity` carries `state`/`details` instead, so both are read with a fallback. Get this wrong and the announcement says the title where the category should be. |
| `black_bloc/golive.py:123` | Lets a presence-only streamer be enriched without a `/twitch link`: the login is already in the URL Discord gives us. It is also how the poller's session bookkeeping and the presence path agree on who is who. |
| `black_bloc/golive.py:53` | ⚠️ **`{game}` falling back to `"something"` is the defect this feature exists to beat** — the incumbent rendered `****` for 4 of 199 measured posts because it interpolated an empty category into `**{game}**` (`phase2-design.md`, §What the incumbent does). `_Fields.__missing__` returns the placeholder verbatim so a typo in an owner-set template prints `{nmae}` instead of raising `KeyError` inside a presence event, where nobody would see the traceback. |
| `black_bloc/golive.py:261` | ⚠️ **A broken owner-set template renders the DEFAULT sentence, not the broken one.** The except is `Exception` on purpose: `str.format_map` has more than the two failure modes originally caught (a lone `{`, a bad conversion, a format spec a value cannot take), and this runs inside a presence event where a raise is invisible. Printing the raw broken template to `#live-now` would be a visible, permanent defect for every member; falling back to the known-good sentence is wrong only in the log line. That is why the log line exists — it is the only place the mistake is reported. |
| `black_bloc/golive.py:285` | ⚠️ **The whole debounce.** No row = never announced = go. A row with `ended_at IS NULL` = still live = do NOT announce, which is what makes a category change, a presence flap and a **bot restart** all silent. A closed row = announce only once the cooldown has passed. The function takes the *latest* session rather than a list precisely so those three cases cannot be reordered by a caller. ⚠️ An `ended_at` that is **present but unreadable** is treated as *ended*, not as open: the two cases were indistinguishable before the review, so one corrupt timestamp silenced that member forever. Only a genuine `NULL`/empty means "still live", and `cogs/content/golive.py:724` ages out even that. |
| `black_bloc/golive.py:328` | The end marker **edits** the announcement rather than deleting it, so the channel keeps its history; appending twice is prevented here rather than at the call site because a retry after a failed edit is the obvious thing to do later. |

## `black_bloc/timezones.py` — the zone Discord will not tell us

| Key | Note |
|---|---|
| `black_bloc/timezones.py:57` | ⚠️ **`parse_start` answers every local time, including the ones that do not exist** (review finding F14). Twice a year a zone skips an hour and twice a year it runs one again: `2027-03-14 02:30` never happens in New York, and `2027-11-07 01:30` happens twice. PEP 495 makes both *representable*, so the parser silently returned a real UTC instant for each — one of them an hour from what the person meant. The gap test is the round trip: stamp the naive time, convert to UTC, convert back, and a wall clock that comes out different means the clock jumped over it. The ambiguity test is the two folds disagreeing about the offset. Both are refused rather than resolved, because picking `fold=0` for somebody is picking the wrong hour half the time and the cost of asking is one sentence. |
| `black_bloc/timezones.py:10` | ⚠️ **America/Phoenix, and it is a deliberate choice rather than a neutral one.** Arizona keeps no summer time, so the default zone is the one where a stored offset can never drift — every other default would have been wrong for half the year for anybody who never ran `/timezone set`. Discord exposes no member time zone at all (checked at design time, `phase4-design.md`), which is why this feature exists rather than being derived. |
| `black_bloc/timezones.py:11` | The one format the modal accepts, stated once and shown to the person in three places — the input's own label, its placeholder, and the refusal at `black_bloc/events.py:55`. A 24-hour clock on purpose: `7:30` with no am/pm is the ambiguity a bot must not resolve by guessing. |
| `black_bloc/timezones.py:13` | Discord's own cap on autocomplete choices. A filter that returned more would be silently truncated by the API, so the truncation happens here where a test can see it (`tests/test_timezones.py:78`). |
| `black_bloc/timezones.py:34` | Prefix matches come before substring matches because `phoenix` should offer `America/Phoenix` first and not whatever alphabetically-earlier zone happens to contain the letters. The typed space becomes an underscore so `new york` finds `America/New_York` — nobody types the underscore, and without this the commonest search in the estate's own zone returns nothing. |
| `black_bloc/timezones.py:45` | ⚠️ **The naive time is stamped with the requester's zone and then converted, never the other way round.** `datetime.strptime` produces a zoneless time; attaching the zone with `replace(tzinfo=…)` and *then* `astimezone(UTC)` is what makes 19:30 in London genuinely 19:30 in London. Doing the conversion first would silently read every submission as UTC. Everything downstream — the row, the HammerTime stamps, the scheduled event — is UTC, so this is the only place a local time exists. |
| `black_bloc/timezones.py:86` | ⚠️ **Both stamps, always, and that is the whole reason this feature does not print a time.** `<t:…:F>` renders in each viewer's own zone and `<t:…:R>` counts down; a rendered string would be right for one person and wrong for everyone else, which is the problem `/timezone set` only half solves. Every card goes through here (`black_bloc/events.py:127`). |
| `black_bloc/timezones.py:92` | A stored zone that this machine cannot resolve reads back as **unset**, loudly. `tzdata` can be missing, and the IANA database does retire names; either way, falling back to the default with a warning is the behaviour that keeps `/event create` working, while raising inside a modal submit would show the person nothing at all. |

## `black_bloc/events.py` — the decisions, with no Discord in them

| Key | Note |
|---|---|
| `black_bloc/events.py:32` | The statuses whose review channel is finished with and may be swept. Review finding F3d: it was `(DONE,)` alone, so a `denied-` or `cancelled-` channel sat in the category for ever — the two outcomes most likely to happen, and the two nobody goes back to read. |
| `black_bloc/events.py:42` | Derived from `TRANSITIONS` rather than typed out, so a status that gains an exit stops being terminal in both places at once. It is what tells the cog when an event's lock may be dropped (`cogs/community/events.py:409`). |
| `black_bloc/events.py:166` | ⚠️ **The announcement promised an Interested button whether or not there was anything to click** (review finding F4) — and in test mode there never is, because a real scheduled event is visible to the whole server and is skipped (`cogs/community/events.py:561`). Three wordings, and the caller picks by what Discord actually returned: a made event with a URL gets the link, a made event without one points at the server's Events list, and no event at all says to watch the channel. Claiming a control that does not exist is the same defect as claiming a check that did not run (checklist 10). |
| `black_bloc/events.py:22` | Not a Discord limit — ours. A duration is free text, and `1000h` is far more likely to be a typo than a six-week event; refusing it here means the scheduled event Discord would have to be told about is always plausible. Raise it if the server ever runs something longer. |
| `black_bloc/events.py:33` | ⚠️ **The safety property of the whole feature, as a table rather than a pile of `if`s.** Every write to `events.status` asks `can_transition` first, so a second Approve cannot overwrite a Deny, a `done` event cannot be dragged back to `live`, and a cancelled one stays cancelled. It is what makes the per-event lock (`cogs/community/events.py:398`) sufficient: the lock serialises two clicks, and this decides which of them was legal. Terminal states are spelled with an empty tuple rather than being absent, so a missing key is a bug and not a silent "anything goes". |
| `black_bloc/events.py:53` | Anchored at both ends on purpose: without the `$` a pattern that matched `1h` inside `1happy hour` would read a title as a duration. The alternation makes both halves optional, so `2h`, `45m` and `1h30m` all parse — and `""` matching everything is why `not any(match.groups())` is checked separately. |
| `black_bloc/events.py:82` | Discord's channel-name rules, applied before Discord sees them. Unicode is folded to ASCII rather than dropped wholesale so `Ünïcödé Ríde` is still readable as `unicode-ride`; a name that folds away to nothing (emoji only) is handled at `:78`, not here. |
| `black_bloc/events.py:88` | ⚠️ **The cut comes before the strip, and the order matters.** Cutting to 100 can land mid-word and leave a trailing dash, which Discord accepts but looks like a mistake; stripping afterwards fixes it. A title and a name that both slugify to nothing still produce a legal channel name — the bare status — because "the API refused to make a channel" is not an acceptable outcome of somebody typing an emoji. |
| `black_bloc/events.py:94` | ⚠️ **A bare number is refused rather than guessed.** `2` could be two hours or two minutes; the cost of guessing wrong is an event that ends 118 minutes early or a scheduled event nobody can attend, and the cost of asking is one more sentence. Empty is different from unreadable: empty means the default two hours, which is the documented behaviour of leaving the field alone. |
| `black_bloc/events.py:127` | ⚠️ **One card, four surfaces** — the review channel, the requester's DM, the public announcement and the closed card after a decision all render through here, so they cannot drift apart. It takes the parts rather than a row so the modal can render a card before anything is written, and `cogs/community/events.py:428` is the one place a stored row becomes those parts. Every attacker-controlled field is clamped on the way in, because an embed Discord rejects is a card nobody sees. |
| `black_bloc/events.py:157` | ⚠️ **The only place an event may ping anything, and it allows exactly one role.** Titles, descriptions and locations are typed by whoever ran `/event create`; a title of `@everyone come here` renders as text and pings nobody (`tests/test_events.py:187`, `:196`). Same shape as `cogs/content/golive.py:558` on purpose — two features, one rule, and if this function ever grows a second allowed thing it grows it for both. |
| `black_bloc/events.py:177` | The go-live line is built here rather than in the loop so the ping prefix and the allowed-mentions list are written by the same module and cannot disagree — a prefix with no matching allowance renders a dead `@role` string, and an allowance with no prefix pings nobody while claiming to. |

## `black_bloc/cogs/content/golive.py` — F1/F2

> ⚠️ **GONE in the 2026-08-31 re-key:** `black_bloc/cogs/content/golive.py:GONE (was :767)` — the construct each note names is no longer in the file; the note itself needs a decision.

| Key | Note |
|---|---|
| `black_bloc/cogs/content/golive.py:57` | Logged **once, at cog load**, not per poll: with no Twitch app the feature is not broken, it is simply presence-only, and a per-minute warning would train the reader to ignore the log (`phase2-design.md`, §Detection). |
| `black_bloc/cogs/content/golive.py:110` | Reads a column that may not be on the row object at all. `sqlite3.Row` raises `IndexError` for an unknown key rather than returning `None`, so a row fetched by older code — or a `dict` fake in a test — would otherwise blow up in the middle of ending a session. |
| `black_bloc/cogs/content/golive.py:120` | ⚠️ **A post that did not happen has a REASON, and the reason decides what gets logged.** Returning `None` for all four failures made a broken channel id, a 403 and a test-mode refusal indistinguishable from a shadow-mode dry run — every one of them logged `golive.would_announce`, so the owner reading the log during the shadow rollout could not tell a working feature from a broken one. |
| `black_bloc/cogs/content/golive.py:148` | One Twitch login belongs to at most one member. Checked at `/twitch link` time with a sentence naming the clash (`cogs/content/golive.py:929`) rather than at poll time, because `INSERT OR REPLACE` is keyed on `user_id`: two members claiming one login both get a row, and the poller can only announce whichever it saw first. |
| `black_bloc/cogs/content/golive.py:199` | Sessions are rows, not memory. That is the entire restart story: a bot that dies mid-stream comes back, finds `ended_at IS NULL`, and stays quiet instead of re-announcing — the incumbent's second measured defect. `announced_message_id` is stored so the end edit can find the message after a restart too. ⚠️ The `IntegrityError` branch is the **partial unique index** (`storage/db.py:13`) speaking: it means another path opened a session for this member between the debounce check and this insert. Returning `None` rather than raising is what lets the caller treat "someone beat me to it" as a normal outcome. |
| `black_bloc/cogs/content/golive.py:206` | Used when the announcement could not be posted in mode `on`: the row is removed rather than closed, so it starts **no cooldown** and the next presence event or poll tick tries again. A closed row would look like a stream that ran and ended, and would suppress the retry for a full `golive_cooldown_minutes`. |
| `black_bloc/cogs/content/golive.py:211` | ⚠️ **Records what actually happened, not what the settings say should have happened** — and since 2026-09-01 it records *which role*, not merely that there was one. The removal path reads the row alone (`:613`), so a live role survives the mode being changed, the guard being installed, or the role setting being cleared mid-stream — all three of which used to strand the role on the member forever, because removal was gated on the *current* mode. ⚠️ The 0/1 flag left one hole those three did not cover: a staffer who **repointed `golive_live_role_id` at a different role mid-stream** had the old role taken off nobody and the new one taken off somebody who never had it. Storing the id closes it, exactly as `birthdays.role_added_id` does (`cogs/community/birthdays.py:153`). `live_role_added` is kept beside it rather than replaced by "id is not NULL" because a row written before the column existed has `NULL` there and did have the role — see the fallback at `:613`. |
| `black_bloc/cogs/content/golive.py:234` | The optional `source` is what keeps the two detection paths from fighting: the poller only ends sessions **it** opened (`source='twitch'`), while a presence go-live claims the user for the presence path. Without it a Twitch poll a minute after someone's presence went live would close a session the grace timer still owns. |
| `black_bloc/cogs/content/golive.py:293` | Twitch logins are 4–25 characters of letters, digits and underscore. Accepting a full URL as well means a member who pastes their channel address gets linked instead of a refusal — the commonest way this command is used wrong. |
| `black_bloc/cogs/content/golive.py:311` | ⚠️ Two `app_commands.Group` class attributes; the Twitch client is `self.helix` **on purpose**, because `self.twitch` is the group object `discord.py` binds here and assigning over it would unregister the commands. |
| `black_bloc/cogs/content/golive.py:314` | **Phase 8a merge.** `loop_health(name)` is how the status page reads this cog's loop health without knowing its attribute names: here they are `last_poll_ok_at` / `last_poll_error`, and only the `poller` loop has any. The page asks; it never guesses (`black_bloc/api/status.py:141`). |
| `black_bloc/cogs/content/golive.py:319` | Reconciliation runs **before** the poller starts and regardless of whether Twitch is configured — presence-only servers strand sessions too. The `is_connected` check is the offline-construction contract (`architecture.md`, rule 6): `tests/test_bot.py` loads every cog with no `connect()`, and both a `tasks.loop` and a reconcile query started there would fail. |
| `black_bloc/cogs/content/golive.py:331` | ⚠️ **The fix for the wedge.** `should_announce` refuses forever while a row has `ended_at IS NULL` (`black_bloc/golive.py:285`), so a kill -9, a Fly redeploy or a crash mid-stream left that member permanently unannounceable — the failure was silent and looked exactly like a working feature. Every open row is now re-checked at start and closed unless it can be *shown* to still be live. |
| `black_bloc/cogs/content/golive.py:339` | Two independent proofs of life, in cost order: the cached presence (free, but only if the guild is chunked — an uncached member reads as "not streaming", and closing is the safe answer there) and, for a Twitch-sourced session, one Helix call. ⚠️ A Twitch call that **fails** leaves the session open on purpose: "I could not check" is not "they are offline", and the age-out at `:718` is the backstop that stops even that wedging forever. |
| `black_bloc/cogs/content/golive.py:360` | The order is the one the review fixed: close the row → move the role → write the action log → **then** the cosmetic message edit. The edit is a round trip to Discord that can 403, 404 on a deleted message, or be refused by the guard; putting it last means none of those can abort the three things that matter. Same order as `_end_live` (`:458`), and the two are separate only because reconciliation has no `Member` object to hand. |
| `black_bloc/cogs/content/golive.py:383` | ⚠️ **The transition matters, not the state.** `before` still streaming means this event is a category or title change, and Discord sends a *lot* of those — reacting to `after` alone would re-announce on every one. The `_cancel_end` on the live branch is the flap fix: presence drops for a few seconds surprisingly often, and a cancelled grace timer is a stream that never ended. |
| `black_bloc/cogs/content/golive.py:395` | ⚠️ **The read-decide-insert below is not atomic**, and the presence listener and the Twitch poller can both reach it for the same member within the same tick — `open_session_for` says "nothing open" to both, and both announce. The per-user lock closes the window inside one process; the unique index (`storage/db.py:13`) closes it in the database, which is what survives a second process. Both, deliberately: the lock keeps the second caller from doing the work at all, the index keeps a bug in the lock from reaching `#live-now`. |
| `black_bloc/cogs/content/golive.py:399` | The order of the gates is deliberate: mode → bot → database → opt-out → role filters → debounce. Each is cheaper than the next, and the opt-out check comes before anything is written so an opted-out member leaves **no** trace in the sessions table (`phase2-design.md`, §Detection). |
| `black_bloc/cogs/content/golive.py:551` | ⚠️ **The guard is asked before the send, not after.** `guard.py` would raise `TestModeViolation` from inside the HTTP layer, which in a background task means an ugly traceback and a half-written session; asking first turns the same rule into a logged `golive.would_announce`. ⚠️ **`test_mode` is deliberately NOT treated as a post failure** — unlike a missing channel or a 403 it is a policy decision that will never succeed on retry, and rolling the session back would make every poll tick re-attempt and re-log it once a minute. It reads as shadow, which is what it is. Do not remove this when test mode is lifted — it is a no-op then (`bot.guard is None`). |
| `black_bloc/cogs/content/golive.py:578` | ⚠️ **Role edits are invisible to `guard.py`** (same class of hole as the role-menu select, `cogs/community/role_menus.py:659`). So the live role is only *added* when the mode is `on` **and** no guard is installed; otherwise the intent is written to the action log as `would_add_role`. Owner rule, `phase2-design.md`, §Test mode. It returns **the id of the role that really moved** (`None` when none did), because that id is what gets written to the session row (`:457`) — returning a bare `True` made the caller re-read the setting, which is the very thing that can change mid-stream. |
| `black_bloc/cogs/content/golive.py:611` | ⚠️ **Removal is unconditional on the session row, never on the current mode.** Adding is a policy decision; removing is cleaning up after one that was already made, and the settings can have changed in between. ⚠️ **The row names the role, and the current setting is only the fallback** (`:613`): `live_role_id` is `NULL` on any session opened before schema 19, and for those — and only those — today's `golive_live_role_id` is the best guess available, which is exactly the behaviour they had when they were written. A row written since carries the id that actually went on, so repointing the setting mid-stream no longer strands the old role. Every way the removal can fail — role deleted, member gone, guard installed, Discord refusing — ends in `golive.role_stuck` naming the member and role ids, because a *Live* role stuck on someone who is not live is invisible to the log otherwise, and it is the failure a person actually notices. |
| `black_bloc/cogs/content/golive.py:652` | ⚠️ Without this a template a staffer edited to contain `@everyone` — or a member whose display name does — pings the server. Only the configured ping role is allowed through, by id, so the mention in the rendered text still works and nothing else does. Passed on the end edit too (`:558`): an edit can create a mention the original post did not have. |
| `black_bloc/cogs/content/golive.py:706` | The 120 s grace is a **task per user**, held in `_end_tasks`, so a reappearing stream just cancels it. The `current_task()` check in `finally` is not paranoia: `_cancel_end` replaces the entry, and without the check a cancelled task's cleanup would pop its successor and leak a timer nobody can cancel. |
| `black_bloc/cogs/content/golive.py:718` | ⚠️ A `tasks.loop` that raises **stops for good**, silently. The body is one call inside a `try` so a Twitch outage costs one log line and the poller lives; `poll_once` is the real work and is what the tests call. `last_poll_error` is set here as well as inside `poll_once` because the two failures are different: this one is a bug, that one is Twitch. |
| `black_bloc/cogs/content/golive.py:730` | The backstop behind reconciliation: a session opened *after* the last restart can still be stranded (a member who leaves the guild, a presence event that never arrives, a grace task killed with the process). Unparseable `started_at` counts as old — the one thing a wedge fix must never do is wedge. Runs before the Twitch sweep and independently of it, so it still happens when Helix is down. ⚠️ It does **not** run at all on a server with no Twitch credentials, because the poller only starts when they exist (`:320`); reconciliation at start is the cover there. |
| `black_bloc/cogs/content/golive.py:748` | A live login with **any** open session is left alone — that is what stops a Twitch poll from double-announcing a stream presence already caught (`phase2-design.md`, §Detection). Ending, by contrast, is scoped to `source='twitch'` so the poller cannot close a presence session behind the grace timer's back. The `by_login` map is built by hand rather than as a comprehension so a login claimed by two members is **logged** instead of one of them being silently dropped. |
| `black_bloc/cogs/content/golive.py:787` | `Database.conn` raises when nothing is connected (`storage/db.py:453`), and a command body that touches it during startup or after a database failure would hand the caller a traceback and no reply. Owner rule: a refusal is a sentence saying what happened, what it needs and how to get it. |
| `black_bloc/cogs/content/golive.py:827` | ⚠️ **`is_running()` answers "is the timer ticking", which is not the same as "is polling working".** A Twitch outage leaves the loop running and every sweep failing, and the old `/golive status` reported that as healthy. The last good poll and the last error are what make the difference visible without reading the process log. |
| `black_bloc/cogs/content/golive.py:GONE (was :767)` | ⚠️ **Ephemeral, and rendered WITHOUT the ping-role prefix.** It was neither until the review: a staffer running a preview posted a real, visible message into the channel and pinged whatever `golive_ping_role_id` names — the ping the feature exists to control. It writes no session and moves no role; it is a preview, not a dry run of the announcer. |
| `black_bloc/cogs/content/golive.py:926` | ⚠️ **Owner sweep finding, and it is about fear, not accuracy: "for /twitch link it should say channel name not login, login sounds more concerning".** The parameter is `channel`, the describe text is *Your Twitch channel name (the part after twitch.tv/)*, and no sentence this command can show a member contains the word *login* any more — a member asked for a "login" reasonably reads it as being asked for a password. The **internal** names are deliberately unchanged: the column is still `twitch_login`, the helper is still `clean_login`, and the action-log detail key is still `login`, because those are Twitch's own term for the field and renaming them would be a migration. Only the two user-facing format placeholders moved to `{channel}`, since they sit inside sentences a member reads.
| `black_bloc/cogs/content/golive.py:948` | Refused before anything is written, and the sentence deliberately does **not** name the other member — `/twitch link` is runnable by anyone, and answering it with "that belongs to <@id>" turns the command into a lookup for who owns which channel. |

---

## `tests/conftest.py`

| Key | Note |
|---|---|
| `tests/conftest.py:18` | ⚠️ `Settings` reads `.env` from the CWD by default. Every test that builds `Settings` must pass `_env_file=None` **and** clear `DISCORD_TOKEN`, or it silently tests against the developer's real token. This fixture does both; a new test that constructs `Settings` directly must repeat them. |

## `tests/test_bot.py`

| Key | Note |
|---|---|
| `tests/test_bot.py:28` | The offline contract: the bot object builds and every cog in `COGS` loads with **no gateway and no token**. Anything that genuinely needs Discord is a manual smoke test in `../access/setup.md` §3, labelled as such (`architecture.md`, rule 6). |
| `tests/test_bot.py:30` | Pins the three privileged intents so a refactor of `black_bloc/intents.py` cannot quietly drop one — dropping `message_content` would disable moderation with no error anywhere. |

## `tests/test_guard.py`

| Key | Note |
|---|---|
| `tests/test_guard.py:153` | The `delete_channel` gate gets a fake channel cache rather than a real guild, because `allows_place` has to resolve an id to a category and that is the whole thing under test. The three cases are the three answers that matter: a sibling of the test channel passes, a channel in another category is refused, and a channel the bot cannot see is refused — an unknown place is never a permitted one. |
| `tests/test_guard.py:2` | ⚠️ **This file is the contract for the test-mode gate** (owner test policy, 2026-08-26). It must keep passing unchanged; a refactor that needs these tests edited is a refactor that changed the policy. |
| `tests/test_guard.py:26` | Calls `http.send_message` directly rather than `channel.send`, because the gate is installed on the HTTP layer — this is the narrowest probe of the thing actually being tested, and it needs no channel objects. |
| `tests/test_guard.py:32` | Patches `_original_send` so the allowed path is proven to pass *through* the gate without anything reaching the network. |
| `tests/test_guard.py:40` | The same two probes as the send pair above, against `edit_message` — the second way to put text in a channel, and the one the go-live end marker uses (`black_bloc/guard.py:118`). Positional `message_id` is passed because the real signature is `(channel_id, message_id, *, params)`; the gate only ever looks at the first argument. |
| `tests/test_guard.py:56` | A two-attribute stand-in for `discord.Interaction`: `allows_interaction` reads only `guild_id` and `channel_id`, so a real interaction object is unnecessary. |
| `tests/test_guard.py:66` | `guild_id=None` is a DM — allowed even though the channel id is `OTHER_CH`. That asymmetry is the point of the assertion. |

## `tests/test_app.py`

| Key | Note |
|---|---|
| `tests/test_app.py:4` | Guards the entrypoint two ways: `black_bloc.app` must import cleanly (it is the `black-bloc` console script, `pyproject.toml:24`), and the exit codes must stay `2`/`3` because `../access/` docs and any process supervisor key on them. |

## `tests/test_config.py`

| Key | Note |
|---|---|
| `tests/test_config.py:27` | A blank `DEV_GUILD_ID=` — exactly what `.env.example` ships — must mean unset. See `black_bloc/config.py:39`. |
| `tests/test_config.py:32` | Garbage must surface as a `ConfigError` naming the field, not a pydantic traceback. This is what makes exit code `2` readable. |

## `tests/storage/test_db.py`

| Key | Note |
|---|---|
| `tests/storage/test_db.py:8` | The `nested/` path is deliberate: it proves `connect()` creates missing parent directories (`black_bloc/storage/db.py:459`), which is what lets `DATABASE_PATH` point at a brand-new location. |
| `tests/storage/test_db.py:31` | The literal `== 6` and the table names are a **tripwire**, not a tautology: they fail loudly if someone edits `SCHEMA` without bumping the version, or bumps the version without shipping the tables. ⚠️ **This is the one existing assertion each schema phase is expected to change**, and changing it is the point — a phase that added a table without touching this line would have shipped a version number that says nothing. Phase 1 owns the first four, Phase 2 the three `golive_*` ones, Phase 3 the two `tempvoice_*` plus `honeypot_hits`, Phase 4 `user_timezones` and `events` (`phase4-design.md`), Phase 5 `birthdays` — and Phase 5 asserts its **columns** as well as the table name, because `opted_in` and `last_announced_on` are the two the sweep cannot work without. |
| `tests/storage/test_db.py:266` | Connecting four times over one file is the only honest test of an "idempotent migration": a `PRAGMA table_info` check that was wrong would raise `duplicate column name` on the second connect, which is precisely the failure that would take the live bot down on its next restart rather than on the deploy. |
| `tests/storage/test_db.py:317` | ⚠️ **Reproduces the one shape of live database that could refuse to open.** Dropping the index, writing the two open rows that only an un-indexed file could hold, then reconnecting proves the pre-schema cleanup runs early enough for `CREATE UNIQUE INDEX` to succeed (`black_bloc/storage/db.py:435`). Without it the fix is untested exactly where it matters — an existing file, not a fresh one. |

## `tests/test_settings_store.py`

| Key | Note |
|---|---|
| `tests/test_settings_store.py:61` | Builds the store on a **real** SQLite file in `tmp_path` rather than a mock, because the round-trip through JSON and `INSERT OR REPLACE` is most of what the store does. Still offline: no Discord anywhere in this file. |
| `tests/test_settings_store.py:74` | Three tiny fakes stand in for `Role`, `Permissions` and `Member`. They work because the staff derivation duck-types (`black_bloc/settings_store.py:575`) — a test that had to build real Discord objects would be a test nobody writes. |
| `tests/test_settings_store.py:129` | The second `load()` is the point of the test: it proves the cache is a *cache* and not the storage, so a restart reads back what was set. |
| `tests/test_settings_store.py:158` | Asserts `set(values) == set(KEY_TYPES)` rather than a literal dict of every key. The literal form was the Phase 1 shape and had to be rewritten the moment Phase 2 added eight keys; the substance — `all()` returns exactly the registry, with the set values in it — is unchanged and now survives the next feature. |

| `tests/test_settings_store.py:646` | ⚠️ **Pins the LIMIT of the staff detection, not just its successes.** A gate two calls away reads `False` on purpose — the owner's instruction was to omit the suffix rather than guess — so if someone later widens the search, this test is the place that says the widening was deliberate. |

## `tests/test_twitch.py`

| Key | Note |
|---|---|
| `tests/test_twitch.py:15` | ⚠️ **The reason no test can ever hit Twitch**: `FakeHttp` is a callable queue of `(status, payload)` pairs and records what it was asked, so token caching and the 401 refresh are asserted by *counting requests* rather than by mocking internals. An unexpected request raises rather than returning a benign default — a silent extra call is exactly the bug this file is for. |
| `tests/test_twitch.py:173` | `DeadSession` fakes the **session**, not the request seam, because the code under test is the default `_aiohttp_request` itself — the one path `FakeHttp` deliberately bypasses. A `request()` that raises synchronously never reaches `async with`, which is the same place a DNS failure surfaces, and it needs no event-loop network access. Still offline. |

## `tests/test_golive.py`

| Key | Note |
|---|---|
| `tests/test_golive.py:160` | Pins the incumbent's sentence **byte for byte** against the default template. It is the migration promise (`settings_store.py:29`): if this test has to change, the server's go-live posts changed with it. |
| `tests/test_golive.py:169` | ⚠️ The `****` assertion is the measured defect from the 199-post scan, turned into a test. Keep it even if `render` is rewritten. |
| `tests/test_golive.py:188` | Two different failures that must not be confused: an **unknown placeholder** still renders (the rest of the sentence is fine and `{nmae}` shows the staffer their typo), while a **broken template** cannot render at all and falls back to the default sentence. The second test compares against `render(GOLIVE_TEMPLATE, …)` rather than a literal so it does not become a second copy of the migration promise at `:160`. |

## `tests/cogs/content/test_golive.py`

| Key | Note |
|---|---|
| `tests/cogs/content/test_golive.py:139` | The fake bot carries a **real** `SettingsStore` on a **real** SQLite file and fake Discord objects around it. That split is deliberate: the settings and session behaviour is what the cog gets wrong, and mocking it would test the mock. `log_channel_id` is pointed at a *second* fake channel so that action-log embeds do not land in the feed channel and inflate the message counts these tests assert on. |
| `tests/cogs/content/test_golive.py:391` | ⚠️ **The restart test.** A second `GoLive` instance on the same database announces nothing, because the open row is the state — no in-memory set of "currently live" exists to be lost. This is the incumbent defect the feature promises to beat. Its counterpart is `:876`: the row must *also* be cleared when the stream is genuinely over, or "quiet across a restart" becomes "quiet forever". |
| `tests/cogs/content/test_golive.py:479` | ⚠️ **The test-policy proof for role changes.** With a guard installed, mode `on` still adds no role and logs `golive.would_add_role`. If this test is ever edited, the test policy changed (`phase2-design.md`, §Test mode). |
| `tests/cogs/content/test_golive.py:647` | The 120 s grace is monkeypatched to 0 on the **module** attribute, because `_end_after_grace` reads it at call time. The paired flap test keeps the real-ish delay and asserts the task was cancelled instead — between them they cover both branches without a test that sleeps. |
| `tests/cogs/content/test_golive.py:877` | ⚠️ **The wedge test.** A row left open by a stop is closed at the next `cog_load`, with `reason="reconciled_on_start"` in the action log; the two tests after it pin the exceptions (a member still streaming, a Twitch session Helix says is live) so that reconciliation cannot degrade into "close everything at start", which would re-announce every stream that survives a redeploy. |
| `tests/cogs/content/test_golive.py:947` | ⚠️ **The stranded-role test.** The role is added in mode `on`, the mode is then changed to `shadow`, and the role must still come off. Gating removal on the current mode is the bug; if this test is ever "fixed" by re-reading the mode, read `black_bloc/cogs/content/golive.py:618` first. |
| `tests/cogs/content/test_golive.py:1018` | Pins that a mode-`on` post that genuinely failed logs `golive.post_failed` and **not** `golive.would_announce`, and — the half that actually matters — that it leaves no session behind, so the very next attempt posts. A rolled-back session that still started a cooldown would look identical for sixty minutes. |
| `tests/cogs/content/test_golive.py:1194` | Asserts the **absence** of a word, which is unusual and is the point: the owner's objection to `login` was that it *sounds* like a password prompt, and a test that only checked the new wording would let the old word creep back into any one of the four sentences. It sweeps the command description, the parameter description and all four link constants in one string. `str()` around each because discord.py wraps descriptions in `locale_str`.
| `tests/cogs/content/test_golive.py:1072` | Drops the unique index first, so the assertion is about the **lock** and nothing else. Without it the index alone would make the test pass and the lock could be deleted unnoticed; `:1025` is the same scenario with both defences in place, which is what actually ships. |

## `tests/test_command_errors.py`

| Key | Note |
|---|---|
| `tests/test_command_errors.py:100` | The two mixins are exercised through **stand-in classes**, not through a real `discord.ui.Button`: building one needs a view, a message and an interaction payload, and none of that is what the test is about. What it asserts is the contract the cogs rely on — a failure answers the person and logs the traceback, and a dynamic item catches its own because nothing else will. |
| `tests/test_command_errors.py:76` | The handler is the **last** line, so the case that matters most is the one where answering itself fails: a 403 on the followup, an expired interaction token. It must warn and return, never raise — an exception escaping an error handler is what turns one broken command into a dead bot. |
| `tests/test_command_errors.py:90` | Asserts identity rather than behaviour on purpose: `install` exists only to put the function on the tree, and the behaviour is already pinned by the tests above. Anything more would be testing `discord.py`. |

## `tests/test_actionlog.py`

| Key | Note |
|---|---|
| `tests/test_actionlog.py:35` | `_Channel(raises=...)` is the whole reason this file exists: the contract is that a failing Discord post **still leaves the row** and warns. Asserting on `caplog` rather than on a mock call keeps the assertion on what an operator would actually see. |
| `tests/test_actionlog.py:198` | Pins that the embed carries only the fields it was given, in order. It is the cheapest guard against a later "just add a field" that pushes a real value past Discord's limits. |

## `tests/cogs/community/test_role_menus.py`

| Key | Note |
|---|---|
| `tests/cogs/community/test_role_menus.py:475` | ⚠️ **The three `role_diff` tests are the safety proof for the whole feature** — that a click can never strip a role the menu does not own (`black_bloc/cogs/community/role_menus.py:277`). If tests are ever pruned here, prune anything else first. |
| `tests/cogs/community/test_role_menus.py:374` | ⚠️ The Phase 3 rider's proof set: a `staff` menu refuses `post`, assign pre-ticks what the target already has and applies the diff to **them** (not to the staffer), unassign only offers what they hold and removes only what was picked, and a guard refuses the lot. The select's `values` are injected as `select._values`, which is what `discord.ui.Select.values` reads — no interaction payload has to be faked. |
| `tests/cogs/community/test_role_menus.py:762` | `showall` proved three ways: the content (heading with posted state, emoji/label/role per option, the empty-menu line), that **every** page is ephemeral and pings nothing, and that a hundred options really do split into more than one message none of which exceeds 1900 characters. The splitting test builds long labels on purpose — a chunker asserted only against short input is a chunker that has never chunked.
| `tests/cogs/community/test_role_menus.py:509` | Builds a real `RoleMenuView` from plain dicts — `discord.ui.View`/`Select` construct fine with no client — so persistence (`timeout is None`, `custom_id`) is asserted offline. Option rows are dicts rather than `sqlite3.Row` because both are read by subscript, and the storage tests already cover the row path. |

## `tests/cogs/community/test_tempvoice.py`

| Key | Note |
|---|---|
| `tests/cogs/community/test_tempvoice.py:493` | Pins the **eleven** `custom_id`s (nine, plus Unban and Unpermit from the `/voice` merge) **and their order**. They are persistence keys (`black_bloc/cogs/community/tempvoice.py:1240`): if this test has to change, every control panel already posted in the server has just stopped working. |
| `tests/cogs/community/test_tempvoice.py:582` | ⚠️ **The test-policy proof for channel creation** — a lobby outside the test channel's category makes nothing, one inside it works. Channel creates and member moves are invisible to `guard.py`, so this test *is* the enforcement's only proof. If it is ever edited, the test policy changed (`phase3-design.md`, Part A, §Test mode). |
| `tests/cogs/community/test_tempvoice.py:597` | Its other half, and ⚠️ **rewritten TWICE rather than renumbered, because the behaviour it describes keeps moving.** The `/voice` merge changed it from “logged as `tempvoice.would_post_panel`, not posted” to “posted into the test channel”; the 2026-08-27 owned-channel allowance changed it again to **posted into the voice channel’s own text chat**, which is where the owner asked for it. It now asserts the inverse of what it used to: the test channel got NOTHING, the voice chat got exactly one message, that message carries no “Controls for” pointer and never names the test channel, `panel_channel_id` is the voice channel’s own id, and `tempvoice.panel_elsewhere` is NOT logged. The fallback it replaced did not go away — `:612` is the same assertions for a channel Black Bloc did not make, which still lands in the test channel with the pointer and the `panel_elsewhere` line. `:631` is the no-test-channel case, which is a `panel_failed` (checklist 2). |
| `tests/cogs/community/test_tempvoice.py:752` | ⚠️ **The burst test.** Two simultaneous leaves must delete the channel once and log once. Voice-state events genuinely arrive together, and unlike go-live there is no unique index behind the lock — the lock and the re-read inside it are the only defence (`black_bloc/cogs/community/tempvoice.py:1419`). |
| `tests/cogs/community/test_tempvoice.py:1246` | ⚠️ **The regression test for the sweep finding "it made a locked channel i cant get into".** It starts from a lobby literally named `join` and asserts setup renames it back to the full setting default rather than refusing, so the recovery path is exercised, not just the happy one. |
| `tests/cogs/community/test_tempvoice.py:1371` | ⚠️ **The other half of that finding, and the one that matters most: the overwrites handed to `create_voice_channel`.** The category denies `@everyone` `connect`; the assertions are that the Member role, the resolved staff role and the bot each come back with `connect=True`, and that `@everyone` is still denied. The same assertions run against the repair path (`:1387`) and against a spawned channel (`:1405`), because all three build their overwrites from the same two helpers and a fix that only reached one of them would look green here. |
| `tests/cogs/community/test_tempvoice.py:1451` | Loop health as two questions, not one: what the loop last finished, and what it last raised. `loop_health("poller")` returning `(None, None)` is asserted deliberately — `api/status.py` asks every cog about every loop name it finds, so a cog that answered for a name it does not own would put another feature's health on the status page. |

| `tests/cogs/community/test_tempvoice.py:1764` | ⚠️ **The regression test for sweep finding 2: a lobby the store lost track of must be TAKEN OVER, not duplicated.** It starts from the owner's real shape — a channel called `join` in the test channel's category and an empty `tempvoice_creator_ids` — and asserts `guild.created == []`. Its pair (`:1794`) asserts the id is stored even when Discord refuses the rename, because the id is the durable half. |

## `tests/cogs/moderation/test_honeypot.py`

| Key | Note |
|---|---|
| `tests/cogs/moderation/test_honeypot.py:320` | The exemption matrix as a table of five authors. It is the test to keep if any others here are dropped: everything else in this feature is recoverable, and banning a member of the server is not. |
| `tests/cogs/moderation/test_honeypot.py:395` | ⚠️ **The test-policy proof for bans.** Mode `on` plus a guard still bans nobody and logs `honeypot.would_ban`. If this test is ever edited, the test policy changed (`phase3-design.md`, Part B, §Test mode). |
| `tests/cogs/moderation/test_honeypot.py:407` | Its counterpart, and the reason both exist: a ban Discord **refused** logs `honeypot.ban_failed` and never `honeypot.would_ban`. The owner's verification method is reading the log, so a broken permission must not look like a dry run (checklist 2). |
| `tests/cogs/moderation/test_honeypot.py:482` | ⚠️ **The burst test.** Two posts from one account arriving together produce two hits and exactly **one** ban call — the per-author lock plus `banned_already` (`black_bloc/cogs/moderation/honeypot.py:174`). |

## `tests/api/test_server.py`

| Key | Note |
|---|---|
| `tests/api/test_server.py:14` | `_FakeBot` keeps the API test offline — `create_app` only ever touches `is_ready()`, `guilds` and `latency`, so a stub is enough and no Discord client is built. |
| `tests/api/test_server.py:31` | `latency = 0.042` → `42` ms pins the seconds-to-milliseconds rounding in `black_bloc/api/server.py:133`. |

## `tests/test_timezones.py`

| Key | Note |
|---|---|
| `tests/test_timezones.py:134` | The DST cases are dated **2027** on purpose: 2026's transitions are in the past relative to the day this was written, and a test that reads differently once a date goes by is a test that will fail on a Tuesday for no reason. Both hemispheres of the estate's zones are covered — New York and London move on different weekends — and Phoenix is the control, because Arizona never moves at all. |
| `tests/test_timezones.py:39` | ⚠️ **This assertion is why `tzdata` is a dependency.** On Windows `zoneinfo` has no zone database of its own: `available_timezones()` returns an empty set and every lookup fails, so the whole feature was dead on the developer's machine until the package was pinned. It fails loudly here rather than silently in a command body. |
| `tests/test_timezones.py:51` | The default zone is tested for **not** moving, and New York is tested for moving, because a conversion that ignored the zone entirely would pass a Phoenix-only test. The pair is the actual proof. |

## `tests/test_events.py`

| Key | Note |
|---|---|
| `tests/test_events.py:98` | ⚠️ **The status-machine tests are the safety proof for the feature** — they are what says a Deny cannot be overwritten by an Approve and a finished event cannot be dragged back. If tests are ever pruned here, prune anything else first. |
| `tests/test_events.py:190` | ⚠️ **The ping test.** Only the configured role may ever be mentioned, and a title of `@everyone come here` must render as text. Titles are typed by anyone with `/event create`; if this test is ever edited, read `black_bloc/events.py:160` first. |

## `tests/cogs/community/test_events.py`

| Key | Note |
|---|---|
| `tests/cogs/community/test_events.py:120` | `FakeScheduledEvent` **raises `ValueError` the way discord.py does** — `cancel()` on a running event, `end()` on one that is not running — because that raise is the whole of review finding F1 and a fake that merely records the call would have passed against the broken code. |
| `tests/cogs/community/test_events.py:223` | `FakeGuard` mirrors the real one's two questions rather than just its channel id: `allows_channel` for speaking, `allows_place` for making, renaming and deleting. It takes the category as a constructor argument instead of walking a channel cache, so a test can say "the test channel is missing" and "there is no category" separately. |
| `tests/cogs/community/test_events.py:411` | Starts are built by formatting a real future instant **in the zone under test**, not by hard-coding a date. A literal would start failing the "already gone by" check on whatever day it passed, which is the kind of test failure nobody diagnoses and everybody deletes. |
| `tests/cogs/community/test_events.py:564` | ⚠️ **The test-policy proof for the review card.** With a guard installed the review channel is still made and still named, and the card lands in the **test channel** instead — the deviation explained at `black_bloc/cogs/community/events.py:405`. If this test is ever edited, the test policy changed. |
| `tests/cogs/community/test_events.py:637` | Its other half, and the one that matters most: a real Discord scheduled event is visible to the whole server, so under a guard none is made and the log says `event.would_create_scheduled` — never `event.create_scheduled_failed`, which is asserted in the same test because the owner's verification method is reading the log (checklist 2). |
| `tests/cogs/community/test_events.py:736` | ⚠️ **The burst test.** Two mods pressing Approve together produce exactly one approval and one action-log row, and the loser is told. Unlike go-live there is no unique index behind the lock — the lock plus the `can_transition` re-read inside it is the only defence (`black_bloc/cogs/community/events.py:326`). |
| `tests/cogs/community/test_events.py:786` | Pins that the go-live sweep picks the started-and-approved row and leaves the future one and the undecided one alone. A loop that took "everything due" would announce events nobody approved. |

---

# Phase 5 — birthdays (F6), added 2026-08-26

> Added on the Phase 5 branch `worktree-agent-af78b986a286af545`, built beside
> Phase 4 rather than after it. New files: `black_bloc/birthdays.py`,
> `black_bloc/data/birthday_import_2026-08-05.json`,
> `black_bloc/cogs/community/birthdays.py`, `tests/test_birthdays.py`,
> `tests/cogs/community/test_birthdays.py`, `tests/cogs/test_core.py`. Edited, by
> APPENDING only so the two branches merge cleanly: `settings_store.py` (five
> `BIRTHDAY_*` constants, `HEX_COLOR`, six `birthday_*` keys at the end of
> `KEY_TYPES` / `KEY_CHOICES` / `KEY_HELP`, six branches at the end of
> `SettingsStore.default`, a `color` branch at the end of `coerce_value` and
> `SettingsStore.clear`), `storage/db.py` (`SCHEMA_VERSION` 6, the `birthdays`
> table at the end of `SCHEMA`, `birthdays.role_added_id` in `ADDED_COLUMNS`),
> `cogs/core.py` (`/settings clear`), `bot.py` (one `COGS` entry at the end),
> `pyproject.toml` (`tzdata` as a runtime dependency and `data/*.json` as package
> data), `tests/storage/test_db.py`, `tests/test_settings_store.py`.
>
> ⚠️ **Line numbers below are the MERGED tree's, re-keyed on 2026-08-26 when
> Phase 5 landed on `main`.** They were the branch's until then; every key in
> `birthdays.py`, `cogs/community/birthdays.py`, both birthday test files and
> `tests/cogs/test_core.py` was re-checked against the file after the merge.
> The branch's own numbers came from commits `149c568` (findings 1–5, the
> must-fix ones) and `6793c97` (6–12). After the merge: **534 tests pass; ruff
> clean.**
>
> ⚠️ **`SCHEMA_VERSION` went 4 → 6 on the branch, skipping 5 on purpose: v5 is
> Phase 4's (`user_timezones` + `events`), built in parallel in the main tree.**
> The comment that would say so does not exist in `storage/db.py` (rule 0); this
> paragraph is it. Both bumps are additive `CREATE TABLE IF NOT EXISTS` steps,
> so the number is a label, not a migration — either order of merging produces
> the same database, and the merged tree is **v6 with all five phases' tables**.
>
> ⚠️ **Two things the merge deleted, both under "one fact, one home" (checklist
> 15).** `birthdays.timezone_table_exists` — a `sqlite_master` probe asking
> whether Phase 4's `user_timezones` existed — is gone, because in the merged
> tree it always does and `storage/db.py:123` is the one place that decides so.
> And Phase 4 and Phase 5 had each written a `SettingsStore.clear`; the merge
> kept Phase 5's, which is the strict superset (see `settings_store.py:649`).
>
> NOT verified: anything against live Discord. No birthday embed has ever been
> posted by this code, no member cache has ever been chunked by it, and the
> 39-row import has never been run against the real member list — so how many of
> the 39 names actually resolve is unknown and will only be known from the report
> the owner gets the first time they run `/birthday import`.

## `black_bloc/birthdays.py` — the decisions, with no Discord in them

| Key | Note |
|---|---|
| `black_bloc/birthdays.py:18` | ⚠️ **Addressed through `importlib.resources.files`, not `__file__`** (review finding 12). `pyproject.toml` ships `data/*.json` as package data, and a package installed as a zip or by a loader that does not unpack has no `__file__` directory to walk — the seed file would silently be "0 rows" and the import would report a packaging fault. The value is a `Traversable`, which answers `read_text` and `exists` the same way a `Path` does; the `path` argument both readers take is still an ordinary `Path` for tests. |
| `black_bloc/birthdays.py:19` | The last-resort zone is a fixed **UTC-7**, which is Phoenix all year because Arizona does not observe DST. It only comes up if `zoneinfo` cannot resolve `America/Phoenix` at all — a container built without `tzdata`, which `pyproject.toml` now pins for exactly this reason. A fixed offset is correct here and would be wrong for any other zone. |
| `black_bloc/birthdays.py:21` | Discord's embed description caps at 4096; 2000 is well under it and keeps a staff-edited template from ever producing a send that fails on length. Truncation, not refusal, because a birthday post half the length is better than none on the day. |
| `black_bloc/birthdays.py:52` | Only a **leading** bracket or paren group is stripped, and repeatedly, because Birthday Bot's export renders nickname prefixes verbatim: `[Straight Hands] ShinDarkShadow`, `(Umazing) nadia`. A trailing flag emoji (`PopNoTartsEh 🇨🇦`) is deliberately left on — it is part of the name people actually use, and the contains-scoring handles it. A name that is *entirely* a tag is returned untouched rather than emptied. |
| `black_bloc/birthdays.py:58` | 3 / 2 / 1 with a floor of 2 is the owner's rule from `phase5-design.md`: a bare "contains" hit (score 1) is never imported on its own, because `PT` is inside dozens of names. Scores are a deliberate ranking, not a confidence — two members scoring 3 is ambiguity, not a tie to break. |
| `black_bloc/birthdays.py:98` | Falls back rather than raising, because this runs inside the five-minute sweep: one member with a nonsense zone string must not stop everyone else's birthday. The fallback chain is member zone → server zone → fixed UTC-7. |
| `black_bloc/birthdays.py:110` | Clamping uses **2024** (a leap year) for the month lengths so February 29 survives storage. Every read of a stored row goes through this, so a hand-edited database row cannot crash the sweep. |
| `black_bloc/birthdays.py:122` | Clamping and refusing are two different jobs and both exist on purpose: a *command* refuses February 30 with a sentence (silently storing the 29th would be a lie about the person's birthday), while a *stored row* is clamped so a bad row is survivable. |
| `black_bloc/birthdays.py:155` | February 29 is observed on the 28th in ordinary years — the choice is the 28th rather than March 1 so the wish always lands in the birth month. |
| `black_bloc/birthdays.py:167` | Returns **local midnight in the member's own zone**, which is what makes `<t:…:D>` render correctly for every viewer. The loop over two years is what handles "already passed this year" and February 29 in one pass. |
| `black_bloc/birthdays.py:186` | The age *they turn in the year of the date handed in*. ⚠️ Which date that is matters and was a review finding (5): the sweep passes **today**, and `/birthday show` passes the **next occurrence** — asking "how old today" for a birthday four months away answers with last year's number. Anything under 0 or over 150 reads as no age rather than a wrong one. |
| `black_bloc/birthdays.py:206` | The colour is staff-editable text, so an unparseable value falls back to the incumbent's `#4eefff` with a warning instead of raising inside the sweep (checklist item 17). It matches with `settings_store.HEX_COLOR` — **one regex, two callers** (checklist 15): the validator refuses a bad colour at the boundary, and this survives one that was already on disk before the validator existed. |
| `black_bloc/birthdays.py:215` | `str.format` raises `KeyError` on an unknown field, which is exactly the wanted behaviour: a staff template with `{nickname}` in it falls back to the default wording and says so in the log, rather than posting `{nickname}` or nothing. |
| `black_bloc/birthdays.py:243` | ⚠️ **The scoring rewritten for review finding 4.** Comparison is casefolded for the "exact" rules too — Discord usernames are case-insensitive in practice, and the export's capitalisation is whatever Birthday Bot rendered on the day. The **tag-stripped display name** is compared as an exact rule, not a contains one, because that is the whole finding: a member whose nickname is `[Straight Hands] ShinDarkShadow` only ever scored 1 against the export's `ShinDarkShadow` and so could never clear the floor of 2. It sits in the *username* tier rather than the display tier on purpose, so a member called plainly `PT` still beats `[40] PT` instead of the pair reading as ambiguous. `global_name` is scored because Discord's new display names live there and are frequently what the export captured. |
| `black_bloc/birthdays.py:283` | The three outcomes are `matched` / `ambiguous` / `not_found` and every one of them is reported — nothing is ever guessed. `ambiguous` deliberately carries the candidates, because the owner resolving it by hand needs the names, not a count. |
| `black_bloc/birthdays.py:295` | ⚠️ **Kept although nothing in the bot calls it** (review finding 7 asked why): it is what **generated** the JSON seed from the archived export, and it is what a future export gets re-parsed with. That is the reason the 39 rows are data and not a Python literal in the cog. It is exercised by `tests/test_birthdays.py`. |
| `black_bloc/birthdays.py:318` | Reads both a bare list and the `{"exported": …, "rows": […]}` wrapper, and skips an unreadable row rather than failing the whole import — a packaging fault should cost one name, not the command. |
| `black_bloc/birthdays.py:344` | Ages in the export are as of the export date, so the year they imply can be a year out until the person corrects it. The date lives in the data file, not in code, and the import report says the caveat out loud. |
| `black_bloc/birthdays.py:354` | Sorting is on the **UTC instant** of each local midnight, not on the local wall clock, because entries in different zones are otherwise not comparable. ⚠️ `/birthday next` calls this rather than sorting its own copy (review finding 7) — the ordering rule has one home. |
| `black_bloc/birthdays.py:378` | Any failure returns the server zone rather than raising: the sweep must produce *a* date for every member, and Phoenix is the same answer the incumbent Birthday Bot gives everyone today. The fallback chain is member zone → server zone → fixed UTC-7 (`:19`). ⚠️ **The `timezone_table_exists` probe that stood in front of this was DELETED when Phase 5 merged into Phase 4** (checklist 15). It existed because the birthdays branch was built beside Phase 4 and could not assume `user_timezones` was there; now `storage/db.py:163` creates the table on every `connect()`, so a `sqlite_master` lookup on each zone read was a **second opinion about the schema** — and the module that owns that fact is `storage/db.py`. The `except` here already answers a genuinely missing table with the server zone, so nothing was lost but the extra query. |

## `black_bloc/cogs/community/birthdays.py` — F6

| Key | Note |
|---|---|
| `black_bloc/cogs/community/birthdays.py:49` | Five minutes is chosen against the measurement: the incumbent posts at ≈00:03 local, so a five-minute tick lands 00:00–00:05 and matches it. A shorter tick buys nothing, because the check is "is it that member's calendar day yet", not "is it exactly midnight". |
| `black_bloc/cogs/community/birthdays.py:113` | The upsert **clears `last_announced_on`** so that setting a birthday to today still posts on the next tick — that is the owner's test sweep. It deliberately does **not** clear `role_added` / `role_added_id`: a role that is on somebody has to come off tomorrow whatever they did to their row in between. |
| `black_bloc/cogs/community/birthdays.py:153` | ⚠️ **The row records WHICH role went on, not just that one did** (review finding 2). `birthdays.role_added_id` is added by `storage/db.py:406`'s additive `ADDED_COLUMNS` step, not by the `CREATE TABLE`, so an existing database gains it on the next start — same pattern as `golive_sessions.live_role_added`. Without it the reversal read the *current* setting, and changing `birthday_role_id` during somebody's birthday stranded the old role on them for good. |
| `black_bloc/cogs/community/birthdays.py:200` | Discord refuses a message over 2000 characters; 39 imported names or a full year's list go past that easily. Splitting is done on whole lines so a name is never cut in half across two messages. |
| `black_bloc/cogs/community/birthdays.py:277` | The counts line comes first because it is the answer; the lists follow for the owner to act on. The second line says **how many members were searched**, because a report of "12 not found" means something completely different against 40 cached members than against 900 (review finding 4, and checklist 10 — never claim a check that did not really happen). |
| `black_bloc/cogs/community/birthdays.py:308` | **Phase 8a merge.** `loop_health(name)` is how the status page reads this cog's loop health without knowing its attribute names: here the success time is `last_run_at`, not `last_ok_at` — the one naming difference that made a guessing reader silently report nothing at all. The page asks; it never guesses (`black_bloc/api/status.py:141`). |
| `black_bloc/cogs/community/birthdays.py:318` | `tasks.loop.start()` runs the body immediately after `before_loop`, so a restart re-checks every row at once — today's un-posted birthdays and yesterday's still-attached roles both (checklist items 4 and 25). ⚠️ When the database is not connected yet the loop is **not** started here; `on_ready` at `:340` starts it instead (review finding 9), otherwise a slow database meant no birthdays for the life of the process. |
| `black_bloc/cogs/community/birthdays.py:323` | Cancelled on unload so a reloaded cog does not leave a second sweep running and double-post. |
| `black_bloc/cogs/community/birthdays.py:326` | The whole tick is wrapped: an exception inside `tasks.loop` kills the loop for the life of the process, and a dead birthday loop is invisible until a birthday is missed. The error is kept for `/birthday status` to show, which is what makes "is it healthy" answerable rather than "is it running" (checklist item 9). |
| `black_bloc/cogs/community/birthdays.py:343` | ⚠️ **The `@loop.error` handler checklist 28 asks for** (review finding 9). The `try` at `:316` covers the body; this covers everything else — a raise from `before_loop`, from the store, or from the wrapper itself — and `restart()` is the only thing that brings a stopped `tasks.loop` back, because discord.py does not retry it. The reason is kept in `last_error` so `/birthday status` shows it. |
| `black_bloc/cogs/community/birthdays.py:351` | The retry for a database that was not connected at `cog_load`. Guarded by `is_running()` so a reconnect (`on_ready` fires again after a resume) does not start a second sweep. |
| `black_bloc/cogs/community/birthdays.py:355` | ⚠️ **Everything hangs off `today` in the *member's* zone, not the server's.** A member at UTC-4 is wished during the evening before in Phoenix — that is not a bug, it is what the incumbent does and what the owner asked for. An **unavailable** guild is skipped entirely (checklist 32): its member cache is not to be trusted, and treating it as real would log every member as missing. |
| `black_bloc/cogs/community/birthdays.py:371` | The role reversal is checked *before* the opt-in and mode gates, so turning the feature off never strands a role (checklist item 3). |
| `black_bloc/cogs/community/birthdays.py:391` | ⚠️ **A cache miss is not a wish** (review finding 6). The row is *not* stamped `last_announced_on`, so once the member is visible again the wish still lands on the day; `birthday.member_missing` is logged at most once per member per local day, because the sweep would otherwise write 288 identical rows for anybody who has left. The old behaviour marked the day done and called it `birthday.skipped`, which silently ate the birthday of anyone the cache had not filled in yet. |
| `black_bloc/cogs/community/birthdays.py:430` | Returns a reason string instead of raising, so the caller can tell the three cases apart: `shadow` and `test_mode` are dry runs that still mark the day done, anything else is a real failure that does not. |
| `black_bloc/cogs/community/birthdays.py:459` | ⚠️ **The guard cannot see a role change, and neither can `shadow`** (review finding 1, checklist item 1). The role is only really added when the mode is `on` **and** no guard is installed; every other case logs `birthday.would_add_role` and does nothing. Before the fix, shadow mode — the mode the feature ships in — handed out a real role on the live server while claiming to be a dry run. `role_added` is only set once Discord has actually accepted the change. |
| `black_bloc/cogs/community/birthdays.py:490` | The reversal is unconditional on the mode at reversal time — the row says the role went on, so it comes off, even if birthdays were switched `off` in between (checklist item 3). ⚠️ It removes **`discord.Object(id=role_added_id)`**, never `guild.get_role(...)`: a role missing from the cache, or a `birthday_role_id` that has since changed or been cleared, must not be a reason to leave it on somebody — and the flag is only cleared once Discord has accepted the removal. A removal Discord refuses keeps the flag and retries next tick; only the *log line* is rate-limited, so a permanent 403 cannot write 288 action rows a day. |
| `black_bloc/cogs/community/birthdays.py:527` | ⚠️ **`/birthday remove` and `/birthday optout` hand the role back first** (review finding 3). Deleting the row was previously enough to strand the role until somebody noticed — the row that says "take this off tomorrow" was the thing being deleted. Both run inside the same per-user lock as the sweep. |
| `black_bloc/cogs/community/birthdays.py:533` | One log line per member per local day per kind. The sweep is idempotent by design, which means a persistent failure would otherwise repeat every five minutes — and the owner's verification method is reading the log. |
| `black_bloc/cogs/community/birthdays.py:624` | ⚠️ The write takes the **per-user lock** (review finding 8, checklist 6): it clears `last_announced_on` while a sweep tick may be deciding whether to post for that same member, and the two interleaved could post twice or not at all. |
| `black_bloc/cogs/community/birthdays.py:620` | The confirmation quotes the zone by name and the next occurrence as a HammerTime stamp, because "midnight" is the question people actually get wrong — theirs or the server's. |
| `black_bloc/cogs/community/birthdays.py:713` | `/birthday show` works the age out at the **next occurrence**, not in the current calendar year (review finding 5): a birthday still four months away was reported a year young. |
| `black_bloc/cogs/community/birthdays.py:748` | `<t:…:D>` and `<t:…:R>` render in each viewer's own zone, which is the point; `allowed_mentions` is `none()` so the `<@id>` list reads as names without pinging five people. The ordering comes from `birthdays.upcoming()` rather than a second sort here. |
| `black_bloc/cogs/community/birthdays.py:786` | Paginated by packing lines, not by a page number: the first page answers the interaction and the rest go as ephemeral follow-ups, so the command never fails on length. |
| `black_bloc/cogs/community/birthdays.py:826` | `/birthday mode` writes a setting, so it takes the same `_ready` / `is_connected` guard as every other command that touches the database (checklist 8) — without it a mode flip during a database outage answered "The application did not respond". |
| `black_bloc/cogs/community/birthdays.py:848` | ⚠️ **`birthday_role_id` had no way back to "none"** (review finding 10): `/settings set-role` can only point it somewhere. This and the general `/settings clear` at `cogs/core.py:260` are two front doors on one `SettingsStore.clear`. The sentence says out loud that a role already given still comes off tomorrow, because that is the surprising half. |
| `black_bloc/cogs/community/birthdays.py:870` | Health, not liveness: last successful sweep, last error, resolved staff roles, and how many rows are stored and opted in. It also says out loud that test mode gives no roles, because that is the fact most likely to look like a bug. |
| `black_bloc/cogs/community/birthdays.py:900` | ⚠️ **Defers first.** Filling the member cache is a gateway round trip that cannot fit in Discord's three-second interaction window (checklist item 24). The report goes back as ephemeral follow-ups to the person who ran it. |
| `black_bloc/cogs/community/birthdays.py:927` | ⚠️ **Scores against `guild.members`, with no network call at all** (review finding 4). The design premise in `phase5-design.md` — *"member lookup uses `guild.query_members(query=…)` (HTTP, no members intent needed)"* — **is wrong for this bot**: the members intent is on (`intents.py:8`), so the cache holds the whole server; and `query_members` matches **prefixes only**, so every `[Tag] Name` nickname in the export was unfindable, and its `limit=10` could silently drop the right member. The cache is chunked first when it is shorter than `member_count`, and the report says how many members were searched, because "not found" against a half-filled cache is a different claim from "nobody matched". |
| `black_bloc/cogs/community/birthdays.py:930` | Re-running imports nothing it has already stored — an existing row of *any* source is kept and reported, which is stricter than the spec's "never overwrite `source='self'`" and makes the command genuinely idempotent. Without that, a re-run on somebody's birthday would clear their `last_announced_on` and post twice. |

## `settings_store.py` and `cogs/core.py` — the Phase 5 appends

| Key | Note |
|---|---|
| `black_bloc/settings_store.py:68` | The hex-colour regex lives here, next to the validator that enforces it, and `birthdays.parse_color` imports it — `birthdays.py` already depends on this module, and the reverse import would be a cycle. |
| `black_bloc/settings_store.py:472` | ⚠️ **`birthday_color` is a `color`, not `text`** (review finding 11). As text, `/settings set-value birthday_color blue` was accepted, stored, and then quietly ignored every night when `parse_color` fell back — a setting that says one thing and does another. The refusal names the shape (`#4eefff`) and the value is normalised to lower case with the `#` so `/settings show` and the stored row always read the same. |
| `black_bloc/cogs/core.py:30` | Only **channel** and **role** keys are clearable: those are the ones whose absence is meaningful ("no ping role", "no birthday role"). An enum or an int has a default that is already a real value, and `set-value` can reach it. The list is 11 long — Discord refuses a choice list over 25. |
| `black_bloc/cogs/core.py:244` | Logged as `settings.clear` only when something was actually removed, so the action log does not fill with no-ops (same rule as `/birthday role clear`). |

## `tests/test_birthdays.py`

| Key | Note |
|---|---|
| `tests/test_birthdays.py:115` | The Phoenix gotcha as a test: at 04:30 UTC it is already the 10th in New York and still the 9th in Phoenix, so the same row is due for one member and not for another. This is the case that decides whether the whole feature is right. |
| `tests/test_birthdays.py:138` | The two dates `age()` can be asked about, side by side: the next occurrence of a January birthday says 37 where today says 36. That difference **is** review finding 5. |
| `tests/test_birthdays.py:188` | The tagged-nickname case from the export — `[Straight Hands] ShinDarkShadow` — scored through `resolve` end to end. It failed before the finding-4 fix and is the reason the stripped display name is an exact-tier rule. |
| `tests/test_birthdays.py:195` | Scoring is tested through `resolve` on the real shapes from the export, because the tag-stripping and the scoring only mean anything together. ⚠️ Two assertions here **changed** with finding 4: `[40] PT` is now a match rather than an ambiguity, and a partial hit is demonstrated with `PTolemy` instead. |
| `tests/test_birthdays.py:238` | Asserts against the **shipped** seed file rather than a copy of the table, so the test fails if the data file is dropped from the package — and, since finding 12, if `importlib.resources` cannot find it either. The parser itself is tested on a small sample; duplicating all 39 rows into the test would be a second home for the same fact. |
| `tests/test_birthdays.py:294` | The fallback chain on a **real** database: no row means the server zone, a row means the member's own. It used to create `user_timezones` by hand and assert the table was absent first, which stopped being possible when Phase 5 merged into Phase 4 — the schema now always has the table (`black_bloc/storage/db.py:163`). |

## `tests/cogs/community/test_birthdays.py`

| Key | Note |
|---|---|
| `tests/cogs/community/test_birthdays.py:270` | Runs the sweep twice and asserts **one** post: `last_announced_on` is the restart story, and a bot that restarts every five minutes must still wish someone once. |
| `tests/cogs/community/test_birthdays.py:350` | The three outcomes are asserted as three different log kinds — a failure retries and is not marked done, a dry run is marked done, and neither is called an announcement (checklist item 2). |
| `tests/cogs/community/test_birthdays.py:380` | Finding 6: a member the cache cannot see is logged once, the day is left **open**, and the wish lands as soon as they appear. |
| `tests/cogs/community/test_birthdays.py:424` | Finding 1 as a test: in `shadow`, with no guard installed, `add_roles` is never called and the row stays clean. This is the one that would have caught the live role hand-out. |
| `tests/cogs/community/test_birthdays.py:437` | Finding 2 as a test: the role is given, `birthday_role_id` is then pointed at a *different* role, and the role that comes off the next day is still the one that went on. |
| `tests/cogs/community/test_birthdays.py:469` | Finding 3, both halves: `/birthday remove` and `/birthday optout` on the day take the role back before they forget or mute the row. |
| `tests/cogs/community/test_birthdays.py:499` | The role goes on once, is not re-added on the next tick, and comes off the following day; the sibling test flips the mode to `off` in between and asserts it still comes off. |
| `tests/cogs/community/test_birthdays.py:555` | The UTC-4 case end to end through the cog — the offline proof that the member's own zone, not the server's, drives the day. It writes one `user_timezones` row into the schema's own table; before the Phase 5 merge it had to `CREATE` that table itself. |
| `tests/cogs/community/test_birthdays.py:778` | Finding 4: the import is resolved against a fake `guild.members` — including `[Straight Hands] ShinDarkShadow` — two members called Prez are ambiguous, one name is not found, no `query_members` call is made, and the re-run stores nothing new. |
| `tests/cogs/community/test_birthdays.py:823` | A cache shorter than `member_count` is chunked before anybody is matched, so an import never reports "not found" against a half-filled cache. |
| `tests/cogs/community/test_birthdays.py:988` | Finding 9: the loop is not started when the database is late, and `on_ready` starts it once the database is there. |

## `tests/cogs/test_core.py`

| Key | Note |
|---|---|
| `tests/cogs/test_core.py:181` | The first test `cogs/core.py` has ever had, added for `/settings clear` (finding 10). It asserts the choice list stays inside Discord's 25 and that `birthday_color` is still reachable from `set-value` after its type changed from `text` to `color` — that type change is what would silently drop it out of the command. |
| `tests/cogs/test_core.py:76` | ⚠️ **This file is the one genuine ADD/ADD merge in the project so far, and its fakes are the merged pair.** Phase 5 created a `tests/cogs/test_core.py` on `main` for `/settings clear`; Phase 6 created a different one on its branch for the chunked `/settings show`; git could not merge two files that never shared an ancestor. The two sets of fakes were folded into one rather than kept side by side, and `FakeMember` is where they disagreed: Phase 5's default member was a **stranger** (no `manage_guild`), Phase 6's was **staff**. The merged one defaults to stranger and takes `manage_guild=True` explicitly, so Phase 5's four tests read unchanged and Phase 6's staff case says out loud what it is relying on. `FakeGuild` gained `name`/`default_role` from Phase 6 and kept `add()`/`members` from Phase 5; `FakeInteraction` gained `followup` (`cogs/core.py:160` sends every chunk after the first through it) and kept the `sent` shorthand. |
| `tests/cogs/test_core.py:223` | The chunking test asserts `len(said) > 1` — that the registry is **already** past one message — so it is also a live check that `/settings show` has not silently gone back to a single 2000-character reply as keys were added. It asserts every chunk is ephemeral, because the first goes out through `response.send_message` and the rest through `followup.send`, which are two different code paths that could disagree. |


| `tests/cogs/test_core.py:440` | ⚠️ **The only test in the suite that builds the REAL bot and loads every cog**, because `/help` renders whatever the tree holds and a fake tree can only prove the renderer. It is what proves the `(staff)` marking survives one hop through a cog helper: `/warn` gates in `modcmds.py`'s `_ready`, not in its own body, and would be listed as if anyone could run it if the detection stopped at the command. Offline — no gateway, no token; `load_extension` and `bot.close()` are all it touches. |
| `tests/cogs/test_core.py:352` | The rendering is asserted as a whole list rather than by substring, so a change to the shape of a line — the bold heading, the em dash, the sort order, the `(staff)` suffix — fails here rather than in the owner's client. |

## `black_bloc/automod.py` — the rule engine, Phase 6 (F7)

> Added 2026-08-26 by the Phase 6 build, **re-keyed to `main` at the Phase 6
> merge**: these numbers were written against build commit `6437d9f` and were
> already stale by the time the branch tip was reached, because the two
> adversarial-review commits moved lines under them. Each one was re-mapped
> from `6437d9f` to this tree and checked against the construct it names. NOT
> verified: any of it running
> against live Discord — no message has ever been deleted and no member has ever
> been timed out by this code.

| Key | Note |
|---|---|
| `black_bloc/automod.py:13` | The rule names are an **ordered tuple, not a set**, because the order decides which verdict a burst produces first and therefore which case card the owner reads at the top of the modlog. Adding a rule = a name here, a row in `DEFAULT_RULES`, a noun pair in `RULE_NOUNS`, a line in `RULE_HELP` and a branch in `_tokens` — five places on purpose, so a half-added rule fails a test rather than silently never firing. |
| `black_bloc/automod.py:26` | A message shorter than eight letters can be 100% capitals by accident ("OK", "BRB", an emote name), so caps is not even asked below it. Without this the caps rule fires on "OK" the moment anybody arms it. |
| `black_bloc/automod.py:30` | ⚠️ **Measured, not invented: this IS Carl-bot's live config**, from the owner's `!am` dump (`../archive/current-bots/carl-bot-dashboard-2026-08-26.md`). Mention-spam 5/30s → delete + warn + 5-minute timeout is **the only rule Carl actually punishes on**; `slowmode` 6/4s and `linkspam` 1/1s are enabled but log only, exactly as Carl has them; the other four are present so the owner can arm them later and **off** because Carl never armed them. ⚠️ `linkspam` at 1 in 1s fires on **every single link**, which is what Carl is set to and therefore what parity has to reproduce — it is log-only, and `/automod rule disable linkspam` is the one command that quiets it. |
| `black_bloc/automod.py:148` | ⚠️ **In memory only, and lost on restart — a deliberate choice, not an oversight** (`phase6-design.md`, §Engine). A window is at most an hour wide, so the cost of a restart is that one burst in flight is forgiven; the cost of persisting it would be a database write per message. `prune` is called from `evaluate` on **every** message and walks every key, so the whole structure is bounded by the largest configured window whatever any single member does (checklist 5: nothing may grow forever). |
| `black_bloc/automod.py:227` | ⚠️ **The validator IS the schema.** `automod_rules` is the registry's only `json` key, and this is what stops `/automod rule set` or a hand-edited row putting a 40-day timeout (Discord's ceiling is 28) or an unknown punishment into the rule book — refused with a sentence, at the settings boundary, per checklist 22. An unknown *field* is refused too, which is what makes `/automod rule set mention_spam words …` say so instead of quietly storing a key nothing reads. |
| `black_bloc/automod.py:264` | The forgiving twin of `normalise_rule`: a rule book that somehow got broken on disk falls back to the **default** for that rule rather than raising, because this is called from inside `on_message` where a raise is invisible. Writes still go through the strict path at `:227`, so a bad book cannot be *created* here — only survived. |
| `black_bloc/automod.py:304` | Everything the engine is allowed to know, and nothing else. It duck-types the message rather than taking a `discord.Message` so the whole engine is testable with no gateway (`architecture.md`, rule 6) — and so a future source of facts (an edit, an attachment scan) can feed the same function. `created_at` is forced to UTC-aware because a naive timestamp compared against an aware one raises inside a listener. |
| `black_bloc/automod.py:332` | Word boundaries with a lookaround rather than `in`, because `"ass" in "classic"` is the oldest bad-words bug there is. Reference bots agree: Wick's banned-word list is documented as "no partial matches" (`reference-bots.md`). |
| `black_bloc/automod.py:381` | ⚠️ **`window_s <= 0` means "this message only"**, which is what makes caps and bad_words per-message rules without a second code path, and lets the owner turn any rule into a per-message one. `mention_spam` counts **distinct** tokens and everything else counts entries — that is the difference between "mentioned five people" and "mentioned one person five times", and Carl punishes only the first. The window boundary is `>=`, so exactly five in exactly thirty seconds fires and five spread over thirty-one does not; both are asserted in `tests/test_automod.py`. |
| `black_bloc/automod.py:431` | ⚠️ **A deliberate near-duplicate of `cogs/moderation/honeypot.py:110`, and it must not be "de-duplicated" by importing that one.** Cogs never import each other (`architecture.md`, rule 2), so the shared shape has to live in a plain module; this is that module. The correct fix is to point the honeypot at *this* function in a later pass, not to add a third copy. The **staff** set handed in always comes from `settings_store.py`'s one computed-permission home (checklist 21) — automod never derives its own. |

## `black_bloc/modcases.py` — the case store both moderation cogs share

> Added 2026-08-26 by the Phase 6 build, **re-keyed to `main` at the Phase 6
> merge** from build commit `6437d9f`, the same way as the section above.

| Key | Note |
|---|---|
| `black_bloc/modcases.py:15` | ⚠️ **This module is a deviation from `phase6-design.md`'s Shape block, and the reason is rule 2.** The design names only `automod.py` plus the two cogs, but `cogs/moderation/automod.py` and `cogs/moderation/modcmds.py` both need the `mod_cases` store, the case card, the duration parser, the DM policy and the modlog post — and cogs may not import each other. `architecture.md` prescribes exactly this: *"shared logic goes in a plain module the cogs both import"*. Keeping it in `automod.py` instead would have put `async` database calls inside the module the design calls **pure**. |
| `black_bloc/modcases.py:26` | Discord refuses to delete more than seven days of a banned account's messages, so eight is not clamped by the API — it is a 400 on every ban. Same fact as `settings_store.py`'s `HONEYPOT_PURGE_MAX_DAYS`; they are two callers of one Discord limit, and if a third appears they should collapse into one constant. |
| `black_bloc/modcases.py:83` | Reads durations the way Carl-bot's commands take them (`reference-bots.md`), so muscle memory survives the migration: `10m`, `2h`, `1d`, `1h30m`. A bare number means **minutes**, which is what Carl's dashboard fields mean. Returns `None` rather than a default for anything unreadable, because silently timing somebody out for a guessed length is worse than a sentence asking again. ⚠️ **A deliberate near-duplicate of `black_bloc/events.py:94`, and the two are NOT interchangeable** (checklist 15 asks about a constant with two homes; this is the documented exception). `events.parse_duration` returns **minutes**, reads only `h`/`m`, caps at a week and falls back to a **default** when the text is empty — it is answering "how long is this event". `modcases.parse_duration` returns **seconds**, reads `w`/`d`/`h`/`m`/`s` plus a bare number meaning minutes, has no default and no cap of its own (`clamp_timeout` does that) — it is answering "how long is this punishment". `DURATION_PATTERN`, `BAD_DURATION` and `describe_duration` are paired with them and differ the same way. Merging them would mean one of the two surfaces silently changing units; if they are ever unified it is a migration, not a refactor. |
| `black_bloc/modcases.py:112` | Clamps at the **act site** as well as at the validator (`black_bloc/automod.py:227`), for the same reason `do_ban` does (`cogs/moderation/honeypot.py:210`): a value written to the settings row before the validator existed is still on disk, and Discord's answer to 29 days is a 400, not a shorter timeout. |
| `black_bloc/modcases.py:120` | ⚠️ **One home for "nothing in a mod message may ping".** A modlog card carries a **reason typed by a moderator** and a **display name chosen by the person being punished** — checklist 11 says both are attacker-controlled surfaces, and a nickname containing `@everyone` must not ping the server from inside a ban notice. Every card, every DM and every command reply in the two moderation cogs goes through this or `discord.AllowedMentions.none()` directly. |
| `black_bloc/modcases.py:125` | Carl's own DM options, reproduced: `none`, server+action, server+action+reason (`../archive/current-bots/carl-bot-dashboard-2026-08-26.md`). A blank reason under `server_action_reason` produces the *same* sentence as `server_action` rather than a dangling "Reason:", and a kind nobody is told about (`purge`, `automod` in shadow) returns `None` so the caller does not have to know which is which. |
| `black_bloc/modcases.py:154` | The one card every mod surface shows — the modlog post, `/case`, and the automod verdict — so "what happened" cannot be described two different ways in two places. The **"Not done"** field is the whole shadow story in one line: a card with it is a would-do, a card without it happened. |
| `black_bloc/modcases.py:351` | Counts `warn` **and** `automod` rows, because Carl's warn threshold counts automod warnings too — that is what makes 8 the number it is on this server. Only `applied=1` rows count, so a shadow verdict nobody acted on never pushes anybody over the line. |
| `black_bloc/modcases.py:361` | `modlog_channel_id` falls back to `log_channel_id` at **read** time as well as in the registry default, so a guild that set a log channel and never heard of a modlog still gets its cases somewhere (`phase6-design.md`: *default = `log_channel_id`*). |
| `black_bloc/modcases.py:365` | ⚠️ **Asks the guard first rather than letting it raise from inside the HTTP layer** — same trick as `cogs/content/golive.py:540`. This runs from a message listener and from a command body alike; a `TestModeViolation` surfacing here would be a traceback in the listener and a dead command in the other. The broad `except` is deliberate for the same reason `actionlog.py:154`'s is: the punishment has **already happened** by the time the card is posted, and a modlog that will not take it must not undo it. |

## `black_bloc/cogs/moderation/automod.py` — F7, the engine wired to Discord

> Added 2026-08-26 by the Phase 6 build, **re-keyed to `main` at the Phase 6
> merge** from build commit `fa6f6e8`. This file grew by ~150 lines after that
> commit, so every key here had drifted; the numbers below are the mapped ones.
> NOT verified: anything against live Discord.

| Key | Note |
|---|---|
| `black_bloc/cogs/moderation/automod.py:59` | Checklist 23: system messages (thread created, pins, joins) carry the **member** as author, so without this filter a join notice would count towards someone's message rate. `default` and `reply` are the only two kinds a person actually typed. |
| `black_bloc/cogs/moderation/automod.py:60` | ⚠️ **A persistence key, matched by `discord.py` as a regex** — same mechanism as the honeypot's Ban-now button (`cogs/moderation/honeypot.py:32`) and the events cards (`cogs/community/events.py:73`). One `add_dynamic_items` call at `cog_load` revives every Apply-now button ever posted, with the case id carried in the `custom_id`. Change this string and every card already in the modlog goes dead with no error anywhere — the click just spins. |
| `black_bloc/cogs/moderation/automod.py:114` | ⚠️ **The per-member lock lives on the BOT**, for the same reason temp voice's and events' do (`cogs/community/tempvoice.py:270`): an Apply-now click arrives with an `interaction` and never with a cog, so the listener and the button have to be able to reach the *same* lock, and a module-level dict outlives the event loop that made it. This is the whole read-decide-write defence for automod (checklist 6) — there is no unique index to fall back on, because what is being raced is "has this member already been punished for this burst". |
| `black_bloc/cogs/moderation/automod.py:160` | ⚠️ **A timeout is a side effect `guard.py` cannot see** (it gates `send_message` and `edit_message` only), so the test policy is enforced here, by hand, exactly as `do_ban` does it. Owner rule: while `TEST_MODE` is on nothing is punished, it is logged as a would-do instead. Do not remove this when test mode is lifted — it is a no-op then (`bot.guard is None`). |
| `black_bloc/cogs/moderation/automod.py:176` | ⚠️ **The three outcomes never share a log kind** (checklist 2): done → `automod.deleted` / `automod.warned` / `automod.timed_out`, refused by the test policy → `automod.would_timeout`, refused by Discord → `automod.timeout_failed`. The owner's verification method is "read the log", so a dry run and a real failure must be tellable apart at a glance. It returns **both** lists because the caller needs "did anything happen" and "did anything fail" separately — a delete that worked beside a timeout Discord refused is not a finished punishment. |
| `black_bloc/cogs/moderation/automod.py:471` | ⚠️ **The place gate, and it is stricter than the honeypot's.** The honeypot allows the test channel's whole category (`cogs/moderation/honeypot.py:614`) because a trap channel has to be a different channel; automod has no such need, so while the guard is installed **the engine only ever sees the test channel itself** (owner rule for this phase). The consequence is deliberate: the shadow log is expected to be nearly empty until test mode is lifted, because automod has not been watching the rest of the server. |
| `black_bloc/cogs/moderation/automod.py:478` | ⚠️ **The order inside one verdict is the contract.** The case row is written **first**, so a crash between the row and the punishment leaves a record of a decision rather than a punishment nobody can explain; then the punishment; then `applied` is set true **only if something was done and nothing was refused**; then the card. That last condition is why an `on`-mode verdict whose timeout the test policy refused still gets an Apply-now button — the verdict is not finished, and the card says so. |
| `black_bloc/cogs/moderation/automod.py:532` | The **Apply now** button is only attached when the verdict actually has a punishment to apply. A rule Carl runs as log-only (`slowmode`, `linkspam`) has no actions, so a button would offer to do nothing; those verdicts get the row and one `automod.detected` line and no affordance. That is also what keeps a link-heavy hour from burying the mention-spam verdict the owner is actually testing. |
| `black_bloc/cogs/moderation/automod.py:698` | `/automod rule set` builds the whole rule object and hands it to `normalise_rule` rather than writing one field, so **one validator** decides what is acceptable however the change arrived (checklist 15). A field that does not belong to that rule — `words` on `mention_spam` — is refused by the same path, which is why there is no separate "is this field allowed here" check. |

## `black_bloc/cogs/moderation/modcmds.py` — F7, the mod commands

> Added 2026-08-26 by the Phase 6 build, **re-keyed to `main` at the Phase 6
> merge** from build commit `71626c5`. NOT verified: anything against live
> Discord — nobody has ever been kicked, banned or timed out by this code.

| Key | Note |
|---|---|
| `black_bloc/cogs/moderation/modcmds.py:49` | Every refusal names **what happened, what it needs and how to get it** (owner rule: a person never sees a bare status code). They are keyed by action because the permission differs — Moderate Members, Kick Members, Ban Members, Manage Messages — and a refusal that names the wrong permission sends somebody asking an admin for access they already have. The purge one also names Discord's 14-day bulk-delete floor, which is the most common cause and is not a permissions problem at all. |
| `black_bloc/cogs/moderation/modcmds.py:407` | ⚠️ **The owner's test policy for this phase in one predicate.** `guard.py` gates messages, not punishments, so timeout / kick / ban / purge check this explicitly and refuse. `/warn` is deliberately **not** gated — it only writes a row and sends a DM — and neither are `/untimeout` and `/unban`, which *lift* a punishment rather than making one. ⚠️ That last pair is worth knowing before test mode is lifted: they are the two commands that can change the live server while the policy is on. |
| `black_bloc/cogs/moderation/modcmds.py:422` | A refused command still writes its case, with `applied=0` and `mode='test_mode'`, and logs `mod.would_<action>` — so the owner's verification method ("read the log, read `/cases`") shows the whole intent, not a gap. `deferred` exists because `/purge` has already deferred by the time it gets here and an interaction that has been deferred can only take a `followup` (`command_errors.py:65`). |
| `black_bloc/cogs/moderation/modcmds.py:455` | The DM is sent **before** the row is written, and the row before the reply: the member is told by the thing that is about to be recorded, and a failed reply cannot take a real warning with it (checklist 12). `dm_member` swallows a closed DM, so a member with DMs off is still warned. |
| `black_bloc/cogs/moderation/modcmds.py:471` | ⚠️ Over 28 days is **refused with a sentence rather than silently clamped**, because somebody typing `30d` is asking for something Discord cannot do and needs to be told to ban instead; the clamp at `modcases.py:112` is the belt underneath that brace, for values that arrive from anywhere else. The audit reason names the moderator, so Discord's own audit log says who did it even though the row here is the record of truth. |
| `black_bloc/cogs/moderation/modcmds.py:542` | `delete_message_seconds`, not the deprecated `delete_message_days` (checklist 22), and the window is clamped to 0–7 days at the call. The DM goes out **before** the ban for the obvious reason: a banned account cannot be DMed by a bot that no longer shares a server with it. |
| `black_bloc/cogs/moderation/modcmds.py:593` | ⚠️ **Defers before it deletes** (checklist 24). A bulk delete of a hundred messages is well outside the three-second interaction window, and a purge that worked but missed the deadline shows the moderator "the application did not respond" — with no way to tell whether it happened. The count is bounded at 100 because that is Discord's own bulk-delete limit, and the refusal says so rather than reporting an API error. |
| `black_bloc/cogs/moderation/modcmds.py:689` | ⚠️ **Pagination is a `page` argument, not buttons — a deliberate, smaller deviation from `phase6-design.md`.** A paging *view* is a persistent component with a `custom_id` that has to survive restarts (`cogs/community/role_menus.py:134`), and this reply is **ephemeral**: nobody else can see it, it cannot be revived after a restart, and a dead button in an ephemeral message is exactly the failure the persistence machinery exists to prevent. The reply names the next page's command, so paging is one click of the command picker. |
| `black_bloc/cogs/moderation/modcmds.py:723` | The audit reason handed to Discord always names the moderator, because Discord attributes the action to **Black Bloc** in the server's own audit log. Without this the server's audit log says the bot banned somebody and gives no way to find out who asked it to. |

## `black_bloc/api/auth.py` — Phase 8a, who may see the site

> Added 2026-08-26 by the Phase 8a build (branch
> `worktree-agent-ae8cc520aba4406d0`, commit `930248d`), then **rewritten the
> same day by the security-review fixes** (`c211715`, `50205dd`), then **merged
> into `main`** the same day. **Line numbers below are `main`'s after the
> merge**, re-read off the file then; `auth.py` merged with no conflict and no
> edit, so they are also `50205dd`'s.
> ⚠️ **NOT verified: a real OAuth round-trip.** Nobody has ever signed in
> through this code against live Discord — every test mocks the exchange. Nor
> has any of it been seen in a browser: `__Host-`, the CSP and HSTS are
> asserted against an in-process ASGI client, which is not a browser.

### ⚠️ Two notes below were WRONG in the build's own addendum

Each described a safety property the code did not have. Called out here
because a wrong note is worse than no note; both are corrected in place.

1. **`auth.py:170` said staff was "re-checked on EVERY request".** It was
   re-checked, and then **failed OPEN**: an uncached member fell back to the
   cookie's own `staff` flag. The gateway does not cache every member, so a
   demoted mod holding a cookie that says `staff: true` kept the dashboard for
   seven days — the exact failure the note claimed was fixed. The guild's
   answer now wins whenever the guild can answer at all, and "cannot answer"
   became its own visible state rather than a silent yes.
2. **`auth.py:225` called `SameSite=Lax` across two hostnames a known
   constraint** and moved on. It was not a constraint to live with — it was a
   sign-in that could never have worked in production, written down and
   shipped. Option A (one hostname) removes it; see `access/site.md`.

| Key | Note |
|---|---|
| `black_bloc/api/auth.py:23` | Exactly two scopes, and `guilds.members.read` is the load-bearing one: `identify` says *who* you are, and only the member read says what roles you hold **in this guild**. That is the question the site exists to answer (`phase8-design.md`), and it is why the login is Discord's and not the estate's — mods do not have estate accounts. Asking for more scopes than these two is a consent screen nobody should have to accept to read a status page. |
| `black_bloc/api/auth.py:26` | ⚠️ **`__Host-` is a prefix with three conditions attached**, and the browser is the thing that enforces them: `Secure`, `Path=/`, and **no `Domain`**. In exchange, a sibling host on `heygabi.ai` cannot set a cookie by this name that our app would then read. It is a name, not a setting — so a deployment whose `SITE_ORIGIN` is `http://` produces cookies every browser silently drops, which on screen looks exactly like "signing in does nothing". `access/site.md` carries that symptom. Deletions pass the same attributes, because a `delete_cookie` that fails the prefix rules is ignored too. |
| `black_bloc/api/auth.py:34` | ⚠️ **The causes get one sentence each, and the API owns all but one so the wording has ONE home.** Not signed in / not staff / expired / **roles could not be checked** / secrets not set. `site/public/assets/app.js` owns only the outage sentence, because a dead API cannot describe itself. The global rule this serves is that nobody ever sees a bare HTTP status — and the harder half of it: **a fault is never described as a permission problem**, because mislabelling one sends people asking for access they already have. |
| `black_bloc/api/auth.py:47` | ⚠️ **`STAFF_UNKNOWN` is the fifth state and the whole point of finding F7.** "We asked Discord and you are not staff" and "we could not ask" are opposite facts, and the old code rendered the second as the first. A real mod was told to go and ask a Lead for a role they already held, during what was actually a Discord outage. It answers **503**, not 403, so `permission-ux.js` classes it as a fault and the page offers a retry rather than a sign-in. |
| `black_bloc/api/auth.py:73` | Ten sign-in attempts a minute per client IP. The point is not brute force — there is no password — it is that `/callback` spends a Discord code and `/login` mints state, so an unbounded loop is free work aimed at Discord's rate limits and at our own memory. The sentence never says "blocked": it says wait a minute, because the caller is usually a person double-clicking. |
| `black_bloc/api/auth.py:87` | A refusal is its own exception, not `HTTPException`, because FastAPI renders `HTTPException` as `{"detail": …}` and the site's contract is `{"error": …, "message": …}`. One handler at `:97` renders every refusal the same way, so no route can invent its own error shape. |
| `black_bloc/api/auth.py:101` | ⚠️ **FastAPI's own validation error is a LIST of objects in `detail`.** Rendered by a page that expects a string it becomes `[object Object]`, which is a bare status wearing a hat. This handler turns every malformed query string into one sentence; `permission-ux.js` was hardened at the same time to take `detail` only when it is a string, because belt-and-braces is cheap and either one alone is a single edit from regressing. |
| `black_bloc/api/auth.py:114` | Signed with `hmac` + `hashlib` and nothing else — the design named itsdangerous, and adding a dependency for forty lines of HMAC is not worth the supply chain. `sort_keys` and the compact separators make the signed body byte-stable, which is what makes the MAC reproducible. |
| `black_bloc/api/auth.py:121` | ⚠️ **Expiry and forgery are different answers on purpose.** `('expired', …)` becomes `session_expired` and `('invalid', …)` becomes `not_signed_in`, because "your seven days ran out" and "that cookie is not ours" are different sentences to a person. A payload with no readable `exp` is `invalid`, not `expired`: a session that never expires is the failure mode that matters. ⚠️ **Both halves are encoded to bytes before `compare_digest`**, and a cookie that will not encode as ASCII is `invalid` rather than a 500: `str.encode("ascii")` raised on any non-ASCII cookie value, and `compare_digest` on two `str`s raises `TypeError` for the same reason. Anyone could send that cookie. |
| `black_bloc/api/auth.py:149` | The one guild the site is about. `DEV_GUILD_ID` first — it is already the guild the slash commands sync to, so there is no second setting for "which server". The single-guild fallback is a convenience; **two guilds and no `DEV_GUILD_ID` returns `None` rather than guessing**, and `None` now means *unknown*, not *no*. |
| `black_bloc/api/auth.py:170` | ⚠️ **The staff rule has ONE home and this is not it — this function calls into it.** The cached member goes straight to `SettingsStore.is_staff`, which is the same predicate `require_staff` uses for slash commands, which is the same `resolved_staff_roles` computed-permission derivation (checklist 21). The site and the commands therefore cannot disagree about who is staff. The role-id fallback below it re-derives `manage_guild` from the guild's own role objects rather than trusting anything the OAuth payload claimed — it runs at **sign-in**, where the OAuth member read is the only evidence there is. |
| `black_bloc/api/auth.py:190` | ⚠️ **This is finding F2, and it used to fail OPEN.** Three answers now, not two: the guild answered yes, the guild answered no, or the guild could not be asked. With the bot ready and the guild cached, **a member the cache has never seen is NOT staff** — the cookie's flag no longer overrules a guild that answered, which is what made a demotion take effect only when the cookie expired. The recorded flag survives for exactly one case: nobody to ask. That case returns `known=False` and becomes `STAFF_UNKNOWN` at `:248`, never `NOT_STAFF`. Asserted by `test_a_member_the_guild_has_never_heard_of_is_not_staff` and `test_a_guild_that_cannot_be_consulted_is_unknown_not_a_refusal`. |
| `black_bloc/api/auth.py:273` | `SameSite=Lax` — and under Option A that is simply correct rather than a compromise. Lax rides the top-level navigation back from Discord, which is what the state cookie needs, and there is no cross-site `fetch` left to break because the page and the API are one origin (`access/site.md`). `Secure` is derived from `SITE_ORIGIN`'s scheme rather than configured, so it cannot be got wrong by hand — and it is **load-bearing twice**, since `__Host-` requires it. |
| `black_bloc/api/auth.py:282` | The HTTP layer is injectable exactly like `twitch.py:93`, for the same reason: **every test stays offline.** Transport errors become `OAuthError` at the boundary (checklist 7) with an explicit `ClientTimeout`, so callers catch one type. Nothing here ever logs a code, a token or the client secret — the log lines carry a status and a user id and stop. |
| `black_bloc/api/auth.py:353` | ⚠️ **`Fly-Client-IP` first, and only then `X-Forwarded-For`.** Fly's proxy sets the first and a caller can write the second, so keying a rate limit on `X-Forwarded-For` alone hands every attacker an unlimited supply of buckets. `uvicorn` also runs with `forwarded_allow_ips="*"` (`server.py:174`), which is safe **only because Fly's proxy is the single ingress** — the machine takes no other traffic. If that ever stops being true, this is the line that becomes a lie. |
| `black_bloc/api/auth.py:362` | A token bucket rather than a fixed window, because a fixed window lets twice the limit through across a boundary. It refills continuously and prunes stale keys past a cap, so a burst of forged IPs cannot grow the dict without bound — the same "the dict is pruned on use, never swept" shape as the modmail refusal cooldown (`cogs/moderation/modmail.py:68`). |
| `black_bloc/api/auth.py:381` | ⚠️ **`hmac.compare_digest` on two `str`s raises `TypeError` if either holds a non-ASCII character**, and `state` comes straight off the query string. A 500 on a hostile query string is a bug, and one on the *callback* is a bug on the security-critical path — so a state that cannot be compared is a mismatch, which is the safe answer. |
| `black_bloc/api/auth.py:440` | Three things about the callback. First, the order is the security: the state is checked **before** the code is spent, so a forged callback never reaches Discord at all (`test_a_bad_state_never_reaches_discord` asserts zero calls), and a rejected state is **cleared** rather than left for a replay. Second, it answers with a **redirect back to the site**, never JSON — a person is looking at this URL in their address bar, and a JSON error body on screen is the bare-status failure in another costume. Third, ⚠️ **a failed member lookup no longer fails the whole sign-in**: a Discord 5xx there is not evidence about anybody's roles, so they are signed in with `staff: false` recorded and the live check at `:190` decides afterwards — which resolves either to the truth or to `STAFF_UNKNOWN`. |
| `black_bloc/api/auth.py:477` | ⚠️ **Someone who is not staff is still SIGNED IN, deliberately.** Refusing them a cookie would collapse "not signed in" and "signed in but not staff" into one indistinguishable state, and those are two of the sentences the whole permission-UX rule exists to keep apart. It also lets the page greet them by name while explaining what to ask a Lead for. |

## `black_bloc/api/status.py` and `server.py` — Phase 8a, the read-only view

> Added 2026-08-26 by the Phase 8a build, commit `930248d`; **line numbers are
> `main`'s after the Phase 8a merge**, re-read off the file then — ⚠️ they are
> NOT `50205dd`'s: the merge added the modmail import and rewrote `_health`, so
> everything below line 13 moved. ⚠️ NOT verified against a live bot: no figure
> this file produces has ever been read out of a running gateway connection.

| Key | Note |
|---|---|
| `black_bloc/api/status.py:20` | ⚠️ **A read-only page must not borrow a write-shaped sentence** (finding F12). `settings_store.DB_UNAVAILABLE` says "nothing was changed", which is true of a slash command and a lie on a page that only reads — and a person told nothing was changed reasonably assumes they broke something. One problem, two audiences, two sentences; each has one home. |
| `black_bloc/api/status.py:111` | ⚠️ **`round(float("nan"))` raises `ValueError`** and `discord.py` reports `nan` latency until the first heartbeat lands — so a status page whose whole job is to survive a sick bot would 500 exactly when it mattered. `None` means "not measured", which is what the page already renders for every other missing figure. It lives here, and `/health` calls it, so the two cannot disagree. |
| `black_bloc/api/status.py:140` | The feature list is **derived from `settings_store.KEY_TYPES`**, not written down here. A feature that adds a `*_mode` key appears on the status page with no edit to this file and none to the site — which is the only way "every feature's mode" stays true as features land. ⚠️ **The merge proved it and caught the one place it was NOT true.** 8a was built off `d9d086a`, before Phases 5–7 merged; the moment they did, `mode_keys()` went from four keys to **seven** (`golive`, `tempvoice`, `honeypot`, `events`, `birthday`, `modmail`, `automod`) with no code edit — and the only thing that broke was a *test* that had written the four out longhand. That test now asserts against `KEY_TYPES` itself, plus a `>=` on the seven known today, so a hard-coded list cannot creep back in. |
| `black_bloc/api/status.py:155` | ⚠️ **The cog is the only home of its own health-attribute names, so the page ASKS it — it does not guess.** Fixed at the Phase 8a merge, and it was a real break, not a tidy-up: the 8a code walked `getattr(loop, field)` → `getattr(cog, f"{name}_{field}")` → `getattr(cog, field)`, and against the cogs that actually exist on `main` that found **nothing for `golive` and `birthdays`** (their attributes are `last_poll_ok_at` / `last_poll_error` and `last_run_at`) and, worse, found `Events.last_error` — which is a **dict keyed by loop name**, so a healthy Events loop would have rendered its last error as `{'golive': None, 'reconcile': None}`, a non-empty and therefore truthy dict. The contract is now one method, `cog.loop_health(name) -> (last_ok_at, last_error)`, implemented on `cogs/content/golive.py`, `cogs/community/events.py`, `cogs/community/birthdays.py` and `cogs/moderation/modmail.py`. A cog that does not implement it reports blanks, which is the honest answer. |
| `black_bloc/api/status.py:168` | ⚠️ **Loops are DISCOVERED, not declared** (2026-08-27, closing KI-7). The old reader asked every cog for `get_tasks()` — a method `commands.Cog` does not have (measured: `hasattr(commands.Cog, "get_tasks")` is `False` in discord.py 2.7.1) and only `cogs/presence.py` defined, so the Health tab listed **one** loop out of seven and the other five cogs' `loop_health` readers were never called. `_loops` walks each cog's class MRO dicts **and** its instance dict for `discord.ext.tasks.Loop` instances and `getattr`s only those names — so `dir(cog)` never runs, and the property-that-raises hazard the old note named is still avoided while the declaration is gone. Names come from the attribute, which every cog's `loop_health` already accepted, so **no mapping table was needed**: `status`, `poller`, `_sweep`, `_golive_loop`, `_reconcile_loop`. Dedupe is by `id(loop)` because `Loop.__get__` caches its bound copy on the instance under the **coro** name — identical to the class attribute name everywhere here, but not guaranteed to be. ⚠️ The residual is that a loop `getattr` cannot reach (held in a list or dict) is invisible; nothing does that today. |
| `black_bloc/api/status.py:214` | ⚠️ **Returns `None`, never zeroes, when the database cannot answer** (checklist 10). "No honeypot hits this week" and "we could not look" are opposite facts, and rendering the second as the first is how a status page becomes worse than no status page. |
| `black_bloc/api/status.py:265` | `open_modmail` was **added at the merge**, because 8a was built off `d9d086a` and `modmail_tickets` did not exist yet — `phase8-design.md` names "open modmail count" as one of the four things 8a shows, and it was the one missing. The open state is `modmail.OPEN`, imported rather than the literal `'open'`, so this query and the partial unique index that enforces one open ticket per member cannot drift apart. ⚠️ Unlike the other counts this one is a **table that only exists on `main`**: any further count added here must be checked against `storage/db.py` on `main`, not against the branch it was written on. |
| `black_bloc/api/status.py:379` | ⚠️ **`details` is withheld unless `?details=1` asks** (finding F13). It is a free-form JSON blob written by every feature, so what it holds is whatever the newest feature decided to put there — a default-deny projection is the only version of this that stays safe as features land (the estate's export rule, applied to a row). The page never asks; nothing renders it. |
| `black_bloc/api/status.py:405` | The staff gate is a **router-level dependency**, so a route added to this file later is behind it whether or not whoever adds it remembers. `/health` stays public because it lives on the app, not on this router — and under Option A that matters more than it did, because ⚠️ **this API is now on the public internet under the site's own hostname**. |
| `black_bloc/api/server.py:36` | ⚠️ **The CSP is only free because the page earned it.** `theme.js`, `motion.js`, `app.js` and `permission-ux.js` were read for this: no inline `<script>`, no `style=` attribute, no `eval`, no `new Function`, no third-party host, fonts local. So `script-src 'self'` with **no** `unsafe-inline` costs nothing today — and a future edit that needs it will break loudly in the console rather than quietly widening the policy. `form-action 'none'` is deliberate on a page with no forms; `frame-ancestors 'none'` is the clickjacking half. HSTS is a year, and Fly already forces https at the proxy. |
| `black_bloc/api/server.py:121` | ⚠️ **uvicorn's access log prints the whole request line, query string and all** — so every sign-in wrote the OAuth `code` to the log (finding F5). One-time codes in a log file are still credentials in a log file. uvicorn's own access log is off (`:173`) and this logs method, path and status; `request.url.path` carries no query by construction, so the fix cannot be undone by forgetting. |
| `black_bloc/api/server.py:156` | ⚠️ **Mounted at `/` and mounted LAST.** Starlette matches routes in order, so the API routers and `/health` are registered first and win; everything else is a file. `html=True` makes `/` serve `index.html`. A missing directory logs and leaves the API running rather than refusing to start — the bot is the product and the page is not worth taking it down for. `SITE_ROOT` resolves against the working directory (`/app` in the image, the repo root locally), which is why the Dockerfile copies `site/public` in. |
| `black_bloc/bot.py:56` | Uptime has to come from somewhere and the bot recorded no start time. This is **process start, not gateway login**, which is the honest number for "how long has this deployment been up": a reconnect does not reset it, a restart does. |
| `black_bloc/config.py:61` | ⚠️ **ONE hostname (owner decision "Option A", 2026-08-26).** `SITE_ORIGIN` is where the page is served, where sign-in returns to, the base of the OAuth redirect URI, and whether the cookies get `Secure`. There is no `API_ORIGIN` any more, and an `API_ORIGIN` environment variable is **not read** — delete it wherever it is set. ⚠️ **The `settings.api_origin` compatibility alias was REMOVED at the merge**, not kept for a release: nothing in the tree read it, and a second name for one fact is checklist item 15 (the dead `MODES` vs `GOLIVE_MODES` finding, again). Use `settings.origin` (`:115`), which is `SITE_ORIGIN` with any trailing slash stripped. `.env.example` was corrected at the same time — it still documented `API_ORIGIN=https://black-bloc.fly.dev`, which would have had the deploy register the **wrong** OAuth redirect URI. Moving to the org's own domain is this value plus a DNS record plus the Discord redirect registration, and nothing else. |

## `tests/api/test_status.py` — the loop-discovery tests (2026-08-27, KI-7)

| Key | Note |
|---|---|
| `tests/api/test_status.py:32` | ⚠️ **`FakeLoop` subclasses the REAL `discord.ext.tasks.Loop`**, because `api/status.py:122` finds loops by `isinstance` now — a duck-typed double would simply not be found, and the test would pass by describing a page that lists nothing. The `_running` / `_broke` flags are **class-level defaults** and are set again after `super().__init__`: `Loop.__init__` calls `change_interval`, which calls `is_running()`, so an override that reads an attribute the constructor has not written yet raises inside the constructor. `next_iteration` is overridden as a property because the real one returns `None` for a loop that was never started. |
| `tests/api/test_status.py:63` | `FakeCog` hangs its loops off the **instance**, which is the other half of discovery: `_loops` walks the class MRO dicts *and* `cog.__dict__`, so this cog proves the instance path and the real cogs below prove the class path. |
| `tests/api/test_status.py:321` | ⚠️ **One row per real cog, and the row is the whole contract.** Each entry builds the actual cog class with the fake bot, records a success the way that cog records one (`last_poll_ok_at`, `last_run_at`, a dict entry, a plain string), and the test asserts every loop it owns comes back from `/api/status` with that `last_ok_at` beside it. A cog that grows a loop is one row here; a cog whose `loop_health` stops recognising its own attribute name fails here rather than rendering a blank dashboard row. `running` is `False` and `state` is `danger` on purpose — nothing starts a loop in an offline test, and the honest report of a loop that is not running is `danger`. |

## `site/` — Phase 8a, the status page the API serves

> Added 2026-08-26 by the Phase 8a build and reshaped by the review. This is
> not `path:line` material — `site/README.md` is the front door — but these
> decisions belong somewhere a future session will find them.

| Key | Note |
|---|---|
| `site/public/assets/*` (the five estate files + fonts) | ⚠️ **A SNAPSHOT, not a link** (owner decision 2026-08-26). Black Bloc's site shares a *domain* with heygabi and nothing else: no `estate-auth.js`, no auth worker, no estate status endpoints, no sync script, no shared deploy, no runtime dependency in either direction. `estate-themes.md` §3a's mechanical theme propagation is **withdrawn for this site** — a sixth estate theme arrives only if somebody copies `estate-theme.css` and `theme.js` in again. ⚠️ `permission-ux.js` is **no longer verbatim**: it carries one hunk marked `BLACK BLOC EDIT` (a non-string `detail` is not a sentence). Keep the marker, so a future re-copy is a three-line reapply rather than a diff nobody can read. |
| `site/public/index.html` `<meta name="api-origin">` | ⚠️ **Empty now, and empty MEANS "the origin this page came from".** Under Option A the same app serves both halves, so there is nothing to point at; filling it in is how you aim the page at a different deployment, and it is still the only place that is written down. The old note here said this tag and `SITE_ORIGIN` had to agree or CORS would block every call — there is no CORS any more, and no second origin to disagree with. |
| `site/public/assets/app.js` `COUNT_LABELS` | ⚠️ **The one place the page and the API have to agree, and the merge moved it.** `renderHealth` walks `COUNT_LABELS`, not `status.open`, so a count the API starts returning is **invisible** until a label is added here — that is deliberate (the page decides its own wording and its own order), but it means `open_counts` in `black_bloc/api/status.py:222` and this object are a matched pair. `open_modmail` was added to both at the Phase 8a merge. Adding a count with no label hides a real figure; a label with no count used to render the badge `undefined`, which is a bare status wearing a hat — the `key in status.open` guard added at the merge now skips it instead, so an older API and a newer page degrade to a shorter list rather than to nonsense. |
| `site/public/assets/app.js` | The signed-out, not-staff, expired and roles-unknown sentences come **from the API**; only the outage sentence is written here, because a dead API cannot describe itself. The theme dropdown is left EMPTY in the markup on purpose — `theme.js` fills it from its own registry, and a hardcoded `<option>` list here would be a second registry that goes stale. ⚠️ **Two timing fixes from finding F10:** the gate is shown **before the first `await`**, so a slow API shows "Checking…" rather than a blank page, and every `fetch` carries a ten-second `AbortController` — a bot that accepts the connection and never answers is indistinguishable from a page that is simply still loading, and the second one has no retry button. |
| `site/public/favicon.ico` | ⚠️ **Written by hand, in bytes, on purpose** (2026-08-27; the log was a `GET /favicon.ico 404` on every page load). Pillow is not in this venv, and an icon produced by a build step is an icon that is missing after the next clean checkout — so the file is a plain 32×32 ICO: one `ICONDIR`, one `ICONDIRENTRY`, a 40-byte `BITMAPINFOHEADER` whose height is **doubled** (Discord's format quirk is everyone's: the field counts the XOR image *and* the AND mask), bottom-up BGRA rows, and an all-zero mask because every pixel is opaque. The glyph is a blocky **B** in the cyberpunk accent. `img-src 'self'` already covered it, so the CSP (`black_bloc/api/server.py:176`) needed no widening, and both `StaticFiles` and `site/mock/server.mjs`'s `.ico` type already served it. ⚠️ The `<link rel="icon">` is on **all thirteen** pages and `tests/api/test_server.py` asserts that plus a real ICO at the route — a page added later without it silently brings the 404 back, which is exactly how this one arrived. |
| `site/public/assets/site.css` `[data-state="info"]` | The fifth state gets the neutral/info dot, never `warn` (which reads as *you* did something) and never `danger` (which reads as *the bot is broken*). "We could not check your roles" is neither, and colour is the first thing a person reads. |

# Phase 7 — modmail (F11), added 2026-08-26

> Built on the branch `worktree-agent-aa864ba565244e0af`, beside Phases 5 and 6
> rather than after them: the build (`b111a7f`, `0d7500c`, `c4e4777`) and then
> the adversarial-review fixes (`669440f`, `2cc9c02`). New files:
> `black_bloc/modmail.py`, `black_bloc/cogs/moderation/modmail.py`,
> `tests/test_modmail.py`, `tests/cogs/moderation/test_modmail.py`. Edited, by
> APPENDING only so the branches merge cleanly: `settings_store.py` (five
> `MODMAIL_*` constants and five `modmail_*` keys at the end of `KEY_TYPES` /
> `KEY_CHOICES` / `KEY_HELP`, four branches at the end of
> `SettingsStore.default`), `storage/db.py` (`SCHEMA_VERSION` 8, four tables,
> two indexes and one `ADDED_COLUMNS` entry), `bot.py` (one `COGS` entry at the
> end), `tests/storage/test_db.py`, `tests/test_settings_store.py`. **MERGED
> into `main` 2026-08-26 as `--no-ff`; the line numbers below are now `main`'s,
> not the branch's.** The two new source files and the two new test files landed
> unchanged, so their keys did not move; what DID move are this section's
> cross-references **out** into `cogs/community/events.py`,
> `cogs/community/tempvoice.py` and `cogs/moderation/honeypot.py` — the branch
> was cut from `d9d086a`, before Phase 5, and `events.py` alone had shifted by
> **246 lines** by the time it merged. Every one of them was re-mapped and
> re-checked against the file it points at. ⚠️ The five conflicts were all the
> same append-on-both-sides shape and were resolved by keeping **both** sides:
> `bot.py` (COGS), `settings_store.py` (three registry tails plus the `default`
> chain), `storage/db.py` (`SCHEMA_VERSION` → 8, both phases' tables, all three
> `ADDED_COLUMNS` entries), and the two shared test files.
>
> ⚠️ **`SCHEMA_VERSION` goes 5 → 8, skipping 6 and 7 on purpose: those are
> Phase 5's and Phase 6's, built in parallel.** Phase 5 has since merged, so the
> file on disk now genuinely passes through 6; **7 is still Phase 6's and has
> never run here.** Every bump is an additive
> `CREATE TABLE IF NOT EXISTS` plus one `ALTER TABLE` through the existing
> `ADDED_COLUMNS` / PRAGMA pattern, so the number is a label, not a migration,
> and any merge order produces the same database. The review's
> `modmail_messages.delivered` column deliberately did **not** bump it further,
> for the same reason.
>
> NOT verified: anything against live Discord. No DM has ever been relayed by
> this code, no ticket channel or private thread has ever been created by it,
> no transcript has ever been uploaded, and `modmail_enabled` defaults **false**
> so the incumbent ModMail bot keeps the inbox until the owner flips it.

## ⚠️ Two notes below were WRONG in the build's own addendum

Both were caught by the adversarial review and are corrected in place in the
tables. They are called out here because a wrong note is worse than no note —
each one described a safety property the code did not have:

1. **`black_bloc/modmail.py:31` (now `:32`, `TRANSCRIPT_BYTES`) said the
   truncation kept a transcript under Discord's upload cap.** It clamped
   **characters** (`text[:7_000_000]`) while the cap is on **bytes**, so a
   transcript of non-ASCII text — the common case, this server's members type
   emoji — could be up to four times the limit and the upload would fail inside
   the close path, exactly where the old note claimed it could not. `clamp_bytes`
   (`:79`) now cuts on the encoded bytes, decodes with `errors="ignore"` so a
   split multi-byte character cannot raise, and appends a visible marker.
2. **`black_bloc/modmail.py:126` (now `:165`, `relay_embed`) said the anonymous
   branch drops the footer as well as the author name.** It did — and then set
   the embed's **colour from the staffer's top role anyway**, which on a server
   whose Leads have distinct role colours names them as surely as the footer
   did. The note's own logic ("a footer reading `Mod Meg · 12` on an anonymous
   reply is worse than no anonymity at all, because staff would believe it had
   worked") applied to the colour and nobody noticed. Both the caller
   (`cogs/moderation/modmail.py:1056`, `_send_reply`) and `relay_embed` itself now
   refuse a colour on an anonymous reply — belt and braces, because either one
   alone is a single edit away from leaking again.

## `black_bloc/modmail.py` — the decisions, with no Discord in them

| Key | Note |
|---|---|
| `black_bloc/modmail.py:23` | ⚠️ **`=` is the incumbent's convention, kept on purpose** (`docs/archive/current-bots/discord-scan-2026-08-26.md`, ModMail category): staff already type `=note`, and muscle memory is the whole reason not to invent a new prefix. It is checked after `lstrip()`, because a leading space is a typo and not a decision to broadcast a private note to the member. |
| `black_bloc/modmail.py:32` | ⚠️ **BYTES, not characters — see the correction above.** Discord refuses an attachment over its size cap and `discord.py` surfaces that as a send-time error *inside the close path*, after the ticket has already been read and the row has already been closed. Truncating means a monstrous ticket files a slightly short transcript instead of filing none. |
| `black_bloc/modmail.py:45` | ⚠️ **Our own topic, deliberately NOT the incumbent's.** ModMail writes `ModMail Channel <user-id> <channel-id> (Please do not change this)`; if Black Bloc wrote the same string the two bots would each treat the other's channels as their own during the changeover, with five live tickets in the middle. `parse_topic` (`:99`) is its exact inverse, and is what lets a ticket channel be identified from Discord alone when the DB row is in doubt. |
| `black_bloc/modmail.py:54` | Discord refuses a message over 2000 characters and `/modmail status`, `/modmail blocked` and `/snippet list` all grow without limit. The cut is 1900 so the ephemeral answer has room for what the caller sees around it; the alternative — one long message that Discord rejects — is a staff command that works until the day it silently does not. |
| `black_bloc/modmail.py:70` | Reads one column off a row that may predate it. `sqlite3.Row` raises `IndexError` for a column that does not exist and a plain dict raises `KeyError`, and the transcript renderer is fed both (rows from SQLite in the cog, dicts in the tests). A missing `delivered` column must read as **delivered**, not as False — an old row is not evidence of a failed DM. |
| `black_bloc/modmail.py:79` | The byte-safe cut. `errors="ignore"` is the point: slicing UTF-8 mid-character is not an edge case at 7 MB, it is the normal case, and a `UnicodeDecodeError` here would lose the whole transcript to save half a character. The marker is visible on purpose (checklist 10) — a transcript that was cut and does not say so is a record that lies by omission. |
| `black_bloc/modmail.py:139` | Attachments are stored as a JSON list of **URLs** and never re-uploaded. Discord's CDN already hosts the file; re-uploading would double the storage, break on anything over the size cap, and turn a relay into a bandwidth bill. An unreadable blob returns `[]` rather than raising — a transcript with one missing link still has to render. ⚠️ The trade-off is that the links **expire**, which is why the transcript header says so (`:258`); a KNOWN_ISSUES entry carries the detail. |
| `black_bloc/modmail.py:155` | ⚠️ **Every relay is attacker text.** A member types the DM and a staffer types the reply; both reach a channel or another person's DMs. Only role ids passed in explicitly may ping, and the ONLY caller that passes any is the thread invite (`:351`), once, when the thread is created. Read `tests/test_modmail.py:168` before touching this. |
| `black_bloc/modmail.py:165` | One function for all three directions, because the difference between them is a title, a colour and whether the author is named. Three functions would have been three places to forget `anonymous`. ⚠️ **`hidden` is computed once and gates the name, the footer AND the colour** — see the correction above; the colour was the leak, and computing the three from one flag is what stops the next one. |
| `black_bloc/modmail.py:243` | Chronological, one line per message, notes labelled `NOTE`, anonymous replies marked, and an OUT row that never reached the member marked `(not delivered)`. An unreadable timestamp is **printed as stored** rather than dropped: the transcript is the record of last resort, and a row it silently omits is a row nobody will ever know existed. |
| `black_bloc/modmail.py:258` | The header block exists so a transcript read a year later still says which server, which member and why it closed, with nothing else to look at. Its counts come from `count_directions`, the same call the summary embed makes, so the file and the embed cannot disagree — one fact, one home. The attachment-expiry line is in the header rather than beside each link because it is a fact about all of them. |

## `black_bloc/cogs/moderation/modmail.py` — F11

| Key | Note |
|---|---|
| `black_bloc/cogs/moderation/modmail.py:68` | The refusal cooldown. ⚠️ **Four different DMs tell somebody their message did not get through** (modmail off, blocked, no shared guild, could not open) and every one of them answers a message the bot did not ask for. Without a per-member cooldown, anything that DMs in a loop — another bot, a script, somebody spamming — gets an answer every time, which is a flood the bot itself is sending. The dict is pruned on each use rather than swept, so it cannot grow. |
| `black_bloc/cogs/moderation/modmail.py:69` | ⚠️ **Two consecutive misses before an irreversible close** (checklist 32). One failed lookup is not evidence a channel was deleted, and closing files a transcript and deletes a channel. The loop runs every five minutes, so two strikes is roughly a five-minute confirmation window; `_recheck` (`:1300`) clears the count the moment the channel is seen again, so a channel that flickers never accumulates strikes. |
| `black_bloc/cogs/moderation/modmail.py:75` | ⚠️ **Only a real, human message is modmail** (checklist 23). `MessageType` also covers pins, joins and thread-created notices, every one of which carries a member as its author — opening a ticket from Discord's own "so-and-so was pinned" line would be a ticket nobody wrote. Same filter, same reason, as the honeypot (`cogs/moderation/honeypot.py:26`). |
| `black_bloc/cogs/moderation/modmail.py:181` | The row is created with `channel_id = 0` and filled in once the channel exists, because the topic has to carry the ticket id and the id only exists once the row does. Channel-first would leave an orphan channel with nothing pointing at it when the process dies, and nothing would ever clean that up. |
| `black_bloc/cogs/moderation/modmail.py:231` | One query answers "which ticket is this channel" for a channel **or** a thread, because thread mode stores the parent in `channel_id` and the thread in `thread_id`. Matching `channel_id` only when `thread_id IS NULL` is what stops every thread ticket in one staff channel matching a message typed in that channel itself. |
| `black_bloc/cogs/moderation/modmail.py:295` | A staff reply is recorded **before** it is sent and marked undelivered afterwards, never the other way round: a reply that was written and failed is a fact the transcript must carry, and a row written only on success loses exactly the messages staff most need to see they lost. `delivered` is an additive column with `DEFAULT 1`, so every row that predates it reads as delivered rather than as a mystery. |
| `black_bloc/cogs/moderation/modmail.py:384` | ⚠️ **The per-user lock is the whole defence against a burst.** Somebody sends three DMs in two seconds; without it three listener invocations each find no open ticket and each create a channel. It lives on the **bot**, not the cog, for the same reason temp voice's does (`cogs/community/tempvoice.py:276`). Behind it sits the partial unique index `modmail_open_ticket` — belt and braces, because a lock is per-process and an index is not (checklist 6). The `IntegrityError` branch in `_open_or_find` (`:882`) is what the index feels like when it fires. |
| `black_bloc/cogs/moderation/modmail.py:395` | `modmail_staff_channel_id` deliberately has **no default of its own**; it falls back to `staff_channel_id` here, in one place. A default copied into the registry would freeze whatever the staff channel was the day the key was added, and then silently disagree with it forever. |
| `black_bloc/cogs/moderation/modmail.py:408` | ⚠️ **Creating a channel is invisible to `guard.py`, so the test policy is enforced by PLACE** — the same rule as events (`cogs/community/events.py:451`), temp voice (`cogs/community/tempvoice.py:1637`) and the honeypot (`cogs/moderation/honeypot.py:310`). While a guard is installed, tickets are made in the test channel's own category and nowhere else. ⚠️ **A test channel with NO category is a refusal, not a `None`**: passing `category=None` to `create_text_channel` is not "nowhere", it is the top level of the server, in public, which is the one place a modmail ticket must never appear. |
| `black_bloc/cogs/moderation/modmail.py:426` | Thread mode's equivalent: while the guard is on, threads are made **in the test channel itself**, which is exactly what the owner's sweep expects to see. A private thread's own id is not the test channel's id, so the guard still refuses to *speak* in it — which is what `speak` (`:493`) exists to handle. |
| `black_bloc/cogs/moderation/modmail.py:466` | ⚠️ **Deleting a ticket channel is a side effect the guard cannot see**, so the question asked is the place, not the mode: a channel in the test category or a thread of the test channel may be removed, anything else logs `modmail.would_remove_place`. The ticket is still closed and its transcript still filed — a refusal to tidy up must never cost the record. |
| `black_bloc/cogs/moderation/modmail.py:479` | ⚠️ **Three answers — "here", "gone" and "could not tell" — and they are not interchangeable** (checklist 10). `guild.get_thread` returns `None` for an **archived** thread, and our threads auto-archive after a day, so closing a ticket on a cache miss would be silent data loss. The miss falls through to a fetch; only `NotFound` counts as gone, and any other failure leaves the ticket open for the next tick. |
| `black_bloc/cogs/moderation/modmail.py:499` | ⚠️ **The one deviation from the guard's usual shape, and the same one events made** (`cogs/community/events.py:471`). A ticket channel is not the test channel, so `guard.py` would refuse every message into it; refusing outright would make the feature untestable, because the ticket **is** the surface the owner has to read. While the guard is on, what the ticket would have said goes to the test channel instead — still the guarded send, nothing lands anywhere the policy forbids, and every caller learns where it went. The explicit unarchive is here rather than in the close path: a thread that auto-archived after a day is the normal state of a quiet ticket, and `send` into an archived thread is not reliably an unarchive. |
| `black_bloc/cogs/moderation/modmail.py:532` | DMs are inside the test policy (owner rule, `CLAUDE.md`), so this is the one path that always really happens. It returns the **reason** rather than a bool, because "the member has blocked the bot" has to reach the ticket as `modmail.dm_failed` (`:590`); a swallowed failure would leave staff believing a reply was delivered. |
| `black_bloc/cogs/moderation/modmail.py:546` | A reaction is a side effect `guard.py` does not patch, so it asks the guard by hand. While test mode is on the ✅ on a staff message is skipped, and the echo into the test channel is the confirmation instead. ⚠️ The tick is **not** unconditional: a DM whose relay never reached the ticket gets ⚠️ instead, because a tick on a message staff never saw is the bot lying to the member. |
| `black_bloc/cogs/moderation/modmail.py:773` | ⚠️ **A test-mode affordance, and a deliberate deviation from `phase7-design.md`.** `tree.interaction_check` only accepts commands typed in the test channel, so `/reply` can never be run inside a ticket while test mode is on. Three answers, in order: the ticket named by `ticket:`, the ticket of the channel you are in, or — only when neither applies — the single open ticket. Two or more open and it refuses and lists them, because guessing which member a reply reaches is the one mistake this feature must not make. The digits check is `isdecimal`, not `isdigit`: `isdigit` accepts `²`, which `int()` then refuses. |
| `black_bloc/cogs/moderation/modmail.py:805` | **Phase 8a merge.** `loop_health(name)` is how the status page reads this cog's loop health without knowing its attribute names: here they are plain `last_ok_at` / `last_error` strings on the cog. The page asks; it never guesses (`black_bloc/api/status.py:139`). |
| `black_bloc/cogs/moderation/modmail.py:825` | ⚠️ **The order of the gates is the safety property.** The guild is chosen from the **open ticket first** and only then from where the member is, so somebody who leaves the server mid-conversation keeps talking in the ticket they already have (`phase7-design.md`, §Edge cases). The `modmail_enabled` gate then runs **before** the no-guild refusal, and a stranger DMing a bot that answers no modmail anywhere gets **silence** — while the incumbent ModMail bot still holds the inbox, an unsolicited "you are not in any server I look after" from a second bot is spam we sent. |
| `black_bloc/cogs/moderation/modmail.py:916` | ⚠️ **No staff role resolving is a refusal to open the ticket at all**, in both modes (checklist 21). A channel with no staff overwrite is visible to server admins only and a private thread with nobody invited has nobody in it: the member is told nobody read their message, which is true, instead of waiting on a ticket nobody can see. The reason reaches the log as `modmail.open_failed` / `no_staff_roles`. |
| `black_bloc/cogs/moderation/modmail.py:956` | A ticket whose channel Discord refused is closed **in the same breath**, with the reason on the row. Left open it would block every future DM from that member behind a ticket that does not exist, and the unique index means nothing else could be opened either. |
| `black_bloc/cogs/moderation/modmail.py:1031` | ⚠️ **A plain message in a ticket is a REPLY that reaches the member; `=` keeps it private.** That is the incumbent's behaviour and it is dangerous by nature, so the checks in front of it are the safety property: a known open ticket, in the right guild, from somebody `store.is_staff` agrees is staff, not a bot, not a webhook, not the text-command prefix, and not a message that opens by mentioning Black Bloc — `@Black Bloc what is this ticket` is a question about the bot, not a sentence to forward to the member. |
| `black_bloc/cogs/moderation/modmail.py:1205` | ⚠️ **The order inside a close is the contract, and the review reversed the first two steps.** Row closed → transcript filed → member told → channel removed, all inside the per-user lock, off a **single** `now_iso()` so the row, the file and the embed cannot disagree by a second, with the status re-read after taking the lock so a second `/close` is told it lost rather than filing a second transcript. Closing first means a crash inside the upload leaves a closed ticket with its channel intact — recoverable; the old order could leave a ticket open whose channel was already gone. ⚠️ **A transcript that did not file keeps the channel** (`modmail.place_kept`): the messages are then only in SQLite, and deleting the one human-readable copy to tidy up would be the review's worst finding made permanent. |
| `black_bloc/cogs/moderation/modmail.py:1218` | Three outcomes, three kinds, never shared (checklist 2): filed → `modmail.transcript`, refused by the test policy → `modmail.would_post_transcript`, refused by Discord or missing a channel → `modmail.transcript_failed`. The owner's verification method is reading the log. The file is built in memory because the container has no writable scratch worth trusting. |
| `black_bloc/cogs/moderation/modmail.py:1258` | Reconciliation runs at `cog_load`, at `on_ready` **and** on a five-minute loop (checklist 4 and 25), for the same reason events does (`cogs/community/events.py:1154`): `setup_hook` runs before the gateway connects, so a reconcile that iterates `bot.guilds` there alone is a no-op on every real start. `on_ready` also **starts the loop** when `cog_load` could not — a cog loaded before the database connected would otherwise never reconcile again for the life of the process. |
| `black_bloc/cogs/moderation/modmail.py:1277` | ⚠️ **discord.py re-raises a non-HTTP exception out of a loop and the loop stops for the life of the process** (checklist 28) — silently, which is the part that matters. The handler logs, records `last_error`, and restarts; `last_ok_at` is stamped at the end of every clean pass and both are printed by `/modmail status` (`:1470`), because `is_running()` is liveness and this is health (checklist 9). |
| `black_bloc/cogs/moderation/modmail.py:1300` | Two jobs. A ticket that never got a place is closed once the grace has passed (checklist 5): a row is written before its channel exists (`:876`), so a process killed between the two leaves `channel_id = 0`, and the grace stops the loop cancelling a ticket that is halfway through being opened. A ticket whose place has **gone** needs two consecutive misses (`:63`), and its close is **not silent** — the member is DMed, because a conversation that ends because staff deleted the channel still ended, and silence would leave them waiting. Unavailable guilds are skipped entirely (checklist 32): `bot.guilds` still lists a guild in an outage, and every lookup in it fails in exactly the way a deleted channel does. |
| `black_bloc/cogs/moderation/modmail.py:1319` | Two jobs, both "forget what no longer exists" (checklist 26): the three channel settings are cleared so `/modmail status` stops naming a dead channel, and any ticket living in the deleted channel is closed at once rather than waiting up to five minutes for the reconciler, which is only the backstop for the case the bot was offline. `/modmail forget` (`:1446`) is the same clearing by hand, for the case where the channel still exists and the pointing was simply wrong. |
| `black_bloc/cogs/moderation/modmail.py:1335` | A member who leaves gets a **note in the ticket, and the ticket stays open** (`phase7-design.md`, §Edge cases). Closing it would be tidier and wrong: staff are usually mid-conversation about the ban that just happened, the DM channel still works, and the transcript would lose the half of the conversation that had not happened yet. |
| `black_bloc/cogs/moderation/modmail.py:1494` | ⚠️ **`/modmail settings` calls this, not the status command.** Two slash commands cannot each `defer()` the same interaction — the second raises `InteractionResponded` — so the shared thing is the lines, not the callback. That is also why every management command defers first and answers through the followup: `staff_roles` walks every role's computed permissions and the DB is touched two or three times, which is comfortably more than Discord's three seconds allows for (checklist 24). The `log_action` calls sit **after** the answer for the same reason: the caller waits on the log channel otherwise. |

## `tests/test_modmail.py`

| Key | Note |
|---|---|
| `tests/test_modmail.py:69` | ⚠️ **The changeover test.** Black Bloc must not read ModMail's own channel topics as its own, or the two bots would fight over five live tickets during the switch. The literal is the real one measured from the server. |
| `tests/test_modmail.py:168` | ⚠️ **The ping test.** DM text is written by anyone who can DM the bot, so `@everyone` in it must render as text. Only the staff roles passed in explicitly may ping, and only the thread invite passes any. If this test is ever edited, read `black_bloc/modmail.py:155` first. |
| `tests/test_modmail.py:182` | The transcript is the only durable record of a ticket once its channel is deleted, so this pins all four things that make it readable: order, the `NOTE` label, the anonymous marker, and attachments as links. |
| `tests/test_modmail.py:269` | ⚠️ **The regression test for the wrong note above.** It passes a deliberately multi-byte string and asserts the ENCODED length, so a return to character slicing fails here rather than in production; it also asserts no replacement character, which is what a naive byte cut produces. |

## `tests/cogs/moderation/test_modmail.py`

| Key | Note |
|---|---|
| `tests/cogs/moderation/test_modmail.py:377` | ⚠️ **The test-policy proof.** With a guard installed the ticket channel is still made, in the test category, and everything it would have said lands in the **test channel** — the deviation explained at `black_bloc/cogs/moderation/modmail.py:499`. If this test is ever edited, the test policy changed. |
| `tests/cogs/moderation/test_modmail.py:388` | ⚠️ **The burst test.** Two DMs dispatched together produce exactly one ticket, one channel and two recorded messages. Unlike the events approve race there IS an index behind the lock, and both are asserted — the lock here, the index in `tests/storage/test_db.py`. |
| `tests/cogs/moderation/test_modmail.py:480` | Pins the four facts that make thread mode private rather than merely tidy: `private_thread`, `invitable=False`, a day's auto-archive, and the staff ping that is the ONLY role mention this feature ever makes — asserted as an `allowed_mentions` list, not just as text in the message. |
| `tests/cogs/moderation/test_modmail.py:560` | A member who has blocked the bot must produce `modmail.dm_failed` **and never a `would_` kind** (checklist 2), and the ticket must say so in words — staff reading the ticket are the only people who can act on it. |
| `tests/cogs/moderation/test_modmail.py:808` | The other half of checklist 2 on the close path: a transcript the guard refuses is a `would_`, the ticket still closes, and the staffer is told the transcript did not land rather than left to assume it did. |
| `tests/cogs/moderation/test_modmail.py:836` | ⚠️ **The two-strike test.** One reconcile leaves the ticket open, the second closes it, and the member is DMed. `:852` is its mirror: a channel that comes back between two ticks resets the count, which is the whole reason the count exists. |
| `tests/cogs/moderation/test_modmail.py:888` | ⚠️ **A failed lookup is not evidence of a deleted channel.** The fake's `fetch_channel` raises a 500 and the ticket stays open. Without this the reconciler would close every open ticket during a Discord outage — deleting channels and filing transcripts for conversations that were still going. |
| `tests/cogs/moderation/test_modmail.py:1007` | ⚠️ **The silence test.** A stranger DMing while no guild has modmail enabled must receive **nothing at all**. It is the one assertion in the file about a message that does not exist, and it is the difference between a bot that is off and a bot that argues with strangers. |
| `tests/cogs/moderation/test_modmail.py:1049` | No staff role resolving means no ticket, no channel and a member who is told — the ticket nobody could have read is never created. Its neighbour at `:1033` is the same refusal for a test channel with no category, which would otherwise put a modmail ticket in public at the top of the server. |
| `tests/cogs/moderation/test_modmail.py:1092` | The close whose transcript did not file keeps the channel, and the messages are still in SQLite. Read this before changing the order inside `_close`. |

---

# Phase 6 — moderation (F7)

> **Keyed against `main` after the Phase 6 merge.** Status: TRACKED (owner, 2026-08-31).
> **Last verified: 2026-08-26** — this section was written against branch
> `worktree-agent-a258e862824ad6c25` (commit `71626c5` plus the two
> adversarial-review fix commits), and the merge check found **every key in it
> unmoved**: the phase's four files landed byte-identical, so branch line
> numbers and `main` line numbers are the same ones. That is evidence about the
> merge, not luck — a moved key here would have meant the merge had edited a
> file it was only supposed to add. Only the keys into files the merge *did*
> touch (`storage/db.py`, `settings_store.py`, `cogs/core.py`) moved, and those
> are corrected below. NOT verified: any of it running against live
> Discord — no message has ever been deleted and no member timed out by this
> code.

## `black_bloc/automod.py` — the rule engine, no Discord in it

| Key | Note |
|---|---|
| `black_bloc/automod.py:89` | `@everyone`/`@here` are matched as raw text rather than read off `message.mention_everyone`, because that attribute is about whether the ping **was allowed**, not about whether the member tried. Somebody without Mention Everyone typing it five times is exactly the spam this rule is for. It matches anywhere in the message, which is what Discord's own parser does. |
| `black_bloc/automod.py:169` | ⚠️ **Clearing the window is what makes a verdict fire ONCE.** Before the review the five-mention window stayed full after firing, so the member's next message — an apology, anything — re-read the same five hits and produced a second verdict, a second case row and a second timeout. Every message for the rest of the window was a fresh punishment for one burst. Firing now empties that (rule, member) deque; the window starts again from the next message. |
| `black_bloc/automod.py:341` | ⚠️ **Owner decision, 2026-08-26: mention spam counts RAW mentions.** Every user and role mention counts, the same person mentioned five times counts five times, and `@everyone`/`@here` count one each. The old unique-target counting made the rule trivially defeatable (mention one person twenty times) and did not match what Carl was doing beside it. The `["@everyone"] * n` tokens are placeholders — nothing reads a token's value any more, only how many there are. |
| `black_bloc/automod.py:381` | ⚠️ **A windowed rule may only fire on a message that CONTRIBUTED to it** (`if not tokens: return None`). The window is per member, not per message, so without this any later message — with no mentions at all — would be the one that "tripped" a full window, and the case card would name a message that did nothing wrong. Paired with the clear above: contribute, fire, reset. |

## `black_bloc/modcases.py` — the case row and the card

| Key | Note |
|---|---|
| `black_bloc/modcases.py:30` | 120 characters of a reason on a `/cases` line, 1900 per message. Discord's ceiling is 2000; the gap is the room a mention or an ellipsis takes when the numbers change. A page of ten cases with 500-character reasons was a 400 from the API — a command that answered nothing at all. |
| `black_bloc/modcases.py:60` | The sentence appended to a shadow card **after** somebody presses Apply now. It uses `<t:…:f>` so every staffer reads it in their own zone, and it goes in the embed's `description` because the fields are already the case's facts. |
| `black_bloc/modcases.py:125` | `duration_s` exists so the automod DM can say **timed out, and for how long** (review finding: the card said "timed out 5m" while the member was told only that they had been "warned by the automatic filter" — the two surfaces disagreed about what had happened to them). `automod_timeout` is its own `DM_ACTIONS` entry rather than a flag because the wording, not just the length, differs. |
| `black_bloc/modcases.py:154` | ⚠️ **`user_id` may be `None`, and then the card names the CHANNEL.** An untargeted `/purge` used to be filed against the moderator who ran it, which put "purge" in the mod history of the staffer tidying up — and `/cases @mod` then read like a disciplinary record. A case about a channel has no member, and `cases_for`/`count_cases` never return it because SQL `user_id = ?` cannot match NULL. |
| `black_bloc/modcases.py:207` | `actions`, `done` and `failed` are JSON lists on the row; `message_id`/`channel_id` are the message that tripped it. All five are what let a shadow verdict be applied later **exactly as the rule asked** — the button used to reconstruct the punishment from `duration_s` alone, which silently dropped `delete` and invented a warn for a rule that had neither. |
| `black_bloc/modcases.py:263` | `row_value` exists because a row read from a database written before these columns were added has no such key, and `sqlite3.Row` raises rather than returning `None`. The columns arrive through `db.py`'s PRAGMA pattern, so a live file gets them on the next start — but a row already in flight must not take a command down. |
| `black_bloc/modcases.py:275` | ⚠️ **The atomic claim: `WHERE id = ? AND applied = 0`, act only when `rowcount == 1`.** Two staffers pressing Apply now on the same card both read `applied = 0` and both punished; the unconditional `UPDATE … SET applied = 1` could not tell them apart. The lock in the cog serialises the common case; this is the fact the **database** guarantees, which is the half that survives a second process (checklist 6). |
| `black_bloc/modcases.py:284` | The outcome write is also the release: `applied` becomes 1 only when something was actually done, so a claim whose every action Discord refused hands the case back and the button works again. One statement rather than a claim/rollback pair, because a partial write here is the state nobody could reason about. |
| `black_bloc/modcases.py:337` | The warn count reads `done` rather than `applied`, because "applied" is now true of a partly-applied verdict: a case where the delete worked and the warn did not is not a warning. `LIKE '%"warn"%'` is safe only because the vocabulary is fixed (`delete`, `warn`, `timeout`) — a new action whose name contains another's would break it. |
| `black_bloc/modcases.py:376` | The card is rewritten through `get_partial_message`, so no fetch is needed, and it asks `guard.allows_channel` first because **editing a message is a second way to speak in a channel** (`guard.py:118`). A card that cannot be rewritten is logged and shrugged off: the punishment already happened, and a stale card must never undo it (checklist 12). |
| `black_bloc/modcases.py:432` | One place decides how a long list becomes several messages, and `/settings show` (`cogs/core.py:150`) uses it too. It lives here rather than in a helpers module because `modcases.py` is the plain module both cogs already import, and cogs never import each other (`architecture.md`, rule 2). |

## `black_bloc/cogs/moderation/automod.py` — the listener and the button

| Key | Note |
|---|---|
| `black_bloc/cogs/moderation/automod.py:62` | Staff resolution walks every role's computed permissions on the staff channel (`settings_store.py:359`); doing that per message put a permissions calculation in the hot path of every message in the server. Sixty seconds is the delay between a staff role changing and automod noticing — acceptable, because the cost of the miss is one moderator's message being read, not punished. |
| `black_bloc/cogs/moderation/automod.py:92` | ⚠️ **While `staff_channel_id` is still the test channel, the resolved staff set means nothing** — the default is `TEST_CHANNEL_ID` (`settings_store.py:478`), so arming automod against it arms it against whoever can see the test channel. The refusal is separate from the empty-staff one because the fix is different: set a real channel, rather than fix the one you set. |
| `black_bloc/cogs/moderation/automod.py:133` | ⚠️ **A delete is invisible to `guard.py`'s send and edit gates** (checklist 1), so it checks the guard itself and returns `test_mode`, exactly like `do_timeout` above it. Defence in depth: `_answer_for` already refuses to punish at all while a guard is installed. Do not remove it when test mode lifts — it is a no-op then. |
| `black_bloc/cogs/moderation/automod.py:146` | ⚠️ **Every message that fed the window is deleted, not just the last one.** Five messages of one mention each is the shape Carl's rule was written for; deleting only the fifth left the other four in the channel — the spam stayed and the member was punished for it anyway. Messages other than the current one are `PartialMessage`s, so no fetch is needed, and each failure is its own `automod.delete_failed` line. |
| `black_bloc/cogs/moderation/automod.py:176` | The DM is sent **after** the timeout attempt so it can say what actually happened. `warn` is what decides whether the member is told at all (it is the "tell them" action); whether the sentence says warned or timed out depends on what landed. |
| `black_bloc/cogs/moderation/automod.py:370` | ⚠️ `SafeDynamicItem` — a `DynamicItem`'s exceptions never reach a view's `on_error` (`command_errors.py:52`), so without it a failure inside Apply now was a button that spun forever. Subclasses implement `on_click`, never `callback`. |
| `black_bloc/cogs/moderation/automod.py:387` | Order in the click: staff → database → **the case lock** → read → test-mode refusal → defer → claim → punish → record → rewrite the card → answer. The defer comes before the DM and the timeout because both are round trips that outrun Discord's three-second interaction window (checklist 24). The lock is keyed on the **case**, not on the clicker: two different staffers pressing the same button was exactly the race, and a per-clicker lock is two locks that never meet. |
| `black_bloc/cogs/moderation/automod.py:298` | Apply-now can only delete when the row remembers where the message was; a verdict written before those columns existed skips the delete rather than guessing. |
| `black_bloc/cogs/moderation/automod.py:338` | The test-mode branch runs **before** the claim, so a refused apply leaves the case open for later — claiming first would mark it applied for something that never happened. |
| `black_bloc/cogs/moderation/automod.py:456` | An edit is a new fact: somebody posting "hi" and editing it into five mentions did nothing the listener would have seen. Only a **content** change re-evaluates, because Discord fires this event for embeds resolving, pins and attachment processing too, and each of those would re-count the same mentions. |
| `black_bloc/cogs/moderation/automod.py:478` | ⚠️ **A log-only verdict is a log line and nothing else** (`automod.observed`). The two rules Carl leaves on — slowmode 6/4s and linkspam 1/1s — fire constantly by design; each one used to write a `mod_cases` row and post a card, which buried the real cases and made `/cases` unreadable. Rules that punish still get a row and a card in every mode. |
| `black_bloc/cogs/moderation/automod.py:484` | ⚠️ **While a guard is installed, `on` behaves like shadow**: nothing is punished, everything is logged `would_…`. The `do_*` functions refuse anyway; deciding it here is what keeps the card, the row and the log telling one story instead of three. |
| `black_bloc/cogs/moderation/automod.py:532` | Apply now is offered only when **nothing** was done. A partly-applied verdict (warn landed, timeout refused) is not a dry run and must not be shown as one — the card names what was done and what Discord refused, and re-applying it would DM the member a second time. |

## `black_bloc/cogs/moderation/modcmds.py` — the mod commands

| Key | Note |
|---|---|
| `black_bloc/cogs/moderation/modcmds.py:471` | ⚠️ **Act first, tell them after** (review finding). The DM used to go out before `member.timeout`, so a timeout Discord refused left the member told they had been timed out when nothing had happened. ⚠️ **`/kick` and `/ban` are the deliberate exception and stay DM-first**: after either, the bot can no longer DM them at all, so the choice there is "tell them before, and risk telling them about a kick that failed" against "never tell them". A failed kick's DM is a confusing message; a successful ban's missing DM is a member who never learns why. |
| `black_bloc/cogs/moderation/modcmds.py:502` | ⚠️ **Owner decision, 2026-08-26: `/untimeout` and `/unban` are refused while `TEST_MODE`**, logged `mod.would_untimeout` / `mod.would_unban`. They are reversals, not punishments, and were allowed at first for that reason — but both change a **third party's** standing on the real server, which is what test mode exists to prevent, and neither is visible to `guard.py`. |
| `black_bloc/cogs/moderation/modcmds.py:593` | An untargeted purge is filed with `user_id = NULL` and the channel on the row (`modcases.py:154`). With a member named it is still their case. |
| `black_bloc/cogs/moderation/modcmds.py:714` | Every long answer goes out as several ephemeral messages: the first as the interaction response, the rest as followups. A single 2000-character overflow is a 400, and the person sees "the application did not respond". |

## `black_bloc/storage/db.py`, `settings_store.py`, `cogs/core.py` — what Phase 6 changed

| Key | Note |
|---|---|
| `black_bloc/storage/db.py:212` | ⚠️ **`mod_cases.user_id` is nullable**, because a purge case belongs to a channel. The `CREATE TABLE` was edited rather than migrated **only** because it has never run anywhere but a developer's machine — the phase is unmerged and undeployed. Any file that did get the `NOT NULL` version is repaired at `:245`. |
| `black_bloc/storage/db.py:227` | The five Phase 6 columns arrive through the PRAGMA pattern (`:406`), so a database written by the first build gets them on the next start with no version bump. |
| `black_bloc/storage/db.py:307` | ⚠️ **The one non-additive change in the project so far, and it is bounded.** A `mod_cases` whose `user_id` is `NOT NULL` is renamed aside **before** the schema script runs, the script recreates the table nullable, and `:255` copies the rows back and drops the husk. Its two indexes are dropped first because `ALTER TABLE … RENAME` takes them with it and `CREATE INDEX IF NOT EXISTS` would then collide with the old names. Idempotent: on a database that never had the constraint the PRAGMA check returns immediately. |
| `black_bloc/cogs/core.py:150` | `/settings show` prints every registered key with its help text; the registry passed 2000 characters in Phase 6 and the command started answering nothing at all. Owner decision: chunk it, the first chunk as the response and the rest as ephemeral followups (`modcases.py:402`). |

---

# Phase 8b — pages

> Written by the 8b **pages** builder (Builder B) on branch
> `worktree-agent-a1a9c6c08baf65618`, cut from `main` @ `618dcd1`. **Last
> verified: 2026-08-26 ~23:30** — every line number below was read off the
> file in that worktree after the last edit, and every page was rendered in a
> browser against `site/mock/server.mjs`. ⚠️ These files are **not in `main`
> yet**; re-key this whole section on merge, exactly as the Phase 6 and 7
> appendices were.
>
> NOT verified: any page against the real API. Builder A wrote the routes
> blind against the same contract (`docs/info/phase8b-design.md`) and the two
> halves have never met. Nothing here has run against live Discord.

## `site/public/assets/api.js` — the fetch wrapper and the name resolver

| Key | Note |
|---|---|
| `site/public/assets/api.js:4` | Ten seconds, then the outage state. A bot that accepts the connection and never answers is indistinguishable from a page that is still loading, and a page that hangs forever tells nobody anything. Same figure as 8a's `app.js`; it moved here because thirteen pages now share it. |
| `site/public/assets/api.js:5` | The `/api/ref/names` batch size. One request per page load is the goal; 80 ids keeps the query string well inside any sane URL limit while still being one call for every table on the page. |
| `site/public/assets/api.js:18` | The **only** place a `fetch` happens. `credentials: 'same-origin'` because the session is an HttpOnly cookie on this origin; a network failure becomes `Outage` (a different thing from a refusal) and every non-ok response becomes an `Error` carrying `status`, `code` and `isPermission`, so `app.js:77` can tell the five states apart without re-reading bodies. |
| `site/public/assets/api.js:57` | ⚠️ **`listOf` is deliberate slack in the contract.** `phase8b-design.md` names each tool route and what it returns in prose, but not the JSON envelope, and Builder A implemented them blind. Every list read goes through this, so `[…]`, `{items: […]}`, `{results: …}`, `{rows: …}` and `{<thing>: […]}` all render. When the real API lands this stays — it costs nothing, and it is what stops one naming disagreement blanking a tab. |
| `site/public/assets/api.js:79` | ⚠️ **A failed lookup is recorded as failed, never as "unknown"** (checklist 10). `looked_up: false` when the request itself failed, `true` when the resolver answered and had nothing; `ui.js:118` says which in the tooltip. Claiming "no such member" for a request that never completed is the same lie as claiming a link was checked. |
| `site/public/assets/api.js:120` | Channels and roles are cached for the life of the page because every picker on every page wants the same two lists, and they change on the scale of weeks. `forgetRefs()` exists for the console; nothing calls it on a timer, so a channel made while the tab is open needs a reload. |
| `site/public/assets/api.js:142` | The settings payload is cached and **thrown away on every write** (`:232`, `:238`), so the next reader re-reads it. A page that edits a setting and then renders a stale copy of it in another section is the "one fact, two homes" bug in miniature. |

## `site/public/assets/app.js` — the shell every page boots through

| Key | Note |
|---|---|
| `site/public/assets/app.js:3` | ⚠️ **One tab list, not thirteen.** The nav is built from this array into every page's empty `<nav id="tabnav">`. Thirteen hand-written navs would drift the first time a tab was renamed, and the drift shows up as a dead link on twelve pages. |
| `site/public/assets/app.js:19` | Feature key → tab, so Overview's mode chips can link to the tab that changes that mode. The key is the settings prefix (`birthday`), the tab is the page name (`birthdays`); they differ, and this is the only place that knows it. |
| `site/public/assets/app.js:45` | The outage sentence is the one refusal wording that lives in the page. The API supplies the other four, because it knows *which* it is — but a dead API cannot describe itself. Verbatim from 8a. |
| `site/public/assets/app.js:73` | The five states, kept apart because their fixes differ: sign in / ask a Lead / sign in again / retry (the bot could not ask Discord) / retry (an outage). ⚠️ `staff_unknown` gets the neutral `info` dot and a **retry**, never a permission colour — it is a fault, and colouring it as a refusal sends people asking for access they already have. |
| `site/public/assets/app.js:126` | `start()` returns its own `reload`, and each page module keeps it in a module-level `refresh`. Every write ends with `refresh()`, which re-runs that page's `load()` and rebuilds `#dash` — the page never reloads, and no page has to reconcile a hand-patched DOM against what the API now says. |

## `site/public/assets/ui.js` — the widgets

| Key | Note |
|---|---|
| `site/public/assets/ui.js:20` | ⚠️ **An `Outage` must not show its own message.** `String(e)` on a failed fetch is `TypeError: Failed to fetch`, which is a bare error wearing a sentence's clothes. Every write path funnels through here, so the person gets the outage sentence and the words "nothing was changed". |
| `site/public/assets/ui.js:25` | The whole page is built with `createElement` + `textContent`; nothing anywhere assigns `innerHTML`. The CSP forbids inline script and style, and a Discord display name is attacker-controlled text — the same reason `allowed_mentions` exists on the bot side (checklist 11). |
| `site/public/assets/ui.js:426` | ⚠️ **The owner's actual complaint** (*"the who category i assume is a discord user id number, that's not helpful"*): every id renders as a name, with `title="Discord id …"` so the id is still one hover away. An id that could not be resolved falls back to the id in mono with a dotted underline **and a tooltip that says why** — a name that could not be looked up is never invented. |
| `site/public/assets/ui.js:444` | `valueNode` is for values whose type the page does not know — the audit table's `value` column. Anything 15–22 digits is treated as a snowflake and resolved; everything else is printed. The width test is what keeps `honeypot_purge_days: 7` from being looked up as a member. |
| `site/public/assets/ui.js:631` | ⚠️ **Not `window.confirm`.** A native confirm cannot say three sentences, cannot be themed, and on a phone reads as a browser warning rather than as this page asking. Every destructive control (ban, kick, unban, apply, delete, unlink, close, post, setup) goes through this, and the body says what will actually happen — including that it cannot be undone from here. |
| `site/public/assets/ui.js:832` | The typed inputs, keyed by the registry's own `type` (`channel`, `channels`, `role`, `roles`, `bool`, `enum`, `int`, `color`, `json`, text). ⚠️ Nothing here decides what is *valid* — `int` carries the registry's `max` as a browser hint only, and the bot's validator is still the authority. A page that pre-empted the validator would be a second copy of the rules, and the two would drift. |
| `site/public/assets/ui.js:415` | Channel and role values are named from the **already-fetched** ref lists rather than through `/api/ref/names`, because the picker beside them has the same list open. One request, not two. |
| `site/public/assets/ui.js:904` | A save reports the API's own sentence on refusal and the **stored** value on success — the value the bot echoed back, not the one that was typed. `storedValue` (`:904`) unwraps `{value}` / `{key: value}` / a bare value, because the contract says "returns the stored value" without saying in what shape. |
| `site/public/assets/ui.js:1250` | Every write in every page module goes through `run(say, work, ok)`: it says "Working…", then either the sentence or the success line, and returns `{ok}` so the caller only refreshes when something actually changed. |

## The page modules

| Key | Note |
|---|---|
| `site/public/assets/page-overview.js:67` | Mode chips are links, not buttons: the owner asked to click a mode and land where it is changed. A feature with no tab (nothing has one today) renders as a plain chip rather than a link that goes nowhere. |
| `site/public/assets/page-overview.js:50` | ⚠️ **Blank, never zero, when the counts could not be read.** `/api/status` returns `open: null` when its database cannot answer, and "0 open tickets" would be a measurement that was never taken. |
| `site/public/assets/page-health.js:13` | Health is 8a's page, moved to its own tab with its rendering intact — same rows, same wording, same "this is liveness, not health" sentence for a loop with no recorded success (checklist 9). |
| `site/public/assets/page-settings.js:18` | `core` first, then alphabetical. The namespaces come from the API (key prefix before the first `_`), so a new key with a new prefix grows a new group here with no page change. ⚠️ The contract lists seven namespaces plus `core`; applied literally the registry also yielded `modlog`, `mod` and `carl` as one-key groups, until the reconciliation folded those three into `automod` (`black_bloc/api/settings_api.py:32`). This page needed no change either way, because it renders whatever it is given rather than a hardcoded list — which is the whole reason the decision could be taken on the API side alone. |
| `site/public/assets/page-audit.js:198` | The default view is `web.*` — what was done *from this dashboard* — filtered in the page, with the typed filter passed to the API as `kind=`. The contract does not say whether `kind` is an exact match or a prefix, so the page never depends on the answer: unfiltered, it fetches 200 and filters itself. |
| `site/public/assets/page-moderation.js:251` | The action bar's duration field is shown only for `timeout`, and kick/ban/unban are confirmed. ⚠️ Reason is not validated here — the bot refuses an empty reason with its own sentence, and that sentence is the one the person should read. |
| `site/public/assets/page-moderation.js:296` | Apply-now is offered **only** when the case says it was not carried out, mirroring the card's own rule (`cogs/moderation/automod.py:532`): a partly-applied verdict is not a dry run, and re-applying it would DM the member twice. |
| `site/public/assets/page-automod.js:85` | The arming switch is `automod_mode` rendered through the ordinary setting row, so an arming refusal (an empty resolved staff set, no mod log) arrives as the bot's sentence in the row's own notice line rather than as a special case this page invents. |
| `site/public/assets/page-modmail.js:30` | A `note` is drawn differently and **labelled** "the member never sees this". A staff note that looks like a reply is how somebody eventually pastes one into a DM. |
| `site/public/assets/page-golive.js:44` | The template preview substitutes a made-up stream client-side. It posts nothing, pings nothing, and is never sent to the bot (checklist 13). |
| `site/public/assets/page-honeypot.js:30` | Ban-now shows only on a `would_*` hit — a hit that was already acted on has nothing to carry out, and offering the button would be offering a second ban. |
| `site/public/assets/page-birthdays.js:133` | Grouped by month, days sorted inside it. ⚠️ The contract's page list mentions an **import report** for this tab but names no route for it, so the page does not have one rather than inventing an endpoint Builder A never built. |

## `site/mock/server.mjs` — the stand-in API

| Key | Note |
|---|---|
| `site/mock/server.mjs:2` | Node's own `http` and nothing else: no dependency, no install, no lockfile. It exists so the pages can be built and looked at before the real routes exist, and so a reviewer can see all thirteen tabs without a Discord token or a database. |
| `site/mock/server.mjs:8` | It serves `site/public` **and** `/api/*` on one origin, which is the arrangement the real deployment uses — so nothing has to be told where the other half is, and the `?as=` cookie applies to both. |
| `site/mock/server.mjs:10` | `MOCK_TEST_MODE` defaults **on**, so every destructive write refuses with a 409 and the guard sentence. That is the state the bot is actually in (`TEST_MODE=true`), and it means the refusal path is the one a developer sees first rather than one nobody exercises. |
| `site/mock/server.mjs:238` | The fake rows' shapes were taken from `black_bloc/storage/db.py`'s column names wherever the contract named a route but not its fields, and the settings registry is a copy of `settings_store.py`'s `KEY_TYPES` / `KEY_CHOICES` / `KEY_HELP`. ⚠️ Where the real API disagrees, **the real API wins** and this file is what changes. |
| `site/mock/server.mjs:1157` | The fake log's kinds are spelled the way the routers spell them (`web.<area>.<verb>`), re-spelled from `web.settings_set` when the two halves met. `page-audit.js` only matches the `web.` prefix, so nothing *broke* while they disagreed — which is exactly why it had to be fixed deliberately rather than being caught by a page: `site/mock/check.mjs` now asserts every kind the mock logs is in `contract.json`'s list. |
| `site/mock/server.mjs:433` | `seedState()` is a factory rather than a literal so `POST /api/mock/reset` can put the mock back. That route is **not part of the contract** — it exists so `check.mjs` can give every route the same fixture, the way each pytest case gets a fresh database. Without it the checks run in one long shared state and the eighth write finds what the seventh did. |

# Phase 8b — API

> Builder A's half: `black_bloc/api/{names,ref,settings_api,writes}.py`,
> `black_bloc/api/tools/*.py`, and the extractions in the cogs that let the web
> and the slash commands share one path. Written against
> `docs/info/phase8b-design.md` § "The contract".

## The shape every router has

| Key | Note |
|---|---|
| `black_bloc/api/writes.py:82` | ⚠️ **One rate-limit bucket per BOT, not per router.** The brief is "60 writes a minute per session"; a bucket built inside each `build_router` would have given eleven separate 60-a-minute allowances to the same person. It is stashed on the bot object because that is the one thing every router already shares. |
| `black_bloc/api/writes.py:61` | `WebActor` exists because the cogs' helpers read `actor.id` and `actor.display_name` off a member — `record_case` uses `getattr(moderator, "id", None)`, so passing a bare int would have silently written a case with **no moderator**. `actor_for` (`:170`) prefers the real cached member and falls back to this. It deliberately has no `send`, so nothing can DM the staffer who pressed the button. |
| `black_bloc/api/writes.py:165` | The 409 is `refuse_guarded`, and the sentence it carries is always the **cog's own** (`refusal_in_test_mode`, `BAN_IN_TEST_MODE`, `guard.refusal_message()`). The site never writes its own version of "we are in test mode", or the two would drift the first time the owner reworded one. |
| `black_bloc/api/writes.py:185` | Every write leaves exactly one extra `web.<area>.<verb>` line **beside** the feature's own line (`mod.banned`, `event.approved`, …), which is what makes the audit tab able to say "this was done from the dashboard" without a second table. |
| `black_bloc/api/settings_api.py:183` | ⚠️ **`Depends(...)` in a default argument is a ruff B008 error here**, and `Annotated[dict, Depends(dep)]` does not work either: `from __future__ import annotations` makes the annotation a string, and FastAPI resolves it against module globals where the closure's `writer` does not exist — the parameter silently becomes a required body field and every request 400s. So reads use a router-level `dependencies=[...]` and writes take `request: Request` and `await writer(request)` in the body. |

## `black_bloc/api/names.py` — the resolver

| Key | Note |
|---|---|
| `black_bloc/api/names.py:135` | ⚠️ **Cache only, in this order: member → role → channel → unknown.** No `fetch_*` call appears anywhere in this module; `tests/api/test_names.py` wraps the guild in a fake whose `fetch_member` raises, so a network call added later fails the suite rather than adding a Discord round-trip to every table render. |
| `black_bloc/api/names.py:47` | `channel_kind` reads `channel.type.name` and maps it, rather than `isinstance` against discord's classes — news and threads answer "text", stage answers "voice", so the four kinds the contract names cover every channel a guild can hold. It also keeps the module importable by tests that use plain fakes. |
| `black_bloc/api/names.py:166` | `named(row, guild, "actor", "target")` is what `/api/actions` uses: an id that resolves gets `<field>_name`, an id that does not gets `None`. **Never the id as its own name** — the page has the id already and needs to know that the lookup failed (checklist 10). |

## `black_bloc/api/settings_api.py`

| Key | Note |
|---|---|
| `black_bloc/api/settings_api.py:52` | Namespace = the key prefix before the first `_`, with `core` for the three un-prefixed keys, exactly as the contract says. ⚠️ Applied literally this also yields `modlog`, `mod` and `carl` as one-key namespaces — **which the reconciliation overruled** with the map at `:26`; the argument against it recorded here is still the right one to weigh (a hand-kept table of exceptions goes stale when Phase 9 adds a key), and the answer is written beside the map. Builder B renders whatever it is given (`page-settings.js:13`), so either way the two halves agree. |
| `black_bloc/api/settings_api.py:61` | JSON carries snowflakes as **strings** (the contract's own rule), but `coerce_value` insists on `int` for `channel`/`role` — so `from_json` converts on the way in and `as_json` (`:76`) converts back on the way out. Without the pair, every channel picker save would be refused by the validator for being "not a channel". |
| `black_bloc/api/settings_api.py:200` | A refused value returns **the validator's own sentence** as a 400 — `SettingError` is not caught and reshaped, so the clamp reasons (`honeypot_purge_days` naming Discord's 7-day ceiling) reach the page word for word. |

## `black_bloc/api/tools/*.py` — the feature routers

| Key | Note |
|---|---|
| `black_bloc/api/tools/mod.py:144` | ⚠️ **The guard check comes before the member lookup**, so a ban aimed at somebody who has left still refuses with the test-mode sentence rather than a 404. It calls the cog's `refuse_in_test_mode`, which records the not-applied case **and** the `mod.would_<kind>` line before the 409 — the refusal is a logged event, not a silent no (checklist 1 and 2). |
| `black_bloc/api/tools/mod.py:184` | Discord refusing an action is a **502**, not a 200 with a sad message: the `do_*` helpers return the cog's `REFUSED[kind]` sentence, which is compared by identity here. The page must not be able to say "kicked" when nobody was kicked. |
| `black_bloc/api/tools/modmail.py:62` | ⚠️ **"Close-with-delete" is the destructive part of closing, not closing itself.** The route asks `may_remove(bot, place)` — the cog's own answer — and refuses with 409 only when the guard would keep the channel. A ticket in the test channel's own category still closes normally. |
| `black_bloc/api/tools/rolemenus.py:34` | `PUT` takes the **whole** option list and syncs to it (add/replace what is listed, remove what is not), because the contract says "options in the PUT body" and a page that edits a menu has the full list in front of it. Both halves are the cogs' `add_option` / `remove_option`. |
| `black_bloc/api/tools/rolemenus.py:491` | Posting a panel outside the test channel is 409 with `guard.refusal_message()` — the same check `/rolemenu post` makes, in the same place, before anything is written. |
| `black_bloc/api/status.py:399` | `kind=` matches a whole kind **or** a prefix (`web`, `web.mod`), so the audit tab can ask for "everything done from the dashboard" in one query; `user_id=` matches either end, because "what happened to them" and "what they did" are the same question on a member's row. |

## The extractions — one home, two callers

Each of these was logic trapped inside an interaction handler. It is now a
plain async function in the **cog's own module**, and the handler calls it too;
no cog behaviour changed, and the 800 pre-existing tests still pass.

| Key | Note |
|---|---|
| `black_bloc/cogs/community/events.py:771` | `apply_decision` is `decide` without the interaction: same `event_lock`, same `can_transition`, same log lines. `decide` now closes the card and answers with what it returns. ⚠️ A refused transition comes back as `(sentence, None)` and the API turns that into a 409 — two mods clicking Approve still cannot decide twice. |
| `black_bloc/cogs/community/events.py:734` | `cancel_event` is `Events._cancel`'s body; the cog method delegates. It returns False when the row was past cancelling, which is what the API's 409 is built on. |
| `black_bloc/cogs/moderation/automod.py:325` | `apply_case` is `ApplyNowButton.on_click`'s body, `case_lock` and `claim_case` included, so the web and the button race each other correctly rather than both applying. ⚠️ The button now **always** defers before doing anything (it used to defer only on the working path) — that is the one behaviour difference, and it is invisible: every branch still answers with the same sentence. |
| `black_bloc/cogs/moderation/automod.py:279` | `save_rule` takes a dict of changes rather than one field, so the web's rule editor is one call and one `automod.rule` log line. `/automod rule set` passes a single-entry dict. |
| `black_bloc/cogs/moderation/modcmds.py:159` | `refuse_in_test_mode` returns the sentence instead of sending it, so both callers do the same recording. ⚠️ The `do_*` helpers (`warn_member`, `timeout_member`, `kick_member`, `ban_member`, `unban_member`) each return the sentence the slash command sends, which is why the API can compare against `REFUSED[kind]` to tell a refusal from a success. |
| `black_bloc/cogs/moderation/honeypot.py:245` | `ban_hit` is the Ban-now path, returning `(outcome, sentence)`; the button sends the sentence, the router maps the outcome onto a status. `make_trap_channel` (`:287`) is `/honeypot setup` the same way. |
| `black_bloc/cogs/moderation/modmail.py:556` | `send_reply`, `close_ticket`, `post_transcript` and `remove_place` are the cog methods' bodies at module level; the methods delegate. The `user_lock` is inside `close_ticket`, so a web close and a slash close cannot both file a transcript. |
| `black_bloc/cogs/community/tempvoice.py:699` | ⚠️ **The merge widened this one.** Builder A extracted `make_creator_channel` from the `618dcd1` setup command, which only ever *created*; `main` had meanwhile grown the remembered name, the join overwrites, repair and adoption (batch 1 and 2). Reconciling the two put all of it inside this function, with `repair_creator_channel` (`:434`) and `adopt_creator_channel` (`:558`) beside it, so the slash command and `POST /api/tempvoice/setup` cannot drift: `setup_channel` (`:1255`) now defers and delegates, and `_adopt`/`_repair` are gone. It still keeps `creator_spot`'s guard-aware placement — in test mode the lobby goes in the test channel's category, wherever it was asked for. |
| `black_bloc/api/tools/tempvoice.py:15` | The outcome vocabulary the merge forced: `repaired` and `adopted` join `created` as **successes**, because repairing the lobby the server already has is what the command now does. The old `already_a_lobby` 409 went with the behaviour it described — a 409 there would have made the page refuse the very thing that had just worked. |

## Deviations from the contract, and why

| What | Note |
|---|---|
| Shapes | The contract fixes the JSON only for `/api/ref/*` and `/api/settings`; those return exactly what it says (bare arrays, and `{namespace: [...]}`). Elsewhere a plain list route returns a bare array and a write returns a small object naming what it did. `GET /api/mod/cases` is `{cases, total, page, pages, per_page}` because the contract asks for `page=` and a pager needs the totals. |
| `black_bloc/api/writes.py` | Not in the deliverables list; it is the shared write side (staff + rate limit, the 409, the guild/database checks, the `web.*` line) that would otherwise have been copied into eleven routers. Tests mirror it at `tests/api/test_writes.py`. |
| Sub-paths the contract left open | `DELETE /api/modmail/snippets/{name}`, `POST /api/modmail/blocks` + `DELETE /api/modmail/blocks/{user_id}`, and `POST /api/mod/untimeout` (the contract names `warn\|timeout\|kick\|ban\|unban`; untimeout is the pair to timeout and the cog already had it). |
| Namespaces | ~~`modlog`, `mod` and `carl` appear as their own one-key namespaces.~~ **Superseded by the reconciliation** — they are folded into `automod` by an explicit override map; see the section below. The third key was retired outright on 2026-08-27. |

# Phase 8b — reconciling the two halves

> The merge of both 8b branches into `main` and the pass that made the pages,
> the routers and the mock agree. **Last verified: 2026-08-27** — every line
> number was read off the file after the last edit; 1105 tests pass, ruff clean,
> and `site/mock/check.mjs` reports 13 pages / 49 routes with every key present.
>
> NOT verified: any of it against live Discord, or the pages in a browser
> against the **real** API — only against the mock, whose shapes are now checked
> to be the same by the two halves of the contract check.

## `site/mock/contract.json` — the shapes, in one place both halves read

| Key | Note |
|---|---|
| `site/mock/contract.json:3` | ⚠️ **The one home for "what shape does this route answer in".** It was derived by reading every property access in `site/public/assets/*.js` per route, so it is the pages' actual demands rather than a restatement of the design doc's prose. `tests/api/test_contract.py` runs it against the real routers and `site/mock/check.mjs` runs it against the mock — the same table, so a shape cannot be right in one half and wrong in the other unless somebody edits one and not the file both read. |
| `site/mock/contract.json:2186` | The thirteen page paths, checked only for `#dash` and `#tabnav`. A page that renders is not a page that works, and this deliberately does not pretend otherwise — it catches a tab whose HTML was never wired to the shared shell, which is the failure a route check cannot see. |
| `site/mock/contract.json:2211` | Every `web.*` action kind the routers can write. The audit tab filters on the `web.` prefix alone, so a misspelt suffix breaks nothing visible — which is why it needs a list rather than a page to catch it. The mock spelled them `web.settings_set` for a week without anybody noticing. |

## `tests/api/test_contract.py`

| Key | Note |
|---|---|
| `tests/api/test_contract.py:41` | The one loop-bearing cog the contract test needs is now a **real `@tasks.loop`** on the class rather than a hand-rolled double with a `get_tasks()`, because `api/status.py:122` discovers loops by type (2026-08-27, KI-7). `/api/status` answers `"loops": []` without it, and `check_rows` refuses an empty list — so deleting this cog would silently stop checking the loop row's shape. |
| `tests/api/test_contract.py:64` | ⚠️ **An empty list fails.** A route that answers `[]` has had its row shape checked against nothing, which is the same lie as a green test that never ran — so the `seeded` fixture puts one of everything in the database and an empty answer is a failure, not a pass. |
| `tests/api/test_contract.py:144` | One fixture, not fifty: every parametrised case gets a fresh database with one case, event, ticket, hit, link, opt-out, session, birthday, temp channel, role menu, snippet and block. `check.mjs` mirrors it with `POST /api/mock/reset` plus the same three writes, so both halves start from the same fixture. |
| `tests/api/test_contract.py:155` | The case is seeded **`mode="shadow"`, `applied=False`** on purpose, because `POST /api/mod/cases/{id}/apply` is the one route whose success needs a verdict that was not carried out. A default case would 409 and the shape would never be seen. |
| `tests/api/test_contract.py:152` | `events_create_scheduled` is turned off, because approve is the route that reaches past the database into Discord. Faking that one narrowly is what lets the rest run against the real routers untouched. ⚠️ The second faked route was `/api/mod/parity`, which had a fake modlog history fastened to one channel; both went with the parity removal (2026-08-27). |

## The reconciliation's own fixes

| Key | Note |
|---|---|
| `black_bloc/api/settings_api.py:32` | ⚠️ **`modlog` and `mod` are moderation keys, so they live in the `automod` namespace** (owner decision at the merge; a third entry went with the parity removal on 2026-08-27). Builder A's note argued the opposite — that a hand-kept exception table goes stale when Phase 9 adds a key — and that risk is real; the answer is that this map is two lines in the one module that decides namespaces, and a settings page with one-key groups called `mod` and `modlog` is a worse thing to hand somebody than a map that needs a line adding. `page-settings.js` renders whatever it is given either way. |
| `black_bloc/api/tools/birthdays.py:120` | ⚠️ **The one route the contract named but nobody built.** `phase8b-design.md` lists an "import report" on the birthdays tab and names no endpoint, so Builder B correctly refused to invent one. It is here now because the cog already had the whole import — trapped inside the slash command, so `import_rows` (`cogs/community/birthdays.py:227`) and `members_of` (`:212`) were lifted out the same way A lifted the other nine, and the method bodies delegate. It returns the counts, the full report **and** `report_lines`' own sentences, so the page prints the bot's wording rather than counting again. |

# Phase 8b — the security review's fixes

> The deploy blockers and the hardening from the review of the 8b write API.
> **Last verified: 2026-08-27** — every line number below was read off the file
> after the last edit; 1150 tests pass and ruff is clean.
>
> NOT verified: any of it against live Discord, or a real browser against the
> real API. The same-site check is exercised through `TestClient` only, which
> sends whatever the test says rather than what Chrome would send.

## The same-site check — `black_bloc/api/server.py`

| Key | Note |
|---|---|
| `black_bloc/api/server.py:99` | ⚠️ **The whole point is that it runs BEFORE any handler, and exempts nothing under `/api` — logout included.** Until this existed, a page on any other site could `<form method="post">` at `/api/mod/ban` and the browser would attach the session cookie: `SameSite=lax` does not stop a top-level form POST, and the routers only ever asked *who* you are, never *where the request came from*. Registered FIRST in `create_app` so it is the innermost middleware, which is what lets its own 403 come back out through `security_headers` and the access log. It returns a `JSONResponse` rather than raising `Refused`, because `add_exception_handler` runs inside the user middleware stack and would never see it. |
| `black_bloc/api/server.py:65` | `Sec-Fetch-Site: same-origin` is the browser's own answer and cannot be set by a page, so it is trusted first. `Origin` is the fallback for a client that sends no fetch metadata, compared **exactly** against `settings.origin` — scheme and host both, never a prefix or a suffix test, because `https://blackbloc.heygabi.ai.evil.test` passes a suffix test. Neither header present means neither condition holds, so a bare `curl` is refused; that is deliberate, and it is why the test clients set the header (`tests/api/conftest.py:17`). |
| `black_bloc/api/server.py:81` | The second half: a **simple** cross-site form POST can only send `application/x-www-form-urlencoded`, `multipart/form-data` or `text/plain`, so requiring `application/json` on anything with a body means such a request cannot reach a handler even if the origin check were ever weakened. A request with no body at all (logout, every `DELETE`) needs no content type — `api.js` sends none for those (`site/public/assets/api.js:160`), and refusing them would break the page. `has_body` (`:72`) treats an unparseable `Content-Length` as a body rather than as none. |
| `black_bloc/api/server.py:116` | ⚠️ **Assignment, not `setdefault`.** The other security headers defer to a handler that set its own; `no-store` must not, or a route that sets a cache header once puts a member's cases in a shared proxy. It is scoped to `/api` so the page's own assets keep caching normally — the test asserts both halves (`tests/api/test_server.py:130`). |

## `black_bloc/config.py`

| Key | Note |
|---|---|
| `black_bloc/config.py:82` | `SESSION_COOKIE_SAMESITE` is `lax` or `strict` and nothing else. `none` was accepted before and would have made the same-site middleware the only thing standing between another site and the session cookie. It is a hard `ValueError`, not a warning, because a mistyped value here fails open — and `load_settings` turns it into the `ConfigError` sentence the operator reads. |
| `black_bloc/config.py:98` | ⚠️ **A short `SESSION_SECRET` disables sign-in rather than signing weakly.** The cookie is an HMAC over a payload carrying `staff`; a secret short enough to guess is a staff badge anybody can mint. 32 characters is the floor. It is a **warning and a closed door**, not an exception, because the bot itself must still start and keep moderating with the site switched off — the same shape as `twitch_configured`. The warning is on the field validator (`:88`) so it is said once at load rather than on every `/api/auth/login`. |

## The hardening — `black_bloc/api/`, `cogs/community/role_menus.py`, `site/mock/`

> **Last verified: 2026-08-27** — line numbers read off the files after the last
> edit; 1178 tests pass, ruff clean, and `node site/mock/check.mjs` reports
> 13 pages / 49 routes with `MOCK_TEST_MODE` at its default.

| Key | Note |
|---|---|
| `black_bloc/api/auth.py:376` | ⚠️ **The prune was O(n) per call and a spoofable header could outrun it.** It only ever swept keys older than the window, so a flood arriving inside one window grew the dict without bound *and* walked every key on every request. `take` now pops and re-inserts, which makes the dict least-recently-used ordered, and evicts from the front while it is over `BUCKET_MAX_KEYS` — O(1) amortised, and the key being evicted is the one nobody has used. A caller spoofing `X-Forwarded-For` can still push others out, but it cannot buy itself a fresh allowance, which is what the limit is for. |
| `black_bloc/api/writes.py:126` | ⚠️ **Reads needed their own bucket: the write limit protected nothing a read could do.** `/api/ref/names` resolves a batch of 80 ids per call and `/api/mod/cases` pages a table — a loop on either is a cheap way to make the bot walk its guild cache and its database forever, and neither ever touched the 60-a-minute write bucket. 300 a minute is five times the write rate and roughly ten page loads' worth, so a person clicking around never meets it. Same key (the session id), same sentence shape, different allowance. |
| `black_bloc/api/status.py:369` | The import is inside `build_router` on purpose: `writes.py` imports `DB_UNREACHABLE` from this module, so a top-level import here is a cycle that fails at `from . import ref` — `ref` pulls in `writes`, which pulls in a half-built `status`. Deferring it to router-build time costs one dict lookup per app, once. |
| `black_bloc/api/tools/mod.py:91` | ⚠️ **`int(payload.get("purge_days") or 0)` was a 500 on the word "seven"**, and a 500 is exactly the bare status the global rule forbids. It is now a guarded parse bounded by Discord's own 0–7, refused with a sentence naming the range — and it runs **before** the guard check, so a junk value cannot first record a `mod.would_ban` case and then fail (checklist 12). |
| `black_bloc/api/tools/rolemenus.py:262` | ⚠️ **The whole body is now checked before anything is written.** `PUT` used to write the heading and the line, then walk the options — so a bad role in position two left a menu whose heading said one thing and whose options said another. `wanted_options` resolves every role, label and shape first and hands `sync_options` (`:272`) a list it can only write. A non-dict option was a `.get` on a string, i.e. an AttributeError and a 500 (`:252`); it is a 400 with a sentence now. |
| `black_bloc/api/tools/rolemenus.py:247` | `description` is coerced to `str` before it can reach sqlite, which refuses a dict with an `InterfaceError` the page would have seen as an outage. ⚠️ The three-way meaning is kept exactly: **absent or `null` leaves the line alone, the empty string clears it, anything else is stored** — `update_menu`'s own `COALESCE`-shaped SQL is what depends on the difference. |
| `black_bloc/cogs/community/role_menus.py:258` | ⚠️ **The clamps live in the COG, not in the API, and both callers reuse them** (one fact, one home — checklist 15 and 22). Discord's limits are 256 / 4096 / 100 / 25, and they are a property of Discord, not of the dashboard; a copy in the router would have been the second home that drifts. ⚠️ **They REFUSE rather than truncate.** A silently shortened heading is words the staffer typed being changed without being told, and the review asked for the reason instead — `check_option_count` only bounds a *new* row (`:598`), so relabelling one of a full 25 still works. The slash commands catch `MenuLimitError` and say the sentence (`:1614`, `:1662`) rather than letting the tree handler answer with the generic one. |
| `site/mock/server.mjs:770` | ⚠️ **The mock refused two things the real bot allows.** A modmail reply DMs the member and a warn only writes a case and DMs them — neither touches a guarded channel, so `tools/modmail.py`'s reply route never asks the guard and `tools/mod.py` lets `warn` past it. Refusing them here taught the pages a rule the bot has not got, which is the wrong direction for a stand-in: where the two disagree, the real API wins. |
| `site/mock/server.mjs:913` | `POST /api/mock/guard` is the second non-contract route, beside `/api/mock/reset`. `check.mjs` asserts the six genuinely-guarded routes 409 and the two ungarded ones do not (`site/mock/check.mjs:212`), then turns the guard off to read the shapes of the routes that refuse (`:515`) and back on at the end. ⚠️ **Before this, `check.mjs` could only pass with `MOCK_TEST_MODE=0`** — a comment told you to set it, so the default run was seven failures and nobody could tell a real break from the expected noise. |

# Presence — the bot's own face (owner asks, 2026-08-27)

> Two asks, verbatim: *"we should put the url for the site in the bio of the
> bot"* and *"The status of the bot should be 'Cookout attendees' then the
> number of server members"*. Both are settings-driven, both are re-appliable
> by hand with `/presence apply`, and neither is a channel side effect — see
> the test-mode note below.

## `black_bloc/presence.py` — the decisions, with almost no Discord in them

| Key | Note |
|---|---|
| `black_bloc/presence.py:12` | ⚠️ **Both limits are Discord's, and both TRIM rather than refuse.** The application description is documented at 400 characters and a custom status at 128. A refusal here would be a bio that silently never gets applied at every `on_ready` for the life of the process, with the reason buried in a warning; a trim is visible on the profile itself. ⚠️ **NOT verified against a live edit** — no `AppInfo.edit` call has ever left this repo, so the two numbers are read off Discord's documentation, not measured. If a long bio ever 400s, this pair is the first thing to check. |
| `black_bloc/presence.py:24` | The whole format, in one pure function, so the sentence the server sees is asserted without a gateway. `prefix` comes from the `status_prefix` setting rather than a constant here because the owner named the words (*"Cookout attendees"*) and words a person chose belong in the registry where they can be changed without a deploy (`settings_store.py:63`). |
| `black_bloc/presence.py:33` | ⚠️ **`guild.member_count` MINUS the bots the cache can see, and the asymmetry is deliberate.** `member_count` is the gateway's own total and is correct even when the member cache is incomplete; the bot subtraction is best-effort from `guild.members`, so a bot that is not cached is counted as a human. That direction is the safe one: the number is a *head count on a status line*, not a figure anybody acts on, and over-counting by one is better than a status that says nothing while the cache fills. `isinstance(total, bool)` is rejected explicitly because `bool` is an `int` in Python and `True` would otherwise render as "Cookout attendees: 1". |
| `black_bloc/presence.py:41` | The dev guild first, the first cached guild second. Black Bloc is a one-server bot, so the fallback is what makes it work before `DEV_GUILD_ID` is set; the dev guild is named first so that a second server it happens to be in can never decide the status or the bio. `None` when nothing is cached yet, which is the normal state for the seconds before the first `READY`. |
| `black_bloc/presence.py:49` | ⚠️ **`change_presence` is a GATEWAY op, not an HTTP send, so `guard.py` neither sees it nor needs to.** The test-mode contract is about *where the bot speaks* — channels and DMs — and a status line is not a channel. This is allowed to run in test mode on purpose (owner ask, 2026-08-27); nothing here can put a message anywhere. Exceptions are **not** caught: the caller is the cog, which records them for the Health tab (`cogs/presence.py:74`). |
| `black_bloc/presence.py:64` | ⚠️ **The application description IS the "About Me" on the bot's profile** — the same field, under two names, which is why the setting is called `bot_bio` and the log line says About Me. `bot.application_info()` is fetched rather than read off `bot.application` so the comparison is against what Discord holds *now*, not against a cached copy from login; the edit needs the bot token and it is the same token the gateway is already using. |
| `black_bloc/presence.py:71` | An empty `bot_bio` is refused rather than applied, because `edit(description="")` would WIPE a profile that a person may have filled in by hand in the Developer Portal. `coerce_value` already refuses blank text at the registry (`settings_store.py:301`), so this only fires for a row that predates the key or was edited on the volume by hand. |
| `black_bloc/presence.py:79` | ⚠️ **The refusal is a warning sentence and never a raise** (owner instruction, 2026-08-27). A 403 here means the application is not owned by this token or Discord is unhappy with the text; either way the bot must keep starting. Same shape as `actionlog.py:143` and for the same reason — the thing being logged is cosmetic, and cosmetics must not take the process down (checklist 12). |
| `black_bloc/presence.py:83` | The action-log row is written only when the description actually CHANGED, so `presence.bio_set` in the log means a real edit rather than a heartbeat. `actor` is deliberately absent: nobody asked for this one, the bot did it to itself on startup. |

## `black_bloc/cogs/presence.py` — the Discord plumbing

| Key | Note |
|---|---|
| `black_bloc/cogs/presence.py:16` | Ten minutes for the loop and five seconds for the debounce. The loop is the backstop for the events the gateway can drop or that never fire (a member removed while the bot was down, a bulk ban); the debounce is what stops a raid or a bulk join sending one presence update per member. Five seconds is long enough to fold a burst and short enough that a single join is reflected while the person is still reading the welcome. |
| `black_bloc/cogs/presence.py:41` | `/presence` is a group with one command rather than a bare `/presence-apply`, so the next thing the bot needs to say about itself has somewhere to go. `apply` is staff-only through `require_staff` in the body, which is also how `/help` knows to mark it (`settings_store.py:652`). |
| `black_bloc/cogs/presence.py:45` | The name is `"status"` because `api/status.py:122` finds the loop by its **attribute name**, and this loop's attribute is `status`. Renaming the loop method silently disconnects its health from the Health tab, which is why `tests/cogs/test_presence.py` asserts the derived name rather than hard-coding the string in two places. ⚠️ **`get_tasks` was DELETED here on 2026-08-27** (KI-7): it was ours, not discord.py's, it was the only one in the tree, and a declaration only one of six cogs remembered to write is exactly the second home the discovery reader removes. |
| `black_bloc/cogs/presence.py:68` | ⚠️ Checklist 28: discord.py re-raises a non-HTTP exception out of a `tasks.loop` and the loop then stops **for the life of the process**. Same shape as `cogs/community/birthdays.py:339`. `restart()` on a loop that is not running is a no-op in the library, so the handler is safe to call from a test. |
| `black_bloc/cogs/presence.py:74` | The one place a status failure is turned into health. `last_ok_at` is stamped only when a status was actually applied — a pass that found no guild or no member count is not a success, and a Health tab that says "last ok 30 seconds ago" while the status is blank would be the "shipped ≠ verified" trap on a dashboard. `last_error` is cleared on any clean pass, so a transient gateway wobble does not stick. |
| `black_bloc/cogs/presence.py:87` | ⚠️ **The bio is written ONCE per process** (owner instruction). The flag is set *before* the await so two `READY`s arriving close together cannot both fire an edit; the status, by contrast, is re-applied on every `READY`, because a reconnect drops the presence Discord was holding and the loop's next tick could be ten minutes away. A changed `bot_bio` therefore lands on the next restart or on `/presence apply` — which is the command's whole reason for existing. |
| `black_bloc/cogs/presence.py:104` | Trailing-edge debounce: the first join schedules the refresh five seconds out and every join inside that window is folded into it, because the task is only replaced once it is `done()`. One task, never a queue — a hundred joins produce one presence update. |
| `black_bloc/cogs/presence.py:116` | `require_staff` answers with `response.send_message`, so the `defer` has to come **after** the gate or the refusal would try to respond to an already-deferred interaction. The defer is there because two round trips to Discord (an application edit and a presence change) can outrun the three-second interaction window (checklist 24). |

## `settings_store.py`, `bot.py` and `api/settings_api.py` — what presence appended

| Key | Note |
|---|---|
| `black_bloc/settings_store.py:89` | ⚠️ **The default bio is a TEMPLATE over `site_origin`, not a copied URL.** The rendered default is byte-identical to what the owner asked for, but the hostname has one home — `config.py`'s `site_origin`, which is also the OAuth redirect base and the cookie's `Secure` decision — so changing where the dashboard lives cannot leave the bot's profile pointing at the old one. `STATUS_PREFIX` is the owner's wording, verbatim. |
| `black_bloc/settings_store.py:154` | Both keys are plain `text`, which means they appear in `/settings set-value` automatically (`cogs/core.py:25`) and nowhere else. ⚠️ **That picker is now at 24 of Discord's 25 choices** — `tests/cogs/test_core.py` asserts the ceiling, so the next text/int/enum key added is a red test rather than a command that silently drops one. |
| `black_bloc/api/settings_api.py:24` | `bot_bio` and `status_prefix` are listed as core keys rather than left to `namespace_of`, which would have split the dashboard's settings page into a one-key "bot" section and a one-key "status" section — the same defect `NAMESPACE_OVERRIDE` was added for (`tests/api/test_contract.py:302`). They configure the bot itself, which is exactly what `core` means here. |
| `black_bloc/bot.py:36` | The cog list's one new line, appended last. Order is not load-bearing (cogs never import each other), and presence needs nothing from any of them. |

## `tests/test_presence.py` and `tests/cogs/test_presence.py`

| Key | Note |
|---|---|
| `tests/test_presence.py:164` | The default bio is asserted **twice on purpose**: once against the literal sentence the owner asked for, and once against the template rendered with the configured origin. The first would pass if the template were hard-coded; the second would pass if the sentence drifted. Together they pin both. |
| `tests/cogs/test_presence.py:195` | ⚠️ **The Health-tab name is derived, never typed.** The test reads the name off `cog.status.coro` and feeds it to `loop_health`, so a rename of the loop method fails here rather than quietly emptying a dashboard row. It used to go through `cog.get_tasks()[0]`; that declaration was deleted on 2026-08-27 when `api/status.py:122` started discovering loops by type. |
| `tests/cogs/test_presence.py:93` | `wait_until_ready` on the fake never returns, so a loop a test starts parks in `before_loop` and never runs its body — which is what lets `on_ready` be asserted for exactly what it did itself. The fixture cancels the loop on the way out. |

# Phase 8b — UX pass

> The dashboard's density pass, on branch `worktree-agent-a0e26f92075c642a9`
> cut from `main` @ `6f45299`, commits `f5d4658` (shell + Settings/Overview)
> and `27224c2` (the feature pages). **Last verified: 2026-08-27 ~07:20** —
> every line number below was read off the file after the last edit, all
> thirteen pages were rendered in a browser against `site/mock/server.mjs`
> with no console errors, and `node site/mock/check.mjs` reports 13 pages /
> 48 routes. ⚠️ **Not in `main` yet**; re-key this section on merge, exactly
> as the Phase 8b appendices were.
>
> NOT verified: anything against the real API — the pages were exercised only
> against the mock. No `black_bloc/**` or `tests/**` file was touched.
>
> The owner's ask, verbatim (2026-08-27 ~06:35): *"The ux is a lot of input
> boxes per page, maybe some page treeing and side tabs to make each page less
> dense, some search stuff, sections that condense."*

## The shape of the answer, and why it is in the shared layer

⚠️ **Four asks, one place.** Treeing, condensing, search and density were all
answered in `ui.js` plus a new `layout.js`, not page by page. Thirteen pages
building thirteen sub-navigations is thirteen chances to drift, and the drift
shows up as a tab whose contents list is wrong — the same reasoning that put
one `TABS` array in `app.js:6` rather than a `<nav>` in each HTML file. The
consequence is that every page got the treatment whether or not its module was
edited: `section()` and `table()` are what changed, and every page already
called both.

**The pages still own the counts**, because only the page knows what a row of
its table means. That split — shared layer owns the *shape*, page owns the
*number* — is why the second commit is small.

## `site/public/assets/layout.js` — the new file

| Key | Note |
|---|---|
| `site/public/assets/layout.js:3` | `bb_sections_<tab>` per page, `bb_last_tab` for the rail. `bb_` and not `hg_`: `theme.js` is an estate snapshot that owns `hg_theme` on this origin, and localStorage is origin-scoped, so a shared prefix is a collision waiting for the day somebody copies a newer `theme.js` in. |
| `site/public/assets/layout.js:7` | Every read and write is wrapped. A browser in private mode, with storage switched off or over quota throws on `getItem` as readily as on `setItem`, and the page must render identically with no memory at all — the memory is a convenience, never a dependency. |
| `site/public/assets/layout.js:42` | The count fallback. A page that passes an explicit count wins; otherwise the section is counted from what is in it — table rows, then `ul.rows`/chips/tiles/messages. ⚠️ It returns **null rather than 0** when it recognises nothing, and a null count renders no badge. "0" is a measurement; "I did not count this" is not, and printing the first for the second is the same lie as `page-overview.js:50`'s blank-not-zero rule. |
| `site/public/assets/layout.js:72` | First section open, the rest shut, unless the page remembers otherwise — and `data-open="1"` outranks both. That flag marks a panel the person *just clicked open* (a mod case, a modmail ticket, the role-menu editor). Without it the rebuild that follows the click would shut the thing the click opened, because a freshly-created section has nothing remembered and is not the first one. |
| `site/public/assets/layout.js:106` | The active section is "the last one whose top is above 160px", recomputed in a rAF-throttled passive scroll handler. Deliberately not an IntersectionObserver: with sections collapsed to a 50px summary, six of them intersect at once and the observer has no opinion about which is *the* one. A single threshold line has exactly one answer. |
| `site/public/assets/layout.js:123` | `syncSubnav()` exists for the settings filter, the one thing that hides sections after they are mounted. A contents list still offering a section that is not on the page any more is a link that lies. |
| `site/public/assets/layout.js:146` | ⚠️ **Called after EVERY load, not once.** `app.js:125`'s `start()` rebuilds `#dash` from scratch on every write (that is the design — no page hand-patches its DOM), so the sections it navigates are new elements each time. Nothing is retained between calls but the localStorage entry and the one scroll listener, which is removed before the next is added (`:186`). |

## `site/public/assets/ui.js` — what changed under the pages

| Key | Note |
|---|---|
| `site/public/assets/ui.js:250` | `section()` now returns a `<details>` card, and this is the whole of "sections that condense". `<details>`/`<summary>` over a button-and-`aria-expanded` toggle because the browser already ships the keyboard handling, the focus behaviour and the expanded-state announcement, and a hand-rolled one is three bugs waiting. The count lives in the summary: ⚠️ **a fold that hides how much it hides is worse than no fold** — you cannot tell a shut empty section from a shut full one. |
| `site/public/assets/ui.js:250` | The `id` option exists because a section's *title* is its slug, and two titles change with state: the audit page's second heading is "Actions taken from this dashboard" or "Actions matching automod." depending on the filter, and a slug that moves is a remembered open state that is silently forgotten. Anything whose title interpolates gets a fixed id. |
| `site/public/assets/ui.js:478` | ⚠️ **The search box appears from TWO rows, and this number is a judgement, not something the brief settled.** A filter over one row cannot do anything the eye cannot; from two it can. The alternative — a box on literally every table — put twelve of them on the birthdays page, one per month, over two rows each, which is why `page-birthdays.js:191` filters the months as a set instead and passes `search: false` down. |
| `site/public/assets/ui.js:479` | Over twelve rows a table gets `data-long`, which caps it at 26rem with its own vertical scroll and a pinned `thead`. The health page's 30-line action log was burying the three sections under it; a table that scrolls inside its box is the same argument as `.table-scroll`'s existing horizontal one, on the other axis. |
| `site/public/assets/ui.js:202` | The filter reads `row.textContent` — what is on the screen, not the row object. That is deliberate: the person is filtering what they can see, so a name resolved from a snowflake matches on the name, and an unresolved one matches on the id, which is exactly what is printed in front of them. |
| `site/public/assets/ui.js:725` | 200ms debounce on `input`, and `search` (the little X in a `type="search"` box) fires immediately — a clear should not wait. |
| `site/public/assets/ui.js:222` | `searchOver` is the same filter over a box of **cards** rather than table rows, because two things here are piles of cards and not tables: the automod rule book and the twelve months of birthdays. It appends its own "nothing matches" line **inside** the root so the line lands under the cards it is about. |
| `site/public/assets/ui.js:928` | ⚠️ **The setting row is where the "a lot of input boxes" complaint actually lived.** It was a stacked block per key — head, help, control, current value, buttons, notice — so a namespace of eight keys ran a screen and a half. It is now two columns: what the key is on the left, what it is set to on the right. `data-search` carries key + type + help pre-lowercased, which is what the Settings filter matches on. |
| `site/public/assets/ui.js:289` | `card()` grew an `actions` option: a bar pinned to the top of the card. Used on exactly one card today, the role-menu editor (`page-rolemenus.js`), because that is the only card tall enough that Save scrolls out of reach. ⚠️ Applying it everywhere would be worse, not better — a sticky bar on a card shorter than the viewport is a bar that never moves and a line of chrome that never earns its space. |

## `site/public/assets/app.js` — the rail's memory

| Key | Note |
|---|---|
| `site/public/assets/app.js:122` | ⚠️ **The last tab is restored from the bare `/` and from nowhere else.** Any query string or hash means a deep link, and a deep link outranks a memory. `/index.html` — which is what the Overview entry in the rail points at — also means Overview, deliberately: without that escape the memory would make Overview unreachable, because every route to it would bounce off to wherever you were last. `location.replace`, not `assign`, so Back does not land on a page that immediately redirects again. |
| `site/public/assets/app.js:179` | The redirect happens **before** `renderNav`, and `start()` returns a no-op refresh, so a page that is about to be replaced does not fetch, render or wire listeners. |

## `site/public/assets/site.css`

| Key | Note |
|---|---|
| `site/public/assets/site.css:175` | The rail is the two navigations in one sticky column: global tabs, then this page's sections. On a phone the same markup is two horizontal strips, above the page title. Putting the sections **under** the tabs rather than inside the page body is what makes the sticky column possible at all — the two cannot be in different grid containers and still scroll as one. |
| `site/public/assets/site.css:229` | ⚠️ **A long section name WRAPS in the wide rail; it must not push it sideways.** `.rail` has `overflow-y: auto` for a page with many sections, and a box that scrolls on one axis scrolls on the other too — so "Actions taken from this dashboard" on one line put a horizontal scrollbar under the whole rail. The element to fix was the label, not the scroller. |
| `site/public/assets/site.css:362` | ⚠️ **`.field > .field-help`, a CHILD selector, not a descendant.** `.field-help` also lives inside `.setting-head`, and a descendant `grid-column: 2` there grew *that* grid a second column, which pushed the type badge up beside the key and wrapped `log_channel_id` mid-word. The label-left layout was right; the selector was too broad. |
| `site/public/assets/site.css:113` | A `.bar` inside a `<td>` was inheriting `.bar`'s 1rem bottom margin and wrapping, so the events table's Approve/Deny/Cancel cell was three rows tall. One line; the table halved in height. |
| `site/public/assets/site.css:17` | Destructive buttons get a danger-tinted **edge**, not a fill. The shell already gives them danger-coloured text on the quiet surface; the border is what tells Delete from Cancel at a glance. ⚠️ Filling them would make the dangerous control the loudest thing on the card, which is the opposite of what a confirmation-guarded action wants. |
| `site/public/assets/site.css:81` | Nothing here re-implements `[hidden]`. `status-shell.css` carries a global `[hidden] { display: none !important; }` that outranks the `display: grid` on `.subnav` and `.setting` and the `display: table-row` on a filtered row. Three such rules were written and then deleted — a second home for a fact that already had one. |

## The pages

| Key | Note |
|---|---|
| `site/public/assets/page-settings.js:28` | The global settings filter: it hides non-matching keys, hides a namespace with nothing left, **opens the namespaces that do match** (a match hidden inside a shut fold is a match nobody finds), and calls `syncSubnav`. It matches `data-search`, so the help text is searchable too — "channel" finds every key whose help says channel, not only the ones named that. Measured: 46 keys down to 10 on "role". |
| `site/public/assets/page-rolemenus.js:677` | One section used to hold the table, a post card per menu, the New menu button and the editor. Three sections now, and the editor is its own. This page is the reason `data-open` exists: click Edit and the whole page rebuilds, and the editor you just asked for must not come back shut. |
| `site/public/assets/page-modmail.js:220` | "Snippets and blocks" became Snippets and Blocks. Two things that share nothing but a screen are two sections; joining them made the contents list say less than it could. |
| `site/public/assets/page-birthdays.js:191` | The month tables pass `search: false` and the **section** carries one filter over all twelve. A month with two people in it does not need its own search box, and twelve boxes down one page is the density complaint reappearing inside the fix for it. |
| `site/mock/server.mjs:150` | The fixture gained rows so the sections look like a real server: five more mod cases (which fills the ten-row first page and so exercises the pager), two more honeypot hits including a carried-out ban and a failed one, three more birthdays, eleven more action-log lines. ⚠️ No route, no shape and no `contract.json` entry changed — `check.mjs` reads shapes, not counts, and it still reports the same 13 pages / 48 routes. |

## birthdays â€” daily import loop (2026-08-27)

| Key | Note |
|---|---|
| `black_bloc/cogs/community/birthdays.py:50` | `IMPORT_HOURS = 24`, and the loop is `@tasks.loop(hours=24)` rather than `time=<a clock time>` on purpose. âš ï¸ **`hours=24` runs once IMMEDIATELY when the loop starts** â€” which is what makes a fresh deploy import inside a minute instead of sitting idle until the next midnight. A `time=` loop sleeps to the next occurrence, so a container restarted at 00:05 would not import for another 24 hours, and the whole point of taking the command away was that nobody has to remember to run it. The trade is that the run drifts with restarts; nothing here cares what hour it lands on, because the import is idempotent. |
| `black_bloc/cogs/community/birthdays.py:347` | The loop body is a copy of `_sweep`'s shape (checklist 28): `is_connected` guard, `try` around the work, `last_import_error` set on failure and cleared on success, `last_import_at` stamped only on a clean pass, a `before_loop` that waits for the gateway, and an `@_import_loop.error` handler that restarts it â€” discord.py re-raises a non-HTTP exception out of a loop and the loop is then dead for the life of the process. The health pair is separate from the sweep's (`last_run_at` / `last_error`) because a broken import must not read as a broken sweep, and `/birthday status` prints both. |
| `black_bloc/cogs/community/birthdays.py:300` | `loop_health` answers for `_import_loop` by attribute name, so `/api/status` lists it with no change at the API end â€” `api/status.py:_loops` finds loops by type and asks the cog for the health beside each. `tests/api/test_status.py:REAL_COGS` has the row that proves it. |
| `black_bloc/cogs/community/birthdays.py:385` | âš ï¸ **The action log only hears about a run that took something.** A daily `0 imported Â· 39 already stored` embed in the log channel is 365 lines a year that say nothing changed, so a run with an empty `imported` bucket goes to `log.info` and stops there; only a non-empty one calls `log_action`. The counts are still in the process log every day, and `/birthday status` shows when the loop last ran. |
| `black_bloc/cogs/community/birthdays.py:392` | `actor=None` and `"trigger": "daily"` in the details are what tell a log reader this was the loop and not a person. The web route (`api/tools/birthdays.py:128`) still logs the same `birthday.import` kind with a real actor and no trigger, which is the distinction. |
| `black_bloc/cogs/community/birthdays.py:370` | `import_once` walks `bot.guilds` and skips `guild.unavailable` (checklist 32) â€” the same shape `run_once` uses. An empty seed file is one `log.warning` for the whole pass and a return, not one per guild, and it is not an error: `last_import_at` still stamps. |
| `black_bloc/cogs/community/birthdays.py:71` | `NOBODY_YET` no longer names `/birthday import` â€” the command is gone, not hidden, so it is deliberately NOT in `command_visibility.HIDDEN_WHEN_OFF`. `import_rows`, `report_lines`, `members_of` and `_import` stayed exactly where they were: the web route at `api/tools/birthdays.py:117` imports all four and is the surviving on-demand path. The cog's own `IMPORT_EMPTY` sentence went with the command (the web route keeps its own). |

## site restyle — Direction A (2026-08-27)

> The dashboard rebuilt to match the approved mock, on branch
> `worktree-agent-a3ebabe5c95e7a297` cut from `main` @ `04fd62f`.
> Owner's decision, verbatim: *"Lets go with A, keep this exact same design and
> implement it but make sure our existing theme selectors work"*, narrowed the
> same day to *"make sure you follow the A design as closely as possible."*
> The pixel source is `docs/info/mock-direction-a/{Main,AModeration,ASettings}.dc.html`;
> the palette and type come from §A of `docs/info/dashboard-inspiration.md`.
>
> **Last verified: 2026-08-27 ~09:55** — every line number below was read off
> the file after the last edit. All thirteen pages were rendered in Chrome
> against `site/mock/server.mjs` (port 8788) with **no console errors and no
> horizontal page scroll on any of them**; `node site/mock/check.mjs` reports
> 13 pages / 48 routes; 1243 pytest tests pass and ruff is clean; every one of
> the six themes × two modes resolves all 24 checked `--et-*` tokens with none
> unset. ⚠️ **Not in `main` yet**; re-key this section on merge.
>
> NOT verified: anything against the real API — only against the mock. Nothing
> under `black_bloc/**` or `tests/**` was touched.

### The theme, and why `discord` is a theme rather than a rewrite

| Key | Note |
|---|---|
| `site/public/assets/estate-theme.css:1351` | The `discord` theme's DARK block is the mock's palette **verbatim** (`#1E1F22` page, `#2B2D31` chrome, `#313338` surface, `#3F4147` hairline, `#5865F2` accent, `#23A55A`/`#F0B132`/`#F23F43`/`#00A8FC`). It is placed dark-first with a `[data-mode="light"]` override, the same shape cyberpunk uses, because the mock is a dark design. Its radii are the mock's own two — 4px on controls and nav, 6px on cards — not a rounded-off grid. |
| `site/public/assets/estate-theme.css:1458` | The LIGHT block is §A's light column, with **one deliberate departure**: §A gives `--et-bg-2: #FFFFFF`, which would make the sidebar the same white as the cards and leave nothing separating chrome from page. The three shell tokens take Discord's own light chrome greys instead (`#EBEDEF` / `#E3E5E8` / `#D7D9DC`). Everything §A actually names is unchanged. |
| `site/public/assets/estate-theme.css:143` | ⚠️ **Three tokens were ADDED to the contract, and every one of the 13 declaration sites defines all three** — six themes × two modes, plus apple's duplicated media-query dark. `--et-shell-bg` is the sidebar and top bar; `--et-shell-inset` is the recessed ground *inside* the chrome (the top-bar pills, every field, the table header strip); `--et-nav-active` is the active nav fill. They exist because the mock needs three grounds the old contract had no name for, and giving them values per theme is what stops the other five themes rendering an unstyled shell. Proof: `grep -c` returns 14 for each (13 blocks + this contract line). |
| `site/public/assets/estate-theme.css:123` | Inter is the **variable** woff2, so one `@font-face` with `font-weight: 100 900` covers the mock's 400/500/600/700 — Google serves the same file for all four, and shipping it four times would be 145 kB of duplicate. JetBrains Mono is declared `100 800` for the same reason. Both are self-hosted under `assets/fonts/` with `OFL-inter-jetbrainsmono.txt` beside them: `black_bloc/api/server.py:37` has no `font-src`, so `default-src 'self'` is the effective rule and a Google Fonts `<link>` would be blocked outright. Only the `discord` theme maps them through `--et-font`/`--et-font-mono`; the other five keep their own faces, and `@font-face` fetches nothing until a theme asks for it. |
| `site/public/assets/theme.js:83` | `discord` is FIRST in `THEMES` and every page declares `data-default-theme="discord"`, which is how it became the default without a second registry. The list and `LABELS` are still the one home for theme names — the cog builds its `<option>`s from them, so theme #7 stays one edit. |

### The shell

| Key | Note |
|---|---|
| `site/public/assets/shell.js:7` | `GROUPS` is the mock's sidebar, and it is the **one place** the four group headings, the thirteen tab labels and the feature-key-per-tab live. `page-overview.js:26` reads the same map for its Features card rather than title-casing the raw feature id — that is why the card says "Go-live" and "Temp voice" rather than "Golive" and "Tempvoice". |
| `site/public/assets/shell.js:53` | ⚠️ **The shell fetches `/api/status` ONCE per page load and every consumer awaits the same promise** — the sidebar dots, the health pill, the server name, Overview's whole page and Moderation's mode pills. No new endpoint was invented; this is the route the Overview page already read. It `.catch(() => null)` on purpose: a stranger gets 403 here and the shell must degrade to "no dots, no pill", never to a broken page. |
| `site/public/assets/shell.js:121` | A feature the bot reports **no** mode for gets **no dot**, not a grey one — a wrong dot is worse than an absent one. `modmail_mode` is `channel`/`thread`, not on/shadow/off, so both are shown as the green ON dot with the real word in the `title`. ⚠️ **The mock shows a green dot on Moderation; there is no `moderation_mode` key**, so that one item has no dot. |
| `site/public/assets/shell.js:139` | The health pill is `online · <uptime>` from `bot.ready` + `bot.uptime_seconds`. When the status call failed it says "health not known" with an amber dot rather than showing a confident green — an unread number is not a healthy one. |
| `site/public/assets/shell.js:201` | The narrow-screen sidebar. `data-open` on `#side` is the only state; CSS owns the transform, JS owns the attribute, so the two never fight over one property. A tap on any link inside closes it, because on a phone the sidebar covers the thing you just navigated to. |
| `site/public/assets/site.css:297` | ⚠️ **The breakpoint is 900px**, chosen because the mock is a 1440px desktop and 240 + the four-column stat strip stops being honest below roughly 900. Under it the sidebar goes `position: fixed` off-canvas behind the top-bar menu button with a scrim; the grid drops to one column. A separate 1100px break drops `.twocol` to one column (§5's "2-up over ~1100px"), and 700px halves the stat strip. |
| `site/public/assets/site.css:250` | ⚠️ **The theme cog is the SAME control, moved.** `#hg-cog` / `#hg-cog-panel` / `#hg-theme-select` and every `theme.js` behaviour are untouched; three declarations take it out of its fixed corner and into the top bar, and the panel's `top` moves under the 56px bar. Restyling it in `site.css` rather than editing `estate-theme.css`'s `.hg-cog` keeps the estate snapshot diffable against its source. |
| `site/public/assets/site.css:34` | The mock's base size is **14px**, not the estate's 17px reading size — this is a console. Setting it on `.shell` rather than `body` means anything outside the shell (nothing today) keeps the estate default, and every explicit size below it is quoted from the mock. |
| `site/public/assets/site.css:1289` | ⚠️ **The "On this page" sub-navigation was MOVED, not dropped.** The mock has no rail for it, but deleting it would lose the section links, their counts and Expand/Collapse all; the sidebar is where a sub-feature already reports itself, so it lives under the nav as an indented list. `layout.js:225` widened its selector from `:scope > section.sect` to any depth, because Settings now nests its sections inside a two-column grid. |
| `site/public/assets/app.js:186` | The subtitle no longer gets `Signed in as X` appended — the top-bar user chip carries that now, and the sub-line is a fixed sentence in the HTML. The 13 page modules stopped passing `subtitle:` for the same reason: one fact, one home. |

### The three mocked pages

| Key | Note |
|---|---|
| `site/public/assets/page-overview.js:36` | Features are shown in **sidebar order**, not registry order, so the card and the rail read the same way down the page. |
| `site/public/assets/page-overview.js:99` | Each feature row's sub-line prefers a real count from `status.open` and falls back to a sentence about the mode. ⚠️ **The mock's sub-lines ("3 open cases", "12 would-have-acted this week") are for counts the API does not report**; inventing them would be the exact failure the verification rules exist to stop, so a feature with no count says what its mode means instead. |
| `site/public/assets/page-overview.js:123` | ⚠️ **`web.modmail.snippet` reads as "modmail snippet", not "snippet".** Taking only the last dot-segment — which the first cut did — threw away the subject and produced lines like "setup — by Nick". The leading `web.` says only where the click came from and is dropped; everything after it is the sentence. `would_` and `_failed` set the row's warn/danger tone, which is how the mock's amber shadow lines are driven. |
| `site/public/assets/ui.js:67` | `shortWhen` is the mock's stamp grammar in one place: the 24-hour clock for today, "Yesterday", then the date. **`hour12: false` is deliberate** — the mock reads `08:41`, and an en-US locale would render `08:41 AM`. The full timestamp travels in the `title`, so shortening loses nothing. |
| `site/public/assets/page-moderation.js:34` | ⚠️ **The mock's pill row is "Moderation ON · Automod SHADOW"; there is no moderation mode**, so the row shows the two moderation-family features that DO report one — Automod and Honeypot. The layout is the mock's; the content is what the data supports. |
| `site/public/assets/page-moderation.js:117` | The four-stat strip. Only `Cases` is authoritative (`payload.total`); the other three count the loaded page, which is why they are labelled with plain nouns rather than the mock's "Warned this week" — the API has no week window. "Showing N of M cases" under the table is what scopes them. |
| `site/public/assets/page-moderation.js:200` | The cases table is the mock's CSS grid, `72px 150px 130px minmax(0,1fr) 150px 120px 24px` with a 12px gap, verbatim — not the shared `table()`. It sits in a `.table-scroll` with `min-width: 860px` so it scrolls **inside its own box** and the page body never scrolls sideways. Filtering is client-side over the loaded page (chips + search), which is why the footer counts against `rows.length` and the pager still asks the API for the next page. |
| `site/public/assets/page-moderation.js:161` | ⚠️ **Two features the mock has no place for were KEPT, as collapsible sections below the table rather than dropped**: "Take an action" (the whole warn/timeout/kick/ban/unban bar, which Phase 8b requires and §A's own wireframe has) and "Only one member" (the server-side member filter). Their cards pass `null` as the title because the section header already names them. |
| `site/public/assets/ui.js:1080` | ⚠️ **ONE save mechanism per page (§5.2), and one implementation of it.** `settingsEditor` owns the dirty set for a group of rows and the docked bar; `settingsPanel` wraps it for the ten feature pages and `page-settings.js` wraps it for all 47 keys at once. The per-field Save/Clear buttons are gone estate-wide, not just on the Settings tab. |
| `site/public/assets/ui.js:1107` | ⚠️ **The per-row Clear button had nowhere to go, so "put it back to its default" became a gesture: empty the control.** A row whose new value is blank while its stored value was not calls `clearSetting` instead of storing `null`. Without this the docked bar would have quietly removed a capability the old page had. |
| `site/public/assets/ui.js:217` | `humanLabel` derives the mock's human label from the key rather than shipping a 47-row lookup table that a new setting would silently miss: strip a known namespace prefix, drop a trailing `_id`/`_ids`, unscore, sentence-case. ⚠️ `mod_` and `modlog_` are deliberately NOT stripped — the API folds them into the `automod` group, where a bare "Channel" would be ambiguous. |
| `site/public/assets/ui.js:803` | The three-segment control. It is used for **any** enum of three or fewer choices, not only `*_mode`, because that is what makes it honest: `modmail_mode` is `channel`/`thread` and gets two segments with its own words, where hard-coding ON/SHADOW/OFF would have shown a mode that key never has. Booleans get the same shape. |
| `site/public/assets/ui.js:793` | The registry lists modes `off, shadow, on`; the mock reads **ON · SHADOW · OFF**. `segOrder` reverses only when every choice is one of those three, so an unrelated enum keeps its own order. |
| `site/public/assets/ui.js:780` | ⚠️ **`jsonText(null)` used to return `"{}"`, which made `automod_rules` read as CHANGED the moment the page loaded** — a dirty row nobody had touched, and a save bar that never went away. Null now renders as an empty box and an empty box reads back as null. |
| `site/public/assets/site.css:874` | `.setrow-control` is the mock's 218px slot, except where it holds a segment: `mod_dm_on_action`'s three choices are long words and were being clipped, so `:has(.seg)` lets that one control size to its content. |
| `site/public/assets/page-settings.js:29` | The two columns are balanced by **row count**, not group count, so a 9-key group and a 1-key group do not end up side by side the way naive alternation puts them. |

### Components, and the two things that had to change under every page

| Key | Note |
|---|---|
| `site/public/assets/ui.js:289` | `card()` now wraps its children in a `.card-body`, so the head can be the mock's bordered strip and a row-list card can pass `flush: true` and let its rows own the padding and hairlines. Every page got the new look without being edited. |
| `site/public/assets/ui.js:46` | `icon()` exists because `el()` uses `createElement` and would build an HTML `<chev>`, not an SVG one. Parsing a literal through a throwaway `<div>` gets the SVG namespace right; the markup is a fixed table in this file, never interpolated, so `innerHTML` here carries nothing an attacker wrote. |
| `site/public/assets/site.css:482` | Every status tint is `color-mix(... N%, transparent)` off the theme's own `--et-ok`/`--et-warn`/`--et-danger`, at the mock's exact 14%/40% fill-and-border (18% for an active segment, 6% for a changed row, 10% for OFF). That is what keeps `site.css` at **zero raw hex** while still matching `rgba(35, 165, 90, 0.14)` on the nose — and what makes a warn pill amber in discord and mustard in retro without a second rule. |
| `site/public/assets/site.css:860` | ⚠️ **A theme whose primary button is a borderless fill leaves its quiet and warn variants with no edge at all.** `.btn.quiet` sets only a background, and discord's `--et-btn-border` is `0 solid transparent`, so on a surface-coloured card the Discard and "Do it" buttons were invisible text. The secondary tiers get an explicit hairline back. |

## go-live — YouTube via presence (2026-08-27)

Owner ask, 2026-08-27 10:34: *"we also need to get youtube going live stuff
too, go let the streaming activity work for youtube"*. The presence path was
already platform-agnostic; what was wrong was everything Twitch-shaped around
it.

| Key | Note |
|---|---|
| `black_bloc/golive.py:15` | `TWITCH` / `YOUTUBE` are constants because three modules compare against them (`platform_of`, `twitch_enrichable`, the cog's `TEST_STREAMS`) and a stray `"twitch"` in one of them would silently disable enrichment. |
| `black_bloc/golive.py:111` | ⚠️ **A `discord.Streaming` activity's `name` IS the platform when the stream has no title.** The library sets `platform = name` and then `name = details or name` (`discord/activity.py:530`), so `details` and `name` are the same string, and a title-less stream used to render `{title}` as literally "YouTube". The title is dropped when it equals the platform. Checked against the installed 2.7.1 source, not memory. |
| `black_bloc/golive.py:118` | `twitch_enrichable` is the one place that decides whether a Twitch lookup could be about a stream: unknown platform yes, Twitch yes, anything named no. `casefold` because `platform_of` returns whatever the gateway put in the activity, not a value we chose. |
| `black_bloc/golive.py:147` | `enriched` re-checks `twitch_enrichable` rather than trusting its caller — it is exported and `test_golive.py` calls it directly, so the guard has to live with the merge, not beside it. |
| `black_bloc/cogs/content/golive.py:538` | ⚠️ **The bug this whole change exists to fix.** `_enrich` fired for ANY presence stream whose member had a `/twitch link` row, so a Twitch-linked member streaming on YouTube got a Helix query and `enriched()` filled their YouTube announcement with Twitch game/title. Now a named non-Twitch platform never reaches Helix at all — the tests assert `stream_calls == []`, not just that the fields survived. |
| `black_bloc/cogs/content/golive.py:95` | `TEST_STREAMS` is keyed by platform name so `/golive test`'s choice list and its fake streams cannot drift apart — the `app_commands.Choice` list is built from the same dict. |
| `black_bloc/cogs/content/golive.py:922` | `/golive test` still prefers the caller's REAL stream when no platform is chosen; an explicit choice always wins, because picking "YouTube" while live on Twitch and being shown the Twitch one reads as a bug. |
| `black_bloc/cogs/content/golive.py:857` | `/golive status` gained a `• <name> on <platform>` line per open session, and the whole reply now carries `AllowedMentions.none()` — it interpolates display names, which are attacker-controlled (review checklist 11). |
| `black_bloc/storage/db.py:119` | `golive_sessions.platform` is additive: in `SCHEMA` for new files and in `ADDED_COLUMNS` for existing ones, nullable with no default, so old rows read `NULL` and `/golive status` says "an unknown platform". Schema version 11 → 12. Safe to ship without a data migration. |
| `black_bloc/api/tools/golive.py:72` | `platform` on the sessions row is the only `black_bloc/api/` change. `site/mock/contract.json` was deliberately NOT touched: both contract checkers assert that the LISTED keys are present and ignore extras, so adding the key there would have failed `site/mock/check.mjs` (the mock server does not serve it) for no gain. Whoever wires the column into `page-golive.js` adds it to the contract and the mock together. |

## site — theme tokens for the new shell (2026-08-27)

> Owner's ask, verbatim (2026-08-27 10:18): *"make sure that the other themes
> work and dont just change the background color, make sure it applies to all
> CSS"*. Built on branch `worktree-agent-a85ee9bc21984cdf9` cut from `main`
> @ `666dd8e`; commit `28472ed`.
>
> **Last verified: 2026-08-27 ~11:05** — every line number below was read off
> the file after the last edit. Measured against `site/mock/server.mjs` on
> port 8788 in Chrome, six themes × dark, on Settings and Moderation; the
> computed-style table is in this section. `node site/mock/check.mjs` clean;
> 1264 pytest tests pass; ruff clean.
>
> NOT verified: anything against the real API or live Discord — the mock only.
> ⚠️ Not in `main` yet; re-key this section on merge.

### What was actually wrong

`site.css` was the mock's px values written out longhand — ~64 raw `font-size`
declarations, `border-radius: 4px`/`999px`, `1px solid`, numeric
`font-weight`, `letter-spacing`, `text-transform`, control heights and focus
rings. Switching to Cyberpunk or Retro therefore repainted the palette and the
body face and left **every metric on the page at Discord's value**: the cards,
the pills, the nav items, the table rows, the controls and the whole type
scale. The estate contract had names for radii and borders but nothing for a
CONSOLE type scale (`--et-text-body` is the estate's 17px reading size, not a
14px dashboard), nothing for weights, nothing for label casing, nothing for a
control height.

### The 25 tokens that joined the contract

| Group | Tokens |
|---|---|
| console type | `--et-ui-xl` `--et-ui-lg` `--et-ui-md` `--et-ui-sm` `--et-ui-xs` `--et-ui-2xs` `--et-ui-line` |
| weight | `--et-weight-body` `--et-weight-medium` `--et-weight-strong` `--et-weight-heavy` |
| faces | `--et-font-nav` |
| labels | `--et-label-transform` `--et-label-tracking` `--et-label-weight` |
| shape | `--et-hairline-w` `--et-dot-radius` `--et-btn-radius` |
| control | `--et-control-h` `--et-control-h-sm` `--et-control-h-lg` `--et-focus-ring` |
| surface | `--et-card-shadow` `--et-table-stripe` `--et-row-hover` |

⚠️ **Every one is declared at all THIRTEEN declaration sites** — six themes ×
light/dark, plus apple's duplicated media-query dark — at
`estate-theme.css:416, 473, 527, 628, 690, 796, 861, 975, 1047, 1183, 1259,
1365, 1429`. `grep -c -- '--et-ui-xl:' site/public/assets/estate-theme.css`
returns **13** for each of the 25, and the contract comment at
`estate-theme.css:163` lists them (so a grep on the NAME rather than the
declaration returns 14). Declaring them in the dark blocks too is not
tidiness: `:root[data-mode="dark"]` is apple's stamped dark at specificity
(0,2,0) and it matches `<html data-theme="classic" data-mode="dark">` as well,
so a theme's own dark block has to restate anything it does not want apple's
value for.

### The value table (measured in Chrome, dark mode, `settings.html`)

| theme | nav item | card | pill (moderation) | page title | text input | Save button |
|---|---|---|---|---|---|---|
| **discord** | Inter 14px r4px | r6px b1px flat | JetBrains Mono 11px r999px UPPER | Inter 24px w600 | h32px r4px | r4px flat |
| classic | system-ui 15px r10px | r14px b1px shadow | system-ui 11px r999px UPPER | system-ui 26px w700 | h34.7px r10px | r10px flat |
| apple | -apple-system 15px r12px | r18px b1px shadow | -apple-system 11px r980px none | -apple-system 28px w700 | h34.7px r12px | **r980px** flat |
| cyberpunk | **Share Tech Mono** 16px r2px | r2px b1px shadow | Share Tech Mono 12px r2px UPPER | **Rajdhani** 26px w700 | h36px r2px | r2px flat |
| retro | **Luckiest Guy** 15px r7px | r10px **b2px** shadow | Luckiest Guy 12px r7px UPPER | **Bangers** 30px w400 | h37.3px r7px | r7px **shadow** |
| hearts | **Luckiest Guy** 15px r4px | r6px **b2px** shadow | Luckiest Guy 12px r4px UPPER | Luckiest Guy 28px w400 | h37.3px r4px | r4px **shadow** |

**Pass condition met**: discord is the mock's numbers exactly, and all FIVE old
themes differ from it on font-family, radius AND type size simultaneously.

### The gotchas, and the places Discord had to be protected

| Key | Note |
|---|---|
| `site/public/assets/site.css:709` and `:744` | ⚠️ **Table column heads are NOT label-treated.** The first cut ran them through `--et-font-label` / `--et-label-transform`, which put Discord's heads in JetBrains Mono caps. The mock reads `>When<` — sentence case, Inter, 12px, weight 600, no tracking — so the base rule takes the body face and `site.css:1298` gives cyberpunk, retro and hearts the shouting version instead. This is the one component where a theme's trick had to be opt-in rather than a token. |
| `site/public/assets/site.css:477` | `h2.sect-title` uses `calc(var(--et-label-tracking) / 2)`, because the mock's section titles are .04em where its pills and nav heads are .08em. A second tracking token would have been a 26th declaration in 13 places to express one halving. |
| `site/public/assets/site.css:531` | ⚠️ **`.chip-filter` deliberately has NO `min-height`.** Adding `var(--et-control-h-sm)` grew the mock's 25.3px filter chip to 28px — measured, not guessed. Its height is its own padding plus whatever type the theme sets. |
| `site/public/assets/shell.js:94` | `group.head.toUpperCase()` became plain `group.head`. Casing a label in JS is a decision no theme can undo, and apple's whole identity is that it does not shout; `.nav-head`'s `text-transform: var(--et-label-transform)` now decides. The rendered Discord page is unchanged because discord's value is `uppercase`. |
| `site/public/assets/site.css:274` | The page title took back `color: var(--et-heading-color)` and `text-shadow: var(--et-glow-title)`, which the Direction A cut had hard-set to `none`. Both are inert in discord and are what makes cyberpunk's SETTINGS glow yellow. |
| `site/public/assets/site.css:432` | `.statgrid` moved from `repeat(4, …)` to `repeat(auto-fit, minmax(9rem, 1fr))` so the Moderation strip can take a fifth tile. Measured: with four tiles the track widths are identical to the old rule (`543.5px` ×4), because auto-fit collapses the empty tracks and their gutters. |
| `site/public/assets/site.css:1285` | The `[data-theme=…]` blocks at the foot are the deliberate exception to "style against tokens, never against a theme". They carry BEHAVIOURS a token cannot: retro/hearts' press-into-shadow (`box-shadow: none` on `:active`), cyberpunk's notch (`clip-path`) on `.card`/`.stat`/`.tile`/`.table-scroll`/`.savebar` and its border-on-hover, and apple's flat chrome. `estate-theme.css` already carried the same shape for `.et-btn`/`.et-tile`; this is that treatment extended to the dashboard's own components. |
| `site/public/assets/site.css:854` and `:1199` | The dirty-row rail and the modmail message spine are `calc(var(--et-border-w) * 3)`, not `3px` — so retro's 2px ink grammar scales them instead of leaving a hairline rail inside a 2px panel. |

### How Discord was proved unchanged

An in-page harness swapped the two stylesheets between their `git show HEAD:`
copies and the new ones and diffed **55 selectors × 21 computed properties**.
After the fixes above the only differences left are three that cannot render:
`text-transform: uppercase` on `.side-wordmark` and `.nav-head` (whose text is
already uppercase — the HTML literal, and what `shell.js` used to do in JS),
and a `min-height` floor on `.searchfield` that sits below its natural
32.93px. Rendered width and height are identical on every sampled element, and
before/after screenshots of Moderation are indistinguishable.

## members page + /api/members (2026-08-27)

> Owner's ask, verbatim (2026-08-27 10:18): *"also show server users, server
> user count also somewhere in the moderation area."* Same branch; commit
> `feea8d9`.
>
> **Last verified: 2026-08-27 ~11:20** — 1264 pytest tests pass (15 new in
> `tests/api/tools/test_members.py`, plus the contract's new route),
> `ruff check .` clean, `node site/mock/check.mjs` reports **14 pages / 49
> routes**. All fourteen pages rendered in Chrome against the mock with no
> console errors and no horizontal page scroll.
>
> ⚠️ **NOT verified: anything against live Discord.** The chunking path
> (`guild.chunk()` when the cache is short of `member_count`), real avatars,
> real role colours and the real staff derivation have only been exercised
> against fakes. ⚠️ Not in `main` yet; re-key this section on merge.

| Key | Note |
|---|---|
| `black_bloc/api/tools/members.py:140` | The router is `prefix="/api"` with one `GET /members`, gated by BOTH `staff_dependency` and `reader_dependency` — the same pair `/api/mod/*` reads behind, so a stranger gets the 403 sentence and a hammering page gets the read bucket's sentence, never a bare status. It is read-only, so there is no guard check and no `web.*` action line. |
| `black_bloc/api/tools/members.py:148` | ⚠️ **`page` and `per_page` are typed `str`, not `int`, on purpose.** With `int` FastAPI answers 422 before the handler runs, so `?page=abc` from a stale bookmark becomes an error card instead of page 1. Every query parameter is read tolerantly and clamped: page ≥ 1, per_page 1–100 (default 50), and an unknown `filter`/`sort` falls back to `all`/`joined_desc`. |
| `black_bloc/api/tools/members.py:113` | ⚠️ **A member with no `joined_at` sorts LAST in BOTH directions.** The first cut sorted `(joined_at is None, joined_at)` and reversed the whole list for `joined_desc`, which put the undated members at the TOP — caught by the test, not by reading. Dated and undated are now partitioned and concatenated. |
| `black_bloc/api/tools/members.py:156` | Membership comes from the birthdays cog's `members_of` (`cogs/community/birthdays.py:214`), which chunks the guild once when the cache is short of `member_count` and logs rather than raising if it cannot — one home for "every member Black Bloc can see", not a second copy. `total` is `guild.member_count` (Discord's own figure) while `shown` is what the cache actually held; the two are reported separately rather than one pretending to be the other. |
| `black_bloc/api/tools/members.py:157` | `staff` is `settings_store.member_is_staff` against `store.staff_role_ids(guild)` — the same computed-permission derivation the sign-in gate uses (review-checklist item 21). ⚠️ A bot is never counted as staff even when it holds a staff role, because the strip's "Staff" number is a count of people. |
| `black_bloc/modcases.py:337` | `count_cases_for` is ONE grouped `IN (…) GROUP BY user_id` for the page's ids, never a query per row, and returns `{}` when the database is down — so the member list still renders with `—` in the Cases column instead of failing whole. |
| `black_bloc/api/tools/members.py:27` | Role colour leaves as `#rrggbb` or `null`, not Discord's int: a colour of 0 means "no colour" and must not render as black. The page tints from it. |
| `site/public/assets/page-members.js:59` | ⚠️ **Role chips carry their colour in a `--role` custom property, not a colour rule.** `style="--role: #e04a6d"` is per-row data; `site.css:648` reads it through `color-mix`, which is what keeps `site.css` at zero raw colours while every role still wears its own. |
| `site/public/assets/page-members.js:197` | ⚠️ **`keepTyping` exists because every keystroke rebuilds the card.** Search is server-side, so `onQuery` calls the page's `refresh()`, which replaces `#dash` and throws away the input being typed in. The caret is restored to the end of the box afterwards; without this the second character goes nowhere. |
| `site/public/assets/page-members.js:179` | The pager asks `shown >= per_page`, because the route reports `total` (the server) rather than a count of the filtered set. "N of M members" is likewise shown-of-server, which is the honest pair. |
| `site/public/assets/shell.js:58` | `memberTally()` mirrors `shellStatus()`: ONE `/api/members?per_page=1` per page load, awaited by both the sidebar count and Moderation's fifth stat. `.catch(() => null)` on purpose — a stranger gets 403 here and the shell must degrade to no count, never to a broken page. `forgetShellStatus()` clears it so Refresh re-reads. |
| `site/public/assets/page-moderation.js:57` | `moderation.html?member=<id>` is how a Members row hands over. The id is digits-only checked before it becomes `state.userFilter`, the "Only one member" section opens itself when one is set, and its note names the member (or the id, when no case on the page carries the name). |
| `site/public/assets/page-moderation.js:101` | `statTile` was extracted so the fifth stat can be an `<a>` to `members.html` while the other four stay `<div>`s; `site.css:425` gives `a.stat` the hover and focus ring a link needs. |
| `site/mock/server.mjs:78` | The mock's `ROSTER` keeps the original eight members' ids (the cases, birthdays and honeypot hits all point at them) and adds four bots and 48 fillers — three staff, two boosters, and five joined inside the last week so no chip is ever empty. ⚠️ The first cut computed those five join dates as `60 + at * 300` minutes, which is nine days, so "New this week" showed one row; measured through the endpoint, not read. |
## temp voice — the control panel in the voice chat (owner ask, 2026-08-27)

> The owner: *"also lets move the controls for the join to create from the
> #test channel into the channel txt of the voice chat that was made like the
> other bot does it"*. This is the FIRST widening of the test-mode gate since
> it was written, so the whole of it is here rather than spread across the two
> file sections above.

| Key | Note |
|---|---|
| `black_bloc/guard.py:23` | ⚠️ **An in-memory set, deliberately, and NOT a database read.** The gate sits on `http.send_message`, which is on the path of every message the bot will ever send; an `await` on SQLite there would put the database in front of all of Discord and turn one slow query into a bot that cannot speak. The set is rebuilt from `tempvoice_channels` by the reconcile that already runs at `cog_load`, at `on_ready` and every five minutes (`black_bloc/cogs/community/tempvoice.py:1392`), so a restart costs at most one reconcile before old panels work again — and losing it fails **closed**: a click lands on the refusal sentence, never on an unguarded send. |
| `black_bloc/guard.py:45` | `own_channel` / `disown_channel` take a channel OR an id for the same reason `_id_of` exists — the create path has the object, the reconcile and delete paths have only the row's `channel_id`. |
| `black_bloc/guard.py:60` | The one widening: a channel id Black Bloc **made itself** is speakable. Not "any voice channel", not "the whole category" — an id has to have been written into `tempvoice_channels` by this bot for it to be in the set, so the blast radius is exactly the channels the feature under test creates. |
| `black_bloc/guard.py:70` | ⚠️ **`allows_place` does NOT inherit the allowance, and that is why `_is_test_home` was split out of `allows_channel`.** It used to start `if self.allows_channel(channel)`, which would have silently widened the channel-DELETE gate the moment `allows_channel` grew. Speaking in a channel and deleting one are different questions; only the first moved. |
| `black_bloc/guard.py:94` | Only **component** interactions are allowed in an owned channel — the panel's buttons. A slash command typed in a temp channel is still refused, because nothing about moving the panel makes `/tempvoice setup` safe there. |
| `black_bloc/guard.py:15` | The type check is a free function because `allows_interaction` is the only caller and the test fakes need to be able to *not* have a `.type`. Note what this gate never sees: `ConnectionState.parse_interaction_create` sends types 2 and 4 to the command tree and dispatches components (3) and **modal submits (5)** straight to the view store, so `tree.interaction_check` — and therefore this method — is never consulted for a button or a modal. The button path is really gated by `panel_context`'s own `allows_channel` call (`black_bloc/cogs/community/tempvoice.py:761`); this allowance is the belt to that braces, and is what stops the tree refusing a component if discord.py ever routes one through it. |
| `black_bloc/cogs/community/tempvoice.py:1601` | The cog talks to the guard through two module helpers rather than reaching into `bot.guard` at five call sites, because the guard is `None` whenever test mode is off and every one of those sites would otherwise need the same `getattr` dance. |
| `black_bloc/cogs/community/tempvoice.py:1523` | ⚠️ **Ownership is recorded BEFORE the panel is posted**, immediately after the row is written. Post first and the guard refuses the send — the channel would exist with no controls in it, which is the exact failure this change was made to remove. |
| `black_bloc/cogs/community/tempvoice.py:1392` | The restore path. Every row whose channel still exists is owned again; a row whose channel is gone is deleted and disowned in the same breath (`:1383`). It is **incremental, not a wholesale replace**, so a reconcile that runs while the gateway reports no guilds cannot blank the set and silence every live panel for five minutes. |
| `black_bloc/cogs/community/tempvoice.py:1439` | Disowned only **after** Discord accepted the delete. A delete Discord refuses keeps the row (checklist 3) and must keep the allowance with it, or the panel in a channel that still exists stops answering. |
| `black_bloc/cogs/community/tempvoice.py:329` | ⚠️ **The bot needs its own overwrite on a spawned channel now that the panel lives inside it.** `owner_overwrites` builds a **hidden** channel by denying `view_channel` to `@everyone`, and a member who hid their last channel gets the next one created hidden — at which point Black Bloc could not see the chat it was about to post the panel into, and the create would end in `tempvoice.panel_failed` with no controls anywhere. `me` is the same allowance the lobby has had since Phase 3 (`:311`), so the two paths now build overwrites the same way. |

## go-live — embed with game art (2026-08-27)

Owner ask, 2026-08-27 ~10:50, with a screenshot of a streamcord announcement:
*"can we make our go live message show the streamer name and the game they're
playing instead of their avatar"*. Black Bloc posted the rendered sentence and
nothing else, so **Discord's own link preview** decided what the message looked
like — and for a `twitch.tv/<login>` link that preview leads with the
streamer's avatar. Nothing in the bot chose that picture; the fix is to stop
leaving the choice to Discord.

⚠️ **Keys in `black_bloc/golive.py`, `black_bloc/twitch.py`,
`black_bloc/cogs/content/golive.py`, `black_bloc/cogs/core.py` and
`black_bloc/settings_store.py` MOVED with this change and were NOT re-keyed** —
this section's own numbers are against `b00521c`, the sections above are not.
The next re-keying pass should map those five files from `74f06b5`.

| Key | Note |
|---|---|
| `black_bloc/golive.py:192` | ⚠️ **The embed sets an author NAME and no `icon_url`, and no thumbnail at all — that absence is the whole feature.** `set_author(name=…, icon_url=…)` is how every other bot puts a face on the line; leaving the parameter off is what removes the avatar the owner objected to. A test asserts `"icon_url" not in payload["author"]` rather than eyeballing the render, because the field is easy to add back by reflex. It is a pure function taking `member` as `Any` so the whole card can be built and asserted with no Discord objects in the test. |
| `black_bloc/golive.py:21` | Platform colours are the platforms' own brand colours (Twitch `#9146FF`, YouTube `#FF0000`), keyed by `casefold()` because `platform_of` returns whatever the gateway put in the activity rather than a value we chose — the same reason `twitch_enrichable` casefolds. Unknown platform falls back to Discord blurple. |
| `black_bloc/golive.py:82` | ⚠️ **`discord.Streaming` is a `BaseActivity`, NOT an `Activity`, so it has NO `large_image_url` property** — only the raw `assets` dict (`discord/activity.py:526`, checked against the installed 2.7.1 source). The property is tried first because `is_streaming` also accepts a generic `Activity` with `type == streaming`, which does have it; everything else is worked out from the asset string. **No network call happens here**, which is what keeps the YouTube no-fetch rule intact: a YouTube presence gets an image without Twitch, Google or anyone else being asked. An asset shape we do not recognise returns `None` rather than a guessed address, and `http://` is refused along with anything containing whitespace. |
| `black_bloc/golive.py:230` | `ended_embed` copies through `Embed.from_dict(embed.to_dict())` rather than mutating the fetched message's embed, and rebuilds the author line from the SESSION ROW (`_display_name` + `platform`) instead of parsing the live one — parsing "X is now live on Y!" back apart would break the moment the wording changed. The footer append is idempotent the same way `ended_text` is, because the end path can run twice (grace timer, then reconcile). |
| `black_bloc/golive.py:158` | `with_box_art` refuses to overwrite art that is already set, so the Helix answer can never clobber a presence image that was better. |
| `black_bloc/twitch.py:58` | ⚠️ **Twitch hands back art addresses with the literal text `{width}x{height}` in them** and expects the caller to substitute. `sized()` does it at the client boundary, so `TwitchStream.thumbnail_url` and `TwitchGame.box_art_url` are always usable strings and `golive.py` never has to know a Twitch URL template exists. `285x380` is the box-art size Discord renders well; `1280x720` the stream preview. |
| `black_bloc/twitch.py:192` | `get_games` is a separate Helix call because **the `streams` endpoint carries `game_id` and `game_name` but not the box art** — the art lives on `/helix/games` only. The per-process cache is keyed by game id and never expires: a game's box art does not change, and a server whose members play a dozen games settles into zero extra requests within an hour. Ids already known are filtered out before batching, so a repeat call sends nothing. |
| `black_bloc/cogs/content/golive.py:522` | ⚠️ **Four gates before Helix is asked anything**, and the platform one is the load-bearing one: `twitch_enrichable` is false for a named non-Twitch platform, so a YouTube stream never reaches the games endpoint even when it somehow carries a `game_id`. The `golive_embed` check is there so turning the card off also turns off the request that only exists to feed it. A `TwitchError` logs and returns the info unchanged — the announcement goes out without a picture rather than not going out. |
| `black_bloc/cogs/content/golive.py:551` | The embed rides the SAME `channel.send` the sentence always used, so `guard.py`'s patch of `http.send_message` covers it with no new gate; the explicit `allows_channel` check above it is unchanged. `embed` is passed through `**{…}` rather than as `embed=None` so a card-less post is byte-identical to what the old code sent. |
| `black_bloc/cogs/content/golive.py:485` | The end-of-stream edit still appends `END_SUFFIX` to the CONTENT and now rewrites the embed in the same `message.edit` — one call, one guarded `http.edit_message`, and the two halves of the message can never disagree about whether the stream is over. |
| `black_bloc/cogs/content/golive.py:91` | ⚠️ **`/golive test` fakes the art rather than fetching it** — `TEST_STREAMS` carries a real Just Chatting box-art address and a real ytimg thumbnail, and a test asserts `game_calls == []`. A preview command that spent a Helix request every time staff pressed it would be a rate-limit hazard for no gain. |
| `black_bloc/settings_store.py:104` | `golive_embed` defaults **true** — the owner asked for the card, so the card is what a server that has never touched the setting gets. Off restores exactly the previous behaviour (sentence only, Discord's preview back), which is why the "off" test asserts the full old string byte for byte. |
| `black_bloc/cogs/core.py:245` | ⚠️ **`golive_embed` was the 26th value-typed setting, and `/settings set-value` listed them all as `app_commands.choices` — Discord takes at most 25.** Adding the key would have made the command fail to register against the live API, which is a failure nothing in the test suite could have seen before (`tests/cogs/test_core.py` asserted `<= 25` and was the only thing that caught it). The key is now a plain `str` with an autocomplete, which filters as the user types and cannot overflow however many settings arrive later. An unknown key still ends at `coerce_value`'s sentence, so a typo gets an explanation rather than a stack trace. |

## chat — @-mention replies (2026-08-27)

> Owner ask, verbatim: *"we need to also add basic conversation and replies to
> the bot when people @ it and say hi, we can set up true covnersation"*, and
> F10 from the feature list: *"when the bot is at'd… hold some semblance of a
> conversation"* with *"personality @d"*. **Step 1 of two** — canned intents
> now, a real conversation backend later behind one seam. Built on branch
> `worktree-agent-aef7fecf62fef390c` off `main` @ `8b8f792`, commits `047f48d` and `e0aa2d6`.
> **Last verified: 2026-08-27** — `pytest -q` 1389 passed (60 new: 46 in
> `tests/test_chat.py`, 14 in `tests/cogs/content/test_chat.py`), `ruff check .`
> clean. ⚠️ **NOT verified against live Discord** — no gateway session has ever
> run this code; every claim below about what Discord delivers is read off the
> installed library, not measured on the wire.

### The intent finding, measured

| Key | Note |
|---|---|
| `.venv/Lib/site-packages/discord/flags.py:1256` | ⚠️ **A guild message that @-mentions the bot carries its `content` WITHOUT the privileged `message_content` intent**, which is what makes this feature possible at all. The library's own docstring lists the three exemptions verbatim: the message was sent by the client, the message was sent in direct messages, **the message mentions the client**. Restated at `message.py:2010` for `content` ("always be an empty string unless the bot is mentioned or the message is a direct message") and again at `:2019`, `:2069` and `:2100` for embeds, attachments and components. So the cog's mention gate is not only a behaviour choice — it is also the condition under which the text is guaranteed to arrive. |
| `black_bloc/intents.py:9` | ⚠️ **`message_content` was ALREADY on before this feature and was NOT touched.** Automod (`cogs/moderation/automod.py:419`) and the honeypot read every message, so the intent is load-bearing for them. The finding above still matters: if the intent is ever dropped — the portal toggle revoked, or a 100-guild verification refused — automod goes dark and **chat keeps working**, because a mention is exempt. That is worth knowing before anybody debugs a half-silent bot. |

### `black_bloc/chat.py` — the words, with no Discord in them

| Key | Note |
|---|---|
| `black_bloc/chat.py:542` | ⚠️ **`reply_for(text, member, bot)` is THE seam, and it exists to be thrown away.** Step 2 of F10 is an LLM backend; when it lands, this one function is what changes, and the cog above it — the mention gate, the mode, the cooldown, the guard check, the action row — does not. Its return type is `str \| None` rather than `str` precisely so a backend that declines (no key, budget spent, upstream 500) has a way to say "say nothing" without the cog learning what a provider is. Today it never returns `None`. `bot` is unused by the canned implementation except for the attendee count; it is in the signature because a real backend needs config and a client, and adding a parameter later would touch the cog. |
| `black_bloc/chat.py:382` | ⚠️ **Word-boundary matching, never substring** — the whole reason `has_phrase` pads both sides with spaces. `"hi" in "this"` is true and would have made every message containing *this*, *history* or *shipping* a greeting; `" hi " in " this "` is false. `tests/test_chat.py` pins six of those (`this`, `think`, `history`, `yolo`, `supply`, `helpful`) as `unknown`. |
| `black_bloc/chat.py:137` | ⚠️ **`ORDER` is the tie-break, and it is not the same as `INTENTS`' declaration order — it is load-bearing.** "hey you suck" contains both a greeting and an insult; insult wins, because reading an insult as a cheerful hello is the failure that makes a bot look oblivious. `what_can_you_do` sits above `help` for the same reason ("hey, what can you do?" is a capability question, not a cry for help), and `greeting` is last because its words are the shortest and the most likely to appear inside a longer question. |
| `black_bloc/chat.py:40` | `LOVE_MARKS` are checked against the RAW mention-stripped text, before `normalise` runs, because normalisation strips every non-alphanumeric character — a bare `❤` would otherwise normalise to the empty string and land in `unknown`. `<3` is in the same tuple for the same reason. |
| `black_bloc/chat.py:376` | Apostrophes are DELETED rather than turned into spaces, so `what's up` and `whats up` normalise identically and every phrase in `INTENTS` can be written one way. Both the ASCII `'` and the curly `’` phones type are handled; a phrase list that only knew the straight one would miss most iOS messages. |
| `black_bloc/chat.py:291` | ⚠️ **Every intent has at least five lines and no line exceeds 200 characters**, both asserted (`tests/test_chat.py:161` renders each line with a long name and a four-digit count before measuring, so the limit holds after interpolation rather than before it). The voice: warm, a little playful, cookout flavour, at most one emoji, and **never claiming to be a person** — several lines lean on being a bot on purpose. The `unknown` lines all point at `/help`, asserted, because the one thing a bot that did not understand must never do is leave the person with nothing to try. |
| `black_bloc/chat.py:355` | The attendee-flavoured lines are a SEPARATE table, offered only when a head count is available, so the base pool is never short of five and a cache that has not filled yet cannot produce "Keeping an eye on None cookout attendees". |
| `black_bloc/chat.py:504` | The count comes from `presence.human_count` rather than a second implementation — one fact, one home (checklist 15). It is the same figure the bot's own status line shows, so the two can never disagree. `status_guild(bot)` is the fallback for a DM, where the member has no guild. |
| `black_bloc/chat.py:483` | `rng` is an injectable `random.Random` rather than a global seed, so a test can pin a choice without leaving the process's RNG seeded for whatever runs next. |

### `black_bloc/cogs/content/chat.py` — the Discord plumbing

> ⚠️ **GONE in the 2026-08-31 re-key:** `black_bloc/cogs/content/chat.py:GONE (was :138)` — the construct each note names is no longer in the file; the note itself needs a decision.

| Key | Note |
|---|---|
| `black_bloc/cogs/content/chat.py:28` | ⚠️ **`mention_everyone` is checked explicitly even though `message.mentions` holds only USER mentions** and an `@everyone` therefore cannot put the bot in it. The check is cheap insurance against a library change, and it states the rule the owner would expect to read: an @everyone is not somebody talking to the bot. Role mentions need no check at all for the same reason — a role ping never lands in `mentions`. **v1 also ignores a reply-to-the-bot that does not mention it**; Discord puts the replied-to author in `mentions` only when "mention author" was left on, and treating a silent reply as a conversation turn would need the reply chain walked. Deliberate, and the obvious first thing to add. |
| `black_bloc/cogs/content/chat.py:111` | ⚠️ **The guard is asked BEFORE the reply, and a refusal is `log.debug` — never an error.** Under `TEST_MODE` the bot is @-mentionable in every channel it can see, so without this the guard's `http.send_message` patch would raise `TestModeViolation` and log `TEST MODE: refused to send…` at ERROR for every ping anywhere in the server. A log that screams on ordinary, expected, correct behaviour is a log nobody reads. The guard is still the enforcement — this check only stops the noise, and `tests/cogs/content/test_chat.py:232` asserts the reply is skipped with **zero** records at WARNING or above. |
| `black_bloc/cogs/content/chat.py:48` | ⚠️ **A DM has no guild, so it takes the REGISTRY'S default cooldown rather than none at all.** The first cut returned `0` for a missing guild, which meant one person could hold the bot in an unbroken back-and-forth in its own DMs — the exact thing the cooldown exists to stop, in the one place no staff would see it. `CHAT_COOLDOWN_SECONDS` is imported from `settings_store` rather than re-typed, so the DM figure and the default a server gets can never drift apart. Fixed in `e0aa2d6`; `tests/cogs/content/test_chat.py:22` pins it. |
| `black_bloc/cogs/content/chat.py:120` | ⚠️ **A cooled-down person gets NOTHING — no nag, no "wait a bit".** A rate-limit message is itself a message, so a bot that announces its own cooldown doubles the spam it was added to prevent. The window is per-user and in-memory: a restart forgives everyone, which is the harmless direction. |
| `black_bloc/cogs/content/chat.py:137` | ⚠️ **The cooldown is stamped only AFTER the reply actually went out**, and the action row is written after that. A reply that raised (permissions, a 429 the library gave up on, test mode from a path this cog did not anticipate) leaves the person un-cooled, so the next ping is answered rather than silently swallowed — pinned by `tests/cogs/content/test_chat.py:269`. |
| `black_bloc/cogs/content/chat.py:GONE (was :138)` | ⚠️ **`classify` is called a second time here, and that is deliberate rather than an oversight.** The brief said `reply_for` should be the only thing the cog calls; it is the only thing that produces WORDS. The intent label is a separate question — it is what the action row records — and keeping it out of `reply_for`'s return type is what lets the return type stay `str \| None` for the step-2 backend. `classify` is a pure function over one short string, so the second call costs nothing, and it keeps working as the log's label even after an LLM replaces `reply_for`. |
| `black_bloc/cogs/content/chat.py:25` | ⚠️ **Only an INSULT writes an action-log row.** Every reply is `log.info` in the bot's own log, but the action log is the staff-facing surface, and a row per "hi" would bury the moderation record it exists for. Somebody repeatedly poking the bot is the one thing staff might actually want to see — the row carries the actor and `details={"intent": "insult"}`, so it filters cleanly. The bot never escalates on its own: `insult` gets a good-humoured deflection and nothing else — no warning, no timeout, no reply to staff. |
| `black_bloc/cogs/content/chat.py:23` | `MessageType.default` and `.reply` only (checklist 23) — a pin or a thread-created system message carries the member as its author and would otherwise read as that member talking. Same tuple as `automod.py:59` and `honeypot.py:32`; it is a third copy of two enum values rather than a shared constant, which is the smallest duplication in the tree and the one worth revisiting if a fourth appears. |
| `black_bloc/cogs/content/chat.py:205` | `mention_author=False` AND `AllowedMentions.none()` together: the first stops the reply pinging the person it answers, the second stops anything interpolated into the text from pinging anybody at all (checklist 11). The only interpolated value today is the member's display name — which is attacker-controlled, and a nickname of `@everyone` is exactly the case that rule was written for. |

### Settings, and what `chat_mode` deliberately does NOT have

| Key | Note |
|---|---|
| `black_bloc/settings_store.py:83` | ⚠️ **`CHAT_MODES` is `("off", "on")` with NO `shadow`, unlike golive, honeypot, events, birthday and automod.** Shadow exists so a PUNISHING feature can be watched before it is armed — the log says what it *would* have done to somebody. A reply is not a punishment; there is nothing to review and nothing to regret, and a third mode would only be a way to leave the feature half-on by accident. |
| `black_bloc/settings_store.py:826` | ⚠️ **`chat_mode` defaults to `on`**, which is the opposite of every mode key that can act on a person. The owner asked for the bot to answer when pinged; a feature that ships off is a feature nobody sees. Under `TEST_MODE` the guard already confines it to `#mute-me-bot-test-spam` and DMs, so "on by default" cannot reach the server until the owner lifts test mode. |
| `black_bloc/settings_store.py:196` | The cooldown is clamped 5–600 seconds at the validator (checklist 22), with both reasons written as sentences a person can act on. Below 5 one person can hold the bot in a back-and-forth that fills a channel; above 600 most people never get an answer, which reads as a broken bot rather than a quiet one. `chat_mode off` is named in the floor's reason as the thing to use instead. |
| `black_bloc/cogs/core.py:236` | No new pressure on Discord's 25-choice ceiling: `/settings set-value` became an **autocomplete** at `8b8f792` when `golive_embed` became the 26th value key, so `chat_mode` and `chat_cooldown_seconds` join a list that filters as staff type. `tests/cogs/test_core.py:144` asserts the list is past 25 and that the autocomplete returns exactly 25. |
| `black_bloc/api/settings_api.py:53` | `namespace_of` derives `chat` from the key prefix with no override needed, so the dashboard grows a Chat section on its own. `tests/api/test_contract.py:85` checks named namespaces are PRESENT rather than that the set is exact, so nothing in `site/` had to change. |
| `black_bloc/api/status.py:122` | `chat_mode` ends in `_mode`, so the status API's feature-mode list picks it up automatically. There is no loop in this cog, so nothing appears under loop health — correctly, since there is nothing that can silently stop. |
| `black_bloc/bot.py:36` | Registered last in `COGS`. Order is not load-bearing; chat needs nothing from any other cog. |

### What was NOT verified

- **No live Discord session.** Every claim about what arrives on the wire —
  that a mention delivers `content`, that `message.reply` accepts both
  `mention_author` and `allowed_mentions`, that the guard raises where this
  cog expects it to — is read off discord.py 2.7.1's source and docstrings,
  not measured against the gateway.
- **The voice has not been read by the owner.** The lines are a first draft
  written to a brief (warm, playful, cookout flavour, no caricature, one emoji
  at most, never claiming to be a person); they are in `LINES` precisely so
  they can be rewritten without touching any logic.
- **No load or abuse testing** of the cooldown. It is an in-memory dict with
  no eviction; a server with tens of thousands of distinct people pinging the
  bot would grow it without bound. Not a concern at this server's size, and
  the fix (age out entries older than the window on write) is a few lines when
  it becomes one.

## site follow-up — controls not displays (2026-08-27)

> Built on branch `worktree-agent-a722f5273a3373659` off `188acf3`, twelve
> commits `adfb5e7`…`dab62c8`. Line numbers are as of `dab62c8`.

### The two live defects

| Key | Note |
|---|---|
| `black_bloc/api/assets.py:19` | ⚠️ **The build id is a sha256 over the BYTES of everything under `site/public`, prefixed with the package version** — `0.8.0-3f2a…`. Deliberately not a git sha (nothing in the container knows one without a Dockerfile build arg) and deliberately not an mtime hash (`docker COPY` carries mtimes in from the build context, so a rebuild from an unchanged checkout would not move it). Content is what cache-busting is actually about: the id moves exactly when an asset moves, which also means an unchanged deploy keeps its caches warm. ~30 small files, read once at startup. |
| `black_bloc/api/assets.py:28` | `stamp` rewrites `href="/assets/…"` / `src="/assets/…"` in the HTML as it is served, so nothing in `site/public/*.html` carries a version and nothing has to be regenerated. ⚠️ **It does NOT reach ES-module `import './api.js'` lines** — those resolve against the importing module's URL and drop the query. That is why the header matters more than the `?v=`: `no-cache` on every asset makes the browser revalidate, so a changed `api.js` is refetched even though its URL never changed. The stamp is the belt; the header is the braces. |
| `black_bloc/api/assets.py:32` | `SiteFiles` subclasses `StaticFiles` rather than putting a route in front of the mount: `get_response` has already resolved the file, so the HTML case is simply "the FileResponse's `.path` ends `.html`". HTML is re-read and returned as an `HTMLResponse` with `no-store`; every other static file keeps its ETag and gets `no-cache`. Favicon and fonts get `no-cache` too — a superset of what was asked for, one line instead of path arithmetic that would behave differently on Windows. |
| `black_bloc/api/server.py:35` | ⚠️ **`img-src` is the ONLY directive Discord's CDNs are added to.** Members' avatars were broken images under `img-src 'self' data:`. `tests/api/test_server.py` pins both halves: the exact `img-src` value, and that no other directive gained an `https:` source. `site/public/assets/page-members.js:96` still falls back to the initial-letter circle on the `img` `error` event, because a CSP is not the only reason a picture fails to load. |

### The sign-in cache — display only

| Key | Note |
|---|---|
| `site/public/assets/app.js:145` | Owner: *"every new page refresh is giving me the message, checking to see if you're logged in, that's too much."* The last successful `/api/auth/me` is kept in **`sessionStorage`** — per tab, gone when the tab closes, never on disk. ⚠️ **It is DISPLAY ONLY.** Every API call is still gated at the server by the session cookie; the cache decides only whether the "Checking…" panel is shown before the page paints. A cached `me` that is stale in the dangerous direction (no longer staff) cannot show anything: `page.load` calls the API, the API refuses, and `handle(error)` puts the gate back. |
| `site/public/assets/app.js:264` | The cached path renders first and re-checks afterwards, so `/api/auth/me` is the LAST request of a warm load instead of the first — measured in the mock: cold `me, status, members, links…`; warm `status, members, birthdays, …, me`. |
| `site/public/assets/app.js:237` | `verify()` drops the cache and shows the gate on any of: not staff, `staff_unknown`, expired, outage. `forgetMe()` also runs on sign-out. Only a `staff === true` answer is ever written. |
| `site/public/assets/app.js:176` | `refuseFor` is the one home for "is this `me` a gate rather than a dashboard", shared by the cold boot and the background re-check — the two were the same twenty lines twice. |

### Shared controls that replaced displays

| Key | Note |
|---|---|
| `site/public/assets/ui.js:1146` | `namespaceSettings(..., { omit })`. ⚠️ **A key with its own editor higher up a page is omitted from that page's accordion**, so it has ONE home per page: `golive_template` (Announcement wording), `birthday_template`, `tempvoice_name_template`, `tempvoice_creator_ids` (gone entirely — the lobby line replaced it), `automod_mode` and the two automod exemption keys. All of them still appear on the global Settings page, which is the registry view. |
| `site/public/assets/ui.js:1219` | `modeSwitch` is the Overview and Moderation rows' control: the settings editor's own three segments, but saving on the click because there is no docked bar out there. ⚠️ **On a refusal it puts the OLD value back and prints the bot's sentence** — verified against the mock's "Automod will not be armed while modlog_channel_id is unset". |
| `site/public/assets/page-overview.js:67` | The feature row is a `div` now, not an `a`. A button inside an anchor is invalid HTML and every click would navigate; the link is the name and the chevron (`site.css:625`, `.chip-go`). |
| `site/public/assets/ui.js:1175` | `fillTemplate` is the ONE home for filling a wording sample, and it copies `black_bloc/golive.py:render` exactly: known tokens filled, unknown ones left standing, `{{`/`}}` unescaped, and **null** when a stray brace means Python's `format_map` would have raised — which the pages report as "Black Bloc would use its own default instead" rather than pretending. |
| `site/public/assets/ui.js:1190` | `templateEditor` wraps one settings row as a textarea (`ui.js:883`, the client-side `longtext` type — the registry still calls these keys `text`, so no validator changed) plus the docked bar, and calls `paint(filled)` on every keystroke. Used by go-live, birthdays and temp voice. |
| `site/public/assets/ui.js:1271` | ⚠️ **`keepSaying`/`sayAgain` exist because a write that calls `refresh()` used to throw away its own outcome sentence** — the reload replaces the notice it was just written into. The sentence is parked under a name and put back on the notice the reload builds. |
| `site/public/assets/site.css:1101` | Owner: *"make month day year all on the same line."* Each `.field` claims an 11rem label column above 48rem, so three of them wrapped. `.formrow.dateline` stacks each label over its own box and shares the width three ways, dropping to two lines under 30rem. |
| `site/public/assets/site.css:877` | A wording key's textarea takes the rest of the settings row rather than the 218px slot a channel picker needs. Keyed on `textarea.area:not(.mono)` so the automod JSON box keeps the narrow slot. |

### The new routes, and one refactor they needed

| Key | Note |
|---|---|
| `black_bloc/cogs/community/tempvoice.py:197` | `forget_creator` was the cog's private `_forget`; the API needed it, so it is a module-level function and `_forget` is a one-line delegation. One implementation, two callers — `/tempvoice forget` and `POST /api/tempvoice/forget`. |
| `black_bloc/cogs/community/tempvoice.py:191` | ⚠️ **`FORGOTTEN` was defined twice** — `"forgotten"` at `:44` as the remembered-access marker, and the lobby sentence at `:185` shadowing it. Only luck kept it harmless: `remember_access` compares against `PERMITTED`/`BANNED` and never against `FORGOTTEN`. The sentence is `LOBBY_FORGOTTEN` now. |
| `black_bloc/api/tools/golive.py:105` | `POST /api/golive/links` reuses `clean_login` and `LINK_TAKEN`, and ⚠️ **says out loud that it did NOT check the channel exists on Twitch** (`"checked": false`). The slash command does a Helix lookup; a staff form has no member to ask, and claiming a check that was skipped is checklist item 10. |
| `black_bloc/api/tools/golive.py:149` | The opt-out is removed by **path parameter** (`DELETE /api/golive/optouts/{user_id}`), not a DELETE body as the brief's shorthand read — it matches `DELETE /api/golive/links/{user_id}` and `DELETE /api/birthdays/{user_id}`, and keeps a body off a method that mostly should not have one. |
| `black_bloc/api/tools/birthdays.py:154` | `POST /api/birthdays/{user_id}/optin` refuses 404 when nobody has that birthday, so the Wished button can never silently create one. |
| `black_bloc/settings_store.py:96` | ⚠️ **`golive_end_suffix` is ADDED but NOT YET READ.** `black_bloc/golive.py:328` still has its own `END_SUFFIX` constant and `ended_text` still uses it — another builder owned that file. The next session deletes `END_SUFFIX` and makes `ended_text` take the setting. Two homes for one string until then; `GOLIVE_END_SUFFIX` in the registry is the one that will survive. |
| `black_bloc/cogs/core.py:216` | The new key made `VALUE_KEYS` 26 long and Discord caps a choice list at 25, so `/settings set-value` autocompletes its key. ⚠️ **The main tree did the SAME conversion independently at `8b8f792`** for `golive_embed`; this branch conflicts there. Keep either — they differ only in the helper's name and in this branch's extra `UNKNOWN_VALUE_KEY` refusal for a typed key that is not in the list. |

### What was NOT verified

- **No live Discord and no deploy.** Cache-busting is proven in the mock and in
  `tests/api/test_server.py`, not against a real deploy; the CSP change is
  proven as a string, not by an avatar loading from Discord's CDN.
- **Browser checks were the mock server only**, Discord dark and the classic
  light theme, all fourteen pages: no console errors, no horizontal scroll, the
  gate never left showing.
- `golive_end_suffix` is shown in the go-live preview but **nothing reads it at
  runtime yet** (see above).

## role menus 2 — approval, expiry, reconciliation (2026-08-27)

Phase 9a, built on `main` at `8b8f792` in three commits: `341757a` (storage),
`940927c` (the cog), `7605730` (the API). Line keys are against those commits.
Nothing here has run against Discord.

### `black_bloc/rolegrants.py` — the words, the date maths, the ledger

| Key | Note |
|---|---|
| `black_bloc/rolegrants.py:38` | `LEDGER_ATTR` hangs the "Black Bloc just did this" book on the **bot object**, not on a module global — a module global would leak between tests and between two bots in one process. `was_ours()` (`:178`) POPS the entry, so one remembered change answers exactly once and a repeated `on_member_update` for the same role reads as by-hand, which is what it would be. |
| `black_bloc/rolegrants.py:39` | 30 s, because the gateway's `on_member_update` for an edit the bot made arrives within a second or two; longer would swallow a real by-hand change that happened right after ours. |
| `black_bloc/rolegrants.py:114` | `expires_at(0)` and `expires_at(-3)` are **None, not an error** — "0 days" is how staff say *no end date* in the approve modal and in `/rolemenu edit`. `positive_days` (`role_menus.py:339`) is the same rule for the menu column. |
| `black_bloc/rolegrants.py:125` | Extending starts from the LATER of now and the end it already had, so pushing back a grant that already lapsed does not hand out four days from a date in the past. |
| `black_bloc/rolegrants.py:188` | `create_request` returns None when one is already open rather than raising, so the caller answers with a sentence; the partial unique index (`storage/db.py:69`) is what makes that true under a race, not the check. |
| `black_bloc/rolegrants.py:270` | ⚠️ **`decide_request` is the whole race story.** It is `UPDATE … WHERE id = ? AND status = 'pending'` and returns `rowcount > 0`, so two staffers pressing Approve at the same instant cannot both act — the loser gets False and is told "somebody got there first". There is deliberately **no `asyncio.Lock`** here (the events cog has one): the conditional update is stronger, because it also holds across two processes. |
| `black_bloc/rolegrants.py:244` | Pending first, then newest first inside each group — the queue the dashboard shows and the order staff actually work in. |
| `black_bloc/rolegrants.py:382` | `record_added` writes **one open grant per member and role**: a second add while one is open leaves the first standing, so a member who picks a role twice does not get two clocks. |

### `black_bloc/storage/db.py` — schema 13

| Key | Note |
|---|---|
| `black_bloc/storage/db.py:69` | `role_requests_one_open` is a **partial** unique index (`WHERE status = 'pending'`), so a member may be denied and ask again later but may never have two open asks for the same role. Checklist 6. |
| `black_bloc/storage/db.py:407` | The three `role_menus` columns are in the `CREATE TABLE` **and** in `ADDED_COLUMNS`; a fresh file gets them from the first, an existing one from the second, and `_add_missing_columns` skips what is already there. `tests/storage/test_db.py` drops all three and reconnects to prove it. |

### `black_bloc/cogs/community/role_menus.py`

| Key | Note |
|---|---|
| `black_bloc/cogs/community/role_menus.py:28` | `from ... import rolegrants as grants` — the module namespace rather than thirty named imports. `rolegrants.STAFF` and this file's `STAFF_MODE` are both the string `"staff"` and mean different things (a grant's source vs a menu's mode); the prefix is what keeps them apart. |
| `black_bloc/cogs/community/role_menus.py:330` | `menu_value` swallows `KeyError`/`IndexError`/`TypeError`, so a `role_menus` row from before schema 13 — and every plain-dict fixture in the tests — still renders. `sqlite3.Row` raises `IndexError` for a column it does not have, a dict raises `KeyError`; both mean the same thing here. |
| `black_bloc/cogs/community/role_menus.py:699` | ⚠️ **`change_roles` is now the ONLY way this file edits roles.** It writes the ledger, calls `apply_diff`, and takes the ledger entries back out again when Discord refuses — a refused edit must not make the next real by-hand change invisible. `apply_diff` (`:681`) is untouched so the old tests still exercise it directly. |
| `black_bloc/cogs/community/role_menus.py:712` | The audit-log actor needs **View Audit Log** on the bot's own role. Without it the actor is `None` — never a guess. Checklist 10: a check that could not run says so. |
| `black_bloc/cogs/community/role_menus.py:730` | `rolemenu_approval_channel_id` falls back to `staff_channel_id` **at use**, not as a settings default, so changing the staff channel moves the requests with it and the setting reads "not set" rather than lying about a value it never stored. |
| `black_bloc/cogs/community/role_menus.py:740` | `card_target` returns *(where, why)*. Under TEST_MODE the approval channel is refused and the card goes to the test channel; the `why` lands in the `role.requested` log line as `"card": "test_channel"` and in the member's own ephemeral reply. Design §Approval flow 3. |
| `black_bloc/cogs/community/role_menus.py:751` | The card's only mention is the approver role, allow-listed by id. Every other send/edit in this file is `AllowedMentions.none()`. Checklist 11. |
| `black_bloc/cogs/community/role_menus.py:822` | Editing the card is the LAST thing every decision does and its failure is only logged — the role, the row and the DM have already happened. Checklist 12. `LookupError` is in the caught tuple because a fake/partial channel raises that rather than an HTTP error. |
| `black_bloc/cogs/community/role_menus.py:847` | `submit_request` is the one home for "a member asked": the open-request refusal, the `retry_days` cooldown, the row, the card and the `role.requested` line. The API does not call it — the dashboard never asks on somebody's behalf. |
| `black_bloc/cogs/community/role_menus.py:943` | ⚠️ **Order in `_approve_request`: decide, THEN add the role.** Winning `decide_request` first is what stops a double approval adding the role twice. The cost is that a Discord refusal after a won decision leaves the request `approved` with the role NOT on — that case logs `role.approve_failed` and the staffer is told to finish it with `/role grant`. No `role_grants` row is written, so nothing pretends the member has it. |
| `black_bloc/cogs/community/role_menus.py:914` | A request whose member has LEFT is refused with a sentence and stays pending, rather than being approved into nothing; staff deny it to close it. |
| `black_bloc/cogs/community/role_menus.py:1132` | `RequestButton` is a `DynamicItem` on `rolereq:(id):(approve|deny)`, registered in `cog_load` with `add_dynamic_items` — that registration, and nothing else, is what makes a card posted before a restart still work after one. Same shape as `events.py:DecisionButton`. |
| `black_bloc/cogs/community/role_menus.py:1107` | The Approve modal only appears when the menu HAS `expires_days`; a menu with no clock approves in one click. Blank days = the menu's own number, `0` = no end date, anything else = refused by name. |
| `black_bloc/cogs/community/role_menus.py:1249` | ⚠️ **`ask_staff` deviates from one sentence of the design.** `phase9-design.md` §Approval flow 1 says "deselecting the pending option withdraws"; the decision table says "picking it again withdraws". The posted select is ONE persistent view shared by every member, so it cannot show a per-member option as selected — deselecting is not an action anybody can take. **Picking a pending role again withdraws it**; omitting it does nothing. Omission would silently bin a request every time somebody picked something else. |
| `black_bloc/cogs/community/role_menus.py:1271` | Dropping a role you already hold is applied straight away even on an approval menu — approval gates getting a role, never giving one back. It closes the grant with `given_up`. |
| `black_bloc/cogs/community/role_menus.py:1194` | The select now reads its own menu row on every click (for `approval` / `expires_days`), so a menu deleted under a live panel answers `MENU_IS_GONE` instead of a traceback. |
| `black_bloc/cogs/community/role_menus.py:1455` | One hourly loop does both halves — expiry and the record sweep — because the design says "same loop". `loop_health("_expiry_loop")` (`:1436`) is what the health tab reads; `api/status.py:_loops` finds it by type. |
| `black_bloc/cogs/community/role_menus.py:1477` | ⚠️ **Expiry removes the role regardless of TEST_MODE.** Checklist 3: a reversal must not depend on the mode at reversal time, and the guard only patches sends and edits anyway. A Discord refusal logs `role.expire_failed` and leaves the grant OPEN for the next hour; a grant whose member has left is closed rather than retried forever (checklist 5). |
| `black_bloc/cogs/community/role_menus.py:1500` | ⚠️ **`reconcile_records` corrects RECORDS ONLY.** It never adds or removes a role — a row disagreeing with Discord means the row is wrong, because Discord is the record. It skips `guild.unavailable` (checklist 32) and logs `role.reconciled` only when something actually moved. |
| `black_bloc/cogs/community/role_menus.py:1523` | `on_member_update` filters through `was_ours` FIRST, so Black Bloc's own edits never come back as `role.changed_by_hand`. The list comprehensions pop the ledger even when the result is discarded, which is what keeps the book from growing. |
| `black_bloc/cogs/community/role_menus.py:1559` | A by-hand add of a role some **timed** menu owns opens a `manual` grant with **no expiry** — Black Bloc starts tracking it but will not take back a role it never handed out. `timed_menu_owns` (`:450`) is the join that decides. |
| `black_bloc/cogs/community/role_menus.py:564` | Deleting a menu marks its pending requests `withdrawn` — a request nobody can decide any more is not left waiting. |
| `black_bloc/cogs/community/role_menus.py:1419` | ⚠️ **`/role` is NOT in `command_visibility.HIDDEN_WHEN_OFF`.** `rolemenu_mode: off` stops members picking; staff handing a role out for a week has nothing to do with the panels and must keep working. |
| `black_bloc/cogs/community/role_menus.py:1703` | `/rolemenu edit` is an ADDITION to the design's slash surface (the design put the editor on the dashboard, which is 9b). Without it there is no way to turn approval on before 9b lands, and the owner's sweep starts with exactly that. |

### `black_bloc/api/tools/rolemenus.py` and `roles.py`

| Key | Note |
|---|---|
| `black_bloc/api/tools/rolemenus.py:268` | `GET /requests` is declared BEFORE `PUT /{name}`; the request routes have a segment count no menu route shares, so nothing shadows anything. |
| `black_bloc/api/tools/rolemenus.py:274` | The API and the button both go through `apply_request_decision`, so a decision made on the dashboard edits the Discord card, DMs the member and writes the grant exactly as a click does. The router adds only the `web.role.*` line on top. |
| `black_bloc/api/tools/rolemenus.py:173` | `wanted_days(..., blank=UNSET)` on PUT means "the page said nothing, leave the clock alone"; `blank=None` on POST means "a new menu with no clock". The `UNSET` sentinel lives in the cog (`role_menus.py:37`) so both callers use one object. |
| `black_bloc/api/tools/roles.py:118` | `POST /api/roles/grants` ADDS the role as well as writing the row, and refuses in words when Discord says no — a grant row without the role would be a lie the expiry loop would later act on. A role they already hold is not re-added; the clock just starts. |
| `black_bloc/api/tools/roles.py:195` | `DELETE` takes the role off first and only closes the row if that worked, so an "ended" grant never leaves the role behind. |
| `black_bloc/api/tools/roles.py:74` | Days that are not a number are refused by name rather than coerced to 0 — 0 means "never runs out" here, so a silent coercion would hand out a permanent role. |

### `site/` was deliberately NOT touched

`site/mock/contract.json` names the routes the checker walks; it does not
enumerate the app's routers, and `tests/api/test_contract.py`'s action-kind
assertion only sees kinds the seeded fixture actually produces. So the six new
routes and the five `web.role.*` kinds pass today with the contract unchanged.
**9b adds them to `contract.json`, the mock server and `action_kinds` alongside
the Requests / Timed roles sections that read them.**

### What was NOT verified

- **Nothing has run against Discord.** No request card has been posted, no
  button pressed, no DM delivered, no role added or removed by this code.
- The **audit-log actor** path is exercised only against a fake `guild.audit_logs`;
  the bot's role needs **View Audit Log** for it to name anybody in production,
  and nobody has checked whether it has that on Black in a Flash!.
- **Persistence across a restart is by construction, not by test** — the cards'
  buttons come back only because `cog_load` calls `add_dynamic_items(RequestButton)`.
- The **hourly loop has never ticked**; expiry and the sweep are tested by
  calling `run_due_grants()` / `reconcile_records()` directly.

## bot batch — end wording setting, mention noise, emoji skin tone (2026-08-27)

> Built on branch `worktree-agent-a7d9a7d2f6a9fada4` off `main` @ `a28e132`,
> commits `853aee3`, `ec7b345`, `046a54a`. **Last verified: 2026-08-27** —
> `pytest -q` 1453 passed (28 new), `ruff check .` clean. ⚠️ **NOT verified
> against live Discord** — no gateway session ran this code; every claim about
> what Discord accepts is read off discord.py 2.7.1's source.

### The stream-ended wording is one string again

| Key | Note |
|---|---|
| `black_bloc/golive.py:226` | ⚠️ **`END_SUFFIX` is GONE and `GOLIVE_END_SUFFIX` in `settings_store.py:37` is the only copy** — the note at `settings_store.py:95` predicted exactly this, and it is now discharged. `golive.py` already imported `GOLIVE_TEMPLATE` from the registry, so the import cost nothing; the constant is the parameter default of both `ended_text` and `ended_embed`, which is what makes "the registry default and the constant are the same object" literally true rather than a promise. |
| `black_bloc/golive.py:328` | `ended_text(text, suffix)` treats a blank suffix as *no suffix* rather than appending whitespace. The store cannot produce one — `coerce_value`'s `text` branch refuses a whitespace-only value — but the function is called with a store read, and a defensive branch is cheaper than a message that ends in a stray space if the registry ever grows a clear-to-empty path. `None` is handled for the same reason. |
| `black_bloc/golive.py:211` | ⚠️ **The embed footer DERIVES its marker from the same setting instead of keeping a second string.** `EMBED_END_FOOTER = "· stream ended"` was the second home; `end_marker` strips the leading separator characters (`END_TRIM`: spaces, em/en dash, hyphen, middot, pipe, comma, semicolon, colon) off the suffix, so the default ` — stream ended` still renders `Black Bloc · via Twitch · stream ended` byte for byte and a custom ` (over)` renders `· (over)`. The two halves of the message can no longer disagree about the wording, only about the punctuation in front of it. |
| `black_bloc/golive.py:216` | Idempotency moved with the words: `ended_footer` compares against the tail it is about to add, not against a fixed constant, because the end path runs twice (grace timer, then reconcile) and the suffix can change between the two. |
| `black_bloc/cogs/content/golive.py:492` | The store is read ONCE per edit and the same value is handed to both `ended_text` and `_ended_embed`. Reading it twice would let a `/settings set` landing between the two calls produce a message whose sentence and footer say different things — the failure the derivation above exists to prevent. |

### The "hi" command noise, and why the prefix was the fix

Measured in the Fly logs, 2026-08-27 18:40:55Z:
`discord.ext.commands.errors.CommandNotFound: Command "hi" is not found`,
once per @-mention that carried a word.

| Key | Note |
|---|---|
| `black_bloc/bot.py:45` | ⚠️ **`commands.when_mentioned_or("!")` made the MENTION ITSELF a command prefix**, so `@Black Bloc hi` was `<prefix><command>` to the prefix dispatcher and `hi` was looked up in `all_commands`. Nothing in the tree is a prefix command — `grep` for `@commands.command` and `bot.command` across `black_bloc/` returns nothing, and `bot.commands` is empty after every cog loads (`tests/test_bot.py`) — so the dispatcher had nothing it could ever match and every mention was a guaranteed miss. |
| `black_bloc/prefix.py:6` | ⚠️ **The prefix approach was chosen over an `on_command_error` that swallows `CommandNotFound`, because it stops the error being RAISED rather than catching it after.** Read off the library: `.venv/Lib/site-packages/discord/ext/commands/bot.py:1319` does `origin.content.startswith(tuple(prefix))`, and `startswith(())` is `False` for every string, so `get_context` returns early with `invoked_with` still `None`; `invoke` (`bot.py:1356`) then takes neither the `ctx.command is not None` branch nor the `elif ctx.invoked_with` branch and dispatches nothing at all. An error handler would still have built a `Context`, done a dict lookup and dispatched an event per mention, and it would have silently swallowed a real `CommandNotFound` the day somebody adds a prefix command. |
| `black_bloc/bot.py:45` | The old and new behaviour were **measured side by side** rather than reasoned about: with `when_mentioned_or("!")` a fake `<@1> hi` dispatched `('command_error', CommandNotFound('Command "hi" is not found'))` — the log line verbatim; with `no_prefix_commands` it dispatched nothing. `tests/test_bot.py` pins the second half (no dispatch, zero records at WARNING or above). |
| `black_bloc/config.py:42` | ⚠️ **`command_prefix` in the settings is NOT dead and was left alone.** `cogs/moderation/modmail.py:1038` reads it to ignore a staff message in a ticket channel that starts with `!` — i.e. one aimed at some other bot. It no longer has anything to do with how Black Bloc dispatches. |

### Skin tones — `black_bloc/emoji.py`

Owner ask, verbatim: *"Make black bloc use dark skin emotes"*.

| Key | Note |
|---|---|
| `black_bloc/emoji.py:19` | ⚠️ **`MODIFIER_BASE` is Unicode's `Emoji_Modifier_Base` list, not a guess at "hands and people".** Getting this wrong is the whole risk of the feature: appending U+1F3FF to an emoji that cannot wear it renders as the emoji followed by a loose brown square. Written as hex code points so the set can be diffed against the Unicode data file rather than squinted at. Deliberately absent and separately pinned by test: hearts, `⚠️`, `✅`, `→`, the honey pot — every glyph the bot uses as a status mark. |
| `black_bloc/emoji.py:41` | `toned` takes ONE emoji; `toned_text` (`:52`) sweeps a whole line. The line sweep is what the bot actually calls — a reply is a sentence, not an emoji — and having both keeps the single-emoji case available for a button label without a second regex. |
| `black_bloc/emoji.py:49` | ⚠️ **A variation selector (U+FE0F) is DROPPED when a modifier is added and KEPT when one is not.** `☝️` + dark is `☝🏿`, not `☝️🏿`: the modifier already forces the emoji presentation, and the three-code-point form is not a valid sequence. Tone `none` keeps the `️` so a bare `☝️` still renders as an emoji rather than a dingbat. |
| `black_bloc/emoji.py:41` | Toning is **idempotent and re-tonable**: an existing modifier is stripped before the new one is appended, so `toned_text` over an already-toned line swaps the tone instead of doubling it. Pinned, because the chat cog could grow a path that tones twice. |
| `black_bloc/emoji.py:60` | ⚠️ **`tone_for` never raises and never returns a value the store did not offer.** A DM has no guild and gets the default; a `store.get` that throws (database not connected — the same case `command_errors.py` exists for) gets the default; a stored value outside `SKIN_TONES` gets the default. A reply is cosmetic, and a bot that goes silent because it could not decide what colour a hand should be would be worse than a bot that waves in the wrong tone. |
| `black_bloc/settings_store.py:19` | ⚠️ **`settings_store` imports `emoji`, never the other way round.** `emoji.py` imports nothing from the package, which is what lets `chat.py`, `settings_store.py` and anything else take it without a cycle — `golive.py` already imports from `settings_store`, so an `emoji → settings_store` edge would have closed one. |
| `black_bloc/settings_store.py:841` | `emoji_skin_tone` defaults to **dark**, which is the owner's ask rather than a neutral choice. It is an `enum` with `SKIN_TONE_NAMES` as its choices, so `/settings set-value` autocompletes the six and `coerce_value` refuses anything else with the registry's own sentence. `namespace_of` (`api/settings_api.py:52`) derives `emoji` from the key prefix, so the dashboard grows an Emoji section with no change under `site/`. |
| `black_bloc/chat.py:542` | ⚠️ **The tone is applied at SEND time, and the `LINES` tables stay written bare.** A test asserts no line in `LINES` or `ATTENDEE_LINES` contains a modifier, because the moment somebody types a toned emoji into the table there are two sources of truth and the setting silently stops working for that line. Routing through `reply_for` also means the step-2 LLM backend inherits the toning for free. |

### The literal sweep — what actually changed

Census across `black_bloc/**` with `[\U0001F300-\U0001FAFF☀-➿←-⇿]`:
**47 occurrences, 32 distinct.** Exactly ONE of them can wear a skin tone.

| Literal | Where | Before → after |
|---|---|---|
| 👋 `U+1F44B` | `black_bloc/chat.py:127` (greeting line) | bare in the table; rendered `👋🏿` at send time |
| 🖤 ❤ ♥ 💜 💖 | `black_bloc/chat.py:40` (`LOVE_MARKS`), `black_bloc/chat.py:422` | unchanged — hearts take no modifier, and `LOVE_MARKS` is INPUT matching, not output |
| 🍯 | `cogs/moderation/honeypot.py:25` | unchanged — an object |
| ⚠️ ×5 | `events.py:209`, `automod.py:71`, `honeypot.py:84`, `modmail.py:175,599` | unchanged — status glyph, per the brief |
| → ×12 | `birthdays.py`, `automod.py`, `honeypot.py`, `modcmds.py`, `role_menus.py`, `api/tools/rolemenus.py` | unchanged — an arrow, not an emoji with a modifier |
| ✅ 📝 ⚠️ | `modmail.py:76-72` (`\N{...}` escapes) | unchanged — reaction status glyphs |
| 🧙 🥷 🧑‍🍳 🏎️ 🚚 … ×24 | `cogs/community/role_menus.py:44-113` | unchanged — role-menu option defaults are the member's/staff's choice, and that file belongs to the Phase 9a builder |

⚠️ **The mechanism is the deliverable, not the one literal.** The bot's copy
is almost entirely gesture-free today; the next line anybody writes with a 👍
or a 🙌 in it is toned by the setting without touching `emoji.py`.

### What was NOT verified

- **No live Discord session**, so nothing here was seen on the wire.
- **Skin-toned emoji in BUTTON labels were not exercised, because the bot has
  none to exercise.** The only `emoji=` on a component in the tree is
  `role_menus.py:476,532`, which is user-configured and off limits. Measured in
  the library instead: `PartialEmoji.from_str`
  (`.venv/Lib/site-packages/discord/partial_emoji.py:147`) matches the
  custom-emoji regex first and otherwise passes the WHOLE string through as
  `name` with `id=None` — so `👋🏿` survives as a two-code-point unicode emoji,
  and `str(PartialEmoji.from_str("👋🏿"))` round-trips unchanged (run, not
  inferred). **Whether Discord's API accepts it on a component is inference
  from that, not a measurement.**
- **`ended_footer`'s punctuation with an exotic suffix.** A suffix that is only
  separator characters (`" — "`) strips to empty and adds nothing to the
  footer, which is the safe direction but has not been seen rendered.
- **The `Emoji_Modifier_Base` list is Unicode 15-era and was transcribed, not
  generated.** The tests pin behaviour for the emoji the bot uses; a
  transcription slip in an unused code point would not be caught.

## site polish — neon cyberpunk, nav headers, level fields (2026-08-27)

> Three owner asks, built on branch `worktree-agent-a5af0aaec50e7dcd7` cut from
> `main` @ `a28e132`, three commits `b936b96` / `8424c60` / `6b7ab62`. Line
> numbers below are as of `6b7ab62`. ⚠️ **Not in `main` yet** — re-key this
> section on merge.
>
> **Last verified: 2026-08-27 ~13:00** — measured against `site/mock/server.mjs`
> on port 8791 in Chrome. `node site/mock/check.mjs` reports 14 pages / 54
> routes; `pytest -q tests/api` is 428 passed. All fourteen pages loaded with
> **no console messages at all** and **zero horizontal overflow at 1280 and
> 390 CSS px** (measured in same-origin iframes, `scrollWidth - innerWidth`,
> so the media queries evaluate against the real width). Nothing under
> `black_bloc/**`, `tests/**` or `site/mock/contract.json` was touched.

### 1 — cyberpunk goes neon

> ⚠️ **GONE in the 2026-08-31 re-key:** `site/public/assets/estate-theme.css:GONE (was :889)`, `site/public/assets/estate-theme.css:GONE (was :790)` — the construct each note names is no longer in the file; the note itself needs a decision.

Owner, verbatim: *"the theme needs more neon blue and othe neon colors"*.

| Key | Note |
|---|---|
| `site/public/assets/estate-theme.css:787` | SUPERSEDED BY `f10260d` (owner: "we look like a neon circus"): the neon pass this note described — electric blue `#3d8bff` as `--et-accent` with the old cyan demoted to a cyberpunk-own `--et-info` — was reverted; `--et-accent` is the estate's cyan `#05d9e8` again, `#3d8bff` appears nowhere, and cyberpunk's own `--et-info` declarations are gone (`--et-info` inherits the accent, as before the neon pass). Kept as the record of why the intermediate state existed. |
| `estate-theme.css:790` | `--et-accent-2` is neon magenta `#ff3df0` (light `#b01a8e`), and because `--et-heading-color: var(--et-accent-2)` was already the theme's rule, that one line moved the page titles, the wordmark, the focus ring and the chrome edge to magenta together. ⚠️ **Yellow `#fcee0a` was NOT retired — it kept `--et-warn` and only `--et-warn`.** As a status tone among neons it still reads as part of the set; as the heading colour it did not survive the blue. |
| `estate-theme.css:792` | `--et-ok` went `#39d98a` → `#2bff88` (light `#1d7a4b` → `#0c6f3e`), staying flagged INVENTED — the source site has no green anywhere and that has not changed. `--et-warn` light moved `#9a7b00` → `#7f6400` for the pill-tint contrast below. |
| `estate-theme.css:761` | The glow trio follows the new roles rather than being repainted independently: `--et-shadow`/`--et-shadow-lift`/`--et-glow` are blue, `--et-glow-title` magenta, and the ground haze's three ellipses are blue/magenta/green. `--et-card-shadow`, `--et-table-stripe` and `--et-row-hover` were already `var(--et-shadow)` / `color-mix(… var(--et-accent) …)`, so they followed with no edit. |
| `estate-theme.css:779` | `--et-hairline`/`--et-ink` are blue-shifted (`#2a2a3a` → `#232a45`, light `#c9cdd9` → `#c5cbdb`) and `--et-nav-active` went `#23233a` → `#16264a`, so the chrome sits in the accent's hue rather than in a neutral grey the neon has to fight. |
| `estate-theme.css:741` | ⚠️ **`--et-hue-1..6` were deliberately left alone.** They are the source site's SHELF hues (audio/books/games/universes/admin/ebooks) and `grep -c -- '--et-hue-' site.css status-shell.css` returns **0** — nothing the dashboard draws reads them, so repainting them would have been a change to the audiobook estate's palette with no effect here. |
| `site/public/assets/site.css:1356` | The wordmark is the one component that needed a rule rather than a token: `.side-wordmark` inherits `--et-fg` from `.side-brand`, so `[data-theme="cyberpunk"] .side-wordmark { color: var(--et-heading-color); text-shadow: var(--et-brand-shadow); }` sits with the other cyberpunk-scoped BEHAVIOUR overrides at the foot of the file. It is scoped to the theme, which is also the proof that no other theme moved. |
| **proof of blast radius** | `git diff -U0` on `estate-theme.css` for that commit produced **18 hunks, every one between old lines 718 and 866** — inside the cyberpunk comment block (717) and the two cyberpunk blocks (724–821 dark, 827–886 light). Retro starts at old 888. The only other file touched was the cyberpunk-scoped `site.css` rule above. |

**Contrast, measured (WCAG 2.x, sRGB, computed from the hexes — not eyeballed).**
Pill text is measured against its own tint, because `site.css:525` renders a
status pill as `color: TONE` on `color-mix(in srgb, TONE 14%, transparent)`
composited over the card.

| | body fg / page | body fg / card | muted / page | muted / card | accent / page | accent / card | btn ink on accent | heading / page | heading / card | ok pill | warn pill | danger pill | info pill |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **dark, new** | 15.83 | 14.89 | 6.07 | 5.71 | **5.95** | **5.60** | **6.12** | **6.74** | **6.34** | 10.19 | 10.88 | 4.53 | 8.20 |
| dark, old | 15.83 | 14.89 | 6.07 | 5.71 | 11.36 | 10.69 | 10.93 | 16.31 | 15.35 | 7.82 | 10.88 | 4.53 | 8.20 |
| **light, new** | 15.77 | 17.99 | 5.36 | 6.11 | **6.53** | **7.44** | **7.44** | **5.44** | **6.20** | 5.08 | 4.64 | 4.57 | 4.92 |
| light, old | 15.77 | 17.99 | 5.36 | 6.11 | 4.46 | 5.08 | 5.08 | 3.54 | 4.03 | 4.39 | 3.43 | 4.18 | 4.18 |

⚠️ **Every text role clears AA 4.5:1 in both modes, and every LIGHT figure is
better than the value it replaced** — light warn was 3.43 on its own pill and
is 4.64, light heading was 3.54 on the page and is 5.44. Dark accent and dark
heading fell (11.36 → 5.95, 16.31 → 6.74) because a blue and a magenta cannot
be as bright on near-black as cyan and lemon-yellow were; both still clear
4.5:1 as text, which is the bar that matters. The light tones were tuned
*to* the pill measurement: `#0f7a45` → `#0c6f3e`, `#8a6d00` → `#7f6400`,
`#00798f` → `#006c80`, each because the first value landed at 4.42/4.12/4.18
and pill text is 11–12px.

### 2 — the sidebar group headers

Owner: *"its hard to tell which ones are header and which are clickable. make
the headers bigger and maybe bold"*.

| Key | Note |
|---|---|
| `estate-theme.css:170` | Four tokens joined the contract — `--et-nav-head-size` `-weight` `-color` `-space` — and ⚠️ **every one is declared at all THIRTEEN declaration sites**: `estate-theme.css:432, 493, 551, 656, 722, 838, 908, 1026, 1102, 1242, 1322, 1432, 1500`. `grep -c -- '--et-nav-head-size:'` returns **13** (the contract comment names the group, not the declaration, so a grep on the name returns 14). |
| `estate-theme.css:432` | ⚠️ **The size is `var(--et-ui-lg)` at every site, and that is the point rather than a copy-paste.** It resolves to 16/17/18/19px per theme, which in every theme is ONE STEP ABOVE that theme's own nav item size (`--et-ui-md`, 14–16px) — the heading is bigger than the things under it by construction, not by a number somebody picked. |
| `estate-theme.css:840` | The per-theme values, and why each: apple `600` weight (**apple never shouts** — it is the theme whose `--et-label-transform` is already `none`); classic and discord `700`; cyberpunk `700` with `--et-nav-head-color: var(--et-accent)` — ⚠️ **the heads are the theme's ELECTRIC BLUE rather than `--et-fg`**, which is what keeps blue leading a page whose titles, wordmark and chrome edge are all magenta; retro and hearts take `var(--et-heading-weight)` = **400**, because Luckiest Guy ships one weight and synthetic bold fills its counters (the same reason `--et-heading-weight` exists at all). Space above is 20px for the three quiet themes and 22px for the three loud ones. |
| `site/public/assets/site.css:85` | ⚠️ **The rhythm moved from `.sidenav`'s flat `gap: 18px` onto the head's own `margin-top`** — "more space ABOVE the header" is a property of the header, and a container gap cannot express it (it also puts space above the FIRST group, which `site.css:95` `.nav-group:first-child > .nav-head { margin-top: 0 }` takes back so the container padding still owns the top edge). `site.css:73` gave `.side-scroll` the 16px bottom padding the two nav blocks used to carry between them. |
| `site.css:1293` | `.subnav-head` ("On this page") takes the same four tokens. It is the same kind of thing — a heading over a list of links — and giving it its own scale would be a second home for one decision. |
| **measured** | Chrome, all six themes × both modes: discord 16/700, classic 17/700, apple 17/600, cyberpunk 18/700 `rgb(61,139,255)` dark / `rgb(18,70,209)` light, retro 19/400, hearts 18/400 — every one bigger than its own nav item (16>14, 17>15, 18>16, 19>15) and at the theme's foreground where the items sit at `--et-muted`. |
| ⚠️ **departure from the mock** | `docs/info/mock-direction-a/Main.dc.html` draws these as 11px uppercase micro-labels, and the Direction A build copied that faithfully. The owner could not tell them apart from the links under them, so this is his call over the mock's, deliberately. |

### 3 — every side-by-side field group is level

Owner: *"make sure every set of text boxes that are next to each other are all
level, it seems to be around when there are subtext beneath or above the box
that pushes the default offline"*.

**The root cause was one declaration**: `.formrow { align-items: flex-end }`.
Fields were BOTTOM-aligned, so anything that changed a field's height moved
its control off the line its siblings sat on — a line of help text under the
box (the reported Role-menus instance), a textarea beside an input (modmail,
92px), or a switch beside a text box (automod).

| Key | Note |
|---|---|
| `site.css:1060` | Each `.field` in a formrow is a three-row grid — label / control / help — `grid-template-rows: auto minmax(var(--et-control-h), auto) auto` with `align-content: start`, and the row that used to bottom-align them is now `align-items: start`. The CONTROL row therefore starts at the same y in every sibling whether the rows above and below it are filled or empty. |
| `site.css:1085` | ⚠️ **The subgrid variant exists for the case the explicit rows cannot cover: a label that WRAPS.** Under `@supports (grid-template-rows: subgrid)` the formrow itself becomes the grid and the fields take `grid-template-rows: subgrid`, so the three rows are shared and a two-line label moves every sibling's control down with it. ⚠️ It is scoped `:not(.dateline):not(:has(> .bar))` — **a button bar sizes to its content and a grid track would give it a full field-width column**, which would visibly re-proportion the Role-menus option row (Role/Label/Emoji/Remove) and modmail's close row. Those rows stay flex and get the explicit rows. |
| `site/public/assets/ui.js:665` | `field()` tags its control `.field-control`. The CSS places the control BY NAME now instead of by "the child that is not a label, help or current" — a `:not()` chain that would silently mis-place anything added to a field later. |
| `site.css:997` | ⚠️ **`.input.switch { margin: 0 }` — the UA stylesheet's own `margin: 3px 3px 3px 4px` on a checkbox was the last 3px of drift** on Automod's Enabled / Window / Threshold / Timeout rows, and it survived the grid fix because it is margin, not alignment. Found by measuring, not by looking. |
| `site.css:1075` | A `.bar` in a formrow has no label above it, so top-aligning the row left the button floating level with the LABELS — 21.55px high. `margin-top: calc(var(--et-ui-xs) * var(--et-ui-line) + 4px)` is one label line plus the field's own row gap, **in tokens rather than a measured px**, so it stays right when a theme changes its type scale (it resolves to 21.55px in cyberpunk's 13px/1.35 and 22px in discord's 12px/1.5 — both matching the measured offset exactly). |
| `site.css:1089` | `.formrow.dateline` lost `align-items: end` for `start` and its child selectors became direct-child (`> .field`), so the shared rules and the dateline's own three-across sizing cannot fight. |
| `site/public/assets/page-golive.js:147` | The hand-built "Playing a game" field (a `div.field` with its own label and help built inline) goes through `field()` now. It was the only `.field` in the codebase not produced by the helper, and therefore the only one the shared fix would have missed. |

**The measurement, not an assertion.** `getBoundingClientRect().top` of every
control in every side-by-side group, at 1280px, in same-origin iframes:

| | groups found | misaligned > 1px | worst |
|---|---|---|---|
| before | 19 | **12** | modmail Name/Says **92.27px** · rolemenus Name*/Title/Description/Mode **40.15px** (the reported one) · automod Enabled/… **11.94px** ×7 · birthdays and moderation 1.06px |
| after | 28 (bars and the modmail ticket view now reachable) | **0** | every group spread **0.00px** |

Per group, after — identical in discord dark and cyberpunk light:

| page | group | spread |
|---|---|---|
| automod | Enabled ∣ Window, seconds ∣ Threshold ∣ Timeout, seconds | 0.00 |
| automod | delete ∣ warn ∣ timeout | 0.00 |
| birthdays | Month ∣ Day ∣ Year (the dateline) | 0.00 |
| moderation | What ∣ Reason | 0.00 |
| modmail | Name ∣ Says ∣ [Save snippet] | 0.00 |
| modmail (open ticket) | Send without your name ∣ [Send reply] | 0.00 |
| modmail (open ticket) | Close reason ∣ Close quietly ∣ [Close ticket] | 0.00 |
| rolemenus | Post in ∣ [Post] | 0.00 |
| rolemenus (editor) | Name\* ∣ Title ∣ Description ∣ Mode | 0.00 |
| rolemenus (editor) | Role ∣ Label ∣ Emoji ∣ [Remove] | 0.00 |

`*` = the field that carries help text. Go-live, events, honeypot, temp voice,
settings, members, audit, health and overview were swept too and have no
formrow with two or more controls in it.

### What was NOT verified

- **The mock only.** Nothing was run against the real API, a real deploy or
  live Discord.
- **Browser checks were Chrome only**, in discord dark, cyberpunk dark,
  cyberpunk light and retro dark. The other eight theme×mode combinations were
  verified by reading computed styles (the nav-head table above), not by eye.
- **The contrast figures are computed from the hexes, not sampled from
  rendered pixels.** Where a colour sits on a `color-mix` tint the composite
  was computed the same way the browser composites it; a screenshot sampler
  would be the stronger instrument and was not used.
- **The subgrid branch was exercised in a browser that HAS subgrid**, so the
  explicit-rows fallback path is proven only by the pre-subgrid reasoning and
  by the rows that are excluded from the subgrid rule (every formrow holding a
  `.bar`, which is 6 of the 10 groups above) — those measured 0.00px on the
  fallback rules alone.
- **No label was actually made to wrap.** The subgrid rule is the guard for
  that case; it was not provoked.

## go-live — stream-end edit is optional (2026-08-27)

> Owner ask, verbatim, 2026-08-27 12:30: *"Let's have stream end announcement by
> optional and off by default"*. Built on branch
> `worktree-agent-a61f076396720cea1` off `main` @ `a46b7ff`, commit `7e46a81`.
> **Last verified: 2026-08-27** — `pytest -q` 1573 passed (8 new; 1565 before),
> `ruff check .` clean. ⚠️ **NOT verified against live Discord** — no gateway
> session ran this code.

| Key | Note |
|---|---|
| `black_bloc/settings_store.py:652` | ⚠️ **`golive_end_mode` defaults to `off`, which CHANGES existing behaviour for every guild** — before this, an announcement was always edited when the stream ended. A server that liked the old behaviour has to ask for it (`golive_end_mode` = `edit`); nothing migrates, because a default flip is what the owner asked for and a silent per-guild backfill would make "off by default" untrue. Six existing tests in `tests/cogs/content/test_golive.py` had to turn the mode on to keep asserting what they always asserted — that is the blast radius, written down. |
| `black_bloc/settings_store.py:33` | The two mode names are constants (`GOLIVE_END_OFF`, `GOLIVE_END_EDIT`) and `GOLIVE_END_MODES` is built from them, rather than a bare tuple of literals like `GOLIVE_MODES` on the line above. The cog compares `golive_mode` against the literal `"off"`; `edits_on_end` deliberately does not, because `"edit"` would otherwise have a second home in `golive.py`. |
| `black_bloc/golive.py:312` | `edits_on_end` is a pure predicate on the mode string, so the decision is assertable with no Discord objects, and it is written as *only `edit` edits* rather than *`off` does not* — an unreadable value or a future third mode leaves the message alone, which is the safe half. |
| `black_bloc/golive.py:317` | ⚠️ **`end_details` puts `"announcement": "left"` in the log ONLY when the announcement was genuinely left alone, and says NOTHING in `edit` mode.** Claiming `"edited"` there would be review-checklist item 10 in miniature: the edit happens *after* the log line is written and can still fail (`_mark_ended` swallows the exception by design), so the log would be asserting something it had not seen. Absence of the key means the edit was attempted; a failure is already visible as the `go-live: could not mark message …` warning. |
| `black_bloc/cogs/content/golive.py:471` | The mode is read ONCE per end, before anything is written, and the same value is handed to both the log line and `_mark_ended` — the same discipline the `golive_end_suffix` note above records for the same path. Reading it twice would let a `/settings set` landing mid-end produce a log that says `left` beside a message that was edited. |
| `black_bloc/cogs/content/golive.py:484` | ⚠️ **The gate is in `_mark_ended`, i.e. AFTER `end_session`, `_remove_live_role` and `log_action`** — checklist item 12 (irreversible first, cosmetics last) and item 3 (reversal must not depend on the mode). `off` costs the announcement its suffix and nothing else: the session still closes, the Live role still comes off, `golive.end` is still logged. Both callers (`_end_live`, and `_close_session` for the reconcile/age-out path) go through it, so a mode flip cannot strand a session either way. |
| `black_bloc/api/status.py:47` | ⚠️ **`mode_keys()` used to mean "every key ending in `_mode`", and `golive_end_mode` is the first such key that is NOT a feature.** Left alone it would have grown the dashboard a features row titled *"Golive_end — off"*: `api/status.py:27` derives `feature` as `key[:-len("_mode")]`, and `site/public/assets/page-overview.js:35` sorts unknown features to the end rather than dropping them, so it renders. A human reading "golive_end · off" beside "golive · on" has been told something false about the feature. `NOT_A_FEATURE` is the explicit exclusion; `tests/api/test_status.py` pins both halves. |

### What was NOT verified

- **No live Discord session.** Nothing here was seen on the wire; the end path
  is exercised only against the fake channel in
  `tests/cogs/content/test_golive.py`.
- ⚠️ **The dashboard's go-live page still previews the ended wording
  unconditionally.** `site/public/assets/page-golive.js:140` reads
  `golive_end_suffix` and renders the "once the stream ends" preview with no
  idea that `golive_end_mode` may be `off`, so with the new default the preview
  shows an edit that will never happen. `site/` belongs to another builder and
  was deliberately not touched. The setting itself IS reachable there —
  `page-settings.js` renders every namespace the API reports, so the golive
  group grows a `golive_end_mode` dropdown with no site change.
- **`/golive status` does not print the end mode.** It does not print
  `golive_end_suffix` either, so this is the existing shape rather than a
  regression — but a staff member asking "why did the message not change?" will
  not find the answer there.

## role menus 2 — dashboard (9b) (2026-08-27)

> Phase 9's second half — the pages that read what 9a built — on branch
> `worktree-agent-abbf5f12160a08357` cut from `main` @ `a46b7ff`, five commits
> `1905b4d` (API), `487da10` (contract + mock), `b669207` (shared widgets and
> the level-field grid), `b284031` (the Role menus page), `ded42aa` (the
> Members tab). Line numbers are as of `ded42aa`. ⚠️ **Not in `main` yet** —
> re-key this section on merge.
>
> **Last verified: 2026-08-27 ~13:20** — `pytest -q` is **1584 passed**
> (1565 before, 19 new), `ruff check .` clean, `node site/mock/check.mjs`
> reports **14 pages / 61 routes** (54 before). Browser work was Chrome against
> `site/mock/server.mjs` on port 8788, discord dark and cyberpunk dark.
>
> ⚠️ **NOT verified: anything against the real API, a deploy or live Discord.**
> No panel has actually moved in a Discord channel; no member has been DM'd.

### ⚠️ The level-field grid was NOT in `main`, so this branch re-does it

The brief for 9b said to put the new fields "on the level field grid" and
pointed at § "site polish — neon cyberpunk, nav headers, level fields", whose
own banner says **⚠️ Not in `main` yet**. It still is not: `main` @ `a46b7ff`
has `.formrow { align-items: flex-end }` and a `field()` that does not tag its
control. The Role menus editor's new row proved it — the Channel field's help
wraps to two lines, so bottom-alignment pushed its control 16px above its three
siblings, measured.

So this branch implements the same fix, in the same places, deliberately: on
merge with `worktree-agent-a5af0aaec50e7dcd7` this is a **keep-either**
conflict in `site.css` and `ui.js`, not two different decisions.

| Key | Note |
|---|---|
| `site/public/assets/site.css:1059` | `.formrow` is `align-items: start` and each `.field` inside it is a three-row grid — `grid-template-rows: auto minmax(var(--et-control-h), auto) auto` with `align-content: start`. The CONTROL row therefore starts at the same y in every sibling whether the rows above and below it are filled or empty. |
| `site.css:1085` | ⚠️ **The subgrid variant covers the one case explicit rows cannot: a label that WRAPS.** Scoped `:not(.dateline):not(:has(> .bar))` — a button bar sizes to its content and a grid track would give it a full field-width column. |
| `site.css:1076` | A `.bar` in a formrow has no label above it, so top-aligning left the button level with the LABELS. `margin-top: calc(var(--et-ui-xs) * var(--et-ui-line) + 4px)` is one label line plus the field's row gap, **in tokens rather than a measured px**, so a theme with a different type scale stays right. |
| `site.css:997` | `.input.switch { margin: 0 }` — the UA stylesheet's own checkbox margin is the last few px of drift, and it survives an alignment fix because it is margin, not alignment. |
| `site/public/assets/ui.js:665` | `field()` tags its control `.field-control`, and the CSS places it BY NAME. Placing "the child that is not a label or help" is a `:not()` chain that silently mis-places anything added to a field later. |
| `site/public/assets/page-golive.js:115` | The hand-built "Playing a game" field goes through `field()` now. `grep "class: 'field'"` returned two hits before this and one after — it was the only `.field` in the codebase the shared fix would have missed. |
| **measured, not asserted** | `getBoundingClientRect().top` of every control in every side-by-side group, in same-origin iframes at **1280 and 390 CSS px**, all fourteen pages, discord dark and cyberpunk dark: **23 groups, every one spread 0.00px**, and `scrollWidth - innerWidth` is **0** on every page at both widths. ⚠️ At 390 a formrow WRAPS, so the measurement clusters siblings by their field box's top and compares only controls that share a visual line — a naive spread across a wrapped row reports 235px and means nothing. |

### The API this half needed (`1905b4d`)

| Key | Note |
|---|---|
| `black_bloc/api/tools/rolemenus.py:166` | ⚠️ **A queue row carried only `menu_id` — an internal row id — and NO menu row carries an id at all**, so the page could not name the menu a request came from, nor find its `expires_days` to offer on Approve. `menu_name` is resolved from one `list_menus` pass for the index and one `get_menu_by_id` for a decision. `user_avatar` joins it for the same reason the Members tab has one; both are display fields, and both are in `contract.json` so the two halves cannot drift. |
| `black_bloc/api/tools/rolemenus.py:282` | `wanted_target` is the post path's refusal ladder in one place — staff menu, no options, role menus off, no such channel, guard — walked by `POST /{name}/post` and by a channel change on `PUT /{name}`. It was inline in the post route before; there is one home for it now, not two. |
| `black_bloc/api/tools/rolemenus.py:446` | ⚠️ **`can_move` is asked BEFORE the edit is written.** The first cut applied the field edits, then moved, so a refused move left a menu whose title had changed under a sentence that said "nothing was changed". Caught in the browser, not by reading: role menus ship OFF in the mock, so the first channel change refused with `rolemenu_off` and the title had already moved. `site/mock/server.mjs:1219` splits `checkMove` out of `movePanel` for the same reason. |
| `black_bloc/api/tools/rolemenus.py:306` | The move takes the OLD panel down before the new one goes up, through `rolemenu_panels.unpost` — one home for "delete this panel and forget the message". An `unpost` that returns False is refused with `409 panel_stuck` rather than posting anyway: a menu in two channels hands out roles twice. |
| `black_bloc/api/tools/rolemenus.py:300` | An UNPOSTED menu is refused (`400 not_posted`) rather than posted from the editor. Posting is a deliberate, confirmed act with its own guard check; the editor's Channel field renders disabled with a sentence saying to use Post a menu, so the refusal is a page-fault backstop rather than something a person meets. |
| `black_bloc/rolegrants.py:331` | `expiring_for` is ONE grouped `IN (…) GROUP BY user_id, role_id` for the page's members, never a query per row — the same shape as `modcases.count_cases_for`, and `{}` when the database is down so the member list still renders. `MIN(expires_at)` because a role can carry more than one open grant and the soonest one is the one that matters. |
| `black_bloc/api/tools/members.py:39` | ⚠️ Only an **open** grant with an expiry reaches a chip. A closed grant is history, not a countdown; a grant with no end date is not "due". Both are pinned by tests, because the page renders "N d" from a truthy `expires_at` and would happily count down a role somebody no longer has. |
| `tests/api/conftest.py` | `WebMessage.delete()` was added — the fake had `edit` and `pin` but nothing to delete with, and moving a panel is the first API path that deletes a message it posted. |

### The Role menus page (`b284031`)

| Key | Note |
|---|---|
| `site/public/assets/page-rolemenus.js:380` | Requests sits **above** Menus, pending first as a card each, then a shut `foldout` of what was decided. The section head's count is the PENDING count, not the row count — a queue's number is how much work is left in it. |
| `page-rolemenus.js:299` | ⚠️ **The days box only exists when the MENU has an `expires_days`.** With one, Approve sends what is in it (blank or 0 = no end date); without one, there is no box and no `days` key, so the API uses the menu's own answer. Offering a clock on a menu that has none would invent policy in the page. |
| `page-rolemenus.js:199` | `channel_id` is only put in the PUT body when the menu is POSTED and the pick actually differs. An unposted menu's Channel select is disabled with `CHANNEL_UNPOSTED`, so nobody meets the API's `not_posted` refusal in normal use. |
| `page-rolemenus.js:94` | Role colours come from `refRoles()`, which reports Discord's **int**; the Members route reports a **hex string**. `ui.js:343 hexColour` takes either, so one `roleChip` serves both and `site.css` keeps its no-raw-colour promise (the value travels as `--role`). |
| `page-rolemenus.js:400` | The Ends cell says three different things and never guesses: `expires in N days` for an open clock, `no expiry` for an open grant without one, `ended <ago> · <reason>` for a closed one. A clock already past reads `overdue by N days` rather than a negative. |
| `page-rolemenus.js:84` | `rolemenus.html?member=<id>` narrows Requests and Timed roles to one person, with a banner naming them and a link back — the same handover shape `page-moderation.js:57` uses. The filtering is client-side even though `/api/roles/grants` takes a `user_id`, so the two sections and the banner all read one fetch. |
| `page-rolemenus.js` outcomes | Every write parks its sentence with `keepSaying` and the reloaded section puts it back with `sayAgain` — without it a write that calls `refresh()` throws away the notice it was just written into. Three parking names: `menus`, `requests`, `timed`. |
| `site/public/assets/ui.js:308` | ⚠️ **`foldout` is deliberately NOT a nested `section()`.** `layout.js` builds the "On this page" rail from `section.sect`, so a fold inside a section would appear there as a place you can navigate to, which it is not. |
| `site/public/assets/shell.js:64` | `requestTally()` mirrors `memberTally()`: ONE `/api/rolemenus/requests?status=pending` per page load, `.catch(() => null)` so a stranger's 403 degrades to no badge rather than a broken shell. ⚠️ **An empty queue shows NOTHING, not a zero** (`shell.js:66`) — a zero is a number somebody has to read and then decide not to act on. |
| `site.css:144` | The waiting count is `--et-warn` and bold where the Members tally is muted, because they are different kinds of number: one is a tally, the other is work. |

### The Members tab (`ded42aa`)

> ⚠️ **GONE in the 2026-08-31 re-key:** `site/public/assets/site.css:GONE (was :733)`, `site/public/assets/site.css:GONE (was :618)` — the construct each note names is no longer in the file; the note itself needs a decision.

| Key | Note |
|---|---|
| `site/public/assets/page-members.js:59` | A chip wears `· N d` when its role has an open grant with an expiry; the full date is the title. `untilWhen().days` is used rather than re-deriving, and a clock already past reads `due` instead of a negative day count. |
| `site/public/assets/page-members.js:88` | ⚠️ **The row is a `div` now, not an `a`.** It carries two destinations — the name to `moderation.html?member=`, the chevron to `rolemenus.html?member=` — and an anchor inside an anchor is invalid HTML whose every click lands on the outer one. Same reasoning as `page-overview.js:67`. `site.css:GONE (was :733)` gives `.grid-row.rowlink` the hover the anchor used to have and each link its own focus ring. |
| `site.css:GONE (was :618)` | `.role-chip-note` is `flex: none`, so the clock is never the part that gets squeezed out when the role's name is long — the NAME ellipsises instead. |
| `site/mock/server.mjs:1051` | ⚠️ **The mock's two open grants were moved onto roles their member actually holds in `ROSTER`.** The first cut put a clock on Casey's `Live now`, which Casey does not have, so `expiryOf` matched nothing and the chips rendered with no countdown — the page looked correct and was testing nothing. Found by looking at the rendered row, not by reading the fixture. |

### The contract and the mock (`487da10`)

| Key | Note |
|---|---|
| `site/mock/contract.json` | The seven 9a routes joined it, so `check.mjs` and `tests/api/test_contract.py` both walk them (54 → 61 routes), and `approval` / `expires_days` / `retry_days` are **required** keys on every menu payload rather than extras a page may or may not get. |
| `site/mock/server.mjs:487` | The mock's menus grew an `id`, because a request row's `menu_id` has to point at something. `runner-status` is the approval-gated, seven-day menu the owner's sweep describes. |
| `site/mock/server.mjs` fixtures | Two pending requests, one approved, one denied with a reason; five grants — one two days from its end, one 29 days out, one with no clock, one expired, one ended by staff. ⚠️ **Every state the page has to draw exists in the seed**, so nobody has to press a button before the page can be looked at. |
| `site/mock/check.mjs` | `checkActionKinds` now denies a request and ends a grant, so the five new `web.role.*` kinds are proven SPELLED that way rather than merely listed in `action_kinds`. `tests/api/test_contract.py` does the same against the real routers. |
| ⚠️ **a checker blind spot** | `/api/members`' contract entry checks `rows.members`, and the checker's `rows` only descends ONE level — so `roles[].expires_at` is **not** covered by either half of the contract. It is covered by `tests/api/tools/test_members.py` instead. Deepening `rows` is a checker change, not a shape change, and was left alone. |

### What was NOT verified

- **The mock only.** Nothing ran against the real API, a deploy or live Discord.
  No panel has moved in a real channel, no member has been DM'd, and the
  approval card in Discord has never been edited by a dashboard press.
- **Browser checks were Chrome, discord dark and cyberpunk dark.** The other
  ten theme×mode combinations were not looked at; the new CSS is token-only
  plus one `[data-tone]` hook, so it inherits, but that is inference.
- **Contrast of the new pieces was not measured.** `.role-chip-note` and the
  warn-toned nav count reuse `--et-muted` / `--et-warn`, whose figures are in
  § "site polish", but no sampler was run here.
- **B5–B7 in `docs/info/site-feature-audit.md` are still open.** Un-post, seed
  and staff-assign were not built and were not in this brief; the audit rows
  are unchanged.

## go-live — the wording section owns the end mode (2026-08-27)

> The follow-up to § "go-live — stream-end edit is optional", which left two
> things open: the dashboard previewed the ended wording whether or not it
> would ever be posted, and `/golive status` did not print the mode at all.
> Built on branch `worktree-agent-ab2b602b0d5849e79` cut from `main` @
> `271b42a`, two commits `607d268` (the bot) and `2e4f58f` (the site). Line
> numbers are as of `2e4f58f`. ⚠️ **Not in `main` yet** — re-key on merge.
>
> **Last verified: 2026-08-27 ~15:20** — `pytest -q` **1596 passed** (1592
> before, 4 new), `ruff check .` clean, `node site/mock/check.mjs` **14 pages
> / 61 routes, all keys present**. Browser work was Chrome against
> `site/mock/server.mjs`, discord dark, both modes flipped in both directions.

| Key | Note |
|---|---|
| `black_bloc/golive.py:321` | ⚠️ **`end_summary` never calls an unreadable mode `off`.** It is written the same way `edits_on_end` is — *only `edit` quotes the wording* — but the other branch prints the STORED value beside the outcome (`wibble (left as posted)`), not the word `off`. Saying `off` there would assert a value nobody stored, which is the same lie as `end_details` claiming `"edited"` would have been. With the two real values it reads exactly `off (left as posted)` and `edit (" — stream ended")`. |
| `black_bloc/cogs/content/golive.py:860` | The line sits directly under `**mode**`, because "is go-live on" and "does the announcement change when the stream ends" are the pair a staffer holds in their head at once. Both halves are one `store.get` each read at print time — there is no state to keep in step here, unlike the end path at `:462`, where the mode must be read once and handed to both the log line and the edit. |
| `site/public/assets/page-golive.js:118` | ⚠️ **`showEnd` is the only thing that decides what the foot of the preview card says**, and it is called from exactly two places: once at build time and once from the switch's `onSaved`. Repainting inside `templateEditor`'s `paint` instead would have tied the MODE's display to a keystroke in the wording textarea. |
| `site/public/assets/page-golive.js:136` | The switch is `modeSwitch`, the same control the Overview and Moderation rows use, so `golive_end_mode` is written by `saveSetting` on the click and gets the shared refusal behaviour (old value back, the bot's own sentence). ⚠️ **Its `onSaved` deliberately does NOT call `refresh()`** the way `linkCard` and `optoutCard` do: a page reload here would rebuild the wording card and throw away an unsaved edit sitting in the template textarea. It repaints locally, which is also why this is the one write on the page needing no `keepSaying`. |
| `site/public/assets/page-golive.js:114` | Three outcomes, not two. A missing `endSpec` → the sentence says the bot did not report a `golive_end_mode` key and **no switch is rendered** — the same shape `wordingSection` already used for a missing `golive_template`, and checklist item 10: a page that could not read the mode must not claim announcements are left as posted. |
| `site/public/assets/page-golive.js:148` | The switch is a second `field()` in the SAME `.formrow` as "Playing a game", so it lands on the level-field grid for free (`.seg` is tagged `.field-control` by `field()`). **Measured at 1280px: control spread 0.00px, label spread 0.00px, help spread 0.00px** — a `<div class="seg">` and an `<input type="checkbox">` are very different heights and the grid rows still line them up. At 390px the two fields stack (`site.css:1031` gives each field the full width under the breakpoint), which is the wrap every other formrow does rather than a misalignment. |
| `site/public/assets/page-golive.js:261` | `golive_end_mode` joins `golive_template` in the page's `omit` list — it has its own editor higher up now, so one home per page (`ui.js:954`). It is still on the global Settings page, which is the registry view; both halves verified in the browser. |
| `site/mock/server.mjs:244` | The mock had `golive_end_suffix` but never `golive_end_mode`, so the switch had nothing to render against. Added with the registry's own choices and default (`off`), and the suffix's help text was brought up to the registry's, which now says the suffix is only used when the mode is `edit`. |
| `site/mock/server.mjs:433` | ⚠️ **`NOT_A_FEATURE` is a SECOND home for `api/status.py:27`'s tuple, and deliberately so** — the mock is a separate program in a separate language and cannot import it. Without it the mock's `statusBody` (`:550`, `key.endsWith('_mode')`) would have grown the Overview a *"Golive_end — off"* feature row the real API never reports, leaving the mock wrong in exactly the way the real code was fixed not to be. Verified: `/api/status` lists eight features, none of them `golive_end_mode`. |

### What was NOT verified

- **No live Discord.** `/golive status` is exercised only against the fake
  interaction in `tests/cogs/content/test_golive.py`; nobody has read the new
  line in a real ephemeral reply.
- **No deploy and nothing against the real API** — every browser check was the
  mock.
- **Chrome, discord dark only.** No CSS was added at all (the switch reuses
  `.seg` and `field()`), so the other themes and light mode were reasoned about
  rather than looked at.
- **The `endSpec`-missing branch was not provoked in a browser.** The mock
  always reports the key now, so that path is proven by reading the code, not
  by running it.

## polls (10a) (2026-08-27)

> Phase 10a of [`phase10-design.md`](phase10-design.md): native Discord polls
> wrapped by Black Bloc. The panel surface (anonymous, hide-until-close, date
> slots > 10), recurrence and the dashboard page are 10b. Built on branch
> `worktree-agent-aa83500e6aae1280f` cut from `main` @ `6e08223`, four commits
> `033e1c7` (storage) → `a0fe975` (pure module + settings) → `d3d1234` (cog) →
> `09d8654` (API + contract + mock). Line numbers are as of `09d8654`.
> ⚠️ **Not in `main` yet** — re-key on merge.
>
> **Last verified: 2026-08-27** — `pytest -q` **1738 passed** (1596 before,
> 142 new), `ruff check .` clean, `node site/mock/check.mjs` **14 pages / 68
> routes, all keys present**. ⚠️ **Nothing has run against Discord: this code
> has never posted a poll.**

### The two questions the brief said to measure first

**1. Does `<t:…>` render inside a poll ANSWER label?**
⚠️ **Still unknown, and it cannot be settled offline.** `PollMedia.to_dict`
(`discord/poll.py:88`) sends the label as a bare `{"text": …}` with no escaping
and no validation, and neither `poll.py` nor the developer docs say a word about
markdown in answers — grepping the whole file for `markdown`/`escape` returns
nothing. So the library will happily **send** one; whether the **client renders**
it is a client-side question that only a posted poll answers. It does not block
10a (no v1 kind generates a date label), but **10b must post one in the test
channel before designing date labels around it.** Read: `discord/poll.py:68-105`
and `:594-625`.

**2. Which poll vote events does discord.py 2.7.1 fire, and on which intent?**
**The raw pair always; the non-raw pair only sometimes.** `state.py:1739` and
`:1757` dispatch `raw_poll_vote_add` / `raw_poll_vote_remove` unconditionally,
then dispatch `poll_vote_add` / `poll_vote_remove` **only** `if message and user`
(`:1752`, `:1770`) — i.e. only while the message is still in the cache AND the
user resolves. A poll that has been open for a day fails both tests. ⚠️ **So the
cog listens to the RAW events only**; listening to both would double-count every
vote. Intent: `guild_polls` = `1 << 24`, `dm_polls` = `1 << 25`
(`discord/flags.py:1358`, `:1375`), **not privileged and already on** —
`black_bloc/intents.py:7` calls `Intents.default()`, which is everything but
presences / members / message_content. **No developer-portal change, no
re-invite.** Read: `discord/state.py:1739-1774`, `discord/flags.py:1342-1390`,
`discord/raw_models.py:527-556`.

### `black_bloc/polls.py` — the rule book, with no gateway in it

| Key | Note |
|---|---|
| `black_bloc/polls.py:89` | The status machine is `draft → pending_review → open → closed → archived`, with `denied` and `cancelled` as the two ways out. ⚠️ **`cancelled` transitions to `archived` as well as `closed` does** — a cancelled poll still occupies a row and still gets a `closed_at`, so the nightly sweep must be able to tidy it away. Only `denied` and `archived` are terminal. |
| `black_bloc/polls.py:277` | `NeedsPanel` is a `ValueError` **carrying the sentence**, not a flag. That is the whole shape of decisions 5 and 6: a poll asking for anonymity or hidden results is **refused in words**, never quietly downgraded to a public one. Downgrading is the failure mode that matters here — "anonymous" that isn't is a lie to every voter. |
| `black_bloc/polls.py:503` | `surface_for` checks in one deliberate order: unknown kind → panel-owned kind → anonymous → hide-until-close → more than ten options. The first thing that needs the panel is what the person is told about, so a poll asking for two impossible things does not have to be submitted twice to learn both. Every branch ends with the same clause, `NEXT_UPDATE` (`:164`), so the promise reads identically wherever it surfaces. |
| `black_bloc/polls.py:303` | `validate` returns a **sentence or None**, never raises, because it is the fast path and every caller answers with it directly. It catches the four measured native limits (question 300, label 55, at least 2 answers, whole hours 1–768) plus case-folded duplicate labels — two identical answers split a vote and no reader can tell them apart, so it is refused rather than posted. |
| `black_bloc/polls.py:326` | `whole_hours` rejects `bool` before `int` on purpose: `True` is an `int` in Python and would otherwise be read as a one-hour poll. |
| `black_bloc/polls.py:550` | `bar` divides by the **total**, and a poll nobody has voted in has a total of 0 — hence the explicit zero branch rather than a try/except. The chart is 20 cells of `█`/`░`, computed with no Discord anywhere, which is what makes it unit-testable. |
| `black_bloc/polls.py:565` | `ranked` sorts by `(-votes, position)`, so a tie keeps the order the options were **written in** rather than whatever the dict happened to yield. |
| `black_bloc/polls.py:571` | `winners` returns a **list**, and `results_text` marks a winner only when that list has exactly one entry. `Poll.victor_answer` (`discord/poll.py:511`) is always `None` until the poll has finished, so the renderer never asks Discord who won — it counts. A genuine tie is named in a `Winner` field on the embed (`:335`) instead of two rows both claiming it. |
| `black_bloc/polls.py:598` | `average_rating` returns `None` — never 0 — the moment a label is not a number, so a `kind="rating"` poll whose options were overwritten does not print an invented mean. |
| `black_bloc/polls.py:771` | `counts_from_options` is the one shape (`position` / `label` / `votes`) that the embed, the API row, the CSV and the mock all read, so a fifth caller cannot invent a sixth spelling. |

### `black_bloc/cogs/community/polls.py` — everything that touches Discord

| Key | Note |
|---|---|
| `black_bloc/cogs/community/polls.py:443` | ⚠️ **`guard_allows` is the whole test-mode story for this feature, and it is asked BY HAND at every acting site.** `guard.py:101-142` patches exactly `http.send_message`, `http.edit_message` and `http.delete_channel`. `http.end_poll` is **not** among them (`discord/message.py:1897`), and neither is the voters endpoint — so `poll.end()` and `PollAnswer.voters()` would reach a real channel with the guard installed and silent. Create, end, cancel, remind, post-results and read-voters each ask first (`:531`, `:592`, `:696`, `:733`, `:1071`, `:1416`), exactly as `cogs/moderation/automod.py` does for delete and timeout. |
| `black_bloc/cogs/community/polls.py:793` | ⚠️ **The answer ids are read back off the posted message, not guessed.** `Poll.add_answer` numbers answers `len(self.answers) + 1` locally (`discord/poll.py:621`), but the ids that arrive on gateway vote events are Discord's. `_answer_ids` therefore reads `message.poll.answers` and falls back to `1..N` only when the count does not match — a guessed id would file every vote against the wrong option. |
| `black_bloc/cogs/community/polls.py:784` | `_expiry` prefers `message.poll.expires_at` over our own arithmetic, because Discord rounds a duration to whole hours when it reads one back (`discord/poll.py:452`) and the loop's close time must be **Discord's**, or the two drift by up to an hour. |
| `black_bloc/cogs/community/polls.py:296` | The reminder is claimed by a **conditional** `UPDATE … WHERE reminded_at IS NULL` whose `rowcount` decides whether to send. Claim-then-send, not send-then-mark: a restart between the two would otherwise double-ping the channel. `clear_reminder` (`:300`) releases the claim when the send fails, so a failure is not recorded as a last call — checklist item 2, with distinguishable kinds (`poll.reminded` vs `poll.remind_failed`). |
| `black_bloc/cogs/community/polls.py:1686` | `_reminder_horizon` takes the **widest** `poll_reminder_minutes` across every guild for the SQL window, then `_remind` re-checks each row against its own guild's setting (`:1051`). One query, no per-guild round trip, and a guild with a short window cannot be reminded early by a guild with a long one. |
| `black_bloc/cogs/community/polls.py:623` | `_write_results` calls `end_poll()` **only when Discord has not finalised the poll itself**. Native polls close on their own and Discord posts a `poll_result` system message; the loop's job is to read the final counts and archive them. Counts are approximate while open and exact once finalised (`discord/poll.py:206-211`), which is why the numbers are read *after* the end call, not before. |
| `black_bloc/cogs/community/polls.py:537` | ⚠️ **`refresh_voters` is why a missed gateway event is not a lost vote.** The raw listeners keep a running `poll_votes` tally, but they can miss (a disconnect, a restart); at close the voter list is read once from `PollAnswer.voters()` and upserted, which heals it. It returns on the first failure rather than half-filling a list, and it never runs for an `anonymous` row — a poll sold as anonymous must not leave names in our database either. |
| `black_bloc/cogs/community/polls.py:1123` | `_vote` listens to `on_raw_poll_vote_add` / `_remove` only, per the measurement above, and ignores any message that is not a Black Bloc poll, is `anonymous`, or is on a non-native surface. |
| `black_bloc/cogs/community/polls.py:690` | `cancel_poll` writes the status and the log line **inside** the lock and ends the vote at Discord **outside** it: the irreversible thing (the row) lands first, cosmetics after (checklist 12). A cancelled poll is still ended at Discord — leaving a vote running that Black Bloc has forgotten is worse than an unfinished cancel. |
| `black_bloc/cogs/community/polls.py:823` | `apply_decision` sets `open` before posting and **cancels the row when the post fails**. Without that the poll would sit `open` with no `message_id` and no `closes_at`, which the due-poll sweep (`:381`, `closes_at IS NOT NULL`) can never pick up — a permanently open row nobody can close. |
| `black_bloc/cogs/community/polls.py:799` | The auto-thread flag lives **on the poll row** (`polls.auto_thread`), not read from the setting at post time. A poll held for review can be approved days later, and the answer to "did this poll ask for a thread" must not change because a Lead flipped the setting in between. The thread is handed to `guard.own_channel` so Black Bloc may speak in it under test mode. |
| `black_bloc/cogs/community/polls.py:482` | `card_channel` sends the review card to `staff_channel_id`, or to the test channel while the guard is installed — the `events.py` shape, one line rather than a second copy of the rule. |
| `black_bloc/cogs/community/polls.py:1095` | The archive runs in the same 5-minute loop and logs **once per pass, only when something moved**, with the ids and the dropped-vote count. `poll_results` is never deleted: decision 14 is "archive, never delete"; only the per-voter rows go, and only when `poll_archive_drop_votes` says so. |
| `black_bloc/cogs/community/polls.py:311` | `save_results` writes `poll_options.final_votes`, one `poll_results` row and `polls.total_votes` together. The `poll_results` row is what survives the archive, which is why the totals are duplicated there rather than re-derived from options that may be gone. |

### `black_bloc/settings_store.py` and `api/status.py`

| Key | Note |
|---|---|
| `black_bloc/settings_store.py:19` | `POLL_MAX_HOURS` / `POLL_MIN_HOURS` are **imported from `polls.py`**, not re-declared. One fact, one home (checklist 15): the 32-day ceiling is Discord's, the pure module owns it, and the settings validator borrows it. |
| `black_bloc/settings_store.py` (`default`, `poll_mode`) | `poll_mode` ships **`on`**, unlike every other feature, and there is no `shadow` value at all. A shadow mode exists so a *punishing* feature can be watched before it is armed, and **a poll punishes nobody** — a shadow poll is just a poll nobody can vote in. |
| `black_bloc/api/status.py:27` | `poll_review_mode` joins `golive_end_mode` in `NOT_A_FEATURE`. It ends in `_mode` and would otherwise show on the Health tab as a fourteenth feature switch; it is a switch **inside** polls. `poll_who_can_create` needs no entry — it does not end in `_mode`, so `mode_keys()` never sees it. |

### `black_bloc/api/tools/polls.py` and the mock

| Key | Note |
|---|---|
| `black_bloc/api/tools/polls.py:292` | `refuse_outside_the_test_channel` is the API's copy of the by-hand guard check, for the same reason the cog has one. It is a no-op for a poll with no channel yet, so a held poll can still be **denied** from the dashboard while test mode is on — denying posts nothing. |
| `black_bloc/api/tools/polls.py:340` | The index carries a `notes` line saying the create form arrives with 10b. ⚠️ **There is deliberately no `POST /api/polls`**: creating from the dashboard means a channel picker and the panel surface, and half of that shipping alone would be a form that silently refuses anonymous polls. A page that cannot create says so in words rather than offering a button that 409s. |
| `black_bloc/api/tools/polls.py:252` | The export writes the totals **always** and the per-voter rows only when the poll kept them, with a `note` row naming which of the two reasons applies (anonymous, or archived-and-dropped). An empty CSV with no explanation reads as a bug; a named reason does not. |
| `site/mock/contract.json` | ⚠️ **`GET /api/polls/{id}/export.csv` is NOT in the contract**, because both halves of the contract check (`check.mjs`, `tests/api/test_contract.py`) parse every answer as JSON and this one is `text/csv`. It is covered by `tests/api/tools/test_polls.py` on the Python side, and by hand against the mock. |
| `site/mock/server.mjs` (`send`) | `send` now passes a **string** body through untouched instead of `JSON.stringify`-ing it, so the mock's CSV route answers real CSV. Nothing else in the mock returns a string, so the change is invisible to every other route. |
| `site/mock/server.mjs` (poll routes) | The mock's approve / end / cancel deliberately do **not** call `guard()`. The real API refuses in test mode only when the poll's own channel is not the test channel, and every fixture poll is in it — a blanket refusal here would teach the 10b page a rule the bot has not got. |
| `site/mock/check.mjs` (`IDS`) | Two entries added, `poll_id: '3'` and `poll_request_id: '2'`, so the contract's `{poll_id}` placeholders point at the mock's own fixture rows. This is the only edit outside `contract.json` and `server.mjs` on the site side, and `check.mjs` cannot fill a placeholder it has never heard of. |

### What was NOT verified

- ⚠️ **No live Discord, at all. This code has never posted a poll.** Every
  assertion about `discord.Poll` is against the payload `Poll._to_dict()`
  builds (a real object, in `tests/cogs/community/test_polls.py`) and a fake
  channel that mirrors it back the way Discord would. Nobody has seen a poll,
  voted in one, waited for a last call, or read a results embed in Discord.
- ⚠️ **`<t:…>` in an answer label is still unmeasured** — see above. It is 10b's
  first job, before any date-slot design.
- **`PollAnswer.voters()` has never paged.** The fake yields a short list; the
  100-per-request pagination in `discord/poll.py:285-291` is proven by reading
  it, not by running it.
- **The review buttons have never been clicked in Discord.** `SafeDynamicItem`
  re-hydration after a restart is proven by `add_dynamic_items` being called,
  not by a restart.
- **`message.create_thread` has never been called for real**, so the thread's
  archive duration and the `own_channel` hand-off are reasoned about.
- **No deploy, and no dashboard page** — 10b owns `polls.html`,
  `page-polls.js` and the nav entry, so there is nothing on the site for the
  owner to look at yet. The routes answer; nothing renders them.

## polls (10b) (2026-08-27)

> Phase 10b of [`phase10-design.md`](phase10-design.md): the panel surface,
> recurring polls, `POST /api/polls`, the dashboard tab, and one shared pager
> fix. Built on branch `worktree-agent-a9f9dbcabf9636130` cut from `main`
> @ `3eb7e4f` (10a's own tip), five commits `16c1db4` (the date kind) →
> `8906032` (the panel) → `a7d8216` (recurrence) → `85d05da` (API + the page) →
> `e4b5dca` (the pager). Line numbers are as of `e4b5dca`.
> ⚠️ **Not in `main` yet** — re-key on merge.
>
> **Last verified: 2026-08-27** — `pytest -q` **1819 passed** (1738 before, 81
> new), `ruff check .` clean, `node site/mock/check.mjs` **15 pages / 72 routes,
> all keys present**. Browser pass on the mock (port 8793) in Chrome: all
> fifteen pages fill `#dash`, **no console errors or warnings on any of them**,
> **zero horizontal overflow at 1280 and 390 CSS px in both Discord dark and
> Cyberpunk** (measured in same-origin iframes so the media queries see the real
> width), and nothing inside `#dash` sticks out past the viewport that is not
> inside its own `overflow-x` container.
>
> ⚠️ **Still no live Discord voting.** One real poll was posted (see below) and
> left in the test channel; nobody has voted in it, no panel button has ever
> been pressed, and no recurrence has ever fired.

### ⚠️ The `<t:…>` question, MEASURED — one real poll, posted 2026-08-27

10a could not settle whether `<t:…>` timestamp markdown survives inside a poll
**answer** label, and said 10b had to post one first. It did.

**What was done:** one native poll via `POST /channels/{id}/messages` with a
`poll` object, straight at the REST API (no gateway, no bot process), into
`#mute-me-bot-test-spam` and nowhere else. Two answers, one hour, question
*"Timestamp-in-answer-label probe"*. Then the message was fetched back with
`GET /channels/{id}/messages/{id}`.

| | |
|---|---|
| **Message id** | **`1542651824950218792`**, channel `1542316174472380517` — ⚠️ **left in place for the owner to look at** |
| Answer 1 as sent | `"<t:1788400000:d>"` |
| **Answer 1 as STORED and returned** | **`'<t:1788400000:d>'`** — byte-for-byte, unescaped, unaltered |
| Answer 2 as stored | `'Sat 30 Aug'` |
| Both statuses | `200` |

**So the API is not the obstacle: it stores the markdown verbatim.** ⚠️ **What
is STILL unknown is whether the CLIENT renders it as a date** — that is a
pixel question and this agent has never seen the message. It is one look away:
open the poll in Discord and read answer 1. If it reads as a date, flip
`poll_date_labels` to `timestamp` and every viewer gets their own zone; if it
reads as the literal `<t:1788400000:d>`, leave it on `plain`.

**The design does not depend on the answer.** `poll_date_labels` (default
`plain`) picks the form at generation time, so the decision is a settings flip
and not a rebuild.

### `black_bloc/polls.py` — the date kind, the surface, the cadence

| Key | Note |
|---|---|
| `black_bloc/polls.py:55` | `DATE_LABEL_FORMS` is `plain` / `timestamp` and **`plain` is the default deliberately**, because a plain label is right whether or not the client renders a stamp and a stamp is right only if it does. Defaulting the other way would have shipped `<t:1788400000:d>` as literal text to every voter on the strength of an unmeasured guess. |
| `black_bloc/polls.py:330` | `parse_day` takes `2026-09-05` **and** `2026-09-05 19:00` and reads both in the server's zone (`America/Phoenix`, no DST, the value birthdays already uses), returning UTC. `timezones.parse_start` was not reused: it accepts only the long form, and a day poll whose slots are whole days should not have to type `00:00`. |
| `black_bloc/polls.py:343` | ⚠️ **`clock_label` builds the twelve-hour time by hand because Windows `strftime` has no `%-I`** — `%I` pads (`07 pm`) and the platform-specific unpadded flag is `%-I` on POSIX, `%#I` on Windows. Building it from `hour % 12 or 12` is the only form that reads the same on both. |
| `black_bloc/polls.py:377` | `date_slots` decides **whether the label carries a time** from the ask rather than from a flag: an hourly step always does, and a daily step does only when the start itself had a time on it. A seven-day poll of "Sat 05 Sep" reads better than seven copies of "· 12 am". |
| `black_bloc/polls.py:362` | `date_trouble` is checked **before** any slot is generated and returns the sentence; `date_slots` returns `[]` for an unreadable start rather than raising, so a caller that skips the check gets nothing rather than a half-laid-out poll. |
| `black_bloc/polls.py:503` | ⚠️ **`surface_for` no longer refuses anonymity, hidden results or eleven options — it returns `panel`.** It still raises `NeedsPanel` for a kind no surface carries (free text, number, ranked) and for more than **25** options, which is the panel's own button ceiling. That is the whole shape of 10b: three of 10a's four refusals became a surface. |
| `black_bloc/polls.py:516` | `panel_reason` returns the **first** thing that rules native out, in a fixed order (anonymous → hidden → too long), so a poll asking for two impossible things names the one the person most likely meant rather than listing both. `panel_note` (`:527`) wraps it in the sentence the creation flow shows. |
| `black_bloc/polls.py:42` | `MULTI_KINDS` is `(checkbox, date)` — a date poll is an availability poll, and asking somebody which single evening they can make defeats the point. |
| `black_bloc/polls.py:653` | `panel_text` is the ONE place the hidden-results promise is kept: with `hidden` it prints the options **numbered, with no bars and no counts**, so a screenshot of the panel gives nothing away. `panel_embed` (`:665`) only passes `hidden=True` while the poll is still `open`, so the bars appear the moment it closes. |
| `black_bloc/polls.py:665` | ⚠️ **The panel counts VOTERS, not votes.** On a checkbox panel one person can be in three options, so dividing by the sum of the options would make the bars read as fractions of a number nobody recognises. Dividing by distinct voters means "7 of the 11 people who voted can make Saturday", which is the sentence a reader actually wants. A single-choice panel is unaffected — the two numbers are equal. |
| `black_bloc/polls.py:84` | `recurring` is a **status**, not a table. A recurrence is a `polls` row that never opens, carrying the `recurrence` / `recur_at` / `recur_tz` / `recur_next_at` columns 10a reserved; each occurrence is an ordinary poll whose `schedule_id` points back at it. `TRANSITIONS[RECURRING]` is `(CANCELLED,)` — a template is only ever stopped, never opened. |
| `black_bloc/polls.py:410` | `cadence_token` is one string (`daily`, `weekly:sat`, `monthly:12`) so the row carries a cadence in one column and the loop parses it in one place. |
| `black_bloc/polls.py:443` | ⚠️ **`MAX_MONTH_DAY` is 28 and the refusal says why: February.** A monthly poll set for the 31st would silently skip four months a year, and clamping it to "the last day" quietly changes what somebody asked for. Refusing with the reason is the only honest option. December rolls into January by `divmod(month, 12)` rather than by date arithmetic that would throw on the 13th month. |
| `black_bloc/polls.py:497` | `whole` replaced the bool-before-int guard `whole_hours` had, and `whole_hours` (`:326`) now calls it. `True` is an `int` in Python and would otherwise be read as one hour, one slot or a one-day step. |

### `black_bloc/cogs/community/polls.py` — the panel, and everything it touches

| Key | Note |
|---|---|
| `black_bloc/cogs/community/polls.py:589` | ⚠️ **`voter_key` is how an anonymous poll counts one vote each without keeping who cast it.** A panel MUST store a row per voter or a person could vote ten times; a poll sold as anonymous must not leave member ids in the database. So for `anonymous` rows the stored `user_id` is the top 63 bits of `sha256("<poll_id>:<user_id>")` — per-poll salted, so the same person is a different number in every poll, deterministic enough for "clear my vote" to find their row, and useless to anybody reading the table. `poll_votes.user_id` stays an INTEGER; nothing else changed. |
| `black_bloc/cogs/community/polls.py:641` | `set_panel_vote` writes a person's **whole answer as a replacement** — delete every row of theirs, insert what they now hold. An append-with-toggle would drift the moment two clicks raced; a replacement is idempotent and the button computes the new set from `my_positions` (`:626`) first. |
| `black_bloc/cogs/community/polls.py:868` | `cast_vote` takes the per-poll `asyncio.Lock` **around the write only**, then repaints outside it: two people pressing at once serialise on the row, and the message edit (which can be rate-limited) never holds the lock. Checklist 6, with the DB's own unique index as the second guard. |
| `black_bloc/cogs/community/polls.py:809` | `panel_view` gives a button per option up to **five** and one "Vote" button past that. Five is not Discord's cap (25 over five rows) — it is where a row of buttons stops being readable, and past it the modal shows the same options with a scrollbar instead. |
| `black_bloc/cogs/community/polls.py:968` | ⚠️ **`vote_picker` is where 2.7.1's typed modal fields earn their place, and where their real cap bites: both `RadioGroup` and `CheckboxGroup` are capped at TEN options in the library** (`discord/ui/radio.py:63`, `discord/ui/checkbox.py:71-73` — "between 2 and 10", "up to 10 items"). So the picker is a `RadioGroup` for one choice, a `CheckboxGroup` for many, and a plain `Select` (25 options, `required=False`, only valid in a modal) once there are more than ten. The research's §4.4 typed-modal design is real, but only for short polls. |
| `black_bloc/cogs/community/polls.py:1005` | `picked_values` reads `.values` when the component has one and `.value` when it does not, so the three pickers above are interchangeable to the caller. A `RadioGroup` has `value`; `CheckboxGroup` and `Select` have `values`. |
| `black_bloc/cogs/community/polls.py:1013` | The modal opens **pre-filled with what that person already picked** (`default=` per option), because a modal that forgets your answer makes "change one thing" mean "type it all again". Submitting it with nothing picked says `PICK_SOMETHING` and changes no vote — clearing is a separate button, so an empty submit is a slip rather than an instruction. |
| `black_bloc/cogs/community/polls.py:791` | `panel_card` is the one home for the panel's embed, so the post, every vote's repaint and the close all render the same card from the same row. The alternative — three call sites each passing its own arguments to `panel_embed` — is how a poll ends up saying `open` after it closed. |
| `black_bloc/cogs/community/polls.py:823` | `repaint_panel` asks `guard_allows` **and** swallows its own errors: a failed repaint must never fail the vote that caused it. The vote is the irreversible thing and the picture is cosmetics (checklist 12). |
| `black_bloc/cogs/community/polls.py:1167` | ⚠️ **`_write_panel_results` never calls `end_poll`, because a panel has no poll at Discord to end.** The whole native close path — `end_poll`, `counts_from_message`, `refresh_voters` — is skipped; the counts come from `poll_votes`, which is the authority for this surface. `_shut_panel` (`:1172`) then takes the buttons off and puts the final bars on, including for a poll that had been hiding them. |
| `black_bloc/cogs/community/polls.py:263` | ⚠️ **`poll_plan` is the one place a poll's arguments become a poll**, and it is why `POST /api/polls` cannot accept something `/poll create` would refuse. Validation, slot generation, surface derivation and the panel sentence all happen here; the two callers only decide where it goes and who is told. |
| `black_bloc/cogs/community/polls.py:315` | `store_poll` writes the row, its options and the `poll.created` line together and answers *(the row, is it held)*. `status=` overrides the review switch, which is how the recurrence loop opens an occurrence without sending it back for approval — a Lead approved the recurrence once, not every Tuesday. |
| `black_bloc/cogs/community/polls.py:252` | `add_options` gained `values`: `poll_options.value` carries the ISO instant a date slot stands for, so a slot survives its own label. If `poll_date_labels` is flipped later, the stored instants are still the truth about which evening won. |
| `black_bloc/cogs/community/polls.py:376` | ⚠️ **`polls_by_status` now excludes `recurrence IS NOT NULL`.** A template is not a poll: without this it would show up in `/poll list`, on the dashboard index and in the pending-review queue, as a poll nobody can vote in. `recurrences` (`:381`) is the query that wants them. |
| `black_bloc/cogs/community/polls.py:421` | ⚠️ **`claim_occurrence` is what makes the recurrence loop idempotent.** It moves `recur_next_at` on with `WHERE recur_next_at = <what we read>` and only opens the poll when `rowcount` says it got there first. Reading-then-opening-then-writing would post the same occurrence twice across a restart, exactly the way the reminder would have without `claim_reminder`. |
| `black_bloc/cogs/community/polls.py:1631` | `_recur` computes the NEXT time before claiming this one, and a cadence it cannot read **pauses the template** (`recur_next_at = NULL`) with a `poll.recur_failed` line rather than being retried every five minutes forever. Checklist 5: a bad row is finished, never left blocking. |
| `black_bloc/cogs/community/polls.py:2206` | Pause is `recur_next_at = NULL` — no new column, and `due_polls` already requires the column to be non-NULL, so a paused template is simply never due. `paused:false` recomputes the next time rather than restoring an old one, so resuming after a fortnight does not fire immediately. |
| `black_bloc/cogs/community/polls.py:2244` | ⚠️ **Delete does not delete.** `/poll recur delete` sets the template to `cancelled` and clears its next time; the row stays, the occurrences it opened keep a `schedule_id` that still resolves, and the archive sweep tidies it away on the usual schedule. Decision 14 is "archive, never delete", and a dangling `schedule_id` is a worse answer than a cancelled row. |
| `black_bloc/cogs/community/polls.py:2088` | ⚠️ **A date poll is refused a recurrence, in words.** Its slots are fixed days; the second time round it would be asking about a day that has been and gone. The sentence says so and points at `/poll create kind:date` or a checkbox poll with the days written on it. |
| `black_bloc/cogs/community/polls.py:1443` | `send_review_card` was lifted out of the cog method so `POST /api/polls` can hold a poll for review too. It answers *(where it went, the card)* and distinguishes "no staff channel at all" (`None, None`) from "the send failed" (`target, None`) — the first cancels the poll, the second leaves it decidable by hand. |

### `black_bloc/api/tools/polls.py` — the create form's route

| Key | Note |
|---|---|
| `black_bloc/api/tools/polls.py:343` | `POST /api/polls` calls `poll_plan` and `store_poll`, so the page cannot ask for anything the slash command would refuse and the refusal sentence is the same one Discord would have shown. 10a deliberately left this route out because half of it shipping alone would be a form that silently refused anonymous polls; with the panel built, that objection is gone. |
| `black_bloc/api/tools/polls.py:400` | `_open_or_hold` cancels the row when the post fails and raises a **409** with the reason, rather than answering 200 with a poll that is not anywhere. A created-but-not-posted row is the state `apply_decision` was already careful about. |
| `black_bloc/api/tools/polls.py:307` | ⚠️ **`_shown` reads an OPEN panel's counts from `poll_votes`, not from `poll_options.final_votes`.** `final_votes` is written once at close, so without this branch every open panel on the dashboard would read zero while its message showed real bars. |
| `black_bloc/api/tools/polls.py:177` | `recurrence_row` is a shape of its own rather than `poll_row` with holes: a template has no `status` a reader would understand, no votes and no close time, but it does have a cadence, a next time and a paused flag. `cadence_said` is rendered server-side by `describe_cadence` so the page and Discord say it identically. |
| `black_bloc/api/tools/polls.py:204` | `wanted_options` takes a list (what the form sends) or a `A \| B` string (what the command sends) and normalises to the string `poll_plan` reads, so one validator serves both. |
| `black_bloc/api/tools/polls.py:441` | Pause/resume and delete are the only recurrence writes the dashboard gets. **There is no create-a-recurrence route**: setting one up needs a cadence, a weekday-or-day-of-month and a timezone, and `/poll recur create` already asks for those with Discord's own choice pickers. The page says where to make one instead of offering a form that would be the worse of the two. |

### `site/` — the fifteenth page

| Key | Note |
|---|---|
| `site/public/assets/page-polls.js:416` | ⚠️ **`outcomeOf` derives the surface in JavaScript the same way `polls.py:surface_for` derives it in Python — a second copy of a rule, on purpose.** The alternative is a round trip on every keystroke. It is kept honest by the fact that the SERVER still decides: the page's sentence is a prediction, the reply's `note` is the answer, and the create button shows whichever the API sent back. If the two ever disagree the person sees the truth. |
| `site/public/assets/page-polls.js:109` | `resultBars` marks a winner only when `winner_position` is set, which the API sets only for an outright winner. A tie marks nobody — the same care `results_text` takes in the embed. |
| `site/public/assets/page-polls.js:141` | The `panel` chip carries a `title` naming which part of the ask made it a panel, so the surface column answers "why is this one different" without a click. |
| `site/public/assets/page-polls.js:385` | Archive is a `foldout` inside its own section rather than a section of its own (D14): shut by default, and the export still works from inside it. A nested `section()` would have put it in the "On this page" rail as a place, which it is not. |
| `site/public/assets/page-polls.js:585` | `load` makes five API calls in parallel and splits the answers by section, so the Closed list can page on its own without re-fetching the open ones. |
| `site/public/assets/site.css:1389` | The result bars are a three-column grid whose name column is **capped, not sized to the longest label** — a 55-character answer would otherwise push the bars off a phone. Under 30rem the track drops to its own row (`:1422`) instead of shrinking to nothing. |
| `site/public/assets/site.css:1434` | ⚠️ **`.field > .seg { justify-self: start }` fixes a bug older than Polls.** A segment is a flex row with a hairline background; as a bare grid item it stretched to the field's full width and painted the rest of the row as a grey bar. Visible on Role menus' Approval field since 9b, and on every segment Polls adds. |
| `site/public/assets/shell.js:74` | `pollTally` asks for `per_page=1` and reads `total`, the same trick `memberTally` uses — the count in the rail costs one row, not the whole list. |

### `site/public/assets/ui.js:613` — the pager scrolls back to the top

> ⚠️ **GONE in the 2026-08-31 re-key:** `site/public/assets/ui.js:GONE (was :522)` — the construct each note names is no longer in the file; the note itself needs a decision.

Owner, verbatim: *"for each page that has pagination make sure on hitting next
page it scrolls back to the top of the list."*

| Key | Note |
|---|---|
| `site/public/assets/ui.js:544` | ⚠️ **`document.scrollingElement` NEVER MOVES on this site.** `site.css:29` puts `overflow: hidden` on `body` and `:260` puts `overflow-y: auto` on `.content`, so the page's scroller is `.content` and every `window.scrollTo` / `document.scrollingElement.scrollTop` reads and writes zero. `scrollerOf` walks up for the first ancestor that actually scrolls. A verification that measured `document.scrollingElement.scrollTop` would have read `0 → 0` and looked like the feature was broken when it worked, or working when it did nothing. |
| `site/public/assets/ui.js:567` | The list top is measured **before** the callback re-renders, because the node it is measured from is thrown away by the re-render. The absolute offset within the scroller survives; the element does not. `listTop` also does NOT subtract a top-bar height: the bar is a *sibling* of the scroller in `.shell-main`, not an overlay on it, so nothing covers y=0 inside `.content`. |
| `site/public/assets/ui.js:604` | ⚠️ **The move is instant, not smooth, and that is the finding of the day.** The first build used `scrollTo({behavior: 'smooth'})` and measured as doing nothing at all — a smooth scroll is an **animation**, and animations are throttled to a stop in a tab that is not on screen. So the one thing this exists to do would silently not happen exactly where nobody would notice. `scrollTop = wanted` always lands. |
| `site/public/assets/ui.js:GONE (was :522)` | The guard is one line: if the scroller is already at or above the list top, do nothing. Pressing Next twice from the top of a list must not jiggle the page. |
| `site/public/assets/page-members.js:180`, `page-moderation.js:239` | Both now **return** their `refresh()` instead of firing and forgetting, so `pager` can await the re-render before it scrolls. This is the only change either file needed. |

**Measured, on the mock at port 8793** (`.content.scrollTop`, the real scroller):

| Page | Before Next | After | The list's top edge |
|---|---|---|---|
| Polls → Closed | 3405 | **989** | −2352 → **+64** (8 px under the bar) |
| Members | 1961 | **0** | −1735 → **+226** |
| Polls → Previous, already at the top | 989 | **989** (unmoved) | +64 → +64 |

`document.scrollingElement.scrollTop` was **0 before and after every one of
them**, which is the measurement above in practice.

⚠️ **Moderation could not be exercised** — the mock seeds nine cases and its
per-page is ten, so Next is disabled and there is nothing to page. The code path
is the same `pager()` Members and Polls both proved. Audit, Modmail and Role
menus have **no pager at all** (they read a fixed `limit=100`/`limit=200`), so
there was nothing to fix on them; the brief listed them as pages to check and
the check is "they do not paginate".

### What was NOT verified

- ⚠️ **No vote has ever been cast, on either surface.** Every panel assertion is
  against the fake channel in `tests/cogs/community/test_polls.py`. Nobody has
  pressed a panel button in Discord, opened the vote modal, or seen a
  `RadioGroup` render — 2.7.1's typed modal components are proven by reading
  `discord/ui/radio.py` and `checkbox.py` and by building the objects, not by
  submitting one.
- ⚠️ **Whether `<t:…>` RENDERS in an answer label is still open** — the API
  half is measured (above), the client half needs one look at message
  `1542651824950218792`.
- ⚠️ **No recurrence has ever fired against Discord.** The loop is proven by
  moving `recur_next_at` into the past in a test database.
- **Nothing has been deployed and nothing merged.** `poll_mode` ships `on`, so
  merging this makes `/poll` and `/poll recur` live for staff the moment the bot
  restarts — under the test-channel guard, which every acting site still asks
  by hand.
- **The anonymous voter hash has not been reviewed by anybody but its author.**
  It is a truncated SHA-256, not a keyed MAC: somebody with the database and a
  list of member ids could confirm a guess about who voted by re-hashing.
  Making that infeasible needs a per-guild secret, which is a bigger change than
  10b; the current form is strictly better than storing the id and worse than a
  real MAC, and it is written down here rather than assumed.
- **The CSV export is served but never downloaded in anger** — it was fetched
  and read as text in the browser, not saved by a person clicking the link.

## chat 2 — dashboard (11b) (2026-08-27)

> Phase 11's second half — the **Chat** page — on branch
> `worktree-agent-aa53d8a518425a5df` cut from `main` @ `ebf99a2`, two commits
> `1aba879` (contract + mock) → `cfc5a2f` (the page). Line numbers are as of
> `cfc5a2f`. ⚠️ **Not in `main` yet** — re-key this section on merge.
>
> ⚠️ **11a was building the bot/storage/API half in parallel and this branch
> touched NOTHING under `black_bloc/`.** The page is written against the route
> contract in the brief and against the mock; `site/mock/contract.json`,
> `server.mjs` and `check.mjs` are the three files both halves edit, and they
> are kept in their own commit (`1aba879`) so the reviewer can reconcile.
>
> **Last verified: 2026-08-27** — `node site/mock/check.mjs` **16 pages / 80
> routes, all keys present**; `pytest -q tests/api` **532 passed, 8 failed**,
> and the eight are exactly the eight new chat contract routes answering 404/405
> because the real API does not serve them yet (`-k "not api/chat"` is **532
> passed, 8 deselected**). Browser pass on the mock at port 8801, Chrome,
> Discord dark and Cyberpunk dark.

### ⚠️ What the contract did NOT carry, and what the page needed anyway

| Gap | What was done |
|---|---|
| **`tokens` on an intent row.** The brief's token help says "+ the data intent's own tokens", but the contract's intent shape has no field for them, so the page could not know that `head_count` takes `{count}` and `whats_next` takes `{title}`/`{when}`/`{where}`. | The mock **sends `tokens`** (a list of the intent's OWN extra tokens; the page always prepends `{name}` and `{attendees}`), it is a required key in `contract.json`, and `page-chat.js:68 OWN_TOKENS` is a **fallback table keyed by intent name** so an intent that arrives without them still gets its help line. ⚠️ **11a must decide**: send `tokens`, or the fallback table becomes a second copy of a rule that will drift. |
| **Every write's reply shape.** The brief says a write returns "the intent" / "the line"; every outcome sentence on this site comes from a `message` key. | The mock answers `{intent, message}`, `{line, message}`, `{intent_id, message}`, `{line_id, message}` — the same shape Polls and Role menus use. Pinned in `contract.json`. |
| **The `settings` key on `GET /api/chat/intents`.** The brief says it carries "the chat_* keys as the settings API reports them" without saying in what shape. | The mock sends an **array of settings-registry rows** — the same rows `/api/settings` reports. `page-chat.js:514` prefers them and falls back to `/api/settings`'s `chat` namespace key by key, so either shape works. |
| **`emoji_skin_tone` is not a chat key.** It namespaces to `emoji`, so it is not in `chat` and not in the route's `settings`. | `page-chat.js:110 specFor` finds a key in **any** namespace of the settings payload, and the Settings section lists the seven keys by name in `SETTING_KEYS` (`:25`) rather than by namespace. |
| **The three manners keys' TYPE.** The design says "off/on"; a mode key is an `enum` here and a yes/no is a `bool`. | The mock registers `chat_greeting_reaction` / `chat_reply_in_threads` / `chat_route_ping_staff` as **`bool`** (`server.mjs:303`), which `ui.js:838` already renders as an On/Off segment. If 11a makes them enums the page still works — `settingsEditor` renders a two-choice enum as the same segment. |

### `site/mock/server.mjs` — the fixture is the bot's own words

> ⚠️ **GONE in the 2026-08-31 re-key:** `site/mock/server.mjs:GONE (was :1956)` — the construct each note names is no longer in the file; the note itself needs a decision.

| Key | Note |
|---|---|
| `site/mock/server.mjs:1089` | ⚠️ **`CANNED` carries `black_bloc/chat.py`'s `LINES` tables VERBATIM**, including the two `ATTENDEE_LINES` as extra lines on `greeting` and `how_are_you`. A fixture that merely resembled them would have let the page look right while editing wording nobody says. `sort` follows `chat.py:ORDER`, so the mock classifies in the bot's own order. |
| `server.mjs:598` | Each data intent keeps **exactly two** lines — the template and the one for when there is nothing to say. That pair is the whole shape of a data intent, and seeding both means the empty state is drawn without anybody having to break something first. |
| `server.mjs:2879` | `seedChat` returns `{intents, lines, nextIntent, nextLine}` — lines live in a flat list keyed by `intent_id` rather than nested in the intent, so `PUT /api/chat/lines/{id}` can find one without knowing its intent, exactly as the route contract does. |
| `server.mjs:2820` | `chatWords` is `black_bloc/chat.py:normalise` in JavaScript, and `chatHasPhrase` is `has_phrase` — ⚠️ **a second copy of a rule, on purpose**, because a mock that matched substrings would let "helping" hit `help` and the page would be tested against a bot that does not exist. Measured: `helping is hard` → `unknown`. |
| `server.mjs:1089` | `chatOrdered` sorts **custom first, then built-ins by `sort`** — the design's classification order — and it is the same list the page renders, so the card order on screen IS the order a message is matched in. |
| `server.mjs:3024` | ⚠️ **The dry run picks the FIRST enabled line, not a random one.** `chat.py:respond` uses `random.choice`; a Try-it box that answered differently every press could not be checked, and the thing being tested is *which line pool*, not which draw. A line pool with nothing enabled falls back to the first line, which is the design's "the code tables remain the fallback". |
| `server.mjs:GONE (was :1956)` | `CHAT_SAMPLE` fills the data tokens server-side so Try it shows a finished sentence. Unknown tokens are **left standing**, the way `ui.js:1055 fillTemplate` leaves them — a token nobody fills is a bug the page should show, not hide. |
| `server.mjs:2879` | `DELETE /api/chat/intents/{id}` refuses a built-in **in words** and names the alternative ("turn it off instead"). `DELETE /api/chat/lines/{id}` (`:2879`) refuses the **last** line for the same reason: removing it would leave the intent with nothing to say. |
| ⚠️ `need_a_mod`'s triggers | The design lists `help me` among them. It **cannot ever fire**: `help` is `sort` 4 and `need_a_mod` is 20, so `help` claims the phrase first. The mock seeds `i need a mod` / `need a mod` / `report` / `staff please` / `need staff` instead, because a fixture with a trigger that can never match tests nothing. **11a should either drop it or sort the route intent ahead of `help`.** |

### `site/public/assets/page-chat.js` — the page

| Key | Note |
|---|---|
| `page-chat.js:298` | ⚠️ **A card is rebuilt from the REPLY, never from what the page assumed.** Every intent write answers with the whole row, so `swap(done.found.intent)` replaces the card with the bot's own truth; a line write answers with the line, so the swap is `{...intent, lines: <the reply's line spliced in>}` — the only part a line write changes. Nothing on this page paints an optimistic value. |
| `page-chat.js:301` | The swap would throw away the sentence the write was just written into, so it calls `keepSaying` first and the rebuilt card calls `sayAgain` (`:299`). Same shape as Role menus' three parking names, but keyed **per intent** (`chat:<id>`) because sixteen cards each have their own notice. |
| `page-chat.js:126` | A line's **Save stays disabled until the text actually differs**, so pressing it always means something and a stray click cannot rewrite a line to itself. The two other line writes (in/out of the pile, remove) are buttons whose LABEL is the action — `Turn off` / `Turn on` — so the button says what will happen rather than what is true. |
| `page-chat.js:369` | ⚠️ **A built-in gets NO Delete button and a sentence saying why, rather than a Disable button beside the Answers switch.** The brief asked for "Disable instead of Delete"; the switch above already IS that control, and two controls writing one field is the duplicate-surface trap. So the destructive slot carries the refusal in words instead. **A deliberate deviation from the brief's wording, not from its intent.** |
| `page-chat.js:187` | A trigger chip's `×` sends the WHOLE remaining list on a `PUT`, because the route takes `triggers` as a list and has no per-phrase route. The add path (`:211`) does the same with the phrase appended, and a phrase already in the list is refused **in the page** with a sentence rather than sent. |
| `page-chat.js:103` | `tokensOf` prefers the API's `tokens` and falls back to `OWN_TOKENS`; `tokenHelp` (`:106`) renders one line of `{token} = what it is`. See the deviations table — the fallback is a rule in two places and should die when 11a lands. |
| `page-chat.js:375` | The intents list **only pages past fifty** (`PER_PAGE`, `:23`). Sixteen intents is the seed, so the pager is not drawn there; it was exercised by seeding 40 more (56 total) — page 1 of 50, page 2 of 6, Next disabled at the end, and the scroll went **25923 → 276.67** with the section's top edge at **+64** (`document.scrollingElement.scrollTop` **0 before and after**, exactly as `ui.js:544` says). |
| `page-chat.js:400` | Try it says "Nothing was sent" in the outcome sentence AND in the section note, because a box that looks like it messages the server is the one thing on this page a person could be wrong about. |
| `page-chat.js:514` | `load` makes two calls in parallel and the settings list is assembled key by key (route → registry → `emoji_skin_tone`), so a key missing from either source is simply absent rather than a hole in the panel. |

### `site/public/assets/site.css:1434` — a badge in a field stretches too

| Key | Note |
|---|---|
| `site.css:1434` | ⚠️ **`.field > .badge` needed the same `justify-self: start` `.field > .seg` got in 10b.** A grid item is stretched unless told not to, so the Kind pill painted its hairline border across the whole field column. Same bug, second shape. `.chat-fixed` joins them. |
| `site.css:1443` | ⚠️ **A built-in's name is TEXT on the control line, and it deliberately does NOT use `.field-current`.** `.field-current` is placed in the field's THIRD grid row (`site.css:1069`, the help row); a node carrying both it and `.field-control` lands in row 3 and drops below every sibling's control. `.chat-fixed` is its own class with the control row's `min-height`. |
| `site.css:1502` | `.chatline > .input { flex: 1 1 18rem }` — the wording takes the room and the three buttons keep theirs, so a 200-character line **wraps the button bar under itself** rather than pushing the row past the card. That is why the page has no horizontal scroll at 390. |
| **measured, not asserted** | Same-origin iframes at **1280 and 390 CSS px**, Discord dark and Cyberpunk dark: **17 side-by-side field groups, every one spread 0.00px**, and the button bars in **34 formrows** sit 0.00px off their sibling's control. `scrollWidth - innerWidth` is **0** at both widths in both themes, and nothing inside `#dash` has a box edge outside the viewport. At 390 every formrow wraps to one field per line, so there is no group left to compare — the same clustering caveat 9b recorded. |

### What was NOT verified

- ⚠️ **Nothing ran against the real API, because it does not exist yet.** Every
  assertion on this page is against `site/mock/server.mjs`. The eight failing
  contract cases above are the honest record of that.
- ⚠️ **`tests/api/test_contract.py` has no `chat_intent_id` / `chat_line_id` in
  its `seeded` fixture** — it was read-only for this half. 11a or the reviewer
  must add them (the mock uses `'1'` for both, the custom intent and its first
  line) or the eight cases will fail on a missing placeholder even once the
  routes exist.
- **No Discord.** Nobody has @-mentioned the bot and seen an edited line come
  back; Try it is a dry run against a fixture, not a message.
- **Browser checks were Chrome, Discord dark and Cyberpunk dark**, 1280 and 390.
  The other theme×mode combinations were not looked at; the new CSS is
  token-only, but that is inference.
- **Contrast of the new pieces was not measured.** `.trigchip`, `.chatline-off`
  and `.chat-answer-line` reuse `--et-muted` / `--et-shell-inset` /
  `--et-accent`; no sampler was run.
- **The four neighbouring pages were checked for regressions** (`polls`,
  `settings`, `rolemenus`, `index` all fill, no overflow, fields still level at
  1280) but the other eleven were not opened by hand — `check.mjs` only proves
  they serve.

## chat 2 (11a) (2026-08-27)

> **Step 2a of F10** — the words become rows a Lead can edit, six intents answer
> from live state, `need_a_mod` routes, and four manners settings decide where
> and how the bot speaks. Built on branch `worktree-agent-aba2337a090a6d590` off
> `main` @ `ebf99a2`, commits `e508232` (bot + storage), `6a91b87` (API +
> contract/mock) and `f00e8de` (11b's clarifications). The dashboard Chat page is **11b** and does not exist yet.
> **Last verified: 2026-08-27** — `pytest -q` **1941 passed** (1819 before,
> +122). `ruff check .` clean. `site/mock/check.mjs` clean at **80 routes**.
> ⚠️ **NOTHING has been run against live Discord** — no gateway session, no
> @-mention, no reaction, no staff note. Every claim about what Discord delivers
> is read off the installed library or off a fake.

### The two decisions that shape everything else

| Key | Note |
|---|---|
| `black_bloc/chat.py:542` | ⚠️ **`reply_for` keeps its parameter list and became a COROUTINE, which is the one real deviation from the brief.** A data intent has to read the database (open go-live sessions, the next approved event, stored birthdays, the member's zone), and a synchronous seam cannot. `answer_for` is the new inner call and returns an `Answer(intent, kind, slot, text)` rather than a bare string, because the cog needs the intent for its action row and the kind to decide whether to route — `black_bloc/chat.py:542`'s `reply_for` is now a two-line wrapper over it and stays the documented swap point for a step-3 backend. The old cog called `classify` a second time to get the label; that second call is gone, and with it the note at `cogs/content/chat.py:91` from step 1. |
| `black_bloc/storage/db.py:351` | ⚠️ **`chat_lines.slot` is a THIRD column the brief did not name, and it is what makes item 3 possible.** Item 1 said "ONE editable template line each"; item 3 said each data intent has "a filled line and an empty-state line, both editable". Those cannot both be true, so a `slot` of `filled` / `empty` / `attendee` carries the difference. `filled` is the ordinary answer, `empty` is what a data intent says when there is nothing to report, and `attendee` is the head-count-flavoured extra that step 1 kept in a separate code table (`ATTENDEE_LINES`) — now seeded as rows so a Lead can turn it off. `need_a_mod` reuses the same two states: `filled` = modmail is answering, `empty` = it is not. |

### Classification over a guild's own rows

| Key | Note |
|---|---|
| `black_bloc/chat.py:412` | `classify(text, intents=())` takes the rows as an argument rather than reading them itself, so it stays a pure function over one short string and every test can pin an order without a database. The default `()` is what keeps step 1's call sites and tests working unchanged, and it is also the honest answer for a DM, where there is no guild to have rows. |
| `black_bloc/chat.py:408` | ⚠️ **A custom intent with no enabled `filled` line is SKIPPED rather than matched.** Without this, saving a new intent and not yet writing a line silently swallows every message that hits its triggers and answers "Not sure I follow" — the half-built intent would be worse than no intent. Pinned by `tests/test_chat.py`'s *a custom intent with nothing to say is skipped*. Built-ins are never skipped this way because the code table always has something for them. |
| `black_bloc/chat.py:258` | ⚠️ **`BUILTIN_ORDER` is not `ORDER` with the new names appended, and the order is load-bearing twice over.** `birthdays` sits **above** `whats_next` because "when is the next birthday" contains `when is the next`, which is a `whats_next` phrase — read the other way round, the bot answers a birthday question with a movie night. `need_a_mod` sits **above** `help` because it owns the phrase "help me": somebody who says that wants a person, not `/help`. `insult` stays first and `greeting` stays last for step 1's reasons. `ORDER` is left exactly as it was, still the canned-only tuple, because `tests/test_chat.py` asserts it matches `INTENTS`. |
| `black_bloc/chat.py:386` | Triggers are normalised at MATCH time, not at save time, so a Lead may type `What's up?` on the page and it still matches `whats up`. The stored value keeps their punctuation, which is what they will see when they come back to edit it. |
| `black_bloc/chat.py:436` | `bare_greeting` asks whether the whole message IS one greeting phrase, not whether it contains one — a wave in answer to "hey, when is the cookout?" would read as the bot ignoring the question. It reads the guild's edited greeting triggers, so a server that renamed "hi" to "ahoy" still gets the wave. |

### The lines, and what falls back to the code tables

| Key | Note |
|---|---|
| `black_bloc/chat.py:469` | ⚠️ **`pool` falls back to the code table for an ANSWER but NOT for the optional extras, and the difference was a real bug a test caught.** The first cut fell back for every slot, which meant disabling all the `attendee` lines did nothing at all: the code `ATTENDEE_LINES` came straight back and the bot kept saying "that makes 12 of us" to a server that had switched it off. An intent must always have something to say, so an empty `filled` slot falls back; the head-count garnish is optional, so an empty `attendee` slot **on a row that exists** means "none, thank you". A guild with no row at all still gets both, because that guild has expressed no preference. Pinned by *turning off the head count lines actually turns them off*. |
| `black_bloc/chat.py:369` | ⚠️ **`Tokens.__missing__` returns the token as it was typed, so a line nobody can render cannot silence the bot.** Every line on the Chat page is staff-authored text going through `str.format_map`; a stray `{when}` in a greeting would otherwise raise `KeyError` inside `on_message` and the member would get nothing at all. `render` at `:390` also catches `ValueError` and `IndexError`, which is what a half-typed `{` or a `{0}` produces, and sends the line as written. Both pinned. |
| `black_bloc/chat.py:456` | One function answers "what do the code tables say" for every intent and slot, so `seed_defaults` and `pool` cannot disagree about what a fresh guild gets. Seeding is `code_lines` written to rows; the fallback is `code_lines` read directly. |
| `black_bloc/chat.py:769` | `seed_defaults` is keyed on `(guild_id, name)` and skips a name already there, so it is safe to call from `cog_load`, `on_ready`, `on_guild_join` and the API's GET — which it is, from all four. It never touches lines on an intent that already exists, so re-running it cannot undo an edit. Pinned by *seeding twice changes nothing and leaves edits alone*. |
| `black_bloc/chat.py:830` | ⚠️ **The cache lives on the BOT, not in a module global.** A module-level dict would leak between tests and between guilds in a way nothing could reset; hanging it off `bot._chat_intents` means a fresh fake bot is a fresh cache and `invalidate(bot, guild_id)` is the only way rows go stale. `guild_intents` returns `()` for a DM and for a bot with no connected database rather than raising, so an @-mention during startup gets the code tables instead of a traceback. |

### The data intents

| Key | Note |
|---|---|
| `black_bloc/chat_data.py:225` | ⚠️ **A resolver that throws becomes the EMPTY line, not an exception.** These run inside `on_message`; a schema surprise or a `None` where a row was expected would otherwise take the whole reply down and log an error for something a member did on purpose. "Nothing to report" is the honest degradation, and the warning names the intent so the log still says what broke. Pinned by *a lookup that throws falls back to the empty line*. |
| `black_bloc/chat_data.py:108` | `whats_next` walks `events_by_status(APPROVED)` — which already orders by `starts_at` — and takes the first one still in the future, so an event that started an hour ago is not announced as "next". A **pending** event is never named, because chat must not leak a request staff have not approved. Both pinned. |
| `black_bloc/chat_data.py:125` | The event's own channel (`card_channel_id`) is preferred over the free-text `location` because a channel mention is clickable; the location is the fallback and "the usual place" is the fallback's fallback, so `{where}` is never blank. |
| `black_bloc/chat_data.py:54` | ⚠️ **`clock` formats by hand rather than with `strftime`, because `%-I` is not portable.** The estate develops on Windows and would ship to Linux; `%-I` (no leading zero) is glibc-only and raises on Windows, while `%I` gives "07:05 pm". Written out, both agree. |
| `black_bloc/chat_data.py:81` | A bare clock time in a message is read in the SERVER's zone (`timezones.DEFAULT_TZ`, America/Phoenix, no DST) and then converted into the member's, which is the question "what time is that for me" actually asks. A `<t:…>` stamp needs no such assumption — it is already an instant — so `wanted_time` tries it first. |
| `black_bloc/chat_data.py:202` | ⚠️ **`need_a_mod` is a data resolver even though it is a `route` kind**, because the words differ by state exactly the way a data intent's do: modmail on is the `filled` line, modmail off is the `empty` one with `{roles}` filled from `resolved_staff_roles` — one fact, one home (checklist 15), the same list every refusal message uses. The staff-channel note is NOT here; that is Discord work and lives in the cog. |
| `black_bloc/chat_data.py:163` | `my_roles` is empty-state when picking is OFF or when no menu has options — not when the member happens to hold nothing. Holding nothing is `{have}` = "nothing from them yet", because the useful half of that answer is the list they COULD pick. |

### The cog

| Key | Note |
|---|---|
| `black_bloc/cogs/content/chat.py:153` | ⚠️ **The manners checks run BEFORE the guard, and the guard still runs.** Order matters for the log, not for safety: an ignored channel is a deliberate server choice and gets `log.debug`, while the guard's refusal is the test-mode rule. Neither can be skipped by the other. A DM (`guild_id is None`) skips the manners checks entirely — there is no server whose settings could apply. |
| `black_bloc/cogs/content/chat.py:227` | ⚠️ **The wave is sent with `add_reaction`, which the test-mode guard does NOT patch** — `guard.install()` wraps `http.send_message`, `edit_message` and `delete_channel` only. That is why the channel check earlier in `on_message` is load-bearing rather than belt-and-braces: without it a reaction would go out in any channel under test mode. *The wave obeys the same channel guard the reply does* is the pin. A wave also stamps the cooldown, because it IS an answer — leaving the member un-cooled would let them hold the bot reacting to "hi" forever. |
| `black_bloc/cogs/content/chat.py:244` | ⚠️ **The staff note needs THREE things true — `chat_route_ping_staff`, `modmail_enabled`, and a staff channel the guard allows.** It is only useful when modmail is the way in: with modmail off the member has already been told which roles to ask, and a note asking staff to look at a message nobody can reply to through the bot is noise. A missing `staff_channel_id` is a `log.warning`; the guard refusing is `log.debug`, because under test mode that is expected every single time. |
| `black_bloc/cogs/content/chat.py:50` | The note carries a jump link and pings nobody — `AllowedMentions.none()`, same as the reply (checklist 11). `{who}` is a mention so staff can click through to the member, and it renders as a name without notifying them. |
| `black_bloc/cogs/content/chat.py:116` | ⚠️ **`cog_load` seeds nothing in practice and `on_ready` does the work.** `cog_load` runs inside `setup_hook`, before the gateway connects, so `bot.guilds` is empty; the call is still there because it is free, idempotent, and correct if the cog is ever reloaded on a running bot. `on_guild_join` covers a server added later. `_seeded` stops the 15-query sweep repeating on every reconnect. |
| `black_bloc/cogs/content/chat.py:113` | The `on_change` hooks on the four manners keys drop the cached rows. None of those settings feeds the loader today — the invalidation is one cache miss of insurance so a fifth setting that DOES feed it cannot ship stale, and it is what makes "invalidate on API writes and on_change" true rather than half-true. |
| `black_bloc/cogs/content/chat.py:68` | A thread is told apart by its channel TYPE name (`public_thread` / `private_thread` / `news_thread`) rather than by `isinstance(channel, discord.Thread)`, so the fakes in the tests can be threads without importing half the library. |

### The API

| Key | Note |
|---|---|
| `black_bloc/api/tools/chat.py:156` | ⚠️ **`GET /api/chat/intents` SEEDS a guild that has no rows, which is a write on a read and deliberate.** Without it the Chat page is blank on any bot whose `on_ready` has not fired yet, and "blank" is indistinguishable from "broken". It is the same idempotent call the cog makes, it happens once per guild ever, and every later GET is fifteen selects. Pinned by *a guild never seeded is seeded on the first read*, which also asserts the ids do not move on the second call. |
| `black_bloc/api/tools/chat.py:58` | ⚠️ **A built-in intent can be turned off, re-worded and re-triggered, but never DELETED, and it keeps its name.** The name is the key the bot looks it up by — `BUILTIN_KINDS`, `code_lines` and `DATA_LINES` are all keyed on it, and `chat_data.RESOLVERS` maps `who_is_live` to a function. Renaming `who_is_live` would leave a row that classifies but has no live lookup and no fallback lines. Deleting it would be worse than switching it off, because the code table would answer again as the fallback — so the refusal says "turn it off instead" and means it. |
| `black_bloc/api/tools/chat.py:353` | `POST /api/chat/try` goes through `reader_dependency`, not `writer_dependency`: it changes nothing and writes no action row, and somebody typing sentences into a Try-it box would burn the 60-writes-a-minute budget in seconds. It calls the real `answer_for`, so what the box shows is what the bot would say, live data and all — pinned by *try it renders a data intent with live data* and *try it uses the edited line straight away*. |
| `black_bloc/api/tools/chat.py:148` | A line is reached only through its intent's `guild_id`, so a line id from another server answers 404 rather than being edited. Ids are strings on the way out (one shape for every id on the dashboard) even though these are small autoincrement integers. |
| `black_bloc/api/tools/chat.py:253` | Every write calls `invalidate(bot, guild.id)` before its action row, so the very next @-mention uses the new words. Pinned by *a write drops the cached rows so the bot answers with the new words*. |

### Settings, and why none of them is a mode

| Key | Note |
|---|---|
| `black_bloc/settings_store.py:164` | ⚠️ **The three switches are `bool`, not an off/on `enum`, and that is what keeps them out of the feature list.** `api/status.py:91` treats every key ending in `_mode` as a feature switch unless it is named in `NOT_A_FEATURE`; an enum called `chat_greeting_reaction_mode` would have needed an exemption, and one that did not end in `_mode` would have been an enum for no reason. `golive_embed` and `poll_auto_thread` are the precedent. `chat_ignore_channels` is `channels`, so it defaults to `[]` through the registry's own list clause with no special case. |
| `black_bloc/settings_store.py:801` | `chat_reply_in_threads` defaults **true** and the other two default **false**: answering in a thread is what a member expects from a bot that answers in channels, while a wave instead of a sentence and a ping into the staff channel are both changes of behaviour a server should ask for. `chat_route_ping_staff` off by default also means turning modmail on cannot start a new stream of staff-channel notes by surprise. |
| `site/mock/server.mjs` | The mock had **no `chat` settings namespace at all** — `chat_mode` and `chat_cooldown_seconds` were never added there in step 1. All six now are, added in `f00e8de` when 11b asked for `settings` on the Chat read; without them the mock's `keyRow` had nothing to render. |

### The 11b clarifications, folded in (commit `f00e8de`)

11b built its page against its own mock first and sent back six clarifications;
all six are answered in the real routes, and two of them changed decisions above.

| Key | Note |
|---|---|
| `black_bloc/chat.py:TOKENS` | ⚠️ **The token NAMES changed to the ones the page offers as chips, and the seed lines changed with them** — `{who}` became `{names}` + `{links}`, `{where}` became `{channel}`, birthdays' `{who}` became `{list}`, `my_roles` traded `{can_pick}`/`{have}` for `{menus}`/`{roles}`. The rule that makes this safe is a test: *every token a seeded line uses is one the page advertises*. A chip the page shows must render, so `TOKENS` and `DATA_LINES` can never drift. `need_a_mod` advertises `{roles}` even though 11b said route intents get `[]`, because its own empty-state line uses it and an unexplained token is worse than an extra chip — the one place 11a is a deliberate superset of what was asked. |
| `black_bloc/api/tools/chat.py:chat_settings` | `GET /api/chat/intents` carries `settings`: the chat namespace in the **same row shape `/api/settings` uses**, built by calling `settings_api.key_row` rather than re-deriving it (one fact, one home — checklist 15). `namespace_of` derives `chat` from the key prefix with no override, so the six keys land there on their own and `emoji_skin_tone` stays where it was. |
| `site/mock/server.mjs` chat seed | ⚠️ **The mock's CUSTOM intent is id 1 and its line is id 1, which is not cosmetic.** The contract's PUT / POST-lines / DELETE entries point at `{chat_intent_id}` and `{chat_line_id}`; a built-in refuses DELETE in words, so those ids must land on the custom row or `check.mjs` fails. 11b's own mock used `1` for both, so 11a renumbered to match and the two mocks cannot disagree. |
| `black_bloc/chat.py:258` | 11b asked whether `need_a_mod` could lose "help me" to `help`. It cannot: `need_a_mod` is index **3** in `BUILTIN_ORDER` and `help` is **11**, and the seeded `sort` values follow that same order, so the route is asked first in both the code path and the page's view of it. Pinned by the `("help me", "need_a_mod")` case. |

### ⚠️ 11a and 11b will conflict in exactly two files

Both slices were built on their own branch off `main` @ `ebf99a2`, and both
edited `site/mock/contract.json` and `site/mock/server.mjs` — 11b to give its
page something to talk to, 11a to record the real routes. **Nothing else
overlaps**: 11b owns `site/public/`, 11a owns `black_bloc/` and `tests/`.

When they are merged:

- **The real router is the truth.** `tests/api/test_contract.py` runs the
  contract table against `black_bloc/api/tools/chat.py`, so any row the mock
  and the router disagree about fails there first.
- The eight chat rows should appear **once**, with `settings` and per-intent
  `tokens` present (11a's shape, which answers 11b's clarifications).
- `site/mock/check.mjs`'s `chat_intent_id` / `chat_line_id` are both `'1'` on
  both sides, and both mocks seed a **custom** intent at that id, so the
  DELETE entries resolve either way.
- After merging, run `pytest -q` **and** `node site/mock/server.mjs` +
  `node site/mock/check.mjs`. Passing one proves nothing about the other.

### What was NOT verified

- ⚠️ **No live Discord at all.** No gateway session has run this code: nobody has
  @-mentioned the bot and got an edited line, seen a 👋🏿 land on a message, read
  a staff note with a jump link, or watched `chat.route` appear in the log
  channel. Every assertion is against fakes or a temporary SQLite file.
- ⚠️ **`<t:…:R>` and `<t:…:D>` are strings that have never been RENDERED here.**
  `whats_next` and `birthdays` build HammerTime stamps the way `events.py` and
  `birthdays.py` do, and those are proven elsewhere, but no chat reply carrying
  one has been posted.
- **`time_for_me`'s server-zone assumption is untested against a person.** A bare
  "7pm" is read as Phoenix time; nobody has confirmed that is what members mean.
- **The seed has never run against a real guild**, only against fresh test
  databases. Nothing has migrated a database that already had chat traffic,
  because there is no such database.
- **The mock's Try it is a re-implementation, not the bot.** `site/mock/server.mjs`
  mirrors `normalise` and the classification order in JavaScript; the two halves
  are checked to agree on shape by `check.mjs` and on nothing else.
- **No dashboard page exists**, so nobody has edited a line through a browser —
  every API assertion is `TestClient`.

## logs — dashboard (12b) (2026-08-27)

> Phase 12's second half — the **Logs** page, the Logs section on every feature
> page, and the mock/contract entries — on branch
> `worktree-agent-a7158ae45cbdd06f1` cut from `main` @ `0090fd8`, five commits
> `48927b2` (contract + mock) → `32c8d23` (logs.js + the twelve mounts) →
> `ec70c9b` (the Logs page) → `6e2b6fc` (Overview important-only) → `047b21a`
> (the 390px fix + empty-state wording). Line numbers are as of `047b21a`.
> ⚠️ **Not in `main` yet** — re-key this section on merge.
>
> ⚠️ **12a was building the bot/API half in parallel and this branch touched
> NOTHING under `black_bloc/`.** The pages are written against the route
> contract in the brief and against the mock; `site/mock/contract.json`,
> `server.mjs` and `check.mjs` are the files both halves edit and they are kept
> in their own commit (`48927b2`) so the reviewer can reconcile — **the real
> router wins.**
>
> **Last verified: 2026-08-27** — `node site/mock/check.mjs` **16 pages / 81
> routes, all keys present**; `pytest -q tests/api` **562 passed, 2 failed**,
> and the two are exactly the two `/api/actions` contract rows waiting on 12a
> (`-k "not (test_every_route_answers_with_the_keys_the_pages_read and
> actions)"` is **562 passed, 2 deselected**). Browser pass on the mock at port
> 8811, Chrome, Discord dark and Cyberpunk dark, 1280 and 390 CSS px.

### ⚠️ What the brief's contract did NOT carry, and what the page needed anyway

| Gap | What was done |
|---|---|
| **`actor: {id,name}` vs today's flat `actor_id` / `actor_name`.** The brief writes the row as `actor: {id,name}\|null`, but it also says "today's rows plus `feature`, `important`, `summary`", and Overview, Health and the old Audit page all read the FLAT keys. | `contract.json` requires the **flat** keys plus the three new ones, and the mock sends flat. ⚠️ **The page reads flat only** — if 12a nests them, `logs.js:116` and `page-audit.js` need one accessor each and the contract row needs updating. Called out here rather than hedged in code, because a dual-read path that is never exercised is a second rule nobody tests. |
| **No list of KINDS on the payload.** The feature sections need chips built from "the kinds present for that feature", and no route reports them. | `logs.js:113 kindsFor` reads them once per feature from `GET /api/actions?feature=X&per_page=200` and caches them in a module `Map`. ⚠️ **One extra request per feature page.** 12a could kill it by adding a `kinds` array to the payload. |
| **`total` / `page` / `per_page` / `shown` beside today's `limit` and `notes`.** The brief's payload drops `limit`; three existing pages send `?limit=`. | The mock answers **both** — `limit` is an alias for `per_page` (`server.mjs:988`) — and `contract.json` requires all seven. If 12a drops `limit`, Overview and Health need editing too. |
| **`mod_log_level` would create a `mod` settings namespace**, and `contract.json`'s `/api/settings` entry asserts `no_namespaces: ["mod", "modlog"]`. | `server.mjs:665` overrides it into **`automod`**, exactly as `modlog_channel_id` and `mod_dm_on_action` already are. 12a must add the same line to `black_bloc/api/settings_api.py:NAMESPACE_OVERRIDE` or the contract test fails on both halves. |
| **`birthday`, not `birthdays`.** The design's namespace list says "birthdays"; the registry's namespace is `birthday` (`birthday_mode`, `birthday_template`). | The key is **`birthday_log_level`**. Same for `poll` (not "polls") and `rolemenu` (not "rolemenus"). |
| **Choice ORDER.** `ui.js:703 SEG_FIRST` reorders `on/shadow/off` loudest-first; `off/important/all` is not that set, so it renders in registry order. | The mock registers `['off', 'important', 'all']` per the design and the segment reads **OFF · IMPORTANT · ALL** — quietest first, the opposite of the mode switches. Worth a look; changing it is one array in 12a. |

### `site/public/assets/logs.js` — the new file

| Key | Note |
|---|---|
| ⚠️ `logs.js` exists at all | The brief said `logsSection` goes in `ui.js` ("one home"). It needs `tabHref` (the Members links) and `syncSubnav` (the rail's counts), and **`ui.js` importing `app.js` closes the cycle `ui → app → shell → ui`**; `layout.js → ui.js` is a second edge. So it is one home in its own file — a deliberate deviation from the brief's wording, not from its intent. |
| `logs.js:184` | The section **fetches and pages itself**: `load()` replaces only `results`, never the page. Nothing above it is rebuilt when a filter changes at the foot, and `group.count(total)` + `syncSubnav()` (`:272`) keep the section badge and the "On this page" rail in step — `layout.js:54 paintCount` honours `data-count` when it is set, which is why the count is not re-derived from the visible rows. |
| `logs.js:140` | `kindsFor` is cached per feature for the life of the page. `forgetKinds()` (`:149`) exists for a caller that needs it; nothing calls it today. |
| `logs.js:75` | ⚠️ **Only a MEMBER links to Members.** `nameRecord(id).kind` decides — a role or a channel target (`tempvoice.channel_created` points at a channel, `rolemenu.role_given` at a role) is a name and nothing more, because Members has nothing to say about either. That is why `load` still calls `names()` even though the rows carry `actor_name`/`target_name`: the resolver is what knows the KIND. |
| `logs.js:47` | Every empty state ends with the sentence that undoes the filter hiding the rows. `ROUTINE` (`:47`) adds the feature-specific reason where there is one — Chat and Dashboard have **no** important lines at all by design, so their sections are empty on arrival and say why. |
| `logs.js:123` | The Important switch is the site's own `segment()`, not a checkbox: two values, `Important` and `All`, so the control says what it will show rather than what it is negating. |
| `logs.js:41` | `PER_PAGE` is **10** in a feature section and 25 on the Logs page — a section at the foot of a page is a glance, the page is the archive. |

### `site/public/assets/page-audit.js` — the Logs page

| Key | Note |
|---|---|
| ⚠️ **The file name did not change** | `audit.html`, the tab id `audit` and `tabHref('audit')` all stay; only what a person READS was renamed — the sidebar item (`shell.js:13`), `TABS` (`app.js:21`), the `<title>`, the `<h1>` and the subtitle. Every existing link survives and no redirect exists to rot. `contract.json`'s `pages` list is untouched. |
| `page-audit.js:102` | `logsSurface()` keeps `state` **local**, so a page Refresh starts with clean filters rather than filters the rebuilt pickers cannot show. |
| `page-audit.js:152` | ⚠️ **The export link drops `page` and `per_page`** (`paramsFor(state, { paged: false })`) and carries every other filter. A page of a CSV is not a file. It is rebuilt on every load so the href is never one filter behind. |
| `page-audit.js:274` | The two member pickers get `.pickerrow`, not `.formrow` — see the CSS note. |
| `page-audit.js:89` | The **Settings audit** section is kept: who changed which setting has no other home, and Health keeps its own last-50 (a different question — "is it alive"). |

### `site/public/assets/site.css` — the 390px bug, measured not guessed

| Key | Note |
|---|---|
| ⚠️ `site.css:573` | **`.section-body` is a GRID, and a grid item's automatic minimum size is its CONTENT.** At 390 CSS px the tools row and the five-column table each reported their whole width as a minimum, so the track grew to **671px inside a 309px section** and the table did not scroll inside its own box. `min-width: 0` on `.logs-tools` / `.logs-chips` / `.logs-results` / `.logs-results > .table-scroll` is the fix, and `:577` lets the search box shrink so the row wraps at a useful width. Found by measuring every box edge in a 390px iframe, not by looking. |
| `site.css:582` | `.pickerrow` is the same bug in reverse: a `.formrow` reserves three grid rows (label / control / help) and a `.picker` is a whole block, so two of them left an empty band under the row. |
| `site.css:550` | `.pill.kindpill` — the quiet base `.pill` **is** the routine look, and only `[data-important="true"]` takes the accent tint. A kind is an identifier, so it keeps its own case and the mono face rather than the caps-and-tracking label treatment. |
| `site.css:584` | `.celllink` is `color: inherit` — the name inside keeps `.name`'s weight and the unresolved-id styling; the link adds only an underline on hover and a focus ring. |

### `site/mock/server.mjs` — the fixture and the second copy of the rule

> ⚠️ **GONE in the 2026-08-31 re-key:** `site/mock/server.mjs:GONE (was :548)`, `site/mock/server.mjs:GONE (was :480)` — the construct each note names is no longer in the file; the note itself needs a decision.

| Key | Note |
|---|---|
| ⚠️ `server.mjs:203` | `LOG_FEATURES` / `featureOf` / `IMPORTANT_KINDS` / `isImportant` / `summaryOf` are **the mock's copy of `black_bloc/logkinds.py`**, on purpose, the way `chatWords` is: a fixture that guessed at importance would let the page look right while showing a classification the bot does not make. **The bot's file is the authority** and the reviewer reconciles them. |
| `server.mjs:1702` | `.would_` is checked FIRST and is always routine, before the explicit set and before the suffix backstop — otherwise a kind like `poll.would_ended` would be caught by the `.ended` suffix and marked important. |
| `server.mjs:GONE (was :480)` | `ACTION_TEMPLATES` — 60 (kind, reason, actor, target) rows across all twelve features. `madeUpActions` (`GONE (was :548)`) walks them with a stride of 13 (coprime with 60, so every template lands) and spreads 120 rows over **five weeks** with `14400 + at*60 + at*at*2.4` minutes — denser recently, which is what a real log looks like and what makes a date range worth setting. |
| `server.mjs:720` | `seedActions` numbers the whole list descending from the newest so the hand-written head (`recentActions`, the 23 rows the older pages were built against) keeps its exact content and its order. `SEEDED_ACTIONS` (`:204`) is built once and **cloned** into each `seedState()`, because `logAction` unshifts into `state.actions`. |
| `server.mjs:960` | `since`/`until` are compared as **strings**: ISO-Z stamps sort lexicographically, so a `YYYY-MM-DD` from a date box is padded to `T00:00:00.000Z` / `T23:59:59.999Z` and no clock arithmetic is needed. |
| `server.mjs:891` | `export.csv` is registered **before** `/api/actions` but the two cannot collide anyway — `match()` requires equal segment counts. It is deliberately **not** in `contract.json` (the brief: "link only"), and it is staff-gated: measured **403** for a stranger on both routes. |
| `server.mjs:307` | The twelve `<feature>_log_level` keys are generated from one list rather than written out, because twelve near-identical spec rows is twelve chances to typo one. |

### The mounts, and the two pages the registry did NOT reach on its own

| Key | Note |
|---|---|
| **twelve pages** | `golive`, `events`, `birthdays`, `tempvoice`, `rolemenus`, `automod`, `honeypot`, `modmail`, `polls`, `chat` + `settings` (core) and `moderation` (mod) all end with `await logsSection('<feature>')`. **Verified: 13 Logs sections across the 16 pages** (the twelve, plus the Logs page's own); Overview, Members and Health have none by design. |
| ⚠️ `page-chat.js:26` | Chat lists its settings keys **by name** in `SETTING_KEYS`, so `chat_log_level` had to be added to that list — the registry does not reach it. |
| ⚠️ `page-moderation.js:371` | Moderation had **no settings section at all**. It gets one holding `mod_log_level` and nothing else, picked by key out of whatever namespace the registry puts it in. |
| ⚠️ `page-automod.js:20` | `MOD_KEYS` is added to the Automod page's `omit` list, so `mod_log_level` has **one home** (Moderation) rather than appearing on both. `modlog_channel_id` and `mod_dm_on_action` still live on Automod as before. |
| `page-members.js:24` | Members reads `?q=` from the URL and seeds its search box with it, and `ui.js:145 searchBox` gained a `value` option so the box is drawn filled in rather than emptied on every rebuild. That is what makes a Logs actor link land somewhere useful. |
| `page-overview.js:181` | Overview asks for `important=1`. Ten routine lines used to push the one that acted on somebody off the card. `allLink()` (`:149`) is one shared node for both the filled and the empty card, and `NOTHING_IMPORTANT` (`:145`) says the card is filtered rather than claiming nothing has happened. |

### Measured, not asserted

**16 pages × {1280, 390} × {Discord dark, Cyberpunk dark}, in same-origin
iframes so the media queries evaluate against the real width:**

| | 1280 discord | 1280 cyberpunk | 390 discord | 390 cyberpunk |
|---|---|---|---|---|
| `scrollWidth - innerWidth` | **0** on all 16 | **0** | **0** | **0** |
| console errors/warnings | **none** | none | none | none |
| boxes past the viewport, outside a `.table-scroll` | **0** | 0 | **6, all on `/automod.html`** | **22 on `/automod.html`, 1 on `/settings.html`** |
| side-by-side control groups | 29 | 29 | 2 | 2 |
| misaligned > 1px | **0** (worst spread **0.00px**) | 0 | 0 | 0 |

⚠️ **The 390px overflow is PRE-EXISTING and is not a Logs node.** Traced to
`mod_dm_on_action`'s three-segment control: the value `server_action_reason` is
one nowrap word 5.3px wider than the viewport, which drags `.settings-grid` and
every `.setrow` in it out with it. Nothing 12b added is involved — the new
`_log_level` rows are shorter, and `/settings.html`, which carries all twelve of
them, is clean in Discord dark. The page still does not scroll sideways
(`.content` is `overflow-x: hidden`), so the failure mode is a clipped segment,
not a scrollbar.

**Every filter exercised against the mock** (`/api/actions`, 160 rows seeded):

| filter | result |
|---|---|
| `important=1` | 76 of 160 |
| `feature=golive` | 15 all / 9 important |
| `kind=mod.` | 19 |
| `q=spam` | 30 |
| `since=2026-08-25` | 28 · `until=2026-08-01` 33 · both 36 |
| `actor_id=…` | 60 · `target_id=…` 17 |
| `page=2&per_page=25` | page 2, 25 shown, Previous enabled |
| `feature=chat&important=1` | **0** — the empty state names the switch |
| `export.csv` | 200, `text/csv`, `attachment; filename="black-bloc-logs.csv"`, 161 lines unfiltered / 18 filtered |
| either route as `stranger` | **403** |

**In the browser**, on the Logs page: feature chip → 19 lines, Important→All →
160, Next → "Page 2 · 25 shown", From `08/20/2026` → 37, Done by `Casey` → 4,
Export CSV href became
`/api/actions/export.csv?since=2026-08-20&actor_id=700000000000000002` (no
paging), and an actor link landed on `/members.html?q=Casey` with the box
prefilled and one result. On Go-live: the section's chips are that feature's
seven kinds, `golive.would_announce` + Important gave the "nothing of that kind
was important" sentence, All → 15, Next → "Page 2 · 5 shown" with Next
disabled.

### What was NOT verified

- ⚠️ **Nothing ran against the real API — it does not serve these filters yet.**
  Every assertion is against `site/mock/server.mjs`. The two failing contract
  cases above are the honest record of that.
- ⚠️ **The nested `actor: {id,name}` shape was never exercised**, because the
  page does not read it. See the deviations table.
- ⚠️ **The IMPORTANT set in the mock is a GUESS at 12a's**, not a copy of it —
  `black_bloc/logkinds.py` did not exist when this was written. The reviewer
  must reconcile the two, and the mock's is the one that should give way.
- **No Discord.** Nothing was flipped to `all` and watched to post; the log
  levels are settings rows on a page, not a behaviour anybody has seen.
- **Chrome only, Discord dark and Cyberpunk dark**, 1280 and 390. The other ten
  theme×mode combinations were not opened; the new CSS is token-only, but that
  is inference. **No contrast sampler was run** on `.pill.kindpill`'s accent
  tint — it reuses `--et-accent` at the same 14%/40% mix as `.pill[data-mode]`,
  measured in the site-polish notes, but not re-measured here.
- **The 200-row kinds probe was not measured against a real database.** On the
  mock it is instant; on a busy guild it is one extra query per feature page.
- **`forgetKinds()` has no caller** and was never invoked.

## logs (12a) (2026-08-27)

> **Phase 12 slice a** — quiet Discord, loud website. Importance becomes a property of the
> kind decided in one place, `log_action` gains a per-feature gate, every command group gains
> `/… logs`, and `GET /api/actions` grows the filters the Logs page needs. Built on branch
> `agent-ac3b8dd35b6cc0c5d` off `main` @ `0090fd8`, commits `313fa48`, `e352f33`, `d6f0541`,
> `d4ac492`, `da020f6`, `a6f422b`, `f0a897f`. **The dashboard is 12b and is not here.**
> **Last verified: 2026-08-27** — `pytest -q` **2017 passed** (1941 before, +76).
> `ruff check .` clean. `site/mock/check.mjs` clean at **16 pages, 81 routes**.
> ⚠️ **NOTHING has run against live Discord** — no gateway session, no log channel. Nobody has
> watched a line be suppressed or posted; every claim is against fakes or a temporary SQLite file.

### The classifier, and the three-way table that decides it

| Key | Note |
|---|---|
| `black_bloc/logkinds.py:276` | ⚠️ **`bare()` strips a leading `web.` before anything else looks at a kind, and that halves the table.** `web.role.granted` and `role.granted` are the same event logged from two places, so they must classify and namespace identically or the dashboard's `feature` chip would disagree with the Discord line's gate. The cost is that a web-driven approval that ALSO logs the underlying kind produces two important lines (`web.poll.approved` and `poll.approved`); that is pre-existing behaviour under today's `all`, and the second line is the provenance. Where the two strings genuinely differ (`web.honeypot.ban` vs `honeypot.banned`, `web.modmail.close` vs `modmail.closed`) the web line is deliberately ROUTINE so the pair is one Discord line, not two. |
| `black_bloc/logkinds.py:35` | `HEADS` is the one alias table: `role` / `role_menu` / `rolemenu` → `rolemenu`, `event` / `events` → `events`, `case` → `mod`, `settings` / `commands` / `presence` → `core`, and anything unknown → `core`. ⚠️ It is read **twice** — by `feature_of` for the gate, and by `like_patterns` to build the SQL `LIKE` forms — so the query and the classifier cannot drift. `role_menu.update` and `role.granted` are distinct heads because `partition(".")` splits on the first dot only. |
| `black_bloc/logkinds.py:301` | ⚠️ **Every `.would_` kind is routine by RULE, not by being listed** (owner, 2026-08-27: *"lets mute all the would calls too, keep that in discord logs"*). `is_shadow` is checked before anything else, so a dry run can never borrow the word it is only pretending to do — `mod.would_ban` cannot reach Discord on the strength of `.ban`. Written as a rule because the alternative is thirty-odd names that a thirty-first shadow kind would quietly not join; the thirty were **deleted from `ROUTINE`** in the same change, so there is one home for the decision and `test_every_shadow_kind_is_routine_by_rule_not_by_being_listed` fails if anybody re-lists one. Nothing was reclassified by it — the counts below are the same either way; what changed is that they now stay true on their own. |
| `black_bloc/logkinds.py:128` | ⚠️ **`ROUTINE` WINS over both `IMPORTANT` and the suffix rules, and that precedence is what earns it.** `.closed` and `.ban` are modmail's and moderation's words; polls and the temp-voice panel borrow them. `poll.closed` is a poll ending on schedule, not a ticket being closed. `tempvoice.kick` / `.ban` / `.unban` are a member managing their **own** temporary channel — not Black Bloc acting on somebody on the server's behalf — so all four sit in `ROUTINE` and the suffixes never see them. Pinned by *the routine set beats a suffix*. |
| `black_bloc/logkinds.py:110` | The line `IMPORTANT` draws: **the bot changed a member's standing** (`automod.deleted`, `mod.unbanned`, `mod.untimed_out`, `role.extended`, `modmail.unblocked`), **a human decision landed** (`event.cancelled`, `poll.cancelled`), or **something failed or was silently skipped** (`golive.role_stuck`, `event.missed`, `event.announce_skipped_late`, `mod.warn_threshold`). Automation's own role churn is NOT one: `golive.add_role` and `birthday.add_role` fire on every stream and every birthday, and a server that wants them can set `all`. |
| `black_bloc/logkinds.py:314` | ⚠️ **An unrecognised level is `all` — today's behaviour — never `off`.** A fake store returning `None`, a key that has not been written, a store that has not loaded: none of those is a decision to go quiet, and the failure mode of guessing `off` is a silently missing audit trail that nobody notices. Pinned by *an unknown level is today's behaviour*. |
| `black_bloc/logkinds.py:292` | `like_patterns` emits both `head.%` and `web.head.%` per head; `feature_clause` in `actionlog.py` asks `core` **backwards** (`NOT (…)` over every other feature's patterns) because `core` is defined as everything nobody else claims and SQL cannot express that forwards. |

### The test that makes silence impossible by accident

| Key | Note |
|---|---|
|  `tests/test_logkinds.py:222` | The scanner walks `black_bloc/**` with `ast`, takes the **third positional argument** of every `log_action(` call, and unwraps an `IfExp` into both branches. Anything else — an f-string, a bare name, a module constant — must appear in `KNOWN_DYNAMIC` or the test fails naming the file and the expression. |
|  `tests/test_logkinds.py:39` | ⚠️ **`KNOWN_DYNAMIC` is keyed `"<path>::<expression source>"`, NOT by line number**, because 12a itself moved every one of those lines when it inserted the `logs` commands. A line-keyed table would have been stale before it was committed. A stale entry is caught too: the test asserts every key still matches a live call site. |
|  `tests/test_logkinds.py:302` | The dead-entry test (`no classification entry is dead`) is the other half: a kind named in `IMPORTANT` or `ROUTINE` that nothing emits is a table nobody maintains, so it fails as loudly as an unclassified one. Both sets were exactly right on the first run, which is only worth recording because it means the two lists were derived from the scan rather than from memory. |

### Every kind, by feature — 269 kinds, 88 important, 181 routine

The counts are what the scanner found on 2026-08-27; the test is what keeps them true.

| Feature | Important | Routine |
|---|---|---|
| `core` | 0 | 6 |
| `automod` | 5 | 8 |
| `honeypot` | 3 | 11 |
| `mod` | 14 | 8 |
| `modmail` | 8 | 20 |
| `golive` | 2 | 16 |
| `events` | 14 | 18 |
| `birthday` | 3 | 17 |
| `tempvoice` | 14 | 27 |
| `rolemenu` | 13 | 19 |
| `poll` | 12 | 23 |
| `chat` | 0 | 8 |

#### `core` — 0 important, 6 routine

**Routine:** `commands.visibility`, `presence.bio_set`, `settings.clear`, `settings.set`, `web.settings.clear`, `web.settings.set`

#### `automod` — 5 important, 8 routine

**Important:** `automod.delete_failed`, `automod.deleted`, `automod.timed_out`, `automod.timeout_failed`, `automod.warned`

**Routine:** `automod.exempt_add`, `automod.exempt_remove`, `automod.mode`, `automod.observed`, `automod.rule`, `automod.would_delete`, `automod.would_timeout`, `automod.would_warn`

#### `honeypot` — 3 important, 11 routine

**Important:** `honeypot.ban_failed`, `honeypot.banned`, `honeypot.delete_failed`

**Routine:** `honeypot.exempt`, `honeypot.exempt_add`, `honeypot.exempt_remove`, `honeypot.hit_recorded`, `honeypot.mode`, `honeypot.setup`, `honeypot.trap_removed`, `honeypot.would_ban`, `honeypot.would_delete`, `web.honeypot.ban`, `web.honeypot.setup`

#### `mod` — 14 important, 8 routine

**Important:** `mod.ban_failed`, `mod.banned`, `mod.kick_failed`, `mod.kicked`, `mod.purge_failed`, `mod.purged`, `mod.timed_out`, `mod.timeout_failed`, `mod.unban_failed`, `mod.unbanned`, `mod.untimed_out`, `mod.untimeout_failed`, `mod.warn_threshold`, `mod.warned`

**Routine:** `mod.would_ban`, `mod.would_kick`, `mod.would_purge`, `mod.would_timeout`, `mod.would_unban`, `mod.would_untimeout`, `web.mod.apply`, `web.mod.rule`

#### `modmail` — 8 important, 20 routine

**Important:** `modmail.blocked`, `modmail.closed`, `modmail.dm_failed`, `modmail.open_failed`, `modmail.relay_failed`, `modmail.remove_place_failed`, `modmail.transcript_failed`, `modmail.unblocked`

**Routine:** `modmail.blocked_dm`, `modmail.category_forgotten`, `modmail.forgotten`, `modmail.log_channel_forgotten`, `modmail.member_left`, `modmail.opened`, `modmail.place_kept`, `modmail.settings`, `modmail.snippet_removed`, `modmail.snippet_saved`, `modmail.staff_channel_forgotten`, `modmail.transcript`, `modmail.would_post_transcript`, `modmail.would_remove_place`, `web.modmail.block`, `web.modmail.close`, `web.modmail.reply`, `web.modmail.snippet`, `web.modmail.snippet_remove`, `web.modmail.unblock`

#### `golive` — 2 important, 16 routine

**Important:** `golive.post_failed`, `golive.role_stuck`

**Routine:** `golive.add_role`, `golive.announce`, `golive.end`, `golive.mode`, `golive.optin`, `golive.optout`, `golive.remove_role`, `golive.test`, `golive.unlink`, `golive.would_add_role`, `golive.would_announce`, `golive.would_remove_role`, `web.golive.link`, `web.golive.optin`, `web.golive.optout`, `web.golive.unlink`

#### `events` — 14 important, 18 routine

**Important:** `event.announce_failed`, `event.announce_skipped_late`, `event.approved`, `event.cancel_scheduled_failed`, `event.cancelled`, `event.card_failed`, `event.channel_failed`, `event.create_scheduled_failed`, `event.denied`, `event.dm_failed`, `event.edit_announcement_failed`, `event.go_live_failed`, `event.missed`, `event.rename_failed`

**Routine:** `event.announce`, `event.announce_channel_forgotten`, `event.announcement_edited`, `event.category_forgotten`, `event.channel_deleted`, `event.created`, `event.done`, `event.go_live`, `event.settings`, `event.would_announce`, `event.would_cancel_scheduled`, `event.would_create_scheduled`, `event.would_delete_channel`, `event.would_edit_announcement`, `event.would_go_live`, `event.would_post_card`, `event.would_rename`, `web.event.cancel`

#### `birthday` — 3 important, 17 routine

**Important:** `birthday.add_role_failed`, `birthday.announce_failed`, `birthday.remove_role_failed`

**Routine:** `birthday.add_role`, `birthday.announce`, `birthday.import`, `birthday.member_missing`, `birthday.mode`, `birthday.optin`, `birthday.optout`, `birthday.remove`, `birthday.remove_role`, `birthday.set`, `birthday.would_add_role`, `birthday.would_announce`, `birthday.would_remove_role`, `web.birthday.clear`, `web.birthday.import`, `web.birthday.optin`, `web.birthday.set`

#### `tempvoice` — 14 important, 27 routine

**Important:** `tempvoice.ban_failed`, `tempvoice.bitrate_failed`, `tempvoice.create_failed`, `tempvoice.delete_failed`, `tempvoice.limit_failed`, `tempvoice.move_failed`, `tempvoice.panel_failed`, `tempvoice.permit_failed`, `tempvoice.privacy_failed`, `tempvoice.region_failed`, `tempvoice.rename_failed`, `tempvoice.repair_failed`, `tempvoice.unban_failed`, `tempvoice.unpermit_failed`

**Routine:** `tempvoice.adopt`, `tempvoice.ban`, `tempvoice.bitrate`, `tempvoice.claim`, `tempvoice.create`, `tempvoice.creator_removed`, `tempvoice.delete`, `tempvoice.hide`, `tempvoice.kick`, `tempvoice.limit`, `tempvoice.lock`, `tempvoice.mode`, `tempvoice.panel_elsewhere`, `tempvoice.permit`, `tempvoice.prefs_reset`, `tempvoice.region`, `tempvoice.rename`, `tempvoice.repair`, `tempvoice.setup`, `tempvoice.show`, `tempvoice.transfer`, `tempvoice.turned_away`, `tempvoice.unban`, `tempvoice.unlock`, `tempvoice.unpermit`, `web.tempvoice.forget`, `web.tempvoice.setup`

#### `rolemenu` — 13 important, 19 routine

**Important:** `role.approve_failed`, `role.approved`, `role.denied`, `role.expire_failed`, `role.expired`, `role.extended`, `role.granted`, `role.request_card_failed`, `role_menu.repost_failed`, `role_menu.unpost_failed`, `web.role.ended`, `web.role.extended`, `web.role.granted`

**Routine:** `role.changed_by_hand`, `role.reconciled`, `role.requested`, `role.withdrawn`, `role_menu.assign`, `role_menu.delete`, `role_menu.edit`, `role_menu.mode`, `role_menu.post`, `role_menu.reposted`, `role_menu.unassign`, `role_menu.unposted`, `role_menu.update`, `role_menu.would_repost`, `role_menu.would_unpost`, `web.rolemenu.create`, `web.rolemenu.delete`, `web.rolemenu.edit`, `web.rolemenu.post`

#### `poll` — 12 important, 23 routine

**Important:** `poll.approved`, `poll.cancelled`, `poll.card_failed`, `poll.denied`, `poll.end_failed`, `poll.open_failed`, `poll.recur_failed`, `poll.remind_failed`, `poll.results_failed`, `poll.thread_failed`, `web.poll.approved`, `web.poll.denied`

**Routine:** `poll.archived`, `poll.channel_forgotten`, `poll.closed`, `poll.created`, `poll.opened`, `poll.recur_created`, `poll.recur_deleted`, `poll.recur_paused`, `poll.recur_resumed`, `poll.recurred`, `poll.reminded`, `poll.settings`, `poll.would_cancel`, `poll.would_close`, `poll.would_open`, `poll.would_post_results`, `poll.would_remind`, `web.poll.cancel`, `web.poll.created`, `web.poll.end`, `web.poll.recur_deleted`, `web.poll.recur_paused`, `web.poll.recur_resumed`

#### `chat` — 0 important, 8 routine

**Routine:** `chat.insult`, `chat.route`, `web.chat.intent_created`, `web.chat.intent_deleted`, `web.chat.intent_edited`, `web.chat.line_added`, `web.chat.line_deleted`, `web.chat.line_edited`

⚠️ **`core` and `chat` have NO important kinds at all**, which is the point: at the default
`important` those two features go completely quiet on Discord and live only on the website.
`golive` has two, so the busiest feature drops from a line per stream to a line per failure.

### The gate

| Key | Note |
|---|---|
| `black_bloc/actionlog.py:107` | The signature is unchanged apart from `notify: bool = False`. ⚠️ **The DB row is written FIRST and unconditionally**, and only then is the level read — so a store that is not loaded yet, or a level nobody can parse, can never cost a row. The embed is not even BUILT when the gate says no, which is why `build_embed` moved inside the `if`. |
| `black_bloc/actionlog.py:86` | `level_for` returns `all` for three separate "we cannot tell" cases: no `store` on the bot, no `id` on the guild (a `discord.Object` stand-in, or a DM), and a store that raises. The third logs a warning naming the kind. ⚠️ Most of the existing cog tests pass unchanged **because of this** — their fake stores return `None` for an unknown key, which is not one of the three levels, so they still see today's behaviour. |
| `black_bloc/actionlog.py:107` | ⚠️ **Approval cards were never `log_action` calls and are untouched** (decision 2). They are their own `channel.send` in the events, role-menu and poll cogs. `tests/cogs/community/test_role_menus.py`'s *the request card is a notification and ignores the log level* sets `rolemenu_log_level = off`, makes a request, and asserts the card is still there — that test exists to fail if anybody ever routes a card through `log_action`. |
|  `black_bloc/actionlog.py:116` | `notify=True` forces the line through **any** level including `off`. Nothing passes it today; it is the hook decision 2 asked for, and it is pinned so it cannot rot. |
| test mode | Unchanged, and deliberately so: `_post` calls `channel.send`, and `guard.install()` patches `http.send_message` underneath it, so the guarded path is the only path. The gate is a decision about *whether to try*, not a way around the guard. |

### The shared renderer and the twelve `logs` commands

| Key | Note |
|---|---|
| `black_bloc/actionlog.py:158` | `feature_clause` derives its SQL from `logkinds.HEADS` rather than repeating the prefixes — one fact, one home (checklist 15). Duplicating them was the obvious first cut and would have meant a new feature namespace silently returning nothing on the website while the Discord gate worked fine. |
| `black_bloc/actionlog.py:171` | ⚠️ **`important_only` scans up to `SCAN_LIMIT` rows and filters in Python, because importance is not a column.** Without the wider scan, asking for 10 important lines out of 500 routine ones would return an empty list and read as "nothing has happened". The plain path still asks SQL for exactly `limit`. |
| `black_bloc/actionlog.py:234` | The line is `<t:…:R> · \`kind\` · <@actor> → <@target> · summary`, with the part after the stamp capped at 100 characters and an ellipsis. The stamp is outside the cap because a truncated `<t:…>` renders as literal text rather than a time. An unparseable `at` falls back to the stored string (pinned) rather than raising inside a slash command. |
| `black_bloc/actionlog.py:286` | `send_logs` is the **entire body** of all twelve commands: guild/staff gate, database check, renderer, ephemeral embed, `AllowedMentions.none()`, footer. ⚠️ **Because the gate it calls is `require_staff`, `settings_store.is_staff_command` finds it for free** — that function follows the callback's `co_names` into module-level helpers, so every `logs` command is hidden from non-staff by `command_visibility` with no `extras={"staff_only": True}` needed. Pinned by *a logs command is staff only and ephemeral*, which would fail if `send_logs` ever stopped calling `require_staff` directly. |
| `black_bloc/cogs/moderation/modcmds.py:392` | ⚠️ **`/mod` is a NEW top-level group and the moderation commands stay where they are.** `/warn`, `/timeout`, `/kick`, `/ban`, `/purge`, `/case`, `/cases` have always been top-level; moving them into `/mod` would have broken every muscle memory and every doc. `/mod` holds `logs` and nothing else for now. |
| `black_bloc/cogs/content/chat.py:78` | `/chat` is the other new group — chat had none at all. It carries `logs` and a **read-only** `settings` that lists the seven `chat_*` keys with `display_value` and points at `/settings set` and the dashboard for changes. Read-only on purpose: `/settings set` already changes any key, and a second writer would be a second home for the same decision. |
| `black_bloc/cogs/community/tempvoice.py` | ⚠️ **`logs` went on `/voice`, not `/tempvoice`**, because the design named `/voice`. It is staff-gated all the same, so a member sees a group whose other seventeen commands are theirs and one that is not. If that reads wrong in use, moving it to `/tempvoice` is a one-line change — the body is shared. |
| `tests/test_bot.py:87` | The tree is **34 top-level commands** after 12a (32 before; `/mod` and `/chat` are the two new ones) against Discord's 100, and no group is near the 25-child ceiling — `/voice` is the fullest at 18. Both ceilings are asserted rather than reasoned about. |
## requests (13a) (2026-08-27)

> **F18, slice a of two** — `/request`, the `requests` tables, the
> `/api/requests` routes and the site's first non-staff gate. Built on branch
> `worktree-agent-ae90babf488323552` off `main` @ `40b7782`, commits `5d637b4`
> (storage), `e7e0f9e` (settings), `cf23268` (cog), `27ec297` (API + member
> gate), `415eb8c` (contract + mock). The dashboard **Requests** page is **13b**
> and does not exist yet. **Last verified: 2026-08-27** — `pytest -q` **2062
> passed** (1941 before, **+121**). `ruff check .` clean.
> `node site/mock/check.mjs` clean at **88 routes** (80 before). Updated for
> 13b's clarifications (due date, `assignee=none`, name search, the id
> placeholders): `pytest -q` **2071 passed**, **+130**.
> ⚠️ **NOTHING has been run against live Discord** — no gateway session, no
> `/request`, no modal submitted, no DM sent, no notice line posted. Every claim
> about what Discord does is read off the installed library or off a fake.

### The one deviation from the brief

| Key | Note |
|---|---|
| `black_bloc/cogs/community/requests.py:245` | ⚠️ **The brief says `/request` opens the modal; it is `/request create`.** Discord cannot have a command group called `request` *and* a bare `/request` — the group owns the name, and `list` / `withdraw` / `set` need the group. `create` is what `/event create` and `/poll create` already use, so it is the name a member has met before. |

### Storage

| Key | Note |
|---|---|
| `black_bloc/storage/db.py:364` | `requests` is additive and `SCHEMA_VERSION` goes 15 → 16. No `ADDED_COLUMNS` entry is needed: nothing had these tables before, so `CREATE TABLE IF NOT EXISTS` is the whole migration. |
| `black_bloc/storage/db.py:383` | The index is `(guild_id, status, id)` rather than the `(guild_id, status)` the brief named. The `id` on the end is free and it is what makes the list's own `ORDER BY … id DESC` an index scan instead of a sort. |
| `black_bloc/storage/db.py:385` | ⚠️ **`request_comments.request_id` is `REFERENCES requests(id) ON DELETE CASCADE`, and `db.py:387` already sets `PRAGMA foreign_keys=ON`** — so deleting a request takes its thread with it rather than leaving orphan rows nothing can reach. Pinned by `tests/storage/test_db.py`'s *a request's comments go when the request does*. Nothing deletes a request today; `withdrawn` and `declined` are states, not deletions. |
| `black_bloc/requests.py:290` | ⚠️ **`ORDER BY (status <> 'pending'), id DESC` — pending first, then newest — is done in SQL, and `limit`/`offset` are passed straight through.** The first cut read every row and sliced in Python, which is fine at fifty requests and wrong at five thousand. `page_of` at `:221` still exists, but only for the SLASH command, where the rows are already in hand and a Discord message caps the list anyway. |
| `black_bloc/requests.py:348` | ⚠️ **`set_status` clears `decline_reason` on any move that is not a decline, and stamps `done_at` only on the move to `done`.** A request declined "we already have one" and later approved would otherwise still be carrying the sentence that says it was refused, and the page would show both. `decided_by`/`decided_at` use `COALESCE`, so a later move that names nobody (a withdrawal) does not erase who decided it first. Pinned by *moving to done stamps when and moving off declined forgets the reason*. |
| `black_bloc/requests.py:375` | `set_fields` takes `...` for "leave it alone" and `None` for "clear it", and returns the names it actually wrote. That is what lets `POST …/status` tell a save that changed nothing (refused) from one that cleared a field (allowed), and what keeps `web.request.updated`'s `changed` list honest. |

### What a person may type

| Key | Note |
|---|---|
| `black_bloc/requests.py:132` | `parse_due` uses `date.fromisoformat`, so `2026-02-30` and `2026-13-01` are refused as firmly as `next tuesday` — a shape check with a regex would have taken both. An empty box is `None`, never an error: the due date is optional and a member who leaves it blank has not made a mistake. |
| `black_bloc/requests.py:147` | ⚠️ **`due_on` is a plain `YYYY-MM-DD` STRING everywhere — stored, sent and taken — and only ever becomes an instant at render time.** `due_stamp` builds `<t:…:D>` from **local midnight in the server's zone** (`timezones.DEFAULT_TZ`, America/Phoenix, a fixed UTC-7), so the stamp reads as the day the person typed rather than the day before it. Midnight UTC would flip the date for every reader west of UTC, the owner included; an ISO instant on the wire would make the dashboard guess a zone. Pinned by *the due stamp is local midnight in the server's zone, not UTC*. |
| `black_bloc/requests.py:187` | `checked_fields` refuses What before Why, so the sentence a person gets names the box they left empty rather than "fill it in". Both are then cut to 1000, which is what the modal's `max_length` already enforces — the API has no such enforcement, so the cut is the one that matters. |
| `black_bloc/requests.py:40` | `STATUS_WORDS` is the vocabulary in one place, and the API sends it as `status_word` beside `status`. Without it the dashboard would carry a second copy of the mapping and the two would drift the first time a state was renamed. |

### The cog

| Key | Note |
|---|---|
| `black_bloc/cogs/community/requests.py:73` | ⚠️ **`submit` asks the guard BY HAND at `:264`, because a modal submission never goes through `tree.interaction_check`.** `guard.install()` patches `http.send_message` and sets `tree.interaction_check`, and neither one sees a modal reply: the interaction response goes out on a different endpoint, and the check only wraps app commands. This is the same rule the polls cog writes down at `cogs/community/polls.py:1421`. Pinned by *a modal sent from outside the test channel is refused by hand*. |
| `black_bloc/cogs/community/requests.py:130` | ⚠️ **`notify` SKIPS a channel the guard refuses rather than raising, and the request is filed either way.** The notice is a courtesy; the row is the point. Raising would mean that setting `request_notify_channel_id` to anything but the test channel while `TEST_MODE` is on would break filing altogether. A channel that refuses the post for a real reason (permissions, an outage) is a logged `request.notify_failed`, so a silent nothing is still a visible fact. |
| `black_bloc/cogs/community/requests.py:161` | `apply_decision` is the one path a status moves by, and both the slash command and the API call it — so the DM, the `request.<status>` line and the "already **x**" refusal cannot differ between the two. It returns `(said, fresh)` with `fresh is None` meaning nothing moved, the shape `role_menus.apply_request_decision` already uses. |
| `black_bloc/cogs/community/requests.py:108` | A DM that bounces is a `request.dm_failed` row, never a swallowed exception — a member who blocks the bot or leaves the server must not make a staff decision look like it failed. `bot.get_user` is the fallback when `guild.get_member` has nothing, so somebody who has left is still tried once. |
| `black_bloc/cogs/community/requests.py:279` | ⚠️ **The auto-approve test is `store.is_staff(interaction.user)`, which is `settings_store.resolved_staff_roles` — the SAME derivation the dashboard's own gate uses**, via `api/auth.py:is_admitted`. Anything else here would mean a mod is auto-approved on the site and held in Discord, or the other way round. |
| `black_bloc/command_visibility.py:16` | `request_mode` joins `rolemenu_mode` in `HIDDEN_WHEN_OFF`, so turning requests off takes the whole `/request` group out of the dev guild's tree. Nothing else changes: `requests_are_on` is still checked inside the commands, because the tree sync is debounced and a member can beat it. |

### The member gate — the site's first non-staff write

| Key | Note |
|---|---|
| `black_bloc/api/writes.py:95` | ⚠️ **`member_dependency` is declared on exactly THREE routes and nowhere else** — `POST /api/requests`, `GET /api/requests/mine`, `POST /api/requests/{id}/withdraw`. Everything else in the API, this router's own six staff routes included, still goes through `staff_dependency` / `writer_dependency` / `reader_dependency`. Pinned by *the member routes are the only three that are not staff only*, which walks the other seven and asserts 403 for a member session. |
| `black_bloc/api/auth.py:203` | `live_member` mirrors `live_staff`: `(member, known)`, with `known` false only when the bot is not ready or the guild cannot be reached. It is a **live** cache lookup, never the cookie — a person who left the server stops being able to file the moment the gateway notices, without waiting seven days for their session to expire. |
| `black_bloc/api/writes.py:31` | ⚠️ **Ten a minute per person, against sixty for a staff write.** A member write is the only one an unvetted account can reach, so it gets the login route's order of magnitude rather than the dashboard's. Its bucket is its own (`_api_member_bucket`), so filing a request cannot spend a staffer's write allowance and a flood of requests cannot lock a mod out of the moderation page. |
| `black_bloc/api/auth.py:51` | ⚠️ **`/api/auth/me` gained `member`, and `state` deliberately did NOT change.** `site/public/assets/app.js:182` gates the whole dashboard on `me.staff` and shows `me.message`; changing `state` would have moved that gate for every existing page. What did change is the sentence: a signed-in **member** who is not staff now gets `MEMBER_NOT_STAFF` — the dashboard is staff-only, but you can still file a request — because the old `NOT_STAFF` ("ask a Lead for the role") is now wrong advice for somebody who has something they *can* do. Somebody signed in who is **not** in the guild still gets the old sentence. |
| `black_bloc/api/tools/requests.py:246` | `_may_file` raises for both refusals and returns the auto-approve answer, so the route reads as one line and the two refusals cannot get out of order — `request_mode = off` is a 409 about the feature, `request_who_can_file = staff` is a 403 about the caller, and a member meets them in that order. |

### The API

| Key | Note |
|---|---|
| `black_bloc/api/status.py:332` | ⚠️ **The filters split across two engines and the split is not arbitrary.** Guild, kind, user, feature and the dates are columns, so SQL does them. Importance is a Python predicate over the kind, and `q` searches actor and target **display names** that only exist after `names.named()` has resolved them — neither can be a `WHERE` clause without duplicating the classifier in SQL or denormalising names into the table. |
| `black_bloc/actionlog.py:35` | The consequence is a **5000-row scan cap**, and the honest half is that `notes` says so when the cap is hit rather than reporting a smaller `total` as if it were the whole truth. |
| `black_bloc/api/status.py:238` | ⚠️ **`kinds` follows `feature` ALONE, not the rest of the filters.** They are the page's chips: if a search that matches nothing also emptied the chips, there would be no way to click back out of it. Pinned by *the chips are what this guild logged, not the page it asked for*. |
| `black_bloc/api/status.py:217` | `summary` is on every row even when `details` is withheld, and it is computed by the same `actionlog.summary_of` the Discord line uses — so the website and the ephemeral embed cannot describe the same action differently. Actor and target stay **flat** (`actor_id`/`actor_name`/…) because Overview, Health and Logs all read them that way. |
| `black_bloc/api/status.py:303` | A bare `until=2026-08-27` is pushed to the **end** of that day. Read as midnight it would silently exclude everything that happened on the day the person asked for, which looks like missing data rather than a filter. |
| `black_bloc/api/status.py:471` | `export.csv` is **deliberately not in `contract.json`**, the same call the polls export made: `check.mjs` validates JSON shapes and this one answers `text/csv`. Its refusals are the list route's refusals, because it shares `searched_actions`. |
| `black_bloc/api/settings_api.py:35` | ⚠️ **`mod_log_level` is namespaced to `automod` by override**, joining `modlog_channel_id` and `mod_dm_on_action`. The contract asserts `no_namespaces: [mod, modlog]`, and the moderation settings already live under `automod`; a lone `mod` namespace would have broken `check.mjs` and `test_contract.py` at once. |
| `site/mock/server.mjs` | The mock mirrors just enough of `logkinds.py` (heads, suffixes, and the four routine overrides its own seed needs) to sort and mark its seed rows. ⚠️ **It is a mirror, not a source** — the router is the truth and `test_logkinds.py` is what guards it. The two halves are checked to agree on shape by `check.mjs` and on nothing else. |

### Settings

| Key | Note |
|---|---|
| `black_bloc/settings_store.py:438` | The twelve keys are **generated from `logkinds.FEATURES`**, not typed out, so a thirteenth feature cannot exist without its key. `settings_store` importing `logkinds` is safe: `logkinds` is pure and imports nothing from the package. |
| `black_bloc/settings_store.py:809` | The default is `important` for every one, matched on the `_log_level` suffix rather than a twelve-way `if`. |
| `black_bloc/settings_store.py:430` | ⚠️ **The help text names the slash command for eleven of the twelve and omits it for `core`**, because `core` is the one feature with no `/… logs`. A help string promising `/settings logs` would have been a lie the page shows to a Lead. |
|  `black_bloc/logkinds.py:16` | `LEVELS` is ordered `off`, `important`, `all` — quietest first, which is the order 12b's segment renders. |

### What CHANGED for the existing tests, and why that was right

Three existing assertions said a Discord line appears for a **routine** kind, which is exactly
the behaviour 12a set out to change. Each was updated to assert the quiet **and** the level flip
that brings the line back, so the change is pinned in both directions rather than weakened:

- `tests/test_actionlog.py` — three tests now set the feature's level to `all` first.
- `tests/cogs/moderation/test_honeypot.py` — `honeypot.exempt` is quiet, then posts at `all`.
- `tests/test_presence.py` — `presence.bio_set` is quiet, plus a new test at `core_log_level = all`.
- `tests/cogs/community/test_tempvoice.py` — `/voice`'s command list gained `logs`.

### What was NOT verified

- ⚠️ **No live Discord at all.** No gateway session has run this code. **Nobody has watched a
  line be suppressed, or watched one arrive.** Every claim about the gate is a fake channel's
  `sent` list.
- ⚠️ **No `/… logs` command has been run in Discord.** The embeds are asserted as objects; no
  `<t:…:R>` stamp built here has ever been RENDERED, and the 100-character line cap has never
  been looked at in a real client where mentions expand to display names.
- **The 34-command tree has never been synced.** `test_bot.py` builds it in memory; Discord has
  not been asked to accept `/mod` or `/chat`, and no `command_sync` has run.
- **The 5000-row scan cap has never been hit.** No database here has more than a few dozen action
  rows, so the truncation note is asserted by construction, not observed.
- **The CSV has never been opened in a spreadsheet** — only asserted as text.
- **Nothing has been deployed**, and no owner sweep from the design's definition of done has been
  run (flip `golive_log_level` to `all`, `/golive test`, see the line; flip back, see only the row).

## requests — dashboard (13b) (2026-08-27)

> Phase 13's second half — the **Requests** page — on branch
> `worktree-agent-acd6d4a9712a56eb0` cut from `main` @ `40b7782`, two commits
> `a260e1b` (contract + mock) → `fec0f57` (the page). Line numbers are as of
> `fec0f57`. ⚠️ **Not in `main` yet — re-key this section on merge.**
>
> ⚠️ **13a is building the bot/storage/API half in parallel and this branch
> touched NOTHING under `black_bloc/` or `tests/`.** The page is written against
> the route contract in the brief and against the mock; `site/mock/contract.json`,
> `server.mjs` and `check.mjs` are the three files both halves edit and they are
> kept in their own commit (`a260e1b`) so the reviewer can reconcile.
>
> ⚠️ **12b was landing `logs.js` / `logsSection()` in parallel**, so this page has
> **no Logs section** and `page-audit.js` / `audit.html` were not touched. One line
> is owed once 12b is in: `await logsSection('request')` at the foot of `load()`.
>
> **Last verified: 2026-08-27 ~18:00** — `node site/mock/check.mjs` **17 pages / 88
> routes, all keys present**; `pytest -q tests/api` **563 passed, 8 failed**, and
> the eight are exactly the eight new request contract routes answering 404
> because the real API does not serve them yet (`-k "not api/requests"` is **563
> passed, 8 deselected**). Browser pass on the mock at port 8902, Chrome, Cyberpunk
> dark, Cyberpunk light and Discord dark, 1280 and 390 CSS px.

### ⚠️ The owner's mid-build ask: "also let people put request on the dashboard too"

This arrived after the page was half built and it is the largest thing here,
because it is the **first non-staff surface on the whole dashboard**.

| Key | Note |
|---|---|
| `site/public/assets/app.js:176` | `refuseFor(me, tab)` gained the tab. A signed-in member who is not staff is **neither a dashboard nor a gate**: on `requests` it returns false and the page renders; on any other tab it `location.replace`s to Requests. ⚠️ That is what makes `/index.html` send a member somewhere useful instead of showing them "This dashboard is for staff". A **stranger** (signed in, not a guild member) still gets that gate — verified against `?as=stranger`. |
| `app.js:165` | `rememberedMe()` accepted `staff === true` only, so a member's session cache was thrown away on every page load and every visit re-asked `/api/auth/me`. It now accepts `member === true` as well. |
| `shell.js:4` | `MEMBER_TAB` and `isMemberOnly(me)` live in `shell.js` because the rail is what they are about; `app.js` imports both rather than deciding twice. |
| `shell.js:264` | `paintNavFor(member)` **hides links rather than rendering a second nav.** `renderNav` runs before `me` is known (it is synchronous at the top of `start()`), so a member-aware renderer would have to be re-run anyway; hiding is the same result with one nav builder. A group whose every link is hidden hides itself, so the member sees `OVERVIEW → Requests` and nothing else. |
| `shell.js:253` | ⚠️ **A member is asked for NO tally at all.** `/api/status`, `/api/members`, `/api/rolemenus/requests`, `/api/polls` and `/api/requests?status=pending` are every one staff-gated; they would all 403 and be swallowed by the `.catch(() => null)`, which is five refusals a page for nothing. The member branch returns before any of them. |
| `page-requests.js:842` | `load(me)` branches once: member → `loadMember()` (File a request + Your requests, `/api/requests/mine`, Withdraw on the pending ones); otherwise `loadStaff()`. **There is no half-staff render** — the decide controls, the settings panel and the filter toolbar are not built at all rather than built and hidden. |
| ⚠️ **not verified** | A session that changes from staff to member **while a tab is open** keeps the staff render: `app.js:241`'s `verify()` re-paints the shell but not the page body. Pre-existing shape (the same is true of staff → not-staff, which at least shows the gate), not introduced here, and a reload fixes it. |

### `site/mock/server.mjs` — the fixture, and the bug it caught

> ⚠️ **GONE in the 2026-08-31 re-key:** `site/mock/server.mjs:GONE (was :2691)` — the construct each note names is no longer in the file; the note itself needs a decision.

| Key | Note |
|---|---|
| ⚠️ `server.mjs:658` | **`state.requests` was already taken by ROLE requests** (`server.mjs:483`, read at `:1488`), and a second `requests:` key in the same object literal silently won — duplicate keys in a JS object literal are not an error, the last one wins. `GET /api/rolemenus/requests` started answering **feature requests mapped through the role-menu row builder**, which is how `check.mjs` reported twelve rows "missing requested_at, deny_reason". Renamed to `featureRequests` / `featureComments` / `nextFeatureRequest` / `nextFeatureComment`, and the row builder to `featureRequestRow` (`:2342`) beside role menus' own `requestRow` (`:1243`). **The contract check found this; reading the diff did not.** |
| `server.mjs:GONE (was :2691)` | `requestOrder` is **waiting first with the longest wait at the top, then everything else newest first** — the top of the list is always the thing somebody is owed an answer on. It is one function used by the list route, `/mine` and the CSV, so the page, the member view and the export cannot disagree about order. |
| `server.mjs:72` | ⚠️ **`dayAhead` builds `YYYY-MM-DD` from the LOCAL clock, and `page-requests.js:124 dueOn` reads it back as LOCAL midnight.** `new Date('2026-09-10')` is UTC midnight, which prints as the **ninth** anywhere west of Greenwich — the page would name a different day from the one somebody typed, on the owner's own machine (Phoenix, UTC-7). This is why the due date does not go through `ui.js:untilWhen`. |
| `server.mjs:3238` | `POST /api/requests` is the **first route in the mock a non-staff session may call**. It checks `request_mode`, then `request_who_can_file`, then auto-approves when the filer is staff and `request_auto_approve_staff` is on — three separate refusals in words rather than one generic 403. |
| `server.mjs:3269` | `/status` refuses a move on a **pending** row ("Approve it first") and on a **declined or withdrawn** one, so the board's segment cannot silently resurrect a settled request. Priority, assignee and notes are settable on any row, which is what lets Approve and triage happen in either order. |
| `server.mjs:3041` | `withdraw` is the member's own: it checks the row is theirs AND still pending. Both refusals name which it was. |
| `check.mjs:34` | ⚠️ **`request_id` was already the ROLE request placeholder**, so a feature request needed its own: `feature_request_id` (25, pending, so Approve and Decline both have something to act on) and `member_request_id` (30, the member fixture's own, the only kind Withdraw takes). |
| `check.mjs:190` | `POST /api/requests` joins **UNGUARDED**: filing writes a row and DMs, and only the one line in `request_notify_channel_id` is a channel post, which the bot guards on its own. ⚠️ **This is an assertion about 13a's API, made by 13b — the reviewer should confirm it.** |

### `site/public/assets/page-requests.js` — the page

| Key | Note |
|---|---|
| ⚠️ `page-requests.js:17` | **The board is CARDS, not a table** — a deliberate deviation from the brief's "table with a status segment, priority select, assignee member-picker, notes inline". `memberPicker()` is a field plus a results list plus a notice, and the staff note is a textarea; neither fits a table cell, and seven columns at 390px is a scroller nobody can use. `phase13-design.md` §Dashboard allows "kanban-ish columns **or** one table", so this stays inside the design's own latitude. Every control the brief lists is present. |
| `page-requests.js:402` | ⚠️ **The board segment has FOUR steps, not three.** Approving a request makes it `approved`, and a three-step Planned → In progress → Done segment would render with **nothing pressed** on every freshly approved row, which reads as broken. Approved is the first step. |
| `page-requests.js:17` | Who is on it is **a line with a Change button**, not a picker per card. Thirteen open cards would otherwise be thirteen search boxes; Change swaps the line for `memberPicker()` and Save/Cancel put it back. |
| ⚠️ `page-requests.js:464` | **`replaceChildren` turns a `null` child into the WORD "null"** — `el()` filters them, `replaceChildren` does not, and the first browser pass had a literal `null` beside every Change button. The list is built then `.filter(Boolean)`ed. |
| `page-requests.js:217` | The two-line clamp's Read-the-rest button is **measured, three times**: on render, again on `document.fonts.ready`, on every `toggle` (capture — `toggle` does not bubble) and debounced on resize. ⚠️ **The first reading is a lie in two ways**: the self-hosted face has not loaded, so the fallback fits in two lines where Rajdhani needs three (measured: 6 whys clamp at 390, and the first pass showed **0** buttons); and a why inside a shut foldout has `clientHeight` 0, so it never overflows. |
| `page-requests.js:287` | The notes drawer **fetches on first open**, not on load — thirty requests would otherwise be thirty extra calls per load for a thread almost nobody opens. A failed fetch resets `filled` so the next open retries. |
| ⚠️ `page-requests.js:362` | **`emptySaid` distinguishes an empty list from a page past the end of one.** Found by measuring: after a pager test left `state.board` at 2 and the fixture was reset to 14 rows, the board said "Nothing is approved and unfinished" while its own count said 14. That is a lie about the list rather than about the page. Real readers hit it whenever somebody else decides the last request while they are on page three. |
| `page-requests.js:711` | The filter box and the three assignee chips are **server-side** (`q`, `assignee`; `On me` resolves to the signed-in id), and both reset `pending` and `board` to page 1. `keepTyping` (`:734`, Members' own trick) puts the caret back after the rebuild. |
| `page-requests.js:609` | The outcome sentence under File a request says whether **this person's** request skips the queue — `request_auto_approve_staff` AND `me.staff`, not one or the other. Measured through all four states (no what / no why / no due / due). |
| `page-requests.js:699` | ⚠️ **Why sits in its own one-field `.formrow`.** A bare `.field` lays its label out BESIDE the control; inside a formrow the label sits above it. The member view showed both shapes on one form until this was fixed. |
| `site.css:1531` | ⚠️ **`ui.js` has drawn `foldout()` since Polls 10b and `site.css` had NO rule for it** — `grep -c foldout site.css` was **0**. The browser's own disclosure triangle sat beside the chevron the helper draws and the count badge had no gap. Now styled once, for Requests' 33 foldouts and Polls' Archive. |
| `site.css:1571` | `.badge[data-tone="info"]` is new: approved / planned / in progress are **states, not warnings**, and `--et-info` is the theme's own token for that. The badge had rules for ok / warn / danger only. |
| `shell.js:14` | The rail's Requests count is `featurerequests`, **not** `requests` — `requests` is the ROLE request badge beside Role menus. Same collision as the mock's state and the check's placeholder, in a third place. |

### Measured, not asserted

Chrome, same-origin iframes so the media queries evaluate at the real width.

| | 1280 | 390 |
|---|---|---|
| `scrollWidth − innerWidth` | **0** | **0** |
| side-by-side field groups | **57**, every one spread **0.00px** | all 57 stacked one control per line — no group left to compare (the same caveat 9b and 11b recorded) |
| whys that overflow two lines | 0 | **6**, and **6** Read-the-rest buttons shown; clicking one sets `data-open="true"`, relabels to Show less and clears the overflow |
| console messages | **none at all** | — |

Every write and filter was exercised against the mock: Approve (#25), Decline
with the reason dialog (#26), the four-step status segment, priority, the
assignee picker (search → pick → Save → Take them off), the staff note (Save
disabled until the text differs, re-disabled after), the notes drawer (lazy
load, add, count 1 → 2, box cleared), the search box (`birthday` → 1 waiting /
0 on the board, caret kept), all three assignee chips, the board pager over 36
seeded rows, File a request as staff (auto-approved) and as a member, Withdraw
as a member, the `?as=member` redirect from `/index.html`, the `?as=stranger`
gate, and `GET /api/requests/export.csv` (**200, `text/csv`, 6592 bytes**).

A regression sweep at 1280 over `polls`, `index`, `chat`, `rolemenus`,
`settings`, `members` and `audit`: every page fills, none overflows. Polls'
one 97.08px "misaligned" group is its five-field Channel/Ping/Voters/Results/
Thread row **wrapping** onto two lines, which is pre-existing and not a
misalignment.

### What was NOT verified

> ⚠️ **GONE in the 2026-08-31 re-key:** `site/public/assets/ui.js:GONE (was :522)` — the construct each note names is no longer in the file; the note itself needs a decision.

- ⚠️ **Nothing ran against the real API, because it does not exist yet.** Every
  assertion is against `site/mock/server.mjs`. The eight failing contract cases
  are the honest record of that.
- ⚠️ **`tests/api/test_contract.py` has no `feature_request_id` /
  `member_request_id` in its `seeded` fixture** — it was read-only for this half.
  13a or the reviewer must add them (the mock uses `'25'` and `'30'`) or the
  eight cases fail on a missing placeholder even once the routes exist.
- ⚠️ **`ui.js:pager` does not scroll back to the list — it lands at the top of
  the PAGE.** Measured: scroller at 3000 → **0** at the moment `#dash` is
  replaced (a `MutationObserver` on `#dash` read 0), so `ui.js:GONE (was :522)`'s
  `if (scroller.scrollTop <= wanted + 1) return` always short-circuits. This is
  the shared helper and it affects **polls, chat, members and requests alike**;
  `ui.js` was left alone because 12b was in it. The reader is never stranded
  mid-list, so it is not harmful — but 11b's recorded "25923 → 276.67" does not
  reproduce here.
- ⚠️ **The dashboard renders `**bold**` literally.** The mock's new messages
  follow the house style every other feature uses ("Filed as `**#31**`"), and
  the page shows the asterisks. Pre-existing across Polls, Role menus and Chat;
  worth one shared fix in `ui.js:run`, not five.
- **`priority N` shows in the member's own meta line.** It is their request and
  the API sends it, but a bare triage number with no legend may read as a slight.
  An owner call, not a bug.
- **The requester chip links to `/members.html` with no filter**, because the
  Members page reads no URL parameter. A link that promised a filter and did not
  deliver one would be worse; the member's name and id are in the `title`.
- **Browser checks were Chrome only**, in Cyberpunk dark, Cyberpunk light and
  Discord dark. The other nine theme×mode combinations were not looked at; the
  new CSS is token-only, but that is inference.
- **Contrast of the new pieces was not measured.** `.req-due`, `.req-reason`,
  `.req-note` and `.badge[data-tone="info"]` reuse `--et-muted` / `--et-danger` /
  `--et-hairline` / `--et-info`; no sampler was run.
- **No Discord, no deploy, and no owner sweep** from the design's definition of
  done.
| `black_bloc/api/tools/requests.py:360` | ⚠️ **`GET /api/requests/mine` and `GET /api/requests/export.csv` are declared BEFORE `GET /api/requests/{request_id}`.** `request_id` is typed `int`, so FastAPI would answer `mine` with a 422 validation error rather than the list — a bare status with no sentence, which is exactly what the front-door rule forbids. Route order is the whole fix and it is load-bearing; the mock's own `match()` scans in registration order for the same reason. |
| `black_bloc/api/tools/requests.py:436` | ⚠️ **`POST …/status` writes the fields FIRST and moves the state LAST.** A bad `assignee_id` sent alongside `status: done` must not leave the row done and unassigned. `set_fields` is a single `UPDATE`, `wanted_assignee` raises before it, and `apply_decision` runs only once everything else has landed. Pinned by *the status route moves the state last so a bad field stops it*. |
| `black_bloc/api/tools/requests.py:116` | `requester` and `assignee` are objects (`{id, name, avatar}`) rather than a flat `assignee_id` / `assignee_name` pair, because the page draws an avatar beside each and a null assignee has to be one absent thing, not two. `decided_by` stays flat, matching the audit rows. |
| `black_bloc/api/tools/requests.py:277` | `pending` rides along on the list response — the sidebar badge, counted over the guild rather than the page, so paging to page 3 does not make the badge say 0. |
| `black_bloc/api/tools/requests.py:217` | `wanted_filter` reads `assignee=none` as the board's **Unassigned** column and turns it into `assignee_id IS NULL`; anything else is an id. It is a separate function from `wanted_assignee` because a FILTER and a WRITE want opposite things from an empty value — the filter wants every row, the write wants the field cleared. |
| `black_bloc/api/tools/requests.py:398` | ⚠️ **`q` also matches the requester's NAME, and a name is not in SQL.** Names live in the gateway's member cache, so `members_matching` resolves the query to ids in Python and `_where` ORs `user_id IN (…)` onto the three `LIKE` clauses. Capped at `NAME_MATCH_LIMIT` = 200 ids so a one-letter query cannot build an unbounded `IN` list. |
| `black_bloc/api/tools/requests.py:214` | `wanted_assignee` takes `...` for absent and `None`/`""` for cleared, so `{"assignee_id": ""}` unassigns and a payload that never mentions it leaves it alone. Both were needed: the page's picker sends the empty string to clear. |
| `black_bloc/api/tools/requests.py:319` | ⚠️ **`POST /api/requests` is NOT guard-refused under `TEST_MODE`, and that is deliberate** — it is a database write, and the only thing this feature sends to a channel is the optional notice line, which asks the guard itself. Refusing the route would mean nobody could file from the site while the bot is in test mode, for no safety gain. The COG's modal reply *is* guard-checked, because that one really is a message. Pinned by *filing from the site is not guard refused while test mode is on*. |
| `black_bloc/api/tools/requests.py:319` | A web decision leaves **two** action rows — `request.<status>` from `apply_decision` and `web.request.<status>` from `note` — which is what `api/tools/rolemenus.py:365` already does. The audit tab filters on `web.`, so the second is what makes a site decision distinguishable from a slash-command one. |

### The contract, and what is not in it

| Key | Note |
|---|---|
| `site/mock/contract.json` | The paths use `{feature_request_id}` — the signed-in staff session's own **pending** row — with `{member_request_id}` beside it for somebody else's, already planned. Both halves seed the pair (`tests/api/test_contract.py`'s `seeded`, the mock's `seedState` as **25** and **30**, `check.mjs`'s `IDS`), which is what makes `/api/requests/mine` non-empty and the approve/decline routes reachable in the same fixture. |
| `site/mock/server.mjs` | ⚠️ **The mock's helpers are `ask*`, not `request*`, and its state key is `state.asks`.** `requestRow` and `state.requests` were already taken by the ROLE-request feature, and the first cut of this file silently shadowed both — the symptom was three unrelated rolemenus contract rows failing, not a syntax error. |
| `site/mock/contract.json` | `GET /api/requests/export.csv` is deliberately absent: `check.mjs` reads JSON shapes and this answers CSV, exactly as the polls and logs exports already are. `POST /api/requests/{id}/withdraw` is absent too — it only ever answers 200 for the person who filed the row, which one fixture session cannot exercise both ways. |

## integration night 2026-08-27 — 13b merged, request kinds, defects, cyberpunk restored, via

> The integration pass on branch `worktree-agent-acd3594b9dbefbec2`, cut from `main`
> @ `16c5781`. Five commits: `641e53b` (13b merged, mocks reconciled) → `196e7a9`
> (request kinds, `request_log_level`, `/request logs`) → `a4e7fcd` (the three
> defects) → `f10260d` (cyberpunk restored) → the `via` commit. Line numbers are as
> of the last of them.
>
> **Last verified: 2026-08-27** — `pytest -q` **2158 passed** (2144 + 14 new; three
> known failures on `main` fixed). `ruff check .` clean. `node site/mock/check.mjs`
> clean at **17 pages / 89 routes**. Browser pass on the mock at port 8912, Chrome,
> Cyberpunk dark / Cyberpunk light / Discord dark, 1280 and 390 CSS px in
> same-origin iframes.
> ⚠️ **NOTHING has run against live Discord.** No gateway session, no `/request`, no
> `/settings logs`, no line watched to arrive or be suppressed. Every claim below is
> against fakes, a temporary SQLite file, or `site/mock/server.mjs`.

### The merge — which side won where

`git merge --no-ff worktree-agent-acd6d4a9712a56eb0` conflicted in five files, 31
hunks. **The real router is the truth**, so `black_bloc/api/tools/requests.py` and
`black_bloc/api/auth.py` decided every shape.

| File | Hunks | How it was resolved |
|---|---|---|
| `site/mock/contract.json` | 16 | **13a's table verbatim** — the resolved file is byte-identical to `main`'s, plus 13b's `/requests.html` page entry, which 13a had not added. 13b's shapes were wrong against the router in five ways: `shown`/`notes` instead of `pages`/`pending`, no `status_word`, `decided_by` as an object rather than a flat id beside `decided_by_name`, a FLAT `GET /api/requests/{id}` instead of `{request, comments}`, and no `request_id` on a comment row. Its `web.request.status` / `web.request.commented` kinds are not what the router emits either (`updated` / `comment`). |
| `site/mock/server.mjs` | 12 | **Split.** 13a's row builders, refusal sentences, statuses, page size and ORDER (`asksSorted` = pending first then id DESC, which is the router's `ORDER BY (status <> 'pending'), id DESC`) all won; 13b's `requestOrder` (pending oldest-first) did not. 13b's **thirty-row fixture** won over 13a's two hand-written rows, moved under 13a's `asks`/`askComments` keys. 13b's **member gating** won on all three non-staff routes. |
| `site/mock/check.mjs` | 1 | A comment only; both halves already agreed on `feature_request_id: '25'` and `member_request_id: '30'`. 13b's UNGUARDED entry and its six `web.request.*` calls merged cleanly and were kept. |
| `site/public/assets/app.js` | 1 | Both: 12b's `audit` → **Logs** label AND 13b's `requests` tab. |
| `site/public/assets/shell.js` | 1 | Both, same way. |

| Key | Note |
|---|---|
| ⚠️ `server.mjs:815` (`meBody`) | **13b invented `state: 'member'`, which the router never returns.** `api/auth.py:516` only ever sends `staff` / `not_staff` / `staff_unknown`, and a guild member who is not staff is `state: "not_staff"` with `member: true` and the `MEMBER_NOT_STAFF` sentence. The mock now says that. Nothing on the page reads `state` for this — `shell.js:272 isMemberOnly` reads `staff !== true && member === true` — so the page was right and only the fixture was lying. A **stranger** keeps `member: false` and keeps the gate, which is what `app.js:173 refuseFor` needs to tell the two apart. |
| ⚠️ `server.mjs` `asks` / `askComments` | **`state.requests` is the ROLE-request list** (`server.mjs:406`, read by `GET /api/rolemenus/requests`), and 13b's first cut shadowed it with a duplicate key — the symptom was twelve unrelated rolemenus contract rows failing. 13a's `ask*` names avoid it in the same way 13b's `featureRequests` did; `ask*` won because the route bodies that survived are 13a's. `check.mjs`'s `request_id` is still the ROLE placeholder and `feature_request_id` is the new one. |
| `server.mjs` seed row 25 | Changed from `MEMBERS[3]` to `MEMBERS[0]` so `{feature_request_id}` is the **staff session's own pending row**, which is what `contract.json` says it is and what makes `GET /api/requests/mine` non-empty for the staff fixture. 30 stays the member session's own pending row — the only kind Withdraw takes. |
| ⚠️ `server.mjs` `POST /api/requests` | 13a's mock never checked `request_who_can_file`; the router does (`api/tools/requests.py:213 _may_file`). Added, with the router's own `STAFF_ONLY_FILES` sentence, so a member meets the same three refusals in the same order on both halves. |
| `page-requests.js:500 pagerFor` | Sent `per_page` the router does not take and derived `hasMore` from a page size of its own. It now reads `payload.per_page` and `payload.pages`, which the router sends (`API_PAGE` is **20**, not the page's 25). |
| **not reconciled, deliberately** | The mock's `/status` route lets a **pending** row move straight to `planned`, because `apply_decision` (`cogs/community/requests.py:161`) does; 13b's mock refused it with "Approve it first". The page tolerates both and the router is the truth. |

### Phase 12 meets Phase 13 — the thirteenth feature

| Key | Note |
|---|---|
| `black_bloc/logkinds.py:25` | `request` joins `FEATURES`, so `settings_store.py:438` generates `request_log_level` with the other twelve and `logkinds.LOG_LEVEL_KEYS` is thirteen long. `HEADS` takes **both** `request` and `requests` as heads, because `feature_of` splits on the first dot and nothing stops a later kind being written either way. |
| `black_bloc/logkinds.py:110` | ⚠️ **IMPORTANT gets only `request.declined` and `request.done`.** `request.approved` arrives free on the `.approved` suffix and `request.dm_failed` / `request.notify_failed` on `_failed`; listing them as well would fail nothing but would be a second home for the same decision. |
| `black_bloc/logkinds.py:233` | ROUTINE gets `filed`, `auto_approved`, `withdrawn`, `planned`, `in_progress`, `updated`, `comment` — the owner's line is that a DECISION is loud and the rest of a request's life is not. `bare()` means every `web.request.*` twin classifies with its bare kind, so nine kinds are covered by seven entries. |
| `tests/test_logkinds.py:39` | Two additions: the `f'request.{status}'` call site in the cog, enumerated to its five statuses, and the nine `web.request.*` kinds under `black_bloc/api/writes.py::kind` — those reach `log_action` through `note()`, so the scanner sees the variable, not the string. |
| `black_bloc/cogs/community/requests.py:448` | `/request logs` is the thirteenth, and it is the whole body of `send_logs` like the other twelve — which is why `settings_store.is_staff_command` finds `require_staff` in its `co_names` and hides it from non-staff with no `extras`. |
| `tests/test_bot.py:96` | The tree is **35** top-level commands (34 before), still far under Discord's 100; `/voice` is still the fullest group at 18. |

### The three defects

| Key | Note |
|---|---|
| ⚠️ `site/public/assets/ui.js:527 backToTop` | **The pager landed at the top of the PAGE.** `#dash`'s `replaceChildren` resets the scroller to 0 before the helper runs, so the old `if (scroller.scrollTop <= wanted + 1) return` always short-circuited. Now: unconditional, and after the new rows are in the document. It places the scroller twice — once the instant `onPage` resolves, once after `painted()` — because `painted()` races two `requestAnimationFrame`s against a **60 ms timer**, and ⚠️ **rAF does not run at all in a tab that is not on screen**, which the first cut of this fix proved by never firing under browser automation. Instant, never smooth, for the same reason. |
| `ui.js:507 listTop` | Keeps the block as well as the offset. When the block survives the rebuild (`logs.js` replaces only its `results`) the landing is re-measured from the live node; when `#dash` was replaced the recorded offset is used, and it is still right because everything ABOVE the list is rebuilt identically. |
| ⚠️ `ui.js:313 boldParts` | **`**x**` rendered its asterisks in every outcome sentence.** One shared fix in `notice()`'s `say`, which is what `run()` writes into: the message is split on `**…**` into text nodes and `el('strong', { text })`. **No innerHTML** — the sentence carries names and reasons people typed. `node.said` keeps the raw text so `keepSaying` parks the markers rather than the flattened text and a sentence that survives a reload keeps its emphasis. |
| `page-requests.js:836` | `await logsSection('request')` at the foot of the STAFF view only — a member cannot read `/api/actions`, and asking would be one 403 swallowed for nothing. `request_log_level` joins the page's `SETTING_KEYS`, `request` joins `logs.js:18 LOG_FEATURES` (so the Logs page gets its chip) and `logs.js:46 ROUTINE` gets its sentence. |

**Measured, the pager, in a 1276×796 iframe on the mock** — `.content.scrollTop`
before Next / after, then where the list block's top sits under the top bar, beside
what the same click did before the fix:

| page | before | after | list top | list top, unfixed |
|---|---|---|---|---|
| Requests · Planned & in progress (33 rows) | 9340 | **930** | **8.18px** | 938.18px |
| Members (60 rows) | 2439 | **122** (the page's own maximum) | **48.21px** | 170.21px |
| Polls · Closed (17 rows) | 663 | 663 (already the maximum) | **296.11px** | 959.45px |

⚠️ **Members and Polls both land on a page whose scroller cannot reach the wanted
offset**, because page 2 is shorter than page 1; `scrollTop` clamps and the list ends
up as near the top as the page allows. That is the right answer and it is why the
raw before/after numbers alone do not tell the story — the list-top column does.

### Cyberpunk

See the `f10260d` commit message for the palette and the contrast table.
⚠️ **The two light-mode figures below 4.5:1 — accent 4.46 on the page ground, heading
3.54 — are the estate's own values.** The neon set beat both; the owner asked for the
estate's palette by name, so they are recorded rather than quietly improved. Dark is
the default this site boots into and clears everything.

### Via — where a change was made

Owner, 2026-08-27 18:51: *"in the logs we should add how someone has set a setting,
if they set it in discord or on the website"*.

| Key | Note |
|---|---|
| `black_bloc/logkinds.py:335 via_of` | Two words, `discord` and `website`. **What the writer recorded wins**; otherwise the kind's `web.` head decides. That second half is what makes every row written before tonight say something rather than nothing. |
| ⚠️ `black_bloc/actionlog.py:97 stamped` | **`log_action` stamps `details["via"]` itself, so no writer can forget it.** There are thirty-odd `store.set` callers across the cogs and editing every one would have been thirty chances to miss one — the same reasoning that made every `.would_` kind routine by RULE. The two settings doors (`cogs/core.py`'s four calls, `api/settings_api.py`'s two) ALSO pass it explicitly, so a kind rename cannot silently relabel the one thing the owner asked about. |
| ⚠️ **the residual, accepted** | A website path that logs a **bare** feature kind — `api/tools/requests.py` calling `apply_decision`, which logs `request.approved` — is stamped `discord` by the rule, and its `web.request.approved` twin beside it says `website`. It is not wrong about the ACTION (a slash command logs the same bare kind) and the pair is the provenance, but a reader scanning the Via column sees one Discord row for a website decision. Passing `via` down through `apply_decision` and its siblings is the fix and is not in scope tonight. **Settings, the owner's actual ask, have no such pair:** a settings change is `settings.set`/`settings.clear` (Discord) or `web.settings.set`/`web.settings.clear` (website) and never both. |
| `black_bloc/actionlog.py:35` | `SUMMARY_SKIPS` keeps `via` out of the flattened `key=value` summary — it is its own column and its own part of the line, so it must not appear twice. The mock mirrors the same list (`server.mjs:938`). |
| `black_bloc/actionlog.py:245` | The `/… logs` line ends `· via Discord`, **outside the 100-character cap**, the way the stamp sits outside it: a truncated line must still say where the action came from. |
| ⚠️ `black_bloc/api/settings_api.py:152 via_by_key` | **The `settings` table has no column for this**, so the Settings audit reads it back off the action log: the newest `settings.*` / `web.settings.*` row whose `details.key` matches, over a 2000-row scan. A key nothing logged answers `null`, which the page draws as `—` rather than guessing Discord. ⚠️ **A cleared key leaves the settings table entirely**, so a clear never appears in the audit at all; the Logs page is where a clear is read. |
| `site/public/assets/logs.js:52 viaCell` | A `.pill.viapill`. Discord is the quiet base pill, the website takes the accent tint — the same grammar `.kindpill[data-important]` already uses, so no new colour was invented. Drawn in `logsTable` (every Logs section and the Logs page) and in `page-audit.js:72`'s Settings audit table. |
| `black_bloc/api/status.py:230` | `via` is on every `/api/actions` row and in the CSV, between `reason` and `details`. |

### What was NOT verified

- ⚠️ **No live Discord, at all.** No `/request`, no `/request logs`, no `/settings logs`,
  no line watched to arrive or be suppressed, no command sync. The 35-command tree has
  never been sent to Discord.
- ⚠️ **The pager fix has never been exercised in a FOREGROUND tab.** Every measurement
  above was taken with the automated tab backgrounded, which is the case the 60 ms
  backstop exists for — the rAF path itself is therefore the half that was NOT observed
  firing. It is the cheaper path, not the load-bearing one.
- **Cyberpunk light's two sub-4.5 contrast figures are computed, not sampled** — the
  numbers are WCAG arithmetic over the token values, not a pixel sampler on a rendered
  page.
- **Chrome only**, Cyberpunk dark, Cyberpunk light and Discord dark, 1280 and 390. The
  other nine theme×mode combinations were not opened; the new CSS is token-only, but
  that is inference.
- **No `.pill.viapill` contrast sample** was taken; it reuses `--et-accent` at the same
  mix as `.pill.kindpill[data-important]`.
- **Nothing was deployed**, and no owner sweep from either phase's definition of done
  has been run.

## Site feature audit B4–B8 — the last five dashboard controls (2026-08-31)

> Built on branch `worktree-agent-aab8d0b3a81f1039b` off `7b7840b`, one commit per item:
> **B4** `4f0f399` · **B5** `47628b7` · **B6** `2c65db0` · **B7** `d8f44c7` · **B8** `379b0c1`.
> **Last verified: 2026-08-31** — `pytest -q` **2227 passed** (2162 before B4),
> `ruff check black_bloc tests site` clean, `node site/mock/check.mjs` clean at **98 routes**
> (89 before). ⚠️ **Nothing here has run against live Discord**: every channel edit, role
> change and event edit is exercised against the repo's fakes and the mock only, and no page
> has been opened in a browser — the JS is parse-checked and contract-checked, not rendered.
>
> ⚠️ **`ruff check .` reports 2 pre-existing errors** in `scripts/doctools/move_done.py`
> (a long docstring and a variable named `l`). That folder is untracked tooling and predates
> this work; `ruff check black_bloc tests site` is the gate these commits pass.

### B4 — temp voice per-room actions

| Key | Note |
|---|---|
| ⚠️ `black_bloc/cogs/community/tempvoice.py:786 Doer` | **The refactor that made B4 possible, and it is deliberately duck-typed.** `do_rename`/`do_limit`/`do_privacy` only ever wanted three things off the interaction — `.client`, `.guild`, `.user` — so `Doer` is a NamedTuple with exactly those names plus `via`. A `discord.Interaction` already satisfies it, so **every panel and `/voice` call site is unchanged** and there is still one implementation of each action rather than an API near-duplicate (checklist 15). The alternative, threading `(bot, guild, actor)` through as three arguments, would have rewritten thirteen call sites for the same result. |
| `black_bloc/cogs/community/tempvoice.py:777 Said` | A `str` subclass carrying `ok`. The helpers answer with a **sentence** and the panel just prints it, but the API has to know whether to answer 200 or refuse — and `str` compatibility is what kept `_act`, both modals, the panel toggle and the existing tests working with no edit at all. Only the three helpers B4 routes return `Said`; the other nine still return plain `str` because nothing outside the panel reads their outcome. |
| ⚠️ `black_bloc/cogs/community/tempvoice.py:844 panel_log` | The kind grows a `web.` head and `details["via"]` **from the doer**, so a rename made on the dashboard logs `web.tempvoice.rename` and a rename made on the panel logs `tempvoice.rename`. No new entry in `logkinds.py` was needed: `bare()` strips the head, so both collapse onto the `tempvoice.rename` already in `ROUTINE`, and `rename_failed` is important by suffix. |
| ⚠️ `black_bloc/api/tools/tempvoice.py:86 room` | **The place gate, and it is the whole test-mode story for these four routes.** A channel edit is a side effect `guard.py` cannot see, so the route asks the cog's own `may_act_in` — the room has to sit in the test channel's category. A room spawned from a lobby the guard placed is in that category, so a staffer can still drive the feature in test mode; a room anywhere else is a 409 in words. That is why these four are in `check.mjs`'s **UNGUARDED** list rather than GUARDED: they are place-gated, not blanket-refused. |
| `black_bloc/api/tools/tempvoice.py:98 answered` | One shape for all four: `{room, message}`, where `room` is the row re-read after the write so the page repaints from what Discord now says rather than from what it asked for. `Said.ok` false becomes `409 discord_refused` carrying the cog's own sentence (the Manage Channels one, or the rename rate-limit one). |
| `black_bloc/cogs/community/tempvoice.py:1085 privacy_of` | Locked and hidden read off the `@everyone` overwrite, in **one** place: `/voice info` and the dashboard's Access column were otherwise going to spell the same rule twice (checklist 15). |
| **skipped, and why** | **Region and Kick are not routed.** Region is cheap on the API side but needs a 25-entry picker per row on a table that already grew four buttons, and Kick needs a member picker per room plus `connected_ids`. Neither is blocked by the refactor — `do_region` and `do_kick` take the same `Doer` — so both are a small follow-up rather than a design problem. |

⚠️ **Two test TABLES move when a `log_action` kind stops being a plain literal**, and both
fail by name rather than silently: `tests/test_logkinds.py:KNOWN_DYNAMIC` is keyed on the
`ast.unparse` of the kind expression, so `f'tempvoice.{kind}'` became
`f'{head}tempvoice.{kind}'` and the key had to move with it; and a `{placeholder}` added to
`site/mock/contract.json` needs the SAME name in `tests/api/test_contract.py`'s ids dict,
because `check.mjs` and the pytest side fill it from two different tables.

### B5 — un-post a role menu panel

| Key | Note |
|---|---|
| ⚠️ `black_bloc/rolemenu_panels.py:61 unpost` | **The route calls this, not `clear_message`.** `clear_message` only forgets the message id; `unpost` deletes the message in Discord, asks the guard first, clears the row and logs — the whole operation the mode switch already used. Calling the storage helper straight would have left the panel up in Discord and the row saying it was down. |
| ⚠️ `black_bloc/api/tools/rolemenus.py:509 rolemenu_unpost` | **The guard is asked twice, on purpose.** `unpost` asks it first so a refused take-down is logged as `web.role_menu.would_unpost` exactly as the slash twin logs `role_menu.would_unpost` (checklist 1 and 2); the route then asks the same question to tell the two `False` answers apart — the guard's own sentence with `409 test_mode`, or `409 panel_stuck` when Discord refused. Without the second ask, both would come back as "Black Bloc could not take it down", which is true of the wrong thing. |
| `black_bloc/rolemenu_panels.py:40 note` | Grew a `via`, so the web's un-post leaves ONE line under a `web.` head rather than a bare line plus a mirror. `bare()` collapses it onto `role_menu.unposted`, which is already in `ROUTINE`, so nothing new needed classifying. **`move_panel` passes it too**, which fixes the same residual on the existing channel-change path. |
| `black_bloc/cogs/community/role_menus.py:1958 unpost` | The slash twin, added because checklist 33 says a per-item action needs both doors — `/rolemenu mode off` took every panel down and there was no way to take ONE down from Discord. It imports `rolemenu_panels` **inside the function**: that module imports this one at the top, so a module-level import is a cycle. |

### B6 — seed the default menus

| Key | Note |
|---|---|
| `black_bloc/cogs/community/role_menus.py:620 seed_summary` | Lifted out of the slash command so the button and `/rolemenu seed-defaults` say the **same** sentence — including the emoji caveat, which is the part people act on. `seed_default_menus` was already idempotent (`create_menu` returns `None` on a name that exists), so the route needed no new safety, only a way to report it. |
| ⚠️ `black_bloc/api/tools/rolemenus.py:322 rolemenu_seed` | Answers `created` and `skipped` as **lists**, not a count, because "already there, left alone" is the half that needs naming — a staffer who sees `event-alerts` skipped is being told why its Marathons emoji is missing, and the message spells the fix. The route is declared **before** `/{name}/…`, and `POST /seed` cannot collide with anything in any case: there is no `POST /{name}`. |
| `black_bloc/cogs/community/role_menus.py:2124` | Seeding now leaves a `role_menu.seeded` line from BOTH doors; the slash command left none at all before, so a seeded server had no record of when its menus appeared. |
| **not verified** | No seed has ever run against the live guild. The six menus' role ids in `SEED` are the real server's; nothing here checked that any of them still exists, and a role that is gone simply becomes an option Discord will refuse at pick time — the same as before this change. |

### B7 — staff assign from the dashboard

| Key | Note |
|---|---|
| ⚠️ `black_bloc/cogs/community/role_menus.py:1288 staff_assign` | **Lifted whole out of `StaffAssignSelect.callback`, which was the only implementation of "hand a menu's roles out".** The select now does the guard/guild/mode checks and then calls it; the route does its own checks and calls the same function. It returns `(done, sentence)` — the shape `make_creator_channel` already set in this repo — because the caller has to choose between an ephemeral reply and an HTTP status. ⚠️ **The extraction also fixed the ORDER:** the select used to answer the clicker BEFORE writing the `role_grants` rows and the action line, so a failed reply took the record of a real role change with it (checklist 12). Everything durable now happens before the sentence is handed back. |
| ⚠️ `black_bloc/cogs/community/role_menus.py:1301 role_diff` | Untouched, and it is what makes this safe: **only roles the menu owns are ever added or removed**, so a staffer handing out `runner-status` cannot strip somebody's Admin. The route passes whatever ids the page sent and they are intersected with the menu's options — an id that is not on the menu is dropped, not refused, exactly as a select value would be. |
| ⚠️ `black_bloc/api/tools/rolemenus.py:452 rolemenu_assign` | **There is deliberately NO test-mode refusal here, and it is in `check.mjs`'s UNGUARDED list.** A member's roles are not a channel, so `guard.py` cannot see the change; the slash twin only checks the guard on *where the click happened*, which means `/rolemenu assign` in the test channel changes real roles today. `POST /api/roles/grants` (Phase 9a) already works the same way. Refusing here would have been a rule the bot has not got. |
| `black_bloc/api/tools/rolemenus.py:282` | The route keeps the slash twin's other two gates — `rolemenu_mode` off is a `409 rolemenu_off`, an empty menu a `400` — so the two doors refuse the same things for the same reasons. |
| `tests/test_logkinds.py KNOWN_DYNAMIC` | `role_menu.assign`/`unassign` stopped being literals when the head became `web.` for the website, so they moved from the literal scan into the table under `role_menus.py::kind`, with all four values named. |
| **deviation from the spec** | The form offers **every menu that has a role on it**, not only `staff`-mode ones, because `/rolemenu assign` has never been restricted to staff-mode menus either — restricting one door and not the other is the drift checklist 15 exists to stop. Each option is labelled `name — mode` so a staff menu is obvious. |

### B8 — event detail and editing

| Key | Note |
|---|---|
| ⚠️ `black_bloc/cogs/community/events.py:245 checked_fields` | **The modal's whole validation chain, lifted out and made callable.** Title, the `YYYY-MM-DD HH:MM` parse, the **DST gap and ambiguity** checks, "that has already gone by" and the `1h30m` duration parse, in that order, returning `(fields, why)`. `submit` now calls it and so does the PUT, so a dashboard edit cannot make an event `/event propose` would have refused — and the refusal sentence is the identical one. |
| ⚠️ `black_bloc/api/tools/events.py:200 event_edit` | **The zone is the caller's, and it is named on the wire.** The body carries `start` as a bare `YYYY-MM-DD HH:MM` plus a `tz`; the page sends the browser's own IANA zone (`Intl.DateTimeFormat().resolvedOptions().timeZone`) and shows it above the field, and an unknown zone falls back to the staffer's stored `/timezone set` one. A bare local time with no zone is the bug this avoids — the cog reads it in the *requester's* zone, which is not who is typing. |
| `black_bloc/api/tools/events.py:194` | Only `pending` and `approved` may be edited (`EDITABLE`); a denied, cancelled, live or done event answers `409 not_editable` naming its state. Nothing here calls `can_transition`, because an edit is not a transition — the status does not move. |
| ⚠️ `black_bloc/api/tools/events.py:238` | **What an edit does NOT do is in the answer, not left to be discovered.** `rename_channel` (the cog's own helper, guard-aware, `would_rename` in test mode) follows the title, so the review channel keeps up. An announcement already posted and a Discord scheduled event already made **keep the old details**, and `notes` says so in words for whichever applies — there is no existing helper that rewrites either, and claiming a change that did not happen is checklist 10. `announced` and `scheduled` are on every row so the page can warn before the save, not only after. |
| `black_bloc/api/tools/events.py:88` | `GET /api/events/{event_id}` exists so the page has a detail route to name, though the list already carried every field the card shows — the audit's finding was that the page *fetched* them and rendered none of them. |
| `site/public/assets/page-events.js:44 localStart` | The prefilled start is the stored instant **rendered in this browser's zone**, which is the same zone the save is read in — the two have to agree or an untouched Save would move the event. |

## KI-6 — revocable sessions (2026-08-31)

> Built in the worktree `agent-a21673af8bc44721c` off `33d1086`.
> **Last verified: 2026-08-31** — `pytest -q` **2244 passed** (2227 before),
> `ruff check black_bloc tests site` clean. ⚠️ **Nothing here has run against a browser
> or live Discord**: every sign-in, logout and stolen-cookie replay is exercised through
> the repo's fakes and `TestClient`, never against `discord.com` or a real cookie jar.
> ⚠️ **Deploying this signs everybody out once** — a cookie minted before this commit
> carries no `sid`, and a payload with no session id is an invalid session. People see
> the ordinary signed-out page and sign in again; there is no new copy for it.

| Key | Note |
|---|---|
| ⚠️ `black_bloc/api/sessions.py alive` | **The whole of KI-6 in one function: present, unexpired, unrevoked.** The cookie is still the stateless signed payload it always was; the only new fact is `sid`, and this is the one place that decides whether that id is still a session. A payload without a `sid` reaches here as `None` and is refused, which is why the deploy is a one-time sign-out rather than a migration. |
| ⚠️ `black_bloc/api/sessions.py database_of` | **A database that cannot be reached is NOT a sign-out.** If `bot.db` is missing or disconnected the check answers `True` and the request carries on with the signature and expiry it already had. The alternative — refusing — would turn a sqlite blip into "everybody is logged out", and buys nothing: every data route already refuses with `database_unavailable` through `writes.require_db`, so a dashboard on a dead database shows nothing either way. The cost is that revocation cannot be enforced while the database is down, which is the same window in which nothing else works. |
| ⚠️ `black_bloc/api/sessions.py SessionCache` | **One DB read per session per 30 s, and a logout is immediate anyway.** `end` writes `False` into the cache BEFORE it touches the row, so the very next request in this process is refused even if the UPDATE is slow — the TTL is about how long a verdict written by somebody else could linger, and there is only ever one process (one uvicorn worker on one Fly machine). Bounded at `CACHE_MAX_KEYS` and evicted oldest-first, the same shape `TokenBucket` uses. A verdict can only ever go true → false, so caching a `False` costs nothing. |
| `black_bloc/api/sessions.py is_past` | An expiry nobody can parse counts as **past**. A session whose dates are unreadable is not a session anybody should be riding on, and this is the same "unparseable timestamp is treated as ended" rule the loops already follow (checklist 5). |
| `black_bloc/api/sessions.py start` | Sign-in deletes rows whose `expires_at` has gone by before writing the new one, so the table is bounded by *live* sessions rather than by every sign-in ever. Sign-in is rare enough that the sweep costs nothing, and there is no loop to own it. |
| ⚠️ `black_bloc/api/auth.py current_session` | **Now `async`, and that is the only reason `writes.member_dependency` and the two dependencies here changed.** The session check is a DB read; making the function async was cheaper than keeping a sync façade that hides one. Every call site was already inside an async dependency or route. |
| `black_bloc/api/auth.py logout` | Takes the `Request` now: it reads the cookie it is about to clear, so it can revoke the row by id. A cookie that is expired or forged yields no payload and nothing is revoked — there is nothing live to revoke. |
| ⚠️ `black_bloc/api/server.py create_app` | `app.state.bot = bot` exists so the **test** sign-in fixture can find the database the app was built with. It is the FastAPI-idiomatic place for it and nothing in `black_bloc` reads it; the alternative was a per-file fixture in twenty test files naming the right database by hand, which is exactly the wiring that goes stale. |
| ⚠️ `tests/conftest.py record_session` | The fixture writes the `sessions` row with **plain `sqlite3` on the same file**, because `sign_in` is a sync fixture called from both sync and async tests and cannot await the real `sessions.start`. It is a real row in the real database, not a seeded cache, so the 270 existing sign-ins exercise the same lookup the site does. |
| **not verified** | No browser has held one of these cookies; no session has been revoked against the live site; the 30-second cache has only ever been exercised with a hand-set clock. |

## KI-9 — keyed anonymous poll votes (2026-08-31)

> Same worktree, the commit after KI-6. **Last verified: 2026-08-31** —
> `pytest -q` **2257 passed** (2244 after KI-6), `ruff check black_bloc tests site` clean.
> ⚠️ **Nothing here has run against live Discord**: every vote is a fake button press in
> the repo's harness, and no anonymous poll has ever been cast in the server.
> ⚠️ **`POLL_VOTE_SECRET` is optional and the deploy does not need it** — without it new
> polls keep the old hash and the bot logs one warning when the polls cog loads.

| Key | Note |
|---|---|
| ⚠️ `black_bloc/cogs/community/polls.py voter_key` | **The scheme is per POLL, not per deploy, and that is the whole migration.** A poll that is already open has `poll_votes` rows keyed with the old per-poll `sha256("<poll_id>:<user_id>")`; if the scheme changed underneath it, the same person would key to a different number and be able to vote a second time. So the row remembers what it was created with (`polls.vote_scheme`, additive, schema 18) and this function follows the row. New polls are `hmac` when `POLL_VOTE_SECRET` is set, `sha256` when it is not. The truncation is unchanged — top 63 bits of the digest, so `poll_votes.user_id` stays an INTEGER and nothing else moved. |
| ⚠️ `black_bloc/cogs/community/polls.py can_key` | **A keyed poll whose key has gone is REFUSED, never downgraded.** Falling back to the hash would key the same person to a new number and hand them a second vote — the exact failure the per-poll scheme exists to prevent. `can_key` asks the question and `voting_row` answers the presser with `VOTE_KEY_MISSING` before anything is written; the `ValueError` is the belt to that braces, so a call site added later fails loudly instead of quietly double-counting. |
| `black_bloc/cogs/community/polls.py scheme_of` | Tolerates a row with no `vote_scheme` **key at all** (a `sqlite3.Row` from before the column, or a plain dict in a test) and reads it as the old scheme. NULL and missing mean the same thing here: this poll predates the column. |
| ⚠️ `black_bloc/cogs/community/polls.py voting_row` | The single gate all three vote buttons already went through, which is why the missing-key refusal is one check rather than three. The log line names the poll id and **never the key or a preimage** — a preimage is a member id, which is the thing anonymity is protecting. |
| `black_bloc/cogs/community/polls.py cog_load` | The one startup warning, and only when the key is unset. It says what the fallback IS (the old hash, on new polls) rather than only that something is missing, because the behaviour is deliberate and safe — a deploy without the secret must not read as broken. |
| ⚠️ `black_bloc/config.py poll_vote_secret` | **A secret, so it is deliberately NOT a settings-registry key** — checklist 33 asks for both doors on every decision, but a registry key is readable on the Settings page and editable with `/settings set-value`, and a MAC key that the dashboard can show is not a MAC key. It follows `SESSION_SECRET`: env only, `fly secrets` in production, blank counts as unset. What IS configurable both ways is the thing people actually decide — a poll's `anonymous` flag — and that already has a slash path and a dashboard control. |
| **not verified** | No key has been set on the Fly machine; no poll has been created under `hmac` outside the tests; nothing has measured the old scheme against a real `poll_votes` table (the live one is empty). |
# R1 — the restyle shell (`docs/info/site-restyle-design.md` §4), 2026-08-31

Front-end only; no route, contract or Python change. `node site/mock/check.mjs`
stayed green (17 pages / 98 routes) at every commit.

⚠️ **Read this first: three of R1's six items were ALREADY BUILT** by the
Direction A restyle of 2026-08-27 (`666dd8e`), and the brief — written against
`1eb8870` — does not know it. The top bar (server name, health dot, user chip,
theme cog holding the same five/six themes) exists identically on all 17 pages;
the rail was already grouped into four groups; the docked-dirty-bar pattern and
`humanLabel` already existed. R1 built what was missing and fixed what the
existing pattern got wrong.

### `site/public/assets/icons.js` — the one sprite

| Key | Note |
|---|---|
| `icons.js ICONS` | **Every glyph the site draws, in one object.** Lifted out of `ui.js` unchanged (the four it already had) and extended with one `nav*` glyph per rail item plus `backspace`. `ui.js icon()` is still the only reader, so no other file's imports moved. |
| `site.css .nav-icon` | Sized in **`em`, painted with `currentColor` through `--bb-nav-icon`**, so a theme dresses the rail without the sprite naming a colour. `icon()` writes `width`/`height` attributes in px; the CSS rule overrides both. The active row's glyph takes `--bb-nav-icon-active` (the theme's accent). Measured across all six themes x light+dark: icon-against-rail contrast 3.46–10.69:1, so every one clears the 3:1 non-text bar. |
| ⚠️ `shell.js GROUPS` | Grouping is UNCHANGED from what shipped — the brief's suggested grouping puts Requests under Community and Members under Server; the code has Requests under Overview and Members under Moderation. Left as-is deliberately (it is shipped and in use); moving either is a one-line move of the item object. |

### `site/public/assets/layout.js mountColumns` — the page fills the window

| Key | Note |
|---|---|
| ⚠️ `layout.js mountColumns` | **Must run AFTER `show('dash')`, and that is why it is called from `app.js` and not from inside `mountSections`.** It balances by measured `offsetHeight`, and a `hidden` element measures zero — `mountSections` runs while `#dash` is still hidden, so a balance done there would put everything in the left column. |
| `layout.js wide()` | A block that carries a table, the stat strip, a save bar, a note or a bare `.bar`/`.pager` **spans the full width and BREAKS the run**. Contiguous narrow blocks between two wide ones are balanced into the `.twocol` the Overview and Settings already used, so the reading order stays whole-block by whole-block instead of interleaving. `data-span="full"` on a node overrides the guess. |
| `layout.js balance()` | Heights are read for every block **before any of them moves**, because wrapping changes all of them. Then greedy: each block joins whichever column is shorter. Same idea as `page-settings.js share()`, which counts rows instead of pixels and is left alone. |
| ⚠️ `site.css #dash` | Gained `display:flex; gap:16px`. It was `display:block` with **no gap at all** — sections touched. The 16px matches what `.twocol`/`.colstack` already used, so a full-width block and a two-up run now sit on one rhythm. This is a visible spacing change on every page. |
| ⚠️ under 1100px | `.twocol` collapses to one column through the media query that already existed, and the reading order becomes **left column entirely, then right column** — the behaviour `page-settings.js` has always had. Verified by forcing the declaration in the browser, NOT by rendering at a narrow viewport: `resize_window` did not move `innerWidth` on this machine. |

### `site/public/assets/ui.js` — the dock, and the reset on the row

| Key | Note |
|---|---|
| ⚠️ `ui.js dockZone` / `saveBar` | **The bar places itself now.** It appends to one `.dockzone` strip built as a sibling of `.content` inside `.shell-main`, so callers no longer put `editor.bar` anywhere — `settingsPanel`, `page-settings.js` and the three `templateEditor` pages each dropped that line. A sibling and not an overlay: it takes layout space when a bar in it is visible and none when they are all hidden, so it can never cover a row. |
| ⚠️ `app.js clearDock()` | Called immediately **before** `page.load()` in both `paint` and `reload`. Without it a reload's new bars stack on top of the previous render's orphans, which are still visible and still wired to rows that no longer exist. `show()` also hides the whole zone whenever the gate is showing. |
| `ui.js saveBar where` | A page can carry more than one editor (Automod has three), so a bar says which panel it belongs to — `"All automod settings — 1 change pending"`. `namespaceSettings` passes its section title; `templateEditor` defaults to the key's own label; the seven `settingsPanel` call sites pass theirs. Without a name two dirty bars would be indistinguishable. |
| `ui.js settingRow wipe` | Clear-to-default is a **backspace text action on the row**, shown only while the row holds something and only for a type that has an empty state — `clearable()` refuses a segment (it always holds one of its choices) and a colour. It blanks the control and marks the row dirty; `settingsEditor.write` turns a blanked row that used to hold something into `clearSetting`, which is the behaviour that already existed. Per-row refusals still render beside their own row through `row.say`. |
| ⚠️ `site.css .shell grid-template-rows` | **`minmax(0, 1fr)`, and the fix is not cosmetic.** The shell's single implicit row was `auto`, an auto row is sized to its tallest item, and `align-content: stretch` only ever GROWS a row — so the docked bar pushed the whole column past the bottom of the window in **five of the six themes** (discord fit by luck). `.content` also moved from `flex-grow: 1` to `flex: 1 1 0`, so the body gives way instead of setting the column's height. Measured across six themes x light+dark: bar inside the window 12/12, `.content` still the scroller 12/12 — which is what `ui.js pager` depends on. |

### `site/public/assets/labels.js` — what a settings key is called

| Key | Note |
|---|---|
| ⚠️ `labels.js LABELS` | `/api/settings` carries `key`, `type`, `value`, `default` and `help` — and **no label**, so there is nothing on the wire to derive one from. The map is the one home; `ui.js` re-exports `humanLabel` so no consumer moved. All **90** registry keys are named (checked against `black_bloc/settings_store.py KEY_TYPES`; the mock serves 86 of them). |
| `labels.js derived()` | The old key-tidying rule, kept as the fallback, so a registry key added tomorrow still reads rather than rendering blank. Adding it to the map is the whole change. |

### Empty states and the title cap

| Key | Note |
|---|---|
| `ui.js sayNothing(text, action)` | An empty state is one sentence **and one thing to do about it**. `table()` takes `emptyAction`; `logsTable` passes one through. Callers that have no honest action pass none — deliberate, not an oversight. |
| `logs.js wayOut()` / `page-audit.js wayOut()` | The action **widens whatever narrowed the list**: "Show every line" while the Important switch is on, then "Clear the filters" if a kind or a query is set, then nothing when the log is genuinely empty — because then there is nothing to do. The Logs page's version reuses its existing Clear-filters button rather than repeating its reset. |
| ⚠️ empties left as a sentence only | Automod's rule book, birthdays, modmail, go-live, honeypot, chat, temp voice, events and health. Each already names the way out in words and none has a control on the page that would fill the list, so an action would have to be invented. Wired: every Logs section and the Logs page, the case book, Members, all five Requests lists, Polls (open / closed / archive / review), Role menus, and the "nothing matches what you typed" line inside `table()` and `searchOver()`. |
| `site.css --bb-page-title-size` | `min(var(--et-ui-xl), 24px)`. `--et-ui-xl` runs 24–30px across the six themes; the page title and the stat number now measure 24px in all twelve theme/mode pairs. |
| `site.css :root` block | ⚠️ **The site now owns tokens of its own**, defined RELATIVELY off `--et-*` at the top of `site.css`, so all six themes x light+dark get a value and `estate-theme.css` — an estate snapshot — is not edited. `--bb-nav-icon`, `--bb-nav-icon-active`, `--bb-page-title-size`, `--bb-stat-size`, `--bb-dock-bg`, `--bb-dock-border`, `--bb-reset-fg`, `--bb-reset-fg-hover`, `--bb-empty-gap`. |

### What R1 did NOT do

| Key | Note |
|---|---|
| per-rule Save buttons | Automod's rule cards and Requests' "Save the note" keep their own buttons. They are not `settingsEditor` rows — each writes a different route with its own body — so the docked bar does not own them. |
| `?v=` on module imports | `black_bloc/api/assets.py` stamps `href`/`src` in HTML only; an `import './icons.js'` inside a stamped module resolves without the query, exactly as `api.js` and `ui.js` already did. New files inherit the existing behaviour, they do not change it. |
| R2 | The new theme, the wordmark and display face, the copy voice, the show-keys toggle, the table toolbar/drawer and the command palette are all R2. R1 changed no theme's palette. |

# R2 — the restyle skin (`docs/info/site-restyle-design.md` §4), 2026-08-31

Front-end only; no route, contract or Python change. `node site/mock/check.mjs`
stayed green (17 pages / 98 routes) at every commit; `pytest -q` 2257 passed and
`ruff check .` clean at the end.

⚠️ **Read this first: the brief says "the 5 existing estate themes stay in the
dropdown". There are SIX** — `discord`, `classic`, `apple`, `cyberpunk`, `retro`,
`hearts` — so the dropdown now holds **seven**, not six. None of the six moved.

### `estate-theme.css` — the Black Bloc theme

| Key | Note |
|---|---|
| ⚠️ `:root[data-theme="blackbloc"]` | **The theme block goes in `estate-theme.css`, not in `site.css`.** R1 put the `--bb-*` helpers in `site.css` because they had to reach every theme without editing the snapshot; a THEME is different — `discord` is already a local addition to this same file ("this dashboard's own identity"), so a second one follows the precedent rather than inventing a place. `theme.js`'s `THEMES`/`LABELS` gained `blackbloc` as the first entry; that file is a snapshot too and the addition is marked as local. |
| `--et-danger: #f4707e` (dark) / `#b01b36` (light) | ⚠️ **The one COLD hue in a warm theme, on purpose.** The C direction's stated risk is that warmth reads as unserious beside a Ban button, so danger sits at hue ~350 where the accent sits at ~25. It reads as *not the accent* at a glance, which is the whole job. |
| the four values moved from § 4 C | `--et-accent` light is `#AA4109`, not the doc's `#C2500B`: at `#C2500B` the accent measures **4.15:1** on the rail's own active row, under AA. `--et-accent-2` light is `#8A5A00` (doc: `#B57C00`, 3.9:1 on white), `--et-muted` light `#68503F` (doc: `#6E584A`), `--et-danger` both modes per the row above. Everything else is the doc's table verbatim. |
| measured contrast | Worst text ratio anywhere in the theme: **4.51:1** (`--et-accent-2`/`--et-warn` on the light rail's active row). Dark runs 5.29–17.01; light 4.51–17.48. Button label on the primary fill: 7.21 dark, 6.05 light. Computed from the token hexes, not sampled off pixels. |
| `--et-bg-texture` | Two low-alpha radial gradients, no image — CSP `img-src` would allow a `data:` URI but a gradient costs nothing to ship. The `prefers-contrast: more` block that drops texture gained `blackbloc`. |
| the light block restates only what CHANGES | `:root[data-theme="blackbloc"][data-mode="light"]` matches the same element as the base block, so an undeclared token keeps the base value. `discord` restates its type scale in both; this one does not need to. |

### The display face

| Key | Note |
|---|---|
| ⚠️ `site.css --bb-title-font` / `--bb-chrome-font` | **`--et-font-display` had SIX readers and only two of them are titles.** The other four are the server name (16px), the stat number, the tile number and the confirm dialog's heading — all under 20px or inside a control, which the direction bans display type from. So the two title places take `--bb-title-font` and the other four take `--bb-chrome-font`; both resolve to `--et-font-display` on `:root`, so the six estate themes are unchanged, and `:root[data-theme="blackbloc"]` drops the chrome font to `--et-font`. |
| `--et-font-display: 'Bangers'` | Already self-hosted for `retro`/`hearts` (OFL, `assets/fonts/bangers.woff2` with `OFL-bangers-luckiestguy.txt` beside it), so **no font was vendored** and no new bytes ship. `Bricolage Grotesque` — the brief's first choice — would have meant fetching a file this machine cannot reach; the inspiration doc names Bangers as the on-disk alternative. |
| `--bb-wordmark-size: 20px` | The rail head was `--et-ui-md` (14px), which would put Bangers under the 20px floor. `--bb-mark-size` grows the bolt to match. Both stay at their old values in the six estate themes. |
| the page title stays 24px | `--bb-page-title-size` is R1's `min(var(--et-ui-xl), 24px)` and `--et-ui-xl` is 26px here, so the cap binds. Inside the brief's 20–26px window. |

### The copy voice

| Key | Note |
|---|---|
| `shell.js GROUPS` | Heads only: "Runs the server" / "Runs the cookout" / "The desk". ⚠️ **Membership is UNCHANGED** — Requests still sits under Overview and Members under Runs-the-server, exactly as R1 left them. |
| ⚠️ `labels.js LABELS` | All **90** rewritten from noun phrases to sentences. The key SET is byte-identical to R1's (checked by diffing the sorted key lists); only the values moved. `derived()` still returns a noun phrase for a key added tomorrow — deliberate, an honest fallback beats a fabricated sentence. |
| `page-settings.js NAMESPACE_NAMES` | The group headings were the raw namespace (`golive`, `rolemenu`, `tempvoice`). ⚠️ `section()` is called with `{ id: namespace }` so the **remembered open/closed slugs do not move** — without it every reader's saved state would silently reset. |
| ⚠️ `page-overview.js todayStrip` | **It REPLACED the "Needs a human" card, it does not sit beside it.** Both would have said the same three counts, and "one fact, one home" applies to surfaces. Built entirely from `/api/status` + the 10 important actions the page already fetched — no new request. The lead is about FAILURE (`_failed` kinds among the last actions), the clauses are about the QUEUE, and each clause is a link to the page that clears it. With no `status.open` it says the counts could not be read rather than printing zeros. |

### Table furniture

| Key | Note |
|---|---|
| `ui.js table()` | Three new options: `tools` (nodes into the toolbar), `foot` (`{noun,total,from}`) and a per-column `help`. Returns the bare `.table-scroll` exactly as before when none of search/tools/foot is wanted, so no existing caller's shape changed. |
| ⚠️ `ui.js footText` | **The foot OWNS the count.** Every surface that gained a foot lost its toolbar `.table-count` — Logs, both log sections, Members and Cases each had a second copy of the same number. `from` is the 1-based index of this page's first row, so a server-paged table counts across pages instead of restarting at 1. |
| `ui.js headCell` | The sentence goes on the `th`'s `title` and the `ⓘ` is `aria-hidden`, so hover and a screen reader get the same text once. Only columns that genuinely need explaining carry one. |
| ⚠️ `ui.js openDrawer` | A native modal `<dialog>` — Escape, the focus trap and the backdrop are the platform's, which is why it is ~30 lines. Cases uses it: a row used to set `state.openCase` and call `refresh()`, which refetched the whole page to append a section at the bottom. It now opens the drawer directly; `load()` re-opens it when `state.openCase` survives a refresh from inside the drawer. |
| ⚠️ Requests has NO drawer | It renders CARDS, not rows. There is no row for a drawer to belong to, and giving it one means rewriting the page into a table first — outside "furniture". Said out loud rather than forced. |
| ⚠️ `site.css --bb-scrim` | **Two defects fixed on the way.** `dialog.ask::backdrop` and the mobile sidebar `.scrim` were painted `var(--et-transit-bg, …)`, and `--et-transit-bg` is an OPAQUE notice tint, not a scrim — `:root` defines it, so the fallback never applied and every theme's modal blacked the page out completely. Both take `--bb-scrim` now. |
| `page-moderation.js` "Apply now" | Carrying out a shadow punishment for real was wearing the accent fill. `{ tone: 'danger' }` — the destructive path stays cold in every theme. |

### The command palette

| Key | Note |
|---|---|
| `palette.js railPages` | Pages come from the **live DOM** (`.nav-link` that is not hidden), not from `app.js TABS`. That is what makes a member-only session see only Requests without the palette knowing who is looking — the same trick `shell.js paintNavFor` already relies on. |
| `palette.js settingsEntries` | Indexed by label AND raw key. The Show-keys switch hides the key sub-line with CSS, not by omitting it, so a key search still works while the keys are out of sight. Gated on the Settings rail link being visible. |
| ⚠️ `page-settings.js jumpToKey` | **`behavior: 'auto'`, not `'smooth'`.** Measured: a smooth scroll started at the end of `load()` is cancelled by the next layout and the row is never reached — it stayed 1160px down the page. It also runs from `setTimeout(…, 0)` and not inline, because `app.js` calls `mountSections` (which re-applies the remembered open/closed state) and `mountColumns` (which re-parents every block) AFTER `page.load()` resolves. |
| `palette.js JUMP` | A `CustomEvent` on `document`, not a `window` global: when the row is already on this page the palette says so where it stands instead of reloading the page out from under it, and the event is inert on the sixteen pages that do not listen. |
| the `Ctrl K` hint | Injected by `mountPalette()` into `.topbar` rather than added to 17 HTML files, and it opens the same palette on click. |

### Show keys

| Key | Note |
|---|---|
| ⚠️ `ui.js` module top level | `data-showkeys` is stamped on `<html>` at IMPORT time, before a row is drawn — every page imports `ui.js`, so a reader who wants the keys never watches them appear a frame late. Reading and writing `localStorage` are both inside `try`/`catch`; a browser that refuses storage still works, the choice just is not remembered. |
| `site.css :root:not([data-showkeys="true"]) .setrow-key` | Hidden by CSS and **not** by omitting the node, which is what keeps the palette's key search working. |

### What R2 did NOT do

| Key | Note |
|---|---|
| the estate themes' own contrast | Untouched, and several of them are still sub-AA. The brief scopes the 4.5:1 promise to the new theme in both modes. |
| ⚠️ long group captions in `cyberpunk` | That theme sets `--et-nav-head-size: var(--et-ui-lg)`, so "RUNS THE COOKOUT" wraps to two lines in the rail. Seen, left alone: fixing it means either shortening the owner's words or overriding a theme's own type scale from page CSS. |
| a `themes` note in `estate-theme.css`'s header | The header still says "FIVE NAMED THEMES" and lists neither `discord` nor `blackbloc`. It was already wrong before this build. |
