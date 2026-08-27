# site/mock — the fake Black Bloc API the pages are built against

The dashboard pages talk to routes that live in `black_bloc/api/`. This is a
zero-dependency Node stand-in for those routes, so the pages can be built,
looked at and exercised without running the bot, a Discord connection or a
database.

```
node site/mock/server.mjs
```

It serves `site/public` **and** the API on the same origin at
<http://127.0.0.1:8788> — the same one-origin arrangement the real deployment
uses, so a page needs no `api-origin` override.

| Variable | Default | What it does |
|---|---|---|
| `MOCK_PORT` | `8788` | port |
| `MOCK_TEST_MODE` | on | while on, every destructive write refuses with 409 and the test-guard sentence, exactly as the bot does under `TEST_MODE`. Set `MOCK_TEST_MODE=0` to let them through. |

## Being somebody else

Add `?as=…` to any URL — page or API. The mock remembers it in a `mock_as`
cookie, so `http://127.0.0.1:8788/index.html?as=stranger` loads the whole
dashboard as that person.

| `as=` | What the pages should show |
|---|---|
| `staff` (default) | the dashboard |
| `none` | "Sign in to see this", with the Discord button |
| `stranger` | signed in, not staff — "Ask a Lead for the role", no retry button |
| `unknown` | roles could not be checked — a fault with a **retry**, not a refusal |
| `expired` | session expired — sign in again |
| `down` | 503 from the data routes: "something is wrong at the bot", with a retry |

Stopping the server altogether is the sixth state: the page says Black Bloc is
not answering and calls it an outage, never a permission problem.

## Checking it still matches the bot

`contract.json` is the one home for every route's shape: for each route, the
keys the pages actually read, taken from their own property accesses.

```
MOCK_TEST_MODE=0 node site/mock/server.mjs &
node site/mock/check.mjs
```

`check.mjs` fetches all thirteen pages and every route in `contract.json` and
reports anything missing. **The bot's own test suite reads the same file** —
`tests/api/test_contract.py` runs it against the real routers with fakes — so a
shape cannot be right in one half and wrong in the other. Change a response
shape and you change three things together: the router, this mock, and
`contract.json`.

Set `MOCK_TEST_MODE=0`, or every destructive route answers 409 by design and
the checker counts that as a failure. `check.mjs` calls `POST /api/mock/reset`
before each route so every one sees the same fixture; that route exists for the
checker and is **not** part of the contract.

## What it is not

Fake data, held in memory: writes last until the process is restarted or reset.
The shapes follow the real routers in `black_bloc/api/` — where the two
disagree, **the real API wins** and this file is what changes.
`docs/info/phase8b-design.md` is the contract in prose, but it fixes the JSON
only for `/api/ref/*` and `/api/settings`; `contract.json` is where the rest is
written down, and it was settled by reading the routers.
