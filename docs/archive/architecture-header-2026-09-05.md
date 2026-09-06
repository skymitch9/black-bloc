# Architecture header — the per-branch readings, 2026-09-03 and earlier

> ⚠️ **RETIRED 2026-09-05.** This is the stacked header
> [`../info/architecture.md`](../info/architecture.md) carried until v92: five paragraphs of
> per-branch figures that disagreed with each other and with the repo, plus the historical
> build-order narrative. **Replaced by** that file's one measured v92 block and its "how the
> counts moved" table. Nothing here is a current reading — every figure in it was superseded
> before it was archived, and the last paragraph is wrong twice over (the site HAS been opened
> in a browser and `blackbloc.heygabi.ai` HAS a certificate). Kept for the reasoning, never
> for the numbers.

**Audience:** Claude sessions and the owner. **Status:** TRACKED (owner,
2026-08-31 — was local-only until then).
Last verified: **2026-09-03** — the fast-moving figures re-measured on `main` after the
**17 → 18 → 19 merge** (`6d61994` chat memory + requests state machine, `0bb3835` raid trains,
`7b1c592` applications), deployed `7b1c592`: `SCHEMA_VERSION` is **25** (23 `chat_profiles` +
`chat_memory_optout` + `requests.held_from` and the pending/approved/planned → open migration,
24 `raid_trains` + `raid_slots`, 25 `application_forms` + `application_questions` +
`applications`). `bot.py:COGS` is **19** cogs and the tree has **44** top-level slash
commands; `node site/mock/check.mjs` reports **17 pages / 136 routes**; `ruff check .` clean;
**3238** tests pass. `settings_store.FEATURES` / the log-level keys count **17**. New files since
Phase 16: `chat_memory.py`, `cogs/content/chat_memory.py`, `raidtrain.py`,
`cogs/content/raidtrain.py`, `api/tools/raidtrain.py`, `applications.py`,
`cogs/community/applications.py`, `api/tools/applications.py` and their mirrored tests. ⚠️ None
of the three features has run against live Discord; all three modes ship **off**. The paragraphs
below are the per-branch readings this one supersedes, left as written.

*(Superseded 2026-09-03:)* the fast-moving figures re-measured on the
**Phase 19** branch (applications, built in parallel with 17 and 18 and merged LAST):
`SCHEMA_VERSION` is **25** — 23 and 24 are Phase 17's and Phase 18's and are empty on this
branch; 25 adds `application_forms`, `application_questions` and `applications`.
`bot.py:COGS` is **17** cogs and the tree had **41** top-level slash commands on that branch
(`/apply` for members, `/applications` for staff). ⚠️ **Stale as a current reading:** on `main`
at `27452ac` the tree is **43**, and the applications panel build takes it to **42** — one
member-visible `/apply` carries both halves and the `applications` group is gone. `node site/mock/check.mjs` reports **17 pages /
126 routes**; `ruff check black_bloc tests site` clean. New files:
`applications.py`, `cogs/community/applications.py`, `api/tools/applications.py` and
their mirrored tests. ⚠️ Measured on the Phase 19 branch only — NOT merged, NOT deployed,
and never run against live Discord. The row below is the Phase 18 reading it sits on.

**Phase 18** branch: `SCHEMA_VERSION` is **24** (17 sessions, 18
`polls.vote_scheme`, 19 `golive_sessions.live_role_id`, 20 the chat tables,
21 `golive_fan_roles`, 22 `youtube_links` + `youtube_videos`, ⚠️ **23 is
Phase 17's and is EMPTY on this branch**, 24 `raid_trains` + `raid_slots`),
`check.mjs` reports **17 pages / 123 routes**, `ruff check .` clean;
`bot.py:COGS` is now **17** cogs and the tree has **41** top-level slash
commands. ⚠️ Phase 18 is on a BRANCH beside Phase 17 — neither is merged and
neither is deployed, so the LIVE bot is still schema 21 / 15 cogs / 37
commands until the conductor merges them (order: 17, then 18). Before that,
the same figures on the Phase 16 branch were schema 22 / 16 cogs / 39
commands / 116 routes / **2865** tests. New since
the tree below was drawn: `chat_llm.py`, `llm.py`, `groq.py`, `knowledge.py`,
`personas.py`, `directory.py`, `chat_check.py`, `dbsnapshot.py`,
`api/costs.py`, `pings.py`, `cogs/content/pings.py`, `api/tools/pings.py`,
`youtube.py`, `cogs/content/youtube.py`, `api/tools/youtube.py`,
`raidtrain.py`, `cogs/content/raidtrain.py`, `api/tools/raidtrain.py`. ⚠️ NOT re-checked: the Shape tree's per-file annotations
(verified 2026-08-31). Three cogs (polls, requests, chat) and eleven modules the tree did not
list have been added, and the **Carl parity** entries removed — parity was
deleted in `47634b8` and `grep -ri carl black_bloc site` is empty.

⚠️ **NOT verified today:** the *prose* below the tree (the rules, the library
table, the API section) was read but not re-traced to the code; and nothing
here was checked against the running bot or a browser.

🔴 **The "NOT verified" paragraph that used to end this header was itself
stale and is replaced.** It claimed the site had never been opened in a
browser and that `blackbloc.heygabi.ai` had "no DNS record and no certificate
yet". Both are false: the owner signed in and saw the dashboard on 2026-08-26
~23:00, the site has been served from the Fly app on that hostname since, and
`docs/deploys.log` records **37 deploys**, the last `8036918` at **2026-08-27
20:15**. What IS still unexercised by a person is tracked, per feature, in
[`../access/sweeps.md`](../access/sweeps.md) — that file is the one home for
"shipped but never clicked", and this header should not grow a second copy.

*(Historical build-order narrative, left as written and NOT re-checked:)*
matches the code after **presence**
(`presence.py`, `cogs/presence.py`, the `bot_bio` and `status_prefix` registry keys;
**1194 tests pass, ruff clean**), on top of the **Phase 8b merge
and reconciliation** (the full dashboard: `api/{writes,names,ref,settings_api}.py`
and `api/tools/*`, thirteen tabs under `site/public`, and `site/mock/` as the
contract's executable form; **1105 tests pass, ruff clean**), on top of the
**Phase 8a merge**
(the config site: `api/auth.py`, `api/status.py`, the reworked `api/server.py`
and the committed `site/` tree; **800 tests pass, ruff clean**), on top of the
**Phase 6 merge**
(moderation: `automod.py`, `modcases.py`, `cogs/moderation/automod.py`,
`cogs/moderation/modcmds.py`), on top of the **Phase 7 merge**
(modmail: `modmail.py`, `cogs/moderation/modmail.py`), on top of the Phase 5
merge (birthdays: `birthdays.py`, `cogs/community/birthdays.py`, the shipped
`data/` seed), the Phase 4 build (timezones, events logic, the
events cog), the Phase 3 adversarial review fixes (temp voice, honeypot,
staff derivation) and the Phase 2 go-live review fixes (Twitch client,
go-live logic, go-live cog, `command_errors.py`). **Schema v8** — Phase 6's
`mod_cases` table with two indexes and its five additive columns
(`actions`, `done`, `failed`, `message_id`, `channel_id`), beside Phase 7's
four `modmail_*` tables, two indexes and its additive
`modmail_messages.delivered`, on top of Phase 5's `birthdays` plus
`birthdays.role_added_id`,
Phase 4's `user_timezones` and `events`, Phase 3's three tables, v3's one
additive column and one partial unique index, all applied by idempotent
steps inside `Database.connect`. ⚠️ **v7 was skipped and stays skipped:** it
was Phase 6's own bump, and the Phase 6 merge kept **8** rather than
renumbering, because every statement on both sides is additive and
idempotent — the number is a label, and the merge order does not change the
database it produces. ⚠️ **Phase 6 brought the project's first NON-additive
step**, and it is bounded and idempotent: a `mod_cases` whose `user_id` is
`NOT NULL` is set aside before the schema script runs, recreated nullable
and copied back (`storage/db.py:296`), because a purge case belongs to a
channel rather than a member. It needs no version branch — the PRAGMA check
returns immediately on a table that never had the constraint. **Phase 8a added
no schema at all** — the status page is a reader, so the version stayed **8**
through 8a and 8b. ⚠️ **The temp-voice panel + `/voice` merge (2026-08-27) took
it to 10**, and this time the numbers are used rather than skipped:
`tempvoice_channels.panel_channel_id` is 9 (a click has to find its channel now
that the panel can live somewhere else) and `tempvoice_prefs.bitrate` is 10.
Both are additive through `ADDED_COLUMNS` and both are in `SCHEMA` as well, so a
fresh database and a migrated one agree. 1134 tests pass; ruff clean.
`cogs/community/role_menus.py` is now the worked example of the cog
convention; `cogs/community/events.py` is the worked example of a feature
whose side effects the guard cannot see at all, and
`cogs/moderation/modmail.py` is the worked example of a feature whose whole
SURFACE the guard would otherwise refuse — see `speak()` there, and
`cogs/moderation/automod.py` is the worked example of a feature whose side
effects (delete, timeout) the guard cannot see AND which therefore checks
`bot.guard` by hand at every act site. NOT verified:
any of it
running against live Discord, no call has ever been made to the real Twitch
API from this repo, no real Discord scheduled event has ever been created
by it, and no DM has ever been relayed into a ticket — `modmail_enabled`
defaults **false**, so the incumbent ModMail bot still holds the inbox. Nor
has automod ever deleted a message, timed anybody out or read a Carl-bot
modlog: `automod_mode` defaults **shadow**, and while `TEST_MODE` is on the
engine only ever sees the test channel itself. Nor has the **site** ever been
opened in a browser, nor has anybody completed a real Discord OAuth round-trip
against this code: `blackbloc.heygabi.ai` has no DNS record and no certificate
yet, and the cookies, CSP and static mount are asserted against an in-process
ASGI client, which is not a browser (`../access/site.md`).
