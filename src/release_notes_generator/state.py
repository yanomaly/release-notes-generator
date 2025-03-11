import operator

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from pydantic import BaseModel, Field
from typing_extensions import Annotated, List

from release_notes_generator.prompts import RELEASE_NOTES_PROMPT


class Section(BaseModel):
    name: str = Field(description="Name for this section of the report.", kw_only=True)
    description: str = Field(
        description="Brief overview of the main topics and concepts to be covered in this section.",
        kw_only=True,
    )
    content: str = Field(description="The content of the section.", kw_only=True)
    main_body: bool = Field(
        description="Whether this is a main body section.", kw_only=True
    )


class Sections(BaseModel):
    sections: List[Section] = Field(
        description="Sections of the release notes.", kw_only=True
    )


class ReleaseNotesState(BaseModel):
    messages: Annotated[list[AnyMessage], add_messages]
    urls: List[str] = Field(default_factory=list, kw_only=True)
    sections: list[Section] = Field(default_factory=list, kw_only=True)
    completed_sections: Annotated[list, operator.add]
    notes_main_body_sections: str = Field(default=None, kw_only=True)
    final_notes: str = Field(default=None, kw_only=True)


class ReleaseNotesStateInput(BaseModel):
    generation_prompt: str = Field(default=RELEASE_NOTES_PROMPT, kw_only=True)
    days_filter: int = Field(default=0, kw_only=True, ge=0)
    urls: List[str] = Field(default_factory=list, kw_only=True)


class ReleaseNotesStateOutput:
    final_notes: str = Field(default=None, kw_only=True)


class SectionState(BaseModel):
    section: Section
    urls: List[str] = Field(default_factory=list, kw_only=True)
    notes_main_body_sections: str = Field(default=None, kw_only=True)
    completed_sections: list[Section] = Field(default_factory=list, kw_only=True)


class SectionOutputState(BaseModel):
    completed_sections: list[Section] = Field(default_factory=list, kw_only=True)
