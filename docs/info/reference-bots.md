# Reference bots — feature inventory for cloning

> Audience: Black Bloc design docs. Status: LOCAL ONLY. Last verified: 2026-08-26 — fetched from the cited URLs that day.

Six products Black Bloc is meant to replace or copy, inventoried feature by
feature. Every section cites the URL it came from. Anything marked
**(inferred)** was reasoned from surrounding docs, not read. Anything marked
**(NOT DOCUMENTED)** is a real gap in the vendor's own docs — do not invent it.

**Maps to:** F1/F2 → §3 YAGPDB Streaming · F4/F5 → §7 Discord platform notes ·
F6 → §5 Birthday Bot · F7 → §3 YAGPDB automod + §4 Carl-bot · F8 → §1 TempVoice ·
F9 → §2 Honeypot · F11 → §6 Modmail.

## Reachability summary

| Bot | Official docs reachable? | Source used |
|---|---|---|
| TempVoice | Partly — `help.tempvoice.xyz` returned **HTTP 403**; `easy.tempvoice.xyz` (also official) worked | <https://easy.tempvoice.xyz/llms.txt> + page `.md` variants |
| Honeypot | Yes, but thin | <https://www.honeypotbot.com/guide/> |
| YAGPDB | Yes | <https://help.yagpdb.xyz> + the docs source repo on GitHub |
| Carl-bot | Rendered site pages 404'd; the **docs source repo** worked | <https://github.com/CarlGroth/carlbot-docs> raw markdown |
| Birthday Bot | Mixed — `noithecat.dev` / `noi.dev` **403**; `birthdaybot.scottbucher.dev` worked | <https://birthdaybot.scottbucher.dev/llms-full.txt> |
| Modmail | Yes, plus source | <https://docs.modmail.dev> + `cogs/modmail.py` |

---

# 1. TempVoice (F8 — temporary voice channels)

Sources: <https://tempvoice.xyz> · <https://easy.tempvoice.xyz/llms.txt> ·
<https://easy.tempvoice.xyz/llms-full.txt> · plus individual `.md` pages cited
inline. `https://help.tempvoice.xyz/docs/*` returned **HTTP 403** and was not
read.

## 1.1 Core flow

| Feature | User's view | Notes |
|---|---|---|
| **Creator Channel** | A normal voice channel. Joining it creates a new temp channel and moves you into it. | "it only exists as long as someone is using it" — deleted when the last person leaves. Free plan: **2 Creator Channels**; unlimited on Premium. Source: `getting-started/setup.md`, `faq/limits.md` |
| **Ownership** | Whoever the Creator Channel spawned the channel for owns it. | Owner gets configurable Discord permissions inside the channel (§1.4). |
| **Control surface** | Either `/voice …` slash commands **or** an **Interface Message** of buttons. | Both do the same things. Source: `commands/interface-message.md` |

## 1.2 Interface Message — 15 buttons, 1:1 with commands

Source: <https://easy.tempvoice.xyz/commands/interface-message.md>. The message
can be posted unlimited times, in a dedicated text channel or embedded in the
temp channel's greeting message (`settings/others/greeting.md`).

| Button | Command | What it does |
|---|---|---|
| NAME | `/voice name` | Rename the channel |
| LIMIT | `/voice limit` | Set user cap |
| PRIVACY | `/voice privacy` | Public / Locked / Hidden |
| WAITING ROOM | `/voice waiting` | Join requests need approval |
| CHAT | `/voice thread` | Create a text thread for the channel |
| TRUST | `/voice user trust` | Whitelist a user |
| UNTRUST | `/voice user untrust` | Remove from whitelist |
| BLOCK | `/voice user block` | Blacklist a user |
| UNBLOCK | `/voice user unblock` | Remove from blacklist |
| INVITE | `/voice user invite` | Invite a user in |
| KICK | `/voice user kick` | Kick a user out of the channel |
| REGION | `/voice region` | Change the voice region |
| CLAIM | `/voice claim` | Take ownership |
| TRANSFER | `/voice transfer` | Hand ownership to someone |
| DELETE | `/voice delete` | Force-delete the channel |

Not on the button panel but present as commands: `/voice bitrate`,
`/voice password`, `/voice reset`, `/voice info`, `/voice lfp` (looking-for-players),
plus top-level `/find` (locate a user in a voice channel) and `/join` (enter a
password-protected channel). Source: <https://easy.tempvoice.xyz/llms.txt>.

**Permission to use:** "A user needs Use Application Command permission to use
this command" (`commands/voice.md`).

## 1.3 Non-obvious behaviours

| Thing | Behaviour | Source |
|---|---|---|
| **Vote-gating** | `claim`, `bitrate`, `waiting` (and more) require a **Top.gg vote, valid 12 hours**, unless the server has Premium. | `commands/voice/claim.md`, `.../bitrate.md`, `.../waiting.md` |
| **Preference persistence** | Changing name / limit / privacy is **saved and re-applied to the next temp channel that user creates**. | `commands/voice/privacy.md` |
| **Restore Owner Settings** | Server-side toggle that *defeats* the above: every new temp channel reverts to the Creator Channel defaults. Users can still change things, "but these settings will not be saved." | `settings/moderation/restore.md` |
| **Ownerless mode** | A feature toggle that removes ownership entirely — the creator "will not be able to customize or moderate it". | `settings/moderation/features.md` |
| **Feature toggles** | Each feature can be *disabled*, open to `@everyone`, or **restricted to specific roles (Premium)**. Disabling a feature also resets users' saved config for it back to the Creator Channel default. | `settings/moderation/features.md` |
| **Claim conditions** | The docs do **not** state when a channel becomes claimable (owner absent? how long?). **(NOT DOCUMENTED)** | `commands/voice/claim.md` |
| **Bitrate range** | Not stated in the docs. Discord's own ceiling is tier-dependent. **(NOT DOCUMENTED)** | `commands/voice/bitrate.md` |
| **Privacy mode semantics** | Three modes — Public / Locked / Hidden — but the exact permission overwrites each applies are **not documented**. Hidden is described as making the channel invisible. **(NOT DOCUMENTED)** | `commands/voice/privacy.md`, `settings/permissions/privacy.md` |

## 1.4 Server-side settings (dashboard, per Creator Channel)

Source: <https://easy.tempvoice.xyz/llms-full.txt> and the `settings/*` pages.

| Tab | Settings |
|---|---|
| **Overview** | Default channel name (placeholders, §1.5), default user limit, target category + fallback categories, default bitrate, channel position |
| **Permissions** | Access roles (who may use the Creator Channel), permission **sync** from creator channel/category, default privacy mode, **owner permissions** granted inside the temp channel |
| **Moderation** | Toggle features (per-role), moderation **log** (webhook), Restore Owner Settings, **censor channel names** (partial matching), age restriction for in-voice chat |
| **Others** | Greeting message (optionally with the interface embedded), temporary **voice role** given while in a temp channel, in-voice-chat interface |

⚠️ Owner-permission warning from the docs: do **not** grant channel owners
*Manage Permissions* — "they risk disrupting bot functionality by modifying
incorrect permission settings" (`settings/permissions/owner.md`). The full list
of grantable owner permissions is **(NOT DOCUMENTED)**.

## 1.5 Name placeholders

Source: <https://easy.tempvoice.xyz/help/placeholders.md> (index at `llms.txt`).

`{CUSTOM}` `{PRIVACY}` `{RANDOM}` `{OWNER_USERNAME}` `{OWNER_NICKNAME}`
`{OWNER_MENTION}` `{OWNER_CREATED}` `{OWNER_JOINED}` `{NUMBER}` `{NUMBER_ROMAN}`
`{NUMBER_ALPHA}` `{NUMBER_DIGIT}` `{NUMBER_EXPONENT}` `{ROLE_HIGHEST}`
`{ROLE_HOIST}` `{GUILD_ID}` `{CHANNEL_ID}` `{ACTIVITY_NAME}`
`{ACTIVITY_MAJORITY_NAME}` `{ACTIVITY_DETAILS}` `{ACTIVITY_STATE}`
`{ACTIVITY_EMOJI}` (activity ones are Premium).

## 1.6 Limits that will bite the clone

Source: <https://easy.tempvoice.xyz/faq/limits.md> (via `llms-full.txt`).

| Limit | Value | Whose limit |
|---|---|---|
| Channels per server | 500 | Discord |
| Channels per category | 50 | Discord |
| Channel **creations** per rolling 24h | 2,000 | Discord |
| **Channel rename cooldown** | once per 5 minutes | Discord — ⚠️ this is the big one for a rename button |
| Trusted/blocked users per channel | 25 | TempVoice |
| Creator Channels (free) | 2 | TempVoice |

Troubleshooting notes: empty temp channels persist if the bot is offline;
re-inviting refreshes permissions
(<https://easy.tempvoice.xyz/troubleshooting/empty-channels.md>).

**Permissions the bot needs (inferred** from the feature set — the docs do not
list them**):** Manage Channels, Move Members, Manage Roles (for the voice
role), Connect/View Channel on the category, Manage Messages (interface).

---

# 2. Honeypot Bot (F9)

Sources: <https://www.honeypotbot.com> · <https://www.honeypotbot.com/guide/> ·
`/guide/quickstart` · `/guide/honeypots/creation` · `/guide/honeypots/editing` ·
`/guide/honeypots/management` · `/guide/logging`. All reachable; the docs are
genuinely short.

Positioning: "a spam prevention bot for discord, primarily aimed at preventing
the 'flood all channels' style of spammer."

## 2.1 Setup flow

| Step | Action | Note |
|---|---|---|
| 1 | Invite with the official OAuth2 link | "Do not uncheck any permissions" — all are required |
| 2 | **Move the auto-created `Honeypot` role to the top of the role list** | Required for it to ban/timeout/assign roles. Repeated as a prerequisite on every page. |
| 3 | `/honeypot create <channel>` | Default = **soft ban**, deleting the last **1 day** of messages |
| 4 | `/logging set channel <channel>` (optional) | `/logging set role <role>` to ping on each log |

## 2.2 Honeypot types (the punishment)

Source: `/guide/honeypots/creation`, `/guide/honeypots/editing`.

| Type | Command | Options | Effect |
|---|---|---|---|
| **Soft ban** (default) | `/honeypot create` | `delete_messages` (0 = delete nothing; default 1 day; up to 5 days) | Ban then immediately unban — "same functional effect as kicking… but allows for the deletion of their messages" |
| **Ban** | `/honeypot edit ban` | `channel`, `delete_messages` (up to 5 days) | Permanent ban |
| **Timeout** | `/honeypot edit timeout` | `channel`, `timeout_length` (hours) | Discord timeout |
| **Role** | `/honeypot edit role` | `channel`, `role` | Assigns a role (quarantine pattern). The admin must have permission to grant that role. |

## 2.3 Management + logging

| Command | Does |
|---|---|
| `/honeypot list` | List all honeypots on the server |
| `/honeypot info <channel>` | Details for one honeypot |
| `/honeypot delete <channel>` | Remove one; the channel can be re-honeypotted later |
| `/honeypot delete_all` | Remove all — useful when the channels no longer exist |
| `/logging set channel` / `remove channel` | Where actions are logged |
| `/logging set role` / `remove role` | Role pinged per log entry |

Logging exists specifically so "your moderation team [can] monitor and respond
to events requiring human judgment" — the docs call out **timeout and role
honeypots** as the ones needing manual follow-up (`/guide/logging`).

## 2.4 Gaps in Honeypot's own docs — decide these ourselves

⚠️ These are **(NOT DOCUMENTED)** anywhere on honeypotbot.com; I checked
`/guide/`, quickstart, creation, editing, management and logging:

- **What exactly triggers it.** Pages only say "the member who triggers the
  honeypot". No statement of whether it is any message, a reaction, a join, or
  whether bots/webhooks count.
- **Whitelist / exempt / bypass roles.** No such feature is documented.
- **Admin/mod exemption.** Not mentioned.
- **False-positive handling.** No undo, appeal or dry-run mode documented.
- **The triggering message itself** — whether it is deleted independently of
  the `delete_messages` window.
- **Permission list.** "All are required" but they are never enumerated.
  **(inferred)** at minimum: Ban Members, Moderate Members (timeout), Manage
  Roles, Manage Messages, View Channel, Read Message History.

**Design consequence for Black Bloc (F9):** we must add what Honeypot lacks —
an exempt-roles list, a shadow/log-only mode (per the rollout rule), and a
"who triggered, with the message content" log line — before this can safely
replace anything.

---

# 3. YAGPDB (F1/F2 streaming; F7 automod reference)

## 3.1 Streaming feature

Sources: <https://help.yagpdb.xyz/docs/notifications/streaming/> and the docs
source <https://github.com/botlabs-gg/yagpdb-docs-v2/blob/master/content/docs/notifications/streaming.md>.

**Detection:** driven entirely by **Discord's streaming presence status** — not
by a Twitch API subscription. Requires the **presence intent** (§7.4).

| Setting | What it does |
|---|---|
| **Announce channel** | Where the "X is live" post goes |
| **Announcement message** | Template text; variables below |
| **Currently streaming role** | Role held **while live** |
| **Game regex** | Only announce / assign role when the game matches this regex |
| **Stream title regex** | Same, on the stream title |
| **Allowed role** (require-role) | Only members with this role are announced / get the role |
| **Ignore role** | Members with this role are never announced and never get the role |

**Template variables** (the streaming feed adds these on top of YAGPDB's normal
template context):

| Variable | Value |
|---|---|
| `{{ .URL }}` | Stream link |
| `{{ .Game }}` | Game being played |
| `{{ .StreamTitle }}` | Stream title |
| `{{ .User.Username }}` | Streamer's Discord username |

⚠️ **Two documented limitations, both directly relevant to F1/F2:**

1. "There are currently some issues with the streaming announcement, and it
   may not always give the announcement." Role assignment is the reliable half.
2. "The streaming role will be **automatically removed** from a member that is
   not streaming if it is given manually" — YAGPDB reconciles the role, so the
   role must be dedicated. Black Bloc must do the same and say so.

**(inferred)** Presence gives the platform implicitly (Discord's streaming
activity carries a URL, which is twitch.tv for Twitch); YAGPDB does not document
a platform filter, so a YouTube-vs-Twitch split would have to come from the URL.

## 3.2 Basic Automoderator — rule types

Source: <https://help.yagpdb.xyz/docs/moderation/basic-automoderator/>. Six
fixed rules. **Every rule warns and deletes the message**; on top of that each
has violation thresholds for mute / kick / ban (0 = disabled) and a violation
expiry of 0 (never) to 44,640 minutes (31 days). Per rule: **one** ignored role
and multiple ignored channels.

| Rule | Trigger | Notes |
|---|---|---|
| Slowmode | N messages in M seconds | docs suggest 5-in-2s |
| Mass Mention | more than N mentions in one message | no cross-channel check |
| Server Invites | invite links, excluding invites to this server | |
| Links | any URL, **including Discord GIFs** | docs recommend Banned Websites instead |
| Banned Words | case-insensitive, **no partial matches**; presets or custom list | |
| Banned Websites | domain list; optional Google Safe Browsing + phishing DB | |

## 3.3 Advanced Automoderator (v2) — the model

Source: <https://help.yagpdb.xyz/docs/moderation/advanced-automoderator/overview/>.

- **Ruleset** = container of rules, toggleable, can carry conditions scoped to
  all its rules.
- **Rule** = triggers + conditions + effects.
- **Triggers use OR** (any one fires the rule). **Conditions use AND** (all must
  hold). **Effects use AND** (all run).

| Limit | Free | Premium |
|---|---|---|
| Lists | 5 | 25 |
| Rulesets | 10 | 25 |
| Rules total | 25 | 150 |
| Parts per rule | 25 | 25 |
| List size | 5,000 chars | 5,000 chars |

### Triggers

Source: [triggers.md](https://github.com/botlabs-gg/yagpdb-docs-v2/blob/master/content/docs/moderation/advanced-automoderator/triggers.md).
"Also match visually similar characters" (homoglyph folding) is an option on
most text triggers.

| Group | Trigger | Key options (defaults) |
|---|---|---|
| Content | All caps | min caps 3, percent 100 |
| Content | Message mentions | min mentions 4 |
| Content | Any link | — |
| Content | Word denylist / allowlist | list |
| Content | Website denylist / allowlist | list; matches subdomains |
| Content | Server invites | excludes this server |
| Content | Google flagged bad links | — |
| Content | Flagged scam links | — |
| Content | Message matches / not matching regex | regex |
| Content | X consecutive identical messages | threshold 4, within 60s |
| Content | Message with / without attachments | — |
| Content | Message more / less than X characters | length 0 |
| Content | Message triggers Discord Automod | rule ID (blank = any) |
| Rate | X violations in Y minutes | name, 4, 60min, "ignore if higher violation trigger activated" on |
| Rate | X user / channel messages in Y seconds | 5 in 5 |
| Rate | user / channel: X mentions in Y seconds | 20 in 10 |
| Rate | X user / channel links in Y seconds | 5 in 60 |
| Rate | X user / channel attachments in Y seconds | 10 in 60 |
| Identity | Nickname matches / not matching regex | regex |
| Identity | Nickname word allowlist / denylist | list |
| Join | Join username word allowlist / denylist | list |
| Join | Join username matches / not matching regex | regex |
| Join | Join username invite | — |
| Join | **New Member** | fires on join |

### Conditions

Source: [conditions.md](https://github.com/botlabs-gg/yagpdb-docs-v2/blob/master/content/docs/moderation/advanced-automoderator/conditions.md).
**This is the "exceptions list" model F7 wants.**

| Condition | Options |
|---|---|
| Ignored Roles | roles |
| Require Roles | roles + "require all / any" (default any) |
| Ignore Channels / Active in Channels | channels |
| Ignore Categories / Active in Categories | categories |
| Account Age Above / Below | minutes |
| Server Member Duration Above / Below | minutes |
| Ignore Bots / Only Bots | toggle |
| New Message / Edited Message | toggle |
| Active in Threads / Ignore Threads | toggle |
| Ignore Messages with Forwards / Only Match Messages with Forwards | toggle |

### Effects

Source: [effects.md](https://github.com/botlabs-gg/yagpdb-docs-v2/blob/master/content/docs/moderation/advanced-automoderator/effects.md).

| Effect | Options (defaults) |
|---|---|
| Delete Message | — |
| Delete multiple messages | count 3, max age 15s |
| +Violation | name |
| Reset violations | violation name |
| Warn user | custom message |
| Mute user | duration min (0 = permanent), custom message |
| Timeout user | duration min, custom message |
| Kick user | custom message |
| Ban user | duration min (0 = permanent), custom message, delete 0–7 days of history |
| Give role / Remove role | duration sec (0 = permanent), role |
| Set nickname | new nickname (empty = remove) |
| Enable channel slowmode | duration sec, ratelimit |
| Send Message | text ≤280 chars, delete-after ≤3600s, ping user, target channel |
| Send Alert | embed about the trigger, ≤280 char note, target channel |

⚠️ Owner has stated **YAGPDB runs NO automod ruleset on this server** — this
section is a *design reference* for F7, not a config to migrate.

---

# 4. Carl-bot (F7 moderation reference — and the export we are waiting on)

Sources: the docs source repo <https://github.com/CarlGroth/carlbot-docs>
(raw markdown). `https://docs.carl.gg/<page>/` returned 404 for the paths I
tried and the site root exposed no navigation to WebFetch.

## 4.1 Automod

Source: [`moderation/automod.md`](https://github.com/CarlGroth/carlbot-docs/blob/master/moderation/automod.md).
Docs recommend the dashboard at carl.gg over commands.

| Rule | Command shape | Settings |
|---|---|---|
| Slowmode | `!slowmode 5 25` | N messages per M seconds |
| Attachment spam | `!attachmentspam 3 5` | N attachments per M seconds |
| Mention spam | `!mentionspam 25 5` | N mentions per M seconds |
| Link spam | — | modes: **block** (punish non-whitelisted), **off** (punish blacklisted only), **norole** (only affect members with no roles) |
| Invite spam | — | same blacklist/whitelist model as link spam |
| Caps | — | percentage-of-uppercase threshold |
| Word censor | — | blacklist + custom response |
| File filter | — | toggle deletion of non-approved file formats |
| Media-only channels | — | force image/link-only posting in a channel |

**Punishments stack** — any combination of: `delete`, `warn`, `tempmute`,
`mute`, `kick`, `tempban`, `ban`, `defer`, `message`, `dm`.

| Concept | Meaning |
|---|---|
| **Whitelist** | Roles and channels automod ignores |
| **Warn threshold** | Once a user's warning count exceeds the limit, a punishment fires **on each new warning while above the threshold** |
| **Automod log** | `automod log` — separate channel from the modlog, because automatic actions differ in nature |
| **Drama channel** | Disputed cases routed to a channel where mods vote by reaction |

## 4.2 Moderation commands + modlog

Source: [`moderation/moderation.md`](https://github.com/CarlGroth/carlbot-docs/blob/master/moderation/moderation.md),
[`logging/modlogs.md`](https://github.com/CarlGroth/carlbot-docs/blob/master/logging/modlogs.md).

| Command | Args | Behaviour |
|---|---|---|
| `ban` | `<@member/ID> [days=2] [reason]` | works on users not in the server (hackban) |
| `softban` | `<@member> [days=2] [reason]` | ban + immediate unban to clear 48h of history |
| `tempban` | `<@user> [days=2] [reason]` | timed, works off-server |
| `massban` | `[days=2] <@members…>` | one modlog entry per user |
| `kick` | `<@member> [reason]` | reason lands in modlog **and** Discord audit log |
| `mute` / `unmute` | `<@member> [time] [reason]` | uses a **muterole**; no time = indefinite |
| `warn` | `<@member> [reason]` | DMs the user the reason, posts to modlog |
| `removewarn` / `clearwarn` | `<case_id>` / `<@member>` | |
| `purge` | `[count=100]` | subcommands: `bot`, `contains`, `user`, `all`, `embeds`, `emoji`, `files`, `images`, `links`, `reactions` |
| `cleanup` | `[count=100]` | like `purge bot` but for Carl-bot across all prefixes |
| `lockdown` / `unlockdown` | `<#channel> <duration>` | plus `lockdown server` / `unlockdown server` |

**Modlog:** `modlog create` / `modlog set <#channel>` / `modlog clear`; every
action gets a **case ID**; `reason <case_id>` back-fills a reason for a manual
or reason-less action; `modlog highscores` ranks mods by action count; per-member
infraction history shows the responsible moderator.

## 4.3 Logging (server events)

Source: [`logging/logging.md`](https://github.com/CarlGroth/carlbot-docs/blob/master/logging/logging.md).

**Events:** `delete`, `edit`, `purge`, `discord`, `role`, `avatar`, `bans`,
`ban`, `unban`, `join`, `leave`, `channels`, `channelcreate`, `channelupdate`,
`channeldelete`, `rolecreate`, `roleupdate`, `roledelete`, `allroles`, `emoji`,
`server`, `voicejoin`, `voicemove`, `voiceleave`, `voice`, plus the meta values
`everything`, `nothing`, `default`.

**Commands:** `log channel [#channel]`, `log [event]`, and split destinations
`log messagechannel` / `memberchannel` / `joinchannel` / `serverchannel` /
`voicechannel`; `log ignore` / `log unignore <channels/members…>`;
`log ip|prefix <prefix>` and `log up|removeprefix <prefix>` (ignore bot-prefixed
messages); `log export`, `log import|custom <perms>`, `log aio`.

## 4.4 Reaction roles

Source: [`roles/reaction-roles.md`](https://github.com/CarlGroth/carlbot-docs/blob/master/roles/reaction-roles.md).

**Setup:** `rr setup|make` (interactive), `rr add` (works on non-bot messages
too), `rr addmany` (newline-separated pairs), `rr aio` (one-shot for power
users), `rr list|show`, `rr edit` (title/description), `rr color`, `rr move`,
`rr remove`, `rr clear`. `!embed` builds the embed the reactions sit on.

| Mode | Behaviour |
|---|---|
| **Normal** | Default: react = add role, unreact = remove role |
| **Unique** | Only one role from that message at a time (per message) |
| **Verify** | Reactions can only *add* roles, never remove |
| **Drop** | Only *removes* roles — the role goes away when the emoji is added |
| **Reversed** | React removes, unreact adds |
| **Binding** | Unique + verify: one pick, and it cannot be changed |
| **Locked** | No assignments happen at all |
| **Temp** | Role granted for a duration then removed (**Patreon only**) |
| **Limit** | `rr limit <msg_id> <n>` — max N roles per member from that message |
| **Maxroles** | Cap on how many *members* may hold a given role |
| **Link** | Share a limit across several messages |
| **bl / wl** | Blacklist / whitelist roles that may use the reaction roles |
| **selfdestruct** | Auto-delete the message after a duration |

## 4.5 Welcome / leave messages

Source: [`logging/welcome-and-leave-messages.md`](https://github.com/CarlGroth/carlbot-docs/blob/master/logging/welcome-and-leave-messages.md).

`!set welcome <#channel>` **must be run first**. Then `!greet|welcome <text>`,
`!farewell|leave <text>`, `!banmsg <text>`, `!dmjoin <text>` (DM instead of
channel post). `!testgreet` previews all of them. Running a command with no
text removes that message.

Placeholders: `{mention}`, `{user}`, `{user(id)}`, `{user(proper)}`,
`{server}`, `{server(members)}`, `{random: a, b, c}`, `{math: expr}`.

## 4.6 Starboard

Source: [`utilities/starboard.md`](https://github.com/CarlGroth/carlbot-docs/blob/master/utilities/starboard.md).

`!starboard [name]` creates it (default channel name `starboard`);
`!star limit <n>` sets the threshold; `!star nsfw` toggles embedding posts from
NSFW channels; `!star self` toggles self-starring; `!star stats [@member]`,
`!star top`, `!star show <id>`, `!star jump`. The starboard entry's footer
carries the original message ID.

## 4.7 Tags / custom commands + autoresponders

Sources: [`tags-and-responses/tags.md`](https://github.com/CarlGroth/carlbot-docs/blob/master/tags-and-responses/tags.md),
[`autoresponses-trigger-words.md`](https://github.com/CarlGroth/carlbot-docs/blob/master/tags-and-responses/autoresponses-trigger-words.md).

**Tags:** `!tag + <name> <content>` create, `!tag edit`, `!tag - <name>` delete,
`!tag += <name> <content>` append, `!tag ++ <name>` from pastebin, `!tag raw`,
`!tag info` / `!tag stats`, `!tag list`, aliases (alias follows the original),
`claim` (take over a tag when the owner leaves). Invocable as bare
`!<tagname>`. Settings: NSFW-only, restrict-to-bot-channels, modonly creation,
ownership enforcement (off by default). Content supports **tagscript**.

**Autoresponders:** `ar add` (substring), `ar strict` (word sequence),
`ar exact` (whole message), `ar startswith`, `ar endswith`, plus `ar list`,
`ar remove`, `ar clear`, `ar channel` (single-channel, overrides channel
ignores but respects member ignores), `ar ignore` / `ar unignore`. Docs note
tags are better than autoresponders for prefix-triggered keywords.

## 4.8 Autorole

Source: [`roles/autoroles-and-delayed-autoroles.md`](https://github.com/CarlGroth/carlbot-docs/blob/master/roles/autoroles-and-delayed-autoroles.md).

`autorole` (show config), `autorole add/remove`, `autorole readd|reassign`
(re-apply roles when a member rejoins — sticky roles), `autorole bl` (roles
never reassigned). When both autoroles and reassigned roles exist, "the member
will receive the **union** of both."

**Delayed autoroles:** `timedrole|tr` lists them; `timedrole add <time> <role>`
(e.g. `42h19m22s`); `timedrole remove`.

---

# 5. Birthday Bot (F6)

⚠️ **Identity caveat.** <https://birthdaybot.io> is a **different product** — a
Slack/workplace "birthdays, work anniversaries, recognition and reward
workflows" SaaS, not the Discord bot. The two Discord candidates:

| Candidate | Docs | Result |
|---|---|---|
| **Birthday Bot** by NoiTheCat (app id `656621136808902656`) | noithecat.dev / noi.dev | **HTTP 403 — not fetched.** |
| **Birthday Bot** by scottbucher | <https://birthdaybot.scottbucher.dev> | Reachable; documented below |

Our export at `archive/current-bots/birthday-bot-export-2026-08-05.md` quotes
the rule *"celebrated on the day and month the user has but in the time zone of
the server"* and shows **ages** in the list — both behaviours exist in
scottbucher's bot (server-time-zone mode + `{Age}`), so the section below is the
best available match, but **which bot the server actually runs is unconfirmed**
and should be checked against the server's installed app ID before F6 ships.

Source for everything below: <https://birthdaybot.scottbucher.dev/llms-full.txt>
and <https://birthdaybot.scottbucher.dev/commands>.

## 5.1 Setup flow

`/setup` walks three steps: **birthday channel** (auto-create / pick existing /
skip) → **birthday role** (same three) → confirm. Fuzzy name matching, so
"birthday" resolves to "birthdays-and-anniversaries".

## 5.2 Timezone + the cutover — the part F6 actually needs

| Setting | Behaviour |
|---|---|
| `/config option:Time Zone` | The **server** time zone. Required for anniversary celebrations. |
| `/config option:Use Time Zone` | **`server`** = all birthday events fire on the server's tz. **`user`** = each member's own tz. If the server tz is unset, it falls back to the user's tz regardless. |
| User tz prompt | When a user first sets a birthday, if the server has a default tz they are prompted to adopt it. |
| `/edit hour type:<type> time:<0-23>` | **The cutover hour** — when the celebration *message* posts. |
| ⚠️ Role vs message timing | The **birthday role is assigned at midnight** in the relevant tz; only the *message* honours the hour setting. These are two different clocks. |
| Delivery window | The bot processes hundreds of thousands of servers hourly; posting "can extend up to 10 minutes" past the hour. Premium buys priority. |

## 5.3 Birthday role

- Assigned on the day, and **actively removed hourly** from anyone whose
  birthday is not current — ⚠️ so the role must be dedicated, exactly like
  YAGPDB's streaming role (§3.1).
- Needs **Manage Roles** and the bot's own role **above** the birthday role.

## 5.4 Membership / eligibility model

| Concept | Behaviour |
|---|---|
| **Trusted roles** | 1 on free, up to 250 on premium. `RequireAllTrustedRoles` decides whether a member needs all of them or any one. Each trusted role can independently gate: message delivery, role assignment, ping mention, and appearance in `/list` and `/next`. |
| **Blacklist** | Users **and roles** whose birthday is never celebrated. **Blacklist beats trusted roles.** |

## 5.5 Age / year privacy

- Birth years are **hidden network-wide by default**.
- Users control visibility **globally** (`/user edit`) and **per server**
  (`/user_server edit`); the per-server setting overrides the global one.
- Admins can force it off server-wide with `/config option:Disable Ages`, plus
  `Filter Birthday Age Messages`.

## 5.6 Messages

- Free: 1 custom message per event type. Premium: 500 each.
- `/message add|edit|remove|clear|test`, `/view_messages`.
- Placeholders — **birthday:** `{Users}`, `{Server}`, `{Age}`, `{Year}` (free)
  and `{Zodiac Sign}` / `{Zodiac Role}` / `{Zodiac Emoji}` (premium);
  **member anniversary:** `{Users}`, `{Year}`, `{Server}`;
  **server anniversary / custom event:** `{Year}`, `{Server}`.
- `/edit ping` accepts `everyone`, `here`, `@role/name`, `none`, or `{Users}`.
- `/edit channel` per event type; `/edit post_mode` (thread/pin, premium);
  embed colour/title/footer/image are premium and only apply when embed mode is on.

## 5.7 Command surface (for parity checking)

`/set`, `/view`, `/next`, `/list`, `/map`, `/purge` (delete your own data),
`/suggest` (propose someone else's birthday, they confirm), `/claim_role`,
`/user settings|edit`, `/user_server settings|edit`, `/settings`, `/setup`,
`/test`, `/config option:…`, `/message …`, `/edit …`, `/trustedRole …`,
`/blacklist …`, `/mar …` (member anniversary roles), `/zodiac …` (premium),
`/help`, `/info`, `/link`, `/premium`, `/subscribe`, `/vote`.

---

# 6. Modmail (F11)

Sources: <https://github.com/modmail-dev/Modmail> (README) ·
<https://docs.modmail.dev> · <https://docs.modmail.dev/usage-guide.md> ·
<https://docs.modmail.dev/usage-guide/permissions.md> · and the authoritative
command list read from the source,
<https://github.com/modmail-dev/Modmail/blob/master/cogs/modmail.py>.

⚠️ <https://docs.modmail.dev/config-references/config-vars.md> has been
**pulled by its maintainers** — the page says it was withdrawn "due to factual
inaccuracies" and is being redone. So the per-variable config list is
**unavailable**, not merely unfetched.

## 6.1 The model

- A member **DMs the bot** → Modmail creates a **channel ("thread") inside a
  designated category**. Staff reply from that channel.
- Messages typed in the thread **without** the reply command are **internal
  notes**, visible only to staff. (`reply_without_command: true` inverts this.)
- On close, Modmail **generates a log link and posts it to the log channel**.

## 6.2 Commands (from `cogs/modmail.py`, with permission level)

| Command | Aliases | Level | Purpose |
|---|---|---|---|
| `setup` | | OWNER | Set the server up for Modmail |
| `reply` | | SUPPORTER | Reply to the user |
| `areply` | `anonreply`, `anonymousreply` | SUPPORTER | **Anonymous** reply (shows the role, not the person) |
| `preply` | `plainreply` | SUPPORTER | Plain (non-embed) reply |
| `pareply` | `plainanonreply` | SUPPORTER | Plain + anonymous |
| `freply` / `fareply` / `fpreply` / `fpareply` | `format*` | SUPPORTER | The four reply forms **with variable substitution** |
| `edit` / `delete` | | SUPPORTER | Edit or delete a sent reply or note |
| `note` | | SUPPORTER | Note on the current thread |
| `note persistent` | `persist` | SUPPORTER | Note that follows the **user** across threads |
| `close` | | SUPPORTER | Close; accepts a custom message, a timer (`2m30s`, `5 hours`), and `-s` silent. A reply before the timer expires **cancels** the scheduled close |
| `snooze` | | SUPPORTER | Snooze the thread |
| `move` | | MODERATOR | Move the thread to another category |
| `title` | | SUPPORTER | Set the thread title |
| `notify` | `alert` | SUPPORTER | Ping a user/role on the **next** thread message |
| `unnotify` | `unalert` | SUPPORTER | Cancel that |
| `subscribe` | `sub` | SUPPORTER | Ping on **every** message in the thread |
| `unsubscribe` | `unsub` | SUPPORTER | Cancel |
| `contact` | | SUPPORTER | Open a thread **with** a specified member |
| `selfcontact` | | REGULAR | Open a thread with yourself |
| `adduser` / `removeuser` | | SUPPORTER | Group threads — add/remove a participant |
| `anonadduser` / `anonremoveuser` | | SUPPORTER | Same, anonymously |
| `block` / `unblock` | | MODERATOR | Block a **user or role** from Modmail |
| `blocked` | | MODERATOR | List blocked users |
| `blocked whitelist` | | MODERATOR | Exempt someone from ever being blocked |
| `logs` | | SUPPORTER | Previous threads for a member |
| `logs search` | `find` | SUPPORTER | Full-text search across logs |
| `logs closed-by` / `logs responded` / `logs key` | | SUPPORTER | Filter logs by closer / responder / key |
| `logs delete` | `wipe` | OWNER | Wipe a log entry from the DB |
| `loglink` / `msglink` | | SUPPORTER | Links to this thread's log / a message |
| `snippet` (+ `add`, `edit`, `remove`, `raw`) | `snippets` | SUPPORTER | Pre-defined replies, invoked by name as a command |
| `nsfw` / `sfw` | | SUPPORTER | Flag the thread |
| `repair` | | SUPPORTER | Repair a thread broken by Discord |
| `enable` / `disable` (`disable new`, `disable all`) / `isenable` | | ADMINISTRATOR | Stop accepting new threads, or all DM function |

## 6.3 Permission model

Five levels — **OWNER (5) · ADMINISTRATOR (4) · MODERATOR (3) · SUPPORTER (2) ·
REGULAR (1)**. Grant by level (`?permissions add level <name> <role/user>`) or
per command (`?permissions add command <cmd> <role/user>`). A command's
required level can be overridden (`?permissions override <cmd> <level>`), and
since v4.2.2 in bulk (`?permissions override bulk`).

## 6.4 Other features

| Feature | Detail |
|---|---|
| **Aliases** | Custom command aliases alongside snippets |
| **Anti-abuse gates** | Minimum **account age** and minimum **guild join age** before a user may open a thread |
| **Auto-close** | Configurable auto-close on inactivity |
| **Customisation** | Bot status, prefix, category, log channel, colours, reactions, thread-creation message, thread naming format |
| **Plugins** | Third-party plugins extend the bot — [wiki](https://github.com/modmail-dev/modmail/wiki/Plugins), [unofficial plugin list](https://github.com/modmail-dev/modmail/wiki/Unofficial-List-of-Plugins) |
| **Transcripts** | The "log link" is a hosted **Logviewer** instance the operator runs (docs have a whole install section for it) |

**Intents:** Modmail's docs carry an [Intents Review Process](https://docs.modmail.dev/faq/intents-review.md)
page — it needs **Message Content** and **Server Members** (§7.4).

---

# 7. Discord platform notes

All from Discord's developer docs. ⚠️ `discord.com/developers/docs/*` now
**301-redirects to `docs.discord.com/developers/*`** — fetchers that do not
follow cross-host redirects will appear to fail. Use the `docs.discord.com`
form.

## 7.1 Modals — the 5-input cap (F4)

Source: <https://docs.discord.com/developers/interactions/receiving-and-responding>
and <https://docs.discord.com/developers/components/reference>.

| Field | Constraint |
|---|---|
| `custom_id` (modal) | 1–100 chars |
| `title` | max 45 chars |
| `components` | **"Between 1 and 5 (inclusive) components that make up the modal"** |

Text Input (type 4): `custom_id` 1–100; `style` 1 = Short, 2 = Paragraph;
`min_length` 0–4000; `max_length` 1–4000; `required` defaults true; `value`
prefill ≤4000; `placeholder` ≤100.

⚠️ **Discrepancy worth resolving before building the event form.** The
interactions page still states the classic **1–5 components** modal limit
(i.e. 5 text inputs). The newer components reference describes modals that may
also contain Label, Text Display, String/User/Role/Mentionable/Channel Select,
File Upload, Radio Group, Checkbox Group and Checkbox, says **Text Inputs
should now sit inside Label components rather than Action Rows**, and gives a
**maximum of 40 components**. Disabled components are not allowed in modals.
**Treat 5 text inputs as the safe floor** and verify the 40-component path
against the library (discord.py) before designing a longer form. **(inferred:
the 40-component figure is the Components-V2 modal path; the two pages were not
reconciled by Discord.)**

## 7.2 Scheduled events (F4/F5)

Source: <https://docs.discord.com/developers/resources/guild-scheduled-event>.
`POST /guilds/{guild.id}/scheduled-events`.

| Param | Type | Required | Notes |
|---|---|---|---|
| `name` | string | yes | |
| `description` | string | no | 1–1000 chars |
| `scheduled_start_time` | ISO8601 | yes | |
| `scheduled_end_time` | ISO8601 | conditional | **required for `EXTERNAL`** |
| `entity_type` | enum | yes | 1 `STAGE_INSTANCE`, 2 `VOICE`, 3 `EXTERNAL` |
| `entity_metadata` | object | conditional | required for `EXTERNAL`, carries `location` |
| `channel_id` | snowflake | conditional | required for `STAGE_INSTANCE`/`VOICE`; **null** for `EXTERNAL` |
| `privacy_level` | enum | yes | only `GUILD_ONLY` (2) |
| `image` | image data | no | cover image |
| `recurrence_rule` | object | no | recurring events |

**Status enum:** 1 `SCHEDULED`, 2 `ACTIVE`, 3 `COMPLETED`, 4 `CANCELED` —
F5 ("ping when an event is live") keys off the transition to `ACTIVE`, which
arrives as a `GUILD_SCHEDULED_EVENT_UPDATE` gateway event **(inferred)**.

**Limit:** "A guild can have a maximum of **100 events** with `SCHEDULED` or
`ACTIVE` status at any time."

**Permissions:** `EXTERNAL` needs `CREATE_EVENTS`. `STAGE_INSTANCE`/`VOICE`
need `CREATE_EVENTS`, `MANAGE_CHANNELS`, `MUTE_MEMBERS`, `MOVE_MEMBERS`.
Supports `X-Audit-Log-Reason`.

## 7.3 Timestamp styles — HammerTime (F4)

Source: <https://docs.discord.com/developers/reference>. Syntax
`<t:UNIX:STYLE>`, **seconds not milliseconds**; omitting the style defaults to
`f`. Rendered in **each viewer's own local timezone** — which is exactly why F4
should store one UTC instant and let Discord localise it.

| Code | Format | Example |
|---|---|---|
| `t` | Short time | 16:20 |
| `T` | Long time | 16:20:30 |
| `d` | Short date | 20/04/2021 |
| `D` | Long date | April 20, 2021 |
| `f` | Short date/time (**default**) | April 20, 2021 at 16:20 |
| `F` | Long date/time | Tuesday, April 20, 2021 at 16:20 |
| `s` | Compact date + time | 20/04/2021, 16:20 |
| `S` | Compact date + long time | 20/04/2021, 16:20:30 |
| `R` | Relative | 4 years ago |

## 7.4 Privileged intents

Source: <https://docs.discord.com/developers/events/gateway>.

| Intent | Gates | Needed by Black Bloc for |
|---|---|---|
| `GUILD_PRESENCES` | online status / activities | **F1/F2** — streaming detection is presence-based |
| `GUILD_MEMBERS` | member events + `List Guild Members` endpoint | F6 birthday import, F7 join-based automod, autorole |
| `MESSAGE_CONTENT` | `content`, `embeds`, `attachments` on messages — without it these arrive **empty** (exceptions: the app's own messages, and DMs) | F7 automod, F9 honeypot, F11 modmail |

- Under **10,000 servers**: just toggle them on in the Developer Portal's Bot
  settings.
- At or over **10,000**: review required for continued access; approved apps
  re-apply annually. (Discord's older "100 servers" threshold has been
  superseded by the 10,000 figure on this page — do not cite 100.)
- Identifying with an **unapproved** privileged intent closes the gateway with
  code **`4014`**.

---

## Appendix — what could not be documented

| Item | Why |
|---|---|
| TempVoice `help.tempvoice.xyz` docs | HTTP 403 on every path tried; covered instead from `easy.tempvoice.xyz` (also official) |
| TempVoice privacy-mode permission effects, claim conditions, bitrate range, owner-permission list | Not in the vendor's docs |
| Honeypot trigger semantics, exempt/whitelist roles, admin exemption, false-positive handling, permission list | Not in the vendor's docs — checked all six guide pages |
| Carl-bot rendered site (`docs.carl.gg/*`) | 404 on the paths tried; used the docs **source repo** instead |
| Birthday Bot by NoiTheCat | noithecat.dev and noi.dev both HTTP 403 |
| Modmail per-variable configuration list | The vendor **withdrew** the page for factual inaccuracies |
| Which Birthday Bot the server actually runs | Unconfirmed — see §5 identity caveat |
