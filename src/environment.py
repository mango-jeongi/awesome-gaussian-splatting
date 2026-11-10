"""Read local credentials literally; process environment always takes precedence."""

from __future__ import annotations

import json
import os
import re
from collections.abc import MutableMapping
from pathlib import Path


def load_local_environment(root: Path, environ: MutableMapping[str, str] | None = None) -> None:
    target = os.environ if environ is None else environ
    parsed: dict[str, str] = {}
    for name in (".env", ".env.local"):
        path = root / name
        if not path.exists():
            continue
        for number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            key, sep, value = line.partition("=")
            key, value = key.strip(), value.strip()
            if not sep or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
                raise ValueError(f"Invalid local environment entry at {name}:{number}")
            try:
                if value.startswith('"'):
                    value = json.loads(value)
                    if not isinstance(value, str):
                        raise ValueError
                elif value.startswith("'"):
                    if len(value) < 2 or not value.endswith("'"):
                        raise ValueError
                    value = value[1:-1]
                if "\n" in value or "\r" in value or "\x00" in value:
                    raise ValueError
            except (ValueError, TypeError):
                raise ValueError(f"Invalid local environment value at {name}:{number}") from None
            parsed[key] = value
    for key, value in parsed.items():
        target.setdefault(key, value)
