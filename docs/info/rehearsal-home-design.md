# The rehearsal home — one channel where every shadow copy lands, so staff can review before the cutover

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **DESIGN, dispatching to Opus 2026-09-17 16:2x as
> branch `rehearsal-home`** (v129). **Last verified: 2026-09-17 16:16** against `main` `fbc4a48`: `black_bloc/shadow.py`
> (`channel_id` = the guard's channel else `log_channel_id`; `channel_ids` = every place a copy could be),
> `black_bloc/guard.py` (`allows_channel` = the test channel, DMs, owned channels), `black_bloc/posts.py` (the shadow
> copy through `shadow_home`), `black_bloc/cogs/community/frontdoor.py` (`WOULD_POST` — the door writes a would-row
> under the guard and posts nothing), the ticket button (`cogs/moderation/modmail.py` `_repanel` → `modmail.would_post_panel`),
> polls in shadow (`poll.opened_shadow` into `shadow.channel_id`). The live guild: `#welcome-test`
> `1550284332365783091` made 16:16 under The Basement with `#blackbloc-logs`' overwrites (staff see it). ⚠️ Secret NAMES only.

## Owner ask, verbatim (2026-09-17 16:1x)

*"put the new ticket button and the rules post the bot will be making in a welcome test channel in the basement
category. I want the mods to test stuff for me and review what the rules output will look like"*

## What blocks it today (measured)

| Piece | Under `TEST_MODE` today |
|---|---|
| The welcome/rules post (`posts_mode = shadow`) | the real message is posted into **the guard's channel** (`#blackbloc-logs`) — `shadow.channel_id` |
| The front door | `frontdoor.would_post` — a log row, **nothing posted** |
| The ticket button (`modmail_panel_*`) | `modmail.would_post_panel` — a log row, nothing posted |
| Polls in shadow | posted into the guard's channel |
| The guard | lets the bot speak only in the test channel, DMs, and channels it made (`owned_channel_ids`) |

So the mods cannot review any of it in a channel of their own, and `#blackbloc-logs` is a stream of everything else.

## A. One key: `shadow_channel_id`

`shadow_channel_id` — channel, default **blank**, namespace `core` (beside `log_channel_id`), help: *"where every
rehearsal goes while a feature is in shadow — the welcome post, the front door, the ticket button, polls; blank means
the bot's own log channel"*. Registry + mock row + label.

`black_bloc/shadow.py` `channel_id(bot, guild)` returns it first when set; `channel_ids` includes it (a copy may
already be there when the key changes). **Every** rehearsal path that asks `shadow.channel_id` follows for free —
posts and polls do today. ⚠️ Changing the key does not move copies already up (the posts reconcile re-posts its
copy where `channel_ids` finds it; say what polls do).

## B. The guard lets the bot speak there

`TestModeGuard.allows_channel` also allows the channel `shadow_channel_id` names — read through the store each time
(`self.bot.store.get(guild_id, "shadow_channel_id")`; the guard has no guild in hand, so `allows_channel` checks
the id against every guild's value, or the bot registers it: pick the simplest that has a test — a `store.on_change`
hook that calls `guard.own_channel` / `disown_channel` is the shape the tempvoice shadow build used, and boot
seeds it). `allows_place` is NOT widened (nothing is deleted there by the bot except its own copies, which are
messages, not channels). The boot `WARNING` names it. ⚠️ The key is the deliberate act that widens test mode by one
channel; the design says so in the help text.

## C. The front door and the ticket button gain a real rehearsal copy

- **Front door:** while the guard refuses `frontdoor_channel_id`, the door posts its REAL message into the rehearsal
  home instead of writing `would_post` — the posts feature's shape: `frontdoor_shadow_message_id` (text) remembers
  the copy, the reconcile keeps it (re-posts if deleted, edits when the wording keys change, takes it down when
  `frontdoor_mode` is off), the log row is `frontdoor.posted_shadow` with both channel ids. The three buttons WORK on
  the copy (they are dynamic items; a press opens the real flows, which are themselves in shadow/test mode).
  `frontdoor.would_post` stays for the case with no rehearsal home at all.
- **Ticket button:** the same for `modmail_panel_*` — `modmail_panel_shadow_message_id`, `modmail.posted_panel_shadow`;
  and the door still takes the button down in the same channel (`frontdoor_replaces_ticket_button`), so in the
  rehearsal home the mods see exactly what `#welcome` will show: the rules post, then the front door under it
  (`frontdoor_follows_post` — the order rule applies to the rehearsal copies too; the welcome post's shadow copy is
  the one compared).
- Both copies carry ONE extra line at the top, `Rehearsal — this is where it would go: #welcome` (the wording a key,
  `rehearsal_note`, default that sentence with `{channel}`; the posts feature has its own note today — reuse or
  unify, say which).

## D. What the conductor does after the deploy

Set `shadow_channel_id` → `#welcome-test` (`1550284332365783091`). The posts reconcile moves the welcome copy there
(or the conductor presses **Post it** once), the front door and the ticket button post their copies on the next
reconcile, and the mods review in `#welcome-test`. Nothing in `#welcome` changes until the cutover.

## E. Tests (mirror the package)

`tests/test_shadow.py` (the key first, blank = as today; `channel_ids` includes it); `tests/test_guard.py` (the
rehearsal channel is allowed for sends while set, refused again when cleared; deletes unchanged);
`tests/cogs/community/test_frontdoor.py` (the shadow copy posted / kept / edited / taken down; the buttons on it
work; would_post only with no home; the order under the welcome copy); `tests/cogs/moderation/test_modmail.py`
(the ticket button's copy; taken down by the door); `tests/cogs/community/test_posts.py` (the copy follows the key);
`tests/test_settings_store.py`. Both orders.

## F. Docs

`code-notes.md`; this doc's `## Deviations`; `posts-design.md`, `front-door-design.md`, `modmail-doors-design.md`
(strike what changes, checklist 35); `docs/info/cutover-plan.md` (P5's note: the rehearsal home stops mattering when
`TEST_MODE` lifts — the copies are taken down by their own reconciles when the real post lands; say how each does);
`sweeps.md` rows `RH-a…`. NOT `TODO.md` / `DONE.md` / `deploys.log`.

## Deviations

*(the build agent writes here what it had to do differently, dated)*
