
from langchain_core.output_parsers import SimpleJsonOutputParser
from agent.my_llm import llm


parser = SimpleJsonOutputParser()

question = "用三句话，介绍机器学习。请以 JSON 格式返回，格式如下：{\"sentence1\": \"...\", \"sentence2\": \"...\", \"sentence3\": \"...\"}"

chain = llm | parser
result = chain.invoke(question)

# 格式化输出
print(result)
print("=" * 50)
print("机器学习简介（结构化输出）:")
print("=" * 50)
print(f"1. {result['sentence1']}")
print(f"2. {result['sentence2']}")
print(f"3. {result['sentence3']}")
print("=" * 50)