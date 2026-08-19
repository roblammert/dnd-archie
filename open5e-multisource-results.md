# Archie v2.0.0-alpha.4 Multi-Source Acceptance Results

Generated: 2026-08-19T16:15:41-05:00

## Branch
```text
v2.0_dev
```

## Sources before
```text
ID                   TYPE              AUTHORITY            EDITION   APPROVED  ENABLED  LICENSE   VERSION              CHUNKS
open5e:srd-2024      open5e_snapshot   approved_supplement  2024      no        no       missing   open5e-v2-b6caac3e9527 0
srd521               local_document    official_srd         2024      yes       yes      present   5.2.1                1067
```

## Discovery + import
```text
Open5e V2 discovery complete: 24 document(s)
Snapshot: data/discovery/open5e/open5e-discovery-20260819T211703Z.json
SHA-256: 03edc93e8dce3c2ec57160bd6a095729a57032efc92bb6fa3ad34a36eba027ae
No Open5e content was imported into Archie.
Imported open5e:srd-2024 as local structured content.
Version: open5e-v2-b6caac3e9527
SHA-256: b6caac3e9527319fcf651820e859fec0e7a11197d4c1128c70e996e8a72d676f
Records: 1740
Evidence chunks: 0
Approved: no
Enabled: no
License status: missing
Import does not grant authority. Open5e content remains unavailable to answer retrieval in alpha.4.
```

## Explicit approval + enablement
```text
Approved open5e:srd-2024. License: Creative Commons Attribution 4.0 International | Enabled: no
Enabled open5e:srd-2024. Evidence chunks: 2896
OK open5e:srd-2024 open5e-v2-b6caac3e9527 ffe19459cc7b10c8bf5d037b026f2651e820045a935863f66f15b2580dc3512e
OK srd521 5.2.1 8974902d109d6e63672d7c490bde9ccf052410503d9cfa768237154fbc5e3d87
Verified 2 enabled source(s).
```

## Enabled source state
```text
Source: System Reference Document 5.2
ID: open5e:srd-2024
Type: open5e_snapshot
Authority: approved_supplement
Edition: 2024
Approved: yes
Enabled: yes
License status: present
Provider: open5e
Provider document: srd-2024
Priority: 80
Version: open5e-v2-b6caac3e9527
Snapshot file SHA-256: ffe19459cc7b10c8bf5d037b026f2651e820045a935863f66f15b2580dc3512e
Canonical content SHA-256: b6caac3e9527319fcf651820e859fec0e7a11197d4c1128c70e996e8a72d676f
Content records: 1740
Evidence chunks: 2896
Status: VERIFIED
```

## Database trust check
```text
enabled sources: ['srd521', 'open5e:srd-2024']
open5e records: 1740
open5e evidence chunks: 2896
2014 enabled evidence: 0
```

## Retrieval sample
```text
[O5E-SRD-2024-MAGIC-ITEMS-SRD-2024-NECKLACE-OF-FIREBALLS-178D58C2-C01] PRIMARY open5e:srd-2024/approved_supplement/2024 PDF p.None | Magic Items — Necklace of Fireballs | score=9.889
Name: Necklace of Fireballs
Content type: magic_items
category.key: wondrous-item
category.name: Wondrous Item
cost: 0.00
desc: This necklace has 1d6 + 3 beads hanging from it. You can take a Magic action to detach a bead and throw it up to 60 feet away. When it reaches the end of its trajectory, the bead detonates as a level 3 Fireball (save DC 15). You can hurl multiple beads, or even the whole necklace, at one time. When you do so, increase the damage of the Fireball by 1d6 for each bead after the first (maximum 12d6).
key: srd-2024_necklace-of-fireballs
name: Necklace of Fireballs
rarity.key: rare
rarity.name: Rare
rarity.rank: 3
requires_attunement: false
size.key: tiny
size.name: Tiny
weight: 0.000
weight_unit: lb
---
[O5E-SRD-2024-MAGIC-ITEMS-SRD-2024-WAND-OF-FIREBALLS-9F62F4D9-C01] PRIMARY open5e:srd-2024/approved_supplement/2024 PDF p.None | Magic Items — Wand of Fireballs | score=9.577
Name: Wand of Fireballs
Content type: magic_items
attunement_detail: Requires Attunement by a Spellcaster
category.key: wand
category.name: Wand
cost: 0.00
desc: This wand has 7 charges. While holding it, you can expend no more than 3 charges to cast Fireball (save DC 15) from it. For 1 charge, you cast the level 3 version of the spell. You can increase the spell's level by 1 for each additional charge you expend. Regaining Charges. The wand regains 1d6 + 1 expended charges daily at dawn. If you expend the wand's last charge, roll 1d20. On a 1, the wand crumbles into ashes and is destroyed.
key: srd-2024_wand-of-fireballs
name: Wand of Fireballs
rarity.key: rare
rarity.name: Rare
rarity.rank: 3
requires_attunement: true
size.key: tiny
size.name: Tiny
weight: 0.000
weight_unit: lb
---
[SRD521-P315-C02] PRIMARY srd521/official_srd/2024 PDF p.315 | Monsters | score=9.157
Fiery Mace.

Melee Attack Roll: +14, reach 10 ft.

Hit: 22
(4d6 + 8) Force damage plus 21 (6d6) Fire damage.

Hellfire Spellcasting (Recharge 4–6).

The pit fiend
casts Fireball (level 5 version) twice, requiring no Material components and using Charisma as the spellcasting
ability (spell save DC 21).

It can replace one Fireball
with Hold Monster (level 7 version) or Wall of Fire.

Planetar
Planetar
Large Celestial (Angel), Lawful Good
AC 19
---
[O5E-SRD-2024-SPELLS-SRD-2024-DELAYED-BLAST-FIREBALL-3DBFCE31-C02] PRIMARY open5e:srd-2024/approved_supplement/2024 PDF p.None | Spells — Delayed Blast Fireball | score=8.950
shape_size: 20
shape_size_unit: feet
shape_type: sphere
somatic: true
target_count: 1
target_type: creature
verbal: true
---
[O5E-SRD-2024-SPELLS-SRD-2024-FIREBALL-EBDBB3E8-C01] PRIMARY open5e:srd-2024/approved_supplement/2024 PDF p.None | Spells — Fireball | score=8.705
Name: Fireball
Content type: spells
attack_roll: false
casting_options[1].damage_roll: 9d6
casting_options[1].type: slot_level_4
casting_options[2].damage_roll: 10d6
casting_options[2].type: slot_level_5
casting_options[3].damage_roll: 11d6
casting_options[3].type: slot_level_6
casting_options[4].damage_roll: 12d6
casting_options[4].type: slot_level_7
casting_options[5].damage_roll: 13d6
casting_options[5].type: slot_level_8
casting_options[6].damage_roll: 14d6
casting_options[6].type: slot_level_9
casting_time: action
classes[1].key: srd-2024_sorcerer
classes[1].name: Sorcerer
classes[2].key: srd-2024_wizard
classes[2].name: Wizard
concentration: false
damage_roll: 8d6
damage_types: fire
desc: A bright streak flashes from you to a point you choose within range and then blossoms with a low roar into a fiery explosion. Each creature in a 20-foot-radius Sphere centered on that point makes 
---
[SRD521-P250-C03] PRIMARY srd521/official_srd/2024 PDF p.250 | Magic Items | score=8.653
The table indicates how many charges you
must expend to cast the spell.

Spell
Charge
Cost
Command (“flee” or “grovel” only)
Fear (60-foot Cone)
Regaining Charges. The wand regains 1d6 +
1 expended charges daily at dawn. If you expend
the wand’s last charge, roll 1d20. On a 1, the wand
crumbles into ashes and is destroyed.
Wand of Fireballs
Wand, Rare (Requires Attunement by a Spellcaster)
This wand has 7 charges. While holding it, you can
expend no more than 3 charges to cast Fireball (save
DC 15) from it. For 1 charge, you cast the level 3 version of the spell. You can increase the spell’s level by
1 for each additional charge you expend.
---
[O5E-SRD-2024-SPELLS-SRD-2024-DELAYED-BLAST-FIREBALL-3DBFCE31-C01] PRIMARY open5e:srd-2024/approved_supplement/2024 PDF p.None | Spells — Delayed Blast Fireball | score=8.518
Name: Delayed Blast Fireball
Content type: spells
attack_roll: false
casting_options[1].damage_roll: 13d6
casting_options[1].type: slot_level_8
casting_options[2].damage_roll: 14d6
casting_options[2].type: slot_level_9
casting_time: action
classes[1].key: srd-2024_sorcerer
classes[1].name: Sorcerer
classes[2].key: srd-2024_wizard
classes[2].name: Wizard
concentration: true
damage_roll: 12d6
damage_types: fire
desc: A beam of yellow light flashes from you, then condenses at a chosen point within range as a glowing bead for the duration. When the spell ends, the bead explodes, and each creature in a 20-foot-radius Sphere centered on that point makes a Dexterity saving throw. A creature takes Fire damage equal to the total accumulated damage on a failed save or half as much damage on a successful one. The spell's base damage is 12d6, and the damage increases by 1d6 whenever your turn ends a
---
[SRD521-P233-C01] PRIMARY srd521/official_srd/2024 PDF p.233 | Magic Items | score=8.142
System Reference Document 5.2.1
Necklace of Fireballs
Wondrous Item, Rare
This necklace has 1d6 + 3 beads hanging from it. You can take a Magic action to detach a bead and
throw it up to 60 feet away. When it reaches the end
of its trajectory, the bead detonates as a level 3 Fireball (save DC 15). You can hurl multiple beads, or even the whole
necklace, at one time. When you do so, increase the
damage of the Fireball by 1d6 for each bead after
the first (maximum 12d6). Necklace of Prayer Beads
Wondrous Item, Rare (Requires Attunement by a
Cleric, Druid, or Paladin)
This necklace has 1d4 + 2 magic beads made from
aquamarine, black pearl, or topaz. It also has many
nonmagical beads made from stones such as amber,
bloodstone, citrine, coral, jade, pearl, or quartz. If a
magic bead is removed from the necklace, that bead
loses its magic. Six types of magic beads exist. The GM decides the
typ
---
[O5E-SRD-2024-MAGIC-ITEMS-SRD-2024-NECKLACE-OF-ADAPTATION-DDCDA3ED-C01] CONTEXT open5e:srd-2024/approved_supplement/2024 PDF p.None | Magic Items — Necklace of Adaptation | score=-999.000
Name: Necklace of Adaptation
Content type: magic_items
category.key: wondrous-item
category.name: Wondrous Item
cost: 0.00
desc: While wearing this necklace, you can breathe normally in any environment, and you have Advantage on saving throws made to avoid or end the Poisoned condition.
key: srd-2024_necklace-of-adaptation
name: Necklace of Adaptation
rarity.key: uncommon
rarity.name: Uncommon
rarity.rank: 2
requires_attunement: true
size.key: tiny
size.name: Tiny
weight: 0.000
weight_unit: lb
---
[O5E-SRD-2024-MAGIC-ITEMS-SRD-2024-NECKLACE-OF-PRAYER-BEADS-562AFDD7-C01] CONTEXT open5e:srd-2024/approved_supplement/2024 PDF p.None | Magic Items — Necklace of Prayer Beads | score=-999.000
Name: Necklace of Prayer Beads
Content type: magic_items
attunement_detail: Requires Attunement by a Cleric, Druid, or Paladin
category.key: wondrous-item
category.name: Wondrous Item
cost: 0.00
desc: This necklace has 1d4 + 2 magic beads made from aquamarine, black pearl, or topaz. It also has many nonmagical beads made from stones such as amber, bloodstone, citrine, coral, jade, pearl, or quartz. If a magic bead is removed from the necklace, that bead loses its magic.

Six types of magic beads exist. The GM decides the type of each bead on the necklace or determines it randomly by rolling on the table below. A necklace can have more than one bead of the same type. To use one, you must be wearing the necklace. Each bead contains a spell that you can cast from it as a Bonus Action (using your spell save DC if a save is necessary). Once a magic bead's spell is cast, that bead can't be use
---
[O5E-SRD-2024-MAGIC-ITEMS-SRD-2024-WAND-OF-ENEMY-DETECTION-6A335690-C01] CONTEXT open5e:srd-2024/approved_supplement/2024 PDF p.None | Magic Items — Wand of Enemy Detection | score=-999.000
Name: Wand of Enemy Detection
Content type: magic_items
category.key: wand
category.name: Wand
cost: 0.00
desc: This wand has 7 charges. While holding it, you can take a Magic action to expend 1 charge. For 1 minute, you know the direction of the nearest creature Hostile to you within 60 feet, but not its distance from you. The wand can sense the presence of Hostile creatures that are Invisible, ethereal, disguised, or hidden, as well as those in plain sight. The effect ends if you stop holding the wand. Regaining Charges. The wand regains 1d6 + 1 expended charges daily at dawn. If you expend the wand's last charge, roll 1d20. On a 1, the wand crumbles into ashes and is destroyed.
key: srd-2024_wand-of-enemy-detection
name: Wand of Enemy Detection
rarity.key: rare
rarity.name: Rare
rarity.rank: 3
requires_attunement: true
size.key: tiny
size.name: Tiny
weight: 0.000
weight_unit: lb
---
[O5E-SRD-2024-MAGIC-ITEMS-SRD-2024-WAND-OF-LIGHTNING-BOLTS-EE1C4911-C01] CONTEXT open5e:srd-2024/approved_supplement/2024 PDF p.None | Magic Items — Wand of Lightning Bolts | score=-999.000
Name: Wand of Lightning Bolts
Content type: magic_items
attunement_detail: Requires Attunement by a Spellcaster
category.key: wand
category.name: Wand
cost: 0.00
desc: This wand has 7 charges. While holding it, you can expend no more than 3 charges to cast Lightning Bolt (save DC 15) from it. For 1 charge, you cast the level 3 version of the spell. You can increase the spell's level by 1 for each additional charge you expend. Regaining Charges. The wand regains 1d6 + 1 expended charges daily at dawn. If you expend the wand's last charge, roll 1d20. On a 1, the wand crumbles into ashes and is destroyed.
key: srd-2024_wand-of-lightning-bolts
name: Wand of Lightning Bolts
rarity.key: rare
rarity.name: Rare
rarity.rank: 3
requires_attunement: true
size.key: tiny
size.name: Tiny
weight: 0.000
weight_unit: lb
---
[SRD521-P315-C01] CONTEXT srd521/official_srd/2024 PDF p.315 | Monsters | score=-999.000
System Reference Document 5.2.1
MOD SAVE
MOD SAVE
MOD SAVE
Str 26 +8
+8
Dex 14 +2
+8
Con 24 +7
+7
Int 22 +6
+6
Wis 18 +4
+10
Cha 24 +7
+7
Skills Perception +10, Persuasion +19
Resistances Cold
Immunities Fire, Poison; Poisoned
Senses Truesight 120 ft.; Passive Perception 20
Languages Infernal; telepathy 120 ft. CR 20 (XP 25,000; PB +6)
Traits
Diabolical Restoration. If the pit fiend dies outside the
Nine Hells, its body disappears in sulfurous smoke, and
it gains a new body instantly, reviving with all its Hit
Points somewhere in the Nine Hells. Fear Aura. The pit fiend emanates an aura in a 20-
foot Emanation while it doesn’t have the Incapacitated
condition. Wisdom Saving Throw: DC 21, any enemy
that starts its turn in the aura. Failure: The target has
the Frightened condition until the start of its next turn. Success: The target is immune to this pit fiend’s aura
for 24 hours. Legenda
---
[SRD521-P315-C03] CONTEXT srd521/official_srd/2024 PDF p.315 | Monsters | score=-999.000
Planetar
Planetar
Large Celestial (Angel), Lawful Good
AC 19

Initiative +10 (20)
HP 262 (21d10 + 147)
Speed 40 ft., Fly 120 ft. (hover)
MOD SAVE
MOD SAVE
MOD SAVE
Str 24 +7
+12
Dex 20 +5
+5
Con 24 +7
+12
Int 19 +4
+4
Wis 22 +6
+11
Cha 25 +7
+12
Skills Perception +11
Resistances Radiant
Immunities Charmed, Exhaustion, Frightened
Senses Truesight 120 ft.; Passive Perception 21
Languages All; telepathy 120 ft.
CR 16 (XP 15,000; PB +5)
Traits
Divine Awareness. The planetar knows if it hears a lie.
Exalted Restoration. If the planetar dies outside Mount
Celestia, its body disappears, and it gains a new body
instantly, reviving with all its Hit Points somewhere in
Mount Celestia.
Magic Resistance. The planetar has Advantage on saving throws against spells and other magical effects.
Actions
Multiattack. The planetar makes three Radiant Sword
attacks or uses Holy Burst twice.
Radiant Sword. Mel
---
```

## Structured overlap report
```text
No same-named structured-record overlaps among enabled sources.
```
