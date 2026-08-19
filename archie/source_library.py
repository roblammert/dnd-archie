from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import yaml

from .config import settings
from .db import connect
from .source import discover_source_manifests, get_source_manifest, verify_enabled_sources, verify_manifest
from .structured_evidence import materialize_structured_evidence


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _db_stats(source_id: str) -> dict:
    if not settings.database.exists():
        return {'registered': False, 'content_records': 0, 'evidence_chunks': 0, 'active_version': None, 'active_content_sha256': None}
    c=connect()
    try:
        row=c.execute('''SELECT s.id, sv.version, sv.content_sha256 FROM sources s
                         LEFT JOIN source_versions sv ON sv.source_id=s.id AND sv.active=1
                         WHERE s.id=?''',(source_id,)).fetchone()
        if not row:
            return {'registered': False, 'content_records': 0, 'evidence_chunks': 0, 'active_version': None, 'active_content_sha256': None}
        cr=c.execute('SELECT count(*) FROM content_records WHERE source_id=?',(source_id,)).fetchone()[0]
        ec=c.execute('SELECT count(*) FROM evidence_chunks WHERE source_id=?',(source_id,)).fetchone()[0]
        return {'registered': True, 'content_records': cr, 'evidence_chunks': ec, 'active_version': row['version'], 'active_content_sha256': row['content_sha256']}
    finally:
        c.close()


def list_sources() -> list[dict]:
    rows=[]
    for m in discover_source_manifests():
        stats=_db_stats(m.id)
        rows.append({'id':m.id,'name':m.name,'source_type':m.source_type,'authority_type':m.authority_type,
                     'edition':m.edition,'enabled':m.enabled,'approved':m.approved,'license_status':m.license_status,
                     'provider':m.provider,'provider_document_key':m.provider_document_key,'priority':m.priority,
                     'version':m.version,**stats})
    return rows


def show_source(source_id: str) -> dict:
    m=get_source_manifest(source_id)
    integrity=verify_manifest(m)
    return {**m.to_dict(), **_db_stats(source_id), 'integrity': integrity}


def verify_sources() -> dict:
    items=verify_enabled_sources()
    return {'ok':all(x['ok'] for x in items),'enabled_count':len(items),'sources':items}


def _manifest_data(source_id: str) -> tuple[Path,dict]:
    m=get_source_manifest(source_id)
    path=m.manifest_path
    data=yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(data,dict):
        raise ValueError(f'Invalid source manifest: {path}')
    return path,data


def _write_manifest(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data,sort_keys=False,allow_unicode=True),encoding='utf-8')


def approve_source(source_id: str, *, license_name: str, license_url: str, note: str | None = None) -> dict:
    if source_id == settings.source_id:
        raise ValueError('The canonical SRD source is already approved.')
    if not license_name.strip() or not license_url.strip():
        raise ValueError('Approval requires explicit license name and license URL.')
    path,data=_manifest_data(source_id)
    data['approved']=True
    data['enabled']=False
    data['license_status']='present'
    data['license_name']=license_name.strip()
    data['license_url']=license_url.strip()
    data['approval_note']=note or 'Explicit local administrator approval.'
    data['approved_at']=_now()
    _write_manifest(path,data)
    c=connect()
    try:
        with c:
            c.execute('''UPDATE sources SET approved=1,enabled=0,license_status='present',license_name=?,license_url=?,updated_at=? WHERE id=?''',
                      (license_name.strip(),license_url.strip(),_now(),source_id))
            if c.total_changes == 0:
                raise ValueError(f'Source is not registered in the Source Library: {source_id}')
    finally:
        c.close()
    return show_source(source_id)


def enable_source(source_id: str) -> dict:
    path,data=_manifest_data(source_id)
    if not bool(data.get('approved')):
        raise ValueError(f'Source is not approved: {source_id}')
    if data.get('license_status') != 'present' or not data.get('license_name') or not data.get('license_url'):
        raise ValueError(f'Source lacks verified license metadata: {source_id}')
    if str(data.get('edition') or '') != settings.active_edition:
        raise ValueError(f'Source edition {data.get("edition")} does not match active edition {settings.active_edition}: {source_id}')
    c=connect()
    try:
        with c:
            row=c.execute('SELECT approved,license_status,edition FROM sources WHERE id=?',(source_id,)).fetchone()
            if not row:
                raise ValueError(f'Source is not registered in the Source Library: {source_id}')
            if not row['approved'] or row['license_status']!='present':
                raise ValueError(f'Database source state is not eligible for enablement: {source_id}')
            # Materialize evidence before flipping enabled, so a partial failure cannot leak the source.
            if source_id != settings.source_id:
                materialize_structured_evidence(c,source_id)
            c.execute('UPDATE sources SET enabled=1,updated_at=? WHERE id=?',(_now(),source_id))
    finally:
        c.close()
    data['enabled']=True
    data['enabled_at']=_now()
    _write_manifest(path,data)
    return show_source(source_id)


def disable_source(source_id: str) -> dict:
    if source_id == settings.source_id:
        raise ValueError('The canonical SRD source cannot be disabled in Archie 2.0 alpha.4.')
    path,data=_manifest_data(source_id)
    data['enabled']=False
    data['disabled_at']=_now()
    _write_manifest(path,data)
    c=connect()
    try:
        with c:
            c.execute('UPDATE sources SET enabled=0,updated_at=? WHERE id=?',(_now(),source_id))
    finally:
        c.close()
    return show_source(source_id)


def source_conflicts() -> list[dict]:
    """Report same-named structured records across enabled sources in the active edition.

    Alpha.4 does not attempt semantic auto-resolution. It exposes overlap so the
    higher-priority source can win retrieval while administrators can inspect it.
    """
    if not settings.database.exists():
        return []
    c=connect()
    try:
        rows=c.execute('''SELECT lower(cr.name) AS norm_name,cr.content_type,group_concat(DISTINCT cr.source_id) AS source_ids,count(DISTINCT cr.source_id) AS n
                          FROM content_records cr JOIN sources s ON s.id=cr.source_id
                          WHERE s.enabled=1 AND (s.edition IS NULL OR s.edition=?) AND cr.name IS NOT NULL
                          GROUP BY lower(cr.name),cr.content_type HAVING count(DISTINCT cr.source_id)>1
                          ORDER BY cr.content_type,norm_name''',(settings.active_edition,)).fetchall()
        return [{'name':r['norm_name'],'content_type':r['content_type'],'source_ids':r['source_ids'].split(','),'source_count':r['n']} for r in rows]
    finally:
        c.close()
