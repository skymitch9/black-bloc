/** Preview of a redesigned Chat page. Static data; no api() call lives here. */
import { start } from './app.js';
import { logsTable } from './logs.js';
import {
  badge,
  bar,
  boldParts,
  button,
  card,
  channelLabel,
  el,
  field,
  foldout,
  humanLabel,
  icon,
  notice,
  openDrawer,
  sayNothing,
  searchOver,
  section,
  segment,
  when,
} from './ui.js';
import { previewBanner, previewWas, wouldDo } from './preview.js';

let refresh = () => {};

const LINE_LIMIT = 200;
const TITLE_LIMIT = 100;
const BODY_LIMIT = 4000;

const TRY_NOTE = 'Type what somebody would say after the @-mention and Black Bloc tells you '
  + 'which intent it lands on and the exact line it would answer with. This is a dry run — '
  + 'nothing is sent anywhere.';
const NEW_NOTE = 'A canned intent of your own. It is matched before the built-in ones, so a '
  + 'phrase you claim here wins.';
const SETTINGS_NOTE = 'Whether Black Bloc answers at all, how often the same person gets a '
  + 'reply, and the channels it stays out of.';
const KNOWLEDGE_NOTE = 'What Black Bloc knows about this server in its own words. When somebody '
  + 'asks something the phrases above do not cover, the closest few notes ride along with the '
  + 'question so the answer quotes them instead of inventing something.';
const PERSONALITY_NOTE = 'How Black Bloc sounds. The cookout voice is the house one; the pool is '
  + 'eleven voices it picks between, a different one per conversation, moving a step at a time. '
  + 'None of them changes what it says — only how it says it.';
const SPEND_NOTE = 'How many answers came from a model today and which of the three tiers is '
  + 'actually answering right now. The money itself lives on the Health page, where hosting and '
  + 'the keys are — this figure links to it.';
const COSTS_CARD = '/health.html#sect-costs';
const COSTS_TITLE = 'What everything costs, on the Health page';
const MEMORY_NOTE = 'What Black Bloc remembers about each person between conversations — '
  + 'preferences only, never anything anybody said. A profile is written after a conversation '
  + 'ends, never while one is going on.';
const MEMORY_COUNTS_ONLY = 'This server keeps the notes themselves private to the person they '
  + 'are about, so only the counts are shown here. Set chat_memory_staff_view to full below if '
  + 'staff should read them.';
const MEMORY_DM_MARK = 'learned in a DM';
const BUILTIN_KEPT = 'Built in, so it cannot be deleted — turn it off above and it stays quiet. '
  + 'Its phrases and its lines are still yours.';
const TIER_LIVE_WORD = 'answering';
const TIER_QUIET_WORD = 'not answering';
const MODE_LABELS = { cookout: 'The cookout voice', pool: 'The pool' };
const LOGS_NOTE = 'Everything this part of Black Bloc has done, whether or not it said so in Discord. '
  + 'Important means it acted on a member or failed.';

const KIND_SAID = {
  canned: 'Answers with one of the lines below, picked at random.',
  data: 'Fills its line in from what the server is doing right now.',
  route: 'Hands the person to staff rather than answering itself.',
};
const KIND_TONE = { canned: null, data: 'ok', route: 'warn' };

const OWN_TOKENS = {
  who_is_live: ['{names}', '{count}'],
  need_a_mod: ['{staff_roles}', '{ticket_how}'],
};

const TOKEN_SAID = {
  '{name}': 'who asked',
  '{attendees}': 'head count',
  '{names}': 'who is live',
  '{count}': 'how many',
  '{staff_roles}': 'the staff roles',
  '{ticket_how}': 'how to open a ticket',
};

const minutesAgo = (minutes) => new Date(Date.now() - minutes * 60000).toISOString();

const CHANNELS = [
  { id: '800000000000000001', name: 'welcome', type: 'text', category_id: null },
  { id: '800000000000000002', name: 'general', type: 'text', category_id: null },
  { id: '800000000000000003', name: 'blackbloc-logs', type: 'text', category_id: null },
  { id: '800000000000000004', name: 'bot-log', type: 'text', category_id: null },
  { id: '800000000000000005', name: 'staff-room', type: 'text', category_id: null },
  { id: '800000000000000006', name: 'announcements', type: 'text', category_id: null },
  { id: '800000000000000007', name: 'free-nitro-here', type: 'text', category_id: null },
  { id: '800000000000000011', name: 'modmail', type: 'category', category_id: null },
  { id: '800000000000000012', name: 'modmail-log', type: 'text', category_id: '800000000000000011' },
];

const ROLES = [
  { id: '900000000000000001', name: 'Aunties / Uncles' },
  { id: '900000000000000002', name: 'Leads' },
  { id: '900000000000000005', name: 'Members' },
  { id: '1073741054563602532', name: 'Members' },
];

/** site/mock/server.mjs state.chatIntents + state.chatLines + state.knowledge, verbatim. */
const DATA = {
  intents: [
    {
      id: '1',
      name: 'cookout_hours',
      kind: 'canned',
      enabled: true,
      builtin: false,
      triggers: ['when is the cookout'],
      updated_at: minutesAgo(50),
      lines: [{ id: '1', text: 'Doors at six, {name}.', enabled: true }],
    },
    {
      id: '2',
      name: 'need_a_mod',
      kind: 'route',
      enabled: true,
      builtin: true,
      triggers: ['i need a mod', 'staff please', 'help me'],
      updated_at: minutesAgo(9000),
      lines: [
        { id: '2', text: 'DM me and I will open a ticket for staff, {name}.', enabled: true },
        { id: '3', text: 'Staff to ask, {name}: {roles}.', enabled: true },
      ],
    },
    {
      id: '3',
      name: 'who_is_live',
      kind: 'data',
      enabled: true,
      builtin: true,
      triggers: ['whos live', 'who is live', 'anyone live'],
      updated_at: minutesAgo(9000),
      lines: [
        { id: '4', text: 'Live right now, {name}: {names} — {links}', enabled: true },
        { id: '5', text: 'Nobody is streaming right now, {name} — the cookout is all off-camera.', enabled: true },
      ],
    },
    {
      id: '4',
      name: 'greeting',
      kind: 'canned',
      enabled: true,
      builtin: true,
      triggers: ['hi', 'hey', 'hello', 'good morning'],
      updated_at: minutesAgo(9000),
      lines: [
        { id: '6', text: 'Hey {name}! Pull up a chair — the cookout is already going.', enabled: true },
        { id: '7', text: 'Hey {name}! That makes {attendees} of us at the cookout today.', enabled: true },
      ],
    },
  ],
  knowledge: {
    sections: [
      {
        id: '1',
        title: 'Cookout hours',
        body: 'The grill goes on at six on a Saturday and the last plate goes out about nine. Nobody minds if you turn up late.',
        tag: 'cookout',
        source: 'staff',
        source_word: 'written here by staff',
        editable: true,
        locked_why: null,
        characters: 118,
        updated_at: minutesAgo(300),
        updated_by: { id: '700000000000000001', name: 'Nick' },
      },
      {
        id: '2',
        title: 'How to get a role',
        body: 'Pick one from the role menus in #roles. A few of them are asked for rather than taken, and staff answer those on the site.',
        tag: 'roles',
        source: 'staff',
        source_word: 'written here by staff',
        editable: true,
        locked_why: null,
        characters: 125,
        updated_at: minutesAgo(4000),
        updated_by: { id: '700000000000000002', name: 'Casey' },
      },
      {
        id: '3',
        title: 'Channels',
        body: 'general — the front room. cookout-planning — who is bringing what. free-nitro-here — a trap, do not post in it.',
        tag: null,
        source: 'server',
        source_word: 'written by Black Bloc from the server itself, every day',
        editable: false,
        locked_why: '**Channels** is one of the notes Black Bloc writes for itself out of the server — the channel list, the roles, what is coming up — so it cannot be changed by hand. It is written again from scratch every day, and an edit here would be gone by morning. Write your own note beside it and Black Bloc reads both.',
        characters: 113,
        updated_at: minutesAgo(120),
        updated_by: null,
      },
    ],
    counts: { staff: 2, server: 1 },
    budget: { word: 'At most 3 notes ride an answer, and a note that will not fit is left out rather than cut short.' },
  },
  personality: {
    mode: 'cookout',
    mode_kind: 'cookout',
    mode_word: 'Everybody gets the cookout voice — warm, playful, the one the rest of the site is written in.',
    counts: { total: 11, enabled: 10 },
    ported_from: 'catalog-platform@03dcb91',
    tropes: [
      ['peppy', 'peppy', 'You are BRIGHT and fast today — genuinely glad to have been asked. Short exclamations, visible delight in the question, quick to celebrate somebody’s good news.', true],
      ['dramatic', 'dramatic', 'You are THEATRICAL today — grand pronouncements about small things, a flair for the reveal. The drama is in the framing; what you actually tell somebody stays plain.', true],
      ['mischievous', 'mischievous', 'You are PLAYFUL today — light teasing, a raised eyebrow, enjoying yourself. Never mean, and never holding something back to be coy about it.', true],
      ['flirty', 'flirty', 'You are CHARMING today, with a playful wink — light compliments, affectionate teasing. CHARM, NOT HEAT, and you never get flustered into dropping the answer.', true],
      ['warm', 'warm', 'You are WARM today — familiar, unhurried, glad to see them. Kind without being saccharine.', true],
      ['cozy', 'cozy', 'You are COSY today — the voice of a folding chair in the shade and a full plate. Calm rather than sleepy.', true],
      ['shy', 'shy', 'You are a little SHY today — soft, hedging, apologetic about taking up room. BUT YOU STILL GIVE THE WHOLE ANSWER, first time.', true],
      ['scholar', 'scholarly', 'You are SCHOLARLY today — precise, fond of getting a detail exactly right. Pedantic about accuracy, never about the person.', true],
      ['noir', 'noir', 'You are HARD-BOILED today — clipped sentences, a little world-weary, everything faintly a metaphor about rain and long odds.', false],
      ['deadpan', 'deadpan', 'You are DEADPAN today — flat, economical, dry. The joke is the flatness. Few words, all of them load-bearing.', true],
      ['tsundere', 'tsundere', 'You are BRUSQUE today, and helping anyway — mildly put upon. THE GRUMBLING IS ALL SURFACE: you still answer fully and promptly.', true],
    ].map(([name, label, voice, enabled]) => ({
      name,
      label,
      voice,
      enabled,
      in_use: false,
      updated_at: name === 'noir' ? minutesAgo(700) : minutesAgo(9000),
      updated_by: name === 'noir' ? { id: '700000000000000001', name: 'Nick' } : null,
    })),
  },
  memory: {
    mode: 'off',
    on: false,
    staff_view: 'counts',
    total: 3,
    opted_out: 1,
    dm_notes: 1,
    message: 'Black Bloc is not remembering anybody on this server, so there is nothing here yet. The Memory switch above turns it on, and profiles start appearing after the next sweep.',
    profiles: [
      { member: { id: '700000000000000002', name: 'Casey' }, call_me: null, notes: 2, threads: 1, turns_seen: 14, updated_at: minutesAgo(200), lines: [] },
      { member: { id: '700000000000000004', name: 'Moth' }, call_me: null, notes: 1, threads: 0, turns_seen: 4, updated_at: minutesAgo(1400), lines: [] },
      { member: { id: '700000000000000007', name: 'Dax' }, call_me: null, notes: 1, threads: 0, turns_seen: 6, updated_at: minutesAgo(4000), lines: [] },
    ],
  },
  // Computed from a 112-row ledger in the mock rather than seeded as literals, so this is a
  // static snapshot of what that arithmetic produces, not a copied row.
  spend: {
    month: { spent_usd: 0.28, cap_usd: 20, left_usd: 19.72, share: 0.014, word: '$0.28 of the $20 Black Bloc may spend this month, so $19.72 is left.' },
    today: { turns: 37, limit: 200, word: '37 answers came from a model today, out of the 200 a day Black Bloc gives.' },
    tiers: [
      { name: 'intents', label: 'Phrases', live: true, word: 'Always on. The phrases on this page answer first, they cost nothing, and they are checked before any model is asked.' },
      { name: 'important', label: 'Claude Haiku', live: true, word: 'Live. Grounded answers and longer questions go here.' },
      { name: 'simple', label: 'Groq Llama', live: false, word: 'Black Bloc has not been given a **GROQ_API_KEY** yet, so this tier does not exist and the answer falls through to the next one. A Lead sets it on the host.' },
    ],
    capped: false,
    cap_key: 'chat_monthly_cap_usd',
    last_turn_at: minutesAgo(6),
  },
  settings: [
    { key: 'chat_mode', type: 'enum', value: 'on', default: 'on', help: 'off, or on (Black Bloc answers when somebody @-mentions it)', choices: ['off', 'on'] },
    { key: 'chat_cooldown_seconds', type: 'int', value: 20, default: 20, help: 'seconds before the same person gets another @-mention reply, 5 to 600' },
    { key: 'chat_ignore_channels', type: 'channels', value: [], default: [], help: 'channels Black Bloc never answers an @-mention in' },
    { key: 'chat_ignore_categories', type: 'channels', value: [], default: [], help: 'categories Black Bloc leaves out of everything it reads and tells people about — the channel names and topics it learns each day, and the channel list every conversational answer is written against. The modmail category and any category with `archive` in its name are left out already, and so is every channel @everyone cannot see' },
    { key: 'chat_home_channel_id', type: 'channel', value: null, default: null, help: 'where somebody is sent when a conversational answer points at a channel that does not exist. Blank is safe: the sentence is written again without the channel in it rather than pointing anywhere. Either way the invention is logged, so `/chat` ▸ **Logs** and the Logs page count how often it happens' },
    { key: 'chat_visibility_role_id', type: 'role', value: '1073741054563602532', default: '1073741054563602532', help: "the role whose view of the server IS the bot's map: channels this role can read are the ones the bot may learn about, list and point people at. This server hides everything from @everyone until the rules screen grants Member, so the default is the Member role - clearing it falls back to @everyone, which on this server means almost no channels at all" },
    { key: 'chat_staff_can_ping_roles', type: 'bool', value: true, default: true, help: "on lets Black Bloc's conversational answers mention a role when the person who @-mentioned it is staff — an Auntie or Uncle and up. Nobody else can make it ping anything, and `@everyone` and `@here` never go through for anyone. Off means a conversational answer pings nobody at all, whoever asked" },
    { key: 'chat_escalation_names', type: 'int', value: 2, default: 2, help: 'how many online staff Black Bloc names when somebody asks for a mod, 0 to name nobody and up to 10. They are named in plain words, never pinged — the person does that themselves. Nobody online says so instead' },
    { key: 'chat_greeting_reaction', type: 'bool', value: false, default: false, help: 'true to answer a bare hello with a wave reaction instead of a sentence; anything longer still gets a reply' },
    { key: 'chat_reply_in_threads', type: 'bool', value: true, default: true, help: 'true to answer @-mentions inside threads as well as channels' },
    { key: 'chat_route_ping_staff', type: 'bool', value: false, default: false, help: 'true to drop one line in the staff channel when somebody asks the bot for a mod; only used while modmail_enabled is true' },
    { key: 'chat_llm_mode', type: 'enum', value: 'on', default: 'off', help: 'off, or on (an @-mention no built-in intent recognises is answered by a language model instead of the catch-all line). Off is the default and off is safe: with it off, or with no keys set, Black Bloc answers exactly as it does today', choices: ['off', 'on'] },
    { key: 'chat_monthly_cap_usd', type: 'int', value: 20, default: 20, help: 'whole dollars a month Black Bloc may run the conversation models for, up to 1000. At the figure it stops calling them until the 1st and answers from its own written lines; 0 stops them altogether' },
    { key: 'chat_status_admin_only', type: 'bool', value: true, default: true, help: "on keeps the spend block on `/chat` (what the conversation models are spending) to server administrators; the rest of the panel still opens for any staff member, and off lets them read the spend too. The dashboard's Spend section stays staff-visible either way" },
    { key: 'chat_log_level', type: 'enum', value: 'important', default: 'important', help: 'which chat log lines reach the Discord log channel: off, important (anything that acted on a member, or failed) or all. Every line is kept on the dashboard and in `/chat logs` either way', choices: ['off', 'important', 'all'] },
    { key: 'emoji_skin_tone', type: 'enum', value: 'dark', default: 'dark', help: "the skin tone Black Bloc's hand and people emoji wear: none, light, medium-light, medium, medium-dark, dark", choices: ['none', 'light', 'medium-light', 'medium', 'medium-dark', 'dark'] },
  ],
  memorySettings: [
    { key: 'chat_memory_mode', type: 'enum', value: 'off', default: 'off', help: 'off, or on (Black Bloc keeps a few preferences about each person — what to call them, how they like to be answered — and reads them back next time). Off writes nothing and reads nothing; the profiles already stored stay until somebody clears them', choices: ['off', 'on'] },
    { key: 'chat_memory_consent', type: 'enum', value: 'optout', default: 'optout', help: 'optout means memory is on for everybody until they stop it themselves on the `/memory` panel; optin means nobody is remembered until they start it there', choices: ['optout', 'optin'] },
    { key: 'chat_memory_dm_scope', type: 'enum', value: 'separate', default: 'separate', help: 'separate keeps what Black Bloc learns in a DM out of public channels — a name or pronouns set by DM never reach the server; shared lets every note be used anywhere', choices: ['separate', 'shared'] },
    { key: 'chat_memory_staff_view', type: 'enum', value: 'counts', default: 'counts', help: 'counts shows staff only how many profiles there are and when each changed; full lets staff read the notes themselves. The person can always read their own with `/memory`', choices: ['counts', 'full'] },
    { key: 'chat_memory_retention_days', type: 'int', value: 180, default: 180, help: 'days a profile nobody has added to is kept before it is deleted, up to 3650; 0 keeps them forever. Leaving the server clears one straight away' },
    { key: 'chat_memory_notes_max', type: 'int', value: 6, default: 6, help: 'how many preferences one profile holds, up to 20; the oldest drops off when a newer one arrives' },
    { key: 'chat_memory_threads_max', type: 'int', value: 5, default: 5, help: 'how many open topics (“was asking about the Thursday event”) one profile holds, up to 20' },
    { key: 'chat_memory_model', type: 'text', value: '', default: '', help: 'which Groq model writes the profile up after a conversation ends; blank uses chat_simple_model, the same quick tier that answers' },
  ],
  logs: [
    { id: 39, at: minutesAgo(35), kind: 'chat.answered', important: false, via: 'discord', actor_id: null, actor_name: null, target_id: '700000000000000002', target_name: 'Casey', reason: 'greeting' },
    { id: 33, at: minutesAgo(900), kind: 'chat.routed', important: true, via: 'discord', actor_id: null, actor_name: null, target_id: '700000000000000004', target_name: 'Moth', reason: 'need_a_mod' },
  ],
};

const SETTINGS_WOULD = (key) => `PUT /api/settings/${key} — save the new value`;

/** A settings row that looks like ui.js:settingRow and saves nothing. */
function staticRow(spec) {
  const say = notice();
  const control = () => {
    if (spec.type === 'enum' && spec.choices.length <= 3) {
      return segment(spec.choices.map((one) => ({ value: one, label: one })), spec.value, {
        onChange: () => wouldDo(say, SETTINGS_WOULD(spec.key)),
      });
    }
    if (spec.type === 'enum') {
      const select = el('select', { class: 'input' });
      for (const one of spec.choices) {
        select.append(el('option', { value: one, text: one, selected: one === spec.value ? true : undefined }));
      }
      select.addEventListener('change', () => wouldDo(say, SETTINGS_WOULD(spec.key)));
      return select;
    }
    if (spec.type === 'bool') {
      const box = el('input', { class: 'input switch', type: 'checkbox', checked: spec.value ? true : undefined });
      box.addEventListener('change', () => wouldDo(say, SETTINGS_WOULD(spec.key)));
      return box;
    }
    if (spec.type.startsWith('role') || spec.type.startsWith('channel')) {
      const many = spec.type.endsWith('s');
      const held = new Set((Array.isArray(spec.value) ? spec.value : [spec.value]).filter(Boolean).map(String));
      const select = el('select', { class: 'input', multiple: many ? true : undefined, size: many ? '4' : undefined });
      if (!many) select.append(el('option', { value: '', text: 'not set' }));
      const source = spec.type.startsWith('role') ? ROLES : CHANNELS;
      for (const one of source) {
        select.append(el('option', {
          value: String(one.id),
          text: spec.type.startsWith('role') ? one.name : channelLabel(one, CHANNELS),
          selected: held.has(String(one.id)) ? true : undefined,
        }));
      }
      select.addEventListener('change', () => wouldDo(say, SETTINGS_WOULD(spec.key)));
      return select;
    }
    const box = el('input', {
      class: 'input',
      type: spec.type === 'int' ? 'number' : 'text',
      value: spec.value === null || spec.value === undefined ? '' : String(spec.value),
    });
    box.addEventListener('change', () => wouldDo(say, SETTINGS_WOULD(spec.key)));
    return box;
  };
  const node = el('div', { class: 'setrow', 'data-key': spec.key, 'data-dirty': 'false' }, [
    el('div', { class: 'setrow-head' }, [
      el('span', { class: 'setrow-label', text: humanLabel(spec.key), title: spec.help || undefined }),
      el('span', { class: 'setrow-key', text: spec.key }),
    ]),
    el('div', { class: 'setrow-control' }, [control()]),
    say,
  ]);
  say.classList.add('setrow-say');
  return node;
}

const staticSettings = (specs) => el('div', { class: 'settings-grid' }, specs.map(staticRow));

function tokenHelp(intent) {
  return ['{name}', '{attendees}'].concat(OWN_TOKENS[intent.name] || [])
    .map((token) => `${token} = ${TOKEN_SAID[token] || 'filled in by the bot'}`)
    .join(' · ');
}

/** page-polls.js:170 — the kind is a chip, and its reason lives in the title. ONE home. */
function kindChip(intent) {
  const chip = badge(intent.kind, KIND_TONE[intent.kind] ?? null);
  chip.setAttribute('title', KIND_SAID[intent.kind] || '');
  return chip;
}

/** page-chat.js:174 lineRow, verbatim, with the three writes turned into notes. */
function lineRow(intent, line, say) {
  const box = el('input', {
    class: 'input',
    type: 'text',
    value: line.text,
    maxlength: String(LINE_LIMIT),
    'aria-label': `What ${intent.name} says`,
  });
  const save = button('Save', () => {
    wouldDo(say, `PUT /api/chat/lines/${line.id} — save this wording`);
  }, { disabled: true });
  box.addEventListener('input', () => {
    save.disabled = box.value.trim() === line.text || box.value.trim() === '';
  });
  const flip = button(line.enabled ? 'Turn off' : 'Turn on', () => {
    wouldDo(say, `PUT /api/chat/lines/${line.id} — take this line out of the pile, or put it back`);
  }, { tone: 'quiet' });
  const drop = button('Remove', () => {
    wouldDo(say, `DELETE /api/chat/lines/${line.id} — stop Black Bloc saying it; the other ${intent.lines.length - 1} line(s) stay`);
  }, { tone: 'danger' });
  return el('div', { class: 'chatline', 'data-enabled': line.enabled ? 'true' : 'false' }, [
    box,
    line.enabled ? null : el('span', { class: 'chatline-off', text: 'off' }),
    bar([save, flip, drop]),
  ].filter(Boolean));
}

function triggerChip(intent, phrase, say) {
  return el('span', { class: 'trigchip' }, [
    el('span', { class: 'trigchip-name', text: phrase, title: phrase }),
    el('button', {
      class: 'trigchip-x',
      type: 'button',
      text: '×',
      'aria-label': `Remove the phrase ${phrase}`,
      on: { click: () => wouldDo(say, `PUT /api/chat/intents/${intent.id} — stop Black Bloc answering to “${phrase}”`) },
    }),
  ]);
}

/** page-chat.js:355 intentCard, moved into the drawer one row opens. */
function intentEditor(intent) {
  const say = notice();
  const nameBox = intent.builtin
    ? el('span', { class: 'chat-fixed', text: intent.name })
    : el('input', { class: 'input mono', type: 'text', value: intent.name, 'aria-label': 'Intent name' });
  const saveName = intent.builtin ? null : button('Rename', () => {
    wouldDo(say, `PUT /api/chat/intents/${intent.id} — rename it`);
  }, { tone: 'quiet' });

  const enabled = segment(
    [{ value: 'true', label: 'Answering' }, { value: 'false', label: 'Quiet' }],
    intent.enabled ? 'true' : 'false',
    { onChange: () => wouldDo(say, `PUT /api/chat/intents/${intent.id} — turn this intent to answering or quiet`) },
  );

  const phrase = el('input', {
    class: 'input',
    type: 'text',
    placeholder: 'a phrase somebody would type',
    'aria-label': `A new trigger phrase for ${intent.name}`,
  });
  const newLine = el('input', {
    class: 'input',
    type: 'text',
    maxlength: String(LINE_LIMIT),
    placeholder: 'another way of saying it',
    'aria-label': `A new line for ${intent.name}`,
  });
  const drop = intent.builtin ? null : button('Delete', () => {
    wouldDo(say, `DELETE /api/chat/intents/${intent.id} — stop Black Bloc answering to its phrases, and take its lines with it`);
  }, { tone: 'danger' });

  return [card(null, [
    el('div', { class: 'formrow' }, [
      field('Name', nameBox, intent.builtin ? 'One of Black Bloc’s own, so the name is fixed.' : 'Letters, numbers and underscores.'),
      field('Kind', kindChip(intent)),
      field('Answers', enabled, 'Quiet leaves the phrases in place and says nothing.'),
      saveName ? bar([saveName]) : null,
    ].filter(Boolean)),
    el('div', { class: 'chatblock' }, [
      el('h4', { text: 'Trigger phrases' }),
      intent.triggers.length === 0
        ? sayNothing('No phrases, so nothing reaches this intent.')
        : el('div', { class: 'chipbar' }, intent.triggers.map((one) => triggerChip(intent, one, say))),
      el('div', { class: 'formrow' }, [
        field('Add a phrase', phrase, 'Whole words, so “help” does not match “helping”. Enter adds it.'),
        bar([button('Add', () => wouldDo(say, `PUT /api/chat/intents/${intent.id} — add that phrase`), { tone: 'quiet' })]),
      ]),
    ]),
    el('div', { class: 'chatblock' }, [
      el('h4', { text: `Lines (${intent.lines.filter((line) => line.enabled).length} of ${intent.lines.length} in the pile)` }),
      intent.lines.length === 0
        ? sayNothing('No lines, so Black Bloc falls back to the wording in its own code.')
        : el('div', { class: 'chatlines' }, intent.lines.map((line) => lineRow(intent, line, say))),
      el('div', { class: 'formrow' }, [
        field('Add a line', newLine, `Up to ${LINE_LIMIT} characters. Enter adds it.`),
        bar([button('Add', () => wouldDo(say, `POST /api/chat/intents/${intent.id}/lines — add that line`), { tone: 'quiet' })]),
      ]),
    ]),
    el('p', { class: 'section-note', text: tokenHelp(intent) }),
    drop ? bar([drop]) : el('p', { class: 'say-nothing', text: BUILTIN_KEPT }),
    say,
  ])];
}

const INTENT_GRID = 'grid-template-columns: minmax(0, 1fr) 110px 130px 150px 120px 24px;';

function intentRow(intent) {
  return el('button', {
    class: 'grid-row',
    type: 'button',
    style: INTENT_GRID,
    'data-search': `${intent.name} ${intent.kind} ${intent.triggers.join(' ')} ${intent.lines.map((one) => one.text).join(' ')}`.toLowerCase(),
    on: { click: () => openDrawer(intent.name, intentEditor(intent)) },
  }, [
    el('span', { class: 'cell-name', text: intent.name }),
    kindChip(intent),
    badge(intent.enabled ? 'Answering' : 'Quiet', intent.enabled ? 'ok' : 'warn'),
    el('span', { class: 'cell-quiet', text: `${intent.triggers.length}` }),
    el('span', { class: 'cell-quiet', text: `${intent.lines.filter((one) => one.enabled).length} of ${intent.lines.length}` }),
    icon('chevronRight', 16),
  ]);
}

/** page-chat.js:519 newIntentSection, folded into the page's one primary action. */
function newIntentDrawer() {
  const say = notice();
  const name = el('input', { class: 'input mono', type: 'text', placeholder: 'wheres_the_food' });
  const triggers = el('input', { class: 'input', type: 'text', placeholder: 'wheres the food, when do we eat' });
  const line = el('input', {
    class: 'input',
    type: 'text',
    maxlength: String(LINE_LIMIT),
    placeholder: 'The grill is always on, {name}.',
  });
  const create = button('Add the intent', () => {
    wouldDo(say, 'POST /api/chat/intents — add the intent, its phrases and its first line');
  }, { tone: 'warn', small: false });
  openDrawer('New intent', [card(null, [
    el('p', { class: 'section-note', text: NEW_NOTE }),
    el('div', { class: 'formrow' }, [
      field('Name', name, 'Letters, numbers and underscores — this is what the log calls it.'),
      field('Trigger phrases', triggers, 'Separated by commas. Whole words, not letters inside one.'),
      field('First line', line, '{name} is filled in with whoever asked.'),
    ]),
    bar([create]),
    say,
  ])]);
}

function intentsSection() {
  const one = section('Intents', null, { count: DATA.intents.length, open: true });
  one.body.append(previewWas('Replaces Intents (every intent’s full editor, expanded) and New intent — the editor is in the drawer and New intent is the page’s action.'));
  const head = el('div', { class: 'grid-row head', style: INTENT_GRID }, [
    el('span', { text: 'Name' }),
    el('span', { text: 'Kind' }),
    el('span', { text: 'Answers' }),
    el('span', { text: 'Trigger phrases' }),
    el('span', { text: 'Lines' }),
    el('span', {}),
  ]);
  const grid = el('div', { class: 'grid-table', style: 'min-width: 760px;' }, [head, ...DATA.intents.map(intentRow)]);
  const scroll = el('div', { class: 'table-scroll' }, [grid]);
  one.body.append(
    searchOver(scroll, {
      label: 'Search the intents',
      placeholder: 'a name, a phrase or a word from a line',
      selector: '.grid-row:not(.head)',
      noun: 'intent(s)',
      empty: 'No intent matches what you typed.',
    }),
    scroll,
  );
  return one;
}

/** page-chat.js:491 trySection, verbatim, answering out of DATA. */
function trySection() {
  const say = notice();
  const box = el('input', {
    class: 'input',
    type: 'text',
    placeholder: 'hey, how many of us are here?',
    'aria-label': 'A message to test',
  });
  const answer = el('div', { class: 'chat-answer', hidden: true });

  const go = () => {
    const text = box.value.trim().toLowerCase();
    if (!text) {
      say.say('Write something first — that is the message being tested.', 'warn');
      answer.hidden = true;
      return;
    }
    const found = DATA.intents.find((intent) => intent.triggers.some((one) => text.includes(one)));
    wouldDo(say, 'POST /api/chat/try — ask the bot which intent this lands on; the answer below is worked out from the static rows instead');
    if (!found) {
      answer.replaceChildren(sayNothing('That intent has no line to answer with, so Black Bloc would fall back to '
        + 'the wording in its own code.'));
      answer.hidden = false;
      return;
    }
    answer.replaceChildren(
      el('div', { class: 'chipbar' }, [
        el('span', { class: 'chat-answer-label', text: 'It lands on' }),
        badge(found.name, KIND_TONE[found.kind] ?? null),
        badge(found.kind, 'ok'),
      ]),
      el('p', { class: 'chat-answer-line', text: found.lines[0].text }),
    );
    answer.hidden = false;
  };
  box.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter') return;
    event.preventDefault();
    go();
  });

  const one = section('Try it', TRY_NOTE, { open: true });
  one.body.append(
    previewWas('Replaces Try it, unchanged — it stays beside the intents it tests.'),
    card(null, [
      el('div', { class: 'formrow' }, [
        field('Message', box, 'The part after the @-mention. Enter runs it.'),
        bar([button('Try it', go, { tone: 'warn', small: false })]),
      ]),
      answer,
      say,
    ]),
  );
  return one;
}

/** page-chat.js:586 noteCard, verbatim, with Save and Remove turned into notes. */
function noteCard(row) {
  const say = notice();
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
    maxlength: '40',
    placeholder: 'optional',
    'aria-label': 'A word for what this note is about',
    disabled: !row.editable,
  });
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
      row.editable
        ? bar([
          button('Save', () => wouldDo(say, `PUT /api/chat/knowledge/${row.id} — save this note`), { tone: 'quiet' }),
          button('Remove', () => wouldDo(say, `DELETE /api/chat/knowledge/${row.id} — stop Black Bloc quoting it`), { tone: 'danger' }),
        ])
        : el('p', { class: 'say-nothing' }, [el('span', { class: 'say-nothing-text' }, boldParts(row.locked_why))]),
      say,
    ]),
  ]);
}

function knowledgeSection() {
  const say = notice();
  const rows = DATA.knowledge.sections;
  const one = section('Knowledge', KNOWLEDGE_NOTE, { count: rows.length });
  const list = el('div', { class: 'section-body' });
  for (const row of rows) list.append(noteCard(row));

  const title = el('input', { class: 'input', type: 'text', maxlength: String(TITLE_LIMIT), placeholder: 'Cookout hours' });
  const body = el('textarea', { class: 'input area', rows: '3', maxlength: String(BODY_LIMIT), placeholder: 'The grill goes on at six on a Saturday.' });
  const tag = el('input', { class: 'input', type: 'text', maxlength: '40', placeholder: 'cookout' });

  one.body.append(
    previewWas('Replaces Knowledge, unchanged.'),
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
      text: `${DATA.knowledge.counts.staff} written by staff, ${DATA.knowledge.counts.server} written by Black Bloc. `
        + DATA.knowledge.budget.word,
    }),
    el('div', { class: 'chatblock' }, [card('A new note', [
      el('div', { class: 'formrow' }, [
        field('Heading', title, `Up to ${TITLE_LIMIT} characters.`),
        field('About', tag, 'Optional, and only for finding it again.'),
      ]),
      field('What it says', body, `Up to ${BODY_LIMIT} characters. A note that will not fit in an answer is left out whole rather than cut short.`),
      bar([button('Write it down', () => wouldDo(say, 'POST /api/chat/knowledge — write the note down'), { tone: 'warn', small: false })]),
      say,
    ])]),
  );
  return one;
}

/** page-chat.js:779 tropeCard, verbatim, with both buttons turned into notes. */
function tropeCard(row, say) {
  const flip = button(row.enabled ? 'Take it out' : 'Put it back', () => {
    wouldDo(say, `PUT /api/chat/personality/${row.name} — take it out of the pool, or put it back`);
  }, { tone: 'quiet' });
  const pick = row.in_use || !row.enabled ? null : button('Be only this one', () => {
    wouldDo(say, `PUT /api/chat/personality — point the whole bot at ${row.label}`);
  }, { tone: 'quiet' });
  return el('div', { class: 'card trope', 'data-enabled': row.enabled ? 'true' : 'false' }, [
    el('div', { class: 'card-body' }, [
      el('div', { class: 'chipbar' }, [
        el('span', { class: 'chat-fixed', text: row.label }),
        row.in_use ? badge('the one in use', 'ok') : null,
        row.enabled ? null : badge('out of the pool', 'warn'),
      ].filter(Boolean)),
      el('p', { class: 'chat-answer-line', text: row.voice }),
      el('p', {
        class: 'section-note',
        text: row.updated_by
          ? `Last changed by ${row.updated_by.name}, ${when(row.updated_at)}.`
          : 'Never changed here — this is how it was ported.',
      }),
      bar([flip, pick].filter(Boolean)),
    ]),
  ]);
}

function personalitySection() {
  const say = notice();
  const payload = DATA.personality;
  const one = section('Personality', PERSONALITY_NOTE, { count: payload.counts.enabled });
  const pick = segment(
    [{ value: 'cookout', label: MODE_LABELS.cookout }, { value: 'pool', label: MODE_LABELS.pool }],
    payload.mode,
    { onChange: () => wouldDo(say, 'PUT /api/chat/personality — change the voice Black Bloc writes in') },
  );
  const list = el('div', { class: 'section-body' });
  for (const row of payload.tropes) list.append(tropeCard(row, say));

  one.body.append(
    previewWas('Replaces Personality, unchanged.'),
    card(null, [
      el('div', { class: 'formrow' }, [
        field('The voice', pick, 'A voice is tone and never truth — the same facts either way.'),
      ]),
      el('p', { class: 'chat-answer-line' }, boldParts(payload.mode_word)),
      say,
    ]),
    el('div', {}, [
      searchOver(list, {
        label: 'Search the voices',
        placeholder: 'a name or a word from one',
        selector: '.trope',
        noun: 'voice(s)',
        empty: 'No voice has those words in it.',
      }),
      list,
    ]),
    el('p', { class: 'section-note', text: `Ported from ${payload.ported_from}.` }),
  );
  return one;
}

/** page-chat.js:955 memoryCard, verbatim, with Forget turned into a note. */
function memoryCard(row, say) {
  const counts = `${row.notes} preference${row.notes === 1 ? '' : 's'} · `
    + `${row.threads} open topic${row.threads === 1 ? '' : 's'} · ${row.turns_seen} turn`
    + `${row.turns_seen === 1 ? '' : 's'} seen`;
  return card(null, [
    el('div', { class: 'req-head' }, [
      el('div', { class: 'req-headtext' }, [
        el('p', { class: 'req-what', text: row.member.name }),
        el('p', {
          class: 'section-note',
          text: `${counts}${row.updated_at ? ` · last changed ${when(row.updated_at)}` : ''}`,
        }),
      ]),
      el('div', { class: 'req-marks' }, [row.call_me ? badge(`goes by ${row.call_me}`, 'info') : null].filter(Boolean)),
    ]),
    bar([button('Forget', () => {
      wouldDo(say, `DELETE /api/chat/memory/${row.member.id} — clear every preference and open topic for ${row.member.name}`);
    }, { tone: 'danger' })]),
  ]);
}

function memorySection() {
  const say = notice();
  const payload = DATA.memory;
  const one = section('Memory', MEMORY_NOTE, { count: payload.profiles.length });
  one.body.append(
    previewWas('Replaces Memory — its eight settings keys moved into Settings, so this is the profile list and nothing else.'),
    card(null, [
      el('div', { class: 'chipbar' }, [
        badge(payload.on ? 'on' : 'off', payload.on ? 'ok' : null),
        badge(`${payload.total} profile(s)`, null),
        badge(`${payload.opted_out} opted out`, null),
        badge(`${payload.dm_notes} ${MEMORY_DM_MARK}`, null),
      ]),
      payload.message ? el('p', { class: 'section-note', text: payload.message }) : null,
      payload.staff_view === 'counts' ? el('p', { class: 'section-note', text: MEMORY_COUNTS_ONLY }) : null,
    ].filter(Boolean)),
    el('div', { class: 'chatblock' }, payload.profiles.map((row) => memoryCard(row, say))),
    say,
  );
  return one;
}

/** page-chat.js:889 spendSection, folded into Settings as a foldout. */
function spendFoldout() {
  const payload = DATA.spend;
  const live = payload.tiers.filter((row) => row.live).length;
  const share = Math.max(0, Math.min(1, Number(payload.month.share) || 0));
  return foldout('Spend & tiers', [
    el('p', { class: 'section-note', text: SPEND_NOTE }),
    card(null, [
      el('div', { class: 'chipbar' }, [
        el('a', {
          class: 'spend-figure',
          href: COSTS_CARD,
          title: COSTS_TITLE,
          text: `$${Number(payload.month.spent_usd).toFixed(2)}`,
        }),
        el('span', { class: 'chat-answer-label', text: `of $${Number(payload.month.cap_usd).toFixed(2)} this month` }),
      ]),
      el('div', {
        class: 'spend-meter',
        'data-capped': 'false',
        role: 'img',
        'aria-label': payload.month.word,
      }, [el('div', { class: 'spend-meter-fill', style: `width: ${(share * 100).toFixed(1)}%` })]),
      el('p', { class: 'section-note', text: payload.month.word }),
      el('p', { class: 'section-note', text: payload.today.word }),
    ]),
    el('div', { class: 'chatblock' }, [
      el('h4', { text: `Tiers (${live} of ${payload.tiers.length} answering)` }),
      el('div', { class: 'chatlines' }, payload.tiers.map((row) => el('div', {
        class: 'chatline',
        'data-enabled': row.live ? 'true' : 'false',
      }, [
        el('span', { class: 'chat-fixed', text: row.label }),
        badge(row.live ? TIER_LIVE_WORD : TIER_QUIET_WORD, row.live ? 'ok' : 'warn'),
        el('span', { class: 'tier-word' }, boldParts(row.word)),
      ]))),
      el('p', { class: 'section-note', text: `The last answer a model gave was ${when(payload.last_turn_at)}.` }),
    ]),
  ], { count: live });
}

function settingsSection() {
  const specs = DATA.settings.concat(DATA.memorySettings);
  const one = section('Settings', SETTINGS_NOTE, { count: specs.length });
  one.body.append(
    previewWas('Replaces Settings, Memory’s own eight keys, Spend & tiers and Logs — one settings surface, with the two read-only surfaces folded into it.'),
    staticSettings(specs),
    spendFoldout(),
    foldout('Logs', [
      el('p', { class: 'section-note', text: LOGS_NOTE }),
      logsTable(DATA.logs, 'Chat has not done anything yet.'),
    ], { count: DATA.logs.length }),
  );
  return one;
}

async function load() {
  const banner = previewBanner({
    today: 9,
    preview: 6,
    note: 'The intents list is a table with a search over it; its editor opens in the drawer.',
  });
  banner.setAttribute('data-span', 'full');

  const aside = document.getElementById('page-aside');
  if (aside) aside.replaceChildren(button('New intent', newIntentDrawer, { tone: 'warn', small: false }));

  document.getElementById('dash').replaceChildren(
    banner,
    intentsSection().node,
    trySection().node,
    knowledgeSection().node,
    personalitySection().node,
    memorySection().node,
    settingsSection().node,
  );
}

refresh = start({ tab: 'chat', load });
