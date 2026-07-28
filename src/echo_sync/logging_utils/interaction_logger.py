"""
Echo-Sync interaction logger.

Saves evidence for documentation and testing.
Each interaction is logged as a CSV row with full details.
"""

import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from echo_sync.ai.intent_schema import IntentResult
from echo_sync.config.settings import Settings

logger = logging.getLogger(__name__)

# Columns used by both the logger and report script
CSV_HEADERS = [
    "timestamp",
    "audio_file",
    "transcript",
    "intent_type",
    "action",
    "interpreted_context",
    "confidence",
    "system_response",
    "success",
    "notes",
]


class InteractionLogger:
    """
    Logs all user interactions to a CSV file.

    Each row captures the full interaction cycle:
    audio → transcript → intent → action → response.

    This log is essential for:
    - Documentation and reporting
    - Testing evidence
    - Debugging interaction issues
    """

    def __init__(self, settings: Settings) -> None:
        self.log_path = settings.log_path
        self._ensure_log_file()

    def _ensure_log_file(self) -> None:
        """Create the log file with headers if it doesn't exist."""
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.log_path.exists():
            with open(self.log_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(CSV_HEADERS)
            logger.info("Created interaction log: %s", self.log_path)

    def log_interaction(
        self,
        audio_file: Optional[str] = None,
        transcript: str = "",
        intent_result: Optional[IntentResult] = None,
        system_response: str = "",
        success: bool = True,
        notes: str = "",
    ) -> None:
        """
        Log a single interaction to the CSV file.

        Args:
            audio_file: Path to the recorded audio file.
            transcript: The transcribed user speech.
            intent_result: The classified intent result.
            system_response: The system's response text.
            success: Whether the interaction was successful.
            notes: Additional notes or error messages.
        """
        try:
            timestamp = datetime.now(timezone.utc).isoformat()

            row = [
                timestamp,
                audio_file or "",
                transcript,
                intent_result.intent_type if intent_result else "",
                intent_result.action if intent_result else "",
                intent_result.interpreted_context if intent_result else "",
                f"{intent_result.confidence:.2f}" if intent_result else "",
                system_response,
                "yes" if success else "no",
                notes,
            ]

            with open(self.log_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(row)

            logger.debug("Interaction logged: %s → %s", transcript[:50], system_response[:50])

        except Exception as e:
            logger.error("Failed to log interaction: %s", e)

    def log_system_event(self, event: str, notes: str = "") -> None:
        """Log a system event (startup, shutdown, error, etc.)."""
        self.log_interaction(
            transcript=f"[SYSTEM] {event}",
            system_response=event,
            notes=notes,
        )

    def get_log_count(self) -> int:
        """Get the number of logged interactions."""
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                return sum(1 for _ in f) - 1  # Subtract header row
        except FileNotFoundError:
            return 0
