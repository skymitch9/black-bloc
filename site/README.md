# site/ — the Black Bloc dashboard

A static site. No build step, no framework, no bundler: what is in
`site/public/` is what is served.

## What it is

Phase 8b — the **staff dashboard**. It signs staff in with Discord and gives
every feature its own tab: what the bot is doing, and the controls that change
it. Phase 8a's read-only status page is still here, as the **Health** tab.

Thirteen tabs, one HTML file each, one module each. The nav is a left rail on
wide screens and a scrolling strip of tabs on a phone, and it is built from one
list in `app.js` — never thirteen copies to drift.

| Tab | File | What it does |
|---|---|---|
| Overview | `index.html` | mode chips that link to their tab, open counts, the last 10 actions |
| Moderation | `moderation.html` | cases (search by member, paged), case detail with Apply-now, the warn/timeout/kick/ban/unban bar |
| Automod | `automod.html` | the rule book, exempt roles and channels, the arming switch |
| Modmail | `modmail.html` | tickets → messages with staff notes marked, reply / anonymous reply / close, snippets, blocks |
| Events | `events.html` | the queue with Approve / Deny (reason) / Cancel |
| Go-live | `golive.html` | Twitch links (unlink), opt-outs, recent streams, a live template preview |
| Role menus | `rolemenus.html` | menus, the options editor, post |
| Birthdays | `birthdays.html` | by month, set and remove |
| Temp voice | `tempvoice.html` | the channels open now, setup and repair |
| Honeypot | `honeypot.html` | hits with Ban-now, trap setup |
| Settings | `settings.html` | every registry key, grouped by namespace, typed inputs |
| Audit | `audit.html` | the settings audit and everything done from the web |
| Health | `health.html` | 8a: gateway, uptime, loop health, the last 50 actions |

| Path | What |
|---|---|
| `public/assets/api.js` | the fetch wrapper: same-origin, session cookie, a 10 s timeout, every failure turned into one of the refusal states — plus the batched name resolver and the reference-data caches |
| `public/assets/app.js` | the shell every page boots through: the tab list, the gate, refresh and sign-out |
| `public/assets/ui.js` | tables, pager, pickers, typed setting inputs, the confirm dialog, the notice line |
| `public/assets/page-*.js` | one module per tab; they hold no HTML, they build DOM |
| `public/assets/site.css` | the only CSS this repo wrote: tokens only, no raw colours |
| `public/favicon.ico` | a 32×32 ICO written by hand into this repo (no image toolchain, no CDN): a blocky **B** in the cyberpunk accent on the page background. Every page links it — the log used to show `GET /favicon.ico 404` on every load |
| `mock/server.mjs` | a zero-dependency stand-in for the API — see `mock/README.md` |
| `mock/contract.json` | **the one home for every route's shape** — read by `mock/check.mjs` AND by the bot's `tests/api/test_contract.py`, so the mock and the real routers cannot answer differently |
| `mock/check.mjs` | fetches every page and every route from a running mock and asserts `contract.json` |
| `public/assets/estate-theme.css`, `theme.js`, `status-shell.css`, `permission-ux.js`, `motion.js`, `fonts/*` | a **SNAPSHOT** copied from `catalog-platform/sites/heygabi-home/public/assets/` on 2026-08-26 |

**Every snowflake on every page renders as a name**, with the id in a `title`
tooltip; one batched `/api/ref/names` call per page load, cached in the page.
An id the resolver could not look up is shown as the id and says so — it never
gets a made-up name, and a lookup that failed is never reported as "unknown".

**Every write shows the API's own sentence**: on refusal the sentence, on
success the new value, and neither reloads the page. Destructive controls ask
first, in an in-page dialog — never `window.confirm`.

⚠️ **The snapshot is a copy, not a link** (owner decision 2026-08-26). This
site shares a domain with heygabi and nothing else — no estate auth, no shared
deploy, no sync script, no runtime dependency in either direction. A sixth
estate theme reaches this page only if someone copies the two files in again.
The fonts' OFL licences travel with the faces and must stay.

The page talks to **its own origin and to no other host.**

## One hostname, one origin (owner decision, 2026-08-26)

⚠️ **There is no separate front-end deployment.** The Fly app `black-bloc`
serves this directory itself, mounted at `/` by `black_bloc/api/server.py`
after the API routers, so `https://blackbloc.heygabi.ai` is both the page and
the API. There is no Cloudflare Pages project, no `wrangler.toml`, and no CORS
middleware — a same-origin `fetch` needs none, and the `SameSite=Lax` session
cookie works because nothing is cross-site any more.

Every page carries `<meta name="api-origin" content="">`. **Empty means "the
origin this page came from"**, which is the normal case. Fill it in only to
point the pages at a different deployment, and never edit `api.js` instead.

The directory the app serves is `SITE_ROOT` (default `site/public`, relative to
the working directory; the Dockerfile copies it to `/app/site/public`).

## Deploying

The page ships **inside the bot's image** — there is no second deploy:

```
flyctl deploy --app black-bloc --ha=false
```

Full runbook, including DNS, the certificate and the Discord Developer Portal
redirect URI that must be registered: `docs/access/site.md`.

## Checking it locally

Run the bot with `API_ENABLED=true` and open `http://127.0.0.1:8080` — the same
process serves the pages and the API, so nothing has to be told where the other
half is.

Without the bot, use the mock — it serves the pages and a full fake API with
realistic data, and `?as=…` puts you in any of the refusal states:

```
node site/mock/server.mjs        # http://127.0.0.1:8788
```

To check the mock still matches the bot, run it with writes let through and
then the checker:

```
MOCK_TEST_MODE=0 node site/mock/server.mjs &
node site/mock/check.mjs         # 13 pages, 49 routes, every key the pages read
```

`site/mock/README.md` has the table of states. A bare static server
(`python -m http.server 8788 --directory site/public`) renders the signed-out
state and nothing else, which is also correct behaviour: a sentence rather than
a status code.
