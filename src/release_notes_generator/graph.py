import json
from asyncio import gather, run
from typing import Literal

import instructor
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_writer import ChatWriter
from langgraph.constants import END, START
from langgraph.graph import StateGraph
from langgraph.types import Command, Send, interrupt
from writerai import AsyncWriter

from release_notes_generator import configuration
from release_notes_generator.prompts import (
    RELEASE_NOTES_PROMPT,
    RELEASE_NOTES_SECTION_PROMPT,
)
from release_notes_generator.state import (
    ReleaseNotesState,
    ReleaseNotesStateInput,
    ReleaseNotesStateOutput,
    Sections,
    SectionState,
)
from release_notes_generator.utils import (
    get_diff_tools,
    get_github_releases,
    get_jira_tickets,
)

load_dotenv()


async def generate_release_notes_plan(
    state: ReleaseNotesStateInput, config: RunnableConfig
):
    """Generate the release notes structure plan"""
    configurable = configuration.Configuration.from_runnable_config(config)

    jira_tickets, github_releases = await gather(
        get_jira_tickets(state, configurable), get_github_releases(configurable)
    )

    release_notes_prompt = RELEASE_NOTES_PROMPT.format(
        generation_prompt=state.generation_prompt,
        release_notes_structure=configurable.release_notes_structure,
        jira_tickets=jira_tickets,
    )

    instructor_client = instructor.from_writer(
        client=AsyncWriter(),
        mode=instructor.Mode.WRITER_TOOLS,
    )
    report_sections = await instructor_client.chat.completions.create(
        model=configurable.model_name,
        messages=[
            {
                "role": "user",
                "content": release_notes_prompt,
            }
        ],
        response_model=Sections,
    )

    return {
        "messages": [
            HumanMessage(release_notes_prompt),
            AIMessage(json.dumps(report_sections.model_dump())),
        ],
        "sections": report_sections.sections,
        "urls": state.urls,
        "jira_tickets": jira_tickets,
        "github_releases": github_releases,
        "days_filter": state.days_filter,
        "generation_prompt": state.generation_prompt,
    }


async def initiate_section_writing(state: ReleaseNotesState):
    """This is the "map" step when we kick off web research for some sections of the report"""
    return [
        Send(
            "write_section",
            SectionState(
                section=sctn,
                urls=state.urls,
                jira_tickets=state.jira_tickets,
                github_releases=state.github_releases,
                generation_prompt=state.generation_prompt,
                messages=state.messages,
            ),
        )
        for sctn in state.sections
    ]


async def write_section(state: SectionState, config: RunnableConfig):
    """Write a section of the report"""
    section_instructions = RELEASE_NOTES_SECTION_PROMPT.format(
        generation_prompt=state.generation_prompt,
        section_name=state.section.name,
        section_topic=state.section.description,
        source_urls=state.urls,
        jira_tickets=state.jira_tickets,
    )

    configurable = configuration.Configuration.from_runnable_config(config)
    llm = ChatWriter(
        model=configurable.model_name, temperature=configurable.model_temperature
    ).bind_tools(get_diff_tools(state))

    response = llm.invoke(state.messages + [HumanMessage(section_instructions)])

    if response.tool_calls:
        ...

    state.section.content = response.content

    return {
        "completed_sections": [state.section],
        "messages": [HumanMessage(section_instructions), AIMessage(response.content)],
    }


async def compile_final_release_notes(state: ReleaseNotesState):
    """Compile the final release notes"""
    completed_sections = {s.name: s.content for s in state.completed_sections}

    for section in state.sections:
        section.content = completed_sections[section.name]

    rendered_notes = "\n\n".join([s.content for s in state.sections])

    return {"final_notes": rendered_notes}


def verify_release_notes(
    state: ReleaseNotesState,
) -> Command[Literal["generate_release_notes_plan", END]]:
    """Verify the final release notes and invoke generation proces in case of any remarks"""
    user_input = interrupt({"final_notes": state.final_notes})
    if "try_again" in user_input and user_input["try_again"]:
        return Command(goto="generate_release_notes_plan")
    else:
        return Command(goto=END)


builder = StateGraph(
    ReleaseNotesState,
    input=ReleaseNotesStateInput,
    output=ReleaseNotesStateOutput,
    config_schema=configuration.Configuration,
)

builder.add_node(generate_release_notes_plan)
builder.add_node(write_section)
builder.add_node(compile_final_release_notes)
builder.add_node(verify_release_notes)

builder.add_edge(START, "generate_release_notes_plan")
builder.add_conditional_edges(
    "generate_release_notes_plan", initiate_section_writing, ["write_section"]
)
builder.add_edge("write_section", "compile_final_release_notes")
builder.add_edge("compile_final_release_notes", "verify_release_notes")

graph = builder.compile()
graph.name = "Release Notes Generator"

# run(graph.ainvoke(input={"days_filter": 14}))
