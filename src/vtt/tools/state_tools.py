from ..state.store import StateStore
from ..state.models import EventLogEntry, CharacterSheet, SceneState

_store: StateStore | None = None


def configure_store(store: StateStore) -> None:
    """Bind the privileged DM/state tools to host-configured storage."""
    global _store
    _store = store


def get_store() -> StateStore:
    """Return the configured store, resolving VTT_DATA_DIR lazily if needed."""
    global _store
    if _store is None:
        _store = StateStore()
    return _store

def read_character(character_id: str) -> str:
    """Reads a character sheet by ID."""
    char = get_store().get_character(character_id)
    if char:
        return char.model_dump_json(indent=2)
    return f"Character '{character_id}' not found."

def update_character(character_id: str, patch: dict) -> str:
    """Updates a character using a JSON patch (dictionary)."""
    success = get_store().update_character(character_id, patch)
    if success:
        return f"Successfully updated character '{character_id}'."
    return f"Failed to update character '{character_id}'. Validation error or not found."

def write_event(actor: str, event_type: str, description: str, outcome: str, session: int = 1, event_id: str = "evt_auto", roll: str = None) -> str:
    """Writes an event to the immutable event log. Type can be 'action', 'movement', etc."""
    try:
        from uuid import uuid4
        if event_id == "evt_auto":
            event_id = f"evt_{uuid4().hex[:8]}"

        event = EventLogEntry(
            event_id=event_id,
            session=session,
            actor=actor,
            type=event_type,
            description=description,
            roll=roll,
            outcome=outcome
        )
        get_store().log_event(event)
        return f"Event logged successfully: {event_id}"
    except Exception as e:
        return f"Error logging event: {e}"

def get_scene() -> str:
    """Reads the current scene state."""
    scene = get_store().get_scene()
    if scene:
        return scene.model_dump_json(indent=2)
    return "No active scene found."

def set_scene(scene_id: str, description: str, active_entities: list) -> str:
    """Sets or updates the current scene."""
    try:
        scene = SceneState(
            scene_id=scene_id,
            description=description,
            active_entities=active_entities,
            events=[] # Reset events for the new scene or preserve them if needed
        )
        get_store().save_scene(scene)
        return "Scene updated successfully."
    except Exception as e:
        return f"Error setting scene: {e}"
