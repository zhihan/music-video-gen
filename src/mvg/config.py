"""Configuration management."""

import os
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config(BaseModel):
    """Application configuration."""
    
    # API Keys
    anthropic_api_key: str = Field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""),
        description="Anthropic API key"
    )
    openai_api_key: str = Field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY", ""),
        description="OpenAI API key (for Whisper)"
    )
    google_application_credentials: str = Field(
        default_factory=lambda: os.getenv("GOOGLE_APPLICATION_CREDENTIALS", ""),
        description="Path to Google Cloud service account JSON"
    )
    google_cloud_project: str = Field(
        default_factory=lambda: os.getenv("GOOGLE_CLOUD_PROJECT", ""),
        description="Google Cloud project ID"
    )
    veo_output_bucket: str = Field(
        default_factory=lambda: os.getenv("VEO_OUTPUT_BUCKET", ""),
        description="GCS bucket for Veo output"
    )
    
    # Paths
    workspace: Path = Field(
        default_factory=lambda: Path(os.getenv("MVG_WORKSPACE", ".")),
        description="Workspace directory"
    )
    
    # Model settings
    default_model: str = Field(
        default="claude-sonnet-4-20250514",
        description="Default Claude model"
    )
    
    class Config:
        """Pydantic config."""
        frozen = False
    
    def validate_required(self) -> None:
        """Validate that required credentials are set."""
        if not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

    def validate_veo_required(self) -> None:
        """Validate that Veo 3 / Google Cloud credentials are set.

        Raises:
            ValueError: If any required Veo configuration is missing.
        """
        missing: list[str] = []

        if not self.google_cloud_project:
            missing.append("GOOGLE_CLOUD_PROJECT")
        if not self.veo_output_bucket:
            missing.append("VEO_OUTPUT_BUCKET")

        if missing:
            raise ValueError(
                f"Missing required Veo configuration: {', '.join(missing)}. "
                "Set the corresponding environment variables."
            )

        # Validate bucket format
        if self.veo_output_bucket and not self.veo_output_bucket.startswith("gs://"):
            raise ValueError(
                f"VEO_OUTPUT_BUCKET must be a GCS URI starting with 'gs://'. "
                f"Got: {self.veo_output_bucket}"
            )


# Global config instance
config = Config()
