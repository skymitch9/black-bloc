# Phase 1 design — settings store, action log, role menus (F16)

> ⚠️ **SUPERSEDED IN PART, 2026-09-04 (v77, `43312b9`):** every `/rolemenu …` and `/role …` subcommand named below is retired — `/rolemenu` is now ONE staff command that opens a panel. The behaviour is unchanged; only the door is. See
> [`role-menus-panel-design.md`](role-menus-panel-design.md) and
> [`panels-program.md`](panels-program.md).
>
> ⚠️ **SUPERSEDED IN PART, 2026-09-05 (v84, `ce97de0`):** `/settings show|set` below are
> retired too — `/settings` is now ONE staff command that opens a paged panel over all the
> registry keys. See [`settings-panel-design.md`](settings-panel-design.md).
>
> **Audience:** the Phase 1 build agent and the reviewer. **Status:** TRACKED ·
> ✅ **LIVE since 2026-08-26** — three commits (`7190855` settings store + schema 2,
> `81fe783` action log, `5c528c5` role menus + Carl seed), deployed `2026-08-27T01:29:57Z`
> (`deploys.log` line 3, `synced 4 app commands`); `DONE.md` → "2026-08-26 — Phase 1 live".
> ⚠️ Fly release numbers were not written into `deploys.log` until **v59** (2026-09-03), so
> the phases 1–19 landings carry a date and a commit but no `vNN`.
> **Last verified: 2026-09-11 08:40** — re-checked against the tree at `1d090e5`: the three
> module paths and `bot.py:COGS` entry exist; `log_channel_id`, `staff_channel_id` and
> `role_menu_channel_id` are all still in `KEY_TYPES` (now **202** keys); `SettingsStore.get/
> set/all/staff_role_ids` all exist (`settings_store.py`); `SCHEMA_VERSION` is now **34**, not
> the 2 this design bumps it to. ⚠️ **NOT checked:** the role and channel IDs in the seed table
> (they need live Discord, and nothing in this pass met Discord or a browser), and whether
> Carl's panels are still posted.
> Before that, **2026-08-26** — role/channel IDs below were from the
> same-day Discord scan; everything else was design, not measurement.
> Owner approvals: build order (Q13), test policy, code style, test layout,
> commit policy — all in `TODO.md` / `CLAUDE.md`.

## Why this phase first

Every later feature needs (a) somewhere to keep its knobs and (b) somewhere
to say what it did. Role menus are the most-used incumbent surface (Carl's 5
panels, 23 roles, hundreds of reactions) and carry zero punishment risk, so
they are the right first thing for the owner to see working.

## Scope — three deliverables, one cog + two modules

```
black_bloc/
├── settings_store.py            ← typed per-guild settings on SQLite; the ONLY way features read config
├── actionlog.py                 ← log_action(): one embed to the log channel + one DB row, every time
└── cogs/community/role_menus.py ← F16: /rolemenu admin commands + persistent select-menu views
tests/
├── test_settings_store.py
├── test_actionlog.py
└── cogs/community/test_role_menus.py
```

`bot.py:COGS` gains `"black_bloc.cogs.community.role_menus"`. `bot.py` gets
`self.store = SettingsStore(self.db)` next to `self.db` and calls
`await self.store.load()` in `setup_hook` after `db.connect()` — nothing else
changes in `bot.py`/`app.py` (rule: lifecycle only / run button).

### 1. Settings store — `settings_store.py`

Schema (additive, appended to `storage/db.py:SCHEMA`, bump `SCHEMA_VERSION`
to 2):

```sql
CREATE TABLE IF NOT EXISTS settings (
    guild_id   INTEGER NOT NULL,
    key        TEXT    NOT NULL,
    value      TEXT    NOT NULL,      -- JSON
    updated_by INTEGER,
    updated_at TEXT    NOT NULL,      -- ISO-8601 UTC
    PRIMARY KEY (guild_id, key)
);
```

Registry of known keys (a module-level dict; unknown keys are refused):

| key | type | default | used by |
|---|---|---|---|
| `log_channel_id` | channel | `settings.test_channel_id` while TEST_MODE, else none | actionlog |
| `staff_channel_id` | channel | `settings.test_channel_id` | "who is staff" = roles that can View this channel (F4/F9 rule) |
| `role_menu_channel_id` | channel | none | where `/rolemenu post` targets by default |

API: `store.get(guild_id, key)`, `store.set(guild_id, key, value, by=user_id)`,
`store.all(guild_id)`; values validated by type; `staff_role_ids(guild)` helper
derives the staff set from `staff_channel_id` overwrites (roles with
`view_channel` allowed) — used by the permission check below.

Commands (in the same cog file as role menus? **No** — a small
`cogs/community/settings_cmds.py`… keep it simpler: put `/settings` in
`cogs/core.py` as a group, since it is core): `/settings show`, `/settings set
<key> <value>` (channel keys take a channel picker). Staff-only via
`is_staff(interaction)` = member has a staff role OR `manage_guild`.
*(Removed: `/settings show|set` retired at **v84**, 2026-09-05 — `/settings` is one command
that opens the paged panel; `settings_panel.py` — see
[`settings-panel-design.md`](settings-panel-design.md).)*

### 2. Action log — `actionlog.py`

```sql
CREATE TABLE IF NOT EXISTS action_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id   INTEGER NOT NULL,
    at         TEXT    NOT NULL,
    kind       TEXT    NOT NULL,      -- e.g. "role_menu.grant", "settings.set"
    actor_id   INTEGER,
    target_id  INTEGER,
    reason     TEXT,
    details    TEXT                   -- JSON
);
```

`await log_action(bot, guild, kind, *, actor=None, target=None, reason=None,
details=None)`: writes the row, then posts a compact embed (kind, actor,
target, reason, details) to `log_channel_id`. **Never raises** on the
Discord side — a log post failing (403, missing channel, `TestModeViolation`)
is caught and logged with `log.warning`; the DB row is the record of truth.
Every feature in every later phase calls this for anything it does to a
member or a channel.

### 3. Role menus — `cogs/community/role_menus.py` (F16)

Schema:

```sql
CREATE TABLE IF NOT EXISTS role_menus (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id    INTEGER NOT NULL,
    name        TEXT    NOT NULL,      -- unique per guild
    title       TEXT    NOT NULL,
    description TEXT,
    mode        TEXT    NOT NULL DEFAULT 'multiple',   -- 'multiple' | 'single'
    message_id  INTEGER,              -- last posted panel
    channel_id  INTEGER,
    UNIQUE (guild_id, name)
);
CREATE TABLE IF NOT EXISTS role_menu_options (
    menu_id  INTEGER NOT NULL REFERENCES role_menus(id) ON DELETE CASCADE,
    role_id  INTEGER NOT NULL,
    label    TEXT    NOT NULL,
    emoji    TEXT,
    position INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (menu_id, role_id)
);
```

Commands (staff-only, all under `/rolemenu`) *(removed: all eighteen `/rolemenu …` / `/role …`
leaves retired at **v77**, 2026-09-04 — `/rolemenu` opens the panel instead; see
[`role-menus-panel-design.md`](role-menus-panel-design.md))*: `create <name> <title>
[description] [mode]`, `add <name> <role> [label] [emoji]`, `remove <name>
<role>`, `list`, `show <name>`, `post <name> [channel]` (re-posting edits
the existing message if it still exists, else posts fresh and stores the new
ids), `delete <name>`.

The posted panel = an embed (title, description, the option list) + a
**`discord.ui.Select`** with `custom_id=f"rolemenu:{menu_id}"`, `min_values=0`,
`max_values=len(options)` (or 1 in `single` mode), one option per role with
its emoji. The view is **persistent** (`timeout=None`) and re-registered in
the cog's `cog_load` for every stored menu so panels survive restarts. On
select: compute the diff between the member's current roles ∩ menu roles and
the selection; add/remove accordingly (one `member.edit(roles=…)` call);
reply ephemerally "Added: … Removed: …"; `log_action(kind="role_menu.update")`.
Roles the bot cannot manage (above it in the hierarchy) are refused at `add`
time with a plain sentence, not at click time.

**Seed data** — a one-shot `/rolemenu seed-from-carl` staff command that
creates the five menus below from the measured maps (idempotent: skips a
menu whose name exists). *(Removed with the rest of the group at **v77**; it shipped as
`seed`/`seed-defaults` and its work is done — the menus exist.)*
IDs are from `archive/current-bots/discord-scan-2026-08-26.md`
§B/§D and `yagpdb-dashboard-2026-08-26.md`:

| name | title | mode | options (emoji → role id) |
|---|---|---|---|
| `pronouns` | Pronouns | multiple | ❤️ He/Him `1285785434131005474` · 💙 She/Her `1285785449541144607` · 💚 He/They `1285785451591897108` · 🤎 She/They `1285785453412220989` · 🤍 They/He `1285785455199260712` · 🧡 They/She `1285785456918925362` · 💜 They/Them `1285785458797711472` · 💛 It/Its `1285785460647526522` · 💞 Ask my pronouns `1285786169392762952` |
| `playstyle` | How do you enjoy games | multiple | 🏎️ Speedrunner `1285790096536109077` · 🛻 Challenge Runner `1285790140538683464` · 🚋 Score Attacker `1285790163380867146` · 🚑 Ranked Gamer `1285790268192460810` · 🚲 Casual `1285790198646706286` |
| `mentoring` | Learn or mentor | multiple | 🧙 Mentor `1075115919967273000` · 🥷 Initiate `1075117204447703040` |
| `interests` | Miscellaneous roles | multiple | 🏈 Sports `1413642880790167653` · 🔢 Squads `1413643063145926666` · 📺 Shows `1413643112965738506` · 🎶 Musichead `1413643194511659102` · 🧑‍🍳 Foodie `1413643284064108544` · 🎲 RPGer `1413643323876573185` · 🪅 Randos `1456219128921718939` · 🍵 QOTW `1474849344644710441` |
| `event-alerts` | Event alerts | multiple | 🎮 Marathons `1515068917628801135` (Carl used a custom emoji; use 🎮 as the placeholder) |

Migration safety: roles live on members, not on panels, so posting our
panels and (later, owner action) deleting Carl's does not strip anyone. We
never remove a role a member did not deselect.

## Test mode and permissions

- All commands go through the existing `tree.interaction_check` (test channel
  or DM only) — nothing to add. `/rolemenu post` without a channel argument
  targets `role_menu_channel_id` if set, else the current channel; while
  `TEST_MODE` the guard refuses any other channel automatically.
- Role edits are side effects the guard cannot see: the select handler must
  call `bot.guard.allows_channel(interaction.channel_id)` first when the
  guard is present, and refuse with the same ephemeral "test mode" sentence.
- Staff check: `is_staff()` as above; non-staff get one plain sentence saying
  the command is for staff and naming the staff channel.

## Tests (offline, mirror the package)

- `tests/test_settings_store.py`: defaults, set/get round-trip with JSON
  types, unknown key refused, type validation, `all()`.
- `tests/test_actionlog.py`: row written; Discord post failure is swallowed
  and warned (fake bot whose channel send raises); embed fields.
- `tests/cogs/community/test_role_menus.py`: CRUD on menus/options via the
  storage functions; diff computation (add/remove sets) as a pure function;
  `single` mode limits; seed is idempotent; persistent view custom_id format.
- `tests/storage/test_db.py`: bump to `SCHEMA_VERSION == 2` and assert the
  four new tables exist. *(`SCHEMA_VERSION` is **34** today — eighteen later phases and
  sweeps moved it; the four tables are still there.)*

## Definition of done

`pytest` green, `ruff` clean, `code-notes.md` updated for every new
`path:line` worth a note, `architecture.md` Shape tree updated, commit on a
clean tree with an explicit file list, **not pushed** (reviewer pushes and
deploys). Report: commit hash, test counts, what was NOT verified (live
Discord behaviour — the reviewer deploys and the owner clicks).
