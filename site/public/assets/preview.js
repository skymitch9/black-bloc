import { el, notice } from './ui.js';

const STORE = 'bb-preview-show-was';

export function previewBanner({ today, preview, note = null }) {
  const box = el('input', { type: 'checkbox', id: 'preview-show-was' });
  const apply = () => {
    document.body.dataset.showWas = box.checked ? '1' : '0';
    try { localStorage.setItem(STORE, box.checked ? '1' : '0'); } catch (error) { /* per-viewer only */ }
  };
  try { box.checked = localStorage.getItem(STORE) === '1'; } catch (error) { box.checked = false; }
  box.addEventListener('change', apply);
  apply();
  return el('div', { class: 'preview-banner', role: 'note' }, [
    el('span', { class: 'preview-banner-text' }, [
      el('strong', { text: 'Preview.' }),
      el('span', { text: ` Static data — nothing here reaches the bot. Today's page has ${today} sections; this has ${preview}.` }),
      note ? el('span', { text: ` ${note}` }) : null,
    ].filter(Boolean)),
    el('label', { class: 'preview-banner-toggle', for: 'preview-show-was' }, [box, el('span', { text: 'show what each section replaces' })]),
  ]);
}

export function previewWas(text) {
  return el('p', { class: 'preview-was', text });
}

export function wouldDo(say, text) {
  (say || notice()).say(`Preview — this would ${text}.`, 'warn');
}
