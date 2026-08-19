from __future__ import annotations
from .config import settings
from .db import connect
from .source import discover_source_manifests, get_source_manifest, verify_enabled_sources, verify_manifest


def _db_stats(source_id: str) -> dict:
    if not settings.database.exists():
        return {'registered': False, 'content_records': 0, 'evidence_chunks': 0, 'active_version': None}
    c=connect()
    try:
        row=c.execute('''SELECT s.id, sv.version FROM sources s
                         LEFT JOIN source_versions sv ON sv.source_id=s.id AND sv.active=1
                         WHERE s.id=?''',(source_id,)).fetchone()
        if not row:
            return {'registered': False, 'content_records': 0, 'evidence_chunks': 0, 'active_version': None}
        cr=c.execute('SELECT count(*) FROM content_records WHERE source_id=?',(source_id,)).fetchone()[0]
        ec=c.execute('SELECT count(*) FROM evidence_chunks WHERE source_id=?',(source_id,)).fetchone()[0]
        return {'registered': True, 'content_records': cr, 'evidence_chunks': ec, 'active_version': row['version']}
    finally:
        c.close()


def list_sources() -> list[dict]:
    rows=[]
    for m in discover_source_manifests():
        stats=_db_stats(m.id)
        rows.append({
            'id': m.id, 'name': m.name, 'source_type': m.source_type,
            'authority_type': m.authority_type, 'edition': m.edition,
            'enabled': m.enabled, 'priority': m.priority,
            'version': m.version, **stats,
        })
    return rows


def show_source(source_id: str) -> dict:
    m=get_source_manifest(source_id)
    integrity=verify_manifest(m)
    return {**m.to_dict(), **_db_stats(source_id), 'integrity': integrity}


def verify_sources() -> dict:
    items=verify_enabled_sources()
    return {'ok': all(x['ok'] for x in items), 'enabled_count': len(items), 'sources': items}
