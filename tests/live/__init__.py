"""The one deliberate exception to "tests mirror the package".

Everything else under `tests/` mirrors a module in `black_bloc/`. These mirror no module
at all: they hit the DEPLOYED api over HTTPS and prove the thing no fixture can — that the
routes the pages read answer on the real host, that a self-test run really does exercise
Discord through the running bot and clean up after itself, and that a caller with no token
is refused in words rather than with a bare status.

They are excluded from the default `pytest` run by `-m 'not live'` in `pyproject.toml`, and
skipped whole unless both `BLACK_BLOC_LIVE_URL` and `BLACK_BLOC_LIVE_TOKEN` are set. The
runbook is `docs/access/testing.md`.
"""
