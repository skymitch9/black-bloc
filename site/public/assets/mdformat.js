/** Pure Discord-markdown editing moves: text + selection in, text + selection out. No DOM. */

const INDENT = '  ';

function runLeft(text, at, char) {
  let count = 0;
  while (at - count - 1 >= 0 && text[at - count - 1] === char) count += 1;
  return count;
}

function runRight(text, at, char) {
  let count = 0;
  while (at + count < text.length && text[at + count] === char) count += 1;
  return count;
}

function holds(run, marker) {
  if (marker === '*') return run % 2 === 1;
  if (marker === '`') return run === 1;
  return run >= marker.length;
}

function outerRun(value, start, end, marker) {
  const char = marker[0];
  return Math.min(runLeft(value, start, char), runRight(value, end, char));
}

function innerRun(value, start, end, marker) {
  const char = marker[0];
  const size = Math.min(runRight(value, start, char), runLeft(value, end, char));
  return 2 * size <= end - start ? size : Math.floor((end - start) / 2);
}

export function isWrapped(value, start, end, marker) {
  return holds(outerRun(value, start, end, marker), marker);
}

export function wrap(value, start, end, marker) {
  const size = marker.length;
  if (end > start && holds(innerRun(value, start, end, marker), marker)) {
    const inner = value.slice(start + size, end - size);
    return { value: value.slice(0, start) + inner + value.slice(end), start, end: end - 2 * size };
  }
  if (isWrapped(value, start, end, marker)) {
    return {
      value: value.slice(0, start - size) + value.slice(start, end) + value.slice(end + size),
      start: start - size,
      end: end - size,
    };
  }
  return {
    value: value.slice(0, start) + marker + value.slice(start, end) + marker + value.slice(end),
    start: start + size,
    end: end + size,
  };
}

const FENCE = '```';

export function codeBlock(value, start, end) {
  const open = `${FENCE}\n`;
  const close = `\n${FENCE}`;
  const picked = value.slice(start, end);
  if (picked.startsWith(open) && picked.endsWith(close) && picked.length >= open.length + close.length) {
    const inner = picked.slice(open.length, picked.length - close.length);
    return { value: value.slice(0, start) + inner + value.slice(end), start, end: start + inner.length };
  }
  if (value.slice(start - open.length, start) === open && value.slice(end, end + close.length) === close) {
    return {
      value: value.slice(0, start - open.length) + picked + value.slice(end + close.length),
      start: start - open.length,
      end: end - open.length,
    };
  }
  const before = start > 0 && value[start - 1] !== '\n' ? '\n' : '';
  const after = end < value.length && value[end] !== '\n' ? '\n' : '';
  const head = before + open;
  return {
    value: value.slice(0, start) + head + picked + close + after + value.slice(end),
    start: start + head.length,
    end: end + head.length,
  };
}

function lineSpan(value, start, end) {
  const from = value.lastIndexOf('\n', start - 1) + 1;
  const last = end > start && value[end - 1] === '\n' ? end - 1 : end;
  const stop = value.indexOf('\n', last);
  return { from, to: stop === -1 ? value.length : stop };
}

function rewriteLines(value, start, end, change) {
  const { from, to } = lineSpan(value, start, end);
  const lines = value.slice(from, to).split('\n');
  const made = change(lines);
  const block = made.join('\n');
  const next = value.slice(0, from) + block + value.slice(to);
  if (start === end) {
    const shift = made[0].length - lines[0].length;
    const caret = Math.max(from, start + shift);
    return { value: next, start: caret, end: caret };
  }
  const first = start === from ? from : Math.max(from, start + made[0].length - lines[0].length);
  return { value: next, start: first, end: Math.max(first, end + block.length - (to - from)) };
}

const filled = (line) => line.trim() !== '';

function touched(lines) {
  return lines.some(filled) ? lines.filter(filled) : lines;
}

export function prefixLines(value, start, end, prefix) {
  return rewriteLines(value, start, end, (lines) => {
    const off = touched(lines).every((line) => line.startsWith(prefix));
    return lines.map((line) => {
      if (off) return line.startsWith(prefix) ? line.slice(prefix.length) : line;
      if (!filled(line) && lines.some(filled)) return line;
      return prefix + line;
    });
  });
}

const NUMBERED = /^\d+[.)] /;

export function numberLines(value, start, end) {
  return rewriteLines(value, start, end, (lines) => {
    const off = touched(lines).every((line) => NUMBERED.test(line));
    let count = 0;
    return lines.map((line) => {
      if (off) return line.replace(NUMBERED, '');
      if (!filled(line) && lines.some(filled)) return line;
      count += 1;
      return `${count}. ${line}`;
    });
  });
}

const HEADING = /^#{1,3} /;

export function heading(value, start, end, level) {
  const mark = `${'#'.repeat(level)} `;
  return rewriteLines(value, start, end, (lines) => {
    const off = touched(lines).every((line) => line.startsWith(mark) && !line.startsWith(`${mark}#`));
    return lines.map((line) => {
      const bare = line.replace(HEADING, '');
      if (off) return bare;
      if (!filled(line) && lines.some(filled)) return line;
      return mark + bare;
    });
  });
}

export function indent(value, start, end) {
  return rewriteLines(value, start, end, (lines) =>
    lines.map((line) => (filled(line) || lines.length === 1 ? INDENT + line : line)));
}

export function outdent(value, start, end) {
  return rewriteLines(value, start, end, (lines) =>
    lines.map((line) => {
      if (line.startsWith('\t')) return line.slice(1);
      return line.replace(/^ {1,2}/, '');
    }));
}

const LINKED = /^\[([^\]\n]*)\]\(([^)\s]*)\)$/;
export const LINK_FILLER = 'link text';

export function linkedText(value, start, end) {
  const found = LINKED.exec(value.slice(start, end));
  return found ? found[1] : null;
}

export function unlink(value, start, end) {
  const text = linkedText(value, start, end);
  return { value: value.slice(0, start) + text + value.slice(end), start, end: start + text.length };
}

export function link(value, start, end, url) {
  const text = value.slice(start, end) || LINK_FILLER;
  const made = `[${text}](${url})`;
  return { value: value.slice(0, start) + made + value.slice(end), start: start + 1, end: start + 1 + text.length };
}

export function cleanUrl(typed) {
  const url = String(typed || '').trim();
  if (!url || /\s/.test(url)) return null;
  if (/^https?:\/\/[^\s)]+$/i.test(url)) return url;
  if (/^[\w-]+(\.[\w-]+)+([/?#][^\s)]*)?$/.test(url)) return `https://${url}`;
  return null;
}
