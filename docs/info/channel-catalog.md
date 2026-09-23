# The channel catalog — every live text channel and what it is for

> **Audience:** the owner, who approves or rewrites each description, and whoever writes the
> approved ones into the bot. **Status:** TRACKED · ✅ **LIVE as v159** (2026-09-23 **14:07** Phoenix, release commit `c54f14a8`). ✅ **The seed is LIVE:** these rows
> ship as `black_bloc/channel_drafts_seed.json` and were seeded at the v159 boot — action 10103
> `chat.channel_drafts_seeded count=94, notes=2` (21:07:27Z); `/api/chat/channels` reads 94 rows, 2 reviewed (the two
> ✅ owner notes, live), 92 drafts left for staff on the Channels page. **This file is now the history of the seed, not
> the place to review** — review happens on <https://blackbloc.heygabi.ai/channels.html>. Until the deploy it read:
> **BUILT, NOT MERGED** with branch `channel-catalog` — nothing here is in the live bot. Secret NAMES only (this file holds none).
> **Last verified: 2026-09-23 14:1x** — the status line above only (live API read at the v159 ritual; the rows below
> were NOT re-compared with the live seed). Before that, **2026-09-23** — the channel list, ids, names and categories were read from the
> live bot with `scripts/read.ps1 -Path /api/ref/channels` (read-only operator token):
> **94 text channels** in **14 categories**, plus **5 forums** not listed here (forums are not in
> the channel list the model reads — `collabs-and-community-events`, `ask-a-gdq-staffer`,
> `modmail`, `requests`, `events`). ⚠️ **NOT checked:** the live topics (the operator API does
> not expose them) and which channels the Member view can read.
>
> **How to read a row.** ✅ is the owner's own description (2026-09-23), ready to use.
> ⚠️ **DRAFT** is the builder's one-sentence guess from the name and category — approve it,
> rewrite it, or leave the channel without a note. **Left out by rule** marks the channels the
> directory skips whatever their note says (an archive category, or the ticket category
> `modmail_category_id`); `—` means it depends on the live settings (`chat_ignore_categories`,
> `chat_visibility_role_id`). Once the build is deployed, the Chat page's **Channel directory**
> section shows each channel's real topic and whether the bot is told about it, and a note is
> saved there or on `/chat` ▸ **Channel notes…**. Design:
> [`channel-catalog-design.md`](channel-catalog-design.md).
>
> ⚠️ **2026-09-23 follow-up (branch `channels-page`, BUILT, NOT MERGED): this table is now the
> SEED, not the review.** Its rows were copied once into `black_bloc/channel_drafts_seed.json`
> (94 rows; the JSON is the source from here on — editing this table changes nothing in the bot),
> and staff review them on the site's **Channels** page (`channels.html`): Use this / Save my
> wording / No note / Reset to the draft. The two ✅ rows become real notes on the first boot.

| id | channel | category | left out by rule | current topic | description |
|---|---|---|---|---|---|
| `1285369365071527997` | `#welcome` | Information | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Where new members land: the rules and how to get into the rest of the server. |
| `1285782324558172180` | `#roles` | Information | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Where members pick their own roles from the role menus. |
| `1452150360293773365` | `#asset-library` | Information | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Shared art, logos and other assets the community can use. |
| `1285381774876344340` | `#announcements` | Information | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Server news and announcements from staff. |
| `1285371141476581509` | `#landing` | The Hole in the Wall | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — The first stop after the rules — say hi here to get into the rest of the server. |
| `1398449806438826025` | `#introductions` | The Hole in the Wall | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Introduce yourself to the community. |
| `1411816390414962700` | `#general-chat` | The Hole in the Wall | — | unknown — the operator API does not expose topics; fill from the page after deploy | ✅ The server's general chat — anything goes, not speedrun-specific. |
| `1474844966021890362` | `#qotw` | The Hole in the Wall | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — The question of the week — answer it and talk about everyone else's answers. |
| `1073710703518683141` | `#daily-wordle` | The Hole in the Wall | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Share your daily Wordle results. |
| `1073710703518683142` | `#venting-and-advice` | The Hole in the Wall | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Get something off your chest or ask for advice; be kind. |
| `1073710703518683143` | `#off-topic` | The Hole in the Wall | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Conversation that fits nowhere else. |
| `1413648696670949376` | `#shows-and-movies` | The Hole in the Wall | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — TV shows and movies — what you are watching and what you think of it. |
| `1413643742308728983` | `#sports-ball` | The Hole in the Wall | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Sports talk — games, teams and results. |
| `1413699977137623121` | `#music-recommendations` | The Hole in the Wall | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Music recommendations — share what you are listening to. |
| `1413700333796069419` | `#recipes-and-food-pics` | The Hole in the Wall | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Recipes and pictures of food you made or ate. |
| `1497233190383915008` | `#gif-spam` | The Hole in the Wall | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Post GIFs freely here. |
| `1524047038562435193` | `#quotes` | The Hole in the Wall | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Funny or memorable things people in the server have said. |
| `1147289379493118033` | `#upcoming-events` | House Parties | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Upcoming community events and when they happen. |
| `1457505283067613287` | `#deals` | House Parties | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Game deals, sales and freebies. |
| `1225457308230746202` | `#live-now` | House Parties | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Announcements for members who are streaming live right now. |
| `1497362790732664893` | `#community-clips` | House Parties | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Clips from community members' streams and videos. |
| `1419778694460866633` | `#opportunities` | House Parties | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Opportunities for members — jobs, calls for runners, collabs and similar. |
| `1437995212122099752` | `#gaming` | Gaming | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — General gaming talk — what everyone is playing. |
| `1076011219351257108` | `#run-prep` | Gaming | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Preparing speedruns — routes, practice and strategy before a run. |
| `1076003845232148580` | `#speed-and-pbs` | Gaming | — | unknown — the operator API does not expose topics; fill from the page after deploy | ✅ Speedrunning records and personal bests — talking about runs, times and PBs, not general chat. |
| `1436166669008502945` | `#squads` | Gaming | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Find people to play with and form squads. |
| `1076005097617760296` | `#knuck-up` | Gaming | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Fighting games — matches, tech and trash talk. |
| `1413701019711442964` | `#rpg` | Gaming | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — RPGs — talking about role-playing games. |
| `1480974710404808837` | `#asian-speedrun-alliance` | Play Cousins | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — The shared channel with the Asian Speedrun Alliance community. |
| `1480297661180678386` | `#fatales` | Play Cousins | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — The shared channel with the Fatales community. |
| `1480974771981258753` | `#lhs` | Play Cousins | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — The shared channel with the LHS community. |
| `1480974833117298790` | `#gdqueer` | Play Cousins | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — The shared channel with the GDQueer community. |
| `1376272041573089402` | `#lab-chat` | Speedrunning Labs | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Chat for the Speedrunning Labs program. |
| `1491507415932469328` | `#the-adult-table` | The Basement | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — A staff or grown-ups-only table for adult conversation. |
| `1094709109841989753` | `#the-main-table` | The Basement | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — The staff table — where staff talk things over. |
| `1094711719797985330` | `#event-heads-up` | The Basement | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Staff heads-up about upcoming events. |
| `1411774767966453791` | `#bot-control` | The Basement | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Where staff run bot commands. |
| `1285782812229763092` | `#carlbot-logs` | The Basement | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Carl-bot's log output. |
| `1073710703518683138` | `#join-log` | The Basement | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — The log of members joining and leaving. |
| `1542316174472380517` | `#blackbloc-logs` | The Basement | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Black Bloc's own log channel. |
| `1496980277841363046` | `#baf-power-quotes` | The Basement | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Power quotes saved for BaF. |
| `1550284332365783091` | `#welcome-test` | The Basement | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Where Black Bloc's rehearsal (shadow) copies are posted for staff to check. |
| `1534971515932643390` | `#welcome` | Back to Black 2027 | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Welcome for the Back to Black 2027 event team. |
| `1534775990704803930` | `#announcements` | Back to Black 2027 | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Announcements for the Back to Black 2027 event team. |
| `1534777301781184522` | `#leads` | Back to Black 2027 | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — The Back to Black 2027 leads' channel. |
| `1534809142546399362` | `#socials` | Back to Black 2027 | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Back to Black 2027 social media planning. |
| `1534777453556273263` | `#live-production` | Back to Black 2027 | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Back to Black 2027 live production. |
| `1534778339569434684` | `#tech-check-chatter` | Back to Black 2027 | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Chatter among Back to Black 2027 tech checkers. |
| `1534778017929498654` | `#runners` | Back to Black 2027 | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Back to Black 2027 runners. |
| `1534778121138602084` | `#committee` | Back to Black 2027 | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — The Back to Black 2027 committee. |
| `1534778880727060622` | `#donations` | Back to Black 2027 | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Back to Black 2027 donations and incentives. |
| `1534998323403034635` | `#interstitials` | Back to Black 2027 | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Back to Black 2027 interstitials — what plays between runs. |
| `1534778635473387610` | `#moderators` | Back to Black 2027 | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Back to Black 2027 moderators. |
| `1546697702790930473` | `#tech-checks` | Back to Black 2027 | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Back to Black 2027 tech checks with runners. |
| `1074781292731842590` | `#who-you-be` | archive | yes — an archive category | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Archived: an old introductions channel. |
| `1073710703518683137` | `#welcome-and-rules` | archive | yes — an archive category | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Archived: the old welcome and rules channel. |
| `1147968944490160261` | `#black-support-hub` | archive | yes — an archive category | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Archived: the old Black support hub. |
| `1073710703518683139` | `#resources` | archive | yes — an archive category | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Archived: an old resources channel. |
| `1285363980516200540` | `#hosts` | Back to Black 2025 | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Back to Black 2025 hosts. |
| `1285364898750267515` | `#committee` | Back to Black 2025 | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — The Back to Black 2025 committee. |
| `1329563943487803473` | `#tech-checkers` | Back to Black 2025 | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Back to Black 2025 tech checkers. |
| `1335035325113831424` | `#donations` | Back to Black 2025 | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Back to Black 2025 donations and incentives. |
| `1285363010692710485` | `#runners` | Back to Black 2025 | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Back to Black 2025 runners. |
| `1285363724890280046` | `#tech-checks` | Back to Black 2025 | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Back to Black 2025 tech checks with runners. |
| `1322311143104184360` | `#mainline-promo-planning` | Back to Black 2025 | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Back to Black 2025 promotion planning for the mainline event. |
| `1285362943155765278` | `#production` | Back to Black 2025 | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Back to Black 2025 production. |
| `1335035068099334164` | `#charity-plaza` | Back to Black 2025 | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Back to Black 2025 charity plaza. |
| `1337090172394930238` | `#live-production` | Back to Black 2025 | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Back to Black 2025 live production. |
| `1285363575556411392` | `#resources` | Back to Black 2025 | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Back to Black 2025 resources for the team. |
| `1445191241217216622` | `#socials-homies` | Back to Black 2026 | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Back to Black 2026 socials and hanging out. |
| `1449940880742944788` | `#btb2026-general` | Back to Black 2026 | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — General chat for the Back to Black 2026 team. |
| `1460453073959915732` | `#btbt2026-leads` | Back to Black 2026 | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — The Back to Black 2026 leads' channel. |
| `1430627630821933107` | `#live-prod` | Back to Black 2026 | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Back to Black 2026 live production. |
| `1472016561047863459` | `#btb2026-yearbook` | Back to Black 2026 | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — The Back to Black 2026 yearbook — memories from the event. |
| `1467777240459772038` | `#live-vol-updates` | Back to Black 2026 | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Updates for Back to Black 2026 live volunteers. |
| `1430626512331083928` | `#runners` | Back to Black 2026 | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Back to Black 2026 runners. |
| `1430625708186800169` | `#tech-checks` | Back to Black 2026 | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Back to Black 2026 tech checks with runners. |
| `1430626931828854975` | `#production` | Back to Black 2026 | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Back to Black 2026 production. |
| `1445157148492435617` | `#mod-central` | Back to Black 2026 | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Back to Black 2026 moderators. |
| `1445191021305790494` | `#tech-checker-chatter` | Back to Black 2026 | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Chatter among Back to Black 2026 tech checkers. |
| `1430625650687086733` | `#committee` | Back to Black 2026 | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — The Back to Black 2026 committee. |
| `1430625933785563198` | `#hosts` | Back to Black 2026 | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Back to Black 2026 hosts. |
| `1430626278142382182` | `#donations` | Back to Black 2026 | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Back to Black 2026 donations and incentives. |
| `1430628292922314803` | `#resources` | Back to Black 2026 | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Back to Black 2026 resources for the team. |
| `1430626798571487272` | `#agdq-promo-planning` | Back to Black 2026 | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Back to Black 2026 promotion planning for AGDQ. |
| `1430639977519382679` | `#interview-brain-dumps` | Back to Black 2026 | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — Back to Black 2026 interview notes and ideas. |
| `1550167775694037075` | `#modmail-log` | BlackMail | — | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — BlackMail's log of tickets and requests. |
| `1442613059704066108` | `#modmail-log` | ModMail | yes — the ticket category | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — The old ModMail log. |
| `1515388560021389463` | `#kurushiidrive` | ModMail | yes — the ticket category | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — A private modmail ticket with one member — not a place to point anyone. |
| `1519898370179858632` | `#yatogaminl` | ModMail | yes — the ticket category | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — A private modmail ticket with one member — not a place to point anyone. |
| `1526703242141237480` | `#riekelt` | ModMail | yes — the ticket category | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — A private modmail ticket with one member — not a place to point anyone. |
| `1530706388215664690` | `#shindarkshadow` | ModMail | yes — the ticket category | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — A private modmail ticket with one member — not a place to point anyone. |
| `1537729008626831410` | `#nadiahooligan` | ModMail | yes — the ticket category | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — A private modmail ticket with one member — not a place to point anyone. |
| `1546281420035723444` | `#mathcat` | ModMail | yes — the ticket category | unknown — the operator API does not expose topics; fill from the page after deploy | ⚠️ DRAFT — A private modmail ticket with one member — not a place to point anyone. |
