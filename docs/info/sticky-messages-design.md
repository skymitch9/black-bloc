# Sticky messages — one staff-set note per channel, kept at the bottom

> **Audience:** future Claude sessions, reviewers and the owner. **Status:** TRACKED · 🔨 **BUILT on branch
> `sticky-messages`** (off `main` `1cde5594`), **NOT merged, NOT deployed.** **Last verified: 2026-10-05** against
> that branch by the test suite, `ruff`, the node tests, `site/mock/check.mjs` and one look at the mock's Posts page
> in a browser. ⚠️ **NOT checked:** nothing here has met Discord — no copy was posted, deleted or silenced in a real
> channel, no real Forbidden was seen, the `/sticky` panel was never opened in Discord, and schema 88 has not run on
> the live database. See `## What was NOT verified` at the foot. Secret NAMES only.

## The ask

Owner, 2026-10-05, verbatim, picking from a list of popular bot features: *"Let's build 1, 8, 10"* / *"We'll leave
them in shadow for now"*. **8** = sticky messages: a staff-set note that stays at the bottom of a channel, e.g. *how
to submit a run*.

## As briefed (conductor) and as built

| Rule | How it is built |
|---|---|
| ONE sticky per channel: its words, on or off | Table `sticky_messages`, primary key `(guild_id, channel_id)`. `paused` is the off switch; the words are staff's own stored text and are the only thing posted |
| The bot deletes its previous copy and posts again at the bottom | `sticky_posts.Desk._place`: take the old copy down wherever `posted_channel_id` says it is, then send, then store the new id. Old copy that will not delete → **no** new one (never two copies) |
| Only after BOTH a number of messages AND a minimum gap | `sticky_after_messages` (5, 1–100) counted in memory per channel; `sticky_min_seconds` (30, 5–3600) measured from the stored `posted_at`. Count reached inside the gap → ONE timer per channel waits the remainder out, then posts once |
| Bots do not count | `sticky.counts`: `author.bot`, any webhook, and every system message type are ignored; only `default` and `reply` count (checklist 23) |
| Survives a restart, never two copies | `message_id` + `posted_channel_id` + `posted_at` are on the row. The count is in memory (see Decisions 3) |
| `sticky_mode` off / shadow / on, default **shadow** | Shadow posts nothing in the real channel: the copy goes to `shadow.channel_id(feature="sticky")` (`sticky_shadow_channel_id`, else `shadow_channel_id`, else the guard's channel, else the log channel) under the `rehearsal_note` line naming the real channel. Kinds: `sticky.would_post` |
| Both staff doors | `/sticky` (one command, an ephemeral panel) and a **Sticky messages** section on the Posts page. Both call the same `Desk` moves with `via` |
| Every default a settings key | Six keys, namespace **posts**: `sticky_mode`, `sticky_after_messages`, `sticky_min_seconds`, `sticky_silent`, `sticky_panel_minutes`, `sticky_shadow_channel_id` |
| A deleted channel / lost permission is logged once, in words, never retried forever, never raises | `on_guild_channel_delete` deletes the row and writes ONE `sticky.channel_gone`. Any other failure writes its reason to `trouble` on the row, drops the channel from the watch list and writes ONE `sticky.post_failed`; a row with `trouble` is not tried again until staff press **Try again** / edit it |
| Guard and permissions as other posting features | `guard.allows_channel(target)` before any send (refusal → `sticky.would_post` `reason: test_mode`, once per channel per boot); `permissions_for(guild.me)` for View Channel + Send Messages before deleting anything; `AllowedMentions.none()` on every copy |

## The pieces

| File | What it holds |
|---|---|
| `black_bloc/sticky.py` | The row reads/writes, the pure rules (`counts`, `seconds_left`, `state_of`, `card_buttons`) and every word the panel and the answers use |
| `black_bloc/sticky_posts.py` | `Desk` — one per bot (`desk_of(bot)`): the per-channel lock, the counts, the timers, `_place`, and the staff moves `save` / `pause` / `resume` / `remove` / `set_mode`, plus `settle` and `channel_deleted` |
| `black_bloc/sticky_panel.py` | The `/sticky` panel: list, a sticky's card, the words modal, the remove confirm |
| `black_bloc/cogs/moderation/sticky.py` | Thin: `on_message`, `on_guild_channel_delete`, `on_ready` reconcile, the settings hooks, the slash command |
| `black_bloc/api/tools/sticky.py` | `GET /api/sticky`, `PUT /api/sticky/{channel}`, `POST …/pause`, `POST …/resume`, `DELETE /api/sticky/{channel}` |
| `site/public/assets/sticky-section.js` | The Posts page section, mounted by `page-posts.js` |

### States (one word, read off the row and the mode — `sticky.state_of`)

`stopped` (has `trouble`) · `paused` · `off` (mode off) · `waiting` (running, no copy up) · `live` (copy in its own
channel) · `rehearsing` (copy somewhere else, i.e. the rehearsal home).

### Log kinds (head `sticky` files under **Posts**)

| Kind | Level | When |
|---|---|---|
| `sticky.set` / `sticky.edited` / `sticky.paused` / `sticky.resumed` / `sticky.removed` / `sticky.mode` (+ `web.` for the first five) | routine | The staff move, one row each (checklist 34: the route passes `via`, never notes a second row) |
| `sticky.posted` | routine | A copy placed by a staff move, a mode change or the boot reconcile — **not** by people talking (Decisions 4) |
| `sticky.would_post` | routine (shadow) | The same moment in shadow, with `rehearsed`, `shadow_home`, `message_id`; or `reason: test_mode` when the guard refused |
| `sticky.post_failed` | important | Once per stop, with the sentence that is also on the row |
| `sticky.channel_gone` | important | Once, when Discord deletes the channel |

## Decisions made beyond the brief

1. **A section of the Posts page, not a page of its own** (`posts.html#sect-sticky`). The `/settings` group select
   holds 25 groups and the registry already has 25, so a `sticky` namespace was not available; the keys are filed
   under **posts** through `NAMESPACE_OVERRIDE`, and the site's precedent for a small feature that shares a
   namespace is a section on that namespace's page (the front door on Modmail, spotlights on Go-live). Its log rows
   file under Posts for the same reason (`logkinds.HEADS["sticky"] = "posts"`), so the panel's **Logs** button and the
   Posts page's Logs fold show them; there is no `sticky_log_level` — `posts_log_level` governs.
2. **`sticky_silent`, default on.** A copy is sent with Discord's silent flag so moving it to the bottom does not
   light up notifications. A key, so staff can turn it off.
3. **The message count is in memory.** A restart resets it to zero, so the next move needs `sticky_after_messages`
   new messages after the boot. The alternative was a database write for every message in every sticky channel.
   What survives is what the brief named: the copy's id and where it is.
4. **A move caused by people talking writes no log row.** It bumps `reposts` on the row (shown as *moved N×* on the
   panel and the page) instead. A busy channel moves its sticky every 30 seconds; a row each time would be thousands
   a day and would bury the Posts log. Placements staff or the bot's own reconcile cause ARE logged
   (`sticky.posted` / `sticky.would_post`). ⚠️ If the owner wants every move in the log, it is one `log_action` in
   `Desk._place`.
5. **In shadow the rehearsal copy moves exactly as the real one would** — deleted and posted again in the rehearsal
   home on the same count and gap — so the cadence can be watched before the flip. One rehearsal copy per sticky.
6. **Pause takes the copy down** and keeps the words; **Resume** posts at once. **Mode off** takes every copy down
   and keeps every row. A mode change, or a change to `sticky_shadow_channel_id` / `shadow_channel_id`, moves the
   copies at once through a settings hook (`Desk.settle`) rather than waiting for the next message.
7. **A stopped sticky stays stopped.** `trouble` is cleared only by **Try again** (the resume move), an edit, or a
   pause. Nothing retries on a clock, which is what *not retried forever* was read to mean.
8. **Reversal does not depend on the mode** (checklist 3): take-down reads `posted_channel_id` off the row, so a
   copy posted under `on` is removed after a flip to `shadow` or `off`, and Remove works in every mode.
9. **No loop.** Checklist 25 asks for a loop beside any startup-only reconcile; nothing here ages on a clock — every
   transition has a trigger (a message, a staff move, a settings hook, `on_ready`, the channel-delete event). A copy
   a moderator deletes by hand is simply posted again at the next move. `on_ready` runs under `loops.Reconciler` and
   every placement re-reads the row inside the channel's lock (checklist 37).
10. **Text and announcement channels only**; 1800 characters, leaving room under Discord's 2000 for the rehearsal
    note. Threads and forum posts are not offered.
11. **The panel's own labels are constants in `black_bloc/sticky.py`**, as on `/honeypot`. Nothing the bot POSTS in
    a channel is a constant: a copy is staff's stored words, plus `rehearsal_note` in shadow. ⚠️ Candidate follow-up
    under the every-word-editable rule if the owner counts ephemeral panel labels.
12. **`/sticky` hides while the mode is off** (`HIDDEN_WHEN_OFF`), like every other feature; the ways back are
    `/settings` and the Settings / Posts pages. The mode is also a picker on the panel.
13. **`page-posts.js` no longer reads a `#sect-…` hash as a post slug**, so `posts.html#sect-sticky` opens the
    section instead of a *no post called sect-sticky* drawer. The bot's **Open on the site** button uses that link.
14. **The mock's `KIND_HEADS` gained `post` / `posts` / `sticky` → posts**, mirroring `logkinds.HEADS`; before this
    the mock filed post rows under Core.
15. **`tests/api/conftest.py`'s `WebChannel` gained `get_partial_message`** — the take-down uses the one-call
    partial delete, and the fake had only `fetch_message`.

## Merge notes for the conductor

- Schema **87 → 88** (new table only, `CREATE TABLE IF NOT EXISTS`, no backfill). Registry **779 → 785**. Two sibling
  builds were cut from the same `main`; each will also claim 88 and move the key count, so the version, the count
  assertion (`tests/test_settings_store.py`), `tests/storage/test_db.py` and `site/mock/contract.json`'s
  `settings.min` / `settings.max` blocks need re-measuring at merge.
- Cogs 26 → 27. Staff commands 17 → 18. `HIDDEN_WHEN_OFF` 17 → 18. `check.mjs`: 23 pages, **300** routes (was 295).
- `docs/info/code-notes.md` gained one section keyed by NAME; re-key after the merge as usual.

## What was NOT verified

- **Nothing met Discord.** No copy posted, deleted or sent silently; the silent flag's effect on notifications, the
  channel select's type filter, the modal and the confirm card were exercised through fakes only.
- **Discord's rate limits** for a delete + send every 5 seconds (the floor of `sticky_min_seconds`) — reasoned, not
  measured. The default is 30.
- **`guild.me` permissions on the live server's channels** — not read.
- **Schema 88 on the live database** — the migration is a new table and ran only on test databases.
- **The site section in a browser** was looked at once on the mock (rows, the three states, search, the deep link);
  the Add and Edit dialogs, Pause/Resume/Remove and the mode switch were NOT clicked in a browser — they are covered
  by `check.mjs` at the route level only.
- **TEST_MODE with a rehearsal home that differs from the guard's channel** — one test, fakes.
