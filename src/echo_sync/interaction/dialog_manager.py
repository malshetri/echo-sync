"""
Echo-Sync dialog manager.

Routes classified intents to the correct handlers and manages
the overall conversation flow. Coordinates between the AI classifier,
media player, guided help, and earcon manager.
"""

import logging
from typing import Optional

from echo_sync.ai.context_mapper import ContextMapper
from echo_sync.ai.intent_schema import IntentResult
from echo_sync.ai.safety_filter import SafetyFilter
from echo_sync.audio.ducking import SmartDucker
from echo_sync.audio.earcons import (
    EARCON_ERROR,
    EARCON_HELP,
    EARCON_MOOD_DETECTED,
    EARCON_SUCCESS,
    EarconManager,
)
from echo_sync.config.settings import Settings
from echo_sync.interaction.guided_help import GuidedHelp
from echo_sync.interaction.response_templates import (
    RESPONSE_NO_MUSIC,
    RESPONSE_PLAYLIST_LOADED,
    get_context_response,
    get_volume_response,
)
from echo_sync.media.player_base import PlayerBase
from echo_sync.media.playlist_manager import PlaylistManager

logger = logging.getLogger(__name__)


class DialogManager:
    """
    Central dialog manager for Echo-Sync.

    Routes intents to the correct handler and coordinates
    all system components to execute user requests.
    """

    def __init__(
        self,
        settings: Settings,
        player: PlayerBase,
        playlist_manager: PlaylistManager,
        context_mapper: ContextMapper,
        earcon_manager: EarconManager,
        ducker: SmartDucker,
    ) -> None:
        self.settings = settings
        self.player = player
        self.playlist_manager = playlist_manager
        self.context_mapper = context_mapper
        self.earcons = earcon_manager
        self.ducker = ducker
        self.guided_help = GuidedHelp()
        self.safety_filter = SafetyFilter(settings)

    def handle_intent(self, intent: IntentResult) -> str:
        """
        Route an intent result to the appropriate handler.

        Args:
            intent: The classified IntentResult.

        Returns:
            Response text to speak back to the user.
        """
        # Apply safety filter
        intent = self.safety_filter.validate(intent)

        # Route by intent type
        handlers = {
            "direct_command": self._handle_direct_command,
            "context_request": self._handle_context_request,
            "help_request": self._handle_help_request,
            "unclear": self._handle_unclear,
            "off_topic": self._handle_off_topic,
        }

        handler = handlers.get(intent.intent_type)
        if handler is None:
            logger.error("Unknown intent type: %s", intent.intent_type)
            return self.guided_help.handle_unclear()

        response = handler(intent)

        # Reset help counters on successful non-help interactions
        if intent.intent_type in ("direct_command", "context_request"):
            self.guided_help.reset_counters()

        return response

    def handle_silence(self) -> str:
        """Handle silence timeout."""
        self.earcons.play(EARCON_HELP)
        return self.guided_help.handle_silence()

    def handle_stt_failure(self) -> str:
        """Handle speech-to-text transcription failure."""
        self.earcons.play(EARCON_ERROR)
        return self.guided_help.handle_stt_failure()

    # ── Private handlers ────────────────────────────────────────────────────

    def _handle_direct_command(self, intent: IntentResult) -> str:
        """Handle direct media control commands."""
        action = intent.action
        response = intent.user_feedback

        try:
            if action == "play":
                if not self.player.is_playing():
                    # Try to play from current playlist or load fallback
                    if not self.player.play():
                        # Load fallback playlist
                        tracks = self.playlist_manager.get_playlist("fallback")
                        if tracks:
                            self.player.load_playlist(tracks)
                            self.player.play(tracks[0])
                self.earcons.play(EARCON_SUCCESS)

            elif action == "pause":
                self.player.pause()
                self.earcons.play(EARCON_SUCCESS)

            elif action == "resume":
                self.player.resume()
                self.earcons.play(EARCON_SUCCESS)

            elif action == "stop":
                self.player.stop()
                self.earcons.play(EARCON_SUCCESS)

            elif action == "next":
                self.player.next_track()
                self.earcons.play(EARCON_SUCCESS)

            elif action == "previous":
                self.player.previous_track()
                self.earcons.play(EARCON_SUCCESS)

            elif action == "volume_up":
                new_vol = self._adjust_volume(delta=10)
                response = get_volume_response("volume_up", new_vol)
                self.earcons.play(EARCON_SUCCESS)

            elif action == "volume_down":
                new_vol = self._adjust_volume(delta=-10)
                response = get_volume_response("volume_down", new_vol)
                self.earcons.play(EARCON_SUCCESS)

            elif action == "set_volume":
                target = intent.volume_level
                if target is None:
                    response = "I didn't catch what level you wanted. Try: set volume to 70 percent."
                else:
                    new_vol = self._adjust_volume(absolute=target)
                    response = get_volume_response("set_volume", new_vol)
                    self.earcons.play(EARCON_SUCCESS)

            elif action == "identify":
                response = self._describe_current_track()
                self.earcons.play(EARCON_SUCCESS)

            else:
                logger.warning("Unknown direct command action: %s", action)
                response = intent.user_feedback

        except Exception as e:
            logger.error("Error executing command '%s': %s", action, e)
            self.earcons.play(EARCON_ERROR)
            response = "I had trouble with that command. Please try again."

        return response

    def _adjust_volume(
        self,
        delta: Optional[int] = None,
        absolute: Optional[int] = None,
    ) -> int:
        """
        Compute and apply a new volume, relative to (or ducking) correctly.

        Relative changes (delta) and absolute targets are both based on the
        "effective" volume — the pre-duck target if Smart Ducking is
        currently active, since the player's live volume is temporarily
        lowered for speech clarity and must not be used as the baseline.

        While ducked, only the ducking target is updated (the audible
        change lands smoothly when it un-ducks); otherwise the player
        volume is changed immediately.
        """
        base = self.ducker.get_effective_volume()
        new_vol = base + delta if delta is not None else absolute
        new_vol = max(0, min(100, new_vol))

        if self.ducker.is_ducked:
            self.ducker.update_target_volume(new_vol)
        else:
            self.player.set_volume(new_vol)
            self.ducker.update_target_volume(new_vol)

        return new_vol

    def _describe_current_track(self) -> str:
        """Build a spoken response announcing the currently playing track (FR-07)."""
        track = ""
        if hasattr(self.player, "get_current_track"):
            track = (self.player.get_current_track() or "").strip()

        # Turn a file stem like "soft_piano_01" into "soft piano 01"
        pretty = track.replace("_", " ").replace("-", " ").strip()

        is_playing = bool(
            hasattr(self.player, "is_playing") and self.player.is_playing()
        )

        if pretty and is_playing:
            return f"This is {pretty}."
        if pretty:
            return f"The last track was {pretty}. Nothing is playing right now."
        return "Nothing is playing right now. You can say: play something calm."

    def _handle_context_request(self, intent: IntentResult) -> str:
        """Handle context/mood-based music requests."""
        context = intent.interpreted_context
        self.earcons.play(EARCON_MOOD_DETECTED)

        # Get playlist path for this context
        playlist_path = self.context_mapper.get_playlist_path(context)
        tracks = self.playlist_manager.get_playlist(playlist_path.name)

        if not tracks:
            logger.warning("No tracks for context '%s'", context)
            return RESPONSE_NO_MUSIC

        # Load and play the playlist
        self.player.load_playlist(tracks)
        self.player.play(tracks[0])

        response = get_context_response(context)
        logger.info(
            "Context request: %s → %d tracks loaded",
            context,
            len(tracks),
        )
        return response

    def _handle_help_request(self, intent: IntentResult) -> str:
        """Handle help requests."""
        self.earcons.play(EARCON_HELP)
        return self.guided_help.handle_help_request()

    def _handle_unclear(self, intent: IntentResult) -> str:
        """Handle unclear/ambiguous input."""
        self.earcons.play(EARCON_HELP)
        return self.guided_help.handle_unclear(intent.user_feedback)

    def _handle_off_topic(self, intent: IntentResult) -> str:
        """Handle off-topic requests."""
        self.earcons.play(EARCON_ERROR)
        return self.guided_help.handle_off_topic()
