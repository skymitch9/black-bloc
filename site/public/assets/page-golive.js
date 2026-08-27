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
  table,
  templateEditor,
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

async function wordingCard(spec, prefix, endSuffix) {
  const shown = el('p', { class: 'preview' });
  const ended = el('p', { class: 'preview' });
  const playing = el('input', { class: 'input switch', type: 'checkbox', checked: true });
  const made = await templateEditor(spec, {
    controls: [playing],
    sample: () => ({ ...SAMPLE, game: playing.checked ? SAMPLE.game : GAME_FALLBACK }),
    paint: (filled) => {
      shown.textContent = filled === null
        ? `Black Bloc would post ${DEFAULT_TEMPLATE} instead.`
        : `${prefix}${filled}`;
      ended.textContent = filled === null ? '' : `${prefix}${filled}${endSuffix}`;
    },
  });

  const preview = card('What an announcement looks like', [
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
    made.say,
  ]);
  return [made.row.node, preview, made.editor.bar];
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
  const prefix = await pingPrefix(specs);
  const suffix = specs.find((one) => one.key === 'golive_end_suffix');
  wording.body.append(...await wordingCard(spec, prefix, suffix ? String(suffix.value || '') : ''));
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
