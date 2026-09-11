# Dashboard feature audit — displays vs controls (2026-08-27)

> **Audience:** Claude sessions and the owner. **Status:** TRACKED (owner,
> 2026-08-31 — was local-only until then).
> Last verified: **2026-09-11 09:30** — docs-wide staleness pass. ⚠️ **This is a RESEARCH
> RECORD of a 2026-08-27 audit, not a current picture of the site.** Two weeks and ~60
> releases separate it from `main` at `1d090e5`, and the whole panels program (17 features,
> one command each) plus the Direction-A restyle landed in between. What was re-checked
> today is ONLY that the **20 repo paths it cites still exist** — they all do, including
> `black_bloc/cogs/community/role_menus.py` and `black_bloc/api/settings_api.py`, which it
> names by bare filename. ⚠️ **NOT re-checked and presumed stale:** every `file:line`
> anchor, every A/B/C ranking, and whether any listed defect is still present — the
> `[object Object]` finding included. Nothing was executed or rendered, then or now; the
> site has **17 pages / 150 routes** today. Read this for the OWNER'S INSTRUCTION and the
> displays-vs-controls rule, not for the state of a page.
> Before that, **2026-08-27** (STATUS line only re-checked 2026-08-31) — a READ-ONLY code audit of `site/public` at `666dd8e` by an
> Opus agent; nothing was executed or rendered. The `[object Object]` finding was a
> high-confidence code read, not a measurement — one browser load confirms it. The
> concurrent themes+Members build may already have moved some `file:line` anchors.

Owner's instruction, verbatim: *"on the website, in the go-live area, can we update the
annoucement wording to be a changable text field instead of just a display. also audit all
the site features. we dont want any displays showing what the bot can do, we want ways to
interact and change."*

Legend: **C** control · **D** data the bot reports (fine) · **X** display with no way to act.

## 0. Read first

- ✅ **Done 2026-08-27 in `8adb4ab`.** 🔴 **BUG — Automod has two dead controls.** `settingRow()` (`ui.js:703`) returns a plain
  object, not a node, and has no save path; `page-automod.js:95` and `:119` append it
  straight into a section body → renders `[object Object]`, saves nothing. Only
  `page-settings.js:95` unwraps `.node` inside a `settingsEditor`. Not in KNOWN_ISSUES.
- ✅ **Done 2026-08-27 in `72368d7`.** **The owner's item.** `golive_template` is the only wording key in the golive namespace and
  IS editable — but only as an unlabelled text box inside the generic Settings accordion
  (`page-golive.js:102`), while the section titled "Announcement wording" (`:94`) is a
  read-only preview card "What an announcement looks like" (`:30`).

## 1. Per-page inventory (X items only; C/D omitted where complete)

| Page | X / gap | Where | Replacement |
|---|---|---|---|
| Overview — **Done 2026-08-27 in `316ad38`** | **Features** card: mode pills + `MODE_NOTE` prose, no way to act | `page-overview.js:65-91`, `:16-22` | three-segment mode control per feature writing `<feature>_mode` (A3); drop the prose (C4) |
| Health — **Done 2026-08-27 in `4a71cef`** | **Features** section: read-only mode badges, third copy of the same fact | `page-health.js:54-63`, `:110-112` | remove (C1); Health keeps gateway, loops, last-50 |
| Moderation — **Done 2026-08-27 in `316ad38`** | aside mode pills read-only; `untimeout` route exists with no control | `page-moderation.js:51-67`, `:26` | switches (A4); add `untimeout` to `KINDS` (A5) |
| Automod — **Done 2026-08-27 in `8adb4ab`** | Mode + Exemptions sections broken (above) | `page-automod.js:90-96`, `:116-120` | one `settingsEditor` (A2); then one home for those keys (C3) |
| Go-live — **Done 2026-08-27 in `72368d7`, `eb2a10b`** | Opt-outs pure list; no "link a member"; wording card read-only; `END_SUFFIX` hardcoded | `page-golive.js:69-72`, `:50-67`, `:28-34`, `golive.py:15` | B1, B2, A1, B9 |
| Birthdays — **Done 2026-08-27 in `eb2a10b`, `ce7774a`** | "Wished" column read-only badge; template has no preview | `page-birthdays.js:107`, `:151` | B3, A6 |
| Temp voice — **A7 done 2026-08-27 in `ce7774a`; B4 still open** | **Open now** list with no actions | `page-tempvoice.js:28-33` | B4 (needs refactor: `do_rename/limit/privacy` take an Interaction) ; name preview (A7) |
| Role menus — **A8 done 2026-08-27 in `ce7774a`; B5–B7 still open** | no settings section; no un-post; no seed; no staff assign | `page-rolemenus.js:277`, `:152-177` | A8, B5, B6, B7 |
| Events — **still open (B8)** | detail fields fetched but never shown; nothing edits an event | `page-events.js:90-99` | B8 (lower priority) |
| Settings — **Done 2026-08-27 in `4a71cef`** | 3-sentence intro prose | `page-settings.js:104-107` | cut to one line |

Complete controls confirmed (write path + refusal in words): Moderation actions/apply,
Automod rules, Honeypot ban/setup/settings, Modmail reply/close/snippets/blocks/settings,
Events decide/settings, Go-live unlink/settings, Birthdays set/import/remove/settings,
Temp voice setup/settings, Role menus switch/menus/post/editor, Settings (the reference
implementation: `settingsEditor` + docked `saveBar`).

## 2. Ranked changes

> **Done 2026-08-27** on branch `worktree-agent-a722f5273a3373659` (off `188acf3`):
> **A1** `72368d7` · **A2** `8adb4ab` · **A3** `316ad38` · **A4** `316ad38` ·
> **A5** `316ad38` · **A6** `ce7774a` · **A7** `ce7774a` · **A8** `ce7774a` ·
> **B1** `eb2a10b` · **B2** `eb2a10b` · **B3** `eb2a10b` · **B9** `72368d7`
> (key added only — `golive.py:ended_text` must still be made to read it) ·
> **C1** `4a71cef` · **C2** `72368d7` · **C3** `8adb4ab` · **C4** `316ad38` ·
> **§4 prose** `4a71cef` and `dab62c8`.
> **Still open: B4** (temp-voice per-room actions, needs the Interaction
> refactor), **B5–B7** (role-menu un-post, seed, staff assign), **B8** (event
> detail/edit).
>
> Two live defects the audit did not carry, fixed in the same run: assets were
> served stale after every deploy (`adfb5e7`) and the CSP blocked Discord
> avatars (`18b313e`).

**(A) display → control, write path exists (front-end only)**
A1 Go-live wording editor (§3) · A2 fix Automod dead controls (**first — live bug**) ·
A3 Overview Features → mode switchers · A4 Moderation aside pills → switches ·
A5 `untimeout` in the action bar · A6 birthday template preview · A7 temp-voice name
preview · A8 Role menus settings section incl. `role_menu_channel_id`.

**(B) needs a new route** — B1 `POST/DELETE /api/golive/optouts` (`set_optout`/`clear_optout`,
`cogs/content/golive.py:123,130`) · B2 `POST /api/golive/links` (`clean_login`, `link_owner`,
`set_link`; reuse `LINK_TAKEN`) · B3 `POST /api/birthdays/{id}/optin` (`set_opted_in`,
`cogs/community/birthdays.py:132`) · B4 temp-voice per-room actions (refactor first) ·
B5 `POST /api/rolemenus/{name}/unpost` (`clear_message`, `role_menus.py:400`) ·
B6 `POST /api/rolemenus/seed` (`seed_default_menus`, `:408`) · B7 staff assign for
`staff`-mode menus (`:850`, `:447`) · B8 event detail/edit · **B9 `golive_end_suffix`
setting key** (replaces the hardcoded `END_SUFFIX`, `golive.py:15`; inherits the whole
write path for free).

**(C) remove — the control lives elsewhere** — C1 Health Features section · C2 duplicate
`golive_template` row in the golive accordion (needs an `omit` option on
`namespaceSettings`, `ui.js:871`) · C3 Automod: one home for mode/exemptions, not two ·
C4 Overview `MODE_NOTE` prose.

## 3. A1 — the Go-live wording editor, in full

1. In the "Announcement wording" section build `settingsEditor([templateSpec])`
   (`ui.js:807`); append `rows[0].node`, the preview, then `editor.bar` → CHANGED mark,
   Discard, docked Save, per-row refusal (`ui.js:844-848`), clear-to-default (`:834-837`):
   the Settings page's exact path (`page-settings.js:88,102`).
2. `golive_template` is typed `"text"` → single-line input (`ui.js:654-659`). Add a
   `"longtext"` type (or special-case the key) rendering the existing `input area`
   textarea (`ui.js:647`).
3. Live preview from the one `SAMPLE` table (`page-golive.js:21-26`), repainted on the
   `input`/`change` events `settingRow` binds (`ui.js:743-744`), from the control's
   current text.
4. Preview fidelity: prepend the resolved `golive_ping_role_id` role like `render()` does
   (`golive.py:126-127`); show `GAME_FALLBACK` "something" for an empty game (a "no
   category" sample toggle); unknown tokens survive literally and an unformattable
   template falls back to the default (`:119-125`) — say so instead of pretending.
5. Save = `saveSetting('golive_template')` → `PUT /api/settings/golive_template`
   (`api.js:148` → `settings_api.py:159-177`), audited as `web.settings.set`.
6. Then C2. Sibling wording keys: none in golive besides the template; the stream-ended
   wording is B9. Wording keys elsewhere for a consistent pass: `birthday_template`,
   `tempvoice_name_template`, `tempvoice_creator_name`, `bot_bio`, `status_prefix`.

## 4. Prose longer than one sentence — cut or drop

Drop: `page-golive.js:31` (A1 replaces), `page-overview.js:16-22` (C4),
`page-health.js:60` (C1). Cut to one line: `page-automod.js:91-93`,
`page-rolemenus.js:26-28` (`SWITCH_HELP`), `page-moderation.js:305`, `page-events.js:103`,
`page-birthdays.js:84` (keep the second sentence), `page-tempvoice.js:36`,
`page-audit.js:74-75`, `page-settings.js:104-107` → "Emptying a row puts it back to its
default." Keep: confirm-dialog bodies (`page-moderation.js:222`, `page-birthdays.js:69-73`),
outcome sentences (`page-rolemenus.js:29-32`), `page-honeypot.js:82`, and the loop
liveness caveat `page-health.js:74`.

## 5. Not determined

Nothing executed; `GET /api/mod/parity` in `phase8b-design.md` is a stale doc line (route
gone with the Carl parity removal), not a gap; B4's refactor size unestimated;
`permission-ux.js` not read line-by-line.
