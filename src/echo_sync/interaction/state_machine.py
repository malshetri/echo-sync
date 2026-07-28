"""
Echo-Sync state machine.

Tracks the application state for the interaction flow.
States: SLEEPING, AWAKE_WAITING_COMMAND, AWAKE_CLARIFYING, PLAYING_PASSIVE
"""

import logging
from enum import Enum, auto
from typing import Optional

logger = logging.getLogger(__name__)


class AppState(Enum):
    """Application states for the Echo-Sync interaction loop."""

    SLEEPING = auto()               # System is waiting only for the wake word
    AWAKE_WAITING_COMMAND = auto()  # Woken up, waiting for a command
    AWAKE_CLARIFYING = auto()       # Didn't understand, keeping awake to help
    PLAYING_PASSIVE = auto()        # Music playing, ignoring everything except wake word
    SHUTTING_DOWN = auto()          # System is shutting down


# Allowed state transitions
VALID_TRANSITIONS: dict[AppState, set[AppState]] = {
    AppState.SLEEPING: {
        AppState.SLEEPING,
        AppState.AWAKE_WAITING_COMMAND,
        AppState.PLAYING_PASSIVE,
        AppState.SHUTTING_DOWN,
    },
    AppState.AWAKE_WAITING_COMMAND: {
        AppState.AWAKE_WAITING_COMMAND,
        AppState.SLEEPING,
        AppState.PLAYING_PASSIVE,
        AppState.AWAKE_CLARIFYING,
        AppState.SHUTTING_DOWN,
    },
    AppState.AWAKE_CLARIFYING: {
        AppState.AWAKE_CLARIFYING,
        AppState.SLEEPING,
        AppState.PLAYING_PASSIVE,
        AppState.AWAKE_WAITING_COMMAND,
        AppState.SHUTTING_DOWN,
    },
    AppState.PLAYING_PASSIVE: {
        AppState.PLAYING_PASSIVE,
        AppState.AWAKE_WAITING_COMMAND,
        AppState.SLEEPING,
        AppState.SHUTTING_DOWN,
    },
    AppState.SHUTTING_DOWN: set(),  # Terminal state
}


class StateMachine:
    """
    Simple state machine for tracking Echo-Sync application state.

    Enforces valid state transitions and provides logging.
    """

    def __init__(self, initial_state: AppState = AppState.SLEEPING) -> None:
        self._state = initial_state
        self._previous_state: Optional[AppState] = None
        logger.info("State machine initialized: %s", self._state.name)

    @property
    def state(self) -> AppState:
        """Current application state."""
        return self._state

    @property
    def previous_state(self) -> Optional[AppState]:
        """Previous application state."""
        return self._previous_state

    def transition(self, new_state: AppState) -> bool:
        """
        Attempt to transition to a new state.

        Args:
            new_state: The target state.

        Returns:
            True if the transition was valid and executed.
            False if the transition is not allowed.
        """
        valid = VALID_TRANSITIONS.get(self._state, set())
        if new_state not in valid:
            logger.warning(
                "Invalid state transition: %s → %s",
                self._state.name,
                new_state.name,
            )
            return False

        self._previous_state = self._state
        self._state = new_state
        logger.debug(
            "State: %s → %s",
            self._previous_state.name,
            self._state.name,
        )
        return True

    def force_state(self, new_state: AppState) -> None:
        """Force a state change without validation (for error recovery)."""
        self._previous_state = self._state
        self._state = new_state
        logger.warning(
            "Forced state: %s → %s",
            self._previous_state.name,
            self._state.name,
        )

    def is_active(self) -> bool:
        """Check if the system is in an active (non-terminal) state."""
        return self._state != AppState.SHUTTING_DOWN

    # State checks
    
    def is_awake(self) -> bool:
        """Check if the system is actively waiting for a command or clarifying."""
        return self._state in {AppState.AWAKE_WAITING_COMMAND, AppState.AWAKE_CLARIFYING}

    def is_passive(self) -> bool:
        """Check if the system is passively playing music or sleeping."""
        return self._state in {AppState.SLEEPING, AppState.PLAYING_PASSIVE}

    # State changes
    
    def wake(self) -> None:
        """Wake up the system to wait for a command."""
        self.transition(AppState.AWAKE_WAITING_COMMAND)

    def sleep(self) -> None:
        """Put the system to sleep, waiting for the wake word."""
        self.transition(AppState.SLEEPING)

    def start_clarifying(self) -> None:
        """Move to clarifying state, keeping the system awake."""
        self.transition(AppState.AWAKE_CLARIFYING)

    def start_playing_passive(self) -> None:
        """Move to passive playing state."""
        self.transition(AppState.PLAYING_PASSIVE)
