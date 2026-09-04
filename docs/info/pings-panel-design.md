# Ping roles — `/pings` is ONE command that opens a panel (wave 2)

> **Audience:** the build agent and the reviewer (Claude sessions), and the owner for §I.
> **Status:** TRACKED · ✅ **SHIPPED v72 `a5ad521` 2026-09-03 18:30** (merged clean after Fable
> review, one merge-time fix: the Names… echo only follows a successful save; boot measured `commands
> synced` **39**; 4050 tests; nothing run against Discord by eye — sweeps 126–134 and 38–42 are the
> owner's). Written as BUILT 2026-09-03 on `worktree-agent-a86e71fd801362ca2` — see the
> `## Deviations` foot for what was built differently and what was measured.
> **Last verified: 2026-09-03** — every `path:line` below was READ in this working tree on `main`
> (the tree whose newest commit is `1735ff8`, after the four wave-1 panels merged), in
> `black_bloc/pings.py`, `black_bloc/cogs/content/pings.py`, `black_bloc/panels.py`,
> `black_bloc/api/tools/pings.py`, `black_bloc/settings_store.py`, `black_bloc/command_visibility.py`,
> `black_bloc/logkinds.py`, `black_bloc/personas.py`, `black_bloc/cogs/community/requests.py`,
> `tests/test_bot.py`, `docs/access/sweeps.md`, `docs/access/OWNER_GUIDE.md`, `docs/info/code-notes.md`.
> Counted, not estimated: **12 leaf subcommands over 2 top-level slots**; `len(top) == 42`
> (`tests/test_bot.py:198`); `tests/cogs/content/test_pings.py` **27 tests**, `tests/test_pings.py`
> **36**, `tests/api/tools/test_pings.py` **16**; `docs/access/OWNER_GUIDE.md` has **zero** matches
> for "ping".
> ⚠️ **NOT verified: anything against Discord.** Nothing was run — no boot, no pytest, no ruff, no
> `check.mjs`, no panel opened. Whether the client submits an EMPTY `RoleSelect` at `min_values=0`
> is the same unproven edge [`events-panel-design.md`](events-panel-design.md) flags (its deviation 6
> built BOTH paths); §C names the same fallback. The `path:line` keys will drift as sibling wave-2
> branches merge — **trust the anchor text, not the number.**
>
> **Inherits every invariant in [`panels-program.md`](panels-program.md) §2 (P1–P17) and its §4
> library — none restated here.** Template: [`requests-panel-design.md`](requests-panel-design.md),
> whose `## Deviations

Written by the build agent, 2026-09-03, on `worktree-agent-a86e71fd801362ca2`.
Everything not listed here was built as this document says.

**Measured:** **4050 tests pass** (3872 on `main` before this branch, +178, none lost),
ruff clean over the whole tree, `node site/mock/check.mjs` **ok — 17 pages, 142 routes**
(unchanged, this build adds no route), `labels.js` parses, and the §H.3 import line —
including `cogs.content.golive` and `cogs.content.youtube` on purpose — succeeds.
`len(top)` measured through
`tests/test_bot.py::test_the_command_tree_stays_inside_discords_limits`: **40 before, 39
after**, exactly one, and the test now pins 39.
⚠️ **NOT verified: anything against Discord.** Nothing was booted, no panel was opened, no
role was moved. The empty-`RoleSelect` submit is still unproven (deviation 5).

1. **The button table is a composing function over a `PanelState` NamedTuple, not a
   `PANEL_BUTTONS` dict keyed by the state tuple.** §F asks for `PANEL_BUTTONS` keyed by
   the boolean tuple; a dict cannot express this state, because I2 makes the events half a
   *variable-length list* — one entry while the feeds agree, two once they split — and
   `followed`/`unfollowed` are counts, not booleans. `panel_buttons(state, *, staff)`
   composes from `PANEL_MOVES` exactly the way the landed `youtube.card_buttons` does, and
   the parametrised test (2 modes × 2 own-role × 2 creation × 2 streams × 4 events-states ×
   2 staff = **128 cases**) asserts the rendered labels equal what the function returns, so
   the table is still proved as data.

2. **`notification_lines` takes the FEEDS, not one `events_role_id`.** §F's signature is
   `notification_lines(guild, member, rows, events_role_id)`. I2 (b) means the panel can
   have two Events rows with different wear-states, which one id cannot describe, so the
   fourth argument is the `((feed, role_id), …)` tuple `events_feeds` returns. Each line is
   parametrised on `{what}` (`Go-live and event pings` / `Go-live pings` / `Event pings`),
   so the single-feed case reads exactly as it does today.

3. **A fourth events wear-state — `gone` — got its own LINE, not just a missing toggle.**
   §C's table says a gone role renders no toggle; it did not say what the embed says. A
   panel that silently drops a control is P9's problem in reverse, so `LIST_EVENTS_GONE`
   names the id and says it is not a role in this server any more. `notification_lines`
   therefore has four branches, not three.

4. **`save_settings` and one new log kind `pings.settings` were added** — not named in §F.
   The Settings sub-panel (§C) writes six keys and had no shared function to call, and
   letting each select call `store.set` directly would have meant a settings sub-panel that
   is the only surface in the feature with no action-log row. It validates every key with
   `coerce_value` BEFORE the first write (so a bad value refuses the whole dict rather than
   writing half), takes `via=` and builds its kind with `kind_via`, and `pings.settings`
   joins `logkinds.ROUTINE` beside `pings.setup`. One dict, one log row (checklist 34).

5. **Both empty-`RoleSelect` paths are built, as §C's fallback asks.** An empty submit
   clears the pick and re-renders the step saying *"Nothing picked, so a fresh role is
   made"*; the confirm button (`Set it up` / `Make the role`) does the identical write with
   `existing_role=None` whether or not anything was picked. ⚠️ Which of the two a real
   client uses is **still unverified** — sweeps row 132 says so out loud.

6. **`panels.site_page_url(origin, feature)` was added and FIVE copies now delegate to it**
   (§F/checklist 15). The brief allowed the consolidation because `panels.py` was free of
   sibling edits. §F says the copies are four; measured, there were **six** — the two
   wave-2 panels that landed while this design was being written added `golive.py:444` and
   `cogs/content/youtube.py:270`. `requests.py`, `events.py`, `applications.py`,
   `cogs/community/polls.py` and `golive.py` each keep a one-line delegate with their own
   feature key, so **every existing import and every existing test is unchanged** — which
   is the proof the consolidation changed nothing. ⚠️ **`cogs/content/youtube.py`'s copy
   was deliberately left**: it returns `""` rather than `None` and names its page with a
   private `SITE_PAGE` constant rather than `FEATURE_PAGES`, so folding it would be a
   behaviour change in a file that landed hours ago. Reported, not fixed.

7. **The `Names…` modal carries three fields, and the panel-minutes one is validated in
   the modal.** §C lists exactly those three. A modal has no `Range`, so a non-numeric
   minutes box is refused in words (`NOT_A_NUMBER`) and **nothing at all is saved** — the
   events-role name and the template do not sneak through on a bad third field. This is
   the youtube `NumbersModal` shape.

8. **The confirm step for `Take my ping role away` re-renders the ROOT embed with an
   "Are you sure?" field**, the way youtube's `open_confirm` does, rather than a card of
   its own; the staff card's `Remove their ping role` does the same over the card embed.
   §C only said "→ `Yes, take it away` / `Keep it`".

9. **`Refresh` and `Back` are ONE button each, dispatched on a `where` attribute the view
   carries.** §C lists `Refresh` on the root and on the Streamers sub-panel and `Back` on
   three different sub-panels; four spellings of one move is the anti-pattern P3 exists to
   kill, so `refresh_where` / `back_from` read `view.where` (`root` / `streamers` / `card`
   / `settings` / `role`) and go to the right place.

10. **`still_staff` runs on the staff READS too** — `Streamers…` and `Settings`, not only
    the writes. P8 says "before every staff move"; a demoted staffer being able to open the
    roster is the same defect one step earlier, and it costs one line each.

11. **Three assertions in `tests/cogs/content/test_pings.py` were rewritten in the
    extractions commit rather than the cog commit**, because the string rewrites (§E) land
    with the functions that own them and those three tests asserted the old wording
    (`/pingroles setup`, `/pingroles streamer add`). Every other test in that file was
    replaced wholesale when the cog was; `tests/api/tools/test_pings.py` is **untouched**,
    which is the proof no route moved.

12. **Two test doubles were repaired, not worked around.** `tests/cogs/content/test_pings.py`'s
    `FakeGuild.create_role` numbered roles `1000 + len(self.roles)`, so deleting a role and
    making another handed out the SAME id — which is exactly the *role deleted by hand, then
    repaired* case the `Make the role again` test exercises. It now uses a monotonic counter.
    `tests/test_pings.py`'s `FakeMember.add_roles` never appends to `role.members`, so a
    follower-count test has to append directly; left alone rather than changed, because
    thirty existing tests read that double.

13. **`docs/access/sweeps.md` rows are 126–134, not 104–114.** §H was written when the last
    written row was 102; `sweeps.md` ends at **125** (118–125 are the youtube panel's), so
    these start at 126 and the nine rows of §H's table became nine rows numbered 126–134.
    Rows **38–42** were rewritten in place as §E says. `docs/access/OWNER_GUIDE.md`'s count
    moved **125 → 134** in its header and its "Test something" row; measured, it still names
    no `/pings` subcommand anywhere (zero matches for "ping", as §E said).

14. **`black_bloc/pings.py:NOT_A_STREAMER` already said `/golive` → **Link my Twitch
    channel** on `main`** — the golive panel landed and rewrote it. §E's instruction to
    "say `/twitch link` and let the conductor reconcile" is therefore moot; only its
    `/pingroles streamer add` half needed rewriting, to `/pings` ▸ **Streamers…**.

15. **Checklist 15 caught one more duplicate during the sweep: the cog's own
    `LABEL_LIMIT = 100`.** `panels.SELECT_OPTION_LIMIT` is the same 100 and already has a
    home, so the constant was deleted and every select-option clamp reads the library's.
    `pings.ROLE_NAME_LIMIT` is left as a separate 100 on purpose — that one is Discord's
    role-NAME ceiling, a different fact that happens to share a number.

16. **Checklist 29, checked against the installed source rather than guessed:**
    `discord/ui/select.py`'s `RoleSelect` documents `min_values` as *"must be between 0 and
    25"* and does **not** validate it at construction, so `min_values=0` is accepted by the
    library. That settles the LIBRARY half of the empty-picker question; the CLIENT half —
    whether Discord's own UI will submit an empty selection — is still unproven and is why
    deviation 5's second path exists.

17. **The panel block was appended to the FOOT of `black_bloc/pings.py`**, after the
    existing shared layer, matching `black_bloc/youtube.py`'s shape rather than sitting
    between the string constants and `Outcome`. Nothing already in that file was renamed or
    re-homed (§J) — `api/tools/pings.py` imports it by name and its sixteen tests are
    unchanged.
