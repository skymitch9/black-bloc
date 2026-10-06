# Structure backup — a dated copy of the server's roles, channels and permissions

> **Audience:** the build agent, reviewers and future Claude sessions. **Status:** TRACKED ·
> 🔨 **MERGED to `main` at `c16deab1`** (2026-10-05, the build and the independent review's fixes),
> **NOT deployed.** Branch `structure-fold-words` (off `c16deab1`, code in `59e62d81`, NOT merged,
> NOT deployed) folds the 46 change sentences into code and is what this page now describes — see
> *Wording folded into code 2026-10-05* near the foot. Branch `structure-leads` (off `main`
> `6e5136c5`, code in `c35746f6`, NOT merged, NOT deployed) makes the whole feature **leads
> only** and stops the notice falling back to any other channel — see *Leads only 2026-10-05*;
> the struck lines in §B, §D, §E and *Decisions* 4 are what it reversed.
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
- **On demand** by ~~staff~~ the server's leads (*Leads only 2026-10-05*): `/structure` ▸
  **Take one now**, or the Structure page.
- Roles and channels are **fetched** (`guild.fetch_roles()`, `guild.fetch_channels()`) rather
  than read off the cache: two calls a day, and a Discord refusal becomes a failure the log
  names instead of a silently stale copy. Guild-level fields come off the cached guild. Each
  fetch has **30 seconds** (`FETCH_SECONDS`); a fetch that does not answer is *Discord could not
  be reached*, never a permission sentence.
- **A capture with no roles or no channels is refused** (`NO_ROLES`, `NO_CHANNELS`) — a server
  always has both, so an empty list is Discord answering badly, not a structure to store.
- **Unchanged means no second copy, and "unchanged" has one rule: the digest equals the latest
  snapshot's.** The digest and the change list agree — a digest that differs always has
  something to say — because (a) every field a snapshot holds has a sentence, a forum tag's
  emoji and `moderated` flag included, and (b) the digest is taken over each role's and
  channel's **place in the order** (`structure.placed`: roles top down, channels within their
  category and kind — the same `top_down` / `in_order` the change list uses), not its raw
  position number, so positions renumbered with the order kept are the same structure. On an
  unchanged look the latest row's body is still **refreshed in place** so the copy held is
  exact (raw positions included), its `checked_at` and `checks` move, and
  `structure.unchanged` is logged. ~~"unchanged" has one rule: the change list has nothing to
  say (`structure_store.same`), equal digests being only the fast path~~ — reversed 2026-10-05
  on `structure-fold-words` (`59e62d81`): that rule existed because two differences had no
  sentence and adding one cost a settings key; with the wording in code they have sentences
  and `same` is gone. (It had itself reversed ~~when the digest equals the latest snapshot's,
  nothing is inserted~~ on `structure-fixes`, review N1, when the raw-position digest stored
  rows whose change list read *0 changes*.)
- **Kept:** `structure_backup_keep` (default **60**) snapshots per server, oldest pruned after
  every stored snapshot (`structure.pruned`) — **except the snapshot the next notice starts
  from** (`structure_looks.noticed_id`), which is held until that notice is posted, so a server
  can briefly hold `keep` + 1.
- **A failure never leaves the loop.** `take_snapshot` catches everything, writes
  `structure.capture_failed` with the reason in words, and stamps `structure_looks`. A failed
  daily look is tried at most **3** times that day, **four hours apart** (`RETRY_GAP_MINUTES`;
  a late hour shares what is left of the day: `retry_gap`), then waits for tomorrow.
  ~~tried again on later ticks~~ — reversed 2026-10-05 (review N6): three tries were spent in
  thirty minutes.
- **An unavailable server is a failed look, not a skipped one** — a `structure_looks` row with
  the reason and one `structure.capture_failed`, on the same three-a-day budget (review N7).
- **A look by hand never moves the daily look's day or its tries** (`record_look(day=None)`),
  whichever way it went (review N2).

## C. Compare

`black_bloc/structure_diff.py:changes(old, new)` — a pure function over two snapshot
dicts, no Discord objects, no settings: its wording is `structure_diff.WORDS`, fixed in code. It returns `{area, kind, text}` rows in words: server fields, roles
added / removed / renamed / permissions gained and lost **by name** / colour, hoist,
mentionable / moved; channels added / removed / renamed / moved to another category / reordered
/ topic, slowmode, age-restricted, bitrate, user limit, type; forum tags added / removed /
renamed / emoji / moderators-only; overwrites added /
removed / changed with the allowed and denied permissions gained and lost by name. Ids resolve
to names from the two snapshots themselves (new first, then old).

- **Moves are the smallest set.** Adding one role shifts every position above it; reporting raw
  position numbers would call the whole list changed. Order is compared among the items both
  snapshots hold, and only those outside the longest run that kept its order are *moved*.
- **A new or removed channel does not also list its overwrites** — the count is in its line.
- Two doors: any two stored snapshots, and **latest vs now** (a live capture that is compared
  and thrown away, never stored).
- **Two channels with one name say where they are**: `general · Lobby`, and `general · Lobby ·
  <id>` when the category is shared too (`Names.label`). A name nobody shares is left alone.
- **An overwrite is its target AND its kind** (`by_target`), so a target whose kind changed is
  one overwrite removed and one added, never silence.
- **Two readers.** `changes(old, new, escape=...)`: Discord's readers (the panel and the
  notice) pass `structure_backup.safe` — `escape_markdown` then `escape_mentions` — over every
  role, channel, tag and server name and every free-text value (a topic), so a role named
  `**x** [click](https://…)` is shown as written. The website passes nothing: its page draws
  text nodes. A tag's emoji is escaped like any other free text.
- ~~**Not said, on purpose for now:** a forum tag's emoji and its `moderated` flag~~ — reversed
  2026-10-05 on `structure-fold-words` (`59e62d81`): both are said (`tag_emoji`,
  `tag_moderated`), which needed no key once the wording was code.

## D. Mode, and the only thing the feature posts

`structure_backup_mode` = `off` \| `shadow` \| `on`, default **`shadow`**.

| Mode | Capture (daily + on demand) | *Structure changed* notice |
|---|---|---|
| `off` | no; **Take one now** refuses in words | none |
| `shadow` | yes, silently | to `structure_backup_shadow_channel_id` **and nowhere else**, under the rehearsal note; blank posts nothing. ~~to the feature's shadow home (`structure_backup_shadow_channel_id`, then `shadow_channel_id`, then the log channel — `black_bloc/shadow.py`)~~ — reversed 2026-10-05 on `structure-leads` (`c35746f6`) |
| `on` | yes, silently | to `structure_backup_channel_id` **and nowhere else**; blank posts nothing. ~~blank means `staff_channel_id`~~ — reversed 2026-10-05 on `structure-leads` (`c35746f6`) |

Why both fallbacks went: the notice lists every changed role and channel by name, private
ones included, and the staff channel, the rehearsal home and the log channel are all read by
ordinary staff. A blank destination leaves one routine `structure.notice_unsent` row (no
names in it) and moves the notice mark, exactly as `structure_backup_notify` = false does.

~~The notice is posted only when a **daily** snapshot differs from the one before it~~ —
reversed 2026-10-05 on `structure-fixes` (review S2): a snapshot taken by hand between two
daily looks became *the one before it*, and the change it held was never put in front of
anybody else. **Now: the daily look (`tell_staff`) compares the latest snapshot with the last
one a notice covered** — `structure_looks.noticed_id` — whether that look stored a snapshot or
found nothing new. The mark moves when a notice is posted, when there is nothing to say, or
when `structure_backup_notify` is false; it does **not** move when the post failed, so the
next daily look owes it. The first snapshot a server ever takes is its starting mark.

It is one embed: `structure_backup_notice_title`, `structure_backup_notice_text`, then at most
`structure_backup_notice_lines` change lines and `structure_backup_notice_more`.
`AllowedMentions.none()`, and every name escaped (§C). An on-demand snapshot posts nothing;
the person who pressed it is looking at the answer. Comparing and downloading stored
snapshots stays open in `off`.

**What fits, and what is said about the rest** (`change_lines`, `cut`): whole lines are kept
while they fit, with the room for the *…and N more* line reserved first; N is the number of
changes not shown, whether the key or the space cut them; one line longer than the room is
cut at a word and ends `…`. The same function fills the panel's 1024-character field and the
notice's 4096-character description.

## E. Doors

- **Discord:** `/structure` (~~staff~~ leads only since 2026-10-05 — `require_lead` at the
  command, `lead_opened` on every press; still `STAFF_ONLY` in Discord's own command list),
  one ephemeral panel: the latest snapshot's
  time and counts, the last look and how it went, **Take one now**, **What changed** (latest vs
  now), a link button to the page, and the **off / shadow / on picker** every feature panel
  has (`ModePick`, through `cogs.core.set_key`, so it leaves one `settings.set` row). No second
  slash command. `/settings` lists the feature under *What each feature is doing*.
- **Site:** `structure.html` — the snapshots table, **Take one now**, compare any two (or one
  against now), download one as JSON, the feature's settings (wording folded), and its twenty
  most recent log rows, asked for by kind (`/api/actions?kind=structure` and
  `kind=web.structure`, merged newest first) — never fetched wide and filtered in the page.
- **API** (`black_bloc/api/tools/structure.py`, ~~staff only~~ leads only since 2026-10-05,
  one router-level `leads_dependency`; the operator token is refused): `GET /api/structure`,
  `POST /api/structure/snapshots`, `GET /api/structure/compare?old=&new=`,
  `POST /api/structure/snapshots/{id}/download` (a POST because it writes a log row, and a GET on this site never writes).
- The download is `structure.export(row)`: built from `SNAPSHOT_FIELDS` and the field lists in
  §A, never the row. Each download leaves a `structure.downloaded` row. The file's name has
  one home, `structure.export_name`: it is the `Content-Disposition` header and
  `snapshot.filename` in the body, and the page saves under the latter.

## F. Storage — schema **88**

Two tables, appended to `SCHEMA`. ⚠️ **One column was added after the merge and it is NOT a
schema bump:** `structure_looks.noticed_id INTEGER` (nullable; the snapshot the next notice
starts from). It is in the `CREATE TABLE` for a fresh file and is the **first** row of
`ADDED_COLUMNS` in `storage/db.py` for a file that already has the table, so it lands at the
next boot whatever `SCHEMA_VERSION` says.

- `structure_snapshots` — `id`, `guild_id`, `taken_at`, `source` (`daily` \| `manual`),
  `taken_by`, `digest`, `roles`, `categories`, `channels`, `overwrites`, `checked_at`, `checks`,
  `body` (the JSON).
- `structure_looks` — one row per guild: `last_at`, `last_day`, `outcome`
  (`saved` \| `unchanged` \| `failed`), `reason`, `attempts`, `noticed_id`. It is what makes
  *looked, nothing changed* and *failed* visible without a snapshot row, and what stops a
  second daily run. `last_at` / `outcome` / `reason` are the LAST look of either kind;
  `last_day` / `attempts` belong to the daily look alone (`attempts` 0 = today's daily look
  worked, 1–3 = it has failed that many times).

It lives inside the SQLite database, so it rides the existing database backups
(`docs/access/RECOVERY.md`).

## G. Keys — all under `core`

`structure_` would have been a 26th setting group and `/settings`' group select is at Discord's
cap of 25, so every key is added to `CORE_KEYS`. Operational: `structure_backup_mode`,
`_hour`, `_keep`, `_notify`, `_channel_id`, `_shadow_channel_id`, `_notice_lines`,
`_panel_minutes`. Wording: the notice's three lines, the panel's title, labels, lines and
answers, and one `structure_backup_say_<name>` key per sentence and label the change list can
write (`structure_diff.WORDS` is the one home of the defaults). ~~one
`structure_backup_say_<name>` key per sentence~~ — reversed 2026-10-05, owner decision (see
*Decisions* 8): the change list's sentences and field labels are fixed wording in
`structure_diff.WORDS`; **29 keys remain** (8 operational + 21 wording). Channel type names and
permission names are Discord's own identifiers, title-cased, not prose.

**Every wording key has the limit of the place Discord shows it in**
(`settings_store.STRUCTURE_BACKUP_SLOT` / `STRUCTURE_SLOTS`, checked by
`checked_structure_words` beside the placeholder check). Over it, the save is refused with
*That is N characters and <the place> holds L on Discord…*; and the render cuts to the same
number (`structure_backup.said`), so a value stored before the limits cannot break a card.

| Slot | Limit | Keys |
|---|---|---|
| a button's label | **80** | `_take_label`, `_changes_label` (also a field name), `_site_label` |
| a picker's hint | **150** | `_mode_label` (also a field name) |
| a heading | **256** | `_notice_title`, `_panel_title`, `_latest_label`, `_look_label`, `_panel_footer` |
| one block of a card | **1024** | every other line (~~and every `_say_` key~~ — no longer keys) |
| a card's main text | **4096** | `_saved_said`, `_unchanged_said`, `_failed_said`, `_off_said` |

An embed also holds 6000 characters in all: `within` shortens the panel's main text, with the
timed-out footer's room kept. `_panel_footer` is held to 256 rather than Discord's 2048 so
that sum can always be met. No key was added or removed for the limits (860 then); the fold
removed 46 — **854** registry keys measured on `structure-fold-words`, 29 of them this feature's.

## H. Log kinds — head `structure`, filed under `core`

Routine: `structure.captured`, `structure.unchanged`, `structure.pruned`,
`structure.notice_posted`, `structure.downloaded`. Important by suffix:
`structure.capture_failed`, `structure.notice_failed`. The website's capture and download carry
the `web.` head through `kind_via`. Success, *looked and nothing changed*, and failure are three
different kinds (checklist 2).

`structure.notice_unsent` (routine, added 2026-10-05) is the daily look finding changes with
no channel to send them to; it carries `mode`, `key`, `snapshot_id`, `since_id`, `changes`
and a `reason` sentence.

**A notice posted in `shadow` is `structure.would_notice`; `structure.notice_posted` is `on`
only** (review N9). It needs no `logkinds.py` entry: a `.would_` kind is routine by rule, and
`tests/test_logkinds.py` refuses one that is listed as well. A notice that could not be posted
is `structure.notice_failed` in either mode. Both carry `since_id` and `changes`.

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
3. **Three attempts a day** for a failed daily look (§B), four hours apart since the review
   fixes. One would lose a day to a blip; a retry every tick would write 144 failure rows.
4. ~~**Blank `structure_backup_channel_id` means the staff channel** in `on` (§D).~~ —
   **reversed by the owner's decision 2026-10-05** (`structure-leads`, `c35746f6`): blank
   means no notice. The staff channel is read by people who may not see the structure.
5. **`structure_backup_notify`** is the switch that makes the notice optional (§D).
6. **Keys are `core`** (§G), and there is **no `structure` feature** in `logkinds.FEATURES` —
   a 23rd feature would add a log-level key and a 26th setting group.
7. **`/structure` is not hidden when the mode is `off`.** Stored snapshots stay readable and
   comparable in `off`; hiding the command would hide them.
8. ~~**Every change-list sentence is a settings key** (§G), per the every-word-editable rule.
   It is ~45 keys; the alternative was prose only the code knows.~~ — **reversed by the owner
   2026-10-05** (branch `structure-fold-words`, `59e62d81`). Asked whether to keep the 46
   `structure_backup_say_*` keys editable or fold them into code, he answered **"B"**: fold the
   46 change sentences into code; titles, button labels and the notice heading stay editable.
   Why it flipped: 46 of the feature's 75 keys were sentence fragments nobody is likely to
   reword, none of them reachable in `/settings` without a search, and each new sayable
   difference cost a key (which is what left N1's two differences unsaid). This is a decided
   exception to the every-word-editable rule for the change list only.
9. **Member overwrites are kept, by id only** (§A).
10. **Downloads are logged** (`structure.downloaded`) — it is a copy of the permission layout
    leaving the bot.
11. **Guild fields are exactly the brief's five** plus `id`; AFK, locale and content-filter
    settings were left out rather than guessed at.
12. **`now` compares are not stored and not logged.**

## Review fixes 2026-10-05

Branch `structure-fixes` off `main` `0d159774`; code and tests in `d53a1117`. An independent
review of the merged feature; each row is a finding, what changed, and the test that pins it.
Every finding's first-named test was **seen failing first** — the cog's, the API's, the
schema's and the settings panel's against a throwaway checkout of `0d159774` with the new test
files copied in (45, 3 and 5 failures), the four module files' in this tree before the fix was
written (19). A test marked ° passed before the fix as well: it guards behaviour that must
not move. Tests live in `tests/cogs/moderation/test_structure_backup.py` unless a file is
named.

| # | Finding | What changed | Pinned by |
|---|---|---|---|
| S2 | A snapshot taken by hand swallowed the *structure changed* notice | §D: the daily look compares against `structure_looks.noticed_id`; pruning protects that snapshot | `test_a_snapshot_taken_by_hand_never_hides_a_change_from_the_daily_notice`, `test_a_notice_covers_every_snapshot_since_the_last_one_it_covered`, `test_a_notice_that_failed_is_owed_and_the_next_daily_look_pays_it`, `test_keeping_one_snapshot_still_keeps_the_one_the_next_notice_starts_from`, `test_the_first_snapshot_ever_taken_by_hand_is_where_the_first_notice_starts`; `tests/test_structure_store.py::test_the_snapshot_a_notice_last_covered_is_remembered_across_looks`, `::test_pruning_never_takes_the_snapshot_the_next_notice_starts_from`; `tests/storage/test_db.py::test_a_looks_table_from_before_the_notice_mark_gains_it_and_keeps_its_row` |
| S3 | Long lists were cut silently and the *…and N more* line went first | §D: `change_lines` reserves that line's room, counts what was left off, cuts one long line at a word | `test_forty_moves_keep_the_line_that_counts_the_rest_on_the_panel`, `test_thirty_long_permission_lines_never_push_out_the_count_of_the_rest`, `test_one_line_longer_than_the_field_is_cut_at_a_word_with_an_ellipsis`, `test_a_line_longer_than_the_whole_notice_is_cut_and_nothing_is_miscounted`, `test_cutting_keeps_whole_words_and_never_runs_past_the_limit` |
| S4 | The no-write test caught one spelling | `write_paths` in the test file reads every attribute, name, reflection call and import: any `.http`, any `Route`, `getattr`/`setattr`/`delattr`/`hasattr` with a computed name or a write name, any bare reference to a write-named attribute, any import outside `ALLOWED_IMPORTS`. The fakes (`Strict`) hand back a `Refuses` for anything not defined on them — calling it raises AND is recorded, and an autouse fixture fails the test if anything was recorded, because `take_snapshot` swallows exceptions. The cog's lock no longer uses `getattr`/`setattr` with a computed name | `test_no_structure_module_can_write_a_role_a_channel_or_a_permission` (failed on `0d159774`: the lock's computed `getattr`/`setattr`), `test_the_guard_trips_on_every_spelling_of_a_write`° (27 spellings — the guard lives in the test file, so this never ran against the old one; the old check run by hand over the same 27 caught **4**), `test_the_guard_lets_the_reads_this_feature_makes_through`°, `test_the_fakes_refuse_every_call_they_were_not_told_about`° |
| S5 | No mode control in Discord; the feature missing from `/settings`; `reachable_on_the_panel` ignored the 25-option cap | §E: `ModePick` on `/structure`; a `FeatureMode` row in `settings_panel.EXTRA_MODES`; `reachable_on_the_panel` is true only when the group's picker lists the key or the group offers a search that brings it up | `test_the_panel_carries_the_mode_control_and_it_changes_the_mode`, `test_the_mode_control_brings_the_feature_back_from_off`, `test_the_mode_control_is_refused_to_someone_who_is_not_staff`, `test_settings_lists_structure_backup_with_every_other_feature_mode`, `test_reachable_on_the_panel_counts_the_picker_cap_and_the_search`; `tests/test_settings_panel.py::test_the_mode_block_is_the_hide_table_plus_exactly_four_hand_added_rows` |
| S6 | A label or title over Discord's limit bricked the panel or the notice | §G: a limit per key at save, the same cut at render, `within` for the 6000 total | `test_wording_longer_than_discord_holds_is_refused_at_save_in_words` (13 keys), `test_every_structure_wording_key_has_a_limit_its_own_default_fits`, `test_wording_stored_before_the_limits_cannot_break_the_panel`, `test_wording_stored_before_the_limits_cannot_break_the_notice` |
| N1 | A snapshot could differ with an empty change list | §B: one rule, `structure_store.same`; §C: an overwrite is keyed by kind too | `tests/test_structure_store.py::test_a_new_row_is_stored_exactly_when_the_change_list_has_something_to_say` (5 cases, 4 failing first), `::test_a_difference_nothing_can_say_refreshes_the_copy_already_held`; `tests/test_structure_diff.py::test_an_overwrite_whose_target_changed_kind_is_a_change_that_is_said` |
| N2 | A failed look by hand re-armed the daily look | `record_look` is an upsert that leaves `last_day`/`attempts` alone without a `day`; `daily_due` reads `attempts`, not `outcome` | `tests/test_structure_store.py::test_a_failed_look_by_hand_never_re_arms_a_daily_look_that_worked`, `::test_a_look_by_hand_that_works_never_spends_a_failed_daily_looks_tries`; `test_a_look_by_hand_that_fails_never_brings_a_second_daily_look` |
| N3 | Two channels with one name were indistinguishable | §C: `Names.label` | `tests/test_structure_diff.py::test_two_channels_with_one_name_are_told_apart_by_their_category`, `::test_two_channels_with_one_name_in_one_place_fall_back_to_their_ids`, `::test_a_name_that_is_unique_is_left_as_it_is`° |
| N4 | Names were not escaped in the staff embed | §C: `escape=` | `test_a_name_written_as_markdown_is_shown_as_written_on_the_panel`, `test_a_name_written_as_markdown_is_shown_as_written_in_the_notice`; `tests/test_structure_diff.py::test_names_and_free_text_are_escaped_when_the_reader_is_discord` |
| N5 | A capture with zero channels replaced the only good snapshot | §B: `NO_CHANNELS` | `test_a_capture_with_no_channels_never_replaces_the_only_good_snapshot`; `tests/test_structure_capture.py::test_a_capture_with_no_channels_is_refused_rather_than_stored` |
| N6 | Three retries spent in thirty minutes | §B: `RETRY_GAP_MINUTES` = 240, `retry_gap` — module constants, no key | `test_a_failed_daily_look_is_tried_three_times_spread_across_the_day`, `test_a_late_hour_still_fits_its_three_tries_into_the_day`; `tests/test_structure_store.py::test_a_failed_daily_look_waits_out_the_gap_before_it_is_tried_again` |
| N7 | An unavailable server was skipped with no row and no log | §B: `run_daily` no longer returns early for it | `test_a_daily_look_at_an_unavailable_server_leaves_a_row_that_says_why` |
| N8 | The fetches had no timeout and held a bot-wide lock | §B: `asyncio.wait_for(…, FETCH_SECONDS)`; `UNREACHABLE` for a timeout or an `OSError` | `test_discord_not_answering_is_a_timeout_in_words_and_the_lock_is_let_go`, `test_a_network_failure_is_never_worded_as_a_permission_problem` |
| N9 | Shadow and on shared `structure.notice_posted` | §H | `test_in_shadow_the_notice_goes_to_the_features_own_rehearsal_home`, `test_on_the_notice_goes_to_its_channel_with_no_rehearsal_line`° |
| N10 | `said()` / `sentence()` caught three exception types | Both catch `Exception`, log, and fall back (checklist 17) | `test_a_template_that_breaks_in_any_way_falls_back_to_the_shipped_wording` in the cog's file (5 templates, 2 failing first) and in `tests/test_structure_diff.py` |
| N11 | This page's header said NOT merged and quoted 300 routes | The header and *Gate* | — |
| N12 | An overwrite's kind was guessed from the role list | `structure_capture.target_kind`: a `discord.Role` / `discord.Member` / `discord.User`, or a `discord.Object`'s `type`; the role list only for a target that carries no type at all | `tests/test_structure_capture.py::test_an_overwrites_kind_is_discords_own_and_not_a_guess_from_the_role_list` |
| N13 | The download's filename had two homes | §E | `tests/test_structure.py::test_a_download_is_built_from_the_field_lists_never_from_the_row`; `tests/api/tools/test_structure.py::test_the_page_takes_the_download_name_from_the_api_and_builds_none_of_its_own` |
| N14 | The page asked for 20 rows and then filtered them | §E | `tests/api/tools/test_structure.py::test_the_page_asks_the_api_for_structure_rows_and_filters_none_itself`, `::test_the_two_kinds_the_page_asks_for_bring_back_only_structure_rows`° |

**~~Open, for the owner — not changed here.~~ Answered 2026-10-05: the 46 `_say_` keys were
folded into code (see the next section; the figures below are as measured before that).**
`reachable_on_the_panel` is truthful now and no
guard test fails, because every group over the cap has a search. Measured 2026-10-05: of the
**860** keys, **527** are past the first 25 of their group and are reached in `/settings` only
by typing a search — and **all 75** structure keys are among them (`core` holds 102). The 46
`_say_` wording keys were left exactly as they are.

**Decisions the fixes made beyond the brief.** (1) The first snapshot a server ever takes is
the first notice's starting mark, so the S2 scenario also holds when no daily look has run
yet. (2) A notice whose post failed is owed, and tried again by every later daily look.
(3) The protected snapshot can make a server hold `keep` + 1. (4) `_panel_footer` is limited
to 256, not 2048 (§G). (5) An unsayable difference refreshes the held copy in place rather
than being dropped (§B). (6) Escaping is `discord.utils.escape_markdown` + `escape_mentions`,
not `block_look.plain`, which doubles the backslash in front of a `[` — this server's role
names are full of them. (7) `ModePick`'s options read `off` / `shadow` / `on`, the setting's
own values, and its hint is `structure_backup_mode_label`: no new wording, no new key.
(8) Two `KEY_HELP` sentences (`_keep`, `_notify`) were reworded to match, with their mock rows.

## Wording folded into code 2026-10-05

Branch `structure-fold-words` off `main` `c16deab1`; code and tests in `59e62d81`.

- **Removed (46):** every `structure_backup_say_*` key — the 31 sentences and fragments
  (`server_changed` … `no`) and the 15 `f_*` field labels — from `settings_store` (registry,
  `CORE_KEYS`, text checks, limits, help), the mock's rows and core-key list, `labels.js` and
  `contract.json`. None was a heading or a button.
- **Kept (29), untouched:** `structure_backup_mode`, `_hour`, `_keep`, `_notify`,
  `_channel_id`, `_shadow_channel_id`, `_notice_lines`, `_panel_minutes`; `_notice_title`,
  `_notice_text`, `_notice_more`, `_panel_title`, `_panel_footer`, `_mode_label`,
  `_latest_label`, `_latest_line`, `_none_yet`, `_look_label`, `_look_saved`,
  `_look_unchanged`, `_look_failed`, `_take_label`, `_changes_label`, `_site_label`,
  `_saved_said`, `_unchanged_said`, `_failed_said`, `_off_said`, `_no_changes_said`.
- **A value already stored for a removed key** is not migrated and cannot crash: the store's
  `load` skips any key outside `KEY_TYPES` and logs `settings ignored: <keys>` once at boot —
  the path a retired key has always taken (`youtube_mode`). Pinned by
  `test_a_change_sentence_stored_before_they_left_the_settings_is_ignored_at_boot`.
- **`structure_diff`**: `WORDS` is `name → sentence`; `sentence(name, **fields)` has no
  fallback because there is no staff template to break; `changes(old, new, *, escape=None)`.
  `cogs…structure_backup.say_words` and `settings_store.STRUCTURE_SAY_KEYS` are gone.
- **N1 finished**: `tag_emoji`, `tag_moderated` (§C) and the order-based digest (§B).
  `structure.py` now owns `by_id`, `top_down`, `bucket`, `in_order`, `VOICE_TYPES` (one home;
  the change list imports them) and `placed`. Pinned in `tests/test_structure_diff.py` by
  `test_every_field_a_snapshot_holds_moves_the_digest_and_has_something_to_say` (31 fields, read
  off the five field lists), `test_the_field_table_covers_every_field_list_so_a_new_field_needs_a_sentence`,
  `test_positions_renumbered_with_the_order_kept_are_the_same_digest_and_say_nothing`,
  `test_an_order_that_changed_moves_the_digest_and_is_said`, and the four tag tests; in
  `tests/test_structure_store.py` by
  `test_a_forum_tags_emoji_or_moderated_flag_changing_is_a_new_snapshot` and
  `test_positions_renumbered_refresh_the_copy_already_held`.
- ⚠️ **The agreement is proved for what a capture can produce**, one field at a time. A
  hand-made body that differs only in a way the readers coerce away (a permission value of
  `null` against `0`) would move the digest and say nothing; `structure_capture` writes
  integers, so no capture produces one.
- **Reach in Discord `/settings`, measured 2026-10-05:** `core` holds **96** keys (95 + the log
  level); **0 of the 29** structure keys are in its first 25, so none is reachable without
  typing a search (the first sits at place 28). Searching `structure_backup` finds 29 and
  lists 25; all 29 pass `reachable_on_the_panel`. Registry-wide, **521 of 854** keys are past
  the first 25 of their group (527 of 860 before).
- **Pinned counts moved:** `len(KEY_TYPES)` 900 → **854** and `len(CORE_KEYS)` 141 → **95**
  (`tests/test_settings_store.py`); the feature's own keys 75 → **29** and its text keys
  67 → **21** (`tests/cogs/moderation/test_structure_backup.py`); `contract.json` core keys
  141 → **95**. Nothing in `tests/test_settings_panel.py` pins a count this moved.
- **Gate, measured 2026-10-05 at `59e62d81`:** `python -m pytest tests -q -p no:cacheprovider
  -n 8` **11323 passed, 3 skipped** (11327 on `main` `c16deab1`); `python -m ruff check .`
  clean; `node site/mock/check.mjs` **ok — 25 pages, 312 routes, 95 core settings, all keys
  present** (port 8796); the thirteen `site/mock/*.test.mjs` files ok. The Structure page was
  opened in a browser against the mock: Snapshots, Compare, Settings (28: 7 + 21 under
  *Wording*) and Logs drew, no `_say_` key on the page, no console error.
- **NOT verified:** nothing has met Discord; the mock's change list is still its short
  JavaScript stand-in and does not say tag changes; no button on the page was pressed this
  time; `docs/info/code-notes.md` was not re-keyed; `ruff format --check` was not run
  repo-wide (`structure_diff.py` was formatted whole, it was not format-clean before).

## Leads only 2026-10-05

Branch `structure-leads` off `main` `6e5136c5`; code and tests in `c35746f6`.

**The owner's decision.** A snapshot holds the name, topic and permission layout of every
channel, including ones an ordinary staff member cannot open in Discord. Asked whether all
staff may see that, the owner answered **"b"**: the Structure page and its notice are Leads
only — and added, verbatim: *"im the exception though or i cant verify anything"*.

**The rule — one function, `black_bloc/structure.py:may_see(store, guild, person)`.** True for
the server **owner** (`guild.owner_id`, by id, so it holds with no role and when the owner is
not in the member cache), for anyone whose `guild_permissions.administrator` is `True`, and
for a holder of the role in **`structure_backup_role_id`** (type `role`, default blank). Blank
means owner and administrators only. Manage Server alone is staff, not a lead.

**It only narrows.** Every door asks the staff gate first and this rule second, so a holder of
the role who is not staff is still refused as *not staff*; nobody who was refused before gets
in now.

| Door | Where the rule is asked |
|---|---|
| `GET /api/structure`, `POST …/snapshots`, `GET …/compare` (stored and `new=now`), `POST …/snapshots/{id}/download` | `api/tools/structure.py:leads_dependency`, the router's one dependency → `api/auth.py:sees_structure` → `may_see`. 403 `structure_leads_only` with `structure.LEADS_ONLY` |
| The operator read token on those routes | refused first, in words (`structure.OPERATOR_REFUSED`, 403 `structure_no_operator`), **before** the token is checked — so a right and a wrong token read the same, no `web.operator.read` row is written, and no live fetch is made. It was able to `GET` the list and the compare, `new=now` included |
| `/structure` | `cogs/moderation/structure_backup.py:require_lead` (staff, then the rule) |
| **Take one now**, **What changed**, the mode picker | `lead_opened` as the first statement of each `callback` — staff and the rule re-asked on every press, before the defer |
| The rail entry | `/api/auth/me` carries `structure` (`sees_structure`); `shell.js` draws the entry hidden and `paintNavFor` shows it only when that is `true`. The command palette lists what the rail shows |
| `structure.html` opened directly | the API's refusal reaches `app.js:handle` → *Structure is for the server's leads* and the sentence: what it is, who it is for, how to get in. No retry button, no empty page |
| Overview's feature row, `/settings` ▸ *What each feature is doing*, `/api/status` | unchanged: ordinary staff see the feature and its mode, and may change the mode. The row carried no snapshot data. Overview no longer links the row to a page the rail does not offer (`page-overview.js:reachable`) |
| `structure_backup_role_id`, `_channel_id`, `_shadow_channel_id` (`structure.LEADS_KEYS`) | `cogs/core.py:leads_only` inside `set_key` and `clear_key` — the one writer behind both `/settings` and `PUT`/`DELETE /api/settings/{key}`. Without it any staff member could name their own role or point the notice at a channel they read |
| The notice | §D: only its own key's channel |
| Logs / Audit | not gated — see below |

**What `structure.*` log rows hold, and why they stay with staff.** Read off the code and
pinned by `test_no_structure_log_row_carries_a_role_or_channel_name_or_a_change_list`: counts
(`roles`, `categories`, `channels`, `overwrites`, `changes`, `removed`), snapshot ids
(`snapshot_id`, `previous_id`, `since_id`), `source`, `via`, `mode`, `key`, the notice's own
`channel_id` / `aimed_at`, and a `reason` sentence (ours, or Discord's own error text). **No
role name, no channel name, no topic, no change list.** So the rows are left visible to staff
and the test fails if a name or a list is ever added to one.

**Keys: +4, 854 → 858** (`CORE_KEYS` 95 → 99; this feature's 29 → 33, its text keys 21 → 24).
`structure_backup_role_id`; and three words for the panel's new **Notice** field, which states
where the notice goes: `structure_backup_notice_label`, `_notice_nowhere` (`{setting}`),
`_notice_off`. The page says the same with a badge (`notice → #channel · Category`, *notice
goes nowhere*, *notice off*) read from the two keys. `KEY_HELP` for `_mode`, `_notify`,
`_channel_id` and `_shadow_channel_id` was reworded to say blank means no notice.

**Decisions this build made beyond the brief.**

1. **The three keys that decide who sees it are leads-only to change** (table above). Not in
   the brief; the gate is decorative without it.
2. **A notice with nowhere to go is not owed.** The mark moves, as it does when
   `structure_backup_notify` is false; otherwise the default configuration (shadow, both keys
   blank) would log a row every day for ever. Changes are never lost — the page compares any two.
3. **The operator is refused before its token is read** (table above).
4. **The owner is matched by id**, so a session whose member is not cached still gets in if it
   is the owner's; an administrator or role holder who is not cached is refused until they are.
5. **`administrator` must be exactly `True`** — a fake or a truthy stand-in does not pass.
6. **In shadow with the real channel blank, the rehearsal line ends with the
   `_notice_nowhere` sentence** rather than an empty *this is where it would go:*.
7. **The refusal sentences are constants in `structure.py`**, like every other refusal here
   (`staff_refusal`, `NOT_STAFF`); they are not settings keys.
8. **The mock gained `?as=mod`** — staff who is not a lead; `staff` stays a lead.
9. **The mode stays with staff**: turning the feature off or on shows nobody anything.

**Tests.** `tests/test_structure.py` (the rule), `tests/cogs/moderation/test_structure_backup.py`
(the command, every control, losing the role mid-panel, the AST walk
`test_every_door_in_the_cog_is_behind_the_one_gate`, the notice, the log rows),
`tests/api/tools/test_structure.py` (every route read off the app's own schema, the operator,
the keys, the rail), `tests/cogs/test_core.py` (the writer), `tests/api/test_auth.py` (`/me`).
The new test files were run against a throwaway checkout of `6e5136c5`: **46 failed** there,
308 passed (the API file with its five new imports stubbed, since they do not exist on main).
The ones that passed on main guard behaviour that must not move (the owner and an
administrator open the panel, a member and a visitor are refused, the other keys stay with
staff). Two tests were **removed** because they pinned the fallbacks:
`test_in_shadow_with_no_home_of_its_own_the_notice_follows_the_rehearsal_home` and
`test_on_with_no_channel_set_the_notice_goes_to_the_staff_channel`. The no-write guard test is
untouched and passes.

**Gate, measured 2026-10-05 on `structure-leads`:** `python -m pytest tests -q -p
no:cacheprovider -n 8` **11377 passed, 3 skipped** (11323 passed, 3 skipped on `main`
`6e5136c5`, run in a throwaway checkout); `python -m ruff check .` clean; `node
site/mock/check.mjs` **ok — 25 pages, 312 routes, 99 core settings, all keys present** (port
8771); the thirteen `site/mock/*.test.mjs` files ok. In a browser against the mock:
`structure.html?as=staff` drew Snapshots (2), Compare, Settings (32, the role key among them),
Wording (24) and Logs, the badge *notice goes nowhere*, and the rail entry;
`structure.html?as=mod` drew the gate row *Structure is for the server's leads* with the
sentence, no button, an empty dashboard and no Structure entry in the rail; `index.html?as=mod`
drew the Structure backup feature row with its mode and no link. No console error.

**NOT verified:** nothing has met Discord — `/structure` was never opened in a client by an
owner, an administrator, a role holder or a mod; `guild.owner_id` and
`guild_permissions.administrator` are discord.py's documented attributes, read through fakes.
The live site was not touched. `docs/info/code-notes.md` was not re-keyed.
`docs/access/operator-read.md` does not mention structure and was not edited, so the refusal
is recorded only here. ⚠️ **On deploy:** production is in `shadow` with `structure_backup_shadow_channel_id`
blank unless somebody set it, so the notice will go nowhere until a lead sets it.

## Gate

Measured 2026-10-05 on branch `structure-fixes` at `d53a1117`, before its docs commit:
`python -m pytest tests -q -p no:cacheprovider -n 8` **11011 passed, 3 skipped** (10911 on
`main` `0d159774`); `python -m ruff check .` clean; `node site/mock/check.mjs` **ok — 24 pages,
305 routes, 101 core settings, all keys present** (on port 8794); the twelve
`site/mock/*.test.mjs` files ok. By import: `len(KEY_TYPES)` **860**, `SCHEMA_VERSION` **88**.

Before that, the build's own gate — measured 2026-10-05 on branch `structure-backup`, before its last docs commit:
`python -m pytest tests -q -p no:cacheprovider -n 8` **10813 passed, 3 skipped** (10618 on `main`);
`python -m ruff check .` clean; `node site/mock/check.mjs` **ok — 24 pages, 300 routes, 101 core
settings, all keys present**; the eleven `site/mock/*.test.mjs` files ok. By import:
`len(KEY_TYPES)` **854** (779 + 75), `len(CORE_KEYS)` **101** (26 + 75), `SCHEMA_VERSION` **88**,
`len(COGS)` **27**. The Structure page was opened in a browser against the local mock: the table,
Compare, *What changed since*, *Take one now* and the Settings section drew and worked; the
console showed no error.

## What was NOT verified

- **Nothing has met Discord.** No real guild was fetched, no notice posted, `/structure` never
  opened in a client, the panel's buttons never pressed outside the fakes.
- Whether `guild.fetch_channels()` returns channels the bot cannot view, and their overwrites.
- The schema change has not run on the live database (two `CREATE TABLE IF NOT EXISTS`).
- The mock's change list is a short JavaScript stand-in (roles, channels, overwrites); the real
  list comes from `structure_diff.py` and was only seen through the tests.
- Download was not pressed in the browser (the route was exercised by the contract check).
- `docs/info/code-notes.md` was not re-keyed and no guide was added to `guides_seed.json`.
- `ruff format --check` was not run.
- **The review fixes (2026-10-05):** the Structure page was not opened in a browser after its
  two changes — `node --check` passed, and the two requests it now makes were made by hand
  against the mock; the mode picker was never pressed in a Discord client; the 30-second
  timeout was exercised at 0.05 seconds against a fake that never answers, not against
  Discord; `structure_looks.noticed_id` has not been added to the live database; and whether
  `fetch_channels()` hands back typed `Object` targets for overwrites on uncached members is
  discord.py 2.7.1's source read, not a capture.
- ~~Stale after these fixes and NOT edited: the structure rows in `docs/info/README.md`,
  `docs/info/architecture.md` and `docs/access/RECOVERY.md` still say *not merged*~~ —
  corrected 2026-10-05 on `structure-fold-words`.
