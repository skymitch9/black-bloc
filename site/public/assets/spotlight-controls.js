/* One channel row's spotlight controls — on/off, extend, keep, bump, pin, the dates, the
   announce opt-out and the Pings card — drawn for the Go-live drawer AND the marathon drawer.
   Every write goes to the same /api/golive/spotlight routes; `after(done)` is the page's redraw.
   See docs/info/code-notes.md § site/public/assets/spotlight-controls.js. */
import { send } from './api.js';
import {
  askForm,
  badge,
  button,
  card,
  el,
  field,
  localWhen,
  run,
  segment,
  when,
  whenField,
} from './ui.js';

export const SPOTLIGHT_TITLE = 'Spotlight';
export const SPOTLIGHT_DATES = 'Dates';
export const SPOTLIGHT_SAVE_DATES = 'Save dates';
export const SPOTLIGHT_STARTS = 'Starts — blank starts now';
export const SPOTLIGHT_ENDS = 'Ends — blank keeps it for ever';
export const SPOTLIGHT_SCHEDULED_STATE = 'Scheduled — its start has not arrived.';
export const PINGS_TITLE = 'Pings';
export const PING_MODE_CHOICES = [
  { value: 'always', label: 'Always' },
  { value: 'never', label: 'Never' },
  { value: 'events', label: 'During events' },
];
const WINDOWS_NONE = 'No window yet, so nothing it posts mentions a role.';
const ADD_WINDOW = 'Add a window…';
const WINDOW_TITLE = 'Add a ping window';
const WINDOW_HELP = 'While a window is open this channel mentions the go-live role and its own '
  + 'ping role. If it is already live when the window opens, one reminder that pings goes out.';
const WINDOW_STARTS = 'Pings start';
const WINDOW_ENDS = 'Pings stop';
const WINDOW_NOTE = 'What it is for (optional)';
const WINDOW_OPEN = 'open now';
export const SPOTLIGHT_ON = 'Spotlight on';
export const SPOTLIGHT_OFF = 'Spotlight off';
export const CHANNEL_OPT_OUT = 'Opt out of announcements';
export const CHANNEL_OPT_IN = 'Opt back in';
const CHANNEL_OPTED_OUT_STATE = 'Opted out \u2014 nothing of its is announced.';
const CHANNEL_ANNOUNCED_STATE = 'On \u2014 announced in the go-live channel whenever it goes live.';

function rowPath(one, tail = '') {
  return `/api/golive/spotlight/${one.id}${tail}`;
}

function patcher(one, say) {
  return (body, fallback) => run(
    say,
    () => send(rowPath(one), 'PATCH', body),
    (found) => found?.message || fallback,
  );
}

/** Spotlight on/off, and while it is on: extend, keep or let it expire, bump, pin. */
export function spotlightMoves(one, say, after) {
  const patch = patcher(one, say);
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
    if (one.live && one.announce !== false && !one.replay) {
      moves.push(button('Bump now', async () => {
        const done = await run(
          say,
          () => send(rowPath(one, '/bump'), 'POST', {}),
          (found) => found?.message || 'Reminded the channel.',
        );
        after(done);
      }, { tone: 'quiet' }));
    }
    moves.push(button(one.pin ? 'Stop pinning it' : 'Pin it while it streams', async () => (
      after(await patch({ pin: !one.pin }, one.pin ? 'It will not be pinned.' : 'It will be pinned.'))
    ), { tone: 'quiet' }));
  }
  if (one.replay) moves.push(treatLiveMove(one, say, after));
  return moves;
}

/** Staff final say on a replay: this stream is live, announced again with the full spotlight. */
function treatLiveMove(one, say, after) {
  return button(one.replay.treat_label || 'Treat as live', async () => {
    const done = await run(
      say,
      () => send(rowPath(one, '/treat-live'), 'POST', {}),
      (found) => found?.message || 'Treated as live.',
    );
    after(done);
  }, { tone: 'warn' });
}

/** The open session's replay read, in the key's words; nothing when it is live. */
export function replayLine(one) {
  if (!one.replay || !one.replay.line) return null;
  return el('p', { class: 'field-help', 'data-replay': 'true' }, [badge(one.replay.line, 'warn')]);
}

/** The owner's date range: two pickers and one Save. */
export function datesCard(one, say, after) {
  const starts = whenField({
    label: SPOTLIGHT_STARTS,
    value: one.starts_at ? localWhen(one.starts_at) : '',
  });
  const ends = whenField({
    label: SPOTLIGHT_ENDS,
    value: one.expires_at ? localWhen(one.expires_at) : '',
  });
  const go = button(SPOTLIGHT_SAVE_DATES, async () => {
    const done = await run(
      say,
      () => send(rowPath(one), 'PATCH', {
        starts_at: starts.value() || null,
        expires_at: ends.value() || null,
        tz: starts.tz() || ends.tz() || null,
      }),
      (found) => found?.message || 'Dates saved.',
    );
    await after(done);
  }, { tone: 'quiet' });
  return el('div', { class: 'card-sub' }, [
    el('h4', { text: SPOTLIGHT_DATES }),
    el('span', { class: 'cell-quiet', text: one.scheduled ? SPOTLIGHT_SCHEDULED_STATE : (one.range || one.until) }),
    el('div', { class: 'formrow' }, [starts.node, ends.node]),
    el('div', { class: 'bar' }, [go]),
  ]);
}

/** Only facts a person cannot see elsewhere in the card: the note, the event it was set up for. */
export function spotlightQuiet(one) {
  const bits = [];
  if (one.event_id) bits.push(`Set up for event #${one.event_id}.`);
  if (one.note) bits.push(one.note);
  return bits.length ? el('span', { class: 'cell-quiet', text: bits.join(' ') }) : null;
}

/** The Spotlight card: `head` goes above the moves, `foot` below the dates. */
export function spotlightCard(one, say, after, { head = [], foot = [] } = {}) {
  return card(SPOTLIGHT_TITLE, [
    ...head,
    replayLine(one),
    spotlightQuiet(one),
    el('div', { class: 'bar' }, spotlightMoves(one, say, after)),
    datesCard(one, say, after),
    ...foot,
  ].filter(Boolean));
}

/** The owner's split: when a channel pings, and the windows that decide it for an events row. */
export function pingsCard(one, say, after) {
  const current = one.ping_mode || 'always';
  const mode = segment(PING_MODE_CHOICES, current, {
    onChange: async () => {
      const wanted = mode.readValue();
      if (wanted === current) return;
      after(await run(
        say,
        () => send(rowPath(one), 'PATCH', { ping_mode: wanted }),
        (found) => found?.message || 'Pings changed.',
      ));
    },
  });
  const bits = [
    el('span', { class: 'cell-quiet', text: one.ping_state || '' }),
    mode,
    one.ping_help ? el('p', { class: 'field-help', text: one.ping_help }) : null,
  ].filter(Boolean);
  if (current === 'events') {
    const windows = one.windows || [];
    if (!windows.length) bits.push(el('span', { class: 'muted', text: WINDOWS_NONE }));
    for (const span of windows) {
      bits.push(el('div', { class: 'bar' }, [
        el('span', { text: `${when(span.starts_at)} – ${when(span.ends_at)}` }),
        span.note ? el('span', { class: 'cell-quiet', text: span.note }) : null,
        span.open ? badge(WINDOW_OPEN, 'ok') : null,
        span.staff
          ? button('Remove', async () => after(await run(
            say,
            () => send(rowPath(one, `/windows/${span.id}`), 'DELETE'),
            (found) => found?.message || 'Window removed.',
          )), { tone: 'quiet' })
          : badge(span.source_words || span.source),
      ].filter(Boolean)));
    }
    bits.push(el('div', { class: 'bar' }, [
      button(ADD_WINDOW, () => addWindow(one, say, after), { tone: 'quiet' }),
    ]));
  }
  return card(PINGS_TITLE, bits);
}

/** A dialog like Add a ping role: two pickers and a note, read by the same route parsing. */
async function addWindow(one, say, after) {
  const starts = whenField({ label: WINDOW_STARTS });
  const ends = whenField({ label: WINDOW_ENDS });
  const note = el('input', { class: 'input', type: 'text', maxlength: '100', placeholder: 'AGDQ 2027' });
  let made = null;
  const sure = await askForm({
    title: WINDOW_TITLE,
    body: [
      WINDOW_HELP,
      el('div', { class: 'formrow' }, [starts.node, ends.node]),
      field(WINDOW_NOTE, note),
    ],
    confirmLabel: 'Add the window',
    tone: 'warn',
    onConfirm: async () => {
      made = await send(rowPath(one, '/windows'), 'POST', {
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
  await after({ ok: true, found: made });
}

/** Whether the channel is announced at all, in words. */
export function announcedSaid(one) {
  return el('p', { class: 'field-help', text: one.announce === false ? CHANNEL_OPTED_OUT_STATE : CHANNEL_ANNOUNCED_STATE });
}

/** Opt the channel out of announcements, or back in. */
export function announceMoves(one, say, after) {
  const out = one.announce === false;
  return [button(out ? CHANNEL_OPT_IN : CHANNEL_OPT_OUT, async () => {
    const done = await run(
      say,
      () => send(rowPath(one), 'PATCH', { announce: out }),
      (found) => found?.message || (out ? 'Opted back in.' : 'Opted out.'),
    );
    await after(done);
  }, { tone: out ? 'quiet' : 'warn' })];
}
