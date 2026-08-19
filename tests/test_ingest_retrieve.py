from archie.ingest import ingest
from archie.retrieve import search


def test_ingest_and_find_advantage():
    """
    Ingest must produce the canonical SRD corpus, and retrieval for a
    core rule such as Advantage/Disadvantage must retain official SRD
    evidence even when approved supplemental 2024 sources are enabled.

    Alpha.5 intentionally permits supplemental evidence to coexist in
    the final retrieval window, so this test must not require every hit
    to come from SRD521.
    """

    info = ingest()

    assert int(info["chunks"]) > 300

    hits = search(
        "advantage disadvantage",
        5,
    )

    assert hits

    # Canonical SRD evidence must remain represented.
    official_hits = [
        hit
        for hit in hits
        if hit.source_id == "srd521"
    ]

    assert official_hits

    assert all(
        hit.evidence_id.startswith("SRD521-P")
        for hit in official_hits
    )

    assert all(
        hit.authority_type == "official_srd"
        for hit in official_hits
    )

    assert all(
        hit.edition == "2024"
        for hit in official_hits
    )

    # Every returned result must come from an approved retrieval
    # authority type in the active 2024 ruleset.
    assert all(
        hit.authority_type
        in {
            "official_srd",
            "approved_supplement",
        }
        for hit in hits
    )

    assert all(
        hit.edition == "2024"
        for hit in hits
    )


def test_core_rule_retrieval_prefers_official_source():
    """
    For a core rule represented in both the official SRD and an approved
    supplemental source, the strongest returned evidence should remain
    canonical SRD evidence.
    """

    hits = search(
        "advantage disadvantage",
        5,
    )

    assert hits

    assert hits[0].source_id == "srd521"
    assert hits[0].authority_type == "official_srd"


def test_supplemental_sources_do_not_remove_canonical_advantage_evidence():
    """
    Multi-source retrieval may add supplemental evidence, but enabling
    those sources must not remove the known SRD Advantage definition
    from the evidence window.
    """

    hits = search(
        "What happens when I have advantage on a roll?",
        12,
    )

    ids = {
        hit.evidence_id
        for hit in hits
    }

    assert (
        "SRD521-P008-C01" in ids
        or "SRD521-P176-C02" in ids
    )
