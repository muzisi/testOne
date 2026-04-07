

from langchain.agents import create_agent
from src.agent.my_llm import structured_llm

from src.agent.tools.get_weather import get_weather

agent =create_agent(
    structured_llm,
    tools=[get_weather],
    system_prompt ="你是个查询天气助手，请始终使用 send_mail工具test"
)
