"""
Echo-Sync silence detector.

Analyzes audio data to detect silence, used for:
- Auto-stopping recording when user finishes speaking
- Triggering silence timeout for guided help
"""

import logging
import numpy as np

logger = logging.getLogger(__name__)

# Silence thresholds
DEFAULT_SILENCE_THRESHOLD = 0.02  # RMS amplitude below this = silence
DEFAULT_SILENCE_DURATION = 1.5    # Seconds of silence to stop recording
DEFAULT_MIN_SPEECH_DURATION = 0.3  # Minimum seconds of speech to be valid


class SilenceDetector:
    """
    Detects silence in audio data using RMS amplitude analysis.

    Used to determine when the user has stopped speaking so recording
    can be automatically terminated.
    """

    def __init__(
        self,
        threshold: float = DEFAULT_SILENCE_THRESHOLD,
        silence_duration: float = DEFAULT_SILENCE_DURATION,
        min_speech_duration: float = DEFAULT_MIN_SPEECH_DURATION,
        sample_rate: int = 16000,
    ) -> None:
        """
        Initialize the silence detector.

        Args:
            threshold: RMS amplitude below which audio is considered silence.
            silence_duration: Seconds of continuous silence to trigger stop.
            min_speech_duration: Minimum seconds of speech required.
            sample_rate: Audio sample rate in Hz.
        """
        self.threshold = threshold
        self.silence_duration = silence_duration
        self.min_speech_duration = min_speech_duration
        self.sample_rate = sample_rate

        # State is reset for each recording.
        self._silence_samples = 0
        self._speech_samples = 0
        self._has_speech = False

    def reset(self) -> None:
        """Reset the detector state for a new recording."""
        self._silence_samples = 0
        self._speech_samples = 0
        self._has_speech = False

    def process_chunk(self, audio_chunk: np.ndarray) -> bool:
        """
        Process a chunk of audio data.

        Args:
            audio_chunk: NumPy array of audio samples.

        Returns:
            True if recording should stop (silence detected after speech),
            False if recording should continue.
        """
        rms = self._calculate_rms(audio_chunk)

        if rms > self.threshold:
            # A louder block starts or continues speech.
            self._speech_samples += len(audio_chunk)
            self._silence_samples = 0

            if not self._has_speech:
                speech_seconds = self._speech_samples / self.sample_rate
                if speech_seconds >= self.min_speech_duration:
                    self._has_speech = True
                    logger.debug("Speech detected (%.2fs)", speech_seconds)
        else:
            # Count quiet blocks only after speech has started.
            self._silence_samples += len(audio_chunk)

        # Enough trailing silence means the command is complete.
        if self._has_speech:
            silence_seconds = self._silence_samples / self.sample_rate
            if silence_seconds >= self.silence_duration:
                logger.info(
                    "Silence detected (%.2fs) — stopping recording",
                    silence_seconds,
                )
                return True

        return False

    def is_only_silence(self) -> bool:
        """Check if no speech was detected at all."""
        return not self._has_speech

    @staticmethod
    def _calculate_rms(audio_chunk: np.ndarray) -> float:
        """Calculate the Root Mean Square of an audio chunk."""
        if len(audio_chunk) == 0:
            return 0.0
        return float(np.sqrt(np.mean(audio_chunk.astype(np.float64) ** 2)))
