from langchain.agents import create_agent, AgentState
from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import StateT
from langgraph.checkpoint.memory import InMemorySaver
from langchain.tools import tool
from langchain.tools import ToolRuntime
from langgraph.runtime import Runtime
from langgraph.typing import ContextT
from llm.llm import llm
from pydantic import Field


class CustomState(AgentState):
    model_call_count: int = Field(default=0)


# 初始化状态，确保 model_call_count 存在
initial_state = {"messages": [], "model_call_count": 0}


class LogAndCountMiddleware(AgentMiddleware):

    def before_agent(self, state: CustomState, runtime:ToolRuntime) :
        print("\n===== before_agent =====")
        print("Agent 开始执行，初始 state:", state)
        return state

        # 2. 每次调用 LLM 前执行

    def before_model(self, state: CustomState, runtime: ToolRuntime):
        print("\n===== before_model =====")
        # 修改状态：模型调用次数 +1
        state["model_call_count"] += 1
        print(f"模型即将调用，次数: {state['model_call_count']}")
        print("当前消息:", state["messages"][-1].content[:50] + "...")
        return state

        # 3. 每次 LLM 返回后执行

    def after_model(self, state: CustomState, runtime: ToolRuntime):
        print("\n===== after_model =====")
        print("模型返回成功")
        return state

    # 4. Agent 结束前执行一次
    def after_agent(self, state: CustomState, runtime: ToolRuntime):
        print("\n===== after_agent =====")
        print(f"Agent 执行完成，总调用次数: {state['model_call_count']}")
        return state

@tool
def echo(msg: str) -> str:
        """简单返回输入的消息"""
        return f"Echo: {msg}"

my_middleware = LogAndCountMiddleware()
agent = create_agent(
    llm,
    tools=[echo],
    state_schema=CustomState,
    middleware=[my_middleware],  # 加入自定义中间件
    checkpointer=InMemorySaver(),
)


if __name__ == "__main__":
    result = agent.invoke(
        {
            "messages": [{"role": "user", "content": "Hello, tell me a joke"}],
            "model_call_count": 0
        },
        config={"configurable": {"thread_id": "test_middleware"}}
    )

    print("\n===== Final Result =====")
    print("AI response:", result["messages"][-1].content)
    print("Model call count:", result["model_call_count"])