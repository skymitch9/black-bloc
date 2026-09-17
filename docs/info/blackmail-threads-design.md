# Blackmail — requests and modmail as forum channels, one thread each; the ticket button under the rules

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **DESIGN, dispatching to Opus as branch
> `blackmail-threads`.** **Last verified: 2026-09-17 09:2x** against `main` `e6bd6ac`: `black_bloc/cogs/moderation/modmail.py`
> (`open_place` ~1628: channel mode makes a text channel in `modmail_category_id`, thread mode a **private thread**
> in `modmail_staff_channel_id`, `AUTO_ARCHIVE_MINUTES` 1440), `black_bloc/cogs/community/requests.py` (`notify`
> ~276 posts the filed card into `request_notify_channel_id`; `status_channel_id` falls back to it), the live
> Blackmail category `1550166808869478420` with `#modmail-log` `1550167775694037075`, the live keys. ⚠️ Secret NAMES only.

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
  `modmail_category_id` (Blackmail) with the category's overwrites + the bot's, writes the key, makes the two tags.
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
  Blackmail, same overwrites rule, tags `open` / `picked up` / `on hold` / `done` / `declined` matching `LOOKS`.

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

*(the build agent writes here what it had to do differently, dated)*
