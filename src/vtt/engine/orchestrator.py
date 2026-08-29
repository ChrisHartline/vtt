import os
from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_anthropic import ChatAnthropic

from .state import GameState
from ..agents.tools import GAME_TOOLS, DM_TOOLS, PLAYER_TOOLS

# Initialize LLM -- separate tool bindings per role, NOT a shared one. This is
# the actual DM/player knowledge wall: an LLM can only emit a tool call for a
# tool it was bound to, so player_node can never invoke query_adventure_module
# regardless of what the prompt says.
llm = ChatAnthropic(model="claude-sonnet-4-6", max_tokens=1024)
dm_llm_with_tools = llm.bind_tools(DM_TOOLS)
player_llm_with_tools = llm.bind_tools(PLAYER_TOOLS)

# How many of the most recent messages keep their full tool-result content.
# Anything older gets its ToolMessage content collapsed to a stub -- a RAG
# pull or state lookup already did its job narrating/resolving the turn it
# was retrieved for; it doesn't need to keep re-inflating every later prompt.
TOOL_RESULT_MEMORY = 6


def _prune_old_tool_results(messages, keep_recent: int = TOOL_RESULT_MEMORY):
    """
    Build the view of `messages` sent to the LLM, with old ToolMessage content
    collapsed. Does NOT mutate `messages` or graph state -- only what's
    actually sent to this invocation is trimmed; the full history is still
    there for the CLI transcript and the event log.
    """
    cutoff = len(messages) - keep_recent
    pruned = []
    for i, msg in enumerate(messages):
        if isinstance(msg, ToolMessage) and i < cutoff:
            pruned.append(ToolMessage(
                content="[Result omitted -- already used earlier in the scene]",
                tool_call_id=msg.tool_call_id,
            ))
        else:
            pruned.append(msg)
    return pruned


# Nodes
def dm_node(state: GameState):
    prompt = SystemMessage(content=(
        "You are the Dungeon Master for a tabletop RPG. "
        "You have access to a query_adventure_module tool to read the official module text. "
        "Use it ONLY when entering a new, unfamiliar room or when you need to look up a specific rule or stat block. "
        "Do NOT use it to resolve general player actions (like casting a spell) unless you need the module's specific ruling. "
        "IMPORTANT: always pass the `section` argument matching the module's own room/entry label for the "
        "party's current location (e.g. '12. OAKEN CABINET', 'ENTRY 5.') -- this scopes the lookup to that room "
        "only. When you set a scene with set_scene, use the module's own room label as (or within) the scene_id "
        "so you can pass the same label back into query_adventure_module later. Only omit `section` for a "
        "general rules lookup that isn't tied to a specific room. "
        "Never reveal secrets, hidden rooms, or monster stats the players haven't discovered through play. "
        "Resolve player actions fairly. Use tools to update the state or roll dice if needed. "
        "Log significant actions using the write_event tool. "
        "End your turn by waiting for the player to act."
    ))
    messages = [prompt] + _prune_old_tool_results(state["messages"])

    # Ensure the last message is a HumanMessage to satisfy Anthropic API
    from langchain_core.messages import AIMessage, HumanMessage
    if isinstance(messages[-1], AIMessage):
        messages.append(HumanMessage(content="The player has acted. Please respond and narrate the outcome."))

    response = dm_llm_with_tools.invoke(messages)
    return {"messages": [response], "current_turn": "dm"}

def player_node(state: GameState):
    prompt = SystemMessage(content=(
        "You are an AI player controlling a character in this tabletop RPG. "
        "Respond to the DM's scene in character. Describe your actions or what you say. "
        "Use tools to check your character sheet if you need to know your stats. "
        "You only know what the DM has narrated or your character would plausibly know -- "
        "you have no access to the adventure module and should never act as if you do."
    ))
    messages = [prompt] + _prune_old_tool_results(state["messages"])

    from langchain_core.messages import AIMessage, HumanMessage
    if isinstance(messages[-1], AIMessage):
        messages.append(HumanMessage(content="It is your turn. What do you do?"))

    response = player_llm_with_tools.invoke(messages)
    return {"messages": [response], "current_turn": "player"}

def tool_executor(state: GameState):
    last_msg = state["messages"][-1]
    tool_messages = []

    # Full tool map for execution -- role restriction already happened at
    # bind_tools() time above, so a role can never produce a tool_call this
    # map wouldn't be allowed to satisfy.
    tool_map = {tool.name: tool for tool in GAME_TOOLS}

    for tool_call in last_msg.tool_calls:
        tool_func = tool_map[tool_call["name"]]
        try:
            result = tool_func.invoke(tool_call["args"])
        except Exception as e:
            result = f"Error: {e}"
        tool_messages.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))
        
    return {"messages": tool_messages}

# Edge Routing
def should_continue(state: GameState):
    last_msg = state["messages"][-1]
    # If the last message invoked tools, route to the tools executor
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        return "tools"
    
    # State transition logic
    if state["current_turn"] == "dm":
        # After the DM, we usually ask the AI player
        return "player"
    elif state["current_turn"] == "player":
        # After the player acts, return END to hand control back to Human (CLI loop)
        # We will loop externally in run.py
        return END
        
    return END

def tools_return(state: GameState):
    # Go back to the agent who called the tool
    return state["current_turn"]

# Graph Definition
workflow = StateGraph(GameState)

workflow.add_node("dm", dm_node)
workflow.add_node("player", player_node)
workflow.add_node("tools", tool_executor)

workflow.set_entry_point("dm")
workflow.add_conditional_edges("dm", should_continue, {"tools": "tools", "player": "player", END: END})
workflow.add_conditional_edges("player", should_continue, {"tools": "tools", END: END, "dm": "dm"})
workflow.add_conditional_edges("tools", tools_return, {"dm": "dm", "player": "player"})

app = workflow.compile()
