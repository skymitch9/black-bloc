import { api, listOf, names, send } from './api.js';
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

async function load() {
  const payload = await api('/api/tempvoice/channels');
  const rows = listOf(payload, 'channels');
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

  document.getElementById('dash').replaceChildren(one.node, two.node, await namespaceSettings('tempvoice'));
}

refresh = start({
  tab: 'tempvoice',
  subtitle: 'The channels open right now, and the join-to-create setup.',
  load,
});
