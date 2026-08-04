"""
Tests for the Echo-Sync smart ducking module.

Tests volume ducking behavior, idempotency, and fail-safety.
"""

import pytest
from unittest.mock import MagicMock

from echo_sync.audio.ducking import SmartDucker


@pytest.fixture
def mock_player():
    """Create a mock player with volume control."""
    player = MagicMock()
    player.get_volume.return_value = 80
    return player


@pytest.fixture
def ducker(mock_player):
    """Create a SmartDucker with a mock player attached."""
    d = SmartDucker(ducking_volume=30)
    d.attach_player(mock_player)
    return d


class TestSmartDucker:
    """Test smart ducking behavior."""

    def test_duck_lowers_volume(self, ducker, mock_player):
        """Ducking should set volume to the ducking level."""
        ducker.duck()
        mock_player.set_volume.assert_called_with(30)
        assert ducker.is_ducked

    def test_duck_saves_original_volume(self, ducker, mock_player):
        """Ducking should save the original volume for restore."""
        mock_player.get_volume.return_value = 75
        ducker.duck()
        assert ducker._original_volume == 75

    def test_double_duck_is_idempotent(self, ducker, mock_player):
        """Calling duck() twice should not lower volume twice."""
        ducker.duck()
        mock_player.set_volume.reset_mock()
        ducker.duck()  # Second call should be a no-op
        mock_player.set_volume.assert_not_called()

    def test_unduck_when_not_ducked(self, ducker, mock_player):
        """Calling unduck() when not ducked should be a no-op."""
        ducker.unduck()  # Should not raise or call set_volume
        mock_player.set_volume.assert_not_called()

    def test_unduck_clears_flag(self, ducker):
        """After unducking, is_ducked should be False."""
        ducker.duck()
        assert ducker.is_ducked
        ducker.unduck()
        assert not ducker.is_ducked

    def test_duck_without_player(self):
        """Ducking with no player attached should not crash."""
        d = SmartDucker(ducking_volume=30)
        # No player attached
        d.duck()   # Should not raise
        d.unduck()  # Should not raise
        assert not d.is_ducked

    def test_duck_with_player_error(self, ducker, mock_player):
        """Ducking should handle player errors gracefully."""
        mock_player.get_volume.side_effect = RuntimeError("player error")
        ducker.duck()  # Should not raise
        # is_ducked might be False since the duck failed

    def test_update_target_volume(self, ducker):
        """update_target_volume should change the restore target."""
        ducker.update_target_volume(90)
        assert ducker._original_volume == 90

    def test_effective_volume_not_ducked_reads_live_volume(self, ducker, mock_player):
        """Not ducked: effective volume is the player's live volume."""
        mock_player.get_volume.return_value = 65
        assert ducker.get_effective_volume() == 65

    def test_effective_volume_while_ducked_returns_pre_duck_volume(
        self, ducker, mock_player
    ):
        """
        Ducked: effective volume must be the saved pre-duck level (80),
        not the live ducked level (30) — this is what the volume up/down
        bug depended on.
        """
        mock_player.get_volume.return_value = 80
        ducker.duck()
        assert ducker.get_effective_volume() == 80

    def test_effective_volume_no_player_falls_back_to_original(self):
        """With no player attached, fall back to the tracked original volume."""
        d = SmartDucker(ducking_volume=30)
        assert d.get_effective_volume() == d._original_volume
