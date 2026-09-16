# Guide screenshots — the capture session, step by step

> **Audience:** a Claude session with Claude in Chrome, after a deploy. **Status:**
> TRACKED — ⚠️ **secret NAMES only.** **Last verified: 2026-09-16** — written at the G2
> build (branch `guides-pages`) and checked against the code it names:
> `black_bloc/api/tools/guides.py` (`GET /api/guides/stale`, `POST /api/guides/{slug}/media`),
> `black_bloc/guides.py` (`MEDIA_BYTES_MAX` 2 MB, `MEDIA_SIDE_MAX` 1600, `media_root`),
> `site/public/assets/page-guides.js` (**Replace screenshot…**), `scripts/deploy.ps1` and
> `scripts/release_json.py` (`release.json`), `docs/access/operator-read.md`
> (`scripts/read.ps1`).
> ✅ **DRILLED END TO END, 2026-09-16 09:19–10:03 Phoenix** (third drill; the first two that
> morning were partial — the drill log at the foot has all three). The **first population**
> ran: the purge window was borrowed, self-test **run #28** posted **24 cards**, **16 root
> cards** were shot and **16 guides** got a picture (`media/1`–`media/16`), the window was put
> back, and the pictures were seen rendering on two guides. **§5 was then exercised too**: the
> one card a capture must not publish (`/birthday`) was drawn as a mock and uploaded as
> `a drawn illustration`, so **all 17 guides now carry a picture** (`media/1`–`media/16`, plus
> **`media/18`** for `birthday-set` after the mock was redrawn — see the drill log).
> The page's own refusal sentences in §4's table are **still** unreproduced — nothing was
> refused, so that table remains written from the code.
> **First drill, 2026-09-16 09:1x Phoenix (partial — stopped at step 2, nothing shot, nothing uploaded).** Found: (1) step 1 answered `count: 0` on the live app right after v111 — there is nothing STALE, because no guide has a picture yet; the runbook says stop there, but the FIRST population of pictures is a different job it does not describe. (2) The self-test's cards are purged **one minute** after they post (`selftest_purge_minutes`, default 1 — the owner's choice, "mainly for you and not me"), so by the time a session reads the to-do list and opens Discord the cards are gone; a capture needs a self-test triggered from the dashboard's Health page and the shots taken inside that minute, or the key raised for the session and put back. (3) The owner's Chrome IS signed in to Discord web and `#blackbloc-logs` renders — that half works. (4) ⚠️ Step 2's "screenshot the tab" lands on disk only with the `computer` tool's `save_to_disk: true`, which returns the path; a plain screenshot is an image in the transcript, not a file, and `$env:TEMP	ab.png` does not exist by itself. (5) Pillow venv, crop and upload were NOT reached. The question of the purge window is the owner's (`TODO.md`).
> **Second drill, 2026-09-16 09:19–09:3x Phoenix (partial — stopped at step 2 again, nothing
> uploaded).** Dispatched to do the FIRST POPULATION with the owner at the machine. Blocked on
> a precondition this file lists but does not weight: 🔴 **the dashboard was SIGNED OUT.**
> `GET /api/auth/me` from the page answered **401 `not_signed_in`**, so the Settings page, the
> Health page's **Run the self-test** and every guide editor were all shut — and the session
> may not press **Sign in with Discord** (an OAuth grant on the owner's account is his click,
> not a session's). Discord was fine: signed in, `#blackbloc-logs` rendered, and — as
> the first drill predicted — **no self-test cards were left** (newest bot message 9/12). Also
> found: (1) the operator token **cannot** read `/api/guides` — it is member-gated and answers
> `not_a_member` in words, so the slug list comes from `black_bloc/guides_seed.json`;
> (2) `zoom` + `save_to_disk` works and needs no Pillow, **but its `region` is in SCREENSHOT
> coordinates, not the CSS pixels `getBoundingClientRect()` returns** — see §2/§3 for the
> conversion and the measured numbers.

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
root card into `#blackbloc-logs` on every deploy, so the thing worth shooting is
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
| 🔴 **CHECK THE DASHBOARD SIGN-IN FIRST — it is the precondition that actually fails** | in the tab, `await fetch('/api/auth/me',{credentials:'include'}).then(r=>r.status)`. **200** and you may work; **401 `not_signed_in`** and the session is done — ⚠️ **the session does NOT press Sign in with Discord.** That link is `/api/auth/login`, an OAuth grant on the owner's own account, and pressing it is his click, not a session's. Ask him to sign in, then carry on. Measured 2026-09-16 09:19: 401 |
| ~~Pillow, for the crop~~ | ⚠️ **NO LONGER NEEDED — and no venv is built.** The `computer` tool's `zoom` action with `save_to_disk: true` crops and writes the file in one call (§3). The old Pillow path is kept only as the fallback block at the foot |

## 1. Read the to-do list, before any browser

```powershell
.\scripts\read.ps1 -Path /api/guides/stale
```

Each row in `shots` carries `slug`, `title`, `feature`, `caption`, `source`
(`capture` or `mock`), `surface` (`discord` or `website`), `shot_release` and
`stale_since`. **That list is the whole job.** An empty `shots` list means there is
nothing to **RE-SHOOT**; say so and stop — do not go hunting.

⚠️ **`count: 0` has TWO meanings, and this file only ever described one.** Staleness is a
fact about pictures that EXIST. Until a guide has a picture there is nothing to mark, so a
brand-new guide reads exactly like a freshly re-shot one. Measured 2026-09-16 09:18 on the
live app at v111: `{"shots": [], "count": 0}` — with **zero pictures in the whole app.**

- **Re-shoot session** (what §1–§6 describe): `count > 0`, and the rows are the job.
- 🔴 **FIRST POPULATION** (what this runbook does not otherwise describe): `count == 0` *and*
  no guide has a picture. The job is then **one shot of each feature's ROOT PANEL CARD on
  step 1 of each guide**, and the list comes from the seed, not from the API:

```powershell
.\.venv\Scripts\python -c "import json;[print(g['slug'],g['command']) for g in json.load(open('black_bloc/guides_seed.json'))['guides']]"
```

⚠️ **`GET /api/guides` is NOT readable with the operator token** — it is member-gated and the
operator identity is deliberately not a member, so it answers *"You are signed in, but Discord
does not show you as a member…"* (the same rule `operator-read.md` records for
`/api/requests/mine`). Measured 2026-09-16 09:18. The seed file is the slug list.

The 17 seeded guides cover 16 distinct commands; **`event-review` (staff) and `event-propose`
(member) share `/event`**, so one `/event` card serves both.

Write the list down before opening a browser: it is what stops the session wandering
around Discord looking for something to shoot.

## 2. Put the cards on screen, then find one

⚠️ **The cards are almost certainly NOT there when you arrive.** They are posted by the
self-test on deploy and **purged one minute later** (`selftest_purge_minutes`, default 1 —
the owner's 2026-09-10 choice, *"mainly for you and not me"*). Measured in both drills: by
the time a session has read the to-do list and opened Discord, the channel's newest bot
message is days old. So the session posts them itself, on the dashboard:

1. **Raise the purge window** — `https://blackbloc.heygabi.ai/settings.html`,
   `selftest_purge_minutes` (Core group; the page has a **Show keys** toggle and <kbd>Ctrl</kbd>
   <kbd>K</kbd> jumps to a key) → **30** → Save, and read the row back. ⚠️ **Put it back to 1
   at the end of the session** — this is a borrowed setting, not a change.
2. **Trigger the self-test** — `https://blackbloc.heygabi.ai/health.html` ▸ **Run the
   self-test**. It posts every panel's root card into `#blackbloc-logs` in about 30 s
   (the boot line says ~24 messages).

Then open the owner's Discord tab at
`https://discord.com/channels/1073710702776299640/1542316174472380517`.

⚠️ **Discord's message list will not paginate for a script.** Two traps, both measured:

- **Setting `scrollTop` loads nothing.** Discord paginates on real wheel events. Use the
  `computer` tool's `scroll` action over the message area; `scrollTop = 0` sits at the top of
  what is already loaded and never fetches more. Measured: stuck at 14 messages until two
  `scroll up` bursts brought it to 42.
- **Pick the right scroller.** `document.querySelector('[class*=scroller]')` finds a sidebar.
  The message scroller is the one that *contains* the messages:
  `document.querySelector('li[id^="chat-messages"]').closest('[class*="scroller__"]')`.
- Keep page scripts **short**: a loop of ~20 scroll-and-wait steps blew the 45 s CDP timeout.

### The cards the self-test posts, and which guide each belongs to

⚠️ **The panels are components-v2 containers, not embeds** — half of them have no
`embedTitle`, so matching on that alone finds about ten of the sixteen. Match on body text
instead. Measured at run #28 (24 cards, 16 of them root panels):

| Guide slug | Command | Card title | A needle that finds it |
|---|---|---|---|
| `golive-announce` | `/golive` | Go-live | `Your Twitch channel` |
| `pings-follow` | `/pings` | Your pings | `What Black Bloc pings you` |
| `event-propose` · `event-review` | `/event` | Events | `Propose an event` |
| `birthday-set` | `/birthday` | Birthdays | `Tell Black Bloc when your birthday` |
| `voice-room` | `/voice` | Your voice channel | `Your voice channel` |
| `poll-vote-make` | `/poll` | Polls | `Put something to the room` |
| `request-file` | `/request` | Requests | `Ask the server` |
| `chat-memory` | `/memory` | What Black Bloc remembers about you | (the title) |
| `raidtrain-slot` | `/raidtrain` | Raid trains | `Raid trains are on` |
| `apply-form` | `/apply` | Applications | `Apply for what this server` |
| `modmail-ticket` | `/modmail` | The modmail inbox | (the title) |
| `mod-case` | `/mod` | What Black Bloc has done | (the title) |
| `automod-arm` | `/automod` | What automod is watching | (the title) |
| `honeypot-set` | `/honeypot` | The trap that catches spam bots | (the title) |
| `rolemenu-post` | `/rolemenu` | Role menus | `event-alerts — 1 role(s)` |
| `feature-modes` | `/settings` | Black Bloc's settings for this server | (the title) |

⚠️ **A select's placeholder is not `innerText`.** `Whose cases?` looks like text on screen but
is a custom select — matching on it finds nothing. Match on the card's prose.

The other eight cards are announcements and self-test scaffolding (a go-live announcement, a
birthday wish, a raid-train announcement, `event.approved` / `event.denied` / `event.cancelled`
log lines, `Black Bloc self-test`), and **no guide uses them**.

- Scroll the card for the feature into view.
- Read its bounding box with the page-script tool — find the message by its text and take
  `getBoundingClientRect()` of the closest `li[id^="chat-messages"]`:

```js
[...document.querySelectorAll('li[id^="chat-messages"]')]
  .filter(li => /New request #/.test(li.innerText))
  .map(li => li.getBoundingClientRect())
```

⚠️ **Do not click anything in Discord.** Scrolling and reading are the whole
interaction. If the card you need is not on screen without a press, it is a mock
(step 5).

### 🔴 A capture contains the bot's card and NOTHING ELSE

**Owner rule, 2026-09-16, verbatim:** *"we need to make sure no chats that arent with the bot
or channels not whats trying to be shown off are visible. wouldn't want to leak mod stuff"*.
A guide screenshot is served to every member, so anything caught at its edges is published
to them.

| Must be in the shot | Must **NOT** be in the shot |
|---|---|
| Black Bloc's own card — the embed, its buttons, its footer | any other member's message, name, avatar or reaction |
| | the channel sidebar and the server list |
| | the member list |
| | the message box at the foot |
| | the channel-name strip at the head |

- **Crop to the message element's own rect** — the bot's `li[id^="chat-messages"]`, or
  tighter (the embed plus its buttons). ⚠️ **Never a wider region "to be safe"**: wider is
  the failure mode, not the safe one. A `li` is full-channel-width, so most of its box is the
  empty gutter where the NEXT message's first line sits — shoot the embed's own box instead,
  and clip the height to the card, not to the row.
- ⚠️ **LOOK AT THE FILE BEFORE YOU UPLOAD IT.** The `Read` tool renders a PNG. Confirm by eye
  that nothing but the card is in it. **A file showing anything else is DELETED, not
  uploaded** — not re-cropped in place, not uploaded "because it is only a username".
- If a card cannot be isolated this way, **do not take it**; report it as not taken (§6).
- The same rule covers the rendered-guide-page screenshot taken for the owner at §6: the
  guide page only.

🔎 **Measured 2026-09-16, three separate ways this bit:**

1. A region taken from a `li`'s full box caught the *next* message's author line at its foot —
   one member's name and server tag. Deleted unused. On a busy channel the neighbour is
   always there.
2. ⚠️ **Padding UPWARD is the dangerous direction.** A 6 px pad above the card caught a sliver
   of the *previous* message's button row on `/settings`. Re-shot with the top edge on the
   container's own top. **Pad left/right/bottom; never up.**
3. 🔴 **A card's OWN BODY can carry member data, and that is the case the rule above does not
   catch by eye-balling the edges.** `/birthday` prints **Next birthdays** — five members'
   IDs, one resolved display name and five dates. The capture was clean of neighbours and
   still unpublishable, because a guide picture is served to **every member**. It was deleted
   and `birthday-set` went to §5 as a **mock** instead (owner's call, 2026-09-16: *"C"*).
   **Read the card's text, not just its borders**, and check `/mod`, `/modmail`, `/honeypot`,
   `/apply` and `/request` the same way — they were all clean this time **only because the
   server had no open cases, tickets, hits or applications**. On a live server they will not be.
   ⚠️ **This is the second reason to draw a mock**, and §5 did not have it: not just *"a
   capture cannot reach it"* but *"a capture reaches it and must not be published"*.

⚠️ **One shot was uploaded WITH a judgement call, and the next session should know:**
`/golive`'s card ends with `live now — 1 · [BK CEO] The BaF Blue Shell on Twitch`. That is one
member's name and that they were streaming — inside Black Bloc's own card, and already public
in `#live-now`. It was uploaded and flagged to the owner rather than withheld. If he would
rather it were not there, re-shoot `/golive` when nobody is live.

## 3. Shoot it — `zoom` straight to disk, no Pillow

✅ **Measured 2026-09-16 09:2x — this replaces the crop helper entirely.** The `computer`
tool's **`zoom`** action takes a `region` and, with **`save_to_disk: true`**, writes the
cropped PNG and returns its path in the result. One call; nothing to install, nothing to
crop afterwards.

```
computer  action: "zoom"
          region: [x0, y0, x1, y1]     ← SCREENSHOT coordinates, see below
          save_to_disk: true
→ "Successfully captured zoomed screenshot of region (227,248) to (1000,434) - 1568x377 pixels"
→ "Screenshot saved to: C:\Users\…\Temp\claude-chrome-screenshots-<rand>\screenshot-<ms>-0.png"
```

🔴 ⚠️ **`region` is NOT in the CSS pixels `getBoundingClientRect()` gives you.** This is the
one thing that will waste a session. The screenshot has its own coordinate frame (every
screenshot result prints it, e.g. *"coordinate frame: 1512x802"*) and the page's CSS
viewport is a different size. Convert:

```js
const k = 1512 / window.innerWidth;     // frame width ÷ CSS width
const dy = 802 - window.innerHeight * k; // browser chrome above the viewport
// region = [r.x*k, r.y*k + dy, (r.x+r.width)*k, (r.y+r.height)*k + dy]
```

⚠️ **Take a `screenshot` first and use the frame IT reports — and do not trust the first zoom
in a tab you have just created.** Measured 2026-09-16: the same region that captured a card
perfectly in one tab came back clipped to ~60% of its width on the first zoom in a fresh tab,
then worked on the retry with the identical numbers. If a zoom comes back clipped or
mis-scaled, **re-shoot it rather than reasoning about it** — and if two attempts disagree,
calibrate with a throwaway `zoom` of `[0,0,200,200]` and see which CSS area comes back.

Measured on the owner's machine 2026-09-16: frame **1512×802**, `innerWidth` **2498**,
`innerHeight` **1269**, `devicePixelRatio` **1.5** → `k` = **0.6053**, `dy` = **34**. A card
predicted this way landed exactly on its box first time. ⚠️ **Re-measure every session** —
`k` and `dy` change with the window size and the zoom level; nothing here is hardcodable.

**The two limits take care of themselves, and here is why.** `zoom` upscales the crop by
`devicePixelRatio × (innerWidth / frameWidth)` — **2.478** in the reading above — and **caps
the long side at 1568 px**, which is under `MEDIA_SIDE_MAX` (1600). Both measured:

| Region (frame px) | Output | Bytes |
|---|---|---|
| 773 × 186 (a full-width card) | **1568 × 377** — capped | **195 115** (191 KB) |
| 343 × 186 | 850 × 460 — uncapped, 343 × 2.478 | not saved |

So a zoom in this window **cannot** breach the 1600 px side limit, and a card-sized region
lands two orders of magnitude inside the 2 MB limit. Shoot the card, not the whole row: a
`li[id^="chat-messages"]` spans the full channel width (2107 CSS px) and most of it is empty.

If a card is taller than the viewport, scroll it fully into view first and re-read the box —
a region partly off-screen captures the background, not the card.

### The box to use: the union of the card's PAINTED elements

✅ **This is the recipe that produced all 16 shots, and it needs no per-card tuning.** A
components-v2 panel is a `.container_…` inside the `li`, and the container is full channel
width (1997 CSS px) while the card paints only ~500 of it. Take the union of the descendants
that actually paint — the embed box and the buttons — and clamp it inside the `li`:

```js
const li = [...document.querySelectorAll('li[id^="chat-messages"]')]
  .find(l => l.innerText.includes(NEEDLE));
li.scrollIntoView({block: 'center'});            // then wait ~700 ms and re-find it
const c = li.querySelector('.container_b7e1cb') || li;
const painted = [...c.querySelectorAll('*')].filter(e => {
  const s = getComputedStyle(e), r = e.getBoundingClientRect();
  return r.width && r.height &&
    (s.backgroundColor !== 'rgba(0, 0, 0, 0)' || s.borderLeftWidth !== '0px');
});
// union of their rects → pad 6 px LEFT/RIGHT/BOTTOM ONLY → clamp bottom to li.bottom - 4
```

⚠️ **Re-find the `li` after scrolling** — the message list is virtualised and the element you
measured can be replaced. ⚠️ **The class hash (`container_b7e1cb`) is Discord's and will
change**; fall back to the `li` and re-read the hash from a live card when it does.

Measured outputs, all 16 well inside both limits: **618×285 to 1055×914**, **38–203 KB**.

## 4. Upload it through the guide's own page

⚠️ **The editor is the only write path.** There is no back door, no `flyctl ssh` copy, no
route that takes a file any other way.

🔴 **Move the files first: `file_upload` REFUSES the folder `zoom` saved them in.**
`%TEMP%\claude-chrome-screenshots-<rand>\` is not a folder the session may upload from —
*"only files this session is allowed to read can be uploaded"*. Copy them under the repo, into
**`scripts/scan/shots/`**, which is gitignored (`scripts/scan/` never enters git, per
`CLAUDE.md`) and is a path the session may read. Name them for the feature while you are
there; `card-golive.png` beats `screenshot-1789576802368-2.png` sixteen times over.

1. Open `https://blackbloc.heygabi.ai/guides.html#<slug>` in the same browser.
2. Press **Edit this guide** (staff only; `guides_who_edits` decides who counts).
   ⚠️ **Measure that button every time and then CHECK IT OPENED.** Its x moves with the
   title's width — measured **1481** on most guides and **1490** on `mod-case` and
   `feature-modes`, and a 9 px miss is a silent no-op. After the click, assert
   `document.querySelectorAll('.step-shotedit').length > 0` before doing anything else.
3. On the step the picture belongs to, fill **Caption** and **Which release** —
   ✅ **What it is** and **Where it is from** already default to `a real screenshot` and
   `Discord`, so a capture session touches neither. The release is the one in `release.json`,
   e.g. `v111`, and it is what staleness is measured against later.
   ⚠️ **Measure the two text inputs too** — step 1's block sat at frame y **396** on some
   guides and **372** on others. 🔴 **Then read the values back before uploading.** A miss of
   ~20 px lands on the **What it is** select, and typing into a focused `<select>` moves it by
   type-ahead: you get a phantom "1 change pending" and a metadata field silently changed.
   Measured twice. **If the readback is empty, do not upload** — reload the page (which
   discards the pending change; nothing has been saved) and start the guide again.
4. Press **Replace screenshot…** and pick the file.
   ⚠️ **Never CLICK a file input** — that opens a native picker no session can see. **Replace
   screenshot…** is a `<label>` over an `<input type=file>`: find that input with `find` or
   `read_page` and hand its `ref` to the **`file_upload`** tool with the path. The page then
   base64s the bytes into the JSON body itself (`guides-design.md` § *G2 deviations*), so
   there is no multipart request to build. ✅ Measured 16 times, 38–203 KB each.
   ⚠️ `find` returns **one ref per step** on a guide with several picture slots — take the one
   it names as the **first** step.
5. The sentence beside the button is the answer. A refusal is the bot's own words —
   read it, do what it says, and do not retry blindly.
6. ✅ **Verify each upload before moving on**, because an upload is the one thing here with no
   undo: the block gains a **Remove screenshot** button, and
   `document.querySelector('img[src*="media"]')` answers `/api/guides/media/<id>` with the
   caption rendered as **`screenshot in Discord · v111 · <your caption>`**. Ids ran 1–16 in
   upload order.

✅ **No save was ever needed.** The upload lands on its own and the page re-renders; across 16
uploads the editor never asked for **Save Changes** and the refusal table below never fired.
⚠️ **`computer left_click` with a `ref` does NOT work on these pages** — it reports success and
nothing happens. Convert the element's `getBoundingClientRect()` to frame coordinates (§3) and
click those. The same is true on the Settings page; there, one **Save Changes** click needed a
`hover` at the point first before it registered.

🔴 ⚠️ **Coordinate clicks do not land in a BACKGROUND tab either** — and this one looks exactly
like a missed coordinate, so it wastes a lot of calls. Measured 2026-09-16: with the owner
browsing his own tab, every click into the session's tab reported success and did nothing,
while `elementFromPoint` at those very coordinates returned the right button. **If the owner
is using the browser, work in the tab HE is looking at, or drive the sanctioned control with
`element.click()` from the page-script tool**, which does not depend on focus. ⚠️ Use that
only for controls this runbook names — it is a way around a focus problem, never around a
gate. `form_input` and `file_upload` are unaffected and keep working in a background tab.

⚠️ **A re-upload creates a NEW media id rather than replacing the old one.** Redrawing
`birthday-set`'s mock moved it from `media/17` to `media/18`. Quote the id you last saw, and
re-read it after any re-upload.

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

⚠️ **On a FIRST population `/api/guides/stale` proves nothing** — it reads `count: 0` before
you start and `count: 0` when you finish, because a fresh shot is not stale (§1). The proof
there is the media ids and the rendered captions from step 6.

🔴 **The picture is `loading="lazy"`, so check the PIXELS, not the attribute.** Measured: on a
freshly opened guide `img.naturalWidth` is **0** and `img.complete` is **false** even after
`scrollIntoView` and a 3 s wait, while `fetch('/api/guides/media/1')` answers **200
`image/png`** with the right byte count and a screenshot shows the picture on the page. Wheel
the page past it and back and the attribute catches up (`1055×902`, `complete: true`). Judging
it by `naturalWidth` alone would report a working picture as broken.

## 5. When a capture cannot reach it — or must not be published — draw a mock

✅ **Drilled 2026-09-16 on `birthday-set`** (`media/17`, redrawn as `media/18`). The recipe below is what was
actually done, not a sketch.

**Two reasons to draw one**, and the second was found the hard way:

1. **A capture cannot reach it** — a modal, a sub-panel (**Streamers…**, **Settings**), a DM
   card, or any state the self-test does not post.
2. 🔴 **A capture reaches it and must NOT be published** — the card's own body carries member
   data (§2's isolation rule). `/birthday` is the case: it prints five real members' names and
   dates, so the real card can never be a guide picture, however cleanly it is cropped.

**The recipe:**

1. **Write the screen as one self-contained HTML file** under `scripts/scan/shots/`
   (gitignored). ⚠️ **Sample the real colours rather than guessing them** — the owner runs a
   purple custom theme, so Discord's stock `#313338` looks wrong beside the other sixteen
   pictures. Read them straight out of a real capture:

   ```powershell
   Add-Type -AssemblyName System.Drawing
   $b = New-Object System.Drawing.Bitmap "scripts\scan\shots\card-golive.png"
   $c = $b.GetPixel(400, 300); '#{0:X2}{1:X2}{2:X2}' -f $c.R, $c.G, $c.B
   ```

   Measured off `card-golive.png` / `card-poll.png`, 2026-09-16:

   | Part | Colour |
   |---|---|
   | message area behind the card | `#271231` |
   | embed body | `#34223E` |
   | embed left accent bar | `#46384F` |
   | title | `#F7F5FA` · body `#C9C0CE` · muted `#8E8494` |
   | inline chip (dates, code) | `#26102B` |
   | mention | `#9BA7F5` on `rgba(88,101,242,.16)` |
   | primary button | **`#5865F2`** (Discord blurple, unchanged by the theme) |
   | secondary button | `#342440`, 1 px `#412F4D`, radius 8 |

   Font stack `"gg sans","Noto Sans","Segoe UI",sans-serif`; body 15 px / 1.42, title 17 px
   bold, buttons 14 px. Give the whole card one wrapper with an **`id`** so its box can be
   measured exactly.

2. ⚠️ **Make every name and date INVENTED, and obviously not a member.** The point of the
   mock is that no real person is in it. Read the card's row in
   [`sweeps.md`](sweeps.md) for what the panel actually says — `/birthday`'s member panel is
   **row 87** — so the drawing tells the truth about the feature.
3. **Serve it and shoot it like a real card:**
   `python -m http.server 8799 --bind 127.0.0.1` from `scripts/scan/shots`, open
   `http://127.0.0.1:8799/<file>.html` in a **new tab**, `getBoundingClientRect()` the
   wrapper, convert to frame coordinates (§3) and `zoom` with `save_to_disk`. **Stop the
   server afterwards** and close the tab.
4. **Upload with What it is = `a drawn illustration`.** That select is the only field that
   differs from a capture; `form_input` sets it reliably where a click does not. ✅ The page
   then captions it **`illustration in Discord · v111 · …`** instead of `screenshot …`, so
   nobody mistakes a drawing for the real thing.

A mock goes stale by the same rule and is redrawn by the same session step.

**A mock is a fallback, never a substitute for a root card that can be shot** — except where
reason 2 applies, and there it is the ONLY correct answer.

## 6. Say what you did, and what you did not

The report names: which slugs were re-shot, which were left (and why), the release the
shots carry, and `/api/guides/stale`'s count before and after. A shot you could not take
is reported as not taken — never quietly skipped.

## The crop helper, in full — ⚠️ RETIRED, kept only as a fallback

🔴 **You do not need this.** §3's `zoom` + `save_to_disk` does the same job in one tool call
with no Pillow and no venv, and was measured working 2026-09-16. This block is kept for the
one case it still covers: cropping a picture that did **not** come from the browser (a mock
exported elsewhere, or a file the owner took with <kbd>Win</kbd>+<kbd>Shift</kbd>+<kbd>S</kbd>).

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
| 2026-09-16 09:1x | §1 against the live app; Discord tab opened | `/api/guides/stale` → `count: 0`. Discord signed in, channel renders, **no cards** (purged). Stopped at §2. Found the `save_to_disk` gap |
| 2026-09-16 09:2x | §1 again, §2's Discord half, §3 end to end | 🔴 **Blocked at §2's dashboard half — `/api/auth/me` = 401 `not_signed_in`.** Nothing shot for a guide, nothing uploaded. §3's `zoom`-to-disk path measured and written up; §1 gained the first-population case; `/api/guides` found unreadable with the operator token; the owner's isolation rule written into §2 |
| 2026-09-16 09:35–10:03 | ✅ **THE FIRST POPULATION, end to end** — purge window 1 → 30, self-test run #28, 16 cards shot, **16 guides uploaded**, window → 1, two guides verified rendering | ✅ **Worked.** `media/1`–`media/16`. 1 guide deliberately left without a picture (`birthday-set`, member data in the card body). §2 gained the card→guide table and Discord's scroll traps; §3 gained the painted-union recipe; §4 gained the upload folder rule, the moving-button rule and the readback rule |
| 2026-09-16 10:10–10:2x | ✅ **§5 EXERCISED** — the owner chose *"C"* for `birthday-set` (a drawn mock) and *"A"* for `golive-announce` (keep the real shot). Drew `scripts/scan/shots/birthday-mock.html` as the `/birthday` **member** panel per `sweeps.md` row 87, with five invented people; served it on `127.0.0.1:8799`, shot the wrapper, uploaded it as `a drawn illustration` | ✅ `media/17`, **848×695, 111 017 bytes**, captioned **`illustration in Discord · v111 · …`**. All **17 of 17** guides now have a picture. §5 rewritten with the sampled palette and the recipe; §2 gained the second reason to mock |
| 2026-09-16 10:3x–10:5x | ✅ **A MOCK REDRAWN, and §5's re-upload path proved** — the owner asked for the five invented people to become famous Black celebrities (*"Chadwick Boseman, Halley Berry, etc Zendaya"*). Same HTML, five real public birthdays in next-occurrence order from today; re-rendered, re-shot, re-uploaded over the old one | ✅ `media/18`, **854×699, 110 604 bytes**, still captioned **`illustration in Discord · v111 · …`**, editor left at `0 changes pending`. ⚠️ A re-upload makes a **NEW media id** — and the OLD row and file are dropped by the route (`drop_media`): `media/17` answers **404** `no_such_media` when fetched with `cache: 'no-store'`. It looked alive only because the browser had cached its `private, max-age=86400` response (the conductor measured both at 11:3x). Quote the id you last saw, and never trust a cached 200. Two new traps found, both below: the zoom frame can go stale right after a tab is created, and clicks do not land in a **background** tab |
| — | 🔴 §4's refusal table, a RE-SHOOT session (a stale count above zero) | still **never run** — nothing was refused and nothing was stale, so both remain written from the code |

## Measured, 2026-09-16 (second drill)

| Thing | Reading |
|---|---|
| `/api/guides/stale` | `{"shots": [], "count": 0}` at 09:18 and unchanged at the end — **nothing was uploaded** |
| `/api/guides` with the operator token | refused in words: *"…Discord does not show you as a member of Black in a Flash!…"* |
| `/health` | `ok: true`, `ready: true`, `guilds: 1`, `latency_ms: 67`, version `0.1.0` |
| `/api/auth/me` in the browser | **401 `not_signed_in`** — the session-stopper |
| Discord | signed in; `#blackbloc-logs` renders; newest bot message **9/12/26**, i.e. no self-test cards |
| `selftest_purge_minutes` | **not read and not changed** — the Settings page was behind the sign-in |
| Self-test | **not run** |
| Screenshot frame / CSS viewport | 1512×802 frame; `innerWidth` 2498, `innerHeight` 1269, `dpr` 1.5 → `k` 0.6053, `dy` 34 |
| `zoom` + `save_to_disk` | works, returns the path, needs no Pillow. 773×186 region → **1568×377 PNG, 195 115 bytes**. Upscale 2.478×, long side capped at 1568 |
| Guides with a picture | **0 of 17** before the third drill |

## Measured, 2026-09-16 — the first population (third drill)

| Thing | Reading |
|---|---|
| `selftest_purge_minutes` | **1** before · **30** during · **1** after (all three read back from `/api/settings`, not just the page) |
| Self-test | **run #28, 9:33:22**, `109 OK · 0 FAILED`, **24 cards**, *"they go after 30 minute(s)"*, *"Started from website"* |
| Root cards shot | **16 of 16** attempted, **15 clean**, **1 withheld** (`/birthday` — it became the §5 mock) |
| Guides given a picture | ✅ **17 of 17** — `media/1`–`media/16` captures, plus the `birthday-set` illustration (`media/17`, redrawn the same morning as **`media/18`**) |
| Capture sizes | 618×285 … 1055×914; **38 857 … 203 232 bytes**. Nothing came near 1600 px or 2 MB |
| `/api/guides/stale` | **0** before, **0** after — see the warning above about what that does and does not prove |
| Two guides re-opened | `golive-announce` → `media/1`, `feature-modes` → `media/16`, both captioned `screenshot in Discord · v111 · …`, both pictures visible on screen |
| Coordinate frame that day | 1543×784 vs `innerWidth` 2498 / `innerHeight` 1269 → `k` **0.6177**, `dy` **≈0** (the earlier drill that morning measured `dy` **34** in the same session — it is per-window, re-measure it) |

## A defect this drill found, outside Guides

🔴 **The Settings page loads with a false "1 change pending", and that change cannot be
saved.** `chat_memory_model` is a `text` key whose stored value and default are both `""`.
The page marks its row `data-dirty="true"` on **every** load — it survives `location.reload()`
and there is no draft in `localStorage` — and sends `null` for it, which the bot refuses in
words: **`'chat_memory_model' takes some text, not None.`** So every save from that page
reports **"1 saved, 1 refused"** even when the staffer changed one thing and it worked.

It is cosmetic-but-loud: it trains staff to ignore a refusal line. Filed here because this
runbook is where it was measured; it belongs in `KNOWN_ISSUES.md`, which this session did not
own. ⚠️ A capture session should **expect** that second refusal and not go hunting for it.
