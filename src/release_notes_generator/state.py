import operator

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from pydantic import BaseModel, Field
from typing_extensions import Annotated


class Section(BaseModel):
    name: str = Field(description="Name for this section of the report.")
    description: str = Field(
        description="Brief overview of the main topics and concepts to be covered in this section."
    )
    content: str = Field(description="The content of the section.")


class Sections(BaseModel):
    sections: list[Section] = Field(
        description="Sections of the release notes.",
    )


class JiraTicket(BaseModel):
    name: str = Field()
    epic: str = Field(default="")
    description: str = Field(default="")
    status: str = Field(default="")


class GitHubRelease(BaseModel):
    repo: str = Field()
    description: str = Field(default="")
    diff: str = Field(default="")


class ReleaseNotesState(BaseModel):
    messages: Annotated[list[AnyMessage], add_messages]

    days_filter: int = Field(default=7, ge=1)
    generation_prompt: str = Field(default="")
    urls: list[str] = Field(default_factory=list)
    jira_tickets: list[JiraTicket] = Field(default_factory=list)
    github_releases: dict[str, GitHubRelease] = Field(default_factory=dict)
    sections: list[Section] = Field(default_factory=list)
    completed_sections: Annotated[list, operator.add] = Field(default_factory=list)

    final_notes: str = Field(default=None)


class ReleaseNotesStateInput(BaseModel):
    generation_prompt: str = Field(default="")
    days_filter: int = Field(default=7, ge=0)
    urls: list[str] = Field(default_factory=list)


class ReleaseNotesStateOutput:
    final_notes: str = Field(default=None)


class SectionState(BaseModel):
    section: Section = Field(default=None)
    urls: list[str] = Field(
        default_factory=list,
    )
    jira_tickets: list[JiraTicket] = Field(
        default_factory=list,
    )
    github_releases: dict[str, GitHubRelease] = Field(default_factory=dict)
    generation_prompt: str = Field(default="")
    messages: list[AnyMessage] = Field()
