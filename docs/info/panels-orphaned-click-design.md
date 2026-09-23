# A click on a panel nobody holds any more — answered in words

> **Audience:** the build agent, reviewers, and whoever builds persistent panels next.
> **Status:** TRACKED · 🔨 BUILT on branch `panels-survive-restart` (off `main` `269338c3`), **not
> merged, not deployed**. **Last verified: 2026-09-22** against the installed **discord.py 2.7.1**
> source (`.venv/Lib/site-packages/discord/state.py`, `client.py`, `ui/view.py`, `message.py`,
> `interactions.py`) and the suite in the worktree. ⚠️ **Nothing here has met live Discord** — every
> claim about what Discord sends is read from the library, and every claim about ordering is proved
> against discord.py's own parser with a fake callback endpoint, not a gateway. ⚠️ Secret NAMES only.

## The defect it answers

[`KNOWN_ISSUES.md`](../KNOWN_ISSUES.md) ▸ **KI-20**. Every panel built on `black_bloc/panels.py` is an
ephemeral `discord.ui.View` with a real timeout. A restart (every deploy is one) drops the Python
object; the member's next press reaches a bot that has no handler for that `custom_id`, discord.py
drops it without a word, and Discord paints its own red *"This interaction failed"*. Since
`TEST_MODE` went off (2026-09-18 16:08) members meet this, not only staff.

This build is the universal, cheap half: **the click is answered in words**. It does NOT make the
panel survive — that is the later, per-feature persistent-view build KI-20 still waits on.

## The mechanism

| Step | Where | What |
|---|---|---|
| 1 | `bot.py` `BlackBlocBot.dispatch` | On `"interaction"` it calls `orphaned.mark(self, interaction)` **before** `super().dispatch`. |
| 2 | `orphaned.mark` | For a component or modal-submit interaction it repeats the view store's own lookups; if none owns the `custom_id` it sets `interaction.extras["black_bloc.orphaned"] = True`. Never raises. |
| 3 | `orphaned.on_interaction` (registered by `orphaned.install`, called first thing in `setup_hook`) | Marked and not yet answered → one **ephemeral** message, the `panel_expired_text` key with `{command}` filled, `allowed_mentions` none. Then one ROUTINE row `panel.expired_click`. |

**The words** are `panel_expired_text` (text, namespace `core`, in `CORE_KEYS`, help in `KEY_HELP`,
labelled on the site as *What a button on a panel that has gone quiet says*). Default:
*"This panel has gone quiet — it timed out, or Black Bloc restarted since it was opened, so its
buttons no longer reach anything. Run {command} again for a fresh one."* The default names BOTH
causes because the same orphan also happens when a panel's own timeout fired but the "gone quiet"
footer edit failed (KI-20's 15-minute case) — "the bot restarted" alone would sometimes be false.

**`{command}`** — `panels.py` builds no `custom_id`s: every `Panel` item takes discord.py's random
32-hex default, so the id carries no feature. The command comes instead from Discord's own record on
the message: the message a slash command's response created carries an `interaction` object whose
`name` is the command (`message.interaction.name`, e.g. `request`). When that is absent (a followup, or
a modal submitted with no message behind it) it says **"the command"**: *"Run the command again for a
fresh one."*

**The row** `panel.expired_click` (head `panel`, filed under `core` in `logkinds.HEADS`, listed in
`ROUTINE` so it reaches the Logs page but not `#blackbloc-logs` at the default level). Details:
`feature` (the command's head through `HEADS`, blank when unknown — `/voice` is blank because
tempvoice's head is `tempvoice`), `command` (`/request` or blank), `surface` (`component` / `modal`),
`custom_id` (the part before the first `:`, at most 40 characters — never anything a member typed).
Logged AFTER the answer: the 3-second window is the scarce thing.

## Why the mark is taken in `dispatch`, not in the listener — measured

`ConnectionState.parse_interaction_create` (state.py:814–831) calls
`ViewStore.dispatch_view` / `dispatch_modal` **synchronously**, which *creates* the owning view's
task, and only then calls `self.dispatch('interaction', …)`, which *creates* the listener's task.
The view's task therefore runs first. A view whose press calls `self.stop()` (or `retire(...)`)
before its first real await has **already removed itself from the store** when any
`on_interaction` listener runs, and its `interaction.response.is_done()` is still `False` while its
own HTTP call is in flight. A listener that looked the id up itself would call that click an
orphan and answer it a second time — a 400 for one of the two.

`BlackBlocBot.dispatch` runs synchronously inside the parser, after the store lookup and before any
task has started, so the store it reads is exactly the store `dispatch_view` just read.

**Proof** — `tests/test_orphaned.py::test_a_click_a_live_view_owns_is_answered_by_the_view_alone`
feeds an `INTERACTION_CREATE` payload through discord.py's real `parse_interaction_create` on a real
`BlackBlocBot`, with a live `View(timeout=None)` whose button stops the view and then answers, and a
fake callback endpoint that yields once the way a real POST does. It asserts exactly ONE response
(the view's) and no log row — and that the store no longer knows the id afterwards, which is the
race. **Measured 2026-09-22:** with the lookup moved into the listener (the naive version) the same
test FAILS with two responses (the view's and the sentence), as does the persistent-view test;
with the mark in `dispatch` all 18 pass. `test_a_click_nobody_owns_gets_the_sentence_ephemerally`
is the other half: an unknown id gets exactly one ephemeral response carrying the sentence.

## The discord.py internals relied on (2.7.1)

| Internal | Where | Used for |
|---|---|---|
| `parse_interaction_create` runs `dispatch_view`/`dispatch_modal` before `dispatch('interaction')`, both synchronously | `state.py:814–831` | the whole ordering argument |
| `ConnectionState(dispatch=self.dispatch, …)` binds the CLIENT's `dispatch` at construction | `client.py:369` | a subclass override is what the parser calls; patching the instance later would not be |
| `ViewStore._views[message_id or None][(component_type, custom_id)]`, `._modals[custom_id]`, `._dynamic_items` (compiled patterns, `fullmatch`) | `ui/view.py` `ViewStore` | `orphaned.is_owned` repeats `dispatch_view`'s three lookups in its order |
| `bot._connection._view_store` | `state.py:304` | reached through ONE helper, `orphaned.view_store` |
| `BaseView.is_finished()` — `_dispatch_item` drops a click on a finished view | `ui/view.py:622` | a finished view still in the store counts as an orphan |
| `Message._interaction` (`MessageInteraction.name`) | `message.py:2252` | `{command}`; the public `Message.interaction` is `@deprecated` since 2.4 and warns, so the private attribute is read |
| `Interaction.extras` | public | carries the mark from `dispatch` to the listener |

⚠️ **A discord.py upgrade must re-read these.** If `ViewStore` is restructured, `mark` catches the
exception and marks nothing — the failure mode is today's red "interaction failed", never a double
answer. If Discord stops sending the message's `interaction` object, `{command}` falls back to
"the command".

## Who else answers interactions — checked

`grep` over `black_bloc/` on 2026-09-22: no other `on_interaction` listener, no
`wait_for("interaction")`. Every component handler is a `View` item (in `_views`) or a
`DynamicItem` (in `_dynamic_items`, 17 templates across 9 cogs), and every modal is in `_modals`.
A dynamic template that MATCHES counts as owned even when its `from_custom_id` later declines —
that silence is the item's own, not this build's.

## What this build does NOT do

- **It does not edit the panel.** The orphaned click is an interaction ON the panel's message, so
  `response.edit_message` could technically disable its buttons — but a message can carry live
  `DynamicItem`s beside dead items, and rebuilding it from `interaction.message.components` to
  disable "everything" would kill live buttons on shared posts. One response is one choice; the
  sentence is the one that cannot break anything. (The brief's premise that an ephemeral panel
  cannot be edited from that click is not what the library says — noted, not relied on.)
- It does not change any `<feature>_panel_minutes` default (all still 10).
- It does not make any panel persistent — KI-20 stays open for that.

## Consequences a reviewer should see

- `core` in `/settings` grew from 25 to **26** keys, one over the group select's 25-cap, so the
  core group now draws **Find a setting** as `chat`, `events`, `golive` and `modmail` already do
  (`tests/test_settings_panel.py` updated to say so).
- `CORE_KEYS` is 25 (was 24) — the key-count tests in `tests/test_settings_store.py` and
  `site/mock/contract.json` changed; parallel builds that add a core key will conflict there.

## Not verified

- Nothing met live Discord: not the payload shape, not the `interaction` object on an ephemeral
  message, not the red banner going away. Sweep row `PX-a` in
  [`../access/sweeps.md`](../access/sweeps.md) is the live check.
- The mock/site were not rendered in a browser; `node site/mock/check.mjs` is the only site check.
