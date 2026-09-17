# Staff reach — every channel the bot makes is the staff's to see and delete, and the BlackMail log

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **DESIGN, dispatching to Opus 2026-09-17 10:5x as branch `staff-reach`** (v120; §C added 10:5x — three site items the owner asked for the same morning). **Last verified: 2026-09-17
> 08:3x** against `main` `91bee8a`: the three overwrite builders named in §A were read in full
> (`cogs/community/tempvoice.py:382–420`, `events.py:1060–1076`, `cogs/moderation/modmail.py:691–701`), the
> role list and the two categories were read off the live guild by the bot token. ⚠️ Secret NAMES only.

## Owner asks, verbatim (2026-09-17, 08:2x–08:3x)

- *"Also for voice channels or any spawned channels make sure the permissions aren't above the aunties/uncles.
  They need to be able to delete channels too manually"*
- *"In black mail add a mod mail log like the other mod mail channel set has. Scan that channel and make sure we
  recreate all of those features"*

## What was measured

| Fact | Measured |
|---|---|
| **Aunties / Uncles** | role `1073711363337236601`, position 55, guild-wide **Manage Channels + Manage Roles**, no Administrator |
| Who counts as staff to the bot | `store.staff_roles(guild)` = the roles that can view `staff_channel_id` (`#blackbloc-logs` today), i.e. Aunties / Uncles, plus admin roles (Leads, Bots) |
| Temp voice room overwrites | `owner_overwrites`: the category's, `@everyone` denied view when **hidden** / connect when **locked**, the allowed role (Member) view+connect, the bot, the owner. **No staff allow** — a hidden room is invisible to Aunties / Uncles, so they cannot reach it to delete it |
| The lobby | `creator_overwrites`: the category's + the allowed role + the bot. Staff see it today only because *The Basement* allows them |
| Event review rooms | `review_overwrites`: `@everyone` denied, **staff roles view+send**, the bot manage, the requester. Reachable; deletable only because the role carries Manage Channels guild-wide |
| Ticket channels | `ticket_overwrites`: same shape as review rooms |
| Incumbent **ModMail** category | `1442613057628012594`: Aunties / Uncles allow `117824` (view, send, react, embed, attach, history), `@everyone` deny view. Channels: `#modmail-log` + one channel per open ticket (topic *"ModMail Channel <user> <thread> (Please do not change this)"*) |
| Incumbent `#modmail-log` | 6 messages, all by the ModMail bot, all one shape: embed **New Ticket**, footer `<name> \| <user id>`, no fields. Nothing else is logged there (closes go nowhere visible, or those six tickets are all still open — all six ticket channels exist) |
| **BlackMail** | made 08:3x as `1550166808869478420`, overwrites cloned from ModMail; `#modmail-log` inside it `1550167775694037075`, overwrites cloned from the incumbent's log. `modmail_category_id` → BlackMail (set by the session). ⚠️ `modmail_log_channel_id` is **still `#blackbloc-logs`** — the session's write was refused by its own permission classifier, so the owner sets it on the Settings page (modmail ▸ *The transcripts channel* → BlackMail's `#modmail-log`); it is safe under `TEST_MODE` because `post_transcript` writes a `modmail.would_post_transcript` row instead of sending while the guard refuses the channel |

## A. Staff reach on every channel the bot makes

**Rule.** Every channel Black Bloc creates carries an explicit overwrite for each of `store.staff_roles(guild)`:
`view_channel`, `manage_channels`, and for voice `connect`, on top of whatever else the builder sets. A room the owner
hides or locks stays hidden and locked to members and stays open to staff. The allow is added LAST so nothing the
builder does afterwards takes it back.

**Key.** `spawned_channels_staff_reach` — bool, **default true**, namespace core (beside `staff_channel_id`), help:
*"true gives the staff roles view + manage on every channel Black Bloc makes (temp voice rooms and the lobby, event
rooms, ticket channels), so a hidden room is still theirs to open or delete by hand; false leaves each builder's own
permissions"*. Registry + mock contract row.

**Where.** One helper, one home — `black_bloc/spawned.py` (new, small): `staff_reach(overwrites, staff_roles, *,
voice: bool) -> overwrites`. Called from:
- `cogs/community/tempvoice.py` `creator_overwrites` and `owner_overwrites` (voice=True) — the lobby and every room;
  also on the **repair** path (`repair_creator_channel` edits the lobby's overwrites) and wherever a room's
  overwrites are re-set (lock / hide / unhide / hand over — grep `edit(overwrites=` and `set_permissions`); the
  staff allow must survive every one of those edits.
- `events.py` `review_overwrites` (voice=False) — adds `manage_channels` to the staff allow it already has.
- `cogs/moderation/modmail.py` `ticket_overwrites` (voice=False) — same.
The helper reads nothing itself; callers pass `bot.store.staff_roles(guild)` and the key's value (a `False` key
returns the overwrites untouched).

**Tests.** The helper both ways; each builder with the key on (the staff role's overwrite has view + manage, connect
for voice; the member-facing denies are unchanged) and off (unchanged from today); the lock/hide/unhide paths keep
the staff allow. Tests mirror the package.

**Not in scope.** Channels the bot did not make (the BlackMail category itself was made by hand with the token —
its overwrites already allow the role). Changing what "staff" means (that is `staff_channel_id`).

## B. The BlackMail log — parity with the incumbent, which is one card

**Rule.** When a ticket opens (any door: DM, `/modmail`, the posted button, staff *Open a ticket with…*), post one
card to `modmail_log_channel_id`: title **New ticket #<id>**, the member's display name and id, the door
(`source`), who opened it when it was staff, the first line of the subject if the modal gave one; footer
`<name> | <user id>` like the incumbent's so staff searching the channel find the same thing. The card is posted the
way `post_transcript` posts — through the guard, writing `modmail.would_log_open` with the channel id while
`TEST_MODE` refuses the channel, and `modmail.log_open_failed` (never a raise) when Discord refuses. Closing already
posts the transcript there; nothing changes on close.

**Key.** `modmail_log_on_open` — bool, **default true**, namespace modmail, help: *"true posts a New-ticket card to
the transcripts channel the moment a ticket opens (what the old ModMail bot's log did); false logs opens only in the
action log"*. Registry + mock contract row. The action-log row `modmail.opened` stays as it is.

**Tests.** A ticket opened through each door with the key on posts the card once (and once only — the DM and the
staff doors share `open_ticket`; assert on the call count); with the key off nothing is posted; under the guard the
would-row is written and nothing sent; a refused send is a log row, not an exception, and the ticket still opens.

## C. Three site items folded in (owner, 2026-09-17 09:3x–10:0x)

1. **Every channel picker shows the category** (owner rule, verbatim: *"Yes good fix. All channel drop-selects should include a category for less confusion."* — after he saved the wrong of two `modmail-log`s). One home: `site/public/assets/ui.js` `channelLabel` reads `#name · Category` (the kind glyph as today, then the name, then ` · ` and the parent category's name from `/api/ref/channels`' `parent_id`; a channel with no category shows the name alone; a category row itself is unchanged). Every `channelSelect` caller inherits it — check `page-polls.js`, the posts target, the guides editor, the settings rows, the tempvoice/honeypot pickers — and the `keepUnlisted` fallback label stays `<said> · <id>`. One test in whatever covers `ui.js` labels (if none exists, a small `site/mock` check that the label contains ` · ` for a channel with a parent).
2. **The ended go-live wording gets the same editor as the live one** (owner: *"i see how to edit the go live but not how to edit the eding stream message"*). On `golive.html` under **Announcement wording**, a second `templateEditor` block **Once the stream is over** for `golive_end_template` and, beneath it, a one-line editor for `golive_end_author`, both with the placeholder list (`{name} {game} {title} {url} {platform} {duration}`), the same save bar and the same as-you-type preview the live block has; the **Wording** card sits directly under both and refreshes on their save (hook `templateEditor`'s save through the `onSaved` it lacks — add it, that is the gap the golive-end build's deviation 8 named). The two settings rows on the right stay (they write the same keys).
3. **KI-28 — blank from Discord.** In `cogs/core.py` the key modal's `TextInput` is `required = key not in settings_store.TEXT_MAY_BE_BLANK`; an empty submit for those keys stores `""` through the same PUT path the website uses. One test. Close KI-28 in `KNOWN_ISSUES.md` (keep the entry, mark `CLOSED` with the date and the commit).

## Deviations

*(the build agent writes here what it had to do differently, dated)*
