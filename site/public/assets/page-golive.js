import { api, listOf, names, refRoles, settings, settingsNamespace } from './api.js';
import { start } from './app.js';
import {
  ask,
  badge,
  button,
  card,
  el,
  idsIn,
  nameNode,
  namespaceSettings,
  notice,
  run,
  section,
  settingsEditor,
  table,
  when,
} from './ui.js';

let refresh = () => {};

const TEMPLATE_KEY = 'golive_template';
const PING_KEY = 'golive_ping_role_id';
const GAME_FALLBACK = 'something';
const DEFAULT_TEMPLATE = 'the default wording';

const SAMPLE = {
  name: 'Casey',
  game: 'Lethal Company',
  title: 'late night runs',
  url: 'https://twitch.tv/caseyfast',
  platform: 'Twitch',
};

const TOKEN = /\{\{|\}\}|\{([^{}]*)\}/g;

/**
 * The same answer `black_bloc/golive.py:render` gives: known tokens are
 * filled in, an unknown one survives literally, and a template Python's
 * format_map could not read at all comes back null so the caller can say the
 * default would be posted instead of pretending this wording works.
 */
function fill(template, values) {
  const text = String(template === null || template === undefined ? '' : template);
  if (/[{}]/.test(text.replace(TOKEN, ''))) return null;
  return text.replace(TOKEN, (whole, token) => {
    if (whole === '{{') return '{';
    if (whole === '}}') return '}';
    return token in values ? values[token] : whole;
  });
}

async function pingPrefix(specs) {
  const spec = specs.find((one) => one.key === PING_KEY);
  if (!spec || !spec.value) return '';
  try {
    const role = (await refRoles()).find((one) => String(one.id) === String(spec.value));
    return role ? `@${role.name} ` : `@${spec.value} `;
  } catch (e) {
    return `@${spec.value} `;
  }
}

function wordingCard(row, prefix, endSuffix) {
  const say = notice();
  const shown = el('p', { class: 'preview' });
  const ended = el('p', { class: 'preview' });
  const playing = el('input', { class: 'input switch', type: 'checkbox', checked: true });
  const values = () => ({ ...SAMPLE, game: playing.checked ? SAMPLE.game : GAME_FALLBACK });

  const paint = () => {
    const found = row.read();
    const filled = found.ok ? fill(found.value, values()) : null;
    if (filled === null) {
      shown.textContent = `Black Bloc cannot read this wording, so it would post ${DEFAULT_TEMPLATE} instead.`;
      ended.textContent = '';
      say.say('Every { needs a matching }. Empty the box to put the wording back to its default.', 'warn');
      return;
    }
    shown.textContent = `${prefix}${filled}`;
    ended.textContent = `${prefix}${filled}${endSuffix}`;
    say.say('');
  };

  const control = row.node.querySelector('.setrow-control');
  if (control) {
    control.addEventListener('input', paint);
    control.addEventListener('change', paint);
  }
  playing.addEventListener('change', paint);
  paint();

  return card('What an announcement looks like', [
    el('div', { class: 'formrow' }, [
      el('div', { class: 'field' }, [
        el('label', { class: 'field-label', text: 'Playing a game' }),
        playing,
        el('p', { class: 'field-help', text: `Off shows what an empty game reads as: “${GAME_FALLBACK}”.` }),
      ]),
    ]),
    shown,
    el('p', { class: 'field-help', text: 'And once the stream has ended:' }),
    ended,
    say,
  ]);
}

async function wordingSection(specs) {
  const wording = section('Announcement wording');
  const spec = specs.find((one) => one.key === TEMPLATE_KEY);
  if (!spec) {
    wording.body.append(el('p', {
      class: 'say-nothing',
      text: 'The bot did not report a golive_template key, so this editor is not shown rather than guessed at.',
    }));
    return wording.node;
  }
  const editor = await settingsEditor([{ ...spec, type: 'longtext' }]);
  const prefix = await pingPrefix(specs);
  const suffix = specs.find((one) => one.key === 'golive_end_suffix');
  wording.body.append(
    editor.rows[0].node,
    wordingCard(editor.rows[0], prefix, suffix ? String(suffix.value || '') : ''),
    editor.bar,
  );
  return wording.node;
}

async function load() {
  const [linkPayload, optoutPayload, sessionPayload, allSettings] = await Promise.all([
    api('/api/golive/links'),
    api('/api/golive/optouts'),
    api('/api/golive/sessions?limit=50'),
    settings(true),
  ]);
  const links = listOf(linkPayload, 'links');
  const optouts = listOf(optoutPayload, 'optouts');
  const sessions = listOf(sessionPayload, 'sessions');
  await names(idsIn(links, ['user_id']).concat(idsIn(optouts, ['user_id'])).concat(idsIn(sessions, ['user_id'])));

  const say = notice();

  const linkTable = table([
    { label: 'Member', cell: (row) => nameNode(row.user_id, row.user_name) },
    { label: 'Twitch', cell: (row) => row.twitch_login, className: 'mono' },
    { label: 'Linked', cell: (row) => when(row.linked_at), className: 'mono' },
    {
      label: '',
      cell: (row) => button('Unlink', async () => {
        const sure = await ask({
          title: `Unlink ${row.user_name || row.user_id}?`,
          body: [`Black Bloc stops watching twitch.tv/${row.twitch_login} for them. They can link it again themselves.`],
          confirmLabel: 'Unlink',
        });
        if (!sure) return;
        const done = await run(say, () => api(`/api/golive/links/${encodeURIComponent(row.user_id)}`, { method: 'DELETE' }), 'Unlinked.');
        if (done.ok) refresh();
      }, { tone: 'danger' }),
    },
  ], links, { empty: 'Nobody has linked a Twitch account.' });

  const optoutTable = table([
    { label: 'Member', cell: (row) => nameNode(row.user_id, row.user_name) },
    { label: 'Since', cell: (row) => when(row.at), className: 'mono' },
  ], optouts, { empty: 'Nobody has opted out.' });

  const sessionTable = table([
    { label: 'Member', cell: (row) => nameNode(row.user_id, row.user_name) },
    { label: 'Started', cell: (row) => when(row.started_at), className: 'mono' },
    { label: 'Ended', cell: (row) => (row.ended_at ? when(row.ended_at) : badge('live now', 'ok')), className: 'mono' },
    { label: 'Game', cell: (row) => row.game },
    { label: 'Title', cell: (row) => row.title, className: 'wrap' },
    { label: 'How', cell: (row) => row.source },
    { label: 'Mode then', cell: (row) => badge(row.mode, row.mode === 'on' ? 'ok' : 'warn') },
  ], sessions, { empty: 'No streams have been seen yet.' });

  const one = section('Twitch links', null, { count: links.length });
  one.body.append(linkTable, say);
  const two = section('Opt-outs', 'These members are never announced, whatever else is set.', {
    count: optouts.length,
  });
  two.body.append(optoutTable);
  const three = section('Recent streams', null, { count: sessions.length });
  three.body.append(sessionTable);

  const golive = settingsNamespace(allSettings, 'golive');

  document.getElementById('dash').replaceChildren(
    one.node,
    two.node,
    three.node,
    await wordingSection(golive),
    await namespaceSettings('golive', { onSaved: () => refresh(), omit: [TEMPLATE_KEY] }),
  );
}

refresh = start({
  tab: 'golive',
  load,
});
