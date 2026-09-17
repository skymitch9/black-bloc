from __future__ import annotations

import ast
import asyncio
import pathlib

import pytest
from discord.ext import tasks

from black_bloc.loops import wait_ready

ROOT = pathlib.Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "black_bloc"
BEFORE_LOOPS = 17


class FakeReady:
    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.waits = 0

    async def wait_until_ready(self) -> None:
        self.waits += 1
        if self.waits <= self.failures:
            raise RuntimeError("the gateway never came up")


class FakeCog:
    def __init__(self, bot: FakeReady) -> None:
        self.bot = bot
        self.last_error: str | None = None
        self.ran = 0
        self.body_ran = asyncio.Event()

    @tasks.loop(seconds=0.01)
    async def work(self) -> None:
        self.ran += 1
        self.body_ran.set()

    @work.before_loop
    async def _before_work(self) -> None:
        await wait_ready(self.bot, self._work_broke)

    @work.error
    async def _work_broke(self, exc: BaseException) -> None:
        self.last_error = f"{type(exc).__name__}: {exc}"
        self.work.restart()


async def test_a_before_loop_failure_is_recorded_and_the_real_loop_restarts_and_runs():
    """The whole of KI-24, exercised against a real `tasks.Loop`, not a stand-in."""
    bot = FakeReady(failures=1)
    cog = FakeCog(bot)

    cog.work.start()
    try:
        await asyncio.wait_for(cog.body_ran.wait(), timeout=5)
    finally:
        cog.work.cancel()

    assert cog.last_error == "RuntimeError: the gateway never came up"
    assert bot.waits == 2
    assert cog.ran >= 1


async def test_a_before_loop_that_is_fine_leaves_no_error_and_waits_once():
    bot = FakeReady(failures=0)
    cog = FakeCog(bot)

    cog.work.start()
    try:
        await asyncio.wait_for(cog.body_ran.wait(), timeout=5)
    finally:
        cog.work.cancel()

    assert cog.last_error is None
    assert bot.waits == 1


async def test_wait_ready_says_whether_the_gateway_came_up():
    seen: list[BaseException] = []

    async def failed(exc: BaseException) -> None:
        seen.append(exc)

    class Fine:
        async def wait_until_ready(self) -> None:
            return None

    class Broken:
        async def wait_until_ready(self) -> None:
            raise RuntimeError("nope")

    assert await wait_ready(Fine(), failed) is True
    assert seen == []
    assert await wait_ready(Broken(), failed) is False
    assert [type(one).__name__ for one in seen] == ["RuntimeError"]


async def test_a_cancelled_wait_is_re_raised_untouched_and_never_reaches_the_handler():
    """A loop being cancelled is not a loop that failed; `cancel()` must not record an error."""
    seen: list[BaseException] = []

    async def failed(exc: BaseException) -> None:
        seen.append(exc)

    class Cancelling:
        async def wait_until_ready(self) -> None:
            raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        await wait_ready(Cancelling(), failed)
    assert seen == []


def _before_loop_methods() -> list[tuple[str, ast.AsyncFunctionDef]]:
    found: list[tuple[str, ast.AsyncFunctionDef]] = []
    for path in sorted(PACKAGE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.AsyncFunctionDef):
                continue
            heads = [
                one.attr for one in node.decorator_list if isinstance(one, ast.Attribute)
            ]
            if "before_loop" in heads:
                found.append((f"{path.relative_to(ROOT).as_posix()}:{node.name}", node))
    return found


def _calls(node: ast.AST) -> set[str]:
    names = set()
    for inner in ast.walk(node):
        if not isinstance(inner, ast.Call):
            continue
        func = inner.func
        names.add(func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", ""))
    return names


def test_every_before_loop_in_the_package_goes_through_the_one_helper():
    """KI-24: one guard, fifteen callers — a new loop that hand-rolls its own wait is the bug."""
    methods = _before_loop_methods()

    assert len(methods) == BEFORE_LOOPS, [where for where, _ in methods]
    missing = [where for where, node in methods if "wait_ready" not in _calls(node)]
    assert not missing, f"these `before_loop`s do not call `loops.wait_ready`: {missing}"


def test_no_before_loop_waits_on_the_gateway_by_itself():
    """No second copy of the try/except: only `loops.py` names `wait_until_ready` at all."""
    direct = [
        where for where, node in _before_loop_methods() if "wait_until_ready" in _calls(node)
    ]

    assert not direct, f"these `before_loop`s call `wait_until_ready` directly: {direct}"
    callers = [
        path.relative_to(ROOT).as_posix()
        for path in sorted(PACKAGE.rglob("*.py"))
        if "wait_until_ready" in path.read_text(encoding="utf-8")
    ]
    assert callers == ["black_bloc/loops.py"]
