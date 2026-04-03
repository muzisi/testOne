from langchain.chat_models import init_chat_model
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_openai import ChatOpenAI

from env_utils import *

# 普通 LLM
llm = ChatOpenAI(
    model="MiniMax-M2.7",
    temperature=0.1,
    api_key=MINIMAX_API_KEY,
    base_url=MINIMAX_BASE_URL,
    timeout=300,
    max_tokens=2000,
    max_retries=6,
    extra_body={"thinking": {"type": "enabled", "tokens": 1024}},
)

# 结构化输出 LLM（禁用 thinking，避免返回 content 包含<think>干扰 JSON 解析）
structured_llm = ChatOpenAI(
    model="MiniMax-M2.7",
    temperature=0.1,
    api_key=MINIMAX_API_KEY,
    base_url=MINIMAX_BASE_URL,
    extra_body={"thinking": {"type": "disabled"}},
)

# 限速器：每秒最多 1 次请求
rate_limiter = InMemoryRateLimiter(
    requests_per_second=1,
    check_every_n_seconds=0.1
)

# 使用 init_chat_model 创建限速 LLM
rate_llm = init_chat_model(
    model="MiniMax-M2.7",
    api_key=MINIMAX_API_KEY,
    base_url=MINIMAX_BASE_URL,
    model_provider="openai",
    rate_limiter=rate_limiter
)

