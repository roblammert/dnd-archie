from __future__ import annotations
import sqlite3
from .config import settings

SCHEMA_VERSION = "7"

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- Compatibility/global index metadata. The v1.6 trust tests intentionally
-- continue to bind the active SRD hash through this table.
CREATE TABLE IF NOT EXISTS metadata(
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sources(
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  source_type TEXT NOT NULL,
  authority_type TEXT NOT NULL,
  authority_id TEXT,
  representation_id TEXT,
  edition TEXT,
  enabled INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0,1)),
  approved INTEGER NOT NULL DEFAULT 1 CHECK(approved IN (0,1)),
  license_status TEXT NOT NULL DEFAULT 'present',
  provider TEXT,
  provider_document_key TEXT,
  priority INTEGER NOT NULL DEFAULT 100,
  license_name TEXT,
  license_url TEXT,
  homepage_url TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_versions(
  id INTEGER PRIMARY KEY,
  source_id TEXT NOT NULL,
  version TEXT,
  imported_at TEXT NOT NULL,
  content_sha256 TEXT NOT NULL,
  source_uri TEXT,
  filename TEXT,
  upstream_revision TEXT,
  active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
  FOREIGN KEY(source_id) REFERENCES sources(id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_source_versions_active
  ON source_versions(source_id) WHERE active=1;

CREATE TABLE IF NOT EXISTS content_records(
  id INTEGER PRIMARY KEY,
  source_id TEXT NOT NULL,
  source_version_id INTEGER NOT NULL,
  external_id TEXT,
  content_type TEXT NOT NULL,
  name TEXT,
  edition TEXT,
  authority_id TEXT,
  representation_id TEXT,
  upstream_id TEXT,
  upstream_path TEXT,
  normalization_schema_version INTEGER,
  structured_json TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY(source_id) REFERENCES sources(id) ON DELETE CASCADE,
  FOREIGN KEY(source_version_id) REFERENCES source_versions(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_content_records_source ON content_records(source_id, content_type);

CREATE TABLE IF NOT EXISTS canonical_entities(
  id TEXT PRIMARY KEY,
  authority_id TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  canonical_key TEXT NOT NULL,
  display_name TEXT NOT NULL,
  parent_entity_id TEXT,
  taxonomy_version TEXT NOT NULL,
  created_by TEXT NOT NULL,
  UNIQUE(authority_id,entity_type,canonical_key),
  FOREIGN KEY(parent_entity_id) REFERENCES canonical_entities(id)
);

CREATE TABLE IF NOT EXISTS entity_mappings(
  content_record_id INTEGER PRIMARY KEY,
  canonical_entity_id TEXT,
  status TEXT NOT NULL CHECK(status IN ('mapped','unmapped','ambiguous')),
  method TEXT NOT NULL CHECK(method IN ('structural_id','explicit_crosswalk','semantic_key','reviewed_alias','singleton','none')),
  mapping_key TEXT,
  mapping_version TEXT NOT NULL,
  detail_json TEXT,
  CHECK((status='mapped' AND canonical_entity_id IS NOT NULL AND method<>'none') OR
        (status<>'mapped' AND canonical_entity_id IS NULL)),
  FOREIGN KEY(content_record_id) REFERENCES content_records(id) ON DELETE CASCADE,
  FOREIGN KEY(canonical_entity_id) REFERENCES canonical_entities(id) ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS ix_entity_mappings_entity ON entity_mappings(canonical_entity_id);

CREATE TABLE IF NOT EXISTS evidence_chunks(
  id INTEGER PRIMARY KEY,
  evidence_id TEXT NOT NULL UNIQUE,
  source_id TEXT NOT NULL,
  source_version_id INTEGER NOT NULL,
  content_record_id INTEGER,
  page_pdf INTEGER,
  page_label TEXT,
  heading TEXT NOT NULL,
  text TEXT NOT NULL,
  evidence_kind TEXT NOT NULL DEFAULT 'prose' CHECK(evidence_kind IN ('pdf_prose','prose','structured_record','structured_field','table')),
  searchable INTEGER NOT NULL DEFAULT 1 CHECK(searchable IN (0,1)),
  FOREIGN KEY(source_id) REFERENCES sources(id) ON DELETE CASCADE,
  FOREIGN KEY(source_version_id) REFERENCES source_versions(id) ON DELETE CASCADE,
  FOREIGN KEY(content_record_id) REFERENCES content_records(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS ix_evidence_source ON evidence_chunks(source_id);
CREATE INDEX IF NOT EXISTS ix_evidence_page ON evidence_chunks(source_id, page_pdf);

CREATE TABLE IF NOT EXISTS evidence_families(
  id TEXT PRIMARY KEY,
  authority_id TEXT NOT NULL,
  canonical_entity_id TEXT,
  family_type TEXT NOT NULL CHECK(family_type IN ('entity_summary','prose_rule','field','table','feature')),
  semantic_key TEXT NOT NULL,
  conflict_status TEXT NOT NULL DEFAULT 'clear' CHECK(conflict_status IN ('clear','conflicted')),
  selection_version TEXT NOT NULL,
  FOREIGN KEY(canonical_entity_id) REFERENCES canonical_entities(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_evidence_families_entity ON evidence_families(canonical_entity_id);

CREATE TABLE IF NOT EXISTS evidence_family_members(
  family_id TEXT NOT NULL,
  evidence_chunk_id INTEGER NOT NULL,
  representation_id TEXT NOT NULL,
  evidence_role TEXT NOT NULL CHECK(evidence_role IN ('primary','equivalent','complementary','observation')),
  normalized_digest TEXT NOT NULL,
  exact_duplicate_of INTEGER,
  PRIMARY KEY(family_id,evidence_chunk_id),
  FOREIGN KEY(family_id) REFERENCES evidence_families(id) ON DELETE CASCADE,
  FOREIGN KEY(evidence_chunk_id) REFERENCES evidence_chunks(id) ON DELETE CASCADE,
  FOREIGN KEY(exact_duplicate_of) REFERENCES evidence_chunks(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS evidence_facts(
  id TEXT PRIMARY KEY,
  family_id TEXT NOT NULL,
  evidence_chunk_id INTEGER NOT NULL,
  field_key TEXT NOT NULL,
  canonical_value TEXT NOT NULL,
  display_value TEXT NOT NULL,
  value_schema_version TEXT NOT NULL,
  FOREIGN KEY(family_id) REFERENCES evidence_families(id) ON DELETE CASCADE,
  FOREIGN KEY(evidence_chunk_id) REFERENCES evidence_chunks(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_evidence_facts_family ON evidence_facts(family_id,field_key);

CREATE VIRTUAL TABLE IF NOT EXISTS evidence_fts USING fts5(
  evidence_id UNINDEXED,
  heading,
  text,
  content='evidence_chunks',
  content_rowid='id',
  tokenize='porter unicode61'
);
CREATE VIRTUAL TABLE IF NOT EXISTS evidence_fts_vocab USING fts5vocab(evidence_fts, instance);
CREATE TRIGGER IF NOT EXISTS evidence_ai AFTER INSERT ON evidence_chunks WHEN new.searchable=1 BEGIN
 INSERT INTO evidence_fts(rowid,evidence_id,heading,text) VALUES(new.id,new.evidence_id,new.heading,new.text);
END;
CREATE TRIGGER IF NOT EXISTS evidence_ad AFTER DELETE ON evidence_chunks WHEN old.searchable=1 BEGIN
 INSERT INTO evidence_fts(evidence_fts,rowid,evidence_id,heading,text) VALUES('delete',old.id,old.evidence_id,old.heading,old.text);
END;
CREATE TRIGGER IF NOT EXISTS evidence_au_reindex AFTER UPDATE ON evidence_chunks WHEN old.searchable=1 AND new.searchable=1 BEGIN
 INSERT INTO evidence_fts(evidence_fts,rowid,evidence_id,heading,text) VALUES('delete',old.id,old.evidence_id,old.heading,old.text);
 INSERT INTO evidence_fts(rowid,evidence_id,heading,text) VALUES(new.id,new.evidence_id,new.heading,new.text);
END;
CREATE TRIGGER IF NOT EXISTS evidence_au_remove AFTER UPDATE ON evidence_chunks WHEN old.searchable=1 AND new.searchable=0 BEGIN
 INSERT INTO evidence_fts(evidence_fts,rowid,evidence_id,heading,text) VALUES('delete',old.id,old.evidence_id,old.heading,old.text);
END;
CREATE TRIGGER IF NOT EXISTS evidence_au_add AFTER UPDATE ON evidence_chunks WHEN old.searchable=0 AND new.searchable=1 BEGIN
 INSERT INTO evidence_fts(rowid,evidence_id,heading,text) VALUES(new.id,new.evidence_id,new.heading,new.text);
END;
"""

def connect():
    settings.database.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(settings.database)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c

def initialize(c):
    c.executescript(SCHEMA)

def rebuild_database():
    """Delete generated index storage and initialize the current schema."""
    if settings.database.exists():
        settings.database.unlink()
    for suffix in ("-wal", "-shm"):
        p = settings.database.with_name(settings.database.name + suffix)
        if p.exists():
            p.unlink()
    c = connect()
    initialize(c)
    return c
