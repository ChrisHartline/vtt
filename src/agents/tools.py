from langchain_core.tools import tool
from ..tools import dice
from ..tools import state_tools
from ..rag.retriever import RAGRetriever

rag_system = RAGRetriever()

@tool
def roll_dice(expression: str) -> str:
    """Evaluates a dice expression like '1d20+5'."""
    return dice.roll_dice(expression)

@tool
def read_character(character_id: str) -> str:
    """Reads a character sheet."""
    return state_tools.read_character(character_id)

@tool
def update_character(character_id: str, patch: dict) -> str:
    """Updates a character using a JSON patch (dictionary)."""
    return state_tools.update_character(character_id, patch)

@tool
def write_event(actor: str, event_type: str, description: str, outcome: str) -> str:
    """Writes an event to the immutable event log. Useful to finalize actions."""
    return state_tools.write_event(actor, event_type, description, outcome)

@tool
def get_scene() -> str:
    """Reads the current scene state."""
    return state_tools.get_scene()

@tool
def set_scene(scene_id: str, description: str, active_entities: list) -> str:
    """Sets or updates the current scene."""
    return state_tools.set_scene(scene_id, description, active_entities)

@tool
def query_adventure_module(topic: str, section: str = None) -> str:
    """Queries the RAG database for official adventure module text, rules, and secrets.

    Pass `section` matching the current scene's room/entry label (e.g.
    "12. OAKEN CABINET", "ENTRY 5.") to scope the search to that room only --
    this is how you avoid pulling in text from rooms the party hasn't reached
    yet. Only omit `section` for general rules lookups that aren't tied to a
    specific room; omitting it for a room-specific question risks leaking
    unrelated rooms/spoilers into your answer.
    """
    return rag_system.query_knowledge(topic, section=section)

GAME_TOOLS = [roll_dice, read_character, update_character, write_event, get_scene, set_scene, query_adventure_module]

# DM: full access, including the module-secrets lookup and world-state mutation.
DM_TOOLS = GAME_TOOLS

# Player/NPC characters: no access to query_adventure_module (that's DM-only
# knowledge -- module secrets, hidden rooms, monster stats) and no world-state
# mutation (write_event/set_scene are the DM's job). Scene context reaches
# players through the DM's narration in the shared message history, not by
# querying state directly.
PLAYER_TOOLS = [roll_dice, read_character, update_character]
