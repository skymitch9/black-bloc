# Carl-bot dashboard — what it is configured to do for *Black in a Flash!*

> **Audience:** F7 (moderation) and the reaction-roles feature. **Status:**
> TRACKED (2026-08-31; private repo), one-off capture. **Last verified: 2026-08-26 ~17:45 Phoenix** —
> read from `carl.gg/dashboard/1073710702776299640/*` as page text in the
> owner's logged-in browser. ⚠️ Page *text* does not expose toggle/checkbox
> STATES or selected dropdown values; where a value is shown below it was
> literally on the page, otherwise it is marked *unknown*. The owner running
> `!am` in `#mute-me-bot-test-spam` would print the automod state exactly.

## Reaction roles — **5 panels, all in `#roles`, all type `normal`** (the live feature)

| # | Roles offered | Type |
|---|---|---|
| 1 | He/Him, She/Her, He/They, She/They, They/He, They/She, They/Them, It/Its, Ask my pronouns | normal |
| 2 | Speedrunner, Challenge Runner, Score Attacker, Ranked Gamer, Casual | normal |
| 3 | Mentor, Initiate | normal |
| 4 | Sports, Squads, Shows, Musichead, Foodie, RPGer, Randos, QOTW | normal |
| 5 | Marathons | normal |

`normal` = react to get the role, unreact to lose it, any number at once.
Emoji → role mapping and the panel message text were NOT on the list page;
the Discord scan (`discord-scan-2026-08-26.md`) captures the actual messages
in `#roles`.

## Moderation — modlog is live

| Setting | Value on page |
|---|---|
| Modlogs channel | `#carlbot-logs` |
| Send reports to | `#carlbot-logs` |
| Logged events (checkboxes) | Bans, Mutes, Warnings, Tempbans, Hardmutes, Kicks, Unmutes, Unbans, Timeout, Remove Timeout — *which are ticked: unknown* |
| DM-on-punish style (timeout/mute/kick/ban/warn/hardmute/tempban) | options: none / server+action / +reason / +name+moderator / custom — *selection unknown* |
| Default timeout / mute / hardmute / tempban durations, ban purge days | *unknown (numeric fields)* |

## Automod — LIVE STATE from `!am` (owner ran it in `#mute-me-bot-test-spam`, 2026-08-27 00:38 UTC)

| Rule | Setting | Punishment |
|---|---|---|
| **Mentionspam** | 5 mentions / 30 s | **delete, warn, tempmute 5 min** — the only rule that acts |
| Slowmode | 6 msgs / 4 s | none |
| Linkspam | Blacklist mode, 1 / 1 s | none |
| Invitespam | ❌ off (but "Norole mode" ✅ enabled; punishment listed: delete, warn, tempmute 10 min) | inactive while off |
| Bad words | — | none |
| Honeypot | channels: none | none |
| Attachmentspam | no ratelimit | none |
| Caps lock | threshold none | none |
| Warn action | threshold 8 warnings | none |
| Whitelisted roles / channels | none / none | |
| Log channel | none (defaults to modlogs = `#carlbot-logs`) | |
| Drama channel / delete files / media-only | none / off / none | |

**So the F7 baseline to reproduce in shadow mode is one rule:** mass-mention
(5/30s → delete + warn + 5-min timeout), with admins/manage-server immune.
Everything else is Carl scaffolding that was never armed.

## Automod — dashboard sections (values were not readable from page text)

Header note on the page: *"Members with manage server or admin are always
immune."* Sections: General (log channel, drama channel [premium], mute
role = **"No muterole selected"**, allowed channels/categories, allowed roles,
media-only channels, delete scary files), Invitespam, Mentionspam (punish
after N mentions in M seconds), Attachmentspam (**shown "Disabled"**), Caps,
**Honeypot** (Carl has this natively: "Users sending messages in these
channels will automatically trigger the configured punishment" — honeypot
channels: *none shown*), Linkspam (mode dropdown read as **Blacklist**;
blacklisted domains list: *not shown*), Bad words (*list not shown*), Spam
(punish after N messages in M seconds), Warn threshold. Punishment options
everywhere: Delete message / Warn / Tempmute (minutes).

## Logging — appears OFF

Default log channel, member/server/voice/message/join-leave log channels: all
**"No channel selected"**. Event checkboxes exist (deleted/edited/purged
messages; joins/leaves; channel/role/server/emoji changes; role/name/avatar
changes, bans/unbans, timeouts; voice join/move/leave) — states unknown but
with no channel selected nothing is delivered.

## Welcome / Autoroles / Starboard / Tags — not in use

- Welcome channel: **No channel selected**; farewell is premium. Message
  bodies not shown. Carl's own Birthday feature is premium (announcement time
  in UTC hours, birthday role) — the server uses Birthday Bot instead.
- Autoroles: selector empty on page (*state unknown*); sticky-roles toggle
  *unknown*.
- Starboard: **"No starboard found"**.
- Tags: **"No matching records"**.

## What this means for Black Bloc

1. The *live* Carl features are **reaction roles (5 panels)** and the
   **modlog to `#carlbot-logs`** (plus whatever automod rules are on — needs
   `!am`). Everything else on Carl is idle.
2. The full channel list (≈130 channels/categories) is in the logging page's
   dropdown text; the Discord scan has it with IDs.
