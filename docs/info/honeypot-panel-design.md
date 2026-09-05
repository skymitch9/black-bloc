# Honeypot — `/honeypot` is ONE command that opens a panel

> **Audience:** the build agent and the reviewer, and the owner for §I.
> **Status:** TRACKED · ✅ **BUILT 2026-09-05** on `worktree-agent-a7ea6b0dbeac7f753` off `932f34e` — see the `## Build deviations` foot for what changed and what is NOT verified. Not merged, not deployed, and **never run against live Discord**.
> **Last verified: 2026-09-05** — every `path:line` below was READ against `main` at
> **`git rev-parse --short HEAD` = `12979c2`** (the two commits since `46fba16` touch
> `docs/TODO.md` only — `git diff --stat 46fba16 12979c2` = 1 file, 5 insertions — so every code
> line number here is valid at both). Files read in full or grepped exhaustively:
> `black_bloc/cogs/moderation/honeypot.py` (**802 lines**), `black_bloc/panels.py` (**219**),
> `black_bloc/api/tools/honeypot.py` (**88**), `black_bloc/settings_store.py`,
> `black_bloc/logkinds.py`, `black_bloc/command_visibility.py`, `black_bloc/actionlog.py`,
> `tests/cogs/moderation/test_honeypot.py` (**768**), `tests/api/tools/test_honeypot.py` (**135**),
> `tests/test_bot.py`, `tests/test_logkinds.py`, `site/public/assets/page-honeypot.js` (**101**),
> `site/public/honeypot.html` (**102**), `site/public/assets/labels.js`, `site/mock/server.mjs`,
> `docs/access/sweeps.md` (**588 lines**, last row **182**), `docs/access/OWNER_GUIDE.md`,
> `docs/info/feature-list.md`, `docs/info/phase3-design.md`, `docs/info/cutover-plan.md`,
> `docs/info/code-notes.md`, `docs/info/panels-program.md`, `docs/info/automod-panel-design.md`,
> `docs/info/review-checklist.md`, `docs/TODO.md`.
>
> **Measured, not assumed:**
> ⚠️ **There is NO `black_bloc/honeypot.py`** — the feature has no pure module at all; every
> function lives in the cog. This build creates one (§F), which is the single biggest cost
> difference against automod (§J).
> ⚠️ **There IS `black_bloc/api/tools/honeypot.py`**, and its three routes ALREADY pass
> `via=VIA_WEBSITE` into shared functions and already `note()` nothing — **checklist 34 is
> satisfied on the web side today** (§E). Two site-driven moves bypass it, and that is a
> reported defect, not this build's to fix.
> `HONEYPOT_MODES = ("off", "shadow", "on")` (`settings_store.py:70`) — **three** modes, so every
> crossing below is three-way. `honeypot_mode`'s default is **`"shadow"`** (`:1473–1474`), NOT
> `off` — which is why §I settles the hide-when-off question the opposite way to `/rolemenu`.
> `HONEYPOT_PURGE_MAX_DAYS = 7` (`:71`), default `1` (`:1475–1476`).
> `tests/test_bot.py:179` asserts **36** top-level commands; `LOGS_GROUPS` (`:11–15`) holds
> `honeypot`, `modmail`, `mod`; `"honeypot"` is in `STAFF_COMMANDS` (`:26`).
> `command_visibility.HIDDEN_WHEN_OFF` (`:16–18`) holds **`request_mode` only** today.
> `docs/access/OWNER_GUIDE.md` names honeypot **nowhere** (zero matches, case-insensitive) —
> the same hole automod found.
> `discord.py` **2.7.1** (measured in `.venv`): `RoleSelect.__init__` takes `default_values:
> Sequence[ValidDefaultValues]`, and `discord.Object(id=…)` is an accepted default for a
> `role_select` (`discord/ui/select.py:152–186`) — so the exempt list CAN be prefilled.
> ⚠️ **NOT verified: anything was run.** No boot, no `pytest`, no `ruff`, no live Discord, no
> live dashboard. `node site/mock/check.mjs` **could not be run** — port 8788 is already held by
> the concurrent hide-when-off build's worktree, so the last recorded figure (**17 pages / 142
> routes**, `automod-panel-design.md`, 2026-09-04) is quoted as an OLD reading, not a current
> one; the build measures it before AND after. Whether a real Discord client submits an EMPTY
> multi-`Select` at `min_values=0` is the same unproven edge `raidtrain-panel-design.md:29`,
> `events-panel-design.md` deviation 6 and `pings-panel-design.md` deviation 5 flag — and here it
> is **load-bearing**, because the exempt list is the select (fork **F-H1**).
>
> **Inherits every invariant in [`panels-program.md`](panels-program.md) §2 (P1–P17) and its §4
> library — none restated here.** Closest precedent:
> [`automod-panel-design.md`](automod-panel-design.md) (the other moderation staff panel) and its
> `## Build deviations` foot, which is the trap list. Template:
> [`requests-panel-design.md`](requests-panel-design.md). Feature behaviour is
> [`phase3-design.md`](phase3-design.md) §F9 and [`feature-list.md`](feature-list.md):47.
>
> ⚠️ **This build changes how staff CONFIGURE the trap and nothing about what it CATCHES.**
> The listener path (`on_message` `:429`, `_caught` `:450`, `_delete` `:539`, `_offer_ban`
> `:569`, `_lock` `:592`, `on_guild_channel_delete` `:750`), the ban path (`do_ban` `:212`,
> `_dm_before_ban` `:234`, `ban_hit` `:247`), the `BanNowButton` (`:380`) and the whole
> hit-recording half (`record_hit` `:138` … `hit_counts` `:204`) are **untouched**, their log
> kinds are untouched, and the shadow-first rollout rule (`cutover-plan.md:53`) is untouched.

## A. Measured today — one group, one sub-group, seven leaf subcommands

`honeypot` is an `app_commands.Group` (`:417–420`, `default_permissions=STAFF_ONLY` `:419`);
`exempt` (`:421–423`) is a sub-group of it. **5 + 2 = seven leaf subcommands over ONE top-level
slot.**

| Subcommand | Line | Gate | Calls · what is INLINE in the cog |
|---|---|---|---|
| `/honeypot logs [count] [important_only]` | `:605` | `send_logs` carries its own `require_staff` (`actionlog.py:287`) | `send_logs(interaction, "honeypot", count=, important_only=)` |
| `/honeypot setup [name]` | `:618` | `require_staff` `:623` → `_database_ready` `:625` → `defer` `:627` | `make_trap_channel(bot, guild, user, name)` `:297` — **already shared, already takes `via`, already `kind_via` `:341`** |
| `/honeypot status` | `:652` | `require_staff` `:654` → `_database_ready` `:656` | ⚠️ **all inline** `:658–681`: `hit_counts` `:664`, the six lines `:665–676`, `NO_STAFF_WARNING` `:677–678` |
| `/honeypot mode <off\|shadow\|on>` | `:683` | `require_staff` `:692` — ⚠️ **no `_database_ready`** | ⚠️ **inline** `:693–708`: the `NO_STAFF_ROLES` refusal `:693–695`, `store.set` `:696`, the reply `:699`, `log_action("honeypot.mode")` `:702` — **bare, no `kind_via`** |
| `/honeypot forget <channel_id>` | `:710` | `require_staff` `:713` — ⚠️ **no `_database_ready`** | the `NOT_AN_ID` digit-parse `:716–721`, then `self._forget` `:732` — a **method**, also called by `on_guild_channel_delete` `:753` with no actor; its `log_action("honeypot.trap_removed")` `:740` is **bare** |
| `/honeypot exempt add <role>` | `:755` | `_change_exempt` → `require_staff` `:767` — ⚠️ **no `_database_ready`** | ⚠️ **inline** `:763–798`: the list edit `:769–782`, the "was already" branch `:774–782`, `store.set` `:783`, the sentence `:786`, `log_action` `:792` — **bare** |
| `/honeypot exempt remove <role>` | `:759` | same | same, `add=False`, `honeypot.exempt_remove` |

**Not a subcommand and NOT moving** (P14): **`BanNowButton`** (`:380`, a
`SafeDynamicItem`/`DynamicItem` re-registered in `cog_load` `:426`, attached by `_offer_ban`
`:581–582`). That button belongs to the shadow-hit card in the log channel, not to the caller.
§I lists it under what is already settled.

**Settings keys today**

| Key | `settings_store.py` | Notes |
|---|---|---|
| `honeypot_mode` | type `:177`, choices `:277`, help `:515`, default **`"shadow"`** `:1473–1474` | the three-way switch |
| `honeypot_channel_ids` | type `:178` (`channels`), help `:516` | ⚠️ help text names `/honeypot setup` |
| `honeypot_purge_days` | type `:179` (`int`), max `:302` (=7), help `:517–520`, default **1** `:1475–1476` | printed by `status` `:670`, read by `do_ban` `:221` and `ban_hit` `:262` — **set by no honeypot subcommand** (fork **F-H3**) |
| `honeypot_exempt_role_ids` | type `:180` (`roles`), help `:521` | the list the multi-select becomes |
| `honeypot_log_level` | generated `:808–810` from `FEATURES` (`logkinds.py:27`) | help built by `log_level_help` `:800`, whose `extra` reads `LOG_LEVEL_COMMANDS["honeypot"] = "honeypot"` `:784` |

Read but not owned by honeypot: `staff_channel_id` (through `store.staff_roles`
`settings_store.py:1742`), `log_channel_id` (`:572`, where the Ban-now card is posted).

**Log kinds today** (`logkinds.py`): `honeypot.exempt`, `honeypot.exempt_add`,
`honeypot.exempt_remove`, `honeypot.hit_recorded`, `honeypot.mode`, `honeypot.setup`,
`honeypot.trap_removed` are all **ROUTINE** (`:224–230`). `honeypot.banned` (`.banned` suffix),
`honeypot.ban_failed` / `honeypot.delete_failed` (`_failed` suffix) are IMPORTANT by
`IMPORTANT_SUFFIXES` (`:112–130`). `make_trap_channel` `:341` and `ban_hit` `:289` already build
their kind with `kind_via`; ⚠️ **`honeypot.mode`, `honeypot.trap_removed` and both exempt kinds
are bare** and gain one in §F.

> 🔴 **`honeypot.exempt` is TAKEN, and it is not what a reader expects.** `:471–477` logs
> `honeypot.exempt` when the LISTENER ignores an author (bot / Manage Server / staff role /
> exempt role). It has nothing to do with configuring the exempt list. The panel's list write
> therefore **cannot** reuse that kind and gets a new one, `honeypot.exempt_set` (§F). Anyone
> who "tidies up" by merging the two breaks the one line that proves a moderator was spared.

**The site, measured** — the dashboard owns the hits table and setup:

| Surface | Where | What it owns |
|---|---|---|
| `honeypot.html` (102) + `page-honeypot.js` (101) | `site/public/` | Hits table `:37–62` with a per-row **Ban now** `:47`, a **Run setup** card `:64–79`, `namespaceSettings('honeypot')` `:93` (every `honeypot_*` key through the GENERIC settings API), `logsSection('honeypot')` `:94` |
| `GET /api/honeypot/hits?limit=` | `api/tools/honeypot.py:53` | `hit_row` `:32` per `recent_hits` |
| `POST /api/honeypot/hits/{hit_id}/ban` | `:60` | `ban_hit(..., "web", via=VIA_WEBSITE)` `:65` |
| `POST /api/honeypot/setup` | `:73` | `make_trap_channel(..., name, via=VIA_WEBSITE)` `:81` |
| the whole router | `:47` | behind `staff_dependency` |

⚠️ **Both write routes already do what checklist 34 asks** — shared function, `via=VIA_WEBSITE`,
no `note()`. Nothing in §E changes them. **The mode and the exempt list are written from the
site through the generic settings API, not through a `/api/honeypot` route** — so
`set_mode`'s arming refusal will not apply on that path. That is a measured defect, reported in
§J, and it is the same one automod found (`automod-panel-design.md` §J).

**`commands synced` — the number does NOT move.** `tests/test_bot.py:179` measures **36**, and
one `Group` occupying one top-level slot becomes one `command` occupying one top-level slot.
This is the `/memory` and `/automod` shape, not the `/voice` shape: **36 → 36.** ⚠️ The build
still **re-measures and states both numbers** (requests deviation 7, checklist 10) — if the
count moves at all, something else broke and the build stops rather than editing the assertion.

> 🔴 **The measurement that decides what the mode control may offer.** `/honeypot mode on` is
> refused by `NO_STAFF_ROLES` (`:78–84`, checked at `:693`) whenever `store.staff_roles(guild)`
> (`settings_store.py:1742`) resolves **no roles** — that is, no role can see
> `staff_channel_id`. Unlike automod there is **no second `STAFF_IS_THE_TEST_CHANNEL` gate**:
> honeypot has exactly one arming blocker. So on a guild whose staff channel resolves nothing,
> **`on` is a mode the panel must not offer** (P3/P9), and the embed must say why in words.
> Whether the live guild's `staff_channel_id` resolves any role is **not knowable from the
> repo** — say so, do not guess. `sweeps.md:215` records the expected reading (*"the resolved
> staff-role count > 0"*).

> 🔴 **`setup` is deliberately NOT mode-gated, and this build must not "fix" that.** The trap
> channel can be built while the mode is `off`; nothing about `make_trap_channel` `:297` reads
> `honeypot_mode`. Its guard is **`test_category(bot)` `:355–363`** — while `bot.guard` is
> installed, the channel is created **inside the test channel's category** and, if the test
> channel cannot be seen, refused outright with `NO_TEST_CHANNEL_TRAP` (`:70–73`). The pinned
> notice is separately gated by `guard.allows_channel` in `post_notice` `:368`, which returns
> False → `NOTICE_NOT_POSTED` (`:74–77`). ⚠️ **Checklist 1 is already satisfied by that pair,
> and it is NOT a `would_setup` dry run.** A build that adds one changes behaviour, changes the
> log kinds, and breaks `tests/cogs/moderation/test_honeypot.py:545` and `:564`. **Setup…
> therefore renders in all three modes.**

## B. The decision — one `/honeypot`, staff only

**The order, verbatim (owner, 2026-09-04, audit proposal 1 of 6, answered "Yes"):** *"All of
honeypot should be 1 slash commands Let's combine"* — recorded at `docs/TODO.md:257–264`.

**`/honeypot` becomes a single `app_commands.command`; the `honeypot` and `exempt` Groups both
go.** It keeps `default_permissions=STAFF_ONLY` (`command_visibility.py:14`,
`manage_messages`), so `"honeypot"` **stays** in `tests/test_bot.py:26`'s `STAFF_COMMANDS` and
never joins `MEMBER_COMMANDS`. There is no member half of this feature and inventing one is out
of scope.

**One panel, no member/staff split** (the P2 split collapses to a single branch): every caller
past the UX lock is re-checked at runtime by `panels.still_staff` (`panels.py:55`) before every
move, exactly as P8 requires. A member who somehow reaches the command gets
`store.staff_refusal(guild_id)` (`settings_store.py:1755`) as a sentence, never a dead button.

**What the panel owns** — the seven subcommands and nothing more:

| Today | On the panel |
|---|---|
| `/honeypot status` | the ROOT embed, always rendered — never hidden behind a button (events deviation 10: a button that hides the loudest warning loses it, and `NO_STAFF_WARNING` `:85–88` is that warning) |
| `/honeypot setup [name]` | **Setup…** → a one-field name modal; renders only when no LIVE trap exists |
| `/honeypot mode <mode>` | a `Select` on the ROOT, with `on` offered only when arming would succeed |
| `/honeypot exempt add\|remove <role>` | ONE `RoleSelect` on the ROOT whose selection IS the list, plus **Exempt nobody** for the empty case (fork **F-H1**) |
| `/honeypot forget <channel_id>` | **Forget…**, rendering only when at least one trap id is recorded — the panel knows the id, so no argument is typed (fork **F-H2**) |
| `/honeypot logs [count] [important_only]` | a **Logs** button answering a NEW ephemeral followup (P11) |

**What stays site-only, said out loud on the panel** — the hits TABLE and its per-row **Ban
now** (`page-honeypot.js:37–62`); `honeypot_log_level` (the generic Settings page); `count` /
`important_only` on Logs, lost exactly as they were for `/request`, `/apply`, `/voice` and
`/automod`. The root's **Open on the site** link (`panels.site_page_url(origin, "honeypot")`,
`panels.py:123` → `logkinds.py:94` → `honeypot.html`) is how a staffer reaches them.

**The states.** Honeypot has no per-caller state — the panel is the same for every staffer — so
the state table is the FEATURE's condition crossed with the mode. `T` = the recorded ids in
`honeypot_channel_ids`; **live** means `guild.get_channel(cid) is not None`, the same
comprehension `make_trap_channel:301–306` uses (one home, §F `live_traps`).

| # | Condition | mode `off` | mode `shadow` | mode `on` |
|---|---|---|---|---|
| S0 | database down | ⚠️ the panel does not open: `panels.db_up` (`panels.py:80`) answers `DB_UNAVAILABLE` as a sentence. **Today `mode`, `forget` and both `exempt` subcommands skip this check entirely (§A) — the panel closes that hole** | same | same |
| S1 | no staff role resolves (`store.staff_roles(guild)` empty) | mode select offers **off · shadow** only; the embed carries `NO_STAFF_ROLES` `:78–84` as its blocker line | same | ⚠️ reachable only because the SITE can write `honeypot_mode` through the generic settings API (§A). The embed carries `NO_STAFF_WARNING` `:85–88` at the foot — today's `:677–678` condition — and the select still offers off/shadow so staff can leave the state |
| S2 | staff resolve · `T` empty | **Setup…** renders; no **Forget…**; embed says *not set up yet* (today's `:669`) | same | same, plus a line saying the trap is armed but there is nothing to fall into |
| S3 | staff resolve · `T` has ≥1 LIVE id | **no Setup…** (`make_trap_channel` would answer `ALREADY_A_TRAP` `:89–93` — P3: not offered, not offered-and-refused); **Forget…** renders | same | same |
| S4 | staff resolve · `T` has a DEAD id (recorded, `guild.get_channel` is `None`) | **Setup…** renders (the `live` list is empty) AND **Forget…** renders; ⚠️ the embed names the dead id in words, so Forget explains itself instead of being a mystery button | same | same |
| S5 | `honeypot_exempt_role_ids` is non-empty | **Exempt nobody** renders beside the role select in every mode; the embed lists the roles as mentions (today's `:671–672`) | same | same |
| S6 | `honeypot_exempt_role_ids` holds **more than 25** ids | ⚠️ the `RoleSelect` is **NOT rendered** in any mode; the embed says the list is longer than Discord can edit in one control and names the site. **Never a capped select** — see the red block below | same | same |
| S7 | `bot.guard` is installed (TEST_MODE) | one extra embed line in every mode and every other state: the trap is contained to the test channel's category and **nobody will actually be banned** (`do_ban:216–218`) | same | same |

> 🔴 **S6 is a data-loss guard, not a nicety, and it is why the cap is a rule rather than a
> fork.** Discord caps a select's `max_values` at 25 and requires
> `min_values ≤ len(default_values) ≤ max_values`. `honeypot_exempt_role_ids` is unbounded (the
> registry types it `roles` with no maximum, `settings_store.py:180`). If 30 roles are stored
> and the control shows 25, **submitting it deletes the other five silently** — an
> access-REDUCING write nobody asked for, from a control that looked like it was showing the
> whole list. So above 25 the control is withheld and the embed says so; below 25 it is exact.
> `panels.capped_placeholder` (`panels.py:88`) is the WRONG tool here: it is for a picker where
> the unshown rows are merely unreachable, not for a control whose submission is the whole set.

P3 in one line: **no state renders a control whose shared function would refuse it.** `on` is
absent from the mode select in S1; **Setup…** is absent in S3; **Forget…** is absent in S2;
**Exempt nobody** is absent when the list is already empty; the role select is absent in S6.

## C. The cards, the sub-panels, the modals

Each is a **re-render in place**: `panels.retire(previous)` first (P6, `panels.py:62`),
`defer()` then `edit_original_response` (P5), `panels.db_ready` (`panels.py:70`) on every click
after a defer, `panels.still_staff` (`panels.py:55`) before **every** move including the reads
(pings deviation 10 — a demoted staffer reading the exempt list is the same defect one step
earlier). Every send and edit that interpolates a `<#…>` or `<@&…>` carries
`allowed_mentions=discord.AllowedMentions.none()` (checklist 11) — this embed is nothing but
channel and role mentions.

**The ROOT embed** is today's `/honeypot status` block `:665–678`, moved WHOLE into
`status_lines` (§F) and passed through `panels.clamped` (`panels.py:108`, `DESCRIPTION_LIMIT`
4000). ⚠️ **The panel's lines and the lines `/honeypot status` printed must never be two
shapes** — one function, both readers:

| Line | Source today |
|---|---|
| **mode** — `off`/`shadow`/`on` | `:666` |
| **staff (always exempt)** — `staff_roles_sentence(staff)` | `:667`, `settings_store.py:1340` |
| **trap channels** — mentions, or *not set up yet* | `:668–669` |
| **purge** — N day(s) of their messages | `:670` |
| **exempt roles** — mentions, or *staff only* | `:671–672` |
| **caught** — banned · logged in shadow · failed · ignored | `:673–675`, from `hit_counts` `:204` |
| `NO_STAFF_WARNING` when `not staff and mode == "on"` | `:677–678` |

**Added by the panel**, because it replaces a command that could explain itself in prose:
one line naming the arming blocker when there is one (S1); one line naming any **dead** recorded
trap id (S4); and, while `bot.guard` is installed, the test-mode line (S7). Nothing else.

**The ROOT view** — four rows, none at Discord's per-row cap:

| Row | Control | Rendered when | Shared function |
|---|---|---|---|
| 0 | `Select` **"What the trap does…"** over `mode_options(current, may_arm)` — `HONEYPOT_MODES` minus `on` in S1, current flagged `default` | always | `set_mode` (§F) |
| 1 | `RoleSelect` **"Roles the trap ignores…"**, `min_values=0`, `max_values=min(25, …)`, `default_values=[discord.Object(id=r) for r in stored]` | **not** S6 | `set_exempt_roles` (§F) |
| 2 | `Setup…` → name modal | no LIVE trap (S2, S4) | `make_trap_channel` — unchanged |
| 2 | `Forget…` | `T` non-empty (S3, S4) | `forget_trap` (§F) — fork **F-H2** decides button vs. card |
| 2 | `Exempt nobody` (danger) | the stored list is non-empty (S5) | `set_exempt_roles(…, [])` — fork **F-H1** |
| 2 | `Settings…` → sub-panel | always | — |
| 3 | `Refresh` | always | — |
| 3 | `Logs` → a NEW ephemeral followup (P11) | always | `send_logs(interaction, "honeypot")` — keeps its own `require_staff` |
| 3 | `Open on the site` (link) | `panels.site_page_url(origin, "honeypot")` is not `None` | — |

⚠️ **Row 2 holds at most four buttons** (Setup… and Forget… can co-exist only in S4). Row 3
holds three. There is deliberate headroom in both, unlike automod's five-button rule card.

**The name modal** (`TrapNameModal`, `AnswersErrors` + `discord.ui.Modal`, P12 / checklist 30):

| Field | Prefill | Limit | Refusal |
|---|---|---|---|
| *What the trap channel is called* | `TRAP_NAME` = `🍯-do-not-post-here` (`:33`) | `max_length=100` — Discord's channel-name ceiling, and the bound that vanished with the `name: str \| None` parameter (checklist 22, voice deviation 13) | an empty submit falls back to `TRAP_NAME`, exactly today's `name or TRAP_NAME` `:319`; `make_trap_channel`'s own four outcomes (`already` / `no_test_channel` / `refused` / `created`) are answered verbatim as they are today |

**The Settings sub-panel** — following `automod-panel-design.md` **build deviation 1**, which
established that a panel's own `*_panel_minutes` key needs a Discord door of its own rather than
only `/settings set-value`:

| Row | Control | Rendered when | Shared function |
|---|---|---|---|
| 0 | `Numbers…` → a two-field modal: **panel minutes** and **purge days** (fork **F-H3** decides whether purge days gets a field or stays a read-only line) | always | `save_settings` (§F) — validate BOTH before writing EITHER, then ONE write per key and ONE log row |
| 1 | `Back` | always | — |

⚠️ **The modal rebuilds the bounds the registry enforces** (checklist 22): purge days is
`0 … HONEYPOT_PURGE_MAX_DAYS` (7, `settings_store.py:71`, `KEY_MAX` `:302`, re-clamped
defensively in `do_ban:221`); panel minutes is `1 … 1440` with the KI-20 warning in its help.
A value that fails validation is answered in words and **nothing at all is written** — not even
the field that parsed (the automod `NumbersModal` rule).

**The Forget card** (only if fork **F-H2** goes (a)) — embed lists every recorded id, live ones
as `<#id>` and dead ones as *a channel Discord no longer has (id)*; row 0 is a `Select`
**"Forget a trap channel…"** over those options; row 1 is `Back`.

⚠️ **`panels.NoteModal` is NOT used** — nothing here sends a person a free-text reason. The DM
this feature does send (`DM_BEFORE_BAN` `:43–47`) is fixed text on the ban path, which this
build does not touch.

## D. Settings (P13 · checklist 33)

Registered **in their own appended block** at the foot of the registry, exactly where
`rolemenu_panel_minutes` sits (`settings_store.py:1134–1145` for `KEY_TYPES`/`KEY_HELP`, `:1681`
for the `default()` branch), so parallel branches merge textually.

| Key | Type | Default | Status |
|---|---|---|---|
| `honeypot_panel_minutes` | `int` | **10** | **NEW.** How long the panel stays live. Help text carries KI-20's warning in the same shape as the twelve shipped keys, word for word: 15+ loses the "gone quiet" footer because Discord's interaction token expires at 15 minutes |

**That is the only new key.** ⚠️ Nothing else here is a decision: the 25-option cap, the
5-buttons-per-row cap and the 5-fields-per-modal cap are Discord's; the button table is the
state machine in §B; the purge ceiling is `HONEYPOT_PURGE_MAX_DAYS` and was decided in Phase 3;
and the two behaviours a reader might mistake for decisions — staff re-checked before every
move, and `on` hidden rather than offered-and-refused — are **settled by the standing rules**
(P8, P3/P9), not chosen here, so neither becomes a key.

**The key also needs its site rows**, following the shipped pattern exactly:

| File | Line to copy | What to add |
|---|---|---|
| `site/public/assets/labels.js` | `:56` (`rolemenu_panel_minutes: 'How long the /rolemenu panel stays live'`) — beside the existing honeypot rows `:65–69` | `honeypot_panel_minutes: 'How long the /honeypot panel stays live'` |
| `site/mock/server.mjs` | `:426` (the `rolemenu_panel_minutes` row) | `['honeypot_panel_minutes', 'int', 10, 10, "…", null, 1440]` |

`labels.js:186`'s `NAMESPACES` already contains `'honeypot'` — measured, no change.

**Existing keys this panel READS or WRITES, all otherwise untouched:** `honeypot_mode`,
`honeypot_channel_ids`, `honeypot_purge_days`, `honeypot_exempt_role_ids`, `honeypot_log_level`,
`staff_channel_id`, `log_channel_id`.

## E. What goes away, and every line that names it

`/help` reads the tree (`cogs/core.py`), so it follows with no edit (P15).

| Thing | Where | Becomes |
|---|---|---|
| `honeypot` Group | `:417–420` | one `@app_commands.command(name="honeypot")`, same `default_permissions=STAFF_ONLY` |
| `exempt` Group | `:421–423` | the root's `RoleSelect` |
| the seven leaf commands | `:605`, `:618`, `:652`, `:683`, `:710`, `:755`, `:759` | buttons, selects, modals |
| `_change_exempt` | `:763–798` | `set_exempt_roles` (§F) — ONE write of the whole list |
| `_forget` (a cog method) | `:732–747` | module-level `forget_trap` (§F); `on_guild_channel_delete` `:750–753` calls it with `actor=None`, unchanged in behaviour |
| `_database_ready` | `:598–603` | `panels.db_up` / `panels.db_ready` — **and the four commands that skipped it (§A) stop skipping it** |
| `_post_notice` `:635`, `_test_category` `:649`, `_may_act_in` `:638` | thin cog wrappers | `_may_act_in` is used by `_delete` `:540` and **stays**; the other two are one-line pass-throughs to module functions and go |
| the `NOT_AN_ID` digit-parse | `:716–721` | **deleted** — nothing types a channel id any more |
| `NOT_AN_ID` | `:98–101` | **DELETED** with it. Nothing else raises it: measured, the string is referenced only at `:719` |
| `NOT_A_TRAP` | `:94–97` | ⚠️ **KEPT** — `forget_trap` can still miss when two staff press Forget on the same id, and the option list can outlive the write. Its TEXT is rewritten (it names `/honeypot status`) |
| `ALREADY_A_TRAP` | `:89–93` | ⚠️ **KEPT** — unreachable from Discord after this build (P3 withholds Setup… in S3) but still raised on the WEB path (`api/tools/honeypot.py:85`, `SETUP_REFUSED["already"]`). Its TEXT is rewritten (it names `/honeypot forget <id>`) |
| `tests/test_bot.py` `LOGS_GROUPS["honeypot"]` | `:12` | **DELETED** — `/honeypot` is no longer a Group with a `logs` child, so the loops at `:160` and `:202` would `KeyError` |
| `tests/test_bot.py` `STAFF_COMMANDS "honeypot"` | `:26` | **unchanged** — still staff-only |
| `tests/test_bot.py` `assert len(top) == 36` | `:179` | **unchanged, and re-measured to prove it** (§A) |
| `settings_store.LOG_LEVEL_COMMANDS["honeypot"]` | `:784` | **REMOVED** — `log_level_help` `:800` renders *"and in `/honeypot logs`"*, and there is no such command afterwards. This is automod build deviation 9 applied to the next row down; with no entry the help simply says the lines are kept on the dashboard, which is true |
| `logkinds.ROUTINE` `honeypot.exempt_add`, `honeypot.exempt_remove` | `:225–226` | ⚠️ **REMOVED, in the same commit as the emission.** `tests/test_logkinds.py::test_no_classification_entry_is_dead` (`:554`) asserts `ROUTINE - emitted` is empty, so leaving them behind **fails the suite**. Their replacement `honeypot.exempt_set` is ADDED to `ROUTINE` beside them |
| `command_visibility.HIDDEN_WHEN_OFF` | `:16–18` | **nothing to change in THIS build** — measured, it holds `request_mode` only. The concurrent hide-when-off build adds `honeypot_mode → ("honeypot",)`; §I settles why that entry stays |

**Strings that name a retired subcommand and are rewritten in the SAME commit** — each currently
tells somebody to run something that will not exist:

| File:line | Today | Becomes |
|---|---|---|
| `cogs/moderation/honeypot.py:48–51` | `ALREADY_BANNED` — *"`/honeypot status` shows what the trap has caught"* | *"`/honeypot` shows what the trap has caught"* |
| `:78–84` | `NO_STAFF_ROLES` — *"check `/honeypot status` lists the roles you expect, then turn the trap on again"* | *"…check the panel lists the roles you expect, then set the mode again"* |
| `:89–93` | `ALREADY_A_TRAP` — *"run `/honeypot forget {channel_id}`"* | *"…or press **Forget…** on `/honeypot`"*. ⚠️ This string is **served to the website** by `SETUP_REFUSED` (`api/tools/honeypot.py:85`), so it must read correctly on a web page too — prefer *"…or forget it from the honeypot panel or this page"* over either command spelling |
| `:94–97` | `NOT_A_TRAP` — *"`/honeypot status` lists the ones it knows about"* | *"`/honeypot` lists the ones it knows about"* |
| `:98–101` | `NOT_AN_ID` | **deleted** (above) |
| `:774–782` | the exempt "was already" sentence — *"`/honeypot status` lists the exempt roles"* | **deleted with `_change_exempt`** — the multi-select cannot be submitted "already exempt"; the list it sends IS the new list |
| `settings_store.py:516` | `honeypot_channel_ids` help — *"the trap channels; /honeypot setup fills this in"* | *"the trap channels; **Setup…** on `/honeypot` fills this in"* |
| `site/mock/server.mjs:311` | the same sentence, mirrored in the mock | the same rewrite — ⚠️ the mock and the registry must not drift, and `check.mjs` compares them |
| `tests/cogs/moderation/test_honeypot.py:688` | asserts `"/honeypot forget" in interaction.sent` | rewritten to the new `ALREADY_A_TRAP` wording |

**Site touch points** — the API needs **no** change. `api/tools/honeypot.py:8` imports `ban_hit`,
`make_trap_channel` and `recent_hits` **by name from the cog**, and this build moves none of the
three; no route is added, removed or renamed; `site/mock/contract.json` and `site/mock/check.mjs`
are **untouched** (the new `kind_via` heads in §F create no new *route*, and
`kind_via(kind, VIA_DISCORD)` returns the bare kind, so no existing row changes). Beyond §D's two
label rows and the `server.mjs:311` help-string rewrite, `page-honeypot.js` and `honeypot.html`
are untouched.

⚠️ **That unchanged import edge is the proof this build moved nothing**: `tests/api/tools/
test_honeypot.py` (135 lines) must stay green **with no edit** (§G).

**Docs rewritten in the same commit** (P15):

| Doc | What |
|---|---|
| `docs/access/sweeps.md:212–216` | the Phase 3 appendix's honeypot half — rewritten **in place**, not added to. It currently says *"Then `/honeypot setup` … `/honeypot status` (expect the resolved staff-role count > 0)"*; both become panel steps |
| `docs/access/OWNER_GUIDE.md` | ⚠️ **names honeypot NOWHERE today (measured, zero matches)** — so this build ADDS one "Catch the spam bots" row beside the existing feature rows, and moves the sweeps count in the header |
| `docs/info/feature-list.md:47` | the F9 row gains one clause: `/honeypot` is one command that opens a panel |
| `docs/info/phase3-design.md:114–121` | names `/honeypot setup [name]`, `/honeypot status`, `/honeypot mode`, `/honeypot exempt add\|remove` — gets a **dated "superseded by the panel" line at the top**, NOT a rewrite. The phase doc is the record of what was decided in Phase 3 |
| `docs/info/cutover-plan.md:53` | the Honeypot row names `/honeypot setup`; rewritten to the panel step |
| `docs/DONE.md:1782` | ⚠️ **NOT edited.** `DONE.md` is append-only and never rewritten (DOCS_STANDARD); the 2026-08-26 entry is a true record of what was run that day |
| `docs/info/panels-program.md:85` | the Honeypot row → built, with the measured `commands synced` before/after, and §3's totals line adjusted by seven subcommands |
| `docs/info/README.md` | a row for this file beside the other panel designs |
| `docs/TODO.md:257–264` | the honeypot bullet moves **WHOLE** to `DONE.md` at landing (global rule: an item moves once, at completion, and moves whole) |
| `docs/info/code-notes.md` | re-keyed at the merge. The honeypot anchors are at `black_bloc/cogs/moderation/honeypot.py:` **25, 26, 32, 33, 34, 39, 77, 110, 111, 175, 210, 211, 246, 310, 380, 427, 448, 537, 567, 614, 644, 647, 651, 730** (code-notes lines 154, 247, 248, 461, 468, 487–502, 732, 945, 957, 975, 979, 1190, 1196, 1457, 2263). ⚠️ **Four of those notes name a retired subcommand in their TEXT and need rewriting, not just re-pointing:** code-notes `:248` (*"for `/honeypot status`"*), `:497` (*"`/honeypot status` says so loudly"*), `:501` (*"`/honeypot status` prints the resolved staff roles"*), `:502` (*"`/honeypot forget <id>` covers the case the bot was offline for"*). Trust the anchor TEXT over the number |

## F. Extractions (P4) — one function per move, called by BOTH doors

⚠️ **The DB/move layer stays in the COG**, as it does for automod, applications and voice.
`api/tools/honeypot.py:8` imports three names from `cogs.moderation.honeypot`; moving them would
be a mechanical diff across two files for no gain this build needs, and keeping every existing
import byte-identical is what makes the unchanged assertions in `tests/api/tools/test_honeypot.py`
the proof the refactor changed nothing (wave-0 deviation 4).

**Already shared, reuse UNCHANGED:** `make_trap_channel` `:297` (takes `via`, builds its kind
with `kind_via` `:341`), `ban_hit` `:247` (same, `:289`), `recent_hits` `:196`, `hit_counts`
`:204`, `record_hit` `:138`, `get_hit` `:166`, `set_hit_action` `:171`, `banned_already` `:176`,
`offered_recently` `:185`, `do_ban` `:212`, `post_notice` `:366`, `test_category` `:355`,
`exempt_reason` `:112`, `trimmed` `:127`, `offer_text` `:131`, `ban_custom_id` `:108`,
`send_logs` (`actionlog.py:287`).

**New, module level in `black_bloc/cogs/moderation/honeypot.py`** — each does ONE write and ONE
log row, each takes `via: str = VIA_DISCORD` and builds its kind with `kind_via` (checklist 34),
each returns a `panels.Outcome` (`panels.py:21`) so a future route reads the same verdict the
panel does:

| Function | Replaces | Note |
|---|---|---|
| `set_mode(bot, guild, value, actor, *, via=VIA_DISCORD) -> Outcome` | inline `:688–708` | keeps the `NO_STAFF_ROLES` refusal `:693–695` so the panel and any future route refuse identically. ⚠️ Today's `log_action("honeypot.mode")` `:702` is **bare** — it gains `kind_via`, so a future route cannot double-post |
| `set_exempt_roles(bot, guild, role_ids, actor, *, via=VIA_DISCORD) -> Outcome` | the whole of `_change_exempt` `:763–798` | ⚠️ **ONE write of the WHOLE list**, ONE `kind_via("honeypot.exempt_set", via)` row carrying `details={"role_ids": [...], "added": [...], "removed": [...], "via": via}`. The added/removed diff is what keeps the log readable after the add/remove kinds go. Ids are de-duplicated and order-stable; a no-op submit (the list is unchanged) writes **nothing and logs nothing** and says so |
| `forget_trap(bot, guild, channel_id, actor=None, *, via=VIA_DISCORD) -> Outcome` | the method `_forget` `:732–747` | module level so both doors reach it; `on_guild_channel_delete` `:753` calls it with `actor=None` exactly as today. `log_action("honeypot.trap_removed")` `:740` gains `kind_via`. ⚠️ **The listener path keeps `via=VIA_DISCORD`** — a channel Discord deleted is not a website action |
| `save_settings(bot, guild, values, actor, *, via=VIA_DISCORD) -> Outcome` | **new** — the Settings sub-panel | `youtube.save_setup`'s shape and automod build deviation 10's: **validate every key before writing any**, then one `store.set` per key, then ONE `kind_via("honeypot.settings", via)` row |
| `status_lines(bot, guild, totals) -> list[str]` | the inline block `:665–678` | the panel embed and `/honeypot status`'s old output are ONE list. Takes the totals rather than the db, so it stays **synchronous and testable** |
| `arming_refusal(bot, guild) -> str \| None` | `:693–695` | `NO_STAFF_ROLES` when `store.staff_roles(guild)` is empty, else `None`. The mode select and `set_mode` read the SAME answer, so the control offered and the function's verdict can never disagree |
| `live_traps(bot, guild) -> list[int]` / `dead_traps(bot, guild) -> list[int]` | the `live` comprehension `:301–306` | ONE home for the fact that decides both whether `Setup…` renders (S2/S4) and whether `make_trap_channel` refuses. ⚠️ `make_trap_channel:301` is rewritten to CALL `live_traps` — that is the only edit inside a function this build otherwise leaves alone, and it must be byte-equivalent in behaviour |

**New pure module `black_bloc/honeypot.py`** — ⚠️ **this file does not exist today**; creating it
is the shape `black_bloc/youtube.py` and `black_bloc/pings.py` landed with (pings deviation 17).
Nothing already in the cog is renamed or re-homed, so `api/tools/honeypot.py:8`'s three imports
and every existing test are unchanged:

| New | Signature / content |
|---|---|
| `HoneypotMove` + `PANEL_MOVES` + `root_buttons(*, may_setup, may_forget, may_clear, has_site)` | §B/§C's tables AS DATA, proved by a parametrised test (P3) |
| `mode_options(current, may_arm) -> list[tuple[str, str, bool]]` | `HONEYPOT_MODES` minus `on` when `may_arm` is False, with the current one flagged. ⚠️ Option labels are **plain text** — no markdown, Discord renders none in a select |
| `trap_options(recorded, names) -> list[tuple[str, int, bool]]` | the Forget options, each carrying whether the channel still exists; a dead id still gets an option, labelled *a channel Discord no longer has (id)* |
| `exempt_defaults(role_ids) -> list[int]` and `EXEMPT_SELECT_MAX = 25` | the prefill for the `RoleSelect`, and the one place the cap lives (S6) |
| `exempt_diff(before, after) -> tuple[list[int], list[int]]` | the added/removed pair `set_exempt_roles` logs; pure, order-stable, de-duplicating |
| `PANEL_MINUTES_KEY = "honeypot_panel_minutes"`, `panel_minutes(store, guild_id)` | one-liners over `panels.panel_minutes` (`panels.py:119`), exactly as the twelve shipped panels do |
| `PANEL_TITLE`, `PANEL_TIMEOUT_FOOTER`, and the new panel sentences | wave-0 deviation 1: the footer is a whole sentence, not a format string |

⚠️ **`black_bloc/honeypot.py` may import `panels` at MODULE level** — unlike
`black_bloc/automod.py`, it is **not** imported by `settings_store.py`, so there is no import
loop to close (automod build deviation 4 is the counter-example; do not copy its function-local
imports here without cause). ⚠️ **Its test file is `tests/test_honeypot.py`, which does not
exist yet** — a second file of that basename beside `tests/cogs/moderation/test_honeypot.py`.
That works: `--import-mode=importlib` is set in `pyproject.toml` (CLAUDE.md), and
`tests/test_automod.py` + `tests/cogs/moderation/test_automod.py` are the shipped precedent.

**Two things to reuse, never re-copy:** `panels.answer` (`panels.py:36`) — the cog has no copy
today, keep it that way; and `panels.site_page_url(origin, "honeypot")` (`panels.py:123`), never
a private `SITE_PAGE` constant (the youtube copy pings deviation 6 deliberately left behind is
the counter-example).

**What to ADD to `black_bloc/panels.py`: nothing, this build.** No confirm helper is needed —
§I settles that arming the honeypot does **not** get a confirm step, for the reason automod's
F-A1 does: automod's `on` starts deleting and timing out immediately, whereas honeypot's `on`
only acts on somebody who posts in a channel whose pinned notice says not to.

## G. Tests (P16 — one file per source file, mirrored paths)

| File | What it gains, and what it keeps |
|---|---|
| `tests/cogs/moderation/test_honeypot.py` (768 lines) | ⚠️ **The listener, ban and Ban-now tests stay UNCHANGED in assertion** — `:320–:351` (the exemption matrix, trimming, the custom id, the offer text, the hits round-trip), `:362–:543` (every mode, the test-mode ban, the refused ban, the undeleteable post, staff/bots, exempt roles, non-trap channels, webhooks and DMs, the burst guard, all five Ban-now button paths), `:609–:681` (system messages, replies, threads, the delete refused outside the test category, the second shadow hit, another account's own button), `:716–:722` (the channel-delete listener), `:760–:768` (staff exempt because they see the staff channel). **That is the proof the catching path did not move**, and it is the strongest evidence this build can produce. The subcommand tests are rewritten to drive the panel: `:545–:607` (setup, exempt add/remove, status), `:682–:715` (setup refusing a second trap, forget, forget staff-only), `:723–:759` (mode refused with no staff, mode once staff resolve, status names the roles, status warns loudly). New: `/honeypot` answers ephemerally with a panel; **parametrised over S1–S7 × all three modes — each renders exactly its §B row and no other**; `on` is absent from the mode select in S1 and present otherwise; `Setup…` is absent in S3 and present in S2 and S4; `Forget…` is absent in S2; `Exempt nobody` is absent with an empty list; the `RoleSelect` is absent at 26 stored roles and its `default_values` are exact at 25; a no-op exempt submit writes nothing; a refused modal value writes **nothing** and does not re-render; every control calls `set_mode` / `set_exempt_roles` / `forget_trap` / `make_trap_channel` / `save_settings` with `via` untouched (mock them); `Logs` answers a NEW followup and still refuses a demoted staffer; a staffer demoted mid-panel moves nothing (`still_staff` at every site, reads included); `db_ready` after a defer, **and the four commands that skipped the DB check no longer can** |
| `tests/test_honeypot.py` | ⚠️ **NEW FILE.** `root_buttons` for every S2–S6 crossing; `mode_options` with and without `may_arm`; `trap_options` including a channel Discord no longer has; `exempt_defaults` at 0, 1, 25 and 26 ids; `exempt_diff` on add-only, remove-only, mixed, reordered (no diff) and duplicated input; `panel_minutes`; that every `PANEL_MOVES` entry is distinct and every select option label is plain text with no markdown characters |
| `tests/test_settings_store.py` | `honeypot_panel_minutes` round-trips, defaults 10, help mentions 15, is in `VALUE_KEYS`, refuses `-1` and the string `"15"` — the shape the shipped `*_panel_minutes` tests use |
| `tests/test_bot.py` | `LOGS_GROUPS` loses `honeypot` (`:12`); `"honeypot"` **stays** in `STAFF_COMMANDS` (`:26`); the tree-limit test **re-measures and expects 36 UNCHANGED** (`:179`) |
| `tests/api/tools/test_honeypot.py` (135 lines) | ⚠️ **must stay green with no edit** — the proof the layer did not move |
| `tests/test_logkinds.py` | `honeypot.mode`, `honeypot.trap_removed` and the new `honeypot.exempt_set` / `honeypot.settings` now go through `kind_via`; `honeypot.exempt_add` and `honeypot.exempt_remove` are gone from `ROUTINE` **and** from emission, so `::test_no_classification_entry_is_dead` (`:554`) and `::test_every_emitted_kind_is_classified` (`:535`) both still pass; ⚠️ `honeypot.exempt` (the LISTENER's kind) is **still emitted** at `:471` and stays in `ROUTINE` — a build that deletes it breaks `::test_every_emitted_kind_is_classified` from the other side |
| `tests/test_command_visibility.py` | ⚠️ **touched by the concurrent hide-when-off build.** This build does not edit `HIDDEN_WHEN_OFF`; if the merge order puts hide-when-off first, the honeypot row is already there and nothing here changes |

## H. §J — prove before merge (P17), and the sweep rows

1. `python -m black_bloc` boots; **read `commands synced` and record both numbers — the
   expectation is NO CHANGE, 36 → 36** (one group's slot becomes one command's slot). ⚠️ **If it
   moves, stop** — something other than this build broke. With no token, measure it the only
   other way: `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits`.
2. The parametrised state test: every state renders its row and no other (checklist 3, 12).
3. `python -c "import black_bloc.honeypot, black_bloc.cogs.moderation.honeypot,
   black_bloc.api.tools.honeypot, black_bloc.panels, black_bloc.settings_store"` — the substitute
   for a boot (wave-0 deviation 5), and the line that catches the two new import edges this build
   creates (the cog → `panels`, and the new pure module → `panels`). ⚠️ Importing
   `settings_store` in the same line is deliberate: it is what would have caught automod
   deviation 4's loop.
4. `ruff check black_bloc tests site`; full `pytest`; `node site/mock/check.mjs` — **state the
   page/route counts BEFORE and AFTER rather than trusting a number**; no route is added or
   removed, so they must match. ⚠️ The last recorded figure is **17 pages / 142 routes**
   (2026-09-04) and this document could NOT re-measure it (port 8788 was held by a concurrent
   worktree). `node --input-type=module --check < site/public/assets/labels.js`.
5. Checklist sweep before reporting — **1 and 2** (⚠️ *nothing in this build may change how a
   side effect is guarded or which kind a dry run gets*; the diff must show zero edits inside
   `do_ban` `:212`, `_delete` `:539`, `_caught` `:450`, `post_notice` `:366` and `test_category`
   `:355`), **8 and 30** (`AnswersErrors` on every modal, select and view), **11**
   (`allowed_mentions` on every interpolated send — this embed is nothing but channel and role
   mentions), **21** (the arming gate reads COMPUTED permissions through `store.staff_roles`,
   unchanged), **22** (the bounds that vanished with the `name: str | None` and
   `app_commands.Choice` parameters are rebuilt in the modal and the select), **26** (the
   list-typed `honeypot_exempt_role_ids` keeps a way to remove an entry — that is the select plus
   **Exempt nobody**; and `honeypot_channel_ids` keeps **Forget…**), **33** (§D), **34**
   (`set_mode`, `set_exempt_roles`, `forget_trap` and `save_settings` all gain `kind_via`).
6. ⚠️ **TEST MODE stands.** The bot speaks only in `#mute-me-bot-test-spam` (`TEST_CHANNEL_ID`)
   and DMs, enforced by `black_bloc/guard.py`. Run every sweep row in that channel. Three
   consequences worth stating rather than discovering: **(a)** `Setup…` creates the trap **inside
   the test channel's category** (`test_category` `:355–363`) and the pinned notice is **not
   posted** (`post_notice` `:368`, `NOTICE_NOT_POSTED`); **(b)** `do_ban` `:216–218` refuses
   every ban and logs `honeypot.would_ban`, so **while a guard is installed `on` behaves like
   `shadow`** — a sweep that flips the mode to `on` proves the CONTROL works and proves nothing
   about enforcement, and the row must say so; **(c)** the **Ban now** card is only posted when
   `log_channel_id` resolves a channel the guard allows (`_offer_ban` `:572–580`).
7. ⚠️ **Commit at clean boundaries, one layer at a time** (the ≥150k rule): (1) the new pure
   module + `tests/test_honeypot.py`, (2) the cog extractions (`set_mode`, `set_exempt_roles`,
   `forget_trap`, `save_settings`, `status_lines`, `arming_refusal`, `live_traps`/`dead_traps`)
   + their tests, (3) the panel itself, (4) the string, settings, log-kind and doc sweep — so a
   kill costs the last layer rather than the build. ⚠️ **`git stash` is never run in a shared
   tree** (two incidents, 2026-08-18); this build runs in its own worktree beside the
   hide-when-off build.

**Sweep rows — numbered by the CONDUCTOR at merge, not by this document.** `docs/access/sweeps.md`
holds **588 lines** and its last row is **182** today, ⚠️ **but the hide-when-off build is in
flight and adds at least one row of its own, so this document claims NO numbers and the build
writes them as `H1`–`H10` (letters on purpose, so a half-renumbered table cannot look
finished)** — the shape the role-menus build landed with. The Phase 3 appendix block at
`:212–216` is rewritten **in place**, not added to.

| Do this | Expect |
|---|---|
| `H1` — `/honeypot` as a Lead in `#mute-me-bot-test-spam` | ONE ephemeral panel: the whole block `/honeypot status` used to print — mode, resolved staff roles by name, trap channels, purge days, exempt roles, and the banned/shadow/failed/ignored tally — over **What the trap does… · Roles the trap ignores… · Setup… · Settings… · Refresh · Logs · Open on the site**. Nothing says `/honeypot status`, `/honeypot setup` or `/honeypot exempt` anywhere. ⚠️ One line says test mode contains the trap and nobody will be banned |
| `H2` — look at the mode picker while at least one staff role resolves | it offers **off · shadow · on**, with the current one already ticked. Then point `staff_channel_id` at a channel no role can see and re-open: it offers **off** and **shadow** and **NOT on**, and the panel says in words that no staff role resolves and what to set. Arming is not offered-and-refused; it is not offered |
| `H3` — `Setup…` → leave the name box as it arrives → submit | the trap is created **inside the test channel's category**, the reply names it and says the notice was not posted because of test mode, and the panel's **trap channels** line now names it. Re-open `/honeypot`: **Setup… is gone** — a second trap is not offered rather than offered-and-refused |
| `H4` — `Setup…` again after typing a name of 101 characters | ⚠️ it cannot be typed: the box stops at 100. This is the bound the `name` parameter used to carry |
| `H5` — post in the trap from a throwaway account, in `shadow` | ⚠️ unchanged from today: the message is deleted, a `honeypot.would_ban` card with a **Ban now** button appears in the test channel, nobody is banned, and a second post from the same account inside 10 minutes gets no second button. **This row is the proof the panel changed nothing about catching** and it is the most important row in the set |
| `H6` — `Roles the trap ignores…` → pick two roles | the reply says which were added, the **exempt roles** line above lists both, and the log holds exactly ONE `honeypot.exempt_set` row naming both. Open the picker again: **both are already ticked** |
| `H7` — `Roles the trap ignores…` → untick one and submit | the reply says which was removed and ONE more row is logged. Submitting again with no change says nothing changed and writes **no** row at all |
| `H8` — press **Exempt nobody** | the list empties, ONE row is logged, and the button disappears because there is nothing left to clear |
| `H9` — delete the trap channel in Server Settings, then `/honeypot` | the id is already forgotten (the channel-delete listener, unchanged) and **Setup…** is back. Then add a stale id by hand from the site's Settings page and re-open: the panel names it as *a channel Discord no longer has* and **Forget…** removes it with no id typed anywhere |
| `H10` — `Settings…` → `Numbers…` → purge days `9`, then `3`; then leave the panel `honeypot_panel_minutes` (10) minutes | `9` is refused in one sentence naming the 0–7 range and **nothing is saved** — not even the panel-minutes field that parsed; `3` saves both and leaves ONE `honeypot.settings` row; the panel then greys out with the *this panel has gone quiet* footer |
| `H11` — `Logs` | answers a **NEW** ephemeral message and the panel stays where it is |
| `H12` — turn `honeypot_mode` to `off` on the dashboard, wait ~60 s, then look for `/honeypot` | ⚠️ **the command is gone** — that is the hide-when-off build doing its job (§I). `/settings set-value honeypot_mode shadow`, or the portal, brings it back within ~60 s |

## I. The genuine forks — the owner decides, one at a time

**Settled first, by the standing rules, so they are NOT put to him:**

- ✅ **`/honeypot` stays staff-locked** (`default_permissions=STAFF_ONLY`) and `"honeypot"` stays
  in `STAFF_COMMANDS`. There is no member half of this feature.
- ✅ **Staff are re-checked before every move, reads included** (P8, pings deviation 10).
- ✅ **`on` is hidden rather than offered-and-refused** in S1 (P3/P9); so is `Setup…` in S3 and
  `Forget…` in S2.
- ✅ **Arming does NOT get a confirm step**, unlike automod's F-A1 = (a). Automod's `on` starts
  deleting messages and timing people out on the next message anybody sends; honeypot's `on`
  only acts on somebody who posts in a channel whose pinned notice says not to, after the trap
  has already been created deliberately. The `NO_STAFF_ROLES` refusal is the real safety rail,
  and it is unchanged. One press.
- ✅ **`Setup…` is not mode-gated** and creates the channel in all three modes — measured, §A's
  second red block. Adding a `would_setup` dry run would change behaviour, add a log kind and
  break two shipped tests.
- ✅ **The `Ban now` button on shadow-hit cards is left exactly as it is** (P14) — a persistent
  `DynamicItem` that belongs to the log channel, not to the caller, and already the owner's
  phone-side review surface during the shadow rollout. A verdict queue on the panel would be a
  third copy of what the card and `page-honeypot.js:37–62` already show.
- ✅ **The hits TABLE stays site-only.** The panel shows the four counts (`hit_counts` `:204`)
  and links to the page; a 25-option select over 50 hits with 500-character contents is a worse
  version of a table that already exists (one fact, one home — the surfaces corollary).
- ✅ **The shadow → enforce rollout rule is untouched.** The panel is a door onto `set_mode`;
  what makes the flip legitimate is still the owner's judgement from the shadow log
  (`cutover-plan.md:53`), not the existence of a picker.
- ✅ **`honeypot_mode → ("honeypot",)` STAYS in `HIDDEN_WHEN_OFF`** when the concurrent
  hide-when-off build adds it — the OPPOSITE of what `/rolemenu` and `/raidtrain` decided, and
  for a measured reason: those two ship with their mode **`off`**, so hiding the command would
  hide the only Discord door back on the day it lands. **`honeypot_mode` defaults to `shadow`**
  (`settings_store.py:1473–1474`), so `/honeypot` is visible out of the box and `off` is a
  deliberate "I do not want this feature" choice — exactly the state the owner asked to hide
  (2026-09-04 20:45, `TODO.md:213–215`).
  ⚠️ **The trade-off, said out loud rather than discovered:** with the command hidden, the
  panel's mode select is unreachable, and the ways back are **`/settings set-value honeypot_mode
  shadow`** (or `on`) and **the portal's Settings page**. P9's "the mode-off panel still opens
  and says so" survives only for the ≤60 s debounce/sync lag (`command_visibility.py:20–21`).
  `hide_commands_when_off` (default `true`, added by that build) turns the whole behaviour off
  for a server that dislikes it — checklist 33 both ways. **The panel's own copy must say this
  where a staffer will read it**: one line on the Settings sub-panel naming
  `/settings set-value honeypot_mode` as the way back.

**Three questions are genuinely his:**

- **F-H1 — how does staff EMPTY the exempt list, when the selection IS the list?**
  A `RoleSelect` prefilled with the current roles is one control for what used to be
  `exempt add` and `exempt remove`, and it is what the owner asked for. Removing the LAST role
  means submitting an EMPTY select at `min_values=0`, and ⚠️ **whether a real Discord client
  will submit an empty multi-select is unproven in this repo** — three shipped designs flag it
  (`raidtrain-panel-design.md:29`, events deviation 6, pings deviation 5) and none needed the
  answer, because clearing was always its own control. Here it is not.
  - **(a) The `RoleSelect` (`min_values=0`) PLUS an `Exempt nobody` button that renders only
    when the list is non-empty. Recommended.** It is the automod `Log only` shape exactly: the
    button is the fallback that works whatever the client does, and if the empty submit turns
    out to work, both doors call the same `set_exempt_roles(…, [])` and a later pass can drop
    one. Cost: two controls for one move — the single P3 exception in this design, called out
    in the build's deviations either way. **The staff-final-say rule decides this**: a stored
    decision staff cannot reverse from Discord is the state the rule forbids.
  - (b) The select alone, `min_values=0`, and accept that clearing may be impossible from
    Discord if the client refuses an empty submit (the dashboard could still clear it). One
    control, cleanest table — and it bets a reversal path on an unproven client behaviour.
  - (c) Keep two controls in the automod shape: a `RoleSelect` to ADD one role and a plain
    `Select` to REMOVE one. No empty-submit risk at all, and no cap problem (S6 disappears) —
    but it is exactly the two-spellings-of-one-move shape the owner's decision replaced, and it
    keeps the "was already exempt, so nothing changed" refusal the panel otherwise deletes.

- **F-H2 — is `Forget` a button or a picker?** `honeypot_channel_ids` is a LIST, and the state
  that needs forgetting most (S4, a recorded id Discord no longer has) is exactly the state
  where TWO ids can be recorded — the live check at `:301–306` only refuses a second trap while
  the first is alive, so a trap deleted while the bot was offline leaves its id behind and a new
  one is created beside it.
  - **(a) A `Forget…` BUTTON that opens a small card with a `Select` over every recorded id
    (live ones as `<#id>`, dead ones as *a channel Discord no longer has (id)*). Recommended.**
    One spelling in every state, one code path, one test; the label on each option says exactly
    what it forgets. Cost: two clicks in the ordinary one-trap case.
  - (b) A `Forget #🍯-do-not-post-here` button when exactly one id is recorded, and the card
    above when there are two or more. One click in the common case; two labels and two code
    paths for one move, and a state crossing that has to be tested both ways.
  - (c) A `Select` **"Forget a trap channel…"** directly on the root, no card. Fewest clicks of
    all — and it spends a whole root row on a control that is empty in the ordinary state, and
    puts a destructive-sounding picker permanently in front of the mode select.

- **F-H3 — does the panel get a control for `honeypot_purge_days`?** `/honeypot status` PRINTS
  it (`:670`) and no honeypot subcommand sets it; today it is reached through
  `/settings set-value` and the dashboard, so checklist 33 is already satisfied either way. This
  is automod's F-A3 with one fact reversed.
  - **(a) Yes — a second field on the Settings sub-panel's `Numbers…` modal, beside panel
    minutes, bounded 0–7. Recommended.** ⚠️ Automod answered its version **no**, because
    `automod_warn_threshold` and `mod_dm_on_action` belong to moderation as a WHOLE and a
    control on the automod panel would quietly edit the mod commands' behaviour.
    `honeypot_purge_days` is read by exactly two places, **both inside this feature** (`do_ban`
    `:221`, `ban_hit` `:262`) — measured — so that argument does not apply, and the number a
    Lead most wants to change while arming the trap is how much of the spammer's history goes
    with them.
  - (b) No — it stays a read-only line on the root embed and the Settings card names the
    Settings page. One fewer field, one fewer bound to rebuild (checklist 22), and consistent
    with automod's answer at the cost of being inconsistent with the fact.

## J. What NOT to build, and what this costs

**Not in this build:**

- **Anything inside the catching or banning path.** `on_message` `:429`, `_caught` `:450`,
  `_delete` `:539`, `_offer_ban` `:569`, `_lock` `:592`, `do_ban` `:212`, `_dm_before_ban`
  `:234`, `ban_hit` `:247`, `BanNowButton` `:380`, `record_hit` `:138` through `hit_counts`
  `:204`, `exempt_reason` `:112`, `post_notice` `:366`, `test_category` `:355`. The single
  edit inside an otherwise-untouched function is `make_trap_channel:301` calling `live_traps`
  (§F), and it must be behaviour-identical.
- **A `would_setup` dry run.** §I, settled — checklist 1 is already met by `test_category` +
  `post_notice`.
- **The hits table, a verdict queue, or a per-hit card on the panel.** §I, settled.
- **Any new API route or site control.** No `/api/honeypot/*` route is added, removed or
  renamed; `site/mock/contract.json` and `check.mjs` are untouched.
- **Touching `HONEYPOT_MODES` or `HONEYPOT_PURGE_MAX_DAYS`.** Three modes, seven days, decided
  in Phase 3.
- **Editing `HIDDEN_WHEN_OFF`.** The concurrent hide-when-off build owns
  `command_visibility.py` and `tests/test_command_visibility.py`; this build must not touch
  either, or the two branches conflict textually. §I only records which way the decision goes.
- **`count` / `important_only` on `Logs`.** Lost exactly as they were for `/request`, `/apply`,
  `/voice` and `/automod`; the site's Logs page has both.
- ⚠️ **REPORT, do not fix — three measured defects found while writing this.**
  **(1)** The website can set `honeypot_mode` to `on` through the **generic settings API**,
  which validates against `KEY_CHOICES` (`settings_store.py:277`) only — so **the arming
  refusal (`:693`) does not apply on the web path**, and a guild with no resolved staff role can
  arm the trap from the dashboard, where one mistyped moderator message is a real ban. Wiring
  `set_mode` into the settings route is a settings-API change, not a panel change, and belongs
  in its own pass. This is the same defect automod reported (`automod-panel-design.md` §J item
  1) and it is a `KNOWN_ISSUES.md` candidate. **The same bypass applies to
  `honeypot_exempt_role_ids`**, which the site writes with no `honeypot.exempt_set` row at all.
  **(2)** `LOG_LEVEL_COMMANDS` (`settings_store.py:783–797`) holds **13** rows, and **10 of
  them name a subcommand that no longer exists** (`pings` → `pingroles`, `tempvoice` → `voice`,
  `events` → `event`, `poll`, `birthday`, `golive`, `request`, `applications`, `rolemenu`,
  `chat`) — so ten `*_log_level` help strings are already wrong. Automod build deviation 9
  reported eight of thirteen; the rolemenu and chat panels have landed since, making it ten.
  This build removes an eleventh (`honeypot`), which does not improve the ten. Only `mod` and
  `modmail` are still correct. It wants one pass of its own.
  **(3)** `NO_STAFF_ROLES` (`:78–84`) tells the reader to run **`/settings set staff_channel_id`**
  — but the registry's subcommand for a channel-typed key is `/settings set`, and
  `staff_channel_id` is written by `set` while roles go through `set-role`; the sentence is
  right today and becomes wrong the moment the `/settings` panel lands (`TODO.md:303–306`,
  `show`/`set`/`set-role`/`set-value`/`clear` all retire). Flag it in the report so the
  `/settings` build sweeps it rather than this one guessing at the future wording.

**Cost.** Measured wave-3 builds: automod **370k**, chat **441k**, raidtrain **473k**, role
menus **529k**. ⚠️ Automod's own note stands — *treat a band as a floor, not a midpoint*; four
of five wave-2 builds ran over.

Sizing this one against automod, the closest comparison:

| Factor | Automod (370k) | Honeypot | Direction |
|---|---|---|---|
| leaf subcommands | 8 | **7** | cheaper |
| cog size / share untouched | 830 lines, ~450 untouched → ~380 rewritten | **802 lines, ~450 untouched** (`:108`–`:410` plus `:429`–`:596`) → **~200 rewritten** | **much cheaper** |
| cog test file | 861 lines, engine half must not move | **768 lines, listener half must not move** | slightly cheaper |
| new pure module + new test file | none — both existed | ⚠️ **BOTH new** (`black_bloc/honeypot.py`, `tests/test_honeypot.py`) | **the single biggest cost against automod** |
| sub-panels | 3 (rule card, exemptions, arming confirm) | **1–2** (Settings, and Forget if F-H2 = (a)) | cheaper |
| modals | 2 | **2** (name, numbers) | level |
| new log kinds / retired classification entries | 1 added | **2 added** (`honeypot.exempt_set`, `honeypot.settings`), **2 retired from `ROUTINE`** with a suite tripwire (`::test_no_classification_entry_is_dead`) | dearer |
| site route change | none | **none** | level |
| string / doc rewrite sites | 11 | **~14** (§E), plus four `code-notes.md` notes whose TEXT changes | slightly dearer |
| unproven client edge | `min_values=0` with a fallback (`Log only`) | **`min_values=0` load-bearing** — the exempt list IS the select (F-H1) | dearer in care, not in tokens |

**Estimate: 320–380k Opus tokens.** The much smaller rewrite surface and one fewer sub-panel
pull below automod; the two new files, the log-kind retirement with its suite tripwire and the
25-role data-loss guard pull above it. Well under chat (441k) and raidtrain (473k), which each
folded two groups and fifteen-plus subcommands.

**Prep before dispatch** (per the ≥150k rule): clean tree, a fresh usage read, its own worktree
(the hide-when-off build holds another), and a brief that carries
[`review-checklist.md`](review-checklist.md), [`panels-program.md`](panels-program.md), this
file and the §H layer order, plus the standing rules that **`git stash` is never run in a shared
tree** and **TEST_MODE is never flipped**.

**Review link for the report** — the panel is Discord-only, so the reviewable surfaces are
`/honeypot` in `#mute-me-bot-test-spam` and the dashboard page it links to:
`https://<dashboard-origin>/honeypot.html` (the origin is the deployment's own; `site_page_url`
builds it from `panels.py:123`). The report names both, plus the `H1`–`H12` rows above.

## Build deviations — what the build did differently, and why

> Written by the build agent on `worktree-agent-a7ea6b0dbeac7f753`, off `932f34e`, 2026-09-05.
> **Status: BUILT, not shipped.** `pytest` **4593 passed** (4539 on `main` before), `ruff check`
> clean over `black_bloc` and `tests`, `node --input-type=module --check` clean on
> `site/public/assets/labels.js`. ⚠️ **Nothing has met live Discord** — no boot, no token, no
> sync, no panel opened, no trap created, nothing deployed.

**The three forks, as BUILT** (decided by the conductor on this document's recommendation;
owner confirmation pending — each reverses in one place):

- **F-H1 = (a)** — a `RoleSelect` at `min_values=0` whose selection IS the exempt list, PLUS an
  **Exempt nobody** button that renders only when the stored list is non-empty. **To reverse to
  (b)**: drop `CLEAR_EXEMPT_MOVE` from `black_bloc/honeypot.py`'s `PANEL_MOVES` and the
  `may_clear` branch of `root_buttons`, and drop the `CLEAR_EXEMPT` arm of `MoveButton.callback`.
  Both doors already call the same `set_exempt_roles(…, [])`, so nothing else moves.
- **F-H2 = (a)** — **Forget…** is a button opening a card with a picker over every recorded id,
  dead ones labelled *a channel Discord no longer has (id)*. **To reverse to (c)** (the picker on
  the root): move `ForgetPick` into `build_root` and delete `build_forget` / `render_forget` /
  `open_forget` and the `FORGET` arm of `MoveButton.callback`.
- **F-H3 = (a)** — `honeypot_purge_days` is a second field on the Settings `Numbers…` modal.
  **To reverse to (b)**: drop the `purge` field from `NumbersModal` and the
  `"honeypot_purge_days"` entry from `SETTINGS_KEYS`; the number stays a read-only line on the
  Settings card and on the root embed, and `/settings set-value` still reaches it.

**Numbered deviations from this document:**

1. **`arming_refusal` and the move functions live in the COG, not in `black_bloc/honeypot.py`** —
   as §F says for the DB layer, and for the same reason: `api/tools/honeypot.py` imports three
   names from the cog by name, and keeping every existing import byte-identical is what makes
   `tests/api/tools/test_honeypot.py` passing **with no edit** the proof the refactor changed
   nothing. The pure module holds only what a test can read without a bot.
2. **`live_traps`/`dead_traps` are built on a third helper, `recorded_traps`** — the raw list is
   read in five places (`status_lines`, `build_forget`, `forget_trap`, `root_buttons`,
   `trap_names`) and three of them wanted the ids rather than the live/dead split.
3. **`exempt_editable(role_ids)` is the cap predicate, not a bare `len(...) <= 25` at each call
   site.** §F named `EXEMPT_SELECT_MAX` and `exempt_defaults`; the panel needs the *question*
   ("may this be edited here?") in one place, because `build_root` and `status_lines` must agree
   or the picker vanishes with nothing said.
4. **`exempt_sentence(added, removed)` is in the pure module** rather than assembled in
   `set_exempt_roles`. It is the half of the move a test can check without a database, and it
   keeps the cog function to one write and one log row.
5. **The Settings card carries `MODE_IS_OFF_WAY_BACK`.** §I asked for this line and did not put
   it in a table; it renders on the Settings sub-panel, where a staffer changing the panel's
   behaviour will read it.
6. **The purge-days bound is enforced by the REGISTRY, not re-parsed in the modal.** The modal
   rebuilds the *floor* (a whole number, ≥ 0) and states the ceiling in its field label; the
   ceiling itself is `KEY_MAX["honeypot_purge_days"]`, raised by `coerce_value` inside
   `save_settings` before anything is written. One home for the number, and the refusal sentence
   is the registry's own (*"cannot be more than 7"*), which is what the dashboard says too.
7. **The `Numbers…` field labels are class-level constants** rather than assigned per instance —
   `discord.ui.TextInput.label`'s setter is deprecated in discord.py 2.7.1 (`use discord.ui.Label
   instead`) and every assignment logs a `DeprecationWarning`. Automod and youtube still do it;
   this build declined to add two more.
8. **`ARMED_WITH_NO_TRAP` renders whenever the mode is `on` and no LIVE trap exists** — §B put it
   in S2 (nothing recorded) only, but S4 (a recorded id Discord no longer has) is the same
   condition for the person reading it: the trap is armed and there is nothing to fall into.
9. **The panel's state test parametrises four conditions, not seven.** S5 (a non-empty exempt
   list), S6 (more than 25 roles) and S7 (test mode) are each proved by their own focused test
   instead of crossing them with the mode, because none of the three interacts with the mode at
   all and the crossing would assert the same thing twelve times.

**Reported, not fixed — measured while building:**

- ⚠️ **The website can still write `honeypot_mode` and `honeypot_exempt_role_ids` through the
  GENERIC settings API**, which validates against `KEY_CHOICES` only. So `set_mode`'s arming
  refusal does **not** apply on that path — a guild with no resolved staff role can arm the trap
  from the dashboard, where one mistyped moderator message is a real ban — and the exempt list
  can be rewritten with **no `honeypot.exempt_set` row at all**. Wiring the shared functions into
  the settings route is a settings-API change, not a panel change. Same defect automod reported
  (`automod-panel-design.md` §J item 1); a `KNOWN_ISSUES.md` candidate.
- ⚠️ **`LOG_LEVEL_COMMANDS` (`settings_store.py`) now holds 12 rows and TEN of them name a
  subcommand that no longer exists** — `pings`→`pingroles`, `tempvoice`→`voice`,
  `events`→`event`, `poll`, `birthday`, `golive`, `request`, `applications`, `rolemenu`, `chat`.
  Only `mod` and `modmail` are correct. This build removed an eleventh (`honeypot`), which does
  not improve the ten. One pass of its own.
- ⚠️ **`NO_STAFF_ROLES` tells the reader to run `/settings set staff_channel_id`** — right today,
  wrong the moment the `/settings` panel lands and `show`/`set`/`set-role`/`set-value`/`clear`
  retire. Flagged for the `/settings` build to sweep rather than guessed at here.

**NOT verified:** no boot, so `commands synced` was measured only through
`tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits` (**36 before, 36 after**);
no live Discord, so whether a client submits an empty `min_values=0` select is **still unproven**
(F-H1's fallback is what makes that safe); `node site/mock/check.mjs` was not run — a concurrent
worktree held 127.0.0.1:8788 — so the 17 pages / 142 routes figure is quoted from 2026-09-04 as an
OLD reading. No route was added, removed or renamed and `contract.json` / `check.mjs` are
untouched, so the counts cannot have moved.
