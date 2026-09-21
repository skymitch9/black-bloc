import { api, refChannels, refMembers, refRoles, send, settings, settingsNamespace } from './api.js';
import { start } from './app.js';
import { htmlToDiscordMarkdown } from './clipmd.js';
import { renderPreview } from './discordmd.js';
import { logsSection } from './logs.js';
import { VIEWING, useItQuestion, versionsFoldout } from './postversions.js';
import {
  ago,
  ask,
  badge,
  bar,
  button,
  card,
  channelSelect,
  el,
  field,
  keepSaying,
  modeSwitch,
  notice,
  openDrawer,
  readSelect,
  run,
  saveBar,
  sayAgain,
  sayNothing,
  section,
  sentenceFor,
  settingsPanel,
  textAction,
} from './ui.js';

const MODE_KEY = 'posts_mode';
const SETTING_KEYS = [MODE_KEY, 'posts_panel_minutes', 'posts_log_level'];
const SETTINGS_NOTE = 'Whether staff may post at all, how long the /posts panel stays live, and '
  + 'how much of it is repeated into the Discord log.';
const LIST_NOTE = 'One message per post. Black Bloc sends it once and edits that same message '
  + 'every time after — it never posts a second copy.';
const NOTHING_YET = 'There are no posts yet.';
const NO_BODY = 'Nothing is written in this one yet.';
const NO_CHANNEL = 'no channel yet';
const AMBER_AT = 0.9;
const PREVIEW_EVERY_MS = 60;
const NEED_A_TITLE = 'A post needs a title. Type one and press Make it again.';
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
// is about what Discord shows. These three are the dashboard talking to staff.
const PASTE_HINT = 'Paste keeps formatting';
const PASTE_KEPT = 'Pasted with formatting kept (headings, bold, bullets, links). '
  + 'Undo with Ctrl+Z.';
const PASTE_DISMISS = 'Dismiss';
const DELETE_QUESTION = 'Every word goes with it. Nothing puts it back.';
const USE_IT_CONFIRM = 'Use version {n}';
const VERSIONS_UNREADABLE = 'The version history could not be read just now. Everything else on '
  + 'this page still works — try again in a moment, and tell a Lead if it keeps happening.';
// Rule 3 of the owner's ask: Post it with unsaved edits saves first, so what goes out is
// always a version. The sentence under the button says both.
const WILL_POST_SAVED = 'Post it saves your changes first, then sends this to {where} as '
  + '{style} and {pin}.';
const WILL_UPDATE_SAVED = 'Update the post saves your changes first, then edits the message '
  + 'already in {where}, as {style} and {pin}.';

const state = { refs: null };
let refresh = () => {};

function full(node) {
  node.setAttribute('data-span', 'full');
  return node;
}

function wantedSlug() {
  const hash = String(location.hash || '').replace(/^#/, '').trim();
  return hash || null;
}

function goTo(slug) {
  const wanted = slug ? `#${slug}` : ' ';
  if (slug) location.hash = wanted;
  else history.replaceState(null, '', location.pathname);
  refresh();
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

function statusPills(row) {
  return row.status.map((word) => badge(word, word === 'changes not yet posted' ? 'warn' : 'quiet'));
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
  const where = rehearsal ? shadowWords(shadow) : whereWords(row);
  return line.replace('{where}', where) + (row.pin ? PINNED_TOO : NOT_PINNED);
}

function listCard(row, shadow) {
  return el('div', { class: 'row', 'data-tone': row.changes_pending ? 'warn' : undefined }, [
    el('span', { class: 'dot' }),
    el('div', { class: 'row-body' }, [
      el('div', { class: 'row-head' }, [
        el('button', {
          class: 'row-name link',
          type: 'button',
          text: row.title,
          on: { click: () => goTo(row.slug) },
        }),
        ...statusPills(row),
      ]),
      el('p', { class: 'row-detail', text: postedLine(row, shadow) }),
      el('p', {
        class: 'row-note',
        text: `${row.body ? `${row.body.slice(0, 160)}${row.body.length > 160 ? '…' : ''}` : NO_BODY}`,
      }),
      el('p', {
        class: 'row-note',
        title: ago(row.updated_at).title,
        text: `Last saved ${ago(row.updated_at).text}${row.updated_by_name ? ` by ${row.updated_by_name}` : ''}.`,
      }),
    ]),
  ]);
}

function newPostCard(say) {
  const title = el('input', { class: 'input', type: 'text', placeholder: 'Welcome and rules' });
  const make = button('Make it', async () => {
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
    goTo(done.found.post.slug);
  }, { tone: 'warn' });
  return card('A new post', [
    el('div', { class: 'formrow' }, [
      field('What is it called?', title, 'The title staff see here, and the embed title if you '
        + 'set the style to an embed.'),
    ]),
    bar([make]),
    say,
  ]);
}

function guardNote(payload) {
  return payload.guard && payload.guard.said ? notice(payload.guard.said, 'warn') : null;
}

async function loadList(payload) {
  const holder = document.getElementById('dash');
  const say = sayAgain('posts', notice());
  const specs = settingsNamespace(await settings(), 'posts')
    .filter((spec) => SETTING_KEYS.includes(spec.key));
  const mode = specs.find((one) => one.key === MODE_KEY);
  const head = document.getElementById('page-aside');
  if (head) {
    head.replaceChildren(mode ? modeSwitch(mode, { onSaved: () => refresh() }).node : el('span'));
  }

  const list = section('The posts', LIST_NOTE, { count: payload.posts.length, open: true });
  list.body.append(
    ...(payload.posts.length
      ? payload.posts.map((row) => listCard(row, payload.shadow))
      : [sayNothing(NOTHING_YET)]),
  );

  const options = section('Settings', SETTINGS_NOTE, { count: specs.length });
  options.body.append(await settingsPanel(specs, { where: 'Posts', onSaved: () => refresh() }));

  holder.replaceChildren(
    ...(payload.notes || []).map((line) => notice(line, 'warn')),
    guardNote(payload),
    say,
    list.node,
    newPostCard(notice()),
    options.node,
    await logsSection('posts'),
  );
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

function willPost(draft, post, payload, dirty = false) {
  if (payload.mode === SHADOW) {
    const where = shadowWords(payload.shadow);
    if (!draft.channel_id) return WILL_SHADOW_NOWHERE.replace('{shadow}', where);
    if (payload.shadow && String(draft.channel_id) === String(payload.shadow.channel_id)) {
      return WILL_SHADOW_SAME.replace('{shadow}', where);
    }
    return WILL_SHADOW
      .replace('{shadow}', where)
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

async function editor(payload, known, history) {
  const post = payload.post;
  const draft = draftOf(post);
  const was = draftOf(post);
  const say = sayAgain('post', notice());
  const dock = saveBar(() => write(), () => discard(), { where: post.title });
  const refreshBar = () => dock.say(changeCount(draft, was));

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

  const box = el('textarea', { class: 'input area postbox', id: 'post-body', rows: '18', spellcheck: 'true' });
  box.value = draft.body;
  const pasteNote = pasteNoteNode();
  const counter = counterNode();
  const preview = el('div', { class: 'preview', id: 'post-preview' });
  const howLine = el('p', { class: 'field-help', id: 'post-how' });

  const capOf = () => (payload.styles.find((one) => one.style === draft.style) || { cap: 2000 }).cap;

  let timer = null;
  const paintPreview = () => {
    preview.innerHTML = renderPreview(draft.body, {
      style: draft.style,
      title: draft.title,
      channels: known.channels,
      roles: known.roles,
      members: known.members,
    });
    counter.paint(draft.body.length, capOf());
    howLine.textContent = willPost(draft, post, payload, Boolean(changeCount(draft, was)));
  };
  const schedule = () => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(paintPreview, PREVIEW_EVERY_MS);
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

  const discard = () => {
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

  const saveDraft = () => send(`/api/posts/${encodeURIComponent(post.slug)}`, 'PUT', {
    title: draft.title.trim(),
    body: draft.body,
    style: draft.style,
    pin: draft.pin,
    channel_id: draft.channel_id || null,
  });

  const write = async () => {
    if (draft.body.length > capOf()) {
      dock.say(0, 'Nothing was saved — the box is over its limit.', 'danger');
      return;
    }
    dock.say(0, 'Saving…', 'info');
    try {
      const found = await saveDraft();
      say.say(found?.message || 'Saved.', 'ok');
      keepSaying('post', say);
      refresh();
    } catch (error) {
      const said = sentenceFor(error);
      dock.say(0, 'Nothing was saved — the sentence is beside the box.', 'danger');
      say.say(said.text, said.tone);
    }
  };

  const move = (label, path, tone) => button(label, async () => {
    const done = await run(
      say,
      () => send(`/api/posts/${encodeURIComponent(post.slug)}/${path}`, 'POST', {}),
      (found) => found?.message || 'Done.',
    );
    if (!done.ok) return;
    keepSaying('post', say);
    refresh();
  }, { tone });

  /** Rule 3: a dirty editor is SAVED first, so what went out is always a version. */
  const publish = () => button(post.move, async () => {
    const done = await run(
      say,
      async () => {
        if (changeCount(draft, was)) await saveDraft();
        return send(`/api/posts/${encodeURIComponent(post.slug)}/publish`, 'POST', {});
      },
      (found) => found?.message || 'Done.',
    );
    if (!done.ok) return;
    keepSaying('post', say);
    refresh();
  }, { tone: 'warn' });

  const viewVersion = async (version) => {
    const found = await run(
      say,
      () => api(`/api/posts/${encodeURIComponent(post.slug)}/versions/${version.n}`),
      () => '',
    );
    if (!found.ok) return;
    const drawn = el('div', { class: 'preview' });
    drawn.innerHTML = renderPreview(found.found.preview.body, {
      style: found.found.preview.style,
      title: found.found.preview.title,
      channels: known.channels,
      roles: known.roles,
      members: known.members,
    });
    openDrawer(VIEWING.replace('{n}', String(version.n)).replace('{title}', post.title), [drawn]);
  };

  const useVersion = async (version) => {
    const top = (history && history.versions && history.versions.length)
      ? Number(history.versions[0].n) : Number(version.n);
    const sure = await ask({
      title: `Use version ${version.n} of “${post.title}”?`,
      body: [useItQuestion(version, top + 1)],
      confirmLabel: USE_IT_CONFIRM.replace('{n}', String(version.n)),
      tone: 'warn',
    });
    if (!sure) return;
    const done = await run(
      say,
      () => send(
        `/api/posts/${encodeURIComponent(post.slug)}/versions/${version.n}/restore`, 'POST', {},
      ),
      (found) => found?.message || 'Put back.',
    );
    if (!done.ok) return;
    keepSaying('post', say);
    refresh();
  };

  const versions = history === null
    ? notice(VERSIONS_UNREADABLE, 'warn')
    : versionsFoldout(history.versions, { onView: viewVersion, onUse: useVersion });

  const buttons = [publish()];
  if (post.posted) buttons.push(move('Take it down', 'takedown', 'quiet'));
  if (!post.seeded) {
    buttons.push(button('Delete this post', async () => {
      const sure = await ask({
        title: `Delete “${post.title}”?`,
        body: [DELETE_QUESTION],
        confirmLabel: 'Delete it',
      });
      if (!sure) return;
      const done = await run(
        say,
        () => api(`/api/posts/${encodeURIComponent(post.slug)}`, { method: 'DELETE' }),
        (found) => found?.message || 'Gone.',
      );
      if (!done.ok) return;
      keepSaying('posts', say);
      goTo(null);
    }, { tone: 'danger' }));
  }

  paintPreview();
  refreshBar();

  const head = document.getElementById('page-aside');
  if (head) {
    head.replaceChildren(button('All the posts', () => goTo(null), { tone: 'quiet', small: false }));
  }

  return [
    ...(payload.notes || []).map((line) => notice(line, 'warn')),
    guardNote(payload),
    full(el('div', { class: 'posthead' }, [
      el('button', {
        class: 'crumb link',
        type: 'button',
        text: '← All the posts',
        on: { click: () => goTo(null) },
      }),
      el('h2', { class: 'posttitle', text: post.title }),
      el('div', { class: 'postmarks' }, statusPills(post)),
    ])),
    full(card('What it says', [
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
      bar(buttons),
      say,
      versions,
    ])),
  ];
}

async function loadPost(slug) {
  const holder = document.getElementById('dash');
  let payload = null;
  try {
    payload = await api(`/api/posts/${encodeURIComponent(slug)}`);
  } catch (error) {
    const said = sentenceFor(error);
    holder.replaceChildren(
      el('p', { class: 'notice', 'data-tone': said.tone, text: said.text }),
      sayNothing('Pick a post from the list.', textAction('All the posts', () => goTo(null))),
    );
    return;
  }
  let history = null;
  try {
    history = await api(`/api/posts/${encodeURIComponent(slug)}/versions`);
  } catch (error) {
    history = null;
  }
  holder.replaceChildren(...(await editor(payload, await refs(), history)));
}

async function load() {
  const slug = wantedSlug();
  if (slug) return loadPost(slug);
  return loadList(await api('/api/posts'));
}

window.addEventListener('hashchange', () => refresh());

refresh = start({ tab: 'posts', load });
