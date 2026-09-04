import { api, listOf, names, refRoles, send, settings, settingsNamespace } from './api.js';
import { start } from './app.js';
import { logsSection } from './logs.js';
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
  modeSwitch,
  nameNode,
  namespaceSettings,
  notice,
  readSelect,
  roleSelect,
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
const END_MODE_KEY = 'golive_end_mode';
const END_SUFFIX_KEY = 'golive_end_suffix';
const END_EDIT = 'edit';
const GAME_FALLBACK = 'something';
const DEFAULT_TEMPLATE = 'the default wording';

const END_LEAD = 'And once the stream has ended:';
const END_LEFT = 'Announcements are left as posted when a stream ends — turn golive_end_mode to '
  + 'edit to mark them.';
const END_UNKNOWN = 'The bot did not report a golive_end_mode key, so what happens once a stream '
  + 'ends is not shown rather than guessed at.';
const END_HELP = 'edit adds the wording below to the announcement; off leaves it as posted.';

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

async function wordingCard(spec, prefix, endSpec, endSuffix) {
  const shown = el('p', { class: 'preview' });
  const ended = el('p', { class: 'preview' });
  const lead = el('p', { class: 'field-help', text: END_LEAD });
  const otherwise = el('p', { class: 'field-help', text: endSpec ? END_LEFT : END_UNKNOWN });
  const playing = el('input', { class: 'input switch', type: 'checkbox', checked: true });

  let endMode = endSpec ? String(endSpec.value ?? '') : null;
  const showEnd = () => {
    const editing = endMode === END_EDIT;
    lead.hidden = !editing;
    ended.hidden = !editing;
    otherwise.hidden = editing;
  };

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

  const end = endSpec === null ? null : modeSwitch(endSpec, {
    label: 'The stream-end wording',
    onSaved: (key, value) => {
      endMode = String(value);
      showEnd();
    },
  });
  showEnd();

  const preview = card('What an announcement looks like', [
    el('div', { class: 'formrow' }, [
      field('Playing a game', playing, `Off shows what an empty game reads as: “${GAME_FALLBACK}”.`),
      end ? field('When a stream ends', end.node, END_HELP) : null,
    ]),
    shown,
    lead,
    ended,
    otherwise,
    end ? end.say : null,
    made.say,
  ]);
  return [made.row.node, preview];
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
  const suffix = specs.find((one) => one.key === END_SUFFIX_KEY);
  const endSpec = specs.find((one) => one.key === END_MODE_KEY) || null;
  wording.body.append(
    ...await wordingCard(spec, prefix, endSpec, suffix ? String(suffix.value || '') : ''),
  );
  return wording.node;
}

const PINGS_MODE_KEY = 'pings_mode';
const PINGS_NOTE = 'One opt-in role for go-live and event pings, and a role per streamer that '
  + 'only their followers wear. Members pick them from the Notifications and Streamer pings '
  + 'panels, or with /pings.';
const PINGS_NO_MODE = 'The bot did not report a pings_mode key, so the switch is not shown '
  + 'rather than guessed at.';
const NO_STREAMERS = 'Nobody has a ping role yet. Start one below, or a streamer starts their '
  + 'own with /pings fans on.';
const ROLE_GONE = 'deleted by hand';
const SETUP_HELP = 'Makes (or reuses) the Events role, points both feeds at it and puts it on '
  + 'the Notifications panel. Post that panel from the Role menus tab.';
const MODE_HELP = 'off stops every opt-in and every fan-role ping; nobody loses a role.';

/** D3: one button for the whole Events-role set-up, beside the role field it fills in. */
function setupCard(say) {
  const go = button('Set up the Events role', async () => {
    const done = await run(
      say,
      () => send('/api/pings/setup', 'POST', {}),
      (found) => found?.message || 'The Events role is set up.',
    );
    if (done.ok) {
      keepSaying('pings.setup', say);
      refresh();
    }
  }, { tone: 'warn' });
  return card('The Events role', [
    el('p', { class: 'field-help', text: SETUP_HELP }),
    bar([go]),
  ]);
}

/** D1: staff may start a streamer's role whatever pings_fan_role_creation says. */
async function streamerCard(say) {
  const picker = memberPicker({ label: 'Streamer' });
  const roles = await roleSelect(null);
  const go = button('Give them a ping role', async () => {
    if (!picker.id) {
      say.say('Pick the streamer this is about first.', 'warn');
      return;
    }
    const done = await run(
      say,
      () => send('/api/pings/streamers', 'POST', {
        member_id: picker.id,
        role_id: readSelect(roles, false),
      }),
      (found) => found?.message || 'Made the role.',
    );
    if (done.ok) {
      keepSaying('pings.streamers', say);
      refresh();
    }
  }, { tone: 'warn' });
  return card('Create for a streamer', [
    picker.node,
    el('div', { class: 'formrow' }, [
      field('Use this role instead', roles, 'Leave it unset and Black Bloc makes one from '
        + 'pings_fan_role_template.'),
    ]),
    bar([go]),
  ]);
}

async function pingsSection(specs, streamers) {
  const say = notice();
  const group = section('Pings', PINGS_NOTE, { count: streamers.length });
  const spec = specs.find((one) => one.key === PINGS_MODE_KEY);
  const mode = spec ? modeSwitch(spec, { say, onSaved: () => refresh() }) : null;

  const rows = table([
    { label: 'Streamer', cell: (row) => nameNode(row.member_id, row.member) },
    {
      label: 'Role',
      cell: (row) => (row.role ? row.role : badge(ROLE_GONE, 'warn')),
    },
    {
      label: 'Followers',
      cell: (row) => (row.followers === null ? '—' : String(row.followers)),
      className: 'mono',
    },
    { label: 'Started', cell: (row) => when(row.created_at), className: 'mono' },
    { label: 'By', cell: (row) => nameNode(row.created_by, row.created_by_name) },
    {
      label: '',
      cell: (row) => button('Remove', async () => {
        const sure = await ask({
          title: `Take ${row.member || row.member_id}'s ping role away?`,
          body: [
            'Everybody who followed them stops being pinged.',
            'Whether the Discord role itself is deleted is pings_fan_role_delete, below.',
          ],
          confirmLabel: 'Remove',
        });
        if (!sure) return;
        const done = await run(
          say,
          () => api(`/api/pings/streamers/${encodeURIComponent(row.member_id)}`, { method: 'DELETE' }),
          (found) => found?.message || 'Removed.',
        );
        if (done.ok) {
          keepSaying('pings.streamers', say);
          refresh();
        }
      }, { tone: 'danger' }),
    },
  ], streamers, { empty: NO_STREAMERS });

  group.body.append(...[
    mode
      ? el('div', { class: 'formrow' }, [field('Ping roles', mode.node, MODE_HELP)])
      : el('p', { class: 'say-nothing', text: PINGS_NO_MODE }),
    rows,
    setupCard(say),
    await streamerCard(say),
    sayAgain('pings.streamers', sayAgain('pings.setup', say)),
  ].filter(Boolean));
  return group.node;
}

const UPLOADS_MODE_KEY = 'youtube_mode';
const UPLOADS_NOTE ='When somebody linked here publishes on YouTube, Black Bloc posts it. '
  + 'Shorts are left out unless youtube_announce_shorts says otherwise, and a live stream is '
  + 'skipped because the go-live feed above already covers it.';
const UPLOADS_NO_MODE = 'The bot did not report a youtube_mode key, so the switch is not shown '
  + 'rather than guessed at.';
const UPLOADS_MODE_HELP = 'off checks nothing at all; shadow writes what it would have posted; '
  + 'on posts it. Uploads go to youtube_channel_id, or the go-live channel when that is blank.';
const NO_UPLOAD_LINKS = 'Nobody has linked a YouTube channel. Add one below, or a member opens '
  + '/youtube and links their own.';
const NO_UPLOAD_VIDEOS = 'No uploads have been seen yet.';
const NOT_SEEDED = 'The feed has not answered for this channel yet, so nothing is counted as '
  + 'seen and nothing would be announced. The next sweep tries again.';
const KEY_UNSET = 'No YOUTUBE_API_KEY is set. Shorts are still told apart by their address; a '
  + 'live stream is only spotted while the member has a YouTube go-live session open.';

const UPLOAD_STATES = { announced: 'ok', would: 'warn', skipped: 'quiet' };

/** F3: what the uploads sweep is actually doing, health first. */
function uploadsStatus(status) {
  if (!status) return null;
  const rows = [
    ['Sweep', status.running ? badge('running', 'ok') : badge('stopped', 'warn')],
    ['Last good sweep', status.last_ok_at ? when(status.last_ok_at) : 'never'],
    ['Last error', status.last_error || 'none'],
    ['Seen', `${status.videos} video(s), ${status.announced} announced`],
  ];
  return card('How the sweep is doing', [
    el('div', { class: 'formrow' }, rows.map(([label, value]) => field(label, (
      typeof value === 'string' ? el('p', { class: 'preview', text: value }) : value
    )))),
    status.api_key_set ? null : el('p', { class: 'field-help', text: KEY_UNSET }),
  ].filter(Boolean));
}

/** F3: staff link somebody's channel without waiting for them to open /youtube. */
function uploadsLinkCard(say) {
  const picker = memberPicker({ label: 'Member' });
  const channel = el('input', {
    class: 'input',
    type: 'text',
    placeholder: 'youtube.com/channel/UC… or @handle',
  });
  const go = button('Link their channel', async () => {
    if (!picker.id) {
      say.say('Pick the member this is about first.', 'warn');
      return;
    }
    const done = await run(
      say,
      () => send('/api/youtube/links', 'POST', {
        member_id: picker.id,
        channel: channel.value.trim(),
      }),
      (found) => found?.message || 'Linked.',
    );
    if (done.ok) {
      keepSaying('youtube.links', say);
      refresh();
    }
  }, { tone: 'warn' });
  return card('Link a member', [
    picker.node,
    el('div', { class: 'formrow' }, [field('YouTube channel', channel,
      'The address that starts with youtube.com/channel/UC…, or their @handle.')]),
    bar([go]),
  ]);
}

async function uploadsSection(specs, links, videos, status) {
  const say = notice();
  const group = section('YouTube uploads', UPLOADS_NOTE, { count: links.length });
  const spec = specs.find((one) => one.key === UPLOADS_MODE_KEY);
  const mode = spec ? modeSwitch(spec, { say, onSaved: () => refresh() }) : null;

  const linkTable = table([
    { label: 'Member', cell: (row) => nameNode(row.user_id, row.user_name) },
    { label: 'Channel', cell: (row) => row.title || row.channel_id, className: 'wrap' },
    { label: 'Id', cell: (row) => row.channel_id, className: 'mono' },
    {
      label: 'Counted',
      cell: (row) => (row.seeded ? badge('seeded', 'ok') : badge('not yet', 'warn')),
    },
    { label: 'Last video', cell: (row) => row.last_video || '—', className: 'wrap' },
    { label: 'Linked', cell: (row) => when(row.linked_at), className: 'mono' },
    {
      label: '',
      cell: (row) => button('Unlink', async () => {
        const sure = await ask({
          title: `Unlink ${row.user_name || row.user_id}?`,
          body: [
            `Black Bloc stops watching ${row.title || row.channel_id} for new uploads.`,
            'Everything already seen is forgotten, so re-linking counts the current videos as '
            + 'history again rather than announcing them.',
          ],
          confirmLabel: 'Unlink',
        });
        if (!sure) return;
        const done = await run(
          say,
          () => api(`/api/youtube/links/${encodeURIComponent(row.user_id)}`, { method: 'DELETE' }),
          'Unlinked.',
        );
        if (done.ok) {
          keepSaying('youtube.links', say);
          refresh();
        }
      }, { tone: 'danger' }),
    },
  ], links, { empty: NO_UPLOAD_LINKS });

  const videoTable = table([
    { label: 'Member', cell: (row) => nameNode(row.user_id, row.user_name) },
    {
      label: 'Video',
      cell: (row) => el('a', { href: row.url, target: '_blank', rel: 'noreferrer', text: row.title || row.video_id }),
      className: 'wrap',
    },
    { label: 'Kind', cell: (row) => badge(row.kind, row.kind === 'video' ? 'ok' : 'quiet') },
    { label: 'Published', cell: (row) => when(row.published_at), className: 'mono' },
    {
      label: 'What happened',
      cell: (row) => badge(row.state, UPLOAD_STATES[row.state] || 'quiet'),
    },
    { label: 'Mode then', cell: (row) => (row.mode ? row.mode : '—') },
  ], videos, { empty: NO_UPLOAD_VIDEOS });

  group.body.append(...[
    mode
      ? el('div', { class: 'formrow' }, [field('Upload announcements', mode.node, UPLOADS_MODE_HELP)])
      : el('p', { class: 'say-nothing', text: UPLOADS_NO_MODE }),
    uploadsStatus(status),
    links.some((row) => !row.seeded) ? el('p', { class: 'field-help', text: NOT_SEEDED }) : null,
    linkTable,
    uploadsLinkCard(say),
    card('Recent uploads', [videoTable], { count: videos.length, flush: true }),
    sayAgain('youtube.links', say),
  ].filter(Boolean));
  return group.node;
}

async function load() {
  const [
    linkPayload,
    optoutPayload,
    sessionPayload,
    streamerPayload,
    uploadLinkPayload,
    uploadVideoPayload,
    uploadStatus,
    allSettings,
  ] = await Promise.all([
    api('/api/golive/links'),
    api('/api/golive/optouts'),
    api('/api/golive/sessions?limit=50'),
    api('/api/pings/streamers'),
    api('/api/youtube/links'),
    api('/api/youtube/videos?limit=50'),
    api('/api/youtube/status'),
    settings(true),
  ]);
  const links = listOf(linkPayload, 'links');
  const optouts = listOf(optoutPayload, 'optouts');
  const sessions = listOf(sessionPayload, 'sessions');
  const streamers = listOf(streamerPayload, 'streamers');
  const uploadLinks = listOf(uploadLinkPayload, 'links');
  const uploads = listOf(uploadVideoPayload, 'videos');
  await names(idsIn(links, ['user_id'])
    .concat(idsIn(optouts, ['user_id']))
    .concat(idsIn(sessions, ['user_id']))
    .concat(idsIn(uploadLinks, ['user_id']))
    .concat(idsIn(uploads, ['user_id']))
    .concat(idsIn(streamers, ['member_id', 'created_by'])));

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
  const pings = settingsNamespace(allSettings, 'pings');
  const youtube = settingsNamespace(allSettings, 'youtube');

  document.getElementById('dash').replaceChildren(
    one.node,
    two.node,
    three.node,
    await wordingSection(golive),
    await namespaceSettings('golive', { onSaved: () => refresh(), omit: [TEMPLATE_KEY, END_MODE_KEY] }),
    await logsSection('golive'),
    await uploadsSection(youtube, uploadLinks, uploads, uploadStatus),
    await namespaceSettings('youtube', {
      title: 'Upload settings',
      onSaved: () => refresh(),
      omit: [UPLOADS_MODE_KEY],
    }),
    await logsSection('youtube', { title: 'Upload logs' }),
    await pingsSection(pings, streamers),
    await namespaceSettings('pings', {
      title: 'Ping role settings',
      onSaved: () => refresh(),
      omit: [PINGS_MODE_KEY],
    }),
    await logsSection('pings', { title: 'Ping role logs' }),
  );
}

refresh = start({
  tab: 'golive',
  load,
});
