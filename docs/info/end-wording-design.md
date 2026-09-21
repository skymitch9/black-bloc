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

## A2. The off / edit toggle goes too — the announcement is ALWAYS edited when the stream ends

Owner, 20:0x, verbatim: *"also the when stream ends edit or off toggle to change whether we dynamically adjust is
unneeded. we will also edit our message. remove this aption"*. **`golive_end_mode` (enum `off` / `edit`) is RETIRED**:
the end path runs as if `edit` for everyone — `golive.py:576` (`ends_by_editing` or whatever `:576` names) returns True
unconditionally and then goes, `cogs/content/golive.py:596` / `:1388` and `cogs/content/spotlight.py:554` stop reading
it, `api/status.py` drops it from the status line, `end_details` stops reporting a mode. On the site: the mode switch in
the Wording card and the *golive_end_mode is off, so…* / `END_UNKNOWN` sentences (`page-golive.js:102`, `:110`, `:1027`,
`:1042`) go; `golive-join.js:placeSettings`, `labels.js`, the mock `SETTING_SPECS`, `page-preview-settings.js` lose the key;
the join fixture drops by one more. Migration: delete any stored `golive_end_mode` row at the same boot pass as the
suffix (the row is meaningless once nothing reads it; log it in the same `golive.end_wording_migrated` details as
`dropped_mode: <value or null>`). **Keys 293 → 291.** A guild that had set `off` will now see its announcements edited
when streams end — that is the owner's decision, stated above; say so in the sweep row.

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

## C2. Follow-up (owner 20:1x) — the live card's top line becomes a key, and the card is ONE editor with a Starting / Ending toggle

Owner, verbatim: *"we have the option to change the card for ending stream: "What the card's top line says once the
stream is over" but not for starting stream, the ending stream and the starting stream should basically look the same,
maybe instead of a stack have a toggle for starting and ending since theyre duplicates and we can save space"*.
**Dispatched as the follow-up of THIS build once its first half lands** (same branch or a fresh brief to the same
agent — the conductor decides at landing), so three agents stop editing one function.

1. **`golive_live_author`** (text, group golive, default **`{name} is now live on {platform}!`** — the words
   `author_line` `:203` builds today, with `LIVE_VERB` folded in so no server's card changes): `announcement_embed` /
   `render` read it through a `live_author(template, name, platform)` that mirrors `ended_author` `:343` (blank keeps
   the default; unrenderable → the default; `{name} {platform}` are the fields — `{duration}` is meaningless while live
   and is refused by the validator). `TEXT_CHECKS`, `KEY_HELP` (*"the card's top line while they are live; {name}
   {platform}"*), mock row, label, `placeSettings` in the same drawer as `golive_end_author`, the join fixture (+1: after
   §A/§A2's −2 the page has **292 → 292 keys?** — count it; the fixture asserts the number), `api/status.py` if it lists
   author keys, the preview route (v149's `/api/golive/preview` and/or the Discord mock's renderer) answers it. Keys:
   291 after §A2, **292** after this.
2. **The Wording card is ONE editor with a segmented toggle `Starting` / `Ending`** (the `segment` construct `ui.js`
   already has — the go-live strip and the polls preview use it): the same three things for whichever is picked — the
   wording box (`golive_template` / `golive_end_template`), the top-line box (`golive_live_author` / `golive_end_author`),
   the preview (the v149 box, or the Discord mock when it lands — pass the picked side as `sample.ended`). The
   *Preview as Twitch / YouTube* chips stay above both. The two stacked cards (`WHILE_LIVE_TITLE` / the ended card) and
   the `msglist` with both lines go; `golive_end_keep_mention` stays with the Ending side. Nothing else on the page moves.
3. Tests: `live_author` (default, custom, blank, unrenderable, `{duration}` refused), the key guards, the fixture; a
   headless render of the card in both toggle states with the console read. Sweep rows `EW-e` (the Starting side's top
   line edits and the live card shows it) and `EW-f` (the toggle swaps the three boxes; nothing else on the page moves).

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
