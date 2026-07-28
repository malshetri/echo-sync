"""
Echo-Sync text-to-speech service.

Provides spoken feedback so blind users hear system responses.
Uses a best-effort approach:
  1. Try pyttsx3 (cross-platform, offline)
  2. Fall back to OS commands (say on macOS, espeak on Linux)
  3. If all fail, silently degrade — the app still prints responses.
"""

import logging
import platform
import subprocess
import threading
from typing import Optional

logger = logging.getLogger(__name__)


class TTSService:
    """
    Best-effort text-to-speech service.

    Speaks text aloud when possible and degrades safely when no backend exists.
    """

    def __init__(self) -> None:
        self._engine = None
        self._lock = threading.Lock()
        self._available = False
        self._backend: str = "none"

        self._init_engine()

    def _init_engine(self) -> None:
        """Try to initialize a TTS engine."""
        # Prefer the same offline library on every platform.
        try:
            import pyttsx3

            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", 160)
            self._available = True
            self._backend = "pyttsx3"
            logger.info("TTS initialized with pyttsx3")
            return
        except Exception as e:
            logger.debug("pyttsx3 not available: %s", e)

        # Otherwise use the speech service already provided by the OS.
        system = platform.system()
        if system == "Darwin" and self._command_exists("say"):
            self._available = True
            self._backend = "say"
            logger.info("TTS initialized with macOS 'say' command")
        elif system == "Linux" and self._command_exists("espeak"):
            self._available = True
            self._backend = "espeak"
            logger.info("TTS initialized with 'espeak' command")
        elif system == "Windows":
            # Windows includes SAPI, so no extra package is needed.
            self._available = True
            self._backend = "sapi"
            logger.info("TTS initialized with Windows SAPI (PowerShell)")
        else:
            logger.warning(
                "No TTS backend available — spoken feedback disabled"
            )

    @staticmethod
    def _command_exists(cmd: str) -> bool:
        """Check if a command is available on the system PATH."""
        try:
            subprocess.run(
                [cmd, "--version"],
                capture_output=True,
                timeout=2,
            )
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            return False

    def speak(self, text: str) -> None:
        """
        Speak the given text aloud.

        If TTS is unavailable, this is a no-op.
        Never raises — all errors are logged and swallowed.
        """
        if not self._available or not text or not text.strip():
            return

        # Serialize responses because overlapping speech is unusable in an
        # eyes-free interface.
        with self._lock:
            self._speak_blocking(text)

    def _speak_blocking(self, text: str) -> None:
        """Speak the text using the selected backend."""
        try:
            if self._backend == "pyttsx3":
                self._speak_pyttsx3(text)
            elif self._backend == "say":
                self._speak_os_command(["say", text])
            elif self._backend == "espeak":
                self._speak_os_command(["espeak", text])
            elif self._backend == "sapi":
                self._speak_sapi(text)
        except Exception as e:
            logger.error("TTS failed: %s", e)

    def _speak_pyttsx3(self, text: str) -> None:
        """Speak using pyttsx3 engine (already serialized by speak())."""
        if self._engine is None:
            return
        try:
            self._engine.say(text)
            self._engine.runAndWait()
        except RuntimeError:
            # Another utterance may still be finishing.
            logger.debug("pyttsx3 busy, skipping utterance")

    @staticmethod
    def _speak_os_command(cmd: list[str]) -> None:
        """Speak using an OS command (say, espeak)."""
        subprocess.run(cmd, capture_output=True, timeout=60)

    @staticmethod
    def _speak_sapi(text: str) -> None:
        """Speak using Windows SAPI via PowerShell."""
        safe_text = text.replace("'", "''")
        # Prefer an English voice because all current prompts are in English.
        ps_command = (
            "Add-Type -AssemblyName System.Speech; "
            "$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$en = $synth.GetInstalledVoices() | Where-Object "
            "{ $_.Enabled -and $_.VoiceInfo.Culture.Name -like 'en*' } | "
            "Select-Object -First 1; "
            "if ($en) { $synth.SelectVoice($en.VoiceInfo.Name) }; "
            "$synth.Rate = 2; "
            f"$synth.Speak('{safe_text}')"
        )
        subprocess.run(
            ["powershell", "-Command", ps_command],
            capture_output=True,
            timeout=60,
        )

    @property
    def is_available(self) -> bool:
        """Check if TTS is available."""
        return self._available

    @property
    def backend_name(self) -> str:
        """Get the name of the active TTS backend."""
        return self._backend

    def cleanup(self) -> None:
        """Release TTS resources."""
        if self._engine is not None:
            try:
                self._engine.stop()
            except Exception:
                pass
            self._engine = None
        self._available = False
