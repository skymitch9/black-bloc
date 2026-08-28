import { api, listOf, names, send } from './api.js';
import { start } from './app.js';
import { logsSection } from './logs.js';
import {
  ask,
  badge,
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

function actionBadge(action) {
  const text = String(action || 'logged');
  if (text.startsWith('would_')) return badge(text, 'warn');
  if (text.includes('failed')) return badge(text, 'danger');
  return badge(text, 'ok');
}

async function load() {
  const payload = await api('/api/honeypot/hits?limit=50');
  const rows = listOf(payload, 'hits');
  await names(idsIn(rows, ['user_id', 'channel_id']));

  const say = notice();

  const list = table([
    { label: 'When', cell: (row) => when(row.at), className: 'mono' },
    { label: 'Member', cell: (row) => nameNode(row.user_id, row.user_name) },
    { label: 'Trap', cell: (row) => nameNode(row.channel_id, row.channel_name) },
    { label: 'Mode then', cell: (row) => badge(row.mode, row.mode === 'on' ? 'ok' : 'warn') },
    { label: 'What happened', cell: (row) => actionBadge(row.action) },
    { label: 'They posted', cell: (row) => row.content, className: 'wrap' },
    {
      label: '',
      cell: (row) => (String(row.action || '').startsWith('would_')
        ? button('Ban now', async () => {
          const sure = await ask({
            title: `Ban ${row.user_name || row.user_id}?`,
            body: [
              'This is the same ban the trap would have carried out: the account is banned and honeypot_purge_days of its messages go with it.',
              'It cannot be undone from here — an unban is a moderation action.',
            ],
            confirmLabel: 'Ban them',
          });
          if (!sure) return;
          const done = await run(say, () => send(`/api/honeypot/hits/${encodeURIComponent(row.id)}/ban`, 'POST', {}), 'Banned.');
          if (done.ok) refresh();
        }, { tone: 'danger' })
        : null),
    },
  ], rows, { empty: 'Nobody has walked into a trap channel.' });

  const setup = card('Setup', [
    el('p', { class: 'field-help', text: 'Safe to run twice; nobody is let into the trap by it.' }),
    bar([
      button('Run setup', async () => {
        const sure = await ask({
          title: 'Run honeypot setup?',
          body: ['This creates or repairs the trap channel in Discord.'],
          confirmLabel: 'Run it',
          tone: 'warn',
        });
        if (!sure) return;
        const done = await run(say, () => send('/api/honeypot/setup', 'POST', {}), 'Setup ran.');
        if (done.ok) refresh();
      }, { tone: 'warn', small: false }),
    ]),
  ]);

  const one = section(
    'Hits',
    'In shadow the trap only writes down what it would have done; Ban now is how a shadow hit gets carried out.',
    { count: rows.length },
  );
  one.body.append(list, say);
  const two = section('Trap channels');
  two.body.append(setup);

  document.getElementById('dash').replaceChildren(
    one.node,
    two.node,
    await namespaceSettings('honeypot'),
    await logsSection('honeypot'),
  );
}

refresh = start({
  tab: 'honeypot',
  load,
});
