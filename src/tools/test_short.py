from typing import Annotated
from langgraph.graph import StateGraph, MessagesState
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import ToolRuntime
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field
from llm.llm import llm
from langchain.tools import tool
from langchain_core.runnables import RunnableConfig


class CustomerAgentState(MessagesState):
    user_id: str = Field(default="")
    preferences: dict = Field(default={})
    user_name: str = Field(default="")
    last_topic: str = Field(default="")


@tool('save_user_info')
def save_user_info(runtime: ToolRuntime[CustomerAgentState]) -> str:
    """Save user info to state based on conversation."""
    messages = runtime.state.get("messages", [])
    # Get the last user message
    last_msg = messages[-1] if messages else ""
    content = last_msg.content if hasattr(last_msg, 'content') else str(last_msg)

    print(f"[DEBUG] save_user_info called with content: {content}")

    # Extract user name from message (simple demo - look for "name is" pattern)
    if "name is" in content.lower():
        name = content.lower().split("name is")[-1].strip().split()[0]
        runtime.state["user_name"] = name.capitalize()
        runtime.state["last_topic"] = "name_introduction"
        print(f"[DEBUG] Saved user_name: {name.capitalize()}")
        return f"Saved user_name: {name.capitalize()}"
    return "No user name found in message"


@tool('get_last_state')
def get_last_state(runtime: ToolRuntime[CustomerAgentState]) -> str:
    """Get the last saved state information."""
    user_name = runtime.state.get("user_name", "not set")
    last_topic = runtime.state.get("last_topic", "not set")
    print(f"[DEBUG] get_last_state called, user_name: {user_name}, last_topic: {last_topic}")
    return f"Last topic: {last_topic}, User name: {user_name}"


# Node that processes messages and calls LLM
def call_llm(state: CustomerAgentState) -> dict:
    """Call LLM with current messages."""
    messages = state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}


# Build graph
builder = StateGraph(CustomerAgentState)
builder.add_node("llm_node", call_llm)
builder.add_node("save_user_info", save_user_info)
builder.add_node("get_last_state", get_last_state)
builder.set_entry_point("llm_node")

# Add conditional edges - LLM decides which tool to call
def should_call_tool(state: CustomerAgentState) -> str:
    """Decide which tool to call based on last message."""
    messages = state.get("messages", [])
    if not messages:
        return "END"

    last_msg = messages[-1]
    content = last_msg.content.lower() if hasattr(last_msg, 'content') else ""

    if "what was my name" in content or "get last state" in content:
        return "get_last_state"
    elif "name is" in content or "i am" in content or "i'm" in content:
        return "save_user_info"

    return "END"

builder.add_conditional_edges("llm_node", should_call_tool, {
    "save_user_info": "save_user_info",
    "get_last_state": "get_last_state",
    "END": "END"
})

# After tool call, go back to LLM
builder.add_edge("save_user_info", "llm_node")
builder.add_edge("get_last_state", "llm_node")

# Compile with checkpointer
checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)

# Config with thread_id for checkpointing
config: RunnableConfig = {"configurable": {"thread_id": "1"}}

print("=" * 50)
print("First invoke: Agent processes message with name")
print("=" * 50)

# First invoke - agent processes message and saves to state
result1 = graph.invoke(
    {"messages": [HumanMessage(content="Hi! My name is Bob.")]},
    config=config
)

print("\n--- State after first invoke ---")
print(f"user_name: {result1.get('user_name', 'not set')}")
print(f"last_topic: {result1.get('last_topic', 'not set')}")

print("\n" + "=" * 50)
print("Second invoke: Agent asks about previous state")
print("=" * 50)

# Second invoke - same thread_id, should access previous state
result2 = graph.invoke(
    {"messages": [HumanMessage(content="What was my name? Use get_last_state tool.")]},
    config=config
)

print("\n--- Final result ---")
print(f"user_name: {result2.get('user_name', 'not set')}")
print(f"last_topic: {result2.get('last_topic', 'not set')}")