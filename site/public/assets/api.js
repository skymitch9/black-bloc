import { describeHttpFailure, isPermissionStatus } from './permission-ux.js';

const API = (document.querySelector('meta[name="api-origin"]')?.content || '').replace(/\/$/, '');
const TIMEOUT_MS = 10000;
const NAME_BATCH = 80;

export class Outage extends Error {}

export function signInHref() {
  return `${API}/api/auth/login`;
}

export async function api(path, options = {}) {
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

export function forgetRefs() {
  channelsCache = null;
  rolesCache = null;
}

let settingsCache = null;

export async function settings(fresh = false) {
  if (fresh || settingsCache === null) settingsCache = await api('/api/settings');
  return settingsCache;
}

export function settingsNamespace(payload, namespace) {
  if (!payload || typeof payload !== 'object') return [];
  const group = payload[namespace];
  return Array.isArray(group) ? group : [];
}

export async function saveSetting(key, value) {
  const stored = await send(`/api/settings/${encodeURIComponent(key)}`, 'PUT', { value });
  settingsCache = null;
  return stored;
}

export async function clearSetting(key) {
  const stored = await api(`/api/settings/${encodeURIComponent(key)}`, { method: 'DELETE' });
  settingsCache = null;
  return stored;
}
