# Go-live replays — a replay is announced plain (or not at all), never spotlit

> **Audience:** the conductor, reviewers, and the next session touching the Go-live channel list, its
> announcements or its spotlight.
> **Status:** TRACKED · 🔨 **BUILT on branch `golive-replays`** (off `main` `49aeb2c2`), NOT merged, NOT deployed.
> Schema **76 → 77**, registry keys **631 → 641**, six new log kinds, one new route.
> **Last verified: 2026-09-27** — against the branch's own code by the tests (`tests/test_golive_replay.py`,
> the replay block at the end of `tests/cogs/content/test_spotlight.py`, the replay block at the end of
> `tests/api/tools/test_golive.py`, `tests/test_twitch.py`, `tests/storage/test_db.py`), the whole suite
> (9151 passed), `node --test site/mock/*.test.mjs`, and `node site/mock/check.mjs` against a mock from the
> worktree on 8826 (*22 pages, 266 routes*), plus `curl` of the mock's `GET /api/golive/spotlight` (the
> Frost Fatales fixture carries `replay`) and `POST …/3/treat-live` (answers, then 409 in words).
> ⚠️ **NOT checked:** anything against Discord, Twitch or Fly; what Twitch's `type` really says for a
> GDQ/ESA replay (see §Twitch's `type`); the live database (the migration has NOT run there); no browser
> rendered the Go-live page with a replay on it. Secret NAMES only.

## The asks, verbatim (owner, 2026-09-27 21:2x Phoenix)

1. *"Looks like GDQ is running a replay. I know esam does that too. We can write code to try and not spotlight
   replays? Error on the side of posting replays of it's fuzzy. Wouldn't want to miss"*
2. *"It's usually on stream title"* — relayed by the conductor mid-build: the TITLE is the primary signal;
   Twitch's rerun `type` is secondary, kept but not depended on.

## Twitch's `type`, in this code

- **Before this build the client never read it.** `black_bloc/twitch.py:stream_from` built `TwitchStream` from
  `user_id/user_login/user_name/game_name/title/started_at/game_id/thumbnail_url` only.
- **Now:** `TwitchStream.stream_type` carries Helix's `type`, lower-cased, `""` when absent.
- **What Helix sends** (from Twitch's API reference as remembered, NOT re-read or measured today): `Get Streams`
  documents `type` as `live`, or an empty string on error. The old v5 API had `stream_type` values including
  `rerun`; Twitch's reruns feature has since been retired, so **a real `rerun` is probably never seen**. The code
  treats `type == "rerun"` as a certain replay and every other value (including `live` and `""`) as saying
  nothing — which is why the title does the real work, as the owner said.

## As built

**Detection** — `black_bloc/golive_replay.py:verdict` (pure):

| Signal | Result | Logged |
|---|---|---|
| `type` is `rerun` | replay, reason `type` — even inside a marathon (Twitch said so) | `golive.replay_detected` |
| a `golive_replay_words` word in the title, whole word, any case, **outside** every marathon span on the channel | replay, reason `title:<word>` | `golive.replay_detected` |
| the same, **inside** a marathon span (start − `marathon_spotlight_lead_minutes` → end + `marathon_spotlight_tail_minutes`, any marathon row on the channel, tracked or not, active or not) | **live** | `golive.replay_overruled` `because: marathon` |
| the same, and the title also carries a `golive_replay_live_words` word | **live** | `golive.replay_overruled` `because: live:<word>` |
| nothing matched | live | nothing |

"Whole word" is `(?<!\w)word(?!\w)`: `[REPLAY]`, `Replay:`, `(Rerun)`, `VOD —`, `RERUN of`, `#replay` match;
`Replayability`, `Vodka`, `Rerunner`, `SuperReplay`, `Hunt_replay_bot`, `Alive` do not. Each decision is logged
once per session (at the session's start — both kinds are routine).

**What a replay gets** — `golive_replay_action`:

| Value | What happens |
|---|---|
| `plain` (default) | `golive_replay_template` posted with NO role mention (`allowed_mentions.roles = False`), NO card, NO pin, NO bumps, NO window-open reminder. `golive.replay_announced` (shadow: `golive.would_replay_announce`). |
| `skip` | nothing posted; the session is opened with no message (so the page can show it and Treat as live can reach it). |
| `live` | the old behaviour: full treatment; the session records the reason with `replay_cleared = action`. |

The row's `spotlight` flag is never touched — a kept GDQ row stays spotlit in the data; only the session's
treatment changes.

**Model** — three `spotlight_sessions` columns (schema 77, `ADDED_COLUMNS`, no backfill): `replay_reason`
(`type` / `title:<word>`, NULL = live), `replay_action` (the action at the start), `replay_cleared` (NULL while it
is a replay; `staff` / `title` / `type` / `marathon` / `action` once it is live). `golive_replay.is_replay`
= reason set and not cleared.

**Staff final say — Treat as live.** `cogs/content/spotlight.py:treat_as_live` (under the row lock) →
`Spotlight.upgrade`: the FULL announcement is posted first (pings by the row's gate, card, pin), and only once it
is out is the replay post deleted and the session marked `replay_cleared = staff`
(`golive.replay_treated_live`, IMPORTANT, `web.` head from the site). A failed post leaves the replay post and
the replay as they were. Doors: the Go-live drawer's Spotlight card (the button replaces **Bump now** while the
stream is a replay), the `/golive` ▸ Channels card (same swap, row 1), and
`POST /api/golive/spotlight/{id}/treat-live` (409 `not_replay` / 502 `post_failed` / 503 `no_cog`, each in the
key's words).

**The flip (err on posting).** Every poll of an open replay session re-reads the verdict; the moment it is live
(the title changed, a marathon's span arrived, or staff set the action to `live`) the same `upgrade` runs
(`golive.replay_upgraded`, `because` = what changed). A live session is never downgraded when a later title
says replay. While it stays a replay, a new title re-words the plain post with the replay sentence.

**Keys (ten, golive namespace, registry + mock row + label + a "Replays" drawer on the Go-live page):**

| Key | Type | Default |
|---|---|---|
| `golive_replay_action` | enum `plain`/`skip`/`live` | `plain` |
| `golive_replay_words` | text (may be blank) | `replay, rerun, rebroadcast, re-broadcast, vod, encore` |
| `golive_replay_live_words` | text (may be blank) | `live` |
| `golive_replay_template` | text `{name} {game} {title} {url} {platform}` | `**{name}** is showing a replay — {title} {url}` |
| `golive_replay_state` | text `{reason}` | `Replay detected ({reason})` |
| `golive_replay_reason_type` | text | `Twitch marks the stream a rerun` |
| `golive_replay_reason_title` | text `{word}` | `the title says “{word}”` |
| `golive_replay_treat_live_label` | text | `Treat as live` |
| `golive_replay_treated_said` | text `{login}` | `**{login}** is treated as live for this stream — announced again with the full spotlight.` |
| `golive_replay_not_replay_said` | text `{login}` | `**{login}** is not showing a replay right now, so there was nothing to change.` |

## Deviations

1. **A third action, `live`.** The brief said `plain` / `skip`; `live` is the off-switch (checklist 33 — the
   decision configurable both ways), so turning detection off never needs a deploy. Detection still logs.
2. **The plain post carries no card (embed).** The live card's top line says *is now live*; a replay card would
   contradict its own sentence. `golive_embed` still governs live posts.
3. **Treat as live posts a NEW message and deletes the replay post**, rather than editing it — an edit never
   pings, and the brief's "full spotlight treatment" includes the role mention.
4. **A `rerun` type wins even inside a marathon.** The brief's fuzzy rule is about title words; Twitch's own mark
   is not fuzzy.
5. **A skipped replay still opens a session** (no message). It is what lets the page say *Replay detected* and
   Treat as live reach it; the boot reconcile keeps such a session instead of closing it as message-less.
6. **YouTube too, by title.** `announce_info` is shared with the YouTube half of a channel row
   (`cogs/content/youtube.py`), so a YouTube live title with a replay word is judged the same way (no `type`
   there). The member go-live path (`cogs/content/golive.py`, presence-driven) does NOT share this code and is
   untouched — the owner's examples are channel rows.
7. **On the `/golive` card, Treat as live replaces Bump** in row 1 (Discord's five rows are full); a replay has
   no bump anyway.
8. **Every marathon row on the channel counts** for the span — active or paused, tracked or not — because a
   marathon anywhere near is the fuzzy case, and fuzzy is live.
9. **`golive_replay_words` matching treats `_` as part of a word** (`Hunt_replay_bot` is a name, not a replay).
10. **Not in the Discord preview gallery.** `golive_replay_template` is edited on Settings ▸ Go-live ▸ Replays;
    the Preview page has no replay entry yet.

## What was NOT verified

- **Twitch.** No live Helix answer was read; whether GDQ/ESA replays carry any `type` other than `live` is
  unknown. The title words are a guess from the owner's two examples and common GDQ/ESA naming — the first live
  replay is the real test (sweep `GR-a`).
- **Discord.** No post, pin, delete or role mention was made against Discord; all behaviour is fakes.
- **The live database.** Schema 77's three columns have not been added on Fly.
- **The page by eye.** No browser rendered the Go-live drawer's replay line or the Replays settings drawer; the
  JS passed `node --check` and the mock's route/shape checks only.
- **Checklist 37 on the upgrade.** It runs under the existing per-row lock both from the poll and from staff, so
  two presses post once — reasoned from the code, and covered only by the second press answering `not_replay`.
