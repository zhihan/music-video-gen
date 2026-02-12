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
- `ANTHROPIC_API_KEY`: For research agent (Claude)
- `GOOGLE_APPLICATION_CREDENTIALS`: For Veo 3 video generation
- `GOOGLE_CLOUD_PROJECT`: Your GCP project ID

Optional:
- `OPENAI_API_KEY`: For Whisper transcription
- `VEO_OUTPUT_BUCKET`: GCS bucket for generated clips

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

**Phase 1: Foundation** ✅ (Current PR)
- Project scaffolding
- Configuration management
- Data models (Scene, Manifest, Project)
- Basic CLI with status command

**Phase 2-6: Coming Soon**
- Video assembly pipeline
- Research agent
- Veo 3 integration
- Lyrics/subtitles
- Full pipeline orchestration

## Architecture

See [CLAUDE.md](CLAUDE.md) for architecture overview and [IMPLEMENTATION.md](IMPLEMENTATION.md) for the detailed implementation plan.
