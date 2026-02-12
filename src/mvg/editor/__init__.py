"""Video editing and assembly module."""

from .compositor import (
    stitch_clips,
    add_transitions,
    export,
    resize_clip,
    crop_to_aspect,
)
from .overlays import (
    TextStyle,
    STYLES,
    render_text,
    apply_style,
    position_overlay,
    add_text_overlay,
    get_style,
    register_style,
)
from .audio import (
    load_audio,
    sync_audio,
    loop_audio,
    fade_audio,
    adjust_volume,
    mix_audio,
    extract_audio,
    get_audio_duration,
)

__all__ = [
    # Compositor
    "stitch_clips",
    "add_transitions",
    "export",
    "resize_clip",
    "crop_to_aspect",
    # Overlays
    "TextStyle",
    "STYLES",
    "render_text",
    "apply_style",
    "position_overlay",
    "add_text_overlay",
    "get_style",
    "register_style",
    # Audio
    "load_audio",
    "sync_audio",
    "loop_audio",
    "fade_audio",
    "adjust_volume",
    "mix_audio",
    "extract_audio",
    "get_audio_duration",
]
