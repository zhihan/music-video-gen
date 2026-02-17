"""Video compositor for stitching clips and transitions."""

from __future__ import annotations

from pathlib import Path

from moviepy import (
    CompositeVideoClip,
    VideoFileClip,
    concatenate_videoclips,
)
from moviepy.video.fx import CrossFadeIn, CrossFadeOut


def stitch_clips(
    clip_paths: list[Path],
    transition_duration: float = 0.0,
) -> CompositeVideoClip:
    """Concatenate video clips into a single video.

    Args:
        clip_paths: List of paths to video clip files.
        transition_duration: Duration of crossfade
            transitions in seconds. If 0, clips are
            concatenated without transitions.

    Returns:
        Concatenated video clip.

    Raises:
        FileNotFoundError: If a clip file doesn't exist.
        ValueError: If clip_paths is empty.
    """
    if not clip_paths:
        raise ValueError("No clips provided")

    clips: list[VideoFileClip] = []
    for clip_path in clip_paths:
        if not clip_path.exists():
            raise FileNotFoundError(
                f"Clip not found: {clip_path}"
            )
        clips.append(VideoFileClip(str(clip_path)))

    if transition_duration > 0 and len(clips) > 1:
        clips = add_transitions(
            clips, transition_duration
        )

    if len(clips) == 1:
        return clips[0]

    return concatenate_videoclips(
        clips, method="compose"
    )


def add_transitions(
    clips: list[VideoFileClip],
    duration: float = 0.5,
) -> list[VideoFileClip]:
    """Add crossfade transitions between clips.

    Args:
        clips: List of video clips.
        duration: Duration of each crossfade in seconds.

    Returns:
        List of clips with fade effects applied.
    """
    if len(clips) < 2:
        return clips

    result: list[VideoFileClip] = []

    for i, clip in enumerate(clips):
        if i < len(clips) - 1:
            clip = clip.with_effects(
                [CrossFadeOut(duration)]
            )
        if i > 0:
            clip = clip.with_effects(
                [CrossFadeIn(duration)]
            )
        result.append(clip)

    return result


def export(
    video: CompositeVideoClip,
    output_path: Path,
    fps: int = 30,
    codec: str = "libx264",
    audio_codec: str = "aac",
    bitrate: str | None = None,
    preset: str = "medium",
) -> Path:
    """Export video to file with proper encoding.

    Args:
        video: Video clip to export.
        output_path: Path for output file.
        fps: Frames per second (default 30).
        codec: Video codec (default libx264).
        audio_codec: Audio codec (default aac).
        bitrate: Video bitrate (e.g., "5000k"). None
            for auto.
        preset: Encoding preset (ultrafast, fast,
            medium, slow, slower).

    Returns:
        Path to the exported video file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    export_params = {
        "fps": fps,
        "codec": codec,
        "audio_codec": audio_codec,
        "preset": preset,
    }

    if bitrate:
        export_params["bitrate"] = bitrate

    video.write_videofile(
        str(output_path), **export_params
    )

    return output_path


def resize_clip(
    clip: VideoFileClip,
    width: int | None = None,
    height: int | None = None,
) -> VideoFileClip:
    """Resize a video clip.

    Args:
        clip: Video clip to resize.
        width: Target width in pixels.
        height: Target height in pixels.

    Returns:
        Resized video clip.
    """
    if width and height:
        return clip.resized((width, height))
    elif width:
        return clip.resized(width=width)
    elif height:
        return clip.resized(height=height)
    return clip


def crop_to_aspect(
    clip: VideoFileClip,
    aspect_ratio: str = "9:16",
) -> VideoFileClip:
    """Crop a video clip to a specific aspect ratio.

    Args:
        clip: Video clip to crop.
        aspect_ratio: Target aspect ratio
            (e.g., "16:9", "9:16").

    Returns:
        Cropped video clip.
    """
    parts = aspect_ratio.split(":")
    target_w = int(parts[0])
    target_h = int(parts[1])
    target_ratio = target_w / target_h

    current_w = clip.w
    current_h = clip.h
    current_ratio = current_w / current_h

    if abs(current_ratio - target_ratio) < 0.01:
        return clip

    if current_ratio > target_ratio:
        new_w = int(current_h * target_ratio)
        x_center = current_w // 2
        x1 = x_center - new_w // 2
        return clip.cropped(x1=x1, x2=x1 + new_w)
    else:
        new_h = int(current_w / target_ratio)
        y_center = current_h // 2
        y1 = y_center - new_h // 2
        return clip.cropped(y1=y1, y2=y1 + new_h)
