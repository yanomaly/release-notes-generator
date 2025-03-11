from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_writer import ChatWriter


def get_message_text(msg: BaseMessage) -> str:
    content = msg.content
    if isinstance(content, str):
        return content
    elif isinstance(content, dict):
        return content.get("text", "")
    else:
        txts = [c if isinstance(c, str) else (c.get("text") or "") for c in content]
        return "".join(txts).strip()


def load_chat_model(fully_specified_name: str) -> BaseChatModel:
    return ChatWriter(model_name=fully_specified_name)
