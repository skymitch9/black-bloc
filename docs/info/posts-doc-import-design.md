# Import a post from a Google Doc link

> **Audience:** the conductor, reviewers and the next build agent. **Status:** TRACKED ·
> 🔨 **BUILT on branch `posts-doc-import`** (off `main` at `05a8fc0c`) — **NOT merged, NOT deployed, and
> NO REAL GOOGLE EXPORT HAS EVER BEEN FETCHED.** A companion to
> [`posts-paste-design.md`](posts-paste-design.md) (the paste converter this reuses) and
> [`posts-design.md`](posts-design.md) (the Posts feature).
> **Last verified: 2026-09-28** — the gate, in the worktree, on the committed tree: `ruff check .` clean;
> `pytest -q -n 16` **9571 passed, 0 failed** (96 s); every node fixture `scripts/deploy.ps1` runs
> exits 0 (discordmd, labels, clipmd, golive-join, layout, discordmock, marathon-words, mdformat); the
> ES-module parse of all **47** `site/public/assets/*.js`; `node site/mock/check.mjs` against a mock on
> `MOCK_PORT=8891` → *22 pages, 280 routes, 26 core settings, all keys present* (the listener on 8891
> was stopped and the port confirmed free).
> ⚠️ **NOT checked:** no browser ran the drawer; no request left this machine for Google; the export's
> shape in `site/mock/clipmd.test.mjs` is hand-built. See `## What was NOT verified`.

## The ask, verbatim

Owner, 2026-09-28:

> *"Can we make a formal feature for the Google Drive link importer for posts? That way we can handle
> converting a post into the correct format based on a Google Drive shared linked as long as it's
> public"*

## As built

### The site (the post drawer, `site/public/assets/page-posts.js`)

- Under the message box, a folded **Import from a Google Doc** (closed by default — the owner's
  "less chrome, the obvious action visible, the rest folded"). Open, it is one row — a link box and
  **Import** (Enter in the box presses it) — one help line, and a notice for the answer.
- **Import** with an empty box says so in words and asks nothing of the server.
- If the message box already has words, the page's own dialog (`ask()`, the same one Delete and Use
  version use — never the browser's `confirm()`) asks *Replace the message with the doc?* first.
  Cancel changes nothing and fetches nothing.
- The server answers the export's HTML; **the page converts it with `clipmd.js`** — the same
  `htmlToDiscordMarkdown` the paste path runs — and the markdown REPLACES the box as an **unsaved draft**:
  the editor's own dirty state (*N changes pending*, **Discard**, the preview, the counter) follows,
  because the write goes through the same `insertText` path a paste does (so Ctrl+Z also reaches it).
- A note under the box: *Imported from "<title>" — the box is an unsaved draft. Nothing is saved or
  posted until you press Save Changes or Post it.* with **Put back what was there** (restores the box
  exactly as it was before the import, as an edit — also unsaved) and **Dismiss**.
- Over the style's cap: the note adds *It runs past this style's limit, so the counter is red and Save
  refuses until it is shorter* — the counter and Save's refusal are the editor's existing warning; the
  import adds no second mechanism.
- A doc that converts to nothing leaves the box untouched and says so.
- Save hides the note (the draft is saved); Discard hides it too.

### The route (`black_bloc/api/tools/posts.py`)

`POST /api/posts/import-doc` `{url, slug?}` → `{html, title, doc_id, bytes, message}`. Gated exactly like
the other posts writes (`_editor`: staff + the write bucket, guild, database). `slug` is only logged.

### The fetch (`black_bloc/doc_import.py`)

| Case | Status · `error` | Words (module constants) |
|---|---|---|
| empty link | 400 · `no_link` | `NO_LINK` |
| not a docs/drive link, or an id that is not `[A-Za-z0-9_-]{20,}` | 400 · `not_a_google_doc_link` | `NOT_A_GOOGLE_LINK` |
| redirect to `accounts.google.com`, a 401/403, or a sign-in page answered 200 | 409 · `doc_not_public` | `DOC_NOT_PUBLIC` — *Share → General access → Anyone with the link → Viewer* |
| 404/410 on a **docs** link | 404 · `doc_not_found` | `DOC_NOT_FOUND` |
| 404/410 on a **drive** link, or an answer that is not `text/html` | 422 · `not_a_google_doc` | `NOT_A_DOC` — only Google Docs convert; *File → Save as Google Docs* |
| body over 2 MB (header or read) | 413 · `doc_too_big` | `DOC_TOO_BIG` |
| no answer within the deadline | 504 · `doc_timeout` | `DOC_TIMEOUT` — *a problem reaching Google, not the doc's sharing* |
| transport error, 5xx/429/other status, redirect loop (> 5 hops), redirect with no Location | 502 · `doc_unreachable` | `DOC_UNREACHABLE` — same *not the sharing* clause |
| a hop to any host but the two allowed | 502 · `doc_redirect_refused` | `DOC_WENT_ELSEWHERE` |

⚠️ **An outage is never labelled as access** (owner rule): every fetch failure is 5xx and says *not a
problem with the doc's sharing*; none is 401/403 (the site reads those as *your* permission).
`tests/test_doc_import.py::test_a_fetch_failure_is_a_fetch_problem_never_an_access_problem` pins it.

### The SSRF guard

1. **The link staff paste is never fetched.** `parse_link` pulls only the id (strict regex, host must be
   exactly `docs.google.com` — `/document[/u/N]/d/<id>` — or `drive.google.com` — `/file[/u/N]/d/<id>`,
   `/open?id=`, `/uc?id=`; no port, no userinfo, http(s) only), and `export_url` builds
   `https://docs.google.com/document/d/{id}/export?format=html` itself, re-checking the id.
2. **Redirects are followed by hand.** `aiohttp_hop` does one GET with `allow_redirects=False`; `_walk`
   joins each `Location` and, BEFORE any request, refuses a hop unless it is `https`, port 443 or none, no
   userinfo, and the host is exactly `docs.google.com` or ends in `.googleusercontent.com`.
   `accounts.google.com` is checked first and answers *not public*; every other host is refused unfetched.
3. **One deadline for the whole walk** (`asyncio.timeout`) and a per-request `ClientTimeout`; the body
   is read in chunks to one byte past 2 MB and no further.

Proved by `tests/test_doc_import.py::test_a_redirect_off_google_docs_is_never_fetched` — seven targets
(`evil.example`, `docs.google.com.evil.example`, plain-`http` docs, a look-alike content host, a
non-443 port, the `169.254.169.254` metadata address, `drive.google.com`) each answer
`doc_redirect_refused` with the fake transport having been asked for **only the export URL**. The route
half is `tests/api/tools/test_posts.py::test_a_redirect_off_google_is_a_fetch_problem_in_words`, and
`test_the_fetch_asks_for_the_export_it_built_never_the_link_it_was_given` proves step 1.

### The converter learns the export (`site/public/assets/clipmd.js`)

- **Marks by class.** The export writes `<style>….c3{font-weight:700}…</style>` and `class="c1 c13"`
  on spans. `classRules` reads every `<style>` block for **single-class selectors only** (`.c3`, not
  `p.c3`, not `.lst-kix_… > li:before`), keeping the six properties the walk already understands; for an
  element, its classes' rules apply **in stylesheet order** (the CSS cascade for equal specificity), then
  the inline `style` on top. The inline path (the clipboard) is unchanged.
- **Links unwrapped.** `https://www.google.com/url?q=<real>&sa=…` becomes `<real>` when `<real>` is a
  linkable address; a wrapper hiding anything else (`javascript:`) keeps the wrapper. The paste path
  gets this too.
- **List depth from the class.** The export never nests lists: a sub-bullet is a sibling
  `<ul class="lst-kix_<id>-1">`. Depth is `nesting + N` from that suffix; numbering comes from `start=`,
  which is how the export resumes a list after a nested bullet.
- **A list of the other kind one level in no longer gets a blank line** (`1. One` / `  - sub` /
  `2. Two`) — for both paths; the blank line between two top-level lists of different kinds stays.
- `<head>` (and its `<title>`) was already dropped with its contents; the fixture proves it.
- Fixtures: `EXPORT_DOCS` is the paste fixture's document in the export's shape and must convert to
  the SAME markdown (`one document, pasted and exported`); `EXPORT_MORE` pins title/subtitle
  paragraphs, h2/h3, class marks with a later rule winning, `<br>`, empty paragraphs, a percent-encoded
  wrapped link, the `javascript:` wrapper, and `start="3"` after a nested bullet. With the class
  resolution switched off the first fixture fails (checked by hand while building).

### Log

One `web.post.imported` row per successful import (`note()`; details `slug`, `doc_id`, `bytes`, `via` —
never the doc's text), classified ROUTINE (`logkinds.py`). Refusals log nothing — the posts API's own
refusals (`refused()`) log nothing either — and fetch problems leave a Python `log.info` line.

### Words

Every word here is shown **only to staff on the site**. Following the Posts module's convention
(`posts.py` `BLOCK_*`, `api/tools/posts.py` `POSTS_ARE_OFF`), the server's sentences are module
constants in `doc_import.py` and the drawer's are page constants in `page-posts.js` (`IMPORT_*`), not
settings keys: the standing rule is *every word the bot POSTS is editable*, and Discord never sees these.
The mock copies the server's sentences, like every other mock route.

## Deviations

1. **Site only — there is no Discord door.** A Discord modal cannot run `clipmd.js`, and a second
   converter in Python would give the export two homes. `/posts` is untouched.
2. **The deadline is 8 s, not 10 s.** The page's own `api()` aborts at 10 s and would show its generic
   outage sentence; 8 s lets the server's *Google did not answer* sentence arrive first.
3. **The route answers `doc_id`, `bytes` and `message` beside `{html, title}`** — the page uses `title`
   and `html`; the other three cost nothing and let the contract pin the shape.
4. **The route takes an optional `slug`** for the log row, so the row says which post was being edited.
   It is not checked against the posts table (an import changes no row).
5. **404 is split by where the link came from**: a Drive link's 404 says *not a Google Doc* (the
   likelier cause for an uploaded .docx/PDF), a Docs link's says *no doc there*. Google may answer
   either way for either; see NOT verified.
6. **Undo is a button and Ctrl+Z.** The replace goes through `insertText`, so the browser's undo also
   reaches it; **Put back what was there** is the explicit one-press undo the brief asked for.
7. **`tests/conftest.py` refuses a real fetch in every test** (`no_test_ever_opens_a_link` now also
   patches `doc_import.aiohttp_hop` with a `pytest.fail`), and `tests/api/test_contract.py` cans the
   contract entry's one fetch.
8. **Published-to-web links** (`/document/d/e/2PACX-…/pub`) are refused as *not a Google Docs link* —
   their id is not the document id and the export endpoint does not take it.

## What was NOT verified

- 🔴 **No real Google export was ever fetched.** Every HTML shape in `clipmd.test.mjs` and every Google
  answer in `tests/test_doc_import.py` is hand-built from what the export is known to emit; the real
  export may carry classes, list shapes or wrappers none of them contain.
- **What Google actually answers** for a private doc (assumed: 302 to `accounts.google.com`, sometimes
  401/403), for a Drive-uploaded .docx/PDF/Sheet id (assumed: 404 or non-HTML), and whether the export
  redirects to `*.googleusercontent.com` at all — each is handled, none is measured.
- **The sign-in-page sniff** (`<form` plus an `accounts.google.com/…signin` address in a 200 answer) is
  a guess at a belt-and-braces case.
- **No browser ran the drawer**: the fold, the dialog, the note, Put back, Ctrl+Z after an import, and
  the CSS at 390 px are unexercised.
- **`aiohttp_hop` never opened a socket** — its tests run it over a fake `ClientSession`.
- Nothing met Discord; nothing here can.

## Live check steps (for the conductor, after a deploy)

Sweep rows **`DI-a` … `DI-e`** in [`../access/sweeps.md`](../access/sweeps.md): one PUBLIC doc
(Anyone with the link → Viewer), one PRIVATE doc (Restricted), one non-Doc Drive file (an uploaded .docx
or PDF), a non-Google link, and Put back.

## Follow-up: the embed box and New post choices

> 🔨 **BUILT on branch `posts-doc-import-2`** (off `main` at `d1d5807a`) — **NOT merged, NOT deployed,
> and still NO real Google export has ever been fetched.** Last verified: 2026-09-28 — see the gate
> figures in the branch report; nothing below was seen in a browser.

The owner, 2026-09-28 08:3x, verbatim:

> *"Make sure it post in a format style box like welcome does"*
> *"Also on make new post have a start from scratch or import drive link options"*

"Format style box" is the **embed** style (`posts.EMBED`, 4096 characters) that the shipped *Welcome and
rules* post uses.

### As built

- **`posts_import_style`** — a new registry key (enum `plain | embed`, default **`embed`**), filed under
  `posts` by prefix, with help, a mock row and a label. It is on the Posts page's **Settings** fold
  (`SETTING_KEYS`, which now lists five keys) and reachable from `/settings` like every posts key
  (checklist 33). `posts.import_style(store, guild_id)` is the one reading; an unknown value reads as the
  embed. The choices are a tuple in `settings_store.py` (it cannot import `posts.py` — `posts` →
  `actionlog` → `settings_store` is a cycle); `tests/test_posts.py::test_the_import_style_choices_are_the_post_styles`
  pins them equal to `posts.STYLES`.
- **Every posts payload says it**: `GET /api/posts` and every post-shaped answer (`_whole`) carry
  `import_style`, so both drawers know it without reading settings.
- **Import into an existing post** (the post drawer): after a successful import the UNSAVED draft's style
  also switches to `import_style` when it differs, the style select follows, and the note adds *The style
  is set to the embed box, like Welcome and rules too — also unsaved.* (`BOX_WORDS` / `IMPORT_RESTYLED`,
  page constants — staff chrome). The cap check (*runs past this style's limit*) uses the NEW style.
  **Put back what was there** restores the previous body AND style. Discard already reset both.
- **New post** opens with two chips — **Start from scratch** (selected; today's title → **Create the
  post**, unchanged) and **Import a Google Doc**: a link box with **Read the doc** (Enter presses it) and
  a title box. Reading calls `POST /api/posts/import-doc` `{url}` (no slug — there is no post yet),
  converts with `markdownOfDoc` — the drawer's own call of `clipmd.js`'s `htmlToDiscordMarkdown`, now one
  page function both drawers use — fills the title with the doc's title unless staff typed their own, and
  only then shows **Create the post**. That press sends `POST /api/posts` `{title, body, style:
  import_style}` — ONE call — and opens the new post's drawer. Nothing is posted to Discord.
- **Refusals in words, nothing created**: empty link, not a Google link, not public, not a Doc, fetch
  problems (the route's own sentences); a doc that converts to nothing; a doc longer than the import
  style's cap (*"X" is N characters and an embed holds 4,096, so nothing was made…*); a link edited after
  it was read (*press Read the doc again*); no title; a taken slug (the server's sentence).
- **`make_post` can bear words** (`body=`, `style=`): the title and body are checked against the chosen
  style's caps BEFORE anything is written (`body_too_long` 400, nothing made); the row is created with
  its body and style; a non-empty body is written as **version 1** through `record_version`
  (`because=saved`, the way Save does); and the ONE log row is still `post.created` / `web.post.created`,
  now with `style` and `version` in its details (checklist 34 — one write, one row). With no body the
  function behaves exactly as before (plain, empty, no version).
- Mock mirrors all of it (`postImportStyle`, `import_style` on both shapes, `POST /api/posts` with
  `body`/`style`, the cap refusal, version 1). Contract: `import_style` required on `GET /api/posts`,
  `GET /api/posts/{post_slug}`, `POST /api/posts`; a second `POST /api/posts` entry born with a body
  and `style: embed`.
- CSS: `.newpost-choice`, `.newpost-pane` (a column, `min-width: 0`); the link row reuses `.docimport`,
  which wraps.

### Deviations

1. **Two presses on the import path, not one** — *Read the doc* then *Create the post*. The brief's title
   box "fills with the doc's own title once fetched and stays editable", which needs a moment between the
   fetch and the create; the read also lets the over-cap refusal land before anything exists.
2. **The client sends the style**; the server does not default a born body to `posts_import_style`. A
   body with no `style` is born plain, like every other post. The page always sends `import_style`.
3. **The import logs `web.post.imported` with no slug** on the New post path (the post does not exist
   yet); the create's `web.post.created` row names it a moment later.
4. **The note names "Welcome and rules"** in `BOX_WORDS.embed`, as the brief worded it — a page constant,
   so a renamed welcome post leaves it stale.
5. **A doc title longer than 256 characters** is put in the title box as is; Create is then refused by
   the server in words (the title cap). Not clipped silently.

### What was NOT verified

- 🔴 **No browser ran either drawer** — the chips, the hidden panes, focus moving, the note's new
  sentence, Put back restoring the style select, and the 390 px layout are reasoned, not seen.
- **No real Google export** (unchanged from the first build).
- The mock path was exercised by hand with curl (born post: style embed, version count 1; a 2001-character
  plain body refused and nothing made) and the mock's canned export was converted by `clipmd.js` in node
  (190 characters); the page code that joins those was not run.
- Nothing met Discord.

### Live check steps

Sweep rows **`DI-f` … `DI-i`** in [`../access/sweeps.md`](../access/sweeps.md).
