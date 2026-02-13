"""Google Imagen API client wrapper via Vertex AI."""

import base64
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import google.auth
import google.auth.transport.requests
import requests
from google.api_core import exceptions as google_exceptions

from ..config import config

logger = logging.getLogger(__name__)


@dataclass
class ImageResult:
    """Result of an Imagen generation operation."""

    prompt: str
    local_path: Optional[Path] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    metadata: dict = field(default_factory=dict)


class ImagenClient:
    """Client wrapper for Google Imagen image generation via Vertex AI."""

    DEFAULT_LOCATION = "us-central1"
    DEFAULT_MODEL = "imagen-3.0-generate-001"

    def __init__(
        self,
        project_id: Optional[str] = None,
        location: str = DEFAULT_LOCATION,
        model: Optional[str] = None,
    ) -> None:
        """Initialize the Imagen client.

        Args:
            project_id: Google Cloud project ID.
            location: GCP region for Vertex AI.
            model: Imagen model name.
        """
        self._project_id = project_id or config.google_cloud_project
        self._location = location
        self._model = model or getattr(config, 'imagen_model', None) or self.DEFAULT_MODEL

        if not self._project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT not set")

    @property
    def project_id(self) -> str:
        return self._project_id

    @property
    def model(self) -> str:
        return self._model

    def generate_image(
        self,
        prompt: str,
        output_path: Path,
        aspect_ratio: str = "1:1",
        negative_prompt: Optional[str] = None,
        num_images: int = 1,
    ) -> ImageResult:
        """Generate an image from a text prompt.

        Args:
            prompt: Text description of the image to generate.
            output_path: Local path to save the generated image.
            aspect_ratio: Image aspect ratio ('1:1', '16:9', '9:16', '4:3', '3:4').
            negative_prompt: Things to avoid in the image.
            num_images: Number of images to generate (saves first one).

        Returns:
            ImageResult with generation details.
        """
        result = ImageResult(
            prompt=prompt,
            created_at=datetime.now(),
            metadata={
                "aspect_ratio": aspect_ratio,
                "model": self._model,
            },
        )

        try:
            # Get credentials
            scopes = ["https://www.googleapis.com/auth/cloud-platform"]
            credentials, _ = google.auth.default(scopes=scopes)
            auth_req = google.auth.transport.requests.Request()
            credentials.refresh(auth_req)

            # Imagen API endpoint
            url = (
                f"https://{self._location}-aiplatform.googleapis.com/v1/"
                f"projects/{self._project_id}/locations/{self._location}/"
                f"publishers/google/models/{self._model}:predict"
            )

            # Build request
            request_body = {
                "instances": [
                    {"prompt": prompt}
                ],
                "parameters": {
                    "sampleCount": num_images,
                    "aspectRatio": aspect_ratio,
                },
            }

            if negative_prompt:
                request_body["parameters"]["negativePrompt"] = negative_prompt

            headers = {
                "Authorization": f"Bearer {credentials.token}",
                "Content-Type": "application/json",
            }

            logger.info(f"Generating image with Imagen: {prompt[:50]}...")
            response = requests.post(url, json=request_body, headers=headers)

            if response.status_code != 200:
                error_msg = f"{response.status_code}: {response.text[:500]}"
                logger.error(f"Imagen API error: {error_msg}")
                result.error_message = error_msg
                return result

            data = response.json()

            # Save debug response
            debug_file = Path(f"imagen_response_{int(time.time())}.json")
            with open(debug_file, "w") as f:
                json.dump(data, f, indent=2, default=str)
            logger.debug(f"Saved response to {debug_file}")

            # Extract image from response
            predictions = data.get("predictions", [])
            if not predictions:
                result.error_message = "No predictions in response"
                return result

            # Get first image
            image_data = predictions[0].get("bytesBase64Encoded")
            if not image_data:
                result.error_message = "No image data in response"
                return result

            # Decode and save
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(base64.b64decode(image_data))

            result.local_path = output_path
            logger.info(f"Saved image to {output_path}")

            return result

        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            result.error_message = str(e)
            return result
