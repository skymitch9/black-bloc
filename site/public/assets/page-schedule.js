import { Outage, api, send } from './api.js';
import { start } from './app.js';
import { BAF, said } from './marathon-words.js';
import { changesOf, placed, refreshMs, secondsWords, signature } from './schedule-merge.js';
import { clockParts, clockTime, dayLabel, deviceZone, fillMoments, pickZone, viewerZone } from './timezone.js';
import {
  ago,
  badge,
  boldParts,
  button,
  card,
  chipBar,
  el,
  linkAction,
  listFilter,
  notice,
  sayNothing,
  sentenceFor,
  zoneSelect,
} from './ui.js';

const HASH = /^marathon-(\d+)$/;
const TICK_MS = 1000;
const FLASH_MS = 8000;
const BY_MARKS = 'marks';
const FILTER_FROM = 12;

const BACK = '← Events';
const PICKER_LABEL = 'Marathon';
const NO_MARATHONS = 'Black Bloc follows no marathon yet, so there is nothing to track. Add one on the Events page.';
const NO_SUCH = 'That marathon is not on the list any more. Pick another one above.';
const HEAD = '{marathon} — {day}';
const DRIFT_ON = 'On time';
const DRIFT_AHEAD = 'Running {minutes} min ahead';
const DRIFT_BEHIND = 'Running {minutes} min behind';
const DRIFT_OVER = 'Every run has started';
const DRIFT_TRACKER = 'Following the tracker';
const DRIFT_TRACKER_HELP = 'The tracker moves its own times, so there is no plan to be ahead of or behind until a run is seen starting.';
const DRIFT_HELP = 'The next run not yet started, against {source} for it.';
const SOURCE_LINE = 'times from {from}';
const READ_LINE = 'source read {ago}';
const NEXT_READ_LINE = 'next read {time}';
const ZONE_LINES = {
  device: 'Times shown in your time — {zone}',
  remembered: 'Times shown in your time — {zone}',
  picked: 'Times shown in {zone} time',
  server: 'Times shown in the server’s time — {zone}',
};
const ZONE_PICKER = 'Show times in';
const ZONE_DEVICE = 'My device’s time ({zone})';
const ZONE_DEVICE_UNKNOWN = 'My device’s time';
const KIND_EDITABLE = '{source} never moves its own times, so staff keep the clock here: every time below can be moved, and the bot’s posts follow.';
const KIND_KEPT = '{source} never moves its own times, so Black Bloc keeps the clock: a run seen starting on the stream re-times the runs after it. Times cannot be typed here yet — **Started now** and **Finished now** work, and the rest follow.';
const KIND_ARCHIVED = 'This marathon is archived, so this is its schedule as it ended. Nothing here can be changed.';
const UPDATED = 'Updated {ago} · re-reads every {seconds} seconds while this tab is showing';
const UPDATE_FAILED = 'Could not update just now — {why} The times below are as they stood at {time}. Trying again in {seconds} seconds.';
const UPDATE_OUTAGE = 'Black Bloc did not answer.';
const KIND_READ_ONLY = 'These times come from {source}, which moves them itself and is re-read every few minutes, so they cannot be changed here. **Started now** and **Finished now** still work.';
const DAY_CHIP = '{day} · {runs}';
const SHIFT_LABEL = 'Runs not yet started';
const SHIFT_STEPS = [[5, 'Behind 5'], [10, 'Behind 10'], [-5, 'Ahead 5'], [-10, 'Ahead 10']];
const SHIFT_FIELD = 'minutes';
const SHIFT_BEHIND = 'Behind';
const SHIFT_AHEAD = 'Ahead';
const SHIFT_EMPTY = 'Type how many minutes to move by, then press **Behind** or **Ahead**.';
const RESET = 'Back to the source’s times';
const UNDO = 'Undo last move';
const UNDO_HELP = 'Takes back: {what}';
const COLUMNS = ['Start', 'Game', 'Est.', 'Runner · host', ''];
const FROM_WORDS = {
  stream: 'seen on stream',
  started: 'started by staff',
  staff: 'set by staff',
  organisers: 'organisers’ sheet',
  source: 'source sheet + setup',
  follows: 'follows the run before',
  held: 'kept from an earlier read',
  tracker: 'from the tracker',
};
const PLAN_WORDS = { organisers: 'sheet said {time}', source: 'sheet said {time}', tracker: 'tracker said {time}' };
const STATE_WORDS = { upcoming: 'upcoming', live: 'live', done: 'done', dropped: 'skipped' };
const STATE_TONE = { upcoming: null, live: 'ok', done: null, dropped: 'warn' };
const OFF_SCHEDULE = 'off the schedule';
const ESTIMATE_STAFF = 'set by staff';
const HOST = 'host';
const WATCH = 'Watch on Twitch ↗';
const YOUTUBE = 'YouTube';
const YOUTUBE_HELP = '{name} on YouTube · {from}';
const LINK_HELP = '{part} · {site} · {from}';
const SITE_WORDS = { twitch: 'Twitch', youtube: 'YouTube' };
const LINK_FROM = { member: 'their go-live link', schedule: 'from the schedule', hosts: 'host list' };
const YOUTUBE_FROM = { member: 'their YouTube link', schedule: 'from the schedule' };
const CHANNEL_URL = /^https:\/\/(?:www\.)?(?:twitch\.tv|youtube\.com)\/[A-Za-z0-9_@.\/-]+$/;
const NOBODY = 'nobody named';
const START_NOW = 'Started now';
const FINISH_NOW = 'Finished now';
const START_AGAIN = 'Mark live again';
const FINISH_UNRUN = 'Mark done';
const MORE = 'More…';
const EDIT = 'Edit…';
const CLOSE = 'Close';
const RESTORE = 'Bring it back';
const SKIP = 'Skip this run';
const SET_START = 'Set start…';
const SET_START_FIELD = 'New start';
const SET_START_HELP = 'Read in {zone} time — type it like 12:40 PM (13:40 works too). Later runs keep their gaps.';
const ESTIMATE = 'Change estimate…';
const ESTIMATE_FIELD = 'Estimate';
const ESTIMATE_HELP = 'As 1:20, or minutes.';
const SAVE = 'Save';
const FILTER_LABEL = 'Filter the runs';
const FILTER_PLACEHOLDER = 'game, runner or host';
const NO_HIT = 'Nothing on this day matches that.';
const NO_RUNS = 'No runs on this schedule yet — it may not be published.';
const POSTS_TITLE = 'What the bot posts next';
const POSTS_NOTE = 'Each heads-up still to go out for a {baf} run or host block, worked out from the start times above — when a run moves, its post moves.';
const POSTS_NONE = 'No {baf} run or host block is left on this day.';
const POST_NOW = 'now';
const POST_PASSED = 'its time has passed';
const POST_DUE = 'due now';
const POST_ROLE = 'pings the Marathon role';
const MOVES_TITLE = 'Moves today';
const MOVES_NONE = 'No staff move here yet.';
const CHANGES_TITLE = 'What changed';
const CHANGES_NONE = 'Nothing has changed a time or a state on this marathon yet.';
const MOVE_UNDONE = 'undone';
const WORKING = 'Working…';

const shown = { id: null, day: null, open: null };
let sheet = null;
let marathons = [];
let say = notice();
let viewer = { zone: 'UTC', picked: false, from: 'server' };
let lastSaid = { text: '', tone: null };
let root = null;
let timer = null;
let refresh = () => {};
let status = null;
let saidNode = null;
let parts = new Map();
let rowParts = new Map();
let sheetPart = null;
let readAt = 0;
let nextAt = 0;
let failed = null;
let reading = false;

function wantedId() {
  const found = HASH.exec(String(location.hash || '').replace(/^#/, '').trim());
  return found ? found[1] : null;
}

function length(seconds) {
  const minutes = Math.round(Number(seconds || 0) / 60);
  return `${Math.floor(minutes / 60)}:${String(minutes % 60).padStart(2, '0')}`;
}

function clock(iso) {
  return clockTime(iso, viewer.zone);
}

function filled(text) {
  return fillMoments(text, viewer.zone);
}

function tell(text, tone = null) {
  lastSaid = { text: text || '', tone };
  if (say.parentNode) say.parentNode.hidden = false;
  say.say(filled(text), tone);
}

function stamp(iso) {
  return `${dayLabel(iso, viewer.zone)} ${clock(iso)}`;
}

function dayNow() {
  return sheet.days.find((one) => one.key === shown.day) || sheet.days.find((one) => one.key === sheet.today) || sheet.days[0] || null;
}

function byMarks() {
  return sheet.moves_by === BY_MARKS;
}

async function mark(runId, move) {
  tell(WORKING);
  try {
    const found = await send(`/api/marathons/${shown.id}/runs/${runId}/${move}`, 'POST', {});
    shown.open = null;
    await read();
    tell(found.message || '', 'ok');
    return true;
  } catch (error) {
    const refused = sentenceFor(error);
    tell(refused.text, refused.tone);
    return false;
  }
}

async function act(path, body = {}) {
  tell(WORKING);
  try {
    const found = await send(`/api/marathons/${shown.id}/schedule/${path}`, 'POST', body);
    take(found);
    shown.open = null;
    tell(found.message || '', 'ok');
    paint();
    return true;
  } catch (error) {
    const refused = sentenceFor(error);
    tell(refused.text, refused.tone);
    return false;
  }
}

function startRun(row) {
  return byMarks() ? mark(row.id, 'live') : act(`runs/${row.id}/start`);
}

function finishRun(row) {
  return byMarks() ? mark(row.id, 'done') : act(`runs/${row.id}/finish`);
}

function take(found) {
  const flashes = changesOf(sheet, found);
  sheet = found;
  readAt = Date.now();
  nextAt = readAt + refreshMs(sheet.refresh_seconds);
  failed = null;
  return flashes;
}

async function read() {
  const flashes = take(await api(`/api/marathons/${shown.id}/schedule`));
  paint();
  flash(flashes);
}

function flash(flashes) {
  for (const [id, kind] of Object.entries(flashes)) {
    const node = document.getElementById(`run-${id}`);
    if (!node) continue;
    node.setAttribute('data-flash', kind);
    setTimeout(() => node.removeAttribute('data-flash'), FLASH_MS);
  }
}

function driftNode(day) {
  const minutes = day.drift_minutes;
  const waits = sheet.kind === 'tracker' && Number(day.upcoming) > 0;
  let text = waits ? DRIFT_TRACKER : DRIFT_OVER;
  let tone = null;
  if (minutes === 0) [text, tone] = [DRIFT_ON, 'ok'];
  else if (minutes > 0) [text, tone] = [said(DRIFT_BEHIND, { minutes }), 'warn'];
  else if (minutes < 0) [text, tone] = [said(DRIFT_AHEAD, { minutes: Math.abs(minutes) }), 'ok'];
  return el('span', {
    class: 'rs-drift',
    'data-tone': tone || undefined,
    title: minutes === null && waits ? DRIFT_TRACKER_HELP : said(DRIFT_HELP, { source: sheet.times_from_word }),
    text,
  });
}

function dot(parts) {
  return parts.filter(Boolean).flatMap((one, at) => (at ? [el('span', { class: 'mx-dot', text: ' · ' }), one] : [one]));
}

function zoneLine() {
  const device = deviceZone();
  const picker = zoneSelect(viewer.picked ? viewer.zone : '', { blank: device ? said(ZONE_DEVICE, { zone: device }) : ZONE_DEVICE_UNKNOWN });
  picker.classList.add('rs-zone-pick');
  picker.setAttribute('aria-label', ZONE_PICKER);
  picker.addEventListener('change', () => {
    pickZone(picker.value || null);
    viewer = viewerZone(sheet.timezone);
    paint();
  });
  return el('p', { class: 'field-help rs-zone' }, [
    el('span', { text: said(ZONE_LINES[viewer.from] || ZONE_LINES.device, { zone: viewer.zone }) }),
    el('label', { class: 'rs-zone-change' }, [el('span', { class: 'rs-label', text: ZONE_PICKER }), picker]),
  ]);
}

function headCard(day) {
  const { marathon } = sheet;
  const source = marathon.schedule_page
    ? el('a', { class: 'say-nothing-do', href: marathon.schedule_page, rel: 'noreferrer', target: '_blank', text: `${marathon.source_word} ↗` })
    : el('span', { text: marathon.source_word });
  const read = marathon.last_fetched_at ? ago(marathon.last_fetched_at) : null;
  const next = marathon.next_read_at && new Date(marathon.next_read_at).getTime() > Date.now() ? marathon.next_read_at : null;
  const kind = marathon.archived ? KIND_ARCHIVED : sheet.editable ? KIND_EDITABLE : sheet.kind === 'tracker' ? KIND_READ_ONLY : KIND_KEPT;
  return card(null, [
    el('div', { class: 'rs-head' }, [
      el('h2', { class: 'rs-title', text: said(HEAD, { marathon: marathon.name, day: day ? dayLabel(day.starts_at, viewer.zone) : '' }) }),
      day ? driftNode(day) : null,
    ]),
    el('p', { class: 'field-help rs-source' }, dot([
      source,
      el('span', { text: said(SOURCE_LINE, { from: sheet.times_from_word }) }),
      read ? el('span', { class: 'rs-read', title: stamp(marathon.last_fetched_at), text: said(READ_LINE, { ago: read.text }) }) : null,
      next ? el('span', { title: stamp(next), text: said(NEXT_READ_LINE, { time: clock(next) }) }) : null,
      channel(marathon.watch_url) ? el('a', { class: 'say-nothing-do', href: marathon.watch_url, target: '_blank', rel: 'noopener', title: `twitch.tv/${marathon.channel_login}`, text: WATCH }) : null,
    ])),
    el('p', { class: 'field-help' }, boldParts(said(kind, { source: marathon.source_word }))),
    zoneLine(),
  ]);
}

function dayStrip() {
  if (sheet.days.length < 2) return null;
  const choices = sheet.days.map((one) => [one.key, said(DAY_CHIP, { day: dayLabel(one.starts_at, viewer.zone), runs: one.runs })]);
  return chipBar(choices, shown.day, (key) => {
    shown.day = key;
    shown.open = null;
    paint();
  }, { className: 'rs-days' });
}

function shiftBar(day) {
  if (!sheet.editable) return null;
  const shift = (minutes) => act('shift', { day: day.key, minutes });
  const typed = el('input', { class: 'input mono rs-number', type: 'text', inputmode: 'numeric', placeholder: SHIFT_FIELD, 'aria-label': SHIFT_FIELD });
  const byTyped = (sign) => {
    const minutes = Number(typed.value.trim());
    if (!typed.value.trim()) tell(SHIFT_EMPTY, 'warn');
    else shift(Number.isFinite(minutes) ? sign * Math.abs(minutes) : typed.value.trim());
  };
  const moves = day.can_shift ? [
    el('span', { class: 'rs-label', text: SHIFT_LABEL }),
    ...SHIFT_STEPS.map(([minutes, label]) => button(label, () => shift(minutes), { tone: 'quiet' })),
    el('span', { class: 'rs-typed' }, [
      typed,
      button(SHIFT_BEHIND, () => byTyped(1), { tone: 'quiet' }),
      button(SHIFT_AHEAD, () => byTyped(-1), { tone: 'quiet' }),
    ]),
  ] : [];
  const reset = day.can_reset ? button(RESET, () => act('reset', { day: day.key }), { tone: 'warn' }) : null;
  if (!moves.length && !reset) return null;
  return el('div', { class: 'bar rs-shift' }, [...moves, reset ? el('span', { class: 'rs-gap' }) : null, reset]);
}

function saidBar() {
  const undo = sheet.undo.available ? button(UNDO, () => act('undo'), { tone: 'quiet' }) : null;
  if (undo) undo.title = said(UNDO_HELP, { what: filled(sheet.undo.text).replaceAll('**', '') });
  if (say.said !== filled(lastSaid.text)) say.say(filled(lastSaid.text), lastSaid.tone);
  const wanted = signature(sheet.undo.available, sheet.undo.text, viewer.zone);
  if (!saidNode) saidNode = el('div', { class: 'rs-said' }, [say]);
  if (saidNode.dataset.sig !== wanted) {
    saidNode.dataset.sig = wanted;
    saidNode.replaceChildren(...[say, undo].filter(Boolean));
  }
  saidNode.hidden = !lastSaid.text && !undo;
  return saidNode;
}

function channel(url) {
  return CHANNEL_URL.test(String(url || '')) ? url : null;
}

function personChip(person) {
  const name = person.baf ? `${person.name} ✦${BAF}` : person.name;
  const twitch = channel(person.twitch_url);
  const youtube = channel(person.youtube_url);
  const href = twitch || youtube;
  const who = person.member_name ? `${person.part} · ${person.member_name}` : person.part;
  const from = twitch ? LINK_FROM[person.twitch_from] : YOUTUBE_FROM[person.youtube_from];
  const title = href ? said(LINK_HELP, { part: who, site: SITE_WORDS[twitch ? 'twitch' : 'youtube'], from: from || '' }) : who;
  const main = el(href ? 'a' : 'span', {
    class: href ? 'mx-chip rs-link' : 'mx-chip',
    'data-baf': person.baf ? 'true' : undefined,
    'data-quiet': person.part === 'runner' ? undefined : 'true',
    href: href || undefined,
    target: href ? '_blank' : undefined,
    rel: href ? 'noopener' : undefined,
    title,
    text: person.part === 'host' ? `${HOST} ${name}` : name,
  });
  if (!twitch || !youtube) return main;
  const also = said(YOUTUBE_HELP, { name: person.name, from: YOUTUBE_FROM[person.youtube_from] || '' });
  return el('span', { class: 'rs-person' }, [
    main,
    el('a', { class: 'mx-chip rs-link rs-also', href: youtube, target: '_blank', rel: 'noopener', title: also, 'aria-label': also, text: YOUTUBE }),
  ]);
}

function peopleCell(row) {
  const people = [...row.people.filter((one) => one.part === 'runner'), ...row.people.filter((one) => one.part !== 'runner')];
  return el('div', { class: 'rs-who mx-chips' }, people.length ? people.map(personChip) : [el('span', { class: 'cell-quiet', text: NOBODY })]);
}

function clockNode(iso) {
  const parts = clockParts(iso, viewer.zone);
  if (!parts) return el('span', { class: 'rs-clock', text: '—' });
  return el('span', { class: 'rs-clock' }, [parts.time, el('span', { class: 'rs-period', text: ` ${parts.period}` })]);
}

function clockCell(row) {
  if (!row.start_at) return el('div', { class: 'rs-when' }, [el('span', { class: 'rs-clock', text: '—' })]);
  const off = row.off_plan_minutes !== 0;
  return el('div', { class: 'rs-when' }, [
    clockNode(row.start_at),
    el('span', { class: 'rs-from', 'data-from': row.from, text: FROM_WORDS[row.from] || row.from }),
    off ? el('span', { class: 'rs-plan', text: said(PLAN_WORDS[row.plan_from] || '{time}', { time: clock(row.plan_at) }) }) : null,
  ]);
}

function typedField(label, value, help, onSave) {
  const input = el('input', { class: 'input mono rs-typed-input', type: 'text', value, 'aria-label': label });
  const save = () => onSave(input.value);
  input.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') save();
  });
  return el('div', { class: 'rs-field' }, [
    el('span', { class: 'rs-label', text: label }),
    input,
    button(SAVE, save),
    el('span', { class: 'field-help', text: help }),
  ]);
}

function primary(row) {
  if (row.state === 'live' && row.can.finish) return 'finish';
  if (row.state === 'upcoming' && row.can.start && (row.next_up || !sheet.editable)) return 'start';
  return null;
}

function folded(row) {
  const first = primary(row);
  const start = row.can.start && first !== 'start';
  const finish = row.can.finish && first !== 'finish';
  return { start, finish, any: start || finish || row.can.set_start || row.can.estimate || row.can.skip };
}

function editPanel(row) {
  const base = `runs/${row.id}`;
  const more = folded(row);
  return el('div', { class: 'rs-edit' }, [
    row.can.set_start ? typedField(SET_START_FIELD, clock(row.start_at), said(SET_START_HELP, { zone: viewer.zone }), (time) => act(`${base}/set-start`, { time, zone: viewer.zone })) : null,
    row.can.estimate ? typedField(ESTIMATE_FIELD, length(row.estimate_seconds), ESTIMATE_HELP, (estimate) => act(`${base}/estimate`, { estimate })) : null,
    el('div', { class: 'bar' }, [
      more.start ? button(row.state === 'done' ? START_AGAIN : START_NOW, () => startRun(row), { tone: 'quiet' }) : null,
      more.finish ? button(row.state === 'upcoming' ? FINISH_UNRUN : FINISH_NOW, () => finishRun(row), { tone: 'quiet' }) : null,
      row.can.skip ? button(SKIP, () => act(`${base}/skip`), { tone: 'warn' }) : null,
      button(CLOSE, () => {
        shown.open = null;
        paint();
      }, { tone: 'quiet' }),
    ]),
  ]);
}

function rowMoves(row) {
  const first = primary(row);
  const open = shown.open === row.id;
  const label = row.can.set_start ? EDIT : row.can.estimate ? ESTIMATE : MORE;
  return [
    first === 'finish' ? button(FINISH_NOW, () => finishRun(row)) : null,
    first === 'start' ? button(START_NOW, () => startRun(row), { tone: row.next_up ? null : 'quiet' }) : null,
    row.can.restore ? button(RESTORE, () => act(`runs/${row.id}/restore`), { tone: 'quiet' }) : null,
    folded(row).any && !open ? button(label, () => {
      shown.open = row.id;
      paint();
    }, { tone: 'quiet' }) : null,
  ];
}

function sheetRow(row) {
  const word = row.state === 'dropped' && !sheet.editable ? OFF_SCHEDULE : STATE_WORDS[row.state] || row.state_word;
  return el('div', { class: 'rs-row', 'data-state': row.state, 'data-baf': row.ours ? 'true' : undefined, id: `run-${row.id}` }, [
    clockCell(row),
    el('div', { class: 'rs-game' }, [
      el('strong', { text: row.game }),
      row.category ? el('span', { class: 'cell-quiet', text: row.category }) : null,
    ]),
    el('div', { class: 'rs-est mono' }, [
      el('span', { text: length(row.estimate_seconds) }),
      row.estimate_from === 'staff' ? el('span', { class: 'rs-from', 'data-from': 'staff', text: ESTIMATE_STAFF }) : null,
    ]),
    peopleCell(row),
    el('div', { class: 'rs-acts' }, [badge(word, STATE_TONE[row.state] || null), ...rowMoves(row)]),
    shown.open === row.id ? editPanel(row) : null,
  ]);
}

function rowText(row) {
  return [row.game, row.category, ...row.people.flatMap((one) => [one.name, one.login, one.member_name])].filter(Boolean).join(' ');
}

function rowNode(row) {
  const open = shown.open === row.id;
  const wanted = signature(row, viewer.zone, open, sheet.editable, sheet.moves_by);
  const had = rowParts.get(row.id);
  if (had && (had.sig === wanted || (open && had.open && had.node.querySelector('input')))) return had.node;
  const node = sheetRow(row);
  rowParts.set(row.id, { sig: wanted, node, open });
  return node;
}

function settle(parent, wanted) {
  const { steps, gone } = placed([...parent.children], wanted);
  for (const one of gone) one.remove();
  for (const one of steps) parent.insertBefore(one.node, one.before);
}

function sheetCard(day) {
  const rows = sheet.rows.filter((one) => one.day === day.key);
  if (!rows.length) {
    sheetPart = null;
    return part('sheet', signature('empty', day.key), () => card(null, [sayNothing(NO_RUNS)]));
  }
  const searchable = rows.length >= FILTER_FROM;
  const wanted = signature(shown.id, day.key, searchable);
  if (!sheetPart || sheetPart.sig !== wanted) {
    const head = el('div', { class: 'rs-row rs-cols' }, COLUMNS.map((text) => el('div', { text })));
    const list = el('div', { class: 'rs-sheet' }, [head]);
    const items = [];
    const filter = searchable ? listFilter({ items, value: (one) => one.row, text: rowText, label: FILTER_LABEL, placeholder: FILTER_PLACEHOLDER, empty: NO_HIT }) : null;
    const node = filter
      ? card(null, [el('div', { class: 'table-tools rs-tools' }, [filter.search]), filter.none, list], { flush: true })
      : card(null, [list], { flush: true });
    sheetPart = { sig: wanted, node, list, head, items, filter };
  }
  const nodes = rows.map((row) => ({ row, node: rowNode(row) }));
  sheetPart.items.splice(0, sheetPart.items.length, ...nodes);
  settle(sheetPart.list, [sheetPart.head, ...nodes.map((one) => one.node)]);
  if (sheetPart.filter) sheetPart.filter.apply();
  for (const id of [...rowParts.keys()]) {
    if (!sheet.rows.some((one) => one.id === id)) rowParts.delete(id);
  }
  return sheetPart.node;
}

function lineList(lines, empty) {
  if (!lines.length) return sayNothing(empty);
  return el('ul', { class: 'rs-lines' }, lines.map(([time, title, body, marks]) => el('li', { 'data-quiet': marks.length ? 'true' : undefined }, [
    el('span', { class: 'mono rs-line-time', title: title || undefined, text: time }),
    el('span', { class: 'rs-line-text' }, [...body, ...marks.map((one) => badge(one))]),
  ])));
}

function postTime(post, day) {
  if (!post.at) return POST_NOW;
  return dayLabel(post.at, viewer.zone) === dayLabel(day.starts_at, viewer.zone) ? clock(post.at) : stamp(post.at);
}

function postsCard(day) {
  const posts = sheet.next_posts.filter((one) => one.day === day.key);
  const lines = posts.map((one) => [
    postTime(one, day),
    one.at ? stamp(one.at) : '',
    boldParts(one.text),
    [one.role ? POST_ROLE : null, one.passed ? (byMarks() ? POST_DUE : POST_PASSED) : null].filter(Boolean),
  ]);
  return card(POSTS_TITLE, [
    el('p', { class: 'field-help', text: said(POSTS_NOTE, { baf: BAF }) }),
    lineList(lines, said(POSTS_NONE, { baf: BAF })),
  ]);
}

function movesCard() {
  const lines = sheet.moves.map((one) => {
    const who = one.by_name || one.by_id;
    return [clock(one.at), stamp(one.at), [who ? el('strong', { text: `${who}: ` }) : null, ...boldParts(filled(one.text))].filter(Boolean), one.undone ? [MOVE_UNDONE] : []];
  });
  return card(byMarks() ? CHANGES_TITLE : MOVES_TITLE, [lineList(lines, byMarks() ? CHANGES_NONE : MOVES_NONE)], { count: sheet.moves.length || null });
}

function typing(node) {
  const active = document.activeElement;
  return Boolean(node && active && node.contains(active) && active.matches('input, select, textarea'));
}

function part(key, wanted, build) {
  const had = parts.get(key);
  if (had && (had.sig === wanted || typing(had.node))) return had.node;
  const node = build();
  parts.set(key, { sig: wanted, node });
  return node;
}

function statusLine() {
  if (!status) status = el('p', { class: 'field-help rs-status', role: 'status' });
  const seconds = Math.round(refreshMs(sheet.refresh_seconds) / 1000);
  if (failed) {
    status.setAttribute('data-tone', 'warn');
    status.textContent = said(UPDATE_FAILED, { why: failed, time: clock(new Date(readAt).toISOString()), seconds: Math.max(1, Math.ceil((nextAt - Date.now()) / 1000)) });
  } else {
    status.removeAttribute('data-tone');
    status.textContent = said(UPDATED, { ago: secondsWords(Date.now() - readAt), seconds });
  }
  const read = root ? root.querySelector('.rs-read') : null;
  if (read && sheet.marathon.last_fetched_at) read.textContent = said(READ_LINE, { ago: ago(sheet.marathon.last_fetched_at).text });
  return status;
}

function paint() {
  const day = dayNow();
  if (day) shown.day = day.key;
  const zone = signature(viewer.zone, viewer.from, viewer.picked);
  const nextRead = Boolean(sheet.marathon.next_read_at) && new Date(sheet.marathon.next_read_at).getTime() > Date.now();
  const posts = day ? sheet.next_posts.filter((one) => one.day === day.key) : [];
  settle(root, [
    part('head', signature(sheet.marathon, day, sheet.kind, sheet.editable, sheet.times_from_word, zone, nextRead), () => headCard(day)),
    statusLine(),
    part('days', signature(sheet.days.map((one) => [one.key, one.starts_at, one.runs]), shown.day, zone), () => dayStrip()),
    day ? part('shift', signature(sheet.editable, day.key, day.can_shift, day.can_reset), () => shiftBar(day)) : null,
    saidBar(),
    day ? sheetCard(day) : part('sheet', signature('none'), () => card(null, [sayNothing(NO_RUNS)])),
    day ? part('two', signature(posts, sheet.moves, zone, sheet.moves_by, day.starts_at), () => el('div', { class: 'rs-two' }, [postsCard(day), movesCard()])) : null,
  ].filter(Boolean));
}

function aside() {
  const picker = el('select', { class: 'input rs-picker', 'aria-label': PICKER_LABEL });
  for (const one of marathons) {
    picker.append(el('option', { value: String(one.id), text: `${one.name} · ${one.source_word}`, selected: String(one.id) === String(shown.id) ? true : undefined }));
  }
  picker.addEventListener('change', () => {
    location.hash = `#marathon-${picker.value}`;
  });
  document.getElementById('page-aside').replaceChildren(
    linkAction(BACK, shown.id ? `/events.html#marathon-${shown.id}` : '/events.html'),
    marathons.length ? picker : '',
  );
}

async function quietRefresh() {
  if (reading || !sheet || !shown.id || !root || !root.isConnected) return;
  reading = true;
  try {
    await read();
  } catch (error) {
    failed = error instanceof Outage ? UPDATE_OUTAGE : String(error.message || UPDATE_OUTAGE);
    nextAt = Date.now() + refreshMs(sheet.refresh_seconds);
    statusLine();
  } finally {
    reading = false;
  }
}

function tick() {
  if (!sheet || !root || !root.isConnected || document.hidden) return;
  if (Date.now() >= nextAt) quietRefresh();
  else statusLine();
}

function forget() {
  parts = new Map();
  rowParts = new Map();
  sheetPart = null;
  saidNode = null;
  status = null;
  failed = null;
  sheet = null;
}

async function load() {
  marathons = (await api('/api/marathons')).marathons || [];
  const wanted = wantedId();
  const first = marathons.find((one) => one.phase === 'live') || marathons[0] || null;
  const id = wanted || (first ? String(first.id) : null);
  if (String(id) !== String(shown.id)) Object.assign(shown, { day: null, open: null });
  shown.id = id;
  say = notice();
  lastSaid = { text: '', tone: null };
  forget();
  root = el('div', { class: 'rs' });
  document.getElementById('dash').replaceChildren(root);
  aside();
  if (!id) {
    root.replaceChildren(sayNothing(NO_MARATHONS));
    return;
  }
  let found = null;
  try {
    found = await api(`/api/marathons/${id}/schedule`);
  } catch (error) {
    if (error.status !== 404) throw error;
    root.replaceChildren(sayNothing(NO_SUCH));
    return;
  }
  take(found);
  viewer = viewerZone(sheet.timezone);
  paint();
  if (timer === null) {
    timer = setInterval(tick, TICK_MS);
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) quietRefresh();
    });
  }
}

window.addEventListener('hashchange', () => refresh());

refresh = start({
  tab: 'events',
  load,
});
