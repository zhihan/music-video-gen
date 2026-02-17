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
        scene_defs.append(
            f'    "{scene.id}": {{"duration": {scene.duration}, "overlay_text": {overlay_text}}},'
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

# Text styling constants (adjust these to change all text at once)
TEXT_WIDTH = {int(width * 0.85)}  # 85% of video width
FONT_SIZE = 48
FONT = "Arial"
TEXT_COLOR = "white"
TEXT_BG = "#000000AA"  # Semi-transparent black background
TEXT_MARGIN = 80  # Margin from bottom edge

# Height constants based on text length (adjust if text is clipped)
TEXT_1LINE_H = 80
TEXT_2LINE_H = 120
TEXT_3LINE_H = 180
TEXT_4LINE_H = 240

# =============================================================================
# SCENE DATA (from script.yaml)
# =============================================================================

SCENES = {{
{scenes_dict}
}}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def estimate_text_height(text: str, width: int, font_size: int) -> int:
    """Estimate text height based on character count and width."""
    if not text:
        return TEXT_1LINE_H
    # Rough estimate: ~15 chars per line at standard font size
    chars_per_line = width // (font_size * 0.6)
    lines = max(1, len(text) // int(chars_per_line) + 1)
    if lines == 1:
        return TEXT_1LINE_H
    elif lines == 2:
        return TEXT_2LINE_H
    elif lines == 3:
        return TEXT_3LINE_H
    else:
        return TEXT_4LINE_H


def create_text_overlay(
    text: str,
    duration: float,
    video_size: tuple[int, int],
) -> TextClip:
    """Create a text overlay clip with semi-transparent background."""
    width, height = video_size
    text_height = estimate_text_height(text, TEXT_WIDTH, FONT_SIZE)

    text_clip = TextClip(
        text=text,
        font=FONT,
        font_size=FONT_SIZE,
        color=TEXT_COLOR,
        bg_color=TEXT_BG,
        size=(TEXT_WIDTH, text_height),
        method="caption",  # Enables word wrapping
        text_align="center",
        vertical_align="center",
    )
    text_clip = text_clip.with_duration(duration)

    # Position at bottom with margin
    text_clip = text_clip.with_position(
        ("center", height - text_height - TEXT_MARGIN)
    )

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
        text_clip = create_text_overlay(
            text=overlay_text,
            duration=clip.duration,
            video_size=(VIDEO_WIDTH, VIDEO_HEIGHT),
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
