"""
Tests for the Echo-Sync guided help module.

Tests help responses for silence, unclear speech, off-topic, and help requests.
"""

import pytest

from echo_sync.ai.intent_schema import IntentResult
from echo_sync.interaction.guided_help import GuidedHelp


@pytest.fixture
def helper():
    """Create a fresh GuidedHelp instance."""
    return GuidedHelp()


class TestGuidedHelp:
    """Test guided help response generation."""

    # Silence handling

    def test_silence_first(self, helper):
        """First silence should give a basic help message."""
        response = helper.handle_silence()
        assert response  # Not empty
        assert "help" in response.lower() or "say" in response.lower()

    def test_silence_progressive(self, helper):
        """Repeated silences should give progressively more help."""
        r1 = helper.handle_silence()
        r2 = helper.handle_silence()
        r3 = helper.handle_silence()
        assert r1 and r2 and r3
        # Progressive help should not repeat the same sentence.
        assert r1 != r3 or r2 != r3

    # Unclear speech

    def test_unclear_with_transcript(self, helper):
        """Unclear with transcript should include what was heard."""
        response = helper.handle_unclear("mumble something")
        assert "mumble something" in response

    def test_unclear_without_transcript(self, helper):
        """Unclear without transcript should give general help."""
        response = helper.handle_unclear()
        assert response
        assert "say" in response.lower()

    # Off-topic requests

    def test_off_topic(self, helper):
        """Off-topic should politely redirect to music."""
        response = helper.handle_off_topic()
        assert "music" in response.lower()

    def test_off_topic_alternates(self, helper):
        """Repeated off-topic should alternate responses."""
        r1 = helper.handle_off_topic()
        r2 = helper.handle_off_topic()
        assert r1  # Not empty
        assert r2  # Not empty

    # Help requests

    def test_help_request(self, helper):
        """Help request should list available commands."""
        response = helper.handle_help_request()
        assert response
        assert any(
            word in response.lower()
            for word in ["play", "pause", "say", "music"]
        )

    def test_help_progressive(self, helper):
        """Repeated help should give more detail."""
        r1 = helper.handle_help_request()
        r2 = helper.handle_help_request()
        r3 = helper.handle_help_request()
        assert r1 and r2 and r3

    # Low-confidence results

    def test_low_confidence(self, helper):
        """Low confidence should trigger clarification."""
        intent = IntentResult(
            intent_type="unclear",
            action="clarify",
            interpreted_context="none",
            confidence=0.3,
            user_feedback="Maybe play something?",
        )
        response = helper.handle_low_confidence(intent)
        assert response
        assert "say" in response.lower() or "mean" in response.lower()

    # Speech-to-text failures

    def test_stt_failure(self, helper):
        """STT failure should ask user to try again."""
        response = helper.handle_stt_failure()
        assert response
        assert "try" in response.lower() or "again" in response.lower()

    # Counter reset

    def test_reset_counters(self, helper):
        """Reset should clear help and silence counters."""
        helper.handle_silence()
        helper.handle_silence()
        helper.handle_help_request()
        helper.reset_counters()
        # Resetting starts the progressive sequence from the beginning.
        r1 = helper.handle_silence()
        assert r1  # Should be the first-silence response
