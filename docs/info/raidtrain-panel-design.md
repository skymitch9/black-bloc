# Raid trains — `/raidtrain` is ONE command that opens a panel (wave 3)

> **Audience:** the build agent and the reviewer (Claude sessions), and the owner for §I.
> **Status:** TRACKED · ✅ **SHIPPED in v76** (`2dd2689`, 2026-09-04 16:56; built on
> `worktree-agent-aba5d44f8e27a8e28` for 473k against the 380–450k estimate, merged clean, 4402 → 4465
> tests, `commands synced` 38 → 37 measured at boot). The `## Deviations` foot (14 items) is the
> BUILD agent's; landing entry in `DONE.md` 2026-09-04.
> **Last verified: 2026-09-04** — every `path:line` below was READ against `main` at `4336a66`
> (the tree's newest commit; **code-identical to `bf3e447`** — the only commit between them is the
> docs commit that dispatched these wave-3 designs, `git status` clean). Files read in full:
> `black_bloc/cogs/content/raidtrain.py` (**1535 lines**), `black_bloc/raidtrain.py` (**404**),
> `black_bloc/api/tools/raidtrain.py` (**394**), `black_bloc/panels.py`, `black_bloc/settings_store.py`,
> `black_bloc/logkinds.py`, `black_bloc/command_visibility.py`, `black_bloc/personas.py`,
> `black_bloc/cogs/community/tempvoice.py` (the `VoicePanel` half), `tests/test_bot.py`,
> `tests/api/conftest.py`, `site/public/assets/labels.js`, `site/public/assets/page-events.js`,
> `site/mock/server.mjs`, `site/mock/contract.json`, `docs/access/sweeps.md`,
> `docs/access/OWNER_GUIDE.md`, `docs/info/feature-list.md`, `docs/info/phase18-design.md`,
> `docs/info/raid-train-capture.md`, `docs/info/code-notes.md`.
> **Counted, not estimated:** **15 leaf subcommands over 2 top-level slots**;
> `tests/test_bot.py:190` asserts **`len(top) == 38`** (the number `commands synced` printed at the
> v73 boot); `docs/access/sweeps.md` ends at row **143**; `docs/access/OWNER_GUIDE.md` has **zero**
> matches for `raidtrain` / "raid train"; `tests/cogs/content/test_raidtrain.py` **59 tests**,
> `tests/test_raidtrain.py` **21**, `tests/api/tools/test_raidtrain.py` **24**;
> `command_visibility.HIDDEN_WHEN_OFF` (`:16–19`) has **no** raid-train entry;
> `RAIDTRAIN_MODES = ("off", "shadow", "on")` (`settings_store.py:125`) — **three** modes, unlike
> temp voice's two.
> ⚠️ **NOT verified: anything was RUN.** No boot, no `pytest`, no `ruff`, no `check.mjs`, nothing
> against live Discord, nothing against a live raid train (none has ever run — `raidtrain_mode` is
> still `off`). Whether a client submits an EMPTY `RoleSelect`/`ChannelSelect` at `min_values=0` is
> the unproven edge [`events-panel-design.md`](events-panel-design.md) and
> [`pings-panel-design.md`](pings-panel-design.md) both flag; **§C's Setup sub-panel is designed so
> the answer does not matter** (clearing is its own control, never an empty submit).
> ⚠️ Three sibling wave-3 designs are being written in parallel, so **every `path:line` and every
> count here will drift before this is built — trust the anchor text, not the number, and
> re-measure at build time.**
>
> **Inherits every invariant in [`panels-program.md`](panels-program.md) §2 (P1–P17) and its §4
> library — none restated here.** Template: [`requests-panel-design.md`](requests-panel-design.md);
> the shape to copy is [`voice-panel-design.md`](voice-panel-design.md) (wave 2's largest) and
> [`applications-panel-design.md`](applications-panel-design.md) (the one that also had to fix the
> web's double logging). Feature behaviour is [`phase18-design.md`](phase18-design.md); the ask it
> came from is [`raid-train-capture.md`](raid-train-capture.md).

## A. Measured today — two groups, fifteen subcommands

`raidtrain` is an `app_commands.Group` (`:389`, **member-visible**, no `default_permissions`);
`raidtrains` is an `app_commands.Group` (`:392`, `default_permissions=STAFF_ONLY`).
**12 + 3 = fifteen leaf subcommands over two top-level slots.**

| Subcommand | Line | Gate | Calls · what is INLINE in the cog |
|---|---|---|---|
| `/raidtrain list` | `:946` | `_ready` `:858` | ⚠️ **all inline** `:950–967` — `list_trains` `:198` + `slots_for` `:211`, capped at `LIST_LIMIT` `:67` (20) |
| `/raidtrain status <train>` | `:969` | `_ready` | `render_lineup` (`raidtrain.py:210`) — shared with the site's `lineup` field |
| `/raidtrain claim <train> [slot]` | `:985` | `_ready`; `NEEDS_LINK` before the defer `:997` | `_claim` `:1007` — ⚠️ **inline**, writes through `take_slot` `:228` |
| `/raidtrain release <train> [slot]` | `:1054` | `_ready` | `_release` `:1072` — ⚠️ **inline**, `empty_slot` `:239` |
| `/raidtrain mine` | `:1092` | `_ready` | ⚠️ **inline** `:1096–1113` over `slots_of_member` `:218`, capped at `MINE_LIMIT` `:68` (10) |
| `/raidtrain create` | `:1117` | `_ready` + `_organizer` `:888` | `TrainModal` `:348` → `submit_train` `:1127` → `create_train` `:146` + `publish_lineup` `:690` |
| `/raidtrain assign <train> <slot> <member>` | `:1218` | `_organizer`; `MEMBER_NOT_LINKED` `:121` | `_assign` `:1250` — ⚠️ **inline** |
| `/raidtrain unassign <train> <slot>` | `:1271` | `_organizer` | ⚠️ **all inline** `:1284–1305` |
| `/raidtrain swap <train> <first> <second>` | `:1307` | `_organizer` | ⚠️ **all inline** `:1324–1344`, `swap_holders` `:250` |
| `/raidtrain lock` · `unlock` | `:1346` `:1352` | `_organizer` | `_move` `:1358` (one body, two doors) — `may_move` / `move_refusal` (`raidtrain.py:122`, `:136`) |
| `/raidtrain cancel <train> <reason>` | `:1388` | `_organizer` | **`cancel_train` `:1414` — the one function the website already calls** |
| `/raidtrains mode <off\|shadow\|on>` | `:1449` | `require_staff` `:1457` | ⚠️ **inline** `:1459–1472`: `store.set` + reply + `log_action("raidtrain.mode")`. **No `kind_via`** |
| `/raidtrains setup [channel] [organizer_role] [ping_role]` | `:1474` | `require_staff` `:1487` | ⚠️ **inline** `:1489–1518`: up to three `store.set`s + one `raidtrain.setup` row. **No `kind_via`** |
| `/raidtrains logs` | `:1520` | `send_logs` carries its own `require_staff` | `send_logs(interaction, "raidtrain", count, important_only)` |

**The gates, measured.** `_ready` `:858` = guild → `db.is_connected` → **mode ≠ `off`**; it refuses
every one of the twelve `/raidtrain` subcommands while the mode is off, and the `/raidtrains` group
deliberately keeps working because `mode` is how you turn it on (`code-notes.md` §
`cogs/content/raidtrain.py:858`). `is_organizer` `:877` = **the configured
`raidtrain_organizer_role_id` role OR `store.is_staff`** — so **staff ⊆ organizer ⊆ member**, three
audiences, not two. `_organizer` `:888` is its answering half and `_organizer_words` `:873` is the
refusal's wording. `_train_or_refusal` `:898` turns a typed id into a row or `NO_SUCH_TRAIN` `:79`.

**Shared with the website** (`api/tools/raidtrain.py:9–20` imports ten names from the cog, plus
`set_status` inline at `:369`, plus the cog methods `publish_lineup`, `_refresh_lineup` and
`cancel_train`): `MEMBER_NOT_LINKED`, `counts` `:307`, `create_train` `:146`, `empty_slot` `:239`,
`get_train` `:191`, `list_trains` `:198`, `slots_for` `:211`, `swap_holders` `:250`,
`take_slot` `:228`, `twitch_login_of` `:299`.

**Persistent surfaces — NOT moving** (P14, program §7): the **lineup post**, `render_lineup`'s text
message posted by `publish_lineup` `:690` and **edited in place** by `_refresh_lineup` `:817`; the
**thread** under it (`_open_thread` `:720`); the Discord **scheduled event** (`_maybe_scheduled_event`
`:746`). ⚠️ **Measured, and it matters:** the lineup post carries **no components at all** — it is
not a `DynamicItem` view like temp voice's control post or the role-menu panels. There is nothing to
rebuild and nothing to leave alone; giving it a button would be a *new* persistent view, which is a
separate build (fork **F-R1**).

**Settings keys today — thirteen, no constants** (`settings_store.py`): `raidtrain_mode` (`:255`,
choices `:298`, default `"off"` `:1569`), `_organizer_role_id` `:256`, `_channel_id` `:257`,
`_ping_role_id` `:258`, `_slot_minutes` `:259`, `_reminder_minutes` `:260`, `_poll_minutes` `:261`,
`_require_link` `:262`, `_thread` `:263`, `_live_posts` `:264`, `_max_slots_per_member` `:265`,
`_scheduled_event` `:266`, and `raidtrain_log_level` through the `_log_level` family
(`default()` `:1609`). Help text `:731–774`; bounds `:318–321` / `:330–332`; module constants
`:125–136`.

**Site, measured.** Seven routes under `/api/raidtrains`, **every one behind
`staff_dependency`** (`api/tools/raidtrain.py:132–136`): `GET /status` `:144`, `GET ""` `:167`,
`GET /{train_id}` `:177`, `POST ""` `:188`, `POST /{train_id}/slots/{position}` `:253`,
`POST /{train_id}/swap` `:310`, `POST /{train_id}/status` `:347`. The surface is a **section on the
Events page**, not a page of its own (`page-events.js:280`, `logkinds.py:108`
`"raidtrain": "events.html"`). Five `note()` calls write `web.raidtrain.*` heads by hand:
`:235` create, `:275` unassign, `:294` assign, `:333` swap, `:373` lock/unlock.

**`commands synced` today: 38** (`tests/test_bot.py:190`, the figure the v73 boot printed). Two
top-level slots become one, so this design takes it to **37 — a delta of exactly one.** ⚠️ **State
the delta, never the number:** three sibling wave-3 panels are being designed in parallel (role
menus also folds two groups into one; chat and automod are one group each and move nothing), so the
absolute figure will differ by build time. The build **re-measures** through
`tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits` and edits `:190` to what it
reads (requests deviation 7).

## B. The decision — one `/raidtrain`, three audiences from one command

**`/raidtrain` becomes a single `app_commands.command`; both `Group`s go and `/raidtrains`
disappears.** It keeps `/raidtrain`'s posture — **no `default_permissions`, member-visible** — so
`"raidtrains"` leaves `STAFF_COMMANDS` (`tests/test_bot.py:38`) and `"raidtrain"` stays in
`MEMBER_COMMANDS` (`:60`). The staff half is gated at runtime by `panels.still_staff`, never by the
UX lock; the organizer half by `is_organizer` `:877`, re-asked on every move (§F `still_organizer`).

`/raidtrain` **does not vanish when the mode is off** — there is no `HIDDEN_WHEN_OFF` entry to
remove (measured), and the owner has answered this shape twice (applications I-A2 "Visible",
2026-09-03 13:47; memory I-M1 "open it", 16:12).

⚠️ **The mode gate moves from the command to the panel.** Today `_ready` `:858` refuses every
`/raidtrain` subcommand while the mode is `off`, and the *staff* commands live on a different group
that keeps working. With one command they cannot be two doors, so: **the panel always opens.** With
the mode off a member gets one sentence and `Refresh`; **staff get the full staff row including the
mode select**, which is the only way a Lead turns raid trains on once `/raidtrains mode` is gone.
This is the youtube-panel precedent (the mode select sits on the ROOT, not inside Setup, because
turning the feature on is why a Lead opens it) and it is required by the staff-final-say rule.

**Root panel** — `build_panel(bot, guild, actor)`, one ephemeral embed + a `Panel` subclass, split
on `is_organizer(actor)` and `store.is_staff(actor)` (P2).

**The root states, crossed with the mode** (three modes, not two):

| # | Where the caller is | mode `on` / `shadow` | mode `off` |
|---|---|---|---|
| R0 | DM, or the database is down | `GUILD_ONLY` / `DB_UNAVAILABLE` through `panels.db_up`, no panel | same |
| R1 | member, no upcoming train | `NOTHING_UPCOMING` `:83` reworded; `My slots` only if they hold one on a finished train; `Refresh` | + one line: raid trains are off, so nothing new can be started |
| R2 | organizer, no upcoming train | + **`Start a raid train`** | + the same off line; `Start a raid train` is **not rendered** (`_ready` would have refused, so P3 forbids the button) |
| R3 | member, trains exist | today's `list_command` lines `:954–964` as the embed + **`A train…`** select → the lineup card; `My slots` when they hold any; `Refresh` | the list still renders (reading is not a write), the claim controls on every card do not |
| R4 | organizer, trains exist | R3 + `Start a raid train` | R3 + the off line |
| R5 | staff, crossed with any of R1–R4 | + the **staff row**, the **sweep block** in the embed, and the **`Mode…`** select | + the same, and the mode select is how it gets turned on |

⚠️ **`shadow` is not `off`.** In `shadow` every command works, every row is written, and only the
DM and the channel post are withheld (`_remind` `:548`, `_say_the_train_moved` `:602`,
`publish_lineup` `:701`). So the panel renders **identically** in `on` and `shadow`; the only
difference is a line in the embed and the `CLAIMED_SHADOW` `:109` tail the shared function already
appends. Do **not** invent a third rendering.

P3 in one line: **no state renders a control whose shared function would refuse it.** `Take an
hour…` only when the train is `open` AND an open slot exists AND `caps_ok` (`raidtrain.py:147`)
passes AND the link condition is met; `Lock` **or** `Unlock`, never both, and neither on a `live`
train (`TRANSITIONS` `raidtrain.py:31` allows `live → done` only); `Take somebody off…` only when
some slot is taken; `Call it off…` only while `may_move(status, "cancelled")`.

## C. The cards, the sub-panels, the modals

Each is a **re-render in place**: `retire(previous)` first (P6), `defer()` then
`edit_original_response` (P5), `db_ready` on every click (requests deviation 6), `still_staff` before
every staff move (P8) and `still_organizer` before every organizer move (§F). The re-render helpers
copy `cogs/community/tempvoice.py:1588 render` / `:1624 ready_to_move` / `:1719 act_on_own`
verbatim in shape — **every move re-reads the train row and the slots before acting**, because a
train can be locked, filled or cancelled while a card is open.

### The root

| Row | Control | Rendered when | Shared function |
|---|---|---|---|
| 0 | `Select` **`A train…`** over `list_trains(scope="upcoming")` `:198`, ≤25 with `panels.capped_placeholder`, labels via `panels.option_label` | at least one upcoming train | — (opens the card) |
| 1 | `Select` **`Mode…`** — `off` / `shadow` / `on`, the current one marked default | staff | `set_mode` (§F) |
| 2 | `Start a raid train` → `TrainModal` `:348` | organizer **and** the mode is not `off` | `create_and_publish` (§F) |
| 2 | `My slots…` → sub-panel | `slots_of_member` `:218` returns a row | — |
| 2 | `Setup…` → sub-panel | staff | `save_setup` (§F) |
| 2 | `Logs` → a NEW ephemeral followup (P11) | staff | `send_logs(interaction, "raidtrain")` — keeps its own `require_staff` |
| 2 | `Refresh` | always | — |
| 3 | `Open on the site` (link) | staff **and** an origin is configured | `panels.site_page_url(origin, "raidtrain")` → `events.html` |

⚠️ **The site link is staff-only.** Every `/api/raidtrains/*` route is behind `staff_dependency`
(`:135`), so offering it to a member is P9's dead control — the same call the voice and pings panels
made.

**The staff block in the embed** is `/api/raidtrains/status`'s own shape (`:144–165`), written out
always rather than hidden behind a `Status` button (events deviation 10: a button that hides the
loudest warning loses it): mode · lineup channel (or the `events_announce_channel_id` it borrows,
`_channel_id` `:617`) · sweep running · `last_ok_at` / `last_error` / `failures`
(`loop_health` `:396`) · `every_minutes` · trains / upcoming / slots / claimed from `counts` `:307`.
`NO_CHANNEL_YET` `:126`'s warning becomes a line here rather than a tail on one reply.

### The lineup card

Embed = `render_lineup(train, slots)` (`raidtrain.py:210`) through `panels.clamped` — **the same
function the post, `/raidtrain status` and the dashboard's `lineup` field all use**, so the card and
the room can never disagree. ⚠️ `render_lineup`'s tail line names `/raidtrain claim`
(`raidtrain.py:234`) and is rewritten in this build (§E) — it is read by the whole room, not just
the panel.

| Row | Control | Rendered when | Shared function |
|---|---|---|---|
| 0 | `Select` **`Take an hour…`** over the OPEN slots (`open_positions` `raidtrain.py:155`), each option its `#N` and its `<t:…:t>` window | status `open` · an open slot exists · `caps_ok(slots, actor, raidtrain_max_slots_per_member)` · (`raidtrain_require_link` off **or** `twitch_login_of` `:299` returns a login) | `claim_slot` (§F) |
| 1 | `Select` **`Take somebody off…`** over the TAKEN slots, each option naming the holder | organizer · at least one taken slot | `unassign_slot` (§F) |
| 2 | `Give back slot #N` | the actor holds **exactly one** slot here (`slots_held` `raidtrain.py:142`) · status `open` | `release_slot` (§F) |
| 2 | `Give an hour back…` → sub-panel | the actor holds **more than one** · status `open` | `release_slot` |
| 2 | `Put somebody in…` → sub-panel | organizer · status `open` or `locked` | `assign_slot` (§F) |
| 2 | `Change two slots round…` → sub-panel | organizer · ≥2 slots · status `open` or `locked` | `swap_slots` (§F) |
| 2 | `Lock the lineup` when `open`, `Open it for sign-ups` when `locked` — **one button** | organizer · `may_move(status, target)` | `move_train` (§F) |
| 3 | `Call it off…` (danger) → `panels.NoteModal` | organizer · `may_move(status, "cancelled")` — i.e. `open` or `locked` only | `cancel_train` `:1414` **with `via`** (§F) |
| 3 | `Back` · `Refresh` | always | — |

⚠️ **Row 2 carries at most five controls and they are mutually exclusive by state**: a member holding
one slot on an open train sees `Give back slot #3`; the organizer of a locked train sees `Put
somebody in…`, `Change two slots round…`, `Open it for sign-ups`. A staff organizer holding a slot
on an open train is the worst case — `Give back #N` · `Put somebody in…` · `Change two slots
round…` · `Lock the lineup` = **four**, and `Give an hour back…` never coexists with `Give back
#N`. The parametrised test asserts the ceiling.

⚠️ **`Take an hour…` is the ONLY claim door — there is deliberately no `Take the next open hour`
button beside it.** Today `/raidtrain claim` takes an optional slot and falls back to
`next_open_position` `raidtrain.py:163`; two controls for one move is what P3 exists to stop. The
fallback keeps its home: `next_open_position` names the next free hour in the card's own line, so
nothing is deleted. **This is fork F-R3** — the owner may want the one-click button back.

⚠️ **Nothing on the card marks a train `live` or `done`.** `TRANSITIONS` allows `live → done`, but
`_run_clock` `:493` is the only thing that walks it, and the auto-lock at start is fixed by design
(D11). A button with no shared function behind it is exactly what P4 forbids.

⚠️ **A member whose Twitch is not linked gets a LINE, never a greyed button.** `NEEDS_LINK`
(`raidtrain.py:54`) already points at `/golive` ▸ **Link my Twitch channel** (the golive panel
rewrote it — measured, correct as it stands) and it becomes a field on the card embed. P9.

### The sub-panels

**`Put somebody in…`** (organizer) — row 0 `Select` over **all** slots (assigning over a taken seat
is deliberate; `_assign` `:1257` empties first); row 1 `UserSelect` "Who takes it?"; row 2 `Put them
in` · `Back`. The confirm re-reads both picks and calls `assign_slot`. `MEMBER_NOT_LINKED` `:121`
stays its refusal — it depends on a value chosen *after* the control renders, so it is a worded
answer, not a dead button.

**`Change two slots round…`** (organizer) — row 0 `Select` **`First…`**, row 1 `Select`
**`Second…`** re-rendered **without the first pick**, row 2 `Swap them` · `Back`. `SAME_SLOT` `:117`
survives as the confirm's belt-and-braces answer (the confirm re-reads; the selects can be re-picked
between renders).

**`Give an hour back…`** (member, >1 slot held) — row 0 `Select` over their own held slots, row 1
`Back`. One pick, one move, straight back to the card.

**`My slots…`** — today's `mine_command` lines `:1101–1110` as the embed (`MINE_LIMIT` `:68` = 10),
row 0 a `Select` **`A train…`** over the trains they hold a slot on → that train's card, row 1
`Back`. It is cross-train, so it cannot live on a card. `NOTHING_HELD` `:87` becomes the empty
state — reworded, it names `/raidtrain list`.

**`Setup…`** (staff) — **five rows, the Discord ceiling, so nothing else may ever join it**:

| Row | Control | Writes |
|---|---|---|
| 0 | `ChannelSelect` "Where the lineup post lives" | `raidtrain_channel_id` |
| 1 | `RoleSelect` "Who may build a lineup, besides staff" | `raidtrain_organizer_role_id` |
| 2 | `RoleSelect` "Who is pinged in front of a lineup" | `raidtrain_ping_role_id` |
| 3 | `Select` **`Clear…`** — one option per key that is currently SET | that one key → blank |
| 4 | `Save` · `Back` | `save_setup` (§F): one validated dict, one `raidtrain.setup` row |

⚠️ **Clearing is its own control on purpose.** An empty `min_values=0` submit cannot be told apart
from "did not touch this one", and whether a client will even send one is still unproven
(pings deviation 5 built both paths and row 132 of `sweeps.md` says so out loud). A `Clear…` select
that renders only when something is set is unambiguous, P3-clean, and **it is what the
staff-final-say rule needs**: today `/raidtrains setup` can only ever *set* these three keys — the
organizer role can be granted from Discord and taken away only on the website. `SETUP_NOTHING`
`:130` becomes unreachable and is deleted.

### The modals

Both `AnswersErrors` + `discord.ui.Modal`, one shape (P12).

- **`TrainModal` `:348` is REUSED, five fields unchanged** (title / description / start / minutes
  per slot / how many slots — already Discord's maximum of five), and keeps `submit_train` `:1127`
  as its `on_submit` body. The only change is that it takes the panel's re-render callback and
  answers through it, so a new train lands on the root with its card already reachable.
  `MODAL_ZONE_HINT` `:69` and `get_timezone` stay exactly as they are.
- **`panels.NoteModal`** for `Call it off…` — one paragraph field labelled with what the note is for
  and who is sent it ("what the people who signed up are told"), `max_length` = the reason's real
  ceiling. ⚠️ **Typing the reason IS the confirmation** — no second Yes/No step, and a blank reason
  is refused in the modal, matching the website's `CANCEL_NEEDS_REASON`
  (`api/tools/raidtrain.py:73`).

⚠️ **Two constants named `DESCRIPTION_LIMIT` are in play and they disagree** — a checklist-15 finding
this build should fix or record: the cog imports `events.DESCRIPTION_LIMIT` = **1000**
(`events.py:43`, cog `:21`) for the modal field and for `clamp(reason, …)` in `cancel_train`
`:1416`, while `raidtrain.DESCRIPTION_LIMIT` = **500** (`raidtrain.py:14`) is what `render_lineup`
`:224` and `cancelled_text` `:270` actually clamp to. A 900-character description is accepted, then
silently halved on the post. **Recommended:** the modal and the note both bound to the raid-train
module's 500, so what a person types is what the room reads.

## D. Settings (P13 · checklist 33)

| Key | Type | Default | Status |
|---|---|---|---|
| `raidtrain_panel_minutes` | `int` | **10** | **NEW.** How long the panel stays live. Help text carries KI-20's warning in the same shape as the six that shipped (15+ loses the "gone quiet" footer, because Discord's interaction token expires at 15 minutes); the value is deliberately NOT clamped |

Registered **in its own appended block** so parallel wave-3 branches merge textually, exactly where
`voice_panel_minutes` sits: `settings_store.py:1066–1078` (`KEY_TYPES.update` + `KEY_HELP.update`)
and the `default()` branch beside `:1607`.

**Both site homes, which the four wave-1 keys are still missing** (recorded review finding,
`TODO.md` 🔧):

| File | Row to add |
|---|---|
| `site/public/assets/labels.js` | `raidtrain_panel_minutes: 'How long the /raidtrain panel stays live',` beside `voice_panel_minutes` (`:51`) |
| `site/mock/server.mjs` | `['raidtrain_panel_minutes', 'int', 10, 10, "minutes the /raidtrain panel stays live …", null, 1440],` beside `voice_panel_minutes` (`:420`) |

**Optional rider, cheap, flagged not assumed:** the four earlier `*_panel_minutes` keys
(`request_`, `poll_`, `birthday_`, `event_`) still have no `labels.js` / `server.mjs` row. Four lines
each; fold them in only if the build has headroom, and say so in the deviations.

**Existing keys this panel READS, all untouched:** the thirteen in §A. **Nothing else here is a
decision.** The 25-option cap and the five-row cap are Discord's; the button table is the state
machine in §B; and the two behaviours a reader might mistake for decisions — staff reaching Setup
and Mode while the feature is off, and staff being able to undo any organizer's stored decision —
are **settled by the standing staff-final-say rule**, not chosen here, so neither becomes a key.

⚠️ **`SLOT_COUNT_MAX = 24` (`raidtrain.py:18`) is below Discord's 25**, so **a slot select can never
cap** — `capped_placeholder` is needed on the *train* selects only. Measured, and worth a test:
`code-notes.md` explains the 24 is a 2000-character message limit, not a taste, so it can move.

## E. What goes away, and every line that names it

`/help` reads the tree (`cogs/core.py`), so it follows with no edit (P15).

| Thing | Where | Becomes |
|---|---|---|
| `raidtrain` Group + 12 children | `:389` and the §A table | the root, the card and the sub-panels |
| `raidtrains` Group + 3 children | `:392`, `:1449`, `:1474`, `:1520` | the staff row (`Mode…`, `Setup…`, `Logs`) |
| `_ready` `:858` · `_organizer` `:888` · `_organizer_words` `:873` | | the gate + `panel_state` (§F); `is_organizer` `:877` **stays** and is what the panel and `still_organizer` read |
| `_train_or_refusal` `:898` | | **deleted** — nothing types an id any more |
| `_train_choices` `:910` · `_slot_choices` `:924` · `CHOICE_LIMIT` `:66` | | **deleted** — there is no autocomplete behind a button (the voice precedent for `region_choices`) |
| `NOBODY_THERE` `:115` | | **deleted** — `Take somebody off…` lists only taken slots, so the refusal is unreachable. ⚠️ `api/tools/raidtrain.py:69` has its **own** copy and keeps it |
| `SETUP_NOTHING` `:130` | | **deleted** — §C's Setup always writes something or is not pressed |
| `LOGS_GROUPS["raidtrains"]` | `tests/test_bot.py:19` | **deleted** — the loops at `:167` and `:213` would `KeyError` |
| `STAFF_COMMANDS "raidtrains"` | `tests/test_bot.py:38` | **deleted** (§B) |
| `assert len(top) == 38` | `tests/test_bot.py:190` | **one lower than whatever the build measures** — never a hard-coded absolute |
| `HIDDEN_WHEN_OFF` | `command_visibility.py:16–19` | **nothing to change** — measured, raid trains have no entry |

⚠️ **`tests/test_bot.py::test_every_feature_group_has_a_logs_command` shrinks again.** After this
build `LOGS_GROUPS` holds `rolemenu`, `role`, `automod`, `honeypot`, `modmail`, `chat`, `mod` — and
three of those are wave 3's other targets. The recorded finding stands: re-express the guarantee
against the panels' **Logs** button before it covers nothing. **Not this build's job**, but say so
in the report.

**Strings that name a retired subcommand and are rewritten in the SAME commit** — each currently
tells somebody to run something that will not exist:

| File:line | What it says today |
|---|---|
| `cogs/content/raidtrain.py:71` | `FEATURE_OFF` — "A Lead turns them on with `/raidtrains mode on`" |
| `:79` | `NO_SUCH_TRAIN` — "`/raidtrain list` shows the ones coming up" (kept: a train can vanish while a card is open) |
| `:83` | `NOTHING_UPCOMING` — "An organizer starts one with `/raidtrain create`" |
| `:87` | `NOTHING_HELD` — "`/raidtrain list` shows what is running" |
| `:97` | `CREATED` — "People claim an hour with `/raidtrain claim`" |
| `:101` | `LINEUP_NOWHERE` — "a Lead runs `/raidtrains setup channel:#somewhere`" |
| `:126` | `NO_CHANNEL_YET` — "`/raidtrains setup channel:#somewhere` fixes that" |
| `raidtrain.py:59` | `SLOT_TAKEN` — "`/raidtrain status` shows which slots are still open" |
| `:63` | `SLOT_UNKNOWN` — "`/raidtrain status` lists them" |
| `:68` | `CAP_REACHED` — "Release one with `/raidtrain release`" |
| `:73` | `TRAIN_LOCKED` — "An organizer unlocks it with `/raidtrain unlock`" |
| `:77` | `NOT_YOURS` — "`/raidtrain mine` lists the slots you hold" |
| `raidtrain.py:234` | ⚠️ **inside `render_lineup`** — "Take an hour with `/raidtrain claim`". **The whole room reads this one**, on a post that is edited in place forever |
| `personas.py:87–89` | ⚠️ **the chat bot's own answer about raid trains** — four subcommands named |
| `raidtrain.py:54` | `NEEDS_LINK` — measured **already correct** (`/golive` ▸ Link my Twitch channel; the golive panel rewrote it). No change |

**Site touch points.** No route is added, removed or renamed, so `node site/mock/check.mjs` must
report the **same page/route counts** before and after. Two mock copies of a rewritten string drift
otherwise: `site/mock/server.mjs:2504` and `:2545` both carry the mock's copy of `SLOT_UNKNOWN`
naming `/raidtrain status`. `site/public/assets/page-events.js:164` (`NO_TRAINS`) names
`/raidtrain create`. `site/mock/contract.json:3489–3495` lists the seven `web.raidtrain.*` kinds —
**six of them stop being written by §F** (see the KI note in §J).

**Docs rewritten in the same commit** (P15): `docs/access/sweeps.md` rows **48–52** rewritten in
place, not added to; `docs/info/feature-list.md:93` (its command list is the whole F19 row);
`docs/info/phase18-design.md` gets a dated *"its command surface is superseded by the panel"* line at
the top, **not** a rewrite (§C `:137–166` describes the two groups); `docs/info/panels-program.md:81`
(the Raid trains row → shipped, with the measured delta); `docs/info/README.md` gains its row;
`docs/access/OWNER_GUIDE.md` — ⚠️ **it names raid trains nowhere today (measured, zero matches)**, so
this build ADDS one "Run a raid train" row and moves the sweeps count (`:5`, `:82`);
`docs/info/code-notes.md` re-keyed at the merge — the raid-train anchors are
`black_bloc/raidtrain.py:18,20,31,83,95,106,147,189,210,252,278,314`;
`black_bloc/cogs/content/raidtrain.py:146,228,250,290,335,409,436,442,477,493,521,538,572,617,627,643,720,746,817,858,877,988,1007,1127,1190`;
`black_bloc/api/tools/raidtrain.py:103,145,189,254`; `site/public/assets/page-events.js:180,280`.
⚠️ Six of those describe code this build rewrites (`:858` the mode gate, `:877` the organizer gate,
`:988` "every command defers first", `:1007` the order of the claim refusals, `:1127`
`submit_train`, `:1190` `_numbers`) — **re-point them by ANCHOR, do not renumber blindly.**

## F. Extractions (P4) — one function per move, called by BOTH doors

⚠️ **The DB layer stays in the COG**, as it does for applications, voice and youtube — and **not**
as it does for events. `api/tools/raidtrain.py:9–20` imports ten names from the cog; moving them
would be a large mechanical diff for no gain this build needs, and every existing import staying
byte-identical is what makes the API tests' unchanged assertions the proof nothing moved
(wave-0 deviation 4).

**New, module level in `cogs/content/raidtrain.py`** — each does ONE write and ONE log row, each
returns a sentence, each takes a keyword-only `via: str = VIA_DISCORD` and builds its kind with
`logkinds.kind_via` (checklist 34):

| Function | Replaces | Note |
|---|---|---|
| `claim_slot(bot, guild, actor, train, position, login)` | `_claim` `:1007` | the caller keeps `_lock(train_id)` `:409` — the lock and `take_slot`'s `WHERE … user_id IS NULL` `:228` are together the race guard (checklist 6) |
| `release_slot(bot, guild, actor, train, position)` | `_release` `:1072` | |
| `assign_slot(bot, guild, actor, train, position, member, login)` | `_assign` `:1250` | the route at `:294` deletes its `note("web.raidtrain.assign")` and passes `via=VIA_WEBSITE` |
| `unassign_slot(bot, guild, actor, train, position)` | inline `:1284–1305` | same, for `:275` |
| `swap_slots(bot, guild, actor, train, a, b)` | inline `:1324–1344` | same, for `:333` |
| `move_train(bot, guild, actor, train, to)` | `_move` `:1358` | lock and unlock, one function; same, for `:373` |
| `create_and_publish(bot, guild, actor, **fields)` | the tail of `submit_train` `:1155–1188` | one create + one `raidtrain.create` row + `publish_lineup`; same, for `:235` |
| `set_mode(bot, guild, actor, value)` | inline `:1459–1472` | ⚠️ today's `raidtrain.mode` is **bare** — it gains `kind_via`, so a future route cannot double-post |
| `save_setup(bot, guild, actor, **fields)` | inline `:1489–1518` | validates every field with `coerce_value` BEFORE the first write (so a bad value refuses the whole dict rather than writing half), then one `raidtrain.setup` row — the pings-deviation-4 shape |
| `cancel_train(…, *, via=VIA_DISCORD)` | **exists** at `:1414` | ⚠️ **it only gains the keyword** |

🔴 **`cancel_train`'s `via` closes a defect this repo has already recorded** (`TODO.md` 🔧,
"Via-labelling gap"): `POST /api/raidtrains/{id}/status` with `status=cancelled` (`:363–367`) calls
`cancel_train` and adds **no** `note()`, so a website cancellation writes one `raidtrain.cancel` row
labelled **Via = Discord** — and `web.raidtrain.cancel`, which `site/mock/contract.json:3495` lists,
**is a kind nothing has ever written.** Threading `via` through fixes the label and makes the
contract's list true. Add the route to `tests/api/conftest.py:405 one_web_row`.

**Pure, into the EXISTING `black_bloc/raidtrain.py`** — ⚠️ **no new module is needed** (voice had to
create one; this feature already has its pure half, which is a real cost saving):

| New | Signature / what it is |
|---|---|
| `PANEL_MINUTES_KEY = "raidtrain_panel_minutes"`, `panel_minutes(store, guild_id)` | one-liners over `panels.panel_minutes` (`panels.py:97`), exactly as `black_bloc/tempvoice.py:262` |
| `PANEL_TITLE`, `PANEL_TIMEOUT_FOOTER` | wave-0 deviation 1: the footer is a whole sentence, not a format string — "This panel has gone quiet — run /raidtrain again" |
| `RaidMove` + `CARD_MOVES` + `card_buttons(status, *, organizer, staff, held, may_claim, has_taken, slot_count)` | §C's card table AS DATA, proved by a parametrised test |
| `root_buttons(*, organizer, staff, has_trains, holds_any, mode)` | §B's root table AS DATA |
| `taken_positions(slots)` | the mirror of `open_positions` `:155`, for `Take somebody off…` |
| `train_options(rows)` · `slot_options(slots, kind)` | the select options, built on `panels.option_label` (`panels.py:74`) |
| `may_claim(train, slots, user_id, *, ceiling, linked, require_link)` | the four conditions §C's row 0 renders on, in ONE function, so the button and `claim_slot`'s refusals read the same source (P3) |

**Reuse, never re-copy:** `panels.answer`, `panels.db_ready` / `db_up`, `panels.retire`,
`panels.still_staff`, `panels.capped_placeholder`, `panels.option_label`, `panels.clamped` (the card
embed — a 24-slot lineup plus the header runs long), `panels.site_page_url`, `panels.Panel`,
`panels.NoteModal`.

**One thing to ADD to `black_bloc/panels.py`** — and it is the only one:

- **`still_allowed(interaction, ok: bool, refusal: str) -> bool`**, with `still_staff` (`panels.py:31`)
  rewritten as a two-line call to it. P8 says a staff move re-asks instead of trusting the render;
  **raid trains are the first panel whose gate is not `is_staff`** (`is_organizer` `:877` = a
  configured role OR staff), and role menus and automod in this same wave will want it too. Without
  it this build copies `still_staff`'s body for the organizer check — a checklist-15 duplicate on
  arrival. ⚠️ **`panels.py` is edited by every wave-3 branch, so this is a one-function, append-shaped
  change**; if the conductor would rather not touch a shared file mid-wave, the fallback is a local
  `still_organizer` in the cog **plus a named note for the conductor to fold at merge**, exactly as
  `clamped` was folded at the voice merge (voice deviation 8).

**Nothing else moves.** `render_lineup`, `reminder_text`, `live_post_text`, `due_reminders`,
`missed_reminders`, `due_checkins`, `ends_at`, `may_move`, `move_refusal`, `slots_held`, `caps_ok`,
`slot_at`, `neighbours`, `positions_word` all keep their names and their `__all__` entry
(`raidtrain.py:359–404`), so the 21 tests in `tests/test_raidtrain.py` stay green unchanged.

## G. Tests (P16 — one file per source file, mirrored paths)

| File | What it gains |
|---|---|
| `tests/cogs/content/test_raidtrain.py` (**59 tests** today) | `/raidtrain` answers ephemerally with a panel; **parametrised over status × viewer(member/organizer/staff) × holds(0/1/2) × has-open × linked × mode — each renders exactly its §B/§C row and no other**; `Lock` and `Open it for sign-ups` are never both present and neither renders on a `live` train; no claim control on `locked`/`live`/`done`/`cancelled`; `Take somebody off…` absent on an empty lineup; `Give back #N` and `Give an hour back…` never coexist; row 2 never exceeds five controls; a member never gets `Mode…` / `Setup…` / `Logs` / the site link; a non-organizer never gets `Start a raid train`; **the mode-off panel still gives staff the mode select**; an organizer demoted mid-card moves nothing (`still_organizer` at every site) and a demoted staffer opens nothing (`still_staff` on the READS too — pings deviation 10); `db_ready` after every defer; `Start a raid train` defers before `create_train`; every move calls its §F function with `via` untouched (mock it); the timeout disables every item and a re-render `retire`s what it replaced |
| `tests/test_raidtrain.py` (**21** today) | `card_buttons` and `root_buttons` for every state; `may_claim`'s four conditions; `taken_positions`; `train_options` / `slot_options`; `panel_minutes`; and **`SLOT_COUNT_MAX` (24) < 25, so a slot select can never cap** — the fact §D rests on |
| `tests/test_settings_store.py` | `raidtrain_panel_minutes` round-trips, defaults **10**, has help text |
| `tests/test_bot.py` | `LOGS_GROUPS` loses `raidtrains`; `raidtrains` leaves `STAFF_COMMANDS`; `raidtrain` stays in `MEMBER_COMMANDS`; the tree-limit test **recounts** |
| `tests/api/tools/test_raidtrain.py` (**24** today) | ⚠️ **this file DOES change, unlike voice's** — the six routes' `note()`s are gone, so each gains `wf.one_web_row(db, "web.raidtrain.<kind>")` and the assertions are on the row **COUNT** (the applications/golive precedent for checklist 34). The cancel route gains its first `web.raidtrain.cancel` assertion — it has never had one |
| `tests/test_logkinds.py` | the nine raid-train kinds now go through `kind_via`; the AST walk `::test_a_route_never_notes_an_event_its_shared_path_already_logged` must cover `api/tools/raidtrain.py` cleanly |

## H. §J — prove before merge (P17), and the sweep rows

1. `python -m black_bloc` boots; **read `commands synced` and record both numbers** — the drop must
   be exactly one. ⚠️ **TEST_MODE stands and is not touched**: the bot speaks only in
   `#mute-me-bot-test-spam` (`TEST_CHANNEL_ID`) and DMs; `guard.py` is not edited, `_post` `:643`
   keeps logging `raidtrain.post_skipped_test_mode` for any other channel, and this build must not
   look for a token. With no token, measure the tree the only other way:
   `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits`.
2. The parametrised state test: every state renders its row and no other (checklist 3, 12).
3. `python -c "import black_bloc.raidtrain, black_bloc.cogs.content.raidtrain,
   black_bloc.api.tools.raidtrain, black_bloc.personas, black_bloc.panels"` — the substitute for a
   boot, and what catches the new import edges (wave-0 deviation 5).
4. `ruff`; full `pytest`; `node site/mock/check.mjs` (**expect the page/route counts unchanged**);
   `node --input-type=module --check < site/public/assets/labels.js`.
5. Checklist sweep before reporting — **8** and **30** (`AnswersErrors` on every modal, select and
   view), **11** (`allowed_mentions` on every interpolated send: the lineup is full of display names
   and `<@id>`s, and `_mentions` `:627` is the one allowed source of a ping), **12** (the state
   change first, the lineup redraw last — a failed `_refresh_lineup` `:817` must never abort a
   committed claim), **15** (the two `DESCRIPTION_LIMIT`s, §C), **22** (`_numbers` `:1190` still
   bounds the modal — a modal has no `app_commands.Range`), **24** (defer before anything that ends
   in a lineup edit; `code-notes.md` § `:988` says the existing tests assert `response.deferred` on
   all seven commands — the panel's equivalents must keep that), **31/32** (the sweep is untouched),
   **33** (§D), **34** (§F — the six routes).

**Sweep rows.** `docs/access/sweeps.md`'s last row today is **143**. ⚠️ **Four wave-3 design docs are
being written in parallel and none of them may claim numbers** — the BUILD agent reads the file at
build time and numbers this block from the next free row, renumbering at the merge if a sibling
landed first (the youtube and pings builds both did exactly this). Rows **48–52** are rewritten in
place, not added.

| Do this | Expect |
|---|---|
| `/raidtrain` with `raidtrain_mode` **off**, as a member, then as a Lead | the member gets ONE ephemeral panel saying raid trains are off and nothing else; the Lead gets the same line PLUS the sweep block, **Mode…**, **Setup…**, **Logs** and the site link — and **Mode… → on** turns the feature on from the panel, which is the only door now that `/raidtrains mode` is gone |
| **Setup…** → a channel, an organizer role, a ping role → **Save**; then **Clear…** → the ping role | one `raidtrain.setup` line for the save (not three), the lines above update, and clearing empties exactly one key. Nothing says `/raidtrains setup` anywhere |
| **Start a raid train** → title, blank description, `2026-09-20 19:30`, `60`, `4` | the five-field form is read in YOUR stored zone; the lineup post appears in the test channel with four `open` rows and a thread under it; the panel lands back on the root with the new train on **A train…**. ⚠️ In TEST_MODE the post only lands if `raidtrain_channel_id` IS the test channel — otherwise **Logs** has one `raidtrain.post_skipped_test_mode` line |
| **A train…** → the card, as a member with no Twitch link | the lineup exactly as the post shows it, **no** *Take an hour…* select, and a line pointing at `/golive` ▸ **Link my Twitch channel** — never a greyed button |
| Link Twitch, re-open the card, **Take an hour…** → `#1`; then try to take `#2` | the first claim edits the lineup post in place (no second message); the second is refused in words naming `raidtrain_max_slots_per_member`, and after the refusal *Take an hour…* is **gone** on the next render because the cap is now reached |
| **Give back slot #1**, then claim two hours with the cap at 0 | the button reads the slot number; with two held it becomes **Give an hour back…** with both hours on one select |
| As an organizer: **Put somebody in…** → a slot + a member → **Put them in**; then **Take somebody off…** | assign ignores the per-member cap; the off-select lists only TAKEN slots, so "already empty" is unreachable; both edit the lineup post |
| **Change two slots round…** → `#1` and `#3` | the second select never offers the first pick; the swap moves the PEOPLE and never the times; the lineup redraws |
| **Lock the lineup**, then re-open the card | the button now reads **Open it for sign-ups** — never both — and every claim control is gone. On a `live` train neither button is there at all |
| **Call it off…** → type a reason | every slot holder is DMed the reason, the post says cancelled, and the card afterwards offers no move at all except **Back** |
| **My slots…** with slots on two trains, then pick one | the hours in your own clock, and picking a train opens that card |
| **Logs** as a Lead, then leave the panel `raidtrain_panel_minutes` (10) minutes | Logs answers a NEW message and the panel stays; then every control greys out and the footer reads *This panel has gone quiet — run /raidtrain again* |
| The website, after any of the above: Events page → Raid trains → cancel a train | the Logs page shows **`web.raidtrain.cancel`, Via = Website** — today it says `raidtrain.cancel`, Via = Discord (§F) |

## I. The genuine forks — the owner decides, one at a time

**Settled first, by the standing rules, so they are NOT put to him:**

- ✅ **The command is `/raidtrain`, member-visible.** `panels-program.md` §3 already names it, and it
  is the half a member types a hundred times to the staff half's one.
- ✅ **`/raidtrain` stays visible with the mode off, and staff reach `Mode…` from it.** Answered twice
  already (applications I-A2 "Visible", memory I-M1 "open it"), and the staff-final-say rule forbids
  a state staff cannot leave — with `/raidtrains` gone this is the ONLY door to turning it on.
- ✅ **Staff can undo any organizer's stored decision** — assign over a claim, unassign, swap, unlock,
  cancel — because staff are organizers (`is_organizer` `:877`) and every one of those already
  exists. Nothing new to decide.
- ✅ **The lineup post, its thread and the scheduled event are untouched.** Program §7.
- ✅ **`raidtrain_panel_minutes` is a settings key** (checklist 33), not a constant.

**Three questions are genuinely his:**

- **F-R1 — should the LINEUP POST get a button?** Measured: it is a plain text message with **no
  components at all**, so `/raidtrain` is the room's only door to claiming an hour. A persistent
  `DynamicItem` **Take an hour** button on the post would make claiming one click from the channel,
  the way the temp-voice control post works.
  - **(a) Leave the post text-only.** Zero build cost, no restart risk, and P14 puts persistent posts
    outside this program. **Recommended** — and if he wants it, it is a *separate* build, not a rider.
  - (b) Add the persistent button in a later build, with its own `custom_id` carrying the train id.
- **F-R2 — should the panel show PAST trains?** Today `/raidtrain list` is upcoming-only; only the
  website's `scope` control reaches `past` and `all` (`list_trains` `:198`, `SCOPES`
  `api/tools/raidtrain.py:51`).
  - **(a) Upcoming only; the Events page owns history.** One fact one home, and it keeps the train
    select clear of the 25 cap. **Recommended.**
  - (b) A `Show…` select (upcoming / past / all) on the root — costs a row, and makes
    `capped_placeholder` a routine sight rather than an edge.
- **F-R3 — one claim control or two?** §C gives the card a single **`Take an hour…`** select over the
  open hours. Today `/raidtrain claim` also has a zero-decision path (omit the slot, take
  `next_open_position`).
  - **(a) The select alone.** One move, one spelling (P3); the next open hour is named in the card's
    text so nobody has to hunt for it. **Recommended.**
  - (b) A **`Take the next open hour`** button beside the select. One click for the commonest action
    in the feature — the default cap is one slot per member, so most people press it exactly once —
    at the cost of two controls doing one thing.

## J. What NOT to build, and what this costs

**Not in this build:**

- **The lineup post, the thread and the scheduled event.** P14 and fork F-R1. No components are added
  to any of them, and `publish_lineup` `:690`, `_open_thread` `:720`, `_maybe_scheduled_event` `:746`
  and `_refresh_lineup` `:817` are called, never rewritten.
- **`Mark it done` / `Go live` buttons.** `_run_clock` `:493` owns those transitions and the auto-lock
  at start is fixed by design (D11). A button with no shared function behind it is what P4 forbids.
- **Anything from `raid-train-capture.md`'s NO / LATER buckets** — 50-slot trains
  (`SLOT_COUNT_MAX = 24` is a message-length limit with its reason written down), per-slot lengths,
  flyer studio, categories/tags, series, Twitch-chat `!raidnow`, automatic stream titles, SMS.
- **Moving the DB layer out of the cog.** §F, and `api/tools/raidtrain.py`'s ten imports are the
  reason not to.
- **Any new API route or site control.** No `/api/raidtrains/*` route is added, removed or renamed and
  `site/mock/contract.json`'s route list is unchanged. ⚠️ Its **kind** list is not: six
  `web.raidtrain.*` kinds stop being written and one (`web.raidtrain.cancel`) starts. Rows already in
  `action_log` keep the old kinds — that is **KI-19's** exact situation, so **append to KI-19 rather
  than opening a new entry**.
- **`count` / `important_only` on `Logs`.** Lost exactly as they were for every shipped panel; the
  site's Logs page has both (recorded finding — a modal if the owner ever wants them back).
- **Touching `RAIDTRAIN_MODES`, the sweep, the reminder DM, the check-in, KI-15 or KI-16.** This is a
  door swap, not a feature pass. Both known issues survive untouched and unchanged.

**Cost.** Measured wave-2 builds: memory **329k**, youtube **371k**, pings **379k**, voice **385k**,
golive **464k**. This one sits between pings and golive — **budget 380–450k**:

| Pushing it up | Pulling it down |
|---|---|
| Fifteen subcommands over two groups, plus a **1535-line** cog | The pure module **already exists** (`black_bloc/raidtrain.py`, 404 lines) — voice had to create one, and that was a whole test file |
| **Five sub-panels** (Put somebody in / Change two round / Give an hour back / My slots / Setup) — more than any wave-2 panel | Three audiences share one table; no second modal shape (`TrainModal` is reused whole, `NoteModal` is the library's) |
| **Six web routes lose their `note()`s** and gain `via` — the checklist-34 work that put golive at 464k | No route is added; `check.mjs` counts must not move, which is a cheap proof |
| Fourteen strings and eight doc files name a retired subcommand; one of them is inside the lineup post the room reads | One new settings key, one new library function |

**Prep before dispatch** (the 150k+ rule): clean tree, a fresh usage read, and a brief that tells the
agent to **commit at layer boundaries** — (1) the pure table + its tests, (2) the extracted `via`
functions + the route edits + the API tests, (3) the cog panel, (4) the doc/string sweep — so a kill
costs the last layer rather than the build. Point the brief at
[`review-checklist.md`](review-checklist.md), [`panels-program.md`](panels-program.md) §2 and this
document, and carry the owner's F-R1/F-R2/F-R3 answers in it.

## Deviations

Written by the BUILD agent, 2026-09-04, on branch `worktree-agent-aba5d44f8e27a8e28`
(commits `3e54d52`, `f584676`, `4bb059c` and the doc sweep). Everything not listed here was
built as §B–§H say, and all three forks were built as the owner answered them: **F-R1 (a)** the
lineup post is untouched and still carries no components; **F-R2 (a)** the train select is
`scope="upcoming"` only; **F-R3 (a)** `Take an hour…` is the single claim door and there is no
`Take the next open hour` button beside it.

1. **`Outcome` and `refusal` moved into `black_bloc/panels.py`; `chat_panel.py` re-exports
   them.** §F said the ONE thing to add to `panels.py` was `still_allowed` — which was already
   there when this branch started, landed by an earlier wave-3 build. But the shared functions
   need an answer object carrying `(ok, message, code, status)` for the website door, and
   `chat_panel.Outcome` is exactly that. Defining a second frozen dataclass of the same name in
   `cogs/content/raidtrain.py` would have been a checklist-15 duplicate on arrival, so the one
   definition moved down into the library and `chat_panel` imports it and keeps its `__all__`
   entry. No chat test moved; the change is append-shaped in `panels.py` and a three-line
   deletion in `chat_panel.py`.
2. **`card_buttons` and `card_selects` are two functions, not the design's single
   `card_buttons(status, *, organizer, staff, held, may_claim, has_taken, slot_count)`.** The
   selects are not buttons and the parametrised test needs to assert on them separately; folding
   both into one return would have meant a tuple-of-tuples nobody could read. `staff` is not a
   parameter of either: staff ⊆ organizer on a card (`is_organizer` returns true for staff), so
   it would have been an argument neither function reads. `may_claim` became `claimable` on
   `card_selects` because the pure function of that name is what computes it. Same for the root:
   `root_selects(*, staff, has_trains)` carries `has_trains`, so `root_buttons` does not.
3. **`Take somebody off…` also requires the train to be `open` or `locked`.** §C's table gates it
   on "organizer · at least one taken slot" only. Cancelling does not empty the slots, so on a
   cancelled train that gate would still render an organizer move — and §H's `Call it off…` row
   says the card afterwards "offers no move at all except **Back**". The status gate is what
   makes that true.
4. **A select option's time is `%H:%M UTC`, not `<t:…:t>`.** §C asks for each option to carry its
   `<t:…:t>` window. Discord renders no markdown inside a select option's label, so that would
   print as the literal text `<t:1789…:t>`. The viewer's own clock is still honoured on the card
   embed, which is `render_lineup` and is full of real timestamps; the option carries UTC, the
   way the retired `_slot_choices` autocomplete did.
5. **`NOBODY_THERE` is KEPT in the cog and the website's duplicate copy is DELETED instead** —
   the reverse of §E. Once the route calls `unassign_slot`, the shared function is what produces
   the refusal, so the router's own copy became dead. It is still reachable: a card can be
   minutes old and its *Take somebody off…* select stale, and the website reaches it directly.
   One home, in the function that returns it.
6. **`move_train` handles all four reachable targets, not just lock and unlock**, keyed by
   `MOVE_KINDS`. `POST /api/raidtrains/{id}/status` accepts any status the transition table
   allows, so `status=live` was reachable from the website — and used to write
   `web.raidtrain.unlock`, the wrong kind entirely. The four bare and four `web.` kinds are
   enumerated in `tests/test_logkinds.py`'s `KNOWN_DYNAMIC`, which is the guard §H asked for.
7. **`site/mock/contract.json`'s kind list is UNCHANGED**, where §J expected six kinds to stop
   being written. Because the shared functions build their kind with `kind_via`, every one of the
   seven `web.raidtrain.*` kinds is still produced — byte-identical to what `note()` wrote — and
   `web.raidtrain.cancel`, which the contract already listed, starts being written for the first
   time. So there is **no KI-19 note to append**: no kind stopped being written and none was
   renamed. `node site/mock/check.mjs` reports the same **17 pages, 142 routes**.
8. **`FEATURE_OFF` was deleted rather than rewritten.** §E lists it as a string to rewrite; with
   `_ready` gone nothing reads it, and the panel's own `OFF_LINE` says the same thing in the
   place a person now sees it. A rewritten string nothing renders is a second home for the fact.
9. **`docs/info/phase18-design.md`'s superseded banner was REPLACED, not added to.** It already
   carried one, dated 2026-09-03 — describing `/golive` and `/twitch`, the wrong feature
   entirely, written into this doc by mistake by an earlier build. The new banner says so out
   loud rather than quietly correcting it.
10. **`docs/info/cutover-plan.md:45` was also fixed**, though §E does not list it: its row 3d told
    the owner to run `/raidtrains setup channel:… organizer_role:…` and `/twitch link`, both of
    which are now gone. `docs/info/raid-train-capture.md`'s command list was deliberately left
    alone — it is the record of what was ASKED for in 2026-09, not a runbook.
11. **`docs/access/OWNER_GUIDE.md`'s sweeps count (`:5`, `:86`) was NOT moved**, per the brief:
    the conductor moves it at the merge, once the final row numbers are fixed. The "Run a raid
    train" row was added. This branch numbered its sweep rows **163–172** from the next free row
    at build time; a sibling wave-3 build landing first means renumbering at the merge.
12. **The four earlier `*_panel_minutes` keys still have no `labels.js` / `server.mjs` rows.** §D
    offered that as an optional rider; it was left, because it is four unrelated keys' worth of
    diff in files two other wave-3 branches also touch. `raidtrain_panel_minutes` has both rows.
13. **`python -m black_bloc` (invariant P17) was NOT run** — this build has no bot token and was
    told not to look for one. `python -c "import black_bloc.raidtrain, black_bloc.cogs.content
    .raidtrain, black_bloc.api.tools.raidtrain, black_bloc.personas, black_bloc.panels"` and
    `import black_bloc.bot` are the substitutes and both pass. The command count was measured the
    only other way, through
    `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits`: **38 → 37**.
14. **`tests/test_bot.py::test_every_feature_group_has_a_logs_command` now covers five groups**
    (`rolemenu`, `role`, `honeypot`, `modmail`, `mod`) and the recorded finding stands: the
    guarantee should be re-expressed against the panels' **Logs** button before it covers
    nothing. Not this build's job — a positive assertion that `"raidtrains" not in groups` was
    added instead, so the retirement is measured rather than merely absent.
