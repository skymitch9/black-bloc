# Phase 3 design — temporary voice channels (F8) + honeypot (F9)

> ⚠️ **The temp-voice half's COMMAND SURFACE is superseded by the panel (2026-09-03)** —
> `/voice` is now ONE member-visible command that opens an ephemeral panel, and the
> `tempvoice` and `voice` groups and all twenty-two subcommands below are retired. See
> [`voice-panel-design.md`](voice-panel-design.md). Everything else here — the join-to-create
> behaviour, the per-channel control post (§ below, unchanged), the remembered preferences, the
> honeypot half — still describes what is built.

> **Audience:** the Phase 3 build agent and the reviewer. **Status:** LOCAL
> ONLY. **Last verified: 2026-08-26** — channel IDs from the same-day scan;
> TempVoice behaviour from `reference-bots.md` (vendor docs via
> `easy.tempvoice.xyz/llms.txt`); Honeypot vendor docs never state triggers or
> exemptions, so those are ours by design. Depends on Phase 1 (settings store,
> action log). Both features are greenfield — the scan found no lobby and no
> honeypot channel.

## Owner decisions this implements

- **Temp voice:** one creator channel **"join to create a channel"** in the
  voice area, **directly above "You Still Here?"** (the AFK channel `You
  Still Here?` — id in the scan §A); spawned channels named **`{user}'s
  bloc`** next to the creator; owner control panel; **Member-only** to start.
- **Honeypot:** post → **ban + purge**, **shadow first**; exempt = **all bots
  + staff** (roles that can see the staff channel); log to the log channel.
- Test policy + rollout rule apply.

---

## Part A — temp voice: `cogs/community/tempvoice.py`

Schema v4 (additive):

```sql
CREATE TABLE IF NOT EXISTS tempvoice_channels (
    channel_id INTEGER PRIMARY KEY, guild_id INTEGER NOT NULL, owner_id INTEGER NOT NULL,
    creator_id INTEGER NOT NULL, created_at TEXT NOT NULL, panel_message_id INTEGER
);
CREATE TABLE IF NOT EXISTS tempvoice_prefs (      -- per-user remembered settings (TempVoice does this)
    user_id INTEGER PRIMARY KEY, name TEXT, user_limit INTEGER, locked INTEGER DEFAULT 0, hidden INTEGER DEFAULT 0
);
```

Settings keys: `tempvoice_creator_ids` (list of channel ids), `tempvoice_name_template`
(default `{user}'s bloc`), `tempvoice_allowed_role_id` (default: the `Member`
role id `1073741054563602532`), `tempvoice_mode` (`off|on`, default `on` —
harmless: only creates channels for people who join the creator).

**Flow.** `on_voice_state_update`: member joins a creator channel → if they
lack the allowed role: move them out (back to AFK) and DM one sentence
naming the role; else create a voice channel in the creator's category with
`name_template` (apply their `tempvoice_prefs` if any), position = creator's
position + 1, permission overwrites: owner gets `manage_channels`,
`move_members`, `mute/deafen`; `@everyone` connect stays as the category
says; move the member in; post the **control panel** in the channel's text
chat (voice channels have text). When the last member leaves → delete the
channel and its row. On startup, reconcile: delete rows whose channel is
gone; delete empty channels that have rows.

**Control panel** (persistent `discord.ui.View`, `custom_id`s prefixed
`tempvoice:`), owner-only buttons (others get "this panel belongs to
@owner"): Rename (modal), Limit (modal 0–99), Lock/Unlock (deny `connect` to
`@everyone`), Hide/Show (deny `view_channel`), Kick (user select →
`move_to(None)`), Ban (user select → overwrite deny connect + kick), Permit
(user select → allow connect/view), Claim (only when the owner is no longer
in the channel → transfer to the clicker), Transfer (user select).
Every action → `log_action("tempvoice.<action>")` and updates `tempvoice_prefs`
for name/limit/lock/hide so the next channel remembers.

**Setup commands** (staff): `/tempvoice setup` — creates the creator channel
named "join to create a channel" **directly above the AFK channel** (find
`guild.afk_channel`; if none, above the channel named "You Still Here?";
if neither, at the bottom of the voice area and say so) and stores its id;
`/tempvoice status`; `/tempvoice mode <off|on>`.

**Test mode.** Channel creation/deletion and moves are side effects the guard
cannot see. While `TEST_MODE`: the cog only acts on creator channels whose
category is the test channel's category, OR — simpler and what we do —
**`/tempvoice setup` while TEST_MODE creates the creator channel in the test
channel's category**, and the listener ignores creator channels elsewhere.
The owner tests join-to-create there; going live = re-running setup with the
guard off (it then goes above the AFK channel).

---

## Part B — honeypot: `cogs/moderation/honeypot.py`

Schema v4 (same migration):

```sql
CREATE TABLE IF NOT EXISTS honeypot_hits (
    id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL, message_id INTEGER, content TEXT, at TEXT NOT NULL,
    mode TEXT NOT NULL, action TEXT NOT NULL      -- 'would_ban' | 'banned' | 'exempt'
);
```

Settings keys: `honeypot_channel_ids` (list), `honeypot_mode`
(`off|shadow|on`, default `shadow`), `honeypot_purge_days` (int, default 1),
`honeypot_exempt_role_ids` (list; staff roles are always exempt in addition).

**Flow.** `on_message` in a honeypot channel (ignore the bot's own
messages): if author is a bot, or has a staff role, or an exempt role, or
`manage_guild` → record `exempt`, delete nothing, log `honeypot.exempt`.
Else: **delete the message immediately** in every mode except `off` (a
human reading the channel should never see spam sitting there — this is not
a punishment, it is housekeeping; state this in code-notes). Then: `shadow`
→ log `honeypot.would_ban` with content + a **"Ban now" button** for staff
(one click converts the shadow hit into the real ban — the watch-mode
affordance); `on` → `guild.ban(user, reason="Honeypot: posted in
#<channel>", delete_message_days=purge_days)`, DM the user one sentence
first (best-effort), log `honeypot.banned`.

**Setup** (staff): `/honeypot setup [name]` — creates a text channel (default
`🍯-do-not-post-here`) at the **bottom** of the channel list, `@everyone`
can view + send, slowmode 0, and posts + pins the notice: *"This channel is
a trap for bots. Do not post here — anything posted is treated as spam and
the account is banned."*; stores the id. `/honeypot status`, `/honeypot mode
<off|shadow|on>`, `/honeypot exempt add|remove <role>`.

**Test mode.** While `TEST_MODE`, `/honeypot setup` creates the trap channel
**inside the test channel's category**; bans are refused (logged as
`would_ban`) regardless of mode — the guard cannot see bans, so the cog
checks `bot.guard is None` before ever calling `ban`.

---

## Part C — rider: role-menu follow-ups from the audit (F17, owner 2026-08-26)

Small changes to `cogs/community/role_menus.py`, one commit:

1. **Marathons uses Carl's real custom emoji.** In `SEED`, replace `🎮` with
   `<:JoyGAMING:1337948924844965931>`; `discord.SelectOption(emoji=…)` accepts
   a `PartialEmoji.from_str(...)` — convert in `RoleMenuSelect` when the
   stored emoji string starts with `<`. Store emojis as strings as now.
2. **Staff-assigned menus.** Add a third mode `staff` to `MODES`: the panel
   is NOT posted for self-serve; instead `/rolemenu assign <name> @member`
   and `/rolemenu unassign <name> @member` (staff only) open an ephemeral
   select of that menu's roles and apply the diff to the *target* member,
   logging `role_menu.assign` with actor and target. `post` refuses a
   `staff`-mode menu with a sentence saying what to use instead.
3. **Seed additions:** `runner-status` (mode `staff`): Runner
   `1285361896383320074`, Live Runner `1285365452666699837`, Commentator
   `1285361954860437516`. *Student/Teacher* is already the `mentoring`
   panel; *Rule Reader* is dropped (Discord's rules screen grants `Member`).
   Seed stays idempotent; existing `event-alerts` rows get the emoji fix
   only if the owner re-runs `seed` after deleting that menu (say so in the
   reply — do not silently rewrite options).

Tests: emoji conversion for both plain and custom strings; `staff` mode
refuses `post`; assign/unassign diff on a target member; seed idempotency
with the new menu.

## Tests (offline, mirror the package)

- `tests/cogs/community/test_tempvoice.py`: name rendering; prefs
  round-trip; position computation ("above AFK"); owner-only panel check as
  a pure function; reconcile logic on fake rows/channels.
- `tests/cogs/moderation/test_honeypot.py`: exemption matrix (bot / staff /
  exempt role / manage_guild / plain member); mode matrix → action; test-mode
  refusal; DM + ban call order with a fake guild.
- `tests/storage/test_db.py`: `SCHEMA_VERSION == 4`, new tables exist.

## Definition of done

As Phase 1: green tests, clean ruff, code-notes, architecture tree, two
commits (tempvoice, honeypot) on a clean tree, not pushed. Live verification
by the reviewer's deploy and the owner's test sweep: join the creator channel
in the test category; post in the trap channel with a throwaway account and
read the shadow log line.
---

## 2026-08-27 — the control panel moved into the voice chat

Owner ask, 10:44: *"also lets move the controls for the join to create from the
#test channel into the channel txt of the voice chat that was made like the
other bot does it"*.

Part A above says the panel goes in "the channel's text chat (voice channels
have text)", and `panel_home` has always tried that first. Under `TEST_MODE`
the guard allowed only `TEST_CHANNEL_ID` and DMs, so every panel fell back to
the test channel and the owner never saw the design as written.

**What changed.** `TestModeGuard` now keeps a set of the channel ids Black Bloc
made itself (`owned_channel_ids`), and `allows_channel` treats those as
speakable alongside the test channel and DMs. TempVoice adds an id when it
creates a channel, drops it when the channel is deleted, and rebuilds the set
from `tempvoice_channels` on every reconcile, so panels survive a restart.

**What deliberately did NOT change.**

| Gate | Still |
|---|---|
| `allows_place` (channel create / rename / delete) | the test channel's own category, only |
| `allows_interaction` for slash commands | the test channel, only |
| `may_act_in` (which lobbies the listener honours) | the test channel's category, only |
| the fallback in `panel_home` | a channel Black Bloc did not make still sends its panel to the test channel |

Only **component** interactions gain the allowance, because only the panel's
buttons moved.

**Rider.** A spawned channel now carries an overwrite for the bot itself
(`view_channel`, `connect`, `manage_channels`, `move_members`), the same one
the lobby has always had. Without it a channel created **hidden** from a
member's remembered preferences denies `view_channel` to `@everyone` and the
bot with it, and the panel could never be posted into the channel it belongs
to.

**Not verified:** anything against live Discord. Nobody has watched a panel
appear in a voice chat, pressed a button there, or confirmed that the Bots role
holds **Send Messages** in that category — a voice channel's text chat needs
`view_channel` + `send_messages` the same way a text channel does.
