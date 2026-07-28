"""
Echo-Sync context mapper.

Maps interpreted user context (mood/situation) to local music folders.
Uses simple dictionary mapping — no AI needed here.
"""

import logging
from pathlib import Path
from typing import Optional

from echo_sync.config.settings import Settings

logger = logging.getLogger(__name__)


# Context-to-folder mapping
# The values match the folder names under assets/music.
CONTEXT_TO_FOLDER = {
    "calm": "calm",
    "energy": "energy",
    "focus": "focus",
    "happy": "happy",
    "sad": "sad",
    "unknown": "fallback",
    "none": "fallback",
}


class ContextMapper:
    """
    Maps interpreted context labels to local music folder paths.

    The mapping is straightforward: each context string maps to a
    subfolder inside the configured music directory.
    """

    def __init__(self, settings: Settings) -> None:
        self.music_root = settings.music_path

    def get_playlist_path(self, context: str) -> Path:
        """
        Get the absolute path to the music folder for a given context.

        Args:
            context: One of 'calm', 'energy', 'focus', 'happy', 'sad',
                     'unknown', or 'none'.

        Returns:
            Path to the corresponding music folder.
            Falls back to 'fallback' folder if context is unknown.
        """
        folder_name = CONTEXT_TO_FOLDER.get(context, "fallback")
        playlist_path = self.music_root / folder_name

        if not playlist_path.exists():
            logger.warning(
                "Music folder does not exist: %s — falling back",
                playlist_path,
            )
            playlist_path = self.music_root / "fallback"

        logger.info("Context '%s' → folder '%s'", context, playlist_path)
        return playlist_path

    def get_available_contexts(self) -> list[str]:
        """
        Return list of contexts that have actual music files available.

        Useful for guided help to tell users what's available.
        """
        available = []
        for context, folder_name in CONTEXT_TO_FOLDER.items():
            if context == "none":
                continue
            folder = self.music_root / folder_name
            if folder.exists() and any(folder.iterdir()):
                available.append(context)
        return available

    def get_all_music_folders(self) -> dict[str, Path]:
        """Return all context-to-path mappings."""
        return {
            ctx: self.music_root / folder
            for ctx, folder in CONTEXT_TO_FOLDER.items()
        }

    @staticmethod
    def get_context_description(context: str) -> str:
        """
        Get a user-friendly description of a context.

        Used in spoken feedback to the user.
        """
        descriptions = {
            "calm": "calm and relaxing",
            "energy": "energetic and upbeat",
            "focus": "focused and ambient",
            "happy": "happy and cheerful",
            "sad": "soft and soothing",
            "unknown": "a mix of",
            "none": "some",
        }
        return descriptions.get(context, "some")
