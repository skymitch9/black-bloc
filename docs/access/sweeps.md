# Owner sweeps — what is shipped but never exercised by a person

> **Audience:** the owner. **Status:** TEMPORARILY TRACKED (owner order 2026-08-27). Last verified:
> **2026-08-27 20:20** — "verified" below means a human did it in the real server; everything else is
> test-suite evidence only. Tick a row by moving it to the verified table with the date.

All of this happens in **`#mute-me-bot-test-spam`** (test mode) or on **https://blackbloc.heygabi.ai**.

## Verified by the owner
| Date | What | Result |
|---|---|---|
| 2026-08-27 | `@Black Bloc hi` (chat step 1) | replies |
| 2026-08-27 | `/golive test` (card with game art) | posts |
| 2026-08-27 | dashboard Direction A, themes, Members, Polls, Chat pages render | seen by Claude in the owner's browser |

## Not yet verified — in the order that matters
| # | Feature | Do this | Expect |
|---|---|---|---|
| 1 | Role approval (Phase 9) | Dashboard → Role menus → Edit `runner-status` → Approval on, Expires after 7, Retry after 7, Channel → Save; post it; pick the role as a member | ephemeral "Sent to staff…"; a card with Approve/Deny in the staff (or set) channel; Approve → DM + role; Members chip shows "· 7 d"; Timed roles section lists it; `/role extend` moves it; End now removes it |
| 2 | Reconciliation | give someone a menu role by hand | Logs shows `role.changed_by_hand` (actor blank until the Bots role has **View Audit Log**) |
| 3 | Temp voice panel | join **join** | your channel's own text chat holds the control panel; buttons work; the log has no `panel_failed` (if it does: Bots role needs Send Messages in voice channels) |
| 4 | YouTube go-live | go live on YouTube with the Discord connection showing "Streaming on YouTube" (`golive_mode` shadow or on) | a card "… is now live on YouTube!" (or a `would_announce` line in shadow) |
| 5 | Stream end | end a stream | with `golive_end_mode` off the announcement is untouched; set it to `edit` and end another: suffix + "was live" card |
| 6 | Polls — native | `/poll create` kind single/checkbox/yesno/rating; vote; `/poll end` | a real Discord poll under a Black Bloc line; results embed on end; dashboard Polls row |
| 7 | Polls — the label question | look at test poll message `1542651824950218792` | does its first answer show as a DATE or as literal `<t:1788400000:d>`? Tell Claude — it decides `poll_date_labels` |
| 8 | Polls — panel | `/poll create … anonymous:true` and one `kind:date slots:12` | Black Bloc's own button panel; anonymous never shows names |
| 9 | Polls — recurring, reminder | `/poll recur create` weekly; a 1-hour poll | the next occurrence opens on schedule; a reminder 60 min before close |
| 10 | Chat 2 | `@Black Bloc how many of us` / `who's live` / `what's next` / `birthdays` / `my roles` / `I need a mod`; edit a greeting line on /chat.html then `hi` | live answers; the edited line is used; 👋🏿 tone visible |
| 11 | Birthday daily import | nothing to do — read the log after a restart | `birthdays: the daily import took nothing new — {… 'already': 38 …}` |
| 12 | Logs (Phase 12, live 18:38) | flip `golive_log_level` to `all`, `/golive test`, then back to `important`, `/golive test` again; `/golive logs` | Discord line only in `all`; dashboard shows both; a role request still posts its card with `rolemenu_log_level = off` |
| 13 | Emoji tone | `@Black Bloc hi` until a 👋 line comes up | dark tone by default; `emoji_skin_tone` setting changes it |
| 14 | Requests — staff (Phase 13, live 20:15) | `/request create` in the test channel as staff (What / Why / due date) | ephemeral "Filed as #N … approved straight away"; the row appears on https://blackbloc.heygabi.ai/requests.html under Planned & in progress; `/request list`, `/request logs` |
| 15 | Requests — member | have a non-staff member sign in at https://blackbloc.heygabi.ai and file one; or `/request create` as a member | they see ONLY the Requests page (file + their own); the row lands in Pending; Approve / Decline from the page → DM; `/request withdraw <id>` while pending |
| 16 | Via column | change one setting from Discord (`/settings set-value …`) and one from the website | Logs page → Settings audit shows **Discord** and **Website** in the Via column; `/settings logs` says the same |
| 17 | Cyberpunk look | cog → Cyberpunk | the estate's cyan/yellow palette again (no magenta) — say if it still reads wrong |

## When something fails
Take a screenshot, note the time, and paste it to Claude with the row number — the Fly logs around that
minute plus the dashboard Logs page are enough to diagnose. Nothing here is destructive; the worst case is
a `would_*` line in the log where you expected a post (that is test mode doing its job).
