import { api, listOf, names, notesOf, settings } from './api.js';
import { FEATURE_TABS, start, tabHref } from './app.js';
import { GROUPS, shellStatus } from './shell.js';
import { card, el, icon, idsIn, modeSwitch, nameNode, notice, sayNothing, shortWhen } from './ui.js';

const LIST_LAST = ' and ';

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
    return card('Features', [sayNothing('Nothing has told the bot what it is meant to be doing yet.')], { flush: true });
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

/** Clauses read as one sentence: "a, b and c". */
function joined(parts) {
  if (parts.length <= 1) return parts;
  const out = [];
  parts.forEach((part, at) => {
    if (at > 0) out.push(at === parts.length - 1 ? LIST_LAST : ', ');
    out.push(part);
  });
  return out;
}

function queueLink(one, count) {
  return el('a', { class: 'today-link', href: tabHref(one.tab), 'data-tone': one.tone }, [
    el('span', { class: 'dot-sm', 'data-tone': one.tone }),
    el('span', { text: one.say(count) }),
  ]);
}

function modesSaid(status) {
  const rows = (status && status.features) || [];
  const shadow = rows.filter((row) => String(row.mode) === 'shadow').length;
  const off = rows.filter((row) => String(row.mode) === 'off').length;
  if (shadow === 0 && off === 0) return null;
  const parts = [];
  if (shadow > 0) parts.push(`${shadow} ${shadow === 1 ? 'feature is' : 'features are'} watching without acting`);
  if (off > 0) parts.push(`${off} ${off === 1 ? 'is' : 'are'} switched off`);
  return `${parts.join(LIST_LAST)}.`;
}

/**
 * The Overview leads with a sentence rather than a grid of counters, and it is
 * the ONE home for "what wants a person" — the counter card it replaces said
 * the same numbers a second time.
 */
function todayStrip(status, rows) {
  const open = status && status.open;
  const said = el('p', { class: 'today-line' });
  if (!open) {
    said.append('The bot did not answer with its open counts, so today is left blank rather than ' +
      'shown as a row of zeros.');
    return el('div', { class: 'today', 'data-span': 'full', 'data-tone': 'unknown' }, [
      el('span', { class: 'today-head', text: 'Today' }),
      said,
    ]);
  }
  const failed = rows.filter((row) => verbOf(row.kind).failed).length;
  said.append(failed === 0
    ? 'Nothing’s on fire.'
    : `${failed} thing${failed === 1 ? '' : 's'} the bot tried has failed.`);
  const waiting = NEEDS
    .filter((one) => Number(open[one.key]) > 0)
    .map((one) => queueLink(one, Number(open[one.key])));
  if (waiting.length === 0) said.append(' Nothing is waiting on a person.');
  else said.append(' ', ...joined(waiting), '.');
  const modes = modesSaid(status);
  if (modes) said.append(` ${modes}`);
  return el('div', {
    class: 'today',
    'data-span': 'full',
    'data-tone': failed === 0 ? 'calm' : 'danger',
  }, [
    el('span', { class: 'today-head', text: 'Today' }),
    said,
  ]);
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

const NOTHING_IMPORTANT = 'Nothing’s happened worth waking anyone for — nothing has acted on a ' +
  'member, and nothing has failed. The routine lines are all on Logs.';

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
    todayStrip(status, rows),
    ...(notes.length ? [el('p', { class: 'section-note', text: notes.join(' ') })] : []),
    el('div', { class: 'twocol' }, [
      featuresCard(status, payload),
      el('div', { class: 'colstack' }, [actionsCard(rows)]),
    ]),
  );
}

start({ tab: 'overview', load });
