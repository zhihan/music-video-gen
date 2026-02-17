"""Scene data model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Scene(BaseModel):
    """Represents a single scene in the video."""

    model_config = ConfigDict(frozen=False)

    id: str = Field(
        ..., description="Unique scene identifier"
    )
    prompt: str | None = Field(
        None, description="Veo generation prompt"
    )
    duration: float = Field(
        ..., description="Scene duration in seconds", gt=0
    )
    source: str = Field(
        default="generate",
        description="Source type: 'generate' or 'file'",
    )
    file: str | None = Field(
        None, description="Path to existing video file"
    )
    overlay_text: str | None = Field(
        None, description="Text to overlay on scene"
    )
    overlay_style: str | None = Field(
        None, description="Text overlay style name"
    )
