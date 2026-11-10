"""Single-executor arXiv connection gate with durable pacing and retry deadlines."""

from __future__ import annotations

import json
import math
import os
import time
from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path

from src.file_lock import exclusive_file
from src.storage import _atomic_write, _encode


class ArxivRateDeferred(RuntimeError):
    def __init__(self, seconds: float):
        self.retry_after = seconds
        self.attempts = 0
        super().__init__(f"arXiv executor deferred for at least {math.ceil(seconds)} seconds")


def default_gate_path() -> Path:
    configured = os.environ.get("PAPERS_ARXIV_GATE")
    if configured:
        return Path(configured)
    base = Path(
        os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache"
    )
    return base / "papers-pipeline" / "arxiv-rate.json"


class ArxivRateGate:
    """Share one SSD-backed gate across all API processes on the designated executor.

    Hold it until the HTTP connection is closed. Independent gates on different
    machines are not a distributed limiter; other workers must use this executor.
    """

    def __init__(
        self,
        path: str | Path | None = None,
        *,
        interval: float = 3.0,
        clock: Callable[[], float] = time.time,
        sleep: Callable[[float], None] = time.sleep,
        lock_timeout: float = 120.0,
    ):
        if not math.isfinite(interval) or interval < 3:
            raise ValueError("arXiv request interval must be at least three seconds")
        if lock_timeout <= 0 or not math.isfinite(lock_timeout):
            raise ValueError("Invalid gate lock timeout")
        self.path = Path(path) if path is not None else default_gate_path()
        self.interval, self.clock, self.sleep = interval, clock, sleep
        self.lock_timeout = lock_timeout

    @contextmanager
    def _exclusive(self):
        with exclusive_file(
            self.path.with_suffix(self.path.suffix + ".lock"),
            self.lock_timeout,
            resource="arXiv API request",
        ):
            yield

    def _state(self) -> dict:
        if not self.path.exists():
            return {}
        state = json.loads(self.path.read_bytes())
        if not isinstance(state, dict) or set(state) - {"last_finished_at", "next_allowed_at"}:
            raise ValueError("Invalid arXiv rate state")
        for value in state.values():
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError("Invalid arXiv rate timestamp")
        return state

    def defer(self, seconds: float) -> None:
        if not math.isfinite(seconds) or seconds < 0:
            raise ValueError("Invalid arXiv retry delay")
        with self._exclusive():
            state = self._state()
            state["next_allowed_at"] = max(state.get("next_allowed_at", 0), self.clock() + seconds)
            _atomic_write(self.path, _encode(state))

    @contextmanager
    def connection(self):
        with self._exclusive():
            state = self._state()
            due = max(
                state.get("last_finished_at", -self.interval) + self.interval,
                state.get("next_allowed_at", 0),
            )
            delay = due - self.clock()
            if delay > 60:
                raise ArxivRateDeferred(delay)
            if delay > 0:
                self.sleep(delay)
            state["last_finished_at"] = self.clock()
            _atomic_write(self.path, _encode(state))
            try:
                yield
            finally:
                state["last_finished_at"] = self.clock()
                _atomic_write(self.path, _encode(state))
