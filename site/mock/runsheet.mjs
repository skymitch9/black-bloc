const MIN = 60000;
const DAY_GAP_MS = 4 * 3600000;
const UNDO_DEPTH = 50;
const SHIFT_LIMIT = 240;
const ESTIMATE_LIMIT = 720;
const DEMO_ID = 60;
const STATE_WORDS = { upcoming: 'upcoming', live: 'live', done: 'done', dropped: 'skipped' };
const TIMES_FROM_WORDS = { organisers: "the organisers' sheet", source: 'the source sheet plus setup time', tracker: 'the tracker' };

const DEMO_DAY_ONE = [
  [-1563, 68, 'Spyro Reignited Trilogy', 'Spyro the Dragon: 80 Dragons NBS', ['Toronite'], null],
  [-1488, 52, 'Hamtaro: Ham-Hams Unite!', 'Any%', ['PumpkinPower14'], null],
  [-1429, 46, 'Bombun', 'Any% NG+', ['debeaunairVT'], null],
];

const DEMO_DAY_TWO = [
  [-123, 23, 'Wii Fit U', 'All Beginner Categories', ['dragonz4477'], 'SYDNEY J'],
  [-90, 80, 'Inazuma Eleven: Victory Road', 'Baseball%', ['Starwindx9'], 'SYDNEY J'],
  [0, 16, "Dr. Robotnik's Ring Racers", 'Power Cup', ['The_Mathcat'], 'SYDNEY J'],
  [26, 110, 'Metroid Prime 4: Beyond', '3 Teleporter Keys', ['BashPrime'], 'chibicarrera'],
  [146, 15, 'E.T. the Extra-Terrestrial', 'Beat the Game?', ['Lunch_the_great'], 'sweetpeebs'],
  [171, 70, 'Battle Chef Brigade', 'Any% Hard', ['Ramseyfox'], 'sweetpeebs'],
  [251, 50, 'Osu! Tatakae! Ouendan 2', 'Showcase', ['LMMotoss'], 'JRisJunior'],
  [311, 50, 'Sayonara Wild Hearts', 'Wild Rank Showcase', ['fletchisafurry'], 'JRisJunior'],
  [371, 40, 'Fear the Spotlight', 'Yuri% Race', ['218_vt', 'Chilling_Willow'], 'Quacksilver'],
  [421, 65, 'Legacy of Kain: Soul Reaver 2', 'All Reavers', ['Jaxler1'], 'Quacksilver'],
  [496, 90, 'Metroid Dread', 'Minimum Items Glitchless', ['araneacharlotte'], 'champrul'],
];

const DEMO_ACTUALS = { 63: [-121, -99], 64: [-92, -14], 65: [-5, null] };
const DEMO_SOURCE_SETUP = 7;

const ms = (iso) => (iso ? new Date(iso).getTime() : null);
const iso = (at) => new Date(at).toISOString();
const plural = (count, word) => `${count} ${word}${count === 1 ? '' : 's'}`;

function zoned(at, timeZone) {
  const parts = {};
  const format = new Intl.DateTimeFormat('en-GB', { timeZone, weekday: 'short', year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' });
  for (const one of format.formatToParts(new Date(at))) parts[one.type] = one.value;
  const month = parts.month === 'Sept' ? 'Sep' : parts.month;
  const number = String(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'].indexOf(month) + 1).padStart(2, '0');
  return {
    key: `${parts.year}-${number}-${String(parts.day).padStart(2, '0')}`,
    label: `${parts.weekday} ${Number(parts.day)} ${month}`,
    time: `${parts.hour}:${parts.minute}`,
    minutes: Number(parts.hour) * 60 + Number(parts.minute),
  };
}

export function clockNear(near, hour, minute, timeZone) {
  const midnight = near - (near % MIN) - zoned(near, timeZone).minutes * MIN;
  return [-1, 0, 1]
    .map((day) => midnight + day * 86400000 + (hour * 60 + minute) * MIN)
    .sort((a, b) => Math.abs(a - near) - Math.abs(b - near))[0];
}

export function clockOf(given) {
  const found = /^\s*(\d{1,2})[:.h]?(\d{2})\s*(am|pm)?\s*$/i.exec(String(given ?? ''));
  if (!found) return null;
  let hour = Number(found[1]);
  const minute = Number(found[2]);
  const half = (found[3] || '').toLowerCase();
  if (half && (hour < 1 || hour > 12)) return null;
  if (half === 'pm' && hour < 12) hour += 12;
  if (half === 'am' && hour === 12) hour = 0;
  return hour > 23 || minute > 59 ? null : { hour, minute };
}

export function minutesOf(given) {
  const said = String(given ?? '').trim();
  const clock = /^(\d{1,2}):(\d{2})$/.exec(said);
  if (clock) return Number(clock[2]) > 59 ? null : Number(clock[1]) * 60 + Number(clock[2]);
  return /^\d{1,4}$/.test(said) ? Number(said) : null;
}

function lengthWords(minutes) {
  return `${Math.floor(minutes / 60)}:${String(minutes % 60).padStart(2, '0')}`;
}

function sourceLength(run) {
  if (run.run_seconds) return run.run_seconds * 1000;
  return Math.max(0, ms(run.sheet_ends_at || run.ends_at) - ms(run.sheet_at || run.scheduled_at));
}

function lengthOf(run) {
  return run.staff_estimate_seconds ? run.staff_estimate_seconds * 1000 : sourceLength(run);
}

function planOf(run, editable) {
  if (!editable) return ms(run.scheduled_at);
  return ms(run.organisers_at) ?? ms(run.sheet_at) ?? ms(run.scheduled_at);
}

function planFrom(run) {
  return run.organisers_at ? 'organisers' : 'source';
}

export function sheetOf(runs, { now, editable }) {
  const sorted = [...runs]
    .filter((run) => planOf(run, editable) !== null)
    .sort((a, b) => planOf(a, editable) - planOf(b, editable) || a.order_no - b.order_no);
  const out = [];
  let day = 0;
  let cursor = null;
  let planEnd = null;
  for (const run of sorted) {
    const plan = planOf(run, editable);
    if (planEnd !== null && plan - planEnd > DAY_GAP_MS) {
      day += 1;
      cursor = null;
      planEnd = null;
    }
    const gap = planEnd === null ? 0 : Math.max(0, plan - planEnd);
    planEnd = plan + sourceLength(run);
    const length = lengthOf(run);
    if (run.state === 'dropped') {
      out.push({ run, day, plan, start: null, end: null, from: null, length });
      continue;
    }
    const actual = ms(run.actual_started_at);
    const begun = run.state === 'live' || run.state === 'done';
    const seen = run.live_because === 'staff' ? 'started' : 'stream';
    let start;
    let from;
    if (actual !== null) [start, from] = [actual, seen];
    else if (!editable) [start, from] = [plan, 'tracker'];
    else if (begun) start = ms(run.scheduled_at);
    else if (run.staff_at) [start, from] = [ms(run.staff_at), 'staff'];
    else start = cursor === null ? plan : cursor + gap;
    if (!from) from = start === plan ? planFrom(run) : 'follows';
    let end = ms(run.actual_ended_at);
    if (end === null) end = begun && actual === null ? ms(run.ends_at) : start + length;
    if (run.state === 'live') end = Math.max(end, now);
    cursor = end;
    out.push({ run, day, plan, start, end, from, length });
  }
  return out;
}

export function runsheetSeed(members, staffId) {
  const anchor = Math.round(Date.now() / MIN) * MIN + 2 * MIN;
  const at = (minutes) => iso(anchor + minutes * MIN);
  const baf = { The_Mathcat: members[6].id, JRisJunior: members[5].id, champrul: members[3].id };
  const person = (name, part) => ({ name, login: name.toLowerCase().replace(/\s+/g, ''), part, user_id: baf[name] || null });
  const runs = [];
  const build = (rows, firstId, withOrganisers) => {
    let source = rows[0][0];
    rows.forEach(([offset, minutes, game, category, runners, host], index) => {
      const id = firstId + index;
      const last = index === rows.length - 1;
      const sourceEnd = source + minutes + (last ? 0 : DEMO_SOURCE_SETUP);
      const [began, ended] = DEMO_ACTUALS[id] || (withOrganisers ? [null, null] : [offset, offset + minutes]);
      const state = ended !== null ? 'done' : began !== null ? 'live' : 'upcoming';
      runs.push({
        id,
        marathon_id: DEMO_ID,
        external_id: String(8000 + id),
        order_no: runs.length + 1,
        game,
        category,
        runners_text: runners.join(', '),
        people: [...runners.map((one) => person(one, 'runner')), ...(host ? [person(host, 'host')] : [])],
        run_seconds: minutes * 60,
        organisers_at: withOrganisers ? at(offset) : null,
        sheet_at: at(source),
        sheet_ends_at: at(sourceEnd),
        scheduled_at: at(began ?? offset),
        ends_at: at(ended ?? (began ?? offset) + minutes),
        actual_started_at: began === null ? null : at(began),
        actual_ended_at: ended === null ? null : at(ended),
        previous_scheduled_at: null,
        moved_at: null,
        state,
        live_because: began === null ? null : 'title+category',
        shout_message_id: null,
        reminders_sent: [],
        twitch_game_id: null,
        twitch_category: null,
        twitch_looked_at: null,
      });
      source = sourceEnd;
    });
  };
  build(DEMO_DAY_ONE, DEMO_ID, false);
  build(DEMO_DAY_TWO, DEMO_ID + DEMO_DAY_ONE.length, true);
  for (const row of sheetOf(runs, { now: Date.now(), editable: true })) {
    Object.assign(row.run, { scheduled_at: iso(row.start), ends_at: iso(row.end) });
  }
  const marathon = {
    id: DEMO_ID,
    name: 'GDQueer (run sheet)',
    schedule_url: 'https://gamesdonequick.com/hotfix/schedule#gdqueer/2026-10-04',
    source: 'gdq_hotfix',
    source_ref: 'gdqueer-runsheet/2026-10-04',
    spotlight_id: 1,
    feed_id: null,
    starts_at: at(DEMO_DAY_ONE[0][0]),
    ends_at: at(DEMO_DAY_TWO.at(-1)[0] + DEMO_DAY_TWO.at(-1)[1]),
    active: true,
    poll_minutes: null,
    board_channel_id: null,
    board_message_id: null,
    board_pinned: false,
    last_fetched_at: iso(Date.now() - 2 * MIN),
    last_fetch_ok: 1,
    last_error: null,
    fetch_failures: 0,
    added_by: staffId,
    added_at: iso(Date.now() - 3000 * MIN),
  };
  return { marathon, runs };
}

export function mountRunsheet({ route, Refused, requireStaff, actorOf, memberName, logAction, state, marathonOf, marathonRow, keepsClock }) {
  const zone = () => String(state().settings.get('default_timezone') || 'America/Phoenix');
  const clock = (at) => zoned(at, zone()).time;
  const setupMinutes = () => Number(state().settings.get('marathon_setup_minutes') || 7);
  const leadMinutes = () => {
    const found = String(state().settings.get('marathon_reminder_minutes') || '15').split(',').map((one) => Number(one.trim())).filter((one) => one > 0);
    return found.length ? Math.min(...found) : 15;
  };
  const editableOf = (row) => keepsClock.has(row.source);
  const runsOf = (row) => state().marathonRuns.filter((one) => one.marathon_id === row.id);
  const sheet = (row, now = Date.now()) => sheetOf(runsOf(row), { now, editable: editableOf(row) });
  const counts = (one) => Boolean(one.user_id) && one.counts !== false;

  function bookOf(row) {
    const books = state().runsheets || (state().runsheets = {});
    return books[row.id] || (books[row.id] = { moves: [], undo: [], next: 1 });
  }

  function daysOf(rows) {
    const days = [];
    for (const row of rows) {
      if (!days[row.day]) {
        const found = zoned(row.plan, zone());
        const taken = days.some((one) => one.key === found.key);
        days[row.day] = { index: row.day, key: taken ? `${found.key}-${row.day}` : found.key, label: found.label, starts_at: iso(row.plan), rows: [] };
      }
      days[row.day].rows.push(row);
    }
    return days;
  }

  function dayOf(row, given) {
    const days = daysOf(sheet(row));
    const found = days.find((one) => one.key === String(given || ''));
    if (!found) throw new Refused(404, 'no_such_day', `**${row.name}** has no day **${String(given || '').slice(0, 20) || 'blank'}** on its run sheet, so nothing was changed. Reload the page and pick a day from the strip.`);
    return found;
  }

  function driftOf(day) {
    const next = day.rows.find((one) => one.run.state === 'upcoming') || day.rows.find((one) => one.run.state === 'live');
    return next ? { minutes: Math.round((next.start - next.plan) / MIN), run_id: next.run.id } : { minutes: null, run_id: null };
  }

  function todayOf(days) {
    const found = days.find((day) => day.rows.some((one) => one.run.state === 'live'))
      || days.find((day) => day.rows.some((one) => one.run.state === 'upcoming'))
      || days.at(-1);
    return found ? found.key : null;
  }

  function personRow(one) {
    return { name: one.name, login: one.login || null, part: one.part, user_id: one.user_id || null, member_name: one.user_id ? memberName(one.user_id) : null, baf: counts(one) };
  }

  function sheetRow(row, day, editable, firstUpcoming) {
    const { run } = row;
    const upcoming = run.state === 'upcoming';
    return {
      id: run.id,
      day: day.key,
      order_no: run.order_no,
      game: run.game,
      category: run.category,
      people: run.people.map(personRow),
      ours: run.people.some(counts),
      state: run.state,
      state_word: STATE_WORDS[run.state] || run.state,
      start_at: row.start === null ? null : iso(row.start),
      ends_at: row.end === null ? null : iso(row.end),
      from: row.from,
      plan_at: iso(row.plan),
      plan_from: editable ? planFrom(run) : 'tracker',
      off_plan_minutes: row.start === null ? null : Math.round((row.start - row.plan) / MIN),
      estimate_seconds: Math.round(row.length / 1000),
      estimate_from: run.staff_estimate_seconds ? 'staff' : 'source',
      source_estimate_seconds: Math.round(sourceLength(run) / 1000),
      actual_started_at: run.actual_started_at || null,
      actual_ended_at: run.actual_ended_at || null,
      staff_at: run.staff_at || null,
      next_up: firstUpcoming === run.id,
      can: {
        start: upcoming,
        finish: run.state === 'live',
        set_start: editable && upcoming,
        estimate: editable && (upcoming || run.state === 'live'),
        skip: editable && upcoming,
        restore: editable && run.state === 'dropped',
      },
    };
  }

  function nextPosts(days, now) {
    const lead = leadMinutes();
    const posts = [];
    const push = (row, day, kind, text) => {
      const at = row.start - lead * MIN;
      posts.push({ at: iso(at), kind, run_id: row.run.id, day: day.key, passed: at < now, text });
    };
    for (const day of days) {
      let block = null;
      for (const row of day.rows.filter((one) => one.run.state !== 'dropped')) {
        const { run } = row;
        const runners = run.people.filter((one) => one.part !== 'host' && counts(one));
        if (runners.length && run.state === 'live') {
          posts.push({ at: null, kind: 'live', run_id: run.id, day: day.key, passed: false, text: `Highlight is up: **${runners.map((one) => one.name).join(', ')}** on **${run.game}**. It goes past tense when the run finishes.` });
        }
        if (runners.length && run.state === 'upcoming') {
          push(row, day, 'run', `Heads-up: **${runners.map((one) => one.name).join(', ')}** runs **${run.game}** in ${lead} minutes.`);
        }
        const host = run.people.find((one) => one.part === 'host' && counts(one)) || null;
        if (!host) {
          block = null;
        } else if (block && block.user_id === String(host.user_id)) {
          block.runs += 1;
          if (block.post) block.post.text = `Heads-up: **${host.name}** hosts ${plural(block.runs, 'run')} from **${block.game}** in ${lead} minutes.`;
        } else {
          block = { user_id: String(host.user_id), runs: 1, game: run.game, post: null };
          if (run.state === 'upcoming') {
            push(row, day, 'host', `Heads-up: **${host.name}** hosts ${plural(1, 'run')} from **${run.game}** in ${lead} minutes.`);
            block.post = posts.at(-1);
          }
        }
      }
    }
    return posts.sort((a, b) => String(a.at || '').localeCompare(String(b.at || '')));
  }

  function payload(row, message = null) {
    const now = Date.now();
    const editable = editableOf(row);
    const days = daysOf(sheet(row, now));
    const book = bookOf(row);
    const base = marathonRow(row);
    const rows = [];
    const dayRows = days.map((day) => {
      const first = day.rows.find((one) => one.run.state === 'upcoming');
      rows.push(...day.rows.map((one) => sheetRow(one, day, editable, first ? first.run.id : null)));
      const staffTimes = day.rows.filter((one) => one.run.staff_at).length;
      const staffEstimates = day.rows.filter((one) => one.run.staff_estimate_seconds).length;
      const drift = driftOf(day);
      return {
        key: day.key,
        label: day.label,
        starts_at: day.starts_at,
        runs: day.rows.filter((one) => one.run.state !== 'dropped').length,
        baf: day.rows.filter((one) => one.run.state !== 'dropped' && one.run.people.some(counts)).length,
        drift_minutes: drift.minutes,
        drift_run_id: drift.run_id,
        staff_times: staffTimes,
        staff_estimates: staffEstimates,
        can_shift: editable && Boolean(first),
        can_reset: editable && staffTimes + staffEstimates > 0,
      };
    });
    const timesFrom = !editable ? 'tracker' : runsOf(row).some((one) => one.organisers_at) ? 'organisers' : 'source';
    const last = book.undo.at(-1) || null;
    return {
      marathon: { id: base.id, name: base.name, source: base.source, source_word: base.source_word, schedule_page: base.schedule_page, phase: base.phase, phase_word: base.phase_word, last_fetched_at: base.last_fetched_at },
      editable,
      kind: editable ? 'editable' : 'read_only',
      times_from: timesFrom,
      times_from_word: TIMES_FROM_WORDS[timesFrom],
      timezone: zone(),
      now: iso(now),
      setup_minutes: setupMinutes(),
      heads_up_minutes: leadMinutes(),
      today: todayOf(days),
      days: dayRows,
      rows,
      next_posts: nextPosts(days, now),
      moves: book.moves.slice(0, 100),
      undo: { available: Boolean(last), text: last ? last.text : null },
      ...(message ? { message } : {}),
    };
  }

  function settle(row) {
    if (!editableOf(row)) return;
    for (const one of sheet(row)) {
      if (one.start !== null) Object.assign(one.run, { scheduled_at: iso(one.start), ends_at: iso(one.end) });
    }
  }

  function restore(row, saved) {
    const kept = new Map(saved.map((one) => [one.id, one]));
    for (const run of runsOf(row)) {
      const was = kept.get(run.id);
      if (!was) continue;
      for (const key of Object.keys(run)) delete run[key];
      Object.assign(run, JSON.parse(JSON.stringify(was)));
    }
  }

  function move(context, kind, work) {
    requireStaff(context.session);
    const row = marathonOf(context.params.marathon_id);
    const book = bookOf(row);
    const before = JSON.parse(JSON.stringify(runsOf(row)));
    const done = work(row);
    settle(row);
    const id = book.next;
    book.next += 1;
    book.undo.push({ move_id: id, text: done.text, runs: before });
    if (book.undo.length > UNDO_DEPTH) book.undo.shift();
    const by = actorOf(context.session);
    book.moves.unshift({ id, at: iso(Date.now()), by_id: by, by_name: memberName(by), kind, text: done.text, undone: false });
    logAction(`web.marathon.runsheet_${kind}`, { details: { marathon_id: row.id, ...done.details, via: 'website' } });
    return payload(row, typeof done.message === 'function' ? done.message() : done.message);
  }

  function runOf(row, id) {
    const run = runsOf(row).find((one) => String(one.id) === String(id));
    if (!run) throw new Refused(404, 'no_such_run', `That run is not on **${row.name}**'s run sheet any more, so nothing was done. Reload the page to see the sheet as it stands.`);
    return run;
  }

  function refuseReadOnly(row) {
    if (editableOf(row)) return;
    const word = marathonRow(row).source_word;
    throw new Refused(409, 'tracker_times', `**${row.name}**'s times come from ${word}, which moves them itself, so a time set here would be overwritten at its next read. Nothing was changed. On this sheet staff can mark a run **Started now** or **Finished now**; to change a time, change it on ${word}.`);
  }

  function timed(row, run) {
    return sheet(row).find((one) => one.run === run);
  }

  function later(row, run) {
    const rows = sheet(row);
    const mine = rows.find((one) => one.run === run);
    return rows.filter((one) => one.day === mine.day && one.plan > mine.plan && one.run.state === 'upcoming');
  }

  function dropLaterStaffTimes(row, run) {
    const held = later(row, run).filter((one) => one.run.staff_at);
    for (const one of held) delete one.run.staff_at;
    return held.length;
  }

  function offWords(minutes) {
    if (minutes === 0) return 'on its sheet time';
    return `${Math.abs(minutes)} min ${minutes > 0 ? 'behind' : 'ahead of'} its sheet time`;
  }

  function refuseBeforeBegun(row, run, target, said) {
    const rows = sheet(row);
    const mine = rows.find((one) => one.run === run);
    const ahead = rows.filter((one) => one.day === mine.day && one.plan < mine.plan && ['live', 'done'].includes(one.run.state)).at(-1);
    if (ahead && target < ahead.start) {
      throw new Refused(409, 'before_the_run_ahead', `**${said}** is before **${ahead.run.game}** started (${clock(ahead.start)}), and a run cannot start before the one ahead of it. Nothing was changed. Pick a time after ${clock(ahead.start)}.`);
    }
  }

  route('GET', '/api/marathons/:marathon_id/runsheet', (context) => {
    requireStaff(context.session);
    return payload(marathonOf(context.params.marathon_id));
  });

  route('POST', '/api/marathons/:marathon_id/runsheet/runs/:run_id/start', (context) => move(context, 'started', (row) => {
    const run = runOf(row, context.params.run_id);
    if (run.state !== 'upcoming') throw new Refused(409, 'not_startable', `**${run.game}** is ${STATE_WORDS[run.state] || run.state}, so nothing was changed. Only a run that has not started can be marked **Started now**; **Undo last move** takes back a press made by mistake.`);
    const now = Math.floor(Date.now() / MIN) * MIN;
    const was = timed(row, run);
    const closed = runsOf(row).filter((one) => one.state === 'live');
    for (const one of closed) Object.assign(one, { state: 'done', actual_ended_at: iso(now) });
    const cleared = editableOf(row) ? dropLaterStaffTimes(row, run) : 0;
    delete run.staff_at;
    Object.assign(run, { state: 'live', live_because: 'staff', actual_started_at: iso(now), actual_ended_at: null });
    const off = Math.round((now - was.plan) / MIN);
    const follow = editableOf(row)
      ? ` The ${plural(later(row, run).length, 'run')} after it follow from here${cleared ? `, and ${plural(cleared, 'staff time')} on them ${cleared === 1 ? 'was' : 'were'} dropped` : ''}.`
      : ' The other times stay the tracker’s.';
    return {
      text: `**${run.game}** started at ${clock(now)} (the sheet said ${clock(was.plan)})`,
      details: { run_id: run.id, before: iso(was.start), after: iso(now), closed: closed.map((one) => one.id) },
      message: `**${run.game}** started at ${clock(now)}, ${offWords(off)}.${closed.length ? ` **${closed.map((one) => one.game).join(', ')}** was marked finished at the same moment.` : ''}${follow}`,
    };
  }));

  route('POST', '/api/marathons/:marathon_id/runsheet/runs/:run_id/finish', (context) => move(context, 'finished', (row) => {
    const run = runOf(row, context.params.run_id);
    if (run.state !== 'live') throw new Refused(409, 'not_live', `**${run.game}** is ${STATE_WORDS[run.state] || run.state}, so nothing was changed. Only the run that is live can be marked **Finished now**.`);
    const now = Math.floor(Date.now() / MIN) * MIN;
    const was = timed(row, run);
    const cleared = editableOf(row) ? dropLaterStaffTimes(row, run) : 0;
    Object.assign(run, { state: 'done', actual_ended_at: iso(now) });
    return {
      text: `**${run.game}** finished at ${clock(now)}`,
      details: { run_id: run.id, before: iso(was.end), after: iso(now) },
      message: () => {
        const next = later(row, run)[0];
        if (!editableOf(row)) return `**${run.game}** finished at ${clock(now)}. The other times stay the tracker’s.`;
        if (!next) return `**${run.game}** finished at ${clock(now)}. Nothing is left to start that day.`;
        return `**${run.game}** finished at ${clock(now)}. The next run, **${next.run.game}**, is now due at ${clock(next.start)} and the rest follow${cleared ? `; ${plural(cleared, 'staff time')} on them ${cleared === 1 ? 'was' : 'were'} dropped` : ''}.`;
      },
    };
  }));

  route('POST', '/api/marathons/:marathon_id/runsheet/runs/:run_id/set-start', async (context) => {
    const body = await context.body();
    return move(context, 'start_set', (row) => {
      refuseReadOnly(row);
      const run = runOf(row, context.params.run_id);
      if (run.state !== 'upcoming') throw new Refused(409, 'not_movable', `**${run.game}** is ${STATE_WORDS[run.state] || run.state}, so its start was not changed. Only a run that has not started takes a new start time.`);
      const wanted = clockOf(body.time);
      if (!wanted) throw new Refused(400, 'bad_time', `**${String(body.time ?? '').slice(0, 20) || 'Nothing'}** is not a time, so nothing was changed. Type it like **14:30** (24-hour, ${zone()} time).`);
      const was = timed(row, run);
      const target = clockNear(was.start, wanted.hour, wanted.minute, zone());
      if (target === was.start) throw new Refused(409, 'same_time', `**${run.game}** already starts at ${clock(target)}, so nothing was changed.`);
      refuseBeforeBegun(row, run, target, clock(target));
      const delta = target - was.start;
      const after = later(row, run);
      for (const one of after.filter((each) => each.run.staff_at)) one.run.staff_at = iso(ms(one.run.staff_at) + delta);
      run.staff_at = iso(target);
      const by = Math.round(Math.abs(delta) / MIN);
      return {
        text: `**${run.game}** set to start at ${clock(target)} (was ${clock(was.start)})`,
        details: { run_id: run.id, before: iso(was.start), after: iso(target) },
        message: `**${run.game}** now starts at ${clock(target)} (was ${clock(was.start)}). The ${plural(after.length, 'run')} after it keep their gaps, so each starts ${by} min ${delta > 0 ? 'later' : 'earlier'}.`,
      };
    });
  });

  route('POST', '/api/marathons/:marathon_id/runsheet/shift', async (context) => {
    const body = await context.body();
    return move(context, 'shifted', (row) => {
      refuseReadOnly(row);
      const minutes = Number(body.minutes);
      if (!Number.isInteger(minutes) || minutes === 0 || Math.abs(minutes) > SHIFT_LIMIT) {
        throw new Refused(400, 'bad_minutes', `**${String(body.minutes ?? '').slice(0, 20) || 'Nothing'}** is not a number of minutes to move by, so nothing was changed. Type a whole number from 1 to ${SHIFT_LIMIT}, then press **Behind** or **Ahead**.`);
      }
      const day = dayOf(row, body.day);
      const waiting = day.rows.filter((one) => one.run.state === 'upcoming');
      if (!waiting.length) throw new Refused(409, 'nothing_to_move', `Every run on ${day.label} has started already, so there is nothing left to move.`);
      const [first] = waiting;
      const target = first.start + minutes * MIN;
      refuseBeforeBegun(row, first.run, target, `${Math.abs(minutes)} min ahead`);
      for (const one of waiting.slice(1).filter((each) => each.run.staff_at)) one.run.staff_at = iso(ms(one.run.staff_at) + minutes * MIN);
      first.run.staff_at = iso(target);
      const way = minutes > 0 ? 'later' : 'earlier';
      return {
        text: `Every run not yet started on ${day.label} moved ${Math.abs(minutes)} min ${way}`,
        details: { day: day.key, minutes, runs: waiting.length, before: iso(first.start), after: iso(target) },
        message: `Every run not yet started on ${day.label} now starts **${Math.abs(minutes)} min ${way}**: ${plural(waiting.length, 'run')}, from **${first.run.game}** (${clock(first.start)} → ${clock(target)}). Live and finished runs did not move.`,
      };
    });
  });

  route('POST', '/api/marathons/:marathon_id/runsheet/runs/:run_id/estimate', async (context) => {
    const body = await context.body();
    return move(context, 'estimate_set', (row) => {
      refuseReadOnly(row);
      const run = runOf(row, context.params.run_id);
      if (!['upcoming', 'live'].includes(run.state)) throw new Refused(409, 'not_movable', `**${run.game}** is ${STATE_WORDS[run.state] || run.state}, so its estimate was not changed. Only a run that is live or has not started takes a new estimate.`);
      const minutes = minutesOf(body.estimate);
      if (minutes === null || minutes < 1 || minutes > ESTIMATE_LIMIT) {
        throw new Refused(400, 'bad_estimate', `**${String(body.estimate ?? '').slice(0, 20) || 'Nothing'}** is not a run length, so nothing was changed. Type it like **1:20**, or as minutes like **45** — from 1 minute to ${ESTIMATE_LIMIT / 60} hours.`);
      }
      const was = Math.round(lengthOf(run) / MIN);
      if (minutes === was) throw new Refused(409, 'same_estimate', `**${run.game}** is booked for ${lengthWords(was)} already, so nothing was changed.`);
      if (minutes * 60 === Math.round(sourceLength(run) / 1000)) delete run.staff_estimate_seconds;
      else run.staff_estimate_seconds = minutes * 60;
      const by = Math.abs(minutes - was);
      const after = later(row, run);
      const held = after.findIndex((one) => one.run.staff_at);
      const following = held === -1 ? after.length : held;
      const way = minutes > was ? 'later' : 'earlier';
      const moved = following ? `The ${plural(following, 'run')} right after it ${following === 1 ? 'starts' : 'start'} ${by} min ${way}` : 'No later run moved';
      const stopped = held === -1 ? '' : `; **${after[held].run.game}** keeps the time staff set, and so does everything after it`;
      return {
        text: `**${run.game}** estimate set to ${lengthWords(minutes)} (was ${lengthWords(was)})`,
        details: { run_id: run.id, before: was * 60, after: minutes * 60 },
        message: `**${run.game}** is now booked for ${lengthWords(minutes)} (was ${lengthWords(was)}). ${moved}${stopped}.`,
      };
    });
  });

  route('POST', '/api/marathons/:marathon_id/runsheet/runs/:run_id/skip', (context) => move(context, 'skipped', (row) => {
    refuseReadOnly(row);
    const run = runOf(row, context.params.run_id);
    if (run.state !== 'upcoming') throw new Refused(409, 'not_skippable', `**${run.game}** is ${STATE_WORDS[run.state] || run.state}, so nothing was changed. Only a run that has not started can be skipped; a live run is ended with **Finished now**.`);
    const after = later(row, run);
    const was = timed(row, run);
    delete run.staff_at;
    Object.assign(run, { state: 'dropped', skipped_by: actorOf(context.session), skipped_at: iso(Date.now()) });
    return {
      text: `**${run.game}** skipped`,
      details: { run_id: run.id, before: iso(was.start), after: null },
      message: () => {
        const next = after.length ? timed(row, after[0].run) : null;
        return `**${run.game}** is skipped.${next ? ` The runs after it close the gap: **${next.run.game}** now starts at ${clock(next.start)}.` : ''} **Bring it back** on its row undoes it.`;
      },
    };
  }));

  route('POST', '/api/marathons/:marathon_id/runsheet/runs/:run_id/restore', (context) => move(context, 'restored', (row) => {
    refuseReadOnly(row);
    const run = runOf(row, context.params.run_id);
    if (run.state !== 'dropped') throw new Refused(409, 'not_skipped', `**${run.game}** is ${STATE_WORDS[run.state] || run.state}, not skipped, so nothing was changed.`);
    Object.assign(run, { state: 'upcoming', live_because: null });
    delete run.skipped_by;
    delete run.skipped_at;
    return {
      text: `**${run.game}** brought back`,
      details: { run_id: run.id },
      message: () => `**${run.game}** is back on the sheet at ${clock(timed(row, run).start)}, and the runs after it make room again.`,
    };
  }));

  route('POST', '/api/marathons/:marathon_id/runsheet/reset', async (context) => {
    const body = await context.body();
    return move(context, 'reset', (row) => {
      refuseReadOnly(row);
      const day = dayOf(row, body.day);
      const times = day.rows.filter((one) => one.run.staff_at);
      const estimates = day.rows.filter((one) => one.run.staff_estimate_seconds);
      if (!times.length && !estimates.length) throw new Refused(409, 'not_retimed', `${day.label} carries no staff time and no staff estimate, so it is on the source's times already and nothing was changed.`);
      for (const one of times) delete one.run.staff_at;
      for (const one of estimates) delete one.run.staff_estimate_seconds;
      return {
        text: `${day.label} put back on the source's times`,
        details: { day: day.key, times: times.length, estimates: estimates.length },
        message: `${day.label} is back on the source's times: ${plural(times.length, 'staff time')} and ${plural(estimates.length, 'staff estimate')} forgotten. Runs that really started or finished keep what happened, and skipped runs stay skipped.`,
      };
    });
  });

  route('POST', '/api/marathons/:marathon_id/runsheet/undo', (context) => {
    requireStaff(context.session);
    const row = marathonOf(context.params.marathon_id);
    const book = bookOf(row);
    const last = book.undo.pop();
    if (!last) throw new Refused(409, 'nothing_to_undo', `No staff move has been made on **${row.name}**'s run sheet since the bot started, so there is nothing to undo.`);
    restore(row, last.runs);
    const undone = book.moves.find((one) => one.id === last.move_id);
    if (undone) undone.undone = true;
    const by = actorOf(context.session);
    const id = book.next;
    book.next += 1;
    book.moves.unshift({ id, at: iso(Date.now()), by_id: by, by_name: memberName(by), kind: 'undone', text: `Undid: ${last.text}`, undone: false });
    logAction('web.marathon.runsheet_undone', { details: { marathon_id: row.id, move_id: last.move_id, via: 'website' } });
    return payload(row, `Undone: ${last.text}. The sheet is as it was before that move.`);
  });
}
