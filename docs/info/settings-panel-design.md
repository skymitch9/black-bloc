# Settings — `/settings` is ONE command that opens the cross-cutting panel (wave 4)

> **Audience:** the build agent and the reviewer, and the owner for §I. **Status:** TRACKED ·
✅ **SHIPPED 2026-09-05 — Build 1 as v83 (`57a878d`, merge `9a7c87e`, `worktree-agent-a3e6ccbead5a90537`), Build 2 as v84 (`ce97de0`, merge `ce97de0`, `worktree-agent-a56c7b5137d9a609d`); sweeps 231–244; tree 30 → 29 with ZERO Groups, measured at the v84 boot (`synced 29`). See [Build 1 deviations](#build-1-deviations--what-the-build-did-differently-and-why) and `## Build 2 deviations` at the foot, which carry the RE-MEASURED numbers.** Forks F-S1–F-S5 all (a), decided by the conductor on this document's recommendation under the owner's "don't wait for me". ⚠️ **Everything above the deviations foot was keyed against `0304c4d` and its counts are STALE** — the registry is **179** keys, not 175, and `tests/test_bot.py` pins **30** top-level, not 36. This is the LAST panel of the program: it retires the last two
> `app_commands.Group`s in the tree.
>
> ⚠️ **Since then — the registry has grown a long way and two reported items are CLOSED.**
> - **The key count is now 202** (`len(settings_store.KEY_TYPES)`, measured 2026-09-11). It was 175
>   when §§A–J were written, 181 at the Build 2 measurement, 185 at the panels-program refresh.
>   ⚠️ **Every key count in this document is a snapshot, not a current fact** — the registry itself
>   is the one home, and `test_every_registry_key_is_reachable_from_the_panel_as_well_as_the_dashboard`
>   is what keeps the panel's reach equal to it. The panel's own tests count `KEY_TYPES`, so the
>   growth costs nothing.
> - 🟢 **KI-21 is CLOSED** (engineering sweep, v89, 2026-09-05 — moved whole to
>   [`../DONE.md`](../DONE.md)): *"Found while building"* item 1's one-commit wiring landed.
>   `api/settings_api.py` imports `set_key` and `clear_key` from `cogs.core` and calls them with
>   `via=VIA_WEBSITE`; the website gets the same verdict the panel does, and there is no KI-21 entry
>   in [`../KNOWN_ISSUES.md`](../KNOWN_ISSUES.md) any more.
> - 🟢 **Build 2 deviation 14 is CLOSED**: `panels-program.md` and `feature-list.md` were both
>   brought current by the conductor — F3 is answered there, the Core row says v84, and
>   `feature-list.md` has its `/settings` row.
> - **The Logs button** this build gave `/settings` grew **Show more** / **Important only** at v96
>   ([`logs-buttons-design.md`](logs-buttons-design.md)), and the shared `LogsPanel` times out on
>   **`settings_panel_minutes`** — this design's own key — because no `logs_panel_minutes` was added.
>
> **Last verified: 2026-09-11 09:55** (the header; the body is as at the design). Measured this pass
> against `main` at `f3ae743` (v108 live): `settings_store.py` holds `SETTINGS_PANEL_MINUTES` and
> `SETTINGS_CORE_KEYS_ADMIN_ONLY` (default `True`, fork F-S3 (a)) and owns `CORE_KEYS`, which
> `api/settings_api.py` re-exports; `labels.js` carries both new keys' rows word for word as §D
> asks; `black_bloc/settings_panel.py` has `has_editor`, `keys_in`, `reachable_on_the_panel`
> (Build 2 deviation 4), `bounds_line`, `confirm_lines` and `key_card_buttons`;
> `cogs/core.py` has `set_key`, `clear_key` and `number_label` (deviations 6, 7) and **no
> `VALUE_KEYS`**; `cogs/community/birthdays.py` still carries `from ..core import clear_key`
> (deviation 8 / reported item 5 — the first cog-package-to-cog-package import, still the only one,
> still a module-level function and still unreviewed against `architecture.md` rule 2). The tree is
> still **29** top-level with **zero** Groups. ⚠️ **NOT checked this pass:** anything in Discord or
> a browser, and none of the §§A–J line numbers were re-keyed — **trust the anchor text, not the
> number.**
>
> Before that, **2026-09-05** — every `path:line` below was READ against `main` at
> **`0304c4d`** ("TODO: F-M2/F-M3 = (a); /mod build dispatched"), in
> `black_bloc/cogs/core.py` (**307 lines**), `black_bloc/cogs/presence.py` (**132**),
> `black_bloc/presence.py`, `black_bloc/settings_store.py` (**1782**),
> `black_bloc/command_visibility.py` (**241**), `black_bloc/panels.py` (**219**),
> `black_bloc/api/settings_api.py` (**227**), `black_bloc/logkinds.py`,
> `tests/cogs/test_core.py` (**513**), `tests/cogs/test_presence.py` (**273**),
> `tests/test_bot.py` (**220**), `tests/test_command_visibility.py`,
> `tests/test_settings_store.py`, `site/public/assets/labels.js`, `site/mock/server.mjs`,
> `docs/access/sweeps.md` (**616 lines, last numbered row 187**),
> `docs/access/OWNER_GUIDE.md` (**119**), `docs/info/review-checklist.md` (**34 items**),
> `docs/KNOWN_ISSUES.md`, `docs/info/panels-program.md`, and the five sibling designs
> [`role-menus-panel-design.md`](role-menus-panel-design.md),
> [`automod-panel-design.md`](automod-panel-design.md),
> [`mod-panel-design.md`](mod-panel-design.md),
> [`honeypot-panel-design.md`](honeypot-panel-design.md),
> [`modmail-panel-design.md`](modmail-panel-design.md).
>
> **Measured, not assumed:**
> the registry holds **175 keys** — 123 in the base `KEY_TYPES` dict (`settings_store.py:143–267`),
> **35** in the fifteen appended feature blocks, and **17** generated `<feature>_log_level` keys
> (`:808–810` over `logkinds.FEATURES`, which has 17 entries `:24–42`). ⚠️ That supersedes
> `panels-program.md:212`'s "~120 keys". **34** of them are `channel` or `role` and therefore
> clearable today (`cogs/core.py:32`); **19** are `channel`, **15** are `role`.
> `tests/test_bot.py:179` asserts **36** top-level commands.
> `command_visibility.py:33` — `NEVER_HIDDEN = ("settings", "help", "about", "ping")`;
> `HIDDEN_WHEN_OFF` (`:17–32`) has **14** entries. **No panel anywhere writes a `_log_level`
> key** (zero matches across `black_bloc/cogs/`), and **9 of the 14 `*_panel_minutes` keys have
> no Discord control at all** (see §A).
>
> ⚠️ **NOT verified: anything was run.** No boot, no `pytest`, no `ruff`, no
> `node site/mock/check.mjs`, no `labels.js` parse, nothing against live Discord or the live
> dashboard. Every count above is a count of TEXT in the files named, not of a loaded module.
> Whether a real client submits an EMPTY multi-`Select` at `min_values=0` is the same unproven
> edge [`automod-panel-design.md`](automod-panel-design.md) §C flags; §C builds both paths.
> Whether the live guild has ever moved `staff_channel_id` off the test channel is **not
> knowable from the repo** — say so, do not guess.
>
> **Inherits every invariant in [`panels-program.md`](panels-program.md) §2 (P1–P17) and its §4
> library — none restated here.** Templates for shape:
> [`automod-panel-design.md`](automod-panel-design.md) (staff-only, one panel, no member half)
> and [`role-menus-panel-design.md`](role-menus-panel-design.md).
>
> ### The top-level count — one measured number and one PREDICTION
>
> **Measured on `main` at `0304c4d`: 36** (`tests/test_bot.py:179`). Today's 36 is
> six `Group`s (`settings`, `presence`, `mod`, `modmail`, `snippet`, `honeypot`), seventeen
> feature commands, nine top-level mod commands (`warn` `timeout` `untimeout` `kick` `ban`
> `unban` `purge` `case` `cases`) and four top-level modmail commands (`reply` `areply` `note`
> `close`).
>
> ⚠️ **Everything below is a PREDICTION, read out of three unmerged design docs, not measured.**
>
> | Step | Source | Δ | Lands at |
> |---|---|---|---|
> | `main` today | `tests/test_bot.py:179` | — | **36** |
> | honeypot panel | `honeypot-panel-design.md:128–129` — one Group's slot becomes one command's slot | 0 | 36 |
> | modmail **Build A** | `modmail-panel-design.md:976` — `/snippet` retired | −1 | 35 |
> | `/mod` panel | `mod-panel-design.md:128–131` — `/case` and `/cases` vanish; the seven direct mod commands STAY | −2 | **33** |
> | modmail **Build B** (later, not wave 4) | `modmail-panel-design.md:977` — `/areply` `/note` `/close` retired, `/reply` kept | −3 | 30 |
> | **this build** | the `settings` Group's slot becomes the `settings` command's slot (0); the `presence` Group retires into it (§I fork **F-S4**) | −1 | **29** |
>
> **29 top-level slots and ZERO `app_commands.Group`s** — which is the owner's stated target, and
> it is only reached if **F-S4 goes (a)**. Under (b) the estate lands at **30** with `/presence`
> as a command of its own. ⚠️ The build **re-measures and states the number it actually reads**;
> it never edits `:179` to a number this document predicted.

**The decision, already made** (owner, 2026-09-05 06:46, *"Okay ship both with your
suggestions"* — option (a)): **`/settings` becomes the CROSS-CUTTING panel.** The root shows
every feature's mode **READ-ONLY** with *open `/x` to change*; a mode is changed on its own
feature panel and nowhere else. The panel owns the keys no feature panel owns. The five
subcommands `show` / `set` / `set-role` / `set-value` / `clear` **retire.**

---

## A. Measured today — one Group, five leaf subcommands, and 175 keys with one door

`settings` is an `app_commands.Group` (`cogs/core.py:152–155`,
`default_permissions=STAFF_ONLY`). **Five leaf subcommands over ONE top-level slot.**

| Subcommand | Line | Gate | What is INLINE in the cog |
|---|---|---|---|
| `/settings show` | `:157` | `require_staff` `:159` | ⚠️ **all inline** `:161–170`: `store.all()` `:163`, one line per key with `display_value` + `KEY_HELP` `:164–165`, paged by `pages_under_limit` `:166`. **175 lines over ~6 ephemeral messages** |
| `/settings set <key> <channel>` | `:172` | `require_staff` `:183` | `store.set` `:187`, the sentence `:193`, `log_action("settings.set")` `:196–203` — ⚠️ **bare, no `kind_via`**. `key` is a `Choice` list built from `CHANNEL_KEYS` `:25` (**19 keys — under Discord's 25 cap, but only just**) |
| `/settings set-role <key> <role>` | `:205` | `require_staff` `:215` | `store.set` `:217`, sentence `:223`, a **second bare copy** of `settings.set` `:226–232`. `Choice` list from `ROLE_KEYS` `:26` (**15**) |
| `/settings set-value <key> <value>` | `:234` | `require_staff` `:241` | `parse_value` `:244` + `store.set` `:245`, sentence `:249`, a **third bare copy** of `settings.set` `:250–256`. `key` is an **autocomplete** (`value_keys` `:258–267`) because `VALUE_KEYS` `:27` outgrew 25 |
| `/settings clear <key>` | `:269` | `require_staff` `:272` | `store.clear` `:275`, `CLEARED`/`NOT_SET` `:281–283`, `log_action("settings.clear")` `:286–292` — **bare**. `key` autocompletes over `CLEARABLE_KEYS` `:32` (**34 keys**) |

⚠️ **None of the five checks the database.** There is no `db_up`/`db_ready` anywhere in
`cogs/core.py` — `show` reads `store._cache` through `store.all()` and answers happily while
the db is down, and the three writers call `db.conn.execute` (`settings_store.py:1736`)
straight into an exception. The panel closes that hole (S0).

⚠️ **`settings.set` is emitted from THREE places in one file** (`:196`, `:226`, `:250`), all
bare. `settings.clear` from one (`:286`), bare. The website emits `web.settings.set` /
`web.settings.clear` from its own route (`api/settings_api.py:205`, `:222`) with an explicit
`details["via"]`. So there are two independent doors, each logging once — checklist 34 is
satisfied today by separation, not by a shared function. §F keeps it that way and says why.

**`/presence`** is a second Group (`cogs/presence.py:42–45`, also `STAFF_ONLY`) with exactly
**one** leaf, `/presence apply` (`:115–128`): `require_staff`, `defer`, `ensure_bio(bot)`,
`self.apply_status()`, then `apply_sentence(changed, text)` (`:29–31`). Everything else in that
cog — the 10-minute `status` loop (`:61`), `on_ready` (`:88`), the join/leave debounce
(`:98–113`), `loop_health` (`:47`, read by the dashboard's Health page) — is **not a command
and does not move.**

### The orphan keys — measured, and this is what the panel is for

⚠️ **"Configurable both ways" (checklist 33) is satisfied for most keys today ONLY by
`/settings set-value`.** Retiring it without a replacement breaks the rule for every key below.
The list was measured by grepping every `store.set` / `store.clear` call in `black_bloc/` and
every `SETTINGS_KEYS` / `SETUP_KEYS` / `PANEL_KEYS` tuple, then subtracting.

| Class | Count | Keys | Why nothing else reaches them |
|---|---|---|---|
| **Core** | 7 | `log_channel_id`, `staff_channel_id`, `role_menu_channel_id`, `bot_bio`, `status_prefix`, `operator_read_log`, `hide_commands_when_off` | no feature panel exists. `role_menu_channel_id` is **read** by `/rolemenu` and written by nothing (`role-menus-panel-design.md:318` lists it under "reads, untouched") |
| **Loose singletons** | 2 | `emoji_skin_tone`, `cost_hosting_usd` | ditto |
| **Moderation, shared** | 3 | `modlog_channel_id`, `mod_dm_on_action`, `automod_warn_threshold` | `/automod` fork **F-A3 = (a)** made them read-only LINES (automod deviation 1); `mod-panel-design.md:337–338` lists all three under "reads, untouched" |
| **Log levels** | **17** | `<feature>_log_level` for every entry in `logkinds.FEATURES` | ⚠️ **zero matches** for `log_level` in any write path under `black_bloc/cogs/` — no panel has ever set one |
| **Panel minutes** | **9 of 14** | `request_`, `event_`, `poll_`, `birthday_`, `memory_`, `golive_`, `voice_`, `raidtrain_`, `rolemenu_` `_panel_minutes` | measured: only **applications, automod, chat, pings, youtube** put their own key on their own panel (`cogs/community/applications.py:2620`, `cogs/moderation/automod.py:1348`, `cogs/content/chat.py:918`, `cogs/content/pings.py:888`, `cogs/content/youtube.py:1637`). ⚠️ After wave 4 the family is **17** keys; honeypot adds a control (`honeypot-panel-design.md` H10) and **`mod-panel-design.md` and `modmail-panel-design.md` list no control for theirs** — so 11 of 17, a prediction |

**Total measured orphans: 38 keys**, plus a long tail inside the feature namespaces that each
panel reads but does not write (the chat panel's `Limits…` modal covers five numbers of ~28
`chat*` keys; `/memory` is member-only and writes **none** of the eight `chat_memory_*` staff
keys). ⚠️ **The exact tail is not load-bearing for this design** — §C's `A setting group…`
path reaches **every** registry key by construction, and §G turns that into an assertion. The
38 above are the ones that earn a CARD of their own.

### Namespaces, measured

The site already groups the registry with `settings_api.namespace_of` (`:53–59`): the six
`CORE_KEYS` (`:24–31`) plus `NAMESPACE_OVERRIDE` (`:33–37`) plus the prefix before the first
underscore. That yields **22 groups** — under Discord's 25-option cap, so ONE select holds
every group with no `capped_placeholder`.

> ⚠️ **Six of the 22 are singletons produced by a naming mismatch, and the Settings page
> already shows them that way.** `event_panel_minutes`/`event_panel_own_list` → **`event`**
> while `events_mode` → **`events`**; `voice_panel_minutes` → **`voice`** while
> `tempvoice_mode` → **`tempvoice`**; `memory_panel_minutes` → **`memory`** while
> `chat_memory_mode` → **`chat`**; and `hide_commands_when_off` → **`hide`**,
> `emoji_skin_tone` → **`emoji`**, `cost_hosting_usd` → **`cost`**. §J reports it; §B reuses
> `namespace_of` **verbatim anyway**, so the panel and the dashboard group identically.

The biggest namespace is **`chat` at 28 keys** (18 `chat_*` + 8 `chat_memory_*` +
`chat_panel_minutes` + `chat_log_level`), the only one over 25 — so `capped_placeholder`
(`panels.py:88`) fires exactly once, and §C's `Find a setting…` filter is what makes the other
three reachable.

### The site, measured

`site/public/settings.html` + `page-settings.js` own all 175 keys end to end, grouped by
`GET /api/settings` (`settings_api.py:178`), written by `PUT /api/settings/{key}` (`:190`) and
cleared by `DELETE /api/settings/{key}` (`:214`), all behind `staff_dependency`. There is a
command palette and a `settings.html#<key>` deep link (`page-settings.js:106`,
`palette.js:29`). `logkinds.py:93` maps the `core` feature to `settings.html`, so
`panels.site_page_url(origin, "core")` (`panels.py:123`) is the link with no new constant.

**Log kinds.** `settings.set` and `settings.clear` are `ROUTINE` (`logkinds.py:319–320`);
`presence.bio_set` is `ROUTINE` (`:290`); `commands.visibility` is `ROUTINE` (`:194`). All
three survive this build unchanged in NAME. `HEADS` (`:45–47`) files `settings`, `commands` and
`presence` under `CORE`, so `Logs` on this panel is `send_logs(interaction, "core")`.

---

## B. The decision — one `/settings`, staff only, and modes are READ-ONLY here

**`/settings` becomes a single `app_commands.command`; the `settings` Group goes**, keeping
`default_permissions=STAFF_ONLY` (`command_visibility.py:15`, `manage_messages`). `"settings"`
stays in `tests/test_bot.py:35`'s `STAFF_COMMANDS` and stays in
`command_visibility.NEVER_HIDDEN` (`:33`) — ⚠️ **that entry is load-bearing and is checked
twice**, in `apply` (`:101`) and in `hidden_names` (`:67`), because two different surfaces read
them (`code-notes.md` against `command_visibility.py:18`).

**One panel, no member half** (P2's split collapses): every caller is re-checked by
`still_staff` (`panels.py:55`) before every move, P8. A member who reaches the command gets
`store.staff_refusal(guild_id)` (`settings_store.py:1774`) as a sentence, never a dead button.

**What the panel owns**

| Today | On the panel |
|---|---|
| `/settings show` (175 lines, ~6 messages) | the ROOT embed — every feature's mode read-only, the server's posture, and how many keys are set away from default. The full 175-line dump does **not** come back; the site owns the whole list |
| `/settings set` / `set-role` | the key card's `ChannelSelect` / `RoleSelect` (§C) |
| `/settings set-value` | the key card's modal / select / toggle, by TYPE (§C) |
| `/settings clear` | **`Put the default back`** on the key card — rendered only when a row is actually stored |
| `/presence apply` | **Re-apply presence** on the `How Black Bloc looks…` sub-panel (fork **F-S4**) |
| — | **`Turn a feature back on…`** — NEW, and the reason the retirement is safe (below) |
| — | `Logs`, a NEW ephemeral followup (P11), `send_logs(interaction, "core")` |

### ⚠️ The way back for a HIDDEN command — the trade-off this build must not lose

`hide_commands_when_off` defaults **true** (`settings_store.py:1162`), so a feature whose mode
reads `off` has its one top-level command removed from the guild's tree within ~60 s
(`command_visibility.py:36–37`). Its panel — the only place its mode can be changed under the
one-fact-one-home rule — is then **unreachable.** Today's documented way back is
`/settings set-value <feature>_mode on`, named in `cogs/core.py:48–52` (`HIDDEN_NOTE`),
`sweeps.md` rows **183–187**, `OWNER_GUIDE.md:91`, and eleven code strings (§E). **Retiring
`set-value` without a replacement locks the owner out of Discord entirely and leaves only the
dashboard.**

**The replacement: a `Turn a feature back on…` `Select` on the ROOT**, rendered **only** when
`command_visibility.hidden_names(bot, guild_id)` returns a non-empty set (P3 — never an empty
control). One option per hidden feature, labelled with the feature and what it will become
(`YouTube — turn it on`), and picking one calls `set_key(bot, guild, "<feature>_mode", "on",
actor)`. ⚠️ It writes **`on`, never `shadow`** — `shadow` does not hide a command
(`command_visibility.py:35`, `sweeps.md` row 185), so `shadow` would leave the feature exactly
as reachable as it already was and read as a no-op.

Three properties that make this safe rather than clever:

1. **`hidden_names` is the ONE source.** The select cannot list a feature that is not actually
   hidden, and cannot miss one that is, because it asks the same function `/help` asks
   (`cogs/core.py:124`). No second table of "which features can hide".
2. **It is a SHORTCUT, not the only door.** `A setting group…` → `youtube` → `youtube_mode`
   reaches the same key in three clicks. If the shortcut were dropped tomorrow the estate would
   still have a way back — which is what makes it a fork-free addition rather than a load-bearing
   invention.
3. **At most 14 features can be hidden** (`HIDDEN_WHEN_OFF` has 14 entries), so the select can
   never hit Discord's 25-option cap. Measured, not assumed.

### The states

`/settings` has no per-caller state; the table is the SERVER's condition crossed with the
caller's permission.

| # | Condition | What renders |
|---|---|---|
| S0 | **database down** | the panel does not open — `panels.db_up` (`:80`) answers `DB_UNAVAILABLE` (`settings_store.py:1181`) as a sentence. ⚠️ Today all five subcommands skip this entirely (§A); the panel closes the hole |
| S1 | caller is not staff | `require_staff`'s sentence; nothing opens |
| S2 | staff, **without** `manage_guild` | the root opens; `Roles & channels…` is **NOT rendered** and the embed says in one line who it is for (P9 — never a dead button). Fork **F-S3** |
| S3 | staff **with** `manage_guild` | everything |
| S4 | `hidden_names(...)` is non-empty | `Turn a feature back on…` renders; the embed says how many commands are hidden and why |
| S5 | `hidden_names(...)` is empty, hiding **on** | the select is absent; the embed says every command is showing |
| S6 | `hide_commands_when_off` is **false** | ⚠️ `hidden_names` returns `set()` whatever the modes say (`command_visibility.py:56–57`), so the select is absent **even with features off** — and the embed must say *that*, not "every command is showing", or a Lead will read it as a bug |
| S7 | a `channels`/`roles` key holds **more than 25** ids | its multi-select is **not rendered** on the key card; the card says the list is longer than Discord can edit in one control and names the site. ⚠️ Discord requires `min_values ≤ len(default_values) ≤ max_values` — the red block in [`honeypot-panel-design.md`](honeypot-panel-design.md) §B. **Never a capped select**: it would silently drop the ids it could not show on the next submit |
| S8 | the `Presence` cog is not loaded | **Re-apply presence** is not rendered and the sub-panel says presence is not running (P3/P9) |

P3 in one line: **no state renders a control whose shared function would refuse it.**
`Turn a feature back on…` is absent with nothing hidden; `Put the default back` is absent when
nothing is stored; `Roles & channels…` is absent without `manage_guild`; a `json` key's card
carries no editor at all; a `bool` never shows both spellings of its toggle.

---

## C. The cards, the sub-panels, the modals

Each is a **re-render in place**: `retire(previous)` first (P6, `panels.py:62`), `defer()` then
`edit_original_response` (P5), `panels.db_ready` (`:70`) on every click after a defer,
`panels.still_staff` (`:55`) before **every** move including the reads (pings deviation 10 — a
demoted staffer browsing the registry is the same defect one step earlier).

### The ROOT embed

Built by `root_lines` (§F) and passed through `panels.clamped` (`:108`, `DESCRIPTION_LIMIT`
4000):

1. One line naming what this panel is: *the settings no feature panel owns, and the whole list
   on the site.*
2. **The mode block — READ-ONLY, one line per feature**, from `FEATURE_MODES` (§F, derived from
   `HIDDEN_WHEN_OFF` so it can never drift), e.g. `**YouTube** — shadow · \`/youtube\` to
   change`. Sixteen lines: the 14 in `HIDDEN_WHEN_OFF` plus `chat_memory_mode` → `/memory`
   (deliberately absent from that table, fork I-M1) and `modmail_enabled` → `/modmail`
   (⚠️ a `bool`, not an enum — `modmail-panel-design.md:146`; it renders as *answering DMs* /
   *not answering DMs*, never as `on`/`off`).
3. A line naming any feature that is hidden right now, and — under S6 — that hiding is switched
   off altogether.
4. One line: how many of the 175 keys this server has set away from their default.

⚠️ **No control on this panel changes a mode**, except `Turn a feature back on…` (whose whole
justification is that the owning panel is unreachable) and the generic key card (which reaches
every key by construction and cannot special-case one). One fact, one home for surfaces
(`CLAUDE.md`, global rules): the mode block links, it does not edit.

### The ROOT view — four rows

| Row | Control | Rendered when | Shared function |
|---|---|---|---|
| 0 | `Select` **"Turn a feature back on…"** | `hidden_names(bot, guild_id)` is non-empty (S4) | `set_key(bot, guild, key, "on", actor)` |
| 1 | `Select` **"A setting group…"** over `groups()` — 22 options, measured | always | — (opens the group card) |
| 2 | `Roles & channels…` → sub-panel | `manage_guild` (S3), fork **F-S3** | — |
| 2 | `How Black Bloc looks…` → sub-panel | always | — |
| 2 | `Panels & commands…` → sub-panel | always | — |
| 2 | `Logs` → a NEW ephemeral followup (P11) | always | `send_logs(interaction, "core")` — keeps its own `require_staff` (`actionlog.py`) |
| 2 | `Open on the site` (link) | `panels.site_page_url(origin, "core")` is not `None` | — |
| 3 | `Log levels…` → sub-panel | fork **F-S5** | — |
| 3 | `Refresh` | always | — |

⚠️ **Row 2 carries exactly five controls — Discord's per-row cap. Do not add a sixth.**

### `Roles & channels…` (Lead-only, S2/S3)

The four keys that decide who counts as staff and where Black Bloc talks:
`staff_channel_id`, `log_channel_id`, `modlog_channel_id`, `role_menu_channel_id`. Embed is
one line each with `display_value` (`settings_store.py:1309`) plus `KEY_HELP`.

| Row | Control | Rendered when | Shared function |
|---|---|---|---|
| 0–3 | one `ChannelSelect` per key, `min_values=1`, `max_values=1`, labelled with the key's purpose in words (never the raw key name) | always | `set_key(...)` |
| 4 | `Back` | always | — |

> 🔴 **The one measurement that decides how this card must read.** `staff_channel_id`'s
> default is `settings.test_channel_id` **always** — `settings_store.py:1436–1437`, on every
> guild in every mode, not only under `TEST_MODE`. So *"put the default back"* on this key
> points the staff channel at `#blackbloc-logs`, which disarms `/automod mode on`
> (`STAFF_IS_THE_TEST_CHANNEL`) and the honeypot's arming gate in one press, silently. The card
> **states what the default IS** before any reset is offered, and fork **F-S2** decides whether
> the reset is offered here at all.

### `How Black Bloc looks…` (presence, fork **F-S4**)

Embed: what the About Me says now, what the status reads, the skin tone, and — from
`Presence.loop_health("status")` (`cogs/presence.py:47`) — when the status loop last succeeded
and its last error, so a Lead can see why the status is stale before pressing anything.

| Row | Control | Rendered when | Shared function |
|---|---|---|---|
| 0 | `Re-apply presence` | the `Presence` cog is loaded (S8) | `reapply_presence(bot)` (§F) → `ensure_bio` + `apply_status`, answered with `apply_sentence` (`cogs/presence.py:29`) **unchanged in wording** |
| 0 | `The About Me…` → paragraph modal, prefilled | always | `set_key(..., "bot_bio", ...)` |
| 0 | `The status…` → short modal, prefilled | always | `set_key(..., "status_prefix", ...)` |
| 1 | `Select` **"Skin tone…"** over `SKIN_TONE_NAMES` | always | `set_key(..., "emoji_skin_tone", ...)` |
| 2 | `Back` | always | — |

⚠️ `Re-apply presence` is **slow work**: `ensure_bio` calls Discord's HTTP API and
`update_status` calls `change_presence`. It defers first (P5) and its refusal is
`STATUS_FAILED` (`cogs/presence.py:23–26`) **verbatim** — the wording is already right and
already tested.

### `Panels & commands…`

The cross-cutting posture keys, one place: `hide_commands_when_off`, the whole
`*_panel_minutes` family, `operator_read_log`, `cost_hosting_usd`.

| Row | Control | Rendered when | Shared function |
|---|---|---|---|
| 0 | ONE button, `Hide a feature's command while it is off` / `Leave every command showing` — never both | always | `set_key(..., "hide_commands_when_off", ...)`. ⚠️ The `on_change` hook (`command_visibility.py:236–237`) fires the ≤60 s re-sync; the reply says so in words, or a Lead will press it twice |
| 1 | `Select` **"How long a panel stays open…"** over the 14 (17 after wave 4) `*_panel_minutes` keys, each option showing its current value | always | — (opens that key's card) |
| 2 | ONE button for `operator_read_log`, same shape as row 0 | `manage_guild` | `set_key(...)` |
| 2 | `The hosting bill…` → number modal (`cost_hosting_usd`, max 10 000, `settings_store.py:317`) | always | `set_key(...)` |
| 3 | `Back` | always | — |

⚠️ **The panel-minutes select is a SECOND door onto five keys that already have one on their
own panel** (applications, automod, chat, pings, youtube — measured, §A). That is deliberate
and it is the owner's stated list: nine of fourteen have no Discord door at all, and *"make
every panel ten minutes"* is a cross-cutting posture no per-feature control can express. Every
option routes to the SAME key card as `A setting group…` does, so there is one editor and one
`set_key`, not two implementations.

### `Log levels…` (fork **F-S5**)

| Row | Control | Rendered when | Shared function |
|---|---|---|---|
| 0 | `Select` **"Which log…"** over `logkinds.FEATURES` (17 — under 25, measured), each option showing its current level | always | — (opens the level card) |
| 1 | on the level card: two buttons, **the two levels it is not on** (`off` / `important` / `all`, `logkinds.py:21`) | always | `set_key(..., log_level_key(feature), ...)` |
| 2 | `Back` | always | — |

⚠️ **Never three buttons with one greyed out** — P3. And the level card's embed carries
`log_level_help(feature)` (`settings_store.py:800`) ⚠️ **which is measurably wrong for most
features**: automod's deviation 9 found that eight of the thirteen `LOG_LEVEL_COMMANDS` rows
(`:783–797`) name a subcommand the panels program already retired. §J reports it; this build
does not fix it.

### `A setting group…` → the group card → the key card

This is the path that makes retiring `set-value` lossless: **every one of the 175 keys is
reachable through it**, and §G turns that sentence into an assertion.

**The group card** — embed lists every key in the group as `**<key>** — <value>` with
`display_value`, clamped:

| Row | Control | Rendered when | Shared function |
|---|---|---|---|
| 0 | `Select` **"A setting…"** over `editable_options(group, needle)` — ≤25, `panels.capped_placeholder(shown, total, pick=…)` naming the site | always | — (opens the key card) |
| 1 | `Find a setting…` → one short modal, the same substring match `value_keys` `:262–266` does today | the group holds more than 25 keys — measured, **`chat` alone** | re-renders the select filtered |
| 1 | `Back` | always | — |

**The key card** — embed: the key's name, its value (`display_value`), its default, `KEY_HELP`,
and its `KEY_MIN`/`KEY_MAX` where it has them. Then ONE editor, chosen by
`KEY_TYPES[key]`. ⚠️ **The table is DATA** (`control_for`, §F) and a parametrised test proves
every one of the 175 keys resolves to exactly one control:

| `KEY_TYPES` | Control | Notes |
|---|---|---|
| `channel` | `ChannelSelect`, `min_values=1`, `max_values=1` | 19 keys |
| `role` | `RoleSelect`, 1/1 | 15 keys |
| `channels` / `roles` | multi-select, `min_values=0`, `max_values=25`, stored ids as `default_values` | ⚠️ **not rendered at all above 25 stored ids** (S7). Beside it, a `Clear the list` button — the same fallback automod's `Log only` is for the unproven empty-submit edge |
| `enum` | `Select` over `KEY_CHOICES[key]`, current one flagged `default` | ⚠️ the build **re-measures** that no `KEY_CHOICES` entry exceeds 25 before trusting it |
| `enums` | multi-select over `KEY_CHOICES[key]`, stored list as `default_values`, `min_values=0` | the registry's only `enums` key is `request_channel_moves` (8 choices, `:904`). Same `Clear the list` fallback |
| `int` | `A number…` modal, one field, `max_length` sized to `KEY_MAX` | ⚠️ **a modal has no `app_commands.Range`** — the bound that vanished with the parameter is rebuilt where the value now enters (checklist 22, voice deviation 13). `coerce_value` (`:1242–1259`) already raises with `KEY_MIN_REASON`/`KEY_MAX_REASON` in words; **answer it verbatim and write nothing** |
| `text` | paragraph modal, prefilled, `max_length` 4000 | `bot_bio`, the templates, `chat_simple_model` |
| `bool` | **ONE** button saying which way it will go | never `Turn it on` and `Turn it off` together |
| `color` | short modal; `HEX_COLOR`'s refusal (`:1271–1274`) verbatim | `birthday_color` only |
| `json` | ⚠️ **no editor.** The card says the rule book is edited on `/automod` ▸ **A rule…** | `automod_rules` is the registry's only `json` key, measured `:211` |

Plus, on every key card:

| Row | Control | Rendered when |
|---|---|---|
| — | **`Put the default back`** (danger) | a row is actually stored for this guild — i.e. `store.clear` would return `True`. ⚠️ Today's `NOT_SET` branch (`cogs/core.py:34`) becomes unreachable by construction, which is the point: a panel should not be able to press a button that answers "nothing changed" |
| — | `Back to <group>` | always |

⚠️ **`Put the default back` widens `clear` from 34 keys to all 175.** `store.clear`
(`settings_store.py:1746`) has never had a type restriction — the restriction is
`CLEARABLE_KEYS` (`cogs/core.py:32`), and the reason recorded in `code-notes.md` against it is
*"an enum or an int has a default that is already a real value, and `set-value` can reach it."*
**`set-value` is going, so the rationale inverts.** §I lists this under settled, not as a fork.
(That code-note also says the list is *"11 long"* — measured today it is **34**. §J reports it.)

### The modals

All `AnswersErrors` + `discord.ui.Modal` (P12, checklist 30). ⚠️ **`panels.NoteModal` is NOT
used** — nothing here sends a person a free-text reason. Four modal shapes, all built from
the same `KeyModal(key, kind)` so there is one submit path and one `set_key` call:

| Shape | Field | Refusal |
|---|---|---|
| number | one short field, prefilled | `coerce_value`'s `SettingError` verbatim; **nothing is written** |
| text | one paragraph field, prefilled, 4000 | ditto |
| colour | one short field, prefilled | ditto |
| find | one short field, empty | never refuses; an empty match re-renders with a sentence, not an error |

---

## D. Settings (P13 · checklist 33)

Registered **in their own appended block** at the foot of the registry, exactly where
`rolemenu_panel_minutes` sits (`settings_store.py:1132–1144` for `KEY_TYPES`/`KEY_HELP`,
`:1698–1699` for `default()`), so the wave-4 branches merge textually.

| Key | Type | Default | Status |
|---|---|---|---|
| `settings_panel_minutes` | `int` | **10** | **NEW.** How long the panel stays live. Help text carries KI-20's warning in the same shape as the fourteen shipped keys, word for word: 15+ loses the "gone quiet" footer because Discord's interaction token expires at 15 minutes |
| `settings_core_keys_admin_only` | `bool` | **fork F-S3** | **NEW whichever way F-S3 goes** — checklist 33 says a default decided in chat is a registry key, not a constant. Its shape is `chat_status_admin_only`'s (`:678–683`) exactly: `true` keeps the four core channel/role keys to `manage_guild`, `false` lets any staff member edit them, and the rest of the panel opens either way |

⚠️ `settings_panel_minutes` joins the family, so it also appears on the
`Panels & commands…` select — **the panel can change how long it itself stays open.** That is
correct and it is the same shape every other panel has; the reply says the new number applies
to the *next* `/settings`, not this one.

**Both keys need their site rows**, following the shipped pattern exactly:

| File | Line to copy | What to add |
|---|---|---|
| `site/public/assets/labels.js` | the `rolemenu_panel_minutes` row (`:56`) | `settings_panel_minutes: 'How long the /settings panel stays live'` and `settings_core_keys_admin_only: 'Whether only a Lead may re-point the staff and log channels'` |
| `site/mock/server.mjs` | the `automod_panel_minutes` row (`:423`) | one `int` row and one `bool` row |

⚠️ `labels.js:187`'s `NAMESPACES` list does **not** contain `'core'` (measured — it is
`golive, youtube, pings, tempvoice, honeypot, events, birthday, modmail, automod, rolemenu,
raidtrain, applications`). Both new keys land in the `settings` namespace by
`namespace_of` (`settings_` prefix), which is a **23rd group** nobody asked for. ⚠️ **Add both
to `CORE_KEYS`** (`settings_api.py:24–31`) in the same commit so they file under `core` beside
`operator_read_log`, and re-measure the group count — the panel's select must stay at 22.

**Existing keys this panel WRITES:** potentially all 175, through one `set_key`. **Existing
keys it reads for its own rendering:** `hide_commands_when_off`, every `<feature>_mode` in
`FEATURE_MODES`, `staff_channel_id` (for the refusal sentence).

**Nothing else here is a decision.** The 25-option cap, the five-per-row cap and the
five-fields-per-modal cap are Discord's; the type→control table is `KEY_TYPES`; the bounds are
`KEY_MIN`/`KEY_MAX` and were decided phase by phase; and the two behaviours a reader might
mistake for decisions — staff re-checked before every move, and a control being hidden rather
than offered-and-refused — are **settled by the standing rules** (P8, P3/P9), so neither
becomes a key.

---

## E. What goes away, and every line that names it

`/help` reads the tree (`cogs/core.py:90–98`, `:118`), so it follows with no edit (P15) — and
the `/help` half of `tests/cogs/test_core.py` (`:374–:513`) is what proves it.

| Thing | Where | Becomes |
|---|---|---|
| `settings` Group | `cogs/core.py:152–155` | one `@app_commands.command(name="settings")`, same `default_permissions=STAFF_ONLY` |
| the five leaf commands | `:157`, `:172`, `:205`, `:234`, `:269` | buttons, selects, modals |
| `value_keys` autocomplete | `:258–267` | **deleted** — nothing types a key name any more; the `Find a setting…` modal inherits its substring match |
| `clearable_keys` autocomplete | `:294–303` | **deleted** |
| `CHANNEL_KEYS` `:25`, `ROLE_KEYS` `:26`, `CLEARABLE_KEYS` `:32` | | **deleted** — the key card branches on `KEY_TYPES[key]` directly, so three derived lists become one lookup |
| `VALUE_KEYS` `:27` | | ⚠️ **KEPT and MOVED** to `black_bloc/settings_panel.py`. `tests/test_settings_store.py:992` asserts checklist 33 against it (*"a key `/settings set-value` cannot autocomplete is a dashboard-only key"*); §G rewrites that test into the stronger form — **every** registry key is reachable from the panel |
| `PICK_FROM_LIST` `:35` | | **deleted** — there is no key box to type in |
| `CLEARED` `:33`, `NOT_SET` `:34` | | `CLEARED`'s wording moves to the key card; `NOT_SET` is **deleted** — unreachable by construction (§C) |
| `HIDDEN_NOTE` `:48–52` | | **rewritten** — see the string table below |
| `presence` Group | `cogs/presence.py:42–45` | **deleted** (fork **F-S4 (a)**) |
| `presence_apply` | `:115–128` | `reapply_presence` (§F) + the **Re-apply presence** button |
| the rest of `cogs/presence.py` | `:47`, `:52–113` | ⚠️ **untouched.** `loop_health` is read by the Health page; the loop, `on_ready` and the join/leave debounce are not commands |
| `tests/test_bot.py` `STAFF_COMMANDS` | `:31` | `"presence"` **removed**; `"settings"` `:35` **stays** |
| `tests/test_bot.py` `LOGS_GROUPS` | `:11–15` | ⚠️ **untouched by this build** — its three entries are honeypot's, modmail's and `/mod`'s to delete. If they have already merged, it is empty and `test_every_feature_group_has_a_logs_command` degenerates; **report it, do not repurpose the test** |
| `tests/test_bot.py:179` | | **re-measured**; the expectation is the arithmetic in the header, and if it does not match, the build **stops** |
| `command_visibility.NEVER_HIDDEN` | `:33` | **unchanged.** `"settings"` stays; `"presence"` was never in it and never needed to be (`HIDDEN_WHEN_OFF` has no presence entry) |

### Strings that name a retired subcommand, rewritten in the SAME commit

⚠️ **This is the largest string sweep of the program: 21 code sites in 15 files, 4 mock
copies, 5 test assertions.** Each currently tells somebody to run something that will not
exist. Measured by `grep -rn "/settings"` at `0304c4d`.

| File:line | Today names | Becomes |
|---|---|---|
| `cogs/core.py:48–52` | `HIDDEN_NOTE` — *"`/settings set-value <feature>_mode on`"* | *"`/settings` ▸ **Turn a feature back on…**"*. ⚠️ **The single most important line in the sweep** — it is the sentence a locked-out owner reads |
| `applications.py:119` | `/settings set-value applications_mode on` | the panel path |
| `cogs/community/role_menus.py:124` | `/settings set-value rolemenu_mode on` | the panel path |
| `cogs/community/role_menus.py:1697` | `/settings set role_menu_channel_id` | *"`/settings` ▸ **Roles & channels…**"* |
| `cogs/content/chat.py:97` | *"`/settings set-value` changes any of these"* | *"`/settings` ▸ **A setting group…** ▸ chat"* |
| `cogs/content/chat_memory.py:63` | `/settings set-value key:chat_memory_mode value:on` | the panel path |
| `cogs/moderation/automod.py:192` | *"`/settings set-value` — not here"* | the panel path |
| `cogs/moderation/automod.py:119`, `:146` | `/settings set staff_channel_id` (two arming refusals) | *"`/settings` ▸ **Roles & channels…**"* |
| `cogs/moderation/honeypot.py:81` | `/settings set staff_channel_id` | ⚠️ **the honeypot build is rewriting this file right now — coordinate at the merge, do not assume the line number** |
| `cogs/moderation/modmail.py:179` | `/settings set staff_channel_id` | ⚠️ **modmail Build A's file — same warning** |
| `cogs/community/polls.py:190`, `:236` | `/settings set staff_channel_id` | the panel path |
| `cogs/community/birthdays.py:122`, `:125` | `/settings set-role birthday_role_id` | the panel path |
| `pings.py:53`, `:88`, `:125` | three `set-value` sentences | the panel path |
| `rolegrants.py:98` | `/settings set-value rolemenu_approval_channel_id` | the panel path |
| `events.py:355` | `/settings set staff_channel_id` | the panel path |
| `requests.py:89` | `/settings set request_mode on` | the panel path |
| `api/tools/chat_memory.py:42` | `/settings set chat_memory_staff_view full` | ⚠️ **served to the WEBSITE** — it must read correctly on a web page, so prefer *"the Settings page, or `/settings` in Discord"* over a Discord-only button path |
| `site/mock/server.mjs:63`, `:2697`, `:4237`, `:4438` | four copies of the sentences above | rewritten to match, or `check.mjs` drifts from the live strings |
| `tests/cogs/content/test_chat.py:1474` | `assert "/settings set-value" in said` | rewritten to the new sentence |
| `tests/cogs/test_core.py:433` | `assert "/settings set-value <feature>_mode on" in said` | rewritten |
| `tests/cogs/test_core.py:511` | `assert "/settings show — …" in said` | rewritten to the single `/settings` line |
| `tests/test_command_visibility.py:341`, `:353` | two docstrings naming `set-value` as the door that survives | rewritten |
| `tests/test_settings_store.py:992` | docstring + assertion built on `set-value`'s autocomplete | rewritten (§G) |

⚠️ **Measured and needing NO edit, contrary to expectation:** `KEY_HELP[HIDE_COMMANDS_WHEN_OFF]`
(`settings_store.py:1166–1173`) names **no command at all** — it says *"turning the feature
back on brings the command back within about a minute."* Leave it. Report that the brief's
assumption was wrong rather than editing a correct sentence.

### Docs rewritten in the same commit (P15)

| Doc | What |
|---|---|
| `docs/access/sweeps.md` | rows **16, 53, 65, 67, 68, 71, 83, 95, 108, 130, 156, 174, 184, 185, 186** and the prose at `:367` each name `/settings set-value` as a step — **rewritten IN PLACE, not added to**. ⚠️ Row **16** (`:150`) also names **`/settings logs`, which has never existed** (measured: `cogs/core.py` registers show/set/set-role/set-value/clear and nothing else) — after this build there IS a `Logs` button, so that row becomes true for the first time |
| `docs/access/OWNER_GUIDE.md:83`, `:86`, `:91` | three rows name `/settings set-value`. ⚠️ `:91` is **the documented way back** for a hidden command and must name the new one exactly. The sweeps count in the header moves |
| `docs/info/panels-program.md:101` | the Core row → built, with the measured `commands synced` before/after |
| `docs/info/panels-program.md:212–214` | ⚠️ **fork F3 is ANSWERED** — it currently asks whether to page, keep the group, or retire the Discord path. It gets the owner's 2026-09-05 quote and a link here. Its "~120 keys" becomes **175** |
| `docs/info/panels-program.md:103–107` | the totals line — 0 subcommands, and the top-level number this build actually lands at |
| `docs/info/feature-list.md` | the core row gains one clause: `/settings` is one command that opens a panel, and `/presence` is gone |
| `docs/info/README.md` | a row for this file beside the other panel designs |
| `docs/info/code-notes.md` | re-keyed at the merge. ⚠️ **`cogs/core.py` carries 21 anchors** — `:25, :32, :35, :48, :60, :81, :92, :97, :111, :115, :139, :141, :151, :152, :184, :218, :226, :238, :246, :247, :287` — and **`cogs/presence.py` carries 8** — `:16, :41, :45, :68, :74, :87, :104, :116`. Several need REWRITING, not just re-pointing: `cogs/core.py:32` (its "the list is 11 long" is already wrong — **34** measured), `:238`, `:246`, `:247` (all name `set-value`), and `cogs/presence.py:116` (names `/presence apply`). Trust the anchor text over the number |
| the phase docs naming a `/settings` subcommand | a dated **"superseded by the panel"** line at the top, NOT a rewrite — a phase doc is the record of what was decided then |

---

## F. Extractions (P4) — one function per move, called by BOTH doors

⚠️ **The DB/move layer stays in the COG**, as it does for automod, applications and voice.

**Already shared, reuse unchanged:** `store.set` / `store.clear` / `store.all` / `store.get` /
`store.default` (`settings_store.py:1734`, `:1746`, `:1731`, `:1726`, `:1435`), `coerce_value`
`:1192`, `parse_value` `:1284`, `display_value` `:1309`, `require_staff` `:1371`,
`send_logs` (`actionlog.py`), the whole `panels.py` library, `command_visibility.hidden_names`
(`:60`), `presence.ensure_bio` / `update_status`, `apply_sentence` (`cogs/presence.py:29`).

**New, module level in `black_bloc/cogs/core.py`** — each does ONE write and ONE log row:

| Function | Replaces | Note |
|---|---|---|
| `set_key(bot, guild, key, value, actor)` | the **three** bare `settings.set` copies at `:196`, `:226`, `:250` | one home for the write and the row. Returns an `Outcome` (`panels.py:22`) so the sentence and the refusal have one shape |
| `clear_key(bot, guild, key, actor)` | `:275–292` | returns `cleared: bool`; the panel never renders the button when it would be `False`, so the `NOT_SET` branch dies |
| `reapply_presence(bot)` | `cogs/presence.py:121–123` | lives in **`cogs/presence.py`**, not `core.py` — it needs `Presence.apply_status`, so the panel reaches it with `bot.get_cog("Presence")` and renders nothing when that is `None` (S8) |

> ⚠️ **`set_key` takes NO `via` parameter, deliberately.** Checklist 34 asks that a web route
> calling a shared path passes `via=VIA_WEBSITE` and deletes its own `note()`. Measured: the
> settings route does **not** call any shared function — it calls `store.set` directly and
> `note("web.settings.set")` itself (`settings_api.py:200–211`). One write, one row, on each
> door independently. Adding a `via` nobody passes is dead weight (automod deviation 2's
> lesson). ⚠️ Wiring `PUT /api/settings/{key}` through `set_key` **is** the right next pass —
> it is also what would close **KI-21** (the website can arm automod past both arming
> refusals) — and §J says so explicitly. It is a settings-API change, not a panel change.

**New pure module `black_bloc/settings_panel.py`** (tests in `tests/test_settings_panel.py`) —
the shape `black_bloc/rolemenus.py` and `black_bloc/chat_panel.py` landed with:

| New | Signature / content |
|---|---|
| `FEATURE_MODES` | ⚠️ **derived from `command_visibility.HIDDEN_WHEN_OFF`**, plus exactly two hand-added rows (`chat_memory_mode` → `/memory`, `modmail_enabled` → `/modmail`). Never a second hand-maintained table of "which features have a mode" — that is how the mode block and the hide table would drift apart |
| `mode_lines(store, guild_id)` | the read-only block, one line per entry, `modmail_enabled` rendered in words not `on`/`off` |
| `root_lines(bot, guild, hidden)` | the whole ROOT embed as a `list[str]` — takes `hidden` rather than computing it, so it stays synchronous and testable |
| `groups()` / `keys_in(group)` | over `namespace_of` — see the move below |
| `control_for(key) -> str` | the §C type→control table AS DATA; a parametrised test walks all 175 keys |
| `key_card_lines(store, guild_id, key)` | name, value, default, help, bounds |
| `editable_options(group, needle="")` | the ≤25 select options + `capped_placeholder` |
| `default_sentence(store, guild_id, key)` | what `Put the default back` would make it, in words — the line that makes `staff_channel_id`'s footgun visible |
| `back_on_options(bot, guild_id)` | `Turn a feature back on…`'s options, straight off `hidden_names` |
| `level_moves(current)` | the two levels a feature is not on |
| `PANEL_MINUTES_KEY = "settings_panel_minutes"`, `panel_minutes(store, guild_id)` | one-liners over `panels.panel_minutes` (`panels.py:119`), exactly as the fourteen shipped panels do |
| `PANEL_TITLE`, `PANEL_TIMEOUT_FOOTER`, the panel sentences | wave-0 deviation 1: the footer is a whole sentence, not a format string |

> ⚠️ **One move that is NOT optional: `namespace_of`, `CORE_KEYS` and `NAMESPACE_OVERRIDE` move
> from `api/settings_api.py:24–59` into `settings_store.py`**, and `settings_api` imports them
> from there. A pure module in the bot's import graph must not import from `api/`, which would
> drag FastAPI into every `import black_bloc.cogs.core`. Moving them keeps ONE grouping for the
> dashboard and the panel (one fact, one home) and adds no dependency in either direction. It is
> a pure move: no call site changes except the import line, and
> `tests/api/test_settings_api.py` must stay green **with no edit** — that is the proof.

**What to ADD to `panels.py`: nothing, this build.** One candidate is real and goes to the
CONDUCTOR: the **confirm helper**. `youtube.open_confirm`, pings' deviation 8 and automod's
deviation 12 are already three hand-rolled copies, and automod handed its copy to the
conductor to fold in — measured, **it has not landed** (`panels.py` is 219 lines and has no
`open_confirm`). Fork **F-S2 (a)** makes this the fourth. Build it locally, name it in the
deviations, and hand it over, the way `clamped` landed.

**Two things to reuse, never re-copy:** `panels.answer` (`:36`) — `cogs/core.py` has no copy
today, keep it that way — and `panels.site_page_url(origin, "core")` (`:123`), never a private
`SETTINGS_PAGE` constant.

---

## G. Tests (P16 — one file per source file, mirrored paths)

| File | What it gains, and what it keeps |
|---|---|
| `tests/cogs/test_core.py` (513) | ⚠️ **The `/help` half `:374–:513` stays UNCHANGED in assertion except `:433` and `:511`** (the two that name a retired path) — that is the proof `/help` still follows the tree with no edit (P15), and it is the strongest evidence this build can produce about the half it did not touch. The settings half `:180–:311` is rewritten to drive the panel: `/settings` answers ephemerally with a panel; **parametrised over S0–S8 — each renders exactly its §B row and no other**; `Turn a feature back on…` is absent with nothing hidden, present with something hidden, and absent under S6 with the switch off; `Roles & channels…` is absent without `manage_guild` and the embed says who it is for; `Put the default back` is absent on an unset key; a `json` key's card carries no editor; a `bool` never shows both spellings; a `channels` key with 26 stored ids renders no select and says so; every write calls `set_key`/`clear_key` (mock them) exactly once; `Logs` answers a **NEW** followup and still refuses a demoted staffer; a staffer demoted mid-card moves nothing (`still_staff` at every site, reads included); `db_ready` after every defer |
| `tests/test_settings_panel.py` | ⚠️ **NEW FILE.** `control_for` over **all 175 keys** — every one resolves to exactly one control, and the set of keys with no control is exactly `{"automod_rules"}`; `FEATURE_MODES` covers `HIDDEN_WHEN_OFF` plus the two extras and nothing else; `mode_lines` renders `modmail_enabled` in words; `groups()` returns 22 and every key lands in exactly one; `editable_options` at 24, 25 and 26 keys and with a `needle`; `back_on_options` empty / one / fourteen; `level_moves` never returns the current level; `default_sentence` for `staff_channel_id` names the test channel; `panel_minutes`; every `PANEL_MOVES` entry distinct |
| `tests/test_settings_store.py` | `settings_panel_minutes` round-trips, defaults 10, help mentions 15, refuses `-1` and the string `"15"` — the shipped `*_panel_minutes` shape; the same for `settings_core_keys_admin_only`. ⚠️ **`:992` is rewritten into the stronger checklist-33 guard:** `set(KEY_TYPES) == set(every key the panel can reach)`, which is a real invariant rather than a statement about an autocomplete that no longer exists |
| `tests/cogs/test_presence.py` (273) | the `presence_apply` test becomes a `reapply_presence` test with the **same assertions on `apply_sentence`'s three outcomes**; every loop / listener / `loop_health` test stays **unchanged** — the proof the loop did not move |
| `tests/test_bot.py` | `STAFF_COMMANDS` loses `"presence"` (`:31`); the tree-limit test `:179` **re-measured** against the header's arithmetic; ⚠️ `LOGS_GROUPS` untouched |
| `tests/test_command_visibility.py` | ⚠️ **the behaviour tests stay green with no edit** — this build changes no visibility logic. Only the two docstrings at `:341`/`:353` move |
| `tests/api/test_settings_api.py` | ⚠️ **must stay green with no edit** — the proof the `namespace_of` move changed nothing and the web door did not move |
| `tests/test_logkinds.py` | ⚠️ **unchanged.** No kind is added, renamed or given a `kind_via` head by this build; the three AST-walk guards named in checklist 34 must still pass |

---

## H. §J — prove before merge (P17), and the sweep rows

1. `python -m black_bloc` boots; **read `commands synced` and record both numbers.** With no
   bot token, measure it the only other way:
   `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits`. ⚠️ **The expected
   number depends on which wave-4 branches have merged** — read the assertion on the base
   commit, subtract 1 for the retired `presence` Group, and if the delta is not exactly **1**,
   **stop**: something other than this build broke.
2. ⚠️ **Assert ZERO `app_commands.Group`s remain** if all of wave 4 has merged — a one-line
   addition to `test_the_command_tree_stays_inside_discords_limits`, and the cleanest possible
   statement that the program is finished. If wave 4 has NOT all merged, do not add it.
3. `python -c "import black_bloc.settings_panel, black_bloc.cogs.core,
   black_bloc.cogs.presence, black_bloc.api.settings_api, black_bloc.panels"` — the substitute
   for a boot (wave-0 deviation 5), and the line that catches the one import edge this build
   creates and the one it moves (`settings_api` → `settings_store` for `namespace_of`).
   ⚠️ **`settings_store` must not import `panels`** — automod deviation 4 measured that
   `panels` imports `DB_UNAVAILABLE` from `settings_store`, so a module-level import closes the
   loop and every import of `settings_store` dies. `settings_panel.py` may import `panels`
   freely; `settings_store.py` may not.
4. The parametrised state test: every state renders its row and no other (checklist 3, 12).
5. `ruff`; full `pytest`; `node site/mock/check.mjs` (**expect page/route counts unchanged** —
   no route is added or removed; state the figure before AND after rather than trusting a
   remembered one); `node --input-type=module --check < site/public/assets/labels.js`.
6. Checklist sweep before reporting — **8 and 30** (`AnswersErrors` on every modal, select and
   view), **11** (`allowed_mentions` on every interpolated send — channel and role mentions are
   all over these embeds), **15/17** (the confirm-helper duplicate, §F), **21** (the
   `manage_guild` gate reads COMPUTED permissions, and `store.staff_roles` is unchanged),
   **22** (⚠️ **the biggest one here** — every bound that vanished with an
   `app_commands.Choice`/`Range` parameter is rebuilt in the modal; `coerce_value` is the
   backstop, never the only check), **26** (every list-typed key keeps a way to remove an entry
   — `Clear the list` plus the multi-select), **33** (§D, and the §G assertion that every key is
   reachable), **34** (no kind changed; `set_key` deliberately takes no `via`, argued in §F).
7. ⚠️ **TEST MODE stands.** The bot speaks only in `#blackbloc-logs` (`TEST_CHANNEL_ID`)
   and DMs, enforced by `black_bloc/guard.py`. Run every sweep row in that channel.
8. ⚠️ **Three sibling branches are rewriting `honeypot.py`, `modmail.py` and `modcmds.py` right
   now.** Two of this build's string sites live in the first two files. **Do the string sweep
   LAST, on a freshly rebased tree**, and never `git stash`; use `git pull --rebase --autostash`
   before every push.

### Sweep rows — lettered `S1…S12`, for the conductor to number

`docs/access/sweeps.md` holds 616 lines and its last numbered row is **187** today, ⚠️ **but
three wave-4 designs are in flight with their own lettered blocks (`H1–H10`, `M1–M12`,
`D1–D9`), so this document claims NO numbers.** The rows named in §E are rewritten **in place**,
not added to.

| # | Do this | Expect |
|---|---|---|
| S1 | `/settings` as a Lead in `#blackbloc-logs` | ONE ephemeral panel. The top reads every feature's mode — sixteen lines, each naming the command that changes it — and **not one of them is a control here.** Below: **Turn a feature back on… · A setting group… · Roles & channels… · How Black Bloc looks… · Panels & commands… · Log levels… · Logs · Open on the site · Refresh**. Nothing says `/settings show` or `/settings set-value` anywhere |
| S2 | `A setting group…` → **chat** | the group card lists the chat settings and the picker says **25 of 28 — the rest are on the site**. Press **Find a setting…**, type `memory`, and the three that were off the end are now on the picker. That is the only namespace over 25 |
| S3 | `A setting group…` → **birthday** → `birthday_color` → type `blue` | one sentence naming the shape `#4eefff` and **nothing is saved** — re-open the card and the colour is what it was. Type `#4eefff` and it saves, one `settings.set` row, **Via: Discord** on the Logs page |
| S4 | the same key card → **Put the default back**, then press it again | the first press says the default is back and leaves one `settings.clear` row; **the second press is not there** — the button does not render on a key with nothing stored. No state is terminal and no button answers "nothing changed" |
| S5 | `A setting group…` → **automod** → `automod_rules` | the card has **no editor at all** and says the rule book is edited on `/automod` ▸ **A rule…**. It is the only key in the registry like that |
| S6 | `A setting group…` → **honeypot** → `honeypot_exempt_role_ids`, with more than 25 roles stored | the role picker is **not drawn**, the card says the list is longer than Discord can edit in one control and names the site, and **Clear the list** is still there. ⚠️ Under 25 the picker IS drawn with the stored roles already ticked |
| S7 | dashboard → Settings → `youtube_mode` → **off**. Wait a minute, `Ctrl+R`, then `/settings` | `/youtube` is gone from the command list, and the panel now carries **Turn a feature back on…** with YouTube on it. Pick it: within about a minute `/youtube` is back **on**, not shadow. ⚠️ **This row is the whole reason `set-value` could be retired** — it is the most important row in the set |
| S8 | `/settings set-value` | ⚠️ **there is no such command.** `/help` says so too: its missing-commands line now names **`/settings` ▸ Turn a feature back on…**, not `set-value` |
| S9 | `hide_commands_when_off` → **false** (Panels & commands…), with two features still off, then `/settings` again | every command is back at once; **Turn a feature back on… is absent**, and the embed says hiding is switched off altogether rather than "every command is showing" — the two sentences mean different things |
| S10 | `How Black Bloc looks…` → **Re-apply presence** | the same sentence `/presence apply` used to print — whether the About Me changed and what the status now reads — and a `presence.bio_set` row when it did change. ⚠️ `/presence` itself is **gone from the command list** |
| S11 | `Roles & channels…` as a staff member who does **not** have Manage Server | the button is **not drawn** and the panel says in one line that re-pointing the staff and log channels is for a Lead. It is not offered-and-refused; it is not offered. As a Lead it is there, and the `staff_channel_id` card says in words that its default is **#blackbloc-logs** |
| S12 | `Log levels…` → **chat** → the two buttons; then `Logs`; then leave the panel `settings_panel_minutes` (10) minutes | the level card offers only the two levels it is **not** on; `Logs` answers a **NEW** ephemeral message and the panel stays where it is; after ten minutes every control greys out and the footer reads *this panel has gone quiet — run /settings again* |

---

## I. The genuine forks — the owner decides, one at a time

### Settled first, by the standing rules, so they are NOT put to him

- ✅ **`/settings` stays staff-only and stays in `NEVER_HIDDEN`** (`command_visibility.py:33`).
  It is the last door when everything else is hidden; a registry row that named it would lock
  the owner out of Discord entirely (`code-notes.md` against `command_visibility.py:18`).
- ✅ **The root lists every feature's mode READ-ONLY, with *open `/x` to change*.** Owner,
  2026-09-05 06:46, option (a), verbatim: *"Okay ship both with your suggestions."* Not a fork.
- ✅ **A mode is changed on its own feature panel and nowhere else** — one fact, one home for
  surfaces. The two exceptions are argued, not assumed: `Turn a feature back on…` exists
  precisely because the owning panel is unreachable, and the generic key card reaches every key
  by construction and cannot special-case sixteen of them.
- ✅ **Staff are re-checked before every move, reads included** (P8, pings deviation 10).
- ✅ **A control the caller may not use is not rendered**, and the embed says who it is for
  (P9). Never a bare status, never a dead button.
- ✅ **`Put the default back` works on every key, not just the 34 clearable ones.** The
  restriction was `CLEARABLE_KEYS` (`cogs/core.py:32`), never `store.clear`, and the recorded
  reason was *"`set-value` can reach it"* — which this build removes. Staff final say: a stored
  decision staff cannot leave is the state the rule forbids.
- ✅ **`automod_rules` gets no editor here.** `/automod` owns it; a 4000-character JSON modal
  is not a control.
- ✅ **The panel is a SECOND surface for keys the dashboard already owns, and that is
  mandated, not duplicated.** Checklist 33 requires two doors for every decision; retiring
  `set-value` with no panel replacement would BREAK the rule for 175 keys.
- ✅ **`/presence`'s loop, listeners and `loop_health` do not move** (P14 in spirit — the
  Health page reads them).
- ✅ **`set_key` takes no `via`**, argued in §F.

### Five questions are genuinely his

- **F-S1 — does `/settings set-value` survive, hidden and undocumented, for one release?**
  Nothing in Discord has ever met this panel; `set-value` is the insurance.
  - **(a) No — all five subcommands go in one commit. Recommended.** A hidden escape hatch is a
    second surface nobody documents and everybody eventually finds; it keeps a 175-key
    autocomplete alive; and every doc line in §E would have to be written twice — once now
    saying "it still works", once later deleting it. The risk it hedges (a key the panel cannot
    reach) is closed by the §G assertion that `set(KEY_TYPES)` equals the set of reachable
    keys. And it buys nothing measurable: `commands synced` does not move either way, because a
    Group was always one slot.
  - (b) Yes — keep it for one release as insurance while the panel meets live Discord. Cost:
    the sweep list stays half-rewritten, and the "way back" is documented two ways at once,
    which is the exact confusion this build exists to end.

- **F-S2 — does `Put the default back` on `staff_channel_id` need a confirm?** Measured: its
  default is `settings.test_channel_id` on every guild in every mode
  (`settings_store.py:1436–1437`), so one press silently disarms automod's and honeypot's
  arming gates and changes who counts as staff.
  - **(a) Yes, and only there — the press re-renders the card with *Are you sure?*, naming the
    channel it will become and what stops working. Every other key's reset stays one press.
    Recommended.** Access-INCREASING and blast-radius moves get confirmed; quiet ones fail
    safe — the same asymmetry pings shipped with (fork I1) and automod shipped with (F-A1).
  - (b) No reset for `staff_channel_id` at all; the card says it is changed by picking a
    channel. Safer in one sense and it creates exactly the terminal state the staff-final-say
    rule forbids.
  - (c) Confirm on every reset. Consistent and wrong: it puts a speed bump in front of undoing
    a mistake, which is the move somebody makes *because* something is broken.

- **F-S3 — who may edit the four core channel/role keys, and `operator_read_log`?**
  ⚠️ **Measured: this app has no "Lead" concept.** `store.is_staff` (`settings_store.py:1769`
  → `member_is_staff` `:1364–1368`) is `manage_guild` **or** a role that can see
  `staff_channel_id`; `/chat`'s spend block uses `administrator` (`cogs/content/chat.py:252`).
  Those are two different spellings of "above staff" and neither is called Lead. Today **any**
  staff member can re-point `staff_channel_id` — the key that decides who is staff.
  - **(a) `manage_guild`, behind the new bool `settings_core_keys_admin_only` (default
    `true`). Recommended.** It is access-REDUCING, so it fails safe; it adds no third concept
    (`member_is_staff` already treats `manage_guild` as automatic staff); and it closes a real
    escalation a panel makes one click easier than a slash command did.
  - (b) `administrator`, matching `/chat`. Stricter, and it makes "above staff" mean two things
    depending on which panel you are on.
  - (c) Plain staff — today's behaviour exactly, nothing renders differently, and the key stays
    at `false`. Cheapest and honest, but it ships a panel that makes an existing escalation
    easier to reach.

- **F-S4 — does presence live on `/settings`, or become its own `/presence` panel?**
  - **(a) On `/settings`, as `How Black Bloc looks…`, and the `presence` Group retires.
    Recommended.** Presence is two settings keys and one action — no mode, no logs command, no
    site page (`logkinds.py:47` files it under `core`, and `FEATURE_PAGES` has no presence
    entry). It is also what takes the estate to **29 top-level slots and ZERO
    `app_commands.Group`s**, which is the program's stated finish line.
  - (b) `/presence` becomes its own one-command panel. One more command in everybody's list for
    one button, and the estate lands at **30** with a group still in the tree unless it is
    flattened anyway.

- **F-S5 — does the panel get a `Log levels…` sub-panel, or do the 17 `<feature>_log_level`
  keys stay in the generic group path?** ⚠️ Measured: **no panel anywhere writes one**, so
  `/settings set-value` is their only Discord door today and it is going.
  - **(a) A sub-panel: one select over the 17 features, then the two levels it is not on.
    Recommended.** It is the one cross-cutting family a Lead actually tunes — the Discord log
    channel going noisy is the thing you fix from your phone — and the generic path costs a
    group pick, a key pick and a select for a three-way enum. It also costs one row on a root
    that has one free.
  - (b) No sub-panel; they are reachable through `A setting group…` like every other key.
    One less sub-panel to build and test; leaves the noisiest knob in the app three clicks deep,
    filed under `automod` for `mod_log_level` (a `NAMESPACE_OVERRIDE`, `settings_api.py:36`)
    where nobody will look for it.

---

## J. What NOT to build, and what this costs

**Not in this build:**

- **Any new API route or site control.** `settings.html`, `page-settings.js`, the command
  palette and the three `/api/settings` routes are untouched; `site/mock/contract.json` gains
  nothing. The only `settings_api.py` edit is the `namespace_of` **move** (§F) and the two new
  `CORE_KEYS` rows (§D).
- ⚠️ **Wiring `PUT /api/settings/{key}` through `set_key` with `via=VIA_WEBSITE`.** It is the
  right next pass and it is also what closes **KI-21** (*the website can arm automod past both
  arming refusals* — the generic settings route validates against `KEY_CHOICES` only, so no
  shared function's gate applies on the web path). It is a settings-API change with its own
  test surface, and doing it here would double-log unless the route's `note()` goes in the same
  commit. **Report it; do not start it.**
- **Anything inside `store.set` / `store.clear` / `default()` / `coerce_value` /
  `parse_value`.** The panel is a door. `parse_value` (`:1284`) may end up called only from the
  modals; leave it where it is and leave its tests alone.
- **A settings SEARCH across all groups.** `Find a setting…` filters inside one group, which is
  what `value_keys`' autocomplete did. A global search is a different control and a different
  25-cap problem.
- **Bringing back `/settings show`'s full 175-line dump.** Six ephemeral messages is what the
  panel replaces, not what it reproduces; the site owns the whole list and the panel links to
  it.
- **`count` / `important_only` on `Logs`.** Lost exactly as they were for `/request`, `/apply`,
  `/voice` and `/automod`; the site's Logs page has both.
- **Touching `HIDDEN_WHEN_OFF`, `NEVER_HIDDEN` or any visibility logic.**
  `tests/test_command_visibility.py` staying green with no edit is the proof.
- ⚠️ **REPORT, do not fix — five measured defects found while writing this.**
  1. **`namespace_of` produces six singleton groups from a naming mismatch** — `event`,
     `voice`, `memory`, `hide`, `emoji`, `cost` (§A). The dashboard's Settings page already
     shows them that way; the panel will inherit it. One rename pass of its own.
  2. **`sweeps.md:150` (row 16) names `/settings logs`, which has never existed** — measured
     against `cogs/core.py`. The row is being rewritten anyway, and after this build the
     command it names is finally real.
  3. **`code-notes.md` against `cogs/core.py:32` says the clearable list is "11 long";
     measured today it is 34** — over Discord's 25-choice cap, which is why that command
     autocompletes at all.
  4. **`LOG_LEVEL_COMMANDS` (`settings_store.py:783–797`) is mostly wrong.** Automod's
     deviation 9 measured eight of the thirteen remaining rows naming a retired subcommand;
     after wave 4 it will be **eleven of thirteen**, because honeypot, modmail and mod all lose
     their `logs` children. Every `<feature>_log_level`'s help text therefore points at a
     command that does not exist. One pass of its own — and it is exactly the kind of stale
     string a `Log levels…` sub-panel (F-S5) would put in front of somebody.
  5. **None of the five `/settings` subcommands checks the database** (§A) — `show` answers off
     the cache while the db is down and the three writers raise. The panel fixes this for the
     panel; nothing else in `cogs/core.py` needs it once they are gone, so it is a defect that
     the fix retires rather than one that survives.

**Cost.** Calibration from wave 3 and the last build: automod **370k**, chat **441k**,
raidtrain **473k**, role menus **529k**; hide-commands-when-off **185k**.

Sizing this one: **five subcommands, the fewest of any panel build** — but that number is
misleading, because what is being rewritten is not five commands, it is a **type-generic editor
over 175 keys with ten control shapes**, each needing its own render branch, its own refusal
and its own test. Against that: a **NEW pure module and a NEW test file** (the single biggest
cost automod avoided); a **513-line cog test whose `/help` half must not move**; a
**cross-cog retirement** (`/presence`, plus its 273-line test file); **21 string sites across 15
files** plus 4 mock copies and 5 test assertions — **the largest string sweep of the program**;
**~20 doc and sweep rows**; two new registry keys with their site rows; and one pure move
(`namespace_of`) that must leave `tests/api/test_settings_api.py` byte-identical.

**Estimate: 380–450k Opus tokens.**

Pushing it **up**: the ten control shapes and their edges — the `>25 default_values` refusal on
`channels`/`roles` (S7), the unproven `min_values=0` empty submit on `enums`, the rebuilt
bounds in every number modal (checklist 22); and the string sweep, three of whose sites are in
files **three sibling branches are rewriting right now** — that is merge risk more than token
cost, but it costs a careful, rebased final pass.
Pushing it **down**: no enforcement path to tiptoe around, no site route, no migration, no new
log kind, no `kind_via` work, and `tests/test_logkinds.py` and
`tests/test_command_visibility.py` both staying green untouched.

> ⚠️ **Split it in two.** 380–450k is above three of the four wave-3 builds and well above the
> ≥150k prep bar.
>
> | Dispatch | Scope | Estimate |
> |---|---|---|
> | **Build 1** | `black_bloc/settings_panel.py` + `tests/test_settings_panel.py`; the `namespace_of` move; `set_key` / `clear_key` / `reapply_presence`; the two registry keys + their site rows and store tests | **150–190k** |
> | **Build 2** | the panel itself, the `/presence` retirement, `tests/cogs/test_core.py`'s settings half, and the whole string + doc sweep | **230–280k** |
>
> Build 2 starts from Build 1's merge. Commit at each layer inside each build — the pure module,
> then the extractions, then the panel, then the sweep — so a kill costs the last layer rather
> than the build.

**Prep before dispatch** (per the ≥150k rule): a clean tree, a fresh usage read, and a brief
carrying `docs/info/review-checklist.md`, `docs/info/panels-program.md`, this file, and the
standing rule that **`git stash` is never run in a shared tree**.

⚠️ **Dispatch this AFTER all three wave-4 branches have merged, not beside them.** It retires
the last `Group` in the tree, its `tests/test_bot.py:179` assertion must be written against a
settled number, and two of its string sites are inside files those branches own.

---

## Build 1 deviations — what the build did differently, and why

> Written by the Build 1 agent on `worktree-agent-a3e6ccbead5a90537`, off `main` at `34331ec`,
> 2026-09-05. **Status: ✅ LIVE as v83** — merge `9a7c87e`, shipped at `57a878d`, deployed
> **2026-09-05 12:53** Phoenix (`../deploys.log`).
> (This line said *"BUILT, not merged, not deployed"* until 2026-09-11; it was stale from the merge
> onwards, and the page header already said SHIPPED.)
> `pytest` **4973 passed** (4739 on
> `main` before, +234), `ruff check .` clean, `node site/mock/check.mjs` **17 pages / 146
> routes** — unchanged before and after, and **150 routes** at v108 — and `node --input-type=module --check` clean on
> `site/public/assets/labels.js`. ⚠️ **Nothing has met live Discord** — no boot, no token, no
> sync, no panel opened, nothing deployed. Build 1 retires nothing: the `settings` and
> `presence` Groups and all six leaf subcommands still exist, and the top-level count is
> **30, unchanged and measured** through
> `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits`.

### ⚠️ The document's numbers were stale; these are the measured ones

| The design says | Measured on `34331ec` | Consequence |
|---|---|---|
| registry holds **175 keys** | **179** before this build, **181** after | every "175" in §§A–J is four low; `/mod` and modmail Build B each added keys after the doc was keyed |
| `tests/test_bot.py:179` asserts **36** top-level | the assertion is **30** and this build does not touch it | the header's arithmetic table is spent; Build 2 pins **29** off 30, not off 36 |
| `settings_store.py` is **1782** lines, `sweeps.md` last row **187** | **1844** and **230** | every `path:line` in the design was re-read by anchor, not trusted |
| 22 namespaces, `chat` the only one over 25 | **both confirmed**, and the six singleton groups (`event`, `voice`, `memory`, `hide`, `emoji`, `cost`) are real | §J defect 1 stands, unfixed |
| no `KEY_CHOICES` entry exceeds 25 | **confirmed** — the largest is `chat_personality` at 13 | the `enum` select never caps |
| 14 `*_panel_minutes` keys | **17**, and **18** with `settings_panel_minutes` | still one select, still under 25 |

### The deviations, numbered

1. **`clear_key` returns an `Outcome`, not a bare `bool`** (§F's table says `cleared: bool`).
   Both writers then have ONE shape, and a refusal gets words: an unknown key (400) and a key
   with nothing stored (409) are different answers and a bool can say neither. The bool survives
   as `Outcome.value`.
2. **`SettingsStore.is_stored(guild_id, key)` is NEW, and the design did not name it.** §C draws
   `Put the default back` only when `store.clear` would return `True`, and there was no way to
   ask that without doing it — `get()` answers with the default when no row exists, so a row
   written *at* its default is invisible to a value comparison. It is a read; nothing inside
   `set` / `clear` / `default` / `coerce_value` / `parse_value` moved, so §J's "not in this
   build" list is respected.
3. **`settings_api`'s own `CORE = "core"` was deleted** and `logkinds.CORE` imported in its place,
   in the same commit as the `namespace_of` move. Two spellings of one string in two modules is
   checklist 15, and the move would otherwise have left `namespace_of` reading one and `grouped`
   the other.
4. **The re-exports use the redundant-alias spelling** (`from ..settings_store import CORE_KEYS as
   CORE_KEYS`). `tests/api/test_settings_api.py` imports `CORE_KEYS` from `settings_api` and had
   to stay byte-identical; a plain import would have been ruff F401. It is, and it is green.
5. **`set_key`'s `details` is `{key, value, via}` for every type**, where the three bare copies
   wrote `{key, channel_id}`, `{key, role_id}` and `{key, value}`, and the `target=channel`
   argument is gone. Measured before unifying: nothing in the repo reads `channel_id` or
   `role_id` out of a `settings.set` row. One function cannot serve eleven control types with
   three detail shapes.
6. **`reapply_presence` resolves the cog itself** and returns `None` when it is absent, rather
   than the caller doing `bot.get_cog`. That is what keeps ONE implementation — `presence_apply`
   now calls it, so the surviving command and Build 2's button cannot drift. ⚠️ It cost two
   lines in `tests/cogs/test_presence.py`: `FakeBot` gained a `get_cog` and the `cog` fixture
   registers itself. **No assertion changed**, which is still the proof the loop and the
   listeners did not move.
7. **Seven tests for `set_key`/`clear_key` were added to `tests/cogs/test_core.py`**, which the
   brief listed under Build 2. The tests-mirror rule leaves nowhere else for them, and a shared
   writer with no test is half-built. Nothing existing in that file was edited — the settings
   half and the whole `/help` half are untouched, which is what Build 2 needs.
8. **`VALUE_KEYS` was NOT moved** out of `cogs/core.py` (§E says it is kept and moved). It is
   still the autocomplete's source and `/settings set-value` still exists in Build 1; the new
   store tests assert against it exactly as the fourteen shipped `*_panel_minutes` tests do.
   The move belongs with the command's retirement, in Build 2.
9. **The commit order is the dependency order**, not the brief's suggested order: the
   `namespace_of` move and the two registry keys land BEFORE the pure module, because the module
   imports both.
10. **The pure module carries the button tables**, not just the render data — `root_buttons`,
    `roles_channels_buttons`, `looks_buttons`, `panels_commands_buttons`, `log_levels_buttons`,
    `level_buttons`, `group_buttons`, `key_card_buttons`. P3 says the table is DATA and §G asks
    for the `PANEL_MOVES` distinctness test, so they are Build 1's; Build 2 renders them.
11. **One `BACK_MOVE`, reused with `_replace(row=…)`**, rather than a `BACK` constant per
    sub-panel. Six moves sharing one action would break the distinctness test that exists to
    catch a real collision.
12. **The two new mock rows carry `max: 1440`, copying their fourteen siblings** — and the real
    registry has **no** `KEY_MAX` for any `*_panel_minutes` key. The divergence is pre-existing
    and fourteen rows deep; a lone row without it would read as an oversight. Reported below,
    not fixed.
13. **`site/mock/server.mjs`'s own `CORE_KEYS` gained both keys too.** It is a second, shorter
    copy of the API's list (three entries against six) and would otherwise have grouped them
    under a `settings` namespace the real API does not have. The pre-existing three-vs-six
    divergence is reported below, not fixed.

### Sweep rows — Build 1 has almost none, and that is the point

⚠️ **Every row in §H (S1–S12) needs the PANEL, so all twelve belong to Build 2.** Build 1 adds
no control, retires no command and changes no string a person reads in Discord. Two rows are
visible, both on the website, and are lettered for the conductor to number:

| # | Do this | Expect |
|---|---|---|
| SB1 | dashboard → **Settings** → the **core** group | two new rows at the bottom of it: **How long the /settings panel stays live** (10) and **Whether only a Lead may re-point the staff and log channels** (true). ⚠️ They must be under **core**, not under a group called `settings` — that is what `CORE_KEYS` is for |
| SB2 | set **How long the /settings panel stays live** to `0`, then to `10` again | `0` is refused in words by the same validator every other panel-minutes key uses, and nothing is saved. There is no Discord door onto either key yet — `/settings set-value settings_panel_minutes 15` is the only one until Build 2 |

### Found while building, REPORTED and not fixed — three beyond §J's five

⚠️ §J's five all stand, re-measured: the six singleton namespaces are real; `sweeps.md` row 16
still names a `/settings logs` that has never existed; `code-notes.md` against `cogs/core.py:32`
still says the clearable list is "11 long" and it is **34**; `LOG_LEVEL_COMMANDS` is now wrong in
**eleven of thirteen** rows because honeypot, modmail and `/mod` all lost their `logs` children;
and none of the five `/settings` subcommands checks the database. Three more:

1. **The mock's `*_panel_minutes` rows claim `max: 1440`; the real registry has no `KEY_MAX` for
   any of them.** Sixteen rows now (the fourteen shipped ones plus this build's two, which copied
   their siblings deliberately). The dashboard renders a bound the API never sends. One pass to
   decide which half is right — a real ceiling in `KEY_MAX` would be the better answer, since a
   panel-minutes key over 15 already loses the gone-quiet footer.
2. **`site/mock/server.mjs`'s `CORE_KEYS` is a second, shorter copy of the API's** — three entries
   against six, so the mock groups `bot_bio`, `status_prefix` and `operator_read_log` under
   `bot`, `status` and `operator` while the real API files all three under `core`. This build
   added both new keys to each list to keep them agreeing; the three-key gap is older and was
   left alone.
3. **`cogs/community/birthdays.py:428` is a FOURTH emitter of `settings.clear`**, and it passes no
   `via` at all — so a birthday role cleared by that path records neither Discord nor the website.
   It is outside the panel's door and outside this build's scope; it should call `clear_key` when
   Build 2 has landed it.
4. ⚠️ **`tests/api/test_writes.py::test_another_session_is_not_slowed_down_by_this_ones_reads` is a
   WALL-CLOCK RACE, and this build's extra load is what surfaces it.** Measured: it failed **2 of
   4** full `pytest -n auto` runs on this branch and **0 of 2** on the base `01c4ed3`, and passes
   every time `tests/api/test_writes.py` runs alone. Root cause, read out of
   `api/auth.py:TokenBucket.take`: the bucket refills **continuously** at `limit / window` = 300/60
   = **5 tokens a second**, and `drain_reads` empties it with a 300-iteration Python loop. Any
   loaded machine where that loop plus the assertion takes more than **0.2 s** regains a token, so
   the `== 429` assertion sees a 200. Nothing in this build touches the rate-limit path; +234 tests
   only made the box busier. The fix is in the test, not the code — drain until `take` returns
   `False` (or pass the frozen `now=` the method already accepts) instead of counting to
   `READ_RATE`. **Not fixed here**: it is another build's file and the deploy gate is the
   conductor's. ⚠️ It WILL flake `scripts/deploy.ps1`, so a retry there is expected, not a signal.

### What Build 2 inherits

- **`black_bloc/settings_panel.py`** — public names in its `__all__`. The render data is
  `root_lines`, `mode_lines`, `hidden_line`, `stored_count`, `key_card_lines`,
  `default_sentence`, `confirm_lines`, `bounds_line`; the option builders are `groups`,
  `keys_in`, `editable_options`, `needs_find`, `back_on_options`, `log_level_options`,
  `panel_minutes_options`, `level_moves`; the tables are `control_for`, `has_editor`,
  `editor_move`, `toggle_label`, `may_edit_core_keys`, `list_is_too_long`, `needs_confirm`,
  and the eight `*_buttons` functions; the panel plumbing is `PANEL_TITLE`,
  `PANEL_TIMEOUT_FOOTER`, `PANEL_MINUTES_KEY`, `panel_minutes`, `site_page_url`.
- **The writers**: `cogs.core.set_key(bot, guild, key, value, actor) -> Outcome`,
  `cogs.core.clear_key(bot, guild, key, actor) -> Outcome` (`.value` is whether a row was
  there), `cogs.presence.reapply_presence(bot) -> str | None` (`None` = cog not loaded).
- **`store.is_stored(guild_id, key)`** is what `Put the default back` renders on.
- **The registry keys**: `settings_panel_minutes` (int, 10) and
  `settings_core_keys_admin_only` (bool, true), both in `CORE_KEYS`.
- **The trap**: `tests/api/test_settings_api.py` must stay byte-identical through Build 2 as
  well — it is the only thing proving the web door did not move.

---

## Build 2 deviations — what the build did differently, and why

> Written by the Build 2 agent on `worktree-agent-a56c7b5137d9a609d`, off `main` at `57a878d`
> (Build 1 merged as `9a7c87e`), 2026-09-05. **Status: ✅ LIVE as v84** — merge `ce97de0`, deployed
> **2026-09-05 13:44** Phoenix (`../deploys.log`), boot `synced 29`. (This line said *"BUILT, not merged, not
> deployed"* until 2026-09-11; it was stale from the merge onwards, and the page header above it
> already said SHIPPED.)
> `pytest` **5002 passed** (4973 on the base, +29), `ruff check .` clean,
> `node site/mock/check.mjs` **17 pages / 146 routes** — unchanged before and after, and **150
> routes** at v108 — and
> `node --input-type=module --check` clean on `site/public/assets/labels.js`.
> ⚠️ **Nothing has met live Discord** — no boot, no token, no sync, no panel opened, nothing
> deployed. What Build 2 retires: `/settings show|set|set-role|set-value|clear` and the whole
> `presence` Group. **Top-level 30 → 29 with ZERO `app_commands.Group`s left**, measured
> through `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits`, which now
> asserts both numbers in one place.

### The numbers, re-measured on `57a878d`

| Build 1 measured | Build 2 measures | Consequence |
|---|---|---|
| registry **181** keys after Build 1 | **181**, unchanged — this build adds no key | every "175" in §§A–J is six low; the panel's own tests count `KEY_TYPES` rather than a literal. **202 at v108** — see the header |
| `tests/test_bot.py` pins **30** | **29**, and there are **0** `app_commands.Group`s | the design's arithmetic table predicted exactly this, and the delta off 30 is exactly 1 |
| 22 namespaces, `chat` the only one over 25 | **both still true**; `chat` is **28** | `capped_placeholder` fires exactly once in the app, on `chat` |
| `CLEARABLE_KEYS` was **34** | **all 181** keys are now clearable | §I's settled item; `store.clear` never had a type restriction |
| `LOG_LEVEL_COMMANDS` wrong in **11 of 13** | **17 of 17 correct**, `core` added | §J defect 4, fixed rather than reported |

### The deviations, numbered

1. **The layer split in the brief is not expressible, and one commit is the honest shape.** The
   brief asked for (1) "the panel views + the `/settings` command opening it, subcommands still
   present" and then (2) "retire the five subcommands". ⚠️ **A tree cannot hold an
   `app_commands.Group` named `settings` and an `app_commands.command` named `settings` at the
   same time**, so the swap is atomic. It landed as one commit; the top-level count stays 30
   through it, and the −1 arrives in the next commit with `/presence`, exactly as the brief's
   pinning instructions expected.
2. **`tests/test_command_visibility.py` needed a REAL edit, not only the two docstrings.** §G
   and the brief both say it stays green with no edit as proof the visibility logic did not
   move. It could not: `test_every_hidden_feature_can_still_be_turned_back_on_from_discord`
   **imported `cogs.core.VALUE_KEYS`**, which this build deletes. The behaviour assertions are
   untouched; the membership test became `settings_panel.reachable_on_the_panel(key)`, which is
   the same claim about the surface that replaced it. **No visibility logic changed**, and the
   rest of the file is byte-identical.
3. **The same import forced 31 rewrites in `tests/test_settings_store.py`**, where the design
   named only `:992`. Every `*_panel_minutes` and every `bool`-key test asserted checklist 33 as
   `key in VALUE_KEYS`. They are all `reachable_on_the_panel(key)` now, and `:992` itself became
   the stronger set-equality the design asked for:
   `test_every_registry_key_is_reachable_from_the_panel_as_well_as_the_dashboard` asserts the
   panel's reach **equals** `KEY_TYPES` and that the no-editor set is exactly `{automod_rules}`.
4. **`settings_panel.reachable_on_the_panel` was ADDED to Build 1's `__all__` contract.** It is
   two lines over `keys_in`/`has_editor` and exists for those 31 assertions; nothing in the
   panel calls it. Adding rather than importing both halves at 31 sites keeps the claim in one
   place.
5. **No confirm helper was built, and nothing goes to the conductor.** §F says fork F-S2 makes a
   fourth hand-rolled `open_confirm` and asks the build to hand it over. It turned out
   unnecessary: Build 1 already returns `key_card_buttons(confirming=True)` and `confirm_lines`,
   so the confirm is the **same card re-rendered in a confirming state** — no new view, no new
   `panels.py` helper. ⚠️ **The three existing hand-rolled copies (`youtube.open_confirm`,
   pings deviation 8, automod deviation 12) are still three copies**; this build did not add a
   fourth and did not fold them in either. Still the conductor's.
6. **The number modal's bound is a compact label of its own, not `bounds_line`.** §C says the
   bound is rebuilt where the value enters (checklist 22). `settings_panel.bounds_line` is prose
   for the embed — *"It takes a whole number no larger than 10000."* — and a Discord `TextInput`
   label is capped at **45 characters**, so it truncated mid-sentence. `cogs.core.number_label`
   is the compact spelling (*"A whole number, no more than 10000"*); the embed keeps the
   sentence, and `coerce_value` is still the backstop answered verbatim.
7. **`set_key` and `clear_key` gained `via: str = VIA_DISCORD`**, which Build 1 argued against
   and the brief required. It is not dead weight any more: `birthdays.clear_role` calls
   `clear_key` (deviation 8) and the website's route can reuse both without a signature change.
   ⚠️ **The route is NOT wired** — design §J says report, do not start — so `PUT`/`DELETE
   /api/settings/{key}` still call `store.set`/`store.clear` and `note()` themselves, and
   **KI-21 is still open**.
8. **`birthdays.clear_role` now calls `clear_key` and keeps its own words.** The brief allowed
   reporting instead if a logged shape a test pins would change; the tests pin the KIND
   (`["settings.clear"]`), not the details, so the fix landed. The row gains `"via": "discord"`,
   which it never had. The words did NOT move to `CLEARED`/`NOT_SET`: *"a role somebody already
   has for today still comes off tomorrow"* is birthday-specific and would be lost. ⚠️ This is
   the first `cogs/community/* → cogs/core` import in the tree; it imports a module-level
   FUNCTION, not a cog, so the "cogs never import each other" rule (`architecture.md` rule 2) is
   not what it would be if it reached for a `Cog` instance — **flagged for the reviewer**.
9. **`LOG_LEVEL_COMMANDS` was FIXED, not reported.** The brief put it in the string sweep. All
   seventeen `logkinds.FEATURES` now map to the command that exists, `core` included (this build
   gives `/settings` its **Logs** button), and the help clause reads *and in `/x` ▸ **Logs***.
   Two rows were wrong independently of the panels program: `pings → pingroles` and
   `applications → applications`, neither of which has ever been a command name.
10. **`test_every_feature_group_has_a_logs_command` was re-expressed, not repurposed and not
    deleted.** ⚠️ `LOGS_GROUPS` was **already `{}`** on the base commit, so the test iterated
    nothing and its sibling `test_a_logs_command_is_staff_only_and_ephemeral` asserted **nothing
    at all**. The guarantee is now: zero Groups in the tree, and an AST walk of `black_bloc/`
    proving every feature in `FEATURES` is the argument of a `send_logs` call. The staff-gate
    half is a direct check that `send_logs` calls `require_staff`, which is where that gate
    lives now that no `logs` subcommand exists. `LOGS_GROUPS` is deleted; `RETIRED_GROUPS`
    replaces it as the list of names that must never come back.
11. **The design's S1–S12 are 12 rows, and the confirm moved into S11.** §H's S11 covered both
    the `manage_guild` absence and `staff_channel_id`'s default sentence; the F-S2 confirm is
    the natural third clause of the same row, so S12 stayed the log-levels/Logs/timeout row and
    the count is exactly 12 as the brief asked.
12. **Eighteen numbered `sweeps.md` rows were rewritten in place, not the fifteen §E listed.**
    §E named 16, 53, 65, 67, 68, 71, 83, 95, 108, 130, 156, 174, 184, 185, 186. Measured today,
    **103, 197 and 199** also name a retired subcommand, and so do four prose blocks (Phase 1,
    Phase 2, Phase 5 and the chat-memory preamble). All of them are rewritten. Row 16's
    `/settings logs` (§J defect 2) is called out in the row itself, because after this build the
    command it names is real for the first time.
13. **Three code sites the design did not list, and two it listed at moved line numbers.**
    Measured by grep on `57a878d`: `black_bloc/honeypot.py` (`MODE_IS_OFF_WAY_BACK`), and
    `cogs/moderation/modmail.py` at **two** sites (the design predicted one, at a line honeypot's
    and modmail's own builds have since moved). `cogs/moderation/honeypot.py:81` — which the
    design flagged as "being rewritten right now" — no longer names `/settings` at all; the
    string moved to `black_bloc/honeypot.py`. Full list in the report.
14. **`docs/info/panels-program.md` and `docs/info/feature-list.md` were NOT touched.** §E's doc
    table asks for four rows in the first and one clause in the second. The brief's scope list
    ("do this and nothing more") enumerates the sweep targets and names neither. ⚠️ **They are
    therefore stale**: `panels-program.md` still asks fork F3 as an open question, still says
    "~120 keys", and its Core row and totals line still describe a `settings` Group. Left for
    the conductor with `docs/info/README.md`.
    🟢 **The conductor did it.** Re-measured 2026-09-11: `panels-program.md` answers F3 (*"the paged
    panel"*), its Core row says v84 / zero Groups, and it carries a measured key count;
    `feature-list.md` has its `/settings` row. Neither is stale on this build's account.
15. **`docs/TODO.md` and `docs/DONE.md` were not touched either**, for the same reason — the
    brief's scope list does not name them and the conductor moves the item at the merge.
16. **Nothing was accepted into `docs/KNOWN_ISSUES.md`.** No defect found here is being
    tolerated: the two that survive (KI-21's route wiring, and the three hand-rolled confirms)
    are both explicitly *"report, do not start"* work with a named owner, not accepted defects.

### Found while building, REPORTED and not fixed

1. 🟢 **CLOSED at v89** (engineering sweep, 2026-09-05, the same day) — the one commit described
   below was written: `api/settings_api.py` now does `from ..cogs.core import NOTHING_STORED,
   clear_key, set_key` and calls both with `via=VIA_WEBSITE`, its own `note()` is gone, and KI-21
   has been moved whole to [`../DONE.md`](../DONE.md). Re-measured 2026-09-11. The original report:
   ⚠️ **KI-21 is still open and the keyword to close it now exists.** `set_key`/`clear_key` take
   `via`; `api/settings_api.py` still writes through `store.set`/`store.clear` and `note()`s
   `web.settings.set`/`web.settings.clear` itself. Wiring the route through the shared writers
   with `via=VIA_WEBSITE` and deleting its `note()` is one commit, closes KI-21 (the website can
   arm automod past both arming refusals, because the generic settings route validates against
   `KEY_CHOICES` only) and satisfies checklist 34 by function rather than by separation.
   ⚠️ `tests/api/test_settings_api.py` is byte-identical through both builds and is the thing
   that will tell you whether the wiring changed the web door's behaviour.
2. ⚠️ **`tests/api/test_writes.py::test_another_session_is_not_slowed_down_by_this_ones_reads`
   is still the wall-clock race Build 1 measured.** It did **not** fail on any of the five full
   `pytest -n auto` runs on this branch, which is luck rather than a fix — the bucket still
   refills at 5 tokens a second and `drain_reads` still counts to `READ_RATE` in Python. Build
   1's diagnosis and fix stand.
3. **The six singleton namespaces are unchanged and now visible on a Discord control.** `event`,
   `voice`, `memory`, `hide`, `emoji`, `cost` each hold one key, and `A setting group…` lists
   all six beside `events`, `tempvoice` and `chat`. It reads as a naming bug because it is one
   (§J defect 1); the panel inherits the dashboard's grouping deliberately, so a rename pass
   fixes both surfaces at once or neither.
4. **`tests/cogs/test_presence.py` and `tests/test_bot.py` cannot share a process cleanly.** Run
   in one `pytest` invocation, `test_bot.py`'s real `BlackBlocBot` starts the presence loop and
   the fake-bot presence tests then see its `change_presence` calls. It does not bite under
   `-n auto` (xdist distributes by file) and both files pass alone and in the full run. It is
   pre-existing — the loop has always started on `load_extension` — and nothing in this build
   touches it.
5. **`black_bloc/cogs/community/birthdays.py` importing `black_bloc/cogs/core.py` is the first
   cog-package-to-cog-package import in the tree.** It is a module-level function and creates no
   cycle, but `architecture.md` rule 2 says cogs never import each other and a reviewer should
   decide whether `set_key`/`clear_key` want a home outside `cogs/` before a second feature does
   the same thing.
