"""
Echo-Sync smart ducking.

Manages music volume ducking behavior:
- When user starts speaking: reduce music volume to 25-35%
- While assistant responds: keep volume low
- After action is complete: fade back to previous volume over 1-2 seconds

This ensures the user's voice and system responses are always
clearly audible over the music.
"""

import logging
import threading
import time

logger = logging.getLogger(__name__)

# ── Ducking defaults ────────────────────────────────────────────────────────
DEFAULT_DUCKING_VOLUME = 30      # Volume level during ducking (%)
DEFAULT_FADE_DURATION = 1.5      # Seconds to fade volume back up
DEFAULT_FADE_STEPS = 15          # Number of steps in the fade


class SmartDucker:
    """
    Controls smart volume ducking for music playback.

    Coordinates with the media player to temporarily reduce volume
    when the user is speaking or the system is responding.
    """

    def __init__(
        self,
        ducking_volume: int = DEFAULT_DUCKING_VOLUME,
        fade_duration: float = DEFAULT_FADE_DURATION,
    ) -> None:
        """
        Initialize the smart ducker.

        Args:
            ducking_volume: Volume level (0-100) during ducking.
            fade_duration: Duration in seconds for the volume fade-in.
        """
        self.ducking_volume = ducking_volume
        self.fade_duration = fade_duration

        self._player = None  # Set via attach_player()
        self._original_volume: int = 80
        self._is_ducked = False
        self._fade_thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def attach_player(self, player) -> None:
        """
        Attach a media player instance for volume control.

        Args:
            player: A player object with get_volume() and set_volume() methods.
        """
        self._player = player

    def duck(self) -> None:
        """
        Reduce music volume for ducking.

        Saves the current volume and reduces to the ducking level.
        Called when user starts speaking or system starts responding.
        """
        with self._lock:
            if self._is_ducked:
                return  # Already ducked

            if self._player is None:
                logger.debug("No player attached — skip ducking")
                return

            try:
                self._original_volume = self._player.get_volume()
                self._player.set_volume(self.ducking_volume)
                self._is_ducked = True
                logger.info(
                    "Ducked: %d%% → %d%%",
                    self._original_volume,
                    self.ducking_volume,
                )
            except Exception as e:
                logger.error("Failed to duck volume: %s", e)

    def update_target_volume(self, target_volume: int) -> None:
        """Update the volume that will be restored when unducking."""
        with self._lock:
            self._original_volume = target_volume

    def get_effective_volume(self) -> int:
        """
        Return the volume the user perceives as "current".

        While ducked, the player's live volume is temporarily lowered for
        speech clarity, so relative changes (volume up/down) must be based
        on the pre-duck target volume instead of the live (ducked) one.
        """
        if self._is_ducked:
            return self._original_volume
        if self._player is not None:
            return self._player.get_volume()
        return self._original_volume

    def unduck(self) -> None:
        """
        Restore music volume with a smooth fade.

        Gradually increases volume from ducking level back to the
        original level over the configured fade duration.
        """
        with self._lock:
            if not self._is_ducked:
                return  # Not ducked

            self._is_ducked = False

        # Fade in a background thread to avoid blocking
        self._fade_thread = threading.Thread(
            target=self._fade_to_volume,
            args=(self._original_volume,),
            daemon=True,
        )
        self._fade_thread.start()

    def _fade_to_volume(self, target_volume: int) -> None:
        """Gradually fade volume to target over fade_duration seconds."""
        if self._player is None:
            return

        try:
            current = self._player.get_volume()
            step_count = DEFAULT_FADE_STEPS
            step_delay = self.fade_duration / step_count
            volume_step = (target_volume - current) / step_count

            for i in range(step_count):
                if self._is_ducked:
                    # Ducking was re-engaged during fade — abort
                    return
                new_volume = int(current + volume_step * (i + 1))
                new_volume = max(0, min(100, new_volume))
                self._player.set_volume(new_volume)
                time.sleep(step_delay)

            # Ensure exact final volume
            self._player.set_volume(target_volume)
            logger.info("Volume restored to %d%%", target_volume)

        except Exception as e:
            logger.error("Failed to fade volume: %s", e)

    @property
    def is_ducked(self) -> bool:
        """Check if volume is currently ducked."""
        return self._is_ducked
