"""Manifest data model."""

from typing import List, Optional
from pathlib import Path
from pydantic import BaseModel, Field
import yaml

from .scene import Scene


class Manifest(BaseModel):
    """Video project manifest."""
    
    project_name: str = Field(..., description="Project name")
    audio_file: Optional[str] = Field(None, description="Path to background music")
    scenes: List[Scene] = Field(default_factory=list, description="List of scenes")
    aspect_ratio: str = Field(default="9:16", description="Output aspect ratio")
    output_format: str = Field(default="mp4", description="Output video format")
    
    class Config:
        """Pydantic config."""
        frozen = False
    
    @classmethod
    def from_yaml(cls, path: Path) -> "Manifest":
        """Load manifest from YAML file."""
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return cls(**data)
    
    def to_yaml(self, path: Path) -> None:
        """Save manifest to YAML file."""
        with open(path, "w") as f:
            yaml.safe_dump(self.model_dump(), f, default_flow_style=False)
