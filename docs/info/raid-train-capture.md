# Raid trains — what r3dlabs.com does, captured for request #1

**Audience:** the owner deciding request #1, and the session that designs it.
**Status:** TRACKED · reference (a capture, not a design). ✅ **The design and the build
both happened:** [`phase18-design.md`](phase18-design.md) shipped as merge `0bb3835`
(deployed `7b1c592`, 2026-09-03, `raidtrain_mode` off), and `/raidtrain` became ONE
command opening a panel in **v76** `2dd2689` (2026-09-04) —
[`raidtrain-panel-design.md`](raidtrain-panel-design.md). A `raidtrain_scheduled_name_template`
key followed in **v104** (2026-09-10). So the line "the design doc comes after the owner
picks a scope" is history; this file is the capture the scope was picked FROM.
**Last verified: 2026-09-11 09:30** — docs-wide staleness pass: it cites **no repo path**
at all, so nothing in it can rot against this tree, and the capture itself is unchanged.
⚠️ **NOT re-checked: r3dlabs.com was NOT re-visited**, so every row is still the
2026-09-02 reading. Before that, **2026-09-02** against
https://r3dlabs.com (home, `/features`, one live event page), read through
the browser while signed OUT — the signed-in organizer UI, R3ddyBot's chat
commands and the OBS/Stream Deck tools were NOT exercised; their rows come
from the site's own marketing copy.

**The request (Pawpette, staff, filed 2026-09-02 16:08 Phoenix, request #1):**

> https://r3dlabs.com — raid train site, want to see if the bot could do this
> instead since this site requires twitch connection. We'd only need it for
> sign ups, slot availability, and when the schedule is live it can DM someone
> 30 minutes before their slot (if possible)!

## What a raid train is (their definition, paraphrased)

A dated event split into consecutive time slots (typically 1 h). Each slot is
claimed by one streamer. When a slot ends, that streamer **raids** (sends their
viewers to) the next streamer in the lineup, so the audience travels down the
train. Organizers build the lineup; contributors claim slots, check in before
going live, and receive the raid from the previous slot.

## Feature inventory

**Bucket** is my first-pass mapping, for the owner to overrule:
**ASKED** = named in the request · **FIT** = cheap because Black Bloc already
has the machinery · **LATER** = real but a second phase · **NO** = belongs to
Twitch/OBS/SMS, not to a Discord bot.

### Events and slots

| r3dlabs feature | Bucket | Black Bloc already has |
|---|---|---|
| Create a raid-train event: title, description, start, duration (≤1024 h), rules, visibility (public / invite) | **ASKED** (the container for sign-ups) | Phase 5 event store + `/event` shape |
| Time slots of a set length; lineup = ordered list of slots | **ASKED** | — (new table) |
| Claim an open slot; reserve; release | **ASKED** ("sign ups") | member identity via Discord, streamer identity via `/twitch link` |
| Open-slot view ("35/50 filled", which hours are free) | **ASKED** ("slot availability") | dashboard page pattern + a slash `status` |
| Organizer invites streamers and **approves requests** to join | FIT | Requests/approval pattern exists (Phase 13) |
| Organizer reorders and **locks** slots | FIT | — |
| Track participation / **check-in** before going live | LATER | go-live detection (Twitch EventSub) could check in automatically |
| Event group chat for contributors | FIT | a thread in the event's channel |
| Event files (150 MB per event) | NO | Discord attachments already do this |
| Categories (music / gaming / creative) + tags (genre, game) for discovery | LATER | tags table pattern |
| Series = recurring trains grouped ("Ev. 82") | LATER | Phase 5 recurring events |
| Teams = streamer collectives that host events | NO for now | the server IS the team |
| Event calendar of everything you're in | FIT | `/schedule` page already lists events |
| Custom event colours / backgrounds / video | NO | embed colour at most |

### Reminders and the live run

| r3dlabs feature | Bucket | Black Bloc already has |
|---|---|---|
| **Reminder before your slot** (their default: in-app / email; SMS is paid) | **ASKED** ("DM 30 min before") | DM path + a `tasks.loop` poll (the Twitch/YouTube pollers) |
| "Tells your chat the moment your target goes live" (R3ddyBot) | FIT | go-live detection already fires; post to the event thread |
| Automatic Twitch **stream title** when checked in and live | NO | needs the streamer's Twitch OAuth grant — the exact thing the request wants to avoid |
| `!raidnow` — the bot performs the raid from Twitch chat | NO | same: needs a Twitch channel-level token per streamer |
| Posts lineup / calendar / organizer messages into Twitch chat | NO | Twitch-chat side; Discord gets the equivalent |
| Live spotlight: who on the train is on air right now, ranked | LATER | go-live state per member is known |

### Everything else on the site

| r3dlabs feature | Bucket | Note |
|---|---|---|
| Streamer DMs / messaging | NO | Discord is the messaging |
| Public community profile (channel, stats, links, bio) | NO | Discord profile / Members page |
| Activity feed | NO | |
| Flyer Studio (promo art from the lineup, AI backgrounds) | LATER, maybe | an embed/card image from the lineup is the cheap 80 % |
| Twitch schedule sync into the profile | NO | needs Twitch OAuth |
| SMS reminders / check-ins / alerts (paid) | NO | DM is the Discord-native equivalent |
| Mixcloud integration, profile branding, premium badge | NO | |
| FirePanel (OBS dock with raid queue + raid button) | NO | desktop/OBS tooling |
| Stream Deck plugin (raid with one key) | NO | |
| Advanced calendar with external/manual events | NO | |

## What the request actually needs — the minimal build

1. **Event + slots**: `/raidtrain create` (title, start, slot length, slot
   count / duration) — organizer only (staff or a `raid_organizer` role,
   configurable). Stored as its own table keyed to the guild.
2. **Sign-ups**: `/raidtrain claim <slot>` / `release`; organizer `assign`,
   `lock`, `reorder`. Requires the member to have `/twitch link`ed, so the
   lineup carries the Twitch name the previous streamer raids.
3. **Availability**: `/raidtrain status` (an embed of the lineup with open
   slots) + a Raid Trains section on the dashboard (events page owns
   "what is scheduled" — extend it, do not add a second page).
4. **Reminder DM**: a poller (10 min floor, `raidtrain_reminder_minutes`
   default 30, configurable both ways) DMs the slot-holder, with the person
   they will be raided BY and the person they raid NEXT in the message.
5. **Nice, nearly free**: post "X is live — the train moves" to the event
   thread from the existing go-live signal; mark the slot checked-in.

Nothing above needs a Twitch OAuth grant from members — which is the whole
point of the request. Everything that would (stream titles, `!raidnow`,
schedule sync) is bucketed NO.

**Size estimate (guess, not measured):** one subsystem — a `content/raidtrain`
cog, one schema bump, one dashboard section, tests. Same class as Phase 16.
