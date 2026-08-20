from archie.ingest import ingest
from archie.retrieve import search
from archie.source_library import list_sources, show_source, verify_sources
from archie.db import connect


def test_source_library_registers_srd521_as_enabled_official_authority():
    ingest()
    rows=list_sources()
    by_id={row['id']:row for row in rows}
    assert 'srd521' in by_id
    src=by_id['srd521']
    assert src['authority_type']=='official_srd'
    assert src['authority_id']=='wotc:srd-5.2.1'
    assert src['representation_id']=='wotc:official-srd-5.2.1'
    assert src['edition']=='2024'
    assert src['approved'] is True
    assert src['enabled'] is True
    assert src['license_status']=='present'
    assert src['evidence_chunks']==1067


def test_source_identity_survives_retrieval():
    hits=search('What does Prone do?',8)
    assert hits
    srd_hits=[x for x in hits if x.source_id=='srd521']
    assert srd_hits
    assert all(x.authority_type=='official_srd' for x in srd_hits)
    assert all(x.edition=='2024' for x in srd_hits)
    assert all(x.source_id for x in hits)
    assert all(x.authority_type for x in hits)


def test_generic_source_schema_contains_srd_content():
    ingest()
    c=connect()
    try:
        row=c.execute("SELECT id,authority_type,authority_id,representation_id,edition,approved,enabled,license_status FROM sources WHERE id='srd521'").fetchone()
        assert row is not None
        assert tuple(row)==('srd521','official_srd','wotc:srd-5.2.1','wotc:official-srd-5.2.1','2024',1,1,'present')
        version=c.execute("SELECT upstream_revision FROM source_versions WHERE source_id='srd521'").fetchone()
        assert version['upstream_revision']=='5.2.1'
        provenance=c.execute("SELECT DISTINCT authority_id,representation_id,normalization_schema_version FROM content_records WHERE source_id='srd521'").fetchall()
        assert [tuple(x) for x in provenance]==[('wotc:srd-5.2.1','wotc:official-srd-5.2.1',1)]
        assert c.execute("SELECT count(*) FROM source_versions WHERE source_id='srd521'").fetchone()[0]==1
        assert c.execute("SELECT count(*) FROM content_records WHERE source_id='srd521'").fetchone()[0]==364
        assert c.execute("SELECT count(*) FROM evidence_chunks WHERE source_id='srd521'").fetchone()[0]==1067
    finally:
        c.close()


def test_srd521_remains_an_enabled_authority_after_rebuild():
    ingest()
    by_id={row['id']:row for row in list_sources()}
    assert 'srd521' in by_id
    assert by_id['srd521']['approved'] is True
    assert by_id['srd521']['enabled'] is True
    assert by_id['srd521']['license_status']=='present'


def test_source_show_and_verify():
    ingest()
    src=show_source('srd521')
    assert src['integrity']['ok'] is True
    assert src['id']=='srd521'
    assert src['authority_type']=='official_srd'
    assert src['authority_id']=='wotc:srd-5.2.1'
    assert src['representation_id']=='wotc:official-srd-5.2.1'
    assert src['edition']=='2024'
    assert src['approved'] is True
    assert src['enabled'] is True
    assert src['evidence_chunks']==1067
    result=verify_sources()
    assert result['ok'] is True
    assert result['enabled_count']>=1
    assert 'srd521' in {item['source_id'] for item in result['sources']}
    official=next(item for item in result['sources'] if item['source_id']=='srd521')
    assert official['authority_id']=='wotc:srd-5.2.1'
    assert official['representation_id']=='wotc:official-srd-5.2.1'
