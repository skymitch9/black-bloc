import { api, refChannels, refMembers, refRoles, send, settings, settingsNamespace } from './api.js';
import { start } from './app.js';
import { docTitle as titleInDoc, htmlToDiscordMarkdown, mentionChannels } from './clipmd.js';
import { blockPreview } from './blockpreview.js';
import { BLOCK_EDITORS } from './blockwords.js';
import { BLOCK_FILTERS, blockText } from './listfilter.js';
import { logsSection } from './logs.js';
import { remember, remembered } from './layout.js';
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
  chipBar,
  closeDrawer,
  el,
  field,
  foldout,
  formatBar,
  icon,
  keepSaying,
  listFilter,
  modeChip,
  notice,
  openDrawer,
  readSelect,
  run,
  sayAgain,
  sayNothing,
  section,
  sentenceFor,
  settingsPanel,
} from './ui.js';

const MODE_KEY = 'posts_mode';
const SETTING_KEYS = [
  MODE_KEY, 'posts_shadow_channel_id', 'posts_panel_minutes', 'posts_import_style', 'posts_untitled_title',
  'posts_log_level',
];
const NOTHING_YET = 'There are no posts yet.';
const NO_CHANNEL = 'no channel yet';
const AMBER_AT = 0.9;
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
// Blocks (owner, 2026-09-27: "lets do blocks"). A block rides under a post in the same message.
const BLOCKS_LABEL = 'Blocks';
const NO_BLOCKS = 'No blocks — the message is only the post.';
const ADD_A_BLOCK = 'Add a block…';
const PICK_A_BLOCK = 'Pick a block…';
const HELD_ON = '{name} — on {title}';
const HELD_LINE = '{name} goes on one post at a time and is on {title}. Remove it there first.';
const REMOVE_IT = 'Remove';
const MOVE_UP = '↑';
const MOVE_DOWN = '↓';
const WILL_CARRY = ' Its blocks ride under it, in the same message: {names}.';
const ONE_AT_A_TIME = 'one post at a time';
const ANY_NUMBER = 'any number of posts';
const EDIT_BLOCK = 'Edit the {name} block';
const OPEN_IT = 'Open {title}';
const ON_NO_POST = 'On no post yet — open a post and use Add a block….';
const LOOKS_LIKE = 'What it looks like in Discord';
const BLOCKS_FOLD_KEY = 'bb_blocks_fold';
const BLOCKS_FOLD_MANY = 3;
const FOLD_ALL = 'Fold all';
const OPEN_ALL = 'Open all';
const SEARCH_BLOCKS = 'Search the blocks';
const SEARCH_BLOCKS_PLACEHOLDER = 'Search the blocks…';
const NO_BLOCK_MATCH = 'No block matches this filter.';
const STYLE_WORDS = { plain: 'a plain message', embed: 'an embed' };
// Site words, not posted words: the "every word the bot posts is editable on the site" rule
// is about what Discord shows. These are the dashboard talking to staff.
const PASTE_KEPT = 'Pasted with formatting kept (headings, bold, bullets, links). '
  + 'Undo with Ctrl+Z.';
const PASTE_DISMISS = 'Dismiss';
const IMPORT_FOLD = 'Import from a Google Doc';
const IMPORT_PLACEHOLDER = 'https://docs.google.com/document/d/…';
const IMPORT_IT = 'Import';
const IMPORT_NO_LINK = "Paste a Google Doc's link into the box first — nothing was fetched.";
const IMPORT_REPLACE_TITLE = 'Replace the message with the doc?';
const IMPORT_REPLACE_BODY = 'The message box already has words in it. The doc replaces them as an '
  + 'unsaved draft; Put back what was there brings them back, and Discard throws the draft away.';
const IMPORT_REPLACE_OK = 'Replace it';
const IMPORT_EMPTY = 'That doc came back with no words Black Bloc can post, so the box was left '
  + 'as it was.';
const IMPORT_DONE = 'Imported from “{title}” — the box is an unsaved draft. Nothing is saved or '
  + 'posted until you press Save Changes or Post it.';
const IMPORT_OVER = ' It runs past this style’s limit, so the counter is red and Save refuses until '
  + 'it is shorter.';
const IMPORT_UNTITLED = 'the Google Doc';
const BOX_WORDS = { embed: 'the embed box, like the welcome post', plain: 'a plain message' };
const IMPORT_RESTYLED = ' The style is set to {box} too — also unsaved.';
const NEW_SCRATCH = 'Start from scratch';
const NEW_IMPORT = 'Import a Google Doc';
const NEW_DOC_LINK = 'The Google Doc’s link';
const NEW_DOC_TITLE_HINT = 'fills in from the doc';
const NEW_READ_IT = 'Read the doc';
const NEW_READ = 'Read “{title}” — {count} characters, as {box}. Check the title, then press Create the post.';
const NEW_OVER = '“{title}” is {count} characters and {style} holds {cap}, so nothing was made. Shorten '
  + 'the doc, or set the import style to the embed on the Settings fold below.';
const NEW_STALE = 'The link changed since the doc was read — press Read the doc again.';
const IMPORT_PUT_BACK = 'Put back what was there';
const IMPORT_PUT_BACK_DONE = 'Put back — the box holds what it had before the import.';
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
  'carries the front door': 'info',
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
const blockState = { filter: 'all', query: '' };
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

/** The doc's title: the export's own, else clipmd's first Title line or real heading, else ''. */
function titleOfDoc(found) {
  const said = String((found && found.title) || '').trim();
  if (said) return said;
  try {
    return titleInDoc((found && found.html) || '');
  } catch (error) {
    return '';
  }
}

/** The one conversion of a fetched export: the paste path's converter, then `#name` → `<#id>`. */
async function markdownOfDoc(found) {
  let made = '';
  try {
    made = htmlToDiscordMarkdown((found && found.html) || '');
  } catch (error) {
    return '';
  }
  const known = await refs().catch(() => ({ channels: [] }));
  return mentionChannels(made, known.channels);
}

function capFor(styles, style) {
  return ((styles || []).find((one) => one.style === style) || { cap: 2000 }).cap;
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
  const pin = el('input', { class: 'input switch', type: 'checkbox', id: 'post-pin' });
  pin.checked = draft.pin;
  const pinLine = el('label', {
    class: 'switchline',
    title: 'Black Bloc pins the message once it is posted, and re-pins it if somebody unpins it.',
  }, [
    pin,
    el('span', { class: 'field-label', text: 'Pin it' }),
  ]);
  const blocksBox = el('div', { class: 'postblocks', id: 'post-blocks' });

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
  const mock = blockPreview({
    post: () => ({ style: draft.style, title: draft.title, body: draft.body }),
    blocks: () => (post.blocks || []).map((one) => one.kind),
  });
  const preview = el('div', { class: 'preview', id: 'post-preview' }, [mock.node, mock.say]);

  const capOf = () => capFor(payload.styles, draft.style);

  const paintPreview = () => {
    mock.repaint();
    counter.paint(draft.body.length, capOf());
    const names = (post.blocks || []).map((one) => one.name).join(', ');
    howLine.textContent = willPost(draft, post, payload, Boolean(changeCount(draft, was)))
      + (names ? WILL_CARRY.replace('{names}', names) : '');
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
    forgetImport();
    refreshBar();
    paintPreview();
  };

  const docLink = el('input', {
    class: 'input',
    type: 'url',
    id: 'post-import-url',
    placeholder: IMPORT_PLACEHOLDER,
    spellcheck: 'false',
    autocomplete: 'off',
  });
  const importSay = notice();
  const importNote = el('p', { class: 'notice pastenote', id: 'post-import-note' });
  importNote.hidden = true;
  let beforeImport = null;

  function forgetImport() {
    beforeImport = null;
    importNote.hidden = true;
  }

  /** Through `insertText` like a paste, so Ctrl+Z still reaches the words the import replaced. */
  const replaceBody = (text) => {
    box.focus();
    box.select();
    if (text) insertAtCaret(box, text);
    if (box.value !== text) box.value = text;
    draft.body = box.value;
    refreshBar();
    paintPreview();
  };

  const setStyle = (wanted) => {
    draft.style = wanted;
    style.value = wanted;
  };

  const putBack = () => {
    if (beforeImport === null) return;
    setStyle(beforeImport.style);
    replaceBody(beforeImport.body);
    forgetImport();
    importSay.say(IMPORT_PUT_BACK_DONE, 'ok');
  };

  const paintImportNote = (named, over, restyled) => {
    const box = restyled ? IMPORT_RESTYLED.replace('{box}', BOX_WORDS[draft.style] || draft.style) : '';
    importNote.replaceChildren(
      el('span', { text: IMPORT_DONE.replace('{title}', named) + box + (over ? IMPORT_OVER : '') }),
      ' ',
      button(IMPORT_PUT_BACK, putBack, { tone: 'quiet' }),
      el('button', {
        class: 'say-nothing-do',
        type: 'button',
        text: PASTE_DISMISS,
        on: { click: () => { importNote.hidden = true; } },
      }),
    );
    importNote.hidden = false;
  };

  const importDoc = async () => {
    const url = docLink.value.trim();
    if (!url) {
      importSay.say(IMPORT_NO_LINK, 'warn');
      return;
    }
    if (draft.body.trim()) {
      const sure = await ask({
        title: IMPORT_REPLACE_TITLE,
        body: [IMPORT_REPLACE_BODY],
        confirmLabel: IMPORT_REPLACE_OK,
        tone: 'warn',
      });
      if (!sure) return;
    }
    importButton.disabled = true;
    let done = null;
    try {
      done = await run(
        importSay,
        () => send('/api/posts/import-doc', 'POST', { url, slug: post.slug }),
        () => '',
      );
    } finally {
      importButton.disabled = false;
    }
    if (!done.ok) return;
    const made = await markdownOfDoc(done.found);
    if (!made.trim()) {
      importSay.say(IMPORT_EMPTY, 'warn');
      return;
    }
    const kept = { body: draft.body, style: draft.style };
    const wanted = payload.import_style || draft.style;
    const restyled = wanted !== draft.style;
    if (restyled) setStyle(wanted);
    replaceBody(made);
    beforeImport = kept;
    pasteNote.hidden = true;
    paintImportNote(done.found.title || IMPORT_UNTITLED, draft.body.length > capOf(), restyled);
  };

  const importButton = button(IMPORT_IT, () => importDoc(), { tone: 'quiet' });
  docLink.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter') return;
    event.preventDefault();
    importDoc();
  });
  const importFold = foldout(IMPORT_FOLD, [
    el('div', { class: 'docimport' }, [docLink, importButton]),
    importSay,
  ]);
  importFold.classList.add('docimportfold');

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
    if (found.block_kinds) payload.block_kinds = found.block_kinds;
    paintBlocks();
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
    const back = blockPreview({ post: () => ({ ...older }), sample: () => ({ ...older }) });
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

  /** A block move acts at once, like Post it: the post's own draft is left exactly as it is. */
  const blockMove = async (work) => {
    const done = await run(say, work, (found) => found?.message || 'Done.');
    if (!done.ok) return;
    const kept = { ...draft };
    settle(done.found);
    Object.assign(draft, kept);
    refreshBar();
    paintPreview();
    refresh();
  };

  const blockRow = (block, index, count) => el('div', { class: 'postblock', 'data-kind': block.kind }, [
    el('span', { class: 'postblock-name', text: block.name }),
    count > 1 ? button(MOVE_UP, () => blockMove(() => send(where(post.slug, '/blocks'), 'PUT', {
      order: moved(post.blocks, index, -1),
    })), { tone: 'quiet', disabled: index === 0 }) : null,
    count > 1 ? button(MOVE_DOWN, () => blockMove(() => send(where(post.slug, '/blocks'), 'PUT', {
      order: moved(post.blocks, index, 1),
    })), { tone: 'quiet', disabled: index === count - 1 }) : null,
    button(REMOVE_IT, () => blockMove(
      () => api(where(post.slug, `/blocks/${encodeURIComponent(block.kind)}`), { method: 'DELETE' }),
    ), { tone: 'quiet' }),
  ]);

  const paintBlocks = () => {
    const mine = post.blocks || [];
    const offered = (payload.block_kinds || []).filter((kind) => !mine.some((one) => one.kind === kind.kind));
    const held = offered.filter((kind) => kind.exclusive && (kind.on || []).length);
    const pick = el('select', { class: 'input', id: 'post-add-block', hidden: true }, [
      el('option', { value: '', text: PICK_A_BLOCK }),
      ...offered.map((kind) => {
        const holder = kind.exclusive && (kind.on || [])[0];
        return el('option', {
          value: kind.kind,
          disabled: holder ? true : undefined,
          text: holder ? HELD_ON.replace('{name}', kind.name).replace('{title}', holder.title) : kind.name,
        });
      }),
    ]);
    pick.addEventListener('change', () => {
      if (!pick.value) return;
      const kind = pick.value;
      blockMove(() => send(where(post.slug, '/blocks'), 'POST', { kind }));
    });
    const add = button(ADD_A_BLOCK, () => {
      pick.hidden = !pick.hidden;
      if (!pick.hidden) pick.focus();
    }, { tone: 'quiet' });
    blocksBox.replaceChildren(...[
      el('div', { class: 'postboxhead' }, [
        el('span', { class: 'field-label', text: BLOCKS_LABEL }),
      ]),
      mine.length
        ? el('div', { class: 'postblock-list' }, mine.map((block, index) => blockRow(block, index, mine.length)))
        : el('p', { class: 'field-help', text: NO_BLOCKS }),
      offered.length ? bar([add, pick]) : null,
      ...held.map((kind) => el('p', {
        class: 'field-help',
        text: HELD_LINE.replace('{name}', kind.name).replace('{title}', kind.on[0].title),
      })),
    ].filter(Boolean));
  };
  paintBlocks();

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
    forgetImport();
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
      field('Title', title),
      field('Channel', channel),
    ]),
    el('div', { class: 'formrow' }, [
      field('Style', style),
    ]),
    el('div', { class: 'postgrid' }, [
      el('div', { class: 'postcol' }, [
        el('div', { class: 'postboxhead' }, [
          el('label', { class: 'field-label', for: 'post-body', text: 'The message' }),
          counter,
        ]),
        formatBar(box),
        box,
        pasteNote,
        importNote,
        importFold,
      ]),
      el('div', { class: 'postcol' }, [
        el('div', { class: 'postboxhead' }, [
          el('span', { class: 'field-label', text: 'What Discord will show' }),
        ]),
        preview,
      ]),
    ]),
    blocksBox,
    howLine,
    pending,
    bar([pinLine, ...moves]),
    say,
    versionsBox,
    versionView,
  ];
}

function moved(blocks, index, step) {
  const order = blocks.map((one) => one.kind);
  const [one] = order.splice(index, 1);
  order.splice(index + step, 0, one);
  return order;
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
function postText(post) {
  return `${post.title} ${post.channel_name || ''} ${(post.status || []).join(' ')} ${post.body || ''}`;
}

function postRow(post, payload) {
  return el('button', {
    class: 'grid-row',
    type: 'button',
    style: COLUMNS,
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

/** Two ways in: a bare title, or a Google Doc born in posts_import_style in one call. */
function newPostDrawer(index) {
  const say = notice();
  const importStyle = index.import_style || 'embed';
  const untitled = String(index.untitled_title || '').trim() || 'Untitled';
  const cap = capFor(index.styles, importStyle);

  const opened = async (done) => {
    keepSaying('posts', say);
    closeDrawer();
    await refresh();
    openPost(done.found.post.slug, done.found.post.title);
  };

  const title = el('input', { class: 'input', type: 'text', id: 'new-title', placeholder: 'Welcome and rules' });
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
    if (done.ok) await opened(done);
  }, { tone: 'warn', small: false });
  const scratch = el('div', { class: 'newpost-pane', id: 'new-scratch' }, [
    el('div', { class: 'formrow' }, [field('What is it called?', title)]),
    bar([make]),
  ]);

  const link = el('input', {
    class: 'input',
    type: 'url',
    id: 'new-import-url',
    placeholder: IMPORT_PLACEHOLDER,
    spellcheck: 'false',
    autocomplete: 'off',
  });
  const docTitle = el('input', { class: 'input', type: 'text', id: 'new-import-title', placeholder: NEW_DOC_TITLE_HINT });
  let fetched = null;
  let typed = false;
  docTitle.addEventListener('input', () => { typed = true; });

  const createIt = button('Create the post', async () => {
    if (!fetched || fetched.url !== link.value.trim()) {
      say.say(NEW_STALE, 'warn');
      return;
    }
    if (!docTitle.value.trim()) {
      say.say(NEED_A_TITLE, 'warn');
      return;
    }
    const done = await run(
      say,
      () => send('/api/posts', 'POST', {
        title: docTitle.value.trim(),
        body: fetched.body,
        style: importStyle,
        ...(typed ? {} : { title_from: 'doc' }),
      }),
      (found) => found?.message || 'Made.',
    );
    if (done.ok) await opened(done);
  }, { tone: 'warn', small: false });
  createIt.hidden = true;

  const forget = () => {
    fetched = null;
    createIt.hidden = true;
  };
  link.addEventListener('input', forget);

  const readIt = button(NEW_READ_IT, async () => {
    forget();
    const url = link.value.trim();
    if (!url) {
      say.say(IMPORT_NO_LINK, 'warn');
      return;
    }
    readIt.disabled = true;
    let done = null;
    try {
      done = await run(say, () => send('/api/posts/import-doc', 'POST', { url }), () => '');
    } finally {
      readIt.disabled = false;
    }
    if (!done.ok) return;
    const titled = titleOfDoc(done.found);
    const named = titled || IMPORT_UNTITLED;
    const body = await markdownOfDoc(done.found);
    if (!body.trim()) {
      say.say(IMPORT_EMPTY, 'warn');
      return;
    }
    if (body.length > cap) {
      say.say(NEW_OVER
        .replace('{title}', named)
        .replace('{count}', body.length.toLocaleString())
        .replace('{style}', STYLE_WORDS[importStyle] || importStyle)
        .replace('{cap}', cap.toLocaleString()), 'danger');
      return;
    }
    if (!typed || !docTitle.value.trim()) {
      docTitle.value = titled || untitled;
      typed = false;
    }
    fetched = { url, body };
    createIt.hidden = false;
    say.say(NEW_READ
      .replace('{title}', named)
      .replace('{count}', body.length.toLocaleString())
      .replace('{box}', BOX_WORDS[importStyle] || importStyle), 'ok');
  }, { tone: 'quiet', small: false });
  link.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter') return;
    event.preventDefault();
    readIt.click();
  });
  const fromDoc = el('div', { class: 'newpost-pane', id: 'new-import' }, [
    field(NEW_DOC_LINK, el('div', { class: 'docimport' }, [link, readIt])),
    field('What is it called?', docTitle),
    bar([createIt]),
  ]);
  fromDoc.hidden = true;

  const panes = { scratch, doc: fromDoc };
  const chips = chipBar([['scratch', NEW_SCRATCH], ['doc', NEW_IMPORT]], 'scratch', (key) => {
    for (const [name, pane] of Object.entries(panes)) pane.hidden = name !== key;
    say.say('');
    (key === 'doc' ? link : title).focus();
  }, { className: 'newpost-choice', role: 'group' });

  return [chips, scratch, fromDoc, say];
}

function postsSection(payload, say) {
  const rows = payload.posts.map((post) => ({ post, node: postRow(post, payload) }));
  const list = section('The posts', null, { count: payload.posts.length, open: true });
  const foot = el('div', { class: 'grid-foot' });
  const grid = el('div', { class: 'grid-table', style: 'min-width: 760px' }, [
    headRow(),
    ...rows.map((one) => one.node),
    foot,
  ]);

  const filter = listFilter({
    items: rows,
    value: (one) => one.post,
    text: postText,
    filters: FILTERS,
    filter: state.filter,
    query: state.query,
    label: 'Search the posts',
    placeholder: 'Search the posts…',
    onChange: ({ query, filter: key, shown }) => {
      state.query = query;
      state.filter = key;
      foot.textContent = shown === rows.length
        ? SHOWING_ALL.replace(/\{n\}/g, String(rows.length)).replace('{s}', plural(rows.length))
        : SHOWING_SOME
          .replace('{shown}', String(shown))
          .replace('{n}', String(rows.length))
          .replace('{s}', plural(rows.length));
    },
  });

  const newPost = button('New post', () => openDrawer('A new post', newPostDrawer(payload)), { tone: 'warn' });
  newPost.style.marginLeft = 'auto';
  filter.apply();

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
      el('div', { class: 'card-head' }, [...filter.parts, newPost]),
      payload.posts.length === 0
        ? sayNothing(NOTHING_YET)
        : el('div', { class: 'table-scroll' }, [grid]),
    ]),
    say,
  );
  return full(list.node);
}

function blockFoldMap() {
  return remembered(BLOCKS_FOLD_KEY) || {};
}

function readBlockFold(kind, fallback) {
  const found = blockFoldMap()[kind];
  return typeof found === 'boolean' ? found : fallback;
}

function writeBlockFold(kind, folded) {
  const map = blockFoldMap();
  map[kind] = folded;
  remember(BLOCKS_FOLD_KEY, map);
}

/** One card, folded to its name and badges until opened; opening is what triggers the lazy preview. */
function blockCard(kind, editorNode, defaultFolded) {
  const on = kind.on || [];
  const details = el('details', {
    class: 'card block-card',
    open: readBlockFold(kind.kind, defaultFolded) ? undefined : true,
  }, [
    el('summary', { class: 'card-head block-card-head' }, [
      icon('chevronDown', 14, 'sect-mark'),
      el('span', { class: 'block-card-name', text: kind.name }),
      el('div', { class: 'postmarks' }, [
        badge(kind.exclusive ? ONE_AT_A_TIME : ANY_NUMBER, null),
        badge(kind.where, on.length ? 'info' : null),
      ]),
    ]),
    el('div', { class: 'card-body' }, [
      on.length
        ? bar(on.map((holder) => button(
          OPEN_IT.replace('{title}', holder.title),
          () => openPost(holder.slug, holder.title),
          { tone: 'quiet' },
        )))
        : sayNothing(ON_NO_POST),
      blockLook(kind),
      editorNode ? foldout(EDIT_BLOCK.replace('{name}', kind.name), [editorNode]) : null,
    ]),
  ]);
  details.addEventListener('toggle', () => writeBlockFold(kind.kind, !details.open));
  return details;
}

function setAllBlockFolds(cards, folded) {
  for (const { node } of cards) node.open = !folded;
}

async function blocksSection(payload) {
  const kinds = payload.block_kinds || [];
  const defaultFolded = kinds.length > BLOCKS_FOLD_MANY;
  const one = section('Blocks', null, { id: 'blocks', count: kinds.length });
  const cards = [];
  for (const kind of kinds) {
    const editor = BLOCK_EDITORS[kind.kind];
    const editorNode = editor ? await editor() : null;
    cards.push({ kind, node: blockCard(kind, editorNode, defaultFolded) });
  }

  const filter = listFilter({
    items: cards,
    value: (found) => found.kind,
    text: blockText,
    filters: BLOCK_FILTERS,
    filter: blockState.filter,
    query: blockState.query,
    label: SEARCH_BLOCKS,
    placeholder: SEARCH_BLOCKS_PLACEHOLDER,
    empty: NO_BLOCK_MATCH,
    onChange: ({ query, filter: key, shown, total }) => {
      blockState.query = query;
      blockState.filter = key;
      one.count(shown === total ? total : `${shown} of ${total}`);
    },
  });
  const foldButtons = bar([
    button(FOLD_ALL, () => setAllBlockFolds(cards, true), { tone: 'quiet' }),
    button(OPEN_ALL, () => setAllBlockFolds(cards, false), { tone: 'quiet' }),
  ]);
  foldButtons.style.marginLeft = 'auto';
  filter.apply();

  one.body.append(
    card(null, [el('div', { class: 'card-head' }, [...filter.parts, foldButtons])]),
    filter.none,
    ...cards.map((found) => found.node),
  );
  return full(one.node);
}

/** The block alone, as Discord draws it from its saved words, under its card. */
function blockLook(kind) {
  const mock = blockPreview({ blocks: [kind.kind], always: true, lazy: true });
  return el('div', { class: 'field blocklook', 'data-kind': kind.kind }, [
    el('span', { class: 'field-label', text: LOOKS_LIKE }),
    el('div', { class: 'preview' }, [mock.node, mock.say]),
  ]);
}

/** A shared block demoted out of the "On this page" rail so a fold is not a place. */
function unsectioned(node) {
  const inner = node.querySelector('.sect-inner');
  return inner ? [...inner.childNodes] : [node];
}

async function machinerySection(specs) {
  const one = section('Settings and logs', null, { id: 'machinery' });
  one.body.append(
    foldout('Settings', [
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
    await blocksSection(payload),
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
