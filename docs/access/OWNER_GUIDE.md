# Owner guide — before the trip, on the road, when you're back

> **Audience:** you (the owner), on your phone or the laptop. **Status:** TRACKED (owner, 2026-08-31 —
> permanently, not temporarily; secret NAMES only).
> Last verified: **2026-08-27 20:22** — commands were run from the main machine this week; the laptop steps
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
| See what it has been doing | https://blackbloc.heygabi.ai → **Logs** (every feature page has its own Logs section too; `/golive logs` etc. in Discord) |
| See the team's requests | https://blackbloc.heygabi.ai/requests.html — members file with `/request create` in Discord or sign in and file on that page (they see only Requests) |
| Test something | [`sweeps.md`](sweeps.md) — 32 rows in priority order, each with what to expect (+ the detailed phase 1–8a scripts) |
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
