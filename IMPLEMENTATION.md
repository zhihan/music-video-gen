# Music Video Generator - Implementation Plan

## 1. Project Structure and File Organization

```
music-video-gen/
├── pyproject.toml              # Package config, dependencies, entry points
├── requirements.txt            # Pinned dependencies
├── .env.example                # Environment variable template
├── CLAUDE.md                   # Architecture overview
├── IMPLEMENTATION.md           # This file
├── README.md                   # User documentation
│
├── assets/
│   ├── clips/                  # Generated/downloaded video clips
│   ├── music/                  # Audio files
│   └── fonts/                  # Custom fonts for overlays
│
├── output/                     # Final rendered videos
│
├── templates/
│   └── overlays/               # Text overlay style templates (JSON)
│
├── src/
│   └── mvg/                    # Main package
│       ├── __init__.py
│       ├── cli.py              # CLI entry point (Typer)
│       ├── config.py           # Configuration management
│       ├── codegen.py          # MoviePy script generation
│       │
│       ├── models/             # Data models
│       │   ├── __init__.py
│       │   ├── scene.py        # Scene dataclass
│       │   ├── manifest.py     # Manifest/script model
│       │   └── project.py      # Project state
│       │
│       ├── agents/             # AI agents
│       │   ├── __init__.py
│       │   └── base.py         # Base agent class
│       │
│       ├── services/           # External service integrations
│       │   ├── __init__.py
│       │   ├── veo.py          # Google Veo 3 client
│       │   ├── imagen.py       # Google Imagen client
│       │   └── anthropic.py    # Claude API wrapper
│       │
│       └── editor/             # Video editing
│           ├── __init__.py
│           ├── compositor.py   # Main video assembly
│           ├── overlays.py     # Text overlay rendering
│           └── audio.py        # Audio sync/mixing
│
└── tests/
```

---

## 2. Module Breakdown

### 2.1 CLI Module (`cli.py`)
**Responsibility:** Command-line interface, argument parsing, orchestration

| Command | Description |
|---------|-------------|
| `status` | Show project state |
| `imagen <prompt>` | Generate reference image |
| `veo` | Generate clips via Veo 3 |
| `generate-script` | Generate MoviePy assembly script with text overlays |

### 2.2 Models (`models/`)
**Responsibility:** Data structures, validation, serialization

| Model | Fields |
|-------|--------|
| `Scene` | id, prompt, duration, source, file, overlay_text, overlay_style |
| `Manifest` | project_name, audio_file, scenes[], aspect_ratio, output_format |
| `Project` | manifest, state, clips_generated, errors |

### 2.3 Agents (`agents/`)
**Responsibility:** AI-powered content generation and planning

| Agent | Input | Output |
|-------|-------|--------|
| `base.py` | — | Abstract base agent class |

### 2.4 Services (`services/`)
**Responsibility:** External API integrations

| Service | API | Purpose |
|---------|-----|---------|
| `VeoClient` | Google Vertex AI (Veo 3) | Generate video clips |
| `ImagenClient` | Google Vertex AI (Imagen) | Generate reference images |
| `ClaudeClient` | Anthropic API | Claude API wrapper |

### 2.5 Editor (`editor/`)
**Responsibility:** Video processing and assembly

| Module | Purpose |
|--------|---------|
| `compositor.py` | Main video assembly |
| `overlays.py` | Text overlay rendering with presets |
| `audio.py` | Audio sync/mixing |

---

## 3. Implementation Phases

### Phase 1: Foundation (Core Infrastructure) ✅
**Deliverables:**
- [x] Project scaffolding (`pyproject.toml`, package structure)
- [x] Configuration management (`config.py` with env vars)
- [x] Data models (`Scene`, `Manifest`, `Project`)
- [x] YAML manifest parser
- [x] Basic CLI skeleton with Typer

### Phase 2: Video Assembly Pipeline ✅
**Deliverables:**
- [x] MoviePy compositor (stitch existing clips)
- [x] Text overlay system with presets (title, text, subtitle)
- [x] Audio sync (loop/trim to match video)
- [x] `generate-script` CLI command (generates standalone MoviePy scripts)

### Phase 3: Veo 3 Integration ✅
**Deliverables:**
- [x] Vertex AI / Veo 3 client
- [x] Concurrent clip generation with thread pool
- [x] `veo` CLI command with dry-run, skip-existing, reference image support
- [x] Imagen client for character reference images

### Phase 4: Lyrics/Subtitles (Planned)
**Deliverables:**
- [ ] Whisper transcription client
- [ ] SRT/VTT generation
- [ ] Subtitle burn-in
- [ ] `transcribe` CLI command

---

## 4. API Integrations

### 4.1 Google Veo 3 (Vertex AI)

**Endpoint:** `us-central1-aiplatform.googleapis.com`
**Authentication:** Google Cloud service account or ADC
**SDK:** `google-cloud-aiplatform`

```python
# Example usage pattern
from google.cloud import aiplatform

client = aiplatform.VideoGenerationClient()
operation = client.generate_video(
    prompt="Cinematic shot of...",
    aspect_ratio="16:9",
    duration_seconds=8,
    output_gcs_uri="gs://bucket/output.mp4"
)
result = operation.result()  # Polling
```

**Required scopes:**
- `https://www.googleapis.com/auth/cloud-platform`

**Environment variables:**
```
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GOOGLE_CLOUD_PROJECT=your-project-id
VEO_OUTPUT_BUCKET=gs://your-bucket
```

### 4.2 Anthropic Claude

**Endpoint:** `https://api.anthropic.com/v1/messages`
**Authentication:** API key
**SDK:** `anthropic`

```python
from anthropic import Anthropic

client = Anthropic()
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    messages=[{"role": "user", "content": prompt}]
)
```

**Environment variables:**
```
ANTHROPIC_API_KEY=sk-ant-...
```

---

## 5. CLI Command Structure

```
video-maker
│
├── status                           # Show project state
│   └── --script PATH                # Path to script.yaml
│
├── imagen <prompt>                  # Generate reference image
│   ├── --output PATH                # Output image file
│   ├── --aspect-ratio TEXT          # Image aspect ratio
│   └── --negative TEXT              # Negative prompt
│
├── veo                              # Generate clips via Veo
│   ├── --script PATH                # Path to script.yaml
│   ├── --output PATH                # Output directory for clips
│   ├── --parallel INT               # Concurrent generations (default: 3)
│   ├── --reference PATH             # Reference image for consistency
│   ├── --skip-existing/--regenerate # Skip existing clips (default: skip)
│   ├── --dry-run                    # Show plan without calling API
│   └── --limit INT                  # Limit scenes to generate
│
└── generate-script                  # Generate MoviePy assembly script
    ├── --script PATH                # Path to script.yaml
    ├── --clips PATH                 # Clips directory
    ├── --output PATH                # Output Python script path
    └── --output-video PATH          # Output video path for generated script
```

**Entry point configuration (pyproject.toml):**
```toml
[project.scripts]
video-maker = "mvg.cli:app"
```

---

## 6. Dependencies

### Core
```
typer>=0.9.0          # CLI framework
pydantic>=2.0         # Data validation
pyyaml>=6.0           # Manifest parsing
python-dotenv>=1.0    # Environment management
```

### AI/ML
```
anthropic>=0.25       # Claude API
google-cloud-aiplatform>=1.45  # Veo 3 + Imagen
```

### Video/Audio
```
moviepy>=2.0          # Video editing
pillow>=10.0          # Image/text rendering
numpy>=1.24           # Array operations
```

### Dev
```
pytest>=8.0
pytest-cov>=4.0
ruff>=0.3.0           # Linting
mypy>=1.8             # Type checking
```

---

## 7. Getting Started

```bash
# Install in dev mode
pip install -e .

# Copy env config
cp .env.example .env
# Fill in Google Cloud credentials

# Verify installation
video-maker status
```
