# YAGPDB dashboard — what it is configured to do for *Black in a Flash!*

> **Audience:** F1/F2 (streaming) and the role-menus feature. **Status:**
> TRACKED (2026-08-31; private repo), one-off capture. **Last verified: 2026-08-26 ~17:50 Phoenix** —
> read from `yagpdb.xyz/manage/1073710702776299640/*` in the owner's logged-in
> browser; the home page prints every plugin's on/off state, so unlike Carl
> these are real values.

## In use

### Streaming (the F1/F2 source of truth) — **enabled**

| Setting | Value |
|---|---|
| Announce channel | `#live-now` — id `1225457308230746202` |
| Announce message | `REGULATORS! Mount up! **{{.User.Username}}** is currently streaming **{{.Game}}**! Check it out: {{.URL}}` |
| Currently-streaming role | None (disabled) |
| Allowed role (only announce these) | None |
| Ignore role | None |
| Game regex / stream-title regex | empty |
| Detection | Discord presence ("streaming status of users"); YAGPDB's own page warns: *"stream announcements are the most unreliable feature on this bot, but the streaming role is fairly reliable"* — bots ignored |
| Template variables available | `{{.User}}` (Username/ID…), `{{.URL}}`, `{{.Game}}`, `{{.StreamTitle}}`, `{{.Server.Name}}` |

Black Bloc must reproduce: same channel, same wording (with a `/streaming
message` setting so it can change), plus what YAG lacks: opt-out, EventSub
enrichment (title/category/preview), and reliability (presence-only is what
YAG itself calls unreliable).

### Role commands — **7 commands in 3 groups**

| Group | Mode | Members (not shown on page — the Discord scan captures the menus) |
|---|---|---|
| Rule Reader | ? | almost certainly the "I read the rules → Member" gate |
| Runner Status | ? | likely Runner / Live Runner / Commentator |
| Student/Teacher | ? | likely Mentor / Initiate (also a Carl reaction-role panel — **duplicate surface**) |

Group modes YAG offers: Standard / Single (one at a time) / Multiple; per
command: requires-roles, ignore-roles. The role list on the page is the
full server role list — see the Discord scan for ids.

## Explicitly OFF (home page states)

Moderation commands (report/clean/kick/ban/mute/timeout/warn) all disabled ·
Basic automod (slowmode, mass mention, invites, links, banned words/sites)
all disabled · Advanced automod **0 rulesets, 0 rules** · Reputation off ·
Autorole off · Tickets off · reCAPTCHA verification off · Voice role off ·
Join/leave/DM/topic messages off · Reddit/YouTube/RSS/**Twitch feeds 0** ·
Custom commands 0 · Soundboard 0 · Logging: 0 ignored channels (message
logging is on by default in YAG — whether anything is delivered was not
checked). Command prefix `-`.

## What this means for Black Bloc

YAGPDB does exactly two things here: the `#live-now` announcement and three
role-command groups. Replacing it = F1 (streaming) + a role-menu feature
that also absorbs Carl's five reaction-role panels into ONE surface.
