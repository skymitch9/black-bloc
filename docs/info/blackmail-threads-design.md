# BlackMail — requests and modmail as forum channels, one thread each; the ticket button under the rules

> **Audience:** the build agent and reviewers. **Status:** TRACKED · ✅ **LIVE as v119** — merge `85d88d3`, release `8040a81`, deployed **2026-09-17 10:51** Phoenix; schema 41; the `## Deviations` foot is the truth where it departs from the body; sweeps **471–486** are the owner's; KI-29 for the withdrawn post. Was: ✅ BUILT, not merged (the paragraph that stood here said nothing in it had met Discord — still true at the deploy; the forums were made by the website's Make the forum right after)** Schema **40 → 41** (`requests.thread_id`) — ⚠️ **migrate before deploy**, and the number
> is written as though the polls build has already taken 40 (`black_bloc/storage/db.py:11` and
> `tests/storage/test_db.py:16` are the two lines that carry it). ⚠️ **Read the `## Deviations` foot
> before the sections above: fourteen things differ from what is written here** — most importantly
> the starter message (1), the guard claim the sweep has to renew (2), the sixth request tag (4),
> the withdrawn gap (5) and `none` in place of a blank key (6). Sweep rows `BT-a` … `BT-p`; the
> code notes are `code-notes.md` `# Blackmail`. **Last verified: 2026-09-17 09:2x** against `main` `e6bd6ac`: `black_bloc/cogs/moderation/modmail.py`
> (`open_place` ~1628: channel mode makes a text channel in `modmail_category_id`, thread mode a **private thread**
> in `modmail_staff_channel_id`, `AUTO_ARCHIVE_MINUTES` 1440), `black_bloc/cogs/community/requests.py` (`notify`
> ~276 posts the filed card into `request_notify_channel_id`; `status_channel_id` falls back to it), the live
> BlackMail category `1550166808869478420` with `#modmail-log` `1550167775694037075`, the live keys. ⚠️ Secret NAMES only.

## Owner asks, verbatim (2026-09-17 09:0x, prompt boxes)

- *"Can we add a section to blackmail called request and have each request make a thread. Better yet have request be
  one of those thread channels. Same for the mod mail. Let's have mod mail be one of those thread channels so it
  doesn't grow to infinite length"*
- On the posted Open-a-ticket button: *"It'll be in the welcome but make sure we can change it. I want it posted right
  after the rules"*

**Reading of "one of those thread channels":** a Discord **Forum** channel — every post is a thread, the channel is a
list with tags, nothing scrolls forever. It is not today's thread mode (private threads hanging off a text channel).
The conductor put this reading to the owner in the same reply that dispatched this build; if he says otherwise the
build stops and re-plans. ⚠️ Forum channels need the guild's **Community** feature? — **No**: forums are available to
every guild since 2022; only *announcement* channels and onboarding need Community. Verify with one `GET
/guilds/{id}` read of `features` in the report anyway.

## A. Modmail gains a third mode — `forum`

| Key | Kind | Default | Help |
|---|---|---|---|
| `modmail_mode` | enum | `channel` (unchanged) | gains **`forum`**: *"channel (one channel per ticket), thread (private threads in the staff channel) or forum (one post per ticket in the forum channel — the list never grows past the forum's own archive)"* |
| `modmail_forum_channel_id` | channel | blank | *"the forum channel tickets are posted in, in forum mode; Setup on /modmail makes one under the ticket category"* |
| `modmail_forum_tags` | bool | **true** | *"true keeps the open / closed tags on each ticket post in forum mode"* |

- `open_place` in forum mode: `forum.create_thread(name=thread_name(...), content=<the ticket's first card text>,
  embed=<the card>, applied_tags=[open], auto_archive_duration=AUTO_ARCHIVE_MINUTES, reason=...)` → the thread. The
  rest of the ticket machinery already speaks to "a thread" (thread mode) — reuse that path for every reply, the
  close, the transcript. Closing edits the tags to `closed` and archives the post; re-opening (if a path exists) the
  reverse. Tags are made once by **Setup** (`open` 🟢 / `closed` ⚫) and their ids kept in the forum's own tag list —
  never in a key; look them up by name each time.
- **Setup** on `/modmail` (and the site's modmail page) gains **Make the forum**: creates `#modmail` as a forum under
  `modmail_category_id` (BlackMail) with the category's overwrites + the bot's, writes the key, makes the two tags.
  Under `TEST_MODE` this creates a channel outside the test category — allowed (creation is not gated), and the
  forum is owned (`guard.own_channel`) so the bot may post and delete there; say so in the reply.
- The PANEL_LINES defect the hide-toggle build found — the line naming the retired `/settings set-value
  modmail_panel_title` — is fixed here (checklist 33: name the Settings page and `/settings` ▸ **A setting group…**).

## B. Requests get the same shape

| Key | Kind | Default | Help |
|---|---|---|---|
| `request_forum_channel_id` | channel | blank | *"a forum channel where every request is its own post; blank posts the card into request_notify_channel_id as before"* |

- When set, `notify` creates a forum post per request (title = the request's one-line summary, first message = the
  card + its buttons), stores the thread id on the row (⚠️ **migration**: `requests.thread_id INTEGER` — schema +1;
  coordinate with the polls build, which also migrates: whoever merges second renumbers), and every `notify_move`
  line goes INTO that thread instead of the status channel; a decision (done / declined) edits the tag and archives
  the post. `request_status_channel_id` keeps working when no forum is set.
- **Setup** on `/request`'s staff panel and the site's requests page gain **Make the forum**: `#requests` under
  BlackMail, same overwrites rule, tags `open` / `picked up` / `on hold` / `done` / `declined` matching `LOOKS`.

## C. The ticket button right after the rules

`modmail_panel_channel_id` is `#welcome` (set 09:1x). The posts feature owns the welcome/rules message
(`black_bloc/posts.py`, slug `welcome`). Rule: when the ticket-button message is (re)posted by the modmail
reconciler and the welcome post's message is in the same channel, the button is posted AFTER it — and when the
welcome post is re-posted (posts' **Post it**), the modmail reconciler re-posts its button so it sits under the new
rules message again. One key: `modmail_panel_follows_post` (text, default `welcome`, blank = never re-post for
that reason). Under `posts_mode = shadow` both messages sit in the guard's channel, in that order — that is the
rehearsal.

## D. Tests (mirror the package)

`tests/cogs/moderation/test_modmail.py`: forum mode open/reply/close/tags; Setup makes the forum + tags; a missing
forum answers in words. `tests/cogs/community/test_requests.py`: a request → a forum post, moves go into the
thread, decisions tag + archive, blank key = today. `tests/storage/test_db.py`: the migration. The panel-follows-post
order: the button lands after the welcome message and re-posts after a **Post it**. Both `pytest -n auto` orders.

## E. Docs

`docs/info/code-notes.md`; `modmail-doors-design.md` and `requests-panel-design.md` foot notes (checklist 35: strike
the decided bullets they change); the modmail and requests guides in `guides_seed.json`; `docs/access/sweeps.md`
rows `BT-a…`; `architecture.md` schema line; this doc's `## Deviations`. NOT `TODO.md` / `DONE.md` / `deploys.log`.

## F. The request post carries the staff moves (owner, 2026-09-17 12:1x) — ✅ LIVE as v122 (release `672c608`, 2026-09-17 12:38; the `### §F` deviations at the foot are the truth; sweeps 499–506)

> ✅ **BUILT** 2026-09-17 on branch `request-post-buttons` off `main` `f7cd19d`;
> **not merged, not deployed, never pressed in Discord.** Read the `### §F` block in this doc's
> `## Deviations` foot first — ⚠️ **deviation 1 is the one that matters: there are TWO move-button
> classes, because a `DynamicItem` on a timeout-bearing panel view de-registers its own template
> for every post in the guild.** `request_post_buttons` defaults to **true**.

Owner, verbatim: *"On the request thread there aren't buttons to edit it or anything / Why is that"* → shown the two
homes (the `/request` panel's staff card and the website) → *"Yes I want staff, mainly me to be able to interact
with request in discord too"*.

**Rule.** The forum post's FIRST message (the one `open_forum_post` makes) carries, under the filed card, the same
staff move buttons the `/request` panel's card draws for that status — `requests.card_buttons(status, ...)` rendered
by the SAME `CardMoveButton` class, one row, staff-gated on press (a member's press answers in words naming the role
it needs; nothing is hidden by rendering because a forum post is one message for everybody) — plus the **Open on the
site** link as the last item of the row or a second row (Discord: five per row). Every move a staff member makes on
the post edits that same first message's buttons to the new status's set (the card already re-renders on
`notify_move`; the buttons ride along) and posts the move line into the post as today. A decision (done / declined)
leaves NO move buttons on the message (the link stays) and archives the post as today. **Persistence:** a press must
survive a restart — register the button as a `DynamicItem` (custom id `request:<id>:<move>`) the way the posted
ticket button and the rolemenu panels do, so the post is pressable for as long as it exists; the panel's own
`CardMoveButton` may stay a panel item if it is not already dynamic — one class, two registrations is fine, two
classes is not.

**Keys.** `request_post_buttons` — bool, **default true**, help: *"true draws the staff move buttons on each
request's forum post (and edits them as the request moves); false leaves the post a notice with the site link"*.
Registry + mock row + label.

**Tests (mirror the package).** The post's first message carries the status's buttons + the link; a staff press moves
the request, edits the buttons and posts the move line into the post; a member's press is refused in words; a decision
leaves only the link; the dynamic item resolves after a fresh view registry (restart); key off = today. Both orders.

**Docs.** `code-notes.md`, this doc's `## Deviations`, `requests-panel-design.md` (strike the bullet that says the
channel card carries no moves, checklist 35), the requests guide in `guides_seed.json` (a staff step: *press a move on
the post*), sweeps rows `RP-a…`.

## G. A post somebody starts by hand in the requests forum becomes a request (owner, 2026-09-17 12:4x)

Owner, verbatim: *"If someone makes a thread in the request area, does that link to a request"* → no → *"Make it so
we don't create a gap but it'll be hopefully under utilized"*.

**Rule.** When a thread is created in the forum `request_forum_channel_id` points at and it is NOT one the bot made
(no row carries its id as `thread_id`, and the starter message's author is not the bot), the bot files a request on
the starter's behalf: `what` = the post's title, `why` = the starter message's text (blank → *"(filed from a forum
post)"*), filer = the post's author, `source` = a new value `forum` (⚠️ check whether `requests` has a source column;
if not, add one with a migration — schema 41 → 42 — defaulting `panel` for old rows, and say so). The row takes that
thread as its `thread_id` (no second post is made), the bot replies IN the post with the filed card + the staff move
buttons (the same first-message shape `open_forum_post` makes, as a reply since the starter message is not the
bot's), applies the `open` tag, and DMs the filer the usual filed notice. Everything after that is a normal request.
Who may file this way follows `request_who_can_file` — a post by somebody it excludes gets one reply in words
(what happened, what it needs, how to get it: *"file it with `/request`, or ask staff"*) and the post is left alone,
not deleted. The bot's own posts, and posts with a row, are ignored (idempotent on `on_thread_create` firing twice
after a restart — check the row by `thread_id` first).

**Key.** `request_forum_adopts_posts` — bool, **default true**, help: *"true turns a post somebody starts by hand in
the requests forum into a request filed by them; false leaves such posts alone"*. Registry + mock row + label.

**Tests.** A hand-made post → a row with `thread_id` = that thread, the card + buttons replied, the tag, the DM, one
`request.filed` row with `via = forum`; the bot's own post is ignored; a second `on_thread_create` for the same thread
is ignored; a filer `request_who_can_file` excludes gets the reply and no row; key off = nothing. Both orders.

**Docs.** `code-notes.md`, this doc's `## Deviations` (`### §G`), the requests guide (a fact line), sweeps `RA-a…`.

## Deviations

> Written by the build, **2026-09-17**, on branch `blackmail-threads` off `main` `905982b`.
> Everything below is a place the build did NOT do what §A–§E says, and why. ⚠️ **Nothing here has
> met Discord.** The whole verification is `pytest -n auto` (**5998 → 6058**, and 6058 again under
> `BB_REVERSE=1`), `ruff check .` (clean), the ES-module parse of every `site/public/assets/*.js`,
> `node site/mock/check.mjs` (*19 pages, 177 routes, 14 core settings, all keys present*) and
> `node site/mock/discordmd.test.mjs`. No browser rendered either page, no Discord button was
> pressed, and `python -m black_bloc` was never booted.

1. ⚠️ **The forum post's starter message is the STAFF LINE, not the ticket card.** §A says
   `create_thread(content=<the ticket's first card text>, embed=<the card>)`. A forum post has to
   be created WITH its first message, but `make_place` runs **before** the ticket row exists — and
   the header embed needs `count_tickets`, the member's roles and their join date, none of which
   can be built at that moment. So the starter message is `thread_invite(...)`, the same one-line
   staff ping thread mode already writes, and `post_header` then posts the dossier embed as
   message two exactly as it does in channel mode. One ping, in the one message that is guaranteed
   to exist, and the ticket machinery is untouched.

2. ⚠️ **The guard has to CLAIM the forum, and the sweep re-claims it.** §A says only that the forum
   Setup makes is owned. Measured while building: a claim lives in `TestModeGuard.owned_channel_ids`,
   which is in memory for the life of the process — so after any restart or deploy, `speak()` would
   have redirected every relay to `#blackbloc-logs` and left the ticket post empty while the ticket
   itself looked fine. `claim_forum` on the five-minute reconcile takes it back, **and only while
   `modmail_mode` is `forum`**, so widening test mode is a deliberate two-key act by a Lead. Each
   POST is claimed as well (at creation, and again on the sweep), and disowned at close so the set
   cannot grow without end. The window before the first sweep is refused in words
   (`FORUM_NOT_CLAIMED`), which names the sweep and its five minutes.

3. ⚠️ **`may_remove` had to learn about owned parents, or every forum close would have refused.**
   It answered `place.parent_id == test_channel.id` for anything with a parent; a ticket post's
   parent is the forum, so a close would have logged `modmail.would_remove_place` and left the post
   open and tagged `open` for ever. It now also accepts a parent the guard owns. Archiving a thread
   is an `edit_channel`, which the guard never patches, so `may_remove` is genuinely the only ask.

4. ⚠️ **The requests forum has SIX tags, where §B named five.** The design said *open / picked up /
   on hold / done / declined*, which leaves `review` — the state whose entire point is that the work
   is finished and waiting — wearing **picked up**, the tag for work still in progress. **ready to
   check** is the sixth. `sent_back` and `check_asked` are LOOKS rather than statuses and correctly
   have none (the row is back at `in_progress` / still at `review`).

5. ⚠️ **A WITHDRAWN request's post keeps its tag and is not archived — a known gap.** §B says a
   decision tags and archives. `withdraw_request` lives in `black_bloc/requests.py` and never calls
   `notify_move`, so it reaches no Discord surface at all today; giving it one would have meant a
   second place that edits a post, which is the duplication this build spent its care avoiding.
   Sweep row `BT-m` is written to find it. The fix, if anybody asks: route `withdraw_request`
   through `notify_move` with a look of its own, not a second tagger.

6. ⚠️ **`modmail_panel_follows_post` takes `none`, not a blank string.** §C says *"blank = never
   re-post for that reason"*. Measured: `coerce_value` refuses empty text for a `text` key, and
   `store.clear()` restores the DEFAULT — which is `welcome` — so "blank" was reachable from
   neither the Settings page nor `/settings`. A decision that only one door can reach is not
   configurable both ways (checklist 33), so the off switch is a word both doors can type.

7. ⚠️ **The button's position is decided by comparing SNOWFLAKES, not by reading the channel.**
   §C says the button is posted after the welcome message. A Discord id counts up with the clock,
   so "has the rules message landed under the button" is one integer comparison between two ids the
   bot already stores — no API call on the five-minute sweep, and no dependence on history order.
   In `posts_mode = shadow` the REHEARSAL copy is the one compared, because that is the copy in the
   guard's channel beside the button; that is the rehearsal §C asks for, and the mock of it is the
   only place it has been seen.

8. ⚠️ **`posts.publish_post` dispatches `post_published`; it does not call modmail.** §C says the
   reconciler re-posts the button after a **Post it**. Waiting up to five minutes for that would
   have left the button above the rules in the meantime, and calling the modmail cog from `posts.py`
   would have coupled a module that three doors share to one feature. `bot.dispatch` plus
   `Modmail.on_post_published` gives promptness with no coupling, and the sweep remains the
   guarantee if the dispatch is missed.

9. **`FORGETTABLE` and the Setup panel grew rather than the design's table.** §A's table names only
   the new keys. In practice the ticket forum needed the same three doors every other pointed place
   has — a picker (**Forum channel…**, forum channels only), a **Forget…** entry (*The ticket
   forum*), and an `on_guild_channel_delete` line (`modmail.forum_forgotten`) — or a deleted forum
   would have stayed in the key as a dead id (checklist 26). The two new Setup buttons are on **row
   3**: rows 1 and 2 already hold five and four components, and Discord allows five a row.

10. **Both web halves were built, and they are the same one path.** §A and §B say the site's modmail
    and requests pages gain **Make the forum**. `POST /api/modmail/forum` and
    `POST /api/requests/forum` call the cogs' own `make_forum` with `via=VIA_WEBSITE` and `note()`
    nothing, so one press leaves ONE `web.*.forum_made` row (checklist 34). ⚠️ **Neither page was
    opened in a browser** — the proof is `tests/api/test_contract.py` and `node site/mock/check.mjs`.

11. **The `PANEL_LINES` defect is fixed as asked**, and its own test asserts `set-value` is absent
    from the ticket-button card rather than only that the new words are present — a positive
    assertion would have passed with the retired subcommand still beside it.

12. ⚠️ **What was verified about Discord's forum API, and what was not.** Read off the installed
    `discord.py` **2.7.1**: `ForumChannel.create_thread` returns a `ThreadWithMessage` (fields
    `thread`, `message`) and takes `applied_tags: Sequence[ForumTag]`; `Thread.edit` takes
    `applied_tags`; `ForumChannel.edit` reaches `available_tags` through `**options` (it is not in
    the signature, but the body pops it and serialises each tag) and `Guild.create_forum` takes
    `available_tags` directly, which is what this build uses. **Measured against the live guild**
    (one `GET /guilds/1073710702776299640` with the bot token, features list only): the guild does
    **NOT** carry `COMMUNITY`, which is consistent with forums needing no Community feature —
    ⚠️ **but no forum was actually created there, so "a forum can be made in this guild" is
    inference from the API docs plus that reading, not a measurement.** `BT-a` is the row that
    proves it.

13. ⚠️ **`pytest -n auto` stalled twice with every worker idle (KI-26).** Once after the modmail
    forum piece and once after §C, both at the same shape the entry describes — the log untouched,
    CPU flat. Killed the process tree and re-ran; both retries passed in ~35 s. Neither was a
    failing test: the same commit passed forward and under `BB_REVERSE=1` immediately afterwards.
    That takes the count to **seven**, and ⚠️ **these two were NOT `deploy.ps1` runs**, so they do
    not meet KI-26's own threshold (*"a sixth hang on a PowerShell-tool `*> file` run"*) — they were
    plain Bash-tool `pytest` invocations, which is a shape the entry has not recorded before.

14. **What this build deliberately did NOT touch.** `modmail_mode` is still `channel`, both forum
    keys are still blank and `modmail_panel_channel_id` was not moved — the conductor sets those
    after the deploy, so every path here is dead code until he does. `docs/TODO.md`, `docs/DONE.md`
    and `docs/deploys.log` were not edited. Nothing was merged, deployed or pushed to `main`.

### Found at the landing (conductor, 2026-09-17 11:0x, v120)

The first real test request (**#6**, filed from the website at 10:58 with `request_forum_channel_id` set) made
NO forum post: `open_forum_post` asks `guard_allows(forum)` and the requests cog never claimed its forum — only
its posts (`thread_of`) — so under `TEST_MODE` every request was `request.notify_skipped_test_mode`. Deviation 2's
claim rule was written for modmail (`claim_forum`, gated on `modmail_mode = forum`) and had no twin here. Fixed in
`forum_of`: a keyed forum is claimed each time it is read — the key is the deliberate act, as the mode is for
modmail. The test that pinned the refusal (`test_a_forum_the_guard_refuses_is_skipped_in_the_log_not_posted`)
now asserts the opposite (`test_a_keyed_forum_is_claimed_for_the_guard_so_test_mode_still_posts`). Request #6
keeps no post; a second test request is filed after the deploy.

### §F — the request post's staff moves (build, 2026-09-17, branch `request-post-buttons` off `main` `f7cd19d`)

> Everything below is a place the build did NOT do what §F says, and why. ⚠️ **Nothing here has
> met Discord.** The whole verification is `pytest -n auto` (**6175 → 6196**, and 6196 again
> under `BB_REVERSE=1`), `ruff check .` (clean), the ES-module parse of every
> `site/public/assets/*.js`, `node site/mock/check.mjs` (*19 pages, 178 routes, 15 core
> settings, all keys present*), `node site/mock/discordmd.test.mjs` and
> `node site/mock/labels.test.mjs`. No forum post was pressed, no browser rendered the
> requests page, and `python -m black_bloc` was never booted.

1. ⚠️ **There are TWO move-button classes, which §F forbade — and the reason is a measured
   defect in `discord.py`, not convenience.** §F: *"one class, two registrations is fine, two
   classes is not."* Measured against the installed **2.7.1**: `ViewStore.remove_view`
   (`ui/view.py:970`) pops every dynamic TEMPLATE a view carried out of the process-wide
   `_dynamic_items` registry, and `View.stop()` (`:650`) reaches `remove_view` through
   `__cancel_callback`. The panel's card view is stopped on **every** re-render (`panels.retire`)
   and again on every timeout (`_dispatch_timeout`). So a `DynamicItem` used on the `/request`
   panel would have **de-registered the template for every forum post in the guild**, silently,
   the first time a staffer pressed Back — and the tests would never have seen it, because the
   fakes call `item.callback` directly and never go through the view store at all. A
   timeout-bearing panel view structurally cannot host a dynamic item. So `CardMoveButton` stays
   the panel's plain item exactly as it was (§F's own escape clause: *"the panel's own
   `CardMoveButton` may stay a panel item"*), `PostMoveButton` is the dynamic one, and the thing
   §F was actually protecting — one implementation — is kept by `move_pressed`, which both
   classes call and which holds all of the behaviour. Each class is ten lines with no logic in
   it. This is the modmail precedent (`TicketCardButton` on the card, the panel's own button,
   one `card_pressed`), arrived at for the same reason.

2. ⚠️ **A press on the post answers the presser with a NEW ephemeral message; it does not
   re-render anything.** §F says the post's first message is edited to the new status's set, and
   it is — but by `notify_move`, on the way through the shared move function, not by the press.
   Measured: a component press defers with `deferred_message_update`, so `finish_card`'s
   `edit_original_response` — the panel's path — would have replaced the request card on the
   post with a panel view, Back button and all. `opened_here(on_post=True)` defers
   `thinking=True` instead (a `deferred_channel_message`), which makes the interaction token
   point at a new ephemeral message the post can never be reached from. That is the whole of the
   divergence between the two surfaces: `opened_here` and `finished`, three lines each.

3. ⚠️ **Every move is drawn for everybody, `may_accept` included, and refused on the press.**
   §F's own reasoning ("nothing is hidden by rendering because a forum post is one message for
   everybody") is followed to its end: `post_view` calls `card_buttons(status)` with
   `may_accept_here` left at its default, where the panel passes the viewer's own answer. The
   staffer who marked a request ready and presses **Accept** on the post gets
   `REVIEW_BY_SOMEBODY_ELSE`, which names who may. Hiding the button on a shared message would
   have hidden it from the person who is allowed to press it.

4. **The `review` row puts the link on row 1; every other status keeps it beside the moves.**
   §F allows either ("the last item of the row or a second row"). `review` draws five moves,
   which is Discord's whole row, so the link has nowhere else to go; two or three moves and a
   link on its own second row reads as a stray. One conditional, `ROW_CAP`.

5. **`notify_move` re-draws the buttons BEFORE it re-tags.** `retag_post` archives the post at a
   decision, and a message inside an archived thread cannot be edited without un-archiving it
   first. Re-drawing while the post is still open costs nothing and leaves the archive the last
   thing that happens.

6. **The key reached a FOURTH door as well as the three §F named.** §F asked for registry + mock
   row + label; `request_post_buttons` also went into `page-requests.js`'s `SETTING_KEYS`, so it
   is editable on the requests page beside the forum key it depends on rather than only on the
   Settings page. ⚠️ **Neither page was opened in a browser** — the proof is
   `node site/mock/check.mjs` and `tests/test_settings_store.py`.

7. ⚠️ **What a WITHDRAWN request's post does is still KI-29, and this build did not change it.**
   `withdraw_request` reaches no Discord surface, so it re-draws no buttons either: a withdrawn
   request's post keeps the moves for the status it was in. That is the same known gap, one
   surface wider. The fix is the one KI-29 already names — route `withdraw_request` through
   `notify_move` — and doing it here would have been the second post-editor this build spent its
   care avoiding.

8. ⚠️ **The panel was left alone on purpose, and one existing test changed meaning.**
   `test_a_forum_post_carries_the_cards_link_button` asserted the link was the post view's FIRST
   child; it is now the last, so the test reads the link by URL instead. Nothing else about the
   panel, the channel/DM card or the DM moved.
   `test_the_panel_card_is_untouched_by_the_post_buttons` is what keeps it that way.

9. **What this build deliberately did NOT touch.** `docs/TODO.md`, `docs/DONE.md` and
   `docs/deploys.log`. No setting was flipped — `request_post_buttons` defaults to true but
   `request_forum_channel_id` is the owner's to set, so on a guild with no request forum every
   path here is unreachable. Nothing was merged, deployed or pushed to `main`.

10. ⚠️ **`pytest -n auto` did not stall once** (KI-26). Four full `-n auto` runs in this
    worktree — the baseline, two after the code, and the `BB_REVERSE=1` one — all finished in
    30–40 s. The count stands at seven.
