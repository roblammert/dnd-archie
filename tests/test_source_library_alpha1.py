from archie.ingest import ingest
from archie.retrieve import search
from archie.source_library import list_sources, show_source, verify_sources
from archie.db import connect


def test_source_library_registers_srd521_as_enabled_official_authority():
    """
    Alpha.1 guarantee:
    SRD 5.2.1 is registered as the canonical enabled official source.

    Later releases may legitimately register additional sources, so this test
    must not assume the Source Library contains exactly one source.
    """
    ingest()

    rows = list_sources()
    by_id = {row["id"]: row for row in rows}

    assert "srd521" in by_id

    src = by_id["srd521"]

    assert src["authority_type"] == "official_srd"
    assert src["edition"] == "2024"
    assert src["approved"] is True
    assert src["enabled"] is True
    assert src["license_status"] == "present"
    assert src["evidence_chunks"] == 1067


def test_source_identity_survives_retrieval():
    """
    Alpha.1 guarantee:
    Evidence returned from the canonical SRD retains source identity,
    authority type, and edition metadata.

    Alpha.4 may also return supplemental evidence, so supplemental hits are
    allowed. We only require that canonical SRD evidence remains identifiable.
    """
    hits = search("What does Prone do?", 8)

    assert hits

    srd_hits = [
        hit
        for hit in hits
        if hit.source_id == "srd521"
    ]

    assert srd_hits

    assert all(
        hit.authority_type == "official_srd"
        for hit in srd_hits
    )

    assert all(
        hit.edition == "2024"
        for hit in srd_hits
    )

    # All retrieved evidence must carry explicit source metadata.
    assert all(hit.source_id for hit in hits)
    assert all(hit.authority_type for hit in hits)


def test_generic_source_schema_contains_srd_content():
    """
    Alpha.1 guarantee:
    The generic Source Library schema contains the complete SRD ingestion.

    Counts are scoped to srd521 because later releases may add additional
    source rows, versions, records, and evidence chunks.
    """
    ingest()

    c = connect()

    try:
        source = c.execute(
            """
            SELECT
                id,
                authority_type,
                edition,
                approved,
                enabled,
                license_status
            FROM sources
            WHERE id = 'srd521'
            """
        ).fetchone()

        assert source is not None
        assert source["id"] == "srd521"
        assert source["authority_type"] == "official_srd"
        assert source["edition"] == "2024"
        assert source["approved"] == 1
        assert source["enabled"] == 1
        assert source["license_status"] == "present"

        source_versions = c.execute(
            """
            SELECT count(*)
            FROM source_versions
            WHERE source_id = 'srd521'
            """
        ).fetchone()[0]

        content_records = c.execute(
            """
            SELECT count(*)
            FROM content_records
            WHERE source_id = 'srd521'
            """
        ).fetchone()[0]

        evidence_chunks = c.execute(
            """
            SELECT count(*)
            FROM evidence_chunks
            WHERE source_id = 'srd521'
            """
        ).fetchone()[0]

        assert source_versions == 1
        assert content_records == 364
        assert evidence_chunks == 1067

    finally:
        c.close()


def test_srd521_remains_an_enabled_authority_after_rebuild():
    """
    Later Source Library phases may restore imported supplemental sources
    during ingest. The historical invariant is that rebuilding the database
    must preserve srd521 as an enabled approved authority.
    """
    ingest()

    rows = list_sources()
    by_id = {row["id"]: row for row in rows}

    assert "srd521" in by_id

    srd = by_id["srd521"]

    assert srd["approved"] is True
    assert srd["enabled"] is True
    assert srd["license_status"] == "present"


def test_source_show_and_verify():
    """
    Alpha.1 guarantee:
    The canonical SRD can be inspected and its enabled-source integrity
    verification succeeds.

    verify_sources() may verify more than one source in later releases, so
    this test does not require enabled_count == 1.
    """
    ingest()

    src = show_source("srd521")

    assert src["integrity"]["ok"] is True
    assert src["id"] == "srd521"
    assert src["authority_type"] == "official_srd"
    assert src["edition"] == "2024"
    assert src["approved"] is True
    assert src["enabled"] is True
    assert src["evidence_chunks"] == 1067

    result = verify_sources()

    assert result["ok"] is True
    assert result["enabled_count"] >= 1

    verified_ids = {
        item["source_id"]
        for item in result["sources"]
    }

    assert "srd521" in verified_ids
