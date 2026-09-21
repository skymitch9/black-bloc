import { ago, badge, bar, button, el, foldout, sayNothing } from './ui.js';

export const VERSIONS_TITLE = 'Versions';
export const VERSIONS_NOTE = 'Every press of Save changes or Post it that changed something is '
  + 'here. Nothing else writes a version, and nothing ever removes one.';
export const VERSIONS_EMPTY = 'Nothing has been saved yet, so there is only what is in the box.';
export const NO_WORDS = 'Nothing is written in this one.';
export const TITLE_WAS = 'Title: {title}';
export const CURRENT = 'current';
export const VIEW_IT = 'View';
export const USE_IT = 'Use this version';
export const USE_IT_QUESTION = 'Replace the current text with version {n} from {ago}? Your '
  + 'current text stays in the history as version {next}.';
export const USE_IT_CONFIRM = 'Use version {n}';
export const VIEWING = 'Version {n} of {title}';

// `site.css` defines `.badge[data-tone]` for ok / warn / danger / info only, so a chip that
// wants none passes nothing rather than a word no stylesheet knows (ux-audit finding 7).
function toneFor(version) {
  if (version.shipped) return 'info';
  const word = String(version.because || '').split(':')[0];
  if (word === 'posted') return 'ok';
  return word === 'restored' ? 'warn' : null;
}

function titleChanged(versions, index) {
  const older = versions[index + 1];
  return older && older.title !== versions[index].title ? versions[index].title : null;
}

function whenLine(version) {
  const when = ago(version.saved_at);
  return {
    text: version.saved_by_name ? `${when.text} by ${version.saved_by_name}` : when.text,
    title: when.title,
  };
}

/** One row of the list: what it was, who saved it and when, and the two moves. */
export function versionRow(version, versions, index, { onView, onUse } = {}) {
  const when = whenLine(version);
  const changed = titleChanged(versions, index);
  const moves = [];
  if (onView) moves.push(button(VIEW_IT, () => onView(version), { tone: 'quiet' }));
  if (onUse && !version.current) moves.push(button(USE_IT, () => onUse(version), { tone: 'warn' }));
  return el('div', { class: 'row' }, [
    el('span', { class: 'dot' }),
    el('div', { class: 'row-body' }, [
      el('div', { class: 'row-head' }, [
        el('span', { class: 'row-name', text: `v${version.n}` }),
        badge(version.because_said, toneFor(version)),
        version.current ? badge(CURRENT, 'ok') : null,
      ]),
      el('p', { class: 'row-detail', text: version.summary || NO_WORDS }),
      changed ? el('p', { class: 'row-note', text: TITLE_WAS.replace('{title}', changed) }) : null,
      el('p', { class: 'row-note', title: when.title, text: when.text }),
      moves.length ? bar(moves) : null,
    ]),
  ]);
}

/** The foldout both the Posts page and its preview draw, shut on arrival. */
export function versionsFoldout(versions, { onView, onUse, open = false } = {}) {
  const rows = (versions || []).map((one, index) =>
    versionRow(one, versions, index, { onView, onUse }));
  return foldout(
    VERSIONS_TITLE,
    [
      el('p', { class: 'field-help', text: VERSIONS_NOTE }),
      ...(rows.length ? rows : [sayNothing(VERSIONS_EMPTY)]),
    ],
    { count: (versions || []).length, open },
  );
}

export function useItQuestion(version, nextN) {
  return USE_IT_QUESTION
    .replace('{n}', String(version.n))
    .replace('{ago}', ago(version.saved_at).text)
    .replace('{next}', String(nextN));
}
