import { api, listOf, names, refChannels, send, settings, settingsNamespace } from './api.js';
import { start } from './app.js';
import {
  ask,
  bar,
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

const CREATOR_KEY = 'tempvoice_creator_ids';

/** The lobby line: the join-to-create channels by name, each with a Forget. */
async function lobbyLine(ids, say) {
  const line = el('p', { class: 'field-help' }, ['Lobby: ']);
  if (ids.length === 0) {
    line.append(el('span', { class: 'muted', text: 'none yet' }));
    return line;
  }
  let channels = [];
  try {
    channels = await refChannels();
  } catch (e) {
    channels = [];
  }
  ids.forEach((id, at) => {
    const found = channels.find((one) => String(one.id) === String(id));
    if (at > 0) line.append(', ');
    line.append(el('span', { class: 'name', title: `Discord id ${id}`, text: found ? `#${found.name}` : String(id) }));
    line.append(' ', button('Forget', async () => {
      const sure = await ask({
        title: `Forget ${found ? `#${found.name}` : id}?`,
        body: ['Joining it stops making anybody a temporary channel. The channel itself is left alone, and setup can adopt it again.'],
        confirmLabel: 'Forget it',
      });
      if (!sure) return;
      const done = await run(
        say,
        () => send('/api/tempvoice/forget', 'POST', { channel_id: String(id) }),
        (found2) => found2.message || 'Forgotten.',
      );
      if (done.ok) refresh();
    }, { tone: 'danger' }));
  });
  return line;
}

async function load() {
  const [payload, allSettings] = await Promise.all([
    api('/api/tempvoice/channels'),
    settings(true),
  ]);
  const rows = listOf(payload, 'channels');
  const creators = settingsNamespace(allSettings, 'tempvoice')
    .find((spec) => spec.key === CREATOR_KEY);
  const lobbies = (creators && creators.value) || [];
  await names(idsIn(rows, ['channel_id', 'owner_id', 'creator_id']));

  const say = notice();

  const list = table([
    { label: 'Channel', cell: (row) => nameNode(row.channel_id, row.name) },
    { label: 'Owner', cell: (row) => nameNode(row.owner_id, row.owner_name) },
    { label: 'Made from', cell: (row) => nameNode(row.creator_id, row.creator_name) },
    { label: 'Since', cell: (row) => when(row.created_at), className: 'mono' },
  ], rows, { empty: 'No temporary channels are open right now.' });

  const setup = card('Setup and repair', [
    el('p', { class: 'field-help', text: 'Makes the join-to-create channel if it is missing and puts back the permissions it needs. Safe to run twice; it does not delete anybody’s channel.' }),
    await lobbyLine(lobbies, say),
    bar([
      button('Run setup', async () => {
        const sure = await ask({
          title: 'Run temp voice setup?',
          body: ['This creates or repairs the join-to-create channel in Discord.'],
          confirmLabel: 'Run it',
          tone: 'warn',
        });
        if (!sure) return;
        const done = await run(say, () => send('/api/tempvoice/setup', 'POST', {}), 'Setup ran. The channel list below is refreshed.');
        if (done.ok) refresh();
      }, { tone: 'warn', small: false }),
    ]),
    say,
  ]);

  const one = section('Open now', 'These are live from Discord, not a stored guess.', {
    count: rows.length,
  });
  one.body.append(list);
  const two = section('Setup');
  two.body.append(setup);

  document.getElementById('dash').replaceChildren(
    one.node,
    two.node,
    await namespaceSettings('tempvoice', { omit: [CREATOR_KEY] }),
  );
}

refresh = start({
  tab: 'tempvoice',
  load,
});
