# A post carries the front door — the rules and the "Need something?" box as ONE message

> ⚠️ **2026-09-27 — SUPERSEDED IN PART by [`post-blocks-design.md`](post-blocks-design.md) (branch
> `post-blocks`, BUILT, NOT MERGED).** ~~One switch per post: *Carry the front door*~~ → the front door is
> now the first **block** a post attaches (**Add a block…** / **Remove**, a `post_blocks` row, schema 78);
> `carries_door` stays as a column DERIVED from that row, so every door path below still reads true. The
> `/posts` card's *Carry the front door* button and the editor's switch are gone; ~~Deviation 5 (a re-word
> reaches the carrier on the next sweep)~~ still holds for a word changed on the Settings page, but saving
> from the Blocks editor redraws the carrier at once. Everything else here — the door riding the post's
> message, the mirrored keys, the refusals, the shadow table — is unchanged.

> **Audience:** the conductor, reviewers, and the next build that touches Posts or the front door.
> **Status:** TRACKED · 🔨 **BUILT on branch `post-carries-door`** (off `main` `91d1daa7`, v179 live),
> NOT merged, NOT deployed, the migration has NOT run on the live database. **Last verified:
> 2026-09-27** — by `pytest` (whole suite, `-n 16`), `ruff check .`, `node --check` on the touched
> JS, the mock's node tests, `node site/mock/check.mjs` against a mock from the worktree on 8822,
> and a headless render of the Posts editor. ⚠️ **NOT checked:** nothing here met Discord — no
> boot, no token, no message sent or edited, no button pressed in a client, no deploy; `TEST_MODE`
> and every mode key were left alone.

## The ask (owner, 2026-09-27 19:5x Phoenix, verbatim)

> *"is there a way we can combine the 2 post so the when rules is posted to welcome it also post
> the something needed box in the same post, we also dont need to pin it. it'll be the only thing in
> the channel. so set pin for that post to be off but let it be toggleable"*

The pin half was done by the conductor before this build (`welcome`'s `pin` = off; the per-post
toggle already existed). This build is the combining half.

## As built

**One switch per post: _Carry the front door_** (`posts.carries_door`, off by default). At most
ONE post in a guild carries it; switching it on for a second post is refused in words naming the
first (`DOOR_CARRIED_ELSEWHERE`, 409 `door_carried_elsewhere`). Both doors reach it: the Posts page
editor (a switch beside **Pin it**, saved with the draft through `PUT /api/posts/{slug}`
`carries_door`) and the `/posts` card (**Carry the front door / Do not carry the front door**, the
label is the move, through the same `save_post`). One press writes ONE `post.saved` row; a change
of the switch adds `carries_door` to its details (checklist 34).

**The message.** While a post carries the door and `frontdoor_mode` is not off, its published
message is the post's own words (plain content, or its own embed first) **plus the door's card
(`door_embed`) as the last embed, plus the door's persistent view (`door_view`)** — the same three
`door:<kind>:<guild>` buttons, so they survive a restart through the registered `DoorButton`
dynamic item. The door's words are still the door's keys (`frontdoor_title`, `frontdoor_text`, the
three labels, `rehearsal_note`). `posts.door_hash` records the door part as drawn (NULL when the
message carries no door); the status pills gain **carries the front door** once it is drawn.

**The door follows the message.** After a carrying publish, `door_rides_post` (a) takes down any
message the door had of its own — real (`frontdoor_message_id`) or rehearsal
(`frontdoor_shadow_message_id`) — that is not the post's; (b) mirrors the door's keys onto the
post: `frontdoor_channel_id` = the post's channel, `frontdoor_message_id` = its real message,
`frontdoor_shadow_message_id` = its shadow copy (so `where_the_door_is`, `door_takes_over`,
`rehearsal_copy`, `hide_ticket_button` and modmail's `_repanel` all resolve to the carrying
message); (c) hides modmail's own ticket button in that channel, as the door always has.

| Door path | With a carrier up |
|---|---|
| `post_door` into the post's channel (or the posts rehearsal home its shadow copy sits in) | Posts **nothing**, deletes **nothing**; answers `DOOR_RIDES_POST_SAID` (*"The front door rides **Welcome and rules** in #welcome, so nothing new was posted…"*). |
| `post_door` anywhere else | Refused, 409 `door_rides_post`, in words: turn **Carry the front door** off on that post first. |
| `take_door_down` / `DELETE /api/frontdoor/panel` | The post's message is **edited** without the door part (`embeds` = its own only, `view=None`), `carries_door` goes **off**, every door key is cleared; answers `DOOR_OFF_THE_POST_SAID`. Staff's final say both ways. |
| The five-minute sweep (`_redoor`) | `keep_the_ride`: if the door's words changed (stamp ≠ `door_hash`), the message is **edited in place** — only `embeds` + `view`, never `content`, so pending unposted post edits are NOT published by a door re-word; keys re-mirrored. Door switched off → the door part is removed and the keys cleared, but the post keeps carrying (switch the door back on and it returns). |
| `take_down_post` on the carrier | The message goes, and the door with it: keys cleared, one `frontdoor.taken_down` row (`with_post`), the answer adds *"The front door was part of that message, so it is down too — **Post it** puts both back."* The switch stays on. Because `frontdoor_channel_id` is cleared, the sweep posts no door of its own. |
| Switching carrying on for a post already up | The message gains the door at once (edit), the door's own message goes. Not up yet → *"joins this post's message the next time it is posted."* |
| Switching carrying off | The message loses the door part at once; `frontdoor_channel_id` is KEPT, so the door's sweep puts it back as a message of its own within five minutes (said in the answer). |

**Pin.** Unchanged: `_pin` runs on the combined message exactly as on any post's message; the
`welcome` post's pin is off, so the combined message is not pinned (tested both ways).

### Shadow — which mode decides

The **post's mode decides where the one message goes** (it is the post's message):

| `posts_mode` | `frontdoor_mode` | The one message | Door part |
|---|---|---|---|
| shadow | shadow | the posts rehearsal home (`posts_shadow_channel_id` → `shadow_channel_id` → …; #welcome-test today) | card + buttons, the card's **footer** is the rehearsal note (*"Rehearsal — this is where it would go: #welcome"*) |
| on | on | the post's channel (#welcome) | card + buttons |
| on | shadow | #welcome | card + buttons + the rehearsal-note footer (the buttons are live; the door said it is rehearsing) |
| shadow | on | the posts rehearsal home | card + buttons, no note |
| any | off | wherever the post goes | **no door part**; the switch is kept |

The note rides the door's card as a footer because the message's `content` belongs to the post.

## Deviations

1. **No new settings keys (registry stays 626).** The brief asked that every new word be a key.
   Nothing new is POSTED: the door part is drawn entirely from the door's existing keys. The new
   words are staff answers and panel labels (`DOOR_RIDES_POST_SAID`, `DOOR_RIDES_ELSEWHERE`,
   `DOOR_OFF_THE_POST_SAID`, `DOOR_CARRIED_ELSEWHERE`, `CARRYING_*_SAID`,
   `TAKEN_DOWN_WITH_DOOR_SAID`, `CARRY_THE_DOOR`/`DO_NOT_CARRY_THE_DOOR`, `STATUS_CARRIES_DOOR`) and
   follow the Posts and front-door modules' existing convention, where every such answer is a
   module constant. If the conductor wants them as keys, it is a mechanical follow-up.
2. **Two columns, not one**: `carries_door` and `door_hash` (schema 76 in one step). The door's
   re-render needs to know what the message already shows, and `posted_hash` describes the post's
   words, not the door's.
3. **The door's keys are MIRRORED onto the carrying message**, not computed. `where_the_door_is` is
   synchronous and read in many places (modmail's `_repanel`, `door_takes_over`); the mirror is
   re-derived by every publish and every sweep, so it cannot drift for longer than one sweep. The
   destructive door paths (`post_door`, `take_door_down`, `_redoor`) check for a carrier FIRST, so
   none of them can delete the post's message through a mirrored key.
4. **`posts.py` imports from the front-door cog inside four functions** (`door_parts`,
   `turn_carrying`, the carrying tails of `publish_post` and `take_down_post`). The cog already
   imports `posts` at module level; the door's persistent view lives in the cog. A deliberate
   function-level import, not a cycle at import time.
5. **A door re-word reaches the carrying message on the next sweep (≤ 5 min)**, the same as the
   door's rehearsal copy today; nothing re-renders on the settings write itself.
6. **Switching carrying OFF returns the door to its own message on the door's next sweep**, not in
   the same press — the press edits one message; posting a new one is the sweep's job (it already
   owns putting a missing door back, under its lock — checklist 37).
7. **The preview draws the door** under the post while the switch is on (`preview.post_message`
   sample `carries_door`; the mock's `PREVIEW_DRAW.post` mirrors it) — beyond the brief, so the
   editor shows what Discord will show.

## What was NOT verified

- ⚠️ Nothing met Discord: whether Discord accepts `content` + two embeds + the view in one send and
  one edit (it should — ≤ 10 embeds, ≤ 6000 characters total; the rules text is ~1,460 plus the
  door's card) is reasoned, not observed.
- The edit that keeps the post's own embed passes `message.embeds[0]` back — reasoned from
  discord.py's `Message.embeds`, exercised only on fakes.
- The live database has not run the 75 → 76 migration.
- The rehearsal copy of modmail's ticket button in #welcome-test coming down under the combined
  message (it should, through `hide_rehearsed_ticket_button`) was exercised only by the existing
  fakes, not in a channel.
- No second browser pass beyond the Posts editor (the Modmail page's Front door card was not
  re-looked at; it reads the mirrored keys).

## Live steps for the conductor (after merge + migrate + deploy)

1. Posts page ▸ **Welcome and rules** ▸ tick **Carry the front door** (Pin it stays off) ▸ **Save
   Changes** — or `PUT /api/posts/welcome` `{"carries_door": true}`. Expect *"… The front door now
   rides this post's message."* if the rules are already up in #welcome-test.
2. **Update the post** (republish `welcome`). With `posts_mode` and `frontdoor_mode` both shadow,
   the message goes to #welcome-test.
3. Confirm **#welcome-test shows ONE message**: the rules text, then the *Need something?* card
   with its rehearsal-note footer, then the three buttons; the door's separate rehearsal copy is
   gone; nothing is pinned. Press **Ask staff privately** — the ticket form opens.
4. Logs: `web.post.saved` (`carries_door: true`), `web.post.shadow_updated`,
   `web.frontdoor.rides_post`.
5. Reversal if wanted: untick the switch (the door returns to its own message within five minutes)
   or Modmail page ▸ Front door ▸ **Take it down** (the rules stay, the door goes, the switch
   goes off).
