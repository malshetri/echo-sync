"""
Echo-Sync microphone recorder.

Records user speech using sounddevice + soundfile.
Automatically stops when silence is detected after speech.
"""

import logging
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional

import numpy as np
import sounddevice as sd
import soundfile as sf

from echo_sync.audio.silence_detector import SilenceDetector

logger = logging.getLogger(__name__)

# Recording defaults
DEFAULT_SAMPLE_RATE = 16000
DEFAULT_CHANNELS = 1
DEFAULT_CHUNK_SIZE = 1024
DEFAULT_MAX_DURATION = 30  # Maximum recording duration in seconds


class MicrophoneRecorder:
    """
    Records audio from the system microphone.

    Features:
    - Automatic silence detection for natural stop
    - Maximum recording duration safety limit
    - Thread-safe recording with clean shutdown
    - Saves to WAV format for STT processing
    """

    def __init__(
        self,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        channels: int = DEFAULT_CHANNELS,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        max_duration: float = DEFAULT_MAX_DURATION,
        no_speech_timeout: float = 10.0,
    ) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.max_duration = max_duration
        # Stop waiting when no speech begins, allowing guided help to respond.
        self.no_speech_timeout = no_speech_timeout

        self.silence_detector = SilenceDetector(sample_rate=sample_rate)

        self._recording = False
        self._audio_data: list[np.ndarray] = []
        self._lock = threading.Lock()

    def record(self, output_path: Optional[Path] = None) -> Optional[Path]:
        """
        Record audio from the microphone until silence is detected.

        Args:
            output_path: Optional path to save the recording.
                         If None, saves to a temporary file.

        Returns:
            Path to the saved WAV file, or None if recording failed.
        """
        if output_path is None:
            tmp = tempfile.NamedTemporaryFile(
                suffix=".wav", delete=False, prefix="echo_sync_"
            )
            output_path = Path(tmp.name)
            tmp.close()

        self._audio_data = []
        self.silence_detector.reset()
        self._recording = True

        logger.info("Recording started — speak now...")

        try:
            start_time = time.time()

            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="float32",
                blocksize=self.chunk_size,
                callback=self._audio_callback,
            ):
                while self._recording:
                    time.sleep(0.05)  # Small sleep to prevent busy-waiting

                    elapsed = time.time() - start_time

                    # Return an empty recording after the no-speech timeout.
                    if (
                        self.silence_detector.is_only_silence()
                        and elapsed >= self.no_speech_timeout
                    ):
                        logger.info(
                            "No speech within %.0fs — stopping (silence timeout)",
                            self.no_speech_timeout,
                        )
                        self._recording = False
                        break

                    # Do not leave the microphone recording indefinitely.
                    if elapsed >= self.max_duration:
                        logger.warning(
                            "Maximum recording duration (%.0fs) reached",
                            self.max_duration,
                        )
                        self._recording = False
                        break

            if self._audio_data:
                audio_array = np.concatenate(self._audio_data, axis=0)
                sf.write(
                    str(output_path),
                    audio_array,
                    self.sample_rate,
                )
                duration = len(audio_array) / self.sample_rate
                logger.info(
                    "Recording saved: %s (%.2fs)",
                    output_path,
                    duration,
                )
                return output_path
            else:
                logger.warning("No audio data recorded")
                return None

        except sd.PortAudioError as e:
            logger.error("Microphone error: %s", e)
            return None
        except Exception as e:
            logger.error("Recording error: %s", e)
            return None

    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: object,
        status: sd.CallbackFlags,
    ) -> None:
        """Callback for sounddevice InputStream — processes each audio chunk."""
        if status:
            logger.warning("Audio callback status: %s", status)

        with self._lock:
            self._audio_data.append(indata.copy())

            # Silence after speech marks the end of the command.
            if self.silence_detector.process_chunk(indata[:, 0]):
                self._recording = False

    def stop(self) -> None:
        """Manually stop the recording."""
        self._recording = False

    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._recording
