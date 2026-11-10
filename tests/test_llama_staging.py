import copy
import json
import sys
from pathlib import Path

import pytest

from scripts.worker import stage_llama


def pins():
    return json.loads(
        (Path(__file__).resolve().parents[1] / "scripts/worker/llama-qwen-pins.json").read_text(
            encoding="utf-8-sig"
        )
    )


def test_pinned_inventory_has_exact_sizes_and_immutable_urls():
    items = stage_llama.validate_pins(pins())
    assert len(items) == 4
    assert sum(item["bytes"] for item in items) == 6227545077
    assert sum(item["bytes"] for item in items if item["kind"] == "model") == 5444831360


@pytest.mark.parametrize(
    "field,value",
    [
        ("name", "../escape"),
        ("name", "bad\\file"),
        ("sha256", "invalid"),
        ("bytes", -1),
        ("bytes", 9000000000),
        ("url", "https://example.org/runtime"),
        ("kind", "executable"),
    ],
)
def test_bad_pin_rejected_before_download(field, value):
    source = pins()
    source["assets"][0][field] = value
    with pytest.raises(ValueError):
        stage_llama.validate_pins(source)


def test_missing_or_duplicate_artifacts_refused():
    source = pins()
    source["assets"].append(copy.deepcopy(source["assets"][0]))
    with pytest.raises(ValueError, match="unique"):
        stage_llama.validate_pins(source)
    source = pins()
    source["model_files"] = []
    with pytest.raises(ValueError, match="both required"):
        stage_llama.validate_pins(source)


def test_preview_does_not_create_directories_or_invoke_curl(tmp_path, monkeypatch, capsys):
    pinfile = tmp_path / "pins.json"
    pinfile.write_text(json.dumps(pins()))
    target = tmp_path / "absent"
    monkeypatch.setattr(
        sys, "argv", ["stage", "--pins", str(pinfile), "--root", str(target), "--dry-run"]
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("Preview attempted a subprocess")

    monkeypatch.setattr(stage_llama.subprocess, "run", forbidden)
    stage_llama.main()
    assert not target.exists()
    assert json.loads(capsys.readouterr().out)["status"] == "preview_no_network"
