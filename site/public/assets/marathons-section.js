import { api, send } from './api.js';
import {
  ago,
  ask,
  askForm,
  badge,
  bar,
  boldParts,
  button,
  card,
  closeDrawer,
  duration,
  el,
  field,
  keepSaying,
  memberPicker,
  modeChip,
  nameNode,
  notice,
  openDrawer,
  run,
  sayAgain,
  sayNothing,
  section,
  segment,
  sentenceFor,
  table,
  textAction,
  when,
} from './ui.js';

const shown = { id: null, filter: 'ours' };
const HASH = /^marathon-(\d+)$/;
let refresh = async () => {};
let showEvent = () => {};
let makesEvent = true;
let deepLinked = false;

const LIST_NOTE = 'Every marathon schedule Black Bloc follows. It re-reads each one on its own '
  + '— every half hour while it is near — and posts a board, a reminder before each run of ours '
  + 'and a shoutout when it goes live. A row opens its runs.';
const NOTHING_YET = 'Black Bloc follows no marathon yet. **Add a marathon** with its GDQ '
  + 'schedule link.';
const GETTING_IT = 'Reading the schedule…';
const MODE_OFF = 'Marathon posts are **{mode}**, so nothing is read or posted. **Marathon '
  + 'settings** below turns them on.';
const MODE_SHADOW = 'Marathon posts are in **shadow**: the board, the reminders and the '
  + 'shoutouts land where shadow_channel_id points, with the rehearsal note.';
const ADD_NOTE = 'Paste the GDQ schedule link (gamesdonequick.com/schedule/74) or the tracker '
  + 'event link. Black Bloc reads it at once and every half hour after that while it is near.';
const CHANNEL_HELP = 'The Twitch channel it airs on, from the Go-live page. With one, its '
  + 'ping window follows the marathon and its live title confirms which run is on.';
const NO_CHANNEL = 'No channel — each run links its runner';
const PAIR_NOTE = 'A name on the schedule with no Twitch link, or the wrong one: pair it with '
  + 'the member it is. A pairing beats the automatic match, and Unpair gives it back.';
const RUNS_NOTE = 'Ours are highlighted. A moved run says where it was; a run the schedule '
  + 'dropped is kept as history.';
const NO_RUNS = 'No runs on this schedule yet — it may not be published. Black Bloc keeps '
  + 'reading it.';
const NO_PAIRINGS = 'No pairings. The automatic match reads each runner’s Twitch link.';
const REMOVE_BODY = 'Its runs and pairings go with it and its ping window closes. Posts already '
  + 'made stay where they are.';
const WINDOW_LINE = 'Ping window on **{login}**: {start} – {end}.';
const NO_WINDOW = 'No ping window — the marathon has no channel, no dates yet, or is paused.';
const CHANNEL_GONE = 'Its channel row is gone from the Go-live page, so it has no window and '
  + 'no live title. Pick another channel, or none.';
const NEXT_LINE = '{marathon} is over — the next GDQ event is **{next}**, {date} ({relative}).';
const NEXT_ADDED = 'Added — see **{name}** below.';
const NEXT_DISMISSED = 'Dismissed — **Look again** asks the tracker once more.';
const NEXT_NONE = '{marathon} is over and the GDQ tracker lists nothing ahead yet.';
const NEXT_NOT_YET = '{marathon} is over. Black Bloc has not looked up the next GDQ event yet.';
const NEXT_NOTE = 'Staff decide: nothing is added until someone presses **Add it**. It is read '
  + 'from the tracker link and airs on this marathon’s channel.';
const NEXT_WAITING = '{count} marathon{s} {have} a next event waiting — **Next up** on the row.';
const POLL_HELP = 'Re-read every N minutes while it is near — blank for the default '
  + '(marathon_poll_minutes). 10 to 120.';
const HELD_NOTE = 'held by staff';
const EVENT_BOX = 'Also make it an event';
const EVENT_BOX_HELP = 'It goes into the events review above like any proposal, dated from the '
  + 'schedule — and waits for the schedule if GDQ has not published one yet. Its dates follow '
  + 'the schedule after that.';
const EVENT_NOTE = 'A marathon is an event: its dates follow the schedule while it is waiting '
  + 'for a decision or approved. **Unlink** leaves the event exactly as it is; removing the '
  + 'marathon calls its event off.';
const EVENT_TONE = { pending: 'warn', approved: 'ok', denied: 'danger', cancelled: null, gone: null };
const PHASE_TONE = { far: null, near: 'warn', live: 'ok', over: null, paused: null };
const STATE_TONE = { upcoming: null, live: 'ok', done: null, dropped: 'danger' };

function full(node) {
  node.setAttribute('data-span', 'full');
  return node;
}

function said(text, values) {
  let out = String(text);
  for (const [key, value] of Object.entries(values)) out = out.replaceAll(`{${key}}`, String(value));
  return out;
}

function wantedId() {
  const found = HASH.exec(String(location.hash || '').replace(/^#/, '').trim());
  return found ? found[1] : null;
}

function forgetHash() {
  const drawer = document.querySelector('dialog.drawer');
  if (drawer && drawer.open) return;
  shown.id = null;
  if (wantedId()) history.replaceState(null, '', location.pathname + location.search);
}

function datesOf(row) {
  if (!row.starts_at) return 'dates not published';
  return `${when(row.starts_at)} – ${when(row.ends_at)}`;
}

function relative(iso) {
  const at = new Date(iso);
  if (!iso || Number.isNaN(at.getTime())) return '—';
  const seconds = Math.round((at.getTime() - Date.now()) / 1000);
  return seconds >= 0 ? `in ${duration(seconds)}` : `${duration(-seconds)} ago`;
}

function nextSentence(row) {
  const next = row.next || {};
  if (next.state === 'added') return said(NEXT_ADDED, { name: next.added_name || next.name || '' });
  if (next.state === 'none') return said(NEXT_NONE, { marathon: row.name });
  if (!next.state) return said(NEXT_NOT_YET, { marathon: row.name });
  const line = said(NEXT_LINE, {
    marathon: row.name,
    next: next.name,
    date: next.datetime ? new Date(next.datetime).toLocaleDateString() : 'no date yet',
    relative: relative(next.datetime),
  });
  return next.state === 'dismissed' ? `${line} ${NEXT_DISMISSED}` : line;
}

async function addNext(row, say) {
  const done = await run(say, () => send('/api/marathons', 'POST', { next_of: row.id, event_id: row.next.event_id }), (found) => found?.message);
  if (!done.ok) return;
  await refresh();
  await openMarathon(done.found.id, done.found.name, done.found.message);
}

async function dismissNext(row, say) {
  const done = await run(say, () => send(`/api/marathons/${row.id}`, 'PATCH', { dismiss_next: true, event_id: row.next.event_id }), (found) => found?.message);
  await after(row, done);
}

async function lookAgain(row, say) {
  const done = await run(say, () => send(`/api/marathons/${row.id}/next`, 'POST', {}), (found) => found?.message);
  await after(row, done);
}

function nextMoves(row, say) {
  const next = row.next || {};
  const moves = [];
  if (next.state === 'open') {
    moves.push(button('Add it', () => addNext(row, say), { tone: 'warn' }));
    moves.push(button('Not this one', () => dismissNext(row, say), { tone: 'quiet' }));
  }
  if (next.state === 'added' && next.added_marathon_id) {
    moves.push(textAction(`Open ${next.added_name || next.name}`, () => openMarathon(next.added_marathon_id, next.added_name || next.name)));
  }
  if (next.can_look_again && next.state !== 'open' && next.state !== 'added') {
    moves.push(button('Look again', () => lookAgain(row, say), { tone: 'quiet' }));
  }
  return moves;
}

function nextCell(row, say) {
  if (!row.next) return el('span', { class: 'cell-quiet', text: '—' });
  const next = row.next;
  const words = {
    open: `${next.name} · ${next.datetime ? new Date(next.datetime).toLocaleDateString() : 'no date yet'}`,
    dismissed: `Dismissed: ${next.name}`,
    added: `Added: ${next.added_name || next.name}`,
    none: 'Nothing listed ahead yet',
  }[next.state] || 'Not looked up yet';
  return el('span', {}, [
    el('span', { class: next.state === 'open' ? 'cell-name' : 'cell-quiet' }, boldParts(words)),
    el('div', { class: 'bar' }, nextMoves(row, say)),
  ]);
}

function nextCard(marathon, say) {
  if (!marathon.next) return null;
  const moves = nextMoves(marathon, say);
  if (marathon.next.state === 'open' && marathon.next.can_look_again) {
    moves.push(button('Look again', () => lookAgain(marathon, say), { tone: 'quiet' }));
  }
  return card('Next up', [
    el('p', {}, boldParts(nextSentence(marathon))),
    marathon.next.state === 'open' ? el('p', { class: 'field-help' }, boldParts(NEXT_NOTE)) : null,
    marathon.next.url && marathon.next.state !== 'none'
      ? el('p', { class: 'field-help' }, [el('a', { href: marathon.next.url, text: 'the tracker', rel: 'noreferrer', target: '_blank' })])
      : null,
    bar(moves),
  ]);
}

function readLine(row) {
  if (row.trouble) return el('span', { class: 'cell-quiet', 'data-tone': 'danger', text: row.trouble });
  if (!row.last_fetched_at) return el('span', { class: 'cell-quiet', text: 'not read yet' });
  const read = ago(row.last_fetched_at);
  return el('span', { class: 'cell-quiet', title: read.title, text: `last read ${read.text}` });
}

async function channelChoices() {
  const rows = await api('/api/golive/spotlight').catch(() => []);
  return (Array.isArray(rows) ? rows : []).map((one) => ({
    value: String(one.id),
    label: one.display_name && one.display_name.toLowerCase() !== one.twitch_login
      ? `${one.twitch_login} · ${one.display_name}`
      : one.twitch_login,
  }));
}

function channelPicker(choices, current) {
  const select = el('select', { class: 'input' }, [
    el('option', { value: '', text: NO_CHANNEL, selected: !current || undefined }),
    ...choices.map((one) => el('option', {
      value: one.value,
      text: one.label,
      selected: String(current || '') === one.value || undefined,
    })),
  ]);
  return select;
}

async function addMarathon() {
  const name = el('input', { class: 'input', type: 'text', placeholder: 'AGDQ 2027' });
  const url = el('input', { class: 'input', type: 'url', placeholder: 'https://gamesdonequick.com/schedule/74' });
  const channel = channelPicker(await channelChoices(), null);
  const alsoEvent = el('input', { class: 'input switch', type: 'checkbox', checked: makesEvent ? true : undefined });
  let made = null;
  const sure = await askForm({
    title: 'Add a marathon',
    body: [
      el('p', { class: 'ask-body', text: ADD_NOTE }),
      field('Name', name),
      field('Schedule link', url),
      field('Channel it airs on', channel, CHANNEL_HELP),
      field(EVENT_BOX, alsoEvent, EVENT_BOX_HELP),
    ],
    confirmLabel: 'Add it',
    tone: 'warn',
    onConfirm: async () => {
      made = await send('/api/marathons', 'POST', {
        name: name.value.trim(),
        schedule_url: url.value.trim(),
        spotlight_id: channel.value || null,
        make_event: alsoEvent.checked,
      });
      return null;
    },
  });
  if (!sure || !made) return;
  await refresh();
  await openMarathon(made.id, made.name, made.message);
}

function personCell(run) {
  return el('span', {}, run.people.map((one, index) => el('span', {}, [
    index ? el('span', { text: ', ' }) : null,
    one.user_id ? nameNode(one.user_id, one.member_name) : el('span', { text: one.name }),
    el('span', { class: 'cell-quiet', text: one.part === 'runner' ? '' : ` (${one.part})` }),
  ])));
}

function whenCell(run) {
  return el('span', {}, [
    el('span', { class: 'mono', text: when(run.scheduled_at) }),
    run.moved && run.previous_scheduled_at
      ? el('span', { class: 'cell-quiet', 'data-tone': 'warn', text: ` · moved from ${when(run.previous_scheduled_at)}` })
      : null,
  ]);
}

async function after(marathon, done) {
  if (!done.ok) return;
  await refresh();
  await openMarathon(marathon.id, marathon.name, (done.found || {}).message || '');
}

function runTools(marathon, row, say) {
  const tools = [];
  if (row.shoutable) {
    tools.push(button('Shout it now', async () => {
      const done = await run(say, () => send(`/api/marathons/${marathon.id}/runs/${row.id}/shout`, 'POST', {}), (found) => found?.message);
      await after(marathon, done);
    }, { tone: 'warn' }));
  }
  if (row.can_mark_done && (row.ours || row.state === 'live')) {
    tools.push(button('Mark done', async () => {
      const done = await run(say, () => send(`/api/marathons/${marathon.id}/runs/${row.id}/done`, 'POST', {}), (found) => found?.message);
      await after(marathon, done);
    }, { tone: 'quiet' }));
  }
  if (row.can_mark_live && !row.shoutable) {
    tools.push(button('Mark it live', async () => {
      const done = await run(say, () => send(`/api/marathons/${marathon.id}/runs/${row.id}/live`, 'POST', {}), (found) => found?.message);
      await after(marathon, done);
    }, { tone: 'quiet' }));
  }
  if (row.can_mark_upcoming) {
    tools.push(button('Mark it upcoming', async () => {
      const done = await run(say, () => send(`/api/marathons/${marathon.id}/runs/${row.id}/upcoming`, 'POST', {}), (found) => found?.message);
      await after(marathon, done);
    }, { tone: 'quiet' }));
  }
  return el('div', { class: 'bar' }, tools);
}

function runsCard(marathon, say) {
  const holder = el('div');
  const paint = () => {
    const rows = (marathon.run_list || []).filter((one) => shown.filter === 'all' || one.ours);
    holder.replaceChildren(table([
      { label: 'When', cell: (row) => whenCell(row) },
      { label: 'Game', cell: (row) => el('span', { class: row.ours ? 'cell-name' : '', text: row.game }) },
      { label: 'Category', cell: (row) => row.category },
      { label: 'People', cell: (row) => personCell(row) },
      { label: 'State', cell: (row) => el('span', { class: 'cell-kind' }, [
        badge(row.state_word, STATE_TONE[row.state] || null),
        row.ours ? badge('ours', 'ok') : null,
        row.held ? badge(HELD_NOTE, 'warn') : null,
      ]) },
      { label: '', cell: (row) => runTools(marathon, row, say) },
    ], rows, { empty: marathon.run_list && marathon.run_list.length ? 'None of ours on this schedule yet — pick All to see every run.' : NO_RUNS }));
  };
  const chips = segment(
    [{ value: 'ours', label: `Ours (${marathon.ours})` }, { value: 'all', label: `All (${marathon.runs})` }],
    shown.filter,
    { onChange: () => { shown.filter = chips.readValue(); paint(); } },
  );
  paint();
  return card('Runs', [el('p', { class: 'field-help', text: RUNS_NOTE }), chips, holder]);
}

function pairingsCard(marathon, say) {
  const rows = (marathon.pairings || []).map((one) => ({
    runner: one.runner_name,
    member: nameNode(one.user_id, one.member_name),
    scope: one.everywhere ? 'every schedule' : 'this schedule',
    tools: button('Unpair', async () => {
      const done = await run(say, () => send(`/api/marathons/${marathon.id}/people/${one.id}`, 'DELETE'), (found) => found?.message);
      await after(marathon, done);
    }, { tone: 'quiet' }),
  }));
  const pair = button('Pair a runner…', async () => {
    const listed = el('datalist', { id: 'marathon-unmatched' }, (marathon.unmatched || []).map((one) => el('option', { value: one })));
    const runner = el('input', { class: 'input', type: 'text', list: 'marathon-unmatched', placeholder: 'the name as the schedule writes it' });
    const picker = memberPicker({ label: 'Member' });
    const scope = segment([{ value: 'this', label: 'This schedule' }, { value: 'every', label: 'Every schedule' }], 'this');
    let done = null;
    const sure = await askForm({
      title: `Pair a runner on ${marathon.name}`,
      body: [el('p', { class: 'ask-body', text: PAIR_NOTE }), listed, field('Name on the schedule', runner), picker.node, field('Where it counts', scope)],
      confirmLabel: 'Pair them',
      tone: 'warn',
      onConfirm: async () => {
        done = await send(`/api/marathons/${marathon.id}/people`, 'POST', {
          runner_name: runner.value.trim(),
          user_id: picker.id,
          everywhere: scope.readValue() === 'every',
        });
        return null;
      },
    });
    if (!sure || !done) return;
    await after(marathon, { ok: true, found: done });
  }, { tone: 'warn' });
  return card('Who is who', [
    el('p', { class: 'field-help', text: PAIR_NOTE }),
    table([
      { label: 'Name on the schedule', cell: (row) => row.runner },
      { label: 'Member', cell: (row) => row.member },
      { label: 'Counts on', cell: (row) => row.scope },
      { label: '', cell: (row) => row.tools },
    ], rows, { empty: NO_PAIRINGS }),
    bar([pair]),
  ]);
}

async function channelCard(marathon, say) {
  const picker = channelPicker(await channelChoices(), marathon.spotlight_id);
  const save = button('Save the channel', async () => {
    const done = await run(say, () => send(`/api/marathons/${marathon.id}`, 'PATCH', { spotlight_id: picker.value || null }), () => 'Saved.');
    await after(marathon, done);
  });
  const windowLine = marathon.window && marathon.channel_login
    ? said(WINDOW_LINE, { login: marathon.channel_login, start: when(marathon.window.starts_at), end: when(marathon.window.ends_at) })
    : NO_WINDOW;
  return card('The channel', [
    marathon.channel_gone ? notice(CHANNEL_GONE, 'warn') : null,
    field('Airs on', picker, CHANNEL_HELP),
    el('p', { class: 'field-help' }, boldParts(windowLine)),
    bar([save]),
  ]);
}

function eventCard(marathon, say) {
  const event = marathon.event || {};
  const moves = [];
  if (event.id && event.status !== 'gone') {
    moves.push(textAction(`Open event #${event.id}`, () => {
      closeDrawer();
      showEvent(event.id);
    }));
  }
  if (event.id || event.wanted) {
    moves.push(button('Unlink', async () => {
      const done = await run(say, () => send(`/api/marathons/${marathon.id}/event`, 'DELETE'), (found) => found?.message);
      await after(marathon, done);
    }, { tone: 'quiet' }));
  } else {
    moves.push(button('Make an event now', async () => {
      const done = await run(say, () => send(`/api/marathons/${marathon.id}/event`, 'POST', {}), (found) => found?.message);
      await after(marathon, done);
    }, { tone: 'warn' }));
  }
  return card('Event', [
    el('p', {}, [
      event.status ? badge(event.status, EVENT_TONE[event.status] || null) : null,
      el('span', { text: event.status ? ' ' : '' }),
      ...boldParts(event.line || ''),
    ]),
    el('p', { class: 'field-help' }, boldParts(EVENT_NOTE)),
    bar(moves),
  ]);
}

function eventCell(row) {
  const event = row.event || {};
  if (event.id) return badge(`#${event.id} ${event.status}`, EVENT_TONE[event.status] || null);
  if (event.waiting) return el('span', { class: 'cell-quiet', text: 'waiting for dates' });
  return el('span', { class: 'cell-quiet', text: '—' });
}

function moveBar(marathon, say) {
  const moves = [];
  if (marathon.active) {
    moves.push(button('Refresh now', async () => {
      const done = await run(say, () => send(`/api/marathons/${marathon.id}/refresh`, 'POST', {}), (found) => found?.message);
      await after(marathon, done);
    }, { tone: 'warn' }));
  }
  moves.push(button(marathon.active ? 'Pause' : 'Resume', async () => {
    const done = await run(say, () => send(`/api/marathons/${marathon.id}`, 'PATCH', { active: !marathon.active }), (found) => found?.message);
    await after(marathon, done);
  }));
  const poll = el('input', {
    class: 'input',
    type: 'text',
    inputmode: 'numeric',
    size: 4,
    placeholder: 'default',
    value: marathon.poll_minutes ? String(marathon.poll_minutes) : '',
    title: POLL_HELP,
    'aria-label': 'Re-read every N minutes',
  });
  moves.push(el('label', { class: 'field-help', title: POLL_HELP }, [el('span', { text: 'Re-read every ' }), poll, el('span', { text: ' minutes' })]));
  moves.push(button('Save', async () => {
    const given = poll.value.trim();
    const wanted = given === '' ? null : (/^\d+$/.test(given) ? Number(given) : given);
    const done = await run(say, () => send(`/api/marathons/${marathon.id}`, 'PATCH', { poll_minutes: wanted }), () => (wanted === null ? `**${marathon.name}** is re-read on the default gap again.` : `**${marathon.name}** is re-read every ${wanted} minutes while it is near.`));
    await after(marathon, done);
  }, { tone: 'quiet' }));
  moves.push(button(marathon.board_message_id ? 'Refresh the board' : 'Post the board', async () => {
    const done = await run(say, () => send(`/api/marathons/${marathon.id}/board`, 'POST', {}), (found) => found?.message);
    await after(marathon, done);
  }));
  moves.push(button('Remove', async () => {
    const sure = await ask({ title: `Remove ${marathon.name}?`, body: [REMOVE_BODY], confirmLabel: 'Remove it' });
    if (!sure) return;
    const done = await run(say, () => send(`/api/marathons/${marathon.id}`, 'DELETE'), (found) => found?.message);
    if (!done.ok) return;
    keepSaying('marathons', say);
    closeDrawer();
    await refresh();
  }, { tone: 'danger' }));
  return bar(moves);
}

async function marathonDrawer(marathon, message) {
  const say = notice();
  if (message) say.say(message, 'ok');
  return [
    say,
    el('p', { class: 'field-help' }, [
      badge(marathon.phase_word, PHASE_TONE[marathon.phase] || null),
      el('span', { text: ` ${datesOf(marathon)} · ${marathon.source_word} · ` }),
      el('a', { href: marathon.schedule_page, text: 'the schedule', rel: 'noreferrer', target: '_blank' }),
      el('span', { text: ' · ' }),
      readLine(marathon),
    ]),
    moveBar(marathon, say),
    eventCard(marathon, say),
    nextCard(marathon, say),
    runsCard(marathon, say),
    pairingsCard(marathon, say),
    await channelCard(marathon, say),
  ];
}

async function openMarathon(marathonId, title, message = '') {
  shown.id = String(marathonId);
  if (wantedId() !== shown.id) {
    history.replaceState(null, '', `${location.pathname}${location.search}#marathon-${shown.id}`);
  }
  openDrawer(title || `Marathon #${marathonId}`, sayNothing(GETTING_IT), { onClose: forgetHash });
  try {
    const marathon = await api(`/api/marathons/${encodeURIComponent(marathonId)}`);
    openDrawer(marathon.name, await marathonDrawer(marathon, message), { onClose: forgetHash });
  } catch (error) {
    const line = sentenceFor(error);
    openDrawer(title || `Marathon #${marathonId}`, [notice(line.text, line.tone)], { onClose: forgetHash });
  }
}

function listSection(payload, say) {
  const rows = payload.marathons || [];
  const list = section('Marathons', LIST_NOTE, { count: rows.length, id: 'marathons', open: true });
  const add = button('Add a marathon', () => addMarathon(), { tone: 'warn' });
  const grid = table([
    { label: 'Marathon', cell: (row) => textAction(row.name, () => openMarathon(row.id, row.name)) },
    { label: 'Dates', cell: (row) => datesOf(row) },
    { label: 'State', cell: (row) => badge(row.phase_word, PHASE_TONE[row.phase] || null) },
    { label: 'Ours', cell: (row) => `${row.ours} of ${row.runs}` },
    { label: 'Channel', cell: (row) => row.channel_login || (row.channel_gone ? 'gone' : '—') },
    { label: 'Event', cell: (row) => eventCell(row) },
    { label: 'Read', cell: (row) => readLine(row) },
    { label: 'Next up', cell: (row) => nextCell(row, say) },
  ], rows, { empty: NOTHING_YET });
  const waiting = Number(payload.next_waiting || 0);
  list.body.append(...[
    waiting ? notice(said(NEXT_WAITING, { count: waiting, s: waiting === 1 ? '' : 's', have: waiting === 1 ? 'has' : 'have' }), 'warn') : null,
    el('p', { class: 'field-help' }, [el('span', { text: 'Marathon posts are ' }), modeChip(payload.mode), el('span', { text: '.' })]),
    payload.mode === 'off' ? el('p', { class: 'field-help' }, boldParts(said(MODE_OFF, { mode: payload.mode }))) : null,
    payload.mode === 'shadow' ? el('p', { class: 'field-help' }, boldParts(MODE_SHADOW)) : null,
    card(null, [bar([add]), grid]),
    say,
  ].filter(Boolean));
  return full(list.node);
}

/** The Events page's Marathons section: the same list, drawer and moves the Marathons page had. */
export async function marathonsSection({ reload, openEvent }) {
  refresh = reload;
  showEvent = openEvent;
  const payload = await api('/api/marathons');
  makesEvent = payload.makes_event !== false;
  const say = sayAgain('marathons', notice());
  const node = listSection(payload, say);
  const wanted = wantedId();
  if (wanted && !deepLinked) {
    deepLinked = true;
    const found = (payload.marathons || []).find((one) => String(one.id) === wanted);
    openMarathon(wanted, found ? found.name : `Marathon #${wanted}`);
  }
  return node;
}

/** The Events page's detail card links back here by address, so the drawer opens the same way. */
export function marathonHref(marathonId) {
  return `#marathon-${marathonId}`;
}

window.addEventListener('hashchange', () => {
  const wanted = wantedId();
  if (!wanted) {
    if (shown.id) closeDrawer();
    return;
  }
  if (wanted === shown.id) return;
  openMarathon(wanted, `Marathon #${wanted}`);
});
