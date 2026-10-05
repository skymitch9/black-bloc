import { api, send, settings, settingsNamespace } from './api.js';
import { start } from './app.js';
import { logsSection } from './logs.js';
import {
  ago,
  ask,
  askForm,
  badge,
  bar,
  boldParts,
  button,
  card,
  el,
  field,
  foldout,
  keepSaying,
  limitCounter,
  memberPicker,
  notice,
  pager,
  roleSelect,
  run,
  sayAgain,
  sayNothing,
  searchOver,
  section,
  segment,
  settingsPanel,
  slugInput,
  table,
  textAction,
  when,
  wordAids,
} from './ui.js';

const PER_PAGE = 50;
const LINE_LIMIT = 200;
const TITLE_LIMIT = 100;
const BODY_LIMIT = 4000;
const TAG_LIMIT = 40;

const SETTING_KEYS = [
  'chat_mode',
  'chat_cooldown_seconds',
  'chat_ignore_channels',
  'chat_ignore_categories',
  'chat_home_channel_id',
  'chat_visibility_role_id',
  'chat_staff_can_ping_roles',
  'chat_escalation_names',
  'chat_greeting_reaction',
  'chat_greeting_via_model',
  'chat_reply_in_threads',
  'chat_route_ping_staff',
  'chat_llm_mode',
  'chat_monthly_cap_usd',
  'chat_status_admin_only',
  'chat_log_level',
  'emoji_skin_tone',
];

// Phase 17. Their own list because they are edited inside the Memory section, beside the
// profiles they govern, rather than in the Settings block at the foot of the page.
const MEMORY_SETTING_KEYS = [
  'chat_memory_mode',
  'chat_memory_consent',
  'chat_memory_dm_scope',
  'chat_memory_staff_view',
  'chat_memory_retention_days',
  'chat_memory_notes_max',
  'chat_memory_threads_max',
  'chat_memory_model',
];

// Personality tones (docs/info/personality-tones-design.md): the cookout sheet and the tone
// sentence are prompt text, edited in the Personality section; the words /chat says about who
// hears what are edited in the Who hears what section's fold.
const TONE_KEYS = ['chat_cookout_voice', 'chat_tone_clause', 'chat_banter_style', 'chat_grounding_note'];
const VOICE_WORD_KEYS = [
  'chat_voice_pinned',
  'chat_voice_cleared',
  'chat_voice_nothing',
  'chat_voice_no_member',
  'chat_voice_no_tone',
  'chat_voice_tone_off',
  'chat_voice_button',
  'chat_voice_title',
  'chat_voice_intro',
  'chat_voice_empty',
  'chat_voice_off_note',
  'chat_voice_line_pinned',
  'chat_voice_line_rolled',
  'chat_voice_line_waiting',
  'chat_voice_active',
  'chat_voice_set_placeholder',
  'chat_voice_tone_placeholder',
  'chat_voice_clear_button',
  'chat_voice_previous_button',
  'chat_voice_next_button',
  'chat_voice_page',
  'chat_voice_member_title',
  'chat_voice_rerolled',
  'chat_voice_tone_set',
  'chat_voice_is_pinned',
  'chat_voice_no_tones',
  'chat_voice_no_role',
  'chat_voice_role_rolled',
  'chat_voice_role_line',
  'chat_voice_role_pinned_line',
  'chat_voice_role_placeholder',
  'chat_voice_role_title',
  'chat_voice_role_only_button',
  'chat_voice_role_everyone_button',
  'chat_voice_reroll_button',
  'chat_voice_start_placeholder',
  'chat_voice_line_stored',
  'chat_voice_state_rolled',
  'chat_voice_state_set',
  'chat_voice_state_drifted',
  'chat_voice_state_feedback',
  'chat_voice_state_pinned',
  'chat_voice_settled_new',
  'chat_voice_settled_settling',
  'chat_voice_settled_settled',
  'chat_voice_role_confirm',
  'chat_voice_role_confirm_button',
  'chat_voice_role_undo_button',
  'chat_voice_role_undone',
  'chat_voice_role_no_undo',
  'chat_voice_role_everyone',
  'chat_voice_state_tone_off',
  'chat_tone_edited',
  'chat_tone_reset',
  'chat_tone_too_long',
];
const SHEET_TITLE = 'The cookout voice — the base every tone sits on';
const VOICES_EMPTY = 'Nobody has been answered by a conversation model yet, so nobody is listed.';
const VOICES_OFF = 'The voice is the cookout one, so nobody hears a tone right now — pins ' +
  'included. Pick the pool or a mood under Personality and the pins come back into play.';
const VOICES_WAITING = 'pin is off';
const VOICES_WAITING_TITLE = 'The pinned tone is switched off';
const VOICES_TALKING = 'talking now';
const VOICES_PICK_FIRST = 'Pick a member first.';
const VOICES_ADD = 'A member who is not listed yet';
const VOICES_SET = 'Set tone';
const VOICES_PIN = 'Pin';
const VOICES_ROLE = 'Roll for a role…';
const VOICES_ROLE_FIRST = 'Pick a role first.';
const VOICES_ROLE_PINNED = 'pinned — left alone';
const VOICES_ROLE_YES = 'Yes, roll';
const VOICES_ROLE_UNDO = 'Undo this roll';
const VOICE_SETTLE_TITLE = 'How a tone settles and moves';
const VOICE_SETTLE_KEYS = [
  'chat_tone_drift_start_percent',
  'chat_tone_drift_halves_every',
  'chat_tone_drift_floor_percent',
  'chat_tone_feedback_mode',
  'chat_tone_feedback_cues',
  'chat_tone_gentle_order',
  'chat_tone_careful_order',
];
const VOICE_WORDS_TITLE = 'The words /chat says about who hears what';
const NO_TONES = 'Every tone is switched off, so there is nothing to pin. Turn one back on under ' +
  'Personality.';

const CHANNELS_LINK = 'Channel directory → Channels page';


const COSTS_CARD = '/health.html#sect-costs';
const COSTS_TITLE = 'What everything costs, on the Health page';
const NO_KNOWLEDGE = 'Black Bloc has nothing written down about this server yet, so it answers ' +
  'every question from the phrases above and its own wording.';
const NO_TROPES = 'The voice pool is empty, so Black Bloc keeps the cookout voice whatever this ' +
  'is set to.';
const NEED_A_TITLE = 'Give the note a heading first — that is the line a question is matched ' +
  'against.';
const NEED_A_BODY = 'Write the note first, or there is nothing for Black Bloc to quote.';
const NOTE_UNCHANGED = 'Nothing in that note is different, so nothing was saved.';
const TIER_LIVE_WORD = 'answering';
const TIER_QUIET_WORD = 'not answering';

const MODE_COOKOUT = 'cookout';
const MODE_POOL = 'pool';
const MODE_LABELS = { cookout: 'The cookout voice', pool: 'The pool' };

const NO_INTENTS = 'Black Bloc has no intents stored yet. It falls back to the lines in its own ' +
  'code until something is saved here.';
const NO_SETTINGS = 'The bot registers no chat settings, so there is nothing to change here.';
const NEED_TEXT = 'Write something first — that is the message being tested.';
const NEED_NAME = 'Give it a name first, like wheres_the_food.';
const NEED_TRIGGER = 'Add at least one trigger phrase, or nothing would ever match it.';
const NEED_LINE = 'Write the first line, or Black Bloc would have nothing to answer with.';
const BUILTIN_KEPT = 'Built in, so it cannot be deleted — turn it off above and it stays quiet.';

const KIND_SAID = {
  canned: 'Answers with one of the lines below, picked at random.',
  data: 'Fills its line in from what the server is doing right now.',
  route: 'Hands the person to staff rather than answering itself.',
};
const KIND_TONE = { canned: null, data: 'ok', route: 'warn' };

/**
 * What a data or route intent may put in a line beyond the two every intent has.
 * The API sends `tokens` per intent; this is the fallback for an intent that
 * arrives without them, so the help line is never silently empty.
 */
const OWN_TOKENS = {
  who_is_live: ['{names}', '{count}'],
  whats_next: ['{title}', '{when}', '{where}'],
  birthdays: ['{birthdays}', '{count}'],
  head_count: ['{count}'],
  who_has: ['{role}', '{count}', '{holders}', '{more}', '{escalate}', '{trouble}'],
  my_roles: ['{menus}', '{roles}'],
  time_for_me: ['{their_time}', '{zone}'],
  need_a_mod: ['{staff_roles}', '{ticket_how}'],
};

const TOKEN_SAID = {
  '{name}': 'who asked',
  '{attendees}': 'head count',
  '{names}': 'who is live',
  '{count}': 'how many',
  '{title}': 'the next event',
  '{when}': 'when it starts',
  '{where}': 'where it is',
  '{birthdays}': 'whose birthday is coming',
  '{menus}': 'the menus they can pick from',
  '{roles}': 'the roles they already hold',
  '{their_time}': 'the time in their zone',
  '{zone}': 'their zone',
  '{staff_roles}': 'the staff roles',
  '{ticket_how}': 'how to open a ticket',
  '{role}': 'the role that was asked about',
  '{holders}': 'who holds it, by display name',
  '{more}': 'how many were left off the list',
  '{escalate}': 'the extra line when it is a staff role',
  '{trouble}': 'why the role could not be counted',
};

const state = { page: 1 };

let refresh = () => {};

const NAME_ONLY = /[^A-Za-z0-9_]/g;

function nameShape(input) {
  return slugInput(input, { join: '_', only: NAME_ONLY });
}

function tokensOf(intent) {
  const given = Array.isArray(intent.tokens) && intent.tokens.length ? intent.tokens : null;
  return ['{name}', '{attendees}'].concat(given || OWN_TOKENS[intent.name] || []);
}

function specFor(payload, key) {
  for (const rows of Object.values(payload || {})) {
    if (!Array.isArray(rows)) continue;
    const found = rows.find((spec) => spec && spec.key === key);
    if (found) return found;
  }
  return null;
}

/**
 * One line of an intent: the wording, whether it is in the pile, and the two
 * writes that change either. Save stays disabled until the text actually
 * differs, so pressing it always means something.
 */
function lineRow(intent, line, say, swap) {
  const box = el('input', {
    class: 'input',
    type: 'text',
    value: line.text,
    maxlength: String(LINE_LIMIT),
    'aria-label': `What ${intent.name} says`,
  });
  const save = button('Save', async () => {
    const done = await run(
      say,
      () => send(`/api/chat/lines/${encodeURIComponent(line.id)}`, 'PUT', { text: box.value.trim() }),
      (found) => found?.message || 'Saved.',
    );
    if (done.ok) {
      swap({
        ...intent,
        lines: intent.lines.map((one) => (one.id === line.id ? done.found.line : one)),
      });
    }
  }, { disabled: true });
  box.addEventListener('input', () => {
    save.disabled = box.value.trim() === line.text || box.value.trim() === '';
  });

  const flip = button(line.enabled ? 'Turn off' : 'Turn on', async () => {
    const done = await run(
      say,
      () => send(`/api/chat/lines/${encodeURIComponent(line.id)}`, 'PUT', { enabled: !line.enabled }),
      (found) => found?.message || 'Saved.',
    );
    if (done.ok) {
      swap({
        ...intent,
        lines: intent.lines.map((one) => (one.id === line.id ? done.found.line : one)),
      });
    }
  }, { tone: 'quiet' });

  const drop = button('Remove', async () => {
    const sure = await ask({
      title: 'Remove this line?',
      body: [`Black Bloc stops saying it. The other ${intent.lines.length - 1} line(s) stay.`, line.text],
      confirmLabel: 'Remove it',
    });
    if (!sure) return;
    const done = await run(
      say,
      () => api(`/api/chat/lines/${encodeURIComponent(line.id)}`, { method: 'DELETE' }),
      (found) => found?.message || 'Removed.',
    );
    if (done.ok) swap({ ...intent, lines: intent.lines.filter((one) => one.id !== line.id) });
  }, { tone: 'danger' });

  return el('div', { class: 'chatline', 'data-enabled': line.enabled ? 'true' : 'false' }, [
    box,
    line.enabled ? null : el('span', { class: 'chatline-off', text: 'off' }),
    bar([save, flip, drop]),
  ]);
}

function triggerChip(intent, phrase, say, swap) {
  return el('span', { class: 'trigchip' }, [
    el('span', { class: 'trigchip-name', text: phrase, title: phrase }),
    el('button', {
      class: 'trigchip-x',
      type: 'button',
      text: '×',
      'aria-label': `Remove the phrase ${phrase}`,
      on: {
        click: async () => {
          const done = await run(
            say,
            () => send(`/api/chat/intents/${encodeURIComponent(intent.id)}`, 'PUT', {
              triggers: intent.triggers.filter((one) => one !== phrase),
            }),
            () => `Black Bloc no longer answers to “${phrase}”.`,
          );
          if (done.ok) swap(done.found.intent);
        },
      },
    }),
  ]);
}

function triggerBlock(intent, say, swap) {
  const box = el('input', {
    class: 'input',
    type: 'text',
    placeholder: 'a phrase somebody would type',
    'aria-label': `A new trigger phrase for ${intent.name}`,
  });
  const add = async () => {
    const phrase = box.value.trim().toLowerCase();
    if (!phrase) return;
    if (intent.triggers.includes(phrase)) {
      say.say(`“${phrase}” is already one of its phrases, so nothing was changed.`, 'warn');
      return;
    }
    const done = await run(
      say,
      () => send(`/api/chat/intents/${encodeURIComponent(intent.id)}`, 'PUT', {
        triggers: intent.triggers.concat([phrase]),
      }),
      () => `Black Bloc now answers to “${phrase}”.`,
    );
    if (done.ok) swap(done.found.intent);
  };
  box.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter') return;
    event.preventDefault();
    add();
  });

  return el('div', { class: 'chatblock' }, [
    el('h4', { text: 'Trigger phrases' }),
    intent.triggers.length === 0
      ? sayNothing('No phrases, so nothing reaches this intent.')
      : el('div', { class: 'chipbar' }, intent.triggers.map((phrase) =>
        triggerChip(intent, phrase, say, swap))),
    el('div', { class: 'formrow' }, [
      field('Add a phrase', box),
      bar([button('Add', add, { tone: 'quiet' })]),
    ]),
  ]);
}

function lineBlock(intent, say, swap) {
  const box = el('input', {
    class: 'input',
    type: 'text',
    maxlength: String(LINE_LIMIT),
    placeholder: 'another way of saying it',
    'aria-label': `A new line for ${intent.name}`,
  });
  const add = async () => {
    const text = box.value.trim();
    if (!text) {
      say.say(NEED_LINE, 'warn');
      return;
    }
    const done = await run(
      say,
      () => send(`/api/chat/intents/${encodeURIComponent(intent.id)}/lines`, 'POST', { text }),
      (found) => found?.message || 'Added.',
    );
    if (done.ok) swap({ ...intent, lines: intent.lines.concat([done.found.line]) });
  };
  box.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter') return;
    event.preventDefault();
    add();
  });

  return el('div', { class: 'chatblock' }, [
    el('h4', { text: `Lines (${intent.lines.filter((line) => line.enabled).length} of ${intent.lines.length} in the pile)` }),
    intent.lines.length === 0
      ? sayNothing('No lines, so Black Bloc falls back to the wording in its own code.')
      : el('div', { class: 'chatlines' }, intent.lines.map((line) =>
        lineRow(intent, line, say, swap))),
    el('div', { class: 'formrow' }, [
      field('Add a line', box, wordAids(box, null, { tokens: tokensOf(intent), said: TOKEN_SAID })),
      bar([button('Add', add, { tone: 'quiet' })]),
    ]),
  ]);
}

/**
 * A whole intent. Every write answers with the row as the bot now holds it, so
 * the card is rebuilt from the reply rather than from what the page assumed —
 * and `keepSaying` carries the outcome sentence across the rebuild.
 */
function intentCard(intent) {
  const say = sayAgain(`chat:${intent.id}`, notice());
  const node = el('div', { class: 'chat-intent', 'data-intent': String(intent.id) });
  const swap = (next) => {
    keepSaying(`chat:${next.id}`, say);
    node.replaceWith(intentCard(next));
  };

  const nameBox = intent.builtin
    ? el('span', { class: 'chat-fixed', text: intent.name })
    : nameShape(el('input', { class: 'input mono', type: 'text', value: intent.name, 'aria-label': 'Intent name' }));
  const saveName = intent.builtin ? null : button('Rename', async () => {
    const done = await run(
      say,
      () => send(`/api/chat/intents/${encodeURIComponent(intent.id)}`, 'PUT', { name: nameBox.value.trim() }),
      (found) => found?.message || 'Saved.',
    );
    if (done.ok) swap(done.found.intent);
  }, { tone: 'quiet' });

  const enabled = segment(
    [{ value: 'true', label: 'Answering' }, { value: 'false', label: 'Quiet' }],
    intent.enabled ? 'true' : 'false',
    {
      onChange: async () => {
        const wanted = enabled.readValue() === 'true';
        if (wanted === intent.enabled) return;
        const done = await run(
          say,
          () => send(`/api/chat/intents/${encodeURIComponent(intent.id)}`, 'PUT', { enabled: wanted }),
          (found) => found?.message || 'Saved.',
        );
        if (done.ok) swap(done.found.intent);
        else enabled.setValue(intent.enabled ? 'true' : 'false');
      },
    },
  );

  const kind = badge(intent.kind, KIND_TONE[intent.kind] ?? null);
  kind.setAttribute('title', KIND_SAID[intent.kind] || '');

  const drop = intent.builtin ? null : button('Delete', async () => {
    const sure = await ask({
      title: `Delete ${intent.name}?`,
      body: [
        'Black Bloc stops answering to its phrases, and its lines go with it. This cannot be undone.',
      ],
      confirmLabel: 'Delete it',
    });
    if (!sure) return;
    const done = await run(
      say,
      () => api(`/api/chat/intents/${encodeURIComponent(intent.id)}`, { method: 'DELETE' }),
      (found) => found?.message || 'Deleted.',
    );
    if (done.ok) {
      keepSaying('chat-intents', say);
      refresh();
    }
  }, { tone: 'danger' });

  node.append(card(null, [
    el('div', { class: 'formrow' }, [
      field('Name', nameBox),
      field('Kind', kind),
      field('Answers', enabled),
      saveName ? bar([saveName]) : null,
    ]),
    triggerBlock(intent, say, swap),
    lineBlock(intent, say, swap),
    drop ? bar([drop]) : el('p', { class: 'say-nothing', text: BUILTIN_KEPT }),
    say,
  ]));
  return node;
}

function intentsSection(intents, say) {
  const one = section('Intents', null, { count: intents.length, open: true });
  const paged = intents.length > PER_PAGE
    ? intents.slice((state.page - 1) * PER_PAGE, state.page * PER_PAGE)
    : intents;
  one.body.append(
    say,
    paged.length === 0
      ? sayNothing(NO_INTENTS)
      : el('div', { class: 'section-body' }, paged.map(intentCard)),
  );
  if (intents.length > PER_PAGE) {
    one.body.append(pager({
      page: state.page,
      hasMore: state.page * PER_PAGE < intents.length,
      count: paged.length,
      onPage: (to) => {
        state.page = Math.max(1, to);
        return refresh();
      },
    }));
  }
  return one.node;
}

function trySection() {
  const say = notice();
  const box = el('input', {
    class: 'input',
    type: 'text',
    placeholder: 'hey, how many of us are here?',
    'aria-label': 'A message to test',
  });
  const answer = el('div', { class: 'chat-answer', hidden: true });

  const paint = (found) => {
    answer.replaceChildren(
      el('div', { class: 'chipbar' }, [
        el('span', { class: 'chat-answer-label', text: 'It lands on' }),
        badge(found.intent, KIND_TONE[found.kind] ?? null),
        badge(found.kind, 'ok'),
      ]),
      found.line
        ? el('p', { class: 'chat-answer-line', text: found.line })
        : sayNothing('That intent has no line to answer with, so Black Bloc would fall back to ' +
          'the wording in its own code.'),
    );
    answer.hidden = false;
  };

  const go = async () => {
    const text = box.value.trim();
    if (!text) {
      say.say(NEED_TEXT, 'warn');
      answer.hidden = true;
      return;
    }
    const done = await run(
      say,
      () => send('/api/chat/try', 'POST', { text }),
      () => 'That is what it would say. Nothing was sent.',
    );
    if (done.ok) paint(done.found);
    else answer.hidden = true;
  };
  box.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter') return;
    event.preventDefault();
    go();
  });

  const one = section('Try it', null, { open: true });
  one.body.append(card(null, [
    el('div', { class: 'formrow' }, [
      field('Message', box),
      bar([button('Try it', go, { tone: 'warn', small: false })]),
    ]),
    answer,
    say,
  ]));
  return one.node;
}

function newIntentSection(say) {
  const name = nameShape(el('input', { class: 'input mono', type: 'text', placeholder: 'wheres_the_food' }));
  const triggers = el('input', { class: 'input', type: 'text', placeholder: 'wheres the food, when do we eat' });
  const line = el('input', {
    class: 'input',
    type: 'text',
    maxlength: String(LINE_LIMIT),
    placeholder: 'The grill is always on, {name}.',
  });

  const create = button('Add the intent', async () => {
    const wanted = name.value.trim();
    const phrases = triggers.value.split(',').map((one) => one.trim().toLowerCase()).filter(Boolean);
    const text = line.value.trim();
    if (!wanted) {
      say.say(NEED_NAME, 'warn');
      return;
    }
    if (phrases.length === 0) {
      say.say(NEED_TRIGGER, 'warn');
      return;
    }
    if (!text) {
      say.say(NEED_LINE, 'warn');
      return;
    }
    const done = await run(
      say,
      () => send('/api/chat/intents', 'POST', { name: wanted, triggers: phrases, lines: [text] }),
      (found) => found?.message || 'Added.',
    );
    if (done.ok) {
      keepSaying('chat-intents', say);
      refresh();
    }
  }, { tone: 'warn', small: false });

  const one = section('New intent', null, {});
  one.body.append(card(null, [
    el('div', { class: 'formrow' }, [
      field('Name', name),
      field('Trigger phrases, comma-separated', triggers),
      field('First line', line, wordAids(line, null, { tokens: ['{name}', '{attendees}'], said: TOKEN_SAID })),
    ]),
    bar([create]),
    say,
  ]));
  return one.node;
}

/** A sentence the API wrote, with its **bold** kept — the wording has one home. */
function said(text) {
  return el('p', { class: 'say-nothing' }, [
    el('span', { class: 'say-nothing-text' }, boldParts(text || '')),
  ]);
}

function openSettings() {
  const found = document.getElementById('sect-settings');
  if (!found) return;
  const details = found.querySelector('details');
  if (details) details.open = true;
  found.scrollIntoView({ behavior: 'auto', block: 'start' });
}

/**
 * One knowledge note. A `server` row is drawn in full and its own `locked_why`
 * sentence is printed under it — the API owns that wording, so the page never
 * writes a second version of the reason.
 */
function noteCard(row, say) {
  const title = el('input', {
    class: 'input',
    type: 'text',
    value: row.title,
    maxlength: String(TITLE_LIMIT),
    'aria-label': 'The heading Black Bloc matches a question against',
    disabled: !row.editable,
  });
  const body = el('textarea', {
    class: 'input area',
    rows: '4',
    maxlength: String(BODY_LIMIT),
    'aria-label': 'What the note says',
    disabled: !row.editable,
    set: { value: row.body },
  });
  const tag = el('input', {
    class: 'input',
    type: 'text',
    value: row.tag || '',
    maxlength: String(TAG_LIMIT),
    placeholder: 'optional',
    'aria-label': 'A word for what this note is about',
    disabled: !row.editable,
  });

  const save = button('Save', async () => {
    const wanted = {
      title: title.value.trim(),
      body: body.value.trim(),
      tag: tag.value.trim(),
    };
    if (!wanted.title) {
      say.say(NEED_A_TITLE, 'warn');
      return;
    }
    if (!wanted.body) {
      say.say(NEED_A_BODY, 'warn');
      return;
    }
    if (wanted.title === row.title && wanted.body === row.body && wanted.tag === (row.tag || '')) {
      say.say(NOTE_UNCHANGED, 'warn');
      return;
    }
    const done = await run(
      say,
      () => send(`/api/chat/knowledge/${encodeURIComponent(row.id)}`, 'PUT', wanted),
      (found) => found?.message || 'Saved.',
    );
    if (done.ok) {
      keepSaying('chat-knowledge', say);
      refresh();
    }
  }, { tone: 'quiet' });

  const drop = button('Remove', async () => {
    const sure = await ask({
      title: `Remove ${row.title}?`,
      body: [
        'Black Bloc stops quoting it. Its own phrases and its other notes stay exactly as they are.',
        row.body,
      ],
      confirmLabel: 'Remove it',
    });
    if (!sure) return;
    const done = await run(
      say,
      () => api(`/api/chat/knowledge/${encodeURIComponent(row.id)}`, { method: 'DELETE' }),
      (found) => found?.message || 'Removed.',
    );
    if (done.ok) {
      keepSaying('chat-knowledge', say);
      refresh();
    }
  }, { tone: 'danger' });

  const wrote = row.updated_by
    ? `${row.source_word} — ${row.updated_by.name}, ${when(row.updated_at)}`
    : `${row.source_word} — last written ${when(row.updated_at)}`;

  return el('div', { class: 'card knowledge-note', 'data-source': row.source }, [
    el('div', { class: 'card-body' }, [
      el('div', { class: 'formrow' }, [
        field('Heading', title, limitCounter(title, TITLE_LIMIT)),
        field('About', tag, limitCounter(tag, TAG_LIMIT)),
        el('div', { class: 'chipbar' }, [
          badge(row.source === 'server' ? 'Black Bloc wrote this' : 'staff wrote this',
            row.source === 'server' ? 'warn' : null),
          el('span', { class: 'chat-answer-label', text: `${row.characters} characters` }),
        ]),
      ]),
      field('What it says', body, limitCounter(body, BODY_LIMIT)),
      el('p', { class: 'section-note', text: wrote }),
      row.editable ? bar([save, drop]) : said(row.locked_why),
    ]),
  ]);
}

function newNoteCard(say) {
  const title = el('input', {
    class: 'input',
    type: 'text',
    maxlength: String(TITLE_LIMIT),
    placeholder: 'Cookout hours',
  });
  const body = el('textarea', {
    class: 'input area',
    rows: '3',
    maxlength: String(BODY_LIMIT),
    placeholder: 'The grill goes on at six on a Saturday.',
  });
  const tag = el('input', {
    class: 'input',
    type: 'text',
    maxlength: String(TAG_LIMIT),
    placeholder: 'cookout',
  });

  const add = button('Write it down', async () => {
    const wanted = title.value.trim();
    const words = body.value.trim();
    if (!wanted) {
      say.say(NEED_A_TITLE, 'warn');
      return;
    }
    if (!words) {
      say.say(NEED_A_BODY, 'warn');
      return;
    }
    const done = await run(
      say,
      () => send('/api/chat/knowledge', 'POST', { title: wanted, body: words, tag: tag.value.trim() }),
      (found) => found?.message || 'Added.',
    );
    if (done.ok) {
      keepSaying('chat-knowledge', say);
      refresh();
    }
  }, { tone: 'warn', small: false });

  return card('A new note', [
    el('div', { class: 'formrow' }, [
      field('Heading', title, limitCounter(title, TITLE_LIMIT)),
      field('About (optional)', tag, limitCounter(tag, TAG_LIMIT)),
    ]),
    field('What it says', body, limitCounter(body, BODY_LIMIT)),
    bar([add]),
  ], { count: null });
}

function knowledgeSection(payload, say) {
  const rows = Array.isArray(payload?.sections) ? payload.sections : [];
  const counts = payload?.counts || {};
  const one = section('Knowledge', null, { count: rows.length || null });
  const list = el('div', { class: 'section-body' });
  const focusNew = () => {
    const box = one.body.querySelector('.card input.input:not([disabled])');
    if (box) box.focus();
  };

  one.body.append(say);
  if (rows.length === 0) {
    one.body.append(sayNothing(NO_KNOWLEDGE, textAction('Write the first note', focusNew)));
  } else {
    for (const row of rows) list.append(noteCard(row, say));
    one.body.append(
      searchOver(list, {
        label: 'Search the notes',
        placeholder: 'a heading or a word inside one',
        selector: '.knowledge-note',
        noun: 'note(s)',
        empty: 'No note has those words in it.',
      }),
      list,
      el('p', {
        class: 'section-note',
        text: `${counts.staff || 0} written by staff, ${counts.server || 0} written by Black Bloc. ` +
          (payload?.budget?.word || ''),
      }),
    );
  }
  one.body.append(el('div', { class: 'chatblock' }, [newNoteCard(say)]));
  return one.node;
}

/**
 * One voice in the pool: its wording, whether Black Bloc may pick it, and the
 * one button that points the whole bot at it.
 */
function toneEditor(row, say) {
  const area = el('textarea', {
    class: 'input area tone-area',
    rows: '5',
    maxlength: '1200',
    'aria-label': `How ${row.label} sounds`,
  });
  area.value = row.voice || '';
  const path = `/api/chat/personality/${encodeURIComponent(row.name)}`;
  const saveTone = async (voice) => {
    const done = await run(
      say,
      () => send(path, 'PUT', { voice }),
      (found) => found?.message || 'Saved.',
    );
    if (done.ok) {
      keepSaying('chat-personality', say);
      refresh();
    }
  };
  const save = button('Save the wording', () => saveTone(area.value.trim()), { tone: 'quiet' });
  const back = row.edited ? button('Put the shipped wording back', () => saveTone(''), { tone: 'quiet' }) : null;
  return el('div', {}, [
    area,
    bar([save, back, limitCounter(area, 1200)]),
  ]);
}

function tropeCard(row, mode, say) {
  const flip = button(row.enabled ? 'Take it out' : 'Put it back', async () => {
    const done = await run(
      say,
      () => send(`/api/chat/personality/${encodeURIComponent(row.name)}`, 'PUT', { enabled: !row.enabled }),
      (found) => found?.message || 'Saved.',
    );
    if (done.ok) {
      keepSaying('chat-personality', say);
      refresh();
    }
  }, { tone: 'quiet' });

  const pick = row.in_use || !row.enabled ? null : button('Be only this one', async () => {
    const done = await run(
      say,
      () => send('/api/chat/personality', 'PUT', { mode: row.name }),
      (found) => found?.message || 'Saved.',
    );
    if (done.ok) {
      keepSaying('chat-personality', say);
      refresh();
    }
  }, { tone: 'quiet' });

  return el('div', { class: 'card trope', 'data-enabled': row.enabled ? 'true' : 'false' }, [
    el('div', { class: 'card-body' }, [
      el('div', { class: 'chipbar' }, [
        el('span', { class: 'chat-fixed', text: row.label }),
        row.in_use ? badge('the one in use', 'ok') : null,
        row.enabled ? null : badge('out of the pool', 'warn'),
        row.edited ? badge('your wording', 'info') : null,
      ]),
      toneEditor(row, say),
      el('p', {
        class: 'section-note',
        text: row.updated_by
          ? `Last changed by ${row.updated_by.name}, ${when(row.updated_at)}.`
          : 'Never changed here — this is how it was ported.',
      }),
      bar([flip, pick]),
    ]),
  ]);
}

async function personalitySection(payload, say, sheetSpecs) {
  const rows = Array.isArray(payload?.tropes) ? payload.tropes : [];
  const mode = String(payload?.mode || MODE_COOKOUT);
  const kind = String(payload?.mode_kind || MODE_COOKOUT);
  const one = section('Personality', null, { count: payload?.counts?.enabled ?? null });

  const named = rows.find((row) => row.name === mode);
  const choices = [
    { value: MODE_COOKOUT, label: MODE_LABELS.cookout },
    { value: MODE_POOL, label: MODE_LABELS.pool },
  ];
  // The third choice exists only while one voice is pinned, so the segment can
  // always show what is true and picking either of the other two is the way off it.
  if (kind === 'trope') choices.push({ value: mode, label: `Only ${named ? named.label : mode}` });

  const pick = segment(choices, mode, {
    onChange: async () => {
      const wanted = pick.readValue();
      if (wanted === mode) return;
      const done = await run(
        say,
        () => send('/api/chat/personality', 'PUT', { mode: wanted }),
        (found) => found?.message || 'Saved.',
      );
      if (done.ok) {
        keepSaying('chat-personality', say);
        refresh();
      } else pick.setValue(mode);
    },
  });

  const list = el('div', { class: 'section-body' });
  for (const row of rows) list.append(tropeCard(row, mode, say));

  const sheet = card(SHEET_TITLE, [
    await settingsPanel(
      sheetSpecs.map((spec) => ({ ...spec, type: 'longtext' })),
      { where: 'Personality', empty: NO_SETTINGS },
    ),
  ]);
  sheet.classList.add('cookout-sheet');

  one.body.append(
    sheet,
    card(null, [
      el('div', { class: 'formrow' }, [
        field('The voice', pick),
      ]),
      el('p', { class: 'chat-answer-line' }, boldParts(payload?.mode_word || '')),
      say,
    ]),
    rows.length === 0
      ? sayNothing(NO_TROPES)
      : el('div', {}, [
        searchOver(list, {
          label: 'Search the voices',
          placeholder: 'a name or a word from one',
          selector: '.trope',
          noun: 'voice(s)',
          empty: 'No voice has those words in it.',
        }),
        list,
      ]),
    el('p', {
      class: 'section-note',
      text: payload?.ported_from ? `Ported from ${payload.ported_from}.` : '',
    }),
  );
  return one.node;
}

function toneSelect(tropes, current) {
  const select = el('select', { class: 'input', 'aria-label': 'Tone' });
  for (const one of tropes) {
    const option = el('option', { value: one.name, text: one.label });
    if (one.name === current) option.selected = true;
    select.append(option);
  }
  return select;
}

const voicePath = (id, tail = '') => `/api/chat/voices/${encodeURIComponent(id)}${tail}`;

async function voiceMove(say, work, fallback) {
  const done = await run(say, work, (found) => found?.message || fallback);
  if (done.ok) {
    keepSaying('chat-voices', say);
    refresh();
  }
  return done;
}

const rerollFor = (say, id) => voiceMove(say, () => send(voicePath(id, '/reroll'), 'POST', {}), 'Rolled.');

/** One dialog for the two moves that need a tone: a starting tone, or a pin. */
async function pickTone(say, id, name, tropes, current, { title, confirmLabel, path, fallback }) {
  const select = toneSelect(tropes, current);
  let said = null;
  const sent = await askForm({
    title: `${title} — ${name}`,
    body: [field('Tone', select)],
    confirmLabel,
    tone: null,
    onConfirm: async () => {
      const found = await send(voicePath(id, path), 'PUT', { trope: select.value });
      said = found?.message || fallback;
      return null;
    },
  });
  if (!sent) return;
  say.say(said, 'ok');
  keepSaying('chat-voices', say);
  refresh();
}

const setToneFor = (say, id, name, tropes, current) => pickTone(say, id, name, tropes, current, {
  title: VOICES_SET, confirmLabel: 'Set tone', path: '/tone', fallback: 'Set.',
});
const pinFor = (say, id, name, tropes, current) => pickTone(say, id, name, tropes, current, {
  title: VOICES_PIN, confirmLabel: 'Pin', path: '', fallback: 'Pinned.',
});

function voiceHow(row) {
  if (!row.state_word) return el('span', { text: '—' });
  const parts = [el('span', { text: row.state_word })];
  if (row.state === 'pinned' && row.pinned_by) parts.push(el('span', { class: 'muted', text: ` · ${row.pinned_by.name}` }));
  if (row.state === 'set' && row.set_by) parts.push(el('span', { class: 'muted', text: ` · ${row.set_by.name}` }));
  const stamp = row.state === 'pinned' ? row.pinned_at : row.moved_at;
  if (stamp) {
    const gone = ago(stamp);
    parts.push(el('span', { class: 'muted', title: gone.title, text: ` · ${gone.text}` }));
  }
  return el('span', { class: 'voice-how' }, parts);
}

function voiceSettled(row) {
  if (!row.settled_word || row.state === 'pinned') return el('span', { text: '—' });
  const share = Math.max(0, Math.min(1, Number(row.settled_share) || 0));
  return el('span', { class: 'tone-settled' }, [
    el('span', { class: 'tone-meter', role: 'img', 'aria-label': row.settled_word }, [
      el('span', { class: 'tone-meter-fill', style: `width: ${(share * 100).toFixed(0)}%` }),
    ]),
    el('span', { text: row.settled_word }),
  ]);
}

function voiceMoves(row, tropes, say) {
  if (row.pinned) {
    return el('div', { class: 'voice-moves' }, [
      button('Unpin', () => voiceMove(say, () => api(voicePath(row.user_id), { method: 'DELETE' }), 'Unpinned.'), { tone: 'quiet' }),
    ]);
  }
  if (tropes.length === 0) return null;
  const current = row.tone || row.trope;
  return el('div', { class: 'voice-moves' }, [
    button('Reroll', () => rerollFor(say, row.user_id), { tone: 'quiet' }),
    button('Set tone…', () => setToneFor(say, row.user_id, row.name, tropes, current), { tone: 'quiet' }),
    button('Pin…', () => pinFor(say, row.user_id, row.name, tropes, current), { tone: 'quiet' }),
  ]);
}

function voiceNew(tropes, say) {
  if (tropes.length === 0) return card(null, [sayNothing(NO_TONES)]);
  const picker = memberPicker({ label: VOICES_ADD });
  const picked = (then) => () => {
    if (!picker.id) {
      say.say(VOICES_PICK_FIRST, 'warn');
      return;
    }
    then(picker.id, picker.name || 'this member');
  };
  return card(null, [
    picker.node,
    el('div', { class: 'voice-moves' }, [
      button('Reroll', picked((id) => rerollFor(say, id)), { tone: 'quiet' }),
      button('Set tone…', picked((id, name) => setToneFor(say, id, name, tropes, tropes[0].name)), { tone: 'quiet' }),
      button('Pin…', picked((id, name) => pinFor(say, id, name, tropes, tropes[0].name)), { tone: 'quiet' }),
    ]),
  ]);
}

let lastRoll = null;

async function rollForRole(say) {
  const role = await roleSelect(null, { id: 'voices-role' });
  const who = segment([
    { value: 'only', label: 'Only members with no tone' },
    { value: 'everyone', label: 'Everyone in it' },
  ], 'only');
  let wanted = null;
  let question = null;
  const picked = await askForm({
    title: VOICES_ROLE,
    body: [field('Role', role), who],
    confirmLabel: 'Roll',
    tone: null,
    onConfirm: async () => {
      if (!role.value) return VOICES_ROLE_FIRST;
      wanted = { role_id: role.value, everyone: who.readValue() === 'everyone' };
      question = await send('/api/chat/voices/roll/preview', 'POST', wanted);
      return null;
    },
  });
  if (!picked || !question) return;
  const sure = await ask({
    title: `@${question.role}`,
    body: [el('p', { class: 'ask-body' }, boldParts(question.message || ''))],
    confirmLabel: VOICES_ROLE_YES,
  });
  if (!sure) return;
  const done = await run(say, () => send('/api/chat/voices/roll', 'POST', wanted), (found) => found?.message || 'Rolled.');
  if (!done.ok) return;
  lastRoll = done.found || null;
  keepSaying('chat-voices', say);
  refresh();
}

async function undoRoll(say) {
  const roll = lastRoll;
  const done = await run(
    say,
    () => send('/api/chat/voices/roll/undo', 'POST', { roll_id: roll.roll_id }),
    (found) => found?.message || 'Undone.',
  );
  lastRoll = null;
  if (done.ok) keepSaying('chat-voices', say);
  refresh();
}

function rollResult(say) {
  if (!lastRoll) return null;
  const rolled = Array.isArray(lastRoll.rolled) ? lastRoll.rolled : [];
  const pinned = Array.isArray(lastRoll.pinned) ? lastRoll.pinned : [];
  const line = (one, mark) => el('div', { class: 'chatline' }, [
    el('span', { text: one.name }),
    el('span', { class: 'chat-fixed', text: one.label || one.trope }),
    mark ? badge(mark, 'warn') : null,
  ]);
  return card(`@${lastRoll.role}`, [
    ...rolled.map((one) => line(one, null)),
    ...pinned.map((one) => line(one, VOICES_ROLE_PINNED)),
  ], {
    count: rolled.length,
    actions: el('div', { class: 'voice-moves' }, [
      lastRoll.roll_id && rolled.length ? button(VOICES_ROLE_UNDO, () => undoRoll(say), { tone: 'quiet' }) : null,
      button('Clear', () => {
        lastRoll = null;
        refresh();
      }, { tone: 'quiet' }),
    ]),
  });
}

async function voicesSection(payload, wordSpecs, say, settleSpecs = []) {
  const rows = Array.isArray(payload?.voices) ? payload.voices : [];
  const tropes = Array.isArray(payload?.tropes) ? payload.tropes : [];
  const one = section('Who hears what', null, { count: rows.length || null });
  const counts = payload?.counts || {};
  one.body.append(card(null, [
    el('div', { class: 'chipbar' }, [
      badge(`the setting is ${payload?.setting || MODE_COOKOUT}`, payload?.setting_kind === MODE_COOKOUT ? null : 'ok'),
      badge(`${counts.pinned ?? 0} pinned`, null),
      badge(`${counts.active ?? 0} talking now`, counts.active ? 'ok' : null),
      tropes.length ? button(VOICES_ROLE, () => rollForRole(say), { tone: 'quiet' }) : null,
    ]),
    payload?.setting_kind === MODE_COOKOUT ? el('p', { class: 'section-note', text: VOICES_OFF }) : null,
    say,
  ]));
  const result = rollResult(say);
  if (result) one.body.append(result);
  one.body.append(table([
    {
      label: 'Member',
      cell: (row) => el('span', {}, [
        el('span', { text: row.name }),
        row.active ? badge(VOICES_TALKING, 'ok') : null,
      ]),
    },
    {
      label: 'Hears',
      cell: (row) => el('span', {}, [
        el('span', { class: 'chat-fixed', text: row.label || row.trope }),
        row.waiting ? el('span', { title: VOICES_WAITING_TITLE }, [badge(VOICES_WAITING, 'warn')]) : null,
      ]),
    },
    { label: 'How', cell: (row) => voiceHow(row) },
    { label: 'Settled', cell: (row) => voiceSettled(row) },
    { label: 'Moves', cell: (row) => voiceMoves(row, tropes, say) },
  ], rows, { empty: VOICES_EMPTY, searchLabel: 'Search the members' }));
  one.body.append(
    voiceNew(tropes, say),
    foldout(VOICE_SETTLE_TITLE, [
      await settingsPanel(settleSpecs, { where: 'Who hears what', empty: NO_SETTINGS }),
    ], { count: settleSpecs.length || null }),
    foldout(VOICE_WORDS_TITLE, [
      await settingsPanel(wordSpecs, { where: 'Who hears what', empty: NO_SETTINGS }),
    ], { count: wordSpecs.length || null }),
  );
  return one.node;
}

function tierRow(row) {
  return el('div', { class: 'chatline', 'data-enabled': row.live ? 'true' : 'false' }, [
    el('span', { class: 'chat-fixed', text: row.label }),
    badge(row.live ? TIER_LIVE_WORD : TIER_QUIET_WORD, row.live ? 'ok' : 'warn'),
    el('span', { class: 'tier-word' }, boldParts(row.word)),
  ]);
}

function spendSection(payload) {
  const month = payload?.month || {};
  const today = payload?.today || {};
  const tiers = Array.isArray(payload?.tiers) ? payload.tiers : [];
  const live = tiers.filter((row) => row.live).length;
  const one = section('Spend & tiers', null, { count: live || null });
  const share = Math.max(0, Math.min(1, Number(month.share) || 0));

  one.body.append(card(null, [
    el('div', { class: 'chipbar' }, [
      el('a', {
        class: 'spend-figure',
        href: COSTS_CARD,
        title: COSTS_TITLE,
        text: `$${Number(month.spent_usd || 0).toFixed(2)}`,
      }),
      el('span', { class: 'chat-answer-label', text: `of $${Number(month.cap_usd || 0).toFixed(2)} this month` }),
      payload?.capped ? badge('the month is spent', 'warn') : null,
    ]),
    el('div', {
      class: 'spend-meter',
      'data-capped': payload?.capped ? 'true' : 'false',
      role: 'img',
      'aria-label': month.word || '',
    }, [
      el('div', { class: 'spend-meter-fill', style: `width: ${(share * 100).toFixed(1)}%` }),
    ]),
    el('p', { class: 'section-note', text: month.word || '' }),
    el('p', { class: 'section-note', text: today.word || '' }),
    bar([textAction(`Change ${payload?.cap_key || 'the cap'}`, openSettings)]),
  ]));
  one.body.append(el('div', { class: 'chatblock' }, [
    el('h4', { text: `Tiers (${live} of ${tiers.length} answering)` }),
    tiers.length === 0
      ? sayNothing('Black Bloc could not say which tiers are answering, so nothing is claimed here.')
      : el('div', { class: 'chatlines' }, tiers.map(tierRow)),
    payload?.last_turn_at
      ? el('p', { class: 'section-note', text: `The last answer a model gave was ${when(payload.last_turn_at)}.` })
      : el('p', { class: 'section-note', text: 'No model has answered anything yet.' }),
  ]));
  return one.node;
}

function channelsSection() {
  const one = section('Channel directory');
  one.body.append(el('p', { class: 'section-note' }, [
    el('a', { href: '/channels.html', text: CHANNELS_LINK }),
  ]));
  return one.node;
}

async function settingsSection(specs) {
  const one = section('Settings', null, { count: specs.length || null });
  one.body.append(await settingsPanel(specs, { where: 'Settings', empty: NO_SETTINGS }));
  return one.node;
}

const MEMORY_COUNTS_ONLY = 'This server keeps the notes themselves private to the person they ' +
  'are about, so only the counts are shown here. Set chat_memory_staff_view to full below if ' +
  'staff should read them.';
const MEMORY_NO_PROFILES = 'Nobody has a profile yet.';
const MEMORY_FORGOT_FAILED = 'That profile was not cleared.';
const MEMORY_DM_MARK = 'learned in a DM';

/** Counts always; the notes themselves only where the server has said staff may read them. */
function memoryLine(one) {
  return el('li', { class: 'chatline' }, [
    el('span', { class: 'chatline-text', text: one.text }),
    one.where === 'dm' ? badge(MEMORY_DM_MARK, 'warn') : null,
  ]);
}

function memoryCard(row, say) {
  const forget = button('Forget', async () => {
    const sure = await ask({
      title: `Clear what Black Bloc remembers about ${row.member.name}?`,
      body: [
        'Every preference and open topic goes at once. It can learn them again from the next ' +
        'conversation unless they have turned memory off for themselves.',
      ],
      confirmLabel: 'Clear it',
    });
    if (!sure) return;
    const done = await run(
      say,
      () => send(`/api/chat/memory/${encodeURIComponent(row.member.id)}`, 'DELETE'),
      (found) => found?.message || MEMORY_FORGOT_FAILED,
    );
    if (!done.ok) return;
    keepSaying('chat-memory', say);
    refresh();
  }, { tone: 'danger' });

  const counts = `${row.notes} preference${row.notes === 1 ? '' : 's'} · ` +
    `${row.threads} open topic${row.threads === 1 ? '' : 's'} · ${row.turns_seen} turn` +
    `${row.turns_seen === 1 ? '' : 's'} seen`;

  return card(null, [
    el('div', { class: 'req-head' }, [
      el('div', { class: 'req-headtext' }, [
        el('p', { class: 'req-what', text: row.member.name }),
        el('p', {
          class: 'section-note',
          text: `${counts}${row.updated_at ? ` · last changed ${when(row.updated_at)}` : ''}`,
        }),
      ]),
      el('div', { class: 'req-marks' }, [row.call_me ? badge(`goes by ${row.call_me}`, 'info') : null]),
    ]),
    row.lines && row.lines.length
      ? el('ul', { class: 'chatlines' }, row.lines.map(memoryLine))
      : null,
    bar([forget]),
  ]);
}

async function memorySection(payload, specs, say) {
  const rows = Array.isArray(payload?.profiles) ? payload.profiles : [];
  const one = section('Memory', null, { count: rows.length || null });
  one.body.append(card(null, [
    el('div', { class: 'chipbar' }, [
      badge(payload?.on ? 'on' : 'off', payload?.on ? 'ok' : null),
      badge(`${payload?.total ?? rows.length} profile(s)`, null),
      badge(`${payload?.opted_out ?? 0} opted out`, null),
      badge(`${payload?.dm_notes ?? 0} learned in a DM`, null),
    ]),
    payload?.message ? el('p', { class: 'section-note', text: payload.message }) : null,
    payload?.staff_view === 'counts'
      ? el('p', { class: 'section-note', text: MEMORY_COUNTS_ONLY })
      : null,
  ]));
  one.body.append(
    rows.length === 0
      ? sayNothing(MEMORY_NO_PROFILES)
      : el('div', { class: 'chatblock' }, rows.map((row) => memoryCard(row, say))),
    await settingsPanel(specs, { where: 'Memory', empty: NO_SETTINGS }),
    say,
  );
  return one.node;
}

// The review queue (docs/info/chat-review-loop-design.md): answers that may have missed, what the
// cheap model suggests Black Bloc learns from each, and the moves staff make on them. Every move
// goes through chat_panel.py's one write path, the same one /chat ▸ Review queue… uses.
const REVIEW_EMPTY = 'Nothing is waiting in this view.';
const REVIEW_DOWNLOAD = 'Download as markdown';
const REVIEW_WORDS_TITLE = 'The words the review queue says';
const REVIEW_SETTINGS_TITLE = 'How the review queue decides';
const REVIEW_STATUS_WORDS = { open: 'Waiting', approved: 'Approved', changed: 'Changed', dismissed: 'Dismissed', all: 'Everything' };
const REVIEW_KIND_WORDS = { phrase: 'A phrase for an intent', intent: 'A new intent', knowledge: 'A knowledge fact' };
const REVIEW_NEED_PHRASE = 'Write the phrase first — the words somebody would say.';
const REVIEW_NEED_LINE = 'Write the fact first, in one plain line.';
const REVIEW_NEED_NAME = 'Give the new intent a name first, like wheres_the_food.';
const REVIEW_DISMISS_ASK = 'Black Bloc learns nothing from it. Reopen puts it back in the queue.';
const REVIEW_SETTING_KEYS = [
  'chat_review_mode',
  'chat_review_reask_seconds',
  'chat_review_downvote_emoji',
  'chat_review_not_it_phrases',
  'chat_review_ack_phrases',
  'chat_review_digest_hour',
];
const REVIEW_WORD_PREFIX = 'chat_review_';
const reviewView = { status: 'open', reason: '' };

function reviewPicker(label, choices, current) {
  const select = el('select', { class: 'input', 'aria-label': label });
  for (const [value, text] of choices) {
    const option = el('option', { value, text });
    if (value === current) option.selected = true;
    select.append(option);
  }
  return select;
}

async function reviewMove(say, work, okText) {
  const done = await run(say, work, (found) => found?.message || okText);
  if (done.ok) {
    keepSaying('chat-review', say);
    refresh();
  }
}

function reviewChange(row, intents, say) {
  const kind = segment(
    Object.entries(REVIEW_KIND_WORDS).map(([value, label]) => ({ value, label })),
    row.suggestion?.kind in REVIEW_KIND_WORDS ? row.suggestion.kind : 'phrase',
    { onChange: () => shape() },
  );
  const intent = reviewPicker('The intent it should reach', intents.map((name) => [name, name]),
    row.suggestion?.intent || intents[0]);
  const name = slugInput(el('input', { class: 'input', type: 'text', maxlength: '60', placeholder: 'wheres_the_food',
    value: row.suggestion?.kind === 'intent' ? row.suggestion.intent || '' : '' }), { lower: true, join: '_', only: NAME_ONLY });
  const phrase = el('input', { class: 'input', type: 'text', maxlength: '60',
    value: row.suggestion?.phrase || '', placeholder: 'when does the grill go on' });
  const line = el('input', { class: 'input', type: 'text', maxlength: '300',
    value: row.suggestion?.line || '', placeholder: 'The grill goes on at six on a Saturday.' });
  const note = el('input', { class: 'input', type: 'text', maxlength: '100',
    value: row.suggestion?.section || '', placeholder: 'From review' });
  const intentField = field('The intent it should reach', intent);
  const nameField = field('The new intent’s name', name, limitCounter(name, 60));
  const phraseField = field('The phrase', phrase, limitCounter(phrase, 60));
  const lineField = field('The fact', line, limitCounter(line, 300));
  const noteField = field('The note it goes in', note, limitCounter(note, 100));
  const shape = () => {
    const now = kind.readValue();
    intentField.hidden = now !== 'phrase';
    nameField.hidden = now !== 'intent';
    phraseField.hidden = now === 'knowledge';
    lineField.hidden = now !== 'knowledge';
    noteField.hidden = now !== 'knowledge';
  };
  shape();
  const save = button('Write this instead', () => {
    const now = kind.readValue();
    const wanted = { kind: now };
    if (now === 'knowledge') {
      if (!line.value.trim()) return say.say(REVIEW_NEED_LINE, 'warn');
      Object.assign(wanted, { line: line.value.trim(), section: note.value.trim() });
    } else {
      if (!phrase.value.trim()) return say.say(REVIEW_NEED_PHRASE, 'warn');
      if (now === 'intent' && !name.value.trim()) return say.say(REVIEW_NEED_NAME, 'warn');
      Object.assign(wanted, { phrase: phrase.value.trim(), intent: now === 'intent' ? name.value.trim() : intent.value });
    }
    return reviewMove(say, () => send(`/api/chat/review/${encodeURIComponent(row.id)}`, 'PUT', wanted), 'Changed.');
  }, { tone: 'warn' });
  return foldout('Change…', [kind, intentField, nameField, phraseField, lineField, noteField, bar([save])]);
}

function reviewMoves(row, intents, say) {
  if (row.status === 'dismissed') {
    return bar([button('Reopen', () => reviewMove(say,
      () => send(`/api/chat/review/${encodeURIComponent(row.id)}/reopen`, 'POST'), 'Reopened.'), { tone: 'quiet' })]);
  }
  if (row.status !== 'open') {
    const by = row.decided_by ? ` by ${row.decided_by.name}` : '';
    return el('p', { class: 'section-note', text: `${REVIEW_STATUS_WORDS[row.status] || row.status}${by}, ${when(row.decided_at)}` });
  }
  const approve = row.suggestion?.teaches ? button('Approve', () => reviewMove(say,
    () => send(`/api/chat/review/${encodeURIComponent(row.id)}/approve`, 'POST'), 'Approved.'), { tone: 'warn' }) : null;
  const dismiss = button('Dismiss', async () => {
    const sure = await ask({ title: `Dismiss item ${row.id}?`, body: [REVIEW_DISMISS_ASK], confirmLabel: 'Dismiss it' });
    if (!sure) return;
    await reviewMove(say, () => send(`/api/chat/review/${encodeURIComponent(row.id)}/dismiss`, 'POST'), 'Dismissed.');
  }, { tone: 'danger' });
  return el('div', {}, [bar([approve, dismiss]), reviewChange(row, intents, say)]);
}

function reviewCard(row, intents, say) {
  const where = `${row.member?.name || 'somebody'} in #${row.channel?.name || '?'} · ${when(row.at)}`;
  const suggestion = row.suggestion;
  return el('div', { class: 'card review-item', 'data-status': row.status, 'data-reason': row.reason }, [
    el('div', { class: 'card-body' }, [
      el('div', { class: 'req-head' }, [
        el('div', { class: 'req-headtext' }, [
          el('p', { class: 'req-what', text: row.asked }),
          el('p', { class: 'section-note' }, [
            el('span', { text: `${where} · ` }),
            row.link ? el('a', { href: row.link, text: 'open in Discord', target: '_blank', rel: 'noopener' }) : null,
          ]),
        ]),
        el('div', { class: 'req-marks' }, [
          badge(row.reason_word, 'warn'),
          row.status === 'open' ? null : badge(REVIEW_STATUS_WORDS[row.status] || row.status, null),
        ]),
      ]),
      el('p', { class: 'section-note review-answered', text: `Black Bloc answered: ${row.answered}` }),
      el('p', { class: 'review-suggestion' }, [
        el('span', { class: 'chat-answer-label', text: 'Suggested: ' }),
        ...boldParts(suggestion ? suggestion.word : 'not looked at yet'),
      ]),
      suggestion?.why ? el('p', { class: 'section-note', text: suggestion.why }) : null,
      reviewMoves(row, intents, say),
    ]),
  ]);
}

function reviewList(payload, say) {
  const rows = Array.isArray(payload?.items) ? payload.items : [];
  const intents = Array.isArray(payload?.intents) ? payload.intents : [];
  if (rows.length === 0) return sayNothing(REVIEW_EMPTY);
  return el('div', { class: 'chatblock' }, rows.map((row) => reviewCard(row, intents, say)));
}

function reviewPath() {
  const query = new URLSearchParams({ status: reviewView.status });
  if (reviewView.reason) query.set('reason', reviewView.reason);
  return `/api/chat/review?${query}`;
}

async function reviewSection(payload, specs, wordSpecs, say) {
  const counts = payload?.counts || {};
  const tagging = payload?.tagging || {};
  const one = section('Review queue', null, { count: counts.open || null, id: 'review' });
  const list = el('div', {}, [reviewList(payload, say)]);
  const statusPick = reviewPicker('Which items', [...(payload?.statuses || ['open']), 'all']
    .map((value) => [value, REVIEW_STATUS_WORDS[value] || value]), reviewView.status);
  const reasonPick = reviewPicker('Why they are here', [['', 'Every reason'],
    ...(payload?.reasons || []).map((row) => [row.key, row.word])], reviewView.reason);
  const reload = async () => {
    reviewView.status = statusPick.value;
    reviewView.reason = reasonPick.value;
    try {
      list.replaceChildren(reviewList(await api(reviewPath()), say));
    } catch (error) {
      say.say(error?.message || 'The queue could not be read just now — try again in a moment.', 'warn');
    }
  };
  statusPick.addEventListener('change', reload);
  reasonPick.addEventListener('change', reload);
  const download = el('a', { class: 'btn small quiet', href: '/api/chat/review.md', download: 'chat-review-queue.md', text: REVIEW_DOWNLOAD });
  one.body.append(card(null, [
    el('div', { class: 'chipbar' }, [
      badge(`${counts.open ?? 0} waiting`, counts.open ? 'warn' : null),
      badge(`${counts.untagged ?? 0} not tagged yet`, null),
      badge(`${counts.approved ?? 0} approved`, null),
      badge(`${counts.changed ?? 0} changed`, null),
      badge(`${counts.dismissed ?? 0} dismissed`, null),
    ]),
    el('p', { class: 'section-note', text: tagging.word || '' }),
    el('div', { class: 'formrow' }, [field('Which items', statusPick), field('Why they are here', reasonPick)]),
    bar([download]),
    say,
  ]));
  one.body.append(
    list,
    foldout(REVIEW_SETTINGS_TITLE, [
      await settingsPanel(specs, { where: 'Review queue', empty: NO_SETTINGS }),
    ], { count: specs.length || null }),
    foldout(REVIEW_WORDS_TITLE, [
      await settingsPanel(wordSpecs, { where: 'Review queue', empty: NO_SETTINGS }),
    ], { count: wordSpecs.length || null }),
  );
  return one.node;
}

async function load() {
  const [payload, allSettings, knowledge, personality, spend, memory, voices, review] = await Promise.all([
    api('/api/chat/intents'),
    settings(true),
    api('/api/chat/knowledge'),
    api('/api/chat/personality'),
    api('/api/chat/spend'),
    api('/api/chat/memory'),
    api('/api/chat/voices'),
    api(reviewPath()),
  ]);

  const intents = Array.isArray(payload?.intents) ? payload.intents : [];
  // The route carries the chat keys; /api/settings is the fallback and the only
  // home for emoji_skin_tone, which is not a chat key but is what its emoji wear.
  const given = Array.isArray(payload?.settings) ? payload.settings : [];
  const fromRoute = new Map(given.map((spec) => [spec.key, spec]));
  const fromRegistry = settingsNamespace(allSettings, 'chat');
  for (const spec of fromRegistry) if (!fromRoute.has(spec.key)) fromRoute.set(spec.key, spec);
  const skinTone = specFor(allSettings, 'emoji_skin_tone');
  if (skinTone) fromRoute.set('emoji_skin_tone', skinTone);
  const specs = SETTING_KEYS.map((key) => fromRoute.get(key)).filter(Boolean);
  const memorySpecs = MEMORY_SETTING_KEYS.map((key) => fromRoute.get(key)).filter(Boolean);
  const toneSpecs = TONE_KEYS.map((key) => fromRoute.get(key)).filter(Boolean);
  const voiceWordSpecs = VOICE_WORD_KEYS.map((key) => fromRoute.get(key)).filter(Boolean);
  const voiceSettleSpecs = VOICE_SETTLE_KEYS.map((key) => fromRoute.get(key)).filter(Boolean);
  const reviewSpecs = REVIEW_SETTING_KEYS.map((key) => fromRoute.get(key)).filter(Boolean);
  const reviewWordSpecs = [...fromRoute.values()]
    .filter((spec) => spec.key.startsWith(REVIEW_WORD_PREFIX) && !REVIEW_SETTING_KEYS.includes(spec.key));

  const memorySay = sayAgain('chat-memory', notice());
  const intentsSay = sayAgain('chat-intents', notice());
  const createSay = notice();
  const knowledgeSay = sayAgain('chat-knowledge', notice());
  const personalitySay = sayAgain('chat-personality', notice());
  const voicesSay = sayAgain('chat-voices', notice());
  const reviewSay = sayAgain('chat-review', notice());

  document.getElementById('dash').replaceChildren(
    trySection(),
    intentsSection(intents, intentsSay),
    newIntentSection(createSay),
    knowledgeSection(knowledge, knowledgeSay),
    await reviewSection(review, reviewSpecs, reviewWordSpecs, reviewSay),
    channelsSection(),
    await personalitySection(personality, personalitySay, toneSpecs),
    await voicesSection(voices, voiceWordSpecs, voicesSay, voiceSettleSpecs),
    await memorySection(memory, memorySpecs, memorySay),
    spendSection(spend),
    await settingsSection(specs),
    await logsSection('chat'),
  );
}

refresh = start({ tab: 'chat', load });
