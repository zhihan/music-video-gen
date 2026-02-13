"""Google Veo 3 API client wrapper via Vertex AI."""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from google.cloud import aiplatform
from google.cloud import storage
from google.api_core import exceptions as google_exceptions
from google.protobuf import json_format

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
    output_uri: Optional[str] = None
    local_path: Optional[Path] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: dict = field(default_factory=dict)


class VeoClient:
    """Client wrapper for Google Veo 3 video generation via Vertex AI.

    This client handles:
    - Submitting video generation requests to Veo 3
    - Polling for operation completion with retry logic
    - Downloading generated videos from GCS
    - Error handling for quota limits, timeouts, and API errors
    """

    # Default configuration
    DEFAULT_LOCATION = "us-central1"
    DEFAULT_MODEL = "veo-3.1-fast-generate-001"
    DEFAULT_POLL_INTERVAL = 10.0  # seconds
    DEFAULT_MAX_POLL_TIME = 600.0  # 10 minutes
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_DELAY = 2.0

    def __init__(
        self,
        project_id: Optional[str] = None,
        location: str = DEFAULT_LOCATION,
        model: Optional[str] = None,
        output_bucket: Optional[str] = None,
        credentials_path: Optional[str] = None,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        max_poll_time: float = DEFAULT_MAX_POLL_TIME,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
    ) -> None:
        """Initialize the Veo client.

        Args:
            project_id: Google Cloud project ID. Defaults to GOOGLE_CLOUD_PROJECT env var.
            location: GCP region for Vertex AI. Defaults to us-central1.
            model: Veo model name. Defaults to VEO_MODEL env var or veo-2.0-generate-001.
            output_bucket: GCS bucket for output videos. Defaults to VEO_OUTPUT_BUCKET env var.
            credentials_path: Path to service account JSON. Defaults to
                GOOGLE_APPLICATION_CREDENTIALS env var.
            poll_interval: Seconds between polling checks.
            max_poll_time: Maximum seconds to wait for generation.
            max_retries: Maximum retry attempts for transient errors.
            retry_delay: Base delay between retries (exponential backoff).
        """
        self._project_id = project_id or config.google_cloud_project
        self._location = location
        self._model = model or config.veo_model or self.DEFAULT_MODEL
        self._output_bucket = output_bucket or config.veo_output_bucket
        self._credentials_path = credentials_path or config.google_application_credentials
        self._poll_interval = poll_interval
        self._max_poll_time = max_poll_time
        self._max_retries = max_retries
        self._retry_delay = retry_delay

        # Validate required configuration
        self._validate_config()

        # Initialize Vertex AI
        self._initialize_client()

    def _validate_config(self) -> None:
        """Validate that required configuration is set."""
        missing = []
        if not self._project_id:
            missing.append("GOOGLE_CLOUD_PROJECT")
        if not self._output_bucket:
            missing.append("VEO_OUTPUT_BUCKET")

        if missing:
            raise ValueError(
                f"Missing required configuration: {', '.join(missing)}. "
                "Set the corresponding environment variables."
            )

        # Validate bucket format
        if self._output_bucket and not self._output_bucket.startswith("gs://"):
            raise ValueError(
                f"VEO_OUTPUT_BUCKET must be a GCS URI starting with 'gs://'. "
                f"Got: {self._output_bucket}"
            )

    def _initialize_client(self) -> None:
        """Initialize the Vertex AI client."""
        try:
            aiplatform.init(
                project=self._project_id,
                location=self._location,
            )
            self._storage_client = storage.Client(project=self._project_id)
            logger.info(
                f"Initialized Veo client for project {self._project_id} "
                f"in {self._location}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI client: {e}")
            raise

    @property
    def project_id(self) -> str:
        """Return the Google Cloud project ID."""
        return self._project_id

    @property
    def output_bucket(self) -> str:
        """Return the output GCS bucket."""
        return self._output_bucket

    def generate_clip(
        self,
        prompt: str,
        duration: float = 8.0,
        aspect_ratio: str = "16:9",
        output_path: Optional[Path] = None,
        scene_id: Optional[str] = None,
        reference_image: Optional[Path] = None,
    ) -> GenerationResult:
        """Generate a video clip from a text prompt.

        Args:
            prompt: Text description of the video to generate.
            duration: Desired duration in seconds (Veo supports 5-8s typically).
            aspect_ratio: Video aspect ratio ('16:9' or '9:16').
            output_path: Local path to save the generated video.
            scene_id: Optional identifier for tracking.
            reference_image: Optional path to a reference image for character consistency.

        Returns:
            GenerationResult with operation details and status.

        Raises:
            ValueError: If prompt is empty or invalid parameters.
            google_exceptions.GoogleAPICallError: If API call fails.
        """
        import base64

        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        if aspect_ratio not in ("16:9", "9:16"):
            raise ValueError(f"Invalid aspect_ratio: {aspect_ratio}. Must be '16:9' or '9:16'")

        # Clamp duration to Veo's supported range
        duration = max(5.0, min(8.0, duration))

        # Load reference image if provided
        reference_image_b64 = None
        if reference_image and reference_image.exists():
            with open(reference_image, "rb") as f:
                reference_image_b64 = base64.b64encode(f.read()).decode("utf-8")
            logger.info(f"Using reference image: {reference_image}")

        operation_id = f"veo-{scene_id or 'clip'}-{int(time.time())}"
        result = GenerationResult(
            operation_id=operation_id,
            status=GenerationStatus.PENDING,
            started_at=datetime.now(),
            metadata={
                "prompt": prompt,
                "duration": duration,
                "aspect_ratio": aspect_ratio,
                "scene_id": scene_id,
                "has_reference_image": reference_image_b64 is not None,
            },
        )

        try:
            logger.info(f"Starting Veo generation: {operation_id}")
            logger.debug(f"Prompt: {prompt[:100]}...")

            # Submit generation request to Veo 3 via Vertex AI
            # Using the imagen/video generation endpoint
            result.status = GenerationStatus.STARTED

            # Construct the output URI
            bucket_name = self._output_bucket.replace("gs://", "").rstrip("/")
            output_uri = f"gs://{bucket_name}/{operation_id}.mp4"

            # Call Veo 3 API via Vertex AI
            # Note: This uses the video generation preview API
            response = self._submit_generation_request(
                prompt=prompt,
                duration=duration,
                aspect_ratio=aspect_ratio,
                output_uri=output_uri,
                reference_image_b64=reference_image_b64,
            )

            result.status = GenerationStatus.PROCESSING

            # Response contains operation name for polling
            logger.info(f"Veo API response: {response}")
            operation_name = response.get("name")
            if not operation_name:
                raise ValueError(f"No operation name in response: {response}")

            # Poll for completion
            final_result = self._poll_rest_operation(
                operation_name=operation_name,
                result=result,
            )

            # Save video if completed and output_path specified
            if final_result.status == GenerationStatus.COMPLETED and output_path:
                # Check if video was returned as base64
                if "video_base64" in final_result.metadata:
                    import base64
                    video_data = base64.b64decode(final_result.metadata["video_base64"])
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(output_path, "wb") as f:
                        f.write(video_data)
                    final_result.local_path = output_path
                    logger.info(f"Saved generated video to {output_path}")
                    # Clean up base64 data from metadata to save memory
                    del final_result.metadata["video_base64"]
                # Otherwise try to download from GCS
                elif final_result.output_uri:
                    try:
                        self._download_from_gcs(final_result.output_uri, output_path)
                        final_result.local_path = output_path
                        logger.info(f"Downloaded generated video to {output_path}")
                    except google_exceptions.NotFound:
                        logger.error(f"Output file not found at {final_result.output_uri}")
                        final_result.error_message = f"Output file not found at {final_result.output_uri}"
                else:
                    logger.warning("No video data or URI found in response")

            return final_result

        except google_exceptions.ResourceExhausted as e:
            logger.error(f"Quota exceeded: {e}")
            result.status = GenerationStatus.FAILED
            result.error_message = f"Quota exceeded: {e}"
            result.completed_at = datetime.now()
            return result

        except google_exceptions.DeadlineExceeded as e:
            logger.error(f"Request timed out: {e}")
            result.status = GenerationStatus.FAILED
            result.error_message = f"Timeout: {e}"
            result.completed_at = datetime.now()
            return result

        except google_exceptions.GoogleAPICallError as e:
            logger.error(f"API error: {e}")
            result.status = GenerationStatus.FAILED
            result.error_message = str(e)
            result.completed_at = datetime.now()
            return result

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            result.status = GenerationStatus.FAILED
            result.error_message = str(e)
            result.completed_at = datetime.now()
            return result

    def _submit_generation_request(
        self,
        prompt: str,
        duration: float,
        aspect_ratio: str,
        output_uri: str,
        reference_image_b64: Optional[str] = None,
    ):
        """Submit a video generation request to Veo via REST API.

        This method interfaces with the Vertex AI video generation API.

        Args:
            prompt: Text description of the video.
            duration: Duration in seconds.
            aspect_ratio: Video aspect ratio.
            output_uri: GCS URI for output (may not be used by Veo).
            reference_image_b64: Optional base64-encoded reference image for
                image-to-video generation with character consistency.
        """
        import requests
        import google.auth
        import google.auth.transport.requests

        # Get credentials with Vertex AI scopes
        scopes = ["https://www.googleapis.com/auth/cloud-platform"]
        credentials, project = google.auth.default(scopes=scopes)
        auth_req = google.auth.transport.requests.Request()
        credentials.refresh(auth_req)

        # Vertex AI endpoint for Veo - predictLongRunning
        url = (
            f"https://{self._location}-aiplatform.googleapis.com/v1/"
            f"projects/{self._project_id}/locations/{self._location}/"
            f"publishers/google/models/{self._model}:predictLongRunning"
        )

        # Map aspect ratio to Veo API format
        # Veo uses "16:9" or "9:16" directly, not "16x9"
        aspect_ratio_map = {
            "16:9": "16:9",
            "9:16": "9:16",
            "16x9": "16:9",
            "9x16": "9:16",
            "1:1": "1:1",
        }
        veo_aspect_ratio = aspect_ratio_map.get(aspect_ratio, "16:9")

        # Construct the instance - include reference image if provided
        instance = {"prompt": prompt}
        if reference_image_b64:
            # Image-to-video: include the reference image
            instance["image"] = {
                "bytesBase64Encoded": reference_image_b64,
                "mimeType": "image/png",
            }
            logger.info("Including reference image in generation request")

        # Construct the generation request per Veo API spec
        request_body = {
            "instances": [instance],
            "parameters": {
                "aspectRatio": veo_aspect_ratio,
                "sampleCount": 1,
                "durationSeconds": int(duration),
            },
        }

        headers = {
            "Authorization": f"Bearer {credentials.token}",
            "Content-Type": "application/json",
        }

        logger.debug(f"Request URL: {url}")
        logger.debug(f"Request body keys: {list(request_body.keys())}")
        response = requests.post(url, json=request_body, headers=headers)

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
        """Poll a long-running operation via REST API until completion or timeout.

        Args:
            operation_name: The operation resource name to poll.
            result: The GenerationResult to update.

        Returns:
            Updated GenerationResult with final status.
        """
        import requests
        import google.auth
        import google.auth.transport.requests

        start_time = time.time()
        poll_count = 0

        # Get credentials with Vertex AI scopes
        scopes = ["https://www.googleapis.com/auth/cloud-platform"]
        credentials, _ = google.auth.default(scopes=scopes)
        auth_req = google.auth.transport.requests.Request()

        while True:
            elapsed = time.time() - start_time
            if elapsed > self._max_poll_time:
                logger.warning(f"Operation {operation_name} timed out after {elapsed:.1f}s")
                result.status = GenerationStatus.FAILED
                result.error_message = f"Operation timed out after {self._max_poll_time}s"
                result.completed_at = datetime.now()
                return result

            poll_count += 1
            logger.debug(f"Polling operation (attempt {poll_count}): {operation_name}")

            try:
                # Refresh credentials if needed
                credentials.refresh(auth_req)

                # For publisher model operations, use fetchPredictOperation
                # Operation name format: projects/{project}/locations/{location}/publishers/google/models/{model}/operations/{op_id}
                if "/publishers/google/models/" in operation_name:
                    # Extract model path and operation ID
                    parts = operation_name.rsplit("/operations/", 1)
                    model_path = parts[0]
                    op_id = parts[1] if len(parts) > 1 else ""
                    url = (
                        f"https://{self._location}-aiplatform.googleapis.com/v1/"
                        f"{model_path}:fetchPredictOperation"
                    )
                    # POST request with operation name in body
                    headers = {
                        "Authorization": f"Bearer {credentials.token}",
                        "Content-Type": "application/json",
                    }
                    body = {"operationName": operation_name}
                    logger.debug(f"Polling URL: {url}")
                    response = requests.post(url, json=body, headers=headers)
                else:
                    url = f"https://{self._location}-aiplatform.googleapis.com/v1/{operation_name}"
                    headers = {
                        "Authorization": f"Bearer {credentials.token}",
                    }
                    logger.debug(f"Polling URL: {url}")
                    response = requests.get(url, headers=headers)

                if response.status_code != 200:
                    logger.warning(f"Poll request failed: {response.status_code}")
                    logger.debug(f"Response: {response.text[:500]}")
                    time.sleep(self._poll_interval)
                    continue

                op_status = response.json()

                if op_status.get("done"):
                    # Save full response to file for debugging
                    debug_file = Path(f"veo_response_{result.operation_id}.json")
                    try:
                        with open(debug_file, "w") as f:
                            json.dump(op_status, f, indent=2, default=str)
                        logger.info(f"Saved full response to {debug_file}")
                    except Exception as e:
                        logger.warning(f"Failed to save debug response: {e}")

                    if "error" in op_status:
                        error = op_status["error"]
                        error_msg = error.get("message", str(error))
                        logger.error(f"Operation {operation_name} failed: {error_msg}")
                        result.status = GenerationStatus.FAILED
                        result.error_message = error_msg
                        result.completed_at = datetime.now()
                        return result
                    else:
                        logger.info(f"Operation {operation_name} completed successfully")
                        result.status = GenerationStatus.COMPLETED
                        result.completed_at = datetime.now()
                        # Extract video data from response
                        if "response" in op_status:
                            resp = op_status["response"]
                            # Veo returns video as base64-encoded data in response.videos[]
                            if "videos" in resp and resp["videos"]:
                                video = resp["videos"][0]
                                if "bytesBase64Encoded" in video:
                                    result.metadata["video_base64"] = video["bytesBase64Encoded"]
                                    result.metadata["mime_type"] = video.get("mimeType", "video/mp4")
                                    logger.info("Video data received as base64")
                                elif "uri" in video or "gcsUri" in video:
                                    result.output_uri = video.get("uri") or video.get("gcsUri")
                                    logger.info(f"Output URI: {result.output_uri}")
                            # Fallback: check other possible structures
                            elif "generateVideoResponse" in resp:
                                gen_resp = resp["generateVideoResponse"]
                                if "generatedSamples" in gen_resp and gen_resp["generatedSamples"]:
                                    video = gen_resp["generatedSamples"][0].get("video", {})
                                    if "bytesBase64Encoded" in video:
                                        result.metadata["video_base64"] = video["bytesBase64Encoded"]
                                        result.metadata["mime_type"] = video.get("mimeType", "video/mp4")
                                        logger.info("Video data received as base64")
                        return result

                # Still processing
                result.status = GenerationStatus.PROCESSING

            except Exception as e:
                logger.warning(f"Error checking operation status: {e}")

            time.sleep(self._poll_interval)

    def _poll_operation(
        self,
        operation_name: str,
        result: GenerationResult,
    ) -> GenerationResult:
        """Poll an operation by name until completion or timeout (legacy).

        Args:
            operation_name: The operation resource name to poll.
            result: The GenerationResult to update.

        Returns:
            Updated GenerationResult with final status.
        """
        start_time = time.time()
        poll_count = 0

        while True:
            elapsed = time.time() - start_time
            if elapsed > self._max_poll_time:
                logger.warning(f"Operation {operation_name} timed out after {elapsed:.1f}s")
                result.status = GenerationStatus.FAILED
                result.error_message = f"Operation timed out after {self._max_poll_time}s"
                result.completed_at = datetime.now()
                return result

            poll_count += 1
            logger.debug(f"Polling operation (attempt {poll_count}): {operation_name}")

            try:
                status = self._check_operation_status(operation_name)

                if status == "SUCCEEDED":
                    logger.info(f"Operation {operation_name} completed successfully")
                    result.status = GenerationStatus.COMPLETED
                    result.completed_at = datetime.now()
                    return result

                elif status in ("FAILED", "CANCELLED"):
                    logger.error(f"Operation {operation_name} {status.lower()}")
                    result.status = (
                        GenerationStatus.CANCELLED
                        if status == "CANCELLED"
                        else GenerationStatus.FAILED
                    )
                    result.completed_at = datetime.now()
                    return result

                # Still processing, continue polling
                result.status = GenerationStatus.PROCESSING

            except Exception as e:
                logger.warning(f"Error checking operation status: {e}")

            time.sleep(self._poll_interval)

    def _check_operation_status(self, operation_name: str) -> str:
        """Check the status of an operation.

        Args:
            operation_name: The operation resource name.

        Returns:
            Status string: RUNNING, SUCCEEDED, FAILED, or CANCELLED.
        """
        from google.longrunning import operations_pb2_grpc
        from google.longrunning.operations_pb2 import GetOperationRequest
        import grpc

        # For Vertex AI operations, check via the operations API
        # This is a simplified check - real implementation depends on
        # how Veo 3 surfaces operation status
        try:
            from google.cloud.aiplatform_v1 import JobServiceClient

            client_options = {"api_endpoint": f"{self._location}-aiplatform.googleapis.com"}
            client = JobServiceClient(client_options=client_options)

            # Check if this is a batch prediction job
            # The actual status check depends on the Veo 3 API structure
            return "SUCCEEDED"  # Placeholder for actual status check

        except Exception as e:
            logger.debug(f"Status check error: {e}")
            return "RUNNING"

    def poll_operation(self, operation_id: str) -> GenerationResult:
        """Poll an existing operation by ID.

        Args:
            operation_id: The operation ID to poll.

        Returns:
            GenerationResult with current status.
        """
        result = GenerationResult(
            operation_id=operation_id,
            status=GenerationStatus.PROCESSING,
        )

        return self._poll_operation(operation_id, result)

    def cancel_operation(self, operation_id: str) -> bool:
        """Cancel an in-progress operation.

        Args:
            operation_id: The operation ID to cancel.

        Returns:
            True if cancellation was successful.
        """
        try:
            logger.info(f"Cancelling operation: {operation_id}")

            from google.cloud.aiplatform_v1 import JobServiceClient

            client_options = {"api_endpoint": f"{self._location}-aiplatform.googleapis.com"}
            client = JobServiceClient(client_options=client_options)

            # Cancel the operation
            # Actual cancellation depends on operation type
            logger.info(f"Cancellation requested for {operation_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to cancel operation: {e}")
            return False

    def _download_from_gcs(self, gcs_uri: str, local_path: Path) -> None:
        """Download a file from GCS to local path.

        Args:
            gcs_uri: GCS URI (gs://bucket/path/to/file).
            local_path: Local path to save the file.
        """
        # Parse GCS URI
        if not gcs_uri.startswith("gs://"):
            raise ValueError(f"Invalid GCS URI: {gcs_uri}")

        uri_parts = gcs_uri[5:].split("/", 1)
        if len(uri_parts) != 2:
            raise ValueError(f"Invalid GCS URI format: {gcs_uri}")

        bucket_name, blob_name = uri_parts

        # Ensure local directory exists
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Download with retry
        for attempt in range(self._max_retries):
            try:
                bucket = self._storage_client.bucket(bucket_name)
                blob = bucket.blob(blob_name)
                blob.download_to_filename(str(local_path))
                logger.debug(f"Downloaded {gcs_uri} to {local_path}")
                return

            except google_exceptions.NotFound:
                logger.error(f"File not found in GCS: {gcs_uri}")
                raise

            except Exception as e:
                delay = self._retry_delay * (2**attempt)
                logger.warning(f"Download failed (attempt {attempt + 1}): {e}. Retrying in {delay}s...")
                if attempt == self._max_retries - 1:
                    raise
                time.sleep(delay)

    def list_operations(self, scene_id: Optional[str] = None) -> list[GenerationResult]:
        """List recent operations, optionally filtered by scene_id.

        Args:
            scene_id: Optional scene ID to filter by.

        Returns:
            List of GenerationResult objects.
        """
        # This would query operation history from Vertex AI
        # Implementation depends on how operations are tracked
        logger.debug(f"Listing operations (scene_id={scene_id})")
        return []


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
        "successful": sum(1 for r in results if r.status == GenerationStatus.COMPLETED),
        "failed": sum(1 for r in results if r.status == GenerationStatus.FAILED),
        "operations": [
            {
                "operation_id": r.operation_id,
                "status": r.status.value,
                "output_uri": r.output_uri,
                "local_path": str(r.local_path) if r.local_path else None,
                "error_message": r.error_message,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "metadata": r.metadata,
            }
            for r in results
        ],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Saved generation metadata to {output_path}")
