# Meeting minutes — the bot joins a voice meeting, records per speaker, transcribes, and writes concise notes (PROTOTYPE)

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **DESIGN, dispatching to Opus 2026-09-17 17:2x
> as branch `minutes`** — a PROTOTYPE that ships **off** (`minutes_mode` off) and is tested by staff only until the
> owner says it is ready. **Last verified: 2026-09-17 17:19** against `main` `452b553`: `pyproject.toml` (discord.py
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
