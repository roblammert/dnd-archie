from archie.retrieve import _fts_query, detect_concepts, search


def ids(query, top_k=8):
    return {e.evidence_id for e in search(query, top_k)}


def test_natural_language_stopwords_do_not_bury_advantage_rule():
    assert _fts_query("What happens when I have advantage on a roll?") == '"advantage" OR "roll"'
    found = ids("What happens when I have advantage on a roll?")
    assert {"SRD521-P008-C01", "SRD521-P176-C02"} & found


def test_prone_prefers_glossary_definition():
    assert "SRD521-P186-C02" in ids("What does the Prone condition do?")


def test_restrained_prefers_glossary_definition():
    assert "SRD521-P187-C01" in ids("What does Restrained do?")


def test_concentration_prefers_general_rule():
    assert "SRD521-P179-C01" in ids("How does Concentration work?")


def test_help_action_definition_is_retrieved():
    assert "SRD521-P182-C03" in ids("What happens when I take the Help action?")


def test_child_language_armor_number_maps_to_armor_class():
    found = ids("Why is my armor number important?")
    assert "SRD521-P007-C02" in found


def test_spell_save_dc_formula_is_retrieved():
    found = ids("What is my spell save DC if my spellcasting ability modifier is +4 and my proficiency bonus is +2?")
    assert {"SRD521-P023-C01", "SRD521-P106-C03"} & found


def test_passive_perception_formula_is_retrieved():
    found = ids("If my Wisdom modifier is +3 and I am proficient in Perception with a +2 proficiency bonus, what is my Passive Perception?")
    assert "SRD521-P022-C02" in found


def test_multi_concept_comparison_retrieves_both_sides():
    found = ids("What is the difference between an ability check and a saving throw?", 10)
    assert any(e in found for e in {"SRD521-P006-C02", "SRD521-P006-C03"})
    assert "SRD521-P007-C01" in found


def test_false_premise_invisible_still_retrieves_definition():
    assert "SRD521-P184-C02" in ids("If I am Invisible, nobody can ever target me, right?")
