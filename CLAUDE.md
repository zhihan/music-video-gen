# Music Video Generator (MVG) - Architecture Plan

## Overview
A Python-based tool to programmatically assemble music videos from short AI-generated clips (e.g., Google Veo, Runway) based on a structured manifest file.

## Features
1.  **Multi-Format:** Support for Vertical (9:16) and Horizontal (16:9) aspect ratios.
2.  **Manifest-Driven:** Uses `script.yaml` to define scene order, timing, and prompts.
3.  **Auto-Stitching:** Concatenates clips, handling resizing/cropping automatically.
4.  **Audio Sync:** Loops video or cuts audio to match specific durations.
5.  **Lyrics Engine:** Auto-transcribe lyrics using OpenAI Whisper and burn captions (SRT style) onto the video.

## Directory Structure
```
/
├── assets/
│   ├── clips/       # Raw video files (01.mp4, etc.)
│   ├── music/       # Input audio file
│   └── fonts/       # Custom fonts for lyrics
├── output/          # Final rendered videos
├── src/
│   ├── main.py      # Entry point
│   ├── manifest.py  # Parser for script.yaml
│   ├── editor.py    # MoviePy logic (stitch, resize, loop)
│   └── lyrics.py    # Whisper integration & subtitle rendering
├── script.yaml      # User configuration (scene list)
└── requirements.txt
```

## `script.yaml` Example
```yaml
project_name: "My Music Video"
resolution: "1080x1920" # 9:16 Vertical
fps: 24
audio_file: "assets/music/song.mp3"

scenes:
  - id: "intro"
    file: "assets/clips/01_intro.mp4"
    duration: 8.0  # Force clip to this length (loop/speed up)
    transition: "crossfade"
    
  - id: "verse1"
    file: "assets/clips/02_verse.mp4"
    duration: 16.0
    
lyrics:
  enabled: true
  provider: "whisper" # or "manual" (srt file)
  style:
    font: "Helvetica-Bold"
    size: 60
    color: "yellow"
    bg_color: "#00000080"
    position: "bottom"
```

## Implementation Steps
1.  **Core Stitcher:** Build `editor.py` to read YAML and stitch clips.
2.  **Audio Layer:** Integrate background music.
3.  **Lyrics Module:** Implement `lyrics.py` using `openai-whisper` to generate SRT, then `MoviePy` TextClip to overlay.
4.  **CLI:** Wrap it in a nice `mvg build` command.

## Tech Stack
- **Python 3.10+**
- **MoviePy:** Video editing core.
- **OpenAI Whisper:** Transcription.
- **PyYAML:** Config parsing.
