# archive/

> **Status:** TRACKED (owner, 2026-08-31 — was local-only until then).
> Last verified: **2026-08-31** — the table below was checked against the files
> actually present (`archive/current-bots/` holds **5**; three were missing from
> this index and are added). ⚠️ **NOT checked:** the contents of any dump — they
> are dated captures and are not re-verified. No doc in `archive/` currently
> carries a retirement banner because nothing has been retired here yet; only
> `current-bots/` data dumps live in this folder.

Superseded docs and one-off data dumps. `current-bots/` holds exports from
the bots Black Bloc replaces (source data for imports). A doc retired
here gets a dated banner at the top naming what replaced it — see
[`../DOCS_STANDARD.md`](../DOCS_STANDARD.md) §6.

## Contents

| Doc | What it is |
|---|---|
| [`current-bots/birthday-bot-export-2026-08-05.md`](current-bots/birthday-bot-export-2026-08-05.md) | Birthday Bot's 39-row birthday export — **source data for the F6 import**. |
| [`current-bots/discord-scan-2026-08-26.md`](current-bots/discord-scan-2026-08-26.md) | READ-ONLY API scan of the live server: full channel + role inventory, bot census. ℹ️ The "sections C–G are blocked, 4 of 134 channels" warning this row carried until 2026-08-31 is **resolved** — the owner gave `Black_Bloc` the `Bots` role on 2026-08-26 ~18:00 and the rescan read 128/128 channels (`../TODO.md`, "Bot access RESOLVED"). |
| [`current-bots/carl-bot-dashboard-2026-08-26.md`](current-bots/carl-bot-dashboard-2026-08-26.md) | Carl-bot's live dashboard config as measured — automod rules, whitelists, warn thresholds, the reaction-role panels and their emoji→role maps. **Source for F7 and F16.** |
| [`current-bots/yagpdb-dashboard-2026-08-26.md`](current-bots/yagpdb-dashboard-2026-08-26.md) | YAGPDB's live dashboard config — the Streaming/go-live feed template, automod (measured OFF), the role-command groups. **Source for F1/F2 and F17.** |
| [`current-bots/role-audit-2026-08-26.md`](current-bots/role-audit-2026-08-26.md) | Per-member role audit: 118 humans, 7 bots, 59 roles, per-role counts and self-assign holders. **Source for F17** (role-process takeover). |
