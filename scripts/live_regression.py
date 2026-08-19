"""Small smoke regression. For the full suite use scripts/run_regression.sh."""
from archie.answer import ask

CASES=[
  ("Explain advantage in simple words.", {"VERIFIED","DERIVED"}),
  ("What does the Prone condition do?", {"VERIFIED","DERIVED"}),
  ("How does Concentration work?", {"VERIFIED","DERIVED"}),
  ("Can I cast two leveled spells on the same turn?", {"VERIFIED","DERIVED"}),
  ("What are the rules for the Circle of the Moon druid?", {"PARTIAL","NOT_IN_SRD"}),
]

failed=0
for q,allowed in CASES:
    r=ask(q)
    ok=r.status in allowed
    print(('PASS' if ok else 'FAIL'),r.status,q)
    if not ok: failed+=1
raise SystemExit(1 if failed else 0)
