/* The one home for what a settings key is CALLED. /api/settings carries a key,
   a type and a help sentence but no label, so the label lives here rather than
   in whichever page happens to draw the row. A key with no entry falls back to
   a tidied-up version of itself, so a new registry key still reads.
   See docs/info/code-notes.md § site/public/assets/labels.js. */

export const LABELS = {
  log_channel_id: 'Where the bot writes its log',
  staff_channel_id: 'Which channel decides who counts as staff',
  role_menu_channel_id: 'Where role menus are posted',
  core_log_level: 'How much of the dashboard’s own work is repeated into Discord',
  bot_bio: 'What the bot’s About Me says',
  status_prefix: 'What the bot’s status says',
  emoji_skin_tone: 'Which skin tone the bot’s emoji wear',

  golive_mode: 'Whether the bot announces streams',
  golive_channel_id: 'Where a go-live announcement is posted',
  golive_template: 'What a go-live announcement says',
  golive_embed: 'Whether the announcement is posted as an embed',
  golive_end_mode: 'What happens when a stream ends',
  golive_end_suffix: 'What is added once a stream has ended',
  golive_live_role_id: 'Which role a live streamer wears',
  golive_require_role_id: 'Only announce people with this role',
  golive_ignore_role_id: 'Never announce people with this role',
  golive_cooldown_minutes: 'How long before the same person is announced again',
  golive_ping_role_id: 'Who is pinged when someone goes live',
  golive_max_session_hours: 'How long a stream may run before it is closed',
  golive_log_level: 'How much of go-live is repeated into Discord',

  youtube_mode: 'Whether the bot posts new YouTube uploads',
  youtube_channel_id: 'Where an upload announcement is posted',
  youtube_ping_role_id: 'Who is pinged when somebody uploads',
  youtube_ping_fan_roles: 'Whether the uploader’s own fans are pinged too',
  youtube_announce_shorts: 'Whether Shorts are announced as well',
  youtube_template: 'What an upload announcement says',
  youtube_poll_minutes: 'How often the bot checks for new uploads',
  youtube_log_level: 'How much of uploads is repeated into Discord',

  pings_mode: 'Whether people can opt in to pings',
  pings_events_role_name: 'What the shared Events role is called',
  pings_fan_role_creation: 'Who may start a streamer’s own ping role',
  pings_fan_role_template: 'What a streamer’s ping role is called',
  pings_fan_role_on_unlink: 'What happens to it when they unlink or opt out',
  pings_fan_role_delete: 'Whether removing one deletes the Discord role too',
  pings_log_level: 'How much of ping roles is repeated into Discord',

  tempvoice_mode: 'Whether people can make their own voice rooms',
  tempvoice_creator_ids: 'Which channels people join to get a room',
  tempvoice_name_template: 'What a new room is called',
  tempvoice_creator_name: 'What the join-to-create channel is called',
  tempvoice_allowed_role_id: 'Who is allowed a room of their own',
  tempvoice_log_level: 'How much of temp voice is repeated into Discord',

  honeypot_mode: 'Whether the trap is armed',
  honeypot_channel_ids: 'Which channels are traps',
  honeypot_purge_days: 'How many days of messages a trip deletes',
  honeypot_exempt_role_ids: 'Which roles the trap ignores',
  honeypot_log_level: 'How much of the honeypot is repeated into Discord',

  events_mode: 'Whether members can put events on',
  events_category_id: 'Where an event waits to be looked at',
  events_announce_channel_id: 'Where an approved event is announced',
  events_ping_role_id: 'Who is pinged about an event',
  events_create_scheduled: 'Whether Discord gets a scheduled event too',
  events_channel_retention_days: 'How long an event keeps its channel',
  events_max_late_minutes: 'How late an event may start before it is dropped',
  events_log_level: 'How much of events is repeated into Discord',

  poll_mode: 'Whether people can run polls',
  poll_who_can_create: 'Who may start a poll',
  poll_review_mode: 'Whether staff see a poll before it runs',
  poll_default_hours: 'How long a poll runs when nobody says',
  poll_channel_id: 'Where a poll is posted',
  poll_ping_role_id: 'Who is pinged about a poll',
  poll_reminder_minutes: 'How long before closing the last call goes out',
  poll_auto_thread: 'Whether a poll opens a thread to argue in',
  poll_archive_days: 'How long a finished poll waits before it is archived',
  poll_archive_drop_votes: 'Whether archiving forgets who voted',
  poll_date_labels: 'How dates are written on a poll',
  poll_log_level: 'How much of polls is repeated into Discord',

  birthday_mode: 'Whether the bot wishes people happy birthday',
  birthday_channel_id: 'Where a birthday is wished',
  birthday_template: 'What a birthday message says',
  birthday_color: 'What colour a birthday embed is',
  birthday_role_id: 'Which role someone wears on their birthday',
  birthday_show_age: 'Whether the age is said out loud',
  birthday_log_level: 'How much of birthdays is repeated into Discord',

  modmail_enabled: 'Whether the bot answers DMs',
  modmail_mode: 'Whether a ticket is a channel or a thread',
  modmail_category_id: 'Where ticket channels are made',
  modmail_staff_channel_id: 'Where ticket threads are made',
  modmail_log_channel_id: 'Where a finished ticket’s transcript goes',
  modmail_log_level: 'How much of modmail is repeated into Discord',

  automod_mode: 'Whether automod is watching',
  automod_rules: 'The rule book automod reads',
  automod_exempt_role_ids: 'Which roles automod ignores',
  automod_exempt_channel_ids: 'Which channels automod never reads',
  automod_warn_threshold: 'How many warnings before automod says so',
  modlog_channel_id: 'Where mod cases are written',
  mod_dm_on_action: 'What a punished member is told',
  automod_log_level: 'How much of automod is repeated into Discord',
  mod_log_level: 'How much of moderation is repeated into Discord',

  rolemenu_approval_channel_id: 'Where a role request card is posted',
  rolemenu_approver_role_id: 'Who may say yes to a role request',
  rolemenu_mode: 'Whether role menus are on',
  rolemenu_log_level: 'How much of role menus is repeated into Discord',

  chat_mode: 'Whether the bot talks back',
  chat_cooldown_seconds: 'How long the bot waits before answering again',
  chat_ignore_channels: 'Which channels the bot never answers in',
  chat_ignore_categories: 'Which categories the bot never reads or mentions',
  chat_home_channel_id: 'Where the bot points when it names a channel that is not real',
  chat_visibility_role_id: 'Whose view of the server is the bot’s map',
  chat_staff_can_ping_roles: 'Whether a staffer’s question lets the bot ping a role',
  chat_escalation_names: 'How many online staff the bot names when a mod is asked for',
  chat_greeting_reaction: 'Whether a bare hello gets a wave',
  chat_reply_in_threads: 'Whether the bot answers inside threads',
  chat_route_ping_staff: 'Whether staff are told when a mod is asked for',
  chat_status_admin_only: 'Whether /chat status is for administrators only',
  chat_log_level: 'How much of chat is repeated into Discord',

  request_mode: 'Whether people can ask for things',
  request_who_can_file: 'Who may file a request',
  request_auto_approve_staff: 'Whether a staffer’s own request is approved on the spot',
  request_notify_channel_id: 'Where a new request is announced',
  request_dm_on_decision: 'Whether the asker is DMed the decision',
  request_log_level: 'How much of requests is repeated into Discord',

  cost_hosting_usd: 'What hosting costs a month, off the invoice',
};

const NAMESPACES = ['golive', 'youtube', 'pings', 'tempvoice', 'honeypot', 'events', 'birthday', 'modmail', 'automod', 'rolemenu'];

function derived(key) {
  let name = String(key || '');
  for (const namespace of NAMESPACES) {
    if (name.startsWith(`${namespace}_`) && name.length > namespace.length + 1) {
      name = name.slice(namespace.length + 1);
      break;
    }
  }
  name = name.replace(/_ids?$/, '');
  name = name.replace(/_/g, ' ').trim();
  if (!name) name = String(key);
  return name.charAt(0).toUpperCase() + name.slice(1);
}

/** The human name a key wears; the raw key survives as the mono sub-line. */
export function humanLabel(key) {
  return LABELS[String(key || '')] || derived(key);
}
