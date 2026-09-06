# Create a recurring poll from the website — design

> **Audience:** the build agent and reviewers. **Status:** TRACKED. Last verified: **2026-09-06 11:05** —
> every `path:name` below was read in the tree at `c29b007` (v94 code, merge `8405bea`). Owner decision
> **2026-09-06 11:00**, verbatim: *"2. A"* — answering "the dashboard has no create-recurrence route:
> (a) add a dashboard form, or (b) Discord-only". The Polls page can already see, pause, resume and
> delete recurrences; it can now also **make** one, the way Discord's `/poll` recurrence step does.

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
  `site/mock/contract.json` describe **149 routes**.

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
NOT booted in a worktree — say so. Sweep rows lettered `RW-a…` in `docs/access/sweeps.md`: create
a weekly recurrence from https://blackbloc.heygabi.ai/polls.html and see it in the recurring list
with the right next-run; a bad time refused in a sentence; Discord's `/poll` panel shows the same
recurrence with its stop-repeating card. Code notes: `# Recurrence create, website` at the foot of
`code-notes.md`, keyed by name. Add a `## Deviations` section to this file for anything that
differed, and why.
