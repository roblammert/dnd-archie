from archie.ingest import ingest
from archie.retrieve import search
from archie.source_library import list_sources, show_source, verify_sources
from archie.db import connect


def test_source_library_registers_only_srd521():
    ingest()
    rows=list_sources()
    assert len(rows) == 1
    src=rows[0]
    assert src['id'] == 'srd521'
    assert src['authority_type'] == 'official_srd'
    assert src['edition'] == '2024'
    assert src['enabled'] is True
    assert src['evidence_chunks'] == 1067


def test_source_identity_survives_retrieval():
    hits=search('What does Prone do?',8)
    assert hits
    assert all(x.source_id == 'srd521' for x in hits)
    assert all(x.authority_type == 'official_srd' for x in hits)
    assert all(x.edition == '2024' for x in hits)


def test_generic_source_schema_contains_srd_content():
    ingest()
    c=connect()
    try:
        assert c.execute('SELECT count(*) FROM sources').fetchone()[0] == 1
        assert c.execute('SELECT count(*) FROM source_versions').fetchone()[0] == 1
        assert c.execute('SELECT count(*) FROM content_records').fetchone()[0] == 364
        assert c.execute('SELECT count(*) FROM evidence_chunks').fetchone()[0] == 1067
        row=c.execute('SELECT id,authority_type,edition FROM sources').fetchone()
        assert tuple(row) == ('srd521','official_srd','2024')
    finally:
        c.close()


def test_source_show_and_verify():
    ingest()
    src=show_source('srd521')
    assert src['integrity']['ok'] is True
    assert src['evidence_chunks'] == 1067
    result=verify_sources()
    assert result['ok'] is True
    assert result['enabled_count'] == 1
