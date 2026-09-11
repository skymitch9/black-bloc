# Events — `/event` is ONE command that opens a panel (wave 1)

> ⚠️ **PARTLY SUPERSEDED, 2026-09-10** by [`when-picker-design.md`](when-picker-design.md): `EventModal`
> and the typed `My time zone` modal are both gone. Propose opens a DRAFT PANEL with Day / Hour /
> Minute / How long dropdowns and a text modal that never refuses; `My time zone` opens a `ZonePanel`
> dropdown whose 25th option is the old typed box. §D's "598 zones cannot fit a 25-option select" is
> still true and is exactly why that option exists. Everything else here — the panel, the card, the
> button tables, the settings sub-panel — is unchanged and still current.

> ⚠️ **AND PARTLY SUPERSEDED AGAIN, 2026-09-10/11** by [`where-picker-design.md`](where-picker-design.md)
> and its three follow-ups (v105 `3205c0f` · v106 `6c10b9d` · v107 `ac43a20` · v108 `73e2e44`): the draft
> panel has a fifth **Where** button opening a `WherePanel` (ChannelSelect over voice/stage/text, a typed
> box beside it, **Clear**, **Back**); `events.where_kind` + `where_channel_id` are new columns
> (**schema 33 → 34**); a typed link is masked and gets an **Open link** button on the review card; a
> shorthand such as `ttv/skyaiva` is normalised at entry and a bare host is a link at render time; and
> the link is tried once with a bounded GET before it is kept. **Six new settings keys in the Events
> group** this §D predates — `events_scheduled_name_template`, `events_test_retention_minutes`,
> `events_where_link_in_description`, `events_where_link_aliases`, `events_where_link_check`,
> `events_where_link_check_seconds` (plus `raidtrain_scheduled_name_template` on the sibling feature).
> Sweeps **329–350**. Everything else here still stands.

> **Audience:** the build agent and the reviewer. **Status:** TRACKED · ✅ **LIVE since v64** (`e670542`, merged `--no-ff` 2026-09-03 after Fable review,
> deployed 14:05, `deploys.log` line 63; synced 43 app commands — **29** today — not run against Discord
> by eye). Still live at **v108** (`73e2e44`, 2026-09-11 00:37), with the two banners above naming what
> changed on top of it. Built on
> `feat/events-panel` (worktree branch `worktree-agent-a448c7ab780ed3c2b`, commits `9a1beb4`
> code, `d85274e` tests, `fbaf046` docs, `e6030c5` a one-constant cleanup; the branch is also
> tagged `feat/events-panel` at the same commit).
> **Since then, beyond the two banners:** **v78** (`3429233`) gave `events_mode` a `HIDDEN_WHEN_OFF`
> entry (`command_visibility.py:22`), so `/event` DOES vanish while the mode is off, behind
> `hide_commands_when_off`; **v92** (`4b327cf`) made the staff **Yes** re-ask `may_cancel`; the
> confirm cards elsewhere folded onto `panels.confirm` at **v88** while the events withdraw card was
> deliberately left unfolded.
> **Last verified: 2026-09-11 08:52** — re-measured in this tree at `1d090e5`: both §D keys are
> registered under the names given (`event_panel_minutes`, `event_panel_own_list`) in a **202**-key
> registry, beside **fourteen** `events_*` keys — seven more than the "seven existing" §D counted,
> every one of them added by the When/Where work the banners name. `SCHEMA_VERSION` is **34**;
> `site/mock/contract.json` **150 routes / 17 pages**; sweeps run to row **350** and the events rows
> are **73–79** plus **323–327** (When) and **329–350** (Where).
> ⚠️ **NOT checked in this pass:** anything in a Discord client or a browser, no boot, no pytest, no
> ruff, no `check.mjs` run; in particular the "one flaky test" at the foot was **not re-run**, so
> whether it still flakes under `-n auto` is unknown.
> **Before that, 2026-09-03** on that branch: `ruff check .` clean, **3502 tests pass** (3442 at
> the base `d3da02c`), `commands synced` measured at **43** through
> `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits`, and
> `import black_bloc.events, black_bloc.cogs.community.events, black_bloc.api.tools.events,
> black_bloc.chat_data, black_bloc.knowledge` succeeds. The `path:line` references below were
> read at `9a326ac` and are **stale by design after the move** — §F relocated most of them from
> `cogs/community/events.py` into `black_bloc/events.py`; trust the anchor text, not the number.
> ⚠️ **NOT verified:** anything against live Discord — no panel has been opened, no button
> pressed, no modal submitted, and the bot was never booted (no token in this environment; the
> import check is the substitute, as in wave 0 deviation 5). In particular, **whether the client
> submits an EMPTY `ChannelSelect`/`RoleSelect` when `min_values=0` is still unproven** — the
> library permits `0` (`discord/components.py` `SelectMenu` docstring, discord.py 2.7.1) and the
> code handles the empty submit, but only a person in Discord can say whether it arrives. §C's
> fallback (`Forget…`) was BUILT alongside it so clearing works either way — deviation 6. The 598
> zones in §B are this machine's `tzdata` (`zoneinfo.available_timezones()`, measured), not a
> promise about Fly's.

**This doc restates NOTHING from [`panels-program.md`](panels-program.md) §2 (P1–P17), which is
inherited whole**; §4 there is the library (`black_bloc/panels.py`).
[`requests-panel-design.md`](requests-panel-design.md) is the shipped template — read its
`## Deviations` foot (1–12) as the trap list before building.

## A. Measured today — two groups, seven subcommands

| Command | Who may run it | What it calls / what is INLINE in the cog |
|---|---|---|
| `/event logs` `:1290` | staff — `send_logs` carries its own `require_staff` (`actionlog.py`) | `send_logs(interaction, "events", …)`. Nothing inline |
| `/event create` `:1303` | anyone; refused when `events_mode == "off"` `:1307` | `get_timezone` → `EventModal` `:978`; the modal calls `Events.submit` `:1313` — ⚠️ **all inline**: `create_event` → `_make_review_channel` `:1388` → `set_review` → `log_action("event.created")` → `_post_review_card` `:1417` → reply → DM |
| `/event list` `:1446` | staff `:1448` | `events_by_status(OPEN_STATUSES)` `:326`, then ⚠️ **inline** line building `:1455–1467` incl. `NO_STAFF_WARNING` `:212` |
| `/event cancel <id>` `:1472` | **requester OR staff** `:1490` | ⚠️ **inline**: id parse `:1477`, guild check, ownership, `OPEN_STATUSES` check; then `cancel_event` `:744` + `rename_channel` `:1513` |
| `/event settings` `:1522` | staff `:1554` | ⚠️ **inline**: the 10-argument write loop `:1561–1579` and the status lines `:1583–1595`; `_health_lines` `:1608` |
| `/timezone set <tz>` `:1625` | anyone; autocomplete `_suggest_timezones` `:1618` over `suggest()` (`timezones.py:34`) | `is_known` → `set_timezone` (`timezones.py:109`); `TZ_SET` `:93` inline |
| `/timezone show` `:1646` | anyone | `stored_timezone` (`timezones.py:92`); `TZ_SHOW` / `TZ_SHOW_DEFAULT` `:97` inline |

**Approve / Deny are not subcommands and do not move.** They are a persistent
`DecisionButton` (`:941`, `DynamicItem`, `custom_id` `event:<id>:approve|deny`) on the review
card in the review channel, gated by `decision_context` `:906` (guard → `require_staff` → db →
row). That post belongs to the room, not the caller — P14, and it survives restarts. The panel
adds a SECOND way to make the same decision through the same `apply_decision` `:781`.

**States** (`events.py:24–40`) — `TRANSITIONS` is the whole state machine:

| From | May become |
|---|---|
| `pending` | `approved` · `denied` · `cancelled` |
| `approved` | `live` · `done` · `cancelled` |
| `live` | `done` · `cancelled` |
| `denied` · `done` · `cancelled` | nothing — `TERMINAL_STATUSES` `events.py:42` |

`live` and `done` are written **only by the loops** (`_go_live` `:1097`, `_finish` `:1160`,
`_missed` `:1132`), never by a person. `OPEN_STATUSES = (pending, approved, live)` `events.py:31`.

**The member-facing half** is `/event create`, `/event cancel` on your own event, and
`/timezone`. The zone is not only an events thing: raid trains read it (`raidtrain.py:1123`)
and so does the site's event editor (`api/tools/events.py:160`) — see fork **I2**.

## B. The decision — one `/event`, two panels

`/event` becomes a single `@app_commands.command` (the `event` Group `:1021` and the whole
`timezone` Group `:1022` go). One ephemeral message, embed + `Panel` subclass, re-rendered in
place; member and staff panels split on `store.is_staff` (P2).

**Member panel** — embed `Events`: one intro line; **"Your time zone is X, where it is now Y"**
(this IS `/timezone show`, `TZ_SHOW`/`TZ_SHOW_DEFAULT` unchanged); the caller's own proposals
only when `event_panel_own_list` is on (default off — mirrors the owner's requests deviation
12); `EVENTS_OFF` `:103` as a line when the mode is off, and then the Propose button is simply
not rendered (P9, never a dead button).

| Row | Control | Rendered when |
|---|---|---|
| 0 | `Propose an event` → `EventModal` `:978` unchanged | `events_mode != "off"` and db up |
| 0 | `My time zone` → one-line modal (below) | beside Propose only — same condition (I2: a zone is only needed where a member TYPES a time) |
| 0 | `Refresh` → re-render | always |
| 0 | `Open on the site` (link, `events.html` — `logkinds.py:95`) | an origin is configured |
| 1 | `Call one off…` select over the caller's own `OPEN_STATUSES` events → `Yes, call it off` / `Keep it` | the caller has ≥1 |

**Staff panel** — the member panel plus a counts line (`pending` / `approved` / `live`), and:

| Row | Control |
|---|---|
| 2 | `Pick an event…` select, guild `OPEN_STATUSES` newest-first, **capped at 25** with `panels.capped_placeholder` (`panels.py:55`); not rendered when nothing is open — the embed says so |
| 3 | `Settings` → the sub-panel in §C · `Logs` → `send_logs(interaction, "events")` as a NEW followup (P11) |

**Where `/timezone set` lands: a one-line MODAL, not a select.** Measured: 598 zones on this
machine against Discord's 25-option cap, so a select can only ever be a guessed shortlist; and
`app_commands.autocomplete` (`:1627`) exists only on a slash parameter — a button cannot have
it. The modal is prefilled with the caller's current zone, validated by `is_known`
(`timezones.py:26`) and stored by the same `set_timezone` (`timezones.py:109`), so **the value
round-trips exactly as today**; an unknown name answers `UNKNOWN_TZ` `:88` plus up to five
`suggest()` matches ("did you mean"), which is strictly more help than the slash command gives.

## C. The card, the modals, the sub-panel

Staff picks a row → the panel re-renders in place as `card_for(row)` `:432` (the same embed the
review channel and the DMs get — one card, never two shapes) with **only the moves valid from
its status**, computed from `TRANSITIONS` plus the guards the shared functions apply (P3):

| Row status | Buttons rendered |
|---|---|
| `pending` | `Approve` (success → `apply_decision(…, APPROVED)`) · `Deny` (danger, note modal) · `Call it off` (danger, confirm) |
| `approved` | `Call it off` |
| `live` | `Call it off` |
| `denied` | `Approve after all` (staff, success) while the review channel resolves — §I, settled |
| `done` · `cancelled` | none — the card says it is final (a `NO_MOVES_LEFT`-shaped sentence in the footer) |

Plus `Back` on every card, and a link button to `<#review_channel_id>` when it still resolves.
Styles: forward move `primary`/`success`, `Deny`/`Call it off` `danger`, the rest `secondary`.

⚠️ **No `Mark it done` button, though `TRANSITIONS` allows `approved`/`live` → `done`.** There
is no shared function that takes an ACTOR for `done`: `_finish` `:1160` and `_missed` `:1132`
are loop-only, and `apply_decision(…, DONE)` would DM the requester the *approved* sentence —
`_tell_requester` `:854` branches on `DENIED` and treats everything else as an approval. A Done
button needs a new shared path; it is not this build. The staff-final-say rule
(`CLAUDE.md`, owner 2026-09-03) is still met: `Call it off` renders in **every** non-terminal
state, so no state is one staff cannot leave, and the terminal three are terminal in the state
machine exactly as they are today.

**Modals** — all `AnswersErrors` + `discord.ui.Modal`, one shape (P12):

| Modal | Shape | Note |
|---|---|---|
| Propose | `EventModal` `:978` **unchanged**: Title, What is it?, Start, How long, Where | Exactly Discord's **5-input cap** — nothing to split, nothing to add |
| Deny | `panels.NoteModal(title="Why not?", label="One line the requester will be sent", max_length=400)` | Replaces `DenyModal` `:925` — same 400 clamp, same `apply_decision(…, DENIED, reason)` |
| My time zone | one line, prefilled, validated as in §B | new |
| Numbers (settings) | `events_channel_retention_days`, `events_max_late_minutes`, clamped by the same bounds `/event settings` uses `:1545–1548` | new |

⚠️ **Calling one off takes NO reason, and that is deliberate.** `cancel_event`'s `reason`
`:744` is a LOOKUP KEY (`CANCEL_WHY` `:174`, read at `:774`), not text a person is sent — the
cog passes `f"cancelled_by_{id}"` `:1504` and the site passes free text (`api/tools/events.py`
`event_cancel`) that falls through to `CANCEL_WHY_DEFAULT` either way. A free-text modal would
LOOK like it told the requester and would not. So: a `Yes, call it off` / `Keep it` confirm,
matching what `/event cancel` does today. Fork **I1** is whether to change that.

**Settings stays a sub-panel** (it does not point at the site): measured, the seven `events_*`
keys have labels on the general Settings page only (`site/public/assets/labels.js:60–66`) —
`site/public/events.html` has no settings section at all, so pointing there would be a worse
answer than the panel. The sub-panel's embed is today's status lines `:1583–1595` plus
`_health_lines` `:1608`, and its five rows are: 0 `mode` select (`EVENTS_MODES`), 1
`ChannelSelect(category)`, 2 `ChannelSelect(text)`, 3 `RoleSelect`, 4 buttons — `Scheduled
events: on/off` toggle, `Numbers…`, `Open on the site` (settings.html), `Back`. Each of the
three selects takes `min_values=0`, and an empty submit means **clear**, which is what
`clear_category` / `clear_announce_channel` / `clear_ping_role` `:1572–1579` do today. ⚠️ If
the client will not submit an empty select (unverified — see the header), the fallback is one
`Forget…` button opening a 3-option select of which key to clear; the write path is the same.

## D. Settings (P13 · checklist 33)

| Key | Type | Default | What it decides |
|---|---|---|---|
| `event_panel_minutes` | `int` | **10** | how long the panel stays live. Help text carries KI-20's warning verbatim in shape: 15+ loses the "gone quiet" footer because Discord's interaction token expires at 15 minutes |
| `event_panel_own_list` | `bool` | **False** | whether a MEMBER sees their own proposals written out. Staff always see theirs. Mirrors `request_panel_own_list` (requests deviation 12, the owner's "make the view request thing staff only") |

Registered in the three places `request_panel_minutes` is — `settings_store.py:876` `KEY_TYPES`,
`:892` `KEY_HELP`, `:1305` `default()` — so the Settings page and `/settings set-value` both
reach them with no new command. Nothing else here is a decision: the 25 cap is Discord's, the
button table is `TRANSITIONS`, and the seven existing `events_*` keys (`settings_store.py:181–187`)
are untouched. ⚠️ **There are FOURTEEN `events_*` keys today** (measured 2026-09-11): the seven here
plus `events_scheduled_name_template` (v100), `events_test_retention_minutes` (v107),
`events_where_link_in_description` (v106), `events_where_link_aliases` / `events_where_link_check` /
`events_where_link_check_seconds` (v108) — see the Where banner at the top.

## E. What goes away

| Thing | Where | Becomes |
|---|---|---|
| `event` Group | `cogs/community/events.py:1021` | `@app_commands.command(name="event")` |
| `timezone` Group + both children | `:1022`, `:1625`, `:1646` | deleted — the panel's `My time zone` button and the embed line |
| the five `/event` children | `:1290`, `:1303`, `:1446`, `:1472`, `:1522` | buttons / selects / the sub-panel |
| `assert len(top) == 44` | `tests/test_bot.py:204` | **43** — two top-level slots become one; this is the program's FIRST real `commands synced` drop (P1) |
| `"event": "events"` | `tests/test_bot.py:13` (`LOGS_GROUPS`) | removed — `/event` is no longer a Group with a `logs` child (`test_every_feature_group_has_a_logs_command` `:171`) |
| `"timezone"` | `tests/test_bot.py:74` (`MEMBER_COMMANDS`) | removed; `"event"` `:65` stays a member command |

Docs rewritten in the SAME commit (P15; `/help` reads the tree, `cogs/core.py`, so it follows
on its own): `docs/info/architecture.md:176` · `docs/info/feature-list.md:42` ·
`docs/access/sweeps.md:67` (row 32), `:82` (row 48's "your `/timezone`"), `:124–132` (the Phase
4 appendix script) · `docs/TODO.md:89` (F4's decision line gets a dated pointer) ·
`docs/info/phase4-design.md:95–98` (dated "superseded by the panel" line at the top, not a
rewrite) · `docs/info/panels-program.md:72` (the Events row → shipped) ·
`docs/info/code-notes.md` re-keyed at the merge (events anchors `:436 :449 :452 :457 :476 :3882`
and `:4464`'s "`/event create`"). ⚠️ **`docs/access/OWNER_GUIDE.md` names none of them** —
measured 2026-09-03, 80 lines, zero matches for "event" or "timezone"; only its sweeps count
(`:57`) moves when the rows in §H land.

## F. Extractions (P4) — the shared layer moves to `black_bloc/events.py`

⚠️ **Today the shared DB/move layer lives in the COG** (`cogs/community/events.py:219–922`:
`create_event`, `checked_fields`, `update_event`, `get_event`, `events_by_status`, `due_events`,
`set_*`, `cancel_event`, `apply_decision`, `rename_channel`, `post_to_announce`, …) and the
site imports it FROM the cog (`api/tools/events.py:9`), as do `chat_data.py:10` and
`knowledge.py:517` — the opposite of requests, where the layer is `black_bloc/requests.py`. The
new functions below all depend on that layer, so **the move is part of this build.** It is
mechanical: the Discord UI classes (`DenyModal`, `DecisionButton`, `EventModal`) and the cog
stay put, no name changes, so each importer is a one-line path edit and every existing
assertion stays as it is (wave 0 deviation 4: unchanged assertions are the proof).

New in `black_bloc/events.py` after the move — the panel and the site call the same one:

| Function | Why |
|---|---|
| `async submit_event(bot, guild, actor, fields: EventFields, *, via=VIA_DISCORD) -> tuple[str, Any]` | `Events.submit` `:1313`'s body: row → channel → `set_review` → log → card → the sentence. The cog keeps only the modal wiring |
| `async cancel_for(bot, guild, row, actor, *, via=VIA_DISCORD) -> tuple[str, Any]` | `cancel_event` **plus the `rename_channel` `:1513` the site never does** — one behaviour, both doors |
| `def may_cancel(store, row, actor) -> bool` | the requester-or-staff rule `:1490`, so the select and the button render only when it would succeed |
| `def wanted_event_id(given: Any) -> int | None` | the `#12` parse `:1477` (`NOT_AN_ID` stays the refusal) |
| `def event_line(row) -> str` / `def list_lines(rows, staff_roles) -> list[str]` | `/event list`'s inline block `:1455–1467`, `NO_STAFF_WARNING` included |
| `def counts_of(rows) -> dict[str, int]` | the staff panel's counts line |
| `def card_buttons(status, *, may_cancel_here=True) -> tuple[EventMove, ...]` | §C's table AS DATA, keyed by status, proved against `TRANSITIONS` by a parametrised test |
| `def settings_lines(store, guild, health) -> list[str]` / `async write_settings(store, guild_id, actor_id, changes) -> dict` | `:1583–1595` and the write loop `:1561–1579`, so the sub-panel and `/settings set-value` write identically |
| `def zone_line(name, *, chosen: bool) -> str` / `async set_zone(db, user_id, given) -> tuple[bool, str]` | `/timezone show` and `set` `:1628–1656`, verbatim strings |
| `async own_events(db, guild_id, user_id, statuses=OPEN_STATUSES) -> list` | NEW query — nothing today lists a member's own events |
| `def panel_minutes(store, guild_id)` / `def panel_shows_own_list(store, guild_id)` | one-liners over `panels.panel_minutes` (`panels.py:63`), exactly as `requests.py:473–478` |

⚠️ **`EventMove` is a LOCAL NamedTuple, not a move of `requests.MoveButton` (`requests.py:385`)
into `panels.py`.** One-fact-one-home says fold them; `panels-program.md` §5 says shared files
are append-only per feature so wave-1 merges stay textual — and three wave-1 builds editing
`panels.py` at once is exactly the conflict that rule exists to avoid. Fold the three copies
after wave 1 merges, as the conductor's job.

## G. Tests (mirror the package, P16)

| File | What it gains |
|---|---|
| `tests/cogs/community/test_events.py` (1604 today) | `/event` answers ephemerally with a panel; member vs staff; `Propose` hidden with `events_mode off` AND the embed says why; the time-zone modal round-trips and an unknown name refuses with suggestions; the `Call one off…` select appears only with an open own-event, and Yes/Keep; **the card renders EXACTLY the table's buttons, parametrised over `STATUSES`** (mirror `tests/cogs/community/test_requests.py:618–627`); Approve / Deny / Call it off each call their shared function with `via` untouched (mirror `:682–714`, `:780–800`); the select caps at 25 and its placeholder says so; `Logs` answers a NEW followup and `send_logs` keeps its own staff gate; timeout disables every item; `still_staff` refuses a demoted staffer mid-card; `db_ready` after a defer; the settings sub-panel writes through `write_settings` and an empty select clears |
| `tests/test_events.py` (263) | every new pure function in §F, `card_buttons` proved against `TRANSITIONS`, plus the moved layer's own tests (the ones in the cog file that test the module, not the cog, come across) |
| `tests/test_settings_store.py` (1193) | both new keys round-trip and appear in `KEY_TYPES` / `KEY_HELP` / `default()` |
| `tests/test_bot.py` | 44 → 43; `LOGS_GROUPS` loses `event`; `MEMBER_COMMANDS` loses `timezone` |
| `tests/api/tools/test_events.py` (273) · `tests/api/test_contract.py:20` · `tests/test_chat_data.py:19` · `tests/test_timezones.py` (148) | **import paths only** — unchanged assertions are the proof the move changed nothing |

## H. §J — prove before merge (P17), and the sweep rows

1. `python -m black_bloc` boots and `commands synced` reports **43**, not 44 (measure it, do
   not assert it — requests deviation 7 is the precedent).
2. The parametrised card test: every status renders its row and no other button.
3. `python -c "import black_bloc.events, black_bloc.cogs.community.events, black_bloc.api.tools.events, black_bloc.chat_data, black_bloc.knowledge"` — the move creates new import edges and this is what a boot would catch (wave 0 deviation 5).
4. `ruff`, full `pytest`, `node site/mock/check.mjs`, `node --input-type=module --check < site/public/assets/labels.js`.

**Sweep rows 73–79** (`docs/access/sweeps.md` holds 65; **66–72 are reserved by the two builds
in flight**, `feat/requests-check` and `feat/applications-no-role`, so events starts at 73 —
polls take 80+, birthdays 87+):

| # | Do this | Expect |
|---|---|---|
| 73 | `/event` as a member | one ephemeral panel: intro, your time zone line, Propose an event / My time zone / Refresh / Open on the site — and NO list of events (`event_panel_own_list` off) |
| 74 | `My time zone` → type `Phoenix`, then type `nonsense` | the zone saves and the panel says the local time; the bad one refuses in words with suggestions and saves nothing |
| 75 | `Propose an event` | the same 5-field modal as `/event create`; a `pending-…` channel and its Approve/Deny card as before |
| 76 | `/event` as staff | adds the counts line, `Pick an event…` (capped 25, "N of M" past that), `Settings`, `Logs` — Logs answers a NEW message and the panel stays |
| 77 | Pick a `pending` event → `Approve`; another → `Deny` with a reason | the card re-renders approved/denied, the requester is DMed, the channel renames — identical to pressing the buttons in the review channel |
| 78 | `Call it off` on the staff card, and `Call one off…` on the member panel | Yes/Keep confirm; the event is cancelled, the channel renamed, the announcement edited |
| 79 | `Settings` → flip mode, pick a category, submit an EMPTY channel select | the lines update; the empty select clears the key exactly as `clear_category` did |

## I. Genuine forks for the owner (two — everything else is settled by §2 or the template)

- ✅ **I1 — the cancel reason — SETTLED by the owner's standing rule, 2026-09-03 (reviewer, not
  a new owner call):** a staff move that affects a person carries a DM'd reason (`CLAUDE.md`,
  staff final say). `cancel_for` gains `note: str | None`; the staff `Call it off` opens
  `panels.NoteModal(title="Why is it off?", label="One line the requester will be sent",
  max_length=400, required=False)` — submit is yes, dismiss is keep; the member's own
  `Call one off…` keeps the plain Yes/Keep confirm (nobody else to tell). The DM appends the
  note when there is one; the lookup-key `reason` is untouched so the site's route still works.
  §C's "takes NO reason" paragraph is superseded by this line.
- ✅ **`denied` gains a staff exit — SETTLED by the same rule** (mirrors polls §I-1): the
  `denied` card renders `Approve after all` (staff, success) → `apply_decision(…, APPROVED)`,
  whose DM branch already says approved for anything but `DENIED` (`:854`);
  `TRANSITIONS[DENIED] = (APPROVED,)`, `TERMINAL_STATUSES` loses `denied`. It renders only
  while the review channel still resolves (the same check the card's link button makes) — with
  the channel gone the card says "denied — the room was cleaned up, propose it again" in words.
- ✅ **I2 — `/timezone` disappears entirely — DECIDED by the owner 2026-09-03 ("Remove it").**
  `commands synced` 44 → 43 as §D already says. Raid trains and the site editor keep reading
  the stored zone unchanged. Two refinements from the same exchange (the owner asked whether a
  member's time can be picked up automatically): Discord exposes a member's `locale`, never a
  time zone, so the stored zone stays the only way to READ a typed time; DISPLAY needs no zone
  at all because `stamp()` (`timezones.py:86`) already emits `<t:…:F> (<t:…:R>)`, which every
  reader's client renders in their own local time. So: (a) the **`My time zone` button is
  rendered only where a member types a time** — the member panel's Propose row (and any raid
  train panel later), not as a standalone feature; (b) **every confirmation that echoes a typed
  time shows both**: "7:00 PM your time (America/Phoenix) · `<t:…:F>`" — the member sees what
  the bot understood and what everyone else will see, in one line.

## Deviations

Written by the build agent, 2026-09-03. Everything not listed here was built as specified.

1. **`submit_event` takes a keyword-only `review_view` callable; §F's signature does not name
   one.** The design's signature is `submit_event(bot, guild, actor, fields, *, via=VIA_DISCORD)`,
   but the body it absorbs ends by posting the review card, and that card's Approve/Deny buttons
   are `DecisionButton` — a `DynamicItem` the design leaves in the cog. A pure module cannot
   import the cog, so the cog passes its own `review_view` in. Omitting it posts the card with no
   view rather than crashing, which is what a future web door would want. The alternative (a
   module-level hook the cog sets on import) hides the dependency; a named argument states it.
2. **`cancel_for` also takes `reason=`, and the site route now calls it instead of
   `cancel_event`.** §F says `cancel_for` is "`cancel_event` **plus the `rename_channel` the site
   never does** — one behaviour, both doors", so the route had to move onto it; but the route
   passes its own free-text `reason` (the lookup key), which the design's signature had no room
   for. `reason=None` still defaults to `f"cancelled_by_{actor_id}"`, so the Discord door is
   unchanged. ⚠️ **This is a real behaviour change for the website**: cancelling from
   `events.html` now renames the review channel, which it never did. That is the point of the
   function, but it is not "import paths only" as §G's last row claims for
   `tests/api/tools/test_events.py` — those tests still pass unchanged in assertion, because none
   of them asserted the absence of a rename.
3. **`card_buttons` takes a third keyword, `room_resolves`.** §F's signature is
   `card_buttons(status, *, may_cancel_here=True)`, but §I's settled `denied` exit says
   `Approve after all` "renders only while the review channel still resolves". That fact is not
   derivable from a status, so it is an argument. `card_footer_override(status, *,
   room_resolves=True)` carries the matching sentence.
4. **`Call it off` opens the note modal directly; there is no Yes/Keep confirm on the STAFF
   card.** §C says a confirm, §I1 (settled later, by the owner's standing staff-final-say rule)
   says a `NoteModal(required=False)` where "submit is yes, dismiss is keep". Those cannot both be
   true, so §I1 wins as the later decision — and it is strictly better, because the modal IS the
   confirm and carries the reason in the same click. The MEMBER's own `Call one off…` keeps the
   plain Yes / Keep confirm exactly as §C describes. Sweep row 78 was written to match what was
   built. `panels.NoteModal` gained `required: bool = True` (a generic addition to the library,
   with its own test in `tests/test_panels.py`), rather than a private copy.
5. **`event.created` now goes through `kind_via`.** §F's `submit_event` takes `via`, and checklist
   34 says a shared path that takes `via` builds its kind with `kind_via` and records
   `details["via"]`. Nothing writes `web.event.created` today (there is no create route), but the
   shape is now correct for the day there is one, and `test_logkinds.py` accepts it with no new
   enumeration because the kind is a string literal inside `kind_via`.
6. ⚠️ **BOTH the `min_values=0` selects AND §C's `Forget…` fallback were built, because the
   client half could not be checked.** The three selects take `min_values=0` and an empty submit
   clears the key, as §C asks; `Forget…` is also on the sub-panel's button row, opening a
   3-option select of which key to clear, writing through the same `write_settings`. Building
   only the unproven path would have shipped a settings panel that might have no way to clear a
   key at all. Row 4 of the sub-panel is therefore exactly Discord's 5-per-row cap: **Scheduled
   events · Numbers… · Forget… · Open on the site · Back** (four when no origin is configured).
7. **`Numbers…` validates in `black_bloc/events.py`, not at the settings validator.** §C says the
   modal is "clamped by the same bounds `/event settings` uses" — those were
   `app_commands.Range` annotations, which a modal has no equivalent of. `checked_numbers` reads
   the same `EVENTS_RETENTION_MIN_DAYS` / `EVENTS_RETENTION_MAX_DAYS` /
   `EVENTS_LATE_CEILING_MINUTES` constants and refuses out-of-range or non-numeric input in
   words, naming the range. Nothing is silently clamped.
8. **Every user-facing string that named a retired command was rewritten**, which §B's "`TZ_SHOW`
   / `TZ_SHOW_DEFAULT` unchanged" did not allow for. A sentence that tells a member to run
   `/timezone set` after `/timezone` is deleted is worse than a stale doc — it is a dead end
   inside the product (P9). Rewritten: `TZ_SHOW`, `TZ_SHOW_DEFAULT`, `TZ_SET`, `BAD_START`,
   `START_IN_THE_PAST`, `DST_GAP`, `MODAL_ZONE_HINT`, `EVENTS_OFF`, `NO_CATEGORY`,
   `NOT_A_CATEGORY`, `NO_SUCH_EVENT`, `NOT_AN_ID`, `NO_STAFF_WARNING`, `DM_MISSED`, every
   `CANCEL_WHY` entry, and `approve_extra`'s "Scheduled events are turned off" line. Outside the
   feature, `black_bloc/personas.py` and `black_bloc/chat.py` said `/event create` and
   `/timezone set` to members' faces; both now say `/event` and the button.
9. **`UNKNOWN_TZ` no longer tells people to "start typing a city and pick a suggestion"** —
   there is no autocomplete behind a button. It names the `Region/City` shape, and `set_zone`
   appends up to five real `suggest()` matches as "Did you mean …", which §B asked for. Typing
   `Phoenix` now gets `America/Phoenix` offered back; the old slash command would simply have had
   it in a dropdown.
10. **The staff panel writes the OPEN list out, not just a counts line.** §B's staff table lists
    only the counts line plus the select. Built that way, `list_lines` and `NO_STAFF_WARNING`
    (both named in §F as extractions of `/event list`) would have had no caller, and the "no staff
    roles resolve" warning — the loudest thing `/event list` said — would have been lost with the
    subcommand. So the staff half of the embed is `counts_line` + `list_lines(open[:10],
    staff_roles)`, which is `/event list` verbatim, and `event_panel_own_list` is now purely a
    MEMBER key (staff see every open event including their own, which is a superset of "staff
    always see theirs").
11. **`decision_id`, `review_view`, `decide`, `close_card` and `decision_context` stayed in the
    cog** — §F's move list is "the shared DB/move layer", and these five are interaction- or
    `DynamicItem`-shaped. `_tell_requester` / `_approve_extra` / `_make_review_channel` /
    `_post_review_card` moved and lost their leading underscore (`tell_requester`,
    `approve_extra`, `make_review_channel`, `post_review_card`) — they are module API now, and
    `make_review_channel` returns `None` instead of answering an interaction, so the sentence is
    the caller's to say.
12. ⚠️ **`TERMINAL_STATUSES` losing `denied` changes when a lock is dropped**, which §I's settled
    `denied` exit did not mention. `apply_decision` drops an event's `asyncio.Lock` once the
    status is terminal; `denied` is no longer terminal, so a denied event keeps its lock until it
    is cancelled (or approved after all and then finished). That is correct — a row that can still
    move must still be raceable-safely — but it means a denied-and-forgotten event holds one
    `asyncio.Lock` object for the life of the process. `tests/cogs/community/test_events.py::
    test_a_settled_event_stops_being_kept_a_lock` now pins exactly this: denied keeps it,
    cancelled drops it.
13. **`python -m black_bloc` (invariant P17, §H item 1) was NOT run** — no bot token in this
    environment, same as wave 0 deviation 5. `commands synced` was **measured** instead through
    `tests/test_bot.py`, which builds the real tree by loading every cog and counts
    `bot.tree.get_commands()`: **43 on this branch**, 44 at the base. The import check (§H item 3)
    was run and passes; it is what a boot would have caught, and this build creates real new
    import edges (`black_bloc/events.py` → `actionlog`, `command_errors`, `panels`,
    `settings_store`). `node site/mock/check.mjs` and the `labels.js` parse (§H item 4) were NOT
    run: the site is untouched by this build — no `site/` file changed, and the seven `events_*`
    keys the general Settings page labels are unchanged.
14. ⚠️ **`docs/TODO.md` was NOT touched, though §E asks for it.** The common build brief says the
    conductor lands `TODO.md`, `DONE.md` and `deploys.log`, and that instruction wins over §E's
    "F4's decision line gets a dated pointer". **The pointer is still owed**: F4's row
    (`docs/TODO.md:94`) still describes `/event create` and `/timezone set` as the way in, and
    needs a dated line saying the slash surface changed on 2026-09-03 and pointing here.
    ⚠️ **Still owed on 2026-09-11** — re-checked: F4's row is now `docs/TODO.md:92` and still
    reads *"`/event create` **modal**"* and *"entered once via `/timezone set`"*. Every
    OTHER doc §E lists was rewritten in the docs commit, plus three §E did not name —
    `phase11-design.md:57` (chat's `time_for_me` pointed at `/timezone set`),
    `phase18-design.md:64` (raid trains "type the start in their `/timezone` like `/event
    create`") and `polls-research.md:416`.
15. **`NOT_YOURS` was DELETED, not moved.** `/event cancel` needed a sentence for "that one is not yours"; the panel cannot produce that state — the member's `Call one off…` lists only their own rows and the staff card's button is gated by `may_cancel` — so under P9 the refusal has no caller. ⚠️ `NO_ANNOUNCE_CHANNEL` in the same file is ALSO dead, but it was dead before this build and is left alone (reported, not fixed).
16. **§H's sweep rows were rewritten where the build diverged.** Row 74 now says the refusal
    suggests a zone (deviation 9), row 78 says the staff note replaces the confirm (deviation 4),
    and row 79 names `Forget…` beside the empty select (deviation 6). Rows 73, 75, 76 and 77 are
    as designed.

### What §H could and could not prove

| # | §H item | Proven? |
|---|---|---|
| 1 | boot reports `commands synced` **43** | **Measured, not booted** — `tests/test_bot.py` counts the real tree at 43 (44 at base). A live boot is deviation 13 |
| 2 | the parametrised card test | **Proven** — `test_the_card_renders_exactly_the_buttons_the_table_says` over all six statuses, plus `test_the_card_table_only_ever_offers_a_move_the_state_machine_allows` checking the table against `TRANSITIONS` itself |
| 3 | the five-module import check | **Proven** — run, passes |
| 4 | ruff, full pytest, `check.mjs`, `labels.js` | **Partly** — ruff clean and 3502 tests pass; the two site checks were skipped because no site file changed (deviation 13) |
| — | the empty `ChannelSelect`/`RoleSelect` submit | **NOT proven, and cannot be here** — needs a Discord client. The fallback is built (deviation 6) |
| — | anything a person sees | **NOT proven** — no panel has been opened in Discord |

### One flaky test, not caused by this build

`tests/api/test_settings_api.py::test_writes_are_rate_limited_per_session` fails under
`pytest -n auto` on this machine and passes under `-n 4` (**3502 passed, 0 failed**) and on its
own. The limiter is 60 writes in a **60-second wall-clock window** (`api/writes.py:23–24`), so 60
sequential `PUT`s straddle the window when the workers are contended. ⚠️ **Measured on the base
commit too, in a throwaway worktree of `d3da02c`: `-n auto` gives `1 failed, 3441 passed` — the
same test, the same way.** It is pre-existing and load-sensitive, not a regression; nothing under
`black_bloc/api/` changed in this build except `api/tools/events.py`, which that test does not
touch. Reported, not fixed. The honest test counts: **base 3442 (3441 + this flake), this branch
3502 (3501 + this flake)** — +60 tests, none lost.
