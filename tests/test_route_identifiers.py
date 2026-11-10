import json
import shutil
import subprocess
from pathlib import Path

import pytest

from src.identity import identifier_key


def test_browser_identifier_normalization_parity(tmp_path):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node required for browser identifier parity")
    values = [
        "HTTPS://DOI.ORG/10.1234/ABC%2Fpart",
        "doi: 10.1234/ABC",
        "10.1234/ABC",
        "https://arxiv.org/pdf/hep-th/9808009v2.pdf",
        "ARXIV:2308.04079v3",
        "https://export.arxiv.org/abs/2308.04079v2",
        "hep-th/9808009v2",
        "https://openalex.org/w123/",
        "OPENALEX:w123",
        "W123",
        "Special/Case:β",
        "constructor",
        "__proto__",
    ]
    helper = Path("docs/assets/route-identifiers.js").resolve()
    script = tmp_path / "check.cjs"
    script.write_text(
        "const {routeIdentifierKey,ownAlias}=require("
        + json.dumps(str(helper))
        + ");\n"
        + "const values="
        + json.dumps(values)
        + ";\n"
        + 'if(ownAlias({},"constructor")!=="constructor")throw new Error("Inherited alias");\n'
        + "process.stdout.write(JSON.stringify(values.map(routeIdentifierKey)));",
        encoding="utf-8",
    )
    actual = json.loads(subprocess.check_output([node, str(script)], text=True, encoding="utf-8"))
    assert actual == [identifier_key(value) for value in values]
