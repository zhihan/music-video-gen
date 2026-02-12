"""Scene data model."""

from typing import Optional
from pydantic import BaseModel, Field


class Scene(BaseModel):
    """Represents a single scene in the video."""
    
    id: str = Field(..., description="Unique scene identifier")
    prompt: Optional[str] = Field(None, description="Veo generation prompt")
    duration: float = Field(..., description="Scene duration in seconds", gt=0)
    source: str = Field(default="generate", description="Source type: 'generate' or 'file'")
    file: Optional[str] = Field(None, description="Path to existing video file")
    overlay_text: Optional[str] = Field(None, description="Text to overlay on scene")
    overlay_style: Optional[str] = Field(None, description="Text overlay style name")
    
    class Config:
        """Pydantic config."""
        frozen = False
