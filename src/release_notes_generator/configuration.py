from __future__ import annotations

import os
from dataclasses import fields
from typing import Any, Literal, Optional

from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

DEFAULT_RELEASE_NOTES_STRUCTURE = """The blog post should follow this strict three-part structure:

1. Introduction (max 1 section)
   - Start with ### Key Links and include user-provided links
   - Brief overview of the problem statement
   - Brief overview of the solution/main topic
   - Maximum 100 words

2. Main Body (exactly 2-3 sections)
    - Each section must:
      * Cover a distinct aspect of the main topic
      * Include at least one relevant code snippet
      * Be 150-200 words
    - No overlap between sections

3. Conclusion (max 1 section)
   - Brief summary of key points
   - Key Links
   - Clear call to action
   - Maximum 150 words"""


class Configuration(BaseModel):
    model_name: Literal["palmyra-x-004", "palmyra-creative"] = Field(
        default="palmyra-x-004",
        description="The name of the language model to use for the agent's interactions. ",
        kw_only=True,
    )

    model_temperature: float = Field(
        default=0.7,
        description="The temperature of model for agent's interactions. ",
        le=1,
        ge=0,
        kw_only=True,
    )

    jira_host: str = Field(
        default=os.getenv("JIRA_HOST"),
        description="Host to paste into Jira request URL. ",
        kw_only=True,
    )

    jira_project_key: str = Field(
        default=os.getenv("JIRA_PROJECT_KEY"),
        description="Project key to fetch issues from. ",
        kw_only=True,
    )

    jira_api_key: str = Field(
        default=os.getenv("JIRA_API_KEY"),
        description="API key to auth on Jira endpoint. ",
        kw_only=True,
    )

    jira_user_email: str = Field(
        default=os.getenv("JIRA_USER_EMAIL"),
        description="User email to auth on Jira endpoint. ",
        kw_only=True,
    )

    github_repo_url: str = Field(
        default=os.getenv("GITHUB_URL"),
        description="URL of GitHub repo to fetch data from. ",
        kw_only=True,
    )

    release_notes_structure: str = Field(
        default=DEFAULT_RELEASE_NOTES_STRUCTURE,
        description="Default structure for release notes generation. ",
        kw_only=True,
    )

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> Configuration:
        """Create a Configuration instance from a RunnableConfig."""
        configurable = (
            config["configurable"] if config and "configurable" in config else {}
        )
        values: dict[str, Any] = {
            f.name: os.environ.get(f.name.upper(), configurable.get(f.name))
            for f in fields(cls)
            if f.init
        }
        return cls(**{k: v for k, v in values.items() if v})
