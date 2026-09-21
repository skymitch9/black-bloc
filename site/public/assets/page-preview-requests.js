import { start } from './app.js';
import { importantSwitch, logsTable } from './logs.js';
import { previewBanner, previewWas, wouldDo } from './preview.js';
import {
  ago,
  ask,
  avatar,
  badge,
  bar,
  button,
  card,
  channelLabel,
  el,
  field,
  foldout,
  notice,
  openDrawer,
  sayNothing,
  searchField,
  section,
  segment,
  textAction,
} from './ui.js';

const minutesAgo = (m) => new Date(Date.now() - m * 60000).toISOString();
const dayAhead = (d) => {
  const at = new Date(Date.now() + d * 86400000);
  return `${at.getFullYear()}-${String(at.getMonth() + 1).padStart(2, '0')}-${String(at.getDate()).padStart(2, '0')}`;
};

const MEMBERS = [
  { id: '700000000000000001', name: 'nbaslamking', display_name: 'Nick' },
  { id: '700000000000000002', name: 'caseyfast', display_name: 'Casey' },
  { id: '700000000000000003', name: 'rivet.exe', display_name: 'Rivet' },
  { id: '700000000000000004', name: 'moth_light', display_name: 'Moth' },
  { id: '700000000000000005', name: 'spamlord99', display_name: 'spamlord99' },
  { id: '700000000000000006', name: 'quietkid', display_name: 'Quiet Kid' },
  { id: '700000000000000007', name: 'daxthecat', display_name: 'Dax' },
  { id: '700000000000000008', name: 'gonefromguild', display_name: 'Left the server' },
];
const STAFF = MEMBERS[0];

const CHANNELS = [
  { id: '800000000000000001', name: 'welcome', type: 'text', category_id: null, position: 0 },
  { id: '800000000000000002', name: 'general', type: 'text', category_id: null, position: 1 },
  { id: '800000000000000003', name: 'blackbloc-logs', type: 'text', category_id: null, position: 2 },
  { id: '800000000000000004', name: 'bot-log', type: 'text', category_id: null, position: 3 },
  { id: '800000000000000005', name: 'staff-room', type: 'text', category_id: null, position: 4 },
  { id: '800000000000000006', name: 'announcements', type: 'text', category_id: null, position: 5 },
  { id: '800000000000000007', name: 'free-nitro-here', type: 'text', category_id: null, position: 6 },
  { id: '800000000000000008', name: 'Events', type: 'category', category_id: null, position: 7 },
  { id: '800000000000000009', name: 'Join to create', type: 'voice', category_id: null, position: 8 },
  { id: '800000000000000010', name: "casey's room", type: 'voice', category_id: null, position: 9 },
  { id: '800000000000000011', name: 'modmail', type: 'category', category_id: null, position: 10 },
  { id: '800000000000000012', name: 'modmail-log', type: 'text', category_id: '800000000000000011', position: 11 },
];

const REQUEST_SEED = [
  [30, 3, 'A #suggestions channel with a poll under every idea', 'The ideas doc is where suggestions go to die. If each one opened a poll we would know in a day whether anybody else wants it.', null, 'open', null, null, null, 40, null],
  [29, 0, 'Let /request take screenshots', 'Half of what I want to describe is a picture of the thing being wrong. Typing it out loses the detail.', 21, 'open', null, null, null, 120, null],
  [28, 6, 'A weekly digest of what the bot did', 'Nobody reads the log channel. One Monday post with the week in five lines would actually get read.', 7, 'open', null, null, null, 300, null],
  [27, 2, 'Birthday shout-outs should skip people who are not in the server any more', 'We wished a happy birthday to somebody who left in March and it was awkward for everyone.', null, 'open', null, null, null, 900, null],
  [26, 5, 'Let members mute the go-live pings without leaving the role', 'I want the colour, not the notification. Right now it is both or neither.', 30, 'open', null, null, null, 1500, null],
  [25, 0, 'A queue for the karaoke nights', 'We keep losing the running order in chat. A /queue with a list everybody can see would fix it.', 14, 'open', null, null, null, 2600, null],
  [24, 1, 'Temp voice channels should remember the name I gave them', 'I rename mine every single time. It should come back the way I left it.', null, 'open', 3, null, null, 4200, null],
  [23, 6, 'Show who is in a temp voice room from the text channel', 'You cannot tell whether it is worth joining without joining.', 45, 'open', 2, 0, null, 5000, null],
  [22, 2, 'An /events ical export', 'Half the group lives in a different time zone and reads the calendar app, not Discord.', 60, 'open', 4, null, 'Casey has the feed format from last year.', 6400, null],
  [21, 4, 'Automod should let me appeal a timeout', 'I got a ten minute timeout for a link nobody minded and there was nowhere to say so.', null, 'open', 5, null, null, 7000, null],
  [20, 3, 'Role menus with a description under each role', 'The emoji is not enough. New people pick the wrong one every week.', 25, 'hold', 2, 0, 'Fits under the existing menu editor — no new storage.', 8200, 'Waiting on the role menu rewrite so this is not built twice.', 'in_progress'],
  [19, 1, 'A #welcome message that names the three channels worth reading', 'We say the same three things to every new person by hand.', null, 'open', 3, 1, null, 9000, null],
  [18, 6, 'Let staff pin a poll result to the top of the channel', 'The result scrolls away and then we argue about it again a month later.', 40, 'open', 3, null, null, 9800, null],
  [17, 2, 'Modmail should show the member\'s last five messages', 'You open a ticket with no idea what happened just before it.', null, 'hold', 1, 0, 'Needs a message cache the bot does not keep yet — ask before starting.', 11000, 'Nothing keeps old messages yet, so there is nothing to show. Waiting on that.', 'open'],
  [16, 5, 'A quiet hours mode for the announcement pings', 'Three in the morning go-live pings are why I turned notifications off entirely.', 90, 'open', 4, null, null, 12000, null],
  [15, 3, 'The cookout countdown on the dashboard', 'Everybody asks how long is left and somebody has to do the arithmetic in their head.', 10, 'in_progress', 2, 0, 'Half built; the timer is drawn, the setting is not wired.', 13000, null],
  [14, 1, 'Search the audit log by member', 'Scrolling to find one person\'s three lines takes minutes.', null, 'in_progress', 1, 1, null, 14000, null],
  [13, 6, 'Let me file a request from a message with a right-click', 'Half of the requests start as somebody complaining in chat.', 35, 'in_progress', 3, 0, null, 15000, null],
  [12, 2, 'Honeypot should tell staff what the trap caught', 'The ban lands and nobody knows what was posted.', null, 'in_progress', 2, 3, 'Rivet is on this one while Moth is away.', 16000, null],
  [11, 3, 'Stop the bot answering @-mentions inside threads', 'It talks over serious threads and it is hard to take seriously afterwards.', null, 'review', 2, 0, null, 20000, null, null, 'A chat_reply_in_threads setting, on by default, that stops the bot answering an @-mention inside a thread.', 'Turn chat_reply_in_threads off on the Chat page, @-mention the bot inside any thread, and watch it stay quiet. Turn it back on and it answers again.'],
  [10, 0, 'A /help that lists only the commands I can actually run', 'The full list is intimidating and most of it refuses me anyway.', null, 'done', 3, 0, null, 22000, null, null, '/help now filters the list against what the caller may actually run, and marks the staff ones.', 'Run /help as a member and again as a Lead — the second list is longer and the staff lines carry the (staff) mark.'],
  [9, 6, 'Timed roles for the event crew', 'We hand the role out and then forget to take it back for months.', null, 'done', 1, 1, 'Shipped as part of the role menus work.', 24000, null, null, 'Role menus grew an expires_days field, and the sweep takes the role back when it runs out.', 'Set a role menu option to expire after a day, take the role, and check the Role menus page shows when it lapses.'],
  [8, 2, 'Birthday wishes with the member\'s own colour', 'A grey embed for a birthday is a bit sad.', null, 'done', 5, 0, null, 26000, null],
  [7, 4, 'Let people opt out of go-live announcements', 'Some of us stream for four people on purpose.', null, 'done', 2, 1, null, 28000, null],
  [6, 5, 'A dashboard I can read on my phone', 'I am never at a desk when something needs answering.', null, 'done', 1, 0, 'The whole site got this, not just one page.', 30000, null],
  [5, 4, 'Give everybody the ping role by default', 'More people would see the announcements.', null, 'declined', null, null, null, 32000, 'Opt-in is the whole point of that role — a default ping is the thing people leave servers over. Ask again if you want a second, quieter role.'],
  [4, 5, 'Let members delete other people\'s messages in their own temp room', 'It is my room, I should be able to tidy it.', null, 'declined', null, null, null, 34000, 'Deleting somebody else\'s words is a moderator action and it stays with the moderators. You can kick somebody from your room instead.'],
  [3, 7, 'An auto-role that gives new joins the Member role instantly', 'The manual step is slow.', null, 'declined', null, null, null, 40000, 'The manual step is the anti-raid measure. We looked at this in March and the answer has not changed — see the pinned post in the Leads channel.'],
  [2, 1, 'Rename #general to #the-porch', 'It suits the place better.', null, 'withdrawn', null, null, null, 41000, null],
  [1, 3, 'A second bot for music', 'Nobody has bothered since the last one broke.', null, 'withdrawn', null, null, null, 44000, null],
];

const REQUEST_COMMENT_SEED = [
  [1, 30, 0, 'This is close to what #ideas was meant to be. Worth doing properly once rather than twice badly.', 30],
  [2, 30, 2, 'A poll under every one would drown the channel. Poll the ones that get five reactions?', 20],
  [3, 27, 0, 'Agreed, and it is a one-line check against the member list.', 800],
  [4, 25, 3, 'I have the running order from the last three nights if that helps size it.', 2400],
  [5, 22, 0, 'Casey is right that the feed format is the hard part. Nothing else here is new.', 6000],
  [6, 22, 1, 'I will dig the old one out this week.', 5900],
  [7, 20, 0, 'Planned for after the requests work lands.', 8000],
  [8, 17, 0, 'Holding this one — the message cache is a bigger change than the ticket view is.', 10500],
  [9, 17, 2, 'Even the last one message would help.', 10400],
  [10, 15, 0, 'Timer is drawn. The setting for the date is the bit left.', 12500],
  [11, 15, 3, 'Can it count down to the next one automatically rather than a date somebody types?', 12400],
  [12, 12, 2, 'Taking this while Moth is away.', 15500],
  [13, 11, 0, 'Shipped — chat_reply_in_threads turns it off.', 19000],
  [14, 5, 0, 'Saying no here rather than in DMs so the reasoning is on the record.', 31000],
  [15, 3, 0, 'Third time this has been asked. The pinned post is the long answer.', 39000],
];

const TRANSITIONS = {
  open: ['declined', 'hold', 'in_progress'],
  in_progress: ['declined', 'hold', 'review'],
  review: ['declined', 'done', 'hold', 'in_progress'],
  hold: ['declined', 'in_progress', 'review'],
  done: [],
  declined: [],
  withdrawn: [],
};

const SAID = {
  open: 'open',
  in_progress: 'in progress',
  review: 'ready to check',
  hold: 'on hold',
  done: 'done',
  declined: 'declined',
  withdrawn: 'withdrawn',
};

const TONE = {
  open: 'warn',
  in_progress: 'info',
  review: 'info',
  hold: 'warn',
  done: 'ok',
  declined: null,
  withdrawn: null,
};

const LOG_ROWS = [
  { id: 46, at: minutesAgo(1), kind: 'web.request.declined', feature: 'request', important: true, via: 'website', actor_id: STAFF.id, actor_name: 'Nick', target_id: MEMBERS[7].id, target_name: 'Left the server', reason: 'Opt-in is the whole point of that role.', summary: 'Opt-in is the whole point of that role.' },
  { id: 45, at: minutesAgo(2), kind: 'web.request.in_progress', feature: 'request', important: false, via: 'website', actor_id: STAFF.id, actor_name: 'Nick', target_id: MEMBERS[1].id, target_name: 'Casey', reason: null, summary: 'request_id=24, was=open' },
  { id: 44, at: minutesAgo(2), kind: 'request.filed', feature: 'request', important: false, via: 'discord', actor_id: MEMBERS[3].id, actor_name: 'Moth', target_id: MEMBERS[3].id, target_name: 'Moth', reason: null, summary: 'request_id=30' },
  { id: 43, at: minutesAgo(3), kind: 'web.request.updated', feature: 'request', important: false, via: 'website', actor_id: STAFF.id, actor_name: 'Nick', target_id: null, target_name: null, reason: null, summary: 'request_id=20, changed=assignee_id,priority' },
  { id: 42, at: minutesAgo(3), kind: 'request.done', feature: 'request', important: true, via: 'discord', actor_id: STAFF.id, actor_name: 'Nick', target_id: MEMBERS[6].id, target_name: 'Dax', reason: null, summary: 'request_id=11' },
];

const SETTING_SPECS = [
  { key: 'request_mode', type: 'enum', value: 'on', choices: ['off', 'shadow', 'on'], label: 'Requests', help: 'off refuses new requests in words; shadow files them into the log channel; on is normal' },
  { key: 'request_who_can_file', type: 'enum', value: 'everyone', choices: ['staff', 'everyone'], label: 'Who can file', help: 'who may file a request: staff, or everyone' },
  { key: 'request_notify_channel_id', type: 'channel', value: '800000000000000005', label: 'Arrival channel', help: 'where the bot says a request arrived' },
  { key: 'request_status_channel_id', type: 'channel', value: null, label: 'Moves channel', help: 'where the bot says a request moved; blank uses the arrival channel' },
  { key: 'request_forum_channel_id', type: 'channel', value: null, label: 'Request forum', help: 'the forum channel every request is posted in; Make the forum below makes one' },
  { key: 'request_dm_on_decision', type: 'bool', value: true, label: 'DM on a decision', help: 'true DMs the person who asked every time staff move it' },
  { key: 'request_channel_moves', type: 'bool', value: true, label: 'Say when it moves', help: 'true posts a line in the moves channel each time a request changes state' },
  { key: 'request_review_by_other', type: 'bool', value: true, label: 'Somebody else checks', help: 'true asks a second pair of eyes: whoever marked it ready cannot be the one to Accept it' },
  { key: 'request_check_fallback_channel', type: 'bool', value: true, label: 'Ask in a channel when DMs are shut', help: 'true asks the person to check in a channel when their DMs are closed' },
  { key: 'request_check_on_ready', type: 'bool', value: false, label: 'Ask them on ready', help: 'true asks the person who asked to try it the moment it is marked ready to check' },
  { key: 'request_post_buttons', type: 'bool', value: true, label: 'Buttons on the card', help: 'true puts the move buttons on the card Black Bloc posts in Discord' },
  { key: 'request_forum_adopts_posts', type: 'bool', value: true, label: 'Forum adopts posts', help: 'true turns a post somebody starts by hand in the requests forum into a request filed by them' },
  { key: 'request_log_level', type: 'enum', value: 'important', choices: ['off', 'important', 'all'], label: 'Log level', help: 'how much of what requests does reaches the action log' },
];

const WHY_MAX = 1000;
const BUILT_MAX = 1000;
const SENT_BACK_MAX = 500;

const OPEN_NOTE = 'Filed and not picked up, longest wait first. Every button here tells the ' +
  'person who asked — picking one up, putting it on hold, and declining it.';
const BOARD_NOTE = 'Being worked on. The buttons here save as you press them — there is no ' +
  'separate Save for the status, the priority or who is on it.';
const HELD_NOTE = 'Parked with a reason, and the reason is what the person who asked was sent. ' +
  'Resume puts one back where it came from.';
const REVIEW_NOTE = 'Built and waiting for somebody to look at it. Accept is the only way a ' +
  'request reaches Done, so what is written here is what the person who asked ends up reading.';
const CLOSED_NOTE = 'Requests that shipped, the answers that were no, and the ones the person ' +
  'who asked took back themselves. Nothing here needs anything from you.';
const SETTINGS_NOTE = 'Whether requests are open, who may file one, where the bot says a request ' +
  'arrived, where it says one moved, and whether it DMs the person who asked each time.';
const LOGS_NOTE = 'Everything this part of Black Bloc has done, whether or not it said so in ' +
  'Discord. Important means it acted on a member or failed.';
const FILE_NOTE = 'The same three fields as /request in Discord. Whoever is signed in is ' +
  'recorded as the person asking — there is no name to fill in.';
const FORUM_NOTE = 'With a forum, every request is a post of its own — the card is its first ' +
  'message, every move lands in the same post, and the post is tagged for wherever the request ' +
  'has got to. Make the forum puts one under the Blackmail category with that category’s own ' +
  'permissions. Leave it unmade and requests behave exactly as they do today.';

const NO_OPEN = 'Nothing is open. Everything filed has been picked up, finished or answered.';
const NO_BOARD = 'Nothing is being worked on. Pick something up above and it lands here.';
const NO_HELD = 'Nothing is on hold.';
const NO_REVIEW = 'Nothing is waiting to be checked. Press Ready to check on something being ' +
  'worked on and it lands here.';
const NO_CLOSED = 'Nothing has shipped, been declined or been taken back yet.';
const NO_MATCH = 'Nothing filed matches what you typed.';

const NEED_A_WHAT = 'Say what you want built first — one line is enough.';
const NEED_A_WHY = 'Say why it is worth building. That is the part that decides the answer, so ' +
  'the form will not send without it.';
const NEED_A_NOTE = 'There is nothing to add yet.';
const NEED_A_BUILT = 'Say what was built first. That line is what the person who asked reads on ' +
  'the card, so the form will not send without it.';
const NEED_A_SENDBACK = 'Say what is still to do. Whoever marked it ready is sent exactly this.';
const NEED_A_PERSON = 'Nobody is picked yet, so nothing was changed. Type part of a name and ' +
  'choose somebody from the list.';

const MOVES = {
  in_progress: { label: 'Pick it up', tone: 'warn' },
  hold: {
    label: 'Put it on hold',
    tone: 'quiet',
    reason: {
      title: (row) => `Park ${row.requester.name}'s request?`,
      body: 'They are sent exactly what you type here, and it moves to On hold.',
      confirm: 'Put it on hold',
      hint: 'Say what it is waiting on.',
    },
  },
  declined: {
    label: 'Decline',
    tone: 'danger',
    reason: {
      title: (row) => `Say no to ${row.requester.name}?`,
      body: 'They are sent exactly what you type here, and the request is closed for good.',
      confirm: 'Decline it',
      hint: 'Say why.',
    },
  },
};

const PRIORITY_SAID = {
  1: '1 — do it first',
  2: '2 — soon',
  3: '3 — when there is room',
  4: '4 — nice to have',
  5: '5 — some day',
};

const ASSIGNEE_FILTERS = [
  ['', 'Anybody'],
  ['none', 'Nobody yet'],
  ['me', 'On me'],
];

const CLOSED_FILTERS = [
  ['', 'Everything'],
  ['done', 'Done'],
  ['declined', 'Declined'],
  ['withdrawn', 'Taken back'],
];

const state = { q: '', assignee: '', closed: '', important: true };

let refresh = () => {};
let viewer = null;

function person(index) {
  if (index === null || index === undefined) return null;
  const found = MEMBERS[index];
  return { id: found.id, name: found.display_name || found.name, avatar: null };
}

function comments(id) {
  return REQUEST_COMMENT_SEED
    .filter(([, requestId]) => requestId === id)
    .map(([commentId, , who, text, aged]) => ({
      id: String(commentId),
      author: person(who),
      text,
      at: minutesAgo(aged),
    }));
}

function rowsOf() {
  return REQUEST_SEED.map(([id, who, what, why, due, status, priority, assignee, notes, aged, reason, heldFrom, built, howToTest]) => {
    const held = status === 'hold' ? heldFrom || 'open' : null;
    return {
      id: String(id),
      what,
      why,
      due_on: due === null ? null : dayAhead(due),
      status,
      priority,
      notes,
      requester: person(who),
      assignee: person(assignee),
      comment_count: comments(id).length,
      comments: comments(id),
      created_at: minutesAgo(aged),
      decline_reason: reason || null,
      held_from: held,
      held_word: held ? SAID[held] || held : '',
      built: built || null,
      how_to_test: howToTest || null,
      ready_by_name: built ? STAFF.display_name : null,
      sent_back_reason: null,
      check_asked_at: null,
      check_asked_by_name: null,
      moves: TRANSITIONS[status] || [],
      resume_to: held ? ((TRANSITIONS.hold || []).includes(held) ? held : 'in_progress') : null,
      done_at: status === 'done' ? minutesAgo(Math.round(aged * 0.2)) : null,
    };
  });
}

const ALL = rowsOf();

function matches(row) {
  if (state.q) {
    const hay = [row.what, row.why, row.notes, row.requester ? row.requester.name : '']
      .join(' ')
      .toLowerCase();
    if (!hay.includes(state.q)) return false;
  }
  if (state.assignee === 'none' && row.assignee) return false;
  if (state.assignee === 'me') {
    const me = viewer && viewer.user ? String(viewer.user.id) : STAFF.id;
    if (!row.assignee || String(row.assignee.id) !== me) return false;
  }
  return true;
}

function inState(status) {
  return ALL.filter((row) => row.status === status && matches(row));
}

function dueOn(day) {
  if (!day) return null;
  const parts = String(day).split('-').map(Number);
  if (parts.length !== 3 || parts.some((one) => !Number.isFinite(one))) return null;
  const at = new Date(parts[0], parts[1] - 1, parts[2]);
  if (Number.isNaN(at.getTime())) return null;
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const days = Math.round((at - today) / 86400000);
  const title = at.toLocaleDateString([], {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
  });
  if (days === 0) return { text: 'due today', title, days };
  if (days > 0) return { text: `due in ${days} day${days === 1 ? '' : 's'}`, title, days };
  const gone = Math.abs(days);
  return { text: `due ${gone} day${gone === 1 ? '' : 's'} ago`, title, days };
}

function dueChip(row) {
  const found = dueOn(row.due_on);
  if (!found) return null;
  const tone = found.days < 0 ? 'danger' : found.days <= 3 ? 'warn' : null;
  return el('span', {
    class: 'req-due',
    'data-tone': tone || undefined,
    title: found.title,
    text: found.text,
  });
}

function statusPill(row) {
  return badge(SAID[row.status] || row.status, TONE[row.status] ?? null);
}

function heldChip(row) {
  if (row.status !== 'hold' || !row.held_word) return null;
  return badge(`was: ${row.held_word}`, null);
}

function readyChip(row) {
  if (!row.ready_by_name) return null;
  return badge(`ready by ${row.ready_by_name}`, null);
}

function requesterNode(one) {
  const name = one && one.name ? one.name : 'somebody who has left';
  return el('a', {
    class: 'req-who',
    href: '/members.html',
    title: `${name} · Discord id ${one ? one.id : 'not known'} — open the Members page`,
  }, [avatar(name, one ? one.avatar : null), el('span', { class: 'req-who-name', text: name })]);
}

function metaLine(row) {
  const asked = ago(row.created_at);
  const parts = [`asked ${asked.text}`];
  if (row.priority !== null && row.priority !== undefined) parts.push(`priority ${row.priority}`);
  if (row.assignee) parts.push(`${row.assignee.name} is on it`);
  if (row.done_at) parts.push(`shipped ${ago(row.done_at).text}`);
  return el('span', { class: 'req-meta', title: asked.title, text: parts.join(' · ') });
}

function anchored(row, node) {
  node.id = `r-${row.id}`;
  return node;
}

function headBlock(row, marks) {
  return el('div', { class: 'req-head' }, [
    requesterNode(row.requester),
    el('div', { class: 'req-headtext' }, [
      el('p', { class: 'req-what', text: row.what }),
      metaLine(row),
    ]),
    el('div', { class: 'req-marks' }, marks || [statusPill(row), heldChip(row), dueChip(row)]),
  ]);
}

function whyBlock(why) {
  const text = el('p', { class: 'req-why', 'data-open': 'false', text: why || '' });
  const more = el('button', { class: 'req-more', type: 'button', text: 'Read the rest', hidden: true });
  more.addEventListener('click', () => {
    const open = text.getAttribute('data-open') === 'true';
    text.setAttribute('data-open', open ? 'false' : 'true');
    more.textContent = open ? 'Read the rest' : 'Show less';
  });
  return el('div', { class: 'req-whybox' }, [text, more]);
}

function measureWhy() {
  for (const text of document.querySelectorAll('.req-why')) {
    const more = text.parentElement.querySelector('.req-more');
    if (!more) continue;
    if (text.getAttribute('data-open') === 'true') {
      more.hidden = false;
      continue;
    }
    more.hidden = text.scrollHeight <= text.clientHeight + 1;
  }
}

let measureSoon = null;

document.addEventListener('toggle', () => measureWhy(), true);
window.addEventListener('resize', () => {
  if (measureSoon) clearTimeout(measureSoon);
  measureSoon = setTimeout(measureWhy, 150);
});

function commentNode(one) {
  const at = ago(one.at);
  return el('div', { class: 'req-note' }, [
    el('span', { class: 'req-note-who', title: at.title, text: `${one.author.name} · ${at.text}` }),
    el('p', { class: 'req-note-text', text: one.text }),
  ]);
}

function commentsDrawer(row) {
  const say = notice();
  const box = el('input', { class: 'input', type: 'text', placeholder: 'a note for the other staff' });
  const add = button('Add the note', () => {
    if (!box.value.trim()) {
      say.say(NEED_A_NOTE, 'warn');
      return;
    }
    wouldDo(say, `POST /api/requests/${row.id}/comments — add that note for the other staff. The ` +
      'person who asked never sees it');
  });
  return foldout('Notes', [
    el('div', { class: 'req-notes' }, row.comments.length
      ? row.comments.map(commentNode)
      : [sayNothing('Nobody has said anything about this one yet.')]),
    el('div', { class: 'formrow' }, [field('Add a note', box), bar([add])]),
    say,
  ], { count: row.comment_count });
}

function prioritySelect(row, say) {
  const box = el('select', { class: 'input' });
  box.append(el('option', { value: '', text: 'not set', selected: row.priority === null || undefined }));
  for (const step of [1, 2, 3, 4, 5]) {
    box.append(el('option', {
      value: String(step),
      text: PRIORITY_SAID[step],
      selected: String(row.priority) === String(step) || undefined,
    }));
  }
  box.addEventListener('change', () => {
    wouldDo(say, `POST /api/requests/${row.id}/status — set the priority to ` +
      `${box.value === '' ? 'not set' : box.value}`);
  });
  return box;
}

function assigneeControl(row, say) {
  const holder = el('div', { class: 'req-assign' });
  let paint = () => {};

  const open = () => {
    const box = el('select', { class: 'input' });
    box.append(el('option', { value: '', text: 'nobody yet', selected: true }));
    for (const one of MEMBERS) box.append(el('option', { value: one.id, text: one.display_name || one.name }));
    holder.replaceChildren(field('Put somebody on it', box), bar([
      button('Save', () => {
        if (!box.value) {
          say.say(NEED_A_PERSON, 'warn');
          return;
        }
        const found = MEMBERS.find((one) => one.id === box.value);
        wouldDo(say, `POST /api/requests/${row.id}/status — put ${found.display_name || found.name} on it`);
      }),
      button('Cancel', () => paint(), { tone: 'quiet' }),
    ]));
  };

  paint = () => {
    holder.replaceChildren(...[
      el('span', { class: 'req-assign-now', text: row.assignee ? row.assignee.name : 'nobody yet' }),
      button('Change', open, { tone: 'quiet' }),
      row.assignee
        ? button('Take them off', () => wouldDo(say, `POST /api/requests/${row.id}/status — take ` +
          `${row.assignee.name} off it and leave it unassigned`), { tone: 'quiet' })
        : null,
    ].filter(Boolean));
  };

  paint();
  return holder;
}

function notesRow(row, say) {
  const box = el('textarea', { class: 'input area', rows: '2', placeholder: 'staff only — the person who asked never sees this' });
  box.value = row.notes || '';
  const save = button('Save the note', () => {
    wouldDo(say, `POST /api/requests/${row.id}/status — store that staff note. The person who ` +
      'asked never sees it');
  }, { disabled: true });
  box.addEventListener('input', () => {
    save.disabled = box.value.trim() === String(row.notes || '').trim();
  });
  return el('div', { class: 'formrow' }, [
    field('Staff note', box, 'What is left to do, or what is blocking it.'),
    bar([save]),
  ]);
}

function writtenRow(row, say, name, label, hint) {
  const box = el('textarea', { class: 'input area', rows: '2', maxlength: String(BUILT_MAX) });
  box.value = row[name] || '';
  const save = button('Save', () => {
    wouldDo(say, `POST /api/requests/${row.id}/status — store “${label}”. Nothing moves`);
  }, { disabled: true });
  box.addEventListener('input', () => {
    save.disabled = box.value.trim() === String(row[name] || '').trim();
  });
  return el('div', { class: 'formrow' }, [field(label, box, hint), bar([save])]);
}

function writtenBlock(row) {
  const shown = [];
  if (row.built) shown.push(el('p', { class: 'req-built' }, [
    el('strong', { text: 'What was built: ' }),
    el('span', { text: row.built }),
  ]));
  if (row.how_to_test) shown.push(el('p', { class: 'req-built' }, [
    el('strong', { text: 'How to test it: ' }),
    el('span', { text: row.how_to_test }),
  ]));
  if (row.sent_back_reason) shown.push(el('p', { class: 'req-reason', text: `Sent back: ${row.sent_back_reason}` }));
  return shown;
}

/** One button per move the row's own list allows — a control that would be refused is never drawn. */
function moveButtons(row, say, moves) {
  return (moves || row.moves || []).map((wanted) => {
    const spec = MOVES[wanted];
    if (!spec) return null;
    return button(spec.label, async () => {
      if (!spec.reason) {
        wouldDo(say, `POST /api/requests/${row.id}/status — move it to ${SAID[wanted]} and DM ` +
          `${row.requester.name} that it moved`);
        return;
      }
      const box = el('input', { class: 'input', type: 'text', placeholder: 'why — they are sent this' });
      const sure = await ask({
        title: spec.reason.title(row),
        body: [spec.reason.body, field('Reason', box, spec.reason.hint)],
        confirmLabel: spec.reason.confirm,
      });
      if (!sure) return;
      wouldDo(say, `POST /api/requests/${row.id}/status — move it to ${SAID[wanted]} and send ` +
        `${row.requester.name} exactly what you typed`);
    }, { tone: spec.tone, small: false });
  }).filter(Boolean);
}

function resumeButton(row, say) {
  return button('Resume', () => {
    wouldDo(say, `POST /api/requests/${row.id}/resume — put it back to ` +
      `${SAID[row.resume_to] || row.resume_to}, where it came from`);
  }, { tone: 'warn', small: false });
}

function readyButton(row, say) {
  return button('Ready to check', async () => {
    const built = el('textarea', { class: 'input area', rows: '3', maxlength: String(BUILT_MAX) });
    built.value = row.built || '';
    const how = el('textarea', { class: 'input area', rows: '3', maxlength: String(BUILT_MAX) });
    how.value = row.how_to_test || '';
    const sure = await ask({
      title: `Say what was built for ${row.requester ? row.requester.name : 'this'}?`,
      body: [
        'Both lines show on the card in Discord and on this page. Either can be edited afterwards without moving the request.',
        field('What was built', built, 'One or two sentences.'),
        field('How to test it', how, 'Optional — the steps somebody follows to see it working.'),
      ],
      confirmLabel: 'Mark it ready to check',
    });
    if (!sure) return;
    if (!built.value.trim()) {
      say.say(NEED_A_BUILT, 'warn');
      return;
    }
    wouldDo(say, `POST /api/requests/${row.id}/ready — move it to ready to check and put those ` +
      'two lines on the card');
  }, { tone: 'warn', small: false });
}

function acceptButton(row, say) {
  return button('Accept', () => {
    wouldDo(say, `POST /api/requests/${row.id}/accept — finish it, and DM ${row.requester.name} ` +
      'what was built');
  }, { tone: 'ok', small: false });
}

function askCheckButton(row, say) {
  return button('Ask them to check', () => {
    wouldDo(say, `POST /api/requests/${row.id}/check — DM ${row.requester.name} and ask them to ` +
      'try it');
  }, { tone: 'quiet', small: false });
}

function sendBackButton(row, say) {
  return button('Send back', async () => {
    const box = el('input', {
      class: 'input', type: 'text', maxlength: String(SENT_BACK_MAX),
      placeholder: 'what is still to do',
    });
    const sure = await ask({
      title: 'Send this one back?',
      body: [
        `${row.ready_by_name || 'Whoever marked it ready'} is sent exactly what you type, and it goes back to In progress.`,
        field('What needs doing', box, 'Say what is missing.'),
      ],
      confirmLabel: 'Send it back',
    });
    if (!sure) return;
    if (!box.value.trim()) {
      say.say(NEED_A_SENDBACK, 'warn');
      return;
    }
    wouldDo(say, `POST /api/requests/${row.id}/sendback — put it back to in progress and send ` +
      `${row.ready_by_name || 'whoever marked it ready'} exactly what you typed`);
  }, { tone: 'quiet', small: false });
}

function openCard(row) {
  const say = notice();
  return anchored(row, card(null, [
    headBlock(row),
    whyBlock(row.why),
    bar(moveButtons(row, say)),
    commentsDrawer(row),
    say,
  ]));
}

function boardCard(row) {
  const say = notice();
  return anchored(row, card(null, [
    headBlock(row),
    whyBlock(row.why),
    el('div', { class: 'formrow' }, [
      field('Priority', prioritySelect(row, say)),
      field('Who is on it', assigneeControl(row, say)),
    ]),
    notesRow(row, say),
    bar([readyButton(row, say), ...moveButtons(row, say)]),
    commentsDrawer(row),
    say,
  ]));
}

function reviewCard(row) {
  const say = notice();
  const moves = (row.moves || []).filter((one) => one !== 'done' && one !== 'in_progress');
  return anchored(row, card(null, [
    headBlock(row, [statusPill(row), readyChip(row), dueChip(row)]),
    whyBlock(row.why),
    writtenRow(row, say, 'built', 'What was built', 'The whole answer the person who asked gets.'),
    writtenRow(row, say, 'how_to_test', 'How to test it', 'Optional — the steps to see it working.'),
    bar([
      acceptButton(row, say),
      askCheckButton(row, say),
      sendBackButton(row, say),
      ...moveButtons(row, say, moves),
    ]),
    commentsDrawer(row),
    say,
  ]));
}

function heldCard(row) {
  const say = notice();
  const moves = (row.moves || []).filter((one) => one !== row.resume_to);
  return anchored(row, card(null, [
    headBlock(row),
    whyBlock(row.why),
    row.decline_reason
      ? el('p', { class: 'req-reason', text: `On hold because: ${row.decline_reason}` })
      : null,
    bar([resumeButton(row, say), ...moveButtons(row, say, moves)]),
    commentsDrawer(row),
    say,
  ]));
}

function shutCard(row) {
  const say = row.status === 'done' ? notice() : null;
  return anchored(row, card(null, [
    headBlock(row, [statusPill(row), dueChip(row)]),
    whyBlock(row.why),
    row.decline_reason
      ? el('p', { class: 'req-reason', text: `Why not: ${row.decline_reason}` })
      : null,
    ...(row.status === 'done'
      ? [
        writtenRow(row, say, 'built', 'What was built', 'Editable — fixing a typo moves nothing.'),
        writtenRow(row, say, 'how_to_test', 'How to test it', 'Optional — the steps to see it working.'),
      ]
      : writtenBlock(row)),
    commentsDrawer(row),
    say,
  ].filter(Boolean)));
}

function emptyDo() {
  if (state.q || state.assignee) {
    return textAction('Clear the filters', () => {
      state.q = '';
      state.assignee = '';
      refresh();
    });
  }
  return textAction('File a request', () => openDrawer('File a request', [fileForm()]));
}

function emptySaid(base) {
  return state.q || state.assignee ? NO_MATCH : base;
}

function queueSection(title, id, note, rows, draw, empty, { open = false } = {}) {
  const one = section(title, note, { count: rows.length, id, open });
  one.body.append(
    rows.length === 0
      ? sayNothing(emptySaid(empty), emptyDo())
      : el('div', { class: 'section-body' }, rows.map(draw)),
    el('div', {
      class: 'grid-foot',
      text: rows.length === 0 ? '' : `Showing all ${rows.length} request${rows.length === 1 ? '' : 's'}`,
    }),
  );
  return one;
}

function openSectionOf() {
  const rows = inState('open');
  const one = queueSection('Open', 'preview-open', OPEN_NOTE, rows, openCard, NO_OPEN, { open: true });
  one.body.prepend(previewWas('The same queue as today, and still the only section open when you ' +
    'arrive. The promise that the person who asked is sent exactly what you type lives here now, ' +
    'once, in this section’s own line.'));
  return one.node;
}

function boardSection() {
  const rows = inState('in_progress');
  const one = queueSection('In progress', 'preview-in-progress', BOARD_NOTE, rows, boardCard, NO_BOARD);
  one.body.prepend(previewWas('Unchanged, except that it is shut on arrival and its count is on ' +
    'the header and in the On this page list.'));
  return one.node;
}

function reviewSection() {
  const rows = inState('review');
  const one = queueSection('Ready to check', 'preview-ready-to-check', REVIEW_NOTE, rows, reviewCard, NO_REVIEW);
  one.body.prepend(previewWas('Unchanged, except that it is shut on arrival.'));
  return one.node;
}

function heldSection() {
  const rows = inState('hold');
  const one = queueSection('On hold', 'preview-on-hold', HELD_NOTE, rows, heldCard, NO_HELD);
  one.body.prepend(previewWas('Unchanged, except that it is shut on arrival.'));
  return one.node;
}

function closedSection() {
  const rows = ALL.filter((row) => ['done', 'declined', 'withdrawn'].includes(row.status) && matches(row));
  const one = section('Closed', CLOSED_NOTE, { count: rows.length, id: 'preview-closed' });
  const cards = rows.map((row) => {
    const node = shutCard(row);
    node.setAttribute('data-status', row.status);
    return node;
  });
  const list = el('div', { class: 'section-body' }, cards);
  const foot = el('div', { class: 'grid-foot' });
  const none = sayNothing(NO_CLOSED, emptyDo());
  none.hidden = rows.length > 0;

  const paint = () => {
    let shown = 0;
    for (const node of cards) {
      const hit = state.closed === '' || node.getAttribute('data-status') === state.closed;
      node.hidden = !hit;
      if (hit) shown += 1;
    }
    foot.textContent = `Showing ${shown} of ${rows.length} closed request${rows.length === 1 ? '' : 's'}`;
    none.hidden = shown > 0;
  };

  const chips = CLOSED_FILTERS.map(([key, label]) => el('button', {
    class: 'chip-filter',
    type: 'button',
    'data-kind': key || 'any',
    'aria-pressed': state.closed === key ? 'true' : 'false',
    text: `${label}${key ? ` · ${rows.filter((row) => row.status === key).length}` : ''}`,
    on: {
      click: (event) => {
        state.closed = key;
        for (const chip of event.currentTarget.parentElement.children) {
          chip.setAttribute('aria-pressed', chip.getAttribute('data-kind') === (key || 'any') ? 'true' : 'false');
        }
        paint();
      },
    },
  }));

  one.body.append(
    previewWas('Replaces Done and Declined — two sections, each wrapping a shut foldout, and a ' +
      'third foldout for the ones taken back. One list now, with which one it is as a chip.'),
    el('div', { class: 'chipbar' }, chips),
    list,
    none,
    foot,
  );
  paint();
  return one.node;
}

function outcomeOf(form) {
  const what = form.what.value.trim();
  if (!what) return NEED_A_WHAT;
  const why = form.why.value.trim();
  if (!why) return NEED_A_WHY;
  const due = dueOn(form.due.value.trim());
  const dated = due ? ` It is marked ${due.text.replace(/^due /, 'due ')}.` : '';
  return `Files “${what}” under your name. It lands open, whoever files it, and you are DMed ` +
    `every time staff move it.${dated}`;
}

function fileForm() {
  const say = notice();
  const what = el('input', { class: 'input', type: 'text', placeholder: 'what you want built', maxlength: String(WHY_MAX) });
  const why = el('textarea', { class: 'input area', rows: '3', placeholder: 'why it is worth building', maxlength: String(WHY_MAX) });
  const due = el('input', { class: 'input', type: 'date' });
  const outcome = el('p', { class: 'section-note' });
  const form = { what, why, due };
  const repaint = () => {
    outcome.textContent = outcomeOf(form);
  };

  const file = button('File the request', () => {
    if (!what.value.trim()) {
      say.say(NEED_A_WHAT, 'warn');
      return;
    }
    if (!why.value.trim()) {
      say.say(NEED_A_WHY, 'warn');
      return;
    }
    wouldDo(say, `POST /api/requests — ${outcomeOf(form).replace(/\.$/, '')}`);
  }, { tone: 'warn', small: false });

  for (const box of [what, why, due]) box.addEventListener('input', repaint);
  due.addEventListener('change', repaint);
  repaint();

  return el('div', {}, [
    el('p', { class: 'section-note', text: FILE_NOTE }),
    el('div', { class: 'formrow' }, [
      field('What', what, 'One line. The detail goes in the why.'),
      field('Due date', due, 'Only when something actually depends on the date.'),
    ]),
    el('div', { class: 'formrow' }, [
      field('Why', why, 'What it fixes, or what it would let people do.'),
    ]),
    outcome,
    bar([file]),
    say,
  ]);
}

function toolbar() {
  const chips = ASSIGNEE_FILTERS.map(([key, label]) => el('button', {
    class: 'chip-filter',
    type: 'button',
    'data-kind': key || 'any',
    'aria-pressed': state.assignee === key ? 'true' : 'false',
    text: label,
    on: {
      click: () => {
        state.assignee = key;
        refresh();
      },
    },
  }));
  const say = notice();
  const waiting = ALL.filter((row) => row.status === 'open').length;
  const working = ALL.filter((row) => row.status === 'in_progress').length;
  return el('div', { class: 'card', 'data-span': 'full' }, [
    el('div', { class: 'card-head' }, [
      searchField({
        label: 'Search requests',
        placeholder: 'Search what, why, notes or who asked…',
        value: state.q,
        onQuery: (query) => {
          if (query === state.q) return;
          state.q = query;
          refresh();
        },
      }),
      el('div', { class: 'chipbar' }, chips),
      el('span', { class: 'topbar-gap' }),
      el('span', { class: 'table-count', text: `${waiting} open · ${working} in progress` }),
      button('Export CSV', () => wouldDo(say, 'GET /api/requests/export.csv — download every ' +
        'request, with what, why, who asked and where it got to'), { tone: 'quiet' }),
    ]),
    say,
  ]);
}

function keepTyping(typed) {
  if (typed === null) return;
  const box = document.querySelector('.searchfield .input.search');
  if (!box) return;
  box.value = typed;
  box.focus();
  box.setSelectionRange(typed.length, typed.length);
}

function channelPicker(value) {
  const node = el('select', { class: 'input' });
  node.append(el('option', { value: '', text: 'not set', selected: !value }));
  for (const channel of CHANNELS) {
    node.append(el('option', {
      value: channel.id,
      text: channelLabel(channel, CHANNELS),
      selected: String(value) === String(channel.id) || undefined,
    }));
  }
  return node;
}

function settingControl(spec, say) {
  const fire = (value) => wouldDo(say, `PUT /api/settings/${spec.key} — store ${JSON.stringify(value)}`);
  if (spec.type === 'bool') {
    const node = segment(
      [{ value: 'true', label: 'On' }, { value: 'false', label: 'Off' }],
      spec.value === true ? 'true' : 'false',
      { onChange: () => fire(node.readValue() === 'true') },
    );
    return node;
  }
  if (spec.type === 'enum') {
    const node = segment(
      (spec.choices || []).map((choice) => ({ value: choice, label: choice })),
      spec.value,
      { onChange: () => fire(node.readValue()) },
    );
    return node;
  }
  if (spec.type === 'channel') {
    const node = channelPicker(spec.value);
    node.addEventListener('change', () => fire(node.value || null));
    return node;
  }
  const node = el('input', { class: 'input', type: 'text', value: spec.value === null ? '' : String(spec.value) });
  node.addEventListener('change', () => fire(node.value));
  return node;
}

function requestForumCard(say) {
  return card('Request forum', [
    el('p', { text: FORUM_NOTE }),
    sayNothing('There is no request forum yet, so cards go to the channels below.'),
    bar([button('Make the forum', () => wouldDo(say, 'POST /api/requests/forum — make a forum ' +
      'under the Blackmail category with that category’s own permissions'), { tone: 'warn' })]),
  ]);
}

function settingsSection() {
  const say = notice();
  const one = section('Settings', SETTINGS_NOTE, { count: SETTING_SPECS.length, id: 'preview-settings' });
  one.body.append(
    previewWas('The same one settings surface, still shut on arrival.'),
    requestForumCard(say),
    el('div', { class: 'settings-grid' }, SETTING_SPECS.map((spec) => el('div', { class: 'setrow', 'data-key': spec.key }, [
      el('div', { class: 'setrow-head' }, [
        el('span', { class: 'setrow-label', text: spec.label, title: spec.help }),
        el('span', { class: 'setrow-key', text: spec.key }),
      ]),
      el('div', { class: 'setrow-control' }, [settingControl(spec, say)]),
    ]))),
    say,
  );
  return one.node;
}

function logsSection() {
  const one = section('Logs', LOGS_NOTE, { id: 'preview-logs' });
  const holder = el('div');
  const paint = () => {
    const rows = state.important ? LOG_ROWS.filter((row) => row.important) : LOG_ROWS;
    holder.replaceChildren(logsTable(
      rows,
      state.important
        ? 'Requests has logged nothing important. Filing a request and moving it along are ' +
          'routine; a decision is not. Switch to All to see the routine lines too.'
        : 'Requests has logged nothing at all yet.',
      state.important
        ? textAction('Show every line', () => {
          state.important = false;
          only.setValue('all');
          paint();
        })
        : null,
      { noun: 'line', total: rows.length },
    ));
  };
  const only = importantSwitch(state.important, (wanted) => {
    state.important = wanted;
    paint();
  });
  paint();
  one.body.append(
    previewWas('The shared logs block, unchanged — one per page, shut on arrival.'),
    el('div', { class: 'card' }, [
      el('div', { class: 'card-head' }, [only, el('span', { class: 'topbar-gap' })]),
      el('div', { class: 'card-body' }, [holder]),
    ]),
  );
  return one.node;
}

function pageHead() {
  const aside = document.getElementById('page-aside');
  if (!aside) return;
  aside.replaceChildren(button('File a request', () => {
    openDrawer('File a request', [fileForm()]);
  }, { tone: 'warn', small: false }));
}

async function load(me) {
  viewer = me || null;
  const active = document.activeElement;
  const typed = active && active.classList && active.classList.contains('search') ? active.value : null;

  pageHead();
  const banner = previewBanner({
    today: 9,
    preview: 7,
    note: 'This is the STAFF shape; a member sees the same cards, their own rows only.',
  });
  banner.setAttribute('data-span', 'full');
  document.getElementById('dash').replaceChildren(
    banner,
    toolbar(),
    openSectionOf(),
    boardSection(),
    reviewSection(),
    heldSection(),
    closedSection(),
    settingsSection(),
    logsSection(),
  );
  keepTyping(typed);
  measureWhy();
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(measureWhy);
}

refresh = start({ tab: 'requests', load });
