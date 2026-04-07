from langchain.agents import create_agent,AgentState
from langgraph.checkpoint.memory import  InMemorySaver
from langchain.tools import BaseTool
from pydantic import Field
from typing import Optional, Dict, Any
from langchain_core.runnables import RunnableConfig
from llm.llm import llm
from langchain.tools import ToolRuntime
from langchain.tools import tool

class CustomerAgentState(AgentState):
    user_id: str= Field(description="用户ID")
    preferences : Dict[str, Any] =Field(description="用户偏好")


class GetUserInfoTool(BaseTool):
    name :str ="get_user_info"
    description: str ="获取当前用户信息（user_id,theme）"

    def _run(self, **kwargs):
        state = kwargs["state"]
        user_id = state.get("user_id")
        theme = state.preferences.get("theme","light")
        return {"user_id":user_id, "theme":theme}

get_user_info_tool = GetUserInfoTool()


@tool
def get_user(runtime: ToolRuntime):
    """
    获取当前用户的信息：user_id 和 theme
    从 ToolRuntime 中获取 state（官方推荐最稳定方式）
    """
    # 🔥 核心：从 runtime 中获取当前状态
    state = runtime.state

    # 读取自定义字段
    user_id = state.get("user_id")
    theme = state["preferences"].get("theme", "light")

    return {
        "user_id": user_id,
        "theme": theme
    }
agent = create_agent(model=llm,tools=[get_user_info_tool],state_schema=CustomerAgentState,checkpointer=InMemorySaver())


result = agent.invoke(
    {
        "messages": [{"role": "user", "content": "Hello，我的名字叫做李四"}],
        "user_id": "user_123",
        "preferences": {"theme": "dark"}
    },
    config={"configurable": {"thread_id": "1"}}
)

print("=" * 50)
print("Final State:")
print("user_id:", result["user_id"])
print("preferences:", result["preferences"])
# Use only ASCII for print
last_msg = result["messages"][-1].content
print("Last message:", last_msg[:100] if len(last_msg) > 100 else last_msg)



agent1 = create_agent(model=llm, tools=[get_user])
re = agent1.invoke(
    {"messages": [{"role": "user", "content": "Hello"}], "user_id": "user_123", "preferences": {"theme": "dark"}}
)
print("=" * 50)
print("Agent1 result:", re.get("messages", [{}])[-1].content[:100] if re.get("messages") else "No response")



