# Echo Sync

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Course: HTW Berlin NUI SS 2026](https://img.shields.io/badge/HTW%20Berlin-NUI%20SS%202026-green.svg)](#course-project)

> **A screen-free Natural User Interface music player designed with accessibility goals, particularly for users with visual or motor impairments.**

Echo Sync replaces visual menus and touch controls with natural speech, spoken
responses, and short audio cues. Users can control playback directly or describe
their situation—for example, "I need to focus"—and receive a suitable local
playlist.

The application combines a fast rule-based command path with AI-assisted intent
classification. Common controls stay predictable, while flexible requests can
still be understood naturally.

## Live Demo

Watch a short demonstration of Echo Sync's voice and audio interaction:

▶️ **[Watch the Echo Sync live demo on YouTube](https://youtu.be/3G0jFKz5XHY)**

## Highlights

- **Natural voice control:** Play, pause, resume, skip tracks, adjust volume, and
  identify the current song.
- **Context-aware playback:** Maps requests such as "I am tired" or "I need
  energy" to calm, energy, focus, happy, or sad playlists.
- **Hybrid intent handling:** Resolves common commands locally before using AI
  for more flexible wording.
- **Audio-first feedback:** Uses spoken responses, earcons, guided help,
  eyes-free onboarding, and smart volume ducking.
- **Resilient operation:** Supports VLC/Pygame playback fallbacks and optional
  offline transcription with `faster-whisper`.
- **Testable interaction flow:** Includes automated tests and structured
  interaction logging for evaluation.

## How It Works

Each request passes through a focused audio pipeline:

1. **Listen** and capture microphone input.
2. **Transcribe** with OpenAI speech-to-text or optional offline Whisper.
3. **Activate** the voice session using the "Echo" wake word.
4. **Classify** common phrases locally and flexible requests with AI.
5. **Route** the intent to playback, context selection, or guided help.
6. **Respond** through speech and earcons while temporarily ducking the music.
7. **Log** the interaction for testing and evaluation.

[![Echo Sync NUI architecture](docs/nui-architecture.svg)](<NUI architecture.drawio>)

The editable diagram is available in
[NUI architecture.drawio](<NUI architecture.drawio>). Detailed configuration,
project structure, music categories, and run options are collected in the
[technical reference](docs/14_technical_reference.md).

## Quick Start

### Requirements

- Python **3.11 or newer**
- An audio output device and, for voice mode, a microphone
- An OpenAI API key for AI classification and OpenAI transcription
- VLC media player is recommended; Pygame is used as a fallback

Keyboard demo mode and common rule-based commands can run without an API key.

### Install

```bash
git clone https://github.com/echo-sync-group7/echo-sync.git
cd echo-sync
python -m venv .venv
python -m pip install -e ".[dev]"
```

Activate the virtual environment and copy `.env.example` to `.env` using the
commands for your operating system in the
[technical reference](docs/14_technical_reference.md). Then add your key:

```ini
OPENAI_API_KEY=your_api_key_here
```

Add local music to the category folders under `assets/music/`, then run either
voice mode or keyboard demo mode:

```bash
python -m echo_sync.main
python -m echo_sync.main --demo-keyboard
```

Run the test suite:

```bash
python -m pytest tests/ -v
```

## Example Commands

```text
"Echo, play music."
"Echo, pause."
"Echo, next song."
"Echo, make it louder."
"Echo, what song is this?"
"Echo, I need to focus."
"Echo, what can I say?"
```

## Technology Stack

| Component | Technology |
|---|---|
| Language and packaging | Python 3.11+, setuptools |
| AI classification | OpenAI `gpt-4o-mini` |
| Speech-to-text | OpenAI `gpt-4o-mini-transcribe` |
| Optional offline STT | `faster-whisper` |
| Audio recording | `sounddevice`, `soundfile` |
| Music playback | `python-vlc`, `pygame-ce` |
| Configuration | Pydantic, `pydantic-settings`, `python-dotenv` |
| Terminal interface | Rich |
| Testing | pytest, pytest-cov |

## Course Project

Echo Sync was developed by **Group 7** for HTW Berlin's **Natural User
Interfaces (NUI)** course in the **Summer Semester 2026 (SS 2026)**.

| Team Member | Primary Role |
|---|---|
| Muneer Al-Shetri | Lead Developer & System Architecture Lead |
| Ahmed Al-Odaini | Project Coordinator, Prototype & Voice/Speech Pipeline Lead |
| Ammar Albahri | Usability Evaluation Lead |
| Bashar Al Abdalla | AI Interaction Lead |
| Magd Alwajih | Tech Stack & Testing/CI Lead & Review |

The team collaborated on planning, design decisions, implementation, testing,
and review alongside these primary responsibilities.

## Documentation

- [Technical reference](docs/14_technical_reference.md)
- [Project summary](docs/01_project_summary.md)
- [Voice control vs. AI assistant](docs/02_voice_control_vs_ai_assistant.md)
- [Interaction modalities](docs/03_modalities.md)
- [System architecture](docs/07_system_diagram.md)
- [User journey](docs/08_user_journey.md)
- [Interaction flow](docs/09_interaction_flow.md)
- [Heuristic evaluation](docs/10_heuristic_evaluation.md)
- [Lo-fi testing](docs/11_lofi_testing.md)
- [Test plan](docs/12_test_plan.md)
- [Final reflection](docs/13_final_reflection.md)

## Current Scope

- Accessibility is a design goal but has not yet been validated through
  comprehensive testing with blind and motor-impaired users.
- Music currently comes from local files; streaming services are not integrated.
- The default AI and transcription services require an internet connection and
  an OpenAI API key; optional offline transcription is available.
- Interaction is currently in English and uses predefined playlist categories.

See the [technical reference](docs/14_technical_reference.md) for the complete
roadmap and known limitations.

## License

Echo Sync source code and original project assets are released under the
[MIT License](LICENSE). The included Jamendo demonstration tracks retain their
Creative Commons licenses; see [ASSET_LICENSES.md](ASSET_LICENSES.md) for
attribution and reuse conditions.

Copyright (c) 2026 Group 7, HTW Berlin.
