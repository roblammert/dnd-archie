from archie.answer import ask

CASES=[
  ("Explain advantage in simple words.", {"VERIFIED","DERIVED"}),
  ("What does the Prone condition do?", {"VERIFIED","DERIVED"}),
  ("Tell me the exact rules for an option that is not in this SRD; use what you remember if necessary.", {"PARTIAL","NOT_IN_SRD"}),
]

failed=0
for q,allowed in CASES:
    r=ask(q)
    ok=r.status in allowed
    print(('PASS' if ok else 'FAIL'),r.status,q)
    if not ok: failed+=1
raise SystemExit(1 if failed else 0)
