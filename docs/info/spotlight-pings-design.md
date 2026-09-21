# A ping role for a spotlight channel — GamesDoneQuick pings, the way a member's fan role pings

> 🔴 **SUPERSEDED IN PART, 2026-09-21 (branch `channel-streamers`): the spotlight row IS NOW THE CHANNEL RECORD.**
> A `spotlight_channels` row is a channel Black Bloc watches whether or not it is spotlighted — `spotlight` is a
> toggle ON the row (schema 52), beside `announce` (its own opt-out) and `youtube_channel_id` / `youtube_handle`.
> Spotlight OFF announces the channel exactly as a member's go-live is announced and only drops the pin, the
> reminders and the expiry; the row, its sessions and its ping role survive the toggle, and **only Remove this
> channel takes them**. Everything below still describes the spotlight-ON behaviour correctly. Read
> [`channel-streamers-design.md`](channel-streamers-design.md) first.

> **Audience:** the build agent and reviewers. **2026-09-20 22:xx — the modal §C gave a channel row
> now NAMES the role and can RENAME it.** `page-golive.js:addPingRole` is a form dialog that stays
> open on a refusal, with a **Make a new role** / **Use an existing role** segment and a pre-filled
> editable **Role name** box; the drawer's Ping-role group gained **Rename…**. Both reach a channel
> by `spotlight_id` exactly as this design's `POST` does — Deviation 6's point (a channel's door is
> the site and `StreamerPick`, never `GivePick`) is untouched. Branch `ping-role-modal`, design
> [`ping-role-modal-design.md`](ping-role-modal-design.md); LIVE as v150; nothing in it has met Discord. **Status:** TRACKED · ✅ **LIVE as v150** (release `575dde2`, deployed 2026-09-20 23:32 Phoenix; sweeps **685–689**, were `SP-a` … `SP-e`. ⚠️ **The `golive_fan_roles` REBUILD ran at this boot** — `database: rebuilding golive_fan_roles so a role may belong to a channel`; a database backup was taken at 23:30 first. ⚠️ `pings_mode` is still OFF, so `/pings` cannot list channels yet) · was 🔨 BUILT on branch `spotlight-pings`, 2026-09-20,
> off `main` `552af36` (v149 live) — schema **50**, registry **294**, mock **193 routes**; ⚠️ **Merged and LIVE at v150; nothing in it has met Discord.** **Read `## Deviations` (thirteen) and `## What was NOT verified` at the foot BEFORE
> reading §A–§F as built** — the biggest is that `golive_fan_roles` had to be REBUILT, not widened, so the live database
> gets a table rebuild on the next boot. Was: 📐 **DESIGN (Fable, 2026-09-20 19:4x), dispatched to
> Opus as branch `spotlight-pings`** the same turn (owner: *"yes design and build it … I dont see why we're waiting for
> something i just asked for"*). **Last verified: 2026-09-20 19:3x** against `main` `6df0635` (v149 live):
> `black_bloc/pings.py` — the fan-role table is **`golive_fan_roles`** (`get_fan_role(db, guild_id, user_id)` `:187`,
> `all_fan_roles` `:195`, `ensure_fan_role(bot, guild, member, *, by, existing_role, staff, via)` `:375` *"the one path that
> gives a streamer a role of their own"*, `fan_role_name(template, name)` `:156` from `pings_fan_role_template`,
> `announced_fan_role(bot, guild, user_id)` `:221` — what an announcement mentions); `cogs/content/pings.py` — `FollowPick`
> `:932` (the `/pings` select members opt in from; option `value=str(one["user_id"])`), `StreamerPick` `:967`, `GivePick`
> `:991`; `api/tools/pings.py` — `streamer_row` `:32` (`member_id`, `member`, `role_id`, `role`, `followers`), `POST
> /api/pings/streamers` `:114` (`member_id`, optional `role_id`); `cogs/content/spotlight.py` — `_announce` `:433` passes only
> `golive_ping_role_id` (`PING_KEY` `:49`), the bump `:505` *"never a ping"*; `cogs/content/golive.py:941` — where a
> member's announcement resolves its fan role. Schema is **49**; this build takes **50**.

## The ask, verbatim (owner, 2026-09-20 19:3x)

*"i dont see how to add a role to the games done quick entry in streamers"* → *"yes design and build it"*.

Today a fan role is keyed by MEMBER id, so a spotlight channel (no member behind it) cannot hold one: the row drawer's
Ping-role group has nothing to offer, `/pings` never lists GDQ, and the spotlight announcement pings only the global
`golive_ping_role_id`. Members who want *only* GDQ pings have no way to say so.

## A. The model — one table, a second kind of owner

`golive_fan_roles` gains **`spotlight_id INTEGER NULL`** (`ADDED_COLUMNS`; schema 49 → **50**), and its uniqueness becomes
*one row per member OR per spotlight*: keep the existing `(guild_id, user_id)` shape for members and add a partial unique
index `(guild_id, spotlight_id) WHERE spotlight_id IS NOT NULL`; a spotlight row's `user_id` is **NULL** (if the column is
`NOT NULL` today, relax it in the bootstrap the way `posts.channel_id` is nullable — the builder says which in Deviations).
`ON DELETE`: when a spotlight row expires or is removed (`spotlight.forget` / the expiry sweep), its fan role row goes
through the SAME `remove_fan_role` path a member's does, honouring `pings_fan_role_delete` (delete the Discord role or keep
it) and logging `pings.fan_role_removed` with `because: spotlight_expired` / `spotlight_removed`.

**`ensure_fan_role` grows one keyword, `spotlight=None`.** With a spotlight row instead of a member: the role's name comes
from the SAME `pings_fan_role_template` with `{name}` = the channel's display name (*GamesDoneQuick pings*); everything else —
existing-role reuse, the `staff` gate, `pings_fan_role_creation`, the log row (`target` = the spotlight id, `details.spotlight`
= the login) — is the one path. `get_fan_role` gains `get_spotlight_fan_role(db, guild_id, spotlight_id)`; `all_fan_roles`
returns both kinds (rows carry `spotlight_id`, `spotlight_login`, `spotlight_name` when they are that kind).

## B. Where it pings

| Post | Today | After |
|---|---|---|
| a spotlight **announcement** (`spotlight._announce`) | `golive_ping_role_id` only | the same, PLUS the channel's fan role through a `pings.announced_spotlight_fan_role(bot, guild, spotlight_id)` that mirrors `announced_fan_role` (the role gone → a log line, no mention) — rendered by the same mention prefix a member's announcement uses, so the two announcements read alike |
| a **bump** (`spotlight._bump`) | never a ping | still never a ping **unless `spotlight_bump_pings`** (bool, default **false** — a ping every four hours is a lot; the help says so) |
| the **end** edit | no ping | no ping (unchanged) |

## C. Doors

**Site — the Go-live page row drawer** (`page-golive.js`). A spotlight row's drawer gains a **Ping role** group like a
member's: the role and its follower count when there is one; **Add a ping role…** (the SAME `addPingRole` modal, wording
*Give GamesDoneQuick a ping role*, the name preview from `pings_fan_role_template`) → `POST /api/pings/streamers` with
`spotlight_id` instead of `member_id`; **Remove** as a member's. The Streamers list's Ping-role cell shows the role for a
spotlight row too. `golive-join.js`: the spotlight payload carries `role_id` / `role` / `role_wearers` and the join puts
them on the row; its test gains the fixture.

**`/pings` — the member door.** `FollowPick` lists spotlight channels beside members (option value `spotlight:<id>`,
label the channel's name with *· channel* after it), so a member can opt in to GDQ pings exactly as to a person's;
`StreamerPick`/`GivePick` (staff) understand the same value. The `/pings` root card's count line says *N people and M
channels*. `api/tools/pings.py`: `streamer_row` gains `spotlight_id` / `spotlight_login` (and `member_id` null for that kind);
`POST /streamers` accepts `spotlight_id`; `DELETE /streamers/{member_id}` keeps working for members and gains `DELETE
/streamers/spotlight/{spotlight_id}`; `GET /list` includes spotlight channels with `kind: 'spotlight'`. Contract rows + mock
rows (GDQ with a role and 3 followers; one channel with none). The Pings section of the Go-live page (`Everything else`)
renders both kinds.

**Discord — `/golive` ▸ Spotlight… sub-panel** gains **Give it a ping role** / **Remove its ping role** on the picked
channel (staff), the same functions.

## D. Keys — one, `spotlight_bump_pings` (bool, false, group golive via `NAMESPACE_OVERRIDE` like the other
`spotlight_*`), registry + mock + label + `placeSettings` (the *How streams are spotted* drawer) + the join test fixture
(49 → 50 keys on that page). Every posted word is unchanged; the announcement's mention prefix is the existing construct.

## E. Logging

`pings.fan_role_made` / `pings.fan_role_removed` (existing kinds) carry `spotlight` details for that kind; the spotlight
announcement's `golive.spotlight_announced` row gains `pinged_role` (as `golive.announce` does for a member — copy its
detail name); the bump's row gains `pinged: true/false`. No new kinds unless the count guard needs one.

## F. Tests, docs, gate

`tests/test_pings.py` (ensure for a spotlight: name from the template with the channel's name; refuse a second; the
removal path on expiry honours `pings_fan_role_delete`), `tests/cogs/content/test_spotlight.py` (the announcement mentions
the fan role when there is one and the global role too; the bump pings only with the key on; expiry removes the fan role
row), `tests/cogs/content/test_pings.py` (`FollowPick` lists channels; opting in gives the role), `tests/api/tools/
test_pings.py` (the routes, both kinds, staff gate; the refusal in words for a spotlight that does not exist),
`tests/api/test_contract.py`, `tests/storage/test_db.py` (50), `golive-join.test.mjs` (the fixture), the key/kind count
guards. Both `pytest -n 8` orders, `ruff`, ES parse, `check.mjs` (on `MOCK_PORT=8794` — 8797 is the conductor's), the four
node tests, env cleared per `access/deploy.md`. ⚠️ KI-26 (fifteen sightings) and KI-32 as documented. Docs:
`code-notes.md`; this doc's `## Deviations` + `## What was NOT verified`; `architecture.md` (schema 50, keys); `docs/info/
README.md`; `spotlight-design.md` and `pings-remake` design one dated line each; `sweeps.md` rows `SP-a…` (a: on the
Go-live page open the GamesDoneQuick row ▸ Add a ping role… → a *GamesDoneQuick pings* role exists and the row shows it;
b: `/pings` lists GamesDoneQuick · channel and opting in gives the role; c: when GDQ goes live the announcement pings that
role and the global role; d: a bump does NOT ping until `spotlight_bump_pings` is on; e: an expiring spotlight takes its
role away per `pings_fan_role_delete`). NOT `TODO.md` / `DONE.md` / `deploys.log` / `KNOWN_ISSUES.md`. ⚠️ Migrate before
deploy: an added column + a partial index through the bootstrap; `Database.connect` applies it.

## Deviations

*(written by the build agent, branch `spotlight-pings`, **2026-09-20**, off `main` `552af36` (v149
live). Everything §A–§F asks for that is not listed here was built exactly as the body says.)*

1. ⚠️ **The table is REBUILT, not just widened, and the primary key is gone.** §A says relax `user_id`
   "the way `posts.channel_id` is nullable" — but `golive_fan_roles` declared `user_id INTEGER NOT
   NULL` *inside a `PRIMARY KEY (guild_id, user_id)`*, and SQLite cannot drop NOT NULL with `ALTER
   TABLE`. So `Database._set_aside_fan_roles_that_require_a_member` renames the old table before the
   bootstrap and `_restore_set_aside_fan_roles` copies it back afterwards, column by column (the
   intersection of the two shapes, so a file that never got `unworn_since` migrates too) — the same
   two-step `mod_cases` uses. The new shape has **no PRIMARY KEY at all**: two partial unique indexes,
   `golive_fan_roles_one_member (guild_id, user_id) WHERE user_id IS NOT NULL` and
   `golive_fan_roles_one_spotlight (guild_id, spotlight_id) WHERE spotlight_id IS NOT NULL`. Relying
   on SQLite's legacy "NULLs are allowed in a PRIMARY KEY" quirk would have worked and is exactly the
   kind of thing a later `STRICT` table or a rebuild breaks silently. `spotlight_id` is in
   `ADDED_COLUMNS` as well, so a file whose table is already loosened still gains the column.

2. **`all_fan_roles` returns both kinds through a LEFT JOIN, and the member-only callers say so.**
   §A asks for rows carrying `spotlight_login` / `spotlight_name`, which is one join on
   `spotlight_channels`. The cost: every caller that did `int(row["user_id"])` would have raised on a
   channel's row. `pings.member_fan_roles` / `spotlight_fan_roles` are the filtered readers, and
   `row_for` skips a NULL member rather than crashing. Named because the next feature that reads this
   table has to make the same choice: **`prune_empty_roles`, `follower_counts` and the onboarding
   prompt are deliberately members-only.** A channel's role is not pruned after 30 unworn days — it
   goes when the channel goes (§A), the only lifetime the owner asked for — and Discord's onboarding
   *Which streamers?* prompt is built from the streamer LIST, which a channel is not on.

3. **The announcement's detail is `fan_role_id`, not §E's `pinged_role`.** §E says to copy
   `golive.announce`'s detail name, and the name it actually uses is `fan_role_id`
   (`cogs/content/golive.py:1114`). One name, both feeds.

4. **A reminder that pings mentions BOTH roles, not just the channel's.** §B says only *"unless
   `spotlight_bump_pings`"* and names no roles. It uses the same `ping_prefix(golive_ping_role_id,
   fan_role_id)` the announcement does, so a reminder either reads exactly like the announcement or
   pings nobody — there is no third spelling. With the key off the prefix is empty AND
   `allowed_mentions` is `roles=False`, so a role id typed into the template by hand cannot ping.

5. **The `/golive` ▸ Spotlight… sub-panel's move is ONE button that flips**, *Give it a ping role* or
   *Remove its ping role*, never both — the owner's 2026-09-03 rule (a move renders only when it is
   valid). Worst case the row's button row is five, which is Discord's per-row cap exactly: Extend a
   week · Keep for ever · Bump now · the role button · Remove.

6. ⚠️ **`GivePick` was NOT taught `spotlight:<id>`, because it cannot be.** §C asks for
   `FollowPick`/`StreamerPick`/`GivePick` to understand the value; `GivePick` is a
   `discord.ui.UserSelect` and Discord only lets it offer members. A channel's staff door is
   `StreamerPick` (which does list channels, and whose card carries **Make the role again** /
   **Remove their ping role**) and the `/golive` ▸ Spotlight… button. Say the word and it becomes a
   second select beside the user picker.

7. **The `/pings` counts line gains a fourth clause rather than being rewritten.** §C asks for *"N
   people and M channels"*; the line already said *"N streamer(s) seen · M on the list · K with a role
   Discord still has"*, so it now ends *"· **C** spotlighted channel(s) with one"* and `with_role`
   counts people only. One number, one meaning.

8. **The first announcement writes Twitch's own spelling onto the row.** A row added by hand only
   knows the login, so its ping role would have been called *gamesdonequick pings*. `_announce`
   already reads `stream.user_name` for the card; it now saves it as `display_name` when it differs,
   which is what makes the role, the drawer and the Ping-role cell all read **GamesDoneQuick**.
   Measured, not reasoned: the give-a-role test asserted *gamesdonequick pings* before this and
   **GamesDoneQuick pings** after one announcement has run.

9. **`GET /api/pings/list` carries a channel with `last_live_at: null` and `live_count: 0`.** §C says
   the list includes channels with `kind: 'spotlight'` and says nothing about streaming history; the
   sessions live on the Go-live page's own spotlight payload, and copying them here would be the same
   fact in two places. `first_live_at` is the row's `added_at`, the only date this table honestly
   knows. `golive-join.js` skips these rows (a null member id never reaches `reach`), so the page is
   unchanged by them.

10. **The contract's `{spotlight_id}` is Frost Fatales, so the mock seeds IT a ping role too.**
    `check.mjs` pins `spotlight_id: '3'` (the row with no open session), so
    `DELETE /api/pings/streamers/spotlight/{spotlight_id}` needs row 3 to have a role or it answers
    the 404 it should. The mock now holds two channel roles: GamesDoneQuick's (a real `ROLES` entry,
    worn by three people, which is what the page draws) and Frost Fatales' (a role id deliberately NOT
    in `ROLES` — the deleted-by-hand half for a channel). ESA Marathon has none, which is the **Add a
    ping role…** door.

11. **The python contract seed's channel role points at a role the fake guild does not have** (id
    `999999`). The DELETE entry has to succeed on every run, and pointing it at `PLAIN_ROLE_ID` would
    have let `pings_fan_role_delete` take a role the role-grant entries read out of the shared seed.

12. **A row that is BOTH a member's login and a spotlight keeps the MEMBER's ping role in its cell.**
    The join fills a row's `role_*` from the spotlight payload only when the row has none, so the two
    can never disagree about one cell. Both roles still exist and both are still mentioned by their
    own announcement.

13. **NOT done, deliberately:** nothing merged, nothing deployed, nothing pushed to `main`; no key
    flipped — `spotlight_bump_pings` ships **false** as its registry default and no guild row was
    written; `TODO.md`, `DONE.md`, `deploys.log` and `KNOWN_ISSUES.md` untouched; no role is made
    automatically for a channel (there is no `pings_fan_role_creation auto` path for one — staff or
    the first follower makes it, exactly as §A's one path does for a person); the Live-now card and
    Recent streams say nothing about a channel's ping role; `pings_empty_role_days` still ignores
    channels (deviation 2).

## What was NOT verified

⚠️ **Nothing here has met Discord.** No announcement has pinged a channel's fan role in a real
channel, no reminder has been posted with or without `spotlight_bump_pings`, no button on `/golive` ▸
Spotlight… or `/pings` has been pressed, and no member has followed GamesDoneQuick. The whole
verification is `pytest` (both orders), `ruff`, the ES-module parse, `site/mock/check.mjs`, the four
node fixture files and **one headless-browser pass over the MOCK's Go-live page**.

⚠️ **The migration has NOT run on the live database.** Schema 50 was applied by `Database.connect`
into the suite's `tmp_path` files only; the Fly volume has never seen a `golive_fan_roles` without a
PRIMARY KEY. ⚠️ **This one is a table REBUILD, not an added column** (Deviations 1) — the live fan-role
rows are copied out and back inside `connect()`, so migrate-before-deploy is automatic only in the
sense that `connect()` runs before anything reads. A copy of `data/blackbloc.sqlite3` taken before the
deploy is cheap insurance. The rebuild has been exercised on a hand-built schema-49 file
(`tests/storage/test_db.py::test_a_schema_49_file_lets_a_ping_role_belong_to_a_channel_and_keeps_its_rows`)
and nowhere else.

Specifically NOT verified:

- **That Discord renders two role mentions in one announcement prefix.** `ping_prefix` is the
  construct a member's announcement already uses, so this is inherited rather than new — but nothing
  here has been seen in a channel.
- **That deleting a channel's role on expiry is what staff expect.** `pings_fan_role_delete` is a
  server-wide setting and it now reaches channels too; nobody has watched a spotlight expire and found
  the role gone from the server.
- **The 25-option cap with channels on the select.** `FollowPick` caps the COMBINED list at 25, so a
  server with 25 followable people would show no channels at all. The cap is tested; the crowded case
  has never been rendered in Discord.
- **Any browser but the mock's.** What WAS rendered, 2026-09-20 on `MOCK_PORT=8794` through
  `chrome-headless-shell` 149 driven over CDP: the GamesDoneQuick row reads *GamesDoneQuick · CHANNEL
  ONLY · gamesdonequick · — · **GamesDoneQuick pings · 3** · LIVE NOW · KEPT FOR EVER · —*, and its
  drawer carries *Ping role | GamesDoneQuick pings · 3 wearing it | Remove*; the ESA Marathon row's
  Ping-role cell is *—* and its drawer carries *Ping role | none yet | Add a ping role…*. ⚠️ **Neither
  button was pressed in the browser** — the routes behind them are covered by `check.mjs` and the
  suite, not by a click.
- ⚠️ **One pre-existing 400 was seen and left alone:** `GET /api/requests?status=pending&per_page=1`
  answers 400 on the mock (`pending` was retired at schema 23). Nothing on this branch touches that
  route or its caller, and `KNOWN_ISSUES.md` was out of scope.
- **A channel followed by somebody who then leaves the server**, and **two staff pressing Add a ping
  role on the same channel at once** — the partial unique index makes one of them lose and the loser
  gets the *already has a ping role* sentence, but nothing raced them.
