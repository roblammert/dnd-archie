from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import httpx

import archie.open5e as open5e
import archie.source as source_module

from archie.open5e import (
    Open5eClient,
    discover_open5e,
    inventory_from_snapshot,
)


def _handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    params = dict(request.url.params)

    if path.endswith("/documents/"):
        return httpx.Response(
            200,
            json={
                "count": 2,
                "next": None,
                "results": [
                    {
                        "key": "srd-2024",
                        "name": "System Reference Document 2024",
                        "type": "ruleset",
                        "publisher": {
                            "name": "Wizards of the Coast",
                            "key": "wotc",
                        },
                        "license": {
                            "name": "CC-BY-4.0",
                            "key": "cc-by-4",
                        },
                        "gamesystem": {
                            "name": "5e",
                            "key": "5e",
                        },
                        "author": "Wizards of the Coast",
                        "published_at": "2025-01-01T00:00:00Z",
                        "permalink": "https://example.invalid/srd-2024",
                    },
                    {
                        "key": "open5e-2024",
                        "name": "Open5e 2024",
                        "license": {
                            "name": "CC-BY-4.0",
                            "key": "cc-by-4",
                        },
                        "publisher": {
                            "name": "Open5e",
                            "key": "open5e",
                        },
                    },
                ],
            },
        )

    key = params.get("document__key__in", "")

    # Stable, endpoint-specific fake counts.
    # The exact values are immaterial; the tests verify filtering behavior.
    base = 100 if key == "srd-2024" else 200

    if path.endswith("/classes/") and params.get("is_subclass") == "true":
        count = base + 2
    elif path.endswith("/classes/"):
        count = base + 1
    elif path.endswith("/spells/"):
        count = base + 3
    else:
        count = base + 4

    return httpx.Response(
        200,
        json={
            "count": count,
            "next": None,
            "results": [{"key": "x"}],
        },
    )


def test_open5e_v2_document_discovery_and_inventory():
    client = Open5eClient(
        base_url="https://api.open5e.test/v2",
        transport=httpx.MockTransport(_handler),
    )

    docs = client.documents()

    assert [d.key for d in docs] == [
        "srd-2024",
        "open5e-2024",
    ]

    assert docs[0].license["name"] == "CC-BY-4.0"
    assert docs[0].publisher["key"] == "wotc"

    counts = client.inventory_document("srd-2024")

    assert counts["classes"] == 101
    assert counts["subclasses"] == 102
    assert counts["spells"] == 103
    assert counts["conditions"] == 104


def test_discovery_snapshot_is_inventory_only(monkeypatch, tmp_path: Path):
    """
    Alpha.2 guarantee:
    Discovery writes only discovery/inventory data.

    It must not create Source Library manifests, an Archie database,
    content records, evidence chunks, or rules authority.
    """
    fake_settings = SimpleNamespace(
        root=tmp_path,
        open5e_discovery_dir=(
            tmp_path
            / "data"
            / "discovery"
            / "open5e"
        ),
        open5e_base_url="https://api.open5e.test/v2",
        open5e_timeout=1.0,
    )

    monkeypatch.setattr(
        open5e,
        "settings",
        fake_settings,
    )

    client = Open5eClient(
        base_url=fake_settings.open5e_base_url,
        transport=httpx.MockTransport(_handler),
    )

    result = discover_open5e(client)

    assert result["provider"] == "open5e"
    assert result["api_version"] == "v2"
    assert result["imported_into_archie"] is False
    assert result["document_count"] == 2
    assert len(result["snapshot_sha256"]) == 64

    latest = (
        fake_settings.open5e_discovery_dir
        / "latest.json"
    )

    assert latest.exists()

    stored = json.loads(
        latest.read_text()
    )

    assert (
        stored["documents"][0]
        ["resource_counts"]["spells"]
        == 103
    )

    # Discovery alone creates no source manifests.
    assert not (
        tmp_path
        / "sources"
        / "open5e"
    ).exists()

    # Discovery alone creates no generated Archie index.
    assert not (
        tmp_path
        / "data"
        / "index"
        / "archie.sqlite3"
    ).exists()

    loaded = inventory_from_snapshot(
        "srd-2024"
    )

    assert loaded["document_count"] == 1
    assert (
        loaded["documents"][0]["key"]
        == "srd-2024"
    )


def test_resource_queries_use_document_filter_and_minimal_page():
    seen = []

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        seen.append(request)

        return httpx.Response(
            200,
            json={
                "count": 7,
                "next": None,
                "results": [{"key": "x"}],
            },
        )

    client = Open5eClient(
        base_url="https://api.open5e.test/v2",
        transport=httpx.MockTransport(handler),
    )

    assert (
        client.resource_count(
            "spells",
            "srd-2024",
        )
        == 7
    )

    req = seen[0]

    assert req.url.path == "/v2/spells/"
    assert (
        req.url.params["document__key__in"]
        == "srd-2024"
    )
    assert req.url.params["limit"] == "1"


def test_open5e_discovery_does_not_register_or_authorize_source(
    monkeypatch,
    tmp_path: Path,
):
    """
    Alpha.2 historical guarantee:

    Discovery by itself must never register, approve, enable, or otherwise
    authorize an Open5e source.

    This test uses an isolated temporary Source Library so it remains valid
    even after alpha.3/alpha.4 legitimately import Open5e sources in the real
    development repository.
    """
    discovery_dir = (
        tmp_path
        / "data"
        / "discovery"
        / "open5e"
    )

    sources_dir = tmp_path / "sources"

    fake_open5e_settings = SimpleNamespace(
        root=tmp_path,
        open5e_discovery_dir=discovery_dir,
        open5e_base_url="https://api.open5e.test/v2",
        open5e_timeout=1.0,
    )

    fake_source_settings = SimpleNamespace(
        sources_dir=sources_dir,
    )

    monkeypatch.setattr(
        open5e,
        "settings",
        fake_open5e_settings,
    )

    monkeypatch.setattr(
        source_module,
        "settings",
        fake_source_settings,
    )

    before = (
        source_module
        .discover_source_manifests()
    )

    assert before == []

    client = Open5eClient(
        base_url=fake_open5e_settings.open5e_base_url,
        transport=httpx.MockTransport(_handler),
    )

    result = discover_open5e(client)

    assert result["imported_into_archie"] is False

    after = (
        source_module
        .discover_source_manifests()
    )

    assert after == []

    # The discovery snapshot exists...
    assert (
        discovery_dir
        / "latest.json"
    ).exists()

    # ...but no Source Library manifest was created.
    assert not sources_dir.exists()
