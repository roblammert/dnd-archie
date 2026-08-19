#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

ROOT="$PWD"
VENV_PYTHON="$ROOT/.venv/bin/python"

if [[ -x "$VENV_PYTHON" ]]; then
    PYTHON="$VENV_PYTHON"
else
    PYTHON="$(command -v python3 || command -v python || true)"
fi

if [[ -z "${PYTHON:-}" ]]; then
    echo "ERROR: No Python interpreter found." >&2
    exit 2
fi

export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

OUTPUT="archie-regression-results.md"

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

{
    echo "# Archie $("$PYTHON" -c 'import archie; print(archie.__version__)') Regression Results"
    echo
    echo "Generated: $(date --iso-8601=seconds)"
    echo
    echo "- Archie repo: $ROOT"
    echo "- Python version: $("$PYTHON" --version 2>&1)"
    echo "- Python executable: $("$PYTHON" -c 'import sys; print(sys.executable)')"
    echo "- Branch: $(git -C "$ROOT" branch --show-current 2>/dev/null || echo unknown)"
    echo "- Total tests: ${#tests[@]}"
    echo
    echo "---"
    echo
} > "$OUTPUT"

for i in "${!tests[@]}"; do
    n=$((i + 1))
    q="${tests[$i]}"
    start=$(date +%s)

    set +e
    result=$("$PYTHON" -m archie.cli ask "$q" 2>&1)
    rc=$?
    set -e

    elapsed=$(($(date +%s) - start))

    printf '[%02d/%02d] %s (%ss)\n' \
        "$n" "${#tests[@]}" "$q" "$elapsed"

    {
        printf '## TEST-%03d\n\n' "$n"
        printf '**Question:** %s\n\n' "$q"
        printf '**Exit code:** `%d`\n\n' "$rc"
        printf '**Elapsed:** %d seconds\n\n' "$elapsed"
        printf '### Archie Output\n\n'
        printf '```text\n%s\n```\n\n' "$result"
        printf '%s\n\n' '---'
    } >> "$OUTPUT"
done

echo
echo "Regression complete: $OUTPUT"
