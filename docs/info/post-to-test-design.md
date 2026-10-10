# Post to test — a preview copy in #post-test whatever the posts switch says

> **Audience:** the build agent (branch `post-to-test`), reviewers, and the next build that touches Posts or
> the sticky desk. **Status:** TRACKED · 🔨 DESIGN 2026-10-10 12:1x Phoenix, dispatched to Opus; BUILT on branch `post-to-test` (see **Deviations** at the end),
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

## Deviations

> Written by the build agent on branch `post-to-test` (2026-10-10). Every line was exercised by the hermetic
> suite or the mock gate; ⚠️ nothing here met Discord or a browser.

1. **The shadow copy carries NO note today — the design said it did.** `publish_post`'s shadow branch sends
   `message_parts(...)` with no rehearsal line (only the sticky desk, the door, modmail and others prefix
   `shadow.note_line`). Post to test adds the line anyway, because the point of step 2 holds: in `on` a test copy
   and nothing else marks it. It is `shadow.note_line(bot, guild, "<#channel>")` (or `no channel yet`), put above a
   plain post with `sticky.fit` and as the content of an embed post (`posts.with_note`). The shadow MODE path is
   unchanged and still sends no note.
2. **In `shadow`, `rehearse_post` CALLS `publish_post`** (not a copy of it) for a post that is not a sticky's, so the
   two cannot drift: same kinds (`post.shadow_posted`), same version, same pin. A sticky's post never takes that
   path (rule 1 of the sticky section decides it).
3. **`no_shadow_channel` has its own words, `posts.NO_TEST_CHANNEL`.** The existing `NO_SHADOW_CHANNEL` opens with
   *"Posts are in shadow…"*, which is false in `on`. Same code, same 409.
4. **Order of refusals.** `posts_off` first, then (sticky) the already-rehearsing answer, then `nothing_to_post`,
   `title_too_long`, `body_too_long`, `no_shadow_channel`, the guard. A sticky's post with no words but a block is
   not refused (the leaderboard is all block); it is refused `nothing_to_post` only when `post_message` comes back
   empty.
5. **No `set_drawn`, door, pin or `post_published` dispatch for a test copy beside a real one.** The block stamps
   and the door describe the REAL message; stamping them from the test copy would tell a block redraw the real copy
   is current when it is not. With no real copy up, `set_shadow_posted` + `set_drawn` run as the shadow branch does.
6. **The narrower writer is `posts.set_test_copy`** (writes only `shadow_message_id`), used whenever the row already
   has a `message_id`; otherwise `set_shadow_posted` as before.
7. **`status_words` and `move_label` take the mode (optional, default unchanged).** In `on`, a `shadow_message_id`
   is a test copy: with no real copy the pills read `not posted` + `test copy` and the button reads **Post it**
   (before, a test copy would have read `posted (shadow)` / **Update the post**, and the drawer's sentence said
   *"edits the message already in #channel"*, which Post it does not do). With a real copy: the usual pills plus
   `test copy`. One helper, `posts.has_test_copy(row, mode)`, is what the API's `test_copy` field reads.
8. **The sweep never pins a shadow copy while posts are `on`** (`reconcile_posts`). Without this, a test copy of a
   `pin = true` post would have been pinned in #post-test within five minutes — the design says it is not pinned.
9. **Desk drop: not one line.** `_post_copy` sits inside the `try` that UNSENDS the new real copy on any exception,
   so dropping there would let a cosmetic failure undo the real copy (checklist 12). The drop is
   `Desk._drop_test_copy`, called after that `try`, catching and logging its own failure. It also skips the id the
   Desk itself just moved: `_take_down` already deleted a sticky's own REHEARSAL copy when it goes live, and the
   stale `post` row still names it, so without the check every shadow→on flip would have logged a spurious
   `post.shadow_message_gone`.
10. **Taking a sticky's post down takes its test copy too.** `take_down_post` hands a sticky's post to
    `Desk.pause`, which calls `clear_posted` and would have forgotten the test copy's id while leaving the message
    in #post-test. When the sticky is not itself rehearsing, `drop_shadow` runs first. (The design said
    `take_down_post` needed nothing; true for an ordinary post, not for a sticky's.)
11. **Card layout: Post to test is on row 1 and takes one Remove slot** (`REMOVE_CAP` stays 3; the card draws
    `REMOVE_CAP - 1` removes while Post to test shows, and 3 in shadow where it is hidden). Row 1 holds at most
    Versions, Back, Post to test and two removes = 5. The third block is still removable from the site.
12. **Card line and drawer line.** The card gains `posts.TEST_COPY_LINE` (*"A test copy is in #post-test."*) when a
    test copy is up and posts are on. The drawer's posted line appends the same sentence (*"Posted in #welcome. It is
    pinned. A test copy is in #post-test."* — the design's ` · ` form read badly after the pin sentence), or reads
    only that sentence when no real copy is up. The second `willPost` line is `posts.REHEARSE_LINE`, shown only in
    `on` (also under *Pick a channel…*, since a test copy needs no channel), with `{where}` = `its channel`
    (`posts.ITS_CHANNEL`) when the draft has none. `tests/test_posts.py::test_the_page_spells_the_test_copy_words_the_way_the_card_does`
    reads the four JS constants off `page-posts.js`.
13. **The drawer stays open after Post to test** (Post it closes it): staff iterate — edit, Post to test, look,
    edit again — so the drawer settles on the answer, repaints the pills and the versions, and reloads the list
    behind it.
14. **Log kinds are ROUTINE** (`post.rehearsed`, `post.rehearsal_updated`): a preview reaches no member, so it does
    not post to the log channel at `important`. `post.would_rehearse` is routine by the `.would_` rule. Details
    carry `shadow_home`, `message_id`, `slug`, `post_id`, `channel_id`, `via`.
15. **Contract.** The entry sets `posts_shadow_channel_id` to the test channel for its own request (the real API's
    seed has no rehearsal home and answered `no_shadow_channel` without it). `test_copy` was added to every posts
    row shape in the contract, not only the new route's, because the list and the drawer both read it.
16. **The mock has no sticky's post on the rehearse route** (its `/publish` has none either); shadow on the mock's
    `/rehearse` runs the mock's publish.
17. ⚠️ **House-rule tension, flagged not decided:** the second `willPost` line is a how-it-works sentence, which the
    2026-10-04 *no explaining blurbs* rule forbids; it was built because this design (2026-10-10, later) asks for it.
    Deleting the `test` suffix in `willPost` and the `REHEARSE_LINE` twin removes it cleanly.
