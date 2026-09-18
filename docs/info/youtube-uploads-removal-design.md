# YouTube uploads — REMOVED; the links and the LIVE half stay

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **DESIGN, dispatched to Opus 2026-09-18 09:2x as
> branch `youtube-uploads-removal`**. **Last verified: 2026-09-18 09:2x** against `main` `7e6c493` (v138):
> `black_bloc/cogs/content/youtube.py` (`poller` ~689, `poll_once` ~721, the uploads sweep ~1014–1290, `fetch_feed`
> calls, the `/youtube` command description *"Your YouTube channel, and how uploads are announced"*), `black_bloc/youtube.py`
> (`FEED_URL`, `fetch_feed`, the feed parser; `probe_live` / `confirm_live` / `search_live` / `channel_info` are the LIVE
> half), `black_bloc/youtube_live.py` (LIVE only — untouched), `settings_store.py` (twelve `youtube_*` keys), the site's
> YouTube page + `/api/youtube/{links,links/{id},status,videos}`, `storage/db.py` (`youtube_links`, `youtube_videos`),
> KI-11 / KI-12 / KI-13 in `docs/KNOWN_ISSUES.md`, `docs/info/phase16-design.md` (the uploads design, F3),
> `docs/info/youtube-live-design.md` (deviations 1–26). ⚠️ Secret NAMES only.

## The ask, verbatim (owner, 2026-09-18 09:2x)

*"the youtube uploader we should just fully trash"* — after: *"i dont super care for uploads right now since so many
different people post"* (2026-09-17) and the measurement that YouTube's RSS feed endpoint now answers 404 for every
channel from every address (20/20 failures 2026-09-17 21:07; KI-12 had it at half on 2026-09-02).

## What goes, what stays

| Goes (the UPLOADS half) | Stays |
|---|---|
| the feed poll loop (`poller`, `poll_once`, the uploads sweep, `fetch_feed`, the Atom parser, the seed-on-link that counted 15 videos as seen, `youtube_videos` writes and reads) | the LINKS: `youtube_links`, `/youtube` ▸ link / unlink (member + staff), `/api/youtube/links*`, the DM on a staff unlink (`youtube_unlink_dms_them`) — the live half needs them |
| the upload ANNOUNCEMENT path (`youtube_template`, `youtube_channel_id`, `youtube_ping_role_id`, `youtube_ping_fan_roles`, `youtube_announce_shorts`, `youtube_poll_minutes`, **`youtube_mode`** itself) | the LIVE half untouched: `youtube_live_mode` / `_poll_minutes` / `_end_misses`, `probe_all`, the search + confirm, `live_health`, `botcheck`, `reading_live`, every `youtube.live_*` kind |
| the `/youtube` panel's upload lines and **Where uploads are posted…**; the site YouTube page's uploads sections (recent videos list, the upload settings); `GET /api/youtube/videos`; the upload fields on `/api/youtube/status` (`fetches`, `unchanged`, `unchanged_ratio`, `videos`, `announced`, `last_ok_at`, `last_error`, `failures`, `running`) | `youtube_log_level`, `youtube_panel_minutes`; `/api/youtube/status` keeps `api_key_set` + every live field |
| the log kinds only the uploads wrote (`youtube.seeded`, `youtube.announced`, `youtube.feed_failed` … — read `logkinds.py`; a kind the LIVE half also writes stays) | the `youtube` feature + its guide (rewritten: link your channel so a live stream is announced) |

- **`youtube_mode` is removed** (not kept as a dead switch): the feature's on/off is `youtube_live_mode` from now on, and
  `HIDDEN_WHEN_OFF` hides `/youtube` when THAT is off. Stored values for removed keys stay as harmless rows in
  `guild_settings` (say so; no migration to delete them).
- **`youtube_videos` is NOT dropped** (schema changes are additive here — rule 5 in `architecture.md`); nothing reads or
  writes it after this build; a later migration may drop it. Schema stays **45**.
- The `/youtube` command's description and panel text say what it is now: *"Your YouTube channel, and whether your live
  streams are announced"* (a key if the bot POSTS it; a command description is Discord metadata, a constant is fine).
- KI-11, KI-12, KI-13 → **CLOSED (moot — the uploads half was removed 2026-09-18)** with a one-line banner each, the
  bodies kept for the record. `phase16-design.md` gets a retirement banner at the top naming this doc (it is not moved —
  the live half's history is in it too).

## Tests, docs, gate

Delete the tests of what went (mirror rule: the same files, fewer tests); keep every live-half test green; the count
guards (keys **284 → 277**, routes 187 → 186, log kinds, HIDDEN_WHEN_OFF); `tests/api/test_contract.py`;
`tests/fixtures/youtube_feed*.xml` go with the parser. Both `pytest -n 8` orders, `ruff check .`, the ES-module
parse, `node site/mock/check.mjs`, `discordmd.test.mjs`, `labels.test.mjs`, env cleared. `code-notes.md` (delete the
notes of deleted code; do not leave notes pointing at nothing), `architecture.md` (the tree line for `youtube.py` /
the cog, keys, routes), `docs/info/README.md` row, `sweeps.md` rows `YU-a…` (a: `/youtube` shows link / unlink and the
live line only; b: the YouTube page shows links + live, no videos list; c: `/api/youtube/status` has no upload fields;
d: a linked channel going live is still announced — the live half survived). NOT `TODO.md` / `DONE.md` / `deploys.log`.

## Deviations

*(the build agent writes here what it had to do differently, dated)*
