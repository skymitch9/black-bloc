import { api, Outage, signInHref } from './api.js';
import { lastTab, mountSections, rememberTab } from './layout.js';

export const TABS = [
  { tab: 'overview', href: '/index.html', label: 'Overview' },
  { tab: 'moderation', href: '/moderation.html', label: 'Moderation' },
  { tab: 'automod', href: '/automod.html', label: 'Automod' },
  { tab: 'modmail', href: '/modmail.html', label: 'Modmail' },
  { tab: 'events', href: '/events.html', label: 'Events' },
  { tab: 'golive', href: '/golive.html', label: 'Go-live' },
  { tab: 'rolemenus', href: '/rolemenus.html', label: 'Role menus' },
  { tab: 'birthdays', href: '/birthdays.html', label: 'Birthdays' },
  { tab: 'tempvoice', href: '/tempvoice.html', label: 'Temp voice' },
  { tab: 'honeypot', href: '/honeypot.html', label: 'Honeypot' },
  { tab: 'settings', href: '/settings.html', label: 'Settings' },
  { tab: 'audit', href: '/audit.html', label: 'Audit' },
  { tab: 'health', href: '/health.html', label: 'Health' },
];

export const FEATURE_TABS = {
  golive: 'golive',
  tempvoice: 'tempvoice',
  honeypot: 'honeypot',
  events: 'events',
  birthday: 'birthdays',
  modmail: 'modmail',
  automod: 'automod',
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

function renderNav(current) {
  const nav = el('tabnav');
  if (!nav) return;
  const links = TABS.map((entry) => {
    const link = document.createElement('a');
    link.setAttribute('href', entry.href);
    link.textContent = entry.label;
    if (entry.tab === current) link.setAttribute('aria-current', 'page');
    return link;
  });
  nav.replaceChildren(...links);
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

export function start(page) {
  if (restoreTab(page.tab)) return () => {};
  renderNav(page.tab);
  rememberTab(page.tab);

  let current = null;

  const reload = async () => {
    try {
      await page.load(current);
      mountSections(page.tab);
      stamp();
      show('dash');
    } catch (error) {
      handle(error);
    }
  };

  const boot = async () => {
    const complaint = returnedFromDiscord();
    show('gate');
    try {
      const me = await api('/api/auth/me');
      current = me;
      if (me.state === 'staff_unknown') {
        refuse({
          title: UNKNOWN_TITLE,
          message: me.message,
          note: `Signed in as ${me.user.name}.`,
          state: 'info',
          canRetry: true,
        });
        return;
      }
      if (!me.staff) {
        refuse({
          title: 'This dashboard is for staff',
          message: me.message,
          note: `Signed in as ${me.user.name}.`,
          state: 'warn',
        });
        return;
      }
      const subtitle = el('subtitle');
      if (subtitle && page.subtitle) {
        subtitle.textContent = `${page.subtitle} Signed in as ${me.user.name}${me.guild ? ` · ${me.guild.name}` : ''}.`;
      }
      await page.load(me);
      mountSections(page.tab);
      stamp();
      show('dash');
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
