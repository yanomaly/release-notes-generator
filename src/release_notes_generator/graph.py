from typing import Literal

from dotenv import load_dotenv
from langchain_core.runnables import RunnableConfig
from langgraph.constants import END, START
from langgraph.graph import StateGraph
from langgraph.types import Command

from release_notes_generator import configuration
from release_notes_generator.state import (
    ReleaseNotesState,
    ReleaseNotesStateInput,
    ReleaseNotesStateOutput,
    SectionState,
)


def generate_release_notes_plan(state: ReleaseNotesState, config: RunnableConfig):
    """Generate the report plan"""
    ...


def write_section(state: SectionState):
    """Write a section of the report"""
    ...


def write_final_sections(state: SectionState):
    """Write final sections of the report, which do not require web search and use the completed sections as context"""
    ...


def initiate_section_writing(state: ReleaseNotesState):
    """This is the "map" step when we kick off web research for some sections of the report"""
    ...


def gather_completed_sections(state: ReleaseNotesState):
    """Gather completed main body sections"""
    ...


def initiate_final_section_writing(state: ReleaseNotesState):
    """This is the "map" step when we kick off research on any sections that require it using the Send API"""
    ...


def compile_final_release_notes(state: ReleaseNotesState):
    """Compile the final release notes"""
    ...


def verify_release_notes(
    state: ReleaseNotesState,
) -> Command[Literal["generate_release_notes_plan", END]]:
    """Verify the final release notes and invoke generation procces in case of any remarks"""
    value = interrupt({"final_notes": state["final_notes"]})
    return Command(
        update={
            "messages": [
                {
                    "role": "human",
                    "content": user_input,
                }
            ]
        },
        goto=(END if "stop" in user_input else generate_release_notes_plan),
    )


load_dotenv()

builder = StateGraph(
    ReleaseNotesState,
    input=ReleaseNotesStateInput,
    output=ReleaseNotesStateOutput,
    config_schema=configuration.Configuration,
)

builder.add_node(generate_release_notes_plan)
builder.add_node(write_section)
builder.add_node(gather_completed_sections)
builder.add_node(write_final_sections)
builder.add_node(compile_final_release_notes)
builder.add_node(verify_release_notes)

builder.add_edge(START, "generate_release_notes_plan")
builder.add_conditional_edges(
    "generate_release_notes_plan", initiate_section_writing, ["write_section"]
)
builder.add_edge("write_section", "gather_completed_sections")
builder.add_conditional_edges(
    "gather_completed_sections",
    initiate_final_section_writing,
    ["write_final_sections"],
)
builder.add_edge("write_final_sections", "compile_final_release_notes")
builder.add_edge("compile_final_release_notes", "verify_release_notes")

graph = builder.compile()
graph.name = "Release Notes Generator"
