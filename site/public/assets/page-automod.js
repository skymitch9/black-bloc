import { api, listOf, send, settings, settingsNamespace } from './api.js';
import { start } from './app.js';
import {
  bar,
  button,
  card,
  el,
  field,
  namespaceSettings,
  notice,
  run,
  sayNothing,
  searchOver,
  section,
  settingRow,
} from './ui.js';

const ACTIONS = ['delete', 'warn', 'timeout'];

let refresh = () => {};

function rulesOf(payload) {
  const found = listOf(payload, 'rules');
  if (found.length) return found;
  const rules = payload && payload.rules && !Array.isArray(payload.rules) ? payload.rules : null;
  if (!rules) return [];
  return Object.entries(rules).map(([name, rule]) => ({ name, ...rule }));
}

function ruleCard(rule) {
  const say = notice();
  const enabled = el('input', { class: 'input switch', type: 'checkbox', checked: rule.enabled ? true : undefined });
  const window = el('input', { class: 'input', type: 'number', min: '0', max: '3600', value: String(rule.window_s ?? 0) });
  const threshold = el('input', { class: 'input', type: 'number', min: '0', max: '1000', value: String(rule.threshold ?? 0) });
  const timeout = el('input', { class: 'input', type: 'number', min: '0', value: String(rule.timeout_s ?? 0) });
  const boxes = ACTIONS.map((action) => {
    const box = el('input', {
      class: 'input switch',
      type: 'checkbox',
      checked: (rule.actions || []).includes(action) ? true : undefined,
    });
    return { action, box, node: field(action, box) };
  });
  const words = Array.isArray(rule.words)
    ? el('textarea', { class: 'input area mono', rows: '4', spellcheck: 'false' })
    : null;
  if (words) words.value = (rule.words || []).join('\n');

  const save = button('Save rule', async () => {
    const body = {
      enabled: enabled.checked,
      window_s: Number(window.value),
      threshold: Number(threshold.value),
      timeout_s: Number(timeout.value),
      actions: boxes.filter((one) => one.box.checked).map((one) => one.action),
    };
    if (words) body.words = words.value.split('\n').map((word) => word.trim()).filter(Boolean);
    const done = await run(
      say,
      () => send(`/api/mod/rules/${encodeURIComponent(rule.name)}`, 'PUT', body),
      () => `Saved. ${rule.name} is ${body.enabled ? 'on' : 'off'}, ${body.threshold} in ${body.window_s}s, doing ${body.actions.join(', ') || 'nothing'}.`,
    );
    if (done.ok) refresh();
  });

  const node = card(rule.name, [
    rule.help ? el('p', { class: 'field-help', text: rule.help }) : null,
    el('div', { class: 'formrow' }, [
      field('Enabled', enabled),
      field('Window, seconds', window),
      field('Threshold', threshold),
      field('Timeout, seconds', timeout),
    ]),
    el('div', { class: 'formrow' }, boxes.map((one) => one.node)),
    words ? field('Blocked words, one per line', words) : null,
    bar([save]),
    say,
  ]);
  node.setAttribute('data-rule', rule.name);
  return node;
}

async function load() {
  const [payload, allSettings] = await Promise.all([api('/api/mod/rules'), settings(true)]);
  const rules = rulesOf(payload);
  const automod = settingsNamespace(allSettings, 'automod');
  const mode = automod.find((spec) => spec.key === 'automod_mode');
  const exempt = automod.filter((spec) => spec.key.startsWith('automod_exempt'));

  const arming = section(
    'Mode',
    'Arming automod is the one switch that starts deleting messages and timing people out. If the bot refuses, its sentence says what is missing.',
  );
  arming.body.append(mode
    ? await settingRow(mode, { onSaved: () => refresh() })
    : sayNothing('The bot did not report an automod_mode key, so this switch is not shown rather than guessed at.'));

  const book = section('Rules', 'Each rule is a burst counter: how many in how long, and what happens then.', {
    count: rules.length || null,
  });
  if (rules.length) {
    const box = el('div', { class: 'settings-grid' }, rules.map(ruleCard));
    book.body.append(
      searchOver(box, {
        label: 'Search the rule book',
        placeholder: 'a rule name, or what it does — spam, caps, invite',
        noun: 'rule(s)',
        empty: 'No rule matches what you typed.',
      }),
      box,
    );
  } else {
    book.body.append(sayNothing('Automod reports no rules at all.'));
  }

  const exemptions = section('Exemptions', 'Staff are always exempt on top of whatever is listed here.', {
    count: exempt.length || null,
  });
  for (const spec of exempt) exemptions.body.append(await settingRow(spec));
  if (exempt.length === 0) exemptions.body.append(sayNothing('No exemption keys are registered.'));

  document.getElementById('dash').replaceChildren(
    arming.node,
    book.node,
    exemptions.node,
    await namespaceSettings('automod', { title: 'All automod settings' }),
  );
}

refresh = start({
  tab: 'automod',
  load,
});
