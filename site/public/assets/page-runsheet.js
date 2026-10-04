import { api, send } from './api.js';
import { start } from './app.js';
import { BAF, said, slotTime } from './marathon-words.js';
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
} from './ui.js';

const HASH = /^marathon-(\d+)$/;
const REFRESH_MS = 60000;
const FILTER_FROM = 12;

const BACK = '← Events';
const PICKER_LABEL = 'Marathon';
const NO_MARATHONS = 'Black Bloc follows no marathon yet, so there is no run sheet to show. Add one on the Events page.';
const NO_SUCH = 'That marathon is not on the list any more. Pick another one above.';
const HEAD = '{marathon} — {day}';
const DRIFT_ON = 'On time';
const DRIFT_AHEAD = 'Running {minutes} min ahead';
const DRIFT_BEHIND = 'Running {minutes} min behind';
const DRIFT_OVER = 'Every run has started';
const DRIFT_HELP = 'The next run not yet started, against {source} for it.';
const SOURCE_LINE = 'times from {from}';
const READ_LINE = 'source read {ago}';
const ZONE_LINE = 'shown in {zone} time';
const KIND_EDITABLE = '{source} never moves its own times, so staff keep this sheet’s clock: every time below can be moved here, and the bot’s posts follow.';
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
const EDIT = 'Edit…';
const CLOSE = 'Close';
const RESTORE = 'Bring it back';
const SKIP = 'Skip this run';
const SET_START = 'Set start…';
const SET_START_FIELD = 'New start';
const SET_START_HELP = 'Later runs keep their gaps.';
const ESTIMATE = 'Change estimate…';
const ESTIMATE_FIELD = 'Estimate';
const ESTIMATE_HELP = 'As 1:20, or minutes.';
const SAVE = 'Save';
const FILTER_LABEL = 'Filter the sheet';
const FILTER_PLACEHOLDER = 'game, runner or host';
const NO_HIT = 'Nothing on this day matches that.';
const NO_RUNS = 'No runs on this schedule yet — it may not be published.';
const POSTS_TITLE = 'What the bot posts next';
const POSTS_NOTE = 'The {minutes}-minute heads-up for each {baf} run and host block, worked out from the start times above — move a run and its post moves.';
const POSTS_NONE = 'No {baf} run or host block is left on this day.';
const POST_NOW = 'now';
const POST_PASSED = 'its time has passed';
const MOVES_TITLE = 'Moves today';
const MOVES_NONE = 'No staff move on this sheet yet.';
const MOVE_UNDONE = 'undone';
const WORKING = 'Working…';

const shown = { id: null, day: null, open: null };
let sheet = null;
let marathons = [];
let say = notice();
let root = null;
let timer = null;
let refresh = () => {};

function wantedId() {
  const found = HASH.exec(String(location.hash || '').replace(/^#/, '').trim());
  return found ? found[1] : null;
}

function length(seconds) {
  const minutes = Math.round(Number(seconds || 0) / 60);
  return `${Math.floor(minutes / 60)}:${String(minutes % 60).padStart(2, '0')}`;
}

function clock(iso) {
  return slotTime(iso, sheet.timezone);
}

function dayNow() {
  return sheet.days.find((one) => one.key === shown.day) || sheet.days.find((one) => one.key === sheet.today) || sheet.days[0] || null;
}

async function act(path, body = {}) {
  say.parentNode.hidden = false;
  say.say(WORKING);
  try {
    const found = await send(`/api/marathons/${shown.id}/runsheet/${path}`, 'POST', body);
    sheet = found;
    shown.open = null;
    say.say(found.message || '', 'ok');
    paint();
    return true;
  } catch (error) {
    const refused = sentenceFor(error);
    say.parentNode.hidden = false;
    say.say(refused.text, refused.tone);
    return false;
  }
}

function driftNode(day) {
  const minutes = day.drift_minutes;
  let text = DRIFT_OVER;
  let tone = null;
  if (minutes === 0) [text, tone] = [DRIFT_ON, 'ok'];
  else if (minutes > 0) [text, tone] = [said(DRIFT_BEHIND, { minutes }), 'warn'];
  else if (minutes < 0) [text, tone] = [said(DRIFT_AHEAD, { minutes: Math.abs(minutes) }), 'ok'];
  return el('span', {
    class: 'rs-drift',
    'data-tone': tone || undefined,
    title: said(DRIFT_HELP, { source: sheet.times_from_word }),
    text,
  });
}

function dot(parts) {
  return parts.filter(Boolean).flatMap((one, at) => (at ? [el('span', { class: 'mx-dot', text: ' · ' }), one] : [one]));
}

function headCard(day) {
  const { marathon } = sheet;
  const source = marathon.schedule_page
    ? el('a', { class: 'say-nothing-do', href: marathon.schedule_page, rel: 'noreferrer', target: '_blank', text: `${marathon.source_word} ↗` })
    : el('span', { text: marathon.source_word });
  const read = marathon.last_fetched_at ? ago(marathon.last_fetched_at) : null;
  return card(null, [
    el('div', { class: 'rs-head' }, [
      el('h2', { class: 'rs-title', text: said(HEAD, { marathon: marathon.name, day: day ? day.label : '' }) }),
      day ? driftNode(day) : null,
    ]),
    el('p', { class: 'field-help rs-source' }, dot([
      source,
      el('span', { text: said(SOURCE_LINE, { from: sheet.times_from_word }) }),
      read ? el('span', { title: read.title, text: said(READ_LINE, { ago: read.text }) }) : null,
      el('span', { text: said(ZONE_LINE, { zone: sheet.timezone }) }),
      channel(marathon.watch_url) ? el('a', { class: 'say-nothing-do', href: marathon.watch_url, target: '_blank', rel: 'noopener', title: `twitch.tv/${marathon.channel_login}`, text: WATCH }) : null,
    ])),
    el('p', { class: 'field-help' }, boldParts(said(sheet.editable ? KIND_EDITABLE : KIND_READ_ONLY, { source: marathon.source_word }))),
  ]);
}

function dayStrip() {
  if (sheet.days.length < 2) return null;
  const choices = sheet.days.map((one) => [one.key, said(DAY_CHIP, { day: one.label, runs: one.runs })]);
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
    if (!typed.value.trim()) {
      say.parentNode.hidden = false;
      say.say(SHIFT_EMPTY, 'warn');
    }
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
  if (undo) undo.title = said(UNDO_HELP, { what: String(sheet.undo.text || '').replaceAll('**', '') });
  return el('div', { class: 'rs-said', hidden: !say.said && !undo ? true : undefined }, [say, undo]);
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

function clockCell(row) {
  if (!row.start_at) return el('div', { class: 'rs-when' }, [el('span', { class: 'rs-clock', text: '—' })]);
  const off = row.off_plan_minutes !== 0;
  return el('div', { class: 'rs-when' }, [
    el('span', { class: 'rs-clock', text: clock(row.start_at) }),
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

function editPanel(row) {
  const base = `runs/${row.id}`;
  return el('div', { class: 'rs-edit' }, [
    row.can.set_start ? typedField(SET_START_FIELD, clock(row.start_at), SET_START_HELP, (time) => act(`${base}/set-start`, { time })) : null,
    row.can.estimate ? typedField(ESTIMATE_FIELD, length(row.estimate_seconds), ESTIMATE_HELP, (estimate) => act(`${base}/estimate`, { estimate })) : null,
    el('div', { class: 'bar' }, [
      row.can.start && !row.next_up ? button(START_NOW, () => act(`${base}/start`), { tone: 'quiet' }) : null,
      row.can.skip ? button(SKIP, () => act(`${base}/skip`), { tone: 'warn' }) : null,
      button(CLOSE, () => {
        shown.open = null;
        paint();
      }, { tone: 'quiet' }),
    ]),
  ]);
}

function rowMoves(row) {
  const base = `runs/${row.id}`;
  const editable = row.can.set_start || row.can.estimate || row.can.skip;
  const open = shown.open === row.id;
  return [
    row.can.finish ? button(FINISH_NOW, () => act(`${base}/finish`)) : null,
    row.can.start && (row.next_up || !sheet.editable) ? button(START_NOW, () => act(`${base}/start`), { tone: row.next_up ? null : 'quiet' }) : null,
    row.can.restore ? button(RESTORE, () => act(`${base}/restore`), { tone: 'quiet' }) : null,
    editable && !open ? button(row.can.set_start ? EDIT : ESTIMATE, () => {
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

function sheetCard(day) {
  const rows = sheet.rows.filter((one) => one.day === day.key);
  if (!rows.length) return card(null, [sayNothing(NO_RUNS)]);
  const items = rows.map((row) => ({ row, node: sheetRow(row) }));
  const head = el('div', { class: 'rs-row rs-cols' }, COLUMNS.map((text) => el('div', { text })));
  const list = el('div', { class: 'rs-sheet' }, [head, ...items.map((one) => one.node)]);
  if (rows.length < FILTER_FROM) return card(null, [list], { flush: true });
  const filter = listFilter({ items, value: (one) => one.row, text: rowText, label: FILTER_LABEL, placeholder: FILTER_PLACEHOLDER, empty: NO_HIT });
  return card(null, [el('div', { class: 'table-tools rs-tools' }, [filter.search]), filter.none, list], { flush: true });
}

function lineList(lines, empty) {
  if (!lines.length) return sayNothing(empty);
  return el('ul', { class: 'rs-lines' }, lines.map(([time, title, body, mark]) => el('li', { 'data-quiet': mark ? 'true' : undefined }, [
    el('span', { class: 'mono rs-line-time', title: title || undefined, text: time }),
    el('span', { class: 'rs-line-text' }, [...body, mark ? badge(mark) : null]),
  ])));
}

function postsCard(day) {
  const posts = sheet.next_posts.filter((one) => one.day === day.key);
  const lines = posts.map((one) => [one.at ? clock(one.at) : POST_NOW, '', boldParts(one.text), one.passed ? POST_PASSED : null]);
  return card(POSTS_TITLE, [
    el('p', { class: 'field-help', text: said(POSTS_NOTE, { minutes: sheet.heads_up_minutes, baf: BAF }) }),
    lineList(lines, said(POSTS_NONE, { baf: BAF })),
  ]);
}

function movesCard() {
  const lines = sheet.moves.map((one) => [clock(one.at), new Date(one.at).toLocaleString(), [el('strong', { text: `${one.by_name || one.by_id}: ` }), ...boldParts(one.text)], one.undone ? MOVE_UNDONE : null]);
  return card(MOVES_TITLE, [lineList(lines, MOVES_NONE)], { count: sheet.moves.length || null });
}

function paint() {
  const day = dayNow();
  if (day) shown.day = day.key;
  root.replaceChildren(...[
    headCard(day),
    dayStrip(),
    day ? shiftBar(day) : null,
    saidBar(),
    day ? sheetCard(day) : card(null, [sayNothing(NO_RUNS)]),
    day ? el('div', { class: 'rs-two' }, [postsCard(day), movesCard()]) : null,
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
  if (!shown.id || shown.open !== null || document.hidden || !root || !root.isConnected) return;
  try {
    sheet = await api(`/api/marathons/${shown.id}/runsheet`);
    paint();
  } catch (error) {
    return;
  }
}

async function load() {
  marathons = (await api('/api/marathons')).marathons || [];
  const wanted = wantedId();
  const first = marathons.find((one) => one.phase === 'live') || marathons[0] || null;
  const id = wanted || (first ? String(first.id) : null);
  if (String(id) !== String(shown.id)) Object.assign(shown, { day: null, open: null });
  shown.id = id;
  say = notice();
  root = el('div', { class: 'rs' });
  document.getElementById('dash').replaceChildren(root);
  aside();
  if (!id) {
    root.replaceChildren(sayNothing(NO_MARATHONS));
    return;
  }
  if (!marathons.some((one) => String(one.id) === String(id))) {
    root.replaceChildren(sayNothing(NO_SUCH));
    return;
  }
  sheet = await api(`/api/marathons/${id}/runsheet`);
  paint();
  if (timer === null) timer = setInterval(quietRefresh, REFRESH_MS);
}

window.addEventListener('hashchange', () => refresh());

refresh = start({
  tab: 'events',
  load,
});
