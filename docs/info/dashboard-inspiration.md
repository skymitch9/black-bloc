# Dashboard inspiration — what the good bot panels do, and three ways we could look

> **Audience:** the owner + the mock builder. **Status:** TRACKED (owner,
> 2026-08-31 — was local-only until then). **Last
> verified: 2026-09-11 09:30** — docs-wide staleness pass. ⚠️ **This is a SURVEY of
> eleven OTHER products' dashboards, captured 2026-08-27 and not re-fetched** — nothing
> in it is a claim about Black Bloc except the "what is wrong with ours today" section,
> which describes the site as it was BEFORE the Direction-A restyle and the R1 pass and
> is therefore history, not a defect list. The only repo paths it cites are
> `/moderation.html` and `/settings.html`, both of which still exist under `site/public/`
> (17 pages there today). ⚠️ **NOT re-checked:** no external dashboard was re-visited,
> so every observation about Carl, YAGPDB, MEE6, Dyno, Wick, ProBot, Sapphire, Discord,
> Linear, Vercel or Cloudflare is a 2026-08-27 reading.
> ℹ️ The restyle this doc fed has SHIPPED: **Direction A** was chosen and
> deployed 2026-08-27 (`666dd8e`), with the theme dropdown kept, and the **A/C-hybrid R1
> pass** landed 2026-08-31 (`0c49257`) — see [`site-restyle-design.md`](site-restyle-design.md).
> The four open owner questions in §7 are therefore answered by those builds, not still open.
> Before that, **2026-08-27** (STATUS line only re-checked 2026-08-31) — every
> observation cites its page.

Owner's ask, verbatim (2026-08-27 ~08:40): *"It's still not quite the look and
feel I want. Can you research some other bot sites for inspiration and then make
a mock."* This is step 1 of 3 (research → canvas mock → restyle brief).

**How to read this in five minutes:** §1 is why ours feels off. §2 is the
one-line verdict per site. §4 is the three directions — read the identity
paragraph and the palette, skip the wireframes unless you want them. §6 is the
recommendation. §7 is the four questions only you can answer.

**Marking:** *(observed)* = I looked at the page myself on 2026-08-27 and the
URL is cited. *(observed, marketing render)* = a screenshot the vendor published
of their own product, not the live product. *(inference)* = my read, not a
measurement.

---

## 1. What is actually wrong with ours today

Read from the live site, signed in, 2026-08-27 (`https://blackbloc.heygabi.ai/`,
`/settings.html`, `/moderation.html`) *(observed)*:

| Symptom | What causes it | The fix direction |
|---|---|---|
| **Half the screen is empty.** On a 1512px window the Overview ends 340px down; content sits in a ~600px column with ~400px of dead black to its right. | One-column body inside `max-width:78rem`, no grid, sections collapsed by default. | A real grid: 2-up cards on wide screens, and a page that fills its width. |
| **Settings reads like a database dump.** Each row's title is the raw key — `log_channel_id`, `role_menu_channel_id` — with a `CHANNEL` type badge under it. 48 of them. | The key registry is being rendered directly. | Human labels ("Log channel"), key shown small/mono as a secondary line for the people who want it. |
| **Two buttons per field × 48 fields.** Every key has its own `Save` and `Clear`. | Save-per-field. | One page-level save bar that appears only when something is dirty (Discord's pattern), or optimistic save + inline "Saved ✓". |
| **No page identity or context.** No top bar, no server name/avatar, no "signed in as" chip except a sentence in the subtitle, no bot-health dot. | The shell is a rail + a body, nothing else. | A top bar: server picker (even with one server it anchors the page), bot status dot, user avatar, theme control. |
| **Everything has the same visual weight.** Chips, cards, buttons, sub-nav links are all outlined rectangles in cyan/yellow on black. | Borrowed theme (cyberpunk) whose accent grammar is decoration, not hierarchy. | One accent reserved for *interaction*; status colour reserved for *status*; everything else greyscale. |
| **Display type shouts, UI type whispers.** `SETTINGS` renders ~2.5rem neon yellow Rajdhani; the controls under it are 14px muted grey. | `--et-text-title` clamp + `--et-heading-color` from the audiobook-site theme. | Page titles ~20–24px, body 14–15px, and let density carry the seriousness. |
| **It looks like a template wearing a bot.** | It literally is: `estate-theme.css` is a snapshot of the heygabi estate themes (`phase8-design.md` decision 2). | The snapshot is replaceable — that is the owner's stated call. |

**The bones are good.** The state machine, name resolver, tab rail, in-page
sub-nav with counts, collapsible sections, per-table search and remembered
tab/sections are all correct and all three directions below keep them. What is
wrong is *skin, density and hierarchy* — not structure.

---

## 2. The survey — one line each

| Site | Reachable? | The one thing to steal |
|---|---|---|
| **Carl-bot** `carl.gg/dashboard/<guild>/…` | Yes, live, owner logged in | Two-column masonry of module cards, each with its own Save; unit-suffixed number inputs; a live "Example:" preview under the DM-style select. |
| **YAGPDB** `yagpdb.xyz/manage/<guild>/…` | Yes, live, owner logged in | **Enable toggle at the top of every module page**, and **tabs inside the page** (General / Timeout / Mute / Kick / Ban / Warnings) with a red dot on the ones that are off. |
| **MEE6** `mee6.xyz/en` | Marketing only (dashboard needs login) | Plugin *grouping* language: Server management · Utilities · Social Alerts · Engagement & Fun · AI Characters. |
| **Dyno** `dyno.gg` | Marketing only; dashboard seen as a laptop mockup | Overview = server info + recent activity + a **Modules** section with its own search box. |
| **Wick** `wickbot.com` | Marketing only; full dashboard shown as a hero render | Overview as **module cards with a toggle and a SETTINGS link on each**, plus a "security score" ring. Rail carries the server banner. |
| **ProBot** `probot.io` | Marketing only | Blurple-on-black, centred nav, "NEW: Tickets Module" pill. Nothing structural. |
| **Sapphire** `sapph.xyz` | Marketing only (dashboard at `dashboard.sapph.xyz` needs login) | The **cases screen**: breadcrumb header, one search box, a row of checkbox filters, table, and a **detail drawer** with an Actions bar (Edit/Close/Delete). |
| **Discord server settings** | Yes, via `support.discord.com` article attachment | Grouped text-only sidebar; numbered steps; **docked save bar** — "Currently Editing … Cancel / Save Changes". |
| **Linear** `linear.app` | Yes | Monochrome + colour only as *status dots*; 13px type; hairline separators; ID eyebrow on every row. |
| **Vercel / Geist** `vercel.com/geist/*` | Yes | The token system: 2 backgrounds, Colors 1–3 = default/hover/active, 10-step scales per hue. Search box with a `Ctrl K` hint in the rail head. |
| **Cloudflare dashboard** `dash.cloudflare.com` | Yes, owner logged in | The best table in the survey: search + Filters + Display options + Export + one primary button; a quota sentence; `—` for empty cells; per-row text actions. And it is **light-first**. |

---

## 3. The patterns worth copying, with citations

### 3.1 Layout skeleton

- **Carl** *(observed, `carl.gg/dashboard/1073710702776299640/automod`)*: fixed
  ~230px dark rail; a top bar with the product logo + horizontal links (Docs,
  Invite, Discord, Status, Games, Discover) + a gold `Premium` pill + server
  avatar dropdown + user avatar dropdown; content is **full-bleed** (no max
  width) laid out as two columns of independent cards. A promo banner sits above
  the content.
- **YAGPDB** *(observed, `yagpdb.xyz/manage/1073710702776299640/streaming`)*:
  ~180px rail headed by the word "Navigation" and a collapse icon; top bar is
  icon-only on the right (premium, ideas, docs, changelog, help, alerts) plus a
  **server chip** ("Black in … / Change s…") and a user chip. Content is one
  panel with a title strip above it.
- **Wick** *(observed, marketing render, `wickbot.com` hero)*: rail is headed by
  the **server's banner art with its icon and name**, then nav; top bar is
  icon-only (language, bell, light/dark, avatar). Content is centred with an
  eyebrow ("OVERVIEW") over the server name.
- **Cloudflare** *(observed, `dash.cloudflare.com/…/heygabi.ai/dns/records`)*:
  ~157px rail, account switcher at its head, `Quick search… Ctrl K` under it,
  then grouped items; content max-width ~970px centred with a page header,
  toolbar, table, footer. Rail collapse button bottom-left.

**Take:** rail 200–240px, a real top bar, content that fills the width with a
grid rather than a single column. Ours has the rail and nothing else.

### 3.2 Navigation

- **Carl** *(observed)*: 8 collapsible groups (SETTINGS, SERVER DISCOVERY,
  PREMIUM, MODERATION, ROLES, CUSTOM COMMANDS, NOTIFICATIONS, UTILITY); only the
  open one shows leaves (Automod / Moderation / Logging), each leaf with a small
  icon; active leaf = lighter fill.
- **YAGPDB** *(observed)*: same idea, icons on the groups (Core, Custom Commands,
  Moderation, Notifications & Feeds, Roles, Tools & Utilities, Fun) and a
  standalone Documentation link at the bottom; active leaf is blue text.
- **Wick** *(observed, marketing render)*: flat items first (Wizard, Overview,
  Miscellaneous, Permits, Appeals) then collapsible feature groups (Auto Mod,
  Anti Nuke, Server Joins). Active = filled magenta pill.
- **Discord** *(observed, `support.discord.com/hc/article_attachments/12974312213271`)*:
  **no icons at all** — uppercase muted group captions (ORCHARD ESPORTS, APPS,
  MODERATION, COMMUNITY, MONETIZATION) with a hairline between groups, plain
  text rows, active = filled grey row.
- **Cloudflare** *(observed)*: group captions (Observe, Build, Protect &
  connect), one thin icon per item, `>` disclosure on expandable ones, and a
  **Recents** group whose rows are two lines (item + where it lives).

**Take:** 13 flat tabs (ours) is past the point where a flat list works. Group
them — 4 groups of 3–4 — and the rail stops being a wall. Everyone groups.

### 3.3 How a module page is composed

- **Enable toggle in the page header.** YAGPDB puts a large green `Enable` pill
  switch at the top of the panel, above the description *(observed, streaming
  page)*. Wick puts the toggle on the overview card instead *(observed,
  marketing render)*. Discord puts a green check-toggle beside the rule name
  *(observed)*.
- **Tabs inside the page.** YAGPDB's Moderation tools page has `General ·
  Timeout • · Mute • · Kick • · Ban • · Warnings •` where the red dot means "this
  sub-feature is disabled" *(observed, `/manage/…/moderation`)*. That is a
  better answer to "too many inputs per page" than our accordion, because it
  hides *and* reports state.
- **Cards, one per concern, each with its own Save.** Carl: General Settings /
  Invitespam / Honeypot / Linkspam / Bad words, each a card with a blue Save at
  its foot *(observed)*.
- **Numbered steps.** Discord's AutoMod rule: `1 Select the type of language`,
  `2 Choose a response`, `3 Allow certain roles or channels (optional)`, each a
  rounded panel of titled checkbox rows *(observed)*.
- **Breadcrumb + drawer.** Sapphire: header reads `Moderation › Cases`, and
  opening a case slides a panel titled `Moderation › Cases › <id>` with an
  Actions bar (Edit / Close / Delete) over a General-information key–value list
  *(observed, marketing render, `sapph.xyz`)*.

### 3.4 Form density and control style

| Control | Who does it | Note |
|---|---|---|
| Pill switch, green = on / red = off | YAGPDB *(observed)*, Wick *(observed, render)* | Colour carries state; the label sits to the right of the switch. |
| Green check-toggle + `⋮` overflow | Discord *(observed)* | The overflow menu is where "delete rule" hides. |
| Blue square checkbox in a titled row (**Title** + muted description + checkbox right) | Discord *(observed)* | Far more readable than a bare checkbox list. |
| Checkbox list as full-width striped rows | Carl moderation "Logged events" *(observed)* | 10 rows, one per event kind. |
| Multi-select as removable chips inside the field (`× Delete message` `× Warn` `× Tempmute`) | Carl *(observed)* | This is what our "actions" arrays should look like. |
| Number + unit suffix pill (`10` `Minutes`, `1` `Links in` `1` `Seconds`) | Carl *(observed)* | Kills the "what unit is this?" question. |
| Tag chip inside a search field (`# mod-logs ×  Search channels or roles`) | Discord *(observed)* | Our channel/role pickers should be this. |
| Live example under the control (`Example: You were warned in CBH. Reason: …`) | Carl *(observed)* | We already have a template preview on Go-live; generalise it. |
| Save: **one bar per card** | Carl *(observed)* | Simple, but 6 cards = 6 saves. |
| Save: **one bar per page**, full-width blue, at the foot | YAGPDB *(observed, "Save Streaming Settings")* | |
| Save: **docked bar that appears when dirty** — `Currently Editing "…" Rule   Cancel   [Save Changes]` | Discord *(observed)* | The best of the three: no button until there is something to save. |
| Save: **none** — inline commit | Cloudflare DNS rows *(observed)*, Linear | Each row edits in place; the list is the truth. |

### 3.5 Tables

Cloudflare's DNS table is the reference *(observed)*:

```
DNS records for heygabi.ai                        [DNS Setup: Full] [ DNS documentation ]
Manage how the Internet finds your web content…

┌ Recommendations ⓘ ───────────────────────────────────────────────────────── ^ ┐
│ • Email cannot reach @heygabi.ai addresses and they could be spoofed          │
└───────────────────────────────────────────────────────────────────────────────┘

[ Search DNS Records            ] [⚙ Filters] [Display options] [Import] [Export] [+ Add record]
You have used 17 of 200 available DNS records in this domain.
┌───┬──────────────────┬──────┬───────────────────────┬──────────────┬──────┬──────┐
│ ☐ │ Name ⓘ ⇅         │ Type │ Content ⓘ             │ Proxy status │ TTL  │      │
│ ☐ │ **blackbloc**.heygabi.ai │ A │ 66.241.125.10   │ ☁ DNS only   │ Auto │ Edit │
└───┴──────────────────┴──────┴───────────────────────┴──────────────┴──────┴──────┘
Showing 1–17 of 17
```

Details that make it feel expensive: the bold/muted split inside one cell
(`**blackbloc**.heygabi.ai`), `—` in every empty cell instead of blank, `ⓘ`
tooltips on the headers, a lock glyph on rows you may not edit, a quota
sentence, and a row count footer. Sapphire adds an inline checkbox filter row
and a `Mass edit` pull-out *(observed, render)*. Carl adds `5 records` centred
under the table and a green `+ Create new reaction role` above it *(observed)*.

### 3.6 Colour

| Site | Ground | Surface | Accent | Status |
|---|---|---|---|---|
| Carl *(observed)* | very dark slate | slightly lighter slate | bright blue Save, green "create", gold Premium, indigo promo banner | punishment chips inherit accent |
| YAGPDB *(observed)* | near-black | dark grey panel | material blue | green = enabled, red = disabled, red mono for command syntax |
| Wick *(observed, render)* | purple→blue photographic gradient | near-black cards | magenta/pink | green toggles, orange gauge |
| Dyno *(observed)* | near-black | dark card | crimson `#e0304d`-ish | red buttons |
| ProBot *(observed)* | near-black w/ violet haze | — | Discord blurple | — |
| Sapphire *(observed)* | dark navy-slate | lifted slate | cyan→blue gradient | green/blue/red action buttons |
| Discord *(observed)* | `#313338` / `#2b2d31` / `#1e1f22` | grey panels | blurple `#5865F2` | green check, blurple links |
| Linear *(observed)* | `#08090a` | hairline-outlined | almost none | colour lives **only** in status/label dots |
| Cloudflare *(observed)* | **white** | white + hairline | blue | red/green delta arrows, orange logo only |

**The premium/cheap line** *(inference, but consistent across all eleven)*:
cheap = many saturated hues doing decoration (Wick's gradient, our yellow+cyan);
premium = one accent doing interaction, greyscale doing structure, and saturated
colour reserved for *state* (Linear, Cloudflare, Discord). Wick is the outlier —
loud and popular — but its loudness is in the *marketing render*, and its cards
are still near-black with one accent.

### 3.7 Typography

- Linear *(observed)*: ~13px UI, ~11px mono micro-labels (`FIG 0.1`, `ENG-928`),
  headings that are only ~2× body. Tight.
- Cloudflare *(observed)*: 14px body, ~24px page title, one weight step.
- Discord *(observed)*: 16px rule name field, 14px row titles, 12px descriptions.
- Carl *(observed)*: a large ~28px card title *inside* a card that already has a
  ~12px header strip with the same name — a duplication we should not copy.

**Take:** our `--et-text-title` (clamp up to 2.5rem) is roughly 2× everyone
else's page title. Nobody in this survey uses display type in a control panel.

### 3.8 Empty and loading states

- Cloudflare: `—` per empty cell, plus "No data" written inside an empty
  sparkline *(observed)*.
- Carl: `5 records` under the table; an empty table would still show its header
  *(observed)*.
- YAGPDB: a dismissible info banner naming the permissions the plugin uses, and
  inline warnings in the body ("stream announcements are the most unreliable
  feature on this bot") *(observed)*.
- Nobody in the survey showed a skeleton loader *(observed — but I only saw
  loaded pages, so this is not evidence they lack them)*.

---

## 4. Three candidate directions

All three keep, unchanged: the **five-state permission machine**, the **name
resolver** (never show a snowflake), the **left tab rail + in-page sub-nav**,
**collapsible sections with counts**, **per-table search**, **remembered tab and
section state**, self-hosted fonts, no framework, and the `--et-*` token
contract (a direction is a new token file, not new page code).

### A — "Discord-native"

**Identity.** It looks like the fourth tab of Discord's own Server Settings, so
a mod who has clicked "Server Settings → AutoMod" a hundred times already knows
where everything is. Text-only grouped sidebar, no icons, grey panels on a
grey-black ground, blurple only on links and the primary action, green only on
toggles and Save. Nothing is styled to be noticed; the content is the design.
Its risk is that it has no personality of its own — it reads as an extension of
Discord rather than as *our* bot.

**Components.** Grouped text sidebar · page header (title + one-line
description + overflow `⋮`) · numbered step panels · titled checkbox rows
(**Title** / muted description / blue checkbox) · green pill toggle + `⋮` per
rule · tag-chips inside search fields for channel/role pickers · collapsed rule
summary rows with action chips · **docked save bar that appears only when
dirty** · modal confirms for destructive actions.

**Palette.**

| Token | Dark | Light |
|---|---|---|
| `--et-bg` | `#1E1F22` | `#F2F3F5` |
| `--et-bg-2` | `#2B2D31` | `#FFFFFF` |
| `--et-surface` | `#313338` | `#FFFFFF` |
| `--et-hairline` | `#3F4147` | `#E3E5E8` |
| `--et-fg` | `#F2F3F5` | `#060607` |
| `--et-muted` | `#B5BAC1` | `#4E5058` |
| `--et-accent` (interaction) | `#5865F2` | `#5865F2` |
| `--et-accent-fg` | `#FFFFFF` | `#FFFFFF` |
| `--et-ok` | `#23A55A` | `#1A6334` |
| `--et-warn` | `#F0B132` | `#B4841D` |
| `--et-danger` | `#F23F43` | `#D22D30` |
| `--et-info` | `#00A8FC` | `#0069A8` |

**Type.** `Inter` 400/500/600/700 (self-hosted woff2, OFL) for everything —
Discord's `gg sans` is proprietary and Inter is its closest legal neighbour;
`JetBrains Mono` 400 for ids, keys and templates. Scale: 12 / 14 / 16 / 20 / 24.

**Wireframes.**

```
OVERVIEW ─────────────────────────────────────────────────────────────────────
┌──────────────┬──────────────────────────────────────────────────────────────┐
│ BLACK BLOC   │  ● online · 4d 6h   Black in a Flash!            [ISky ▾] ⚙  │
│              ├──────────────────────────────────────────────────────────────┤
│ OVERVIEW     │  Overview                                                    │
│  Home        │  Every feature's mode, what's open, the last ten actions.     │
│  Health      │  ┌─ Features ─────────────────┐ ┌─ Open now ────────────────┐ │
│              │  │ Moderation      ● On    ›  │ │ Modmail tickets      3    │ │
│ MODERATION   │  │ Automod         ◐ Shadow › │ │ Events pending       1    │ │
│  Cases       │  │ Go-live         ● On    ›  │ │ Honeypot hits (24h)  0    │ │
│  Automod     │  │ Birthdays       ◐ Shadow › │ │ Warnings (7d)        1    │ │
│  Modmail     │  │ Honeypot        ◐ Shadow › │ └───────────────────────────┘ │
│  Audit       │  │ Temp voice      ● On    ›  │ ┌─ Last 10 actions ─────────┐ │
│              │  │ Modmail         ⬤ Channel ›│ │ 08:41 warn  Sky → Bob     │ │
│ COMMUNITY    │  └────────────────────────────┘ │ 08:38 would_ban  … → Eve  │ │
│  Go-live     │                                 │ …                 [All ›] │ │
│  Events      │                                 └───────────────────────────┘ │
│  Role menus  │                                                               │
│  Birthdays   │                                                               │
│  Temp voice  │                                                               │
│              │                                                               │
│ SERVER       │                                                               │
│  Settings    │                                                               │
│  Access      │                                                               │
└──────────────┴───────────────────────────────────────────────────────────────┘

MODERATION ───────────────────────────────────────────────────────────────────
│  Moderation                                                         ⋮       │
│  Cases, and the same actions the slash commands take.                       │
│  ┌ Take an action ─────────────────────────────────────────────────────────┐│
│  │ 1  Who       [ 🔍 type part of a name…            ] (no member yet)     ││
│  │ 2  What      ( ) warn  (•) timeout  ( ) kick  ( ) ban  ( ) unban        ││
│  │              For [ 10 ][ Minutes ▾ ]                                    ││
│  │ 3  Why       [ the member is told this…                              ]  ││
│  │              Preview: "You were timed out in Black in a Flash! …"       ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│  ┌ Cases  8 ───────────────────────────────────────────────────────────────┐│
│  │ [ 🔍 case id / member / reason ]  ☑Warns ☑Timeouts ☑Bans  ☐Only open    ││
│  │ #  Kind     Member      Reason           Moderator   When     ›         ││
│  │ 8  ● warn   Bob         Mass mention     Sky         2h ago   ›         ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│ ▓ Careful — you have unsaved changes.        [ Cancel ] [ Save Changes ]  ▓ │  ← only when dirty
```

```
SETTINGS ─────────────────────────────────────────────────────────────────────
│  Settings                                                                   │
│  [ 🔍 filter 48 keys… ]                                    48 keys · 7 groups│
│  ┌ Core ───────────────────────────────────────────────────────────────────┐│
│  │ Log channel                              [ # black_bloc-logs  ▾ ] ││
│  │ where Black Bloc posts what it did         core.log_channel_id          ││
│  │ ─────────────────────────────────────────────────────────────────────── ││
│  │ Staff channel                            [ # black_bloc-logs  ▾ ] ││
│  │ whoever can see it can see this dashboard  core.staff_channel_id        ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│  ┌ Automod  7 ▸ ┐  ┌ Birthdays  6 ▸ ┐  ┌ Events  7 ▸ ┐  (collapsed groups)  │
│ ▓ 2 changes pending                          [ Cancel ] [ Save Changes ]  ▓ │
```

**What changes vs today:** raw keys become labels (key demoted to a mono
sub-line); per-field Save/Clear buttons disappear in favour of the docked bar;
the 13 flat tabs become 4 groups; the theme dropdown moves into the top-bar cog;
display type disappears.

---

### B — "Ops console"

**Identity.** A control room, not a website. Near-black, one accent, 13–14px
type, hairlines instead of cards, tables instead of forms wherever a table will
do, and `Ctrl K` opens a command palette that can reach every setting and every
action by name ("timeout", "go-live channel", "case 7"). It is the densest of
the three: the whole Overview fits above the fold and Settings is a filterable
list, not a stack of panels. It is aimed at the two or three people who use this
weekly; it will feel austere to someone who opens it twice a year.

**Components.** Rail with a search field at its head (`Search  ⌘K`) · grouped
nav, one thin icon per item · page header = title + description + one primary
button + secondary text actions · **toolbar row** (search · filters · display
options · export · primary) · hairline tables with `—` for empty cells, tooltip
`ⓘ` headers, per-row text actions · right-hand **detail drawer** rather than a
new page · inline editing with optimistic save + a 2-second "Saved ✓" · stat
tiles with number + delta chip + sparkline · keyboard: `/` focus search, `j/k`
row, `Enter` open, `Esc` close drawer, `⌘K` palette.

**Palette.**

| Token | Dark | Light |
|---|---|---|
| `--et-bg` | `#0A0A0B` | `#FFFFFF` |
| `--et-bg-2` | `#121214` | `#FAFAFA` |
| `--et-surface` | `#161618` | `#FFFFFF` |
| `--et-hairline` | `#26262A` | `#E4E4E7` |
| `--et-fg` | `#EDEDEF` | `#09090B` |
| `--et-muted` | `#A1A1A6` | `#71717A` |
| `--et-accent` | `#3B82F6` | `#1D4ED8` |
| `--et-accent-fg` | `#FFFFFF` | `#FFFFFF` |
| `--et-ok` | `#3FB950` | `#1A7F37` |
| `--et-warn` | `#D29922` | `#9A6700` |
| `--et-danger` | `#F85149` | `#CF222E` |
| `--et-info` | `#58A6FF` | `#0969DA` |

**Type.** `Geist Sans` 400/500/600 + `Geist Mono` 400 (both OFL, on Google Fonts,
self-hostable) — or `Inter` + `JetBrains Mono` if we want to reuse one family
across directions. Scale: 11 (mono micro-labels) / 13 / 14 / 16 / 22. One weight
step for emphasis, never a size jump.

**Wireframes.**

```
OVERVIEW ─────────────────────────────────────────────────────────────────────
┌────────────────┬────────────────────────────────────────────────────────────┐
│ ◆ Black Bloc ▾ │ Overview                                    ● healthy 4d6h │
│ [ Search  ⌘K ] │ ──────────────────────────────────────────────────────────  │
│                │  cases 7d   modmail open   events pending   honeypot 24h    │
│ ⌂ Overview     │      3 ↑2         3 →           1 ↑1            0 →         │
│ ⛨ Moderation   │   ▁▂▁▄▁▁▂       ▁▁▂▂▁▁▁       ▁▁▁▁▁▂▁        ▁▁▁▁▁▁▁       │
│ ⚙ Automod      │ ──────────────────────────────────────────────────────────  │
│ ✉ Modmail      │  FEATURE      MODE     CHANGED        BY          ›         │
│ ◷ Events       │  moderation   ● on     2d ago         Sky         ›         │
│ ▶ Go-live      │  automod      ◐ shadow 2d ago         Sky         ›         │
│ ☰ Role menus   │  go-live      ● on     6h ago         Sky         ›         │
│ ⚑ Birthdays    │  birthdays    ◐ shadow 2d ago         —           ›         │
│ ♪ Temp voice   │  honeypot     ◐ shadow 2d ago         —           ›         │
│ ⌗ Honeypot     │  tempvoice    ● on     2d ago         Sky         ›         │
│ ─────────────  │  modmail      ⬤ channel 2d ago        Sky         ›         │
│ ⚙ Settings     │ ──────────────────────────────────────────────────────────  │
│ ▤ Audit        │  RECENT                                        [ all → ]    │
│ ♥ Health       │  08:41:02  warn        Sky → Bob      mass mention          │
│                │  08:38:11  would_ban   — → Eve        honeypot #trap        │
└────────────────┴────────────────────────────────────────────────────────────┘

MODERATION ───────────────────────────────────────────────────────────────────
│ Moderation › Cases                                        [ + Take action ] │
│ [ 🔍 case id / member / reason ] [Filters ▾] [Columns ▾] [Export]           │
│ 8 cases · 1 open                                                            │
│  #   KIND     MEMBER    REASON          MODERATOR  DURATION  WHEN      ⋯    │
│  8   ● warn   Bob       Mass mention    Sky        —         2h ago    ⋯    │
│  7   ◐ would  Eve       Honeypot #trap  —          —         2d ago    ⋯    │
│                                        ┌── Case 8 ──────────────── × ──┐    │
│                                        │ [Edit] [Close] [Delete]        │    │
│                                        │ State     ● open               │    │
│                                        │ Member    Bob            ⧉      │    │
│                                        │ Reason    Mass mention          │    │
│                                        │ Created   2026-08-25 08:41      │    │
│                                        │ DM sent   yes  · view text ›    │    │
│                                        └────────────────────────────────┘    │
```

```
SETTINGS ─────────────────────────────────────────────────────────────────────
│ Settings                                          48 keys · 3 changed today │
│ [ 🔍 filter…            ] [ Group: all ▾ ] [ ☐ only changed ]               │
│  KEY                    VALUE                              DEFAULT   SET BY │
│  core.log_channel_id    [ # black_bloc-logs    ▾ ]   —         Sky    │
│  core.staff_channel_id  [ # black_bloc-logs    ▾ ]   —         Sky    │
│  automod.mode           [ shadow ▾ ]                       off       Sky    │
│  automod.mention_limit  [ 5 ] per [ 30 ] s                 5/30      —      │
│  golive.channel_id      [ # live-now                 ▾ ]   —         Sky    │
│                                                    ↑ edits commit on blur,  │
│                                                      "Saved ✓" for 2s       │
```

**What changes vs today:** the accordion mostly goes away (a table does not need
folding); Settings becomes one filterable list with the group as a column, not
seven collapsible cards; every table gains a toolbar; a drawer replaces
in-page expansion; keyboard shortcuts become a documented feature.

---

### C — "Cookout"

**Identity.** Black in a Flash! is a speedrunning community, and the bot's
status already says *"Cookout attendees"*. This direction leans into that: warm
charcoal instead of blue-black, ember orange as the accent, a chunky display
face used **only** for page titles and the wordmark, generous rounded cards, and
copy with a voice ("Nothing's on fire." as the empty state for the action log).
It is still a control panel — the tables, the toggles and the save bar are the
same as A — but it feels like it belongs to this server rather than to Discord
or to a devops vendor. Its risk is that warmth reads as unserious next to a
`Ban` button, so the destructive path stays cold and plain.

**Components.** Everything in A, plus: a wordmark lockup in the rail head ·
section headers in the display face at 20px (never larger) · mode pills as
rounded "badges" (ON / SHADOW / OFF) · a "what happened today" strip on the
Overview written as sentences, not counters · illustrated-but-flat empty states
(one line of copy + one action) · a subtle warm grain on the page ground only
(`--et-bg-texture`, already in the token vocabulary). Destructive dialogs are
plain, cold and typed-confirmation for bans.

**Palette.**

| Token | Dark | Light |
|---|---|---|
| `--et-bg` | `#17110E` | `#FFF7EC` |
| `--et-bg-2` | `#1E1613` | `#FFFFFF` |
| `--et-surface` | `#241A16` | `#FFFFFF` |
| `--et-hairline` | `#3A2A22` | `#E8D8C4` |
| `--et-fg` | `#FBF3E9` | `#231710` |
| `--et-muted` | `#C0A897` | `#6E584A` |
| `--et-accent` (ember) | `#FF7A18` | `#C2500B` |
| `--et-accent-2` (flame) | `#FFC93C` | `#B57C00` |
| `--et-accent-fg` | `#1A0F08` | `#FFFFFF` |
| `--et-ok` | `#7CC04B` | `#3F7D20` |
| `--et-warn` | `#FFC93C` | `#9A6B00` |
| `--et-danger` | `#F0603C` | `#C13B1F` |
| `--et-info` | `#69B7E0` | `#1668A5` |

**Type.** Display `Bricolage Grotesque` 700 or — free, already on disk —
`Bangers`/`Luckiest Guy` (OFL, self-hosted in `assets/fonts/`) for the wordmark
and page titles only; UI `Figtree` 400/500/700 (OFL) or `Inter`; mono
`Space Mono` 400 or the already-present `Share Tech Mono`. Scale: 12 / 14 / 16 /
20 / 26. **Rule: the display face never appears below 20px and never inside a
control.**

**Wireframes.**

```
OVERVIEW ─────────────────────────────────────────────────────────────────────
┌────────────────┬────────────────────────────────────────────────────────────┐
│  ⚡ BLACK BLOC │  Black in a Flash!            ● up 4d 6h        [ISky ▾] ⚙ │
│                ├────────────────────────────────────────────────────────────┤
│  Overview      │  TODAY                                                      │
│                │  Nothing's on fire. 1 warning, 3 open modmails,             │
│  ── RUNS THE   │  1 event waiting on a Lead.                                 │
│     SERVER ──  │                                                             │
│  Moderation    │  ┌ Moderation ──────────┐ ┌ Automod ─────────────┐          │
│  Automod       │  │  ● ON                │ │  ◐ SHADOW            │          │
│  Modmail       │  │  8 cases · 1 open    │ │  7 rules · 0 armed   │          │
│  Honeypot      │  │            [ open › ]│ │            [ open › ]│          │
│                │  └──────────────────────┘ └──────────────────────┘          │
│  ── RUNS THE   │  ┌ Go-live ─────────────┐ ┌ Events ──────────────┐          │
│     COOKOUT ── │  │  ● ON  #live-now     │ │  ● ON · 1 pending    │          │
│  Go-live       │  │  4 live this week    │ │            [ open › ]│          │
│  Events        │  └──────────────────────┘ └──────────────────────┘          │
│  Role menus    │                                                             │
│  Birthdays     │  LAST TEN THINGS THE BOT DID                    [ all › ]   │
│  Temp voice    │  08:41  warned Bob — mass mention — by Sky                  │
│                │  08:38  would have banned Eve — honeypot                    │
│  ── THE DESK ──│                                                             │
│  Settings      │                                                             │
│  Audit · Health│                                                             │
└────────────────┴────────────────────────────────────────────────────────────┘

MODERATION ───────────────────────────────────────────────────────────────────
│  MODERATION                                          Moderation is ● ON  ⏻  │
│  Same actions as the slash commands, same case book.                        │
│  ┌ Take an action ─────────────────────────────────────────────────────────┐│
│  │  Who  [ 🔍 type part of a name…                    ]                    ││
│  │  Do   ( ) warn  (•) time out  ( ) kick  ( ) ban  ( ) unban              ││
│  │       for [ 10 ] [ minutes ▾ ]                                          ││
│  │  Why  [ the member is told this…                                     ]  ││
│  │       They'll see: "You were timed out in Black in a Flash! …"          ││
│  │                                                       [ Do it ]         ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│  ┌ The case book  8 ───────────────────────────────────────────────────────┐│
│  │ [ 🔍 name, reason or case number ]   ☑ warns ☑ timeouts ☑ bans          ││
│  │ #8  ● warn     Bob    Mass mention     by Sky      2h ago      ›        ││
│  └─────────────────────────────────────────────────────────────────────────┘│

SETTINGS ─────────────────────────────────────────────────────────────────────
│  SETTINGS                                              48 knobs, 7 groups   │
│  [ 🔍 what are you looking for? ]                                           │
│  ┌ The basics  5 ──────────────────────────────────────────────────────────┐│
│  │  Where the bot writes its log     [ # black_bloc-logs        ▾ ]  ││
│  │  Who counts as staff              [ # black_bloc-logs        ▾ ]  ││
│  │  What the bot's status says       [ Cookout attendees                ]  ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│  ┌ Moderation  7 ▸ ┐ ┌ Birthdays  6 ▸ ┐ ┌ Go-live  9 ▸ ┐ ┌ Cookout  7 ▸ ┐   │
│  ▓ 2 changes waiting            [ Never mind ]  [ Save it ]  ▓              │
```

**What changes vs today:** groups get human names ("Runs the server" / "Runs the
cookout" / "The desk"); settings get sentence labels; the Overview leads with a
sentence rather than a chip grid; the neon-on-black palette is replaced by warm
charcoal; display type is capped at 26px and banned inside controls.

---

## 5. What every direction must fix regardless of which one wins

1. **Human labels everywhere**; the raw key survives as a small mono sub-line.
2. **One save mechanism per page**, not per field. (A/C: docked dirty-bar.
   B: inline commit.)
3. **A top bar** with server name, bot health dot, signed-in user, theme cog.
4. **Fill the width**: a 2-up grid over ~1100px, single column under it.
5. **Sub-features report their state in the navigation** — YAGPDB's red dot on
   the tab, or a mode pill in the rail — so "what is off?" is answerable without
   opening seven pages.
6. **Empty cells get `—`, empty tables get a sentence and an action**, never a
   blank box.
7. **Destructive actions look different from Save** and, for bans, ask for a
   typed confirmation. (Ours already tints the border; keep that.)
8. **Cap the title size** and drop display type from controls.

---

## 6. Recommendation

**Build A ("Discord-native") as the shell, and take B's table furniture and
command palette inside it. Keep C on the shelf for the marketing/landing page.**

Why:

- The audience is *this server's* mods — the people the design must not confuse
  are Aunties/Uncles and above, and they already know Discord's settings
  grammar. Familiarity is worth more than novelty for a panel someone opens
  once a month *(inference, but it is the reason every bot in §2 imitates
  Discord)*.
- A's docked dirty-bar is the single biggest fix to the actual complaint ("a lot
  of input boxes per page"): it removes 96 buttons from Settings *(observed: 48
  keys × Save+Clear on `/settings.html`)*.
- B's tables are strictly better than A's and cost nothing to adopt: toolbar,
  `—`, tooltip headers, drawer, row actions *(observed on Cloudflare DNS)*. B on
  its own is a harder sell as a whole-site identity — it is the most beautiful
  and the least welcoming.
- C is genuinely on-brand and would be the most *liked* on first sight, but warm
  colour plus a chunky display face around a `Ban` button is a real risk, and it
  is the most work (new fonts, new tokens, new copy voice). It also cannot be
  evaluated fairly in ASCII — it needs the canvas mock.

**So the mock should show A and C** (B's contribution is the table detail, which
I'd render inside A) — that gives the owner a real choice between "familiar" and
"ours" rather than three near-identical dark panels.

---

## 7. Questions only the owner can answer

Ask these one at a time, in this order (global rule):

1. **Dark only, or dark + light?** Every bot in the survey is dark-only;
   Cloudflare, the most "premium" thing in the survey, is light-first. Keeping
   both doubles the palette work and every review pass. *(Today's site ships 5
   themes × 2 modes — the widest of anything surveyed, and none of them was
   designed for this app.)*
2. **Do we keep the 5-theme dropdown at all?** It is a snapshot of the estate
   themes and the site is meant to be disconnected. Dropping it to one owned
   theme (plus dark/light if you want it) is the single biggest simplification
   available.
3. **Icons in the navigation, or Discord-style text only?** Text-only is
   cheaper, ages better and is what Discord itself does; icons make a 13-item
   rail scannable faster.
4. **Which of the three names the site's voice — A "Discord-native", B "Ops
   console", or C "Cookout"?** (My recommendation is A's shell with B's tables;
   C is the one I'd want to see mocked before deciding.)

Two more, lower stakes, whenever convenient:

5. Do you want a **command palette** (`Ctrl K` to jump to any setting/action)?
   It is B's best idea and works in any skin.
6. Should Settings show the **raw key** at all, or hide it behind a "show keys"
   toggle for the people who read the docs?

---

## 8. Sources

Pages I opened on 2026-08-27 (Phoenix):

- `https://blackbloc.heygabi.ai/` · `/settings.html` · `/moderation.html` (ours, signed in)
- `https://carl.gg/dashboard/1073710702776299640/automod` · `/moderation` · `/reactionroles`
- `https://yagpdb.xyz/manage/1073710702776299640/streaming` · `/moderation`
- `https://mee6.xyz/en`
- `https://dyno.gg/`
- `https://wickbot.com/`
- `https://probot.io/`
- `https://sapph.xyz/`
- `https://support.discord.com/hc/en-us/articles/4421269296535-AutoMod-FAQ` and its
  attachment `…/hc/article_attachments/12974312213271`
- `https://linear.app/`
- `https://vercel.com/geist/introduction` · `https://vercel.com/geist/colors`
- `https://dash.cloudflare.com/` (account home) and a DNS records page

**Not reachable without an account, so marketing-only:** MEE6, Dyno, ProBot,
Sapphire and Wick dashboards. Dyno's interior is known only from a low-resolution
laptop render on its own home page; Wick's only from its hero render. Discord's
own settings were read from a support-article screenshot, not from a live client.
No page's toggle *states* were changed and nothing was clicked that writes.
