# Pings, remade — one "what pings me" panel, a streamer list fed by going live, raid trains wired in, and Discord's Community onboarding as the front door

> **Audience:** the owner (to settle the forks) and the build agent. **2026-09-20 22:xx —
> `ensure_fan_role` is no longer template-only:** it takes an optional `name=` (the site's modal
> types one), refuses `DUPLICATE_ROLE` rather than making a second role of that name, and its
> TEMPLATE path now REUSES a same-named assignable role instead of duplicating it; the new sibling
> `rename_fan_role` renames one in place (`PATCH /api/pings/streamers/…`, routine kind
> `pings.fan_role_renamed`). Every `/pings` door described below is UNCHANGED — the new arguments
> are optional and the website is their only caller. Branch `ping-role-modal`, design
> [`ping-role-modal-design.md`](ping-role-modal-design.md); ⚠️ not merged, not deployed, nothing in
> it has met Discord. **Status:** TRACKED · ✅ **LIVE as v116** — merge `f420d3a`, release `29c77b6`, deployed **2026-09-17 00:28** Phoenix; landing entry in [`../DONE.md`](../DONE.md) (*"2026-09-17 — PINGS, REMADE"*); the `## Deviations` foot is the truth where it departs from the body; sweeps **435–448** are the owner's (442–445 need a Community server); `pings_mode` is still OFF. Was: 🔨 BUILT 2026-09-17 on branch `pings-remake` off `main` `337d22a` — schema **39**, registry
> **225**, **5986** tests pass in both orders (5889 before), ruff clean, `check.mjs` ok.
> ⚠️ **NOT merged, NOT deployed, and nothing below has met Discord**; §C5's onboarding half is
> proved with fakes only, because this is not a Community server yet. **Read `## Deviations` at
> the foot BEFORE reading §C as built** — eighteen entries, starting with the numbers Discord
> will not publish.
> Before that: 📐 **DESIGN —
> all three forks DECIDED (a) by the owner 2026-09-16 22:5x; dispatch waits on his word.** Owner, 2026-09-16 22:2x–22:4x, verbatim: *"A wire in pings / Also
> for roles can we start a listener, each time someone goes live their added to a streamer list / Then a
> user can opt into a streamer role? / To give some caveats to this whole system. / We're moving to a
> discord community server so that will handle some role stuff. / We need this system to work with"* →
> *"Yes that was the final part. Community and role prompts"* → *"Our role menus will probably retire to
> use discords to turn them off for now"*. Before that, 16:4x: *"lets turn off the pings stuff, make the
> guide staff only. We want to work on the pings experience more"* and *"let's first go over what it
> does before we add to it"* (the walkthrough is in the session; §A restates it).
> **Last verified: 2026-09-16 22:50 Phoenix** — §A read off `main` at `26a55c9` (v115 live);
> `discord.py` 2.7.1 measured to carry `Guild.onboarding()` and `Guild.edit_onboarding(prompts=,
> default_channels=, enabled=, mode=)`. ⚠️ **NOT verified:** Discord's onboarding LIMITS (prompts per
> guild, options per prompt, roles per option) and the endpoint's permission names — the docs page
> would not yield them to a fetch; the build measures them against the live API and writes them into
> its deviations. Nothing here met Discord.

## A. What exists (measured)

| Fact | Where |
|---|---|
| `/pings` (v72) is one member-visible command: member half = the follow / stop-following selects, the Events toggle, start / take away my own ping role; staff half adds Streamers…, Set up the Events role, Settings, Logs. **`pings_mode` is `off` since 16:44 today**, so the command is hidden and the follow moves are gone; **Stop following…** never needed the mode | [`pings-panel-design.md`](pings-panel-design.md), `black_bloc/pings.py` |
| A fan role exists only for a **linked** Twitch channel, made by the streamer (**Start my own ping role**), by staff (**Streamers…**), or automatically at link time when `pings_fan_role_creation = auto` (`pings.maybe_auto_create`). Stored in `golive_fan_roles (guild_id, user_id, role_id)` | `pings.py:461`, `storage/db.py:152` |
| The Events role is one role both feeds point at (`golive_ping_role_id`, `events_ping_role_id`); **Set up the Events role** also puts it on a **Notifications** role menu | `pings.events_role_id`, `phase15-design.md` |
| Go-live detection is `on_presence_update` → `_go_live_once` (Discord presence, anyone in the server, linked or not) plus the Helix poller for linked logins; a go-live announcement reads the Events role and the streamer's fan role, deduplicated, AFTER the cooldown gate | `cogs/content/golive.py:645–661`, `:679`, `:760` |
| Raid trains ping ONE static role (`raidtrain_ping_role_id`) in front of a lineup post; the thread's *"the train moves"* line (who is on air, who is next) pings nobody | `cogs/content/raidtrain.py:1083`, `raidtrain.py:444` |
| Role menus (v77, `rolemenu_mode`) are the bot's self-serve roles: pronouns, play style, mentoring, interests, event alerts, plus approval-gated and TIMED grants and staff-assigned sets. **`rolemenu_mode` set `off` 22:4x today** at the owner's word; the timed-grant reconciler and `Grants…` still work with the mode off | [`role-menus-panel-design.md`](role-menus-panel-design.md) |
| `Member` is granted by **Discord's rules screen**, not the bot (decided 2026-08-26) | `feature-list.md` F17 |
| The server is **not yet** a Community server (owner: "we're moving to"); `discord.py` 2.7.1 can read and write onboarding (`Onboarding`, `OnboardingPrompt`, `OnboardingPromptOption`, `OnboardingMode`); onboarding needs the `COMMUNITY` guild feature and, when enabled, Discord enforces constraints on default channels (the numbers are the build's to measure) | measured in the venv 22:45 |

## B. The decision in one paragraph

Pings becomes the one place a member says **what should ping me**: events, go-lives, raid trains,
and any streamer on a **streamer list** the bot builds by itself — every member Discord ever shows
streaming lands on it the moment they first go live, linked or not. Following a streamer makes their
fan role lazily on the first follow, so roles exist only for streamers somebody wants. Raid trains use
the same roles: when the train moves to a streamer, their followers are mentioned, and "raid trains"
is its own opt-in beside events and go-lives. Discord's **Community onboarding** becomes the front
door for the shared opt-ins: the bot keeps ONE onboarding prompt in step — *"What should ping you?"*
with options for Events, Go-lives, Raid trains — and, as a second prompt, the streamers who have a
role, capped by what Discord allows. `/pings` stays as the in-server door and the only door for
"stop", and the site's Go-live page stays the staff view. The bot's own role menus retire: the
opt-in ones become onboarding prompts, the approval-gated and timed grants stay in the bot because
onboarding cannot do them.

## C. The pieces

### C1. The streamer list (schema 38 → 39)

```
streamers  guild_id, user_id (PK), first_live_at, last_live_at, live_count, platform, login (NULL ok),
           listed (bool, default 1), hidden_by (NULL ok), hidden_at
```

- `golive._go_live_once` and the Helix poller both call `pings.saw_streaming(bot, guild, member,
  platform, login)` — one upsert per go-live, never on the reply path's hot loop more than that. A
  member Discord shows streaming is on the list after their first go-live, whether or not they ever
  linked; a linked login fills `login`.
- **Opt-out is the member's** (staff final say applies the other way too): `/pings` ▸ **Take me off the
  streamer list** hides the row (`listed = 0`, `hidden_by = self`) and drops their fan role if nobody
  wears it; staff can hide or restore anyone (`Streamers…`). A hidden streamer is never re-listed by
  a later go-live unless the member presses **Put me back on the list**.
- The existing opt-out for ANNOUNCEMENTS (`/golive` ▸ Stop announcing my streams) is a different
  thing and stays; §D-4 offers to link them.
- Pruning: a streamer with no go-live for `pings_streamer_stale_days` (default **90**) leaves the
  list on the sweep, keeping their role only if somebody wears it (`pings.streamer_pruned`).

### C2. Roles made lazily, roles reconciled

- `golive_fan_roles` stays the role table. **Follow a streamer…** on a listed streamer with no role
  yet → `ensure_fan_role` makes it (named from `pings_fan_role_template`) and puts it on the follower
  and on the Streamer pings menu (until the menus retire — §C5) — one log row. **Start my own ping
  role** stays for streamers who want the role to exist before anybody follows.
- `pings_fan_role_creation` gains a fourth value **`follow`** (default going forward): the role is
  made by the first follow. `auto` (at link) keeps its meaning.
- A role nobody wears for `pings_empty_role_days` (default **30**) is deleted on the sweep and the row
  cleared, so the server's role count tracks demand, not history (`pings.role_pruned`). The 250-role
  guild cap is the reason this exists.

### C3. Raid trains wired in (owner: "A wire in pings")

- When the sweep marks a slot LIVE ("the train moves"), the thread line mentions that streamer's fan
  role if one exists, and the **raid-train opt-in role** (§C4) once; `allowed_mentions` lists exactly
  those two. `raidtrain_live_posts` still gates the line as a whole.
- The lineup post's static `raidtrain_ping_role_id` keeps working; **Set up the Events role**'s
  sibling, **Set up the raid-train role**, makes or reuses a role and points that key at it, so a
  member opts in from the pings panel instead of asking staff. The reminder DM is unchanged.

### C4. The panel — "what should ping you"

Root, everybody, one embed **What pings you**: three toggles as buttons whose label is the move
(**Ping me for events / Stop event pings**, **…go-lives…**, **…raid trains…** — the events and go-live
toggles are ONE button while both feeds share a role, two when staff split them, as today), then
**Follow a streamer…** (a select over the streamer LIST, not over roles — a streamer with no role yet
is still offered; ≤ 25 with the site named past the cap for staff and the onboarding prompt named for
members), **Stop following…**, **Take me off the streamer list** / **Put me back on the list** (only for
a member who has ever been seen streaming), **Refresh**. Every refusal is a line, as today.
Staff add: the counts line, **Streamers…** (hide / restore / make the role again / remove a role),
**Set up the Events role**, **Set up the raid-train role**, **Onboarding…** (§C5), **Settings**,
**Logs**, **Open on the site**. `pings_mode` off hides the command; **Stop following…** and the three
"stop" halves of the toggles work whatever the mode (access-reducing moves never need a switch).

### C5. Community onboarding — the front door, kept in step by the bot

- **Only when the guild carries the `COMMUNITY` feature.** Without it every onboarding move says so
  in words and the Notifications role menu stays as the fallback; the moment the feature appears the
  reconciler switches over and the menu's own post is taken down (`pings.onboarding_took_over`).
- The bot OWNS two prompts, marked by a title prefix it controls (`pings_onboarding_prompt_title`,
  default *What should ping you?*), and never touches prompts it did not make:
  1. **What should ping you?** — multiple choice, options **Events** (the Events role), **Go-lives**
     (the same role, or its own when split), **Raid trains** (the raid-train role).
  2. **Which streamers?** — multiple choice, one option per streamer who HAS a role, most-followed
     first, capped at Discord's per-prompt limit (measured at build; the panel and the site say *"N
     more on /pings"* past it).
- `pings.reconcile_onboarding(bot, guild)` runs on the 5-minute sweep and after any role make /
  delete: reads `guild.onboarding()`, builds the two prompts from the tables, and writes ONLY if they
  differ (`edit_onboarding(prompts=…)` keeping every foreign prompt and every default channel as it
  found them; `pings.onboarding_synced` with the diff, `pings.onboarding_failed` in words when Discord
  refuses — permissions, constraints, or the feature missing). A prompt option's role is the fan role
  itself, so a member who ticks it in Discord's screen simply wears the role and the bot sees them as
  a follower with no extra bookkeeping.
- Staff **Onboarding…** sub-panel: what the bot's prompts contain now, when they were last synced,
  **Sync now**, **Stop managing onboarding** (`pings_onboarding_managed` → false: the bot leaves the
  prompts as they are and never writes again).
- ⚠️ Enabling onboarding itself (the default-channel constraints) is the OWNER's move in Discord's
  settings; the bot never flips `enabled` (§E).

### C6. Role menus retire (owner: "turn them off for now")

- `rolemenu_mode` is `off` as of 22:4x. The design's retirement: the **opt-in** menus (pronouns, play
  style, interests, event alerts / Notifications, Streamer pings) become onboarding prompts the
  OWNER builds in Discord's screen, or, where the roles are the bot's (Events, raid trains, fan
  roles), the prompts §C5 keeps in step. The **approval-gated** menus, **timed grants** and the
  **staff-assigned** sets (`runner-status`) have no onboarding equivalent and stay in the bot under
  `/rolemenu` ▸ Grants… / Hand roles out…, which the mode does not hide (measure at build: `Grants…`
  must survive `rolemenu_mode off`; if it does not, that is the first fix).
- Nothing is deleted by this design: menus stay in the table, un-posted. A later, separate call
  deletes them.

### C7. Keys (checklist 33), group `pings` unless noted

| Key | Type | Default | Help |
|---|---|---|---|
| `pings_fan_role_creation` | enum self/staff/auto/**follow** | **follow** | when a streamer's ping role is made |
| `pings_streamer_stale_days` | int 7–365 | **90** | days without a go-live before a streamer leaves the list |
| `pings_empty_role_days` | int 1–365 | **30** | days a fan role nobody wears survives |
| `pings_onboarding_managed` | bool | **true** | whether the bot keeps its two onboarding prompts in step (Community only) |
| `pings_onboarding_prompt_title` | text | `What should ping you?` | the first prompt's title (the second is *Which streamers?*) |
| `raidtrain_ping_role_id` | (exists) | — | now self-serve through the panel and onboarding |

Registry 220 → **225**. `pings_mode` stays the master switch.

### C8. Log kinds

`pings.streamer_seen` (routine, once per first go-live), `pings.streamer_hidden` / `_restored` /
`_pruned`, `pings.role_pruned`, `pings.onboarding_synced` / `_failed` / `_took_over`,
`raidtrain.moved_pinged` (routine). The existing `pings.follow` / `unfollow` / `events_on` / `_off`
stay.

### C9. The website

The Go-live page's Pings section gains the streamer list (seen, listed / hidden, role or none,
followers, last live), hide / restore, and the Onboarding card (what the bot's prompts hold, last
sync, Sync now, the managed switch). Routes under `/api/pings/*` stay staff-only. The `pings-follow`
guide is rewritten for the new panel at the build (member audience again once the owner turns the
mode on).

## D. Calls the owner may overturn

1. Roles made on the first follow (`follow`) rather than at link (`auto`) → one key.
2. The 90-day list prune and the 30-day empty-role prune → two keys.
3. The bot owning two onboarding prompts rather than one → §C5.
4. Linking the announcement opt-out to the streamer-list opt-out (one press does both) → one line.
5. Keeping the approval-gated and timed grants in the bot rather than dropping them → §C6.

## E. Out of scope

Enabling Community or onboarding itself (the owner, in Discord's settings); deleting the old role
menus; any change to go-live announcements' wording; per-game or per-category follows; a public
streamer directory page for members (the site stays staff-only for pings); DM digests.

## F. Build brief essentials

One Opus build, est. **250–350k — double it at dispatch per the 2026-09-16 calibration**, worktree
`C:/lcw/bb-pings-remake`, branch `pings-remake`, off `main`. Schema 39. Tests mirror the package:
`tests/test_pings.py`, `tests/cogs/content/test_pings.py`, `tests/cogs/content/test_golive.py` (the
listener), `tests/cogs/content/test_raidtrain.py` (the moved line's mentions), `tests/api/tools/
test_pings.py`, `tests/storage/test_db.py` (the migration). Prove: a presence go-live lists the
streamer once; a second go-live updates `last_live_at` and adds no row; a hidden streamer stays
hidden across a go-live; the first follow makes the role and the second does not; the prune deletes
only unworn roles; the onboarding reconciler writes only on a diff and never touches a foreign prompt;
without `COMMUNITY` every onboarding move refuses in words; the moved line mentions exactly the two
roles. The onboarding limits go into `## Deviations` as measured numbers. Sweep rows `PR-a`…

## G. Forks — one at a time to the owner, recommendation first

- **F-PR1 — the Streamer prompt in onboarding. ✅ DECIDED 2026-09-16 22:50, owner verbatim "A".** (a) Yes, capped at Discord's limit, most-followed
  first — recommended: it is the "turn our roles into Discord's prompts" the owner asked for. (b) Only
  the three shared opt-ins in onboarding; streamers stay on `/pings`.
- **F-PR2 — who lands on the streamer list. ✅ DECIDED 2026-09-16 22:51, owner verbatim "A".** (a) Anyone Discord shows streaming — recommended
  (that is the listener as asked). (b) Only linked members.
- **F-PR3 — role lifetime. ✅ DECIDED 2026-09-16 22:52, owner verbatim "A".** (a) Made on first follow, pruned when unworn 30 days — recommended.
  (b) Made for every listed streamer, never pruned (simple, but the guild role cap is 250).

## Deviations

0. **2026-09-20, branch `spotlight-pings` — `golive_fan_roles` holds a second kind of owner.**
   §C2's *"`golive_fan_roles` stays the role table"* still holds, but a row's owner is now a
   member **or** a spotlight channel (`spotlight_id`, schema 50): `user_id` is nullable, the
   primary key is two partial unique indexes, and `all_fan_roles` returns both kinds.
   ⚠️ **§C2's 30-day unworn prune and §C5's onboarding prompt are members-only on purpose** —
   `pings.member_fan_roles` is what they read. Design:
   [`spotlight-pings-design.md`](spotlight-pings-design.md).

Written by the build agent, branch `pings-remake`, 2026-09-17. Everything §C asks for that is
not listed here was built exactly as the design says. ⚠️ **Nothing below has met Discord**: the
whole verification is `pytest` (5986), `ruff`, `node --check`, `site/mock/check.mjs` and one
browser pass over the MOCK's Go-live page. The onboarding half in particular was proved only
with fakes — see deviation 3.

### The numbers Discord will not publish

1. ⚠️ **Discord's onboarding LIMITS could not be measured, and are not documented anywhere the
   build could reach.** What WAS measured, 2026-09-17:
   - `discord.py` 2.7.1's `discord/onboarding.py` is 369 lines and carries **no numeric
     constant at all** — no cap on prompts, options, roles per option, or title length. Neither
     does `Guild.edit_onboarding` (`discord/guild.py:4912–4966`).
   - Discord's own docs page for the Guild resource
     (`docs.discord.com/developers/resources/guild`) documents the onboarding object, the prompt
     and the prompt option, and **states no limit for any of them** — fetched and read, not
     assumed. The same for `docs.discord.food/resources/guild` and Discord.Net's
     `GuildOnboardingPromptProperties` page. A web search turned up a support-forum request to
     *raise* the prompt limit but no number from Discord.
   - **From the library's docstring** (`Guild.edit_onboarding`): the endpoint needs
     **Manage Server** *and* **Manage Roles**, and raises `Forbidden` / `HTTPException`.

   So the design's *"capped at Discord's per-prompt limit (measured at build)"* could not be
   honoured as written. The build caps the **Which streamers?** prompt at **25** — the same
   number Discord uses for a select menu and the number `/pings` already caps at — and makes it
   a **registry key**, `pings_onboarding_option_cap` (int **1–50**, default **25**), so the
   owner can raise it the day the real number is known without another build. That key is the
   **fifth** of §C7's five, which is how the registry reaches 225: §C7's own table lists only
   four genuinely new keys (`raidtrain_ping_role_id` and `pings_fan_role_creation` already
   existed), so 220 + 4 would have been 224.

   ⚠️ **A cap that is too high is not silent.** Discord refuses the whole write, the reconciler
   catches it, writes `pings.onboarding_failed` with Discord's own words, and the panel and the
   site both say so in a sentence. Nothing else about anybody's pings changes.

2. **`edit_onboarding(prompts=…)` alone was verified to leave the default channels and
   `enabled` untouched — from the library's source, not from Discord.**
   `discord/http.py:2563–2589` builds the PUT payload key by key and omits anything passed as
   `None`, so a call that passes only `prompts` sends only `prompts`. ⚠️ **What Discord does
   with a partial PUT is NOT documented on the page the build could read**, so this is a
   measured fact about the library and an inference about the API. A fake guild in
   `tests/test_pings_onboarding.py` asserts the library half.

   ⚠️ Also measured and worth knowing: `edit_onboarding` re-numbers prompts by their position
   (`p.to_dict(id=i) for i, p in enumerate(prompts)`), so **a foreign prompt round-tripped
   through a write keeps its title, options and roles but gets a NEW id.** Black Bloc's
   reconciler passes foreign prompts through as the objects it read, in the order it read them,
   which is the closest thing to "untouched" the endpoint allows.

3. ⚠️ **NOT VERIFIED: every onboarding path against a real Community guild.** The build has no
   token and the server is not a Community server yet (§A). `reconcile`, the diff, the foreign
   -prompt pass-through, the take-over and the two refusals are proved against a fake guild that
   mimics `Guild.onboarding()` / `Guild.edit_onboarding()`. Sweep rows `PR-h`…`PR-k` are the
   rows that will actually prove it, and they cannot be pressed until Community is on.

### Where the code went

4. **`pings.reconcile_onboarding` is `pings_onboarding.reconcile`.** §C5 names it as a `pings`
   function; `pings.py` was already 987 lines and the house rule is one module per behaviour, so
   onboarding is `black_bloc/pings_onboarding.py` with `tests/test_pings_onboarding.py` beside
   it. It imports `pings`, never the other way round, so there is no cycle and no re-export —
   callers say `pings_onboarding.reconcile(...)`.

5. **The two prompts are owned by EXACT TITLE, not by a prefix.** §C5 says *"marked by a title
   prefix it controls"*. A literal prefix would have put *"What should ping you?"* in front of
   *"Which streamers?"* on a member-facing screen. What shipped: the bot claims exactly the two
   titles it builds — `pings_onboarding_prompt_title` (default *What should ping you?*) and the
   constant *Which streamers?*. ⚠️ **The cost: a foreign prompt titled exactly *Which
   streamers?* would be adopted and rewritten.** The staff sub-panel lists exactly which prompts
   the bot claims, and **Stop managing onboarding** is the one-press way out; changing the title
   key makes a fresh pair and leaves the old ones alone, which the key's help text says.

6. **The take-over takes down the Notifications menu ONLY.** §C5 says *"the menu's own post is
   taken down"*, singular. The *Streamer pings* menus keep being rebuilt by
   `sync_streamer_menus` as before — §C2 says they stay "until the menus retire". It is
   idempotent: the post comes down once, and `pings.onboarding_took_over` is written only when a
   post was actually there to remove.

### The listener

7. **`saw_streaming` runs BEFORE the announcement opt-out, the role filters and the cooldown,
   and after the `golive_mode == off` gate.** F-PR2 decided *"anyone Discord shows streaming"*,
   and §C1 says in terms that the announcement opt-out *"is a different thing"*, so somebody who
   has pressed **Stop announcing my streams** still lands on the list and can still be followed.
   The cooldown is skipped for the same reason — it exists to stop a second ANNOUNCEMENT, and
   letting it stop `last_live_at` moving would make the 90-day prune lie.
   ⚠️ **The consequence worth the owner's eye: `golive_ignore_role_id` no longer keeps somebody
   off the streamer list.** That follows from the literal F-PR2 answer rather than from a
   separate decision; one staff press on **Streamers…** ▸ **Hide them from the list** undoes it,
   and a hide by a person is never undone by going live again.
   `tests/cogs/content/test_golive.py::test_an_opted_out_member_is_never_announced` reverses its
   own earlier assertion and says why.

8. **It is NOT gated on `pings_mode`.** The list is a record of who has streamed; recording it
   pings nobody and changes nobody's roles. Gating it would mean the day the owner turns pings
   on, the list starts empty and every streamer has to go live again before anybody can follow
   them. `golive_mode == off` still stops it, because that is the switch that means "Black Bloc
   is not doing go-live things here".

9. **`hidden_by` is what tells a person's hide apart from a staleness prune**, using the
   design's own columns rather than a new one. `listed = 0` with `hidden_by` set is somebody's
   decision and a later go-live never undoes it; `listed = 0` with `hidden_by` empty is the
   90-day prune, and one more go-live puts them straight back. The site shows who hid whom.

10. **`golive_fan_roles` gains `unworn_since` (an `ADDED_COLUMNS` migration).** §C2's *"a role
    nobody wears for `pings_empty_role_days`"* needs a clock, and `created_at` is the wrong one —
    a role worn for a year and then abandoned would have been deleted on the next sweep. The
    sweep stamps `unworn_since` the first time it sees a role empty, clears it the moment
    somebody wears it again, and deletes only once the stamp is old enough. ⚠️ The role's
    `members` list is re-read immediately before the delete, so a role somebody wears is never
    deleted even if the stamp is stale.

11. **The stale prune gets to an unworn role before the 30-day clock does.** §C1 says a pruned
    streamer keeps their role "only if somebody wears it", so `prune_stale_streamers` drops an
    unworn role in the same move and records it in `pings.streamer_pruned`'s details as
    `role_deleted`. That means the pair leaves **one** log row, not two, when both would have
    fired — which the sweep tests assert by name.

### The panel

12. **Button rows are PACKED, not fixed.** The busiest staff state is 12 buttons (two split
    feeds + raid trains + an own role + the list switch + Refresh + six staff moves) plus the
    site link, and `PanelMove.row` was a constant. `pings.packed` / `pings.free_slot` lay them
    out from row 2 within Discord's five-per-row; `tests/test_pings.py` asserts the worst case
    fits and that no row holds six.

13. **The website's onboarding card does NOT carry the managed switch.** The design's
    *"**Stop managing onboarding**"* is built, on the Discord sub-panel. On the site the switch
    is `pings_onboarding_managed` in the settings block below the card — one fact, one control
    (the surfaces rule) — and the card names where it is. The first attempt put a `modeSwitch`
    on the card and it rendered as an empty box, because `modeSwitch` reads `spec.choices` and a
    bool key has none; that is why this is a deviation and not an oversight.

14. **`POST /api/pings/onboarding/sync` is deliberately absent from `contract.json`.** It
    answers **409 in words** on any guild without the `COMMUNITY` feature — which is every guild
    the contract runner can build — and the runner asserts 200. Its refusals are covered by
    `tests/api/tools/test_pings.py` instead, both of them, including that they leave no log line.

15. **`pings.setup_raidtrain_role` names its role from a module constant, not a key.** The
    Events role has `pings_events_role_name`; §C7 adds no sibling for raid trains, so the role is
    called **Raid trains** and staff pick an existing role instead when they want another name
    (the same `RolePick` the Events set-up uses). Say the word and it becomes a sixth key.

### §C6, measured before anything was built

16. ⚠️ **Two of the three things §C6 says "must" work with `rolemenu_mode` off did NOT.**
    Measured on `main` at `337d22a`, before the fix:

    | Thing | With the mode off | Where |
    |---|---|---|
    | `/rolemenu` itself | ⚠️ **HIDDEN from the guild's command tree** — `hide_commands_when_off` defaults **true** and `HIDDEN_WHEN_OFF` carried `"rolemenu_mode": ("rolemenu",)`, so nothing under it was reachable at all | `command_visibility.py:17,30`; `settings_store.py:1550` |
    | **Grants…** | rendered unconditionally *when the panel could be opened* — `root_buttons` says in its own docstring "the mode never removes a control from the root" | `rolemenus.py:193–202` |
    | **Hand roles out…** | ⚠️ **absent** — gated on `picking_on` | `rolemenus.py:225` |
    | the hand-out WRITE | ⚠️ **refused in words** (`ROLE_MENUS_OFF`) | `cogs/community/role_menus.py:2483` |
    | the timed-grant reconciler | ✅ **ran** — no mode gate in `_expiry_loop`, `run_due_grants`, `_expire` or `reconcile_records` | `role_menus.py:3067–3133` |

    Commit `57ce7cb` is the fix, before any other work: `rolemenu` moves out of
    `HIDDEN_WHEN_OFF` and into `NEVER_HIDDEN` (and into `settings_panel.EXTRA_MODES`, so the
    Settings panel's mode block still carries its row — 17 rows, 14 hidden + 3 hand-added);
    `menu_buttons` draws **Hand roles out…** whenever the menu has options; `run_assign` no
    longer refuses. `PICKING_IS_OFF` was reworded to match. Three tests that asserted the old
    behaviour now assert the new one and say so in their docstrings.

    **2026-09-25 — the console moved (owner, option "B").** `/mod` ▸ **Role grants…** now opens
    the same Grants console (one implementation, `role_menus.open_grants_from`; Back returns to
    `/mod`), so `rolemenu_mode` went back into `HIDDEN_WHEN_OFF` and `/rolemenu` hides while role
    menus are off. Branch `hide-rolemenu`; why in `code-notes.md` ▸ *`/mod` ▸ Role grants… and
    `/rolemenu` hiding again*.

### The guide

17. ⚠️ **`guides.refresh_seed_text` updates ONLY `seed_do` / `seed_expect`.** The rewritten
    `pings-follow` entry changes its title, goal, **audience**, faults and facts as well, and
    none of those reach a database that already holds the guide. **The guide's *Reset to seed*
    is what takes them** — and `audience` is set to `staff` in the seed to match what the owner
    did to the live guide on 2026-09-16, so the conductor flips the seed and the live row back
    to `member` together with `pings_mode`. Two member-guide counts fell 10 → 9 and say why.

### Not built

18. **Nothing was cut.** §C1–§C9 are all here, including §C5's staff sub-panel and §C9's
    Onboarding card, which the brief named as the first and last things to drop.
