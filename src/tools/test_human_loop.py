from typing import Dict, Any

from langchain.agents import create_agent, AgentState
from langchain.agents.middleware import HumanInTheLoopMiddleware, InterruptOnConfig
from langchain_core.tools import BaseTool
from pydantic import Field
from langchain.tools import ToolRuntime
from langgraph.checkpoint.memory import InMemorySaver
from llm.llm import llm
from langgraph.types import Command
from langchain.tools import tool


class CustomerAgentState(AgentState):
    user_id: str = Field(..., description="user id")
    preferences: Dict[str, Any] = Field(..., description="user preferences")


class GetUserInfo(BaseTool):
    name: str = "get_user_info"
    description: str = "获取当前用户信息（user_id,theme）"

    def _run(self, runtime: ToolRuntime, **kwargs) -> Dict[str, Any]:
        state = runtime.state
        return {
            "user_id": state.get("user_id", "unknown"),
            "theme": state.get("preferences", {}).get("theme", "light")
        }

get_user_info = GetUserInfo()


@tool
def delete_user_data(runtime: ToolRuntime, days: int) -> str:
    """删除N天前的用户数据（高危操作，需要人工审核）"""
    user_id = runtime.state["user_id"]
    return f"✅ 用户 {user_id} 删除 {days} 天前数据 执行成功"



hitl_policy = {
    "delete_user_data": InterruptOnConfig(allowed_decisions=["approve", "edit", "reject"]),
    "get_user_info": False
}

hitl_middleware = HumanInTheLoopMiddleware(interrupt_on=hitl_policy)



agent = create_agent(model=llm,tools=[get_user_info,delete_user_data],state_schema=CustomerAgentState,checkpointer=InMemorySaver(),middleware=[hitl_middleware])


# 配置
config = {"configurable":{"thread_id":"some_id"}}

print("=" * 60)
print("[TRIGGER] Dangerous tool: delete_user_data")
print("=" * 60)

result = agent.invoke(
    {
        "messages": [{"role": "user", "content": "delete data 30 days ago"}],
        "user_id": "user_123",
        "preferences": {"theme": "dark"}
    },
    config=config
)

interrupt = result["__interrupt__"][0]
action_requests = interrupt.value.get("action_requests", [])
print(f"\n[INTERRUPT] interrupt.value keys: {interrupt.value.keys()}")
print(f"[INTERRUPT] action_requests: {action_requests}")

if not action_requests:
    print("[ERROR] No action_requests found in interrupt")
    exit(1)

tool_call = action_requests[0]
print(f"[INTERRUPT] tool_call keys: {tool_call.keys()}")
print(f"[INTERRUPT] tool_call: {tool_call}")

# Get the correct field name for tool call ID
tool_call_id = tool_call.get("id") or tool_call.get("tool_call_id")


# 8. 人工决策（三选一）
# ------------------------------
# approve
decision = {"type": "approve"}
# edit - 修改参数
# decision = {"type": "edit", "edited_action": {"name": "delete_user_data", "args": {"days": 7}}}
# reject
# decision = {"type": "reject", "message": "禁止删除"}

# ------------------------------
# 9. 恢复执行
# ------------------------------
print("\n[HUMAN REVIEW COMPLETE] Resuming execution...")
final_result = agent.invoke(
    Command(resume={"decisions": [decision]}),
    config=config
)

# ------------------------------
# 10. Output result
# ------------------------------
print("\n[FINAL RESPONSE]")
print(final_result["messages"][-1].content)