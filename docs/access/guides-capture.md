# Guide screenshots — the capture session, step by step

> **Audience:** a Claude session with Claude in Chrome, after a deploy. **Status:**
> TRACKED — ⚠️ **secret NAMES only.** **Last verified: 2026-09-16** — written at the G2
> build (branch `guides-pages`) and checked against the code it names:
> `black_bloc/api/tools/guides.py` (`GET /api/guides/stale`, `POST /api/guides/{slug}/media`),
> `black_bloc/guides.py` (`MEDIA_BYTES_MAX` 2 MB, `MEDIA_SIDE_MAX` 1600, `media_root`),
> `site/public/assets/page-guides.js` (**Replace screenshot…**), `scripts/deploy.ps1` and
> `scripts/release_json.py` (`release.json`), `docs/access/operator-read.md`
> (`scripts/read.ps1`).
> 🔴 ⚠️ **NEVER DRILLED.** No session has run this end to end: no browser has been opened
> at Discord for it, no `/api/guides/stale` has been read against the live app, no picture
> has been cropped by `crop_shot.py` on a real capture, and nothing has been uploaded to a
> live guide. Every sentence below is written from the code, not from having done it.
> **The first session to follow it owns correcting it**, and dating a drill line at the foot.

## What this is for

A guide step carries at most one picture. A picture goes **stale** when the feature it
shows has changed since it was taken — the deploy writes which features changed
(`site/public/assets/release.json`), the bot reads that file on boot and marks the
matching `guide_media` rows, and the page then shows a `stale` pill on the picture and a
count on the hub for staff. Nothing deletes an old picture: an old real picture beats no
picture, and only an upload clears the pill.

⚠️ **The bot cannot do this.** A bot user has no rendered view of anything. A Claude
session can, because it drives the owner's own already-signed-in browser.

🔴 **The line this runbook does not cross: the session PRESSES NOTHING on the owner's
Discord account.** It scrolls, it reads, it screenshots. The self-test posts every panel's
root card into `#mute-me-bot-test-spam` on every deploy, so the thing worth shooting is
already on screen without anybody clicking it. A screen that would need a press —
a modal, a sub-panel, a DM card — is **not** captured: it is drawn as a mock and uploaded
with `source = mock`, and the page labels it *illustration* (§C4.4 of
[`../info/guides-design.md`](../info/guides-design.md)).

## Before you start

| Need | How |
|---|---|
| The deploy landed and named a feature | `release.json` is committed by `scripts/deploy.ps1`; the `guide.shots_stale` log row says how many shots it marked and for which features |
| The operator token | `BLACK_BLOC_OPERATOR_TOKEN` on this machine — [`operator-read.md`](operator-read.md). It never appears in a transcript |
| Chrome, with the owner signed in to Discord **and** to the dashboard | the Claude in Chrome extension, with permission for `discord.com` and `blackbloc.heygabi.ai` |
| Pillow, for the crop | ⚠️ **NOT in the repo's `.venv`, and it must stay out** — Black Bloc does not depend on it. Use a throwaway one |

```powershell
python -m venv $env:TEMP\shots-venv
& $env:TEMP\shots-venv\Scripts\pip install pillow
```

## 1. Read the to-do list, before any browser

```powershell
.\scripts\read.ps1 -Path /api/guides/stale
```

Each row in `shots` carries `slug`, `title`, `feature`, `caption`, `source`
(`capture` or `mock`), `surface` (`discord` or `website`), `shot_release` and
`stale_since`. **That list is the whole job.** An empty `shots` list means there is
nothing to do; say so and stop — do not go hunting.

Write the list down before opening a browser: it is what stops the session wandering
around Discord looking for something to shoot.

## 2. Open the test channel, and find the card

In Chrome, open the owner's Discord tab at `#mute-me-bot-test-spam`. The self-test has
just posted every panel's root card there.

- Scroll the card for the feature into view.
- Read its bounding box with the page-script tool, e.g.
  `document.querySelector('[id="chat-messages-…"]').getBoundingClientRect()`, or find
  the message by its text and take `getBoundingClientRect()` of the closest `li`.
- Screenshot the tab.

⚠️ **Do not click anything in Discord.** Scrolling and reading are the whole
interaction. If the card you need is not on screen without a press, it is a mock
(step 5).

## 3. Crop it

`scripts/scan/crop_shot.py` — **gitignored**, because it gathers pictures rather than
making the bot work. If the folder is empty, write it back from the block at the foot of
this file.

```powershell
& $env:TEMP\shots-venv\Scripts\python scripts\scan\crop_shot.py `
    $env:TEMP\tab.png $env:TEMP\golive-panel.png --box 420 310 860 520
```

| Flag | What it does | Default |
|---|---|---|
| `--box X Y W H` | the rectangle to keep, in the coordinates `getBoundingClientRect()` gave | required |
| `--pad N` | pixels of breathing room around the box | 8 |
| `--max-side N` | shrinks so the longest side is at most this | **1600** — the API refuses more, in words |
| `--max-bytes N` | shrinks further until the file fits | **2097152** (2 MB) — the API refuses more |

It prints the final `WxH` and byte count. Those two numbers are exactly what the upload
is checked against, twice: once in the browser before the request, and once at the bot.

## 4. Upload it through the guide's own page

⚠️ **The editor is the only write path.** There is no back door, no `flyctl ssh` copy, no
route that takes a file any other way.

1. Open `https://blackbloc.heygabi.ai/guides.html#<slug>` in the same browser.
2. Press **Edit this guide** (staff only; `guides_who_edits` decides who counts).
3. On the step the picture belongs to, fill **Caption**, **What it is**
   (`a real screenshot` / `a drawn illustration`), **Where it is from** and
   **Which release** — the release is the one in `release.json`, e.g. `v111`, and it is
   what staleness is measured against later.
4. Press **Replace screenshot…** and pick the cropped file.
5. The sentence beside the button is the answer. A refusal is the bot's own words —
   read it, do what it says, and do not retry blindly.

| If it says | It means | Do this |
|---|---|---|
| *"…is not a picture Black Bloc can serve"* | the file is not PNG/JPEG/WebP | re-export it |
| *"That picture is N KB and Black Bloc keeps guide screenshots under 2.0 MB"* | over the byte limit | crop tighter, or lower `--max-side` |
| *"That picture is N pixels on its longest side"* | over 1600 px | run the crop again with `--max-side 1600` |
| *"Save your changes first"* | the editor has pending edits | press **Save Changes**, then upload |
| *"Save the guide first"* | the step is new and has no id at the bot yet | press **Save Changes**, then upload |

⚠️ **An upload lands immediately and reloads the guide.** Anything typed and not saved
would be lost, which is why the page refuses while the save bar is showing.

Uploading clears `stale` on that step. Re-read `/api/guides/stale` when you think you are
finished — the count going to zero is the only proof.

## 5. When a capture cannot reach it — draw a mock

A modal, a sub-panel (**Streamers…**, **Settings**), a DM card, or any state the self-test
does not post: build the screen as HTML in the Discord look, screenshot **that**, and
upload it with **What it is** = `a drawn illustration`. The page then captions it
*illustration · v111 · …* rather than *screenshot*, so nobody mistakes a drawing for the
real thing. A mock goes stale by the same rule and is redrawn by the same session step.

**A mock is a fallback, never a substitute for a root card that can be shot.**

## 6. Say what you did, and what you did not

The report names: which slugs were re-shot, which were left (and why), the release the
shots carry, and `/api/guides/stale`'s count before and after. A shot you could not take
is reported as not taken — never quietly skipped.

## The crop helper, in full

`scripts/scan/crop_shot.py` is gitignored, so a fresh clone does not have it. This is the
copy of record.

```python
"""Crop a full-tab screenshot down to one card, for docs/access/guides-capture.md.

Not bot code: scripts/scan/ is gitignored and this never ships.

    python crop_shot.py <in.png> <out.png> --box X Y W H [--max-side 1600] [--max-bytes 2097152]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

MAX_SIDE = 1600
MAX_BYTES = 2 * 1024 * 1024


def shrink(image: Image.Image, side: int) -> Image.Image:
    longest = max(image.size)
    if longest <= side:
        return image
    scale = side / longest
    return image.resize(
        (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
        Image.LANCZOS,
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source")
    parser.add_argument("out")
    parser.add_argument("--box", nargs=4, type=int, metavar=("X", "Y", "W", "H"), required=True)
    parser.add_argument("--max-side", type=int, default=MAX_SIDE)
    parser.add_argument("--max-bytes", type=int, default=MAX_BYTES)
    parser.add_argument("--pad", type=int, default=8)
    args = parser.parse_args(argv[1:])

    image = Image.open(args.source).convert("RGB")
    x, y, w, h = args.box
    pad = args.pad
    box = (
        max(0, x - pad),
        max(0, y - pad),
        min(image.width, x + w + pad),
        min(image.height, y + h + pad),
    )
    if box[2] <= box[0] or box[3] <= box[1]:
        print(
            "crop_shot: that box is empty or off the picture, so nothing was written.",
            file=sys.stderr,
        )
        return 2

    shot = shrink(image.crop(box), args.max_side)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    shot.save(out, "PNG", optimize=True)

    side = args.max_side
    while out.stat().st_size > args.max_bytes and side > 400:
        side = int(side * 0.85)
        shrink(shot, side).save(out, "PNG", optimize=True)

    size = out.stat().st_size
    print(f"{out} {Image.open(out).size[0]}x{Image.open(out).size[1]} {size} bytes")
    if size > args.max_bytes:
        print(
            "crop_shot: still over 2 MB after shrinking to 400 px. The upload will be refused in "
            "words; crop tighter.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

## Where the pictures end up

`/data/guides/<id>.<ext>` on the Fly volume, beside the database — **not** under
`site/public`, which is public and ships with the image. They are served by
`GET /api/guides/media/{id}`, member-gated, `private, max-age=86400`, ETag = the sha.
`scripts/backup_db.ps1` tars the folder with the nightly snapshot;
[`RECOVERY.md`](RECOVERY.md) carries the restore.

## Drill log

| Date | What was drilled | Result |
|---|---|---|
| — | 🔴 nothing yet | this runbook is **untested**; the first capture session is its drill |
