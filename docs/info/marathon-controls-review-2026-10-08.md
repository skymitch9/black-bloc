# Marathon controls — streamlining review (2026-10-08)

> **Audience:** the owner (decisions) and the session that builds what he picks. **Status:** TRACKED, a REVIEW — nothing here is built; each numbered decision is put to the owner one at a time and its answer lands in `docs/TODO.md`. **Last verified: 2026-10-08 07:0x Phoenix** — a Fable review agent read the sixteen marathon design docs and the rendering code, MEASURED the live labels and the eleven live marathon rows through the operator token, counted presses per control from the live action log (the window the log exposes: **15 days, 2026-09-23 → 2026-10-08**, not 30), and looked at the drawer and the tracker on the local mock by eye. ⚠️ Not looked at: the thread controls, a run post, the inbox card or the People view rendered in Discord; a Hotfix overlay button live; phone width. Secret NAMES only (none here).
>
> The ask, verbatim (owner, 2026-10-08): *"Can we also review all the buttons on a marathon any we can drop or adjust or rename to have a more streamline experience"*. Already decided the same morning and built on `marathon-controls-tidy` (taken as given): the per-person whole-marathon opt-out leaves the run posts for the People view; "BaF announcements" → "Runner announcements", independent of Host announcements.

## What was measured on live

- 11 marathons, 4 tracked. **`event_mode = none` on all 11.** Every tracked one: Runner (BaF) announcements on (default), Host announcements off (default), `spotlight_mode = follow`; Auto-highlight on for the three that mattered; the ping switch on two.
- Presses per control in the 15-day window:

| Control | Presses | Door |
|---|---|---|
| Marathon event / BaF run/host events | **0** | — |
| Spotlight start/stop on the thread | 2 | thread |
| Spotlight writes from the site | 21 | site (Go-live page or the drawer's copy — the log does not say which) |
| Follow the schedule | 3 | mixed |
| Auto-highlight | 4, all → on, one per marathon at tracking time | thread |
| Ping the marathon role | 4 | thread |
| BaF / Host announcements, Event schedule, BaF event, per-run answer, no-@, marathon opt-out | **0 each** | — |
| Track / Ignore / Unignore | 6 / 1 / 1 | inbox, site |
| Pair / Unpair | 3 / 1 | drawer |
| Post the board / Pause / Rename / Archive / Remove | 1 (+6 automatic) / 0 / 0 / 2 / 1 | |

## Inventory (where a control appears, what it does, what reverses it)

**A. Thread controls** (pinned; 11 buttons, 12 on a Hotfix marathon): Marathon event · BaF run/host events · Spotlight (five labels, one greyed "no channel") · Auto-highlight · Ping the marathon role · BaF announcements · Host announcements · Event schedule (Hotfix) · Marathon tracker ↗ · BaF event follow / yes / no (+ Clear when answered) — plus the `marathon_controls_help` line, which is an explaining blurb under the 2026-10-04 rule. Every switch reverses itself.
**B. Inbox card:** Track · Ignore · Open on the site; tracked → Untrack · Open the thread; ignored → Track anyway. Complete reverse pairs.
**C. Each BaF run's post:** the whole-marathon opt-out (leaving) · per person: Do not announce / Announce / back to the default *for this run* · No @ / @ again · a menu past four people · a state line per person.
**D. People slot view** (Discord and the drawer's slot): link / unlink · Twitch name · Spotlight the PERSON's channel · the marathon opt-out · this run's answer and the @ · Shout it now · Mark done · Make it now (drawer only).
**E. `/event ▸ Marathons…` card:** 14–15 buttons over four rows (read, pause, board, rename, remove, pair, next up, schedule, event, spotlight, ping, archive, track, people).
**F. Site drawer:** tracker link · header · Spotlight block with the channel's whole Go-live card and Pings card copied in · People card · Settings for this marathon (eleven fields + Save) · the bar (Track · Post it to the inbox now · Read it now · Back to the sheet's times · Pause · Rename · Archive · Remove).
**G. Tracker:** Started now / Finished now · More… · day shift · Reset · Undo · zone. Clean.

## One decision wearing two names — found

1. Events ×4 (thread ×2, the drawer's Event select, "Make an event now", the slot's "Make it now") all write `event_mode`; 0 presses.
2. Spotlight ×3 spellings: the thread's start / cancel / stop is the drawer's Follow the schedule switch; the drawer also carries the channel's full Go-live and Pings cards a second time.
3. Auto-highlight vs Runner announcements: two gates on "post about our runners publicly"; every tracked marathon turned both on.
4. Ping the marathon role: three doors, two spellings.
5. BaF event: a 3–4 button row for a reading the bot makes itself; 0 presses, 0 questions ever asked; the question message already has Yes/No.
6. Run state ×2: the tracker's Started/Finished vs the drawer slot's Shout / Mark live / Mark done.
7. Five ways to stop a marathon: Pause, Untrack, Ignore, Archive, Remove.
8. The help line is a blurb; the greyed "no channel" spotlight button renders when it cannot succeed.
9. "Spotlight" means two things on one marathon (the marathon's, a person's channel).

## The proposed streamlined set

**Thread controls — row 0 is the whole message; the help blurb becomes a state line** (marathon · when · "2 of 55 runs are BaF" · spotlight state · the role-ping reason):
- *Before and during the show:* **Runner announcements** · **Host announcements** · **Ping the marathon role** · **Spotlight follows the schedule: on · turn off** (one switch; dates in the state line; no greyed button) · **Marathon tracker ↗**; row 1 only when valid: **one BaF event button** ("BaF event: no (2 of 55 runs) · say yes" / "yes (the show is named …) · say no" / "yes (staff) · clear").
- *After the show:* the state line + **Marathon tracker ↗** · **Archive it**. Switches that can no longer post are not drawn.
- Dropped from the thread: Marathon event, BaF run/host events, Event schedule (the drawer keeps them), Auto-highlight (merged into Runner announcements).

**Each run's post:** one button per person — **Don't announce {name} / Announce {name} / {name}: back to the default** ("for this run" dropped: every button on a run post is about that run); the @ pair moves to the People view; state lines only for exceptions.

**People view** (Discord and the drawer's slot, same set, same order): Link to a member… / Unlink · Twitch name… · **Spotlight their channel…** / Stop · **Opt out of this marathon / Opt back in** · **No @ for {name} / @ {name} again** · **Don't announce {name}** (this run) · Back. The drawer slot drops Shout / Mark live / Mark done / Mark upcoming / Make it now — the tracker owns run state.

**Drawer:** tracker link · header · Spotlight: state + Follow the schedule + Open on Go-live ↗ (the channel's card, dates, pings and announce opt-out fold behind the link — Go-live owns them) · People card · Settings in the thread's order and words, switches writing at once (Save only for typed fields) · bar: **Track · Read it now · Archive it · More…** (Rename, Pause, Post it to the inbox now, Back to the sheet's times, Remove).

**Inbox card:** unchanged. **`/event` card:** People… · Track/Untrack · Read it now · Open on the site ↗ · Back. **Tracker:** unchanged.

## The decisions, by impact (put to the owner one at a time; answers land in TODO.md)

1. Drop Marathon event and BaF run/host events from the thread controls (0 presses; all 11 at `none`; the drawer's Event select and `/event` keep the decision). Rec: yes.
2. Collapse the BaF event row to one button showing the reading and its one reverse. Rec: yes.
3. One Spotlight switch on the thread, worded like the drawer, dates in the state line, no greyed button. Rec: yes.
4. Merge Auto-highlight into Runner announcements, default on (the guild keys `marathon_public_reminders` / `marathon_host_highlights` stay as global gates). Rec: yes.
5. Shape the controls message by phase; after the show only the tracker link and Archive it. Rec: yes.
6. Replace the help line with a state line. Rec: yes.
7. Run post: one button per person, the @ pair to the People view, "for this run" dropped, state lines for exceptions only. Rec: yes.
8. Fold the channel's Go-live and Pings cards out of the drawer behind Open on Go-live ↗ — ⚠️ reverses the owner's 2026-09-26 "spotlight controls that match the channel's" ask. Rec: fold, his call.
9. The drawer slot drops its run-state buttons; the tracker owns run state. Rec: yes.
10. Drawer bar: Track · Read it now · Archive it visible; the rest under More…. Rec: yes.
11. Merge Remove into Archive it (the only difference is "a feed won't re-add", which Ignore already is). Rec: ask — a destructive path.
12. Shrink the `/event` marathon card to People… · Track/Untrack · Read it now · Open on the site · Back. Rec: yes.
13. Drop Event schedule from the thread (the drawer keeps it). Rec: yes.
14. Same order, same words, instant writes on the thread and the drawer's Settings fold. Rec: yes.
15. Rename the person's Spotlight → "Spotlight their channel…", and make the People-view labels keys. Rec: yes.
