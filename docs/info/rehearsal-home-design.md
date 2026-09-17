# The rehearsal home — one channel where every shadow copy lands, so staff can review before the cutover

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 🔨 **BUILT 2026-09-17 on branch `rehearsal-home`,
> off `main` `9c8c179`; planned as v129, NOT merged and NOT deployed.** Read the `## Deviations` foot before
> §A–§F — nine things differ. `pytest -n auto` **6406 → 6455**, forward and under `BB_REVERSE=1`; registry
> **256 → 262** keys; no schema change. Was: 📐 DESIGN, dispatched to Opus 2026-09-17 16:2x (v129). **Last verified: 2026-09-17 16:16** against `main` `fbc4a48`: `black_bloc/shadow.py`
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

> Written by the Opus build, **2026-09-17**, branch `rehearsal-home` off `main` `9c8c179` (v128 live).
> Every line below is a place the build did NOT do what §A–§F says, and why. ⚠️ **Nothing here has met
> Discord:** the bot was never booted (a worktree holds no token), no message was posted in a real
> channel, no button was pressed in a client, `TEST_MODE` was never flipped and `shadow_channel_id` was
> NOT set — that is still the conductor's step after the deploy. Every figure is from `pytest -n auto`
> (**6455 passed**, both orders, from **6406** at the base commit), `ruff check .`, `node
> site/mock/check.mjs` (*19 pages, 180 routes, 17 core settings, all keys present*),
> `node site/mock/discordmd.test.mjs`, `node site/mock/labels.test.mjs`, and `node --check` over every
> `site/public/assets/*.js` and `site/mock/*.mjs`.

1. ⚠️ **`shadow.py` may not import `settings_store`, so the key NAMES live in `shadow.py` and
   `settings_store` aliases them.** §A reads as though the registry owns the key.
   `settings_store` imports `polls`, and `polls` imports `shadow`, so the import has to go the
   other way round: `shadow.REHEARSAL_KEY` / `NOTE_KEY` / `NOTE_DEFAULT` are the home, and
   `settings_store.SHADOW_CHANNEL` / `REHEARSAL_NOTE` / `REHEARSAL_NOTE_DEFAULT` are aliases of
   them. Still one home for each string; just not the one you would guess.

2. ⚠️ **The guard learns the channel through a `store.on_change` hook, but NOT through
   `own_channel`.** §B offers `guard.own_channel` / `disown_channel` as the shape. Those write
   `owned_channel_ids`, which is read by `allows_place` (deleting a channel), `owns_channel` and
   `allows_interaction` — so using them would have widened test mode by three powers, not one.
   `rehearse_in` / `rehearses_in` write a separate per-guild dict that only `allows_channel`
   reads. `allows_place` is untouched, as §B asks. The hook is registered by `shadow.install`
   from `bot.setup_hook` right after `store.load()`, which also seeds the guard from
   `store.stored_values` — a new public method, because `bot.guilds` is empty at that point.

3. ⚠️ **`allows_interaction` is NOT widened either, so a slash command still cannot be run in the
   rehearsal home.** §B says nothing about it and the brief said "nothing else". A mod in
   `#welcome-test` typing `/ask` is refused in words and told to use the test channel. **This
   does not affect the buttons**, which is what §C cares about: measured against `discord.py`
   2.7.1, `tree.interaction_check` is only reached by application-command interactions —
   component presses go through `ConnectionState.parse_interaction_create` →
   `_view_store.dispatch_view` and never meet the guard at all. So the three buttons on the
   rehearsal copy work. Widening `allows_interaction` by the same one channel is a one-line
   follow-up if the mods want to drive the panels there too.

4. ⚠️ **With `shadow_channel_id` blank, the front door and the ticket button rehearse in
   `#blackbloc-logs` from the moment this deploys — they do not wait for the conductor.** §D
   reads as though nothing happens until the key is set. The brief says ONE implementation of
   "where a rehearsal goes", and that implementation falls back to the guard's channel, so the
   first reconcile after the deploy posts both copies there. That is the same place the welcome
   post's copy already lives, it is staff-only, and setting the key moves both copies within five
   minutes. `frontdoor.would_post` / `modmail.would_post_panel` are therefore left for the
   genuinely homeless case: no rehearsal home, no guard channel and no log channel, or a home the
   guard still refuses.

5. ⚠️ **The rehearsal copies MOVE when the key moves; §A's warning that "changing the key does
   not move copies already up" is true of posts and polls only.** The front door and the ticket
   button reconcile every five minutes, so the same sweep that re-posts a deleted copy also
   notices the copy is in the wrong channel, posts a fresh one in the new home and deletes the
   old. That is what §D actually requires ("post their copies on the next reconcile"). **Posts is
   unchanged and is the one to watch:** pressing **Post it** after moving the key posts a fresh
   copy in the new home, writes one `post.shadow_message_gone` row about the old one — which is
   not gone, only elsewhere — and strands it. Deleting it is a hand step (sweeps **RH-d**). The
   fix is three lines in `posts.publish_post` (hunt with `shadow.find_copy`, drop the copy that
   is not in the current home) and was left out on purpose: §A scoped posts to "follows for
   free". **Polls:** an open poll's copy stays where it was, and `shadow.channel_ids` still finds
   it for edits and closing; a poll opened after the change goes to the new home.

6. **Two bookkeeping keys per copy, not one: `*_shadow_message_id` AND `*_shadow_hash`.** §C names
   only the message id. "Edits when the wording keys change" needs something to compare against,
   and the alternatives were worse: editing every sweep breaks the no-edit-that-changes-nothing
   rule, and keeping the fingerprint in memory means one pointless edit per restart per guild.
   The hash covers the note line, the heading, the line under it and (for the door) the three
   button labels. Registry **256 → 262**: `shadow_channel_id`, `rehearsal_note`,
   `frontdoor_shadow_message_id`, `frontdoor_shadow_hash`, `modmail_panel_shadow_message_id`,
   `modmail_panel_shadow_hash`.

7. **`rehearsal_note` is a CORE key beside `shadow_channel_id`, may be left blank, and is NOT
   unified with the posts feature's note.** §C says "the posts feature has its own note today —
   reuse or unify, say which": **neither.** `posts.shadow_words` is a sentence drawn on the
   Posts page and the `/posts` card telling a staffer what shadow will do; it is never sent to
   Discord. `rehearsal_note` is a line IN the message. They answer different questions in
   different places, so unifying them would have been one string pretending to be two. The note
   is the message CONTENT above the embed rather than a line inside it, so the embed the mods
   review is byte-for-byte the one `#welcome` will get; blank leaves no line at all
   (`rehearsal_note` joins `golive_end_template` and `golive_end_author` in `TEXT_MAY_BE_BLANK`).

8. **The modmail kinds are `modmail.panel_posted_shadow` / `panel_updated_shadow` /
   `panel_taken_down_shadow`, not §C's `modmail.posted_panel_shadow`.** Every sibling is
   `modmail.panel_*` (`panel_posted`, `panel_moved`, `panel_gone`, `panel_below_post`,
   `panel_failed`), and one kind spelled the other way round is the thing that makes a log
   filter miss a row. The front door's three follow its own family: `frontdoor.posted_shadow`,
   `frontdoor.updated_shadow`, `frontdoor.taken_down_shadow`. All six are ROUTINE, like the real
   `frontdoor.posted` and `modmail.panel_posted` beside them; none is a `.would_` kind, because a
   rehearsal copy is a real message really sent (the same reasoning `posts-design.md` §C8 gives).

9. **The website's Front door card was not changed.** §C asks for nothing on the site and the
   route now answers **200** with the rehearsal sentence, which the card shows as its toast —
   but the card's steady state still reads *"It is in #welcome"* from `frontdoor_channel_id`,
   which is where the door is AIMED, not where the copy is. A **rehearsing in #…** pill on the
   Doors section of `modmail.html` is the obvious follow-up. ⚠️ **The route's status changed from
   409 to 200 for exactly this case**, and `tests/api/tools/test_frontdoor.py` was rewritten to
   say so; the 409 is still tested, on the no-rehearsal-home path.

### What was NOT done, and what was NOT verified

- **Nothing met Discord.** No boot, no token, no message sent, no button pressed, no key set, no
  deploy, and `TEST_MODE` was never flipped. Every claim above is the test suite, the mock and a
  reading of `main`.
- **`shadow_channel_id` was NOT set** — §D is the conductor's step after the deploy, as the
  design says. The registry default is blank.
- **No browser saw anything**, real or mock: `check.mjs`, `labels.test.mjs` and
  `discordmd.test.mjs` were run headless and the Settings page was never opened to look at the
  two new core rows.
- **No migration** — six registry keys, no schema change; `SCHEMA_VERSION` is untouched at 43.
- **`docs/TODO.md`, `docs/DONE.md` and `docs/deploys.log` were not touched**, as the brief said.
- **`posts.publish_post` was left alone** — see deviation 5. It is the one known rough edge and
  it bites at §D.
- **KI-26 did not fire once** during this build: eleven `pytest -n auto` runs, no stall.
