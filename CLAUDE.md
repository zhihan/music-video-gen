# Music Video Generator (MVG) - Architecture Plan

## Overview
A CLI-based tool to create video content from idea to final render using AI agents and Google Veo 3.

**Pipeline:**
1. **Research Agent** → Topic/idea → Scene descriptions (narrative, visuals, timing)
2. **Music Selector** → Pick appropriate background track
3. **Script Formatter** → Convert scenes into Veo-compatible prompts
4. **Veo Generation** → Generate video clips via Google Veo 3 API
5. **Assembly Agent** → Stitch clips + text overlays + music → Final video

## Features
1.  **Agent-Driven Workflow:** Automated scene research, music selection, and assembly
2.  **Multi-Format:** Support for Vertical (9:16) and Horizontal (16:9)
3.  **Manifest-Driven:** Uses `script.yaml` to define scene order, timing, and prompts
4.  **Auto-Stitching:** Concatenates clips with text overlays, handling resizing/cropping
5.  **Audio Sync:** Loops video or cuts audio to match durations
6.  **Lyrics Engine:** Auto-transcribe via OpenAI Whisper & burn subtitles
7.  **AI Generation:** Direct integration with **Google Veo 3 API** to generate clips from prompts
8.  **CLI Interface:** Personal tool, command-line driven

## CLI Usage
```bash
# All commands default to script.yaml and can be overridden with --script

# 1. Generate scene descriptions from an idea
video-maker research "Man's Purpose - spiritual journey, 90s" --duration 90

# 2. Check project status
video-maker status
video-maker status --script custom.yaml

# 3. Generate a character reference image (for consistency across scenes)
video-maker imagen "12-year-old Asian girl with short black hair, school uniform" -o assets/character.png

# 4. Generate video clips via Veo 3 (with optional character reference)
video-maker veo
video-maker veo --reference assets/character.png   # Use character image for consistency
video-maker veo --script custom.yaml --output clips/

# 5. Assemble final video
video-maker assemble
video-maker assemble --script custom.yaml --clips clips/ --music song.mp3 --output final.mp4
```

## Directory Structure
```
/
├── assets/
│   ├── clips/       # Generated/Downloaded clips
│   ├── music/       # Input audio
│   └── fonts/
├── output/
├── clips/           # Default Veo output directory
├── src/mvg/
│   ├── cli.py       # CLI entry point (Typer)
│   ├── config.py    # Environment configuration
│   ├── agents/
│   │   ├── base.py      # Abstract base agent
│   │   └── research.py  # Scene generation agent
│   ├── models/
│   │   ├── scene.py     # Scene data model
│   │   ├── manifest.py  # Project manifest
│   │   └── project.py   # Project state
│   ├── services/
│   │   ├── anthropic.py # Claude API client
│   │   └── veo.py       # Google Veo 3 client
│   └── editor/
│       ├── compositor.py # Video stitching
│       ├── audio.py      # Audio processing
│       └── overlays.py   # Text overlays
├── script.yaml      # Default manifest file
├── pyproject.toml
└── requirements.txt
```

## `script.yaml` (Enhanced)
```yaml
project_name: "AI Masterpiece"
audio_file: "assets/music/song.mp3"

scenes:
  - id: "scene1"
    prompt: "Cinematic close up of water filling a crystal glass, 4k, photorealistic"
    duration: 8.0
    source: "generate" # Uses Veo 3
    
  - id: "scene2"
    file: "assets/clips/my_manual_clip.mp4" # Uses existing file
    duration: 4.0
```

## Tech Stack
- **Python 3.10+**
- **Typer:** CLI framework
- **Pydantic:** Data validation & settings
- **MoviePy:** Video editing & assembly
- **Anthropic SDK:** Claude API for research agent
- **Google Cloud AI Platform:** Veo 3 clip generation
- **OpenAI Whisper:** Lyrics transcription (planned)

## Implementation Notes

### Research Agent
- Uses Claude Sonnet by default
- Optional web search integration
- Outputs structured JSON scene descriptions with:
  - Visual prompts for Veo
  - Text overlays
  - Timing/duration
  - Narrative flow

### Music Selection
- **Phase 1:** Manual selection (user provides path)
- **Phase 2:** AI-generated (Suno/Udio integration)
- **Phase 3:** Mood-based library matching

### Veo Integration
- Google Veo 3 via Vertex AI
- Scene prompts → video clips
- Handles aspect ratio, duration, quality settings
- **TODO:** Confirm API access/credentials

### Assembly Agent
- Reads generated clips + scene manifest
- Applies text overlays (styled via templates)
- Syncs audio
- Outputs final MP4

## Roadmap
- [x] Basic CLI scaffold (Typer)
- [x] Research agent (Claude-powered scene generation)
- [x] Veo API client (structure ready, API calls stubbed)
- [x] Assembly pipeline (MoviePy)
- [x] Text overlay templates
- [x] Audio sync & processing
- [ ] Complete Veo 3 API integration
- [ ] Lyrics/Whisper transcription
- [ ] Music selection agent
- [ ] End-to-end test with "Man's Purpose" project
