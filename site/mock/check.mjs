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
  // A case the seed already has VOIDED, because /restore is only legal from there and every
  // contract entry runs against a fresh seed.
  voided_case_id: '8',
  event_id: '3',
  ticket_id: '5',
  hit_id: '7',
  test_channel_id: '800000000000000003',
  lobby_channel_id: '800000000000000009',
  room_channel_id: '800000000000000010',
  plain_role_id: '900000000000000005',
  request_id: '4',
  grant_id: '5',
  poll_id: '3',
  poll_request_id: '2',
  poll_recurrence_id: '4',
  chat_intent_id: '1',
  chat_line_id: '1',
  // A STAFF-written knowledge note. The mock's third section is the one Black Bloc writes for
  // itself, and every write on that one refuses in words — see the contract's own note.
  chat_section_id: '1',
  // request_id above is a ROLE request; a feature request is a different table and gets its
  // own pair: 25 is the staff session's own pending row, 30 is somebody else's.
  feature_request_id: '25',
  member_request_id: '30',
  // A row the seed already has ON HOLD, because /resume is only legal from there and every
  // contract entry runs against a fresh seed.
  held_request_id: '20',
  // 13c: a row the seed already has READY TO CHECK, so /accept and /sendback reach it without
  // walking the machine first, and one already being worked on, which is where /ready is legal.
  review_request_id: '11',
  progress_request_id: '12',
  // F14: {member_id} already HAS a ping role in the seed, so the GET and the DELETE act on it
  // and the POST needs somebody who does not — otherwise it answers the 409 it should.
  ping_member_id: '700000000000000004',
  // Phase 18: train 1 is the upcoming one, still open, so lock/assign/swap all reach it.
  raid_train_id: '1',
  // Phase 19: form 1 is the Twitch Team form with three questions and people waiting on it;
  // form 2 is the closed one nobody has applied to, so the DELETE entry has something to remove.
  application_form_id: '1',
  empty_form_id: '2',
  application_id: '1',
  // The no-role pass: form 1 keeps a LIST rather than handing a role over, so its approved
  // rows are the roster and row 2 is the one the remove entry takes off it.
  listed_form_id: '1',
  listed_application_id: '2',
  // Wave 5: run 2 is the recent one whose cards are still in Discord, so the purge entry has
  // something to take down. Run 1 is already cleaned up.
  selftest_run_id: '2',
  // Guides (G1): golive-announce is one of the seventeen Black Bloc ships with, so it is
  // the one /reset takes and the one DELETE refuses; house-rules is written here, which
  // is the other way round.
  guide_slug: 'golive-announce',
  scratch_guide_slug: 'house-rules',
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
  // Posted here so the unpost entry has a panel to take down; refused while the guard is on,
  // which is exactly what the GUARDED pass asserts a moment later.
  await post('/api/rolemenus/contract/post', { channel_id: IDS.test_channel_id });
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
  // The body is NOT run through fill(), so this one carries the id itself.
  ['POST', '/api/applications/forms/{application_form_id}/panel', { channel_id: IDS.test_channel_id }],
];
const UNGUARDED = [
  // A room action is place-gated (tempvoice.py:may_act_in), not blanket-refused: a room
  // spawned from a lobby the guard placed sits in the test channel's own category, so it is
  // one of the ones a staffer may still change while test mode is on.
  ['POST', '/api/tempvoice/rooms/{room_channel_id}/rename', { name: 'guarded check' }],
  // A member's roles are not a channel, so guard.py cannot see this and neither the picker
  // nor the route refuses it in test mode — /rolemenu assign changes real roles today.
  ['POST', '/api/rolemenus/contract/assign', { user_id: '{member_id}', role_ids: ['{plain_role_id}'] }],
  ['POST', '/api/modmail/tickets/{ticket_id}/reply', { text: 'hello' }],
  ['POST', '/api/mod/warn', { user_id: '{member_id}', reason: 'contract check' }],
  // Filing a request writes a row and DMs; only the one line in request_notify_channel_id
  // is a channel post, and that is guarded on its own inside the bot.
  ['POST', '/api/requests', { what: 'contract check', why: 'the guard list needs one' }],
  // Phase 18: making a train writes rows and then tries one lineup post; the post is guarded
  // inside the bot (it logs raidtrain.post_skipped_test_mode) rather than refusing the route.
  ['POST', '/api/raidtrains', { title: 'Guard check', start: '2099-09-14 19:30', tz: 'UTC', slot_minutes: 60, slot_count: 2 }],
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
  // The six web.tempvoice.* room kinds, each left by the write that spells it: lock and unlock
  // are two kinds off one route, and so are hide and show.
  await post(`/api/tempvoice/rooms/${IDS.room_channel_id}/rename`, { name: 'contract room' });
  await post(`/api/tempvoice/rooms/${IDS.room_channel_id}/limit`, { limit: 4 });
  await post(`/api/tempvoice/rooms/${IDS.room_channel_id}/lock`, { locked: true });
  await post(`/api/tempvoice/rooms/${IDS.room_channel_id}/lock`, { locked: false });
  await post(`/api/tempvoice/rooms/${IDS.room_channel_id}/hide`, { hidden: true });
  await post(`/api/tempvoice/rooms/${IDS.room_channel_id}/hide`, { hidden: false });
  await post('/api/rolemenus/contract/unpost', {});
  await post('/api/rolemenus/seed', {});
  await post('/api/rolemenus/contract/assign', { user_id: IDS.member_id, role_ids: [IDS.plain_role_id] });
  await post('/api/rolemenus/contract/assign', { user_id: IDS.member_id, role_ids: [IDS.plain_role_id], remove: true });
  await send('PUT', `/api/events/${IDS.event_id}`, { title: 'Contract night', start: '2099-09-14 19:30', duration: '2h' });
  // F3's two web.youtube.* kinds. The member already holds that channel in the seed, so the
  // POST re-links rather than tripping the 409 a second owner would get.
  await post('/api/youtube/links', { member_id: IDS.member_id, channel: 'UCsXVk37bltHxD1rDPwtNM8Q' });
  await send('DELETE', `/api/youtube/links/${IDS.member_id}`, undefined);
  // The three web.pings.* kinds, each left by the write that spells it.
  await post('/api/pings/setup', {});
  await post('/api/pings/streamers', { member_id: IDS.ping_member_id });
  await send('DELETE', `/api/pings/streamers/${IDS.ping_member_id}`, undefined);
  // The six web.chat.* kinds, each left by the write that spells it rather than merely listed.
  await post('/api/chat/intents', { name: 'contract_check', triggers: ['contract check'], lines: ['Hello {name}.'] });
  await send('PUT', `/api/chat/intents/${IDS.chat_intent_id}`, { enabled: true });
  await post(`/api/chat/intents/${IDS.chat_intent_id}/lines`, { text: 'Another contract line.' });
  await send('PUT', `/api/chat/lines/${IDS.chat_line_id}`, { text: 'An edited contract line.' });
  await send('DELETE', `/api/chat/lines/${IDS.chat_line_id}`, undefined);
  await send('DELETE', `/api/chat/intents/${IDS.chat_intent_id}`, undefined);
  // The six web.chat.* kinds 14b adds, each left by the write that spells it. The trope pair is
  // two kinds off one route, the way tempvoice's lock/unlock is.
  await post('/api/chat/knowledge', { title: 'Contract note', body: 'Written on the contract run.' });
  await send('PUT', `/api/chat/knowledge/${IDS.chat_section_id}`, { body: 'Edited on the contract run.' });
  await send('DELETE', `/api/chat/knowledge/${IDS.chat_section_id}`, undefined);
  await send('PUT', '/api/chat/personality', { mode: 'pool' });
  await send('PUT', '/api/chat/personality/tsundere', { enabled: false });
  await send('PUT', '/api/chat/personality/tsundere', { enabled: true });
  // Phase 17: the one web.chat.memory_* kind the website can leave.
  await send('DELETE', `/api/chat/memory/${IDS.member_id}`, undefined);
  // The ten web.request.* kinds. Hold then resume walks the state machine both ways off one
  // row, and ready → check → sendback → ready → accept walks the review pass off another.
  // Withdraw is the member's own, so it is the one call here that goes in as somebody who is
  // not staff.
  await post('/api/requests', { what: 'contract check', why: 'so web.request.filed is left' });
  await post(`/api/requests/${IDS.feature_request_id}/comments`, { text: 'contract check' });
  await post(`/api/requests/${IDS.feature_request_id}/status`, { priority: 2 });
  await post(`/api/requests/${IDS.feature_request_id}/hold`, { reason: 'contract check' });
  await post(`/api/requests/${IDS.feature_request_id}/resume`, {});
  await post(`/api/requests/${IDS.progress_request_id}/ready`, { built: 'contract check', how_to_test: 'press it' });
  await post(`/api/requests/${IDS.review_request_id}/check`, {});
  await post(`/api/requests/${IDS.review_request_id}/sendback`, { reason: 'contract check' });
  await post(`/api/requests/${IDS.review_request_id}/ready`, { built: 'contract check' });
  await post(`/api/requests/${IDS.review_request_id}/accept`, {});
  await post('/api/requests/26/decline', { reason: 'contract check' });
  await fetch(`${BASE}/api/requests/${IDS.member_request_id}/withdraw`, {
    method: 'POST',
    headers: { cookie: 'mock_as=member', 'content-type': 'application/json' },
    body: '{}',
  });
  // The seven web.raidtrain.* kinds, each left by the write that spells it. Lock and unlock are
  // two kinds off one route, the way tempvoice's lock/unlock is.
  await post('/api/raidtrains', { title: 'Contract train', start: '2099-09-14 19:30', tz: 'UTC', slot_minutes: 60, slot_count: 2 });
  await post(`/api/raidtrains/${IDS.raid_train_id}/slots/3`, { member_id: IDS.member_id });
  await post(`/api/raidtrains/${IDS.raid_train_id}/slots/3`, { member_id: null });
  await post(`/api/raidtrains/${IDS.raid_train_id}/swap`, { a: 1, b: 2 });
  await post(`/api/raidtrains/${IDS.raid_train_id}/status`, { status: 'locked' });
  await post(`/api/raidtrains/${IDS.raid_train_id}/status`, { status: 'open' });
  await post(`/api/raidtrains/${IDS.raid_train_id}/status`, { status: 'cancelled', reason: 'contract check' });
  // The seven web.application.* kinds, each left by the write that spells it.
  await post('/api/applications/forms', { name: 'contract-form-kinds', title: 'Contract form', role_id: IDS.plain_role_id });
  await send('PATCH', `/api/applications/forms/${IDS.application_form_id}`, { title: 'Twitch Team' });
  await send('PUT', `/api/applications/forms/${IDS.application_form_id}/questions`, { questions: [{ label: 'Twitch handle' }] });
  await post(`/api/applications/forms/${IDS.application_form_id}/panel`, { channel_id: IDS.test_channel_id });
  await send('DELETE', `/api/applications/forms/${IDS.empty_form_id}`, undefined);
  await post(`/api/applications/${IDS.application_id}/decide`, { status: 'denied', reason: 'contract check' });
  await post('/api/applications/4/decide', { status: 'approved' });
  await post(`/api/applications/${IDS.listed_application_id}/remove`, { reason: 'contract check' });
  const response = await fetch(`${BASE}/api/actions?limit=200`, { headers: { cookie: 'mock_as=staff' } });
  const payload = await response.json();
  const known = new Set(contract.action_kinds);
  const web = (payload.actions || []).map((row) => row.kind).filter((kind) => String(kind).startsWith('web'));
  if (web.length === 0) fail('GET /api/actions', 'the mock logged no web.* line at all');
  for (const kind of new Set(web)) {
    if (!known.has(kind)) fail('GET /api/actions', `unlisted action kind ${kind}`);
  }
}

// The settings registry has ONE home, black_bloc/settings_store.py, and contract.json's
// `settings` block is the table both halves read: tests/api/test_contract.py checks it against
// the registry, this checks the mock against it. It exists because the mock had invented a
// max of 1440 for sixteen *_panel_minutes keys the registry does not bound, was missing sixteen
// keys altogether, and kept a shorter second copy of CORE_KEYS.
async function checkSettings() {
  await setGuard(false);
  await seed();
  const wanted = contract.settings;
  const response = await send('GET', '/api/settings', undefined);
  if (response.status !== 200) {
    fail('GET /api/settings', `answered ${response.status}`);
    return;
  }
  const body = await response.json();
  const rows = new Map();
  for (const [namespace, list] of Object.entries(body)) {
    for (const row of list) rows.set(row.key, { ...row, namespace });
  }
  const core = [...rows.values()].filter((row) => row.namespace === 'core').map((row) => row.key);
  const wantedCore = [...wanted.core_keys, 'core_log_level'].sort();
  if (core.sort().join(',') !== wantedCore.join(',')) {
    fail('GET /api/settings[core]', `holds ${core.join(', ')}, not ${wantedCore.join(', ')}`);
  }
  for (const [key, bound] of Object.entries(wanted.max)) {
    const row = rows.get(key);
    if (!row) fail('GET /api/settings', `has no ${key} row at all`);
    else if (row.max !== bound) fail(`GET /api/settings[${key}]`, `max is ${row.max}, not ${bound}`);
  }
  for (const [key, bound] of Object.entries(wanted.min)) {
    const row = rows.get(key);
    if (!row) fail('GET /api/settings', `has no ${key} row at all`);
    else if (row.min !== bound) fail(`GET /api/settings[${key}]`, `min is ${row.min}, not ${bound}`);
  }
  for (const [key, row] of rows) {
    if ('max' in row && !(key in wanted.max)) {
      fail(`GET /api/settings[${key}]`, `claims max ${row.max}; the registry bounds no such thing`);
    }
    if ('min' in row && !(key in wanted.min)) {
      fail(`GET /api/settings[${key}]`, `claims min ${row.min}; the registry bounds no such thing`);
    }
  }
}

// The roster foldout's walk, without a DOM: the list a no-role form keeps, one member taken
// off it with a reason, and the row that leaves showing as `removed` in the Decided table.
async function checkRoster() {
  await setGuard(false);
  await seed();
  const roster = async () => (await (await send('GET', `/api/applications/roster?form=${IDS.listed_form_id}`, undefined)).json());
  const before = await roster();
  if (before.length !== 3) fail('GET /api/applications/roster', `listed ${before.length} row(s), not 3`);
  if (!before.some((row) => row.twitch_login)) fail('GET /api/applications/roster', 'no row carries a twitch_login');
  if (!before.some((row) => row.in_server === false)) fail('GET /api/applications/roster', 'no row is flagged as having left');

  const off = await post(`/api/applications/${IDS.listed_application_id}/remove`, { reason: 'stopped streaming' });
  if (off.status !== 200) fail('POST remove', `answered ${off.status}`);
  const blank = await post(`/api/applications/${IDS.listed_application_id}/remove`, { reason: '  ' });
  if (blank.status !== 400) fail('POST remove (no reason)', `answered ${blank.status}, not 400`);

  const after = await roster();
  if (after.length !== 2) fail('GET /api/applications/roster', `listed ${after.length} row(s) after a removal, not 2`);
  const decided = await (await send('GET', '/api/applications?status=removed', undefined)).json();
  if (!decided.some((row) => String(row.id) === IDS.listed_application_id)) {
    fail('GET /api/applications?status=removed', 'the removed row is not in the Decided list');
  }
}

process.stdout.write(`check: ${BASE} against ${HERE}contract.json\n`);
await checkPages();
await checkGuard();
await checkRoutes();
await checkSettings();
await checkRoster();
await checkActionKinds();
await setGuard(true);

if (failures.length) {
  process.stdout.write(`check: ${failures.length} problem(s)\n`);
  for (const said of failures) process.stdout.write(`  - ${said}\n`);
  process.exit(1);
}
process.stdout.write(
  `check: ok - ${contract.pages.length} pages, ${contract.routes.length} routes, `
    + `${contract.settings.core_keys.length} core settings, all keys present\n`,
);
