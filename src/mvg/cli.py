"""CLI entry point for the music video generator."""

from __future__ import annotations

import logging
from pathlib import Path

import typer

from . import __version__
from .config import config
from .models import Manifest

app = typer.Typer(
    name="video-maker",
    help="AI-powered music video generator",
    no_args_is_help=True,
)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging level.

    Args:
        verbose: If True, set DEBUG level.
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
    )


def version_callback(value: bool) -> None:
    """Print version and exit.

    Args:
        value: Whether --version was passed.
    """
    if value:
        typer.echo(f"video-maker version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool | None = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
) -> None:
    """Music Video Generator - Create videos using AI."""


@app.command()
def status(
    script: Path = typer.Option(
        Path("script.yaml"),
        "--script",
        "-s",
        help="Path to scenes YAML file",
        exists=False,
        file_okay=True,
        dir_okay=False,
    ),
) -> None:
    """Show project status."""
    if not script.exists():
        typer.echo(f"No project found at {script}")
        typer.echo(
            "   Create a script.yaml file to start "
            "a new project"
        )
        raise typer.Exit(1)

    try:
        manifest = Manifest.from_yaml(script)
        typer.echo(
            f"Project: {manifest.project_name}"
        )
        typer.echo(
            f"   Aspect ratio: {manifest.aspect_ratio}"
        )
        typer.echo(
            f"   Scenes: {len(manifest.scenes)}"
        )

        if manifest.audio_file:
            typer.echo(
                f"   Audio: {manifest.audio_file}"
            )

        total_duration = sum(
            s.duration for s in manifest.scenes
        )
        typer.echo(
            f"   Total duration: {total_duration:.1f}s"
        )

        typer.echo("\nScenes:")
        for scene in manifest.scenes:
            icon = "done" if scene.file else "pending"
            typer.echo(
                f"   [{icon}] {scene.id}: "
                f"{scene.duration}s"
            )
            if scene.prompt:
                preview = (
                    scene.prompt[:60] + "..."
                    if len(scene.prompt) > 60
                    else scene.prompt
                )
                typer.echo(f"      -> {preview}")

    except Exception as e:
        typer.echo(f"Error loading project: {e}")
        raise typer.Exit(1)


@app.command()
def imagen(
    prompt: str = typer.Argument(
        ...,
        help="Text description of the image to generate",
    ),
    output: Path = typer.Option(
        Path("./assets/character.png"),
        "--output",
        "-o",
        help="Output image file path",
    ),
    aspect_ratio: str = typer.Option(
        "1:1",
        "--aspect-ratio",
        "-a",
        help="Image aspect ratio "
        "(1:1, 16:9, 9:16, 4:3, 3:4)",
    ),
    negative: str | None = typer.Option(
        None,
        "--negative",
        "-n",
        help="Negative prompt - things to avoid",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging",
    ),
) -> None:
    """Generate a reference image using Google Imagen.

    Use this to create consistent character references
    for video generation.
    """
    from .services.imagen import ImagenClient

    setup_logging(verbose)
    typer.echo("Generating image with Imagen")
    typer.echo(f"   Prompt: {prompt[:70]}...")

    try:
        client = ImagenClient()
        typer.echo(f"   Model: {client.model}")
    except ValueError as e:
        typer.echo(f"Configuration error: {e}")
        raise typer.Exit(1)

    result = client.generate_image(
        prompt=prompt,
        output_path=output,
        aspect_ratio=aspect_ratio,
        negative_prompt=negative,
    )

    if result.error_message:
        typer.echo(
            f"Generation failed: {result.error_message}"
        )
        raise typer.Exit(1)

    typer.echo(f"Image saved: {result.local_path}")
    typer.echo("\nUse this image as a character reference:")
    typer.echo(
        f"   video-maker veo --reference "
        f"{result.local_path}"
    )


@app.command()
def music(
    audio_file: Path = typer.Argument(
        ...,
        help="Local audio file to cover/remix "
        "(max 8 min)",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    prompt: str = typer.Option(
        ...,
        "--prompt",
        "-p",
        help="Text description or lyrics prompt",
    ),
    style: str | None = typer.Option(
        None,
        "--style",
        "-s",
        help="Music style tags (e.g. 'Pop, Upbeat'). "
        "Enables custom mode",
    ),
    title: str | None = typer.Option(
        None,
        "--title",
        "-t",
        help="Song title (used with --style)",
    ),
    model: str = typer.Option(
        "V5",
        "--model",
        "-m",
        help="Suno model version "
        "(V4, V4_5, V4_5PLUS, V4_5ALL, V5)",
    ),
    instrumental: bool = typer.Option(
        False,
        "--instrumental",
        "-i",
        help="Generate instrumental only (no vocals)",
    ),
    vocal_gender: str | None = typer.Option(
        None,
        "--vocal-gender",
        help="Vocal gender: 'm' or 'f'",
    ),
    output: Path = typer.Option(
        Path("./assets/music/generated.mp3"),
        "--output",
        "-o",
        help="Output audio file path",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="Enable verbose logging",
    ),
) -> None:
    """Cover/remix audio using KIE.ai (Suno).

    Uploads a local audio file to KIE.ai, then submits
    a cover request. Polls until ready and downloads
    the result.
    """
    from .services.kie import KieClient

    setup_logging(verbose)

    try:
        config.validate_kie_required()
    except ValueError as e:
        typer.echo(f"Configuration error: {e}")
        raise typer.Exit(1)

    typer.echo("Covering audio with KIE.ai (Suno)")
    typer.echo(f"   Source: {audio_file}")
    typer.echo(f"   Prompt: {prompt[:70]}")
    if style:
        typer.echo(f"   Style: {style}")
    if title:
        typer.echo(f"   Title: {title}")
    typer.echo(f"   Model: {model}")
    typer.echo(
        f"   Instrumental: {instrumental}"
    )

    try:
        client = KieClient(model=model)
    except ValueError as e:
        typer.echo(f"Configuration error: {e}")
        raise typer.Exit(1)

    typer.echo("\nUploading audio file...")

    result = client.upload_and_cover(
        audio_file=audio_file,
        prompt=prompt,
        style=style,
        title=title,
        instrumental=instrumental,
        vocal_gender=vocal_gender,
        output_path=output,
    )

    if result.status not in (
        "SUCCESS",
        "FIRST_SUCCESS",
    ):
        error = result.error_message or "Unknown error"
        typer.echo(f"\nGeneration failed: {error}")
        if result.task_id:
            typer.echo(
                f"   Task ID: {result.task_id}"
            )
        raise typer.Exit(1)

    typer.echo("\nCover complete!")
    if result.title:
        typer.echo(f"   Title: {result.title}")
    if result.duration:
        typer.echo(
            f"   Duration: {result.duration:.1f}s"
        )
    if result.local_path:
        typer.echo(f"   Saved to: {result.local_path}")
    if result.task_id:
        typer.echo(
            f"   Task ID: {result.task_id}"
        )
    if result.metadata.get("audio_id"):
        typer.echo(
            f"   Audio ID: "
            f"{result.metadata['audio_id']}"
        )
        typer.echo(
            "\nTo get timestamped lyrics:"
        )
        typer.echo(
            f"   video-maker lyrics "
            f"--task-id {result.task_id} "
            f"--audio-id "
            f"{result.metadata['audio_id']}"
        )


@app.command(name="generate-script")
def generate_script(
    script: Path = typer.Option(
        Path("script.yaml"),
        "--script",
        "-s",
        help="Path to scenes YAML file",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    clips_dir: Path = typer.Option(
        Path("./clips"),
        "--clips",
        "-c",
        help="Directory containing video clips",
    ),
    output: Path = typer.Option(
        Path("./scripts/assembly.py"),
        "--output",
        "-o",
        help="Output Python script path",
    ),
    output_video: Path = typer.Option(
        Path("./output/final.mp4"),
        "--output-video",
        help="Output video path for the generated script",
    ),
) -> None:
    """Generate a MoviePy assembly script.

    Creates a standalone Python script that adds text
    overlays to video clips based on the script.yaml.
    """
    from .codegen import generate_assembly_script

    typer.echo(
        f"Generating assembly script from {script}"
    )

    try:
        manifest = Manifest.from_yaml(script)
    except Exception as e:
        typer.echo(f"Error loading manifest: {e}")
        raise typer.Exit(1)

    overlay_count = sum(
        1 for s in manifest.scenes if s.overlay_text
    )
    typer.echo(f"   Project: {manifest.project_name}")
    typer.echo(f"   Scenes: {len(manifest.scenes)}")
    typer.echo(
        f"   Scenes with text overlays: {overlay_count}"
    )

    try:
        script_content = generate_assembly_script(
            manifest=manifest,
            clips_dir=clips_dir,
            output_video=output_video,
        )
    except Exception as e:
        typer.echo(f"Error generating script: {e}")
        raise typer.Exit(1)

    output.parent.mkdir(parents=True, exist_ok=True)

    try:
        output.write_text(script_content)
        typer.echo(f"\nScript generated: {output}")
        typer.echo("\nNext steps:")
        typer.echo(
            "   1. Review and adjust the script "
            "as needed"
        )
        typer.echo(f"   2. Run: python {output}")
        typer.echo(
            "   3. Ask Claude to refine text "
            "positioning/sizing"
        )
    except Exception as e:
        typer.echo(f"Error writing script: {e}")
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
        dir_okay=False,
    ),
    output: Path = typer.Option(
        Path("./clips"),
        "--output",
        "-o",
        help="Output directory for generated clips",
    ),
    parallel: int = typer.Option(
        3,
        "--parallel",
        "-p",
        help="Maximum concurrent generations",
        min=1,
        max=10,
    ),
    skip_existing: bool = typer.Option(
        True,
        "--skip-existing/--regenerate",
        "-k/-K",
        help="Skip scenes that already have clip files",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Show what would be generated without "
        "calling API",
    ),
    aspect_ratio: str = typer.Option(
        None,
        "--aspect-ratio",
        "-a",
        help="Override aspect ratio (16:9 or 9:16)",
    ),
    reference: Path | None = typer.Option(
        None,
        "--reference",
        "-r",
        help="Reference image for character consistency",
    ),
    limit: int | None = typer.Option(
        None,
        "--limit",
        "-l",
        help="Limit number of scenes to generate",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging",
    ),
) -> None:
    """Generate video clips using Google Veo 3.

    Reads a YAML manifest with scene descriptions and
    generates video clips for each scene.
    """
    from concurrent.futures import (
        ThreadPoolExecutor,
        as_completed,
    )

    from .services.veo import (
        GenerationResult,
        GenerationStatus,
        VeoClient,
        save_generation_metadata,
    )

    setup_logging(verbose)
    typer.echo(f"Veo Generation: {script}")

    if not dry_run:
        try:
            config.validate_veo_required()
        except ValueError as e:
            typer.echo(f"Configuration error: {e}")
            raise typer.Exit(1)

    try:
        manifest = Manifest.from_yaml(script)
    except Exception as e:
        typer.echo(f"Error loading manifest: {e}")
        raise typer.Exit(1)

    typer.echo(f"   Project: {manifest.project_name}")
    typer.echo(
        f"   Total scenes: {len(manifest.scenes)}"
    )

    ratio = (
        aspect_ratio
        or manifest.aspect_ratio
        or "9:16"
    )
    if ratio not in ("16:9", "9:16"):
        typer.echo(
            f"Invalid aspect ratio: {ratio}. "
            "Must be '16:9' or '9:16'"
        )
        raise typer.Exit(1)
    typer.echo(f"   Aspect ratio: {ratio}")

    output.mkdir(parents=True, exist_ok=True)
    typer.echo(f"   Output directory: {output}")

    scenes_to_generate = _filter_scenes(
        manifest, output, skip_existing
    )
    skipped = (
        len(manifest.scenes) - len(scenes_to_generate)
    )

    if limit and limit > 0:
        scenes_to_generate = scenes_to_generate[:limit]

    typer.echo("\nGeneration Plan:")
    typer.echo(
        f"   To generate: {len(scenes_to_generate)}"
    )
    typer.echo(f"   Skipped: {skipped}")

    if not scenes_to_generate:
        typer.echo("\nNo scenes to generate")
        raise typer.Exit(0)

    if dry_run:
        _show_dry_run(scenes_to_generate)
        raise typer.Exit(0)

    try:
        client = VeoClient()
        typer.echo(
            f"\nConnected to Veo 3 "
            f"(project: {client.project_id})"
        )
    except Exception as e:
        typer.echo(
            f"Failed to initialize Veo client: {e}"
        )
        raise typer.Exit(1)

    if reference and not reference.exists():
        typer.echo(
            f"Reference image not found: {reference}"
        )
        raise typer.Exit(1)

    if reference:
        typer.echo(
            f"   Using reference image: {reference}"
        )

    results, successful, failed = _run_generation(
        client=client,
        scenes=scenes_to_generate,
        output=output,
        ratio=ratio,
        reference=reference,
        parallel=parallel,
    )

    metadata_path = output / "generation_metadata.json"
    try:
        save_generation_metadata(results, metadata_path)
        typer.echo(f"\nMetadata saved: {metadata_path}")
    except Exception as e:
        typer.echo(f"Failed to save metadata: {e}")

    typer.echo("\nSummary:")
    typer.echo(
        f"   Total scenes: {len(manifest.scenes)}"
    )
    typer.echo(f"   Generated: {successful}")
    typer.echo(f"   Failed: {failed}")
    typer.echo(f"   Skipped: {skipped}")

    if failed > 0:
        typer.echo(
            f"\n{failed} scene(s) failed to generate"
        )
        raise typer.Exit(1)
    else:
        typer.echo("\nAll clips generated successfully!")


def _filter_scenes(
    manifest: Manifest,
    output: Path,
    skip_existing: bool,
) -> list[tuple[int, object]]:
    """Filter scenes that need generation.

    Args:
        manifest: Project manifest.
        output: Output directory.
        skip_existing: Whether to skip existing clips.

    Returns:
        List of (index, scene) tuples to generate.
    """
    scenes = []
    for i, scene in enumerate(manifest.scenes):
        if scene.source == "file" and scene.file:
            continue
        if not scene.prompt:
            continue
        clip_path = output / f"{scene.id}.mp4"
        if skip_existing and clip_path.exists():
            continue
        scenes.append((i, scene))
    return scenes


def _show_dry_run(
    scenes: list[tuple[int, object]],
) -> None:
    """Display dry run information.

    Args:
        scenes: List of (index, scene) tuples.
    """
    typer.echo(
        f"\nDry run - would generate "
        f"{len(scenes)} clips:"
    )
    for idx, scene in scenes:
        preview = (
            scene.prompt[:70] + "..."
            if len(scene.prompt) > 70
            else scene.prompt
        )
        typer.echo(
            f"   [{idx + 1}] {scene.id}: "
            f"{scene.duration}s"
        )
        typer.echo(f"       -> {preview}")


def _run_generation(
    client: object,
    scenes: list[tuple[int, object]],
    output: Path,
    ratio: str,
    reference: Path | None,
    parallel: int,
) -> tuple[list, int, int]:
    """Run parallel video generation.

    Args:
        client: VeoClient instance.
        scenes: List of (index, scene) tuples.
        output: Output directory.
        ratio: Aspect ratio string.
        reference: Optional reference image path.
        parallel: Max concurrent generations.

    Returns:
        Tuple of (results, successful_count,
        failed_count).
    """
    from concurrent.futures import (
        ThreadPoolExecutor,
        as_completed,
    )

    from .services.veo import (
        GenerationResult,
        GenerationStatus,
    )

    results: list[GenerationResult] = []
    successful = 0
    failed = 0

    typer.echo(
        f"\nGenerating {len(scenes)} clips "
        f"(max {parallel} concurrent)...\n"
    )

    def generate_scene(
        scene_data: tuple[int, object],
    ) -> GenerationResult:
        """Generate a single scene clip."""
        _, scene = scene_data
        clip_path = output / f"{scene.id}.mp4"
        duration = max(5.0, min(8.0, scene.duration))

        return client.generate_clip(
            prompt=scene.prompt,
            duration=duration,
            aspect_ratio=ratio,
            output_path=clip_path,
            scene_id=scene.id,
            reference_image=reference,
        )

    with ThreadPoolExecutor(
        max_workers=parallel
    ) as executor:
        future_to_scene = {
            executor.submit(
                generate_scene, scene_data
            ): scene_data
            for scene_data in scenes
        }

        for future in as_completed(future_to_scene):
            _, scene = future_to_scene[future]
            try:
                result = future.result()
                results.append(result)

                if (
                    result.status
                    == GenerationStatus.COMPLETED
                ):
                    successful += 1
                    typer.echo(
                        f"   {scene.id}: Generated -> "
                        f"{result.local_path}"
                    )
                else:
                    failed += 1
                    error_msg = (
                        result.error_message
                        or "Unknown error"
                    )
                    typer.echo(
                        f"   {scene.id}: Failed - "
                        f"{error_msg}"
                    )

            except Exception as e:
                failed += 1
                typer.echo(
                    f"   {scene.id}: Error - {e}"
                )
                results.append(
                    GenerationResult(
                        operation_id=(
                            f"error-{scene.id}"
                        ),
                        status=GenerationStatus.FAILED,
                        error_message=str(e),
                        metadata={
                            "scene_id": scene.id
                        },
                    )
                )

    return results, successful, failed


if __name__ == "__main__":
    app()
