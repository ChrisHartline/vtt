import pytest
from pydantic import ValidationError
from vtt.state.models import CharacterSheet, EventLogEntry, HitPoints, AbilityScores, Personality

def test_valid_character_sheet():
    char_data = {
        "id": "test_rhea",
        "name": "Rhea",
        "class": "Wizard",
        "level": 3,
        "hp": {"current": 14, "max": 18},
        "armor_class": 12,
        "abilities": {"str": 8, "dex": 14, "con": 12, "int": 17, "wis": 13, "cha": 10},
        "inventory": ["Spellbook"],
        "spells": [],
        "conditions": [],
        "personality": {"traits": ["smart"], "goals": ["learn"]}
    }
    
    char = CharacterSheet(**char_data)
    assert char.id == "test_rhea"
    assert char.class_name == "Wizard" # tests the alias resolution
    assert char.hp.current == 14

def test_invalid_character_sheet_missing_required():
    with pytest.raises(ValidationError):
        char_data = {
            "name": "Rhea" # missing everything else
        }
        CharacterSheet(**char_data)

def test_valid_event_log():
    event_data = {
        "event_id": "evt_123",
        "session": 1,
        "actor": "rhea",
        "type": "action",
        "description": "Casts a spell",
        "outcome": "Goblin takes 5 damage"
    }
    
    event = EventLogEntry(**event_data)
    assert event.event_id == "evt_123"
    assert event.type == "action"
    assert event.roll is None
