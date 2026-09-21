# A ping role for a spotlight channel — GamesDoneQuick pings, the way a member's fan role pings

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **DESIGN (Fable, 2026-09-20 19:4x), dispatched to
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

*(the build agent writes here what it had to do differently, dated)*
