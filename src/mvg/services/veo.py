"""Google Veo 3 API client wrapper via Vertex AI."""

from __future__ import annotations

import base64
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

import google.auth
import google.auth.transport.requests
import requests
from google.api_core import exceptions as google_exceptions
from google.cloud import aiplatform, storage

from ..config import config

logger = logging.getLogger(__name__)


class GenerationStatus(str, Enum):
    """Status of a Veo generation operation."""

    PENDING = "pending"
    STARTED = "started"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class GenerationResult:
    """Result of a Veo generation operation."""

    operation_id: str
    status: GenerationStatus
    output_uri: str | None = None
    local_path: Path | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    metadata: dict = field(default_factory=dict)


class VeoClient:
    """Client for Google Veo 3 video generation.

    Handles submitting video generation requests,
    polling for completion, and downloading results.
    """

    DEFAULT_LOCATION = "us-central1"
    DEFAULT_MODEL = "veo-3.1-fast-generate-001"
    DEFAULT_POLL_INTERVAL = 10.0
    DEFAULT_MAX_POLL_TIME = 600.0
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_DELAY = 2.0

    def __init__(
        self,
        project_id: str | None = None,
        location: str = DEFAULT_LOCATION,
        model: str | None = None,
        output_bucket: str | None = None,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        max_poll_time: float = DEFAULT_MAX_POLL_TIME,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
    ) -> None:
        """Initialize the Veo client.

        Args:
            project_id: Google Cloud project ID.
            location: GCP region for Vertex AI.
            model: Veo model name.
            output_bucket: GCS bucket for output videos.
            poll_interval: Seconds between poll checks.
            max_poll_time: Maximum seconds to wait.
            max_retries: Maximum retry attempts.
            retry_delay: Base delay between retries
                (exponential backoff).

        Raises:
            ValueError: If required configuration is
                missing.
        """
        self._project_id = (
            project_id or config.google_cloud_project
        )
        self._location = location
        self._model = (
            model or config.veo_model or self.DEFAULT_MODEL
        )
        self._output_bucket = (
            output_bucket or config.veo_output_bucket
        )
        self._poll_interval = poll_interval
        self._max_poll_time = max_poll_time
        self._max_retries = max_retries
        self._retry_delay = retry_delay

        self._validate_config()
        self._initialize_client()

    def _validate_config(self) -> None:
        """Validate that required configuration is set.

        Raises:
            ValueError: If required config is missing or
                invalid.
        """
        missing = []
        if not self._project_id:
            missing.append("GOOGLE_CLOUD_PROJECT")
        if not self._output_bucket:
            missing.append("VEO_OUTPUT_BUCKET")

        if missing:
            raise ValueError(
                "Missing required configuration: "
                f"{', '.join(missing)}. "
                "Set the corresponding environment "
                "variables."
            )

        if (
            self._output_bucket
            and not self._output_bucket.startswith("gs://")
        ):
            raise ValueError(
                "VEO_OUTPUT_BUCKET must be a GCS URI "
                "starting with 'gs://'. "
                f"Got: {self._output_bucket}"
            )

    def _initialize_client(self) -> None:
        """Initialize the Vertex AI client.

        Raises:
            Exception: If initialization fails.
        """
        try:
            aiplatform.init(
                project=self._project_id,
                location=self._location,
            )
            self._storage_client = storage.Client(
                project=self._project_id
            )
            logger.info(
                "Initialized Veo client for project %s "
                "in %s",
                self._project_id,
                self._location,
            )
        except Exception as e:
            logger.error(
                "Failed to initialize Vertex AI "
                "client: %s",
                e,
            )
            raise

    @property
    def project_id(self) -> str:
        """Return the Google Cloud project ID."""
        return self._project_id

    def generate_clip(
        self,
        prompt: str,
        duration: float = 8.0,
        aspect_ratio: str = "9:16",
        output_path: Path | None = None,
        scene_id: str | None = None,
        reference_image: Path | None = None,
    ) -> GenerationResult:
        """Generate a video clip from a text prompt.

        Args:
            prompt: Text description of the video.
            duration: Desired duration in seconds
                (Veo supports 5-8s).
            aspect_ratio: Video aspect ratio
                ('16:9' or '9:16').
            output_path: Local path to save the video.
            scene_id: Optional identifier for tracking.
            reference_image: Optional reference image path
                for character consistency.

        Returns:
            GenerationResult with operation details.

        Raises:
            ValueError: If prompt is empty or parameters
                are invalid.
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        if aspect_ratio not in ("16:9", "9:16"):
            raise ValueError(
                f"Invalid aspect_ratio: {aspect_ratio}. "
                "Must be '16:9' or '9:16'"
            )

        duration = max(5.0, min(8.0, duration))

        reference_image_b64 = None
        if reference_image and reference_image.exists():
            with open(reference_image, "rb") as f:
                reference_image_b64 = base64.b64encode(
                    f.read()
                ).decode("utf-8")
            logger.info(
                "Using reference image: %s",
                reference_image,
            )

        op_id = (
            f"veo-{scene_id or 'clip'}-{int(time.time())}"
        )
        result = GenerationResult(
            operation_id=op_id,
            status=GenerationStatus.PENDING,
            started_at=datetime.now(),
            metadata={
                "prompt": prompt,
                "duration": duration,
                "aspect_ratio": aspect_ratio,
                "scene_id": scene_id,
                "has_reference_image": (
                    reference_image_b64 is not None
                ),
            },
        )

        try:
            logger.info(
                "Starting Veo generation: %s", op_id
            )
            logger.debug("Prompt: %s...", prompt[:100])

            result.status = GenerationStatus.STARTED

            bucket_name = self._output_bucket.replace(
                "gs://", ""
            ).rstrip("/")
            output_uri = (
                f"gs://{bucket_name}/{op_id}.mp4"
            )

            response = self._submit_generation_request(
                prompt=prompt,
                duration=duration,
                aspect_ratio=aspect_ratio,
                output_uri=output_uri,
                reference_image_b64=reference_image_b64,
            )

            result.status = GenerationStatus.PROCESSING

            logger.info("Veo API response: %s", response)
            operation_name = response.get("name")
            if not operation_name:
                raise ValueError(
                    "No operation name in response: "
                    f"{response}"
                )

            final_result = self._poll_rest_operation(
                operation_name=operation_name,
                result=result,
            )

            if (
                final_result.status
                == GenerationStatus.COMPLETED
                and output_path
            ):
                self._save_video(final_result, output_path)

            return final_result

        except google_exceptions.ResourceExhausted as e:
            logger.error("Quota exceeded: %s", e)
            result.status = GenerationStatus.FAILED
            result.error_message = (
                f"Quota exceeded: {e}"
            )
            result.completed_at = datetime.now()
            return result

        except google_exceptions.DeadlineExceeded as e:
            logger.error("Request timed out: %s", e)
            result.status = GenerationStatus.FAILED
            result.error_message = f"Timeout: {e}"
            result.completed_at = datetime.now()
            return result

        except google_exceptions.GoogleAPICallError as e:
            logger.error("API error: %s", e)
            result.status = GenerationStatus.FAILED
            result.error_message = str(e)
            result.completed_at = datetime.now()
            return result

        except Exception as e:
            logger.error("Unexpected error: %s", e)
            result.status = GenerationStatus.FAILED
            result.error_message = str(e)
            result.completed_at = datetime.now()
            return result

    def _save_video(
        self,
        result: GenerationResult,
        output_path: Path,
    ) -> None:
        """Save generated video to local path.

        Handles both base64-encoded responses and GCS
        downloads.

        Args:
            result: The completed generation result.
            output_path: Local path to save the video.
        """
        if "video_base64" in result.metadata:
            video_data = base64.b64decode(
                result.metadata["video_base64"]
            )
            output_path.parent.mkdir(
                parents=True, exist_ok=True
            )
            with open(output_path, "wb") as f:
                f.write(video_data)
            result.local_path = output_path
            logger.info(
                "Saved generated video to %s",
                output_path,
            )
            del result.metadata["video_base64"]
        elif result.output_uri:
            try:
                self._download_from_gcs(
                    result.output_uri, output_path
                )
                result.local_path = output_path
                logger.info(
                    "Downloaded generated video to %s",
                    output_path,
                )
            except google_exceptions.NotFound:
                logger.error(
                    "Output file not found at %s",
                    result.output_uri,
                )
                result.error_message = (
                    "Output file not found at "
                    f"{result.output_uri}"
                )
        else:
            logger.warning(
                "No video data or URI found in response"
            )

    def _submit_generation_request(
        self,
        prompt: str,
        duration: float,
        aspect_ratio: str,
        output_uri: str,
        reference_image_b64: str | None = None,
    ) -> dict:
        """Submit a generation request via REST API.

        Args:
            prompt: Text description of the video.
            duration: Duration in seconds.
            aspect_ratio: Video aspect ratio.
            output_uri: GCS URI for output.
            reference_image_b64: Optional base64-encoded
                reference image.

        Returns:
            Parsed JSON response from the API.

        Raises:
            GoogleAPICallError: If the request fails.
        """
        scopes = [
            "https://www.googleapis.com/"
            "auth/cloud-platform"
        ]
        credentials, _ = google.auth.default(
            scopes=scopes
        )
        auth_req = (
            google.auth.transport.requests.Request()
        )
        credentials.refresh(auth_req)

        url = (
            f"https://{self._location}"
            "-aiplatform.googleapis.com/v1/"
            f"projects/{self._project_id}/"
            f"locations/{self._location}/"
            "publishers/google/"
            f"models/{self._model}:predictLongRunning"
        )

        aspect_ratio_map = {
            "16:9": "16:9",
            "9:16": "9:16",
            "16x9": "16:9",
            "9x16": "9:16",
            "1:1": "1:1",
        }
        veo_aspect_ratio = aspect_ratio_map.get(
            aspect_ratio, "9:16"
        )

        instance = {"prompt": prompt}

        parameters = {
            "aspectRatio": veo_aspect_ratio,
            "sampleCount": 1,
            "durationSeconds": int(duration),
            "generateAudio": False,
        }

        if reference_image_b64:
            parameters["referenceImages"] = [
                {
                    "referenceType": (
                        "REFERENCE_TYPE_STYLE"
                    ),
                    "referenceId": 1,
                    "image": {
                        "bytesBase64Encoded": (
                            reference_image_b64
                        ),
                    },
                }
            ]
            logger.info(
                "Including reference image for "
                "style consistency"
            )

        request_body = {
            "instances": [instance],
            "parameters": parameters,
        }

        headers = {
            "Authorization": (
                f"Bearer {credentials.token}"
            ),
            "Content-Type": "application/json",
        }

        logger.debug("Request URL: %s", url)
        logger.debug(
            "Request body keys: %s",
            list(request_body.keys()),
        )
        response = requests.post(
            url, json=request_body, headers=headers
        )

        if response.status_code != 200:
            raise google_exceptions.GoogleAPICallError(
                f"{response.status_code} {response.text}"
            )

        return response.json()

    def _poll_rest_operation(
        self,
        operation_name: str,
        result: GenerationResult,
    ) -> GenerationResult:
        """Poll a long-running operation until done.

        Args:
            operation_name: The operation resource name.
            result: The GenerationResult to update.

        Returns:
            Updated GenerationResult with final status.
        """
        start_time = time.time()
        poll_count = 0

        scopes = [
            "https://www.googleapis.com/"
            "auth/cloud-platform"
        ]
        credentials, _ = google.auth.default(
            scopes=scopes
        )
        auth_req = (
            google.auth.transport.requests.Request()
        )

        while True:
            elapsed = time.time() - start_time
            if elapsed > self._max_poll_time:
                logger.warning(
                    "Operation %s timed out after %.1fs",
                    operation_name,
                    elapsed,
                )
                result.status = GenerationStatus.FAILED
                result.error_message = (
                    "Operation timed out after "
                    f"{self._max_poll_time}s"
                )
                result.completed_at = datetime.now()
                return result

            poll_count += 1
            logger.debug(
                "Polling operation (attempt %d): %s",
                poll_count,
                operation_name,
            )

            try:
                credentials.refresh(auth_req)
                op_status = self._fetch_operation_status(
                    operation_name, credentials
                )

                if op_status is None:
                    time.sleep(self._poll_interval)
                    continue

                if op_status.get("done"):
                    self._save_debug_response(
                        op_status, result.operation_id
                    )
                    self._handle_completed_operation(
                        op_status,
                        operation_name,
                        result,
                    )
                    return result

                result.status = (
                    GenerationStatus.PROCESSING
                )

            except Exception as e:
                logger.warning(
                    "Error checking operation "
                    "status: %s",
                    e,
                )

            time.sleep(self._poll_interval)

    def _fetch_operation_status(
        self,
        operation_name: str,
        credentials: google.auth.credentials.Credentials,
    ) -> dict | None:
        """Fetch the status of an operation.

        Args:
            operation_name: The operation resource name.
            credentials: Refreshed auth credentials.

        Returns:
            Parsed status dict, or None if the request
            failed.
        """
        if "/publishers/google/models/" in operation_name:
            parts = operation_name.rsplit(
                "/operations/", 1
            )
            model_path = parts[0]
            url = (
                f"https://{self._location}"
                "-aiplatform.googleapis.com/v1/"
                f"{model_path}:fetchPredictOperation"
            )
            headers = {
                "Authorization": (
                    f"Bearer {credentials.token}"
                ),
                "Content-Type": "application/json",
            }
            body = {"operationName": operation_name}
            logger.debug("Polling URL: %s", url)
            response = requests.post(
                url, json=body, headers=headers
            )
        else:
            url = (
                f"https://{self._location}"
                "-aiplatform.googleapis.com/v1/"
                f"{operation_name}"
            )
            headers = {
                "Authorization": (
                    f"Bearer {credentials.token}"
                ),
            }
            logger.debug("Polling URL: %s", url)
            response = requests.get(url, headers=headers)

        if response.status_code != 200:
            logger.warning(
                "Poll request failed: %d",
                response.status_code,
            )
            logger.debug(
                "Response: %s", response.text[:500]
            )
            return None

        return response.json()

    def _save_debug_response(
        self, op_status: dict, operation_id: str
    ) -> None:
        """Save full API response for debugging.

        Args:
            op_status: The operation status dict.
            operation_id: ID for the debug filename.
        """
        debug_file = Path(
            f"veo_response_{operation_id}.json"
        )
        try:
            with open(debug_file, "w") as f:
                json.dump(
                    op_status, f, indent=2, default=str
                )
            logger.info(
                "Saved full response to %s", debug_file
            )
        except Exception as e:
            logger.warning(
                "Failed to save debug response: %s", e
            )

    def _handle_completed_operation(
        self,
        op_status: dict,
        operation_name: str,
        result: GenerationResult,
    ) -> None:
        """Handle a completed operation response.

        Args:
            op_status: The completed operation status.
            operation_name: The operation resource name.
            result: The GenerationResult to update.
        """
        if "error" in op_status:
            error = op_status["error"]
            error_msg = error.get(
                "message", str(error)
            )
            logger.error(
                "Operation %s failed: %s",
                operation_name,
                error_msg,
            )
            result.status = GenerationStatus.FAILED
            result.error_message = error_msg
            result.completed_at = datetime.now()
            return

        logger.info(
            "Operation %s completed successfully",
            operation_name,
        )
        result.status = GenerationStatus.COMPLETED
        result.completed_at = datetime.now()

        resp = op_status.get("response", {})
        self._extract_video_data(resp, result)

    def _extract_video_data(
        self, resp: dict, result: GenerationResult
    ) -> None:
        """Extract video data from the API response.

        Args:
            resp: The response payload.
            result: The GenerationResult to update.
        """
        if "videos" in resp and resp["videos"]:
            video = resp["videos"][0]
            if "bytesBase64Encoded" in video:
                result.metadata["video_base64"] = (
                    video["bytesBase64Encoded"]
                )
                result.metadata["mime_type"] = (
                    video.get("mimeType", "video/mp4")
                )
                logger.info(
                    "Video data received as base64"
                )
            elif "uri" in video or "gcsUri" in video:
                result.output_uri = video.get(
                    "uri"
                ) or video.get("gcsUri")
                logger.info(
                    "Output URI: %s", result.output_uri
                )
        elif "generateVideoResponse" in resp:
            gen_resp = resp["generateVideoResponse"]
            samples = gen_resp.get(
                "generatedSamples", []
            )
            if samples:
                video = samples[0].get("video", {})
                if "bytesBase64Encoded" in video:
                    result.metadata["video_base64"] = (
                        video["bytesBase64Encoded"]
                    )
                    result.metadata["mime_type"] = (
                        video.get(
                            "mimeType", "video/mp4"
                        )
                    )
                    logger.info(
                        "Video data received as base64"
                    )

    def _download_from_gcs(
        self, gcs_uri: str, local_path: Path
    ) -> None:
        """Download a file from GCS to local path.

        Args:
            gcs_uri: GCS URI (gs://bucket/path/to/file).
            local_path: Local path to save the file.

        Raises:
            ValueError: If the GCS URI is invalid.
            google_exceptions.NotFound: If the file is
                not in GCS.
        """
        if not gcs_uri.startswith("gs://"):
            raise ValueError(
                f"Invalid GCS URI: {gcs_uri}"
            )

        uri_parts = gcs_uri[5:].split("/", 1)
        if len(uri_parts) != 2:
            raise ValueError(
                f"Invalid GCS URI format: {gcs_uri}"
            )

        bucket_name, blob_name = uri_parts
        local_path.parent.mkdir(
            parents=True, exist_ok=True
        )

        for attempt in range(self._max_retries):
            try:
                bucket = self._storage_client.bucket(
                    bucket_name
                )
                blob = bucket.blob(blob_name)
                blob.download_to_filename(str(local_path))
                logger.debug(
                    "Downloaded %s to %s",
                    gcs_uri,
                    local_path,
                )
                return

            except google_exceptions.NotFound:
                logger.error(
                    "File not found in GCS: %s", gcs_uri
                )
                raise

            except Exception as e:
                delay = self._retry_delay * (
                    2**attempt
                )
                logger.warning(
                    "Download failed (attempt %d): %s. "
                    "Retrying in %ds...",
                    attempt + 1,
                    e,
                    delay,
                )
                if attempt == self._max_retries - 1:
                    raise
                time.sleep(delay)


def save_generation_metadata(
    results: list[GenerationResult],
    output_path: Path,
) -> None:
    """Save generation metadata to a JSON file.

    Args:
        results: List of generation results.
        output_path: Path to save the metadata JSON.
    """
    metadata = {
        "generated_at": datetime.now().isoformat(),
        "total_scenes": len(results),
        "successful": sum(
            1
            for r in results
            if r.status == GenerationStatus.COMPLETED
        ),
        "failed": sum(
            1
            for r in results
            if r.status == GenerationStatus.FAILED
        ),
        "operations": [
            {
                "operation_id": r.operation_id,
                "status": r.status.value,
                "output_uri": r.output_uri,
                "local_path": (
                    str(r.local_path)
                    if r.local_path
                    else None
                ),
                "error_message": r.error_message,
                "started_at": (
                    r.started_at.isoformat()
                    if r.started_at
                    else None
                ),
                "completed_at": (
                    r.completed_at.isoformat()
                    if r.completed_at
                    else None
                ),
                "metadata": r.metadata,
            }
            for r in results
        ],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(
        "Saved generation metadata to %s", output_path
    )
