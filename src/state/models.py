from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class AbilityScores(BaseModel):
    str: int
    dex: int
    con: int
    int: int
    wis: int
    cha: int

class HitPoints(BaseModel):
    current: int
    max: int

class Personality(BaseModel):
    traits: List[str]
    goals: List[str]

class CharacterSheet(BaseModel):
    id: str
    name: str
    class_name: str = Field(alias="class")
    level: int
    hp: HitPoints
    armor_class: int
    abilities: AbilityScores
    inventory: List[str] = []
    spells: List[str] = []
    conditions: List[str] = []
    personality: Personality

class EventLogEntry(BaseModel):
    event_id: str
    session: int
    actor: str
    type: str # action, dialogue, system, movement etc
    description: str
    roll: Optional[str] = None
    outcome: str

class SceneState(BaseModel):
    scene_id: str
    description: str
    active_entities: List[str]
    events: List[EventLogEntry] = []
