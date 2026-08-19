import pytest
from archie.characters import load_character

def test_example_character_loads():
    p,data,raw=load_character('example-ranger.yaml')
    assert data['class']=='Ranger'
    assert 'Rowan' in raw

def test_character_escape_rejected():
    with pytest.raises(ValueError): load_character('../../README.md')
