# Temp voice — a shadow mode: the lobby hidden from members until it is switched on, then un-hidden and synced by the bot

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 🔨 **BUILT on branch `tempvoice-shadow`
> (off `main` `c56962f`), NOT merged and NOT deployed** — the `## Deviations` foot is the truth where the build
> departed from §A–§F, and it is what a reviewer reads first. Planned as v125, beside `front-door`.
> **Last verified: 2026-09-17 14:0x** by the build: `TEMPVOICE_MODES` is now `("off", "shadow", "on")`,
> `makes_rooms` is the one mode predicate, `apply_mode` / `hide_lobby` / `show_lobby` /
> `install_mode_hook` are in `cogs/community/tempvoice.py`, the mock row and `labels.js` carry the third
> value, and the v117 *"staff-only"* claim in `voice-panel-design.md` is struck (checklist 35).
> ⚠️ **NOT verified:** anything against Discord — no lobby was hidden, no **Sync now** was pressed, no
> mode was flipped and the bot was never booted; every claim is from the suite. ⚠️ **`tempvoice_mode` was
> NOT set to `shadow`** — that is still the conductor's step after the deploy. Before that,
> **2026-09-17 13:18** against `main` `3ab2f0d`: the lobby's overwrites read off Discord by the token (below),
> `TEMPVOICE_MODES = ("off", "on")`, `creator_overwrites` / `join_roles` / `repair_creator_channel`, the v117
> lobby deviations, cutover row **P5a**. ⚠️ Secret NAMES only.

## Owner ask, verbatim (2026-09-17 13:1x)

*"i had to manually make join to create not visible to members or everyone, let this mean that the feature is in
shadow mode with whatever rules it had before. when shadow mode turns off set member visibility back to on and also
do a sync of the permissions of the category"*

## What was measured — and the conductor's error

The lobby (`Join To Create A Channel`, `1542419019099807835`) was moved to *Voice Channels* at v117 with its
overwrites "kept". They were: Member **view + connect allow**, Bots allow, Aunties / Uncles allow, Leads allow,
the bot allow, @everyone deny — because `creator_overwrites` adds `tempvoice_allowed_role_id` (Member) through
`allow_join`. So members could see and join the lobby in the main voice area; the conductor had reported it as
staff-only, which was wrong. The owner set **Member view → DENY** by hand at 13:1x. Today's overwrites:

| Target | view | connect |
|---|---|---|
| @everyone | deny | deny |
| Member (`tempvoice_allowed_role_id`) | **deny** (by hand) | allow |
| Aunties / Uncles, Leads, Bots, the bot | allow | allow |

## A. `tempvoice_mode` gains `shadow`

`TEMPVOICE_MODES = ("off", "shadow", "on")`, help: *"off, shadow (join-to-create works, but only staff can see the
lobby — the rooms it spawns follow it), or on (the lobby is visible to whoever its category shows)"*. Registry +
mock row + label; the mode helpers that read `== "on"` today must treat `shadow` as working (spawning, the panel,
the reconcile) — grep every `tempvoice_mode` read. **The live value is set to `shadow` by the conductor after the
deploy** (never by the build), and the registry default stays `on`.

## B. What shadow does to the lobby — the reconcile enforces it

On every reconcile (`reconcile_channels`, `on_ready` + the five-minute loop) and on Setup/repair, while the mode is
`shadow`: every lobby in `tempvoice_creator_ids` carries **view = False** for `@everyone` AND for
`tempvoice_allowed_role_id` (the Member role), on top of whatever else it has; the staff roles, the bot and any
role the owner allowed by hand keep their allows (never remove an allow that is not the allowed role's). Nothing
else changes: `creator_overwrites`' allowed-role allow is simply masked by the deny while shadow is on. Rooms follow
the lobby (`tempvoice_room_overwrites = lobby`, the v117 default) so they are staff-only too. Write one log row
`tempvoice.lobby_hidden` the first time a lobby is changed, not on every sweep (compare before writing —
checklist: no edits that change nothing).

## C. Flipping shadow → on — the bot un-hides and syncs, once

When the stored mode changes from `shadow` to `on` (the settings-store on-change hook, the same place
`golive_mode`-style flips are noticed — find how other cogs react to a mode change, or run it on the next reconcile
with a "last seen mode" remembered in memory + a log row), for each lobby:

1. `lobby.edit(sync_permissions=True, reason=...)` — Discord's own **Sync now**: the lobby takes exactly its
   category's overwrites (the owner's *"do a sync of the permissions of the category"*).
2. Then re-apply `creator_overwrites(category, allow=join_roles, me=guild.me)` **plus the staff reach**
   (`spawned.staff_reach`, v121) on top — so the allowed role can see and connect again (the owner's *"set member
   visibility back to on"*), the bot keeps manage, staff keep reach. One `edit(overwrites=...)`.
3. Log `tempvoice.lobby_shown` with the lobby id and what changed.

Flipping on → shadow hides again (§B on the next reconcile — run it immediately on the flip too). `off` changes
no permissions (as today). ⚠️ Under `TEST_MODE` the lobby sits outside the test category — the guard does not gate
`edit_channel`, and the lobby is a place `may_act_in` accepts (v117), so both edits go through; say so in the reply.

## D. Cutover

`docs/info/cutover-plan.md` row **P5a** is rewritten: *"flip `tempvoice_mode` shadow → on (Settings ▸ tempvoice, or
`/voice` ▸ Mode…); the bot syncs the lobby with its category and gives the allowed role its view back — nothing
to do in Discord; ⚠️ never press Setup to do it"*. The `/voice` panel's staff block shows the mode and, in shadow,
the line *"the lobby is hidden from members while temp voice is in shadow"*.

## E. Tests (mirror the package)

`tests/cogs/community/test_tempvoice.py`: shadow hides (both denies present, staff allows untouched, a hand-made
extra allow untouched, no edit when already hidden); on → the sync call then the re-applied allows in one edit and
the log row; shadow → on → shadow round trip; `off` touches nothing; the mode helpers accept `shadow`;
`tests/test_settings_store.py` the enum. Both orders.

## F. Docs

`code-notes.md`; this doc's `## Deviations`; `voice-panel-design.md` (strike the v117 deviation line that said the
lobby was staff-only, checklist 35, and point here); `cutover-plan.md` P5a; the voice guide in `guides_seed.json`
(a fact: *"while temp voice is in shadow only staff see the lobby"*); `sweeps.md` rows `TS-a…`. NOT `TODO.md` /
`DONE.md` / `deploys.log`.

## Deviations

Written by the build agent, **2026-09-17** (branch `tempvoice-shadow`, off `main` `c56962f`).
Eight departures from §A–§F, all reported. Nothing met Discord.

1. **§C's reasoning about `may_act_in` is wrong; its conclusion is right.** The doc says *"the
   lobby is a place `may_act_in` accepts (v117)"*. Measured: `may_act_in` accepts a channel the
   guard **owns** or one in the test channel's category, and the lobby is neither —
   `own_channel` is called on spawned rooms (`reconcile_channels`, `_create_for`) and never on
   the lobby, which is also why `repair_creator_channel` still refuses it under `TEST_MODE`
   (the v117 deviation, deliberately). So `may_act_in(lobby)` is **False** today. Both edits go
   through anyway, for the other reason the same paragraph gives: the guard patches
   `send_message` / `edit_message` only and has never gated `channel.edit`. **The hide and the
   show therefore do NOT ask `may_act_in`** — asking it would have made shadow inert in exactly
   the state this ships into. ⚠️ Under `TEST_MODE=true` these two edits are real writes to a
   real channel in the main voice area; that is intended, and it is the only thing this feature
   does outside `#blackbloc-logs`.

2. **The mode control is a `Mode…` card with a select, not a toggle button.** §D's cutover text
   names `/voice` ▸ **Mode…**, which did not exist — the staff block carried a two-state toggle
   (`MODE_OFF_MOVE` / `MODE_ON_MOVE`). Three modes cannot be a two-state toggle, and cycling
   them would be the *"status menu with two spellings of the same move"* the owner's panel rule
   forbids (from `on` it would take two presses to reach `shadow`). Built as one **Mode…**
   button → a card with a three-option select drawn from `TEMPVOICE_MODES`, descriptions from
   `MODE_MEANS`, **Back** beneath it. `card_buttons` **lost its `mode_on` parameter**, and
   `run_mode` now takes the wanted value instead of computing a toggle.

3. **The `guides_seed.json` fact is a FAULT row, not a `facts` entry.** §F asks for *"a fact:
   'while temp voice is in shadow only staff see the lobby'"*. `guides.FACT_KINDS` is
   `("setting", "probe")` — a `facts` entry is a typed **reference**, not free text, so that
   sentence has no valid shape there. It went into the voice guide's existing *"No creator
   channel"* fault, which is the question a member in shadow actually asks. The
   `{"kind": "setting", "ref": "tempvoice_mode"}` fact already present now carries the three-way
   help text, so the guide states it twice over, in both the places a reader looks.

4. **A third log kind was added that §B/§C do not name: `tempvoice.lobby_failed`.** Checklist 2
   and 7 — a refused `edit` must not be silence and must not share a kind with a success. It
   carries `doing` (`hide` / `sync` / `show`) in the details rather than splitting into three
   kinds. It needs no registration (`IMPORTANT_SUFFIXES` classes `_failed`); the two named kinds
   `tempvoice.lobby_hidden` and `tempvoice.lobby_shown` were added to `logkinds.ROUTINE`.

5. **`labels.js` changed, though §A only says "registry + mock row + label".** The label read
   *"Whether people can make their own voice rooms"*, which is no longer the whole of what the
   key decides; it is now *"…, and who sees the lobby"*. Nothing else on the site moved — the
   Settings page reads its choices from `KEY_CHOICES`, so `shadow` appears there for free.

6. **The flip is noticed by BOTH doors §C offers, not one.** The `settings_store.on_change` hook
   (registered in `cog_load`, guarded against a double registration) makes it immediate; a
   last-seen mode on the bot (`mode_memory`, seeded by every reconcile) is what lets
   `reconcile_channels` converge as well, and is what stops `off → on` syncing a lobby that was
   never hidden. One function, `apply_mode`, serves both so they cannot disagree.

7. **`make_creator_channel`'s hand-rolled live-lobby list became `live_lobbies`.** It called
   `guild.get_channel` twice per id inline; the new sweep needed the same list, and two spellings
   of *"the lobbies this guild still has"* is the duplication checklist 15 exists for.

8. **`MODE_OFF_LINE` now fires only on `off`, not on "anything but `on`".** In shadow a member
   with the role really can make a room — they just cannot see the lobby — so telling them
   join-to-create is off would be false. The shadow sentence went on the **staff** block instead
   (`status_lines`), where the person who can act on it is.

**Not done, and why.** Nothing on Discord: no lobby was hidden, no **Sync now** was pressed, no
mode was flipped, and `python -m black_bloc` was never booted (a worktree holds no token). Every
claim here is from the test suite and from reading `main`. ⚠️ `tempvoice_mode` was **not**
touched — the live value is still whatever it was, and setting it to `shadow` is the conductor's
step after the deploy, as §A says. `TEST_MODE=true` was not touched. The `## Deviations` foot of
`voice-panel-design.md` was corrected (checklist 35) but the rest of that page's v117 prose was
left as written.

**Gates, measured in the worktree with a cleared environment** (`env -i` plus `PYTHONPATH`):
`pytest -q -n auto` **6166 passed** forward (33.6 s) and **6166 passed** under `BB_REVERSE=1`
(52.5 s), from **6223** at `c56962f` — the fall is the `mode_on` parametrize dimension coming off
`test_every_state_renders_exactly_its_row_of_the_table` (**−80** instances), against **+10** for
the `shadow` row of the cog's own table test and **+13** new tests. `ruff check .` clean;
ES-module `--check` clean across `site/**`; `node site/mock/check.mjs` **19 pages / 178 routes /
15 core settings, all keys present**; `discordmd.test.mjs` and `labels.test.mjs` both ok.
`ruff format --check` is red repo-wide and is not a gate.

⚠️ **KI-26 fired twice during this build** — `pytest -n auto` stalled with every worker idle, once
at spawn (no output at all after 14 minutes) and once at **77 %** (log untouched for 7 minutes).
Each was killed by **process tree** (`taskkill /F /T /PID <the pytest root>`, never by image name)
and the retry passed. That takes the count to **nine**.
