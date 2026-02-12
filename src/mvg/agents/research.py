"""Research agent for scene generation."""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..models import Scene
from .base import BaseAgent

logger = logging.getLogger(__name__)

# Load prompt template
PROMPT_TEMPLATE_PATH = Path(__file__).parent.parent.parent.parent / "templates" / "prompts" / "research.txt"


def _load_system_prompt() -> str:
    """Load the system prompt from template file."""
    if PROMPT_TEMPLATE_PATH.exists():
        return PROMPT_TEMPLATE_PATH.read_text()
    # Fallback inline prompt if template not found
    return """You are a creative director specializing in video content creation.
Your task is to generate scene descriptions for video generation.

Output valid JSON only, with no additional text or markdown formatting.
The JSON should be an object with a "scenes" array containing scene objects."""


@dataclass
class ResearchInput:
    """Input data for the research agent."""

    idea: str
    duration: int
    num_scenes: Optional[int] = None
    style: Optional[str] = None


class ResearchAgent(BaseAgent[ResearchInput, list[Scene]]):
    """Agent for generating video scenes from an idea.

    Takes a creative idea and generates a structured list of scenes
    with Veo-compatible prompts, durations, and narrative flow.
    """

    @property
    def name(self) -> str:
        """Return the agent's name."""
        return "ResearchAgent"

    @property
    def system_prompt(self) -> str:
        """Return the system prompt for scene generation."""
        return _load_system_prompt()

    def run(self, input_data: ResearchInput) -> list[Scene]:
        """Generate scenes from the input idea.

        Args:
            input_data: Research input containing idea, duration, and options.

        Returns:
            List of Scene objects with prompts and durations.

        Raises:
            ValueError: If the response cannot be parsed as valid scenes.
        """
        self._logger.info(
            f"Generating scenes for: '{input_data.idea}' "
            f"(duration: {input_data.duration}s)"
        )

        # Build the user prompt
        prompt = self._build_prompt(input_data)

        # Get response from Claude
        response = self._create_message(
            prompt=prompt,
            max_tokens=4096,
            temperature=0.8,  # Higher temperature for creative output
        )

        # Parse and validate the response
        scenes = self._parse_response(response, input_data.duration)

        self._logger.info(f"Generated {len(scenes)} scenes")
        return scenes

    def _build_prompt(self, input_data: ResearchInput) -> str:
        """Build the user prompt for scene generation."""
        prompt_parts = [
            f"Create a video scene breakdown for the following idea:",
            f"",
            f"IDEA: {input_data.idea}",
            f"TOTAL DURATION: {input_data.duration} seconds",
        ]

        if input_data.num_scenes:
            prompt_parts.append(f"NUMBER OF SCENES: {input_data.num_scenes}")
        else:
            # Suggest scene count based on duration
            suggested = max(3, input_data.duration // 10)
            prompt_parts.append(
                f"SUGGESTED SCENES: {suggested} (adjust as needed for pacing)"
            )

        if input_data.style:
            prompt_parts.append(f"VISUAL STYLE: {input_data.style}")

        prompt_parts.extend([
            "",
            "Generate a JSON response with scene descriptions.",
            "Each scene should have cinematic, visually detailed prompts suitable for AI video generation.",
            "Ensure the scenes form a cohesive narrative with good pacing.",
        ])

        return "\n".join(prompt_parts)

    def _parse_response(self, response: str, target_duration: int) -> list[Scene]:
        """Parse Claude's response into Scene objects.

        Args:
            response: Raw response from Claude.
            target_duration: Target total duration for adjusting scene times.

        Returns:
            List of validated Scene objects.

        Raises:
            ValueError: If response cannot be parsed as valid JSON with scenes.
        """
        # Try to extract JSON from the response
        json_str = self._extract_json(response)

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            self._logger.error(f"Failed to parse JSON: {e}")
            self._logger.debug(f"Raw response: {response}")
            raise ValueError(f"Invalid JSON in response: {e}")

        # Handle different response formats
        scenes_data = data.get("scenes", data) if isinstance(data, dict) else data

        if not isinstance(scenes_data, list):
            raise ValueError("Response does not contain a scenes array")

        # Convert to Scene objects
        scenes: list[Scene] = []
        for i, scene_data in enumerate(scenes_data):
            scene = Scene(
                id=scene_data.get("id", f"scene_{i + 1}"),
                prompt=scene_data.get("prompt", ""),
                duration=float(scene_data.get("duration", 5.0)),
                source="generate",
                overlay_text=scene_data.get("overlay_text"),
                overlay_style=scene_data.get("overlay_style"),
            )
            scenes.append(scene)

        # Adjust durations to match target
        scenes = self._adjust_durations(scenes, target_duration)

        return scenes

    def _extract_json(self, response: str) -> str:
        """Extract JSON from a response that may contain markdown or other text."""
        # Try to find JSON in code blocks
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            if end > start:
                return response[start:end].strip()

        if "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end > start:
                return response[start:end].strip()

        # Try to find raw JSON object or array
        for start_char, end_char in [("{", "}"), ("[", "]")]:
            start = response.find(start_char)
            if start != -1:
                # Find matching end bracket
                depth = 0
                for i, char in enumerate(response[start:], start):
                    if char == start_char:
                        depth += 1
                    elif char == end_char:
                        depth -= 1
                        if depth == 0:
                            return response[start:i + 1]

        # Return as-is if no JSON structure found
        return response.strip()

    def _adjust_durations(
        self, scenes: list[Scene], target_duration: int
    ) -> list[Scene]:
        """Adjust scene durations to match the target total duration.

        Args:
            scenes: List of scenes with initial durations.
            target_duration: Target total duration in seconds.

        Returns:
            Scenes with adjusted durations.
        """
        if not scenes:
            return scenes

        current_total = sum(scene.duration for scene in scenes)

        if current_total == 0:
            # Distribute evenly if no durations set
            per_scene = target_duration / len(scenes)
            for scene in scenes:
                scene.duration = round(per_scene, 1)
            return scenes

        # Scale durations proportionally
        scale_factor = target_duration / current_total

        for scene in scenes:
            scene.duration = round(scene.duration * scale_factor, 1)

        # Adjust for rounding errors
        adjusted_total = sum(scene.duration for scene in scenes)
        if adjusted_total != target_duration:
            diff = target_duration - adjusted_total
            scenes[-1].duration = round(scenes[-1].duration + diff, 1)

        return scenes
