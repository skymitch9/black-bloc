import { api, listOf, names, notesOf } from './api.js';
import { FEATURE_TABS, start, tabHref } from './app.js';
import { shellStatus } from './shell.js';
import { card, el, icon, idsIn, nameNode, sayNothing, shortWhen } from './ui.js';

const OPEN_NOTE = {
  rolemenu: (open) => `${open.role_menus_posted} posted`,
  tempvoice: (open) => `${open.temp_channels} rooms open`,
  honeypot: (open) => `${open.honeypot_hits_7d} trips in 7 days`,
  events: (open) => `${open.open_events} waiting`,
  modmail: (open) => `${open.open_modmail} open tickets`,
};

const MODE_NOTE = {
  on: 'acting on what it sees',
  shadow: 'logging what it would do, acting on nothing',
  off: 'not running',
  channel: 'one channel per ticket',
  thread: 'private threads in one channel',
};

const NEEDS = [
  { key: 'open_events', tone: 'warn', tab: 'events', say: (n) => `${n} event${n === 1 ? '' : 's'} waiting on a Lead` },
  { key: 'open_modmail', tone: 'info', tab: 'modmail', say: (n) => `${n} open modmail${n === 1 ? '' : 's'}` },
  { key: 'honeypot_hits_7d', tone: 'danger', tab: 'honeypot', say: (n) => `${n} honeypot trip${n === 1 ? '' : 's'} in 7 days` },
];

function title(feature) {
  return String(feature).replace(/^./, (c) => c.toUpperCase());
}

function pillMode(mode) {
  if (mode === null || mode === undefined || mode === '') return 'off';
  const said = String(mode);
  return said === 'channel' || said === 'thread' ? 'on' : said;
}

function featureNote(feature, open) {
  const note = OPEN_NOTE[feature];
  if (!note || !open) return null;
  const value = note(open);
  return value.startsWith('undefined') ? null : value;
}

function featureRow(row, open) {
  const tab = FEATURE_TABS[row.feature];
  const said = featureNote(row.feature, open) || MODE_NOTE[String(row.mode)] || 'no mode set';
  const blank = row.mode === null || row.mode === undefined || row.mode === '';
  return el(tab ? 'a' : 'div', {
    class: 'chip',
    href: tab ? tabHref(tab) : undefined,
  }, [
    el('div', { class: 'rowlist-main' }, [
      el('span', { class: 'rowlist-name', text: title(row.feature) }),
      el('span', { class: 'rowlist-note', text: said }),
    ]),
    el('span', { class: 'pill', 'data-mode': pillMode(row.mode), text: blank ? 'not set' : String(row.mode) }),
    tab ? icon('chevronRight', 16) : null,
  ]);
}

function featuresCard(status) {
  const rows = (status && status.features) || [];
  if (rows.length === 0) {
    return card('Features', [sayNothing('No feature reports a mode yet.')], { flush: true });
  }
  return card('Features', rows.map((row) => featureRow(row, status.open)), {
    count: rows.length,
    flush: true,
  });
}

function needsCard(status) {
  const open = status && status.open;
  if (!open) {
    return card('Needs a human', [
      sayNothing('The open counts could not be read, so they are left blank rather than shown as zero.'),
    ], { flush: true });
  }
  const rows = NEEDS
    .filter((one) => Number(open[one.key]) > 0)
    .map((one) => el('a', { class: 'chip', href: tabHref(one.tab) }, [
      el('span', { class: 'dot-sm', 'data-tone': one.tone }),
      el('span', { class: 'rowlist-line', text: one.say(Number(open[one.key])) }),
      icon('chevronRight', 16),
    ]));
  if (rows.length === 0) {
    return card('Needs a human', [sayNothing('Nothing is waiting on a person right now.')], { flush: true });
  }
  return card('Needs a human', rows, { count: rows.length, flush: true });
}

function verbOf(kind) {
  const last = String(kind || '').split('.').pop();
  const would = last.startsWith('would_');
  const stem = (would ? last.slice('would_'.length) : last).replace(/_/g, ' ');
  return { would, stem, failed: last.endsWith('failed') };
}

function sentence(row) {
  const { would, stem } = verbOf(row.kind);
  const node = el('span', { class: 'actline-text', text: would ? `would have ${stem}` : stem });
  if (row.target_name || row.target_id) node.append(' ', nameNode(row.target_id, row.target_name));
  if (row.reason) node.append(` — ${row.reason}`);
  if (row.actor_name || row.actor_id) node.append(' — by ', nameNode(row.actor_id, row.actor_name));
  return node;
}

function actionsCard(rows) {
  if (rows.length === 0) {
    return card('Last actions', [sayNothing('Black Bloc has not logged anything yet.')], { flush: true });
  }
  const lines = rows.map((row) => {
    const said = verbOf(row.kind);
    const at = shortWhen(row.at);
    return el('div', {
      class: 'actline',
      'data-tone': said.failed ? 'failed' : (said.would ? 'would' : undefined),
    }, [
      el('span', { class: 'actline-at', text: at.text, title: at.title }),
      sentence(row),
    ]);
  });
  return card('Last actions', lines, {
    actions: [el('a', { href: tabHref('audit'), text: 'All' })],
    flush: true,
  });
}

async function load() {
  const [status, actions] = await Promise.all([
    shellStatus(),
    api('/api/actions?limit=10'),
  ]);
  const rows = listOf(actions, 'actions');
  await names(idsIn(rows, ['actor_id', 'target_id']));

  const notes = notesOf(status || {}).concat(notesOf(actions));
  document.getElementById('dash').replaceChildren(
    ...(notes.length ? [el('p', { class: 'section-note', text: notes.join(' ') })] : []),
    el('div', { class: 'twocol' }, [
      featuresCard(status),
      el('div', { class: 'colstack' }, [needsCard(status), actionsCard(rows)]),
    ]),
  );
}

start({ tab: 'overview', load });
