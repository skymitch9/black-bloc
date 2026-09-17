import { api, listOf, send, settings, settingsNamespace } from './api.js';
import { start } from './app.js';
import { featureLabel, logsSection } from './logs.js';
import { guidesIndex } from './shell.js';
import {
  ago,
  ask,
  badge,
  bar,
  boldParts,
  button,
  card,
  el,
  field,
  notice,
  run,
  saveBar,
  sayAgain,
  keepSaying,
  sayNothing,
  section,
  sentenceFor,
  settingsPanel,
  table,
  textAction,
} from './ui.js';

const FACTS_MAX = 4;
const TITLE_MAX = 120;
const GOAL_MAX = 300;
const DO_MAX = 400;
const EXPECT_MAX = 600;
const SYMPTOM_MAX = 120;
const ANSWER_MAX = 400;
const CAPTION_MAX = 200;
const PICTURE_BYTES_MAX = 2 * 1024 * 1024;
const PICTURE_SIDE_MAX = 1600;
const FACTS_EVERY_MS = 60000;

const SETTING_KEYS = [
  'guides_mode',
  'guides_who_edits',
  'guides_help_links',
  'guides_show_facts',
  'guides_fault_files_request',
  'guides_log_level',
];

const SETTINGS_NOTE = 'Whether members see this page at all, who may edit a guide, whether ' +
  '/help links to one, whether a guide shows live values, and where Something’s off lands.';
const HUB_NOTE = 'One page per goal. Each one is the shortest set of presses that gets it done, ' +
  'with the picture of what you should be looking at.';
const NO_GUIDES = 'Nothing is published yet.';
const NO_MATCH = 'Nothing here matches those filters.';
const STALE_NOTE = 'A screenshot is marked stale when the feature it shows has changed since the ' +
  'picture was taken. The picture stays up until somebody replaces it.';
const MARK_ALL_NOTE = 'A deploy marks the shots of the features it changed. Nothing else can — ' +
  'a mode flip, a renamed channel or a rewritten message leave every picture looking current.';
const MARK_ALL_ASK = 'Every picture in the app is marked for re-shooting. No picture is deleted: ' +
  'each one stays up until somebody replaces it.';
const MARK_ALL_WHY = 'Optional. It goes on the log line, so the capture session knows what changed.';
const REASON_MAX = 200;

const FAULT_HEAD = 'If it did not work';
const NO_FAULTS = 'Nothing is written down for this one yet.';
const NO_STEPS = 'This guide has no steps yet.';
const NO_FACTS = 'This guide shows no live values.';
const FACTS_OFF = 'Live values are turned off for guides, so this one shows its steps only.';
const GUIDES_ARE_OFF = 'There is nothing to show here until a Lead turns guides back on.';

const TELL_A_LEAD = 'Something wrong here? Tell a Lead in the staff channel — filing a request ' +
  'from this page is turned off.';
const NEED_A_FAULT = 'Say what was wrong first — one line is enough.';
const FAULT_FILED = 'Filed. Staff see it with everything else people have asked for.';

const SAVE_FIRST = 'Save your changes first. A picture is uploaded straight away, and reloading ' +
  'the guide to show it would throw away what you have typed.';
const NEW_STEP_FIRST = 'Save the guide first. A picture is filed against a step, and this step ' +
  'does not exist at the bot yet.';
const NEED_A_TITLE = 'A guide needs a title and a goal. Fill both in and press Make it again.';
const PICTURE_TOO_BIG = 'That picture is {size} and Black Bloc keeps guide screenshots under ' +
  '2.0 MB. Nothing was uploaded — crop it, or save it again as a PNG at no more than 1600 ' +
  'pixels on its longest side.';
const PICTURE_TOO_WIDE = 'That picture is {side} pixels on its longest side and Black Bloc keeps ' +
  'guide screenshots under 1600. Nothing was uploaded — crop or export it smaller and send it ' +
  'again.';
const PICTURE_UNREADABLE = 'This browser could not read that file as a picture, so nothing was ' +
  'uploaded. Send a PNG, a JPEG or a WebP.';
const PICTURE_GONE = 'This picture did not load. The words above are the whole step; tell a Lead ' +
  'if it stays missing.';

const AUDIENCE_SAID = { member: 'For everyone', staff: 'For staff' };
const SOURCE_SAID = { capture: 'screenshot', mock: 'illustration' };
const WHERE_SAID = { discord: 'in Discord', website: 'on this site' };

const WHERE_CHIPS = [
  ['', 'Anywhere'],
  ['discord', 'In Discord'],
  ['site', 'On this site'],
];

const AUDIENCE_CHIPS = [
  ['', 'Everyone'],
  ['member', 'For members'],
  ['staff', 'For staff'],
];

const state = { audience: '', where: '', onlyOn: false, editing: false };

let refresh = () => {};
let factTimer = null;

/** layout.js balances #dash into two columns; a block marked full is never halved. */
function full(node) {
  if (node) node.setAttribute('data-span', 'full');
  return node;
}

function stopFacts() {
  if (factTimer === null) return;
  clearInterval(factTimer);
  factTimer = null;
}

function wantedSlug() {
  const found = /^#([a-z0-9-]{1,60})$/.exec(String(window.location.hash || ''));
  return found ? found[1] : null;
}

/** `hashchange` is what repaints, so this never refreshes twice for one press. */
function goTo(slug) {
  const wanted = slug ? `#${slug}` : '';
  if (String(window.location.hash || '') === wanted) {
    refresh();
    return;
  }
  if (slug) {
    window.location.hash = wanted;
    return;
  }
  window.history.replaceState(null, '', window.location.pathname);
  refresh();
}

function modePill(mode) {
  if (mode === null || mode === undefined || mode === '') return null;
  return el('span', { class: 'pill', 'data-mode': String(mode), text: String(mode) });
}

function audiencePill(row) {
  return badge(AUDIENCE_SAID[row.audience] || row.audience, row.audience === 'staff' ? 'info' : null);
}

function stalePill(count) {
  if (!count) return null;
  return badge(count === 1 ? '1 stale picture' : `${count} stale pictures`, 'warn');
}

function publishPill(row) {
  return row.published ? null : badge('not published', 'warn');
}

function whereOf(row) {
  return row.command ? 'discord' : 'site';
}

function metaOf(row) {
  const parts = [];
  if (row.command) parts.push(row.command);
  parts.push(`${row.step_count} step${row.step_count === 1 ? '' : 's'}`);
  return parts.join(' · ');
}

function hubCard(row, mayEdit) {
  return el('a', { class: 'guidecard', href: `#${row.slug}`, 'data-slug': row.slug }, [
    el('div', { class: 'guidecard-head' }, [
      el('h3', { class: 'guidecard-title', text: row.title }),
      el('div', { class: 'guidecard-marks' }, [
        audiencePill(row),
        modePill(row.feature_mode),
        publishPill(row),
        mayEdit ? stalePill(row.stale_count) : null,
      ]),
    ]),
    el('p', { class: 'guidecard-goal', text: row.goal }),
    el('p', { class: 'guidecard-meta', text: metaOf(row) }),
  ]);
}

/**
 * The hub's fixed strip. `/api/status` is staff-only, so `/api/guides` carries
 * the same facts and this is the one place that reads them.
 */
function rightNowStrip(payload) {
  const found = payload.right_now || {};
  const parts = [];
  parts.push(found.test_mode
    ? `Test mode is on — Black Bloc only speaks in #${found.test_channel || 'the test channel'} and in DMs`
    : 'Test mode is off — Black Bloc speaks in the server');
  parts.push(`${found.on ?? 0} features on`);
  parts.push(`${found.shadow ?? 0} in shadow`);
  parts.push(`${found.off ?? 0} off`);
  return full(el('div', { class: 'today' }, [
    el('div', { class: 'today-head', text: 'Right now' }),
    el('p', { class: 'today-line', text: parts.join(' · ') }),
  ]));
}

function chipRow(choices, current, onPick) {
  return el('div', { class: 'chipbar' }, choices.map(([key, label]) => el('button', {
    class: 'chip-filter',
    type: 'button',
    'aria-pressed': current === key ? 'true' : 'false',
    text: label,
    on: { click: () => onPick(key) },
  })));
}

function filters(payload) {
  const rows = [];
  if (payload.may_edit) {
    rows.push(chipRow(AUDIENCE_CHIPS, state.audience, (key) => {
      state.audience = key;
      refresh();
    }));
  }
  rows.push(chipRow(WHERE_CHIPS, state.where, (key) => {
    state.where = key;
    refresh();
  }));
  rows.push(el('div', { class: 'chipbar' }, [el('button', {
    class: 'chip-filter',
    type: 'button',
    'aria-pressed': state.onlyOn ? 'true' : 'false',
    text: 'Only what is on',
    on: {
      click: () => {
        state.onlyOn = !state.onlyOn;
        refresh();
      },
    },
  })]));
  return el('div', { class: 'guidefilters' }, rows);
}

function kept(rows) {
  return rows.filter((row) => {
    if (state.audience && row.audience !== state.audience) return false;
    if (state.where && whereOf(row) !== state.where) return false;
    if (state.onlyOn && String(row.feature_mode || '') === 'off') return false;
    return true;
  });
}

function newGuideCard(payload, say) {
  const title = el('input', { class: 'input', type: 'text', maxlength: String(TITLE_MAX), placeholder: 'what somebody is trying to do' });
  const goal = el('input', { class: 'input', type: 'text', maxlength: String(GOAL_MAX), placeholder: 'one sentence, in their words' });
  const audience = el('select', { class: 'input' }, [
    el('option', { value: 'member', text: 'For everyone' }),
    el('option', { value: 'staff', text: 'For staff' }),
  ]);
  const feature = featureSelect(payload, 'core');
  const command = el('input', { class: 'input', type: 'text', placeholder: '/golive — leave blank if there is none' });

  const make = button('Make it', async () => {
    if (!title.value.trim() || !goal.value.trim()) {
      say.say(NEED_A_TITLE, 'warn');
      return;
    }
    const done = await run(
      say,
      () => send('/api/guides', 'POST', {
        title: title.value.trim(),
        goal: goal.value.trim(),
        audience: audience.value,
        feature: feature.value,
        command: command.value.trim(),
      }),
      (found) => found?.message || 'Made.',
    );
    if (!done.ok) return;
    state.editing = true;
    keepSaying('guide', say);
    goTo(done.found.guide.slug);
  }, { tone: 'warn', small: false });

  return card(null, [
    el('div', { class: 'formrow' }, [
      field('Title', title, 'The goal as a person would say it.'),
      field('Goal', goal, 'One sentence. It is what the card on the hub reads.'),
    ]),
    el('div', { class: 'formrow' }, [
      field('Who it is for', audience, 'Staff guides are hidden from members and from /help.'),
      field('Which feature', feature, 'Decides the Where it happens link and which release makes its shots stale.'),
      field('Command', command, 'Only one published member guide per command.'),
    ]),
    bar([make]),
    say,
  ]);
}

function featureSelect(payload, current) {
  const rows = listOf(payload, 'features');
  const select = el('select', { class: 'input' });
  for (const one of rows) {
    const label = featureLabel(one.feature);
    select.append(el('option', {
      value: one.feature,
      text: label === one.feature ? label : `${label} (${one.feature})`,
      selected: one.feature === current || undefined,
    }));
  }
  if (!rows.some((one) => one.feature === current)) {
    select.append(el('option', { value: current, text: current, selected: true }));
  }
  return select;
}

async function loadHub(payload) {
  const say = sayAgain('guide', notice());
  const rows = listOf(payload, 'guides');
  const shown = kept(rows);
  const holder = document.getElementById('dash');
  const blocks = [];

  for (const line of payload.notes || []) blocks.push(notice(line, 'warn'));
  blocks.push(rightNowStrip(payload));
  blocks.push(full(say));

  const list = section('Guides', HUB_NOTE, { count: rows.length || null, open: true });
  list.body.append(
    filters(payload),
    shown.length === 0
      ? sayNothing(
        rows.length === 0 ? NO_GUIDES : NO_MATCH,
        rows.length === 0 ? null : textAction('Clear the filters', () => {
          state.audience = '';
          state.where = '';
          state.onlyOn = false;
          refresh();
        }),
      )
      : el('div', { class: 'guidegrid' }, shown.map((one) => hubCard(one, payload.may_edit))),
  );
  blocks.push(full(list.node));

  if (payload.may_edit) {
    const stale = section('Screenshots to re-shoot', STALE_NOTE, { count: payload.stale || null });
    stale.body.append(await staleList(), markAllCard());
    blocks.push(stale.node);
    const made = section('New guide', null, { count: null });
    made.body.append(newGuideCard(payload, notice()));
    blocks.push(made.node);

    const specs = settingsNamespace(await settings(true), 'guides')
      .filter((spec) => SETTING_KEYS.includes(spec.key));
    const box = section('Settings', SETTINGS_NOTE, { count: specs.length || null });
    box.body.append(await settingsPanel(specs, {
      where: 'Settings',
      empty: 'The bot registers no guide settings yet.',
    }));
    blocks.push(box.node);
    blocks.push(await logsSection('guides'));
  }

  holder.replaceChildren(...blocks);
}

async function staleList() {
  let payload = null;
  try {
    payload = await api('/api/guides/stale');
  } catch (error) {
    const said = sentenceFor(error);
    return el('p', { class: 'notice', 'data-tone': said.tone, text: said.text });
  }
  const rows = listOf(payload, 'shots');
  return table(
    [
      { key: 'title', label: 'Guide', cell: (row) => el('a', { class: 'celllink', href: `#${row.slug}`, text: row.title }) },
      { key: 'caption', label: 'Picture' },
      { key: 'shot_release', label: 'Shot at' },
      {
        key: 'stale_since',
        label: 'Marked stale',
        cell: (row) => {
          const when = ago(row.stale_since);
          return el('span', { title: when.title, text: when.text });
        },
      },
    ],
    rows,
    { empty: 'Nothing needs re-shooting.' },
  );
}

function markAllCard() {
  const say = notice();
  const reason = el('input', {
    class: 'input',
    type: 'text',
    maxlength: String(REASON_MAX),
    placeholder: 'shadow mode is off and the channel was renamed',
  });
  const press = button('Mark every screenshot stale…', async () => {
    const yes = await ask({
      title: 'Mark every screenshot stale?',
      body: [MARK_ALL_ASK, field('Why', reason, MARK_ALL_WHY)],
      confirmLabel: 'Mark them all',
      tone: 'warn',
    });
    if (!yes) return;
    const done = await run(
      say,
      () => send('/api/guides/stale/all', 'POST', { reason: reason.value.trim() }),
      (found) => found?.message || 'Marked.',
    );
    if (!done.ok) return;
    keepSaying('guide', say);
    refresh();
  }, { tone: 'warn', small: false });

  return card(null, [el('p', { class: 'muted', text: MARK_ALL_NOTE }), bar([press]), say]);
}

/* ---- one guide, read ------------------------------------------------------ */

function breadcrumb() {
  return el('p', { class: 'guidecrumb' }, [
    textAction('Guides', () => goTo(null)),
    el('span', { class: 'muted', text: ' › ' }),
  ]);
}

function copyChip(command, say) {
  return button(`Copy ${command}`, async () => {
    try {
      await navigator.clipboard.writeText(command);
      say.say(`${command} is on your clipboard. Paste it into any channel.`, 'ok');
    } catch (e) {
      say.say(`This browser would not let the page copy for you. Type ${command} into any channel instead.`, 'warn');
    }
  }, { tone: 'warn', small: false });
}

function captionOf(picture) {
  const parts = [`${SOURCE_SAID[picture.source] || picture.source} ${WHERE_SAID[picture.surface] || ''}`.trim()];
  if (picture.shot_release) parts.push(picture.shot_release);
  if (picture.caption) parts.push(picture.caption);
  return parts.join(' · ');
}

/** The alt is the step's own words; the bold markers are typography, not speech. */
function plain(text) {
  return String(text ?? '').split('**').join('');
}

function pictureBlock(picture, alt) {
  if (!picture) return null;
  const said = plain(alt || picture.alt || '');
  const shot = el('img', {
    class: 'step-img',
    src: picture.url,
    alt: said,
    loading: 'lazy',
    width: picture.width || undefined,
    height: picture.height || undefined,
    on: { error: () => shot.replaceWith(el('p', { class: 'step-gone', text: PICTURE_GONE })) },
  });
  return el('figure', { class: 'step-shot' }, [
    shot,
    el('figcaption', { class: 'step-caption' }, [
      el('span', { text: captionOf(picture) }),
      picture.stale
        ? badge(`stale — the feature changed since ${picture.shot_release || 'this shot'}`, 'warn')
        : null,
    ]),
  ]);
}

function warningsBlock(step, mayEdit) {
  if (!mayEdit || !(step.warnings || []).length) return null;
  return el('div', { class: 'step-warns' }, step.warnings.map((line) =>
    el('p', { class: 'step-warn' }, boldParts(line))));
}

function stepBlock(step, mayEdit) {
  return el('li', { class: 'step', id: `s-${step.position}` }, [
    el('span', { class: 'step-n', text: String(step.position) }),
    el('div', { class: 'step-body' }, [
      el('p', { class: 'step-do' }, boldParts(step.do_text)),
      pictureBlock(step.media, step.do_text),
      step.expect_text
        ? el('p', { class: 'step-expect' }, [
          el('span', { class: 'step-expect-label', text: 'Expect' }),
          el('span', {}, boldParts(step.expect_text)),
        ])
        : null,
      warningsBlock(step, mayEdit),
    ]),
  ]);
}

function factRow(fact) {
  return el('div', { class: 'factrow' }, [
    el('span', { class: 'fact-label', text: fact.label || fact.ref }),
    el('span', { class: 'fact-value', text: fact.value }),
    fact.help ? el('p', { class: 'fact-help', text: fact.help }) : null,
  ]);
}

function factsCard(payload) {
  const rows = payload.facts || [];
  const stamp = el('span', { class: 'fact-stamp' });
  const body = el('div', { class: 'facts' });

  const paint = (found) => {
    const lines = found.facts || [];
    body.replaceChildren(...(lines.length ? lines.map(factRow) : [sayNothing(FACTS_OFF)]));
    const when = ago(found.read_at);
    stamp.textContent = `updated ${when.text}`;
    stamp.title = when.title;
  };
  paint({ facts: rows, read_at: payload.read_at });

  stopFacts();
  factTimer = setInterval(async () => {
    if (!document.body.contains(body)) {
      stopFacts();
      return;
    }
    try {
      paint(await api(`/api/guides/${encodeURIComponent(payload.guide.slug)}`));
    } catch (e) {
      stamp.textContent = 'could not be read just now';
    }
  }, FACTS_EVERY_MS);

  return card('Right now', [body], { actions: [stamp] });
}

function faultsBlock(payload) {
  return table(
    [
      { key: 'symptom', label: 'If this happens', cell: (row) => el('span', {}, boldParts(row.symptom)) },
      { key: 'answer', label: 'Do this', cell: (row) => el('span', {}, boldParts(row.answer)) },
    ],
    payload.faults || [],
    { empty: NO_FAULTS, search: false },
  );
}

function settingsLink(ref, mayEdit) {
  if (!mayEdit) return el('span', { class: 'mono', text: ref });
  return el('a', { class: 'celllink mono', href: `/settings.html#${encodeURIComponent(ref)}`, text: ref });
}

function railBlock(title, children) {
  return el('div', { class: 'guiderail-block' }, [
    el('div', { class: 'today-head', text: title }),
    ...[].concat(children).filter(Boolean),
  ]);
}

function rail(payload, hub) {
  const guide = payload.guide;
  const related = listOf(hub, 'guides')
    .filter((one) => one.feature === guide.feature && one.slug !== guide.slug);
  const chosen = payload.chosen_facts || [];
  const when = ago(guide.updated_at);

  return el('aside', { class: 'guiderail' }, [
    railBlock('Who it is for', [
      el('p', { class: 'guiderail-line', text: AUDIENCE_SAID[guide.audience] || guide.audience }),
    ]),
    railBlock('Where it happens', [
      el('p', { class: 'guiderail-line' }, [
        el('span', { text: `${featureLabel(guide.feature)} ` }),
        modePill(guide.feature_mode),
      ]),
      guide.feature_page
        ? el('p', { class: 'guiderail-line' }, [
          el('a', { class: 'celllink', href: `/${guide.feature_page}`, text: 'Open its page' }),
        ])
        : null,
    ]),
    chosen.length
      ? railBlock('The values it reads', chosen.map((one) => el('p', { class: 'guiderail-line' }, [
        one.kind === 'setting'
          ? settingsLink(one.ref, payload.may_edit)
          : el('span', { class: 'mono', text: one.ref }),
      ])))
      : null,
    related.length
      ? railBlock('Guides for the same thing', related.map((one) =>
        el('p', { class: 'guiderail-line' }, [
          el('a', { class: 'celllink', href: `#${one.slug}`, text: one.title }),
        ])))
      : null,
    railBlock('About this page', [
      el('p', { class: 'guiderail-line', title: when.title, text: `Last edited ${when.text}${guide.updated_by_name ? ` by ${guide.updated_by_name}` : ''}.` }),
      el('p', { class: 'guiderail-line', text: guide.seeded ? 'Black Bloc ships this guide; staff may rewrite every word of it.' : 'Staff wrote this guide here.' }),
      el('p', { class: 'guiderail-line', text: 'Every word and picture on it is edited by staff on this page.' }),
    ]),
  ]);
}

/* ---- the two foot buttons (§C8) ------------------------------------------ */

function footButtons(payload) {
  const guide = payload.guide;
  const say = notice();
  const right = button('This guide was right', async () => {
    await run(
      say,
      () => send(`/api/guides/${encodeURIComponent(guide.slug)}/confirmed`, 'POST', {}),
      (found) => found?.message || 'Thank you.',
    );
  }, { tone: 'ok', small: false });

  if (!payload.fault_files_request) {
    return card(null, [bar([right]), el('p', { class: 'section-note', text: TELL_A_LEAD }), say]);
  }

  const wrong = button('Something’s off', async () => {
    const box = el('textarea', { class: 'input area', rows: '3', placeholder: 'what was wrong, and on which step' });
    const step = el('input', { class: 'input', type: 'number', min: '1', max: String(guide.step_count || 1), placeholder: 'which step' });
    const sure = await ask({
      title: `What is wrong with “${guide.title}”?`,
      body: [
        'This files a request under your name, exactly as the Requests page does, and staff answer it there.',
        field('Which step', step, 'Leave it blank if it is the whole guide.'),
        field('What was wrong', box, 'One or two lines. Staff read exactly this.'),
      ],
      confirmLabel: 'File it',
      tone: 'warn',
    });
    if (!sure) return;
    if (!box.value.trim()) {
      say.say(NEED_A_FAULT, 'warn');
      return;
    }
    const which = step.value.trim() ? `, step ${step.value.trim()}` : '';
    await run(
      say,
      () => send('/api/requests', 'POST', {
        what: `Guide “${guide.title}”${which}: ${box.value.trim()}`,
        why: guide.url,
      }),
      (found) => found?.message || FAULT_FILED,
    );
  }, { tone: 'quiet', small: false });

  return card(null, [bar([right, wrong]), say]);
}

/* ---- one guide, read mode ------------------------------------------------ */

function readGuide(payload, hub) {
  const guide = payload.guide;
  const say = sayAgain('guide', notice());
  const steps = payload.steps || [];

  const head = el('div', { class: 'guidehead' }, [
    breadcrumb(),
    el('h2', { class: 'guidetitle', text: guide.title }),
    el('p', { class: 'guidegoal', text: guide.goal }),
    el('div', { class: 'guidemarks' }, [
      audiencePill(guide),
      modePill(guide.feature_mode),
      publishPill(guide),
      payload.may_edit ? stalePill(guide.stale_count) : null,
    ]),
    guide.command ? bar([copyChip(guide.command, say)]) : null,
    say,
  ]);

  const main = el('div', { class: 'colstack' }, [
    (payload.chosen_facts || []).length ? factsCard(payload) : null,
    steps.length
      ? el('ol', { class: 'steps' }, steps.map((one) => stepBlock(one, payload.may_edit)))
      : sayNothing(NO_STEPS),
    card(FAULT_HEAD, [faultsBlock(payload)]),
    footButtons(payload),
  ]);

  return [full(head), full(el('div', { class: 'guidebody' }, [main, rail(payload, hub)]))];
}

/* ---- one guide, edit mode ------------------------------------------------ */

function draftOf(payload) {
  const guide = payload.guide;
  return {
    title: guide.title,
    goal: guide.goal,
    audience: guide.audience,
    feature: guide.feature,
    command: guide.command || '',
    sort: guide.sort,
    published: Boolean(guide.published),
    steps: (payload.steps || []).map((one) => ({
      id: one.id,
      do_text: one.do_text,
      expect_text: one.expect_text || '',
      media_id: one.media_id,
      media: one.media,
      seed_do: one.seed_do,
      seed_expect: one.seed_expect,
      can_restore: one.can_restore,
      warnings: one.warnings || [],
    })),
    faults: (payload.faults || []).map((one) => ({ symptom: one.symptom, answer: one.answer })),
    facts: (payload.chosen_facts || []).map((one) => ({ kind: one.kind, ref: one.ref })),
  };
}

function listChanges(now, was, keys) {
  let count = Math.abs(now.length - was.length);
  const pairs = Math.min(now.length, was.length);
  for (let at = 0; at < pairs; at += 1) {
    if (keys.some((key) => String(now[at][key] ?? '') !== String(was[at][key] ?? ''))) count += 1;
  }
  return count;
}

function changeCount(now, was) {
  let count = 0;
  for (const key of ['title', 'goal', 'audience', 'feature', 'command', 'published']) {
    if (String(now[key] ?? '') !== String(was[key] ?? '')) count += 1;
  }
  count += listChanges(now.steps, was.steps, ['do_text', 'expect_text']);
  count += listChanges(now.faults, was.faults, ['symptom', 'answer']);
  count += listChanges(now.facts, was.facts, ['kind', 'ref']);
  return count;
}

function move(rows, at, by) {
  const to = at + by;
  if (to < 0 || to >= rows.length) return;
  const [one] = rows.splice(at, 1);
  rows.splice(to, 0, one);
}

/** A data URL from a file input, with the same two numbers the API refuses by. */
function readPicture(file) {
  return new Promise((resolve) => {
    if (file.size > PICTURE_BYTES_MAX) {
      resolve({ ok: false, said: PICTURE_TOO_BIG.replace('{size}', `${Math.round(file.size / 1024)} KB`) });
      return;
    }
    const reader = new FileReader();
    reader.onerror = () => resolve({ ok: false, said: PICTURE_UNREADABLE });
    reader.onload = () => {
      const data = String(reader.result || '');
      const picture = new Image();
      picture.onerror = () => resolve({ ok: false, said: PICTURE_UNREADABLE });
      picture.onload = () => {
        const side = Math.max(picture.naturalWidth, picture.naturalHeight);
        if (side > PICTURE_SIDE_MAX) {
          resolve({ ok: false, said: PICTURE_TOO_WIDE.replace('{side}', String(side)) });
          return;
        }
        resolve({ ok: true, data, name: file.name });
      };
      picture.src = data;
    };
    reader.readAsDataURL(file);
  });
}

function pictureControls(slug, step, say, dirty) {
  const picker = el('input', { class: 'input', type: 'file', accept: 'image/png,image/jpeg,image/webp', hidden: true });
  const caption = el('input', { class: 'input', type: 'text', maxlength: String(CAPTION_MAX), placeholder: 'what the picture shows' });
  caption.value = step.media ? step.media.caption || '' : '';
  const source = el('select', { class: 'input' }, [
    el('option', { value: 'capture', text: 'a real screenshot' }),
    el('option', { value: 'mock', text: 'a drawn illustration' }),
  ]);
  const surface = el('select', { class: 'input' }, [
    el('option', { value: 'discord', text: 'Discord' }),
    el('option', { value: 'website', text: 'this site' }),
  ]);
  const release = el('input', { class: 'input', type: 'text', placeholder: 'v110' });
  if (step.media) {
    source.value = step.media.source;
    surface.value = step.media.surface;
    release.value = step.media.shot_release || '';
  }

  picker.addEventListener('change', async () => {
    const file = picker.files && picker.files[0];
    picker.value = '';
    if (!file) return;
    const found = await readPicture(file);
    if (!found.ok) {
      say.say(found.said, 'warn');
      return;
    }
    const done = await run(
      say,
      () => send(`/api/guides/${encodeURIComponent(slug)}/media`, 'POST', {
        filename: found.name,
        data: found.data,
        step_id: step.id,
        caption: caption.value.trim(),
        source: source.value,
        surface: surface.value,
        shot_release: release.value.trim(),
      }),
      (payload) => payload?.message || 'Replaced.',
    );
    if (!done.ok) return;
    keepSaying('guide', say);
    refresh();
  });

  const replace = button('Replace screenshot…', () => {
    if (!step.id) {
      say.say(NEW_STEP_FIRST, 'warn');
      return;
    }
    if (dirty()) {
      say.say(SAVE_FIRST, 'warn');
      return;
    }
    picker.click();
  }, { tone: 'quiet' });

  const remove = step.media
    ? button('Remove screenshot', async () => {
      if (dirty()) {
        say.say(SAVE_FIRST, 'warn');
        return;
      }
      const sure = await ask({
        title: 'Take this picture down?',
        body: ['The step keeps its words and shows no picture until a new one is uploaded.'],
        confirmLabel: 'Take it down',
      });
      if (!sure) return;
      step.media_id = null;
      step.media = null;
      say.say('The picture is off this step once you press Save Changes.', 'ok');
      refreshBar();
    }, { tone: 'quiet' })
    : null;

  return el('div', { class: 'step-shotedit' }, [
    el('div', { class: 'formrow' }, [
      field('Caption', caption, 'What the picture shows. It is written under it.'),
      field('What it is', source, 'A real capture, or a drawing of a screen a capture cannot reach.'),
      field('Where it is from', surface, null),
      field('Which release', release, 'The version it was shot at, so staleness can be told.'),
    ]),
    bar([replace, remove]),
    picker,
  ]);
}

let refreshBar = () => {};

function stepEditor(slug, draft, step, at, say, dirty, repaint) {
  const doBox = el('textarea', { class: 'input area', rows: '2', maxlength: String(DO_MAX) });
  doBox.value = step.do_text;
  doBox.addEventListener('input', () => {
    step.do_text = doBox.value;
    refreshBar();
  });
  const expectBox = el('textarea', { class: 'input area', rows: '2', maxlength: String(EXPECT_MAX) });
  expectBox.value = step.expect_text;
  expectBox.addEventListener('input', () => {
    step.expect_text = expectBox.value;
    refreshBar();
  });

  const restore = step.can_restore
    ? button('Put the original back', () => {
      step.do_text = step.seed_do || step.do_text;
      step.expect_text = step.seed_expect || '';
      doBox.value = step.do_text;
      expectBox.value = step.expect_text;
      refreshBar();
    }, { tone: 'quiet' })
    : null;

  return el('li', { class: 'step step-edit' }, [
    el('span', { class: 'step-n', text: String(at + 1) }),
    el('div', { class: 'step-body' }, [
      el('div', { class: 'formrow' }, [
        field('Do this', doBox, 'One press. Write the button in **bold**, spelled the way Discord spells it.'),
      ]),
      el('div', { class: 'formrow' }, [
        field('Expect', expectBox, 'What is on the screen afterwards. Leave it blank if there is nothing to see.'),
      ]),
      warningsBlock(step, true),
      pictureBlock(step.media, step.do_text),
      pictureControls(slug, step, say, dirty),
      bar([
        button('↑', () => {
          move(draft.steps, at, -1);
          repaint();
        }, { tone: 'quiet' }),
        button('↓', () => {
          move(draft.steps, at, 1);
          repaint();
        }, { tone: 'quiet' }),
        restore,
        button('×', () => {
          draft.steps.splice(at, 1);
          repaint();
        }, { tone: 'danger' }),
      ]),
    ]),
  ]);
}

function faultEditor(draft, fault, at, repaint) {
  const symptom = el('input', { class: 'input', type: 'text', maxlength: String(SYMPTOM_MAX) });
  symptom.value = fault.symptom;
  symptom.addEventListener('input', () => {
    fault.symptom = symptom.value;
    refreshBar();
  });
  const answer = el('textarea', { class: 'input area', rows: '2', maxlength: String(ANSWER_MAX) });
  answer.value = fault.answer;
  answer.addEventListener('input', () => {
    fault.answer = answer.value;
    refreshBar();
  });
  return el('div', { class: 'formrow faultrow' }, [
    field('If this happens', symptom, null),
    field('The answer', answer, null),
    bar([button('×', () => {
      draft.faults.splice(at, 1);
      repaint();
    }, { tone: 'danger' })]),
  ]);
}

function factEditor(hub, draft, fact, at, repaint) {
  const choices = (hub && hub.fact_choices) || { settings: [], probes: [] };
  const kind = el('select', { class: 'input' }, [
    el('option', { value: 'setting', text: 'a setting', selected: fact.kind === 'setting' || undefined }),
    el('option', { value: 'probe', text: 'something the bot counts', selected: fact.kind === 'probe' || undefined }),
  ]);
  const ref = el('select', { class: 'input' });
  const fill = () => {
    ref.replaceChildren();
    if (kind.value === 'setting') {
      for (const key of choices.settings) {
        ref.append(el('option', { value: key, text: key, selected: key === fact.ref || undefined }));
      }
    } else {
      for (const one of choices.probes) {
        ref.append(el('option', { value: one.ref, text: `${one.label} (${one.ref})`, selected: one.ref === fact.ref || undefined }));
      }
    }
    if (![...ref.options].some((option) => option.selected)) {
      ref.append(el('option', { value: fact.ref, text: fact.ref, selected: true }));
    }
    fact.ref = ref.value;
  };
  fill();
  kind.addEventListener('change', () => {
    fact.kind = kind.value;
    fill();
    refreshBar();
  });
  ref.addEventListener('change', () => {
    fact.ref = ref.value;
    refreshBar();
  });
  return el('div', { class: 'formrow factrow' }, [
    field('Kind', kind, null),
    field('Which one', ref, null),
    bar([button('×', () => {
      draft.facts.splice(at, 1);
      repaint();
    }, { tone: 'danger' })]),
  ]);
}

function editGuide(payload, hub) {
  const guide = payload.guide;
  const draft = draftOf(payload);
  const was = draftOf(payload);
  const say = sayAgain('guide', notice());
  const factsSay = notice();
  const body = el('div', { class: 'colstack' });
  const dock = saveBar(() => write(), () => discard(), { where: guide.title });
  const dirty = () => changeCount(draft, was) > 0;

  refreshBar = () => dock.say(changeCount(draft, was));

  const title = el('input', { class: 'input', type: 'text', maxlength: String(TITLE_MAX) });
  title.value = draft.title;
  title.addEventListener('input', () => {
    draft.title = title.value;
    refreshBar();
  });
  const goal = el('textarea', { class: 'input area', rows: '2', maxlength: String(GOAL_MAX) });
  goal.value = draft.goal;
  goal.addEventListener('input', () => {
    draft.goal = goal.value;
    refreshBar();
  });
  const audience = el('select', { class: 'input' }, [
    el('option', { value: 'member', text: 'For everyone', selected: draft.audience === 'member' || undefined }),
    el('option', { value: 'staff', text: 'For staff', selected: draft.audience === 'staff' || undefined }),
  ]);
  audience.addEventListener('change', () => {
    draft.audience = audience.value;
    refreshBar();
  });
  const feature = featureSelect(hub, draft.feature);
  feature.addEventListener('change', () => {
    draft.feature = feature.value;
    refreshBar();
  });
  const command = el('input', { class: 'input', type: 'text' });
  command.value = draft.command;
  command.addEventListener('input', () => {
    draft.command = command.value;
    refreshBar();
  });

  const publish = button(draft.published ? 'Unpublish' : 'Publish', () => {
    draft.published = !draft.published;
    publish.textContent = draft.published ? 'Unpublish' : 'Publish';
    refreshBar();
  }, { tone: draft.published ? 'quiet' : 'warn' });

  const reset = guide.seeded
    ? button('Reset the whole guide', async () => {
      const sure = await ask({
        title: 'Put every word back to the original?',
        body: ['Every step and every expect line goes back to the wording Black Bloc ships. Pictures are kept.'],
        confirmLabel: 'Put it all back',
      });
      if (!sure) return;
      const done = await run(
        say,
        () => send(`/api/guides/${encodeURIComponent(guide.slug)}/reset`, 'POST', {}),
        (found) => found?.message || 'Put back.',
      );
      if (!done.ok) return;
      keepSaying('guide', say);
      refresh();
    }, { tone: 'quiet' })
    : null;

  const remove = guide.seeded
    ? null
    : button('Delete this guide', async () => {
      const sure = await ask({
        title: `Delete “${guide.title}”?`,
        body: ['Every step, every answer and every picture goes with it. Nothing puts it back.'],
        confirmLabel: 'Delete it',
      });
      if (!sure) return;
      const done = await run(
        say,
        () => api(`/api/guides/${encodeURIComponent(guide.slug)}`, { method: 'DELETE' }),
        (found) => found?.message || 'Gone.',
      );
      if (!done.ok) return;
      keepSaying('guide', say);
      goTo(null);
    }, { tone: 'danger' });

  const paint = () => {
    body.replaceChildren(
      card('The guide itself', [
        el('div', { class: 'formrow' }, [
          field('Title', title, 'The goal as a person would say it.'),
          field('Who it is for', audience, 'A staff guide is hidden from members and from /help.'),
        ]),
        el('div', { class: 'formrow' }, [field('Goal', goal, 'One sentence — it is what the hub card reads.')]),
        el('div', { class: 'formrow' }, [
          field('Which feature', feature, 'Sets the Where it happens link and which release makes its shots stale.'),
          field('Command', command, 'Only one published member guide per command.'),
        ]),
        bar([publish, reset, remove]),
        say,
      ]),
      card('Steps', [
        draft.steps.length
          ? el('ol', { class: 'steps' }, draft.steps.map((one, at) =>
            stepEditor(guide.slug, draft, one, at, say, dirty, paint)))
          : sayNothing('No steps yet. Add the first one.'),
        bar([button('Add a step', () => {
          draft.steps.push({ id: null, do_text: '', expect_text: '', media_id: null, media: null, seed_do: null, seed_expect: null, can_restore: false, warnings: [] });
          paint();
        })]),
      ]),
      card(FAULT_HEAD, [
        ...draft.faults.map((one, at) => faultEditor(draft, one, at, paint)),
        draft.faults.length ? null : sayNothing(NO_FAULTS),
        bar([button('Add an answer', () => {
          draft.faults.push({ symptom: '', answer: '' });
          paint();
        })]),
      ]),
      card('Right now', [
        ...draft.facts.map((one, at) => factEditor(hub, draft, one, at, paint)),
        draft.facts.length ? null : sayNothing(NO_FACTS),
        bar([button('Add a value', () => {
          draft.facts.push({ kind: 'probe', ref: '' });
          paint();
        }, { disabled: draft.facts.length >= FACTS_MAX })]),
        factsSay,
      ]),
    );
    refreshBar();
  };

  const discard = () => {
    const fresh = draftOf(payload);
    Object.assign(draft, fresh);
    title.value = draft.title;
    goal.value = draft.goal;
    audience.value = draft.audience;
    feature.value = draft.feature;
    command.value = draft.command;
    publish.textContent = draft.published ? 'Unpublish' : 'Publish';
    factsSay.say('');
    paint();
  };

  const write = async () => {
    dock.say(0, 'Saving…', 'info');
    try {
      const found = await send(`/api/guides/${encodeURIComponent(guide.slug)}`, 'PUT', {
        title: draft.title.trim(),
        goal: draft.goal.trim(),
        audience: draft.audience,
        feature: draft.feature,
        command: draft.command.trim(),
        sort: draft.sort,
        published: draft.published,
        steps: draft.steps.map((one) => ({
          id: one.id,
          do_text: one.do_text.trim(),
          expect_text: one.expect_text.trim(),
          media_id: one.media_id,
        })),
        faults: draft.faults.map((one) => ({ symptom: one.symptom.trim(), answer: one.answer.trim() })),
        facts: draft.facts.map((one) => ({ kind: one.kind, ref: one.ref })),
      });
      say.say(found?.message || 'Saved.', 'ok');
      keepSaying('guide', say);
      refresh();
    } catch (error) {
      const said = sentenceFor(error);
      dock.say(0, 'Nothing was saved — the sentence is beside the part that refused.', 'danger');
      if (error.code === 'bad_fact' || error.code === 'too_many_facts') factsSay.say(said.text, said.tone);
      else say.say(said.text, said.tone);
    }
  };

  paint();

  const head = el('div', { class: 'guidehead' }, [
    breadcrumb(),
    el('h2', { class: 'guidetitle', text: guide.title }),
    el('div', { class: 'guidemarks' }, [
      badge('editing', 'info'),
      audiencePill(draft),
      publishPill(draft),
    ]),
  ]);

  return [full(head), full(body)];
}

/* ---- the page ------------------------------------------------------------ */

function editSwitch(payload) {
  const aside = document.getElementById('page-aside');
  if (!aside) return;
  if (!payload || !payload.may_edit) {
    aside.replaceChildren();
    return;
  }
  aside.replaceChildren(button(state.editing ? 'Stop editing' : 'Edit this guide', () => {
    state.editing = !state.editing;
    refresh();
  }, { tone: state.editing ? 'quiet' : 'warn', small: false }));
}

async function loadGuide(slug, hub) {
  const holder = document.getElementById('dash');
  let payload = null;
  try {
    payload = await api(`/api/guides/${encodeURIComponent(slug)}`);
  } catch (error) {
    const said = sentenceFor(error);
    editSwitch(null);
    holder.replaceChildren(
      breadcrumb(),
      el('p', { class: 'notice', 'data-tone': said.tone, text: said.text }),
      sayNothing('Pick a guide from the list.', textAction('Back to all the guides', () => goTo(null))),
    );
    return;
  }
  editSwitch(payload);
  const blocks = [];
  for (const line of payload.notes || []) blocks.push(notice(line, 'warn'));
  blocks.push(...(state.editing && payload.may_edit ? editGuide(payload, hub) : readGuide(payload, hub)));
  holder.replaceChildren(...blocks);
}

async function load() {
  stopFacts();
  const found = await guidesIndex();
  if (!found.ok) {
    if (found.error.code !== 'guides_off') throw found.error;
    editSwitch(null);
    document.getElementById('dash').replaceChildren(
      notice(found.error.message, 'warn'),
      sayNothing(GUIDES_ARE_OFF),
    );
    return undefined;
  }
  const hub = found.payload;
  const slug = wantedSlug();
  if (!slug) {
    state.editing = false;
    editSwitch(null);
    return loadHub(hub);
  }
  return loadGuide(slug, hub);
}

window.addEventListener('hashchange', () => {
  state.editing = false;
  refresh();
});

refresh = start({ tab: 'guides', load });
