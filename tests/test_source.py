from archie.source import verify_source

def test_source_hash_matches_manifest():
    assert verify_source()['ok'] is True
