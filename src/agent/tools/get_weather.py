from typing import Literal

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


@tool('get_weather', args_schema=WeatherInput)
def get_weather(location: str, units: str ="beijing", include_forecast: bool =False ) ->str:
    """get current weather  and optionally include forecast data
    Args:
        location (str): location
        units (str): units
        include_forecast (bool): include forecast data
    Returns:
          返回天气情况
    """

    temp = 18 if units == "beijing" else 30
    result = f"current weather in{location}: {temp}"
    if include_forecast:
        result += "\n next 5 day: sunny"
    return result


if __name__ == '__main__':
    print(get_weather.name)
    print(get_weather.description)
    print(get_weather.args_schema)