// The run sheet's recompute, proved twice: as pure fixtures on `sheetOf`, and — when a mock is
// listening on MOCK_PORT — by walking every move route and checking the returned times by rule.
//
//   node site/mock/runsheet.test.mjs                 (pure fixtures only)
//   MOCK_PORT=8798 node site/mock/runsheet.test.mjs  (also walks the mock; it resets the mock's state)

import { clockNear, clockOf, minutesOf, sheetOf } from './runsheet.mjs';

const MIN = 60000;
const failures = [];
const is = (where, found, wanted) => {
  if (JSON.stringify(found) !== JSON.stringify(wanted)) failures.push(`${where}: is ${JSON.stringify(found)}, not ${JSON.stringify(wanted)}`);
};

const T0 = Date.UTC(2026, 9, 4, 17, 0);
const at = (minutes) => new Date(T0 + minutes * MIN).toISOString();
const run = (id, plan, minutes, extra = {}) => ({ id, order_no: id, state: 'upcoming', run_seconds: minutes * 60, organisers_at: at(plan), sheet_at: at(plan), scheduled_at: at(plan), ends_at: at(plan + minutes), ...extra });
const starts = (rows) => rows.map((one) => (one.start === null ? null : (one.start - T0) / MIN));
const froms = (rows) => rows.map((one) => one.from);
const day = () => [run(1, 0, 23), run(2, 33, 80), run(3, 123, 16), run(4, 149, 110)];
const sheet = (runs, now = T0) => sheetOf(runs, { now, editable: true });

is('untouched: every run on its sheet time', starts(sheet(day())), [0, 33, 123, 149]);
is('untouched: every tag is the organisers', froms(sheet(day())), ['organisers', 'organisers', 'organisers', 'organisers']);

let runs = day();
Object.assign(runs[0], { state: 'live', live_because: 'title+category', actual_started_at: at(2) });
is('a start seen 2 min late moves every later run 2 min', starts(sheet(runs, T0 + 5 * MIN)), [2, 35, 125, 151]);
is('…and says where each time came from', froms(sheet(runs, T0 + 5 * MIN)), ['stream', 'follows', 'follows', 'follows']);
is('a live run past its estimate ends now, so the next waits for it', starts(sheet(runs, T0 + 40 * MIN))[1], 50);

runs = day();
runs[1].staff_at = at(45);
is('a staff time wins over the sheet and later runs keep their gaps', starts(sheet(runs)), [0, 45, 135, 161]);
is('…tagged set by staff, then follows', froms(sheet(runs)), ['organisers', 'staff', 'follows', 'follows']);
Object.assign(runs[1], { state: 'live', live_because: 'staff', actual_started_at: at(40) });
is('what really happened wins over the staff time', starts(sheet(runs))[1], 40);
is('…tagged started by staff', froms(sheet(runs))[1], 'started');

runs = day();
runs[1].staff_estimate_seconds = 60 * 60;
is('a shorter estimate pulls later runs in', starts(sheet(runs)), [0, 33, 103, 129]);

runs = day();
runs[1].state = 'dropped';
is('a skipped run has no time and the next one closes the gap', starts(sheet(runs)), [0, null, 33, 59]);

runs = day();
Object.assign(runs[0], { state: 'done', actual_started_at: at(0), actual_ended_at: at(20) });
is('a finish 3 min early: next = finish + its setup gap', starts(sheet(runs)), [0, 30, 120, 146]);

runs = [...day(), run(5, 149 + 110 + 600, 30)];
is('a gap over four hours starts a new day', sheet(runs).map((one) => one.day), [0, 0, 0, 0, 1]);
runs[0].staff_at = at(30);
is('…and a move on one day never reaches the next', starts(sheet(runs))[4], 859);

runs = day().map((one) => ({ ...one, organisers_at: null }));
is('with no organisers sheet the tag is the source sheet', froms(sheet(runs))[0], 'source');
is('a tracker sheet shows the tracker time and never chains', froms(sheetOf(day(), { now: T0, editable: false })), ['tracker', 'tracker', 'tracker', 'tracker']);

is('clockOf 14:30', clockOf('14:30'), { hour: 14, minute: 30 });
is('clockOf 2:05 pm', clockOf('2:05 pm'), { hour: 14, minute: 5 });
is('clockOf 1430', clockOf('1430'), { hour: 14, minute: 30 });
is('clockOf 25:99', clockOf('25:99'), null);
is('minutesOf 1:20', minutesOf('1:20'), 80);
is('minutesOf 45', minutesOf('45'), 45);
is('minutesOf abc', minutesOf('abc'), null);
is('clockNear picks the same local day (Phoenix, UTC-7)', new Date(clockNear(Date.UTC(2026, 9, 4, 19, 29), 12, 40, 'America/Phoenix')).toISOString(), '2026-10-04T19:40:00.000Z');
is('clockNear crosses midnight to the nearer side', new Date(clockNear(Date.UTC(2026, 9, 5, 6, 50), 0, 10, 'America/Phoenix')).toISOString(), '2026-10-05T07:10:00.000Z');

async function walk(port) {
  const base = `http://127.0.0.1:${port}`;
  const ask = async (method, path, body) => {
    const response = await fetch(`${base}${path}`, { method, headers: { cookie: 'mock_as=staff', 'content-type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body) });
    return { status: response.status, body: await response.json() };
  };
  const post = (path, body = {}) => ask('POST', `/api/marathons/60/runsheet/${path}`, body);
  const ms = (iso) => new Date(iso).getTime();
  const today = (found) => found.rows.filter((one) => one.day === found.today);
  const startsOf = (found) => today(found).map((one) => (one.start_at ? ms(one.start_at) : null));
  const refused = (where, got, status, error) => {
    is(`${where}: status`, got.status, status);
    is(`${where}: error`, got.body.error, error);
    if (!got.body.message || /^\d{3}$/.test(String(got.body.message).trim())) failures.push(`${where}: refused without words`);
  };

  await ask('POST', '/api/mock/reset', {});
  const seed = (await ask('GET', '/api/marathons/60/runsheet')).body;
  const before = startsOf(seed);
  const states = today(seed).map((one) => one.state);
  is('walk: the seed is two done, one live, eight upcoming', states.join(','), 'done,done,live,upcoming,upcoming,upcoming,upcoming,upcoming,upcoming,upcoming,upcoming');
  const [, , live, next, third] = today(seed);
  is('walk: the live run is 5 min ahead of its sheet time', live.off_plan_minutes, -5);

  const behind = (await post('shift', { day: 'today', minutes: 10 })).body;
  is('walk: Behind 10 moves every upcoming run 10 min and no other', startsOf(behind).map((one, index) => one - before[index]), states.map((one) => (one === 'upcoming' ? 10 * MIN : 0)));
  is('walk: Behind 10 tags the first moved run set by staff', today(behind)[3].from, 'staff');
  is('walk: Behind 10 moves the drift by 10', behind.days.find((one) => one.key === behind.today).drift_minutes, -5 + 10);
  is('walk: Behind 10 moves the next host post by 10', ms(behind.next_posts.find((one) => one.kind === 'host').at) - ms(seed.next_posts.find((one) => one.kind === 'host').at), 10 * MIN);

  const undone = (await post('undo')).body;
  is('walk: Undo puts every time back', startsOf(undone), before);
  refused('walk: a second Undo', await post('undo'), 409, 'nothing_to_undo');

  const typed = new Intl.DateTimeFormat('en-GB', { timeZone: seed.timezone, hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).format(new Date(ms(third.start_at) + 20 * MIN));
  const set = (await post(`runs/${third.id}/set-start`, { time: typed })).body;
  is('walk: Set start moves that run and every later one 20 min, nothing before it', startsOf(set).map((one, index) => one - before[index]), states.map((one, index) => (index >= 4 ? 20 * MIN : 0)));

  const longer = (await post(`runs/${next.id}/estimate`, { estimate: '2:00' })).body;
  is('walk: a longer estimate stops at the run staff set', startsOf(longer).map((one, index) => one - before[index]), states.map((one, index) => (index >= 4 ? 20 * MIN : 0)));
  is('walk: …and the estimate reads as staff’s', today(longer)[3].estimate_from, 'staff');

  const reset = (await post('reset', { day: 'today' })).body;
  is('walk: Back to the source’s times forgets both', startsOf(reset), before);
  refused('walk: a second reset', await post('reset', { day: 'today' }), 409, 'not_retimed');

  const skipped = (await post(`runs/${next.id}/skip`)).body;
  is('walk: a skipped run has no time', today(skipped)[3].start_at, null);
  is('walk: …and the run after it starts where the gap closes', ms(today(skipped)[4].start_at), ms(live.ends_at) + 10 * MIN);
  const back = (await post(`runs/${next.id}/restore`)).body;
  is('walk: Bring it back restores every time', startsOf(back), before);

  const started = (await post(`runs/${next.id}/start`)).body;
  const [, , closed, nowLive, after] = today(started);
  is('walk: Started now makes the run live and finishes the one before', [closed.state, nowLive.state, nowLive.from], ['done', 'live', 'started']);
  is('walk: …at the same minute', closed.actual_ended_at, nowLive.actual_started_at);
  is('walk: …and the next run follows: start + estimate + 10 min setup', ms(after.start_at), ms(nowLive.start_at) + 110 * MIN + 10 * MIN);
  is('walk: …while the two done runs did not move', startsOf(started).slice(0, 2), before.slice(0, 2));

  const finished = (await post(`runs/${next.id}/finish`)).body;
  is('walk: Finished now: next = finish + 10 min setup', ms(today(finished)[4].start_at), ms(today(finished)[3].actual_ended_at) + 10 * MIN);

  refused('walk: starting a done run', await post(`runs/${next.id}/start`), 409, 'not_startable');
  refused('walk: a time that is not a time', await post(`runs/${third.id}/set-start`, { time: '25:99' }), 400, 'bad_time');
  refused('walk: zero minutes', await post('shift', { day: 'today', minutes: 0 }), 400, 'bad_minutes');
  refused('walk: a run that is not there', await post('runs/999/skip'), 404, 'no_such_run');
  refused('walk: a tracker sheet refuses a shift', await ask('POST', '/api/marathons/1/runsheet/shift', { day: 'today', minutes: 5 }), 409, 'tracker_times');
  is('walk: a tracker sheet is read-only', (await ask('GET', '/api/marathons/1/runsheet')).body.kind, 'read_only');
  is('walk: the moves log is newest first', finished.moves[0].kind, 'finished');
  await ask('POST', '/api/mock/reset', {});
}

if (process.env.MOCK_PORT) await walk(process.env.MOCK_PORT);

if (failures.length) {
  console.error('runsheet: not ok');
  for (const said of failures) console.error(`  - ${said}`);
  process.exit(1);
}
console.log(`runsheet: ok - whose time wins, gaps, skips, days and typed times${process.env.MOCK_PORT ? ', and every move walked against the mock' : ' (set MOCK_PORT to walk the mock too)'}`);
