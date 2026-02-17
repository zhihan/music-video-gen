"""Configuration management."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field

# Load environment variables
load_dotenv()


class Config(BaseModel):
    """Application configuration."""

    model_config = ConfigDict(frozen=False)

    # API Keys
    anthropic_api_key: str = Field(
        default_factory=lambda: os.getenv(
            "ANTHROPIC_API_KEY", ""
        ),
        description="Anthropic API key",
    )
    openai_api_key: str = Field(
        default_factory=lambda: os.getenv(
            "OPENAI_API_KEY", ""
        ),
        description="OpenAI API key (for Whisper)",
    )
    google_application_credentials: str = Field(
        default_factory=lambda: os.getenv(
            "GOOGLE_APPLICATION_CREDENTIALS", ""
        ),
        description="Path to Google Cloud service account JSON",
    )
    google_cloud_project: str = Field(
        default_factory=lambda: os.getenv(
            "GOOGLE_CLOUD_PROJECT", ""
        ),
        description="Google Cloud project ID",
    )
    veo_output_bucket: str = Field(
        default_factory=lambda: os.getenv(
            "VEO_OUTPUT_BUCKET", ""
        ),
        description="GCS bucket for Veo output",
    )
    veo_model: str = Field(
        default_factory=lambda: os.getenv(
            "VEO_MODEL", "veo-3.1-fast-generate-001"
        ),
        description="Veo model name",
    )

    # Paths
    workspace: Path = Field(
        default_factory=lambda: Path(
            os.getenv("MVG_WORKSPACE", ".")
        ),
        description="Workspace directory",
    )

    # Model settings
    default_model: str = Field(
        default="claude-sonnet-4-20250514",
        description="Default Claude model",
    )

    def validate_required(self) -> None:
        """Validate that required credentials are set.

        Raises:
            ValueError: If ANTHROPIC_API_KEY is not set.
        """
        if not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

    def validate_veo_required(self) -> None:
        """Validate Veo 3 / Google Cloud credentials.

        Raises:
            ValueError: If any required Veo configuration
                is missing.
        """
        missing: list[str] = []

        if not self.google_cloud_project:
            missing.append("GOOGLE_CLOUD_PROJECT")
        if not self.veo_output_bucket:
            missing.append("VEO_OUTPUT_BUCKET")

        if missing:
            raise ValueError(
                "Missing required Veo configuration: "
                f"{', '.join(missing)}. "
                "Set the corresponding environment "
                "variables."
            )

        if (
            self.veo_output_bucket
            and not self.veo_output_bucket.startswith("gs://")
        ):
            raise ValueError(
                "VEO_OUTPUT_BUCKET must be a GCS URI "
                "starting with 'gs://'. "
                f"Got: {self.veo_output_bucket}"
            )


# Global config instance
config = Config()
