# Polls (F15) — what the popular poll apps do, what Discord gives free, and what Black Bloc should build

> **Audience:** the owner (to make the decisions at the bottom) and the build
> agent that eventually ships F15. **Status:** TRACKED (owner, 2026-08-31 —
> was local-only until then).
> **Last verified: 2026-09-11 09:30** — docs-wide staleness pass. **Re-measured:**
> `discord.py` is still **2.7.1** in the repo's `.venv`
> (`.venv/Lib/site-packages/discord/__init__.py:16`, `version_info` at :89), so every
> §3/§4 constraint cited against that version still cites the installed library, and the
> four typed-component modules §4 leans on — `discord/ui/label.py`, `radio.py`,
> `checkbox.py`, `file_upload.py` — are all present. ⚠️ **NOT re-checked:** no `path:line`
> anchor inside those library files was re-read, and no competitor (EasyPoll, Simple Poll,
> Polly) page was re-fetched — the vendor matrices are still the 2026-08-27 reading.
> ℹ️ **F15 SHIPPED long since** — Polls 10a/10b live 2026-08-27, the `/poll` **panel** as
> **v65** 2026-09-03, saved drafts as **v94** and create-a-recurrence-from-the-website as
> **v96**, both 2026-09-06. This doc is the research record behind that build, not a pending
> brief, and the command surface it proposes has been superseded by the panel.
> Before that, **2026-08-27** (STATUS line only re-checked 2026-08-31).
>
> **What IS measured:** every Discord-API constraint in §3 and §4 is read out of
> the repo's own `.venv` — `discord.py` **2.7.1**
> (`.venv/Lib/site-packages/discord/__init__.py:16`) — with `path:line`
> citations. The repo-fit design in §6 is read from the code in this tree.
>
> **What is NOT verified:** every third-party bot row is from **vendor
> marketing/docs pages, not from running the bot** — no poll bot was installed,
> no poll was created, and no pricing was seen behind a login. Discord's own
> published limits (§3) come from `docs.discord.com`; the *client-side* duration
> presets and the "mods with Manage Messages can end a poll" claim come from
> third-party write-ups, **not** from Discord's developer docs, and are marked
> `[blog]` below. Nothing here has been run against live Discord: **this repo
> has never created a poll of any kind.** `top.gg` returned **403** to every
> fetch, so bot install counts and "still maintained" claims are inferred from
> dated 2026 comparison articles, not from a store page.

---

## 1. The headline

Three things decide this whole feature:

1. ⚠️ **"Polly" is not a Discord app.** [polly.ai](https://www.polly.ai) is a
   **Slack and Microsoft Teams** product. Its help pages and pricing page name
   Slack and Teams and nothing else; its Discord presence is a small, unrelated
   reaction-poll bot of the same name on top.gg. So "copy Polly" cannot be taken
   literally — what the owner is describing (typed questions, anonymity,
   scheduling, recurrence, reminders, exports, a dashboard) is Polly's *Slack*
   feature set, and the Discord-native equivalents are **EasyPoll** and
   **Simple Poll**.
2. **Discord shipped native polls in 2024 and they are good.** Up to 10 answers,
   emoji per answer, multi-select, a duration up to 32 days, live bar results in
   the message, a real end-of-poll system message, and a gateway event per vote.
   `discord.py` 2.7.1 exposes all of it, and **the repo's existing intents
   already enable the vote events** (§4). Voting is a first-class Discord UI, not
   a bot's buttons — nothing we build will feel as native.
3. ⚠️ **Discord 2.7 modals are no longer text-only.** `discord.py` 2.7.1 ships
   `CheckboxGroup`, `Checkbox`, `RadioGroup`, `FileUpload` and *required* select
   menus **inside modals** (§4.4). That is what makes the owner's "set a data
   type for the box" ask cheap for everything except dates — there is still **no
   date picker anywhere in Discord**, so date polls are options-we-generate, not
   a calendar widget.

**The recommendation in one line:** native Discord polls as the voting surface
for the four types that fit it, a Black Bloc **panel** (buttons + modals) as a
second surface for the types native cannot express, one `/poll` command and one
storage layer over both, and scheduling / recurrence / reminders / results
archive / dashboard as the wrapper — which is exactly the part every poll bot
charges for.

---

## 2. Feature matrix

Columns: **Polly** (Slack/Teams — the thing the owner named) · **EasyPoll**
(Discord) · **Simple Poll** (Slack product; the Discord bot of that name is a
separate, thinner thing) · **Discord native** · **Black Bloc proposal**.

| Feature | Polly (Slack/Teams) | EasyPoll (Discord) | Simple Poll | Discord native | **Black Bloc proposal** |
|---|---|---|---|---|---|
| Runs on Discord | ❌ no Discord app | ✅ | ⚠️ Slack product; a same-named Discord bot exists | ✅ built in | ✅ |
| Max answer options | not published | **20** (`/poll`), **19** (`/timepoll`) | 20 `[blog]` | **10** | 10 native / 25 panel |
| Question length | not published | **1024** chars | not published | **300** chars | 300 native / 1024 panel |
| Answer label length | not published | **256** chars | not published | **55** chars | 55 native / 100 panel |
| Multi-select | ✅ | ✅ `maxchoices` 1–20 | ✅ | ✅ `allow_multiselect` | ✅ both surfaces |
| Anonymous voting | ✅ **Pro tier only** ($29/mo) | ✅ free (`type: anonymous`) | ✅ premium `[blog]` | ❌ voters are public and listable | ✅ panel only (see §5) |
| Hidden results until close | ✅ | ✅ (`type: hidden`) | ✅ premium `[blog]` | ❌ live bars, always | ✅ panel only |
| Live results | ✅ | ✅ | ✅ | ✅ (approximate until final) | ✅ |
| Duration / auto-close | ✅ deadlines | ✅ **30 days** max, natural-language times | ✅ | ✅ **32 days** max, **1 h** minimum | ✅ 32 d cap, 24 h default |
| Scheduled (post later) | ✅ Basic tier+ | ✅ `/schedulepoll` | ✅ premium `[blog]` | ❌ | ✅ |
| Recurring (daily/weekly/monthly) | ✅ Basic tier+ | ❌ not documented | ✅ | ❌ | ✅ |
| Reminders before close | ✅ `/polly remind` | ❌ not documented | ✅ | ❌ | ✅ |
| Restrict who may vote by role | ✅ audience targeting (Team tier) | ✅ `allowedrole` | not documented | ❌ everyone who can see it | ✅ panel enforces; native cannot |
| Weighted votes by role | ❌ | ✅ `/settings role-weight` | ❌ | ❌ | ❌ (recommend skipping) |
| Ping a role on open | ✅ | ❌ not documented | not documented | ❌ | ✅ |
| Edit poll after posting | ✅ | ✅ `/editpoll` | ✅ | ❌ **"the poll message cannot be edited"** | ⚠️ panel only |
| Reopen a closed poll | ✅ | ✅ `/reopenpoll` | ❌ | ❌ | ❌ (recommend skipping) |
| Close early | ✅ | ✅ `/closepoll` | ✅ | ✅ author only via API; mods w/ Manage Messages in-client `[blog]` | ✅ |
| Results export (CSV) | ✅ Basic tier+ | ✅ `/exportpoll` | ✅ | ❌ | ✅ from the dashboard |
| Results archive / history | ✅ 45 d free, unlimited paid | ✅ `/listpolls` | ✅ | ❌ nothing after the message scrolls away | ✅ SQLite, forever |
| Web dashboard | ✅ | ✅ `/dashboard` | ❌ | ❌ | ✅ a tab beside the other 13 |
| Auto-thread on the poll | ❌ | ✅ `/settings threads` | ❌ | ❌ | ⚠️ optional, cheap |
| Templates | ✅ | `/copypoll` | ❌ | ❌ | ⚠️ recurrence covers most of it |
| Q&A / surveys (multi-question) | ✅ | ❌ | ✅ up to 20 questions | ❌ | ❌ out of scope for v1 |
| Price for the above | Free 25 responses/mo → **$19 / $29 / $249** per month | **free, all features**; premium "planned" | free tier + premium | free | free, ours |

**Maintenance in 2026:** EasyPoll and Discord-native are both being actively
compared and documented in dated-2026 articles; EasyPoll's docs site is live and
lists a 2026 command set. Simple Poll is described in 2026 write-ups as "one of
the longest-running" and still recommended. Polly is a live commercial SaaS but
irrelevant to Discord. ⚠️ None of that is a *measurement* of maintenance — no
commit history or status page was checked.

### 2b. What each one charges for

Worth stating plainly because it is the argument for building this ourselves:
**the paid features in every one of these products are the wrapper, not the
voting.** Polly gates anonymity, scheduling, exports and history behind $19–$29
per month; Simple Poll gates anonymity and scale. EasyPoll gives it all away
free today and says a premium tier is "planned" — i.e. the free ride has a
stated end date. Black Bloc already owns a settings store, an action log, a
scheduler pattern (events, birthdays) and a dashboard; adding polls to it is
cheaper than adopting a bot whose free tier is on notice.

---

## 3. Answer types — the owner's "set a data type for the box"

The ask: the poll creator picks the **type of the answer box**, and that changes
how the poll behaves. Here is every type, who supports it, and what Black Bloc
would have to build.

| Answer type | Polly | EasyPoll | Discord native | What it takes in Discord | Black Bloc v1? |
|---|---|---|---|---|---|
| **Single choice** (radio) | ✅ | ✅ | ✅ | nothing — it *is* the native poll | ✅ native |
| **Checkbox** (multi-select) | ✅ | ✅ `maxchoices>1` | ✅ `allow_multiselect=True` | nothing | ✅ native |
| **Yes / No** | ✅ | ✅ | ✅ (a 2-answer poll) | nothing | ✅ native |
| **Rating scale / number scale** (1–5, 1–10) | ✅ | ⚠️ as plain options | ⚠️ as 5 or 10 answers — **10 is the cap**, so 1–10 exactly fits and 0–10 does not | nothing; the *average* has to be computed by us from the counts | ✅ native |
| **Ranked choice** | ✅ (rank order) | ❌ | ❌ | panel: one string-select per rank, or N selects in a modal; instant-runoff counted in a pure module | ❌ v2 |
| **Free text / open-ended** | ✅ | ❌ | ❌ | panel: an "Answer" button → modal with a paragraph `TextInput`; answers stored by us | ⚠️ owner call |
| **Number** (free numeric, not a scale) | ✅ (numerical) | ❌ | ❌ | modal `TextInput` + our own validation and error sentence | ❌ v2 |
| **Point allocation** | ✅ | ❌ | ❌ | modal with one `TextInput` per option + a sums-to-100 check | ❌ skip |
| **Date / date-range (availability)** | ⚠️ not a documented Polly type | ❌ | ❌ | ⚠️ **there is no date input anywhere in Discord.** See below | ✅ panel (owner call) |
| **File / image answer** | ❌ | ❌ | ❌ | modal `FileUpload` (new in discord.py 2.7) | ❌ skip |

### 3a. The date type, in detail — because it is the one with no native answer

⚠️ **Discord has no date picker, no calendar widget and no date input.** Not in
modals, not in components, not in polls. Every "date poll" in Discord is really
*a list of candidate dates rendered as options*. The three patterns actually in
use:

- **Generated options + a normal poll.** The creator gives a start date and a
  count (`/poll date start:2026-09-01 days:7`), we generate the candidate slots,
  and each becomes an answer. **If ≤10 slots it is a native multi-select poll**
  and costs us nothing beyond the label generation. Above 10 it must be a panel.
- **A persistent weekly grid of buttons** — the Supatimer pattern: a fixed set
  of day × time-block buttons (morning / afternoon / evening / late), a
  *per-server* timezone so the blocks mean the same thing for everyone, and a
  message that edits itself in place and resets weekly. This is the When2meet
  shape, done with buttons.
- **Leave Discord** — a When2meet link. What the server presumably does today.

**How we render the dates matters and is unverified.** The repo already has the
right tool: `timezones.py:stamp` produces HammerTime-style `<t:epoch:F>` stamps,
which render in each viewer's own timezone. ⚠️ **It has NOT been verified that
`<t:…>` markdown renders inside a poll *answer* label** — poll answers are
`PollMedia.text` (a 55-character string), and there is no statement either way
in the developer docs. **The build agent must test this in the test channel
before designing around it.** If it does not render, date labels fall back to
plain text in the server timezone (`America/Phoenix`, the value already used for
birthdays) plus one `<t:…>` line in the poll *question* or a follow-up message.

### 3b. What the type actually changes

The type is not cosmetic — it selects the **surface**, the **validation**, the
**storage** and the **results renderer**:

| Type | Surface | Where the votes live | Results shown as |
|---|---|---|---|
| single / checkbox / yes-no / scale | **native poll** | at Discord (we read counts) | native bars live; our archive embed at close |
| scale | native poll | at Discord | bars + **a mean we compute** |
| date (≤10 slots) | native poll, multi-select | at Discord | bars, best slot named |
| date (>10 slots) | **panel** | `poll_votes` | a text bar chart per slot |
| free text / number | **panel** (button → modal) | `poll_votes.answer` | a list, or numeric summary |
| ranked | **panel** | `poll_votes` with rank | IRV rounds, computed in the pure module |

---

## 4. Discord native polls, measured from discord.py 2.7.1

All paths below are relative to
`C:\Users\nbasl\OneDrive\Documents\vs-code-repos\black_bot_baf\.venv\Lib\site-packages\`.
Version: `discord/__init__.py:16` → `__version__ = '2.7.1'`.

### 4.1 The objects

| Thing | Where | Note |
|---|---|---|
| `discord.Poll(question, duration, *, multiple=False, layout_type=…)` | `discord/poll.py:323`, ctor `:364` | `__all__` at `:58` exports exactly `Poll`, `PollAnswer`, `PollMedia` |
| `PollMedia(text, emoji=None)` | `discord/poll.py:68` | emoji "is only valid for poll answers" (`:77`) |
| `PollAnswer` | `discord/poll.py:107` | `.id`, `.text`, `.emoji`, `.vote_count`, `.self_voted`, `.victor` |
| `Message.poll` → `Optional[Poll]` | `discord/message.py:2224–2227`, documented `:2125` | populated from the payload on construction |
| `poll.end()` | `discord/poll.py:648` | calls `Message.end_poll()` (`discord/message.py:1877`) → `POST /channels/{id}/polls/{id}/expire` (`discord/http.py:2766`) |
| `PollAnswer.voters()` | `discord/poll.py:236` | async iterator of `User`/`Member` |
| Sending one | `discord/abc.py:1541` (`Messageable.send(poll=…)`), `discord/interactions.py:970` (`InteractionResponse.send_message(poll=…)`), `discord/webhook/async_.py:1678` | |

### 4.2 The numbers

| Limit | Value | Source |
|---|---|---|
| Max answers per poll | **10** | Discord developer docs (`docs.discord.com/developers/resources/poll`). ⚠️ **`discord.py` does NOT enforce it** — `Poll.add_answer` (`discord/poll.py:594`) has no cap; an 11th answer fails as a `400` from the API at send time |
| Question text | **300** characters | `discord/poll.py:331` (docstring) |
| Answer label text | **55** characters | `discord/poll.py:605–606` (docstring) |
| Duration | **up to 32 days**, default 24 h | developer docs |
| Duration granularity | **whole hours, minimum 1** | `discord/poll.py:333` "Duration must be in hours"; `_to_dict` sends `duration.total_seconds() / 3600` (`:479`); reading one back **rounds to whole hours** (`:452`). A 30-minute poll is not expressible |
| Layout types | **exactly one** (`default = 1`) | `discord/enums.py:937–938` |
| `voters()` page size | **100 per request**, `limit` defaults to the vote count or 100 | `discord/poll.py:285–291` |
| Voters endpoint (API) | 1–100, default 25 | developer docs |
| Answers editable after posting | **no** — "the poll message cannot be edited" | developer docs; `add_answer` raises `ClientException` once the poll has a message (`discord/poll.py:621–622`) |
| Bots may vote | **no** — "Apps are not allowed to vote on polls" | developer docs |
| Who may end it | the author. "You cannot end polls from other users" | developer docs. `[blog]` Mods with Manage Messages can end one in the client — **not** in the developer docs, treat as unconfirmed |
| Client duration presets | 1 h, 4 h, 8 h, 24 h, 3 d, 1 week, 2 weeks | `[blog]` — the **API** allows any whole hour up to 32 days, so a bot is not bound by the client's list |

### 4.3 The vote events and the intent

- Events: `on_poll_vote_add` / `on_poll_vote_remove` (user + `PollAnswer`) and
  `on_raw_poll_vote_add` / `on_raw_poll_vote_remove`
  (`discord/state.py:1739` and `:1757`).
- ⚠️ **The non-raw events only fire when the message is in the cache AND the
  user resolves** (`discord/state.py:1752` / `:1770`: `if message and user:`).
  For a poll that has been open for a week, **the raw events are the reliable
  ones** — `RawPollVoteActionEvent` carries `user_id`, `channel_id`,
  `message_id`, `guild_id`, `answer_id` (`discord/raw_models.py:528–555`).
- Intent: `Intents.guild_polls` = `1 << 24`, `Intents.dm_polls` = `1 << 25`,
  the `polls` alias sets both (`discord/flags.py:1342–1387`). **Not privileged.**
- ✅ **The repo already has it.** `black_bloc/intents.py:7` calls
  `discord.Intents.default()`, which is `Intents.all()` minus `presences`,
  `members`, `message_content` (`discord/flags.py:834–841`) — so
  `guild_polls` and `dm_polls` are **already on**. **No intent change, no
  developer-portal change, no re-invite.**

### 4.4 Modal components in 2.7.1 — the "data type for the box" primitives

This is newer than most write-ups and it is what makes §3 affordable:

| Component | Where | Added |
|---|---|---|
| `ui.Label(text=…, component=…)` — wraps a component with a label | `discord/ui/label.py:50` | 2.6 |
| `ui.TextInput` (short / paragraph, `min_length`, `max_length`, `required`) | `discord/ui/text_input.py:53` | 2.0 |
| `ui.CheckboxGroup` (with `min_values` / `max_values`) and `ui.Checkbox` | `discord/ui/checkbox.py:61`, `:283` | **2.7** |
| `ui.RadioGroup` | `discord/ui/radio.py:56` | **2.7** |
| `ui.FileUpload` (`min_values` / `max_values`) | `discord/ui/file_upload.py:55` | **2.7** |
| Select menus inside modals, with `required` | `discord/ui/select.py:348–353` — "Only supported in modals" | 2.7 |

So a **one-screen poll-creation modal with typed fields** is now possible:
question (`TextInput`), answer type (`RadioGroup`), options (`TextInput`
paragraph, one per line), duration (`Select`), flags (`CheckboxGroup` —
multi-select / anonymous / hide results / ping role). ⚠️ **Not verified against
live Discord** — the repo's `phase4-design.md` already flags that the modal
component cap is ambiguous between the old 5 and a newer 40-component scheme,
and this has never been exercised. The build agent must confirm the cap in the
test channel and be ready to fall back to slash-command options.

### 4.5 Test mode — where the guard does and does not reach

Measured from `black_bloc/guard.py:75–116`: the guard patches exactly
`http.send_message`, `http.edit_message` and `http.delete_channel`.

| Poll operation | Gated by `TestModeGuard`? |
|---|---|
| `channel.send(poll=…)` from a loop / the API | ✅ yes — goes through `http.send_message` |
| A poll posted as a slash-command **response** | ⚠️ **not by the HTTP patch** — `InteractionResponse.send_message` uses `adapter.create_interaction_response` (`discord/interactions.py:1085`). It is gated by `tree.interaction_check` (`guard.py:121`), i.e. only because the *command* must be run in the test channel |
| `poll.end()` / `end_poll()` | ❌ **no** — `http.end_poll` is unpatched |
| `PollAnswer.voters()` | ❌ no — read-only, but it reads a real channel |

⚠️ **So the polls cog must check `bot.guard` by hand at the close and
voter-fetch sites**, exactly as `cogs/moderation/automod.py` does for delete and
timeout. This belongs in the build brief as a hard requirement.

---

## 5. What native polls cannot do — and whether the panel fallback is worth it

| Native cannot | Consequence | Fallback worth building? |
|---|---|---|
| **More than 10 options** | a 14-date availability poll is impossible | ✅ **yes** — panel with buttons/select (25 select options, 25 buttons over 5 rows) |
| **Anonymous voting** | ⚠️ **anyone can list every voter**, and so can we (`voters()`) | ✅ **yes, if the owner wants it** — but only a panel can deliver it, because on a native poll the anonymity would be a lie |
| **Hide results until close** | live bars sway late voters | ✅ yes, same panel |
| **Restrict voting to a role** | anyone who can see the channel votes | ⚠️ **partial** — a panel can refuse the button press with a sentence. On native, the *only* option is posting in a role-gated channel |
| **Extend or edit after posting** | a typo means delete and repost | ⚠️ panel only; low value |
| **Ranked choice** | no IRV, no rank order | ⚠️ v2 — real work (a counting algorithm and a rank UI) |
| **Free text / number answers** | no open-ended questions | ✅ cheap now that modals are typed (§4.4) |
| **Sub-hour polls** | no 15-minute "who's on now" | ⚠️ panel only; low value |
| **Any record after the message scrolls away** | no history, no export, no dashboard | ✅ **this is the highest-value thing we add, and it works for native polls too** |

**Verdict.** The panel is worth building — but as the **second** surface, in a
second slice, and only because the owner's own ask (typed answer boxes, dates)
cannot be met without it. ⚠️ **Do not make the panel the default.** Native polls
get Discord's own voting UI, mobile support, notifications and a real end-of-poll
system message; a button panel gets none of that and drifts the moment Discord
changes its component rules. Native first, panel when the type demands it.

---

## 6. Recommended design, in this repo's shape

### 6.1 Shape

```
black_bloc/
├── polls.py                     ← PURE: the answer types, option generation, duration parsing,
│                                  the date-slot generator, the text bar chart, the IRV count later,
│                                  the status machine, every refusal sentence. No discord import
│                                  beyond embeds, exactly like events.py / birthdays.py
├── cogs/community/polls.py      ← the cog: /poll group, the creation modal, the panel view,
│                                  the due-loop (open scheduled, remind, close), the vote listeners
└── api/tools/polls.py           ← ONE router, calling the cog's plain helpers — never a second
                                   copy of the rule (the events router is the model)
site/public/polls.html + assets/page-polls.js   ← a 14th tab; nav entry added to the ONE array in app.js
site/mock/contract.json                         ← routes + page keys, or the contract check goes red
tests/test_polls.py
tests/cogs/community/test_polls.py
tests/api/tools/test_polls.py
```

### 6.2 The status machine (pure module, mirrors `events.py:24–40`)

```
draft → scheduled → open → closed
            ↓         ↓
        cancelled  cancelled
pending → denied            (only when poll_review_required is true)
```

### 6.3 Storage — four tables, all additive

Per `architecture.md` rule 5 these are `CREATE TABLE IF NOT EXISTS` + an index,
so **no `SCHEMA_VERSION` bump is required**; nothing here is a rewrite of an
existing table.

```sql
CREATE TABLE IF NOT EXISTS polls (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id      INTEGER NOT NULL,
    creator_id    INTEGER NOT NULL,
    question      TEXT    NOT NULL,
    kind          TEXT    NOT NULL DEFAULT 'choice',   -- choice|checkbox|yesno|scale|date|text|number|ranked
    surface       TEXT    NOT NULL DEFAULT 'native',   -- native|panel
    multi         INTEGER NOT NULL DEFAULT 0,
    anonymous     INTEGER NOT NULL DEFAULT 0,
    hide_results  INTEGER NOT NULL DEFAULT 0,
    channel_id    INTEGER,
    message_id    INTEGER,                             -- the poll message once posted
    ping_role_id  INTEGER,
    vote_role_id  INTEGER,                             -- panel only; native cannot enforce it
    status        TEXT    NOT NULL DEFAULT 'draft',
    opens_at      TEXT,                                -- scheduled polls
    closes_at     TEXT,
    reminded_at   TEXT,                                -- set once, so a reminder never doubles
    closed_at     TEXT,
    total_votes   INTEGER,                             -- exact, written at close
    schedule_id   INTEGER,                             -- the recurrence that produced it
    decided_by    INTEGER,  decided_at TEXT,  deny_reason TEXT,   -- only if review is on
    created_at    TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS polls_by_status ON polls(guild_id, status, closes_at);

CREATE TABLE IF NOT EXISTS poll_options (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    poll_id     INTEGER NOT NULL,
    position    INTEGER NOT NULL,
    answer_id   INTEGER,          -- Discord's PollAnswer.id, when surface='native'
    label       TEXT    NOT NULL,
    emoji       TEXT,
    value       TEXT,             -- ISO instant for kind='date', the number for 'scale'
    final_votes INTEGER           -- written once at close; NULL while open
);
CREATE UNIQUE INDEX IF NOT EXISTS poll_options_slot ON poll_options(poll_id, position);

CREATE TABLE IF NOT EXISTS poll_votes (           -- PANEL surface only; native votes live at Discord
    poll_id   INTEGER NOT NULL,
    option_id INTEGER,
    user_id   INTEGER NOT NULL,
    answer    TEXT,               -- free text / number / rank
    at        TEXT    NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS poll_votes_one ON poll_votes(poll_id, option_id, user_id);

CREATE TABLE IF NOT EXISTS poll_schedules (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id    INTEGER NOT NULL,
    creator_id  INTEGER NOT NULL,
    template    TEXT    NOT NULL,   -- JSON: the /poll arguments, replayed each time
    cadence     TEXT    NOT NULL,   -- 'daily' | 'weekly:mon' | 'monthly:1'
    at_local    TEXT    NOT NULL,   -- 'HH:MM'
    tz          TEXT    NOT NULL,   -- defaults to America/Phoenix, same as birthdays
    next_at     TEXT    NOT NULL,
    last_poll_id INTEGER,
    enabled     INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL
);
```

⚠️ **Deliberate asymmetry, and it is the crux of the design: for a native poll
we do NOT store individual votes.** Discord owns them; we read counts from
`Message.poll` and, at close, write `final_votes` per option and `total_votes`
once. Storing a per-user row for a native poll would mean maintaining a shadow
tally off the vote gateway events — which, per §4.3, **only fire reliably in
their raw form** and would silently drift on any missed event. Counts read from
the message at close are exact (`discord/poll.py:206–211`: approximate while
open, exact when finished). Anonymity is why `poll_votes` exists at all: it is
for the panel, where we are the authority.

### 6.4 Commands

```
/poll create      question, type (choice|checkbox|yesno|scale|date|text), options,
                  duration, multi, ping_role, anonymous, hide_results, channel
                  → opens the typed modal (§4.4) for anything the options cannot carry
/poll date        start, days, blocks_per_day, duration      → the availability shape
/poll list        open / scheduled / closed
/poll close       id                     → poll.end() + the results embed
/poll results     id                     → re-post the results embed
/poll cancel      id
/poll schedule    … cadence, at, tz      → a row in poll_schedules
/poll settings    the keys below         → the same shape as /event settings  (⚠️ 2026-09-03: that subcommand is retired; events' settings are a sub-panel now)
```

### 6.5 Settings keys (rows in `settings_store.py:KEY_TYPES`, per rule 4)

| Key | Type | Default |
|---|---|---|
| `poll_mode` | enum `off\|shadow\|on` | `off` until the owner turns it on |
| `poll_channel_id` | channel | unset → the channel the command was run in |
| `poll_results_channel_id` | channel | unset → same channel as the poll |
| `poll_ping_role_id` | role | none |
| `poll_who_can_create` | enum `staff\|role\|everyone` | `staff` |
| `poll_creator_role_id` | role | none (used when `poll_who_can_create=role`) |
| `poll_default_duration_hours` | int (1–768) | `24` |
| `poll_default_surface` | enum `native\|panel` | `native` |
| `poll_max_options` | int (2–25) | `10` |
| `poll_review_required` | bool | `false` |
| `poll_reminder_minutes` | int (0 = off) | `60` |
| `poll_allow_anonymous` | bool | `false` |
| `poll_retention_days` | int | `0` = keep forever |

Constants beside them, in the style of `EVENTS_*`: `POLL_MODES`,
`POLL_KINDS`, `POLL_SURFACES`, `POLL_MAX_NATIVE_OPTIONS = 10`,
`POLL_QUESTION_LIMIT = 300`, `POLL_LABEL_LIMIT = 55`,
`POLL_MAX_DURATION_HOURS = 32 * 24`, `POLL_MIN_DURATION_HOURS = 1`.

### 6.6 The loop and the reminder

One `tasks.loop(minutes=1)` in the cog, the `events.py` `run_due_events` shape:
open anything `scheduled` whose `opens_at` has passed; post the reminder for any
`open` poll inside `poll_reminder_minutes` of `closes_at` with `reminded_at`
still NULL (**set `reminded_at` in the same statement that sends, so a restart
cannot double-ping**); close anything past `closes_at` that Discord has already
finalised, and write the results. Plus a `reconcile` loop on the `events.py`
model, to notice a poll whose message was deleted.

⚠️ **Native polls auto-close themselves at expiry** — Discord posts a
`MessageType.poll_result` system message (`discord/enums.py:279`,
`discord/message.py:2854`). Our loop's job at close is **not** to end the poll
but to *read the final counts and archive them*; call `poll.end()` only for a
manual early close.

### 6.7 The results embed

One embed, the `events.py` "one card" pattern, with a text bar chart:

```
Best day for the cookout?          closed · 41 votes · 2026-09-01 18:00

Saturday    ████████████████░░░░  22  (54%)   ← winner
Sunday      ██████████░░░░░░░░░░  13  (32%)
Friday      ████░░░░░░░░░░░░░░░░   6  (15%)
```

Twenty cells, `█`/`░`, computed in `polls.py` and unit-tested with no gateway —
the same way `events.py` renders its card. The winner comes from
`Poll.victor_answer` (`discord/poll.py:511`), which ⚠️ **is always `None` until
the poll has finished** (`:517`), so the renderer must handle both states.

### 6.8 The dashboard tab

`polls.html` + `page-polls.js`, a nav entry in the one array in `app.js`, and
routes in `contract.json` (or the contract check goes red — the Phase 8b lesson).
Routes, following `api/tools/events.py` exactly (`staff_dependency` on the
router, `writer_dependency` per write, `require_guild` / `require_db`, a
`web.poll.<verb>` line through `note()`):

```
GET  /api/polls?status=open,scheduled,closed
POST /api/polls                    create (and post, or schedule)
GET  /api/polls/{id}               one poll + its options + counts
POST /api/polls/{id}/close
POST /api/polls/{id}/cancel
GET  /api/polls/{id}/export        CSV — the thing Polly charges for
GET  /api/polls/schedules
POST /api/polls/schedules          create a recurrence
POST /api/polls/schedules/{id}/toggle
```

### 6.9 Action-log kinds

`poll.create`, `poll.open`, `poll.remind`, `poll.close`, `poll.cancel`,
`poll.schedule` — every one through `actionlog.py:log_action`
(`black_bloc/actionlog.py:54`), and the web verbs as `web.poll.*`, so the audit
tab picks them up with no extra work. New kinds also need adding to
`contract.json`'s `action_kinds`.

---

## 7. Owner decisions — one per line, each with a recommended default

Ask these **one at a time** per the global rule; the recommended default is what
Black Bloc does if the owner says "your call".

1. **Which answer types in v1?** → *recommended:* **single choice, checkbox, yes/no, rating scale, and date/availability.** Free text, number and ranked wait for v2. The first four are free (native); date is the only one that forces the panel, and it is the one with real use here (event scheduling).
2. **Who may create a poll?** → *recommended:* **staff only** (`poll_who_can_create=staff`) for the first weeks, then widen. Matches how events shipped.
3. **Is staff review required before a poll posts, like events?** → *recommended:* **no.** A poll is not a scheduled event; review is friction with no payoff. Revisit only if decision 2 becomes `everyone`.
4. **Default duration?** → *recommended:* **24 hours** (Discord's own default), owner-changeable per poll, hard ceiling 32 days.
5. **Anonymous votes?** → *recommended:* **off by default, and only available on panel polls.** On a native poll anyone can list every voter, so offering "anonymous" on native would be a false promise.
6. **Results live or only at close?** → *recommended:* **live** — it is what native does and cannot be turned off there. "Hide until close" available on panel polls only.
7. **Which channel do polls go to?** → *recommended:* **the channel the command was run in**, with `poll_channel_id` as an optional pin. ⚠️ Under `TEST_MODE` this is `#mute-me-bot-test-spam` regardless.
8. **Ping a role when a poll opens?** → *recommended:* **none by default**, `poll_ping_role_id` available — the same call the owner already made for events and go-live.
9. **Reminder before close?** → *recommended:* **60 minutes, in the poll's channel, no role ping**; `0` turns it off.
10. **Recurring polls in v1?** → *recommended:* **yes, but staff-only and capped at daily/weekly/monthly.** It is the feature Polly charges $19/month for and the loop is already the events/birthdays shape.
11. **Weighted votes by role** (EasyPoll has it)? → *recommended:* **no.** A weighted vote that looks like a normal vote is a trust problem, and this server has no use for it.
12. **Reopen a closed poll?** → *recommended:* **no.** Native cannot, and a reopened poll with a published result is a data-integrity mess.
13. **Auto-create a thread under each poll for discussion?** → *recommended:* **off, with a setting.** Cheap, but it clutters a quiet server.
14. **Keep results forever, and expose a CSV export on the dashboard?** → *recommended:* **yes to both** — this is the single biggest thing we add over native, and it costs one route.
15. **Does F15 jump the queue, or land after the current phase?** → *recommended:* **after.** Nothing depends on it, and native polls already cover the incumbent's YAGPDB reaction polls in `#announcements` today at zero cost.

---

## 8. Build size, in this repo's phase terms

Split it. The whole thing in one dispatch is a multi-layer build in the
expensive band; two slices each land on their own.

| Slice | Contents | Rough size |
|---|---|---|
| **9a — native polls** | `polls.py` (pure: types, durations, bar chart, status machine, sentences) · `cogs/community/polls.py` (`/poll create/list/close/results/cancel/settings`, the due-loop, the reminder, the raw vote listeners) · the four tables · ~13 settings keys · `tests/test_polls.py` + `tests/cogs/community/test_polls.py` | ~**1,200–1,500** lines of source, ~**900** of tests. Comparable to Phase 4 (events: 1,559 + 187 source, 1,851 test) — call it one Opus build agent in the **250–350k** band |
| **9b — the wrapper** | the panel surface (date/availability, free text, anonymity, >10 options) · `/poll schedule` + recurrence · `api/tools/polls.py` · `polls.html` + `page-polls.js` + the nav entry + `contract.json` · `tests/api/tools/test_polls.py` | ~**900** lines of source, ~**500** of tests. A second agent in the **200–300k** band |

**Prep before dispatching either** (global rule): clean tree, a fresh usage read,
and a brief that carries the test-channel rule, `docs/info/review-checklist.md`,
the §4.5 guard finding, and the two unverified items in §9 as things to *measure
first, then design around*.

---

## 9. What is NOT verified — read this before trusting anything above

- ⚠️ **Nothing here has ever run.** This repo has never created a poll, native or
  otherwise, and no poll bot was installed to compare against.
- ⚠️ **Whether `<t:…>` timestamp markdown renders inside a poll answer label
  (`PollMedia.text`) is UNKNOWN** and there is no statement either way in the
  developer docs. It decides how date polls read. **Test it first.**
- ⚠️ **The modal component cap in 2.7.1 is untested** — `phase4-design.md`
  already flags the 5-vs-40 ambiguity, and §4.4's typed-modal design assumes the
  newer scheme. Confirm before designing the creation flow around one screen.
- **The "mods with Manage Messages can end a poll early" claim is `[blog]`**, not
  developer docs. The docs say only "You cannot end polls from other users."
- **Every third-party bot row is vendor-published, not observed.** EasyPoll's
  numbers (20 answers, 1024/256 characters, 30 days, `allowedrole`, role weights,
  the command list) come from its own docs site; Simple Poll's Discord-side
  behaviour is the weakest row in the table because `simplepoll.rocks` documents
  the **Slack** product and `top.gg` returned **403**.
- **Pricing is as published on 2026-08-27** and was not seen behind a login.
  Polly: free (25 responses/mo) / $19 Basic / $29 Pro / $249 Team. EasyPoll:
  free, premium "planned".
- **"Still maintained in 2026" is inference** from dated comparison articles, not
  from commit history, a status page, or a store listing.
- The repo-side claims **are** measured: intents (`black_bloc/intents.py:7`),
  the guard's reach (`black_bloc/guard.py:75–116`), the schema conventions
  (`black_bloc/storage/db.py:227`), the settings registry
  (`black_bloc/settings_store.py:68`) and the router pattern
  (`black_bloc/api/tools/events.py`) were all read today.

## See also

- [`feature-list.md`](feature-list.md) — F15 is listed as *Future (found)*: "YAG
  reaction polls are used in `#announcements`… Discord now has native polls — may
  need nothing." This document is the answer to "may need nothing": **native
  covers the voting, and the wrapper is what is missing.**
- [`phase4-design.md`](phase4-design.md) — the closest existing feature; the
  loop, the review flow, the status machine and the one-card renderer are all
  borrowed from it.
- [`architecture.md`](architecture.md) — rules 2, 4, 5 and 7 shape §6.
- [`review-checklist.md`](review-checklist.md) — the build and review brief.
