# No-blurbs sweep of the site — 2026-10-04

> **Audience:** Claude sessions and the owner. **Status:** TRACKED.
> **Last verified: 2026-10-04**, on branch `no-blurbs-sweep` (off `main` `97036645`), against a mock started from
> that branch: every row below is a line that was READ in the source and judged; the 23 pages were rendered in
> headless Chrome at 1280 and 390 wide and the converted controls were pressed there (what was seen is in the
> build report, not repeated here). ⚠️ **NOT checked:** nothing met live Discord or the real bot — the mock only;
> no theme other than the default (`blackbloc`, dark) was looked at; the member (non-staff) view of Requests and
> Guides was not opened; hover titles (column headers, badges, mode switches) were listed as a class, not line by
> line; the Discord-side list at the foot is a grep of constant names, not a reading of every panel.

The owner, 2026-10-04: *"From now on no more explaining blurbs. We build features that are self explanatory to
use"* — then: *"We should do a full blurbs sweep of the site."* This is the record of that sweep: one row per
line judged, what group it fell in, and what was done. The rule itself is in `CLAUDE.md`.

## The three groups

| Group | What it is | What happens to it |
|---|---|---|
| **A** | Explanation — what a page, section, card or control is, or how the feature works | removed, with its constant and any wrapper it leaves empty |
| **B** | State or result — what is true now, what just happened, a refusal, a row's facts | kept; where it carried a lecture in its tail, trimmed to the state and the one way out |
| **C** | Something a person cannot get from the control and needs in order to use it | converted — the control says it itself (chips, a counter, a cap, a named blank choice, a label, a confirm step, the answer after saving) |

## Counts

| What | Count |
|---|---|
| Page subtitles on `main` (`<p class="sub">`) | **22**, all removed — plus the one Go-live wrote from JS (`SUBTITLE`) |
| `field-help` paragraphs on `main` (`grep -o field-help site/public/assets/*.js`) | **127** → removed **35**, kept **57**, kept-trimmed **16**, converted **18**, UNDECIDED **1** |
| `field-help` occurrences on the branch after the sweep | **77** — the survivors are state lines and the `field()` / `whenField()` helpers themselves |
| Lines judged beyond those two greps (rows below that are not a `field-help :NNN` row) | **234** rows, many covering several spellings of one line → removed 156, kept 19, kept-trimmed 17, converted 41 |
| All rows in the tables below | **385** (22 subtitles + 363) |

`page-events.js:145` is one `field-help` on `main` that drew two different notes (the Events fold and the
Marathons fold), so it has two rows; `blockwords.js:368` and `:447` each drew one note per block kind and have one row.

## UNDECIDED — left in place, needs an owner call

| Where | The line | Why it was left |
|---|---|---|
| `blockwords.js` | field help (The Marathon role): The role the button hands out. A role with a staff permission (kick, ban, manage anything, mention everyone) is never handed out — the press says it is not set up, and the Logs get a marathon.role_failed row. | The refusal happens on a member's press in Discord, not at save, and the role list the site is given carries no permission flags, so the picker cannot mark or refuse such a role without a new API field |
| `spotlight-controls.js` | field-help :193 one.ping_help — “On a marathon channel, During events pings only while one of its marathons is running…” | It is an explanation, but it is a settings key the API sends (marathon_channel_ping_help, editable on Settings); dropping it from the page orphans the key, which is a back-end call this front-end-only sweep cannot make |

⚠️ One reversal worth an owner glance, not an UNDECIDED: the twelve **drawer notes** under Go-live ▸ Settings and
logs were added on the owner's own ask of 2026-09-21 (*"what each of the settings does isnt clear"*). The
2026-10-04 rule is newer and names exactly this (*no help sentence describing a feature*), so they were removed;
each setting still carries its own registry help as its hover title. `git revert` of the Go-live commit brings them back.

## The shared helpers the conversions use

All in `site/public/assets/ui.js`, on a pure half in `site/public/assets/fieldaids.js` that
`site/mock/fieldaids.test.mjs` proves under node (added to `scripts/deploy.ps1` and `.github/workflows/ci.yml`).

| Helper | What it does | Used by |
|---|---|---|
| `placeholderChips(box, tokens, {said})` | a row of `{field}` chips; pressing one inserts it at the cursor (undo-able, fires `input`) | every wording row via `settingRow` (Settings and every page's settings/wording panel), `wordAids`, Chat |
| `placeholdersOf(spec)` → `fieldaids.placeholdersFor` | the chip list for a settings key: the `{fields}` in its own default and stored value, plus the ones its registry help names — and none at all when the default has no field (a help that mentions `{part}` is describing ANOTHER wording) | `settingRow`, `wordAids` |
| `wordAids(box, spec, {tokens, said})` | chips + a live counter when the box has a `maxlength` + the shipped words as the empty box's grey text | `blockwords.js` (every block editor), Chat (intent lines) |
| `limitCounter(input, max)` | a counter that appears at 80 % of the limit, warns at it | Requests, Guides, Chat, block editors, link-button labels |
| `capMark(addButton, cap)` | “3 of 10” beside an add button, greys the button at the cap | link buttons (10), application questions (Discord's 5) |
| `blankMeans(select, text)` | names the blank choice of a picker (“the default channel”, “nobody”) | Polls, Role menus ▸ application form |
| `slugInput(input, {lower, join, only})` | enforces a name's shape as it is typed | Role menus (menu and form names), Chat (intent names) |
| `quietHint(control, text)` | visually-hidden text the control points at with `aria-describedby` | the format bar's Tab / Ctrl+M hint (Posts editor and everywhere `formatBar` is used) |
| `field(label, control, help)` | `help` may now be a node (a counter, a cap mark, chips); a number box with `min`/`max` says its bound in the browser's own words when it is broken | every page |
| `whenField(...)` | no longer prints “Read in {zone}.” when the zone picker beside the box already names it; an empty help line is hidden | every date-and-time box |

## Found beyond the two greps

- **Section notes** — `section(title, note)` drew a paragraph under ~70 section heads (`class="section-note"`), plus the default note on every page's Logs block. All judged below; the explanations are gone, `section()` keeps the parameter for the few state uses.
- **`field(label, control, help)` strings** — the third argument is drawn as `field-help` by the helper, so the grep counted the helper once and none of its ~120 callers. All judged below.
- **Card and dialog intros** — plain `<p>`s at the top of cards (Modmail doors, Request forum), `ask-body` paragraphs in form dialogs, `muted` lines. Judged below; a dialog line that says what the move will do is a confirm step and stays.
- **Stat notes and drawer notes** on Go-live (`stat-note`, `gldrawer-note`).
- **Left, as a class:** hover titles — table column-header tooltips (`help:` on a column in Logs, Members, Moderation, Polls, Settings audit), the mode switches' `title`, the `certain` badge, the pin switch on Posts. They are not drawn on the page; they are explanations all the same, and a second pass could take them.
- **Left:** `fact-help` under a guide's live values (the guide's own body), the per-key help on Settings rows (out of scope — it is the registry's, and is a hover title), every `ask()` confirm body (that is where a consequence belongs), every empty-state sentence that is state.
- **Not blurbs, found while looking (pre-existing on `main`):** a settings row with no Discord mock appended a literal `null` after its reset button (`node.append(…, null)`) — fixed here in `settingRow`; the Chat page and the Settings page both open with “N changes pending” on the mock (`chat_review_line`, `chat_review_item` and three Settings rows read dirty on load) — NOT fixed, not part of this sweep; the Minutes page prints `**events**` with its asterisks (an API note drawn as plain text) — NOT fixed.

## The 22 subtitles

| Page | The subtitle (on `main`) | Group | What was done |
|---|---|---|---|
| `audit.html` | Everything Black Bloc has done, and every settings change. | A | removed. |
| `automod.html` | The rule book, the exemptions and the arming switch. | A | removed. |
| `birthdays.html` | Who has a birthday stored, by month. | A | removed. |
| `channels.html` | What each channel is for, in one sentence — the list Black Bloc reads before it points anybody anywhere. | A | removed. |
| `chat.html` | What Black Bloc says when somebody @-mentions it, and where it stays quiet. | A | removed. |
| `events.html` | The approval queue, what happens to an approved event, and the marathons Black Bloc follows — each one an event of its own. | A | removed. |
| `golive.html` | Twitch links, opt-outs, recent streams and the announcement wording. | A | removed. |
| `guides.html` | One page per goal: the steps, the pictures, and what the bot is set to right now. | A | removed. |
| `health.html` | Gateway, uptime, loop health and the last 50 actions. | A | removed. |
| `honeypot.html` | Who walked into a trap channel, and what was done about it. | A | removed. |
| `index.html` | Every feature’s mode, what’s open, and the last actions the bot took. | A | removed. |
| `members.html` | Everyone Black Bloc can see in the server, and what it has on file for them. | A | removed. |
| `minutes.html` | Black Bloc joins a voice meeting, records each speaker, transcribes what was said and writes it up. The audio is never stored. | A | removed. The privacy fact is kept — see `page-minutes.js` below. |
| `moderation.html` | Cases, and the same actions the slash commands take. | A | removed. |
| `modmail.html` | Tickets, replies, snippets and blocks. | A | removed. |
| `polls.html` | What is running, what is waiting on staff, and how every closed one went. | A | removed. |
| `posts.html` | The messages Black Bloc keeps current in Discord — written here, posted once, then edited in place. | A | removed. |
| `raidtrain.html` | Sign-ups by the hour, a DM to each streamer before their slot, and an event on the calendar when a train wants one. | A | removed. |
| `requests.html` | What the team wants built, from /request and this page. | A | removed. |
| `rolemenus.html` | Every menu, its options, and where it is posted. | A | removed. |
| `settings.html` | Every key the bot reads, grouped by what it runs. | A | removed. |
| `tempvoice.html` | The channels open right now, and the join-to-create setup. | A | removed. |

`schedule.html` had none. The page head is the same 35 px tall on every page at 1280 wide after the removal.

## Every other line, by file

`field-help :NNN` is the line number on `main` (`97036645`) of one of the 127; the other rows are the lines
the greps missed. Text is trimmed.

### `page-audit.js`

| The line | Group | What was done |
|---|---|---|
| section note: Every line Black Bloc has written, whether or not it said so in Discord. Important means… | A | removed |
| section note: Every settings change, whoever made it and however they made it. | A | removed |
| whenField help: The first day to include. | A | removed |
| whenField help: The last day to include. | A | removed |
| field help: The start of a kind, like automod. | C | converted — the label now reads “Kind starts with” |
| empty state: Nothing important has been logged…. Switch to All to see the routine lines too. | B | kept (state + the one way out) |

### `page-automod.js`

| The line | Group | What was done |
|---|---|---|
| field-help :69 rule.help (each rule's own description, from the API) | A | converted — it is the rule card heading's hover title now, the way a Settings row carries its key help |
| section note: Arming automod is the switch that starts deleting messages and timing people out. | A | removed |
| section note: Each rule is a burst counter: how many in how long, and what happens then. | A | removed |
| section note: Staff are always exempt on top of whatever is listed here. | C | converted — a fixed first row in Exemptions: Staff · always exempt |

### `page-birthdays.js`

| The line | Group | What was done |
|---|---|---|
| field-help :65 words.confirm (birthday_post_confirm, the confirm question) | B | kept — the confirm step's own question, a settings key |
| field-help :84 Filled in with a made-up member. The embed’s colour is … from birthday_color. | A | removed (the mock draws the colour) |
| field-help :128 The year is optional, and only used when birthday_show_age is on. | A | removed (the Year box already says “optional”) |
| section note: N birthday(s) stored. | B | removed — the same count is the section's count badge |
| birthday_template wording field | C | placeholder chips under the box (settingRow, from the key's default + help) |

### `page-honeypot.js`

| The line | Group | What was done |
|---|---|---|
| field-help :65 Safe to run twice; nobody is let into the trap by it. | C | converted — said by the Run setup confirm step |
| section note: In shadow the trap only writes down what it would have done; Ban now is how a shadow hit gets carried out. | A | removed (the Ban now confirm already says what it carries out) |

### `page-minutes.js`

| The line | Group | What was done |
|---|---|---|
| field-help :47 N line(s), oldest first. Deleted after minutes_keep_days. | B | kept-trimmed — the count is the Transcript card's count badge; the ordering and retention tail is dropped |
| field-help :128 #channel · started … · status (the meeting's facts) | B | kept |
| field-help :160 payload notes (the API's own state lines) | B | kept |
| field-help :161 This host is missing …, so a meeting cannot be recorded end to end here. | B | kept (state + refusal) |
| field-help :163 payload.guard.said (the test-guard sentence) | B | kept |
| section note: N recorded. | B | removed — the same count is the section's count badge |
| section note: Filed under events, because the /settings group picker is full. | A | removed |
| the privacy fact (was in the subtitle): The audio is never stored. | C | kept visible — an ok badge at the top of Meetings. The site has no control that starts a recording (that is /minutes in Discord), so it sits where a meeting first appears |

### `page-tempvoice.js`

| The line | Group | What was done |
|---|---|---|
| field-help :44 Filled in with a made-up member; {user} is whoever joined the lobby. | C | converted — {user} is a placeholder chip under the box (settingRow) |
| field-help :112 Lobby: #channel / none yet | B | kept |
| field-help :175 Safe to run twice; it does not delete anybody’s channel. | C | converted — said by the Run setup confirm step |
| section note: These are live from Discord, not a stored guess. | A | removed |

### `logs.js` — every page with a Logs block

| The line | Group | What was done |
|---|---|---|
| section note on every page's Logs block: Everything this part of Black Bloc has done, whether or not it said so in Discord. Important means it acted on a member or failed. | A | removed (one edit, every page with a Logs block) |
| empty-state tails (5): Settings changes are routine… / Chat replies are routine… / Rooms opening and closing are routine. / Creating a poll… / Filing a request… | A | removed — kept-trimmed to “X has logged nothing important. Switch to All to see the routine lines too.” |

### `page-settings.js`

| The line | Group | What was done |
|---|---|---|
| page note: The ⌫ beside a row puts it back to its default; nothing is written until you press Save Changes. Show keys puts… | A | removed (the ⌫ and Show keys buttons carry their own titles; the docked bar says N changes pending) |
| section note (core): staff_channel_id is what decides who may see this dashboard. | A | removed |
| section note (automod): automod_rules has its own editor on the Automod tab; the JSON box here is the fallback. | A | removed |
| section note (cost): The Costs card on the Health page is where this figure is read; nothing on the bot can see an invoice. | A | removed |
| section note (pings): The Pings section on the Go-live tab is where the Events role is set up… | A | removed |
| section note (marathon): The Marathons section of the Events page is where schedules are added, paired and paused… | A | removed |
| Logs note: Everything done from this dashboard and every settings change… switch to All to see them. | A | removed |
| every text/longtext row | C | placeholder chips under the box where the key's own default carries {fields} (plus any its help names); the per-key help itself is untouched |

### `ui.js` — every page (shared helpers)

| The line | Group | What was done |
|---|---|---|
| field-help :887 field(label, control, help) — the helper's own paragraph | — | kept as the helper; every caller's help string is judged on its own row. It now also takes a node (a counter, a cap mark) in the same slot |
| field-help :966 whenField: “Read in {zone}.” after every date-and-time box | B | kept-trimmed — drawn only when no zone picker stands beside the box (the picker already names the zone); an empty line is hidden |
| field-help :1662 Drawing what Discord would show… | B | kept (a working state, replaced by the mock) |
| field-help :2009 Discord formatting — what the preview shows is what Discord shows. (title: Tab indents inside the box; Ctrl+M lets Tab leave it.) | A + C | paragraph removed; the keyboard hint is visually-hidden text the box points at with aria-describedby (quietHint) |
| askLink field help: The web address the words should open. | A | removed (the refusal already says “Start it with https://”) |
| field help under every member picker: Names come from the bot's own copy of the member list. | A | removed (one edit, every page with a member picker) |

### `page-health.js`

| The line | Group | What was done |
|---|---|---|
| section note: Every dollar Black Bloc costs, in one place. The model figures are measured from its own ledger; hosting is what somebody typed in… | A | removed |
| section-note lines: total.word / prior.word / payload notes (the API's own figures) | B | kept |
| empty state: Hosting is the one figure nobody can read off the bot. [Set it] | B | kept-trimmed to “No hosting figure is set.” + the link |
| section-note: The keys Black Bloc is configured with, by name. No value is ever read out of the bot, so this says set or unset and nothing else. | A | removed |
| section note: Black Bloc exercising itself against this server: every setting’s channel and role, every read these pages make… | A | removed |
| empty state: It has not run in this server yet. Run it and watch — nothing here is destructive, and the cards it posts are cleaned up on their own. | B | kept-trimmed to “It has not run in this server yet.” |
| run detail: A run is going right now. This card refreshes itself every 15 seconds until it finishes. | B | kept-trimmed to “A run is going right now.” |
| row note: This loop does not record its last success yet, so this is liveness, not health. | B | kept (a row's own fact) |

### `page-overview.js`

| The line | Group | What was done |
|---|---|---|
| section-note: Only somebody with Manage Server can do this. Black Bloc serves this site, so the page goes down with it while it restarts. | C | removed from the card — the confirm step already says the site goes down with it, and the API's refusal says who may (restart.NOT_A_LEAD) |
| empty state: Nothing’s happened worth waking anyone for … The routine lines are all on Logs. | B | kept |

### `page-channels.js`

| The line | Group | What was done |
|---|---|---|
| section note: Each channel came with a one-sentence description drafted from its name. Use it as it is, change the words and save yours… | A | removed |
| section-note: The exact channel list the conversation models are handed with every answer. It is rebuilt each time… | A | removed |
| section-note: To stay inside the budget, the longest descriptions were left off these channels: … Shorten a note to bring them back. | B | kept (state + the one way out) |
| section-note: Its category is on chat_ignore_categories, or it is the ticket category — change that list on the Settings page to bring it in. | B | kept (why this channel is left out + the one way out) |
| section-notes: Draft: … / the channel's Discord topic / “Told about N of M channel(s)” | B | kept (row facts, counts) |

### `page-moderation.js`

| The line | Group | What was done |
|---|---|---|
| field help: Discord refuses anything over 28 days. | C | converted — the box carries max=2419200 and says “Discord refuses a timeout over 28 days” the moment a longer number is typed |
| field help: What the member was told. Editing it leaves one case.reason_edited line. | C | converted — the label reads “Reason the member was told”; the logging sentence is dropped |
| field help: For the next moderator, not for the member. One note per case, replaced not appended. | C | converted — the label reads “Staff note” |
| section note: The same code path as the slash command, into the same case table. | A | removed |
| section note: Ask the bot for one member’s cases instead of the whole page. / Filtered to NAME. | A / B | the explanation removed; “Filtered to NAME.” kept while a filter is on |
| section note: How much of what moderation does is repeated into the Discord log channel. The Logs section below is written to whatever this says. | A | removed |

### `page-modmail.js`

| The line | Group | What was done |
|---|---|---|
| card intro: One message with an Open a ticket button under it. Pressing it asks what is happening and opens a ticket… | A | removed |
| card intro: One message with three buttons: Ask staff privately opens a ticket, Request something files a request… | A | removed (the card draws the door itself) |
| card intro: In forum mode every ticket is a post of its own, tagged open while it is running and closed when it ends… | A | removed |
| muted line (always drawn): While the front door is up in the ticket button’s channel, that button is taken down — one door per channel. Moving the front door elsewhere… frontdoor_replaces_ticket_button below is what switches that off. | C | converted to state — drawn only when it applies (the door is on, in the ticket button's own channel, and the setting is on): “The Open a ticket button in this channel is down while the front door is here.” |
| muted line (shadow): The Open a ticket button follows the door while it is rehearsing, so it comes down too — frontdoor_replaces_ticket_button below is what switches that off. | B | kept-trimmed to “The Open a ticket button is down while the door rehearses.”, and only while the setting is on |
| state lines: frontdoor_mode is off, so /ask is hidden… / shadow — the door is rehearsing in … / It is in #x. / No ticket button is posted anywhere. / There is no ticket forum yet… | B | kept |
| Clear modmail_forum_channel_id below to let go of it. | B | kept (the one way out of a state) |
| section note: Canned replies staff can send without retyping them. | A | removed |
| section note: A blocked member’s DMs stop opening tickets, and they are not told. | A | removed (the Block confirm step says both) |
| section note: The messages Black Bloc keeps posted, and where they live. | A | removed |

### `page-events.js`

| The line | Group | What was done |
|---|---|---|
| section note: Every event proposed here or in Discord, with the same lock and the same allowed-transition check as the buttons there. | A | removed |
| section note: How events and marathons behave, and what the bot did about them. All shut until you open one. | A | removed |
| field-help :145 (Events fold): Where proposals are reviewed, when an approved event is announced, and whether a Discord scheduled event is made. | A | removed |
| field-help :145 (Marathons fold): Whether marathon posts go out, where, how often a schedule is read, when the reminders go and which one pings… | A | removed |

### `page-polls.js`

| The line | Group | What was done |
|---|---|---|
| section note + field help (twice): Off hides Create on the /poll panel and refuses new polls. Shadow posts every poll for real, into the log channel… | A | removed |
| section note: Every poll taking votes right now. Ending one publishes the result; cancelling stops it without publishing anything. | A | removed (the cancel/end confirm steps already say what each does) |
| section note: Polls waiting on a Lead. Approving posts it straight away and DMs the person who asked… | A | removed |
| section note: Polls that open again on their own. Pausing leaves everything it has already opened alone… | A | removed |
| section note: How every finished poll went. The export is a CSV of the totals… | A | removed |
| section note: Polls older than poll_archive_days. The totals are kept forever… | A | removed |
| section note: The same rules as the /poll panel in Discord — Black Bloc picks the surface from what you ask for… | A | removed |
| section note: Who may start a poll, how long one runs, where a poll made here goes… | A | removed |
| whenField help: When each copy opens. | A | removed |
| field help: Blank pings nobody. | A | removed |
| field help (Timezone): The zone the time of day is read in. Leave it on the server’s own zone… | A | removed |
| empty state: Nobody is waiting on a Lead. A poll only waits when poll_review_mode is on. [Where review is switched on] | B | kept-trimmed to “Nobody is waiting on a Lead.” + the link |
| empty state: No poll repeats on its own yet. Repeat on the Create a poll form below starts one, and so does Repeat… on the /poll panel. | B | kept-trimmed to “No poll repeats on its own yet.” |
| field help (Repeat): A repeating poll is a template rather than a poll: nothing is posted when you save it… | C | removed — the live outcome sentence under the form already says “Saves … as a template … Nothing is posted until it first comes round.” |
| whenField help (First slot): Midnight means the slots are shown as plain dates, with no time on them. | C | converted — the live outcome sentence adds “The slots are shown as plain dates…” when the first slot is midnight |
| zone word (First slot): Black Bloc reads it in the server’s own time zone. | B | kept (the box has no zone picker) |
| field helps (limits): Two to twenty-five. / One to 28 — every month has those. / One hour to 32 days — Discord counts in whole hours. | C | converted — each box already carries min/max; the shared field() now makes the browser say the bound in words the moment a number outside it is entered |
| field help: Blank uses poll_channel_id. | C | removed — the outcome sentence already names “the default channel” |
| field helps: Anonymous forces a Black Bloc panel. / Hidden until close forces one too. | C | removed — the outcome sentence already says “a Black Bloc panel … because nobody can be shown who voted / the bars stay hidden” |
| deny dialog field help: Say why — they are sent this word for word. | A | removed (the dialog's own line says they are DM’d exactly what is typed) |
| Channel and Ping pickers on the create form | C | the blank choice is named: “the default channel”, “nobody” (blankMeans) |

### `page-requests.js`

| The line | Group | What was done |
|---|---|---|
| section note: Everything asked for, in one list. The chips narrow it to a state; a row opens the request… | A | removed |
| section note: The reference half of the page: the request settings, and everything requests has done… | A | removed |
| field-help :1306 Whether requests are open, who may file one, where the bot says a request arrived… | A | removed |
| card intro: With a forum, every request is a post of its own — the card is its first message… | A | removed |
| chip tooltips (6): Filed and not picked up, longest wait first… / Being worked on. The buttons here save as you press them… / Parked with a reason… / Built and waiting… / Requests that shipped… / Every request this server has… | A | removed |
| drawer intro: The same three fields as /request in Discord. Whoever is signed in is recorded as the person asking… | A | removed |
| section note: Every request you have filed and where each one got to. You can take back one nobody has answered yet. | A | removed |
| drawer intro (members): What you want built, and why it is worth building. Staff answer these on the same page… | A | removed |
| field help: One line. The detail goes in the why. | A | removed |
| field help: What it fixes, or what it would let people do. | A | removed |
| field help: What is left to do, or what is blocking it. | A | removed |
| field helps: The whole answer the person who asked gets. / Editable — fixing a typo moves nothing. / One or two sentences. / Say what is missing. | A | removed |
| field-help :728 Put it on hold, Decline, Send back and Ready to check each ask for a line, and whoever it concerns is sent exactly what you type. | C | converted — the reason box in each of those confirm steps is labelled “Reason — they are sent exactly this”; the old “Say why.” hints are the box's placeholder |
| field helps: Optional — the steps somebody follows to see it working. (three places) / Only when something actually depends on the date. | C | converted — the labels read “How to test it (optional)” and “Due date (optional)” |
| the 1000 / 500 character limits on What, Why, What was built, How to test it, What needs doing | C | new — a live counter appears as each box nears its limit (limitCounter); the boxes already stop at the limit |
| state lines: Every request gets its own post there. / There is no request forum yet, so cards go to the channels below. / Clear request_forum_channel_id below to let go of it. / the NO_* empty states / the outcome sentence under the form | B | kept |

### `page-rolemenus.js`

| The line | Group | What was done |
|---|---|---|
| section note: Off takes the panels down; on posts every menu again, and nobody loses a role either way. | A | removed |
| section note: What members have asked for on the menus that ask staff first. Approving hands the role over… | A | removed |
| section note: Every role Black Bloc is holding a clock on. Ending one takes the role off now… | A | removed |
| field-help :603 The same path /rolemenu ▸ Hand roles out… takes: only the roles on the menu you pick are touched… | A | removed |
| section note: Forms staff write, that members fill in. Approving one hands the form’s role over… | A | removed |
| field help (applications switch): Off leaves /apply in Discord saying so and offering nobody a form… | A | removed |
| section note: Where a menu goes, who answers role requests, and who gets pinged about them. | A | removed |
| field help: The human step after an approval. The card says “@owner — next step: …” and the applicant is told the same thing. | A | removed |
| field helps (Name, editing): A menu keeps its name for life… / A form keeps its name for life… (the box is disabled) | A | removed |
| dialog field helps (3): Say why — they are sent exactly this. | A | removed (each dialog's own line says they are DM’d the reason) |
| field help: On, picking this role asks staff first instead of handing it over. | C | converted — the label reads “Staff approve first” |
| field help: How long after a no before they may ask again. | C | converted — the label reads “Ask again after a no, days” |
| field help: What an approved applicant is DMed. | C | converted — the label reads “DM on approval” |
| field helps (blank means…): Blank means the role never runs out. (x2) / Blank or 0 means the role never runs out. / Blank or 0 hands it over with no end date. / Blank uses applications_retry_days. | C | converted — the empty box itself reads “never”, “no end date” or “the default” (placeholder) |
| field helps: Blank uses applications_channel_id. / Blank uses applications_approver_role_id, then staff. / Leave blank to keep a list instead of handing over a role. | C | converted — the blank choice in each picker is named: “the default channel”, “the default approvers”, “No role — keep a list” (blankMeans) |
| field helps (new Name): Short, no spaces — this is how the slash commands find it. / Short, lower-case, no spaces — this is what the logs and the /apply panel name it by. | C | converted — the box enforces it as you type: a space becomes a hyphen, a form name is lower-cased (slugInput) |
| field help: Saving a different channel moves the panel: the old message comes down and a new one goes up. | C | removed — the save's own answer says “Saved … and moved its panel — the old message is gone.” |
| field help: This menu has no panel yet, so there is nothing to move — post it from Post a menu below. | B | kept-trimmed to “No panel is posted yet.” (the picker is disabled) |
| field-help :806 Discord shows at most five boxes on one form, in this order. | C | converted — the count stands beside Add question (“3 of 5”), the button greys at the cap, and the existing refusal still says why (capMark) |
| section note: Posting again makes a new message; the old one stops handing out roles. | C | removed — the Post confirm step already says it |
| field-help :339 Nothing is posted yet, so there is nothing to take down. | B | kept |
| field-help :815 They answered nothing. | B | kept |
| empty states: Nobody is waiting on staff. A menu only asks first when its Approval is on. / No application form exists yet. Make one below — the Twitch Team form is what this was built for. | B | kept-trimmed to the state (and “Make one below.”) |
| result sentences: On. Every menu that has a channel is posted there again… / Off. The posted panels are removed… / the seed confirm body | B | kept (what a move answers with; a confirm step) |
| field help under the mode chip: the rolemenu_mode key's own registry help, drawn as a paragraph | A | converted — it is the chip's hover title now, the way a Settings row carries its key help |

### `page-guides.js`

| The line | Group | What was done |
|---|---|---|
| section note: Whether members see this page at all, who may edit a guide, whether /help links to one… | A | removed |
| section note: One page per goal. Each one is the shortest set of presses that gets it done… | A | removed |
| section note: A screenshot is marked stale when the feature it shows has changed since the picture was taken… | A | removed |
| card intro: A deploy marks the shots of the features it changed. Nothing else can — a mode flip, a renamed channel… | A | removed |
| field helps (Title, x2): The goal as a person would say it. | A | removed |
| field helps (Goal, x2): One sentence. It is what the card on the hub reads. | A | removed |
| field helps (Which feature, x2): Decides the Where it happens link and which release makes its shots stale. | A | removed |
| field helps (Command, x2): Several guides may share a command; /help links every published guide for everyone. | A | removed |
| field help: What the picture shows. It is written under it. | A | removed |
| field help: A real capture, or a drawing of a screen a capture cannot reach. | A | removed |
| field help: One or two lines. Staff read exactly this. | A | removed |
| rail line (always true): Every word and picture on it is edited by staff on this page. | A | removed |
| field helps (Who it is for, x2): Staff guides are hidden from members and from /help. | C | converted — the choice itself reads “For staff — hidden from members and /help” |
| field help: Optional. It goes on the log line, so the capture session knows what changed. | C | converted — the label reads “Why (optional)” |
| field help: Leave it blank if it is the whole guide. | C | converted — the empty box reads “the whole guide” |
| field help: The version it was shot at, so staleness can be told. | C | converted — the label reads “Shot at release” |
| field help: One press. Write the button in **bold**, spelled the way Discord spells it. | C | converted — the empty box shows the shape: “Press **Save Changes**” |
| field help: What is on the screen afterwards. Leave it blank if there is nothing to see. | C | converted — the label reads “Expect (optional)”, the empty box “what is on the screen afterwards” |
| the title / goal / caption / step length limits | C | new — a live counter appears as each box nears its limit (limitCounter) |
| state lines: Something wrong here? Tell a Lead in the staff channel — filing a request from this page is turned off. / Black Bloc ships this guide; staff may rewrite every word of it. / Staff wrote this guide here. / Last edited… | B | kept |
| fact-help: the registry help under each live value in a guide's “what the bot is set to” rail | — | left — it is the body of a guide (the guide's own content), not page chrome; listed under Found beyond the greps |

### `blockwords.js` — Posts ▸ Blocks, Modmail ▸ Front door

| The line | Group | What was done |
|---|---|---|
| field-help :77 Every button is switched off, so the card goes out with nothing to press. Tick at least one to keep it a door. | B | kept (state + the one way out) |
| field-help :134 Each button label is at most 80 characters; blank puts the shipped words back. | C | converted — a live counter appears as a label nears 80 (the box stops there), and an empty box shows the shipped words in grey (wordAids) |
| field-help :141 Which buttons the card carries, here and on /ask. | A | removed |
| field help (Rehearsal note): The line a rehearsal copy carries while the door is in shadow. It is shared by every rehearsal copy Black Bloc posts, not only this one; {channel} is the real channel. | C | converted — the label reads “Rehearsal note — shared by every rehearsal copy”; {channel} is a placeholder chip |
| field help (Lobby button): One button per join-to-create lobby (at most four); {lobby} is the lobby's name… At most 80 characters. | C | converted — {lobby} is a placeholder chip; the explanation is dropped |
| field-help :230 Opens the same /voice panel a member gets by typing /voice — every rule it has still applies… | A | removed |
| field-help :233 The lobbies are the ones set up on the Temp voice page; with none set up yet, a sample lobby is drawn. | A | removed |
| field helps (Button, 4 block kinds): Gives the member who presses it the Marathon role… / Opens the same /pings panel… / Asks for the date straight away… / Opens the same private card… — each ending “At most 80 characters.” | A + C | explanations removed; the 80 limit is the live counter under the box |
| field helps (said lines): {role} is the role's name. (x2) / {said} is the same sentence /birthday answers with. (x2) | C | converted — {role} / {said} are placeholder chips under each box |
| field helps (said lines): Also said if the role is gone from the server or carries a staff permission. / Said on the press, or on the form, if birthdays were turned off after the post was drawn. Nothing is saved. | A | removed (the labels already say when each line is said) |
| field-help :319 No Marathon role is picked yet, so a press says staff have not set it up. Pick it here or on the Settings page (marathon_role_id). | B | kept-trimmed to the state (the picker is the line above it) |
| field help (The Marathon role): The role the button hands out. A role with a staff permission (kick, ban, manage anything, mention everyone) is never handed out — the press says it is not set up, and the Logs get a marathon.role_failed row. | C | UNDECIDED — left in place. The refusal happens on a member's press in Discord, not at save, and the role list the site is given carries no permission flags, so the picker cannot mark or refuse such a role without a new API field |
| field-help :368 (3 kinds) Nothing is drawn on a post while pings / birthdays / event proposals are off (Settings ▸ …). | B | converted to state — drawn only while that feature's mode really is off: “Pings are off, so this block is not drawn on a post.” |
| field-help :444 and :622 Leave a line blank to put the shipped words back. | C | converted — an empty box shows the shipped words in grey (wordAids) |
| field helps (live lists): {name} is who is live; {title} is the stream’s title… / {title} is the event…; {when}…; {relative}… | C | converted — placeholder chips under each line box |
| field helps (numbers): 1 to 25. / 10 to 200; a longer title is cut with an ellipsis. / 1 to 20. | C | converted — each box carries min/max and the shared field() says the bound when it is broken |
| field-help :447 (2 kinds) The streams drawn here are samples. On a post, the card lists the go-live and spotlight streams announced right now… / The events drawn here are samples… | A | removed |
| field-help :532 That is ten links, the most one block carries (two rows of five). | C | converted — the count stands beside Add a link (“10 of 10”) and the button greys at the cap (capMark) |
| field-help :612 Each button opens its address in the browser. The label is at most 80 characters and the address must start with https://. A row that does not check is refused with its number, and nothing is saved. | C | converted — each label has a live counter, and a row whose address does not start with https:// says so beside it as it is typed |
| field-help :616 Off leaves the buttons alone under the post, with no heading or line above them. | A | removed (the mock under it shows it) |

### `postversions.js` — Posts ▸ versions

| The line | Group | What was done |
|---|---|---|
| field-help :69 Every press of Save changes or Post it that changed something is here. Nothing else writes a version, and nothing ever removes one. | A | removed |

### `page-posts.js`

| The line | Group | What was done |
|---|---|---|
| field-help :436 (post-how) Post it sends this to #x as an embed and pins it. / Update the post edits the message already in… / shadow — this goes to… | B | kept (what the button will do right now) |
| field-help :437 the pending-changes line | B | kept |
| field-help :628 The doc must be shared Anyone with the link → Viewer. Its words replace the message box as an unsaved draft — nothing is saved or posted until you press Save Changes or Post it. | C | removed — the import's own refusal says how to share the doc (doc_import.py NOT_PUBLIC, passed through untouched), the replace confirm and the “Imported from … — the box is an unsaved draft” answer say the rest |
| field-help :753 No blocks — the message is only the post. | B | kept |
| field-help :756 {name} goes on one post at a time and is on {title}. Remove it there first. | B | kept (state + the one way out) |
| field-help :759 What rides under this post, in the same message. A block is added or removed at once — it is not part of Save Changes. | A | removed |
| field-help :856 Paste keeps formatting | A | removed (the “Pasted with formatting kept … Undo with Ctrl+Z” notice says it when it happens) |
| field-help :1122 Posts are [mode]. + the API's first note | B | kept |
| field-help :1128 the API's further notes | B | kept |
| field-help :1130 payload.guard.said | B | kept |
| field-help :1241 Drawn by the bot from the saved words, alone — on a post it rides under the post's own message. A list that changes by itself is drawn with sample entries. | A | removed |
| field-help :1255 Whether staff may post at all, where a rehearsal lands, how long the /posts panel stays live… | A | removed |
| section note: One message per post. Black Bloc sends it once and edits that same message every time after — it never posts a second copy. | A | removed |
| section note: A block rides under a post, in the same message. Each kind is listed with the post it is on… | A | removed |
| section note: The reference half of the page: six keys, and everything posts has done… | A | removed |
| field helps: Staff see this here; an embed shows it at the top of the message. / Where the message lives. Black Bloc edits that one message. / A plain message renders # headers; an embed holds more but does not. / The title staff see here, and the embed title… | A | removed (the mock beside the box and its counter show what a style does) |
| field help (new post from a doc): Shared Anyone with the link → Viewer. Nothing is posted to Discord — the new post opens for you to check first. | C | removed — the read's refusal says how to share; the “Read … Check the title, then press Create the post.” answer says the rest |
| field help (doc title): Fills with the doc’s own title, else its title line or first heading, once it is read — or “Untitled”… numbered… | A | removed (the box fills itself when the doc is read) |

### `page-raidtrain.js`

| The line | Group | What was done |
|---|---|---|
| field-help :162 sweeping every N min · last error… (the loop's health) | B | kept |
| field-help :234 No event is tied to this train yet. **Make an event for it** raises one and sends it to the events review, where a Lead approves or denies it… | B | kept-trimmed to “No event is tied to this train yet.” (the Make an event confirm step says the rest) |
| field-help :234 Event **#N** carries this train. It is **status**, and the Events page is where it is decided. | B | kept-trimmed to “Event #N carries this train. It is status.” (the Open it on the Events page button is beside it) |
| field-help :276 The people move; the times belong to the position and stay put. | A | removed |
| field-help :297 status · starts … · N/M hour(s) taken | B | kept |
| field-help :358 The lineup is posted once and edited in place after that. | A | removed |
| field-help :405 Raid trains are [mode]. | B | kept |
| field-help :411 Raid trains are {mode} at the moment, so nothing is posted and no reminder is sent. **Settings and logs** below turns them on. | B | kept-trimmed to the one way out, “**Settings and logs** below turns them on.” (the mode line above it is the state) |
| field-help :435 Whether raid trains are on, where the lineup post goes, who may build one, and whether a new train also makes an event. | A | removed |
| section note: Every raid train, the hours on it and who holds them. A row opens the lineup… | A | removed |
| section note: The reference half of the page: the raid-train settings, and everything raid trains have done… | A | removed |
| whenField help: The first slot opens then. | A | removed |
| field helps (limits): 15 to 720. / 1 to 24 — Discord will not carry a longer lineup in one message. | C | converted — both are number boxes with min/max now, and the shared field() says the bound when it is broken |
| field help: The event goes to the events review, where a Lead approves or denies it. Which way this starts is raidtrain_event_default… | A | removed |

### `page-schedule.js`

| The line | Group | What was done |
|---|---|---|
| field-help :274 Times shown in your time — {zone} [change] | B | kept |
| field-help :292 source · times from … · read N ago · next read … · watch | B | kept |
| field-help :299 This marathon is archived, so this is its schedule as it ended. Nothing here can be changed. | B | kept-trimmed to “Archived — read-only.” |
| field-help :412 (New start) Read in {zone} time — type it like 12:40 PM (13:40 works too). Later runs keep their gaps. | B + C | kept-trimmed to “Read in {zone} time”; the box arrives filled in the format it takes, and the move's own answer says “The N runs after it keep their gaps…” |
| field-help :412 (Estimate) As 1:20, or minutes. | C | removed — the box arrives filled in the format it takes (1:20) |
| field-help :550 Each heads-up still to go out for a BaF run or host block, worked out from the start times above — when a run moves, its post moves. | A | removed |
| field-help :577 Updated N seconds ago · re-reads every N seconds while this tab is showing / Could not update just now — … | B | kept-trimmed to “Updated N seconds ago”; the failure sentence is kept whole |

### `page-chat.js`

| The line | Group | What was done |
|---|---|---|
| card intro: Every answer a model writes is in this voice: the words it reaches for, how it greets, teases and signs off… | A | removed |
| section note: Which tone each member hears on top of the cookout voice. A pin beats the server's setting… | A | removed |
| section note: What each channel is for, in one sentence, and the review of the drafted descriptions… | A | removed |
| section note: Type what somebody would say after the @-mention and Black Bloc tells you which intent it lands on… This is a dry run — nothing is sent anywhere. | A | removed (the Try it answer already ends “Nothing was sent.”) |
| section note: One card per thing Black Bloc understands. A canned intent answers from its own lines… | A | removed |
| section note: A canned intent of your own. It is matched before the built-in ones… | A | removed |
| section note: Whether Black Bloc answers at all, how often the same person gets a reply… | A | removed |
| section note: What Black Bloc knows about this server in its own words… | A | removed |
| section note: How Black Bloc sounds. The cookout voice is the house one; the pool is eleven voices… | A | removed |
| section note: How many answers came from a model today and which of the three tiers is actually answering… | A | removed |
| section note: What Black Bloc remembers about each person between conversations… | A | removed |
| section note: Answers that may have missed: a real question no note could ground… | A | removed |
| field-help :1430 The open items as one document — the same file a scheduled Claude routine reads through the read-only operator token. | A | removed |
| field helps (Kind): Answers with one of the lines below, picked at random. / Fills its line in from what the server is doing right now. / Hands the person to staff… | A | removed as a paragraph — it stays as the Kind badge's hover title, which it already was |
| field help: Quiet leaves the phrases in place and says nothing. | A | removed |
| field help: One of Black Bloc’s own, so the name is fixed. | A | removed |
| field help: Whole words, so “help” does not match “helping”. Enter adds it. | A | removed |
| field help: The part after the @-mention. Enter runs it. | A | removed |
| field helps (note card): What a question is matched against. / One word, so you can find it again. Optional. / Plain words. Black Bloc quotes this rather than paraphrasing it. / One plain line Black Bloc can quote. | A | removed |
| field help: A voice is tone and never truth — the same facts either way. | A | removed |
| empty line: The cap itself is a setting. [Change chat_monthly_cap_usd] | A | removed — the Change… action stays |
| section-note under every intent: {name} = who asked · {attendees} = head count · {count} = how many… | C | converted — placeholder chips under Add a line, from the intent's own tokens (the API's `tokens`); each chip's hover says what it fills in |
| field help: {name} is filled in with whoever asked. | C | converted — placeholder chips under First line |
| field helps: Letters, numbers and underscores. / Letters, numbers and underscores — this is what the log calls it. / Lowercase words joined by underscores. | C | converted — the name box enforces it as you type (a space becomes _, anything else is dropped; the review name is lower-cased) — slugInput |
| field help: Separated by commas. Whole words, not letters inside one. | C | converted — the label reads “Trigger phrases, comma-separated” |
| field helps (limits): Up to 200 characters. Enter adds it. / Up to 80 characters. / Up to N characters. A note that will not fit in an answer is left out whole… / The words somebody would say, up to 60 characters. / …Up to 1200 characters. | C | converted — a live counter appears as each box nears its limit (limitCounter) |
| field help: Optional, and only for finding it again. | C | converted — the label reads “About (optional)” |
| field help: Blank uses the From review note. | C | removed — the empty box already reads “From review” |
| tone hint: Your wording is kept when Black Bloc starts up. Blank and Save puts the shipped wording back. Up to 1200 characters. | A + C | removed — “Put the shipped wording back” is its own button; the limit is the live counter |
| empty states: Nobody has been answered by a conversation model yet, so nobody is listed. Pin somebody below… / Nobody has a profile yet. One is written after… / Nothing is waiting in this view. An answer lands here when it may have missed. | B | kept-trimmed to the state |
| state line: Built in, so it cannot be deleted — turn it off above and it stays quiet. Its phrases and its lines are still yours. | B | kept-trimmed (state + the one way out) |
| state lines: The voice is the cookout one, so nobody hears a tone right now… / This server keeps the notes themselves private… Set chat_memory_staff_view to full below… / month.word / today.word / tagging.word / Last changed by… / N written by staff… | B | kept |

### `spotlight-controls.js` — Go-live and marathon drawers ▸ Spotlight, Pings

| The line | Group | What was done |
|---|---|---|
| field-help :120 the replay line (badge) | B | kept |
| field-help :192 Only the role mentions change. The announcement, the pin and the reminders go out exactly as they do now, whichever of the three is picked. | A | removed (the state line above the switch, from the API, says what is mentioned) |
| field-help :193 one.ping_help — “On a marathon channel, During events pings only while one of its marathons is running…” | A | UNDECIDED — left in place. It is an explanation, but it is a settings key the API sends (marathon_channel_ping_help, editable on Settings); dropping it from the page orphans the key, which is a back-end call this front-end-only sweep cannot make |
| field-help :251 Opted out — nothing of its is announced, whatever the spotlight says. The row, its ping role and its YouTube link all stay. / On — announced in the go-live channel whenever it goes live. | B | kept; the opted-out line trimmed to “Opted out — nothing of its is announced.” |
| whenField helps: When Black Bloc starts watching it. Leave it blank to start now… / When the row is purged. Leave it blank to keep it for ever, the way GamesDoneQuick is kept. | C | converted — the labels read “Starts — blank starts now” and “Ends — blank keeps it for ever” (a date box has no empty-state text of its own) |
| state: Scheduled — its start has not arrived, so nothing of its is announced, pinned or reminded yet. | B | kept-trimmed to “Scheduled — its start has not arrived.” |
| field help: Optional — for example AGDQ 2027. Shown beside the window here. | C | converted — the label reads “What it is for (optional)”; the empty box already shows AGDQ 2027 |
| dialog body: While a window is open this channel mentions the go-live role and its own ping role. If it is already live when the window opens, one reminder that pings goes out. | B | kept (a confirm step saying what the move does) |

### `golive-join.js` — Go-live ▸ Settings and logs

| The line | Group | What was done |
|---|---|---|
| drawer notes (12): Which roles let a stream be announced, how often the same person may be… / The channel it is posted in… / Discord presence, the YouTube probe… (one under every Settings drawer head) | A | removed — and the fixture that demanded a note of eight words or more now pins that no drawer carries one |

### `page-golive.js`

| The line | Group | What was done |
|---|---|---|
| subtitle set from JS: Who is streaming, who is set up to be announced, and what the announcement says. One list of people, whichever platform they use. | A | removed (with the constant and the line that wrote it) |
| field-help :968 rowFoot — the row's facts | B | kept |
| field-help :1179 For an org channel like GamesDoneQuick, or a marathon nobody here runs. Black Bloc announces it in the go-live channel whenever it goes live… | A | removed |
| field-help :1236 One box for both platforms. A Twitch name goes to the go-live watcher; a YouTube channel address or @handle goes to the live probe. Nothing is guessed… | A | removed (the box's own refusal says so when a value could be either) |
| field-help :1238 Leave this blank for a channel with nobody here behind it. It goes on the same list, is announced the same way… | C | converted — the member picker's label reads “Member — leave blank for a channel with nobody here behind it” |
| field-help :1301 The sentence and the card’s top line the moment they go live. The wording takes {name} {game} {title} {url} {platform}; the top line takes {name} and {platform} only… | C | converted — placeholder chips under each box, read from that key's own default and help (settingRow) |
| field-help :1309 {live} is the sentence exactly as it was posted, so “{live} — stream ended” adds to the end of it and a wording without {live} replaces the whole post… | C | converted — {live} and the other fields are placeholder chips; the mock under the box shows what a wording with or without {live} does |
| field-help :1334 Every box below is drawn by the bot itself — the same functions Discord gets, not a copy living on this page… | A | removed |
| field-help :1428 Makes (or reuses) the Events role, points both feeds at it and puts it on the Notifications panel. Post that panel from the Role menus tab. | C | converted — said by a confirm step on Set up the Events role |
| field-help :1429 Makes (or reuses) the Raid trains role and points raidtrain_ping_role_id at it, so a member opts in from /pings instead of asking staff. | C | converted — said by a confirm step on Set up the raid-train role |
| field-help :1452 onboarding state lines (prompt — options / N more streamer(s) are on /pings / N prompt(s) belong to somebody else and are left alone / not a Community server… / Nothing to put on the screen yet…) | B | kept; “The bot is not managing onboarding. The prompts stay exactly as somebody left them.” trimmed to the state + “pings_onboarding_managed above turns it on.” |
| field-help :1454 Last written: … / Not written yet. | B | kept |
| field-help :1474 The bot keeps two of Discord’s onboarding prompts in step with these roles: what should ping you, and which streamers. It never touches a prompt it did not make… | A | removed |
| field-help :1477 Whether the bot manages them at all is pings_onboarding_managed in the settings above, and Stop managing onboarding on /pings. | A | removed (its one way out moved onto the not-managing state line) |
| field-help :1500 A linked channel going live is announced through the go-live feed above, as source youtube. golive_mode still decides whether anything is posted. | A | removed |
| field-help :1504 From the bot’s datacenter address YouTube sometimes answers with its “Sign in to confirm you’re not a bot” page… | A | removed (the Bot check and Behind the bot check now rows are the state) |
| field-help :1505 With no YOUTUBE_API_KEY the stream is announced from the page alone, so its title reads Live now and no quota is spent. | B | kept-trimmed to “No YOUTUBE_API_KEY is set, so an announced stream’s title reads Live now.” |
| section notes: One card per open stream, both platforms together. / One row per person. Click a row for everything about them. / One wording for both platforms. {platform} fills itself in. / Every go-live, YouTube and ping-role setting, in a drawer named for the question it answers… | A | removed |
| drawer note (log): What the bot actually did: announcements, links, ping roles and every refusal… | A | removed |
| stat notes (always true): posted through the go-live feed / the opt-in roles members pick with /pings | A | removed; the notes that are state (no announcement channel set, N spotlighted…) are kept |
| empty state: Nobody is streaming right now. A Twitch stream shows up the moment Discord sees it; a linked YouTube channel is looked at on the cadence in the strip above. | B | kept-trimmed to “Nobody is streaming right now.” |
| panel line: Not spotlighted. Spotlighting a channel pins its announcement while it streams and reminds people every few hours… | B | kept-trimmed to “Not spotlighted.” |
| field helps: Watched by name. No member here is behind them. / The name in twitch.tv/…, or the address that starts with youtube.com/channel/UC…, or their @handle. | A | removed (the second is already the box's placeholder) |

### `event-drawer.js` — Events ▸ event drawer

| The line | Group | What was done |
|---|---|---|
| field-help :295 Decided by NAME, when | B | kept |
| field-help :301 Why not: REASON | B | kept |
| field-help :304 Nothing is left to decide on this one. | B | kept |
| field-help :311 the marathon's line + Open ↗ | B | kept |
| field-help :340 Optional beside a channel — a Twitch link, say. / Only used when it is somewhere else. | C | converted — the box's own label changes with the Where picker: “Where, or a link” or “A link too (optional)” |
| field-help :367 This one is settled, so its details cannot be changed — only an event waiting for a decision or already approved can be edited. | B | kept-trimmed to “This one is settled, so its details cannot be changed.” |
| field-help :395 Saving does not rewrite an announcement that is already up or a Discord scheduled event that already exists; the answer says when that applies. | C | removed — the save's answer already carries the API's notes for exactly that case (found.message + found.notes) |
| field-help :412 status · asked by NAME · when | B | kept |
| field-help :434 Proposed WHEN · #id | B | kept |
| field help: A voice or stage channel gives everybody a Join button on the Discord event; anything else is written on it as words. | A | removed |
| whenField help: When it begins. | A | removed |
| field help: Like 1h30m, 2h or 45m; blank means two hours. | C | converted — the empty box reads “2h — or 1h30m, 45m” |

### `marathon-words.js` — Events ▸ feed drawer

| The line | Group | What was done |
|---|---|---|
| field help (Search words): What horaro.net event names are searched for, commas between them — at most five. Blank searches by the feed’s name. | C | converted — the empty box already shows the names it searches by; a sixth word is refused in words beside the box as it is typed |
| field help (Owner): The horaro.net account that makes the events. Every event it owns is kept, even one that does not name this channel’s Twitch. Blank keeps only the ones that do. | C | converted — the empty box reads “only events naming this channel” |

### `marathons-section.js` — Events ▸ Marathons, drawers and dialogs

| The line | Group | What was done |
|---|---|---|
| field-help :364 line() — the helper every drawer state line goes through (each caller is its own row) | B | kept |
| field-help :546 After this one: NAME, date (relative) | B | kept |
| field-help :549 the tracker ↗ | B | kept |
| field-help :604 reading state · counts · event · channel · tracked | B | kept |
| field-help :938 runner → member · this/every schedule · Unlink | B | kept |
| field-help :979 the event state line + its move | B | kept |
| field-help :986 Marathon role / no Marathon role + why | B | kept |
| field-help :1006 The schedule viewer links no event sheet that matches this marathon, so GDQ’s sheet times are used. | B | kept |
| field-help :1009 This event has its own schedule sheet, LINK, but Event schedule is off… | B | kept |
| field-help :1011 Times, hosts and commentators come from LINK — N of M run(s) matched. | B | kept |
| field-help :1091 the spotlight state line | B | kept |
| field-help :1151 Reads from LINK · Change the schedule link… | B | kept |
| field-help :1173 board / sent state · where · the move | B | kept |
| field-help :1243 archived word · who · counts · event | B | kept |
| field-help :1268 Archived — read-only. **Restore** puts it back on the list, paused. | B | kept |
| field-help :1386 the schedule ↗ | B | kept |
| field-help :1432 a Hotfix show's row (tick, chips, hosts, why it is tracked) | B | kept |
| field-help :1463 a listed show that is not on the sheet this week + Remove | B | kept |
| field-help :1523 open it ↗ (the viewer link) | B | kept |
| field-help :1539 Reads the sheet the Hotfix page embeds: LINK | B | kept |
| field-help :1582 Read from: SOURCE · #channel · paused | B | kept |
| field-help :1590 Added by this feed: … | B | kept |
| field-help :1725 an archive row | B | kept |
| field-help :1788 Marathon posts are [mode]. | B | kept |
| field-help :1790 Marathon posts are in **shadow**: the board, the reminders and the shoutouts land where shadow_channel_id points, with the rehearsal note. | B | kept |
| field-help :611 Found, not tracked: it is read and kept current, and posts nothing. **Track** gives it its own thread…; **Ignore** keeps it quiet on the list. | B | kept-trimmed to the state (Track and Ignore are the buttons beside it) |
| field-help :1107 These are the channel’s own controls — every change here shows on the Go-live page too. [Open on Go-live ↗] | A | text removed; the link stays |
| field-help :1385 Staff decide: nothing is added until someone presses **Add it**. It airs on the feed’s channel. | A | removed (Add it / Not this one are the two buttons under it) |
| field-help :1603 Remembers N Oengus marathon(s) it has already looked at, so each is read once. **Look again** reads them all once more. (and the horaro / Lady Arcaders spellings) | B | kept-trimmed to the count: “Remembers N … it has already looked at.” |
| field-help :1627 the per-source paragraph under Read from (8 spellings): Every event on the GDQ tracker that is still ahead. / … / The GDQ Hotfix shows named in marathon_hotfix_shows… | A | removed; the horaro slug box's own label now reads “The part after horaro.net/” |
| field-help :1698 A source reads the events list of one channel Black Bloc already watches and adds (or suggests) every new marathon it finds… | A | removed |
| field-help :1699 Checks are off (marathon_feeds under **Marathons** in Settings and logs), so nothing checks on its own. **Check now** still works. | B | kept-trimmed to “Checks are off. **Marathons** under Settings and logs turns them on.” |
| field-help :1789 Marathon posts are **off**, so nothing is read or posted. **Marathons** under Settings and logs turns them on. | B | kept-trimmed to “Marathon posts are **off**. **Marathons** under Settings and logs turns them on.” |
| section note: Every marathon schedule Black Bloc reads; a row opens where it is read from, its runs, its event and its posts. | A | removed |
| dialog intro: Paste the GDQ schedule link (gamesdonequick.com/schedule/74) or the tracker event link. Black Bloc reads it at once… (the box's placeholder is that link) | A | removed |
| field help: The Twitch channel it airs on, from the Go-live page. With one, its ping window follows the marathon… | A | removed |
| field help (Event, add dialog): No event by default. One event for the marathon goes into the events review above… (11 lines) | A | removed |
| field help (Event, settings): Which Discord events this marathon makes; the setting explains the four choices. | A | removed |
| line: Staff decide: nothing is added until someone presses **Add it**. It is read from the tracker link and airs on this marathon’s channel. | A | removed |
| field help (Follow the schedule): On: the channel is spotlit from marathon_spotlight_lead_minutes before the first run… | A | removed |
| field help (Ping the marathon role): On: the public heads-up marathon_ping_minutes before a BaF run mentions the Marathon role… (the Marathon role / no Marathon role line under it is the state) | A | removed |
| field help (Auto-highlight): On: the moment a BaF run goes live its highlight posts in the public channel… | A | removed |
| field help (BaF announcements): On: every BaF runner and host of this marathon is announced publicly… | A | removed |
| field help (Event schedule): On: when the Hotfix schedule viewer links the event’s own schedule sheet… (the overlay line under it is the state) | A | removed |
| field helps (Twitch name, x2): Only when the schedule gives the wrong channel. It replaces the schedule’s everywhere Black Bloc uses one… | A | removed |
| dialog line: Only a channel-only row that takes marathons and has no feed reading the same source can be picked. (the picker lists only those) | A | removed |
| field help (feed Event): What a marathon this feed adds does about events; the first choice follows marathon_event_mode_default. | A | removed |
| field help (Auto-track): On: each marathon this feed adds is tracked the moment its schedule is out… | A | removed |
| line: A marathon this feed added and staff removed is never added again until **Forget ignored**. | A | removed |
| dialog intro (Add a feed): Pick the channel first — a feed belongs to a channel Black Bloc already watches… (8 sources described) | A | removed |
| field help (Shows): Every show on the Hotfix schedule this week. A ticked show becomes a marathon each run of days it airs… | A | removed |
| field help (Schedule viewer): A second source beside GDQ’s own sheet, never a replacement… | A | removed |
| archive line: Marathons that ended N day(s) ago or more, and any staff archived or removed. Nothing is deleted: a row opens it read-only, with Restore. | A | removed |
| field help (Re-read every): While it is near, 10 to 120; blank = the default (N). Far off: every N h. | C | converted — the empty box shows the default number, and a number outside 10–120 is refused in words as it is typed |
| dialog line: The schedule says **X**. Type the channel NAME really streams on, or leave it blank to go back to the schedule’s. | B + C | kept-trimmed to “The schedule says **X**.”; the empty box reads “blank keeps the schedule’s” |
| field help (Schedule viewer): …Blank turns it off. | C | converted — the empty box reads “https://… — blank turns it off” |
| dialog line: Any schedule Black Bloc reads: a GDQ or RPG Limit Break tracker, horaro.net, Oengus… It keeps its tracking, thread, event and switches, and reads the new schedule at once. | B | kept-trimmed to what the move does: “It keeps its tracking, thread, event and switches, and reads the new schedule at once.” |
| dialog line: **NAME** as MARATHON’s schedule writes it. A link beats the automatic match and makes their runs BaF at once; **Unlink** gives it back. | B | kept (the Link confirm step saying what it does) |
| state lines: Shows a BaF person runs are tracked too… Hosts always count, like runners. / Only the ticked shows are tracked — marathon_hotfix_track_people is off, so a BaF runner on another show does not add it. | B | kept-trimmed to the state |
| empty state: Nothing is archived yet. A marathon moves here N day(s) after its last run. | B | kept-trimmed to “Nothing is archived yet.” |
| state lines and confirm bodies kept as they are: No runs on this schedule yet… / Nobody from BaF is on this schedule yet — open a slot below and **Link to a member…** / No ping window — … / the Spotlight, Remove, Archive, Restore, Opt out confirm bodies | B | kept |
| field help (Add a feed, Name): Blank uses the channel’s name. | C | removed — the empty box already reads “the channel’s name” |

## Discord-side findings — listed, nothing changed

The same kind of sentence in what the BOT posts: panel intros and how-this-works lines. `black_bloc/` was not
touched by this sweep; this is the list for a later one. Found by constant name (`*_INTRO`, `*_HOW`, and the
notes that explain), so a blurb written inline in an embed is not on it.

| Where | Constant | It begins |
|---|---|---|
| `black_bloc/applications.py:221` | `PANEL_INTRO` | Apply for what this server hands out, and see where what you already sent has got to. |
| `black_bloc/birthdays.py:47` | `PANEL_INTRO` | Tell Black Bloc when your birthday is, and see whose is coming up. |
| `black_bloc/cogs/community/polls.py:321` | `DRAFT_INTRO` | Nothing is saved until you press **Post it**. |
| `black_bloc/cogs/community/polls.py:366` | `RESUMED_INTRO` | This is your saved draft. **Post it** puts it up and clears the draft. |
| `black_bloc/cogs/community/role_menus.py:163` | `SEED_EMOJI_NOTE` | A menu that already exists is left exactly as it is, options and all — to pick up the  |
| `black_bloc/cogs/community/role_menus.py:208` | `NEEDS_APPROVAL_NOTE` | Picking a role here asks staff first — you get a DM either way, and nothing changes until  |
| `black_bloc/cogs/community/role_menus.py:212` | `EXPIRES_NOTE` | A role from this menu lasts {days} day(s), then Black Bloc takes it back. |
| `black_bloc/cogs/community/tempvoice.py:188` | `PEOPLE_INTRO` | Who may be in your channel. Letting somebody in or shutting them out is remembered for your  |
| `black_bloc/cogs/community/tempvoice.py:192` | `REGION_INTRO` | Which of Discord's servers carries the audio. **Automatic** lets Discord pick the closest  |
| `black_bloc/cogs/community/tempvoice.py:196` | `HAND_OVER_INTRO` | Pick who should own **{channel}**. They get the controls and you do not — you keep whatever  |
| `black_bloc/cogs/community/tempvoice.py:200` | `LOBBY_INTRO` | The channels Black Bloc treats as join-to-create. Forgetting one leaves the Discord channel  |
| `black_bloc/cogs/content/chat.py:143` | `SETTINGS_FOOTER` | `/settings` ▸ **A setting group…** ▸ chat changes any of these, and the Chat page on  |
| `black_bloc/cogs/content/golive.py:160` | `STREAMERS_INTRO` | Everyone who has linked a Twitch channel. Picking one shows what Black Bloc knows about  |
| `black_bloc/cogs/content/pings.py:63` | `PANEL_INTRO` | What Black Bloc pings you about, and how to change it. Nothing here is on until you turn  |
| `black_bloc/cogs/content/pings.py:114` | `ROLE_PICK_INTRO` | Pick a role Black Bloc should use, or leave the picker empty and one is made from the  |
| `black_bloc/cogs/content/raidtrain.py:955` | `SETUP_HOW` | Pick what you want to change and press **Save**. **Clear…** empties one of them again. |
| `black_bloc/cogs/content/raidtrain.py:963` | `PUT_IN_HOW` | Pick the hour and the person, then press **Put them in**. |
| `black_bloc/cogs/content/raidtrain.py:966` | `SWAP_HOW` | Pick two hours, then press **Swap them**. The people move; the times do not. |
| `black_bloc/cogs/content/raidtrain.py:969` | `GIVE_BACK_HOW` | Pick the hour you would rather not keep. It opens again for somebody else. |
| `black_bloc/cogs/content/youtube.py:150` | `PANEL_INTRO` | Tell Black Bloc where your YouTube channel is and it posts when you go live, in the same  |
| `black_bloc/cogs/core.py:50` | `HELP_HEADER` | Every command Black Bloc can run here. The ones marked (staff) need the Manage Server  |
| `black_bloc/cogs/core.py:61` | `HIDDEN_NOTE` | \n*{count} command(s) are not listed because their feature is turned off. A Lead brings  |
| `black_bloc/cogs/core.py:435` | `PANEL_MINUTES_INTRO` | **How long a panel stays open** — {count} panels have their own number, and the picker  |
| `black_bloc/cogs/core.py:439` | `LEVELS_INTRO` | Every feature keeps every line on the dashboard's Logs page. This decides how much of it  |
| `black_bloc/cogs/core.py:443` | `GROUP_INTRO` | {count} setting(s) in **{group}**. Pick one to see what it is and change it. |
| `black_bloc/cogs/moderation/automod.py:177` | `EXEMPT_INTRO` | Staff are always exempt. These are the roles and channels automod skips on top of that. |
| `black_bloc/cogs/moderation/honeypot.py:860` | `FORGET_INTRO` | Forgetting a channel only stops Black Bloc treating it as a trap — the channel itself is  |
| `black_bloc/events.py:583` | `DRAFT_ZONE_HINT` | Times are read in **{tz}** — the server's default. Press **Time zone** if that is not yours. |
| `black_bloc/events.py:593` | `WHERE_PANEL_INTRO` | Pick the voice or text channel it happens in, or **Other** for a place or a link that is  |
| `black_bloc/events.py:605` | `WHERE_JOIN_NOTE` | A voice or stage channel gives everybody a **Join** button on the Discord event; anything  |
| `black_bloc/events.py:625` | `ZONE_PANEL_INTRO` | Times you pick are read in this zone. Pick one, or **Other — type it…** for anywhere else. |
| `black_bloc/events.py:973` | `PANEL_INTRO` | Propose something for the server to do, and see where the open ones have got to. |
| `black_bloc/golive.py:705` | `PANEL_INTRO` | Your Twitch channel, and whether your streams get announced. |
| `black_bloc/minutes.py:78` | `PANEL_INTRO` | Black Bloc joins the voice channel you are in, listens, and writes the meeting up  |
| `black_bloc/modmail.py:556` | `MEMBER_INTRO` | Modmail is how you reach staff privately. Nobody else sees what you write. |
| `black_bloc/polls.py:200` | `PANEL_HOW_ONE` | Press an option to vote. Pressing a different one moves your vote. |
| `black_bloc/polls.py:201` | `PANEL_HOW_MANY` | Press everything that works for you. Pressing one again takes it back. |
| `black_bloc/polls.py:202` | `PANEL_HIDDEN` | Hidden until this closes, so nobody's vote is swayed by the bars. |
| `black_bloc/polls.py:299` | `PANEL_INTRO` | Put something to the room, or look at what is already running. |
| `black_bloc/posts.py:207` | `PANEL_INTRO` | The messages Black Bloc keeps current in this server. |
| `black_bloc/posts.py:216` | `VERSIONS_INTRO` | Every press of Save changes or Post it that changed something is here. Nothing else writes  |
| `black_bloc/requests.py:226` | `PANEL_INTRO` | Ask the server for something, or see where what you already asked for has got to. |
| `black_bloc/settings_panel.py:131` | `ROOT_INTRO` | The settings no feature panel owns. All {total} of them are on the site, and every one is  |
| `black_bloc/settings_panel.py:206` | `SELFTEST_INTRO` | Black Bloc exercises itself against this server: every setting's channel and role, every  |
| `black_bloc/spotlight.py:156` | `PANEL_INTRO` | Twitch channels watched by name, for org channels and marathons that have nobody in this  |
| `black_bloc/spotlight.py:298` | `CHANNELS_INTRO` | Twitch channels watched by name, for org channels and marathons that have nobody in this  |
| `black_bloc/tempvoice.py:66` | `PANEL_INTRO` | Your own temporary voice channel, and everything you can change about it. Nothing here  |
| `black_bloc/tempvoice.py:111` | `MODE_INTRO` | What joining the lobby does, and who can see it. |

Three of the site's own settings keys are intros by name and are posted words (`chat_channel_notes_intro`,
`chat_voice_intro`, `chat_review_intro` in `settings_store.py`), and `marathon_channel_ping_help` is the one the
site draws (UNDECIDED above).
