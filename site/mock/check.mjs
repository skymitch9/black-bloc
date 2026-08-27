// Checks a running mock against site/mock/contract.json: every page loads, and every
// route answers with the keys the pages read. The same table tests/api/test_contract.py
// runs against the real routers, so a shape can only be right in one half and wrong in
// the other if somebody edits one and not the file both read.
//
//   node site/mock/server.mjs &
//   node site/mock/check.mjs            (or MOCK_PORT=8788 node site/mock/check.mjs)
//
// Exits 0 when everything matched, 1 with a list of what did not.

import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const HERE = fileURLToPath(new URL('.', import.meta.url));
const PORT = Number(process.env.MOCK_PORT || 8788);
const BASE = `http://127.0.0.1:${PORT}`;

const contract = JSON.parse(await readFile(new URL('./contract.json', import.meta.url), 'utf8'));

// The mock's own fixture ids, so the {placeholders} in the table point at rows it has.
const IDS = {
  member_id: '700000000000000002',
  case_id: '9',
  event_id: '3',
  ticket_id: '5',
  hit_id: '7',
  test_channel_id: '800000000000000003',
  lobby_channel_id: '800000000000000009',
  plain_role_id: '900000000000000005',
  request_id: '4',
  grant_id: '5',
  poll_id: '3',
  poll_request_id: '2',
  poll_recurrence_id: '4',
};

const failures = [];
const fail = (where, said) => failures.push(`${where}: ${said}`);

function fill(text) {
  let found = text;
  for (const [name, value] of Object.entries(IDS)) found = found.split(`{${name}}`).join(value);
  return found;
}

function missing(found, keys) {
  if (found === null || typeof found !== 'object') return keys;
  return keys.filter((key) => !(key in found));
}

function checkRows(where, rows, keys) {
  if (!Array.isArray(rows)) {
    fail(where, `is ${rows === null ? 'null' : typeof rows}, not a list`);
    return;
  }
  if (rows.length === 0) {
    fail(where, 'came back empty, so its row shape was never checked');
    return;
  }
  for (const row of rows) {
    const gone = missing(row, keys);
    if (gone.length) fail(where, `row is missing ${gone.join(', ')}`);
  }
}

function check(where, payload, spec) {
  const keys = spec.keys || [];
  if (spec.shape === 'list') {
    checkRows(where, payload, keys);
  } else if (spec.shape === 'map') {
    const entries = Object.values(payload || {});
    if (entries.length === 0) fail(where, 'came back empty');
    for (const value of entries) {
      const gone = missing(value, keys);
      if (gone.length) fail(where, `entry is missing ${gone.join(', ')}`);
    }
  } else if (spec.shape === 'namespaces') {
    for (const namespace of spec.namespaces) {
      if (!(namespace in (payload || {}))) fail(where, `has no ${namespace} namespace`);
      else checkRows(`${where}[${namespace}]`, payload[namespace], keys);
    }
    for (const namespace of spec.no_namespaces) {
      if (namespace in (payload || {})) {
        fail(where, `still groups ${namespace} on its own; it belongs in automod`);
      }
    }
  } else {
    const gone = missing(payload, keys);
    if (gone.length) fail(where, `is missing ${gone.join(', ')}`);
  }
  for (const [field, rowKeys] of Object.entries(spec.rows || {})) {
    if (spec.shape === 'list') {
      for (const row of Array.isArray(payload) ? payload : []) {
        checkRows(`${where}.${field}`, row[field], rowKeys);
      }
    } else {
      checkRows(`${where}.${field}`, (payload || {})[field], rowKeys);
    }
  }
  for (const [field, nestedKeys] of Object.entries(spec.nested || {})) {
    const found = (payload || {})[field];
    if (found === null || typeof found !== 'object' || Array.isArray(found)) {
      fail(`${where}.${field}`, 'is not an object');
      continue;
    }
    const gone = missing(found, nestedKeys);
    if (gone.length) fail(`${where}.${field}`, `is missing ${gone.join(', ')}`);
  }
}

async function checkPages() {
  for (const page of contract.pages) {
    const response = await fetch(`${BASE}${page}`);
    const html = await response.text();
    if (!response.ok) {
      fail(`GET ${page}`, `answered ${response.status}`);
      continue;
    }
    if (!html.includes('id="dash"')) fail(`GET ${page}`, 'has no #dash for a page module to fill');
    if (!html.includes('id="tabnav"')) fail(`GET ${page}`, 'has no #tabnav for the shared nav');
    if (/(?:href|src)="\/assets\/[^"?#]+"/.test(html)) {
      fail(`GET ${page}`, 'serves an /assets URL with no ?v= build id, so a deploy leaves it cached');
    }
    if (response.headers.get('cache-control') !== 'no-store') {
      fail(`GET ${page}`, `answered cache-control ${response.headers.get('cache-control')}, not no-store`);
    }
  }
  const asset = await fetch(`${BASE}/assets/site.css`);
  if (asset.headers.get('cache-control') !== 'no-cache') {
    fail('GET /assets/site.css', `answered cache-control ${asset.headers.get('cache-control')}, not no-cache`);
  }
}

async function post(path, body) {
  return send('POST', path, body || {});
}

function send(method, path, body) {
  const init = { method, headers: { cookie: 'mock_as=staff' } };
  if (body !== undefined) {
    init.headers['content-type'] = 'application/json';
    init.body = JSON.stringify(body);
  }
  return fetch(`${BASE}${path}`, init);
}

async function seed() {
  // The same fixture the pytest side builds: the mock is put back to its seed, then given
  // the one role menu the contract's PUT / post / DELETE entries act on.
  await post('/api/mock/reset');
  // rolemenu_mode ships off, and a panel is not posted while it is off — so the post route's
  // shape, and the guard's own 409 on it, are only reachable with it turned on.
  await send('PUT', '/api/settings/rolemenu_mode', { value: 'on' });
  await post('/api/rolemenus', { name: 'contract', title: 'Contract', mode: 'multiple' });
  await fetch(`${BASE}/api/rolemenus/contract`, {
    method: 'PUT',
    headers: { cookie: 'mock_as=staff', 'content-type': 'application/json' },
    body: JSON.stringify({
      title: 'Contract',
      mode: 'multiple',
      options: [{ role_id: '900000000000000005', label: 'Members', emoji: null }],
    }),
  });
  await post('/api/modmail/snippets', { name: 'contract', content: 'hello' });
  await post('/api/modmail/blocks', { user_id: IDS.member_id, reason: 'contract check' });
  // The opt-out the DELETE entry takes away again; the seed's own opt-out is somebody else.
  await post('/api/golive/optouts', { user_id: IDS.member_id });
}

// The routes the REAL API refuses while test mode is on, and the two it does not. A reply
// DMs the member and a warn only writes a case, so black_bloc's own guard never sees them.
const GUARDED = [
  ['POST', '/api/rolemenus/contract/post', { channel_id: '{test_channel_id}' }],
  ['POST', '/api/tempvoice/setup', {}],
  ['POST', '/api/honeypot/setup', {}],
  ['POST', '/api/honeypot/hits/{hit_id}/ban', {}],
  ['POST', '/api/mod/cases/{case_id}/apply', {}],
  ['POST', '/api/modmail/tickets/{ticket_id}/close', {}],
];
const UNGUARDED = [
  ['POST', '/api/modmail/tickets/{ticket_id}/reply', { text: 'hello' }],
  ['POST', '/api/mod/warn', { user_id: '{member_id}', reason: 'contract check' }],
];

async function setGuard(on) {
  await post('/api/mock/guard', { on });
}

async function checkGuard() {
  await setGuard(true);
  for (const [method, path, body] of GUARDED) {
    await seed();
    const response = await send(method, fill(path), body);
    if (response.status !== 409) {
      fail(`${method} ${fill(path)}`, `answered ${response.status}, not the guard's 409`);
    }
  }
  for (const [method, path, body] of UNGUARDED) {
    await seed();
    const response = await send(method, fill(path), body);
    if (response.status === 409) {
      fail(`${method} ${fill(path)}`, 'refused with 409; the real API allows this in test mode');
    }
  }
}

async function checkRoutes() {
  // The guard is off for this pass: every route has to answer so its shape can be read.
  await setGuard(false);
  for (const spec of contract.routes) {
    await seed();
    const path = fill(spec.path);
    const where = `${spec.method} ${path}`;
    const init = { method: spec.method, headers: { cookie: 'mock_as=staff' } };
    if (spec.body !== undefined) {
      init.headers['content-type'] = 'application/json';
      init.body = fill(JSON.stringify(spec.body));
    }
    let response;
    try {
      response = await fetch(`${BASE}${path}`, init);
    } catch (e) {
      fail(where, `the mock did not answer: ${e.message}`);
      continue;
    }
    const text = await response.text();
    if (response.status !== 200) {
      fail(where, `answered ${response.status}: ${text.slice(0, 200)}`);
      continue;
    }
    let payload;
    try {
      payload = JSON.parse(text);
    } catch (e) {
      fail(where, 'did not answer JSON');
      continue;
    }
    check(where, payload, spec);
  }
}

async function checkActionKinds() {
  await seed();
  await post('/api/tempvoice/setup');
  await post('/api/honeypot/setup');
  await post('/api/modmail/snippets', { name: 'contract', content: 'hello' });
  await post(`/api/rolemenus/requests/${IDS.request_id}/deny`, { reason: 'contract check' });
  await send('DELETE', `/api/roles/grants/${IDS.grant_id}`, undefined);
  const response = await fetch(`${BASE}/api/actions?limit=200`, { headers: { cookie: 'mock_as=staff' } });
  const payload = await response.json();
  const known = new Set(contract.action_kinds);
  const web = (payload.actions || []).map((row) => row.kind).filter((kind) => String(kind).startsWith('web'));
  if (web.length === 0) fail('GET /api/actions', 'the mock logged no web.* line at all');
  for (const kind of new Set(web)) {
    if (!known.has(kind)) fail('GET /api/actions', `unlisted action kind ${kind}`);
  }
}

process.stdout.write(`check: ${BASE} against ${HERE}contract.json\n`);
await checkPages();
await checkGuard();
await checkRoutes();
await checkActionKinds();
await setGuard(true);

if (failures.length) {
  process.stdout.write(`check: ${failures.length} problem(s)\n`);
  for (const said of failures) process.stdout.write(`  - ${said}\n`);
  process.exit(1);
}
process.stdout.write(
  `check: ok - ${contract.pages.length} pages, ${contract.routes.length} routes, all keys present\n`,
);
