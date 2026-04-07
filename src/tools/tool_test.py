from langchain.agents import create_agent
from langchain_core.messages import human
from langgraph.types import Command
from langchain.tools import tool,ToolRuntime
from langchain.messages import HumanMessage
from langchain.tools import tool

from llm.llm import llm

@tool
def get_last_user_message(runtime: ToolRuntime) -> str:
    """Get the most recent message from the user"""

    messages = runtime.state["messages"]

    #find the last human message

    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return message.content
    return "No user message found"

@tool
def get_user_preference(
    pref_name: str,
    runtime: ToolRuntime
) -> str:
    """Get a user preference value."""
    preferences = runtime.state.get("user_preferences", {})
    return preferences.get(pref_name, "Not set")


def set_user_name(new_name: str) -> Command:
    """Set the user's name in the conversation state."""
    return Command(update={"user_name": new_name})


human_msg = HumanMessage("你好")
agent = create_agent(model=llm,tools=[get_last_user_message],system_prompt="你是测试，必须调用get_last_user_message 方法")
messages =[human_msg]
repose = agent.invoke({"messages": messages})
repose1 = agent.ainvoke({"messages": messages})
print(repose)