# Music Video Generator

AI-powered CLI tool to create video content from idea to final render using agents and Google Veo 3.

## Installation

```bash
# Clone the repository
git clone https://github.com/zhihan/music-video-gen.git
cd music-video-gen

# Install in development mode
pip install -e .
```

## Configuration

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

Required:
- `GOOGLE_APPLICATION_CREDENTIALS`: For Veo 3 video generation
- `GOOGLE_CLOUD_PROJECT`: Your GCP project ID
- `VEO_OUTPUT_BUCKET`: GCS bucket for generated clips

Optional:
- `ANTHROPIC_API_KEY`: For Claude API integration
- `KIE_API_KEY`: For KIE.ai music generation (Suno)

## Usage

### Check project status

```bash
video-maker status
```

### Show version

```bash
video-maker --version
```

## Development Status

**Completed:**
- Project scaffolding, configuration, data models
- CLI with `status`, `imagen`, `veo`, `generate-script` commands
- Veo 3 integration (clip generation from prompts)
- Imagen integration (character reference images)
- MoviePy assembly script generation with text overlays

**Planned:**
- KIE.ai music generation (Suno)
- Timestamped lyrics & subtitle burn-in

## Architecture

See [CLAUDE.md](CLAUDE.md) for architecture overview and [IMPLEMENTATION.md](IMPLEMENTATION.md) for the detailed implementation plan.
