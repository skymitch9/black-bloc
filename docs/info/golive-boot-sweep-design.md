# Go-live boot sweep — nobody is missed because the bot was restarting

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 🔨 **BUILT on branch `boot-sweep` 2026-09-20**, off
> `main` `f73e81c` (spotlight v148) — **nothing in it has met Discord**. Gate green both orders. The `## Deviations` foot
> is the truth where this body departs from what was built, `## What was NOT verified` is the honest half, and sweeps
> `BS-a` … `BS-d` in `../access/sweeps.md` are the proof that is missing. 🔴 **Read Deviation 0 first:** §A described the
> reconcile correctly and the boot never reached it — `cog_load` runs before the bot has any guilds, so the v141 boot
> reconcile has been a no-op on Fly. Was: 📐 **DESIGN (Fable, 2026-09-20 18:0x) — dispatches
> AFTER `spotlight` lands** (same cog, same boot path). **Last verified: 2026-09-20 18:0x** against `main` `45fd819`
> (v145 deploying): `cogs/content/golive.py` — `reconcile_open_sessions` `:669` / `_reconcile_one` `:675` (v141's boot
> reconcile, under `loops.Reconciler`), `_side_live` `:697`, `_close_session` `:737` (ends through `_mark_ended`, so the
> past-tense edit / delete of `golive_end_mode` happens), `poll_once` `:1418` (*"live logins with no open session go
> live, gone ones end"*), the `poller` loop `:1355` whose first tick runs as soon as the bot is ready; `cogs/content/
> youtube.py` — the `live_poller` loop `:434` (every minute, acting every `youtube_live_poll_minutes`) → `_live_now`
> `:524` (an open session joins, none opens one); `golive.py:extract_stream` `:126`, `should_announce` `:546`.

## The ask, verbatim (owner, 2026-09-20 17:5x)

*"also for go live detection, have the bot check all the channels with status and taht are linked on start up and make sure
the most recent post regarding them in the golive channel is accurate so we dont miss people during reboots"*

## A. What a reboot already gets right (measured in the code above — the build's first job is to PROVE each with a test)

| Case | Today |
|---|---|
| a linked Twitch login live at boot, no session | `poll_once`'s first tick (immediately after ready) announces it through `_go_live`; the cooldown against the LAST session's `ended_at` applies, so a bounce does not re-ping |
| a linked YouTube channel live at boot, no session | the `live_poller`'s first sweep probes it and `_live_now` opens the session and announces |
| an open session whose person is still live | `_reconcile_one` keeps it (each side re-checked on its platform) |
| an open session whose person went offline while the bot was down | `_reconcile_one` → `_close_session` → `_mark_ended` — the past-tense edit or delete per `golive_end_mode`, the live role removed, `golive.end` logged with `reason: reconciled_on_start` |
| a co-stream where one side ended during the downtime | `drop_platform`, the other side promoted |

## B. The gap — the owner's "channels with status"

**Presence-only streamers.** A member with no Twitch/YouTube link is detected ONLY by `on_presence_update` (`:762`). Discord
does not replay presences at boot: a member already streaming when the bot comes back raises no update, and nothing walks
`member.activities` for people with NO session (the reconcile reads activities only for sessions that exist). That person
is missed until their presence next changes — after a redeploy, every deploy. That is the miss.

**Second, smaller:** nothing records that the boot pass ran and what it found, so "did the reboot miss anyone?" cannot be
answered from the Logs page.

## C. The build

1. **`sweep_presences()`** in the go-live cog, called once per guild right after `reconcile_open_sessions()` and before
   `self.poller.start()`, under the same `loops.Reconciler` lock (checklist **37** — one pass per boot, the `on_ready`
   60-second skip applies). For each `guild.members` whose `extract_stream(member.activities)` is a stream and who has no
   open session (`open_session_for`), call `self._go_live(member, info, "presence")` — the SAME door presence updates use,
   so mode / opt-out / role filters / cooldown / shadow all apply unchanged. ⚠️ Needs the members and presences intents
   the bot already has (`build_intents`); a guild whose member cache is not chunked walks what it has and says so in the
   log row.
2. **One log row per boot per guild**, kind `golive.boot_swept` (routine; `logkinds.HEADS` under golive), details:
   `sessions_kept`, `sessions_closed`, `presence_found`, `presence_announced`, `presence_skipped` (with why: cooldown /
   opted out / role filter / mode off), `members_walked`. The Health page's go-live card reads the latest row's line.
3. **Key `golive_boot_sweep`** (bool, default **true**, group golive; help: *"true walks every member's Discord presence at
   boot and announces anyone already streaming with no session; false trusts presence updates alone, as before v146"*). Mock
   row + label. Configurable both ways; the Twitch/YouTube halves of the boot are their pollers' first ticks and need no key.
4. **Tests** — `tests/cogs/content/test_golive.py`: the five §A rows each get a test that boots a cog over a fake bot
   (they are the proof the design claims; if one fails, that row was wrong and the build fixes the code, not the test);
   the sweep announces a presence-only streamer with no session; skips one with an open session; honours the cooldown;
   does nothing when the key is off; writes one `boot_swept` row with the counts; runs once under the lock. Count guards
   (kinds, keys). `code-notes.md` rows. `golive-page-design.md` one dated line if the Health card changes.
   NOT `TODO.md` / `DONE.md` / `deploys.log` / `KNOWN_ISSUES.md`. Sweep rows `BS-a…` in `access/sweeps.md`
   (a: a member streaming through Discord presence with no link, bot redeployed → announced within a minute of boot;
   b: a linked Twitch streamer live across a redeploy → one announcement, not two; c: a streamer who ended during the
   redeploy → the post reads past tense after boot; d: the `golive.boot_swept` row on the Logs page).

## Deviations

*(written by the build agent, branch `boot-sweep`, **2026-09-20**, off `main` `f73e81c` — the commit
that carries spotlight v148. Every item is a departure from the body above; where the body is silent
and a choice had to be made, it says so.)*

0. 🔴 **§A IS TRUE ABOUT `reconcile_open_sessions`, AND WAS FALSE ABOUT A REBOOT — the code is
   fixed.** Every mechanism §A names does what it says when it is called. But the only thing that
   called it at boot was `cog_load`, and **`bot.py:setup_hook` loads the cogs before IDENTIFY**
   (`_load_cogs()` at `bot.py:83`, inside `setup_hook`), so `self.bot.guilds` is **empty** at
   `cog_load` and `for guild in self.bot.guilds` iterated nothing. On the real bot the v141 boot
   reconcile has been a **no-op**: an open session left by a restart was closed not by the
   reconcile but by `age_out_sessions` twelve hours later (`golive_max_session_hours`), or by the
   member's next presence change. This is measured from the source, not from Discord — the
   *"0 guild(s)"* half has never been read off a boot log, and `BS-b`/`BS-c` are the rows that
   confirm it end to end. The fix is the `on_ready` listener this build adds, plus
   `stamp=bool(self._guilds())` on the `cog_load` call: **a pass over no guilds must not close the
   60-second window**, or the one pass that HAS guilds is exactly the one `skip_if_recent` throws
   away. Guarded by `test_a_cog_load_with_no_guilds_yet_leaves_the_boot_to_on_ready`.
   ✅ **The same shape WAS in `cogs/content/spotlight.py`, and the conductor asked for it on this
   branch, so it is fixed too** (the third commit here): `stamp=bool(self._guilds())`, the same
   non-`unavailable` guild source, and the mirror guard `tests/cogs/content/test_spotlight.py::
   test_a_cog_load_with_no_guilds_yet_leaves_the_boot_to_on_ready`, **falsified against the
   un-fixed cog before it was kept**. Recorded at
   [`spotlight-design.md`](spotlight-design.md) ▸ Deviations ▸ **19**, sweep row `BS-e`.
   ⚠️ **NOT audited: `frontdoor.py`, `modmail.py` and `events.py`**, which each hold a
   `Reconciler` with a `cog_load` + `on_ready` pair. They POST rather than sweep, and their
   incident (2026-09-18) was a DOUBLE post — which means their `cog_load` pass did see guilds,
   so the same reasoning may not apply to them. Named, not guessed at, and not touched.

1. ⚠️ **Every one of §A's five rows was TRUE as a description of the code it names** — see 0 for
   the boot path that never reached them. All five now have a test
   that boots the cog rather than calling the reconcile by hand: `test_a_twitch_login_live_across_a_
   reboot_is_announced_by_the_first_poll` (row 1, including the bounce that the cooldown swallows),
   `tests/cogs/content/test_youtube.py::test_a_channel_live_across_a_reboot_is_announced_by_the_
   first_probe` (row 2), `test_a_boot_keeps_an_open_session_whose_streamer_is_still_live` (row 3),
   `test_a_boot_closes_a_session_whose_streamer_went_offline_and_marks_it_ended` (row 4) and
   `test_a_boot_drops_the_co_stream_side_that_ended_in_the_downtime` (row 5).

2. **Row 2's test lives in `tests/cogs/content/test_youtube.py`, not `test_golive.py`.** §C.4 puts
   all five in `test_golive.py`, but the behaviour it proves is `youtube.py`'s `probe_all` →
   `_live_now`, and the standing rule is that tests mirror the package. It boots the go-live cog
   (`cog_load`) first, so the frame is still a reboot: the presence sweep finds nothing, and the
   probe is what catches the stream.

3. **`reconcile_open_sessions()` was NOT already under `loops.Reconciler`** — the design's header
   says it was, and it was not (`cog_load` simply called it, and there was no `on_ready` path at
   all). So this build added the `Reconciler`, the `on_ready` listener with `skip_if_recent=True`
   and the single `boot_pass()` the lock wraps. That is checklist **37** arriving at this cog for
   the first time, not a change to an existing arrangement, and it is why
   `test_two_boots_at_once_sweep_once_and_write_one_row` is a genuinely new guard.
   `_guilds()` is the one home for *which guilds a boot pass covers* — non-`unavailable`, in cache
   order — and both the stamp decision and the pass itself read it.

4. **The pass is per GUILD, not "all reconciles, then all sweeps".** §C.1 says the sweep runs
   "right after `reconcile_open_sessions()`"; the counts in §C.2 are per guild, so `boot_pass()`
   reconciles one guild, sweeps that same guild, writes that guild's row, then moves on. With one
   guild — the only case that exists — the order is exactly what §C describes.

5. **`_reconcile_one` now RETURNS its outcome (`kept` / `closed` / `dropped`) and the row carries a
   third count, `sessions_dropped`.** §C.2 names only `sessions_kept` and `sessions_closed`, but
   §A's fifth row is a co-stream side being dropped, and folding that into either of the two would
   have made the row lie about a session that is still open. `reconcile_open_sessions()` keeps its
   old signature and is still what the older tests call.

6. **`_go_live_once` now returns a reason string, and that is where `presence_skipped` comes from.**
   The alternative was for `sweep_presences` to re-check the mode, the opt-out, the role filters and
   the cooldown itself before calling `_go_live` — four copies of decisions that have one home
   (checklist 15), and four chances to drift from the door presence updates actually use. The
   reasons are `mode_off` / `opted_out` / `role_filter` / `open_session` / `cooldown` /
   `no_session` / `post_failed`; `announced` is the one that is not a skip. ⚠️ A **shadow**
   announcement counts as `announced` — the row's own `mode` says which it was, and the question
   the count answers is *"did the sweep act on this person?"*.

7. **The row carries two counts §C.2 does not name: `swept` and `members_cached`.** `swept` is the
   key's value, so a row with nothing in it is distinguishable from a boot where the sweep was
   turned off — the difference the Logs page has to show. `members_cached` is `guild.chunked`, which
   is §C.1's *"a guild whose member cache is not chunked walks what it has and says so in the log
   row"* made into a field rather than a sentence.

8. **The row is written even when the key is off**, with `swept: false` and the reconcile's counts.
   §C.2 says one row per boot per guild with no exception, and the second gap §B names — *"nothing
   records that the boot pass ran"* — is not answered by a row that disappears.

9. **`boot_pass` skips `guild.unavailable`** (checklist 32). The body does not mention it; an
   outage-shaped guild has an empty member cache and would have written a row claiming it walked
   nobody.

10. **There is no go-live card on the Health page, so §C.2's last sentence could not be honoured as
    written.** `site/public/assets/page-health.js` contains no `golive` anything. Rather than invent
    a second surface for one line (one fact, one home), the row is read where go-live rows already
    are: the Logs page's **golive** chip, and the Logs section at the foot of the Go-live page
    itself. Naming it here rather than guessing at it.

11. **The key's help says "as before v149", not the body's "v146".** v148 is live; this build is the
    next one.

12. **`golive_boot_sweep` sits in the *How streams are spotted* drawer** (`golive-join.js:DRAWERS`),
    first in the list, beside the YouTube poll cadence and the spotlight poll — which is what that
    drawer is for. The every-key-lands-once fixture went **48 → 49**.

13. **Two test doubles changed shape: `FakeGuild.members` is now a property returning a LIST** in
    both `tests/cogs/content/test_golive.py` and `test_youtube.py` (the members live in `by_id`).
    They were dicts keyed by id, and `discord.Guild.members` is a list — the sweep would have walked
    integers and found nothing, which is the shape of a test that passes for the wrong reason.

14. **NOT done, deliberately:** nothing merged, deployed or pushed to `main`; `TODO.md`, `DONE.md`,
    `deploys.log` and `KNOWN_ISSUES.md` untouched; **`architecture.md` NOT edited** — its
    *Registry keys* line says **290 on `main` at v148** and is correct until this branch merges, at
    which point it becomes **291** (the conductor's docs ritual owns that number); no key flipped in
    any guild (`golive_boot_sweep` ships **true** as its registry DEFAULT, which is what §C.3 asks
    for — note that this is a build that CAN POST on boot, and the brake on it is
    `golive_mode`, which is per-guild and already set); no schema change, so no migration; no new
    loop, so `BEFORE_LOOPS` in `tests/test_loops.py` is unchanged at 20.

## What was NOT verified

⚠️ **Nothing in this build has met Discord.** No bot has been restarted, no presence has been walked,
no announcement has been posted from a boot. Every claim above is the suite's, against
`FakeGuild` / `FakeMember` / `FakeChannel` / `FakeHelix`. The sweep rows `BS-a` … `BS-d` in
`../access/sweeps.md` are the proof that does not exist yet.

Specifically NOT verified:

- ⚠️ **That `guild.members` is populated by the time `on_ready` fires.** This is the assumption the
  whole feature now rests on. The members intent is on (`intents.py`) and discord.py chunks guilds
  before dispatching `on_ready` when `chunk_guilds_at_startup` is left at its default — but that is
  library knowledge, not a measurement, and this bot has never been watched doing it. Deviation 0
  removed the failure that WAS measurable (a pass over zero guilds stamping the window); what is
  left is the cache's contents on a real boot. **`members_walked` and `members_cached` on the first
  real `golive.boot_swept` row are the numbers that settle it** — a walk of 0, or `members_cached:
  false`, means the pass ran too early. `BS-a` and `BS-d` are the rows that find out.
- **That a Discord presence at boot carries the streaming activity at all.** `extract_stream` reads
  `member.activities`, which the tests hand it directly. Whether a cached presence for a member the
  bot has never seen change carries a `Streaming` activity has never been observed.
- **`guild.chunked` against a real guild.** It is read, defaulted to `True` when absent, and printed
  on the row; no guild has ever answered `False` here.
- **That the v141 boot reconcile really has been a no-op on Fly** (Deviation 0). It is read off
  `bot.py:setup_hook` and discord.py's own ordering; no boot log has been checked for an open
  session surviving a restart, and no `golive.end` row with `reason: reconciled_on_start` has been
  looked for in production.
- **The two-boots race against real timing.** `test_two_boots_at_once_sweep_once_and_write_one_row`
  drives `cog_load` then `on_ready` in sequence, which is the incident's shape; nothing raced them
  concurrently, and `Reconciler`'s own tests are the floor under that.
- **Any browser.** The Go-live page was not opened. The new `golive_boot_sweep` control in the
  *How streams are spotted* drawer was checked through `check.mjs` and the join fixture, and
  **rendered nowhere**.
- **The Logs page showing a `golive.boot_swept` row.** The kind is classified routine and the row is
  written in the suite; no human has read one.
- **A guild with more than a handful of members.** `sweep_presences` walks the whole cache once and
  does one `open_session_for` query per streaming member — fine for this server, unmeasured for a
  large one.
