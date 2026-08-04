"""
Echo-Sync intent schema.

Defines the strict output format for the AI intent classifier
using Pydantic models for type-safe, validated results.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class IntentResult(BaseModel):
    """
    Structured result from the AI intent classifier.

    This schema is used both as the expected JSON output format from the AI
    and as the internal data structure for routing user requests.
    """

    intent_type: Literal[
        "direct_command",
        "context_request",
        "help_request",
        "unclear",
        "off_topic",
    ] = Field(
        description="The classified type of user intent."
    )

    action: Literal[
        "play",
        "pause",
        "resume",
        "stop",
        "next",
        "previous",
        "volume_up",
        "volume_down",
        "set_volume",
        "select_playlist",
        "identify",
        "help",
        "reject",
        "clarify",
    ] = Field(
        description="The specific action to execute."
    )

    interpreted_context: Literal[
        "calm",
        "energy",
        "focus",
        "happy",
        "sad",
        "unknown",
        "none",
    ] = Field(
        default="none",
        description=(
            "The interpreted context/mood from user wording. "
            "Uses 'interpreted context' — not 'detected emotion.'"
        ),
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="AI confidence score between 0.0 and 1.0.",
    )

    volume_level: Optional[int] = Field(
        default=None,
        ge=0,
        le=100,
        description=(
            "Explicit target volume percentage (0-100), only set when "
            "action is 'set_volume' and the user named a specific level."
        ),
    )

    user_feedback: str = Field(
        description="Short, accessible response to speak back to the user.",
    )

    def is_low_confidence(self, threshold: float = 0.6) -> bool:
        """Check if the confidence is below the given threshold."""
        return self.confidence < threshold

    def needs_playlist(self) -> bool:
        """Check if this intent requires selecting a playlist."""
        return self.action == "select_playlist"

    def is_music_command(self) -> bool:
        """Check if this is a direct media control command."""
        return self.intent_type == "direct_command"


# ── JSON schema for AI prompt injection ─────────────────────────────────────
INTENT_RESULT_JSON_SCHEMA = IntentResult.model_json_schema()
