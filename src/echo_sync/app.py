"""
Echo-Sync main application loop.

Orchestrates the complete interaction cycle:
earcon → record → transcribe → classify → execute → log → repeat.

Supports two modes:
- Voice mode: uses microphone for speech input
- Keyboard demo mode: uses typed input (--demo-keyboard flag)
"""

import logging
import sys
import time

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from echo_sync.ai.context_mapper import ContextMapper
from echo_sync.ai.intent_classifier import IntentClassifier
from echo_sync.audio.ducking import SmartDucker
from echo_sync.audio.earcons import EarconManager
from echo_sync.audio.recorder import MicrophoneRecorder
from echo_sync.audio.tts import TTSService
from echo_sync.config.prompts import WELCOME_MESSAGE, GOODBYE_MESSAGE
from echo_sync.config.settings import Settings
from echo_sync.interaction.dialog_manager import DialogManager
from echo_sync.interaction.onboarding import OnboardingWizard
from echo_sync.interaction.state_machine import AppState, StateMachine
from echo_sync.logging_utils.interaction_logger import InteractionLogger
from echo_sync.media.playlist_manager import PlaylistManager
from echo_sync.media.player_base import PlayerBase
from echo_sync.speech.stt_base import STTBase

logger = logging.getLogger(__name__)
console = Console()

import re

def parse_wake_word(transcript: str, wake_word: str) -> tuple[bool, str]:
    if not wake_word:
        return True, transcript.strip()

    valid_wake_words = [wake_word.lower()]
    if wake_word.lower() == "echo":
        valid_wake_words.extend(["eko", "ecco", "eco", "ekko", "acou", "ico", "iko"])

    transcript_lower = transcript.lower()
    woken = False
    for w in valid_wake_words:
        if w in transcript_lower:
            woken = True
            break
            
    if not woken:
        return False, transcript
        
    cleaned_transcript = transcript
    for w in valid_wake_words:
        pattern = re.compile(r'\b' + re.escape(w) + r'\b', re.IGNORECASE)
        cleaned_transcript = pattern.sub("", cleaned_transcript)
        
    cleaned_transcript = re.sub(r'^(hi|hey|hello)\s*', '', cleaned_transcript.strip(), flags=re.IGNORECASE)
    cleaned_transcript = cleaned_transcript.strip(" .,!?")
    
    return True, cleaned_transcript.strip()


class EchoSyncApp:
    """
    Main Echo-Sync application.

    Manages the interaction loop and coordinates all components.
    """

    def __init__(
        self,
        settings: Settings,
        demo_keyboard: bool = False,
        force_setup: bool = False,
        skip_setup: bool = False,
    ) -> None:
        self.settings = settings
        self.demo_keyboard = demo_keyboard
        self.force_setup = force_setup
        self.skip_setup = skip_setup
        self.state_machine = StateMachine()
        self.running = False
        # Keyboard mode accepts commands immediately, without a wake word.
        self.active_session = demo_keyboard

        # Set up the services used by the interaction loop.
        console.print("[dim]Initializing Echo-Sync...[/dim]")

        # Media player
        self.player = self._create_player(settings)
        self.playlist_manager = PlaylistManager(settings.music_path)

        # Audio
        self.earcons = EarconManager(settings)
        self.ducker = SmartDucker(
            ducking_volume=settings.ducking_volume,
        )
        self.ducker.attach_player(self.player)

        if not demo_keyboard:
            self.recorder = MicrophoneRecorder(
                no_speech_timeout=settings.silence_timeout,
            )
        else:
            self.recorder = None

        # Speech-to-text
        self.stt = self._create_stt(settings)

        # AI
        self.classifier = IntentClassifier(settings)
        self.context_mapper = ContextMapper(settings)

        # Interaction
        self.dialog_manager = DialogManager(
            settings=settings,
            player=self.player,
            playlist_manager=self.playlist_manager,
            context_mapper=self.context_mapper,
            earcon_manager=self.earcons,
            ducker=self.ducker,
        )

        # Logging
        self.interaction_logger = InteractionLogger(settings)

        # TTS is optional; terminal output still works if it is unavailable.
        self.tts = TTSService()
        if self.tts.is_available:
            console.print(f"[dim]TTS backend: {self.tts.backend_name}[/dim]")

        # First-run setup is spoken so it does not depend on a display.
        self.onboarding = OnboardingWizard(
            settings=settings,
            respond=self._respond,
            earcons=self.earcons,
            console=console,
            recorder=self.recorder,
            stt=self.stt,
            demo_keyboard=demo_keyboard,
        )

        console.print("[green]✓ Echo-Sync initialized[/green]")

    @staticmethod
    def _create_player(settings: Settings) -> PlayerBase:
        """Create the appropriate media player based on settings."""
        if settings.player == "vlc":
            try:
                from echo_sync.media.vlc_player import VLCPlayer
                return VLCPlayer(default_volume=settings.default_volume)
            except Exception as e:
                logger.warning("VLC player failed, trying pygame: %s", e)

        from echo_sync.media.pygame_player import PygamePlayer
        return PygamePlayer(default_volume=settings.default_volume)

    @staticmethod
    def _create_stt(settings: Settings) -> STTBase:
        """Create the appropriate STT provider based on settings."""
        if settings.stt_mode == "openai":
            from echo_sync.speech.openai_stt import OpenAISTT
            stt = OpenAISTT(settings)
            if stt.is_available():
                return stt
            logger.warning("OpenAI STT not available, trying offline")

        from echo_sync.speech.offline_stt import OfflineSTT
        return OfflineSTT()

    def run(self) -> None:
        """Start the main interaction loop."""
        self.running = True
        self.interaction_logger.log_system_event("System started")

        # The full tutorial runs once; later starts use the short welcome.
        if self.onboarding.should_run(force=self.force_setup, skip=self.skip_setup):
            self.interaction_logger.log_system_event("First-run onboarding started")
            self.onboarding.run()
        else:
            console.print()
            console.print(
                Panel(
                    Text(WELCOME_MESSAGE, style="bold cyan"),
                    title="🎵 Echo-Sync",
                    border_style="cyan",
                )
            )
            console.print()
            self.tts.speak(WELCOME_MESSAGE)

        try:
            while self.running:
                self._interaction_cycle()
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted by user[/yellow]")
        finally:
            self._shutdown()
    def _interaction_cycle(self) -> None:
        """Execute one full interaction cycle."""
        current_state = self.state_machine.state
        
        # Let the user know when the assistant is ready for a command.
        if self.state_machine.is_awake():
            self.earcons.play_listening()

        # Read either typed input or microphone audio.
        if self.demo_keyboard:
            transcript = self._get_keyboard_input()
        else:
            transcript = self._get_voice_input(play_earcon=False)

        if transcript is None:
            self.running = False
            return

        # Voice mode ignores background speech until the wake word is heard.
        wake_word = self.settings.wake_word
        if self.demo_keyboard:
            is_woken = True
            clean_transcript = transcript.strip()
        else:
            is_woken, clean_transcript = parse_wake_word(transcript, wake_word)

        if self.state_machine.is_passive():
            if not is_woken:
                if transcript.strip():
                    logger.info("Ignored background speech (wake word not detected): '%s'", transcript)
                return
            
            if not clean_transcript:
                self._respond("I am listening.")
                self.state_machine.wake()
                return
            else:
                self.state_machine.wake()
                command_to_process = clean_transcript
        else:
            command_to_process = clean_transcript if is_woken else transcript

        cancel_words = ["cancel", "sleep", "stop listening", "never mind", "nevermind"]
        if command_to_process.lower().strip() in cancel_words:
            self._respond("Okay, I will wait.")
            self.state_machine.sleep()
            return

        if not command_to_process.strip():
            response = self.dialog_manager.handle_silence()
            self._respond(response)
            self.state_machine.start_clarifying()
            return

        # Classify the request and carry out the matching action.
        self.ducker.duck()
        console.print(f"[dim]You said: \"{command_to_process}\"[/dim]")

        try:
            intent = self.classifier.classify(command_to_process)

            response = self.dialog_manager.handle_intent(intent)
            self._respond(response)

        finally:
            self.ducker.unduck()

        self.interaction_logger.log_interaction(
            transcript=command_to_process,
            intent_result=intent,
            system_response=response,
        )

        # Return to the state that matches the result and player status.
        if intent.intent_type in ["unclear", "off_topic", "help_request"]:
            self.state_machine.start_clarifying()
        else:
            if intent.action in ["play", "resume", "select_playlist", "next", "previous"]:
                self.state_machine.start_playing_passive()
            elif intent.action in ["pause", "stop"]:
                self.state_machine.wake()
            else:
                if hasattr(self.player, "is_playing") and self.player.is_playing():
                    self.state_machine.start_playing_passive()
                else:
                    self.state_machine.wake()

    def _get_keyboard_input(self) -> str | None:
        """Get input from keyboard (demo mode)."""
        try:
            console.print()
            user_input = console.input(
                "[bold green]🎤 You:[/bold green] "
            ).strip()

            if user_input.lower() in ("quit", "exit", "q"):
                return None

            return user_input

        except EOFError:
            return None

    def _get_voice_input(self, play_earcon: bool = False) -> str | None:
        """Get input from microphone."""
        if self.recorder is None:
            return self._get_keyboard_input()

        if play_earcon:
            self.earcons.play_listening()
            
        console.print("[dim]🎤 Listening...[/dim]")

        audio_path = self.recorder.record()
        if audio_path is None:
            return ""

        transcript = self.stt.transcribe(audio_path)

        # Recordings are temporary and may contain private speech.
        try:
            audio_path.unlink(missing_ok=True)
        except Exception:
            pass

        return transcript

    def _respond(self, text: str) -> None:
        """Output the system response (print + TTS)."""
        console.print(
            Panel(
                Text(text, style="bold white"),
                title="🔊 Echo-Sync",
                border_style="blue",
            )
        )
        self.tts.speak(text)

    def _shutdown(self) -> None:
        """Clean shutdown of all components."""
        self.state_machine.force_state(AppState.SHUTTING_DOWN)
        self.running = False

        console.print()
        console.print(f"[cyan]{GOODBYE_MESSAGE}[/cyan]")

        if hasattr(self.player, "cleanup"):
            self.player.cleanup()

        self.tts.cleanup()

        self.interaction_logger.log_system_event("System shutdown")
        logger.info("Echo-Sync shut down cleanly")
