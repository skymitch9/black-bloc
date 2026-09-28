# One search module for every list

> **Audience:** the conductor, reviewers and the next build agent. **Status:** TRACKED ·
> 🔨 **BUILT on branch `search-module`** (off `main` at `93c0bbb5`) — **NOT merged, NOT deployed, NOT
> looked at in a browser.** The owner, 2026-09-28 08:4x: *"try and use the same search module everywhere
> for code reusability and stuff"* — now a standing rule.
> **Last verified: 2026-09-28** — in the worktree, on the committed tree (`c9bd673a`): the ES-module
> parse of every `site/public/assets/*.js`; every node fixture `scripts/deploy.ps1` runs exits 0
> (discordmd, labels, clipmd, golive-join, layout, discordmock, marathon-words, mdformat, **listfilter**);
> `node site/mock/check.mjs` against a mock on `MOCK_PORT=8899` → *22 pages, 281 routes, 26 core
> settings, all keys present*; every page script and `ui.js` LINKS under node (no missing named import —
> the check was proved to catch one); a throwaway fake-DOM smoke of `listFilter`/`chipBar` (chips AND
> search, the pressed chip moving, the no-match line, `clear()`, an empty list) passed 12/12. **NOT
> checked:** any page rendered in a browser, at desktop or phone width; Python (untouched — `git diff
> --name-only origin/main` lists no `.py`).

## The API

Two homes, one module: the pure matcher in `site/public/assets/listfilter.js` (no DOM, so
`site/mock/listfilter.test.mjs` pins it under plain node), and the DOM builders next to `searchField` in
`site/public/assets/ui.js`, which also re-exports `matches`, `passes` and `applyFilters`.

| Export | Where | What it does |
|---|---|---|
| `matches(text, query)` | `listfilter.js` | Case-insensitive substring; the query is trimmed; an empty query matches everything. |
| `ruleOf(filters, key)` | `listfilter.js` | The chip's rule; an unknown key falls back to the FIRST chip. |
| `passes(item, {text, filters, filter, query})` | `listfilter.js` | Chip rule AND search. |
| `applyFilters(items, options)` | `listfilter.js` | `{hits: bool[], shown, total}`. |
| `BLOCK_FILTERS`, `blockText(kind)` | `listfilter.js` | The Blocks section's four chips and haystack (folded in from the deleted `blockmatch.js`). |
| `filterChip(label, pressed, onClick, {key, title})` | `ui.js` | The one `button.chip-filter` with `aria-pressed` (and `data-kind` when keyed). |
| `chipBar(choices, current, onPick, {className, role})` | `ui.js` | A `div.chipbar` of single-choice chips from `[key, label, …]`; the pressed chip moves on click, then `onPick(key)`; `.setValue(key)` presses one. |
| `listFilter({...})` | `ui.js` | The search box (built WITH `searchField`) + optional chips over a list, below. |
| `searchField({... , className})` | `ui.js` | Unchanged, plus an optional extra class on the wrapper (Channels uses `review-search`). |

`listFilter` options: `items`, `node(item)` (default `item.node`), `value(item)` (what the rules and
`text` see; default the item), `text(value)`, `filters` (`[[key, label, rule|null], …]` — no filters, no
chips), `filter` / `query` (initial, e.g. a page's remembered state), `label`, `placeholder`, `empty` (a
string → a `sayNothing` line, or a ready node), `chipClass`, `onChange({query, filter, hits, shown,
total})`. It returns `{search, chips, none, parts, state, apply, clear}`: `parts` is `[search, chips]`
for the page to drop into its own `card-head` / `table-tools` row (so every toolbar keeps its extra
buttons and its markup), `apply()` hides non-matching nodes with `hidden`, hides `none` unless the list
is non-empty and nothing matched, and calls `onChange` — which is where each page writes its own count
("Showing N of M", a section count, a foot) and remembers its state. The page calls `apply()` once
after mounting (the marathon schedule deliberately does not: its day folds open from remembered
slots, and the first `apply()` would reset them).

## Which pages moved

| Page / surface | Now |
|---|---|
| Posts ▸ The posts (`postsSection`) | `listFilter` — same fields (title, channel, status words, body), same four chips, same remembered `state.filter`/`state.query`, same foot. |
| Posts ▸ Blocks | `listFilter` with `BLOCK_FILTERS`/`blockText`; same count in the section head, same no-match line, same remembered `blockState`. |
| Posts ▸ New post (scratch / Google Doc) | `chipBar` (`newpost-choice`, `role=group`). |
| Moderation ▸ cases | `listFilter` — same fields, same five chips (kinds lists turned into rules), same foot. |
| Raid trains | `listFilter` for the client-side search; scope chips are a `chipBar` that still refetches. |
| Requests ▸ Your requests | `listFilter` — same chips with their counts, same no-match line with *Clear the filters*. |
| Requests ▸ staff list | Still server-side (`q` + status + assignee go to the API); chips are `filterChip`. |
| Go-live ▸ Streamers | `listFilter` — same fields and six chips, same foot and section count. Preview and log chips: `filterChip`. |
| Events ▸ marathon schedule | `listFilter` over every slot; `onChange` hides empty day folds and opens matching ones exactly as before. |
| Settings ▸ key filter | `listFilter` over every `.setrow`; per-group counts, hiding and opening as before. |
| Channels ▸ Review | `searchField` (class `review-search`) + `matches` inside the page's own `wanted()`; the segment, category select and "keep the row just answered" rule stay page-owned. |
| Members, Logs (every feature page), Audit, Guides, Events log picker | Server-side or re-render filters: chips are `chipBar` / `filterChip`; Members/Logs/Audit keep `searchField` feeding the API. |
| `ui.js` `table()` search, `searchOver` (Automod, Birthdays) | Their row test is `matches` now. |

**Not moved, on purpose:** `palette.js` (the command palette ranks commands and drives the keyboard — not a
list filter); `memberPicker` (a server typeahead); `page-chat.js` / `page-health.js` / `page-channels.js`
`div.chipbar` rows that hold badges and labels, not filter chips. The brief expected own search inputs
in `page-events.js` and `page-guides.js`; measured, they had none — only copied chip markup, now shared.
After this build `class: 'chip-filter'` appears in exactly one file (`ui.js`) and no page sets
`data-search` (Settings rows still carry the one `ui.js` builds).

## Behaviour unified (drift, one pick each)

1. **Channels search debounces.** It was a bare input filtering on every keystroke with no magnifier; it
   is now the shared `searchField` (200 ms debounce, Enter/clear fire at once, the magnifier). Same
   placeholder, label and width (`review-search` still sizes it).
2. **Moderation's box shows its remembered query.** `state.query` survived a page change but the box
   came back empty while still filtering; `listFilter` always seeds the box from state.
3. **No "no match" line on an empty list.** The Blocks section showed *No block matches this filter*
   when there were no blocks at all; every list now shows it only when it has items and none match.
4. **One schedule matcher.** `marathon-words.js` `slotMatches` tested each word; the page matched the
   joined string. Both now use `slotText(run)` + `matches` (a query spanning two fields can match).
5. **Unknown chip key → first chip, everywhere** (Moderation used "no rule", same effect).
6. **Every chip carries `data-kind`** (Guides, Logs, Audit, Events and Go-live chips did not); no CSS
   reads it on chips.
7. Posts: the doc-import note says *the embed box, like the welcome post* instead of naming *Welcome and
   rules* (it went stale on a rename; the payload does not carry the front-door post's name, so not derived).

## Live check steps (not yet run)

Sweep rows `SM-a` … `SM-h` in [`../access/sweeps.md`](../access/sweeps.md). Each page should look as it
did (Channels gains the magnifier) at desktop and 390 px.
