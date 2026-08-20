from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from .source import verify_source
from .source_library import list_sources, show_source, verify_sources, approve_source, enable_source, disable_source, source_conflicts
from .ingest import ingest
from .retrieve import search, diagnose
from .answer import ask
from .characters import load_character,list_characters
from .config import settings
from .open5e import discover_open5e, inventory_from_snapshot, import_open5e_document
from .foundry import acquire_foundry_snapshot, import_foundry_snapshot
from .cantilux import acquire_cantilux_snapshot, import_cantilux_snapshot
from .db import connect
from .identity import identity_fingerprint, identity_report
from .evidence_families import evidence_fingerprint, evidence_report


def print_answer(r):
    print(f"[{r.status}]\n{r.answer}")
    if r.claims:
        print('\nEvidence-backed claims:')
        byid={e.evidence_id:e for e in r.evidence}
        for c in r.claims:
            refs=', '.join((f"{x} (PDF p.{byid[x].page_pdf}, {byid[x].source_id})" if byid[x].page_pdf is not None else f"{x} ({byid[x].source_id})") for x in c['evidence_ids'])
            print(f"- {c['text']} [{c['kind']}] — {refs}")
    if getattr(r,'sources_used',None):
        print('\nSources used:')
        for src in r.sources_used:
            evidence_count=len(src.get('evidence_ids',[]))
            print(f"- {src['source_id']} [{src.get('edition') or '-'}] — {evidence_count} cited evidence item(s)")
        print("Authority: SRD 5.2.1")
    print(f"\nProvenance: {r.reason}")


def _print_sources(rows):
    print(f"{'ID':<20} {'TYPE':<17} {'AUTHORITY':<20} {'EDITION':<9} {'APPROVED':<9} {'ENABLED':<8} {'LICENSE':<9} {'VERSION':<20} CHUNKS")
    for x in rows:
        print(f"{x['id']:<20} {x['source_type']:<17} {x['authority_type']:<20} {(x['edition'] or '-'):<9} "
              f"{('yes' if x['approved'] else 'no'):<9} {('yes' if x['enabled'] else 'no'):<8} {x['license_status']:<9} "
              f"{(x['version'] or '-'):<20} {x['evidence_chunks']}")


def _short_meta(value):
    if isinstance(value, dict):
        return str(value.get('name') or value.get('key') or value.get('title') or '-')
    return str(value or '-')


def main(argv=None):
    p=argparse.ArgumentParser(prog='archie',description='Evidence-gated D&D player assistant')
    sub=p.add_subparsers(dest='cmd',required=True)
    sub.add_parser('verify-source')
    sub.add_parser('ingest')
    s=sub.add_parser('search'); s.add_argument('query'); s.add_argument('--top-k',type=int,default=None); s.add_argument('--json',action='store_true')
    d=sub.add_parser('diagnose-retrieval'); d.add_argument('query'); d.add_argument('--top-k',type=int,default=None)
    a=sub.add_parser('ask'); a.add_argument('question'); a.add_argument('--character'); a.add_argument('--no-audit',action='store_true')
    sub.add_parser('characters')
    sub.add_parser('doctor')
    ident=sub.add_parser('identity',help='Inspect deterministic structured-resource identity')
    idsub=ident.add_subparsers(dest='identity_cmd',required=True)
    for command in ('report','unmapped','ambiguous'):
        ip=idsub.add_parser(command); ip.add_argument('--json',action='store_true')
    ie=idsub.add_parser('show'); ie.add_argument('entity_id'); ie.add_argument('--json',action='store_true')
    ev=sub.add_parser('evidence',help='Inspect alpha.6.2 evidence families')
    evsub=ev.add_subparsers(dest='evidence_cmd',required=True)
    evsub.add_parser('report')
    evf=evsub.add_parser('family'); evf.add_argument('family_id')
    evsub.add_parser('conflicts')

    src=sub.add_parser('sources',help='Inspect and verify the local Source Library')
    srcsub=src.add_subparsers(dest='sources_cmd',required=True)
    sl=srcsub.add_parser('list'); sl.add_argument('--json',action='store_true')
    ss=srcsub.add_parser('show'); ss.add_argument('source_id'); ss.add_argument('--json',action='store_true')
    sv=srcsub.add_parser('verify'); sv.add_argument('--json',action='store_true')
    sd=srcsub.add_parser('discover',help='Discover external source-provider catalogs without importing content')
    sd.add_argument('provider',choices=['open5e']); sd.add_argument('--json',action='store_true')
    si=srcsub.add_parser('inventory',help='Inspect the latest external discovery snapshot')
    si.add_argument('provider',choices=['open5e']); si.add_argument('--document'); si.add_argument('--json',action='store_true')
    sacq=srcsub.add_parser('acquire',help='Reproducibly acquire a pinned external source snapshot')
    sacq.add_argument('provider',choices=['foundry','cantilux']); sacq.add_argument('--checkout'); sacq.add_argument('--output'); sacq.add_argument('--json',action='store_true')
    simp=srcsub.add_parser('import',help='Import an explicitly allowed external snapshot into the local Source Library')
    simp.add_argument('provider',choices=['open5e','foundry','cantilux']); simp.add_argument('document'); simp.add_argument('--json',action='store_true')
    sap=srcsub.add_parser('approve',help='Explicitly approve an imported source after license review')
    sap.add_argument('source_id'); sap.add_argument('--license-name',required=True); sap.add_argument('--license-url',required=True); sap.add_argument('--note'); sap.add_argument('--json',action='store_true')
    sen=srcsub.add_parser('enable',help='Enable an approved source and materialize searchable evidence')
    sen.add_argument('source_id'); sen.add_argument('--json',action='store_true')
    sdis=srcsub.add_parser('disable',help='Disable a supplemental source without deleting its local snapshot')
    sdis.add_argument('source_id'); sdis.add_argument('--json',action='store_true')
    scf=srcsub.add_parser('conflicts',help='List same-named structured records across enabled sources')
    scf.add_argument('--json',action='store_true')

    args=p.parse_args(argv)
    try:
        if args.cmd=='verify-source': print(json.dumps(verify_source(),indent=2))
        elif args.cmd=='ingest': print(json.dumps(ingest(),indent=2))
        elif args.cmd=='search':
            rows=search(args.query,args.top_k)
            if args.json: print(json.dumps([r.to_dict() for r in rows],indent=2))
            else:
                for r in rows:
                    role='PRIMARY' if r.origin=='primary' else 'CONTEXT'
                    print(f"[{r.evidence_id}] {role} {r.source_id}/{r.authority_type}/{r.edition or '-'} PDF p.{r.page_pdf} | {r.heading} | score={r.score:.3f}\n{r.text[:900]}\n---")
        elif args.cmd=='diagnose-retrieval':
            print(json.dumps(diagnose(args.query,args.top_k),indent=2))
        elif args.cmd=='ask':
            raw=None
            if args.character: _,_,raw=load_character(args.character)
            print_answer(ask(args.question,raw,strict_audit=not args.no_audit))
        elif args.cmd=='characters':
            for x in list_characters(): print(x.name)
        elif args.cmd=='identity':
            c=connect()
            try:
                if args.identity_cmd=='report':
                    x=identity_report(c); x['fingerprint']=identity_fingerprint(c)
                elif args.identity_cmd=='show':
                    row=c.execute('SELECT * FROM canonical_entities WHERE id=?',(args.entity_id,)).fetchone()
                    if not row: raise ValueError(f'Unknown canonical entity: {args.entity_id}')
                    x=dict(row); x['mappings']=[dict(r) for r in c.execute(
                        '''SELECT cr.representation_id,cr.content_type,cr.name,cr.upstream_id,cr.upstream_path,em.status,em.method
                           FROM entity_mappings em JOIN content_records cr ON cr.id=em.content_record_id
                           WHERE em.canonical_entity_id=? ORDER BY cr.representation_id,cr.upstream_path''',(args.entity_id,))]
                else:
                    x=[dict(r) for r in c.execute(
                        '''SELECT cr.id,cr.representation_id,cr.content_type,cr.name,cr.upstream_id,cr.upstream_path,
                                  em.status,em.method,em.mapping_key,em.detail_json
                           FROM entity_mappings em JOIN content_records cr ON cr.id=em.content_record_id
                           WHERE em.status=? ORDER BY cr.representation_id,cr.content_type,cr.name,cr.upstream_path''',
                        (args.identity_cmd,))]
                if getattr(args,'json',False): print(json.dumps(x,indent=2))
                else: print(json.dumps(x,indent=2))
            finally: c.close()
        elif args.cmd=='evidence':
            c=connect()
            try:
                if args.evidence_cmd=='report':
                    x=evidence_report(c); x['fingerprint']=evidence_fingerprint(c)
                elif args.evidence_cmd=='conflicts':
                    x=[dict(r) for r in c.execute("SELECT * FROM evidence_families WHERE conflict_status='conflicted' ORDER BY id")]
                else:
                    family=c.execute('SELECT * FROM evidence_families WHERE id=?',(args.family_id,)).fetchone()
                    if not family: raise ValueError(f'Unknown evidence family: {args.family_id}')
                    x=dict(family); x['members']=[dict(r) for r in c.execute(
                        '''SELECT ec.evidence_id,ec.evidence_kind,ec.searchable,efm.representation_id,efm.evidence_role,
                                  efm.normalized_digest,dup.evidence_id exact_duplicate_of,ec.heading,ec.text
                           FROM evidence_family_members efm JOIN evidence_chunks ec ON ec.id=efm.evidence_chunk_id
                           LEFT JOIN evidence_chunks dup ON dup.id=efm.exact_duplicate_of
                           WHERE efm.family_id=? ORDER BY ec.evidence_id''',(args.family_id,))]
                    x['facts']=[dict(r) for r in c.execute('SELECT * FROM evidence_facts WHERE family_id=? ORDER BY field_key,id',(args.family_id,))]
                print(json.dumps(x,indent=2))
            finally: c.close()
        elif args.cmd=='sources':
            if args.sources_cmd=='list':
                rows=list_sources()
                print(json.dumps(rows,indent=2) if args.json else '',end='') if args.json else _print_sources(rows)
            elif args.sources_cmd=='show':
                x=show_source(args.source_id)
                if args.json: print(json.dumps(x,indent=2))
                else:
                    print(f"Source: {x['name']}\nID: {x['id']}\nType: {x['source_type']}\nAuthority type: {x['authority_type']}\nAuthority ID: {x.get('authority_id') or '-'}\nRepresentation ID: {x.get('representation_id') or '-'}\nEdition: {x['edition'] or '-'}\nApproved: {'yes' if x['approved'] else 'no'}\nEnabled: {'yes' if x['enabled'] else 'no'}\nLicense status: {x['license_status']}\nProvider: {x.get('provider') or '-'}\nProvider document: {x.get('provider_document_key') or '-'}\nPriority: {x['priority']}\nVersion: {x['version']}\nUpstream revision: {x.get('upstream_revision') or '-'}\nSnapshot file SHA-256: {x['sha256']}\nCanonical content SHA-256: {x.get('active_content_sha256') or '-'}\nContent records: {x['content_records']}\nEvidence chunks: {x['evidence_chunks']}\nStatus: VERIFIED")
            elif args.sources_cmd=='verify':
                x=verify_sources()
                if args.json: print(json.dumps(x,indent=2))
                else:
                    for item in x['sources']:
                        print(f"OK {item['source_id']} {item['version']} {item['sha256']}")
                    print(f"Verified {x['enabled_count']} enabled source(s).")
            elif args.sources_cmd=='discover':
                x=discover_open5e()
                if args.json: print(json.dumps(x,indent=2))
                else:
                    print(f"Open5e V2 discovery complete: {x['document_count']} document(s)")
                    print(f"Snapshot: {x['snapshot_path']}")
                    print(f"SHA-256: {x['snapshot_sha256']}")
                    print('No Open5e content was imported into Archie.')
            elif args.sources_cmd=='inventory':
                x=inventory_from_snapshot(args.document)
                if args.json: print(json.dumps(x,indent=2))
                else:
                    print(f"Open5e V2 inventory snapshot: {x['generated_at']}")
                    for d in x['documents']:
                        counts=d.get('resource_counts',{})
                        total=sum(v for v in counts.values() if isinstance(v,int))
                        print(f"{d['key']}: {d['name']} | resources={total} | license={_short_meta(d.get('license'))}")
                        print('  '+', '.join(f"{k}={v if v is not None else '?'}" for k,v in counts.items()))
                    print('Inventory only; no Open5e content is enabled or searchable by Archie.')
            elif args.sources_cmd=='acquire':
                output=(Path(args.output) if args.output else
                        (settings.sources_dir/'foundry'/'srd-5.2'/'raw'/'foundry-srd-5.2-release-5.2.0.json'
                         if args.provider=='foundry' else
                         settings.sources_dir/'cantilux'/'dnd-srd-json'/'raw'/'cantilux-dnd-srd-json-df536fe94c92.json'))
                x=(acquire_foundry_snapshot(output,Path(args.checkout) if args.checkout else None)
                   if args.provider=='foundry' else
                   acquire_cantilux_snapshot(output,Path(args.checkout) if args.checkout else None))
                if args.json: print(json.dumps(x,indent=2))
                elif args.provider=='cantilux':
                    print(f"Acquired pinned Cantilux bundle: {x['snapshot_path']}")
                    print(f"SHA-256: {x['snapshot_sha256']}\nDocuments: {x['documents']}\nSections: {x['sections']}\nCollections: {x['collections']}\nResources: {x['resources']}")
                else:
                    print(f"Built pinned Foundry snapshot: {x['snapshot_path']}")
                    print(f"SHA-256: {x['snapshot_sha256']}\nFiles observed: {x['upstream_files_observed']}\nRecords: {x['snapshot_records']}")
                    for pack,counts in x['packs'].items():
                        print(f"{pack}: files={counts['upstream_files_observed']} records={counts['snapshot_records']} folders={counts['folder_metadata_files']}")
            elif args.sources_cmd=='import':
                x=(import_open5e_document(args.document) if args.provider=='open5e'
                   else (import_foundry_snapshot(Path(args.document)) if args.provider=='foundry'
                         else import_cantilux_snapshot(Path(args.document))))
                if args.json: print(json.dumps(x,indent=2))
                elif args.provider in ('foundry','cantilux'):
                    print(f"Imported {x['source_id']} as non-searchable structured content.")
                    print(f"Revision: {x['upstream_revision']}\nSHA-256: {x['content_sha256']}\nRecords: {x['content_records']}\nEvidence chunks: 0")
                    diag=x['diagnostics']
                    print(f"Observed: {diag['observed']}\nAccepted: {diag['accepted']}\nRejected non-WotC: {diag['rejected_non_wotc']}\nInvalid provenance: {diag['invalid_provenance']}\nNormalization failures: {diag['normalization_failures']}")
                    print(f"{args.provider.title()} remains unavailable to answer retrieval until approved and enabled.")
                else:
                    print(f"Imported {x['source_id']} as local structured content.")
                    print(f"Version: {x['version']}\nSHA-256: {x['content_sha256']}\nRecords: {x['content_records']}\nEvidence chunks: {x['evidence_chunks']}")
                    diag=x['diagnostics']
                    print(f"Observed: {diag['observed']}\nAccepted: {diag['accepted']}\nRejected non-WotC: {diag['rejected_non_wotc']}\nInvalid provenance: {diag['invalid_provenance']}\nNormalization failures: {diag['normalization_failures']}")
                    print(f"Approved: no\nEnabled: no\nLicense status: {x['license_status']}")
                    print('Import does not grant authority. Open5e content remains unavailable to answer retrieval until approved and enabled.')
            elif args.sources_cmd=='approve':
                x=approve_source(args.source_id,license_name=args.license_name,license_url=args.license_url,note=args.note)
                if args.json: print(json.dumps(x,indent=2,default=str))
                else: print(f"Approved {args.source_id}. License: {x['license_name']} | Enabled: no")
            elif args.sources_cmd=='enable':
                x=enable_source(args.source_id)
                if args.json: print(json.dumps(x,indent=2,default=str))
                else: print(f"Enabled {args.source_id}. Evidence chunks: {x['evidence_chunks']}")
            elif args.sources_cmd=='disable':
                x=disable_source(args.source_id)
                if args.json: print(json.dumps(x,indent=2,default=str))
                else: print(f"Disabled {args.source_id}. Evidence remains local but is excluded from retrieval.")
            elif args.sources_cmd=='conflicts':
                x=source_conflicts()
                if args.json: print(json.dumps(x,indent=2))
                elif not x: print('No same-named structured-record overlaps among enabled sources.')
                else:
                    for item in x: print(f"{item['content_type']}: {item['name']} -> {', '.join(item['source_ids'])}")
        elif args.cmd=='doctor':
            srcinfo=verify_source()
            print('Source: OK',srcinfo['sha256'])
            print('Source ID:',srcinfo['source_id'])
            print('Authority:',srcinfo['authority_type'])
            print('Edition:',srcinfo['edition'])
            print('Index:', 'present' if settings.database.exists() else 'missing (run ingest)')
            print('LLM endpoint:',settings.llm_base_url)
            print('LLM model:',settings.llm_model)
            print('Strict audit:',settings.strict_audit)
            print('Top K:',settings.top_k)
            print('Neighbor radius:',settings.neighbor_radius)
    except Exception as e:
        print(f"ERROR: {e}",file=sys.stderr); return 2
    return 0

if __name__=='__main__': raise SystemExit(main())
