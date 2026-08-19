from archie.ingest import ingest
from archie.retrieve import search
from archie.db import connect

def test_search_rejects_index_bound_to_wrong_source():
    ingest()
    c=connect()
    with c:
        c.execute("UPDATE metadata SET value='wrong' WHERE key='source_sha256'")
    c.close()
    try:
        search('advantage')
        assert False, 'search should reject stale index'
    except RuntimeError as e:
        assert 'does not match' in str(e)
    finally:
        ingest()
