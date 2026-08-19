from archie.retrieve import search, build_query_plan

CASES = [
    ("What happens when I have advantage on a roll?", {"SRD521-P008-C01", "SRD521-P176-C02"}),
    ("What does the Prone condition do?", {"SRD521-P186-C02"}),
    ("How does Concentration work?", {"SRD521-P179-C01"}),
    ("What is my spell save DC if my spellcasting ability modifier is +4 and my proficiency bonus is +2?", {"SRD521-P023-C01", "SRD521-P106-C03"}),
    ("If my Wisdom modifier is +3 and I am proficient in Perception with a +2 proficiency bonus, what is my Passive Perception?", {"SRD521-P022-C02", "SRD521-P186-C01"}),
    ("What do I roll when I try to sneak past a guard?", {"SRD521-P010-C01", "SRD521-P183-C01"}),
    ("What does the Help action do?", {"SRD521-P182-C03"}),
    ("What does Restrained do?", {"SRD521-P187-C01"}),
    ("If I am Invisible, nobody can ever target me, right?", {"SRD521-P184-C02"}),
    ("How far can I jump?", {"SRD521-P183-C02", "SRD521-P185-C01"}),
]

def test_v15_known_evidence_coverage():
    for question, acceptable in CASES:
        ids={x.evidence_id for x in search(question)}
        assert ids & acceptable, (question, ids, acceptable)

def test_comparison_retrieves_both_concepts():
    ids={x.evidence_id for x in search("What is the difference between an ability check and a saving throw?")}
    assert "SRD521-P006-C02" in ids
    assert "SRD521-P007-C01" in ids

def test_child_language_alias_armor_number():
    plan=build_query_plan("Why is my armor number important?")
    assert "armor class" in plan.aliases
    assert "armor class" in plan.concepts
    ids={x.evidence_id for x in search("Why is my armor number important?")}
    assert ids & {"SRD521-P007-C02", "SRD521-P022-C03", "SRD521-P092-C01"}

def test_neighbor_expansion_crosses_page_boundary():
    items=search("What happens when I have advantage on a roll?", top_k=1)
    ids={x.evidence_id for x in items}
    assert "SRD521-P008-C01" in ids
    # Strong page-8 hit should carry adjacent document context, including page 7 or another page-8 chunk.
    assert any(x.origin == "context" for x in items)

def test_retrieval_diagnostics_are_explainable():
    plan=build_query_plan("What does Prone do?")
    assert plan.concepts == ["prone"]
    assert "prone" in plan.terms

def test_leveled_spells_targets_spell_slot_per_turn_rule():
    ids={x.evidence_id for x in search("Can I cast two leveled spells on the same turn?")}
    assert "SRD521-P105-C01" in ids

def test_move_before_after_targets_breaking_up_move():
    ids={x.evidence_id for x in search("Can I move before and after my action?")}
    assert "SRD521-P014-C02" in ids

def test_false_natural20_premise_retrieves_attack_only_rule_and_ability_checks():
    ids={x.evidence_id for x in search("Since a natural 20 always succeeds on every ability check, what happens if I roll one?")}
    assert "SRD521-P007-C03" in ids
    assert "SRD521-P006-C02" in ids

def test_v151_reliability_queries_have_authoritative_evidence():
    cases={
        "What is my spell save DC if my spellcasting ability modifier is +4 and my proficiency bonus is +2?": {"SRD521-P023-C01","SRD521-P106-C03"},
        "How does a Long Rest work?": {"SRD521-P185-C01"},
        "Can I use a longbow while I am Prone?": {"SRD521-P186-C02"},
        "If I am Invisible, nobody can ever target me, right?": {"SRD521-P184-C02"},
    }
    for question, expected in cases.items():
        ids={x.evidence_id for x in search(question)}
        assert ids & expected, (question, ids, expected)
