# The post editor's paste converter — a Google Doc arrives as Discord markdown

> **Audience:** the build agent and reviewers. **Status:** TRACKED · ✅ **LIVE as v140** — merge `698f33a`, release `413f939`, deployed **2026-09-18 16:38** Phoenix; the `## Deviations` foot is the truth; sweeps **613–615** are the owner's (613 = the first real Google Docs paste); verified: boot clean at 16:38:26 (no front door or ticket button posted this time — both channel keys are blank), /health ready, self-test 116/116, and the live site serves /assets/clipmd.js (200). No real Google Docs paste yet — row 613 is the owner's. Was: TRACKED · 🔨 **BUILT on branch
> `posts-paste`** — off `main` at `0b4e7c4`, **not merged, not deployed, and NOBODY HAS PASTED
> ANYTHING**. A companion to [`posts-design.md`](posts-design.md) (the Posts feature, ✅ LIVE
> v113); it changes no row, no key, no route and no Python.
> **Last verified: 2026-09-18** — the full gate is green in the worktree, on the committed tree:
> `ruff check .` clean; `pytest -q -n 8` **6720 passed / 3 skipped** forward (57 s) and again
> under `BB_REVERSE=1` (61 s); the ES-module parse of all **34** `site/public/assets/*.js`;
> `node site/mock/check.mjs` on `MOCK_PORT=8791` → *20 pages, 186 routes, 24 core settings*
> (the server was stopped and the port confirmed free); `discordmd.test.mjs`, `labels.test.mjs`
> and the new `clipmd.test.mjs` all exit 0.
> ⚠️ **The `BB_REVERSE=1` run hit [`gotchas.md`](gotchas.md)'s xdist hang once** (KI-26, shape 1:
> silent at spawn, no output at all in 10 minutes). Killed by process tree and re-run with
> output to a file, per that entry; **the retry was green in 61 s**, and the same commit is green
> forward. That is the known hang, not a red suite.
> ⚠️ **NOT checked:** no browser has run this code and **no real Google Docs clipboard has ever
> been pasted into the box** — every fixture is a hand-written fragment in the shape Docs is
> documented and observed to emit, not a capture taken from the owner's own document. See
> `## What was NOT verified`.

## The ask, verbatim

Owner, 2026-09-18 16:0x, on the welcome post:

> *"the formatting was lost when copying from google drive"*

Offered a paste converter on the dashboard's post editor; he answered:

> *"2 but do it now"*

## Why this is the SITE editor and can never be the Discord one

`/posts` is the Discord door to the same post (`posts-design.md` §C4), and its edit modal is a
`discord.ui.Modal` with a paragraph `TextInput`. **A Discord modal never sees the clipboard.**
The client hands the bot the finished string on submit; there is no paste event, no
`clipboardData`, no `text/html` flavour and no way to ask for one. Rich formatting is lost in
the client before anything the bot can run exists.

The browser is the only place the rich flavour is reachable: a `paste` event on the textarea
carries `event.clipboardData`, and `getData('text/html')` is the same markup Google Docs writes
to the system clipboard. So the converter lives on the dashboard, beside the preview that
already renders what Discord will draw, and the `/posts` modal is untouched. Staff who need
formatting paste on the site; staff who are typing keep typing anywhere.

## The shape: a string in, a string out — no DOM

`site/public/assets/clipmd.js` exports one function:

```js
htmlToDiscordMarkdown(html: string): string
```

⚠️ **It does not use `DOMParser`, and that is the decision.** The two shapes offered were a DOM
walk (real `DOMParser` in the browser, a hand-rolled node tree in the test) and a
regex-tokeniser the test can feed directly. **The tokeniser was picked**, because it makes the
browser and the gate run *the same code over the same input*: a fake node tree in the test
would have proved the walk and left the parse — the half that actually meets Google's markup —
unproven. It also keeps `site/mock/clipmd.test.mjs` dependency-free, which the gate requires
(`jsdom` is not allowed and there is no `package.json` to hang it on).

The module is three passes:

1. **Tokenise + tree.** A tag regex over the string, comments and doctypes dropped first.
   `script` / `style` / `head` / `noscript` / `iframe` / `svg` / `template` are skipped **with
   their contents** (the scanner jumps past the close tag). A close tag matching nothing open is
   ignored rather than fatal; `<p>`/`<li>` auto-close a sibling of the same name.
2. **Walk into blocks of runs.** Every piece of text becomes a *run* carrying its marks
   (bold / italic / underline / strike / code), the `href` it sits inside, and its font size in
   points. Blocks are paragraphs, headings and list items.
3. **Render.** Adjacent runs with identical marks merge, whitespace is moved outside the marks,
   and each block becomes one line.

## What converts to what

| In the clipboard HTML | Out as Discord markdown |
|---|---|
| `<b>`, `<strong>`, `style="font-weight:700"` (also 600/800/900/`bold`/`bolder`) | `**bold**` |
| `<i>`, `<em>`, `style="font-style:italic"` (also `oblique`) | `*italic*` |
| `<u>`, `<ins>`, `text-decoration:underline` | `__underline__` |
| `<s>`, `<strike>`, `<del>`, `text-decoration:line-through` | `~~strike~~` |
| `<code>`, `<kbd>`, `<samp>`, `<tt>`, `<pre>`, `font-family:…mono/Courier/Consolas…` | `` `code` `` |
| `<h1>` / `<h2>` / `<h3>` | `# ` / `## ` / `### ` |
| `<h4>`–`<h6>` | `### ` (Discord has only three) |
| A `<p>`/`<div>` whose **every** word is ≥20pt / ≥16pt / ≥13.5pt | `# ` / `## ` / `### ` |
| `class="…Title…"` / `…Subtitle…` / `…Heading2…`, `role="heading" aria-level="N"` | `# ` / `## ` / `### ` |
| `<ul><li>` | `- ` |
| `<ol><li>`, honouring `start=` | `1. `, `2. `, … |
| A list nested inside a list item | two spaces of indent per level |
| `<a href="https://…">words</a>` | `[words](https://…)` |
| `<a href="https://…">the same address</a>` | the bare URL |
| `<a href="javascript:…">words</a>` | `words` — the href is dropped |
| `<a>` with no words (an image link) | nothing |
| `<br>` | one newline inside the block |
| `<p>`, `<div>`, `<tr>`, `<blockquote>`, a block boundary | a blank line between blocks |
| `&nbsp;`, `&amp;`, `&#8212;`, `&#x2014;`, … | the character itself |
| `<script>`, `<style>`, `<head>`, `<iframe>`, `<svg>`, `<template>` | dropped **with their contents** |
| `<img>`, `<input>`, `<button>`, `<select>` | dropped |
| colour, alignment, font family, size (below a heading's), margins, table shape | stripped |
| runs of spaces, tabs and newlines | one space |
| three or more newlines, trailing spaces on a line | at most two newlines, no trailing space |

### The four Google-Docs-shaped traps the fixtures pin

1. ⚠️ **Docs wraps the whole selection in `<b style="font-weight:normal" id="docs-internal-guid-…">`.**
   Read the tag and the entire document is bold. **An explicit `font-weight` in the element's own
   style beats the tag** — the same rule makes `<span style="font-weight:700">` bold and
   `font-weight:400` (which Docs puts on ordinary words) not.
2. ⚠️ **Docs styles its own links** `text-decoration:underline; color:#1155cc` on a `<span>`
   *inside* the `<a>`. Taken literally, every pasted link becomes `__[words](url)__`. **Inside an
   anchor the underline mark is forced off** — that underline is the editor drawing a link, not
   the author underlining a word.
3. ⚠️ **Docs wraps each `<li>`'s words in a `<p>`.** A block inside an *empty* list item or
   heading does not start a new block; it fills the one already open. Without this every bullet
   would arrive as a bare paragraph and the list would vanish.
4. ⚠️ **Docs often has no `<h1>` at all** — a heading can be a `<p>` whose span is `font-size:20pt`.
   Both paths are handled, and a block is only promoted when **every** run in it is large, so one
   big word in a sentence is not a heading.

## The editor half

`site/public/assets/page-posts.js`, the body box only:

- A `paste` listener. It reads `text/html`; if that is empty it does **nothing at all** and the
  browser's own plain paste happens (this is the whole of "plain paste is untouched").
- It converts, then compares against `text/plain` trimmed. **If the markdown is the same as the
  plain text, it also does nothing** — there is no formatting to keep, so there is no reason to
  take over the paste or to show a note.
- Otherwise: `preventDefault`, insert at the caret (replacing any selection), re-run the
  existing preview, and show the note. The insert goes through
  `document.execCommand('insertText', …)` — ⚠️ **that is what keeps Ctrl+Z working**, which is
  what the note promises. `setRangeText` is the fallback if `execCommand` is refused.
- The note, under the box, dismissable: *"Pasted with formatting kept (headings, bold, bullets,
  links). Undo with Ctrl+Z."*
- A **Paste keeps formatting** hint beside the **The message** label.

**These words are page constants (`PASTE_HINT` / `PASTE_KEPT` / `PASTE_DISMISS`), not settings
keys, on purpose.** The standing rule (owner, 2026-09-17) is that *every word the bot posts* is
editable on the site. These words are the site talking to staff about the site; Discord never
sees them, and a registry key for each would put three more rows in front of the `/settings`
group select that is already at its 25 cap (`posted-strings-audit.md`).

Nothing else moved: no schema, no settings key, no route, **no Python**. The preview renderer
(`discordmd.js`) is untouched — the converter's output is ordinary markdown and the existing
preview draws it.

## Deviations — 2026-09-18, branch `posts-paste`

1. **No `DOMParser`, anywhere.** The brief offered it with a test-side fake; the
   regex-tokeniser shape was taken instead so the browser and the gate run one code path over
   one input. Reasoning under *The shape*.
2. **`<h4>`–`<h6>` become `### `** rather than being stripped to paragraphs. Discord has three
   heading levels; flattening a sixth-level heading into body text loses more than clamping it.
3. **A heading's bold mark is dropped.** Docs headings are usually bold, and `# **Rules**` would
   draw asterisks in Discord — a heading is already bold there. Bold *inside* a paragraph is
   untouched.
4. **`<blockquote>` is a paragraph, not `> `.** The brief's list does not name quotes, and Docs
   emits `<blockquote>` for indentation as often as for quotation; a wrongly-quoted paragraph is
   more visible damage than a lost indent. `discordmd.js` renders `> ` if staff type it.
5. **`<pre>` keeps its newlines but does not get a fenced block.** Its runs are backticked as
   monospace, per the brief's "`<code>`/monospace → backticks".
6. **A blank line is put between a `<ul>` and an `<ol>` that touch** (and between two lists of
   different kinds), so Discord starts a second list rather than continuing the first. Two lists
   of the *same* kind separated only by a block boundary still merge into one.
7. **Markdown characters in the pasted words are NOT escaped.** A document containing a literal
   `*` or `_` can produce markdown Discord reads as emphasis. Escaping would have made the
   "plain fragment comes back unchanged" contract false, and the preview beside the box shows
   exactly what Discord will draw, so the staffer sees it before pressing anything.
8. **A link whose text is empty is dropped, not rendered as its bare href.** Its only content
   was an image, and images are stripped; emitting a URL where the doc showed a picture would
   add something the author never wrote.
9. **Tables lose their shape.** A `<tr>` is a paragraph and each cell is separated by a space.
   Discord has no table markdown; a pipe grid would be worse than a sentence.
10. **`clipmd.test.mjs` was also added to `.github/workflows/ci.yml`**, not only to
    `scripts/deploy.ps1`. The other two node fixture files' headers already claim both runners,
    and leaving CI out would have made that claim false for the third.
11. **`site/public/assets/site.css` gained four rules** (`.postboxlabel`, `.pastehint`,
    `.pastenote`). `.postboxhead` is `justify-content: space-between`, so adding the hint as a
    third child would have pushed the counter into the middle; the label and the hint are
    wrapped in one span instead.

## What was NOT verified

- 🔴 **No browser has pasted a real Google Docs clipboard into this box.** Not once. Every
  fixture in `site/mock/clipmd.test.mjs` is hand-written markup in the shape Docs is known to
  emit — the `docs-internal-guid` wrapper, `font-weight:400` on body words, the underlined link
  span, the `<p>` inside each `<li>`. **A real clipboard may carry shapes none of them contain**,
  and the four traps above are the ones anticipated, not the ones measured. Sweep row **`PP-a`**
  is the row that turns this from a claim into a fact.
- **No browser has run `page-posts.js` at all** on this branch: the paste listener, the caret
  insert, the note and the hint are unexercised. In particular **`document.execCommand('insertText')`
  has not been observed to keep Ctrl+Z working here** — it is the documented behaviour and the
  reason it was chosen over `setRangeText`, not something this branch measured (sweep `PP-c`).
- **Nothing met Discord.** No post was made, updated or previewed in a channel; the guard and
  `TEST_MODE` were never in the picture, because nothing in this branch reaches Discord.
- **No CSS was rendered.** The four new rules were written against the existing
  `.postboxhead` / `.postcol` rules by reading them, not by looking at a page.
- **The heading thresholds (20pt / 16pt / 13.5pt) are library knowledge, not measurement.** They
  are keyed to Docs' 11pt body default; a document written at a different base size may promote
  or fail to promote a heading.
- **`site/mock/check.mjs` was run on a spare port (`MOCK_PORT=8791`)**, not the gate's 8788,
  because another session was holding a mock on the default. It reported *20 pages, 186 routes,
  24 core settings*; the server was stopped and the port confirmed free. ⚠️ **Nothing in this
  branch touches the contract** — no route, no page, no key — so a green `check.mjs` says only
  that nothing was broken, not that anything new was proved.
- The **CI job** was edited but not run — GitHub has not executed the new `Paste converter` step.

## Sweeps

[`../access/sweeps.md`](../access/sweeps.md) rows **`PP-a`** (a formatted Google Doc pasted into
the post body arrives as markdown and the preview draws it), **`PP-b`** (a plain-text paste is
unchanged and no note appears) and **`PP-c`** (Ctrl+Z puts the box back).
