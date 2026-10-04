import { el } from './ui.js';

const RUNSHEET = 'Run sheet';
const RUNSHEET_HELP = 'The runs in order with the times the bot is working from, and the staff moves that change them.';

export function runsheetHref(marathonId) {
  return `/runsheet.html#marathon-${marathonId}`;
}

export function runsheetLink(marathonId) {
  return el('a', { class: 'btn small quiet mx-runsheet-link', href: runsheetHref(marathonId), title: RUNSHEET_HELP, text: RUNSHEET });
}
