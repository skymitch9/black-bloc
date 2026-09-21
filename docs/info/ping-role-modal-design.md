# Add a ping role — make a NAMED role from the modal, and refuse a duplicate name without closing it

> **Audience:** the build agent and reviewers. **Status:** TRACKED · ✅ **LIVE as v150** (release `575dde2`, deployed 2026-09-20 23:32 Phoenix) · was BUILT on branch `ping-role-modal` (off `main` `495d7b6`, 2026-09-20 22:xx — commits `95788f6` the modal, `4f8dac5` the rename). ⚠️ **NOTHING IN IT HAS MET DISCORD YET** — see
> `## Deviations` and `## What was NOT verified` at the foot, and sweeps **701–705** (were `PR-a` … `PR-e`; ⚠️ each MAKES OR RENAMES A REAL ROLE). Was
> 📐 **DESIGN (Fable, 2026-09-20 21:3x), dispatched to
> Opus as branch `ping-role-modal`** the same turn. **Last verified: 2026-09-20 21:3x** against `main` `e177b27`:
> `page-golive.js:addPingRole` `:457` — an `ask()` modal with a role select (*Use an existing role, or leave it to make a new
> one*) and a sentence naming the role the template would make; `ui.js:ask` `:701` resolves on confirm and CLOSES — a
> refusal after it lands as a notice on the page, not in the modal; `pings.ensure_fan_role` `:499` (`existing_role=`
> reuses a picked role, else makes one named by `fan_role_name(template, name)` `:530`; refusals `ALREADY_HAS_ONE`,
> `ROLE_UNASSIGNABLE`, `CANNOT_MAKE_ROLE`); `api/tools/pings.py` `POST /streamers` (`member_id` | `spotlight_id`,
> optional `role_id`). Discord allows two roles with one name; nothing today checks.

## The ask, verbatim (owner, 2026-09-20 21:3x)

*"in the golive i see the ability to set a ping but not to make a ping role. I should be able to make a role and set it
in the golive menu, also if 2 roles have the same name when trying to make a new one give a warning so they know it
already exist. dont close the modal in error though just inform the user and dont let them set a duplicate."*

## A. The modal — two clear choices, one of them named

`addPingRole` becomes a **form dialog that stays open until it succeeds or is cancelled** (a new `ui.js:askForm({title,
body, confirmLabel, onConfirm})` beside `ask()`: same `<dialog>` construct and stacking, but `onConfirm` returns a sentence
to show inside the dialog and keep it open, or `null` to close — every refusal the route answers lands INSIDE the
modal, in words, and the fields keep what was typed). Its body:

1. A segment **Make a new role** / **Use an existing role** (the `segment` construct).
2. *Make a new role*: a text box **Role name**, pre-filled from `pings_fan_role_template` with `{name}` (so it reads
   *GamesDoneQuick pings* for a channel, *Casey pings* for a member) and editable; under it, live as they type, one of:
   *"Black Bloc will make **Casey pings**."* · ⚠️ *"A role named **Casey pings** already exists — pick it under Use an
   existing role, or choose another name."* (the roles list the select already loaded, compared case-insensitively
   after trimming) — and while that warning shows, the confirm button is **disabled**.
3. *Use an existing role*: the role select as today, with *"That role becomes their ping role; nobody is added to it."*
4. Confirm **Add the ping role** → `POST /api/pings/streamers` with `member_id`/`spotlight_id` and EITHER `role_id`
   OR `name`. A refusal (below) shows inside the modal; success closes it, the row re-renders.

## B. The server — the name is the client's suggestion, the guild is the truth

`ensure_fan_role` gains `name: str | None` — when given, it is the role's name instead of the template's (trimmed,
clamped to Discord's 100, refused in words when blank); before creating, it looks for an existing role with that name
(case-insensitive) and **refuses with `DUPLICATE_ROLE`** (*"A role named **Casey pings** already exists in this server,
so nothing was made — pick it as the existing role, or choose another name."*) — the route answers 409
`duplicate_role`. The template path keeps working for every caller that passes no name (Discord's `/pings`, the auto
creation on link), AND it gains the same duplicate check: a template-named role that already exists is **reused**
rather than duplicated when it is assignable (that is what a person would expect), logged with `reused: true` — say so
in Deviations if the reuse changes any existing test. `POST /api/pings/streamers` accepts `name`; the mock mirrors it
including the duplicate refusal against its seeded roles. Discord's `/pings` staff door (**Give a streamer a role**)
is unchanged — the modal is the site's; note it.

## C. Words — the modal's sentences are constants in `page-golive.js`; the refusal is `pings.DUPLICATE_ROLE`; no key.

## D. Tests, docs, gate

`tests/test_pings.py` (a given name is used; a duplicate name refuses; a blank name refuses; the template path reuses
an existing same-named assignable role and logs it), `tests/api/tools/test_pings.py` (`name` accepted; the 409 in words),
the mock route, `site/mock/check.mjs`; a headless render of the modal on `/golive.html` in both segments, typing a name
that clashes with a seeded role (the mock seeds *Casey pings*) → the warning and the disabled confirm, then a fresh name
→ success; the console read. Docs: `code-notes.md`; this doc's `## Deviations` + `## What was NOT verified`;
`pings-remake` design and `spotlight-pings-design.md` one dated line each; `sweeps.md` rows `PR-a…` (a: Make a new role
with a fresh name → the role exists, the row shows it; b: type an existing role's name → the warning, the button greys,
the modal stays; c: Use an existing role; d: the modal stays open on a server refusal and shows it). NOT `TODO.md` /
`DONE.md` / `deploys.log` / `KNOWN_ISSUES.md`.

## Deviations

*(written by the build agent, branch `ping-role-modal`, **2026-09-20 22:xx**, off `main` `495d7b6`.
Everything §A–§D asks for that is not listed here was built exactly as the body says.)*

0. ⚠️ **§A's "leave it blank to make one" path is GONE, at the owner's own refinement** — *"i see
   that i was partially wrong, leaving it blank sets an auto role. how about we don't do that and we
   have a new role button, the name is automatically generated in an editable text box so the end
   user can change the role name or hit confirm and take the role name we auto generated"*. So
   **Make a new role** is the segment's FIRST option and is selected by default, its **Role name**
   box arrives already holding the template's name, and confirm takes whatever is in the box. There
   is no way left to ask the site for a role without naming it. ⚠️ The Discord door (`/pings` ▸
   **Give a streamer a role**) and the automatic creation on link still use the template with no
   name, which is the whole reason `ensure_fan_role(name=)` is optional rather than required.

1. ⚠️ **THE FINDING: `tests/test_pings.py:FakeRole.delete` never took the role off the guild, and
   Discord does.** §B's template-path reuse turned that into a failure within a minute —
   `hide_streamer` deleted an unworn role, the role stayed in `guild.roles`, and the next
   `ensure_fan_role` "reused" a role that no longer existed. The fake now removes itself
   (`FakeGuild.add_role` hands each role its guild). Two tests leaned on the old lie and are
   corrected, not weakened: `test_hiding_yourself_drops_an_unworn_role_and_keeps_a_worn_one` now
   really gets a second role, and `test_taking_a_channels_ping_role_away_obeys_the_delete_setting`
   holds the role object before the delete and asserts `get_role(...) is None` after it. **No
   production code was changed for either.**

2. **The template path's reuse is gated on `assignable`, which §B did not say.** A same-named role
   Black Bloc cannot hand out is worse than a duplicate: every follower would be stranded. So an
   unassignable clash makes a second role, and a test pins it.

3. **`Outcome` gained a `code`, and the route maps it.** §B says "the route answers 409
   `duplicate_role`", and the route had one `raise Refused(409, "not_created", …)` for every
   refusal. Matching on the sentence would have broken the first time a word changed, so the refusal
   carries its own name: `duplicate_role` → 409, `blank_role_name` → 400, `fan_role_gone` → 404,
   everything else unchanged at 409 `not_created`. `code` defaults to `""`, so no existing refusal
   moved.

4. **The local streamer name inside `ensure_fan_role` is `who` now.** The new parameter had to be
   `name` (it is the role's name and the payload's key) and the function already had a local `name`
   for the person or channel. Nothing else changed about those sentences.

5. **`site/mock/server.mjs` refuses against the SEEDED roles, and a role the mock makes now lives in
   `state.golive.madeRoles`.** The file's own note forbids pushing into module-level `ROLES`
   (check.mjs re-seeds `state` between routes), so made and renamed roles go in `state`, `roleOf`
   reads it first and `/api/ref/roles` serves the overlay. That is what lets the rename work on a
   role the mock invented thirty seconds earlier.

6. **`contract.json`'s POST body was left alone.** Adding `name` there would have made `check.mjs`
   take the typed path and never exercise the template path. The two PATCH rows below are new; the
   POST's answer keys did not change.

7. **The modal's live check reads `refRoles()`, which caches for the life of the page.** A role made
   in another tab is not in it. That is not a hole, it is the reason the dialog stays open: the
   SERVER's `DUPLICATE_ROLE` catches it and the sentence lands inside the modal with the fields as
   typed. Sweep `PR-d` is exactly that walk.

8. **Two dialogs, not one.** `ask()` resolves and closes; `askForm()` cannot. They share the CSS
   (`dialog.ask`) and nothing else, and each keeps its own node. No CSS changed — the CSP is
   `style-src 'self'` and nothing new is inline.

9. **`.field` is `display: grid`, so `hidden` does not hide it.** The segment swaps the two controls
   by replacing the children of a plain `<div>` instead.

### The rename (owner ask, same sitting — 2026-09-20 22:xx)

Owner, after pressing the first build: *"i was able to set an auto generated one, i wasnt able to
edit it on the go live screen where i made it, it should be editable right away."* Added on this
branch rather than a second one, because it is the same files and the same dialog:

10. **`Rename…` sits beside `Remove` in the drawer's Ping-role group**, member rows and channel rows
    alike, and **renders only when `row.role` is a role Discord still has** (the 2026-09-03 rule: a
    move renders only when it is valid). A role deleted by hand offers `Remove`, which is the move
    that actually helps.

11. **`pings.rename_fan_role(bot, guild, row, name, *, by, via)` is the one path** — it takes the
    fan-role ROW (member or channel; `is_spotlight` decides), refuses a blank name, a role the guild
    no longer has (`FAN_ROLE_GONE`, code `fan_role_gone` → **404**), a role Black Bloc cannot hand
    out, and a name another role already has (`DUPLICATE_ROLE`, **excluding the role's own current
    name** — renaming *Casey pings* to *casey pings* is allowed). It calls `sync_streamer_menus`, so
    the panels people follow from say the new name in the same write.

12. **`pings.fan_role_renamed` is ROUTINE, not IMPORTANT**, as the ask specified — `fan_role_created`
    and `fan_role_removed` are IMPORTANT and a rename is not a change of who is pinged. It is still
    an `action_log` row on the Logs page, with `from` and `to`. ⚠️ Worth one look by the owner: if a
    rename should reach the Discord log channel, moving it is a one-line change in `logkinds.py`.

13. **The route is `PATCH`, and the spotlight route is declared BEFORE the member route**, the same
    ordering the DELETE pair already needs, or `spotlight` would be read as a member id.

14. **`tests/api/test_contract.py`'s seed gained a SECOND spotlighted channel** (*ESA Marathon*)
    whose ping role is a role the fake guild actually has, because the existing one's role is
    deliberately absent and a rename must edit a real role. `rewind()` builds a fresh guild per
    entry, so the new name never escapes into another entry.

15. **`tests/api/conftest.py:WebRole` gained `edit`**, the same one-line fake `delete` already was.

## What was NOT verified

*(2026-09-20 22:xx, branch `ping-role-modal`)*

- ⚠️ **NOTHING IN THIS BUILD HAS MET DISCORD.** No role has been made, named, renamed or refused on
  a real server; `guild.create_role`, `role.edit` and `named_role` were exercised only against the
  fakes. The owner's sweeps **701–705** (were `PR-a` … `PR-e`; ⚠️ each MAKES OR RENAMES A REAL ROLE) are the only proof that will exist until somebody
  presses the buttons.
- **Not merged and not deployed.** The branch is `ping-role-modal`; nothing has been pushed to Fly
  and the live site still has the old modal.
- **The browser pass was against the local MOCK on `127.0.0.1:8784`, in
  `chrome-headless-shell`** — not the real API, not the deployed site, and not a phone. No window
  was resized, so **the 390 px layout of either dialog is unverified**.
- **`ui.js:askForm` has no unit test** — there is no DOM harness in this repo for `ui.js`, and the
  `site/mock/*.test.mjs` files are pure-function fixtures. Its behaviour is covered by the headless
  walk only.
- **`page-golive.js:tidyName` / `fillName` / `roleNameBox` are likewise untested by fixture**, for
  the same reason. `pings.typed_role_name`, which they mirror, IS unit-tested.
- **Nobody has renamed a role that somebody is WEARING on a real server.** The suite asserts the
  wearers survive (`role.members` is untouched), which is what `role.edit` does — but that is
  discord.py's behaviour taken on trust, not measured.
- **The mock cannot refuse a name it invented in an earlier run of the same session** in the way a
  guild would, because `seed()` empties `state.golive.madeRoles` between check.mjs's entries. The
  real server has no such gap.
- **No migration, no schema change, no new settings key** — so nothing here needs to meet the live
  database.
