# Ninja marks — design

> **Audience:** future sessions and reviewers of the `ninja` branch. **Status:** TRACKED.
> **Last verified: 2026-11-02** — against branch `ninja` (off `main` `665a4219`): the full
> suite, the mock's `check.mjs` and node tests, and the Posts page drawn on the local mock in
> Chrome. ⚠️ **NOT verified:** anything against real Discord (the reaction itself, the user and
> channel selects' default values, the modal), anything on Fly, and the owner's sign-off.

## The ask (owner, 2026-11-02, verbatim)

*"Whenever PT pop or yato talk in the QOTW channel put the black skin ninja emote on their post.
do this for their next post and then let it be kicked off for a set amount of time with the
/ninja. the /ninja command should be staff only and let you select people to have the bot emote
on their post with the black ninja and for how many post or minutes with a settings menu"*

## What was built

A **mark** says: when THIS member posts in THIS channel, the bot puts the ninja emote on the
post, for a budget of N posts and/or M minutes, ending at whichever runs out first.

| Piece | Where |
|---|---|
| Table `ninja_marks` (schema **102**): `id, guild_id, user_id, channel_id, emoji, posts_left, until, made_by, made_at, ended_at, ended_because` (`posts` / `time` / `staff`); active = `ended_at IS NULL`; partial unique index `ninja_marks_one_active` on `(guild_id, user_id, channel_id) WHERE ended_at IS NULL` | `black_bloc/storage/db.py` |
| Store | `black_bloc/ninja_store.py` |
| Rules, words, moves (`mark`, `end`, `on_post`, `settle`, `is_due`, the in-memory map) | `black_bloc/ninja.py` |
| `/ninja` panel | `black_bloc/ninja_panel.py` |
| Listener + one-minute sweep + the slash command | `black_bloc/cogs/community/ninja.py` (in `bot.py:COGS`) |
| `GET/POST /api/ninja`, `DELETE /api/ninja/{id}` | `black_bloc/api/tools/ninja.py` |
| `GET /api/ref/emojis` (`{id, name, animated, string}`) | `black_bloc/api/ref.py`, `api/names.py:emojis` |
| Site fold **Ninja marks** on `posts.html#sect-ninja` | `site/public/assets/ninja-section.js` |
| The reaction itself, shared with weekly-question replies | `black_bloc/emoji.py:react_with` |

### Settings (all under `core`; `ninja_` would be a 26th group)

| Key | Type | Default |
|---|---|---|
| `ninja_mode` | enum `off`/`on` | `on` |
| `ninja_emoji` | text (one emoji or `<:name:id>` / `<a:name:id>`, never blank) | 🥷🏿 (U+1F977 U+1F3FF) |
| `ninja_default_posts` | int 0–1000 (0 = blank in the form) | 1 |
| `ninja_default_minutes` | int 0–43200 (0 = blank) | 0 |
| 33 word keys `ninja_*_label` / `_line` / `_said` / `_placeholder` / `_field` / `ninja_left_*` / `ninja_panel_*` / `ninja_end_confirm` / `ninja_modal_title` / `ninja_pick_line` | text | see `settings_store.NINJA_WORDS` |

`checked_question_reaction` became the shared `checked_emoji` (both emote keys use it).
`ninja_mode` is also a row in `/settings`' mode block (`settings_panel.EXTRA_MODES`, "`/ninja` to change").

### Log kinds (head `ninja`, filed under `core`, page `posts.html#sect-ninja`, label *Ninja marks*)

| Kind | Class | Details |
|---|---|---|
| `ninja.marked` / `web.ninja.marked` | important | `mark_id, user_id, channel_id, posts, minutes, until, emoji, via` |
| `ninja.reacted` | routine | `user_id, channel_id, message_id, mark_id, posts_left` (after) |
| `ninja.ended` / `web.ninja.ended` | routine | `mark_id, user_id, channel_id, because` (+ `via` from staff) |
| `ninja.react_failed` | important (`_failed`) | `mark_id, channel_id, message_id, why` |

### The panel's moves

Root: the emote and `ninja_mode`, one line per active mark (member, channel, what is left,
who made it, when). Buttons **Mark someone**, **Turn off** / **Turn on** (whichever is not in
force), **Refresh**; an **End a mark…** select when marks exist → a confirm card (**End** / Keep it).
**Mark someone** → a card with a member select (up to 25) and a channel select defaulting to
`question_channel_id`; **Next** renders only once both are picked → the **How long** form with
*Posts* and *Minutes* prefilled from the default keys (blank or 0 = no limit of that kind).
A refused form (no limit / bad number) keeps the card so staff can press Next again.

## Deviations from the brief, and why

1. **Panel words are settings keys** (as the brief asked), although the questions panel the
   brief pointed at keeps its words as constants. The points panel's `*_WORDS` registry shape
   was used; blank or unfillable staff wording falls back to the shipped words (`ninja.words`).
2. **The sweep ends timed-out marks even while `ninja_mode` is off.** The brief said off means
   "the listener and sweep do nothing". Checklist 3 and 38 say an end must not depend on the
   mode; ending reacts to nobody, and otherwise the page would list marks whose time has passed.
   Off still means: no reaction, no post counted.
3. **No asyncio lock; one-statement claims instead** (checklist 6). `claim_post` takes a post
   with a conditional `UPDATE` (live, posts left, clock not passed), `end` only ends an active
   row, and the unique index refuses a second active mark — so two posts, the sweep and a staff
   End cannot double-count or double-log. The reaction happens after the claim; a refused
   reaction gives the post back.
4. **Test mode / a guarded channel gives the post back silently** (no `react_failed` row), the
   same as `question_answers.react` treats the guard.
5. **A post after the clock ran out ends the mark (`time`) on the spot** without the emote,
   rather than waiting for the sweep.
6. **`ninja.react_failed`** was added (checklist 2: a failure never shares a kind with success);
   the brief named three kinds.
7. **Turn on / Turn off on the panel** — so `/settings`' mode row can truthfully say "`/ninja` to
   change". It writes through `cogs.core.set_key` (one `settings.set` row).
8. **The site fold shows `ninja_mode` as the shared mode switch on the Marked card** and lists the
   server's own emotes (from `/api/ref/emojis`) beside the `ninja_emoji` field; no picker.
9. `/ninja` is **not** hidden when `ninja_mode` is off (not in `HIDDEN_WHEN_OFF`): the panel is
   where staff see it is off and turn it back on.
10. The channel select offers text, announcement and public-thread channels.

## Open questions for the owner

- PT and yato are not marked by the build — staff mark them with `/ninja` (or the Posts page)
  after the deploy, as "their next post" = Posts 1 (the default).
- Is 🥷🏿 the emote he meant, or a server emote? (`ninja_emoji` takes `<:name:id>`; the page
  lists the server's emotes.)
