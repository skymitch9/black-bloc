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

> Written by the build, **2026-09-17**, on branch `staff-reach` off `main` `4da192c`, in the
> worktree `C:/lcw/bb-staff-reach`. Everything §A, §B and §C ask for is built. What is below is
> every place the build did something the design did not say, or did not do something it did.
> ⚠️ **Nothing here has met Discord.** The whole verification is `pytest -n auto` (**6144 → 6175**,
> and 6175 again under `BB_REVERSE=1`), `ruff check .` (clean), the ES-module parse of every
> `site/public/assets/*.js`, `node site/mock/check.mjs` (*19 pages, 178 routes, 15 core settings,
> all keys present*), `node site/mock/discordmd.test.mjs`, the new `node site/mock/labels.test.mjs`,
> and **one browser pass against the mock** (`node site/mock/server.mjs`, `golive.html` and
> `modmail.html`) — no Discord button was pressed, no channel was created, and
> `python -m black_bloc` was never booted. `TEST_MODE=true` was not touched and no settings key was
> flipped.

### §A — the staff allow

1. ⚠️ **§A's own measurement was already false for temp voice, and the gap it describes is
   narrower than it says.** *"Temp voice room overwrites … **No staff allow** — a hidden room is
   invisible to Aunties / Uncles"* is true of `owner_overwrites` read alone, but not of what it is
   called with: `join_roles` (`cogs/community/tempvoice.py:716`) has returned
   `store.staff_roles(guild)` since `178fe69` (2026-08-26) and the caller passes it as `allow=`,
   so the staff roles have had an explicit **view + connect** on the lobby and on every spawned
   room all along — a hidden room was already visible to them. What §A actually adds for temp
   voice is **`manage_channels`**, plus an allow that no longer depends on the allowed-role
   plumbing. The owner's ask still lands (staff can delete a room from Discord's own UI without
   relying on the role's guild-wide Manage Channels), but the *"they cannot reach it"* half of the
   finding did not reproduce.
2. **There is a second function in `spawned.py`: `reach_roles(bot, guild, roles=None)`.** §A says
   the helper reads nothing and the callers pass the key's value. Five call sites each reading the
   key is five places to forget it, so the key is read once, in the one place that also resolves
   the roles; `staff_reach` itself stays pure and testable, exactly as §A asks. `roles=` lets
   `events.py` and `modmail.py` hand in the staff roles they have already resolved for their own
   view+send allow rather than resolving them twice.
3. **`review_overwrites` and `ticket_overwrites` take `reach=` as a SECOND parameter beside
   `staff_roles`.** The existing `staff_roles` allow (view + send) is what makes a review room or a
   ticket usable and is not the key's business. One parameter for both would have meant that
   turning `spawned_channels_staff_reach` off also took staff's *view* of a ticket away, which is
   not what the key says it does.
4. **The lock / hide / unhide / ban / permit / hand-over paths needed no change at all, and that is
   a measurement, not an assumption.** Every one of them is
   `channel.set_permissions(<one target>, …)` against `@everyone` or one member — never a
   whole-dict rewrite — so none of them can take the staff allow back. The only path that rewrites
   the dict is `repair_creator_channel`, which builds it through `creator_overwrites` and therefore
   gets the allow back; `adopt_creator_channel` delegates to it. `apply_remembered_members` runs
   *after* `owner_overwrites` returns but writes member keys only, which a test now pins.
5. **Three channels the bot makes are deliberately NOT covered:** the honeypot trap
   (`cogs/moderation/honeypot.py`), and the modmail and requests **forums**. §A names three
   builders and these are not among them; the trap is `@everyone`-visible by design (there is
   nothing to be shut out of), and both forums are created from a copy of the BlackMail category's
   own overwrites, which the design's own table measured as already allowing the staff role
   (`117824`). Say the word and they are one `staff_reach(...)` call each.

### §B — the New-ticket card

6. **`log_open` is the LAST thing `open_or_find` does**, after the ticket row, the place, the
   `modmail.opened` row and the header (checklist 12). It returns a reason string and never raises,
   so a refusal cannot cost anybody their ticket. It is not gated on the mode or on the door,
   because `open_or_find` is the one place all four doors meet — which is what makes "once and once
   only" structural rather than something four call sites have to remember.
7. **A missing transcripts channel writes `modmail.log_open_failed` with `no_log_channel`**, once
   per ticket, exactly as `post_transcript` writes `modmail.transcript_failed`. §B only names the
   guard and the Discord refusal. Silence was the alternative and it is worse: a guild whose card
   goes nowhere should be able to see that on the Logs page.
8. **A successful post writes NO log row.** §B asks for the two failure kinds and says
   `modmail.opened` stays as it is; `modmail.opened` already records the open, so a second
   "and we logged it" row would be noise. Neither new kind needed registering in `logkinds` —
   `_failed` is an `IMPORTANT_SUFFIXES` entry and `would_` is the shadow prefix.
9. **A PRACTICE ticket gets no card.** `open_practice` has its own path and never reaches
   `open_or_find`. The incumbent's log holds real tickets only, and a practice ticket exists to be
   thrown away.
10. ⚠️ **Two existing tests changed, and the change is real behaviour, not a test fix.**
    `modmail_log_channel_id` still defaults to the test channel, so under the guard the card is
    genuinely sent — `test_the_relay_lands_in_the_test_channel_while_the_guard_is_on` now expects
    `["Ticket #1", "New ticket #1", "From the member"]`, and
    `test_with_the_guard_lifted_a_ticket_talks_in_its_own_channel` no longer asserts the test
    channel is empty, because the transcripts channel is where the card goes. ⚠️ **In the live
    guild this means a New-ticket card in `#blackbloc-logs` from the first boot after this
    deploys**, until the owner points `modmail_log_channel_id` at BlackMail's `#modmail-log` (the
    click the design's own table already says is his).

### §C — the three site items

11. ⚠️ **`/api/ref/channels` carries `category_id`, not `parent_id`.** §C.1 names `parent_id`;
    measured, `api/names.py:channel_row` emits `category_id` and `contract.json` lists it. The
    label reads the field that is there; nothing was added to the route.
12. **`channelLabel` moved to `labels.js` and is re-exported by `ui.js`.** §C.1 says the one home
    is `ui.js`. `ui.js` cannot be imported outside a browser (it reaches `document` through
    `api.js` at import time), so a test of it was impossible, and §C.1 asks for a test. `labels.js`
    is a leaf and already owns *what a thing is called*. New `site/mock/labels.test.mjs` covers the
    six cases, and it is registered in **`scripts/deploy.ps1`** and **`.github/workflows/ci.yml`**
    beside `discordmd.test.mjs` — a test nothing runs is not a test. Those two files were not on
    the brief's list; the change to each is two lines of registration.
13. **`page-events.js`'s Where picker was the only hand-rolled channel label left, and it now calls
    `channelLabel` too.** Visible change beyond the category: a space after the `#`, which every
    other picker on the site already has.
14. **The mock grew one channel** — a second `modmail-log`, inside the `modmail` category. Every
    mock channel had `category_id: null`, so the mock could not show the thing §C.1 is for; the new
    row is the owner's own confusion case, and it is what the browser pass looked at.
15. **`templateEditor` now takes a LIST of specs, an `onSaved`, and a per-spec `editorType`.** §C.2
    asks for a second editor block *and* a one-line editor *and* one save bar *and* the `onSaved`
    hook. A second `templateEditor` call would have docked a second save bar for one decision, so
    both ended keys go through one call: the template as a textarea, the author as a one-line input
    (`editorType: 'text'`), one bar reading *Once the stream is over*, and `paint(filled, key)` so
    one painter serves both rows. Checklist 35: this closes the gap
    `golive-end-design.md` deviation 8 recorded, and that bullet is struck and dated there, as is
    deviation 3's *"the Discord side … is NOT closed"*.
16. **An empty ended box previews what blank MEANS, rather than going blank.** Blank is a real
    value for these two keys, not an unfinished edit, so the preview says *"the live sentence is
    kept and golive_end_suffix is added"*. The **Wording** card underneath remains the one home for
    what the bot has actually stored (golive-end deviation 7 stands), and its own help line was
    rewritten: it used to tell the reader to press Refresh after every save, which the `onSaved`
    hook has now made wrong.
17. **KI-28's fix imports `TEXT_MAY_BE_BLANK` straight from `settings_store`.** Re-exporting it
    through `settings_panel` (which `cogs/core.py` reads as `sp`) would have been an unused import
    there and `ruff` says so.

### What was NOT done

18. `docs/TODO.md`, `docs/DONE.md` and `docs/deploys.log` were not touched. Nothing was merged,
    deployed, or pushed to `main`. No settings key was flipped — `spawned_channels_staff_reach` and
    `modmail_log_on_open` both ship **true**, which is their design default, and every other key is
    as it was.
19. Nothing was proved against live Discord or the live dashboard. The browser pass was against
    `site/mock/server.mjs` only, and it looked at two things: the ended-wording editor with its
    preview on `golive.html`, and a channel dropdown on `modmail.html` reading
    `# modmail-log · modmail`. Sweep rows `SR-a` … `SR-l` in `docs/access/sweeps.md` are what is
    left to walk.
20. `pytest -n auto` did **not** stall once in this build, forward or reversed — KI-26's count
    stands at seven.
