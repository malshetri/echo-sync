"""
Echo-Sync guided help module.

Handles inclusive support for various user situations:
- Silence (no speech for 10+ seconds)
- Speech not understood
- Off-topic questions
- New user asking "what can I say?"
- Low AI confidence results
"""

import logging
from typing import Optional

from echo_sync.ai.intent_schema import IntentResult
from echo_sync.interaction.response_templates import (
    RESPONSE_HELP_COMMANDS,
    RESPONSE_HELP_GENERAL,
    RESPONSE_HELP_MOODS,
    RESPONSE_LOW_CONFIDENCE,
    RESPONSE_OFF_TOPIC,
    RESPONSE_OFF_TOPIC_GENTLE,
    RESPONSE_SILENCE,
    RESPONSE_STT_FAILED,
    RESPONSE_UNCLEAR,
)

logger = logging.getLogger(__name__)


class GuidedHelp:
    """
    Provides guided help and error handling for Echo-Sync.

    Generates appropriate responses based on the type of
    user difficulty or system state.
    """

    def __init__(self) -> None:
        self._help_count = 0  # Track how many times help was requested
        self._silence_count = 0  # Track consecutive silences

    def handle_silence(self) -> str:
        """
        Handle silence timeout (no speech detected).

        Returns progressively more helpful messages.
        """
        self._silence_count += 1

        if self._silence_count == 1:
            response = RESPONSE_SILENCE
        elif self._silence_count == 2:
            response = (
                "I'm still listening. You can say things like: "
                "play jazz, I'm tired, or help."
            )
        else:
            response = (
                "Take your time. When you're ready, just say something like: "
                "play something calm. Or say 'stop' to end."
            )

        logger.info("Silence handled (count: %d)", self._silence_count)
        return response

    def handle_unclear(self, transcript: Optional[str] = None) -> str:
        """
        Handle unclear or unrecognized speech.

        Args:
            transcript: The transcript that couldn't be classified.
        """
        self._silence_count = 0  # Reset silence counter

        if transcript:
            response = (
                f"I heard '{transcript}' but I'm not sure what you mean. "
                "You can say: play, pause, next song, or tell me how you feel."
            )
        else:
            response = RESPONSE_UNCLEAR

        logger.info("Unclear speech handled: '%s'", transcript or "empty")
        return response

    def handle_off_topic(self) -> str:
        """Handle off-topic requests."""
        self._silence_count = 0

        # Vary repeated replies so they do not sound mechanical.
        if self._help_count % 2 == 0:
            response = RESPONSE_OFF_TOPIC
        else:
            response = RESPONSE_OFF_TOPIC_GENTLE

        self._help_count += 1
        logger.info("Off-topic request handled")
        return response

    def handle_help_request(self) -> str:
        """
        Handle explicit help requests.

        Returns progressively more detailed help.
        """
        self._silence_count = 0
        self._help_count += 1

        if self._help_count <= 1:
            response = RESPONSE_HELP_GENERAL
        elif self._help_count == 2:
            response = RESPONSE_HELP_COMMANDS
        else:
            response = RESPONSE_HELP_MOODS

        logger.info("Help request handled (count: %d)", self._help_count)
        return response

    def handle_low_confidence(self, result: IntentResult) -> str:
        """
        Handle low-confidence AI classification results.

        Args:
            result: The low-confidence IntentResult.
        """
        self._silence_count = 0
        response = RESPONSE_LOW_CONFIDENCE
        logger.info(
            "Low confidence handled (%.2f for '%s')",
            result.confidence,
            result.intent_type,
        )
        return response

    def handle_stt_failure(self) -> str:
        """Handle speech-to-text transcription failure."""
        self._silence_count = 0
        return RESPONSE_STT_FAILED

    def reset_counters(self) -> None:
        """Reset help and silence counters (e.g., after successful interaction)."""
        self._silence_count = 0
        self._help_count = 0
