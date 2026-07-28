"""
Echo-Sync earcon manager.

Plays short audio cues (.wav files) for accessible feedback:
- listening: system is ready for input
- success: action completed successfully
- error: something went wrong
- mood_detected: context/mood was interpreted
- help: guided help is being provided

Uses winsound (built-in on Windows) or pygame as fallback.
"""

import logging
import platform
import threading
from pathlib import Path
from typing import Optional

from echo_sync.config.settings import Settings

logger = logging.getLogger(__name__)

# Earcon file names
EARCON_LISTENING = "listening"
EARCON_SUCCESS = "success"
EARCON_ERROR = "error"
EARCON_MOOD_DETECTED = "mood_detected"
EARCON_HELP = "help"

ALL_EARCONS = [
    EARCON_LISTENING,
    EARCON_SUCCESS,
    EARCON_ERROR,
    EARCON_MOOD_DETECTED,
    EARCON_HELP,
]


class EarconManager:
    """
    Manages and plays earcon audio cues.

    Earcons are short, distinctive sounds that provide non-visual
    feedback to blind users about the system state.

    Uses winsound on Windows (no extra dependencies needed),
    falls back to pygame.mixer.Sound on other platforms.
    """

    def __init__(self, settings: Settings) -> None:
        self.earcons_dir = settings.earcons_path
        self._earcon_cache: dict[str, Optional[Path]] = {}
        self._is_windows = platform.system() == "Windows"
        self._load_earcons()

    def _load_earcons(self) -> None:
        """Load and cache paths to all earcon files."""
        for name in ALL_EARCONS:
            wav_path = self.earcons_dir / f"{name}.wav"
            if wav_path.exists():
                self._earcon_cache[name] = wav_path
                logger.debug("Loaded earcon: %s", wav_path)
            else:
                self._earcon_cache[name] = None
                logger.warning("Earcon file not found: %s", wav_path)

    def play(self, earcon_name: str, blocking: bool = False) -> None:
        """
        Play an earcon sound.

        Args:
            earcon_name: Name of the earcon to play (e.g., 'listening').
            blocking: If True, wait for playback to finish.
                      If False, play in a background thread.
        """
        path = self._earcon_cache.get(earcon_name)
        if path is None:
            logger.debug("Earcon '%s' not available — skipping", earcon_name)
            return

        if blocking:
            self._play_file(path)
        else:
            thread = threading.Thread(
                target=self._play_file,
                args=(path,),
                daemon=True,
            )
            thread.start()

    def _play_file(self, path: Path) -> None:
        """Play a WAV file using the best available backend."""
        try:
            if self._is_windows:
                self._play_winsound(path)
            else:
                self._play_pygame(path)
            logger.debug("Played earcon: %s", path.stem)
        except Exception as e:
            logger.error("Failed to play earcon '%s': %s", path.stem, e)

    @staticmethod
    def _play_winsound(path: Path) -> None:
        """Play a WAV file using Windows built-in winsound module."""
        import winsound
        winsound.PlaySound(str(path), winsound.SND_FILENAME)

    @staticmethod
    def _play_pygame(path: Path) -> None:
        """Play a WAV file using pygame.mixer as fallback."""
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            sound = pygame.mixer.Sound(str(path))
            sound.play()
            # Earcons are short and should finish before the next response.
            import time
            while pygame.mixer.get_busy():
                time.sleep(0.05)
        except ImportError:
            logger.warning(
                "Neither winsound nor pygame available — earcon not played"
            )

    def play_listening(self) -> None:
        """Play the 'listening' earcon."""
        self.play(EARCON_LISTENING)

    def play_success(self) -> None:
        """Play the 'success' earcon."""
        self.play(EARCON_SUCCESS)

    def play_error(self) -> None:
        """Play the 'error' earcon."""
        self.play(EARCON_ERROR)

    def play_mood_detected(self) -> None:
        """Play the 'mood detected' earcon."""
        self.play(EARCON_MOOD_DETECTED)

    def play_help(self) -> None:
        """Play the 'help' earcon."""
        self.play(EARCON_HELP)

    def is_available(self, earcon_name: str) -> bool:
        """Check if an earcon file is available."""
        return self._earcon_cache.get(earcon_name) is not None
