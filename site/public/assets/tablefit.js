export const FIT_GAP = 16;
export const FIT_BELOW = 48;
export const FIT_FLOOR_REM = 26;
const MAX_TRIES = 120;

const fitted = new Map();
let listening = null;

export function tableFit({ top, viewport, below, floor = 0 }) {
  return Math.max(Math.floor(viewport - top - below), Math.ceil(floor));
}

function scrollBox(node) {
  if (!node) return null;
  if (node.matches?.('.table-scroll')) return node;
  return node.querySelector?.('.table-scroll') || null;
}

function scrolledBy(box, win) {
  let by = win.scrollY || 0;
  for (let up = box.parentElement; up; up = up.parentElement) by += up.scrollTop || 0;
  return by;
}

function measure(box, below, win, tries = 0) {
  if (!box.isConnected) {
    if (tries < MAX_TRIES) win.requestAnimationFrame(() => measure(box, below, win, tries + 1));
    else fitted.delete(box);
    return null;
  }
  const rem = parseFloat(win.getComputedStyle(win.document.documentElement).fontSize) || 16;
  const under = below && below.isConnected ? below.getBoundingClientRect().height : FIT_BELOW;
  const px = tableFit({
    top: box.getBoundingClientRect().top + scrolledBy(box, win),
    viewport: win.innerHeight,
    below: under + FIT_GAP,
    floor: FIT_FLOOR_REM * rem,
  });
  box.style.setProperty('--table-fit', `${px}px`);
  return px;
}

function refitAll(win) {
  win.requestAnimationFrame(() => {
    for (const [box, below] of fitted) measure(box, below, win, MAX_TRIES);
  });
}

export function fitScroll(node, { below = null, win = globalThis } = {}) {
  const box = scrollBox(node);
  if (!box || box.dataset.long !== 'true') return null;
  box.dataset.fit = 'true';
  fitted.set(box, below);
  if (listening !== win) {
    win.addEventListener('resize', () => refitAll(win));
    listening = win;
  }
  win.requestAnimationFrame(() => measure(box, below, win));
  return box;
}
