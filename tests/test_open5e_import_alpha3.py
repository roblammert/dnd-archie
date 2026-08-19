from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

import archie.open5e as open5e
from archie.db import SCHEMA
from archie.open5e import Open5eClient, Open5eError, import_open5e_document


def _handler(request: httpx.Request) -> httpx.Response:
    path=request.url.path
    params=dict(request.url.params)
    if path.endswith('/documents/'):
        return httpx.Response(200,json={'count':1,'next':None,'results':[{
            'key':'srd-2024','name':'System Reference Document 5.2','type':'SOURCE',
            'publisher':{'name':'Wizards of the Coast','key':'wotc'},
            # Match the real alpha.2 discovery finding: license metadata may be absent.
            'license':None,'gamesystem':{'name':'5th Edition 2024','key':'5e-2024'},
            'permalink':'https://example.invalid/srd-2024'
        }]})
    key=params.get('document__key__in')
    assert key == 'srd-2024'
    is_sub=params.get('is_subclass')
    label=path.rstrip('/').split('/')[-1]
    prefix=f"{label}-sub" if is_sub=='true' else label
    results=[
        {'key':f'{prefix}-one','name':f'{prefix.title()} One','document':{'key':'srd-2024'}},
        {'key':f'{prefix}-two','name':f'{prefix.title()} Two','document':{'key':'srd-2024'}},
    ]
    return httpx.Response(200,json={'count':2,'next':None,'results':results})


def _temp_setup(monkeypatch, tmp_path: Path):
    fake=SimpleNamespace(
        root=tmp_path,
        sources_dir=tmp_path/'sources',
        open5e_import_dir=tmp_path/'sources'/'open5e',
        open5e_discovery_dir=tmp_path/'data'/'discovery'/'open5e',
        open5e_base_url='https://api.open5e.test/v2',
        open5e_timeout=1.0,
        database=tmp_path/'data'/'index'/'archie.sqlite3',
    )
    fake.database.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(fake.database)
    db.row_factory=sqlite3.Row
    db.executescript(SCHEMA)
    db.execute("INSERT INTO sources(id,name,source_type,authority_type,edition,enabled,approved,license_status,priority,created_at,updated_at) VALUES('srd521','SRD','local_document','official_srd','2024',1,1,'present',100,'now','now')")
    db.commit(); db.close()
    monkeypatch.setattr(open5e,'settings',fake)
    def connect_temp():
        c=sqlite3.connect(fake.database); c.row_factory=sqlite3.Row; return c
    monkeypatch.setattr(open5e,'connect',connect_temp)
    client=Open5eClient(base_url=fake.open5e_base_url,transport=httpx.MockTransport(_handler))
    return fake,connect_temp,client


def test_selective_import_is_disabled_unapproved_and_preserves_raw(monkeypatch,tmp_path):
    fake,connect_temp,client=_temp_setup(monkeypatch,tmp_path)
    result=import_open5e_document('srd-2024',client)
    assert result['source_id']=='open5e:srd-2024'
    assert result['approved'] is False
    assert result['enabled'] is False
    assert result['license_status']=='missing'
    assert result['automatic_approval_blocked'] is True
    assert result['evidence_chunks']==0
    assert result['content_records'] == 22  # 11 normalized categories x 2 records
    raw=fake.root/result['raw_snapshot']
    assert raw.exists()
    payload=json.loads(raw.read_text())
    assert payload['document']['key']=='srd-2024'
    assert payload['resources']['spells'][0]['document']['key']=='srd-2024'
    manifest=(fake.root/result['manifest']).read_text()
    assert 'enabled: false' in manifest
    assert 'approved: false' in manifest
    assert 'license_status: missing' in manifest
    db=connect_temp()
    row=db.execute("SELECT enabled,approved,license_status,provider,provider_document_key FROM sources WHERE id='open5e:srd-2024'").fetchone()
    assert tuple(row)==(0,0,'missing','open5e','srd-2024')
    assert db.execute("SELECT count(*) FROM evidence_chunks WHERE source_id='open5e:srd-2024'").fetchone()[0]==0
    db.close()


def test_reimport_same_content_is_idempotent(monkeypatch,tmp_path):
    _,connect_temp,client=_temp_setup(monkeypatch,tmp_path)
    first=import_open5e_document('srd-2024',client)
    second=import_open5e_document('srd-2024',client)
    assert first['content_sha256']==second['content_sha256']
    assert second['unchanged'] is True
    db=connect_temp()
    assert db.execute("SELECT count(*) FROM source_versions WHERE source_id='open5e:srd-2024'").fetchone()[0]==1
    assert db.execute("SELECT count(*) FROM content_records WHERE source_id='open5e:srd-2024'").fetchone()[0]==22
    db.close()


def test_alpha3_policy_rejects_unapproved_document_key(monkeypatch,tmp_path):
    _,connect_temp,client=_temp_setup(monkeypatch,tmp_path)
    with pytest.raises(Open5eError,match='allows only'):
        import_open5e_document('deepm',client)
    db=connect_temp()
    assert db.execute("SELECT count(*) FROM sources WHERE id LIKE 'open5e:%'").fetchone()[0]==0
    db.close()


def test_import_does_not_change_enabled_authorities(monkeypatch,tmp_path):
    _,connect_temp,client=_temp_setup(monkeypatch,tmp_path)
    db=connect_temp(); before=[r[0] for r in db.execute('SELECT id FROM sources WHERE enabled=1 ORDER BY id')]; db.close()
    import_open5e_document('srd-2024',client)
    db=connect_temp(); after=[r[0] for r in db.execute('SELECT id FROM sources WHERE enabled=1 ORDER BY id')]; db.close()
    assert before==after==['srd521']
