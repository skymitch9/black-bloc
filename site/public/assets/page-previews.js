import { start } from './app.js';
import { badge, card, el, section } from './ui.js';

const NOTE = 'Each card opens a preview. Every preview is static data inside the real shell — nothing on '
  + 'it reaches the bot — and its rail still points at today’s page, so the two are one click apart. '
  + 'Ranked as the UX audit ranked them, worst first; go-live is missing because it was rebuilt first.';

const PAGES = [
  { slug: 'posts', title: 'Posts', rank: 2, severity: 'danger', fails: 4, from: 3, to: 2,
    what: 'One section of posts and one of machinery, instead of two sections, a loose card and a separate detail page. A row opens the post in a drawer.' },
  { slug: 'rolemenus', title: 'Role menus', rank: 3, severity: 'danger', fails: 4, from: 9, to: 4,
    what: 'Four sections instead of nine, Applications lifted out to a page of its own, and a menu’s editor opening in a drawer over its row.' },
  { slug: 'minutes', title: 'Meeting minutes', rank: 4, severity: 'danger', fails: 3, from: 4, to: 2,
    what: 'Two sections instead of four: pressing a meeting opens its notes and transcript in a drawer over the table.' },
  { slug: 'chat', title: 'Chat', rank: 5, severity: 'warn', fails: 4, from: 9, to: 3,
    what: 'One row per intent with the editor in a drawer, and the machinery folded into Settings.' },
  { slug: 'events', title: 'Events', rank: 6, severity: 'warn', fails: 4, from: 7, to: 4,
    what: 'One queue with a drawer; raid trains as a second tab rather than a second half of the page.' },
  { slug: 'automod', title: 'Automod', rank: 7, severity: 'warn', fails: 3, from: 5, to: 3,
    what: 'The rule book IS the page, with the mode in the page head and the machinery folded into it.' },
  { slug: 'polls', title: 'Polls', rank: 8, severity: 'warn', fails: 3, from: 9, to: 4,
    what: 'Nine sections become four, and Create a poll moves to the button beside the heading.' },
  { slug: 'modmail', title: 'Modmail', rank: 9, severity: 'warn', fails: 3, from: 6, to: 6,
    what: 'A ticket opens in a drawer rather than a second section, and Doors splits into the front door and the ways into a ticket.' },
  { slug: 'requests', title: 'Requests', rank: 10, severity: 'warn', fails: 2, from: 9, to: 7,
    what: 'For staff: Done and Declined become one Closed list, only Open arrives open, and File a request moves to the button beside the heading.' },
  { slug: 'settings', title: 'Settings', rank: 11, severity: 'warn', fails: 2, from: 26, to: 3,
    what: 'Every key the bot reads in one searchable list, instead of a section per namespace.' },
  { slug: 'birthdays', title: 'Birthdays', rank: 12, severity: 'warn', fails: 2, from: 5, to: 3,
    what: 'Who has a birthday stored, by month, with the machinery folded away.' },
  { slug: 'honeypot', title: 'Honeypot', rank: 13, severity: 'warn', fails: 2, from: 4, to: 3,
    what: 'Who walked into a trap channel and what was done about it, on one page.' },
];

const SEVERITY = { danger: 'audit red', warn: 'audit orange' };

function previewCard(page) {
  return el('a', { class: 'guidecard', href: `/preview/${page.slug}.html`, 'data-slug': page.slug }, [
    el('div', { class: 'guidecard-head' }, [
      el('h3', { class: 'guidecard-title', text: page.title }),
      el('div', { class: 'guidecard-marks' }, [
        badge(`#${page.rank}`, null),
        badge(SEVERITY[page.severity], page.severity),
        badge(`${page.fails} of 6 tests failed`, null),
      ]),
    ]),
    el('p', { class: 'guidecard-goal', text: page.what }),
    el('p', { class: 'guidecard-meta', text: `${page.from} sections today → ${page.to} in the preview · today’s page: /${page.slug}.html` }),
  ]);
}

async function load() {
  const one = section('Every preview', NOTE, { count: PAGES.length, open: true });
  one.body.append(card(null, [el('div', { class: 'guidegrid' }, PAGES.map(previewCard))], { flush: true }));
  const node = one.node;
  node.setAttribute('data-span', 'full');
  document.getElementById('dash').replaceChildren(node);
}

start({ tab: 'previews', load });
