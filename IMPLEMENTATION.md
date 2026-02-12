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
│   ├── overlays/               # Text overlay style templates (JSON)
│   └── prompts/                # Agent prompt templates
│
├── src/
│   └── mvg/                    # Main package
│       ├── __init__.py
│       ├── cli.py              # CLI entry point (Typer)
│       ├── config.py           # Configuration management
│       │
│       ├── models/             # Data models
│       │   ├── __init__.py
│       │   ├── scene.py        # Scene dataclass
│       │   ├── manifest.py     # Manifest/script model
│       │   └── project.py      # Project state
│       │
│       ├── agents/             # AI agents
│       │   ├── __init__.py
│       │   ├── base.py         # Base agent class
│       │   ├── research.py     # Research agent (Claude)
│       │   └── assembly.py     # Assembly planning agent
│       │
│       ├── services/           # External service integrations
│       │   ├── __init__.py
│       │   ├── veo.py          # Google Veo 3 client
│       │   ├── whisper.py      # OpenAI Whisper transcription
│       │   └── anthropic.py    # Claude API wrapper
│       │
│       ├── editor/             # Video editing
│       │   ├── __init__.py
│       │   ├── compositor.py   # Main video assembly
│       │   ├── overlays.py     # Text overlay rendering
│       │   ├── audio.py        # Audio sync/mixing
│       │   └── effects.py      # Transitions, filters
│       │
│       └── utils/
│           ├── __init__.py
│           ├── paths.py        # Path resolution
│           └── formats.py      # Video format constants
│
└── tests/
    ├── conftest.py
    ├── test_cli.py
    ├── test_models/
    ├── test_agents/
    ├── test_services/
    └── test_editor/
```

---

## 2. Module Breakdown

### 2.1 CLI Module (`cli.py`)
**Responsibility:** Command-line interface, argument parsing, orchestration

| Command | Description |
|---------|-------------|
| `create <idea>` | Full pipeline execution |
| `research <idea>` | Generate scene descriptions |
| `music <scenes>` | Select/validate music |
| `veo <scenes>` | Generate clips via Veo 3 |
| `assemble <scenes> <clips> <music>` | Stitch final video |
| `transcribe <audio>` | Generate lyrics/subtitles |
| `status` | Show project state |

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
| `ResearchAgent` | Idea string, duration | List[Scene] with prompts |
| `AssemblyAgent` | Manifest, clips | Assembly instructions |

### 2.4 Services (`services/`)
**Responsibility:** External API integrations

| Service | API | Purpose |
|---------|-----|---------|
| `VeoClient` | Google Vertex AI (Veo 3) | Generate video clips |
| `WhisperClient` | OpenAI Whisper | Transcribe audio to subtitles |
| `ClaudeClient` | Anthropic API | Power research/assembly agents |

### 2.5 Editor (`editor/`)
**Responsibility:** Video processing and assembly

| Module | Functions |
|--------|-----------|
| `compositor.py` | `stitch_clips()`, `add_transitions()`, `export()` |
| `overlays.py` | `render_text()`, `apply_style()`, `position_overlay()` |
| `audio.py` | `sync_audio()`, `loop_audio()`, `fade_audio()` |
| `effects.py` | `crossfade()`, `resize()`, `crop_to_aspect()` |

---

## 3. Implementation Phases

### Phase 1: Foundation (Core Infrastructure)
**Dependencies:** None
**Deliverables:**
- [ ] Project scaffolding (`pyproject.toml`, package structure)
- [ ] Configuration management (`config.py` with env vars)
- [ ] Data models (`Scene`, `Manifest`, `Project`)
- [ ] YAML manifest parser
- [ ] Basic CLI skeleton with Typer

**Key Files:**
```
src/mvg/__init__.py
src/mvg/cli.py
src/mvg/config.py
src/mvg/models/scene.py
src/mvg/models/manifest.py
```

### Phase 2: Video Assembly Pipeline
**Dependencies:** Phase 1
**Deliverables:**
- [ ] MoviePy compositor (stitch existing clips)
- [ ] Text overlay system (basic styles)
- [ ] Audio sync (loop/trim to match video)
- [ ] `assemble` CLI command

**Key Files:**
```
src/mvg/editor/compositor.py
src/mvg/editor/overlays.py
src/mvg/editor/audio.py
```

### Phase 3: Research Agent
**Dependencies:** Phase 1
**Deliverables:**
- [ ] Claude API wrapper
- [ ] Research agent with structured output
- [ ] Prompt templates for scene generation
- [ ] `research` CLI command

**Key Files:**
```
src/mvg/services/anthropic.py
src/mvg/agents/base.py
src/mvg/agents/research.py
templates/prompts/research.txt
```

### Phase 4: Veo 3 Integration
**Dependencies:** Phase 1, Phase 3
**Deliverables:**
- [ ] Vertex AI / Veo 3 client
- [ ] Async clip generation with polling
- [ ] Progress tracking and retry logic
- [ ] `veo` CLI command

**Key Files:**
```
src/mvg/services/veo.py
```

### Phase 5: Lyrics/Subtitles
**Dependencies:** Phase 2
**Deliverables:**
- [ ] Whisper transcription client
- [ ] SRT/VTT generation
- [ ] Subtitle burn-in
- [ ] `transcribe` CLI command

**Key Files:**
```
src/mvg/services/whisper.py
src/mvg/editor/subtitles.py
```

### Phase 6: Full Pipeline & Polish
**Dependencies:** All previous phases
**Deliverables:**
- [ ] `create` command (end-to-end)
- [ ] Project state persistence
- [ ] Error recovery / resume
- [ ] Progress display (rich console)

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

### 4.3 OpenAI Whisper

**Option A: API**
```python
from openai import OpenAI

client = OpenAI()
transcription = client.audio.transcriptions.create(
    model="whisper-1",
    file=audio_file,
    response_format="srt"
)
```

**Option B: Local (faster-whisper)**
```python
from faster_whisper import WhisperModel

model = WhisperModel("large-v3")
segments, info = model.transcribe(audio_path)
```

**Environment variables:**
```
OPENAI_API_KEY=sk-...
WHISPER_MODEL=large-v3  # For local
```

---

## 5. CLI Command Structure

```
video-maker
│
├── create <idea>                    # Full pipeline
│   ├── --duration INT               # Target duration in seconds
│   ├── --aspect [16:9|9:16]         # Output aspect ratio
│   ├── --music PATH                 # Optional audio file
│   └── --output PATH                # Output directory
│
├── research <idea>                  # Generate scene descriptions
│   ├── --duration INT               # Target duration
│   ├── --scenes INT                 # Number of scenes (auto if omitted)
│   ├── --style TEXT                 # Visual style hints
│   └── --output PATH                # Output JSON file
│
├── music <scenes-file>              # Music selection/validation
│   ├── --file PATH                  # Specific audio file
│   └── --output PATH                # Copy to output location
│
├── veo <scenes-file>                # Generate clips via Veo
│   ├── --output PATH                # Output directory for clips
│   ├── --parallel INT               # Concurrent generations (default: 3)
│   └── --skip-existing              # Don't regenerate existing clips
│
├── assemble <scenes> <clips> <music># Stitch final video
│   ├── --output PATH                # Output file
│   ├── --format [mp4|webm|mov]      # Container format
│   └── --quality [draft|final]      # Encoding quality
│
├── transcribe <audio>               # Generate subtitles
│   ├── --output PATH                # Output SRT/VTT file
│   ├── --format [srt|vtt]           # Subtitle format
│   └── --language TEXT              # Force language
│
└── status                           # Show project state
    └── --project PATH               # Project directory
```

**Entry point configuration (pyproject.toml):**
```toml
[project.scripts]
video-maker = "mvg.cli:app"
```

---

## 6. Testing Approach

### 6.1 Unit Tests
**Coverage:** Models, utils, isolated functions

```python
# tests/test_models/test_scene.py
def test_scene_from_yaml():
    data = {"id": "s1", "prompt": "test", "duration": 5.0}
    scene = Scene.from_dict(data)
    assert scene.id == "s1"
    assert scene.duration == 5.0
```

### 6.2 Integration Tests
**Coverage:** Service clients with mocked APIs

```python
# tests/test_services/test_veo.py
@pytest.fixture
def mock_vertex():
    with patch("google.cloud.aiplatform.VideoGenerationClient") as m:
        yield m

def test_generate_clip(mock_vertex):
    client = VeoClient()
    result = client.generate("prompt", duration=5)
    assert result.path.exists()
```

### 6.3 Editor Tests
**Coverage:** Video processing with small test clips

```python
# tests/test_editor/test_compositor.py
def test_stitch_clips(tmp_path, sample_clips):
    output = tmp_path / "output.mp4"
    stitch_clips(sample_clips, output)
    assert output.exists()
    # Verify duration matches sum of inputs
```

### 6.4 End-to-End Tests
**Coverage:** Full pipeline with fixtures

```python
# tests/test_e2e.py
@pytest.mark.slow
def test_full_pipeline(tmp_project):
    result = runner.invoke(app, ["create", "test idea", "--duration", "10"])
    assert result.exit_code == 0
    assert (tmp_project / "output" / "final.mp4").exists()
```

### 6.5 Test Fixtures
- Small (1-2 second) test video clips
- Sample audio files
- Mock API responses (recorded/fixture-based)

**Test commands:**
```bash
# Unit tests only
pytest tests/ -m "not slow"

# Full suite
pytest tests/

# With coverage
pytest tests/ --cov=mvg --cov-report=html
```

---

## 7. Component Complexity Estimates

| Component | Complexity | Notes |
|-----------|------------|-------|
| **CLI scaffold** | Low | Typer boilerplate, straightforward |
| **Data models** | Low | Pydantic dataclasses, YAML parsing |
| **Config management** | Low | Env vars, simple validation |
| **Claude client** | Low | SDK wrapper, structured output parsing |
| **Research agent** | Medium | Prompt engineering, output parsing |
| **Veo client** | Medium-High | Async operations, GCS, polling, error handling |
| **MoviePy compositor** | Medium | Clip concatenation, resizing, encoding |
| **Text overlays** | Medium | Font handling, positioning, styling |
| **Audio sync** | Medium | Duration matching, looping, fades |
| **Whisper integration** | Low-Medium | API call or local model setup |
| **Subtitle burn-in** | Medium | Timing sync, styling |
| **Full pipeline orchestration** | High | State management, error recovery, coordination |
| **Project state persistence** | Medium | Save/resume, partial completion tracking |

### Complexity Legend
- **Low:** < 100 LOC, straightforward implementation
- **Medium:** 100-300 LOC, requires careful design
- **Medium-High:** 300-500 LOC, multiple edge cases
- **High:** 500+ LOC, complex state/coordination

---

## 8. Dependencies

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
google-cloud-aiplatform>=1.45  # Veo 3
openai>=1.0           # Whisper API (optional)
faster-whisper>=1.0   # Local Whisper (optional)
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

## 9. Risk Areas & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Veo 3 API access/quotas | High | Early credential setup, fallback to manual clips |
| Long generation times | Medium | Async/parallel generation, progress display |
| MoviePy encoding issues | Medium | Test multiple codecs, provide format options |
| Large file handling | Medium | Streaming, temp file cleanup, progress bars |
| API cost control | Medium | Dry-run mode, confirmation prompts |

---

## 10. Getting Started (First Steps)

1. **Initialize project:**
   ```bash
   mkdir -p src/mvg assets/{clips,music,fonts} output templates/{overlays,prompts} tests
   ```

2. **Create pyproject.toml** with dependencies and entry point

3. **Implement Phase 1** (foundation) in order:
   - `config.py` - env var loading
   - `models/scene.py` - Scene dataclass
   - `models/manifest.py` - Manifest with YAML loading
   - `cli.py` - Basic Typer app with `status` command

4. **Verify with:**
   ```bash
   pip install -e .
   video-maker status
   ```

5. **Continue with Phase 2** (assembly) as the core value proposition
