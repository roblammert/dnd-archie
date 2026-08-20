from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

import archie.db as dbmod
import archie.source as sourcemod
import archie.source_library as sl
import archie.retrieve as retrieve
from archie.db import SCHEMA


def _settings(tmp_path: Path):
    return SimpleNamespace(
        root=tmp_path,
        sources_dir=tmp_path/'sources',
        database=tmp_path/'data'/'index'/'archie.sqlite3',
        source_id='srd521',
        active_edition='2024',
        top_k=6,
        retrieval_candidate_k=36,
        neighbor_radius=0,
    )


def _connect(path: Path):
    path.parent.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(path); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON')
    return c


def _manifest(root: Path, source_id: str, *, approved=False, enabled=False, license_status='missing', edition='2024', priority=80):
    d=root/'sources'/'open5e'/'srd-2024'; d.mkdir(parents=True,exist_ok=True)
    raw=d/'raw.json'; raw.write_text('{"provider":"open5e","document_key":"srd-2024","resources":{},"content_sha256":"abc"}\n')
    sha=hashlib.sha256(raw.read_bytes()).hexdigest()
    data={
        'id':source_id,'name':'System Reference Document 5.2','source_type':'open5e_snapshot',
        'authority_type':'approved_supplement','edition':edition,'enabled':enabled,'approved':approved,
        'license_status':license_status,'provider':'open5e','provider_document_key':'srd-2024','priority':priority,
        'license_name':'CC BY 4.0' if license_status=='present' else None,
        'license_url':'https://example.invalid/license' if license_status=='present' else None,
        'homepage_url':'https://example.invalid',
        'version':{'version':'open5e-v2-test','filename':'raw.json','sha256':sha,'source_uri':'https://api.open5e.test/v2/documents/'},
    }
    (d/'source.yaml').write_text(yaml.safe_dump(data,sort_keys=False))
    return d/'source.yaml'


def _setup(monkeypatch,tmp_path: Path):
    st=_settings(tmp_path)
    for mod in (dbmod,sourcemod,sl,retrieve):
        monkeypatch.setattr(mod,'settings',st)
    c=_connect(st.database); c.executescript(SCHEMA)
    c.execute("INSERT INTO metadata(key,value) VALUES('source_id','srd521')")
    c.execute("INSERT INTO metadata(key,value) VALUES('source_sha256','test')")
    c.execute("""INSERT INTO sources(id,name,source_type,authority_type,edition,enabled,approved,license_status,priority,created_at,updated_at)
                 VALUES('srd521','SRD','local_document','official_srd','2024',1,1,'present',100,'now','now')""")
    cur=c.execute("INSERT INTO source_versions(source_id,version,imported_at,content_sha256,active) VALUES('srd521','5.2.1','now','test',1)")
    official_ver=cur.lastrowid
    _manifest(tmp_path,'open5e:srd-2024')
    c.execute("""INSERT INTO sources(id,name,source_type,authority_type,edition,enabled,approved,license_status,provider,provider_document_key,priority,created_at,updated_at)
                 VALUES('open5e:srd-2024','System Reference Document 5.2','open5e_snapshot','approved_supplement','2024',0,0,'missing','open5e','srd-2024',80,'now','now')""")
    cur=c.execute("INSERT INTO source_versions(source_id,version,imported_at,content_sha256,active) VALUES('open5e:srd-2024','open5e-v2-test','now','abc',1)")
    supp_ver=cur.lastrowid
    obj={'key':'mystic-spark','name':'Mystic Spark','level':1,'desc':'A unique alpha four test rule about mystic spark.'}
    c.execute("""INSERT INTO content_records(source_id,source_version_id,external_id,content_type,name,edition,structured_json,created_at)
                 VALUES('open5e:srd-2024',?,'mystic-spark','spells','Mystic Spark','2024',?,'now')""",(supp_ver,json.dumps(obj)))
    c.commit(); c.close()
    monkeypatch.setattr(retrieve,'verify_source',lambda:{'ok':True})
    monkeypatch.setattr(retrieve,'_verify_index',lambda c:None)
    return st,official_ver,supp_ver


def test_approval_requires_explicit_license_and_enable_materializes(monkeypatch,tmp_path):
    st,_,_= _setup(monkeypatch,tmp_path)
    with pytest.raises(ValueError,match='license'):
        sl.approve_source('open5e:srd-2024',license_name='',license_url='')
    approved=sl.approve_source('open5e:srd-2024',license_name='CC BY 4.0',license_url='https://example.invalid/cc')
    assert approved['approved'] is True and approved['enabled'] is False
    enabled=sl.enable_source('open5e:srd-2024')
    assert enabled['enabled'] is True
    assert enabled['evidence_chunks'] >= 1
    c=_connect(st.database)
    row=c.execute("SELECT approved,enabled,license_status FROM sources WHERE id='open5e:srd-2024'").fetchone()
    assert tuple(row)==(1,1,'present')
    assert c.execute("SELECT count(*) FROM evidence_chunks WHERE source_id='open5e:srd-2024'").fetchone()[0] >= 1
    c.close()


def test_unapproved_source_cannot_enable(monkeypatch,tmp_path):
    _setup(monkeypatch,tmp_path)
    with pytest.raises(ValueError,match='not approved'):
        sl.enable_source('open5e:srd-2024')


def test_enabled_structured_source_is_searchable_and_source_aware(monkeypatch,tmp_path):
    _setup(monkeypatch,tmp_path)
    sl.approve_source('open5e:srd-2024',license_name='CC BY 4.0',license_url='https://example.invalid/cc')
    sl.enable_source('open5e:srd-2024')
    hits=retrieve.search('mystic spark',top_k=4,expand_neighbors=False)
    assert hits
    hit=next(x for x in hits if x.source_id=='open5e:srd-2024')
    assert hit.authority_type=='approved_supplement'
    assert hit.edition=='2024'
    assert hit.page_pdf is None
    assert hit.evidence_id.startswith('O5E-SRD-2024-')


def test_active_edition_excludes_enabled_2014_source(monkeypatch,tmp_path):
    st,_,_= _setup(monkeypatch,tmp_path)
    sl.approve_source('open5e:srd-2024',license_name='CC BY 4.0',license_url='https://example.invalid/cc')
    sl.enable_source('open5e:srd-2024')
    c=_connect(st.database)
    c.execute("""INSERT INTO sources(id,name,source_type,authority_type,edition,enabled,approved,license_status,priority,created_at,updated_at)
                 VALUES('old2014','Old','test','approved_supplement','2014',1,1,'present',90,'now','now')""")
    cur=c.execute("INSERT INTO source_versions(source_id,version,imported_at,content_sha256,active) VALUES('old2014','1','now','old',1)")
    c.execute("INSERT INTO evidence_chunks(evidence_id,source_id,source_version_id,heading,text) VALUES('OLD-1','old2014',?,'Mystic Spark','mystic spark old 2014 rule')",(cur.lastrowid,))
    c.commit(); c.close()
    hits=retrieve.search('mystic spark',top_k=10,expand_neighbors=False)
    assert all(x.source_id!='old2014' for x in hits)


def test_official_authority_precedes_supplement_on_equivalent_match(monkeypatch,tmp_path):
    st,official_ver,_= _setup(monkeypatch,tmp_path)
    sl.approve_source('open5e:srd-2024',license_name='CC BY 4.0',license_url='https://example.invalid/cc')
    sl.enable_source('open5e:srd-2024')
    c=_connect(st.database)
    c.execute("INSERT INTO evidence_chunks(evidence_id,source_id,source_version_id,heading,text) VALUES('SRD-TEST','srd521',?,'Mystic Spark','Name: Mystic Spark unique alpha four test rule about mystic spark.')",(official_ver,))
    c.commit(); c.close()
    hits=retrieve.search('mystic spark',top_k=4,expand_neighbors=False)
    assert hits[0].source_id=='srd521'


def test_conflict_report_lists_same_named_content_across_enabled_sources(monkeypatch,tmp_path):
    st,official_ver,_= _setup(monkeypatch,tmp_path)
    sl.approve_source('open5e:srd-2024',license_name='CC BY 4.0',license_url='https://example.invalid/cc')
    sl.enable_source('open5e:srd-2024')
    c=_connect(st.database)
    c.execute("""INSERT INTO content_records(source_id,source_version_id,external_id,content_type,name,edition,structured_json,created_at)
                 VALUES('srd521',?,'mystic-spark','spells','Mystic Spark','2024','{}','now')""",(official_ver,))
    c.commit(); c.close()
    conflicts=sl.source_conflicts()
    assert any(x['name']=='mystic spark' and set(x['source_ids'])=={'srd521','open5e:srd-2024'} for x in conflicts)


def test_disable_excludes_source_without_deleting_evidence(monkeypatch,tmp_path):
    st,_,_= _setup(monkeypatch,tmp_path)
    sl.approve_source('open5e:srd-2024',license_name='CC BY 4.0',license_url='https://example.invalid/cc')
    sl.enable_source('open5e:srd-2024')
    c=_connect(st.database); before=c.execute("SELECT count(*) FROM evidence_chunks WHERE source_id='open5e:srd-2024'").fetchone()[0]; c.close()
    sl.disable_source('open5e:srd-2024')
    c=_connect(st.database); after=c.execute("SELECT count(*) FROM evidence_chunks WHERE source_id='open5e:srd-2024'").fetchone()[0]; c.close()
    assert before==after and after>0
    assert all(x.source_id!='open5e:srd-2024' for x in retrieve.search('mystic spark',top_k=10,expand_neighbors=False))

def test_rehydrate_restores_enabled_approved_source_with_evidence(monkeypatch,tmp_path):
    import archie.open5e as o5
    st=_settings(tmp_path)
    st.open5e_import_dir=tmp_path/'sources'/'open5e'
    monkeypatch.setattr(dbmod,'settings',st)
    monkeypatch.setattr(sourcemod,'settings',st)
    monkeypatch.setattr(o5,'settings',st)
    source_dir=tmp_path/'sources'/'open5e'/'srd-2024'; source_dir.mkdir(parents=True,exist_ok=True)
    raw=source_dir/'raw.json'
    payload={
        'provider':'open5e','document_key':'srd-2024','content_sha256':'content-test',
        'resources':{'spells':[
            {'key':'spark','name':'Spark','desc':'A rebuild persistence test spell.','document':{'key':'srd-2024'}},
            {'key':'other','name':'Other','document':{'key':'third-party'}},
            {'key':'missing','name':'Missing'},
        ]}
    }
    raw.write_text(json.dumps(payload)+'\n')
    sha=hashlib.sha256(raw.read_bytes()).hexdigest()
    manifest={
        'id':'open5e:srd-2024','name':'System Reference Document 5.2','source_type':'open5e_snapshot',
        'authority_type':'approved_supplement','edition':'2024','enabled':True,'approved':True,
        'license_status':'present','provider':'open5e','provider_document_key':'srd-2024','priority':80,
        'license_name':'CC BY 4.0','license_url':'https://example.invalid/cc',
        'version':{'version':'test','filename':'raw.json','sha256':sha,'source_uri':'https://api.open5e.test/v2/'},
    }
    (source_dir/'source.yaml').write_text(yaml.safe_dump(manifest,sort_keys=False))
    c=_connect(st.database); c.executescript(SCHEMA)
    result=o5.rehydrate_open5e_imports(c,'now')
    c.commit()
    assert result=={'sources':1,'content_records':1,'diagnostics':{
        'observed':3,'accepted':1,'rejected_non_wotc':1,
        'invalid_provenance':1,'normalization_failures':0,
    }}
    assert tuple(c.execute("SELECT enabled,approved FROM sources WHERE id='open5e:srd-2024'").fetchone())==(1,1)
    assert c.execute("SELECT count(*) FROM evidence_chunks WHERE source_id='open5e:srd-2024'").fetchone()[0] >= 1
    c.close()
