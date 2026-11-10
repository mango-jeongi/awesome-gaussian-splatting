"""Local queue generation, bounded execution, and strict result validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.workers.queue import ExtractionLimits, ExtractionQueue, ExtractionResult
from src.workers.runner import cache_pdf, worker_pass


def main(argv=None):
    parser = argparse.ArgumentParser(prog="papers-worker")
    sub = parser.add_subparsers(dest="command", required=True)
    enqueue = sub.add_parser("enqueue")
    enqueue.add_argument("--queue", type=Path, required=True)
    enqueue.add_argument("--cache", type=Path, required=True)
    enqueue.add_argument("--pdf", type=Path, required=True)
    enqueue.add_argument("--paper-id", required=True)
    enqueue.add_argument("--source-url", required=True)
    enqueue.add_argument("--max-pages", type=int, default=100)
    enqueue.add_argument("--max-bytes", type=int, default=50_000_000)
    enqueue.add_argument("--timeout", type=int, default=120)
    run = sub.add_parser("pass")
    run.add_argument("--queue", type=Path, required=True)
    run.add_argument("--cache", type=Path, required=True)
    run.add_argument("--max-jobs", type=int, default=1)
    validate = sub.add_parser("validate-result")
    validate.add_argument("result", type=Path)
    review_parser = sub.add_parser("review-import")
    review_parser.add_argument("--data", type=Path, required=True)
    review_parser.add_argument("--ledger", type=Path, required=True)
    review_parser.add_argument("--result", type=Path, required=True)
    review_parser.add_argument("--pdf", type=Path, required=True)
    review_parser.add_argument("--review", type=Path, required=True)
    review_parser.add_argument("--dry-run", action="store_true")
    coverage_parser = sub.add_parser("coverage")
    coverage_parser.add_argument("--data", type=Path, required=True)
    coverage_parser.add_argument(
        "--queue",
        type=Path,
        action="append",
        default=[],
        help="Existing queue directory containing queue.json; repeat for multiple queues",
    )
    coverage_parser.add_argument("--reviewed", type=Path)
    coverage_parser.add_argument("--local-sources", type=Path)
    coverage_parser.add_argument("--extractor-version", required=True)
    coverage_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "enqueue":
        from src.workers.pdf_parser import extractor_version

        limits = ExtractionLimits(
            max_pages=args.max_pages, max_bytes=args.max_bytes, timeout_seconds=args.timeout
        )
        digest = cache_pdf(args.pdf, args.cache, limits)
        job = ExtractionQueue(args.queue).enqueue(
            args.paper_id, digest, extractor_version(), args.source_url, limits=limits
        )
        print(json.dumps({"job_key": job.key, "state": job.state, "pdf_sha256": digest}))
    elif args.command == "pass":
        print(
            json.dumps(worker_pass(ExtractionQueue(args.queue), args.cache, max_jobs=args.max_jobs))
        )
    elif args.command == "coverage":
        from src.schema import PaperDatabase
        from src.workers.coverage import scan_coverage
        from src.workers.review import ReviewedExtractionStore

        for path in args.queue:
            if not path.is_dir() or not (path / "queue.json").is_file():
                parser.error(
                    f"--queue requires an existing queue directory containing queue.json: {path}"
                )
        reviewed = (
            ReviewedExtractionStore.model_validate_json(args.reviewed.read_bytes())
            if args.reviewed
            else None
        )
        local_sources = (
            json.loads(args.local_sources.read_text(encoding="utf-8"))
            if args.local_sources
            else None
        )
        coverage = scan_coverage(
            PaperDatabase.load(args.data),
            [ExtractionQueue(path) for path in args.queue],
            extractor_version=args.extractor_version,
            reviewed=reviewed,
            local_sources=local_sources,
        )
        coverage.save(args.output)
        print(
            json.dumps(
                {
                    "records": len(coverage.records),
                    "summary": coverage.summary,
                    "source_tasks": len(coverage.source_tasks),
                }
            )
        )
    elif args.command == "review-import":
        from src.workers.review import ExtractionReview, import_review

        review = ExtractionReview.model_validate_json(args.review.read_bytes())
        print(
            json.dumps(
                import_review(
                    data_path=args.data,
                    ledger_path=args.ledger,
                    result_path=args.result,
                    pdf_path=args.pdf,
                    review=review,
                    dry_run=args.dry_run,
                )
            )
        )
    else:
        result = ExtractionResult.model_validate_json(args.result.read_bytes())
        print(
            json.dumps(
                {
                    "job_key": result.job_key,
                    "page_count": result.page_count,
                    "candidates": len(result.candidates),
                    "review_required": True,
                }
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
