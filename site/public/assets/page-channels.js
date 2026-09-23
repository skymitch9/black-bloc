import { api, send, settings, settingsNamespace } from './api.js';
import { start } from './app.js';
import { channelLabel } from './labels.js';
import {
  badge,
  button,
  card,
  el,
  foldout,
  notice,
  run,
  sayNothing,
  section,
  segment,
  settingsPanel,
  when,
} from './ui.js';

const WORD_KEYS = [
  'chat_channel_note_saved',
  'chat_channel_draft_used',
  'chat_channel_draft_none',
  'chat_channel_draft_reset',
  'chat_channel_draft_missing',
  'chat_channel_note_cleared',
  'chat_channel_note_nothing',
  'chat_channel_note_too_long',
  'chat_channel_note_no_channel',
  'chat_channel_notes_button',
  'chat_channel_notes_title',
  'chat_channel_notes_intro',
  'chat_channel_notes_placeholder',
  'chat_channel_note_modal',
  'chat_channel_note_label',
  'chat_channel_reach_shown',
  'chat_channel_reach_hidden',
  'chat_channel_reach_cleared',
  'chat_channel_reach_nothing',
  'chat_channel_reach_ignored',
];

const REVIEW_NOTE = 'Each channel came with a one-sentence description drafted from its name. ' +
  'Use it as it is, change the words and save yours, or decide the channel needs no note. ' +
  'Black Bloc reads only what is used or saved — a draft nobody has decided is never read.';
const SEES_NOTE = 'The exact channel list the conversation models are handed with every answer. ' +
  'It is rebuilt each time, so a decision here reaches the very next answer.';
const SEES_TRIMMED = 'To stay inside the budget, the longest descriptions were left off these ' +
  'channels: {names}. Shorten a note to bring them back.';
const NO_CHANNELS = 'Black Bloc could not list the server\'s text channels, so there is nothing ' +
  'to review yet.';
const NOTHING_MATCHES = 'No channel matches this filter.';
const ALL_DONE = 'Every drafted channel has been reviewed. Pick All or Reviewed to look again.';
const NO_TOPIC = 'no topic in Discord';
const TOPIC_LABEL = 'Discord topic: ';
const DRAFT_LABEL = 'Drafted: ';
const PROGRESS = 'Reviewed {reviewed} of {total} · {left} drafts left';
const NO_DRAFTS = 'No channel has a drafted description.';
const UNDRAFTED = 'made after the catalog — no draft';
const WORDS_TITLE = 'The words Black Bloc says about channel notes';
const NO_WORDS = 'The bot registers no channel-note words, so there is nothing to change here.';
const HIDDEN_WORDS = {
  ignored_category: 'left out — in an ignored category',
  archive: 'left out — archive',
  not_visible: 'left out — members cannot see it',
  hidden_by_staff: 'left out by staff',
};
const SEEN_WORD = 'told about it';
const ROLE_WORD = 'told about it — members reach it through the {role} role';
const STAFF_SHOWN_WORD = 'shown by staff';
const ROLE_VIA = 'role:';
const TELL_ANYWAY = 'Tell the bot anyway';
const HIDE_IT = 'Hide from the bot';
const BACK_TO_RULE = 'Back to the rule';
const IGNORED_HINT = 'Its category is on chat_ignore_categories, or it is the ticket category — ' +
  'change that list on the Settings page to bring it in.';
const TOLD = 'Told about {shown} of {total} channel(s)';
const STATUS_WORDS = { draft: 'Draft', used: 'Used', rewritten: 'Rewritten', none: 'No note' };
const STATUS_TONES = { draft: 'warn', used: 'ok', rewritten: 'ok', none: null };
const FILTERS = [
  { value: 'left', label: 'Drafts left' },
  { value: 'reviewed', label: 'Reviewed' },
  { value: 'all', label: 'All' },
];
const ANY_CATEGORY = '';
const NO_CATEGORY = '(no category)';

const view = {
  rows: [], review: null, limit: 240, filter: 'left', category: ANY_CATEGORY, query: '', kept: null, apply: null, choice: null,
};

const clean = (text) => String(text || '').replace(/\s+/g, ' ').trim();

function categoriesOf(rows) {
  return rows
    .filter((one) => one.category_id)
    .map((one) => ({ id: one.category_id, name: one.category, type: 'category' }));
}

function wanted(row) {
  if (view.kept === row.id) return true;
  if (view.filter === 'left' && row.status !== 'draft') return false;
  if (view.filter === 'reviewed' && !(row.status && row.status !== 'draft')) return false;
  if (view.category && (row.category || NO_CATEGORY) !== view.category) return false;
  if (!view.query) return true;
  const said = `${row.name} ${row.category || ''} ${row.topic || ''} ${row.note || ''} ${row.draft || ''}`;
  return said.toLowerCase().includes(view.query);
}

function statusChip(row) {
  if (!row.status) return badge(UNDRAFTED, null);
  const parts = [STATUS_WORDS[row.status] || row.status];
  if (row.status !== 'draft') {
    if (row.decided_by?.name) parts.push(`by ${row.decided_by.name}`);
    if (row.decided_at) parts.push(when(row.decided_at));
  }
  return badge(parts.join(' · '), STATUS_TONES[row.status] ?? null);
}

function reviewCard(row, answer) {
  const drafted = row.draft !== null && row.draft !== undefined;
  const box = el('textarea', {
    class: 'input area review-box',
    rows: '2',
    maxlength: String(view.limit),
    placeholder: 'what people talk about here, in one sentence',
    'aria-label': `What #${row.name} is for`,
  });
  box.value = row.note || (drafted ? row.draft : '');
  const counter = el('span', { class: 'review-count' });
  const say = notice();
  const path = `/api/chat/channels/${encodeURIComponent(row.id)}`;
  const move = (label, work, tone = 'quiet') => button(label, async () => {
    const done = await run(say, work, (found) => found?.message || 'Done.');
    if (done.ok && done.found?.channel) answer(done.found, say);
  }, { tone });

  const use = move('Use this', () => send(`${path}/use`, 'POST', {}), null);
  const save = move('Save my wording', () => send(path, 'PUT', { note: box.value.trim() }), null);
  const none = move('No note', () => send(`${path}/none`, 'POST', {}));
  const reset = move('Reset to the draft', () => send(`${path}/reset`, 'POST', {}));
  const clear = move('Clear', () => api(path, { method: 'DELETE' }));

  const paint = () => {
    const now = clean(box.value);
    const length = now.length;
    counter.textContent = `${length} / ${view.limit}`;
    counter.setAttribute('data-over', length > view.limit ? 'true' : 'false');
    const same = now === clean(row.note);
    if (drafted) {
      use.hidden = now !== clean(row.draft) || (row.status === 'used' && same);
      save.hidden = now === clean(row.draft) || !now || same;
      none.hidden = row.status === 'none';
      reset.hidden = row.status === 'draft';
      clear.hidden = true;
    } else {
      use.hidden = true;
      none.hidden = true;
      reset.hidden = true;
      save.hidden = !now || same;
      clear.hidden = !row.note;
    }
  };
  box.addEventListener('input', paint);
  paint();

  return el('div', { class: 'review-card' }, [
    drafted && row.note && clean(row.note) !== clean(row.draft)
      ? el('p', { class: 'section-note review-draft', text: `${DRAFT_LABEL}${row.draft}` })
      : null,
    box,
    el('div', { class: 'review-bar' }, [use, save, none, reset, clear, el('span', { class: 'review-gap' }), counter]),
    say,
  ]);
}

function reachOf(row) {
  const reach = row.reach || {};
  return {
    visible: reach.visible ?? Boolean(row.shown),
    via: reach.via ?? null,
    override: reach.override ?? null,
  };
}

function reachChip(row) {
  const reach = reachOf(row);
  if (!reach.visible) return badge(HIDDEN_WORDS[row.hidden_because] || 'left out', 'warn');
  if (reach.via === 'override') return badge(STAFF_SHOWN_WORD, 'ok');
  if (String(reach.via || '').startsWith(ROLE_VIA)) {
    return badge(ROLE_WORD.replace('{role}', String(reach.via).slice(ROLE_VIA.length)), 'ok');
  }
  return badge(SEEN_WORD, 'ok');
}

function reachBar(row, answer) {
  if (row.hidden_because === 'ignored_category') {
    return el('p', { class: 'section-note channel-reach-note', text: IGNORED_HINT });
  }
  const reach = reachOf(row);
  const say = notice();
  say.setAttribute('data-slot', 'reach');
  const path = `/api/chat/channels/${encodeURIComponent(row.id)}/reach`;
  const move = (label, work) => button(label, async () => {
    const done = await run(say, work, (found) => found?.message || 'Done.');
    if (done.ok && done.found?.channel) answer(done.found, say);
  }, { tone: 'quiet' });
  let control;
  if (reach.override !== null) control = move(BACK_TO_RULE, () => api(path, { method: 'DELETE' }));
  else if (reach.visible) control = move(HIDE_IT, () => send(path, 'PUT', { shown: false }));
  else control = move(TELL_ANYWAY, () => send(path, 'PUT', { shown: true }));
  return el('div', { class: 'channel-reach' }, [
    el('div', { class: 'review-bar' }, [control]),
    say,
  ]);
}

function channelRow(row, answer) {
  const label = channelLabel({ name: row.name, type: 'text', category_id: row.category_id }, categoriesOf(view.rows));
  return el('div', {
    class: 'card channel-row',
    id: `channel-${row.id}`,
    'data-id': row.id,
    'data-shown': row.shown ? 'true' : 'false',
    'data-status': row.status || 'undrafted',
  }, [
    el('div', { class: 'card-body' }, [
      el('div', { class: 'chipbar' }, [
        el('span', { class: 'chat-fixed channel-name', text: label }),
        statusChip(row),
        reachChip(row),
      ]),
      reachBar(row, answer),
      el('p', {
        class: 'section-note channel-topic',
        text: row.topic ? `${TOPIC_LABEL}${row.topic}` : NO_TOPIC,
      }),
      reviewCard(row, answer),
    ]),
  ]);
}

function seesCard(payload) {
  const budget = payload?.budget || {};
  const used = Number(budget.used) || 0;
  const cap = Number(budget.cap) || 0;
  const share = cap > 0 ? Math.max(0, Math.min(1, used / cap)) : 0;
  const trimmed = Array.isArray(budget.trimmed) ? budget.trimmed : [];
  return card(null, [
    el('p', { class: 'section-note', text: SEES_NOTE }),
    el('div', { class: 'chipbar' }, [
      el('span', { class: 'chat-answer-label', text: `${used} of ${cap} bytes used` }),
      trimmed.length ? badge(`${trimmed.length} description(s) left off`, 'warn') : null,
    ]),
    el('div', {
      class: 'spend-meter',
      'data-capped': trimmed.length ? 'true' : 'false',
      role: 'img',
      'aria-label': `${used} of ${cap} bytes`,
    }, [el('div', { class: 'spend-meter-fill', style: `width: ${(share * 100).toFixed(1)}%` })]),
    el('pre', { class: 'directory-block', text: payload?.directory || '' }),
    trimmed.length
      ? el('p', { class: 'section-note', text: SEES_TRIMMED.replace('{names}', trimmed.map((name) => `#${name}`).join(', ')) })
      : null,
  ]);
}

function progressText(review) {
  if (!review || !review.total) return NO_DRAFTS;
  return PROGRESS
    .replace('{reviewed}', String(review.reviewed))
    .replace('{total}', String(review.total))
    .replace('{left}', String(review.drafts_left));
}

function toldText() {
  const shown = view.rows.filter((row) => reachOf(row).visible).length;
  return TOLD.replace('{shown}', String(shown)).replace('{total}', String(view.rows.length));
}

function paintProgress(review) {
  const aside = document.getElementById('page-aside');
  if (!aside) return;
  const next = review && review.drafts_left > 0
    ? button('Next draft', () => {
      const found = view.rows.find((row) => row.status === 'draft');
      const node = found && document.getElementById(`channel-${found.id}`);
      if (!node) return;
      if (node.hidden && view.apply) {
        view.filter = 'left';
        view.kept = found.id;
        if (view.choice) view.choice.setValue(view.filter);
        view.apply();
      }
      node.scrollIntoView({ behavior: 'auto', block: 'center' });
      const box = node.querySelector('textarea');
      if (box) box.focus({ preventScroll: true });
    }, { tone: null, small: false })
    : null;
  aside.replaceChildren(el('div', { class: 'review-progress' }, [
    el('span', { class: 'review-progress-text', id: 'review-progress', text: progressText(review) }),
    el('span', { class: 'review-progress-text', id: 'review-told', text: toldText() }),
    next,
  ]));
}

function filterBar(rows, apply) {
  const choice = segment(FILTERS, view.filter, {
    onChange: () => {
      view.filter = choice.readValue();
      view.kept = null;
      apply();
    },
  });
  const names = [...new Set(rows.map((row) => row.category || NO_CATEGORY))];
  const category = el('select', { class: 'input review-category', 'aria-label': 'Only this category' }, [
    el('option', { value: ANY_CATEGORY, text: 'Every category' }),
    ...names.map((name) => el('option', { value: name, text: name })),
  ]);
  category.value = view.category;
  category.addEventListener('change', () => {
    view.category = category.value;
    view.kept = null;
    apply();
  });
  const search = el('input', {
    class: 'input review-search',
    type: 'search',
    placeholder: 'a channel name, or a word from a note',
    'aria-label': 'Search the channels',
  });
  search.value = view.query;
  search.addEventListener('input', () => {
    view.query = search.value.trim().toLowerCase();
    view.kept = null;
    apply();
  });
  view.choice = choice;
  return el('div', { class: 'review-filter' }, [choice, category, search]);
}

async function wordsFold() {
  let specs = [];
  try {
    const found = settingsNamespace(await settings(true), 'chat');
    const byKey = new Map(found.map((spec) => [spec.key, spec]));
    specs = WORD_KEYS.map((key) => byKey.get(key)).filter(Boolean);
  } catch (error) {
    specs = [];
  }
  const words = section('Words', null, { id: 'words', count: specs.length || null });
  words.body.append(foldout(WORDS_TITLE, [
    await settingsPanel(specs, { where: 'Channels', empty: NO_WORDS }),
  ], { count: specs.length || null }));
  return words.node;
}

async function load() {
  const payload = await api('/api/chat/channels');
  view.rows = Array.isArray(payload?.channels) ? payload.channels : [];
  view.limit = Number(payload?.note_chars) || 240;
  view.kept = null;
  if (payload?.review && payload.review.drafts_left === 0 && view.filter === 'left') view.filter = 'all';
  view.review = payload?.review || null;
  paintProgress(payload?.review);

  const review = section('Review', REVIEW_NOTE, { id: 'review', open: true, count: view.rows.length || null });
  const list = el('div', { class: 'review-list' });
  const empty = sayNothing(NOTHING_MATCHES);
  const shown = el('p', { class: 'section-note review-shown' });
  const sees = section('What the bot sees', null, { id: 'sees', open: true });
  let seesNode = seesCard(payload);
  sees.body.append(seesNode);

  const apply = () => {
    let count = 0;
    for (const node of list.children) {
      const row = view.rows.find((one) => one.id === node.getAttribute('data-id'));
      node.hidden = !row || !wanted(row);
      if (!node.hidden) count += 1;
    }
    empty.hidden = count > 0;
    const allDone = view.filter === 'left' && count === 0 && !view.query && !view.category;
    empty.textContent = allDone ? ALL_DONE : NOTHING_MATCHES;
    shown.textContent = `Showing ${count} of ${view.rows.length} channel(s).`;
  };

  const answer = (found, say) => {
    const fresh = found.channel;
    const at = view.rows.findIndex((one) => one.id === fresh.id);
    if (at >= 0) view.rows[at] = fresh;
    view.kept = fresh.id;
    const old = document.getElementById(`channel-${fresh.id}`);
    const made = channelRow(fresh, answer);
    const slot = say && say.getAttribute('data-slot');
    const kept = made.querySelector(slot ? `.notice[data-slot="${slot}"]` : '.review-card .notice');
    if (kept && kept.say && say) kept.say(say.said, say.getAttribute('data-tone') || 'ok');
    if (old) old.replaceWith(made);
    const next = seesCard({ ...found, directory: found.directory, budget: found.budget });
    seesNode.replaceWith(next);
    seesNode = next;
    if (found.review) view.review = found.review;
    paintProgress(view.review);
    apply();
  };

  view.apply = apply;
  for (const row of view.rows) list.append(channelRow(row, answer));

  if (view.rows.length === 0) {
    review.body.append(sayNothing(NO_CHANNELS));
  } else {
    review.body.append(filterBar(view.rows, apply), shown, empty, list);
    apply();
  }

  document.getElementById('dash').replaceChildren(review.node, sees.node, await wordsFold());
}

start({ tab: 'channels', load });
