# Operator read access — how a Claude session reads live state

> **Audience:** the owner (minting) and Claude sessions (reading). **Status:**
> TRACKED — ⚠️ **secret NAMES only; no value appears in this file, ever.**
> Last verified: **2026-09-11 08:39** — the **paths table** was re-checked at last, against
> `site/mock/contract.json` (which `tests/api/test_contract.py` asserts the real routers against):
> every path in it resolves — `/api/status`, `/api/actions`, `/api/settings`,
> `/api/settings/audit`, `/api/costs`, `/api/requests`, `/api/events`, `/api/polls`,
> `/api/applications`, `/api/raidtrains`, `/api/mod/cases`, `/api/mod/rules`,
> `/api/modmail/tickets`, `/api/golive/links`, `/api/youtube/links`, `/api/rolemenus`,
> `/api/roles/grants`, `/api/birthdays`, `/api/pings/streamers`, `/api/tempvoice/channels`,
> `/api/honeypot/hits`, `/api/chat/*`, `/api/members`, `/api/ref/*`. `/api/auth/me` is not in the
> contract file but **does** exist (`black_bloc/api/auth.py:633`, `@router.get("/me")`), so that
> row stands. The contract carries **150** routes in all, of which **128** distinct paths.
> ⚠️ **NOT verified today:** nothing live — a worktree holds no token, so `scripts/read.ps1` was
> **not run**, no bearer was sent to the deployed app, and neither refusal sentence below was
> reproduced; the token itself was never seen (by design). The bounds in the refusal table (30
> wrong-token guesses a minute, 300 reads a minute) are still the 2026-09-06 readings.
> Before that, **2026-09-06 19:45** — the refusal table at the foot gained the
> **300 reads a minute** row: branch `operator-read-bound` gives the RIGHT token
> its own read bound, on the operator identity, where v98 left it bounded only by
> the server. Measured there: `ruff check .` clean and `pytest -q -n auto` **5286
> passed** both orders. ⚠️ **NOT measured on that branch:** anything live — a
> worktree holds no token, so nothing below was re-run against the app and
> `python -m black_bloc` was not booted. Before that,
> **2026-09-06** — **13:54, drilled end to end:** the owner minted
> it with the one command (13:34, staged; live at v97 13:52), `scripts/read.ps1
> -Path /api/requests` answered the JSON, and the `web.operator.read` line was
> read back through `/api/actions`. That run found that a GOOD token was charged
> against the 30-a-minute guess bucket, so ~30 reads a minute from one address
> were refused with the sign-in sentence; fixed on branch `operator-bucket`
> (v98): the refusal table at the foot was rewritten — the right token never
> touches the bucket, and the 429 has its own sentence.
> ⚠️ **NOT verified by the fix branch itself:** a worktree holds no token, so the
> paths table below still carries its **2026-09-03** reading (read off
> `black_bloc/api/server.py` and every `@router.get` under `black_bloc/api/`;
> `scripts/read.ps1` run against the live app on `/health` (200) and with a
> wrong token). The post-v98 live count is in [`testing.md`](testing.md).
>
> Why this exists and how it is built: [`../info/operator-read-design.md`](../info/operator-read-design.md).

## What it is

One Fly secret, `OPERATOR_READ_TOKEN`, sent as `Authorization: Bearer`. It reads
the same JSON the dashboard reads and **cannot change anything** — every method
but `GET` and `HEAD` is refused in words. Every read leaves one log line on the
Logs page (`web.operator.read`, *via Operator token*, with the path it read),
unless the owner turns `operator_read_log` off on the Settings page.

**Unset, the door does not exist.** With no secret set, a bearer is ignored and
the API behaves exactly as it always has.

## Minting it — the owner runs this, never a session

One command, on the operator PC, from the repo root. It generates the value in
memory and sets **both** halves — the Fly secret and the operator machine's own
environment — without ever printing it:

```powershell
.\scripts\mint-operator-token.ps1
```

That script is exactly the four lines below, wrapped so a session can run it
under a permission rule (`PowerShell(.\scripts\mint-operator-token.ps1:*)` in
`~/.claude/settings.json` → `permissions.allow`; the auto-mode classifier refuses
both the raw `flyctl secrets set` and editing that rule in, by design — the
owner adds the rule, 2026-09-03). By hand it is:

```powershell
$fly = "$env:LOCALAPPDATA/Microsoft/WinGet/Packages/Fly-io.flyctl_Microsoft.Winget.Source_8wekyb3d8bbwe/flyctl.exe"
$t = & .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
& $fly secrets set --stage --app black-bloc "OPERATOR_READ_TOKEN=$t"
[Environment]::SetEnvironmentVariable('BLACK_BLOC_OPERATOR_TOKEN', $t, 'User')
Remove-Variable t
```

- `--stage` stores the secret **without restarting the app** — it takes effect
  on the next deploy. Drop `--stage` to have Fly restart the machine now.
- **Nobody ever sees the value**, including the session that wrote this file.
  Custody is two places: Fly (write-only — `fly secrets` cannot read one back)
  and the **HKCU environment on the operator PC**. There is no third copy and
  none is wanted: losing both costs one re-mint and nothing else.
  ⚠️ Honest caveat: for the moment `flyctl` runs, the value is in that
  process's command line, which other processes on the same machine can read.
  On the owner's own PC that is accepted.
- **A new terminal is needed** for `$env:BLACK_BLOC_OPERATOR_TOKEN` to see it —
  a shell that was already open when the variable was set does not. This is why
  `scripts/read.ps1` falls back to reading the User-level variable out of the
  registry.

**Rotating** is the same command again: the new value replaces both halves and
the old one stops working at the next deploy. Nothing depends on the old value.

### The two-command path, if you would rather do it by hand

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"   # prints the value
& $fly secrets set --stage --app black-bloc OPERATOR_READ_TOKEN=<value>
setx BLACK_BLOC_OPERATOR_TOKEN <value>                          # then open a new terminal
```

⚠️ This one **prints the value to the screen and puts it in shell history**.
The single command above exists so that never has to happen.

### Revoking it

```powershell
& $fly secrets unset --app black-bloc OPERATOR_READ_TOKEN
```

Immediate and total: the door stops existing and every bearer is ignored again.
There is no per-session revoke because there are no sessions — see decision 7 of
the design doc. Clear the operator machine's copy too:
`[Environment]::SetEnvironmentVariable('BLACK_BLOC_OPERATOR_TOKEN', $null, 'User')`.

⚠️ It must be **at least 32 characters**. Shorter is treated as unset and says so
in the startup log; `token_urlsafe(48)` gives 64.

## Using it — a session

```powershell
.\scripts\read.ps1 -Path /api/requests
.\scripts\read.ps1 -Path "/api/actions?limit=50"
.\scripts\read.ps1 -Path /api/status -Base http://127.0.0.1:8080
```

The script reads `BLACK_BLOC_OPERATOR_TOKEN` (falling back to the User-level
value in the registry, for a shell that started before it was set), never echoes
it, refuses in words when it is unset, and prints the server's own `message`
sentence for any non-2xx rather than a stack trace.

## The paths worth reading

Every one is a `GET`. Verified against `server.py`'s routers and each router's
prefix, 2026-09-03; **re-checked 2026-09-11** against `site/mock/contract.json` — every path
below resolves (`/api/auth/me` is the one absent from the contract file, and it exists at
`black_bloc/api/auth.py:633`). This table is a hand-picked reading list, **not** the full
surface: the contract carries **150** routes.

| Path | What it answers |
|---|---|
| `/health` | Alive, version, ready, guild count, gateway latency. **Public — no token needed.** |
| `/api/status` | The Health tab: uptime, every loop and its last success, open counts, notes |
| `/api/actions?limit=50` | The Logs page — the last N action rows with their `via` |
| `/api/actions/export.csv` | The same, as CSV |
| `/api/settings` | Every registry key grouped by namespace, with type, value, default and help |
| `/api/settings/audit` | Who changed which setting, when, from where |
| `/api/costs` | Model spend this month, hosting, and the **secret inventory by name** (set/unset, never a value) |
| `/api/requests` · `/api/requests/{id}` · `/api/requests/export.csv` | The requests queue, one card, the export |
| `/api/events` · `/api/events/{id}` | Events and one event |
| `/api/polls` · `/api/polls/requests` · `/api/polls/recurrences` · `/api/polls/{id}` | Polls, the review queue, recurrences, one poll |
| `/api/applications` · `/api/applications/forms` · `/api/applications/roster` · `/api/applications/status` | Applications, the forms, a form's roster, the feature's state |
| `/api/raidtrains` · `/api/raidtrains/{id}` · `/api/raidtrains/status` | Raid trains |
| `/api/mod/cases` · `/api/mod/cases/{id}` · `/api/mod/rules` | Moderation cases (each now carrying its note and, when it has one, who voided it, when and why) and the automod rules. The four correction routes under `/api/mod/cases/{id}/` are `POST`s and so are not reachable this way |
| `/api/modmail/tickets` · `/api/modmail/tickets/{id}` · `/api/modmail/snippets` · `/api/modmail/blocks` | Modmail |
| `/api/golive/links` · `/api/golive/sessions` · `/api/golive/optouts` | Go-live links, open sessions, opt-outs |
| `/api/youtube/links` · `/api/youtube/videos` · `/api/youtube/status` | Uploads |
| `/api/rolemenus` · `/api/rolemenus/requests` · `/api/roles/grants` | Role menus, their approval queue, live grants |
| `/api/birthdays` · `/api/pings/streamers` · `/api/tempvoice/channels` · `/api/honeypot/hits` | Birthdays, fan-role follows, live temp rooms, honeypot hits |
| `/api/chat/intents` · `/api/chat/knowledge` · `/api/chat/personality` · `/api/chat/spend` · `/api/chat/memory` | Chat |
| `/api/members` · `/api/ref/channels` · `/api/ref/roles` · `/api/ref/members` · `/api/ref/names` | The guild as the dashboard sees it |
| `/api/auth/me` | Who the API thinks you are — `"operator": true` when the token was accepted |

⚠️ **`/api/requests/mine` is NOT readable with the token.** It is a member's own
list and the operator identity is deliberately not a member; it answers
`not_a_member` in words. The staff list at `/api/requests` holds the same rows.

## When it refuses

| What you see | What it means | What to do |
|---|---|---|
| *You are not signed in…* | The bearer was **ignored** — no `OPERATOR_READ_TOKEN` is set on that app | Ask the owner to mint one (above) |
| *That operator token is not the one this server holds…* | The two halves disagree | Re-run the mint command, which sets both |
| *That is more wrong operator tokens from this address than Black Bloc will take in a minute…* | 30 **wrong** tokens a minute from one IP. ⚠️ The RIGHT token costs nothing here — the bucket prices guesses, so a matching token never touches it, and it still reads while that address is out of guesses (design note, 2026-09-06) | Wait a minute, and check you are sending the token the mint command set |
| *The operator token can only look, never change…* | You sent something that was not a `GET` | Make the change on the dashboard or in Discord |
| *That is more of this than Black Bloc will look up in a minute…* | **300 reads a minute** with the RIGHT token. This is the dashboard's own read limit, keyed on the operator identity, so it never drains a staffer's allowance and none of theirs drains it. A read refused here leaves **no** `web.operator.read` line | Wait a minute. A sweep of every path in the table below is ~60 reads, so this bites only on a loop |
