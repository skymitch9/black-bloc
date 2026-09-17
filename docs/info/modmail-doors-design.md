# Modmail doors — a member half of `/modmail`, a posted Open-a-ticket button, and staff opening a ticket with a member

> **Audience:** the build agent and reviewers. **Status:** TRACKED · ✅ **LIVE as v114** — merge `04de842`, release `c279676`, deployed **2026-09-16 18:38** Phoenix (`../deploys.log`); landing entry in [`../DONE.md`](../DONE.md) (*"2026-09-16 — MODMAIL DOORS"*); the `## Deviations` foot is the truth where it departs from the body; sweeps **419–433** are the owner's; ⚠️ nothing in it has met Discord by a person. Was: ✅ BUILT on branch `modmail-doors`, off `main` `4d60f68` — NOT merged, NOT deployed.** Schema **37 → 38** (`modmail_tickets.source`, `.opened_by`) — ⚠️ **migrate before deploy**.
> Registry **+5**; mock **168 → 170 routes**; `pytest` **5839 → 5880**, both orders green. Read the
> `## Deviations` foot before the sections above: fifteen things differ from what is written here.
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

⚠️ **SUPERSEDED IN PLACE by the front door (branch `front-door`, 2026-09-17, design [`front-door-design.md`](front-door-design.md) §B).** The posted Open-a-ticket button is now ONE OF THREE buttons on a message that also files a request and proposes an event, and `frontdoor_replaces_ticket_button` (**true**) takes this message down while the front door is up in the same channel — one door per channel. ~~Nothing below changed:~~ the code, both keys and the reconciler are untouched; `modmail_panel_channel_id` keeps its value, so moving the front door away or taking it down puts this button back on modmail's own next five-minute sweep. Everything below still describes what this button does; it is simply no longer the only thing in that channel.

Staff `/modmail` ▸ **Setup…** gains **Ticket button…** → a `ChannelSelect` → the bot posts one message
(embed: `modmail_panel_title` / `modmail_panel_text`, two new text keys with sensible defaults) with
one persistent button **Open a ticket** (`TicketButton(DynamicItem)`, `custom_id` carries the guild
id). Stored as `modmail_panel_channel_id` + `modmail_panel_message_id` (two keys, both doors).
**Move it…** re-posts and deletes the old message; **Take it down** deletes it and clears the id;
`reconcile` on the 5-minute loop re-posts a message that was deleted by hand (`modmail.panel_gone` then
`modmail.panel_posted`) — the role-menu behaviour. ⚠️ **~~That deletion is the only reason it
re-posts.~~ SINCE v117** (2026-09-17, branch `blackmail-threads`) it ALSO re-posts when the post
named by `modmail_panel_follows_post` (**`welcome`** by default) lands under the button in the same
channel, so the button keeps sitting directly beneath the rules — a second reason, its own log kind
`modmail.panel_below_post`, and `none` to switch it off. The owner asked for it: *"I want it posted
right after the rules"*; the design is `blackmail-threads-design.md` §C. Under `TEST_MODE` the guard
refuses any channel but the test channel in words (`modmail.would_post_panel`). Pressing the button runs `TicketModal` with
`source = panel`. The bot's reply is ephemeral, so nobody else in the channel learns who pressed.

### C4. Staff: Open a ticket with…

⚠️ **~~Drawn on every staff root.~~ HIDDEN BY DEFAULT since v117** (2026-09-17, branch
`modmail-hide`) — the owner asked for the door kept but hidden (*"Let's keep but hide the open a
ticket with option on the bot. Toggleable of course."*). Everything below is what the door does
**once `modmail_open_with_button` is on**; off is the default and the button is not drawn. The
code is untouched, which is the point of a toggle rather than a deletion. See *Hide toggle
(v117)* in `## Deviations`.

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
| `modmail_open_with_button` | bool | **false** (v117) | true draws **Open a ticket with…** on the staff row of `/modmail`; false hides that door and leaves every other way in untouched |

Per-ticket `source` needs no key. Registry +5, and **+1** at v117 (the hide toggle).

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

> Written by the build, 2026-09-16, on branch `modmail-doors` off `main` `4d60f68` (v113).
> Everything below is a place the build did NOT do what §A–§F said, and why. ⚠️ **Nothing here
> has met Discord**: the whole verification is `pytest` (**5839 → 5880**, both orders), `ruff`,
> `node site/mock/check.mjs` (*19 pages, 170 routes, 14 core settings, all keys present*) and one
> pass over the Modmail page on the MOCK in a browser.

1. ⚠️ **A ticket had no `source` column, so this build is a MIGRATION — schema 37 → 38.** §A's
   table says *"Tickets carry a `source` (`dm`, `practice`)"* and the research doc says *"No
   schema change expected (the `source` column exists)"*. **Measured: false.** `modmail_tickets`
   carried `practice` and nothing else; `SOURCES` in `black_bloc/modmail.py` is the vocabulary a
   **reply** carries in its log details (`card` / `typed` / `command` / `web`), not a column.
   Two additive columns through the existing `ADDED_COLUMNS` / PRAGMA pattern:
   `source TEXT NOT NULL DEFAULT 'dm'` and `opened_by INTEGER`. **Migrate before deploy.** Every
   ticket older than the migration reads `dm`, which is right for every real one — the DM was the
   only door — and wrong only for old PRACTICE rows, which the `practice` flag still identifies.
2. **`SOURCES` was not widened; `TICKET_SOURCES` is a second tuple.** §C1 says the three new words
   are *"added to `SOURCES`"*. `tests/test_modmail.py::test_the_four_sources_a_reply_can_come_from_are_named_once`
   asserts `SOURCES == ("card", "typed", "command", "web")` by name, and a reply source and a
   ticket source answer different questions. So `TICKET_SOURCES = (dm, command, panel, staff,
   practice)` sits beside it, `command` is the one word both use, and the reply test is unchanged
   — which is the proof nothing moved.
3. **`modmail_panel_message_id` is a `text` key, not `int`** (§C5's table says int). Two reasons,
   the second found in a browser: `api/settings_api.py:66` already says *"Ids leave as strings,
   because a snowflake does not survive a JavaScript number"* — a message id is ~1.4e18 and
   `Number.MAX_SAFE_INTEGER` is 9.0e15, so an `int` key would hand the dashboard a mangled id;
   and while it was `int`, the mock returned the value as a string, the int editor read it back
   with `Number()`, and the row sat permanently **CHANGED** with *"1 change pending"* on every
   load — the third instance of the family `code-notes.md` `# Settings editor — the false "1 change
   pending"` records. The bot writes `str(message.id)`; `panel_where` is the one place it is
   `int()`ed back.
4. **The member's reply carries no channel mention, the staff one does.** §C1's sentence is
   *"Your ticket is open: <#…>"*. A ticket channel's overwrites deny `@everyone`, so for a member
   that mention renders as an unclickable unknown channel — a dead link is worse than no link.
   A member is told the ticket number and that replies come back by DM; **Open a ticket with…**
   and *"they already have one"* keep the mention, because staff can see it.
5. **The member panel does not draw a button the modal would refuse.** §C1 orders the modal's
   refusals (off → blocked → already open). It keeps all three, because a door can close while a
   panel is open — but P3 says no state renders a control whose shared function would refuse it,
   so the panel itself draws **Open a ticket** only when modmail is on, the member is not blocked
   and has no ticket, and says which of the three it is in words instead.
6. **A member door also DMs the opening line, and says so when the DM bounces.** The DM path
   sends `opening_dm` when it opens a ticket; the command and the button do the same through the
   same `deliver_dm`. ⚠️ **A member whose DMs are shut still gets a ticket** — that is the point
   the research doc asked about — and the ephemeral reply then carries *"Black Bloc could not DM
   you, so open DMs from this server or staff's replies will not reach you."*, because a ticket
   whose replies can never arrive is worth saying out loud.
7. ⚠️ **`deliver_dm`, the line §C4 told the build to confirm.** `cogs/moderation/modmail.py`
   `deliver_dm` **returns the reason as a string and raises nothing**; `ticket_dm` wraps it
   (a practice ticket short-circuits to `None`) and `send_reply` does the rest: the row is marked
   `delivered = 0`, `modmail.dm_failed` is logged, and a `⚠️ Black Bloc could not DM the member`
   line is spoken **into the ticket**. So a staff-opened ticket with DMs shut **opens, keeps the
   words, and reports the failure** — nothing rolls back. The card now says so too: `last_reply_missed`
   reads the newest OUT row and `ticket_card_lines` adds *"⚠️ The last reply did not reach them"*.
8. **The staff door writes `modmail.opened_by_staff` INSTEAD of `modmail.opened`, not beside it.**
   §C6 lists both. One act leaves one row (checklist 34's whole point); the two kinds carry the
   same details, and the staff one is IMPORTANT while `modmail.opened` is ROUTINE — which is the
   only reason the second kind exists.
9. **Ticket button… is its own sub-panel, not a select on `Setup…`.** §C3 says Setup gains
   **Ticket button…** → a `ChannelSelect`. Setup's own rows already hold five and four buttons;
   adding a select plus **Move it…** plus **Take it down** does not fit inside Discord's five per
   row. It is the `Blocked…` / `Snippets…` shape instead: **Ticket button…** opens a surface
   that says where the button is and what it says, and draws **Post it…** *or* **Move it…** +
   **Take it down** — never both spellings of one move.
10. **Take it down clears BOTH keys.** §C3 says it *"deletes it and clears the id"*. Clearing only
    the message id leaves the channel pointed, and the five-minute reconciler would put the button
    straight back — "down" would last five minutes. Both keys go; posting again names a channel.
11. **The reconciler's guard refusal is logged ONCE per guild per process.** Checklist 1 wants a
    `would_` row where a side effect is refused, but the reconciler runs every five minutes, so a
    button that cannot be re-posted under `TEST_MODE` would write `modmail.would_post_panel`
    twelve times an hour forever. The cog keeps a `_panel_shadowed` set, cleared the moment a post
    succeeds. The deliberate doors (Setup…, the website) log every time, because somebody is
    waiting for the answer.
12. **The root panel's rows moved down one.** The doors row is row 0 (**Open a ticket**, **Open a
    ticket with…**), the ticket select is row 1, today's five moves are row 2 and the tail
    (Logs · Refresh · Open on the site) is row 3 — four rows of at most five, measured by a test.
    `root_buttons` re-rows its own moves, so the label table still has one home.
13. **A subject heads the paragraph AND prefixes the channel topic.** §C1 asks for the topic-line
    prefix, which only channel mode has. `first_message` makes the stored message
    `**{subject}**\n{paragraph}` so a thread-mode ticket and the transcript keep it too, and
    `ticket_topic(user_id, ticket_id, subject)` puts it in front of the topic — `parse_topic`
    uses `search`, so the ids are still found (asserted).
14. **The website's Ticket button is its own card above the settings rows**, not a pair of buttons
    inside the Setup section — the Modmail page has no Setup section, it has `namespaceSettings('modmail')`,
    which generates the five new rows for free. `DELETE /api/modmail/panel` answers **200** with
    `taken_down: false` when nothing is up, rather than a 404: taking down nothing is not an error,
    and the flag plus the sentence keep the two apart.
15. **The mock's ticket rows carry a `source` each** (`dm`, `panel`, `staff`) so the page's new
    column has something to show, and the seed's staff row carries `opened_by`.

### Hide toggle (v117) — written 2026-09-17 on branch `modmail-hide` off `main` `91bee8a` (v116)

Owner, 2026-09-17 08:3x, verbatim: *"Let's keep but hide the open a ticket with option on the
bot. Toggleable of course."* One key, `modmail_open_with_button` (bool, **default false**,
namespace `modmail`, registry 225 → **226** on this branch — ⚠️ measured against `91bee8a`, and
`main` gained `tempvoice_room_overwrites` at `255974c` while this was building, so the merged
count is one higher again). What it changes, and the three things it does not:

1. **`door_buttons` gained `open_with: bool = False`** rather than reading the store itself —
   `black_bloc/modmail.py` is the pure half and stays pure, so the flag is tested both ways with
   no fakes. `build_root` is the one caller that reads the key, through
   `cogs/moderation/modmail.py:open_with_on(store, guild_id)` — one reader, so the button, the
   picker and the modal cannot disagree.
2. ⚠️ **Three stale windows, not one.** A panel opened while the door was on keeps its button; a
   `UserSelect` already on screen keeps answering; and a `TicketModal` already open submits into
   `open_a_ticket`. All three are gated, in that order: `run_open_with` (the press),
   `open_with_refusal` (the pick, ahead of the bot / disabled / blocked answers) and
   `open_a_ticket` itself (`staff_door and not open_with_on` → `refuse_open`, reason word
   `open_with_off`, so it leaves the usual quiet `modmail.open_refused` row). The last one is the
   only gate a ticket could otherwise slip past, because a modal is on the member's screen for as
   long as they leave it there.
3. **The refusal names the key and both doors back to it.** `OPEN_WITH_OFF` says what happened
   (the door is switched off), what it needs (`modmail_open_with_button` on) and how to get it
   (the dashboard's Settings page under **modmail**, or `/settings` ▸ **A setting group…** ▸
   modmail) — never a bare refusal, and never a button that would refuse (P3): with the key off
   the staff root simply does not draw it.
4. **Nothing was deleted and no web route moved.** `OPEN_WITH_MOVE`, `MemberPick`, `TicketModal`
   and the `staff` ticket source are all untouched; `open_a_ticket(source=SOURCE_STAFF)` has no
   caller outside this cog, so there is no website door to gate. The mock gained the settings row
   and `labels.js` the label, which is the dashboard half of checklist 33; the Discord half is
   the generated key card, proved by
   `tests/test_settings_panel.py::test_every_registry_key_resolves_to_exactly_one_control[modmail_open_with_button]`.
5. **`modmail-ticket` in `guides_seed.json` was NOT touched** — no step, fault or fact in it
   names **Open a ticket with…** (it is the ticket-card guide: Reply, Reply as Staff, note,
   close), so there was no sentence to qualify. The brief's "(only when `modmail_open_with_button`
   is on)" clause has no home today; if a guide ever names that door, it needs one.

**Measured on the branch:** `pytest -q -n auto` **5986 → 5993** (+6 written here, +1 the
parametrised `test_every_registry_key_resolves_to_exactly_one_control[modmail_open_with_button]`
the new key adds for free), green forward (44.1 s) **and** under `BB_REVERSE=1` (39.3 s);
`ruff check .` clean; `node site/mock/check.mjs` ok. ⚠️ Two reversed runs before that one stalled
mid-suite with the workers idle — **KI-26's hang, at 98 % under `-n auto` and at 81 % serial**,
and the serial stall is worth the entry knowing: it is **not** an xdist-only shape.

⚠️ **NOT verified, this change:** nothing met Discord — no boot, no token, no press, no DM;
`TEST_MODE` was never flipped and nothing was deployed. No browser saw the Settings page, real or
mock; the mock was exercised only by `node site/mock/check.mjs` (*19 pages, 175 routes, 14 core
settings, all keys present*). Sweep rows 422 and 428–430 in `../access/sweeps.md` still tell the
owner to press **Open a ticket with…** on a staff `/modmail`; with the key shipping **off** he
must turn it on first, and those four rows were left for the conductor's landing ritual rather
than rewritten here.

### What was NOT verified

- **Nothing met Discord.** No boot, no token, no ticket opened, no button pressed in a client, no
  DM sent. `TEST_MODE` was never flipped and nothing was deployed.
- **The migration was not run against a copy of the live database.** `tests/storage/test_db.py`
  migrates a schema-29 file and reads `source == 'dm'` on a row written before the column, which
  is the same ALTER through the same pattern — but the live file was not touched.
- **The posted button has never survived a real restart.** `TicketButton` is registered in
  `cog_load` beside `TicketCardButton` and the reconciler re-posts a deleted message; both are
  tested with fakes only.
- **No browser saw the real site** — only `site/mock` at `127.0.0.1:8790`, as staff.
- **`/help`'s rendering of a member-visible `/modmail` was not looked at**, only asserted:
  `is_staff_command` answers False through the command's `extras`, which is what `cogs/core.py`
  reads for its staff suffix.
