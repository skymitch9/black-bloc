import { api, listOf, names, settings, settingsNamespace } from './api.js';
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
  when,
} from './ui.js';

let refresh = () => {};

const SAMPLE = {
  '{name}': 'Casey',
  '{game}': 'Lethal Company',
  '{title}': 'late night runs',
  '{url}': 'https://twitch.tv/caseyfast',
};

function previewCard(template) {
  const filled = Object.entries(SAMPLE).reduce((text, [token, value]) => text.split(token).join(value), String(template || ''));
  return card('What an announcement looks like', [
    el('p', { class: 'field-help', text: 'Filled in with a made-up stream, so nothing here is posted anywhere.' }),
    el('p', { class: 'preview', text: filled || 'golive_template is not set, so nothing would be posted.' }),
  ]);
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

  const one = section('Twitch links');
  one.body.append(linkTable, say);
  const two = section('Opt-outs', 'These members are never announced, whatever else is set.');
  two.body.append(optoutTable);
  const three = section('Recent streams');
  three.body.append(sessionTable);

  const template = settingsNamespace(allSettings, 'golive').find((spec) => spec.key === 'golive_template');
  const four = section('Announcement wording');
  four.body.append(previewCard(template ? template.value : null));

  document.getElementById('dash').replaceChildren(
    one.node,
    two.node,
    three.node,
    four.node,
    await namespaceSettings('golive', { onSaved: () => refresh() }),
  );
}

refresh = start({
  tab: 'golive',
  subtitle: 'Twitch links, opt-outs, recent streams and the announcement wording.',
  load,
});
