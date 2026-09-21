# Go-live / Twitch — `/golive` is ONE command that opens a panel (wave 2)

> **Audience:** the build agent, the reviewer and the owner. **Status:** TRACKED · ✅ **Follow-up 2026-09-21
> LIVE v153 12:13** — [a member's opt-out ends the announcement that is already out](#follow-up-2026-09-21-a-members-opt-out-ends-the-announcement-that-is-already-out),
> merge `1deb296` of branch `member-optout`, release commit `3d75254`; read that section's own banner and its
> `### Follow-up deviations` — the body below is the v70 build. · ✅ **SHIPPED v70
> `0aeed72` 2026-09-03 17:25** (merged from the branch below after Fable review; boot measured `commands synced`
> **41**; 3796 tests; nothing run against Discord by eye — sweeps 109–117 are the owner's). Written as BUILT
> 2026-09-03 on branch `worktree-agent-a87a00d41b8dc47d1` (off `main` `8cbe453`, v67 live), in
> four commits — code, tests, the cross-feature string sweep, docs. **3756 tests pass** (3710 on
> the base commit, +46, none lost), `ruff check .` clean, `node site/mock/check.mjs` reports the
> same **17 pages / 142 routes** as `main`, and `labels.js` parses. `commands synced` is
> **41**, one lower than the base's 42, **measured** through
> `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits` — ⚠️ **no boot was
> run** (no bot token here) at build time, and **nothing has met live Discord**: no panel opened, no
> button pressed, no Helix call made. ⚠️ **The sentence "Not merged and not deployed" that stood here
> was stale from the moment the merge happened** — it was written on the branch and never updated;
> this build merged as `0aeed72` and shipped as **v70** the same afternoon (`deploys.log`), and it is
> still live at **v108** (`73e2e44`, 2026-09-11 00:37). Both owner forks were decided
> before the build and built as decided: **I1 = `/golive`**, **I2 = build the `Streamers…`
> sub-panel**. ⚠️ **Read the `## Deviations` foot before trusting the body of this doc.**
> **Since then, four things this document predates:** **v78** (`3429233`) gave `golive_mode` a
> `HIDDEN_WHEN_OFF` entry (`command_visibility.py:23`), so `/golive` DOES vanish while the mode is
> off, behind `hide_commands_when_off`; **v84** (`ce97de0`) corrected `LOG_LEVEL_COMMANDS` so
> `golive_log_level`'s help names `/golive` ▸ **Logs** rather than a retired `/golive logs`;
> **v92** (`4b327cf`) folded the youtube/golive site-link copy onto the shared helper; **v93**
> (`09ff46b`) folded `golive.db_up` and added the AST guard that stops a cog keeping its own copy
> (`cogs/content/golive.py:56`, `:1244`, `:1321`).
> ✅ **"Findings, reported and NOT fixed" #1 is CLOSED** — all four wave-1 `*_panel_minutes` keys have
> `labels.js` rows today (`:102`, `:117`, `:129`, `:193`), along with every later panel's.
> **Last verified: 2026-09-11 08:58** — re-measured in this tree at `1d090e5`: `golive_panel_minutes`
> registered beside **thirteen** other `golive_*` keys (registry **202**); every move label §C names
> still reads the same string — `LINK_CHANNEL` / `CHANGE_CHANNEL` / `UNLINK_CHANNEL` /
> `STOP_ANNOUNCING` / `ANNOUNCE_AGAIN` / `STREAMERS` (`golive.py:391–398`) and `PREVIEW_PICK`
> (`cogs/content/golive.py:122`); sweeps landed as rows **109–117** and the file runs to **350**;
> `site/mock/contract.json` **150 routes / 17 pages** (142 at the build).
> ⚠️ **NOT checked in this pass:** anything in a Discord client, on Twitch or in a browser; no boot,
> no pytest, no ruff, no `check.mjs` run; the flaky-test note below was not re-run.
> **Before that, 2026-09-03** — every `path:line` below was READ at `f49e493` (`main`) in
> `black_bloc/cogs/content/golive.py`, `black_bloc/golive.py`, `black_bloc/panels.py`,
> `black_bloc/guard.py`, `black_bloc/settings_store.py`, `black_bloc/command_visibility.py`,
> `black_bloc/actionlog.py`, `black_bloc/logkinds.py`, `black_bloc/personas.py`,
> `black_bloc/chat.py`, `black_bloc/pings.py`, `black_bloc/raidtrain.py`,
> `black_bloc/api/tools/golive.py`, `tests/test_bot.py`, `docs/access/sweeps.md`,
> `docs/info/code-notes.md`. The command count (**42**) is `tests/test_bot.py:198`. The string
> sweep in §E was measured by grep for `/golive` and `/twitch` across `black_bloc/`, `site/`,
> `tests/` and `docs/`.
> ⚠️ **NOT verified: anything against live Discord or Twitch.** Nothing was booted, no panel
> opened, no button pressed, no Helix call made. Four wave-2 design agents are writing sibling
> docs in parallel, so the line numbers will drift by their merges — **trust the anchor text over
> the number**, and re-key `code-notes.md` after the merge as the standing rule says. Secret
> NAMES only appear here (`TWITCH_CLIENT_ID`, `TWITCH_CLIENT_SECRET`, `TEST_CHANNEL_ID`).
>
> **Inherits every invariant in [`panels-program.md`](panels-program.md) §2 (P1–P17) and its §4
> library (`black_bloc/panels.py`) — none restated here.** Template:
> [`requests-panel-design.md`](requests-panel-design.md); read its `## Deviations` foot as the
> trap list, plus [`events-panel-design.md`](events-panel-design.md) deviations 4, 6, 8, 13 and
> 15 and [`applications-panel-design.md`](applications-panel-design.md) deviations 1, 4 and 15.
> Feature behaviour is [`phase2-design.md`](phase2-design.md) (F1 + F2 + the F5 hook).

## A. Measured today — two groups, eight subcommands

`golive` is a `Group` (`cogs/content/golive.py:311`) and `twitch` is a `Group` (`:312`).
**Neither carries `default_permissions`** — both are in `MEMBER_COMMANDS` (`tests/test_bot.py:61`,
`:69`), and the staff half is gated at runtime by `require_staff` (`settings_store.py:1198`).
**6 + 2 = eight leaf subcommands over two top-level slots.**

| Subcommand | Line | Who | Calls · what is INLINE in the cog |
|---|---|---|---|
| `/golive logs` | `:848` | staff — `send_logs` carries its own `require_staff` (`actionlog.py:295`) | `send_logs(interaction, "golive", count, important_only)`. Nothing inline |
| `/golive optout` | `:857` | anyone, own row | `set_optout` `:162` + `_fan_role_after_leaving` `:1053` + `_log_command` `:1062`; the sentence `OPTED_OUT` `:60` is inline |
| `/golive optin` | `:869` | anyone, own row | `clear_optout` `:169`; ⚠️ **inline**: the `OPTED_IN` / `NOT_OPTED_OUT` branch and the conditional log |
| `/golive status` | `:880` | `require_staff` `:881` | ⚠️ **all inline** `:885–910`: `counts` `:276`, `_polling_summary` `:664`, `end_summary`, `open_sessions` `:245`, eleven lines built by hand |
| `/golive mode` | `:917` | `require_staff` `:920` | ⚠️ **inline** `:922–934`: `store.set` + the sentence + `log_action("golive.mode")` |
| `/golive test` | `:941` | `require_staff` `:946` | ⚠️ **inline** `:948–970`: `TEST_STREAMS` `:90` or the caller's own activity → `render` → `_embed` `:515` → **an EPHEMERAL reply** → `log_action("golive.test")` |
| `/twitch link <channel>` | `:974` | anyone, own row | ⚠️ **inline** `:977–1025`: `clean_login` `:292`, `link_owner` `:147` clash check, `helix.get_users`, `set_link` `:128`, `_auto_fan_role` `:1044`, three sentences, the log |
| `/twitch unlink` | `:1028` | anyone, own row | `remove_link` `:156` + `_fan_role_after_leaving` `:1053`; the sentence is inline `:1035–1041` |

⚠️ **`/golive test` does NOT post anything.** It answers `interaction.response.send_message(...,
ephemeral=True)` `:962` and renders **without** the ping-role prefix — `code-notes.md:593` records
that as a review fix, not an accident ("a staffer running a preview posted a real, visible message
into the channel and pinged whatever `golive_ping_role_id` names"). It writes no session, moves no
role and never reaches `_post` `:558`, so **`guard.allows_channel` (`guard.py:60`) is not in its
path at all.** §C keeps it that way; see §C's *Where the preview may go* for what the panel says
about the real channel instead.

**Not subcommands and NOT moving** (P14): the presence listener `on_presence_update` `:382`, the
60-second `poller` `:738` → `poll_once` `:794`, the announcement path `_go_live_once` `:398`, the
end path `_end_live` `:471` / `_close_session` `:358`, `reconcile_open_sessions` `:330` and
`age_out_sessions` `:750`. **The panel adds no new writer of a session row and no second
announcer.**

**The audience split is two-way, not three:** member (`link`, `unlink`, `optout`, `optin` — all on
`interaction.user`) and staff (`status`, `mode`, `test`, `logs`). There is no approver role here.

**The states the panel renders from** are four independent facts, not a state machine:

| Fact | Read by |
|---|---|
| linked / not linked | `get_link(db, user_id)` `:137` |
| opted out / opted in | `is_opted_out(db, user_id)` `:180` |
| `golive_mode` `off` / `shadow` / `on` | `_mode` `:689` |
| Twitch app configured or not | `self.helix is None` (`config.py:98` `twitch_configured`) |

## B. The decision — one `/golive`, member panel and staff panel

**`/golive` becomes a single `app_commands.command`; BOTH `Group`s go and `/twitch` disappears.**
`commands synced` drops by **one** relative to whatever it is when this lands (42 today). ⚠️ **The
build MEASURES it, never asserts an absolute** — four sibling wave-2 features each drop one too and
the conductor reconciles at merge (requests deviation 7).

**The one command stays member-visible** — no `default_permissions`, because both groups are
member-visible today. `"twitch"` leaves `MEMBER_COMMANDS` (`tests/test_bot.py:69`); `"golive"`
`:61` stays. **Nothing changes in `command_visibility.py`** — measured, `HIDDEN_WHEN_OFF`
(`:16–20`) has no `golive_mode` entry, so `/golive` never vanished and still will not.

Root panel — `build_panel(bot, guild, actor)`, one ephemeral embed + `Panel` subclass, split on
`store.is_staff(actor)` (P2). Discord caps a row at 5 controls and a view at 5 rows; this uses 4.

| Row | Member sees | Staff sees additionally |
|---|---|---|
| 0 | `Link my Twitch channel` (primary) **when not linked** · `Change my channel` (secondary) + `Unlink` (danger) **when linked** | — |
| 1 | `Stop announcing my streams` (danger) **when not opted out** · `Announce my streams again` (success) **when opted out** — exactly one ever renders (P3) | — |
| 2 | `Refresh` · `Open on the site` (link, `golive.html` — `logkinds.py:93`, only with an origin) | `Logs` · `Streamers…` (**fork I2 only**) — 4 controls, inside the cap |
| 3 | — | Select **"Preview an announcement…"**: *As you are now* · *Twitch* · *YouTube* |
| 4 | — | Select **"Announcements: off / shadow / on"** (`GOLIVE_MODES`), the current value as the default option |

**Member embed — `Go-live`.** One intro line; **your Twitch channel** (`twitch.tv/<login>`, when it
was linked, and "not verified with Twitch" when `twitch_user_id` is NULL — checklist 10, the same
honesty `LINK_NOT_CHECKED` `:79` carries today); **whether your streams are announced** (opted out,
or announced-when-seen); and, when `golive_mode` is not `on`, one line saying announcements are
**off** or in **shadow** right now — as a LINE, never a refusal of the whole command and never a
dead button (P9, the applications I-A2 precedent). Linking still does something with the mode off
(raid trains require a link — `raidtrain.py:56`; fan roles are made from one — `pings.py:79`), so
every member control renders in every mode.

**Staff embed — the member embed plus `/golive status` verbatim.** `status_lines` (§F) is the
eleven lines `:890–907` unchanged: mode · stream end · channel · cooldown · twitch polling · last
good poll · last poll error (+ failures in a row) · links / opt-outs / live now · one line per open
session. ⚠️ **There is no `Status` button** — the status IS the staff embed, which is one click
fewer and keeps checklist 9 (health, not liveness: `code-notes.md:592` records that `is_running()`
alone once reported a Twitch outage as healthy).

**No Settings sub-panel, deliberately.** The site's Go-live page owns the twelve `golive_*` keys —
the template preview, the end wording and the role filters all live in `page-golive.js` — and
one-fact-one-home says the panel must not become a second editor for them. The only key the panel
WRITES is `golive_mode`, because `/golive mode` is a subcommand being retired and its move has to
land somewhere. Everything else is `Open on the site` and `/settings set-value` (checklist 33 is
met: every key is in the registry already). This is the opposite call to `events`, and for the
opposite reason — events had **no** site section to point at.

## C. The moves, the modal, the preview

Each is a **re-render in place**: `retire(previous)` (P6), `defer()` then `edit_original_response`
(P5), `db_ready` on every click after the defer (requests deviation 6), `still_staff` before every
staff move (P8 — never `require_staff` after a defer, which answers through
`interaction.response` `:1205` and is requests deviation 11 exactly).

| Control | State it renders in | Shared function it calls (§F) |
|---|---|---|
| `Link my Twitch channel` | no `golive_links` row | `LinkModal` → `link_channel(...)` — `clean_login` `:292`, the `link_owner` `:147` clash, the Helix check, `set_link` `:128`, `_auto_fan_role` `:1044`, one `golive.link` row |
| `Change my channel` | a row exists | the same modal, **prefilled** with the stored login, the same `link_channel` |
| `Unlink` | a row exists | `unlink_channel(...)` — `remove_link` `:156` + `_fan_role_after_leaving` `:1053`, one `golive.unlink` row |
| `Stop announcing my streams` | not in `golive_optout` | `opt_out(...)` — `set_optout` `:162` + the fan-role sentence, one `golive.optout` row |
| `Announce my streams again` | in `golive_optout` | `opt_in(...)` — `clear_optout` `:169`, one `golive.optin` row |
| `Logs` | staff | a NEW ephemeral followup (P11), `send_logs(interaction, "golive")`, which keeps its own `require_staff` |
| "Preview an announcement…" | staff | `preview(...)` → a NEW ephemeral followup + one `golive.test` row |
| "Announcements: off/shadow/on" | staff | `set_mode(...)` — `store.set` + one `golive.mode` row, then re-render |
| `Streamers…` | staff, **fork I2 only** | the sub-panel below |

**`LinkModal`** — `panels.NoteModal` is a paragraph field; this is one SHORT line, so it is a
three-line subclass of `discord.ui.Modal` + `AnswersErrors` (P12, checklist 8), title *Your Twitch
channel*, label *The name after twitch.tv/*, `max_length=25` (`clean_login`'s own bound `:296`),
`default=` the stored login when changing. Refusals stay the sentences that exist: `BAD_LOGIN`
`:71`, `LINK_TAKEN` `:84`, the "Twitch has no channel called…" line `:999`, `LINK_NOT_CHECKED`
`:79`. ⚠️ **A modal cannot `defer()` first**, and building a prefilled modal READS the link row —
so the button that opens it needs the pre-defer database gate (`db_up`, applications deviation 15),
not the library's `db_ready`, which answers a followup.

**Where the preview may go.** The preview is ephemeral (§A) and is not changed by this build — it
still never posts, never pings and never writes a session. What the panel ADDS is the sentence the
old `/golive status` did not say: when `bot.guard` is not None and
`guard.allows_channel(golive_channel_id)` (`guard.py:60`) is False, the **channel** line reads
`<#id> — but test mode means nothing is posted outside <#TEST_CHANNEL_ID>`, which is
`guard.refusal_message()` `:88` in the panel's own words. That is the honest answer to "why did my
real stream not get announced", in words and never a stack trace (owner rule: what happened, what
it needs, how to get it). **Nothing in this build may weaken the guard**, and the announce path is
untouched.

**`Streamers…` sub-panel (fork I2 only).** Select over `all_links` `:142`, **capped at 25** with
`panels.capped_placeholder` (`panels.py:56`) and `panels.option_label` for the label; picking one
re-renders a small card — display name, `twitch.tv/<login>`, verified or not, opted out or not —
with `Unlink them` (danger, confirm), `Opt them out` / `Opt them back in`, and `Back`. Every one is
the SAME function the member's own button calls, with a `target` that is not the actor, which is
exactly what the five site routes (`api/tools/golive.py:94–162`) already do. No new query, no new
route, no new key.

## D. Settings (P13 · checklist 33)

| Key | Type | Default | Status |
|---|---|---|---|
| `golive_panel_minutes` | `int` | **10** | **NEW.** How long the panel stays live. Help text follows `event_panel_minutes` (`settings_store.py:972`) and carries the KI-20 warning verbatim in shape: 15 or more loses the "gone quiet" footer because Discord's interaction token expires at 15 minutes. Registered in **its own block** after the polls block (`:986–1001`) with a `default()` branch beside `poll_panel_minutes` (`:1353`), so the five parallel wave-2 branches merge textually (`panels-program.md` §5) |

**Nothing else here is a decision.** The 25 cap and the 5-per-row cap are Discord's; the control
table is the four facts in §A; and the twelve existing `golive_*` keys (`settings_store.py:147–158`
`KEY_TYPES`, `:446–464` `KEY_HELP`, `:1267–1284` `default()`) are untouched — the panel READS
`golive_mode`, `golive_channel_id`, `golive_end_mode`, `golive_end_suffix`,
`golive_cooldown_minutes`, `golive_template`, `golive_embed` and WRITES only `golive_mode`.
**There is no `golive_panel_own_link` key**: a member's own Twitch login is data they typed about
themselves, not somebody else's row, so the requests/applications own-list question does not arise.

## E. What goes away, and every line that names it

`/help` reads the tree (`cogs/core.py:113`), so it follows with no edit (P15).

| Thing | Where | Becomes |
|---|---|---|
| `golive` Group | `cogs/content/golive.py:311` | `@app_commands.command(name="golive")` |
| `twitch` Group + both children | `:312`, `:974`, `:1028` | the Link/Change modal and `Unlink` |
| the six `/golive` children | `:848`, `:857`, `:869`, `:880`, `:917`, `:941` | buttons, two selects, the staff embed |
| `_database_ready` | `:836` | `panels.db_ready` after a defer, plus a pre-defer `db_up` for the modal openers |
| `LOGS_GROUPS["golive"]` | `tests/test_bot.py:12` | **deleted** — `/golive` is no longer a `Group` with a `logs` child, and the loops that read it would `KeyError` |
| `MEMBER_COMMANDS` `"twitch"` | `tests/test_bot.py:69` | **deleted**; `"golive"` `:61` stays |
| `assert len(top) == 42` | `tests/test_bot.py:198` | **one lower than whatever the build measures**, never a hard-coded absolute (§B) |
| `NOT_OPTED_OUT` `:68` · `NOT_LINKED` `:75` | the cog | **unreachable and deleted** — the panel never renders `Opt in` to somebody who is opted in, nor `Unlink` to somebody with no link (P9). Events deviation 15 is the precedent. ⚠️ `api/tools/golive.py:30`/`:34` have same-named strings that STAY — different door, different sentence |

**Strings that name a retired subcommand and are rewritten in the SAME commit** — each currently
tells somebody to type something that will not exist:

| File | Lines | What it says |
|---|---|---|
| `cogs/content/golive.py` | `:61` `:66` `:79` `:1014` `:1037` | "Run `/golive optin`", "`/golive optout` turns it back off", "run `/twitch link` again later", "`/twitch unlink` undoes it", "`/golive optout` stops that too" |
| `black_bloc/personas.py` | `:76–77` | ⚠️ **the chat bot's own command list** — two lines (`/twitch` and `/golive`) collapse to ONE `/golive` line naming the panel, in the shape `:95–96` already uses for `/apply` |
| `black_bloc/chat.py` | `:491–498` | ⚠️ **all five `link_twitch` answers** say `/twitch link` and one also says `/golive optout` — this is what Black Bloc replies to "how do I link my twitch" |
| `black_bloc/pings.py` | `:79` (`NOT_A_STREAMER`), `:449` (docstring) | "Link your channel with `/twitch link <your twitch channel name>` first" |
| `black_bloc/raidtrain.py` | `:56` (`NEEDS_LINK`), `:234` | "Run `/twitch link <your channel name>` and claim the slot again" |
| `cogs/content/raidtrain.py` | `:123` | the same refusal for the site's door |
| `black_bloc/settings_store.py` | `:759` | `raidtrain_require_link`'s help text |

**Site touch points — measured, and smaller than expected.** `black_bloc/api/tools/golive.py`
names **no** slash command (its `NOT_LINKED` `:30` and `NOT_OPTED_OUT` `:34` point at the tables),
and `site/public/assets/page-golive.js` names none either. The only site strings that name a
retired command belong to raid trains: `site/mock/server.mjs:403` (the mirror of
`settings_store.py:759`) and `:2514` (the mock's 409). **No route is added or changed in shape**, so
`node site/mock/check.mjs` must report the same page/route counts as `main`.

**Tests that assert a retired string** and move with it: `tests/cogs/content/test_raidtrain.py:343`
`:525`, `tests/cogs/content/test_pings.py:334`, `tests/api/tools/test_raidtrain.py:300`,
`tests/test_chat.py:161–162`.

**Docs rewritten in the same commit** (P15): `docs/access/sweeps.md` rows 12 (`:71`), 19 (`:78`),
31 (`:90`), 49 (`:107`) and the Phase 2 appendix block (`:125–131`, six slash lines) — rewritten in
place, not added to; ⚠️ the **verified** row `:53` (`2026-08-27 · /golive test`) is HISTORY and is
left exactly as it is. `docs/KNOWN_ISSUES.md:72` (KI-15 names `/twitch unlink`);
`docs/info/architecture.md:190`; `docs/info/feature-list.md:39` (F1 names `/twitch link`);
`docs/access/OWNER_GUIDE.md:67` (names `/golive logs`) and `:71` (the sweeps count);
`docs/info/panels-program.md:78` (the Go-live row → shipped). The phase docs get **one dated
"superseded by the panel" line at the top and no rewrite**: `phase2-design.md:113–125`,
`phase12-design.md:75` `:91–92`, `phase15-design.md:27` `:39` `:42` `:99–100` `:118`,
`phase16-design.md:24`, `phase18-design.md:36` `:53`. `docs/info/code-notes.md` is re-keyed at the
merge — the golive anchors `:98 :132 :135 :185 :230 :313 :330 :341 :556–595`, and specifically
`:571` (⚠️ the note explaining that `self.twitch` is the Group attribute and the client is therefore
`self.helix` — with the group gone the note must be rewritten, and **`self.helix` is NOT
renamed**), `:590` (`_database_ready`), `:592` (health, not liveness — its home moves onto the staff
embed) and `:593` (already marked `GONE (was :767)`; this build gives that note a live anchor again
on the preview select). ⚠️ `docs/TODO.md` and `docs/DONE.md` are the **conductor's** to land, not
the build's (events deviation 14).

## F. Extractions (P4) — one function per move, called by BOTH doors

⚠️ **The DB layer stays in the COG.** `api/tools/golive.py:8–20` imports eleven names from
`cogs.content.golive`, exactly as applications does (§F there). **Do not move the layer**; this
build adds to it in place. `black_bloc/golive.py` (the pure module) takes only the things with no
Discord and no database in them.

**New, module level in `cogs/content/golive.py`** — each does ONE write and ONE log row, each takes
`target` (who it is about) separately from `actor` (who pressed), and each takes
`via: str = VIA_DISCORD` so the kind is built by `logkinds.kind_via` (checklist 34):

| Function | Replaces |
|---|---|
| `link_channel(bot, guild, actor, target, given, *, helix=None, via)` | the inline body `:977–1025` (+ `POST /api/golive/links` `:105`). ⚠️ **`helix` is a parameter, not read off a cog** — a module function has no `self`, and it is what keeps the site's contract: the route passes `helix=None` and its `"checked": False` / `LINKED` `:42` sentence stays literally true (checklist 10). Returns `(outcome, row)`, where outcome is one of `bad_login` / `taken` / `no_such_channel` / `linked` / `linked_unchecked` |
| `unlink_channel(bot, guild, actor, target, *, via)` | `:1031–1042` (+ `DELETE /api/golive/links/{user_id}` `:94`) |
| `opt_out(bot, guild, actor, target, *, via)` · `opt_in(bot, guild, actor, target, *, via)` | `:860–866` and `:872–877` (+ `POST /api/golive/optouts` `:135` and `DELETE /api/golive/optouts/{user_id}` `:149`) |
| `set_mode(bot, guild, actor, value, *, via)` | inline `:922–934` |
| `status_lines(bot, cog, guild) -> list[str]` | inline `:885–907`, `_polling_summary` `:664` included — the staff embed and any future door read one builder |
| `preview(bot, guild, actor, platform) -> tuple[str, Any, dict]` | `:948–961` — the render, the embed and the log details, WITHOUT the reply and WITHOUT the log call, so the caller keeps the ephemeral contract |
| `panel_minutes(store, guild_id)` | one line over `panels.panel_minutes` (`panels.py:76`), exactly as `requests.py:510` |

⚠️ **Each door keeps its own SENTENCES.** The five routes word themselves for a staffer acting on
somebody else (`LINKED` `:42`, `OPTED_OUT` `:46`, `OPTED_IN` `:47`) and the cog words itself for a
member acting on themselves (`OPTED_OUT` `:60`, `OPTED_IN` `:66`). Forcing one wording on both
audiences would be worse English, so the shared function owns the **write and the log row** and
returns an outcome the caller words. Checklist 34 is satisfied by the log count, which is what the
test asserts — **five `note()` calls (`api/tools/golive.py:102` `:119` `:142` `:157`) are deleted**,
the same move requests deviation 8 made.

**Pure, into `black_bloc/golive.py`** (no DB, no Discord):

| New | Signature |
|---|---|
| `PanelMove` + `PANEL_BUTTONS` + `panel_buttons(*, linked, opted_out, staff)` | §B's table AS DATA, proved by a parametrised test over all eight member combinations |
| `card_lines(login, verified, opted_out, *, mode, channel_note)` | the member half of the embed |
| `PANEL_TIMEOUT_FOOTER = "This panel has gone quiet — run /golive again"` | the constructor argument `Panel(minutes, footer=…)` takes (wave-0 deviation 1) |

⚠️ **`PanelMove` is a LOCAL `NamedTuple`, not a move of `requests.MoveButton` into `panels.py`.**
One-fact-one-home says fold them; five wave-2 builds editing `panels.py` at once is the exact
conflict `panels-program.md` §5 exists to avoid. **Fold after wave 2, as the conductor's job**
(events deviation 16 and applications §F say the same thing). Same rule for
`panels.option_label` — if a sibling wave-2 build has already generalised it, use theirs; never a
fifth copy.

## G. Tests (P16 — one file per source file, mirrored paths)

| File | What it gains |
|---|---|
| `tests/cogs/content/test_golive.py` (1640 today) | `/golive` answers ephemerally with a panel; a member sees the link controls, the opt control, Refresh and the site link and **no** Logs / preview / mode; staff see all of it plus the status lines; **parametrised over linked × opted-out × staff — the panel renders exactly its §B row and no other**; each control calls its shared function with `via` untouched (mock it); the mode select writes `golive_mode` and logs ONE row; the preview answers a NEW ephemeral followup, carries **no ping-role prefix** and posts nothing (assert `_post` is never called); the channel line names test mode when `guard.allows_channel` is False; `Logs` answers a NEW followup and still refuses a demoted staffer; a staffer demoted mid-panel moves nothing (`still_staff`, every site); `db_ready` after a defer and `db_up` before the modal; timeout disables every item and a re-render `retire`s the view it replaced |
| `tests/test_golive.py` (532) | `panel_buttons` for all eight member states plus the staff overlay; `card_lines`; the footer constant |
| `tests/api/tools/test_golive.py` (185) | the five routes answer the same shapes and now log through `kind_via` — **assert the log-row COUNT, not just the kind** (checklist 34 is the one this build can fail silently); `POST /api/golive/links` still returns `"checked": false` because it passes `helix=None` |
| `tests/test_settings_store.py` | `golive_panel_minutes` round-trips, defaults 10, has help text; the twelve existing `golive_*` keys unchanged |
| `tests/test_bot.py` | `LOGS_GROUPS` loses `golive`; `MEMBER_COMMANDS` loses `twitch`; the tree-limit test recounts (42 → 41 for this feature alone) |
| `tests/test_logkinds.py` | **no new kind** — `golive.link/unlink/optout/optin` and their `web.` heads all exist (`logkinds.py:198–208`), and `kind_via` produces exactly those strings |
| `tests/test_chat.py` `tests/cogs/content/test_raidtrain.py` `tests/cogs/content/test_pings.py` `tests/api/tools/test_raidtrain.py` | the rewritten sentences (§E) — assertion text only |

The existing detection tests (`extract_stream`, `poll_once`, `_go_live_once`, the end paths,
reconciliation, the age-out, the live role) **stay green untouched** — that is the proof this build
changed nothing about announcing (wave-0 deviation 4).

## H. §J — prove before merge (P17), and the sweep rows

1. `python -m black_bloc` boots; **read `commands synced` and record BOTH numbers** (before,
   after) — the drop must be exactly one for this feature (requests deviation 7; checklist 10 — a
   check that could not run is not a check that passed). With no token, measure it the way events
   and applications did: `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits`
   counts the real tree, and say plainly that a boot was not run.
2. The parametrised panel test: every state renders its row and no other control.
3. `python -c "import black_bloc.golive, black_bloc.cogs.content.golive,
   black_bloc.api.tools.golive, black_bloc.personas, black_bloc.chat, black_bloc.pings,
   black_bloc.raidtrain"` — the substitute for a boot (wave-0 deviation 5), and it covers every
   module whose strings §E rewrites.
4. `ruff`; full `pytest`; `node site/mock/check.mjs` (**expect the same page/route counts as
   `main`** — this design adds no route); `node --input-type=module --check <
   site/public/assets/labels.js` (⚠️ that file failed to parse once — `code-notes.md:5008`).
5. Checklist sweep before reporting — **1** and **2** (nothing in this build touches the announce
   path; prove it by the untouched tests), **8** (`AnswersErrors` on the modal and every
   component), **9** (the status lines keep last-good-poll and last-error, not `is_running`),
   **10** (the unverified link still says so), **11** (`allowed_mentions` on every send and edit),
   **13** (the preview stays ephemeral and never pings), **15** and **17** (one `answer`, one
   `MoveButton` — §F), **16** (the `link_owner` clash refusal survives the extraction),
   **30** (`on_error` on the modal and the view), **33** (§D), **34** (the log-row count).

⚠️ `tests/api/test_settings_api.py::test_writes_are_rate_limited_per_session` is a known
load-sensitive flake under `pytest -n auto` (events deviations, "One flaky test"). Measure the base
commit before calling anything a regression.

**Sweep rows — BUILT as 109–117** (`docs/access/sweeps.md`; 103 is the operator-token row and
104–108 are claimed by a sibling wave-2 build, so this one took 109 onward — **the conductor
renumbers at landing** if the siblings land first). The table below is the DESIGN's numbering;
what shipped is rows 109–117, one per row here, plus a tenth for the panel going quiet. Rows 12,
19, 31, 49 and the Phase 2 appendix were rewritten in place, not added.

| # | Do this | Expect |
|---|---|---|
| 104 | `/golive` as a plain member with no Twitch linked | one ephemeral panel: the intro, "no Twitch channel linked", **Link my Twitch channel**, **Stop announcing my streams**, Refresh, Open on the site — and NO status lines, NO Logs, NO preview, NO mode select |
| 105 | **Link my Twitch channel** → type your channel name; then **Change my channel** → type nonsense | the first links and the panel says `twitch.tv/<you>` (verified, or "not verified" if Twitch could not be reached); the second refuses in words and changes nothing. Try a name another member already holds: refused, and the sentence never names who holds it |
| 106 | **Stop announcing my streams**, then **Announce my streams again** | one button at a time, never both; the panel line flips each way; `/golive` Logs shows one `golive.optout` and one `golive.optin` |
| 107 | **Unlink**, then go live on Twitch with Discord showing Streaming | the link is gone (and the fan role does whatever `pings_fan_role_on_unlink` says); presence still announces, because unlinking is not opting out |
| 108 | `/golive` as staff | adds the eleven status lines (mode, stream end, channel, cooldown, twitch polling, last good poll, last poll error, counts, who is live), **Logs**, **Preview an announcement…** and the **off/shadow/on** select — Logs answers a NEW message and the panel stays |
| 109 | **Preview an announcement…** → *Twitch*, then *YouTube*, then *As you are now* | three ephemeral previews with the card and box art, **no ping**, nothing posted in any channel, one `golive.test` log row each — and with `golive_channel_id` pointing outside the test channel the panel's channel line SAYS test mode is why nothing real would post |
| 110 | The mode select → **on**, then **shadow** | the panel re-renders with the new mode, one `golive.mode` row each, and the next go-live behaves accordingly (`would_announce` in shadow) |
| 111 | Leave the panel alone for `golive_panel_minutes` minutes | every control disables itself and the footer reads "This panel has gone quiet — run /golive again" |
| 112 | **fork I2 only** — **Streamers…** → pick somebody → **Unlink them** / **Opt them out** | the same result as the website's Go-live page does it, one log row each, and the select says "25 of N" past 25 |

## I. The genuine forks — the owner decides, one at a time

Settled first, by the standing rules, so they are NOT put to him:

- ✅ **The preview stays ephemeral and keeps no ping prefix** — `code-notes.md:593` records that as
  a review fix; changing it would re-create the defect.
- ✅ **No Settings sub-panel** — the site's Go-live page already owns the twelve keys
  (one-fact-one-home). Only `golive_mode` gets a Discord control, because its subcommand is being
  retired.
- ✅ **Every member control renders in every mode** — the applications I-A2 answer ("Visible") plus
  P9: the panel says the feature is off in words rather than vanishing, and `HIDDEN_WHEN_OFF` gains
  nothing.

Two were genuinely his, and he answered both on 2026-09-03 at 16:10 — ✅ **I1 = `/golive`**
(described *"Your Twitch channel, and whether your streams get announced"*, member-visible, the
`twitch` group retired) and ✅ **I2 = build the `Streamers…` sub-panel**. Both are built as
decided; the arguments are kept below because they are why:

- **I1 — what is the ONE command called, `/golive` or `/twitch`?** Two groups become one command
  and one word has to carry both halves. `/golive` is what the feature, the log kinds
  (`logkinds.py:25`), the twelve settings keys, the site page and the Logs section are all called —
  and it is honest about scope, because the feature announces **YouTube and Discord-presence
  streams too** (`TEST_STREAMS` `:99`, `phase2-design.md`), so a member who never touches Twitch
  still opts out here. `/twitch` is the word a member reaching for it would type, and linking is
  the half that gets used a hundred times to the staff half's one — the same argument that made the
  owner pick `/apply` over `/applications` on 2026-09-03 ("it's gamer lingo"). ⚠️ **Discord's
  command picker matches on the NAME**, so whichever loses, the people typing the other word find
  nothing. **Recommended: `/golive`**, with the description reading *"Your Twitch channel, and
  whether your streams get announced"* so the word "Twitch" is at least on the card. Whichever he
  picks it stays member-visible, and the feature, the log kinds, the keys and the site keep the word
  "golive" either way.

- **I2 — do STAFF get a `Streamers…` sub-panel in Discord, or does that stay on the website?**
  Today staff have **no** Discord way to unlink or opt out another member — only the website does
  (`api/tools/golive.py:94` `:135` `:149`), and that is a real gap in the standing *staff always get
  the final say* rule, softened only by the site being a second door they already have. Building it
  is §C's sub-panel: one select capped at 25 over `all_links`, a small card, and three buttons —
  **no new query, no new route, no new key**, because the five functions §F extracts are the ones
  the site routes already call. **Recommended: build it.** A Lead with a phone should be able to
  clear a wrong link, and the marginal cost is one select and one card on a panel that has two empty
  rows. The alternative is to leave rows 2 and 4 as they are and let the **Open on the site** link
  be the answer, which is smaller, keeps one editor for the links table, and is defensible because
  the site's Go-live page shows the whole table where a 25-cap select cannot.

## J. What NOT to build

- **No second announcer, and no new session writer.** The listener, the poller, `_go_live_once`,
  `_end_live`, `_close_session`, the reconciler and the age-out are untouched. If a diff touches
  `_post` `:558` or `_go_live_once` `:398`, it is out of scope.
- **No settings editor** — see §I's settled list. No template preview, no end-wording editor, no
  role-filter pickers in Discord.
- **No `Status` button** (the embed is the status) and **no `Test` button** (the select is).
- **No persistent post.** This panel is ephemeral and dies on a restart (P14, KI-19). The feature's
  posted things — the announcement itself — belong to the room and are not a `DynamicItem` anybody
  clicks.
- **No `option_label` / `MoveButton` promotion into `panels.py`** during wave 2 (§F).
- **No change to `guard.py`, to test mode, or to the announce channel.**
- **No `docs/TODO.md` / `docs/DONE.md` / `deploys.log` edit** — the conductor lands those.
- **No renaming of `self.helix`** (`code-notes.md:571` explains why it is not `self.twitch`; the
  reason survives the group's deletion as a note, not as a rename).

**Cost estimate for the Opus build: ~200–280k tokens**, below the 376k–458k wave-1 range and stated
as an estimate, not a measurement. The reasons it is smaller: eight subcommands rather than
seventeen; **no state machine** (four independent booleans, so the parametrised test is eight rows,
not a `TRANSITIONS` proof); **no CRUD sub-panels** (no forms, no questions, no rosters); **one** new
settings key rather than two or three; **no site change** and no new route; and the DB layer stays
where it is instead of moving. The two things that could push it past 280k are fork I2 (one extra
sub-panel) and the cross-feature string sweep in §E, which touches seven modules and five test
files — brief the builder to do the string sweep as its own commit at a clean boundary.

## Deviations

Written by the build agent, 2026-09-03. Everything not listed here was built as this document says,
including both decided forks (I1 `/golive`, I2 the `Streamers…` sub-panel) and every item in §J's
"what NOT to build".

1. ⚠️ **`checked` is `twitch_user_id is not None`, not `helix is None` — and the old expression
   would have made the website LIE in its own log.** §F says `link_channel` takes `helix` as a
   parameter and the route passes `helix=None` so its `"checked": false` stays true. It does; but
   the body absorbed from `/twitch link` opened with `checked = self.helix is None`, which meant
   "Twitch enrichment is off, so do not blame Twitch for being unreachable". Read with
   `helix=None` coming from a ROUTE that simply never asked, that expression evaluates **true**,
   so `POST /api/golive/links` would have written `checked: true` into `action_log` beside a
   response body saying `"checked": false`. That is checklist 10's exact defect, moved from a
   sentence into a log line. `checked` now means *a Twitch lookup confirmed this channel exists*
   and nothing else. The **outcome** is a separate question, so the Discord wording is unchanged:
   with no Twitch client at all the sentence is still the plain "Linked **x** to you", because
   nothing was unreachable — nobody asked. ⚠️ **Found by `tests/api/tools/test_golive.py`, not by
   reading**, which is why that file now asserts the row's `checked` value and not only its kind.
2. **The four move functions return `(outcome, extra)`, not §F's `(outcome, row)`.** `extra` is the
   fan-role sentence `pings.maybe_auto_create` / `pings.on_streamer_left` produce, and the caller
   cannot recover it any other way; `row` would only have saved the link route one `get_link` it
   already makes. All four return the same shape, so the two doors read alike.
3. ⚠️ **This is a real behaviour change for the WEBSITE, and it is the point of §F.** The fan-role
   step used to belong to the Discord door alone: `POST /api/golive/links` never ran
   `pings.maybe_auto_create` and `DELETE /api/golive/links/{id}` never ran `pings.on_streamer_left`.
   Now they do, because one function serves both doors. So with `pings_fan_role_creation` on `auto`,
   linking somebody from `golive.html` makes their fan role; with `pings_fan_role_on_unlink` on
   `delete`, unlinking from the site drops it. Both were already the configured behaviour — the
   site was quietly not honouring it. The same shape as events deviation 2. `pings` logs those rows
   itself, so the one-write-one-row count is unaffected and the route tests prove it.
4. **`preview()` returns `(text, embed, details)` and the SELECT writes the `golive.test` row.**
   §F asks for exactly this ("WITHOUT the reply and WITHOUT the log call"), but it is worth naming
   because it is the one place in this build where a panel control logs rather than a shared
   function (P4). The reason is that the log line is about a reply that may not have happened, and
   a function with no interaction cannot know. The count is what the test asserts.
5. **`panels.option_label` was not used for the `Streamers…` select.** §C names it. Its shape is
   `#<id> · <status> · <text>`, and `#900000000000000002` is not what a staffer picking a streamer
   reads — the label is the display name and the channel. The 100-character clamp still has one
   home: `panels.SELECT_OPTION_LIMIT`. This is the same call wave 0 deviation 2 left open ("for the
   first feature wave that actually needs a second copy of it"); this feature needs a different
   shape, not a second copy, so nothing was promoted into `panels.py`.
6. **`NOT_LINKED` and `NOT_OPTED_OUT` were deleted, and NOTHING replaced them.** §E says they are
   unreachable under P9 and go. The races are still real (two clicks a millisecond apart), so the
   question was what to say. Inventing "you were already unlinked" would have re-created the
   sentences the panel exists to remove, so instead **`unlink_channel` and `opt_in` log only when
   they actually changed a row** and the caller says the same thing either way — which is true
   either way ("Black Bloc has forgotten your Twitch channel" is a statement about the end state).
   The routes keep their own 404s off the returned boolean, so the website is unchanged.
7. ⚠️ **The Logs button loses `/golive logs`'s two options, `count` and `important_only`.** It calls
   `send_logs(interaction, FEATURE)` at its defaults, exactly as the applications and events panels'
   Logs buttons do. Reported rather than fixed: matching wave 1 is worth more than a bespoke control
   here, the site's Logs page has both filters, and adding two selects would cost the row **Streamers…**
   sits in. If the owner wants them back it is a modal, not a subcommand.
8. **`polling_summary` moved out of the cog to module level and takes the cog.** §F only lists
   `status_lines`, which "includes `_polling_summary`". Making it a module function is what lets
   `status_lines(bot, None, guild)` say *the go-live cog is not loaded* rather than raising — the
   same health-not-liveness rule (checklist 9) read one level up. `code-notes.md:531` carries the
   note that used to sit on `_polling_summary`.

### What §H could and could not prove

| # | §H item | Proven? |
|---|---|---|
| 1 | boot reports `commands synced` **41** | **Measured, not booted** — `tests/test_bot.py` builds the real tree by loading every cog and counts `bot.tree.get_commands()`: **42 at `8cbe453`, 41 on this branch**, and the drop is exactly the one slot §B predicts. ⚠️ **No boot was run**: there is no bot token in this environment, the same gap wave 0 deviation 5 and events deviation 13 recorded |
| 2 | the parametrised panel test | **Proven** — `test_the_panel_renders_exactly_the_row_the_table_says` over linked × opted-out × staff asserts the rendered labels ARE `panel_buttons(...)` and that Logs / Streamers… / the two selects / the status lines appear only for staff; `tests/test_golive.py` proves the table itself over the same eight states |
| 3 | the seven-module import check | **Proven** — `python -c "import black_bloc.golive, black_bloc.cogs.content.golive, black_bloc.api.tools.golive, black_bloc.personas, black_bloc.chat, black_bloc.pings, black_bloc.raidtrain"` passes. It matters here because this build creates a real new import edge, `black_bloc/golive.py` → `black_bloc/panels.py` → `settings_store` |
| 4 | ruff, full pytest, `check.mjs`, `labels.js` | **Proven** — ruff clean; **3756 passed** (3710 at `8cbe453`); `node site/mock/check.mjs` says **17 pages, 142 routes, all keys present**, the same as the base; `node --input-type=module --check < site/public/assets/labels.js` parses |
| 5 | the checklist sweep | **Proven by test** for 1/2 (the detection tests are green **unchanged in assertion**, which is the proof the announce path did not move), 9 (last-good-poll and last-error, never `is_running` alone), 10 (deviation 1), 11 (`AllowedMentions.none()` on every send and edit, asserted), 13 (the preview is ephemeral, unpinged, and `_post` is asserted never called), 15/17 (one `answer`, one move table), 16 (the `link_owner` clash survives, and still never names the holder), 33 (§D), 34 (row COUNTs on both doors). **8 and 30** are structural: `LinkModal` is `AnswersErrors + discord.ui.Modal` and every view is a `Panel`, which is `AnswersErrors` too |
| — | anything a person SEES | **NOT proven** — no panel has been opened in Discord, no button pressed, no modal submitted, no Helix call made. Sweep rows 109–117 are what would prove it |
| — | the `default=` on a re-rendered select | **NOT proven and cannot be here** — that the mode select and the streamer select show the current value as chosen is asserted on the option objects, not seen in a client |

### One flaky test, not seen on this branch

`tests/api/test_settings_api.py::test_writes_are_rate_limited_per_session` is the known
load-sensitive flake (events deviations, "One flaky test"). It did **not** fire in any run on this
branch, including the base measurement — `8cbe453` gave **3710 passed, 0 failed** under
`pytest -q -n auto` and this branch gives **3756 passed, 0 failed** the same way. Recorded so the
next reader knows the counts are clean ones, not ones with a flake subtracted.

### Findings in existing code, reported and NOT fixed

The design already lists five. These are the ones this build met:

1. ⚠️ **Four wave-1 settings keys have no label anywhere on the site.** `event_panel_minutes`,
   `poll_panel_minutes`, `birthday_panel_minutes` and `request_panel_minutes` are in the registry
   but appear in neither `site/public/assets/labels.js` nor `site/mock/server.mjs`, so the Settings
   page falls through to a tidied-up key name for all four. Measured today by grep while adding
   `golive_panel_minutes`, which HAS both. Four one-line rows in somebody else's feature; not
   touched. ✅ **Closed** — measured 2026-09-11, `site/public/assets/labels.js` carries all four
   (`event_panel_minutes` `:102`, `poll_panel_minutes` `:117`, `birthday_panel_minutes` `:129`,
   `request_panel_minutes` `:193`) plus every later panel's; the sweep landed with v93's
   *"13 labels.js sentences"* pass.
2. **`api/tools/golive.py` still imports `clean_login` from the cog, for wording only.** The 400 and
   409 name the cleaned channel, and the shared function has no reason to hand it back. Harmless,
   but it means the route cleans a login it does not store — if `clean_login` ever became two
   functions, this is a place that would need looking at.
3. **The `# Applications, no-role pass` and `# Events panel (wave 1)` sections of `code-notes.md`
   are keyed against UNMERGED branches**, as their own banners say. This build re-keyed only the
   golive keys; the conductor's merge-order re-key still owes the rest.

## Follow-up 2026-09-21: a member's opt-out ends the announcement that is already out

> ✅ **FOLLOW-UP LIVE v153 (2026-09-21 12:13)** — release commit `3d75254`; `release.json` says `v153` at
> `0b3653d`. Merge `1deb296` of branch `member-optout`, **3 commits**, eight deviations, **15 new tests**;
> the gate shipped on its THIRD run (**7237 passed, 3 skipped** — run 1 was refused on KI-32's guides test,
> run 2 was killed by the OS for memory, KI-37; neither reached Fly). Sweeps are numbered **732–733** (were
> `MO-a` / `MO-b`) and **neither has been walked**. Was 🔨 BUILT 2026-09-21 on branch `member-optout`, off
> `main` `20b615d` (v152 live + one TODO commit). ⚠️ **NOTHING IN IT HAS MET DISCORD** — no opt-out has
> ended a real announcement, nothing has been deleted and no pin has come off; only the boot was verified at
> the deploy. Review link:
> <https://blackbloc.heygabi.ai/golive.html> ▸ a live member's row ▸ **Opt out**.

**The ask, owner verbatim (2026-09-21 10:4x):** *"opt out should end their annoucement"* — said of a
MEMBER's opt-out, the morning after v152 made a *channel's* opt-out end the announcement already
out. The channel half is
[`channel-streamers-design.md`](channel-streamers-design.md) ▸ **Follow-up 2026-09-21**, and its
Deviation **5** is exactly this asymmetry, recorded there as "worth the owner's word if he wants
both". He did.

**What was wrong.** `opt_out` wrote the `golive_optout` row and dropped the fan role, and nothing
else. An open `golive_sessions` row and its posted announcement ran on until presence went quiet,
the Twitch poller read offline, or the boot sweep aged the row out — so a member who pressed **Stop
announcing my streams** mid-stream was still announced, still wearing the live role, with the post
still reading in the present tense. Three doors reach `opt_out` and all three behaved this way:
`/golive` ▸ **Stop announcing my streams**, the site's member drawer ▸ **Opt them out**, and staff's
`POST /api/golive/optouts`.

**The rule after.** `opt_out` returns `(the fan-role sentence, what an OPEN announcement had done to
it)` and funnels through `settle_open_session`, which hands the work to the cog's `end_for_optout`.
That takes the member's own `asyncio.Lock` — the same one `_go_live` holds while it announces — and
**re-reads the open row inside it** (checklist 6), so a second press of Opt out ends nothing twice.

The end itself is the usual member end path, with two things added:

- the `golive.end` row carries **`reason: "opted_out"`** and a **`post`** detail naming which of the
  three treatments ran;
- the live role comes off (`_remove_live_role`, which already records `role_stuck` when it cannot),
  the session is closed, and any scheduled grace-period end is cancelled.

**The key — `golive_member_optout_post`** (enum, group `golive`, default **`end`**): registry
(`KEY_TYPES` / `KEY_CHOICES` / `KEY_HELP` / the default chain) + the mock's `SETTING_SPECS` row +
`labels.js` + `golive-join.js:placeSettings` (the *How streams are spotted* drawer, beside
`golive_channel_optout_post`) + the join fixture (**52 → 53** keys in the three namespaces).
⚠️ **Registry keys measured 2026-09-21 on this branch: 298** (`297` before this key).

| Value | What happens to the post that is out |
|---|---|
| **`end`** (default) | Unpinned and edited to the ONE end wording, exactly as any stream end does |
| `delete` | Deleted outright (`golive.post_deleted`); a refusal logs and falls back to the words |
| `leave` | Left exactly as posted — only the pin comes off |

The session is closed and the live role comes off in all three, so nothing waits on Twitch or on the
member's presence.

**The sentence.** `golive.optout_said(said, settled)` is the ONE sentence function all three doors
use: each door passes its own base sentence and the clause lands only when a session was actually
open, naming `golive_member_optout_post` so a reader knows what to change. The API answer's
`message` carries it, and the site drawer prints what the route answers. Opting back **in** says in
the same breath that a stream already running is not announced after the fact — the member's own
`OPTED_IN`, staff's `THEY_OPTED_IN` and the route's `OPTED_IN` all say it.

### Follow-up deviations

1. ⚠️ **`optout_said` takes the base SENTENCE, not a row — it is not `announce_said`'s exact
   shape.** The brief said to mirror `spotlight.announce_said(row, settled)`, which picks its own
   base because a channel row keys one sentence. A member's three doors address three different
   people — *your* streams, *their* streams, **{name}**'s streams — so a row-keyed function would
   have to carry the door as an argument anyway. One function, three bases, one clause table:
   `optout_said(said, settled)`. It is still the single place the clause is decided, which is what
   "one sentence function" was for.
2. **`MEMBER_OPTOUT_END` / `_DELETE` / `_LEAVE` / `_POSTS` are ASSIGNED FROM the channel
   constants**, not re-spelled. The three value words are one fact (checklist 15) and the member
   names point at it, so they cannot drift; only the KEY is new.
   `tests/test_settings_store.py::test_the_member_and_channel_optout_posts_are_two_keys_over_one_set_of_words`
   guards the identity. The alternative — renaming `CHANNEL_OPTOUT_*` to a neutral `OPTOUT_POST_*` —
   would have churned `spotlight.py`, the spotlight cog and their tests a day after v152 shipped,
   for no behaviour.
3. **A failure kind was invented rather than reused: `golive.post_delete_failed` /
   `golive.post_deleted`, and `golive.unpin_failed` / `golive.unpinned`.** The spotlight family
   folds its delete failure into `golive.spotlight_post_failed` with `what: "delete"`, because that
   kind already existed there for the bump path. The member family has no such kind, so inventing
   one is cheaper than inventing a `what` field with one value. Checklist 2: an `on`-mode failure
   never shares a kind with a success.
4. **`_mark_ended` gained a keyword-only `message`**, so the opt-out path fetches the announcement
   ONCE and hands the same object to the unpin and to the edit. Every other caller passes nothing
   and fetches as before.
5. ⚠️ **The unpin is defensive, not a mirror.** This feature never pins a member's announcement —
   only the spotlight half pins — so the only pin `_unpin_announcement` can find is one a human put
   on by hand. It comes off because the MESSAGE carries one (checklist 3), never because a key says
   so. A reader comparing this to the channel path should not conclude that members get pinned.
6. **`_end_live` was NOT changed.** The ordinary end (presence quiet, poller offline, grace expired)
   still does not unpin and still writes `golive.end` with no `reason` and no `post`. Only the
   opt-out path is new, which keeps the diff to the case the owner asked about; the cost is that a
   hand-pinned announcement ended the ordinary way still strands its pin.
7. **This section lives in `golive-panel-design.md`, not the `docs/info/golive-design.md` the brief
   named** — there is no such file, and the go-live feature already has five design docs
   (`golive-panel`, `golive-page`, `golive-end`, `golive-boot-sweep`, `channel-streamers`). This
   doc owns the member opt-out move across all three doors, so a sixth would have split the fact.
8. **No warning before the press.** The sentence is the *result* sentence, exactly as the channel
   follow-up's Deviation 6 decided; the drawer and the panel still say nothing in advance about
   what will happen to a post that is out.

### Follow-up — what was NOT verified

- ⚠️ **NOTHING HERE HAS MET DISCORD.** No member was opted out in a real server, no pin came off a
  real message, nothing was deleted, no announcement was edited and no live role was removed. Every
  claim about what a post reads is the suite's, against fakes. **A Discord run is impossible from a
  build worktree** — it needs the token and a live gateway.
- ⚠️ **The live role removal is proved only against `FakeMember.remove_roles`.** The `role_stuck`
  branch (role gone, member not visible, HTTP refusal) was not exercised by this build at all; it is
  the pre-existing code reached unchanged.
- **No browser check was made.** The site half is the route's sentence and the mock's mirror of it,
  proved by `check.mjs`, the node tests and the suite — not by a page anybody looked at.
- **The mock's settle is a hand-written mirror**, not shared code: `site/mock/server.mjs`
  (`settleOpenMemberSession`, `MEMBER_OPTED_OUT_POST_SAID`, `memberOptedOutSaid`) restates the three
  sentences and the session close, and the mock has no live role and no pin to move. If the Python
  wording changes and the mock's does not, nothing fails — the two copies are only checked by eye.
  It WAS exercised by hand on `MOCK_PORT=8780`: the first opt-out of the seeded live member
  (`Casey`, session 12) answered with the `end` clause, a second answered with the plain sentence.
- **`delete` and `leave` were never exercised against the mock** — only against the Python suite;
  the mock's `leave` branch does nothing but close the session, which is all it can do.
- **No migration was written and none is needed** — the key is a settings row with a default, so an
  unset guild reads `end` from the default chain.
