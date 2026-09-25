import { api, Outage, signInHref } from './api.js';
import { lastTab, mountColumns, mountSections, rememberTab } from './layout.js';
import { mountPalette } from './palette.js';
import { MEMBER_TAB, MEMBER_TABS, forgetShellStatus, isMemberOnly, mountShell, paintShell, renderNav } from './shell.js';
import { clearDock } from './ui.js';

export const TABS = [
  { tab: 'overview', href: '/index.html', label: 'Overview' },
  { tab: 'moderation', href: '/moderation.html', label: 'Moderation' },
  { tab: 'members', href: '/members.html', label: 'Members' },
  { tab: 'automod', href: '/automod.html', label: 'Automod' },
  { tab: 'modmail', href: '/modmail.html', label: 'Modmail' },
  { tab: 'events', href: '/events.html', label: 'Events' },
  { tab: 'raidtrain', href: '/raidtrain.html', label: 'Raid trains' },
  { tab: 'golive', href: '/golive.html', label: 'Go-live' },
  { tab: 'rolemenus', href: '/rolemenus.html', label: 'Role menus' },
  { tab: 'polls', href: '/polls.html', label: 'Polls' },
  { tab: 'chat', href: '/chat.html', label: 'Chat' },
  { tab: 'channels', href: '/channels.html', label: 'Channels' },
  { tab: 'birthdays', href: '/birthdays.html', label: 'Birthdays' },
  { tab: 'tempvoice', href: '/tempvoice.html', label: 'Temp voice' },
  { tab: 'honeypot', href: '/honeypot.html', label: 'Honeypot' },
  { tab: 'settings', href: '/settings.html', label: 'Settings' },
  { tab: 'audit', href: '/audit.html', label: 'Logs' },
  { tab: 'requests', href: '/requests.html', label: 'Requests' },
  { tab: 'health', href: '/health.html', label: 'Health' },
  { tab: 'guides', href: '/guides.html', label: 'Guides' },
  { tab: 'posts', href: '/posts.html', label: 'Posts' },
  { tab: 'minutes', href: '/minutes.html', label: 'Minutes' },
];

export const FEATURE_TABS = {
  golive: 'golive',
  pings: 'golive',
  tempvoice: 'tempvoice',
  honeypot: 'honeypot',
  events: 'events',
  raidtrain: 'raidtrain',
  marathon: 'events',
  birthday: 'birthdays',
  modmail: 'modmail',
  automod: 'automod',
  rolemenu: 'rolemenus',
  poll: 'polls',
  chat: 'chat',
  request: 'requests',
  guides: 'guides',
  posts: 'posts',
  minutes: 'minutes',
};

export function tabHref(tab) {
  return (TABS.find((entry) => entry.tab === tab) || TABS[0]).href;
}

const OUTAGE_TITLE = 'Black Bloc is not answering';
const OUTAGE = 'This page cannot reach Black Bloc right now. That is an outage, not a permission ' +
  'problem — your access is fine. The bot may be restarting; try again in a minute, and tell a ' +
  'Lead if it stays down.';

const SIGNED_OUT_TITLE = 'Sign in to see this';
const SIGNED_OUT = 'Sign in with the Discord account you moderate Black in a Flash! with, and ' +
  'this page will fill in.';

const UNKNOWN_TITLE = 'Your roles could not be checked';

const RETURNED = {
  denied: 'Discord sign-in was cancelled, so nobody was signed in. Start again when you are ready.',
  state: 'That sign-in could not be finished safely, so it was stopped. Nothing is wrong with ' +
    'your access — start again from this page rather than from an old link.',
  failed: 'Discord could not finish the sign-in. That is a fault on the way to Discord, not a ' +
    'permission problem — try again in a moment.',
};

const el = (id) => document.getElementById(id);

function show(which) {
  el('gate').hidden = which !== 'gate';
  el('dash').hidden = which !== 'dash';
  el('footbar').hidden = which !== 'dash';
  const zone = el('dockzone');
  if (zone) zone.hidden = which !== 'dash';
}

export function refuse({ title, message, note = null, state = null, canSignIn = false, canRetry = false }) {
  el('gate-row').setAttribute('data-state', state || '');
  el('gate-title').textContent = title;
  el('gate-message').textContent = message;
  el('gate-note').textContent = note || '';
  el('gate-note').hidden = !note;
  el('signin').hidden = !canSignIn;
  el('retry').hidden = !canRetry;
  el('gate-actions').hidden = !(canSignIn || canRetry);
  show('gate');
}

export function handle(error) {
  if (error instanceof Outage) {
    refuse({ title: OUTAGE_TITLE, message: OUTAGE, state: 'danger', canRetry: true });
    return;
  }
  if (error.code === 'session_expired') {
    refuse({ title: 'Your sign-in has expired', message: error.message, canSignIn: true });
    return;
  }
  if (error.code === 'not_signed_in') {
    refuse({ title: SIGNED_OUT_TITLE, message: SIGNED_OUT, canSignIn: true });
    return;
  }
  if (error.code === 'not_staff') {
    refuse({ title: 'This dashboard is for staff', message: error.message, state: 'warn' });
    return;
  }
  if (error.code === 'staff_unknown') {
    refuse({ title: UNKNOWN_TITLE, message: error.message, state: 'info', canRetry: true });
    return;
  }
  refuse({
    title: error.isPermission ? 'That was refused' : 'Something is wrong at the bot',
    message: error.message,
    state: error.isPermission ? 'warn' : 'danger',
    canRetry: !error.isPermission,
  });
}

/**
 * The rail remembers where you were. Arriving at the bare "/" with no deep
 * link is the one case that gets sent on to that tab; "/index.html" — which
 * is what the Overview link in the rail points at — always means Overview, so
 * there is a way back that the memory cannot take away.
 */
function restoreTab(current) {
  if (current !== 'overview') return false;
  if (location.pathname !== '/') return false;
  if (location.search || location.hash) return false;
  const wanted = lastTab();
  if (!wanted || wanted === 'overview') return false;
  const entry = TABS.find((one) => one.tab === wanted);
  if (!entry) return false;
  location.replace(entry.href);
  return true;
}

function returnedFromDiscord() {
  const outcome = new URLSearchParams(location.search).get('signin');
  if (outcome) history.replaceState(null, '', location.pathname);
  return outcome && outcome !== 'ok' ? RETURNED[outcome] || RETURNED.failed : null;
}

function stamp() {
  const at = el('checked');
  if (at) at.textContent = `loaded ${new Date().toLocaleTimeString()}`;
}

const ME_KEY = 'blackbloc.me';

export function rememberMe(me) {
  try {
    sessionStorage.setItem(ME_KEY, JSON.stringify({ me, at: new Date().toISOString() }));
  } catch (e) {
    forgetMe();
  }
}

export function forgetMe() {
  try {
    sessionStorage.removeItem(ME_KEY);
  } catch (e) {
    /* a browser that refuses session storage simply has no cache */
  }
}

export function rememberedMe() {
  try {
    const found = JSON.parse(sessionStorage.getItem(ME_KEY) || 'null');
    if (!found || !found.me) return null;
    return found.me.staff === true || found.me.member === true ? found.me : null;
  } catch (e) {
    return null;
  }
}

/**
 * True when this `me` is a gate rather than a dashboard; the gate is shown.
 * A signed-in MEMBER is neither: they are not staff, but Requests is theirs,
 * so they are sent there instead of being told the dashboard is not for them.
 */
function refuseFor(me, tab) {
  if (isMemberOnly(me)) {
    if (MEMBER_TABS.includes(tab)) return false;
    location.replace(tabHref(MEMBER_TAB));
    return true;
  }
  if (me.state === 'staff_unknown') {
    refuse({
      title: UNKNOWN_TITLE,
      message: me.message,
      note: `Signed in as ${me.user.name}.`,
      state: 'info',
      canRetry: true,
    });
    return true;
  }
  if (!me.staff) {
    refuse({
      title: 'This dashboard is for staff',
      message: me.message,
      note: `Signed in as ${me.user.name}.`,
      state: 'warn',
    });
    return true;
  }
  return false;
}

export function start(page) {
  if (restoreTab(page.tab)) return () => {};
  renderNav(page.tab, tabHref);
  mountShell();
  mountPalette();
  rememberTab(page.tab);

  let current = null;

  const reload = async () => {
    try {
      forgetShellStatus();
      await paintShell(current);
      clearDock();
      await page.load(current);
      mountSections(page.tab);
      stamp();
      show('dash');
      mountColumns();
    } catch (error) {
      handle(error);
    }
  };

  const paint = async (me) => {
    await paintShell(me);
    clearDock();
    await page.load(me);
    mountSections(page.tab);
    stamp();
    show('dash');
    mountColumns();
  };

  const verify = async () => {
    try {
      const me = await api('/api/auth/me');
      current = me;
      if (refuseFor(me, page.tab)) {
        forgetMe();
        return;
      }
      rememberMe(me);
      await paintShell(me);
    } catch (error) {
      forgetMe();
      handle(error);
    }
  };

  const ask = async () => {
    const me = await api('/api/auth/me');
    current = me;
    if (refuseFor(me, page.tab)) {
      forgetMe();
      return;
    }
    rememberMe(me);
    await paint(me);
  };

  const boot = async () => {
    const complaint = returnedFromDiscord();
    const known = rememberedMe();
    if (known) {
      current = known;
      try {
        await paint(known);
        verify();
        return;
      } catch (error) {
        forgetMe();
        current = null;
      }
    }
    show('gate');
    try {
      await ask();
    } catch (error) {
      handle(error);
      if (complaint) {
        el('gate-note').textContent = complaint;
        el('gate-note').hidden = false;
      }
    }
  };

  el('signin').setAttribute('href', signInHref());
  el('retry').addEventListener('click', boot);
  el('refresh').addEventListener('click', reload);
  el('signout').addEventListener('click', async () => {
    forgetMe();
    try {
      await api('/api/auth/logout', { method: 'POST' });
    } catch (e) {
      current = null;
    }
    refuse({ title: SIGNED_OUT_TITLE, message: SIGNED_OUT, canSignIn: true });
  });

  boot();
  return reload;
}
