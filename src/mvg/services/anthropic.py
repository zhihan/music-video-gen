"""Anthropic Claude API client wrapper."""

from __future__ import annotations

import logging
import time

from anthropic import (
    Anthropic,
    APIConnectionError,
    APIError,
    RateLimitError,
)

from ..config import config

logger = logging.getLogger(__name__)


class AnthropicClient:
    """Client wrapper for Anthropic Claude API.

    Includes retry logic with exponential backoff for
    transient errors.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        """Initialize the Anthropic client.

        Args:
            api_key: Anthropic API key. Defaults to
                ANTHROPIC_API_KEY env var.
            model: Model to use. Defaults to
                config.default_model.
            max_retries: Maximum retry attempts for failed
                requests.
            retry_delay: Base delay between retries in
                seconds (exponential backoff).

        Raises:
            ValueError: If no API key is provided or found.
        """
        self._api_key = api_key or config.anthropic_api_key
        if not self._api_key:
            raise ValueError(
                "Anthropic API key not provided. "
                "Set ANTHROPIC_API_KEY env var."
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
        system: str | None = None,
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
            APIError: If the request fails after all
                retries.
        """
        messages = [{"role": "user", "content": prompt}]

        for attempt in range(self._max_retries):
            try:
                logger.debug(
                    "Sending request to Claude "
                    "(attempt %d/%d)",
                    attempt + 1,
                    self._max_retries,
                )

                kwargs = {
                    "model": self._model,
                    "max_tokens": max_tokens,
                    "messages": messages,
                    "temperature": temperature,
                }
                if system:
                    kwargs["system"] = system

                response = self._client.messages.create(
                    **kwargs
                )

                content = response.content[0]
                if hasattr(content, "text"):
                    return content.text
                return str(content)

            except RateLimitError:
                delay = self._retry_delay * (2**attempt)
                logger.warning(
                    "Rate limited. Retrying in %.1fs...",
                    delay,
                )
                time.sleep(delay)
                if attempt == self._max_retries - 1:
                    raise

            except APIConnectionError as e:
                delay = self._retry_delay * (2**attempt)
                logger.warning(
                    "Connection error: %s. "
                    "Retrying in %.1fs...",
                    e,
                    delay,
                )
                time.sleep(delay)
                if attempt == self._max_retries - 1:
                    raise

            except APIError as e:
                logger.error("API error: %s", e)
                raise

        raise APIError("Max retries exceeded")
