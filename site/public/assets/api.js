import { describeHttpFailure, isPermissionStatus } from './permission-ux.js';

const API = (document.querySelector('meta[name="api-origin"]')?.content || '').replace(/\/$/, '');
const TIMEOUT_MS = 10000;
const NAME_BATCH = 80;

export class Outage extends Error {}

export const READ_ONLY_SAID = 'You can look at this page but not change it, so nothing was changed. Ask staff to make the change for you, or a Lead for a staff role.';
const READ_METHODS = ['GET', 'HEAD'];
let readOnly = null;

/** Set once per page for a member who may only look: writes stop here and staff-only reads are skipped. */
export function setReadOnly(state) {
  readOnly = state || null;
}

export function readOnlyState() {
  return readOnly;
}

function readOnlyRefusal() {
  const error = new Error(READ_ONLY_SAID);
  error.status = 403;
  error.code = 'read_only';
  error.isPermission = true;
  return error;
}

export function signInHref() {
  const here = `${location.pathname}${location.search}${location.hash}`;
  return `${API}/api/auth/login?next=${encodeURIComponent(here)}`;
}

/** For the handful of links a person follows rather than the page fetching. */
export function apiHref(path) {
  return `${API}${path}`;
}

export async function api(path, options = {}) {
  const method = String(options.method || 'GET').toUpperCase();
  if (readOnly && !READ_METHODS.includes(method) && !String(path).startsWith('/api/auth/')) throw readOnlyRefusal();
  const abort = new AbortController();
  const timer = setTimeout(() => abort.abort(), TIMEOUT_MS);
  let response;
  try {
    response = await fetch(`${API}${path}`, {
      credentials: 'same-origin',
      signal: abort.signal,
      ...options,
    });
  } catch (e) {
    throw new Outage(String(e));
  } finally {
    clearTimeout(timer);
  }
  let body = null;
  try {
    body = await response.json();
  } catch (e) {
    body = null;
  }
  if (!response.ok) {
    const error = new Error(body?.message || describeHttpFailure(response.status, body));
    error.status = response.status;
    error.code = body?.error || null;
    error.isPermission = isPermissionStatus(response.status);
    throw error;
  }
  return body;
}

export function send(path, method, body) {
  return api(path, {
    method,
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body === undefined ? {} : body),
  });
}

export function listOf(payload, key) {
  if (Array.isArray(payload)) return payload;
  if (!payload || typeof payload !== 'object') return [];
  if (Array.isArray(payload[key])) return payload[key];
  if (Array.isArray(payload.items)) return payload.items;
  if (Array.isArray(payload.results)) return payload.results;
  if (Array.isArray(payload.rows)) return payload.rows;
  return [];
}

export function notesOf(payload) {
  const notes = payload && payload.notes;
  return Array.isArray(notes) ? notes.filter((note) => typeof note === 'string') : [];
}

const nameCache = new Map();

export function nameRecord(id) {
  if (id === null || id === undefined) return null;
  return nameCache.get(String(id)) || null;
}

export async function names(ids) {
  const wanted = [];
  for (const raw of ids || []) {
    if (raw === null || raw === undefined || raw === '') continue;
    const id = String(raw);
    if (nameCache.has(id) || wanted.includes(id)) continue;
    wanted.push(id);
  }
  for (let at = 0; at < wanted.length; at += NAME_BATCH) {
    const chunk = wanted.slice(at, at + NAME_BATCH);
    let payload = null;
    let failed = false;
    try {
      payload = await api(`/api/ref/names?ids=${chunk.map(encodeURIComponent).join(',')}`);
    } catch (e) {
      failed = true;
    }
    for (const id of chunk) {
      const found = payload && typeof payload === 'object' ? payload[id] : null;
      if (found && (found.display_name || found.name)) {
        nameCache.set(id, {
          name: found.name || null,
          display_name: found.display_name || null,
          kind: found.kind || 'unknown',
          looked_up: true,
        });
      } else {
        nameCache.set(id, { name: null, display_name: null, kind: 'unknown', looked_up: !failed });
      }
    }
  }
  return nameCache;
}

export function forgetNames() {
  nameCache.clear();
}

let channelsCache = null;
let rolesCache = null;

export async function refChannels() {
  if (channelsCache === null) channelsCache = listOf(await api('/api/ref/channels'), 'channels');
  return channelsCache;
}

export async function refRoles() {
  if (rolesCache === null) rolesCache = listOf(await api('/api/ref/roles'), 'roles');
  return rolesCache;
}

export async function refMembers(query) {
  const found = await api(`/api/ref/members?q=${encodeURIComponent(query || '')}&limit=25`);
  return listOf(found, 'members');
}

export async function refSports(kind, league, query) {
  const params = new URLSearchParams({ kind: kind || 'team', league: league || '', q: query || '' });
  return listOf(await api(`/api/ref/sports?${params}`), 'names');
}

export function forgetRefs() {
  channelsCache = null;
  rolesCache = null;
}

let settingsCache = null;

export async function settings(fresh = false) {
  if (readOnly && !readOnly.settings) return {};
  if (fresh || settingsCache === null) settingsCache = await api('/api/settings');
  return settingsCache;
}

export function settingsNamespace(payload, namespace) {
  if (!payload || typeof payload !== 'object') return [];
  const group = payload[namespace];
  return Array.isArray(group) ? group : [];
}

const CONFIRM_NEEDED = 'confirm_needed';
let confirmer = null;

/** The page's way to ask "are you sure?" when the bot answers a change with a count first. */
export function setConfirmer(ask) {
  confirmer = ask;
}

async function againIfConfirmed(error, retry) {
  if (error?.status !== 409 || error?.code !== CONFIRM_NEEDED || !confirmer) throw error;
  if (!(await confirmer(error.message))) throw error;
  return retry();
}

export async function saveSetting(key, value) {
  const path = `/api/settings/${encodeURIComponent(key)}`;
  const stored = await send(path, 'PUT', { value })
    .catch((error) => againIfConfirmed(error, () => send(path, 'PUT', { value, confirm: true })));
  settingsCache = null;
  return stored;
}

export async function clearSetting(key) {
  const path = `/api/settings/${encodeURIComponent(key)}`;
  const stored = await api(path, { method: 'DELETE' })
    .catch((error) => againIfConfirmed(error, () => api(`${path}?confirm=true`, { method: 'DELETE' })));
  settingsCache = null;
  return stored;
}
