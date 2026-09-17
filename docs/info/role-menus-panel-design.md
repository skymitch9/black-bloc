# Role menus — `/rolemenu` is ONE command that opens a panel (wave 3)

> **Audience:** the build agent and the reviewer, and the owner for §I. **Status:** TRACKED ·
> ✅ **SHIPPED in v77** (`43312b9`, 2026-09-04 20:51) — built on `worktree-agent-ace2086f9f7cfa541` for 529k
> against a 420–500k estimate, four commits off `4523118`, eight append-shaped merge conflicts, sweeps
> **173–182**; the `## Deviations` foot (14 items) is the build agent's. Boot-verified only
> (`synced 36`); nothing below has met live Discord.
>
> 🔴 **Since then — one settled fork was REVERSED the next day.** §I's *"`/rolemenu` no longer
> vanishes when the mode is off"*, and deviation 11's new test that `rolemenu_mode` is **not** in
> `HIDDEN_WHEN_OFF`, both stopped being true at **v78** (`baede2a`, 2026-09-05 07:05) — *"Hide
> commands when off: a feature turned off on the portal takes its `/command` with it"*. Live
> `command_visibility.HIDDEN_WHEN_OFF` now carries **14** entries including
> `"rolemenu_mode": ("rolemenu",)`. What changed the argument is that hiding became a **setting**,
> `hide_commands_when_off` (bool, default **true**), so the owner can turn it off and get this
> design's behaviour back; `NEVER_HIDDEN` is `settings, help, about, ping`, and `/memory` is the one
> feature deliberately left out of the 15 (fork I-M1). Landing entry in
> 🔴 **AND REVERSED AGAIN, 2026-09-17** (branch `pings-remake`, §C6, measured before
> anything else was built): `/rolemenu` is **back out of `HIDDEN_WHEN_OFF` and into
> `NEVER_HIDDEN`** (now `settings, help, about, ping, rolemenu`), so v78's rule holds for the
> other fourteen features and not for this one. Why it flipped a second time: the owner turned
> `rolemenu_mode` **off** on 2026-09-16 while keeping the approval-gated menus, the **timed
> grants** and the staff-assigned sets, none of which onboarding can do — and hiding the
> command hid the only door to all three. `settings_panel.EXTRA_MODES` gains a `rolemenu_mode`
> row so the Settings panel's mode block still carries it (17 rows: 14 hidden + 3 hand-added).
> ⚠️ **Two more things the mode used to take away now stay**: **Hand roles out…** renders
> whenever a menu has options, and `run_assign` no longer refuses on the mode. **Post it** is the
> one thing the mode still removes, and `PICKING_IS_OFF` says exactly that.
> [`../DONE.md`](../DONE.md). ⚠️ **Deviation 11's other claim — that `request_mode` is the only
> entry left in `HIDDEN_WHEN_OFF` — is stale for the same reason.**
>
> ⚠️ **Also since then:** the **Logs** button's `count` / `important_only` came back at **v96** as
> **Show more** / **Important only** under the list
> ([`logs-buttons-design.md`](logs-buttons-design.md)).
>
> **Last verified: 2026-09-11 09:45** (the header; the body is as at the design). Measured this pass
> against `main` at `f3ae743` (v108 live): `settings_store.py` registers `rolemenu_panel_minutes`
> (int) and `labels.js` carries its row (§D); the pure `black_bloc/rolemenus.py` holds
> `menu_heading`, `option_line` and `menu_lines(menu, options, *, note="")` (deviation 2) plus
> `active_grants(db, guild_id, *, user_id=None)`, `grant_order`, `time_left`, `grant_line` and
> `grant_lines` (deviation 1); `cogs/community/role_menus.py` holds `put_option`, `drop_option`,
> `grant_role`, `extend_role`, `revoke_grant`, `repost_if_live` (fork F-R3 (a)) and `AssignPick`
> (deviation 7), with **no `StaffAssignView` and no `ALREADY_TIMED`** (deviations 5, 7);
> `logkinds.ROUTINE` carries the `role_menu.*` family (deviation 10) and the `web.` prefix is
> stripped before classification (`logkinds.bare` / `WEB`), so `web.role_menu.create` classifies as
> `role_menu.create` under feature `rolemenu`. The sweep rows landed as **173–182** (deviation 13).
> ⚠️ **NOT checked this pass:** anything in Discord or a browser — nothing booted, no menu posted,
> no role changed.
>
> Before that, **2026-09-04** — every `path:line` below was READ against `main` at `bf3e447`
> (the working tree is `4336a66`, one docs-only commit on top of it; no source file differs), in
> `black_bloc/cogs/community/role_menus.py` (**2164 lines**), `black_bloc/rolegrants.py` (467),
> `black_bloc/rolemenu_panels.py` (187), `black_bloc/panels.py` (194),
> `black_bloc/api/tools/rolemenus.py` (566), `black_bloc/api/tools/roles.py` (231),
> `black_bloc/settings_store.py`, `black_bloc/command_visibility.py`, `black_bloc/logkinds.py`,
> `black_bloc/personas.py`, `tests/test_bot.py`, `tests/test_logkinds.py`,
> `site/public/assets/labels.js`, `site/mock/server.mjs`, `docs/access/sweeps.md`,
> `docs/access/OWNER_GUIDE.md`, `docs/info/code-notes.md`.
> **Counted, not estimated:** **18 leaf subcommands over 2 top-level slots** (⚠️
> [`panels-program.md`](panels-program.md) §3 says 17 — it is one short; the four it left unnamed are
> `edit`, `showall`, `mode`, `seed-defaults`); `len(top) == 38` (`tests/test_bot.py:190`);
> `tests/cogs/community/test_role_menus.py` **1558 lines, 108 tests**; `docs/access/sweeps.md`
> holds **143 rows, numbered to 143**; `black_bloc/personas.py` names no role-menu command
> (**zero** matches).
> ⚠️ **NOT verified: anything was run.** No boot, no pytest, no ruff, no `check.mjs`, nothing
> against live Discord. The `path:line` keys will drift as the three sibling wave-3 branches merge —
> **trust the anchor text, not the number.**
>
> **Inherits every invariant in [`panels-program.md`](panels-program.md) §2 (P1–P17) and its §4
> library — none restated here.** Template: [`requests-panel-design.md`](requests-panel-design.md);
> the wave-2 shapes to copy are [`voice-panel-design.md`](voice-panel-design.md) (the longest cog so
> far) and [`pings-panel-design.md`](pings-panel-design.md) (staff list → pick → card). Feature
> behaviour is [`phase1-design.md`](phase1-design.md) §3 (F16) and
> [`phase9-design.md`](phase9-design.md) (approval, timed grants, reconciliation).

## A. Measured today — two groups, eighteen subcommands

`rolemenu` is a `Group` (`:1431`, `default_permissions=STAFF_ONLY`); `role` is a `Group` (`:1435`,
also `STAFF_ONLY`). **15 + 3 = eighteen leaf subcommands over two top-level slots**, every one
staff-gated. There is no member subcommand anywhere in this feature — members use the posted menus.

| Subcommand | Line | Gate | Calls · what is INLINE in the cog |
|---|---|---|---|
| `/rolemenu logs` | `:1595` | `send_logs` carries its own `require_staff` | `send_logs(interaction, "rolemenu", …)` |
| `/rolemenu create` | `:1616` | `require_staff` `:1624` | `create_menu` `:482`. ⚠️ **Writes no log row** — the website's `POST /api/rolemenus` does (`rolemenus.py:423`) |
| `/rolemenu add` | `:1654` | `require_staff` `:1662` | `role.is_assignable()` `:1668` then `add_option` `:586`. ⚠️ **No log row** |
| `/rolemenu remove` | `:1689` | `require_staff` `:1692` | `remove_option` `:610`. ⚠️ **No log row** |
| `/rolemenu edit` | `:1720` | `require_staff` `:1728` | `update_menu` `:521` + `log_action("role_menu.edit")` `:1750` — **bare, no `kind_via`** |
| `/rolemenu list` | `:1899` | `require_staff` `:1900` | `list_menus` `:423` + `get_options` `:579`; the lines are **inline** `:1906–1911` |
| `/rolemenu show` | `:1914` | `require_staff` `:1915` | `menu_heading` `:322` + `option_line` `:327` |
| `/rolemenu showall` | `:1932` | `require_staff` `:1933` | the same two + `pages_under_limit` (`modcases.py`) `:1946` |
| `/rolemenu post` | `:1954` | `require_staff` `:1960` | `post_panel` `:676` + `role_menu.post` `:1999` (**bare**); guard `:1990`; `_default_channel` `:2149` |
| `/rolemenu unpost` | `:2008` | `require_staff` `:2011` | `rolemenu_panels.unpost` `:69` — the one shared function here that already takes `via` and logs itself |
| `/rolemenu assign` | `:2030` | `_staff_pick` `:2042` → `require_staff` `:2045` | `StaffAssignView` `:1419` → `staff_assign` `:1312` (takes `via`, builds `kind_via` `:1351`) |
| `/rolemenu unassign` | `:2037` | same, `remove=True` | same, options filtered to held roles `:2059–2062` |
| `/rolemenu mode` | `:2090` | `require_staff` `:2093` | ⚠️ **inline** `:2095–2109`: `store.set` + reply + `role_menu.mode` (**bare**) |
| `/rolemenu delete` | `:2112` | `require_staff` `:2113` | `delete_menu` `:565` + `role_menu.delete` `:2123` (**bare**) |
| `/rolemenu seed-defaults` | `:2134` | `require_staff` `:2135` | `seed_default_menus` `:649` + `seed_summary` `:634` + `role_menu.seeded` `:2141` (**bare**) |
| `/role logs` | `:1768` | `send_logs` | `send_logs(interaction, "rolemenu", …)` — **the same feature**, so two groups share one log stream |
| `/role grant` | `:1783` | `require_staff` `:1791` | ⚠️ **all inline** `:1794–1851`: `open_grant` → `change_roles` → `add_grant`/`extend_grant` → `role.granted` (**bare**) |
| `/role extend` | `:1855` | `require_staff` `:1862` | ⚠️ **all inline** `:1864–1896`: `open_grant` → `pushed_back` → `extend_grant` → `role.extended` (**bare**) |

**Not a subcommand and NOT moving** (P14, program §7):

| Persistent thing | Where | Registered |
|---|---|---|
| `RoleMenuView` + `RoleMenuSelect` — the posted picker, `timeout=None` | `:1306`, `:1190`, `custom_id(menu_id)` `:267` | `cog_load` `:1444–1451`; posted by `post_panel` `:676` |
| `RequestButton` (Approve / Deny), a `SafeDynamicItem` on `REQUEST_TEMPLATE` `:35` | `:1148` | `bot.add_dynamic_items` `:1441` |
| `request_view` `:764`, `request_card` `:771`, `post_request_card` `:789`, `edit_request_card` `:823` | | the card in `rolemenu_approval_channel_id` |
| `RequestDenyModal` `:1105`, `RequestApproveModal` `:1123` | | reached from that card |

⚠️ **`StaffAssignView` `:1419` / `StaffAssignSelect` `:1368` are NOT persistent** (`timeout=180`,
never `add_view`ed). They are an ephemeral second message today, which is exactly what a sub-panel
is — they move.

**Loops and listeners, all untouched:** `_expiry_loop` `:1471` with its `@error` `:1482` and
`loop_health` `:1459`; `run_due_grants` `:1486`; `reconcile_records` `:1517`; `on_member_update`
`:1539`; `rolemenu_panels.reconcile` `:133` and its `store.on_change(MODE_KEY)` hook `:178`.

**Settings keys, measured:**

| Key | `KEY_TYPES` | Choices / help | Default |
|---|---|---|---|
| `rolemenu_mode` | `:219` enum | `ROLEMENU_MODES = ("off","on")` `:58`, choices `:287`, help `:585` | **`"off"`** `:1499` |
| `role_menu_channel_id` | `:146` channel | help `:445` ("where /rolemenu post goes by default") | — |
| `rolemenu_approval_channel_id` | `:251` channel | help `:716` | blank → `staff_channel_id` (`approval_channel` `:731`) |
| `rolemenu_approver_role_id` | `:252` role | help `:719` | blank → pings nobody |
| `rolemenu_log_level` | generated by the log-level family | `labels.js:116` | ⚠️ **not read line-by-line in `settings_store.py`** — the build confirms its registration site |

**Command visibility:** `HIDDEN_WHEN_OFF["rolemenu_mode"] = ("rolemenu",)`
(`command_visibility.py:17`) — with the mode off the **whole `rolemenu` group leaves the tree**.
`role` is not listed, so `/role grant` survives an off mode today. `hidden_names` `:38` matches on
top-level NAME, so the entry would still bite a top-level `/rolemenu` command.

**Site, measured:** `/api/rolemenus` (`api/tools/rolemenus.py:317`, whole router behind
`staff_dependency`) — `GET ""`, `POST /seed`, `GET /requests`, `POST /requests/{id}/approve`,
`POST /requests/{id}/deny`, `POST ""`, `PUT /{name}`, `DELETE /{name}`, `POST /{name}/post`,
`POST /{name}/assign`, `POST /{name}/unpost` (**11**). `/api/roles` (`api/tools/roles.py:96`, also
`staff_dependency`) — `GET /grants`, `POST /grants`, `POST /grants/{id}/extend`,
`DELETE /grants/{id}` (**4**). Page `site/public/rolemenus.html` + `site/public/assets/page-rolemenus.js`
(`editor` `:203`, `postCard` `:294`, `pendingCard` `:343`, `requestsSection` `:424`, `grantActions`
`:461`, `grantForm` `:508`, `assignForm` `:551`, `timedSection` `:614`; the Applications sections
share the page). `FEATURE_PAGES["rolemenu"] = "rolemenus.html"` (`logkinds.py:103`).

**`commands synced` is 38 today** (`tests/test_bot.py:190`, the boot figure at v73). Two top-level
slots become one, so this design takes it to **37**. ⚠️ **State the delta, not the number:** three
sibling wave-3 builds may land first, so the build **re-measures** and edits `:190` to what it reads.

### The five asymmetries this design has to answer

Measured, not inferred — each is a place the website and Discord already disagree:

1. ⚠️ **`/role revoke` does not exist**, and four places tell somebody to run it:
   `cogs/community/applications.py:92` (`REMOVE_IS_FOR_LISTS`, shown to staff), `:642` (its
   docstring), `docs/access/OWNER_GUIDE.md:86`, `docs/access/sweeps.md:254` and
   `docs/info/applications-panel-design.md:130`. The move itself exists only on the website
   (`DELETE /api/roles/grants/{grant_id}` `roles.py:194`).
2. **Discord cannot LIST grants or pending requests.** `GET /api/roles/grants` (`roles.py:102`) and
   `GET /api/rolemenus/requests` (`rolemenus.py:351`) have no Discord counterpart; a request is
   decidable only from the card in the approval channel.
3. **`/role grant` requires days** (`app_commands.Range[int, 1, DAYS_MAX]` `:1788`); the route makes
   them optional (`wanted_days(..., required=False)` `roles.py:139`), so the site can hand over a
   role with no end date and Discord cannot. → fork **F-R2**.
4. **`create` / `add` / `remove` write no action-log row on the Discord side** while the site
   `note()`s `web.rolemenu.create` and `web.rolemenu.edit`. The same move leaves a row from one door
   and nothing from the other.
5. **Seven log kinds here are bare** — `role_menu.edit`, `.post`, `.delete`, `.mode`, `.seeded`,
   `role.granted`, `role.extended` — so a route that ever calls the shared path would double-post
   (checklist 34's exact failure). Only `staff_assign` `:1351` and `rolemenu_panels.note` `:41`
   build `kind_via` today.

**Two duplicate-code findings**, both standing 🔧 items in [`../TODO.md`](../TODO.md) (`:303`, `:311`):
`role_menus.py:392 answer()` is byte-for-byte `panels.py:20 answer()`; and `grant`/`extend` are
implemented **twice**, once inline in the cog (`:1794`, `:1864`) and once in the route
(`roles.py:117`, `:169`), with different behaviour (finding 3, plus the cog refusing an
already-timed grant `:1795` where the route silently extends `roles.py:143`).

## B. The decision — one `/rolemenu`, staff only

**`/rolemenu` becomes a single `app_commands.command` keeping `default_permissions=STAFF_ONLY`;
both `Group`s go and `/role` disappears.** `commands synced` drops by **one** — **38 → 37** on
`main` today.

- `"role"` leaves `STAFF_COMMANDS` (`tests/test_bot.py:40`); `"rolemenu"` stays (`:41`).
- `LOGS_GROUPS` loses **both** `"rolemenu"` (`:12`) and `"role"` (`:13`) — the only panel in the
  wave that deletes two entries, leaving six.
- ⚠️ **`HIDDEN_WHEN_OFF["rolemenu_mode"]` is DELETED** (`command_visibility.py:17`). Not a fork:
  `rolemenu_mode` ships **off** (`settings_store.py:1499`), so on the default posture the command
  that could turn it on is not in the tree. Today `/role` survives to keep a staff door open; after
  this merge there is none, and the only ways back would be the site and `/settings set-value`.
  Staff-final-say (*"never design a terminal state staff cannot leave"*) settles it, and the owner
  answered this exact shape twice already — applications **"Visible"** (sweeps row 53,
  `sweeps.md:230`) and memory fork **I-M1, "open it"**.

**Root panel** — `build_panel(bot, guild, actor)`, one ephemeral embed + a `Panel` subclass (P2).
There is **no member half**: every path is `require_staff` today, so a non-staffer gets `still_staff`'s
refusal and no panel at all (P9 — the sentence, never a dead button).

**The states, crossed with the mode** (there are two modes, not three):

| # | This guild has | mode `on` | mode `off` |
|---|---|---|---|
| S0 | db down, or not in a guild | `db_up` / `NOT_IN_GUILD` `:129` as words; no panel | same |
| S1 | no menus | `NO_MENUS_YET` `:152` reworded as the embed; **New menu** · **Seed the defaults** · **Grants…** · the mode button · **Logs** · **Refresh** | + a line saying picking is off, and the mode button reads **Turn role menus on** |
| S2 | menus, none pending | the list as lines + **A menu…**; the same staff row | same, plus the off line |
| S3 | menus + ≥1 pending request | + **Waiting on staff (N)…** | same — a request can still be decided with picking off |

P3 in one line: **no state renders a control whose shared function would refuse it.** The mode never
removes a button from the ROOT; ~~it removes **Post it** and **Hand roles out…** from the menu card,
because `post` `:1979`, `_staff_pick` `:2069` and the route `:527` all answer `ROLE_MENUS_OFF` while
it is off~~ 🔴 **narrowed 2026-09-17 (`pings-remake` §C6): it removes ONLY Post it.**
`run_assign`'s `ROLE_MENUS_OFF` is gone, because handing a role over by name is a STAFF move with no
onboarding equivalent and the mode is about members picking for themselves. The card still says so in
a sentence, and the sentence now names what still works.

## C. The cards, the sub-panels, the modals

Each is a **re-render in place**: `retire(previous)` first (P6), `defer()` then
`edit_original_response` (P5), `db_ready` on every click (requests deviation 6), `still_staff` before
**every** move (P8 — and, since this feature is staff-only end to end, before every READ too, which
is the pings deviation 10 precedent).

**The root.**

| Row | Control | Rendered when | Shared function |
|---|---|---|---|
| 0 | `A menu…` `Select` over `list_menus` `:423`, ≤25 with `capped_placeholder` (`panels.py:66`) | at least one menu | — |
| 1 | `New menu` → `NewMenuModal` | always | `make_menu` (§F) |
| 1 | `Seed the defaults` → `Yes, make them` / `Leave it` | always | `seed_menus` (§F) over `SEED` `:45` |
| 1 | `Grants…` → sub-panel | always | — |
| 1 | `Waiting on staff (N)…` → sub-panel | `requests_by_status(db, guild.id, (PENDING,))` (`rolegrants.py:244`) is non-empty | — |
| 2 | `Turn role menus off` / `on` — **one button that says what it will do** | always | `set_mode` (§F) |
| 2 | `Logs` → a NEW ephemeral followup (P11) | always | `send_logs(interaction, "rolemenu")` — keeps its own `require_staff` |
| 2 | `Refresh` | always | — |
| 2 | `Open on the site` (link, `rolemenus.html`) | an origin is configured | `panels.site_page_url(origin, "rolemenu")` (`panels.py:101`) |

⚠️ Flipping the mode fires `rolemenu_panels.install`'s `store.on_change` hook (`:178`), which
debounces a sweep that posts or unposts **every** menu and re-syncs the tree ~5 s later. The reply
keeps today's "in a few seconds" wording (`MODE_ON` `:120` / `MODE_OFF` `:124`), minus the half about
commands disappearing (§E).

**The menu card.** Embed = `menu_lines(menu, options)` (§F) — `menu_heading` `:322` plus one
`option_line` `:327` per option — followed by `panel_note` `:370`'s approval/expiry sentences, so
the card and the posted panel can never describe one menu two ways.

| Row | Control | Rendered when | Shared function |
|---|---|---|---|
| 0 | `Add a role…` → sub-panel | `len(options) < OPTIONS_MAX` (25, `:43`) | `put_option` (§F) → `add_option` `:586` |
| 0 | `Remove a role…` → `Select` over `get_options` `:579` | ≥1 option | `drop_option` (§F) → `remove_option` `:610` |
| 0 | `Words…` → `WordsModal` | always | `change_menu` (§F) → `update_menu` `:521` |
| 0 | `Rules…` → `RulesModal` (days) | always | `change_menu` |
| 0 | `Ask staff first` / `Hand it over straight away` — **one button** | always | `change_menu(approval=…)` |
| 1 | `Post it` (no `message_id`) / `Move it…` (has one) → `ChannelSelect`, defaulting to `_default_channel` `:2149` | mode `on` **and** `menu["mode"] != STAFF_MODE` **and** ≥1 option | `post_menu` (§F) → `post_panel` `:676` |
| 1 | `Take it down` | `menu["message_id"]` is set | `rolemenu_panels.unpost` `:69` |
| 1 | `Hand roles out…` → sub-panel | ~~mode `on` **and**~~ ≥1 option (2026-09-17: the mode gate went) | `staff_assign` `:1312` |
| 1 | `Delete it` (danger) → `Yes, delete it` / `Keep it` | always | `drop_menu` (§F) → `delete_menu` `:565` |
| 2 | `Back` · `Refresh` | always | — |

Every "rendered when" above is a refusal that becomes unreachable, which is the point of P3:

| Refusal today | Why it can no longer fire from Discord |
|---|---|
| `STAFF_MENU_NOT_POSTED` `:143` (`post` `:1966`) | `Post it` is absent on a `staff`-mode menu; `rolemenu_panels.repost` `:92` skips it for the same reason |
| "has no roles on it yet, so there is nothing to post" `:1974` | `Post it` needs ≥1 option — and Discord rejects `max_values=0` anyway (`max_values_for` `:305`) |
| `NOTHING_TO_UNPOST` `:174` | `Take it down` needs a `message_id` |
| `TOO_MANY_OPTIONS` `:193` (`check_option_count` `:257`) | `Add a role…` disappears at 25; the sub-panel says to split the menu |
| `NOTHING_ON_THIS_MENU` `:170` / `NOTHING_TO_UNASSIGN` `:148` | `Hand roles out…` needs options, and `Take back…` needs them to hold one |
| `NO_SUCH_MEMBER` `:166` | a `UserSelect`, never a typed id |
| `_no_such_menu` `:2155` | every menu arrives from a select, never a typed name |

⚠️ Each of those strings **stays in the module** — the API routes and `rolemenu_panels` still answer
with most of them. Only their `/rolemenu …` sentences are rewritten (§E).

**`Add a role…` sub-panel.** Row 0 a `RoleSelect` (a native picker beats a typed name and gives
`role.is_assignable()` `:1668` something real to check), row 1 `Use the role's own name` (writes
straight through) and `Give it a label…` → `OptionModal` (label ≤ `LABEL_MAX` 100 `:42`, emoji), row
2 `Back`. ⚠️ A role Black Bloc cannot hand out is refused **in words** after the pick, not hidden —
`is_assignable()` depends on role position, which the panel cannot re-check per option cheaply, and
the existing sentence `:1670` already names the fix.

**`Hand roles out…` sub-panel.** Row 0 `UserSelect` "Who?"; then row 1 `Give them roles…` /
`Take roles back…` — the two buttons ARE today's `assign` / `unassign`, i.e. `staff_assign`'s
`remove` flag. `Take roles back…` renders only when they hold at least one of the menu's roles
(`_staff_pick` `:2059–2062`'s filter, moved to the render). Picking either drops
`StaffAssignSelect` `:1368` **reused unchanged** into row 2 (its `default=` marking of held roles
`:1380` is the one thing that makes "have" mean have). `Back` on row 3.

**`Grants…` sub-panel.**

| Row | Control | Rendered when | Shared function |
|---|---|---|---|
| 0 | `UserSelect` "Whose roles?" | always | filters `grants_for(db, guild, user_id=…)` `rolegrants.py:349` |
| 1 | `A timed role…` `Select` over `grants_for`, ≤25 with `capped_placeholder` | ≥1 grant matches | — |
| 2 | `Give somebody a role…` → `UserSelect` + `RoleSelect` + `DaysModal` | always | `grant_role` (§F) |
| 3 | `Back` | always | — |

⚠️ **The `UserSelect` is how a grant past the 25 cap is still reachable** — the memory panel's
"above the cap" precedent. The site is the long list; a named member is a short one.

**The grant card** — the `grant_row` shape (`roles.py:55`): who, which role, source, granted by,
when it ends.

| Control | Rendered when | Shared function |
|---|---|---|
| `Push it back…` → `DaysModal` | `expires_at` set **and** `removed_at` unset | `extend_role` (§F) → `extend_grant` `rolegrants.py:391` |
| `End it now` (danger) → `Yes, take it back` / `Leave it` | `removed_at` unset | `revoke_grant` (§F) — **the Discord half that has never existed** (§A finding 1) |
| `Back` | always | — |

⚠️ `Push it back…` is absent on a grant with no end date, so `GRANT_NEVER_ENDS`
(`rolegrants.py:86`) becomes unreachable from the panel; `NO_SUCH_GRANT` `:82` likewise, since the
grant arrived from a select.

**`Waiting on staff…` sub-panel.** Row 0 a `Select` over `requests_by_status(…, (PENDING,))`
(`rolegrants.py:244`), ≤25 with `capped_placeholder`, labelled with
`panels.option_label` (⚠️ imported under an alias — see §F). Picking one renders **`request_card(row,
label=…, menu_name=…, days=…)` `:771` unchanged**, so the panel's card and the channel's card are
one shape.

| Control | Rendered when | Shared function |
|---|---|---|
| `Approve` | `status == PENDING` and `expires_days_of(menu)` `:361` is falsy | `apply_request_decision(…, APPROVED)` `:915` |
| `Approve for N days…` → `RequestApproveModal` `:1123` **reused** | `PENDING` and the menu sets a duration | the same, with `days` |
| `Deny…` → `RequestDenyModal` `:1105` **reused** | `PENDING` | `apply_request_decision(…, DENIED)` |
| `Back` | always | — |

⚠️ **This is a second door onto a decision the persistent card also offers, and that is safe by
construction:** `apply_request_decision` `:932` refuses a non-`PENDING` row with `ALREADY_DECIDED`,
and `decide_request` (`rolegrants.py:270`) is a conditional UPDATE, so whoever loses the race is told
so rather than acting twice. The panel re-reads the row on every press and **never edits the channel
card itself** — `_approve_request` `:1009` and `_deny_request` `:1062` already call
`edit_request_card` `:823`. See fork **F-R1**.

**Modals** — all `AnswersErrors` + `discord.ui.Modal`, one shape (P12):

| Modal | Fields | Bounds |
|---|---|---|
| `NewMenuModal` | name · heading · line under it · mode | heading `TITLE_MAX` 256 `:40`; ⚠️ the description field is **4000**, not `DESCRIPTION_MAX` 4096 `:41`, because a `TextInput` caps at 4000 — `check_description` `:249` still guards the route |
| `WordsModal` | heading · line under it | as above, prefilled |
| `RulesModal` | days a role lasts (0 = never) · days after a no | ⚠️ a modal has no `Range`: refuse a non-number **in words** and save nothing (the youtube `NumbersModal` shape). `positive_days` `:340` / `whole_days` `:349` still clamp to `DAYS_MAX` |
| `OptionModal` | label · emoji | `LABEL_MAX` 100 `:42`; the emoji goes through `select_emoji` `:288` at render, so `<:name:id>` stays stored as text (checklist 14) |
| `DaysModal` | days | same refusal shape; see fork **F-R2** on whether 0 is allowed |
| `RequestApproveModal` `:1123` · `RequestDenyModal` `:1105` | reused unchanged | they already defer and answer |

`panels.NoteModal` is **not** used: the only free-text-to-a-person here is the deny reason, and
`RequestDenyModal` already exists with `grants.REASON_LIMIT` on it.

**Mode is one button, never a select.** Two spellings of one move is what P3 exists to kill; the
button says what it will do.

## D. Settings (P13 · checklist 33)

| Key | Type | Default | Status |
|---|---|---|---|
| `rolemenu_panel_minutes` | `int` | **10** | **NEW.** How long the panel stays live. Help text carries KI-20's warning in the same shape as the other seven (15+ loses the "gone quiet" footer, because Discord's interaction token expires at 15 minutes). Registered exactly where `voice_panel_minutes` is — `settings_store.py:1070` `KEY_TYPES.update`, `:1073` `KEY_HELP.update`, `:1607` `default()` — but **in its own appended block** so the parallel wave-3 branches merge textually |

Site rows, both appended in their own block:

| File | Line to copy | New row |
|---|---|---|
| `site/public/assets/labels.js` | `:51` (`voice_panel_minutes`) | `rolemenu_panel_minutes: 'How long the /rolemenu panel stays live',` |
| `site/mock/server.mjs` | `:420` (`voice_panel_minutes`) | `['rolemenu_panel_minutes', 'int', 10, 10, "minutes the /rolemenu panel stays live … 15 or more means the buttons simply stop working with no footer to explain it", null, 1440],` |

**Existing keys this panel READS, all untouched:** `rolemenu_mode`, `role_menu_channel_id`,
`rolemenu_approval_channel_id`, `rolemenu_approver_role_id`, `rolemenu_log_level`.

**Nothing else here is a decision.** The 25-option and 5-row caps are Discord's; `OPTIONS_MAX`,
`TITLE_MAX`, `DESCRIPTION_MAX`, `LABEL_MAX` are Discord's; the button table is the state machine in
§B/§C; `RETRY_DAYS_DEFAULT` (`rolegrants.py:34`) is already a per-menu column reachable from
`Rules…` and the site editor. The two behaviours a reader might mistake for decisions — staff
deciding a request from the panel, and staff ending a grant early — are **settled by the standing
staff-final-say rule**, so neither becomes a key. The one genuine new decision, whether a grant may
have no end date, is fork **F-R2**; whichever way it goes it is a behaviour, not a key, because the
website has no such key either.

## E. What goes away, and every line that names it

`/help` reads the tree (`cogs/core.py:85 tree_commands`), so it follows with no edit (P15).

| Thing | Where | Becomes |
|---|---|---|
| `rolemenu` Group + 15 children | `:1431` and §A | the root panel, the menu card, four sub-panels |
| `role` Group + 3 children | `:1435`, `:1768`, `:1783`, `:1855` | the Grants sub-panel |
| `_staff_pick` | `:2042` | the `Hand roles out…` sub-panel |
| `_no_such_menu` | `:2155` | **deleted** — nothing types a menu name |
| `_default_channel` | `:2149` | **kept** — it is the `ChannelSelect`'s default |
| `LOGS_GROUPS["rolemenu"]` **and** `["role"]` | `tests/test_bot.py:12–13` | **both deleted** — the loops at `:167` and `:213` would `KeyError` |
| `STAFF_COMMANDS "role"` | `tests/test_bot.py:40` | **deleted**; `"rolemenu"` `:41` stays |
| `assert len(top) == 38` | `tests/test_bot.py:190` | **one lower than whatever the build measures** — never a hard-coded absolute |
| `HIDDEN_WHEN_OFF["rolemenu_mode"]` | `command_visibility.py:17` | **deleted** (§B); its case in `tests/test_command_visibility.py` goes with it |

**Strings that name a retired subcommand and are rewritten in the SAME commit** — each currently
tells somebody to run something that will not exist:

| Line | String | Names |
|---|---|---|
| `:117` | `ROLE_MENUS_OFF` | ⚠️ shown to **members** on a posted panel — keep it pointing at the dashboard and `/settings set-value`, never at a staff panel button |
| `:121` `:124` | `MODE_ON` · `MODE_OFF` | "the `/rolemenu` commands come back / disappear" — both halves are now false |
| `:143` | `STAFF_MENU_NOT_POSTED` | `/rolemenu assign` · `/rolemenu unassign` |
| `:148` | `NOTHING_TO_UNASSIGN` | `/rolemenu assign` |
| `:152` | `NO_MENUS_YET` | `/rolemenu create` · `/rolemenu seed-defaults` |
| `:156` | `SEED_EMOJI_NOTE` | `/rolemenu delete event-alerts` |
| `:170` `:174` | `NOTHING_ON_THIS_MENU` · `NOTHING_TO_UNPOST` | `/rolemenu post` |
| `:219` | `ROLE_REFUSED_AFTER_DECISION` | `/role grant` |
| `:228` | `ALREADY_TIMED` | `/role extend` |
| `:642` | `seed_summary`'s tail | `/rolemenu post <name>` · `/rolemenu assign` |
| `:1637` `:1642` `:1683` `:1700` `:1706` `:1747` `:1924` `:1945` `:1974` `:1986` `:2054` `:2119` `:2158` | the inline command replies | most go with their command; the survivors are rewritten |
| `rolegrants.py:84` | `NO_SUCH_GRANT` | "`/role grant` starts one" |
| `cogs/community/applications.py:92` `:642` | `REMOVE_IS_FOR_LISTS` + its docstring | ⚠️ **`/role revoke`, a command that has never existed** (§A finding 1) — now name the panel path this build creates |
| `settings_store.py:445` `:585–587` | two `KEY_HELP` entries | "where /rolemenu post goes by default" · "hides the /rolemenu commands" |

**Site touch points** — no route is added or removed, so `node site/mock/check.mjs` must report the
**same** page/route counts before and after. Three mock copies of rewritten strings drift otherwise:
`site/mock/server.mjs:63` (its copy of `ROLE_MENUS_OFF`, ⚠️ **already drifted** — it says
`/rolemenu mode on` where the real string says `/settings set-value rolemenu_mode on`), `:279` and
`:352` (the two `KEY_HELP` copies). `site/public/assets/labels.js:113–116` names no command —
measured, untouched apart from §D's new row.

**Docs rewritten in the same commit** (P15): `docs/access/sweeps.md` rows **1** (`:90`), **12**
(`:101`), **19** (`:108`), **22** (`:111`), **23** (`:112`), **38** (`:126`), **53** (`:230`), **72**
(`:254`) and the Phase 1/2 appendix scripts at `:150–153` and `:179–181` — rewritten **in place**,
not added to; `docs/access/OWNER_GUIDE.md:86` (the `/role revoke` sentence) and its sweeps count
(`:5`, `:82`); `docs/info/feature-list.md:54` (F16); `docs/info/panels-program.md:76` (the Role menus
row → shipped, and its "17" → **18**); `docs/info/applications-panel-design.md:130`;
`docs/info/phase1-design.md` and `docs/info/phase9-design.md` each get a dated "superseded by the
panel" line at the top, **not** a rewrite; `docs/info/code-notes.md` re-keyed at the merge — the
anchors cluster at `:107–113` (`rolemenu_panels.py`), `:268–303` (the F16 section at `:264`),
`:702` (`## tests/cogs/community/test_role_menus.py`), `:1440–1441` and `:1551–1553` (the hardening
section at `:1539`), `:2131–2138` (`rolegrants.py`) and `:2151–2164`+ under `## role menus 2` at
`:2121`, plus the dashboard section at `:2467`.

## F. Extractions (P4) — one function per move, called by BOTH doors

⚠️ **The DB/move layer stays in the COG**, as it does for applications and temp voice.
`api/tools/rolemenus.py:10–40` imports about thirty names from the cog and `api/tools/roles.py:9`
imports `change_roles`; moving the layer would be a large mechanical diff across a 2164-line cog and
a 1558-line test file for no gain this build needs. Every existing import stays byte-identical,
which is what makes the existing route tests' unchanged assertions the proof the refactor changed
nothing (wave-0 deviation 4).

**New, module level in `cogs/community/role_menus.py`** — each does ONE write and ONE log row, each
takes `via: str = VIA_DISCORD` and builds its kind with `kind_via` (checklist 34):

| Function | Replaces · what the route loses |
|---|---|
| `make_menu(bot, guild, actor, …, *, via)` | `create_menu` `:482` **plus the log row Discord never wrote**. `rolemenus.py:423` deletes `note("web.rolemenu.create")` and passes `via=VIA_WEBSITE` |
| `change_menu(bot, guild, actor, name, *, via, **fields)` | `update_menu` `:521` + today's `role_menu.edit` `:1750`, which gains `kind_via`. `rolemenus.py:454` deletes `note("web.rolemenu.edit")` |
| `drop_menu(bot, guild, actor, name, *, via)` | `delete_menu` `:565` + `role_menu.delete` `:2123` with `kind_via`. `rolemenus.py:477` deletes its `note` |
| `put_option(…)` / `drop_option(…)` | `add_option` `:586` / `remove_option` `:610` + a **new** `role_menu.option_added` / `role_menu.option_removed` row each. ⚠️ Two new kinds — they join `logkinds.ROUTINE` beside `role_menu.edit` (`logkinds.py:305`) |
| `post_menu(…)` | `post_panel` `:676` + `role_menu.post` `:1999` with `kind_via`. `rolemenus.py:459` and `:495` delete their `note("web.rolemenu.post")` |
| `seed_menus(bot, guild, actor, *, via)` | `seed_default_menus` `:649` + `role_menu.seeded` `:2141` with `kind_via`. `rolemenus.py:340` deletes `note("web.role_menu.seeded")` |
| `set_mode(bot, guild, actor, value, *, via)` | inline `:2095–2109`; `role_menu.mode` gains `kind_via` |
| `grant_role(…)` | ⚠️ **two implementations become one** — inline `:1794–1851` AND `roles.py:117–163`. `roles.py:161` deletes `note("web.role.granted")` |
| `extend_role(…)` | same shape — inline `:1864–1896` AND `roles.py:169–188`. `roles.py:181` deletes its `note` |
| `revoke_grant(bot, guild, actor, grant_id, *, via)` | `roles.py:194–222` **only** today — this is the Discord half that does not exist, i.e. the phantom `/role revoke`. `roles.py:216` deletes `note("web.role.ended")` |

⚠️ **`grant_role` / `extend_role` / `revoke_grant` are the largest single risk in this build.** They
are not "extract the cog's inline half"; they are "reconcile two divergent implementations". Measured
differences: the cog refuses an already-timed grant up front (`ALREADY_TIMED` `:1797`) where the
route silently extends (`roles.py:143`); the cog requires days ≥ 1 (`:1788`) where the route allows
none (`roles.py:139`); the cog logs `role.granted` bare where the route wrote `web.role.granted`.
**The build picks one behaviour per difference and records it in its Deviations foot.** This is also
the one place the build cannot claim "the route tests are unchanged, so nothing moved" —
`tests/api/tools/test_roles.py` (212 lines) will need edits, and saying which is part of §H.

⚠️ `tests/test_logkinds.py:81–88` lists `web.role.ended`, `web.role.extended`, `web.role.granted` and
the four `web.rolemenu.*` in the routes' own allowed set. **Those seven entries move into the SHARED
map at `:234`** beside the `role_menu.assign` block, or the AST walk
(`test_a_route_never_notes_an_event_its_shared_path_already_logged`) fails.

**Pure, into a NEW `black_bloc/rolemenus.py`** (there is none today; ⚠️ **it must not import
`rolemenu_panels`**, which imports FROM the cog at `rolemenu_panels.py:9` — that is the cycle §H.3
exists to catch):

| New | What it is |
|---|---|
| `MenuMove` + `MENU_MOVES` + `menu_buttons(*, posted, options, menu_mode, picking_on)` | §C's menu-card table AS DATA, proved by a parametrised test |
| `root_buttons(*, has_menus, picking_on, pending)` | §B's root table |
| `grant_buttons(*, ends, removed)` · `request_buttons(status, *, timed)` | the two cards |
| `menu_lines(menu, options)` | `/rolemenu show`'s shape, from `menu_heading` `:322` + `option_line` `:327` |
| `list_lines(menus, counts)` | `/rolemenu list`'s inline `:1906–1911` |
| `PANEL_MINUTES_KEY = "rolemenu_panel_minutes"`, `panel_minutes(store, guild_id)` | one-liners over `panels.panel_minutes` (`panels.py:97`), exactly as `requests.py` does |
| `PANEL_TITLE`, `PANEL_TIMEOUT_FOOTER`, the new sentences | wave-0 deviation 1 — a whole sentence, not a format string |

⚠️ `menu_heading` `:322`, `option_line` `:327`, `panel_note` `:370`, `summary` `:311` and
`seed_summary` `:634` **stay where they are** and are imported by the new module —
`api/tools/rolemenus.py` imports several by name, and moving them changes an import outside the cog.

**Two things to reuse, never re-copy:**

1. `role_menus.py:392 answer()` is byte-for-byte `panels.py:20 answer()` — **import the library's and
   delete this one** (the standing 🔧 finding, [`../TODO.md`](../TODO.md) `:303` and `:311`; the same
   dedup applications and voice each made).
2. ⚠️ **`role_menus.py:448 option_label(db, menu_id, role_id)` and `panels.py:74
   option_label(ident, status, text)` share a NAME and nothing else.** A plain
   `from ...panels import option_label` silently shadows the cog's own and breaks `label_for` `:473`,
   which is the approval path's only source of a role's wording. **Import it aliased**
   (`option_label as select_label`). This is the trap of this build.

**No `do_*` signature changes.** The shared functions here take `bot` / `db` and an actor
explicitly, never an `Interaction`, so the panel passes `interaction.client` and `interaction.user`
and nothing else moves.

**Nothing to add to `panels.py`.** `capped_placeholder`, `option_label`, `clamped`, `panel_minutes`,
`site_page_url`, `Panel`, `answer`, `still_staff`, `retire`, `db_ready`, `db_up` cover every need
here. The one candidate — a shared numbers-modal validator, wanted by `RulesModal` and `DaysModal`
and already hand-rolled in the youtube and pings panels — is **reported, not built**: it would edit
a file three sibling wave-3 branches are also touching, and voice deviation 8 says a clean textual
merge is worth more than one-fact-one-home for a few lines. Fold it at the conductor's merge.

## G. Tests (P16 — one file per source file, mirrored paths)

| File | What it gains |
|---|---|
| `tests/cogs/community/test_role_menus.py` (1558 lines, 108 tests) | `/rolemenu` answers ephemerally with a panel; **parametrised over S1–S3 × both modes — each renders exactly its §B row and no other**; `Post it` is absent on a `staff`-mode menu, on an empty menu and with the mode off; `Take it down` only with a `message_id`; `Add a role…` absent at 25 options; `Take back roles…` absent when they hold none; `Push it back…` absent on a no-end grant; `End it now` absent on a closed one; `Waiting on staff (N)…` absent with no pending row; every button calls its shared function with `via` untouched (mock it); a staffer demoted mid-card moves nothing (`still_staff` at every site, reads included); `db_ready` after a defer; `Post it` and `Seed the defaults` defer first; timeout disables every item and a re-render `retire`s what it replaced |
| `tests/test_rolemenus.py` (**new file**) | the four button tables against every flag combination; `menu_lines` and `list_lines` against the strings `/rolemenu show` and `/rolemenu list` produce today; `panel_minutes` |
| `tests/test_settings_store.py` | `rolemenu_panel_minutes` round-trips, defaults 10, has help text |
| `tests/test_bot.py` | `LOGS_GROUPS` loses **two** entries; `role` leaves `STAFF_COMMANDS`; the tree-limit test **recounts** |
| `tests/test_command_visibility.py` | the `rolemenu_mode` case goes with the `HIDDEN_WHEN_OFF` entry (§B) |
| `tests/test_logkinds.py` | the seven `web.*` kinds move from the routes' set (`:81–88`) into `SHARED` (`:234`); the two new option kinds join `ROUTINE` |
| `tests/api/tools/test_rolemenus.py` (904 lines) | ⚠️ **mostly unchanged — that is the proof no route moved.** Only the assertions that read a `web.rolemenu.*` row change, to one row carrying `via` (`tests/api/conftest.py:one_web_row`) |
| `tests/api/tools/test_roles.py` (212 lines) | ⚠️ **will change** — §F's reconciliation. The build says in its Deviations foot exactly which behaviours moved and why |
| `tests/test_rolemenu_panels.py` (396) · `tests/test_rolegrants.py` (264) | **unchanged** — the mode sweep and the grants store are untouched |

## H. §J — prove before merge (P17), and the sweep rows

1. `python -m black_bloc` boots; **read `commands synced` and record both numbers** — the drop must
   be exactly one (requests deviation 7; checklist 10 — a check that could not run is not a check
   that passed). With no token, measure it the only other way:
   `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits` counts the real tree.
2. The parametrised state test: every state renders its row and no other (checklist 3, 12).
3. `python -c "import black_bloc.rolemenus, black_bloc.cogs.community.role_menus,
   black_bloc.rolemenu_panels, black_bloc.api.tools.rolemenus, black_bloc.api.tools.roles"` — the
   substitute for a boot (wave-0 deviation 5), and the thing that catches the **import cycle** this
   build risks: `rolemenu_panels.py:9` imports from the cog, so the new pure module must not import
   it back.
4. `ruff`; full `pytest`; `node site/mock/check.mjs` (**expect the counts unchanged** — no route
   changes); `node --input-type=module --check < site/public/assets/labels.js`.
5. Checklist sweep before reporting — **1** and **2** (unposting is a message DELETE the guard cannot
   see; `rolemenu_panels.py:71` handles it and `would_unpost` must stay distinct from
   `unpost_failed`), **8** and **30** (`AnswersErrors` on every modal, select and view), **11**
   (`allowed_mentions` on every interpolated send — menu titles, option labels and display names are
   all over this feature), **12** (role change and log before the card edit — `edit_request_card`
   `:823` is deliberately last), **14** (`select_emoji` `:288` keeps custom emoji as `<:name:id>`),
   **15** and **17** (the duplicate `answer()` and the `option_label` name collision — §F), **22**
   (`positive_days` `:340` / `whole_days` `:349` still bound what the modals accept; a modal has no
   `app_commands.Range`), **24** (defer before `Post it` and before `Seed the defaults` — six menus
   and forty options in one call), **26** (options keep a way to be removed — that is
   `Remove a role…`), **28** (`_expiry_loop` `:1471` and `loop_health` `:1459` are untouched), **33**
   (§D), **34** (nine routes lose their `note()` and gain `via=VIA_WEBSITE`).

⚠️ **TEST_MODE stands, and this feature is where it matters most.** `TEST_MODE=true`
(`black_bloc/guard.py`): the bot speaks only in `#blackbloc-logs` and DMs. `Post it` to any
other channel is refused by `guard.allows_channel` (`:1990` today) and logged; `card_target` `:741`
redirects an approval card to the test channel and `CARD_IN_TEST_CHANNEL` `:206` says so;
`rolemenu_panels.unpost` `:72` logs `would_unpost` instead of deleting. ⚠️ **But `Hand roles out…`,
`Give somebody a role…` and `End it now` change REAL roles even in test mode** — the guard patches
sends, not `member.edit` (`sweeps.md` row 23 says this out loud). Nothing in this design may read as
"safe because test mode is on".

**Sweep rows — numbered at BUILD time, starting at the next free row.** `docs/access/sweeps.md`
holds **143 rows, numbered to 143** as this is written, but **four wave-3 designs are being written
in parallel** and each will claim a block, so this document claims **no numbers**: the build reads
the file's last row and starts after it. Rows 1, 12, 19, 22, 23, 38, 53, 72 and the Phase 1/2
appendix scripts are rewritten **in place**, not added to.

| # | Do this | Expect |
|---|---|---|
| N | `/rolemenu` on a guild with menus | one ephemeral panel: the menu list as lines, **A menu…**, New menu, Seed the defaults, Grants…, the mode button, Logs, Refresh, Open on the site — and nothing that types a name anywhere |
| N+1 | Turn the mode **off**, then run `/rolemenu` again | ⚠️ **the command is still there** (this is the change) — the panel says picking is off, the posted panels come down within a few seconds, and **Post it** / **Hand roles out…** are gone from every menu card while everything else stays |
| N+2 | Mode back on, **A menu…** → `pronouns` | the card: Add a role… · Remove a role… · Words… · Rules… · Ask staff first · Post it · Hand roles out… · Delete it — and the lines above match what `/rolemenu show` used to print |
| N+3 | **A menu…** → `runner-status` (a `staff`-mode menu) | **no Post it at all** — the card says in words that nobody gives these roles to themselves, and **Hand roles out…** is how they are handed out |
| N+4 | `Add a role…` → pick a role above Black Bloc's own in Server Settings → Roles | refused **in words** naming the fix, and nothing is added. Then add a real one with a label and an emoji; `Remove a role…` takes it off and says nobody loses the role they have |
| N+5 | `Post it` → pick the test channel; then `Move it…` to the same channel; then `Take it down` | one panel, moved not duplicated (it edits the message it already has); taking it down leaves the menu and everybody's roles alone; **Post it** comes back on the card |
| N+6 | `Rules…` → 7 days, retry 7; `Ask staff first`; re-post; pick the role as a member | the panel's "Before you pick" block says both things; picking sends a request and DMs you; a card with Approve / Deny appears in the approval channel (⚠️ in the test channel while test mode is on, and the reply says so) |
| N+7 | `/rolemenu` → **Waiting on staff (1)…** → the request → **Approve for N days…** | the same card the channel shows; approving DMs the member, adds the role, edits the channel card — and pressing Approve on the channel card afterwards says it was already decided rather than acting twice |
| N+8 | `Grants…` → pick that member → the grant → `Push it back…` 3, then `End it now` | the end date moves; ending takes the role back, DMs nothing (staff move), and the Timed roles table on the site agrees. ⚠️ **This is the `/role revoke` that four docs have been promising** |
| N+9 | `Grants…` → `Give somebody a role…`; `Seed the defaults` twice; leave the panel `rolemenu_panel_minutes` minutes | the grant lands with its clock (see fork F-R2 for a 0-day grant); seeding twice says "already there, left alone" and never rewrites a menu; the panel goes quiet with the footer |

## I. The genuine forks — the owner decides, one at a time

Settled first, by the standing rules, so they are **not** put to him:

- ✅ **`/rolemenu` stays `STAFF_ONLY`.** All eighteen subcommands are staff-gated today; members
  never had a door here and do not gain one. The posted menus are the member surface.
- ✅ **`/rolemenu` no longer vanishes when the mode is off** (`HIDDEN_WHEN_OFF`, §B). The owner
  answered this shape for applications ("Visible") and for memory (I-M1, "open it"), and here the
  mode ships **off**, so hiding it hides the only Discord way to turn it on.
  🔴 **REVERSED at v78, 2026-09-05** — `rolemenu_mode` is back in `HIDDEN_WHEN_OFF` (14 entries),
  because hiding became the `hide_commands_when_off` setting (default **true**) rather than a
  per-feature decision. The Settings page and `/settings set-value` are the way back in, and
  `/help` says how many are hidden. See the header.
- ✅ **Staff may decide a request from the panel as well as from the card.** Staff-final-say, and
  `decide_request`'s conditional UPDATE makes two doors safe rather than racy.
- ✅ **`End it now` exists at last.** Every stored decision gets a staff reversal; the website has had
  it since 9b; and it makes `/role revoke` — named in four places — true instead of a lie.
- ✅ **The posted menus and the request cards are untouched** (P14, program §7).

**Three questions are genuinely his:**

- **F-R1 — the pending-requests queue inside the panel.** Today a pending role request is decidable
  only from the persistent card in `rolemenu_approval_channel_id`, or on the site.
  - **(a) Build it** — `Waiting on staff (N)…` on the root, the same `request_card` embed, Approve /
    Approve for N days / Deny. A card that has scrolled away cannot be found again from Discord at
    all, and staff who missed the ping currently have no Discord door. **Recommended.**
  - (b) Leave it out. Smaller build by roughly one sub-panel, and it keeps ONE surface per question —
    the owner's one-fact-one-home rule for surfaces pulls this way, because the card already owns
    "decide this request".

- **F-R2 — may `Give somebody a role…` grant with NO end date?** The website can
  (`roles.py:139`, `required=False`); `/role grant` cannot (`Range[int, 1, DAYS_MAX]` `:1788`). One
  of the two is wrong and this build has to pick.
  - **(a) Yes — the Days modal takes 0 = never runs out**, matching the site and matching
    `RequestApproveModal`'s own wording (`:1125`, *"Days, or 0 for a role that never runs out"*). A
    no-end grant still writes a `role_grants` row, which is what keeps `on_member_update`
    reconciliation (`:1539`) honest about who gave what. **Recommended** — the asymmetry reads as an
    accident, not a decision.
  - (b) No — the panel requires days, and the website is tightened to match. Keeps "a grant is a
    clock" true everywhere, but it removes a behaviour from a live surface.

- **F-R3 — what `Words…` and `Rules…` do to a menu that is already posted.** Editing does not
  refresh the posted panel today; `/rolemenu edit`'s reply just says to post it again (`:1747`), so a
  live panel can describe rules it no longer has.
  - **(a) Re-post automatically** when the menu is posted and the edit changed something the panel
    shows. `post_panel` `:676` **edits** the existing message (`edit_existing` `:664`) rather than
    posting a second one, so this costs one API call, makes no new message, and cannot double-post.
    **Recommended.**
  - (b) Keep it manual and say so on the card. Zero chance of an unexpected channel edit — but it
    leaves a posted panel able to lie about its own rules until somebody presses Post.

## J. What NOT to build, and what this costs

**Not in this build:**

- **The posted `RoleMenuView` / `RoleMenuSelect` and the `RequestButton` cards.** P14 and program §7:
  they are persistent `DynamicItem` views that belong to the room, not the caller. Their behaviour,
  their `custom_id`s and their re-registration in `cog_load` `:1444` are untouched.
- **Reordering a menu's options.** `position` `:581` is stored and only a drag can set it; Discord
  has nothing to drag with. The card says so, exactly as the applications Questions sub-panel does.
- **Moving the DB/move layer out of the cog** (§F) — about thirty route imports say don't.
- **Any new API route or site control.** `site/mock/contract.json` is untouched; `check.mjs` counts
  must be identical before and after; the three mock string copies in §E are the only site edits
  beyond §D's one settings row.
- **A member half of the panel.** There is none today and this is a door swap, not a feature pass.
- **`count` / `important_only` on `Logs`** — lost exactly as they were for every other panel; the
  site's Logs page has both.
- **Per-option approval or per-option expiry.** Both are per-MENU columns (`approval`,
  `expires_days`, `retry_days` `:504`) and stay that way.
- **Touching `ROLEMENU_MODES`** — two modes, not three; do not add `shadow` to make it rhyme.
- **Rewriting the 2164-line cog.** Append the panel block at the FOOT, as the pings build did (its
  deviation 17); nothing already in the file is renamed or re-homed.
- **A shared numbers-modal helper in `panels.py`** — reported in §F, folded by the conductor at the
  merge, not built here beside three sibling branches.

**Cost.** Wave-2 measured, against its own estimates: memory **329k** (est 250–300k), golive **464k**
(est 230–300k), youtube **371k** (est 180–250k), pings **379k** (est 300–360k), voice **385k** (est
420–480k) — four of the five landed **above** their estimate, and only voice's ran high.

This is **the longest cog in the wave** (2164 lines against voice's 1986), eighteen subcommands over
two groups, **seven surfaces** (root, menu card, Add a role, Hand roles out, Grants, grant card,
Requests + request card), a brand-new pure module with its own test file, and the one thing no
wave-2 panel had: **two divergent implementations of grant / extend to reconcile**, which reaches
into `api/tools/roles.py` and edits its tests. **Budget 420–500k**, with ~400k the likely landing —
same band as voice, one notch wider because of §F's reconciliation.

**Prep before dispatch:** clean tree, a fresh usage read, and a brief that tells the agent to commit
at clean boundaries, one layer at a time —

1. the pure module `black_bloc/rolemenus.py` + `tests/test_rolemenus.py`;
2. the extractions in the cog + the nine route `note()` deletions + `tests/api/tools/test_roles.py`
   (the riskiest layer, and the one worth landing alone);
3. the cog panel + `tests/cogs/community/test_role_menus.py`;
4. the doc/string/site sweep + `tests/test_bot.py` + `command_visibility.py`

— so a kill costs the last layer rather than the build.


## Deviations from this design

Written by the BUILD agent, 2026-09-04, on `worktree-agent-ace2086f9f7cfa541`. Everything not
listed here was built as §B–§H say. The header above is the CONDUCTOR's to flip at landing.

1. **§I-amend — the owner's addition to F-R2, built.** `Grants…` **opens as an audit** of every
   timed role running in the guild: soonest to end first (a grant with no end date sorts LAST, not
   first), one line per grant — member · role · time left · the end date, or `no end date` twice
   over. Capped at 25 lines with a sentence pointing at the site's Timed roles table. The
   `UserSelect` **Whose roles?** NARROWS that audit rather than being the only way to see anything,
   and `A timed role…` picks from whatever is currently shown. `active_grants(db, guild_id, *,
   user_id=None)` is the one shared function behind it, in the pure module, and the ordering and
   the "time left" wording (`grant_order`, `time_left`, `grant_line`, `grant_lines`) are unit
   tested in `tests/test_rolemenus.py`, including the no-end-date case and the 25 cap.

2. **`menu_heading` and `option_line` MOVED into `black_bloc/rolemenus.py`.** §F says they stay in
   the cog and are imported by the new module. That is a circular import — the cog imports the pure
   module for its button tables, so the pure module importing the cog closes the loop — and §H.3
   exists to catch exactly that shape. They are pure formatters with no route importing them
   (measured: `api/tools/rolemenus.py` imports neither), so moving them costs nothing. `panel_note`,
   `summary`, `seed_summary`, `needs_approval`, `expires_days_of` and `retry_days_of` all STAY in
   the cog as the design says; `menu_lines` takes the note as a keyword instead of computing it.

3. **The card's rows are Discord rows, not the design's logical groupings.** §C puts four buttons
   AND a select on "row 0" of the menu card, which Discord cannot draw — a select occupies a whole
   action row. Built as: row 0 the `Take a role off this menu…` select, row 1 `Add a role…` ·
   `Words…` · `Rules…` · the approval toggle, row 2 `Post it`/`Move it…` · `Take it down` ·
   `Hand roles out…` · `Delete it`, row 3 `Back` · `Refresh`. Every state is asserted to sit inside
   Discord's five rows.

4. **`Post it` opens a "where should it go?" view rather than dropping a `ChannelSelect` onto the
   card.** discord.py's `ChannelSelect` cannot be pre-defaulted to a channel the way §C's
   "defaulting to `_default_channel`" asks, so the default is named in a SENTENCE on that view
   instead (`_default_channel` survives as the module-level `default_channel`, exactly as §E says).
   `Back` returns to the card.

5. **`grant_role` / `extend_role` / `revoke_grant` reconciled onto the WEBSITE's behaviour, on all
   three measured differences** (§F says the build picks one per difference and records it):
   days are optional — `None` or `0` means the role never runs out (fork F-R2 (a), and the site
   has always allowed it); a second grant over an open one RESETS its clock rather than being
   refused (`ALREADY_TIMED` is deleted — nothing refuses that now); the kind is
   `kind_via("role.granted", via)`. The routes keep their own member/role lookups and their own
   `Refused` codes, so **`tests/api/tools/test_roles.py` needed no edit at all** — which is the
   proof the reconciliation did not move the website.

6. **`put_option` / `drop_option` are panel-only.** §F's table implies both doors; the website's
   `PUT /api/rolemenus/{name}` rewrites the whole option list in one request, so routing
   `sync_options` through them would write nine `role_menu.option_*` rows for one edit that
   `role_menu.edit` already records. They still take `via` at its Discord default.

7. **`StaffAssignSelect` and `StaffAssignView` were REPLACED, not "reused unchanged".** §C asks for
   the select to be dropped into the sub-panel untouched; its callback sends a NEW ephemeral
   message, which is the thing a panel exists to stop. `AssignPick` keeps the option building and
   the `default=` marking of held roles byte-for-byte and re-renders the card in place instead.
   `StaffAssignView` had no other caller once `_staff_pick` went, so it is gone.

8. **The three role-changing moves keep an explicit `guard.allows_channel` check** (`guarded`,
   used by `run_assign`, `run_grant`, `run_revoke`). §H says these change REAL roles in test mode
   and the design does not ask for a guard; but the retired `StaffAssignSelect` DID check it, and
   silently dropping it would have been an access-INCREASING change made by accident. Reads are not
   guarded.

9. **An automatic re-post writes no log row.** Fork F-R3 (a) is built, but `repost_if_live` calls
   `post_panel` directly rather than `post_menu`, so a `Words…`/`Rules…` edit leaves ONE
   `role_menu.edit` row and no `role_menu.post` beside it. A failure is swallowed and adds one
   sentence to the reply (checklist 12).

10. **The log kinds are the `role_menu.*` family throughout, so four `web.rolemenu.*` kinds were
    RENAMED.** §F pairs `make_menu` with the route's `web.rolemenu.create` and `change_menu` with
    the cog's `role_menu.edit`; those are two different families and one shared function can only
    emit one. `role_menu.*` won (it is the Discord-side family already in `ROUTINE`), so
    `web.rolemenu.create|edit|delete|post` became `web.role_menu.*` in `logkinds.ROUTINE`,
    `site/mock/contract.json`, `site/mock/server.mjs` and the route tests. `HEADS["rolemenu"]`
    stays, so rows already in the database still classify.

11. **`tests/test_command_visibility.py` was re-pointed at `request_mode`, not trimmed.** §E says
    "its case in `tests/test_command_visibility.py` goes with it"; in fact the WHOLE file used
    `rolemenu_mode` as its exemplar, and `request_mode` is the only entry left in
    `HIDDEN_WHEN_OFF`. Its `bot` fixture now sets `request_mode` off before `install` (it defaults
    **on**), and the one real-tree test that pins the staff LOCK still loads the role-menus cog,
    because `/request` is a member command and could not have proved it. A new test says
    `rolemenu_mode` is not in `HIDDEN_WHEN_OFF` and `/rolemenu` is never hidden.
    🔴 **Both of those sentences went stale one day later, at v78** — `HIDDEN_WHEN_OFF` has **14**
    entries, `rolemenu_mode` among them, and `/rolemenu` IS hidden while the mode is off unless
    `hide_commands_when_off` is turned off. See the header.

12. **Two strings the design did not list were rewritten**, because they also named a command that
    no longer exists: `black_bloc/applications.py` (twice, `/role grant`) and
    `black_bloc/pings.py` (twice, `/rolemenu post <menu>`), plus their mock-server copies and three
    lines of `site/public/assets/page-rolemenus.js` that told the reader the mode hides the
    commands. `docs/access/sweeps.md` row **12** was in §E's list but names no retired subcommand,
    so it was left alone and the header says so.

13. **`docs/access/OWNER_GUIDE.md` gained its `/rolemenu` row; its sweeps COUNT is untouched** —
    the new sweep rows were lettered `M1`–`M10` and the conductor numbered them **173–182** at
    the merge (after raidtrain's 163–172) and moved the count 172 → 182.

14. **What was NOT verified.** No boot (`python -m black_bloc` — no bot token in this environment;
    the §H.3 import check plus `import black_bloc.bot` is the substitute), nothing against live
    Discord, and no `commands synced` line read off a real login — 38 → 37 was measured through
    `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits`, which counts the real
    tree after loading every cog. `node site/mock/check.mjs` reports **17 pages / 142 routes**,
    unchanged (no route was added or removed).
