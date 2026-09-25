// The Events page's marathon words, proved without a browser: the drawer's card order, the
// Schedule card's reading line, the table's Schedule cell and the Sources foldout's title.
//
//   node --test site/mock/marathon-words.test.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

import {
  BAF,
  countsLine,
  drawerCards,
  feedReading,
  postsLines,
  readingLine,
  scheduleCell,
  sourcesTitle,
} from '../public/assets/marathon-words.js';

const NOW = Date.parse('2026-09-25T18:00:00Z');
const at = (minutes) => new Date(NOW + minutes * 60000).toISOString();
const CADENCE = { near: 30, far: 24 };

test('the drawer opens on the Schedule card and keeps every card', () => {
  assert.deepEqual(drawerCards(), ['Schedule', 'Runs', 'Who is who', 'Event', 'The channel', 'Posts']);
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
