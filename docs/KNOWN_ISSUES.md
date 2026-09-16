# Black Bloc — Known Issues, Waivers & Exceptions

> **Audience:** Claude sessions and the owner. **Status:** TRACKED (owner,
> 2026-08-31 — was local-only until then).
> Last verified: **2026-09-11 10:55** — **KI-26 ADDED** (the xdist deploy-gate hang, `WATCHING`, 5 hangs v94–v100, 0 of 8 since v103); 10:50 — **KI-25 ADDED** (Discord-only sign-in, `WAIVED` by the owner: "A discord is fine"); **08:33** — every OPEN entry was re-read against the repo at
> `main` `1d090e5` (**v108 LIVE**). What moved:
> **KI-24 is now LIVE, not just closed on a branch** — it merged as `689eff5` and shipped
> **v97** (`aa44e3b`, 2026-09-06 13:52; `deploys.log:96`); `black_bloc/loops.py` exists and
> `wait_ready` has **27** call sites, with the only bare `bot.wait_until_ready()` left in the
> helper itself. **KI-20's symptom list was two panels and is now eighteen** — measured:
> **18** `*_panel_minutes` keys in `settings_store.KEY_TYPES`, every one defaulting to **10**.
> **KI-10's "15 cogs" is the 2026-09-03 boot line** and is left as the historical reading; the
> tree holds **19** cogs today. Re-confirmed unchanged: KI-22 (`mod.purged` / `mod.purge_failed`
> are still bare literals at `cogs/moderation/modcmds.py:874,895` and there is still **no**
> `POST /api/mod/purge`), KI-2 (`bot.py:setup_hook` still calls `sync_dev_guild` unconditionally),
> KI-11/KI-13 (`youtube_mode` default `off`, `youtube_poll_minutes` default **10**,
> `FEED_ATTEMPTS` **4**), KI-14 (`chat_memory_mode` default `off`), KI-6 (`SESSION_TTL_SECONDS`
> still 7 d). ⚠️ **NOT re-tested:** no entry's symptom was REPRODUCED — this was a read of the
> code, not a run; nothing met live Discord, no browser rendered a page, and the two thresholds
> flagged under KI-6 (">1 site user", ">1 person with `/data` access") are **still unmeasured and
> still waiting on the owner**. Before that,
> **2026-09-06 — KI-24 CLOSED** on branch `loop-guard`: the fourteen `before_loop`s
> now go through `black_bloc/loops.py:wait_ready`, the restart is proved against a real
> `tasks.Loop`, and two AST guards keep the helper the only copy — `info/loop-guard-design.md`
> carries the design and its Deviations. ⚠️ Verified by the suite in a worktree only: not merged,
> not deployed, and never exercised against live Discord (that caveat is **superseded** by the
> v97 line above). Nothing else here was re-checked.
> Before that, **2026-09-05 22:10 — KI-24 ADDED** by ENGINEERING SWEEP 3 on
> `worktree-agent-ab52a6d7c53bc1ecb`. It was found through a measured deploy-gate symptom that
> is now **FIXED in the same branch**: `pytest -q -n 4` off `main` at `6af0ba0` (v92) was green
> at 5188 passed while writing **1716 stderr lines / 143 tracebacks across 14 loops in 13
> cogs**; bisected to one fixture (`tests/test_selftest_panels.py::live`) and taken to **0
> stderr lines**, 5188 still passing. What the entry keeps is the PRODUCTION half the bisect
> exposed — that a `before_loop` failure bypasses `@loop.error` — read from the installed
> `discord/ext/tasks/__init__.py` (line 210 outside the try on 217, error dispatch on 278),
> **never from a running bot**. Nothing else was re-checked then. Before that, **2026-09-05 19:45 — KI-23 CLOSED and moved WHOLE to [`DONE.md`](DONE.md)** ("Personality
> pool, both halves"): both numbers it named arrived — GABI's `/api/health` answers
> `gabi_personality_pool_version: 1` (deployed by the owner, `755cfd54`) and `sync_personality_pool.py`
> exits 0 (`synced_from: catalog-platform@de4ef63`); Black Bloc v91 `604226f` compares her roster by name.
> Nothing else was re-checked then. Before that, **2026-09-05 — KI-23 ADDED** by the personality-pool
> build (Black Bloc half): nothing was verifying that the two bots' rosters agreed until the GABI half landed. Before that, **2026-09-05 — KI-21 RESOLVED and moved WHOLE to [`DONE.md`](DONE.md)** by the
> engineering sweep on `worktree-agent-accb69989b295c889`: `PUT /api/settings/{key}` hands
> `automod_mode`, `honeypot_mode` and `honeypot_exempt_role_ids` to the cog's own move, so the
> website reads the same verdict the Discord panel does. ⚠️ Fixed in tests only — the branch has
> not been merged, deployed, or exercised against the live dashboard. Before that, **2026-09-05 —
> KI-21 widened at the v79 (honeypot panel) landing: the same generic
> route bypasses `/honeypot`'s arming refusal and rewrites its exempt list with no log row; from the
> build's read of the code, not an incident.** Before that, **2026-09-04 — KI-21 added at the v74 (automod
> panel) landing from the design doc's
> read of `api/settings_api.py`, not from an incident; not exercised against the live site.** Before
> that, **2026-09-03 — KI-20 added by the requests fourth pass build, from
> reading its own code (the panel's View has a real timeout, not a persistent one)
> rather than an incident; not run against live Discord.** Before that, **2026-09-02
> — KI-17 and KI-18 added by the Phase 19 (applications)
> build; KI-15 and KI-16 by the Phase 18 (F19, raid trains) build, from reading its own
> code rather than from an incident; KI-14 by the Phase 17 build from its own §J
> measurement (two leaked third-person threads in run 1, none in run 2 after the fix).
> All five describe code that has never met live Discord, built in parallel, merged
> 17 → 18 → 19 and deployed `7b1c592` on 2026-09-03 with all three modes **off**. Before that,
> KI-11, KI-12 and KI-13 added from the Phase 16
> section-J measurements against the LIVE YouTube feed (30 timed requests, the
> response headers, and a real captured feed now kept as
> `tests/fixtures/youtube_feed.xml`); KI-10 added earlier the same day from a
> live Fly log line during the `d777f57` rolling deploy. Nothing else re-tested.**
> ⚠️ The three new entries describe a branch that has NEVER run against live
> Discord or a live YouTube API key. Before that, 2026-08-31 for the STATUS line only. ⚠️ **No entry below
> was re-tested then**, and two carry thresholds that may already have been
> crossed — see the note under KI-6. The dated history that follows is the
> 2026-08-27 reading: KI-9 added (anonymous poll votes are a per-poll hash, accepted); before that KI-8 added when the role-menu panels started
> following the mode (measured in tests only; no panel has ever been deleted
> against live Discord). Before that, KI-2 gained a second-sync note when command
> visibility landed (measured only in tests; no sync has been sent to Discord).
> Before that, KI-7 closed after the generic loop discovery
> landed (measured: seven loops, six cogs, `pytest -q` green). The other entries
> were written from reading the code, not from an incident, and were NOT
> re-checked today.
>
> **This file exists to stop the same non-bug being re-reported.** It holds
> things that ARE wrong, or look wrong, and are deliberately tolerated.
> Every entry: Symptom · Status · Why tolerated · What would change it.
>
> - Work in flight → [`TODO.md`](TODO.md)
> - Traps you fall INTO while working → [`info/gotchas.md`](info/gotchas.md)

## KI-27 — Guide wording and screenshots are edited on the WEBSITE only; there is no Discord door — `WAIVED`

**Symptom:** the "every decision configurable BOTH ways" rule (`CLAUDE.md`, checklist 33) has a
Discord half for every setting, but a guide's steps, faults, facts and pictures can only be changed
on `guides.html` (**Edit this guide**). Discord's half of the feature is `/help`'s guide links and
nothing more. The six `guides_*` KEYS are both ways as always.

**Status:** `WAIVED` — owner, 2026-09-16 06:5x, verbatim *"A"* (fork F-G1 in
[`info/guides-design.md`](info/guides-design.md) §G: (a) none, (b) a `/guides` staff panel).

**Why tolerated:** a guide is up to forty steps of long text plus a table and pictures; Discord's
modal holds five fields, so a Discord editor would be a modal per step with no way to reorder or
see the whole. The website exists for exactly this shape of edit (the same reason `bot_bio` is the
Settings page's). The rule is about DECISIONS; guide copy is CONTENT.

**What would change it:** a staffer asking for it **once** — then fork (b) as designed, a `/guides`
panel with **A guide…** → **A step…** → a modal, built on `panels.py`.

## KI-26 — `deploy.ps1` hangs mid-pytest with every xdist worker idle, roughly one run in four — `WATCHING`

**Symptom:** the deploy gate's `pytest -q -n auto` stops making progress — 33 idle pythons,
the log untouched for over a minute, CPU flat — at spawn (twice) or at 81–92 % of the run
(three times). Five times so far, measured off `deploys.log` 2026-09-11: the runs before **v94**
(10:42, detached, 92 %), **v97** (13:45, detached, 88 %), **v98** (14:09, foreground console, at
spawn), **v99** (19:52, 81 %) and **v100** (15:55, detached, 82 %) — 2026-09-06 and 2026-09-10.
(`gotchas.md` and the docs-pass finding said "v103 attempt 1"; the v103 line itself says *no hang*.) Not a failing test: the same commit passes
forward and under `BB_REVERSE=1` on the retry, in 26–30 s. The hung tree cannot be stopped from
the session; the owner kills it.

**Status:** `WATCHING` — filed 2026-09-11 10:55 from the docs-pass finding (c). The retry is in
[`info/gotchas.md`](info/gotchas.md) (*"`deploy.ps1` hangs mid-pytest…"*), which owns the
what-to-do; this entry owns the count.

**Why tolerated:** the retry has shipped every time and costs two minutes; nothing reaches Fly
until the gate passes, so a hang is lost time, never a bad deploy. Cause unestablished — the
pattern — detached runs and one foreground console run hung; every run through the PowerShell
tool with `*> file` (the ritual since v98) has passed, 0 of 7 — points at console stdout handling of
xdist workers rather than the suite.

**What would change it:** a sixth hang **on a PowerShell-tool `*> file` run** (none of the five was),
or the count passing **10** — then spend a session on it: run the gate under `-n auto -p no:cacheprovider`
with `PYTEST_DEBUG` and a worker log, and compare a hung run's `py-spy dump` against a live one.
Runs since v103: v103–v110 (eight) all passed the gate first time.

## KI-25 — Discord is the ONLY sign-in; the phase-8 Google SSO for the owner was never built — `WAIVED`

**Symptom:** phase 8 decision 3 (2026-08-26, [`info/phase8-design.md`](info/phase8-design.md))
planned two identity providers — Discord OAuth2 for staff and Google OAuth2 allow-listed to the
owner's account, linked by a `user_identities` table. Neither the Google flow nor the table exists
(`grep -ri google black_bloc/` finds only the YouTube Data API host). The owner signs in through
Discord like every staffer and gets owner rights because `api/auth.py:222` matches the guild's
`owner_id`.

**Status:** `WAIVED` — owner, 2026-09-11 10:50, verbatim *"A discord is fine"* (answer to the
docs-pass question, option A: drop it).

**Why tolerated:** every gate on the site is a Discord role, so a Google identity would grant no
permission the Discord one does not already carry; a second provider is a second login surface
and a second secret to hold. The one thing it would buy is a Discord-independent door if the
owner's Discord account were locked or Discord were down.

**What would change it:** the owner being locked out of Discord with something on the site that
cannot wait — that is the break-glass case. If it ever happens, the design is still written in
`phase8-design.md` decision 3; build it then, not before.

## KI-24 — (RESOLVED 2026-09-06, **LIVE v97**) A `before_loop` failure bypasses `@loop.error` — `CLOSED`

**Was:** all fourteen `before_loop`s awaited `bot.wait_until_ready()` bare, and discord.py 2.7.1
runs `before_loop` outside the `try` that dispatches to `error`, so a failure there killed the
loop with no restart and no `last_error`. **Now:** one helper, `black_bloc/loops.py:wait_ready`,
hands the exception to the loop's own `@loop.error` handler; two AST guards in
`tests/test_loops.py` keep it that way and a real `tasks.Loop` test proves the restart. The whole
design, what was measured, and what deviated from it:
[`info/loop-guard-design.md`](info/loop-guard-design.md).

✅ **Resolved and SHIPPED — merge `689eff5`, deployed as v97 (`aa44e3b`, 2026-09-06 13:52,
`deploys.log:96`)**, in the same deploy that took `OPERATOR_READ_TOKEN` live. Re-measured
2026-09-11: `black_bloc/loops.py` is present, `wait_ready` has **27** call sites across the
package, and the only bare `bot.wait_until_ready()` left in `black_bloc/` is the one inside the
helper (`loops.py:12`). ⚠️ Still never exercised against a real `before_loop` failure on the live
bot — the proof is the suite plus the AST guards, not an incident. Kept here rather than deleted
so the reasoning stays findable; nothing about it is open.

## KI-22 — `/purge`'s two log kinds cannot say which door made them — `ACCEPTED`

**Symptom.** Every other moderation kind is built with `kind_via` (`logkinds.py`), so the same
action taken from the dashboard is written `web.mod.<kind>` and the Logs page can label it
Via=Website. `mod.purged` and `mod.purge_failed` are built as bare string literals inside
`ModCommands.purge` and cannot. They are the last two mod kinds without it — measured while
writing `mod-panel-design.md`, and unchanged by the wave-4 build, which was scoped to how the
case record is READ and CORRECTED.

**Status:** `ACCEPTED`.

**Why tolerated.** `/purge` has **no web door**: there is no `POST /api/mod/purge`, so nothing
can currently write a `web.mod.purged` row, and nothing double-posts. The defect is latent, not
live. Adding `kind_via` now would be an edit inside the punishment path, which the panel build
deliberately left with a zero-line diff — that zero diff is the evidence the punishment path did
not move, and spending it on a kind nobody can emit twice is a poor trade.

**What would change it.** **One** — the moment a `POST /api/mod/purge` route is proposed. At that
point the two kinds get `kind_via` and a `via` parameter in the same commit as the route, and
`tests/test_logkinds.py`'s AST guard is what catches it if they do not.

✅ **Re-measured 2026-09-11 (v108):** unchanged in both halves — the two literals are still bare
at `black_bloc/cogs/moderation/modcmds.py:874` (`"mod.purge_failed"`) and `:895` (`"mod.purged"`),
and `grep` over `black_bloc/api/` finds **no** `POST /api/mod/purge`, so the defect is still
latent. The number stands.

## KI-14 — A memory note about a THIRD PERSON is prevented, not proved impossible — `ACCEPTED`

**Symptom.** `chat_memory.parse_distilled` is what stops a preference note
naming somebody other than the person whose profile it is (§D2-definition rule
1). It is three layers, all of them heuristics: the distil prompt says so; a
phrase list catches the obvious carriers (`said`, `told`, `according to`, `<@`,
the departure family); and `other_names(guild, user_id)` drops any note
containing another member's display name. None of them is a proof, and the last
one only works for a name the guild cache actually holds — a nickname the person
typed that no member wears would pass.

**Status.** `ACCEPTED` for the dark launch (`chat_memory_mode` ships **off**).

**Why tolerated.** The blast radius is one sentence, visible to one person, and
that person can read every note the bot holds about them and drop any of them —
`/memory` opens one panel with the lines numbered, a **Forget one of these…**
picker and **Forget everything**; §D2-definition rule 7 makes that panel the
enforcement of last resort. A note is also never a quote: the
six-word shingle check against the window text (`shingles`) means whatever leaks
is the model's paraphrase, not somebody's words. **Measured 2026-09-02, §J:** in
run 1 the model produced third-person threads twice in six attempts on a window
containing a third-person question; after the `OUTCOMES` fix all three run-2
attempts were dropped. There is no measurement of the rate against real
conversations — none have been distilled.

**What would change it.** Number: **one leaked note reported by a member**, or
**one note about a third person found by the owner in the DB**. At that point
the fix is not a longer phrase list — it is to stop keeping `threads` at all
(§I already excludes cross-person memory), since the note leaks measured so far
were all threads, never preferences.

## KI-15 — A raid-train slot keeps the Twitch name it was claimed with — `ACCEPTED`

**Symptom.** `raid_slots.twitch_login` is COPIED at claim time from
`golive_links`. A member who presses **Unlink** on `/golive`, or who re-links to a
different channel, keeps their slot and the lineup keeps naming the OLD login —
so the streamer before them may raid a channel that no longer belongs to
anybody. Nothing tells the organizer.

**Status.** `ACCEPTED` (Phase 18, §I). Measured only in the test suite; no raid
train has ever run against live Discord.

**Why tolerated.** The copy is deliberate: reading the link live would mean a
lineup that silently rewrites itself between the reminder DM and the hour it
describes, and a slot that empties itself when somebody unlinks for an unrelated
reason. A stale name is visible and fixable (`/raidtrain unassign` then claim
again); a lineup that changes under people is neither.

**What would change it.** **1 report** of a raid landing on a wrong channel.
The fix is a sweep step that re-reads `golive_links` for un-started slots and
logs `raidtrain.login_stale` rather than rewriting anything.

## KI-16 — Raid-train check-in sees only what go-live sees — `ACCEPTED`

**Symptom.** D9's check-in (`checked_in_at`, and the "the train moves" line in
the thread) reads `golive.open_sessions`. A slot holder whose Discord presence
is hidden and who is not Twitch-linked never has an open session, so they are
never marked live and the thread never says the train moved on — even though
they are streaming.

**Status.** `ACCEPTED` (Phase 18, §I). Test-suite evidence only.

**Why tolerated.** It is the same limit as F1 go-live, from the same source, and
the phase deliberately reuses that one signal rather than growing a second
detector. Nothing breaks: the lineup, the reminders and the raid order are all
unaffected — only the ✅ and the one thread line are missing.

**What would change it.** Whatever closes the go-live gap closes this one too
(Twitch EventSub with a public callback, or a `/raidtrain checkin` command a
holder runs by hand). Number: **1 report** of a train whose lineup showed nobody
checked in while it was visibly running.

## KI-19 — Log rows written before 2026-09-03 keep their retired kinds — `ACCEPTED`

**Symptom.** The double-post fix (owner report, 2026-09-03) stopped the routes
writing a second `web.<kind>` line, and eight kinds are now never written again:
`web.event.cancel`, `web.honeypot.ban`, `web.mod.apply`, `web.mod.rule`,
`web.modmail.close`, `web.poll.cancel`, `web.poll.end`, `web.tempvoice.forget`
(plus `web.mod.warn`/`timeout`/`untimeout`/`kick`/`ban`/`unban`). Rows already in
`action_log` keep them. They still render, still filter onto the right feature
page (`feature_of` reads the head, which is unchanged) and still classify as
routine — with **one exception**: `honeypot.ban` was removed from `ROUTINE`, and
`.ban` is an `IMPORTANT_SUFFIXES` entry, so historical `web.honeypot.ban` rows
now read as *important* rather than routine.

⚠️ **Four more joined them on 2026-09-05** (the modmail panel, Build A): the website's
`web.modmail.block`, `web.modmail.unblock`, `web.modmail.snippet` and
`web.modmail.snippet_remove` are now written as `web.modmail.blocked`, `.unblocked`,
`.snippet_saved` and `.snippet_removed`, so both doors spell the same act the same way.
The four old spellings were deleted from `logkinds.ROUTINE` in the same commit, because a
classification entry nothing emits is a table nobody maintains
(`tests/test_logkinds.py::test_no_classification_entry_is_dead`). Rows already in
`action_log` keep the old kinds and are now **unclassified**, which `is_important` reads as
*not important* — the same quiet they had as `ROUTINE` entries, so nothing on the Logs page
moves. ⚠️ The reverse is worth knowing: the NEW `web.modmail.blocked` and `.unblocked` are
**important**, where `web.modmail.block`/`.unblock` were routine — that is the
classification bug this rename fixes (blocking somebody was loud from Discord and quiet
from the website).

**Why tolerated.** Rewriting history in `action_log` is worse than a handful of
retired kind strings: the log is the audit trail, and a migration that edits it
destroys the thing it exists to prove. The one classification change moves a
honeypot ban from quiet to loud, which matches how the replacement kind
(`honeypot.banned`) classifies — so the old rows now agree with the new ones
rather than disagreeing.

**What would change it.** Nothing planned. Number: **1 report** of a stale kind
confusing somebody reading the Logs page — the fix would be a display alias, not
a migration.

## KI-20 — An ephemeral panel's buttons die on a bot restart — `WATCHING`

**Symptom.** Every panel built on `black_bloc/panels.py` — ⚠️ **measured 2026-09-11 there are
now EIGHTEEN of them, not the two this entry was written about**: `applications`, `automod`,
`birthday`, `chat`, `event`, `golive`, `honeypot`, `memory`, `mod`, `modmail`, `pings`, `poll`,
`raidtrain`, `request`, `rolemenu`, `settings`, `voice`, `youtube` (one `<feature>_panel_minutes`
key each in `settings_store.KEY_TYPES`, **every one defaulting to 10**). It was `/request`
(`requests-panel-design.md`) and, from 2026-09-03, `/poll`
(`polls-panel-design.md`) alone when this was written. Each
opens an ephemeral `discord.ui.View` with a real
timeout (`<feature>_panel_minutes`), not a persistent `View(timeout=None)` re-registered
with `bot.add_view()` on `cog_load` (the pattern `TempVoicePanel` uses). If the
bot restarts while a member's panel or request card is still open, every button
and select on it answers Discord's own "This interaction failed" — the view's
Python object is gone, and nothing on the message itself says so. ⚠️ **A second way the same footer goes
missing, and this one is a setting anybody can walk into:** `<feature>_panel_minutes`
of **15 or more** loses the "this panel has gone quiet" footer entirely, because
the footer is written through a Discord interaction token that expires 15 minutes
after the click that made it — the buttons simply stop answering with nothing to
explain why. All **eighteen** such keys ship at **10** for exactly this reason
(re-measured 2026-09-11: `SettingsStore.default` returns 10 for every one) and each one's own
help text in `settings_store.py` `KEY_HELP` carries the warning; the value is deliberately NOT
clamped.

**Why tolerated.** A panel is a moment, not a post: it exists for the seconds a
member spends filing or a staffer spends triaging, then it is gone (its own
timeout disables it and says "run /request again"). Restarts are rare and short,
and the only other affected surface today with a real timeout, `MemberPickView`
in temp voice, has carried the same limitation since Phase 2 with no report.

**What would change it.** A persistent `DynamicItem`-based panel (`custom_id`
carrying the request id, so a restart can re-derive an item's target) if staff
ask for it — the same shape `TempVoicePanel`'s own buttons already use, minus
the request-card state that currently lives only in the View's Python object.
Number: **0 reports** so far; nothing planned.

## KI-18 — Editing a question changes the form, never the answers already sent — `ACCEPTED`

**Symptom.** An application stores its answers as a snapshot of `{label, answer}` pairs
(`black_bloc/applications.py:answers_json`). Rewording question 3, or removing it, changes
what the NEXT applicant is asked and leaves every card already on the record exactly as it
was — so two cards side by side can show different questions.

**Status.** `ACCEPTED` — chosen, not discovered (Phase 19 §A).

**Why tolerated.** The alternative is worse in both directions: joining answers to the
live question rows would silently relabel somebody's answer with a question they were
never asked, and refusing to edit a question once anybody has applied would freeze the
form at its first draft. A card is a record of what was asked and what was said.

**What would change it.** Staff reporting confusion between two cards. The fix then is a
version number on the question set and a "asked as it stood on <date>" line on the card,
not live joins.

## KI-17 — Black Bloc cannot confirm the twitch.tv Team invite was ever sent — `ACCEPTED`

**Symptom.** Approving a Twitch Team application grants the Discord role and names the
person who has to send the twitch.tv invite (`owner` + `next_step` on the form), but the
invite itself is a human clicking a button on twitch.tv. Black Bloc has no way to see
whether it was sent, accepted, or forgotten — so an application can read **approved** here
while the person is not on the Team at all.

**Status.** `ACCEPTED` — measured at design time, 2026-09-02: Twitch publishes **no Teams
API**. Only the Team owner can add members, and only from twitch.tv.

**Why tolerated.** Everything around the click is automated — the form, the review, the
role, both DMs — and the design turns the one manual step into a named nudge on the card
rather than pretending it does not exist. The alternative (asking the applicant to confirm)
adds a step that can also be forgotten and proves nothing.

**What would change it.** Twitch publishing a Teams API, or **1** applicant reporting they
never got an invite. The cheap fix for the second is a per-form reminder on the card after
N days, not a new integration.

## KI-13 — An upload announcement can be up to ~25 minutes late — `ACCEPTED`

**Symptom.** Two delays add up. The feed is edge-cached: the live response
carries `Cache-Control: public, max-age=900` and an `Age` header (measured
2026-09-02: `Age: 56` on a fresh fetch), so a publish can be up to **15
minutes** old before the feed even shows it. On top of that the sweep runs
every `youtube_poll_minutes` — **10** by default. Worst case is therefore about
**25 minutes** between hitting publish and the post appearing.

**Status.** `ACCEPTED` — there is no push path without a key, and no push path
at all short of PubSubHubbub, which needs a public callback URL this bot does
not have.

**Why tolerated.** An upload is not time-critical the way a go-live post is;
nobody is being told to come and watch something that is already half over. The
gap is a setting, so the owner can shorten it — but not below 5 minutes, and the
validator says why: below the feed's own 15-minute cache, a shorter sweep
re-fetches the same bytes and finds nothing new any sooner.

**What would change it.** The owner reporting the lateness as a problem, or
uploads becoming time-critical (a premiere people are meant to arrive for). The
fix then is PubSubHubbub with a public callback, not a shorter poll.

## KI-12 — YouTube's own uploads feed answers only about half the time — `ACCEPTED`

**Symptom.** `https://www.youtube.com/feeds/videos.xml?channel_id=UC…` returns
HTTP 404 or 500 for a channel that plainly exists, at random. Measured
2026-09-02 from this machine, one channel, 30 requests two seconds apart:
**15 × 200, 12 × 404, 3 × 500**. It is not per-channel — two other well-known
channels took 11 and 24 tries respectively before their first 200 — and it is
not the network: `youtube.com/robots.txt`, the channel page itself and an
unrelated Atom feed all answered 200 throughout, and the failures carry
YouTube's own `Server: YouTube RSS Feeds server` header.

**Status.** `ACCEPTED` — worked around, not fixed. `YouTubeClient.fetch_feed`
retries up to `FEED_ATTEMPTS` (4) per sweep, and a feed that never answers
raises `YouTubeError`, which the poller treats as a **transient fetch failure**
— never as "that channel is gone". Nothing is unlinked and nothing is seeded on
a failure; the next sweep tries again.

**Why tolerated.** It is YouTube's server, there is no alternative keyless
source of the same data, and a 10-minute sweep with 4 tries each makes a missed
upload very unlikely to be missed twice. The cost of a failure is lateness, not
a wrong announcement.

**What would change it.** A measured 200-rate below **~25%** (at which four
tries stops being enough), or **1 upload confirmed missed for a whole day**.
Either would mean moving to the Data API's `playlistItems.list` on the uploads
playlist, which needs `YOUTUBE_API_KEY` and spends quota per channel per sweep.

## KI-11 — Without `YOUTUBE_API_KEY` a live broadcast can be announced as an upload — `ACCEPTED`

**Symptom.** The Atom feed carries no duration and no live-stream marker — it is
`yt:videoId`, `title`, `published`, `link` and the author, and nothing else
(measured 2026-09-02 against a real feed). So a scheduled or live broadcast that
appears in the feed is indistinguishable from an ordinary upload. D6's keyless
fallback skips an entry only while its uploader has an **open go-live session on
platform `youtube`**; a broadcast published while they have no such session open
is announced as "just dropped a new video".

**Status.** `ACCEPTED` — the design decided this (D6) rather than discovering it.

**Why tolerated.** Go-live presence already covers streams, so the overlap is
narrow: it needs a YouTube broadcast whose author is linked here AND who is not
showing as live on Discord at that moment. Shorts do NOT have this problem —
the feed links them as `/shorts/<id>`, so they are told apart with no key at
all, which is better than the design assumed.

**What would change it.** `YOUTUBE_API_KEY` being set (the cog then asks
`videos.list` for `liveStreamingDetails` and marks it `live`), or **1
mis-announcement** the owner notices. Until then `youtube_mode` ships `off`.

## KI-10 — The OLD process logs `asyncio: Unclosed client session` while a rolling deploy replaces it — `WATCHING`

**Symptom.** In the Fly log stream during the `d777f57` deploy (2026-09-03
00:42:59Z), the machine being retired printed `ERROR asyncio: Unclosed client
session` on its way down. The NEW process booted clean (15 cogs — that is the
**2026-09-03** boot line, kept as read; the tree holds **19** cogs today — logged in,
birthdays import ran) and the line has not reappeared since.

**Status.** `WATCHING` — seen **twice**, both at shutdown only, on the process that was
already being stopped: the `d777f57` deploy (2026-09-03) and the **v111** deploy (2026-09-16 16:06:56Z,
the retiring machine's last line before the new one's `database ready` at 16:07:02Z). Still never on a
running machine, still one per deploy.

**Why tolerated.** An aiohttp `ClientSession` that was never `close()`d is
reported by its finaliser at interpreter exit; it costs nothing after the
process is gone and cannot affect the replacement machine. Candidates are the
Twitch/YouTube/Groq/webhook clients that are opened lazily and never closed in
`bot.py`'s `close()` path — not confirmed; the log line does not name the
owner.

**What would change it.** The same line appearing on a RUNNING machine (not at
shutdown), or more than one per deploy — then it is a leak, not a finaliser
grumble, and `bot.py`'s shutdown path gets an explicit close for each lazily
opened session. Next deploy: read the retiring machine's tail and count.

## KI-1 — (CLOSED 2026-09-01) SQLite database lives inside a OneDrive-synced folder

**Was:** the entry below. **Now:** local `.env` `DATABASE_PATH` points at
`C:/Users/nbasl/black-bloc-data/black_bloc.sqlite3` (outside OneDrive); the old
file was copied there and the original under `data/` is inert (deletable at
will). The hosted deployment always used the Fly volume and was never affected.

## KI-1 (original text, kept for the record) — SQLite database lives inside a OneDrive-synced folder — `WATCHING`

**Symptom:** the default `DATABASE_PATH=data/black_bloc.sqlite3` sits under
`OneDrive/Documents/...`. OneDrive syncing a live SQLite file (plus its `-wal`
and `-shm` sidecars) is a known source of "database is locked" errors and, in
the worst case, a torn copy in the cloud.
**Why tolerated:** the DB is empty and the bot is not yet running unattended;
the hosted deployment uses a Fly volume at `/data`, not this folder.
**What would change it:** the first real table with data, OR the bot running
locally for more than a test session. Fix is one line in `.env`
(`DATABASE_PATH=C:\...\outside-onedrive\black_bloc.sqlite3`).

## KI-2 — Slash commands are re-synced to the dev guild on EVERY startup — `ACCEPTED`

**Symptom:** `bot.py:setup_hook` calls `tree.sync(guild=...)` unconditionally
when `DEV_GUILD_ID` is set. Command sync is rate-limited by Discord; frequent
restarts can trip it (symptom is a 429 in the log and a startup delay).
**Why tolerated:** guild-scoped sync is instant and the limit is generous for
a single dev guild; the convenience of "restart and the new command is there"
is worth it during development.
**What would change it:** the bot serving more than one guild — then commands
sync globally, once, via an explicit command, not at boot. Number: **>1 guild**.

⚠️ **Second sync on the same boot, 2026-08-27 — `ACCEPTED` too.** Command
visibility (`info/code-notes.md` § `command_visibility.py`) re-applies the
stored feature modes right after the startup sync, so a boot with
`rolemenu_mode` **off** spends a *second* guild sync about five seconds after
the first. It only happens when a hidden-when-off feature is actually off and
the tree therefore had to change; a boot with everything on syncs once, as
before. The alternative — applying visibility *before* the startup sync — was
rejected because `copy_global_to` re-seeds the guild mapping from the globals
and would put the hidden command straight back. **What would change it:** a 429
on startup in the log. Number: **1 observed 429**.

## KI-4 — Modmail transcripts link to attachments that expire — `ACCEPTED`

**Symptom:** transcripts store attachment URLs as Discord CDN links, which
carry signed `?ex=…&is=…&hm=…` parameters and stop resolving after ~24 h.
A transcript read a week later has dead attachment links (the text is
intact).
**Why tolerated:** re-uploading every attachment into the log channel would
double storage and re-post member content; the incumbent Modmail bot has the
same limitation. The transcript header says the links expire.
**What would change it:** a staff request to keep attachments — then mirror
them to the Fly volume (or R2) at close time. Number: **any** such request.

## KI-5 — Test mode does not stop a web modmail reply or a web `/warn` from reaching a member — `ACCEPTED`

**Symptom:** while `TEST_MODE`, `POST /api/modmail/tickets/{id}/reply` and
`POST /api/mod/warn` (and their slash-command twins) still DM the real
member; `POST /api/honeypot/setup` and `POST /api/tempvoice/setup` still
create real channels (inside the test category). The guard sees channel
sends and edits, not DMs or channel creation.
**Why tolerated:** DMs are inside the owner's test policy ("you're allowed to
be dm'd to test too"); the slash commands behave identically, so the web is
not a wider door; channel creation is place-gated to the test category.
**What would change it:** the first time a real member receives a test DM by
mistake — then add a `TEST_DM_ALLOWLIST` of user ids the guard permits.
Number: **1 incident**.
⚠️ **The modmail PRACTICE ticket is the one modmail DM test mode does stop**
(2026-09-05, Build B): a practice reply and a practice close send nothing at
all, and log **no** `modmail.dm_failed` — a suppressed DM is not a failed one.
That is deliberate and is why the practice ticket is the safe place to try the
card. A REAL ticket's **Reply** button reaches a real member exactly as
`/reply` does, test mode or not — nothing in modmail may be read as "safe
because test mode is on".

## KI-6 — (SUPERSEDED 2026-08-31) A stolen session cookie stays valid after sign-out — `CLOSED`

**Was:** the entry below — a stateless signed cookie that logout could not revoke,
accepted while the owner was the only site user. **Its threshold (">1 site user")
was crossed by Phase 13**, which opened the dashboard to any signed-in guild
member. **Now:** schema 17 adds a `sessions` table; the cookie payload carries a
session id, every authenticated request checks it live (30 s in-process verdict
cache, logout poisons the cache before the row), and `POST /api/auth/logout`
revokes. Deployed 2026-08-31 (`0c49257`) — every cookie minted before it became
invalid at that deploy, one sign-in each. **Residual, accepted:** if the database
is down, `alive()` answers True and the request proceeds on signature + expiry
alone — refusing would turn a sqlite blip into "everyone signed out" while every
data route already refuses via `require_db`; revocation is unenforceable exactly
while nothing else works.

## KI-6 (original text, kept for the record) — A stolen session cookie stays valid for up to 7 days after sign-out — `ACCEPTED`

**Symptom:** the site session is a stateless signed cookie
(`__Host-bb_session`); `/api/auth/logout` clears it in the browser but
cannot revoke a copy taken elsewhere until it expires (`SESSION_TTL_SECONDS`,
7 d).
**Why tolerated:** every request re-checks staff status against the live
guild cache, so a stolen cookie is useless the moment the account loses its
staff role or leaves; the cookie is `__Host-`, `Secure`, `HttpOnly`, so
theft needs the browser itself.
**What would change it:** a second staff member (i.e. any user other than
the owner) signing in — then add a `sessions` table with a per-session id
in the signed payload and a revocation on logout. Number: **>1 site user**.

⚠️ **THRESHOLD LIKELY CROSSED — owner decision needed (flagged by the docs
audit, 2026-08-31, not acted on).** Phase 13 (live `8036918`, 2026-08-27 20:15)
opened the dashboard to **any signed-in guild member** in the member-only
Requests view, so ">1 site user" is no longer a hypothetical: the design intends
many. The same reasoning touches **KI-9** (anonymous poll votes: "Number: >1
person with `/data` access, or 1 sensitive poll"). Neither number was measured
today — nobody checked how many distinct accounts have actually signed in. Both
entries stay `ACCEPTED` until the owner rules; this note exists so the next
session does not read the old threshold as still un-met.

## KI-8 — A role-menu panel in a channel Black Bloc cannot reach is retried on every flip — `ACCEPTED`

**Symptom:** turning `rolemenu_mode` **off** logs `role_menu.unpost_failed` for
any menu whose channel is gone, invisible, or refuses the delete, and keeps the
row's `message_id`. Every later flip tries that menu again and logs the same
line, forever. `role_menu.would_unpost` behaves the same way while test mode
refuses the channel — which today is **every** panel outside
`TEST_CHANNEL_ID`.
**Why tolerated:** the alternative is worse. Clearing `message_id` on a failure
would tell the database the panel is down while it is still up in the channel,
and the next `on` would post a **second** panel beside it — two live selects
with the same `custom_id`. A repeated log line is cheap; a duplicated panel is
the kind of thing somebody has to clean up by hand. The sweep never blocks on
it: one failure costs one menu and the loop carries on
(`info/code-notes.md` § `rolemenu_panels.py:108`).
**What would change it:** a menu whose channel has genuinely been **deleted**
(`on_guild_channel_delete`) should clear both `channel_id` and `message_id`, at
which point the row stops being retried because there is nothing left to
reconcile. Number: **any menu logging `unpost_failed` on more than 2
consecutive flips** with a channel that no longer exists.

## KI-7 — (SUPERSEDED 2026-08-27) The dashboard Health tab lists no loops but the presence one — `CLOSED`

**Was:** `api/status.py` built the loop list by asking every cog for
`get_tasks()`. `commands.Cog` in discord.py 2.7.1 has no such method — measured
2026-08-27 at runtime, `hasattr(commands.Cog, "get_tasks")` is `False` — and only
`cogs/presence.py` defined one, so the other five loop-owning cogs contributed
nothing and their `loop_health` readers were never called.
**Now:** `api/status.py:_loops` discovers loops **generically**, by walking each
cog's class and instance dicts for `discord.ext.tasks.Loop` instances and asking
`cog.loop_health(<attribute name>)` for the health beside each one. `get_tasks`
is gone from `presence.py` — one home, and the fix was one reader rather than
the five near-identical three-line methods this entry proposed. The Health tab
now lists **seven** loops across six cogs; every cog's `loop_health` already
accepted its own attribute name, so no mapping table was needed. The API shape
(`cog`, `name`, `running`, `failed`, `state`, `next_iteration`, `last_ok_at`,
`last_error`) is unchanged, so `site/` and `site/mock/contract.json` needed no
edit. A parametrised test in `tests/api/test_status.py` builds each real cog and
asserts every loop it owns reaches `/api/status` with the `last_ok_at` the cog
records — so a cog added later with a loop is covered by adding one row.
**Residual, accepted:** discovery is by TYPE, so a loop a cog holds somewhere
`getattr` cannot reach (inside a list, a dict, a lazily-built object) is still
invisible. Nothing in the tree does that, and the honest "this loop does not
record its last success yet" text still covers a cog with no `loop_health`.

## KI-3 — (SUPERSEDED 2026-08-26 by Phase 8a) The FastAPI companion has no authentication — `CLOSED`

**Was:** off by default, localhost only, no auth. **Now:** the API is public
on `https://blackbloc.heygabi.ai` with Discord-OAuth sessions on every route
except `/health`; rate-limited login/callback; CSP/HSTS. The three original
"why tolerated" premises are all false, so the entry is closed rather than
edited. `/health` exposing guild count + latency publicly is the residual
and is accepted (it is what a status page is for).

## KI-3 (original text, kept for the record) — The FastAPI companion has no authentication — `ACCEPTED`

**Symptom:** `/health` (and anything added later) answers anyone who can reach
the port.
**Why tolerated:** `API_ENABLED` defaults to `false`; when on, it binds to
`127.0.0.1` and `fly.toml` deliberately has no `[http_service]`, so nothing is
reachable from outside the machine/container.
**What would change it:** the first route that is exposed beyond localhost
(a dashboard, a webhook receiver). At that point auth is a blocker for the
exposure, not a follow-up.

## KI-9 — (SUPERSEDED 2026-08-31) Anonymous panel-poll votes are hashed, not unlinkable — `CLOSED` for new polls

**Was:** the entry below — a truncated per-poll SHA-256 anyone with the DB could
confirm a guess against; its "what would change it" (a second person with data
access / the member-facing turn) arrived with Phase 13. **Now:** schema 18 stores
a `vote_scheme` per poll; polls created while `POLL_VOTE_SECRET` is set (it was
set 2026-08-31) use HMAC-SHA256, so confirming a guess needs the key, not just
the table. Old polls keep their scheme — changing it under an open poll would
hand voters a second vote. A poll keyed to a lost secret refuses votes in words
(never double-counts). The live `poll_votes` table was empty at cut-over, so in
practice every real anonymous vote will be keyed.

## KI-9 (original text, kept for the record) — Anonymous panel-poll votes are hashed, not unlinkable — `ACCEPTED`

**Symptom:** a poll created with `anonymous` on runs on Black Bloc's own panel and stores one `poll_votes` row per voter keyed by a truncated per-poll SHA-256 of the member id (no name, no id). Someone holding BOTH the database and a member list could confirm a guess ("did member X vote?") by recomputing the hash; they cannot enumerate voters from the table alone.
**Why tolerated:** a panel must store one row per person to stop double voting; a keyed MAC would need a secret that has to live somewhere (env + Fly secret + recovery doc) for a threat that requires database access, which already exposes far more than poll choices. The dashboard and every embed never show per-voter rows for anonymous polls. Recorded in `info/code-notes.md` § "polls (10b)".
**What would change it:** a second staff member with database access, or the first anonymous poll about anything sensitive (staff elections, conduct). Number: **>1 person with `/data` access**, or **1 sensitive poll** — then move to an HMAC with a `POLL_VOTE_SECRET`.
