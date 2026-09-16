# Modmail doors — how ticket bots open a ticket from a button or a command (research, 2026-09-16)

> **Audience:** the owner (to decide) and the session that designs the build. **Status:** TRACKED ·
> 🔎 **RESEARCH, nothing built.** Owner ask, 2026-09-16 16:1x, verbatim: *"is there a way for a user to
> do /modmail to start a mod mail? can we also have a channel where the modmail can be started with a
> ticket button like some bots have. do research on that and then get back to me"*. Researched by a
> Sonnet agent from the vendors' own docs and this repo's code; **Last verified: 2026-09-16 16:30** —
> the repo references were read at `main` `8cce7eb`; the vendor pages are as fetched that day.
> ⚠️ **NOT verified:** `docs.ticketsbot.net` did not resolve (its `.org` and `docs.tickets.bot` twins
> were used); Ticket Tool's on-click behaviour is not in its docs; no vendor documents what happens
> to a member whose DMs are closed; `modmail.py`'s `deliver_dm` was not read.

## Today

The ONLY member door is a **DM to the bot** (`cogs/moderation/modmail.py:_inbound`): the first DM
opens the ticket, later DMs land in it, refusals (modmail off, blocked) are DMed back with a cooldown.
`/modmail` is a **staff** panel with no member half, by design (`modmail-panel-design.md` §B).

## What the vendors do

| Bot | Door | On press | Second ticket | Privacy |
|---|---|---|---|---|
| **Ticket Tool** | a posted panel (one button, or up to 25 buttons on a "multipanel"); no member slash command documented | not documented (modal or immediate channel) | per-panel and global caps; the refusal wording is not documented | not documented |
| **TicketsBot** | a posted panel — one button, a dropdown of ticket types, or "thread mode" | a **modal first** (≤ 5 fields; text, selects, file, radio, checkbox), whose answers become the opening embed of the new channel | per-panel cap on open tickets | thread mode opens a private thread with no staff in it and a **Join ticket** button in a staff channel |
| **Modmail (modmail.dev)** | **DM only** — Discord's own safety page: "almost all modmail bots require a user to DM the bot" | DM → a channel in a category | one active thread per member | the DM *is* the privacy |
| 2026 round-ups (several) | panel + modal is now the norm | modal answers → opening embed | auto-close on inactivity (~48 h), transcript on close | an **ephemeral** "your ticket is open" reply, because a public reply names the member |

Discord has no ticket primitive; every bot builds it from channels or private threads plus overwrites.
Nobody documents a special path for a member whose DMs are closed.

## The choices that matter here, with the recommendation

1. **Keep the DM door exactly as it is.** It is the one door where a member's name never touches a
   public channel, which is what the vendors' ephemeral replies are approximating after the fact.
2. **Give `/modmail` a member half**, the way `/request` has one: a member who runs it sees either a
   line naming their open ticket, or one button, **Open a ticket**. The staff panel is untouched.
3. **A posted "Open a ticket" panel message**, placed by staff from `/modmail` ▸ **Setup…** into a
   channel of their choosing, moved and taken down the way role-menu panels are; a persistent button
   that survives restarts (the same `DynamicItem` shape the sticky ticket card uses).
4. **Modal first, like TicketsBot**, two fields: *What is this about* (short, optional) and *Tell us
   what is happening* (paragraph, required). The paragraph becomes the ticket's first message through
   the same path a DM takes, so the card, the relay, the transcript and the close do not fork.
5. **A second press says so**: "You already have an open ticket: #…" — an interaction can answer where
   a second DM today silently lands in the existing ticket.
6. **Every reply is ephemeral.** Discord does not tell other viewers who pressed a button; the only
   way a press goes public is the bot's own reply, so it never posts one.
7. **No claim/assign.** Not asked for, and "staff final say" argues against restricting who may reply.

What stays as it is: `modmail_mode` (channel / thread), the sticky card and its four buttons, close
and transcript, one open ticket per member (the existing unique index), every settings key. New: one
`source` value per door (`command`, `panel`) beside `dm`, so the card and the Modmail page say where a
ticket came from; one key for the panel's channel; one for the panel's wording.

## Limits that bite

A modal holds five classic fields (this repo already builds five-field modals). A panel button must be
a persistent item, not a timed view. Private threads and channels are visible only to those granted —
the modes already do this. A member with DMs closed can still OPEN a ticket through either new door,
which is better than today; whether the "your ticket is open" DM failing blocks anything is the one
line the build must confirm in `deliver_dm`.

## Estimate, if built

One Opus build, ~150–220k: the modal, the member half, the panel item + Setup move, the `source`
value, two keys, tests, sweep rows. No schema change expected (the `source` column exists).
