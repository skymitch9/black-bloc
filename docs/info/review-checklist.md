# Review checklist — traced to real findings in this repo

> **Audience:** every build agent (read BEFORE building) and every review
> agent (score against it). **Status:** TRACKED (owner, 2026-08-31 — was
> local-only until then). **Last verified:
> 2026-08-31** — the file now holds **33 numbered items** (counted today), not
> the 20 it started with: items 1–20 are CONFIRMED findings from the Phase 2
> adversarial review (`phase2-design.md` build, commit `ece5e3b`) or an
> incident earlier the same day; 21–33 were added by later phases, the newest
> being **33** (every decision configurable from both the dashboard and the bot
> — owner, 2026-08-27, commit `ad1ab5a`). Generic advice is deliberately absent.
> ⚠️ Only the COUNT and item 33's provenance were re-verified today; the wording
> of items 1–32 was not re-traced to its incident.

## Test policy and rollout

1. **Every side effect the HTTP guard cannot see** (role add/remove, ban,
   kick, channel create/delete/rename, member move, scheduled event) checks
   `bot.guard` explicitly and, in `shadow`, is logged as `would_…` and NOT
   done. The guard patches `send_message` and `edit_message` only.
2. **A failed action must never share a log kind with a dry run.** `on`-mode
   failure → `<feature>.<action>_failed` with the reason; `shadow` →
   `<feature>.would_<action>`. The owner's verification method is "read the
   log", so these must be distinguishable at a glance.
3. **Reversal must not depend on the mode at reversal time.** If a role was
   added / a channel created / a member moved, record that fact on the row
   and undo it unconditionally later. (Finding: Live role stranded by a mode
   flip mid-stream.)

## State and restarts

4. **Reconcile on `cog_load`.** Any "open" row (session, ticket, temp
   channel, pending event) is re-checked against reality on startup and
   closed/aged out if stale. A deploy can land inside any grace window.
5. **No infinite blocking on a bad row.** Unparseable timestamps and open
   rows older than a sane maximum are treated as ended, never as "still
   open forever".
6. **Read-decide-write races between two triggers** (listener + poller,
   two clicks) get a per-key `asyncio.Lock` AND a DB uniqueness constraint
   (partial unique index on the open state).

## Failure visibility

7. **Wrap transport errors at the client boundary.** `aiohttp.ClientError`,
   `asyncio.TimeoutError`, `OSError` become the client's own error type;
   set an explicit `ClientTimeout`. Callers catch one type.
8. **A slash command must never end in "The application did not respond".**
   The tree error handler (`command_errors.py`) answers with a sentence and
   logs the traceback; commands that touch the DB check `is_connected`.
9. **Status commands show health, not liveness.** `is_running()` is not
   health; show last success time and last error.
10. **Claiming a check that was skipped is a lie.** If validation could not
    run (upstream down), say "could not be checked", not "linked".

## Discord specifics

11. **`allowed_mentions` on every send/edit of interpolated text.** Display
    names, stream titles, event titles, modal fields are attacker-controlled;
    `@everyone` in a nickname must not ping. Allow only the configured ping
    role.
12. **Do the irreversible/important thing first, cosmetics last.** Role
    change and action log before the message edit; a cosmetic failure must
    not abort the state change.
13. **Test/preview commands are ephemeral and never ping.**
14. **Custom emoji are stored as `<:name:id>` strings** and converted with
    `PartialEmoji.from_str` at render time.

## Permissions and Discord limits (Phase 3 review)

21. **"Who can see the staff channel" means COMPUTED permissions**
    (`channel.permissions_for(role).view_channel`), never explicit
    overwrites alone — category inheritance is how most roles see it. An
    empty resolved staff set must refuse to arm any punishing mode, and
    status commands print the resolved count, not "staff only".
22. **Clamp every value that Discord bounds** at the settings validator
    (ban purge 0–7 days, user limit 0–99, timeouts ≤28 d, name lengths) —
    and use the non-deprecated API parameter.
23. **Filter `message.type`** before treating a message as user content;
    system messages (thread created, pins) carry the member as author.
    Trap/gate channels deny thread creation in their overwrites.
24. **Defer before any Discord edit that can be rate-limited** (channel
    name/topic: 2 per 10 min) — discord.py sleeps through 429s and the
    3-second interaction window expires.
25. **Anything that only reconciles on startup also reconciles on a loop**
    (5 min) — a long-lived process never restarts on its own.
26. **Every list-typed setting has a way to remove an entry** (`forget`
    command + `on_guild_channel_delete` listener); setup refuses to append
    a duplicate and says how to forget the old one.
27. **Emptiness/occupancy from `channel.voice_states`, not
    `channel.members`** (the cache can be incomplete).

## Loops and library exceptions (Phase 4 review)

28. **Every `tasks.loop` has an `@loop.error` handler that logs and
    restarts it**, and records `last_ok_at` / `last_error` shown by the
    feature's status command. discord.py re-raises non-HTTP exceptions
    out of a loop and the loop stops for the life of the process.
29. **discord.py raises bare `ValueError`/`TypeError` for state and
    argument errors** (e.g. `ScheduledEvent.cancel()` on a live event) —
    catch the shared tuple in `command_errors.py`, not `HTTPException`
    alone. Check the installed library source, not memory.
30. **Components and modals do not use `tree.on_error`** — every
    `View`/`DynamicItem`/`Modal` that defers gets an `on_error` that
    answers with a sentence (the shared mixin), or the user sees a
    permanent spinner.
31. **Due-row sweeps age out** — a row whose window has fully passed is
    finished without acting; late actions have a maximum lateness.
32. **Reconcile skips `guild.unavailable`** and needs two consecutive
    misses before an irreversible cancel.

## Code shape

15. **One fact, one home** — a constant that exists in two modules is a bug
    (dead `MODES` vs `GOLIVE_MODES`).
16. **Two members must not be able to claim the same external identity**
    (Twitch login, etc.) silently; refuse with a sentence.
17. **Template rendering from staff-editable text** catches `Exception` and
    falls back to the default template with a log line.

## Process (from the day's incidents)

18. Bash tool commands that are long/heredoc-heavy trip Windows Defender's
    ClickFix signature — use script files + PowerShell.
19. A directory/Docker deploy ships the working tree: never deploy while a
    builder has uncommitted files; never run two builders in one tree.
20. Subagent cost is invisible until it lands — read usage before dispatch
    and after landing; builds run 150–260k Opus tokens here.

33. **Is every decision this change introduces configurable from BOTH the dashboard and the bot?** (owner rule 2026-08-27: "all decisions we make here can be configured in dashboard and with bot"). A decided default is a registry key (`KEY_TYPES`/`KEY_HELP`/`KEY_CHOICES`), which gives the Settings page + `/settings set-value` for free; a per-item choice (menu approval, poll anonymity, request status) needs a slash subcommand AND a dashboard control. Traced to: Phase 12 log levels, Phase 9 approval fields, Phase 10 per-poll flags — all built that way; the rule stops the next one from being a constant.
