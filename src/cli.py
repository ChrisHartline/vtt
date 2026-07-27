
import os
import sys
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage

# Ensure src module is importable from script dir
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from src.engine.orchestrator import app
from src.state.store import StateStore
from src.state.models import CharacterSheet

def setup_mock_data():
    store = StateStore()
    
    # Create sample wizard if not exists
    if not store.get_character("rhea"):
        rhea = {
            "id": "rhea",
            "name": "Rhea",
            "class_name": "Wizard",  # Ensure this matches the pydantic initialization correctly, 
            "level": 3,
            "hp": { "current": 14, "max": 18 },
            "armor_class": 12,
            "abilities": { "str": 8, "dex": 14, "con": 12, "int": 17, "wis": 13, "cha": 10 },
            "inventory": ["Spellbook", "Wand"],
            "spells": ["Magic Missile", "Shield"],
            "conditions": [],
            "personality": { "traits": ["analytical", "cautious"], "goals": ["recover lost knowledge"] }
        }
        # In pydantic we used alias="class", but we can pass `class` in a dict to initialize
        rhea_init = rhea.copy()
        rhea_init["class"] = rhea_init.pop("class_name")
        store.save_character(CharacterSheet(**rhea_init))
        print("Mock character 'rhea' created.")

def print_messages(messages):
    for msg in messages:
        role = "Human/System" if isinstance(msg, HumanMessage) else "AI"
        
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                print(f"[Tool Action: {tc['name']} -> {tc['args']}]")
            continue
        if type(msg).__name__ == "ToolMessage":
            print(f"[Tool Result: {msg.content}]")
            continue
        if type(msg).__name__ == "SystemMessage":
            continue
            
        print(f"\n{role}: {msg.content}\n")

def main():
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable not set. Please create a .env file.")
        return

    print("\nAI Multi-Agent Tabletop RPG Engine (CLI MVP)")
    print("Setting up game state...")
    setup_mock_data()
    
    state = {
        "messages": [],
        "current_turn": "dm"
    }

    state["messages"].append(HumanMessage(content="Start the session. Describe the environment and introduce Rhea the Wizard, a player character. Wait for Rhea to state her action."))

    while True:
        try:
            print("\n--- Engine Processing Loop ---")
            # Invoke passes the state through the graph until END
            result = app.invoke(state)
            
            # Print only new messages added during this graph execution step
            new_msgs = result["messages"][len(state["messages"]):]
            print_messages(new_msgs)
            
            state["messages"] = result["messages"]
            state["current_turn"] = result["current_turn"]
            
            print("\n--- Handing control to Human ---")
            human_input = input("Human [steer game] or ENTER to let the AI party continue: ")
            
            if human_input.lower() in ['q', 'quit', 'exit']:
                break
                
            if human_input.strip():
                state["messages"].append(HumanMessage(content=human_input))
                
            # If we reached END from player node, current_turn doesn't transition to DM automatically in the edges 
            # unless we intervene. But actually LangGraph invoke returns the final state.
            # To re-trigger, we force current_turn to dm
            state["current_turn"] = "dm"

        except Exception as e:
            print(f"\nEngine Error: {e}")
            break

if __name__ == "__main__":
    main()
