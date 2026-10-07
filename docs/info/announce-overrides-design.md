# Announce overrides — hosts off by default, a per-run answer for each person, and a no-@ choice

> 🔴 **THIS CHANGES LIVE BEHAVIOUR AT DEPLOY.** Every marathon whose own **Host announcements** switch follows the
> setting — which is **every marathon at deploy**, because the column is new and reads NULL — **stops announcing its BaF
> hosts**: no host-block heads-up at any mark and no host highlight. Runners are unchanged. A host highlight already up
> is carried to *done*. To keep a marathon's hosts announced, turn its **Host announcements** on (thread controls, the
> drawer, or `PATCH`), or set `marathon_host_announcements_default` on for the whole server. ⚠️ The live rows were NOT
> read by this build; the rule above is what applies to them.

> 🔨 **BUILT 2026-10-06 on branch `announce-overrides` (worktree `C:/lcw/bb-announce-overrides`, off `main`
> `2c2a256b`), NOT MERGED, NOT DEPLOYED.**
>
> **Audience:** the conductor, reviewers, and the next session touching marathon reminders, highlights, host blocks,
> the runner post's buttons, the thread controls or the People card. **Status:** TRACKED. **Last verified:
> 2026-10-06** — against the branch's own code by the suite (`tests/test_marathon_announce.py`,
> `tests/cogs/content/test_marathon_announce.py`, the new tests at the foot of `tests/api/tools/test_marathons.py`,
> `tests/cogs/content/test_marathon_people.py`, `tests/cogs/content/test_marathon_thread_controls.py`,
> `tests/storage/test_db.py`), `ruff check .`, `node site/mock/check.mjs` on `MOCK_PORT=8802`, every
> `site/mock/*.test.mjs`, and one rendered look at the mock's AGDQ 2027 drawer in Chrome (the Host announcements field,
> the People card's per-run line and its button pressed once). ⚠️ **NOT checked:** anything against Discord, the live
> database, the live settings. Secret NAMES only.

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
when any run of it goes live. `marathon_announce.block_people` weighs the host **as a host on every run of the block**.
So *Announce X for this run* on any run of a four-run block announces the block once; leaving them out of every run
silences it.

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
- Hosts are still FOUND, matched and shown exactly as before: no change to matching, the People view, the runner posts
  or `marathon_hosts_count_as_ours`.

## 2. A run's own answer for each person

- **Storage: `marathon_runs.announce_people TEXT`** — a JSON object `{user_id: "in" | "out"}` on the run row; no entry
  means *follow the defaults*; NULL once it is empty.
- **One writer, `cogs/content/marathon_announce.set_run_answer`** (under the marathon lock). It posts nothing. Refusals
  in words: 422 `bad_announce` for a word it does not know, 404 for a run that is gone, 404 `not_on_run` for someone
  who is not BaF on that run. On a change it logs `marathon.announce_run_set` (`run_id`, `game`, `member`, `from`,
  `to`, `via`) and follows the highlights the way the marathon-wide opt-out does:
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
- **More than four people** on a run (Discord takes five rows): the buttons become ONE menu
  (`marathon:announce:{marathon_id}:{run_id}:pick`, `AnnouncePick`, placeholder `marathon_announce_pick`) holding the
  same moves, at most 25 options (twelve people); anyone past that is reached from the site.
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
- When a person is *plain*, every public post about them on that marathon writes their **server display name as plain
  text**, markdown- and mention-escaped (the schedule's name when they are not in the server), wherever the template
  says `{member}` / `{mention}`. Timing, role mentions and everything else are unchanged. Runners and hosts alike; two
  people on one run each follow their own.
- **One writer, `set_mention`.** It logs `marathon.mention_set` (`member`, `from`, `to`, `via`) and re-renders what is
  up in place: highlights (runner and host) and every reminder still being followed. Nothing new is posted.
- The staff thread's own posts and reminder copy are not public and keep the `<@id>` text.

## What is stored, what is counted

| | Added |
|---|---|
| Columns (`ADDED_COLUMNS`, no `SCHEMA_VERSION` step — it stays **89**) | `marathons.host_announcements INTEGER`, `marathons.mention_people TEXT`, `marathon_runs.announce_people TEXT` (mirrored to the two archive tables at boot) |
| Tables | none |
| Registry keys | **867 → 893 (+26)**: `marathon_host_announcements_default`, `marathon_mention_people`, `marathon_controls_host_announcements_on` / `_off`, `marathon_host_announcements_on_said` / `_off_said`, `marathon_announce_button_run_out` / `_run_in` / `_run_default` / `_plain` / `_mention`, `marathon_announce_pick`, `marathon_announce_state_line` / `_state_yes` / `_state_no` / `_state_plain`, `marathon_announce_why_default` / `_why_run` / `_why_marathon` / `_why_off` / `_why_hosts_off`, `marathon_announce_run_in_said` / `_run_out_said` / `_run_default_said`, `marathon_mention_plain_said` / `_on_said`. Two defaults reworded: `marathon_public_button_opt_out` / `_opt_in` |
| Log kinds | **+3** routine: `marathon.host_announcements_set`, `marathon.announce_run_set`, `marathon.mention_set` (+ their `web.` twins through `kind_via`) |
| Contract | **312 → 315 entries (+3)**: the two new routes and one more `PATCH` variant; `action_kinds` +3 |
| Thread controls | **6 → 7** buttons (8 with Event schedule), + the link button |
| Dynamic items | +2 (`AnnounceButton`, `AnnouncePick`) |

## Decisions beyond the brief

1. **A post already up is followed with the master forced on** (`standing`): BaF announcements going off stops new
   posts and never rewrites or strands one in flight (the behaviour before this build, kept).
2. **Host announcements going off while a host post is up carries it** with everyone on it who is not left out by
   name. A later per-person move on that block is weighed with the real switch (`carried=False`), so pressing *back to
   the default* on the only run that announced a host takes their highlight down.
3. **A host who also runs a run of their own block does not announce the block by default** — the block weighs them as
   a host; that run's reminder still names them as a runner.
4. **The run's answer and the @ are separate moves**, two buttons a person, so four people fit as buttons.
5. **Per-run buttons and the state lines show only while the run is upcoming or live**; a finished run's post keeps the
   whole-marathon button only.
6. **With the master off the per-run button still offers the move the defaults would allow** (it stores the answer for
   when the master comes back); the state line says *BaF announcements are off for this marathon*.
7. **The site's button words** *Opt out of every run* / *Opt back in to every run* are site chrome constants (the
   existing convention); the per-run and @ labels come from the keys.
8. **Refusals are module constants** (`BAD_RUN`, `NOT_ON_RUN`, `BAD_MENTION`) — the existing refusals' convention.
9. **The default highlight template names people with `{runner}`** (bold, no @), so the no-@ choice shows on a
   highlight only when staff's template uses `{mention}`; the default reminder template uses `{member}` and always
   shows it.
10. **A reminder whose run is already live or done is not rewritten** when the @ choice changes (edit-in-place rule 5),
    and nothing is rewritten while `marathon_reminder_on_move` is `repost`.

## What is NOT built

- No per-run answer for a whole block in one press; no bulk move across runs.
- No migration of data: every existing row reads *follow the defaults*.
- The role-mention logic (`marathon_role_ping`) is untouched; branch `baf-event-ping` owns it.
- The archive's read-only board does not show the per-run state.

## What was NOT verified

- ⚠️ **Nothing met Discord**: the run post with five buttons or a menu, a real press, the seven-button controls.
- **The live database and settings were not read**; which live marathons have BaF hosts is not known here.
- **The menu's layout past twelve people** is truncation by design and was tested only as a count.
- The site was rendered on the mock only (one drawer, one press); the real API under a browser was not.
- The tests were written after the code; four mutations of the decision (host default on, master ignored, the run's
  yes not passing the opt-out, the plain name ignored) were each seen to fail them.
