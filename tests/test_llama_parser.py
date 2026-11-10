import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from src.storage import _encode
from src.workers.llama_parser import (
    LlamaConfig,
    PageSelections,
    candidates_from_selection,
    extractor_version,
    parse_page,
)
from src.workers.queue import ExtractionQueue, ExtractionResult
from src.workers.runner import worker_pass


def config(**kwargs):
    return LlamaConfig(model_alias="qwen-local", declared_model_sha256="a" * 64, **kwargs)


def words():
    return [
        {"text": text, "x0": i * 20, "x1": i * 20 + 15, "top": 10, "bottom": 20}
        for i, text in enumerate(["Ours", "PSNR", "32.15", "dB"])
    ]


def selection(**kwargs):
    return {
        "cells": [
            {
                "value": [2],
                "row_label": [0],
                "column_label": [1],
                "dataset": [],
                "split": [],
                "metric": [1],
                "unit": [3],
                **kwargs,
            }
        ]
    }


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://127.0.0.1:8080",
        "http://localhost:8080",
        "http://example.org:8080",
        "http://127.0.0.1:8080/path",
        "http://user@127.0.0.1:8080",
        "http://127.0.0.1:8080/?key=value",
        "http://127.0.0.1",
    ],
)
def test_endpoint_is_literal_loopback_only(endpoint):
    with pytest.raises(ValueError):
        config(endpoint=endpoint)


def test_config_and_prompt_are_bound_to_job_version():
    assert extractor_version(config()) == extractor_version(config())
    assert extractor_version(config()) != extractor_version(config(max_page_requests=2))
    changed = config().model_copy(update={"declared_model_sha256": "b" * 64})
    assert extractor_version(config()) != extractor_version(changed)


def test_candidates_copy_exact_words_coordinates_and_require_review():
    candidate = candidates_from_selection(PageSelections.model_validate(selection()), words(), 3)[0]
    assert candidate.raw_value == "32.15"
    assert candidate.bbox == (40, 10, 55, 20)
    assert candidate.page == 3 and candidate.unit == "dB" and candidate.metric == "PSNR"
    assert candidate.dataset is None and candidate.split is None
    assert candidate.review_required is True


@pytest.mark.parametrize(
    "updates",
    [
        {"value": [-1]},
        {"value": [999]},
        {"value": [2, 2]},
        {"value": [3, 2]},
        {"value": [0]},
        {"unit": [999]},
    ],
)
def test_invented_or_invalid_word_selection_rejected(updates):
    with pytest.raises(ValueError):
        candidates_from_selection(PageSelections.model_validate(selection(**updates)), words(), 1)


def test_llama_schema_request_and_response_contract():
    def respond(request):
        assert request.url.host == "127.0.0.1"
        body = json.loads(request.content)
        assert body["max_tokens"] == 2048 and body["stream"] is False
        assert body["chat_template_kwargs"] == {"enable_thinking": False}
        assert body["response_format"]["type"] == "json_schema"
        assert body["response_format"]["schema"] == PageSelections.model_json_schema()
        return httpx.Response(
            200,
            json={
                "model": "qwen-local",
                "choices": [
                    {"finish_reason": "stop", "message": {"content": json.dumps(selection())}}
                ],
            },
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        assert parse_page(client, config(), words(), 1)[0].raw_value == "32.15"


@pytest.mark.parametrize("model,finish", [("other", "stop"), ("qwen-local", "length")])
def test_model_mismatch_or_truncation_refused(model, finish):
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda req: httpx.Response(
                200,
                json={
                    "model": model,
                    "choices": [
                        {"finish_reason": finish, "message": {"content": json.dumps(selection())}}
                    ],
                },
            )
        )
    ) as client:
        with pytest.raises(ValueError):
            parse_page(client, config(), words(), 1)


def test_queue_routes_optional_parser_and_retains_fenced_result(tmp_path, monkeypatch):
    cfg = tmp_path / "llama.json"
    cfg.write_bytes(_encode(config().model_dump()))
    queue = ExtractionQueue(tmp_path / "queue")
    job = queue.enqueue("paper", "a" * 64, extractor_version(config()), "https://example.org/a.pdf")
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / ("a" * 64 + ".pdf")).write_bytes(b"%PDF-fixture")

    def child(command, **kwargs):
        assert command[2] == "src.workers.llama_parser"
        assert Path(command[-1]) == cfg.resolve()
        assert kwargs["timeout"] == job.limits.timeout_seconds
        leased = json.loads(kwargs["input"])
        result = ExtractionResult(
            job_key=job.key,
            paper_id=job.paper_id,
            pdf_sha256=job.pdf_sha256,
            extractor_version=job.extractor_version,
            completed_at=leased["updated_at"],
            page_count=1,
            candidates=candidates_from_selection(
                PageSelections.model_validate(selection()), words(), 1
            ),
        )
        kwargs["stdout"].write(_encode(result.model_dump(mode="json")))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("src.workers.runner.subprocess.run", child)
    assert worker_pass(queue, cache, llama_config=cfg) == {
        "claimed": 1,
        "review-required": 1,
        "failed": 0,
    }
    assert queue.load().jobs[job.key].state == "review-required"
    assert worker_pass(queue, cache, llama_config=cfg)["claimed"] == 0


def test_recorded_live_gemma_response_remains_grounded_and_unreviewed():
    raw = (Path(__file__).parent / "fixtures/llama/gemma-e4b-synthetic-response.json").read_bytes()
    cfg = config().model_copy(update={"model_alias": "gemma-e4b-qat-676c3507"})
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=raw))
    ) as client:
        candidates = parse_page(client, cfg, words(), 1)
    assert len(candidates) == 1 and candidates[0].raw_value == "32.15"
    assert candidates[0].bbox == (40, 10, 55, 20)
    assert candidates[0].unit is None and candidates[0].metric is None
    assert candidates[0].review_required is True


def test_thinking_configuration_changes_the_fenced_job_identity():
    assert extractor_version(config()) != extractor_version(config(enable_thinking=True))
