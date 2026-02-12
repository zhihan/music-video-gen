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


# Global config instance
config = Config()
