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

The page talks to **its own origin and the API origin, and to no other host.**

## The API origin

`index.html` carries `<meta name="api-origin" content="https://black-bloc.fly.dev">`.
That tag is the only place it is written down — point the site at a different
deployment by editing it, never by editing `app.js`.

The API's CORS allow-list is the other half: it is `SITE_ORIGIN` in the bot's
environment (default `https://blackbloc.heygabi.ai`). Both must agree or the
browser blocks every call.

## Deploying

⚠️ **A directory deploy ships the WORKING TREE, not a commit.** Deploy only
from a clean tree; if another agent has uncommitted work here, deploy from a
`git worktree add <tmp> HEAD` checkout instead.

```
git status --short          # must be empty
npx wrangler pages deploy site/public --project-name blackbloc
```

Custom domain `blackbloc.heygabi.ai` is attached in the Cloudflare dashboard
(Workers & Pages → blackbloc → Custom domains). Full runbook, including the
Discord Developer Portal redirect URI that must be registered:
`docs/access/site.md`.

## Checking it locally

Any static server will do; the page needs no origin of its own to render its
signed-out state.

```
python -m http.server 8788 --directory site/public
```

The API calls will be refused by CORS unless `SITE_ORIGIN` matches where you
are serving from — which is the correct behaviour, and the page says so in a
sentence rather than showing a status code.
