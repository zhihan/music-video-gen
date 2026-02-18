#!/usr/bin/env python3
"""Auto-generated MoviePy assembly script.

Project: Pressed Into Gold

Adds text overlays to video clips based on script.yaml.
Adjust text sizing, positioning, and styling as needed.

Usage:
    python scripts/assembly.py
"""

import textwrap
from pathlib import Path

from moviepy import (
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    TextClip,
    VideoFileClip,
    concatenate_videoclips,
    vfx,
)

# ============================================================
# CONFIGURATION
# ============================================================

CLIPS_DIR = Path("clips")
AUDIO_PATH = Path("song.mp3")
OUTPUT_PATH = Path("output/final.mp4")
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920

TEXT_WIDTH = 960
FONT = "Arial"
TEXT_COLOR = "white"
TEXT_BG = "#000000AA"

PRESETS = {
    "title": {
        "font_size": 105,
        "chars_per_line": 17,
        "max_lines": 2,
    },
    "text": {
        "font_size": 75,
        "chars_per_line": 24,
        "max_lines": 5,
    },
    "subtitle": {
        "font_size": 60,
        "chars_per_line": 30,
        "max_lines": 3,
    },
}

# ============================================================
# SCENE DATA (from script.yaml)
# ============================================================

SCENES = {
    "harvest_press": {"duration": 8.0, "overlay_text": 'Olives that have known no pressure. No oil can bestow.', "overlay_style": 'text'},
    "winepress": {"duration": 8.0, "overlay_text": 'If the grapes escape the winepress / Cheering wine can never flow.', "overlay_style": 'text'},
    "perfumer": {"duration": 8.0, "overlay_text": 'Spikenard only through the crushing / Fragrance can diffuse.', "overlay_style": 'text'},
    "lutherie": {"duration": 8.0, "overlay_text": 'Do my heart-strings need Thy stretching / Songs divine to prove?', "overlay_style": 'text'},
    "silversmith": {"duration": 8.0, "overlay_text": 'Though Thy love has done its stripping / Still pursue Thy way.', "overlay_style": 'text'},
    "sculptor": {"duration": 8.0, "overlay_text": 'In the place of what Thou takest / Thou dost give Thyself to me.', "overlay_style": 'text'},
    "desert_rain": {"duration": 8.0, "overlay_text": "If Thy pleasure means my sorrow / Still my heart shall answer, 'Yea!'", "overlay_style": 'text'},
    "ascension": {"duration": 8.0, "overlay_text": 'Thou increase and I decrease, Lord / This is now my only plea.', "overlay_style": 'text'},
}

# ============================================================
# HELPER FUNCTIONS
# ============================================================


def wrap_text(
    text: str, chars_per_line: int, max_lines: int
) -> str:
    """Word-wrap text at word boundaries."""
    lines = textwrap.wrap(text, width=chars_per_line)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        if len(last) > chars_per_line - 3:
            last = last[:chars_per_line - 3]
        lines[-1] = last.rstrip() + "..."
    return "\n".join(lines)


def calc_text_height(
    line_count: int, font_size: int
) -> int:
    """Calculate text box height."""
    line_height = int(font_size * 1.4)
    return line_height * line_count + int(
        font_size * 0.3
    )


def create_text_overlay(
    text: str,
    duration: float,
    video_size: tuple[int, int],
    preset: str = "text",
) -> TextClip:
    """Create a text overlay clip."""
    width, height = video_size
    cfg = PRESETS.get(preset, PRESETS["text"])
    font_size = cfg["font_size"]

    wrapped = wrap_text(
        text, cfg["chars_per_line"], cfg["max_lines"]
    )
    line_count = wrapped.count("\n") + 1
    text_height = calc_text_height(
        line_count, font_size
    )

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

    y_position = (
        int(height * 0.75) - text_height // 2
    )
    text_clip = text_clip.with_position(
        ("center", y_position)
    )

    return text_clip


def load_and_process_clip(
    scene_id: str, scene_data: dict
) -> VideoFileClip:
    """Load a clip and add text overlay if specified."""
    clip_path = CLIPS_DIR / f"{scene_id}.mp4"

    if not clip_path.exists():
        raise FileNotFoundError(
            f"Clip not found: {clip_path}"
        )

    clip = VideoFileClip(str(clip_path))

    if clip.size != (VIDEO_WIDTH, VIDEO_HEIGHT):
        clip = clip.resized(height=VIDEO_HEIGHT)
        if clip.size[0] > VIDEO_WIDTH:
            x_center = clip.size[0] // 2
            x1 = x_center - VIDEO_WIDTH // 2
            clip = clip.cropped(
                x1=x1, x2=x1 + VIDEO_WIDTH
            )

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


# ============================================================
# MAIN ASSEMBLY
# ============================================================


def main():
    """Assemble all clips with text overlays."""
    print(f"Assembling video: Pressed Into Gold")
    print(f"Output: {OUTPUT_PATH}")
    print()

    clips = []
    for scene_id, scene_data in SCENES.items():
        print(f"  Processing {scene_id}...")
        try:
            clip = load_and_process_clip(
                scene_id, scene_data
            )
            clips.append(clip)
            overlay = scene_data.get("overlay_text", "")
            if overlay:
                preview = (
                    overlay[:40] + "..."
                    if len(overlay) > 40
                    else overlay
                )
                print(f"    Text: {preview}")
        except FileNotFoundError as e:
            print(f"    WARNING: {e}")
            continue

    if not clips:
        print("No clips found to assemble!")
        return

    # 1s white screen that fades out (fade in)
    fade_in = ColorClip(
        size=(VIDEO_WIDTH, VIDEO_HEIGHT),
        color=(255, 255, 255),
    ).with_duration(1.0)
    fade_in = fade_in.with_effects(
        [vfx.CrossFadeOut(1.0)]
    )
    clips.insert(0, fade_in)

    # 2s white screen that fades in (fade out)
    fade_out = ColorClip(
        size=(VIDEO_WIDTH, VIDEO_HEIGHT),
        color=(255, 255, 255),
    ).with_duration(2.0)
    fade_out = fade_out.with_effects(
        [vfx.CrossFadeIn(2.0)]
    )
    clips.append(fade_out)

    print()
    print(f"Concatenating {len(clips)} clips...")

    final = concatenate_videoclips(
        clips, method="compose"
    )

    if AUDIO_PATH.exists():
        audio = AudioFileClip(str(AUDIO_PATH))
        audio = audio.subclipped(0, final.duration)
        final = final.with_audio(audio)
        print(f"Audio: {AUDIO_PATH}")
    else:
        print(f"WARNING: Audio not found: {AUDIO_PATH}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    print(f"Rendering to {OUTPUT_PATH}...")
    final.write_videofile(
        str(OUTPUT_PATH),
        fps=30,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
    )

    print()
    print(f"Done! Output: {OUTPUT_PATH}")
    print(f"Duration: {final.duration:.1f}s")

    final.close()
    for clip in clips:
        clip.close()


if __name__ == "__main__":
    main()
