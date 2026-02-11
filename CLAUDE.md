# Music Video Generator (MVG) - Architecture Plan

## Overview
A Python-based tool to programmatically assemble music videos from AI-generated clips.
**New Feature:** Can generate clips directly using Google Veo 3 (via Vertex AI) if prompts are provided.

## Features
1.  **Multi-Format:** Support for Vertical (9:16) and Horizontal (16:9).
2.  **Manifest-Driven:** Uses `script.yaml` to define scene order, timing, and **prompts**.
3.  **Auto-Stitching:** Concatenates clips, handling resizing/cropping.
4.  **Audio Sync:** Loops video or cuts audio to match durations.
5.  **Lyrics Engine:** Auto-transcribe via OpenAI Whisper & burn subtitles.
6.  **AI Generation:** Direct integration with **Google Veo 3 API** to generate missing clips from prompts.

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
- **MoviePy:** Editing.
- **OpenAI Whisper:** Lyrics.
- **Google-Cloud-AI-Platform:** Veo 3 Generation.
