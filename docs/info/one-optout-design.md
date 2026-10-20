# One opt-out: one per-person table every announcer reads

> **Audience:** the conductor (merge + deploy), reviewers, and later sessions. **Status:** TRACKED ·
> 🔨 **BUILT on branch `one-optout`** (off `main` `fb664e86`, v244), **NOT merged, NOT deployed**.
> **Last verified: 2026-10-20 03:2x Phoenix**. Measured on the branch: `pytest -n auto` all green
> (the exact count is in the merge report), `ruff check .` clean, `node site/mock/check.mjs` ok against a
> FRESH mock (port 8841, nonce `oneopt-1`: 28 pages, 375 routes, 353 core settings), registry
> `len(KEY_TYPES)` **1233** (was 1222), the mock's `/api/settings` 1233 keys, schema **98** (was 97).
> Live values were read through `scripts/read.ps1` (operator token, 2026-10-20 03:10).
> ⚠️ **NOT verified:** anything in Discord (the `/settings` confirm button and the log-channel
> notice were exercised only with test fakes); the migration against the live database (it ran
> against a fixture that mirrors the live API reads); phone width.

Owner decisions 2026-10-19, sheet items **i4, i5a, i5b, i5c, i8, i9a, i9b** of
[`switch-audit-2026-10-19.md`](switch-audit-2026-10-19.md) §5. **i10 was a No**: staff opting a member
back in on `/golive` ▸ Streamers still needs no reason and sends no DM. It is only logged now.
Build 5 of the sheet. Builds 1–4 are LIVE (v241–v244).

## 1. The kinds

`person_optouts(guild_id, user_id, kind, by, reason, at)`, primary key `(guild_id, user_id, kind)`.
`black_bloc/optouts.py` is the only reader and writer.

| Kind | Means | Copied from (old store, still written one release) | Read by |
|---|---|---|---|
| `announce` | don't announce my streams anywhere | `golive_optout` (no guild column) | member go-live, the history sweep, spotlight (and YouTube channel rows through it), marathon public, host and runner posts and their @-mentions, the PB feed |
| `birthday` | don't wish me | `birthdays.opted_in = 0` | the birthday sweep and the posted-today path |
| `chat_memory` | don't remember me, whatever the model | `chat_memory_optout` while the model is `optout` | `chat_memory.remembers` and the write-up's race guard |
| `chat_memory_in` | remember me (only matters under `optin`) | `chat_memory_optout` while the model is `optin` | the same; never shown in the roll-up |
| `pbs` | don't post my personal bests | `pb_matches.state = opted_out` | the roll-up (the feed's own state still stops looks) |
| `streamer_list` | take me off the streamer list | `streamers.listed = 0` with `hidden_by` set | the roll-up (the list still reads `listed`, which also carries stale prunes) |

There is no `marathon` kind. In marathons, the person's own choice is wearing a role of
`marathon_optout_role_ids`. The roll-up reads that as a role filter, the same way it reads the
go-live ignore role.

## 2. Gate order per announcer

| Announcer | Before (v244) | After |
|---|---|---|
| Member go-live (Twitch presence, YouTube link) | mode, then `golive_optout`, then require/ignore role, then cooldown | mode, then **`announce`**, then require/ignore role, then cooldown (unchanged order; the ignore role is now also a roll-up filter) |
| Spotlight (Twitch and YouTube channel rows) | channel `announce` flag | channel `announce` flag, then **`announce` of the member linked to the login or the YouTube channel** |
| Marathon public, host and reminder posts, @-mentions | run answer, then per-marathon opt-out, then the Runner/Host switch | **`announce`** first, then run answer, per-marathon opt-out, switch. A run answer of `in` no longer beats it |
| Marathon runner posts (tracking thread) | every BaF run | a run whose BaF people are **all** `announce`-out gets no new post; one already up is left |
| Marathon People **Spotlight…** offer | any runner with a login and no row | not offered for an `announce`-out person (Discord card and site) |
| PB feed | `pb_matches.state` | state, then **`announce`**: the claimed run is settled `dry` (`announce_opted_out`) |
| Birthday wishes | `opted_in` column | **`birthday`** kind |

## 3. The migration

`black_bloc/one_optout.py`, run from `setup_hook` after `shadow_one_meaning`, before every cog.
It copies every old row missing from the table (`INSERT OR IGNORE`, reason `migrated`), then
writes one `optouts.migrated` row per guild with counts per kind. A second boot finds nothing to
copy and writes nothing. The check is by state, so rows written during a rollback window are still
copied on the way forward. `golive_optout` rows go to `dev_guild_id`, else to the one guild seen.
With several guilds and none configured, they are not copied, and a note says why.

**Dry run against the live mirror** (`tests/test_one_optout.py::test_the_dry_run_against_the_live_rows_finds_nothing_to_copy`):
`[]`. Live 2026-10-20 03:10 has no rows to copy:

| Kind | Live count |
|---|---|
| announce | 0 (`/api/golive/optouts` empty) |
| birthday | 0 (42 birthdays, none opted out) |
| chat_memory | 0 (consent `optout`, roll-up shows none) |
| pbs | 0 (`pb_feed_mode` off, roll-up shows none) |
| streamer_list | 0 (48 streamers, all listed) |

The 32-person fixture covers every combination of the five old stores. It copies 16 rows per kind
and logs `{"announce": 16, "birthday": 16, "chat_memory": 16, "pbs": 16, "streamer_list": 16}`.

## 4. The roll-up (Members ▸ Opted out)

| Source | Before | After |
|---|---|---|
| marathon role holders | role less overrides | same (`marathon_role`) |
| marathon override | a chip inside Opted out | **its own Counted in list** (`counted_in`: name, word, reason or *no reason given*, by, when, Undo) |
| per-marathon posts | each marathon's list | same, the third layer of i5c (not per-person, so it is not in the table) |
| go-live | `golive_optout` | `announce` kind |
| go-live ignore role | missing | **added** as a role filter (`golive_ignore_role`, *ignored by role (Role)*) |
| chat memory | old table, meaning flipped with the model | `chat_memory` kind, one meaning |
| birthdays | column | `birthday` kind |
| PBs | state | `pbs` kind |
| streamer list hides | missing | **added** (`streamer_list`) |

These stay out because they are not per-person:

- **Spotlight channel opt-outs** are on the channel row (`spotlight_channels.announce`), shown on the Go-live page.
- **Marathon-opted-out channels** (ESA seed) stay in the roll-up's separate `channels` list.
- **Honeypot and automod exempt roles** are moderation exemptions, set on those pages.

## 5. The consent change (i9b)

Changing `chat_memory_consent` anywhere (site, `/settings`, a reset) is refused with
`409 confirm_needed`, and the bot's sentence gives the count: *N members would stop/start being
remembered*. On the site this is an *Are you sure?* dialog. In `/settings` it is the card with
**Yes, change it** and **Leave it as it is**. When the flip to `optin` is confirmed, everyone it
moves gets a `chat_memory` row with reason `consent:optin`. Flipping back lifts only those rows.
The count is on the `settings.set` row's `flip` detail.

## 6. What changes the moment it ships

- **Nobody is newly announced.** `tests/test_one_optout.py::test_nobody_silent_before_the_migration_is_announced_after_it`
  checks every combination, and `tests/test_marathon_announce.py::test_nobody_silent_before_the_one_opt_out_is_announced_after_it`
  checks every truth-table row.
- **Newly silent, by count:** spotlight 0, marathon posts 0, runner posts 0, PB feed 0. Live has
  no go-live opt-outs, so nobody changes today. From now on, a member's own **Stop announcing my
  streams** also silences spotlight, marathons and the PB feed.
- **Members:** nothing to do. They keep the same buttons, which now reach further.
- **Staff:**
  - **Count as BaF anyway** asks for a reason.
  - A member who takes the opt-out role after being counted in drops out of the override, and the log channel says so.
  - Spotlighting an opted-out member's channel says it will stay silent.
  - The `chat_memory_consent` change asks with a count first.
  - Opting a member back in on `/golive` ▸ Streamers writes `optouts.overridden` instead of `golive.optin`.
- Registry 1222 → **1233**: `golive_ignored_role_word`, `golive_spotlight_opted_out_said`,
  `chat_memory_consent_confirm_out_said`, `…_in_said`, `…_button`, `marathon_baf_override_reason_title`,
  `…_reason_label`, `…_no_reason_word`, `…_needs_reason_said`, `marathon_override_cleared_by_optout_said`,
  `marathon_announce_why_optout`. Go-live page keys 87 → 89.

## 7. Rollback

Redeploy v244 (`0d4597ae`) and restore the pre-deploy snapshot if needed. Schema 98 only adds a
table and one nullable column, so v244 runs on it. The old stores were written the whole time, so
v244 reads the same people.

Exceptions:
- A `chat_memory_consent` flip made after the deploy would read the old table with its old,
  flipped meaning.
- Override reasons are not shown by v244.

## 8. Deviations

- **Spotlight add on an opted-out member is not an override.** The channel is added, but its
  announcements stay silent and staff are told why. The logged override is the existing `/golive` ▸
  Streamers opt-back-in (i10: no reason, no DM). Adding a reason box to every spotlight add (panel,
  site, People card) is unbuilt.
- **The staff opt-back-in writes `optouts.overridden` instead of `golive.optin`**, not as well as it
  (checklist 34). The same applies to a staff PB repost of an opted-out member, which carries
  `overrides_optout` in its details.
- **`chat_memory_in`** is an in-kind in a table named for opt-outs. The `optin` model needs an
  explicit yes.
- **The per-marathon "not this one" stays in the roll-up**, though it is per marathon, not per
  person. It is i5c's third layer.
- **i5a is done in the member-update handler**, not where `not_ours` is computed. A role added
  while the bot is down is not seen until the next role change.
- **No consent-flipped log kind.** The count is on the `settings.set` row.
- **People who join after a flip to `optin`** are out by the model but have no row, so the roll-up
  does not list them.
