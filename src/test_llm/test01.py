from agent.my_llm import llm

from langchain.messages import HumanMessage,AIMessage,SystemMessage
question = "用三句话，介绍机器学习"

system_msg = SystemMessage("你是个优秀的语文老师")
human_msg = HumanMessage("请问 李白最有名的诗是哪首？并写出来")
ai_message = AIMessage("赠汪伦很好")
messages = [system_msg, human_msg]

# 收集流式响应
respone = llm.invoke(messages)
print(respone.content)

print("*" *5)

print(respone.usage_metadata)

