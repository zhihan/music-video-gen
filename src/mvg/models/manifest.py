"""Manifest data model."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field
import yaml

from .scene import Scene


class Manifest(BaseModel):
    """Video project manifest."""

    model_config = ConfigDict(frozen=False)

    project_name: str = Field(
        ..., description="Project name"
    )
    audio_file: str | None = Field(
        None, description="Path to background music"
    )
    scenes: list[Scene] = Field(
        default_factory=list,
        description="List of scenes",
    )
    aspect_ratio: str = Field(
        default="9:16",
        description="Output aspect ratio",
    )

    @classmethod
    def from_yaml(cls, path: Path) -> Manifest:
        """Load manifest from YAML file.

        Args:
            path: Path to the YAML file.

        Returns:
            Parsed Manifest instance.
        """
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def to_yaml(self, path: Path) -> None:
        """Save manifest to YAML file.

        Args:
            path: Output path for the YAML file.
        """
        with open(path, "w") as f:
            yaml.safe_dump(
                self.model_dump(),
                f,
                default_flow_style=False,
            )
