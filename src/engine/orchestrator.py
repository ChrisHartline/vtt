import os
from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_anthropic import ChatAnthropic

from .state import GameState
from ..agents.tools import GAME_TOOLS

# Initialize LLM
llm = ChatAnthropic(model="claude-sonnet-4-6", max_tokens=1024)
llm_with_tools = llm.bind_tools(GAME_TOOLS)

# Nodes
def dm_node(state: GameState):
    prompt = SystemMessage(content=(
        "You are the Dungeon Master for a tabletop RPG. "
        "You have access to a query_adventure_module tool to read the official module text. "
        "Use it ONLY when entering a new, unfamiliar room or when you need to look up a specific rule or stat block. "
        "Do NOT use it to resolve general player actions (like casting a spell) unless you need the module's specific ruling. "
        "If the retrieved text is irrelevant to the current scene, ignore it and rely on the active scene description. "
        "Resolve player actions fairly. Use tools to update the state or roll dice if needed. "
        "Log significant actions using the write_event tool. "
        "End your turn by waiting for the player to act."
    ))
    messages = [prompt] + state["messages"]
    
    # Ensure the last message is a HumanMessage to satisfy Anthropic API
    from langchain_core.messages import AIMessage, HumanMessage
    if isinstance(messages[-1], AIMessage):
        messages.append(HumanMessage(content="The player has acted. Please respond and narrate the outcome."))
        
    response = llm_with_tools.invoke(messages)
    return {"messages": [response], "current_turn": "dm"}

def player_node(state: GameState):
    prompt = SystemMessage(content=(
        "You are an AI player controlling a character in this tabletop RPG. "
        "Respond to the DM's scene in character. Describe your actions or what you say. "
        "Use tools to check your character sheet if you need to know your stats."
    ))
    messages = [prompt] + state["messages"]
    
    from langchain_core.messages import AIMessage, HumanMessage
    if isinstance(messages[-1], AIMessage):
        messages.append(HumanMessage(content="It is your turn. What do you do?"))
        
    response = llm_with_tools.invoke(messages)
    return {"messages": [response], "current_turn": "player"}

def tool_executor(state: GameState):
    last_msg = state["messages"][-1]
    tool_messages = []
    
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
