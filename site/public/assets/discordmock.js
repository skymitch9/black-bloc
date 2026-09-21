/* Discord's own chrome around a message the BOT rendered. Nothing here decides what the
   words are — `black_bloc/preview.py` answers exactly what would be sent and this draws it.
   `messageTree` is pure so site/mock/discordmock.test.mjs can run it under plain node;
   `mountTree` turns that tree into nodes with the caller's element factory (`ui.js:el`),
   which is what keeps every inline style on the CSSOM side of `style-src 'self'`.
   See docs/info/code-notes.md § site/public/assets/discordmock.js. */

import { renderDiscord } from './discordmd.js';

export const CAPTION = 'How Discord will show it';
export const BOT_TAG = 'BOT';
export const BOT_NAME = 'Black Bloc';
export const BOT_COLOUR = '#5865f2';
export const NOTHING = 'Discord would post nothing at all for this.';
export const IMAGE_MARK = 'image';
export const THUMB_MARK = 'thumbnail';

const BUTTON_STYLES = new Set(['primary', 'secondary', 'success', 'danger', 'link']);
const LINK_MARK = '↗';
const EMBED_LIMIT = 10;

function words(value) {
  return value === null || value === undefined ? '' : String(value);
}

/** Discord's integer colour as a hex the CSSOM will take; nothing means its grey bar. */
export function colourOf(value) {
  if (value === null || value === undefined || value === '') return null;
  const found = Number(value);
  if (!Number.isInteger(found) || found < 0 || found > 0xffffff) return null;
  return `#${found.toString(16).padStart(6, '0')}`;
}

/** The file name at the end of an attachment URL, which is all a placeholder can honestly show. */
export function fileName(url) {
  const text = words(url).split(/[?#]/)[0];
  const last = text.split('/').filter(Boolean).pop();
  return last || text;
}

export function timeWords(when) {
  const at = when instanceof Date ? when : new Date(when);
  if (!when || Number.isNaN(at.getTime())) return '';
  const now = new Date();
  const clock = at.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  const day = new Date(at.getFullYear(), at.getMonth(), at.getDate());
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const gap = Math.round((today - day) / 86400000);
  if (gap === 0) return `Today at ${clock}`;
  if (gap === 1) return `Yesterday at ${clock}`;
  return `${at.toLocaleDateString()} ${clock}`;
}

function refsOf(rendered) {
  const mentions = (rendered && rendered.mentions) || {};
  return {
    roles: mentions.roles || [],
    channels: mentions.channels || [],
    members: mentions.members || [],
  };
}

function markdown(text, refs, style) {
  return renderDiscord(words(text), { style, ...refs });
}

function fieldTree(one, refs) {
  return {
    tag: 'div',
    class: 'dcmock-field',
    'data-inline': one && one.inline ? 'true' : 'false',
    children: [
      { tag: 'div', class: 'dcmock-field-name', text: words(one && one.name) },
      { tag: 'div', class: 'dcmock-field-value', html: markdown(one && one.value, refs, 'embed') },
    ],
  };
}

function mediaTree(url, mark) {
  return {
    tag: 'div',
    class: 'dcmock-media',
    'data-kind': mark,
    title: words(url),
    children: [
      { tag: 'span', class: 'dcmock-media-mark', text: mark },
      { tag: 'span', class: 'dcmock-media-name', text: fileName(url) },
    ],
  };
}

function authorTree(author) {
  const name = words(author && author.name);
  if (!name) return null;
  return {
    tag: 'div',
    class: 'dcmock-embed-author',
    children: [
      author && author.icon_url ? { tag: 'span', class: 'dcmock-embed-icon' } : null,
      { tag: 'span', text: name },
    ].filter(Boolean),
  };
}

function footerTree(embed) {
  const footer = embed.footer || {};
  const text = words(footer.text);
  const stamp = timeWords(embed.timestamp);
  if (!text && !stamp) return null;
  return {
    tag: 'div',
    class: 'dcmock-embed-footer',
    children: [
      footer.icon_url ? { tag: 'span', class: 'dcmock-embed-icon' } : null,
      { tag: 'span', text: [text, stamp].filter(Boolean).join(' • ') },
    ].filter(Boolean),
  };
}

/** One embed as Discord draws it: the bar, the author line, the title, the body, the grid. */
export function embedTree(embed, refs) {
  const bar = colourOf(embed.color);
  const fields = embed.fields || [];
  const title = words(embed.title);
  const description = words(embed.description);
  const main = [
    authorTree(embed.author),
    title
      ? {
        tag: 'div',
        class: 'dcmock-embed-title',
        'data-link': embed.url ? 'true' : 'false',
        text: title,
      }
      : null,
    description
      ? { tag: 'div', class: 'dcmock-embed-desc', html: markdown(description, refs, 'embed') }
      : null,
    fields.length
      ? { tag: 'div', class: 'dcmock-embed-fields', children: fields.map((one) => fieldTree(one, refs)) }
      : null,
    embed.image && embed.image.url ? mediaTree(embed.image.url, IMAGE_MARK) : null,
  ].filter(Boolean);
  const thumb = embed.thumbnail && embed.thumbnail.url
    ? mediaTree(embed.thumbnail.url, THUMB_MARK)
    : null;
  return {
    tag: 'div',
    class: 'dcmock-embed',
    children: [
      { tag: 'span', class: 'dcmock-embed-bar', style: bar ? `background: ${bar}` : null },
      {
        tag: 'div',
        class: 'dcmock-embed-inner',
        children: [
          { tag: 'div', class: 'dcmock-embed-main', children: main },
          thumb,
          footerTree(embed),
        ].filter(Boolean),
      },
    ],
  };
}

function buttonTree(one) {
  const style = BUTTON_STYLES.has(words(one && one.style)) ? one.style : 'secondary';
  return {
    tag: 'span',
    class: 'dcmock-btn',
    'data-style': style,
    'data-disabled': one && one.disabled ? 'true' : 'false',
    title: words(one && one.url) || null,
    children: [
      one && one.emoji ? { tag: 'span', class: 'dcmock-btn-emoji', text: words(one.emoji) } : null,
      { tag: 'span', text: words(one && one.label) },
      style === 'link' ? { tag: 'span', class: 'dcmock-btn-mark', text: LINK_MARK } : null,
    ].filter(Boolean),
  };
}

/**
 * The whole message: avatar, name, BOT tag, time, the text, every embed, every button row.
 * `rendered` is the `/api/preview/message` payload and nothing else is consulted.
 */
export function messageTree(rendered = {}, { bot = {}, when = null, caption = CAPTION } = {}) {
  const refs = refsOf(rendered);
  const content = words(rendered.content);
  const embeds = (rendered.embeds || []).slice(0, EMBED_LIMIT);
  const rows = (rendered.components || []).filter((row) => row && row.length);
  const name = words(bot.name) || BOT_NAME;
  const colour = words(bot.colour) || BOT_COLOUR;
  const body = [
    {
      tag: 'div',
      class: 'dcmock-head',
      children: [
        { tag: 'span', class: 'dcmock-name', style: `color: ${colour}`, text: name },
        { tag: 'span', class: 'dcmock-tag', text: BOT_TAG },
        { tag: 'span', class: 'dcmock-when', text: timeWords(when || new Date()) },
      ],
    },
    content ? { tag: 'div', class: 'dcmock-content', html: markdown(content, refs, 'plain') } : null,
    ...embeds.map((one) => embedTree(one, refs)),
    rows.length
      ? {
        tag: 'div',
        class: 'dcmock-actions',
        children: rows.map((row) => ({
          tag: 'div',
          class: 'dcmock-row',
          children: row.map(buttonTree),
        })),
      }
      : null,
  ].filter(Boolean);
  if (!content && !embeds.length && !rows.length) {
    body.push({ tag: 'p', class: 'dcmock-nothing', text: NOTHING });
  }
  return {
    tag: 'div',
    class: 'dcmock',
    children: [
      caption ? { tag: 'div', class: 'dcmock-cap', text: caption } : null,
      {
        tag: 'div',
        class: 'dcmock-msg',
        children: [
          {
            tag: 'div',
            class: 'dcmock-avatar',
            style: `background: ${colour}`,
            text: name.slice(0, 1).toUpperCase(),
          },
          { tag: 'div', class: 'dcmock-body', children: body },
        ],
      },
    ].filter(Boolean),
  };
}

/**
 * The tree as real nodes. `make` is `ui.js:el`, so every `style` goes through the CSSOM
 * and the page's `style-src 'self'` is never asked to allow an inline style attribute.
 */
export function mountTree(spec, make) {
  if (!spec) return null;
  const { tag, children, html, ...props } = spec;
  const node = make(tag, props, (children || []).map((one) => mountTree(one, make)).filter(Boolean));
  if (html !== undefined) node.innerHTML = html;
  return node;
}

export default messageTree;
