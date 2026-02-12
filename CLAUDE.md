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
# Full pipeline
video-maker create "Man's Purpose - spiritual journey, 90s"

# Or step-by-step
video-maker research "Man's Purpose" --duration 90 > scenes.json
video-maker music scenes.json > music.mp3
video-maker veo scenes.json --output clips/
video-maker assemble scenes.json clips/ music.mp3 --output final.mp4
```

## Directory Structure
```
/
├── assets/
│   ├── clips/       # Generated/Downloaded clips
│   ├── music/       # Input audio
│   └── fonts/
├── output/
├── src/
│   ├── main.py
│   ├── manifest.py
│   ├── editor.py    # MoviePy logic
│   ├── lyrics.py    # Whisper logic
│   └── generator.py # Google Veo / Vertex AI Client
├── script.yaml
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
- **MoviePy:** Video editing & assembly
- **OpenAI Whisper:** Lyrics transcription
- **Google-Cloud-AI-Platform:** Veo 3 clip generation
- **Claude/Gemini:** Research & assembly agents
- **Click/Typer:** CLI framework

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
- [ ] Basic CLI scaffold (Click)
- [ ] Research agent (prompt engineering)
- [ ] Veo API client stub
- [ ] Assembly pipeline (MoviePy)
- [ ] Text overlay templates
- [ ] Music integration
- [ ] End-to-end test with "Man's Purpose" project
