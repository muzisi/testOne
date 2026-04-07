from typing import Annotated
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore
from langchain_core.messages import HumanMessage, AIMessage
import os
from llm.llm import llm


store =InMemoryStore()


def agent_node(state: MessagesState ,store: BaseStore) -> str:

    messages =state["messages"]
    print("\n【State 内存历史】本轮对话消息：")
    for m in messages:
        print(f"- {type(m).__name__}: {m.content}")

    user_info = store.get(("user_preferences",), "user_1")
    user_name = user_info.value.get("name", "陌生人") if user_info else "陌生人"
    print(f"\n【Store 长期记忆】记住的用户名：{user_name}")

    response = llm.invoke(messages)

    if "我叫" in messages[-1].content:
        name = messages[-1].content.replace("我叫","").strip()
        store.put(("user_preferences",), "user_1", {"name": name})

    return {"messages": [response]}

builder = StateGraph(MessagesState)
builder.add_node(agent_node)
builder.set_entry_point("agent_node")
builder.set_finish_point("agent_node")

graph = builder.compile(store=store)


print("=" * 50)
print("第一轮对话")
print("=" * 50)

graph.invoke({
    "messages": [HumanMessage(content="你好，我叫张三")]
}, config={"configurable": {"user_id": "user_1"}})

# ------------------------------
# 测试第二轮对话（模拟新对话，State 重置，但 Store 还在）
# ------------------------------
print("\n" + "=" * 50)
print("第二轮对话（State 重置，Store 保留）")
print("=" * 50)

graph.invoke({
    "messages": [HumanMessage(content="你知道我叫什么吗？")]
}, config={"configurable": {"user_id": "user_1"}})