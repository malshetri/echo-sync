"""
Tests for the Echo-Sync dialog manager volume handling.

Regression tests for the ducking/volume interaction bug: relative
volume changes (and explicit targets) must be based on the pre-duck
volume, not the temporarily-lowered live player volume.
"""

from unittest.mock import MagicMock

import pytest

from echo_sync.audio.ducking import SmartDucker
from echo_sync.interaction.dialog_manager import DialogManager


@pytest.fixture
def mock_player():
    player = MagicMock()
    player.get_volume.return_value = 80
    return player


@pytest.fixture
def ducker(mock_player):
    d = SmartDucker(ducking_volume=30)
    d.attach_player(mock_player)
    return d


@pytest.fixture
def dialog(mock_player, ducker):
    return DialogManager(
        settings=MagicMock(),
        player=mock_player,
        playlist_manager=MagicMock(),
        context_mapper=MagicMock(),
        earcon_manager=MagicMock(),
        ducker=ducker,
    )


class TestVolumeAdjustment:
    """Regression tests for the ducking/volume-level bug."""

    def test_volume_up_not_ducked_uses_live_volume(self, dialog, mock_player):
        """Not ducked: relative change is based on the live player volume."""
        mock_player.get_volume.return_value = 50
        new_vol = dialog._adjust_volume(delta=10)
        assert new_vol == 60
        mock_player.set_volume.assert_called_with(60)

    def test_volume_up_while_ducked_uses_pre_duck_baseline(
        self, dialog, ducker, mock_player
    ):
        """
        The bug: while ducked, live volume is 30%, so naive +10 gave 40%
        regardless of the real baseline. Fixed: must use the pre-duck
        volume (80) as the baseline, giving 90 — not 40.
        """
        mock_player.get_volume.return_value = 80
        ducker.duck()
        assert ducker.is_ducked
        mock_player.set_volume.reset_mock()  # clear the duck()'s own call

        new_vol = dialog._adjust_volume(delta=10)

        assert new_vol == 90
        assert new_vol != 40  # the reported bug value
        # While still ducked, the live volume must not be touched directly —
        # only the restore target, so the change lands smoothly on unduck.
        mock_player.set_volume.assert_not_called()
        assert ducker._original_volume == 90

    def test_volume_down_while_ducked_uses_pre_duck_baseline(
        self, dialog, ducker, mock_player
    ):
        """Same bug, other direction: must not collapse to 20%."""
        mock_player.get_volume.return_value = 80
        ducker.duck()

        new_vol = dialog._adjust_volume(delta=-10)

        assert new_vol == 70
        assert new_vol != 20  # the reported bug value
        assert ducker._original_volume == 70

    def test_volume_clamped_at_100(self, dialog, mock_player):
        mock_player.get_volume.return_value = 95
        assert dialog._adjust_volume(delta=10) == 100

    def test_volume_clamped_at_0(self, dialog, mock_player):
        mock_player.get_volume.return_value = 5
        assert dialog._adjust_volume(delta=-10) == 0

    def test_set_absolute_volume_not_ducked(self, dialog, mock_player):
        new_vol = dialog._adjust_volume(absolute=70)
        assert new_vol == 70
        mock_player.set_volume.assert_called_with(70)

    def test_set_absolute_volume_while_ducked(self, dialog, ducker, mock_player):
        """An explicit target while ducked also only updates the restore target."""
        ducker.duck()
        mock_player.set_volume.reset_mock()  # clear the duck()'s own call
        new_vol = dialog._adjust_volume(absolute=55)
        assert new_vol == 55
        mock_player.set_volume.assert_not_called()
        assert ducker._original_volume == 55

    def test_set_volume_action_routes_through_handle_intent(
        self, dialog, mock_player
    ):
        """A 'set_volume' intent with volume_level is applied end-to-end."""
        from echo_sync.ai.intent_schema import IntentResult

        intent = IntentResult(
            intent_type="direct_command",
            action="set_volume",
            interpreted_context="none",
            confidence=0.97,
            volume_level=65,
            user_feedback="Volume set to 65 percent.",
        )
        response = dialog._handle_direct_command(intent)
        mock_player.set_volume.assert_called_with(65)
        assert "65" in response
