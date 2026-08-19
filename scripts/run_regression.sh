#!/usr/bin/env bash
set -u

OUTPUT="${1:-archie-regression-results.md}"

tests=(
"What happens when I have advantage on a roll?"
"What does the Prone condition do?"
"How does Concentration work?"
"What is my spell save DC if my spellcasting ability modifier is +4 and my proficiency bonus is +2?"
"If my Wisdom modifier is +3 and I am proficient in Perception with a +2 proficiency bonus, what is my Passive Perception?"
"Can I cast two leveled spells on the same turn?"
"Can I use a longbow while I am Prone?"
"What happens if I roll a natural 20 on an attack?"
"What happens if I roll a natural 1 on an attack?"
"Does Advantage stack if I get it from two different things?"
"What happens if I have both Advantage and Disadvantage?"
"What does Heroic Inspiration do?"
"Can I reroll both dice when I have Advantage and use Heroic Inspiration?"
"What is Armor Class?"
"Why is my armor number important?"
"What do I roll when I try to sneak past a guard?"
"What does proficiency do?"
"Do I add my proficiency bonus twice if I am proficient in two relevant skills?"
"What is a saving throw?"
"What is the difference between an ability check and a saving throw?"
"What does the Dodge action do?"
"What happens when I take the Help action?"
"Can I move before and after my action?"
"How far can I jump?"
"What happens when I am Invisible?"
"What does Restrained do?"
"What does Grappled do?"
"What is difficult terrain?"
"How does a Short Rest work?"
"How does a Long Rest work?"
"How does the Artificer class work?"
"What are the rules for the Circle of the Moon druid?"
"How does the Hexblade warlock work?"
"What does the Booming Blade spell do?"
"What are the rules for flanking?"
"Since a natural 20 always succeeds on every ability check, what happens if I roll one?"
"Because two sources of Advantage let me roll three d20s, which one do I keep?"
"If I am Invisible, nobody can ever target me, right?"
)

total=${#tests[@]}

cat > "$OUTPUT" <<EOF
# Archie v1.5.0 Regression Results

Generated: $(date --iso-8601=seconds)

## Environment

- Archie repo: $(pwd)
- Python: $(python --version 2>&1)
- Archie version: $(grep -E '^version[[:space:]]*=' pyproject.toml | head -1 | sed 's/^[^"]*"//; s/".*$//')
- Total tests: $total

---

EOF

echo "Running $total Archie regression tests..."
echo "Results: $OUTPUT"
echo

for i in "${!tests[@]}"; do
    number=$((i + 1))
    question="${tests[$i]}"

    printf '[%02d/%02d] %s\n' "$number" "$total" "$question"

    start=$(date +%s)

    set +e
    result=$(python -m archie.cli ask "$question" 2>&1)
    rc=$?
    set -e

    end=$(date +%s)
    elapsed=$((end - start))

    {
        printf '## TEST-%03d\n\n' "$number"
        printf '**Question:** %s\n\n' "$question"
        printf '**Exit code:** `%d`\n\n' "$rc"
        printf '**Elapsed:** %d seconds\n\n' "$elapsed"
        printf '### Archie Output\n\n'
        printf '```text\n'
        printf '%s\n' "$result"
        printf '```\n\n'
        printf '%s\n\n' '---'
    } >> "$OUTPUT"

    if [[ $rc -eq 0 ]]; then
        echo "         completed in ${elapsed}s"
    else
        echo "         ERROR (exit $rc) after ${elapsed}s"
    fi
done

{
    echo "# Run Complete"
    echo
    echo "- Completed: $(date --iso-8601=seconds)"
    echo "- Tests attempted: $total"
} >> "$OUTPUT"

echo
echo "========================================"
echo "Regression run complete."
echo "Output: $OUTPUT"
echo "========================================"
