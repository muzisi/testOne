"""
天气查询 Agent - 基于 LangChain 框架
"""
import os
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_openai import ChatOpenAI

# ============ 天气工具 ============

@tool
def get_weather(city: str) -> str:
    """
    获取指定城市的天气信息。

    Args:
        city: 城市名称（中文或英文）

    Returns:
        天气信息描述
    """
    # 这里可以接入真实的天气 API（如 OpenWeatherMap）
    # 目前返回模拟数据作为演示
    weather_data = {
        "北京": {"temp": "15°C", "condition": "晴朗", "humidity": "45%"},
        "上海": {"temp": "22°C", "condition": "多云", "humidity": "65%"},
        "深圳": {"temp": "28°C", "condition": "晴", "humidity": "70%"},
        "杭州": {"temp": "20°C", "condition": "小雨", "humidity": "80%"},
    }

    if city in weather_data:
        data = weather_data[city]
        return f"{city}今天天气{data['condition']}，气温{data['temp']}，湿度{data['humidity']}"
    else:
        return f"抱歉，暂不支持查询{city}的天气。您可以尝试查询：北京、上海、深圳、杭州"


@tool
def get_forecast(city: str, days: int = 3) -> str:
    """
    获取指定城市的天气预报。

    Args:
        city: 城市名称
        days: 预报天数（默认3天，最多7天）

    Returns:
        天气预报信息
    """
    if days > 7:
        days = 7
    if days < 1:
        days = 1

    forecasts = {
        "北京": ["今天: 晴 15°C", "明天: 多云 17°C", "后天: 小雨 13°C"],
        "上海": ["今天: 多云 22°C", "明天: 晴 24°C", "后天: 多云 21°C"],
        "深圳": ["今天: 晴 28°C", "明天: 晴 30°C", "后天: 多云 27°C"],
    }

    if city in forecasts:
        return f"{city}未来{min(days, len(forecasts[city]))}天预报：\n" + "\n".join(forecasts[city][:days])
    else:
        return f"抱歉，暂不支持查询{city}的预报。"


# ============ Agent 配置 ============

def create_weather_agent():
    """创建天气查询 Agent"""

    # 获取 OpenAI API Key
    openai_api_key = os.getenv("OPENAI_API_KEY")

    if not openai_api_key:
        raise ValueError("请设置 OPENAI_API_KEY 环境变量")

    # 初始化 LLM
    llm = ChatOpenAI(
        model="gpt-4o",
        api_key=openai_api_key,
        temperature=0.7
    )

    # 定义工具列表
    tools = [get_weather, get_forecast]

    # 创建 Agent
    agent = create_openai_tools_agent(llm, tools, prompt="""
你是一个专业的天气预报助手，可以帮助用户查询天气信息。

你可以使用以下工具：
- get_weather: 查询城市当前天气
- get_forecast: 查询城市未来天气预报

请根据用户的问题，调用合适的工具来回答。
""")

    # 创建 Agent 执行器
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True

    )

    return agent_executor


def main():
    """主函数 - 演示天气 Agent"""
    try:
        agent = create_weather_agent()

        # 示例对话
        print("=" * 50)
        print("天气查询 Agent 已启动（输入 'quit' 退出）")
        print("=" * 50)

        while True:
            user_input = input("\n用户: ").strip()

            if user_input.lower() in ['quit', 'exit', '退出']:
                print("再见！")
                break

            if not user_input:
                continue

            print("\nAgent: ", end="", flush=True)
            response = agent.invoke({"input": user_input})
            print(response["output"])

    except ValueError as e:
        print(f"错误: {e}")
        print("\n请在 .env 文件中设置 OPENAI_API_KEY=你的API密钥")
    except Exception as e:
        print(f"发生错误: {e}")


if __name__ == "__main__":
    main()