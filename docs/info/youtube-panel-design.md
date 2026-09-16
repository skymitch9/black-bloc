# YouTube — `/youtube` is ONE command that opens a panel (wave 2)

> **Audience:** the build agent and the reviewer, and the owner for §I. **Status:** TRACKED ·
> ✅ **SHIPPED v71 `b764757` 2026-09-03 17:37** (merged after Fable review; boot measured `commands
> synced` **40**; 3872 tests; **F-Y2 done 17:42 — `youtube_mode` is shadow**; nothing run against
> Discord or YouTube by eye — sweeps 118–125 are the owner's). Written as BUILT 2026-09-03 on branch
> `worktree-agent-a74823f4d9293d080` off `main` `ea252bd`
> (v68 live), commits `7809b57` (code), `7f800cb` (tests) and the docs commit that follows
> them. Gates at the time: **3820 tests pass** (3744 on the base commit —
> +76, none lost), ruff clean over the whole tree, `node site/mock/check.mjs` ok (17 pages,
> 142 routes), `labels.js` and `page-golive.js` both parse, and
> `import black_bloc.youtube, black_bloc.cogs.content.youtube, black_bloc.api.tools.youtube,
> black_bloc.personas` succeeds. `commands synced` **41, measured** by loading every cog
> (`tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits`) — a drop of
> exactly one, as §B predicted. ⚠️ **NOT verified: anything against Discord or YouTube.** The
> build agent has no token; no panel was opened, no button pressed, no channel resolved, no
> feed fetched. Its `## Deviations` foot is at the bottom of this file.
>
> **§I's two forks are DECIDED (owner, 2026-09-03 16:10–16:15):**
> **F-Y1 = (a), keep `/youtube` and `/golive` SEPARATE** — the Twitch link is not folded into
> this panel, and the sibling golive panel keeps its own. Built that way.
> **F-Y2 = (b), flip `youtube_mode` to `shadow` when the panel lands** — ⚠️ **that is
> OPERATIONAL, not a build change.** The conductor does it from the Settings page (or
> **Announcements are…** on the panel itself) after the deploy; the stored value and the
> registry default are **untouched by this build** and `youtube_mode` still ships `off`.
>
> ⚠️ **Since then:** the **Logs** button's lost `count` / `important_only` (§C, §J) came back at
> **v96** as **Show more** / **Important only** buttons under the list
> ([`logs-buttons-design.md`](logs-buttons-design.md)). Nothing else in this build has been touched.
>
> **Last verified: 2026-09-11 09:28** (the header; the body is as at the design). Measured this pass
> against `main` at `f3ae743` (v108 live): `settings_store.py` registers **both** new keys,
> `youtube_panel_minutes` (int) and `youtube_unlink_dms_them` (bool);
> `black_bloc/youtube.py` has `YouTubeError(..., network=…)` set at **four** raise sites
> (deviation 7) and `status_lines(row, latest_title, *, where, shorts)` (deviation 2);
> `cogs/content/youtube.py` has `LinkRefused`, `link_channel`, `save_setup`, `SETUP_DONE`,
> `LinkModal`, `NumbersModal` and `UnlinkForModal(NoteModal)` (deviations 1, 8, 9, 10);
> `logkinds.FEATURE_PAGES["youtube"]` is still `golive.html`, so `Open on the site` is the Go-live
> page as §C says. The sweep rows landed as **118–125** in
> [`../access/sweeps.md`](../access/sweeps.md) — ⚠️ **not the 104-onward §H predicts**; the conductor
> renumbered at the merge, exactly as §H said he would. ⚠️ **NOT checked this pass:** anything in
> Discord, a browser or YouTube, and the LIVE value of `youtube_mode` (the header records the
> conductor's 17:42 flip to `shadow` at the v71 landing; it was not re-read from the live store).
>
> Before that, **2026-09-03** — every `path:line` below was READ at `main` `1735ff8` in
> `black_bloc/cogs/content/youtube.py`, `black_bloc/youtube.py`, `black_bloc/api/tools/youtube.py`,
> `black_bloc/panels.py`, `black_bloc/settings_store.py`, `black_bloc/command_visibility.py`,
> `black_bloc/logkinds.py`, `black_bloc/personas.py`, `tests/test_bot.py`,
> `site/public/assets/page-golive.js`, `site/public/assets/labels.js`, `docs/access/sweeps.md`,
> `docs/info/code-notes.md`. The test counts (50 / 44 / 17) were counted, not remembered.
> ⚠️ **NOT verified: anything run.** No boot, no pytest, no ruff, no `check.mjs`, nothing against
> live Discord and **nothing against YouTube** — no channel resolved, no feed fetched, no panel
> opened, no button pressed. `youtube_mode` is **`off` in production** (`settings_store.py:1285`),
> so the off-state wording in §B is the half most likely to be wrong and the half hardest to
> exercise (§I, F-Y2). Whether a client submits an EMPTY `ChannelSelect`/`RoleSelect` at
> `min_values=0` is the same unproven edge events and applications both flagged; §C names the same
> `Forget…` fallback, and it is BUILT either way (events deviation 6).
>
> **Inherits every invariant in [`panels-program.md`](panels-program.md) §2 (P1–P17) and its §4
> library — none restated here.** Template: [`requests-panel-design.md`](requests-panel-design.md),
> whose `## Deviations` foot is the trap list (1 defer-then-edit, 4 the member select's placeholder,
> 5 the 5-per-row cap, 7 `commands synced` does not always drop, 9 `retire`, 10 the 15-minute
> footer, 11 `still_staff` not `require_staff` after a defer). Feature behaviour is
> [`phase16-design.md`](phase16-design.md) (F3), which this design **undoes none of** — the poller,
> the seed rule (D10), the guarded post path and every log kind are untouched.

## A. Measured today — two groups, nine subcommands

`youtube` is a `Group` (`cogs/content/youtube.py:214`, **member-visible**, no
`default_permissions`); `uploads` is a `Group` (`:215`, `default_permissions=STAFF_ONLY`).
**3 + 6 = nine leaf subcommands over two top-level slots.**

| Subcommand | Line | Who | Calls · what is INLINE in the cog |
|---|---|---|---|
| `/youtube link <channel>` | `:611` | anyone | `_database_ready` `:567` → defer → `_link_to` `:574` → `client.resolve` (`youtube.py:273`) → `link_owner` `:105` → `link_and_seed` `:597`; ⚠️ the `MODE_OFF_NOTE` tail and the `youtube.link` log are **inline** `:621–627` |
| `/youtube unlink` | `:629` | anyone, own row | `remove_link` `:114` + `youtube.unlink` — **inline** `:633–637` |
| `/youtube status` | `:639` | anyone, own row | `get_link` `:95`, `latest_video` `:180`, `_where_words` `:522`; ⚠️ **the five lines are built inline** `:653–659` |
| `/uploads logs` | `:664` | staff — `send_logs` carries its own gate (`actionlog.py`) | `send_logs(interaction, "youtube", count, important_only)`. Nothing inline |
| `/uploads mode` | `:677` | `require_staff` `:685` | ⚠️ **inline** `:687–700`: `store.set` + `NO_CHANNEL` tail + `youtube.mode`. ⚠️ **no `_database_ready` check** — see §K finding 5 |
| `/uploads setup` | `:702` | `require_staff` `:713` | ⚠️ **inline** `:715–743`: `SETUP_NOTHING` guard, two `store.set`s, `SETUP_DONE`, `youtube.setup`. Same missing db check |
| `/uploads link-for` | `:745` | `require_staff` `:750` | `_link_to` again + a **second** inline `youtube.link` log `:759–771` |
| `/uploads unlink-for` | `:773` | `require_staff` `:778` | `remove_link` + a **second** inline `youtube.unlink` log `:782–801`. **Nobody is told** |
| `/uploads list` | `:803` | `require_staff` `:805` | `all_links` `:100`, `counts` `:189`; ⚠️ **the seven health lines AND the per-member lines are inline** `:813–830` |

**Nothing here is a `DynamicItem` and there is no persistent post**, so P14 has no work in this
feature — unlike events, applications and role menus. The panel is the ONLY door this build adds.

**There is no state machine.** The "state" is the product of four facts, and §B's table is that
product as data:

| Fact | Values | Read from |
|---|---|---|
| linked? | yes / no | `get_link(db, user_id)` `:95` |
| who | member / staff | `store.is_staff` |
| whose card | mine / somebody else's | the staff select |
| mode | `off` · `shadow` · `on` (`YOUTUBE_MODES`, `settings_store.py:53`; **`off` by default**, `:1285`) | `_mode` `:519` |

**The web is a real second door already** — `api/tools/youtube.py:8` imports eight names FROM the
cog, and `POST /links` `:109` re-implements `_link_to`'s resolve and owner check in HTTP words.
That duplication is §F's work.

## B. The decision — one `/youtube`, member panel and staff panel

**`/youtube` becomes a single `app_commands.command`; both `Group`s go and `/uploads`
disappears.** `commands synced` drops by **one** relative to whatever it is when this lands
(42 today, `tests/test_bot.py:198`). ⚠️ **State the delta, not the number** — other wave-2
features drop one each and the conductor reconciles at merge; the build **re-measures** and edits
`tests/test_bot.py:198` to what it reads (requests deviation 7).

⚠️ **The one command keeps NO `default_permissions`** — the member half has none today, so
`"youtube"` STAYS in `MEMBER_COMMANDS` (`tests/test_bot.py:71`) and `"uploads"` leaves
`STAFF_COMMANDS` (`:53`). The staff half is gated at runtime by `still_staff` as it always was.

**`Status` is not a button — it IS the embed.** `/youtube status`'s five lines `:653–659` are what
the member's card says, so a `Status` button would be a second spelling of the render (P3). The
button that re-asks is `Refresh`.

**Root panel** — `build_panel(bot, guild, actor)`, one ephemeral embed + `Panel` subclass, split on
`store.is_staff(actor)`.

| Row | Member sees | Staff sees additionally |
|---|---|---|
| 0 | `Link my channel` (not linked) **or** `Relink…` · `Unlink` (linked) · `Refresh` · `Open on the site` | same — a staffer's own card is the member card |
| 1 | — | Select **"Somebody's channel…"** — `all_links` `:100`, ≤25, `capped_placeholder` (`panels.py:56`). Not rendered when nobody is linked; the embed says `NOBODY_LINKED` `:59` |
| 2 | — | Select **"Announcements are…"** — `YOUTUBE_MODES`, current value as the default option |
| 3 | — | `Link for somebody…` · `Setup` · `Logs` |
| 4 | — | `UserSelect` **"Whose channel is it?"** — rendered ONLY on the re-render after `Link for somebody…`; picking a member opens the Link modal for them |

**Why the mode select is on the ROOT and not inside `Setup`.** `youtube_mode` ships `off`
(`:1285`) and is off in production today, so "turn it on" is the single most likely reason a Lead
opens this panel; one click deep is the wrong depth for the only control that changes whether the
feature runs at all. The `Setup` sub-panel therefore shows the mode as a **line**, never as a
second select — two spellings of one move is exactly what P3 forbids.

**Embed — "Your YouTube channel".** Member half, in order:

| When | What the embed says |
|---|---|
| not linked | one intro line + `NOT_LINKED` `:35` **reworded off the retired command** ("Link one with the button below") |
| linked | the five `/youtube status` lines `:653–659` verbatim: channel · linked · last video seen (`NOT_SEEDED_YET` `:58` when the feed has not answered) · announced here (`_where_words` `:522`) · Shorts |
| `youtube_mode == "off"`, any | ⚠️ **an extra LINE, and `Link my channel` STILL RENDERS.** Linking works with the mode off today and the reply already says so (`MODE_OFF_NOTE` `:60`) — the link is the member's opt-in, the mode is the server's switch, and hiding the button would make an off server unable to prepare. The line is `MODE_OFF_NOTE` reworded to name the panel's own mode select instead of `/uploads mode on` |
| db down | `db_ready` / `DB_UNAVAILABLE` in words (P9); no control that writes is rendered |

Staff half adds the seven health lines `:813–823` (mode · channel · every N minutes · api key set
or feed-only · last good sweep · last error + failure run · links/videos/announced) and, when
`self.client.keyed` is false, `NO_KEY` `:26` as a line. That block IS `/uploads list`'s header and
must not be re-worded.

⚠️ **`panels.SELECT_OPTION_LIMIT` is 100 and is the LABEL CHARACTER clamp inside `option_label`
(`panels.py:15`, `:64`) — it is NOT the 25-option cap.** The 25 cap is Discord's own and is handled
by `capped_placeholder` (`panels.py:56`) exactly as the requests and applications selects handle
it. With more than 25 linked channels the select shows the 25 most recently linked (`all_links`
orders by `linked_at` `:101` — the build reverses it) and the placeholder reads "25 of N — the rest
are on the site", which is true: the site's links table (`GET /api/youtube/links`) is the other
door. **Both facts are needed and neither substitutes for the other.**

## C. The cards, the sub-panel, the modals

Each is a **re-render in place**, `retire(previous)` first (P6), `defer()` then
`edit_original_response` (P5), `db_ready` on every click (requests deviation 6), `still_staff`
before every staff move (P8).

**The button table, AS DATA** — `CARD_BUTTONS` + `card_buttons(...)` in `black_bloc/youtube.py`
(§F), proved by a parametrised test over the whole product (checklist 3, 12):

| Card | linked | mode | Buttons rendered (+ `Refresh`, + `Open on the site` when an origin is set) |
|---|---|---|---|
| mine | no | any | `Link my channel` |
| mine | yes | any | `Relink…` · `Unlink` (danger, Yes/Keep confirm) |
| theirs (staff) | yes | any | `Relink for…` · `Unlink for` (danger, `NoteModal(required=False)`) · `Back` |
| theirs (staff) | no | — | unreachable — the select only lists linked rows |
| root, staff | — | any | + the mode select, `Link for somebody…`, `Setup`, `Logs` |

⚠️ **No button is hidden by the mode.** The mode changes what the embed SAYS, never which control
renders — nothing here writes to Discord, so nothing here is unsafe with the feature off.

**`Unlink for` tells the member, and that is new behaviour.** Staff-final-say
(`CLAUDE.md`, owner 2026-09-03) says a staff move that affects a person carries a DM'd reason;
today `/uploads unlink-for` `:773` tells nobody. The panel's `Unlink for` opens
`panels.NoteModal(title="Why?", label="One line they will be sent", max_length=400,
required=False)` — submit is yes, dismiss is keep, exactly as events deviation 4 settled it — and
`unlink_channel` (§F) DMs the member best-effort, wrapped, when `actor != member` and
`youtube_unlink_dms_them` is on (§D). A DM that cannot be delivered is a `details` field on the
existing `youtube.unlink` row, **never a second log row** (checklist 34).

**The Link modal** — one `TextInput`, `AnswersErrors` + `discord.ui.Modal` (P12), label
"Your channel address, @handle, or UC… id", prefilled on a relink with `row["handle"]` or
`row["channel_id"]`. Validation is **`YouTubeClient.resolve` (`youtube.py:273`) and nothing else** —
byte for byte the path `/youtube link` uses through `_link_to` `:579`. Three outcomes, three
different sentences, and ⚠️ **the build must not collapse them into one "could not link"**:

| Outcome | Sentence today | Where |
|---|---|---|
| the paste is not a channel | `CANNOT_RESOLVE` — names what to paste AND that a Lead can set an API key so handles work | `youtube.py:44`, raised `:281` `:306` |
| YouTube would not answer | `FEED_REFUSED` ("usually the feed being flaky rather than the channel being wrong … try again in a minute") or `"youtube unreachable: …"` | `youtube.py:49` `:254`, `:228` |
| somebody else owns it | `ALREADY_LINKED` — a channel belongs to one member; ask a Lead | cog `:30`, checked `:586` |

**Bad input and an outage are the same exception type** (`YouTubeError` `youtube.py:56`) and today
land on one log kind (§K finding 3). `link_channel` (§F) takes them apart: the refusal sentence is
whichever `str(exc)` already is, and the log row carries `details["network"] = True|False`
decided at the raise site, not by string-matching the message.

**The `Setup` sub-panel** (staff). Its embed is the same seven health lines plus the mode as a
LINE. Rows:

| Row | Control | Note |
|---|---|---|
| 0 | `ChannelSelect` "Where uploads are posted…" (`youtube_channel_id`) | `min_values=0`; **empty = clear, and clearing is meaningful** — blank falls back to `golive_channel_id` (D3, `_channel_id` `:512`) |
| 1 | `RoleSelect` "Who is pinged…" (`youtube_ping_role_id`) | `min_values=0`, empty = clear = ping nobody |
| 2 | `Shorts: announced / not` · `Fans pinged: on / off` · `Words…` · `Numbers…` · `Back` | exactly Discord's 5-per-row cap. `Words…` is the `youtube_template` modal; `Numbers…` takes `youtube_poll_minutes` (floor `YOUTUBE_POLL_MIN_MINUTES` = 5, `settings_store.py:56`/`:329`) and `youtube_panel_minutes` |
| 3 | `Forget…` · `Open on the site` | ⚠️ `Forget…` is the events-deviation-6 fallback, BUILT alongside the empty submits, opening a 2-option select of which key to clear through the same writer |

`Words…` writes `youtube_template` through the settings validator; a broken template already falls
back at render time with a warning (`youtube.py:175`, checklist 17), so the modal refuses nothing —
but the sub-panel renders the result beneath it so a mistake is visible before it is posted.

**`Logs`** — a button answering a NEW ephemeral followup (P11), `send_logs(interaction,
"youtube")`, which carries its own `require_staff`. ⚠️ The `count` / `important_only` options
`:665–673` are LOST, as they were for `/request` and every wave-1 panel; the site's Logs page has
both, and `logkinds.py:94` already points the feature at `golive.html`. **Given back at v96** as
**Show more** / **Important only** buttons under the list, plus the `logs_count` and
`logs_important_only` keys — [`logs-buttons-design.md`](logs-buttons-design.md).

**`Open on the site`** — a link button to `{origin}/golive.html` (`FEATURE_PAGES["youtube"]`,
`logkinds.py:94`), built with `site_page_url`'s shape (`requests.py:503`). **No origin, no
button** — never a broken link.

## D. Settings (P13 · checklist 33)

| Key | Type | Default | Status |
|---|---|---|---|
| `youtube_panel_minutes` | `int` | **10** | **NEW.** Registered exactly as `applications_panel_minutes` is (`settings_store.py:825` `KEY_TYPES`, `:864` `KEY_HELP`, `:1499` `default()`), in a **`# YouTube panel (wave 2)` block appended at the foot** of the registry so parallel wave-2 branches merge textually. Help text carries KI-20's warning verbatim in shape: 15+ loses the "gone quiet" footer |
| `youtube_unlink_dms_them` | `bool` | **True** | **NEW.** Whether a STAFF `Unlink for` DMs the member the reason (§C). It is a decided default, so it is a key and not a constant (checklist 33). Mirrors `applications_dm_on_decision` (`:823`). A member unlinking themselves is never DMed |

**Read, never changed:** `youtube_mode` · `youtube_channel_id` · `youtube_ping_role_id` ·
`youtube_ping_fan_roles` · `youtube_announce_shorts` · `youtube_template` · `youtube_poll_minutes`
(`settings_store.py:159–165`), plus `golive_channel_id` as the D3 fallback and `youtube_log_level`
(site-only, `labels.js:37`). Nothing else here is a decision: the 25 cap and the 5-per-row cap are
Discord's, the poll floor is measured (`code-notes.md` `youtube.py:19`), and the button table is
the product in §A.

## E. What goes away, and every line that names it

`/help` reads the tree (`cogs/core.py:113`), so it follows with no edit (P15).

| Thing | Where | Becomes |
|---|---|---|
| `youtube` Group | `cogs/content/youtube.py:214` | `@app_commands.command(name="youtube")`, still no `default_permissions` |
| `uploads` Group + 6 children | `:215`, `:664` `:677` `:702` `:745` `:773` `:803` | the mode select, the staff buttons, the `Setup` sub-panel, `Logs` |
| the three `/youtube` children | `:611` `:629` `:639` | the Link modal, `Unlink`, the embed itself |
| `LOGS_GROUPS["uploads"] = "youtube"` | `tests/test_bot.py:22` | **deleted** — `/youtube` is not a Group with a `logs` child, so the loops at `:175` and `:221` would `KeyError` |
| `STAFF_COMMANDS` `"uploads"` | `tests/test_bot.py:53` | **deleted**. `MEMBER_COMMANDS` `"youtube"` `:71` **stays** |
| `assert len(top) == 42` | `tests/test_bot.py:198` | **one lower than whatever the build measures** — never a hard-coded absolute (§B) |
| `HIDDEN_WHEN_OFF` | `command_visibility.py:16–20` | ⚠️ **NOTHING TO DO — there is no youtube entry today** (only `rolemenu_mode`, `request_mode`, `chat_memory_mode`). The command does not vanish when the mode is off, which is already what the owner decided for applications on 2026-09-03 13:47 ("Visible"). **Do not add one** |

**Strings that name a retired subcommand and are rewritten in the SAME commit** — each currently
tells somebody to run something that will not exist:
`cogs/content/youtube.py:37` (`NOT_LINKED` → "`/youtube link <your channel address>`"),
`:40` (`NOT_LINKED_FOR` → "`/uploads list`"), `:46` (`LINKED` → "`/youtube unlink` undoes it"),
`:62` (`MODE_OFF_NOTE` → "`/uploads mode on`"), `:67` (`SETUP_NOTHING` → "`/uploads setup
channel:… ping_role:…`"), `:71` (`NO_CHANNEL` → "Run `/uploads setup channel:#somewhere`"),
`:529` (`_where_words` → "a Lead runs `/uploads setup`");
`black_bloc/personas.py:78–79` (⚠️ **the chat bot's own answer to "how do I get my uploads
posted"** — two sentences naming all three member subcommands).

**Site touch points** (§J says the page itself is not rebuilt): `site/public/assets/page-golive.js:310`
(`NO_UPLOAD_LINKS` — "or a member runs /youtube link themselves") and its comment `:336`;
optionally two label lines beside `youtube_*` in `site/public/assets/labels.js:30–37` for the two
new keys — `applications_panel_minutes` has one (`:168`) and the wave-1 keys do not, so this is a
consistency fix, not a requirement. ⚠️ **Touching either file means `node site/mock/check.mjs` and
the `labels.js` parse are no longer skippable** (§H item 4).

**Docs rewritten in the same commit** (P15): `docs/access/sweeps.md` rows **43** (`:101`), **44**
(`:102`), **47** (`:105`) rewritten IN PLACE, not added to — row 45 (`:103`) names no command and
row 46 (`:104`) is the dashboard; `docs/info/architecture.md:194` ("/youtube (members) and
/uploads (staff)"); `docs/info/feature-list.md:41`; `docs/info/cutover-plan.md:44`;
`docs/info/phase16-design.md:109–115` gets a dated "superseded by the panel" line **at the top**,
not a rewrite; `docs/info/panels-program.md:80` (the YouTube row → shipped);
`docs/access/OWNER_GUIDE.md:71` (the sweeps count) — ⚠️ measured 2026-09-03, `OWNER_GUIDE.md`
names no youtube command anywhere else; `docs/info/code-notes.md` re-keyed at the merge, with the
youtube anchors at `:4601–4649` (`youtube.py`, the cog) and `:4651–4659` (the API) — specifically
`:4618` ("that is the path `/uploads link-for` …"), `:4633` ("The `/youtube …`"), `:4645`
("A member asking `/youtube status`"), `:4646` ("`/youtube link`, `/uploads link-for` and `POST
/api/youtube/links` all land here"), `:4648` ("`/youtube status` defers to `_where_words`").

## F. Extractions (P4) — one function per move, called by BOTH doors

⚠️ **The DB/move layer lives in the COG** (`cogs/content/youtube.py:75–201`) and
`api/tools/youtube.py:8` imports eight names from it. **Do not move the layer** — the applications
precedent, not the events one: the move buys nothing here (no third importer, no cycle) and every
line of it is risk this build does not need.

**New, module level in `cogs/content/youtube.py`** — each does ONE write and ONE log row, each
returns `(what to say, the fresh row)`, each takes `via: str = VIA_DISCORD` and builds its kind
with `logkinds.kind_via` (checklist 34):

| Function | Replaces | Notes |
|---|---|---|
| `link_channel(bot, guild, actor, member, given, *, via)` | `_link_to` `:574` **+ both** inline tails `:617–627` and `:755–771` | resolve → owner check → `link_and_seed` `:597` → ONE `youtube.link` row. `details["network"]` on the failure path (§C). The web's `POST /links` `:109` keeps its `Refused(400/409)` HTTP shapes and calls this for the write, deleting `note("web.youtube.link")` `:127` — `kind_via` produces the same `web.youtube.link` string, so the row is byte-identical |
| `unlink_channel(bot, guild, actor, member, *, note, via)` | `unlink` `:633–637` **+** `unlink_for` `:782–801` | `remove_link` `:114` → ONE `youtube.unlink` row → the best-effort DM (§C, `youtube_unlink_dms_them`). `DELETE /links/{id}` `:143` calls it and deletes `note("web.youtube.unlink")` `:151` |
| `set_mode(bot, guild, actor, value, *, via)` | inline `:687–700` | `NO_CHANNEL` `:69` tail included, reworded |
| `save_setup(bot, guild, actor, changes, *, via)` | inline `:715–743` | takes a dict so the sub-panel and a future route write identically; `SETUP_NOTHING` `:65` is what an empty dict answers |

**Pure, into `black_bloc/youtube.py`:**

| New | What it is |
|---|---|
| `PanelMove` (NamedTuple) + `CARD_BUTTONS` + `card_buttons(*, linked, mine, staff)` | §C's table AS DATA. ⚠️ **A LOCAL NamedTuple, not a fold of `requests.MoveButton` / `polls.MoveButton` / `events.EventMove` into `panels.py`** — one-fact-one-home says fold them, and events deviation's reasoning stands: shared files are append-only per feature so parallel branches merge textually. The fold is the conductor's job after the wave |
| `status_lines(row, latest, *, where, shorts)` | the five inline lines `:653–659` |
| `health_lines(...)` / `link_lines(rows, names)` | the two inline blocks `:813–823` and `:824–830`, `NOBODY_LINKED` `:59` included |
| `where_words(mode, channel_id)` | the pure half of `_where_words` `:522`; the cog method becomes a one-line caller |
| `panel_minutes(store, guild_id)` | one-liner over `panels.panel_minutes` (`panels.py:76`), exactly `requests.py:510` |
| `PANEL_TIMEOUT_FOOTER` | `"This panel has gone quiet — run /youtube again"` (`requests.py:206`'s shape; wave-0 deviation 1 makes it a constructor argument) |

⚠️ **`panels.option_label` (wave-0 deviation 2) is the shared one — use it, never a fifth copy.**
Same for `panels.answer`: `cogs/community/role_menus.py:392` is a third byte-for-byte copy of
`panels.py:18` and is a known duplicate; do not make a fourth.

## G. Tests (P16 — one file per source file, mirrored paths)

| File | What it gains |
|---|---|
| `tests/cogs/content/test_youtube.py` (**50** today) | `/youtube` answers ephemerally with a panel; a member sees their own card and no select, no Setup, no Logs; staff see all of it; **parametrised over linked × mine/theirs × staff/member × the three modes — the panel renders exactly its §C row and no other**; with the mode `off` the embed says so **and `Link my channel` still renders**; the Link modal calls `client.resolve` and each of the three outcomes answers its own sentence (mock the client — assert the sentence, not a substring shared by two of them); `Unlink for` DMs when the key is on and does not when it is off, and a DM failure adds a detail rather than a second row; the select caps at 25 and its placeholder says so; `Logs` answers a NEW followup and still refuses a demoted staffer; a staffer demoted mid-card moves nothing (`still_staff`, every site); `db_ready` after a defer; the mode select writes through `set_mode`; the Setup sub-panel writes through `save_setup` and an empty select clears exactly as `Forget…` does; timeout disables every item and a re-render `retire`s the view it replaced |
| `tests/test_youtube.py` (**44**) | `card_buttons` over the whole product; `status_lines` / `health_lines` / `link_lines` / `where_words` against the strings they replace; `panel_minutes` |
| `tests/api/tools/test_youtube.py` (**17**) | the four routes answer the same shapes and now log through `kind_via` — ⚠️ **assert the log-row COUNT, not just the kind** (checklist 34 is the item this build can fail silently) |
| `tests/test_settings_store.py` | both new keys round-trip, appear in `KEY_TYPES` / `KEY_HELP` / `default()`, and default 10 / True |
| `tests/test_bot.py` | `LOGS_GROUPS` loses `uploads`; `STAFF_COMMANDS` loses `uploads`; `MEMBER_COMMANDS` keeps `youtube`; the tree-limit test recounts |
| `tests/test_logkinds.py` | no new kind — `link_channel` / `unlink_channel` emit `youtube.link` / `youtube.unlink` and their `web.` heads through `kind_via` |

The poller's existing tests (seed/D10, dedupe, classify, the guarded post, `would_announce` vs
`post_failed`, test mode) **stay green untouched** — that is the proof this build changed nothing
behind the door (wave-0 deviation 4).

## H. §J — prove before merge (P17), and the sweep rows

1. `python -m black_bloc` boots; **read `commands synced` and record both numbers** — the drop must
   be exactly one for this feature. No token here means measuring it the other way instead:
   `tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits` counts the real tree
   after loading every cog (applications deviation 11's precedent). **Say which you did.**
2. The parametrised panel test: every state renders its row and no other (checklist 3, 12).
3. `python -c "import black_bloc.youtube, black_bloc.cogs.content.youtube,
   black_bloc.api.tools.youtube, black_bloc.personas"` — the substitute for a boot (wave-0
   deviation 5); this build adds the import edge `black_bloc/youtube.py` → `panels`.
4. `ruff`; full `pytest`; and **if and only if a `site/` file was touched** (§E),
   `node site/mock/check.mjs` and `node --input-type=module --check < site/public/assets/labels.js`
   (⚠️ that file did not parse once before — `code-notes.md:5008`).
5. Checklist sweep before reporting — **2** (a failure and a dry run never share a kind), **8**
   (`AnswersErrors` on every modal and component), **10** (⚠️ the seed-count sentence, §K finding 1
   — do not ship a panel that claims a check that did not run), **11** (`allowed_mentions` on every
   send: a YouTube TITLE and a channel title are attacker-controlled text), **15**/**17** (no new
   `answer` or `option_label` copy), **22** (the poll-minutes floor in the `Numbers…` modal, refused
   in words naming the range — a modal has no `app_commands.Range`, events deviation 7), **29** (the
   `min_values=0` submit checked against installed source, not guessed), **30** (`on_error` on every
   view and modal), **33** (§D), **34** (assert the row COUNT).

**Sweep rows — this feature takes 104 onward** (`docs/access/sweeps.md`'s last row today is **102**;
**103 is taken by a sibling wave-2 build** — ⚠️ **renumber at landing**, the conductor reconciles).
Rows 43, 44 and 47 are rewritten in place, not added.
⚠️ **They landed as 118–125**, under the heading *"The YouTube panel — `/youtube` is one window
(wave 2, 2026-09-03)"*. The table below keeps the design's numbering; read it as 118 onward.

| # | Do this | Expect |
|---|---|---|
| 104 | `/youtube` as a plain member with nothing linked, with `youtube_mode` **off** | one ephemeral panel: the intro, a line saying announcements are off **and how that is changed**, `Link my channel`, `Refresh`, `Open on the site` — and no select, no Setup, no Logs |
| 105 | `Link my channel` → paste `youtube.com/channel/UC…`; then re-open the panel | the same words `/youtube link` gave, the same seeded count, the same `youtube.link` row — and the panel now shows the five status lines |
| 106 | `Relink…` → paste nonsense; then `@ahandlethatdoesnotexist` | two DIFFERENT refusals — "I could not turn … into a YouTube channel id" for the paste, and the flaky-feed sentence if YouTube itself would not answer. **Nothing is changed either way** |
| 107 | `Unlink` → Yes; then again → Keep it | the first forgets the channel (the panel goes back to `Link my channel`); the second changes nothing |
| 108 | `/youtube` as staff | adds **Somebody's channel…** (25 cap, "25 of N" past that), the **Announcements are…** select, `Link for somebody…`, `Setup`, `Logs` — Logs answers a NEW message and the panel stays |
| 109 | `Link for somebody…` → pick a member → paste their channel; then pick them on the select → `Unlink for` with a reason | linking counts their history exactly as `/uploads link-for` did; unlinking forgets it, **DMs them the reason**, and leaves ONE `youtube.unlink` row |
| 110 | The mode select → `shadow`; then `Setup` → pick a channel, submit an EMPTY channel select, `Forget…` the ping role, `Numbers…` → `2` | the mode line updates; the empty select clears the channel and the panel says uploads fall back to the go-live channel; `2` is refused in words naming the 5-minute floor |
| 111 | Leave the panel `youtube_panel_minutes` minutes | every button disables itself and the footer says the panel went quiet |

## I. The genuine forks for the owner — one at a time

Settled first, by the two standing rules, so they are NOT put to him:

- ✅ **`Unlink for` DMs the member a reason** — staff-final-say, the same call events made (I1
  there). New behaviour, behind `youtube_unlink_dms_them` (§D), default on.
- ✅ **The command stays visible with the mode off, and a member may still link** — the owner's
  2026-09-03 13:47 "Visible" for applications, and today's `/youtube link` behaviour.
- ✅ **A member does not see who else is linked** — staff-only today (`/uploads list` is
  `require_staff` `:805`); today's permission is the default.
- ✅ **`Logs` loses `count` / `important_only`** — every panel so far; the site has both.

The two that are genuinely his:

- ✅ **F-Y1 — DECIDED (a), 2026-09-03: leave them separate.** Built that way; nothing in this
  panel mentions Twitch.
- ✅ **F-Y2 — DECIDED (b), 2026-09-03: flip to `shadow` when the panel lands** — an
  OPERATIONAL step for the conductor after the deploy, not a build change. The registry
  default is still `off` and the build wrote no value.

- **F-Y1 — should `/youtube` also carry the member's TWITCH link?** A member who streams on Twitch
  and uploads to YouTube does one job — "tell the bot where I am" — through two commands, and the
  sibling `/golive` design puts `Link` / `Unlink` for Twitch on its own panel. Options: **(a) leave
  them separate**, one panel per feature exactly as `panels-program.md` §3 lays out; (b) `/youtube`
  gains a read-only "Your Twitch: …" line with a button that opens the golive panel; (c) a later
  `/links` panel fronting both platforms, and both feature panels drop the link controls.
  **Recommended: (a).** The settings namespaces, the log features, the sweep rows and the site
  sections are all per-platform, and (c) is a cross-feature panel nothing else in the program has —
  but (b) is cheap and honest if he finds the two-command shape confusing. *This is the only
  question in this document that changes the panel's shape.*
- **F-Y2 — `youtube_mode` has been `off` since F3 shipped, so sweeps rows 43–47 have never run.**
  Should the deploy that lands this panel also flip the mode so the feature is finally exercised?
  Options: **(a) leave it `off`** — this build changes no runtime behaviour and row 104 tests the
  off-state wording, which is the wording most likely to be wrong; (b) flip to **`shadow`** after
  the deploy so rows 44 and 45 run against real uploads with nothing posted; (c) flip to **`on`**,
  which posts into `#black_bloc-logs` only while `TEST_MODE` stands. **Recommended: (b)** —
  shadow is the mode the sweeps were written for, it posts nothing, and it is the only way to learn
  whether the poller has been quietly failing for a day. It is an operational call, not a build
  call: **the build lands either way.**

## J. What NOT to build, and what it should cost

**Not built, explicitly:**

- The **poller** and everything behind it: `poll_once` `:272`, `_poll_link` `:311`, `_seed` `:332`,
  `_kinds` `:352`, `_found` `:364`, `_settled` `:393`, `_skipped` `:407`, `_announce` `:414`,
  `_post` `:477`. No new announcement path, no test-post button (`/golive test` exists; uploads
  has no twin and this build does not invent one).
- The **DB layer's location** — §F says add in place, do not move.
- The **API routes' shapes**, `site/mock/contract.json`, and the Go-live page's YouTube section.
  One string on that page changes (§E); the section is not rebuilt.
- **Any persistent view.** There is no `DynamicItem` in this feature and this build adds none —
  the ephemeral panel is for the caller (P14).
- **A Shorts / live re-classification control** (KI-11's gap is a key-availability fact, not a
  setting), and `youtube_log_level` editing — the general Settings page owns it (`labels.js:37`).
- Folding `MoveButton` into `panels.py`, or touching another wave-2 branch's files.
- Any of §K — those are findings, reported and left alone unless a §H checklist item forces one
  (finding 1 is the one checklist 10 does force).

**Cost.** Wave-1 builds measured **376k–458k** Opus tokens. This one is materially smaller: nine
subcommands rather than seventeen, **no state machine**, no schema change, no persistent items, no
layer move, no new API route, and the site is one string. Against that, it adds a DM path and two
settings keys. **Estimate 230–300k**, and it should be dispatched with the standing instruction to
commit at clean boundaries — code, tests, docs as three commits — so a kill costs nothing.

## K. Findings in the existing code — reported, NOT fixed

Read at `1735ff8`. None is caused by this design; each is one the builder will walk past.

1. ⚠️ **A link whose feed would not answer says "0 counted as seen" and claims a check that did not
   run** (checklist 10). `link_and_seed` `:597` returns `0` when `fetch_feed` raises `:605`, and
   `LINKED` `:43` then reads "the 0 already on the channel are counted as seen, so nothing old is
   announced" — the row is left `seeded = 0` and the poller seeds later. **The WEB path already has
   the honest sentence for exactly this** (`LINKED_NOT_SEEDED`, `api/tools/youtube.py:42`); the
   Discord path has no equivalent. §H item 5 forces the panel to carry it.
2. **Two numbers for one fact.** `LINKED`'s count is `len(videos)` `:609`, while the
   `youtube.seeded` log's `counted_as_seen` is `stored` `:337` — rows actually inserted. Re-linking
   a channel whose videos are still in `youtube_videos` says "12 counted as seen" while the log
   says 0.
3. **A network outage is logged as a resolve failure.** `_link_to` `:582` writes
   `youtube.resolve_failed` for both `CANNOT_RESOLVE` (bad paste) and `"youtube unreachable"` /
   `FEED_REFUSED` (YouTube down) — one `YouTubeError`, one kind, and `_failed` makes both
   "important" (`logkinds.py:107`). Same family as the estate's "a network failure is not a
   permission failure" rule.
4. **The one refusal staff need to see leaves no row.** `ALREADY_LINKED` `:588` — two members
   claiming one channel, checklist 16's exact case — logs nothing, while the resolve failure beside
   it logs.
5. **`/uploads mode` `:677` and `/uploads setup` `:702` never call `_database_ready`**, though every
   other command in the cog does. Both write through `store.set`, so with the database down they
   end in the generic tree-error sentence instead of `DB_UNAVAILABLE`.
6. **`_seed` `:339` and `_poll_failed` `:553` write one log row per guild** over a global table —
   the same implicit single-server assumption `_minutes` `:266` documents, undocumented here. And
   **`remove_link` `:114` leaves the member's `youtube_videos` rows behind**, so `counts()` `:189`
   keeps counting videos of people no longer linked. Both are deliberate (re-linking must not
   re-announce); neither says so.

## Deviations

Written by the build agent, 2026-09-03. Everything not listed here was built as this
document says.

1. **`link_channel` RAISES `LinkRefused` for the two refusals and returns a THREE-tuple
   `(said, row, counted)` on success**, not the `(what to say, the fresh row)` §F specifies.
   Two things forced it. The refusals: §F says the web route keeps its `Refused(400,
   "bad_channel")` / `Refused(409, "link_taken")` HTTP shapes, and a 2-tuple whose second
   element is `None` cannot tell those two apart — the alternative was for the route to
   re-run `client.resolve` and the owner check itself, which is a second network call to
   YouTube and exactly the duplication §F exists to delete. The count: the route's `LINKED`
   sentence carries `{count}` and `tests/api/tools/test_youtube.py` asserts `"5 video(s)"`,
   so the seeded count has to leave the function. `LinkRefused` carries `status` and `code`,
   so the route's mapping is one line and its shapes are byte-identical.
2. **`status_lines` takes the latest video's TITLE, not the row** — `status_lines(row,
   latest_title, *, where, shorts)`. Reading `latest["title"]` safely needs a `row_value`
   helper, and there are already **five** near-copies of one in the package
   (`modcases.py`, `requests.py`, and `_row_value` in birthdays, golive and this cog). A
   sixth in `black_bloc/youtube.py` is checklist 15; the cog passes the value instead.
3. **The staff root embed keeps the linked list as LINES beside the picker.** §B's table put
   `link_lines` nowhere except the empty case. Dropping the list loses what `/uploads list`
   actually showed staff — a select's options are only visible once it is clicked — and it is
   not two spellings of one move (P3): the lines are data, the picker is the control, which is
   exactly the shape `/request` ships (`summary_line` + `RequestPick`). Capped at the same 25.
4. **`Forget…` opens its own small view rather than adding a select to the Setup rows.** §C
   put `Forget…` and `Open on the site` on row 3; a select added in place would need a fifth
   action row and would sit under two pickers that already say the same thing. Pressing it
   re-renders the Setup embed with a two-option select and a **Back** that returns to Setup.
   Same writer (`save_setup({key: None})`), proved by a test asserting the sentence it
   answers is character-for-character the one an empty picker gives.
5. **`Refresh` on somebody else's card re-renders THAT card, not the root.** §C's table adds
   `Refresh` to every card without saying what it refreshes; refreshing back to the root
   would silently throw away the staffer's place.
6. **The "theirs, not linked" cell is BUILT rather than left unreachable.** §C calls it
   unreachable because the picker only lists linked rows — but the member can unlink between
   the render and the click. It renders `Refresh · Back` and the embed says they have no
   channel linked.
7. **`YouTubeError` gained a `network` flag** in `black_bloc/youtube.py`, set at the four
   raise sites (`_aiohttp_request`, `fetch_feed`'s `FEED_REFUSED`, `_api`'s non-200, and
   `parse_feed`'s unreadable XML). §C asked for `details["network"]` "decided at the raise
   site, not by string-matching the message", and an attribute on the exception is the only
   way to carry that. §K finding 3 itself is NOT fixed — both outcomes still share the
   `youtube.resolve_failed` kind; the row now says which one it was.
8. **Two new modals were written rather than reusing `panels.NoteModal`** — `LinkModal` (a
   short single-line field, prefilled on a relink) and `NumbersModal` (two fields).
   `NoteModal` is hard-wired to one paragraph field with no default. `UnlinkForModal` IS
   `panels.NoteModal`, exactly as §C says.
9. **`save_setup` validates every value with `coerce_value` BEFORE writing any of them**, so
   a `Numbers…` submit with a good panel-minutes and a bad poll-minutes changes nothing at
   all rather than half of it. The floor's refusal sentence is the settings validator's own
   (`KEY_MIN_REASON`), which already names the number.
10. **`SETUP_DONE` is now computed from the store rather than from what was passed**, and
    says which of three things is true — the upload channel, the go-live channel it falls
    back to, or nowhere. The old wording could not describe a CLEAR, which §C's row 0
    requires.
11. **`tests/test_bot.py`'s `LOGS_GROUPS` entry for `uploads` and `tests/test_logkinds.py`'s
    `KNOWN_DYNAMIC` entry for `black_bloc/cogs/content/youtube.py::kind` were both deleted.**
    §E named the first; the second is the cog's old `_log(interaction, kind, …)` helper,
    which is gone — every kind is now a literal inside `kind_via(...)`, which the AST walk
    already unwraps, so the entry had become stale and the test said so.

**Findings NOT fixed, per §J** — §K 2 (two numbers for one fact), 3 (one kind for an outage
and a bad paste — the row now distinguishes them, the kind still does not), 4
(`ALREADY_LINKED` leaves no log row), 5 (moot: the retired subcommands were the ones missing
the db check, and the panel checks `db_ready` on every click), 6 (per-guild rows over a global
table; orphaned `youtube_videos`). §K 1 WAS fixed, because §H item 5 forces it: a link whose
feed would not answer now says the seed is still to come instead of claiming "the 0 already on
the channel are counted as seen".

**NOT verified.** No boot, no Discord, no YouTube: no panel opened, no button pressed, no
modal submitted, no channel resolved, no feed fetched, no DM delivered. Whether a Discord
client will submit an EMPTY `ChannelSelect`/`RoleSelect` at `min_values=0` is still unproven
here as it was for events and applications — `Forget…` is the fallback and is built either
way. The `youtube_mode` flip (F-Y2) was made by the conductor on the Go-live page at 17:42 after
v71 deployed; the mode is `shadow`.
