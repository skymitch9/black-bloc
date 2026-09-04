# Owner guide — before the trip, on the road, when you're back

> **Audience:** you (the owner), on your phone or the laptop. **Status:** TRACKED (owner, 2026-08-31 —
> permanently, not temporarily; secret NAMES only).
> Last verified: **2026-09-03** for the APPLICATIONS row (`/apply` is ONE command that opens a
> panel; both the `apply` and `applications` groups and their seventeen subcommands are gone;
> live in v66 since 15:00; not run against Discord by eye) and the sweeps
> count (**95** rows, numbered to 102). Same day, the POLLS row (`/poll` is one command that opens
> a panel — live in v65 14:14; not run by eye), the EVENTS row (`/event` is one command that opens a panel and
> `/timezone` is gone — live in v64 since 14:05; not run against Discord by eye) and
> the birthdays row (`/birthday` is ONE command that opens a panel — live in v63). Before that the same day, for the applications row
> (a form may keep a LIST instead of handing a
> role over — live in v62 since 12:48) and the sweeps count
> (69 rows, numbered to 72; 66–68 belong to the sibling requests-check build). Before that the same
> day, for the requests row only — the `/request` panel no longer writes a
> member's own requests out (`request_panel_own_list`, off by default), and the sweeps count was
> re-counted against [`sweeps.md`](sweeps.md) (**68**, was 65 this morning and 42 before that; rows
> 66–68 are the sixth pass, built on `feat/requests-check` and not yet merged).
> ⚠️ Not run against live Discord. Before that,
> **2026-08-27 20:22** — commands were run from the main machine that week; the laptop steps
> are the same tools on a fresh clone and have NOT been rehearsed on your laptop.
> Details live in [`runbook.md`](runbook.md) (operations) and [`sweeps.md`](sweeps.md) (what to test); this
> page is the order to do things in.

## 1. Before you leave (main machine, ~5 minutes)

1. **Encrypt `.env` so the laptop can have it** — in a **Git Bash** terminal (VS Code: Terminal ▸ the ▾ next
   to `+` ▸ Git Bash; or right-click the `black_bot_baf` folder ▸ *Git Bash Here*). The prompt should end in
   `black_bot_baf`.
   ```
   sh scripts/env-lock.sh
   ```
   Type a passphrase (nothing shows), Enter, type it again. Put the passphrase in your password manager —
   there is no recovery. It prints `wrote .env.enc`.
2. **Commit only the encrypted file:**
   ```
   git add .env.enc
   git commit -m "Encrypted env"
   git push
   ```
   Never run `sh scripts/env-lock.sh` through Claude — it must never see the values.
3. **Leave this Claude Code window open** if you want the Sunday 16:05 wake-up to fire (it lives in the
   session). The laptop can sleep and reconnect; the window on this machine must stay open. If you close it,
   nothing breaks — Sunday's work simply starts when you next open a session and say "continue".
4. Optional: give the **Bots** role *View Audit Log* (so hand-made role changes name who did them) and
   *Send Messages* in voice channels (so temp-voice panels can post) — two clicks in Server Settings ▸ Roles.

## 2. On the laptop (once, ~10 minutes)

1. Install **Git for Windows** (gitforwindows.org) — gives you Git Bash and OpenSSL.
2. In Git Bash:
   ```
   git clone https://github.com/skymitch9/black-bloc.git
   cd black-bloc
   sh scripts/env-unlock.sh
   ```
   Enter the passphrase → `wrote .env`. (Only needed to run the bot locally; skip if you'll only deploy.)
3. Only if you want to deploy from the laptop: `winget install --id Fly-io.flyctl`, open a **new** terminal,
   `flyctl auth login` (browser), then follow **Deploy** in [`runbook.md`](runbook.md). Python/Node only
   if you want to run tests or the mock: `python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"`.

## 3. On the road — what to look at (phone is fine)

| Want to… | Go to |
|---|---|
| See if the bot is up | https://blackbloc.heygabi.ai/health (should say `"ok":true,"ready":true`) |
| See what it has been doing | https://blackbloc.heygabi.ai → **Logs** (every feature page has its own Logs section too; every feature panel has a **Logs** button in Discord) |
| See the team's requests | https://blackbloc.heygabi.ai/requests.html — members file with `/request` in Discord (opens a panel — **File a request**) or sign in and file on that page (they see only Requests). ⚠️ The panel's **list** of requests is staff-only: a member sees File a request, Refresh, the site link and a **Take one back…** select, but not their own requests written out. Set `request_panel_own_list` to `true` (Settings page or `/settings set-value`) to give members their list back |
| Store a birthday, or see whose is coming up | `/birthday` in Discord — ONE command that opens a panel. **Set my birthday** is a modal (`MM-DD`, or `MM-DD-YYYY` if you want the year); **Remove**, **Opt out** / **Opt in** and **Refresh** are buttons, and **Look someone up…** shows anybody's stored date. Staff get three more rows on the same panel: a month list, a **Wishes are…** off/shadow/on picker, **Status**, **Clear the birthday role** and **Logs** — and, on somebody's card, **Set their birthday** and **Forget their birthday** (they are DMed when staff forget it). Two switches decide what members see: `birthday_panel_next_for_members` and `birthday_panel_lookup`, both **on** — Settings page or `/settings set-value`. The old `/birthday set` / `show` / `next` / `list` / `mode` / `status` subcommands are gone |
| Run a poll, or decide one waiting on review | `/poll` in Discord — **one** command that opens a panel. **Create** is a two-step modal (question, `A \| B \| C` options, hours, kind) then a preview with **Post it · Repeat… · Start over · Cancel**; nothing is written until Post it. Pick a running poll on the select to see results, **End** (creator or staff) or **Cancel** (staff). With review on, staff **Approve** / **Deny** from the panel — and a denied poll still has **Post it anyway**. Site: https://blackbloc.heygabi.ai/polls.html |
| Test something | [`sweeps.md`](sweeps.md) — 112 rows in priority order, each with what to expect (+ the detailed phase 1–8a scripts) |
| Link your Twitch, or stop your streams being announced | `/golive` in Discord — **one** command that opens a panel. Members get **Link my Twitch channel** (a one-line modal; **Change my channel** afterwards, prefilled), **Unlink**, and **Stop announcing my streams** / **Announce my streams again** — exactly one of the pair is ever drawn. Staff get the whole of the old `/golive status` written into the same embed (mode, stream end, channel, cooldown, twitch polling, last good poll, last poll error, the counts, and who is live right now) plus **Logs**, **Streamers…** (unlink or opt out somebody else, the same as the Go-live page does it), **Preview an announcement…** (ephemeral, never pings, never posts) and an **off / shadow / on** select. ⚠️ `/twitch link`, `/twitch unlink`, `/golive optout`, `/golive optin`, `/golive status`, `/golive mode`, `/golive test` and `/golive logs` are all **gone** (2026-09-03) — every one of them is a button now. `golive_panel_minutes` (10) decides how long the panel stays live. ⚠️ **In test mode the panel SAYS so**: if `golive_channel_id` is not `#mute-me-bot-test-spam`, the channel line tells you that is why nothing real is posted |
| Put an event on, or decide one | `/event` in Discord — **one** command that opens a panel. Members get **Propose an event** (the same form as before), **My time zone** and, once they have one on the go, **Call one off…**. Staff get the counts, the open list, **Pick an event…** → Approve / Deny / Call it off, plus **Settings** and **Logs**. ⚠️ `/event create`, `/event list`, `/event cancel`, `/event settings`, `/event logs` and the whole `/timezone` group are **gone** (2026-09-03) — everything they did is a button. The panel's **list** of your own events is staff-only; set `event_panel_own_list` to `true` to give members theirs back, and `event_panel_minutes` decides how long the panel stays live (10 by default) |
| Apply for something, or run the forms | `/apply` in Discord — **one** command that opens a panel. Members get **Apply for…** (the same form modal as before), their own applications written out, and **Take one back…**. Staff get **Pick an application…** → Approve / Deny, **A form…** → the form card (**Edit… · Questions… · Close it/Open it · Post the Apply button · Roster · Fill it in · Delete**), plus **New form**, **Find #…** (any application by number, settled ones included), **Settings** and **Logs**. ⚠️ The whole `/applications` group and `/apply start` / `status` / `withdraw` are **gone** (2026-09-03) — everything they did is a button. With `applications_mode` **off** the command still opens and says so in words; `applications_panel_own_list` (**on**) decides whether members see their own applications, and `applications_panel_minutes` (10) how long the panel stays live |
| Keep a list of people instead of handing a role out | https://blackbloc.heygabi.ai/rolemenus.html#applications → **Applications**. A form's role is now optional: leave **Role it hands over** on **No role — keep a list** and an approval stores the record, DMs the person and gives nothing. Each form gets an **Approved for …** foldout — everyone who was said yes to, their Twitch login where they have linked one, and **Copy as text** for pasting into the official team page. Staff take somebody off with the roster's **Take off the list**, or in Discord with `/apply` → **A form…** → **Roster** → **Take somebody off…**; they are DMed the reason. A form that DOES hand a role over keeps `/role revoke` as the way off, and staff can put a denied or removed application back with **Approve after all** / **Put them back on the list** |
| Turn a feature on/off | Dashboard → that feature's page → the ON / SHADOW / OFF switch (or **Settings**) |
| Quiet the Discord log channel | Settings → `<feature>_log_level` (off / important / all) |

Everything still runs in **test mode** (only `#mute-me-bot-test-spam`, DMs, and the temp-voice channels it
made). Lifting it is a Fly secret (`TEST_MODE=false`) — your call, never Claude's.

## 4. If something looks wrong

1. Screenshot it, note the time (Phoenix).
2. Check [`runbook.md` ▸ Common failures](runbook.md) — most things there are "expected in test mode".
3. Paste the screenshot + time to Claude when you're back; the Fly logs around that minute + the Logs page
   are enough to diagnose. Nothing on the sweeps list is destructive.
4. Genuine outage (health page dead for more than a minute): in a terminal with flyctl,
   `flyctl machine restart 85e744c4d959d8 --app black-bloc`.

## 5. When you're back (Sunday night)

1. Open the Claude Code session (or a new one — it reads `docs/` first) and say **continue**. It will show
   you what landed while you were gone (`docs/TODO.md` top entries, `docs/DONE.md`, `docs/deploys.log`).
2. Decide one thing: **keep `docs/` tracked in git, or purge it from history again** (it was made public
   to the private repo only for this trip).
3. Work the [`sweeps.md`](sweeps.md) list top-down; tell Claude each result.
4. The Requests page is your backlog — approve / plan / assign from there.
