import { api, send, settings, settingsNamespace } from './api.js';
import { start } from './app.js';
import { logsSection } from './logs.js';
import {
  ask,
  badge,
  bar,
  boldParts,
  button,
  card,
  el,
  field,
  keepSaying,
  notice,
  pager,
  run,
  sayAgain,
  sayNothing,
  searchOver,
  section,
  segment,
  settingsPanel,
  textAction,
  when,
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
  'chat_staff_can_ping_roles',
  'chat_greeting_reaction',
  'chat_reply_in_threads',
  'chat_route_ping_staff',
  'chat_llm_mode',
  'chat_monthly_cap_usd',
  'chat_status_admin_only',
  'chat_log_level',
  'emoji_skin_tone',
];

const TRY_NOTE = 'Type what somebody would say after the @-mention and Black Bloc tells you ' +
  'which intent it lands on and the exact line it would answer with. This is a dry run — ' +
  'nothing is sent anywhere.';
const INTENTS_NOTE = 'One card per thing Black Bloc understands. A canned intent answers from ' +
  'its own lines; a data intent fills its line in from what the server is doing right now; a ' +
  'route intent hands the person to staff.';
const NEW_NOTE = 'A canned intent of your own. It is matched before the built-in ones, so a ' +
  'phrase you claim here wins.';
const SETTINGS_NOTE = 'Whether Black Bloc answers at all, how often the same person gets a ' +
  'reply, and the channels it stays out of.';

const KNOWLEDGE_NOTE = 'What Black Bloc knows about this server in its own words. When somebody ' +
  'asks something the phrases above do not cover, the closest few notes ride along with the ' +
  'question so the answer quotes them instead of inventing something.';
const PERSONALITY_NOTE = 'How Black Bloc sounds. The cookout voice is the house one; the pool is ' +
  'eleven voices it picks between, a different one per conversation, moving a step at a time. ' +
  'None of them changes what it says — only how it says it.';
const SPEND_NOTE = 'What answering has cost this month, how many answers came from a model ' +
  'today, and which of the three tiers is actually answering right now.';
const NO_KNOWLEDGE = 'Black Bloc has nothing written down about this server yet, so it answers ' +
  'every question from the phrases above and its own wording.';
const NO_TROPES = 'The voice pool is empty, so Black Bloc keeps the cookout voice whatever this ' +
  'is set to.';
const NEED_A_TITLE = 'Give the note a heading first — that is the line a question is matched ' +
  'against.';
const NEED_A_BODY = 'Write the note first, or there is nothing for Black Bloc to quote.';
const NOTE_UNCHANGED = 'Nothing in that note is different, so nothing was saved.';
const CAP_LIVES_IN_SETTINGS = 'The cap itself is a setting.';
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
const BUILTIN_KEPT = 'Built in, so it cannot be deleted — turn it off above and it stays quiet. ' +
  'Its phrases and its lines are still yours.';

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

function tokensOf(intent) {
  const given = Array.isArray(intent.tokens) && intent.tokens.length ? intent.tokens : null;
  return ['{name}', '{attendees}'].concat(given || OWN_TOKENS[intent.name] || []);
}

function tokenHelp(intent) {
  return tokensOf(intent)
    .map((token) => `${token} = ${TOKEN_SAID[token] || 'filled in by the bot'}`)
    .join(' · ');
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
      field('Add a phrase', box, 'Whole words, so “help” does not match “helping”. Enter adds it.'),
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
      field('Add a line', box, `Up to ${LINE_LIMIT} characters. Enter adds it.`),
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
    : el('input', { class: 'input mono', type: 'text', value: intent.name, 'aria-label': 'Intent name' });
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
      field('Name', nameBox, intent.builtin ? 'One of Black Bloc’s own, so the name is fixed.' : 'Letters, numbers and underscores.'),
      field('Kind', kind, KIND_SAID[intent.kind] || null),
      field('Answers', enabled, 'Quiet leaves the phrases in place and says nothing.'),
      saveName ? bar([saveName]) : null,
    ]),
    triggerBlock(intent, say, swap),
    lineBlock(intent, say, swap),
    el('p', { class: 'section-note', text: tokenHelp(intent) }),
    drop ? bar([drop]) : el('p', { class: 'say-nothing', text: BUILTIN_KEPT }),
    say,
  ]));
  return node;
}

function intentsSection(intents, say) {
  const one = section('Intents', INTENTS_NOTE, { count: intents.length, open: true });
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

  const one = section('Try it', TRY_NOTE, { open: true });
  one.body.append(card(null, [
    el('div', { class: 'formrow' }, [
      field('Message', box, 'The part after the @-mention. Enter runs it.'),
      bar([button('Try it', go, { tone: 'warn', small: false })]),
    ]),
    answer,
    say,
  ]));
  return one.node;
}

function newIntentSection(say) {
  const name = el('input', { class: 'input mono', type: 'text', placeholder: 'wheres_the_food' });
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

  const one = section('New intent', NEW_NOTE, {});
  one.body.append(card(null, [
    el('div', { class: 'formrow' }, [
      field('Name', name, 'Letters, numbers and underscores — this is what the log calls it.'),
      field('Trigger phrases', triggers, 'Separated by commas. Whole words, not letters inside one.'),
      field('First line', line, '{name} is filled in with whoever asked.'),
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
        field('Heading', title, 'What a question is matched against.'),
        field('About', tag, 'One word, so you can find it again. Optional.'),
        el('div', { class: 'chipbar' }, [
          badge(row.source === 'server' ? 'Black Bloc wrote this' : 'staff wrote this',
            row.source === 'server' ? 'warn' : null),
          el('span', { class: 'chat-answer-label', text: `${row.characters} characters` }),
        ]),
      ]),
      field('What it says', body, 'Plain words. Black Bloc quotes this rather than paraphrasing it.'),
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
      field('Heading', title, `Up to ${TITLE_LIMIT} characters.`),
      field('About', tag, 'Optional, and only for finding it again.'),
    ]),
    field('What it says', body, `Up to ${BODY_LIMIT} characters. A note that will not fit in an answer is left out whole rather than cut short.`),
    bar([add]),
  ], { count: null });
}

function knowledgeSection(payload, say) {
  const rows = Array.isArray(payload?.sections) ? payload.sections : [];
  const counts = payload?.counts || {};
  const one = section('Knowledge', KNOWLEDGE_NOTE, { count: rows.length || null });
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
      ]),
      el('p', { class: 'chat-answer-line', text: row.voice }),
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

function personalitySection(payload, say) {
  const rows = Array.isArray(payload?.tropes) ? payload.tropes : [];
  const mode = String(payload?.mode || MODE_COOKOUT);
  const kind = String(payload?.mode_kind || MODE_COOKOUT);
  const one = section('Personality', PERSONALITY_NOTE, { count: payload?.counts?.enabled ?? null });

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

  one.body.append(
    card(null, [
      el('div', { class: 'formrow' }, [
        field('The voice', pick, 'A voice is tone and never truth — the same facts either way.'),
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
  const one = section('Spend & tiers', SPEND_NOTE, { count: live || null });
  const share = Math.max(0, Math.min(1, Number(month.share) || 0));

  one.body.append(card(null, [
    el('div', { class: 'chipbar' }, [
      el('span', { class: 'spend-figure', text: `$${Number(month.spent_usd || 0).toFixed(2)}` }),
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
    sayNothing(
      CAP_LIVES_IN_SETTINGS,
      textAction(`Change ${payload?.cap_key || 'the cap'}`, openSettings),
    ),
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

async function settingsSection(specs) {
  const one = section('Settings', SETTINGS_NOTE, { count: specs.length || null });
  one.body.append(await settingsPanel(specs, { where: 'Settings', empty: NO_SETTINGS }));
  return one.node;
}

async function load() {
  const [payload, allSettings, knowledge, personality, spend] = await Promise.all([
    api('/api/chat/intents'),
    settings(true),
    api('/api/chat/knowledge'),
    api('/api/chat/personality'),
    api('/api/chat/spend'),
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

  const intentsSay = sayAgain('chat-intents', notice());
  const createSay = notice();
  const knowledgeSay = sayAgain('chat-knowledge', notice());
  const personalitySay = sayAgain('chat-personality', notice());

  document.getElementById('dash').replaceChildren(
    trySection(),
    intentsSection(intents, intentsSay),
    newIntentSection(createSay),
    knowledgeSection(knowledge, knowledgeSay),
    personalitySection(personality, personalitySay),
    spendSection(spend),
    await settingsSection(specs),
    await logsSection('chat'),
  );
}

refresh = start({ tab: 'chat', load });
