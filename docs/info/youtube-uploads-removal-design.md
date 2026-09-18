# YouTube uploads — REMOVED; the links and the LIVE half stay

> **Audience:** the build agent and reviewers. **Status:** TRACKED · ✅ **LIVE as v139** — merge `72733e5`, release `fad4e50`, deployed **2026-09-18 10:05** Phoenix; the `## Deviations`
> foot is the truth (sixteen); sweeps **609–612** are the owner's; verified: boot clean (logged in 10:05:49, the youtube cog loaded, one 'settings ignored: youtube_mode' line for the orphaned stored row — as designed — and no feed warning for the first time since v131), /health ready; /api/youtube/status read in the browser after the boot (see the DONE entry for what it carried). Was: BUILT on branch
> `youtube-uploads-removal` (off `main` `9bc1982`). Measured in the worktree: registry keys **284 → 277**, mock
> **20 pages / 187 → 186 routes**, tests **6808 → 6720 passed + 3 skipped** (`pytest -n 8` forward
> and under `BB_REVERSE=1`), schema unchanged at **45**. The `## Deviations` foot is the truth where
> this build departed from the body. Was: 📐 DESIGN, dispatched to Opus 2026-09-18 09:2x. **Last verified: 2026-09-18 09:2x** against `main` `7e6c493` (v138):
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

*Written 2026-09-18 by the build agent on branch `youtube-uploads-removal`, cut from `main`
`9bc1982`. Everything below is a departure from the body above, or a decision the body left open.
⚠️ **Nothing in this build has met Discord or a browser** — a worktree holds no token, and no page
was rendered.*

1. ⚠️ **A channel's TITLE came from the uploads feed, and the body did not say what replaces it.**
   `YouTubeClient._title_of` fetched `FEED_URL` and ran the Atom parser over it, so it had to go
   with `fetch_feed`. It is now **one `channels.list(part=snippet, id=…)` call — 1 unit, only at
   link time, and only where `YOUTUBE_API_KEY` is set**; without a key `resolve` answers
   `(channel_id, "")` and every surface falls back to the `UC…` id, which they all already did
   (`row['title'] or row['channel_id']`). The old path was free but measured dead: the feed
   endpoint answered 404 for every channel from every address on 2026-09-17 (20/20), so in
   practice `_title_of` has been returning `""` in production for some time. A new pure helper,
   `youtube.title_of(payload)`, reads the answer, and `_title_of` swallows a `YouTubeError` so a
   refused lookup still links the channel.
2. ✅ **DECIDED — the whole `/youtube` ▸ Setup sub-panel is REMOVED, not trimmed.** The body listed
   *"the `/youtube` panel's upload lines and **Where uploads are posted…**"*. Everything that panel
   edited was an upload key (`youtube_channel_id`, `youtube_ping_role_id`,
   `youtube_announce_shorts`, `youtube_ping_fan_roles`, `youtube_template`, `youtube_poll_minutes`)
   except one: **`youtube_panel_minutes`**, which was the second field of its `Numbers…` modal. A
   sub-panel, a `ChannelSelect`, a `RoleSelect`, two toggles, two modals and a `ForgetPick` kept
   alive for one integer is a surface nobody would build. The key keeps **both doors** through the
   registry — the `/settings` panel's own key card and the dashboard's Settings page — which is
   exactly what checklist 33 asks for (*"a decided default is a registry key … which gives the
   dashboard's Settings page + the `/settings` panel's own key card for free"*). Gone with it:
   `save_setup`, `run_setup`, `setup_embed`, `setup_view`, `render_setup`, `render_forget`,
   `open_setup`, `open_forget`, `SetupButton`, `UploadChannelPick`, `PingRolePick`, `ForgetPick`,
   `WordsModal`, `NumbersModal`, `SETUP_KEYS` and the `youtube.setup` log kind.
3. ✅ **DECIDED — the Go-live page's YouTube section keeps a mode switch, and it is now
   `youtube_live_mode`.** The body said the uploads sections go; it did not say what happens to the
   switch at the head of the section, which was `youtube_mode`. Deleting it outright would have
   left the section's own on/off two clicks away in **YouTube settings** below it, on a page where
   every other section (go-live, pings) carries its switch at the top. So `channelsSection` reads
   `youtube_live_mode` and `namespaceSettings('youtube', …)` omits it, which is the shape
   `golive`/`pings` already use. The section is titled **YouTube channels**, its settings card
   **YouTube settings** and its logs card **YouTube logs**.
4. **`logkinds.FEATURE_LABELS["youtube"]` is now `YouTube`, not `YouTube uploads`.** The body did
   not name it, but that one string is read by the Logs page's feature filter, by the settings
   root's mode block, by `log_level_help` (which lowercases it into *"which youtube uploads log
   lines reach…"*) and by `api/tools/youtube.FEATURE` in the 503 sentence. A label naming the half
   that went would have been wrong in four places at once. `site/public/assets/logs.js` and the
   mock's `LOG_LEVEL_FEATURES` row were changed to match.
5. ⚠️ **`settings_panel.MODE_LABELS` needed a new entry, and the tests caught it.**
   `_hidden_when_off_modes` derives a feature name with `key.removesuffix("_mode")`, so moving
   `HIDDEN_WHEN_OFF`'s entry from `youtube_mode` to `youtube_live_mode` made it ask
   `FEATURE_LABELS["youtube_live"]` — a namespace that does not exist — and the `/settings` root
   printed the raw string `youtube_live`. `MODE_LABELS["youtube_live"] = FEATURE_LABELS["youtube"]`
   fixes it without a second copy of the word. Found by
   `tests/test_settings_panel.py::test_the_mode_block_says_modmail_in_words_and_never_as_on_or_off`,
   not by reading.
6. **`counts()` survives as `{"links": n}` rather than being replaced.** It is in the cog's
   `__all__` and `api/tools/youtube.py` calls it; a rename would have been churn in two files for
   no gain. `videos` and `announced` are gone from it because they counted `youtube_videos`, which
   is now orphaned — a count of a table nothing writes only ever goes stale.
7. **`link_channel` returns a 2-tuple now, not a 3-tuple.** The third element was the seeded count,
   which no longer exists. `api/tools/youtube.py` is the only other caller and was changed in the
   same commit. `youtube-panel-design.md`'s deviation about the 3-tuple is therefore half-retired;
   the `LinkRefused` half of it is untouched and still carries the 400/409.
8. **`set_link` no longer names `etag` or `seeded` in its INSERT.** Both columns keep their schema
   defaults (`NULL`, `0`) and nothing reads them any more, so no surface shows a permanent *not
   counted yet*. They stay in the table — schema is additive here (rule 5 in `architecture.md`) —
   exactly as `youtube_videos` does. **SCHEMA_VERSION stays 45** and there is no migration.
9. **Six log kinds removed from `logkinds.ROUTINE`**, not five and not eight:
   `youtube.announce`, `youtube.mode`, `youtube.poll_degraded`, `youtube.seeded`, `youtube.setup`
   and `youtube.skipped`. `youtube.would_announce` and `youtube.post_failed` were never table
   entries in the first place (a `.would_` shadow kind and a `_failed` suffix are both classified
   by rule), so nothing had to be removed for them. `youtube.probe_unreadable` stays in `IMPORTANT`
   and `youtube.live_*` all stay — they are the live half's.
   `tests/test_logkinds.py::test_no_classification_entry_is_dead` is what makes this a rule.
10. **`selftest_panels` lost its `youtube` sender AND a line in `send_pings`.** The sender posted a
    rendered upload sentence, which no longer exists; `send_pings` built its prefix from
    `golive_ping_role_id` + `youtube_ping_role_id` + the events role, and the middle one is a
    deleted key. The `PanelDoor("youtube", …)` entry stays — the panel still exists and the
    self-test still opens it.
11. **`personas.py`, `config.py` and `api/costs.py` each carried one sentence about uploads**, none
    of them named in the body. `/youtube`'s `/help` line now says *"saying whether your live streams
    are announced"*; `youtube_api_key`'s field description says *"unset leaves live detection on the
    page alone"*; and the Costs page's secret note says the key *"names the video a linked channel
    is live on, and turns an @handle into a channel id"* instead of *"sorts a new upload into video,
    Short or live stream"*. Every word the bot posts being editable is a standing rule; these three
    are metadata and a field description, which the design already says a constant is fine for.
12. **The `golive-announce` guide's step 6 said *"One link does both: your uploads AND your live
    streams are announced"*.** It now reads *"Your live streams are announced here too."* Step 3's
    YouTube sentence and the *"You went live on YouTube and nothing posted"* fault were already
    about the live half and are unchanged. ⚠️ **Per deviation 11 of `youtube-live-design.md`,
    `guides.refresh_seeds` rewrites `seed_do`/`seed_expect` by position, so this amended wording
    DOES reach a guild already seeded** — but a guide a staffer has edited by hand keeps their words.
13. **One test file was rewritten rather than trimmed, and one was trimmed hard.**
    Measured, test FUNCTIONS: `tests/test_youtube.py` **69 → 43** (the feed, duration and
    classification tests deleted; the resolve/handle/panel-table/health/error ones kept, and four
    ADDED that assert the removal — the module has no `FEED_URL`/`parse_feed`/`render`/`Video`/
    `classify_row` and the client no `fetch_feed`/`classify`; no move opens a Setup panel; the
    health lines say neither *sweep* nor *upload*; the staff tail is two moves, not three).
    `tests/cogs/content/test_youtube.py` **122 → 84** — it lost its whole uploads half (seeding,
    announcing, modes, test mode, Shorts, D6, pings, the feed's flakiness, the poll gap) and kept
    every live-probe test untouched; `_Feed` became `_Client`, which answers `resolve` and `close`
    and nothing else. `tests/api/tools/test_youtube.py` **20 → 17**, and it now asserts the nine
    upload status fields are ABSENT and that `GET /api/youtube/videos` answers **404**. ⚠️ **`tests/fixtures/youtube_feed.xml` is DELETED** with the parser
    it pinned; the five `youtube_*_page.html` fixtures are the live half's and are untouched.
14. **Two count guards outside the YouTube tests had to move**, and both are honest consequences
    rather than test-fixing: `tests/test_loops.py:BEFORE_LOOPS` **20 → 19** (the uploads
    `poller.before_loop` is gone) and `tests/api/test_status.py`'s recorder map for the YouTube cog
    lost its `poller` entry. Neither is a YouTube test; both would have failed silently as
    "the number changed" without this note.
15. ⚠️ **NOT touched, and it is stale: `docs/README.md` says `info/` holds "**66** beside its
    index".** Measured 2026-09-18: **87**. It was already 20 out before this build added the
    eighty-eighth file, and its header is dated 2026-09-11, so it is reported here rather than
    edited — `docs/README.md` is not in this design's scope and fixing the number without
    re-verifying the rest of that header would be a measurement wearing another's clothes.
16. ⚠️ **What was NOT verified.** Nothing met Discord: no panel was opened, no button pressed, no
    modal submitted, `python -m black_bloc` was never booted. No browser rendered the Go-live page,
    so **the `channelsSection` rewrite is proved only by the ES-module parse and the mock contract**
    — `site/mock/check.mjs` checks the routes a page reads, not what it draws. The live half is
    proved by the same fixtures and fake client it always was; **no real YouTube request was made by
    this build**, including the new `channels.list` title lookup, which has never met Google's API.
    Sweep rows `YU-a` … `YU-d` are the proof that is missing, and `YU-d` needs the live bot on Fly.
