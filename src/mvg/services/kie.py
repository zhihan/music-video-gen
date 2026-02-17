"""KIE.ai (Suno) upload-and-cover API client."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

import requests

from ..config import config

logger = logging.getLogger(__name__)

BASE_URL = "https://api.kie.ai/api/v1"
UPLOAD_URL = "https://kieai.redpandaai.co/api"

# Status values from /generate/record-info endpoint.
_SUCCESS_STATES = {"SUCCESS", "FIRST_SUCCESS"}
_FAIL_STATES = {
    "CREATE_TASK_FAILED",
    "GENERATE_AUDIO_FAILED",
    "CALLBACK_EXCEPTION",
    "SENSITIVE_WORD_ERROR",
}
_PENDING_STATES = {"PENDING", "TEXT_SUCCESS"}


@dataclass
class MusicResult:
    """Result of a KIE.ai music generation."""

    task_id: str
    status: str = "PENDING"
    audio_url: str | None = None
    local_path: Path | None = None
    title: str | None = None
    duration: float | None = None
    error_message: str | None = None
    metadata: dict = field(default_factory=dict)


class KieClient:
    """Client for KIE.ai upload-and-cover endpoint.

    Uploads an audio URL for Suno to cover/remix, then
    polls for completion and downloads the result.
    """

    DEFAULT_MODEL = "V5"
    DEFAULT_POLL_INTERVAL = 30.0
    DEFAULT_MAX_POLL_TIME = 600.0

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        max_poll_time: float = DEFAULT_MAX_POLL_TIME,
    ) -> None:
        """Initialize the KIE client.

        Args:
            api_key: KIE.ai API key. Falls back to
                config.
            model: Suno model version (V4, V4_5,
                V4_5PLUS, V4_5ALL, V5).
            poll_interval: Seconds between poll checks.
            max_poll_time: Maximum seconds to wait for
                generation.

        Raises:
            ValueError: If API key is not provided.
        """
        self._api_key = api_key or config.kie_api_key
        if not self._api_key:
            raise ValueError(
                "KIE_API_KEY not set. "
                "Get your API key at https://kie.ai/"
            )
        self._model = model
        self._poll_interval = poll_interval
        self._max_poll_time = max_poll_time
        self._headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def upload_file(self, file_path: Path) -> str:
        """Upload a local audio file to KIE.ai.

        Uses the file-stream-upload endpoint. Files are
        retained for 3 days.

        Args:
            file_path: Path to the local audio file.

        Returns:
            Public URL of the uploaded file.

        Raises:
            FileNotFoundError: If file does not exist.
            ValueError: If the upload fails.
        """
        if not file_path.exists():
            raise FileNotFoundError(
                f"File not found: {file_path}"
            )

        logger.info(
            "Uploading %s to KIE.ai", file_path
        )

        with open(file_path, "rb") as f:
            resp = requests.post(
                f"{UPLOAD_URL}/file-stream-upload",
                files={"file": (
                    file_path.name, f,
                )},
                data={
                    "uploadPath": "music",
                },
                headers={
                    "Authorization": (
                        f"Bearer {self._api_key}"
                    ),
                },
            )

        if resp.status_code != 200:
            raise ValueError(
                f"Upload failed ({resp.status_code}): "
                f"{resp.text[:500]}"
            )

        data = resp.json()
        logger.debug("Upload response: %s", data)

        if not data.get("success"):
            raise ValueError(
                f"Upload failed: "
                f"{data.get('msg', 'Unknown error')}"
            )

        inner = data.get("data") or {}
        file_url = (
            inner.get("fileUrl")
            or inner.get("downloadUrl")
            or ""
        )
        if not file_url:
            raise ValueError(
                "No fileUrl in upload response: "
                f"{data}"
            )

        logger.info("Uploaded to: %s", file_url)
        return file_url

    def upload_and_cover(
        self,
        audio_file: Path,
        prompt: str,
        style: str | None = None,
        title: str | None = None,
        instrumental: bool = False,
        vocal_gender: str | None = None,
        negative_tags: str | None = None,
        output_path: Path | None = None,
    ) -> MusicResult:
        """Upload a local audio file and cover it.

        Uploads the file to KIE.ai, then submits an
        upload-and-cover request to Suno.

        Args:
            audio_file: Path to the local source audio
                (max 8 minutes, 1 min for V4_5ALL).
            prompt: Text description or lyrics prompt.
            style: Music style tags (e.g. "Pop, Upbeat").
                Enables custom mode when provided.
            title: Song title (used with custom mode).
            instrumental: If True, generate instrumental
                only.
            vocal_gender: Vocal gender ("m" or "f").
            negative_tags: Tags to avoid.
            output_path: Local path to save the audio.

        Returns:
            MusicResult with generation details.
        """
        # Upload local file first.
        try:
            upload_url = self.upload_file(audio_file)
        except (FileNotFoundError, ValueError) as e:
            return MusicResult(
                task_id="",
                status="FAILED",
                error_message=f"Upload failed: {e}",
            )

        custom_mode = style is not None

        body: dict = {
            "uploadUrl": upload_url,
            "prompt": prompt,
            "customMode": custom_mode,
            "instrumental": instrumental,
            "model": self._model,
            "callBackUrl": "https://example.com/noop",
        }

        if custom_mode:
            body["style"] = style or ""
            body["title"] = title or ""

        body["weirdnessConstraint"] = 0.10
        body["audioWeight"] = 0.99
        body["styleWeight"] = 0.80

        if vocal_gender:
            body["vocalGender"] = vocal_gender

        if negative_tags:
            body["negativeTags"] = negative_tags

        logger.info(
            "Submitting upload-and-cover request"
        )
        logger.debug("Request body: %s", body)

        try:
            resp = requests.post(
                f"{BASE_URL}/generate/upload-cover",
                json=body,
                headers=self._headers,
            )
        except requests.RequestException as e:
            return MusicResult(
                task_id="",
                status="FAILED",
                error_message=f"Request failed: {e}",
            )

        if resp.status_code != 200:
            return MusicResult(
                task_id="",
                status="FAILED",
                error_message=(
                    f"API error {resp.status_code}: "
                    f"{resp.text[:500]}"
                ),
            )

        data = resp.json()
        logger.debug("Response: %s", data)

        # Check for API-level error codes.
        api_code = data.get("code")
        if api_code and api_code != 200:
            return MusicResult(
                task_id="",
                status="FAILED",
                error_message=(
                    f"API error {api_code}: "
                    f"{data.get('msg', 'Unknown error')}"
                ),
            )

        # Extract task ID.
        inner = data.get("data") or {}
        task_id = (
            inner.get("taskId")
            or data.get("taskId")
            or ""
        )

        if not task_id:
            return MusicResult(
                task_id="",
                status="FAILED",
                error_message=(
                    f"No taskId in response: {data}"
                ),
            )

        result = MusicResult(
            task_id=task_id,
            status="PENDING",
            title=title,
            metadata={
                "upload_url": upload_url,
                "prompt": prompt,
                "style": style,
                "model": self._model,
                "instrumental": instrumental,
            },
        )

        logger.info("Task submitted: %s", task_id)

        # Poll until completion.
        result = self._poll_task(result)

        # Download audio if successful.
        if (
            result.status in _SUCCESS_STATES
            and result.audio_url
            and output_path
        ):
            self._download_audio(
                result.audio_url, output_path
            )
            result.local_path = output_path

        return result

    def _poll_task(
        self, result: MusicResult
    ) -> MusicResult:
        """Poll task status until completion.

        Uses the /generate/record-info endpoint.
        Recommended poll interval is 30s (max 3 req/s).

        Args:
            result: MusicResult to update in place.

        Returns:
            Updated MusicResult with final status.
        """
        start_time = time.time()
        poll_count = 0

        while True:
            elapsed = time.time() - start_time
            if elapsed > self._max_poll_time:
                logger.warning(
                    "Task %s timed out after %.1fs",
                    result.task_id,
                    elapsed,
                )
                result.status = "FAILED"
                result.error_message = (
                    "Task timed out after "
                    f"{self._max_poll_time}s"
                )
                return result

            poll_count += 1
            logger.debug(
                "Polling task (attempt %d): %s",
                poll_count,
                result.task_id,
            )

            try:
                resp = requests.get(
                    f"{BASE_URL}/generate/record-info",
                    params={"taskId": result.task_id},
                    headers=self._headers,
                )

                if resp.status_code != 200:
                    logger.warning(
                        "Poll request failed: %d",
                        resp.status_code,
                    )
                    time.sleep(self._poll_interval)
                    continue

                data = resp.json()
                logger.debug("Poll response: %s", data)

                record = data.get("data") or {}
                if not record:
                    time.sleep(self._poll_interval)
                    continue

                status = record.get("status", "")
                result.status = status

                if status in _SUCCESS_STATES:
                    self._extract_result(
                        record, result
                    )
                    return result

                if status in _FAIL_STATES:
                    result.error_message = (
                        record.get("errorMessage")
                        or f"Generation failed: {status}"
                    )
                    return result

                # Log progress.
                if status in _PENDING_STATES:
                    logger.info(
                        "Task %s: %s (%.0fs elapsed)",
                        result.task_id,
                        status,
                        elapsed,
                    )

            except requests.RequestException as e:
                logger.warning(
                    "Error polling task: %s", e
                )

            time.sleep(self._poll_interval)

    def _extract_result(
        self, record: dict, result: MusicResult
    ) -> None:
        """Extract audio URL and metadata from record.

        Args:
            record: The task record from record-info.
            result: MusicResult to update.
        """
        response = record.get("response") or {}
        audio_list = response.get("sunoData", [])

        if audio_list:
            audio = audio_list[0]
            result.audio_url = audio.get("audioUrl")
            result.title = (
                result.title or audio.get("title")
            )
            result.duration = audio.get("duration")
            result.metadata["audio_id"] = audio.get(
                "id"
            )
            result.metadata["tags"] = audio.get(
                "tags"
            )
            result.metadata["image_url"] = audio.get(
                "imageUrl"
            )

            logger.info(
                "Audio ready: %s (%.1fs)",
                result.title or "untitled",
                result.duration or 0,
            )

    def _download_audio(
        self, url: str, output_path: Path
    ) -> None:
        """Download audio file from URL.

        Args:
            url: Audio file URL.
            output_path: Local path to save the file.

        Raises:
            requests.RequestException: If download fails.
        """
        logger.info(
            "Downloading audio to %s", output_path
        )
        output_path.parent.mkdir(
            parents=True, exist_ok=True
        )

        resp = requests.get(url, stream=True)
        resp.raise_for_status()

        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(
                chunk_size=8192
            ):
                f.write(chunk)

        logger.info(
            "Downloaded audio: %s", output_path
        )
