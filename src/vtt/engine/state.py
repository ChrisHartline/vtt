from typing import TypedDict, Annotated, Sequence, Literal
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class GameState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    current_turn: str
