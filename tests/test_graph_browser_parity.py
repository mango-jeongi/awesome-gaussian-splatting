import json
import shutil
import subprocess
from pathlib import Path

import pytest

from src.graph import bounded_graph, graph_projection
from src.public import build_public
from src.schema import PaperDatabase, PaperRecord


@pytest.mark.parametrize("dense", [False, True])
def test_browser_python_projection_parity(tmp_path, dense):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for browser/Python graph parity; CI checks availability")
    ids = [f"p{index:04d}" for index in range(170 if dense else 340)]
    ids[-2:] = ['special/quote:"Unicode', "special/colon:β"]
    papers = []
    for index, key in enumerate(ids):
        refs = [other for other in ids if other != key] if dense else ([ids[0]] if index else [])
        papers.append(
            PaperRecord(
                id=key,
                title=f"Paper {index}",
                db_references=refs,
                db_citation_count=999 if index == 2 else 0,
                citation_count=index % 4,
                categories=["even" if index % 2 == 0 else "odd"],
            )
        )
    db = PaperDatabase(papers=papers, total_count=len(papers))
    manifest = build_public(db, tmp_path / "public")
    graph = graph_projection(db)
    index = json.loads((tmp_path / "public" / manifest["graph"]["index"]["path"]).read_bytes())
    assert index["nodes"][ids[0]]["incoming_count"] != db.papers[0].db_citation_count
    records = {
        key: {"id": key, "node": graph["nodes"][key], **row}
        for key, row in graph["adjacency"].items()
    }
    scenarios = [
        {},
        {"center": ids[0]},
        {"center": ids[0], "hops": 2},
        {"category": "odd"},
        {"category": "missing"},
        {"center": ids[0], "hops": 2, "category": "odd"},
    ]
    source = tmp_path / "input.json"
    source.write_text(
        json.dumps({"index": index, "records": records, "scenarios": scenarios}), encoding="utf-8"
    )
    script = tmp_path / "check.cjs"
    projector = Path("docs/assets/graph-projector.js").resolve()
    script.write_text(
        "const {projectCitationGraph}=require("
        + json.dumps(str(projector))
        + ");\n"
        + """const data=JSON.parse(require('fs').readFileSync(process.argv[2],'utf8'));
(async()=>{const result=[];for(const scenario of data.scenarios)result.push(await projectCitationGraph({index:data.index,record:async id=>data.records[id],...scenario}));process.stdout.write(JSON.stringify(result));})().catch(error=>{console.error(error);process.exit(1)});
""",
        encoding="utf-8",
    )
    actual = json.loads(
        subprocess.check_output([node, str(script), str(source)], text=True, encoding="utf-8")
    )
    for scenario, result in zip(scenarios, actual, strict=True):
        expected = bounded_graph(graph, **scenario)
        for field in ("nodes", "edges", "omitted_nodes", "omitted_edges", "node_cap", "edge_cap"):
            assert result[field] == expected[field], (scenario, field)
