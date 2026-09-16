# Guides — one web page per goal, staff-editable, with real screenshots and live values

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **DESIGN, not built, not
> dispatched** (owner, 2026-09-15: "dont build yet jusy mock", then "write the design doc").
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
> **Last verified: 2026-09-15 22:05 Phoenix** — every `path:name` in §A was read on `main` at
> `b32fb43` (v110 live). ⚠️ **NOT checked:** nothing here met Discord or a browser; the `/help`
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
| ⚠️ **A bot cannot take a screenshot of Discord, and automating a user account to do it is against Discord's terms** (self-bots). Nothing in the tree or `reference-bots.md` contradicts this | — | "re-shot each release" is a PERSON with a phone or the desktop app; the bot's job is to know WHEN a shot is stale and to say so |

## B. The decision in one paragraph

A **guide** is a stored row, not a file: a goal ("Get your stream announced in #live-now"), who it is
for, which feature and command it belongs to, and an ordered list of **steps** — each step ONE
imperative sentence naming the exact button, ONE "expect" sentence, and at most ONE screenshot —
followed by an **"If it did not work"** table and up to four **"Right now"** facts read live from the
bot. The site's new **Guides** page (member-gated through `member_dependency`, the second thing a
non-staff member may open) renders the hub and each guide from `/api/guides`; staff edit every word
in place on the same page (a docked save bar, like Settings), never a form elsewhere. Screenshots
are real captures a person uploads through that editor; the deploy writes which features changed,
and a shot older than its feature's last change is marked **stale** on the page and on the staff
panel until somebody re-shoots it. `/help` keeps its list and gains a small `guide` link per line.
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
              sha256, width, height, bytes, source (discord|website), shot_release, shot_by,
              shot_at, caption, stale (bool), stale_since
guide_releases release (text, e.g. 'v112'), commit, shipped_at, changed_features (JSON list)
```

- `slug` is the URL and the `/help` link target: `{origin}/guides.html#golive-announce`.
- One partial unique index keeps one `published` guide per `(guild_id, command)`, so `/help` never has
  two links to choose from for one line (checklist 6).
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
- ⚠️ **No Discord editing door** — fork **F-G1** below; the recommendation is (a) and the reason is
  written there. The settings KEYS are both ways as always.

### C4. Screenshots — real, and honest about their age

1. **Capture is a person.** After a deploy the self-test has already posted every panel's root card in
   the test channel; the owner (or any staffer) screenshots the card on the desktop app, opens the
   guide, presses **Replace screenshot…** on the step. Website screenshots CAN be scripted
   (`scripts/scan/shoot_site.mjs`, Playwright against the mock with `?as=staff`, gitignored per the
   only-bot-code rule) — the build may ship that script but the design does not depend on it.
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
   log row per release: `guide.shots_stale` with the count and the features.
4. **Stale is visible in three places:** a `STALE` pill on the screenshot for members ("from v110 —
   the feature changed in v112"), the hub's staff-only line "3 screenshots need re-shooting", and the
   `/help` reply's existing hidden-note footer does **not** mention it (members cannot act on it).
5. **A shot is never deleted by staleness.** An old real picture beats no picture; only a person
   replaces it. Replacing clears `stale`.
6. Alt text is the step's `do_text`; the caption is `shot on <release> by <name>`.

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

Seventeen guides, zero screenshots at seed time (the person shoots them; the page renders a step
without a picture as text only, never a broken image — the mock's "screenshot" frames are for the
owner, not the seed).

## D. Calls the owner may overturn (each is one key or one line)

1. Facts from the four core keys and the `*_log_level`s are refused → one line in the validator.
2. Screenshots ≤ 2 MB, ≤ 1600 px → two constants; a registry key if the owner wants to move them.
3. A stale shot stays up with a pill rather than being hidden → one branch in the renderer.
4. The linter warns and never refuses → one flag.
5. `/help`'s link is masked Markdown per line + one button → §C7; the button alone is one `if`.
6. One published guide per command → the partial unique index; drop it to allow two.

## E. Out of scope (so nobody builds it by accident)

Video or GIF captures; automated Discord screenshots of any kind (terms); per-member progress
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
  `deploy.ps1` step + `release.json`, the backup line and the RECOVERY row. Est. **220–320k**.
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
  `/data/guides/`; `code-notes.md` section by NAME.

## G. Open forks (one at a time to the owner, recommendation first)

- **F-G1 — a Discord editing door.** (a) **None** — wording and screenshots are edited on the website
  only; the Discord half of this feature is `/help`'s links, and a multi-field long-text edit is what
  the website exists for (the same reason the Settings page, not the panel, owns `bot_bio`). This is
  a deliberate exception to checklist 33's "both ways" for CONTENT, not for the keys — record it in
  `KNOWN_ISSUES.md` as `WAIVED` if chosen. (b) A `/guides` staff panel with **A guide…** → **A step…**
  → a modal per step (five fields is Discord's cap; the faults table and facts would need more
  modals). Recommend **(a)**; the owner's words were "webpages".
- **F-G2 — where "Something's off" lands.** (a) A request, as designed (staff see it where they see
  everything else). (b) A `guide.fault` log row only, no request. Recommend **(a)**.
- **F-G3 — the hub for a member.** (a) Member guides only, staff guides hidden. (b) Both, staff ones
  marked. Recommend **(a)** — a member cannot press any button a staff guide names.

## Deviations

*(empty until the build lands; the builder appends what departed from the above and why)*
