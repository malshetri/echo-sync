# Echo Sync Technical Reference

This document contains the detailed setup, configuration, structure, supported
interaction modes, roadmap, and limitations for Echo Sync.

[Back to the main README](../README.md)

## Project Structure

```text
.
|-- src/echo_sync/
|   |-- ai/                 # Intent classification, context mapping, safety
|   |-- audio/              # Recording, earcons, TTS, silence and ducking
|   |-- config/             # Settings, prompts, and response configuration
|   |-- interaction/        # Dialog flow, onboarding, help, and app state
|   |-- logging_utils/      # CSV interaction logging
|   |-- media/              # Playlist management and VLC/Pygame players
|   |-- speech/             # OpenAI and offline speech-to-text backends
|   |-- app.py              # Main interaction loop
|   `-- main.py             # Command-line entry point
|-- assets/
|   |-- earcons/            # Accessible audio feedback cues
|   `-- music/              # Local music grouped by context
|-- docs/                   # Design, evaluation, testing, and reflection
|-- scripts/                # Test-audio and report helpers
|-- tests/                  # Automated test suite
|-- logs/                   # Interaction logs
|-- NUI architecture.drawio # Editable system architecture
|-- pyproject.toml          # Package metadata and dependencies
`-- README.md
```

## Interaction Modalities

| Modality | Purpose | Example |
|---|---|---|
| **Direct Control** | Immediate and predictable playback commands | "Pause" pauses the music |
| **Context-Based Request** | Interprets the user's wording and selects a suitable playlist | "I am exhausted" selects calm music |
| **Guided Help** | Supports discovery, silence, unclear input, and off-topic requests | "What can I say?" gives spoken examples |

Echo Sync interprets the context expressed in the user's words; it does **not**
perform medical or psychological emotion detection.

## Music Categories

Local tracks are organized under `assets/music/`:

| Category | Example request |
|---|---|
| `calm` | "Play something relaxing." |
| `energy` | "I need energy." |
| `focus` | "I want to study." |
| `happy` | "Play something cheerful." |
| `sad` | "I feel sad." |
| `fallback` | Used when a requested category has no tracks |

Supported file types are `.mp3`, `.wav`, `.flac`, `.ogg`, `.m4a`, `.aac`, and
`.wma`.

## Detailed Setup

### Prerequisites

- Python 3.11 or newer
- A working audio output device
- A microphone for voice mode
- An OpenAI API key for OpenAI transcription and AI classification
- VLC media player is recommended; Echo Sync falls back to Pygame if VLC is unavailable

Keyboard demo mode and common rule-based commands can be used without an API key.

### Create and Activate the Environment

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install the project and development tools:

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

For optional offline speech-to-text support:

```bash
python -m pip install -e ".[dev,offline]"
```

Create a new virtual environment on each computer. Virtual environments are
machine-specific and should not be copied or committed.

### Configuration

Copy the environment template:

```powershell
# Windows PowerShell
Copy-Item .env.example .env
```

```bash
# macOS/Linux
cp .env.example .env
```

Add the API key to `.env`:

```ini
OPENAI_API_KEY=your_api_key_here
```

Optional settings use the `ECHO_SYNC_` prefix:

```ini
ECHO_SYNC_STT_MODE=openai
ECHO_SYNC_STT_MODEL=gpt-4o-mini-transcribe
ECHO_SYNC_AI_MODEL=gpt-4o-mini
ECHO_SYNC_PLAYER=vlc
ECHO_SYNC_WAKE_WORD=echo
ECHO_SYNC_DEFAULT_VOLUME=80
ECHO_SYNC_DUCKING_VOLUME=30
ECHO_SYNC_SILENCE_TIMEOUT=10
```

For local transcription, install the `offline` dependency group and set:

```ini
ECHO_SYNC_STT_MODE=offline
```

### Add Music

Place audio files in the matching category folders:

```text
assets/music/
|-- calm/
|-- energy/
|-- focus/
|-- happy/
|-- sad/
`-- fallback/
```

### Run Options

Voice mode:

```bash
python -m echo_sync.main
```

Keyboard demo mode:

```bash
python -m echo_sync.main --demo-keyboard
```

Additional options:

```bash
python -m echo_sync.main --verbose
python -m echo_sync.main --reset-setup
python -m echo_sync.main --skip-setup
```

In keyboard mode, type `quit`, `exit`, or `q` to close the application.

### Tests

```bash
python -m pytest tests/ -v
```

With coverage:

```bash
python -m pytest tests/ --cov=echo_sync --cov-report=term-missing
```

## Roadmap

- [x] Direct music-control commands
- [x] Context-to-playlist mapping
- [x] Guided help and off-topic handling
- [x] Earcons, spoken feedback, and smart ducking
- [x] Wake-word flow and eyes-free onboarding
- [x] VLC/Pygame playback fallback
- [x] Automated tests and interaction logging
- [ ] Streaming-service integration
- [ ] Fully local AI classification
- [ ] Multilingual interaction
- [ ] Remembered user preferences and multiple profiles
- [ ] Broader testing with blind and motor-impaired users

## Known Limitations

- Accessibility has not yet been validated through comprehensive testing with blind and motor-impaired users.
- Music is loaded from local files; streaming services are not yet integrated.
- AI classification and the default STT backend require an internet connection and an OpenAI API key.
- The interaction language is currently English.
- Context selection is limited to predefined playlist categories.
- Offline STT requires the optional `faster-whisper` dependency and downloads a local model on first use.
- Text-to-speech quality depends on the operating system and available voices.
