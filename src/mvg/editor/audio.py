"""Audio processing for video assembly."""

from pathlib import Path
from typing import Optional

from moviepy import AudioFileClip, VideoClip, CompositeAudioClip
from moviepy.audio.fx import AudioFadeIn, AudioFadeOut


def load_audio(audio_path: Path) -> AudioFileClip:
    """Load an audio file.

    Args:
        audio_path: Path to the audio file.

    Returns:
        AudioFileClip instance.

    Raises:
        FileNotFoundError: If audio file doesn't exist.
    """
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    return AudioFileClip(str(audio_path))


def sync_audio(
    video: VideoClip,
    audio_path: Path,
    loop: bool = True,
    fade_out: float = 0.0
) -> VideoClip:
    """Sync audio with video, adjusting duration as needed.

    Args:
        video: Video clip to add audio to.
        audio_path: Path to audio file.
        loop: If True, loop audio to match video duration.
            If False, trim audio to video duration.
        fade_out: Duration of fade out at the end (seconds).

    Returns:
        Video clip with synchronized audio.
    """
    audio = load_audio(audio_path)
    video_duration = video.duration

    if audio.duration < video_duration and loop:
        # Loop audio to match video duration
        audio = loop_audio(audio, video_duration)
    elif audio.duration > video_duration:
        # Trim audio to video duration
        audio = audio.subclipped(0, video_duration)

    # Apply fade out if requested
    if fade_out > 0:
        audio = fade_audio(audio, fade_out=fade_out)

    return video.with_audio(audio)


def loop_audio(
    audio: AudioFileClip,
    target_duration: float
) -> CompositeAudioClip:
    """Loop audio to match a target duration.

    Args:
        audio: Audio clip to loop.
        target_duration: Target duration in seconds.

    Returns:
        Audio clip looped to target duration.
    """
    if audio.duration >= target_duration:
        return audio.subclipped(0, target_duration)

    # Calculate how many loops we need
    loops_needed = int(target_duration / audio.duration) + 1

    # Create multiple copies with appropriate start times
    clips = []
    for i in range(loops_needed):
        clip = audio.with_start(i * audio.duration)
        clips.append(clip)

    # Composite and trim to exact duration
    composite = CompositeAudioClip(clips)
    return composite.subclipped(0, target_duration)


def fade_audio(
    audio: AudioFileClip,
    fade_in: float = 0.0,
    fade_out: float = 0.0
) -> AudioFileClip:
    """Apply fade in/out effects to audio.

    Args:
        audio: Audio clip to process.
        fade_in: Duration of fade in effect (seconds).
        fade_out: Duration of fade out effect (seconds).

    Returns:
        Audio clip with fade effects applied.
    """
    effects = []

    if fade_in > 0:
        effects.append(AudioFadeIn(fade_in))

    if fade_out > 0:
        effects.append(AudioFadeOut(fade_out))

    if effects:
        return audio.with_effects(effects)

    return audio


def adjust_volume(
    audio: AudioFileClip,
    factor: float = 1.0
) -> AudioFileClip:
    """Adjust audio volume.

    Args:
        audio: Audio clip to adjust.
        factor: Volume multiplier (1.0 = original, 0.5 = half, 2.0 = double).

    Returns:
        Audio clip with adjusted volume.
    """
    return audio.with_volume_scaled(factor)


def mix_audio(
    primary: AudioFileClip,
    secondary: AudioFileClip,
    secondary_volume: float = 0.5
) -> CompositeAudioClip:
    """Mix two audio tracks together.

    Args:
        primary: Primary audio track (full volume).
        secondary: Secondary audio track (background).
        secondary_volume: Volume factor for secondary track.

    Returns:
        Mixed audio clip.
    """
    secondary = adjust_volume(secondary, secondary_volume)
    return CompositeAudioClip([primary, secondary])


def extract_audio(video: VideoClip, output_path: Path) -> Path:
    """Extract audio from a video clip.

    Args:
        video: Video clip to extract audio from.
        output_path: Path for output audio file.

    Returns:
        Path to extracted audio file.
    """
    if video.audio is None:
        raise ValueError("Video has no audio track")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    video.audio.write_audiofile(str(output_path))
    return output_path


def get_audio_duration(audio_path: Path) -> float:
    """Get the duration of an audio file.

    Args:
        audio_path: Path to audio file.

    Returns:
        Duration in seconds.
    """
    audio = load_audio(audio_path)
    duration = audio.duration
    audio.close()
    return duration
