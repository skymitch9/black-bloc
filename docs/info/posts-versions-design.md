# Posts — version history instead of "Put the original back"

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **DESIGN (Fable, 2026-09-20 18:2x) — dispatch
> when the conductor says** (independent of `spotlight`; touches `posts.py`, its cog, its routes, its page and the
> schema). **Last verified: 2026-09-20 18:2x** against `main` `84157d1` (v147 deploying): `black_bloc/posts.py` —
> `save_post` `:665` (*"the one write both doors make"*), `publish_post` `:840` (posts the ROW's body — it never reads
> a draft), `reset_post` + `PUT_THE_ORIGINAL_BACK` `:178` / `:588` (what this design removes), `render_message` `:350`;
> `api/tools/posts.py` — `PUT /{slug}` `:213` (save), `POST /{slug}/publish` `:226`, `POST /{slug}/reset` `:234`;
> `site/public/assets/page-posts.js` — the move buttons `:443`, the reset button `:446–455`, `WILL_POST` `:47`;
> `cogs/community/posts.py` — the **Put the original back** button `:358`; `storage/db.py:795` the `posts` table
> (`posted_hash`, `seed_hash`, `updated_at/by`); `logkinds.py` `post.reset` `:478`, `post.saved` `:479`.
> Schema is **47** on `main`; `spotlight` takes **48**; this build takes **the next free number at dispatch** and says which.

## The ask, verbatim (owner, 2026-09-20 18:1x)

*"for all post lets remove the put back original and add a version history so you can view and swap to any previous
saved post. Don't so snapshots only save a post once save changes has been pushed or post it has been pushed. post it
should also trigger save changes if it doesnt"*

Three sentences, three rules: (1) **Put the original back** goes; (2) a **version** is written only by a press of
**Save changes** or **Post it** — never an autosave, never a snapshot of a draft; (3) **Post it** with unsaved edits saves
first, then posts, so what went out is always a version.

## A. The model

Table **`post_versions`**: `id, guild_id, post_id, n` (1, 2, 3 … per post), `title, body, style, channel_id, pin`
(the five fields `save_post` owns — a version is the whole post, not a diff), `saved_at, saved_by, via, because`
(`saved` · `posted` · `restored:<n>` · `backfill`), `UNIQUE (post_id, n)`. Append-only: nothing ever updates or deletes
a version except the keep-limit trim (§D). The `posts` row stays the working copy; `seed_hash` stays (the Settings
card still says *shipped with the bot*) but nothing restores from it any more.

**When a version is written — the whole rule, in `posts.py`, one function `record_version(db, row, actor, via,
because)`:**

| Door | Writes a version when |
|---|---|
| `save_post` (both doors: the site's **Save changes**, the Discord modal's submit) | the five fields differ from the LATEST version (or there is none). A save that changes nothing writes nothing and says so as today |
| `publish_post` | the row differs from the latest version at the moment of posting (covers a post whose row was edited before this shipped, and any path that wrote the row without a version) — `because: posted`. Otherwise nothing: the latest version IS what went out |
| **Use this version** (§C) | always — it is a save of that version's five fields, `because: restored:<n>`, so history never loses the step |
| the migration | ONE `backfill` version per existing post from its current row, so every post has a version 1 and *View* never meets an empty list |

**Rule 3 on the site:** the page's **Post it** with a dirty editor first calls `PUT /{slug}` with the draft, and only on
`ok` calls `/publish`; the outcome sentence under the button says both (*"Saves your changes, then posts to #welcome as
plain text"*). The Discord panel has no draft (the modal saves on submit), so nothing changes there. **`publish_post`
itself is not changed** — the site does the save, the server still posts the row.

## B. What goes

`reset_post`, `PUT_THE_ORIGINAL_BACK`, `original_of` / whatever `:588` names, `POST /{slug}/reset` (contract row + mock
route + test), the page button `:446–455`, the Discord button `:358`, the `post.reset` kind (kept in `logkinds` only
if old rows exist — check the live Logs page; if any `post.reset` row exists keep the kind and its label so history
renders, else remove it). The `ux-audit.md` row for posts and the posts preview (`page-preview-posts.js`) lose the
button too (one line each).

## C. Doors — site first, Discord small

**Site (`page-posts.js`, the post's editor).** A **Versions** foldout under the editor (`foldout('Versions', …, {count})`,
shut on arrival): one row per version, newest first — `n`, when (`ago`), who, `because` as a chip (*saved* / *posted* /
*restored from 3* / *shipped*), the title if it changed, and a one-line body summary (first 80 characters, one line).
Two buttons per row: **View** opens the version in the existing drawer (`openDrawer`) rendered by `render_message` as
the editor's own preview renders — read-only; **Use this version** confirms (`ask()`: *"Replace the current text with
version 3 from 2 days ago? Your current text stays in the history as version 5."*), then `POST
/api/posts/{slug}/versions/{n}/restore`, which answers the row and the new version; the editor reloads. The current
version's row says *current* and has no Use button. The preview page (`page-preview-posts.js`) gets the same foldout
with static rows so the owner's walk sees it.

**Discord (`cogs/community/posts.py`).** The post card gains one button **Versions…** → a sub-panel: the last 25 as a
select (`v5 · 2 days ago · saved by Sky`), then **View** (ephemeral, the rendered message) and **Use this version**
(confirm → the same `restore` function). Nothing a member can press; staff-gated as the rest of the panel.

**Routes** (`api/tools/posts.py`, contract, mock, `test_contract.py`): `GET /api/posts/{slug}/versions` (list, newest
first, `n, saved_at, saved_by, saved_by_name, via, because, title, summary, current`), `GET /api/posts/{slug}/versions/{n}`
(the full five fields + rendered preview), `POST /api/posts/{slug}/versions/{n}/restore`. Refusals in words: no such
version; restoring the current version (*"Version 5 is already what the post says."*).

## D. Keys — two, prefix `posts_`, group posts

`posts_versions_keep` (int, **0** = keep every version, else 1–500: the oldest beyond N are trimmed after each write,
never version 1's `backfill` row while it is the only one; help says why 0 is the default: *"history is cheap, a lost
version is not"*), `posts_versions_summary_chars` (int, 80, 20–300 — the one-line summary length on the list). Mock
rows + labels. Every posted word is unchanged; panel and page words are constants.

## E. Logging

`post.saved` gains `version: n` in details; `post.posted` too; new kind `post.restored` (IMPORTANT — a staff move that
changes what members read) with `from_version`, `new_version`; `post.versions_trimmed` (routine) when the keep limit
drops rows. Health/Logs chips unchanged (feature `posts`).

## F. Tests, docs, gate

`tests/test_posts.py` (a save that changes something writes a version and one that changes nothing does not; publish
writes `posted` only when the row differs from the latest; restore writes `restored:n` and returns the new n; the
trim keeps N and never the only row; backfill gives every existing post version 1), `tests/api/tools/test_posts.py`
(the three routes + staff gate + the two refusals; `/reset` is GONE — a test asserts 404/405), `tests/cogs/community/
test_posts.py` (the Versions sub-panel; no Put-the-original-back button), `tests/api/test_contract.py`, `tests/storage/
test_db.py` (the version pin), the key and kind count guards, `site/mock/check.mjs` (routes), and the page's node tests
if any touch it. Both `pytest -n 8` orders, `ruff`, ES parse, `check.mjs`, the four node tests, env cleared (the
`config.py` names — see `access/deploy.md`). ⚠️ KI-26 (thirteen sightings): kill by process tree only; read the log,
not the exit code. Docs: `code-notes.md`; this doc's `## Deviations` + `## What was NOT verified`; `architecture.md`
(schema, keys, kinds, routes); `docs/info/README.md`; `posts-design.md` one dated line (put-back retired → versions);
`ux-audit.md` posts row one line; `sweeps.md` rows `PV-a…` (a: Save changes twice with a change → Versions shows 2 and
3 with who/when; b: Save with no change → no new version, the page says nothing changed; c: edit, then Post it without
saving → one new version AND the post goes out with the edit; d: Use this version 2 → the post's text is version 2's
and the list shows a new version *restored from 2*; e: `/posts` ▸ the card ▸ Versions… ▸ pick one ▸ View shows it;
f: the old Put the original back is gone on both doors). NOT `TODO.md` / `DONE.md` / `deploys.log` / `KNOWN_ISSUES.md`.
⚠️ Migrate before deploy — the table and the backfill run in `Database.connect`; the backfill is idempotent (skips
posts that already have a version).

## Deviations

*(the build agent writes here what it had to do differently, dated)*
