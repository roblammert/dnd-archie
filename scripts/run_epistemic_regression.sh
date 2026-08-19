#!/usr/bin/env bash
set -u
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
OUTPUT="archie-epistemic-regression-results.md"
tests=(
"If I am Invisible, nobody can ever target me, right?"
"Because two sources of Advantage let me roll three d20s, which one do I keep?"
"If the rules don't say I can't do it, that means I can, right?"
"If the SRD doesn't mention this spell, does that mean the spell doesn't exist?"
"If Prone gives me Disadvantage with a bow, that means I am definitely allowed to fire one while Prone, right?"
"If an Invisible creature can't be seen, attacks against it automatically miss, correct?"
"If the rules only describe natural 20s on attacks, that means natural 20s do nothing special on ability checks, right?"
)
{
  echo "# Archie $(python -c 'import archie; print(archie.__version__)') Epistemic Regression Results"
  echo
  echo "Generated: $(date --iso-8601=seconds)"
  echo
  echo "- Archie repo: $(pwd)"
  echo "- Python: $(python --version 2>&1)"
  echo "- Total tests: ${#tests[@]}"
  echo
  echo "---"
} > "$OUTPUT"
for i in "${!tests[@]}"; do
  n=$((i+1)); q="${tests[$i]}"; start=$(date +%s)
  set +e; result=$(python -m archie.cli ask "$q" 2>&1); rc=$?; set -e
  elapsed=$(($(date +%s)-start))
  printf '[%02d/%02d] %s (%ss)\n' "$n" "${#tests[@]}" "$q" "$elapsed"
  {
    printf '## TEST-%03d\n\n' "$n"
    printf '**Question:** %s\n\n' "$q"
    printf '**Exit code:** `%d`\n\n' "$rc"
    printf '**Elapsed:** %d seconds\n\n' "$elapsed"
    printf '### Archie Output\n\n```text\n%s\n```\n\n---\n\n' "$result"
  } >> "$OUTPUT"
done
echo "Epistemic regression complete: $OUTPUT"
