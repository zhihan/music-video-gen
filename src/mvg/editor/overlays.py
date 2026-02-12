"""Text overlay rendering for video clips."""

from dataclasses import dataclass, field
from typing import Optional, Tuple

from moviepy import TextClip, VideoClip, CompositeVideoClip


@dataclass
class TextStyle:
    """Configuration for text overlay styling."""

    font: str = "Arial"
    font_size: int = 48
    color: str = "white"
    stroke_color: Optional[str] = "black"
    stroke_width: int = 2
    background_color: Optional[str] = None
    background_padding: Tuple[int, int] = field(default_factory=lambda: (10, 5))


# Preset styles
STYLES = {
    "default": TextStyle(),
    "title": TextStyle(font_size=72, stroke_width=3),
    "subtitle": TextStyle(font_size=36, stroke_width=1),
    "caption": TextStyle(
        font_size=32,
        background_color="rgba(0,0,0,0.7)",
        stroke_color=None,
        stroke_width=0
    ),
    "minimal": TextStyle(
        font_size=42,
        stroke_color=None,
        stroke_width=0
    ),
}


def render_text(
    text: str,
    style: Optional[TextStyle] = None,
    duration: Optional[float] = None
) -> TextClip:
    """Create a text clip with the given style.

    Args:
        text: Text content to render.
        style: TextStyle configuration. Uses default if None.
        duration: Duration of the text clip in seconds.

    Returns:
        TextClip with the styled text.
    """
    if style is None:
        style = STYLES["default"]

    # Build TextClip parameters
    params = {
        "text": text,
        "font": style.font,
        "font_size": style.font_size,
        "color": style.color,
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


def apply_style(text_clip: TextClip, style_name: str) -> TextClip:
    """Apply a preset style to a text clip.

    Args:
        text_clip: Existing text clip.
        style_name: Name of the preset style to apply.

    Returns:
        Text clip with the new style (recreated).

    Raises:
        ValueError: If style_name is not found.
    """
    if style_name not in STYLES:
        raise ValueError(f"Unknown style: {style_name}. Available: {list(STYLES.keys())}")

    # Get the text content and duration
    # Note: We need to recreate the clip with new style
    return render_text(
        text=text_clip.text if hasattr(text_clip, 'text') else "",
        style=STYLES[style_name],
        duration=text_clip.duration
    )


def position_overlay(
    text_clip: TextClip,
    position: str = "center",
    margin: int = 50
) -> TextClip:
    """Position a text overlay on the screen.

    Args:
        text_clip: Text clip to position.
        position: Position name. Options:
            - "center": Center of screen
            - "top": Top center
            - "bottom": Bottom center
            - "top-left", "top-right"
            - "bottom-left", "bottom-right"
        margin: Margin from edges in pixels.

    Returns:
        Text clip with position set.
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
        # Allow tuple positions like (100, 200)
        if isinstance(position, tuple):
            return text_clip.with_position(position)
        raise ValueError(f"Unknown position: {position}. Available: {list(position_map.keys())}")

    pos = position_map[position]

    # Handle negative margins for bottom/right positioning
    if isinstance(pos[1], int) and pos[1] < 0:
        # Bottom positioning
        return text_clip.with_position((pos[0], lambda t: ("center", pos[1])))

    return text_clip.with_position(pos)


def add_text_overlay(
    video: VideoClip,
    text: str,
    position: str = "bottom",
    style_name: str = "default",
    start_time: float = 0.0,
    duration: Optional[float] = None
) -> CompositeVideoClip:
    """Add a text overlay to a video clip.

    Args:
        video: Video clip to add overlay to.
        text: Text content.
        position: Position of the text overlay.
        style_name: Name of the text style preset.
        start_time: When the text appears (seconds).
        duration: How long the text appears. None for full video duration.

    Returns:
        Composite video clip with text overlay.
    """
    if style_name not in STYLES:
        style_name = "default"

    style = STYLES[style_name]

    # Calculate duration
    if duration is None:
        duration = video.duration - start_time if video.duration else None

    # Create and position text
    text_clip = render_text(text, style, duration)
    text_clip = position_overlay(text_clip, position)

    # Set start time
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
        raise ValueError(f"Unknown style: {name}. Available: {list(STYLES.keys())}")
    return STYLES[name]


def register_style(name: str, style: TextStyle) -> None:
    """Register a custom text style.

    Args:
        name: Name for the style.
        style: TextStyle configuration.
    """
    STYLES[name] = style
