# Posts formatting toolbar — the Word-style bar above the post's text box

> **Audience:** the conductor, reviewers, and the next build that wants a toolbar on another editor.
> **Status:** TRACKED · 🔨 **BUILT on branch `posts-toolbar`** (off `main` `6f829602`), NOT merged, NOT
> deployed. Site only: no Python, no schema, no settings keys. **Last verified: 2026-09-27** — by
> `node site/mock/mdformat.test.mjs` (56 fixtures), `node --test site/mock/*.test.mjs` (25 files, 0 fail),
> `node site/mock/check.mjs` against a mock from the worktree on 8825, the whole Python suite (unchanged,
> 9074 passed), and headless Chrome renders of the Posts editor at 1400 px and 390 px (Bold pressed on a
> selection, preview re-rendered, zero console errors), plus a hand-driven Chrome pass (real mouse click on
> Italic, real Tab / Shift+Tab / Ctrl+B keys, the link dialog typed into and confirmed with Enter).
> ⚠️ **NOT checked:** a true light theme (see *What was NOT verified*), Safari/Firefox, a real phone,
> screen readers, and Discord itself (the toolbar only writes markdown the existing preview already renders).

## The ask (owner, 2026-09-27 20:5x Phoenix, verbatim)

> *"on the post site i like the preview box and stuff. can we add one of those text editor control panels
> to the top of the edit text box? the ones that allow font bold tab italics etc. like word or a standard
> site"*

## As built

A row of buttons sits directly above **The message** box in a post's drawer, with a quiet hint under it:
*Discord formatting — what the preview shows is what Discord shows.* Every button writes Discord markdown
into the box — never HTML, never a rich-text layer — so the existing live preview (and Discord) is the only
renderer.

| Control | Writes | Toggle off when |
|---|---|---|
| **B** Bold (Ctrl/Cmd+B) | `**x**` | the selection is, or sits inside, `**…**` (also inside `***…***`) |
| *I* Italic (Ctrl/Cmd+I) | `*x*` | a run of 1 or 3 stars surrounds / starts-and-ends the selection |
| U Underline (Ctrl/Cmd+U) | `__x__` | wrapped in `__` |
| S Strikethrough | `~~x~~` | wrapped in `~~` |
| **H** Heading ▸ Heading 1 / 2 / 3 | `# ` / `## ` / `### ` at each touched line's start (replaces another level) | every touched line already has that level |
| Bullet list | `- ` per touched line (blank lines skipped) | every touched line starts `- ` |
| Numbered list | `1. `, `2. `, … per touched line | every touched line is numbered |
| Quote | `> ` per touched line | every touched line starts `> ` |
| Inline code | `` `x` `` | wrapped in exactly one backtick |
| Code block | ```` ``` ```` on their own lines around the selection | the selection is, or sits inside, a fence |
| Link | `[text](url)` — the URL asked in the site's own small dialog (`askForm`), `link text` selected when nothing was | the selection already is a `[text](url)` (unlinks without asking) |
| Spoiler | `\|\|x\|\|` | wrapped in `\|\|` |
| Outdent (Shift+Tab) / Indent (Tab) | removes / adds two spaces at each touched line's start | — |

- **Selection**: a button with a caret inserts the pair with the caret between; with a selection it wraps
  it and the same words stay selected. The textarea never loses focus (buttons cancel `mousedown`).
- **Preview**: each press fires the textarea's own `input` event (through `execCommand('insertText')`,
  which also makes **Ctrl+Z** undo a press), so the draft, the pending count and the preview update at once.
- **Tab** stays in the box. **Ctrl+M** toggles Tab back to moving focus until the box loses focus — the
  keyboard user's way out, named in the hint's tooltip.
- **One component**: `formatBar(textarea)` in `ui.js`; the pure moves are `site/public/assets/mdformat.js`;
  `page-posts.js` mounts it once (the page has one multi-line body box). Another editor reuses it with one
  line: `formatBar(itsTextarea)` above the textarea.
- **Looks**: real `<button type="button">`s with `aria-label` and `title` tooltips in a `role="toolbar"`;
  theme tokens only (`--et-*`), sprite glyphs coloured by `currentColor`; `flex-wrap` — one row at desktop
  (487 px wide), two rows at 390 px, document and drawer `scrollWidth` = viewport (no sideways scroll).
- **Words**: button labels, tooltips, the hint and the link dialog's lines are site constants — site words,
  not posted words, so they are not settings keys (the every-word-editable rule covers what the BOT posts).
- **Tests**: `site/mock/mdformat.test.mjs`, 56 fixtures, wired into CI and `scripts/deploy.ps1` beside the
  other node fixtures.

## Deviations

1. **Ctrl+M escape hatch added** (not in the brief). "Tab must NOT leave the box" traps a keyboard-only
   user in the drawer; Ctrl+M is the CodeMirror / VS Code convention. Drop it if the owner prefers.
2. **Line moves keep the user's selection** instead of selecting the whole rewritten block (a selection that
   starts at a line start keeps starting there, so the new prefix lands inside it). Found live: after
   Shift+Tab selected the whole line, the next Ctrl+B bolded the whole line.
3. **Link addresses**: a bare domain (`example.org`) gets `https://`; anything that is not an `http(s)`
   address is refused in words inside the dialog (the preview only draws `http(s)` links).
4. **Nine sprite glyphs added to `icons.js`** (`fmtBullets` … `fmtOutdent`) rather than text/emoji glyphs,
   so the icons follow the theme instead of rendering as colour emoji.
5. The new node test was also wired into `.github/workflows/ci.yml` and `scripts/deploy.ps1`, as every other
   `site/mock/*.test.mjs` is.

## Found, not fixed (pre-existing)

- The preview renderer (`discordmd.js` `links`) parks a masked link's label raw, so `[**bold**](https://…)`
  previews with literal stars while Discord renders the label bold. Not this build's surface; worth a line
  if staff start bolding link text.

## What was NOT verified

- **A true light theme.** The headless pass set `data-theme="light"`, which on this site selects an estate
  theme rather than light mode, so the screenshot was still dark. The CSS uses only `--et-*` tokens, so it
  should follow; not looked at.
- Firefox / Safari (the `execCommand('insertText')` path has a value-write fallback, not exercised), a real
  phone (390 px was an emulated viewport), iOS keyboard shortcuts, screen readers.
- Nothing met Discord; the markdown written is the same markdown the preview and bot already handle.
