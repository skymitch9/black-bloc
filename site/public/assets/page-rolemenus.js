import { api, listOf, names, refRoles, saveSetting, send, settings, settingsNamespace } from './api.js';
import { start } from './app.js';
import {
  ask,
  badge,
  bar,
  button,
  card,
  channelSelect,
  el,
  field,
  idsIn,
  modeChip,
  nameNode,
  notice,
  readSelect,
  roleSelect,
  run,
  sayNothing,
  searchOver,
  section,
  settingsPanel,
  table,
} from './ui.js';

const MODE_KEY = 'rolemenu_mode';
const DEFAULT_CHANNEL_KEY = 'role_menu_channel_id';
const SWITCH_HELP = 'Off takes the panels down and hides the /rolemenu commands; on posts every ' +
  'menu again, and nobody loses a role either way.';
const TURNED_ON = 'On. Every menu that has a channel is posted there again, and the /rolemenu ' +
  'commands come back, within about five seconds.';
const TURNED_OFF = 'Off. The posted panels are removed and the /rolemenu commands disappear from ' +
  'Discord within about five seconds. Nobody loses a role and no menu is changed.';
const NO_KEY = 'The bot did not report a rolemenu_mode key, so this switch is not shown rather ' +
  'than guessed at.';

const state = { editing: null, creating: false };

let refresh = () => {};

function modeSwitch(spec) {
  const say = notice();
  const chip = modeChip(spec.value);
  let now = spec.value === 'on' ? 'on' : 'off';

  const flip = async (wanted) => {
    if (wanted === now) return;
    const done = await run(say, () => saveSetting(MODE_KEY, wanted), wanted === 'on' ? TURNED_ON : TURNED_OFF);
    if (done.ok) paint(done.found && done.found.value ? done.found.value : wanted);
  };

  const on = button('Turn on', () => flip('on'), { small: false });
  const off = button('Turn off', () => flip('off'), { small: false, tone: 'warn' });

  function paint(value) {
    now = value === 'on' ? 'on' : 'off';
    chip.textContent = now;
    chip.setAttribute('data-mode', now);
    on.disabled = now === 'on';
    off.disabled = now === 'off';
  }
  paint(spec.value);

  return card('Members picking roles', [
    field('Now', chip, spec.help || null),
    bar([on, off]),
    say,
  ]);
}

async function optionRow(option) {
  const role = await roleSelect(option ? option.role_id : null);
  const label = el('input', { class: 'input', type: 'text', value: option ? option.label || '' : '' });
  const emoji = el('input', { class: 'input', type: 'text', value: option ? option.emoji || '' : '', placeholder: '🔴 or <:name:id>' });
  const node = el('div', { class: 'formrow' }, [
    field('Role', role),
    field('Label', label),
    field('Emoji', emoji),
    bar([button('Remove', () => node.remove(), { tone: 'quiet' })]),
  ]);
  return {
    node,
    read: () => {
      const roleId = readSelect(role, false);
      if (!roleId) return null;
      return { role_id: roleId, label: label.value.trim() || null, emoji: emoji.value.trim() || null };
    },
  };
}

async function editor(menu) {
  const say = notice();
  const name = el('input', { class: 'input', type: 'text', value: menu ? menu.name : '', disabled: menu ? true : undefined });
  const title = el('input', { class: 'input', type: 'text', value: menu ? menu.title || '' : '' });
  const description = el('input', { class: 'input', type: 'text', value: menu ? menu.description || '' : '' });
  const mode = el('select', { class: 'input' });
  for (const one of ['multiple', 'single', 'staff']) {
    mode.append(el('option', { value: one, text: one, selected: menu && menu.mode === one ? true : undefined }));
  }

  const options = [];
  const list = el('div');
  const addOption = async (option) => {
    const made = await optionRow(option);
    options.push(made);
    list.append(made.node);
  };
  for (const option of (menu && menu.options) || []) await addOption(option);
  if (!menu) await addOption(null);

  const save = button(menu ? 'Save menu' : 'Create menu', async () => {
    const body = {
      title: title.value.trim(),
      description: description.value.trim() || null,
      mode: mode.value,
      options: options.map((one) => one.read()).filter(Boolean),
    };
    if (!menu) body.name = name.value.trim();
    const done = await run(
      say,
      () => (menu
        ? send(`/api/rolemenus/${encodeURIComponent(menu.name)}`, 'PUT', body)
        : send('/api/rolemenus', 'POST', body)),
      (found) => `Saved ${found?.name || body.name || menu.name} with ${body.options.length} option(s). Post it again for the change to show in Discord.`,
    );
    if (done.ok) {
      state.editing = null;
      state.creating = false;
      refresh();
    }
  }, { small: false });

  const close = button('Close editor', () => {
    state.editing = null;
    state.creating = false;
    refresh();
  }, { tone: 'quiet' });

  return card(menu ? `Editing ${menu.name}` : 'New menu', [
    el('div', { class: 'formrow' }, [
      field('Name', name, menu ? 'A menu keeps its name for life; make a new one to rename it.' : 'Short, no spaces — this is how the slash commands find it.'),
      field('Title', title),
      field('Description', description),
      field('Mode', mode),
    ]),
    el('h3', { text: 'Options' }),
    list,
    bar([button('Add option', () => addOption(null), { tone: 'quiet' })]),
    say,
  ], { actions: [save, close] });
}

async function postCard(menu, say) {
  const where = await channelSelect(menu.channel_id);
  return el('div', { class: 'formrow' }, [
    field('Post in', where),
    bar([
      button('Post', async () => {
        const channelId = readSelect(where, false);
        if (!channelId) {
          say.say('Pick a channel to post it in.', 'warn');
          return;
        }
        const sure = await ask({
          title: `Post ${menu.name}?`,
          body: [menu.message_id
            ? 'This posts a new message. The old one stops handing out roles once this one exists.'
            : 'This posts the menu where people can click it and get roles.'],
          confirmLabel: 'Post it',
          tone: 'warn',
        });
        if (!sure) return;
        const done = await run(say, () => send(`/api/rolemenus/${encodeURIComponent(menu.name)}/post`, 'POST', { channel_id: channelId }), 'Posted.');
        if (done.ok) refresh();
      }, { tone: 'warn' }),
    ]),
  ]);
}

async function load() {
  const [payload, , allSettings] = await Promise.all([api('/api/rolemenus'), refRoles(), settings(true)]);
  const menus = listOf(payload, 'rolemenus');
  const rolemenu = settingsNamespace(allSettings, 'rolemenu');
  const mode = rolemenu.find((spec) => spec.key === MODE_KEY);
  const defaultChannel = settingsNamespace(allSettings, 'core')
    .find((spec) => spec.key === DEFAULT_CHANNEL_KEY);
  const settingSpecs = (defaultChannel ? [defaultChannel] : [])
    .concat(rolemenu.filter((spec) => spec.key !== MODE_KEY));
  const optionIds = [];
  for (const menu of menus) for (const option of menu.options || []) optionIds.push(option.role_id);
  await names(idsIn(menus, ['channel_id']).concat(optionIds));

  const say = notice();

  const list = table([
    { label: 'Name', cell: (row) => el('span', { class: 'mono', text: row.name }) },
    { label: 'Title', cell: (row) => row.title, className: 'wrap' },
    { label: 'Mode', cell: (row) => badge(row.mode) },
    {
      label: 'Options',
      cell: (row) => {
        const parts = [];
        (row.options || []).forEach((option, at) => {
          if (at > 0) parts.push(', ');
          parts.push(nameNode(option.role_id, option.role_name));
        });
        return parts.length ? el('span', {}, parts) : null;
      },
      className: 'wrap',
    },
    { label: 'Posted in', cell: (row) => (row.message_id ? nameNode(row.channel_id, row.channel_name) : badge('not posted', 'warn')) },
    {
      label: '',
      cell: (row) => el('div', { class: 'bar' }, [
        button('Edit', () => {
          state.editing = row.name;
          state.creating = false;
          refresh();
        }, { tone: 'quiet' }),
        button('Delete', async () => {
          const sure = await ask({
            title: `Delete ${row.name}?`,
            body: ['The menu and its options are removed. A message already posted stops working; nobody loses a role they already have.'],
            confirmLabel: 'Delete it',
          });
          if (!sure) return;
          const done = await run(say, () => api(`/api/rolemenus/${encodeURIComponent(row.name)}`, { method: 'DELETE' }), 'Deleted.');
          if (done.ok) refresh();
        }, { tone: 'danger' }),
      ]),
    },
  ], menus, { empty: 'No role menus exist yet.' });

  const one = section('Menus', null, { count: menus.length });
  one.body.append(
    bar([
      button('New menu', () => {
        state.creating = true;
        state.editing = null;
        refresh();
      }, { small: false }),
    ], { sticky: true }),
    list,
    say,
  );

  const two = section('Post a menu', 'Posting again makes a new message; the old one stops handing out roles.', {
    count: menus.length || null,
  });
  if (menus.length === 0) {
    two.body.append(sayNothing('There is no menu to post yet.'));
  } else {
    const box = el('div', { class: 'section-body' });
    for (const menu of menus) box.append(card(`Post ${menu.name}`, [await postCard(menu, say)]));
    two.body.append(
      searchOver(box, {
        label: 'Search the menus',
        placeholder: 'part of a menu name',
        noun: 'menu(s)',
        empty: 'No menu matches what you typed.',
      }),
      box,
    );
  }

  const switchboard = section('Role selection', SWITCH_HELP);
  switchboard.body.append(mode ? modeSwitch(mode) : sayNothing(NO_KEY));

  const box = section('Settings', 'Where a menu goes when /rolemenu post is not given a channel.', {
    count: settingSpecs.length || null,
  });
  box.body.append(await settingsPanel(settingSpecs, {
    empty: 'The bot registers no role-menu settings beyond the switch above.',
  }));

  const nodes = [switchboard.node, one.node, two.node, box.node];
  if (state.creating) {
    const made = section('New menu', null, { id: 'editor', open: true });
    made.body.append(await editor(null));
    nodes.push(made.node);
  } else if (state.editing) {
    const menu = menus.find((entry) => entry.name === state.editing);
    if (menu) {
      const made = section(`Editing ${menu.name}`, null, { id: 'editor', open: true });
      made.body.append(await editor(menu));
      nodes.push(made.node);
    }
  }

  document.getElementById('dash').replaceChildren(...nodes);
}

refresh = start({
  tab: 'rolemenus',
  load,
});
