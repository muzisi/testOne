from email.message import EmailMessage

from langchain.agents import create_agent

from my_llm import llm


def send_mail(to: str, subject: str, body: str):
    email = {
        "to": to,
        "subject": subject,
        "body": body
    }

agent =create_agent(
    llm,
    tools=[send_mail],
    system_prompt ="你是个发邮件助手，请始终使用 send_mail工具test"
)