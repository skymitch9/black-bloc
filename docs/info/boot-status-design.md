# Boot status — red while it restarts, green when it is ready

> **Audience:** the build agent and reviewers. **Status:** TRACKED · ✅ **LIVE as v134** — merge `6421c0f`, release `79fcef8`,
> deployed **2026-09-17 19:01** Phoenix; sweeps **591–593** are the owner's; verified: boot log clean (presence cog loaded, logged in 19:01:17, 11 s after the old process's shutdown line) + /health ready; ✅ the red → green flip was SEEN by the owner on a machine restart at 21:17 (row 591: *"i saw it turn red then green for the bot yes"*); the shutdown→login gap measured 9 s from the log. Was: 🔧 BUILT on branch `boot-status`, cut from `main` `5ceea19`. **Last verified: 2026-09-17**
> — measured on that branch: `pytest -n 8` **6668 passed, 3 skipped** in both orders
> (`BB_REVERSE=1` for the second), `ruff check .` clean, `node site/mock/check.mjs` *20 pages,
> 186 routes, **24** core settings, all keys present*, both `.mjs` fixture tests green, every
> `site/public/assets/*.js` parses as an ES module. Registry keys **277 → 280**, core settings
> **21 → 24**, namespaces still **25**. ⚠️ **Nothing here has met Discord** — see
> *What was NOT verified*. ⚠️ Secret NAMES only.

## The owner's ask, verbatim (2026-09-17, 18:0x)

*"when the bot is restarting can we set its status to red and have the status message say im
currently restarting and booting and then turn green again when its ready to accept request in
discord status? is that a fair ask or is that not gonna work"*

Fair, with one limit that is Discord's and not ours: **a presence exists only while the bot is
CONNECTED.** The seconds between the old process stopping and the new one connecting show
grey/offline, not red. Everything from the first connect onwards is ours.

## What a member sees, at each of the three moments

| Moment | Dot | Status line |
|---|---|---|
| The old process is gone, the new one has not connected | ⚫ grey (offline) | nothing — Discord's, not ours |
| From the first connect until ready | 🔴 Do Not Disturb | `boot_status_text` — *"Restarting and booting — back in a moment"* |
| Ready (Discord's `on_ready`, after every cog loaded in `setup_hook`) | 🟢 online | the usual `status_prefix` + head count — *"Cookout attendees: 412"* |
| The last second of a planned shutdown | 🔴 Do Not Disturb | `shutdown_status_text` — *"Restarting — back in a moment"* |

## A. From the first connect: red and the sentence

`BlackBlocBot.__init__` (`black_bloc/bot.py:55`) now builds the `Database` and the
`SettingsStore` **first**, so it can hand `presence.boot_presence(store)` — `status=dnd` plus a
`discord.CustomActivity` — to `super().__init__` as keyword arguments. discord.py copies those
into `ConnectionState._status` / `._activity`, which is exactly what the **IDENTIFY** packet
reads (`discord/gateway.py:DiscordWebSocket.identify`). So the red dot and the sentence are
part of the first thing Discord is ever told about this session; there is no window in which a
booting bot reads as green.

**Which text is sent.** The database is shut at construct time, so the sentence built there is
the registry **default**. `setup_hook` re-reads it once the database is open
(`bot.py:88 _apply_boot_presence`) and assigns `self.status` / `self.activity` — and because
`Client.login()` calls `setup_hook()` **before** `connect()` ever opens a socket (measured
against the installed discord.py 2.7.1), the value a Lead stored on the Settings page is the
one IDENTIFY actually carries. The construct-time default is the floor for a boot where the
database cannot be opened at all.

**Which guild's value.** No guild objects exist during `setup_hook`, so `presence.status_guild`
cannot be used. The stored value is read for `settings.dev_guild_id` when it is set, and the
registry default is used when it is not. Black Bloc is a one-server bot, so in practice that is
the server.

## B. Ready: green and the usual face, in ONE call

`cogs/presence.py`'s `on_ready` already calls `apply_status` → `presence.update_status`.
`update_status` now passes `status=discord.Status.online` in the **same** `change_presence` call
as the custom activity (`presence.py:67`). ⚠️ **Never two calls** — a green bot still saying
*"restarting and booting"*, even for a moment, is the thing this section exists to prevent.

"Ready" is Discord's own ready event, which fires after `setup_hook` has loaded every cog. The
API's `/health` `ready` flag already reads `bot.is_ready()`; there is no second notion of ready
here and none was added.

**The one path where the count cannot be read.** `update_status` returns `None` without sending
anything when there is no guild in the cache or no `member_count` — and a bot left on that path
would stay red, saying it is restarting, forever. So the cog's `on_ready` calls
`presence.go_green` when `apply_status()` answers `None` (`cogs/presence.py:98`): online, no
sentence, which is exactly today's behaviour for a bot with no count to show. See *Deviations*.

## C. Before a planned shutdown: red again

`BlackBlocBot.close` (`bot.py:123`) calls `_say_shutting_down` **first**, before the API tasks
are cancelled, the database is closed or the socket goes away. One best-effort
`change_presence(status=dnd, activity=CustomActivity(shutdown_status_text))`, wrapped so that
any failure is swallowed with one `log.debug` and never delays or breaks the close.

⚠️ **This is the ask's floor, and the deviation to name.** Discord keeps a bot's presence only
while it is connected, so the red "restarting" reads for at most the last second before the
session drops and the bot goes grey. It cannot cover the gap between processes; nothing can.

## D. Keys — every word is a key, and every decision is configurable both ways

All three sit under **`core`** (checklist 33). They are in `CORE_KEYS` rather than left to
`namespace_of`, which would have opened a `boot` group and a `shutdown` group — and the
`/settings` group select is at Discord's cap of **25**, where a 26th namespace is dropped
silently. `tests/test_settings_store.py` guards the cap and the filing.

| Key | Type | Default | What it decides |
|---|---|---|---|
| `boot_status_mode` | enum `off` \| `on` | **`on`** | `off` is today's behaviour: no initial presence and no shutdown flip |
| `boot_status_text` | text | *"Restarting and booting — back in a moment"* | the sentence while it starts up |
| `shutdown_status_text` | text | *"Restarting — back in a moment"* | the sentence on the way down |

Both doors, for free: the registry entry gives the dashboard's Settings page ▸ **core** and the
`/settings` panel's own key card. Mirrored in `site/mock/server.mjs` (rows + its `CORE_KEYS`
copy), `site/mock/contract.json` (`settings.core_keys`) and `site/public/assets/labels.js`.

## Deviations

**2026-09-17 — the setup_hook re-read APPLIES the stored sentence rather than only reading it.**
The brief said to re-read the key in `setup_hook` and noted that *"`change_presence` will apply
it at the first ready anyway"*. It would not: at first ready the sentence is replaced wholesale
by the head count, so a re-read that did not assign anything would make `boot_status_text` a key
whose value could never appear — which the "every word the bot posts is editable on the site"
rule forbids. `change_presence` is also impossible there (`self.ws` is `None` until `connect()`).
What landed instead assigns `self.status` / `self.activity`, the documented public setters, which
IDENTIFY then reads. Verified against the installed discord.py 2.7.1: `Client.login()` awaits
`setup_hook()` before `connect()`, and `identify()` builds its `presence` block from
`ConnectionState._status` / `._activity`.

**2026-09-17 — `presence.go_green` was ADDED; the brief did not ask for it.** Section B explains
why: `update_status`'s two early returns send nothing, so without it a ready bot that cannot read
a head count stays red and says it is restarting for the life of the process. It is one function
and one call site, behind the `apply_status() is None` branch, so the ordinary path is still the
single call the brief required. ⚠️ It is also reached by the ten-minute refresh loop, where it is
idempotent.

**2026-09-17 — `boot_status_mode` **off** sets `status=online` explicitly rather than leaving
the presence untouched.** `__init__` has already put `dnd` into `ConnectionState` by the time
`setup_hook` reads a stored `off`, so it has to be cleared rather than skipped. The result is an
IDENTIFY that carries `status: online, game: null` where today's carries no `presence` block at
all. Same rendering; not byte-identical.

**2026-09-17 — a blank sentence gives a red dot and no status line.** `text` keys already refuse
an empty value at `coerce_value` (only `TEXT_MAY_BE_BLANK` may be emptied, and these two are not
on it), so this branch is unreachable from either door today. It exists so a future blank cannot
crash a boot.

**2026-09-17 — `docs/access/sweeps.md` rows are lettered `BS-a`…`BS-c`, not numbered.** `main`
moved to **v133** while this branch was building and took sweep numbers **586–590**; numbering
here would collide. The letters are renumbered at the merge, as `MM-a`…`MM-n` → 572–585 were.

## What was NOT verified

⚠️ **Nothing in this build has met Discord.** No gateway session was opened, no IDENTIFY packet
was sent or captured, and **no member has seen a red dot, a green dot or either sentence.** The
whole proof is the test suite plus a read of the installed `discord.py` 2.7.1 source. Concretely
unverified:

- **That Discord renders `CustomActivity` beside a `dnd` status on a BOT account the way it does
  for a person.** This is the single assumption the feature rests on and the reason sweep `BS-a`
  exists.
- **The shutdown flip landing at all.** Whether Discord processes a presence update in the
  milliseconds between it being sent and the socket closing is unmeasured — the deviation above
  says the display is "at most the last second", and even that is inference.
- **Whether a Fly rolling deploy shows the red state long enough to be seen.** The new machine
  boots while the old one is still up, so the observable sequence during a real deploy is
  unknown. Sweep `BS-a` is what finds out.
- **The Settings page ▸ core rendering the three new rows in a browser.** The mock's contract
  check passed; no page was opened. Sweeps `BS-b` and `BS-c`.
- ⚠️ **One library gotcha found on the way**, filed where a debugger will look:
  [`gotchas.md`](gotchas.md) — *"`Client.activity` gives a different answer the second time you
  read it"*. It cost one confusing test failure here, and it has a production edge worth knowing
  before anyone adds a read of `bot.activity` before `connect()`.
