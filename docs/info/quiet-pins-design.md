# Quiet pins — the bot's own "pinned a message" notices are deleted

> **Audience:** future Claude sessions and the owner. **Status:** TRACKED.
> **Last verified: 2026-09-27** — against branch `quiet-pins` (off `main` `6f1b9f9e`, code at `f64c74c3`)
> by the test suite and the local mock only. ⚠️ **NOT checked:** nothing here has met Discord — no real
> pin notice has been deleted, the Manage Messages requirement was not measured on the live server's
> channels, and the author of a real `pins_add` notice was taken from Discord's documented behaviour
> and discord.py's `MessageType`, not observed. Not merged, not deployed.

## The ask

The owner, 2026-09-27 20:4x Phoenix, verbatim:

> *"also whenever the bot pins something it leaves that message in chat that the bot has pinned
> something, can we have that message be auto deleted if its pinned by a bot automatic process. it
> looks unsightly"*

## As built

| Piece | What it is |
|---|---|
| `black_bloc/cogs/moderation/quiet_pins.py` | One listener cog, `QuietPins`, registered last in `bot.py:COGS`. |
| `quiet_bot_pins` | Core `bool`, default **on** (`settings_store.py`, in `CORE_KEYS`). On the Settings page under Core; the `/settings` panel reaches it the same way. Off leaves every notice. |
| `quiet_pins.deleted` | ROUTINE row per deletion: `channel_id`, `channel`, `notice_id`, `pinned_message_id` (when Discord sent a reference), `parent_id` in a thread/forum post. |
| `quiet_pins.delete_failed` | IMPORTANT (by the `_failed` suffix) — at most **once per channel per boot**, with the reason (*Missing Manage Messages here…*, *The notice was already gone*, or Discord's status). Never raised, never retried. Files under Core on the Logs page (an unknown head is Core; no `HEADS` entry). |

The rule, all of it (`should_quiet`):

1. the message is in a guild, **and**
2. `message.type is discord.MessageType.pins_add` — the notice Discord posts, and nothing else, **and**
3. its author is **this bot** (`bot.user.id`) — Discord authors the notice as whoever pinned, so every automatic pin
   (marathon boards, runner posts, thread controls, go-live/spotlight pins, polls, posts) matches and a person's pin
   never does, **and**
4. `quiet_bot_pins` is on for that guild.

Then `message.delete()`. Threads and forum posts get the same notice and are handled the same way.

⚠️ **The bot needs Manage Messages in every channel it pins in** — deleting a system message is deleting a message.
Pinning already needs Manage Messages (or Pin Messages on newer permission sets), so where the bot can pin it can
usually delete; where it cannot, the first refusal in that channel lands in the log channel once per boot.

## Deviations

1. **No shadow mode.** The key is a plain bool, as briefed. The only thing this ever deletes is a notice the bot
   itself caused, so a rehearsal copy has nothing to rehearse; `bot.guard` is not consulted (it patches sends and
   edits, and deleting the bot's own notice is not a post).
2. **Filed under Core** (`CORE_KEYS`), because the `/settings` group select is at its cap of 25 and a pin can come
   from any feature. That makes it a core key, so `settings_core_keys_admin_only` gates who may flip it from Discord.
3. **No `logkinds.HEADS` entry.** An unlisted head already files as Core; adding `quiet_pins` would change
   `like_patterns("core")` (and its pinned test) for no gain.
4. **The failure memory is per boot** (a set on the cog). A deploy forgets it, so a still-missing permission is
   logged once more after each restart — deliberate, as a reminder.

## What was NOT verified

- Nothing met Discord. No real notice deleted; no real Forbidden seen.
- That Discord authors a bot-made pin notice as the bot — documented behaviour, not observed here.
- Which live channels lack Manage Messages for the bot — not measured.
- Rate: a marathon that pins many runner posts at once makes one delete per pin; not load-tested.
