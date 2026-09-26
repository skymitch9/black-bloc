# Guides — one web page per goal, staff-editable, with real screenshots and live values

> **2026-09-25 (branch `guides-per-command`, schema 66):** the one-published-guide-per-command index is DROPPED — a
> command may carry several published guides per audience (`/event` ▸ Marathons…, `/golive` ▸ Channels…); `/help`
> names each one. §D6 is taken and Deviation 1 is superseded — see *Several guides per command* at the foot.

> **Audience:** the build agent and reviewers. **Status:** TRACKED · ✅ **LIVE as v111** — merges `cad1abc` (G1 core) and `307b759` (G2 pages), release `67aee7e`, deployed **2026-09-16 09:07** Phoenix (`../deploys.log`); landing entry in [`../DONE.md`](../DONE.md) (*"2026-09-16 — GUIDES"*). The two `## Deviations` feet below are the truth where they depart from the body. ⚠️ Rows **360–389** of [`../access/sweeps.md`](../access/sweeps.md) are the owner's; the capture runbook has never been drilled. Was: 📐 DESIGN, not built (owner, 2026-09-15: "dont build yet jusy mock", then "write the design doc"; 2026-09-16 06:5x: "do it all").
> Mock the owner reacted to: https://claude.ai/artifact/C6MGnYLSdSyDHL42y729YA (the hub, one guide,
> the phone view, the augmented `/help`). Owner asks, verbatim, 2026-09-15 21:2x–21:5x:
> *"we need guides on how to use each feature. I dont want just readmes, and i dont want more menus,
> maybe we augment help a bit. What I think we really need is webpages with guides/photos/dynamic
> information about how to achieve something"* · *"lets make guides only server level access"* ·
> *"real captures, re-shot each release if something about that feature changes"* · *"small guide
> link"* (on `/help`) · *"i like A"* (a picture under each step) · *"we need to make sure every part
> of it is editable by the staff. wording more than screen shots. As little fluff text as possible,
> just very empirical almost ikea like steps on how to achieve each thing"*.
>
> **Last verified: 2026-09-15 21:48 Phoenix** — every `path:name` in §A was read on `main` at
> `b32fb43` (v110 live). **§C4 rewritten 21:5x** after the owner's "You can screenshot discord in
> browser mode no? If not make mocks": captures are a Claude-in-Chrome session step over the cards the
> self-test posts, mocks only for screens a capture cannot reach without clicking as the owner.
> **F-G1 DECIDED 21:5x "A"** (no Discord editing door), **F-G2 06:51 "a"** (a request), **F-G3 06:53 "a"** (member guides only) — §G. Nothing waits on the owner; the seed copy (§C11) is the conductor's next step, then dispatch on the owner's word. ⚠️ **NOT checked:** nothing here met Discord or a browser; the `/help`
> reply and the member rail were read from the source, not rendered. Estimates are estimates.

## A. What exists (measured at `b32fb43`)

| Fact | Where | Why it matters here |
|---|---|---|
| The site is one FastAPI app; `site/public/*.html` is a `StaticFiles(html=True)` mount AFTER the routers, so a page is public but every `/api/*` route is gated | `black_bloc/api/server.py`, [`../access/site.md`](../access/site.md) | a guide's HTML shell can be served to anyone; the CONTENT comes from a gated route |
| A signed-in **member who is not staff** already exists as a state: `member_dependency` (`api/writes.py:82`) answers 503 `member_unknown` / 403 `not_a_member` in words, and takes from a per-member rate bucket | `api/auth.py:member_state`, `api/writes.py:82`, used by `api/tools/requests.py:274` | "server level access" = this dependency, nothing new |
| The rail paints ONE item for a non-staff member (`paintNavFor(member)`, `shell.js:260–264`): Requests | `site/public/assets/shell.js:4` ("The one page a signed-in member who is not staff may use") | Guides becomes the second; that comment and function change |
| Staff-editable text already lives in the DB and is edited from the site AND Discord: `chat_intents` / `chat_lines` (`storage/db.py:412–437`, routes `api/tools/chat.py:298–478`), knowledge notes (`/chat` ▸ Knowledge ▸ Write one down…) | `black_bloc/knowledge.py`, `chat_panel.py` | the pattern for "content in rows, seeded once, never overwritten by a deploy" |
| `/help` is `cogs/core.py:216 help_command` → `help_lines(entries, filter)` (`:130`) — one bold heading per top-level command, `HELP_HEADER`, `HIDDEN_NOTE` for commands hidden when their feature is off, paged by `pages_under_limit` | `cogs/core.py:52–60, 130–148` | the guide link is one more clause per line; nothing else moves |
| `logkinds.FEATURE_PAGES` maps a feature to its site page (17 entries) | `black_bloc/logkinds.py:97` | the guide's "Where it happens" and the `/help` link both key on the feature name |
| Every registry key has a `KEY_TYPES` type, a `KEY_HELP` sentence and `display_value` | `settings_store.py` (**204** keys) | a "Right now" fact is a key rendered the way the panel renders it |
| The self-test posts every panel's root card live in the test channel on every deploy | `black_bloc/selftest.py`, [`selftest-design.md`](selftest-design.md) | the thing a person screenshots is already posted for them after each deploy |
| The deploy script knows the commit (`scripts/deploy.ps1:41 git rev-parse --short HEAD`) and appends `deploys.log`; the app knows only `__version__ = "0.1.0"` (`__init__.py:1`) and the site's `build_id` digest (`api/assets.py`) | `scripts/deploy.ps1`, `api/assets.py:build_id` | the app cannot tell which FEATURE changed between releases unless the deploy writes it down |
| `access/sweeps.md` carries a **Do this / Expect** row for every button in the app (rows 1–359) | [`../access/sweeps.md`](../access/sweeps.md) | the seed copy for every guide already exists in the right voice |
| Filing a request from the site is `POST /api/requests` through the shared function `/request` ▸ **File a request** uses; the route is the sole logger (`web.request.filed`, checklist 34) | `api/tools/requests.py`, `black_bloc/requests.py` | "Something's off" is one call to that function |
| Schema **34**; the DB and its nightly snapshot live on the Fly volume `/data` (`dbsnapshot.py`, `scripts/backup_db.ps1`) | `storage/db.py:11`, [`../access/RECOVERY.md`](../access/RECOVERY.md) | uploaded screenshots go beside the DB and into the same backup, or they are not recoverable |
| ⚠️ **The bot cannot take a screenshot of Discord** (a bot user has no rendered view of anything). **A Claude session CAN** — Claude in Chrome drives the owner's own signed-in Discord web tab and screenshots it (the same browser automation this repo already uses to read usage), and the self-test has already posted every panel's root card in the test channel by then, so shooting a root card needs no click on the owner's account. Pressing buttons on the account through automation is the line this design stays behind: ~~automating a user account is against Discord's terms~~ — **reading and screenshotting the owner's own tab is not** (owner, 2026-09-15 21:5x: "You can screenshot discord in browser mode no? If not make mocks") | Claude in Chrome tools; `selftest.py` | "re-shot each release" is a SESSION step in a runbook, not the owner's chore; screens the self-test does not post (modals, sub-panels, DM cards) are drawn mocks, labelled as such |

## B. The decision in one paragraph

A **guide** is a stored row, not a file: a goal ("Get your stream announced in #live-now"), who it is
for, which feature and command it belongs to, and an ordered list of **steps** — each step ONE
imperative sentence naming the exact button, ONE "expect" sentence, and at most ONE screenshot —
followed by an **"If it did not work"** table and up to four **"Right now"** facts read live from the
bot. The site's new **Guides** page (member-gated through `member_dependency`, the second thing a
non-staff member may open) renders the hub and each guide from `/api/guides`; staff edit every word
in place on the same page (a docked save bar, like Settings), never a form elsewhere. Screenshots
are real captures — a Claude session shoots the cards the self-test posts, through the owner's
browser, and uploads them through that editor; a screen a capture cannot reach without clicking as
the owner is a drawn mock labelled *illustration*. The deploy writes which features changed, and a
shot older than its feature's last change is marked **stale** on the page and on the staff panel
until the next capture session replaces it. `/help` keeps its list and gains a small `guide` link per line.
Every guide ships from a seed written off `access/sweeps.md` in the IKEA voice, seeded once and
never overwritten; **Put the original back** is per step. No new slash command.

## C. The pieces

### C1. Storage (schema 34 → 35)

```
guides        id, guild_id, slug UNIQUE(guild_id, slug), title, goal, audience (member|staff),
              feature (a FEATURE_PAGES key), command ('/golive' or NULL), sort, published (bool),
              seed_hash, updated_at, updated_by
guide_steps   id, guide_id, position, do_text, expect_text (NULL ok), media_id (NULL ok),
              seed_do, seed_expect (the originals — Put the original back reads these)
guide_faults  id, guide_id, position, symptom, answer          ("If it did not work")
guide_facts   id, guide_id, position, kind (setting|probe), ref (a registry key, or a probe name)
guide_media   id, guild_id, guide_id, step_id (NULL ok), file (relative under /data/guides/),
              sha256, width, height, bytes, source (capture|mock), surface (discord|website), shot_release, shot_by,
              shot_at, caption, stale (bool), stale_since
guide_releases release (text, e.g. 'v112'), commit, shipped_at, changed_features (JSON list)
```

- `slug` is the URL and the `/help` link target: `{origin}/guides.html#golive-announce`.
- One partial unique index keeps one `published` guide per ~~`(guild_id, command)`~~
  **`(guild_id, command, audience)`** (widened at the G1 build, 2026-09-16, `guides-core` — the
  seed in §C11 publishes a member AND a staff guide against `/event`, so the narrower index
  refuses the shipped seed on the first boot; **Deviation 1**), so `/help` never has two links to
  choose from for one line (checklist 6). `/help` links member guides only, for the same reason
  F-G3 hides a staff guide from a member (**Deviation 2**).
- Media files live at `/data/guides/<id>.<ext>` on the volume, served by `GET /api/guides/media/{id}`
  (member-gated, `Cache-Control: private, max-age=86400`, ETag = sha). **Not** under `site/public` —
  that mount is public and ships with the image. `scripts/backup_db.ps1` grows one line to copy the
  folder with the snapshot; [`../access/RECOVERY.md`](../access/RECOVERY.md) gains the row.
- Accepted uploads: PNG/JPEG/WebP, ≤ 2 MB, longest side ≤ 1600 px (re-encoded server-side with
  Pillow — already a dependency? **measure at build**; if not, refuse over-size in words rather than
  add a dependency for this).

### C2. The wording rules — "IKEA": empirical, no fluff

These are enforced by the editor's linter (`black_bloc/guides.py:lint_step`), which **warns, never
refuses** (staff final say): a step that trips a rule saves with an amber note beside it.

| Rule | Warns when |
|---|---|
| One action per step | `do_text` contains " and then ", " then ", or two bold button names |
| Name the control | `do_text` has no `**bold**` span (buttons, selects and menu items are written **bold**, exactly as Discord shows them) |
| Imperative, second person | `do_text` starts with "You can", "Simply", "Just", "Easily", "Please" |
| Short | `do_text` > 140 characters; `expect_text` > 200 |
| Expect is observable | `expect_text` present and starts with a noun or "The"/"A"/"Your", not "It should" |
| No adjectives of ease | contains "easy", "simple", "quick", "intuitive" |
| Facts, not promises | contains "always", "never fails", "instantly" |

The page renders a step as: **N** · `do_text` · (screenshot) · `EXPECT` `expect_text`. No intro
paragraph, no closing paragraph. The hub card is `title` + `goal` (one sentence) + three pills. That
is the whole vocabulary; the seed follows it and the linter keeps edits inside it.

### C3. Editing — every word, in place, by staff

- **Where:** the guide page itself. A staff visitor sees **Edit this guide** in the page head; it
  turns every text into an input, every step into a row with **↑ ↓ + ×**, the faults table and the
  facts list likewise, and docks the site's existing save bar ("N changes pending · Save Changes ·
  Discard"). Members never see the button. Same `settingsEditor`/`saveBar` plumbing the Settings page
  uses (`site/public/assets/ui.js`), not a second implementation.
- **Per step:** **Put the original back** (restores `seed_do` / `seed_expect`), **Replace
  screenshot…** (upload), **Remove screenshot**. Per guide: **Unpublish** / **Publish** (an unpublished
  guide is hidden from members and from `/help`, visible to staff with a pill), **Reset the whole
  guide to the original** behind a confirm.
- **New guide:** **New guide** on the hub (staff only): title, goal, audience, feature, command → an
  empty guide with one blank step. Slug derived from the title, editable once, unique.
- **Who:** `guides_who_edits` (§C9): `staff` (default — the same set that sees the staff channel) or
  `manage_guild`. Read at save time, not render time (checklist item: re-check on every press, row 290
  precedent).
- **Writes:** `PUT /api/guides/{slug}` takes the WHOLE guide (steps, faults, facts) and syncs to it,
  the way `PUT /api/rolemenus/{name}` takes the whole option list — one write, one `web.guide.edited`
  row carrying the diff summary (`steps +1 −0 ~2, faults ~1`). Media upload is its own
  `POST /api/guides/{slug}/media` and one `web.guide.media_replaced` row. Checklist 34: these routes
  are the sole loggers, so `note()` is correct here.
- ⚠️ **No Discord editing door** — fork **F-G1**, DECIDED (a) by the owner; the reason is written
  there, and the waiver goes to `KNOWN_ISSUES.md` at the build's landing. The settings KEYS are both ways as always.

### C4. Screenshots — real captures by a session, drawn mocks where a capture cannot reach

1. **Capture is a session step, in the owner's browser.** After a deploy whose `release.json`
   (step 2) names a feature, the landing ritual gains one step: the session opens
   [`../access/guides-capture.md`](../access/guides-capture.md) (new runbook, written at the G2
   landing) and, with Claude in Chrome: (i) opens the test channel in the owner's signed-in Discord
   web tab, where the self-test has just posted every panel's root card; (ii) scrolls each stale
   card into view, reads its bounding box with the page-script tool, screenshots the tab and crops
   with Pillow (`scripts/scan/crop_shot.py`, gitignored — not bot code); (iii) opens the dashboard
   page for a website shot (the owner is signed in there too); (iv) uploads each file through the
   guide's own **Replace screenshot…** in the same browser, which is the one write path.
   ⚠️ **The session presses nothing on the owner's Discord account** — it reads and screenshots.
   That is the line: the self-test posts the cards so no interaction is needed, and a screen that
   WOULD need one is a mock (4).
2. **The deploy records what changed.** `scripts/deploy.ps1` gains one step before `flyctl deploy`:
   `git diff --name-only <last line of deploys.log>..HEAD` mapped through `guides.FEATURE_PATHS`
   (one home: a dict `feature → [path prefixes]`, e.g. `golive → [black_bloc/golive.py,
   black_bloc/cogs/content/golive.py, black_bloc/api/tools/golive.py, site/public/golive.html,
   site/public/assets/page-golive.js]`) → written to `site/public/assets/release.json` as
   `{release, commit, changed_features}`. The file ships inside the image. ⚠️ The script must
   refuse to deploy if `release.json` is dirty-but-uncommitted the way check-clean already refuses;
   the file is committed by the deploy commit, not left behind.
3. **Boot marks stale.** `guides.reconcile_releases(bot)` on `cog_load` (and every 5 min, checklist 25)
   reads `release.json`, inserts the `guide_releases` row if new, and sets `stale = true, stale_since`
   on every `guide_media` row whose `feature ∈ changed_features` and `shot_release < release`. One
   log row per release: `guide.shots_stale` with the count and the features. The staff line on the
   hub ("3 screenshots need re-shooting") IS the capture session's to-do list — `GET /api/guides/stale`
   returns it as JSON so the session reads it with the operator token before opening a browser.
4. **Mocks for what a capture cannot reach.** A modal, a sub-panel (`Streamers…`, `Settings`), a DM
   card, or a state the self-test does not post (a linked member's panel) is drawn — HTML in the
   Discord look, the way the design canvas drew them — exported to PNG once and uploaded with
   `source = mock`. The page labels it *illustration, drawn from v110*; a capture is *screenshot,
   v110*. A mock goes stale by the same rule and is redrawn by the same session step. **A mock is a
   fallback, never a substitute for a root card that can be shot.**
5. **Stale is visible in three places:** a `STALE` pill on the picture for members ("from v110 —
   the feature changed in v112"), the hub's staff-only line with the count, and the stale list
   route. The `/help` reply does **not** mention it (members cannot act on it).
6. **A picture is never deleted by staleness.** An old real picture beats no picture; only an upload
   replaces it, and replacing clears `stale`.
7. Alt text is the step's `do_text`; the caption is `screenshot|illustration · <release> · <name>`.

### C5. "Right now" — live values, chosen by staff

- A guide carries up to **4 facts**. Kind `setting`: any registry key except the four core keys
  behind `settings_core_keys_admin_only` and every `*_log_level` (refused in words by the editor — a
  member does not need them and the panel does not show them either). Rendered as the panel would:
  `display_value` + names resolved from the cache (`api/names.py`, never a fetch) + the key's
  `KEY_HELP` sentence. A mode key renders as the site's mode pill.
- Kind `probe`: a fixed list in `guides.PROBES`, each a coroutine `(bot, guild) → str` reusing an
  existing reader: `golive.linked_count`, `golive.live_now`, `events.open_count`,
  `requests.open_count`, `tempvoice.open_rooms`, `polls.open_count`, `birthdays.next`,
  `raidtrain.next`, `test_mode` (whether the guard is on, and the test channel's name). No new
  queries; each maps onto a function the status pages already call.
- `GET /api/guides/{slug}` resolves the facts server-side and returns `{fact, value, help,
  read_at}`. The page shows `read_at` as "updated N s ago" and re-reads every 60 s while open.
- The hub's strip is fixed, not editable: test mode on/off, and the count of features in shadow /
  off — read from `/api/status` the rail already fetches.

### C6. Access, pages and the rail

- Two new pages: `site/public/guides.html` (hub, and a guide by `#slug` — one page, the way
  `requests.html#r-{id}` anchors a card) and nothing else; `assets/page-guides.js`. Mock: two pages
  → **18**, routes in `site/mock/contract.json` grow by the C7 table. `noindex` meta like every page.
- Gate: `GET /api/guides`, `GET /api/guides/{slug}`, `GET /api/guides/media/{id}` under
  `member_dependency`; the writes under `staff_dependency` + the `guides_who_edits` check inside.
  ⚠️ `member_dependency` takes from the member WRITE bucket on every call (`writes.py:92`) — the
  build adds a read-only twin (`member_read_dependency`) or lifts the bucket out; **measure the
  bucket size first** and say which. A member reading four guides must not be told to slow down.
- Signed out: the page paints the existing gate row and **Sign in with Discord**; not a member: the
  existing "not a member" sentence. The five-state machine is untouched (`permission-ux.js`).
- Rail: `paintNavFor(member)` paints **Requests and Guides** for a non-staff member; the `shell.js:4`
  comment is rewritten. Staff see Guides under **Overview** after Requests (`GROUPS`). `Ctrl K`
  palette indexes guide titles (`page` kind, one line in the palette's source list).
- `guides_mode` off (§C9) hides the rail item and the `/help` links; the URL still answers for staff
  with a pill "Guides are off for members". `guides_mode` is not hidden-when-off (nothing to hide —
  there is no command).

### C7. `/help` — one clause per line, one button

- `help_lines` gains a `guides: dict[str, str]` argument (command name → url) built once per call from
  the published guides (`guides.links_for(bot, guild_id)`); a line whose command has a guide becomes
  `**/golive** — Announce your streams … · [guide](url)`; one with none is unchanged. The link is
  masked Markdown, which Discord renders as a small link — no embed, no select, no new message.
- The reply's last page gains one `discord.ui.Button(style=link, label="All the guides", url=…)`
  when at least one guide is published and `guides_help_links` is true. `HELP_HEADER`,
  `HIDDEN_NOTE`, the filter and the paging are untouched; `pages_under_limit` already accounts for
  the longer lines.
- `allowed_mentions=none()` stays (the urls are ours, the titles are staff text — checklist 11).

### C8. "Something's off" — files a request

- Two buttons at the foot of every guide: **This guide was right** (writes one `guide.confirmed` row
  with the slug and release — a count staff can read, nothing else) and **Something's off** → a
  one-field box ("what was wrong?") → `POST /api/requests` through the shared filer with `what` =
  `Guide "<title>", step N: <text>` and `why` = the guide url. The requester is the signed-in member,
  exactly as filing from the Requests page. Rate-limited by the same member bucket. Behind
  `guides_fault_files_request` (§C9) — off makes the button a mailto-less "tell a Lead" sentence.

### C9. Settings keys (checklist 33) — group `guides`, all in `KEY_TYPES` / `KEY_HELP` / `labels.js`

| Key | Type | Default | Help sentence |
|---|---|---|---|
| `guides_mode` | enum on/off | **on** | whether members see the Guides page and `/help` shows guide links |
| `guides_who_edits` | enum staff/manage_guild | **staff** | who may edit a guide's wording and screenshots |
| `guides_help_links` | bool | **true** | whether `/help` puts a guide link beside each command |
| `guides_show_facts` | bool | **true** | whether guides show live values read from the bot |
| `guides_fault_files_request` | bool | **true** | whether "Something's off" files a request, or just says to tell a Lead |
| `guides_log_level` | the log-level family | family default | generated like every other `_log_level` |

204 → **210** keys; `settings_api.NAMESPACE_OVERRIDE` needs nothing (prefix `guides_`). The `/settings`
panel's group select is at **23** namespaces against a 25-option cap (TODO, "still open" bullet) —
this makes **24**; the build reports the count and does not add a `Find…` path unless it hits 25.

### C10. Log kinds (`logkinds.py`)

`guide.edited`, `guide.media_replaced`, `guide.published`, `guide.unpublished`, `guide.created`,
`guide.reset` (routine, all through `kind_via` with `via=VIA_WEBSITE` since the website is the only
door — checklist 34 says the route is then the sole logger and `note()` is right); `guide.shots_stale`
(routine, the bot); `guide.confirmed` (routine, hidden by default like self-test); `guide.fault_filed`
is NOT a kind — the request's own `web.request.filed` row is the record. Feature `guides` →
`FEATURE_PAGES["guides"] = "guides.html"`.

### C11. The seed

`black_bloc/guides_seed.py` (or JSON beside `personality_pool.json`): one entry per guide below,
written by the conductor off `access/sweeps.md` in the §C2 voice BEFORE dispatch, so the builder
seeds and does not author. Seeded on `cog_load` when the `guides` table has no row for the guild
(`guide.seeded`, one row); a later deploy with a changed seed never touches an existing guide — it
only refreshes `seed_do` / `seed_expect` (what **Put the original back** restores), and logs
`guide.seed_refreshed` with the count. First set, member then staff:

| Slug | Title | Command | Sweeps rows the steps come from |
|---|---|---|---|
| `golive-announce` | Get your stream announced in #live-now | `/golive` | 109–112 |
| `pings-follow` | Follow a streamer's pings | `/pings` | 38–40, 126–134 |
| `event-propose` | Propose an event | `/event` | 32, 73–79, 323–326, 329–334 |
| `birthday-set` | Set your birthday, in your own time zone | `/birthday` | 87–93 |
| `voice-room` | Make your own voice room | `/voice` | 3, 20, 135–143 |
| `poll-vote-make` | Vote in a poll, or make one | `/poll` | 6, 8, 80–86, 300–304 |
| `request-file` | Ask for something to be built | `/request` | 14–15, 66–68 |
| `chat-memory` | Talk to the bot, and see what it remembers | `/memory` | 10, 104–108 |
| `raidtrain-slot` | Take an hour on a raid train | `/raidtrain` | 48–50, 163–172 |
| `apply-form` | Apply to the Twitch Team | `/apply` | 53–57, 94–102 |
| `event-review` (staff) | Approve or deny an event | `/event` | 73–79, 351–359 |
| `modmail-ticket` (staff) | Handle a modmail ticket | `/modmail` | 200–207, 219–230 |
| `mod-case` (staff) | Warn, time out, and correct a case | `/mod` | 208–218 |
| `automod-arm` (staff) | Arm automod without surprising anyone | `/automod` | 144–154 |
| `honeypot-set` (staff) | Set a honeypot trap | `/honeypot` | 188–199 |
| `rolemenu-post` (staff) | Post a role menu | `/rolemenu` | 1, 22–23, 173–182 |
| `feature-modes` (staff) | Turn a feature on, off, or to shadow | `/settings` | 183–187, 231–244 |

Seventeen guides, zero pictures at seed time (the first capture session at the G2 landing shoots
the root cards and draws the first mocks; the page renders a step without a picture as text only,
never a broken image).

## D. Calls the owner may overturn (each is one key or one line)

1. Facts from the four core keys and the `*_log_level`s are refused → one line in the validator.
2. Screenshots ≤ 2 MB, ≤ 1600 px → two constants; a registry key if the owner wants to move them.
3. A stale shot stays up with a pill rather than being hidden → one branch in the renderer.
4. The linter warns and never refuses → one flag.
5. `/help`'s link is masked Markdown per line + one button → §C7; the button alone is one `if`.
6. One published guide per command → the partial unique index; drop it to allow two.

## E. Out of scope (so nobody builds it by accident)

Video or GIF captures; a session PRESSING buttons on the owner's Discord account to reach deeper screens (those are mocks); the bot rendering its own panels to images (a browser in the container); per-member progress
("you did step 2"); translations; a Discord editing panel (fork F-G1 unless the owner picks b);
guides for the website's own pages (the site is the guide for itself — the Settings page's
`KEY_HELP` sentences already are); comments or threads under a guide; a public, signed-out guide
(the owner chose server level).

## F. Build brief essentials (the conductor's dispatch copies these)

- Two dispatches, Opus, each committing at clean boundaries in its own worktree off a clean `main`:
  **G1 core** — schema 35, `black_bloc/guides.py` (rows, lint, PROBES, FEATURE_PATHS,
  `reconcile_releases`, `links_for`), the seed, the API routes + contract + mock, the `/help` clause
  and button, the six keys, the log kinds. Est. **200–280k**.
  **G2 pages** — `guides.html` + `page-guides.js` (hub, guide, the in-place editor, the docked save
  bar, upload, stale pills, the two foot buttons), the rail change, the palette entry, the
  `deploy.ps1` step + `release.json`, `GET /api/guides/stale`, the backup line, the RECOVERY row and
  the `access/guides-capture.md` runbook (the session's step-by-step, with the crop helper). Est.
  **220–320k**. The FIRST capture session runs at the G2 landing and is the runbook's drill.
  ⚠️ Both are multi-layer; prep per the global rule (clean tree, before-read, commit often).
- Tests mirror the package: `tests/test_guides.py`, `tests/api/tools/test_guides.py` (contract +
  member gate: a signed-out read is 401 in words, a non-member 403, a member 200, a staff write 200,
  a member write 403), `tests/cogs/test_core.py` grows the `/help` link cases (a command with a
  guide, without one, `guides_help_links` false, `guides_mode` off), `tests/test_logkinds.py`'s AST
  guards must stay green, `tests/api/test_contract.py` reads the new routes from `contract.json`.
  Reversed-order run (`BB_REVERSE=1`) as always.
- Prove before merge: seed → 17 rows, 0 media; lint fires on a "Simply press" step and saves anyway;
  a `release.json` naming `golive` flips exactly the go-live shots stale and no other; `/help`
  output measured under the 2000-char page limit with 17 links; the member bucket not tripped by 10
  guide reads in a minute.
- Sweep rows at landing (numbered at the merge): the hub as a member; a guide as a member with
  facts live; edit a step as staff and see the save bar; upload a screenshot; deploy a go-live change
  and see the pill; press Something's off and find the request; `/help` shows the links; `guides_mode`
  off hides everything.
- Docs ritual: this header → BUILT → LIVE; `info/README.md` row; `feature-list.md` row **G1**;
  `access/site.md` page count 17 → 18; `architecture.md` fact table; RECOVERY row for
  `/data/guides/`; `access/README.md` row for the capture runbook; the landing ritual in `TODO.md`
  gains "capture session if `release.json` names a feature"; `code-notes.md` section by NAME.

## G. Forks — ALL THREE DECIDED 2026-09-15/16 (kept with their reasoning)

- **F-G1 — a Discord editing door. ✅ DECIDED 2026-09-15 21:5x, owner verbatim "A": none.** (a) **None** — wording and screenshots are edited on the website
  only; the Discord half of this feature is `/help`'s links, and a multi-field long-text edit is what
  the website exists for (the same reason the Settings page, not the panel, owns `bot_bio`). This is
  a deliberate exception to checklist 33's "both ways" for CONTENT, not for the keys — record it in
  `KNOWN_ISSUES.md` as `WAIVED` if chosen. (b) A `/guides` staff panel with **A guide…** → **A step…**
  → a modal per step (five fields is Discord's cap; the faults table and facts would need more
  modals). Recommend **(a)**; the owner's words were "webpages".
- **F-G2 — where "Something's off" lands. ✅ DECIDED 2026-09-16 06:51, owner verbatim "a": a request.** (a) A request, as designed (staff see it where they see
  everything else). (b) A `guide.fault` log row only, no request. Recommend **(a)**.
- **F-G3 — the hub for a member. ✅ DECIDED 2026-09-16 06:53, owner verbatim "a": member guides only.** (a) Member guides only, staff guides hidden. (b) Both, staff ones
  marked. Recommend **(a)** — a member cannot press any button a staff guide names.

## Deviations

> Written by the G1 build (branch `guides-core`, off `main` at `ecb2bb6`), 2026-09-16. Every
> departure from §A–§G above and why. G2's own list goes under it.

1. ⚠️ **The partial unique index is `(guild_id, command, audience)`, not `(guild_id, command)`
   (§C1).** The seed in §C11 publishes **two** guides against `/event` — `event-propose` (member)
   and `event-review` (staff) — so the literal index makes the shipped seed un-seedable. Measured:
   seeding seventeen guides raised `sqlite3.IntegrityError: UNIQUE constraint failed:
   guides.guild_id, guides.command`. §C7's *reason* for the index is kept whole, because `/help`
   links member guides only (2 below), so no line ever has two links to choose from.
2. ⚠️ **`/help` links MEMBER guides only, never a staff one.** F-G3 hides a staff guide from a
   member, so a `[guide]` clause on `/automod` or `/mod` would be a 404 for everybody who is not
   staff — a dead link in the one place a member is most likely to press it. `guides.links_for`
   filters `audience = 'member'`: the **ten** member guides carry a link, the seven staff ones do
   not. Staff reach theirs from the hub.
3. **Seeding runs on the guides loop's FIRST TICK, not inside `cog_load` itself (§C11).**
   `cog_load` runs before the gateway is ready, so `bot.guilds` is empty there and a seed written
   from it would write nothing at all. `Core.guides_loop`'s `before_loop` is `loops.wait_ready`
   and its first tick is at boot — the same moment, with a guild list. The loop is 5 minutes
   (checklist 25) and carries `@loop.error` + `loop_health("guides_loop")` like every other.
4. ⚠️ **A screenshot is uploaded as base64 in a JSON body, not as multipart (§C3).**
   `api/server.py:same_site_writes` answers **415 in words** to any `/api/*` write whose
   content-type is not `application/json`, so a multipart upload cannot reach the route at all.
   `POST /api/guides/{slug}/media` takes `{filename, data, step_id, caption, source, surface,
   shot_release}` and `data` may be a bare base64 string or a `data:` URL.
5. ⚠️ **Pillow is NOT a dependency — measured, not assumed** (`import PIL` in the repo venv:
   `ModuleNotFoundError`). §C1's own fallback applies: nothing is re-encoded, and a picture over
   **2 MB** or over **1600 px** on its longest side is refused in a sentence that says what to do.
   `guides.picture_size` reads the dimensions out of the PNG / JPEG / WebP header, so no
   dependency was added to find them.
6. **`GET /api/guides/media/{id}` is exempt from the `no-store` middleware.**
   `api/server.py:security_headers` forced `Cache-Control: no-store` onto every `/api/*` response,
   which silently overwrote §C1's `private, max-age=86400`. One named prefix,
   `server.KEEPS_ITS_OWN_CACHE`, is the exemption; the ETag is the sha and a repeat read answers
   **304**.
7. **`guide.confirmed` is NOT a log kind yet; `guide.deleted` IS (§C10).** §C8's two foot buttons
   are G2's page work, so nothing in G1 can write `guide.confirmed`, and
   `tests/test_logkinds.py::test_no_classification_entry_is_dead` refuses a classification entry
   nothing emits. `DELETE /api/guides/{slug}` is in G1's scope and §C10 named no kind for it — a
   write that leaves no log row is worse than one kind more.
8. **`guides` is NOT in `logkinds.HIDDEN_BY_DEFAULT`** although §C10 asks for `guide.confirmed` to
   be hidden like the self-test's rows. That list is per **feature**, not per kind, so adding
   `guides` would have hidden every guide edit from the Logs page as well. Revisit it at G2, when
   `guide.confirmed` exists and its volume is measurable.
9. ⚠️ **Two structural guards gained ONE named exception:
   `logkinds.FEATURES_WITHOUT_A_COMMAND = ("guides",)`.** `guides` joins `logkinds.FEATURES`
   so that `guides_log_level` generates with every other feature's and the Logs page can filter on
   it — but F-G1 gives it no Discord panel and no slash command, which
   `tests/test_bot.py::test_every_features_logs_is_a_panel_button…` and
   `::test_every_log_level_names_a_command_that_still_exists` both assumed of every feature. The
   exception is one constant with the reason beside it, read by both tests; `LOG_LEVEL_COMMANDS`
   simply has no `guides` row, and `log_level_help` already drops the panel clause when there is
   none.
10. **The registry is 206 → 212, not 204 → 210 (§C9).** 204 was measured at `b32fb43`; `main` at
    `ecb2bb6` holds **206**. The five decided keys plus `guides_log_level` make **212**. The
    `/settings` group select is **23 → 24** namespaces exactly as designed, so no `Find…` path was
    added (the cap is 25).
11. **`seed_hash` doubles as "is this guide seeded".** §C1 lists no `seeded` column and one would
    be a second home for the same fact: a guide with a `seed_hash` is one Black Bloc ships with,
    which is what **Reset the whole guide** reads and what makes DELETE refuse in words.
12. **A new guide starts with ZERO steps, not one blank step (§C3).** `PUT` refuses a step with
    nothing in it (`STEP_NEEDS_TEXT`), so a blank row would be a guide that cannot be saved until
    it is filled or removed. The page adds the first step.
13. ⚠️ **`black_bloc/guides_seed.json` was NOT reworded, and it trips the linter's first rule on
    36 of its 70 steps.** Measured. Almost every one is a step that bolds a button AND a value —
    *"Press **Propose an event…** and pick a **day**"* — which §C2's literal *"two bold button
    names"* counts as two actions. The linter warns and the save happens (§D.4), so nothing is
    blocked, but the editor will paint amber on half the shipped copy. Narrowing the rule to two
    bold spans that both look like CONTROLS is one line in `guides.lint_step`; the conductor owns
    the call, so nothing was changed here.
14. **Not built, and left to G2 as §F says:** `site/public/guides.html`, `assets/page-guides.js`,
    the rail change in `shell.js`, the `Ctrl K` palette entry, the `scripts/deploy.ps1` step that
    writes `site/public/assets/release.json`, the `scripts/backup_db.ps1` line for
    `/data/guides/`, the RECOVERY row, `docs/access/guides-capture.md`, and §C8's two foot buttons
    (`This guide was right` / `Something's off`) with `guide.confirmed`. `guides.FEATURE_PATHS`
    and `guides.features_changed()` are in place for the deploy step to call.

## G2 deviations

> Written by the G2 build (branch `guides-pages`, off `main` at `cad1abc`), 2026-09-16.
> Every departure from §A–§G and from G1's own list above, and why. Each one is a fact
> measured on this branch, not a preference.

1. ⚠️ **The hub's Right now strip is read from `GET /api/guides`, NOT from `/api/status`
   (§C5, last bullet).** `/api/status` is `staff_dependency`, and `shell.js:paintShell`
   returns early for a member-only viewer *specifically so a member is asked for no staff
   route*. Following §C5 literally would have given a member a hub with no strip at all,
   or a 403 on every load. `guides.right_now(bot, guild)` is the one home and it answers
   `{test_mode, test_channel, on, shadow, off}` inside the hub payload, reusing
   `api.status.feature_modes` so the mode list is still counted in one place.
2. ⚠️ **`guide.confirmed` is NOT hidden by default, and cannot be without hiding every
   guide edit (§C10).** G1's deviation 8 left this to be measured at G2; measured:
   `logkinds.hidden_by_default_patterns()` builds from `like_patterns(feature)`, which is
   every kind head belonging to a FEATURE. There is no per-kind entry. Putting `guides` in
   `HIDDEN_BY_DEFAULT` would take `guide.edited`, `guide.published` and the rest off the
   Logs page's default view as well, which is the opposite of what staff want. The kind
   is in `ROUTINE`, so it is already out of the "important only" view — which is what the
   Logs page opens on. **Left visible, deliberately.**
3. **Four fields and one route were added to G1's API**, each minimal and each with a
   test, because the page could not be built honestly without them:
   - `right_now` on the hub (1 above);
   - `feature_mode` on every guide row — §C6's card and §C6's rail both show a mode pill,
     and nothing in G1's payload carried one. `None` for a feature with no `_mode` key
     (`core`), because a pill saying "not set" is a lie about a feature with no switch;
   - `features` and `fact_choices` on the hub, staff only — the editor's feature picker
     and fact picker. The alternative was the page re-deriving `guides.refused_setting`'s
     rule in JavaScript, which is checklist 15's exact failure. A member gets
     `{"settings": [], "probes": []}`;
   - `fault_files_request` on a guide (asked for by the brief) so §C8's right-hand button
     is drawn only when filing is on;
   - `POST /api/guides/{slug}/confirmed`, §C8's left-hand button, member-gated through
     `member_read_dependency` like the reads.
   Contract: **17 → 18 pages, 159 → 160 routes.**
4. **The hub's filter chips are "who it is for", "where you do it" and "only what is on"
   (§C6 names no chips; the brief did).** "Where you do it" is derived from `command`: a
   guide with one is done in Discord, one without is done on the site. There is no column
   for it and one would be a second home for what `command` already says. The audience
   chips are drawn for staff only — F-G3 means a member's list is member guides already.
5. **The stale pill on a hub CARD is staff-only; the pill on the picture is everyone's.**
   §C4.5 makes the count a staff line and the pill a thing on the picture. The card's pill
   is a count, so it follows the staff line.
6. **An upload is refused, in words, while the editor has unsaved changes.** The media
   POST lands immediately and the page must reload to show the new picture, which would
   throw away everything typed. §C3 does not say what happens here; losing a staffer's
   typing silently was the alternative. Same for a step that has not been saved yet — it
   has no id for the bot to file a picture against, and the sentence says so.
7. **Publish / Unpublish is a pending change on the save bar, not an immediate write.**
   §C3 lists it beside **Reset** and **Delete**, which are immediate; but §C3 also says
   the PUT takes the WHOLE guide including `published`, and two write paths for one field
   is two places for it to disagree. Reset and Delete stay immediate (both are confirmed).
8. ⚠️ **`scripts/deploy.ps1` writes and commits `release.json` FIRST, before the
   check-clean gate.** §C4.2 says "one step before `flyctl deploy`" and that the file is
   committed by the deploy commit. The gate at the top of the script refuses a dirty tree,
   so a file written later in the run would either be swept into a commit nobody reviewed
   or left behind. It stages exactly one path — never `git add -A`, per the global rule
   about a job that commits beside an agent — and the check-clean two lines later still
   refuses anything else dirty.
9. **The release step REFUSES when the last `deploys.log` line's commit is unreadable.**
   §C4.2 does not say. The silent alternative — an empty diff — is indistinguishable from
   "nothing changed", so a whole release of screenshots would be wrong and nobody would
   know. A one-line fix to `deploys.log` is cheaper. When the *number* is missing (§C4.2's
   own fallback), the release is named after the commit and the script says so on stderr.
10. **`release.json`'s `commit` is HEAD BEFORE the release commit**, because that commit
    does not exist until the file is written. It names the code the diff was taken
    against; `deploys.log` carries the hash that actually shipped.
11. **The page speaks a sentence when a picture will not load**, rather than leaving the
    reserved box empty. §C4.6 says a picture is never deleted by staleness; it says
    nothing about one that 404s. A silent hole is indistinguishable from a page fault.
12. **`docs/access/guides-capture.md` is written but 🔴 NEVER DRILLED**, and its header
    says so at the top rather than in a footnote. §F says "the FIRST capture session runs
    at the G2 landing and is the runbook's drill" — that session has not run. No browser
    opened Discord for it, nothing was cropped, nothing was uploaded to a live guide.
13. **Nothing in G1's list was reversed.** Deviations 1–14 there all still hold; 14's list
    of what it left to G2 is now built, except the drill in 12 above.

### Mark-all-stale

Branch `guides-stale`, off `main` at `c6a341a`. The follow-up §C4.3 does not describe: a
staff move that marks EVERY picture, for what a release never can reach (owner, 2026-09-16
15:5x, "we need to update all screen shots once shadow mode is off to not have that message
and to not have the old channel"). ⚠️ **Nothing below has met the live app** — the whole
verification is `pytest`, `ruff`, `check.mjs` and one browser pass over the MOCK.

1. ⚠️ **`guides.mark_all_stale(db, guild_id)` takes NO `reason`, and leaves NO log row.**
   The brief gave it `*, reason`. `reason` has no column on `guide_media` and the row is the
   ROUTE's — checklist 34 says the route is the sole logger here, and `tests/test_logkinds.py
   ::test_a_route_never_notes_an_event_its_shared_path_already_logged` fails the `note()` the
   moment the shared path logs the same kind. So the module stays the sibling of `mark_stale`:
   it marks and counts, and its caller writes the row. The reason reaches the log as the
   route's `note(reason=…)` and as `details["reason"]`.
2. **The route's kind is `web.guide.shots_stale` — the existing kind with the website head**,
   not a new one. §C10 lists `guide.shots_stale` as the bot's; the same event with a person
   behind it takes the `web.` head, which is what `via_of` reads and what the Logs page's Via
   column says. `logkinds.py` needed no change; the note table in `tests/test_logkinds.py` and
   `contract.json`'s `action_kinds` did.
3. **The row is written even when it marked nothing.** A press that found every picture
   already marked is a result, not a non-event, and `count: 0` in the log is how a later
   session tells "nobody pressed it" from "it was already done".
4. ⚠️ **The hub's Screenshots-to-re-shoot block is now drawn for staff whatever the count.**
   It used to render only when `payload.stale` was non-zero — and none-stale is EXACTLY the
   state the cutover presses the button in, so the button would not have existed when it was
   needed. The table's own `Nothing needs re-shooting.` empty line carries the zero case.
5. **The button is a card under the table, not a control beside the count.** §C4.5's "staff
   line with the count" is the section's own count pill; hanging a destructive-ish move off a
   count would put it where a member's eye goes first on a page they share with staff.
6. **The confirm's reason box is optional and capped at 200** (`guides.REASON_MAX`), the way
   a caption is. A forced reason is a box people type `.` into.
7. **The mock seed gains a SECOND picture, on `house-rules`, NOT stale.** The one seeded
   picture was already stale, so the mock could only ever answer *"Every screenshot was
   already marked."* and no browser pass could see the sentence that matters.

### Found at the v125 landing (conductor, 2026-09-17 15:0x, v127)

The `front-door` guide (seeded at v125, guides 17 → 18 in the file) never reached the live database: `Core._seed_guides`
called `seed_guides` only when a guild had NO guides at all, and `refresh_seeds` never inserts. Every guide added to the
seed after a guild's first seeding was invisible — the youtube-live build had named the same limitation for steps and
faults (its deviation 11). Fixed: `seed_guides` (idempotent by slug) runs on every guides tick and logs `guide.seeded`
with the count of what it added; `refresh_seeds` follows as before. One test. Steps and faults added to an EXISTING
guide still reach a fresh seed only — that stays a known limit (**Reset the whole guide** brings them in).

### Several guides per command (branch `guides-per-command`, off `main` `582977f1`, 2026-09-25)

Owner, 2026-09-25 20:3x: *"why does marathon have an empty event category"*. §D6 exercised: the index is gone.

1. **Schema 66.** `guides_one_published_command` is dropped at boot (`DROP INDEX IF EXISTS`, the additive way) and
   `guides_by_command (guild_id, command, audience)` is a plain index for the lookups. Deviation 1 above is history.
2. **`/help` puts every published MEMBER guide for a command on that command's heading line.** One guide keeps the
   old clause exactly (` · [guide](url)`); two or more each read ` · [guide: <title>](url)`, ordered by `sort`, then
   title. They ride the heading rather than a line each so a `/help` filter keeps them with their command and the page
   count does not grow. Staff guides are still never linked (Deviation 2). `/event` for a member now reads
   `**/event** — … · [guide: Propose an event](…#event-propose) · [guide: See when BaF runs at a marathon](…#marathons-follow)`
   (titles as seeded; staff-edited titles show as edited).
3. **The site's refusal is REMOVED, words and all** (`COMMAND_TAKEN`, `409 command_taken`). No unpublished-duplicate
   case needed it: a new guide is always made unpublished, and publishing a second guide for a command is now allowed.
   The editor's and the new-guide form's hint now say several guides may share a command.
4. **The hub keeps a command's cards together** (`page-guides.js:byCommand`, stable, in the API's order); every card's
   foot still reads `/command · N steps`.
5. **The seed:** `marathons-follow` and `marathons-manage` → `/event`, `ping-windows` → `/golive`. ⚠️ The brief named
   four; `golive-channels` already carried `/golive` in the seed (it was the first staff `/golive` guide), so only three
   were null.
6. ⚠️ **The boot refresh fills a NULL command and touches nothing else a person wrote.** `refresh_seeds` runs only for
   a guide whose `seed_hash` differs from the shipped entry (the three changed entries do, once); for those it now sets
   `command = COALESCE(command, <seed command>)` beside the `seed_hash`, `seed_do`, `seed_expect` it always wrote. It
   does NOT write title, goal, audience, feature, sort, published, steps' shown text, faults, facts or media, and it
   never overwrites a command that is set. Limit: a staffer who had deliberately blanked one of these three commands
   gets it back once, at the first boot after this ships (the hash then matches, so never again); clearing it again
   sticks.
