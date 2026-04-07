from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse

from llm.llm import llm
from llm.llm import simple_llm

@wrap_model_call
def dynamic_model_selection(request: ModelRequest, handler) -> ModelResponse:
    """Choose model based on message length.
    When message length > 100 chars, use llm (thinking enabled).
    Otherwise use simple_llm (thinking disabled).
    """
    # Get the last user message content
    messages = request.state.get("messages", [])
    last_message = messages[-1] if messages else None

    if last_message:
        message_length = len(str(last_message.content))
    else:
        message_length = 0

    if message_length > 100:
        model = llm
    else:
        model = simple_llm

    return handler(request.override(model=model))


agent = create_agent(model =simple_llm,middleware=[dynamic_model_selection])