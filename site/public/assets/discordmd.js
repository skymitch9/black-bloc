/* The preview's markdown renderer — the only one this site has, and it is used by
   page-posts.js and nothing else. It returns an HTML STRING and never touches the
   document, so site/mock/discordmd.test.mjs can run it under plain node.
   See docs/info/code-notes.md § site/public/assets/discordmd.js. */

const HTML = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };

/** Everything else in this file runs on the OUTPUT of this, never on raw input. */
export function escapeHtml(text) {
  return String(text === null || text === undefined ? '' : text).replace(
    /[&<>"']/g,
    (one) => HTML[one],
  );
}

const MARK = '\u0000';
const CHANNEL_GONE = '#deleted-channel';
const NOBODY = '@unknown';

const TIME_STYLES = {
  t: { hour: 'numeric', minute: '2-digit' },
  T: { hour: 'numeric', minute: '2-digit', second: '2-digit' },
  d: { year: 'numeric', month: '2-digit', day: '2-digit' },
  D: { year: 'numeric', month: 'long', day: 'numeric' },
  f: { year: 'numeric', month: 'long', day: 'numeric', hour: 'numeric', minute: '2-digit' },
  F: {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  },
};

function whenWords(seconds, style) {
  const at = new Date(Number(seconds) * 1000);
  if (Number.isNaN(at.getTime())) return `<t:${seconds}:${style || 'F'}>`;
  if (style === 'R') {
    const gap = Math.round((at.getTime() - Date.now()) / 1000);
    const away = Math.abs(gap);
    const [size, word] = away < 3600
      ? [60, 'minute']
      : away < 86400 ? [3600, 'hour'] : [86400, 'day'];
    const count = Math.max(1, Math.round(away / size));
    const said = `${count} ${word}${count === 1 ? '' : 's'}`;
    return gap < 0 ? `${said} ago` : `in ${said}`;
  }
  return at.toLocaleString(undefined, TIME_STYLES[style] || TIME_STYLES.F);
}

class Held {
  /** Anything already rendered is parked here so the span pass cannot reach inside it. */
  constructor() {
    this.kept = [];
  }

  park(html) {
    this.kept.push(html);
    return `${MARK}${this.kept.length - 1}${MARK}`;
  }

  restore(text) {
    return text.replace(
      new RegExp(`${MARK}(\\d+)${MARK}`, 'g'),
      (whole, at) => this.kept[Number(at)] ?? whole,
    );
  }
}

function named(list, id) {
  for (const one of list || []) {
    if (String(one.id) === String(id)) return one.display_name || one.name || null;
  }
  return null;
}

function mentions(text, held, refs) {
  // The angle brackets are already `&lt;`/`&gt;` by now — that is the whole point of
  // escaping first, and it is why these patterns look the way they do.
  return text
    .replace(/&lt;#(\d+)&gt;/g, (whole, id) => {
      const name = named(refs.channels, id);
      return held.park(`<span class="md-mention">${name ? `#${escapeHtml(name)}` : CHANNEL_GONE}</span>`);
    })
    .replace(/&lt;@&amp;(\d+)&gt;/g, (whole, id) => {
      const name = named(refs.roles, id);
      return held.park(`<span class="md-mention">${name ? `@${escapeHtml(name)}` : NOBODY}</span>`);
    })
    .replace(/&lt;@!?(\d+)&gt;/g, (whole, id) => {
      const name = named(refs.members, id);
      return held.park(`<span class="md-mention">${name ? `@${escapeHtml(name)}` : NOBODY}</span>`);
    })
    .replace(/&lt;(a?):([A-Za-z0-9_]+):(\d+)&gt;/g, (whole, animated, name) =>
      held.park(`<span class="md-emoji">:${escapeHtml(name)}:</span>`))
    .replace(/&lt;t:(-?\d+)(?::([tTdDfFR]))?&gt;/g, (whole, seconds, style) =>
      held.park(`<span class="md-time">${escapeHtml(whenWords(seconds, style))}</span>`));
}

/** A link is never an anchor: a preview of somebody else's text is not a place to click. */
function links(text, held) {
  return text
    .replace(/\[([^\]\n]+)\]\((https?:\/\/[^\s)]+)\)/g, (whole, label, href) =>
      held.park(`<span class="md-link" title="${href}">${label}</span>`))
    .replace(/(^|[\s(])(https?:\/\/[^\s<]+)/g, (whole, before, href) =>
      `${before}${held.park(`<span class="md-link">${href}</span>`)}`);
}

function spans(text) {
  return text
    .replace(/\|\|([\s\S]+?)\|\|/g, '<span class="md-spoiler">$1</span>')
    .replace(/\*\*\*([\s\S]+?)\*\*\*/g, '<strong><em>$1</em></strong>')
    .replace(/\*\*([\s\S]+?)\*\*/g, '<strong>$1</strong>')
    .replace(/__([\s\S]+?)__/g, '<u>$1</u>')
    .replace(/~~([\s\S]+?)~~/g, '<s>$1</s>')
    .replace(/\*([^*\n]+?)\*/g, '<em>$1</em>')
    .replace(/(^|[\s(])_([^_\n]+?)_(?=$|[\s.,!?)])/g, '$1<em>$2</em>');
}

function inline(text, held, refs) {
  return held.restore(spans(links(mentions(text, held, refs), held)));
}

const HEADERS = [
  [/^###\s+(.*)$/, 'h4', 'md-h3'],
  [/^##\s+(.*)$/, 'h3', 'md-h2'],
  [/^#\s+(.*)$/, 'h2', 'md-h1'],
];

function listKind(line) {
  if (/^\s*[-*]\s+/.test(line)) return 'ul';
  if (/^\s*\d+[.)]\s+/.test(line)) return 'ol';
  return null;
}

function listText(line) {
  return line.replace(/^\s*[-*]\s+/, '').replace(/^\s*\d+[.)]\s+/, '');
}

/** One block per paragraph, quote, list or header — the shape Discord draws. */
function blocks(lines, held, refs, headers) {
  const out = [];
  let at = 0;
  let quoting = false;
  while (at < lines.length) {
    const line = lines[at];
    if (line.startsWith('&gt;&gt;&gt; ') || line === '&gt;&gt;&gt;') {
      quoting = true;
      lines[at] = line.slice('&gt;&gt;&gt;'.length).replace(/^ /, '');
      continue;
    }
    if (quoting || /^&gt;\s?/.test(line)) {
      const kept = [];
      while (at < lines.length && (quoting || /^&gt;\s?/.test(lines[at]))) {
        kept.push(lines[at].replace(/^&gt;\s?/, ''));
        at += 1;
      }
      out.push(`<blockquote class="md-quote">${blocks(kept, held, refs, headers)}</blockquote>`);
      continue;
    }
    if (!line.trim()) {
      at += 1;
      continue;
    }
    if (headers) {
      const header = HEADERS.find(([shape]) => shape.test(line));
      if (header) {
        const [shape, tag, mark] = header;
        out.push(`<${tag} class="${mark}">${inline(line.replace(shape, '$1'), held, refs)}</${tag}>`);
        at += 1;
        continue;
      }
    }
    if (/^-#\s+/.test(line)) {
      out.push(`<p class="md-subtext">${inline(line.replace(/^-#\s+/, ''), held, refs)}</p>`);
      at += 1;
      continue;
    }
    const kind = listKind(line);
    if (kind) {
      const items = [];
      while (at < lines.length && listKind(lines[at]) === kind) {
        items.push(`<li>${inline(listText(lines[at]), held, refs)}</li>`);
        at += 1;
      }
      out.push(`<${kind} class="md-list">${items.join('')}</${kind}>`);
      continue;
    }
    const paragraph = [];
    while (
      at < lines.length
      && lines[at].trim()
      && !listKind(lines[at])
      && !/^&gt;\s?/.test(lines[at])
      && !/^-#\s+/.test(lines[at])
      && !(headers && HEADERS.some(([shape]) => shape.test(lines[at])))
    ) {
      paragraph.push(lines[at]);
      at += 1;
    }
    if (paragraph.length) {
      out.push(`<p>${paragraph.map((one) => inline(one, held, refs)).join('<br>')}</p>`);
    }
  }
  return out.join('');
}

/**
 * Discord's markdown as Discord draws it, from text nobody here wrote.
 * `style` is `plain` or `embed`; an embed description renders no `#` headers.
 */
export function renderDiscord(text, { style = 'plain', channels = [], roles = [], members = [] } = {}) {
  const held = new Held();
  let body = escapeHtml(text);
  body = body.replace(/```(?:[a-zA-Z0-9+#-]*\n)?([\s\S]*?)```/g, (whole, code) =>
    held.park(`<pre class="md-code">${code.replace(/^\n/, '')}</pre>`));
  body = body.replace(/``?([^`\n]+?)``?/g, (whole, code) =>
    held.park(`<code class="md-inline">${code}</code>`));
  const refs = { channels, roles, members };
  return blocks(body.split('\n'), held, refs, style !== 'embed');
}

/** The embed box the preview draws around an embed-style post; plain style gets no box. */
export function renderPreview(text, options = {}) {
  const inner = renderDiscord(text, options);
  if (options.style !== 'embed') return `<div class="md-plain">${inner}</div>`;
  const title = options.title ? `<div class="md-embed-title">${escapeHtml(options.title)}</div>` : '';
  return `<div class="md-embed"><div class="md-embed-bar"></div><div class="md-embed-body">${title}${inner}</div></div>`;
}

export default renderDiscord;
