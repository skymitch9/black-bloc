import { api } from './api.js';
import { duration, el, icon } from './ui.js';

/** The pages a signed-in member who is not staff may use; the first is where they land. */
export const MEMBER_TABS = ['requests', 'guides'];
export const MEMBER_TAB = MEMBER_TABS[0];

export const GROUPS = [
  {
    head: 'Overview',
    items: [
      { tab: 'overview', label: 'Overview', icon: 'navOverview' },
      { tab: 'health', label: 'Health', icon: 'navHealth' },
      { tab: 'audit', label: 'Logs', icon: 'navLogs' },
      { tab: 'requests', label: 'Requests', icon: 'navRequests', feature: 'request', count: 'featurerequests' },
      { tab: 'guides', label: 'Guides', icon: 'navGuides', feature: 'guides' },
    ],
  },
  {
    head: 'Runs the server',
    items: [
      { tab: 'moderation', label: 'Moderation', icon: 'navModeration' },
      { tab: 'members', label: 'Members', icon: 'navMembers', count: 'members' },
      { tab: 'automod', label: 'Automod', icon: 'navAutomod', feature: 'automod' },
      { tab: 'honeypot', label: 'Honeypot', icon: 'navHoneypot', feature: 'honeypot' },
      { tab: 'modmail', label: 'Modmail', icon: 'navModmail', feature: 'modmail' },
    ],
  },
  {
    head: 'Runs the cookout',
    items: [
      { tab: 'golive', label: 'Go-live', icon: 'navGolive', feature: 'golive' },
      { tab: 'events', label: 'Events', icon: 'navEvents', feature: 'events' },
      { tab: 'birthdays', label: 'Birthdays', icon: 'navBirthdays', feature: 'birthday' },
      { tab: 'tempvoice', label: 'Temp voice', icon: 'navTempvoice', feature: 'tempvoice' },
      { tab: 'rolemenus', label: 'Role menus', icon: 'navRolemenus', feature: 'rolemenu', count: 'requests' },
      { tab: 'polls', label: 'Polls', icon: 'navPolls', feature: 'poll', count: 'polls' },
      { tab: 'chat', label: 'Chat', icon: 'navChat', feature: 'chat' },
    ],
  },
  {
    head: 'The desk',
    items: [{ tab: 'settings', label: 'Settings', icon: 'navSettings' }],
  },
];

const at = (id) => document.getElementById(id);

let statusOnce = null;
let membersOnce = null;
let requestsOnce = null;
let pollsOnce = null;
let featureOnce = null;
let guidesOnce = null;

/**
 * The hub payload, memoised so the rail and `page-guides.js` share ONE read.
 * It resolves rather than throws, because the rail asks it only to find out
 * whether guides are off for this person.
 */
export function guidesIndex() {
  if (guidesOnce === null) {
    guidesOnce = api('/api/guides').then(
      (payload) => ({ ok: true, payload, error: null }),
      (error) => ({ ok: false, payload: null, error }),
    );
  }
  return guidesOnce;
}

export function shellStatus() {
  if (statusOnce === null) statusOnce = api('/api/status').catch(() => null);
  return statusOnce;
}

export function memberTally() {
  if (membersOnce === null) membersOnce = api('/api/members?per_page=1').catch(() => null);
  return membersOnce;
}

/** Waiting role requests, for the badge beside Role menus. */
export function requestTally() {
  if (requestsOnce === null) {
    requestsOnce = api('/api/rolemenus/requests?status=pending')
      .then((found) => (Array.isArray(found) ? found.length : null))
      .catch(() => null);
  }
  return requestsOnce;
}

/** Polls still open, for the badge beside Polls. */
export function pollTally() {
  if (pollsOnce === null) {
    pollsOnce = api('/api/polls?status=open&per_page=1')
      .then((found) => (found && typeof found.total === 'number' ? found.total : null))
      .catch(() => null);
  }
  return pollsOnce;
}

/** Feature requests still waiting on an answer, for the badge beside Requests. */
export function featureRequestTally() {
  if (featureOnce === null) {
    featureOnce = api('/api/requests?status=pending&per_page=1')
      .then((found) => (found && typeof found.total === 'number' ? found.total : null))
      .catch(() => null);
  }
  return featureOnce;
}

export function forgetShellStatus() {
  statusOnce = null;
  membersOnce = null;
  requestsOnce = null;
  pollsOnce = null;
  featureOnce = null;
  guidesOnce = null;
}

export function renderNav(current, hrefFor) {
  const nav = at('tabnav');
  if (!nav) return;
  nav.replaceChildren(...GROUPS.map((group) => el('div', { class: 'nav-group' }, [
    el('div', { class: 'nav-head', text: group.head }),
    ...group.items.map((item) => el('a', {
      class: 'nav-link',
      href: hrefFor(item.tab),
      'data-tab': item.tab,
      'data-feature': item.feature || undefined,
      'aria-current': item.tab === current ? 'page' : undefined,
    }, [
      icon(item.icon, 16, 'nav-icon'),
      el('span', { class: 'nav-label', text: item.label }),
      item.feature ? el('span', { class: 'nav-dot', 'data-tab': item.tab, hidden: true }) : null,
      item.count ? el('span', { class: 'nav-count', 'data-count': item.count, hidden: true }) : null,
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

function paintCount(which, value, said) {
  for (const node of document.querySelectorAll(`.nav-count[data-count="${which}"]`)) {
    if (value === null) {
      node.hidden = true;
      continue;
    }
    node.textContent = String(value);
    node.setAttribute('title', said(value));
    node.setAttribute('data-tone', which === 'requests' && value > 0 ? 'warn' : 'quiet');
    node.hidden = false;
  }
}

function paintCounts(tally, waiting, running) {
  paintCount(
    'members',
    tally && typeof tally.total === 'number' ? tally.total : null,
    (total) => `${total} member${total === 1 ? '' : 's'} in the server`,
  );
  // A queue with nobody in it says nothing rather than a zero nobody has to act on.
  paintCount(
    'requests',
    typeof waiting === 'number' && waiting > 0 ? waiting : null,
    (found) => `${found} role request${found === 1 ? '' : 's'} waiting for staff`,
  );
  paintCount(
    'polls',
    typeof running === 'number' && running > 0 ? running : null,
    (found) => `${found} poll${found === 1 ? '' : 's'} still open`,
  );
}

/**
 * A signed-in member who is not staff gets Requests and Guides, because every
 * other page would refuse them. The nav is built before `me` arrives, so this
 * trims it rather than the renderer knowing who is looking.
 */
function paintNavFor(member) {
  for (const link of document.querySelectorAll('.nav-link')) {
    link.hidden = member && !MEMBER_TABS.includes(link.getAttribute('data-tab'));
  }
  paintGroups();
}

function paintGroups() {
  for (const group of document.querySelectorAll('.nav-group')) {
    group.hidden = ![...group.querySelectorAll('.nav-link')].some((link) => !link.hidden);
  }
}

function hideTab(tab) {
  for (const link of document.querySelectorAll(`.nav-link[data-tab="${tab}"]`)) {
    link.hidden = true;
  }
  paintGroups();
}

export function isMemberOnly(me) {
  return Boolean(me) && me.staff !== true && me.member === true;
}

export async function paintShell(me) {
  paintUser(me);
  paintNavFor(isMemberOnly(me));
  if (isMemberOnly(me)) {
    // Every tally below this line is a staff route, so a member is asked for none of them.
    paintCounts(null, null, null);
    paintCount('featurerequests', null, () => '');
    paintGuild(null, me);
    // guides_mode off answers this member 409 guides_off, so the rail stops offering it.
    const guides = await guidesIndex();
    if (!guides.ok) hideTab('guides');
    return null;
  }
  const [status, tally, waiting, running, asked] = await Promise.all([
    shellStatus(), memberTally(), requestTally(), pollTally(), featureRequestTally(),
  ]);
  paintDots(status);
  paintHealth(status);
  paintGuild(status, me);
  paintCounts(tally, waiting, running);
  paintCount(
    'featurerequests',
    typeof asked === 'number' && asked > 0 ? asked : null,
    (found) => `${found} request${found === 1 ? '' : 's'} waiting on an answer`,
  );
  return status;
}
