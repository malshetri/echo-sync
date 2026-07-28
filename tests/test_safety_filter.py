"""
Tests for the Echo-Sync safety filter.

Tests validation of AI output, confidence thresholds,
off-topic handling, and unsafe phrase detection.
"""

import pytest
from unittest.mock import MagicMock

from echo_sync.ai.intent_schema import IntentResult
from echo_sync.ai.safety_filter import SafetyFilter


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock()
    settings.confidence_threshold = 0.6
    return settings


@pytest.fixture
def safety_filter(mock_settings):
    """Create a SafetyFilter with mock settings."""
    return SafetyFilter(mock_settings)


class TestSafetyFilter:
    """Test the safety filter validation."""

    # Low confidence

    def test_low_confidence_triggers_clarification(self, safety_filter):
        """Low confidence should be overridden to 'unclear/clarify'."""
        intent = IntentResult(
            intent_type="direct_command",
            action="play",
            interpreted_context="none",
            confidence=0.3,
            user_feedback="Playing something.",
        )
        result = safety_filter.validate(intent)
        assert result.intent_type == "unclear"
        assert result.action == "clarify"

    def test_high_confidence_passes_through(self, safety_filter):
        """High confidence should pass through unchanged."""
        intent = IntentResult(
            intent_type="direct_command",
            action="play",
            interpreted_context="none",
            confidence=0.95,
            user_feedback="Playing music.",
        )
        result = safety_filter.validate(intent)
        assert result.intent_type == "direct_command"
        assert result.action == "play"

    def test_threshold_boundary(self, safety_filter):
        """Exactly at threshold should pass through."""
        intent = IntentResult(
            intent_type="direct_command",
            action="play",
            interpreted_context="none",
            confidence=0.6,
            user_feedback="Playing music.",
        )
        result = safety_filter.validate(intent)
        assert result.intent_type == "direct_command"

    # Off-topic normalization

    def test_off_topic_without_reject_is_fixed(self, safety_filter):
        """Off-topic with wrong action should be fixed to 'reject'."""
        intent = IntentResult(
            intent_type="off_topic",
            action="play",  # Wrong action for off-topic
            interpreted_context="none",
            confidence=0.9,
            user_feedback="The weather is...",
        )
        result = safety_filter.validate(intent)
        assert result.action == "reject"

    def test_off_topic_with_reject_passes(self, safety_filter):
        """Off-topic with correct 'reject' action should pass."""
        intent = IntentResult(
            intent_type="off_topic",
            action="reject",
            interpreted_context="none",
            confidence=0.9,
            user_feedback="I can only help with music.",
        )
        result = safety_filter.validate(intent)
        assert result.action == "reject"
        assert result.intent_type == "off_topic"

    # Empty feedback

    def test_empty_feedback_is_fixed(self, safety_filter):
        """Empty user_feedback should be filled with default."""
        intent = IntentResult(
            intent_type="direct_command",
            action="pause",
            interpreted_context="none",
            confidence=0.95,
            user_feedback="",
        )
        result = safety_filter.validate(intent)
        assert result.user_feedback  # Should not be empty

    # Unsafe phrase detection

    def test_safe_response(self, safety_filter):
        """Normal response should be safe."""
        assert safety_filter.is_safe_response("Playing calm music for you.")

    def test_unsafe_emotion_detection(self, safety_filter):
        """Claiming emotion detection should be flagged."""
        assert not safety_filter.is_safe_response(
            "I detect your emotion as sad."
        )

    def test_unsafe_feeling_claim(self, safety_filter):
        """Claiming to know feelings should be flagged."""
        assert not safety_filter.is_safe_response(
            "You are feeling stressed right now."
        )

    def test_unsafe_psychological(self, safety_filter):
        """Psychological claims should be flagged."""
        assert not safety_filter.is_safe_response(
            "Based on psychological analysis..."
        )

    def test_interpreted_context_fixed_for_direct(self, safety_filter):
        """Direct commands should not have 'unknown' context."""
        intent = IntentResult(
            intent_type="direct_command",
            action="play",
            interpreted_context="unknown",
            confidence=0.9,
            user_feedback="Playing music.",
        )
        result = safety_filter.validate(intent)
        assert result.interpreted_context == "none"
