# Archie v1.0.0 Regression Results

Generated: 2026-08-19T09:17:30-05:00

## Environment

- Archie repo: /home/roblammert/git-repos/dnd-archie
- Python: Python 3.12.3
- Total tests: 38

---

## TEST-001

**Question:** What happens when I have advantage on a roll?

**Exit code:** `0`

**Elapsed:** 8 seconds

### Archie Output

```text
[VERIFIED]
When you have Advantage on a d20 test, you roll two d20s and use the higher result. For example, if you roll a 12 and a 15, you would use the 15.

Evidence-backed claims:
- If you have Advantage on a d20 Test, roll two d20s, and use the higher roll. [DIRECT] — SRD521-P176-C02 (PDF p.176)
- When a roll has Advantage, roll a second d20 when you make the roll and use the higher of the two rolls. [DIRECT] — SRD521-P008-C01 (PDF p.8)

Provenance: The answer is directly supported by the 'Advantage' definition in the Rules Glossary and the 'Roll Two d20s' section in Playing the Game.
```

---

## TEST-002

**Question:** What does the Prone condition do?

**Exit code:** `0`

**Elapsed:** 4 seconds

### Archie Output

```text
[NOT_IN_SRD]
I cannot verify the specific mechanical effects of the Prone condition from the provided SRD 5.2.1 evidence. While the evidence mentions that creatures can be forced into the Prone condition or that it is a component of the Unconscious condition, it does not define the condition's primary rules.

Provenance: The provided evidence mentions the Prone condition in several contexts (monsters, spells, and the Unconscious condition) but does not contain a definition of the condition's mechanics.
```

---

## TEST-003

**Question:** How does Concentration work?

**Exit code:** `0`

**Elapsed:** 9 seconds

### Archie Output

```text
[PARTIAL]
The provided evidence does not contain a general rule for how Concentration works. It only mentions that Concentration is required for certain actions, such as using the Marvelous Pigments item or casting a spell from a magic item.

Evidence-backed claims:
- Concentration is required to use the Marvelous Pigments item. [DIRECT] — SRD521-P230-C01 (PDF p.230)
- A user must concentrate if a spell cast from a magic item requires Concentration. [DIRECT] — SRD521-P206-C01 (PDF p.206)

Provenance: The SRD evidence provided mentions Concentration as a requirement for specific items and spells but does not define the general mechanics of the Concentration condition.
```

---

## TEST-004

**Question:** What is my spell save DC if my spellcasting ability modifier is +4 and my proficiency bonus is +2?

**Exit code:** `0`

**Elapsed:** 9 seconds

### Archie Output

```text
[PARTIAL]
I found relevant SRD material, but my evidence audit could not support every rules claim in the generated answer. I am refusing to guess. Try asking a narrower version of the question.

Provenance: Fail-closed audit rejected claim indexes: [1]
```

---

## TEST-005

**Question:** If my Wisdom modifier is +3 and I am proficient in Perception with a +2 proficiency bonus, what is my Passive Perception?

**Exit code:** `0`

**Elapsed:** 13 seconds

### Archie Output

```text
[PARTIAL]
I found relevant SRD material, but my evidence audit could not support every rules claim in the generated answer. I am refusing to guess. Try asking a narrower version of the question.

Provenance: Fail-closed audit rejected claim indexes: [2, 3]
```

---

## TEST-006

**Question:** Can I cast two leveled spells on the same turn?

**Exit code:** `0`

**Elapsed:** 3 seconds

### Archie Output

```text
[NOT_IN_SRD]
I cannot verify if you can cast two leveled spells on the same turn from the provided SRD 5.2.1 evidence.

Provenance: The provided evidence does not contain the general rules for actions, turns, or the specific limitations on casting multiple spells per turn.
```

---

## TEST-007

**Question:** Can I use a longbow while I am Prone?

**Exit code:** `0`

**Elapsed:** 3 seconds

### Archie Output

```text
[NOT_IN_SRD]
I cannot verify if you can use a longbow while Prone from the provided SRD 5.2.1 evidence.

Provenance: The provided evidence contains monster statistics and descriptions but does not include the general rules for the Prone condition or the rules for using ranged weapons while Prone.
```

---

## TEST-008

**Question:** What happens if I roll a natural 20 on an attack?

**Exit code:** `0`

**Elapsed:** 9 seconds

### Archie Output

```text
[VERIFIED]
A natural 20 on an attack roll is a Critical Hit, which means the attack hits regardless of any modifiers or the target's Armor Class (AC).

Evidence-backed claims:
- If you roll a 20 on the d20 (called a “natural 20”) for an attack roll, the attack hits regardless of any modifiers or the target’s AC. [DIRECT] — SRD521-P007-C03 (PDF p.7)
- This is called a Critical Hit. [DIRECT] — SRD521-P007-C03 (PDF p.7)

Provenance: The answer is directly supported by the 'Rolling 20 or 1' section of the provided SRD evidence.
```

---

## TEST-009

**Question:** What happens if I roll a natural 1 on an attack?

**Exit code:** `0`

**Elapsed:** 7 seconds

### Archie Output

```text
[VERIFIED]
If you roll a natural 1 on the d20 for an attack roll, the attack misses regardless of any modifiers or the target's AC.

Evidence-backed claims:
- If you roll a 1 on the d20 (a "natural 1") for an attack roll, the attack misses regardless of any modifiers or the target’s AC. [DIRECT] — SRD521-P007-C03 (PDF p.7)

Provenance: The rule for a natural 1 on an attack roll is directly stated in the Playing the Game section.
```

---

## TEST-010

**Question:** Does Advantage stack if I get it from two different things?

**Exit code:** `0`

**Elapsed:** 7 seconds

### Archie Output

```text
[VERIFIED]
No, Advantage does not stack. If multiple situations grant you Advantage on a roll, you still only roll two d20s and use the higher result.

Evidence-backed claims:
- If multiple situations affect a roll and they all grant Advantage on it, you still roll only two d20s. [DIRECT] — SRD521-P008-C01 (PDF p.8)

Provenance: The rule regarding Advantage stacking is directly stated in the 'Roll Two d20s' section of the Playing the Game rules.
```

---

## TEST-011

**Question:** What happens if I have both Advantage and Disadvantage?

**Exit code:** `0`

**Elapsed:** 8 seconds

### Archie Output

```text
[VERIFIED]
If a roll has both Advantage and Disadvantage, the roll has neither of them, and you roll only one d20.

Evidence-backed claims:
- If circumstances cause a roll to have both Advantage and Disadvantage, the roll has neither of them, and you roll one d20. [DIRECT] — SRD521-P008-C01 (PDF p.8)

Provenance: The rule for overlapping Advantage and Disadvantage is directly stated in the 'They Don't Stack' section of the provided evidence.
```

---

## TEST-012

**Question:** What does Heroic Inspiration do?

**Exit code:** `0`

**Elapsed:** 9 seconds

### Archie Output

```text
[VERIFIED]
You can expend Heroic Inspiration to reroll any die immediately after rolling it, and you must use the new roll. You can only have one instance of Heroic Inspiration at a time.

Evidence-backed claims:
- If you have Heroic Inspiration, you can expend it to reroll any die immediately after rolling it, and you must use the new roll. [DIRECT] — SRD521-P008-C01 (PDF p.8), SRD521-P183-C01 (PDF p.183)
- You can never have more than one instance of Heroic Inspiration. [DIRECT] — SRD521-P008-C01 (PDF p.8)

Provenance: The rules for Heroic Inspiration are directly stated in the Playing the Game and Rules Glossary sections.
```

---

## TEST-013

**Question:** Can I reroll both dice when I have Advantage and use Heroic Inspiration?

**Exit code:** `0`

**Elapsed:** 8 seconds

### Archie Output

```text
[VERIFIED]
No, you can only reroll one of the two dice. When you have Advantage and use Heroic Inspiration, you must choose which single die to reroll, not both.

Evidence-backed claims:
- When you have Advantage or Disadvantage and something in the game lets you reroll or replace the d20, you can reroll or replace only one die, not both. [DIRECT] — SRD521-P008-C02 (PDF p.8)

Provenance: The rule regarding interactions with rerolls explicitly states that only one die can be replaced when Advantage or Disadvantage is active.
```

---

## TEST-014

**Question:** What is Armor Class?

**Exit code:** `0`

**Elapsed:** 9 seconds

### Archie Output

```text
[VERIFIED]
Armor Class (AC) is a value that represents your base defense when wearing a specific type of armor. For monsters, AC includes their natural armor, Dexterity, gear, and other defenses.

Evidence-backed claims:
- The Armor Class column tells you what your base AC is when you wear a type of armor. [DIRECT] — SRD521-P092-C01 (PDF p.92)
- A monster’s Armor Class (AC) includes its natural armor, Dexterity, gear, and other defenses. [DIRECT] — SRD521-P254-C03 (PDF p.254)

Provenance: The answer is directly supported by the Equipment and Monsters sections of the SRD.
```

---

## TEST-015

**Question:** Why is my armor number important?

**Exit code:** `0`

**Elapsed:** 4 seconds

### Archie Output

```text
[NOT_IN_SRD]
I cannot verify why your armor number is important from the provided SRD 5.2.1 evidence. The text mentions Armor Class (AC) for monsters and specific types of armor like Mithral Armor, but it does not define a specific 'armor number' or its general importance for a player character.

Provenance: The provided evidence does not contain a definition or explanation for a general 'armor number' for players.
```

---

## TEST-016

**Question:** What do I roll when I try to sneak past a guard?

**Exit code:** `0`

**Elapsed:** 3 seconds

### Archie Output

```text
[NOT_IN_SRD]
I can't verify the specific roll for sneaking past a guard from SRD 5.2.1. While the rules mention that you take the Hide action to hide, they do not specify the exact ability check or roll required for that action.

Provenance: The provided evidence mentions the Hide action but does not define the mechanics or specific rolls associated with it.
```

---

## TEST-017

**Question:** What does proficiency do?

**Exit code:** `0`

**Elapsed:** 10 seconds

### Archie Output

```text
[VERIFIED]
Proficiency represents the impact of training on a creature's capabilities. It allows you to add your Proficiency Bonus to a d20 test when you are proficient in a skill, a saving throw, or with an item you are using.

Evidence-backed claims:
- Proficiency reflects the impact that training has on a creature's capabilities. [DIRECT] — SRD521-P008-C02 (PDF p.8)
- The Proficiency Bonus is applied to a D20 Test when the creature has proficiency in a skill, in a saving throw, or with an item that the creature uses to make the D20 Test. [DIRECT] — SRD521-P008-C02 (PDF p.8)

Provenance: The answer is directly supported by the 'Proficiency' section on page 8 of the SRD.
```

---

## TEST-018

**Question:** Do I add my proficiency bonus twice if I am proficient in two relevant skills?

**Exit code:** `0`

**Elapsed:** 8 seconds

### Archie Output

```text
[VERIFIED]
No, you do not add your Proficiency Bonus twice. If a rule allows you to make a check using two different skills and you are proficient in both, you only add your Proficiency Bonus once.

Evidence-backed claims:
- If a rule allows you to make a check using two skills and you are proficient in both, you do not add your Proficiency Bonus twice. [DIRECT] — SRD521-P008-C03 (PDF p.8)

Provenance: The SRD explicitly states that you do not add the Proficiency Bonus twice if you are proficient in both skills for a check that allows for either.
```

---

## TEST-019

**Question:** What is a saving throw?

**Exit code:** `0`

**Elapsed:** 10 seconds

### Archie Output

```text
[VERIFIED]
A saving throw (or 'save') is an attempt to evade or resist a threat, such as a fiery explosion, a blast of poisonous gas, or a spell trying to invade your mind. You don't normally choose to make a save; you must make one because your character or a monster is at risk.

Evidence-backed claims:
- A saving throw represents an attempt to evade or resist a threat, such as a fiery explosion, a blast of poisonous gas, or a spell trying to invade your mind. [DIRECT] — SRD521-P007-C01 (PDF p.7)
- You don’t normally choose to make a save; you must make one because your character or a monster (if you’re the GM) is at risk. [DIRECT] — SRD521-P007-C01 (PDF p.7)

Provenance: The definition and context of saving throws are directly stated in the 'Saving Throws' section of the provided SRD evidence.
```

---

## TEST-020

**Question:** What is the difference between an ability check and a saving throw?

**Exit code:** `0`

**Elapsed:** 8 seconds

### Archie Output

```text
[PARTIAL]
An ability check represents a creature using talent and training to try to overcome a challenge, such as picking a lock or deciphering a cipher. While the SRD 5.2.1 evidence provided describes ability checks in detail, it does not contain the specific rules for saving throws.

Evidence-backed claims:
- An ability check represents a creature using talent and training to try to overcome a challenge, such as forcing open a stuck door, picking a lock, entertaining a crowd, or deciphering a cipher. [DIRECT] — SRD521-P006-C02 (PDF p.6)

Provenance: The evidence provided defines ability checks but does not contain any information regarding saving throws.
```

---

## TEST-021

**Question:** What does the Dodge action do?

**Exit code:** `0`

**Elapsed:** 10 seconds

### Archie Output

```text
[VERIFIED]
When you take the Dodge action, any attack roll made against you has Disadvantage if you can see the attacker, and you make Dexterity saving throws with Advantage until the start of your next turn. You lose these benefits if you are Incapacitated or if your Speed is 0.

Evidence-backed claims:
- If you take the Dodge action, you gain the following benefits: until the start of your next turn, any attack roll made against you has Disadvantage if you can see the attacker, and you make Dexterity saving throws with Advantage. [DIRECT] — SRD521-P181-C02 (PDF p.181)
- You lose these benefits if you have the Incapacitated condition or if your Speed is 0. [DIRECT] — SRD521-P181-C02 (PDF p.181)

Provenance: The Dodge action's mechanics and conditions are directly stated in the Rules Glossary.
```

---

## TEST-022

**Question:** What happens when I take the Help action?

**Exit code:** `0`

**Elapsed:** 7 seconds

### Archie Output

```text
[PARTIAL]
I found relevant SRD material, but my evidence audit could not support every rules claim in the generated answer. I am refusing to guess. Try asking a narrower version of the question.

Provenance: Fail-closed audit rejected claim indexes: [0]
```

---

## TEST-023

**Question:** Can I move before and after my action?

**Exit code:** `0`

**Elapsed:** 7 seconds

### Archie Output

```text
[VERIFIED]
Yes, you can use some or all of your movement to move between attacks if you have a feature that gives you more than one attack as part of the Attack action.

Evidence-backed claims:
- If you move on your turn and have a feature, such as Extra Attack, that gives you more than one attack as part of the Attack action, you can use some or all of that movement to move between those attacks. [DIRECT] — SRD521-P177-C02 (PDF p.177)

Provenance: The rules explicitly state that movement can be used between multiple attacks provided the character has a feature allowing for more than one attack.
```

---

## TEST-024

**Question:** How far can I jump?

**Exit code:** `0`

**Elapsed:** 11 seconds

### Archie Output

```text
[VERIFIED]
The distance you can jump depends on the type of jump you are making. For a Long Jump (horizontal), you can jump a distance equal to your movement, but a standing Long Jump is limited to half that distance; for a High Jump (vertical), you can jump a distance equal to your movement, but a standing High Jump is limited to half that distance.

Evidence-backed claims:
- Each foot of the jump costs a foot of movement. [DIRECT] — SRD521-P185-C01 (PDF p.185)
- When you make a standing Long Jump, you can leap only half that distance. [DIRECT] — SRD521-P185-C01 (PDF p.185)
- When you make a standing High Jump, you can jump only half that distance. [DIRECT] — SRD521-P183-C02 (PDF p.183)

Provenance: The answer is derived from the movement costs and standing jump limitations found in the Rules Glossary.
```

---

## TEST-025

**Question:** What happens when I am Invisible?

**Exit code:** `0`

**Elapsed:** 11 seconds

### Archie Output

```text
[VERIFIED]
While you are Invisible, you have Advantage on Initiative rolls, your attack rolls have Advantage, and attack rolls against you have Disadvantage. You are also considered concealed, meaning you aren't affected by effects that require a target to be seen unless the creator can somehow see you.

Evidence-backed claims:
- If you're Invisible when you roll Initiative, you have Advantage on the roll. [DIRECT] — SRD521-P184-C02 (PDF p.184)
- You aren't affected by any effect that requires its target to be seen unless the effect's creator can somehow see you. [DIRECT] — SRD521-P184-C02 (PDF p.184)
- Attack rolls against you have Disadvantage, and your attack rolls have Advantage. [DIRECT] — SRD521-P184-C02 (PDF p.184)

Provenance: The effects of the Invisible condition are directly stated in the Rules Glossary.
```

---

## TEST-026

**Question:** What does Restrained do?

**Exit code:** `0`

**Elapsed:** 4 seconds

### Archie Output

```text
[NOT_IN_SRD]
I cannot verify the specific mechanical effects of the Restrained condition from SRD 5.2.1. While the provided evidence describes various ways a creature can become Restrained (such as by a Net, Manacles, or a Gorgon's breath), it does not define the general rules for the condition itself.

Provenance: The provided evidence mentions the Restrained condition in the context of specific items and monsters, but does not contain a general definition of the condition's mechanics.
```

---

## TEST-027

**Question:** What does Grappled do?

**Exit code:** `0`

**Elapsed:** 12 seconds

### Archie Output

```text
[VERIFIED]
While you have the Grappled condition, your Speed is 0 and cannot increase. You also have Disadvantage on attack rolls against any target other than the creature grappling you, and the grappler can drag or carry you when it moves.

Evidence-backed claims:
- Your Speed is 0 and can't increase. [DIRECT] — SRD521-P182-C02 (PDF p.182)
- You have Disadvantage on attack rolls against any target other than the grappler. [DIRECT] — SRD521-P182-C02 (PDF p.182)
- The grappler can drag or carry you when it moves, but every foot of movement costs it 1 extra foot unless you are Tiny or two or more sizes smaller than it. [DIRECT] — SRD521-P182-C02 (PDF p.182)

Provenance: The effects of the Grappled condition are explicitly listed in the Rules Glossary.
```

---

## TEST-028

**Question:** What is difficult terrain?

**Exit code:** `0`

**Elapsed:** 9 seconds

### Archie Output

```text
[VERIFIED]
Difficult Terrain is a condition where every foot of movement in that space costs 1 extra foot. For example, moving 5 feet through Difficult Terrain would cost 10 feet of movement.

Evidence-backed claims:
- If a space is Difficult Terrain, every foot of movement in that space costs 1 extra foot. [DIRECT] — SRD521-P181-C01 (PDF p.181), SRD521-P014-C02 (PDF p.14)
- Moving 5 feet through Difficult Terrain costs 10 feet of movement. [DIRECT] — SRD521-P181-C01 (PDF p.181)

Provenance: The definition and movement cost of Difficult Terrain are directly stated in the Rules Glossary and Playing the Game sections.
```

---

## TEST-029

**Question:** How does a Short Rest work?

**Exit code:** `0`

**Elapsed:** 11 seconds

### Archie Output

```text
[VERIFIED]
A Short Rest is a 1-hour period of downtime where you do nothing more strenuous than reading, talking, eating, or standing watch. When you finish the rest, you can spend one or more Hit Point Dice to regain Hit Points by rolling the dice and adding your Constitution modifier (minimum of 1 Hit Point per die).

Evidence-backed claims:
- A Short Rest is a 1-hour period of downtime, during which a creature does nothing more strenuous than reading, talking, eating, or standing watch. [DIRECT] — SRD521-P187-C02 (PDF p.187)
- To start a Short Rest, you must have at least 1 Hit Point. [DIRECT] — SRD521-P187-C02 (PDF p.187)
- When you finish the rest, you can spend one or more Hit Point Dice to regain Hit Points by rolling the die and adding your Constitution modifier (minimum of 1 Hit Point). [DIRECT] — SRD521-P187-C02 (PDF p.187)

Provenance: The answer is directly supported by the 'Short Rest' entry in the Rules Glossary.
```

---

## TEST-030

**Question:** How does a Long Rest work?

**Exit code:** `0`

**Elapsed:** 21 seconds

### Archie Output

```text
[VERIFIED]
A Long Rest is a period of at least 8 hours where you sleep for at least 6 hours and perform no more than 2 hours of light activity. Upon finishing, you regain all Hit Points, restore reduced ability scores, decrease your Exhaustion level by 1, and recharge any special features that specify a Long Rest as their recharge condition.

Evidence-backed claims:
- A Long Rest is a period of at least 8 hours where you sleep for at least 6 hours and perform no more than 2 hours of light activity. [DIRECT] — SRD521-P185-C01 (PDF p.185)
- During a Long Rest, you have the Unconscious condition while sleeping. [DIRECT] — SRD521-P185-C01 (PDF p.185)
- You must wait at least 16 hours before starting another Long Rest. [DIRECT] — SRD521-P185-C01 (PDF p.185)
- To start a Long Rest, you must have at least 1 Hit Point. [DIRECT] — SRD521-P185-C01 (PDF p.185)
- When you finish the rest, you regain all lost Hit Points and all spent Hit Point Dice. [DIRECT] — SRD521-P185-C01 (PDF p.185)
- If any of your ability scores were reduced, they return to normal. [DIRECT] — SRD521-P185-C01 (PDF p.185)
- If you have the Exhaustion condition, its level decreases by 1. [DIRECT] — SRD521-P185-C01 (PDF p.185)
- Some features are recharged by a Long Rest in the way specified in their description. [DIRECT] — SRD521-P185-C01 (PDF p.185)

Provenance: The answer is directly supported by the 'Long Rest' entry in the Rules Glossary (SRD521-P185-C01).
```

---

## TEST-031

**Question:** How does the Artificer class work?

**Exit code:** `0`

**Elapsed:** 3 seconds

### Archie Output

```text
[NOT_IN_SRD]
I cannot verify the rules for the Artificer class from the provided SRD 5.2.1 evidence.

Provenance: The provided evidence does not contain a description of the Artificer class.
```

---

## TEST-032

**Question:** What are the rules for the Circle of the Moon druid?

**Exit code:** `0`

**Elapsed:** 4 seconds

### Archie Output

```text
[NOT_IN_SRD]
I cannot verify the rules for the Circle of the Moon druid from the provided SRD 5.2.1 evidence. The evidence only contains information regarding the Circle of the Land druid subclass.

Provenance: The provided evidence packet does not contain any information regarding the Circle of the Moon subclass.
```

---

## TEST-033

**Question:** How does the Hexblade warlock work?

**Exit code:** `0`

**Elapsed:** 3 seconds

### Archie Output

```text
[NOT_IN_SRD]
I cannot verify the rules for the Hexblade warlock from the provided SRD 5.2.1 evidence. The evidence covers the core Warlock class features, such as Pact Magic and Eldritch Invocations, but does not include specific subclass information like Hexblade.

Provenance: The provided evidence contains the base Warlock class but does not contain the Hexblade subclass information.
```

---

## TEST-034

**Question:** What does the Booming Blade spell do?

**Exit code:** `0`

**Elapsed:** 3 seconds

### Archie Output

```text
[NOT_IN_SRD]
I can't verify the effects of the Booming Blade spell from SRD 5.2.1.

Provenance: The provided evidence does not contain the description or rules for the Booming Blade spell.
```

---

## TEST-035

**Question:** What are the rules for flanking?

**Exit code:** `0`

**Elapsed:** 2 seconds

### Archie Output

```text
[NOT_IN_SRD]
I cannot verify the rules for flanking from SRD 5.2.1, as that term is not defined in the provided evidence.

Provenance: The provided SRD 5.2.1 evidence does not contain a definition or rules for 'flanking'.
```

---

## TEST-036

**Question:** Since a natural 20 always succeeds on every ability check, what happens if I roll one?

**Exit code:** `0`

**Elapsed:** 4 seconds

### Archie Output

```text
[NOT_IN_SRD]
I cannot verify that from SRD 5.2.1. The provided evidence does not state that a natural 20 always succeeds on every ability check.

Provenance: The supplied SRD evidence describes how to perform D20 Tests but does not contain a rule regarding natural 20s automatically succeeding on ability checks.
```

---

## TEST-037

**Question:** Because two sources of Advantage let me roll three d20s, which one do I keep?

**Exit code:** `0`

**Elapsed:** 8 seconds

### Archie Output

```text
[VERIFIED]
You still only roll two d20s. If multiple situations grant you Advantage, they do not stack, and you simply use the higher of the two dice.

Evidence-backed claims:
- If multiple situations affect a roll and they all grant Advantage on it, you still roll only two d20s. [DIRECT] — SRD521-P008-C01 (PDF p.8)
- When a roll has Advantage, you roll two d20s and use the higher roll. [DIRECT] — SRD521-P006-C01 (PDF p.6), SRD521-P176-C02 (PDF p.176)

Provenance: The SRD explicitly states that Advantage does not stack and that you only roll two dice even if multiple sources of Advantage apply.
```

---

## TEST-038

**Question:** If I am Invisible, nobody can ever target me, right?

**Exit code:** `0`

**Elapsed:** 4 seconds

### Archie Output

```text
[NOT_IN_SRD]
I cannot verify the rules for the Invisible condition from the provided SRD 5.2.1 evidence.

Provenance: The provided evidence does not contain the definition or mechanical effects of the Invisible condition.
```

---

# Run Complete

- Completed: 2026-08-19T09:22:13-05:00
- Tests attempted: 38
