import { el } from './ui.js';

const SECTIONS_KEY = (tab) => `bb_sections_${tab}`;
const TAB_KEY = 'bb_last_tab';
const ACTIVE_LINE = 160;

export function remembered(key) {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const found = JSON.parse(raw);
    return found && typeof found === 'object' && !Array.isArray(found) ? found : null;
  } catch (e) {
    return null;
  }
}

export function remember(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch (e) {
    /* private mode, a full quota, storage switched off — the page still works */
  }
}

export function rememberTab(tab) {
  try {
    localStorage.setItem(TAB_KEY, String(tab));
  } catch (e) {
    /* same guard as remember() */
  }
}

export function lastTab() {
  try {
    return localStorage.getItem(TAB_KEY);
  } catch (e) {
    return null;
  }
}

function countIn(node) {
  const tables = node.querySelectorAll('.log-table tbody');
  if (tables.length) {
    let found = 0;
    for (const body of tables) found += body.children.length;
    return found;
  }
  const rows = node.querySelectorAll('ul.rows > li, .chipgrid > *, .tiles > *, .msglist > li');
  return rows.length || null;
}

function paintCount(node) {
  if (node.hasAttribute('data-count')) return Number(node.getAttribute('data-count'));
  const found = countIn(node);
  if (found === null) return null;
  const label = node.querySelector('.sect-count');
  if (label) {
    label.textContent = String(found);
    label.hidden = false;
  }
  node.setAttribute('data-count', String(found));
  return found;
}

/**
 * First section open, the rest shut, unless this page remembers otherwise.
 * data-open="1" outranks both: it marks a panel the person just asked for —
 * an opened case, a ticket, the menu editor — and shutting that would undo
 * the click that made it.
 */
function apply(sections, saved) {
  sections.forEach((node, at) => {
    const details = node.querySelector('details.sect-card');
    if (!details) return;
    if (node.getAttribute('data-open') === '1') {
      details.open = true;
      return;
    }
    const slug = node.getAttribute('data-sect');
    const known = saved && slug in saved ? saved[slug] === true : null;
    details.open = known === null ? at === 0 : known;
  });
}

function subnavLink(node, onGo) {
  const slug = node.getAttribute('data-sect');
  const count = node.getAttribute('data-count');
  const link = el('a', {
    class: 'subnav-link',
    href: `#sect-${slug}`,
    'data-for': slug,
    on: {
      click: (event) => {
        event.preventDefault();
        onGo(node);
      },
    },
  }, [
    el('span', { class: 'subnav-label', text: node.getAttribute('data-title') || slug }),
    count === null || count === undefined ? null : el('span', { class: 'subnav-count', text: count }),
  ]);
  return link;
}

function highlight(links, sections) {
  let active = sections[0] || null;
  for (const node of sections) {
    if (node.getBoundingClientRect().top <= ACTIVE_LINE) active = node;
  }
  const slug = active ? active.getAttribute('data-sect') : null;
  for (const link of links) {
    if (link.getAttribute('data-for') === slug) link.setAttribute('aria-current', 'true');
    else link.removeAttribute('aria-current');
  }
}

/**
 * Puts the sub-navigation back in step with the sections after something has
 * hidden or re-counted them — the settings filter is the one caller today. A
 * link to a section that is not on the page any more is a link that lies.
 */
export function syncSubnav() {
  const nav = document.getElementById('subnav');
  const dash = document.getElementById('dash');
  if (!nav || !dash) return;
  for (const link of nav.querySelectorAll('.subnav-link')) {
    const slug = link.getAttribute('data-for');
    const node = dash.querySelector(`section.sect[data-sect="${slug}"]`);
    if (!node) continue;
    link.hidden = node.hidden;
    const label = link.querySelector('.subnav-count');
    const value = node.getAttribute('data-count');
    if (label && value !== null) label.textContent = value;
  }
}

const WIDE = '.twocol, .statgrid, .savebar, .section-note, .bar, .pager, .say-nothing';
const NEEDS_WIDTH = '.table-scroll, .grid-table, table';
const RUN_MIN = 2;

function wide(node) {
  const asked = node.getAttribute('data-span');
  if (asked) return asked === 'full';
  if (node.matches(WIDE)) return true;
  return Boolean(node.querySelector(NEEDS_WIDTH));
}

/**
 * Greedy longest-first-in-document-order balance: each block joins whichever
 * column is shorter right now. Heights are read BEFORE anything moves, because
 * wrapping changes every one of them.
 */
function balance(run) {
  const heights = run.map((node) => node.offsetHeight || 1);
  const left = el('div', { class: 'colstack' });
  const right = el('div', { class: 'colstack' });
  let leftAt = 0;
  let rightAt = 0;
  run.forEach((node, at) => {
    if (leftAt <= rightAt) {
      left.append(node);
      leftAt += heights[at];
    } else {
      right.append(node);
      rightAt += heights[at];
    }
  });
  return el('div', { class: 'twocol' }, [left, right]);
}

/**
 * Turns the page's stack of blocks into two columns so a wide window is not
 * half empty. A block that carries a table, a stat strip or a save bar spans
 * the full width and breaks the run, so the reading order stays whole-block by
 * whole-block. Must run AFTER #dash is shown — a hidden element measures zero
 * and the balance would be meaningless.
 */
export function mountColumns() {
  const dash = document.getElementById('dash');
  if (!dash || dash.hidden) return;
  const kids = [...dash.children];
  if (kids.length < RUN_MIN) return;
  const blocks = [];
  let run = [];
  const flush = () => {
    if (run.length >= RUN_MIN) blocks.push(balance(run));
    else blocks.push(...run);
    run = [];
  };
  for (const node of kids) {
    if (wide(node)) {
      flush();
      blocks.push(node);
    } else {
      run.push(node);
    }
  }
  flush();
  dash.replaceChildren(...blocks);
}

let watching = null;

/**
 * Reads whatever the page module just put in #dash, gives every section its
 * remembered open state and a count, and rebuilds the in-page sub-navigation.
 * Safe to call after every load — nothing is retained between calls but the
 * localStorage entry.
 */
export function mountSections(tab) {
  const dash = document.getElementById('dash');
  const nav = document.getElementById('subnav');
  if (!dash || !nav) return;

  const sections = [...dash.querySelectorAll('section.sect')];
  if (sections.length === 0) {
    nav.replaceChildren();
    nav.hidden = true;
    return;
  }

  const key = SECTIONS_KEY(tab);
  const saved = remembered(key);
  apply(sections, saved);
  const store = saved || {};
  for (const node of sections) paintCount(node);

  const links = [];
  const go = (node) => {
    const details = node.querySelector('details.sect-card');
    if (details && !details.open) details.open = true;
    node.scrollIntoView({ behavior: 'smooth', block: 'start' });
    highlight(links, sections);
  };

  for (const node of sections) {
    const link = subnavLink(node, go);
    links.push(link);
    const details = node.querySelector('details.sect-card');
    if (!details) continue;
    details.addEventListener('toggle', () => {
      store[node.getAttribute('data-sect')] = details.open;
      remember(key, store);
      highlight(links, sections);
    });
  }

  const all = (open) => {
    for (const node of sections) {
      const details = node.querySelector('details.sect-card');
      if (details) details.open = open;
    }
  };

  nav.replaceChildren(
    el('p', { class: 'subnav-head', text: 'On this page' }),
    el('div', { class: 'subnav-links' }, links),
    el('div', { class: 'subnav-bar' }, [
      el('button', { class: 'btn quiet small', type: 'button', text: 'Expand all', on: { click: () => all(true) } }),
      el('button', { class: 'btn quiet small', type: 'button', text: 'Collapse all', on: { click: () => all(false) } }),
    ]),
  );
  nav.hidden = false;

  if (watching) window.removeEventListener('scroll', watching);
  let queued = false;
  watching = () => {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => {
      queued = false;
      highlight(links, sections);
    });
  };
  window.addEventListener('scroll', watching, { passive: true });
  highlight(links, sections);
}
