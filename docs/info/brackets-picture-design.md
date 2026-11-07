# Bracket picture on the starter card

> **Audience:** Claude sessions and the owner. **Status:** TRACKED.
> **Last verified: 2026-11-07** on branch `brackets-picture` (off `main` `ed2d9424`): built and tested through
> Pillow and the thread fakes. ⚠️ **NOT checked:** nothing has met real Discord (how the embed image scales in the
> client, the upload on a forum `create_thread`, the edit replacing the attachment); not merged, not deployed.

The ask (owner, 2026-11-07 10:1x): *"We should also generate a bracket preview image in discord so people can see a
preview"* — decision **A**: the picture lives on the thread's starter card, redrawn as the tree moves, drawn while
seeding so the pairings show before the start. No Preview button.

## What and where

| Piece | Where |
|---|---|
| Pure renderer: `Bracket` + names + `Words` + per-set `Extra` → PNG bytes | `black_bloc/brackets/picture.py` |
| What to draw for a tournament, the fingerprint cache, the failure streak, the payload | `black_bloc/brackets_picture.py` |
| The ONE hook | `brackets_thread.starter_of` — every send, forum `create_thread` and edit of the starter goes through it |
| Font | `black_bloc/assets/fonts/Rajdhani-{Regular,Bold}.ttf` + `OFL-rajdhani.txt` (google/fonts `ofl/rajdhani`), in package-data |

A send carries `file=` and the embed's `image` is `attachment://bracket.png`; an edit carries `attachments=[file]`,
which REPLACES the message's attachments (never appends). With no picture, an edit carries `attachments=[]`, so
turning the key off or failing to draw takes the old picture away. *Move to #knuck-up*'s word on the old starter
drops it too. Drawing runs in `asyncio.to_thread`.

## The look

The site's tree (`bracket-layout.js` `eliminationLayout`, ported column for column as `elimination_layout`), in the
`blackbloc` theme's colours (page `#17110e`, card `#241a16`, hairline, muted, accent): one box per set keyed like the
page (W1-1, L2-3, G1-1), two slots with the score on the right, winner bold, loser muted, waiting sets dimmed to the
page's 0.55, border by state (ready / called / reported / disputed), connectors with finished feeders brighter, round
headings from the `brackets_round_*` keys. Double elimination: winners above, losers below, grand final(s) on the
right; third place under the final; round-0 play-ins in their own first column.

Round robin and Swiss (and the pools phase, one table per pool under `brackets_pool_title`) draw a table: rank, name,
W-L, points (= set wins). Title band: name, the kind pill, *format · state*, and *Champion: X* once complete.

Width 1600 px for 8+ entrants (Discord shows ~550, so it is drawn at about 2×), the natural width below 8 (1000 for a
table). Font size steps down with the column count (32 → 22, never under 18); long names are ellipsised to the box.

**Not drawn:** byes and void sets (as on the page), K3's `pending-*` feeders, the pools' sets once the final runs,
best-of, the set state words, a sports set's start time (`<t:…>` markup does not render in a picture), picks.

## When it redraws

Every starter edit asks for the picture; it is drawn only when the scene's fingerprint (sha256 of the exact data
drawn) differs from the last one drawn for that tournament, kept in memory on the bot (`_brackets_pictures`). A
restart draws once. Picks, check-ins and anything else that edits the starter without moving the tree reuse the
bytes (re-uploaded, not re-drawn). Before the start (draft/sign-ups/check-in/seeding) with 2+ active entrants the
picture is what Start would build from today's seed order (`play.build` / `pools.build`, never stored); a sports
bracket's Import/Build sets are drawn as stored.

## Keys (all `core`, CORE_KEYS 469 → 474)

| Key | Default | |
|---|---|---|
| `brackets_picture` | on | off = no picture anywhere |
| `brackets_picture_max_entrants` | 64 (4–256) | past it, no picture and one line on the card |
| `brackets_picture_too_big_line` | `No picture past {most} entrants: {count} are in` | that line |
| `brackets_picture_champion_line` | `Champion: {name}` | added beyond the brief: the picture's words are keys too |
| `brackets_picture_standings_head` | `#\|Name\|W-L\|Pts` | the table's four headings, split by `\|` |

## Failure

A drawing that raises leaves the card posting without a picture; `brackets.picture_failed` (IMPORTANT, by the
`_failed` suffix) is written ONCE per failure streak per tournament, and `brackets.picture_back` (ROUTINE) when it
draws again. Both are in memory, so a restart mid-streak can write one more `picture_failed`.

## Gate (branch `brackets-picture`)

- Checklist items that bit: **2** (the failure kind is distinct from the back kind and from a card failure),
  **11** (the starter's `allowed_mentions=none` kept), **12** (the picture is cosmetic: it never blocks the card),
  **15** (one renderer; the layout is a deliberate port of `eliminationLayout`, the JS stays the page's — two
  runtimes, documented NOT-interchangeable twins: change one, change the other), **22** (max entrants clamped 4–256),
  **33** (every decided default is a key), **37** (the draw and the cache write run inside the tournament's card
  lock that `sync` already holds).
- NOT verified: real Discord (scaling, upload size limits on a 64 bracket ~285 KB, forum posts), the Fly image
  build installing Pillow (the wheel was built locally only), memory of the cache on a busy server.
