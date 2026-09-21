# Phase 5 design — birthdays (F6)

> 🔴 **RETIRED IN PART, 2026-09-20 (branch `events-group`, off `main` `5ea8d44`) — THE BIRTHDAY BOT
> IMPORT IS GONE, WHOLE.** Owner: *"in bvirthdays remove the import from birthday bot, its been
> kicked"* — the bot that produced the export was kicked from the server, so the source no longer
> exists. ~~Every bullet below about importing the 39-row export~~ is history: the seed file
> `black_bloc/data/birthday_import_2026-08-05.json`, `birthdays.parse_export` / `ImportRow` /
> `load_import_rows` / `import_as_of_year` / `resolve` / `score_member(s)` / `strip_tags` /
> `year_from_age`, the cog's `import_rows` / `report_lines` / `candidate_text` / `_import_loop` /
> `import_once`, `POST /api/birthdays/import`, the site's **Import from Birthday Bot** card and
> the `birthday.import` log kind are all DELETED. The **stored** birthdays are untouched — a row
> whose `source` is `import` keeps it, and the status line still counts them. The transcribed
> export survives as the archive doc
> [`../archive/current-bots/birthday-bot-export-2026-08-05.md`](../archive/current-bots/birthday-bot-export-2026-08-05.md),
> which is the only copy left.
>
> ⚠️ **SUPERSEDED IN PART, 2026-09-03 (v63, `616adb3`) — the slash surface is gone.**
> `/birthday` is ONE command that opens an ephemeral panel and all twelve subcommands are
> retired. See [`birthdays-panel-design.md`](birthdays-panel-design.md) and
> [`panels-program.md`](panels-program.md). Everything else here still describes what is built.
>
> **Audience:** the Phase 5 build agent and the reviewer. **Status:** TRACKED ·
> ✅ **LIVE since 2026-08-26** (shipped in `shadow`) — deployed `2026-08-27T04:56:54Z` as
> `08b114c` (`deploys.log` line 8, `synced 11 app commands`); `DONE.md` → "2026-08-26 — Phase 5
> live: birthdays (F6) — first parallel-worktree phase". ⚠️ Fly release numbers were not
> written into `deploys.log` until **v59** (2026-09-03), so this landing has a date and a
> commit but no `vNN`.
> **Last verified: 2026-09-11 09:00** — re-checked against the tree at `1d090e5`:
> `black_bloc/birthdays.py` and `cogs/community/birthdays.py` exist, the seeded data file
> `black_bloc/data/birthday_import_2026-08-05.json` is committed, `Birthdays._import_loop`
> exists, and all **six** `birthday_*` keys named below are in `KEY_TYPES`.
> ⚠️ **NOT checked:** whether `birthday_mode` is still `shadow` on the live guild, whether
> Birthday Bot is still posting, and anything in Discord — nothing in this pass met Discord
> or a browser. The channel and role IDs below need a live scan.
> Before that, **2026-08-26** — incumbent behaviour measured from 16
> Birthday Bot posts (`archive/current-bots/discord-scan-2026-08-26.md` §C);
> seed data = `archive/current-bots/birthday-bot-export-2026-08-05.md` (39
> rows). Depends on Phase 1 (settings, action log) and Phase 4
> (`user_timezones`).

## Owner decisions this implements

- Opt-in birthdays; **per-member midnight**, **fallback = server midnight
  (America/Phoenix)** when the member has no timezone set.
- Import the 39-row Birthday Bot list; every unresolved name is reported,
  never guessed.

## What the incumbent does (to match)

Channel **`#return-of-the-gen`** (`1411816390414962700`). An embed with
`description = "Happy Birthday **{display_name}**!"`, colour `#4eefff`, no
title/footer/fields, empty content, no ping, no role. Fires at ≈00:03 in
the member's own zone. It echoes the nickname verbatim (`[40] PT`). The
`🎂` role (`1467088677330227305`) exists but nothing observed grants it.

## Shape

```
black_bloc/
├── birthdays.py                 ← pure: next_occurrence(month, day, tz, now), age(year, today), name resolution scoring, export parser
└── cogs/community/birthdays.py  ← the cog: /birthday commands, five-minute sweep, daily import loop
tests/ test_birthdays.py · cogs/community/test_birthdays.py
```

Schema v6 (additive):

```sql
CREATE TABLE IF NOT EXISTS birthdays (
    user_id INTEGER PRIMARY KEY, guild_id INTEGER NOT NULL,
    month INTEGER NOT NULL, day INTEGER NOT NULL, year INTEGER,          -- year optional
    opted_in INTEGER NOT NULL DEFAULT 1, source TEXT NOT NULL,           -- 'self' | 'import'
    set_at TEXT NOT NULL, last_announced_on TEXT                          -- 'YYYY-MM-DD' in the member's zone
);
```

Settings keys: `birthday_channel_id` (default `#return-of-the-gen`; test
channel while TEST_MODE), `birthday_template` (default
`Happy Birthday **{name}**!`), `birthday_color` (`#4eefff`),
`birthday_role_id` (none; if set, add for the day and remove the next),
`birthday_mode` (`off|shadow|on`, default **`shadow`** — Birthday Bot keeps
posting until the owner flips it), `birthday_show_age` (bool, default
**false** — the incumbent didn't compute ages; `{age}` is available in the
template when a year is stored and the flag is on).

## Timing (the Phoenix gotcha, resolved)

A `tasks.loop(minutes=5)`: for every opted-in row, compute `today` in the
member's zone (`user_timezones`, else `America/Phoenix`); if `(month, day)
== today` (Feb 29 → Feb 28 in non-leap years) AND `last_announced_on !=
today` AND local time ≥ 00:00 → announce and set `last_announced_on`. Five-
minute granularity means posts land 00:00–00:05 local, matching the
incumbent's ≈00:03. Because the check is "today in *their* zone", the
announcement lands on the right calendar day for them — which, for a UTC-4
member, is the evening before in Phoenix, exactly as today. Restart-safe:
`last_announced_on` prevents double posts.

## Import — the daily loop (was `/birthday import`)

> **Superseded 2026-08-27** (owner: *"lets hide the birthday import command and
> just put it on a daily cron"*). The slash command is gone — deleted, not
> hidden, so it is deliberately not in `command_visibility.HIDDEN_WHEN_OFF`.
> The resolution, scoring and idempotency described below are unchanged and now
> run on `Birthdays._import_loop` (`@tasks.loop(hours=24)`): once at startup, so
> a fresh deploy imports within a minute, then daily. No report is posted to a
> channel any more — the action log gets a `birthday.import` line
> (`actor=None`, `"trigger": "daily"`) **only when a run actually imported
> somebody**; a 0-row run is a `log.info`. The staff-facing on-demand path is
> the web tool (`POST /api/birthdays/import`), which still returns the full
> report. `/birthday status` and the Health tab both show the loop's last run
> and last error. Detail: `docs/info/code-notes.md` § *birthdays — daily
> import loop (2026-08-27)*.

The original design, still accurate about matching and idempotency:


Parses `birthday-bot-export-2026-08-05.md`'s table (the builder embeds the
39 rows as a Python literal in the cog module? **No** — data is not code:
ship it as `black_bloc/data/birthday_import_2026-08-05.json`, committed,
generated from the archive doc). Resolution: for each row, strip bracket
tags/`(Umazing)`-style prefixes, then match against members by exact
display name, exact username, then case-insensitive contains, scoring 3/2/1;
a unique best match ≥ 2 imports (`source='import'`, `opted_in=1`, year from
the age column if present: `year = 2026 - age` with a ±1 caveat noted in
the report); everything else goes into the **report** posted to the
invoking channel: *N imported · M ambiguous (candidates listed) · K not
found* — the owner resolves those by hand with `/birthday set @user`.
Re-running never overwrites a `source='self'` row. Member lookup uses
`guild.query_members(query=…)` (HTTP, no members intent needed) per name.

## Commands

> ⚠️ **Superseded 2026-09-03 (v63, `616adb3`) by [`birthdays-panel-design.md`](birthdays-panel-design.md):
> `/birthday` is now ONE command that opens a panel, and every subcommand listed below is
> retired.** Nothing else in this document changes — the sweep, the role, the daily import
> and the settings are untouched; only the front door moved.

- `/birthday set <month> <day> [year]` — self; `/birthday remove`; `/birthday
  optout` / `optin`; `/birthday show [@user]`; `/birthday next` — next 5
  upcoming (opted-in only), rendered with `<t:…:D>`.
- Staff: `/birthday set-for @user …`, `/birthday list` (paginated by month,
  like the incumbent's list), `/birthday mode`, `/birthday settings …`.
  (`/birthday import` was removed 2026-08-27 — see the Import section above.)

## Test mode

Announcements go to the test channel (guard). The role side effect is
skipped while `TEST_MODE` (logged). The owner can test by `/birthday set`
to today's date in their zone → the next loop tick posts within 5 minutes
(in shadow: a `birthday.would_announce` log line; in `on`: the embed).

## Tests (offline)

`test_birthdays.py`: `next_occurrence` across zones incl. Feb 29 and the
UTC-4-evening-before case; `age()`; name-resolution scoring on the real 39
names against a fake member list (include the `[40] PT` and `(Umazing)
nadia` shapes); export parser yields 39 rows with December 12 split.
`cogs/community/test_birthdays.py`: loop picks exactly today's rows once;
`last_announced_on` guard; import idempotency and the report counts.

## Definition of done

As before; two commits (pure logic + data file → cog). Owner's test sweep:
`/birthday next`, one same-day `set` to see a post, and `/birthday list` to
see what the daily import brought over (2026-08-27: the import is no longer a
command to run).
