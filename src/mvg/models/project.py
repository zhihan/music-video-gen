"""Project state model."""

from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field

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
    
    manifest: Manifest = Field(..., description="Project manifest")
    state: ProjectState = Field(default=ProjectState.INIT, description="Current state")
    clips_generated: List[str] = Field(default_factory=list, description="Generated clip paths")
    errors: List[str] = Field(default_factory=list, description="Error messages")
    
    class Config:
        """Pydantic config."""
        frozen = False
