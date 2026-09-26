// The Events page's marathon words, proved without a browser: the drawer's card order, the
// Schedule card's reading line, the table's Schedule cell and the Sources foldout's title.
//
//   node --test site/mock/marathon-words.test.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

import {
  BAF,
  countsLine,
  dayTitle,
  daysOf,
  drawerCards,
  entryFor,
  runChip,
  runLength,
  slotMatches,
  slotPeople,
  slotTime,
  sourceCell,
  feedReading,
  postsLines,
  readingLine,
  scheduleCell,
  sourcesTitle,
} from '../public/assets/marathon-words.js';

const NOW = Date.parse('2026-09-25T18:00:00Z');
const at = (minutes) => new Date(NOW + minutes * 60000).toISOString();
const CADENCE = { near: 30, far: 24 };

test('the drawer opens on the Schedule card, then People — Runs and Who is who are folded into it', () => {
  assert.deepEqual(drawerCards(), ['Schedule', 'People', 'Event', 'The channel', 'Posts']);
});

test('the word a person reads is BaF', () => {
  assert.equal(BAF, 'BaF');
  assert.equal(countsLine([{ state: 'done', ours: true }, { state: 'live', ours: false }, { state: 'upcoming', ours: true }, { state: 'dropped', ours: true }]), '3 runs · 2 BaF · 1 done · 1 on now');
  assert.equal(countsLine([]), 'No runs yet — nothing published.');
});

test('a healthy read says when it was, when it is next, and the cadence', () => {
  const found = readingLine({ active: true, last_fetch_ok: true, last_fetched_at: at(-20), next_read_at: at(10), poll_minutes: null }, CADENCE, NOW);
  assert.equal(found.text, 'Last read 20 min ago · next read in 10 min · every 30 min while it is near, every 24 h when it is far');
  assert.equal(found.tone, null);
  const own = readingLine({ active: true, last_fetched_at: at(-5), next_read_at: at(5), poll_minutes: 10 }, CADENCE, NOW);
  assert.match(own.text, /every 10 min while it is near/);
});

test('a failed read says why, in the warn tone, and when it is tried again', () => {
  const found = readingLine({ active: true, last_fetch_ok: false, last_fetched_at: at(-30), last_error: 'the GDQ tracker has the event but has not published its schedule yet', next_read_at: at(10) }, CADENCE, NOW);
  assert.equal(found.tone, 'warn');
  assert.match(found.text, /^Could not be read since .+ — the GDQ tracker has the event but has not published its schedule yet; read again in 10 min$/);
});

test('a paused marathon says it is paused, never a next read', () => {
  const found = readingLine({ active: false, last_fetched_at: at(-60), next_read_at: null }, CADENCE, NOW);
  assert.equal(found.text, 'Last read 1 h ago · paused — not read until it is resumed');
});

test('the table cell is short', () => {
  assert.equal(scheduleCell({ active: true, last_fetched_at: at(-19), runs: 11, next_read_at: at(11) }, NOW), 'read 19 min ago');
  assert.equal(scheduleCell({ active: true, last_fetched_at: at(-19), runs: 0, next_read_at: at(10) }, NOW), 'not published — again in 10 min');
  assert.equal(scheduleCell({ active: true, last_fetch_ok: false, last_fetched_at: at(-19), next_read_at: at(10) }, NOW), 'could not be read — again in 10 min');
  assert.equal(scheduleCell({ active: false }, NOW), 'paused');
});

test('a feed reads in the same shape, and the foldout title names the soonest check', () => {
  const feeds = [
    { active: true, hours: 6, last_checked_at: at(-19), last_ok: true },
    { active: true, hours: 6, last_checked_at: at(-300), last_ok: true },
    { active: false, hours: 6, last_checked_at: at(-10), last_ok: true },
  ];
  assert.equal(feedReading(feeds[0], NOW).text, 'every 6 h · last 19 min ago · next in 5 h 41 min');
  assert.equal(feedReading(feeds[2], NOW).text, 'every 6 h · last 10 min ago · paused');
  assert.equal(sourcesTitle(feeds, {}, NOW), 'Where marathons come from · 3 sources · next check in 1 h');
  assert.equal(sourcesTitle(feeds, { enabled: false }, NOW), 'Where marathons come from · 3 sources · checks are off');
});

test('posts count the reminders and shoutouts from the runs', () => {
  const found = postsLines({ board_message_id: '1', board_pinned: true, run_list: [{ reminders_sent: [120, 15], shouted: true }, { reminders_sent: [], shouted: false }] });
  assert.equal(found.board, 'Board: up and pinned in');
  assert.equal(found.sent, 'Reminders: 2 sent · Shoutouts: 1');
  assert.equal(postsLines({ run_list: [] }).board, 'Board: none yet.');
});

test('the table names the source, and a feed-made row says so', () => {
  assert.equal(sourceCell({ source_word: 'GDQ tracker', feed_id: 1 }), 'GDQ tracker · feed');
  assert.equal(sourceCell({ source_word: 'horaro.net', feed_id: null }), 'horaro.net');
});

// 2027-01-12 is a Tuesday; 20:00 UTC is 13:00 in Phoenix (UTC-7, no DST).
const DAY_NOW = Date.parse('2027-01-12T20:00:00Z');
const t = (minutes) => new Date(DAY_NOW + minutes * 60000).toISOString();
const RUNS = [
  { id: 1, game: 'Halo 2', scheduled_at: t(-300), ends_at: t(-240), state: 'done', ours: true, people: [] },
  { id: 2, game: 'Super Mario 64', category: '16 Star', scheduled_at: t(-20), ends_at: t(23), state: 'live', ours: true, people: [
    { name: 'Moth', part: 'commentator', user_id: '4' },
    { name: 'Casey', login: 'caseyfast', part: 'runner', user_id: '2' },
    { name: 'TheKing', login: 'thekingspride', part: 'runner', user_id: null },
  ] },
  { id: 3, game: 'Celeste', scheduled_at: t(1500), ends_at: t(1560), state: 'upcoming', ours: false, people: [] },
  { id: 4, game: 'Kirby', scheduled_at: t(3000), ends_at: t(3060), state: 'upcoming', ours: true, people: [] },
  { id: 5, game: 'Dropped', scheduled_at: t(10), ends_at: t(70), state: 'dropped', ours: true, people: [] },
  { id: 6, game: 'Yesterday', scheduled_at: t(-1500), ends_at: t(-1440), state: 'done', ours: false, people: [] },
];

test('the schedule goes by day in the guild zone: today open, past shut, future shut unless BaF', () => {
  const days = daysOf(RUNS, 'America/Phoenix', DAY_NOW);
  assert.deepEqual(days.map((one) => one.label), ['Mon 11 Jan', 'Tue 12 Jan', 'Wed 13 Jan', 'Thu 14 Jan']);
  assert.deepEqual(days.map((one) => one.runs.length), [1, 2, 1, 1]);
  assert.deepEqual(days.map((one) => one.open), [false, true, false, true]);
  assert.equal(days[1].today, true);
  assert.equal(dayTitle(days[1]), 'Tue 12 Jan · 2 slots · 2 BaF');
  assert.equal(dayTitle(days[2]), 'Wed 13 Jan · 1 slot · 0 BaF');
});

test('a slot reads its time, its length, runners first, and a BaF run is a short chip', () => {
  assert.equal(slotTime(RUNS[1].scheduled_at, 'America/Phoenix'), '12:40');
  assert.equal(runLength(RUNS[1]), '0:43');
  assert.deepEqual(slotPeople(RUNS[1]).map((one) => one.name), ['Casey', 'TheKing', 'Moth']);
  assert.equal(runChip(RUNS[1], 'America/Phoenix'), 'Tue 12 Jan 12:40 Super Mario 64');
  assert.ok(slotMatches(RUNS[1], 'thekings'));
  assert.ok(slotMatches(RUNS[1], 'mario'));
  assert.ok(!slotMatches(RUNS[1], 'celeste'));
});

test('a person on a slot finds their line in the People answer', () => {
  const board = {
    baf: [{ name: 'Casey', runs: [{ id: 2, name: 'Casey', part: 'runner' }] }],
    others: [{ name: 'TheKing', runs: [{ id: 2, name: 'TheKing', part: 'runner' }] }],
  };
  assert.equal(entryFor(board, 2, RUNS[1].people[1]).name, 'Casey');
  assert.equal(entryFor(board, 2, RUNS[1].people[2]).name, 'TheKing');
  assert.equal(entryFor(board, 3, RUNS[1].people[2]), null);
});
