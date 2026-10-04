import { el } from './ui.js';

const TRACKER = 'Marathon tracker';
const TRACKER_HELP = 'The runs in order with the times the bot is working from and what is live right now. It re-reads itself while it is open.';

export function trackerHref(marathonId) {
  return `/schedule.html#marathon-${marathonId}`;
}

export function trackerLink(marathonId) {
  return el('a', { class: 'btn small quiet mx-tracker-link', href: trackerHref(marathonId), title: TRACKER_HELP, text: TRACKER });
}
