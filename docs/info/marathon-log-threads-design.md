# Marathon log threads — a thread per tracked marathon under the log channel

> 🔨 **2026-10-10 — BUILT on branch `marathon-log-threads` (off `main` `b4d232a1`), NOT merged, NOT deployed.** Schema **93 → 94**, keys **1184 → 1187**, two new log kinds. Deviations and *What was NOT verified* at the foot.

> **Audience:** the conductor (merge + deploy) and reviewers. **Status:** TRACKED.
> **Last verified: 2026-10-10** — by the build's own gate on the branch (ruff, the hermetic suite, the mock check). ⚠️ Nothing met live Discord.

## The ask, verbatim (owner, Sat 2026-10-10 17:0x Phoenix)

*"we in the middle of an event and we're getting spammed with marathon run moved pings in the black bloc logs channel. lets from now on make a thread for each tracked event in the logs channel and move those marathon logs into that. I dont want to lose them but i dont want to flood the chat while we're working on other things too."*

Measured live by the conductor at 17:1x: `marathon_log_level` = important, `log_channel_id` = #blackbloc-logs. The flood is `marathon.member_run_moved` (IMPORTANT) plus the other marathon rows that pass the level, one embed each, all into the one channel. Every row is already in `action_log` and on the Logs page; only the Discord copy moves.

## The design

1. **One module, one call.** `black_bloc/log_threads.py`. `actionlog._post` now takes the row's `details` and calls `log_threads.deliver(bot, guild, kind, details, channel, embed)` where it used to call `channel.send(embed=embed)`. `build_embed` is unchanged; a thread gets the same embed.
2. **What is routed.** A row goes to a thread when ALL hold: `logkinds.feature_of(kind) == "marathon"` (so `web.marathon.*` too), `details["marathon_id"]` names a marathon whose row `marathon_inbox.is_tracked` says is tracked, and `marathon_log_threads` is on. Everything else posts to `log_channel_id` as before — rows with no `marathon_id`, untracked or ignored or archived marathons, every other feature (even with a `marathon_id` in its details, even `notify=True`). The log level still decides WHETHER a row posts; the thread only changes WHERE.
3. **The thread.** One public thread per marathon under `log_channel_id`, made on the first routed row, remembered on `marathons.log_thread_id` + `marathons.log_thread_channel_id` (schema 94, `ADDED_COLUMNS`; the archive twin mirrors them at boot). A stored channel that is no longer `log_channel_id` → a new thread in the new channel; the old one is left alone. An archived thread is reopened before the send (`cogs/content/marathon_inbox.reopened`). A thread that is gone (`find_channel` says NotFound) → `marathon.log_thread_lost` (IMPORTANT, to the channel) and a new one. `marathon.log_thread_made` (routine) when one is made, with `replaced` = the old id. Made with `cogs/content/marathon_inbox.make_thread`, so `auto_archive_duration` is the inbox's longest (`AUTO_ARCHIVE_MINUTES`, 10080) and the opening is sent with no mentions.
4. **Words are keys** (checklist 33, every-word rule): `marathon_log_threads` (bool, **on**), `marathon_log_thread_name_template` (default `{marathon}`; fields `{marathon} {when}`), `marathon_log_thread_opening_template` (default `{marathon} — Black Bloc's log for this marathon. Tracker: {url}`; fields `{marathon} {when} {url}`). `{url}` is `marathon_thread_controls.tracker_url(settings.origin, id)` — the same helper the thread controls use (`{origin}/schedule.html#marathon-{id}`), never a hard-coded host; blank while the site has no origin. Registered in `MARATHON_SETTINGS` / `MARATHON_WORDS` (registry + help + checks), the mock's settings rows and `labels.js`.
5. **Checklist 37.** Thread-making runs under a per-(guild, marathon) `asyncio.Lock` kept on the bot (the `brackets_moves.lock_for` shape) and re-reads the marathon row after taking it, so two rows at once make one thread (`tests/test_log_threads.py::test_two_rows_at_once_make_exactly_one_thread` makes four threads with the lock removed).
6. **Never raises into the writer.** Any failure finding, making or sending to the thread is a `log.warning` and the embed goes to the channel; the channel send itself stays inside `_post`'s existing try. Nothing is silently dropped.
7. **Modes.** Logs are not shadowed (`actionlog` ignores `marathon_mode`); the log thread always lives under `log_channel_id`.
8. **The site.** `tracking_of` (every marathon payload) gains `log_thread_id` and `log_thread_url` (`marathon_inbox.channel_url`); the Events page's marathon drawer header shows *log thread ↗* beside *thread ↗* when set. The mock carries both fields and seeds marathon 1 with a log thread.
9. **Existing rows are NOT moved.** Only rows written after the deploy go to a thread.

## Deviations

1. **`deliver` rather than a bare destination.** The brief had the module return a thread (or None) and `_post` send. The module does expose that (`thread_for`), but `_post` calls `deliver`, which also owns the fall-back when the THREAD refuses the send — keeping `actionlog.py` to one call, as the brief asked, instead of growing a second try/except there.
2. **The module's own two kinds are never routed.** `marathon.log_thread_made` / `log_thread_lost` carry a `marathon_id` and are logged while the marathon's lock is held; routing them would re-enter the lock. They go to the channel (the lost one is IMPORTANT, so staff see it there).
3. **A log channel that takes no threads** (no `create_thread`) is treated as a failure: a warning and the channel, every row. Real text channels and forums always have it; the hermetic fakes of many older tests do not, which is why those tests are unchanged.
4. **A thread that could not be READ (not NotFound — a network hiccup)** is not remade: the row goes to the channel with a warning, the stored id is kept and tried again on the next row. The `NOT_READ` rule of `ensure_thread`.
5. **Schema bumped 93 → 94** for the two columns, as every `ADDED_COLUMNS` step in this repo has done; six existing `== "93"` asserts in `tests/storage/test_db.py` follow it and a new `test_a_schema_93_file_gains_the_marathon_log_thread_columns` covers the step.
6. **No contract change.** `log_thread_url` is not added to `site/mock/contract.json`'s required keys — the mock and the API both carry it, and the page reads it as optional.
7. **The drawer link is *log thread ↗*,** a page constant beside `THREAD_LINK`, not *Open the log thread ↗* — the existing thread link in that header is the short `thread ↗`, and the brief asked for the same style. 4 lines of page, 2 of API, 3 of mock.

## What was NOT verified

- ⚠️ **Nothing met live Discord.** No thread was made in #blackbloc-logs; the thread, the reopen, the lost-and-remade path and the fall-backs are proven against the hermetic fakes only (`tests/test_log_threads.py`).
- Whether Discord rate-limits thread creation during a flood was not measured — a marathon makes ONE thread, so a flood costs one create and N sends, the same N sends the channel took before.
- The drawer link was not rendered in a browser; `node --check` on the page and `site/mock/check.mjs` passed.
- Not checked: how `marathon_log_level = all` plus a busy marathon reads inside a thread; the thread's own auto-archive (7 days) after the marathon ends — it is simply left to archive.
