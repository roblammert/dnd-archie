from __future__ import annotations

# Canonical SRD concepts used only to improve retrieval. These mappings never
# establish rules; they only help locate the authoritative SRD text.
CONCEPTS = {
    # Conditions
    **{name.lower(): {"canonical": name, "sections": ("Rules Glossary",), "marker": f"{name} [Condition]"}
       for name in (
           "Blinded", "Charmed", "Deafened", "Exhaustion", "Frightened",
           "Grappled", "Incapacitated", "Invisible", "Paralyzed", "Petrified",
           "Poisoned", "Prone", "Restrained", "Stunned", "Unconscious"
       )},
    # Actions
    **{name.lower(): {"canonical": name, "sections": ("Rules Glossary", "Playing the Game"), "marker": f"{name} [Action]"}
       for name in (
           "Attack", "Dash", "Disengage", "Dodge", "Help", "Hide", "Influence",
           "Magic", "Ready", "Search", "Study", "Utilize"
       )},
    "advantage": {"canonical": "Advantage", "sections": ("Rules Glossary", "Playing the Game")},
    "disadvantage": {"canonical": "Disadvantage", "sections": ("Rules Glossary", "Playing the Game")},
    "armor class": {"canonical": "Armor Class", "sections": ("Playing the Game", "Character Creation", "Rules Glossary", "Equipment")},
    "ability check": {"canonical": "Ability Checks", "sections": ("Playing the Game",)},
    "saving throw": {"canonical": "Saving Throws", "sections": ("Playing the Game", "Rules Glossary")},
    "concentration": {"canonical": "Concentration", "sections": ("Rules Glossary", "Spells")},
    "passive perception": {"canonical": "Passive Perception", "sections": ("Character Creation", "Rules Glossary")},
    "heroic inspiration": {"canonical": "Heroic Inspiration", "sections": ("Playing the Game", "Rules Glossary")},
    "proficiency": {"canonical": "Proficiency", "sections": ("Playing the Game", "Rules Glossary")},
    "difficult terrain": {"canonical": "Difficult Terrain", "sections": ("Playing the Game", "Rules Glossary")},
    "short rest": {"canonical": "Short Rest", "sections": ("Rules Glossary", "Playing the Game")},
    "long rest": {"canonical": "Long Rest", "sections": ("Rules Glossary", "Playing the Game")},
    "initiative": {"canonical": "Initiative", "sections": ("Rules Glossary", "Playing the Game", "Character Creation")},
    "spell save dc": {"canonical": "Spell save DC", "sections": ("Spells", "Character Creation")},
    "spell attack": {"canonical": "Spell attack", "sections": ("Spells", "Character Creation")},
    "spell slot per turn": {"canonical": "One Spell with a Spell Slot per Turn", "sections": ("Spells",)},
    "breaking up your move": {"canonical": "Breaking Up Your Move", "sections": ("Playing the Game",)},
    "natural 20": {"canonical": "Rolling 20 or 1", "sections": ("Playing the Game",)},
    "natural 1": {"canonical": "Rolling 20 or 1", "sections": ("Playing the Game",)},
    "jump": {"canonical": "Jump", "sections": ("Rules Glossary", "Playing the Game")},
    "long jump": {"canonical": "Long Jump", "sections": ("Rules Glossary",)},
    "high jump": {"canonical": "High Jump", "sections": ("Rules Glossary",)},
}

# Child-friendly / informal language aliases. These map wording to search
# concepts only; they are not treated as rules facts.
ALIASES = {
    "armor number": ("armor class",),
    "armour number": ("armor class",),
    "defense number": ("armor class",),
    "defence number": ("armor class",),
    "ac number": ("armor class",),
    "health": ("hit points",),
    "health points": ("hit points",),
    "hp": ("hit points",),
    "sneak": ("hide", "stealth"),
    "sneaking": ("hide", "stealth"),
    "sneak past": ("hide", "stealth"),
    "hide from": ("hide", "stealth"),
    "magic difficulty": ("spell save dc",),
    "spell difficulty": ("spell save dc",),
    "passive awareness": ("passive perception",),
    "to hit": ("attack roll",),
    "leveled spell": ("spell slot per turn",),
    "levelled spell": ("spell slot per turn",),
    "two leveled spells": ("spell slot per turn",),
    "two levelled spells": ("spell slot per turn",),
    "move before and after": ("breaking up your move",),
}
