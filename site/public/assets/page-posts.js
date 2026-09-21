import { api, refChannels, refMembers, refRoles, send, settings, settingsNamespace } from './api.js';
import { start } from './app.js';
import { htmlToDiscordMarkdown } from './clipmd.js';
import { logsSection } from './logs.js';
import { VIEWING, useItQuestion, versionsFoldout } from './postversions.js';
import {
  ago,
  ask,
  badge,
  bar,
  boldParts,
  button,
  card,
  channelSelect,
  closeDrawer,
  discordMock,
  el,
  field,
  foldout,
  icon,
  keepSaying,
  modeChip,
  notice,
  openDrawer,
  readSelect,
  run,
  sayAgain,
  sayNothing,
  searchField,
  section,
  sentenceFor,
  settingsPanel,
} from './ui.js';

const MODE_KEY = 'posts_mode';
const SETTING_KEYS = [MODE_KEY, 'posts_panel_minutes', 'posts_log_level'];
const SETTINGS_NOTE = 'Whether staff may post at all, how long the /posts panel stays live, and '
  + 'how much of it is repeated into the Discord log.';
const MACHINERY_NOTE = 'The reference half of the page: three keys, and everything posts has '
  + 'done. Both are shut until you want them.';
const LIST_NOTE = 'One message per post. Black Bloc sends it once and edits that same message '
  + 'every time after — it never posts a second copy.';
const NOTHING_YET = 'There are no posts yet.';
const NO_CHANNEL = 'no channel yet';
const AMBER_AT = 0.9;
const POST_FEATURE = 'post';
const NEED_A_TITLE = 'A post needs a title. Type one and press Create the post again.';
const POSTED_HERE = 'Posted in {where}.';
const POSTED_IN_SHADOW = 'The shadow copy is in {where}.';
const NOT_POSTED_ANYWHERE = 'Not posted anywhere yet.';
const PINNED_TOO = ' It is pinned.';
const NOT_PINNED = ' It is not pinned.';
const WILL_POST = 'Post it sends this to {where} as {style} and {pin}.';
const WILL_UPDATE = 'Update the post edits the message already in {where}, as {style} and {pin}.';
const NEEDS_A_CHANNEL = 'Pick a channel before this can be posted anywhere.';
// The twins of posts.SHADOW_LINE / posts.SHADOW_LINE_NOWHERE: Discord's card is written in
// Python, this line is written live from the draft, so the words are kept the same by test.
const WILL_SHADOW = 'shadow — this goes to {shadow}, not {where}, until posts are on.';
const WILL_SHADOW_NOWHERE = 'shadow — this goes to {shadow}. It has no channel of its own yet, '
  + 'and nothing reaches one until posts are on.';
const WILL_SHADOW_SAME = 'shadow — this goes to {shadow}, which is where it was going anyway.';
const NO_SHADOW_CHANNEL = 'no shadow channel yet';
const SHADOW = 'shadow';
const PIN_WORDS = { true: 'pins it', false: 'leaves it unpinned' };
const STYLE_WORDS = { plain: 'a plain message', embed: 'an embed' };
// Site words, not posted words: the "every word the bot posts is editable on the site" rule
// is about what Discord shows. These are the dashboard talking to staff.
const PASTE_HINT = 'Paste keeps formatting';
const PASTE_KEPT = 'Pasted with formatting kept (headings, bold, bullets, links). '
  + 'Undo with Ctrl+Z.';
const PASTE_DISMISS = 'Dismiss';
const DELETE_QUESTION = 'Every word goes with it. Nothing puts it back.';
const USE_IT_CONFIRM = 'Use version {n}';
const VERSIONS_UNREADABLE = 'The version history could not be read just now. Everything else on '
  + 'this page still works — try again in a moment, and tell a Lead if it keeps happening.';
const GETTING_IT = 'Asking Black Bloc for this post…';
const NOTHING_CHANGED = 'Nothing has changed, so nothing was saved.';
const OVER_ITS_LIMIT = 'Nothing was saved — the box is over its limit.';
const SAVE_IT = 'Save Changes';
const DISCARD_IT = 'Discard';
const PENDING = '{n} change{s} pending';
const HIDE_IT = 'Hide';
const SHOWING_ALL = 'Showing {n} of {n} post{s}';
const SHOWING_SOME = 'Showing {shown} of the {n} post{s} on this page';
// Rule 3 of the owner's ask: Post it with unsaved edits saves first, so what goes out is
// always a version. The sentence under the button says both.
const WILL_POST_SAVED = 'Post it saves your changes first, then sends this to {where} as '
  + '{style} and {pin}.';
const WILL_UPDATE_SAVED = 'Update the post saves your changes first, then edits the message '
  + 'already in {where}, as {style} and {pin}.';

const COLUMNS = 'grid-template-columns: 12px minmax(0, 1.5fr) minmax(220px, 1.2fr) '
  + 'minmax(0, 1fr) minmax(0, 0.9fr) 24px';

const TONES = {
  posted: 'ok',
  'posted (shadow)': 'info',
  pinned: null,
  'changes not yet posted': 'warn',
  'not posted': 'danger',
};

const STATE_OF = {
  posted: 'ok',
  'posted (shadow)': 'info',
  'changes not yet posted': 'warn',
  'not posted': 'danger',
};

const FILTERS = [
  ['all', 'All', null],
  ['posted', 'Posted', (row) => row.posted],
  ['pending', 'Changed since posted', (row) => row.changes_pending],
  ['unposted', 'Not posted', (row) => !row.posted],
];

const state = { refs: null, filter: 'all', query: '' };
const shown = { slug: null };
let refresh = () => {};
let deepLinked = false;

function full(node) {
  node.setAttribute('data-span', 'full');
  return node;
}

function plural(count) {
  return count === 1 ? '' : 's';
}

function where(slug, tail = '') {
  return `/api/posts/${encodeURIComponent(slug)}${tail}`;
}

function wantedSlug() {
  const hash = String(location.hash || '').replace(/^#/, '').trim();
  return hash || null;
}

/** `close` is dispatched a task late, so a drawer replaced in the meantime keeps its hash. */
function forgetHash() {
  const drawer = document.querySelector('dialog.drawer');
  if (drawer && drawer.open) return;
  shown.slug = null;
  if (location.hash) history.replaceState(null, '', location.pathname + location.search);
}

/** The three `/api/ref/*` lists the preview resolves mentions through, read once per load. */
async function refs() {
  if (state.refs === null) {
    const [channels, roles, members] = await Promise.all([
      refChannels().catch(() => []),
      refRoles().catch(() => []),
      refMembers('').catch(() => []),
    ]);
    state.refs = { channels, roles, members };
  }
  return state.refs;
}

function whereWords(row) {
  return row.channel_name ? `#${row.channel_name}` : NO_CHANNEL;
}

function shadowWords(shadow) {
  return shadow && shadow.channel_name ? `#${shadow.channel_name}` : NO_SHADOW_CHANNEL;
}

function postedLine(row, shadow) {
  if (!row.posted) return NOT_POSTED_ANYWHERE;
  const rehearsal = row.posted_where === SHADOW;
  const line = rehearsal ? POSTED_IN_SHADOW : POSTED_HERE;
  const at = rehearsal ? shadowWords(shadow) : whereWords(row);
  return line.replace('{where}', at) + (row.pin ? PINNED_TOO : NOT_PINNED);
}

/** The one word that decides the dot: what the row's own status list leads with. */
function leadState(row) {
  if (row.changes_pending) return 'warn';
  const head = (row.status || []).find((word) => word in STATE_OF);
  return head ? STATE_OF[head] : 'danger';
}

function statusPills(row) {
  return (row.status || []).map((word) => badge(word, TONES[word] === undefined ? null : TONES[word]));
}

function willPost(draft, post, payload, dirty = false) {
  if (payload.mode === SHADOW) {
    const at = shadowWords(payload.shadow);
    if (!draft.channel_id) return WILL_SHADOW_NOWHERE.replace('{shadow}', at);
    if (payload.shadow && String(draft.channel_id) === String(payload.shadow.channel_id)) {
      return WILL_SHADOW_SAME.replace('{shadow}', at);
    }
    return WILL_SHADOW
      .replace('{shadow}', at)
      .replace('{where}', `#${draft.channel_name || post.channel_name || ''}`);
  }
  if (!draft.channel_id) return NEEDS_A_CHANNEL;
  const saving = post.posted ? WILL_UPDATE_SAVED : WILL_POST_SAVED;
  const template = dirty ? saving : (post.posted ? WILL_UPDATE : WILL_POST);
  return template
    .replace('{where}', `#${draft.channel_name || post.channel_name || ''}`)
    .replace('{style}', STYLE_WORDS[draft.style] || STYLE_WORDS.plain)
    .replace('{pin}', PIN_WORDS[String(Boolean(draft.pin))]);
}

function draftOf(post) {
  return {
    title: post.title || '',
    body: post.body || '',
    style: post.style,
    pin: Boolean(post.pin),
    channel_id: post.channel_id || '',
    channel_name: post.channel_name || '',
  };
}

function changeCount(now, was) {
  return ['title', 'body', 'style', 'pin', 'channel_id']
    .filter((key) => String(now[key]) !== String(was[key])).length;
}

function counterNode() {
  const node = el('span', { class: 'counter mono' });
  node.paint = (count, cap) => {
    node.textContent = `${count.toLocaleString()} / ${cap.toLocaleString()}`;
    const tone = count > cap ? 'danger' : count >= cap * AMBER_AT ? 'warn' : null;
    if (tone) node.setAttribute('data-tone', tone);
    else node.removeAttribute('data-tone');
  };
  return node;
}

function pasteNoteNode() {
  const node = el('p', { class: 'notice pastenote' }, [
    el('span', { text: PASTE_KEPT }),
    ' ',
    el('button', {
      class: 'say-nothing-do',
      type: 'button',
      text: PASTE_DISMISS,
      on: { click: () => { node.hidden = true; } },
    }),
  ]);
  node.hidden = true;
  node.show = () => { node.hidden = false; };
  return node;
}

/** `insertText` is what keeps Ctrl+Z working; `setRangeText` is the fallback that may not. */
function insertAtCaret(node, text) {
  node.focus();
  try {
    if (document.execCommand && document.execCommand('insertText', false, text)) return;
  } catch (error) {
    // fall through to the range write
  }
  const from = node.selectionStart === null || node.selectionStart === undefined
    ? node.value.length
    : node.selectionStart;
  const to = node.selectionEnd === null || node.selectionEnd === undefined ? from : node.selectionEnd;
  node.setRangeText(text, from, to, 'end');
}

/** The markdown a rich paste is worth, or '' when the clipboard has nothing plain text lacks. */
function markdownFromPaste(event) {
  const data = event.clipboardData || (typeof window === 'undefined' ? null : window.clipboardData);
  if (!data) return '';
  let html = '';
  try {
    html = data.getData('text/html') || '';
  } catch (error) {
    return '';
  }
  if (!html.trim()) return '';
  let made = '';
  try {
    made = htmlToDiscordMarkdown(html);
  } catch (error) {
    return '';
  }
  const plain = String(data.getData('text/plain') || '').replace(/\r\n/g, '\n').trim();
  return made && made !== plain ? made : '';
}

async function versionsOf(slug) {
  try {
    return await api(where(slug, '/versions'));
  } catch (error) {
    return null;
  }
}

/**
 * The whole post, in the drawer the row opens — what used to be a page of its own
 * behind an unstyled title button.
 */
async function postDrawer(payload, known, history) {
  const post = payload.post;
  const draft = draftOf(post);
  const was = draftOf(post);
  const say = notice();
  let seen = history;

  const marks = el('div', { class: 'postmarks' }, statusPills(post));
  const whereLine = el('p', { class: 'row-detail', text: postedLine(post, payload.shadow) });

  const title = el('input', { class: 'input', type: 'text', maxlength: String(post.title_cap) });
  title.value = draft.title;

  const channel = await channelSelect(draft.channel_id || null, { id: 'post-channel' });
  const style = el('select', { class: 'input', id: 'post-style' }, payload.styles.map((one) =>
    el('option', {
      value: one.style,
      text: `${one.label} — ${one.cap.toLocaleString()} characters`,
      selected: one.style === draft.style || undefined,
    })));
  const pin = el('input', { class: 'switch', type: 'checkbox', id: 'post-pin' });
  pin.checked = draft.pin;

  const box = el('textarea', { class: 'input area postbox', id: 'post-body', rows: '14', spellcheck: 'true' });
  box.value = draft.body;
  const pasteNote = pasteNoteNode();
  const counter = counterNode();
  const howLine = el('p', { class: 'field-help', id: 'post-how' });
  const pending = el('p', { class: 'field-help' });
  const versionsBox = el('div');
  const versionView = el('div', { class: 'postcol' });

  // The BOT decides what a post becomes — plain or embed, and where the title is clamped —
  // so the pane asks it rather than rendering a second opinion here. See code-notes.
  const mock = discordMock({
    feature: POST_FEATURE,
    sample: () => ({ style: draft.style, title: draft.title, body: draft.body }),
  });
  const preview = el('div', { class: 'preview', id: 'post-preview' }, [mock.node, mock.say]);

  const capOf = () => (payload.styles.find((one) => one.style === draft.style) || { cap: 2000 }).cap;

  const paintPreview = () => {
    mock.repaint();
    counter.paint(draft.body.length, capOf());
    howLine.textContent = willPost(draft, post, payload, Boolean(changeCount(draft, was)));
  };
  const schedule = paintPreview;

  const discard = button(DISCARD_IT, () => discardDraft(), { tone: 'quiet', small: false });

  const refreshBar = () => {
    const count = changeCount(draft, was);
    pending.textContent = PENDING.replace('{n}', String(count)).replace('{s}', plural(count));
    pending.hidden = count === 0;
    discard.hidden = count === 0;
  };

  title.addEventListener('input', () => {
    draft.title = title.value;
    refreshBar();
    schedule();
  });
  box.addEventListener('input', () => {
    draft.body = box.value;
    refreshBar();
    schedule();
  });
  box.addEventListener('paste', (event) => {
    const made = markdownFromPaste(event);
    if (!made) return;
    event.preventDefault();
    insertAtCaret(box, made);
    draft.body = box.value;
    refreshBar();
    paintPreview();
    pasteNote.show();
  });
  style.addEventListener('change', () => {
    draft.style = style.value;
    refreshBar();
    paintPreview();
  });
  pin.addEventListener('change', () => {
    draft.pin = pin.checked;
    refreshBar();
    paintPreview();
  });
  channel.addEventListener('change', () => {
    draft.channel_id = readSelect(channel, false) || '';
    const picked = known.channels.find((one) => String(one.id) === String(draft.channel_id));
    draft.channel_name = picked ? picked.name : '';
    refreshBar();
    paintPreview();
  });

  const discardDraft = () => {
    Object.assign(draft, draftOf(post));
    title.value = draft.title;
    box.value = draft.body;
    style.value = draft.style;
    pin.checked = draft.pin;
    channel.value = draft.channel_id;
    say.say('');
    refreshBar();
    paintPreview();
  };

  const saveDraft = () => send(where(post.slug), 'PUT', {
    title: draft.title.trim(),
    body: draft.body,
    style: draft.style,
    pin: draft.pin,
    channel_id: draft.channel_id || null,
  });

  const settle = (found) => {
    Object.assign(post, found.post);
    payload.mode = found.mode;
    payload.shadow = found.shadow;
    Object.assign(was, draftOf(post));
    marks.replaceChildren(...statusPills(post));
    whereLine.textContent = postedLine(post, payload.shadow);
    refreshBar();
    paintPreview();
  };

  /** A move that changes Discord parks its sentence, shuts the drawer and reloads the list. */
  const andClose = async () => {
    keepSaying('posts', say);
    closeDrawer();
    await refresh();
  };

  const viewVersion = async (version) => {
    const found = await run(say, () => api(where(post.slug, `/versions/${version.n}`)), () => '');
    if (!found.ok) return;
    const older = found.found.preview;
    const back = discordMock({ feature: POST_FEATURE, sample: () => ({ ...older }) });
    const drawn = el('div', { class: 'preview' }, [back.node, back.say]);
    versionView.replaceChildren(
      el('div', { class: 'postboxhead' }, [
        el('span', {
          class: 'field-label',
          text: VIEWING.replace('{n}', String(version.n)).replace('{title}', post.title),
        }),
        button(HIDE_IT, () => versionView.replaceChildren(), { tone: 'quiet' }),
      ]),
      drawn,
    );
  };

  const useVersion = async (version) => {
    const top = (seen && seen.versions && seen.versions.length)
      ? Number(seen.versions[0].n) : Number(version.n);
    const sure = await ask({
      title: `Use version ${version.n} of “${post.title}”?`,
      body: [useItQuestion(version, top + 1)],
      confirmLabel: USE_IT_CONFIRM.replace('{n}', String(version.n)),
      tone: 'warn',
    });
    if (!sure) return;
    const done = await run(
      say,
      () => send(where(post.slug, `/versions/${version.n}/restore`), 'POST', {}),
      (found) => found?.message || 'Put back.',
    );
    if (!done.ok) return;
    await andClose();
  };

  const paintVersions = (found) => {
    seen = found;
    versionView.replaceChildren();
    versionsBox.replaceChildren(found === null
      ? notice(VERSIONS_UNREADABLE, 'warn')
      : versionsFoldout(found.versions, { onView: viewVersion, onUse: useVersion }));
  };
  paintVersions(history);

  const save = button(SAVE_IT, async () => {
    if (!changeCount(draft, was)) {
      say.say(NOTHING_CHANGED, 'warn');
      return;
    }
    if (draft.body.length > capOf()) {
      say.say(OVER_ITS_LIMIT, 'danger');
      return;
    }
    const done = await run(say, () => saveDraft(), (found) => found?.message || 'Saved.');
    if (!done.ok) return;
    settle(done.found);
    paintVersions(await versionsOf(post.slug));
    refresh();
  }, { tone: 'warn', small: false });

  /** Rule 3: a dirty editor is SAVED first, so what went out is always a version. */
  const publish = button(post.move, async () => {
    if (draft.body.length > capOf()) {
      say.say(OVER_ITS_LIMIT, 'danger');
      return;
    }
    const done = await run(
      say,
      async () => {
        if (changeCount(draft, was)) await saveDraft();
        return send(where(post.slug, '/publish'), 'POST', {});
      },
      (found) => found?.message || 'Done.',
    );
    if (!done.ok) return;
    await andClose();
  }, { tone: 'warn' });

  const moves = [save, discard, publish];
  if (post.posted) {
    moves.push(button('Take it down', async () => {
      const done = await run(
        say,
        () => send(where(post.slug, '/takedown'), 'POST', {}),
        (found) => found?.message || 'Done.',
      );
      if (!done.ok) return;
      await andClose();
    }, { tone: 'quiet' }));
  }
  if (!post.seeded) {
    moves.push(button('Delete this post', async () => {
      const sure = await ask({
        title: `Delete “${post.title}”?`,
        body: [DELETE_QUESTION],
        confirmLabel: 'Delete it',
      });
      if (!sure) return;
      const done = await run(
        say,
        () => api(where(post.slug), { method: 'DELETE' }),
        (found) => found?.message || 'Gone.',
      );
      if (!done.ok) return;
      await andClose();
    }, { tone: 'danger' }));
  }

  paintPreview();
  refreshBar();

  return [
    marks,
    whereLine,
    el('div', { class: 'formrow' }, [
      field('Title', title, 'Staff see this here; an embed shows it at the top of the message.'),
      field('Channel', channel, 'Where the message lives. Black Bloc edits that one message.'),
    ]),
    el('div', { class: 'formrow' }, [
      field('Style', style, 'A plain message renders # headers; an embed holds more but does not.'),
      field('Pin it', pin, 'Black Bloc pins the message once it is posted, and re-pins it if '
        + 'somebody unpins it.'),
    ]),
    el('div', { class: 'postgrid' }, [
      el('div', { class: 'postcol' }, [
        el('div', { class: 'postboxhead' }, [
          el('span', { class: 'postboxlabel' }, [
            el('label', { class: 'field-label', for: 'post-body', text: 'The message' }),
            el('span', { class: 'field-help pastehint', text: PASTE_HINT }),
          ]),
          counter,
        ]),
        box,
        pasteNote,
      ]),
      el('div', { class: 'postcol' }, [
        el('div', { class: 'postboxhead' }, [
          el('span', { class: 'field-label', text: 'What Discord will show' }),
        ]),
        preview,
      ]),
    ]),
    howLine,
    pending,
    bar(moves),
    say,
    versionsBox,
    versionView,
  ];
}

async function openPost(slug, title) {
  shown.slug = slug;
  if (wantedSlug() !== slug) location.hash = `#${slug}`;
  openDrawer(title, sayNothing(GETTING_IT), { onClose: forgetHash });
  let payload = null;
  try {
    payload = await api(where(slug));
  } catch (error) {
    const said = sentenceFor(error);
    openDrawer(title, [notice(said.text, said.tone)], { onClose: forgetHash });
    return;
  }
  const history = await versionsOf(slug);
  openDrawer(
    payload.post.title,
    await postDrawer(payload, await refs(), history),
    { onClose: forgetHash },
  );
}

/**
 * The row IS the control — `button.grid-row`, the construct `page-moderation.js:144`
 * already uses, with the hover, focus and cursor rules `site.css:910` gives it.
 */
function postRow(post, payload) {
  return el('button', {
    class: 'grid-row',
    type: 'button',
    style: COLUMNS,
    'data-search': `${post.title} ${post.channel_name || ''} ${(post.status || []).join(' ')} ${post.body || ''}`.toLowerCase(),
    on: { click: () => openPost(post.slug, post.title) },
  }, [
    el('span', { class: 'dot-sm', 'data-tone': leadState(post) }),
    el('span', { class: 'cell-name', text: post.title }),
    el('span', { class: 'cell-kind' }, statusPills(post)),
    el('span', { class: 'cell-quiet', text: postedLine(post, payload.shadow) }),
    el('span', {
      class: 'cell-quiet',
      title: ago(post.updated_at).title,
      text: `Last saved ${ago(post.updated_at).text}`,
    }),
    icon('chevronRight', 16),
  ]);
}

function headRow() {
  return el('div', { class: 'grid-row head', style: COLUMNS }, [
    el('span'),
    el('span', { text: 'Post' }),
    el('span', { text: 'Status' }),
    el('span', { text: 'Channel' }),
    el('span', { text: 'Last saved' }),
    el('span'),
  ]);
}

function newPostDrawer() {
  const say = notice();
  const title = el('input', { class: 'input', type: 'text', placeholder: 'Welcome and rules' });
  const make = button('Create the post', async () => {
    if (!title.value.trim()) {
      say.say(NEED_A_TITLE, 'warn');
      return;
    }
    const done = await run(
      say,
      () => send('/api/posts', 'POST', { title: title.value.trim() }),
      (found) => found?.message || 'Made.',
    );
    if (!done.ok) return;
    keepSaying('posts', say);
    closeDrawer();
    await refresh();
    openPost(done.found.post.slug, done.found.post.title);
  }, { tone: 'warn', small: false });
  return [
    el('div', { class: 'formrow' }, [
      field('What is it called?', title, 'The title staff see here, and the embed title if you '
        + 'set the style to an embed.'),
    ]),
    bar([make]),
    say,
  ];
}

function postsSection(payload, say) {
  const rows = payload.posts.map((post) => ({ post, node: postRow(post, payload) }));
  const list = section('The posts', LIST_NOTE, { count: payload.posts.length, open: true });
  const foot = el('div', { class: 'grid-foot' });
  const grid = el('div', { class: 'grid-table', style: 'min-width: 760px' }, [
    headRow(),
    ...rows.map((one) => one.node),
    foot,
  ]);

  const paint = () => {
    const rule = (FILTERS.find(([key]) => key === state.filter) || FILTERS[0])[2];
    let hits = 0;
    for (const one of rows) {
      const hit = (rule === null || rule(one.post))
        && (state.query === '' || (one.node.getAttribute('data-search') || '').includes(state.query));
      one.node.hidden = !hit;
      if (hit) hits += 1;
    }
    foot.textContent = hits === rows.length
      ? SHOWING_ALL.replace(/\{n\}/g, String(rows.length)).replace('{s}', plural(rows.length))
      : SHOWING_SOME
        .replace('{shown}', String(hits))
        .replace('{n}', String(rows.length))
        .replace('{s}', plural(rows.length));
  };

  const chips = el('div', { class: 'chipbar' }, FILTERS.map(([key, label]) => el('button', {
    class: 'chip-filter',
    type: 'button',
    'data-kind': key,
    'aria-pressed': state.filter === key ? 'true' : 'false',
    text: label,
    on: {
      click: (event) => {
        state.filter = key;
        for (const chip of event.currentTarget.parentElement.children) {
          chip.setAttribute('aria-pressed', chip.getAttribute('data-kind') === key ? 'true' : 'false');
        }
        paint();
      },
    },
  })));
  const search = searchField({
    label: 'Search the posts',
    placeholder: 'Search the posts…',
    value: state.query,
    onQuery: (query) => {
      state.query = query;
      paint();
    },
  });

  const newPost = button('New post', () => openDrawer('A new post', newPostDrawer()), { tone: 'warn' });
  newPost.style.marginLeft = 'auto';
  paint();

  list.body.append(
    el('p', { class: 'field-help' }, [
      el('span', { text: 'Posts are ' }),
      modeChip(payload.mode),
      el('span', { text: (payload.notes || [])[0] ? '. ' : '.' }),
      ...boldParts((payload.notes || [])[0] || ''),
    ]),
    ...(payload.notes || []).slice(1).map((line) => el('p', { class: 'field-help' }, boldParts(line))),
    payload.guard && payload.guard.said
      ? el('p', { class: 'field-help' }, boldParts(payload.guard.said))
      : null,
    card(null, [
      el('div', { class: 'card-head' }, [search, chips, newPost]),
      payload.posts.length === 0
        ? sayNothing(NOTHING_YET)
        : el('div', { class: 'table-scroll' }, [grid]),
    ]),
    say,
  );
  return full(list.node);
}

/** A shared block demoted out of the "On this page" rail so a fold is not a place. */
function unsectioned(node) {
  const inner = node.querySelector('.sect-inner');
  return inner ? [...inner.childNodes] : [node];
}

async function machinerySection(specs) {
  const one = section('Settings and logs', MACHINERY_NOTE, { id: 'machinery' });
  one.body.append(
    foldout('Settings', [
      el('p', { class: 'field-help', text: SETTINGS_NOTE }),
      await settingsPanel(specs, { where: 'Posts', onSaved: () => refresh() }),
    ], { count: specs.length }),
    foldout('Logs', unsectioned(await logsSection('posts'))),
  );
  return full(one.node);
}

async function load() {
  const payload = await api('/api/posts');
  const say = sayAgain('posts', notice());
  const specs = settingsNamespace(await settings(), 'posts')
    .filter((spec) => SETTING_KEYS.includes(spec.key));
  const head = document.getElementById('page-aside');
  if (head) head.replaceChildren();

  document.getElementById('dash').replaceChildren(
    postsSection(payload, say),
    await machinerySection(specs),
  );

  const slug = wantedSlug();
  if (slug && !deepLinked) {
    deepLinked = true;
    const found = payload.posts.find((one) => String(one.slug) === slug);
    openPost(slug, found ? found.title : slug);
  }
}

window.addEventListener('hashchange', () => {
  const slug = wantedSlug();
  if (!slug) {
    if (shown.slug) closeDrawer();
    return;
  }
  if (slug === shown.slug) return;
  openPost(slug, slug);
});

refresh = start({ tab: 'posts', load });
