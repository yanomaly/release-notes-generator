from datetime import datetime, timezone
from typing import Dict, List, Literal, cast

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode

from release_notes_generator.configuration import Configuration
from release_notes_generator.state import InputState, State
from release_notes_generator.tools import TOOLS
from release_notes_generator.utils import load_chat_model
from dotenv import load_dotenv


load_dotenv()

async def call_model(
    state: State, config: RunnableConfig
) -> Dict[str, List[AIMessage]]:
    configuration = Configuration.from_runnable_config(config)

    model = load_chat_model(configuration.model).bind_tools(TOOLS)

    system_message = configuration.system_prompt.format(
        system_time=datetime.now(tz=timezone.utc).isoformat()
    )

    chat_response = await model.ainvoke(
            [{"role": "system", "content": system_message}, *state.messages], config
        ),

    response = chat_response[0]

    if state.is_last_step and response.tool_calls:
        return {
            "messages": [
                AIMessage(
                    id=response.id,
                    content="Sorry, I could not find an answer to your question in the specified number of steps.",
                )
            ]
        }

    return {"messages": [response]}


builder = StateGraph(State, input=InputState, config_schema=Configuration)

builder.add_node(call_model)
builder.add_node("tools", ToolNode(TOOLS))

builder.add_edge("__start__", "call_model")


def route_model_output(state: State) -> Literal["__end__", "tools"]:
    last_message = state.messages[-1]
    if not isinstance(last_message, AIMessage):
        raise ValueError(
            f"Expected AIMessage in output edges, but got {type(last_message).__name__}"
        )
    if not last_message.tool_calls:
        return "__end__"
    return "tools"


builder.add_conditional_edges(
    "call_model",
    route_model_output,
)

builder.add_edge("tools", "call_model")


graph = builder.compile(
    interrupt_before=[],
    interrupt_after=[],
)
graph.name = "Release Notes Generator"
