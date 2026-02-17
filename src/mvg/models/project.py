"""Project state model."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from .manifest import Manifest


class ProjectState(str, Enum):
    """Project state enum."""

    INIT = "init"
    RESEARCHING = "researching"
    GENERATING = "generating"
    ASSEMBLING = "assembling"
    COMPLETED = "completed"
    FAILED = "failed"


class Project(BaseModel):
    """Project state tracking."""

    model_config = ConfigDict(frozen=False)

    manifest: Manifest = Field(
        ..., description="Project manifest"
    )
    state: ProjectState = Field(
        default=ProjectState.INIT,
        description="Current state",
    )
    clips_generated: list[str] = Field(
        default_factory=list,
        description="Generated clip paths",
    )
    errors: list[str] = Field(
        default_factory=list,
        description="Error messages",
    )
