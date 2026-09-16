# Modmail doors — a member half of `/modmail`, a posted Open-a-ticket button, and staff opening a ticket with a member

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **DESIGN, dispatch queued behind
> the Posts build** (both touch `settings_store`, `logkinds`, `contract.json`, `tests/test_bot.py`).
> Owner, 2026-09-16 16:1x–16:3x, verbatim: *"is there a way for a user to do /modmail to start a mod
> mail? can we also have a channel where the modmail can be started with a ticket button like some bots
> have"* → *"let mods also be able to make a modmail with /modmail make it a button"*. Research and
> sources: [`modmail-doors-research.md`](modmail-doors-research.md). **Last verified: 2026-09-16 16:35**
> — §A read off `main` at `64d33c9`. ⚠️ **NOT checked:** nothing here met Discord; `deliver_dm`'s
> failure path is the one line §C4 tells the build to confirm.

## A. What exists (measured)

| Fact | Where |
|---|---|
| The only member door is a DM: `Modmail.on_message` → `_inbound` finds or opens the member's ticket (`_open_or_find`, one open ticket per member by a partial unique index), relays the text, DMs refusals with a cooldown (`DISABLED_DM`, `BLOCKED_DM`, `CANNOT_OPEN_DM`) | `cogs/moderation/modmail.py:1518–1600`, `storage/db.py` |
| `/modmail` is staff-only: root (Setup…, Blocked…, Snippets…, Forget…, A ticket…, Try a fake ticket, Logs, Open on the site) and the ticket card (Reply · Reply as Staff · Private note · Close…) | [`modmail-panel-design.md`](modmail-panel-design.md) §B–§C |
| Tickets carry a `source` (`dm`, `practice`); replies carry `source` too, and the card and the Modmail page show it | `black_bloc/modmail.py` `SOURCES`, `modmail-panel-design.md` §F |
| A persistent button that survives restarts is a `DynamicItem` (`RequestButton`, `BanNowButton`, the sticky card) | `panels-program.md` P14 |
| A posted-and-movable panel message with Post it / Move it… / Take it down is the role-menu shape | `rolemenu_panels.py` |
| Five-field `Label` modals are already built here (`NewPollModal`) | `modmail-panel-design.md` §C |

## B. The decision in one paragraph

Three new doors onto the SAME ticket: a member who runs `/modmail` gets a small private panel with
**Open a ticket** (or a line naming the ticket they already have); a staff-placed **Open a ticket**
message sits in a channel of staff's choosing with one persistent button; and the staff `/modmail`
root gains **Open a ticket with…**, which picks a member and opens the ticket for them. Every door
goes through a two-field form and then the exact path a DM takes today, so the card, the relay, the
transcript and the close do not fork. Every reply to a press is ephemeral. The DM door does not change.

## C. The pieces

### C1. `TicketModal` (one class, three callers)

Fields: **What is this about** (short, optional, ≤ 100) and **Tell us what is happening** (paragraph,
required, ≤ 1900). On submit, in order: `modmail_enabled` off → refuse in words (the `DISABLED_DM`
sentence, ephemeral); blocked → the `BLOCKED_DM` sentence; an open ticket already → *"You already
have an open ticket: <#…>"* (the channel or thread mention) and **nothing new**; else
`_open_or_find` → the paragraph becomes the first inbound row through the same `add_message`/relay
call a DM uses, with the subject as the ticket's `topic`-line prefix where the mode has one, and the
reply *"Your ticket is open: <#…>. Staff will answer there, and by DM."* — ephemeral. A `source` value
per door: `command`, `panel`, `staff` (added to `SOURCES`; the card and the Modmail page show it as
they show `dm`).

### C2. The member half of `/modmail`

`/modmail` stops being staff-only in `command_visibility`/`is_staff_command`; the cog splits on
`store.is_staff` exactly as `/request` does (`panels-program.md` P2). **Owner, 16:3x, verbatim:**
*"basically for modmail, anyone can make it, if youre a staff when you do a /modmail you see more than
just create and a modal with header and comment and stuff, you also see the other settings"* — so the
first row is the SAME for everybody: **Open a ticket** (→ the modal: header + comment) or, with a
ticket open, the line *"Your ticket is open: <#…>"* and no button; a member sees ONE ephemeral panel
with just that and a line ("Modmail is how you reach staff privately."); staff see that row and then
everything the staff root has today, plus **Open a ticket with…** (§C4). Nothing else: no
list, no logs, no site link (every `/api/modmail/*` route is staff-only). `modmail_panel_minutes`
governs it.

### C3. The posted Open-a-ticket panel

Staff `/modmail` ▸ **Setup…** gains **Ticket button…** → a `ChannelSelect` → the bot posts one message
(embed: `modmail_panel_title` / `modmail_panel_text`, two new text keys with sensible defaults) with
one persistent button **Open a ticket** (`TicketButton(DynamicItem)`, `custom_id` carries the guild
id). Stored as `modmail_panel_channel_id` + `modmail_panel_message_id` (two keys, both doors).
**Move it…** re-posts and deletes the old message; **Take it down** deletes it and clears the id;
`reconcile` on the 5-minute loop re-posts a message that was deleted by hand (`modmail.panel_gone` then
`modmail.panel_posted`) — the role-menu behaviour. Under `TEST_MODE` the guard refuses any channel but
the test channel in words (`modmail.would_post_panel`). Pressing the button runs `TicketModal` with
`source = panel`. The bot's reply is ephemeral, so nobody else in the channel learns who pressed.

### C4. Staff: Open a ticket with…

On the staff root, **Open a ticket with…** → a `UserSelect` → the same modal (the subject becomes the
ticket's first line; the paragraph is sent to the member as the FIRST staff reply through
`send_reply`, `source = staff`) → the ticket opens with `source = staff`, the member is DMed the
opening message exactly as a staff reply is DMed today, and the card carries *"opened by staff ·
@who"*. Refusals in words: the member is blocked (offer **Unblock them** — staff final say), the
member already has an open ticket (link it), the member is a bot. ⚠️ **The one line to confirm:** if
`deliver_dm` fails (DMs closed), the ticket still opens and the card says the member could not be
reached — read `modmail.py:668` and say which it does today.

### C5. Keys (checklist 33), group `modmail`

| Key | Type | Default | Help |
|---|---|---|---|
| `modmail_member_command` | bool | **true** | whether a member running `/modmail` gets the Open-a-ticket panel (off = the old staff-only behaviour) |
| `modmail_panel_channel_id` | channel | blank | where the Open-a-ticket message is posted (blank = no panel) |
| `modmail_panel_message_id` | int | blank | the posted message (written by the bot) |
| `modmail_panel_title` | text | `Need a moderator?` | the panel's heading |
| `modmail_panel_text` | text | `Press the button and tell us what is happening. Only staff see it.` | the panel's body |

Per-ticket `source` needs no key. Registry +5.

### C6. Log kinds

`modmail.opened` gains `source` in its details (no new kind); new: `modmail.panel_posted`,
`modmail.panel_moved`, `modmail.panel_taken_down`, `modmail.panel_gone`, `modmail.would_post_panel`,
`modmail.opened_by_staff` (important), `modmail.open_refused` (routine, with the reason word).

### C7. The website

The Modmail page's Setup section gains the panel channel + the two texts (settings rows, generated)
and a **Post the ticket button** / **Take it down** pair beside them (one route each:
`POST /api/modmail/panel`, `DELETE /api/modmail/panel`, `via=website`); the ticket table's `source`
column shows `command` / `panel` / `staff`. Contract + mock + `check.mjs`.

## D. Calls the owner may overturn

1. The member half is on by default → the key.
2. The panel's wording → the two text keys.
3. A subject field at all → drop one field from the modal.
4. Staff-opened tickets DM the member the opening message → one flag in §C4.

## E. Out of scope

Claim/assign; ticket categories (a select of types); auto-close on inactivity; a second open ticket
per member; anything in the DM path; the practice ticket (unchanged).

## F. Build brief essentials

One Opus build, worktree `C:/lcw/bb-modmail-doors`, branch `modmail-doors`, off `main` AFTER the Posts
merge. Est. **180–260k**. Tests mirror: `tests/cogs/moderation/test_modmail.py` grows the three doors
(member panel both states; the panel button; staff open with a blocked member, with an open ticket,
with DMs closed), `tests/test_command_visibility.py` (`/modmail` member-visible now),
`tests/api/tools/test_modmail.py` the two routes, `tests/test_bot.py` counts unchanged (30 commands
after Posts). Prove: a press never posts a public reply (assert every response is ephemeral); the
second press links the open ticket and opens nothing; the panel re-posts after a hand delete; the
`deliver_dm` finding written into `## Deviations`. Sweep rows `MD-a`…; `code-notes.md` `# Modmail
doors`; the `modmail-panel-design.md` §B row that says "no member half" struck and rewritten
(checklist 35).

## Deviations

*(empty until the build lands)*
