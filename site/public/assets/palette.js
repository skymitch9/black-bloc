import { LABELS } from './labels.js';
import { el, icon, setShowKeys } from './ui.js';

const SETTINGS_TAB = 'settings';
const SHOWN = 12;

/** Fired when a setting on THIS page is the thing that was picked. */
export const JUMP = 'bb-jump-to-setting';

let node = null;
let input = null;
let list = null;
let found = [];
let at = 0;

function railPages() {
  return [...document.querySelectorAll('.nav-link')]
    .filter((link) => !link.hidden && !link.closest('.nav-group[hidden]'))
    .map((link) => ({
      kind: 'Page',
      title: link.querySelector('.nav-label').textContent,
      note: link.getAttribute('href'),
      run: () => location.assign(link.getAttribute('href')),
    }));
}

function settingsHref(key) {
  const link = document.querySelector(`.nav-link[data-tab="${SETTINGS_TAB}"]`);
  return `${link ? link.getAttribute('href') : '/settings.html'}#${encodeURIComponent(key)}`;
}

/**
 * Every registry key, findable by its sentence label AND by its raw key — the
 * key is what somebody who knows the bot types, and the Show keys switch
 * hiding the sub-line does not take that away.
 */
function settingsEntries() {
  if (!document.querySelector(`.nav-link[data-tab="${SETTINGS_TAB}"]:not([hidden])`)) return [];
  return Object.entries(LABELS).map(([key, label]) => ({
    kind: 'Setting',
    title: label,
    note: key,
    run: () => {
      // Already looking at the row? Say so where it stands rather than
      // reloading the page out from under it.
      if (document.querySelector(`.setrow[data-key="${key}"]`)) {
        history.replaceState(null, '', `#${encodeURIComponent(key)}`);
        document.dispatchEvent(new CustomEvent(JUMP, { detail: { key } }));
        return;
      }
      location.assign(settingsHref(key));
    },
  }));
}

function modeActions() {
  const theme = window.estateTheme;
  if (!theme) return [];
  const modes = [
    ['Dark', 'dark'],
    ['Light', 'light'],
    ['Follow the system', 'auto'],
  ].map(([said, mode]) => ({
    kind: 'Do',
    title: `Appearance: ${said}`,
    note: 'this browser only',
    run: () => theme.setMode(mode),
  }));
  const themes = theme.themes.map((id) => ({
    kind: 'Do',
    title: `Theme: ${theme.label(id)}`,
    note: 'this browser only',
    run: () => theme.setTheme(id),
  }));
  return modes.concat(themes);
}

function doings() {
  const showing = document.documentElement.getAttribute('data-showkeys') === 'true';
  const out = [
    { kind: 'Do', title: 'Reload this page', note: 'ask the bot for everything again', run: () => location.reload() },
    {
      kind: 'Do',
      title: showing ? 'Hide the settings keys' : 'Show the settings keys',
      note: 'the mono key under each setting’s name',
      run: () => setShowKeys(!showing),
    },
  ];
  const out2 = document.getElementById('signout');
  if (out2) {
    out.push({ kind: 'Do', title: 'Sign out', note: 'ends this session', run: () => out2.click() });
  }
  return out.concat(modeActions());
}

function index() {
  return [...railPages(), ...settingsEntries(), ...doings()].map((entry) => ({
    ...entry,
    hay: `${entry.title} ${entry.note} ${entry.kind}`.toLowerCase(),
  }));
}

/** Whatever starts with what you typed comes first; a match in the middle still counts. */
function rank(entries, query) {
  if (query === '') return entries.slice(0, SHOWN);
  return entries
    .map((entry) => ({ entry, hit: entry.hay.indexOf(query) }))
    .filter((one) => one.hit >= 0)
    .sort((a, b) => a.hit - b.hit || a.entry.title.length - b.entry.title.length)
    .slice(0, SHOWN)
    .map((one) => one.entry);
}

function paintRows() {
  list.replaceChildren(...found.map((entry, index_) => el('button', {
    class: 'palette-row',
    type: 'button',
    'aria-selected': index_ === at ? 'true' : 'false',
    on: { click: () => run(index_) },
  }, [
    el('span', { class: 'palette-kind', text: entry.kind }),
    el('span', { class: 'palette-title', text: entry.title }),
    el('span', { class: 'palette-note', text: entry.note }),
  ])));
  const on = list.children[at];
  if (on) on.scrollIntoView({ block: 'nearest' });
}

function paint(entries) {
  const query = input.value.trim().toLowerCase();
  found = rank(entries, query);
  at = 0;
  if (found.length === 0) {
    list.replaceChildren(el('p', { class: 'say-nothing' }, [
      el('span', { class: 'say-nothing-text', text: 'Nothing here is called that.' }),
    ]));
    return;
  }
  paintRows();
}

function shut() {
  if (node && node.open) node.close();
}

function run(which) {
  const entry = found[which];
  if (!entry) return;
  shut();
  entry.run();
}

function move(by) {
  if (found.length === 0) return;
  at = (at + by + found.length) % found.length;
  paintRows();
}

function build() {
  input = el('input', {
    class: 'input palette-input',
    type: 'text',
    autocomplete: 'off',
    'aria-label': 'Search pages, settings and actions',
    placeholder: 'Go to a page, a setting, or do something…',
  });
  list = el('div', { class: 'palette-list', role: 'listbox' });
  node = el('dialog', { class: 'palette' }, [
    el('div', { class: 'palette-inner' }, [
      el('div', { class: 'palette-box' }, [icon('search', 16, 'search-mark'), input]),
      list,
      el('p', { class: 'palette-help', text: '↑ ↓ to move · Enter to go · Esc to close' }),
    ]),
  ]);
  node.addEventListener('click', (event) => {
    if (event.target === node) shut();
  });
  document.body.append(node);
}

function open() {
  if (node === null) build();
  if (node.open) return;
  const entries = index();
  input.value = '';
  input.oninput = () => paint(entries);
  input.onkeydown = (event) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      move(1);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      move(-1);
    } else if (event.key === 'Enter') {
      event.preventDefault();
      run(at);
    }
  };
  paint(entries);
  node.showModal();
  input.focus();
}

/** The hint that says the keybinding exists, beside the theme cog. */
function hint() {
  const bar = document.querySelector('.topbar');
  const cog = document.getElementById('hg-cog');
  if (!bar || bar.querySelector('.kbd-hint')) return;
  const said = navigator.platform && /mac/i.test(navigator.platform) ? '⌘ K' : 'Ctrl K';
  const button = el('button', {
    class: 'kbd-hint',
    type: 'button',
    title: 'Search pages, settings and actions',
    on: { click: open },
  }, [icon('search', 14, 'search-mark'), el('kbd', { text: said })]);
  if (cog) bar.insertBefore(button, cog);
  else bar.append(button);
}

export function mountPalette() {
  hint();
  document.addEventListener('keydown', (event) => {
    if (!(event.ctrlKey || event.metaKey) || event.altKey) return;
    if (String(event.key).toLowerCase() !== 'k') return;
    event.preventDefault();
    open();
  });
}
