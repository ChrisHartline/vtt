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
def query_adventure_module(topic: str) -> str:
    """Queries the RAG database for official adventure module text, rules, and secrets."""
    return rag_system.query_knowledge(topic)

GAME_TOOLS = [roll_dice, read_character, update_character, write_event, get_scene, set_scene, query_adventure_module]
