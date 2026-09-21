# The Discord mock — every editable posted text shows staff exactly what Discord will draw

> **Audience:** the build agent and reviewers. **Status:** TRACKED · ✅ **BUILT (Opus, 2026-09-20 20:2x, branch `discord-mock` off `main` `be78bff`) — not merged, not deployed; see `## Deviations` (14) and `## What was NOT verified`.** Was: 📐 DESIGN (Fable, 2026-09-20 20:0x), dispatched
> at the 20:50 session reset. **Last verified: 2026-09-20 20:0x** against
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
section and the posts editor with the console read — say what you saw. Docs: `code-notes.md`; this doc's `## Deviations

*(the build agent writes here what it had to do differently, dated)*

**2026-09-20, branch `discord-mock`, off `main` `be78bff` (v149 live).** Thirteen, in the order
they would surprise a reader of the body.

1. ⚠️ **`GET /api/golive/preview` IS NOW UNREAD AND WAS NOT DELETED.** §A says it "stays for one
   release and is retired when `page-golive.js` no longer reads it" — that day is today: the only
   reader (`wordingPreview`, the Wording card) is gone. It was kept anyway because the **sibling
   `end-wording` build is editing `preview_payload` in the same file right now** (`golive_end_suffix`
   comes out of it), and deleting a function another branch is rewriting turns a merge into a
   conflict for no gain in this release. **What to delete when `end-wording` has landed:**
   `black_bloc/api/tools/golive.py` — `preview_payload`, the `@router.get("/preview")` handler,
   `PREVIEW_STREAM` / `PREVIEW_DURATION` / `PREVIEW_SOURCE` and the now-unused imports
   (`author_line`, `embed_footer`, `ended_author`, `ended_footer`, `ended_render`, `render`,
   `StreamInfo`, `TWITCH`, `display_name`); the `/api/golive/preview` route in
   `site/mock/server.mjs` with `PREVIEW_SAMPLE`'s golive-only use; its row in
   `site/mock/contract.json`; and the eight call sites in `tests/api/tools/test_golive.py`. Its
   `read_by` in the contract already says out loud that nothing reads it.
2. **The renderers are SYNC, not `async`.** §A writes `async (bot, guild, overrides, sample)`. Not
   one renderer touches the database, the network or Discord — they read the settings store's
   in-memory cache and build `discord.Embed`s — so `async` would have promised I/O that never
   happens. `POST /api/preview/message` is async, which is where FastAPI wants it.
3. **A renderer is handed a `PreviewStore`, not the raw `overrides` dict.** Same effect, one
   difference that matters: the overlay is built ONCE, in `preview.render`, so no renderer can
   forget to apply it or apply it to the wrong key. Two renderers (`rehearsal`, `minutes_notes`)
   call functions that take a `bot` and read `bot.store` themselves; they get a `PreviewBot`, which
   is the real bot with `.store` swapped.
4. **Fifteen renderers, and the list is not quite §A's.** Built: `golive_live`, `golive_ended`,
   `golive_costream`, `spotlight_bump`, `frontdoor`, `ticket_button`, `rehearsal`, `request_filed`,
   `request_card`, `event_card`, `modmail_relay`, `post`, `birthday`, `poll_card`, `minutes_notes`.
   §A's `…` is filled by `rehearsal` (the `rehearsal_note` line every shadow copy carries) and
   `minutes_notes` (`minutes_start_text` + `minutes_notes_title`). Nothing on §A's list is missing.
5. ⚠️ **The mock is drawn under a settings ROW, which is why §C4 and §C5 are one change.**
   `ui.js:settingRow` draws it under any `text`/`longtext` key whose feature has a renderer. Every
   settings surface on the site ends at that row — the Settings page, `settingsPanel`, the Go-live
   page's drawers, `namespaceSettings` — so the Settings page and "the feature pages' own text
   fields" were the same job. **Nineteen of 292 rows get one** (measured in the browser), and the
   other 273 show nothing at all rather than a fake.
6. ⚠️ **A row's mock is LAZY.** 292 rows on the Settings page × one request each at load is not a
   page, it is an outage. It draws itself the first time it is scrolled to (`IntersectionObserver`,
   with a paint-immediately fallback where the API is missing) and repaints on input after that.
   Measured: one mock drawn on arrival at `settings.html`, five after the modmail group was opened.
7. **There is no costream card on the Go-live page.** §C1 asks for three editors in *The
   announcement*. `golive_costream_template` / `_author` are placed by `golive-join.js:WORDING_KEYS`,
   which the **sibling `end-wording` build is rewriting** (it removes two keys and the join
   fixture's count). Moving them would have conflicted with it, and putting a second editor on the
   page while the drawer still holds one is two surfaces for one fact. They keep their single home
   in *Everything else*, where deviation 5 now gives them the mock anyway. The
   `golive_costream` renderer and its contract row exist and are tested; only the card is deferred.
8. **The Wording card is gone, not turned into two mocks.** §C1 says it "becomes two mocks". Each
   editor now carries the real message directly under it, so a second card showing the same two
   messages would have been the duplicate-surface bug the docs standard names. `drawCard`,
   `botLine`, `withRoleNames` and `wordingPreview` went with it, and `page-golive.js` no longer
   imports `discordmd.js`.
9. **`discordmock.js` exports a TREE and a mounter, not just a node.** `messageTree` is pure and
   imports only `discordmd.js`, because `site/mock/discordmock.test.mjs` runs under plain node and
   `ui.js` cannot be imported there at all (`document is not defined` at module scope).
   `mountTree(spec, make)` takes the element factory, and `ui.js:discordMessage` is the two-line
   binding that passes `el`. So the CSP rule holds — every colour goes through the CSSOM — without
   the component importing the DOM library.
10. **The platform owns the sample URL.** The chips send `{platform}` and nothing else; `url` and
    `source` are derived (`preview.platform_facts`, mirrored as `server.mjs:previewStreamFacts`).
    They were sample keys at first, and the headless render showed *Preview as YouTube* changing the
    word while leaving `twitch.tv` in the sentence and a Twitch-purple bar on the card. No test
    caught that; the browser did.
11. **`SAMPLE_LIMIT` is 4000, not a short clamp.** The posts editor sends the whole draft body as
    the sample, and Discord's own caps are 2000 / 4096.
12. **`site/mock/server.mjs` renders the previews itself** rather than proxying: it is a lower
    environment with no bot in it. It answers the same shape from the same keys, and the contract
    row is what stops the two halves drifting. ⚠️ Its wording is CLOSE but not identical to the
    bot's (its `fillWording` is not Python's `format_map`, its poll bars are a fixed string), so a
    difference seen on `127.0.0.1` is not evidence about the deployed bot.
13. **The Birthdays page's *What a birthday wish looks like* card became the mock.** It held a
    `templateEditor` `paint:` line — the wording filled in as plain text. With deviation 5 the row
    above it would also have carried a mock, so the card was about to show the same fact twice; it
    now holds `made.mock.node` and nothing else. **Tempvoice's `tempvoice_name_template` card was
    left exactly as it is** and is the counter-example the rule needs: a spawned channel's NAME is
    not a message the bot posts, so it has no renderer and gets no mock — which is `DM-d`.
14. **`page-golive.js` lost two orphaned string fragments** that `cb59eca` left behind when it
    removed the end-mode button — two `+ '…'` continuation lines with nothing to continue. They
    parsed and did nothing.

⚠️ **One test of this build's own was FLAKY and is fixed.** `test_the_live_announcement_is_the_bot_s_own_render_and_not_a_copy` compared the renderer's embed against a second `announcement_embed` call, and `announcement_embed` stamps `datetime.now(UTC)` — so it failed once, on the reverse-order run after the `posts-page` merge, on a **half-millisecond** difference in `timestamp` and nothing else. It now compares everything BUT the stamp and asserts separately that a stamp is there. It passed four full runs before it failed, which is exactly how a time-dependent assertion behaves.

**KI-26 fired once, sighting count +1.** The `BB_REVERSE=1` `pytest -n 8` stalled at **94 %** with
the log untouched for eight minutes and a single worker left alive; killed by its own tree
(identified by `bb-discord-mock` in the command line, with two other agents' suites running beside
it) and green in **85 s** on the retry. This build did not touch `KNOWN_ISSUES.md`.

## What was NOT verified

⚠️ **NOTHING HERE HAS MET DISCORD.** The mock is a drawing of a payload the bot built; whether that
drawing matches what Discord actually puts on the screen is the one thing a mock can never prove
about itself. **Sweep row `DM-b` — post one for real and read the two side by side — is the only
evidence that will ever exist**, and until somebody walks it, every "true to Discord" claim in this
document is a reading of Discord's CSS by a model, not a measurement.

- **Not merged, not deployed, no key flipped.** Nothing ran against the live bot or the live
  database; `GET /api/preview/features` and `POST /api/preview/message` have never answered a real
  browser signed in to `blackbloc.heygabi.ai`.
- **The browser work was done against `site/mock/server.mjs`, not the real API.** The mock answers
  the same shape by construction (the contract row holds both halves to it) but not the same words.
  The Python renderers were exercised only by `pytest`.
- **Seen in `chrome-headless-shell` 149.0.7827.22 at 1280 px and 390 px** (mock on `127.0.0.1:8791`):
  `golive.html` (two mocks, caption, avatar, name, **BOT** tag, *Today at 8:21 PM*, the content with
  its markdown, the 4 px `rgb(145,70,255)` Twitch bar, the author line, the title, the **Game** field
  and the footer; typing in the wording box changed the sentence; *Preview as YouTube* turned the bar
  `rgb(255,0,0)` and the address to `youtube.com`), `posts.html#welcome` (the pane is the mock, and
  typing `**world**` came back bold), `settings.html` (19 mock rows of 292, `frontdoor_title` has one,
  `chat_simple_model` and `staff_channel_id` have none, one drawn on arrival and five after a group
  was opened, and typing changed the embed title). **No horizontal overflow at 390 px on any of the
  three** (`scrollWidth === clientWidth === 390`, and nothing inside a `.dcmock` reached past 391 px).
- ⚠️ **The console carries one error on every page and it is NOT this build's:**
  `GET /api/requests?status=pending&per_page=1` → **400**, the rail badge, already on the
  conductor's small-fixes list. Nothing else was logged, and no exception was thrown.
- ⚠️ **The pages were read as a DOM, not LOOKED AT.** Class names, computed positions and inline
  colours were measured; **no screenshot was taken and no human eye has seen the mock**. Whether it
  reads as Discord rather than as a dark box is unjudged.
- **Only three of the fifteen renderers were seen in a browser** (`golive_live`, `golive_ended`,
  `post`, plus `frontdoor` under a settings row). The other eleven are proved by
  `tests/test_preview.py` and the node fixtures alone; nobody has looked at `event_card`,
  `request_card`, `modmail_relay`, `poll_card`, `birthday`, `minutes_notes`, `spotlight_bump`,
  `rehearsal`, `request_filed`, `ticket_button` or `golive_costream` on a page.
- **The image and thumbnail placeholders have never been drawn with a real URL.** The go-live card
  only carries art when Twitch or YouTube gave it some, and no sample does; the placeholder is proved
  by the node fixture, not by a page.
- **The `link` button style has never appeared on a page** — no renderer emits one yet (the
  requests card's *Open it on the site* needs an `origin` the preview does not pass). It is proved by
  the node fixture.
- **Nobody has typed into a mock on a phone**, and no touch target was pressed; 390 px was an
  emulated viewport, not a device.
- **The `end-wording` sibling has not landed**, so `golive_ended` was exercised against today's
  `ended_render` (which still takes a `suffix` argument with a default). The renderer never passes
  one and never names `golive_end_suffix` or `golive_end_mode`, so it should survive that build
  untouched — but the two have not been merged together and that is an expectation, not a result.
- ✅ **`posts-page` WAS merged in** (`origin/posts-page` was pushed while this build ran; §C2 and the
  brief allow that one merge). The posts wiring was re-applied by hand on top of the rebuilt page:
  three conflicts, resolved as **theirs for the page, mine for the renderer** — the editor's mock is
  named `mock` because the rebuilt page has a module-level `shown`, `PREVIEW_EVERY_MS` went with the
  local debounce, and the Versions view is their inline `versionView` panel rather than the drawer
  the design named. ⚠️ **The merged page was NOT re-rendered in the browser** — it parses, the node
  tests and `check.mjs` are green against it, and `renderPreview` is gone from the file, but nobody
  has opened the rebuilt Posts page with the mock in it. That is the one thing this build finished
  without seeing.
- **No `TODO.md` / `DONE.md` / `deploys.log` / `KNOWN_ISSUES.md` edit** — those are the conductor's.
