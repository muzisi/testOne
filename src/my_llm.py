from langchain_openai import ChatOpenAI

from env_utils import *


llm = ChatOpenAI(
     model="MiniMax-M2.7",
     temperature = 0.1,
     api_key= MINIMAX_API_KEY,
     base_url =MINIMAX_BASE_URL,
)

