# Shadow has one meaning — test, staff only, and the switches that folded or retired

> **Audience:** the conductor (merge + deploy), reviewers, and later sessions. **Status:** TRACKED ·
> 🔨 **BUILT on branch `shadow-one-meaning`** (off `main` `0720ee9d`, v243), **NOT merged, NOT deployed**.
> **Last verified: 2026-10-20 02:3x Phoenix** — measured on the branch: `pytest -n auto` 13,496 passed +
> 1 skipped, `ruff check .` clean, `node site/mock/check.mjs` ok against a FRESH mock (port 8823, nonce
> `som-1`: 28 pages, 375 routes, 353 core settings), registry `len(KEY_TYPES)` **1222** (was 1230), the
> mock's `/api/settings` 1222 keys; live values read through `scripts/read.ps1 -Path /api/settings`
> (operator token, 2026-10-20 02:13). ⚠️ **NOT verified:** anything in Discord; the migration against the
> live database (it ran against a fixture mirroring the live API read); which default-valued rows are
> actually STORED live (the API shows a value, not whether it is stored — the migration drops them
> either way); the value of the stale `youtube_mode` row (the boot log names only the key); phone width.

Owner decisions 2026-10-19, sheet items **p3b, p3c, p3d, p3e, p4a, p4b, p4c, p4d, p4e, p4g, h1, h2** of
[`switch-audit-2026-10-19.md`](switch-audit-2026-10-19.md) (§1a, §1b, §4 P3, P4; §5 I8), plus two
leftovers the conductor added: `pb_feed_no_channel_words` (no reader since v241) and the stale
`youtube_mode` row the boot log reports as ignored. Build 4 of the sheet; builds 1–3 are LIVE (v241–v243,
[`posts-one-switch-design.md`](posts-one-switch-design.md), [`one-test-channel-design.md`](one-test-channel-design.md)).

## 1. Before / after, per key (live values 2026-10-20 02:13)

| Key | Live | Before | After |
|---|---|---|---|
| 14 automated / safety modes (marathon, golive, birthday, points, brackets, pb_feed, raidtrain, applications, events, honeypot, automod, structure_backup) | various | stored `shadow`, read **shadow** | stored `shadow` unchanged, read **test** everywhere (p3b). Honeypot and automod behave exactly as before |
| `tempvoice_mode` | on | read **shadow** | stored `shadow` unchanged, read **staff only** (p3c) |
| `youtube_live_mode` | **on** | off/shadow/on, its own switch | **RETIRED** → `golive_youtube` |
| `golive_youtube` | — | — | **NEW** bool *Also watch YouTube*, default false, Go-live group; **true** after the migration (p3d) |
| `spotlight_mode` | **on** | off/shadow/on | **RETIRED**; spotlights follow `golive_mode` (p3e) |
| `golive_mode` | **on** | help said "Off by default" | help says what it governs and that the default is test (h2) |
| `birthday_mode` | **on** | help said "log only" | help: test logs the day's wishes; a wish staff post by hand goes to the test channel (h1) |
| `boot_status_mode` | on (= default) | enum | **RETIRED** → constant `presence.BOOT_STATUS = "on"` (p4a) |
| `handoff_mode` | on (= default) | enum | **RETIRED** → constant `handoff.MODE = "on"` (p4d) |
| `chat_greeting_via_model` | on (= default) | enum off/on | **bool**, default true (p4b) |
| `golive_costream_mode` | on (= default) | enum off/on | **RETIRED**; co-streaming always joins (p4c) |
| `modmail_enabled` | **true** ★ | bool, false = old ModMail bot | **RETIRED**; Black Bloc always answers (p4e) |
| `points_modmail_off_said` | default | words for the modmail-off refusal | **RETIRED** with `modmail_enabled` (no other reader) |
| `pb_feed_posting_shadow` | default | the member's line while the feed rehearses | **RETIRED** (p4g) |
| `pb_feed_no_channel_words` | default | no reader since v241 | **RETIRED** |
| `youtube_mode` (stale row) | — | ignored at every boot | row **dropped** by the migration |

Registry **1230 → 1222** (nine retired, one new). Contract `core_keys` **357 → 353**. Go-live page keys
**89 → 87**. `/settings` mode list (`FEATURE_MODES`) **24 → 22** (`youtube_live_mode` left `HIDDEN_WHEN_OFF`,
`modmail_enabled` left `EXTRA_MODES`); `/youtube` now hides under `golive_mode`.

## 2. The one wording source

There was none: every page printed `String(choice)` and every panel its own label. Now:

- **Python:** `black_bloc/mode_words.py` — `mode_word(key, value)` (`shadow` → *test*, *staff only* for
  `tempvoice_mode`), `stored_mode` (a typed *test* / *staff only* is read back as `shadow`), `words_for`.
  Read by `settings_store.display_value` (enum) and `coerce_value`'s refusal, `settings_panel.mode_state`,
  `/settings` choice options, and every feature panel's mode select and *now X* sentence (automod, honeypot,
  birthdays, events, temp voice, go-live, raid trains, applications, marathon, personal bests, points,
  structure backup, modcases).
- **Site:** `labels.js` `modeWord(value, key)` — the same table. `ui.js` segments, `modeSwitch`, `modeChip`,
  the Overview and Moderation pills, the nav-dot title, Role menus' applications switch, Guides' pill, the
  Go-live probe badge. `data-value` / `data-mode` stay the stored value.
- Prose sentences that named the state (*Raid trains are in **test***, *Keep it in test*, help texts) say
  *test* literally; they are sentences, not value labels.

## 3. The migration (`black_bloc/shadow_one_meaning.py`)

Runs once per boot in `setup_hook`, after `_migrate_test_channel`, before `install_rehearsal_home` and every
cog. Raw SQL, no schema change; a failure is logged and never stops the boot. Per guild with any stored
retired row or a string `chat_greeting_via_model`:

1. `youtube_live_mode` → `golive_youtube`: `on` → true; `off` → false; `shadow` → **false** (fail safe: its
   shadow only logged, so nothing visible is lost; the row's `notes` say so). Skipped if `golive_youtube`
   is already stored.
2. A stored `chat_greeting_via_model` string → true (`on`) / false (`off`).
3. `spotlight_mode` `off` while `golive_mode` is not off → a note *spotlights now follow golive_mode* (live
   both are on: no note).
4. Delete every stored row of the ten retired keys (`youtube_live_mode`, `spotlight_mode`,
   `boot_status_mode`, `handoff_mode`, `golive_costream_mode`, `modmail_enabled`, `pb_feed_posting_shadow`,
   `pb_feed_no_channel_words`, `points_modmail_off_said`, `youtube_mode`).
5. One `settings.migrated` row `{build, removed, values, written, notes}`; the store re-reads. A second boot
   finds nothing (tested twice).

**Dry run against the live-mirroring fixture** (`tests/test_shadow_one_meaning.py::live_mirror` — the
non-default live rows plus `youtube_mode`; run twice, identical, nothing written):

```json
[
  {
    "guild_id": 1073710702776299640,
    "drop": {
      "youtube_live_mode": "on",
      "spotlight_mode": "on",
      "modmail_enabled": true,
      "youtube_mode": "on"
    },
    "write": {"golive_youtube": {"before": null, "after": true}},
    "notes": []
  }
]
```

If the default-valued rows are stored live they are dropped too and listed in `removed` (tested:
`test_rows_stored_at_their_old_defaults_go_too_and_the_greeting_becomes_a_bool`).

## 4. What changes the moment it ships

- **Members:** nothing visible. YouTube streams keep being announced (`golive_youtube` true, go-live on),
  spotlights keep being announced (go-live on), modmail keeps answering, co-streams keep joining, the boot
  status stays red while restarting, a hello is still answered by the model. A temp-voice lobby refusal
  says *staff only* where it said *shadow*.
- **Staff:** every three-way mode reads **on · test · off** (temp voice **on · staff only · off**) on the
  Settings page, feature pages, `/settings` and every panel; typing `test` into `/settings set-value` works.
  Go-live page strip: *Go-live announcements*, *Also watch YouTube*, *Ping roles* (no YouTube or Spotlight
  switch). `/golive` staff get *Also watch YouTube* / *Stop watching YouTube*. The `/youtube` panel loses
  *Live streams are…*. `/modmail` ▸ Setup loses *Answer DMs on/off* and the *answering DMs* line. `/settings`
  root lists 22 modes (no YouTube, no Modmail line). Nine keys vanish from the Settings page.

## 5. Calls on items 5 and 6

- **`chat_greeting_via_model` → bool (kept as a key).** `chat_llm.greets_by_model` reads it as on vs
  anything else — but it is a real choice (model-written hello in the member's tone vs the written lines:
  tone and model cost), with a Chat page control (`page-chat.js`). So a bool, not a constant.
- **`golive_costream_mode` → removed.** Its only effect was `off` = the v135 hold-back
  (`joins_session` returned false), which the owner called *"silly to suppress one of the live avenues
  someone is on"* (costream-design, the ask). No staff-wanted behaviour is lost.
- **`modmail_enabled` → retired.** Readers: the DM path, the member door, the staff door, the Setup toggle,
  the panel's incumbent line, chat's escalation sentence and staff note, the points refusal. Every `false`
  branch either pointed at *"the **ModMail** bot instead — it is still the one on duty"* or named staff
  roles in its place; the cut-over plan (row 7) had the owner disable the incumbent the same hour. Live is
  `true`, so retiring changes no live behaviour. ⚠️ **Consequence the owner should know:** modmail no longer
  has an off switch. The stops left are per person (Blocked…), the member door (`modmail_member_command`)
  and the staff door (`modmail_open_with`). Whether the old ModMail bot is still in the server was NOT
  verified (nothing here can see it).

## 6. Rollback

Redeploy **v243** (`a5f98055`) and restore the pre-deploy snapshot ([`../access/deploy.md`](../access/deploy.md)).
Without the snapshot, after a v243 redeploy set `youtube_live_mode` = on, `spotlight_mode` = on,
`modmail_enabled` = true (the other retired keys were at their defaults) — otherwise v243 reads YouTube
**off** (its default) and modmail **off** (default false), which would stop YouTube announcements and
modmail. ⚠️ That makes the snapshot (or those three writes) mandatory on rollback. `golive_youtube` and a
bool `chat_greeting_via_model` are harmless to v243 (unknown key ignored; a bool greeting reads `!= "on"`
→ written lines until set back to `on`).

## 7. Deviations

1. `points_modmail_off_said` retired although not on the sheet — its only reader was the `modmail_enabled`
   refusal.
2. h1: the brief said birthday shadow = a rehearsal copy; the code does both — the daily sweep only logs,
   a staff *Post today's wishes* sends a rehearsal copy to the test channel. The help says both.
3. Go-live in **test** now covers spotlights, which in shadow post a rehearsal copy, while a member's
   stream only logs — two kinds of test under one switch (audit §1a kinds a/b). Not unified here.
4. `/youtube` hides with `golive_mode` (it hid with `youtube_live_mode`); `golive_youtube` false leaves it up.
5. With `pb_feed_posting_shadow` gone, a matched member reads no posting sentence while the feed is in test.
6. `boot_status_mode` / `handoff_mode` constants keep their off branch (`HANDOFF_OFF` reworded, no key
   named) so flipping the constant still refuses in words.
7. The mock's `golive_mode` default was `off` (drift); it now matches the registry (`shadow`).
8. Guides seed: the YouTube symptom now names *Also watch YouTube*, its fact is `golive_youtube`; the
   modmail guide's `modmail_enabled` fact is gone. A guide staff edited on the site keeps its old ref and
   shows the *no such setting* refusal for it.

## 8. What was verified on the local mock (fresh, port 8823, nonce `som-1`, Chrome)

- Settings page: all 12 three-way mode segments drawn there (structure backup, pb feed, brackets, points, raid trains, applications, automod, birthdays, events, go-live, honeypot, marathon) read **on · test · off**; `tempvoice_mode` reads **on · staff
  only · off**; no button, option, pill or chip says *shadow*; none of the nine retired keys appears;
  `golive_youtube` does.
- Go-live page strip: *Go-live announcements* on/**test**/off, *Also watch YouTube* On/Off, *Ping roles*;
  no YouTube-mode or Spotlight switch; no retired key in the page. Pressing Off then On on *Also watch
  YouTube* saved `false` then `true` and said *Also watch YouTube is now off/on.*
- Personal bests page: `pb_feed_mode` reads on/test/off; 55 pb keys drawn, neither retired one.
- Dry run — §3.
