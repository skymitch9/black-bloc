# One box for the end-of-stream wording — `{live}` replaces the separate suffix

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **DESIGN (Fable, 2026-09-20 20:0x) — dispatches
> with the Discord mock at the 20:50 session reset** (budget, not decision; the owner's rule is that an ask IS the go).
> **Last verified: 2026-09-20 20:0x** against `main` `3c803db` (v149 live): `black_bloc/golive.py:ended_render` `:318` —
> a blank `golive_end_template` keeps the live sentence and appends `golive_end_suffix` (`GOLIVE_END_SUFFIX = " — stream
> ended"` `:68`); a set template is `format_map`'d over `ended_fields` (`{name} {game} {title} {url} {platform} {duration}`)
> and an unrenderable one falls back to the suffix; `settings_store.py` `:302–303` the two `text` keys, `:705–717` their help,
> `:3268` the suffix default; the suffix key is read in `api/tools/golive.py` (the preview), `cogs/content/golive.py`,
> `cogs/content/spotlight.py`, and on the site in `golive-join.js` (`placeSettings`), `labels.js`, `page-golive.js`
> (`END_SUFFIX_KEY`, `END_BLANK_TEMPLATE`), `page-preview-settings.js`.

## The ask, verbatim (owner, 2026-09-20 20:0x)

*"we have a text box to edit the ending annoucement and to edit was is appended at the end of a stream, redundant and
could cause issues if you update one but not the other"*

He is right about the failure: the two boxes are one decision spread over two keys, joined by a rule ("blank template →
suffix") that only the code knows. A staff member who edits the suffix while a template is set changes nothing; one who
blanks the template to "turn the rewrite off" loses their suffix edit's visibility. One box, one rule.

## A. The rule after

**`golive_end_template` is the only end wording**, and it gains one placeholder: **`{live}`** — the announcement's
sentence exactly as it was posted (today's `without_mention(content)`). Its **default becomes `{live} — stream ended`**, so
every server on defaults reads exactly as today. A template WITHOUT `{live}` is a full rewrite (today's behaviour with a
set template); one WITH it appends or wraps. Blank is no longer special: a blank template renders `{live}` alone (the
sentence stays, nothing appended — the honest reading of "blank"), and an unrenderable template falls back to the DEFAULT
template, never to a second key. `golive_end_keep_mention` is untouched (it is about the ping, not the words).

**`golive_end_suffix` is RETIRED**: removed from `KEY_TYPES` / `KEY_HELP` / `TEXT_CHECKS` / the mock `SETTING_SPECS` /
`labels.js` / `placeSettings` (the join fixture's count drops by one) / `page-golive.js` (`END_SUFFIX_KEY`,
`END_BLANK_TEMPLATE`'s sentence, the Wording card's suffix mention) / `page-preview-settings.js`; `ended_render` loses its
`suffix` argument; `GOLIVE_END_SUFFIX` goes (its text lives on inside the template default). The spotlight end path
(`cogs/content/spotlight.py`) renders through the same function and needs no words of its own.

## B. The migration — nobody's wording changes at the deploy

At boot, once (`Database.connect` or the cog's first pass — the builder picks the idempotent spot and says which; the
`settings` table is the target): for each guild, read the stored `golive_end_suffix` (if any) and the stored
`golive_end_template` (if any). If the guild has **a custom suffix and no template** → write `golive_end_template =
"{live}" + suffix` so the posted result is identical. If it has **a template** → leave it (the suffix was never used).
Then **delete the `golive_end_suffix` row** either way, and log one `golive.end_wording_migrated` row (routine) with
what it did (`carried_suffix: true/false`). A second boot finds no suffix row and does nothing. Tests for all three cases.

## C. The site

The Wording card on the Go-live page shows ONE box, **What the announcement says once the stream ends**, with its help
naming `{live}` first (*"`{live}` is the sentence as it was posted; the rest of the placeholders are `{name} {game}
{title} {url} {platform} {duration}`"*), the live preview under it (the v149 markdown box until the Discord mock lands,
then the mock). The Settings page shows the one key. `KEY_HELP` for the template rewritten to say the rule in one
sentence. Every word posted is still a key; one fewer key: **293 → 292**.

## D. Tests, docs, gate

`tests/test_golive.py` (`ended_render`: default = live sentence + " — stream ended"; `{live}` inside a longer template;
a template without `{live}` rewrites; blank keeps the sentence bare; an unrenderable template falls back to the default;
the mention prefix behaviour unchanged), `tests/test_settings_store.py` (the key is gone; the count), the migration's
three cases in `tests/storage/test_db.py` or the cog's test — wherever it lives, `tests/cogs/content/test_golive.py` +
`test_spotlight.py` (the end edit still renders), `tests/api/tools/test_golive.py` (the preview answers the new
default), `golive-join.test.mjs` (the fixture minus one key), the key count guards. Both `pytest -n 8` orders, `ruff`,
ES parse, `check.mjs`, the four node tests, env cleared. Docs: `code-notes.md`; this doc's `## Deviations` + `## What was
NOT verified`; `golive-design.md` / `golive-page-design.md` one dated line each; `architecture.md` (keys); `docs/info/
README.md`; `sweeps.md` rows `EW-a…` (a: the Wording card has ONE end box and no suffix box anywhere on the site; b: on
defaults an ended stream's post reads exactly as before; c: put `{live} (over)` in the box → the post ends with "(over)";
d: a template without `{live}` rewrites the whole thing). NOT `TODO.md` / `DONE.md` / `deploys.log` / `KNOWN_ISSUES.md`.

## Deviations

*(the build agent writes here what it had to do differently, dated)*
