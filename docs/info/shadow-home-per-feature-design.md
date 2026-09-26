# A rehearsal home per feature, and a marathon notice with the detail and the control staff need

> 🔨 **2026-09-25 22:xx — §E's notice now waits for the schedule, branch `marathon-notice-when` (BUILT, NOT merged):** the SAME embed + rows + People… (`send_added_notice`), through the same `_send_staff` (forum post under `marathon_notice_home = events`, staff channel, or the shadow home), posts on the first read that finds runs while `marathon_feed_notice_when = published` (default); `added` posts at add as §E shipped. `marathon.notice_posted` gains `because`. [`marathon-feeds-design.md`](marathon-feeds-design.md)'s top line has the rules.
>
> ✅ **2026-09-25 — LIVE as v166 19:30** (merge `0fecffa9`; release commit `b06d4f1d`; boot `database ready` 02:30:22Z, `logged in` 02:30:27Z, no Traceback, `/health` 65 ms — `deploys.log`'s v166 line). Set through the site at 19:3x by the conductor: `shadow_channel_id` → #blackbloc-logs, `frontdoor_shadow_channel_id` + `posts_shadow_channel_id` → #welcome-test (each answered 200 and read back — not re-read by the docs ritual). No rehearsal copy seen in its new home yet; sweeps `SH-a`…`SH-c` are the owner's.
>
> 🔨 **2026-09-25 — BUILT on branch `shadow-home-per-feature`, NOT merged, NOT deployed.** Six keys, not eleven (Deviation 1); §E covers the feed-added notice (Deviation 8). No live values set. See `## Deviations` and `## What was NOT verified` at the foot.

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **DESIGN (Fable, 2026-09-25 17:0x Phoenix),
> dispatched to Opus as branch `shadow-home-per-feature`** off `main` `0374f5a5` (v165 live; `marathon-ux` merged, not
> deployed — this rides with it as v166). **Last verified: 2026-09-25 17:0x** against that `main`: `black_bloc/shadow.py`
> — `REHEARSAL_KEY = "shadow_channel_id"` `:13`, `home_id(bot, guild)` `:36`, `channel_id(bot, guild, *, log_key)` `:41`
> (the rehearsal home, else the log channel), `channel_ids` `:55`, `channel_of` `:71`, `note_line(bot, guild,
> channel_words)` `:99`; the callers, by grep: `cogs/community/frontdoor.py` (`shadow.channel_id` ×2, `note_line` ×2),
> `cogs/moderation/modmail.py` (×1, ×2), `polls.py` (`channel_id`, `channel_ids`), `posts.py` (`shadow_home.channel_id(…,
> log_key=…)`), `minutes.py` / `minutes_session.py`, `cogs/community/birthdays.py` (×2 + note), `cogs/content/spotlight.py`
> (×2 + `channel_of` ×2 + note ×2), `cogs/content/marathon.py` (×2 + `channel_of` ×3 + note ×2), `preview.py` (note).
> Go-live's own shadow path lives in `cogs/content/golive.py` (check how it reads the home — the same key through its
> own name, or `shadow`). Live values (operator read 14:4x): `shadow_channel_id` = `#welcome-test`
> (1550284332365783091), `log_channel_id` = `#blackbloc-logs`, `frontdoor_mode` shadow aimed at `#welcome`,
> `marathon_mode` shadow. Settings namespaces: applications, automod, birthday, chat, core, cost, emoji, events, golive,
> guides, hide, honeypot, logs, marathon, memory, modmail, pings, poll, posts, raidtrain, request, rolemenu, tempvoice,
> voice, youtube. ⚠️ Secret NAMES only.

## The ask, verbatim (owner, 2026-09-25 17:0x Phoenix)

*"you posted the rehersal stuff in the welcome test, should have gone to lackblocl logs"* → offered (a) move every
rehearsal or (b) marathons only → *"for now make post go to welcome test, and everything else go to logs channel"*.

**Read as:** the front door's welcome POST keeps rehearsing in `#welcome-test` (it is aimed at `#welcome`, and seeing
it beside the real thing is the point); every other feature's rehearsal copies go to `#blackbloc-logs`. One global
home cannot say that, so every feature gets an OVERRIDE, blank meaning *the global one*.

## A. The model — one override key per feature that rehearses, read by the one helper

- `black_bloc/shadow.py` gains `feature: str | None = None` on `home_id`, `channel_id`, `channel_ids` and `note_line`
  (and `channel_of` if it needs the home to pick): with a feature, the helper reads **`<namespace>_shadow_channel_id`**
  first and falls back to `shadow_channel_id`; the note line names the real target as today. One place decides,
  never a caller.
- **The keys**, type `channel`, default blank, one per feature that rehearses (the callers above + go-live):
  `frontdoor_shadow_channel_id` (namespace: whatever the front door's keys use — `frontdoor_*` sits in `core`? check
  `namespace_of` and put it where `frontdoor_mode` lives), `posts_shadow_channel_id`, `golive_shadow_channel_id` (covers
  spotlight, which is golive's), `marathon_shadow_channel_id`, `poll_shadow_channel_id`, `birthday_shadow_channel_id`,
  `modmail_shadow_channel_id`, `tempvoice_shadow_channel_id`, `honeypot_shadow_channel_id`, `automod_shadow_channel_id`,
  `minutes` (namespace `voice`? put it beside `minutes_channel_id`). Help text on each: *Where this feature's rehearsal
  copies go while it is in shadow — blank means `shadow_channel_id`.* Registry + mock + labels + each feature's
  settings drawer on its page (`placeSettings` or the namespace drawer) + the KI-36 join fixture where the namespace has
  one. The global `shadow_channel_id`'s help gains one sentence: *A feature's own `…_shadow_channel_id` wins over this.*
- Every caller passes its feature word. `preview.py`'s note line gets the feature the preview is of, if it knows it,
  else none.
- ⚠️ **No live values are set by the build.** After the deploy the CONDUCTOR sets, through the site: `shadow_channel_id`
  → `#blackbloc-logs`, `frontdoor_shadow_channel_id` → `#welcome-test` — the owner's exact state. Say in Deviations
  that a guard-era `TEST_MODE` path (`guard.allows_channel`) is untouched.

## B. Doors

The Settings page (every key lands in its feature's drawer) and `/settings` (the channel keys are already settable
there — confirm the new ones appear in the picker's group). No new panel moves.

## C. Logging

Every existing `*.would_*` / `*_shadow` row gains `shadow_home` (the channel id actually used) so a reader can tell
which home a rehearsal went to. No new kinds.

## D. Tests, docs, gate

`tests/test_shadow.py` (the override wins, blank falls back, the note line unchanged, `channel_ids` includes the
override), one test per caller file asserting the feature word is passed (a rehearsal post lands in the override when
set — the fakes already capture channel ids), `tests/test_settings_store.py` (the keys, types, defaults, namespaces),
`tests/api/test_contract.py`, the key count guards, the join fixtures. Both `pytest -n 8` orders, `ruff`, ES parse,
node tests, `check.mjs` on a port of the builder's own. Docs: `code-notes.md`; this doc's foot; `architecture.md`
(the keys); `docs/info/README.md` (one row); `docs/info/cutover-plan.md` one dated line (the shadow home is per
feature now); `sweeps.md` rows `SH-a…` (a: set `frontdoor_shadow_channel_id` and `shadow_channel_id` as above → the
next front-door rehearsal lands in #welcome-test and the next marathon notice in #blackbloc-logs; b: blank the front
door's → it follows the global). NOT `TODO.md` / `DONE.md` / `deploys.log` / `KNOWN_ISSUES.md`. No schema.

## E. The marathon notice — detail and control, not two buttons (owner, 17:0x: *"also pause it and remove it, thats not enough control over the schedule or enough detail"*)

The feed's *added* notice (and the next-event / suggestion notices, same shape) today is one sentence with **Pause it** /
**Remove it**. It becomes:

- **An embed** (the same construct the go-live card uses) titled with the marathon's name, and fields: **When** (the
  schedule's start – end as `<t:…:f>`, or *dates not published yet*), **Read from** (the source words + the schedule
  link), **Channel** (the channel row it airs on, as a link), **Schedule** (the reading line: *read 2 min ago · next in
  28 min · 11 runs · 3 BaF* or *not published yet — the tracker answers 404; read again in 30 min*), **Event** (the mode
  word: *No event* / *One event for the marathon* / *An event per BaF run* / *Both*, and *Event #N — approved* when one
  exists), **Found by** (the feed) — every label a constant, every value from the row (`marathon_feed_added_template`
  stays the text above the embed).
- **Row 1 — the decisions:** **Pause it** / **Remove it** (as today, persistent, staff-gated) and **Read it now**
  (re-read the schedule, then EDIT the notice's embed with the fresh reading — the one place the schedule's detail
  updates in Discord without the panel).
- **Row 2 — the event select:** a persistent `Select` *Event: none / marathon / runs / both* (`custom_id`
  `marathon:feed:<feed>:<ref>:mode`) that sets the marathon's `event_mode` (§A of the event-modes design, the same
  function the site uses) and edits the embed's Event field.
- **Row 3 — everything else:** **Manage…** opens the SAME marathon card `/event` ▸ Marathons… shows for that marathon,
  ephemeral to the presser (the run pick, Who is who, the channel, the interval, Refresh the board, the board's pin) —
  full control without a second copy of the moves — and **Open on the site** (a link button to `events.html#marathon-<id>`).
- After Remove it the embed stays with a struck title and the buttons are removed, as today. Every button and the
  select survive a restart (KI-20, the `DynamicItem` template the feeds build used).
- Tests: the notice's embed fields from a fixture row (published / unpublished / with an event); Read it now edits the
  embed; the select sets the mode and edits; Manage… opens the card for staff and refuses a member in words; the
  custom ids round-trip through `from_custom_id`. Sweeps `SH-c`: a feed-added notice in the rehearsal home shows the
  six fields and the three rows.

## Deviations

*(the build agent, 2026-09-25, branch `shadow-home-per-feature`, commits `a1d33aaf` → `6b698f18` + docs)*

1. **Six keys, not eleven.** Built: `frontdoor_shadow_channel_id` (namespace **modmail**), `posts_shadow_channel_id`
   (**posts**), `golive_shadow_channel_id` (**golive**), `marathon_shadow_channel_id` (**marathon**),
   `poll_shadow_channel_id` (**poll**), `birthday_shadow_channel_id` (**birthday**) — `channel`, default blank. NOT
   built, because nothing would read them: **modmail** (the Open a ticket button has no mode of its own — *"in shadow
   it follows the door's"*, `frontdoor.py:panel_follows_the_door` — so its rehearsal copy now lands in the FRONT DOOR's
   home, keeping *one door per channel holds in the rehearsal home*); **minutes** (modes are `off`/`on` only; the home is
   read solely by `minutes.landing` under the retired TEST_MODE guard, which would refuse any other channel anyway);
   **tempvoice / honeypot / automod** (their shadow hides a lobby or writes log rows — none posts a copy anywhere).
   A key that changes nothing would be a lying Settings row.
2. **Check — the front door's namespace:** `frontdoor_*` is `NAMESPACE_OVERRIDE`'d onto **modmail**, so the new key is
   too (`test_contract.py::test_the_mock_groups_a_key_the_way_the_registry_does` holds the mock to it). The key is
   named by the FEATURE word (`frontdoor_`), not the namespace (`modmail_`): `shadow.feature_key(feature)`.
3. **Check — go-live's own shadow path:** `cogs/content/golive.py` posts NOTHING in shadow (`PostResult(reason=
   "shadow")`) and never read the home, so `golive_shadow_channel_id` serves **spotlights** only (its help says so).
4. **Check — minutes:** see 1; no key, `minutes.py` untouched.
5. **`note_line` takes no `feature`,** and `preview.py` is untouched: the note's words are the rehearsal note with the
   REAL target — they never depended on the home. `channel_of` needed none either.
6. **`shadow_home` rides only on rows where a home was actually used:** `frontdoor.posted_shadow` / `updated_shadow`
   / `would_post` (both), `modmail.panel_posted_shadow` / `panel_updated_shadow` / `would_post_panel` (both),
   `post.would_post` / `shadow_posted` / `shadow_updated` (shadow only), `poll.opened_shadow` / `poll.would_open`
   (rehearsing only), `birthday.would_announce` (rehearsed only), `golive.would_spotlight_announce` /
   `would_channel_announce`, `marathon.would_post_board` / `would_refresh_board` / `would_shout` / `would_remind` /
   `would_suggest_next` / `would_feed_add` / `would_feed_suggest`. NOT on would-rows that post nothing
   (`honeypot.would_ban`, `event.would_*`, `automod.would_*`, `golive.would_announce`, role rows) nor on take-down rows.
7. **`guard.allows_channel` / `teach_guard` untouched** (as the design asked): only the GLOBAL key widens a TEST_MODE
   guard, so under TEST_MODE a feature home that differs from `shadow_channel_id` is refused and the feature says so
   in its existing words. Production runs with no guard (`TEST_MODE=false`).
8. **§E covers the feed-ADDED notice only.** The feed SUGGEST notice and the marathon next-event notice keep their one
   row (**Add it / Not this one**): they describe a candidate that is not a marathon yet, so Pause/Remove/Read/Event/
   Manage… have no row to act on. Their rehearsals do follow `marathon_shadow_channel_id`.
9. **The new button labels are constants** (`mf.NOTICE_READ_LABEL`, `NOTICE_MANAGE_LABEL`, `NOTICE_SITE_LABEL`, the
   select's placeholder), like the shipped *Pause it* / *Remove it* — the brief made the embed's field LABELS constants;
   under the every-word-editable rule these button words are a candidate follow-up, not settings keys yet.
10. **Pause it still folds the notice** (a line, rows removed) exactly as before; the design said so only of Remove it.
    Resume lives on Manage… / the site.
11. **Manage…** is sent as an ephemeral FOLLOWUP (every notice press is deferred ephemeral first), with `view.message`
    set, so its moves edit that card and never the notice.
12. **The persistent select is `NoticeModePick`, not `FeedModePick`** — that name was already the feed card's
    (ephemeral, per-feed) select. Registered beside `FeedButton` in `Marathons.cog_load`.
13. **Commits:** the notice's embed, rows AND Manage… landed as one commit (`6b698f18`) — the view is one object.
14. ⚠️ **For the conductor — "post" may mean the POSTS feature.** The owner's *"make post go to welcome test"* was read
    (by the design) as the front door. The front door FOLLOWS the welcome post (`frontdoor_follows_post` = welcome) and
    its rehearsal checks for that post's rehearsal copy IN THE DOOR'S HOME (`posted.overtaken_by`). If `posts_mode` is
    shadow and posts rehearse in #blackbloc-logs while the door rehearses in #welcome-test, the "rules post, then the
    door under it" pairing no longer shares one channel. Setting `posts_shadow_channel_id` → #welcome-test as well keeps
    it. Not decided here — no live values were set.

## What was NOT verified

- **Nothing met live Discord.** No rehearsal was posted to a real channel; the notice's embed, its three rows, the
  select and Manage… were exercised only through the test fakes. Discord's own rendering of `<t:…:f>`, a link button
  beside Manage… on row 2, and an embed on a FORUM post (`open_notice_post(embed=)`) are unseen.
- **A restart with a notice already up** — proved only as far as registration (`cog_load` adds `FeedButton` AND
  `NoticeModePick`) and every custom id round-tripping through `from_custom_id`; no gateway re-dispatch was run.
- **No browser rendered a page.** The Settings page drawers, the Posts page's four-key drawer, the Go-live page's
  Spotlighted channels drawer and the Modmail page's door line were checked by the node fixture / mock `check.mjs`
  only. `/settings`'s group picker was not opened in Discord — the keys' namespaces are asserted in
  `tests/test_settings_store.py`.
- **Read it now against the real GDQ tracker / horaro** — only the fake schedule client.
- **TEST_MODE** (a guard installed) with a feature home set — reasoned (Deviation 7), one modmail test only.

