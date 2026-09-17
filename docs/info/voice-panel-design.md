# Temp voice — `/voice` is ONE command that opens a panel (wave 2)

> **Audience:** the build agent and the reviewer, and the owner for §I. **Status:** TRACKED ·
> ✅ **SHIPPED v73 `4d64b36` 2026-09-03 22:08** (built on `worktree-agent-a386d425f5527fe95`;
> `clamped` folded into `panels.py` at the merge) — see the `## Deviations` foot for
> what differs and what was measured. ⚠️ Several numbers in the body below were measured against
> `main` at `1735ff8` and were already stale at build time; the Deviations foot carries the
> re-measured ones.
>
> ⚠️ **Since then:** the **Logs** button's lost `count` / `important_only` (see §J *"Not in this
> build"*) came back at **v96** as **Show more** / **Important only** buttons under the list
> ([`logs-buttons-design.md`](logs-buttons-design.md)), and the `Forget my settings` confirm is
> drawn by the shared `panels.confirm` since the confirm/opened fold (**v88**, sweep row **275**) —
> one builder, the same card.
>
> **Last verified: 2026-09-11 09:20** (the header; the body is as at the design). Measured this pass
> against `main` at `f3ae743` (v108 live): the pure `black_bloc/tempvoice.py` holds `CARD_BUTTONS`,
> `panel_state`, `card_buttons` and `people_controls` (deviation 1);
> `cogs/community/tempvoice.py` holds `has_voice_role`, `may_open` (deviation 4), `stray_lobbies`
> and `lobby_choices` (deviation 6), `voice_health` (deviation 9) and `status_lines`;
> `settings_store.py` registers `voice_panel_minutes` (int) and `TEMPVOICE_MODES` is still
> `("off", "on")` — no `shadow`; deviation 8's fold LANDED — `clamped` exists **once**, in
> `black_bloc/panels.py`, and neither the pings nor the tempvoice cog carries a copy; the sweep rows
> are **135–143** in [`../access/sweeps.md`](../access/sweeps.md) (deviation 11), not the 104-onward
> the body predicts. Fork **F1 = (a)**: the owner re-confirmed 2026-09-03 21:20 (*"Leave it as is"*),
> so the in-channel control post is untouched and still is. ⚠️ **NOT checked this pass:** anything
> in Discord or a browser — nothing booted, no panel opened, no channel made.
>
> Before that, **2026-09-03** — every `path:line` below was READ against `main` at `1735ff8`, in
> `black_bloc/cogs/community/tempvoice.py` (1986 lines), `black_bloc/panels.py`,
> `black_bloc/api/tools/tempvoice.py`, `black_bloc/settings_store.py`,
> `black_bloc/command_visibility.py`, `black_bloc/personas.py`, `black_bloc/logkinds.py`,
> `tests/test_bot.py`, `docs/access/sweeps.md`, `docs/info/code-notes.md`. Measured, not assumed:
> `TEMPVOICE_MODES = ("off", "on")` (`settings_store.py:69`) — **there is no `shadow` mode for temp
> voice**, so every "off/shadow/on" crossing below is a two-way one; `command_visibility.py:16–20`
> has **no** tempvoice entry, so nothing vanishes when the mode is off; `tests/test_bot.py:198`
> asserts **42** top-level commands today; `docs/access/sweeps.md` holds **95 rows, numbered to
> 102**; `docs/access/OWNER_GUIDE.md` names neither `/voice` nor `/tempvoice` (zero matches).
> ⚠️ **NOT verified: anything was run.** No boot, no pytest, no ruff, no `check.mjs`, nothing
> against live Discord. Whether the client submits an EMPTY `UserSelect` at `min_values=0` is the
> same unproven edge [`events-panel-design.md`](events-panel-design.md) flags — this design needs
> no empty submit, so it does not depend on the answer.
>
> **Inherits every invariant in [`panels-program.md`](panels-program.md) §2 (P1–P17) and its §4
> library — none restated here.** Template: [`requests-panel-design.md`](requests-panel-design.md),
> whose `## Deviations` foot is the trap list. The two shipped wave-1 designs to copy shape from are
> [`applications-panel-design.md`](applications-panel-design.md) and
> [`events-panel-design.md`](events-panel-design.md). Feature behaviour is
> [`phase3-design.md`](phase3-design.md) Part A.

## A. Measured today — two groups, twenty-two subcommands

`tempvoice` is a `Group` (`:1390`, `default_permissions=STAFF_ONLY`); `voice` is a `Group`
(`:1394`, **member-visible**, no `default_permissions`). **4 + 18 = twenty-two leaf subcommands
over two top-level slots.**

| Subcommand | Line | Who | Calls · what is INLINE in the cog |
|---|---|---|---|
| `/tempvoice setup [name]` | `:1694` | `require_staff` `:1699` | `make_creator_channel` `:734` — shared with the site |
| `/tempvoice forget <channel_id>` | `:1711` | `require_staff` `:1714` | id parse inline `:1716–1721` (`NOT_AN_ID` `:182`), then `forget_creator` `:192` |
| `/tempvoice status` | `:1743` | `require_staff` `:1745` | ⚠️ **all inline** `:1749–1776`: the eight status lines + `STRAY_LOBBIES` `:158` over `lobbies_by_name` `:227` |
| `/tempvoice mode <off\|on>` | `:1778` | `require_staff` `:1786` | ⚠️ **inline** `:1788–1800`: `store.set` + reply + `log_action("tempvoice.mode")`. **No `kind_via`** |
| `/voice logs` | `:1850` | `send_logs` carries its own `require_staff` | `send_logs(interaction, "tempvoice", count, important_only)` |
| `/voice rename <name>` | `:1863` | owner, via `_act` `:1841` | `do_rename` `:902` |
| `/voice limit <people>` | `:1868` | owner | `do_limit` `:917` |
| `/voice lock` · `unlock` | `:1875` `:1879` | owner | `do_privacy(…, "connect", True\|False)` `:929` |
| `/voice hide` · `show` | `:1883` `:1887` | owner | `do_privacy(…, "view_channel", True\|False)` `:929` |
| `/voice kick <member>` | `:1891` | owner | `do_kick` `:968` |
| `/voice ban <member>` | `:1896` | owner | `do_ban` `:977` |
| `/voice unban` · `unpermit` | `:1901` `:1911` | owner | `do_forget_member(…, "unban"\|"unpermit")` `:1012` |
| `/voice permit <member>` | `:1906` | owner | `do_permit` `:996` |
| `/voice claim` | `:1918` | anyone connected — `owner_only=False` | `do_claim` `:1191` |
| `/voice transfer <member>` | `:1922` | owner | `do_transfer` `:1177` |
| `/voice bitrate <kbps>` | `:1929` | owner | `do_bitrate` `:1144` (+ `clamp_bitrate` `:1050`) |
| `/voice region <region>` | `:1937` | owner; autocomplete `_region_options` `:1942` → `region_choices` `:1064` | `do_region` `:1160` |
| `/voice info` | `:1948` | owner | `info_lines` `:1098` + `remembered_lines` `:1118` — both pure |
| `/voice reset` | `:1962` | anyone with the role | ⚠️ **inline** `:1965–1981`: `clear_prefs` `:531` + `tempvoice.prefs_reset` + `PREFS_CLEARED`/`NOTHING_REMEMBERED` |

**Not a subcommand and NOT moving** (P14): the per-channel **control post**
(`TempVoicePanel` `:1303`, a persistent view re-registered in `cog_load` `:1403`, posted by
`_post_panel` `:1632`) and its `MemberPickView` `:1281`. That post belongs to the room. See fork
**F1** — it is the one thing here the program does not settle.

**The gate, measured** (`_voice_allowed` `:1802`, called by `_voice_target` `:1817`): guild →
`may_use_voice(tempvoice_allowed_role_id, user)` `:265` → `_database_ready` `:1687`.
⚠️ **`may_use_voice` has no staff bypass**, so a Lead without the allowed role cannot run `/voice`
today at all. `pick_row` `:271` then picks the channel: the one you are CONNECTED to if you own it,
else any row you own; with `owner_only=False` it returns only the connected one.

**`tempvoice_mode` gates CREATION ONLY** (`_maybe_create` `:1515`). An existing channel keeps
working with the mode off, and no command is hidden — `command_visibility.HIDDEN_WHEN_OFF`
(`:16–20`) has no tempvoice key.

## B. The decision — one `/voice`, member panel and staff panel

**`/voice` becomes a single `app_commands.command`; both `Group`s go and `/tempvoice`
disappears.** `commands synced` drops by **one** relative to whatever it is when this lands (two
top-level slots become one) — **42 → 41** on `main` today. ⚠️ **State the delta, not the number:**
the build **re-measures** and edits `tests/test_bot.py:198` to what it reads (requests deviation 7).

⚠️ **The one command keeps `/voice`'s posture — no `default_permissions`, member-visible.** So
`"tempvoice"` leaves `STAFF_COMMANDS` (`tests/test_bot.py:49`) and `"voice"` stays in
`MEMBER_COMMANDS` (`:70`). The staff half is gated at runtime by `still_staff` (`panels.py:29`),
never by the UX lock.

**Root panel** — `build_panel(bot, guild, actor)`, one ephemeral embed + a `Panel` subclass,
split on `store.is_staff(actor)` (P2). ⚠️ **Staff bypass the allowed-role gate** — the
staff-final-say rule (`CLAUDE.md`, owner 2026-09-03) forbids a state staff cannot reach, and today
a Lead without the Member role cannot reach Setup or Mode at all. A staffer without the role gets
the staff row and a line saying why there is no card of their own.

**The five states, crossed with the mode** (there are two modes, not three):

| # | Where the caller is | mode `on` | mode `off` |
|---|---|---|---|
| S0 | no allowed role, not staff | `VOICE_NEEDS_ROLE` `:120` as the whole embed; `Refresh` only | same |
| S1 | owns none, in none | `NO_OWNED_CHANNEL` `:124` naming the lobby; `Forget my settings` (only with prefs) · `Refresh` | + a line: join-to-create is off, so joining the lobby makes nothing |
| S2 | owns one (`pick_row` `:271`) | the **owner card**, §C | **identical** — the mode never touches a channel that exists |
| S3 | in someone else's, owner NOT connected | `Claim` (success) · `Refresh`; the embed names the absent owner | same |
| S4 | in someone else's, owner IS connected | no `Claim` (it would only ever answer `OWNER_STILL_HERE` `:92`); the embed says whose it is and to ask for **Hand it over** | same |
| S5 | staff, crossed with any of S0–S4 | + the **staff row** and the status block | + the same, and the mode button reads **Turn join-to-create on** |

P3 in one line: **no state renders a control whose shared function would refuse it.** `Claim` only
in S3; `Lock` **or** `Unlock`, never both; `Move someone out…` only when somebody else is
connected; `Undo for…` only when the channel actually lets somebody in or keeps somebody out;
`Forget my settings` only when `get_prefs` `:470` returns a row.

## C. The cards, the sub-panels, the modals

Each is a **re-render in place**, `retire(previous)` first (P6), `defer()` then
`edit_original_response` (P5), `db_ready` on every click (requests deviation 6), `still_staff`
before every staff move (P8).

**The owner card.** Embed = `info_lines(channel, row, role_ids)` `:1098` + `remembered_lines(prefs)`
`:1118`, both unchanged — the card the panel shows and the lines `/voice info` showed must never be
two shapes.

| Row | Control | Rendered when | Shared function |
|---|---|---|---|
| 0 | `Rename` → modal | always | `do_rename` `:902` |
| 0 | `Limit` → modal | always | `parse_limit` `:253` → `do_limit` `:917` |
| 0 | `Unlock` when locked else `Lock` — **one button** | always | `do_privacy(…, "connect", want)` `:929` |
| 0 | `Show` when hidden else `Hide` — **one button** | always | `do_privacy(…, "view_channel", want)` `:929` |
| 0 | `Bitrate` → modal | always | `do_bitrate` `:1144` |
| 1 | `People…` → sub-panel | always | — |
| 1 | `Region…` → sub-panel | always | — |
| 1 | `Hand it over…` → sub-panel | always | `do_transfer` `:1177` |
| 1 | `Forget my settings` (danger) → `Yes, forget it` / `Keep it` | `get_prefs` `:470` is not `None` | `reset_prefs` (§F) |
| 1 | `Refresh` | always | — |

Locked / hidden come from `privacy_of(channel)` `:1089`, which reads the channel's own `@everyone`
overwrite — the same source `info_lines` uses, so the button and the line can never disagree.

**People sub-panel** — one row per question, `Back` on row 4:

| Row | Control | Rendered when | Shared function |
|---|---|---|---|
| 0 | `UserSelect` "Let someone in…" | always | `do_permit` `:996` |
| 1 | `UserSelect` "Keep someone out…" | always | `do_ban` `:977` |
| 2 | `Select` "Move someone out…" over `connected_ids(channel)` `:313` minus the owner, ≤25 with `capped_placeholder` (`panels.py:56`) | somebody else is connected | `do_kick` `:968` |
| 3 | `Select` "Undo for…" over `member_lists(channel.overwrites, owner_id, role_ids)` `:1069`, each option carrying its kind | either list is non-empty | `do_forget_member(…, "unban"\|"unpermit")` `:1012` |

⚠️ **Row 3 is why `unban` and `unpermit` do not become two buttons.** One control, options that
already know which undo they are — P3's "never two spellings of one move", and it is the only
surface that can tell a member who is actually banned here.

**Region sub-panel** — ⚠️ `VOICE_REGIONS` `:47` holds **26** entries and a Discord select caps at
25, which is exactly the bug `region_choices` `:1064` hides today (§J findings). So: **one select of
the 25 NAMED regions** (`VOICE_REGIONS` minus `AUTO_REGION` `:46` — 25 exactly, no cap, no
placeholder needed), plus an **`Automatic`** button and `Back`. Both write through `do_region`
`:1160`, which already maps `auto` to `rtc_region=None`.

**Hand it over… sub-panel** — one `UserSelect` "Who should own it?" + `Back` → `do_transfer`
`:1177`, whose `channel_lock` + fresh-row re-read (`:1178–1188`) is the race guard; `CLAIM_LOST`
`:104` stays its refusal.

**The staff row** (row 2 of whatever card is showing) and the staff embed block:

| Control | Rendered when | Shared function |
|---|---|---|
| `Setup` → one-field modal, prefilled with `tempvoice_creator_name` | always | `make_creator_channel` `:734` — **defer first** (it creates a channel; checklist 24) |
| `Forget a lobby…` → `Select` over `tempvoice_creator_ids` **plus** the strays `lobbies_by_name` `:227` found, ≤25 | at least one id or stray | `forget_creator` `:192` |
| `Turn join-to-create off` / `on` — **one button that says what it will do** | always | `set_mode` (§F) |
| `Logs` → a NEW ephemeral followup (P11) | always | `send_logs(interaction, "tempvoice")` — keeps its own `require_staff` |

Row 3 for staff: `Select` **"A channel…"** over `rows_for_guild` `:430` (≤25, `capped_placeholder`)
→ the **staff card** for any open temp channel: its `info_lines`, `Hand it over…` (the same
`do_transfer`, so staff can always leave a stored `owner_id`; the displaced owner is DM'd one line
— see §F `staff_hand_over`) and `Back`. ⚠️ **No `Close it` button** — Discord's own channel delete
already works and `on_guild_channel_delete` `:1735` cleans the row, so a second door would be a
duplicate, not an override.

Row 4: `Open on the site` (link, `tempvoice.html` — `logkinds.py:97`) when an origin is configured
**and the caller is staff** — the page is behind `staff_dependency` (`api/tools/tempvoice.py:82`),
so offering it to a member is P9's dead control.

**The staff embed block** is today's `/tempvoice status` lines `:1757–1773` plus `STRAY_LOBBIES`
`:158`, written out always rather than hidden behind a `Status` button (the events build's
deviation 10 precedent: a button that hides the loudest warning loses it).

**Modals** — all `AnswersErrors` + `discord.ui.Modal`, one shape (P12). `RenameModal` `:1211` and
`LimitModal` `:1228` are **reused unchanged** except that they take the panel's re-render callback
instead of answering; `Bitrate` and `Setup` are two new one-field modals of the same shape.
`panels.NoteModal` is **not** used — nothing here sends a person a free-text reason.

## D. Settings (P13 · checklist 33)

| Key | Type | Default | Status |
|---|---|---|---|
| `voice_panel_minutes` | `int` | **10** | **NEW.** How long the panel stays live. Help text carries KI-20's warning verbatim in shape (15+ loses the "gone quiet" footer, because Discord's interaction token expires at 15 minutes). Registered exactly where `applications_panel_minutes` is — `settings_store.py:825` `KEY_TYPES`, `:864` `KEY_HELP`, `:1499` `default()` — but **in its own appended block** so parallel wave-2 branches merge textually |

**Existing keys this panel READS, all untouched:** `tempvoice_mode` (`:172`, choices `:276`,
default `"on"` `:1307`), `tempvoice_creator_ids` (`:173`), `tempvoice_name_template` (`:174`),
`tempvoice_creator_name` (`:175`), `tempvoice_allowed_role_id` (`:176`), and `tempvoice_log_level`
through `send_logs`.

**Nothing else here is a decision.** The 25 cap and the 5-per-row cap are Discord's; the button
table is the state machine in §B; the region list is Discord's; and the two behaviours a reader
might mistake for decisions — staff bypassing the allowed-role gate, and staff being able to
reassign any channel — are **settled by the standing staff-final-say rule**, not chosen here, so
neither becomes a key.

## E. What goes away, and every line that names it

`/help` reads the tree (`cogs/core.py:88`), so it follows with no edit (P15). ⚠️
`tests/cogs/test_core.py:379–382` mention `/tempvoice` but build a **fake** tree of their own —
measured, no change needed there.

| Thing | Where | Becomes |
|---|---|---|
| `tempvoice` Group + 4 children | `:1390`, `:1694`, `:1711`, `:1743`, `:1778` | the staff row and the staff embed block |
| `voice` Group + 18 children | `:1394`, and the §A table | buttons, selects, sub-panels |
| `_act` `_voice_target` `_voice_allowed` | `:1841`, `:1817`, `:1802` | `voice_gate` + the pure `panel_state` (§F) |
| `region_choices` + `_region_options` | `:1064`, `:1942` | **deleted** — no autocomplete behind a button, and the Region sub-panel has no 25-cap problem to solve |
| `NOT_AN_ID` | `:182` | **deleted** — nothing types an id any more; `api/tools/tempvoice.py` imports `NOT_A_LOBBY`, not this |
| `NOTHING_REMEMBERED` | `:140` | **deleted** — `Forget my settings` renders only when there is something to forget (P9), and `remembered_lines(None)` `:1121` already says "nothing yet" |
| `LOGS_GROUPS["voice"]` | `tests/test_bot.py:13` | **deleted** — `/voice` is no longer a Group with a `logs` child, so the loops at `:175` and `:221` would `KeyError` |
| `STAFF_COMMANDS "tempvoice"` | `tests/test_bot.py:49` | **deleted** (§B) |
| `assert len(top) == 42` | `tests/test_bot.py:198` | **one lower than whatever the build measures** — never a hard-coded absolute |
| `HIDDEN_WHEN_OFF` | `command_visibility.py:16–20` | **nothing to change** — measured, temp voice has no entry |

**Strings that name a retired subcommand and are rewritten in the SAME commit** — each currently
tells somebody to run something that will not exist:
`cogs/community/tempvoice.py:129` (`CLAIM_NEEDS_A_CHANNEL` — "run `/voice claim` again") ·
`:138` (`PREFS_CLEARED` — "`/voice info` shows it") · `:156` (`EXTRA_LOBBIES` — "`/tempvoice
forget <id>`") · `:160` (`STRAY_LOBBIES` — "Run `/tempvoice setup`") · `:175` (`NOT_A_LOBBY` —
"`/tempvoice status` lists the ones it knows about") · `:625` (`where_sentence` — "Run `/tempvoice
setup` again") · `:1140` (`remembered_lines` — "`/voice reset` forgets all of it") ·
`settings_store.py:510` ("`/tempvoice setup` fills this in") · `black_bloc/personas.py:89`
(⚠️ **the chat bot's own answer about voice channels**).

**Site touch points** — the API itself needs no change (`api/tools/tempvoice.py` imports functions
and strings, and this build moves none of them), but two mock copies of a rewritten string drift
otherwise: `site/mock/server.mjs:305` (the `tempvoice_creator_ids` help text) and `:3391` (the mock's
copy of `NOT_A_LOBBY`). `site/public/assets/labels.js:47–52` names no command — measured, untouched.
No route is added or removed, so `node site/mock/check.mjs` must report the **same** page/route
counts before and after.

**Docs rewritten in the same commit** (P15): `docs/access/sweeps.md:78` (row 19), `:79` (row 20),
`:132` and `:138–139` (the Phase 3 appendix script) — rewritten in place, not added to;
`docs/info/architecture.md:103` and `:177`; `docs/info/feature-list.md:46`;
`docs/info/phase3-design.md` gets a dated "superseded by the panel" line at the top, **not** a
rewrite (`:53–67` describe the control post and the setup commands);
`docs/info/panels-program.md:77` (the Temp voice row → shipped);
`docs/access/OWNER_GUIDE.md` — ⚠️ **it names neither command today (measured, zero matches)**, so
this build ADDS one "Give people their own voice rooms" row beside the birthdays row (`:69`) and
moves the sweeps count (`:8`, `:71`); `docs/info/code-notes.md` re-keyed at the merge — the
tempvoice anchors cluster at `:3–5`, `:154`, `:181`, `:229`, `:302`, `:312–350`, `:363–374`,
`:388–394`, `:464–499`, `:714–717`, `:975`, `:1193–1195`, `:1458–1459`.

## F. Extractions (P4) — one function per move, called by BOTH doors

⚠️ **The DB/move layer stays in the COG**, as it does for applications and **not** as it does for
events. `api/tools/tempvoice.py:8–25` imports seventeen names from the cog; moving the layer would
be a large mechanical diff across a 1986-line cog and a 1900-line test file for no gain this build
needs. Every existing import stays byte-identical, which is what makes the existing tests' unchanged
assertions the proof the refactor changed nothing (wave-0 deviation 4).

**New, module level in `cogs/community/tempvoice.py`** — each does ONE write and ONE log row, each
returns a `Said` `:788`, each takes `via: str = VIA_DISCORD` and builds its kind with `kind_via`
(checklist 34):

| Function | Replaces |
|---|---|
| `set_mode(who, value)` | inline `:1788–1800`. ⚠️ Today's `log_action("tempvoice.mode")` is **bare** — it gains `kind_via`, so a future route cannot double-post |
| `reset_prefs(who)` | inline `:1965–1981` — `clear_prefs` `:531` + the `tempvoice.prefs_reset` row + `PREFS_CLEARED` `:135` |
| `staff_hand_over(who, channel, row, target)` | `do_transfer` `:1177` **plus** a best-effort DM to the displaced owner naming who has it now (staff final say: a person affected is told). The member's own `Hand it over…` keeps plain `do_transfer` — they are the person affected |
| `voice_gate(interaction) -> bool` | `_voice_allowed` `:1802`, answering through `panels.answer` on every branch and **letting staff through the role check**. ⚠️ The trap: `_voice_allowed` calls `interaction.response.send_message` directly, which after a `defer()` is requests deviation 11 all over again |
| `lobby_choices(bot, guild, rows)` | the stray-lobby half of `/tempvoice status` `:1755–1756`, so `Forget a lobby…` and the embed read one list |

**Pure, into a NEW `black_bloc/tempvoice.py`** (there is none today; nothing existing moves into it,
so no import outside the cog changes):

| New | Signature |
|---|---|
| `VoiceMove` + `CARD_BUTTONS` + `card_buttons(state, *, locked, hidden, has_prefs, others_here, has_lists)` | §B/§C's tables AS DATA, proved by a parametrised test |
| `panel_state(rows, user_id, here_id, connected_ids) -> str` | `none` · `owner` · `orphan` · `guest`, from the same rules `pick_row` `:271` and `do_claim` `:1191` apply, with **no** Discord objects |
| `PANEL_MINUTES_KEY = "voice_panel_minutes"`, `panel_minutes(store, guild_id)` | one-liners over `panels.panel_minutes` (`panels.py:76`), exactly as `requests.py:510` |
| `PANEL_TITLE`, `PANEL_TIMEOUT_FOOTER`, and the new panel sentences | wave-0 deviation 1: the footer is a whole sentence, not a format string. It names the CHANNEL, not the command |
| `undo_options(permitted, banned) -> list[tuple[int, str]]` | the "Undo for…" options and which kind each carries |
| `named_regions()` | `VOICE_REGIONS` minus `AUTO_REGION` — **25 exactly**, which is what removes the cap problem |

⚠️ `VOICE_REGIONS` `:47` and `AUTO_REGION` `:46` **move** into the pure module and are re-exported
from the cog by name, so no import outside the cog changes and the existing region tests keep their
assertions.

**Two things to reuse, never re-copy:** `cogs/community/tempvoice.py:870 answer()` is a
byte-for-byte copy of `panels.py:18 answer()` — import the library's and delete this one (the same
dedup `applications-panel-design.md` §F made for `role_menus.py`). And `panels.option_label`
(wave-0 deviation 2) for the "A channel…" / "Undo for…" option labels.

**The panel passes the `interaction` itself** to every `do_*`, exactly as `TempVoicePanel` `:1303`
does today: `Doer` `:799` is the shape (`client`, `guild`, `user`, `via`) and an `Interaction`
already satisfies it, with `panel_log` `:859` falling back to `VIA_DISCORD`. **No `do_*` signature
changes.**

## G. Tests (P16 — one file per source file, mirrored paths)

| File | What it gains |
|---|---|
| `tests/cogs/community/test_tempvoice.py` (1986 lines today) | `/voice` answers ephemerally with a panel; **parametrised over S0–S5 × both modes — each renders exactly its §B row and no other**; `Lock` and `Unlock` are never both present; `Claim` renders in S3 and never in S2 or S4; `Move someone out…` is absent with an empty channel; `Undo for…` is absent with no by-name entries and carries the right kind per option; `Forget my settings` is absent with no prefs; every button calls its existing `do_*` with `via` untouched (mock it); a staffer WITHOUT the allowed role still gets the staff row; a member never gets `Setup` / `Mode` / `Logs` / the site link; `Logs` answers a NEW followup and still refuses a demoted staffer; a staffer demoted mid-card moves nothing (`still_staff` at every site); `db_ready` after a defer; `Setup` defers before creating; timeout disables every item and a re-render `retire`s what it replaced |
| `tests/test_tempvoice.py` (**new file**) | `card_buttons` for every state × locked/hidden/prefs/occupancy; `panel_state` against the same rules `pick_row` and `do_claim` use; `undo_options`; `named_regions()` is **exactly 25**; `panel_minutes` |
| `tests/test_settings_store.py` | `voice_panel_minutes` round-trips, defaults 10, has help text |
| `tests/test_bot.py` | `LOGS_GROUPS` loses `voice`; `tempvoice` leaves `STAFF_COMMANDS`; `voice` stays in `MEMBER_COMMANDS`; the tree-limit test **recounts** |
| `tests/api/tools/test_tempvoice.py` (unchanged) | ⚠️ **must stay green with no edit** — that is the proof the layer did not move |
| `tests/test_logkinds.py` | `tempvoice.mode` now goes through `kind_via` (`tests/test_logkinds.py:127` already allows the feature's `f'tempvoice.{kind}'` form) |

## H. §J — prove before merge (P17), and the sweep rows

1. `python -m black_bloc` boots; **read `commands synced` and record both numbers** — the drop must
   be exactly one (requests deviation 7; checklist 10 — a check that could not run is not a check
   that passed). With no token, measure it the only other way:
   `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits` counts the real tree.
2. The parametrised state test: every state renders its row and no other (checklist 3, 12).
3. `python -c "import black_bloc.tempvoice, black_bloc.cogs.community.tempvoice,
   black_bloc.api.tools.tempvoice, black_bloc.personas"` — the substitute for a boot, and it is
   what catches the one new import edge this build creates (wave-0 deviation 5).
4. `ruff`; full `pytest`; `node site/mock/check.mjs` (**expect the counts unchanged** — no route
   changes); `node --input-type=module --check < site/public/assets/labels.js`.
5. Checklist sweep before reporting — **8** and **30** (`AnswersErrors` on every modal, select and
   view), **11** (`allowed_mentions` on every interpolated send — display names are all over this
   feature), **22** (`parse_limit` `:253` and `clamp_bitrate` `:1050` still bound the modals; a
   modal has no `app_commands.Range`), **24** (defer before `Setup` and before every rename —
   `RENAMED_TOO_OFTEN` `:116` exists because Discord caps renames at 2 per 10 minutes), **26** (the
   list-typed `tempvoice_creator_ids` keeps its way to remove an entry — that is `Forget a lobby…`),
   **27** (occupancy from `connected_ids` `:313`, never `channel.members`), **33** (§D), **34**
   (`set_mode`'s new `kind_via`) — and **15/17**, the duplicate `answer()` (§F).

**Sweep rows — this feature takes 104 onward.** `docs/access/sweeps.md`'s last row today is **102**;
⚠️ **row 103 is claimed by another build in flight, so start at 104 and renumber at landing.**
⚠️ **They landed as 135–143** — the file's last row was 134 by the time the build ran, and staff
reassigning somebody else's channel got a ninth row (deviation 11). The table below keeps the
design's numbering; read it as 135 onward.
Rows 19, 20 and the Phase 3 appendix block are rewritten in place, not added.

| # | Do this | Expect |
|---|---|---|
| 104 | `/voice` with no temp channel of your own | one ephemeral panel saying to join the lobby by name — and no Rename/Lock/Claim anywhere |
| 105 | Join the lobby, then `/voice` | your channel's card: Rename · Limit · **Lock** · **Hide** · Bitrate, then People… · Region… · Hand it over… · Refresh |
| 106 | `Lock`, then re-open the panel; `Hide`, then re-open | the button now reads **Unlock** / **Show** — never both, and the lines above it agree |
| 107 | `People…` → let someone in, keep someone else out, then `Undo for…` | the two names appear on the undo select with the right word each; undoing puts the channel's own rules back and it is remembered for next time |
| 108 | `Region…` → pick one, then `Automatic`; `Bitrate` → 96 | the region changes and is remembered; `Automatic` says Discord picks; a bitrate above the boost level says so |
| 109 | Leave your channel, have somebody else join it and run `/voice` | with you gone they see **Claim** and it works; with you still in it they see no Claim and are told to ask you for **Hand it over** |
| 110 | `/voice` as staff | adds the status block, `Setup`, `Forget a lobby…`, **Turn join-to-create off**, `Logs`, `A channel…` — Logs answers a NEW message and the panel stays |
| 111 | `Setup` with a name; then `Forget a lobby…`; then `Turn join-to-create off` and re-join the lobby; then leave the panel `voice_panel_minutes` minutes | setup says **repaired / took it over** (never a second lobby); forgetting removes it from the list; with the mode off joining makes no channel and existing ones still work; the panel goes quiet with the footer |

## I. The genuine forks — the owner decides, one at a time

Settled first, by the standing rules, so they are NOT put to him:

- ✅ **Staff bypass the allowed-role gate.** *"Never design a terminal state staff cannot leave"* —
  today a Lead without the Member role cannot reach `/tempvoice setup` at all (`may_use_voice`
  `:265`). §B settles it.
- ✅ **Staff can reassign any open temp channel** through `A channel…` → `Hand it over…`, and the
  displaced owner is DM'd (`staff_hand_over`, §F). `owner_id` is a stored decision, so it gets a
  staff override.
- ✅ **The command is `/voice`, member-visible.** [`panels-program.md`](panels-program.md) §3 already
  names it, and it is the half a member types a hundred times to the staff half's one.
- ✅ **`/voice` does not vanish when the mode is off.** The owner answered this shape on 2026-09-03
  13:47 ("Visible") for applications, and temp voice has no `HIDDEN_WHEN_OFF` entry to remove.

**One question is genuinely his:**

- ✅ **F1 ANSWERED: (a), "Leave it as is"** — the owner, 2026-09-03 21:20, re-confirming an earlier
  answer. The in-channel control post is untouched, and still is at v108.
- **F1 — the in-channel control post.** Every spawned channel gets a persistent post with eleven
  always-visible buttons (`TempVoicePanel` `:1303`, posted by `_post_panel` `:1632`). After this
  build it is a second door onto the same functions, and it is the only surface left in the app that
  shows a member a button for a move they cannot make right now (Claim on a channel you already own;
  Unban with nobody banned). P14 says persistent posts are outside the program; the owner's
  one-surface-one-question rule pulls the other way.
  - **(a) Leave it exactly as it is.** Zero build cost, no restart risk, and it is how a member
    discovers the controls without having heard of `/voice`. **Recommended.**
  - (b) Rebuild its buttons from the same `card_buttons` table and re-render it on
    `on_voice_state_update` — one shape everywhere, but that is a message edit per join and leave,
    and channel edits here are already rate-limit-sensitive (`RENAMED_TOO_OFTEN` `:116`).
  - (c) Drop the post; `/voice` is the only door. Simplest story, and it costs the discovery: nothing
    else tells a member the controls exist.

## J. What NOT to build, and what this costs

**Not in this build:**

- **The persistent in-channel post and `MemberPickView`** — P14, and fork F1 above. Whatever he
  picks, (b) and (c) are a *separate* build, not a rider on this one.
- **Moving the shared layer out of the cog.** §F. Events did it because its new functions needed it;
  nothing here does, and `api/tools/tempvoice.py`'s seventeen imports are the reason not to.
- **Any new API route or site control.** No `/api/tempvoice/*` route is added, removed or renamed;
  `site/mock/contract.json` is untouched; the two mock string copies in §E are the only site edits.
- **A `Close it` / delete button.** Discord's own delete plus `on_guild_channel_delete` `:1735`
  already covers it; a second door would duplicate, not override.
- **Per-guild region shortlists, a bitrate preset picker, or anything `/voice` does not do today.**
  This is a door swap, not a feature pass.
- **`count` / `important_only` on `Logs`.** Lost exactly as they were for `/request` and `/apply`;
  the site's Logs page has both. ⚠️ **Given back at v96** to all eighteen Logs buttons as **Show
  more** / **Important only** under the list, plus the `logs_count` and `logs_important_only` keys
  — [`logs-buttons-design.md`](logs-buttons-design.md).
- **Touching `TEMPVOICE_MODES`.** Two modes, not three — do not add `shadow` to make it rhyme with
  other features.

**Cost.** Wave-1 builds measured **376k–458k** Opus tokens. This one is at the **top of that band —
budget 420–480k**: twenty-two subcommands (five more than applications, the largest so far), a
1986-line cog and a 1986-line test file, four sub-panels, a brand-new pure module with its own test
file, and nine doc/string rewrite sites. **Prep before dispatch:** clean tree, a fresh usage read,
and a brief that tells the agent to commit at clean boundaries — one layer at a time (pure module +
tests, then the cog panel, then the doc/string sweep), so a kill costs the last layer rather than
the build.

## Deviations

Written by the build agent, 2026-09-03, on `worktree-agent-a386d425f5527fe95`. Everything not
listed here was built as this document says.

**Measured, before and after** (from the worktree, `.venv` at the main checkout):

| | before | after |
|---|---|---|
| top-level commands (`test_the_command_tree_stays_inside_discords_limits`) | **39** | **38** |
| tests | **4050 pass** | **4265 pass** |
| `ruff check .` | clean | clean |
| `node site/mock/check.mjs` | 17 pages, 142 routes | **17 pages, 142 routes** |
| `node --input-type=module --check < site/public/assets/labels.js` | parses | parses |
| `tests/api/tools/test_tempvoice.py` | green | **green, not edited** |

⚠️ **NOT verified: anything against live Discord.** No boot (`python -m black_bloc`, invariant
P17) — this build has no token and must not look for one. No panel opened, no channel created,
no DM sent, no select submitted by a real client. The substitute is
`python -c "import black_bloc.tempvoice, black_bloc.cogs.community.tempvoice,
black_bloc.api.tools.tempvoice, black_bloc.personas"`, which passes, plus the parametrised
state test. The design's §B claim of "42 → 41" was stale twice over — the tree had already
dropped to 39 through the other wave-2 merges — which is exactly why §B says to state the
delta and re-measure. The delta is one, as predicted.

1. **`card_buttons` takes `staff`, `mode_on` and `has_lobbies`, and there is no separate
   `CARD_BUTTONS(state, …)` signature as §F spelled it.** §F asked for
   `card_buttons(state, *, locked, hidden, has_prefs, others_here, has_lists)`, but
   `others_here` and `has_lists` govern the **People sub-panel's** selects, not the card, and
   the staff row hangs off the same state the card does. Splitting it the way §F spelled it
   would have let a state exist in the member half and not the staff half, which is precisely
   what the parametrised test is meant to make impossible. So: **one** `card_buttons` for the
   whole §B/§C root table including the staff row, and a second tiny
   `people_controls(*, others_here, has_lists)` for the sub-panel. `CARD_BUTTONS` survives as
   the flat tuple of every move, which the test uses to prove no button was invented outside
   the table.

2. **`Forget a lobby…` is a BUTTON that opens a sub-panel, not a `Select` on the staff row.**
   Discord allows five action rows. The owner card uses rows 0 and 1; the staff row is 2;
   `A channel…` is a select and needs all of row 3; `Open on the site` is row 4. There is no
   sixth row for a second select. As a button it also gets a place to explain itself, which a
   bare select does not.

3. **`Forget a lobby…` lists ONLY the stored `tempvoice_creator_ids` — the strays are NOT on
   it.** §C says the select covers the ids "plus the strays `lobbies_by_name` found".
   `forget_creator` returns `False` for anything not in the id list, so a stray on that select
   would be a control the shared function refuses — the one thing P3 forbids. The strays are
   still named, in the staff status block, by `STRAY_LOBBIES`, whose sentence was rewritten to
   point at **Setup** (which adopts and repairs them) or at deleting the channel. Both of those
   do something.

4. **`voice_gate` refuses only a DM and a database that is down; the allowed-role check became
   part of the state.** §F describes `voice_gate` as replacing `_voice_allowed` "letting staff
   through the role check", but §B S0 renders `VOICE_NEEDS_ROLE` **as a panel**, with `Refresh`.
   Those two cannot both be true of one function, and §B wins: a refusal that also shows you
   the door is better than one that does not. `may_open` (staff **or** the role) feeds
   `panel_state`'s `allowed` flag; `has_voice_role` stays separate so a staffer without the role
   can still be told why they have no card of their own.

5. **`Forget my settings` renders in every state past the role gate, not only S1 and S2.** §B's
   table lists it on the "owns none" row and §C lists it on the owner card, which would leave a
   member standing in somebody else's channel unable to forget their own remembered settings —
   a valid move, hidden. `reset_prefs` touches the member's preferences and never the channel,
   so nothing about the state can make it invalid. It is still absent in S0, where the caller
   has no business with the feature at all.

6. **`lobby_choices` and `stray_lobbies` are two functions, not the one `lobby_choices(bot,
   guild, rows)` §F names.** The staff embed needs the strays; the select needs the stored ids
   (deviation 3); `status_lines` needs both. Two named functions read better than one that
   returns a pair and is destructured at three call sites, and `stray_lobbies` is the one that
   replaced the inline half of `/tempvoice status`.

7. **`RenameModal` and `LimitModal` keep BOTH paths rather than "taking the panel's re-render
   callback instead of answering".** Fork F1 = (a) says the in-channel control post is left
   exactly as it is, and that post is these two modals' other caller. With `previous=None` they
   behave byte-for-byte as they did; with a view they go through `act_on_own`. Rewriting them
   to only re-render would have changed the post's behaviour, which F1 forbids.

8. **`clamped` was copied into the cog rather than added to `panels.py`.** `cogs/content/pings.py`
   already carries the identical four lines, so this is knowingly a second copy and a checklist-15
   smell. Adding it to `panels.py` would edit a file that three other unmerged wave-2 branches are
   also editing, and a clean textual merge is worth more than one-fact-one-home for four lines.
   ⚠️ **This is a job for the conductor at merge**: fold `clamped` into `panels.py` and delete both
   copies. `code-notes.md` carries the same note against the line. ✅ **Done at the merge** —
   `clamped` and `DESCRIPTION_LIMIT` live once in `black_bloc/panels.py`; re-measured 2026-09-11,
   there is still exactly one `def clamped` in the tree and neither cog carries a copy.

9. **`voice_health` reads the reconcile loop's health off the cog through `bot.get_cog`.** The
   panel builders are module-level (they are called from the command, from every button and from
   the tests) while `last_ok_at` / `last_error` live on the cog instance. Every miss degrades to
   "not yet" / "none" rather than raising, so a bot without the cog loaded still renders.

10. **The staff card has no `Close it` and no `Forget this room`, as §J asks — but it also has no
    embed of the member's own prefs.** `info_lines` alone, plus `Hand it over…` and `Back`. The
    remembered-settings block belongs to the person whose settings they are, and a staffer
    looking at somebody else's room has no business with it.

11. **Row 20 and the Phase 3 appendix block in `sweeps.md` were rewritten in place, as asked;
    row 19 too. `OWNER_GUIDE.md` gained the "Give people their own voice rooms" row and its
    sweeps count moved 134 → 143.** The design said the rows start at 104; the file's last row
    was **134**, so this build's are **135–143** — nine, not eight, because staff reassigning
    somebody else's channel (the settled §I fork, with its DM) had no row of its own and now
    has 143.

12. **`tests/cogs/test_core.py:test_help_marks_the_staff_commands_the_real_bot_registers` needed
    one edit after all.** §E says that file only builds a fake tree — true of two of its three
    `/tempvoice` mentions, but this third one asserts against the REAL tree and had to move to
    `/voice`. Measured, not assumed: the other two are fixtures and are untouched.

13. **The `Bitrate` modal bounds 8–96 itself, which `/voice bitrate` never had to.** The
    subcommand carried `app_commands.Range[int, MIN_BITRATE, MAX_BITRATE]` and Discord did the
    refusing; a modal has no such thing, and `clamp_bitrate` would have taken `500` to 96 and
    reported it as done — `do_bitrate`'s "as high as your boost level allows" line only fires
    when the GUILD capped it, not when the clamp did. Checklist 22 in its literal sense: the
    bound that vanished with the parameter had to be rebuilt where the value now enters.

### Lobby in the main voice area (v117, 2026-09-17)

Built on `tempvoice-lobby`, off `91bee8a`. The owner's two asks, verbatim: *"Let's move it up to
the main voice channel area but keep its visibility staff only, when we swap off shadow mode it
should become visible to whatever permissions inherit from the voice group"* and, told the
test-mode guard would strand the rooms, *"Do a, would the spawned channels be visible to
everyone?"* — (a) being *let the bot delete what it made itself*. Neither is a change to
`/voice`'s panel; both are the two things that had to move before the lobby could leave the test
channel's category.

1. **`guard.allows_place` gained one clause: a channel Black Bloc owns is an allowed place.**
   `tests/test_guard.py::test_owning_a_channel_does_not_widen_where_channels_may_be_deleted` pinned
   the opposite decision on purpose and is now
   `::test_owning_a_channel_lets_black_bloc_delete_what_it_made` — owned means `allows_place`
   True and `delete_channel` passes through, an unowned channel outside the test category is still
   refused, and `disown_channel` takes it back. Nothing else in `guard.py` moved; the refusal
   sentence, the delete log line and the boot `WARNING` were reworded to name both reasons, because
   *"sits outside the test channel's category"* on its own is no longer why. Checklist 35: the
   reversal is written into the `guard.py:70` rows of `code-notes.md`, which is where that contract
   was actually recorded — no design doc carried a DECIDED bullet for it.

2. **New key `tempvoice_room_overwrites`, enum `lobby` | `category`, default `lobby`.** A spawned
   room's overwrites used to start from `category_overwrites(creator.category)`, so a staff-only
   lobby sitting in a public category would have spawned rooms everyone could see — the
   question the owner asked. With `lobby` the room starts from the **lobby channel's own**
   overwrites instead; with `category`, today's behaviour. The room is still *created* in the
   lobby's category — only the permission source moves — and everything layered on top
   (owner, locked/hidden, allowed roles, permitted/banned, the bot itself) is untouched.
   `owner_overwrites`' keyword `category=` is now `source=`, since it takes either.

**Three departures from the brief, all reported:**

- **`may_act_in` — the cog's own place gate — had to move too, and the brief did not name
  it.** It is a second, independent gate that `allows_place` knows nothing about: it compares
  `channel.category_id` to the test channel's and is what the website's room edits
  (`api/tools/tempvoice.py:95`, the `OUTSIDE_TEST_ROOM` sentence) and `repair_creator_channel` ask.
  It gained the same owned-channel clause, so a room in the main voice area is still editable from
  the dashboard.
- **`may_spawn_from` is new, and it is the one thing without which the feature would have been
  inert.** The `TODO.md` finding said a moved lobby *"would spawn rooms the bot can never clean
  up"*; measured, it would have spawned **nothing at all** — `_maybe_create` asks
  `may_act_in(lobby)` before it creates anything, and the lobby is neither owned nor in the test
  category. Widening `allows_place` alone would therefore have shipped a lobby that quietly did
  nothing until `TEST_MODE` lifted, which is option (b) the owner turned down. `may_spawn_from`
  allows a lobby the guild has **written down** (`tempvoice_creator_ids`) and nothing else; the
  room is owned the instant it exists, which is the protection the category check used to buy.
- **`repair_creator_channel` was deliberately left refusing.** It rewrites the lobby's overwrites
  from its **category**, so letting it run on a moved, staff-only lobby would undo the very thing
  the move is for. Pressing **Setup** on `/voice` against a lobby outside the test category still
  answers `OUTSIDE_TEST_CATEGORY` while test mode is on. That sentence was left as it is, because
  for the lobby it is still both true and the reason.

**Not done, and why:** nothing on Discord. The lobby's `parent_id` move and its overwrites are the
owner's/conductor's step after v117 boots, and no room was ever spawned, deleted or looked at in a
client — every claim here is from the test suite. `TEST_MODE=true` was never touched.

Tests **5986 → 5991**, forward and under `BB_REVERSE=1`; `ruff check .` clean; `node
site/mock/check.mjs` **19 pages / 175 routes / 14 core settings, all keys present**.
