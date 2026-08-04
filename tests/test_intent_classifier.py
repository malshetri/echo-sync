"""
Tests for the Echo-Sync AI intent classifier.

Covers all 20 test cases from the implementation guide,
testing both rule-based fast-path and AI classification.
"""

import pytest

from echo_sync.ai.intent_classifier import try_rule_based
from echo_sync.ai.intent_schema import IntentResult


class TestRuleBasedClassifier:
    """Test the rule-based fast-path classifier."""

    # ── T01: Play jazz ──────────────────────────────────────────────
    def test_play_jazz(self):
        result = try_rule_based("play jazz")
        assert result is not None
        assert result.intent_type == "direct_command"
        assert result.action == "play"
        assert result.confidence >= 0.9
        assert "jazz" in result.user_feedback.lower()

    # ── T02: Pause ──────────────────────────────────────────────────
    def test_pause(self):
        result = try_rule_based("pause")
        assert result is not None
        assert result.intent_type == "direct_command"
        assert result.action == "pause"
        assert result.confidence >= 0.9

    # ── T03: Continue / Resume ──────────────────────────────────────
    def test_resume(self):
        for word in ["resume", "continue", "unpause"]:
            result = try_rule_based(word)
            assert result is not None, f"Failed for '{word}'"
            assert result.intent_type == "direct_command"
            assert result.action == "resume"

    # ── T04: Next song ──────────────────────────────────────────────
    def test_next_song(self):
        for phrase in ["next", "next song"]:
            result = try_rule_based(phrase)
            assert result is not None, f"Failed for '{phrase}'"
            assert result.intent_type == "direct_command"
            assert result.action == "next"

    # ── T05: Previous song ──────────────────────────────────────────
    def test_previous_song(self):
        for phrase in ["previous", "previous song", "prev", "prev song"]:
            result = try_rule_based(phrase)
            assert result is not None, f"Failed for '{phrase}'"
            assert result.intent_type == "direct_command"
            assert result.action == "previous"

    # ── T06: Volume up ──────────────────────────────────────────────
    def test_volume_up(self):
        for phrase in ["volume up", "louder", "turn it up", "make it louder"]:
            result = try_rule_based(phrase)
            assert result is not None, f"Failed for '{phrase}'"
            assert result.intent_type == "direct_command"
            assert result.action == "volume_up"

    # ── T07: Volume down ────────────────────────────────────────────
    def test_volume_down(self):
        for phrase in ["volume down", "quieter", "turn it down", "lower the volume"]:
            result = try_rule_based(phrase)
            assert result is not None, f"Failed for '{phrase}'"
            assert result.intent_type == "direct_command"
            assert result.action == "volume_down"

    # ── Explicit volume level ("set volume to 70 percent") ──────────
    def test_set_volume_explicit_level(self):
        cases = [
            ("set volume to 70", 70),
            ("set the volume to 70 percent", 70),
            ("volume to 45%", 45),
            ("volume 100", 100),
            ("volume 0", 0),
        ]
        for phrase, expected_level in cases:
            result = try_rule_based(phrase)
            assert result is not None, f"Failed for '{phrase}'"
            assert result.intent_type == "direct_command"
            assert result.action == "set_volume"
            assert result.volume_level == expected_level

    def test_set_volume_clamps_above_100(self):
        result = try_rule_based("set volume to 150")
        assert result is not None
        assert result.action == "set_volume"
        assert result.volume_level == 100

    # ── T13: Help request ───────────────────────────────────────────
    def test_help_request(self):
        for phrase in ["help", "help me", "what can I say?"]:
            result = try_rule_based(phrase)
            assert result is not None, f"Failed for '{phrase}'"
            assert result.intent_type == "help_request"
            assert result.action == "help"

    # ── T17: Empty input (silence) ──────────────────────────────────
    def test_silence_empty(self):
        result = try_rule_based("")
        assert result is not None
        assert result.intent_type == "unclear"
        assert result.action == "clarify"
        assert result.confidence < 0.5

    # ── T20: Stop music ─────────────────────────────────────────────
    def test_stop(self):
        result = try_rule_based("stop")
        assert result is not None
        assert result.intent_type == "direct_command"
        assert result.action == "stop"

    # ── Play with target ────────────────────────────────────────────
    def test_play_with_target(self):
        result = try_rule_based("play something relaxing")
        assert result is not None
        assert result.intent_type == "direct_command"
        assert result.action == "play"

    # ── Context requests now handled by rules ──────────────────────
    def test_context_handled_by_rules(self):
        """Context requests like 'I am tired' should match rules directly."""
        result = try_rule_based("I am tired")
        assert result is not None
        assert result.intent_type == "context_request"
        assert result.action == "select_playlist"
        assert result.interpreted_context == "calm"

    def test_off_topic_handled_by_rules(self):
        """Off-topic like 'what is the weather' should be caught by rules."""
        result = try_rule_based("What is the weather?")
        assert result is not None
        assert result.intent_type == "off_topic"
        assert result.action == "reject"

    # ── Case insensitivity ──────────────────────────────────────────
    def test_case_insensitive(self):
        result = try_rule_based("PAUSE")
        assert result is not None
        assert result.action == "pause"

        result = try_rule_based("Play Jazz")
        assert result is not None
        assert result.action == "play"


class TestIntentResultSchema:
    """Test the IntentResult Pydantic model."""

    def test_valid_intent(self):
        intent = IntentResult(
            intent_type="direct_command",
            action="play",
            interpreted_context="none",
            confidence=0.95,
            user_feedback="Playing music.",
        )
        assert intent.intent_type == "direct_command"
        assert intent.action == "play"
        assert intent.is_music_command()

    def test_low_confidence(self):
        intent = IntentResult(
            intent_type="unclear",
            action="clarify",
            interpreted_context="none",
            confidence=0.3,
            user_feedback="Please try again.",
        )
        assert intent.is_low_confidence(0.6)
        assert not intent.is_low_confidence(0.2)

    def test_needs_playlist(self):
        intent = IntentResult(
            intent_type="context_request",
            action="select_playlist",
            interpreted_context="calm",
            confidence=0.85,
            user_feedback="Playing calm music.",
        )
        assert intent.needs_playlist()
        assert not intent.is_music_command()

    def test_confidence_bounds(self):
        """Confidence must be between 0.0 and 1.0."""
        with pytest.raises(Exception):
            IntentResult(
                intent_type="direct_command",
                action="play",
                interpreted_context="none",
                confidence=1.5,  # Invalid
                user_feedback="test",
            )

    def test_invalid_intent_type(self):
        """Invalid intent types should raise validation error."""
        with pytest.raises(Exception):
            IntentResult(
                intent_type="invalid_type",
                action="play",
                interpreted_context="none",
                confidence=0.9,
                user_feedback="test",
            )


from unittest.mock import patch

class TestAIClassifier:
    """Test the AI-based fallback classifier with mocked OpenAI."""

    @pytest.fixture
    def mock_settings(self):
        from echo_sync.config.settings import Settings
        settings = Settings()
        settings.openai_api_key = "test_key"
        settings.ai_model = "test-model"
        return settings

    @patch("echo_sync.ai.intent_classifier.OpenAI")
    def test_ai_fallback_stop_music(self, mock_openai_cls, mock_settings):
        mock_openai = mock_openai_cls.return_value
        # Setup mock JSON response
        mock_response = mock_openai.chat.completions.create.return_value
        mock_message = mock_response.choices[0].message
        mock_message.content = '{"intent_type": "direct_command", "action": "stop", "interpreted_context": "calm", "confidence": 0.95, "user_feedback": "Stopping the music."}'

        from echo_sync.ai.intent_classifier import IntentClassifier
        classifier = IntentClassifier(mock_settings)
        
        # Act
        result = classifier.classify("I want to sleep, stop the music")
        
        # Assert
        assert result.intent_type == "direct_command"
        assert result.action == "stop"
        assert result.interpreted_context == "calm"
        assert result.confidence == 0.95

    @patch("echo_sync.ai.intent_classifier.OpenAI")
    def test_ai_fallback_volume_down(self, mock_openai_cls, mock_settings):
        mock_openai = mock_openai_cls.return_value
        mock_response = mock_openai.chat.completions.create.return_value
        mock_message = mock_response.choices[0].message
        mock_message.content = '{"intent_type": "direct_command", "action": "volume_down", "interpreted_context": "none", "confidence": 0.9, "user_feedback": "Turning it down."}'

        from echo_sync.ai.intent_classifier import IntentClassifier
        classifier = IntentClassifier(mock_settings)
        
        result = classifier.classify("This song is too loud")
        
        assert result.intent_type == "direct_command"
        assert result.action == "volume_down"

    @patch("echo_sync.ai.intent_classifier.OpenAI")
    def test_ai_fallback_next_song(self, mock_openai_cls, mock_settings):
        mock_openai = mock_openai_cls.return_value
        mock_response = mock_openai.chat.completions.create.return_value
        mock_message = mock_response.choices[0].message
        mock_message.content = '{"intent_type": "direct_command", "action": "next", "interpreted_context": "none", "confidence": 0.9, "user_feedback": "Skipping song."}'

        from echo_sync.ai.intent_classifier import IntentClassifier
        classifier = IntentClassifier(mock_settings)
        
        result = classifier.classify("This song is annoying")
        
        assert result.intent_type == "direct_command"
        assert result.action == "next"
