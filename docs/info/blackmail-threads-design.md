# BlackMail — requests and modmail as forum channels, one thread each; the ticket button under the rules

> **Audience:** the build agent and reviewers. **Status:** TRACKED · ✅ **BUILT on branch
> `blackmail-threads`, off `main` `905982b` — NOT merged, NOT deployed, and nothing in it has met
> Discord.** Schema **40 → 41** (`requests.thread_id`) — ⚠️ **migrate before deploy**, and the number
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
