# The Posts page's one switch — `posts_mode` off/on for posts, stickies and weekly questions

> **Audience:** the conductor (merge + deploy), reviewers, and later sessions. **Status:** TRACKED ·
> 🔨 **BUILT on branch `posts-one-switch`** (off `main` `7e4f4286`, v241), **NOT merged, NOT deployed**.
> **Last verified: 2026-10-20 00:3x Phoenix** — measured on the branch: `pytest -n auto` 13,503 passed +
> 1 skipped, `ruff check .` clean, `node site/mock/check.mjs` ok against a FRESH mock (nonce
> `posts-switch-4`: 28 pages, 375 routes, 360 core settings), registry `len(KEY_TYPES)` 1238, the
> mock's `/api/settings` 1238 keys; the Posts, Settings and Polls pages exercised on the local mock in
> Chrome. ⚠️ **NOT verified:** anything in Discord (no button pressed, the bot not booted against a
> real guild), the migration against the live database (it ran against a fixture that mirrors the
> rows the switch audit read live), phone width.

Owner decisions 2026-10-19, the proposal sheet ticked from
[`switch-audit-2026-10-19.md`](switch-audit-2026-10-19.md): **p1a, p1d, p1e, p1f, i1, i2, p3a (front
door and polls), p4f, p4i, p4j** — the audit's P1 slice 2 plus P3(a). Owner, verbatim: *"on off
shadow should be one button for everything in the post page umbrella i think to keep permissions
simple"*. Slice 1 (Post to test for questions and stickies, `rehearsal_note` retired) is v241.

## 1. Before and after

| Switch | Before (v241) | After this build |
|---|---|---|
| `posts_mode` | off / shadow / on, default shadow; places posts only | **off / on, default on**; places posts, every sticky and the weekly question; off hides `/posts`, `/sticky`, `/questions` |
| `sticky_mode` | off / shadow / on; a sticky of a feature-owned post followed that feature's mode instead | **retired** — read as `posts_mode` |
| `question_mode` | off / shadow / on | **retired** — read as `posts_mode` |
| `points_mode` | decided where the leaderboard sticky and the top-places post went | **whether runs count only** (see §4) |
| `frontdoor_mode` | off / shadow / on | **off / on**; a carried door goes where its post goes |
| `poll_mode` | off / shadow / on | **off / on**; polls get Post to test |
| `posts_shadow_channel_id` | posts' rehearsal home | **the one rehearsal home** for Post to test of posts, stickies and questions |
| `sticky_shadow_channel_id`, `question_shadow_channel_id` | their own homes (#post-test live) | **retired**, folded into `posts_shadow_channel_id` (also #post-test live, so nothing moves) |
| `frontdoor_shadow_channel_id`, `frontdoor_shadow_message_id`, `frontdoor_shadow_hash` | the door's rehearsal home and copy | **retired** (p4i) |
| `poll_shadow_channel_id`, `poll_shadow_note` | polls' rehearsal home and line | **retired** (p4f); poll Post to test goes to `shadow_channel_id` |
| `modmail_panel_shadow_message_id` / `_hash` | the ticket button's rehearsal copy | **kept** — §6 |
| `/settings` mode list (`FEATURE_MODES`) | 25 | **24** (`sticky_mode` left `HIDDEN_WHEN_OFF`) |
| Registry keys | 1247 | **1238** (nine retired) |

Where each surface is now: the Posts page shows **one** switch, `posts_mode`, in its *Settings and
logs ▸ Settings* fold beside the one rehearsal home `posts_shadow_channel_id`; the top line reads the
state (*Posts are ON*) and, while off, the two notes (*Posts are off: …* and */posts, /sticky,
/questions are out of the server's command list until posts are on*). The sticky section lost its
mode segment; the weekly-questions fold lost `question_mode`. In Discord `/sticky` lost its mode
select and shows `**posts_mode** — on`; `/questions` shows the same line.

## 2. The migration (`black_bloc/posts_switch.py`)

Runs once per boot in `BlackBlocBot.setup_hook`, **after `store.load()` and before any cog loads**, so
no sticky Desk ever reads a rehearsing row under `posts_mode = on`. It follows the
`settings_store.carry_end_wording` pattern (raw reads of retired rows, one log row, idempotent), but
in `setup_hook` rather than a cog's boot pass because the Desk loads in `cog_load`. A failure is
logged (`posts switch: the boot migration failed…`) and never stops the boot; the Desk's existing
*held* rule (§5) is the safety net. No schema change.

Steps, per guild found in `settings` ∪ `sticky_messages`:

1. **Pause** every sticky row that is rehearsing — `paused = 0`, no trouble, a copy up, and that copy
   NOT in the sticky's own channel. `paused = 1`; `message_id` / `posted_channel_id` are **kept**.
   One `sticky.paused_by_migration` row each: `{channel_id, post_id, copy:{channel_id, message_id},
   before:"rehearsing", after:"paused", build}`.
2. **Map** stored mode values: `posts_mode` shadow → **on**; `frontdoor_mode` shadow → **off**;
   `poll_mode` shadow → **off** (fail safe: a door or a poll never reaches members because of the
   migration; both are `on` live, so nothing changes there).
3. **Delete** every stored row of the nine retired keys. One `settings.migrated` row naming the keys
   removed, their values and the mode maps.
4. Commit; the store re-reads. A second boot finds nothing and writes no row (tested twice).

`dry_run(db)` returns what `apply` would change and writes nothing.

**Dry run against the live-mirroring fixture** (`tests/test_posts_switch.py::live_mirror` — the
rows the audit read live 2026-10-19 ~18:27; the leaderboard copy's message id is a stand-in):

```json
[
  {
    "guild_id": 1073710702776299640,
    "pause": [
      {
        "channel_id": 1076003845232148580,
        "post_id": 2,
        "copy": {"channel_id": 1550284332365783091, "message_id": 1560200000000000001},
        "before": "rehearsing",
        "after": "paused"
      }
    ],
    "drop": {
      "frontdoor_shadow_channel_id": 1550284332365783091,
      "frontdoor_shadow_message_id": "1560105628234420427",
      "question_mode": "on",
      "question_shadow_channel_id": 1550284332365783091,
      "sticky_shadow_channel_id": 1550284332365783091
    },
    "modes": {}
  }
]
```

Exactly **one sticky to pause** (the leaderboard in #speed-and-pbs) and **five keys to drop**.
`sticky_mode` is not in the list because live it equals its default (shadow) and is assumed unstored;
if it is stored it is dropped too. `posts_mode` is already `on`, so no mode map fires.

**The rehearsing copy in #post-test stays** until staff act: the migration deletes nothing, and the
Desk now leaves a paused row's copy where it is (§5). **Resume** takes it down and posts the
leaderboard for real in #speed-and-pbs; **Remove** takes it down with the row; **Post to test**
sends a fresh copy and does not touch it. The stored `frontdoor_shadow_message_id`
(`1560105628234420427`, in #post-test) is forgotten, its message left alone — delete it by hand if it
is clutter.

## 3. What members and staff see differently the moment it ships

- **Members:** nothing at once. The welcome post (posts on) and the weekly question (on) are
  unchanged; the leaderboard sticky is paused, so no new message appears in #speed-and-pbs.
- ⚠️ **The next approved run that changes the top places posts a *Leaderboard update* in
  `points_channel_id` (#speed-and-pbs, `1076003845232148580` live)** — p1f: the top-places post
  follows `posts_mode` (on), no longer `points_mode` (shadow). `points_ping_role_id` is blank live,
  so it pings nobody. Before this build it went to #post-test.
- **Staff:** one switch on the Posts page; the leaderboard row reads **paused** with **Resume** and
  **Post to test**; the sticky and question mode controls are gone; the Settings page lists none of
  the nine keys; polls have **Post to test** (Discord preview, staff only; the site's create form);
  the modmail page's door card loses its shadow lines; `/settings` lists 24 modes.

## 4. What `points_mode` means now

| Value | Runs | Member DM about their run | Top-places post / leaderboard sticky / leaderboard block |
|---|---|---|---|
| off | every move refused | — | the block draws nothing; a sticky whose post is ONLY the block stops at its next move with *Its post has no words and no block to show* |
| **shadow** | taken and approved for real | **none** (`points.would_dm`) | placed by `posts_mode` |
| on | taken and approved | sent | placed by `posts_mode` |

`points_shadow_channel_id` has **no reader** after this build (its help says so); it is a removal
candidate for the next slice — not retired here because the owner's sheet did not tick it.

## 5. Behaviour the Desk changed

- `owner_rule` is one line: `(posts mode, "posts")`. `post_blocks.owner_of` and `BlockKind.owner`
  are gone. Every shadow placement branch in the Desk went (`_target` / `_wanted` / `_own_home` /
  `_home_is_back`, `REHEARSED`, `OWN_HOME`, the home troubles), with `set_mode` and `/sticky`'s mode
  select.
- **A paused row's copy is never moved by a settle** (`_misplaced` is false for paused rows). Before,
  a paused copy that would not delete was retried at the next settle; now it waits for Resume or
  Remove, which is what `PAUSED_COPY_LEFT` already told staff to do.
- The *held* rule stays: a running row with a copy away from its own channel is taken down and held
  for Post it — the net under a migration that failed or a rehearsal it missed.

## 6. The judgement call (item 6): the ticket button's rehearsal keys are KEPT

`modmail_panel_shadow_message_id` / `_hash` are read by `cogs/moderation/modmail.py`
(`rehearse_panel`, `drop_panel_rehearsal`, `take_panel_down`, `_repanel`) and
`cogs/community/frontdoor.py`. The rehearsal path had **two** triggers: the door's shadow mode
(`panel_follows_the_door`, retired with the door's shadow) **and** `TEST_MODE`'s guard refusing the
real channel. The second is a life of its own — the guard code stays for future rehearsals — so the
keys stay, the door-shadow trigger and `hide_rehearsed_ticket_button` went, and the copy's home is
now `shadow_channel_id` (the retired `frontdoor_shadow_channel_id` was its home). Live both keys are
blank. Asymmetry recorded: under `TEST_MODE` the ticket button still rehearses; the **front door no
longer does** — it refuses in words (`DOOR_GUARDED` names Post to test) and writes a would-row.

## 7. Item 8 — the 1247 / 1246 gap

Measured: registry `len(KEY_TYPES)` **1247** at `main`; the **live** `/api/settings` (operator token,
2026-10-19 ~23:3x) **1247** — no gap there; the **mock's** `/api/settings` **1246**: it lacked
`minutes_log_level` because `server.mjs` `LOG_LEVEL_FEATURES` had no `minutes` row. A defect — fixed.
After this build: registry **1238**, mock **1238**, contract `core_keys` 360.

## 8. Deviations

1. Migration runs in `setup_hook`, not a cog boot pass (§2) — the Desk would otherwise settle first.
2. `frontdoor_mode` / `poll_mode` shadow map to **off**, not on (fail safe; no live effect).
3. `posts_mode` default is **on** (was shadow); an unknown stored value reads as **off**.
4. Post to test on a `/posts` card is now hidden while posts are **off** (it only refused there).
5. Poll Post to test goes to `shadow_channel_id` (blank → guard → log channel), not
   `posts_shadow_channel_id` — polls are not in the Posts umbrella; staff-only on the Discord preview.
6. The poll copy carries no vote buttons (a panel poll is the card alone; a native poll is a real
   Discord poll nobody counts) and pings nobody.
7. The `poll_card` preview renderer (whose only key was `poll_shadow_note`) is removed.
8. Dead log kinds unclassified: `post.shadow_posted`, `post.shadow_updated`,
   `frontdoor.posted_shadow` / `updated_shadow` / `taken_down_shadow`, `poll.opened_shadow`,
   `sticky.mode`. New: `sticky.paused_by_migration`, `settings.migrated`, `poll.rehearsed`.
9. `/api/posts` gained `commands_hidden` (the switch's commands currently out of the list) and a
   second note while off; the mock mirrors it. There is no command-visibility route of its own.
10. Guides seed: the polls guide lost its *shadow* fault and the `poll_shadow_note` fact.
11. Tests: about 90 tests of retired shadow behaviour deleted (counted per file in the build); the rest re-pointed at `posts_mode`; new: `tests/test_posts_switch.py`, `tests/test_polls_rehearse.py`.

## 9. Rollback

Redeploy **v241** (`1628212a`) and restore the pre-deploy snapshot ([`../access/deploy.md`](../access/deploy.md)).
The snapshot matters: the migration deletes the retired rows and pauses the leaderboard row, and v241
code would read the missing keys as their defaults (`sticky_mode` shadow, `question_mode` shadow —
⚠️ the weekly question would rehearse instead of posting). Without the snapshot, after a v241
redeploy set `question_mode` on and `question_shadow_channel_id` / `sticky_shadow_channel_id` /
`frontdoor_shadow_channel_id` to #post-test (`1550284332365783091`) again, and Resume or leave the
leaderboard paused.

## 10. Incident during the build (2026-10-19 ~23:4x Phoenix)

An import sweep (`pkgutil.walk_packages` over `black_bloc`) imported `black_bloc/__main__.py`, which
ran the bot with the local `.env` token: it logged in over HTTP, ran `setup_hook` and **synced this
branch's command tree to `DEV_GUILD_ID` (the real server) with nothing hidden**, then crashed in
`install_visibility` before the gateway connected. Effect until the live bot next re-syncs (its next
boot, i.e. the next deploy): commands whose feature is off live (`/rolemenu`, `/minutes`, …) may show
in the server's command list. No command definition differs from v241. Lesson: never import
`black_bloc.__main__` (or `app`) in a sweep.
