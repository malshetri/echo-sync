"""
Echo-Sync application settings.

Loads configuration from environment variables and .env file
using pydantic-settings for type-safe, validated configuration.
"""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


# Keep asset paths relative to the repository instead of a user's computer.
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    """Echo-Sync application configuration."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        env_prefix="ECHO_SYNC_",
        extra="ignore",
    )

    # OpenAI
    # OpenAI uses its usual unprefixed environment variable.
    openai_api_key: str = "your_api_key_here"

    # Speech-to-text
    stt_mode: Literal["openai", "offline"] = "openai"
    stt_model: str = "gpt-4o-mini-transcribe"

    # Intent classification
    ai_model: str = "gpt-4o-mini"

    # Media player
    player: Literal["vlc", "pygame"] = "vlc"
    default_volume: int = 80
    ducking_volume: int = 30

    # Interaction timing
    silence_timeout: int = 10
    confidence_threshold: float = 0.6
    
    # Voice activation
    wake_word: str = "echo"

    # Paths relative to PROJECT_ROOT
    music_dir: str = "assets/music"
    earcons_dir: str = "assets/earcons"
    log_file: str = "logs/interaction_logs.csv"

    # Absolute paths used by the application
    @property
    def music_path(self) -> Path:
        """Absolute path to the music assets directory."""
        return PROJECT_ROOT / self.music_dir

    @property
    def earcons_path(self) -> Path:
        """Absolute path to the earcons assets directory."""
        return PROJECT_ROOT / self.earcons_dir

    @property
    def log_path(self) -> Path:
        """Absolute path to the interaction log file."""
        return PROJECT_ROOT / self.log_file



def load_settings() -> Settings:
    """
    Load and return application settings.

    Reads from .env file and environment variables.
    OPENAI_API_KEY is read without prefix; all other settings use ECHO_SYNC_ prefix.
    """
    import os
    from dotenv import load_dotenv

    # Load the standard OpenAI variable before Pydantic reads the settings.
    load_dotenv(PROJECT_ROOT / ".env")

    settings = Settings()

    api_key = os.environ.get("OPENAI_API_KEY", settings.openai_api_key)
    settings.openai_api_key = api_key

    return settings
