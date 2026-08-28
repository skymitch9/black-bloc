import { api, send, settings, settingsNamespace } from './api.js';
import { start } from './app.js';
import {
  ask,
  badge,
  bar,
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
  section,
  segment,
  settingsPanel,
} from './ui.js';

const PER_PAGE = 50;
const LINE_LIMIT = 200;

const SETTING_KEYS = [
  'chat_mode',
  'chat_cooldown_seconds',
  'chat_ignore_channels',
  'chat_greeting_reaction',
  'chat_reply_in_threads',
  'chat_route_ping_staff',
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

async function settingsSection(specs) {
  const one = section('Settings', SETTINGS_NOTE, { count: specs.length || null });
  one.body.append(await settingsPanel(specs, { empty: NO_SETTINGS }));
  return one.node;
}

async function load() {
  const [payload, allSettings] = await Promise.all([
    api('/api/chat/intents'),
    settings(true),
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

  document.getElementById('dash').replaceChildren(
    trySection(),
    intentsSection(intents, intentsSay),
    newIntentSection(createSay),
    await settingsSection(specs),
  );
}

refresh = start({ tab: 'chat', load });
