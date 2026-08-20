from __future__ import annotations

import json
from pathlib import Path
import sqlite3

import pytest
import yaml

import archie.foundry as foundry
import archie.source_library as source_library
from archie.db import SCHEMA
from archie.foundry import FoundryError, foundry_record_admission, import_foundry_snapshot
from archie.source import load_source_manifest


ROOT = Path(__file__).resolve().parents[1]
REVISION = "905c29bcab6a0c6622f3ac6b70f9e040bacbedac"


def _pack(name="spells24", source_book="SRD 5.2"):
    return {"name": name, "path": f"packs/{name}", "type": "Item",
            "flags": {"dnd5e": {"sourceBook": source_book}}}


def _entry(*, record_id="phbsplBestowCurs", pack="spells24", book="", rules="2024",
           license_name="CC-BY-4.0", path=None):
    return {
        "pack": pack,
        "path": path or f"packs/_source/{pack}/3rd-level/bestow-curse.yml",
        "document": {"_id": record_id, "name": "Bestow Curse", "type": "spell",
                     "system": {"source": {"rules": rules, "license": license_name, "book": book}}},
    }


def _without_source_field(entry, field):
    del entry["document"]["system"]["source"][field]
    return entry


def _snapshot(records, packs=None):
    snapshot = {"schema_version": 1, "provider": "foundry-dnd5e", "repository": foundry.REPOSITORY,
                "upstream_revision": REVISION,
                "system_manifest": {"id": "dnd5e", "version": "5.2.0", "packs": packs or [_pack()]},
                "records": records}
    snapshot["content_sha256"] = foundry._content_hash(snapshot)
    return snapshot


def _write(tmp_path, snapshot):
    path = tmp_path / "foundry.json"
    path.write_text(json.dumps(snapshot), encoding="utf-8")
    return path


def _connection():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    return c


@pytest.mark.parametrize(("entry", "pack", "expected"), [
    (_entry(), _pack(), "accepted"),
    (_without_source_field(_entry(), "book"), _pack(), "accepted"),
    (_without_source_field(_entry(), "license"), _pack(), "accepted"),
    (_entry(book="SRD 5.2"), _pack(), "accepted"),
    (_entry(book="PHB 2024"), _pack(), "rejected_non_wotc"),
    (_entry(book="DMG 2024"), _pack(), "rejected_non_wotc"),
    (_entry(book="MM 2024"), _pack(), "rejected_non_wotc"),
    (_entry(), _pack(source_book="PHB 2024"), "rejected_non_wotc"),
    (_entry(pack="content24"), _pack("content24"), "rejected_non_wotc"),
    ({"pack": "spells24", "path": "packs/_source/spells24/x.yml", "document": {"_id": "x"}}, _pack(), "invalid_provenance"),
    (_entry(rules="2014"), _pack(), "invalid_provenance"),
    (_entry(license_name="other"), _pack(), "invalid_provenance"),
    (_entry(path="packs/_source/classes24/x.yml"), _pack(), "invalid_provenance"),
])
def test_foundry_admission_uses_pack_inheritance_and_record_provenance(entry, pack, expected):
    assert foundry_record_admission(entry, pack) == expected


def test_import_accepts_genuine_record_preserves_provenance_and_creates_no_evidence(tmp_path):
    c = _connection()
    result = import_foundry_snapshot(_write(tmp_path, _snapshot([_entry()])), connection=c, imported_at="now")
    assert result["diagnostics"] == {"observed": 1, "accepted": 1, "rejected_non_wotc": 0,
                                     "invalid_provenance": 0, "normalization_failures": 0}
    row = c.execute("SELECT * FROM content_records WHERE source_id=?", (foundry.SOURCE_ID,)).fetchone()
    assert (row["authority_id"], row["representation_id"]) == (foundry.AUTHORITY_ID, foundry.REPRESENTATION_ID)
    assert row["upstream_id"] == "phbsplBestowCurs"
    assert row["upstream_path"] == "packs/_source/spells24/3rd-level/bestow-curse.yml"
    version = c.execute("SELECT upstream_revision FROM source_versions WHERE source_id=?", (foundry.SOURCE_ID,)).fetchone()
    assert version["upstream_revision"] == REVISION
    assert c.execute("SELECT count(*) FROM evidence_chunks WHERE source_id=?", (foundry.SOURCE_ID,)).fetchone()[0] == 0
    c.close()


def test_rejected_and_invalid_records_create_no_content_and_import_is_idempotent(tmp_path):
    c = _connection()
    path = _write(tmp_path, _snapshot([
        _entry(record_id="premium", book="PHB 2024"),
        _entry(record_id="missing"),
        _entry(record_id="malformed", rules="2014"),
    ]))
    # Remove required provenance from the middle record.
    payload = json.loads(path.read_text())
    del payload["records"][1]["document"]["system"]["source"]
    payload["content_sha256"] = foundry._content_hash(payload)
    path.write_text(json.dumps(payload), encoding="utf-8")
    first = import_foundry_snapshot(path, connection=c, imported_at="now")
    second = import_foundry_snapshot(path, connection=c, imported_at="later")
    assert first["diagnostics"] == {"observed": 3, "accepted": 0, "rejected_non_wotc": 1,
                                    "invalid_provenance": 2, "normalization_failures": 0}
    assert second["unchanged"] is True
    assert c.execute("SELECT count(*) FROM source_versions WHERE source_id=?", (foundry.SOURCE_ID,)).fetchone()[0] == 1
    assert c.execute("SELECT count(*) FROM content_records WHERE source_id=?", (foundry.SOURCE_ID,)).fetchone()[0] == 0
    c.close()


def test_duplicate_pack_identity_is_ambiguous_and_rejected(tmp_path):
    c = _connection()
    result = import_foundry_snapshot(_write(tmp_path, _snapshot([_entry()], [_pack(), _pack()])), connection=c, imported_at="now")
    assert result["diagnostics"]["invalid_provenance"] == 1
    assert result["content_records"] == 0
    c.close()


def test_unknown_repository_or_mutable_revision_fails_closed(tmp_path):
    bad = _snapshot([_entry()])
    bad["repository"] = "https://example.invalid/dnd5e"
    with pytest.raises(FoundryError, match="Unknown"):
        import_foundry_snapshot(_write(tmp_path, bad), connection=_connection())
    bad = _snapshot([_entry()])
    bad["upstream_revision"] = "release-5.2.0"
    with pytest.raises(FoundryError, match="immutable"):
        import_foundry_snapshot(_write(tmp_path, bad), connection=_connection())
    bad = _snapshot([_entry()])
    bad["upstream_revision"] = "a" * 40
    bad["content_sha256"] = foundry._content_hash(bad)
    with pytest.raises(FoundryError, match="pinned upstream commit"):
        import_foundry_snapshot(_write(tmp_path, bad), connection=_connection())


def test_committed_foundry_manifest_is_pinned_and_legacy_compatible():
    manifest = load_source_manifest(ROOT / "sources/foundry/srd-5.2/source.yaml")
    assert manifest.id == "foundry:srd-5.2"
    assert manifest.authority_id == "wotc:srd-5.2.1"
    assert manifest.representation_id == "foundry:srd-5.2"
    assert manifest.upstream_revision == REVISION
    assert len(manifest.sha256) == 64


def test_active_snapshot_is_complete_deterministic_permitted_corpus():
    path = ROOT / "sources/foundry/srd-5.2/raw/foundry-srd-5.2-release-5.2.0.json"
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    assert snapshot["content_sha256"] == foundry._content_hash(snapshot)
    assert snapshot["acquisition"]["permitted_packs"] == sorted(foundry.ALLOWED_PACKS)
    assert snapshot["acquisition"]["excluded_packs"] == ["content24", "tables24"]
    assert snapshot["acquisition"]["upstream_files_observed"] == 2252
    assert snapshot["acquisition"]["snapshot_records"] == len(snapshot["records"]) == 2100
    assert {key: snapshot["acquisition"][key] for key in foundry.DIAGNOSTIC_KEYS} == {
        "observed": 2100, "accepted": 1697, "rejected_non_wotc": 0,
        "invalid_provenance": 403, "normalization_failures": 0,
    }
    assert {entry["pack"] for entry in snapshot["records"]} == foundry.ALLOWED_PACKS
    assert not ({"content24", "tables24"} & {entry["pack"] for entry in snapshot["records"]})
    assert [entry["path"] for entry in snapshot["records"]] == sorted(entry["path"] for entry in snapshot["records"])


def test_active_full_snapshot_import_is_idempotent_and_quarantined(monkeypatch):
    raw_path = ROOT / "sources/foundry/srd-5.2/raw/foundry-srd-5.2-release-5.2.0.json"
    c = _connection()
    first = import_foundry_snapshot(raw_path, connection=c, imported_at="now")
    second = import_foundry_snapshot(raw_path, connection=c, imported_at="later")
    # Explicit non-SRD books are rejected_non_wotc. Explicit rules: 2014 is
    # invalid_provenance because it is incompatible with the 2024 representation.
    expected = {"observed": 2100, "accepted": 2095, "rejected_non_wotc": 1,
                "invalid_provenance": 4, "normalization_failures": 0}
    assert first["diagnostics"] == second["diagnostics"] == expected
    assert second["unchanged"] is True
    assert c.execute("SELECT count(*) FROM source_versions WHERE source_id=?", (foundry.SOURCE_ID,)).fetchone()[0] == 1
    assert c.execute("SELECT count(*) FROM content_records WHERE source_id=?", (foundry.SOURCE_ID,)).fetchone()[0] == 2095
    assert c.execute("SELECT count(*) FROM evidence_chunks WHERE source_id=?", (foundry.SOURCE_ID,)).fetchone()[0] == 0
    assert c.execute("SELECT count(*) FROM evidence_fts").fetchone()[0] == 0
    c.close()

    manifest = load_source_manifest(ROOT / "sources/foundry/srd-5.2/source.yaml")
    monkeypatch.setattr("archie.source.discover_source_manifests", lambda: [manifest])
    rebuilt = _connection()
    restored = foundry.rehydrate_foundry_imports(rebuilt, "rebuild")
    assert restored["content_records"] == 2095
    assert restored["diagnostics"] == expected
    assert rebuilt.execute("SELECT count(*) FROM evidence_chunks WHERE source_id=?", (foundry.SOURCE_ID,)).fetchone()[0] == 0
    assert rebuilt.execute("SELECT count(*) FROM evidence_fts").fetchone()[0] == 0
    rebuilt.close()


def test_snapshot_builder_consumes_all_permitted_packs_and_is_deterministic(monkeypatch, tmp_path):
    checkout = tmp_path / "checkout"
    packs = []
    for pack_name in sorted(foundry.ALLOWED_PACKS | {"content24", "tables24"}):
        source_book = "SRD 5.2" if pack_name in foundry.ALLOWED_PACKS else None
        pack = {"name": pack_name, "path": f"packs/{pack_name}", "type": "Item"}
        if source_book:
            pack["flags"] = {"dnd5e": {"sourceBook": source_book}}
        packs.append(pack)
        directory = checkout / "packs" / "_source" / pack_name
        directory.mkdir(parents=True)
        document = _entry(pack=pack_name)["document"]
        document["_id"] = f"id-{pack_name}"
        (directory / "record.yml").write_text(yaml.safe_dump(document), encoding="utf-8")
        (directory / "_folder.yml").write_text(yaml.safe_dump({"_id": f"folder-{pack_name}", "_key": "!folders!x"}), encoding="utf-8")
    (checkout / "system.json").write_text(json.dumps({"id": "dnd5e", "version": "5.2.0", "packs": packs}), encoding="utf-8")
    monkeypatch.setattr(foundry, "_run_git", lambda *args, cwd=None: REVISION)
    first = foundry.build_foundry_snapshot(checkout)
    second = foundry.build_foundry_snapshot(checkout)
    assert first == second
    assert first["content_sha256"] == second["content_sha256"]
    assert first["acquisition"]["upstream_files_observed"] == 14
    assert first["acquisition"]["snapshot_records"] == 7
    assert first["acquisition"]["accepted"] == 7
    assert {entry["pack"] for entry in first["records"]} == foundry.ALLOWED_PACKS
    assert not ({"content24", "tables24"} & {entry["pack"] for entry in first["records"]})


def test_rebuild_rehydration_reapplies_admission(monkeypatch, tmp_path):
    snapshot = _snapshot([_entry(), _entry(record_id="premium", book="MM 2024")])
    raw_path = _write(tmp_path, snapshot)
    digest = foundry.hashlib.sha256(raw_path.read_bytes()).hexdigest()
    manifest_path = tmp_path / "source.yaml"
    manifest_path.write_text(
        "\n".join([
            "id: foundry:srd-5.2", "name: Foundry SRD", "source_type: foundry_snapshot",
            "authority_type: approved_supplement", "authority_id: wotc:srd-5.2.1",
            "representation_id: foundry:srd-5.2", 'edition: "2024"', "enabled: false",
            "approved: true", "license_status: present", "provider: foundry-dnd5e",
            "provider_document_key: srd-5.2", "priority: 90", "license_name: CC-BY-4.0",
            "version:", "  version: release-5.2.0", "  filename: foundry.json",
            f"  sha256: {digest}", f"  upstream_revision: {REVISION}",
        ]) + "\n", encoding="utf-8",
    )
    manifest = load_source_manifest(manifest_path)
    monkeypatch.setattr("archie.source.discover_source_manifests", lambda: [manifest])
    c = _connection()
    result = foundry.rehydrate_foundry_imports(c, "now")
    assert result["content_records"] == 1
    assert result["diagnostics"]["accepted"] == 1
    assert result["diagnostics"]["rejected_non_wotc"] == 1
    assert c.execute("SELECT count(*) FROM evidence_chunks").fetchone()[0] == 0
    c.close()


def test_foundry_manifest_is_enabled_for_alpha63():
    assert load_source_manifest(ROOT / "sources/foundry/srd-5.2/source.yaml").enabled is True
