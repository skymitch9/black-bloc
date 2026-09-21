import { api, listOf, names, refRoles, send, settings, settingsNamespace } from './api.js';
import { start } from './app.js';
import { renderPreview } from './discordmd.js';
import {
  joinStreamers,
  liveStreams,
  placeSettings,
  routeTyped,
  spotlightCards,
  spotlightSessions,
} from './golive-join.js';
import { logsSection } from './logs.js';
import {
  ago,
  ask,
  badge,
  bar,
  button,
  card,
  closeDrawer,
  el,
  field,
  icon,
  idsIn,
  keepSaying,
  memberPicker,
  modeSwitch,
  nameNode,
  notice,
  openDrawer,
  readSelect,
  roleSelect,
  run,
  sayAgain,
  sayNothing,
  searchField,
  section,
  sentenceFor,
  settingsPanel,
  table,
  templateEditor,
  when,
} from './ui.js';

let refresh = () => {};

const TWITCH = 'twitch';
const YOUTUBE = 'youtube';
const PLATFORM_WORDS = { twitch: 'Twitch', youtube: 'YouTube' };

const TEMPLATE_KEY = 'golive_template';
const PING_KEY = 'golive_ping_role_id';
const END_TEMPLATE_KEY = 'golive_end_template';
const END_AUTHOR_KEY = 'golive_end_author';
const END_KEEP_KEY = 'golive_end_keep_mention';
const GOLIVE_MODE_KEY = 'golive_mode';
const LIVE_MODE_KEY = 'youtube_live_mode';
const PINGS_MODE_KEY = 'pings_mode';
const SPOTLIGHT_MODE_KEY = 'spotlight_mode';
const CHANNEL_KEY = 'golive_channel_id';
const GAME_FALLBACK = 'something';
const DEFAULT_TEMPLATE = 'the default wording';

const SUBTITLE = 'Who is streaming, who is set up to be announced, and what the announcement '
  + 'says. One list of people, whichever platform they use.';

const NOBODY_LIVE = 'Nobody is streaming right now. A Twitch stream shows up the moment Discord '
  + 'sees it; a linked YouTube channel is looked at on the cadence in the strip above.';
const LIVE_NOTE = 'One card per open stream, both platforms together.';
const HELD_BACK = 'their {platform} stream already has the session';

const STREAMERS_NOTE = 'One row per person. Click a row for everything about them.';
const NO_STREAMERS = 'Nobody is linked and nobody has a ping role yet. Add a streamer above, or '
  + 'a member links their own channel with /golive or /youtube.';
const NOTHING_MATCHES = 'Nobody here matches what you typed.';
const PUTTING_TOGETHER = 'Putting this person together…';
const READY = 'ready';
const OPTED_OUT = 'opted out';
const LIVE_NOW = 'live now';
const NOT_LINKED = 'not linked';
const NO_ROLE_YET = 'none yet';
const ROLE_GONE = 'deleted by hand';
const HIDDEN = 'hidden';

const ADD_TITLE = 'Add a streamer';
const ADD_HELP = 'One box for both platforms. A Twitch name goes to the go-live watcher; a '
  + 'YouTube channel address or @handle goes to the live probe. Nothing is guessed — a value '
  + 'that could be either is refused and says so.';
const ADD_FIELD_HELP = 'The name in twitch.tv/…, or the address that starts with '
  + 'youtube.com/channel/UC…, or their @handle.';
const ADD_PICK_FIRST = 'Pick the member this is about first.';

const ANNOUNCEMENT_NOTE = 'One wording for both platforms. {platform} fills itself in.';
const WHILE_LIVE_TITLE = 'While they are live';
const ENDED_TITLE = 'Once the stream has ended';
const WORDING_TITLE = 'Wording';
const WORDING_NOTE = 'Both messages as the bot itself renders them — the same functions Discord '
  + 'gets, not a copy living on this page. The sample is a two-hour stream of Celeste.';
const WORDING_STALE ='This card repaints itself whenever either wording above is saved. Refresh '
  + 'is for a change somebody else made, on the Settings page or from Discord.';
const WHILE_LIVE = 'while live';
const AFTER_THE_STREAM = 'after the stream';
const END_NO_KEYS = 'The bot did not report a golive_end_template key, so the ending is edited '
  + 'from Everything else rather than guessed at here.';
const END_LIVE_HELP = '{live} is the sentence exactly as it was posted, so “{live} — stream '
  + 'ended” adds to the end of it and a wording without {live} replaces the whole post. The '
  + 'rest of the fields are {name} {game} {title} {url} {platform} {duration}. The announcement '
  + 'is always edited once the stream is over.';
const END_BLANK_TEMPLATE = 'Empty — the sentence stays exactly as it was posted and nothing is '
  + 'added to it.';
const END_BLANK_AUTHOR = 'Empty — the card’s top line keeps saying “was live on”.';
const END_WORDING_WHERE = 'Once the stream is over';
const NO_TEMPLATE = 'The bot did not report a golive_template key, so this editor is not shown '
  + 'rather than guessed at.';
const PLAYING_HELP = `Off shows what an empty game reads as: “${GAME_FALLBACK}”.`;

  + 'forgotten, so write it again to go back.';
  + 'it in the Once the stream is over box above.';

const SAMPLES = {
  twitch: {
    name: 'Casey',
    game: 'Lethal Company',
    title: 'late night runs',
    url: 'https://twitch.tv/caseyfast',
    platform: 'Twitch',
  },
  youtube: {
    name: 'Casey',
    game: 'Lethal Company',
    title: 'late night runs',
    url: 'https://youtube.com/watch?v=caseyfast',
    platform: 'YouTube',
  },
};
const ENDED_EXTRA = { duration: '2 h 10 min' };

const REST_NOTE = 'The settings nobody touches weekly, and the log. Closed by default.';
const NO_SETTINGS_HERE = 'The bot registers no settings under this heading.';
const SETUP_HELP = 'Makes (or reuses) the Events role, points both feeds at it and puts it on '
  + 'the Notifications panel. Post that panel from the Role menus tab.';
const RAID_HELP = 'Makes (or reuses) the Raid trains role and points raidtrain_ping_role_id at '
  + 'it, so a member opts in from /pings instead of asking staff.';
const ONBOARDING_NOTE = 'The bot keeps two of Discord’s onboarding prompts in step with these '
  + 'roles: what should ping you, and which streamers. It never touches a prompt it did not '
  + 'make, and it never turns onboarding itself on or off.';
const ONBOARDING_NO_COMMUNITY = 'This server is not a Community server, so Discord has no '
  + 'onboarding screen. Turn Community on in Server Settings ▸ Enable Community; until then '
  + 'the Notifications role menu is the fallback.';
const ONBOARDING_OFF = 'The bot is not managing onboarding. The prompts stay exactly as '
  + 'somebody left them.';
const ONBOARDING_NEVER = 'Not written yet.';
const ONBOARDING_NOTHING = 'Nothing to put on the screen yet — set up the Events role or the '
  + 'raid-train role first.';
const ONBOARDING_WHERE = 'Whether the bot manages them at all is '
  + 'pings_onboarding_managed in the settings above, and Stop managing onboarding on /pings.';

const PROBE_NOTE = 'A linked channel going live is announced through the go-live feed above, as '
  + 'source youtube. golive_mode still decides whether anything is posted.';
const PROBE_KEY_UNSET = 'With no YOUTUBE_API_KEY the stream is announced from the page alone, so '
  + 'its title reads Live now and no quota is spent.';

const NO_EVENTS_ROLE = 'No Events role yet';
const ONBOARDING_DRIFTED = 'Onboarding has never been written';
const SETUP_OPEN = 'open Ping roles';

const GOLIVE_MODE_HELP = 'off watches nothing; shadow logs what it would have announced; on '
  + 'posts it.';
const LIVE_MODE_HELP = 'off probes nothing at all; shadow probes and logs what it would have '
  + 'announced; on announces it. The post itself goes wherever go-live posts, so golive_mode and '
  + 'golive_channel_id still decide whether anybody sees it.';
const PINGS_MODE_HELP = 'off stops every opt-in and every fan-role ping; nobody loses a role.';

const LOG_CHIPS = [
  { id: 'all', label: 'All' },
  { id: 'golive', label: 'Go-live' },
  { id: 'youtube', label: 'YouTube' },
  { id: 'pings', label: 'Ping roles' },
];

const CHANNEL_ONLY = 'channel only';
const SPOTLIGHT_MODE_HELP = 'off, shadow (rehearse where shadow_channel_id points) or on \u2014 '
  + 'Twitch channels with nobody here behind them are announced, reminded and pinned in the '
  + 'go-live channel.';
const SPOTLIGHT_NOTE = 'Watched by name. No member here is behind them.';
const SPOTLIGHT_MEMBER_NOTE = 'Not spotlighted. Spotlighting their channel bumps it every few hours and pins it while they stream — for a marathon, say.';
const SPOTLIGHT_KEPT = 'Kept for ever \u2014 no purge takes it off the list.';
const SPOTLIGHT_ADD_TITLE = 'Spotlight a channel';
const SPOTLIGHT_ADD_HELP = 'For an org channel like GamesDoneQuick, or a marathon nobody here '
  + 'runs. Black Bloc announces it in the go-live channel whenever it goes live, reminds people '
  + 'while it runs, and pins the announcement for the duration.';
const SPOTLIGHT_DAYS_HELP = 'Days before it is purged. Leave it blank to keep it for ever, the '
  + 'way GamesDoneQuick is kept.';
const SPOTLIGHT_REMOVE_ASK = 'Take **{login}** off the spotlight list? Any announcement it has '
  + 'out there is left as posted, and it can be added again at any time.';
const NO_MEMBER = 'Nobody here \u2014 this is a channel Black Bloc watches by name.';

function platformPill(platform) {
  return el('span', {
    class: 'pill glplat',
    'data-platform': platform,
    text: PLATFORM_WORDS[platform] || platform,
  });
}

function muted(text) {
  return el('span', { class: 'muted', text });
}

function chipButton(label, pressed, onPick) {
  return el('button', {
    class: 'chip-filter',
    type: 'button',
    'aria-pressed': pressed ? 'true' : 'false',
    text: label,
    on: { click: onPick },
  });
}

function drawer(title, children, { open = false } = {}) {
  return el('details', { class: 'gldrawer', open: open || undefined }, [
    el('summary', { class: 'gldrawer-head' }, [
      icon('chevronDown', 14, 'sect-mark'),
      el('span', { text: title }),
    ]),
    el('div', { class: 'gldrawer-body' }, [].concat(children).filter(Boolean)),
  ]);
}

/** A logsSection node, demoted so the in-page rail still counts five sections. */
function unsection(node) {
  node.classList.remove('sect');
  node.removeAttribute('data-sect');
  node.removeAttribute('data-title');
  const details = node.querySelector('details.sect-card');
  if (details) details.open = true;
  return node;
}

function settingWord(count) {
  return `${count} setting${count === 1 ? '' : 's'}`;
}

function statCell(label, value, note) {
  return el('div', { class: 'stat' }, [
    el('span', { class: 'stat-label', text: label }),
    el('span', { class: 'stat-value', text: value }),
    note ? el('span', { class: 'stat-note', text: note }) : null,
  ].filter(Boolean));
}

function modeCell(label, spec, note, help) {
  if (!spec) return statCell(label, '—', `The bot did not report the ${label.toLowerCase()} key.`);
  const made = modeSwitch(spec, { onSaved: () => refresh() });
  made.node.setAttribute('title', help);
  made.say.classList.add('stat-note');
  return el('div', { class: 'stat' }, [
    el('span', { class: 'stat-label', text: label }),
    made.node,
    el('span', { class: 'stat-note', text: note }),
    made.say,
  ]);
}

function warnCell(lines, onOpen) {
  return el('button', {
    class: 'stat',
    type: 'button',
    'data-tone': 'warn',
    on: { click: onOpen },
  }, [
    el('span', { class: 'stat-label', text: 'Set-up' }),
    el('span', { class: 'stat-value', text: String(lines.length) }),
    el('span', { class: 'stat-note', text: `${lines.join(' · ')} — ${SETUP_OPEN}` }),
  ]);
}

function channelWord(specs) {
  const spec = specs.find((one) => one.key === CHANNEL_KEY);
  const value = spec ? (spec.value ?? spec.default) : null;
  return value ? 'posted where golive_channel_id points' : 'no announcement channel set';
}

function headerStrip({
  golive, youtube, pings, rows, cards, status, warnings, onOpenPings,
}) {
  const linked = rows.filter((row) => row.twitch || row.youtube).length;
  const tw = rows.filter((row) => row.twitch).length;
  const yt = rows.filter((row) => row.youtube).length;
  const out = rows.filter((row) => row.opted_out).length;
  const liveTw = cards.filter((one) => one.platforms.includes(TWITCH)).length;
  const liveYt = cards.filter((one) => one.platforms.includes(YOUTUBE)).length;
  const probe = status
    ? `last look ${status.last_probe_at ? ago(status.last_probe_at).text : 'never'} · `
      + `${status.quota_today || 0} unit(s) of quota today`
    : 'the bot did not report the probe';
  const cells = [
    statCell('Live right now', String(cards.length), `${liveTw} Twitch · ${liveYt} YouTube`),
    modeCell(
      'Twitch announcements',
      golive.find((one) => one.key === GOLIVE_MODE_KEY),
      channelWord(golive),
      GOLIVE_MODE_HELP,
    ),
    modeCell(
      'YouTube announcements',
      youtube.find((one) => one.key === LIVE_MODE_KEY),
      'posted through the go-live feed',
      LIVE_MODE_HELP,
    ),
    modeCell(
      'Ping roles',
      pings.find((one) => one.key === PINGS_MODE_KEY),
      'the opt-in roles members pick with /pings',
      PINGS_MODE_HELP,
    ),
    modeCell(
      'Spotlight',
      golive.find((one) => one.key === SPOTLIGHT_MODE_KEY),
      spotlightWords(rows),
      SPOTLIGHT_MODE_HELP,
    ),
    statCell('Set up', String(linked), `${tw} Twitch · ${yt} YouTube · ${out} opted out`),
    statCell(
      'Watching',
      status && status.live_minutes ? `every ${status.live_minutes} min` : '—',
      probe,
    ),
  ];
  if (warnings.length) cells.push(warnCell(warnings, onOpenPings));
  return el('div', { class: 'statgrid' }, cells);
}

function liveCard(one) {
  const words = one.platforms.map((platform) => PLATFORM_WORDS[platform] || platform);
  return el('div', { class: 'livecard', 'data-held': one.announced ? undefined : 'true' }, [
    el('div', { class: 'livecard-who' }, [
      nameNode(one.user_id, one.name),
      ...one.platforms.map(platformPill),
    ]),
    one.title ? el('p', { class: 'livecard-what', text: one.title }) : null,
    el('div', { class: 'livecard-meta' }, [
      one.announced ? badge('announced', 'ok') : badge('seen, not announced', 'warn'),
      one.game ? badge(one.game) : null,
      one.platforms.length > 1 ? muted(`one announcement covers ${words.join(' and ')}`) : null,
      !one.announced && one.held_by
        ? muted(HELD_BACK.replace('{platform}', PLATFORM_WORDS[one.held_by] || one.held_by))
        : null,
      one.spotlight_id ? badge(CHANNEL_ONLY) : null,
      one.pinned ? badge('pinned') : null,
      one.bump_count ? muted(`${one.bump_count} reminder(s) so far`) : null,
      one.started_at ? muted(`started ${ago(one.started_at).text}`) : null,
      one.url ? el('a', { class: 'mono', href: one.url, rel: 'noreferrer', text: one.url }) : null,
      one.also_url
        ? el('a', { class: 'mono', href: one.also_url, rel: 'noreferrer', text: one.also_url })
        : null,
    ].filter(Boolean)),
  ].filter(Boolean));
}

function liveSection(cards) {
  const group = section('Live now', LIVE_NOTE, { count: cards.length });
  group.body.append(cards.length
    ? el('div', { class: 'golive-lives' }, cards.map(liveCard))
    : sayNothing(NOBODY_LIVE));
  return group.node;
}

function twitchMoves(row, say) {
  if (row.twitch) {
    return [
      el('a', {
        class: 'btn small quiet',
        href: `https://twitch.tv/${row.twitch}`,
        rel: 'noreferrer',
        text: 'Open channel',
      }),
      button('Unlink', async () => {
        const sure = await ask({
          title: `Unlink ${row.name || row.user_id}?`,
          body: [`Black Bloc stops watching twitch.tv/${row.twitch} for them. They can link it again themselves.`],
          confirmLabel: 'Unlink',
        });
        if (!sure) return;
        const done = await run(
          say,
          () => api(`/api/golive/links/${encodeURIComponent(row.user_id)}`, { method: 'DELETE' }),
          'Unlinked.',
        );
        if (done.ok) {
          keepSaying('golive.links', say);
          refresh();
        }
      }, { tone: 'danger' }),
    ];
  }
  const login = el('input', { class: 'input', type: 'text', placeholder: 'the name in twitch.tv/…' });
  return [
    login,
    button('Link them', async () => {
      const done = await run(
        say,
        () => send('/api/golive/links', 'POST', { user_id: row.user_id, twitch_login: login.value.trim() }),
        (found) => found?.message || 'Linked.',
      );
      if (done.ok) {
        keepSaying('golive.links', say);
        refresh();
      }
    }, { tone: 'warn' }),
  ];
}

function youtubeMoves(row, say) {
  if (row.youtube_id) {
    return [
      el('a', {
        class: 'btn small quiet',
        href: `https://youtube.com/channel/${row.youtube_id}`,
        rel: 'noreferrer',
        text: 'Open channel',
      }),
      button('Unlink', async () => {
        const sure = await ask({
          title: `Unlink ${row.name || row.user_id}?`,
          body: [
            `Black Bloc stops watching ${row.youtube || row.youtube_id} for live streams.`,
            'They can link it again themselves on /youtube, and a Lead can link it for them below.',
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
    ];
  }
  const channel = el('input', {
    class: 'input',
    type: 'text',
    placeholder: 'youtube.com/channel/UC… or @handle',
  });
  return [
    channel,
    button('Link their channel', async () => {
      const done = await run(
        say,
        () => send('/api/youtube/links', 'POST', { member_id: row.user_id, channel: channel.value.trim() }),
        (found) => found?.message || 'Linked.',
      );
      if (done.ok) {
        keepSaying('youtube.links', say);
        refresh();
      }
    }, { tone: 'warn' }),
  ];
}

let pingsTemplate = '{name} pings';

/** The same door /pings has: an existing role, or a new one named by pings_fan_role_template. */
async function addPingRole(row, say) {
  const who = row.name || row.user_id;
  const roles = await roleSelect(null);
  const named = el('p', { class: 'field-help' });
  const sayName = () => {
    const picked = readSelect(roles, false);
    named.textContent = picked
      ? 'That role becomes their ping role; nobody gets added to it by this.'
      : `Black Bloc makes a new role named “${pingsTemplate.replace('{name}', who)}” — the name comes from `
        + 'pings_fan_role_template, in Everything else ▸ Ping roles.';
  };
  roles.addEventListener('change', sayName);
  sayName();
  const sure = await ask({
    title: `Give ${who} a ping role`,
    body: [
      'Members who press their name on /pings get this role, and it is pinged when they go live.',
      field('Use an existing role, or leave it to make a new one', roles),
      named,
    ],
    confirmLabel: 'Add the ping role',
    tone: 'warn',
  });
  if (!sure) return;
  const done = await run(
    say,
    () => send('/api/pings/streamers', 'POST', {
      member_id: row.user_id,
      role_id: readSelect(roles, false),
    }),
    (found) => found?.message || 'Made the role.',
  );
  if (done.ok) {
    keepSaying('pings.streamers', say);
    refresh();
  }
}

async function roleMoves(row, say) {
  const moves = [];
  if (row.role_id) {
    moves.push(button('Remove', async () => {
      const sure = await ask({
        title: `Take ${row.name || row.user_id}'s ping role away?`,
        body: [
          'Everybody who followed them stops being pinged.',
          'Whether the Discord role itself is deleted is pings_fan_role_delete, in Everything else.',
        ],
        confirmLabel: 'Remove',
      });
      if (!sure) return;
      const done = await run(
        say,
        () => api(`/api/pings/streamers/${encodeURIComponent(row.user_id)}`, { method: 'DELETE' }),
        (found) => found?.message || 'Removed.',
      );
      if (done.ok) {
        keepSaying('pings.streamers', say);
        refresh();
      }
    }, { tone: 'danger' }));
  } else if (!String(row.user_id).startsWith('spotlight:')) {
    moves.push(button('Add a ping role…', () => addPingRole(row, say), { tone: 'warn' }));
  }
  if (row.listed !== null) {
    moves.push(button(row.listed ? 'Hide' : 'Restore', async () => {
      if (row.listed) {
        const sure = await ask({
          title: `Take ${row.name || row.user_id} off the streamer list?`,
          body: ['Nobody new can follow them, and going live does not put them back. Their '
            + 'ping role goes too if nobody is wearing it.'],
          confirmLabel: 'Hide',
        });
        if (!sure) return;
      }
      const done = await run(
        say,
        () => send(`/api/pings/list/${encodeURIComponent(row.user_id)}`, 'POST', { listed: !row.listed }),
        (found) => found?.message || 'Done.',
      );
      if (done.ok) {
        keepSaying('pings.streamer', say);
        refresh();
      }
    }, { tone: row.listed ? 'danger' : 'warn' }));
  }
  return moves;
}

function announceMoves(row, say) {
  if (row.opted_out) {
    return [button('Announce them again', async () => {
      const done = await run(
        say,
        () => api(`/api/golive/optouts/${encodeURIComponent(row.user_id)}`, { method: 'DELETE' }),
        (found) => found?.message || 'The opt-out is gone.',
      );
      if (done.ok) {
        keepSaying('golive.optouts', say);
        refresh();
      }
    }, { tone: 'quiet' })];
  }
  return [button('Opt them out', async () => {
    const done = await run(
      say,
      () => send('/api/golive/optouts', 'POST', { user_id: row.user_id }),
      (found) => found?.message || 'Opted out.',
    );
    if (done.ok) {
      keepSaying('golive.optouts', say);
      refresh();
    }
  }, { tone: 'warn' })];
}

function spotlightMoves(row, say) {
  const one = row.spotlight;
  const after = (done) => {
    if (!done.ok) return;
    keepSaying('golive.spotlight', say);
    closeDrawer();
    refresh();
  };
  const patch = (body, fallback) => run(
    say,
    () => send(`/api/golive/spotlight/${one.id}`, 'PATCH', body),
    (found) => found?.message || fallback,
  );
  const moves = [
    button('Extend a week', async () => after(await patch({ days: 7 }, 'Extended.')), { tone: 'quiet' }),
  ];
  if (one.kept) {
    moves.push(button('Let it expire', async () => after(await patch({ days: 7 }, 'It runs out in a week.')), { tone: 'quiet' }));
  } else {
    moves.push(button('Keep for ever', async () => after(await patch({ keep: true }, 'Kept for ever.')), { tone: 'quiet' }));
  }
  if (one.live) {
    moves.push(button('Bump now', async () => {
      const done = await run(
        say,
        () => send(`/api/golive/spotlight/${one.id}/bump`, 'POST', {}),
        (found) => found?.message || 'Reminded the channel.',
      );
      after(done);
    }, { tone: 'quiet' }));
  }
  moves.push(button(one.pin ? 'Stop pinning it' : 'Pin it while it streams', async () => (
    after(await patch({ pin: !one.pin }, one.pin ? 'It will not be pinned.' : 'It will be pinned.'))
  ), { tone: 'quiet' }));
  moves.push(button('Remove', async () => {
    const yes = await ask({
      title: `Remove ${one.twitch_login} from the spotlight?`,
      body: [SPOTLIGHT_REMOVE_ASK.replace('{login}', one.twitch_login)],
      confirmLabel: 'Remove it',
    });
    if (!yes) return;
    const done = await run(
      say,
      () => api(`/api/golive/spotlight/${one.id}`, { method: 'DELETE' }),
      (found) => found?.message || 'Off the list.',
    );
    after(done);
  }, { tone: 'warn' }));
  return moves;
}

function spotlightSaid(row) {
  const one = row.spotlight;
  const bits = [one.kept ? SPOTLIGHT_KEPT : `Runs out ${when(one.expires_at)}.`];
  if (one.bump_hours) bits.push(`Reminders every ${one.bump_hours} h.`);
  if (one.event_id) bits.push(`Set up for event #${one.event_id}.`);
  if (one.note) bits.push(one.note);
  return el('span', { text: bits.join(' ') });
}

function panelGroup(label, said, moves) {
  return card(label, [said, el('div', { class: 'bar' }, moves)]);
}

function rowFoot(row) {
  const bits = [];
  if (row.twitch_at) bits.push(`Twitch linked ${when(row.twitch_at)}`);
  if (row.youtube_at) bits.push(`YouTube linked ${when(row.youtube_at)}`);
  if (row.last_live_at) bits.push(`last live ${when(row.last_live_at)}`);
  if (row.live_count !== null && row.live_count !== undefined) {
    bits.push(`${row.live_count} go-live(s)`);
  }
  if (row.listed === false) bits.push('off the streamer list');
  return bits.join(' · ') || 'Nothing has happened for this person yet.';
}

async function rowPanel(row, say) {
  const twitchSaid = row.twitch
    ? el('span', { class: 'mono', text: `twitch.tv/${row.twitch}` })
    : muted(NOT_LINKED);
  const youtubeSaid = row.youtube
    ? el('span', {}, [
      el('span', { text: row.youtube }),
      row.youtube_id ? el('span', { class: 'mono glid', text: row.youtube_id }) : null,
    ].filter(Boolean))
    : muted(NOT_LINKED);
  const roleSaid = row.role
    ? el('span', { text: `${row.role} · ${row.role_wearers === null ? '—' : row.role_wearers} wearing it` })
    : (row.role_id ? badge(ROLE_GONE, 'warn') : muted(NO_ROLE_YET));
  const announceSaid = el('span', {
    text: row.opted_out
      ? 'Opted out — never announced'
      : 'On — announced wherever they go live',
  });

  if (String(row.user_id).startsWith('spotlight:')) {
    return [
      panelGroup('Spotlight', spotlightSaid(row), spotlightMoves(row, say)),
      panelGroup('Twitch', twitchSaid, twitchMoves(row, say).slice(0, 1)),
      el('p', { class: 'field-help', text: NO_MEMBER }),
      say,
    ];
  }
  return [
    ...(row.spotlight
      ? [panelGroup('Spotlight', spotlightSaid(row), spotlightMoves(row, say))]
      : (row.twitch
        ? [panelGroup('Spotlight', el('span', { class: 'cell-quiet', text: SPOTLIGHT_MEMBER_NOTE }), [
          button('Spotlight this channel…', () => openSpotlightForm(row.twitch), { tone: 'quiet' }),
        ])]
        : [])),
    panelGroup('Twitch', twitchSaid, twitchMoves(row, say)),
    panelGroup('YouTube', youtubeSaid, youtubeMoves(row, say)),
    panelGroup('Ping role', roleSaid, await roleMoves(row, say)),
    panelGroup('Announcements', announceSaid, announceMoves(row, say)),
    el('p', { class: 'field-help', text: rowFoot(row) }),
    say,
  ];
}

/** The same construct Moderation's case rows use: the right-hand drawer, opened twice so
    the panel appears at once and fills in when the role list has loaded. */
async function showStreamer(row) {
  const title = row.name || row.user_id;
  openDrawer(title, sayNothing(PUTTING_TOGETHER));
  openDrawer(title, await rowPanel(row, notice()));
}

function announcedCell(row) {
  if (row.live) return el('span', { class: 'cell-kind' }, [badge(LIVE_NOW, 'ok')]);
  return muted(READY);
}

function expiresCell(row) {
  if (!row.spotlight) return muted('—');
  if (row.spotlight.kept) return el('span', { class: 'cell-kind' }, [badge('kept for ever', 'ok')]);
  return el('span', { class: 'cell-quiet', text: row.spotlight.until });
}

function optedOutCell(row) {
  return row.opted_out ? el('span', { class: 'cell-kind' }, [badge(OPTED_OUT, 'warn')]) : muted('—');
}

function memberCell(row) {
  if (String(row.user_id).startsWith('spotlight:')) {
    return el('span', { class: 'cell-name' }, [
      el('span', { text: row.name }),
      badge(CHANNEL_ONLY),
    ]);
  }
  return el('span', { class: 'cell-name' }, [
    nameNode(row.user_id, row.name),
    row.listed === false ? badge(HIDDEN, 'warn') : null,
    row.spotlight ? badge('spotlight') : null,
  ].filter(Boolean));
}

const FILTERS = [
  { id: 'all', label: 'All', keep: () => true },
  { id: 'live', label: 'Live now', keep: (row) => Boolean(row.live) },
  { id: 'yt', label: 'Has YouTube', keep: (row) => Boolean(row.youtube) },
  { id: 'notyt', label: 'Twitch only', keep: (row) => Boolean(row.twitch) && !row.youtube },
  { id: 'out', label: 'Opted out', keep: (row) => row.opted_out === true },
  { id: 'spot', label: 'Spotlight', keep: (row) => Boolean(row.spotlight) },
  { id: 'kept', label: 'Kept forever', keep: (row) => Boolean(row.spotlight && row.spotlight.kept) },
];

function spotlightWords(rows) {
  const spots = rows.filter((row) => row.spotlight);
  const kept = spots.filter((row) => row.spotlight.kept).length;
  return `${spots.length} channel(s) with no member · ${kept} kept for ever · ${spots.length - kept} expiring`;
}

/** The card as Discord would draw it: the top line, then the wording with its markdown. */
function drawCard(node, text, head, roles) {
  node.innerHTML = renderPreview(String(text || ''), {
    style: 'embed',
    title: head || '',
    roles: (roles || []).map((one) => ({ id: String(one.id), name: one.name })),
  });
}

const COLUMNS = ['Member', 'Twitch', 'YouTube', 'Ping role', 'Announced', 'Expires', 'Opted out'];
const STREAMER_GRID = 'grid-template-columns: minmax(180px, 1.3fr) minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1fr) minmax(0, 0.9fr) minmax(0, 0.9fr) minmax(0, 0.8fr) 24px';

function roleCell(row) {
  if (row.role) {
    return el('span', {
      class: 'cell-quiet',
      text: `${row.role} · ${row.role_wearers === null ? '—' : row.role_wearers}`,
    });
  }
  return row.role_id ? el('span', { class: 'cell-kind' }, [badge(ROLE_GONE, 'warn')]) : muted('—');
}

function streamerRow(row) {
  return el('button', {
    class: 'grid-row',
    type: 'button',
    style: STREAMER_GRID,
    'data-search': (`${row.name || ''} ${row.user_id} ${row.twitch || ''} `
      + `${row.youtube || ''} ${row.role || ''}`).toLowerCase(),
    on: { click: () => showStreamer(row) },
  }, [
    memberCell(row),
    row.twitch ? el('span', { class: 'cell-quiet mono', text: row.twitch }) : muted('—'),
    row.youtube ? el('span', { class: 'cell-quiet', text: row.youtube }) : muted('—'),
    roleCell(row),
    announcedCell(row),
    expiresCell(row),
    optedOutCell(row),
    icon('chevronRight', 16),
  ]);
}

function streamersSection(rows, say) {
  const group = section('Streamers', STREAMERS_NOTE, { count: rows.length, open: true });
  const voice = sayAgain('golive.links', sayAgain('golive.optouts', sayAgain('youtube.links',
    sayAgain('pings.streamers', sayAgain('pings.streamer', say)))));
  if (rows.length === 0) {
    group.body.append(sayNothing(NO_STREAMERS), voice);
    return group.node;
  }
  const head = el('div', { class: 'grid-row head', style: STREAMER_GRID }, [
    ...COLUMNS.map((label) => el('span', { text: label })),
    el('span'),
  ]);
  const lines = rows.map(streamerRow);
  const foot = el('div', { class: 'grid-foot' });
  const none = sayNothing(NOTHING_MATCHES);
  none.hidden = true;

  const state = { filter: 'all', query: '' };
  const paint = () => {
    const found = FILTERS.find((one) => one.id === state.filter) || FILTERS[0];
    let shown = 0;
    lines.forEach((line, at) => {
      const hit = found.keep(rows[at])
        && (state.query === '' || (line.getAttribute('data-search') || '').includes(state.query));
      line.hidden = !hit;
      if (hit) shown += 1;
    });
    foot.textContent = shown === rows.length
      ? `${rows.length} ${rows.length === 1 ? 'person' : 'people'}`
      : `${shown} of the ${rows.length} ${rows.length === 1 ? 'person' : 'people'} here`;
    none.hidden = shown > 0;
    group.count(shown);
  };

  const chips = el('div', { class: 'chipbar' });
  const paintChips = () => {
    chips.replaceChildren(...FILTERS.map((one) => chipButton(one.label, state.filter === one.id, () => {
      state.filter = one.id;
      paintChips();
      paint();
    })));
  };
  paintChips();

  group.body.append(
    el('div', { class: 'table-tools' }, [
      searchField({
        label: 'Find a streamer',
        placeholder: 'Find a person, a handle, a channel…',
        onQuery: (query) => {
          state.query = query;
          paint();
        },
      }),
      chips,
      streamerDoors(),
    ]),
    el('div', { class: 'table-scroll' }, [
      el('div', { class: 'grid-table streamers' }, [head, ...lines, foot]),
    ]),
    none,
    voice,
  );
  paint();
  return group.node;
}

function addSpotlightButton() {
  return button(SPOTLIGHT_ADD_TITLE, () => openSpotlightForm(), { tone: 'quiet' });
}

/** One form for both doors: the toolbar (empty) and a member's drawer (their login filled in). */
function openSpotlightForm(preset = '') {
  {
    const box = el('input', {
      class: 'input',
      type: 'text',
      placeholder: 'gamesdonequick',
      value: preset || undefined,
    });
    const days = el('input', { class: 'input', type: 'number', min: '1', placeholder: '7' });
    const voice = notice();
    const go = button('Spotlight it', async () => {
      const done = await run(
        voice,
        () => send('/api/golive/spotlight', 'POST', {
          twitch_login: box.value,
          days: days.value.trim() === '' ? null : days.value.trim(),
          keep: days.value.trim() === '',
        }),
        (found) => found?.message || 'On the list.',
      );
      if (done.ok) {
        keepSaying('golive.spotlight', voice);
        closeDrawer();
        refresh();
      }
    }, { tone: 'warn' });
    openDrawer(SPOTLIGHT_ADD_TITLE, [
      el('p', { class: 'field-help', text: SPOTLIGHT_ADD_HELP }),
      el('div', { class: 'formrow' }, [field('The name after twitch.tv/', box, SPOTLIGHT_NOTE)]),
      el('div', { class: 'formrow' }, [field('Days to keep it', days, SPOTLIGHT_DAYS_HELP)]),
      bar([go]),
      voice,
    ]);
  }
}

function addStreamerButton() {
  return button(ADD_TITLE, () => {
    const picker = memberPicker({ label: 'Member' });
    const box = el('input', {
      class: 'input',
      type: 'text',
      placeholder: 'twitch name, or youtube.com/channel/UC… or @handle',
    });
    const voice = notice();
    const go = button('Link them', async () => {
      if (!picker.id) {
        voice.say(ADD_PICK_FIRST, 'warn');
        return;
      }
      const routed = routeTyped(box.value);
      if (!routed.where) {
        voice.say(routed.why, 'warn');
        return;
      }
      const done = await run(
        voice,
        () => (routed.where === YOUTUBE
          ? send('/api/youtube/links', 'POST', { member_id: picker.id, channel: routed.value })
          : send('/api/golive/links', 'POST', { user_id: picker.id, twitch_login: routed.value })),
        (found) => found?.message || 'Linked.',
      );
      if (done.ok) {
        keepSaying(routed.where === YOUTUBE ? 'youtube.links' : 'golive.links', voice);
        closeDrawer();
        refresh();
      }
    }, { tone: 'warn' });
    openDrawer(ADD_TITLE, [
      el('p', { class: 'field-help', text: ADD_HELP }),
      picker.node,
      el('div', { class: 'formrow' }, [field('Twitch name or YouTube channel', box, ADD_FIELD_HELP)]),
      bar([go]),
      voice,
    ]);
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

function botLine(mark, line, text, footer) {
  return el('li', { class: 'msg', 'data-direction': 'out' }, [
    el('div', { class: 'msg-head' }, [
      badge(mark, mark === WHILE_LIVE ? 'ok' : null),
      el('span', { text: line }),
    ]),
    el('p', { class: 'msg-body', text }),
    footer ? el('p', { class: 'msg-head', text: footer }) : null,
  ].filter(Boolean));
}

function withRoleNames(text, roles) {
  return String(text || '').replace(/<@&(\d+)>/g, (whole, id) => {
    const role = roles.find((one) => String(one.id) === id);
    return role ? `@${role.name}` : whole;
  });
}

async function wordingPreview(say) {
  const list = el('ul', { class: 'msglist' });
  let roles = [];
  const heads = { live: '', ended: '', roles };
  const paint = async () => {
    try {
      const found = await api('/api/golive/preview');
      heads.live = found.live.author || '';
      heads.ended = found.ended.author || '';
      heads.roles = roles;
      list.replaceChildren(
        botLine(WHILE_LIVE, found.live.author, withRoleNames(found.live.text, roles)),
        botLine(
          AFTER_THE_STREAM,
          found.ended.author,
          withRoleNames(found.ended.text, roles),
          found.ended.footer,
        ),
      );
      say.say('');
    } catch (error) {
      const said = sentenceFor(error);
      say.say(said.text, said.tone);
    }
  };
  try {
    roles = await refRoles();
  } catch (error) {
    roles = [];
  }
  await paint();
  const node = card(WORDING_TITLE, [
    el('p', { class: 'field-help', text: WORDING_NOTE }),
    list,
    el('p', { class: 'field-help', text: WORDING_STALE }),
    say,
  ], {
    actions: [
      button('Refresh', () => paint(), { tone: 'quiet' }),
    ],
  });
  return { node, paint, heads };
}

async function announcementSection(specs, wordingSpecs) {
  const group = section('The announcement', ANNOUNCEMENT_NOTE);
  const spec = specs.find((one) => one.key === TEMPLATE_KEY);
  if (!spec) {
    group.body.append(el('p', { class: 'say-nothing', text: NO_TEMPLATE }));
    return group.node;
  }
  const shape = { which: TWITCH };
  const playing = el('input', { class: 'input switch', type: 'checkbox', checked: true });
  const prefix = await pingPrefix(specs);
  const endTemplate = specs.find((one) => one.key === END_TEMPLATE_KEY) || null;
  const endAuthor = specs.find((one) => one.key === END_AUTHOR_KEY) || null;
  const preview = await wordingPreview(notice());

  const liveShown = el('div', { class: 'preview discord-preview' });
  const liveMade = await templateEditor(spec, {
    controls: [playing],
    onSaved: () => preview.paint(),
    sample: () => ({
      ...SAMPLES[shape.which],
      game: playing.checked ? SAMPLES[shape.which].game : GAME_FALLBACK,
    }),
    paint: (filled) => {
      drawCard(liveShown, filled === null ? DEFAULT_TEMPLATE : `${prefix}${filled}`, preview.heads.live, preview.heads.roles);
    },
  });

  const endShown = {
    [END_TEMPLATE_KEY]: el('div', { class: 'preview discord-preview' }),
    [END_AUTHOR_KEY]: el('p', { class: 'preview' }),
  };
  const endHead = { text: '' };
  const blank = { [END_TEMPLATE_KEY]: END_BLANK_TEMPLATE, [END_AUTHOR_KEY]: END_BLANK_AUTHOR };
  let endMade = null;
  if (endTemplate) {
    const wanted = [{ ...endTemplate, editorType: 'longtext' }];
    if (endAuthor) wanted.push({ ...endAuthor, editorType: 'longtext' });
    endMade = await templateEditor(wanted, {
      where: END_WORDING_WHERE,
      onSaved: () => preview.paint(),
      sample: () => ({ ...SAMPLES[shape.which], ...ENDED_EXTRA }),
      paint: (filled, key) => {
        const node = endShown[key];
        if (!node) return;
        const empty = filled !== null && String(filled).trim() === '';
        if (key === END_AUTHOR_KEY) {
          endHead.text = empty || filled === null ? '' : String(filled);
          node.textContent = empty ? blank[key] : (filled === null ? '' : filled);
          node.classList.toggle('field-help', empty);
          return;
        }
        if (empty) {
          node.textContent = blank[key];
          node.classList.add('field-help');
          return;
        }
        node.classList.remove('field-help');
        drawCard(node, filled === null ? '' : filled, endHead.text || preview.heads.ended, preview.heads.roles);
      },
    });
  }

  const chips = el('div', { class: 'chipbar' });
  const paintChips = () => {
    chips.replaceChildren(...[TWITCH, YOUTUBE].map((which) => chipButton(
      `Preview as ${PLATFORM_WORDS[which]}`,
      shape.which === which,
      () => {
        shape.which = which;
        paintChips();
        liveMade.repaint();
        if (endMade) endMade.repaint();
      },
    )));
  };
  paintChips();

  const endRows = wordingSpecs.filter((one) => one.key === END_KEEP_KEY);

  group.body.append(
    chips,
    card(WHILE_LIVE_TITLE, [
      liveMade.row.node,
      el('div', { class: 'formrow' }, [
        field('Playing a game', playing, PLAYING_HELP),
      ]),
      liveShown,
      liveMade.say,
    ].filter(Boolean)),
    card(ENDED_TITLE, [
      el('p', { class: 'field-help', text: END_LIVE_HELP }),
      ...(endMade
        ? endMade.rows.map((row) => row.node)
        : [el('p', { class: 'say-nothing', text: END_NO_KEYS })]),
      endShown[END_AUTHOR_KEY],
      endShown[END_TEMPLATE_KEY],
      endRows.length
        ? await settingsPanel(endRows, { onSaved: () => preview.paint(), where: ENDED_TITLE })
        : null,
      endMade ? endMade.say : null,
    ].filter(Boolean)),
    preview.node,
  );
  return group.node;
}

const LINK_FROM_HISTORY = 'Link them';
const LINKED_ALREADY = '—';

/** A stream seen by presence alone is one press from a real link: the row already knows who and where. */
function linkFromHistory(row, linked, say) {
  const id = String(row.user_id || '');
  if (!id || id.startsWith('spotlight:') || linked.has(id) || !row.url) return muted(LINKED_ALREADY);
  const routed = routeTyped(String(row.url));
  if (!routed.where) return muted(LINKED_ALREADY);
  const who = row.user_name || id;
  return button(LINK_FROM_HISTORY, async () => {
    const sure = await ask({
      title: `Link ${who} to ${routed.value}?`,
      body: [
        `Black Bloc will watch ${routed.where === YOUTUBE ? 'that YouTube channel' : 'that Twitch channel'} for ${who} `
          + 'and announce them when they go live, instead of relying on their Discord status alone.',
      ],
      confirmLabel: 'Link them',
      tone: 'warn',
    });
    if (!sure) return;
    const done = await run(
      say,
      () => (routed.where === YOUTUBE
        ? send('/api/youtube/links', 'POST', { member_id: id, channel: routed.value })
        : send('/api/golive/links', 'POST', { user_id: id, twitch_login: routed.value })),
      (found) => found?.message || 'Linked.',
    );
    if (done.ok) {
      keepSaying(routed.where === YOUTUBE ? 'youtube.links' : 'golive.links', say);
      refresh();
    }
  }, { tone: 'warn' });
}

function recentSection(sessions, linked = new Set(), say = notice()) {
  const group = section('Recent streams', null, { count: sessions.length });
  group.body.append(table([
    { label: 'Member', cell: (row) => nameNode(row.user_id, row.user_name) },
    { label: 'Started', cell: (row) => when(row.started_at), className: 'mono' },
    {
      label: 'Ended',
      cell: (row) => (row.ended_at ? when(row.ended_at) : badge(LIVE_NOW, 'ok')),
      className: 'mono',
    },
    { label: 'Game', cell: (row) => row.game },
    { label: 'Title', cell: (row) => row.title, className: 'wrap' },
    { label: 'How', cell: (row) => (row.also_source ? `${row.source} + ${row.also_source}` : row.source) },
    { label: 'Mode then', cell: (row) => badge(row.mode, row.mode === 'on' ? 'ok' : 'warn') },
    { label: 'Link', cell: (row) => linkFromHistory(row, linked, say) },
  ], sessions, { empty: 'No streams have been seen yet.' }), say);
  return group.node;
}

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
  const train = button('Set up the raid-train role', async () => {
    const done = await run(
      say,
      () => send('/api/pings/raidtrain-role', 'POST', {}),
      (found) => found?.message || 'The raid-train role is set up.',
    );
    if (done.ok) {
      keepSaying('pings.raidtrain_setup', say);
      refresh();
    }
  }, { tone: 'warn' });
  return card('The shared roles', [
    el('p', { class: 'field-help', text: SETUP_HELP }),
    el('p', { class: 'field-help', text: RAID_HELP }),
    bar([go, train]),
  ]);
}

function onboardingLines(found) {
  if (!found) return [ONBOARDING_NO_COMMUNITY];
  const lines = [];
  if (!found.managed) lines.push(ONBOARDING_OFF);
  if (!found.community) lines.push(ONBOARDING_NO_COMMUNITY);
  if (lines.length) return lines;
  if (!(found.prompts || []).length) return [ONBOARDING_NOTHING];
  for (const prompt of found.prompts) {
    lines.push(`${prompt.title} — ${(prompt.options || []).join(', ') || 'nothing yet'}`);
  }
  if (found.more_on_pings) lines.push(`${found.more_on_pings} more streamer(s) are on /pings.`);
  if (found.foreign_prompts) {
    lines.push(`${found.foreign_prompts} prompt(s) belong to somebody else and are left alone.`);
  }
  return lines;
}

function onboardingCard(say, found) {
  const lines = onboardingLines(found).map((text) => el('p', { class: 'field-help', text }));
  const last = el('p', {
    class: 'field-help mono',
    text: found && found.last_synced_at
      ? `Last written: ${found.last_synced_at}`
      : ONBOARDING_NEVER,
  });
  const controls = [];
  if (found && found.community && found.managed) {
    controls.push(button('Sync now', async () => {
      const done = await run(
        say,
        () => send('/api/pings/onboarding/sync', 'POST', {}),
        (one) => one?.message || 'Onboarding is in step.',
      );
      if (done.ok) {
        keepSaying('pings.onboarding', say);
        refresh();
      }
    }, { tone: 'warn' }));
  }
  return card('Discord onboarding', [
    el('p', { class: 'field-help', text: ONBOARDING_NOTE }),
    ...lines,
    last,
    el('p', { class: 'field-help', text: ONBOARDING_WHERE }),
    controls.length ? bar(controls) : null,
  ].filter(Boolean));
}

function probeCard(status) {
  if (!status) return null;
  const rows = [
    ['Live streams', badge(status.live_mode || 'off', status.live_mode === 'on' ? 'ok' : 'warn')],
    ['Probe', status.live_running ? badge('running', 'ok') : badge('stopped', 'warn')],
    ['Last probe', status.last_probe_at ? when(status.last_probe_at) : 'never'],
    ['Last probe error', status.last_probe_error || 'none'],
    ['Channels probed', `${status.probed || 0}, every ${status.live_minutes} minute(s)`],
    ['Live now', `${status.live_now || 0}, ended after ${status.live_end_misses} quiet probe(s)`],
    ['Reading live now', `${status.reading_live || 0} channel(s)`],
    ['Quota used today', `${status.quota_today || 0} unit(s)`],
    ['Bot check', status.botcheck ? badge('yes — that page had no video id', 'warn') : 'no'],
  ];
  return card('How live streams are spotted', [
    el('p', { class: 'field-help', text: PROBE_NOTE }),
    el('div', { class: 'formrow' }, rows.map(([label, value]) => field(label, (
      typeof value === 'string' ? el('p', { class: 'preview', text: value }) : value
    )))),
    status.api_key_set ? null : el('p', { class: 'field-help', text: PROBE_KEY_UNSET }),
  ].filter(Boolean));
}

async function logDrawer() {
  const blocks = await Promise.all([
    logsSection('golive'),
    logsSection('youtube', { title: 'YouTube logs' }),
    logsSection('pings', { title: 'Ping role logs' }),
  ]);
  const holders = LOG_CHIPS.slice(1).map((one, at) => ({ id: one.id, node: unsection(blocks[at]) }));
  const chips = el('div', { class: 'chipbar' });
  const state = { pick: 'all' };
  const paint = () => {
    chips.replaceChildren(...LOG_CHIPS.map((one) => chipButton(one.label, state.pick === one.id, () => {
      state.pick = one.id;
      paint();
    })));
    for (const holder of holders) {
      holder.node.hidden = !(state.pick === 'all' || state.pick === holder.id);
    }
  };
  paint();
  return drawer('Log · both platforms and ping roles', [chips, ...holders.map((one) => one.node)]);
}

async function restSection({ placed, onboarding, status, pingHolder }) {
  const group = section('Everything else', REST_NOTE, { count: placed.drawers.length + 1 });
  const pingSay = notice();
  const drawers = [];
  for (const one of placed.drawers) {
    const panel = await settingsPanel(one.specs, {
      onSaved: () => refresh(),
      where: one.title,
      empty: NO_SETTINGS_HERE,
    });
    if (one.id === 'pings') {
      const node = drawer(
        `${one.title} · ${settingWord(one.specs.length)} · the shared roles · Discord onboarding`,
        [
          panel,
          setupCard(pingSay),
          onboardingCard(pingSay, onboarding),
          sayAgain('pings.setup', sayAgain('pings.raidtrain_setup', sayAgain('pings.onboarding', pingSay))),
        ],
      );
      pingHolder.node = node;
      drawers.push(node);
    } else if (one.id === 'spotted') {
      drawers.push(drawer(
        `${one.title} · ${settingWord(one.specs.length)} and the probe`,
        [panel, probeCard(status)],
      ));
    } else {
      drawers.push(drawer(`${one.title} · ${settingWord(one.specs.length)}`, [panel]));
    }
  }
  group.body.append(...drawers, await logDrawer());
  return group.node;
}

function warningsFor(golive, onboarding) {
  const lines = [];
  const events = golive.find((one) => one.key === PING_KEY);
  if (!events || !events.value) lines.push(NO_EVENTS_ROLE);
  if (onboarding && onboarding.managed && onboarding.community && !onboarding.last_synced_at) {
    lines.push(ONBOARDING_DRIFTED);
  }
  return lines;
}

function pageHead() {
  const subtitle = document.getElementById('subtitle');
  if (subtitle) subtitle.textContent = SUBTITLE;
  const aside = document.getElementById('page-aside');
  if (aside) aside.replaceChildren();
}

/** The two ways a row gets onto the list, beside the list (the owner: the page head was too far away). */
function streamerDoors() {
  const doors = el('div', { class: 'bar' }, [addStreamerButton(), addSpotlightButton()]);
  doors.style.marginLeft = 'auto';
  return doors;
}

async function load() {
  const [
    linkPayload,
    optoutPayload,
    sessionPayload,
    streamerPayload,
    listingPayload,
    onboardingPayload,
    youtubeLinkPayload,
    youtubeStatus,
    spotlightPayload,
    allSettings,
  ] = await Promise.all([
    api('/api/golive/links'),
    api('/api/golive/optouts'),
    api('/api/golive/sessions?limit=50'),
    api('/api/pings/streamers'),
    api('/api/pings/list'),
    api('/api/pings/onboarding'),
    api('/api/youtube/links'),
    api('/api/youtube/status'),
    api('/api/golive/spotlight'),
    settings(true),
  ]);
  const links = listOf(linkPayload, 'links');
  const optouts = listOf(optoutPayload, 'optouts');
  const sessions = listOf(sessionPayload, 'sessions');
  const streamers = listOf(streamerPayload, 'streamers');
  const listing = listOf(listingPayload, 'streamers');
  const youtubeLinks = listOf(youtubeLinkPayload, 'links');
  const spotlight = listOf(spotlightPayload, 'spotlight');
  await names(idsIn(links, ['user_id'])
    .concat(idsIn(optouts, ['user_id']))
    .concat(idsIn(sessions, ['user_id']))
    .concat(idsIn(youtubeLinks, ['user_id']))
    .concat(idsIn(listing, ['member_id', 'hidden_by']))
    .concat(idsIn(streamers, ['member_id', 'created_by'])));

  const rows = joinStreamers({
    links,
    youtubeLinks,
    optouts,
    listing,
    streamers,
    sessions,
    spotlight,
    status: youtubeStatus,
  });
  const cards = [...liveStreams(sessions), ...spotlightCards(spotlight)];
  const past = [...sessions, ...spotlightSessions(spotlight)].sort((a, b) => (
    String(b.started_at || '') < String(a.started_at || '') ? -1 : 1
  ));

  const golive = settingsNamespace(allSettings, 'golive');
  const pings = settingsNamespace(allSettings, 'pings');
  const nameSpec = pings.find((one) => one.key === 'pings_fan_role_template');
  if (nameSpec) pingsTemplate = String(nameSpec.value ?? nameSpec.default ?? pingsTemplate);
  const youtube = settingsNamespace(allSettings, 'youtube');
  const placed = placeSettings([...golive, ...pings, ...youtube]);

  const say = notice();
  pageHead();

  const pingHolder = { node: null };
  const openPings = () => {
    if (!pingHolder.node) return;
    const sect = pingHolder.node.closest('details.sect-card');
    if (sect) sect.open = true;
    pingHolder.node.open = true;
    pingHolder.node.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const rest = await restSection({
    placed,
    onboarding: onboardingPayload,
    status: youtubeStatus,
    pingHolder,
  });

  document.getElementById('dash').replaceChildren(
    headerStrip({
      golive,
      youtube,
      pings,
      rows,
      cards,
      status: youtubeStatus,
      warnings: warningsFor(golive, onboardingPayload),
      onOpenPings: openPings,
    }),
    liveSection(cards),
    streamersSection(rows, say),
    await announcementSection(golive, placed.wording),
    recentSection(past, new Set([...links, ...youtubeLinks].map((one) => String(one.user_id ?? one.member_id ?? ''))), say),
    rest,
  );
}

refresh = start({
  tab: 'golive',
  load,
});
