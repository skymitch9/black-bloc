# Announce overrides — hosts off by default, a per-run answer for each person, and a no-@ choice

> 🔴 **THIS CHANGES LIVE BEHAVIOUR AT DEPLOY.** Every marathon whose own **Host announcements** switch follows the
> setting — which is **every marathon at deploy**, because the column is new and reads NULL — **stops announcing its BaF
> hosts**: no host-block heads-up at any mark and no host highlight. Runners are unchanged. A host highlight already up
> is carried to *done*. To keep a marathon's hosts announced, turn its **Host announcements** on (thread controls, the
> drawer, or `PATCH`), or set `marathon_host_announcements_default` on for the whole server. ⚠️ The live rows were NOT
> read by this build; the rule above is what applies to them. The full list is in **Deploy note** at the foot.

> 🔧 **REVIEWED AND AMENDED 2026-10-06** — an independent review found 12 things; all are fixed on this branch and
> listed in **Review fixes 2026-10-06** at the foot, each with the test that pins it. Where a fix changed a rule, the
> section it lives in was rewritten in place (*Host blocks*, *A post already up*, §2, §3, the decisions), so this doc
> reads as the code now is.

> 🔨 **BUILT 2026-10-06 on branch `announce-overrides` (worktree `C:/lcw/bb-announce-overrides`, off `main`
> `2c2a256b`), NOT MERGED, NOT DEPLOYED.**
>
> **Audience:** the conductor, reviewers, and the next session touching marathon reminders, highlights, host blocks,
> the runner post's buttons, the thread controls or the People card. **Status:** TRACKED. **Last verified:
> 2026-10-06** — against the branch's own code by the suite (`tests/test_marathon_announce.py`,
> `tests/cogs/content/test_marathon_announce.py`, the new tests at the foot of `tests/api/tools/test_marathons.py`,
> `tests/cogs/content/test_marathon_people.py`, `tests/cogs/content/test_marathon_thread_controls.py`,
> `tests/storage/test_db.py`, `tests/test_marathon_reminder_posts.py`, `tests/test_marathon_host_highlights.py`),
> `ruff check .`, `node site/mock/check.mjs` (the builder on `MOCK_PORT=8802`, the review fixes on `8803`), every
> `site/mock/*.test.mjs`, and — the builder only — one rendered look at the mock's AGDQ 2027 drawer in Chrome (the Host
> announcements field, the People card's per-run line and its button pressed once). The review fixes opened no
> browser. ⚠️ **NOT checked:** anything against Discord, the live database, the live settings. Secret NAMES only.

## The ask and the answers, verbatim (owner, 2026-10-06)

Ask: *"Add a opt out for individual runner pings next to the highlight run button, that way some runners wont get
pinged when they're getting into the zone for their run. We also want to revert the host vs runner pings opt in opt out
change we made. Out host pings out by default opt runner pings on by default. then with each scanned run have an opt
out/opt in override so some runners can be announced if staff allow runner to be annoucned at all."*

- **What "runner pings" means:** *"Right now we say @skyaiva is running Pokemon in 2 hours, thats the ping im talking
  about for the runners themselves."* … *"if the @runner thing isn't actually pinging people thats a none issue then.
  add the opt in opt out anyway like planned"*.
- **Hosts off by default, how far:** *"3. a"* — NO public host posts at all by default; hosts are still found and shown
  to staff; staff can turn hosts on for a marathon or opt a single run in. Runners stay on by default.
- **Precedence:** *"4. b"* — the marathon's announcements switch is the MASTER: off means nobody on it is announced,
  and no per-run button gets round it.

## The decision — one pure function

`marathon_announce.decide(master, opted_out, answer, role, hosts_on)` answers *is this person announced for this run*
for every public post: a runner's reminder at every mark, a runner's highlight, a host block's heads-up and highlight.
In this order:

1. the marathon's **BaF announcements** switch is off → **no** (`marathon_off`);
2. the person is opted out of the whole marathon and the run has no *yes* of its own → **no** (`opted_out`);
3. the run's own answer, if it has one → *in* **yes**, *out* **no** (`run`);
4. the default for their part on that run → runner **yes** (`default`); host → the marathon's **Host announcements**
   (`default` when on, `hosts_off` when off).

### Truth table (every row is one parametrized case of `test_every_row_of_the_truth_table`)

| BaF announcements | Opted out of the marathon | This run's answer | Runner | Host, Host announcements OFF | Host, Host announcements ON |
|---|---|---|---|---|---|
| off | any | any | no · `marathon_off` | no · `marathon_off` | no · `marathon_off` |
| on | no | none | **yes** · `default` | no · `hosts_off` | **yes** · `default` |
| on | no | in | **yes** · `run` | **yes** · `run` | **yes** · `run` |
| on | no | out | no · `run` | no · `run` | no · `run` |
| on | yes | none | no · `opted_out` | no · `opted_out` | no · `opted_out` |
| on | yes | in | **yes** · `run` | **yes** · `run` | **yes** · `run` |
| on | yes | out | no · `opted_out` | no · `opted_out` | no · `opted_out` |

That is 2 × 2 × 3 × 2 × 2 = 48 combinations; the test lists all 48 and asserts the list is complete.

Three gates sit OUTSIDE the function, unchanged: `marathon_public_reminders` (guild, every public reminder),
Auto-highlight (per marathon, whether a highlight is posted at all), and `marathon_host_highlights` (guild, the old
host master — off still means no host posts whatever the table says).

### Who is on a run, and in which part

- `marathon_announce.baf_on(row)`: the people of ours on the run (`mt.ours`, one line a member, the runner part first)
  plus its BaF hosts even when a host does not make the run ours (`marathon_hosts_count_as_ours` off).
- **Someone who runs and hosts the same run is a runner for it** (the brief).
- A commentator who counts as ours is weighed as a runner (announced by default, as before this build).

### Host blocks

Blocks are unchanged (`marathon_host_highlights.blocks`). A block is announced when its host is announced for **at
least one run of it**, once, exactly as before: the heads-up at each mark from the block's first run, one highlight
when any run of it goes live. `marathon_announce.block_people` weighs the host **as a host on every run of the block**
(`host_verdict`).

- **On a run the host only hosts**, the run's own answer is about their hosting: *Announce X for this run* on any such
  run of a four-run block announces the block once; leaving them out of every run silences it.
- **On a run the host also RUNS**, the run's own answer is about their run only (`runs_it`). It is read as *no answer*
  when the block is weighed, in both directions: *Announce X for this run* there never opts their block in, and *Do not
  announce X for this run* there never silences it. Their run's own reminder and highlight follow the answer.

### A post already up — it keeps or loses names, it never gains one the decision does not announce

Every public post **records who it names**, with the record of its own message id:

| Post | Where the names are recorded |
|---|---|
| A run's highlight | `marathon_runs.public_people` — JSON list of `{user_id, name, part, login, plain}` |
| A host block's highlight | `named` on the block's record in `marathons.host_highlight_posts` — the same shape |
| A run's public reminder, each mark | `people` (a list of ids) on that mark's `public` copy in `marathon_runs.reminder_posts` |
| A host block's heads-up, each mark | `people` on that mark's `public` copy in the block record's `reminders` |

`marathon_announce.still_named` is the one rule a post already up is weighed by, a person at a time:

1. **Someone the post names stays** unless they are left out *by name* — opted out of the marathon, or this run's
   answer is *out* — or they are no longer on the run / hosting the block. The master going off and Host announcements
   going off never take them off (the two carries, decisions 1 and 2).
2. **Someone a move was aimed at is weighed afresh, and only them**: the master still held on, the real Host
   announcements switch. So *back to the default* on a host while hosts are off takes **that host** off the post and
   leaves a co-host exactly as they were.
3. **Someone the post does not name joins only when the real decision announces them** — the real master, the real
   Host announcements switch. A host who counts as ours (`marathon_hosts_count_as_ours`) while hosts are off is never
   written onto a run's post because its runner left.
4. **No record** (a post from before the record existed) **reads as naming everyone of ours not left out by name** —
   which is who `main` named — and the record is written at the first tick that follows it.

The record is written whenever who is named changes, before the edit. What follows from a post naming **nobody**:

- **A highlight** (a run's or a block's) is **taken down** by the existing path — the decision stored, the message
  edited to `marathon_public_removed` — while its run / block is **not over**. Once it is over the post is **left as
  it stands**: nothing can put a finished highlight back (`put_back` is for upcoming and live), so the tick never takes
  one down. A staff move still does, as before.
- **The taken-down line names who the post named** (its record), never everyone on the run.
- **A reminder** is **left as posted** — `reminder-edit-in-place-design.md` rule 10, unchanged. Its record still
  shrinks, so a later edit cannot write the person back unless the decision announces them.
- **A run nobody of ours is on any more** whose post has no record keeps `main`'s behaviour (the schedule's own names).

## 1. Hosts off by default — the Host announcements switch

- **`marathons.host_announcements INTEGER`** — NULL follows the new guild key
  **`marathon_host_announcements_default`** (bool, **off**); 1 / 0 is the marathon's own answer.
- **One writer:** `cogs/content/marathon_hosts.set_switch` with a third `which` (`mh.HOST_ANNOUNCE`). It logs
  `marathon.host_announcements_set` (`from`, `to`, `on`, `via`), re-renders the thread controls and answers
  `marathon_host_announcements_on_said` / `_off_said`.
- **Doors:** the thread controls' new button (`marathon:controls:{id}:hostannounce:{on|off}`, labels
  `marathon_controls_host_announcements_on` / `_off`, placed straight after BaF announcements — nothing else moved),
  the drawer's *Settings for this marathon* ▸ **Host announcements**, and `PATCH /api/marathons/{id}`
  `{"host_announcements": true|false|null|"follow"}`. `GET` answers `host_announcements: {own, on, default}`.
- **Checklist 38:** the switch going off stops NEW host posts; a host highlight already up follows its block to *done*
  (`test_host_announcements_going_off_carries_a_highlight_already_up_to_done`).
- A skipped host heads-up logs `marathon.host_reminder_skipped` with `because: host_announcements_off` when turning the
  switch on would have named someone, else `opted_out` as before.
- A host **highlight** that would have gone up when a run of the block went live, but names nobody, logs
  `marathon.host_highlight_skipped` with the same `because` — **one row a block** (`skipped` on the block's record),
  not one a run and not one a tick. Turning Host announcements on later still posts it at the block's next run.
- Hosts are still FOUND, matched and shown exactly as before: no change to matching, the People view, the runner posts
  or `marathon_hosts_count_as_ours`.

## 2. A run's own answer for each person

- **Storage: `marathon_runs.announce_people TEXT`** — a JSON object `{user_id: "in" | "out"}` on the run row; no entry
  means *follow the defaults*; NULL once it is empty.
- **One writer, `cogs/content/marathon_announce.set_run_answer`** (under the marathon lock). It posts nothing. Refusals
  in words: 422 `bad_announce` for a word it does not know, 404 for a run that is gone, 404 `not_on_run` for someone
  who is not BaF on that run, and **409 `run_over` for a run that is done or off the schedule** — `**{game}** is over,
  so nothing was changed.` / `**{game}** is off the schedule, so nothing was changed.` Every door comes through this
  writer (the run post's buttons and menus, the People slot view, the site's route), so a stale button and a hand-made
  `POST` are refused the same way; the mock refuses with the same words. On a change it logs
  `marathon.announce_run_set` (`run_id`, `game`, `member`, `from`, `to`, `via`) and follows the highlights the way the
  marathon-wide opt-out does:
  - a highlight that names nobody any more is taken down (the decision stored first, the message edited to
    `marathon_public_removed`, never deleted);
  - one that still names someone is rewritten in place;
  - one taken down comes back IN PLACE (an edit) while its run / block is not over **and the marathon still
    announces** — with the master off nothing comes back.
  - No reminder that already went out is sent again and no passed mark is replayed. A reminder still ahead is rewritten
    in place by the existing follower (`reminder-edit-in-place-design.md`).
- **The marathon-wide opt-out stays** (`set_opt_out`, the *every run on this marathon* move). Its labels now say so:
  `marathon_public_button_opt_out` defaults to **Opt out of every run on this marathon**, `_opt_in` to **Opt back in to
  this marathon** (a stored custom value is staff's and stays).

### The doors

- **Each scanned run's post in the staff thread.** While the run is upcoming or live the post carries, under the
  whole-marathon button, **two buttons a person** — never two spellings of one move:
  - the run's answer: **Do not announce {name} for this run** (they would be announced), **Announce {name} for this
    run** (they would not), or **{name}: back to the default for this run** (the run has an answer);
  - their @: **No @ for {name}** / **@ {name} again**.
  Custom ids `marathon:announce:{marathon_id}:{run_id}:{user_id}:{in|out|default|plain|mention}`
  (`AnnounceButton`, persistent, staff re-checked on press).
- **More than four people** on a run (Discord takes five rows): the buttons become a menu
  (`marathon:announce:{marathon_id}:{run_id}:pick`, `AnnouncePick`, placeholder `marathon_announce_pick`) holding the
  same moves. **Past twelve people it is one menu for every twelve** — `…:pick`, `…:pick2`, `…:pick3`, `…:pick4`, a
  menu a row, a person's two moves always in the same menu — so nobody loses a move up to 48 people on one run. Past
  48 the rest are reached from the site (the post has no rows left).
- **The state in words**, one line a person under the post's own text (`marathon_announce_state_line`):
  *Sky: announced for this run — the default* · *anarchy: not announced for this run — host announcements are off for
  this marathon* · *… — set for this run* · *… — opted out of every run on this marathon* · *… — BaF announcements are
  off for this marathon*, with *· written without an @* when that applies. The post is edited in place.
- **The People slot view** (`/event` ▸ a marathon ▸ People… ▸ a slot ▸ a BaF person): the same two moves on their own
  row and the same state line. This is the Discord door for a run that has no post of its own (a run only a BaF host is
  on).
- **The site's People card:** a slot's BaF person shows the state line and the one move; the BaF row shows the @ move.
  The words are the bot's keys (`move_label`, `said` in the payload).
- **The API:** `POST /api/marathons/{id}/runs/{run_id}/people/{user_id}/announce` `{"to": "in"|"out"|"default"}` and
  `POST /api/marathons/{id}/people/{user_id}/mention` `{"to": "plain"|"mention"}`; both answer the People board +
  `message`. `GET /api/marathons/{id}` carries `announce` on each BaF person of each run (`role`, `answer`,
  `announced`, `why`, `said`, `move`, `move_label`); the board's BaF rows carry `mention` (`plain`, `own`, `move`,
  `move_label`).

## 3. The no-@ choice

- **Storage: `marathons.mention_people TEXT`** — `{user_id: "plain" | "mention"}`; no entry follows the new guild key
  **`marathon_mention_people`** (bool, **on** = today's @). Only an answer that differs from the server's is stored.
- When a person is *plain*, every public post about them on that marathon writes their **name as the schedule has
  it** — the same name `{runner}` shows on a highlight, so a person reads the same on the reminder and the highlight —
  as plain text wherever the template says `{member}` / `{mention}`. It is escaped by `pb_feed.plain` (markdown, masked
  links, and a zero-width space inside `://` so an address in a name never links) and then mention-escaped. Timing,
  role mentions and everything else are unchanged. Runners and hosts alike; two people on one run each follow their
  own. (What staff are *told* after a move still uses the server display name; that reply is not public.)
- **A finished post keeps how it wrote each name.** The record holds `plain` a person; once a run or a block is done
  its post is rendered from that, so changing the @ choice later never rewrites a finished highlight — which is why
  the no-@ move needs no refusal on a run that is over.
- **One writer, `set_mention`.** It logs `marathon.mention_set` (`member`, `from`, `to`, `via`) and re-renders what is
  up in place: highlights (runner and host) and every reminder still being followed. Nothing new is posted.
- The staff thread's own posts and reminder copy are not public and keep the `<@id>` text.

## What is stored, what is counted

| | Added |
|---|---|
| Columns (`ADDED_COLUMNS`, no `SCHEMA_VERSION` step — it stays **89**) | `marathons.host_announcements INTEGER`, `marathons.mention_people TEXT`, `marathon_runs.announce_people TEXT`, and — review fixes — `marathon_runs.public_people TEXT` (all mirrored to the two archive tables at boot) |
| JSON fields inside existing columns (review fixes) | `named` and `skipped` on a block record in `marathons.host_highlight_posts`; `people` on a public copy in `marathon_runs.reminder_posts` and in a block record's `reminders` |
| Tables | none |
| Registry keys | **867 → 893 (+26)**: `marathon_host_announcements_default`, `marathon_mention_people`, `marathon_controls_host_announcements_on` / `_off`, `marathon_host_announcements_on_said` / `_off_said`, `marathon_announce_button_run_out` / `_run_in` / `_run_default` / `_plain` / `_mention`, `marathon_announce_pick`, `marathon_announce_state_line` / `_state_yes` / `_state_no` / `_state_plain`, `marathon_announce_why_default` / `_why_run` / `_why_marathon` / `_why_off` / `_why_hosts_off`, `marathon_announce_run_in_said` / `_run_out_said` / `_run_default_said`, `marathon_mention_plain_said` / `_on_said`. Two defaults reworded: `marathon_public_button_opt_out` / `_opt_in` |
| Log kinds | **+3** routine: `marathon.host_announcements_set`, `marathon.announce_run_set`, `marathon.mention_set` (+ their `web.` twins through `kind_via`); review fixes **+1** routine: `marathon.host_highlight_skipped`. `marathon.public_highlight_removed` and `marathon.host_highlight_removed` carry `because`: `opted_out` (the marathon-wide opt-out), `run_answer` (this run's answer), `hosts_off` (Host announcements, after a move back to the default), `not_on_run` (the person left the run / the block), `marathon_off` (reserved: a post already up is never taken down by the master) |
| Contract | **312 → 315 entries (+3)**: the two new routes and one more `PATCH` variant; `action_kinds` +3 |
| Thread controls | **6 → 7** buttons (8 with Event schedule), + the link button |
| Dynamic items | +2 (`AnnounceButton`, `AnnouncePick`) |

## Decisions beyond the brief

Numbered once. 1–12 are the build's; 13–20 were made by the review fixes.

1. **A post already up is followed with the master held on**: BaF announcements going off stops new posts and never
   rewrites or strands one in flight (the behaviour before this build, kept). Amended by the review: the master is
   held on only for people the post already names; nobody joins a post while the master is off.
2. **Host announcements going off while a host post is up carries it** with everyone on it who is not left out by
   name. A later move aimed at **one host** weighs that host with the real switch, so *back to the default* on the only
   run that announced a host takes them off; amended by the review — it no longer touches a co-host.
3. **A host who also runs a run of their own block does not announce the block by default** — the block weighs them as
   a host; that run's reminder still names them as a runner. Amended by the review: that run's own answer is about
   their run only (*Host blocks*).
4. **The run's answer and the @ are separate moves**, two buttons a person, so four people fit as buttons.
5. **Per-run buttons and the state lines show only while the run is upcoming or live**; a finished run's post keeps the
   whole-marathon button only.
6. **With the master off the per-run button still offers the move the defaults would allow** (it stores the answer for
   when the master comes back); the state line says *BaF announcements are off for this marathon*.
7. **The site's button words** *Opt out of every run* / *Opt back in to every run* are site chrome constants (the
   existing convention); the per-run and @ labels come from the keys.
8. **Refusals are module constants** (`BAD_RUN`, `NOT_ON_RUN`, `BAD_MENTION`, and now `RUN_OVER` / `RUN_DROPPED`) — the
   existing refusals' convention.
9. **The default highlight template names people with `{runner}`** (bold, no @), so the no-@ choice shows on a
   highlight only when staff's template uses `{mention}`; the default reminder template uses `{member}` and always
   shows it.
10. **A reminder whose run is already live or done is not rewritten** when the @ choice changes (edit-in-place rule 5),
    and nothing is rewritten while `marathon_reminder_on_move` is `repost`.
11. **A commentator who counts as ours is weighed as a runner** — announced by default, as before this build — and
    **someone who runs and hosts the same run is a runner for it** (*Who is on a run*).
12. **The marathon-wide opt-out's two labels were reworded** to say *every run on this marathon*, so they never read
    like the per-run button beside them; a stored custom wording is staff's and stays (see *Deploy note*).
13. **A post records who it names; nothing is inferred from "nobody is left"** (*A post already up*). This replaces
    the build's `carried` retry, which is what named a host who was never announced.
14. **No record reads as "everyone of ours not left out by name"** — who `main` named — so a post that is up at deploy
    keeps its names, and the record is written at the first tick.
15. **The tick never takes down a finished highlight.** A highlight that names nobody is taken down while its run or
    block is not over, and left as it stands once it is. The reason is finding 5's: nothing can put a finished
    highlight back.
16. **A run that is over refuses its own answer; the no-@ move is not refused.** The @ choice is the marathon's, not
    the run's, and a finished post keeps how it wrote each name, so it rewrites nothing finished.
17. **One name for a plain person: the schedule's**, the name `{runner}` already shows on the highlight. The server
    display name is no longer written publicly by this feature.
18. **The plain name reuses `pb_feed.plain`** — the repo's one helper for somebody else's words that must not link —
    rather than a second escaping rule.
19. **Menus split at twelve people, up to four menus**; past 48 people on one run the rest are reached from the site.
20. **`because` on a takedown is the decision that binds the person a move was aimed at** (else the first person the
    post named): for a block, the marathon-wide opt-out before Host announcements before a run's answer.

## What is NOT built

- No per-run answer for a whole block in one press; no bulk move across runs.
- No migration of data: every existing row reads *follow the defaults*.
- The role-mention logic (`marathon_role_ping`) is untouched; branch `baf-event-ping` owns it.
- The archive's read-only board does not show the per-run state.

## What was NOT verified

- ⚠️ **Nothing met Discord**: the run post with five buttons or a menu, a real press, the seven-button controls.
- **The live database and settings were not read**; which live marathons have BaF hosts is not known here.
- **The menus past twelve people** were tested as components and as presses on a fake interaction, never in Discord.
- **The review fixes opened no browser**: the People card and the drawer were not looked at again; the only site
  changes are one label and three settings descriptions.
- **No post from `main` was replayed.** *No record reads as everyone not left out by name* is pinned by clearing the
  record of a post this branch made (`test_a_highlight_remembers_who_it_named_and_one_from_before_keeps_its_names`),
  not by a post `main` actually wrote. A reminder copy with no `people` is covered the same way only by the pure test.
- The site was rendered on the mock only (one drawer, one press); the real API under a browser was not.
- The tests were written after the code; four mutations of the decision (host default on, master ignored, the run's
  yes not passing the opt-out, the plain name ignored) were each seen to fail them.


## Review fixes 2026-10-06

An independent review of `f34870b4`. Every finding below was reproduced as a failing test first, then fixed; the
tests were also run against `f34870b4` itself in a throwaway worktree, where each one named here failed. Cog tests are
in `tests/cogs/content/test_marathon_announce.py` unless a file is named; "pure" is `tests/test_marathon_announce.py`.

| # | Finding | What changed | Pinned by |
|---|---|---|---|
| 1 | **BLOCKER.** The `carried` fallback was inferred from "nobody is left", so a run's post that lost its runner was rewritten to name a counting host while hosts were off — on the public reminder and on the highlight; `people or None` then fell through to everyone of ours. | The inference is gone. Each post records who it names and is weighed against that record by `still_named` (*A post already up*); a standing post never falls through to `ours`; a highlight naming nobody is taken down, a reminder is left as posted (rule 10). | `test_a_reminder_already_up_never_gains_a_host_who_is_not_announced`, `test_a_highlight_whose_runner_left_the_schedule_never_names_the_host_instead`, `test_a_reminder_remembers_who_it_named`, `test_a_highlight_remembers_who_it_named_and_one_from_before_keeps_its_names`; pure `test_a_post_already_up_keeps_or_loses_names_and_gains_only_who_is_announced` |
| 2 | A move aimed at one co-host dropped the other, then took the whole post down. | Only the person a move was aimed at is weighed afresh (`moved`); everyone else the post names is carried. | `test_a_move_on_one_co_host_leaves_the_other_on_the_post`, `test_a_move_on_one_co_host_leaves_the_other_on_the_blocks_reminder`; pure `test_a_block_post_already_up_weighs_only_the_host_a_move_was_aimed_at` |
| 3 | One per-run press on a run the host RUNS announced their whole host block. | `host_verdict` reads the run's answer as *none* on a run the host also runs. Both directions pinned. | `test_a_runs_own_yes_where_the_host_runs_never_announces_their_block`, `test_a_runs_own_yes_where_the_host_only_hosts_announces_their_block`; pure `test_a_runs_own_answer_where_the_host_runs_is_about_their_run_only`, `test_a_runs_own_answer_where_the_host_only_hosts_is_about_their_block` |
| 4 | The taken-down line named a host the post never named. | The line is rendered from the post's record (`as_written`). | `test_the_taken_down_line_names_only_who_the_post_named`, `test_a_co_host_left_out_of_every_run_leaves_the_other_and_the_line_names_who_was_up` |
| 5 | A per-run *do not announce* on a DONE run took the finished highlight down for good. | `set_run_answer` refuses a run that is over, in words, on every door (409 `run_over`). The no-@ move is not refused: a finished post keeps how it wrote each name. | `test_a_run_that_is_over_refuses_its_own_answer_in_words_and_changes_nothing`, `test_a_finished_highlight_keeps_how_its_names_were_written`; `tests/api/tools/test_marathons.py::test_a_run_that_is_over_refuses_its_own_answer_on_the_site_in_words`; pure `test_a_run_that_is_over_says_so_in_words` |
| 6 | The menu cut the 13th person's second move (26 moves sliced to 25). | One menu for every twelve people, up to four. | pure `test_past_twelve_people_the_menu_splits_and_nobody_loses_a_move` (12, 13, 20); `test_past_twelve_people_a_runs_post_carries_a_menu_for_every_twelve` (13, 20) |
| 7 | A host highlight skipped at live because hosts are off left no log row. | `marathon.host_highlight_skipped`, one row a block. | `test_a_host_highlight_skipped_for_the_host_default_leaves_one_row_a_block`, `test_a_skipped_host_highlight_still_goes_up_once_hosts_are_announced` |
| 8 | A host takedown always logged `because: opted_out`; a runner takedown logged none. | Both carry the decision that caused it. | `test_the_log_says_which_decision_took_a_post_down`, `test_a_runs_own_no_says_so_in_the_log`, `test_back_to_the_default_with_hosts_off_says_so_in_the_log`; pure `test_the_log_names_the_decision_that_emptied_a_post` |
| 9 | `labels.js` still said the announcements default covers "runners and hosts". | Reworded there, and in the key's description (registry + mock row): the master over both; hosts also need Host announcements. | read, not tested (a label) |
| 10 | A plain name containing a bare address linked in the public channel. | `plain_name` goes through `pb_feed.plain`. | `test_a_plain_name_is_the_schedules_name_and_never_links` |
| 11 | The plain reminder showed the server display name, the highlight's `{runner}` the schedule's. | One rule: the schedule's name (decision 17). The four older plain-name tests now expect it. | the same test, and `test_a_plain_name_is_written_on_the_reminder_and_survives_a_move` |
| 12 | This doc listed 10 decisions where the report claimed 12. | The list above is complete and numbered once; this section and *Deploy note* added. | — |

**Coverage the suite never had** — `marathon_hosts_count_as_ours` ON with Host announcements OFF (`counted(...)`):
the reminder edit-in-place (`test_a_moved_reminder_is_rewritten_without_the_host_who_is_not_announced`), the highlight
re-render and the taken-down line (the two tests of finding 1 and finding 4), the finished highlight
(`test_a_finished_highlight_never_names_a_host_who_is_not_announced`,
`test_a_finished_highlight_whose_runner_left_the_schedule_is_left_as_it_stands`), the host block
(`test_a_host_block_stays_silent_while_hosts_count_as_ours_and_are_not_announced`), and a counting host joining only
once announced (`test_a_host_who_counts_as_ours_joins_a_post_only_once_announced`). Each asserts no public text names
the host.

## Deploy note

- **Every marathon follows the host default, which is off**, because `marathons.host_announcements` is new and reads
  NULL. From the first tick: no host-block heads-up at any mark, no host highlight. A host highlight or heads-up
  **already up is carried** — it keeps its names and follows its block to *done*.
- **Every BaF run post in every tracked marathon's staff thread is edited at the first tick** — once — to carry the
  per-person buttons and the state lines. No ping; the thread shows as edited.
- **A staff-stored custom wording of `marathon_public_button_opt_out` (or `_opt_in`) stays** and will sit beside the
  new per-run button. If it reads like a per-run move, reword it on the Settings page.
- **Posts already up have no record of who they name.** They are read as naming everyone of ours not left out by name
  — who `main` named — and the record is written at the first tick that follows them. Nothing is rewritten by that.
- **Four columns arrive through `ADDED_COLUMNS`** at boot, NULL for what was there; `SCHEMA_VERSION` stays 89.
- **The plain name is the schedule's name** from this deploy; nobody is plain until staff say so.
