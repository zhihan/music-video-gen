"""Anthropic Claude API client wrapper."""

import logging
import time
from typing import Optional

from anthropic import Anthropic, APIError, APIConnectionError, RateLimitError

from ..config import config

logger = logging.getLogger(__name__)


class AnthropicClient:
    """Client wrapper for Anthropic Claude API with retry logic."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        """Initialize the Anthropic client.

        Args:
            api_key: Anthropic API key. Defaults to ANTHROPIC_API_KEY env var.
            model: Model to use. Defaults to config.default_model.
            max_retries: Maximum number of retry attempts for failed requests.
            retry_delay: Base delay between retries in seconds (exponential backoff).
        """
        self._api_key = api_key or config.anthropic_api_key
        if not self._api_key:
            raise ValueError(
                "Anthropic API key not provided. Set ANTHROPIC_API_KEY env var."
            )

        self._client = Anthropic(api_key=self._api_key)
        self._model = model or config.default_model
        self._max_retries = max_retries
        self._retry_delay = retry_delay

    @property
    def model(self) -> str:
        """Return the model being used."""
        return self._model

    def create_message(
        self,
        prompt: str,
        max_tokens: int = 4096,
        system: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        """Create a message using Claude.

        Args:
            prompt: The user prompt to send.
            max_tokens: Maximum tokens in the response.
            system: Optional system prompt.
            temperature: Sampling temperature (0.0-1.0).

        Returns:
            The text content of Claude's response.

        Raises:
            APIError: If the API request fails after all retries.
        """
        messages = [{"role": "user", "content": prompt}]

        for attempt in range(self._max_retries):
            try:
                logger.debug(
                    f"Sending request to Claude (attempt {attempt + 1}/{self._max_retries})"
                )

                kwargs = {
                    "model": self._model,
                    "max_tokens": max_tokens,
                    "messages": messages,
                    "temperature": temperature,
                }
                if system:
                    kwargs["system"] = system

                response = self._client.messages.create(**kwargs)

                # Extract text content from response
                content = response.content[0]
                if hasattr(content, "text"):
                    return content.text
                return str(content)

            except RateLimitError as e:
                delay = self._retry_delay * (2**attempt)
                logger.warning(f"Rate limited. Retrying in {delay:.1f}s...")
                time.sleep(delay)
                if attempt == self._max_retries - 1:
                    raise

            except APIConnectionError as e:
                delay = self._retry_delay * (2**attempt)
                logger.warning(f"Connection error: {e}. Retrying in {delay:.1f}s...")
                time.sleep(delay)
                if attempt == self._max_retries - 1:
                    raise

            except APIError as e:
                logger.error(f"API error: {e}")
                raise

        raise APIError("Max retries exceeded")
