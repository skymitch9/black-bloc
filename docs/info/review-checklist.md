# Review checklist — traced to real findings in this repo

> **Audience:** every build agent (read BEFORE building) and every review
> agent (score against it). **Status:** TRACKED (owner, 2026-08-31 — was
> local-only until then). **Last verified: 2026-09-11 08:50** — docs-wide staleness pass.
> **Counted:** the file holds **34** numbered items, 1–34 with none missing (items are NOT
> in numeric order on the page — they are grouped by subject, and that is deliberate; do not
> renumber). **Every item's named trace was checked to still exist on `main` at `1d090e5`:**
> `command_errors.py` (items 8, 29), `settings_store.KEY_TYPES`/`KEY_HELP`/`KEY_CHOICES`
> (33), `logkinds.kind_via` / `bare` / `VIA_WEBSITE` and all three guarding tests in
> `tests/test_logkinds.py` — `test_a_route_never_notes_an_event_its_shared_path_already_logged:439`,
> `test_a_shared_logger_stays_discord_unless_a_route_says_otherwise:549`,
> `test_no_module_builds_the_web_head_for_itself:585` (34), `settings_store.GOLIVE_MODES` and
> `cogs/community/role_menus.py:36 MODES` (15). **Two FIXED:** item 33 told a person to run
> `/settings set-value`, a subcommand retired at the v84 landing (**zero hits in
> `black_bloc/`** today) — it now names the panel; item 20's cost band was the 2026-08 figure
> and is replaced with what builds in this repo actually measured. ⚠️ **NOT re-checked:** the
> *wording* of items 1–32 was not re-traced to the incident that produced it, and no item was
> exercised against Discord or a browser.
> ⚠️ **`CLAUDE.md` says "33 items" — it is one behind; this file owns the count.**
> Before that, **2026-09-03** — items 1–20 are CONFIRMED findings from the Phase 2
> adversarial review (`phase2-design.md` build, commit `ece5e3b`) or an
> incident earlier the same day; 21–33 were added by later phases, and **34**
> (one web write leaves one log row) was added that day from the owner's
> 2026-09-03 double-post report. Generic advice is deliberately absent.

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
    and after landing. ⚠️ **Measured in THIS repo, not estimated:** a
    one-subsystem build 279k; the panel builds 370k (`automod`), 441k
    (`chat`), 473k (`raidtrain`), 529k (`role-menus`) — several of them
    **over their own 300–500k estimates**. A multi-layer build is the
    expensive shape; a research or lookup agent is not.

33. **Is every decision this change introduces configurable from BOTH the dashboard and the bot?** (owner rule 2026-08-27: "all decisions we make here can be configured in dashboard and with bot"). A decided default is a registry key (`KEY_TYPES`/`KEY_HELP`/`KEY_CHOICES`), which gives the dashboard's Settings page + the `/settings` panel's own key card for free (⚠️ `/settings set-value` was retired at the v84 landing — do not tell anyone to run it); a per-item choice (menu approval, poll anonymity, request status) needs a slash subcommand AND a dashboard control. Traced to: Phase 12 log levels, Phase 9 approval fields, Phase 10 per-poll flags — all built that way; the rule stops the next one from being a constant.

34. **A web route that calls a shared path which already logs passes `via=VIA_WEBSITE` and never `note()`s the same event again.** One write leaves ONE `action_log` row and ONE Discord embed. The shared function takes a keyword-only `via: str = VIA_DISCORD`, builds its kind with `logkinds.kind_via(kind, via)` — the single inverse of `bare()`, never a hand-rolled `f"{WEB}."` — and records `details["via"] = via`; the route passes `via=VIA_WEBSITE` and deletes its own `note()`. `note()` stays ONLY where the route is the sole logger (`web.request.filed`, `web.request.updated`, comments, withdraw, the raid-train and role-menu CRUD). Consequential rows the bot emits on its own (`request.dm_failed`, `request.notify_failed`, `modmail.place_kept`) keep their bare kind — only the actor's action row takes the head. Traced to: owner, 2026-09-03, "The app double posted all messages with a web.request and a request" — `apply_decision` logged `request.done` and the route noted `web.request.done` on top of it, in 8 route files. Guarded by `tests/test_logkinds.py::test_a_route_never_notes_an_event_its_shared_path_already_logged` (an AST walk of `api/tools/*.py`), `::test_no_module_builds_the_web_head_for_itself` and `::test_a_shared_logger_stays_discord_unless_a_route_says_otherwise`.
