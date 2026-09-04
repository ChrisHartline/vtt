"""Public, lightweight API for the VTT package."""

from .config import VTTConfigurationError
from .player import PlayerGateway
from .state.models import (
    AbilityScores,
    CharacterSheet,
    EventLogEntry,
    HitPoints,
    Personality,
    PlayerAction,
    PlayerActionResult,
    PlayerContext,
    PlayerScene,
    SceneState,
)
from .state.store import StateStore
from .tools.dice import roll_dice

__all__ = [
    "AbilityScores",
    "CharacterSheet",
    "EventLogEntry",
    "HitPoints",
    "Personality",
    "PlayerAction",
    "PlayerActionResult",
    "PlayerContext",
    "PlayerGateway",
    "PlayerScene",
    "SceneState",
    "StateStore",
    "VTTConfigurationError",
    "roll_dice",
]
