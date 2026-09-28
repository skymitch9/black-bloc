import { clearSetting, saveSetting, send, settings } from './api.js';
import { blockPreview } from './blockpreview.js';
import { bar, button, el, field, notice, readSelect, roleSelect, run } from './ui.js';

// The one editor of a block's words, shared by the Posts page's Blocks section and the Modmail
// page's Front door card. Every field is a settings key the Settings page also reaches.
const WORD_KEYS = {
  title: 'frontdoor_title',
  text: 'frontdoor_text',
  ticket: 'frontdoor_ticket_label',
  request: 'frontdoor_request_label',
  event: 'frontdoor_event_label',
  note: 'rehearsal_note',
};
const SHOW_KEYS = {
  ticket: 'frontdoor_show_ticket',
  request: 'frontdoor_show_request',
  event: 'frontdoor_show_event',
};
const BUTTON_WORDS = {
  ticket: 'Ask staff privately (opens a ticket)',
  request: 'Request something (files a request)',
  event: 'Propose an event (starts a proposal)',
};
const REDRAW = '/api/post-blocks/frontdoor/redraw';
const SAVE_IT = 'Save the words';
const NOTHING_CHANGED = 'Nothing has changed, so nothing was saved.';
const SAVED_FALLBACK = 'Saved.';
const NO_BUTTONS = 'Every button is switched off, so the card goes out with nothing to press. '
  + 'Tick at least one to keep it a door.';
const NOTE_HELP = 'The line a rehearsal copy carries while the door is in shadow. It is shared by '
  + 'every rehearsal copy Black Bloc posts, not only this one; {channel} is the real channel.';
const LABEL_HELP = 'Each button label is at most 80 characters; blank puts the shipped words back.';
const SHOWS_HELP = 'Which buttons the card carries, here and on /ask.';

function specsByKey(payload) {
  const found = {};
  for (const group of Object.values(payload || {})) {
    if (!Array.isArray(group)) continue;
    for (const spec of group) found[spec.key] = spec;
  }
  return found;
}

function textOf(spec) {
  const value = spec ? (spec.value ?? spec.default) : '';
  return value === null || value === undefined ? '' : String(value);
}

function isOn(spec) {
  const value = spec ? (spec.value ?? spec.default) : true;
  return value === null || value === undefined ? true : Boolean(value);
}

/** The front door block's words: heading, line, three labels, which buttons show, the note. */
export async function frontDoorWords({ onSaved = null, say = null } = {}) {
  const specs = specsByKey(await settings(true));
  const was = {};
  const inputs = {};
  for (const [name, key] of Object.entries(WORD_KEYS)) {
    was[key] = textOf(specs[key]);
    inputs[key] = name === 'text'
      ? el('textarea', { class: 'input area', rows: '3', id: `bw-${name}` })
      : el('input', { class: 'input', type: 'text', id: `bw-${name}`, maxlength: name === 'title' ? '256' : '80' });
    inputs[key].value = was[key];
  }
  inputs.frontdoor_text.removeAttribute('maxlength');
  inputs.rehearsal_note.removeAttribute('maxlength');
  const ticks = {};
  for (const [kind, key] of Object.entries(SHOW_KEYS)) {
    was[key] = isOn(specs[key]);
    ticks[key] = el('input', { class: 'input switch', type: 'checkbox', id: `bw-show-${kind}` });
    ticks[key].checked = was[key];
  }

  const voice = say || notice();
  const warn = el('p', { class: 'field-help', 'data-tone': 'warn', text: NO_BUTTONS, hidden: true });
  const shows = () => Object.entries(SHOW_KEYS).filter(([, key]) => ticks[key].checked).map(([kind]) => kind);
  const mock = blockPreview({
    feature: 'frontdoor',
    draft: () => ({
      frontdoor_title: inputs.frontdoor_title.value,
      frontdoor_text: inputs.frontdoor_text.value,
      frontdoor_ticket_label: inputs.frontdoor_ticket_label.value,
      frontdoor_request_label: inputs.frontdoor_request_label.value,
      frontdoor_event_label: inputs.frontdoor_event_label.value,
    }),
    sample: () => ({ shows: shows().join(',') || 'none' }),
  });
  const paint = () => {
    warn.hidden = shows().length > 0;
    mock.repaint();
  };
  for (const node of [...Object.values(inputs), ...Object.values(ticks)]) {
    node.addEventListener(node.type === 'checkbox' ? 'change' : 'input', paint);
  }

  const changed = () => [
    ...Object.values(WORD_KEYS)
      .filter((key) => inputs[key].value !== was[key])
      .map((key) => [key, inputs[key].value]),
    ...Object.values(SHOW_KEYS)
      .filter((key) => ticks[key].checked !== was[key])
      .map((key) => [key, ticks[key].checked]),
  ];

  const save = button(SAVE_IT, async () => {
    const wanted = changed();
    if (!wanted.length) {
      voice.say(NOTHING_CHANGED, 'warn');
      return;
    }
    const done = await run(voice, async () => {
      for (const [key, value] of wanted) {
        await saveSetting(key, value);
        was[key] = value;
      }
      return send(REDRAW, 'POST', {});
    }, (found) => found?.message || SAVED_FALLBACK);
    if (done.ok && onSaved) onSaved(done.found);
  }, { tone: 'warn', small: false });

  paint();
  return el('div', { class: 'blockwords' }, [
    el('div', { class: 'formrow' }, [
      field('Heading', inputs.frontdoor_title),
      field('Line under it', inputs.frontdoor_text),
    ]),
    el('div', { class: 'formrow' }, [
      field('Ticket button', inputs.frontdoor_ticket_label),
      field('Request button', inputs.frontdoor_request_label),
      field('Event button', inputs.frontdoor_event_label),
    ]),
    el('p', { class: 'field-help', text: LABEL_HELP }),
    el('div', { class: 'field' }, [
      el('span', { class: 'field-label', text: 'Buttons it shows' }),
      bar(Object.entries(SHOW_KEYS).map(([kind, key]) => el('label', { class: 'switchline' }, [
        ticks[key],
        el('span', { class: 'field-label', text: BUTTON_WORDS[kind] }),
      ]))),
      el('p', { class: 'field-help', text: SHOWS_HELP }),
      warn,
    ]),
    field('Rehearsal note', inputs.rehearsal_note, NOTE_HELP),
    el('div', { class: 'blockwords-preview' }, [mock.node, mock.say]),
    bar([save]),
    voice,
  ]);
}

const VOICE_WORDS = {
  title: 'tempvoice_block_title',
  text: 'tempvoice_block_text',
  lobby: 'tempvoice_block_lobby_label',
  controls: 'tempvoice_block_controls_label',
};
const VOICE_SHOW = 'tempvoice_block_show_controls';
const VOICE_REDRAW = '/api/post-blocks/tempvoice/redraw';
const LOBBY_HELP = 'One button per join-to-create lobby (at most four); {lobby} is the lobby\'s '
  + 'name, and the button opens that lobby in Discord. At most 80 characters.';
const CONTROLS_HELP = 'Opens the same /voice panel a member gets by typing /voice — every rule '
  + 'it has still applies. Join-to-create and the controls in each room are unchanged.';
const VOICE_PREVIEW_HELP = 'The lobbies are the ones set up on the Temp voice page; with none '
  + 'set up yet, a sample lobby is drawn.';

/** The temp voice lobby block's words: heading, line, the lobby and controls labels. */
export async function voiceLobbyWords({ onSaved = null, say = null } = {}) {
  const specs = specsByKey(await settings(true));
  const was = {};
  const inputs = {};
  for (const [name, key] of Object.entries(VOICE_WORDS)) {
    was[key] = textOf(specs[key]);
    inputs[key] = name === 'text'
      ? el('textarea', { class: 'input area', rows: '3', id: `vw-${name}` })
      : el('input', { class: 'input', type: 'text', id: `vw-${name}`, maxlength: name === 'title' ? '256' : '80' });
    inputs[key].value = was[key];
  }
  inputs[VOICE_WORDS.lobby].removeAttribute('maxlength');
  was[VOICE_SHOW] = isOn(specs[VOICE_SHOW]);
  const tick = el('input', { class: 'input switch', type: 'checkbox', id: 'vw-show-controls' });
  tick.checked = was[VOICE_SHOW];

  const voice = say || notice();
  const mock = blockPreview({
    feature: 'block_tempvoice',
    draft: () => Object.fromEntries(Object.values(VOICE_WORDS).map((key) => [key, inputs[key].value])),
    sample: () => ({ controls: tick.checked ? 'on' : 'off' }),
  });
  for (const node of [...Object.values(inputs), tick]) {
    node.addEventListener(node.type === 'checkbox' ? 'change' : 'input', () => mock.repaint());
  }

  const changed = () => [
    ...Object.values(VOICE_WORDS)
      .filter((key) => inputs[key].value !== was[key])
      .map((key) => [key, inputs[key].value]),
    ...(tick.checked !== was[VOICE_SHOW] ? [[VOICE_SHOW, tick.checked]] : []),
  ];

  const save = button(SAVE_IT, async () => {
    const wanted = changed();
    if (!wanted.length) {
      voice.say(NOTHING_CHANGED, 'warn');
      return;
    }
    const done = await run(voice, async () => {
      for (const [key, value] of wanted) {
        await saveSetting(key, value);
        was[key] = value;
      }
      return send(VOICE_REDRAW, 'POST', {});
    }, (found) => found?.message || SAVED_FALLBACK);
    if (done.ok && onSaved) onSaved(done.found);
  }, { tone: 'warn', small: false });

  return el('div', { class: 'blockwords' }, [
    el('div', { class: 'formrow' }, [
      field('Heading', inputs[VOICE_WORDS.title]),
      field('Line under it', inputs[VOICE_WORDS.text]),
    ]),
    el('div', { class: 'formrow' }, [
      field('Lobby button', inputs[VOICE_WORDS.lobby], LOBBY_HELP),
      field('Voice controls button', inputs[VOICE_WORDS.controls]),
    ]),
    el('div', { class: 'field' }, [
      el('label', { class: 'switchline' }, [
        tick,
        el('span', { class: 'field-label', text: 'Carry the voice controls button' }),
      ]),
      el('p', { class: 'field-help', text: CONTROLS_HELP }),
    ]),
    el('div', { class: 'blockwords-preview' }, [mock.node, mock.say]),
    el('p', { class: 'field-help', text: VOICE_PREVIEW_HELP }),
    bar([save]),
    voice,
  ]);
}

const BUTTON_BLOCKS = {
  marathonrole: {
    feature: 'block_marathonrole',
    words: { title: 'marathon_block_title', text: 'marathon_block_text', label: 'marathon_block_label' },
    labelName: 'Button',
    labelHelp: 'Gives the member who presses it the Marathon role, or takes it back if they have it. '
      + 'It pings nobody. At most 80 characters.',
    role: 'marathon_role_id',
    said: [
      ['marathon_block_added_said', 'When it gives the role', '{role} is the role\'s name.'],
      ['marathon_block_removed_said', 'When it takes the role back', '{role} is the role\'s name.'],
      ['marathon_block_unset_said', 'While no role is picked', 'Also said if the role is gone '
        + 'from the server or carries a staff permission.'],
    ],
  },
  pingsfollow: {
    feature: 'block_pingsfollow',
    words: { title: 'pings_block_title', text: 'pings_block_text', label: 'pings_block_label' },
    labelName: 'Button',
    labelHelp: 'Opens the same /pings panel a member gets by typing /pings, with its Follow a '
      + 'streamer… picker — every rule it has still applies. At most 80 characters.',
    previewHelp: 'Nothing is drawn on a post while pings are off (Settings ▸ pings).',
  },
  birthday: {
    feature: 'block_birthday',
    words: { title: 'birthday_block_title', text: 'birthday_block_text', label: 'birthday_block_label' },
    labelName: 'Button',
    labelHelp: 'Asks for the date straight away, in the same form /birthday’s Set my birthday '
      + 'button opens. The answer is private; the post is never changed. At most 80 characters.',
    said: [
      ['birthday_block_saved_said', 'Once the date is saved', '{said} is the same sentence '
        + '/birthday answers with.'],
      ['birthday_block_refused_said', 'When the date cannot be used', '{said} is the same '
        + 'refusal /birthday answers with. Nothing is saved.'],
      ['birthday_block_off_said', 'While birthdays are off', 'Said on the press, or on the '
        + 'form, if birthdays were turned off after the post was drawn. Nothing is saved.'],
    ],
    previewHelp: 'Nothing is drawn on a post while birthdays are off (Settings ▸ birthday).',
  },
  proposeevent: {
    feature: 'block_proposeevent',
    words: { title: 'events_block_title', text: 'events_block_text', label: 'events_block_label' },
    labelName: 'Button',
    labelHelp: 'Opens the same private card the front door\'s event button opens; its Propose '
      + 'button starts the /event form. At most 80 characters.',
    previewHelp: 'Nothing is drawn on a post while event proposals are off (Settings ▸ events).',
  },
};
const NO_ROLE_YET = 'No Marathon role is picked yet, so a press says staff have not set it up. '
  + 'Pick it here or on the Settings page (marathon_role_id).';
const ROLE_HELP = 'The role the button hands out. A role with a staff permission (kick, ban, '
  + 'manage anything, mention everyone) is never handed out — the press says it is not set up, '
  + 'and the Logs get a marathon.role_failed row.';

/** One editor for every one-button block: heading, line, the button, and a kind's extras. */
function buttonBlockWords(kind) {
  const shape = BUTTON_BLOCKS[kind];
  return async ({ onSaved = null, say = null } = {}) => {
    const specs = specsByKey(await settings(true));
    const was = {};
    const inputs = {};
    for (const [name, key] of Object.entries(shape.words)) {
      was[key] = textOf(specs[key]);
      inputs[key] = name === 'text'
        ? el('textarea', { class: 'input area', rows: '3', id: `${kind}-${name}` })
        : el('input', { class: 'input', type: 'text', id: `${kind}-${name}`, maxlength: name === 'title' ? '256' : '80' });
      inputs[key].value = was[key];
    }
    for (const [key] of shape.said || []) {
      was[key] = textOf(specs[key]);
      inputs[key] = el('textarea', { class: 'input area', rows: '2', id: `${kind}-${key}` });
      inputs[key].value = was[key];
    }
    let role = null;
    if (shape.role) {
      was[shape.role] = specs[shape.role]?.value ? String(specs[shape.role].value) : null;
      role = await roleSelect(was[shape.role], { id: `${kind}-role` });
    }

    const voice = say || notice();
    const warn = el('p', { class: 'field-help', 'data-tone': 'warn', text: NO_ROLE_YET, hidden: true });
    const mock = blockPreview({
      feature: shape.feature,
      draft: () => Object.fromEntries(Object.values(shape.words).map((key) => [key, inputs[key].value])),
    });
    const paint = () => {
      if (role) warn.hidden = Boolean(readSelect(role, false));
      mock.repaint();
    };
    for (const node of [...Object.values(inputs), ...(role ? [role] : [])]) {
      node.addEventListener(node.tagName === 'SELECT' ? 'change' : 'input', paint);
    }

    const changed = () => [
      ...Object.keys(inputs)
        .filter((key) => inputs[key].value !== was[key])
        .map((key) => [key, inputs[key].value]),
      ...(role && readSelect(role, false) !== was[shape.role]
        ? [[shape.role, readSelect(role, false)]]
        : []),
    ];

    const save = button(SAVE_IT, async () => {
      const wanted = changed();
      if (!wanted.length) {
        voice.say(NOTHING_CHANGED, 'warn');
        return;
      }
      const done = await run(voice, async () => {
        for (const [key, value] of wanted) {
          if (value === null) await clearSetting(key);
          else await saveSetting(key, value);
          was[key] = value;
        }
        return send(`/api/post-blocks/${kind}/redraw`, 'POST', {});
      }, (found) => found?.message || SAVED_FALLBACK);
      if (done.ok && onSaved) onSaved(done.found);
    }, { tone: 'warn', small: false });

    paint();
    return el('div', { class: 'blockwords' }, [
      el('div', { class: 'formrow' }, [
        field('Heading', inputs[shape.words.title]),
        field('Line under it', inputs[shape.words.text]),
      ]),
      field(shape.labelName, inputs[shape.words.label], shape.labelHelp),
      ...(role ? [field('The Marathon role', role, ROLE_HELP), warn] : []),
      ...(shape.said || []).map(([key, name, help]) => field(name, inputs[key], help)),
      el('div', { class: 'blockwords-preview' }, [mock.node, mock.say]),
      shape.previewHelp ? el('p', { class: 'field-help', text: shape.previewHelp }) : null,
      bar([save]),
      voice,
    ]);
  };
}

const BLANK_RESTORES = 'Leave a line blank to put the shipped words back.';
const EMPTY_TICK = 'Show it as it looks when the list is empty';

/** A saved word, or the key cleared back to its shipped words when the field is blank. */
async function keep(key, value) {
  if (typeof value === 'string' && !value.trim()) return clearSetting(key);
  return saveSetting(key, value);
}

function numberOf(spec) {
  const value = spec ? (spec.value ?? spec.default) : '';
  return value === null || value === undefined ? '' : String(value);
}

/**
 * A live list block's words: heading, line template, the empty line and its numbers.
 * `spec.words` are [label, key, help]; `spec.numbers` are [label, key, help, low, high];
 * `spec.sample` names the preview sample that draws the list empty.
 */
function liveListWords(spec) {
  return async ({ onSaved = null, say = null } = {}) => {
    const specs = specsByKey(await settings(true));
    const was = {};
    const inputs = {};
    for (const [, key] of spec.words) {
      was[key] = textOf(specs[key]);
      inputs[key] = key.endsWith('_line') || key.endsWith('_empty')
        ? el('textarea', { class: 'input area', rows: '2', id: `lw-${key}` })
        : el('input', { class: 'input', type: 'text', id: `lw-${key}`, maxlength: '256' });
      inputs[key].value = was[key];
    }
    for (const [, key, , low, high] of spec.numbers) {
      was[key] = numberOf(specs[key]);
      inputs[key] = el('input', {
        class: 'input', type: 'number', id: `lw-${key}`, min: String(low), max: String(high),
      });
      inputs[key].value = was[key];
    }
    const empty = el('input', { class: 'input switch', type: 'checkbox', id: `lw-${spec.kind}-empty` });
    const voice = say || notice();
    const mock = blockPreview({
      feature: spec.feature,
      draft: () => Object.fromEntries(spec.words.map(([, key]) => [key, inputs[key].value])),
      sample: () => ({ [spec.sample]: empty.checked ? 'none' : '' }),
    });
    for (const node of [...Object.values(inputs), empty]) {
      node.addEventListener(node.type === 'checkbox' ? 'change' : 'input', () => mock.repaint());
    }
    const changed = () => Object.keys(inputs)
      .filter((key) => inputs[key].value !== was[key])
      .map((key) => [key, inputs[key].type === 'number' ? Number(inputs[key].value) : inputs[key].value]);
    const save = button(SAVE_IT, async () => {
      const wanted = changed();
      if (!wanted.length) {
        voice.say(NOTHING_CHANGED, 'warn');
        return;
      }
      const done = await run(voice, async () => {
        for (const [key, value] of wanted) {
          await keep(key, value);
          was[key] = inputs[key].value;
        }
        return send(`/api/post-blocks/${spec.kind}/redraw`, 'POST', {});
      }, (found) => found?.message || SAVED_FALLBACK);
      if (done.ok && onSaved) onSaved(done.found);
    }, { tone: 'warn', small: false });
    return el('div', { class: 'blockwords' }, [
      el('div', { class: 'formrow' }, spec.words.map(([label, key, help]) => field(label, inputs[key], help))),
      el('div', { class: 'formrow' }, spec.numbers.map(([label, key, help]) => field(label, inputs[key], help))),
      el('p', { class: 'field-help', text: BLANK_RESTORES }),
      el('label', { class: 'switchline' }, [empty, el('span', { class: 'field-label', text: EMPTY_TICK })]),
      el('div', { class: 'blockwords-preview' }, [mock.node, mock.say]),
      el('p', { class: 'field-help', text: spec.previewHelp }),
      bar([save]),
      voice,
    ]);
  };
}

/** The who's-live-now block's words and numbers. */
export const liveNowWords = liveListWords({
  kind: 'livenow',
  feature: 'block_livenow',
  sample: 'live',
  words: [
    ['Heading', 'golive_block_title', null],
    ['Each stream’s line', 'golive_block_line', '{name} is who is live; {title} is the stream’s title, linked to the stream.'],
    ['Link words for a stream with no title', 'golive_block_untitled', null],
    ['While nobody is live', 'golive_block_empty', null],
  ],
  numbers: [
    ['Streams listed at most', 'golive_block_max', '1 to 25.', 1, 25],
    ['Characters of a title shown', 'golive_block_title_chars', '10 to 200; a longer title is cut with an ellipsis.', 10, 200],
  ],
  previewHelp: 'The streams drawn here are samples. On a post, the card lists the go-live and '
    + 'spotlight streams announced right now, and updates itself within a minute or so of one '
    + 'starting or ending.',
});

/** The upcoming-events block's words and number. */
export const upcomingWords = liveListWords({
  kind: 'upcoming',
  feature: 'block_upcoming',
  sample: 'events',
  words: [
    ['Heading', 'events_upcoming_title', null],
    ['Each event’s line', 'events_upcoming_line', '{title} is the event, linked to it in Discord; {when} is its start in each reader’s own time; {relative} is how long until then.'],
    ['While nothing is coming up', 'events_upcoming_empty', null],
  ],
  numbers: [
    ['Events listed at most', 'events_upcoming_max', '1 to 20.', 1, 20],
  ],
  previewHelp: 'The events drawn here are samples. On a post, the card lists the approved events '
    + 'still ahead, soonest first, and drops one once it has started.',
});

const LINK_WORDS = { title: 'posts_block_links_title', text: 'posts_block_links_text' };
const LINK_ROWS = 'posts_block_links_rows';
const LINK_CARD = 'posts_block_links_card';
const LINKS_MAX = 10;
const ADD_LINK = 'Add a link';
const REMOVE_LINK = 'Remove';
const LINKS_FULL = 'That is ten links, the most one block carries (two rows of five).';
const LINKS_HELP = 'Each button opens its address in the browser. The label is at most 80 '
  + 'characters and the address must start with https://. A row that does not check is refused '
  + 'with its number, and nothing is saved.';
const CARD_HELP = 'Off leaves the buttons alone under the post, with no heading or line above them.';

function linkRowsOf(spec) {
  try {
    const found = JSON.parse(textOf(spec) || '[]');
    return Array.isArray(found)
      ? found.map((one) => ({ label: String(one.label || ''), url: String(one.url || '') }))
      : [];
  } catch {
    return [];
  }
}

/** The link buttons block: rows of label and address, added, removed and moved here. */
export async function linkButtonsWords({ onSaved = null, say = null } = {}) {
  const specs = specsByKey(await settings(true));
  const rows = linkRowsOf(specs[LINK_ROWS]);
  const drafted = () => JSON.stringify(rows.map((one) => ({ label: one.label, url: one.url })));
  const was = {
    [LINK_ROWS]: drafted(),
    [LINK_WORDS.title]: textOf(specs[LINK_WORDS.title]),
    [LINK_WORDS.text]: textOf(specs[LINK_WORDS.text]),
    [LINK_CARD]: isOn(specs[LINK_CARD]),
  };
  const title = el('input', { class: 'input', type: 'text', id: 'lb-title', maxlength: '256' });
  title.value = was[LINK_WORDS.title];
  const text = el('textarea', { class: 'input area', rows: '2', id: 'lb-text' });
  text.value = was[LINK_WORDS.text];
  const card = el('input', { class: 'input switch', type: 'checkbox', id: 'lb-card' });
  card.checked = was[LINK_CARD];
  const list = el('div', { class: 'linkrows' });
  const full = el('p', { class: 'field-help', 'data-tone': 'warn', text: LINKS_FULL, hidden: true });
  const voice = say || notice();
  const mock = blockPreview({
    feature: 'block_links',
    draft: () => ({
      [LINK_ROWS]: drafted(),
      [LINK_WORDS.title]: title.value,
      [LINK_WORDS.text]: text.value,
    }),
    sample: () => ({ card: card.checked ? 'on' : 'off' }),
  });
  let paint = () => {};
  const add = button(ADD_LINK, () => {
    rows.push({ label: '', url: 'https://' });
    paint();
  }, { tone: 'quiet' });
  const move = (at, by) => {
    const to = at + by;
    if (to < 0 || to >= rows.length) return;
    [rows[at], rows[to]] = [rows[to], rows[at]];
    paint();
  };
  const rowOf = (one, at) => {
    const label = el('input', { class: 'input', type: 'text', maxlength: '80', placeholder: 'Label', 'aria-label': `Link ${at + 1} label` });
    label.value = one.label;
    label.addEventListener('input', () => { one.label = label.value; mock.repaint(); });
    const url = el('input', { class: 'input', type: 'url', placeholder: 'https://', 'aria-label': `Link ${at + 1} address` });
    url.value = one.url;
    url.addEventListener('input', () => { one.url = url.value; mock.repaint(); });
    return el('div', { class: 'formrow' }, [
      label,
      url,
      bar([
        at > 0 ? button('↑', () => move(at, -1), { tone: 'quiet' }) : null,
        at < rows.length - 1 ? button('↓', () => move(at, 1), { tone: 'quiet' }) : null,
        button(REMOVE_LINK, () => { rows.splice(at, 1); paint(); }, { tone: 'quiet' }),
      ].filter(Boolean)),
    ]);
  };
  paint = () => {
    list.replaceChildren(...rows.map(rowOf));
    add.hidden = rows.length >= LINKS_MAX;
    full.hidden = rows.length < LINKS_MAX;
    mock.repaint();
  };
  for (const node of [title, text, card]) {
    node.addEventListener(node.type === 'checkbox' ? 'change' : 'input', () => mock.repaint());
  }

  const changed = () => [
    ...(drafted() !== was[LINK_ROWS] ? [[LINK_ROWS, rows.length ? drafted() : '']] : []),
    ...(title.value !== was[LINK_WORDS.title] ? [[LINK_WORDS.title, title.value]] : []),
    ...(text.value !== was[LINK_WORDS.text] ? [[LINK_WORDS.text, text.value]] : []),
    ...(card.checked !== was[LINK_CARD] ? [[LINK_CARD, card.checked]] : []),
  ];

  const save = button(SAVE_IT, async () => {
    const wanted = changed();
    if (!wanted.length) {
      voice.say(NOTHING_CHANGED, 'warn');
      return;
    }
    const done = await run(voice, async () => {
      for (const [key, value] of wanted) {
        if (key === LINK_ROWS) await saveSetting(key, value);
        else await keep(key, value);
        was[key] = key === LINK_ROWS ? drafted() : value;
      }
      return send('/api/post-blocks/links/redraw', 'POST', {});
    }, (found) => found?.message || SAVED_FALLBACK);
    if (done.ok && onSaved) onSaved(done.found);
  }, { tone: 'warn', small: false });

  paint();
  return el('div', { class: 'blockwords' }, [
    el('div', { class: 'field' }, [
      el('span', { class: 'field-label', text: 'Buttons' }),
      list,
      bar([add]),
      full,
      el('p', { class: 'field-help', text: LINKS_HELP }),
    ]),
    el('div', { class: 'field' }, [
      el('label', { class: 'switchline' }, [card, el('span', { class: 'field-label', text: 'Put a card above the buttons' })]),
      el('p', { class: 'field-help', text: CARD_HELP }),
    ]),
    el('div', { class: 'formrow' }, [
      field('Heading', title),
      field('Line under it', text),
    ]),
    el('p', { class: 'field-help', text: BLANK_RESTORES }),
    el('div', { class: 'blockwords-preview' }, [mock.node, mock.say]),
    bar([save]),
    voice,
  ]);
}

/** Each block kind's editor, by the kind's key; a new kind adds its editor here. */
export const BLOCK_EDITORS = {
  frontdoor: frontDoorWords,
  tempvoice: voiceLobbyWords,
  marathonrole: buttonBlockWords('marathonrole'),
  pingsfollow: buttonBlockWords('pingsfollow'),
  birthday: buttonBlockWords('birthday'),
  proposeevent: buttonBlockWords('proposeevent'),
  livenow: liveNowWords,
  upcoming: upcomingWords,
  links: linkButtonsWords,
};
