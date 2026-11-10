import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src import deep_research as research
from src.schema import PaperDatabase


def docs():
    return [
        {
            "paper_id": "a",
            "pages": ["A Gaussian model improves rendering.", "Second page."],
            "title": "Example",
            "pdf": b"%PDF-example",
        }
    ]


def draft(**evidence):
    return {
        "claims": [
            {
                "statement": "Authors report a rendering improvement.",
                "kind": "reported",
                "evidence": [{"paper_id": "a", "page": 1, "quote": "Gaussian model", **evidence}],
            }
        ],
        "coverage_gaps": [],
        "limitations": ["Single paper; protocol comparison is unavailable."],
    }


def fake_client(payload=None, tokens=100, finish="STOP"):
    models = SimpleNamespace(
        count_tokens=Mock(return_value=SimpleNamespace(total_tokens=tokens)),
        generate_content=Mock(
            return_value=SimpleNamespace(
                text=json.dumps(payload or draft()),
                candidates=[SimpleNamespace(finish_reason=finish)],
                usage_metadata=None,
            )
        ),
    )
    return SimpleNamespace(models=models)


@pytest.mark.parametrize(
    "evidence",
    [
        {"paper_id": "invented"},
        {"page": 3},
        {"quote": "invented number 99.9"},
        {"quote": " "},
        {"quote": "word " * 26},
    ],
)
def test_unsupported_evidence_rejected(evidence):
    with pytest.raises(ValueError):
        research.validate_evidence(research.Synthesis.model_validate(draft(**evidence)), docs())


def test_generation_is_budgeted_and_grounded():
    pytest.importorskip("google.genai")
    client = fake_client()
    result, usage = research.synthesize(client, docs(), model="fixture", question="Compare")
    assert result.claims[0].evidence[0].paper_id == "a"
    assert usage["admitted_input_tokens_with_reserve"] == 1124
    assert client.models.generate_content.call_count == 1
    config = client.models.generate_content.call_args.kwargs["config"]
    assert config.response_schema is research.Synthesis
    assert config.max_output_tokens == 8192


@pytest.mark.parametrize("tokens", [None, -1, 200000])
def test_budget_failure_prevents_generation(tokens):
    pytest.importorskip("google.genai")
    client = fake_client(tokens=tokens)
    with pytest.raises(ValueError):
        research.synthesize(client, docs(), model="fixture", question="Compare")
    client.models.generate_content.assert_not_called()


@pytest.mark.parametrize("finish", ["MAX_TOKENS", "SAFETY", None])
def test_incomplete_generation_refused(finish):
    pytest.importorskip("google.genai")
    with pytest.raises(ValueError):
        research.synthesize(fake_client(finish=finish), docs(), model="fixture", question="Compare")


def test_dryrun_no_provider_and_no_source_text_in_receipt(tmp_path, monkeypatch):
    source = tmp_path / "catalog.json"
    PaperDatabase().save(source)
    output = tmp_path / "draft.json"
    monkeypatch.setattr(research, "prepare", lambda *a: docs())
    monkeypatch.setattr(research, "load_local_environment", Mock(side_effect=AssertionError))
    assert (
        research.main(
            [
                "--data",
                str(source),
                "--paper",
                "a=fake.pdf",
                "--question",
                "Compare",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    receipt = json.loads(output.read_text())
    assert receipt["status"] == "prepared_no_network"
    assert receipt["review_status"] == "unreviewed"
    assert "pdf" not in receipt["sources"][0] and "pages" not in receipt["sources"][0]
    assert "synthesis" not in receipt
    # A rerun cannot clobber an existing draft.
    with pytest.raises(SystemExit):
        research.main(
            [
                "--data",
                str(source),
                "--paper",
                "a=fake.pdf",
                "--question",
                "Compare",
                "--output",
                str(output),
            ]
        )


def test_secret_provider_error_is_not_printed_or_accepted(tmp_path, monkeypatch, capsys):
    pytest.importorskip("google.genai")
    from google import genai

    source = tmp_path / "catalog.json"
    PaperDatabase().save(source)
    output = tmp_path / "draft.json"
    monkeypatch.setattr(research, "prepare", lambda *a: docs())
    monkeypatch.setattr(research, "load_local_environment", lambda *a: None)
    monkeypatch.setenv("GEMINI_API_KEY", "SECRET_FIXTURE")
    monkeypatch.setattr(genai, "Client", Mock(side_effect=RuntimeError("SECRET_FIXTURE")))
    assert (
        research.main(
            [
                "--data",
                str(source),
                "--paper",
                "a=fake.pdf",
                "--question",
                "Compare",
                "--output",
                str(output),
                "--execute",
            ]
        )
        == 1
    )
    assert not output.exists()
    assert "SECRET_FIXTURE" not in capsys.readouterr().out


def test_pdf_limits_checked_before_parser(tmp_path):
    db = PaperDatabase.model_validate(
        {"papers": [{"id": "a", "title": "Example paper"}], "total_count": 1}
    )
    source = tmp_path / "fake.pdf"
    source.write_bytes(b"%PDF-fixture")
    with pytest.raises(ValueError, match="byte budget"):
        research.prepare(db, {"a": source}, max_bytes=2)
    with pytest.raises(ValueError, match="not active"):
        research.prepare(db, {"unknown": source})


def test_source_coverage_cannot_silently_drop_selected_papers():
    documents = docs() + [{"paper_id": "b", "pages": ["Other text."]}]
    payload = draft()
    with pytest.raises(ValueError, match="coverage"):
        research.validate_evidence(research.Synthesis.model_validate(payload), documents)
    payload["coverage_gaps"] = [{"paper_id": "b", "reason": "No supported comparative evidence"}]
    research.validate_evidence(research.Synthesis.model_validate(payload), documents)
    payload["coverage_gaps"].append({"paper_id": "invented", "reason": "Missing"})
    with pytest.raises(ValueError, match="coverage"):
        research.validate_evidence(research.Synthesis.model_validate(payload), documents)


def test_quote_must_be_on_the_claimed_physical_page():
    with pytest.raises(ValueError, match="source page"):
        research.validate_evidence(research.Synthesis.model_validate(draft(page=2)), docs())


def test_real_sdk_serialization_against_offline_transport():
    pytest.importorskip("google.genai")
    import httpx2
    from google import genai
    from google.genai import types

    requests = []

    def respond(request):
        requests.append(json.loads(request.content))
        if request.url.path.endswith(":countTokens"):
            return httpx2.Response(200, json={"totalTokens": 100})
        assert request.url.path.endswith(":generateContent")
        return httpx2.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {"parts": [{"text": json.dumps(draft())}], "role": "model"},
                        "finishReason": "STOP",
                    }
                ],
                "usageMetadata": {
                    "promptTokenCount": 100,
                    "candidatesTokenCount": 50,
                    "totalTokenCount": 150,
                },
            },
        )

    transport = httpx2.MockTransport(respond)
    with genai.Client(
        api_key="offline-fixture",
        http_options=types.HttpOptions(
            httpx_client=httpx2.Client(transport=transport),
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    ) as client:
        result, usage = research.synthesize(
            client, docs(), model="gemini-2.5-flash", question="Compare"
        )
    assert len(requests) == 2
    assert result.claims[0].kind == "reported"
    assert usage["usage"]["total_token_count"] == 150
    body = requests[-1]
    assert body["generationConfig"]["responseMimeType"] == "application/json"
    assert body["generationConfig"]["maxOutputTokens"] == 8192
    assert any(
        part.get("inlineData", {}).get("mimeType", part.get("inlineData", {}).get("mime_type"))
        == "application/pdf"
        for content in body["contents"]
        for part in content["parts"]
    )
    assert "systemInstruction" in body
