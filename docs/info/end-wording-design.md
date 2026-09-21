# One box for the end-of-stream wording — `{live}` replaces the separate suffix

> **Audience:** the build agent and reviewers. **Status:** TRACKED · ✅ **BUILT 2026-09-20 21:0x on branch
> `end-wording`, off `main` `be78bff`** — ⚠️ **not merged, not deployed, nothing has met Discord and the boot migration
> has never run on the live database**; the `## Deviations` foot is the truth where it departs from the body, and
> **Deviation 1 is a decision the conductor owes before the merge**. Sweeps `EW-a … EW-d`.
> Was: 📐 DESIGN (Fable, 2026-09-20 20:0x).
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

**2026-09-20, branch `end-wording`, off `main` `be78bff` (v149 live).** Eight, worst first.

1. 🔴 **§A's "so every server on defaults reads exactly as today" IS NOT TRUE, and the build shipped
   the design's value anyway.** The design's own header measured `ended_render` and the suffix but
   never read `settings_store.py:69`, where **`golive_end_template` already had a non-blank default**:
   `**{name}** was streaming **{game}** — the stream has ended. {url}`. A guild on defaults therefore
   got a **full rewrite** today, not the live sentence plus a suffix — the suffix path was reached
   only by a guild that had deliberately BLANKED the template. Changing the default to
   `{live} — stream ended` (stated twice: §A and §D's first test) is what the spec says, so that is
   what was built, but it **changes what an ended announcement says on every server that has not
   stored its own end wording**: from *"**Ada** was streaming **Celeste** — the stream has ended.
   https://…"* to *"REGULATORS! Mount up! **Ada** is currently streaming **Celeste**! Check it out:
   https://… — stream ended"*. ⚠️ **This is a decision for the conductor before the merge, not a
   detail.** To keep today's wording instead, set `GOLIVE_END_TEMPLATE` back to the old sentence (it
   has no `{live}`, so the new code renders it as a rewrite exactly as before) and the only other
   edits are `END_MARK_DEFAULT`'s derivation (give it the literal `"stream ended"`) and the handful
   of tests that assert the new default. Sweep row **EW-b** is written to what the code now does.
2. **The embed footer's mark needed a home the design never gave it.** `ended_embed` /
   `ended_footer` took the SUFFIX, not the template, and the design's §A lists neither. Hard-coding
   *stream ended* would have broken the owner's standing *every word the bot posts is editable on
   the site* rule with no key left to edit it. `end_marker(template)` now derives it from the one
   box: the literal tail after the last `{live}`, trimmed (`{live} (over)` → *(over)*); a wording
   with no `{live}`, or whose tail still holds a placeholder, keeps `END_MARK_DEFAULT`, which is
   byte-identical to today for a rewrite; a **blank** wording marks nothing. Three tests pin it.
3. **`end_summary` was rewritten, which §A2 did not mention.** It took the mode and the suffix and
   led with the mode word. It now takes the template alone and says what the wording does —
   `edited (appended: "…")` / `edited (rewritten: "…")` / `edited (the sentence as posted, nothing
   added)`. The staff panel's `**stream end**` line is the only caller.
4. **`ended_text` and `end_details` were DELETED**, not just unused. §A names only `ended_render`'s
   `suffix` argument and §A2 only `end_details`' mode report; `ended_text` IS the suffix appender and
   `end_details` can now only ever return `{}`. Checklist 15. `edits_on_end` went the same way.
5. **The migration lives in `GoLive.boot_pass`, not `Database.connect`** (§B left the choice to the
   builder). It has to: the row is `golive.end_wording_migrated` **per guild** and `connect()` has no
   bot and no guilds. It is the first thing each guild's pass does, inside checklist 37's
   `Reconciler` lock. ⚠️ **It reads the `settings` table with raw SQL**, because once the two keys
   leave `KEY_TYPES` the store skips their rows at `load()` and `get`/`stored_values` raise.
6. **`golive_end_mode` was also removed from `api/status.py:NOT_A_FEATURE` and the mock's copy**
   (both now shorter by one); §A2 says only that the status line drops it. A `_mode`-suffixed name
   that is not a key cannot reach `mode_keys()` anyway, so the entry was dead.
7. **`guides_seed.json` told a person to turn `golive_end_mode` to edit.** Not in scope for any
   section, but it is posted copy naming a key that no longer exists; one answer sentence was
   rewritten to *"Black Bloc always edits the post once the stream is over"*.
8. **`page-preview-settings.js` gained `golive_end_template` where the two retired rows were**,
   rather than shrinking the sample `golive` group to three. §C says only that the page loses the
   key; a static preview of the Settings page with no end wording in it demonstrates less.

⚠️ **Not done, deliberately:** `page-golive.js` lines 121–123 hold two ORPHANED string-continuation
statements (`  + '…forgotten, so write it again to go back.';`) left by an earlier build; one of them
names *"the Once the stream is over box above"*. They parse (unary `+` on a string) and ruff/ES-parse
are clean, but they are dead. **Two other agents are editing this file right now** (`spotlight-pings`
and `discord-mock`), so the diff was kept to the Wording card's switch, the suffix references and the
named sentences. Somebody should sweep them.

**KI-26 fired TWICE**, both times a `> file` run of `pytest -n 8`, both times stalling at **87 %**
with the log untouched for five-plus minutes. Killed each time by PID tree, identified by the
`bb-end-wording` on the parent's command line (three agents' suites were running side by side), and
green on the retry in 93 s and 71 s. This build did not touch `KNOWN_ISSUES.md`; the sightings are
reported to the conductor.

## What was NOT verified

⚠️ **NOTHING HERE HAS MET DISCORD.** No stream has started or ended, no announcement has been edited
and no card footer has been seen in a real channel. Every claim about what a post reads is the
suite's, against fakes.

⚠️ **THE MIGRATION HAS NEVER RUN ON THE LIVE DATABASE.** `carry_end_wording` is proved by five unit
tests and three boot-pass tests against a fresh SQLite file. **Nobody has looked at what the live
`settings` table actually holds** — whether any guild has a stored `golive_end_suffix`, a stored
`golive_end_mode`, or a stored `golive_end_template` — so which of the three branches will fire on
the first boot after the deploy is UNKNOWN, and Deviation 1's blast radius depends on exactly that.
Reading it is one `flyctl ssh sftp get` away and was not done.

- **Not merged, not deployed, no key flipped.** `v149` is still live.
- **The browser check was the MOCK, not the live site**, at one width, in one theme, signed in as the
  mock's staff. The Go-live page rendered with the Wording card's *Once the stream has ended* holding
  ONE end-wording box (`{live} — stream ended`) plus the separate author box, **no suffix box and no
  mode switch** — three `<textarea>` on the whole page and one `.switch` (*Playing a game*) — and
  `suffix` / `golive_end_mode` / *When a stream ends* / *left exactly as posted* match **nothing** in
  the rendered text. The only console error was a **pre-existing** 400 on
  `/api/requests?status=pending&per_page=1` (the rail-badge 400 already dispatched at `edf2112`).
- **Nothing was SAVED from the page.** The end-wording box was never edited and no `PUT` was made, so
  the save path and the preview repaint after a save are unexercised outside the suite.
- **The spotlight end path was not seen end to end.** Its test asserts the edited post ends with
  *— stream ended*; nobody has watched a spotlighted channel go offline.
- **`end_marker`'s fallback for a placeholder-bearing tail is a JUDGEMENT, not a measurement.**
  `{live} — {name} is done` marks the card *stream ended* because the footer cannot render a field;
  nobody has decided that is the wording they want.
