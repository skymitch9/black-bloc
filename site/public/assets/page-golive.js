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
  sentenceFor,
  table,
  templateEditor,
  when,
} from './ui.js';

let refresh = () => {};

const TEMPLATE_KEY = 'golive_template';
const PING_KEY = 'golive_ping_role_id';
const END_MODE_KEY = 'golive_end_mode';
const END_EDIT = 'edit';
const GAME_FALLBACK = 'something';
const DEFAULT_TEMPLATE = 'the default wording';

const END_UNKNOWN = 'The bot did not report a golive_end_mode key, so what happens once a stream '
  + 'ends is not shown rather than guessed at.';
const END_HELP = 'edit rewrites the announcement once the stream is over; off leaves it as '
  + 'posted. The Wording card below shows both.';

const WORDING_TITLE = 'Wording';
const WORDING_NOTE = 'Both messages as the bot itself renders them — the same functions Discord '
  + 'gets, not a copy living on this page. The sample is a two-hour stream of Celeste.';
const WORDING_LEFT = 'golive_end_mode is off, so an announcement is left exactly as posted. This '
  + 'is what edit would write instead.';
const WORDING_STALE = 'This card repaints itself whenever either wording above is saved. Refresh '
  + 'is for a change somebody else made, on the Settings page or from Discord.';
const WHILE_LIVE = 'while live';
const AFTER_THE_STREAM = 'after the stream';

const END_TEMPLATE_KEY = 'golive_end_template';
const SUFFIX_ONLY = 'Just add the ending instead';
const REWRITE_IT = 'Rewrite it instead';
const SUFFIX_ASK_TITLE = 'Leave the sentence alone and just add the ending?';
const SUFFIX_ASK_BODY = 'The announcement keeps its present-tense sentence and golive_end_suffix '
  + 'is added to the end of it, the way it worked before. The wording you have written is '
  + 'forgotten, so write it again to go back.';
const REWRITE_ASK_TITLE = 'Rewrite the whole announcement once the stream ends?';
const REWRITE_ASK_BODY = 'The past-tense wording Black Bloc ships with comes back, and you edit '
  + 'it in the Once the stream is over box above.';

const SAMPLE = {
  name: 'Casey',
  game: 'Lethal Company',
  title: 'late night runs',
  url: 'https://twitch.tv/caseyfast',
  platform: 'Twitch',
};

const END_AUTHOR_KEY = 'golive_end_author';
const END_WORDING_WHERE = 'Once the stream is over';
const END_WORDING_TITLE = 'What the ending looks like';
const END_WORDING_NOTE = 'As you type, filled in with the same sample and a two-hour '
  + '{duration}. The Wording card below is what the bot has actually stored.';
const END_BLANK_TEMPLATE = 'Empty — the live sentence is kept and golive_end_suffix is added to '
  + 'the end of it instead.';
const END_BLANK_AUTHOR = 'Empty — the card’s top line keeps saying “was live on”.';
const END_NO_KEYS = 'The bot did not report a golive_end_template key, so the ending is edited '
  + 'from the Settings group on the right rather than guessed at here.';
const ENDED_SAMPLE = { ...SAMPLE, duration: '2 h 10 min' };

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

async function wordingCard(spec, prefix, endSpec, onEndMode, onSaved) {
  const shown = el('p', { class: 'preview' });
  const playing = el('input', { class: 'input switch', type: 'checkbox', checked: true });

  const made = await templateEditor(spec, {
    controls: [playing],
    onSaved,
    sample: () => ({ ...SAMPLE, game: playing.checked ? SAMPLE.game : GAME_FALLBACK }),
    paint: (filled) => {
      shown.textContent = filled === null
        ? `Black Bloc would post ${DEFAULT_TEMPLATE} instead.`
        : `${prefix}${filled}`;
    },
  });

  const end = endSpec === null ? null : modeSwitch(endSpec, {
    label: 'The stream-end wording',
    onSaved: (key, value) => onEndMode(String(value)),
  });

  const preview = card('What an announcement looks like', [
    el('div', { class: 'formrow' }, [
      field('Playing a game', playing, `Off shows what an empty game reads as: “${GAME_FALLBACK}”.`),
      end ? field('When a stream ends', end.node, END_HELP) : null,
    ]),
    shown,
    end ? null : el('p', { class: 'field-help', text: END_UNKNOWN }),
    end ? end.say : null,
    made.say,
  ].filter(Boolean));
  return [made.row.node, preview];
}

/** C.2: the ended wording gets the editor the live one has — both keys, one save bar. */
async function endWordingCard(endTemplate, endAuthor, onSaved) {
  const drawn = {
    [END_TEMPLATE_KEY]: el('p', { class: 'preview' }),
    [END_AUTHOR_KEY]: el('p', { class: 'preview' }),
  };
  const blank = { [END_TEMPLATE_KEY]: END_BLANK_TEMPLATE, [END_AUTHOR_KEY]: END_BLANK_AUTHOR };
  const specs = [{ ...endTemplate, editorType: 'longtext' }];
  if (endAuthor) specs.push({ ...endAuthor, editorType: 'text' });

  const made = await templateEditor(specs, {
    where: END_WORDING_WHERE,
    sample: () => ENDED_SAMPLE,
    onSaved,
    paint: (filled, key) => {
      const node = drawn[key];
      if (!node) return;
      const empty = filled !== null && String(filled).trim() === '';
      node.textContent = empty ? blank[key] : (filled === null ? '' : filled);
      node.classList.toggle('field-help', empty);
    },
  });

  const preview = card(END_WORDING_TITLE, [
    el('p', { class: 'field-help', text: END_WORDING_NOTE }),
    drawn[END_AUTHOR_KEY],
    drawn[END_TEMPLATE_KEY],
    made.say,
  ]);
  return [...made.rows.map((row) => row.node), preview];
}

/** One rendered message, in the shape the modmail tab already draws a bot line in. */
function botLine(mark, line, text, footer) {
  return el('li', { class: 'msg', 'data-direction': 'out' }, [
    el('div', { class: 'msg-head' }, [
      badge(mark, mark === WHILE_LIVE ? 'ok' : 'quiet'),
      el('span', { text: line }),
    ]),
    el('p', { class: 'msg-body', text }),
    footer ? el('p', { class: 'msg-head', text: footer }) : null,
  ].filter(Boolean));
}

/** `<@&123>` reads as the role's name here; the bot sends the id, Discord draws the name. */
function withRoleNames(text, roles) {
  return String(text || '').replace(/<@&(\d+)>/g, (whole, id) => {
    const role = roles.find((one) => String(one.id) === id);
    return role ? `@${role.name}` : whole;
  });
}

/** The one control for "rewrite it" against "just add the ending": a blank golive_end_template
    is the second shape, and emptying a settings row restores the default rather than blanking it. */
function shapeButton(say, endTemplate) {
  const rewriting = String(endTemplate || '').trim() !== '';
  return button(rewriting ? SUFFIX_ONLY : REWRITE_IT, async () => {
    const sure = await ask({
      title: rewriting ? SUFFIX_ASK_TITLE : REWRITE_ASK_TITLE,
      body: [rewriting ? SUFFIX_ASK_BODY : REWRITE_ASK_BODY],
      confirmLabel: rewriting ? 'Just add the ending' : 'Rewrite it',
    });
    if (!sure) return;
    const done = await run(
      say,
      () => (rewriting
        ? send(`/api/settings/${END_TEMPLATE_KEY}`, 'PUT', { value: '' })
        : api(`/api/settings/${END_TEMPLATE_KEY}`, { method: 'DELETE' })),
      rewriting ? 'Saved — the ending is added to the live sentence again.' : 'Saved — the '
        + 'announcement is rewritten once the stream ends.',
    );
    if (done.ok) refresh();
  }, { tone: 'quiet' });
}

/** C: the Wording card — both renderings, read from the bot, never rendered here. */
async function wordingPreview(say, endMode, endTemplate) {
  const list = el('ul', { class: 'msglist' });
  const left = el('p', { class: 'field-help', text: WORDING_LEFT });
  let roles = [];
  const paint = async () => {
    try {
      const found = await api('/api/golive/preview');
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
    left,
    el('p', { class: 'field-help', text: WORDING_STALE }),
    say,
  ], {
    actions: [
      shapeButton(say, endTemplate),
      button('Refresh', () => paint(), { tone: 'quiet' }),
    ],
  });
  const showEnd = (mode) => { left.hidden = String(mode) === END_EDIT; };
  showEnd(endMode);
  return { node, paint, showEnd };
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
  const endSpec = specs.find((one) => one.key === END_MODE_KEY) || null;
  const endTemplate = specs.find((one) => one.key === END_TEMPLATE_KEY);
  const preview = await wordingPreview(
    notice(),
    endSpec ? endSpec.value : null,
    endTemplate ? (endTemplate.value ?? endTemplate.default) : '',
  );
  const onEndMode = (mode) => {
    preview.showEnd(mode);
    preview.paint();
  };
  const ended = endTemplate
    ? await endWordingCard(
      endTemplate,
      specs.find((one) => one.key === END_AUTHOR_KEY) || null,
      () => preview.paint(),
    )
    : [el('p', { class: 'say-nothing', text: END_NO_KEYS })];
  wording.body.append(
    ...await wordingCard(spec, prefix, endSpec, onEndMode, () => preview.paint()),
    ...ended,
    preview.node,
  );
  return wording.node;
}

const PINGS_MODE_KEY = 'pings_mode';
const PINGS_NOTE = 'One opt-in role for go-live and event pings, one for raid trains, and a '
  + 'role per streamer that only their followers wear. Members pick them with /pings, or from '
  + 'Discord’s onboarding screen once this is a Community server.';
const PINGS_NO_MODE = 'The bot did not report a pings_mode key, so the switch is not shown '
  + 'rather than guessed at.';
const NO_STREAMERS = 'Nobody has a ping role yet. Start one below, or a streamer starts their '
  + 'own from /pings.';
const NO_LISTED = 'The bot has not seen anybody streaming here yet. Nobody is added by hand — '
  + 'going live is what puts somebody on this list.';
const ROLE_GONE = 'deleted by hand';
const NO_ROLE_YET = 'none yet';
const HIDDEN = 'hidden';
const LISTED = 'listed';
const SETUP_HELP = 'Makes (or reuses) the Events role, points both feeds at it and puts it on '
  + 'the Notifications panel. Post that panel from the Role menus tab.';
const RAID_HELP = 'Makes (or reuses) the Raid trains role and points raidtrain_ping_role_id at '
  + 'it, so a member opts in from /pings instead of asking staff.';
const MODE_HELP = 'off stops every opt-in and every fan-role ping; nobody loses a role.';

const LIST_NOTE = 'Everybody the bot has ever seen streaming here. Hiding somebody stops new '
  + 'followers and stops a later go-live putting them back; it never takes a role off anybody '
  + 'who is wearing one.';
const HIDE_TITLE = 'Take {name} off the streamer list?';
const HIDE_BODY = 'Nobody new can follow them, and going live does not put them back. Their '
  + 'ping role goes too if nobody is wearing it.';

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
  + 'pings_onboarding_managed in the settings below, and Stop managing onboarding on /pings.';

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

/** C9: the streamer list, which the bot writes and staff only ever hide or restore from. */
function streamerList(say, rows) {
  return table([
    { label: 'Streamer', cell: (row) => nameNode(row.member_id, row.member) },
    {
      label: 'On the list',
      cell: (row) => (row.listed ? LISTED : badge(HIDDEN, 'warn')),
    },
    {
      label: 'Role',
      cell: (row) => (row.role || (row.role_id ? badge(ROLE_GONE, 'warn') : NO_ROLE_YET)),
    },
    {
      label: 'Followers',
      cell: (row) => (row.followers === null ? '—' : String(row.followers)),
      className: 'mono',
    },
    { label: 'Last live', cell: (row) => when(row.last_live_at), className: 'mono' },
    { label: 'Go-lives', cell: (row) => String(row.live_count), className: 'mono' },
    {
      label: '',
      cell: (row) => button(row.listed ? 'Hide' : 'Restore', async () => {
        if (row.listed) {
          const sure = await ask({
            title: HIDE_TITLE.replace('{name}', row.member || row.member_id),
            body: [HIDE_BODY],
            confirmLabel: 'Hide',
          });
          if (!sure) return;
        }
        const done = await run(
          say,
          () => send(`/api/pings/list/${encodeURIComponent(row.member_id)}`, 'POST', {
            listed: !row.listed,
          }),
          (found) => found?.message || 'Done.',
        );
        if (done.ok) {
          keepSaying('pings.streamer', say);
          refresh();
        }
      }, { tone: row.listed ? 'danger' : 'warn' }),
    },
  ], rows, { empty: NO_LISTED });
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

/** C9: what the bot's prompts hold and when they were last written. The managed switch is
    `pings_onboarding_managed` in the settings block below — one fact, one control. */
function onboardingCard(say, found) {
  const lines = onboardingLines(found).map(
    (text) => el('p', { class: 'field-help', text }),
  );
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

async function pingsSection(specs, streamers, listing, onboarding) {
  const say = notice();
  const group = section('Pings', PINGS_NOTE, { count: listing.length });
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
    el('p', { class: 'field-help', text: LIST_NOTE }),
    streamerList(say, listing),
    rows,
    setupCard(say),
    await streamerCard(say),
    onboardingCard(say, onboarding),
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
    listingPayload,
    onboardingPayload,
    uploadLinkPayload,
    uploadVideoPayload,
    uploadStatus,
    allSettings,
  ] = await Promise.all([
    api('/api/golive/links'),
    api('/api/golive/optouts'),
    api('/api/golive/sessions?limit=50'),
    api('/api/pings/streamers'),
    api('/api/pings/list'),
    api('/api/pings/onboarding'),
    api('/api/youtube/links'),
    api('/api/youtube/videos?limit=50'),
    api('/api/youtube/status'),
    settings(true),
  ]);
  const links = listOf(linkPayload, 'links');
  const optouts = listOf(optoutPayload, 'optouts');
  const sessions = listOf(sessionPayload, 'sessions');
  const streamers = listOf(streamerPayload, 'streamers');
  const listing = listOf(listingPayload, 'streamers');
  const uploadLinks = listOf(uploadLinkPayload, 'links');
  const uploads = listOf(uploadVideoPayload, 'videos');
  await names(idsIn(links, ['user_id'])
    .concat(idsIn(optouts, ['user_id']))
    .concat(idsIn(sessions, ['user_id']))
    .concat(idsIn(uploadLinks, ['user_id']))
    .concat(idsIn(uploads, ['user_id']))
    .concat(idsIn(listing, ['member_id', 'hidden_by']))
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
    await pingsSection(pings, streamers, listing, onboardingPayload),
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
