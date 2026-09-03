# Requests, second pass — the state machine and the notifications

**Audience:** the builder carrying this (rides along in the Phase 17 build),
and the reviewer. **Status:** TRACKED · **BUILDABLE** — every decision below
is the owner's, taken 2026-09-02 20:19–20:42 while reviewing the first three
member requests. **Last verified: 2026-09-02** against `black_bloc/requests.py`,
`cogs/community/requests.py`, `api/tools/requests.py`,
`site/public/assets/page-requests.js` at `7295f61`. Supersedes the status
part of [`phase13-design.md`](phase13-design.md); everything else in Phase 13
stands.

## Why

Reviewing requests #1–#3 with the owner showed three gaps in one evening:
staff filings auto-approved themselves (the owner: "Even a staff request can
be bad"); there was no way to put a request on hold (the API refused
`pending` in words — staff moves were forward-only); and a finished request
DMs the requester but nothing is ever posted to a channel after filing.

## The machine (owner's words, then the table)

> "add a new status for open and then change pending to hold. so it goes from
> open -> planned -> in prog -> done with hold and declined as side states.
> Declined is a final state like done and hold can be anywhere in the process.
> we should also mark what state it was previously for my own sake." …
> "lets also get rid of planned since we'll hold or decline anything no need
> for planned." … "i agree we dont need to auto approve. Even a staff request
> can be bad"

```
open ──► in_progress ──► done      (final)
  │           │
  ├───────────┴──► hold            (reason REQUIRED; remembers held_from)
  └───────────┴──► declined        (final; reason REQUIRED; also from hold)
withdrawn = the requester's own final state (from open or hold)
```

| From \ To | in_progress | done | hold | declined | withdrawn |
|---|---|---|---|---|---|
| **open** | staff | — | staff | staff | requester |
| **in_progress** | — | staff | staff | staff | — |
| **hold** | staff ("resume", default = `held_from`) | — | — | staff | requester |
| done / declined / withdrawn | final — no moves | | | | |

Encode this as ONE data table (`TRANSITIONS: dict[str, frozenset[str]]`) in
`black_bloc/requests.py` and make every path — slash, web, tests — ask it.
A refused move says, in words, which moves are allowed from where it is.

**Retired:** `pending` (→ `open`), `approved`, `planned`, and the setting
`requests_auto_approve` (no approve step exists any more; every filing, staff
or member, arrives `open`). Remove the key from the registry, `labels.js`,
the mock server, the exact-key-set test, and `FILED_APPROVED` wording.

**New column:** `held_from TEXT NULL` — set on the move into `hold`, cleared
on the move out. Shown on the page as a badge on the hold card
("on hold — was: in progress") and in the requester's DM.

**Data migration (in schema 23, with the Phase 17 tables):**
`pending → open`, `approved → open`, `planned → open`; the rest unchanged.
Rows already `in_progress`/`done`/`declined`/`withdrawn` keep their status.

## Notifications — on EVERY staff move

Today: DM on approved/declined/done only (`DM_STATUSES`), channel post only
at filing (`NOTIFY_LINE` → `request_notify_channel_id`). Owner: "when a
request finishes can we message the channel and dm the person who made the
request saying its done" and "make sure we dm the person and post it chat
that we marked something as hold and why".

| Move | DM the requester | Channel line |
|---|---|---|
| → in_progress | "…is being worked on: {what}" | "Request **#{id}** from {who} is being worked on: {what}" |
| → hold | "…is on hold — {reason}\n\nIt was: {held_from}" | "Request **#{id}** from {who} is on hold — {reason}" |
| → done | "…is done: {what}" (exists) | "Request **#{id}** from {who} is done: {what}" |
| → declined | "…was declined — {reason}" (exists) | "Request **#{id}** from {who} was declined — {reason}" |
| filed | — | "New request **#{id}** from {who}: {what}" (exists) |

- Channel: **`request_status_channel_id`** (new key; blank = fall back to
  `request_notify_channel_id`, so one channel is the default). Template per
  move is fixed wording above; a single **`request_status_template`** key is
  NOT wanted — the four lines differ in shape. Keep them as constants next to
  `NOTIFY_LINE`.
- `request_dms_on_decision` stays the DM switch (rename its label to "DM the
  requester on every status change"; the key name stays — persisted keys are
  migrations to change).
- `AllowedMentions.none()` everywhere; guard-checked (`guard_allows`), a
  refused channel is logged `request.notify_skipped_test_mode`, not raised;
  a failed post logs `request.notify_failed` with the move in `details`.
- The staff `notes` field is NOT sent to the requester — `reason` is the
  public sentence, `notes` stays internal. (Owner wrote the hold reason for
  #3 as a note because no reason field existed yet; at landing, move #3 to
  `hold` with reason "youtube player is currently unreliable. Will do
  further research on this." so PT gets the DM.)

## Surfaces

- **Requests page** sections become **Open · In progress · On hold · Done ·
  Declined · Mine**; the status control offers only the moves the table
  allows from the row's state; `hold` and `declined` open the reason box;
  a hold card shows the `held_from` badge and a **Resume** button.
- **Slash:** `/request set` choices follow the table; `/request hold
  <id> <reason>` and `/request resume <id>` as explicit paths (both ways
  rule); `/request list` scopes `mine | open | all` (`pending` → `open`).
- **Mock contract:** update `contract.json` + `server.mjs` fixtures for the
  new statuses; `check.mjs` must stay green.
- **Logs:** kinds `request.in_progress`, `request.hold`, `request.resumed`
  join the existing `request.done`/`request.declined`; `logkinds.py` rows.

## Out of scope

A status history table (the audit log already carries `was:` on every move);
per-move templates; requester-side hold. Say so in the report if tempted.
