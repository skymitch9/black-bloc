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

## What it is not

Fake data, held in memory: writes last until the process is restarted. The
shapes follow `docs/info/phase8b-design.md` (the contract) and, where the
contract names a route but not its fields, the column names of the matching
table in `black_bloc/storage/db.py`. Where the real API turns out to disagree,
**the real API wins** and this file is what changes.
