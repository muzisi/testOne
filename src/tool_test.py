from typing import Literal

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from my_llm import llm

from pydantic import BaseModel,Field
from langchain.tools import  tool,ToolRuntime

class WeatherInput(BaseModel):
    """ input for weather data """
    location: str = Field(description="location")
    units: Literal["beijing", "shanghai"] = Field(
        default="beijing",
        description="Temperature unit preference"
    )
    include_forecast: bool = Field(
        default=False,
        description="include forecast data"
    )



@tool(name='get_weather',args_schema=WeatherInput)
def get_weather(location: str, units: str ="beijing", include_forecast: bool =False ) ->str:
    """get current weather  and optionally include forecast data"""

    temp = 18 if units == "beijing" else 30
    result = f"current weather in{location}: {temp}"
    if include_forecast:
        result += "\n next 5 day: sunny"
    return result



@tool
def search_database(query: str, limit: int = 10) -> str:
    """
    search_database for records

    Args:
          query: search query
          limit: number of records to return
    """
    if query == "liubei":
        return query+"快乐"
    elif query == "cao":
        return query+"分流"
    else:
        return "别毛"



@tool
def get_last_user_message(runtime : ToolRuntime) -> str:
    """get the most recent message from the  user message"""
    messages = runtime.state["messages"]

    #find the last human message
    for message in  reversed(messages):
        if isinstance(message,HumanMessage):
            return message.content

    return "no user message find"