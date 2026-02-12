"""CLI entry point for the music video generator."""

import typer
from pathlib import Path
from typing import Optional
from enum import Enum

from . import __version__
from .config import config
from .models import Manifest, Project, ProjectState

app = typer.Typer(
    name="video-maker",
    help="AI-powered music video generator",
    no_args_is_help=True
)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        typer.echo(f"video-maker version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit"
    )
) -> None:
    """Music Video Generator - Create videos from ideas using AI."""
    pass


@app.command()
def status(
    project_dir: Path = typer.Option(
        Path("."),
        "--project",
        "-p",
        help="Project directory",
        exists=True,
        file_okay=False,
        dir_okay=True
    )
) -> None:
    """Show project status."""
    manifest_path = project_dir / "script.yaml"
    
    if not manifest_path.exists():
        typer.echo(f"❌ No project found at {project_dir}")
        typer.echo("   Run 'video-maker research' to create a new project")
        raise typer.Exit(1)
    
    try:
        manifest = Manifest.from_yaml(manifest_path)
        typer.echo(f"📁 Project: {manifest.project_name}")
        typer.echo(f"   Aspect ratio: {manifest.aspect_ratio}")
        typer.echo(f"   Scenes: {len(manifest.scenes)}")
        
        if manifest.audio_file:
            typer.echo(f"   Audio: {manifest.audio_file}")
        
        # Calculate total duration
        total_duration = sum(scene.duration for scene in manifest.scenes)
        typer.echo(f"   Total duration: {total_duration:.1f}s")
        
        # Scene breakdown
        typer.echo("\n📽️  Scenes:")
        for scene in manifest.scenes:
            status_icon = "✅" if scene.file else "⏳"
            typer.echo(f"   {status_icon} {scene.id}: {scene.duration}s")
            if scene.prompt:
                prompt_preview = scene.prompt[:60] + "..." if len(scene.prompt) > 60 else scene.prompt
                typer.echo(f"      → {prompt_preview}")
        
    except Exception as e:
        typer.echo(f"❌ Error loading project: {e}")
        raise typer.Exit(1)


class OutputQuality(str, Enum):
    """Output quality presets."""
    DRAFT = "draft"
    FINAL = "final"


class OutputFormat(str, Enum):
    """Output video formats."""
    MP4 = "mp4"
    WEBM = "webm"
    MOV = "mov"


@app.command()
def research(
    idea: str = typer.Argument(
        ...,
        help="Creative idea or concept for the video"
    ),
    duration: int = typer.Option(
        30,
        "--duration",
        "-d",
        help="Target duration in seconds",
        min=5,
        max=600
    ),
    scenes: Optional[int] = typer.Option(
        None,
        "--scenes",
        "-s",
        help="Number of scenes (auto-calculated if not specified)"
    ),
    style: Optional[str] = typer.Option(
        None,
        "--style",
        help="Visual style hints (e.g., 'cinematic', 'ethereal', '90s aesthetic')"
    ),
    output: Path = typer.Option(
        Path("manifest.yaml"),
        "--output",
        "-o",
        help="Output manifest file path"
    )
) -> None:
    """Generate scene descriptions from a creative idea using AI."""
    from .agents import ResearchAgent
    from .agents.research import ResearchInput

    typer.echo(f"🎬 Researching: {idea}")
    typer.echo(f"   Target duration: {duration}s")

    if style:
        typer.echo(f"   Style: {style}")

    # Validate API key
    if not config.anthropic_api_key:
        typer.echo("❌ ANTHROPIC_API_KEY environment variable not set")
        raise typer.Exit(1)

    # Create and run the research agent
    try:
        agent = ResearchAgent()
        typer.echo(f"   Using model: {agent.model}")
        typer.echo("   Generating scenes...")

        input_data = ResearchInput(
            idea=idea,
            duration=duration,
            num_scenes=scenes,
            style=style,
        )

        generated_scenes = agent.run(input_data)

    except Exception as e:
        typer.echo(f"❌ Error generating scenes: {e}")
        raise typer.Exit(1)

    # Create manifest with generated scenes
    # Generate project name from idea (first few words)
    project_name = " ".join(idea.split()[:5])
    if len(idea.split()) > 5:
        project_name += "..."

    manifest = Manifest(
        project_name=project_name,
        scenes=generated_scenes,
        aspect_ratio="16:9",
        output_format="mp4",
    )

    # Save manifest
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        manifest.to_yaml(output)
        typer.echo(f"\n✅ Manifest saved: {output}")
    except Exception as e:
        typer.echo(f"❌ Error saving manifest: {e}")
        raise typer.Exit(1)

    # Show summary
    total_duration = sum(scene.duration for scene in generated_scenes)
    typer.echo(f"\n📋 Summary:")
    typer.echo(f"   Scenes: {len(generated_scenes)}")
    typer.echo(f"   Total duration: {total_duration:.1f}s")

    typer.echo(f"\n📽️  Scene breakdown:")
    for scene in generated_scenes:
        typer.echo(f"   • {scene.id}: {scene.duration}s")
        prompt_preview = scene.prompt[:70] + "..." if len(scene.prompt) > 70 else scene.prompt
        typer.echo(f"     {prompt_preview}")


@app.command()
def assemble(
    scenes_file: Path = typer.Argument(
        ...,
        help="Path to scenes YAML file",
        exists=True,
        file_okay=True,
        dir_okay=False
    ),
    clips_dir: Path = typer.Argument(
        ...,
        help="Directory containing video clips",
        exists=True,
        file_okay=False,
        dir_okay=True
    ),
    music_file: Optional[Path] = typer.Argument(
        None,
        help="Path to background music file"
    ),
    output: Path = typer.Option(
        Path("output/final.mp4"),
        "--output",
        "-o",
        help="Output file path"
    ),
    output_format: OutputFormat = typer.Option(
        OutputFormat.MP4,
        "--format",
        "-f",
        help="Output video format"
    ),
    quality: OutputQuality = typer.Option(
        OutputQuality.FINAL,
        "--quality",
        "-q",
        help="Output quality preset"
    ),
    transition: float = typer.Option(
        0.5,
        "--transition",
        "-t",
        help="Transition duration in seconds (0 for no transitions)"
    ),
    fade_audio_out: float = typer.Option(
        2.0,
        "--fade-audio",
        help="Audio fade out duration at end (seconds)"
    )
) -> None:
    """Assemble video clips into final video with music and overlays."""
    from .editor import stitch_clips, sync_audio, export, add_text_overlay

    typer.echo(f"📼 Assembling video from {scenes_file}")

    # Load manifest
    try:
        manifest = Manifest.from_yaml(scenes_file)
    except Exception as e:
        typer.echo(f"❌ Error loading manifest: {e}")
        raise typer.Exit(1)

    # Collect clip paths in scene order
    clip_paths: list[Path] = []
    missing_clips: list[str] = []

    for scene in manifest.scenes:
        if scene.file:
            # Use explicit file path
            clip_path = Path(scene.file)
        else:
            # Look for clip in clips directory
            clip_path = clips_dir / f"{scene.id}.mp4"

        if not clip_path.exists():
            missing_clips.append(f"{scene.id}: {clip_path}")
        else:
            clip_paths.append(clip_path)

    if missing_clips:
        typer.echo("❌ Missing clips:")
        for clip in missing_clips:
            typer.echo(f"   - {clip}")
        raise typer.Exit(1)

    if not clip_paths:
        typer.echo("❌ No clips found to assemble")
        raise typer.Exit(1)

    typer.echo(f"   Found {len(clip_paths)} clips")

    # Stitch clips together
    try:
        typer.echo("   Stitching clips...")
        video = stitch_clips(clip_paths, transition_duration=transition)
    except Exception as e:
        typer.echo(f"❌ Error stitching clips: {e}")
        raise typer.Exit(1)

    # Add text overlays if defined in scenes
    for i, scene in enumerate(manifest.scenes):
        if scene.overlay_text:
            style_name = scene.overlay_style or "default"
            typer.echo(f"   Adding overlay to {scene.id}: '{scene.overlay_text}'")
            # Note: For complex multi-scene overlays with timing, we'd need
            # to track cumulative start times. This is a simplified version.

    # Add audio if provided
    audio_path = music_file or (Path(manifest.audio_file) if manifest.audio_file else None)
    if audio_path:
        if not audio_path.exists():
            typer.echo(f"⚠️  Audio file not found: {audio_path}")
        else:
            typer.echo(f"   Adding audio: {audio_path}")
            try:
                video = sync_audio(video, audio_path, loop=True, fade_out=fade_audio_out)
            except Exception as e:
                typer.echo(f"⚠️  Error adding audio: {e}")

    # Configure encoding based on quality
    encoding_params = {
        "fps": 30,
        "preset": "medium" if quality == OutputQuality.FINAL else "ultrafast",
    }

    if quality == OutputQuality.FINAL:
        encoding_params["bitrate"] = "8000k"
    else:
        encoding_params["bitrate"] = "3000k"

    # Adjust codec based on format
    codec_map = {
        OutputFormat.MP4: ("libx264", "aac"),
        OutputFormat.WEBM: ("libvpx", "libvorbis"),
        OutputFormat.MOV: ("libx264", "aac"),
    }
    video_codec, audio_codec = codec_map[output_format]
    encoding_params["codec"] = video_codec
    encoding_params["audio_codec"] = audio_codec

    # Ensure output has correct extension
    output = output.with_suffix(f".{output_format.value}")

    # Export final video
    typer.echo(f"   Rendering to {output} ({quality.value} quality)...")
    try:
        export(video, output, **encoding_params)
        typer.echo(f"✅ Video assembled: {output}")

        # Show video info
        typer.echo(f"   Duration: {video.duration:.1f}s")
        typer.echo(f"   Resolution: {video.w}x{video.h}")

    except Exception as e:
        typer.echo(f"❌ Error exporting video: {e}")
        raise typer.Exit(1)
    finally:
        # Clean up
        video.close()


@app.command()
def veo(
    scenes_file: Path = typer.Argument(
        ...,
        help="Path to scenes YAML manifest file",
        exists=True,
        file_okay=True,
        dir_okay=False
    ),
    output: Path = typer.Option(
        Path("./clips"),
        "--output",
        "-o",
        help="Output directory for generated clips"
    ),
    parallel: int = typer.Option(
        3,
        "--parallel",
        "-p",
        help="Maximum concurrent generations",
        min=1,
        max=10
    ),
    skip_existing: bool = typer.Option(
        False,
        "--skip-existing",
        "-s",
        help="Skip scenes that already have clip files"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Show what would be generated without calling API"
    ),
    aspect_ratio: str = typer.Option(
        None,
        "--aspect-ratio",
        "-a",
        help="Override aspect ratio (16:9 or 9:16)"
    ),
) -> None:
    """Generate video clips from scene prompts using Google Veo 3.

    Reads a YAML manifest with scene descriptions and generates video clips
    for each scene using the Veo 3 API via Vertex AI.
    """
    import json as json_module
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from .services.veo import VeoClient, GenerationStatus, save_generation_metadata, GenerationResult

    typer.echo(f"🎬 Veo Generation: {scenes_file}")

    # Validate Veo configuration (unless dry run)
    if not dry_run:
        try:
            config.validate_veo_required()
        except ValueError as e:
            typer.echo(f"❌ Configuration error: {e}")
            raise typer.Exit(1)

    # Load manifest
    try:
        manifest = Manifest.from_yaml(scenes_file)
    except Exception as e:
        typer.echo(f"❌ Error loading manifest: {e}")
        raise typer.Exit(1)

    typer.echo(f"   Project: {manifest.project_name}")
    typer.echo(f"   Total scenes: {len(manifest.scenes)}")

    # Determine aspect ratio
    ratio = aspect_ratio or manifest.aspect_ratio or "16:9"
    if ratio not in ("16:9", "9:16"):
        typer.echo(f"❌ Invalid aspect ratio: {ratio}. Must be '16:9' or '9:16'")
        raise typer.Exit(1)
    typer.echo(f"   Aspect ratio: {ratio}")

    # Create output directory
    output.mkdir(parents=True, exist_ok=True)
    typer.echo(f"   Output directory: {output}")

    # Filter scenes that need generation
    scenes_to_generate: list[tuple[int, object]] = []
    skipped_scenes: list[str] = []

    for i, scene in enumerate(manifest.scenes):
        # Skip scenes with explicit file source
        if scene.source == "file" and scene.file:
            skipped_scenes.append(f"{scene.id} (has explicit file)")
            continue

        # Skip if no prompt
        if not scene.prompt:
            skipped_scenes.append(f"{scene.id} (no prompt)")
            continue

        # Check if clip already exists
        clip_path = output / f"{scene.id}.mp4"
        if skip_existing and clip_path.exists():
            skipped_scenes.append(f"{scene.id} (exists)")
            continue

        scenes_to_generate.append((i, scene))

    # Show summary
    typer.echo(f"\n📋 Generation Plan:")
    typer.echo(f"   To generate: {len(scenes_to_generate)}")
    typer.echo(f"   Skipped: {len(skipped_scenes)}")

    if skipped_scenes and len(skipped_scenes) <= 10:
        for s in skipped_scenes:
            typer.echo(f"     - {s}")

    if not scenes_to_generate:
        typer.echo("\n✅ No scenes to generate")
        raise typer.Exit(0)

    # Dry run mode - show what would be generated
    if dry_run:
        typer.echo(f"\n🔍 Dry run - would generate {len(scenes_to_generate)} clips:")
        for idx, scene in scenes_to_generate:
            prompt_preview = scene.prompt[:70] + "..." if len(scene.prompt) > 70 else scene.prompt
            typer.echo(f"   [{idx + 1}] {scene.id}: {scene.duration}s")
            typer.echo(f"       → {prompt_preview}")
        raise typer.Exit(0)

    # Initialize Veo client
    try:
        client = VeoClient()
        typer.echo(f"\n🔌 Connected to Veo 3 (project: {client.project_id})")
    except Exception as e:
        typer.echo(f"❌ Failed to initialize Veo client: {e}")
        raise typer.Exit(1)

    # Track results
    results: list[GenerationResult] = []
    successful = 0
    failed = 0

    typer.echo(f"\n⏳ Generating {len(scenes_to_generate)} clips (max {parallel} concurrent)...\n")

    def generate_scene(scene_data: tuple[int, object]) -> GenerationResult:
        """Generate a single scene clip."""
        idx, scene = scene_data
        clip_path = output / f"{scene.id}.mp4"

        # Clamp duration for Veo (typically 5-8 seconds)
        duration = max(5.0, min(8.0, scene.duration))

        return client.generate_clip(
            prompt=scene.prompt,
            duration=duration,
            aspect_ratio=ratio,
            output_path=clip_path,
            scene_id=scene.id,
        )

    # Process scenes with thread pool for concurrent generation
    with ThreadPoolExecutor(max_workers=parallel) as executor:
        # Submit all jobs
        future_to_scene = {
            executor.submit(generate_scene, scene_data): scene_data
            for scene_data in scenes_to_generate
        }

        # Process completions
        for future in as_completed(future_to_scene):
            idx, scene = future_to_scene[future]
            try:
                result = future.result()
                results.append(result)

                if result.status == GenerationStatus.COMPLETED:
                    successful += 1
                    typer.echo(f"   ✅ {scene.id}: Generated → {result.local_path}")
                else:
                    failed += 1
                    error_msg = result.error_message or "Unknown error"
                    typer.echo(f"   ❌ {scene.id}: Failed - {error_msg}")

            except Exception as e:
                failed += 1
                typer.echo(f"   ❌ {scene.id}: Error - {e}")
                results.append(GenerationResult(
                    operation_id=f"error-{scene.id}",
                    status=GenerationStatus.FAILED,
                    error_message=str(e),
                    metadata={"scene_id": scene.id},
                ))

    # Save generation metadata
    metadata_path = output / "generation_metadata.json"
    try:
        save_generation_metadata(results, metadata_path)
        typer.echo(f"\n📄 Metadata saved: {metadata_path}")
    except Exception as e:
        typer.echo(f"⚠️  Failed to save metadata: {e}")

    # Final summary
    typer.echo(f"\n📊 Summary:")
    typer.echo(f"   Total scenes: {len(manifest.scenes)}")
    typer.echo(f"   Generated: {successful}")
    typer.echo(f"   Failed: {failed}")
    typer.echo(f"   Skipped: {len(skipped_scenes)}")

    if failed > 0:
        typer.echo(f"\n⚠️  {failed} scene(s) failed to generate")
        raise typer.Exit(1)
    else:
        typer.echo(f"\n✅ All clips generated successfully!")


if __name__ == "__main__":
    app()
