"""One approved bounded RadSplat diagnostic; no retries or persistent model daemon."""

import argparse
import hashlib
import json
import socket
import subprocess
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

UNIT = "papers-llama-table-pilot.service"
BASE = "http://127.0.0.1:8791"
PAYLOAD_SHA = "6cd23e8e42761c674cd2845abe6c1dc93ecc6dd7a1a61eda1607382e4c9e2673"


def command(*args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=25)
        return {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
    except subprocess.TimeoutExpired:
        return {"returncode": 124, "stdout": "", "stderr": "Bounded command timeout"}
    except OSError as error:
        return {"returncode": 127, "stdout": "", "stderr": type(error).__name__}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = args.request.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PAYLOAD_SHA or args.output.exists():
        raise ValueError("Payload differs or output already exists; do not repeat automatically")
    body = json.loads(raw)
    words = json.loads(body["messages"][1]["content"])["words"]
    if len(words) != 498 or body["max_tokens"] != 2048:
        raise ValueError("Unexpected approved request limits")
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 8791)) == 0:
            raise ValueError("Port already occupied; refuse to disturb another model service")
    started = time.monotonic()
    deadline = started + 32 * 60
    stamp = datetime.now(UTC).isoformat()
    receipt = {
        "started_at": stamp,
        "request_sha256": PAYLOAD_SHA,
        "unit": UNIT,
        "generation_requests": [],
        "gpu_samples": [],
        "status": "starting",
    }
    stop = threading.Event()

    def save():
        temporary = args.output.with_suffix(".tmp")
        temporary.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        temporary.replace(args.output)

    def sample():
        while not stop.is_set():
            receipt["gpu_samples"].append(
                {
                    "elapsed_seconds": time.monotonic() - started,
                    "sample": command(
                        "nvidia-smi",
                        "--query-gpu=memory.used,utilization.gpu",
                        "--format=csv,noheader,nounits",
                    ),
                }
            )
            stop.wait(2)

    thread = threading.Thread(target=sample, daemon=True)
    try:
        receipt["start"] = command("systemctl", "--user", "start", UNIT)
        if receipt["start"]["returncode"]:
            raise RuntimeError("Service startup failed")
        thread.start()
        with httpx.Client(trust_env=False, follow_redirects=False) as client:

            def request(method, path, payload=None, timeout=20):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("Overall client deadline")
                response = client.request(
                    method, BASE + path, json=payload, timeout=min(timeout, remaining)
                )
                response.raise_for_status()
                if len(response.content) > 2_000_000:
                    raise ValueError("Oversized local model response")
                return response.json()

            ready_by = time.monotonic() + 120
            while True:
                try:
                    receipt["health"] = request("GET", "/health", timeout=3)
                    break
                except (httpx.HTTPError, OSError):
                    if time.monotonic() >= ready_by:
                        raise TimeoutError("Model readiness deadline") from None
                    time.sleep(1)
            receipt["ready_elapsed_seconds"] = time.monotonic() - started
            receipt["models"] = request("GET", "/v1/models")
            if body["model"] not in [x["id"] for x in receipt["models"]["data"]]:
                raise ValueError("Unexpected model alias")
            receipt["slots"] = request("GET", "/slots")
            if len(receipt["slots"]) != 1 or receipt["slots"][0]["n_ctx"] != 16384:
                raise ValueError("Unexpected slot context")
            template = request(
                "POST",
                "/apply-template",
                {
                    "messages": body["messages"],
                    "chat_template_kwargs": body["chat_template_kwargs"],
                    "add_generation_prompt": True,
                },
            )
            receipt["applied_template"] = template
            tokens = request(
                "POST",
                "/tokenize",
                {"content": template["prompt"], "add_special": True, "parse_special": True},
            )
            receipt["tokenization"] = tokens
            count = len(tokens["tokens"])
            receipt["preflight_prompt_tokens"] = count
            if count + 2048 + 256 > 16384:
                raise ValueError("Prompt/output/safety allowance exceeds slot context")
            save()
            for repetition in range(2):
                if deadline - time.monotonic() < 30:
                    receipt["warm_repeat_omitted"] = "Client deadline admission"
                    break
                entry = {
                    "repetition": repetition + 1,
                    "started_elapsed_seconds": time.monotonic() - started,
                }
                receipt["generation_requests"].append(entry)
                save()
                t = time.monotonic()
                result = request("POST", "/v1/chat/completions", body, timeout=900)
                entry.update(wall_seconds=time.monotonic() - t, response=result)
                save()
                if result.get("model") != body["model"] or len(result.get("choices", [])) != 1:
                    raise ValueError("Unexpected generation model or choices")
                choice = result["choices"][0]
                if choice.get("finish_reason") != "stop":
                    raise ValueError("Incomplete generation; do not retry")
                cells = json.loads(choice["message"]["content"])["cells"]
                if not isinstance(cells, list) or len(cells) > 100:
                    raise ValueError("Invalid cell inventory")
                seen = set()
                fields = {
                    "value": 1,
                    "row_label": 30,
                    "column_label": 30,
                    "dataset": 20,
                    "split": 20,
                    "metric": 20,
                    "unit": 10,
                }
                for cell in cells:
                    if set(cell) != set(fields):
                        raise ValueError("Unexpected selection fields")
                    for name, maximum in fields.items():
                        indices = cell[name]
                        if (
                            not isinstance(indices, list)
                            or len(indices) > maximum
                            or any(type(i) is not int or not 0 <= i < len(words) for i in indices)
                            or indices != sorted(set(indices))
                        ):
                            raise ValueError("Invalid source-word indices")
                    if (
                        len(cell["value"]) != 1
                        or cell["value"][0] in seen
                        or not any(c.isdigit() for c in words[cell["value"][0]]["text"])
                    ):
                        raise ValueError("Invalid or duplicated numeric selection")
                    seen.add(cell["value"][0])
                entry["source_index_validation_passed"] = True
                save()
            receipt["status"] = "completed"
    except Exception as error:
        receipt["status"] = "failed_diagnostic"
        receipt["error"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        receipt["stop"] = command("systemctl", "--user", "stop", UNIT)
        stop.set()
        if thread.is_alive():
            thread.join(timeout=30)
        receipt["unit_after"] = command(
            "systemctl",
            "--user",
            "show",
            UNIT,
            "-p",
            "ActiveState",
            "-p",
            "SubState",
            "-p",
            "ExecMainStatus",
        )
        receipt["timer_after"] = command(
            "systemctl", "--user", "is-active", "papers-extraction.timer"
        )
        receipt["journal"] = command(
            "journalctl", "--user", "-u", UNIT, "--since", stamp, "--no-pager", "-o", "short-iso"
        )
        receipt["gpu_after"] = command(
            "nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"
        )
        with socket.socket() as probe:
            receipt["port_open_after"] = probe.connect_ex(("127.0.0.1", 8791)) == 0
        receipt["elapsed_seconds"] = time.monotonic() - started
        save()
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "generation_requests": len(receipt["generation_requests"]),
                "port_open_after": receipt["port_open_after"],
                "elapsed_seconds": receipt["elapsed_seconds"],
            }
        )
    )


if __name__ == "__main__":
    main()
