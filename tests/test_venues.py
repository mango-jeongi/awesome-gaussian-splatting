from pathlib import Path

import httpx
import pytest
import yaml

from src.extractors.dblp import DBLPClient, DBLPFailure
from src.extractors.openalex import OpenAlexWork
from src.extractors.venues import publication_locations
from src.schema import PaperRecord


def test_requested_inventory_tracks_are_separate():
    inventory = yaml.safe_load(Path("config/sources.yaml").read_text())["editions"]
    keys = {(row["venue"], row["year"], row["track"]) for row in inventory}
    assert len(keys) == len(inventory) == 56
    assert ("CVPR", 2020, "main") in keys and ("CVPR", 2026, "workshop") in keys
    assert ("ICCV", 2020, "main") not in keys and ("ICCV", 2025, "main") in keys
    assert ("ECCV", 2024, "main") in keys and ("ECCV", 2025, "main") not in keys
    assert all(
        row["status"] in ("pending", "crawled", "reconciled", "unavailable") for row in inventory
    )
    assert all(row["evidence"] for row in inventory if row["status"] != "pending")


def test_repository_is_not_publication_and_work_year_is_not_venue_year():
    paper = PaperRecord(id="p", title="Fixture method", doi="10.1234/example")
    work = OpenAlexWork(
        id="https://openalex.org/W1",
        doi="10.1234/example",
        cited_by_count=0,
        referenced_works=[],
        publication_year=2023,
        locations=[
            {
                "is_published": True,
                "landing_page_url": "https://arxiv.org/abs/2308.04079",
                "source": {"id": "S1", "type": "repository", "display_name": "arXiv"},
            },
            {
                "is_published": True,
                "landing_page_url": "https://doi.org/10.1234/example",
                "source": {"id": "S2", "type": "conference", "display_name": "Fixture conference"},
            },
        ],
    )
    rows = publication_locations(paper, work)
    assert len(rows) == 1 and rows[0].venue == "Fixture conference"
    assert (
        rows[0].venue_year is None
        and rows[0].reported_work_year == 2023
        and rows[0].status == "provisional"
    )
    paper.doi = "10.1234/different"
    assert publication_locations(paper, work) == []


def test_dblp_pages_reconcile_and_nonjson_status_is_not_empty():
    def handler(request):
        first = int(request.url.params["f"])
        return httpx.Response(
            200,
            json={
                "result": {
                    "hits": {
                        "@total": "2",
                        "@sent": "1",
                        "@first": str(first),
                        "hit": [{"info": {"key": f"conf/example/{first}", "title": "Fixture"}}],
                    }
                }
            },
        )

    with DBLPClient(transport=httpx.MockTransport(handler), sleep=lambda seconds: None) as client:
        assert len(client.search("fixture", page_size=1)) == 2
    with DBLPClient(transport=httpx.MockTransport(lambda request: httpx.Response(202))) as client:
        with pytest.raises(DBLPFailure, match="202"):
            client.search("fixture")
