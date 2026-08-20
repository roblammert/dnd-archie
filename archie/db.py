from __future__ import annotations
import sqlite3
from .config import settings

SCHEMA_VERSION = "5"

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
  FOREIGN KEY(source_id) REFERENCES sources(id) ON DELETE CASCADE,
  FOREIGN KEY(source_version_id) REFERENCES source_versions(id) ON DELETE CASCADE,
  FOREIGN KEY(content_record_id) REFERENCES content_records(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS ix_evidence_source ON evidence_chunks(source_id);
CREATE INDEX IF NOT EXISTS ix_evidence_page ON evidence_chunks(source_id, page_pdf);

CREATE VIRTUAL TABLE IF NOT EXISTS evidence_fts USING fts5(
  evidence_id UNINDEXED,
  heading,
  text,
  content='evidence_chunks',
  content_rowid='id',
  tokenize='porter unicode61'
);
CREATE TRIGGER IF NOT EXISTS evidence_ai AFTER INSERT ON evidence_chunks BEGIN
 INSERT INTO evidence_fts(rowid,evidence_id,heading,text) VALUES(new.id,new.evidence_id,new.heading,new.text);
END;
CREATE TRIGGER IF NOT EXISTS evidence_ad AFTER DELETE ON evidence_chunks BEGIN
 INSERT INTO evidence_fts(evidence_fts,rowid,evidence_id,heading,text) VALUES('delete',old.id,old.evidence_id,old.heading,old.text);
END;
CREATE TRIGGER IF NOT EXISTS evidence_au AFTER UPDATE ON evidence_chunks BEGIN
 INSERT INTO evidence_fts(evidence_fts,rowid,evidence_id,heading,text) VALUES('delete',old.id,old.evidence_id,old.heading,old.text);
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
