from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

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
    inventory: List[str] = Field(default_factory=list)
    spells: List[str] = Field(default_factory=list)
    conditions: List[str] = Field(default_factory=list)
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
    events: List[EventLogEntry] = Field(default_factory=list)


class PlayerScene(BaseModel):
    """The intentionally small, player-visible projection of a scene."""

    scene_id: str
    description: str
    active_entities: List[str] = Field(default_factory=list)


class PlayerContext(BaseModel):
    """Identity bound by a host before player-facing operations are exposed."""

    campaign_id: str
    player_id: str
    character_id: str


class PlayerAction(BaseModel):
    """An immutable player request awaiting authoritative DM resolution."""

    action_id: str
    campaign_id: str
    player_id: str
    character_id: str
    description: str = Field(min_length=1)
    target: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PlayerActionResult(BaseModel):
    """The public portion of the authority's resolution of a player action."""

    action_id: str
    campaign_id: str
    status: Literal["pending", "resolved", "rejected"]
    public_outcome: Optional[str] = None
    roll: Optional[str] = None
    resolved_at: Optional[datetime] = None
