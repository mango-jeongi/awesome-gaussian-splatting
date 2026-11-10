"""Cross-process advisory locks shared by cooperative local pipeline writers."""

from __future__ import annotations

import math
import os
import time
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def exclusive_file(
    path: str | Path, timeout: float = 120.0, *, resource: str = "pipeline operation"
):
    if timeout <= 0 or not math.isfinite(timeout):
        raise ValueError("Invalid file lock timeout")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a+b") as lock:
        lock.seek(0, os.SEEK_END)
        if lock.tell() == 0:
            lock.write(b"0")
            lock.flush()
        started = time.monotonic()
        while True:
            lock.seek(0)
            try:
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() - started >= timeout:
                    raise TimeoutError(f"Another {resource} holds the file lock") from None
                time.sleep(0.05)
        try:
            yield
        finally:
            lock.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
