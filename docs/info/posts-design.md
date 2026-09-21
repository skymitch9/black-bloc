# Posts — the welcome and rules message, written on the website, posted and kept current by the bot

> **Audience:** the build agent and reviewers. **Status:** TRACKED · ✅ **LIVE as v113** — merges `440c0c6` (base) + `34b86a5` (shadow), release `4d60f68`, deployed **2026-09-16 17:36** Phoenix (`../deploys.log`); landing entry in [`../DONE.md`](../DONE.md) (*"2026-09-16 — POSTS"*); the two `## … deviations` feet are the truth where they depart from the body; sweeps **390–418** are the owner's. Was: 📐 DESIGN → dispatched to an Opus build 2026-09-16 15:4x (owner, 2026-09-16 13:5x, verbatim: *"in the welcome channel there is a post
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

### C1. Storage (schema 35 → 36; ⚠️ `shadow_message_id` actually landed at **37**, in the follow-up — see `## Shadow-mode deviations`)

```
posts  id, guild_id, slug UNIQUE(guild_id, slug), title, channel_id (NULL ok), body, style
       (plain|embed), pin (bool, default 1), message_id (NULL ok), posted_hash (NULL ok), posted_at,
       posted_by, shadow_message_id (NULL ok — the copy a shadow publish keeps up), seed_hash (NULL ok),
       updated_at, updated_by
```

- One message per post. `body` is capped by style at save time **and** at post time: `plain` **2000**,
  `embed` **4096** (title ≤ 256 in the embed's own title). Over the cap is refused in words that name
  the cap and the count.
- `posted_hash` = sha256 of (`style`, `title`, `body`) at the moment it was sent; **"changes not yet
  posted"** = `posted_hash` differs from the same hash of the row now. One home: `posts.body_hash`.
- `seed_hash` marks the shipped post (same convention as guides): it cannot be deleted, only taken down
  and emptied; ~~**Put the original back** restores the seed text~~ **RETIRED 2026-09-20 on branch
  `posts-versions`** (owner: *"for all post lets remove the put back original and add a version
  history"*). `reset_post`, its route and both put-back buttons are gone; the shipped words are
  **version 1** in the new `post_versions` history, restored with **Use this version** like any
  other. `seed_hash` stays — it is still what refuses a delete and what earns the `shipped` chip.
  See [`posts-versions-design.md`](posts-versions-design.md).

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
| `posts_mode` | enum off/shadow/on | **shadow** | ~~enum on/off, default on~~ **changed 2026-09-16 15:4x, owner: "lets have all the test work go to blackbloc-logs until we're ready to go live, another shadow mode"** — `shadow` sends and edits the message in the shadow channel (~~the guard's test channel while `TEST_MODE`, else `log_channel_id`~~ **changed 2026-09-17, v129: `shadow_channel_id` FIRST when it is set, then the guard's test channel, then `log_channel_id` — `black_bloc/shadow.py` is the one home and posts follows it for free; `info/rehearsal-home-design.md`**) whatever the post's own channel says, tracked in `shadow_message_id`; `on` posts to the post's channel and removes the shadow copy on the first real post; `off` refuses and hides `/posts` |
| `posts_panel_minutes` | int 1–1440 | **10** | how long the `/posts` panel stays live |
| `posts_log_level` | the log-level family | family default | generated |

Per-post choices (channel, style, pin) live on the row with both doors. Registry 212 → **215**.

### C8. Log kinds

`post.saved`, `post.posted`, `post.updated`, `post.would_post`, `post.post_failed`, `post.taken_down`,
`post.would_take_down`, `post.pinned`, `post.pin_failed`, `post.message_gone`, `post.reset`,
`post.created`, `post.deleted`, `post.mode`, `post.seed_channel_unknown`; feature `posts`,
`FEATURE_PAGES["posts"] = "posts.html"`; `posted` / `updated` / `taken_down` / `post_failed` important,
the rest routine. ⚠️ **The shadow follow-up adds four:** `post.shadow_posted` /
`post.shadow_updated` (important, like their twins), `post.shadow_taken_down` /
`post.shadow_message_gone` (routine). `logkinds.SHADOW` is the string `".would_"`, not the word
"shadow", so none of the four is silenced by the dry-run rule — a shadow publish is a real
message really sent.

### C9. Test mode, shadow, and the cutover

~~Under `TEST_MODE`, **Post it** on a post aimed at `#welcome` logs `post.would_post` and the site says so; a staffer points the post at `#blackbloc-logs` to see it~~ **Superseded 2026-09-16 15:4x by the owner's shadow mode:** with `posts_mode` = **shadow** (the default), **Post it** sends the real message into `#blackbloc-logs` (the shadow channel) and keeps it edited in place there, whatever channel the post names — so staff see exactly what would go up, where the bot is allowed to speak. The site's "how it will post" line and the panel card say so. Flipping to **on** is the go-live: the next Post it posts to `#welcome` and removes the shadow copy. `cutover-plan.md` gains one row: *point `welcome` at `#welcome`, press Post
it, then delete Carl's `1285806434050768927` by hand and turn Carl's welcome off*. Nothing here deletes
Carl's message.

## D. Calls the owner may overturn (each one line)

1. `plain` as the default style (headers render; 2000 cap) → one seed field.
2. Pin by default → the seed's `pin`.
3. Links in the preview are not clickable → one attribute in `discordmd.js`.
4. `/posts` exists at all (F-P1 below) → drop the cog, keep the module.
6. `shadow` as the default mode (owner's own call, 15:4x) → the seed of the key.
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

**2026-09-20, branch `discord-mock`:** the editor's preview pane and the Versions **View** drawer are now the **Discord mock** — `POST /api/preview/message` with feature `post`, so `posts.render_message` decides plain vs embed and clamps the title rather than the page deciding it a second time with `discordmd.renderPreview`. Side effect worth knowing: `<#id>` / `<@&id>` in a body now come back named by the BOT's guild rather than by the page's `/api/ref/*` lists. ⚠️ Built at `main` `be78bff`, so if the `posts-page` rebuild lands first these four small edits must be re-applied — see [`discord-mock-design.md`](discord-mock-design.md) ▸ What was NOT verified.

> Written by the Opus build, 2026-09-16, branch `posts` off `main` at `193dac9`. Each one is a
> place the build did NOT do what the section above says, with the reason. Nothing here has met
> Discord: every figure below is from the test suite, `check.mjs`, the Node renderer fixtures or
> the mock in a browser.

1. **§C2 — `render_message` answers BOTH keys, always.** The table says `{"content": body}` for
   plain and `{"embed": Embed}` for embed. It answers `{"content": …, "embed": None}` and
   `{"content": None, "embed": Embed}` instead. An **edit** from embed back to plain that does
   not pass `embed=None` leaves the old embed under the new content, and there is only one
   payload builder, so it has to be safe for the edit path too.

2. **§C1 — an over-long TITLE is refused, not clipped, in BOTH styles.** §C1 bounds the title
   only inside an embed. The first draft clamped to 256 and then checked the cap, which made the
   check dead and silently shortened what a staffer typed. Both doors now refuse over 256 with
   the count in the sentence; the embed wording offers the way out (set the style back to
   plain), the plain wording does not, because there is no bigger title.

3. **§C2 — an EMPTY body is refused at post time.** Not in the design. Discord rejects a message
   with no content, so without this the staffer gets a Discord error instead of a sentence.
   `post.nothing_to_post` is a refusal, not a log kind.

4. **§C2 — `reset_post` restores the title, the style and the pin as well as the body, and keeps
   the CHANNEL.** §C1 says "restores the seed text". Restoring the channel too would undo the
   §C9 workaround (point it at `#blackbloc-logs`, look at it, point it back) the moment somebody
   pressed **Put the original back**.

5. **§C8 — one kind more than the fifteen listed: `post.seeded`.** The same row `guide.seeded`
   leaves, written once per guild when the table is first filled. Routine.

6. **§C5 — the panel root carries a `Turn posts off` / `Turn posts on` button.** §C5's root lists
   four controls and no mode. Without it `post.mode` is a kind nothing emits, which
   `tests/test_logkinds.py::test_no_classification_entry_is_dead` fails on by name — and the
   "both ways" rule wants the mode reachable from Discord, not only from the site. The Posts page
   carries the matching `modeSwitch` in its head.

7. **§C7 — `posts_panel_minutes` is BOUNDED 1–1440; the other fourteen `*_panel_minutes` keys are
   not.** §C7 says 1–1440, so it was built that way (checklist 22), which meant adding the bound
   to `contract.json`'s `settings` block and to the mock. ⚠️ The other panel keys are still
   unbounded — that is a pre-existing inconsistency this build did not widen its scope to fix.

8. **§C3 — the preview draws mentions from `/api/ref/*` read ONCE per page load**, not per
   keystroke, and re-renders on a 60 ms timer rather than on every character.

9. **§C3 — the preview's headers are pinned to the UI face.** The site's display face (Bangers in
   the Black Bloc theme) reaches `h2`/`h3` by default, which made the preview's `# header` look
   nothing like Discord. Three lines of CSS inside `.preview`.

10. **`where_words` has one spelling of "there is no channel".** The panel line, the card and the
    page all read `no channel yet` for an unset channel and `a channel Black Bloc cannot see` for
    an id whose channel has gone. One home, because the two mean different things to a staffer.

## What the build did NOT do

- ✅ **BUILT 2026-09-16 on branch `posts-shadow` off `440c0c6`** — the paragraph below is kept
  as written because the refusal was correct and the reasoning is the precedent; what it
  describes as unbuilt is now built, and its calls are recorded in `## Shadow-mode deviations`
  at the foot of this file. ⚠️ **The shadow-mode clarification that arrived mid-build was
  REFUSED and was unbuilt at the time.** A
  mid-flight message asked for `posts_mode` to become `off / shadow / on` defaulting to
  **shadow**, with a new `shadow_message_id` column, `post.shadow_posted` /
  `post.shadow_updated` / `post.shadow_taken_down`, routing every shadow publish to the guard's
  test channel, deleting the shadow copy on the first `on` publish, and a mode select on both
  surfaces. That is new behaviour rather than a clarification — a column, three kinds, a routing
  rule and two new controls — and the standing rule is that a mid-flight message narrows,
  clarifies or stops, never widens. **It belongs in a fresh agent's initial brief**, where it
  will proceed normally. What is on the branch is §C7 as written: an `off` / `on` enum
  defaulting to `on`.
  ⚠️ **The decision itself is real and is recorded on `main` at `94c4b5b`** ("Posts design:
  posts_mode off/shadow/on, default shadow", owner verbatim), which is the commit AFTER this
  branch's base `193dac9`. So §C1, §C7 and §C9 on `main` already say off/shadow/on and this
  branch's code is one design revision behind them. Merging will conflict in
  `docs/info/posts-design.md` — take `main`'s §C1/§C7/§C9 and keep this file's `## Deviations`.
  The follow-up is small and well bounded: one column (schema 36 → 37), three kinds, a
  `shadow_channel_id` resolution in `publish_post`, the `off/shadow/on` choices on the key, and
  the mode control that already exists on both surfaces gaining a third value.
- **Nothing here has met Discord.** No message was sent, no pin taken, no `/posts` panel opened
  in a real client. The whole feature is proved against fakes, the mock and the Node fixtures.
- **`site/mock/check.mjs` was not run against the REAL API** — that is `tests/api/test_contract.py`'s
  half, and it is green.
- **The seed's channel id `1285369365071527997` was not checked against the live guild.** It is
  the 2026-08-26 archive's capture. If it is wrong the post simply has no channel and one
  `post.seed_channel_unknown` row says so, which is the behaviour §C6 asks for.

## Shadow-mode deviations

> Written by the Opus build, 2026-09-16, branch `posts-shadow` off `main` at `440c0c6` — the
> follow-up the base build listed under `## What the build did NOT do`. The ten deviations above
> still stand; these are additional. ⚠️ **Nothing here has met Discord either.** Every figure is
> from the test suite (**5832 passed**, both orders, up from 5810), `ruff check .`, `check: ok -
> 19 pages, 168 routes, 14 core settings, all keys present`, the Node renderer fixtures, and the
> mock in a real browser at `http://127.0.0.1:8788/posts.html?as=staff`.

1. **`posted_where`, not `shadow_posted_hash` — ONE hash for both copies.** §C7's follow-up left
   the choice open. There is still exactly one `posted_hash`; the API says which copy it
   describes with `posted_where` (`"channel"` / `"shadow"` / `null`), and `is_posted` widens to
   mean "a copy is up somewhere". That is the smaller change: a second hash would be a second
   column, a second write path and a second way for the **changes not yet posted** pill to
   disagree with itself.

2. **`_existing_message` gained a `shadow=` FLAG rather than a twin function.** The brief said
   "its own `_existing_message` twin". One function with one keyword is the same behaviour with
   one canonical implementation, which is what the checklist asks for everywhere else.

3. **⚠️ A shadow copy is hunted through SEVERAL channels, not the one resolution picks.**
   ⚠️ **v129 note:** the hunt is now `shadow.find_copy` and `shadow_channel_id` is the first
   channel in it, so a copy left in `#blackbloc-logs` when the key moves is still found, edited
   and deleted. ⚠️ **It is NOT moved:** the next **Post it** posts a fresh copy in the new home,
   writes one `post.shadow_message_gone` row about the old one (which is not gone, only
   elsewhere) and leaves it where it was. The front door's and the ticket button's copies DO
   move themselves, because they reconcile on a sweep and a post does not. Deleting the
   stranded copy is a hand step — sweeps row **RH-d**.
   `shadow_channel_id` (singular) is where a rehearsal GOES; `shadow_channel_ids` (plural) is
   where one already IS — the guard's channel, `settings.test_channel_id`, and
   `log_channel_id`. Not in the brief, and it is the only place the build went wider than asked.
   The reason is checklist 3: **the cutover lifts `TEST_MODE` (P5) and then flips the mode to
   `on` (row 11)**, so the guard is gone by the time the rehearsal has to be deleted. Resolving
   once at delete time strands the copy in `#blackbloc-logs` for ever *and* clears its id off
   the row. The alternative — a `shadow_channel_id` COLUMN recording where the copy went — is
   the textbook answer and is a second column the brief did not ask for; if a later session
   wants it, that is the upgrade.

4. **A failed shadow delete reuses `post.post_failed`, not a fifth kind.** The brief named four
   kinds. `take_down_post` already reuses `post.post_failed` for a delete Discord refuses, so a
   fifth would be a second spelling of the same event. ⚠️ Checklist 2 is still satisfied: the
   success (`post.shadow_taken_down`) and the 404 (`post.shadow_message_gone`) are their own
   kinds, so no dry run and no failure share one.

5. **The failure KEEPS `shadow_message_id`.** The brief says a failure to delete "logs and does
   not abort". It also must not clear the id: a cleared id is a message nobody can find again.
   Keeping it means the next **Post it** retries the delete.

6. **`off` is refused by the MODULE, which closes a hole the base build had.** The panel gated
   on the mode; the website's **Post it** did not — it only carried an amber note and posted
   anyway. `publish_post` now answers `posts_off` / 409 for both doors.

7. **Shadow does NOT require the post's own channel.** `no_channel` is raised on `on` only.
   Shadow never reads `channel_id`, so refusing for want of one would refuse for a reason that
   has nothing to do with what shadow does — and seeing the message before choosing a channel is
   the point of the default.

8. **Three shadow sentences, not one.** `SHADOW_LINE`, `SHADOW_LINE_NOWHERE` and
   `SHADOW_LINE_SAME`. ⚠️ The third exists because §C9's OLD workaround told staff to point a
   post at `#blackbloc-logs`, and for such a row the asked-for sentence reads
   *not #blackbloc-logs* about `#blackbloc-logs`. Caught in the browser, not by a test.

9. **The sentence has a Python home AND a JS home.** Discord's card is built in Python; the
   site's "how it will post" line is rebuilt live from the draft as a staffer picks a channel,
   so it cannot come from the payload. That is the base build's own split (`WILL_POST` has no
   Python twin either); each side has a test asserting the exact words.

10. **`labels.js` was NOT changed.** Its `posts_mode` label is the key's human NAME, not its
    choices, and every sibling three-value mode (`golive_mode`, `automod_mode`, `events_mode`)
    keeps the same *"Whether …"* phrasing. Changing it would have made this one key read
    differently from the other fourteen.

11. **The site's switch reads ON · SHADOW · OFF, not off / shadow / on.** `ui.js`'s `segOrder`
    imposes the house ordering on every mode switch on the site; the DISCORD select uses the
    brief's order (`Posts are: off / shadow / on`, the golive shape). Not worth a special case
    for one feature.

12. **The `/posts` root lost its `Turn posts off` BUTTON.** Three values do not fit a two-state
    button. It is now a `ModePick` select on row 2, the same shape `/golive` has. ⚠️ Four sweep
    rows (`P-f`, `P-g`, `P-n`, `P-p`) were made stale by this and are corrected in place in
    `docs/access/sweeps.md`.

13. **Three fixtures turn posts ON, in three files.** `site/mock/check.mjs`'s `seed()`,
    `tests/api/test_contract.py`'s seeded fixture, and an autouse fixture in
    `tests/api/tools/test_posts.py`. Every contract route and every `web.post.*` kind is the `on`
    shape — and the GUARDED `/publish` entry only means anything when the post's own channel is
    the target, because in shadow it reaches the channel the guard allows and answers 200. The
    three fixtures are separate, so the decision is written three times; shadow has its own
    tests beside each.

14. **`tests/test_posts.py`'s fake channels no longer share message ids.** Every `FakeChannel`
    started at 9000, so hunting a shadow copy by id found the ACTION LOG's own message in
    `#bot-log` and reported the rehearsal alive. Discord's snowflakes are globally unique; the
    fake was the thing that was wrong, and it was wrong in a way that made a real bug look fixed.

### What this build did NOT do

- **Nothing has met Discord.** No shadow copy has been sent, no pin taken, no `/posts` select
  opened in a real client. The whole of it is proved against fakes, the mock and a browser
  pointed at the mock.
- **No `shadow_channel_id` COLUMN.** Deviation 3 covers the gap with a search; a column would be
  the stronger answer and is a schema 38.
- **The nine unrelated "no key" failures** under a shell carrying the real `.env` names are
  unchanged: **9 failed, 5824 passed** polluted, against **5832 passed** clean. None is a posts
  test.
- **`tests/api/test_contract.py` was not run against the MOCK**, and `check.mjs` was not run
  against the REAL API — that split is the base build's and is unchanged.
