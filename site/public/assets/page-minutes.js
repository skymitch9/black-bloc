import { api, listOf, names, notesOf, send, settings, settingsNamespace } from './api.js';
import { start } from './app.js';
import { logsSection } from './logs.js';
import {
  ask,
  bar,
  button,
  card,
  el,
  idsIn,
  nameNode,
  notice,
  run,
  sayNothing,
  section,
  settingsPanel,
  table,
} from './ui.js';

let refresh = () => {};
let openMeeting = null;

const NOTES_PLACEHOLDER = 'Nothing has been written up for this meeting yet.';
const NO_TRANSCRIPT = 'No words were transcribed for this meeting.';
const RECORDING_NOTE = 'This meeting is still being recorded. Press Stop on /minutes in Discord ' +
  'first — the notes are written then.';

function when(value) {
  const text = String(value || '');
  return text ? text.slice(0, 16).replace('T', ' ') : '—';
}

function hostLines(host) {
  if (!host) return [];
  const missing = [];
  if (host.extension === false) missing.push('the voice-recording extension');
  if (host.opus === false) missing.push('the Opus audio library');
  if (host.transcriber === false) missing.push('a speech-to-text key');
  if (host.notes_writer === false) missing.push('a writing key');
  if (missing.length === 0) return [];
  return [`This host is missing ${missing.join(', ')}, so a meeting cannot be recorded end to end here.`];
}

function transcriptCard(rows) {
  if (rows.length === 0) return card('Transcript', [sayNothing(NO_TRANSCRIPT)]);
  return card('Transcript', [
    el('p', { class: 'field-help', text: `${rows.length} line(s), oldest first. Deleted after minutes_keep_days.` }),
    table([
      { label: 'When', cell: (row) => when(row.started_at), className: 'mono' },
      { label: 'Who', cell: (row) => row.speaker },
      { label: 'Said', cell: (row) => row.text },
    ], rows, { search: rows.length > 10 }),
  ]);
}

function notesCard(payload) {
  const meeting = payload.meeting || {};
  const say = notice();
  const recording = meeting.status === 'recording';
  const box = el('textarea', {
    class: 'input',
    rows: '14',
    maxlength: String(meeting.notes_cap || 4000),
    placeholder: NOTES_PLACEHOLDER,
  });
  box.value = String(meeting.notes || '');

  const save = button('Save the notes', async () => {
    const done = await run(
      say,
      () => send(`/api/minutes/${encodeURIComponent(meeting.id)}`, 'PUT', { notes: box.value }),
      (found) => found?.message || 'Saved.',
    );
    if (done.ok) refresh();
  }, { tone: 'primary', small: false });

  const again = button('Write the notes again', async () => {
    const sure = await ask({
      title: 'Write these notes again?',
      body: [
        'Black Bloc reads the transcript again and replaces what is in the box.',
        'Anything typed here by hand is lost. The transcript itself is untouched.',
      ],
      confirmLabel: 'Write them again',
      tone: 'warn',
    });
    if (!sure) return;
    const done = await run(
      say,
      () => send(`/api/minutes/${encodeURIComponent(meeting.id)}/write`, 'POST', {}),
      (found) => found?.message || 'Written.',
    );
    if (done.ok) refresh();
  }, { tone: 'warn' });

  const post = button('Post again', async () => {
    const done = await run(
      say,
      () => send(`/api/minutes/${encodeURIComponent(meeting.id)}/post`, 'POST', {}),
      (found) => found?.message || 'Posted.',
    );
    if (done.ok) refresh();
  });

  const remove = button('Delete this meeting', async () => {
    const sure = await ask({
      title: `Delete meeting #${meeting.id}?`,
      body: [
        'The notes and every word of the transcript go with it.',
        'Nothing puts them back, and the message already posted in Discord is left where it is.',
      ],
      confirmLabel: 'Delete it',
    });
    if (!sure) return;
    const done = await run(
      say,
      () => api(`/api/minutes/${encodeURIComponent(meeting.id)}`, { method: 'DELETE' }),
      (found) => found?.message || 'Deleted.',
    );
    if (done.ok) {
      openMeeting = null;
      refresh();
    }
  }, { tone: 'danger' });

  const moves = recording ? [remove] : [save, again, post, remove];
  return card(`Meeting #${meeting.id}`, [
    el('p', { class: 'field-help', text: `${meeting.channel_name} · started ${when(meeting.started_at)} · ${meeting.status_words}${meeting.ended_reason ? ` (${meeting.ended_reason})` : ''}` }),
    recording ? sayNothing(RECORDING_NOTE) : box,
    bar(moves),
    say,
    transcriptCard(listOf(payload, 'transcript')),
  ]);
}

async function meetingsTable(rows, say) {
  await names(idsIn(rows, ['started_by']));
  return table([
    { label: '#', cell: (row) => String(row.id), className: 'mono' },
    { label: 'Where', cell: (row) => row.channel_name },
    { label: 'Started', cell: (row) => when(row.started_at), className: 'mono' },
    { label: 'By', cell: (row) => nameNode(row.started_by, row.started_by_name) },
    { label: 'How it stands', cell: (row) => row.status_words },
    { label: 'Posted', cell: (row) => (row.posted ? row.notes_channel_name : 'not posted') },
    {
      label: '',
      cell: (row) => button(openMeeting === row.id ? 'Close' : 'Open', () => {
        openMeeting = openMeeting === row.id ? null : row.id;
        refresh();
      }, { tone: openMeeting === row.id ? 'quiet' : null }),
    },
  ], rows, { search: rows.length > 10, empty: say });
}

async function load() {
  const [payload, allSettings] = await Promise.all([api('/api/minutes'), settings(true)]);
  const rows = listOf(payload, 'meetings');

  const list = section('Meetings', `${rows.length} recorded.`, { count: rows.length });
  for (const line of notesOf(payload)) list.body.append(el('p', { class: 'field-help', text: line }));
  for (const line of hostLines(payload.host)) list.body.append(el('p', { class: 'field-help', text: line }));
  if (payload.guard && payload.guard.said) {
    list.body.append(el('p', { class: 'field-help', text: payload.guard.said }));
  }
  if (rows.length === 0) {
    list.body.append(sayNothing('No meeting has been recorded yet. Run /minutes in Discord while you are in the voice channel.'));
  } else {
    list.body.append(await meetingsTable(rows, 'No meeting matches that.'));
  }

  const one = section('The meeting you opened');
  if (openMeeting && rows.some((row) => row.id === openMeeting)) {
    const found = await api(`/api/minutes/${encodeURIComponent(openMeeting)}`);
    one.body.append(notesCard(found));
  } else {
    one.body.append(sayNothing('Press Open beside a meeting to read its notes and its transcript.'));
  }

  const specs = settingsNamespace(allSettings, 'events').filter((spec) => spec.key.startsWith('minutes_'));
  const keys = section('Settings', 'Filed under events, because the /settings group picker is full.', { count: specs.length || null });
  keys.body.append(await settingsPanel(specs, {
    where: 'Minutes',
    empty: 'The bot registers no minutes settings.',
  }));

  document.getElementById('dash').replaceChildren(
    list.node,
    one.node,
    keys.node,
    await logsSection('minutes'),
  );
}

refresh = start({
  tab: 'minutes',
  load,
});
