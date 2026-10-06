# Structure backup — a dated copy of the server's roles, channels and permissions

> **Audience:** the build agent, reviewers and future Claude sessions. **Status:** TRACKED ·
> 🔨 **BUILT on branch `structure-backup`** (off `main` `1cde5594`), NOT merged, NOT deployed.
> **Last verified: 2026-10-05** — by the hermetic test suite and the local mock only (figures at the
> foot under *Gate*). ⚠️ **NOT checked:** nothing here has met Discord. No real guild was captured,
> no notice was posted, `/structure` was never opened in a client, and the claim that the bot is
> sent every channel's overwrites (including channels it cannot view) is discord.py's documented
> behaviour, not a measurement. ⚠️ Secret NAMES only.

## The ask

Owner, 2026-10-05, verbatim: *"Let's build 1, 8, 10 / We'll leave them in shadow for now"* — 10
being *a saved copy of the server's roles, channels and permissions, Xenon-style*, from the
filtered list of popular bot features in `docs/TODO.md`.

**Read as:** capture and compare. The owner asked for a saved copy; putting one back is a
different, permission-granting act he has not asked for (see *Not built*).

## A. What a snapshot holds

One JSON document per snapshot, `version` **1**, built through explicit field lists in
`black_bloc/structure.py` (`GUILD_FIELDS`, `ROLE_FIELDS`, `CHANNEL_FIELDS`, `TAG_FIELDS`,
`OVERWRITE_FIELDS`). The same lists build the capture AND the download, so a field can only
leave the bot if it is named there.

| Part | Fields |
|---|---|
| `guild` | `id`, `name`, `verification_level`, `default_notifications`, `system_channel_id`, `rules_channel_id` |
| `roles[]` | `id`, `name`, `color`, `permissions`, `position`, `hoist`, `mentionable`, `managed` |
| `channels[]` (categories are channels of type `category`) | `id`, `name`, `type`, `parent_id`, `position`, `topic`, `slowmode`, `nsfw`, `bitrate`, `user_limit`, `tags[]`, `overwrites[]` |
| `tags[]` (forums) | `id`, `name`, `moderated`, `emoji` |
| `overwrites[]` | `target_id`, `target_type` (`role` \| `member`), `allow`, `deny` |

Ids are strings (a snowflake does not survive a JavaScript number); permission values are
integers. Lists are sorted by id so the same structure always serialises to the same bytes.

🔴 **Never captured:** message content, member lists, who holds which role, member names,
threads, emoji, stickers, invites, webhooks, bans, integrations. A member-level overwrite is
permission structure and IS captured — as the member's id and nothing else; the change list
reads *member 123…* because no name is stored.

## B. When one is taken

- **Daily**, at `structure_backup_hour` (default **4**) in the server's `default_timezone`
  (the repo's one configured zone, default America/Phoenix). The loop ticks every ten minutes;
  a guild is due when its local hour has reached the key and `structure_looks.last_day` is not
  today, so a bot that was down at the hour catches up when it comes back.
- **On demand** by staff: `/structure` ▸ **Take one now**, or the Structure page.
- Roles and channels are **fetched** (`guild.fetch_roles()`, `guild.fetch_channels()`) rather
  than read off the cache: two calls a day, and a Discord refusal becomes a failure the log
  names instead of a silently stale copy. Guild-level fields come off the cached guild.
- **Unchanged means no second copy.** The body is hashed (SHA-256 of the canonical JSON). When
  the digest equals the latest snapshot's, nothing is inserted: the latest row's `checked_at`
  and `checks` move, and `structure.unchanged` is logged.
- **Kept:** `structure_backup_keep` (default **60**) snapshots per server, oldest pruned after
  every stored snapshot (`structure.pruned`).
- **A failure never leaves the loop.** `take_snapshot` catches everything, writes
  `structure.capture_failed` with the reason in words, and stamps `structure_looks`. A failed
  daily look is tried again on later ticks, at most **3** times that day, then waits for tomorrow.

## C. Compare

`black_bloc/structure_diff.py:changes(old, new, say)` — a pure function over two snapshot
dicts, no Discord objects. It returns `{area, kind, text}` rows in words: server fields, roles
added / removed / renamed / permissions gained and lost **by name** / colour, hoist,
mentionable / moved; channels added / removed / renamed / moved to another category / reordered
/ topic, slowmode, age-restricted, bitrate, user limit, type; forum tags; overwrites added /
removed / changed with the allowed and denied permissions gained and lost by name. Ids resolve
to names from the two snapshots themselves (new first, then old).

- **Moves are the smallest set.** Adding one role shifts every position above it; reporting raw
  position numbers would call the whole list changed. Order is compared among the items both
  snapshots hold, and only those outside the longest run that kept its order are *moved*.
- **A new or removed channel does not also list its overwrites** — the count is in its line.
- Two doors: any two stored snapshots, and **latest vs now** (a live capture that is compared
  and thrown away, never stored).

## D. Mode, and the only thing the feature posts

`structure_backup_mode` = `off` \| `shadow` \| `on`, default **`shadow`**.

| Mode | Capture (daily + on demand) | *Structure changed* notice |
|---|---|---|
| `off` | no; **Take one now** refuses in words | none |
| `shadow` | yes, silently | to the feature's shadow home (`structure_backup_shadow_channel_id`, then `shadow_channel_id`, then the log channel — `black_bloc/shadow.py`), under the rehearsal note |
| `on` | yes, silently | to `structure_backup_channel_id`; blank means `staff_channel_id` |

The notice is posted only when a **daily** snapshot differs from the one before it, and only
while `structure_backup_notify` is true. It is one embed: `structure_backup_notice_title`,
`structure_backup_notice_text`, then at most `structure_backup_notice_lines` change lines and
`structure_backup_notice_more`. `AllowedMentions.none()` — role and channel names are
attacker-controlled text. An on-demand snapshot posts nothing; the person who pressed it is
looking at the answer. Comparing and downloading stored snapshots stays open in `off`.

## E. Doors

- **Discord:** `/structure` (staff, `STAFF_ONLY`), one ephemeral panel: the latest snapshot's
  time and counts, the last look and how it went, **Take one now**, **What changed** (latest vs
  now), and a link button to the page. No second slash command.
- **Site:** `structure.html` — the snapshots table, **Take one now**, compare any two (or one
  against now), download one as JSON, the feature's settings, its log.
- **API** (`black_bloc/api/tools/structure.py`, staff only): `GET /api/structure`,
  `POST /api/structure/snapshots`, `GET /api/structure/compare?old=&new=`,
  `GET /api/structure/snapshots/{id}/download`.
- The download is `structure.export(row)`: built from `SNAPSHOT_FIELDS` and the field lists in
  §A, never the row. Each download leaves a `structure.downloaded` row.

## F. Storage — schema **88**

Two tables, appended to `SCHEMA` (additive; no column migration):

- `structure_snapshots` — `id`, `guild_id`, `taken_at`, `source` (`daily` \| `manual`),
  `taken_by`, `digest`, `roles`, `categories`, `channels`, `overwrites`, `checked_at`, `checks`,
  `body` (the JSON).
- `structure_looks` — one row per guild: `last_at`, `last_day`, `outcome`
  (`saved` \| `unchanged` \| `failed`), `reason`, `attempts`. It is what makes *looked, nothing
  changed* and *failed* visible without a snapshot row, and what stops a second daily run.

It lives inside the SQLite database, so it rides the existing database backups
(`docs/access/RECOVERY.md`).

## G. Keys — all under `core`

`structure_` would have been a 26th setting group and `/settings`' group select is at Discord's
cap of 25, so every key is added to `CORE_KEYS`. Operational: `structure_backup_mode`,
`_hour`, `_keep`, `_notify`, `_channel_id`, `_shadow_channel_id`, `_notice_lines`,
`_panel_minutes`. Wording: the notice's three lines, the panel's title, labels, lines and
answers, and one `structure_backup_say_<name>` key per sentence and label the change list can
write (`structure_diff.WORDS` is the one home of the defaults). Channel type names and
permission names are Discord's own identifiers, title-cased, not prose.

## H. Log kinds — head `structure`, filed under `core`

Routine: `structure.captured`, `structure.unchanged`, `structure.pruned`,
`structure.notice_posted`, `structure.downloaded`. Important by suffix:
`structure.capture_failed`, `structure.notice_failed`. The website's capture and download carry
the `web.` head through `kind_via`. Success, *looked and nothing changed*, and failure are three
different kinds (checklist 2).

## Not built

🔴 **No restore.** There is no *apply*, no *put it back*, and no code path in this feature that
creates, edits or deletes a role, a channel or a permission overwrite. Restoring a snapshot
grants permissions; that is access-increasing and is the owner's separate decision. Rebuilding
a server from a snapshot today is a manual, undrilled procedure with the downloaded JSON open
beside Discord's own settings.

Also not built: a per-snapshot note or label, deleting one snapshot by hand (pruning is by
count only), an event-driven snapshot on every role or channel change, threads, and a log-level
key of its own (the kinds follow `core_log_level`).

## Decisions made by the build beyond the brief

1. **Fetch, not cache**, for roles and channels (§B) — it is what makes *missing permission /
   Discord error* a real, loggable outcome.
2. **`structure_looks`** is a table of its own (§F). The brief asked that an unchanged look be
   recorded; the snapshot row carries `checked_at`/`checks`, and the looks row carries the
   failure a snapshot row cannot.
3. **Three attempts a day** for a failed daily look (§B). One would lose a day to a blip; a
   retry every tick would write 144 failure rows.
4. **Blank `structure_backup_channel_id` means the staff channel** in `on` (§D).
5. **`structure_backup_notify`** is the switch that makes the notice optional (§D).
6. **Keys are `core`** (§G), and there is **no `structure` feature** in `logkinds.FEATURES` —
   a 23rd feature would add a log-level key and a 26th setting group.
7. **`/structure` is not hidden when the mode is `off`.** Stored snapshots stay readable and
   comparable in `off`; hiding the command would hide them.
8. **Every change-list sentence is a settings key** (§G), per the every-word-editable rule.
   It is ~45 keys; the alternative was prose only the code knows.
9. **Member overwrites are kept, by id only** (§A).
10. **Downloads are logged** (`structure.downloaded`) — it is a copy of the permission layout
    leaving the bot.
11. **Guild fields are exactly the brief's five** plus `id`; AFK, locale and content-filter
    settings were left out rather than guessed at.
12. **`now` compares are not stored and not logged.**

## Gate

Recorded by the build at its last commit — see the branch's final report for the exact lines.
