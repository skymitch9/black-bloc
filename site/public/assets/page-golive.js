import { api, listOf, names, refRoles, send, settings, settingsNamespace } from './api.js';
import { start } from './app.js';
import {
  ask,
  badge,
  bar,
  button,
  card,
  el,
  field,
  idsIn,
  memberPicker,
  nameNode,
  namespaceSettings,
  notice,
  run,
  keepSaying,
  sayAgain,
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

/** B2: link a member to a Twitch channel without waiting for them to do it. */
function linkCard(say) {
  const picker = memberPicker({ label: 'Member' });
  const login = el('input', { class: 'input', type: 'text', placeholder: 'the name in twitch.tv/…' });
  const go = button('Link them', async () => {
    if (!picker.id) {
      say.say('Pick the member this is about first.', 'warn');
      return;
    }
    const done = await run(
      say,
      () => send('/api/golive/links', 'POST', { user_id: picker.id, twitch_login: login.value.trim() }),
      (found) => found?.message || 'Linked.',
    );
    if (done.ok) {
      keepSaying('golive.links', say);
      refresh();
    }
  }, { tone: 'warn' });
  return card('Link a member', [
    picker.node,
    el('div', { class: 'formrow' }, [field('Twitch channel', login)]),
    bar([go]),
  ]);
}

/** B1: opt somebody out, or take the opt-out away again. */
function optoutCard(say) {
  const picker = memberPicker({ label: 'Member' });
  const go = button('Opt them out', async () => {
    if (!picker.id) {
      say.say('Pick the member this is about first.', 'warn');
      return;
    }
    const done = await run(
      say,
      () => send('/api/golive/optouts', 'POST', { user_id: picker.id }),
      (found) => found?.message || 'Opted out.',
    );
    if (done.ok) {
      keepSaying('golive.optouts', say);
      refresh();
    }
  }, { tone: 'warn' });
  return card('Opt somebody out', [picker.node, bar([go])]);
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
      field('Playing a game', playing, `Off shows what an empty game reads as: “${GAME_FALLBACK}”.`),
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
        if (done.ok) {
          keepSaying('golive.links', say);
          refresh();
        }
      }, { tone: 'danger' }),
    },
  ], links, { empty: 'Nobody has linked a Twitch account.' });

  const optoutSay = notice();
  const optoutTable = table([
    { label: 'Member', cell: (row) => nameNode(row.user_id, row.user_name) },
    { label: 'Since', cell: (row) => when(row.at), className: 'mono' },
    {
      label: '',
      cell: (row) => button('Announce them again', async () => {
        const done = await run(
          optoutSay,
          () => api(`/api/golive/optouts/${encodeURIComponent(row.user_id)}`, { method: 'DELETE' }),
          (found) => found?.message || 'The opt-out is gone.',
        );
        if (done.ok) {
          keepSaying('golive.optouts', optoutSay);
          refresh();
        }
      }, { tone: 'quiet' }),
    },
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
  one.body.append(linkTable, linkCard(say), sayAgain('golive.links', say));
  const two = section('Opt-outs', 'These members are never announced, whatever else is set.', {
    count: optouts.length,
  });
  two.body.append(optoutTable, optoutCard(optoutSay), sayAgain('golive.optouts', optoutSay));
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
