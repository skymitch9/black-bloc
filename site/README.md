# site/ — the Black Bloc status page

A static page. No build step, no framework, no bundler: what is in
`site/public/` is what is served.

## What it is

`site/public/index.html` is Phase 8a — the **read-only** status page. It signs
staff in with Discord and shows the bot's health, every feature's mode, loop
health and the last 50 actions. It writes nothing. Settings pages are 8b.

| Path | What |
|---|---|
| `public/index.html` | the page |
| `public/assets/app.js` | the only script this repo wrote: calls the API, renders, and owns the outage sentence |
| `public/assets/site.css` | the only CSS this repo wrote: the action-log table and the mode chips |
| `public/assets/estate-theme.css`, `theme.js`, `status-shell.css`, `permission-ux.js`, `motion.js`, `fonts/*` | a **SNAPSHOT** copied from `catalog-platform/sites/heygabi-home/public/assets/` on 2026-08-26 |

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

`index.html` carries `<meta name="api-origin" content="">`. **Empty means "the
origin this page came from"**, which is the normal case. Fill it in only to
point the page at a different deployment, and never edit `app.js` instead.

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
process serves the page and the API, so nothing has to be told where the other
half is.

A bare static server (`python -m http.server 8788 --directory site/public`)
renders the signed-out state, but every API call fails and the page says the
bot is not answering — correct behaviour, and a sentence rather than a status
code.
