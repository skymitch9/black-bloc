# Go-live, once the stream is over — the announcement rewritten in the past tense

> **Audience:** the build agent and reviewers. **Status:** TRACKED · ✅ **LIVE as v117** — merge `65f0931`, release `7d5d6ad`, deployed **2026-09-17 09:53** Phoenix; `golive_end_mode` = edit since then; the `## Deviations` foot is the truth where it departs from the body; sweeps **449–457** are the owner's; KI-28 for the blank-from-Discord gap. Was: 📐 DESIGN, dispatching to Opus as branch `golive-end`. **Last verified: 2026-09-17 08:4x** against `main` `fb1600b`: `black_bloc/golive.py`
> (`render`, `ended_text`, `ended_embed`, `author_line`, `end_summary`), `black_bloc/cogs/content/golive.py`
> (`_end_live`, `_mark_ended`, `_ended_embed`, lines ~750–806), the `golive_sessions` table
> (`storage/db.py:134–147`), the live keys read off the dashboard, and both wordings rendered with the server's
> own template through the real functions. ⚠️ Secret NAMES only.

## Owner asks, verbatim (2026-09-17, 08:3x–08:4x)

*"For the golive channel, can we update the message of a stream once it's over / So it's past tense indicating
its ended? Make this editable of course / Show me our current message and what it could look like after the stream
has ended"* → shown both → *"Do a, we have time so let's make sure we do it right."* Also, same minute: *"Let's not tag
a role when a stream goes live. We'll end up tagging the related fan group but not yet."* (that is a settings flip,
`golive_ping_role_id` blank — not part of this build, but §C says what the edit does with a mention prefix).

## What exists today (measured)

| Piece | Today |
|---|---|
| `golive_end_mode` | enum `off` \| `edit`, live **off**. `edit` → `_mark_ended` fetches the announcement and edits it |
| `golive_end_suffix` | text, ` — stream ended`. `ended_text` appends it to the content; `ended_footer` puts `· stream ended` on the card's footer |
| The card's author line | `author_line(name, platform, ended=True)` → *"Sky was live on Twitch"* — the verb `ENDED_VERB` is a **constant** |
| The sentence | stays present tense: *"**Sky** is currently streaming **Celeste**! You can check it out: <url> — stream ended"* |
| The mention prefix | `render` prepends `ping_prefix(ping_role_id, fan_role_id)`; the edit keeps the content's prefix text (Discord does not re-ping on edit, but the `@Events` stays visible) |
| Duration | `golive_sessions.started_at` / `ended_at` exist; nothing renders a length |
| Guard | an edit in a real channel is refused under `TEST_MODE`; `_mark_ended` already catches and logs (`go-live: could not mark message …`). With `golive_mode` shadow nothing is announced, so nothing is edited |

## A. Keys (registry + mock contract; every one reachable from the Settings page and `/settings set-value`)

| Key | Kind | Default | Help (registry voice) |
|---|---|---|---|
| `golive_end_template` | text | `**{name}** was streaming **{game}** — the stream has ended. {url}` | the whole announcement once the stream is over; `{name} {game} {title} {url} {platform} {duration}`; blank keeps the live sentence and appends `golive_end_suffix` as before |
| `golive_end_author` | text | `{name} was live on {platform}` | the card's top line once the stream is over; `{name} {platform} {duration}`; blank keeps *"was live on"* |
| `golive_end_keep_mention` | bool | **false** | true keeps the role mention at the front of the edited announcement; false drops it — nobody is pinged by an edit either way |
| `golive_end_suffix` | (exists) | ` — stream ended` | unchanged: the footer marker, and the appended tail when `golive_end_template` is blank |
| `golive_end_mode` | (exists) | off | unchanged. ⚠️ Do NOT flip it in the build — the owner flips it on the Settings page after the deploy |

`{duration}` is humanised from `started_at` → `ended_at`: `2 h 10 min`, `48 min`, `under a minute`; when either stamp
is missing it renders as an empty string and any doubled space is collapsed (the template must never show `()` or
`for `). `{title}` blank → empty, `{game}` blank → `something` (as `render` does), `{platform}` blank → empty and
the author line's `on ` is dropped (as `author_line` does today).

## B. Rendering — one home, `black_bloc/golive.py`

- `ended_render(template, info_or_row, name, *, duration, mention_prefix, keep_mention) -> str`: `format_map` with
  the same forgiving `_Fields` as `render` (an unknown placeholder or a bad template logs a warning and falls back to
  `ended_text(live_content, suffix)` — never a raise, never `****`). When `template` is blank → `ended_text` as today.
  The mention prefix (`<@&…> ` at the very front of the existing content) is stripped unless `keep_mention`.
- `ended_embed(...)` takes an `author` template; blank → today's `author_line(..., ended=True)`.
- `end_summary(...)` for the staff panel's **stream end** line says which of the three shapes is in force: `off
  (left as posted)` / `edit (rewritten: "<first 40 chars of template>")` / `edit (suffix " — stream ended")`.
- The cog's `_mark_ended` reads the three keys and the session row (it already has `row` with `started_at`; make sure
  `ended_at` is read after `end_session` wrote it, or pass `now_iso()` through) and edits content + embed in ONE
  `message.edit` as today. `allowed_mentions` stays `self._mentions(...)` (nothing re-pings).
- `GET /api/golive/preview` (staff, same dependency as the other go-live routes in `black_bloc/api/tools/golive.py`)
  returns `{live: {text, author}, ended: {text, author, footer}}` rendered from the guild's saved keys with a fixed
  sample (`name` = the caller's display name, game `Celeste`, title `Any% attempts`, url `https://twitch.tv/…`,
  platform `Twitch`, duration `2 h 10 min`) — through the REAL functions, so the page never carries a second
  renderer. Mock contract row for the route; `check.mjs` must pass.

## C. The site — `golive.html` gains a **Wording** card

Under the existing go-live settings on the Go-live page: the two renderings from `/api/golive/preview` shown as
Discord-ish text (the page already has a style for a bot line — reuse it), refreshed after any of the go-live keys
saves (the page's settings rows fire a save event — hook the refresh on it, do not poll). Read-only for members;
staff see it beside the editable keys. Review link the agent puts in its report:
`https://blackbloc.heygabi.ai/golive.html` (the mock: `node site/mock/server.mjs` → `/golive.html`).

## D. Tests (mirror the package)

`tests/test_golive.py`: `ended_render` with the default template (the exact expected string), blank template →
suffix behaviour, `{duration}` present/absent, mention stripped/kept, a bad template falls back; `humanise_duration`
table (0 s, 59 s, 60 s, 3600 s, 7800 s, missing stamp); `ended_embed` with a custom author and blank author;
`end_summary` three shapes. `tests/cogs/content/test_golive.py`: `_mark_ended` edits content + embed once with the
keys set, keeps today's behaviour with the new keys blank, and never raises when the fetch/edit refuses (a log line
instead). `tests/api/tools/test_golive.py`: the preview route for staff, refused in words for a member (the
refusal names what it needs — checklist: never a bare status). Both `pytest -n auto` orders per
`docs/access/testing.md`.

## E. Docs the build touches (in its worktree)

`docs/info/code-notes.md` for the lines touched; the `golive-*` guide(s) in `black_bloc/guides_seed.json` — a step
"Set what the announcement says once the stream ends" if one is missing; `docs/access/sweeps.md` rows lettered
`GE-a…` (the owner numbers them at the landing): end mode on → a real stream ends → the message reads the past
tense with the length, the card's top line reads the new author, the `@Events` text is gone; preview on the page
matches; blank template → old behaviour. This doc's `## Deviations` foot. NOT `TODO.md` / `DONE.md` / `deploys.log`.

## Deviations

*(the build agent writes here what it had to do differently, dated)*

*(the build, 2026-09-17, branch `golive-end`, cut off `main` `fb1600b` and rebased onto `main`
`905982b` once the modmail-hide and tempvoice-lobby merges landed. Everything §A–§E asks for is
built; these are the places the build had to decide something the design left open, or depart.)*

1. **`keep_mention` governs the BLANK template too.** §A says a blank `golive_end_template`
   keeps the live sentence "as before" (which kept the mention), §B says the prefix is stripped
   unless `keep_mention`. Those disagree, so one rule was chosen for both shapes: the key decides,
   default **off**, which is the owner's "let's not tag a role". `golive_end_keep_mention` true is
   literally-as-before. The existing cog test that asserted the old prefix-keeping behaviour was
   updated rather than deleted, and a second test covers the kept case.
2. **The registry had to be taught that these two keys may be blank.** `coerce_value` refuses
   blank for every `text` key, so `golive_end_template = ""` — the shape §A promises — could not be
   stored at all. New `settings_store.TEXT_MAY_BE_BLANK = ("golive_end_template",
   "golive_end_author")`; nothing else about text validation moved.
3. ⚠️ **Emptying the settings ROW does not blank it, and that is `ui.js`, not this build.** A
   settings row that is emptied calls `DELETE`, which clears the override and brings the DEFAULT
   back — so with a non-blank shipped default the blank shape is unreachable from the Settings
   page. Rather than change a shared file two other builds are in, the **Wording** card carries one
   button whose label flips: **Just add the ending instead** (`PUT ""`) / **Rewrite it instead**
   (`DELETE`, so the shipped wording comes back). ~~⚠️ **The Discord side has the same gap and it is
   NOT closed:** `/settings` ▸ the key card's modal is `discord.ui.TextInput` with
   `required=True` (`cogs/core.py:1284`), so an empty submit is refused by Discord itself, and
   Clear restores the default. Blanking from Discord would mean changing that shared modal for
   every key. **Left as a finding for the conductor** — a `KNOWN_ISSUES.md` entry was NOT written,
   because that file is not one this build was told to touch.~~
   ✅ **REVERSED 2026-09-17, branch `staff-reach`** (checklist 35). The finding became **KI-28**,
   and KI-28 is now CLOSED: the shared modal reads `settings_store.TEXT_MAY_BE_BLANK`
   (`required = key not in TEXT_MAY_BE_BLANK`), so an empty submit is accepted for those two keys
   and refused for every other text key exactly as before. Discord and the dashboard now reach the
   same shape, which is what checklist 33 asks for. Clear still restores the shipped default.
4. **`ended_render`'s signature carries the live `content` and the `suffix`.** §B's sketch
   (`template, info_or_row, name, *, duration, mention_prefix, keep_mention`) has nothing for the
   fallback to append the suffix TO, and the mention prefix is read off the content rather than
   passed in — one argument fewer and no way for the caller to hand in a prefix the message does
   not have. Signature as built: `ended_render(template, info_or_row, name, *, content, suffix,
   duration, keep_mention)`.
5. **`ended_author` is its own function, not a branch inside `ended_embed`.** The preview route
   needs the author line without building an embed, and the cog needs it inside one.
6. **`tidy` is shared by both templates and is a fixed list of four repairs** — empty brackets, a
   dangling `for on in at — – ·` before punctuation or end of line, a doubled space, a space before
   a full stop. §A only names `()` and `for `; the other two came out of the author line
   (`"Sky was live on "` with no platform) and a trailing `{url}`.
7. **The page's client-side guess at the ended sentence is GONE.** `wordingCard` used to paint
   `${prefix}${filled}${endSuffix}` as it typed, which is the wrong answer the moment a rewrite
   exists. The ending now has one home: the **Wording** card, rendered by the bot. The live
   preview-as-you-type stays, because a server route cannot preview unsaved text.
8. ~~**The card has its own Refresh, and that is a real gap in the "hook the save event"
   instruction (§C).** `namespaceSettings` and `modeSwitch` both take `onSaved` and are hooked. The
   wording editor above it saves through `templateEditor`'s docked bar, and `ui.js` passes no
   `onSaved` through — reaching into a shared file for that one hook was not worth the collision,
   so the card says what it reads and offers the press.~~
   ✅ **REVERSED 2026-09-17, branch `staff-reach`** (checklist 35, and §C.2 of
   `staff-reach-design.md` names this deviation as the gap it closes). `templateEditor` now takes
   `onSaved` and passes it to `settingsEditor`, which already had it; both wording editors on the
   page hook it, so the **Wording** card repaints itself when either is saved. Refresh stays, for a
   change somebody else made from the Settings page or from Discord, and its help line was
   rewritten to say so rather than to tell the reader to press it after every save.
9. **Two files outside the brief's list had to change, both one-liners of registration, not
   behaviour:** `site/public/assets/labels.js` (three labels — `tests/test_settings_store.py::
   test_every_registry_key_the_site_shows_has_a_label` fails without them) and
   `site/mock/contract.json` (the route's row, which §B asks for in the same breath as the mock).
10. **The preview sample's url is `https://www.twitch.tv/blackbloc`** — §B writes
    `https://twitch.tv/…`, which is not a url. It matches the `/golive` panel's own test stream.
11. **`_mark_ended` takes `ended_at` from its caller** rather than re-reading the row, so the
    stored stamp and the rendered length cannot disagree; both callers (`_end_live`,
    `_close_session`) compute `now_iso()` once.
12. **The guide step went in the MEMBER guide as an observation, not a staff "Set …" step.**
    `golive-announce` is the only `golive-*` guide and its audience is `member`; a settings step
    would be one the reader cannot press. It gained a fifth step ("Stop your stream and wait a
    minute") and a fault row that names `golive_end_mode` and where a Lead flips it.
13. **NOT done, deliberately:** `golive_end_mode` was NOT flipped (§A says the owner does it);
    `TODO.md`, `DONE.md` and `deploys.log` untouched; nothing deployed or merged; no `/golive`
    panel control was added for the new keys (§B only asks the panel's **stream end** line to name
    the shape, which it does).
