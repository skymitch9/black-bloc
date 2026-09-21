# Go-live boot sweep — nobody is missed because the bot was restarting

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **DESIGN (Fable, 2026-09-20 18:0x) — dispatches
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

*(the build agent writes here what it had to do differently, dated)*
