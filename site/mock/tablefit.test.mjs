// The table-height fit (site/public/assets/tablefit.js, re-exported by ui.js as fitScroll), proved without a browser.
//   node site/mock/tablefit.test.mjs
// Exits 0 when every fixture matched, 1 with a list of what did not.

import { FIT_BELOW, FIT_GAP, fitScroll, tableFit } from '../public/assets/tablefit.js';

const failures = [];
const is = (where, found, wanted) => {
  if (found !== wanted) failures.push(`${where}: is ${JSON.stringify(found)}, not ${JSON.stringify(wanted)}`);
};

is('owner window, pager 44 + gap 16', tableFit({ top: 260, viewport: 802, below: 60, floor: 416 }), 482);
is('tall window', tableFit({ top: 260, viewport: 1300, below: 60, floor: 416 }), 980);
is('short window keeps the 26rem floor', tableFit({ top: 500, viewport: 700, below: 60, floor: 416 }), 416);
is('no floor', tableFit({ top: 100, viewport: 500, below: 50 }), 350);
is('fractions floor down', tableFit({ top: 100.6, viewport: 500, below: 50 }), 349);

function fakeWin({ innerHeight, rem = 16 }) {
  const frames = [];
  const listeners = {};
  return {
    innerHeight,
    scrollY: 0,
    frames,
    listeners,
    document: { documentElement: { tag: 'html' } },
    getComputedStyle: (node) => ({ fontSize: `${rem}px`, overflowY: node?.overflowY || 'visible' }),
    requestAnimationFrame: (fn) => frames.push(fn),
    addEventListener: (type, fn) => { listeners[type] = fn; },
    flush() { while (frames.length) frames.shift()(); },
  };
}

const shell = (top) => ({ overflowY: 'auto', parentElement: null, getBoundingClientRect: () => ({ top }) });
const inCard = (parent) => ({ overflowY: 'visible', parentElement: parent, getBoundingClientRect: () => ({ top: 400 }) });

function fakeBox({ top, long = true, parent = inCard(shell(56)) }) {
  const props = {};
  const box = {
    isConnected: true,
    parentElement: parent,
    dataset: long ? { long: 'true' } : {},
    rect: { top, height: 0 },
    style: {
      setProperty: (name, value) => { props[name] = value; },
      set height(value) { props.height = value; },
      set maxHeight(value) { props.maxHeight = value; },
    },
    props,
    matches: (selector) => selector === '.table-scroll',
    getBoundingClientRect() { return this.rect; },
  };
  return box;
}

const win = fakeWin({ innerHeight: 795 });
const box = fakeBox({ top: 327 });
const pager = { isConnected: true, getBoundingClientRect: () => ({ height: 48 }) };
is('returns the box', fitScroll(box, { below: pager, win }), box);
is('opts the box in', box.dataset.fit, 'true');
is('waits for a frame', box.props['--table-fit'], undefined);
win.flush();
is('owner window: the window under the topbar, not under the box', box.props['--table-fit'], `${795 - 56 - 64}px`);
is('never sets height', 'height' in box.props, false);
is('never sets max-height inline', 'maxHeight' in box.props, false);

box.rect.top = -900;
win.innerHeight = 1000;
win.listeners.resize();
win.flush();
is('re-fits on resize; the box scrolled out of view does not matter', box.props['--table-fit'], `${1000 - 56 - 64}px`);

const bare = fakeBox({ top: 100 });
fitScroll(bare, { win });
win.flush();
is('no pager: the default below', bare.props['--table-fit'], `${1000 - 56 - FIT_BELOW - FIT_GAP}px`);

const windowed = fakeBox({ top: 300, parent: inCard(null) });
fitScroll(windowed, { win });
win.flush();
is('no scrolling shell: the window top', windowed.props['--table-fit'], `${1000 - 0 - FIT_BELOW - FIT_GAP}px`);

const tiny = fakeWin({ innerHeight: 400 });
const cramped = fakeBox({ top: 300 });
fitScroll(cramped, { win: tiny });
tiny.flush();
is('a short window keeps the 26rem floor', cramped.props['--table-fit'], '416px');

const short = fakeBox({ top: 100, long: false });
is('a short table is left alone', fitScroll(short, { win }), null);
win.flush();
is('a short table gets no fit', short.props['--table-fit'], undefined);
is('a short table is not opted in', short.dataset.fit, undefined);

const late = fakeBox({ top: 200 });
late.isConnected = false;
fitScroll(late, { win });
win.frames.shift()();
is('not on the page yet: waits', late.props['--table-fit'], undefined);
late.isConnected = true;
win.flush();
is('measured once it lands', late.props['--table-fit'], `${1000 - 56 - FIT_BELOW - FIT_GAP}px`);

const holder = { matches: () => false, querySelector: (selector) => (selector === '.table-scroll' ? fakeBox({ top: 0 }) : null) };
is('finds the box inside a holder', fitScroll(holder, { win })?.dataset.fit, 'true');
is('an empty holder is ignored', fitScroll({ matches: () => false, querySelector: () => null }, { win }), null);

box.isConnected = false;
win.innerHeight = 1200;
win.listeners.resize();
win.flush();
is('a box gone from the page is dropped, not re-measured', box.props['--table-fit'], `${1000 - 56 - 64}px`);

if (failures.length) {
  console.error(`tablefit: ${failures.length} failure(s)`);
  for (const one of failures) console.error(`  ${one}`);
  process.exit(1);
}
console.log('tablefit: every fixture matched');
