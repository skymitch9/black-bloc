# The Discord mock — every editable posted text shows staff exactly what Discord will draw

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **DESIGN (Fable, 2026-09-20 20:0x) — dispatches
> at the 20:50 session reset** (three builds are in flight and the session pool is at 67 %; the owner's rule is that an
> ask IS the go, and this one is only queued by budget, not by decision). **Last verified: 2026-09-20 20:0x** against
> `main` `cb59eca` (v149 live): the go-live wording previews are `discordmd.renderPreview` embed boxes (`page-golive.js:drawCard`,
> v149 — markdown in a box, NOT Discord's chrome); the posts editor previews with the same renderer
> (`page-posts.js:343`); the guides carry REAL screenshots (`guides-design.md` §C4) and no renderer; `GET /api/golive/preview`
> (`api/tools/golive.py:214`) answers `text` / `author` / `footer` strings, not the embed the bot sends. The bot's own render
> functions: `golive.announcement_embed` `:218` + `render` `:423`, `posts.render_message` `:393` (a dict already),
> `frontdoor.door_embed` `:169`, `events.card_for` `:1301` + `card_buttons` `:2638`, `requests.request_embed` `:813` +
> `card_buttons` `:540`, `modmail.relay_embed` `:182` / `header_embed` `:212`, `birthdays.render_description` `:255` +
> `card_lines` `:509`, `polls` (its card builder — find it), `spotlight` reuses go-live's. `ui.js:templateEditor` `:1330`
> (the wording editor with a `paint(filled)` hook) and `settingRow` `:1019` (every Settings-page control).

## The ask, verbatim (owner, 2026-09-20 19:5x)

*"i thought we talked about having a discord like mock similar to what we have in guides to display how the wording will
look for go live? in fact we should do that for all editable text boxes. I want the staff to see a true to discord
rendering when they change text around similar to our guides screenshots and mocks."*

Two halves: **true to Discord** (the chrome Discord draws — avatar, name, BOT tag, time, the embed's colour bar, author
line, title, description, fields, footer, the button row, mention pills) and **as they change text** (live, from the draft,
before Save). And "all editable text boxes": every settings key of type `text` / `longtext` whose words the bot posts.

## A. One source of truth: the bot renders, the site draws

**`black_bloc/preview.py`** — a registry `RENDERERS: dict[str, Renderer]` keyed by feature (`golive_live`, `golive_ended`,
`golive_costream`, `spotlight_bump`, `frontdoor`, `ticket_button`, `post`, `event_card`, `request_card`, `request_filed`,
`modmail_relay`, `birthday`, `poll_card`, …). A renderer is `async (bot, guild, overrides: dict[str, str], sample: dict)
-> Rendered` where `Rendered` is the exact thing the bot would send: `{content: str, embeds: [Embed.to_dict()],
components: [[{label, style, emoji, disabled}]], mentions: {roles: [...], channels: [...]}}`. `overrides` is the draft:
the settings keys the editor holds, applied through a **`PreviewStore`** overlay (`store.get` answers the override for
those keys and the real store for everything else — no write, ever). `sample` is the feature's sample facts (the
go-live `SAMPLES`, a seeded post, a made-up event) — each renderer owns its defaults and the site may pass a platform.
Every renderer CALLS the existing function (`announcement_embed`, `door_embed`, `request_embed`, …) — never a copy — so
the mock cannot drift from the post. ⚠️ Checklist 15: one canonical implementation.

**Route** `POST /api/preview/message` `{feature, overrides?, sample?}` → `Rendered` (staff; refused in words for an
unknown feature; overrides limited to keys the feature's renderer declares — `Renderer.keys` — so nobody previews a key
into a post it does not belong to). Mock route + contract row + `test_contract.py` (one fixture per feature). The old
`GET /api/golive/preview` stays for one release and is retired when `page-golive.js` no longer reads it (say which in
Deviations).

## B. The component — `site/public/assets/discordmock.js`

`discordMessage(rendered, {bot, when})` returns a node that looks like Discord's dark theme, pixel-honest where it
matters: the message row (avatar 40 px round, the bot's display name in its role colour, the **BOT** tag, *Today at 8:03 PM*
in the viewer's locale), the content through `discordmd.renderDiscord` (mention pills for roles `<@&id>` and channels
`<#id>` resolved by name — the refs already exist in `page-golive.js:withRoleNames` and `ui.js:channelLabel`), each embed
as Discord draws it (4 px colour bar from `color`, author line with icon, title (linked when `url`), description,
fields in Discord's inline grid, image / thumbnail as a placeholder box with the URL's file name, footer text + icon +
timestamp), and the components as Discord's button rows (`primary` blurple, `secondary` grey, `success` green, `danger`
red, `link` with the ↗ mark). Discord's palette is its own token set (`--dc-bg`, `--dc-text`, …) so the mock is dark whatever
the site's theme, with a thin frame and the caption *How Discord will show it*. Attachments and stickers are out of scope.
CSS in `site.css` under one heading. Pure and testable: `site/mock/discordmock.test.mjs` renders three fixtures (a plain
message with a role mention, a go-live embed, a request card with buttons) through jsdom-free DOM stubs the other node
tests use, or through `vm` + a tiny element shim — the builder picks and wires it into `deploy.ps1` + CI.

## C. Where it is wired — first the two the owner named, then every text box

1. **Go-live ▸ The announcement** (`page-golive.js`): the live wording, the end wording and the costream wording each get
   a `discordMessage` under the editor, re-rendered on input (debounced 250 ms) from `POST /api/preview/message` with
   the draft as `overrides`; the *Preview as Twitch / YouTube* chips set `sample.platform`. `drawCard` and the
   `renderPreview` boxes go. The Wording card's *While live* / *After the stream* list becomes two mocks.
2. **Posts** (`page-posts.js` — coordinate with the `posts-page` build if it is still open; if it has landed, edit the
   new page): the editor's preview pane becomes `discordMessage` for the `post` feature (plain or embed style), the
   Versions **View** drawer too.
3. **`ui.js:templateEditor`** gains `preview: {feature, sample}`: when given, it mounts the mock itself and re-renders
   on input — so every page that uses `templateEditor` gets the mock by adding two fields.
4. **The Settings page** (`page-settings.js`): every `text` / `longtext` key whose namespace maps to a renderer
   (`RENDERERS[feature].keys` includes the key; the route `GET /api/preview/features` answers the map) shows **How Discord
   will show it** under the control, live as they type; keys with no renderer show nothing (never a fake).
5. **Feature pages' own text fields** that are not `templateEditor` (the front door's card on Modmail, the request
   filed line on Requests, birthdays' wording, polls' card wording): the same call, one line each. The builder lists
   which pages got it and which did not, with why.

**Guides are unchanged** — their screenshots stay real captures; this mock is for text being edited.

## D. Keys — none new. Every word stays where it is; this only shows it.

## E. Tests, docs, gate

`tests/test_preview.py` (each renderer calls the real function — assert the embed dict equals the one the bot's own
path builds for the same store; overrides reach the render and never the store; an unknown key is refused; an unknown
feature answers in words), `tests/api/test_preview.py` (the route + staff gate), `tests/api/test_contract.py`,
`site/mock/discordmock.test.mjs`, the ES parse, `check.mjs`. A headless-browser render of the go-live announcement
section and the posts editor with the console read — say what you saw. Docs: `code-notes.md`; this doc's `## Deviations`
+ `## What was NOT verified`; `architecture.md` (routes); `docs/info/README.md`; `golive-page-design.md` one dated line;
`sweeps.md` rows `DM-a…` (a: type in the go-live announcement box → the mock changes as you type and looks like Discord;
b: post it for real → the Discord message and the mock match line for line; c: the Settings page ▸ a text key ▸ the mock
under it; d: a key with no renderer shows nothing). NOT `TODO.md` / `DONE.md` / `deploys.log` / `KNOWN_ISSUES.md`.
⚠️ The one thing a mock cannot prove is Discord itself — row b is the proof, and the design's honesty depends on it.

## Deviations

*(the build agent writes here what it had to do differently, dated)*
