# Discord server scan — Black in a Flash! — 2026-08-26

> **Audience:** Black Bloc feature builders (F1/F2 live-now, F6 birthdays, F7 moderation,
> F8 temp voice, F9 honeypot, F11 modmail). **Status:** TRACKED (2026-08-31; private repo).
> One-off measurement dump, not a living doc. **Last verified: 2026-08-26.**
>
> **Method:** READ-ONLY Discord HTTP API via the Black Bloc bot token
> (`client.login()` + REST fetches; the gateway was never started, nothing was
> sent, reacted to, edited or created). Scripts: `scripts/scan/*.py` (uncommitted).

---

## 0. Scan coverage — what this document is built on

An earlier pass on the same day was **blocked**: the bot held only `@everyone` + its own
managed role, every category denies `read_messages` to `@everyone` and allows it only to
`Member`, and **117 of 119 channels answered `403 Missing Access`**. The owner then gave
the `Black_Bloc` role a role carrying channel visibility, and the scan was re-run.

| Measure | Before the grant | **After (this document)** |
|---|---|---|
| Channels the bot can view | 4 / 134 | **134 / 134** |
| Channels with Read Message History | 3 / 134 | **134 / 134** |
| Text-capable channels swept at `limit=200` | 119 (117 × 403) | **128 (0 × 403)** |
| Bot-authored messages recovered | 1 | **449** |

⚠️ **Keep the permission fact — it is a live gotcha, not history.** The visibility the bot
now has is a *granted role*, not a property of the bot. If that role is ever removed or
re-ordered, every read-dependent feature (F1 presence posts, F6 announcements, F7
moderation, F11 modmail) silently starts 403-ing. **Black Bloc must treat
`403 Missing Access` as an alertable condition, not a skip.**

**Sweep size:** 128 channels × up to 200 messages = **12,488 messages read**, of which 449 were bot- or webhook-authored.
A second **deep scan** (`deep_birthday.py`, `limit=6000`) covered 5 high-value channels to
establish Birthday Bot's posting pattern: **18,995 further messages**, back to 2023-09-13.

---

## A. Channel inventory

**Guild:** Black in a Flash! (`1073710702776299640`) — ~125 members, boost tier 2.
**Totals:** 134 channels — 13 categories, 90 text, 29 voice, 2 forum, 0 stage.

Measured from `guild.fetch_channels()`. `Bot msgs` is how many of the channel's most recent
200 messages came from a bot or webhook — **0 means the channel is purely human**.
Voice rows carry `limit` (∞ = unlimited) and bitrate.

### 📁 Information (`1073710703518683136`)
*Category position 0*

| Channel | Type | ID | Bot msgs | Voice limit / bitrate | Topic | Feature flag |
|---|---|---|---|---|---|---|
| `#welcome` | text | `1285369365071527997` | **1** |  |  | welcome / gate |
| `#roles` | text | `1285782324558172180` | **5** |  |  | roles / self-assign |
| `#asset-library` | text | `1452150360293773365` | 0 |  |  |  |
| `#announcements` | text | `1285381774876344340` | **1** |  |  | announcements |

### 📁 The Hole in the Wall (`1073710703518683140`)
*Category position 1*

| Channel | Type | ID | Bot msgs | Voice limit / bitrate | Topic | Feature flag |
|---|---|---|---|---|---|---|
| `#landing` | text | `1285371141476581509` | 0 |  | Say hi and you'll get a role to access the rest of the server.   If you're here for an event, say what you're running or commentating for.  … | welcome / gate |
| `#introductions` | text | `1398449806438826025` | 0 |  | use this channel to make a brief introduction to who you are and what brings you to BaF!  If you need something to help mold the conversatio… | welcome / gate |
| `#return-of-the-gen` | text | `1411816390414962700` | **1** |  | Yes! It has risen from the depths of Wordle heck! General channel is back! Talk about what general gaming thing you want to your heart's con… |  |
| `#qotw` | text | `1474844966021890362` | 0 |  | This is a space where we can get to know each other. Each week, there will be a question that will be asked. This may be something goofy af,… | scheduled content (QOTW) |
| `#wordle-central` | text | `1073710703518683141` | **155** |  |  | Wordle activity bot |
| `#advice-needed` | text | `1073710703518683142` | 0 |  | We all need a place to ask for advice. IRL happens. We want to be a community to support each other. Whether for just letting it out, or ask… |  |
| `#off-topic` | text | `1073710703518683143` | 0 |  | Be random, from pet pics to whatever the latest meme is. |  |
| `#shows-and-movies` | text | `1413648696670949376` | 0 |  |  |  |
| `#sports-ball` | text | `1413643742308728983` | 0 |  |  |  |
| `#drop-da-playlist` | text | `1413699977137623121` | 0 |  |  |  |
| `#recipes-and-food-pics` | text | `1413700333796069419` | 0 |  |  |  |
| `#gif-spam` | text | `1497233190383915008` | 0 |  | here dang |  |
| `#quotes` | text | `1524047038562435193` | 0 |  |  |  |

### 📁 House Parties (`1414725511778664458`)
*Category position 2*

| Channel | Type | ID | Bot msgs | Voice limit / bitrate | Topic | Feature flag |
|---|---|---|---|---|---|---|
| `#upcoming-events` | text | `1147289379493118033` | 0 |  | If you are going to be in something to please the Ancestors, drop it here! | events |
| `#deals` | text | `1457505283067613287` | 0 |  | Got a good deal on something we should know about? From a sale on controllers to a half-off ice cream machine, post those bargains! |  |
| `#live-now` | text | `1225457308230746202` | **199** |  | Wanna let people know when you're going live? Post your links here and let everyone turn up for it! | live/streaming |
| `#community-clips` | text | `1497362790732664893` | 0 |  |  |  |
| `#opportunities` | text | `1419778694460866633` | 0 |  |  |  |
| `#collabs-and-community-events` | forum | `1474885454267678850` | 0 | tags: community event, collab | All in one shop to gather for collabs or stay up to date on community events such as the messipelagos (archipelagos), watch parties, game ni… | events |
| `#ask-a-gdq-employee` | forum | `1488247961224745110` | 0 |  | Have a specific question about an upcoming event or suggestions for an idea you have? Ask here and we'll be able to answer! No stupid questi… |  |

### 📁 Gaming (`1414694257721082028`)
*Category position 3*

| Channel | Type | ID | Bot msgs | Voice limit / bitrate | Topic | Feature flag |
|---|---|---|---|---|---|---|
| `#gaming` | text | `1437995212122099752` | 0 |  |  |  |
| `#run-prep` | text | `1076011219351257108` | 0 |  | It's dangerous to go alone. Take some friends with you! This space is for your and your crew to get your work in! |  |
| `#speed-and-pbs` | text | `1076003845232148580` | 0 |  | If you are a speedrunner or aspiring speedrunner, this channel is for you to come and chat! Got a new PB? Drop it here and let us celebrate … |  |
| `#squads` | text | `1436166669008502945` | 0 |  | Use this as your quad for your squad! Get ready to stomp ~~the yard~~ your game! |  |
| `#knuck-up` | text | `1076005097617760296` | 0 |  | If you love fighting games, this is your channel! Just don't drop your combos or get countered! |  |
| `#rpg` | text | `1413701019711442964` | 0 |  |  |  |

### 📁 Play Cousins (`1480297391146930358`)
*Category position 4*

| Channel | Type | ID | Bot msgs | Voice limit / bitrate | Topic | Feature flag |
|---|---|---|---|---|---|---|
| `#asian-speedrun-alliance` | text | `1480974710404808837` | 0 |  |  |  |
| `#fatales` | text | `1480297661180678386` | 0 |  | yap about frame fatales events (frost, flame, etc.)! |  |
| `#lhs` | text | `1480974771981258753` | 0 |  |  |  |
| `#gdqueer` | text | `1480974833117298790` | 0 |  |  |  |

### 📁 Voice Channels (`1073710703518683144`)
*Category position 5*

| Channel | Type | ID | Bot msgs | Voice limit / bitrate | Topic | Feature flag |
|---|---|---|---|---|---|---|
| `#The Lounge` | voice | `1073710703518683145` | 0 | limit ∞ / 64 kbps |  |  |
| `#Gaming 1` | voice | `1411463390546624602` | 0 | limit 4 / 64 kbps |  |  |
| `#Gaming 2` | voice | `1411463467474620447` | 0 | limit 6 / 64 kbps |  |  |
| `#lab it out` | voice | `1429344872170651743` | 0 | limit 4 / 64 kbps |  |  |
| `#Work & Chill` | voice | `1480595026751782932` | 0 | limit ∞ / 64 kbps |  |  |
| `#You Still Here?` | voice | `1494421792675070123` | 0 | limit ∞ / 64 kbps |  |  |

### 📁 SGDQ 2026 Lab (`1376271608246833254`)
*Category position 6*

| Channel | Type | ID | Bot msgs | Voice limit / bitrate | Topic | Feature flag |
|---|---|---|---|---|---|---|
| `#lab-chat` | text | `1376272041573089402` | 0 |  |  |  |
| `#Lab 1` | voice | `1376347035133022228` | 0 | limit ∞ / 64 kbps |  |  |
| `#Lab 2` | voice | `1376347065956958291` | 0 | limit ∞ / 64 kbps |  |  |

### 📁 The Basement (`1094708810813280326`)
*Category position 7*

| Channel | Type | ID | Bot msgs | Voice limit / bitrate | Topic | Feature flag |
|---|---|---|---|---|---|---|
| `#the-adult-table` | text | `1491507415932469328` | 0 |  |  |  |
| `#the-main-table` | text | `1094709109841989753` | 0 |  |  |  |
| `#event-heads-up` | text | `1094711719797985330` | 0 |  |  | events |
| `#bot-control` | text | `1411774767966453791` | **49** |  |  | bot control / test |
| `#carlbot-logs` | text | `1285782812229763092` | **7** |  |  | logging / mod |
| `#join-log` | text | `1073710703518683138` | **5** |  |  | logging / mod |
| `#baf-power-quotes` | text | `1496980277841363046` | 0 |  |  |  |
| `#mute-me-bot-test-spam` | text | `1542316174472380517` | **3** |  |  | bot control / test |
| `#Meeting Room` | voice | `1073710703858426006` | 0 | limit ∞ / 64 kbps |  |  |

### 📁 Back to Black 2027 (`1534693157415948390`)
*Category position 8*

| Channel | Type | ID | Bot msgs | Voice limit / bitrate | Topic | Feature flag |
|---|---|---|---|---|---|---|
| `#welcome` | text | `1534971515932643390` | **1** |  |  | welcome / gate |
| `#announcements` | text | `1534775990704803930` | **1** |  |  | announcements |
| `#leads` | text | `1534777301781184522` | 0 |  |  |  |
| `#live-production` | text | `1534777453556273263` | 0 |  |  | live/streaming |
| `#tech-checks` | text | `1534778339569434684` | 0 |  |  |  |
| `#runners` | text | `1534778017929498654` | 0 |  |  |  |
| `#committee` | text | `1534778121138602084` | 0 |  |  |  |
| `#donations` | text | `1534778880727060622` | 0 |  |  |  |
| `#interstitials` | text | `1534998323403034635` | 0 |  |  |  |
| `#moderators` | text | `1534778635473387610` | 0 |  |  | logging / mod |
| `#socials` | text | `1534809142546399362` | 0 |  |  |  |

### 📁 archive (`1285804172951949373`)
*Category position 9*

| Channel | Type | ID | Bot msgs | Voice limit / bitrate | Topic | Feature flag |
|---|---|---|---|---|---|---|
| `#who-you-be` | text | `1074781292731842590` | 0 |  |  | welcome / gate |
| `#welcome-and-rules` | text | `1073710703518683137` | 0 |  |  | rules, welcome / gate |
| `#black-support-hub` | text | `1147968944490160261` | 0 |  | A channel to tell us about the cool stuff you're doing, the cool stuff you're HOSTING, the cool stuff you're involved in at all, and to get … |  |
| `#resources` | text | `1073710703518683139` | 0 |  |  |  |

### 📁 Back to Black 2025 (`1285362804030832661`)
*Category position 10*

| Channel | Type | ID | Bot msgs | Voice limit / bitrate | Topic | Feature flag |
|---|---|---|---|---|---|---|
| `#hosts` | text | `1285363980516200540` | 0 |  |  |  |
| `#committee` | text | `1285364898750267515` | 0 |  |  |  |
| `#tech-checkers` | text | `1329563943487803473` | 0 |  |  |  |
| `#donations` | text | `1335035325113831424` | 0 |  |  |  |
| `#runners` | text | `1285363010692710485` | 0 |  |  |  |
| `#tech-checks` | text | `1285363724890280046` | 0 |  |  |  |
| `#mainline-promo-planning` | text | `1322311143104184360` | 0 |  |  |  |
| `#production` | text | `1285362943155765278` | 0 |  |  |  |
| `#charity-plaza` | text | `1335035068099334164` | 0 |  |  |  |
| `#live-production` | text | `1337090172394930238` | 0 |  |  | live/streaming |
| `#resources` | text | `1285363575556411392` | 0 |  |  |  |
| `#Live Channel` | voice | `1285365589703000134` | 0 | limit ∞ / 64 kbps |  | live/streaming |
| `#Interview` | voice | `1337181194541858877` | 0 | limit ∞ / 64 kbps |  |  |
| `#Setup 1` | voice | `1285365672066420796` | 0 | limit ∞ / 64 kbps |  |  |
| `#Setup 2` | voice | `1285365723446771803` | 0 | limit ∞ / 64 kbps |  |  |
| `#Event Chat` | voice | `1285365898013577289` | 0 | limit ∞ / 64 kbps |  | events |
| `#Tech Check` | voice | `1285366017257902224` | 0 | limit ∞ / 64 kbps |  |  |
| `#Committee` | voice | `1335338689785499781` | 0 | limit ∞ / 64 kbps |  |  |
| `#locker room hype (remixed)` | voice | `1318021296549924864` | 0 | limit ∞ / 64 kbps |  |  |
| `#host meeting` | voice | `1335407017795518524` | 0 | limit ∞ / 64 kbps |  |  |

### 📁 Back to Black 2026 (`1428165625108496486`)
*Category position 11*

| Channel | Type | ID | Bot msgs | Voice limit / bitrate | Topic | Feature flag |
|---|---|---|---|---|---|---|
| `#btb2026-general` | text | `1449940880742944788` | 0 |  |  |  |
| `#btbt2026-leads` | text | `1460453073959915732` | 0 |  |  |  |
| `#live-prod` | text | `1430627630821933107` | 0 |  |  | live/streaming |
| `#btb2026-yearbook` | text | `1472016561047863459` | 0 |  |  |  |
| `#live-vol-updates` | text | `1467777240459772038` | 0 |  |  |  |
| `#runners` | text | `1430626512331083928` | 0 |  |  |  |
| `#tech-checks` | text | `1430625708186800169` | 0 |  |  |  |
| `#production` | text | `1430626931828854975` | 0 |  |  |  |
| `#mod-central` | text | `1445157148492435617` | **4** |  |  | logging / mod |
| `#tech-checker-chatter` | text | `1445191021305790494` | 0 |  |  |  |
| `#committee` | text | `1430625650687086733` | 0 |  |  |  |
| `#socials-homies` | text | `1445191241217216622` | 0 |  |  |  |
| `#hosts` | text | `1430625933785563198` | 0 |  |  |  |
| `#donations` | text | `1430626278142382182` | 0 |  |  |  |
| `#resources` | text | `1430628292922314803` | 0 |  |  |  |
| `#agdq-promo-planning` | text | `1430626798571487272` | 0 |  |  |  |
| `#interview-brain-dumps` | text | `1430639977519382679` | 0 |  |  |  |
| `#🎙️Tech Checks` | voice | `1430630080991858729` | 0 | limit ∞ / 64 kbps |  |  |
| `#🎙️Tech Checks 2` | voice | `1445181504429883422` | 0 | limit ∞ / 64 kbps |  |  |
| `#🔴 LIVE CHANNEL (ACTIVE RUNNERS + COMMS ONLY)` | voice | `1430632176508080148` | 0 | limit ∞ / 64 kbps / region us-east |  | live/streaming |
| `#✅Green Room 1` | voice | `1430630791578255522` | 0 | limit ∞ / 64 kbps |  |  |
| `#☑️Alt-Green Room 2` | voice | `1430630881927626837` | 0 | limit ∞ / 64 kbps |  |  |
| `#🗣️Event Locker Room` | voice | `1430631197549137950` | 0 | limit ∞ / 64 kbps |  | events |
| `#🧐 General Meeting Hub` | voice | `1463265211594309855` | 0 | limit ∞ / 64 kbps |  |  |
| `#📓Interview` | voice | `1430630469954699374` | 0 | limit ∞ / 64 kbps |  |  |
| `#🎮 Committee Meeting Hub` | voice | `1430632417991069888` | 0 | limit ∞ / 64 kbps |  |  |
| `#💻Lead Meeting Hub` | voice | `1430632776906051675` | 0 | limit ∞ / 64 kbps |  |  |
| `#😄Host Meeting Hub` | voice | `1430632591261831179` | 0 | limit ∞ / 64 kbps |  |  |

### 📁 ModMail (`1442613057628012594`)
*Category position 12*

| Channel | Type | ID | Bot msgs | Voice limit / bitrate | Topic | Feature flag |
|---|---|---|---|---|---|---|
| `#modmail-log` | text | `1442613059704066108` | **5** |  |  | logging / mod, modmail |
| `#kurushiidrive` | text | `1515388560021389463` | **2** |  | ModMail Channel 280397245206102028 1267275219777884263 (Please do not change this) |  |
| `#yatogaminl` | text | `1519898370179858632` | **2** |  | ModMail Channel 165189391583674368 1519898046727716999 (Please do not change this) |  |
| `#riekelt` | text | `1526703242141237480` | **3** |  | ModMail Channel 78578364285194240 1526703129452871680 (Please do not change this) |  |
| `#shindarkshadow` | text | `1530706388215664690` | **2** |  | ModMail Channel 226810899015532545 1530701370787758180 (Please do not change this) |  |
| `#nadiahooligan` | text | `1537729008626831410` | **3** |  | ModMail Channel 450785299639828491 1358295308626427934 (Please do not change this) |  |

### Channels that matter to Black Bloc — now with what is actually IN them

| Channel | ID | Measured contents |
|---|---|---|
| `#welcome-and-rules` | `1073710703518683137` | rules, welcome / gate — no bot activity |
| `#join-log` | `1073710703518683138` | **NOT a bot log** — 151 messages, all Discord-native `new_member` join notices. The 5 'bot' entries are bots' own join notices. |
| `#wordle-central` | `1073710703518683141` | Discord's built-in **Wordle activity** webhook — 155 of 200 messages. A daily streak summary is posted each night. |
| `#who-you-be` | `1074781292731842590` | welcome / gate — no bot activity |
| `#event-heads-up` | `1094711719797985330` | events — no bot activity |
| `#upcoming-events` | `1147289379493118033` | **F4/F5 target** — 0 bot messages; events are announced by hand today. |
| `#live-now` | `1225457308230746202` | **F1/F2 target — and it is ALREADY a bot feed.** 199 of the last 200 messages are YAGPDB go-live posts; exactly 1 is human. See section G. |
| `🔊 Live Channel` | `1285365589703000134` | live/streaming — no bot activity |
| `🔊 Event Chat` | `1285365898013577289` | events — no bot activity |
| `#welcome` | `1285369365071527997` | Carl-bot rules post (❤️ ×74). The front door of the onboarding flow. |
| `#landing` | `1285371141476581509` | **The gate** — 0 bot messages in 200. The `Member` grant is NOT posted here by any bot; it happens silently (Carl-bot/YAGPDB autorole, not observable from message history). |
| `#announcements` | `1285381774876344340` | Server announcements — only 1 bot message in its entire 96-message history (a YAGPDB reaction poll, 2026-05-08). |
| `#roles` | `1285782324558172180` | **5 Carl-bot reaction-role panels** covering ~23 self-assign roles. See section D. |
| `#carlbot-logs` | `1285782812229763092` | Carl-bot mod-log. **7 automod `warn` cases** measured — mention-spam and one blacklisted word. |
| `#live-production` | `1337090172394930238` | live/streaming — no bot activity |
| `#introductions` | `1398449806438826025` | welcome / gate — no bot activity |
| `#bot-control` | `1411774767966453791` | Where the owner tests bots: Carl-bot, ModMail, Birthday Bot and a **Red-DiscordBot instance (`baf#0659`)** all replied here. |
| `#return-of-the-gen` | `1411816390414962700` | **The birthday channel** — and also the server's general chat. All 16 Birthday Bot announcements landed here; only 1 falls inside the 200-message window, the other 15 came from the 6,000-message deep scan. See section C. |
| `#live-prod` | `1430627630821933107` | live/streaming — no bot activity |
| `🔊 🗣️Event Locker Room` | `1430631197549137950` | events — no bot activity |
| `🔊 🔴 LIVE CHANNEL (ACTIVE RUNNERS + COMMS ONLY)` | `1430632176508080148` | live/streaming — no bot activity |
| `#modmail-log` | `1442613059704066108` | ModMail ticket index: `New Ticket` embeds, footer `username \| user-id`. |
| `#mod-central` | `1445157148492435617` | YAGPDB used as a **timezone converter** (`Above time (HH:00 GMT) in your local time`) — relevant to F4. |
| `#qotw` | `1474844966021890362` | QOTW — 0 bot messages. The weekly question is posted by a human, not a bot. |
| `#collabs-and-community-events` | `1474885454267678850` | events — no bot activity |
| `#announcements` | `1534775990704803930` | announcements — 1 bot msgs in last 200 |
| `#live-production` | `1534777453556273263` | live/streaming — no bot activity |
| `#moderators` | `1534778635473387610` | logging / mod — no bot activity |
| `#welcome` | `1534971515932643390` | welcome / gate — 1 bot msgs in last 200 |
| `#mute-me-bot-test-spam` | `1542316174472380517` | Black Bloc's `TEST_CHANNEL_ID`. Carries today's **Carl-bot automod config dump** and **YAGPDB automod-v2 check** — the F7 spec. See sections D and E. |

**Honeypot / trap channels: NONE.** No channel matches the pattern by name, **and this is
now confirmed from config**: Carl-bot's automod dump reports `Honeypot — Channels: None,
Punishment: None` (section D). Carl-bot *has* the feature and it is switched off, so F9 is
a genuinely unbuilt capability rather than a duplicate.

**Join-to-create voice: NONE.** No lobby channel exists and every voice channel is a fixed
room. Three carry manual user limits (`Gaming 1` = 4, `Gaming 2` = 6, `lab it out` = 4);
the other 26 are unlimited. tempvoice.xyz is not installed — F8 is unbuilt.

---

## B. Role inventory

Measured from `guild.fetch_roles()`. **Exact member counts are still absent** —
`fetch_roles()` returns none and `guild.fetch_members()` fails with *"Intents.members must
be enabled to use this"* (the GUILD_MEMBERS privileged intent is off for this app).
**However, the self-assign roles now have a measured lower bound**: the reaction counts on
the Carl-bot panels (section D) are how many members clicked each role.

**60 roles**, listed highest position first.

| Pos | Role | ID | Colour | Hoist | Ment. | Managed | Notable permissions | Looks like |
|---|---|---|---|---|---|---|---|---|
| 59 | Leads | `1406041634675884174` | — | ✓ | ✓ |  | 🔴 **`administrator`** (implies all) | staff/mod |
| 58 | PT | `1406041768256077975` | #dec0cc |  |  |  | — |  |
| 57 | ground zero | `1406041866306195476` | #ff7766 |  |  |  | — |  |
| 56 | Pop | `1462664385565560843` | #a183c0 |  |  |  | — |  |
| 55 | Aunties / Uncles | `1073711363337236601` | #206694 | ✓ | ✓ |  | `manage_guild`, `manage_roles`, `manage_channels`, `manage_messages`, `manage_nicknames`, `manage_events`, `manage_threads`, `kick_members`, `ban_members`, `moderate_members`, `mention_everyone`, `mute_members`, `deafen_members`, `move_members` | staff/mod |
| 54 | Staff | `1335035657730523219` | #e74c3c | ✓ |  |  | `mention_everyone` | staff/mod |
| 53 | carl-bot | `1285781991345619008` | — |  |  | ✓ | 🔴 **`administrator`** (implies all) | **bot-managed** |
| 52 | YAGPDB.xyz | `1073736137052540963` | — |  |  | ✓ | 🔴 **`administrator`** (implies all) | **bot-managed** |
| 51 | Bots | `1075183804429389916` | — |  |  |  | 🔴 **`administrator`** (implies all) |  |
| 50 | Production | `1285361827139682345` | — |  | ✓ |  | `manage_roles`, `manage_channels`, `mention_everyone`, `mute_members`, `deafen_members`, `move_members` |  |
| 49 | Live Runner | `1285365452666699837` | #ff5858 | ✓ |  |  | — | **live/streaming** |
| 48 | Runner | `1285361896383320074` | — |  | ✓ |  | — |  |
| 47 | Commentator | `1285361954860437516` | — |  | ✓ |  | — |  |
| 46 | He/Him | `1285785434131005474` | — |  |  |  | — | **self-assign: pronouns** |
| 45 | She/Her | `1285785449541144607` | — |  |  |  | — | **self-assign: pronouns** |
| 44 | He/They | `1285785451591897108` | — |  |  |  | — | **self-assign: pronouns** |
| 43 | She/They | `1285785453412220989` | — |  |  |  | — | **self-assign: pronouns** |
| 42 | They/He | `1285785455199260712` | — |  |  |  | — | **self-assign: pronouns** |
| 41 | They/She | `1285785456918925362` | — |  |  |  | — | **self-assign: pronouns** |
| 40 | They/Them | `1285785458797711472` | — |  |  |  | — | **self-assign: pronouns** |
| 39 | It/Its | `1285785460647526522` | — |  |  |  | — | **self-assign: pronouns** |
| 38 | Ask my pronouns | `1285786169392762952` | — |  |  |  | — | **self-assign: pronouns** |
| 37 | Speedrunner | `1285790096536109077` | — |  |  |  | — | **self-assign: panel** |
| 36 | Challenge Runner | `1285790140538683464` | — |  |  |  | — | **self-assign: panel** |
| 35 | Score Attacker | `1285790163380867146` | — |  |  |  | — | **self-assign: panel** |
| 34 | Ranked Gamer | `1285790268192460810` | — |  |  |  | — | **self-assign: panel** |
| 33 | Casual | `1285790198646706286` | — |  |  |  | — | **self-assign: panel** |
| 32 | Mentor | `1075115919967273000` | — |  | ✓ |  | `mention_everyone` | **self-assign: panel** |
| 31 | Initiate | `1075117204447703040` | — |  |  |  | `mention_everyone` | **self-assign: panel** |
| 30 | Verification Bot | `1291098154476769312` | — |  |  | ✓ | — | **bot-managed** |
| 29 | Server Booster | `1411444909235503205` | #f47fff |  |  | ✓ | — | booster |
| 28 | Sports | `1413642880790167653` | — |  |  |  | — | **self-assign: panel** |
| 27 | Squads | `1413643063145926666` | — |  |  |  | — | **self-assign: panel** |
| 26 | Shows | `1413643112965738506` | — |  |  |  | — | **self-assign: panel** |
| 25 | Musichead | `1413643194511659102` | — |  |  |  | — | **self-assign: panel** |
| 24 | Foodie | `1413643284064108544` | — |  |  |  | — | **self-assign: panel** |
| 23 | RPGer | `1413643323876573185` | — |  |  |  | — | **self-assign: panel** |
| 22 | Randos | `1456219128921718939` | #ffffff |  |  |  | — | **self-assign: panel** |
| 21 | ModMail | `1442295025173135551` | — |  |  | ✓ | `manage_roles`, `manage_channels`, `manage_messages` | **bot-managed**, staff/mod |
| 20 | Committee | `1316914599345262632` | #f1c40f | ✓ | ✓ |  | `manage_roles` | staff/mod |
| 19 | Charity Rep | `1335035563492769843` | #71368a | ✓ |  |  | — |  |
| 18 | Donations | `1322311322699825193` | #11806a | ✓ |  |  | — |  |
| 17 | Interstitials | `1442634698475180093` | #2ecc71 | ✓ |  |  | — |  |
| 16 | Host Coord | `1449893690222055556` | #8b0b0d | ✓ |  |  | — |  |
| 15 | Host First Assist | `1451860698991693844` | #ff2f18 |  |  |  | — |  |
| 14 | Host | `1285362003933659248` | #992d22 | ✓ | ✓ |  | — |  |
| 13 | Backup Host | `1443558932743196702` | #c27c0e | ✓ |  |  | — |  |
| 12 | Tech Check | `1329563750214144051` | #3498db | ✓ | ✓ |  | `mention_everyone` |  |
| 11 | Tech Support | `1329563814156308592` | #7475ca | ✓ | ✓ |  | — |  |
| 10 | Chat Mods | `1445186218223730718` | #70e7d1 | ✓ |  |  | — | staff/mod |
| 9 | Prizes | `1446567371727704318` | #80658b | ✓ |  |  | — |  |
| 8 | Social Media | `1445186353636708384` | #d1a1e4 | ✓ |  |  | — |  |
| 7 | Member | `1073741054563602532` | #ffffff | ✓ | ✓ |  | — |  |
| 5 | SGDQ Runner | `1376270322440994907` | #ad1457 |  |  |  | — |  |
| 4 | Birthday Bot | `1467087801538445347` | — |  |  | ✓ | — | **bot-managed**, **birthday** |
| 3 | 🎂 | `1467088677330227305` | #ac1cfe | ✓ | ✓ |  | — | **birthday** |
| 2 | QOTW | `1474849344644710441` | — |  |  |  | — | **self-assign: panel** |
| 1 | Marathons | `1515068917628801135` | — |  |  |  | — | **self-assign: panel** |
| 1 | Black_Bloc | `1542320164949860364` | — |  |  | ✓ | `manage_roles`, `manage_channels`, `manage_messages`, `manage_events`, `kick_members`, `ban_members`, `moderate_members`, `mention_everyone`, `move_members` | **bot-managed** |
| 0 | @everyone | `1073710702776299640` | — |  |  |  | — | default |

### Role findings that matter

- 🔴 **Four roles hold `administrator`:** `Leads` (59), `Bots` (51), `YAGPDB.xyz` (52),
  `carl-bot` (53). `Bots` being an Administrator role is worth raising — anything added to
  it gets the whole server.
- **`Aunties / Uncles` (55)** is the real moderator role: every `manage_*`, kick, ban,
  `moderate_members`, `mention_everyone`, and voice mute/deafen/move — but *not*
  Administrator. **This is the permission set F7 should mirror.**
- **`Staff` (54)** is a hoisted display/label role: only `mention_everyone`. **`Chat Mods`
  (10) has NO permissions at all** — it grants access via channel overwrites only.
- **No `Muted` role exists**, and Carl-bot's automod confirms why: its punishments are
  `tempmute (5m)` / `tempmute (10m)`, which on a server with no mute role means Discord's
  native timeout. **F7 should implement timeouts, not a mute role.**
- **`Live Runner` (49, `#ff5858`, hoisted)** — despite the name, **it is not the
  streaming role**. The go-live feed (section G) assigns nothing; `Live Runner` is hoisted
  next to event-production roles and reads as *on-stream at a marathon*. **F1/F2 needs a
  NEW role**; do not reuse this one without asking.
- **`🎂` (3, `#ac1cfe`, hoisted, mentionable)** sits directly below the `Birthday Bot`
  managed role (4) — the ordering a bot needs to assign it. But see section C: **no
  observed announcement mentions or grants the role**, and Birthday Bot has no
  `manage_roles`. How `🎂` gets applied is still unresolved.
- **`Member` (7) is the access key to the whole server** — the role every category's
  overwrite allows. `#landing`'s topic says posting there grants it; **0 bot messages exist
  in `#landing`**, so the grant is a silent autorole rule in Carl-bot or YAGPDB, not
  observable from message history. F7 must confirm which bot owns it before cutover.
- **Self-assign roles are all reaction-driven through Carl-bot** — 23 roles across 5
  panels, with measured take-up in section D.

---

## C. Birthday Bot posting time — ✅ MEASURED (16 announcements)

### The headline

⚠️ **There is no single posting hour, and that is the most important finding in this
section.** Across 16 announcements the UTC hour ranges over 23:03, 04:02, 04:03, 05:03,
05:13, 06:02, 06:13 and 07:03 — but **the minute is almost always `:03`**, and every post
lands at **≈00:03 local midnight in a timezone that differs per member**.

All 16 announcements were posted in **`#return-of-the-gen`** (`1411816390414962700`)
— the general chat, not a dedicated birthday channel.

| Announced (UTC) | America/Phoenix (UTC-7) | Implied local offset | Member |
|---|---|---|---|
| `2026-02-04 06:13:32` | `2026-02-03 23:13:32` | **UTC-6** | Stray Ketchum |
| `2026-02-11 05:13:28` | `2026-02-10 22:13:28` | **UTC-5** | [Champrul] Champrul |
| `2026-03-24 05:03:11` | `2026-03-23 22:03:11` | **UTC-5** | Corporate YN |
| `2026-03-26 04:02:54` | `2026-03-25 21:02:54` | **UTC-4** | Thormungandr |
| `2026-03-28 04:03:15` | `2026-03-27 21:03:15` | **UTC-4** | Blazette Midnight |
| `2026-04-30 04:03:11` | `2026-04-29 21:03:11` | **UTC-4** | PhotoshopSMB |
| `2026-05-02 05:03:03` | `2026-05-01 22:03:03` | **UTC-5** | rosheeki |
| `2026-06-01 23:03:36` | `2026-06-01 16:03:36` | **UTC+1** | palustrine |
| `2026-06-04 04:03:14` | `2026-06-03 21:03:14` | **UTC-4** | raelcun |
| `2026-06-15 04:03:43` | `2026-06-14 21:03:43` | **UTC-4** | lanzthemaster |
| `2026-06-17 04:03:40` | `2026-06-16 21:03:40` | **UTC-4** | Prez |
| `2026-06-29 04:03:09` | `2026-06-28 21:03:09` | **UTC-4** | mcknux |
| `2026-07-02 07:03:04` | `2026-07-02 00:03:04` | **UTC-7** | blamprul |
| `2026-07-16 04:03:08` | `2026-07-15 21:03:08` | **UTC-4** | mrpainandsorrow |
| `2026-07-26 05:03:08` | `2026-07-25 22:03:08` | **UTC-5** | (Umazing) nadia |
| `2026-08-10 06:02:50` | `2026-08-09 23:02:50` | **UTC-6** | [40] PT |

**Implied-offset histogram:** `UTC-7` ×1, `UTC-6` ×2, `UTC-5` ×4, `UTC-4` ×8, `UTC+1` ×1.
**Minute-of-hour:** `:03` ×12, `:02` ×2, `:13` ×2.

### Why this is per-member local midnight, not a server hour

A fixed server timezone produces ONE UTC hour that shifts only at DST boundaries. Instead:

- **June 2026 alone contains two different offsets** — four posts at `04:03Z` (UTC-4) and
  one at `23:03Z` the previous day (UTC+1, `palustrine`). No single timezone does that.
- The offsets track real DST: `Champrul` was `UTC-5` on 11 Feb (EST) and the same cohort
  reads `UTC-4` from late March (EDT). `PT` reads `UTC-6` on 10 Aug — Mountain **with**
  DST, i.e. Denver, *not* Phoenix.
- The distribution (`UTC-4` ×8, `-5` ×4, `-6` ×2, `-7` ×1, `+1` ×1) is a plausible member
  spread for a mostly-US community with one UK member.

⚠️ **This CONTRADICTS Birthday Bot's own boilerplate**, which its `Birthday List` embed
states as: *"Birthdays are celebrated on the day and month the user has but in the
__time zone__ of the server."* **Measured behaviour wins over the blurb.** The most likely
mechanism is Birthday Bot's per-user timezone setting overriding the server default —
**that mechanism is an inference; the 16 timestamps are the measurement.**

### 🔴 The Phoenix gotcha F6 must decide on

Because Phoenix is UTC-7 with no DST, and most members are UTC-4/-5, **15 of the 16
announcements landed on the DAY BEFORE the birthday in Phoenix terms** — 14 of them
between `21:02` and `23:13` Phoenix, and `palustrine` (UTC+1) a full `16:03` Phoenix the
previous afternoon. **Exactly one — `blamprul`, at UTC-7 — landed on the Phoenix-correct
day**, at `00:03`.

In other words: **read in the estate's own Phoenix convention, today's birthday bot is
wrong about the date 15 times out of 16.** It is right in each member's own timezone,
which is the whole point of the design — but a Phoenix-anchored F6 that simply "kept the
existing hour" would shift every announcement by a day.

**Open question for the owner (F6 cutover):** does Black Bloc replicate per-member local
midnight, or post once at a fixed hour? A fixed Phoenix hour is simpler and matches the
estate's Phoenix convention, but will move every existing member's announcement.

### The wording to match

Every announcement is an **embed** — one line, no title, no footer, no fields:

```
embed.description = "Happy Birthday **{display_name}**!"
embed.color       = #4eefff   (light cyan)
embed.title       = null      embed.footer = null      content = "" (empty)
```

Real examples, exactly as posted:

```text
Happy Birthday **Thormungandr**!
Happy Birthday **[40] PT**!
Happy Birthday **(Umazing) nadia**!
Happy Birthday **[Champrul] Champrul**!
```

⚠️ **The name is the member's Discord display name at post time, verbatim** — bracketed
nickname prefixes and all. `[40] PT` shows the server's habit of putting the age in the
nickname; **Birthday Bot did not compute that 40**, it just echoed the nickname.

**No role is mentioned, granted or announced**, and **no ping** appears in any of the 16.
The only interaction is organic: one post carries a 🫡 ×2 reaction.

### Cross-validation against the existing export

**All 16 announcement dates match `archive/current-bots/birthday-bot-export-2026-08-05.md`
exactly** (interpreting each in its own implied local timezone). That independently
validates both the export and the local-midnight reading.

Two roster snapshots were also recovered from `#bot-control`, showing the list is not
static — **37 birthdays on 2026-02-01, 38 minutes later, 39 on 2026-08-05** — and the
Feb-2026 names differ from the Aug-2026 export (members join and leave). **The Aug-2026
export remains the import source of truth.**

### Still not measured in section C

- **How the `🎂` role is applied.** No announcement grants or mentions it, and Birthday Bot
  has no `manage_roles`. Unresolved.
- **Birthday Bot's configured channel/hour settings** as stored in its dashboard — inferred
  from output, never read from config.
- **Why 5 export rows never produced an announcement** in range (Feb 15, Mar 20, Apr 12,
  Apr 17, Jun 24). Most likely those members left or opted out; not verified.
- Birthday Bot is **running on the free tier and rate-limited by voting** — `#bot-control`
  holds 6 `Vote Required!` refusals. Its `list` command is intermittently unavailable.

---

## D. Carl-bot role features — ✅ MEASURED: 5 reaction-role panels

**27 Carl-bot messages recovered** across 7 channels: `#bot-control` (11), `#carlbot-logs` (7), `#roles` (5), `#welcome` (1), `#join-log` (1), `#mute-me-bot-test-spam` (1), `#Archi Lists` (1).

### The 5 role panels in `#roles` (`1285782324558172180`)

All 5 are **reaction-role** panels — plain embeds with reactions, **no buttons and no
select menus** (`components` is empty on every one). Reaction counts are a measured lower
bound on how many members hold each role.

#### Would you like any pronouns displayed?

`1285788538885111898` · posted 2024-09-18 02:24:36 UTC / 2024-09-17 19:24:36 Phoenix · 85 total reactions

> Pick one, or multiple, sets of pronouns to have displayed on your profile as a role.

| Emoji | → Role | Role ID | Members who reacted |
|---|---|---|---|
| ❤️ | `He/Him` | `1285785434131005474` | 32 |
| 💙 | `She/Her` | `1285785449541144607` | 17 |
| 💚 | `He/They` | `1285785451591897108` | 11 |
| 🤎 | `She/They` | `1285785453412220989` | 7 |
| 🤍 | `They/He` | `1285785455199260712` | 5 |
| 🧡 | `They/She` | `1285785456918925362` | 2 |
| 💜 | `They/Them` | `1285785458797711472` | 6 |
| 💛 | `It/Its` | `1285785460647526522` | 3 |
| 💞 | `Ask my pronouns` | `1285786169392762952` | 2 |

Panel text labels the last one *“Ask me!”*; the role is named **Ask my pronouns**.

#### How do you like to enjoy your games?

`1285792084816560202` · posted 2024-09-18 02:38:41 UTC / 2024-09-17 19:38:41 Phoenix · 142 total reactions

> Pick what applies best to you.

| Emoji | → Role | Role ID | Members who reacted |
|---|---|---|---|
| 🏎️ | `Speedrunner` | `1285790096536109077` | 55 |
| 🛻 | `Challenge Runner` | `1285790140538683464` | 21 |
| 🚋 | `Score Attacker` | `1285790163380867146` | 11 |
| 🚑 | `Ranked Gamer` | `1285790268192460810` | 16 |
| 🚲 | `Casual` | `1285790198646706286` | 39 |

Emoji→role names match 1:1. `Speedrunner` is the most-taken role on the server (55).

#### Would you like to learn or mentor others?

`1285793481721380866` · posted 2024-09-18 02:44:14 UTC / 2024-09-17 19:44:14 Phoenix · 60 total reactions

> These are opt in roles for learning a skill whether it be speedrunning, challenge running, or even fighting games. These are entirely opt in, though these are pingable.

| Emoji | → Role | Role ID | Members who reacted |
|---|---|---|---|
| 🧙 | `Mentor` | `1075115919967273000` | 19 |
| 🥷 | `Initiate` | `1075117204447703040` | 41 |

⚠️ **Replication gotcha:** the panel TEXT uses skin-tone emoji 🧙🏿 / 🥷🏿, but the actual reactions are the **unmodified** 🧙 / 🥷. Copy the reactions, not the text.

#### Miscellanous Roles

`1413703747359604787` · posted 2025-09-06 01:53:58 UTC / 2025-09-05 18:53:58 Phoenix · 300 total reactions

> Select any of the things below that you are into! You'll see additional channels to be able to bond over common interests.

| Emoji | → Role | Role ID | Members who reacted |
|---|---|---|---|
| 🏈 | `Sports` | `1413642880790167653` | 15 |
| 🔢 | `Squads` | `1413643063145926666` | 42 |
| 📺 | `Shows` | `1413643112965738506` | 45 |
| 🎶 | `Musichead` | `1413643194511659102` | 46 |
| 🧑‍🍳 | `Foodie` | `1413643284064108544` | 41 |
| 🎲 | `RPGer` | `1413643323876573185` | 46 |
| 🪅 | `Randos` | `1456219128921718939` | 30 |
| 🍵 | `QOTW` | `1474849344644710441` | 35 |

Title is misspelled *“Miscellanous”* in the original. Panel labels differ from role names: *Squads/Knuck Up*→`Squads`, *Shows, Anime, and Movies*→`Shows`, *Music*→`Musichead`, *RPGs*→`RPGer`, *Randos / Archipelago*→`Randos`, *Question of the Week*→`QOTW`. ⚠️ 🧑‍🍳 is a ZWJ sequence — copy the bytes exactly. **These roles unlock channels**, so this panel is load-bearing for access.

#### Event Alerts

`1515108632017109054` · posted 2026-06-12 21:40:47 UTC / 2026-06-12 14:40:47 Phoenix · 25 total reactions

> Want to know when a Black in a Flash member is on a GDQ Hotfix or another gaming marathon? Click the reaction below to add this role!

| Emoji | → Role | Role ID | Members who reacted |
|---|---|---|---|
| <:JoyGAMING:1337948924844965931> | `Marathons` | `1515068917628801135` | 25 |

The role name is **not** in the panel text — this mapping is INFERRED, but strongly: the `Marathons` role was created `2026-06-12 19:02Z` and this panel posted `2026-06-12 21:40Z`, 2h38m later, with no other role created nearby. Uses a **custom server emoji**, not unicode.

**Coverage check:** the 5 panels offer **23 distinct roles**. Cross-referenced against
section B, that accounts for every zero-permission self-assign role in the server except
`Live Runner` and `🎂`, which are not self-assignable.

### 🔑 Carl-bot automod configuration — the F7 spec, measured

Recovered from `#mute-me-bot-test-spam` (`1542332531196559391`, posted **2026-08-27
00:38:50 UTC / 2026-08-26 17:38:50 Phoenix**) — the owner ran Carl-bot's automod dump. This
is the *“Carl export”* `docs/TODO.md` F7 was waiting on.

| Automod module | Configuration | Punishment |
|---|---|---|
| Slowmode | Ratelimit `6/4s` | **None** |
| **Mentionspam** | Ratelimit `5/30s` | **delete, warn, tempmute (5m)** |
| Linkspam | Permission level `Blacklist`, ratelimit `1/1s` | **None** |
| **Invitespam** | ❌ Off — but **Norole mode ✅ Enabled** | **delete, warn, tempmute (10m)** |
| Bad words | (list not shown by the dump) | **None** |
| **Honeypot** | Channels: **None** | **None** |
| Attachmentspam | No ratelimit | None |
| Caps lock | Threshold: None | None |
| Warn action | Threshold **8** | **None** |
| Whitelisted roles | **None** | — |
| Whitelisted channels | **None** | — |
| Log channel | **None (defaults to modlogs)** | — |
| Drama channel | None | — |
| Delete files | ❌ Off | — |
| Media only channels | None | — |

**What F7 should take from this:**

1. ⚠️ **Only TWO modules actually punish anything** — mention-spam and invite-spam. Every
   other module is configured but set to `Punishment: None`, i.e. detection without
   action. Copying "Carl's settings" wholesale would copy mostly no-ops.
2. ⚠️ **`Warn action` threshold is 8 with punishment `None`** — warnings accumulate and
   nothing ever happens at the threshold. Ask the owner whether that is intended before
   replicating it.
3. **Whitelisted roles and channels are both `None`.** The TODO's *"exceptions list to be
   fine-tuned (role-based exceptions)"* has **no existing configuration to inherit** —
   it is a greenfield decision.
4. **`Norole mode` on invite-spam** is the real anti-raid control: it targets members with
   no roles, which pairs with the `#landing` → `Member` gate.
5. **Honeypot is present-but-off**, confirming F9 is new work.

### Carl-bot mod log — 7 real automod actions

`#carlbot-logs` (`1285782812229763092`), case numbering is Carl-bot's own:

| Case | When (UTC) | Reason as logged |
|---|---|---|
| 1 | 2024-10-01 15:09 | Automatic action for spamming mentions (`4/6s`) |
| 2 | 2024-10-01 22:03 | Automatic action for spamming mentions (`4/6s`) |
| 3 | 2024-10-08 18:53 | Automatic action for spamming mentions (`4/6s`) |
| 4 | 2024-10-28 14:57 | Automatic action for spamming mentions (`4/6s`) |
| 5 | 2024-11-08 22:03 | Automatic action for **using a blacklisted word** |
| 6 | 2026-01-18 02:36 | Automatic action for spamming mentions (`10/30s`) |
| 7 | 2026-01-18 02:37 | Automatic action for spamming mentions (`10/30s`) |

Log embed shape: title `warn | case N`, description `**Offender:** … **Reason:** … 
**Responsible moderator:** Carl-bot#1536`, footer `ID: <user-id>`.

⚠️ **The thresholds in the logs do not match the current config** — `4/6s` in 2024, `10/30s`
in Jan 2026, `5/30s` today. **Mention-spam has been retuned at least twice**, which is
evidence the owner's *"fine-tune the exceptions"* instinct comes from real friction. Also
note: **7 automod actions in ~2 years** on a 125-member server — this is a quiet server,
and F7 should not be tuned as if it were busy.

### Carl-bot: welcome, starboard, logs

| Kind | Status |
|---|---|
| **Welcome / rules** | ✅ `#welcome` `1285806434050768927` — plain markdown, ❤️ ×74, **no components**. Full text below. |
| **Mod log** | ✅ `#carlbot-logs` — 7 cases above. |
| **Role panels** | ✅ 5 in `#roles`. |
| **Starboard** | ❌ **Not in use.** No starboard channel exists and no Carl-bot starboard post appears in any of the 128 channels swept. |
| **Reminders** | ✅ In use — Carl-bot reminder in thread *Archi Lists* (`New Reminder \| ID:93823800` … *"I'll remind you in 3 days about: count poll"*). Minor, but a feature members touch. |
| **Autorole on `#landing`** | ❓ Unconfirmed — 0 bot messages in `#landing`; the grant is silent. |

The `#welcome` rules text is reproduced verbatim for reuse:

```text
Welcome to** Black in a Flash**, a dedicated space for Black gamers!  While we appreciate
and see multiple teams around the content creation space we don't see one that is just for
us, and that is what this Discord hopes to alleviate: the creation of a space where we can
authentically and openly be ourselves.
# Familiarize yourselves with the rules before you join the discord.
**Failure to comply with the rules may lead to moderator action.**

***1. The moderation team reserve the right to remove anyone from the space.***
> If you cannot abide the rules or plainly speaking are not a good fit for the space, the
> moderators can remove you at will.

***2. Be respectful of others.***
> We will not tolerate any forms of harassment or bigotry, such as- but not limited to-
> harassment about race, gender/identity expression, sexual orientation, religion,
> disability, physical appearances. There's a line between a friendly roast and being a jerk.

***3. First and foremost, this space is to adapt, learn, and grow.***
> Let's try to keep that as the primary focus. It's okay to have off topic conversations or
> to be upset about things, but this is a space to empower ourselves. If you are going to
> detract from the experience of others, there may be moderator intervention.

You can head to the landing channel and type a message so you gain access to the rest of
the discord. If you are unsure of something, you are welcome to ping the Aunties / Uncles role.
```

**Onboarding flow, now confirmed end to end:** `#welcome` (rules) → post any message in
`#landing` → receive `Member` → the rest of the server unlocks → self-assign roles in
`#roles`. Escalation is *ping `@Aunties / Uncles`*.

---

## E. YAGPDB features in use — ✅ MEASURED

**208 YAGPDB messages recovered**: `#live-now` (199), `#mod-central` (4), `#mute-me-bot-test-spam` (2), `#announcements` (1), `#join-log` (1), `#Archipelago Weeklies Setup` (1).

### 1. Twitch go-live announcements — the main feature (199 messages)

**YAGPDB owns `#live-now` outright.** Content template, measured on 195 of 199 posts:

```text
REGULATORS! Mount up! **{twitch_login}** is currently streaming **{game}**! Check it out: https://www.twitch.tv/{login}
```

Real examples:

```text
REGULATORS! Mount up! **thormungandr** is currently streaming **Magic: The Gathering**! Check it out: https://www.twitch.tv/thormungandr
REGULATORS! Mount up! **franthescrivener** is currently streaming **OCTOPATH TRAVELER II**! Check it out: https://www.twitch.tv/franthescrivener
REGULATORS! Mount up! **jcstrife** is currently streaming **Splatoon RAIDERS**! Check it out: https://www.twitch.tv/jc_strife
```

- **`REGULATORS! Mount up!` is a custom prefix** configured by the server, not YAGPDB
  default. **F1 must keep it** — it is the server's voice.
- ⚠️ **4 of 199 posts render the game as `****` (empty)** — the streamer had no category
  set. **F1 needs a fallback for a missing game name**; YAGPDB does not have one.
- ⚠️ **The Twitch login is not the Discord name.** `jcstrife` → `twitch.tv/jc_strife`,
  `thepresidentnoir` → `twitch.tv/prez`. **F1's `/twitch link` identity mapping is
  mandatory, not optional** — a name-guessing approach would break on these.
- The rich card underneath is **Discord's own Twitch link preview**, not a YAGPDB embed:
  title `{DisplayName} - Live on Twitch`, description `{stream title} | Streaming {game}.`
  (sometimes `… for N viewers.`), thumbnail, no colour. **Black Bloc gets this free by
  posting the URL** — no Helix call needed for the card itself.

### 2. Reaction polls (not role menus)

**No YAGPDB role menu exists anywhere in the server** — all role panels are Carl-bot's.
YAGPDB is instead used for numbered reaction polls:

| Where | When (UTC) | Poll | Votes |
|---|---|---|---|
| `#announcements` `1502334608426012813` | 2026-05-08 15:41 | **BAF Community Events** — 1⃣ Sinners Watch Party II · 2⃣ Game Night · 3⃣ Anime Watch Party (Lucky Star) · 4⃣ Other | 11 / 20 / 10 / 1 |
| thread *Archipelago Weeklies Setup* `1532135636067156205` | 2026-07-29 21:20 | **When would you rather play the next Archi?** — 1⃣ 8/9-8/15 · 2⃣ 8/16-8/22 · 3⃣ Other | 10 / 8 / 3 |

### 3. Timezone conversion — directly relevant to F4

Four YAGPDB posts in `#mod-central` (Feb 2026) are **timestamp conversions**: an empty embed
carrying only a `timestamp` plus the footer *`Above time (HH:00 GMT) in your local time`* —
YAGPDB rendering a time in each viewer's local zone.

⚠️ **The staff already have a per-viewer timezone habit, and it is a WORSE mechanism than
the one F4 plans.** `docs/TODO.md` F4 specifies HammerTime `<t:…>` markers, which Discord
renders natively per viewer with no bot involved. **F4's approach is the upgrade** — worth
saying so when it ships, because staff will recognise the behaviour.

### 4. Automod — ✅ CONFIRMED NOT IN USE

`docs/TODO.md` F7 records the owner's claim that *"YAGPDB runs NO automod ruleset"*. **That
is now measured, not asserted**, from two YAGPDB replies in `#mute-me-bot-test-spam` dated
**2026-08-27 00:22–00:23 UTC / 2026-08-26 17:22–17:23 Phoenix**:

```text
1542328423207411822:  No automod v2 rulesets set up on this server
1542328563691167754:  [embed] Automod logs
                      ```
                      No Entries```  RS = ruleset, R = rule, TR = trigger
```

**All automod on this server is Carl-bot's** (section D). YAGPDB does go-live posts, polls
and time conversion only.

### 5. Not found for YAGPDB

- **No custom-command output** was observed in any of the 128 channels swept.
- **No YouTube feed** posts — F3 has no incumbent to replace.
- **No role menus, no autorole message.** Whether YAGPDB owns the silent `#landing` →
  `Member` autorole is **still unconfirmed** (see section B).

---

## F. Other bots present

**8 bot/webhook authors** appeared across the 12,488 messages swept. This
supersedes the role-derived list from the blocked pass — it found bots that hold no managed
role, and it separates bots that *post* from bots that merely *joined*.

| Bot | ID | Msgs in sweep | Where | Last seen (UTC) | What it does here |
|---|---|---|---|---|---|
| `YAGPDB.xyz#8760` | `204255221017214977` | 208 | `#live-now`, `#mod-central`, `#mute-me-bot-test-spam` | 2026-08-27 00:23 | **Go-live feed for `#live-now`**, reaction polls, timezone conversion. No automod. → F1/F2 |
| `Wordle#2092` *(webhook)* | `1211781489931452447` | 155 | `#wordle-central` | 2026-08-27 00:36 | Discord's built-in **Wordle activity webhook**. Posts *“X was playing”* + a nightly streak summary with a `Play now!` button. **Not in the TODO's replace list.** |
| `Carl-bot#1536` | `235148962103951360` | 27 | `#bot-control`, `#carlbot-logs`, `#roles` | 2026-08-27 00:38 | **All 5 role panels**, all automod, mod log, welcome/rules, reminders. → F7 + role panels |
| `ModMail#5460` | `575252669443211264` | 24 | `#bot-control`, `#modmail-log`, `#nadiahooligan` | 2026-08-16 17:31 | Ticket-per-user channels, `New Ticket` / `Message Received` / `Message Sent` embeds. → F11 |
| `baf#0659` | `1411490878345711660` | 19 | `#bot-control`, `#join-log` | 2025-09-01 13:35 | ⚠️ **A previous self-hosted bot — a Red-DiscordBot V3 instance.** Only ever active 2025-08-31→09-01 in `#bot-control`. Dormant for ~1 year. |
| `Birthday Bot#5876` | `656621136808902656` | 14 | `#bot-control`, `#return-of-the-gen` | 2026-08-10 06:02 | Birthday announcements in `#return-of-the-gen` (13 of these 14 are `/list` + vote-gate replies in `#bot-control`; the **deep scan found 16 real announcements**). Free tier, vote-gated. → F6 |
| `Black Block#1423` | `1291857406979997861` | 1 | `#join-log` | 2025-09-19 03:55 | ⚠️ **An earlier “Black Block” bot.** Its ONLY message is its own join notice (2025-09-19). Never posted. **Not the current `Black_Bloc` app.** |
| `Verification Bot#0883` | `1290862874742362212` | 1 | `#join-log` | 2024-10-02 18:03 | Its ONLY message is its own join notice (2024-10-02). **Never posted in ~2 years — effectively dormant.** |

### Corrections to the earlier bot census

- 🔎 **`Wordle#2092` (`1211781489931452447`) is a bot nobody had listed.** It is a *webhook*,
  so it holds no managed role and the role-derived census missed it entirely. It is the
  busiest bot on the server after YAGPDB (155 of `#wordle-central`'s last 200 messages) and
  the community clearly uses it — *“Your group is on a 422 day streak!”*. **It is Discord's
  own activity feature, so Black Bloc should not try to replace it** — but it should be on
  the inventory so nobody is surprised.
- 🔎 **`baf#0659` and `Black Block#1423` are PRIOR attempts at this same project.** Neither
  is the current app (`Black_Bloc#6132`, `1542317881822281739`). `baf#0659` was a
  Red-DiscordBot install; `Black Block#1423` never posted at all. **Ask the owner whether
  both should be removed from the server** — each still occupies a bot slot and
  `Black Block#1423` is confusingly named.
- ✅ **`Verification Bot` downgraded from "fifth incumbent" to "dormant".** The earlier pass
  flagged it as a missing incumbent. With message history it turns out its only message is
  its own join notice — **it has never posted in ~2 years**. Still worth asking whether to
  remove it, but it is not a feature to replace.
- **`#join-log` is not a bot feature.** All 151 messages are Discord-native `new_member`
  system notices. The 5 "bot messages" there are bots' own join notices.

**ModMail's ticket schema, measured** — F11 must replicate it:

| Element | Measured value |
|---|---|
| Category | `ModMail` (`1442613057628012594`) |
| Index channel | `#modmail-log` — one `New Ticket` embed per ticket |
| Ticket channel | one per user, **named after the username** (5 open: `kurushiidrive`, `yatogaminl`, `riekelt`, `shindarkshadow`, `nadiahooligan`) |
| Routing store | the channel **topic**: `ModMail Channel <user-id> <dm-channel-id> (Please do not change this)` |
| Embed footer | `<username> \| <user-id>` on every ticket message |
| Message kinds | `New Ticket`, `Message Received` (from user), `Message Sent` (staff reply) |
| Staff prefix | `=` — messages starting with it are **ignored and used for staff-only discussion in the ticket channel** |
| Close | `=close [reason]` |

⚠️ **The staff-discussion-inside-the-ticket behaviour is the non-obvious part** and the one
most likely to be missed: staff can talk in the same channel without the user seeing it, by
prefixing `=`. A thread-based F11 design must provide an equivalent or staff will lose a
workflow they use.

---

## G. `#live-now` — ✅ MEASURED

**199 of the last 200 messages are YAGPDB. Exactly 1 is human.** This is a bot feed
with effectively no human conversation in it.

| Field | Value |
|---|---|
| Channel | `#live-now` (`1225457308230746202`), *House Parties* |
| Window measured | `2026-08-02 16:09` → `2026-08-26 23:01` UTC (~24 days) |
| Posts in window | 199 bot + 1 human = 200 |
| Sole poster | `YAGPDB.xyz#8760` |
| Distinct streamers announced | **30** |
| Rate | ~8 posts/day |
| Reactions on bot posts | **none at all** — 0 reactions across all 199 |
| Topic | *"Wanna let people know when you're going live? Post your links here and let everyone turn up for it!"* |

⚠️ **The topic is stale and actively misleading** — it invites humans to post links, but the
channel is 99.5% automated. Worth correcting when F1 ships.

✅ **This CORRECTS the blocked pass**, which inferred from that topic that `#live-now` was a
human self-post channel and warned F2 might have nothing to replace. **That inference was
wrong.** There is a fully-working incumbent go-live feed, and F1/F2 is a *replacement* with
a real cutover, not a greenfield build. (The inference was labelled as an inference at the
time — this is exactly why.)

**Most-announced streamers in the window** (a ready-made F1/F2 test cohort):

| Streamer | Posts | | Streamer | Posts |
|---|---|---|---|---|
| `thormungandr` | 18 | | `syilensa` | 14 |
| `mrpainandsorrow` | 14 | | `supernamu` | 12 |
| `champrul` | 12 | | `glitchaston` | 11 |
| `thepresidentnoir` | 10 | | `rockstarlexxi` | 10 |
| `jcstrife` | 10 | | `zvrra` | 10 |
| `thestampstories` | 8 | | `azurelv_7` | 8 |
| `yatogaminl` | 8 | | `pleasantlytwstd` | 7 |
| `mcknux` | 6 | | `riekelt` | 6 |
| `popnotarts` | 6 | | `smliquid` | 6 |
| `musume` | 4 | | `rosheeki` | 3 |

Plus 10 more with 1–3 posts each. **30 distinct streamers out of ~125 members is ~24% of
the server** — F1/F2's opt-out therefore matters to a large minority, not a handful.

⚠️ **Re-announcement behaviour to decide on:** several streamers appear multiple times in a
single day (`thormungandr` posted 15:06 and again 16:xx on 2026-08-03; `zvrra` at 14:29 and
18:17 on 2026-08-05). YAGPDB re-posts when a stream restarts or changes category. **F1 must
choose a debounce window** or it will be noisier than the bot it replaces.

**Other `live`-named channels** are marathon production rooms, not feeds:
`#live-production` (`1337090172394930238`), `#live-prod` (`1430627630821933107`),
`#live-production` (`1534777453556273263`), `#live-vol-updates` (`1467777240459772038`),
voice `Live Channel` (`1285365589703000134`) and
`🔴 LIVE CHANNEL (ACTIVE RUNNERS + COMMS ONLY)` (`1430632176508080148`). All measured at 0
bot messages. `#live-now` is the only F1 target.

---

## What could NOT be read

**Channel access is no longer a limitation: 0 of 128 channels returned 403.** What remains:

| Not measured | Why | How to get it |
|---|---|---|
| **Exact member counts per role** | `guild.fetch_members()` → `ClientException: Intents.members must be enabled` (GUILD_MEMBERS privileged intent is off for this app) | Enable the intent in the Developer Portal, or accept the reaction counts in section D as lower bounds |
| **How the `🎂` role is applied** | No announcement grants or mentions it; Birthday Bot has no `manage_roles` | Ask the owner / read the Birthday Bot dashboard |
| **Which bot owns the `#landing` → `Member` autorole** | The grant is silent — 0 bot messages in `#landing` | Carl-bot or YAGPDB dashboard |
| **Carl-bot's bad-words list** | The automod dump shows the module but not its word list | Carl-bot dashboard |
| **Bot dashboard configuration generally** | External web config, not exposed over the Discord API | Owner |
| **Audit log** (who configured what, when) | Bot lacks `view_audit_log` | Grant the permission if provenance matters |
| **Installed-integrations list** | Requires `manage_guild`, which the bot lacks | Server Settings → Integrations |
| **Anything older than the scan window** | 200/channel for the sweep; 6000 each for 5 deep-scanned channels | Re-run with a higher `SCAN_LIMIT` |
| **Archived threads** | Only *active* threads were pulled (`guild.active_threads()`) | Add `archived_threads()` to the sweep |

**Findings that are INFERENCE, not measurement — flagged so nobody promotes them:**

- That Birthday Bot's varying hour is caused by **per-user timezone settings**. The 16
  timestamps and their implied offsets are measured; the mechanism is inferred.
- That <:JoyGAMING:> on the *Event Alerts* panel maps to the **`Marathons`** role. Inferred
  from role/message creation times 2h38m apart on the same day; the panel text never names
  the role.
- That `Live Runner` is an **event-production** role rather than a streaming role. Inferred
  from naming, hoisting and the fact that the go-live feed assigns nothing.
- That the ❤️ ×74 on the `#welcome` rules post is **ordinary reactions, not a reaction
  role**. Supported by it being the only emoji present and the role panels all living in
  `#roles` — but not confirmed from config.
- That the ~268 webhook messages in `#off-topic` dated 2025-09-01 13:36–13:43 are a
  **bulk channel-history import** (human content, `#0000` discriminators, all within 7
  minutes) rather than bot activity. They are excluded from the bot census on that basis.

---

## Rerun instructions

Scripts live in `scripts/scan/` (uncommitted, read-only, gateway never started):

| Script | Does |
|---|---|
| `scan_structure.py` | channels + roles → JSON |
| `scan_messages.py` | `history(limit=$SCAN_LIMIT)` over every text-capable channel + active threads, priority-ordered; records every author and every bot message with UTC **and** America/Phoenix timestamps, embeds, components, reactions |
| `deep_birthday.py` | deep history (`$DEEP_LIMIT`) over 5 high-value channels, bot messages only |
| `diag_perms2.py` | per-channel View/History verdict + the overwrites causing it |
| `scan_bots.py` | bot census from managed roles |
| `analyse*.py` | the summaries this report is built from |
| `build_report.py` | renders this document |

```powershell
$env:SCAN_OUT='<path>.json'; $env:SCAN_LIMIT='200'
& .\.venv\Scripts\python.exe .\scripts\scan\scan_messages.py
$env:SCRATCH='<scratch dir>'; $env:REPORT_OUT='docs/archive/current-bots/discord-scan-2026-08-26.md'
& .\.venv\Scripts\python.exe .\scripts\scan\build_report.py
```
