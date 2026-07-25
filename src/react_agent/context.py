"""Define the configurable parameters for the agent."""

from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from typing import Annotated

from . import prompts


@dataclass(kw_only=True)
class Context:
    """The context for the agent."""

    system_prompt: str = field(
        default=prompts.SYSTEM_PROMPT,
        metadata={
            "description": "The system prompt to use for the agent's interactions. "
            "This prompt sets the context and behavior for the agent."
        },
    )

    model: Annotated[str, {"__template_metadata__": {"kind": "llm"}}] = field(
        default="google_genai/gemini-3.5-flash-lite",
        metadata={
            "description": "The name of the language model to use for the agent's main interactions. "
            "Should be in the form: provider/model-name."
        },
    )

    max_emails: int = field(
        default=25,
        metadata={
            "description": "The maximum number of emails to return for each Gmail search."
        },
    )

    gmail_credentials_file: str = field(
        default="credentials.json",
        metadata={
            "description": "Path to the Google Cloud OAuth client secrets file "
            "(downloaded from the Google Cloud console)."
        },
    )

    gmail_token_file: str = field(
        default="token.json",
        metadata={
            "description": "Path where the cached OAuth token is stored after the "
            "first successful sign-in. Created automatically."
        },
    )

    def __post_init__(self) -> None:
        """Fetch env vars for attributes that were not passed as args."""
        for f in fields(self):
            if not f.init:
                continue

            if getattr(self, f.name) == f.default:
                setattr(self, f.name, os.environ.get(f.name.upper(), f.default))
