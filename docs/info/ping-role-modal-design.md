# Add a ping role — make a NAMED role from the modal, and refuse a duplicate name without closing it

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **DESIGN (Fable, 2026-09-20 21:3x), dispatched to
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

*(the build agent writes here what it had to do differently, dated)*
