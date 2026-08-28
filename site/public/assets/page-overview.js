import { api, listOf, names, notesOf, settings } from './api.js';
import { FEATURE_TABS, start, tabHref } from './app.js';
import { GROUPS, shellStatus } from './shell.js';
import { card, el, icon, idsIn, modeSwitch, nameNode, notice, sayNothing, shortWhen } from './ui.js';

const many = (n, one, more) => `${n} ${Number(n) === 1 ? one : more}`;

const OPEN_NOTE = {
  rolemenu: (open) => `${many(open.role_menus_posted, 'menu', 'menus')} posted`,
  tempvoice: (open) => `${many(open.temp_channels, 'room', 'rooms')} open`,
  honeypot: (open) => `${many(open.honeypot_hits_7d, 'trip', 'trips')} in 7 days`,
  events: (open) => `${many(open.open_events, 'event', 'events')} waiting`,
  modmail: (open) => `${many(open.open_modmail, 'open ticket', 'open tickets')}`,
};

const NEEDS = [
  { key: 'open_events', tone: 'warn', tab: 'events', say: (n) => `${n} event${n === 1 ? '' : 's'} waiting on a Lead` },
  { key: 'open_modmail', tone: 'info', tab: 'modmail', say: (n) => `${n} open modmail${n === 1 ? '' : 's'}` },
  { key: 'honeypot_hits_7d', tone: 'danger', tab: 'honeypot', say: (n) => `${n} honeypot trip${n === 1 ? '' : 's'} in 7 days` },
];

/**
 * The sidebar already carries a human name for every feature; the raw feature
 * id ("golive", "rolemenu") is never what a person should read.
 */
const NAV_LABEL = new Map(GROUPS.flatMap((group) => group.items
  .filter((item) => item.feature)
  .map((item) => [item.feature, item.label])));
const NAV_AT = [...NAV_LABEL.keys()];

function title(feature) {
  return NAV_LABEL.get(feature) || String(feature).replace(/^./, (c) => c.toUpperCase());
}

/** Show the features in the order the sidebar lists them, not registry order. */
function inNavOrder(rows) {
  return [...rows].sort((a, b) => {
    const at = NAV_AT.indexOf(a.feature);
    const bt = NAV_AT.indexOf(b.feature);
    return (at < 0 ? NAV_AT.length : at) - (bt < 0 ? NAV_AT.length : bt);
  });
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

/** The row's own switch, or the plain badge when the bot registers no key for it. */
function modeNode(row, specs, say) {
  const spec = specs.get(row.key);
  if (!spec || !Array.isArray(spec.choices) || spec.choices.length === 0) {
    const blank = row.mode === null || row.mode === undefined || row.mode === '';
    return el('span', { class: 'pill', 'data-mode': pillMode(row.mode), text: blank ? 'not set' : String(row.mode) });
  }
  return modeSwitch(spec, { say, label: title(row.feature) }).node;
}

function featureRow(row, open, specs, say) {
  const tab = FEATURE_TABS[row.feature];
  const said = featureNote(row.feature, open);
  const name = el('span', { class: 'rowlist-name', text: title(row.feature) });
  const main = el(tab ? 'a' : 'div', {
    class: 'rowlist-main',
    href: tab ? tabHref(tab) : undefined,
  }, [name, said ? el('span', { class: 'rowlist-note', text: said }) : null]);
  return el('div', { class: 'chip' }, [
    main,
    modeNode(row, specs, say),
    tab ? el('a', { class: 'chip-go', href: tabHref(tab), 'aria-label': `Open ${title(row.feature)}` }, [icon('chevronRight', 16)]) : null,
  ]);
}

function featuresCard(status, payload) {
  const rows = (status && status.features) || [];
  if (rows.length === 0) {
    return card('Features', [sayNothing('No feature reports a mode yet.')], { flush: true });
  }
  const specs = new Map();
  for (const group of Object.values(payload || {})) {
    for (const spec of Array.isArray(group) ? group : []) specs.set(spec.key, spec);
  }
  const say = notice();
  return card('Features', [
    ...inNavOrder(rows).map((row) => featureRow(row, status.open, specs, say)),
    say,
  ], { count: rows.length, flush: true });
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

/**
 * `web.modmail.snippet` reads as "modmail snippet", not "snippet": the leading
 * `web.` says only where the click came from, and the segments after it are the
 * sentence. `would_` and `_failed` carry the shadow and failure tones.
 */
function verbOf(kind) {
  const parts = String(kind || '').split('.').filter(Boolean);
  if (parts[0] === 'web') parts.shift();
  const last = parts[parts.length - 1] || '';
  const would = last.startsWith('would_');
  if (would) parts[parts.length - 1] = last.slice('would_'.length);
  return {
    would,
    failed: last.endsWith('failed'),
    stem: parts.join(' ').replace(/_/g, ' ').trim() || String(kind),
  };
}

function sentence(row) {
  const { would, stem } = verbOf(row.kind);
  const node = el('span', { class: 'actline-text', text: would ? `would have ${stem}` : stem });
  if (row.target_name || row.target_id) node.append(' ', nameNode(row.target_id, row.target_name));
  if (row.reason) node.append(` — ${row.reason}`);
  if (row.actor_name || row.actor_id) node.append(' — by ', nameNode(row.actor_id, row.actor_name));
  return node;
}

const NOTHING_IMPORTANT = 'Nothing important has happened — nothing has acted on a member ' +
  'or failed. The Logs page has the routine lines.';

/** Overview shows only what acted on somebody; the Logs page shows the rest. */
function allLink() {
  return el('a', {
    href: tabHref('audit'),
    title: 'Every line, important or routine, on the Logs page',
    text: 'All',
  });
}

function actionsCard(rows) {
  if (rows.length === 0) {
    return card('Last actions', [sayNothing(NOTHING_IMPORTANT)], {
      actions: [allLink()],
      flush: true,
    });
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
  return card('Last actions', lines, { actions: [allLink()], flush: true });
}

async function load() {
  const [status, actions, payload] = await Promise.all([
    shellStatus(),
    api('/api/actions?limit=10&important=1'),
    settings(true),
  ]);
  const rows = listOf(actions, 'actions');
  await names(idsIn(rows, ['actor_id', 'target_id']));

  const notes = notesOf(status || {}).concat(notesOf(actions));
  document.getElementById('dash').replaceChildren(
    ...(notes.length ? [el('p', { class: 'section-note', text: notes.join(' ') })] : []),
    el('div', { class: 'twocol' }, [
      featuresCard(status, payload),
      el('div', { class: 'colstack' }, [needsCard(status), actionsCard(rows)]),
    ]),
  );
}

start({ tab: 'overview', load });
