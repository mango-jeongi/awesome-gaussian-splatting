"""HF observations: provider evidence never silently replaces reviewed canonical fields."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from src.extractors.huggingface_client import HFFailure, HFPapersClient
from src.file_lock import exclusive_file
from src.identity import normalize_arxiv
from src.observations import SignalStore, refresh_order


def hf_ttl(observation, now):
    if observation and observation.status == "not_found":
        return timedelta(days=7)
    stamp = observation.values.get("submitted_on_daily_at") if observation else None
    if stamp:
        parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        if timedelta(0) <= now - parsed <= timedelta(days=30):
            return timedelta(days=1)
    return timedelta(days=7)


def refresh_huggingface(
    papers, path: Path, client: HFPapersClient, *, limit=50, cache_only=False, now=None
):
    now = now or datetime.now(UTC)
    if now.utcoffset() is None or limit < 0:
        raise ValueError("HF refresh requires aware time and nonnegative limit")
    with exclusive_file(str(path) + ".run.lock", resource="HF refresh"):
        store = SignalStore.load(path, "huggingface")
        due = [
            paper
            for paper in papers
            if paper.id not in store.observations
            or store.observations[paper.id].due(now, hf_ttl(store.observations.get(paper.id), now))
            or (
                store.observations[paper.id].status == "ok"
                and store.observations[paper.id].response_schema_version != "hf-paper-v2"
                and (
                    store.observations[paper.id].next_retry_at is None
                    or store.observations[paper.id].next_retry_at <= now
                )
            )
        ]
        due = refresh_order(due, store.observations)
        report = {
            "due": len(due),
            "attempted": 0,
            "ok": 0,
            "not_found": 0,
            "ambiguous": 0,
            "error": 0,
            "rate_limited": 0,
            "requests": 0,
        }
        if cache_only:
            return report
        initial = client.requests
        for paper in due[:limit]:
            if not paper.arxiv_id:
                store.apply(paper.id, status="ambiguous", now=now, retry_after=timedelta(days=7))
                report["ambiguous"] += 1
                report["attempted"] += 1
                store.save(path)
                continue
            try:
                work = client.paper(paper.arxiv_id)
            except HFFailure as failure:
                if failure.reason == "run_budget":
                    break
                status = (
                    "rate_limited"
                    if failure.reason in ("rate_limited", "retry_deadline")
                    else "ambiguous"
                    if failure.reason == "identity_mismatch"
                    else "error"
                )
                store.apply(
                    paper.id,
                    status=status,
                    now=now,
                    retry_after=timedelta(seconds=max(3600, failure.retry_after or 0)),
                )
                report[status] += 1
                report["attempted"] += 1
                store.save(path)
                if client.stopped or status == "rate_limited":
                    break
                continue
            if work is None:
                store.apply(paper.id, status="not_found", now=now, retry_after=timedelta(days=7))
                status = "not_found"
            else:
                url = "https://huggingface.co/papers/" + normalize_arxiv(work.id)
                values = {
                    "source_url": url,
                    "repository_evidence": {"url": work.githubRepo, "ownership": "unverified"}
                    if work.githubRepo
                    else None,
                    "project_page_evidence": work.projectPage,
                    "submitted_on_daily_at": work.submittedOnDailyAt,
                    "provider_summary": {
                        "text": work.summary,
                        "provider": "huggingface",
                        "source_url": url,
                    }
                    if work.summary
                    else None,
                }
                values["provider_ai_summary"] = (
                    {"text": work.ai_summary, "provider": "huggingface", "source_url": url}
                    if work.ai_summary
                    else None
                )
                values["linked_spaces"] = (
                    [
                        {
                            "id": space.id,
                            "url": "https://huggingface.co/spaces/" + space.id,
                            "relationship": "provider_linked_not_verified_official",
                        }
                        for space in work.linkedSpaces
                    ]
                    if work.linkedSpaces is not None
                    else None
                )
                values["linked_spaces_total"] = work.numTotalSpaces
                values["linked_spaces_complete"] = (
                    (len(work.linkedSpaces) == work.numTotalSpaces)
                    if work.linkedSpaces is not None and work.numTotalSpaces is not None
                    else None
                )
                for field, value in [("upvotes", work.upvotes), ("stars", work.githubStars)]:
                    if value is not None:
                        values[field] = value
                store.apply(
                    paper.id,
                    status="ok",
                    now=now,
                    provider_id=work.id,
                    values=values,
                    response_schema_version="hf-paper-v2",
                )
                status = "ok"
            report[status] += 1
            report["attempted"] += 1
            store.save(path)
        report["requests"] = client.requests - initial
        return report
