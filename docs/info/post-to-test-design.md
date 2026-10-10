# Post to test — a preview copy in #post-test whatever the posts switch says

> **Audience:** the build agent (branch `post-to-test`), reviewers, and the next build that touches Posts or
> the sticky desk. **Status:** TRACKED · 🔨 DESIGN 2026-10-10 12:1x Phoenix, dispatched to Opus; NOT built,
> NOT merged, NOT deployed. **Last verified: 2026-10-10** — the code facts below were read off `main`
> `c6a8b057` (v221 live) by the conductor: `posts.publish_post` `:1359`, `_existing_message` `:1285`,
> `_drop_shadow` `:1323`, `set_shadow_posted` `:654`, `forget_message` `:665`, `shadow_channel_id` `:1254`,
> `shadow_words` `:1264`; the API route `api/tools/posts.py:311` (`_move`); the site `page-posts.js` (`publish`
> button `:769`, `willPost` `:243`, `postedLine` `:224`); the mock `site/mock/server.mjs:4028`; the sticky desk
> `sticky_posts.py` (`post_message` `:91`, `owner_rule` `:113`, `_post_copy` `:365`, `repost` `:679`).
> ⚠️ **NOT checked:** nothing met Discord or a browser. Secret NAMES only (none here).

## The ask (owner, Sat 2026-10-10 12:0x Phoenix, verbatim)

> *"So when we turn post live we'll lose the ability to preview them in post test. Can we have a button for post
> to test it first to post test even once we set the actual channel for the post?"*

Context: the rehearsal channel is **#post-test** (`1550284332365783091`, renamed from #welcome-test this
morning); `posts_shadow_channel_id` points there ([`rehearsal-home-design.md`](rehearsal-home-design.md)).
Today a copy reaches it ONLY while `posts_mode = shadow`, through the shadow branch of `publish_post`. The day
posts go `on`, Post it goes straight to the post's own channel and there is no preview path left.

## The design — the shadow branch becomes a move of its own

**One new move, `posts.rehearse_post(bot, guild, row, actor, *, via)`**, which is `publish_post`'s shadow branch
with `shadow` forced on, regardless of `posts_mode` above `off`:

1. Refusals as `publish_post`: `posts_off` (409) when the mode is off; `nothing_to_post`; `title_too_long` /
   `body_too_long`; `no_shadow_channel` when `shadow_channel_id(bot, guild)` is blank; the guard's `test_mode`
   with a `post.would_rehearse` row. A missing `channel_id` is NOT a refusal (a test copy needs no real channel).
2. The target is `shadow_channel_id(bot, guild)` (#post-test). The message is `message_parts(...)` with the
   blocks, exactly what Post it would send — plus the rehearsal note line the shadow copy carries today, so
   staff can tell a test copy from a real one in the same channel. **Reuse the existing note, do not invent a
   second spelling** (`shadow.note_line`; see how the sticky desk's `_place` composes it at `:331`).
3. The copy is tracked on **`shadow_message_id`** exactly as a shadow copy is: `_existing_message(..., shadow=True)`
   edits in place on a second press; a 404 is forgotten and re-sent. Written with `set_shadow_posted`.
   **⚠️ `set_shadow_posted` also overwrites `posted_hash` / `posted_at` / `posted_by`.** When the row ALREADY has
   a real `message_id` (posts are on and the post is up), a test copy must NOT disturb those three — they are
   what `changes_pending` and the Posts page's *posted* state read. Add a narrower writer (`set_test_copy`, or a
   `touch_posted=False` flag on `set_shadow_posted`) that writes only `shadow_message_id` in that case. Test it.
4. Log kinds: `post.rehearsed` (first copy) and `post.rehearsal_updated` (edited in place), `web.`-prefixed from
   the site (`logkinds.kind_via`; checklist 34), with `shadow_home`, `message_id`, `slug`, `post_id`, `via`.
   Register both in `logkinds.py`; a version is NOT recorded (nothing shipped — `record_version` is for real
   posts; the shadow branch records one today, and that stays as it is for the shadow MODE path).
5. **The next real Post it / Update takes the test copy down** — `publish_post` already calls `_drop_shadow` on
   every non-shadow publish; nothing to add. `take_down_post` already removes a shadow copy; nothing to add.
   Say so in the words (below).
6. **While `posts_mode = shadow`, `rehearse_post` and `publish_post` do the same thing.** The button is HIDDEN
   on both doors in shadow (Post it already says *this goes to #post-test*). In `on` it shows beside Post it.
   In `off` it shows and refuses in words like Post it does.

**A sticky's post (the leaderboard).** `publish_post` hands a sticky's post to the Desk (`sticky_rules.row_of_post`).
`rehearse_post` must NOT — a test copy of a sticky is one PLAIN message in the rehearsal home, not pinned, not a
sticky, never counted by the Desk: build it with `sticky_posts.post_message(bot, guild, post, note)` (the post and
its blocks, fresh, the note above) and send it through the same path as any other test copy, tracked on
`shadow_message_id`. Two rules:
- If the sticky is itself REHEARSING (`owner_rule` says `shadow`), its live rehearsal copy already sits in that
  home and `shadow_message_id` is that copy's id — answer 200 *"It already rehearses in #post-test — the copy there
  is live."* and send nothing.
- When the Desk next posts a REAL copy (`_post_copy` with `rehearsed=False`), it drops the test copy the way
  `publish_post` drops a shadow one: call `posts._drop_shadow` (make it public, `drop_shadow`) there. One line.

## The doors

| Where | What |
|---|---|
| Posts ▸ a post's drawer | A **Post to test** button beside Post it / Update the post (tone `quiet`), shown when `payload.mode !== 'shadow'`. Like Post it it SAVES a dirty draft first (rule 3 of the owner's ask: what goes out is a version), then `POST /api/posts/{slug}/rehearse`. The sentence under the buttons (`willPost`) gains a second line in `on`: *Post to test sends a copy to #post-test as it would look, without touching #channel; the next Post it takes the copy down.* The posted line (`postedLine`) names BOTH when a real copy and a test copy are up: *Posted in #channel · a test copy is in #post-test.* A **test copy** pill in the status pills (tone `info`). |
| Posts list row | The same pill. |
| `/posts` card | A **Post to test** button (`ButtonStyle.secondary`, row 0 — ⚠️ row 0 already holds Post it, Take it down, Edit…, Pin it and sometimes Delete: that is FIVE. Put Post to test on row 1 beside Versions and Back; `RemoveBlockButton`s share row 1 capped by `REMOVE_CAP` — lower the cap by one or move Post to test to row 1 only when fewer than two removes show. Say which in Deviations.) Hidden in shadow. The card's lines gain *a test copy is in #post-test* when one is up and the mode is on. |
| API | `POST /api/posts/{slug}/rehearse` `{}` → the same `_move` wrapper and the same whole-posts payload as `/publish`. Errors: the codes above. Contract entry beside `/publish` (`read_by: page-posts.js Post to test`); mock route in `server.mjs` beside `/publish` (`shadow_message_id`, `web.post.rehearsed` / `web.post.rehearsal_updated`, no version). |

The payload's post rows already carry `posted_where`; add `test_copy: bool` (a `shadow_message_id` while the mode is
`on`) so the page does not have to infer it.

## Words (module constants in `posts.py`, the Posts convention — not keys)

- `REHEARSED_SAID`: *"Sent a test copy of {title} to {shadow}. The real post in {where} is untouched; the next Post
  it takes the test copy down."* — `{where}` reads *its channel* when the post has none yet.
- `REHEARSAL_UPDATED_SAID`: *"Updated the test copy of {title} in {shadow}."*
- `STICKY_ALREADY_REHEARSING`: as above.
- The `/posts` card line and the site's second `willPost` line: one spelling each, exported so the test can
  assert the page and the card say the same thing (`test_posts.py` has this pattern for `shadow_words`).

## Tests (the hermetic suite; `tests/test_posts.py`, `tests/cogs/community/test_posts.py`,
`tests/test_sticky_posts.py`, the API tests beside the publish ones)

- `on` + real copy up: rehearse sends to the rehearsal home, writes `shadow_message_id`, leaves `message_id`,
  `posted_hash`, `posted_at`, `posted_by` byte-for-byte; a second press edits; the next `publish_post` drops it
  and the row's `shadow_message_id` is NULL.
- `on` + no channel: rehearse works; `publish_post` still refuses `no_channel`.
- `off`: refused `posts_off`. Blank rehearsal home: `no_shadow_channel`. Guard on: `post.would_rehearse`.
- `shadow`: the site payload / card hides the button (assert on the rendered view: no button labelled Post to test).
- A sticky's post: rehearsing in shadow answers the already-rehearsing sentence and sends nothing; on, one plain
  message (not pinned, `Desk` counts untouched), and the Desk's next real `_post_copy` deletes it.
- The log kinds exist and the web-prefixed ones are real kinds (`tests/test_logkinds.py` guards).
- Contract: `node site/mock/check.mjs` passes with the route added (routes 362 → 363).

## What the build does NOT do

- No new settings key, no schema change (`shadow_message_id` exists).
- No change to what `shadow` mode does.
- No deploy: the conductor merges, deploys and runs the live check.

## Live check steps for the conductor (after merge + deploy)

1. Posts ▸ Welcome and rules (posts are shadow → no button; Post it still names #post-test).
2. Flip NOTHING live. The proof of the `on` path is the suite plus the mock until the owner flips posts on; record
   that in the deploy line as NOT verified live.
3. `/posts` ▸ a card in shadow: no Post to test. Logs: nothing new.
