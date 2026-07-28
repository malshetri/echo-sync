"""
Echo-Sync safety filter.

Validates AI output and ensures safe, accessible behavior.
Catches edge cases the AI might miss: off-topic leaks,
dangerously low confidence, or malformed responses.
"""

import logging

from echo_sync.ai.intent_schema import IntentResult
from echo_sync.config.settings import Settings

logger = logging.getLogger(__name__)


class SafetyFilter:
    """
    Post-processing safety filter for AI intent classification results.

    Validates that:
    - Off-topic requests are properly rejected
    - Low-confidence results trigger clarification
    - Responses are appropriate for blind/motor-impaired users
    """

    def __init__(self, settings: Settings) -> None:
        self.confidence_threshold = settings.confidence_threshold

    def validate(self, result: IntentResult) -> IntentResult:
        """
        Validate and potentially override an intent classification result.

        Args:
            result: The raw IntentResult from the classifier.

        Returns:
            A validated (possibly modified) IntentResult.
        """
        # Ask for clarification instead of guessing on weak results.
        if result.is_low_confidence(self.confidence_threshold):
            logger.info(
                "Low confidence (%.2f) — triggering clarification",
                result.confidence,
            )
            return IntentResult(
                intent_type="unclear",
                action="clarify",
                interpreted_context="none",
                confidence=result.confidence,
                user_feedback=(
                    "I'm not quite sure what you mean. "
                    "You can say: play, pause, next song, or tell me how you feel."
                ),
            )

        # Off-topic requests must always use the reject action.
        if result.intent_type == "off_topic" and result.action != "reject":
            logger.warning("Off-topic intent without reject action — fixing")
            result.action = "reject"

        if not result.user_feedback or not result.user_feedback.strip():
            result.user_feedback = "Done."

        # Direct controls do not need a mood or context category.
        if result.intent_type == "direct_command" and result.interpreted_context == "unknown":
            result.interpreted_context = "none"

        return result

    def is_safe_response(self, feedback: str) -> bool:
        """
        Check if a feedback message is safe and appropriate.

        Ensures the system doesn't claim emotion detection
        or make medical/psychological claims.
        """
        unsafe_phrases = [
            "i detect your emotion",
            "you are feeling",
            "i can tell you're",
            "emotional state",
            "psychological",
            "diagnosis",
            "mental health",
        ]
        feedback_lower = feedback.lower()
        for phrase in unsafe_phrases:
            if phrase in feedback_lower:
                logger.warning(
                    "Unsafe phrase detected in feedback: '%s'",
                    phrase,
                )
                return False
        return True
