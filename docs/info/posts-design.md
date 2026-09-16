# Posts — the welcome and rules message, written on the website, posted and kept current by the bot

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **DESIGN → dispatched to an Opus
> build 2026-09-16 15:4x** (owner, 2026-09-16 13:5x, verbatim: *"in the welcome channel there is a post
> there by Carl-bot that xontain the rules and the welcome message, We will be taking over that task. on
> the site we need a text box and preview window so the staff can update the rules on the website and
> have the bot post them"*). **Last verified: 2026-09-16 15:40 Phoenix** — §A read off `main` at
> `8e09399` (v112 live) and the 2026-08-26 archive scan. ⚠️ **NOT checked:** nothing here met Discord
> or a browser; the incumbent text is the archive's capture, not a fresh read of `#welcome`.

## A. What exists (measured)

| Fact | Where | Why it matters |
|---|---|---|
| The incumbent: **one Carl-bot message** in `#welcome` (channel `1285369365071527997`, message `1285806434050768927`), plain markdown, ❤️ ×74, **no components**; its full text is in the archive and is reproduced in §C6 as the seed | `docs/archive/current-bots/discord-scan-2026-08-26.md` § *Carl-bot: welcome, starboard, logs* | the takeover reproduces the text byte for byte, then staff edit it |
| Onboarding is `#welcome` (read the rules) → type in `#landing` → `Member` → the server. The rules post is INFORMATIONAL; the gate is elsewhere and the 2026-08-26 decision keeps `Member` on Discord's own rules screen | same archive; `feature-list.md` F17 | this feature posts text; it grants nothing |
| Carl's markdown uses `#` headers, `***bold italics***`, `>` quotes, `**bold**` — all render in plain message CONTENT (2000-char cap); an EMBED description (4096) does **not** render `#` headers | Discord's own rendering | style `plain` by default; `embed` is a per-post choice for long text |
| The pattern for "post a message once, then edit it in place, keep its id": role-menu panels — `rolemenu_panels.py` `repost` / `unpost` / `delete_panel`, `menu["message_id"]`, `WOULD_REPOST` under the guard, `REPOST_FAILED` with the reason | `black_bloc/rolemenu_panels.py:61–115` | copy the shape, not the code |
| `guard.allows_channel` is true only for the test channel, DMs and channels the bot MADE (`own_channel`); `#welcome` is none of those, so under `TEST_MODE` a post there is a `would_post` log row, never a message | `black_bloc/guard.py:45–70` | the site's Post button says that in words (the existing 409 guard sentence from `api/writes.py`) |
| The site has NO markdown renderer — `grep -rn markdown site/public/assets` → nothing | measured | the preview is new code, and it must escape HTML before it draws anything |
| The rail's **Runs the server** group: Moderation, Members, Automod, Honeypot, Modmail | `site/public/assets/shell.js:20–27` | **Posts** joins it after Modmail; mock pages 18 → 19 |
| Every panel is `panels.Panel`; the last program landing left **29** top-level commands and zero groups | `panels-program.md` §4 | `/posts` is the 30th, hidden when `posts_mode` is off like the other fourteen |
| The test channel is `#blackbloc-logs` (renamed today); `TEST_MODE` stays on until the cutover | `TODO.md`, `cutover-plan.md` | the FIRST real post to `#welcome` is a cutover step, not this build's |

## B. The decision in one paragraph

A **post** is a row: a slug, a title, the channel it lives in, its markdown body, a style (`plain` or
`embed`), whether to pin it, and — once the bot has posted it — the message id and a hash of what was
posted. Staff write and edit posts on a new **Posts** page: a text box with a character counter against
the style's cap, and a **live preview** that renders Discord's markdown the way Discord does, with
channel/role/member mentions resolved by name. **Save** writes the row. **Post it** makes the bot send
the message (or, if it already has one, **edit it in place**, never a second copy) and pin it if asked;
"changes not yet posted" shows whenever the saved body differs from the posted one. **Take it down**
deletes the bot's message and keeps the text. A `/posts` staff panel is the Discord door to the same
moves and a prefilled edit modal. The seed is Carl's welcome text, verbatim, aimed at `#welcome` — which
under `TEST_MODE` posts nowhere until the cutover; a staffer who wants to see it live points the post at
`#blackbloc-logs` first.

## C. The pieces

### C1. Storage (schema 35 → 36)

```
posts  id, guild_id, slug UNIQUE(guild_id, slug), title, channel_id (NULL ok), body, style
       (plain|embed), pin (bool, default 1), message_id (NULL ok), posted_hash (NULL ok), posted_at,
       posted_by, seed_hash (NULL ok), updated_at, updated_by
```

- One message per post. `body` is capped by style at save time **and** at post time: `plain` **2000**,
  `embed` **4096** (title ≤ 256 in the embed's own title). Over the cap is refused in words that name
  the cap and the count.
- `posted_hash` = sha256 of (`style`, `title`, `body`) at the moment it was sent; **"changes not yet
  posted"** = `posted_hash` differs from the same hash of the row now. One home: `posts.body_hash`.
- `seed_hash` marks the shipped post (same convention as guides): it cannot be deleted, only taken down
  and emptied; **Put the original back** restores the seed text.

### C2. `black_bloc/posts.py` (new pure module) — the moves, each with `via`

| Move | What happens | Log kind |
|---|---|---|
| `save_post` | writes the row; refuses over-cap in words; refuses an unknown channel in words | `post.saved` |
| `publish_post` | `channel_id` unset → refuse in words. Guard says no → `post.would_post` with the channel named, **nothing sent**. Has a `message_id` and the message still exists → `message.edit(...)` → `post.updated`. No message (never posted, or `fetch` 404s) → `channel.send(...)` → `post.posted` (a 404 first logs `post.message_gone`). Then pin if `pin` and not pinned (`post.pinned`, `post.pin_failed` never aborts the post — checklist 12). `allowed_mentions` = none except role mentions the body carries only if the actor may mention them (checklist 11). Any `HTTPException` → `post.post_failed` with the reason, row untouched | as listed |
| `take_down_post` | deletes the message if it exists, clears `message_id`/`posted_hash`, keeps the body | `post.taken_down` / `post.would_take_down` |
| `reset_post` | seed text back into `body` (seeded posts only) | `post.reset` |
| `reconcile_posts` | on `cog_load` and every 5 min (checklist 4/25): a row with a `message_id` whose message `fetch` 404s → clear it, `post.message_gone`; a row whose message exists but `pin` says pinned and it is not → re-pin once | `post.message_gone`, `post.pinned` |

`render_message(row)` → `{"content": body}` for plain, `{"embed": Embed(title, description)}` for embed,
in ONE function both doors and the preview's contract use. Every kind through `logkinds.kind_via`;
the website passes `via=VIA_WEBSITE`; the routes never `note()` on top (checklist 34).

### C3. The website — `site/public/posts.html` + `assets/page-posts.js` + `assets/discordmd.js`

- **Posts** under **Runs the server**, after Modmail (`shell.js` GROUPS; `icons.js` one glyph). Staff only.
- The list: one card per post — title, channel (name from the cache), **posted · pinned** pills or
  **not posted**, and a **changes not yet posted** pill when the hashes differ; **New post**.
- The editor (one post at a time): **Title**, **Channel** (the site's `channelSelect`), **Style**
  (plain / embed — the cap changes with it), **Pin it** (switch), the **text box** (a textarea with a
  live counter `1 482 / 2 000`, amber over 90 %, red over the cap and Save refused in words), and the
  **preview** beside it (right of the box on a wide screen, under it on a phone) that re-renders on every
  keystroke. Buttons: **Save** (the docked save bar the Settings page uses), **Post it** / **Update the
  post** (the label is the move it will make: post when there is no message, update when there is),
  **Take it down**, **Put the original back** (seeded only, behind a confirm), **Delete** (unseeded only,
  behind a confirm, refused while posted). Every refusal is the bot's sentence.
- **`discordmd.js`** — a small, dependency-free renderer used ONLY by the preview: escape HTML **first**,
  then `#`/`##`/`###` headers and `-#` subtext, `***`/`**`/`*`/`__`/`~~`/`||` spans, inline and
  fenced code, `>` and `>>>` quotes, `-`/`*`/numbered lists, masked and bare links (never made
  clickable — `rel`-less anchors would be a phishing surface; render them as link-coloured text),
  `<#id>` / `<@id>` / `<@&id>` resolved through the cached `/api/ref/*` lists (a missing id renders as
  `#deleted-channel` / `@unknown`, like Discord), `<:name:id>` / `<a:name:id>` as `:name:`, and
  `<t:unix:F>` as the reader's local time. Unknown syntax stays literal. In **embed** style the preview
  draws the embed box and does NOT render `#` headers (Discord does not). Its own test file:
  `tests/site/` does not exist — the renderer is proved by a Node test under `site/mock/` run by
  `check.mjs`'s script (`node site/mock/discordmd.test.mjs`), with Carl's seed text as one fixture and
  an HTML-injection fixture (`<img onerror>` in the body renders as text).
- A **"how it will post"** line under the preview: the channel, the style, pinned or not, and — under
  `TEST_MODE` — the sentence that it will not leave `#blackbloc-logs` until the guard is lifted.

### C4. The API — `black_bloc/api/tools/posts.py`

| Route | Gate | Does |
|---|---|---|
| `GET /api/posts` | staff | the list with `changes_pending`, `posted`, `pinned`, `channel_name` |
| `GET /api/posts/{slug}` | staff | the whole row + `cap` for its style + `seeded` |
| `PUT /api/posts/{slug}` | writer | `save_post(via=website)` |
| `POST /api/posts` | writer | new post (title, slug from title, empty body, no channel) |
| `POST /api/posts/{slug}/publish` | writer | `publish_post(via=website)`; the guard's refusal is the existing **409** with its sentence |
| `POST /api/posts/{slug}/takedown` | writer | `take_down_post(via=website)` |
| `POST /api/posts/{slug}/reset` | writer | `reset_post` |
| `DELETE /api/posts/{slug}` | writer | unseeded and not posted only; refused in words otherwise |

Contract + mock fixtures (the seed post, unposted; a second post, posted with pending changes) +
`check.mjs` green; `tests/api/test_contract.py` green.

### C5. `/posts` — the Discord door (one staff command, `posts_mode` off hides it)

Root: the posts as lines (title · channel · posted/pinned/changes pending) over **A post…**, **New
post…**, **Logs**, **Open on the site**. A post's card: the same lines plus a short preview (the first
300 characters) over **Post it** / **Update the post** (one of the two, never both), **Take it down**
(only when posted), **Edit…** (a modal: title + a paragraph box prefilled with the body; Discord caps
the box at 4000, which is above both style caps, so the cap is checked on submit and refused in words),
**Channel…** (a `ChannelSelect`), **Style…**, **Pin it / Do not pin it** (the label is the move),
**Put the original back** (seeded only), **Back**. Same functions as the site, `via=VIA_DISCORD`.
`posts_panel_minutes` (10).

### C6. The seed

`black_bloc/posts_seed.json`: ONE post, slug `welcome`, title `Welcome and rules`, style `plain`,
`pin` true, `channel_id` **`1285369365071527997`** (`#welcome`, from the archive — the build verifies
it against `/api/ref/channels` at seed time and leaves the channel UNSET with a `post.seed_channel_unknown`
row if it is not in the cache), body = the archive's verbatim text:

```text
Welcome to** Black in a Flash**, a dedicated space for Black gamers!  While we appreciate and see multiple teams around the content creation space we don't see one that is just for us, and that is what this Discord hopes to alleviate: the creation of a space where we can authentically and openly be ourselves.
# Familiarize yourselves with the rules before you join the discord.
**Failure to comply with the rules may lead to moderator action.**

***1. The moderation team reserve the right to remove anyone from the space.***
> If you cannot abide the rules or plainly speaking are not a good fit for the space, the moderators can remove you at will.

***2. Be respectful of others.***
> We will not tolerate any forms of harassment or bigotry, such as- but not limited to- harassment about race, gender/identity expression, sexual orientation, religion, disability, physical appearances. There's a line between a friendly roast and being a jerk.

***3. First and foremost, this space is to adapt, learn, and grow.***
> Let's try to keep that as the primary focus. It's okay to have off topic conversations or to be upset about things, but this is a space to empower ourselves. If you are going to detract from the experience of others, there may be moderator intervention.

You can head to the landing channel and type a message so you gain access to the rest of the discord. If you are unsure of something, you are welcome to ping the Aunties / Uncles role.
```

(The archive wrapped the lines for the page; the seed keeps Discord's line breaks — one paragraph per
blank line, quotes as single `>` lines. The `Welcome to** Black` spacing is Carl's own and is kept.)
Seeded once per guild when the table is empty; `seed_hash` refreshed on later boots; never overwrites
a staff edit. **Never posted by the seed** — posting is a person's press.

### C7. Keys (checklist 33), group `posts`

| Key | Type | Default | Help |
|---|---|---|---|
| `posts_mode` | enum on/off | **on** | whether staff can post from the site or `/posts`; off hides `/posts` |
| `posts_panel_minutes` | int 1–1440 | **10** | how long the `/posts` panel stays live |
| `posts_log_level` | the log-level family | family default | generated |

Per-post choices (channel, style, pin) live on the row with both doors. Registry 212 → **215**.

### C8. Log kinds

`post.saved`, `post.posted`, `post.updated`, `post.would_post`, `post.post_failed`, `post.taken_down`,
`post.would_take_down`, `post.pinned`, `post.pin_failed`, `post.message_gone`, `post.reset`,
`post.created`, `post.deleted`, `post.mode`, `post.seed_channel_unknown`; feature `posts`,
`FEATURE_PAGES["posts"] = "posts.html"`; `posted` / `updated` / `taken_down` / `post_failed` important,
the rest routine.

### C9. Test mode and the cutover

Under `TEST_MODE`, **Post it** on a post aimed at `#welcome` logs `post.would_post` and the site says so
in the guard's own sentence; a staffer who wants to see the real message points the post at
`#blackbloc-logs`, posts, reads it, then points it back — the row keeps the `message_id` of the test
post until **Take it down**. `cutover-plan.md` gains one row: *point `welcome` at `#welcome`, press Post
it, then delete Carl's `1285806434050768927` by hand and turn Carl's welcome off*. Nothing here deletes
Carl's message.

## D. Calls the owner may overturn (each one line)

1. `plain` as the default style (headers render; 2000 cap) → one seed field.
2. Pin by default → the seed's `pin`.
3. Links in the preview are not clickable → one attribute in `discordmd.js`.
4. `/posts` exists at all (F-P1 below) → drop the cog, keep the module.
5. A seeded post cannot be deleted → one refusal.

## E. Out of scope

Reaction-gating or any role grant from the post (the gate stays Discord's rules screen); scheduled or
recurring posts; more than one message per post (a body over the cap is refused, not split); images or
attachments; a per-member welcome DM; Carl's autorole on `#landing` (unconfirmed, not ours yet).

## F. Build brief essentials

- One Opus dispatch, worktree `C:/lcw/bb-posts`, branch `posts`, off `main` at the dispatch commit. Est.
  **300–420k** (schema + module + API + page + renderer + cog + tests). Commit at clean boundaries.
- Tests mirror the package: `tests/test_posts.py`, `tests/api/tools/test_posts.py`,
  `tests/cogs/community/test_posts.py` (or wherever the cog lands — say where), `tests/storage/test_db.py`
  the migration, `tests/test_logkinds.py` guards green, `tests/test_bot.py` counts (30 commands, 20
  features, 25 groups, schema 36), `node site/mock/discordmd.test.mjs` wired into the gate the way
  `check.mjs` is (`scripts/deploy.ps1` runs it; say where you added the line).
- Prove: seed → 1 row with the verbatim text and the channel resolved (or the unknown-channel row);
  publish under a guard that refuses → `would_post`, nothing sent; publish with a fake channel → one
  `send`, then a second publish → one `edit` and no second `send`; a 404 on fetch → `message_gone` then
  `send`; over-cap refused in both styles with the count in the sentence; the renderer's injection
  fixture renders as text; the counter and the pending pill measured in the mock in a browser.
- Docs: `## Deviations` foot here; `# Posts` in `code-notes.md` by NAME; sweep rows `P-a`… at the foot of
  `access/sweeps.md`; `access/site.md` page count; `cutover-plan.md` the one row; `info/README.md` row
  and `TODO.md` are the conductor's.

## G. Forks (decided by the conductor under the standing autonomy rule; the owner may flip any)

- **F-P1 — a Discord door at all.** (a) `/posts` as §C5 — recommended and chosen: the "both ways" rule,
  and a staffer at a phone can push the saved text without the site. (b) None, like guides (KI-27).
- **F-P2 — style default.** (a) `plain` — chosen: it is what Carl posts and headers render. (b) `embed`.
- **F-P3 — where it lives on the site.** (a) its own **Posts** page — chosen: a text box and preview
  need the width. (b) a section on the Moderation page.

## Deviations

*(empty until the build lands)*
