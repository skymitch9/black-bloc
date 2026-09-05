# Phase 7 design — modmail (F11)

> **Audience:** the Phase 7 build agent and the reviewer. **Status:** LOCAL
> ONLY. **Last verified: 2026-08-26** — incumbent schema measured from the
> scan (`discord-scan-2026-08-26.md`: ModMail category, 5 open tickets, topic
> `ModMail Channel <user-id> <channel-id> (Please do not change this)`, staff
> private notes by prefixing `=`); command table from `reference-bots.md`
> (Modmail `cogs/modmail.py`). Depends on Phase 1.
>
> ⚠️ **SUPERSEDED IN PART, 2026-09-05, by
> [`modmail-panel-design.md`](modmail-panel-design.md) (Builds A and B).** Everything §4
> *Management* names below — `/modmail block|unblock|blocked|mode|forget|status|settings`
> and the whole `/snippet` group — is **gone** (Build A); `/modmail` is one command that
> opens a panel, and those moves are its buttons, selects and modals. **Build B then
> retired `/areply`, `/note` and `/close`** into a sticky card at the bottom of every open
> ticket (**Reply · Reply as Staff · Private note · Close…**), added `modmail_reply_style`
> (`buttons`/`typing`/`both`) which decides whether a plain message typed in a ticket is
> still relayed, and added a practice ticket. **Only `/reply` is still typed.** The DM
> listener, ticket creation, the relay itself, the transcript and the reconciler are
> unchanged — the relay is GATED, not replaced. This document is kept as the record of WHY
> modmail works the way it does, not of which commands exist.

## Owner decisions this implements

- **Do what the current bot does** (channel-per-ticket) **and** wire a
  second mode — **private threads in one staff channel** — as a setting;
  the toggle moves to the F12 site later.
- Keep the staff workflow: private notes inside the ticket (`=` prefix in
  the incumbent).

## Shape

```
black_bloc/
├── modmail.py                   ← pure: ticket naming, message relay formatting (user→staff, staff→user, anonymous), transcript rendering
└── cogs/moderation/modmail.py   ← the cog: DM listener, ticket channels/threads, reply/close/block/snippets
tests/ test_modmail.py · cogs/moderation/test_modmail.py
```

Schema v8 (additive):

```sql
CREATE TABLE IF NOT EXISTS modmail_tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
    mode TEXT NOT NULL,                 -- 'channel' | 'thread'
    channel_id INTEGER NOT NULL,        -- the ticket channel, or the parent channel for threads
    thread_id INTEGER,                  -- thread mode only
    status TEXT NOT NULL DEFAULT 'open',-- open | closed
    opened_at TEXT NOT NULL, closed_at TEXT, closed_by INTEGER, close_reason TEXT, log_message_id INTEGER
);
CREATE TABLE IF NOT EXISTS modmail_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ticket_id INTEGER NOT NULL REFERENCES modmail_tickets(id),
    at TEXT NOT NULL, author_id INTEGER NOT NULL, direction TEXT NOT NULL,   -- in | out | note
    anonymous INTEGER NOT NULL DEFAULT 0, content TEXT, attachments TEXT       -- JSON list of urls
);
CREATE TABLE IF NOT EXISTS modmail_blocks   (user_id INTEGER PRIMARY KEY, by INTEGER, reason TEXT, at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS modmail_snippets (name TEXT PRIMARY KEY, content TEXT NOT NULL, by INTEGER, at TEXT NOT NULL);
```

Settings keys: `modmail_mode` (`channel|thread`, default **`channel`**),
`modmail_category_id` (channel mode; default: the existing *ModMail*
category id from the scan — while TEST_MODE, the test channel's category),
`modmail_staff_channel_id` (thread mode parent; default = staff channel),
`modmail_log_channel_id` (default `#modmail-log` `1442613059704066108`; test
channel while TEST_MODE), `modmail_enabled` (bool, default **false** — the
incumbent keeps answering DMs until the owner flips it; while off, a DM
gets one sentence pointing at the existing ModMail bot).

## The flow

1. **Inbound.** A DM to the bot from a guild member (not blocked, not a
   bot): find their open ticket or open one — channel mode: create
   `<username>` text channel in the category with topic
   `Black Bloc modmail | user <id> | ticket <id>` (our own topic; we do not
   pretend to be ModMail), staff roles view+send; thread mode: create a
   **private thread** named `<username> · #<ticket id>` in the staff channel
   and add the staff roles' members who react/… — simpler: **private thread
   + the bot mentions the staff roles once inside it** (mentioning a role
   in a private thread adds those members). Post a header embed (user,
   account age, join date, roles, prior ticket count), then relay the DM
   (content + attachments) as an embed `user → staff`. React ✅ to the DM.
2. **Staff reply.** `/reply <text>` (or plain messages in the ticket without
   a prefix = reply, matching the incumbent) → DM the user as an embed
   showing the staff member's name and role colour; `/areply <text>` →
   anonymous ("Staff"). **Private note:** a message starting with `=` (kept
   from the incumbent) or `/note <text>` → stays in the ticket, recorded as
   `note`, never relayed. Every relayed/noted message → `modmail_messages`.
3. **Close.** `/close [reason]` → DM the user the reason, render the
   **transcript** (chronological, notes marked, attachments as links) into
   the log channel as a file + summary embed, `status=closed`, then delete
   the channel / archive+lock the thread. `/close` with `silent:true` skips
   the DM. Auto-close: none in v1 (setting `modmail_autoclose_hours`
   reserved).
4. **Management.** ⚠️ **Superseded 2026-09-05 — every command in this item is
   retired; the moves are now controls on the `/modmail` panel.** As built:
   block/unblock a member, save/change/remove snippets, point the three places,
   pick the mode (applies to new tickets only — open ones keep their mode, and the
   panel still says so) and turn answering DMs on or off. `/reply snippet:<name>`
   survives. See [`modmail-panel-design.md`](modmail-panel-design.md).
5. **Edge cases.** User leaves the guild → note in ticket, keep it open;
   user DMs while blocked → one sentence, logged; bot restart → open
   tickets re-derived from DB (persistent views not needed — commands only).

## Test mode

Ticket creation is a side effect the guard cannot see: while `TEST_MODE`,
tickets are created **only in the test channel's category / as threads in
the test channel**, the log goes to the test channel, and the DM relay is
allowed (DMs are inside the policy). `modmail_enabled` defaults false, so
the owner turns it on for the sweep, DMs the bot, and sees a ticket appear
in the test category.

## Tests (offline)

`test_modmail.py`: ticket naming/topic, relay embed rendering (in/out/anon/
note), transcript rendering with attachments and notes; `cogs/moderation/
test_modmail.py`: open-or-find logic, block handling, `=` detection, close
state transition, mode selection for new vs existing tickets, test-mode
category forcing.

## Definition of done

As before; three commits (pure → cog inbound/reply → close/transcript/
management), not pushed. Owner's test sweep: enable, DM the bot, reply from
the ticket, `=` note, `/areply`, `/close reason`, read the transcript.
