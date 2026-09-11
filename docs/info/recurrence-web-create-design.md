# Create a recurring poll from the website — design

> **Audience:** the build agent and reviewers. **Status:** TRACKED, ✅ **LIVE as v96** — branch
> `recur-web`, merge **`c915ade`**, deployed **2026-09-06 11:39** Phoenix (`../deploys.log`); it
> shipped in the same release as the Logs buttons
> ([`logs-buttons-design.md`](logs-buttons-design.md)), landing entry in
> [`../DONE.md`](../DONE.md). The owner's by-eye rows are **310–314** in
> [`../access/sweeps.md`](../access/sweeps.md) (lettered `RW-a`–`RW-e` here; renumbered at the merge).
> Owner decision
> **2026-09-06 11:00**, verbatim: *"2. A"* — answering "the dashboard has no create-recurrence route:
> (a) add a dashboard form, or (b) Discord-only". The Polls page can already see, pause, resume and
> delete recurrences; it can now also **make** one, the way Discord's `/poll` recurrence step does.
>
> **Last verified: 2026-09-11 08:33** (the header; the body is as at the build). Measured this pass
> against `main` at `f3ae743` (v108 live): `api/tools/polls.py` carries `@router.post("/recurrences")`
> beside the pause / resume / delete routes, plus `_asked_for`, `RECUR_CREATED_SAID`,
> `_refuse_outside_the_test_channel_id` and `Refused(400, "not_a_recurrence", RECUR_NOT_A_DATE)`;
> `black_bloc/polls.py` still owns `cadence_token`, `next_occurrence`, `describe_cadence`,
> `RECUR_SAVED` and `RECUR_NOT_A_DATE`; `site/public/assets/page-polls.js` posts to
> `/api/polls/recurrences` and its `NO_RECUR` line names the Create-a-poll form; there is still **no
> `poll_recurring` key** in `settings_store.py`. `site/mock/contract.json` reads **150 routes, 17
> pages, 14 core settings** (counted from the file — the live `check.mjs` needs the mock server up,
> which was not started this pass). ⚠️ **NOT checked this pass:** anything in Discord or a browser —
> no recurrence was created, no page was opened, the bot was not booted. Before that, **2026-09-06
> 11:05** — every `path:name` below was read in the tree at `c29b007` (v94 code, merge `8405bea`).

## 1. What exists

- **Discord:** `cogs/community/polls.py:post_the_draft` (the `Post it` path) calls `store_poll(…,
  status=RECURRING if draft.repeating else None)` and then `save_recurrence(bot, guild, row, token,
  at_local, tz_name, actor, via=…)` — `cogs/community/polls.py:save_recurrence` — which computes
  `next_occurrence`, `set_recurrence`, and writes ONE `poll.recur_created` log row (`kind_via`).
  The cadence token comes from `polls.cadence_token(cadence, day)`; `polls.next_occurrence(token,
  at_local, tz_name)` returns `None` for anything unreadable; `polls.describe_cadence` phrases it.
- **API:** `api/tools/polls.py` — `POST /api/polls` (`poll_create`) builds a `poll_plan`, refuses in
  words (`Refused(400, …)`), refuses a channel outside the test channel
  (`_refuse_outside_the_test_channel_id`), then `store_poll(…, via=VIA_WEBSITE)`. `GET
  /api/polls/recurrences` returns `recurrence_row(guild, row, options)`; pause/resume and delete
  routes call the cog's `pause_recurrence` / `resume_recurrence` / `delete_recurrence` with
  `actor_for(bot, who, guild)` and `via=VIA_WEBSITE`. The router carries `staff_dependency`.
- **Site:** `site/public/assets/page-polls.js:createForm` posts `/api/polls`;
  `recurringSection` lists recurrences with pause/delete. The mock (`site/mock/server.mjs`) and
  `site/mock/contract.json` describe **149 routes** (that was the count before this build; it is
  **150** from v96 onwards, and still 150 at v108 — this route is the one that was added).

## 2. Rules

1. **One creation path.** The new route reuses `poll_plan` → `store_poll(status=RECURRING)` →
   `save_recurrence(via=VIA_WEBSITE)`. No second implementation of the cadence maths, no second
   log kind: the row is the existing `poll.recur_created` with `via: website`.
2. **Validate the cadence BEFORE the poll row exists.** `next_occurrence(token, at, tz)` is called
   first; `None` → `Refused(400, "not_a_recurrence", <sentence>)` and nothing is written. (The cog
   validates in `draft_plan`; the route must not leave an orphan `RECURRING` row.)
3. **Same gates as Discord.** Whatever key gates the Discord recurrence step (read the cog: if
   `poll_recurring`/similar exists it gates the route too; if only `polls_are_on` gates it, so here),
   the same test-channel refusal, the same review-channel rule if recurrences can be held for review
   (read `save_recurrence` callers — a recurrence is a TEMPLATE; it does not go for review, the polls
   it opens do, so the route returns the template, not a posted poll).
4. **Refusals are sentences** (`Refused(status, code, sentence)`), never a bare status; the page
   shows the sentence in the form's notice line like `createForm` already does.
5. **Configurable both ways (checklist 33):** no NEW decision is made here — the route honours the
   existing `poll_*` keys. If the build finds it must decide something (a default tz for the form,
   say), it is a registry key with a label, not a constant.

## 3. The route

`POST /api/polls/recurrences` — body = the `POST /api/polls` body (`question`, `kind`, `options`,
`hours`, `anonymous`, `results`, `channel_id`, `ping_role_id`, `auto_thread`) plus `cadence`
(`daily` / `weekly` / `monthly`), `day` (weekday name for weekly, 1–28 for monthly, ignored for
daily), `at` (`HH:MM`), `tz` (IANA name; default `timezones.DEFAULT_TZ`). Response
`{"recurrence": recurrence_row(...), "message": RECUR_SAVED-style sentence}` — the same shape the
pause route returns. Add the route to `site/mock/contract.json` (`read_by`: the page's create form)
and to `site/mock/server.mjs`; the check must then say **17 pages / 150 routes** with the core
settings count unchanged.

## 4. The page

`createForm` gains a **Repeat** block: a cadence select (`Doesn't repeat` / `Every day` / `Every week`
/ `Every month`), then — only when repeating — the day control (weekday select or a 1–28 number), a
time field and a tz field. When repeating, submit goes to `/api/polls/recurrences`, the notice says
the returned message, the recurring section is refreshed (`sayAgain('recurring', …)` pattern) and
the form resets. Labels for any new field follow the page's existing style. No new page.

## 5. Tests (mirror the package)

`tests/api/tools/test_polls.py`: creates a weekly recurrence → one `polls` row with status
`RECURRING`, `recur_next_at` set, ONE `poll.recur_created` log row with `via: website`; bad cadence
→ 400 in words and ZERO poll rows; outside the test channel → the existing refusal; not staff →
the existing staff refusal. `tests/api/test_contract.py` stays green with the route added.
Mock: `node site/mock/check.mjs` → `ok - 17 pages, 150 routes, N core settings`.

## 6. Prove before merge, and the sweep rows

`ruff` clean; full suite `-n auto` forward and `BB_REVERSE=1`; mock check; `python -m black_bloc`
NOT booted in a worktree — say so. Sweep rows lettered `RW-a…` in `docs/access/sweeps.md`
(**renumbered 310–314 at the merge**): create
a weekly recurrence from https://blackbloc.heygabi.ai/polls.html and see it in the recurring list
with the right next-run; a bad time refused in a sentence; Discord's `/poll` panel shows the same
recurrence with its stop-repeating card. Code notes: `# Recurrence create, website` at the foot of
`code-notes.md`, keyed by name. Add a `## Deviations` section to this file for anything that
differed, and why.

## Deviations

Built on branch `recur-web` off `main` at `b428236`, in a worktree at `C:/lcw/bb-recur-web`,
2026-09-06. **Status: ✅ LIVE v96 — merged `c915ade`, deployed 2026-09-06 11:39.**
The design was followed as written; these are the places the build made a call it
did not spell out, plus one thing it got wrong.

1. **§3's "same gates" resolved to `poll_mode` + staff — there is no recurrence key.** The
   question §3 left open has an answer in the cog: `post_the_draft` checks `polls_are_on`
   (`poll_mode != "off"`), then `may_create`, then `store.is_staff` for the repeating half.
   `settings_store.py` has no `poll_recurring`. The router's `staff_dependency` already
   covers the staff half (and `may_create` with it), so the route adds exactly one gate:
   `409 polls_off` carrying the cog's own `POLLS_OFF`, in the shape `api/tools/rolemenus.py`
   uses for `ROLE_MENUS_OFF`. **Since v97** the one-off `POST /api/polls` got the same gate — it was
   deliberately left alone here and reported as a finding, then closed by the loop-guard build
   ([`loop-guard-design.md`](loop-guard-design.md) §2.4). `api/tools/polls.py` now raises
   `Refused(409, "polls_off", POLLS_OFF)` at **both** creation routes.
2. **A gate the design did not name: a DATE poll cannot recur.** `CadenceModal.on_submit`
   refuses one with `polls.RECUR_NOT_A_DATE`, so the route does too (400, before any row),
   and the page hides the whole Repeat block for that kind rather than offering a control
   that will be refused.
3. **The success sentence is the route's own constant, not `polls.RECUR_SAVED`.** §3 asked
   for a "`RECUR_SAVED`-style sentence"; the literal constant ends in `<t:{when}:R>`, Discord
   timestamp markup that renders as raw text in a browser. `RECUR_CREATED_SAID` keeps the
   shared `describe_cadence` wording and points at the Repeating section, which already
   prints the real next-run time.
4. **The timezone field defaults by being BLANK.** §3 says "default `timezones.DEFAULT_TZ`".
   The page sends `tz` only when somebody types one, so the default stays in
   `black_bloc/timezones.py` rather than being copied into a JS file. Rule 5 asked whether a
   default tz should become a registry key: no new decision was made, so it is not one.
5. **`poll_create` was refactored, not just added beside.** The body-reading both routes
   share is now `_asked_for(guild, payload)` — a pure extraction with no behaviour change,
   so there is one spelling of "where does this poll go".
6. **The success message lands on the Repeating section, not the create form.**
   `keepSaying('recurring', …)`, which §4's "`sayAgain('recurring', …)` pattern" points at:
   after the refresh the sentence sits beside the row it made. The form clears its question
   and returns to *Doesn't repeat*.
7. **`NO_RECUR` on the page was rewritten.** It told people the only way to start a
   recurrence was Discord's `/poll` panel, which this change made untrue.
8. **The mock does not reimplement `next_occurrence`.** It mirrors `cadence_token` and the
   refusals a person can see, and sets `next_at` to `daysAhead(1)` — the same simplification
   the resume half of the pause route already makes. The arithmetic has one home.

**Not verified:** live Discord, the live dashboard, and a real boot — `python -m black_bloc`
was NOT run (no token in a worktree), so no recurrence made here has ever opened a poll and
the sweep loop (`run_due_polls`) was not exercised against a website-made row. The page half
WAS driven in a real browser against the mock.
