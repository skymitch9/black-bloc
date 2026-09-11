# Site restyle — the A/C hybrid (design brief)

> **Audience:** the restyle builder + the owner. **Status:** TRACKED · ✅ **COMPLETE — BOTH
> SLICES ARE LIVE.** R1 `0c49257` deployed 2026-08-31 12:20; **R2 `c334922` deployed
> 2026-08-31 13:14** ("Restyle R2: Black Bloc theme (dark+light, new default, worst contrast
> 4.51), Bangers wordmark+titles, sentence-voice labels (90) + group captions + Overview
> TODAY sentence, table toolbars/tooltip heads/count feet, Cases drawer, Ctrl+K palette,
> Show-keys toggle" — `../deploys.log` line 41; landing entry in
> [`../DONE.md`](../DONE.md), *"2026-08-31 — Restyle R2 live: the site wears Black Bloc"*).
> **Last verified: 2026-09-11 09:35** — docs-wide staleness pass. **FIXED:** the header said
> R2 was "BUILT and awaiting review … not yet deployed"; it had shipped the same afternoon
> and has been live for eleven days. **Re-checked on `main` at `1d090e5`:**
> `site/public/assets/shell.js:7 GROUPS` exists, `site/public/assets/fonts/bangers.woff2` is
> on disk with its OFL file beside it, and `code-notes.md` carries the `# R2 — the restyle
> skin` section at :4008 with its *What R2 did NOT do* foot at :4076. ⚠️ **NOT re-checked:**
> nothing was rendered in a browser, no contrast ratio was re-measured, and the §2–§4 body
> was not re-traced against the CSS that shipped — the deviation notes below are the
> builder's own, not a fresh reading.
> Before that, **2026-08-31 (afternoon)** — ⚠️ the morning draft claimed "nothing
> here has been built yet"; the R1 builder measured otherwise: the top bar (server
> name, health dot, user chip, theme cog), the 4-group rail and the
> settingsEditor/saveBar/humanLabel plumbing had ALL already shipped with the
> 2026-08-27 Direction-A restyle (`666dd8e`). **R1 is now LANDED and LIVE
> (`0c49257`, deployed 2026-08-31 ~12:20):** nav icons, width-filling 2-up grid,
> docked dirty save bar (per-field Save/Clear gone), 90/90 human labels with mono
> key sub-lines, empty-state pass, title cap, plus a cross-theme shell fix (the
> docked bar sat off-screen in 5 of 6 themes — `grid-template-rows` auto vs 1fr).
> R1 deviations worth knowing: Requests sits under Overview and Members under
> Moderation (as shipped 08-27, contrary to §2 — one line in `shell.js:GROUPS` to
> change); labels are short noun phrases (the sentence voice is R2's copy pass).
> **R2 (the skin) is ✅ LIVE** (`a28caef`..`c9d14b7`, deployed as `c334922`
> 2026-08-31 13:14 — this line said "BUILT and awaiting review … not yet deployed" until
> 2026-09-11): the Black Bloc theme dark+light as the default, the wordmark and the
> display-face rule, the copy voice (group captions, all 90 sentence labels, the
> Overview's TODAY sentence), table toolbars/tooltip heads/row-count feet plus a
> Cases detail drawer, the Ctrl K command palette, and the Show keys switch.
> ⚠️ R2 deviations: there are **six** estate themes, not five, so the dropdown
> holds seven; the display face is **Bangers** (already on disk, OFL) rather than
> Bricolage Grotesque, which would have had to be fetched; **Requests gets no
> drawer** — it renders cards, not rows; and four of § 4 C's palette values were
> darkened to clear 4.5:1. Full reasoning in `code-notes.md § R2`.
> Research base: [`dashboard-inspiration.md`](dashboard-inspiration.md) (§ refs below).
> Mock canvas the owner reacted to: https://claude.ai/code/artifact/ad76df70-49f4-4fcd-a66a-07c8969d0ddd

## 1. The owner's decisions (2026-08-31, one at a time, verbatim answers)

| Q | Answer |
|---|---|
| Direction | **"I want a A/C hybrid"** |
| Dark-only or both | **"Both, dark default"** |
| Theme dropdown | **"Keep all 5 themes"** |
| Nav | **"Icons + text"** |

| Command palette | **"Yes, in R2"** — `Ctrl K` jumps to any setting/page/action |
| Raw keys on Settings | **"Show keys toggle"** — hidden by default, a switch reveals the mono key sub-lines, remembered per browser (checklist 33: it's a user-facing toggle) |

All six questions are now decided; nothing in this brief waits on the owner.

## 2. What "A/C hybrid" means here

**A is the skeleton, C is the voice and the warmth.** Concretely:

**From A (Discord-native) — the structure, applied to every theme:**
- Grouped sidebar (13 flat tabs → 4 groups), top bar (server name, bot health
  dot, signed-in user, theme cog), page header = title + one-line description.
- **Docked dirty save bar** replacing per-field Save/Clear (the single biggest
  fix: removes ~96 buttons from Settings). Discard + Save Changes, appears only
  when something is dirty.
- Numbered step panels for compound forms (Take an action), titled checkbox
  rows, tag-chips inside channel/role search fields.
- B's table furniture inside it (per the research recommendation): toolbar row
  (search · filters · export), `—` in empty cells, tooltip headers, per-row
  text actions, right-hand detail drawer for cases/tickets/events.
- Title size capped; display type never inside controls.

**From C (Cookout) — the identity, mostly in the new default theme + copy:**
- A new **"Black Bloc" theme** (warm charcoal ground, ember `#FF7A18` accent,
  flame yellow secondary; dark + light per §4 of the inspiration doc's C
  palette) becomes the **default**. The existing 5 estate themes stay in the
  dropdown unchanged (owner's call) — 6 entries total.
- Wordmark lockup in the rail head; display face (`Bricolage Grotesque` 700,
  OFL, self-hosted) for the wordmark and page titles only, 20–26px, never in a
  control.
- **Copy voice** (theme-independent): group names "Runs the server" /
  "Runs the cookout" / "The desk" (+ "Overview"); sentence labels on settings
  ("Where the bot writes its log" with the raw key as a mono sub-line);
  Overview leads with a TODAY sentence ("Nothing's on fire. 1 warning, …");
  empty states are one line of copy + one action.
- Destructive paths stay cold and plain in every theme: danger tint, typed
  confirmation for bans — warmth never touches the Ban button.

**Nav icons:** one thin outline glyph per item (inline SVG sprite, `1em`,
`currentColor` so all 6 themes inherit) beside the label. Group captions stay
text-only uppercase.

## 3. Constraints that carry over unchanged

- Keep: five-state permission machine, name resolver (never a snowflake),
  in-page sub-nav with counts, collapsible sections, per-table search,
  remembered tab/section state, self-hosted fonts, no framework.
- The `--et-*` token contract is how themes work: **structure ships as page/CSS
  changes, identity ships as a token file.** New tokens (nav icon color, dirty
  bar, drawer, TODAY strip) get defined for all 6 themes, with the 5 estate
  themes receiving derived/neutral values so nothing breaks.
- Every review must check the worst pair: new default dark, new default light,
  plus a spot-check of Cyberpunk dark (the owner's most-used alternate).
  Contrast ≥ 4.5:1 for text roles in the NEW theme both modes (the estate
  themes keep their recorded sub-AA values — not this build's problem).
- Checklist item 33: theme choice, and any new UI behaviors (e.g. "show raw
  keys") are user-facing toggles, not hard-coded.
- `node site/mock/check.mjs` stays green; no route or contract changes are
  expected in this work (front-end + CSS only) — if one becomes necessary,
  stop and say so.

## 4. Build slices (after the B4–B8 builder lands — both touch `site/`)

- **R1 — shell (structure, all themes):** top bar · grouped nav with icons ·
  width-filling 2-up grid over ~1100px · docked dirty save bar on Settings and
  every settings-editor page (per-field Save/Clear removed) · human labels with
  mono key sub-lines · `—`/empty-state pass · title-size cap.
- **R2 — skin (identity):** the Black Bloc theme (dark + light) as default ·
  wordmark + display face · copy voice pass (group names, TODAY sentence,
  empty-state lines) · table toolbar + drawer furniture · mode badges as pills.

Estimated as two multi-layer front-end builds (~250–400k each, Opus). R1 is the
riskier merge (touches every page's chrome); R2 is mostly tokens + copy.

## 5. What this doc does NOT decide

Command palette (owner Q5), raw-key visibility (owner Q6), whether the estate
snapshot file is eventually replaced wholesale (owner said keep all 5 themes —
so no), and the landing/marketing page (C was recommended for it; out of scope).
