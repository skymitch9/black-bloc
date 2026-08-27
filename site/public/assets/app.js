/**
 * app.js — the whole status page. Talks to the Black Bloc API and to nothing
 * else; the API origin comes from <meta name="api-origin">, never hardcoded.
 *
 * The four refusal states are the point of this file (global rule: nobody
 * sees a bare HTTP status). They are kept apart because their fixes differ:
 *   not signed in            → sign in
 *   signed in, not staff     → ask a Lead for the role
 *   session expired          → sign in again, nothing is wrong with access
 *   API unreachable          → an OUTAGE, never described as a permission
 *                              problem, and never given a "sign in" button
 * The API supplies the sentence for the first three, so the wording has one
 * home. Only the outage sentence lives here, because a dead API cannot
 * describe itself.
 */

import { describeHttpFailure, isPermissionStatus } from './permission-ux.js';

const API = (document.querySelector('meta[name="api-origin"]')?.content || '').replace(/\/$/, '');

const OUTAGE_TITLE = 'Black Bloc is not answering';
const OUTAGE = 'This page cannot reach Black Bloc right now. That is an outage, not a permission ' +
  'problem — your access is fine. The bot may be restarting; try again in a minute, and tell a ' +
  'Lead if it stays down.';

const SIGNED_OUT_TITLE = 'Sign in to see this';
const SIGNED_OUT = 'Sign in with the Discord account you moderate Black in a Flash! with, and ' +
  'this page will fill in.';

const RETURNED = {
  denied: 'Discord sign-in was cancelled, so nobody was signed in. Start again when you are ready.',
  state: 'That sign-in could not be finished safely, so it was stopped. Nothing is wrong with ' +
    'your access — start again from this page rather than from an old link.',
  failed: 'Discord could not finish the sign-in. That is a fault on the way to Discord, not a ' +
    'permission problem — try again in a moment.',
};

const el = (id) => document.getElementById(id);

const gate = el('gate');
const dash = el('dash');

function show(which) {
  gate.hidden = which !== 'gate';
  dash.hidden = which !== 'dash';
}

// state defaults to null — a neutral grey dot. Being signed out is not a
// warning and must not wear a warning's colour; only a real refusal (warn) or
// a real fault (danger) gets one.
function refuse({ title, message, note = null, state = null, canSignIn = false, canRetry = false }) {
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

class Outage extends Error {}

async function api(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API}${path}`, { credentials: 'include', ...options });
  } catch (e) {
    throw new Outage(String(e));
  }
  let body = null;
  try { body = await response.json(); } catch (e) { body = null; }
  if (!response.ok) {
    const error = new Error(body?.message || describeHttpFailure(response.status, body));
    error.status = response.status;
    error.code = body?.error || null;
    error.isPermission = isPermissionStatus(response.status);
    throw error;
  }
  return body;
}

function signInHref() {
  return `${API}/api/auth/login`;
}

// ---- rendering -------------------------------------------------------------

function row({ name, badge = null, badgeTone = null, detail = null, note = null, state = null }) {
  const li = document.createElement('li');
  li.className = 'row';
  if (state) li.setAttribute('data-state', state);

  const dot = document.createElement('span');
  dot.className = 'dot';
  li.appendChild(dot);

  const body = document.createElement('div');
  body.className = 'row-body';

  const head = document.createElement('div');
  head.className = 'row-head';
  const label = document.createElement('span');
  label.className = 'row-name';
  label.textContent = name;
  head.appendChild(label);
  if (badge !== null) {
    const chip = document.createElement('span');
    chip.className = badgeTone === 'mode' ? 'mode-chip' : 'badge';
    if (badgeTone === 'mode') chip.setAttribute('data-mode', badge);
    chip.textContent = badge;
    head.appendChild(chip);
  }
  body.appendChild(head);

  if (detail !== null) {
    const p = document.createElement('p');
    p.className = 'row-detail';
    p.textContent = detail;
    body.appendChild(p);
  }
  if (note !== null) {
    const p = document.createElement('p');
    p.className = 'row-note';
    p.textContent = note;
    body.appendChild(p);
  }
  li.appendChild(body);
  return li;
}

function fill(list, rows) {
  list.replaceChildren(...rows);
}

function duration(seconds) {
  if (seconds === null || seconds === undefined) return 'not known';
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (d) return `${d}d ${h}h`;
  if (h) return `${h}h ${m}m`;
  return `${m}m`;
}

function when(iso) {
  if (!iso) return '—';
  const at = new Date(iso);
  return Number.isNaN(at.getTime()) ? String(iso) : at.toLocaleString();
}

const COUNT_LABELS = {
  role_menus_posted: 'Role menus posted',
  temp_channels: 'Temporary voice channels open',
  honeypot_hits_7d: 'Honeypot hits, last 7 days',
  open_events: 'Events open',
};

function renderHealth(status) {
  const bot = status.bot;
  const rows = [
    row({
      name: 'Gateway',
      badge: bot.ready ? 'connected' : 'not ready',
      state: bot.ready ? 'ok' : 'danger',
      detail: bot.ready
        ? `${bot.latency_ms} ms to Discord · ${bot.guilds} server(s) · up ${duration(bot.uptime_seconds)}`
        : 'Black Bloc is running but has not finished connecting to Discord.',
      note: `Version ${bot.version}${bot.test_mode ? ' · TEST MODE: the bot speaks only in the test channel' : ''}`,
    }),
  ];
  if (status.open) {
    for (const [key, label] of Object.entries(COUNT_LABELS)) {
      rows.push(row({ name: label, badge: String(status.open[key]), state: 'ok' }));
    }
  }
  fill(el('health'), rows);

  const note = el('health-note');
  const notes = status.notes || [];
  note.textContent = notes.join(' ');
  note.hidden = notes.length === 0;
}

function renderFeatures(status) {
  const rows = status.features.map((feature) => row({
    name: feature.feature.replace(/^./, (c) => c.toUpperCase()),
    badge: feature.mode === null || feature.mode === undefined ? 'not set' : String(feature.mode),
    badgeTone: 'mode',
    state: feature.mode === 'on' ? 'ok' : feature.mode === 'shadow' ? 'warn' : null,
    detail: feature.mode === 'shadow' ? 'Logging what it would do, doing nothing.' : null,
  }));
  fill(el('features'), rows.length ? rows : [sayNothing('No features report a mode yet.')]);
}

function sayNothing(text) {
  const li = document.createElement('li');
  const p = document.createElement('p');
  p.className = 'say-nothing';
  p.textContent = text;
  li.appendChild(p);
  return li;
}

function renderLoops(status) {
  const rows = (status.loops || []).map((loop) => row({
    name: `${loop.cog} · ${loop.name}`,
    badge: loop.running ? 'running' : loop.failed ? 'stopped after an error' : 'stopped',
    state: loop.state,
    detail: loop.last_error
      ? `Last error: ${loop.last_error}`
      : loop.last_ok_at
        ? `Last success ${when(loop.last_ok_at)}`
        : 'This loop does not record its last success yet, so this is liveness, not health.',
    note: loop.next_iteration ? `Next run ${when(loop.next_iteration)}` : null,
  }));
  fill(el('loops'), rows.length ? rows : [sayNothing('No loops are loaded.')]);
}

function kindTone(kind) {
  if (kind.includes('would_')) return 'would';
  if (kind.includes('_failed')) return 'failed';
  return null;
}

function cell(text, className = null) {
  const td = document.createElement('td');
  if (className) td.className = className;
  td.textContent = text;
  return td;
}

function renderActions(payload) {
  const body = el('actions').querySelector('tbody');
  const rows = (payload.actions || []).map((action) => {
    const tr = document.createElement('tr');
    tr.appendChild(cell(when(action.at), 'mono'));

    const kind = document.createElement('td');
    const span = document.createElement('span');
    span.className = 'kind';
    const tone = kindTone(action.kind);
    if (tone) span.setAttribute('data-tone', tone);
    span.textContent = action.kind;
    kind.appendChild(span);
    tr.appendChild(kind);

    tr.appendChild(cell(action.actor_id || '—', 'mono'));
    tr.appendChild(cell(action.target_id || '—', 'mono'));
    tr.appendChild(cell(action.reason || '—', 'wrap'));
    return tr;
  });
  body.replaceChildren(...rows);

  const note = el('actions-note');
  if (!rows.length) {
    note.textContent = 'Black Bloc has not logged anything yet.';
    note.hidden = false;
  } else {
    note.hidden = true;
  }
}

// ---- the boot sequence -----------------------------------------------------

async function loadDashboard() {
  const [status, actions] = await Promise.all([api('/api/status'), api('/api/actions?limit=50')]);
  renderHealth(status);
  renderFeatures(status);
  renderLoops(status);
  renderActions(actions);
  el('checked').textContent = `checked ${when(status.checked_at)}`;
  show('dash');
}

function handle(error) {
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
  // Anything else — a 503 from the API, a database that cannot answer — is a
  // fault, so it gets a retry and never a permission sentence.
  refuse({
    title: error.isPermission ? 'That was refused' : 'Something is wrong at the bot',
    message: error.message,
    state: error.isPermission ? 'warn' : 'danger',
    canRetry: !error.isPermission,
  });
}

function returnedFromDiscord() {
  const outcome = new URLSearchParams(location.search).get('signin');
  if (outcome) history.replaceState(null, '', location.pathname);
  return outcome && outcome !== 'ok' ? RETURNED[outcome] || RETURNED.failed : null;
}

async function boot() {
  const complaint = returnedFromDiscord();
  try {
    const me = await api('/api/auth/me');
    if (!me.staff) {
      refuse({
        title: 'This dashboard is for staff',
        message: me.message,
        note: `Signed in as ${me.user.name}.`,
        state: 'warn',
      });
      return;
    }
    el('subtitle').textContent =
      `Signed in as ${me.user.name}${me.guild ? ` · ${me.guild.name}` : ''}. Read-only — nothing on this page changes anything.`;
    await loadDashboard();
  } catch (error) {
    handle(error);
    if (complaint) {
      el('gate-note').textContent = complaint;
      el('gate-note').hidden = false;
    }
  }
}

el('signin').setAttribute('href', signInHref());
el('retry').addEventListener('click', boot);
el('refresh').addEventListener('click', () => loadDashboard().catch(handle));
el('signout').addEventListener('click', async () => {
  try { await api('/api/auth/logout', { method: 'POST' }); } catch (e) { /* signing out locally is enough */ }
  refuse({ title: SIGNED_OUT_TITLE, message: SIGNED_OUT, canSignIn: true });
});

boot();
