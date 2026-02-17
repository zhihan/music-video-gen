"""CLI entry point for the music video generator."""

import logging
import typer
from pathlib import Path
from typing import Optional

from . import __version__
from .config import config
from .models import Manifest, Project, ProjectState

app = typer.Typer(
    name="video-maker",
    help="AI-powered music video generator",
    no_args_is_help=True
)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
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
    script: Path = typer.Option(
        Path("script.yaml"),
        "--script",
        "-s",
        help="Path to scenes YAML file",
        exists=False,
        file_okay=True,
        dir_okay=False
    )
) -> None:
    """Show project status."""
    if not script.exists():
        typer.echo(f"❌ No project found at {script}")
        typer.echo("   Create a script.yaml file to start a new project")
        raise typer.Exit(1)

    try:
        manifest = Manifest.from_yaml(script)
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


@app.command()
def imagen(
    prompt: str = typer.Argument(
        ...,
        help="Text description of the image to generate"
    ),
    output: Path = typer.Option(
        Path("./assets/character.png"),
        "--output",
        "-o",
        help="Output image file path"
    ),
    aspect_ratio: str = typer.Option(
        "1:1",
        "--aspect-ratio",
        "-a",
        help="Image aspect ratio (1:1, 16:9, 9:16, 4:3, 3:4)"
    ),
    negative: Optional[str] = typer.Option(
        None,
        "--negative",
        "-n",
        help="Negative prompt - things to avoid"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging"
    ),
) -> None:
    """Generate a reference image using Google Imagen.

    Use this to create consistent character references for video generation.

    Example:
        video-maker imagen "12-year-old Asian girl with short black hair, school uniform"
    """
    from .services.imagen import ImagenClient

    setup_logging(verbose)
    typer.echo(f"🎨 Generating image with Imagen")
    typer.echo(f"   Prompt: {prompt[:70]}...")

    try:
        client = ImagenClient()
        typer.echo(f"   Model: {client.model}")
    except ValueError as e:
        typer.echo(f"❌ Configuration error: {e}")
        raise typer.Exit(1)

    result = client.generate_image(
        prompt=prompt,
        output_path=output,
        aspect_ratio=aspect_ratio,
        negative_prompt=negative,
    )

    if result.error_message:
        typer.echo(f"❌ Generation failed: {result.error_message}")
        raise typer.Exit(1)

    typer.echo(f"✅ Image saved: {result.local_path}")
    typer.echo(f"\nUse this image as a character reference:")
    typer.echo(f"   video-maker veo --reference {result.local_path}")


@app.command(name="generate-script")
def generate_script(
    script: Path = typer.Option(
        Path("script.yaml"),
        "--script",
        "-s",
        help="Path to scenes YAML file",
        exists=True,
        file_okay=True,
        dir_okay=False
    ),
    clips_dir: Path = typer.Option(
        Path("./clips"),
        "--clips",
        "-c",
        help="Directory containing video clips"
    ),
    output: Path = typer.Option(
        Path("./scripts/assembly.py"),
        "--output",
        "-o",
        help="Output Python script path"
    ),
    output_video: Path = typer.Option(
        Path("./output/final.mp4"),
        "--output-video",
        help="Output video path for the generated script"
    ),
) -> None:
    """Generate a MoviePy assembly script with text overlays.

    Creates a standalone Python script that adds text overlays to video clips
    based on the script.yaml. The generated script can be refined with Claude.

    Example:
        video-maker generate-script
        python scripts/assembly.py
    """
    from .codegen import generate_assembly_script

    typer.echo(f"📝 Generating assembly script from {script}")

    # Load manifest
    try:
        manifest = Manifest.from_yaml(script)
    except Exception as e:
        typer.echo(f"❌ Error loading manifest: {e}")
        raise typer.Exit(1)

    # Count scenes with overlays
    overlay_count = sum(1 for s in manifest.scenes if s.overlay_text)
    typer.echo(f"   Project: {manifest.project_name}")
    typer.echo(f"   Scenes: {len(manifest.scenes)}")
    typer.echo(f"   Scenes with text overlays: {overlay_count}")

    # Generate the script
    try:
        script_content = generate_assembly_script(
            manifest=manifest,
            clips_dir=clips_dir,
            output_video=output_video,
        )
    except Exception as e:
        typer.echo(f"❌ Error generating script: {e}")
        raise typer.Exit(1)

    # Ensure output directory exists
    output.parent.mkdir(parents=True, exist_ok=True)

    # Write the script
    try:
        output.write_text(script_content)
        typer.echo(f"\n✅ Script generated: {output}")
        typer.echo(f"\nNext steps:")
        typer.echo(f"   1. Review and adjust the script as needed")
        typer.echo(f"   2. Run: python {output}")
        typer.echo(f"   3. Ask Claude to refine text positioning/sizing")
    except Exception as e:
        typer.echo(f"❌ Error writing script: {e}")
        raise typer.Exit(1)


@app.command()
def veo(
    script: Path = typer.Option(
        Path("script.yaml"),
        "--script",
        "-s",
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
        True,
        "--skip-existing/--regenerate",
        "-k/-K",
        help="Skip scenes that already have clip files (default: skip existing)"
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
    reference: Optional[Path] = typer.Option(
        None,
        "--reference",
        "-r",
        help="Reference image for character consistency (use 'imagen' command to generate)"
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        "-l",
        help="Limit number of scenes to generate (for testing)"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging"
    ),
) -> None:
    """Generate video clips from scene prompts using Google Veo 3.

    Reads a YAML manifest with scene descriptions and generates video clips
    for each scene using the Veo 3 API via Vertex AI.
    """
    import json as json_module
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from .services.veo import VeoClient, GenerationStatus, save_generation_metadata, GenerationResult

    setup_logging(verbose)
    typer.echo(f"🎬 Veo Generation: {script}")

    # Validate Veo configuration (unless dry run)
    if not dry_run:
        try:
            config.validate_veo_required()
        except ValueError as e:
            typer.echo(f"❌ Configuration error: {e}")
            raise typer.Exit(1)

    # Load manifest
    try:
        manifest = Manifest.from_yaml(script)
    except Exception as e:
        typer.echo(f"❌ Error loading manifest: {e}")
        raise typer.Exit(1)

    typer.echo(f"   Project: {manifest.project_name}")
    typer.echo(f"   Total scenes: {len(manifest.scenes)}")

    # Determine aspect ratio
    ratio = aspect_ratio or manifest.aspect_ratio or "9:16"
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

    # Apply limit if specified
    if limit and limit > 0:
        scenes_to_generate = scenes_to_generate[:limit]

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

    # Validate reference image if provided
    if reference and not reference.exists():
        typer.echo(f"❌ Reference image not found: {reference}")
        raise typer.Exit(1)

    if reference:
        typer.echo(f"   Using reference image: {reference}")

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
            reference_image=reference,
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
