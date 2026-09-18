# Meeting minutes — the bot joins a voice meeting, records per speaker, transcribes, and writes concise notes (PROTOTYPE)

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 🔨 **BUILT on branch `minutes`
> 2026-09-17, NOT merged, NOT deployed** — a PROTOTYPE that ships **off** (`minutes_mode` off) and is tested by
> staff only until the owner says it is ready. ✅ **The spike's verdict: voice receive WORKS on this stack** —
> `discord-ext-voice-recv` **0.5.2a179** installs and imports on **Python 3.12.10** against the pinned
> **discord.py 2.7.1**, and an Opus frame round-trips 96 bytes → 3,840 bytes of PCM through `discord.opus`
> (proved in a throwaway `.venv-spike`; the repo's own venv was NOT touched, and the three tests that need the
> extension `importorskip` there). The Fly image needs **`libopus0`** and nothing else — see Deviations 2.
> ⚠️ **Nothing below has met Discord:** no channel was joined, no word was transcribed, no notes were posted.
> Sweep rows `MM-a…MM-n` in [`../access/sweeps.md`](../access/sweeps.md) are what proves it; `MM-a` is the real join. **Last verified: 2026-09-17 17:19** against `main` `452b553`: `pyproject.toml` (discord.py
> ≥2.4, anthropic; no PyNaCl / voice extras yet), `config.py` (`groq_api_key`, `anthropic_api_key` exist),
> `black_bloc/llm.py` `HaikuClient` (the bot's LLM door), the Fly image (`Dockerfile` — check for ffmpeg/libopus),
> the temp-voice cog (the one voice-channel code in the bot: it never joins a channel). ⚠️ Secret NAMES only.

## Owner asks, verbatim (2026-09-17 17:0x–17:2x)

*"how hard would it be to have a meeting minutes bot? I want a command so if we're having an important meeting and i
want the bot to be able join and take notes. Maybe a full transcript that later gets processed into a concise set of
notes."* → the assessment (two builds; the risk is voice RECEIVE) → *"start building the prototype thats fine, we
will keep this feature off for a while and just test it until we're absolutely sure its ready"*.

## The risk first — voice receive, proved alone before anything else

discord.py sends voice and does not receive it. The prototype's FIRST commit is a spike that proves receive works
on this stack, or reports that it does not:

- Add `discord.py[voice]` (PyNaCl) and **`discord-ext-voice-recv`** (imayhaveborkedit's receive extension for
  discord.py 2.x) to `pyproject.toml`; `libopus` + `ffmpeg` to the Fly image (`Dockerfile` — say what was there).
- A pure sink `black_bloc/minutes_audio.py`: receives per-user Opus frames, decodes to 48 kHz PCM, and hands
  **one WAV chunk per speaker per `minutes_chunk_seconds` (60)** to a callback; audio is discarded after the chunk
  is handed off — nothing large ever sits on the volume.
- The spike's test is offline (fake frames → chunks); the report says plainly whether a real join was tried. The
  conductor tries the real join in the test guild after the deploy (row `MM-a`) — the bot's voice permissions
  (Connect, Speak is not needed) in *The Basement*'s **Meeting Room** are the first thing to check.
  If the extension does not install or import on Python 3.12 / the pinned discord.py, STOP after the spike and report.

## A. The feature

| Piece | What |
|---|---|
| `/minutes` (staff-only, `HIDDEN_WHEN_OFF`) | one panel: **Start taking notes** (joins the voice channel the presser is in; refused in words if they are in none, if a meeting is already running, or if anyone present wears `minutes_opt_out_role_id`), **Stop**, **Where notes go…**, **Logs**, the site link. The panel's status lines: recording since, speakers heard, chunks transcribed, last transcription error |
| The announcement | on join the bot posts `minutes_start_text` (default *"🔴 Black Bloc is taking notes in this meeting. Say **stop notes** or press Stop on /minutes to end it."*) into the voice channel's own text chat (or `minutes_channel_id` when set) — under `TEST_MODE` that message obeys the guard like every other (the rehearsal home / the test channel; say where it lands) |
| Transcription | each speaker chunk → **Groq Whisper** (`whisper-large-v3-turbo`, the key `GROQ_API_KEY` already exists; no key = refuse to start in words), with the speaker's display name attached; lines go into `meeting_lines` (`meeting_id, speaker_id, started_at, text`) as they come. Failures never stop the meeting — a `minutes.transcribe_failed` row and the chunk is dropped |
| Stop | `/minutes` ▸ Stop, the presser leaving with nobody left, or `minutes_max_hours` (3) — the bot leaves, closes the row, and builds the NOTES |
| The notes | the transcript (ordered, speaker-labelled) → the bot's existing LLM door (`llm.py`, the Anthropic key) with `minutes_prompt` (a text key; default asks for: a two-line summary, decisions, action items with names, open questions, in plain words) → `meetings.notes`; posted as an embed (+ the transcript as a `.txt` attachment) into `minutes_channel_id` (default blank = the meeting's own text chat; under the guard, the shadow home), and shown on a **Minutes** page on the site (`minutes.html`: the list, each meeting's notes editable in place by staff, the transcript below, **Post again**, **Delete**) |
| Consent | `minutes_opt_out_role_id` (role, blank): a member wearing it makes Start refuse, naming them; `minutes_start_text` is mandatory (blank refused) |

**Keys:** `minutes_mode` (off/on, **off**), `minutes_channel_id`, `minutes_opt_out_role_id`, `minutes_start_text`,
`minutes_prompt`, `minutes_chunk_seconds` (30–120, 60), `minutes_max_hours` (1–6, 3), `minutes_keep_days` (1–365,
90 — the transcript rows are deleted after). Namespace: ⚠️ the group select is at its 25-cap — file them under
**`events`** (a meeting is an event's cousin) and say so. Every word the bot posts is a key (owner rule 2026-09-17).

**Storage:** migration schema 43 → **44**: `meetings` (id, guild_id, channel_id, started_by, started_at, ended_at,
notes TEXT, notes_message_id, status) and `meeting_lines`. The audio is never stored.

**Site:** `minutes.html` + `page-minutes.js`, routes under `/api/minutes` (list, one, edit notes, post again,
delete; staff). Mock rows, contract, labels, the nav entry (`FEATURE_PAGES`).

## B. Tests (mirror the package)

`tests/test_minutes_audio.py` (frames → chunks, per speaker, discard after hand-off); `tests/test_minutes.py`
(the transcript order, the notes prompt assembly, the refusals' words); `tests/cogs/community/test_minutes.py`
(start refuses without a voice channel / with an opt-out present / without a key / mode off; stop builds notes and
posts; a transcription failure is a log row; max hours ends it); `tests/api/tools/test_minutes.py`;
`tests/storage/test_db.py` (the migration). The Whisper and LLM calls are faked; the extension is imported in one
test to prove it installs. Both orders.

## C. Docs

`code-notes.md`; this doc's `## Deviations`; `architecture.md` (cog 22, command 32, schema 44, the new module);
`docs/access/RECOVERY.md` (the image now needs ffmpeg/libopus — say where); a staff guide `minutes-take` in
`guides_seed.json`; `sweeps.md` rows `MM-a…` (MM-a is the real join); `docs/info/hosting.md` if the image changes;
`KNOWN_ISSUES.md` if the spike finds a limit. NOT `TODO.md` / `DONE.md` / `deploys.log`.

## Deviations

*(the build agent writes here what it had to do differently, dated)*

**All 2026-09-17, branch `minutes`, Opus.**

1. **The sink hands off 16 kHz MONO WAV, not 48 kHz stereo.** §"The risk first" says "decodes to
   48 kHz PCM and hands one WAV chunk per speaker". It still decodes to 48 kHz stereo — that is what
   the extension gives — but `minutes_audio.to_mono_16k` downmixes on every 20 ms frame before
   buffering. Two measured reasons: a 60-second chunk at 48 kHz stereo is **11.5 MB**, which is close
   to Groq's own upload ceiling, against **1.9 MB** at 16 kHz mono; and doing the conversion at the
   chunk boundary is ~960k Python loop iterations ON THE EVENT LOOP, against ~320 per frame. Whisper
   resamples everything to 16 kHz anyway, so nothing is lost that the model would have used.

2. **ffmpeg was NOT added to the image; `libopus0` was.** §"The risk first" says "libopus + ffmpeg to
   the Fly image". libopus is genuinely needed — measured: `discord.opus._load_default` loads a bundled
   DLL on Windows and calls `ctypes.util.find_library('opus')` everywhere else, so `python:3.12-slim`
   without `libopus0` decodes nothing. **ffmpeg is not needed at all on this path:** the bot never
   sends audio, the decode is libopus's, the WAV is written with the stdlib `wave` module in memory,
   and Groq accepts WAV directly. Adding it would put ~250 MB in the image for nothing. If a later
   build ever needs `FFmpegSink` or transcoding, this is the line to revisit.

3. **The spike found a limit and filed it: [KI-31](../KNOWN_ISSUES.md).** `discord-ext-voice-recv`
   has no stable release — `0.5.2a179` is an alpha, so `pyproject.toml` has to name a pre-release for
   pip to consider it — and `discord/ext/voice_recv/sinks.py` imports `audioop`, **removed in Python
   3.13**. The image is `python:3.12-slim`, so this is fine today; it means the base image can no
   longer be bumped without checking that first, which `hosting.md` now says.

4. **Eleven keys, not eight, and `events` gained a Find box.** The design named eight. Three more
   were needed: `minutes_notes_title` (owner rule 2026-09-17 — every word the bot posts is a key; the
   notes embed has a heading), `minutes_panel_minutes` (every panel has one — KI-20), and
   `minutes_log_level` (generated for every feature in `FEATURES`). All eleven are
   `NAMESPACE_OVERRIDE`'d onto **`events`** as instructed, which takes that group to **33** keys — past
   the select's 25 — so `events` now shows *25 of 33* and reaches the rest through **Find…**, beside
   `chat` and `modmail`. `settings_panel`'s guard test was updated from two such groups to three, and
   that is the visible cost of the cap.

5. **`minutes` IS its own log FEATURE, even though its keys are filed under `events`.** Filing the
   kinds under events too would have sent `minutes.*` rows to the events page and made the panel's
   **Logs** button show every event row. `FEATURES` is **20 → 21**; the extra `minutes_log_level` key
   it generates is overridden onto `events` like the rest, so `settings_panel.groups()` is **still 25**.

6. **One commit for storage + keys + `/minutes` + the transcription loop + the notes, not four.**
   The brief listed them as four boundaries. The cog, the session and the domain module are mutually
   dependent and the repo's AST guard tests (`test_logkinds`, `test_loops`, `test_actionlog`,
   `test_bot`) fail on any tree that has the keys without the cog, so an intermediate commit would
   have been red. The spike, the site half and the docs are their own commits as asked.

7. **`black_bloc/minutes_session.py` is a fourth module the design did not name.** The design named
   `minutes_audio.py`, the cog, and the routes. One meeting's RUNTIME — the voice client, the queue,
   the Whisper worker, and the four ways a meeting ends — is behaviour rather than a Discord surface,
   and `CLAUDE.md` says every behaviour is its own module. It also makes the loop testable without a
   cog: `tests/test_minutes_session.py` drives it with a fake voice client.

8. **A partial unique index does the "one meeting at a time" work, not just a lock.** Review
   checklist 6 asks for a per-key lock AND a DB constraint on the open state.
   `meetings_one_open ON meetings(guild_id) WHERE ended_at IS NULL` is the constraint; the in-memory
   `bot.minutes_sessions` dict is the read-decide-write side, and `may_start` re-asks the database.

9. **The announcement and the notes obey the guard through one helper, `minutes.landing`.** Under
   `TEST_MODE` a channel the guard refuses falls back to the rehearsal home (`shadow.channel_id`), and
   the sentence naming where it went is returned to the caller and printed by both the panel and the
   site — rather than each door inventing its own wording.

10. **What was NOT built.** The design's `/minutes` panel line mentions *"Where notes go…"* and it is
    there, but as a channel picker that writes `minutes_channel_id` — there is no per-meeting override.
    Nothing reconciles a meeting against Discord on `cog_load` beyond closing a stranded row, because a
    voice connection does not survive a restart in any form worth reconciling.

## What was NOT verified

Everything Discord-side. No voice channel was joined, no audio was ever received from Discord, no
chunk was sent to Groq Whisper, no notes were written by a real model, and no embed was posted. Every
test in this build runs on fakes: hand-built PCM frames, a fake voice client, a fake Whisper door and
a fake LLM door. The Fly image was NOT rebuilt, so `libopus0` resolving inside `python:3.12-slim` is
**inference from `discord.opus._load_default`'s source**, not a measurement — `MM-a` and the
`flyctl ssh` one-liner in [`../access/RECOVERY.md`](../access/RECOVERY.md) are what would prove it.
