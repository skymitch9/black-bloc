import { api, nameRecord, names, refChannels, send } from './api.js';
import { marathonHref } from './marathons-section.js';
import {
  HERE_ZONE,
  ask,
  avatar,
  badge,
  bar,
  boldParts,
  button,
  card,
  channelLabel,
  closeDrawer,
  el,
  field,
  foldout,
  linkAction,
  localWhen,
  nameNode,
  notice,
  openDrawer,
  run,
  sayNothing,
  sentenceFor,
  when,
  whenField,
} from './ui.js';

export const TONE = { pending: 'warn', approved: 'ok', denied: null, cancelled: null };

const HASH = /^(?:event-|detail=)(\d+)$/;
const GETTING_IT = 'Getting the event…';
const CARD_EVENT = 'The event';
const CARD_DECIDE = 'Decide';
const CARD_MARATHON = 'Marathon';
const CHANGE_IT = 'Change it';
const ASKED_BY = 'asked by ';
const DECIDED_LINE = 'Decided by ';
const WHY_NOT = 'Why not: ';
const NOTHING_TO_DECIDE = 'Nothing is left to decide on this one.';
const OPEN_MARATHON = 'Open ↗';
const PROPOSED = 'Proposed ';
const ANNOUNCED_WORDS = 'yes — the announcement is up';
const SCHEDULED_WORDS = 'made — it is on the server’s Events list';
const SETTLED = 'This one is settled, so its details cannot be changed — only an event waiting ' +
  'for a decision or already approved can be edited.';
const NOT_RESENT = 'Saving does not rewrite an announcement that is already up or a Discord ' +
  'scheduled event that already exists; the answer says when that applies.';
const PLACE_WORD = { room: 'Review channel', post: 'Review post' };
const PLACE_DELETE = { room: 'Delete this room', post: 'Delete this post' };
const PLACE_DELETE_BODY = {
  room: 'The review room is removed. If the event is still waiting or approved it is called off '
    + 'with it, and the person who proposed it is told.',
  post: 'The review post is removed. If the event is still waiting or approved it is called off '
    + 'with it, and the person who proposed it is told.',
};
const PLACE_NOTE = 'A line the host is sent (if the event is still open)';
const SPOTLIGHT_LABEL = 'Spotlight this stream';
const SPOTLIGHT_BODY = 'twitch.tv/{login} goes on the Go-live page’s spotlight list until the '
  + 'event ends (plus the usual slack): the go-live channel announces it, reminds people while it '
  + 'runs, and pins it for the duration.';
const START_HELP = 'When it begins.';
const OPEN_STATUSES = ['pending', 'approved', 'live'];
const MOVE_BUTTON = 'Move to the forum';
const MOVE_BODY = 'A post goes up in the events forum carrying the same card and the same buttons, '
  + 'the room is told where it went, and then the room is removed. The event is NOT called off, '
  + 'and the messages already in the room are not carried over — Discord cannot move those.';
const NOWHERE = '— nowhere in particular —';
const SOMEWHERE_ELSE = '— somewhere else —';
const ELSEWHERE = '__other__';
const WHERE_HELP = 'A voice or stage channel gives everybody a Join button on the Discord '
  + 'event; anything else is written on it as words.';
const BESIDE_HELP = 'Optional beside a channel — a Twitch link, say.';
const INSTEAD_HELP = 'Only used when it is somewhere else.';
const TWITCH = /^(?:https?:\/\/)?(?:www\.|m\.)?twitch\.tv\/([A-Za-z0-9_]{1,25})\/?$/i;
const LINK_SCHEMES = ['https://', 'http://'];
const BARE_HOST = /^(?:www\.)?[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,}(?:\/\S*)?$/i;

const shown = { id: null };
let refresh = () => {};
let forumNow = async () => null;

function tick() {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

function path(id, tail = '') {
  return `/api/events/${encodeURIComponent(id)}${tail}`;
}

export function eventHref(eventId) {
  return `#event-${eventId}`;
}

function wantedEvent() {
  const found = HASH.exec(String(location.hash || '').replace(/^#/, '').trim());
  return found ? found[1] : null;
}

function forgetHash() {
  const drawer = document.querySelector('dialog.drawer');
  if (drawer && drawer.open) return;
  shown.id = null;
  if (wantedEvent()) history.replaceState(null, '', location.pathname + location.search);
}

function whereHref(text) {
  const said = String(text || '').trim();
  if (!said || said.split(/\s+/).length !== 1) return null;
  const lowered = said.toLowerCase();
  for (const scheme of LINK_SCHEMES) {
    if (lowered.startsWith(scheme)) return said.length > scheme.length ? said : null;
  }
  return BARE_HOST.test(said) ? `https://${said}` : null;
}

function twitchLogin(row) {
  if (row.status !== 'approved' || row.where_kind !== 'other') return null;
  const found = TWITCH.exec(String(row.location || '').trim());
  return found ? found[1].toLowerCase() : null;
}

function fact(label, children) {
  return el('div', { class: 'field' }, [
    el('span', { class: 'field-label', text: label }),
    el('div', { class: 'ev-fact' }, [].concat(children).filter(Boolean)),
  ]);
}

function gap() {
  return el('span', { text: ' ' });
}

async function landed(row, done) {
  if (!done.ok) return;
  refresh();
  await openEvent(row.id, (done.found && done.found.message) || '');
}

/** Approve, Deny… and Cancel…, only where the status allows them — the row and the drawer share these. */
export function eventMoves(row, say, after) {
  const moves = [];
  if (row.status === 'pending') {
    moves.push(button('Approve', async () => {
      const sure = await ask({
        title: `Approve “${row.title}”?`,
        body: ['The review channel is updated, the announcement goes out at the configured time, and a Discord scheduled event is made if that setting is on.'],
        confirmLabel: 'Approve it',
        tone: 'warn',
      });
      if (!sure) return;
      after(await run(say, () => send(path(row.id, '/approve'), 'POST', {}), `Approved “${row.title}”.`));
    }));
    moves.push(button('Deny', async () => {
      const reason = el('input', { class: 'input', type: 'text', placeholder: 'why — they are told this' });
      const sure = await ask({
        title: `Deny “${row.title}”?`,
        body: [
          'The person who asked is told, and is shown the reason you type here.',
          field('Reason', reason),
        ],
        confirmLabel: 'Deny it',
      });
      if (!sure) return;
      after(await run(
        say,
        () => send(path(row.id, '/deny'), 'POST', { reason: reason.value.trim() }),
        `Denied “${row.title}”.`,
      ));
    }, { tone: 'danger' }));
  }
  if (row.status !== 'cancelled' && row.status !== 'denied') {
    moves.push(button('Cancel', async () => {
      const sure = await ask({
        title: `Cancel “${row.title}”?`,
        body: ['Anyone who was told about it is told it is off, and the scheduled event is removed.'],
        confirmLabel: 'Cancel it',
      });
      if (!sure) return;
      after(await run(say, () => send(path(row.id, '/cancel'), 'POST', {}), `Cancelled “${row.title}”.`));
    }, { tone: 'quiet' }));
  }
  return moves;
}

/** Move to the forum, only for an open room while the review mode is forum and a forum exists. */
export function forumMove(row, say, forum, after) {
  const movable = row.review_channel_id && row.review_kind !== 'post'
    && OPEN_STATUSES.includes(row.status) && forum && forum.id && forum.mode === 'forum';
  if (!movable) return null;
  return button(MOVE_BUTTON, async () => {
    const sure = await ask({
      title: `Move “${row.title}” into the forum?`,
      body: [MOVE_BODY],
      confirmLabel: 'Move it',
      tone: 'warn',
    });
    if (!sure) return;
    after(await run(say, () => send(path(row.id, '/forum'), 'POST', {}), (found) => found?.message));
  }, { tone: 'warn' });
}

function deletePlace(row, say) {
  const kind = row.review_kind === 'post' ? 'post' : 'room';
  return button(PLACE_DELETE[kind], async () => {
    const note = el('input', { class: 'input', type: 'text' });
    const sure = await ask({
      title: `${PLACE_DELETE[kind]} for “${row.title}”?`,
      body: [PLACE_DELETE_BODY[kind], field(PLACE_NOTE, note)],
      confirmLabel: PLACE_DELETE[kind],
    });
    if (!sure) return;
    const done = await run(
      say,
      () => send(path(row.id, '/room/delete'), 'POST', { note: note.value.trim() }),
      (found) => found?.message,
    );
    await landed(row, done);
  }, { tone: 'danger' });
}

function spotlightMove(row, say, login) {
  return button(SPOTLIGHT_LABEL, async () => {
    const sure = await ask({
      title: `${SPOTLIGHT_LABEL}?`,
      body: [SPOTLIGHT_BODY.replace('{login}', login)],
      confirmLabel: 'Spotlight it',
      tone: 'warn',
    });
    if (!sure) return;
    const done = await run(say, () => send(path(row.id, '/spotlight'), 'POST', {}), (found) => found?.message);
    await landed(row, done);
  }, { tone: 'warn' });
}

function whereFact(row, say) {
  const parts = [];
  if (row.where_channel_id) parts.push(el('span', { text: row.where_label || '' }));
  const typed = String(row.location || '').trim();
  if (typed && (row.where_kind === 'other' || row.where_channel_id)) {
    if (parts.length) parts.push(el('span', { text: ' · ' }));
    const href = whereHref(typed);
    parts.push(href
      ? el('a', { href, rel: 'noreferrer', target: '_blank', text: typed })
      : el('span', { text: typed }));
  }
  if (!parts.length) return null;
  const login = twitchLogin(row);
  if (login) parts.push(gap(), spotlightMove(row, say, login));
  return fact('Where', parts);
}

function whenWords(row) {
  if (!row.starts_at) return null;
  const range = row.ends_at ? `${when(row.starts_at)} – ${when(row.ends_at)}` : when(row.starts_at);
  return [range, row.duration, HERE_ZONE].filter(Boolean).join(' · ');
}

function eventCard(row, say, forum) {
  const facts = [];
  if (row.description) facts.push(el('p', { class: 'ev-about', text: row.description }));
  facts.push(whereFact(row, say));
  const at = whenWords(row);
  if (at) facts.push(fact('When', el('span', { text: at })));
  if (row.review_channel_id) {
    const kind = row.review_kind === 'post' ? 'post' : 'room';
    const move = forumMove(row, say, forum, (done) => landed(row, done));
    facts.push(fact(PLACE_WORD[kind], [nameNode(row.review_channel_id), gap(), deletePlace(row, say), move ? gap() : null, move]));
  }
  if (row.moved_word) facts.push(fact('Now', el('span', { text: row.moved_word })));
  if (row.announced) facts.push(fact('Announced', el('span', { text: ANNOUNCED_WORDS })));
  if (row.scheduled) facts.push(fact('Discord event', el('span', { text: SCHEDULED_WORDS })));
  return card(CARD_EVENT, facts.filter(Boolean));
}

function decideCard(row, say) {
  const lines = [];
  if (row.decided_by_id || row.decided_at) {
    lines.push(el('p', { class: 'field-help' }, [
      el('span', { text: DECIDED_LINE }),
      nameNode(row.decided_by_id, row.decided_by_name),
      row.decided_at ? el('span', { text: `, ${when(row.decided_at)}` }) : null,
    ]));
  }
  if (row.deny_reason) lines.push(el('p', { class: 'field-help', text: `${WHY_NOT}${row.deny_reason}` }));
  const moves = eventMoves(row, say, (done) => landed(row, done));
  if (moves.length) lines.push(bar(moves));
  if (!lines.length) lines.push(el('p', { class: 'field-help', text: NOTHING_TO_DECIDE }));
  return card(CARD_DECIDE, lines);
}

function marathonCard(row) {
  if (!row.marathon) return null;
  return card(CARD_MARATHON, [
    el('p', { class: 'field-help mx-line' }, [
      ...boldParts(row.marathon.line || row.marathon.name || ''),
      gap(),
      linkAction(OPEN_MARATHON, marathonHref(row.marathon.id)),
    ]),
  ]);
}

/** A channel from the server, a typed place, or both — the box is never taken away. */
function whereControl(row, channels) {
  const select = el('select', { class: 'input' });
  select.append(el('option', { value: '', text: NOWHERE }));
  select.append(el('option', { value: ELSEWHERE, text: SOMEWHERE_ELSE }));
  for (const [kind, label] of [['voice', 'Voice channels'], ['text', 'Text channels']]) {
    const group = el('optgroup', { label });
    for (const channel of channels.filter((one) => one.type === kind)) {
      group.append(el('option', {
        value: String(channel.id),
        text: channelLabel(channel, channels),
        selected: String(row.where_channel_id || '') === String(channel.id) ? true : undefined,
      }));
    }
    if (group.childElementCount) select.append(group);
  }
  if (row.where_kind === 'other') select.value = ELSEWHERE;
  else if (!row.where_channel_id) select.value = '';

  const typed = el('input', { class: 'input', type: 'text', value: row.location || '', placeholder: 'twitch.tv/blackbloc' });
  const typedField = field('Where, or a link', typed, INSTEAD_HELP);
  const hint = typedField.querySelector('.field-help');
  const sayHint = () => {
    const beside = select.value !== '' && select.value !== ELSEWHERE;
    hint.textContent = beside ? BESIDE_HELP : INSTEAD_HELP;
  };
  select.addEventListener('change', sayHint);
  sayHint();

  return {
    nodes: [field('Where', select, WHERE_HELP), typedField],
    payload: () => {
      const location = typed.value.trim();
      if (select.value === '') return { where_kind: null, where_channel_id: null, location };
      if (select.value === ELSEWHERE) {
        return { where_kind: 'other', where_channel_id: null, location };
      }
      const picked = channels.find((one) => String(one.id) === select.value);
      return {
        where_kind: picked && picked.type === 'voice' ? 'voice' : 'text',
        where_channel_id: select.value,
        location,
      };
    },
  };
}

async function changeFold(row) {
  if (!row.editable) return el('p', { class: 'field-help', text: SETTLED });
  const say = notice();
  const title = el('input', { class: 'input', type: 'text', value: row.title || '' });
  const description = el('textarea', { class: 'input area', rows: '3' });
  description.value = row.description || '';
  const where = whereControl(row, await refChannels());
  const start = whenField({ label: 'Starts', value: localWhen(row.starts_at), min: localWhen(), help: START_HELP });
  const duration = el('input', { class: 'input', type: 'text', value: row.duration || '', placeholder: '2h' });

  const save = button('Save', async () => {
    const done = await run(
      say,
      () => send(path(row.id), 'PUT', {
        title: title.value.trim(),
        description: description.value.trim(),
        start: start.value(),
        duration: duration.value.trim(),
        tz: start.tz(),
        ...where.payload(),
      }),
      (found) => [found?.message, ...(found?.notes || [])].filter(Boolean).join(' '),
    );
    if (!done.ok) return;
    refresh();
    await openEvent(row.id, say.said === undefined ? say.textContent : say.said);
  }, { tone: 'warn', small: false });

  return foldout(CHANGE_IT, [
    el('p', { class: 'field-help', text: NOT_RESENT }),
    field('Title', title),
    field('What it is', description),
    ...where.nodes,
    start.node,
    field('How long', duration, 'Like 1h30m, 2h or 45m; blank means two hours.'),
    bar([save]),
    say,
  ]);
}

function headLine(row) {
  const record = nameRecord(row.requester_id);
  const who = row.requester_name || (record && (record.display_name || record.name)) || null;
  const at = row.starts_at
    ? (row.ends_at ? `${when(row.starts_at)} – ${when(row.ends_at)}` : when(row.starts_at))
    : null;
  return el('p', { class: 'field-help ev-head' }, [
    badge(row.status, TONE[row.status] || null),
    el('span', { text: ' · ' }),
    avatar(who, record && record.avatar_url),
    el('span', { text: ` ${ASKED_BY}` }),
    nameNode(row.requester_id, row.requester_name),
    at ? el('span', { text: ` · ${at}` }) : null,
  ]);
}

async function eventDrawer(row, message) {
  await names([row.requester_id, row.decided_by_id, row.review_channel_id].filter(Boolean)).catch(() => null);
  const forum = await forumNow().catch(() => null);
  const say = notice();
  if (message) say.say(message, 'ok');
  return [
    say,
    headLine(row),
    eventCard(row, say, forum),
    decideCard(row, say),
    marathonCard(row),
    await changeFold(row),
    el('p', { class: 'field-help ev-foot', text: `${PROPOSED}${when(row.created_at)} · #${row.id}` }),
  ];
}

/** Opens (or redraws) event `eventId` in the drawer; the page's queue is refreshed by the caller. */
export async function openEvent(eventId, message = '') {
  await tick();
  shown.id = String(eventId);
  if (wantedEvent() !== shown.id || !location.hash.startsWith('#event-')) {
    history.replaceState(null, '', `${location.pathname}${location.search}${eventHref(shown.id)}`);
  }
  const fallback = `Event #${eventId}`;
  if (!message) openDrawer(fallback, sayNothing(GETTING_IT), { onClose: forgetHash });
  try {
    const payload = await api(path(eventId));
    const row = payload.event || payload;
    openDrawer(row.title || fallback, await eventDrawer(row, message), { onClose: forgetHash });
  } catch (error) {
    const found = sentenceFor(error);
    openDrawer(fallback, [notice(found.text, found.tone)], { onClose: forgetHash });
  }
}

let deepLinked = false;

/** Wires the drawer to the page: how to reload the queue, how to read the forum, and the deep link. */
export function eventDrawerFor({ reload, forum }) {
  refresh = reload;
  forumNow = forum;
  const wanted = wantedEvent();
  if (wanted && !deepLinked) {
    deepLinked = true;
    openEvent(wanted);
  }
}

window.addEventListener('hashchange', () => {
  const wanted = wantedEvent();
  if (!wanted) {
    if (shown.id && !location.hash) closeDrawer();
    shown.id = null;
    return;
  }
  if (wanted === shown.id) return;
  openEvent(wanted);
});
