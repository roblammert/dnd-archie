from archie.ingest import ingest
from archie.retrieve import search

def test_ingest_and_find_advantage(tmp_path):
    info=ingest()
    assert int(info['chunks'])>300
    hits=search('advantage disadvantage',5)
    assert hits
    assert all(h.evidence_id.startswith('SRD521-P') for h in hits)
    assert any('advantage' in h.text.lower() for h in hits)

def test_find_prone():
    hits=search('Prone condition',8)
    assert hits
    assert any('prone' in h.text.lower() for h in hits)
