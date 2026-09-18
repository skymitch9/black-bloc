/* Rich-clipboard HTML (Google Docs' flavour) to Discord markdown, for the post editor's
   paste. A STRING goes in and a STRING comes out — no DOM, no DOMParser, so
   site/mock/clipmd.test.mjs feeds it the same fixtures under plain node with no dependency.
   See docs/info/code-notes.md § site/public/assets/clipmd.js and
   docs/info/posts-paste-design.md. */

const VOID = new Set([
  'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param',
  'source', 'track', 'wbr',
]);
const DROP = new Set([
  'script', 'style', 'head', 'title', 'meta', 'link', 'noscript', 'iframe', 'object',
  'svg', 'template',
]);
const BLOCKS = new Set([
  'p', 'div', 'section', 'article', 'header', 'footer', 'main', 'aside', 'blockquote',
  'pre', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'tr', 'table', 'dl', 'dt', 'dd',
  'figure', 'figcaption', 'form', 'fieldset',
]);
const HEADINGS = { h1: 1, h2: 2, h3: 3, h4: 3, h5: 3, h6: 3 };

const BOLD_WEIGHTS = new Set(['bold', 'bolder', '600', '700', '800', '900']);
const BOLD_TAGS = new Set(['b', 'strong', 'th']);
const ITALIC_TAGS = new Set(['i', 'em', 'cite', 'var', 'dfn']);
const UNDER_TAGS = new Set(['u', 'ins']);
const STRIKE_TAGS = new Set(['s', 'strike', 'del']);
const CODE_TAGS = new Set(['code', 'kbd', 'samp', 'tt', 'pre']);
const MONO = /mono|courier|consolas|menlo|monaco|lucida console/;
const LINKABLE = /^(?:https?:|mailto:|discord:)/i;

/** Body text in Google Docs is 11pt; everything here is measured against that. */
const BASE_PT = 11;
const HEADING_PT = [[20, 1], [16, 2], [13.5, 3]];

const ENTITIES = {
  amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ', ensp: ' ', emsp: ' ',
  thinsp: ' ', shy: '', hellip: '…', mdash: '—', ndash: '–', bull: '•', middot: '·',
  lsquo: '‘', rsquo: '’', ldquo: '“', rdquo: '”', copy: '©',
  reg: '®', trade: '™', deg: '°', laquo: '«', raquo: '»', times: '×', hearts: '♥',
};

function decode(text) {
  return String(text).replace(/&(#[Xx]?[0-9A-Fa-f]+|[A-Za-z][A-Za-z0-9]*);/g, (whole, body) => {
    if (body.charAt(0) === '#') {
      const hex = body.charAt(1) === 'x' || body.charAt(1) === 'X';
      const code = hex ? parseInt(body.slice(2), 16) : Number(body.slice(1));
      if (!Number.isFinite(code) || code <= 0 || code > 0x10ffff) return whole;
      try {
        return String.fromCodePoint(code);
      } catch (error) {
        return whole;
      }
    }
    const found = ENTITIES[body] ?? ENTITIES[body.toLowerCase()];
    return found === undefined ? whole : found;
  });
}

const TAG = /<(\/)?([a-zA-Z][a-zA-Z0-9:_-]*)((?:"[^"]*"|'[^']*'|[^'">])*)>/g;
const ATTR = /([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*(?:=\s*("[^"]*"|'[^']*'|[^\s"'>]+))?/g;

function attrsOf(raw) {
  const out = {};
  ATTR.lastIndex = 0;
  let found = ATTR.exec(raw);
  while (found) {
    const value = found[2] === undefined ? '' : found[2].replace(/^["']|["']$/g, '');
    out[found[1].toLowerCase()] = decode(value);
    found = ATTR.exec(raw);
  }
  return out;
}

/** Tags in, a tree out. A close tag that matches nothing open is ignored, never fatal. */
function parse(html) {
  const root = { tag: null, attrs: {}, children: [] };
  const stack = [root];
  const source = String(html === null || html === undefined ? '' : html)
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/<![^>]*>/g, '');
  const add = (node) => stack[stack.length - 1].children.push(node);
  let at = 0;
  TAG.lastIndex = 0;
  let found = TAG.exec(source);
  while (found) {
    if (found.index > at) add({ text: decode(source.slice(at, found.index)) });
    at = TAG.lastIndex;
    const name = found[2].toLowerCase();
    const closing = Boolean(found[1]);
    const raw = (found[3] || '').replace(/\/\s*$/, '');
    const selfShut = raw !== (found[3] || '');
    if (DROP.has(name)) {
      if (!closing && !selfShut && !VOID.has(name)) {
        const shut = new RegExp(`<\\/${name}\\s*>`, 'ig');
        shut.lastIndex = at;
        at = shut.exec(source) ? shut.lastIndex : source.length;
        TAG.lastIndex = at;
      }
    } else if (closing) {
      for (let depth = stack.length - 1; depth > 0; depth -= 1) {
        if (stack[depth].tag === name) {
          stack.length = depth;
          break;
        }
      }
    } else {
      if ((name === 'li' || name === 'p') && stack[stack.length - 1].tag === name) stack.pop();
      const node = { tag: name, attrs: attrsOf(raw), children: [] };
      add(node);
      if (!VOID.has(name) && !selfShut) stack.push(node);
    }
    found = TAG.exec(source);
  }
  if (at < source.length) add({ text: decode(source.slice(at)) });
  return root;
}

function styleOf(attrs) {
  const out = {};
  for (const one of String(attrs.style || '').split(';')) {
    const split = one.indexOf(':');
    if (split < 0) continue;
    out[one.slice(0, split).trim().toLowerCase()] = one.slice(split + 1).trim().toLowerCase();
  }
  return out;
}

function decorationOf(style) {
  return [
    style['text-decoration-line'],
    style['text-decoration'],
    style['-webkit-text-decorations-in-effect'],
  ].filter(Boolean).join(' ');
}

/** An explicit style beats the tag — Docs wraps a whole paste in `<b style="font-weight:normal">`. */
function marksOf(tag, style, was) {
  const weight = style['font-weight'];
  const slant = style['font-style'];
  const lines = decorationOf(style);
  const off = /\bnone\b/.test(lines);
  return {
    b: weight ? BOLD_WEIGHTS.has(weight) : BOLD_TAGS.has(tag) || was.b,
    i: slant ? slant === 'italic' || slant === 'oblique' : ITALIC_TAGS.has(tag) || was.i,
    u: /underline/.test(lines) || (!off && (UNDER_TAGS.has(tag) || was.u)),
    s: /line-through/.test(lines) || (!off && (STRIKE_TAGS.has(tag) || was.s)),
    code: CODE_TAGS.has(tag) || MONO.test(style['font-family'] || '') || was.code,
  };
}

function ptOf(style, was) {
  const found = /^(-?[\d.]+)\s*(pt|px|em|rem|%)?$/.exec(String(style['font-size'] || '').trim());
  if (!found) return was;
  const size = Number(found[1]);
  if (!Number.isFinite(size) || size <= 0) return was;
  const unit = found[2] || 'px';
  if (unit === 'pt') return size;
  if (unit === 'px') return size * 0.75;
  if (unit === 'em' || unit === 'rem') return size * BASE_PT;
  if (unit === '%') return (size / 100) * BASE_PT;
  return was;
}

function headingFromPt(pt) {
  for (const [least, level] of HEADING_PT) if (pt >= least - 0.01) return level;
  return 0;
}

/** Word and the older editors say it in a class or a role; Docs says it in a font size. */
function headingFromAttrs(attrs) {
  if (String(attrs.role || '').toLowerCase() === 'heading') {
    const level = Number(attrs['aria-level']);
    return Number.isFinite(level) && level >= 1 ? Math.min(3, Math.round(level)) : 2;
  }
  const klass = String(attrs.class || '').toLowerCase();
  if (/(^|[\s_-])subtitle/.test(klass)) return 2;
  if (/(^|[\s_-])title([\s_-]|$)/.test(klass)) return 1;
  const found = /heading[\s_-]?([1-6])/.exec(klass);
  if (found) return Math.min(3, Number(found[1]));
  return /(^|[\s_-])heading/.test(klass) ? 2 : 0;
}

function headingFromRuns(runs) {
  let least = Infinity;
  for (const one of runs) {
    if (one.pt === null || one.pt === undefined) return 0;
    least = Math.min(least, one.pt);
  }
  return headingFromPt(least);
}

const WRAPS = [['code', '`'], ['i', '*'], ['b', '**'], ['u', '__'], ['s', '~~']];

function wrapped(text, marks) {
  if (!text.trim()) return text;
  const head = /^\s*/.exec(text)[0];
  const tail = /\s*$/.exec(text)[0];
  let core = text.slice(head.length, text.length - tail.length);
  for (const [key, mark] of WRAPS) if (marks[key]) core = `${mark}${core}${mark}`;
  return `${head}${core}${tail}`;
}

function sameRun(a, b) {
  return !a.br && !b.br && a.href === b.href && a.marks.b === b.marks.b
    && a.marks.i === b.marks.i && a.marks.u === b.marks.u && a.marks.s === b.marks.s
    && a.marks.code === b.marks.code;
}

function bareUrl(url) {
  return String(url).trim().replace(/^https?:\/\//i, '').replace(/\/+$/, '').toLowerCase();
}

/** A bare URL whose words already ARE the address stays bare — masking it would say less. */
function linkOf(text, href) {
  if (!text.trim()) return '';
  const head = /^\s*/.exec(text)[0];
  const tail = /\s*$/.exec(text)[0];
  const shown = text.slice(head.length, text.length - tail.length);
  if (bareUrl(shown) === bareUrl(href)) return `${head}${href}${tail}`;
  return `${head}[${shown}](${href})${tail}`;
}

function inlineOf(runs) {
  const merged = [];
  for (const one of runs) {
    const last = merged[merged.length - 1];
    if (last && sameRun(last, one)) last.text += one.text;
    else if (one.br) merged.push({ br: true });
    else merged.push({ text: one.text, marks: one.marks, href: one.href || null });
  }
  let out = '';
  let at = 0;
  while (at < merged.length) {
    const one = merged[at];
    if (one.br) {
      out += '\n';
      at += 1;
    } else if (one.href) {
      const href = one.href;
      const group = [];
      while (at < merged.length && !merged[at].br && merged[at].href === href) {
        group.push(merged[at]);
        at += 1;
      }
      out += linkOf(group.map((each) => wrapped(each.text, each.marks)).join(''), href);
    } else {
      out += wrapped(one.text, one.marks);
      at += 1;
    }
  }
  return out;
}

function lineOf(block) {
  const runs = block.kind === 'h'
    ? block.runs.map((one) => (one.br ? one : { ...one, marks: { ...one.marks, b: false } }))
    : block.runs;
  const said = inlineOf(runs).replace(/[ \t]+\n/g, '\n').replace(/\n[ \t]+/g, '\n').trim();
  if (!said) return '';
  if (block.kind === 'h') return `${'#'.repeat(block.level)} ${said}`;
  if (block.kind === 'li') {
    const mark = block.ordered ? `${block.number}. ` : '- ';
    return `${'  '.repeat(block.depth)}${mark}${said.replace(/\n+/g, ' ')}`;
  }
  return said;
}

function blank() {
  return { b: false, i: false, u: false, s: false, code: false };
}

/**
 * A rich-clipboard HTML fragment as the markdown Discord draws.
 * Anything with no markdown of its own — colour, size, alignment, images, tables' shape —
 * is stripped rather than approximated.
 */
export function htmlToDiscordMarkdown(html) {
  const blocks = [];
  let open = null;

  const shut = () => {
    if (!open) return;
    const said = open.runs.filter((one) => one.text && one.text.trim());
    if (said.length) {
      if (open.kind === 'p') {
        const level = open.heading || headingFromRuns(said);
        if (level) {
          open.kind = 'h';
          open.level = level;
        }
      }
      blocks.push(open);
    }
    open = null;
  };

  const start = (kind, extra = {}) => {
    if (open && !open.runs.length && kind === 'p' && (open.kind === 'li' || open.kind === 'h')) {
      return;
    }
    shut();
    open = { kind, runs: [], ...extra };
  };

  const into = (run) => {
    if (!open) open = { kind: 'p', runs: [] };
    open.runs.push(run);
  };

  const walk = (nodes, ctx) => {
    for (const node of nodes) {
      if (node.text !== undefined) {
        if (!node.text) continue;
        const text = ctx.pre
          ? node.text.replace(/[^\S\n]+/g, ' ')
          : node.text.replace(/\s+/g, ' ');
        const parts = ctx.pre ? text.split('\n') : [text];
        parts.forEach((part, part_at) => {
          if (part_at) into({ br: true, marks: ctx.marks, pt: ctx.pt });
          if (part) into({ text: part, marks: ctx.marks, href: ctx.href, pt: ctx.pt });
        });
        continue;
      }
      const tag = node.tag;
      if (tag === 'br') {
        into({ br: true, marks: ctx.marks, pt: ctx.pt });
        continue;
      }
      if (tag === 'hr') {
        shut();
        continue;
      }
      if (tag === 'img' || tag === 'input' || tag === 'button' || tag === 'select') continue;
      const style = styleOf(node.attrs);
      const next = { ...ctx, marks: marksOf(tag, style, ctx.marks), pt: ptOf(style, ctx.pt) };
      if (tag === 'a') {
        const href = String(node.attrs.href || '').trim();
        if (LINKABLE.test(href)) next.href = href;
      }
      if (next.href) next.marks = { ...next.marks, u: false };
      if (tag === 'pre') next.pre = true;
      if (tag === 'ul' || tag === 'ol') {
        shut();
        const list = { ordered: tag === 'ol', at: Number(node.attrs.start) || 1 };
        walk(node.children, { ...next, lists: ctx.lists.concat([list]) });
        shut();
        continue;
      }
      if (tag === 'li') {
        const list = ctx.lists[ctx.lists.length - 1] || { ordered: false, at: 1 };
        start('li', {
          depth: Math.max(0, ctx.lists.length - 1),
          ordered: list.ordered,
          number: list.at,
        });
        list.at += 1;
        walk(node.children, next);
        shut();
        continue;
      }
      if (HEADINGS[tag]) {
        start('h', { level: HEADINGS[tag] });
        walk(node.children, next);
        shut();
        continue;
      }
      if (tag === 'td' || tag === 'th') {
        into({ text: ' ', marks: next.marks, href: next.href, pt: next.pt });
        walk(node.children, next);
        continue;
      }
      if (BLOCKS.has(tag)) {
        start('p', { heading: headingFromAttrs(node.attrs) });
        walk(node.children, next);
        shut();
        continue;
      }
      walk(node.children, next);
    }
  };

  walk(parse(html).children, {
    marks: blank(), pt: null, href: null, pre: false, lists: [],
  });
  shut();

  let out = '';
  let before = null;
  for (const block of blocks) {
    const line = lineOf(block);
    if (!line) continue;
    if (out) {
      const run = before && before.kind === 'li' && block.kind === 'li'
        && before.ordered === block.ordered;
      out += run ? '\n' : '\n\n';
    }
    out += line;
    before = block;
  }
  return out.replace(/[ \t]+$/gm, '').replace(/\n{3,}/g, '\n\n').trim();
}

export default htmlToDiscordMarkdown;
