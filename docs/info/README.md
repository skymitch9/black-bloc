# info/ — how Black Bloc works, and why it is built this way

> **Audience:** Claude sessions and the owner. **Status:** LOCAL ONLY (gitignored 2026-08-26).
> Last verified: **2026-08-27** (added `phase8b-design.md` and
> `dashboard-inspiration.md` rows; the other rows were not re-checked).

| File | Answers |
|---|---|
| [`phase1-design.md`](phase1-design.md) · [`phase2-design.md`](phase2-design.md) · [`phase3-design.md`](phase3-design.md) · [`phase4-design.md`](phase4-design.md) · [`phase5-design.md`](phase5-design.md) · [`phase6-design.md`](phase6-design.md) · [`phase7-design.md`](phase7-design.md) · [`phase8-design.md`](phase8-design.md) | Per-phase build specs (the builder's brief source): 1 settings/log/role menus · 2 go-live · 3 temp voice + honeypot · 4 events · 5 birthdays · 6 moderation (shadow) · 7 modmail · **8 the config website** |
| [`phase12-design.md`](phase12-design.md) | **Logs** (2026-08-27): Discord gets only important lines (acted on a member / failed; approvals always notify), per-feature `_log_level`, Logs sections on every page + a global Logs page, `/… logs` on every group; two slices — after the Sunday reset |
| [`phase11-design.md`](phase11-design.md) | **Chat 2 (F10 step 2)** (2026-08-27): editable intents/lines page, data intents (live / next / birthdays / count / roles / timezone), modmail routing, manners settings; two slices — after polls |
| [`phase10-design.md`](phase10-design.md) | **Polls (F15)** (2026-08-27): the 15 owner decisions, deltas from the research design, the test-mode rule, two build slices — build after Phase 9 |
| [`phase9-design.md`](phase9-design.md) | **Role menus 2** (2026-08-27): approval-gated menus (staff Approve/Deny, settable channel), time-limited grants with an expiry loop, reconciliation of hand-made role changes — the four owner decisions and the storage/flows/surfaces |
| [`phase8b-design.md`](phase8b-design.md) | The full dashboard: the 13 tabs, the API/page contract both 8b builders code against |
| [`polls-research.md`](polls-research.md) | **F17 polls**: Polly is Slack-only; EasyPoll/Simple Poll vs Discord native polls feature matrix, typed-answer matrix, discord.py 2.7.1 limits measured, the recommended native-plus-wrapper design, 15 owner decisions |
| [`site-feature-audit.md`](site-feature-audit.md) | **Every dashboard section classed control / data / display** (2026-08-27 read-only audit): the ranked A/B/C change list that feeds the "no displays, only controls" build, incl. the Automod `[object Object]` bug |
| [`dashboard-inspiration.md`](dashboard-inspiration.md) | **What the site should LOOK like.** Survey of 11 bot/admin dashboards (Carl, YAGPDB, MEE6, Dyno, Wick, ProBot, Sapphire, Discord, Linear, Vercel, Cloudflare), what is wrong with ours today, and three candidate directions with palettes, type stacks and wireframes |
| [`review-checklist.md`](review-checklist.md) | ⚠️ **Read before building or reviewing any phase** — 20 items, each traced to a confirmed finding or incident in this repo |
| [`feature-list.md`](feature-list.md) | **The full feature list** (F1–F16): incumbents → replacements, decisions, measured constraints, proposed build order |
| [`architecture.md`](architecture.md) | Package layout, the cog convention, config, storage, the optional API |
| [`code-notes.md`](code-notes.md) | ⚠️ **The comments the source no longer carries.** Every explanation stripped out of `black_bloc/**` and `tests/**`, keyed by `path:line` (owner rule, 2026-08-26) |
| [`hosting.md`](hosting.md) | Why not Cloudflare Workers; why Fly.io; what the alternatives cost |
| [`gotchas.md`](gotchas.md) | Traps that will cost real time: intents, command sync, OneDrive + SQLite, Ctrl+C with the API on |
| [`reference-bots.md`](reference-bots.md) | Feature-by-feature inventory of the bots we are cloning/replacing: TempVoice, Honeypot, YAGPDB, Carl-bot, Birthday Bot, Modmail — plus Discord platform limits (modals, scheduled events, `<t:…>`, intents) |

Design docs for individual features go here too, one file each
(`<feature>-design.md`), written BEFORE the cog when the feature has a
decision in it.
