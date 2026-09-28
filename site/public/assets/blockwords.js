import { saveSetting, send, settings } from './api.js';
import { blockPreview } from './blockpreview.js';
import { bar, button, el, field, notice, run } from './ui.js';

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

/** Each block kind's editor, by the kind's key; a new kind adds its editor here. */
export const BLOCK_EDITORS = {
  frontdoor: frontDoorWords,
  tempvoice: voiceLobbyWords,
};
