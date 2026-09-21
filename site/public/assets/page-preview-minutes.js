import { start } from './app.js';
import {
  ago,
  badge,
  bar,
  button,
  card,
  channelLabel,
  el,
  field,
  foldout,
  icon,
  nameNode,
  notice,
  openDrawer,
  sayNothing,
  searchField,
  section,
  segment,
  table,
} from './ui.js';
import { previewBanner, previewWas, wouldDo } from './preview.js';

const DATA = {
  "meetings": [
    {
      "id": "1",
      "channel_id": "800000000000000009",
      "channel_name": "#Join to create",
      "started_by": "700000000000000001",
      "started_by_name": "Nick",
      "started_at": "2026-09-20T20:35:42.365Z",
      "ended_at": "2026-09-20T21:15:42.365Z",
      "ended_reason": "by hand",
      "status": "done",
      "status_words": "done",
      "notes": "**In short**\nThe meeting-minutes prototype ships off and is tested by staff only.\n\n**Decisions**\n- Nobody turns it on until it has been tested.\n\n**Action items**\n- Casey: write the guide.\n\n**Left open**\n- Which channel the notes should land in once it is on.",
      "notes_cap": 4000,
      "notes_channel_id": "800000000000000003",
      "notes_channel_name": "#blackbloc-logs",
      "notes_message_id": "830000000000000001",
      "posted": true,
      "lines": 3
    },
    {
      "id": "2",
      "channel_id": "800000000000000009",
      "channel_name": "#Join to create",
      "started_by": "700000000000000001",
      "started_by_name": "Nick",
      "started_at": "2026-09-20T23:51:42.365Z",
      "ended_at": null,
      "ended_reason": null,
      "status": "recording",
      "status_words": "recording",
      "notes": "",
      "notes_cap": 4000,
      "notes_channel_id": null,
      "notes_channel_name": "nowhere yet",
      "notes_message_id": null,
      "posted": false,
      "lines": 0
    }
  ],
  "mode": "off",
  "guard": {
    "test_mode": true,
    "test_channel": "blackbloc-logs",
    "said": "Black Bloc is in test mode, so a meeting’s announcement and its notes land in #blackbloc-logs rather than the channel they name. **Post again** obeys the same rule."
  },
  "host": {
    "extension": true,
    "opus": true,
    "transcriber": true,
    "notes_writer": true
  },
  "notes": [
    "Meeting minutes are off for this server, so `/minutes` is hidden and Start refuses in words. This is a prototype and it ships off on purpose. Every meeting already recorded is kept — a Lead turns it on from the Settings page under **events**."
  ],
  "detail": {
    "1": {
      "transcript": [
        {
          "id": "1",
          "speaker": "Mod",
          "speaker_id": "700000000000000001",
          "started_at": "2026-09-20T20:36:42.365Z",
          "text": "We should ship the prototype off by default."
        },
        {
          "id": "2",
          "speaker": "Casey",
          "speaker_id": "700000000000000002",
          "started_at": "2026-09-20T20:37:42.365Z",
          "text": "I will write the guide for it."
        },
        {
          "id": "3",
          "speaker": "Mod",
          "speaker_id": "700000000000000001",
          "started_at": "2026-09-20T20:38:42.365Z",
          "text": "Agreed. Nobody turns it on until we have tested it."
        }
      ],
      "speakers": [
        "Mod",
        "Casey"
      ]
    },
    "2": {
      "transcript": [],
      "speakers": []
    }
  },
  "settings": [
    {
      "key": "minutes_mode",
      "type": "enum",
      "value": "off",
      "default": "off",
      "help": "off or on. This is a PROTOTYPE and it ships off: while it is off `/minutes` is hidden and both doors refuse in words. On lets staff have Black Bloc join the voice channel they are in and take notes; it always announces itself first, and the audio is never stored",
      "choices": [
        "off",
        "on"
      ]
    },
    {
      "key": "minutes_channel_id",
      "type": "channel",
      "value": null,
      "default": null,
      "help": "where a meeting’s announcement and its notes go; blank means the voice channel’s own text chat. While test mode is on, both land in the test channel or the rehearsal home instead, and the panel says where they went"
    },
    {
      "key": "minutes_opt_out_role_id",
      "type": "role",
      "value": null,
      "default": null,
      "help": "a role that means do not record me: if anybody in the voice channel is wearing it, Start refuses and names them. Blank means nobody can opt out that way"
    },
    {
      "key": "minutes_start_text",
      "type": "text",
      "value": "🔴 Black Bloc is taking notes in this meeting. Say **stop notes** or press Stop on /minutes to end it.",
      "default": "🔴 Black Bloc is taking notes in this meeting. Say **stop notes** or press Stop on /minutes to end it.",
      "help": "the message Black Bloc posts the moment it joins a meeting, before a word is recorded. It cannot be blank — a meeting that is recorded silently is the one thing this feature must never do"
    },
    {
      "key": "minutes_notes_title",
      "type": "text",
      "value": "Meeting notes",
      "default": "Meeting notes",
      "help": "the heading on the notes embed when a meeting is written up"
    },
    {
      "key": "minutes_prompt",
      "type": "text",
      "value": "You are writing the minutes of a voice meeting from an automatic transcript.",
      "default": "You are writing the minutes of a voice meeting from an automatic transcript.",
      "help": "what Black Bloc asks the model for when it turns a transcript into notes. The transcript is sent after it, so write instructions rather than content"
    },
    {
      "key": "minutes_chunk_seconds",
      "type": "int",
      "value": 60,
      "default": 60,
      "help": "how much of one person’s speech is gathered before it is sent to be transcribed; 60 by default, 30–120. Nothing reaches the transcript until a chunk is finished, so this is also how far behind the live meeting the transcript runs",
      "max": 120,
      "min": 30
    },
    {
      "key": "minutes_max_hours",
      "type": "int",
      "value": 3,
      "default": 3,
      "help": "the longest a single meeting may be recorded before Black Bloc leaves and writes the notes anyway; 3 by default. It is what stops a bot left in an empty channel recording all night",
      "max": 6,
      "min": 1
    },
    {
      "key": "minutes_keep_days",
      "type": "int",
      "value": 90,
      "default": 90,
      "help": "how long a meeting’s TRANSCRIPT is kept before it is deleted; 90 days by default. The notes and the meeting itself are kept until somebody deletes them",
      "max": 365,
      "min": 1
    },
    {
      "key": "minutes_panel_minutes",
      "type": "int",
      "value": 10,
      "default": 10,
      "help": "minutes the /minutes panel stays live before its buttons disable themselves; 10 by default. The 'this panel has gone quiet' footer can only be written while Discord's 15-minute interaction window is still open, so 15 or more means the buttons simply stop working with no footer to explain it",
      "max": 1440,
      "min": 1
    }
  ],
  "roles": [
    {
      "id": "900000000000000001",
      "name": "Aunties / Uncles",
      "color": "#e04a6d",
      "position": 12,
      "managed": false
    },
    {
      "id": "900000000000000002",
      "name": "Leads",
      "color": "#4eefff",
      "position": 14,
      "managed": false
    },
    {
      "id": "900000000000000003",
      "name": "Live now",
      "color": "#a35bff",
      "position": 5,
      "managed": false
    },
    {
      "id": "900000000000000004",
      "name": "Birthday",
      "color": "#ffd166",
      "position": 4,
      "managed": false
    },
    {
      "id": "900000000000000005",
      "name": "Members",
      "color": "#8a8f98",
      "position": 1,
      "managed": false
    },
    {
      "id": "900000000000000006",
      "name": "Server Booster",
      "color": "#f47fff",
      "position": 9,
      "managed": true
    },
    {
      "id": "900000000000000007",
      "name": "Events",
      "color": "#8a8f98",
      "position": 2,
      "managed": false
    },
    {
      "id": "900000000000000008",
      "name": "Casey pings",
      "color": "#8a8f98",
      "position": 3,
      "managed": false
    }
  ],
  "logs": [],
  "channels": [
    {
      "id": "800000000000000001",
      "name": "welcome",
      "type": "text",
      "category_id": null,
      "position": 0
    },
    {
      "id": "800000000000000002",
      "name": "general",
      "type": "text",
      "category_id": null,
      "position": 1
    },
    {
      "id": "800000000000000003",
      "name": "blackbloc-logs",
      "type": "text",
      "category_id": null,
      "position": 2
    },
    {
      "id": "800000000000000004",
      "name": "bot-log",
      "type": "text",
      "category_id": null,
      "position": 3
    },
    {
      "id": "800000000000000005",
      "name": "staff-room",
      "type": "text",
      "category_id": null,
      "position": 4
    },
    {
      "id": "800000000000000006",
      "name": "announcements",
      "type": "text",
      "category_id": null,
      "position": 5
    },
    {
      "id": "800000000000000007",
      "name": "free-nitro-here",
      "type": "text",
      "category_id": null,
      "position": 6
    },
    {
      "id": "800000000000000008",
      "name": "Events",
      "type": "category",
      "category_id": null,
      "position": 7
    },
    {
      "id": "800000000000000009",
      "name": "Join to create",
      "type": "voice",
      "category_id": null,
      "position": 8
    },
    {
      "id": "800000000000000010",
      "name": "casey's room",
      "type": "voice",
      "category_id": null,
      "position": 9
    },
    {
      "id": "800000000000000011",
      "name": "modmail",
      "type": "category",
      "category_id": null,
      "position": 10
    },
    {
      "id": "800000000000000012",
      "name": "modmail-log",
      "type": "text",
      "category_id": "800000000000000011",
      "position": 11
    }
  ]
};

const NOTES_PLACEHOLDER = 'Nothing has been written up for this meeting yet.';
const NO_TRANSCRIPT = 'No words were transcribed for this meeting.';
const RECORDING_NOTE = 'This meeting is still being recorded. Press Stop on /minutes in Discord '
  + 'first — the notes are written then.';
const NO_MEETINGS = 'No meeting has been recorded yet. Run /minutes in Discord while you are in '
  + 'the voice channel.';
const NO_MATCH = 'No meeting matches that.';
const SETTINGS_NOTE = 'Filed under events, because the /settings group picker is full.';
const LOGS_NOTE = 'Everything this part of Black Bloc has done, whether or not it said so in '
  + 'Discord. Important means it acted on a member or failed.';
const NOTHING_LOGGED = 'Minutes has logged nothing at all yet.';
const NOT_POSTED = 'not posted';

const WAS_MEETINGS = 'Replaces Meetings and The meeting you opened — the two sections a meeting '
  + 'used to live in at once. Open now opens a drawer over the table instead of a shut section '
  + 'nine lines further down.';
const WAS_MACHINERY = 'Replaces the Settings section and the Logs section — two shut headers '
  + 'become one, with a fold each.';

const state = { query: '' };
let refresh = () => {};

function full(node) {
  node.setAttribute('data-span', 'full');
  return node;
}

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

function transcriptOf(id) {
  const found = DATA.detail[String(id)];
  return (found && found.transcript) || [];
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

/**
 * What used to be `section('The meeting you opened')` — the section that was
 * never given `open: true`, so pressing Open appeared to do nothing. Here the
 * same card is the drawer's body, over the row that opened it.
 */
function meetingDrawer(meeting) {
  const say = notice();
  const recording = meeting.status === 'recording';
  const box = el('textarea', {
    class: 'input',
    rows: '14',
    maxlength: String(meeting.notes_cap || 4000),
    placeholder: NOTES_PLACEHOLDER,
  });
  box.value = String(meeting.notes || '');

  const save = button('Save the notes', () => wouldDo(say, `PUT /api/minutes/${meeting.id} — save the notes as they stand in this box`), { small: false, tone: 'warn' });
  const again = button('Write the notes again', () => wouldDo(say, `POST /api/minutes/${meeting.id}/write — read the transcript again and replace every word in the box`), { tone: 'warn' });
  const post = button('Post again', () => wouldDo(say, `POST /api/minutes/${meeting.id}/post — send the notes to ${meeting.notes_channel_name || 'nowhere yet'} again`));
  const remove = button('Delete this meeting', () => wouldDo(say, `DELETE /api/minutes/${meeting.id} — remove the meeting, its notes and every word of its transcript`), { tone: 'danger' });

  return [
    el('p', { class: 'field-help', text: `${meeting.channel_name} · started ${when(meeting.started_at)} · ${meeting.status_words}${meeting.ended_reason ? ` (${meeting.ended_reason})` : ''}` }),
    el('div', { class: 'postmarks' }, [
      badge(meeting.status_words, meeting.status === 'recording' ? 'warn' : 'ok'),
      meeting.posted
        ? badge(`posted in ${meeting.notes_channel_name}`, 'ok')
        : badge(NOT_POSTED, 'danger'),
    ]),
    recording ? sayNothing(RECORDING_NOTE) : box,
    bar(recording ? [remove] : [save, again, post, remove]),
    say,
    transcriptCard(transcriptOf(meeting.id)),
  ];
}

const COLUMNS = 'grid-template-columns: 12px 56px minmax(0, 1fr) 150px 130px 130px 170px 24px';

function meetingRow(meeting) {
  return el('button', {
    class: 'grid-row',
    type: 'button',
    style: COLUMNS,
    'data-search': `${meeting.id} ${meeting.channel_name} ${meeting.started_by_name || ''} ${meeting.status_words} ${meeting.notes || ''}`.toLowerCase(),
    on: { click: () => openDrawer(`Meeting #${meeting.id}`, meetingDrawer(meeting)) },
  }, [
    el('span', { class: 'dot-sm', 'data-tone': meeting.status === 'recording' ? 'warn' : 'ok' }),
    el('span', { class: 'cell-id', text: `#${meeting.id}` }),
    el('span', { class: 'cell-name', text: meeting.channel_name }),
    el('span', { class: 'cell-quiet', text: when(meeting.started_at) }),
    el('span', { class: 'cell-quiet' }, [nameNode(meeting.started_by, meeting.started_by_name)]),
    el('span', { class: 'cell-kind' }, [
      badge(meeting.status_words, meeting.status === 'recording' ? 'warn' : 'ok'),
    ]),
    el('span', { class: 'cell-kind' }, [
      meeting.posted
        ? badge(meeting.notes_channel_name, 'ok')
        : badge(NOT_POSTED, 'danger'),
    ]),
    icon('chevronRight', 16),
  ]);
}

function headRow() {
  return el('div', { class: 'grid-row head', style: COLUMNS }, [
    el('span'),
    el('span', { text: '#' }),
    el('span', { text: 'Where' }),
    el('span', { text: 'Started' }),
    el('span', { text: 'By' }),
    el('span', { text: 'How it stands' }),
    el('span', { text: 'Posted' }),
    el('span'),
  ]);
}

function meetingsSection() {
  const rows = DATA.meetings.map((meeting) => ({ meeting, node: meetingRow(meeting) }));
  const one = section('Meetings', `${DATA.meetings.length} recorded.`, {
    count: DATA.meetings.length,
    open: true,
  });
  const foot = el('div', { class: 'grid-foot' });
  const grid = el('div', { class: 'grid-table', style: 'min-width: 900px' }, [
    headRow(),
    ...rows.map((entry) => entry.node),
    foot,
  ]);
  const none = sayNothing(NO_MATCH);
  none.hidden = true;

  const paint = () => {
    let shown = 0;
    for (const entry of rows) {
      const hit = state.query === '' || (entry.node.getAttribute('data-search') || '').includes(state.query);
      entry.node.hidden = !hit;
      if (hit) shown += 1;
    }
    none.hidden = shown > 0;
    grid.hidden = shown === 0;
    foot.textContent = shown === rows.length
      ? `Showing ${rows.length} of ${rows.length} meeting${rows.length === 1 ? '' : 's'}`
      : `Showing ${shown} of the ${rows.length} meeting${rows.length === 1 ? '' : 's'} on this page`;
  };
  const search = searchField({
    label: 'Search the meetings',
    placeholder: 'Search the meetings…',
    onQuery: (query) => {
      state.query = query;
      paint();
    },
  });
  paint();

  one.body.append(
    previewWas(WAS_MEETINGS),
    ...(DATA.notes || []).map((line) => el('p', { class: 'field-help', text: line.replace(/[*`]/g, '') })),
    ...hostLines(DATA.host).map((line) => el('p', { class: 'field-help', text: line })),
    DATA.guard && DATA.guard.said
      ? el('p', { class: 'field-help', text: DATA.guard.said.replace(/\*\*/g, '') })
      : null,
    DATA.meetings.length === 0
      ? sayNothing(NO_MEETINGS)
      : card(null, [
        el('div', { class: 'card-head' }, [search]),
        el('div', { class: 'table-scroll' }, [grid]),
        none,
      ]),
  );
  return one.node;
}

function settingControl(spec, say) {
  if (spec.type === 'enum') {
    const select = el('select', { class: 'input' }, (spec.choices || []).map((choice) =>
      el('option', { value: choice, text: choice, selected: String(spec.value) === String(choice) || undefined })));
    select.addEventListener('change', () => wouldDo(say, `PUT /api/settings/${spec.key} — set it to ${select.value}`));
    return select;
  }
  if (spec.type === 'int') {
    const input = el('input', { class: 'input', type: 'number', step: '1', value: String(spec.value) });
    input.addEventListener('change', () => wouldDo(say, `PUT /api/settings/${spec.key} — set it to ${input.value}`));
    return input;
  }
  if (spec.type === 'channel') {
    const select = el('select', { class: 'input' });
    select.append(el('option', { value: '', text: 'not set', selected: spec.value ? undefined : true }));
    for (const channel of DATA.channels) {
      select.append(el('option', {
        value: String(channel.id),
        text: channelLabel(channel, DATA.channels),
        selected: String(channel.id) === String(spec.value) || undefined,
      }));
    }
    select.addEventListener('change', () => wouldDo(say, `PUT /api/settings/${spec.key} — set it to ${select.options[select.selectedIndex].text}`));
    return select;
  }
  if (spec.type === 'role') {
    const select = el('select', { class: 'input' });
    select.append(el('option', { value: '', text: 'not set', selected: spec.value ? undefined : true }));
    for (const role of DATA.roles) {
      select.append(el('option', {
        value: String(role.id),
        text: `@${role.name}`,
        selected: String(role.id) === String(spec.value) || undefined,
      }));
    }
    select.addEventListener('change', () => wouldDo(say, `PUT /api/settings/${spec.key} — set it to ${select.options[select.selectedIndex].text}`));
    return select;
  }
  const input = el('input', {
    class: 'input',
    type: 'text',
    value: spec.value === null || spec.value === undefined ? '' : String(spec.value),
  });
  input.addEventListener('change', () => wouldDo(say, `PUT /api/settings/${spec.key} — set it to what is typed in the box`));
  return input;
}

function machinerySection() {
  const say = notice();
  const one = section('Settings and logs', 'The reference half of the page. Both are shut until '
    + 'you want them.', { id: 'machinery' });
  /* The mode is in the page head, so it keeps one home — `namespaceSettings`'s `omit`. */
  const specs = DATA.settings.filter((spec) => spec.key !== 'minutes_mode');
  one.body.append(
    previewWas(WAS_MACHINERY),
    foldout('Settings', [
      el('p', { class: 'field-help', text: SETTINGS_NOTE }),
      ...specs.map((spec) => field(spec.key, settingControl(spec, say), spec.help)),
      say,
    ], { count: specs.length }),
    foldout('Logs', [
      el('p', { class: 'field-help', text: LOGS_NOTE }),
      DATA.logs.length === 0
        ? sayNothing(NOTHING_LOGGED)
        : table([
          { label: 'When', cell: (row) => ago(row.at).text },
          { label: 'Kind', cell: (row) => row.kind },
          { label: 'Summary', cell: (row) => row.summary, className: 'wrap' },
        ], DATA.logs),
    ], { count: DATA.logs.length }),
  );
  return one.node;
}

/**
 * A meeting is started with `/minutes` in Discord, so this page has no "make
 * one" action. The slot carries the mode instead, the way
 * `page-moderation.js:412` already uses it.
 */
function modeAside() {
  const spec = DATA.settings.find((one) => one.key === 'minutes_mode');
  const say = notice();
  if (!spec) return [el('span')];
  const picker = segment(
    (spec.choices || ['off', 'on']).map((choice) => ({ value: choice, label: choice })),
    spec.value,
    { onChange: () => wouldDo(say, `PUT /api/settings/minutes_mode — set meeting minutes to ${picker.readValue()}`) },
  );
  picker.setAttribute('aria-label', 'Meeting minutes mode');
  return [picker, say];
}

async function load() {
  const aside = document.getElementById('page-aside');
  if (aside) aside.replaceChildren(...modeAside());
  document.getElementById('dash').replaceChildren(
    full(previewBanner({
      today: 4,
      preview: 2,
      note: 'Pressing a meeting opens it in a drawer over the table, so the click has a visible answer.',
    })),
    full(meetingsSection()),
    full(machinerySection()),
  );
}

refresh = start({ tab: 'minutes', load });
