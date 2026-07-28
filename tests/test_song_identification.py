"""
Tests for FR-07 Song Identification.

Covers both the rule-based routing ("what song is this?" → identify) and
the dialog-manager handler that announces the current track title.
"""

from pathlib import Path
from types import SimpleNamespace

import pytest

from echo_sync.ai.intent_classifier import try_rule_based
from echo_sync.ai.intent_schema import IntentResult
from echo_sync.config.settings import Settings
from echo_sync.interaction.dialog_manager import DialogManager


class TestIdentifyRouting:
    """The intent classifier should route identification questions correctly."""

    @pytest.mark.parametrize(
        "phrase",
        [
            "what song is this",
            "what song is this?",
            "what's playing",
            "what is playing",
            "what track is this",
            "name this track",
            "name this song",
            "which song is playing",
            "current song",
            "now playing",
        ],
    )
    def test_identify_recognized(self, phrase):
        result = try_rule_based(phrase)
        assert result is not None, f"Failed for '{phrase}'"
        assert result.intent_type == "direct_command"
        assert result.action == "identify"
        assert result.confidence >= 0.9

    @pytest.mark.parametrize(
        "phrase",
        ["What is the weather?", "What is 2+2?", "Tell me about dogs"],
    )
    def test_identify_does_not_swallow_off_topic(self, phrase):
        """Identification patterns must not hijack genuine off-topic questions."""
        result = try_rule_based(phrase)
        assert result is not None
        assert result.action == "reject"
        assert result.intent_type == "off_topic"


class _FakePlayer:
    def __init__(self, track: str = "", playing: bool = False) -> None:
        self._track = track
        self._playing = playing

    def get_current_track(self) -> str:
        return self._track

    def is_playing(self) -> bool:
        return self._playing


class _FakeEarcons:
    def play(self, *args, **kwargs) -> None:
        pass


def _make_dialog_manager(player: _FakePlayer) -> DialogManager:
    settings = Settings()
    return DialogManager(
        settings=settings,
        player=player,
        playlist_manager=SimpleNamespace(get_playlist=lambda *a, **k: []),
        context_mapper=SimpleNamespace(get_playlist_path=lambda c: Path(c)),
        earcon_manager=_FakeEarcons(),
        ducker=SimpleNamespace(),
    )


def _identify_intent() -> IntentResult:
    return IntentResult(
        intent_type="direct_command",
        action="identify",
        interpreted_context="none",
        confidence=0.97,
        user_feedback="Let me check what's playing.",
    )


class TestIdentifyHandler:
    """The dialog manager should announce the current track when asked."""

    def test_announces_current_track(self):
        dm = _make_dialog_manager(_FakePlayer("soft_piano_01", playing=True))
        response = dm.handle_intent(_identify_intent())
        assert "soft piano 01" in response.lower()

    def test_reports_nothing_playing(self):
        dm = _make_dialog_manager(_FakePlayer("", playing=False))
        response = dm.handle_intent(_identify_intent())
        assert "nothing is playing" in response.lower()
