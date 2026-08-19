from pathlib import Path
from types import SimpleNamespace

import pytest

import archie.characters as characters_module
from archie.characters import load_character


FIXTURES = Path(__file__).parent / "fixtures" / "characters"


def _test_settings(characters_dir: Path):
    return SimpleNamespace(
        characters=characters_dir,
    )


def test_example_character_loads(tmp_path, monkeypatch):
    fixture = FIXTURES / "example-ranger.yaml"

    assert fixture.exists()

    characters_dir = tmp_path / "characters"
    characters_dir.mkdir()

    target = characters_dir / "example-ranger.yaml"
    target.write_text(
        fixture.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        characters_module,
        "settings",
        _test_settings(characters_dir),
    )

    path, data, raw = load_character("example-ranger.yaml")

    assert path == target
    assert data["player_name"] == "Test Player"
    assert data["character_name"] == "Example Ranger"
    assert data["level"] == 1
    assert data["class"] == "Ranger"
    assert data["species"] == "Elf"

    assert "Example Ranger" in raw


def test_missing_character_raises_error(tmp_path, monkeypatch):
    characters_dir = tmp_path / "characters"
    characters_dir.mkdir()

    monkeypatch.setattr(
        characters_module,
        "settings",
        _test_settings(characters_dir),
    )

    with pytest.raises(FileNotFoundError):
        load_character("does-not-exist.yaml")
