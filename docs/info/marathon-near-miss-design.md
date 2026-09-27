# Near misses ask staff in the thread — a runner whose name IS a member's username

> **Audience:** the conductor, reviewers, and the owner. **Status:** TRACKED · 🔨 **BUILT 2026-09-27 on branch
> `marathon-near-miss` (worktree `C:/lcw/bb-marathon-near-miss`, off `main` `7f7b99e7`, v178 live), NOT MERGED, NOT
> DEPLOYED.** Nothing has met Discord or Fly.
>
> **Last verified: 2026-09-27** — against the branch's own code by its tests (`tests/test_marathon_near_miss.py`,
> `tests/cogs/content/test_marathon_near_miss.py`), the whole suite, `ruff`, and `node site/mock/check.mjs` against a
> mock from the worktree on port 8821. **NOT checked:** a real Discord thread, the persistent buttons across a real
> restart, the live SS4C data, the site's People card (unchanged — see Deviations).

## The owner's words (2026-09-27 15:0x, verbatim)

> *"Speed stuff had cassasaur on streaming doctor Mario and Tetris. Hype piece Cass is the discord visible name. We
> didn't catch that"*

What happened (measured by the conductor): SS4C marathon #6's People answer listed runner `cassasaur` with
`member: false` and `looks_like: {username: "cassasaur", user_id: "909587042609025034"}`. The bot SAW that a member's
Discord username equals the runner's Twitch login, but only a Twitch link (or a staff pairing) counts as BaF — and the
near miss was shown only on the site's People card, which nobody watched during the run. Cass (he/they) has since been
paired everywhere by the conductor (pairing id 1).

## As built

**Who gets a post** (`black_bloc/marathon_near_miss.py:exact_match`). A person on the schedule (grouped by
`marathon_people.group_people`, dropped runs left out) who:

- is not already a member (no `user_id` — not linked, not paired, not name-matched);
- counts as BaF-able: has a **runner** part, or any part while `marathon_match_hosts` is on (a pairing for a host does
  nothing with that key off, so asking would be a lie);
- has a Twitch login OR a schedule name that equals a member's Discord **username** outright, case-insensitive (no
  squashing, no one-edit, no underscore head) — AND `marathon_people.looks_like` agrees for that username, so the post
  is always a subset of what the People card already calls a near miss.

Fuzzy near misses (`peasplay` vs `peasplays`, `gz` vs `gz_hero`, `cassa_saur` vs `cassasaur`) stay on the People card
only.

**Where and when** (`black_bloc/cogs/content/marathon_near_miss.py:sync_near_misses`). Called by
`Marathons.sync_board` after the runner posts, so every board sync (the tick's follow, a read, a pairing) runs it.
Nothing happens unless `marathon_near_miss_posts` is on, `marathon_mode` is not off and the marathon is **tracked**
(`marathon_inbox.is_tracked`). The post goes out through `Marathons._send` — the marathon's staff thread, or in shadow
the rehearsal home with the shadow note, exactly as the thread's other posts. `allowed_mentions` is none: the member is
named as `<@id>` and never pinged.

**Once per runner per marathon per place.** Each post is an action-log row (`marathon.near_miss_posted`, or
`marathon.would_post_near_miss` in shadow) carrying `marathon_id`, `runner`, `runner_key` (`person_key`: the login,
else the name), `member_id`, `username`, `message_id`, `channel_id`. A runner with a row for the current post place is
skipped; a runner with ANY answer row is never asked again on that marathon, whatever the place.

**The words** — every one a key (Marathons group, registry + mock row + label):

| Key | Default |
|---|---|
| `marathon_near_miss_posts` (bool, **on**) | — |
| `marathon_near_miss_post` | `**{runner}** on the schedule looks like {member} ({display_name}) — link them?` |
| `marathon_near_miss_link_here` | `Link (this marathon)` |
| `marathon_near_miss_link_everywhere` | `Link everywhere` |
| `marathon_near_miss_not_them` | `Not them` |
| `marathon_near_miss_linked` | `**{runner}** is {member} ({display_name}) on **{marathon}** — linked by {staff}.` |
| `marathon_near_miss_linked_everywhere` | `**{runner}** is {member} ({display_name}) on every marathon — linked by {staff}.` |
| `marathon_near_miss_dismissed` | `**{runner}** is not {member} ({display_name}) — {staff} said so, and **{marathon}** will not ask again.` |
| `marathon_near_miss_dismissed_said` | the ephemeral answer after Not them |
| `marathon_near_miss_gone` | the refusal for a press on a post with no record |
| `marathon_near_miss_answered` | the answer for a press after staff already answered |

Fields: `{runner} {member} {username} {display_name} {marathon}`, plus `{staff}` on the three outcome lines.
`{display_name}` is the member's server display name (Cass), falling back to the username.

**The buttons** (`NearMissButton`, a `DynamicItem` registered in `Marathons.cog_load`, custom id
`marathon:nearmiss:<marathon_id>:<here|everywhere|not>`, so they outlive a restart). The pressed message's id finds the
post's row. Guard check, then `still_staff` (the standing staff refusal), then the database check.

| Press | Writes | Then |
|---|---|---|
| **Link (this marathon)** | `pair_runner(…, runner, member_id)` — the ONE canonical pairing path (rematch, sync_runs, sync_board) | The runner's run is now ours, so the runner post appears in the same `sync_board` the pairing ran |
| **Link everywhere** | `pair_runner(…, everywhere=True)` | the same, on every marathon |
| **Not them** | nothing but the answer row | nothing is linked |

Every press then writes `marathon.near_miss_resolved` (`outcome` here / everywhere / not, `staff`, the post's ids) and
edits the post to the outcome line with its buttons removed (`view=None`), still `allowed_mentions` none; a shadow post
keeps its shadow note. A second press (another staff member, a stale client) answers *already answered* and re-edits
the post to the recorded outcome — nothing is paired twice.

**Where dismissals live:** the `action_log` table — `marathon.near_miss_resolved` rows with `outcome = "not"`, read
back with `json_extract(details, '$.marathon_id')` (the pattern `selftest.py` already uses). No schema change.

**Staff keep the final say.** Link is undone by Unlink in People… (or `/marathon unpair`); Not them is overridden by
linking from People… — the dismissal only stops the thread asking again.

**Log kinds:** routine `marathon.near_miss_posted`, `marathon.near_miss_resolved`; shadow
`marathon.would_post_near_miss`; `marathon.near_miss_failed` IMPORTANT by suffix. The pairing itself logs
`marathon.paired` as before.

## Deviations

1. **State is action-log rows, not a table or column.** The brief said "store dismissals in an existing place". The
   `marathon_people` pairings table needs a real `user_id`, and a sentinel there would feed `match_people`; the
   marathon row has no free JSON column. The action log is append-only and never pruned, so it doubles as the record;
   the cost is one indexed-by-guild scan filtered by kind and `json_extract` per sync of a marathon that has an exact
   near miss (none otherwise — the scan runs only when an exact match exists).
2. **"Once per runner per marathon" is per post PLACE.** A post made in the shadow home does not stop the real thread
   getting one when `marathon_mode` goes on (the runner posts' own rule). An answer is per marathon, whatever the place.
3. **The site's People card is unchanged.** A dismissed near miss still shows its `looks_like` there; the brief asked
   only for the thread post. Hiding it would be a follow-up.
4. **Hosts are asked only when `marathon_match_hosts` is on** (not in the brief; a host pairing does nothing with the
   key off).
5. **The link pairs the person's first schedule name**, exactly as People… ▸ Link does; a person listed under two
   different names with one login has the second name unpaired.

## What was NOT verified

- Nothing has met Discord: a real thread post, a real press, a real `interaction.message`, a real `view=None` edit
  removing the components, or the buttons surviving a real restart.
- The live SS4C data: Cass is already paired, so SS4C #6 would post nothing now.
- The cost of the `json_extract` scan on the live action log (size not measured).
- Shadow presses were not exercised by a test (shadow posting was).
