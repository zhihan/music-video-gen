"""Text overlay rendering for video clips."""

from __future__ import annotations

import textwrap
from dataclasses import dataclass, field

from moviepy import CompositeVideoClip, TextClip, VideoClip

# Default text width for a 1080px-wide (9:16) canvas
TEXT_WIDTH = 680


@dataclass
class TextStyle:
    """Configuration for text overlay styling."""

    font: str = "Arial"
    font_size: int = 50
    color: str = "white"
    stroke_color: str | None = None
    stroke_width: int = 0
    background_color: str | None = "#000000AA"
    background_padding: tuple[int, int] = field(
        default_factory=lambda: (10, 5)
    )
    chars_per_line: int = 24
    max_lines: int = 5
    text_width: int = TEXT_WIDTH


# Preset styles for 9:16 canvas with TEXT_WIDTH=680
STYLES: dict[str, TextStyle] = {
    "title": TextStyle(
        font_size=70,
        chars_per_line=17,
        max_lines=2,
    ),
    "text": TextStyle(
        font_size=50,
        chars_per_line=24,
        max_lines=5,
    ),
    "subtitle": TextStyle(
        font_size=40,
        chars_per_line=30,
        max_lines=3,
    ),
}
STYLES["default"] = STYLES["text"]


def wrap_text(
    text: str, chars_per_line: int, max_lines: int
) -> str:
    """Word-wrap text within character limits.

    Breaks at word boundaries using textwrap. If the
    text exceeds max_lines, it is truncated with '...'
    on the last visible line.

    Args:
        text: The text to wrap.
        chars_per_line: Maximum characters per line.
        max_lines: Maximum number of lines.

    Returns:
        Wrapped text with newlines.
    """
    lines = textwrap.wrap(text, width=chars_per_line)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        if len(last) > chars_per_line - 3:
            last = last[: chars_per_line - 3]
        lines[-1] = last.rstrip() + "..."
    return "\n".join(lines)


def calc_text_height(
    line_count: int, font_size: int
) -> int:
    """Calculate text box height.

    Uses line_height=1.4x and padding=0.3x.

    Args:
        line_count: Number of text lines.
        font_size: Font size in pixels.

    Returns:
        Height in pixels.
    """
    line_height = int(font_size * 1.4)
    return line_height * line_count + int(
        font_size * 0.3
    )


def render_text(
    text: str,
    style: TextStyle | None = None,
    duration: float | None = None,
) -> TextClip:
    """Create a text clip with word wrapping.

    Args:
        text: Text content to render.
        style: TextStyle configuration. Uses default
            if None.
        duration: Duration of the text clip in seconds.

    Returns:
        TextClip with the styled text.
    """
    if style is None:
        style = STYLES["default"]

    wrapped = wrap_text(
        text, style.chars_per_line, style.max_lines
    )
    line_count = wrapped.count("\n") + 1
    text_height = calc_text_height(
        line_count, style.font_size
    )

    params: dict = {
        "text": wrapped,
        "font": style.font,
        "font_size": style.font_size,
        "color": style.color,
        "size": (style.text_width, text_height),
        "method": "caption",
        "text_align": "center",
        "vertical_align": "top",
    }

    if style.stroke_color and style.stroke_width > 0:
        params["stroke_color"] = style.stroke_color
        params["stroke_width"] = style.stroke_width

    if style.background_color:
        params["bg_color"] = style.background_color

    text_clip = TextClip(**params)

    if duration is not None:
        text_clip = text_clip.with_duration(duration)

    return text_clip


def apply_style(
    text_clip: TextClip, style_name: str
) -> TextClip:
    """Apply a preset style to a text clip.

    Args:
        text_clip: Existing text clip.
        style_name: Name of the preset style.

    Returns:
        Text clip with the new style (recreated).

    Raises:
        ValueError: If style_name is not found.
    """
    if style_name not in STYLES:
        raise ValueError(
            f"Unknown style: {style_name}. "
            f"Available: {list(STYLES.keys())}"
        )

    return render_text(
        text=(
            text_clip.text
            if hasattr(text_clip, "text")
            else ""
        ),
        style=STYLES[style_name],
        duration=text_clip.duration,
    )


def position_overlay(
    text_clip: TextClip,
    position: str = "center",
    margin: int = 50,
) -> TextClip:
    """Position a text overlay on the screen.

    Args:
        text_clip: Text clip to position.
        position: Position name. Options: "center",
            "top", "bottom", "top-left", "top-right",
            "bottom-left", "bottom-right".
        margin: Margin from edges in pixels.

    Returns:
        Text clip with position set.

    Raises:
        ValueError: If position is unknown.
    """
    position_map = {
        "center": ("center", "center"),
        "top": ("center", margin),
        "bottom": ("center", -margin),
        "top-left": (margin, margin),
        "top-right": (-margin, margin),
        "bottom-left": (margin, -margin),
        "bottom-right": (-margin, -margin),
    }

    if position not in position_map:
        if isinstance(position, tuple):
            return text_clip.with_position(position)
        raise ValueError(
            f"Unknown position: {position}. "
            f"Available: {list(position_map.keys())}"
        )

    pos = position_map[position]

    if isinstance(pos[1], int) and pos[1] < 0:
        return text_clip.with_position(
            (pos[0], lambda t: ("center", pos[1]))
        )

    return text_clip.with_position(pos)


def add_text_overlay(
    video: VideoClip,
    text: str,
    position: str = "bottom",
    style_name: str = "default",
    start_time: float = 0.0,
    duration: float | None = None,
) -> CompositeVideoClip:
    """Add a text overlay to a video clip.

    Args:
        video: Video clip to add overlay to.
        text: Text content.
        position: Position of the text overlay.
        style_name: Name of the text style preset.
        start_time: When the text appears (seconds).
        duration: How long the text appears. None for
            full video duration.

    Returns:
        Composite video clip with text overlay.
    """
    if style_name not in STYLES:
        style_name = "default"

    style = STYLES[style_name]

    if duration is None:
        duration = (
            video.duration - start_time
            if video.duration
            else None
        )

    text_clip = render_text(text, style, duration)
    text_clip = position_overlay(text_clip, position)

    if start_time > 0:
        text_clip = text_clip.with_start(start_time)

    return CompositeVideoClip([video, text_clip])


def get_style(name: str) -> TextStyle:
    """Get a text style by name.

    Args:
        name: Style name.

    Returns:
        TextStyle configuration.

    Raises:
        ValueError: If style not found.
    """
    if name not in STYLES:
        raise ValueError(
            f"Unknown style: {name}. "
            f"Available: {list(STYLES.keys())}"
        )
    return STYLES[name]


def register_style(
    name: str, style: TextStyle
) -> None:
    """Register a custom text style.

    Args:
        name: Name for the style.
        style: TextStyle configuration.
    """
    STYLES[name] = style
