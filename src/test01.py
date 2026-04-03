import json
from my_llm import llm

question = "用三句话，介绍机器学习"

# 收集流式响应
respone = llm.invoke(question)
print(respone)
