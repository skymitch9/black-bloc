# Channel streamers — an org channel is a persistent row like any linked member; spotlight and the ping role are toggles on it

> 🔇 **FOLLOW-UP 2026-09-21 17:3x, branch `quiet-channel-kinds` off `main` `0612da0` — NOT merged, NOT
> deployed: this whole family stops posting an embed to `#blackbloc-logs`.** Owner, 2026-09-21 17:2x, verbatim: *"okay that works, i dont want log messages appearing in black bloc logs for channel linking or channel spotlight or channel annouce"*.
> `golive.channel_announced`, `golive.history_swept`, `golive.spotlight_added`,
> `golive.spotlight_announced`, `golive.spotlight_expired` and `golive.spotlight_removed` move from
> `IMPORTANT` to `ROUTINE` in `black_bloc/logkinds.py`, joining the seven that were routine already
> (`golive.link`, `youtube.link`, `golive.spotlight_bumped` / `_pinned` / `_unpinned` / `_updated`,
> `golive.channel_ended`), so at the default `golive_log_level = important` Discord sees none of them.
> ⚠️ **Nothing was taken off the Logs page** — every row is still written to `action_log` and still
> drawn under the **golive** chip — and **`golive_log_level = all` turns the Discord mirror back up
> with no deploy**. Every `*_failed` twin, `golive.role_stuck`, `youtube.probe_unreadable` and
> `golive.costream_added` stay IMPORTANT. ⚠️ **This STRIKES Deviation F2 of the 16:5x follow-up** and
> the *both spellings are added* sentence in its mock paragraph. Sweep row `QK-a`, unwalked.
> ⚠️ **Nothing in it has met Discord and no browser rendered the Logs page.**
>
> **Audience:** the build agent and reviewers. **Status:** TRACKED · ✅ **LIVE v151 (2026-09-21)** — release `c1b83f0`,
> deployed commit `c7ef8f1`, **2026-09-21 09:51** Phoenix; merge `e3f873a`, 7 commits; sweeps **719–725** (were
> `CS-a` … `CS-g`) are the owner's and **none has been walked**. ✅ **The migration RAN at this boot** — `database: added
> spotlight_channels.spotlight / .announce / .youtube_channel_id / .youtube_handle`, schema **52**, four ADDED columns,
> **no rebuild** (so no backup was needed). ✅ **Applied on live through the site 09:5x:** GDQ (row id 3) linked to
> `@GamesDoneQuick` (`UCI3DTtB-a3fJPjKtQ5kYHfA`, *Games Done Quick*), ESA (row id 4) linked to `@esamarathon`
> (`UC3Oe-jfrIqEGygxYBYyN6jQ`, *ESA Speedrunning*) with announce **OFF**, `rpglimitbreak` added as row id 5 kept +
> spotlight on + announce **OFF**. ⚠️ **NOTHING IN IT HAS MET DISCORD, HELIX OR YOUTUBE LIVE**, and ⚠️ **ESA was
> announced and pinned at the boot itself, before its opt-out could land** — the 🔇 *channel opt-out must end an open
> session* item on [`../TODO.md`](../TODO.md), branch `channel-optout`. Was 🔨 BUILT on branch `channel-streamers`
> 2026-09-21 (design: Fable, 08:2x, dispatched to Opus the
> same turn). The `## Deviations` foot is the truth where this body departs from
> 🔨 **FOLLOW-UP BUILT 2026-09-21 16:5x, branch `channel-kinds` off `main` `d4e3535` (v153 live) — NOT merged, NOT deployed**: *a channel announcement is not a spotlight*. A row whose spotlight is OFF now logs **`golive.channel_announced`** / **`golive.channel_ended`** (shadow: `golive.would_channel_announce`), because `actionlog.build_embed` makes the KIND the embed title and `#blackbloc-logs` was therefore telling the owner GamesDoneQuick was spotlighted when it was not. ⚠️ **This STRIKES Deviation 2 below** — read [**§ Follow-up 2026-09-21 (16:5x)**](#follow-up-2026-09-21-16-5x-the-log-kind-says-channel-not-spotlight) before trusting it. Sweep row `CK-a`, unwalked. ⚠️ **Nothing in it has met Discord or Helix and no browser rendered the Logs page.**
> ✅ **FOLLOW-UP LIVE v152 (2026-09-21 10:35)** — release commit `32d3c0b` (which is also the deployed commit),
> `release.json` says `v152` at `8dcb52f`; merge `8dcb52f` of branch `channel-optout`, 2 commits, key
> **`golive_channel_optout_post`**, registry keys **297**, sweeps **730–731** (were `CO-a` / `CO-b`) and **neither has been
> walked**. *Opting a channel out while it is LIVE now ends the announcement that is already out*, which Deviation 5 below
> got wrong; read
> [**§ Follow-up 2026-09-21**](#follow-up-2026-09-21-opting-out-ends-the-announcement-that-is-already-out) before trusting
> Deviation 5. ⚠️ **Nothing in the follow-up has met Discord or Helix** — the only live move after the v152 boot was ESA
> being opted back in and out once through the site to settle its open session, and ⚠️ **its result was not captured**.
> what was built, and `## What was NOT verified` is the honest half; sweeps `CS-a` … `CS-g` in
> [`../access/sweeps.md`](../access/sweeps.md) are the proof that is missing. ⚠️ **Schema is 52 and the migration
> added FOUR columns, not three** — `announce` is the owner's mid-build ask. Was: **Last verified: 2026-09-21 08:2x** against `main` `c4cc672`
> (v150 live): a channel with no member exists ONLY as a `spotlight_channels` row (`storage/db.py:876` — `id, guild_id,
> twitch_login, twitch_user_id, display_name, note, added_by, added_at, expires_at, bump_hours, pin, event_id`); its
> go-live is announced/pinned/bumped by `cogs/content/spotlight.py` (the five-minute Helix poll, `_announce`, the bump,
> `_end`); its ping role hangs off `golive_fan_roles.spotlight_id` (v150); `forget_spotlight` `:995` deletes the row —
> and with it the channel, its role and its sessions — which is what the owner hit; `golive-join.js` draws a spotlight
> row as `spotlight:<id>` with a *channel only* badge; the YouTube live sweep (`cogs/content/youtube.py`) walks
> `youtube_links` (member-keyed) only; `api/tools/youtube.py:40` accepts `youtube.com/channel/UC…` or an `@handle` and
> resolves it (`:55` `handle`).

## The ask, verbatim (owner, 2026-09-21 08:1x)

*"I removed them from Spotlight as a test and they vanished from the whole list. I want them linked like any other stream
so they're persistent. I then want to be able to spotlight or role them like any other stream on and off. Also find
YouTube channels for both of them if possible to link"*

## A. The model — the spotlight row becomes the channel record; spotlight is a flag on it

`spotlight_channels` is renamed in MEANING, not in name (no table rename — checklist: migrations are additive): it gains
**`spotlight INTEGER NOT NULL DEFAULT 1`** (the toggle; existing rows stay spotlighted, so GDQ and ESA keep today's
behaviour), **`youtube_channel_id TEXT`** and **`youtube_handle TEXT`** (`ADDED_COLUMNS`, schema 51 → **52**). The
row is the channel streamer: *a Twitch login and/or a YouTube channel with no Discord member behind it*. `twitch_login`
becomes nullable in effect for a YouTube-only channel — if the column is `NOT NULL`, keep it and store `''` … NO: the
UNIQUE `(guild_id, twitch_login)` would then collide; the builder picks between relaxing the column (the `mod_cases`
two-step rebuild the spotlight-pings build used for `golive_fan_roles`) and requiring a Twitch login for every channel
row (YouTube-only channels refused in words *for now*) — and SAYS which in Deviations. The owner's two channels both
have Twitch logins, so either choice serves today.

**Going live.** A channel row's Twitch login is polled as today (one batched Helix call). When it goes live:
- **spotlight off** → announced EXACTLY as a member's go-live is (`golive_template`, the card, `golive_live_author`,
  the global ping role + the row's own fan role), one `spotlight_sessions` row, the end path edits to past tense per
  the one end wording — **no pin, no bumps**. Log `golive.channel_announced` (IMPORTANT) — or reuse
  `golive.spotlight_announced` with `spotlight: false` in details; the builder picks the one that keeps the Logs chip
  honest and says why.
- **spotlight on** → today's behaviour: pinned, bumped every `bump_hours`, unpinned + cleaned at the end.
The **YouTube side**: the YouTube live sweep walks channel rows with a `youtube_channel_id` beside `youtube_links`
(same `probe_live`, same `_live_now` path with a `name=` instead of a member, the same co-stream join if the Twitch side
is already open — `open_session_on` finds the row's session by either side). A YouTube handle typed in (`@GamesDoneQuick`)
resolves through the same code `api/tools/youtube.py` uses for a member link.

## B. Doors

**Site — Go-live page.** **Add a streamer** takes *a channel with no member*: the member picker becomes optional; with
no member, the typed value routes as today (Twitch login or YouTube URL/handle) and makes a channel row (spotlight OFF by
default — a key, `golive_channel_spotlight_default`, bool false, so the owner can flip it). **Spotlight a channel** stays
as the door that makes a row with spotlight ON (it is what the owner used today). The row's drawer: **Spotlight** group
becomes a toggle — *Spotlight on* / *Spotlight off* (with the kept / expires / bump / pin moves shown only while on) —
plus **Link a YouTube channel** / **Unlink it** in the YouTube group (the member group's construct), the Ping-role group
as v150 (Add / Rename / Remove), and **Remove this channel** (danger, confirm: *"Removes GamesDoneQuick from the list,
its spotlight, its YouTube link and its ping role (per pings_fan_role_delete). Nothing in Discord is deleted except the
role if that setting says so."*). The Streamers list: the *channel only* badge stays; the Announced cell reads *live now*
/ *ready*; the Expires cell reads *kept for ever* / *until …* only while spotlight is on, else *—*; a new
**Spotlight** column? NO — the existing Spotlight chip filters, and the drawer's toggle says the state; the Expires
column's *—* is enough.

**Discord — `/golive` ▸ Spotlight… sub-panel** becomes **Channels…**: the list, Add a channel… (Twitch login, optional
YouTube handle, spotlight on/off), per row: Spotlight on/off, Extend / Keep, Bump now (while on and live), the ping role
moves, Remove. Panels-over-slash: buttons that render only when valid.

**Routes:** `POST /api/golive/spotlight` gains `spotlight: bool` (default from the key) and `youtube: <url|handle>`;
`PATCH /api/golive/spotlight/{id}` gains `spotlight` and `youtube` (null to unlink); `GET` rows carry `spotlight`,
`youtube_channel_id`, `youtube_handle`. Contract + mock rows (GDQ with both links, spotlight on; a channel with
spotlight off; a YouTube-only channel if allowed).

## C. Keys — one, `golive_channel_spotlight_default` (bool, false, group golive), registry + mock + label + `placeSettings`
+ the join fixture.

## D. The two channels — do the lookup, then the owner links them

The design cannot know YouTube channel ids. The builder RESOLVES `@GamesDoneQuick` and `@ESAMarathon` (or the
handles the channels actually use — check `youtube.com/@GamesDoneQuick` and `youtube.com/@esamarathon`) through the
resolver the routes use (or a one-off `curl` of the channel page for its canonical `UC…` id if the resolver needs the
API key it cannot have) and writes the two ids into the **mock seed** and into the report; the conductor links them on
the live site through the new route after the deploy (the live rows are GDQ `id 1`… re-added 08:1x — read them, do
not assume ids).

## E. Tests, docs, gate

`tests/test_spotlight.py` + `tests/cogs/content/test_spotlight.py` (a channel with spotlight off is announced like a
member and never pinned or bumped; on → today's behaviour; the toggle flips without losing the row, the role or the
sessions; Remove takes everything; the YouTube side announces and co-streams), `tests/cogs/content/test_youtube.py`
(the sweep walks channel rows), `tests/api/tools/test_golive.py` (the route fields, both defaults, refusals in words),
`tests/api/test_contract.py`, `tests/storage/test_db.py` (52), `golive-join.test.mjs`, the key/kind guards. Both
`pytest -n 8` orders, `ruff`, ES parse, `check.mjs`, the six node tests, env cleared. A headless render of the row
drawer in both toggle states and Add a streamer with no member. Docs: `code-notes.md`; this doc's `

## Follow-up 2026-09-21: opting out ENDS the announcement that is already out

> ✅ **LIVE v152 (2026-09-21 10:35)** — built on branch `channel-optout` off `main` `1a35d75` (v151 live), merged as
> `8dcb52f`, deployed commit `32d3c0b`. ⚠️ **Nothing in it has met Discord or Helix.** Sweeps **730–731** (were `CO-a`
> and `CO-b`), neither walked.

**The defect, owner verbatim (2026-09-21 09:5x):** *"the bot went live and annouced esam and pinned
it, it should have been in the list silent. i opted out of the spotlight for it and opted out of
notifications"*.

**Measured on live.** ESA's spotlight session 2 opened at **16:51:16Z — the same second the bot
logged in after the v151 deploy**. The boot poll found the channel live and announced and pinned it
under the migration's `announce = 1` default, before the owner could set the row otherwise. He then
turned `announce` off and `spotlight` off. ⚠️ **Deviation 5 above says an opted-out channel "gets no
post, no session, no pin and no reminder" — true of a channel that is opted out BEFORE it goes live,
and false of one opted out while a session is open**, which is the case the whole build never
considered. `change_spotlight` only wrote the row: the session stayed open, the announcement stayed
posted and PINNED, and the only thing that ends a spotlight session is `_seen` counting
`spotlight_end_misses` quiet Helix polls. ⚠️ **ESA runs reruns around the clock, so that never
happens** — the pin was permanent. `_maybe_bump` is gated on `announces(row)`, so at least no
reminder followed.

**The rule after.** `change_spotlight` funnels through `changed_spotlight`, which returns `(row,
settled)` and, after the row has moved, settles an OPEN session **under the row's own lock**
(checklist 6 — the poller holds the same lock while it announces or ends):

- **`announce` 1 → 0 with a session open** runs the existing `_end` path with the reason word
  `opted_out`: the session is closed, the usual `golive.spotlight_ended` row is written, and what
  becomes of the post is the new key's decision.
- **`spotlight` 1 → 0 with a session open** only **unpins** the announcement
  (`golive.spotlight_unpinned` with `because: spotlight_off`). The session stays open and the post
  stays live-worded — the channel is announced like a member's from now on, and the post is edited
  to past tense when the stream really ends. ~~Turning the spotlight back ON mid-stream still does
  NOT retro-pin (sweep row 721 already says so).~~ ⚠️ **REVERSED 2026-09-22** (owner ask, branch
  `spotlight-retro-pin`): turning it back ON mid-stream now pins the live post — see **Follow-up
  2026-09-22** below.
- ~~Turning either back ON settles nothing: nothing that happened while it was off is posted after
  the fact.~~ ⚠️ **Amended 2026-09-22:** opting back IN still settles nothing and posts nothing
  after the fact; turning the SPOTLIGHT back on now settles the pin (and only the pin) — see
  **Follow-up 2026-09-22** below.

**The key — `golive_channel_optout_post`** (enum, group `golive`, default **`end`**), registry +
mock `SETTING_SPECS` + `labels.js` + `golive-join.js:placeSettings` (the *How streams are spotted*
drawer, beside `golive_channel_spotlight_default`) + the join fixture (**51 → 52** keys in the
three namespaces). ⚠️ **Registry keys measured 2026-09-21 on this branch: 297** (`296` before this
key) — `architecture.md`'s **295** was measured on `channel-streamers` and two more have landed on
`main` since, so do not arithmetic off that number.

| Value | What happens to the post that is out |
|---|---|
| **`end`** (default) | Unpinned and edited to the ONE end wording, exactly as any stream end does |
| `delete` | Deleted outright (`golive.spotlight_post_deleted`); deleting takes the pin with it |
| `leave` | Left exactly as posted — only the pin comes off |

The session is closed in all three, so no reminder follows and nothing waits on Twitch.

**The sentence.** `spotlight.announce_said(row, settled)` and `spotlight.spotlight_said(row,
settled)` are the ONE sentence function both doors use — `/golive` ▸ **Channels…** ▸ **Opt out of
announcements** and `PATCH /api/golive/spotlight/{id}` both return it, and the site drawer prints
what the route answers. The clause lands only when a session was actually open, and names
`golive_channel_optout_post` so a reader knows what to change.

### Follow-up deviations

1. ⚠️ **`golive.spotlight_ended` carries `reason: "opted_out"`, NOT `because: "opted_out"`.** The
   brief asked for `because`. Every other end row in the family already spells this field `reason`
   (`ended` / `expired` / `removed` / `reconciled_on_start`), and splitting one event's *why* across
   two field names would mean a reader filtering the family has to know which build wrote the row.
   `because` IS used where the family already uses it: `golive.spotlight_expired` keeps its own, and
   `golive.spotlight_unpinned` / `_unpin_failed` **gain** one (`spotlight_off` from the toggle, and
   the end's reason word from every other path) because those rows had no *why* field at all.
2. **`_end` gained a `post` argument and the end row a `"post"` detail**, which the brief did not
   name. The three key values are three different treatments of the same message, and the end row is
   the only place a reader can see which one ran; without it, `leave` and a failed edit look
   identical in the log — checklist 2.
3. **`delete` reuses `golive.spotlight_post_failed` with `what: "delete"`** for its failure, the way
   the bump path already does, rather than inventing a failure kind. Its success is a new routine
   kind, `golive.spotlight_post_deleted`, because a deleted announcement is a thing staff will look
   for and it has no other row.
4. **`change_spotlight` kept its signature and return.** Its five other call sites (extend, keep,
   expire, `link_youtube`, `unlink_youtube`) want the row and nothing else, so the `(row, settled)` pair
   lives on `changed_spotlight` and `change_spotlight` is a one-line wrapper. The PATCH route and
   `set_announce` / `set_spotlight` are the three callers that take the pair.
5. ~~**The member opt-out (`cogs/content/golive.py:opt_out`) was NOT changed to match.** The brief
   said to mirror it if it ends an open session; it does not — it writes the opt-out row and drops
   the fan role, and a member's open go-live session runs on until presence or the poller says it
   is over. That asymmetry is now deliberate rather than accidental: a member's session ends by
   itself within the hour, a 24/7 channel's never does. Worth the owner's word if he wants both.~~
   ⚠️ **REVERSED 2026-09-21 by the owner — "opt out should end their annoucement"** — branch
   `member-optout`, off `main` `20b615d`. The asymmetry is gone: a member's opt-out now ends the
   open session the same way, under the member's own lock, with its own key
   `golive_member_optout_post`. The reasoning above was wrong about the stakes rather than the
   mechanism — a member's session does end by itself within the hour, but an hour of a post that
   says somebody is live when they have asked not to be announced is exactly what the owner did not
   want. Design: [`golive-panel-design.md`](golive-panel-design.md) ▸ **Follow-up 2026-09-21**.
6. **No forward-looking warning was added to the drawer or the panel before the press.** The Opt-out
   sentence is the *result* sentence, per the brief's "both doors use the one sentence function";
   saying it in advance on the site would mean putting `golive_channel_optout_post` into the
   spotlight row payload, which is an API contract change for a warning the answer already gives.

### Follow-up — what was NOT verified

- ⚠️ **NOTHING HERE HAS MET DISCORD.** No channel was opted out in a real server, no pin came off a
  real message, nothing was deleted and no announcement was edited. Every claim about what a post
  reads is the suite's, against fakes. **A Discord run is impossible from a build worktree** — it
  needs the token and a live gateway.
- ⚠️ **Nothing has met Helix, and the live ESA row was not touched.** The measurement in the body
  is the conductor's reading of the live logs, not this build's.
- **No browser check was made** — the site half is the route's sentence and the mock's mirror of it,
  proved by `check.mjs` and the suite, not by a page anybody looked at.
- **The mock's settle is a hand-written mirror**, not shared code: `site/mock/server.mjs`
  (`settleOpenSession`, `OPTED_OUT_POST_SAID`, `UNPINNED_NOW`) restates the three sentences and the
  session close. If the Python wording changes and the mock's does not, nothing fails — the two
  copies are only checked by eye.
- **`delete` was never exercised against a message Discord refused to delete**; the failure branch
  is proved by the unit path alone.

## Follow-up 2026-09-22: Spotlight ON settles the pin (the retro-pin)

> **Status:** built on branch `spotlight-retro-pin` off `main` `95cb8954` — NOT merged, NOT deployed.
> ⚠️ **Nothing in it has met Discord.** Sweep row `RP-a` in `../access/sweeps.md`, unwalked.

**The ask, owner verbatim (2026-09-22):** *quick fix, when something gets tagged for a spotlight do a check to see if the channel is pinned, if its live and not pinned, pin it. if its not live and pinned un pin it, when its live again its pinned again*

**Measured on live (conductor's reading).** GamesDoneQuick (spotlight row 3) had its spotlight OFF,
went live and was announced unpinned (`golive.channel_announced`), and the owner pressed
**Spotlight on** mid-stream. Nothing pinned it: `settle_open_session` settled only `announce` 1→0
and `spotlight` 1→0, and the pin was taken only at announce time — while the bot's own sentence
(`SPOTLIT_SAID`, *"its announcement is pinned while it streams"*) promised otherwise.

**The rule after.** `spotlight` 0→1 is a third settle case ("brightened"), under the row's lock:

- **A session is OPEN and the row's `pin` is on:** the live announcement is fetched and, if it is
  not already pinned, pinned now — `golive.spotlight_pinned` with `because: spotlight_on`. The
  answer adds *"The announcement that is out now has been pinned for the rest of the stream, and
  the reminders pick up from here."* A refusal from Discord (`golive.spotlight_pin_failed`, same
  `because`) is returned in words — the `PIN_REFUSED` sentence — and the row stays flipped.
- **The row's `pin` is off, or the row is opted out:** nothing is pinned.
- **No session is open:** the LAST session's announcement is read; if it is still pinned (an end
  whose unpin failed), it is unpinned now (`golive.spotlight_unpinned`, `because: spotlight_on`)
  and the answer says so. Nothing pinned → nothing settled. The next stream is pinned at announce
  time as before — *"when its live again its pinned again"* is the existing announce-time rule.
- ⚠️ **Toggle time ONLY.** The poller does NOT re-check pins: staff who take the pin off a live post
  by hand mid-stream are not fought every poll (staff final say).
- **Announce 1→0 in the same write wins** — the session ends, and nothing is pinned first.

**Deviations from the brief.** (1) The stale-pin case returns a new word `UNPINNED_ENDED`, not
`UNPINNED`: the sentence differs (the stream has ended) and an existing test pins that a spotlit
row's answer never carries the mid-stream unpinned sentence. (2) The mock (`site/mock/server.mjs`)
mirrors the brighten; it tracks no pin state, so it pins whenever a live session is open and the
row's pin is on. (3) The sweep row is lettered `RP-a`, not numbered: the `SD-*` rows above it are
still waiting on the conductor's numbers, and taking `740` could collide with them.

**Not verified.** Nothing has met Discord or Helix; the live GDQ post was not touched. Every claim
about pins is the suite's, against fakes. No browser rendered the drawer; the mock's sentence was
read off `PATCH /api/golive/spotlight/1` with curl.

## Follow-up 2026-09-21 (16:5x): the log kind says CHANNEL, not spotlight

> ✅ **LIVE v154 (2026-09-21 20:08)** — built on branch `channel-kinds` off `main` `d4e3535` (v153
> live), merged `6017db05`, release commit `52c48235`, 3 commits + one conductor line, 7 new
> tests, sweep **736**. ⚠️ **Nothing in it has met Discord or Helix** — sweep row `736` in
> [`../access/sweeps.md`](../access/sweeps.md) is the proof that is missing.
> ⚠️ **This section reverses [Deviation 2](#deviations) of the v151 build**, which is struck below.

**The defect, owner verbatim (2026-09-21 16:5x):** *"why is gdq being spotlighted in the logs
channel? its spot light isnt on"*.

**Measured on live, 2026-09-21.** The GamesDoneQuick channel row has **spotlight OFF and announce
ON**. At **22:53Z** its stream was announced in `#live-now` (`golive_channel_id`) and was **not
pinned** — which is exactly what a spotlight-off row is supposed to do. The row written to
`action_log`, and posted to `#blackbloc-logs` because it is IMPORTANT, was
**`golive.spotlight_announced`**, with `spotlight: false` buried in the details JSON. ⚠️ **The
behaviour was right and the wording lied**: `actionlog.build_embed` has no title table — it sets
`discord.Embed(title=kind)` — so the KIND IS THE SENTENCE the owner read, and he concluded from the
logs channel that the spotlight was on.

**The rule after.** The kind is read off the row at the moment of the event:

| The row at that moment | Announce, mode `on` | Announce, mode `shadow` | End |
|---|---|---|---|
| `is_spotlit(row)` **true** | `golive.spotlight_announced` | `golive.would_spotlight_announce` | `golive.spotlight_ended` |
| `is_spotlit(row)` **false** | **`golive.channel_announced`** | **`golive.would_channel_announce`** | **`golive.channel_ended`** |

- **Both new kinds are IMPORTANT** (`logkinds.IMPORTANT`), so a channel announcement reaches
  `#blackbloc-logs` exactly as a spotlight announcement does — the owner is not being asked to look
  in a quieter place for the same event. ⚠️ **`golive.channel_ended` therefore DIVERGES from its
  two siblings**: `golive.spotlight_ended` and `golive.end` are both ROUTINE. See Deviation F2 below.
- **The shadow twin is classified by RULE, not by a list.** `logkinds.is_important` returns False for
  anything containing `.would_`, and `test_every_shadow_kind_is_routine_by_rule_not_by_being_listed`
  *forbids* listing a `would_` kind in `ROUTINE` — so `golive.would_channel_announce` appears in no
  set at all, which is correct and deliberate.
- **The details carry `spotlight`, `announce` and `platform` on BOTH halves**, so a reader filtering
  on either detail still finds both families. The end row gained `spotlight` and `announce`; the
  announce row gained `announce` (it already carried `spotlight`, `pin` and `platform`).

**The Logs page needed nothing, and that is a measurement, not an assumption.** Grepped
2026-09-21 across `site/public/assets/*.js`, `site/mock/server.mjs` and `docs/info/`: **no surface
labels a log kind by name**. `logs.js:kindPill` prints `row.kind` verbatim into the pill and its
`title` attribute; the family chips in `logs.js:LOG_FEATURES` are keyed by FEATURE (`golive`), which
`actionlog.py` turns into SQL through `logkinds.like_patterns('golive')` → `golive.%` +
`web.golive.%` — so `golive.channel_announced` is inside the **golive** filter by construction and
`labels.js` holds settings labels, never kinds.

**The mock's mirror.** `site/mock/server.mjs:settleOpenSession` restates the opt-out close by hand
(there is no bot behind it), so it now picks `golive.channel_ended` when `row.spotlight === false`
and carries the same two details. ⚠️ **Nothing checks the Python and the JavaScript copies against
each other** — the same warning the v152 follow-up already carries.

⚠️ **The mock keeps its OWN classification list, and it was already wrong about this family.**
`site/mock/server.mjs:IMPORTANT_KINDS` is a short hand-written subset of `logkinds.IMPORTANT`, and
it did not hold `golive.spotlight_announced` — so the mock's Logs page has been drawing the
announce row as *routine* while live draws it *important*. Both spellings are added, which fixes
the old one as well as classifying the new one. `golive.channel_ended` needs no entry either side:
`.ended` is in both copies of `IMPORTANT_SUFFIXES`.
~~Both spellings are added.~~ 🔇 **STRUCK 2026-09-21 17:3x (`quiet-channel-kinds`)** — the mock's
`IMPORTANT_KINDS` no longer holds `golive.spotlight_announced` or `golive.channel_announced` either,
and `golive.spotlight_expired` / `golive.spotlight_removed` are listed in its `ROUTINE_KINDS` because
`.expired` and `.removed` ARE `IMPORTANT_SUFFIXES` entries and would otherwise classify by suffix.

### Follow-up (16:5x) — Deviations

**F1. A mid-stream toggle SPLITS the pair, on purpose.** §1 of the brief allowed either the
session's spotlight at announce time or the row's at end time. The row at END time wins, because
`spotlight_sessions` has no `spotlight` column and adding one would be a migration for a log label.
So a channel that is spotlit when it goes live and has its spotlight taken off mid-stream logs
`golive.spotlight_announced` … `golive.channel_ended`. ⚠️ **That is the honest reading** — each row
says what the channel was when the row was written — but a reader pairing announce-to-end by kind
alone will not match them. The `spotlight` detail on both rows is how they pair; the
`session_id`/`spotlight_id` details are how they pair exactly.
`test_a_spotlight_taken_off_mid_stream_ends_under_the_kind_the_row_says_now` pins it.

**~~F2. `golive.channel_ended` is IMPORTANT while `golive.spotlight_ended` is ROUTINE — a real
divergence, flagged rather than smoothed over.~~** 🔇 **STRUCK TWICE.** The conductor took the call
at the merge (`6017db0`, *"channel_ended is ROUTINE like every other end"*), and on 2026-09-21 17:3x
the owner quietened the whole family (branch `quiet-channel-kinds`, the follow-up in this doc's
header): announce, end, link, sweep and every spotlight success kind are ROUTINE together, so the
divergence below no longer exists in either direction. The reasoning is kept because it is the
reason `.ended` needs an EXPLICIT `ROUTINE` entry rather than none: The brief said "the two new IMPORTANT kinds", and
`.ended` is in `IMPORTANT_SUFFIXES` besides, so IMPORTANT is also what the kind gets with no entry
at all. The consequence: with `golive_log_level = important` a spotlight-off channel's END reaches
`#blackbloc-logs` and a spotlit one's does not. 🔁 **Reversing it is one line** — move
`"golive.channel_ended"` from `IMPORTANT` to `ROUTINE` in `black_bloc/logkinds.py` and flip the
assertion in `test_a_channel_with_no_spotlight_has_its_own_kinds_so_the_title_cannot_lie`. The
conductor's call; nothing else depends on it.

**F3. `actionlog.build_embed` was NOT touched.** The brief allowed for a kind→title table. There
is none: `build_embed` is `discord.Embed(title=kind)`, which is precisely why renaming the kind is
the whole fix. `test_the_embed_title_is_the_kind_so_a_channel_row_never_says_spotlight` in
`tests/test_actionlog.py` now pins that the title is the kind, so a future title table cannot
quietly reintroduce the word.

**F4. The announce details gained `announce`.** Deviation 2 below claimed the details "now carry
`spotlight`, `announce`, `platform`" — **they carried `spotlight`, `pin` and `platform` and never
`announce`**, measured on the v151 code. The claim is now true rather than the sentence corrected,
because the brief asks a filter to find both families by detail.

**F5. `sweep_expiries` still skips a spotlight-off row, so `_expire` never writes a channel end.**
Pre-existing (`cogs/content/spotlight.py:sweep_expiries` returns early on `not is_spotlit(row)`, and
`test_a_channel_with_the_spotlight_off_is_never_purged` asserts it). Untouched here — it is a
purge-policy question, not a wording one — but it means `golive.channel_ended` is reachable from
three paths only: the stream going quiet, an opt-out settling an open session, and
**Remove this channel**.

### Follow-up (16:5x) — what was NOT verified

- ⚠️ **NOTHING HERE HAS MET DISCORD.** No embed was posted to `#blackbloc-logs`, and the claim that
  the title now reads *golive.channel\_announced* is the suite's against a `discord.Embed` object,
  not a screenshot. **A Discord run is impossible from a build worktree** — it needs the token and a
  live gateway.
- ⚠️ **Nothing has met Helix**, so no real GDQ stream has been announced under the new kind. The
  22:53Z measurement in the body is the conductor's reading of the live logs, made BEFORE this build.
- ⚠️ **No browser rendered the Logs page.** That `golive.channel_announced` falls inside the
  **golive** chip is derived from `like_patterns('golive')` and asserted in `tests/test_logkinds.py`;
  nobody has filtered a real page on it. The review link is
  [`https://blackbloc.heygabi.ai/logs.html`](https://blackbloc.heygabi.ai/logs.html) ▸ **golive**.
  ⚠️ **That path is `audit.html` in the repo** (`site/public/audit.html`, `<title>Black Bloc —
  logs</title>`, `data-tab="audit"`); `site/public/logs.html` does not exist, so the public URL is a
  rewrite this build did not verify.
- ⚠️ **No existing `golive.spotlight_announced` row is rewritten.** There is no migration: every row
  already in `action_log` keeps the kind it was written with, including the 22:53Z one the owner
  read. The Logs page will show both spellings on either side of the deploy.
- **The mock half was not opened in a browser** — `settleOpenSession` is exercised by
  `node site/mock/check.mjs` and by eye, and no page was pressed.

## Deviations

**Built 2026-09-21 on branch `channel-streamers` off `main` `9b865b8` (v150 live).** Where this
body and the code disagree, the code is what shipped and this section is why.

1. ⚠️ **`twitch_login` was NOT relaxed; a YouTube-only channel is refused in words *for now*.**
   §A left the choice to the builder. The migration is **purely additive** — four columns
   through `ADDED_COLUMNS`, no rebuild — because `spotlight_channels.id` is referenced by
   `spotlight_sessions.spotlight_id` and `golive_fan_roles.spotlight_id` with **no foreign key
   to protect either**, and the live rows (GDQ, ESA, re-added by the owner this morning) carry
   both. A `mod_cases`-style rebuild of that table buys nothing today — both of the owner's
   channels have Twitch logins — and risks the two tables that point at it. The refusal is
   `spotlight.NEEDS_A_TWITCH_NAME`, raised as `400 needs_twitch` by `POST /api/golive/spotlight`
   and said in the browser by `page-golive.js`'s `ADD_CHANNEL_NEEDS_TWITCH` before any request
   goes out. Relaxing the column later is a one-commit rebuild on the `golive_fan_roles`
   precedent; nothing built here assumes the column is `NOT NULL` except the two refusals.

2. ~~⚠️ **The log kind is the EXISTING `golive.spotlight_announced` with `spotlight: false` in
   details — no new kind.**~~ 🔴 **STRUCK 2026-09-21 16:5x, branch `channel-kinds`** — the owner
   read `#blackbloc-logs` and concluded GamesDoneQuick's spotlight was on when it was off
   (*"why is gdq being spotlighted in the logs channel? its spot light isnt on"*). The reasoning
   below missed that `actionlog.build_embed` has NO title table: the kind IS the embed's title, so
   "the same event with one field different" was a sentence in a Discord channel saying the
   opposite of the truth, and `spotlight: false` was inside a JSON blob nobody reads. `golive.
   channel_announced` / `golive.channel_ended` / `golive.would_channel_announce` are what ship —
   see [**§ Follow-up 2026-09-21 (16:5x)**](#follow-up-2026-09-21-16-5x-the-log-kind-says-channel-not-spotlight)
   above, which also records that the end pair is NOT symmetric with the announce pair. The
   original reasoning, left as written: §A offered `golive.channel_announced` as the alternative. Reusing it
   keeps the Logs chip honest in the way that actually matters: the rest of the family
   (`golive.spotlight_ended`, `…_post_failed`, `…_pin_failed`, `…_bumped`) is unchanged, so a
   reader who filters on the announce kind still finds the matching end. A new head would have
   split one event across two kinds whose ends were the same kind, and would have needed a
   `logkinds.py` registration and a chip mapping for a row that is not a new event at all — it
   is the same event with one field different. The details now carry `spotlight`, `announce`,
   `platform`, and `pin` already reflects the toggle (`pin AND is_spotlit`).

3. ⚠️ **A channel with the spotlight OFF never expires**, and `sweep_expiries` skips it. The
   body only said the **Expires** cell reads `—`. Letting such a row keep expiring would
   reproduce the owner's complaint exactly — a channel added for persistence vanishing a week
   later — so `spotlight_channel(...)` stores `expires_at = NULL` for a row it makes with the
   spotlight off, AND the sweep ignores a non-spotlit row whatever its date. Turning the
   spotlight back ON re-arms whatever date the row still carries.

4. ⚠️ **"A session joins from either side" is ONE SESSION PER ROW, not two platforms on one
   session row.** `spotlight_sessions` has no `also_*` columns and §A capped the migration at the
   three (now four) columns, so a co-stream on a channel row is not modelled the way a member's
   is. Instead: whichever sweep sees it first opens the session; the other logs
   `youtube.live_seen` with `announced: false` and `because: joined_session` and posts nothing;
   and **only the side whose address the session carries ends it**. Which side that is is read
   off the session's own `url` (`spotlight.platform_of`), because no column says it — the Twitch
   sweep's miss counter now skips a session on a `youtu…` address, and the YouTube sweep's skips
   one that is not. The Live-now card and Recent-streams row read the same way, so a YouTube
   session draws a YouTube card, not a Twitch one.

5. **A fourth column, `announce`, landed in the same migration** (owner, mid-build: *"once built
   let's keep esam in the list but opt them out of notifications"*). It is a channel's own
   opt-out, the twin of a member's: `announce_info` returns before it starts a session, so an
   opted-out channel gets no post, no session, no pin and no reminder, and therefore no end
   either — while the row, its ping role, its YouTube link and its spotlight all stay exactly as
   they were. The **Opted out** column on the Streamers list reads it for a channel row the way
   it already reads a member's. Sweep row `CS-g`.
   🔴 **HALF WRONG, and it cost the owner a permanently pinned post — corrected 2026-09-21 on
   branch `channel-optout` (checklist 35).** ~~"no post, no session, no pin and no reminder, and
   therefore no end either"~~ is true ONLY of a channel opted out **before** it goes live. Opted
   out **while a session is open**, the sentence above described nothing that happened: the post
   stayed, the pin stayed, and the session stayed open for ever on a 24/7 rerun channel. The
   opt-out now settles the open announcement per `golive_channel_optout_post` — see
   [**§ Follow-up 2026-09-21**](#follow-up-2026-09-21-opting-out-ends-the-announcement-that-is-already-out).

6. **A member row offers Spotlight whether or not they are linked** (owner, mid-build: *"It
   seems like you need to be linked to be spotlighted. While this is preferred I don't think this
   should be mandatory"*). The **Spotlight this channel…** button used to render only under
   `row.twitch`; it now always renders on a member row with no spotlight, and opens the same form
   with an EMPTY box when there is no link to prefill. The join is unchanged, so a login typed
   that matches a linked member is still ONE row — theirs — carrying the channel's facts. **A
   link is preferred, not required.**

7. **The mock cannot reach YouTube**, so its `PATCH …/{id}` with `youtube` resolves a `UC…` id
   out of the value itself and otherwise knows the owner's two handles by name
   (`KNOWN_CHANNELS`); anything else is refused with the same shape of sentence the bot uses.
   The bot's own path is `client.resolve(...)`, which needs **no API key** — it reads the channel
   page's canonical link, which is exactly how the two ids below were found.

8. **The two YouTube channel ids, resolved 2026-09-21 by `curl` of the channel page** (the same
   canonical link `YouTubeClient.resolve_without_key` reads; no API key was available):

   | Handle | Channel id | Title on the page |
   |---|---|---|
   | `@GamesDoneQuick` | `UCI3DTtB-a3fJPjKtQ5kYHfA` | Games Done Quick |
   | `@esamarathon` | `UC3Oe-jfrIqEGygxYBYyN6jQ` | ESA Speedrunning |

   Both are in the mock seed. ⚠️ **They are NOT on the live rows** — the conductor links them
   through the new route after the deploy (`CS-d`).

9. **`/golive` ▸ Spotlight… is `Channels…`**, and its buttons moved to three rows — the spotlight
   toggle and its moves on row 1, the opt-out / role / YouTube / remove moves on row 2, Add and
   Back on row 3 — because a spotlit, live, roled, YouTube-linked channel now offers eight
   buttons and Discord caps a row at five.

## What was NOT verified

- ⚠️ **NOTHING IN THIS BUILD HAS MET DISCORD.** No panel was opened, no button pressed, no
  announcement posted. The `/golive` ▸ **Channels…** half is exercised only by `pytest` against
  fakes.
- ⚠️ **Nothing has met Helix.** No channel was polled, no real stream announced, pinned, bumped
  or ended. The spotlight-off announcement path is proved by a test asserting the rendered text,
  not by a post in `#go-live`.
- ⚠️ **Nothing has met YouTube live.** The two channel ids were resolved by fetching the channel
  pages, which is a real network read — but `probe_live` was never called against either, so no
  channel row has been announced from a YouTube stream and the either-side join has never run
  outside a fixture.
- ⚠️ **The migration has NOT run on the live database.** Schema 51 → 52 applies at the next
  boot. ✅ **What IS measured (2026-09-21): a hand-built schema-51 `spotlight_channels` holding a
  `gamesdonequick` and an `esamarathon` row was opened by `Database.connect()` and came back at
  schema 52 with `spotlight = 1` and `announce = 1` on both**, the two new text columns NULL — so
  the four `ALTER TABLE … DEFAULT` statements do keep an existing channel behaving exactly as it
  did. What is still NOT measured is that run against the PRODUCTION file, which has rows,
  sessions and fan roles this fixture did not.
- ⚠️ **The site half was pressed against the LOCAL MOCK only**, in `chrome-headless-shell`
  149.0.7827.22 over raw CDP, at 1280 px and 390 px, with **zero console rows** of any kind.
  Verified there: the GamesDoneQuick drawer in BOTH toggle states (spotlight on offers
  *Spotlight off · Extend a week · Let it expire · Bump now · Stop pinning it*; spotlight off
  offers *Spotlight on* alone and the other four are gone), **Add a streamer** with the member
  left blank, and **Link a YouTube channel** on the `rpglimitbreak` row — after which that row's
  YouTube cell read `@GamesDoneQuick`. The Streamers list showed ESA and RPG Limit Break as
  *opted out* and GamesDoneQuick as *kept for ever*.
- **Not exercised at all:** the expiry sweep against a real clock; `pings_fan_role_delete` on a
  real Discord role through **Remove this channel**; the event-card **Spotlight this stream**
  path (it now passes `spotlight=True` explicitly, and its own tests pass, but no event was
  spotlighted end to end).
- **A pre-existing failure, NOT from this build:** `site/mock/discordmock.test.mjs` fails one
  assertion (*the go-live embed: drops the embed stamp*). Measured on a throwaway worktree of
  `main` `9b865b8` — it fails there identically.
