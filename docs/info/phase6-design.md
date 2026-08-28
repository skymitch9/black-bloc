# Phase 6 design — moderation (F7), shadow beside Carl-bot

> **Audience:** the Phase 6 build agent and the reviewer. **Status:** LOCAL
> ONLY. **Last verified: 2026-08-26** — Carl's live config from the owner's
> `!am` dump (`archive/current-bots/carl-bot-dashboard-2026-08-26.md`);
> modlog history (`#carlbot-logs`, 7 cases in ~2 years) from the scan. Depends
> on Phase 1 (settings, action log, staff derivation).

## Owner decisions this implements

- **"Follow what exists"** — reproduce Carl's armed behaviour as-is; tune in
  shadow; change later. Exceptions list (exempt roles/channels) fine-tuned
  later.
- Rollout: **shadow → watch → on**; Carl stays on until parity is measured.
- No Muted role exists; the server uses **native timeouts**.

## Carl's live config, translated

| Rule | Carl setting | Black Bloc v1 |
|---|---|---|
| Mention spam | 5 mentions / 30 s → delete, warn, tempmute 5 min | `mention_spam`: 5 unique user/role mentions in a rolling 30 s window per user → delete offending message(s), warn, **timeout 5 min** |
| Slowmode / linkspam / attachment / caps / bad words / invites | logged or off, no punishment | Implemented as rule types with `punishment: none` — present in the settings so the owner can arm them later; **disabled by default** except the two Carl logs (`slowmode` 6/4s, `linkspam` 1/1s) which log only |
| Warn threshold | 8 warnings, no punishment | `warn_threshold`: 8 → log only |
| Immune | admins / manage server | + staff roles + `automod_exempt_role_ids` + `automod_exempt_channel_ids` |

## Shape

```
black_bloc/
├── automod.py                   ← pure rule engine: RuleConfig, sliding-window counters, evaluate(message_facts) → Verdict
└── cogs/moderation/
    ├── automod.py               ← on_message → facts → engine → act/log per mode
    └── modcmds.py               ← /warn /timeout /untimeout /kick /ban /unban /purge /case /cases
tests/ test_automod.py · cogs/moderation/test_automod.py · cogs/moderation/test_modcmds.py
```

Schema v7 (additive):

```sql
CREATE TABLE IF NOT EXISTS mod_cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
    kind TEXT NOT NULL,                 -- warn | timeout | untimeout | kick | ban | unban | purge | automod
    moderator_id INTEGER,               -- NULL for automod
    reason TEXT, duration_s INTEGER, at TEXT NOT NULL,
    mode TEXT NOT NULL, applied INTEGER NOT NULL,   -- applied=0 in shadow (would-do)
    log_message_id INTEGER
);
```

Settings keys: `automod_mode` (`off|shadow|on`, default **`shadow`**),
`automod_rules` (JSON object keyed by rule name: `{enabled, window_s,
threshold, actions:[delete|warn|timeout], timeout_s}` — defaults = the table
above), `automod_exempt_role_ids`, `automod_exempt_channel_ids`,
`modlog_channel_id` (default = `log_channel_id`), `mod_dm_on_action` (enum
matching Carl's options: `none | server_action | server_action_reason`,
default `server_action_reason`).

## Engine

`evaluate(facts: MessageFacts, state: WindowState, rules) -> list[Verdict]`
— pure; `MessageFacts` = author id, channel id, mention ids, link count,
attachment count, caps ratio, has_invite, created_at. Sliding windows are
per (rule, user) deques of timestamps kept in memory (reset on restart —
acceptable; state the choice in code-notes). Each `Verdict` = rule name,
actions, human sentence ("5 mentions in 30s").

## Acting, per mode

- `shadow`: **no delete, no warn, no timeout** — one modlog embed per
  verdict, `mod_cases.applied=0`, kind `automod`, with a **"Apply now"**
  staff button (watch-mode affordance) that performs the actions on click.
- `on`: delete the triggering message(s), DM the user per `mod_dm_on_action`,
  apply the timeout via `member.timeout(timedelta)`, write the case,
  modlog embed, `log_action`.
- Exempt authors (bots, staff, exempt roles, `manage_guild`) and exempt
  channels never reach the engine; the honeypot channel is excluded too.

## Commands (staff only; every one writes a `mod_cases` row + modlog embed)

`/warn @user <reason>` · `/timeout @user <duration> <reason>` (durations
`10m`, `2h`, `1d`; Discord max 28 d) · `/untimeout` · `/kick` · `/ban
[purge_days] <reason>` · `/unban <user id>` · `/purge <n> [@user]` · `/case
<id>` · `/cases @user` (paginated) · `/automod status|mode|rule <name>
enable|disable|set …|exempt add|remove`. While `TEST_MODE`, the destructive
ones (timeout/kick/ban/purge) are **refused with the test-mode sentence
unless the target is in the test channel's member set and the invoker is
staff** — simpler: **refused outright while TEST_MODE, logged as
would-do** (the guard cannot see them). `/warn` is allowed (it only writes
a row + DM).

## Parity measurement (the cut-over criterion)

`/automod parity [days]` (staff): lists shadow verdicts in the window and
the Carl-bot modlog entries in `#carlbot-logs` for the same window (read via
history, matched by user + ±2 min), and reports agree / Carl-only /
Bloc-only. The owner flips `automod_mode on` and turns Carl's automod off
only when Bloc-only and Carl-only are both zero over a week — the number
the rollout rule asks for.

## Tests (offline)

`test_automod.py`: window arithmetic (exactly 5 in 30 s fires, 5 in 31 s
does not, unique mentions counted once), each rule's facts extraction,
exemptions; `cogs/moderation/test_automod.py`: mode matrix → which side
effects are called on a fake member/channel; `test_modcmds.py`: duration
parsing, case numbering, test-mode refusals.

## Definition of done

As before; three commits (engine → automod cog → mod commands), not pushed.
Owner's test sweep: `/warn` a throwaway in the test channel, spam 5
mentions there and read the shadow verdict, `/automod parity 7` (expect
Carl-only = the real cases, Bloc-only = 0 since the shadow only sees the
test channel until `TEST_MODE` lifts).
