"""
Echo-Sync playlist manager.

Scans music folders, builds playlists, and selects tracks.
Supports random shuffle and sequential playback modes.
"""

import logging
import random
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Audio formats scanned from the music folders
SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".wma"}


class PlaylistManager:
    """
    Manages music playlists from local folders.

    Scans configured music directories and builds playlists
    organized by context/mood category.
    """

    def __init__(self, music_root: Path) -> None:
        """
        Initialize the playlist manager.

        Args:
            music_root: Root directory containing music subfolders
                        (calm/, energy/, focus/, happy/, sad/, fallback/).
        """
        self.music_root = music_root
        self._playlists: dict[str, list[Path]] = {}
        self._scan_folders()

    def _scan_folders(self) -> None:
        """Scan all subfolders in the music root for audio files."""
        if not self.music_root.exists():
            logger.warning("Music root does not exist: %s", self.music_root)
            return

        for folder in sorted(self.music_root.iterdir()):
            if folder.is_dir():
                tracks = self._get_audio_files(folder)
                self._playlists[folder.name] = tracks
                logger.info(
                    "Found %d tracks in '%s/'",
                    len(tracks),
                    folder.name,
                )

    @staticmethod
    def _get_audio_files(folder: Path) -> list[Path]:
        """Get all supported audio files from a folder."""
        files = []
        for f in sorted(folder.iterdir()):
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS:
                files.append(f)
        return files

    def get_playlist(
        self,
        category: str,
        shuffle: bool = True,
    ) -> list[Path]:
        """
        Get a playlist for a given category.

        Args:
            category: Folder name (e.g., 'calm', 'energy', 'fallback').
            shuffle: If True, return the tracks in random order.

        Returns:
            List of paths to audio files.
            Falls back to 'fallback' category if requested one is empty.
        """
        tracks = self._playlists.get(category, [])

        if not tracks:
            logger.warning(
                "No tracks in '%s' — trying fallback",
                category,
            )
            tracks = self._playlists.get("fallback", [])

        if not tracks:
            logger.warning("No tracks available at all!")
            return []

        playlist = list(tracks)  # Copy to avoid modifying original
        if shuffle:
            random.shuffle(playlist)

        return playlist

    def get_track_by_name(self, name: str) -> Optional[Path]:
        """
        Search all playlists for a track matching the given name.

        Args:
            name: Partial or full track name to search for.

        Returns:
            Path to the first matching track, or None.
        """
        name_lower = name.lower()
        for category, tracks in self._playlists.items():
            for track in tracks:
                if name_lower in track.stem.lower():
                    logger.info(
                        "Found track '%s' in '%s'",
                        track.stem,
                        category,
                    )
                    return track
        return None

    def get_all_tracks(self) -> list[Path]:
        """Get all tracks from all categories."""
        all_tracks = []
        for tracks in self._playlists.values():
            all_tracks.extend(tracks)
        return all_tracks

    def get_available_categories(self) -> list[str]:
        """Get list of categories that have tracks."""
        return [
            cat for cat, tracks in self._playlists.items()
            if tracks
        ]

    def get_track_count(self, category: Optional[str] = None) -> int:
        """Get the number of tracks in a category or total."""
        if category:
            return len(self._playlists.get(category, []))
        return sum(len(t) for t in self._playlists.values())

    def refresh(self) -> None:
        """Re-scan all music folders."""
        self._playlists.clear()
        self._scan_folders()
