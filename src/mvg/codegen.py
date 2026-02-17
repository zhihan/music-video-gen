"""Code generation for MoviePy assembly scripts."""

from pathlib import Path

from .models import Manifest


def generate_assembly_script(
    manifest: Manifest,
    clips_dir: Path,
    output_video: Path,
) -> str:
    """Generate a MoviePy script that assembles clips with text overlays.

    Args:
        manifest: Project manifest with scenes and overlay text.
        clips_dir: Directory containing video clips.
        output_video: Output video file path.

    Returns:
        Python script content as a string.
    """
    # Build scene definitions
    scene_defs = []
    for scene in manifest.scenes:
        overlay_text = repr(scene.overlay_text) if scene.overlay_text else "None"
        overlay_style = repr(scene.overlay_style) if scene.overlay_style else '"text"'
        scene_defs.append(
            f'    "{scene.id}": {{"duration": {scene.duration},'
            f' "overlay_text": {overlay_text},'
            f' "overlay_style": {overlay_style}}},'
        )
    scenes_dict = "\n".join(scene_defs)

    # Determine video dimensions based on aspect ratio
    if manifest.aspect_ratio == "16:9":
        width, height = 1920, 1080
    else:  # Default to 9:16 vertical
        width, height = 1080, 1920

    script = f'''#!/usr/bin/env python3
"""
Auto-generated MoviePy assembly script for: {manifest.project_name}

This script adds text overlays to video clips based on script.yaml.
Feel free to adjust text sizing, positioning, and styling as needed.

Usage:
    python scripts/assembly.py

To refine with Claude:
    "The text on scene X is too small, make it larger"
    "Move the overlay up, it's covering the subject's face"
    "Add a fade-in effect to the text"
"""

import textwrap
from pathlib import Path
from moviepy import (
    VideoFileClip,
    TextClip,
    CompositeVideoClip,
    concatenate_videoclips,
)

# =============================================================================
# CONFIGURATION - Adjust these values as needed
# =============================================================================

CLIPS_DIR = Path("{clips_dir}")
OUTPUT_PATH = Path("{output_video}")
VIDEO_WIDTH = {width}
VIDEO_HEIGHT = {height}

# Common styling
TEXT_WIDTH = 680
FONT = "Arial"
TEXT_COLOR = "white"
TEXT_BG = "#000000AA"  # Semi-transparent black background

# Text presets: font_size, chars_per_line, max_lines
# Based on sampler testing with TEXT_WIDTH=680 on 1080x1920 canvas
PRESETS = {{
    "title": {{"font_size": 70, "chars_per_line": 17, "max_lines": 2}},
    "text":  {{"font_size": 50, "chars_per_line": 24, "max_lines": 5}},
    "subtitle": {{"font_size": 40, "chars_per_line": 30, "max_lines": 3}},
}}

# =============================================================================
# SCENE DATA (from script.yaml)
# =============================================================================

SCENES = {{
{scenes_dict}
}}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def wrap_text(text: str, chars_per_line: int, max_lines: int) -> str:
    """Word-wrap text at word boundaries, capped at max_lines."""
    lines = textwrap.wrap(text, width=chars_per_line)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        if len(last) > chars_per_line - 3:
            last = last[:chars_per_line - 3]
        lines[-1] = last.rstrip() + "..."
    return "\\n".join(lines)


def calc_text_height(line_count: int, font_size: int) -> int:
    """Calculate text box height from line count and font size."""
    line_height = int(font_size * 1.4)
    return line_height * line_count + int(font_size * 0.3)


def create_text_overlay(
    text: str,
    duration: float,
    video_size: tuple[int, int],
    preset: str = "text",
) -> TextClip:
    """Create a text overlay clip with word wrapping and semi-transparent background."""
    width, height = video_size
    cfg = PRESETS.get(preset, PRESETS["text"])
    font_size = cfg["font_size"]

    wrapped = wrap_text(text, cfg["chars_per_line"], cfg["max_lines"])
    line_count = wrapped.count("\\n") + 1
    text_height = calc_text_height(line_count, font_size)

    text_clip = TextClip(
        text=wrapped,
        font=FONT,
        font_size=font_size,
        color=TEXT_COLOR,
        bg_color=TEXT_BG,
        size=(TEXT_WIDTH, text_height),
        method="caption",
        text_align="center",
        vertical_align="top",
    )
    text_clip = text_clip.with_duration(duration)

    # Position at 75% down the screen
    y_position = int(height * 0.75) - text_height // 2
    text_clip = text_clip.with_position(("center", y_position))

    return text_clip


def load_and_process_clip(scene_id: str, scene_data: dict) -> VideoFileClip:
    """Load a clip and add text overlay if specified."""
    clip_path = CLIPS_DIR / f"{{scene_id}}.mp4"

    if not clip_path.exists():
        raise FileNotFoundError(f"Clip not found: {{clip_path}}")

    # Load the video clip
    clip = VideoFileClip(str(clip_path))

    # Resize/crop to target dimensions if needed
    if clip.size != (VIDEO_WIDTH, VIDEO_HEIGHT):
        clip = clip.resized(height=VIDEO_HEIGHT)
        if clip.size[0] > VIDEO_WIDTH:
            # Center crop
            x_center = clip.size[0] // 2
            x1 = x_center - VIDEO_WIDTH // 2
            clip = clip.cropped(x1=x1, x2=x1 + VIDEO_WIDTH)

    # Add text overlay if present
    overlay_text = scene_data.get("overlay_text")
    if overlay_text:
        preset = scene_data.get("overlay_style", "text")
        text_clip = create_text_overlay(
            text=overlay_text,
            duration=clip.duration,
            video_size=(VIDEO_WIDTH, VIDEO_HEIGHT),
            preset=preset,
        )
        clip = CompositeVideoClip([clip, text_clip])

    return clip


# =============================================================================
# MAIN ASSEMBLY
# =============================================================================

def main():
    """Assemble all clips with text overlays."""
    print(f"Assembling video: {manifest.project_name}")
    print(f"Output: {{OUTPUT_PATH}}")
    print()

    clips = []
    for scene_id, scene_data in SCENES.items():
        print(f"  Processing {{scene_id}}...")
        try:
            clip = load_and_process_clip(scene_id, scene_data)
            clips.append(clip)
            overlay = scene_data.get("overlay_text", "")
            if overlay:
                preview = overlay[:40] + "..." if len(overlay) > 40 else overlay
                print(f"    Text: {{preview}}")
        except FileNotFoundError as e:
            print(f"    WARNING: {{e}}")
            continue

    if not clips:
        print("No clips found to assemble!")
        return

    print()
    print(f"Concatenating {{len(clips)}} clips...")

    # Concatenate all clips
    final = concatenate_videoclips(clips, method="compose")

    # Ensure output directory exists
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Export
    print(f"Rendering to {{OUTPUT_PATH}}...")
    final.write_videofile(
        str(OUTPUT_PATH),
        fps=30,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
    )

    print()
    print(f"Done! Output: {{OUTPUT_PATH}}")
    print(f"Duration: {{final.duration:.1f}}s")

    # Cleanup
    final.close()
    for clip in clips:
        clip.close()


if __name__ == "__main__":
    main()
'''

    return script
