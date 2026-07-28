"""
First-run setup for Echo-Sync.

The tutorial checks audio output, explains the main commands, reports missing
configuration by voice, and saves a local completion marker. This keeps setup
usable without relying on text shown on screen.
"""

import logging
from pathlib import Path
from typing import Callable, Optional

from echo_sync.config.settings import PROJECT_ROOT, Settings

logger = logging.getLogger(__name__)

# This local marker prevents the tutorial from running on every start.
SETUP_MARKER = PROJECT_ROOT / ".echo_sync_setup_complete"

# Short confirmations accepted during voice setup.
_READY_WORDS = {"ready", "yes", "yeah", "okay", "ok", "start", "begin", "sure", "go"}


class OnboardingWizard:
    """Runs the one-time, voice-guided first-run setup for Echo-Sync."""

    def __init__(
        self,
        settings: Settings,
        respond: Callable[[str], None],
        earcons,
        console,
        recorder=None,
        stt=None,
        demo_keyboard: bool = False,
    ) -> None:
        self.settings = settings
        self._respond = respond
        self.earcons = earcons
        self.console = console
        self.recorder = recorder
        self.stt = stt
        self.demo_keyboard = demo_keyboard

    # Public API

    @staticmethod
    def is_complete() -> bool:
        """True if onboarding has already been completed at least once."""
        return SETUP_MARKER.exists()

    @staticmethod
    def reset() -> None:
        """Remove the completion marker so onboarding runs again next start."""
        try:
            SETUP_MARKER.unlink(missing_ok=True)
        except Exception as e:  # pragma: no cover - best effort
            logger.debug("Could not reset onboarding marker: %s", e)

    def should_run(self, force: bool = False, skip: bool = False) -> bool:
        """Decide whether the onboarding flow should run on this start."""
        if skip:
            return False
        if force:
            return True
        return not self.is_complete()

    def run(self) -> None:
        """Execute the full voice-guided onboarding flow."""
        logger.info("Running first-run onboarding (FR-10)")

        self._respond(
            "Welcome to Echo-Sync. This is your first time, so let me set you up. "
            "You will not need a screen — I will guide you by voice."
        )

        # Start with a sound so the user can confirm audio output works.
        self._play_test_tone()
        self._respond(
            "You just heard a short sound. If you heard it, your audio is working. "
            "I use short sounds like that to confirm your actions."
        )

        # Configuration problems must be spoken, not only printed.
        self._announce_config_state()

        # Introduce only the commands needed to get started.
        self._respond(
            "Here is how to talk to me. To control music directly, say: "
            "play, pause, next song, or volume up. "
            "To pick music by how you feel, just tell me, for example: "
            "I am tired, or, I need energy, and I will choose for you. "
            "To hear what is playing, ask: what song is this. "
            "If you ever feel lost, say: help. To stop me, say: stop, or cancel."
        )

        self._await_ready()

        self._mark_complete()
        self._respond("Great, setup is complete. You can start whenever you like.")

    # Setup steps

    def _play_test_tone(self) -> None:
        try:
            self.earcons.play_success()
        except Exception as e:  # pragma: no cover - best effort
            logger.debug("Could not play onboarding test tone: %s", e)

    def _announce_config_state(self) -> None:
        """Tell the user, out loud, whether advanced AI features are available."""
        key = (self.settings.openai_api_key or "").strip()
        if not key or key == "your_api_key_here":
            self._respond(
                "One note: advanced understanding of free speech is not set up yet, "
                "so I will use my built-in voice commands. "
                "You can still play music, change volume, and tell me how you feel."
            )
        else:
            self._respond("Your assistant is fully set up and ready.")

    def _await_ready(self) -> None:
        """Block until the user indicates they are ready to begin."""
        # Keyboard demos use Enter instead of waiting for microphone input.
        if self.demo_keyboard or self.recorder is None or self.stt is None:
            try:
                self.console.input(
                    "[bold green]Press Enter when you are ready to start…[/bold green] "
                )
            except (EOFError, KeyboardInterrupt):
                pass
            return

        # Listen once only, so setup cannot get stuck waiting for a response.
        self._respond("When you are ready, say: ready.")
        try:
            self.earcons.play_listening()
            audio_path = self.recorder.record()
            if audio_path is not None:
                heard = (self.stt.transcribe(audio_path) or "").strip()
                try:
                    audio_path.unlink(missing_ok=True)
                except Exception:
                    pass
                if heard:
                    self.console.print(f"[dim]Heard: {heard}[/dim]")
                    if not any(w in heard.lower() for w in _READY_WORDS):
                        # Any response is enough to continue the tutorial.
                        logger.info("Onboarding: proceeding after user spoke ('%s')", heard)
        except Exception as e:  # pragma: no cover - best effort
            logger.debug("Onboarding listen skipped: %s", e)

    def _mark_complete(self) -> None:
        try:
            SETUP_MARKER.write_text("Echo-Sync onboarding completed.\n", encoding="utf-8")
            logger.info("Onboarding marked complete: %s", SETUP_MARKER)
        except Exception as e:  # pragma: no cover - best effort
            logger.warning("Could not write onboarding marker: %s", e)
