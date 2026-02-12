"""Base agent abstraction."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar, Optional

from ..services.anthropic import AnthropicClient
from ..config import config

logger = logging.getLogger(__name__)

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class BaseAgent(ABC, Generic[InputT, OutputT]):
    """Abstract base class for AI agents.

    Provides shared functionality for agents that use Claude for generation.
    Subclasses must implement the `run` method and define their prompts.
    """

    def __init__(
        self,
        client: Optional[AnthropicClient] = None,
        model: Optional[str] = None,
    ) -> None:
        """Initialize the agent.

        Args:
            client: AnthropicClient instance. Created if not provided.
            model: Model to use. Defaults to config.default_model.
        """
        self._model = model or config.default_model
        self._client = client or AnthropicClient(model=self._model)
        self._logger = logging.getLogger(f"{__name__}.{self.name}")

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the agent's name."""
        ...

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        ...

    @property
    def model(self) -> str:
        """Return the model being used."""
        return self._model

    @abstractmethod
    def run(self, input_data: InputT) -> OutputT:
        """Execute the agent's main task.

        Args:
            input_data: Input data for the agent.

        Returns:
            Structured output from the agent.
        """
        ...

    def _create_message(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """Create a message using the agent's client and system prompt.

        Args:
            prompt: The user prompt to send.
            max_tokens: Maximum tokens in the response.
            temperature: Sampling temperature.

        Returns:
            The text content of Claude's response.
        """
        self._logger.debug(f"Creating message with prompt length: {len(prompt)}")

        try:
            response = self._client.create_message(
                prompt=prompt,
                max_tokens=max_tokens,
                system=self.system_prompt,
                temperature=temperature,
            )
            self._logger.debug(f"Received response of length: {len(response)}")
            return response

        except Exception as e:
            self._logger.error(f"Error creating message: {e}")
            raise
