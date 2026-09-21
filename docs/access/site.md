# The config website — runbook

> **Audience:** whoever deploys or fixes the site, and the reviewer doing the
> first live sign-in. **Status:** TRACKED (owner, 2026-08-31 — was local-only
> until then; secret NAMES only). **Last verified:
> 2026-09-19** — the docs staleness pass after the **TEST_MODE lift** (2026-09-18 16:08).
> What changed here: three sentences that told a developer destructive routes answer **409**
> *"while `TEST_MODE` is on"* — they do not any more on the DEPLOYED site, and a reader who
> trusted that would expect a refusal where the bot will now act. ⚠️ **`MOCK_TEST_MODE` still
> defaults ON in the mock**, and that is deliberate; it just no longer *"matches the bot's real
> state"*, which is what its own paragraph claimed. Re-counted off disk: `ls site/public/*.html`
> = **20** (this page said 18). ⚠️ **NOT re-measured:** the route count (**`node
> site/mock/check.mjs` was not run** — it needs a listening mock; `../info/architecture.md`'s
> fact table carries the last measured figure, 186 at v139), DNS, the certificate, the OAuth
> redirect string, the CSP/HSTS/cookie claims, the first-sign-in drill and the route table's
> completeness. Nothing in this pass touched the live app beyond reading `/health`.
> Before that,
> **2026-09-16** — the Guides G2 build (branch `guides-pages`, ⚠️ **not merged and not
> deployed**) re-measured two figures only: `ls site/public/*.html` is **17 → 18**
> (`guides.html`) and `site/mock/contract.json` is **159 → 160** routes, both green under
> `node site/mock/check.mjs` on that branch. ⚠️ **NOT re-checked in that pass:** everything
> else on this page — DNS, the certificate, the OAuth redirect string, the CSP/HSTS/cookie
> claims, the first-sign-in drill, and the route table's completeness; nothing in it touched
> the live app. Before that, **2026-09-11 08:37** — the counts were re-measured off `main` `1d090e5`:
> `ls site/public/*.html` = **17** (and the list below names exactly those 17, checked
> name by name against `site/mock/contract.json`'s `pages`), and the route figure is
> **150**, not 89. 🔴 **The big correction: the "NOTHING HERE HAS BEEN RUN" block was
> retired.** It is false — the site has been live at https://blackbloc.heygabi.ai since
> Phase 8a, the certificate was issued, the redirect URI is registered, and people have
> signed in; **107** deploy lines in [`../deploys.log`](../deploys.log) record `/health`
> answering after each one. ⚠️ **NOT re-verified today:** the DNS records, the
> certificate, the OAuth redirect string byte-for-byte, the CSP/HSTS/cookie claims, the
> first-sign-in drill in §5, and the route table's completeness — nothing in this pass
> opened a browser or touched the live app. Before that, **2026-08-31** — the page count
> and the mock's figures (17 pages / 89 routes). Before that, **2026-08-27** — the routes table and the mock section below were added at the
> **Phase 8b merge** and read off the merged tree (`black_bloc/api/tools/*`,
> `site/mock/`); the deploy steps above them are unchanged and still
> **2026-08-26**, rewritten for **Option A** (one hostname) after the Phase 8a
> security review, then **re-read against `main` after the Phase 8a merge** that
> same day (was: branch `worktree-agent-ae8cc520aba4406d0` at `50205dd`). Every
> path, command and URL below was read off the merged tree. Three things changed
> at the merge and are corrected here: `settings.api_origin` is gone,
> `DISCORD_CLIENT_ID` joins the secrets to set, and the status page now also
> counts **open modmail tickets** (Phases 5–7 had not merged when 8a was built).
>
> ⚠️ **RETIRED 2026-09-11 — this header used to say "NOTHING HERE HAS BEEN RUN".**
> That was written before Phase 8a shipped and stopped being true almost immediately;
> it is kept here, struck, because a reader who acted on it would have treated a live
> production site as an unbuilt plan. ~~The DNS records have never been created, the
> certificate has never been issued, the redirect URI has never been registered, and no
> human has ever signed in.~~ **What is true now:** the site is LIVE at
> https://blackbloc.heygabi.ai, the certificate resolves, sign-in works, and every one
> of the **107** lines in [`../deploys.log`](../deploys.log) records `/health` answering
> after the deploy.
>
> ⚠️ **What is STILL not verified by any doc pass:** the `__Host-` cookie prefix, the
> CSP, HSTS and the static mount are asserted by tests against an in-process ASGI
> client, which is **not a browser** — nobody has read those headers off a real browser
> and written the result down. The steps in §2 (DNS) and §3 (redirect URI) were run once
> by the owner and have not been re-read against Cloudflare or the Developer Portal
> since.

Companions: [`deploy.md`](deploy.md) (the bot on Fly),
[`../info/phase8-design.md`](../info/phase8-design.md) (why any of this
exists), [`../info/code-notes.md`](../info/code-notes.md) (why the code is
shaped the way it is), `site/README.md` in the repo (the developer-facing
half, which IS committed).

## ⚠️ Option A — one app, one hostname (owner decision, 2026-08-26)

**There is no second deployment.** The Fly app `black-bloc` serves the page
*and* the API at **`https://blackbloc.heygabi.ai`**:
`black_bloc/api/server.py` mounts `site/public` with `StaticFiles(html=True)`
at `/`, after the API routers, so `/health` and `/api/*` win and everything
else is a file.

What that decision deleted, and why each mattered:

| Gone | Why |
|---|---|
| the Cloudflare Pages project, `site/wrangler.toml`, `wrangler pages deploy` | the page ships inside the bot's image; a directory deploy cannot ship another agent's working tree if there is no directory deploy |
| `CORSMiddleware` | same-origin `fetch` needs no CORS, and an allow-list that must match a second hostname is one more thing to get wrong |
| `API_ORIGIN` as a second hostname | one value, `SITE_ORIGIN`. The `settings.api_origin` alias was **removed at the main merge** (2026-08-26) rather than kept for a release — nothing read it, and a second name for one fact is checklist item 15. Use `settings.origin`. An `API_ORIGIN` environment variable is **no longer read** — delete it wherever it is set |
| the `SameSite=Lax` cross-site constraint | it was a real, written-down defect: a Lax cookie does not ride a cross-site `fetch`, so the old two-hostname shape would have signed everybody out on their first API call. One origin makes it moot, and the cookie stays `Lax` |

⚠️ **The API is now PUBLIC on the internet, on the same hostname as the
page** (finding F9). Every route requires a signed-in staff session except
**`/health`**, which is deliberately public because it is the uptime probe and
says nothing a stranger could not learn by watching the bot come online.
`/openapi.json`, `/docs` and `/redoc` are switched off.

## 1. Secrets and config to import — set these on Fly before anything else

Names only; values live in `fly secrets` and the Discord Developer Portal.

```
flyctl secrets set --app black-bloc DISCORD_CLIENT_ID=…
flyctl secrets set --app black-bloc DISCORD_CLIENT_SECRET=…
flyctl secrets set --app black-bloc SESSION_SECRET=…
flyctl secrets set --app black-bloc SITE_ORIGIN=https://blackbloc.heygabi.ai
```

⚠️ **`DISCORD_CLIENT_ID` is in that list on purpose.** It is not a secret, but
`site_login_configured` is false without it and sign-in never switches on — the
commonest way to deploy a page that says "signing in is not switched on yet".

| Name | What it is | Where a copy lives |
|---|---|---|
| `DISCORD_CLIENT_ID` | the Black Bloc application's client id — not a secret, but sign-in is off without it | Developer Portal → Black Bloc → OAuth2 |
| `DISCORD_CLIENT_SECRET` | the same application's secret | Developer Portal (re-mintable there) |
| `SESSION_SECRET` | any long random string; it signs the session cookie | `fly secrets` and `.env` only. **Changing it signs everybody out** — that is also the emergency lever if a cookie is ever believed compromised |
| `POLL_VOTE_SECRET` | long random string; keys the HMAC that hashes anonymous poll votes (set 2026-08-31) | `fly secrets` and `.env` only. ⚠️ **Never lose or casually rotate it**: a poll created while it was set refuses votes in words without it (refusing beats double-counting). Deliberately NOT a settings-registry key — a MAC key the dashboard can show is not a MAC key |
| `SITE_ORIGIN` | the one hostname (default `https://blackbloc.heygabi.ai`) | `fly.toml`/`fly secrets`. It is the OAuth redirect base, where sign-in returns to, and whether the cookies get `Secure` |
| `SITE_ROOT` | the directory served (default `site/public`); the Dockerfile puts it at `/app/site/public` | nothing to set — listed so a "the page 404s" hunt has a name to grep |

Until `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET` and `SESSION_SECRET` are all
set, sign-in is **off** and the page says so in a sentence that blames the
setup and not the visitor. That is deliberate.

⚠️ **`SITE_ORIGIN` must be `https://…`.** The cookies are named `__Host-…`,
which a browser honours only with `Secure`, `Path=/` and no `Domain` — and
`Secure` is derived from this value's scheme. An http `SITE_ORIGIN` produces
cookies every browser silently drops, which looks exactly like "signing in
does nothing".

## 2. DNS — point the hostname at Fly (proxy OFF)

In Cloudflare, on `heygabi.ai`:

```
A     blackbloc  →  66.241.125.10
AAAA  blackbloc  →  2a09:8280:1::17c:d6fb:0
```

⚠️ **Both records must be DNS-only (grey cloud, proxy OFF).** Fly issues and
serves the certificate itself; proxying through Cloudflare puts a second TLS
terminator in front of it and breaks the ACME check.

Then issue the certificate and watch it:

```
flyctl certs add   blackbloc.heygabi.ai --app black-bloc
flyctl certs check blackbloc.heygabi.ai --app black-bloc
```

`certs check` is the one to re-run while waiting; it names which check is
outstanding rather than just failing.

## 3. ⚠️ The redirect URI to register — this exact string

Developer Portal → the Black Bloc application → **OAuth2** → **Redirects** →
Add:

```
https://blackbloc.heygabi.ai/api/auth/callback
```

**It is on the site's own hostname now** — the old
`https://black-bloc.fly.dev/api/auth/callback` is wrong under Option A and
must be removed. Discord compares byte for byte: no trailing slash, no `www`.
The value the code sends is derived at `black_bloc/config.py`'s
`oauth_redirect_uri` from `SITE_ORIGIN`, so if `SITE_ORIGIN` ever changes this
registration changes with it or every sign-in fails with `invalid_request`.

No other Discord setting is needed: the scopes (`identify`,
`guilds.members.read`) are requested per-authorisation, not configured.

## 4. Deploy

One deploy ships the bot, the API and the page:

```
flyctl deploy --app black-bloc --ha=false
```

⚠️ **Do not run `fly launch`** — it rewrites `fly.toml`, and the three machine
settings in `[http_service]` are load-bearing: the machine answering HTTP is
the machine holding the gateway websocket, so `auto_stop_machines = false`,
`auto_start_machines = false` and `min_machines_running = 1` must survive every
edit. An idle HTTP service is not an idle bot.

Confirm:

```
curl -s https://blackbloc.heygabi.ai/health
curl -sI https://blackbloc.heygabi.ai/ | grep -i "strict-transport\|content-security"
```

`/health` is public on purpose. Everything else answers `401` with a sentence
until you sign in.

## 5. First sign-in — the drill

In order, because each step's failure looks different:

1. Open `https://blackbloc.heygabi.ai`. Expect the signed-out state and a
   **Sign in with Discord** button, shown *immediately* — the page paints its
   "Checking…" row before it asks the API anything.
2. Click it. Discord asks to authorise **identify** and **members read**.
3. Expect a bounce back to the site, already signed in, showing health,
   feature modes, loops and the action log.
4. Have a **non-staff** member try it. Expect: signed in, greeted by name, and
   told this is for mods and to ask a Lead — never a bare 403.
5. Open the browser console. **A CSP violation is a bug to report**, not
   something to loosen the policy over: the page was built with no inline
   script, no `eval` and no third-party host.

## When it looks broken — read the symptom, not the status

| What you see | What it actually is |
|---|---|
| "Black Bloc is not answering" | the app is down, or the request took more than ten seconds. There is no CORS any more, so this is now an honest outage rather than a same-origin mistake in disguise. Check `/health`. |
| Discord says `invalid_request` / redirect mismatch | §3. The registered URI is not byte-identical to `<SITE_ORIGIN>/api/auth/callback`, or the old `black-bloc.fly.dev` one is still registered and being sent. |
| "Signing in is not switched on for this server yet" | §1 — one of the three sign-in values is unset. Not a permission problem. |
| Sign-in appears to do nothing; you land back signed out | ⚠️ the `__Host-` cookies were dropped. `SITE_ORIGIN` is not `https://`, or something in front of Fly is stripping `Secure`. §1. |
| "That is more sign-in attempts than Black Bloc will take in a minute" | the rate limit (ten a minute per client IP). It is keyed on `Fly-Client-IP`; if **everyone** trips it at once, the proxy header is missing and every visitor is sharing one bucket. |
| **"Black Bloc could not check your roles with Discord just now"** | the fifth state, and it is **not** a refusal. The bot is up but could not consult the guild — still starting, the guild not yet cached, or a Discord outage. The retry button is the fix. ⚠️ Nobody is told they are not staff in this case, by design: the old code answered "not staff", which sent real mods to ask a Lead for a role they already had. |
| "signed in but not staff" for somebody who IS a mod | the staff set is derived from who can *see* the staff channel (`staff_channel_id`), computed permissions and all. Run `/settings` in Discord and check the channel; the site and the slash commands share one definition, so if one is wrong both are. |
| A mod who was just demoted still has access | they should not — staff is re-checked against the guild on **every** request, and the cookie's flag is no longer allowed to overrule a guild that answered. Signing them out (or rotating `SESSION_SECRET`) is the hard stop. |

## The pages

**Nineteen** HTML files in `site/public/`, served by the same app at `/`
(re-counted 2026-09-16 — **18 → 19**, `posts.html` added by the Posts build on branch
`posts`; `guides.html` was **17 → 18** on branch `guides-pages` before it. The nineteen
names below match `site/mock/contract.json`'s `pages` list exactly. It said "Thirteen"
until 2026-08-31, which predates Polls, Chat, Requests and Members):
`index.html` (Overview), `moderation.html`, `automod.html`, `modmail.html`,
`events.html`, `golive.html`, `rolemenus.html`, `birthdays.html`,
`tempvoice.html`, `honeypot.html`, `polls.html`, `chat.html`, `requests.html`,
`members.html`, `settings.html`, `audit.html`,
`health.html`, `guides.html`, `posts.html`. `site/README.md` says what each one does.

⚠️ **`guides.html` is the SECOND page a signed-in member who is not staff may open**
(`requests.html` was the first). It is one page for two views — the hub, and a guide at
`guides.html#<slug>` — and its routes are under `/api/guides`, gated by
`member_read_dependency` for the reads and `staff_dependency` (plus `guides_who_edits`)
for the writes. `POST /api/guides/{slug}/confirmed` is the one guide write a member makes.
`GET /api/guides/media/{id}` answers a picture rather than JSON and keeps its own
`Cache-Control: private, max-age=86400` — the one named exception to the site's
`no-store` middleware (`api/server.py:KEEPS_ITS_OWN_CACHE`).

⚠️ **`posts.html` is staff-only and is the only page that draws text nobody here
wrote.** Its preview is `assets/discordmd.js`, which escapes HTML **first** and works on the
escaped text from there — the reason its mention patterns read `&lt;#(\d+)&gt;`. It never
emits an anchor: a masked link renders as link-coloured text with the address in a `title`.
The renderer has no Python half, so its fixtures are `site/mock/discordmd.test.mjs`, run by
`scripts/deploy.ps1` and by CI beside `check.mjs`; an injection fixture and Carl's own seed
text are both in it. Its routes are under `/api/posts`, staff-gated end to end, and
~~**Post it** answers the guard's existing **409** while `TEST_MODE` is on.~~ ⚠️ **Superseded
2026-09-18 16:08:** there is no guard, so **Post it** posts. What keeps the welcome post out of
`#welcome` now is `posts_mode` being **shadow** — the real message goes to `shadow_channel_id`
(`#welcome-test`) and the page's pill reads *posted (shadow)*.

⚠️ **Every page links `/favicon.ico`** (added 2026-08-27 — the log showed a
`GET /favicon.ico 404` on every single page load). The file is a 32×32 ICO
written by hand into the repo, so there is no image toolchain and no CDN to
depend on, and `img-src 'self'` covers it with no CSP change. A page added
later without the `<link rel="icon">` brings the 404 back;
`tests/api/test_server.py` asserts every page carries it and that the app
serves the file.

## The routes, after Phase 8b (2026-08-27)

⚠️ **This table is the Phase 8b snapshot and is BADLY INCOMPLETE — it covers roughly a
third of the surface.** `site/mock/contract.json` carries **160 routes** (re-measured
2026-09-16; it was 89 when this warning was first written, and the table below predates
even that). Everything Phases 9–19 and the panel program added is missing from it —
polls, chat, requests, members, timed roles, applications, raid trains, YouTube, pings,
costs, the self-test and the operator reads. **`site/mock/contract.json` is the one home
for the route shapes** — read it, and never trust this table for completeness. A
readable path-by-path list of the GETs lives in
[`operator-read.md`](operator-read.md#the-paths-worth-reading).

Every one is under `/api`, JSON, staff-gated by the same
`staff_dependency` 8a introduced (401 `not_signed_in`, 403 `not_staff`,
503 `staff_unknown`; every error body is `{error, message}` with a sentence).
**Writes** additionally go through `api/writes.py`: one rate-limit bucket **per
bot** (60 a minute per session, not per router), the guild/database checks, the
guard's 409 carrying the **cog's own** refusal sentence, and one
`web.<area>.<verb>` line in the action log beside the feature's own line.

| Surface | Routes | Notes |
|---|---|---|
| Reference | `GET /api/ref/{channels,roles,members,names}` | the pickers and the name resolver. **Cache only** — no `fetch_*` call anywhere in `api/names.py`, so a table render never costs a Discord round-trip |
| Settings | `GET /api/settings` · `PUT`/`DELETE /api/settings/{key}` · `GET /api/settings/audit` | `PUT` returns the **stored** value through the same `SettingsStore.set(..., by=)` the slash commands use, and a refusal is the validator's own sentence as a 400 |
| Moderation | `GET /api/mod/cases[?user_id=&page=]` · `GET/POST /api/mod/cases/{id}[/apply]` · `POST /api/mod/cases/{id}/{reason,note,void,restore}` · `POST /api/mod/{warn,timeout,untimeout,kick,ban,unban}` · `GET /api/mod/rules` · `PUT /api/mod/rules/{name}` | `cases` is the one paged route: `{cases,total,page,pages,per_page}`. Discord refusing an action is a **502**, never a 200 with a sad message. `GET /api/mod/parity` was removed 2026-08-27. The four correction routes (2026-09-05) call the same shared functions `/mod`'s panel does and pass `via=website`, so a correction leaves ONE `web.case.*` row: 404 `no_such_case`, 400 `bad_reason`/`bad_note`, 409 `already_voided`/`not_voided` |
| Modmail | `GET /api/modmail/tickets[?status=]` · `GET /api/modmail/tickets/{id}` · `POST …/{reply,close}` · `GET/POST /api/modmail/snippets` · `DELETE /api/modmail/snippets/{name}` · `GET/POST /api/modmail/blocks` · `DELETE /api/modmail/blocks/{user_id}` | closing refuses under the guard only when it would **delete** the channel |
| Events | `GET /api/events[?status=]` · `POST /api/events/{id}/{approve,deny,cancel}` | same lock and same allowed-transition check as the buttons in Discord |
| Go-live | `GET /api/golive/{links,optouts,sessions}` · `DELETE /api/golive/links/{user_id}` | |
| Role menus | `GET/POST /api/rolemenus` · `PUT/DELETE /api/rolemenus/{name}` · `POST /api/rolemenus/{name}/post` | `PUT` takes the **whole** option list and syncs to it |
| Birthdays | `GET /api/birthdays` · `PUT/DELETE /api/birthdays/{user_id}` · `POST /api/birthdays/{user_id}/optin` | ⚠️ **`POST /api/birthdays/import` is GONE (branch `events-group`, 2026-09-20)** — the Birthday Bot that produced the export was kicked, so the importer, its daily loop and the seed file went with it |
| Temp voice | `GET /api/tempvoice/channels` · `POST /api/tempvoice/setup` | setup **repairs or adopts** the lobby the server already has; `repaired` and `adopted` are successes, not refusals |
| Honeypot | `GET /api/honeypot/hits[?limit=]` · `POST /api/honeypot/hits/{id}/ban` · `POST /api/honeypot/setup` | Ban-now is the trap's own ban path, test-mode refusal included |
| Status | `GET /api/status` · `GET /api/actions[?limit=&kind=&user_id=]` | as 8a, plus `actor_name`/`target_name` resolved. `kind=` matches a whole kind **or** a prefix, so `kind=web` is "everything done from the dashboard" |

⚠️ **`modlog_channel_id` and `mod_dm_on_action` are served in the `automod`
namespace**, not as two one-key groups of their own. The namespace is otherwise
the key prefix before the first `_`; the exceptions live in one map,
`settings_api.py:NAMESPACE_OVERRIDE`. A new moderation key with a new prefix
needs a line there or it grows its own group. (A third key was in that map until
2026-08-27, when the parity tool it belonged to was removed.)

## Running the site without a bot — the mock

`site/mock/server.mjs` serves `site/public` **and** `/api/*` on one origin, the
way the real deployment does, with fixture data and no dependency beyond Node
itself. It is how the pages are looked at without a Discord token or a database.

```bash
node site/mock/server.mjs                 # http://127.0.0.1:8788
MOCK_PORT=9000 node site/mock/server.mjs  # somewhere else
MOCK_TEST_MODE=0 node site/mock/server.mjs  # let destructive writes succeed
```

`MOCK_TEST_MODE` defaults **on**, so every
destructive write refuses with a 409 and the guard's sentence — the refusal path
is the one a developer meets first rather than one nobody exercises. ⚠️ **It no longer
"matches the bot's real state"** (that clause was true until 2026-09-18 16:08, when the owner
lifted `TEST_MODE`); the default is kept because meeting the refusal first is still the safer
shape for the mock, not because the deployed bot behaves that way. ⚠️ **Do not read a mock 409
as proof the live bot would refuse** — it would not.

**Try the five permission states** by appending `?as=` to any page or route; it
also sets a cookie, so the rest of the session stays in that state:

| `?as=` | What you get |
|---|---|
| *(absent)* or `staff` | signed in, staff — the working dashboard |
| `none` | signed out (401) |
| `stranger` | signed in, not staff (403) |
| `unknown` | roles could not be checked (503) — the fifth state, with a retry |
| `expired` | the session has expired (401) |
| `down` | the database is unreachable (503) |

**Checking the mock still matches the bot** — run the mock, then the checker:

```bash
MOCK_TEST_MODE=0 MOCK_PORT=8788 node site/mock/server.mjs &
MOCK_PORT=8788 node site/mock/check.mjs
```

It fetches all **20** pages (counted off disk 2026-09-19; this said 19, and the header said 18 — `ls site/public/*.html`) and every route (**186** at v139, off [`../info/architecture.md`](../info/architecture.md)'s fact table, which owns the figure — ⚠️ **not re-run here**; this said 168 as of 2026-09-16) and asserts the keys in
`site/mock/contract.json`. ⚠️ **`site/mock/contract.json` is the one home for
those shapes**, and `tests/api/test_contract.py` asserts the **real** routers
against the same file — so the mock cannot teach a shape the bot does not
serve. If you change a response shape, change the router, the mock and that
file together, and both checks stay green. Set `MOCK_TEST_MODE=0` or every
destructive route answers 409 and the checker reports it as a failure.

## What this site deliberately does NOT do

- **Phase 8b writes; 8a did not.** Every write goes through the same code path
  the slash command uses, so the audit trail stays one table and the bot sees
  the change live. ~~What it still does **not** do is act outside the test channel
  while `TEST_MODE` is on — those routes answer 409 with the same sentence the
  slash command gives.~~ ⚠️ **Superseded 2026-09-18 16:08** — `TEST_MODE` is off, so a write
  from the website reaches the real server exactly as the slash command does. The website was
  never a *wider* door than Discord and still is not; what changed is that neither is narrowed
  any more. The 409 path survives in the code and in the mock for a future rehearsal.
- **It has no connection to heygabi** beyond sharing a domain (owner decision,
  2026-08-26): no estate auth, no auth worker, no estate status endpoints, no
  shared deploy script. The theme is a **copied snapshot** — a new estate theme
  reaches this page only if someone copies it in.
- **It talks to no host but its own origin.** Under Option A there is not even
  a second one. If a future change adds a host, that is a decision to take to
  the owner, not a detail — and the CSP will refuse it first.
