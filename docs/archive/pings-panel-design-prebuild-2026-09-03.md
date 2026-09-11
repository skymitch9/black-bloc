# Ping-roles panel design — the pre-build sections (§A, §E, §G, §H), 2026-09-03

> ⚠️ **RETIRED 2026-09-11.** These four sections of
> [`../info/pings-panel-design.md`](../info/pings-panel-design.md) were written BEFORE the `/pings`
> panel was built (v72, 2026-09-03) and describe what was there to replace: §A measures the two
> command groups and twelve subcommands that existed that morning, §E lists every string and doc
> line that named them, §G is the test plan and §H the prove-before-merge list with its sweep rows.
> The commands they name (`/pingroles …`, `/pings list|follow|unfollow …`) are gone; the sweep rows
> §H numbers as 104–114 were renumbered **126–134** at the build (deviation 13). Nothing here is a
> current reading — kept for the reasoning. **Replaced by** the live doc's §B–§J plus its
> `## Deviations` foot, which say what shipped. Commit `8426b1a` had deleted the whole body; the
> spec half was restored 2026-09-11 and this half archived, per the owner (*"Restore it"*).

## A. Measured today — two groups, twelve subcommands

`pingroles` is a `Group` (`cogs/content/pings.py:98`, `default_permissions=STAFF_ONLY`) with a nested
`streamer` group (`:103`); `ping` is a `Group` named **pings** (`:106`, member-visible, no
`default_permissions`) with nested `events` (`:107`) and `fans` (`:110`) groups. **5 + 7 = twelve
leaf subcommands over two top-level slots.**

| Subcommand | Line | Who | Calls · what is INLINE in the cog |
|---|---|---|---|
| `/pings follow <streamer>` | `:181` | member; `_ready` `:114` + `_on` `:124`; autocomplete `_streamer_choices` `:143` | `_follow` `:199` — ⚠️ **all inline** `:204–234`: `_wanted_streamer` `:159`, `role_of` `:79`, `wears` `:83`, `pings.wear` (`pings.py:260`), the sentence, `log_action("pings.follow")` |
| `/pings unfollow <streamer>` | `:190` | member | the same `_follow` with `adding=False` |
| `/pings list` | `:236` | member; ⚠️ **`_on` is NOT asked** — reading works with the mode off | `pings.events_role_id` (`pings.py:468`), `all_fan_roles` (`:182`); ⚠️ **lines built inline** `:242–259`, paged by `_pages` `:136` |
| `/pings events on\|off` | `:262` `:266` | member | `_events` `:270` — ⚠️ **all inline** `:274–300`: unset / gone refusals, `wears`, `pings.wear`, sentence, `log_action("pings.events_on")` |
| `/pings fans on` | `:302` | member | ⚠️ **inline** `:307–316`: `CREATION_KEY == STAFF` gate, `_streams` `:331`, then `ensure_fan_role` (`pings.py:362`) — shared |
| `/pings fans off` | `:318` | member | ⚠️ **inline** `:323–329`: `get_fan_role` guard (`FANS_OFF_NONE` `:67`), then `remove_fan_role` (`pings.py:410`) — shared |
| `/pingroles setup [role]` | `:337` | `require_staff` `:344`; allowed with the mode OFF (`code-notes.md:4540`) | `setup_events_role` (`pings.py:489`) — shared, nothing inline |
| `/pingroles streamer add <member> [role]` | `:356` | `require_staff` `:364` | `ensure_fan_role(…, staff=True)` — shared; `staff=True` is the ONLY way past mode off (`code-notes.md:4536`) |
| `/pingroles streamer remove <member>` | `:381` | `require_staff` | `remove_fan_role` — shared |
| `/pingroles streamer list` | `:398` | `require_staff` | `all_fan_roles`; ⚠️ **lines inline** `:410–418` (`STREAMER_LINE` `:74`, `followers_word` `:87`) |
| `/pingroles logs` | `:421` | `send_logs` carries its own `require_staff` | `send_logs(interaction, "pings", count, important_only)` |

**Not subcommands and NOT moving** (P14, program §7): the auto-maintained **Streamer pings** role-menu
panels (`streamers`, `streamers-2`, … — `sync_streamer_menus` `pings.py:314`) and the **Notifications**
panel (`ensure_notifications_menu` `:472`). Those are `DynamicItem` posts that belong to the room and
survive restarts. The ephemeral panel is a SECOND door onto the same rows and the same helpers.

**There is no state machine.** Unlike every wave-1 feature, `golive_fan_roles` has no `status`
column and `pings.py` has no `TRANSITIONS`. The state a button renders from is a **tuple of
booleans**, not a status word — §C says which — so §G's parametrised test is over that tuple. A
builder looking for `TRANSITIONS` will not find one; that is correct, not a gap.

**The shared layer is ALREADY pure.** `black_bloc/pings.py` holds the store, the role calls, the two
`Outcome` paths and the menu sync, and `api/tools/pings.py:8` imports it from there — the opposite of
events, whose expensive half was moving the layer out of its cog. **No move is part of this build.**

## E. What goes away, and every line that names it

`/help` reads the tree (`cogs/core.py`), so it follows with no edit (P15). `HIDDEN_WHEN_OFF`
(`command_visibility.py:16`) has **no** pings entry today — measured — so nothing there changes.

| Thing | Where | Becomes |
|---|---|---|
| `pingroles` Group + `streamer` Group + 5 children | `:98`, `:103`, `:337`, `:356`, `:381`, `:398`, `:421` | the Streamers sub-panel, the streamer card, the role-pick step, `Set up the Events role`, `Logs` |
| `ping` Group + `events` + `fans` Groups + 7 children | `:106`, `:107`, `:110`, and the §A table | `@app_commands.command(name="pings")` + the buttons and selects of §B/§C |
| `_streamer_choices` `:143` · `_wanted_streamer` `:159` · `CHOICE_LIMIT` / `NAME_LIMIT` `:25` | — | **deleted with the autocomplete.** A select carries the `user_id` as its value, so the "somebody typed a display name" second try (`code-notes.md:4550`) has no caller. `NO_SUCH_STREAMER` `:32` survives only as the stale-select refusal |
| `_say` `:130` · `_pages` `:136` | — | `panels.answer`; the embed replaces the paged list. ⚠️ `pages_under_limit` keeps its `/rolemenu showall` and `/help` callers — do not delete it |
| `LOGS_GROUPS["pingroles"]` | `tests/test_bot.py:21` | **deleted** — `/pings` is not a `Group` with a `logs` child, so `:175` and `:221` would `KeyError` |
| `STAFF_COMMANDS` `"pingroles"` | `tests/test_bot.py:40` | **deleted**; `MEMBER_COMMANDS` `"pings"` (`:65`) stays |
| `assert len(top) == 42` | `tests/test_bot.py:198` | **one lower than whatever the build measures** — never a hard-coded absolute (§B) |

**Strings that name a retired subcommand and are rewritten in the SAME commit** — each currently tells
somebody to run something that will not exist. In `black_bloc/pings.py`: `:53` `NO_EVENTS_ROLE`, `:58`
`EVENTS_ROLE_GONE`, `:77` `NOT_A_STREAMER`, `:82` `STAFF_ONLY_CREATION`, `:87` `ALREADY_HAS_ONE`,
`:91` `NO_FAN_ROLE`, `:95` `CREATED`, `:100` `REUSED`. In `cogs/content/pings.py`: `:28` `:32` `:36`
`:39` `:43` `:48` `:52` `:55` `:58` `:63` `:65` `:67` `:70`. ⚠️ **Leave alone**: the `/rolemenu post`
half of `CREATED` `:95` and `SETUP_MENU_ADDED` `:119` (role menus is wave 3), the
`/settings set-value` half of `OFF` `:49` and `SETUP_STILL_OFF` `:121` (fork F3, wave 4), and the
`/twitch link` half of `NOT_A_STREAMER` `:77` (golive/twitch is a **sibling wave-2 build** — say
`/twitch link` and let the conductor reconcile).

⚠️ **`black_bloc/personas.py:80–82` is the chat bot's own answer** to "how do I get SuperNamu's
pings?" and names four dead subcommands (`/pings follow`, `/pings events on`, `/pings fans on`,
`/pings list`). Rewrite it to `/pings` and the panel's buttons — this is the applications build's
`personas.py:95–96` finding in the same place.

**Site strings** (no route changes; `api/tools/pings.py` is untouched): `settings_store.py:487`
(`pings_events_role_name` help names `/pingroles setup`) and `:491–492` (`pings_fan_role_creation`
help names `/pings fans on` and `/pingroles streamer add`), with their byte-mirrors in
`site/mock/server.mjs:299` and `:300`; `site/public/assets/page-golive.js:188` ("their own with
/pings fans on"); the mock's refusal strings `server.mjs:2618`, `:2638–2639`, `:2648`.
`page-golive.js:184` ("or with /pings") is still TRUE — leave it.

**Docs rewritten in the same commit** (P15): `docs/access/sweeps.md` rows **38–42** (`:96–100`)
rewritten in place, not added to; `docs/info/feature-list.md:52`; `docs/info/architecture.md:192–193`;
`docs/info/cutover-plan.md:43`; `docs/info/phase15-design.md` gets a dated "superseded by the panel"
line at the top, **not** a rewrite (its `:49`, `:63`, `:97–104`, `:117–121`, `:161–171`);
`docs/info/panels-program.md:79` (the Ping roles row → shipped); `docs/info/code-notes.md` re-keyed at
the merge — the pings sections at `:4523`, `:4543`, `:4561`, and specifically `:4548` (the
`ping`-vs-`pings` attribute trap, whose Group goes), `:4549` (`pages_under_limit`, whose `/pings list`
caller goes) and `:4550` (the typed-name second try, deleted). ⚠️ **`docs/access/OWNER_GUIDE.md` names
none of them** — measured, zero matches for "ping"; only its sweeps count (`:71`, "95 rows") moves.

## G. Tests (P16 — one file per source file, mirrored paths)

| File | What it gains |
|---|---|
| `tests/cogs/content/test_pings.py` (27 today) | `/pings` answers ephemerally with a panel; a member sees the two follow selects and the two toggles and **no** `Streamers…` / `Settings` / `Logs` / `Open on the site`; staff see all of it, **including with `pings_mode` off**; **parametrised over every row of §C's table — the panel renders exactly its row and no other**; each button calls its shared function with `via` untouched (mock it); `Stop following…` renders with the mode off and `Follow a streamer…` does not; a select capped at 25 says so **and names the Streamer pings panels, not the site**; the streamer card's `Make the role again` appears only when the role is gone; the role-pick step writes with and without a role picked; `Names…` echoes the rendered template and a broken one falls back visibly; `Logs` answers a NEW followup and still refuses a demoted staffer; a staffer demoted mid-card moves nothing (`still_staff`, every site); `db_ready` after a defer; timeout disables every item and a re-render `retire`s the view it replaced |
| `tests/test_pings.py` (36) | every new pure function in §F; `panel_buttons` over the whole state tuple; `notification_lines` / `streamer_lines` / `counts_of` / `panel_minutes`; `follow_streamer` and `set_event_pings` each leave exactly ONE log row with the right kind (assert the COUNT, not just the kind — checklist 34) |
| `tests/test_settings_store.py` | `pings_panel_minutes` round-trips, defaults 10, is in `KEY_TYPES` and has `KEY_HELP` |
| `tests/test_bot.py` | `LOGS_GROUPS` loses `pingroles`; `STAFF_COMMANDS` loses `pingroles`; `MEMBER_COMMANDS` keeps `pings`; the tree-limit test **recounts** |
| `tests/api/tools/test_pings.py` (16) | ⚠️ **unchanged** — no route moves and no route is added. Unchanged assertions are the proof the refactor changed nothing (wave-0 deviation 4) |

The existing shared-function tests (`ensure_fan_role`, `remove_fan_role`, `setup_events_role`,
`sync_streamer_menus`, the 26-row paging, `announced_fan_role`) **stay green untouched.**

## H. §J — prove before merge (P17), and the sweep rows

1. `python -m black_bloc` boots; **read `commands synced` and record both numbers** — the drop must be
   exactly one for this feature. With no token, measure it the only other way:
   `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits` counts the real tree
   (events deviation 13, applications deviation 11).
2. The parametrised state test: every row of §C renders its buttons and no other.
3. `python -c "import black_bloc.pings, black_bloc.cogs.content.pings, black_bloc.api.tools.pings,
   black_bloc.cogs.content.golive, black_bloc.cogs.content.youtube, black_bloc.personas"` — the boot
   substitute (wave-0 deviation 5). ⚠️ `golive.py` and `youtube.py` are in the list on purpose: both
   `from ... import pings`, and §F's cycle trap is exactly what this catches.
4. `ruff`; full `pytest`; `node site/mock/check.mjs` (the route count is **unchanged** — this design
   adds no route); `node --input-type=module --check < site/public/assets/labels.js` (⚠️ that file
   failed to parse once — `code-notes.md:5008`).
5. Checklist sweep before reporting — **8**, **11** (a fan role must never be mentioned in a panel
   reply — phase15 §Guard rails), **12**, **15** (the five `site_page_url` copies, §F), **17** (the
   template fallback, `pings.py:143`), **22**, **29** (the empty `RoleSelect` submit checked against
   the installed source, not guessed), **30**, **33** (§D), **34** (assert the log-row COUNT).

**Sweep rows — this feature takes 104 onward** (`docs/access/sweeps.md`'s last written row is **102**;
**103 is already claimed**, so start at 104 and **renumber at landing** if a sibling wave-2 branch got
there first). Rows **38–42** (`:96–100`) are rewritten in place, not added.

| # | Do this | Expect |
|---|---|---|
| 104 | `/pings` as a plain member with the mode ON | ONE ephemeral panel: your pings written out, **Follow a streamer…**, **Stop following…** if you follow one, the Events toggle, the fan button, **Refresh** — and no Streamers…, no Settings, no Logs, no site link |
| 105 | **Follow a streamer…** → a name, then **Stop following…** → the same name | the role goes on and comes off; the panel re-renders each time; `/pingroles logs`' successor shows `pings.follow` then `pings.unfollow`, one row each |
| 106 | Press the Events toggle twice | the role goes on and off; with the Events role NOT set up, there is no toggle at all and the panel says staff have not made it yet |
| 107 | As a linked streamer press **Start my own ping role**, then **Take my ping role away** → **Keep it**, then again → **Yes** | the role is made and appears on the **Streamer pings** panel; Keep it changes nothing; Yes removes it and the panel loses it |
| 108 | With `pings_mode` **off**: `/pings` as a member who follows somebody | the panel still opens, says ping roles are off, offers **no** Follow control — but **Stop following…** still works and takes the role off |
| 109 | `/pings` as a Lead | adds **Streamers…**, **Set up the Events role**, **Settings**, **Logs**, **Open on the site** — Logs answers a NEW message and the panel stays |
| 110 | **Set up the Events role** → leave the role picker empty → confirm; then again, picking an existing role | the first makes or reuses **Events** and points both feeds at it; the second reuses the one you picked; the reply says which, and says "still off" while the mode is off |
| 111 | **Streamers…** → **Give somebody a ping role…** → pick a member, leave the role picker empty → **Make the role**; then pick them on **A streamer…** → **Remove their ping role** → **Yes** | identical to `/pingroles streamer add` / `remove`: the role is made from the template, the Streamer pings panel refreshes, removal deletes the Discord role (`pings_fan_role_delete`) |
| 112 | Delete a streamer's role by hand in Server Settings, then open their card | the card says the role is gone and shows **Make the role again**; pressing it makes a fresh one and the panel picks it up |
| 113 | **Settings** → flip **Mode…**, flip **Who may start one…** to *staff*, open **Names…** and type `{game} pings` | the lines update; the template box shows what it will actually produce and refuses to pretend a broken one worked; with *staff* set, a member's **Start my own ping role** is gone and the panel says why |
| 114 | Leave the panel alone for `pings_panel_minutes` minutes | every button greys out and the footer says it went quiet |
