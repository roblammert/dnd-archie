from __future__ import annotations
import sqlite3
from .config import settings

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS chunks(
  id INTEGER PRIMARY KEY,
  evidence_id TEXT NOT NULL UNIQUE,
  page_pdf INTEGER NOT NULL,
  page_label TEXT NOT NULL,
  heading TEXT NOT NULL,
  text TEXT NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
  evidence_id UNINDEXED,
  heading,
  text,
  content='chunks',
  content_rowid='id',
  tokenize='porter unicode61'
);
CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
 INSERT INTO chunks_fts(rowid,evidence_id,heading,text) VALUES(new.id,new.evidence_id,new.heading,new.text);
END;
CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
 INSERT INTO chunks_fts(chunks_fts,rowid,evidence_id,heading,text) VALUES('delete',old.id,old.evidence_id,old.heading,old.text);
END;
CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
 INSERT INTO chunks_fts(chunks_fts,rowid,evidence_id,heading,text) VALUES('delete',old.id,old.evidence_id,old.heading,old.text);
 INSERT INTO chunks_fts(rowid,evidence_id,heading,text) VALUES(new.id,new.evidence_id,new.heading,new.text);
END;
"""

def connect():
    settings.database.parent.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(settings.database)
    c.row_factory=sqlite3.Row
    return c

def initialize(c):
    c.executescript(SCHEMA)
