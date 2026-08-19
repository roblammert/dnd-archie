from __future__ import annotations
from pathlib import Path
import yaml
from .config import settings

ALLOWED_EXT={'.yaml','.yml'}

def load_character(path_or_name: str) -> tuple[Path,dict,str]:
    p=Path(path_or_name)
    if not p.is_absolute() and not p.exists():
        p=settings.characters/p
    p=p.resolve()
    base=settings.characters.resolve()
    try:p.relative_to(base)
    except ValueError: raise ValueError('Character file must live under data/characters/.')
    if p.suffix.lower() not in ALLOWED_EXT: raise ValueError('Character file must be YAML.')
    raw=p.read_text(encoding='utf-8')
    data=yaml.safe_load(raw) or {}
    if not isinstance(data,dict): raise ValueError('Character YAML root must be a mapping.')
    return p,data,raw

def list_characters():
    settings.characters.mkdir(parents=True,exist_ok=True)
    return sorted([p for p in settings.characters.iterdir() if p.suffix.lower() in ALLOWED_EXT])
