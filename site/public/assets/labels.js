/* The one home for what a settings key is CALLED. /api/settings carries a key,
   a type and a help sentence but no label, so the label lives here rather than
   in whichever page happens to draw the row. A key with no entry falls back to
   a tidied-up version of itself, so a new registry key still reads.
   See docs/info/code-notes.md § site/public/assets/labels.js. */

export const LABELS = {
  log_channel_id: 'Log channel',
  staff_channel_id: 'Staff channel',
  role_menu_channel_id: 'Role menu channel',
  core_log_level: 'Core log level',
  bot_bio: 'The bot’s About Me',
  status_prefix: 'Status wording',
  emoji_skin_tone: 'Emoji skin tone',

  golive_mode: 'Go-live mode',
  golive_channel_id: 'Announcement channel',
  golive_template: 'Announcement wording',
  golive_embed: 'Post as an embed',
  golive_end_mode: 'When a stream ends',
  golive_end_suffix: 'Ended wording',
  golive_live_role_id: 'Live role',
  golive_require_role_id: 'Only announce this role',
  golive_ignore_role_id: 'Never announce this role',
  golive_cooldown_minutes: 'Cooldown, minutes',
  golive_ping_role_id: 'Ping role',
  golive_max_session_hours: 'Longest stream, hours',
  golive_log_level: 'Go-live log level',

  tempvoice_mode: 'Temp voice mode',
  tempvoice_creator_ids: 'Join-to-create channels',
  tempvoice_name_template: 'Room name wording',
  tempvoice_creator_name: 'Join-to-create channel name',
  tempvoice_allowed_role_id: 'Who may get a room',
  tempvoice_log_level: 'Temp voice log level',

  honeypot_mode: 'Honeypot mode',
  honeypot_channel_ids: 'Trap channels',
  honeypot_purge_days: 'Messages deleted, days',
  honeypot_exempt_role_ids: 'Roles the trap ignores',
  honeypot_log_level: 'Honeypot log level',

  events_mode: 'Events mode',
  events_category_id: 'Review category',
  events_announce_channel_id: 'Announcement channel',
  events_ping_role_id: 'Ping role',
  events_create_scheduled: 'Make a Discord event',
  events_channel_retention_days: 'Keep the channel, days',
  events_max_late_minutes: 'Allowed lateness, minutes',
  events_log_level: 'Events log level',

  poll_mode: 'Polls mode',
  poll_who_can_create: 'Who may start a poll',
  poll_review_mode: 'Staff review first',
  poll_default_hours: 'Default length, hours',
  poll_channel_id: 'Poll channel',
  poll_ping_role_id: 'Ping role',
  poll_reminder_minutes: 'Last call, minutes before',
  poll_auto_thread: 'Open a discussion thread',
  poll_archive_days: 'Move to archive after, days',
  poll_archive_drop_votes: 'Forget who voted on archive',
  poll_date_labels: 'How dates are written',
  poll_log_level: 'Polls log level',

  birthday_mode: 'Birthdays mode',
  birthday_channel_id: 'Birthday channel',
  birthday_template: 'Birthday wording',
  birthday_color: 'Embed colour',
  birthday_role_id: 'Birthday role',
  birthday_show_age: 'Show the age',
  birthday_log_level: 'Birthdays log level',

  modmail_enabled: 'Answer DMs',
  modmail_mode: 'Ticket style',
  modmail_category_id: 'Ticket category',
  modmail_staff_channel_id: 'Ticket thread channel',
  modmail_log_channel_id: 'Transcript channel',
  modmail_log_level: 'Modmail log level',

  automod_mode: 'Automod mode',
  automod_rules: 'Rule book',
  automod_exempt_role_ids: 'Roles automod ignores',
  automod_exempt_channel_ids: 'Channels automod never reads',
  automod_warn_threshold: 'Warnings before it says so',
  modlog_channel_id: 'Mod case channel',
  mod_dm_on_action: 'What a punished member is told',
  automod_log_level: 'Automod log level',
  mod_log_level: 'Moderation log level',

  rolemenu_approval_channel_id: 'Request card channel',
  rolemenu_approver_role_id: 'Approver role',
  rolemenu_mode: 'Role menus mode',
  rolemenu_log_level: 'Role menus log level',

  chat_mode: 'Chat mode',
  chat_cooldown_seconds: 'Cooldown, seconds',
  chat_ignore_channels: 'Channels it never answers in',
  chat_greeting_reaction: 'Wave at a bare hello',
  chat_reply_in_threads: 'Answer inside threads',
  chat_route_ping_staff: 'Tell staff when a mod is asked for',
  chat_log_level: 'Chat log level',

  request_mode: 'Requests mode',
  request_who_can_file: 'Who may file a request',
  request_auto_approve_staff: 'Auto-approve staff requests',
  request_notify_channel_id: 'Notify channel',
  request_dm_on_decision: 'DM the asker on a decision',
  request_log_level: 'Requests log level',
};

const NAMESPACES = ['golive', 'tempvoice', 'honeypot', 'events', 'birthday', 'modmail', 'automod', 'rolemenu'];

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
