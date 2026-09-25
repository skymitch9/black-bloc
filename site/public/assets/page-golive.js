import { api, listOf, names, refRoles, send, settings, settingsNamespace } from './api.js';
import { start } from './app.js';
import {
  joinStreamers,
  liveStreams,
  pingSuffix,
  placeSettings,
  routeTyped,
  spotlightCards,
  spotlightSessions,
} from './golive-join.js';
import { logsSection } from './logs.js';
import {
  ago,
  ask,
  askForm,
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
  localWhen,
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
  segment,
  sentenceFor,
  settingsPanel,
  table,
  templateEditor,
  when,
  whenField,
} from './ui.js';

let refresh = () => {};

const TWITCH = 'twitch';
const YOUTUBE = 'youtube';
const PLATFORM_WORDS = { twitch: 'Twitch', youtube: 'YouTube' };

const TEMPLATE_KEY = 'golive_template';
const LIVE_AUTHOR_KEY = 'golive_live_author';
const PING_KEY = 'golive_ping_role_id';
const END_TEMPLATE_KEY = 'golive_end_template';
const END_AUTHOR_KEY = 'golive_end_author';
const END_KEEP_KEY = 'golive_end_keep_mention';
const GOLIVE_MODE_KEY = 'golive_mode';
const LIVE_MODE_KEY = 'youtube_live_mode';
const PINGS_MODE_KEY = 'pings_mode';
const SPOTLIGHT_MODE_KEY = 'spotlight_mode';
const CHANNEL_KEY = 'golive_channel_id';

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
  + 'that could be either is refused and says so. Leave the member blank for an org channel '
  + 'with nobody here behind it, like GamesDoneQuick.';
const ADD_FIELD_HELP = 'The name in twitch.tv/…, or the address that starts with '
  + 'youtube.com/channel/UC…, or their @handle.';
const ADD_PICK_FIRST = 'Pick the member this is about first.';
const ADD_NO_MEMBER_HELP = 'Leave this blank for a channel with nobody here behind it. It goes '
  + 'on the same list, is announced the same way, and its own row turns the spotlight, the '
  + 'ping role and announcements on and off.';
const ADD_CHANNEL_NEEDS_TWITCH = '**{given}** is a YouTube channel, and a channel with nobody '
  + 'behind it needs a Twitch name to hang on, so nothing was added. Put the name from '
  + 'twitch.tv/… here and link its YouTube channel on its own row afterwards.';
const SWEEP_TITLE = 'Link from history';
const SWEEP_ASK_TITLE = 'Link everyone the go-live history knows about?';
const SWEEP_ASK_BODY = 'Every person who has streamed here and has no channel linked is linked to '
  + 'the newest Twitch or YouTube address their go-live carried. Anybody who already has one, has '
  + 'asked not to be announced, or has left is left alone, and a channel that belongs to somebody '
  + 'else is refused by name rather than moved.';
const SWEEP_ASK_UNDO = 'Every link this makes can be undone one at a time with Unlink.';
const SWEEP_CONFIRM = 'Link them';
const SWEEP_DONE = 'The sweep ran.';
const SWEEP_SAID = 'golive.sweep';

const ANNOUNCEMENT_NOTE = 'One wording for both platforms. {platform} fills itself in.';
const WORDING_TITLE = 'The wording';
const STARTING = 'starting';
const ENDING = 'ending';
const SIDES = [
  { value: STARTING, label: 'Starting' },
  { value: ENDING, label: 'Ending' },
];
const SIDES_LABEL = 'Which announcement this edits';
const LIVE_WORDING_WHERE = 'While the stream is on';
const LIVE_HELP = 'The sentence and the card’s top line the moment they go live. The wording '
  + 'takes {name} {game} {title} {url} {platform}; the top line takes {name} and {platform} '
  + 'only, because a stream that is still running has no length yet.';
const END_LIVE_HELP = '{live} is the sentence exactly as it was posted, so “{live} — stream '
  + 'ended” adds to the end of it and a wording without {live} replaces the whole post. The '
  + 'rest of the fields are {name} {game} {title} {url} {platform} {duration}. The announcement '
  + 'is always edited once the stream is over.';
const END_NO_KEYS = 'The bot did not report a golive_end_template key, so the ending cannot be '
  + 'edited here rather than guessed at.';
const END_WORDING_WHERE = 'Once the stream is over';
const NO_TEMPLATE = 'The bot did not report a golive_template key, so this editor is not shown '
  + 'rather than guessed at.';
const MOCK_NOTE = 'Every box below is drawn by the bot itself — the same functions Discord gets, '
  + 'not a copy living on this page. The mock under each one repaints as you type. Starting and '
  + 'ending are the same two boxes, so they share one card.';
const LIVE_FEATURE = 'golive_live';
const ENDED_FEATURE = 'golive_ended';

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

const SETTINGS_TITLE = 'Settings and logs';
const SETTINGS_NOTE = 'Every go-live, YouTube and ping-role setting, in a drawer named for the '
  + 'question it answers, plus the log. Each drawer says what is inside before you open it, and '
  + 'each setting says what it does. All closed by default.';
const LOG_DRAWER_TITLE = 'Log · both platforms and ping roles';
const LOG_DRAWER_NOTE = 'What the bot actually did: announcements, links, ping roles and every '
  + 'refusal, filtered by feature with the chips inside.';
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
const PROBE_WALL_NOTE = 'From the bot’s datacenter address YouTube sometimes answers with its '
  + '"Sign in to confirm you’re not a bot" page. That page still says whether a channel is live, '
  + 'but not which video, and when it drops the live marker too the channel reads as offline.';
const PROBE_LINKS_KEYED = 'the stream’s own watch page — behind the bot check the id is searched '
  + 'for once per broadcast (100 units), and if the search finds nothing the channel’s /live page, '
  + 'titled Live now';
const PROBE_LINKS_KEYLESS = 'the stream’s watch page when YouTube shows it; behind the bot check '
  + 'the channel’s own /live page, titled Live now, with no thumbnail';
const PROBE_WALLED_YES = 'yes — the last page was the bot check';
const PROBE_IDS_NONE_LIVE = 'nobody reads as live';
const PROBE_IDS_ALL = 'found for every channel reading live';

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
const SPOTLIGHT_MEMBER_NOTE = 'Not spotlighted. Spotlighting a channel pins its announcement while it streams and reminds people every few hours — for a marathon, say. A linked Twitch account is preferred but not needed: the form takes any channel name.';
const SPOTLIGHT_ADD_TITLE = 'Spotlight a channel';
const SPOTLIGHT_ADD_HELP = 'For an org channel like GamesDoneQuick, or a marathon nobody here '
  + 'runs. Black Bloc announces it in the go-live channel whenever it goes live, reminds people '
  + 'while it runs, and pins the announcement for the duration.';
const SPOTLIGHT_DAYS_HELP = 'Days before it is purged. Leave it blank to keep it for ever, the '
  + 'way GamesDoneQuick is kept.';
// The owner's ask, 2026-09-22: "let me set a date range for start and end time".
const SPOTLIGHT_DATES = 'Dates';
const SPOTLIGHT_SAVE_DATES = 'Save dates';
const SPOTLIGHT_STARTS = 'Starts';
const SPOTLIGHT_ENDS = 'Ends';
const SPOTLIGHT_STARTS_HELP = 'When Black Bloc starts watching it. Leave it blank to start now '
  + '— nothing of its is announced, pinned or reminded before this.';
const SPOTLIGHT_ENDS_HELP = 'When the row is purged. Leave it blank to keep it for ever, the '
  + 'way GamesDoneQuick is kept.';
const SPOTLIGHT_SCHEDULED = 'scheduled';
const SPOTLIGHT_SCHEDULED_STATE = 'Scheduled — its start has not arrived, so nothing of its '
  + 'is announced, pinned or reminded yet.';
const NO_MEMBER = 'Nobody here \u2014 this is a channel Black Bloc watches by name.';
// The owner's ask, 2026-09-25: "I want GDQ to always be spotlighted, but I only want it to ping
// the marathon role during events". The state line itself is the bot's worded key.
const PINGS_TITLE = 'Pings';
const PING_MODE_CHOICES = [
  { value: 'always', label: 'Always' },
  { value: 'never', label: 'Never' },
  { value: 'events', label: 'During events' },
];
const PINGS_HELP = 'Only the role mentions change. The announcement, the pin and the reminders go '
  + 'out exactly as they do now, whichever of the three is picked.';
const WINDOWS_NONE = 'No window yet, so nothing it posts mentions a role.';
const ADD_WINDOW = 'Add a window…';
const WINDOW_TITLE = 'Add a ping window';
const WINDOW_HELP = 'While a window is open this channel mentions the go-live role and its own '
  + 'ping role. If it is already live when the window opens, one reminder that pings goes out.';
const WINDOW_STARTS = 'Pings start';
const WINDOW_ENDS = 'Pings stop';
const WINDOW_NOTE = 'What it is for';
const WINDOW_NOTE_HELP = 'Optional — for example AGDQ 2027. Shown beside the window here.';
const WINDOW_OPEN = 'open now';

const SPOTLIGHT_ON = 'Spotlight on';
const SPOTLIGHT_OFF = 'Spotlight off';
const CHANNEL_OPTED_OUT_STATE = 'Opted out \u2014 nothing of its is announced, whatever the '
  + 'spotlight says. The row, its ping role and its YouTube link all stay.';
const CHANNEL_OPT_OUT = 'Opt out of announcements';
const CHANNEL_OPT_IN = 'Opt back in';
const CHANNEL_LINK_YOUTUBE = 'Link a YouTube channel';
const CHANNEL_UNLINK_YOUTUBE = 'Unlink it';
const CHANNEL_YOUTUBE_HELP = 'The address that starts with youtube.com/channel/UC\u2026, or the '
  + '@handle. The same resolver a member\u2019s link goes through.';
const CHANNEL_REMOVE = 'Remove this channel';
const CHANNEL_REMOVE_ASK = 'Removes {name} from the list, its spotlight, its YouTube link and '
  + 'its ping role (per pings_fan_role_delete). Nothing in Discord is deleted except the role '
  + 'if that setting says so.';

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

function drawer(title, children, { open = false, note = null } = {}) {
  return el('details', { class: 'gldrawer', open: open || undefined }, [
    el('summary', { class: 'gldrawer-head' }, [
      icon('chevronDown', 14, 'sect-mark'),
      el('span', { class: 'gldrawer-heads' }, [
        el('span', { class: 'gldrawer-title', text: title }),
        note ? el('span', { class: 'gldrawer-note', text: note }) : null,
      ].filter(Boolean)),
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
let spotlightDefaultDays = 7;

const MAKE_ROLE = 'make';
const PICK_ROLE = 'pick';
const MAKE_ROLE_LABEL = 'Make a new role';
const PICK_ROLE_LABEL = 'Use an existing role';
const ROLE_NAME_LABEL = 'Role name';
const ROLE_NAME_MAX = 100;
const PING_ROLE_MEMBER = 'Members who press their name on /pings get this role, and it is pinged '
  + 'when they go live.';
const PING_ROLE_CHANNEL = 'Members who press this channel on /pings get this role, and it is '
  + 'pinged when the channel goes live — the announcement and, with spotlight_bump_pings on, the '
  + 'reminders.';
const ROLE_NAME_FREE = 'Black Bloc will make **{name}**.';
const ROLE_NAME_TAKEN = '⚠️ A role named **{name}** already exists — pick it under Use an '
  + 'existing role, or choose another name.';
const ROLE_NAME_BLANK = 'Type the name the role should have, or use an existing role instead.';
const ROLE_PICKED = 'That role becomes their ping role; nobody is added to it.';
const ROLE_PICK_ONE = 'Pick the role that becomes their ping role.';
const ROLE_MADE = 'Made the role.';
const ROLE_RENAMED = 'Renamed the role.';
const RENAME_ROLE_TITLE = "Rename {name}'s ping role";
const RENAME_ROLE_LINE = 'The Discord role is renamed where it stands — everybody wearing it keeps '
  + 'it, and the panels people follow from say the new name.';
const RENAME_ROLE_FREE = 'The role will be called **{name}**.';
const RENAME_ROLE_TAKEN = '⚠️ A role named **{name}** already exists — choose another name.';
const RENAME_ROLE_BLANK = 'Type the name the role should have.';
const RENAME_LABEL = 'Rename…';
const RENAME_CONFIRM = 'Rename the role';

/** `{name}` everywhere it appears, the way the bot's own template does — never a regexp. */
function fillName(template, name) {
  return String(template).split('{name}').join(name);
}

/** What Discord will take of a typed name; mirrors black_bloc/pings.py:typed_role_name. */
function tidyName(given) {
  return String(given ?? '').trim().replace(/\s+/g, ' ').slice(0, ROLE_NAME_MAX);
}

/** The roles this server has, folded for the live duplicate check both dialogs make. */
async function roleNamesHere() {
  return (await refRoles()).map((role) => tidyName(role.name).toLowerCase());
}

/** The Role name box and the sentence under it; `keep` is the name it may keep (a rename). */
function roleNameBox(value, here, { free = ROLE_NAME_FREE, taken = ROLE_NAME_TAKEN,
  blank = ROLE_NAME_BLANK, keep = null } = {}) {
  const typed = el('input', {
    class: 'input',
    type: 'text',
    maxlength: String(ROLE_NAME_MAX),
    set: { value },
  });
  const kept = tidyName(keep).toLowerCase();
  const check = (named) => {
    const wanted = tidyName(typed.value);
    if (!wanted) {
      named.say(blank, 'warn');
      return false;
    }
    if (wanted.toLowerCase() !== kept && here.includes(wanted.toLowerCase())) {
      named.say(fillName(taken, wanted), 'warn');
      return false;
    }
    named.say(fillName(free, wanted));
    return true;
  };
  return { typed, node: field(ROLE_NAME_LABEL, typed), check, read: () => tidyName(typed.value) };
}

/** The same door /pings has: a role named here and made, or one that already exists.
    A channel row asks by spotlight id, because there is no member behind it. */
async function addPingRole(row, say) {
  const who = row.name || row.user_id;
  const channel = spotlightOnly(row) ? row.spotlight.id : null;
  const roles = await roleSelect(null);
  const box = roleNameBox(fillName(pingsTemplate, who), await roleNamesHere());
  const making = segment(
    [{ value: MAKE_ROLE, label: MAKE_ROLE_LABEL }, { value: PICK_ROLE, label: PICK_ROLE_LABEL }],
    MAKE_ROLE,
    { onChange: () => showName() },
  );
  const picking = field(PICK_ROLE_LABEL, roles);
  const swap = el('div', {}, [box.node]);
  const named = notice();
  const held = { confirm: null };
  const showName = () => {
    const makes = making.readValue() === MAKE_ROLE;
    swap.replaceChildren(makes ? box.node : picking);
    let ready = true;
    if (makes) {
      ready = box.check(named);
    } else if (readSelect(roles, false)) {
      named.say(ROLE_PICKED);
    } else {
      named.say(ROLE_PICK_ONE, 'warn');
      ready = false;
    }
    if (held.confirm) held.confirm.disabled = !ready;
  };
  box.typed.addEventListener('input', showName);
  roles.addEventListener('change', showName);
  let made = null;
  const sure = await askForm({
    title: `Give ${who} a ping role`,
    body: [channel === null ? PING_ROLE_MEMBER : PING_ROLE_CHANNEL, making, swap, named],
    confirmLabel: 'Add the ping role',
    tone: 'warn',
    ready: ({ confirm }) => {
      held.confirm = confirm;
      showName();
    },
    onConfirm: async () => {
      const asks = channel === null ? { member_id: row.user_id } : { spotlight_id: channel };
      made = await send('/api/pings/streamers', 'POST', making.readValue() === MAKE_ROLE
        ? { ...asks, name: box.read() }
        : { ...asks, role_id: readSelect(roles, false) });
      return null;
    },
  });
  if (!sure) return;
  say.say(made?.message || ROLE_MADE, 'ok');
  keepSaying('pings.streamers', say);
  refresh();
}

/** The owner's "it should be editable right away": the role's name, on the row that made it. */
async function renamePingRole(row, say) {
  const who = row.name || row.user_id;
  const channel = spotlightOnly(row) ? row.spotlight.id : null;
  const box = roleNameBox(row.role || '', await roleNamesHere(), {
    free: RENAME_ROLE_FREE,
    taken: RENAME_ROLE_TAKEN,
    blank: RENAME_ROLE_BLANK,
    keep: row.role || '',
  });
  const named = notice();
  const held = { confirm: null };
  const showName = () => {
    const ready = box.check(named);
    if (held.confirm) held.confirm.disabled = !ready;
  };
  box.typed.addEventListener('input', showName);
  let done = null;
  const sure = await askForm({
    title: fillName(RENAME_ROLE_TITLE, who),
    body: [RENAME_ROLE_LINE, box.node, named],
    confirmLabel: RENAME_CONFIRM,
    tone: 'warn',
    ready: ({ confirm }) => {
      held.confirm = confirm;
      showName();
    },
    onConfirm: async () => {
      const where = channel === null
        ? `/api/pings/streamers/${encodeURIComponent(row.user_id)}`
        : `/api/pings/streamers/spotlight/${encodeURIComponent(channel)}`;
      done = await send(where, 'PATCH', { name: box.read() });
      return null;
    },
  });
  if (!sure) return;
  say.say(done?.message || ROLE_RENAMED, 'ok');
  keepSaying('pings.streamers', say);
  refresh();
}

async function roleMoves(row, say) {
  const moves = [];
  const channel = spotlightOnly(row) ? row.spotlight.id : null;
  if (row.role_id) {
    if (row.role) {
      moves.push(button(RENAME_LABEL, () => renamePingRole(row, say), { tone: 'warn' }));
    }
    moves.push(button('Remove', async () => {
      const sure = await ask({
        title: `Take ${row.name || row.user_id}'s ping role away?`,
        body: [
          'Everybody who followed them stops being pinged.',
          'Whether the Discord role itself is deleted is pings_fan_role_delete, in Settings and '
            + 'logs ▸ Ping roles.',
        ],
        confirmLabel: 'Remove',
      });
      if (!sure) return;
      const where = channel === null
        ? `/api/pings/streamers/${encodeURIComponent(row.user_id)}`
        : `/api/pings/streamers/spotlight/${encodeURIComponent(channel)}`;
      const done = await run(
        say,
        () => api(where, { method: 'DELETE' }),
        (found) => found?.message || 'Removed.',
      );
      if (done.ok) {
        keepSaying('pings.streamers', say);
        refresh();
      }
    }, { tone: 'danger' }));
  } else {
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
  const after = async (done) => {
    if (!done.ok) return;
    await redrawRow(row, say);
  };
  const patch = (body, fallback) => run(
    say,
    () => send(`/api/golive/spotlight/${one.id}`, 'PATCH', body),
    (found) => found?.message || fallback,
  );
  const spotlit = one.spotlight !== false;
  const moves = [
    button(spotlit ? SPOTLIGHT_OFF : SPOTLIGHT_ON, async () => (
      after(await patch({ spotlight: !spotlit }, spotlit ? 'Spotlight off.' : 'Spotlight on.'))
    ), { tone: spotlit ? 'quiet' : 'warn' }),
  ];
  // The kept / expires / bump / pin moves belong to the spotlight, so they only render
  // while it is on — never a control that would refuse.
  if (spotlit) {
    moves.push(button('Extend a week', async () => after(await patch({ days: 7 }, 'Extended.')), { tone: 'quiet' }));
    if (one.kept) {
      moves.push(button('Let it expire', async () => after(await patch({ days: 7 }, 'It runs out in a week.')), { tone: 'quiet' }));
    } else {
      moves.push(button('Keep for ever', async () => after(await patch({ keep: true }, 'Kept for ever.')), { tone: 'quiet' }));
    }
    if (one.live && one.announce !== false) {
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
  }
  return moves;
}

/** The owner's date range: two pickers and one Save, on every channel row's drawer. */
function datesCard(row, say) {
  const one = row.spotlight;
  const starts = whenField({
    label: SPOTLIGHT_STARTS,
    value: one.starts_at ? localWhen(one.starts_at) : '',
    help: SPOTLIGHT_STARTS_HELP,
  });
  const ends = whenField({
    label: SPOTLIGHT_ENDS,
    value: one.expires_at ? localWhen(one.expires_at) : '',
    help: SPOTLIGHT_ENDS_HELP,
  });
  const go = button(SPOTLIGHT_SAVE_DATES, async () => {
    const done = await run(
      say,
      () => send(`/api/golive/spotlight/${one.id}`, 'PATCH', {
        starts_at: starts.value() || null,
        expires_at: ends.value() || null,
        tz: starts.tz() || ends.tz() || null,
      }),
      (found) => found?.message || 'Dates saved.',
    );
    if (!done.ok) return;
    await redrawRow(row, say);
  }, { tone: 'quiet' });
  return el('div', { class: 'card-sub' }, [
    el('h4', { text: SPOTLIGHT_DATES }),
    el('span', { class: 'cell-quiet', text: one.scheduled ? SPOTLIGHT_SCHEDULED_STATE : (one.range || one.until) }),
    el('div', { class: 'formrow' }, [starts.node, ends.node]),
    el('div', { class: 'bar' }, [go]),
  ]);
}

/** The owner's split: when a channel pings, and the windows that decide it for an events row. */
/** A Pings-card write keeps the drawer open: the row takes the fresh answer and is drawn again. */
async function redrawRow(row, say) {
  const one = row.spotlight;
  const fresh = listOf(await api('/api/golive/spotlight'), 'spotlight').find((it) => it.id === one.id);
  if (fresh) row.spotlight = fresh;
  keepSaying('golive.spotlight', say);
  refresh();
  openDrawer(row.name || row.user_id, await rowPanel(row, say));
}

function pingsCard(row, say) {
  const one = row.spotlight;
  const current = one.ping_mode || 'always';
  const after = async (done) => {
    if (!done.ok) return;
    await redrawRow(row, say);
  };
  const mode = segment(PING_MODE_CHOICES, current, {
    onChange: async () => {
      const wanted = mode.readValue();
      if (wanted === current) return;
      after(await run(
        say,
        () => send(`/api/golive/spotlight/${one.id}`, 'PATCH', { ping_mode: wanted }),
        (found) => found?.message || 'Pings changed.',
      ));
    },
  });
  const bits = [
    el('span', { class: 'cell-quiet', text: one.ping_state || '' }),
    mode,
    el('p', { class: 'field-help', text: PINGS_HELP }),
  ];
  if (current === 'events') {
    const windows = one.windows || [];
    if (!windows.length) bits.push(muted(WINDOWS_NONE));
    for (const span of windows) {
      bits.push(el('div', { class: 'bar' }, [
        el('span', { text: `${when(span.starts_at)} – ${when(span.ends_at)}` }),
        span.note ? el('span', { class: 'cell-quiet', text: span.note }) : null,
        span.open ? badge(WINDOW_OPEN, 'ok') : null,
        span.staff
          ? button('Remove', async () => after(await run(
            say,
            () => send(`/api/golive/spotlight/${one.id}/windows/${span.id}`, 'DELETE'),
            (found) => found?.message || 'Window removed.',
          )), { tone: 'quiet' })
          : badge(span.source_words || span.source),
      ].filter(Boolean)));
    }
    bits.push(el('div', { class: 'bar' }, [
      button(ADD_WINDOW, () => addWindow(row, say), { tone: 'quiet' }),
    ]));
  }
  return card(PINGS_TITLE, bits);
}

/** A dialog like Add a ping role: two pickers and a note, read by the same route parsing. */
async function addWindow(row, say) {
  const one = row.spotlight;
  const starts = whenField({ label: WINDOW_STARTS });
  const ends = whenField({ label: WINDOW_ENDS });
  const note = el('input', { class: 'input', type: 'text', maxlength: '100', placeholder: 'AGDQ 2027' });
  let made = null;
  const sure = await askForm({
    title: WINDOW_TITLE,
    body: [
      WINDOW_HELP,
      el('div', { class: 'formrow' }, [starts.node, ends.node]),
      field(WINDOW_NOTE, note, WINDOW_NOTE_HELP),
    ],
    confirmLabel: 'Add the window',
    tone: 'warn',
    onConfirm: async () => {
      made = await send(`/api/golive/spotlight/${one.id}/windows`, 'POST', {
        starts_at: starts.value() || null,
        ends_at: ends.value() || null,
        note: note.value.trim() || null,
        tz: starts.tz() || ends.tz() || null,
      });
      return null;
    },
  });
  if (!sure) return;
  say.say(made?.message || 'Window added.', 'ok');
  await redrawRow(row, say);
}

function channelAnnounceMoves(row, say) {
  const one = row.spotlight;
  const out = one.announce === false;
  return [button(out ? CHANNEL_OPT_IN : CHANNEL_OPT_OUT, async () => {
    const done = await run(
      say,
      () => send(`/api/golive/spotlight/${one.id}`, 'PATCH', { announce: out }),
      (found) => found?.message || (out ? 'Opted back in.' : 'Opted out.'),
    );
    if (!done.ok) return;
    keepSaying('golive.spotlight', say);
    closeDrawer();
    refresh();
  }, { tone: out ? 'quiet' : 'warn' })];
}

function channelYoutubeMoves(row, say) {
  const one = row.spotlight;
  const after = (done) => {
    if (!done.ok) return;
    keepSaying('golive.spotlight', say);
    closeDrawer();
    refresh();
  };
  if (one.youtube_channel_id) {
    return [
      el('a', {
        class: 'btn small quiet',
        href: one.youtube_url || `https://www.youtube.com/channel/${one.youtube_channel_id}`,
        rel: 'noreferrer',
        text: 'Open channel',
      }),
      button(CHANNEL_UNLINK_YOUTUBE, async () => {
        const yes = await ask({
          title: `Unlink ${one.twitch_login}'s YouTube channel?`,
          body: [`Black Bloc stops watching ${one.youtube_handle || one.youtube_channel_id} for live streams. Its Twitch side and everything else about the row stay as they are.`],
          confirmLabel: 'Unlink it',
        });
        if (!yes) return;
        after(await run(
          say,
          () => send(`/api/golive/spotlight/${one.id}`, 'PATCH', { youtube: null }),
          (found) => found?.message || 'Unlinked.',
        ));
      }, { tone: 'danger' }),
    ];
  }
  const box = el('input', {
    class: 'input',
    type: 'text',
    placeholder: 'youtube.com/channel/UC… or @handle',
  });
  return [
    box,
    button(CHANNEL_LINK_YOUTUBE, async () => {
      after(await run(
        say,
        () => send(`/api/golive/spotlight/${one.id}`, 'PATCH', { youtube: box.value.trim() }),
        (found) => found?.message || 'Linked.',
      ));
    }, { tone: 'warn' }),
  ];
}

function channelRemoveMoves(row, say) {
  const one = row.spotlight;
  return [button(CHANNEL_REMOVE, async () => {
    const yes = await ask({
      title: `${CHANNEL_REMOVE}?`,
      body: [CHANNEL_REMOVE_ASK.replace('{name}', one.display_name || one.twitch_login)],
      confirmLabel: 'Remove it',
    });
    if (!yes) return;
    const done = await run(
      say,
      () => api(`/api/golive/spotlight/${one.id}`, { method: 'DELETE' }),
      (found) => found?.message || 'Off the list.',
    );
    if (!done.ok) return;
    keepSaying('golive.spotlight', say);
    closeDrawer();
    refresh();
  }, { tone: 'danger' })];
}

/** Only facts a person cannot see elsewhere in the card: the note, the event it was set up for. */
function spotlightQuiet(row) {
  const one = row.spotlight;
  const bits = [];
  if (one.event_id) bits.push(`Set up for event #${one.event_id}.`);
  if (one.note) bits.push(one.note);
  return bits.length ? el('span', { class: 'cell-quiet', text: bits.join(' ') }) : null;
}


const MARATHONS_CHOICES = [{ value: 'on', label: 'Marathons: on' }, { value: 'off', label: 'off' }];
const MARATHONS_OFF_SAID = 'Marathons: off — no feed checks for it, nothing can be added on it, and its marathons are paused until it is turned back on.';
const NO_MARATHONS = 'no marathons';

function takesMarathons(one) {
  return Boolean(one) && one.marathons !== false;
}

function channelMarathonsMoves(row, say) {
  const one = row.spotlight;
  const chips = segment(MARATHONS_CHOICES, takesMarathons(one) ? 'on' : 'off', {
    onChange: async () => {
      const wanted = chips.readValue() === 'on';
      if (wanted === takesMarathons(one)) return;
      const done = await run(
        say,
        () => send(`/api/golive/spotlight/${one.id}`, 'PATCH', { marathons: wanted }),
        (found) => found?.message || (wanted ? 'Marathons on.' : 'Marathons off.'),
      );
      if (!done.ok) {
        chips.setValue(takesMarathons(one) ? 'on' : 'off');
        return;
      }
      keepSaying('golive.spotlight', say);
      closeDrawer();
      refresh();
    },
  });
  return [chips];
}

function marathonsSuffix(one) {
  return takesMarathons(one) ? '' : ` · ${NO_MARATHONS}`;
}

function channelAnnouncementsSaid(row) {
  const said = announcedSaidFor(row);
  if (takesMarathons(row.spotlight)) return said;
  return el('span', {}, [said, el('span', { class: 'cell-quiet', text: ` ${MARATHONS_OFF_SAID}` })]);
}

function announcedSaidFor(row) {
  return el('span', {
    text: row.spotlight.announce === false
      ? CHANNEL_OPTED_OUT_STATE
      : 'On — announced in the go-live channel whenever it goes live.',
  });
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

  if (spotlightOnly(row)) {
    const channelYoutube = row.spotlight.youtube_channel_id
      ? el('span', {}, [
        el('span', { text: row.spotlight.youtube_handle || row.spotlight.youtube_channel_id }),
        el('span', { class: 'mono glid', text: row.spotlight.youtube_channel_id }),
      ])
      : muted(NOT_LINKED);
    return [
      card('Spotlight', [
        spotlightQuiet(row),
        el('div', { class: 'bar' }, spotlightMoves(row, say)),
        datesCard(row, say),
      ].filter(Boolean)),
      pingsCard(row, say),
      panelGroup('Twitch', twitchSaid, twitchMoves(row, say).slice(0, 1)),
      panelGroup('YouTube', channelYoutube, channelYoutubeMoves(row, say)),
      panelGroup('Ping role', roleSaid, await roleMoves(row, say)),
      panelGroup('Announcements', channelAnnouncementsSaid(row), [...channelAnnounceMoves(row, say), ...channelMarathonsMoves(row, say)]),
      panelGroup('Remove', el('span', { class: 'cell-quiet', text: NO_MEMBER }), channelRemoveMoves(row, say)),
      say,
    ];
  }
  return [
    ...(row.spotlight
      ? [
        card('Spotlight', [
          spotlightQuiet(row),
          el('div', { class: 'bar' }, spotlightMoves(row, say)),
          datesCard(row, say),
        ].filter(Boolean)),
        pingsCard(row, say),
      ]
      // Owner, 2026-09-21: a link is PREFERRED but never required to spotlight, so the move
      // renders whether or not they have one; with no link the form's box starts empty.
      : [panelGroup('Spotlight', el('span', { class: 'cell-quiet', text: SPOTLIGHT_MEMBER_NOTE }), [
        button('Spotlight this channel…', () => openSpotlightForm(row.twitch || ''), { tone: 'quiet' }),
      ])]),
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
  if (row.spotlight && row.spotlight.spotlight !== false) {
    return el('span', { class: 'cell-quiet' }, [
      el('span', {
        text: (row.spotlight.announced || row.spotlight.range || row.spotlight.until)
          + pingSuffix(row.spotlight)
          + (spotlightOnly(row) ? marathonsSuffix(row.spotlight) : ''),
      }),
      row.spotlight.scheduled ? badge(SPOTLIGHT_SCHEDULED, 'warn') : null,
    ].filter(Boolean));
  }
  if (spotlightOnly(row) && !takesMarathons(row.spotlight)) return muted(`${READY} · ${NO_MARATHONS}`);
  return muted(READY);
}

function expiresCell(row) {
  // A row whose spotlight is off never expires, so the cell says nothing rather than a date
  // the sweep would ignore.
  if (!row.spotlight || row.spotlight.spotlight === false) return muted('—');
  if (row.spotlight.kept && !row.spotlight.starts_at) {
    return el('span', { class: 'cell-kind' }, [badge('kept for ever', 'ok')]);
  }
  return el('span', { class: 'cell-quiet', text: row.spotlight.range || row.spotlight.until });
}

function optedOutCell(row) {
  return row.opted_out ? el('span', { class: 'cell-kind' }, [badge(OPTED_OUT, 'warn')]) : muted('—');
}

/** A row with no member behind it: the join gives it a `spotlight:<id>` id of its own. */
function spotlightOnly(row) {
  return String(row.user_id).startsWith('spotlight:') && Boolean(row.spotlight);
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

// A scheduled row is a spotlight that has not started; the chip keeps it, because a staffer
// looking for "what is spotlighted" means the list they curate, not only the ones running now.
function spotlightChip(row) {
  return Boolean(row.spotlight) && row.spotlight.spotlight !== false;
}

function scheduledChip(row) {
  return Boolean(row.spotlight && row.spotlight.scheduled);
}

const FILTERS = [
  { id: 'all', label: 'All', keep: () => true },
  { id: 'live', label: 'Live now', keep: (row) => Boolean(row.live) },
  { id: 'yt', label: 'Has YouTube', keep: (row) => Boolean(row.youtube) },
  { id: 'notyt', label: 'Twitch only', keep: (row) => Boolean(row.twitch) && !row.youtube },
  { id: 'out', label: 'Opted out', keep: (row) => row.opted_out === true },
  { id: 'spot', label: 'Spotlight', keep: spotlightChip },
  { id: 'chan', label: 'Channels', keep: (row) => Boolean(row.spotlight) },
  { id: 'kept', label: 'Kept forever', keep: (row) => Boolean(row.spotlight && row.spotlight.kept) },
  { id: 'sched', label: 'Scheduled', keep: scheduledChip },
];

function spotlightWords(rows) {
  const channels = rows.filter((row) => row.spotlight);
  const spots = channels.filter(spotlightChip).length;
  const out = channels.filter((row) => row.spotlight.announce === false).length;
  const soon = channels.filter(scheduledChip).length;
  const said = `${channels.length} channel(s) with no member · ${spots} spotlighted · ${out} opted out`;
  return soon ? `${said} · ${soon} ${SPOTLIGHT_SCHEDULED}` : said;
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

/** The form opens on spotlight_default_days out, which is what the key is for. */
function defaultEnd() {
  const days = Number(spotlightDefaultDays) || 7;
  return new Date(Date.now() + days * 24 * 60 * 60 * 1000);
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
    const starts = whenField({ label: SPOTLIGHT_STARTS, help: SPOTLIGHT_STARTS_HELP });
    const ends = whenField({
      label: SPOTLIGHT_ENDS,
      value: localWhen(defaultEnd()),
      help: SPOTLIGHT_ENDS_HELP,
    });
    const voice = notice();
    const go = button('Spotlight it', async () => {
      const done = await run(
        voice,
        () => send('/api/golive/spotlight', 'POST', {
          twitch_login: box.value,
          starts_at: starts.value() || null,
          expires_at: ends.value() || null,
          tz: starts.tz() || ends.tz() || null,
          spotlight: true,
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
      el('div', { class: 'formrow' }, [starts.node, ends.node]),
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
      const routed = routeTyped(box.value);
      if (!routed.where) {
        voice.say(routed.why, 'warn');
        return;
      }
      // No member picked: this is a channel with nobody behind it, so it goes on the same
      // list as a spotlight row — which is what makes it persist.
      if (!picker.id) {
        if (routed.where === YOUTUBE) {
          voice.say(ADD_CHANNEL_NEEDS_TWITCH.replace('{given}', box.value.trim()), 'warn');
          return;
        }
        const made = await run(
          voice,
          () => send('/api/golive/spotlight', 'POST', { twitch_login: routed.value }),
          (found) => found?.message || 'On the list.',
        );
        if (made.ok) {
          keepSaying('golive.spotlight', voice);
          closeDrawer();
          refresh();
        }
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
      el('p', { class: 'field-help', text: ADD_NO_MEMBER_HELP }),
      el('div', { class: 'formrow' }, [field('Twitch name or YouTube channel', box, ADD_FIELD_HELP)]),
      bar([go]),
      voice,
    ]);
  });
}

async function announcementSection(specs, wordingSpecs) {
  const group = section('The announcement', ANNOUNCEMENT_NOTE);
  const spec = specs.find((one) => one.key === TEMPLATE_KEY);
  if (!spec) {
    group.body.append(el('p', { class: 'say-nothing', text: NO_TEMPLATE }));
    return group.node;
  }
  const shape = { which: TWITCH, side: STARTING };
  const liveAuthor = specs.find((one) => one.key === LIVE_AUTHOR_KEY) || null;
  const endTemplate = specs.find((one) => one.key === END_TEMPLATE_KEY) || null;
  const endAuthor = specs.find((one) => one.key === END_AUTHOR_KEY) || null;

  /** The facts the BOT makes the sample announcement out of; the chips move the platform. */
  const facts = () => ({
    platform: shape.which,
    game: SAMPLES[shape.which].game,
  });

  const liveWanted = [{ ...spec, editorType: 'longtext' }];
  if (liveAuthor) liveWanted.push({ ...liveAuthor, editorType: 'longtext' });
  const liveMade = await templateEditor(liveWanted, {
    where: LIVE_WORDING_WHERE,
    sample: () => ({ ...SAMPLES[shape.which] }),
    preview: { feature: LIVE_FEATURE, sample: facts },
  });

  let endMade = null;
  if (endTemplate) {
    const wanted = [{ ...endTemplate, editorType: 'longtext' }];
    if (endAuthor) wanted.push({ ...endAuthor, editorType: 'longtext' });
    endMade = await templateEditor(wanted, {
      where: END_WORDING_WHERE,
      sample: () => ({ ...SAMPLES[shape.which], ...ENDED_EXTRA }),
      preview: { feature: ENDED_FEATURE, sample: facts },
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

  const starting = el('div', { 'data-side': STARTING }, [
    el('p', { class: 'field-help', text: LIVE_HELP }),
    ...liveMade.rows.map((row) => row.node),
    liveMade.mock.node,
    liveMade.mock.say,
    liveMade.say,
  ].filter(Boolean));

  const ending = el('div', { 'data-side': ENDING, hidden: true }, [
    el('p', { class: 'field-help', text: END_LIVE_HELP }),
    ...(endMade
      ? endMade.rows.map((row) => row.node)
      : [el('p', { class: 'say-nothing', text: END_NO_KEYS })]),
    endMade ? endMade.mock.node : null,
    endMade ? endMade.mock.say : null,
    endRows.length
      ? await settingsPanel(endRows, {
        onSaved: () => { if (endMade) endMade.repaint(); },
        where: END_WORDING_WHERE,
      })
      : null,
    endMade ? endMade.say : null,
  ].filter(Boolean));

  const sides = segment(SIDES, shape.side, {
    onChange: () => {
      shape.side = sides.readValue() || STARTING;
      starting.hidden = shape.side !== STARTING;
      ending.hidden = shape.side !== ENDING;
    },
  });
  sides.setAttribute('aria-label', SIDES_LABEL);

  group.body.append(
    el('p', { class: 'field-help', text: MOCK_NOTE }),
    chips,
    card(WORDING_TITLE, [starting, ending], { actions: [sides] }),
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
      cell: (row) => {
        let rehearsal = null;
        if (row.mode && row.mode !== 'on') {
          rehearsal = badge('rehearsal', 'warn');
          rehearsal.title = 'posted into the shadow channel, not the go-live channel';
        }
        return el('span', { class: 'cell-ended' }, [
          row.ended_at ? when(row.ended_at) : badge(LIVE_NOW, 'ok'),
          rehearsal,
        ]);
      },
      className: 'mono',
    },
    { label: 'Game', cell: (row) => row.game },
    { label: 'Title', cell: (row) => row.title, className: 'wrap' },
    { label: 'How', cell: (row) => (row.also_source ? `${row.source} + ${row.also_source}` : row.source) },
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
    ['Bot check', status.botcheck ? badge(PROBE_WALLED_YES, 'warn') : 'no'],
    ['Behind the bot check now', status.walled
      ? badge(`${status.walled} channel(s)`, 'warn') : 'none'],
    ['Video id', probeIds(status)],
    ['What a post links', status.api_key_set ? PROBE_LINKS_KEYED : PROBE_LINKS_KEYLESS],
  ];
  return card('How live streams are spotted', [
    el('p', { class: 'field-help', text: PROBE_NOTE }),
    el('div', { class: 'formrow' }, rows.map(([label, value]) => field(label, (
      typeof value === 'string' ? el('p', { class: 'preview', text: value }) : value
    )))),
    status.walled || status.botcheck ? el('p', { class: 'field-help', text: PROBE_WALL_NOTE }) : null,
    status.api_key_set ? null : el('p', { class: 'field-help', text: PROBE_KEY_UNSET }),
  ].filter(Boolean));
}

function probeIds(status) {
  if (!status.reading_live) return PROBE_IDS_NONE_LIVE;
  if (!status.id_unknown) return PROBE_IDS_ALL;
  return badge(`unknown for ${status.id_unknown} of ${status.reading_live} — the post links the `
    + 'channel’s /live page', 'warn');
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
  return drawer(LOG_DRAWER_TITLE, [chips, ...holders.map((one) => one.node)], {
    note: LOG_DRAWER_NOTE,
  });
}

async function restSection({ placed, onboarding, status, pingHolder }) {
  const shown = placed.drawers.filter((one) => one.id !== 'rest' || one.specs.length > 0);
  const group = section(SETTINGS_TITLE, SETTINGS_NOTE, { count: shown.length + 1 });
  const pingSay = notice();
  const drawers = [];
  for (const one of shown) {
    const panel = await settingsPanel(one.specs, {
      onSaved: () => refresh(),
      where: one.title,
      empty: NO_SETTINGS_HERE,
    });
    const head = `${one.title} · ${settingWord(one.specs.length)}`;
    if (one.id === 'pings') {
      const node = drawer(`${head} · the shared roles · Discord onboarding`, [
        panel,
        setupCard(pingSay),
        onboardingCard(pingSay, onboarding),
        sayAgain('pings.setup', sayAgain('pings.raidtrain_setup', sayAgain('pings.onboarding', pingSay))),
      ], { note: one.note });
      pingHolder.node = node;
      drawers.push(node);
    } else if (one.id === 'spotted') {
      drawers.push(drawer(`${head} and the probe`, [panel, probeCard(status)], { note: one.note }));
    } else {
      drawers.push(drawer(head, [panel], { note: one.note }));
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
  const voice = sayAgain(SWEEP_SAID, notice());
  const sweep = button(SWEEP_TITLE, async () => {
    const sure = await ask({
      title: SWEEP_ASK_TITLE,
      body: [SWEEP_ASK_BODY, SWEEP_ASK_UNDO],
      confirmLabel: SWEEP_CONFIRM,
    });
    if (!sure) return;
    const done = await run(
      voice,
      () => send('/api/golive/links/sweep', 'POST', {}),
      (found) => found?.message || SWEEP_DONE,
    );
    if (done.ok) {
      keepSaying(SWEEP_SAID, voice);
      refresh();
    }
  }, { tone: 'quiet' });
  const doors = el('div', {}, [
    el('div', { class: 'bar' }, [addStreamerButton(), addSpotlightButton(), sweep]),
    voice,
  ]);
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
  const daysSpec = golive.find((one) => one.key === 'spotlight_default_days');
  if (daysSpec) spotlightDefaultDays = Number(daysSpec.value ?? daysSpec.default ?? spotlightDefaultDays);
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
