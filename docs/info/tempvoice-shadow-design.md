# Temp voice — a shadow mode: the lobby hidden from members until it is switched on, then un-hidden and synced by the bot

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **DESIGN, dispatching to Opus 2026-09-17 13:2x
> as branch `tempvoice-shadow`** (v125, beside `front-door`). **Last verified: 2026-09-17 13:18** against `main` `3ab2f0d`:
> the lobby's overwrites read off Discord by the token (below), `TEMPVOICE_MODES = ("off", "on")`,
> `creator_overwrites` / `join_roles` / `repair_creator_channel` in `cogs/community/tempvoice.py`, the v117 lobby
> deviations in `voice-panel-design.md`, cutover row **P5a**. ⚠️ Secret NAMES only.

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

*(the build agent writes here what it had to do differently, dated)*
