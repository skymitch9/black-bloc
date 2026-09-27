# Marathon public highlights — each BaF runner highlighted where members can see it; the thread stays staff-only

> **Audience:** the conductor, reviewers, and the next session touching marathon threads, runner posts, go-live or the
> marathon drawer. **Status:** TRACKED · 🔨 **BUILT on branch `marathon-public-highlights` (off `main` `f8494278`, the
> merged, undeployed runner-posts; v177 live), NOT merged, NOT deployed** — meant to ship with runner-posts as v178.
> Schema **74 → 75**, registry keys **578 → 597**, API routes unchanged (**264**; the contract gained one PATCH body
> entry, so `check.mjs` counts **265** entries), six new routine log kinds plus two shadow twins and one `_failed`;
> deviations below.
> **Last verified: 2026-09-26** — against the branch's own code by the tests (`tests/cogs/content/test_marathon_public.py`,
> `tests/test_marathon_public.py`, the PATCH test in `tests/api/tools/test_marathons.py`, the schema-75 test in
> `tests/storage/test_db.py`, the fourth-button assertions in both `test_marathon_thread_controls.py`), the whole suite,
> `check.mjs` on a worktree mock (`MOCK_PORT=8818`: *22 pages, 265 routes, 25 core settings, all keys present*), and a
> headless render (`chrome-headless-shell` 149.0.7827.22 over CDP, against the mock): the Settings row *Where a BaF run's
> public highlight goes* draws a channel select whose categorised options read `# name · Category`, and the marathon
> drawer's Settings fold draws *Auto-highlight BaF runners when live* under *Ping the marathon role*; pressing On + Save
> set `public_highlight` true; zero console errors. ⚠️ **NOT checked:** anything against Discord (the button on a real
> runner post, a real post in go-live, a role ping, a restart with real components), the live database and its migration,
> the live marathons (SS4C); the bot was never run. Secret NAMES only.

## The ask, verbatim (owner, 2026-09-26 20:3x–20:4x Phoenix)

1. *"We also want an option that says repost in go live if a BaF runner is live, is that already built out"*
2. ⚠️ **The revision that replaced the repost-only design:** *"To give context nobody can see the events thread except
   staff, we use it to control events. We need a way to highlight each [runner] in go live if we want to. Or somewhere
   else. Have that channel be changeable. Go live for now."*

The marathon threads in **# events · BlackMail** are staff-only — the control room. Everything the marathon feature has
posted there (the board, the runner posts, the shoutouts, the reminders) is seen by staff alone. This build gives staff a
way to put one runner in front of members, and a per-marathon switch to do it by itself at the moment a run goes live.

## As built

**(1) Where it goes — `marathon_public_channel_id`** (channel, blank = `golive_channel_id`; Marathons group; registry +
mock row + label; the Settings page's channel select uses the shared `channelLabel`, so it reads `# name · Category`).
`cogs/content/marathon_public.py:public_channel` is the one resolver. Changing it re-labels every runner post's button on
the next tick and sends the NEXT highlight there; a highlight already up stays where it was posted and keeps being edited
there (Deviation 2).

**(2) The button on each runner post** (`HighlightButton`, a `DynamicItem` registered in `Marathons.cog_load`; custom id
`marathon:highlight:{marathon_id}:{run_id}:{post|remove}`, so it answers after a restart). The runner post (the
`marathon-runner-posts` build) now carries one button, decided by `marathon_public.button_for`:

| The run | The button |
|---|---|
| a highlight is up (posted, not taken down) | **Remove the highlight** (`marathon_public_button_remove`) |
| BaF, upcoming / live / done, a public channel resolves | **Highlight in #<channel>** (`marathon_public_button_post`, `{channel}` = the current public channel's name) |
| otherwise (dropped, unlisted, no public channel) | no button — a move renders only when valid |

- **Highlight** (`press` → `highlight_now` → `post_highlight`), staff-gated by `still_staff` (the standing worded refusal),
  deferred, answered privately, under the marathon lock: posts `marathon_public_template` in the public channel now,
  stores `marathon_runs.public_message_id` / `public_channel_id`, `public_removed = 0`, and re-renders the runner post
  (`sync_posts`), whose button becomes **Remove the highlight**. Refused in words for a run dropped or unlinked
  (`marathon_public_not_postable`) and when no public channel resolves (`marathon_public_no_channel`); a send that fails
  answers `marathon_public_failed` with the reason and logs `marathon.public_highlight_failed`. Pressed on a run whose
  highlight is up: *already up*, nothing changes.
- **Remove the highlight** (`remove_highlight`): **deletes nothing.** `public_removed = 1` is stored first, then the public
  message is edited to `marathon_public_removed` (*Staff took down the highlight for **{runner}** on **{marathon}**.*) with
  no mentions, and it is never edited again. The runner post's button goes back to **Highlight**.
- **Staff final say both ways:** Highlight after a Remove edits the SAME message back to the live words (logged
  `marathon.public_highlight_restored`) when it is still in the channel a highlight would go to now; otherwise it posts a
  new one.
- **Edited in place** (`sync_highlights`, called from `Marathons.sync_board` after the runner posts, so every door that
  refreshes the board — the fetch, the minute follow, Shout it now, Mark live/done/upcoming, pair/unpair — also moves the
  highlight): the slot moves (`{when}`), it goes live, it is done, it is dropped. The words are the runner post's own
  fields (`marathon_runner_posts.post_text`) — `{runner}`, `{mention}`, `{game}`, `{category}`, `{part}`, `{when}`,
  `{relative}`, `{url}`, `{marathon}`, `{state}` — so the state words are the existing `marathon_state_*` keys, reused.
  An unchanged tick costs no Discord call (`cog.public_sent`); after a restart each highlight that is up is fetched once.

**(3) The per-marathon switch — Auto-highlight BaF runners when live.** `marathons.public_highlight INTEGER NOT NULL
DEFAULT 0` (schema 75). A new marathon copies the guild key `marathon_public_highlight_default` (bool, **off**) at
creation (`create_marathon`); every marathon already on the list is off. One writer, `set_public_highlight` (words
`marathon_public_auto_on_said` / `_off_said` / `_same_said`; logs `marathon.public_highlight_set` `from`/`to`/`via`), and
three doors reach it:
- a **fourth button on the pinned thread control message** — `marathon:controls:{id}:highlight:{on|off}`, labels
  `marathon_controls_highlight_on` / `_off` (*Auto-highlight BaF runners when live: on · turn off* / *…: off · turn on*),
  green when on, grey when off, carrying its target like the other three;
- the **drawer's Settings fold** — a segmented On/Off beside *Ping the marathon role*, riding **Save** exactly as the ping
  switch does;
- **`PATCH /api/marathons/{id}`** with `public_highlight` (a bad word → 422 `bad_public_highlight`); the row carries
  `public_highlight`.
The writer calls the controls' canonical hook (`controls_changed`) after it writes, so the pinned message re-renders from
any door.

**When it is on**, `auto_highlight` runs inside `Marathons.shout` — the moment the shoutout fires, before the
said-by-its-event skip, for every caller (`advance` when the schedule or the title flips a run live, Mark live, Shout it
now): a tracked marathon with the switch on, a BaF run that is upcoming/live/done, and **no highlight ever posted for
that run** (so a highlight staff took down is never put back by the switch). A failure there is a log line and never
breaks the shoutout.

**(4) Pings and shadow.** A highlight's first post pings through `Marathons._ping_roles` — the runner's fan role and the
channel's through its ping-window gate — which returns nothing unless that marathon's `ping_role` is on. With it on, the
roles are prefixed and are the only mentions allowed (`users=False`, `everyone=False`); otherwise
`AllowedMentions.none()`. Every edit (moves, live, done, taken down) mentions nobody. `marathon_mode` governs it: **off**
posts nothing (Highlight answers *could not post: marathon posts are off*); **shadow** sends the highlight to its **own
rehearsal home** — a new feature home **`marathon_public`** (`marathon_public_shadow_channel_id`, blank =
`shadow_channel_id`, `shadow.py`'s chain) — with the rehearsal note naming the real public channel, and logs
`marathon.would_post_public_highlight` / `would_edit_public_highlight` with `shadow_home`.

**Every word a key** — sixteen words (Marathons group, registry + mock row + label): the template, the taken-down line,
the two button labels, seven answers (`posted_said`, `removed_said`, `already_up`, `not_up`, `no_channel`, `failed`,
`not_postable`), the three switch answers and the two control-button labels. The one PATCH refusal (`bad_public_highlight`)
is a module constant, as the ping switch's is (it is a site answer, not a posted word).

**Log kinds:** routine `marathon.public_highlight_posted` (`auto`, `pinged`, `roles`, `channel_id`, `via`),
`_edited`, `_restored`, `_removed` (`edited`), `_lost`, `_set`; shadow `marathon.would_post_public_highlight`,
`would_edit_public_highlight`; `marathon.public_highlight_failed` (`step: post | edit | remove`) IMPORTANT by suffix.

## Deviations

1. **Three run columns and one marathon column** (`marathon_runs.public_message_id INTEGER`, `public_channel_id INTEGER`,
   `public_removed INTEGER NOT NULL DEFAULT 0`; `marathons.public_highlight INTEGER NOT NULL DEFAULT 0`; schema
   **74 → 75** via `ADDED_COLUMNS`, mirrored to both archive twins by the boot rule). `public_removed` is the brief's
   *"unless staff removed it"* — the message id alone cannot tell a highlight staff took down from one still up.
2. **A channel change moves the NEXT highlight only.** One already up keeps being edited where it was posted (its stored
   channel), and Highlight-after-Remove puts a message back in place only when it is in the channel a highlight would go
   to now — otherwise it posts fresh in the new channel and the old taken-down line stays.
3. **Highlight after Remove re-uses the message** (edits it back) instead of posting a second one — no duplicate in the
   public channel. The ping prefix is not re-sent on that edit.
4. **Edits drop the ping prefix.** The first post carries the role mention (when `ping_role` is on); the edits as the run
   moves carry the template only — the shout's own done-edit does the same. The compare is `endswith(text)`, so a post
   that still carries its prefix is not edited for that alone.
5. **The auto path is hooked in `shout`, not in `advance`.** One place covers the schedule, the title, Mark live and
   Shout it now. It runs before the *said by its event* skip, so a run whose own event announces it is still highlighted
   publicly (the event announcement goes to the events channel, not the public one). A run whose shout already exists is
   not shouted again, so a run marked upcoming and live again does not re-trigger the switch.
6. **A highlight a person deleted by hand is forgotten, not re-posted** (`marathon.public_highlight_lost`: its id and
   channel are cleared, `public_removed` stays 0); the runner post's button reads **Highlight** again. A transient fetch
   failure (not NotFound) leaves everything as it was.
7. **Updates run only while the marathon is tracked and `marathon_mode` is not off** — they ride `sync_board`, which the
   tick skips in those states. **Remove** is not gated: it stores the decision and edits the message whatever the mode.
8. **The button shows only when valid** (the panels rule): no public channel resolving, or a run dropped/unlinked, draws
   no button at all rather than a disabled one. A highlight that is up always shows **Remove** — staff can always take
   it down.
9. **The label names the channel by its Discord name**, falling back to the id when the bot cannot see the channel.
10. **Shadow home is a new feature home, `marathon_public`**, not the marathon one: the public highlight rehearses where
    staff point it, apart from the thread's rehearsals. Blank follows `shadow_channel_id` as every feature home does.
11. **Runner-post compare after a restart:** the runner post's cached value now includes its button; after a restart the
    compare also reads the fetched message's components (`marathon_public.shown_button`). A message whose components
    cannot be read is edited once.
12. **No `/event` or `/settings` twin for the per-marathon switch beyond the thread button and the site** — the thread's
    control message is the Discord door, like the other three controls. The guild keys are reachable from both the
    Settings page and the `/settings` panel as every registry key is.

## What was NOT verified

- ⚠️ **Nothing met Discord.** The button on a real runner post, the press, the post in go-live, the role ping, the edits,
  the taken-down line, the fourth control button, and a real restart with real message components were exercised against
  the suite's fakes only.
- ⚠️ **The live migration (schema 75) has not run**; every live marathon will read `public_highlight = 0` and every run
  empty until staff press.
- **The go-live channel's own behaviour** (auto-publish, slow mode, who can see it) was not read; the highlight is a
  plain bot message there.
- **The site** was rendered headlessly against the mock only (the Settings row and the drawer switch); the Discord-side
  words were checked by the tests.
- **Open question left for the owner** (recorded in the TODO item, not built): reminders (*X is up in 15 min*) still post
  only in the staff thread.

## Follow-up — public reminders + ping button (2026-09-26)

> **Status:** 🔨 **BUILT on branch `marathon-public-reminders` (off `main` `59e71860`: v177 live, runner-posts +
> public-highlights merged and undeployed), NOT merged, NOT deployed** — meant to ship with them as v178. Schema
> **unchanged at 75** (no migration). Registry keys **597 → 602** (measured: `len(settings_store.KEY_TYPES)`). API routes
> and the contract unchanged (`check.mjs`: *22 pages, 265 routes*). **Last verified: 2026-09-26** by the tests
> (`tests/cogs/content/test_marathon_public_reminders.py`, the fifth-button tests in both `test_marathon_thread_controls.py`),
> the whole suite, and `check.mjs` on a worktree mock (`MOCK_PORT=8819`). ⚠️ Nothing met Discord; no browser rendered the
> new Settings rows.

**The asks, verbatim.** Owner 20:5x: *"Champ is up in 15 minutes will go in go live for now but we may move it. Make sure
where the shoutouts post to is a separate key in settings so I can set it to a different channel from the spotlight post.
So champ is up can be post separate channel from the marathon channel post in go live"*. Owner 21:0x, *"Yes perfect"*, to a
fifth button on the pinned thread control message: **Ping the marathon role: on / off**.

### As built

**(1) Public reminders.** Three destination keys, three Settings rows (Marathons group), each blank → `golive_channel_id`:

| Key | What goes there | Resolver |
|---|---|---|
| `golive_channel_id` | the go-live spotlight / stream post (unchanged; read directly by `cogs/content/golive.py`) | — |
| `marathon_public_channel_id` | runner highlights (the previous build) | `marathon_public.public_channel` |
| `marathon_reminder_channel_id` (**new**, channel) | the public copy of every reminder (*X is up in N min*) | `marathon_public_reminders.reminder_channel` |

The fallback chain is the only link: each resolver reads its own key, then go-live; setting one never changes what the
others resolve to (tested). Every reminder of a TRACKED marathon (`Marathons.remind` returns early for any other) now
calls `post_public_reminder` right after the staff-thread copy in `_post_reminder`; the staff copy is exactly as before.

- **Words:** `marathon_public_reminder_template` (new; default identical to `marathon_reminder_template`, the same fields),
  so the public copy can be worded apart from the staff one.
- **Switch:** `marathon_public_reminders` (bool, **on**) — off keeps reminders in the staff thread only (the
  configurable-both-ways rule: the decided default is a key).
- **Pings:** the public copy carries exactly the staff copy's roles — the `marathon_ping_minutes` mark, with
  `marathon_reminder_pings` on, through `Marathons._ping_roles`, which is empty unless that marathon's `ping_role` is on.
  With roles, only those roles are allowed; otherwise `AllowedMentions.none()`.
- **Shadow:** reuses the **`marathon_public`** rehearsal home (`marathon_public_shadow_channel_id`, blank =
  `shadow_channel_id`) — no new home key; the home's description now reads *public highlights … and its public
  reminders*. The note names the real reminder channel. Mode off posts nothing.
- **No double post on restart:** no message id is stored. The reminder's existing sent-marker (`marathon_runs.reminders_sent`)
  is written BEFORE either copy is sent, and the public copy is sent in the same call, so a restart never re-sends it.
- **Logs:** routine `marathon.public_reminded`, `marathon.public_reminder_skipped`; shadow `marathon.would_remind_public`;
  `marathon.public_reminder_failed` IMPORTANT by suffix (also for *no channel at all*).

**(2) The fifth control button — Ping the marathon role.** `marathon:controls:{id}:ping:{on|off}` (`mtc.PING`, the
template grew `ping`), labels `marathon_controls_ping_on` / `_off` (*Ping the marathon role: on · turn off* / *…: off ·
turn on*), green when on, grey when off, carrying its target like the other four. A press goes to
`marathon_ping.set_ping_role` — the controls build's one writer, so the drawer, the `/event` card and the thread agree —
staff-gated by `still_staff` (the standing refusal), answered with the writer's own `marathon_ping_role_*_said` words.
`set_ping_role` now calls `controls_changed` after it writes, so a change from ANY door (drawer/PATCH, `/event` card,
the button) re-renders the pinned message.

### Deviations

1. **A fifth key beyond the brief: `marathon_public_reminders`** (bool, on) — a way to stop the public copy without
   blanking go-live. Keys: channel + switch + template + two labels = **5**.
2. **A separate public template** (`marathon_public_reminder_template`) rather than re-using the staff one, so the public
   words can differ; its default is the staff template's text.
3. **Same-channel skip.** A tracked marathon with no thread posts its staff copy in the marathon channel, which is itself
   blank → go-live; the public copy would land beside it word for word. When the staff copy's real destination (its
   thread, or the marathon channel it stands for — `staff_went_to`) IS the reminder channel, the public copy is skipped and
   logged `marathon.public_reminder_skipped` `because: same_channel`. This also kept every existing reminder test green.
4. **Shadow home reused** (`marathon_public`), not a new `marathon_reminder` home.
5. **No new PATCH field or drawer control**: `ping_role` already had both; the fifth button is the Discord door.
6. **The drawer's ping help line** (`PING_HELP` in `marathons-section.js`, a site string) now says the public reminder copy
   and public highlights follow the switch too.
7. **A public-copy failure never touches the staff copy** — it is wrapped and logged; the staff log line is written as
   before.

### What was NOT verified

- ⚠️ **Nothing met Discord**: a real public reminder in go-live, a role ping there, the fifth button on a real pinned
  message (five buttons fit one action row; not seen rendered), a restart with real components.
- **The Settings page rows were not rendered in a browser** — `check.mjs` confirms the keys are present in the mock; the
  `# name · Category` picker is the shared `channelLabel` every channel row uses, not re-checked by eye for these rows.
- **The go-live channel's own behaviour** (slow mode, auto-publish) with reminders added — not read.
- **Volume:** with the default marks (`120, 15`) every BaF run adds two public posts; not measured against a real
  marathon's run count.
