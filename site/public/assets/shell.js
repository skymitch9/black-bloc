import { api } from './api.js';
import { duration, el } from './ui.js';

export const GROUPS = [
  {
    head: 'Overview',
    items: [
      { tab: 'overview', label: 'Overview' },
      { tab: 'health', label: 'Health' },
      { tab: 'audit', label: 'Audit log' },
    ],
  },
  {
    head: 'Moderation',
    items: [
      { tab: 'moderation', label: 'Moderation' },
      { tab: 'automod', label: 'Automod', feature: 'automod' },
      { tab: 'honeypot', label: 'Honeypot', feature: 'honeypot' },
      { tab: 'modmail', label: 'Modmail', feature: 'modmail' },
    ],
  },
  {
    head: 'Community',
    items: [
      { tab: 'golive', label: 'Go-live', feature: 'golive' },
      { tab: 'events', label: 'Events', feature: 'events' },
      { tab: 'birthdays', label: 'Birthdays', feature: 'birthday' },
      { tab: 'tempvoice', label: 'Temp voice', feature: 'tempvoice' },
      { tab: 'rolemenus', label: 'Role menus', feature: 'rolemenu' },
    ],
  },
  {
    head: 'Server',
    items: [{ tab: 'settings', label: 'Settings' }],
  },
];

const at = (id) => document.getElementById(id);

let statusOnce = null;

export function shellStatus() {
  if (statusOnce === null) statusOnce = api('/api/status').catch(() => null);
  return statusOnce;
}

export function forgetShellStatus() {
  statusOnce = null;
}

export function renderNav(current, hrefFor) {
  const nav = at('tabnav');
  if (!nav) return;
  nav.replaceChildren(...GROUPS.map((group) => el('div', { class: 'nav-group' }, [
    el('div', { class: 'nav-head', text: group.head.toUpperCase() }),
    ...group.items.map((item) => el('a', {
      class: 'nav-link',
      href: hrefFor(item.tab),
      'data-tab': item.tab,
      'data-feature': item.feature || undefined,
      'aria-current': item.tab === current ? 'page' : undefined,
    }, [
      el('span', { class: 'nav-label', text: item.label }),
      item.feature ? el('span', { class: 'nav-dot', 'data-tab': item.tab, hidden: true }) : null,
    ])),
  ])));
}

function paintDots(status) {
  const modes = new Map();
  for (const row of (status && status.features) || []) modes.set(row.feature, row.mode);
  for (const dot of document.querySelectorAll('.nav-dot')) {
    const link = dot.closest('.nav-link');
    const feature = link ? link.getAttribute('data-feature') : null;
    const mode = feature && modes.has(feature) ? modes.get(feature) : null;
    if (mode === null || mode === undefined || mode === '') {
      dot.hidden = true;
      continue;
    }
    const shown = String(mode) === 'thread' || String(mode) === 'channel' ? 'on' : String(mode);
    dot.setAttribute('data-mode', shown);
    dot.setAttribute('title', `${link.querySelector('.nav-label').textContent} is ${mode}`);
    dot.hidden = false;
  }
}

function paintHealth(status) {
  const pill = at('health-pill');
  const text = at('health-text');
  const dot = pill ? pill.querySelector('.dot-sm') : null;
  if (!pill || !text) return;
  if (!status || !status.bot) {
    text.textContent = 'health not known';
    if (dot) dot.setAttribute('data-tone', 'warn');
    pill.hidden = false;
    return;
  }
  const up = status.bot.uptime_seconds;
  text.textContent = status.bot.ready
    ? `online · ${duration(up)}`
    : 'not connected to Discord';
  if (dot) dot.setAttribute('data-tone', status.bot.ready ? 'ok' : 'danger');
  pill.hidden = false;
}

function paintGuild(status, me) {
  const node = at('topbar-guild');
  if (!node) return;
  const guild = (status && status.guild) || (me && me.guild) || null;
  if (guild && guild.name) node.textContent = guild.name;
}

function paintUser(me) {
  const chip = at('user-chip');
  if (!chip) return;
  const name = me && me.user ? me.user.name : null;
  if (!name) {
    chip.hidden = true;
    return;
  }
  at('user-initial').textContent = String(name).trim().charAt(0).toUpperCase() || '?';
  at('user-name').textContent = name;
  chip.hidden = false;
}

function toggle(button, panel, open) {
  panel.hidden = !open;
  button.setAttribute('aria-expanded', open ? 'true' : 'false');
}

function wireUserMenu() {
  const chip = at('user-chip');
  const menu = at('user-menu');
  if (!chip || !menu) return;
  chip.addEventListener('click', () => toggle(chip, menu, menu.hidden));
  document.addEventListener('pointerdown', (event) => {
    if (menu.hidden) return;
    if (menu.contains(event.target) || chip.contains(event.target)) return;
    toggle(chip, menu, false);
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !menu.hidden) {
      toggle(chip, menu, false);
      chip.focus();
    }
  });
}

function wireSidebar() {
  const button = at('side-toggle');
  const side = at('side');
  const scrim = at('scrim');
  if (!button || !side || !scrim) return;
  const set = (open) => {
    side.setAttribute('data-open', open ? 'true' : 'false');
    button.setAttribute('aria-expanded', open ? 'true' : 'false');
    scrim.hidden = !open;
  };
  set(false);
  button.addEventListener('click', () => set(side.getAttribute('data-open') !== 'true'));
  scrim.addEventListener('click', () => set(false));
  side.addEventListener('click', (event) => {
    if (event.target.closest('a')) set(false);
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') set(false);
  });
}

export function mountShell() {
  wireUserMenu();
  wireSidebar();
}

export async function paintShell(me) {
  paintUser(me);
  const status = await shellStatus();
  paintDots(status);
  paintHealth(status);
  paintGuild(status, me);
  return status;
}
