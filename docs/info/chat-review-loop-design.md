# The chat review loop — learning from conversations with the bot (loop 1)

> **Audience:** the owner, the conductor, and any session touching chat. **Status:** TRACKED.
> **Last verified: 2026-09-23 16:2x — the status and §11 only**, at the v162 docs ritual. ✅ **LIVE as v162** — merged to `main` as
> `737e660c` (8 commits, 16:14 by `git log`; registry count fix `ed42d7e3`), deployed 2026-09-23 **16:20** Phoenix (release commit
> `4e6e4e4c`); schema **58** live; the v162 gate on merged main: **7790 passed / 3 skipped**, check.mjs 22 pages / 216 routes. Boot
> `database ready` 23:19:53Z, `logged in` 23:19:57Z; `GET /api/chat/review` at 16:2x answers every count 0, `items []` — the route is
> live, the queue empty. §11 lists what is still not verified.
> Before that, **2026-09-23** against branch `chat-review-loop` (off `main` `c69ac22e`): the gate numbers in §10 were measured on the
> branch, BUILT, NOT MERGED, NOT DEPLOYED.

## 1. The ask

Owner, 2026-09-23 15:3x, verbatim: *"is there a way to automate the training loop? … see how people
talk, assign intentions to them and then audit those intentions periodically and feed that data to
the bot"* → *"start with loop 1, park loop 2, we would want an automated way to tag intent. maybe we
need to feed it into a doc that i can set up a schedule for and have claude work review it and
assign intent or something. I want to automate it somehow".*

**Loop 1 = learn from conversations WITH the bot.** The models are hosted, so nothing is
fine-tuned: what Black Bloc "learns" is its intents (`chat_intents` + `chat_lines`), its knowledge
notes, its channel notes and its voice. This loop feeds the first two. Loop 2 (server-wide
listening) is parked — §8.

## 2. The shape

```
answer posted ──► weak? (4 reasons) ──► chat_review row (open) ──► cheap model tags it (one capped call)
                                                                   │
            staff: Approve / Change / Dismiss  ◄── Chat page Review queue · /chat ▸ Review queue…
                         │                                         ▲
                         ▼                                         │ daily digest line in the log channel
           intent trigger · new intent · knowledge fact            │ GET /api/chat/review.md (scheduled reader)
```

One module owns detection, tagging, teaching and the digest: `black_bloc/chat_review.py`. One write
path owns the four staff moves: `chat_panel.approve_review / change_review / dismiss_review /
reopen_review`, which the site routes and the `/chat` panel both call.

## 3. When an answer is queued — the four reasons

| Reason | Key | When |
|---|---|---|
| `ungrounded` | — | The answer came from the IMPORTANT tier and `hits_for` found **zero** knowledge sections: a real question the bot could not ground. `conversational_reply` hands the hit count over through `chat_review.note_grounding` on its return path (the one line it gained); nothing else in `chat_llm` changed. |
| `reask` | `chat_review_reask_seconds` (90; 0 turns it off) | The same person writes again in the same channel within the window, and the message is not only a thanks/ack (`chat_review_ack_phrases`, one home, a key). |
| `not_it` | `chat_review_not_it_phrases` (a handful, comma-separated; blank off) | The follow-up contains one of the phrases. Judged over the longer of the re-ask window and 90 s, so it still works with re-ask off. Beats `reask`. |
| `downvote` | `chat_review_downvote_emoji` (👎; blank off) | Anybody but the bot reacts with it on one of the bot's recent chat answers. |

- **One item per reply** (unique index on `reply_id`): the first reason wins; a later 👎 on an
  already-queued answer adds nothing.
- Every reply is judged, canned or model — a canned intent that fired on the wrong phrase is exactly
  what loop 1 should catch. DMs are never queued (the queue is per server).
- The follow-up and 👎 checks read an in-memory note of the last answer per (channel, person) and
  the last 500 replies. ⚠️ **A restart forgets them**: a 👎 on an answer from before the restart is
  not seen. Accepted — a thumbs down lands within minutes or not at all.
- ⚠️ **Known noise:** a real back-and-forth conversation with the bot counts every quick follow-up
  as a re-ask. The ack list takes the thanks out; `chat_review_reask_seconds = 0` takes the rest
  out if the queue fills with it. Measure before tuning.

## 4. The memory opt-out, and what is kept

A person the `/memory` consent says is **not remembered** gets **no review row at all** — their text
is never stored. The check is `chat_memory.remembers(...)` with `chat_memory_consent`, the same read
`/memory` and the distiller use, so under `optin` nobody is queued until they opt in. An unreadable
opt-out table counts as *not remembered* (fails safe). What a row keeps is the two messages only —
`asked` and `answered` — each clipped to 1,000 characters, plus ids, tier, trope, the matched intent
and the reason.

## 5. Tagging — the one model call

Once per item, off the reply path (`schedule_tag` → a background task), plus a batch of 5 on a
10-minute review tick for anything the moment of opening missed. The cheap tier (Groq,
`chat_simple_model`) gets the reason, the person's message, the bot's answer, the enabled intents
with up to 12 of their phrases each, and the staff-written knowledge headings, and must answer:

```json
{"kind": "intent"|"phrase"|"knowledge"|"none", "intent": "<name or null>", "phrase": "<trigger or null>",
 "line": "<one-line fact or null>", "section": "<knowledge heading or null>", "why": "<short>"}
```

`section` is an optional extra over the brief's shape, so a fact can name the note it belongs in.
**Parsed defensively** (`parse_tag`): not JSON, not an object, an unknown kind, a non-string field,
a phrase over 60 or a line over 300 characters, a `phrase` naming an intent the server does not
have, or a missing phrase/line → `kind: none` with `why` = *the model's answer was not in the shape
asked for*, and a warning in the log. A `kind: intent` naming an intent that already exists becomes
`phrase`. A new intent's name is made snake_case from what the model gave, or from the phrase.

**The cap.** Every call writes an `llm_ledger` row (tier `review`, no user) and counts toward
`chat_monthly_cap_usd`; once the month's spend reaches the cap, items wait **untagged** and the page
and `/chat` say so (`chat_review_capped`). A tag also counts as one turn toward `chat_daily_turns`,
and waits when the day is full. No Groq key → untagged, said in words. `chat_review_mode = off`
stops detection, tagging and the digest; items already queued stay decidable.

Log kinds (all ROUTINE): `chat.review_opened` (reason), `chat.review_tagged` (the suggestion),
`chat.review_approved`, `chat.review_changed`, `chat.review_dismissed`, `chat.review_reopened`
(`web.` spellings through the site), `chat.review_digest`.

## 6. Staff review — both doors, one write path

| Move | Writes | Refused when |
|---|---|---|
| **Approve** | the suggestion: a phrase → appended to that intent's triggers (`clean_triggers` dedups and bounds it); a new intent → created with the phrase and ONE **switched-off** placeholder line (`chat_review_placeholder_line`), so it stays silent until staff write the real line and switch it on; a fact → appended to the named staff note, or to a *From review* note (`chat_review_section_default`), never to a note Black Bloc writes for itself | the item is not open (409 `already_decided`), or has nothing to teach (409 `nothing_to_approve`) |
| **Change** | staff's own `{kind, intent, phrase, line, section}` through the same `teach`, and records it on the row | the intent does not exist, the phrase/line is blank, the kind is unknown (400, in words) |
| **Dismiss** | nothing learned | not open |
| **Reopen** | a dismissed item back to open — *staff always have the final say* | not dismissed: an approved or changed item is undone where it was written (Intents / Knowledge) |

The item is **claimed first** (`UPDATE … WHERE status = 'open'`), then written; a write that is
refused hands it back open, so two staff pressing at once write once. Every answer is a keyed
sentence (`chat_review_*`, 44 wording keys — every word the panel and the digest say).

- **Chat page ▸ Review queue** (`#sect-review`, count in the rail): filter by status and reason,
  each card asked → answered (dim) with the reason badge, the suggestion and its why, Approve /
  Dismiss / Change… (a phrase for an intent, a new intent, or a fact) / Reopen, **Download as
  markdown**, and the six behaviour keys + the 44 wording keys in two foldouts.
- **`/chat` ▸ Review queue…**: five items a page (Previous/Next render only where there is
  somewhere to go), an item picker, then the item card: an intent select ("Change it: this should
  reach…") opens a phrase form prefilled with the suggestion; **Approve** renders only when the
  suggestion teaches something; **Write a fact…**; **Dismiss**; Back.
- API: `GET /api/chat/review?status=&reason=`, `POST /api/chat/review/{id}/approve|dismiss|reopen`,
  `PUT /api/chat/review/{id}`, all staff-gated, writes behind the writer gate.

## 7. The daily digest and the scheduled second pass

On the review tick, once per **local** day (`default_timezone`) at or after
`chat_review_digest_hour` (9), if anything is open: ONE line to `log_channel_id` —
`chat_review_digest` with `{count}` and `{link}` (the Chat page's `#sect-review`, or `/chat ▸
Review queue…` when no origin is set) — and a `chat.review_digest` row, which is what makes it once
a day across restarts. The test-mode guard still applies.

**The export.** `GET /api/chat/review.md` is the open queue as one markdown document (item, reason,
when, tier, matched intent, asked, answered, suggestion, why). A scheduled Claude routine can read
it with the **operator token** and write its own second-pass review into a doc for the owner.
⚠️ **The operator token is read-only by design**: the routine can read and recommend; it **cannot
approve, change or dismiss** — every write answers 403 `operator_read_only`. Deciding stays with
staff on the page or `/chat`. How to point a routine at it: [`../access/site.md`](../access/site.md).

## 8. Loop 2 — parked

Listening to how people talk **server-wide** (not only to the bot) and tagging intent from that.
Parked by the owner. It would need: a consent story wider than `/memory` (people who never spoke to
the bot), a channel allowlist (the channel-reach rule is the natural one), sampling and retention
limits, a per-day tagging budget separate from the reply fuses, and the same review queue with a
fifth reason. None of it is built.

## 9. Decisions made here (configurable both ways)

All are keys in `settings_store.py` (`REVIEW_SETTINGS`, `REVIEW_WORDS`), reachable from the Settings
page, the Chat page's foldouts and `/settings set-value`: `chat_review_mode` (on),
`chat_review_reask_seconds` (90, 0–3600), `chat_review_downvote_emoji` (👎, may be blank),
`chat_review_not_it_phrases`, `chat_review_ack_phrases` (both may be blank),
`chat_review_digest_hour` (9, 0–23). The tagging prompt is code (`TAG_SYSTEM`), not a key: it is
never posted, and a staff edit that broke the JSON shape would silently turn every tag into `none`.

**Deviations from the brief:** a 10-minute review tick instead of the 24-hour ingest tick (the ingest
tick cannot hit a 9 o'clock digest or tag promptly); extra columns `intent`, `suggested_intent`,
`suggested_section`, `suggested_why`, `tagged_at`; a fourth move, Reopen; an ack list as a key
rather than a constant.

## 10. Gate (measured on the branch, 2026-09-23)

- `ruff check .` — all checks passed.
- `pytest -q -n 16` — **7758 passed, 3 skipped** (at `3c40ef5d`).
- `node site/mock/check.mjs` against a mock started on port 8931 (checked free first) — *ok - 22
  pages, 216 routes, 25 core settings, all keys present*; `node site/mock/labels.test.mjs` ok.
- Headless Chrome against the mock, `chat.html#sect-review`, 1280 px and 400 px: 3 open cards, 3
  Approve buttons, the rail reads *Review queue: 3*, no console errors, no sideways scroll. The
  mock's `POST /api/chat/review/1/approve` added the phrase to `cookout_hours`, and
  `GET /api/chat/review.md` returned the document.

## 11. Not verified

- Nothing met **live Discord**: the follow-up and reaction listeners, the real `message.reply`
  return value, `on_raw_reaction_add` delivery (the default intents include reactions — not
  observed), the panel's selects and modals in a real client.
- Nothing met a **live model**: whether Groq's model answers in the shape, how often it says
  `none`, and what a tag costs (priced at $0 in `llm.PRICES` for the Groq models).
- The digest's real post in the log channel, and how noisy `reask` is in practice (§3).
- After v162 (16:2x): the route answers live with an empty queue, but no weak answer has been queued, no 👎 pressed, no follow-up
  tried (`RL-*`), no digest posted, and the Chat page's **Review queue** section not opened in a browser.
- A greeting never reaches this loop's model path: at 16:17 (under v161) the owner's *"whats good"* got the CANNED greeting-intent
  reply (`chat: answered … (greeting)`), so it cannot carry the tone or be queued as ungrounded; whether greetings should go through
  the model when the voice is not `cookout` is open (TODO ▸ 🔧 👋, owner undecided).
