"""CLI entry point for the music video generator."""

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


if __name__ == "__main__":
    app()
