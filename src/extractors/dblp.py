"""Bounded DBLP publication paging; non-JSON/challenge responses are unresolved."""

from __future__ import annotations

import json
import re
import time

import httpx


class DBLPFailure(RuntimeError):
    pass


def parse_page(payload, first):
    try:
        hits = payload["result"]["hits"]

        def count(key):
            value = hits[key]
            if (
                not isinstance(value, (str, int))
                or isinstance(value, bool)
                or not re.fullmatch(r"\d+", str(value))
            ):
                raise ValueError
            return int(value)

        total, sent, start = count("@total"), count("@sent"), count("@first")
        rows = hits.get("hit", [])
        if isinstance(rows, dict):
            rows = [rows]
        if (
            not isinstance(rows, list)
            or sent != len(rows)
            or start != first
            or start + sent > total
        ):
            raise ValueError
        if any(
            not isinstance(row, dict)
            or not isinstance(row.get("info"), dict)
            or not isinstance(row["info"].get("key"), str)
            or not row["info"]["key"].strip()
            for row in rows
        ):
            raise ValueError
        return total, [row["info"] for row in rows]
    except (ValueError, KeyError, TypeError):
        raise DBLPFailure("Invalid DBLP page contract") from None


class DBLPClient:
    def __init__(self, *, max_requests=10, transport=None, sleep=time.sleep, clock=time.monotonic):
        if max_requests < 0:
            raise ValueError("Invalid DBLP budget")
        self.http = httpx.Client(timeout=20, transport=transport, follow_redirects=False)
        self.max_requests, self.requests = max_requests, 0
        self.sleep, self.clock = sleep, clock
        self.next_request = clock()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.http.close()

    def search(self, query, *, page_size=100, max_seconds=120, max_response_bytes=2_000_000):
        if not query.strip() or not 1 <= page_size <= 1000:
            raise ValueError("Invalid DBLP query/page size")
        if not 0 < max_seconds <= 1800 or not 1 <= max_response_bytes <= 20_000_000:
            raise ValueError("Invalid DBLP time/response budget")
        started = self.clock()
        first = 0
        expected = None
        seen = set()
        records = []
        while True:
            if self.requests >= self.max_requests:
                raise DBLPFailure("DBLP request budget exhausted; query unresolved")
            delay = max(0, self.next_request - self.clock())
            if self.clock() - started + delay >= max_seconds:
                raise DBLPFailure("DBLP time budget exhausted; query unresolved")
            if delay:
                self.sleep(delay)
            self.requests += 1
            try:
                with self.http.stream(
                    "GET",
                    "https://dblp.org/search/publ/api",
                    params={"q": query, "format": "json", "h": page_size, "f": first, "c": 0},
                ) as response:
                    if response.status_code != 200:
                        raise DBLPFailure(f"DBLP deferred HTTP {response.status_code}")
                    raw = bytearray()
                    for chunk in response.iter_bytes():
                        raw.extend(chunk)
                        if len(raw) > max_response_bytes:
                            raise DBLPFailure("DBLP response byte budget exceeded")
                        if self.clock() - started >= max_seconds:
                            raise DBLPFailure("DBLP time budget exhausted; query unresolved")
            except httpx.HTTPError:
                raise DBLPFailure("DBLP transport failure") from None
            finally:
                self.next_request = self.clock() + 1
            try:
                payload = json.loads(raw)
            except (ValueError, UnicodeError):
                raise DBLPFailure("DBLP non-JSON response") from None
            total, rows = parse_page(payload, first)
            if len(rows) > page_size:
                raise DBLPFailure("DBLP response exceeds requested page size")
            if expected is not None and total != expected:
                raise DBLPFailure("DBLP source count drift")
            expected = total
            for row in rows:
                if row["key"] in seen:
                    raise DBLPFailure("Repeated DBLP result")
                seen.add(row["key"])
                records.append(row)
            if len(records) == total:
                return records
            if len(rows) != page_size:
                raise DBLPFailure("Short DBLP page before source total")
            first += len(rows)
