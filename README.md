# Liveframe

Automatically identify and extract highlight clips from long stream recordings using Google Gemini's video understanding.

Feed Liveframe a 5+ hour stream VOD and it will:
1. Split the video into chunks that fit Gemini's context window
2. Analyze each chunk to find the most highlight-worthy moments
3. Deduplicate moments found near chunk boundaries
4. Extract individual clips with configurable margin/padding via ffmpeg
5. Optionally add Opus-style auto-captions with speaker diarization
6. Output clips in any aspect ratio (16:9, 9:16, 1:1)

---

## Quick Start

```bash
git clone https://github.com/your-username/vugola.git
cd vugola
python3 -m venv .venv && source .venv/bin/activate  # see below for Windows
pip install -e .
cp .env.example .env   # then add your GEMINI_API_KEY
liveframe run stream.mp4
```

---

## Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Python | 3.11+ | Runtime |
| ffmpeg | Any recent | Video splitting & clip extraction |
| ffprobe | Ships with ffmpeg | Video metadata extraction |
| Gemini API key | — | Video analysis ([get one free](https://aistudio.google.com/apikey)) |

### Install Python

| Platform | Command |
|----------|---------|
| macOS | `brew install python@3.12` or download from [python.org](https://www.python.org/downloads/) |
| Ubuntu/Debian | `sudo apt update && sudo apt install python3.12 python3.12-venv` |
| Fedora | `sudo dnf install python3.12` |
| Arch | `sudo pacman -S python` |
| Windows | `winget install Python.Python.3.12` or download from [python.org](https://www.python.org/downloads/) |

Verify: `python3 --version` (or `python --version` on Windows)

### Install ffmpeg

| Platform | Command |
|----------|---------|
| macOS | `brew install ffmpeg` |
| Ubuntu/Debian | `sudo apt install ffmpeg` |
| Fedora | `sudo dnf install ffmpeg` |
| Arch | `sudo pacman -S ffmpeg` |
| Windows | `winget install ffmpeg` or download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH |

Verify: `ffmpeg -version` and `ffprobe -version`

> **Windows PATH note:** If you downloaded ffmpeg manually, extract it and add the `bin/` folder to your system PATH. Search "Environment Variables" in Windows Settings to edit PATH.

---

## Installation

### macOS / Linux

```bash
git clone https://github.com/your-username/vugola.git
cd vugola

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Liveframe
pip install -e .
```

### Windows (PowerShell)

```powershell
git clone https://github.com/your-username/vugola.git
cd vugola

# Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install Liveframe
pip install -e .
```

### Windows (Command Prompt)

```cmd
git clone https://github.com/your-username/vugola.git
cd vugola

python -m venv .venv
.venv\Scripts\activate.bat

pip install -e .
```

---

## Configuration

### API Key (required)

Get a free Gemini API key at https://aistudio.google.com/apikey

**Option A — `.env` file (recommended, works on all platforms):**

```bash
cp .env.example .env
```

Then edit `.env` and replace `your-api-key-here` with your actual key:

```
GEMINI_API_KEY=AIza...
```

**Option B — Environment variable:**

```bash
# macOS / Linux
export GEMINI_API_KEY=AIza...

# Windows PowerShell
$env:GEMINI_API_KEY="AIza..."

# Windows Command Prompt
set GEMINI_API_KEY=AIza...
```

### Optional Settings

All settings use the `LIVEFRAME_` prefix as environment variables or in your `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | — | Google Gemini API key (required) |
| `LIVEFRAME_GEMINI_MODEL` | `gemini-2.5-flash` | Model: `gemini-2.5-flash`, `gemini-2.5-pro`, `gemini-2.0-flash-lite` |
| `LIVEFRAME_ANALYSIS_MODE` | `fast` | `fast` (~2.5h per chunk, cheaper) or `detailed` (~52min per chunk, finer) |
| `LIVEFRAME_TARGET_CLIPS_PER_HOUR` | `2.5` | Highlights to find per hour of video |
| `LIVEFRAME_MIN_CLIP_SECONDS` | `15` | Minimum clip duration in seconds |
| `LIVEFRAME_MARGIN_SECONDS` | `3.0` | Padding added before/after each clip |
| `LIVEFRAME_ACCURATE_CUTS` | `false` | Re-encode for frame-accurate cuts (slower) |
| `LIVEFRAME_ANALYSIS_FPS` | `2` | FPS for analysis uploads (lower = faster uploads) |
| `LIVEFRAME_DOWNSCALE_FOR_ANALYSIS` | `false` | Downscale to 720p before uploading |

---

## Usage

### Full Pipeline (analyze + extract)

```bash
liveframe run stream.mp4
```

### Import from URL (Twitch, YouTube, etc.)

When using the hosted platform, you can paste a URL directly instead of uploading a file. The worker downloads the video using [yt-dlp](https://github.com/yt-dlp/yt-dlp).

**Supported platforms include:**

| Platform | Example URL |
|----------|-------------|
| Twitch VODs | `https://www.twitch.tv/videos/123456789` |
| Twitch Clips | `https://clips.twitch.tv/ClipName` |
| YouTube | `https://www.youtube.com/watch?v=dQw4w9WgXcQ` |
| Kick VODs | `https://kick.com/streamer/video/123` |
| Facebook | `https://www.facebook.com/watch/?v=123` |
| Instagram | `https://www.instagram.com/reel/ABC123/` |
| TikTok | `https://www.tiktok.com/@user/video/123` |
| X / Twitter | `https://x.com/user/status/123` |
| Vimeo | `https://vimeo.com/123456789` |
| Reddit | `https://www.reddit.com/r/sub/comments/abc/` |
| Dailymotion | `https://www.dailymotion.com/video/x123` |
| Rumble | `https://rumble.com/v123-title.html` |
| Streamable | `https://streamable.com/abc123` |
| Medal.tv | `https://medal.tv/games/clip/123` |

And [1,000+ more platforms](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md) supported by yt-dlp.

For the CLI, you can use yt-dlp directly:

```bash
yt-dlp -o stream.mp4 "https://www.twitch.tv/videos/123456789"
liveframe run stream.mp4
```

Clips are saved to `./liveframe_output/<video_name>/`.

### Common Options

```bash
# Custom highlight criteria
liveframe run stream.mp4 -c "Look for funny moments and big plays"

# Use a preset (gaming, irl, music, sports, educational)
liveframe run stream.mp4 -p gaming

# More clips per hour, shorter minimum length
liveframe run stream.mp4 --clips-per-hour 5 --min-clip-length 10

# Use Gemini Pro for better analysis (costs more)
liveframe run stream.mp4 -m pro

# Dry run — analyze only, write manifest without extracting
liveframe run stream.mp4 --dry-run

# Frame-accurate cuts (slower, re-encodes)
liveframe run stream.mp4 --accurate-cuts

# Custom output directory
liveframe run stream.mp4 -o ./my-clips

# Output as 9:16 vertical (TikTok/Reels/Shorts)
liveframe run stream.mp4 --aspect-ratio 9:16

# Output as 1:1 square (Instagram)
liveframe run stream.mp4 --aspect-ratio 1:1

# Add Opus-style auto-captions
liveframe run stream.mp4 --captions

# Captions with speaker diarization (each speaker gets a unique color)
liveframe run stream.mp4 --captions --diarize
```

### Analyze Only

Output highlights as JSON or a table (no clip extraction):

```bash
liveframe analyze stream.mp4
liveframe analyze stream.mp4 --format table
```

### Extract from Manifest

Run analysis first, curate the results, then extract only the clips you want:

```bash
liveframe run stream.mp4 --dry-run
# Edit liveframe_output/stream/manifest.json to remove unwanted highlights
liveframe extract stream.mp4 --highlights liveframe_output/stream/manifest.json
```

### Web Dashboard & API Server

Liveframe includes a web-based dashboard for browsing, editing, and rendering clips:

```bash
liveframe serve
```

Open http://localhost:8000 in your browser. The dashboard lets you:
- Browse and select video files
- Submit processing jobs
- Preview detected highlights
- Customize aspect ratio, captions, watermarks, and intros/outros per clip
- Render final clips with your settings

Server options:

```bash
liveframe serve --port 9000       # custom port
liveframe serve --reload          # auto-reload on code changes (development)
liveframe serve --host 127.0.0.1  # bind to localhost only
```

---

## Auto-Captions

Liveframe can burn Opus-style captions into clips — word-by-word display with the active word highlighted.

```bash
# Install the captions extra
pip install -e ".[captions]"

# Basic captions (uses local faster-whisper)
liveframe run stream.mp4 --captions

# Use a larger Whisper model for better accuracy
liveframe run stream.mp4 --captions --caption-model small
```

### Speaker Diarization

When multiple people are talking, `--diarize` assigns each speaker a unique caption color.

**Additional requirements:**

1. Install pyannote: `pip install pyannote.audio`
2. Accept model terms on HuggingFace:
   - [pyannote/segmentation-3.0](https://hf.co/pyannote/segmentation-3.0)
   - [pyannote/speaker-diarization-3.1](https://hf.co/pyannote/speaker-diarization-3.1)
3. Create an access token at [hf.co/settings/tokens](https://hf.co/settings/tokens) (Read permission)

```bash
# Set your HuggingFace token
export LIVEFRAME_HF_TOKEN=hf_...  # or add to .env

# Run with diarization
liveframe run stream.mp4 --captions --diarize
```

---

## Preset Criteria

| Preset | Best For |
|--------|----------|
| `general` | Any content (default) |
| `gaming` | Gameplay — kills, clutches, reactions |
| `irl` | IRL streams — interactions, surprises, stories |
| `music` | Music — performances, reactions |
| `sports` | Sports — goals, comebacks |
| `educational` | Tutorials — key insights, demos, Q&A |

---

## Output Structure

```
liveframe_output/stream/
├── clip_001_00h12m34s_insane_triple_kill.mp4
├── clip_002_01h05m12s_funny_donation_reaction.mp4
├── clip_003_02h30m45s_clutch_victory.mp4
├── rendered/                  # crops, captions, watermarked versions
│   └── clip_001_..._9x16.mp4
└── manifest.json              # full metadata, settings, timestamps
```

---

## REST API Reference

When running `liveframe serve`, the full OpenAPI docs are at http://localhost:8000/docs.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/jobs` | Submit a processing job |
| `GET` | `/jobs` | List all jobs |
| `GET` | `/jobs/{id}` | Poll job status and progress |
| `GET` | `/jobs/{id}/highlights` | Get detected highlights |
| `GET` | `/jobs/{id}/clips` | Get extracted clips |
| `DELETE` | `/jobs/{id}` | Cancel or remove a job |
| `POST` | `/jobs/{id}/render/{clip_index}` | Render clip with effects |
| `GET` | `/jobs/{id}/render/{clip_index}/status` | Poll render progress |
| `POST` | `/jobs/{id}/clips/{clip_index}/transcribe` | Transcribe clip audio |
| `GET` | `/jobs/{id}/clips/{clip_index}/transcribe/status` | Poll transcription status |
| `GET` | `/jobs/{id}/thumbnail/{clip_index}` | Get clip thumbnail |
| `GET` | `/jobs/{id}/session-defaults` | Get session render defaults |
| `PUT` | `/jobs/{id}/session-defaults` | Set session render defaults |
| `GET` | `/probe?path=...` | Probe video file metadata |
| `GET` | `/browse?path=...` | Browse filesystem for videos |
| `GET` | `/fonts` | List available caption fonts |
| `GET` | `/asset?path=...` | Serve local media file |
| `GET` | `/health` | System health check |

### Example API Usage

```bash
# Submit a job
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"input_path": "/path/to/stream.mp4", "preset": "gaming"}'

# Poll status
curl http://localhost:8000/jobs/{job_id}

# Check system health
curl http://localhost:8000/health
```

---

## How It Works

1. **Probe** — Extract video metadata (duration, resolution, codec) via ffprobe
2. **Chunk** — Split the timeline into overlapping windows that fit Gemini's 1M token context
3. **Split** — Create physical chunk files via `ffmpeg -c copy` (fast, no re-encoding)
4. **Upload** — Upload each chunk to Gemini's File API
5. **Analyze** — Send each chunk with a structured prompt; Gemini returns JSON with timestamps, titles, descriptions, and confidence scores
6. **Deduplicate** — Merge highlights found in overlapping regions between chunks
7. **Extract** — Cut clips from the source video with configurable margin

---

## Setup for AI Agents (Claude Code, Codex, etc.)

If you're using an AI coding agent to set up and run Liveframe, here's what the agent needs to do:

### 1. Check prerequisites

```bash
python3 --version   # needs 3.11+
ffmpeg -version     # must be installed
ffprobe -version    # must be installed
```

### 2. Create virtual environment and install

```bash
cd /path/to/vugola
python3 -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\Activate.ps1  # Windows PowerShell
pip install -e .
```

### 3. Configure API key

```bash
cp .env.example .env
# Edit .env to add: GEMINI_API_KEY=<user's key>
```

### 4. Verify installation

```bash
liveframe --help           # CLI works
liveframe serve &          # start server
curl http://localhost:8000/health   # all checks pass
```

### 5. Run a job

```bash
liveframe run /path/to/video.mp4 -p gaming
```

**Notes for agents:**
- The `.env` file in the project root is auto-loaded — no need to export variables
- The `liveframe` CLI is available after `pip install -e .` (registered as a console script)
- For captions, also run `pip install -e ".[captions]"`
- The web dashboard at http://localhost:8000 provides a GUI alternative to the CLI
- All output goes to `./liveframe_output/<video_stem>/` by default
- Check `/health` endpoint to verify ffmpeg and API key are configured

---

## Troubleshooting

### "command not found: liveframe"

Make sure your virtual environment is activated:

```bash
source .venv/bin/activate    # macOS/Linux
.venv\Scripts\Activate.ps1   # Windows PowerShell
```

### "No Gemini API key found"

Ensure `GEMINI_API_KEY` is set. Check with:

```bash
# macOS/Linux
echo $GEMINI_API_KEY

# Windows PowerShell
echo $env:GEMINI_API_KEY
```

Or verify your `.env` file exists in the project root and contains `GEMINI_API_KEY=...`.

### "ffmpeg: command not found"

Install ffmpeg (see [Prerequisites](#install-ffmpeg)) and ensure it's on your PATH:

```bash
which ffmpeg    # macOS/Linux — should print a path
where ffmpeg    # Windows — should print a path
```

### Windows: "running scripts is disabled"

If PowerShell blocks the venv activation script:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Captions not working

Install the captions extra:

```bash
pip install -e ".[captions]"
```

This installs `faster-whisper` for local transcription.

### Diarization errors

Speaker diarization requires:
1. `pip install pyannote.audio`
2. A HuggingFace token with access to the pyannote models (see [Speaker Diarization](#speaker-diarization))
3. `LIVEFRAME_HF_TOKEN` set in your `.env` or environment

---

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check src/
```

---

## License

GPL-3.0-or-later

