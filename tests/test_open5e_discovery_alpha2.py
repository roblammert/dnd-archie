from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import httpx

import archie.open5e as open5e
from archie.open5e import Open5eClient, discover_open5e, inventory_from_snapshot


def _handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    params = dict(request.url.params)
    if path.endswith('/documents/'):
        return httpx.Response(200, json={
            'count': 2,
            'next': None,
            'results': [
                {
                    'key': 'srd-2024',
                    'name': 'System Reference Document 2024',
                    'type': 'ruleset',
                    'publisher': {'name': 'Wizards of the Coast', 'key': 'wotc'},
                    'license': {'name': 'CC-BY-4.0', 'key': 'cc-by-4'},
                    'gamesystem': {'name': '5e', 'key': '5e'},
                    'author': 'Wizards of the Coast',
                    'published_at': '2025-01-01T00:00:00Z',
                    'permalink': 'https://example.invalid/srd-2024',
                },
                {
                    'key': 'open5e-2024',
                    'name': 'Open5e 2024',
                    'license': {'name': 'CC-BY-4.0', 'key': 'cc-by-4'},
                    'publisher': {'name': 'Open5e', 'key': 'open5e'},
                },
            ],
        })
    key = params.get('document__key__in', '')
    # Stable, endpoint-specific fake counts. The exact values are immaterial.
    base = 100 if key == 'srd-2024' else 200
    if path.endswith('/classes/') and params.get('is_subclass') == 'true':
        count = base + 2
    elif path.endswith('/classes/'):
        count = base + 1
    elif path.endswith('/spells/'):
        count = base + 3
    else:
        count = base + 4
    return httpx.Response(200, json={'count': count, 'next': None, 'results': [{'key': 'x'}]})


def test_open5e_v2_document_discovery_and_inventory():
    client = Open5eClient(base_url='https://api.open5e.test/v2', transport=httpx.MockTransport(_handler))
    docs = client.documents()
    assert [d.key for d in docs] == ['srd-2024', 'open5e-2024']
    assert docs[0].license['name'] == 'CC-BY-4.0'
    assert docs[0].publisher['key'] == 'wotc'
    counts = client.inventory_document('srd-2024')
    assert counts['classes'] == 101
    assert counts['subclasses'] == 102
    assert counts['spells'] == 103
    assert counts['conditions'] == 104


def test_discovery_snapshot_is_inventory_only(monkeypatch, tmp_path: Path):
    fake_settings = SimpleNamespace(
        root=tmp_path,
        open5e_discovery_dir=tmp_path / 'data' / 'discovery' / 'open5e',
        open5e_base_url='https://api.open5e.test/v2',
        open5e_timeout=1.0,
    )
    monkeypatch.setattr(open5e, 'settings', fake_settings)
    client = Open5eClient(base_url=fake_settings.open5e_base_url, transport=httpx.MockTransport(_handler))
    result = discover_open5e(client)
    assert result['provider'] == 'open5e'
    assert result['api_version'] == 'v2'
    assert result['imported_into_archie'] is False
    assert result['document_count'] == 2
    assert len(result['snapshot_sha256']) == 64
    latest = fake_settings.open5e_discovery_dir / 'latest.json'
    assert latest.exists()
    stored = json.loads(latest.read_text())
    assert stored['documents'][0]['resource_counts']['spells'] == 103
    # Alpha.2 is explicitly discovery-only: it creates no source manifests or evidence database.
    assert not (tmp_path / 'sources' / 'open5e').exists()
    assert not (tmp_path / 'data' / 'index' / 'archie.sqlite3').exists()
    loaded = inventory_from_snapshot('srd-2024')
    assert loaded['document_count'] == 1
    assert loaded['documents'][0]['key'] == 'srd-2024'


def test_resource_queries_use_document_filter_and_minimal_page():
    seen = []
    def handler(request: httpx.Request):
        seen.append(request)
        return httpx.Response(200, json={'count': 7, 'next': None, 'results': [{'key': 'x'}]})
    client = Open5eClient(base_url='https://api.open5e.test/v2', transport=httpx.MockTransport(handler))
    assert client.resource_count('spells', 'srd-2024') == 7
    req = seen[0]
    assert req.url.path == '/v2/spells/'
    assert req.url.params['document__key__in'] == 'srd-2024'
    assert req.url.params['limit'] == '1'


def test_open5e_discovery_does_not_change_local_source_library():
    # Alpha.2 does not register an Open5e source merely because discovery tooling exists.
    from archie.source import discover_source_manifests
    ids = {m.id for m in discover_source_manifests()}
    assert 'srd521' in ids
    assert all(not x.startswith('open5e') for x in ids)
