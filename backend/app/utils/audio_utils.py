"""
Audio Utilities for M3 Enhanced
Common audio processing operations and helper functions
"""

import numpy as np
import librosa
import soundfile as sf
import torch
import torchaudio
from pathlib import Path
from typing import Tuple, Optional, Dict, List, Union
import logging
from dataclasses import dataclass
import warnings

# Suppress librosa warnings
warnings.filterwarnings("ignore", category=UserWarning, module="librosa")

logger = logging.getLogger(__name__)

@dataclass
class AudioInfo:
    """Container for audio file information"""
    sample_rate: int
    channels: int
    duration: float
    frames: int
    format: str
    bitrate: Optional[int] = None

class AudioUtils:
    """Comprehensive audio processing utilities"""

    # Standard configurations
    DEFAULT_SAMPLE_RATE = 44100
    DEFAULT_HOP_LENGTH = 512
    DEFAULT_N_FFT = 2048
    MAX_AUDIO_LENGTH = 30 * 60  # 30 minutes max

    @staticmethod
    def load_audio(
        file_path: Union[str, Path],
        target_sr: Optional[int] = None,
        mono: bool = True,
        normalize: bool = True,
        duration: Optional[float] = None,
        offset: float = 0.0
    ) -> Tuple[np.ndarray, int]:
        """
        Load audio file with comprehensive options

        Args:
            file_path: Path to audio file
            target_sr: Target sample rate (None to keep original)
            mono: Convert to mono if True
            normalize: Normalize audio amplitude
            duration: Load only specified duration in seconds
            offset: Start loading from offset seconds

        Returns:
            Tuple of (audio_data, sample_rate)
        """
        try:
            file_path = Path(file_path)

            if not file_path.exists():
                raise FileNotFoundError(f"Audio file not found: {file_path}")

            # Load audio using librosa for flexibility
            audio, sr = librosa.load(
                str(file_path),
                sr=target_sr,
                mono=mono,
                duration=duration,
                offset=offset
            )

            # Validate audio length
            if len(audio) == 0:
                raise ValueError("Loaded audio is empty")

            duration_seconds = len(audio) / sr
            if duration_seconds > AudioUtils.MAX_AUDIO_LENGTH:
                logger.warning(f"Audio duration ({duration_seconds:.1f}s) exceeds maximum ({AudioUtils.MAX_AUDIO_LENGTH}s)")

            # Normalize if requested
            if normalize and len(audio) > 0:
                audio = AudioUtils.normalize_audio(audio)

            logger.debug(f"Loaded audio: {file_path.name} ({duration_seconds:.2f}s, {sr}Hz)")
            return audio, sr

        except Exception as e:
            logger.error(f"Failed to load audio {file_path}: {str(e)}")
            raise

    @staticmethod
    def save_audio(
        audio: np.ndarray,
        file_path: Union[str, Path],
        sample_rate: int,
        format: str = "wav",
        subtype: str = "PCM_24",
        normalize: bool = True
    ) -> Path:
        """
        Save audio to file with high quality settings

        Args:
            audio: Audio data array
            file_path: Output file path
            sample_rate: Audio sample rate
            format: Audio format (wav, flac, etc.)
            subtype: Audio subtype for quality
            normalize: Normalize before saving

        Returns:
            Path to saved file
        """
        try:
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Ensure audio is in correct format
            if audio.dtype != np.float32:
                audio = audio.astype(np.float32)

            # Normalize if requested
            if normalize:
                audio = AudioUtils.normalize_audio(audio)

            # Ensure audio is in valid range
            audio = np.clip(audio, -1.0, 1.0)

            # Save using soundfile for high quality
            sf.write(
                str(file_path),
                audio,
                sample_rate,
                format=format.upper(),
                subtype=subtype
            )

            logger.debug(f"Saved audio: {file_path} ({len(audio)/sample_rate:.2f}s)")
            return file_path

        except Exception as e:
            logger.error(f"Failed to save audio to {file_path}: {str(e)}")
            raise

    @staticmethod
    def get_audio_info(file_path: Union[str, Path]) -> AudioInfo:
        """Get comprehensive audio file information"""
        try:
            file_path = Path(file_path)

            if not file_path.exists():
                raise FileNotFoundError(f"Audio file not found: {file_path}")

            # Use soundfile for detailed info
            info = sf.info(str(file_path))

            return AudioInfo(
                sample_rate=info.samplerate,
                channels=info.channels,
                duration=info.duration,
                frames=info.frames,
                format=info.format,
                bitrate=getattr(info, 'bitrate', None)
            )

        except Exception as e:
            logger.error(f"Failed to get audio info for {file_path}: {str(e)}")
            raise

    @staticmethod
    def normalize_audio(audio: np.ndarray, target_level: float = 0.95) -> np.ndarray:
        """
        Normalize audio to target level

        Args:
            audio: Input audio array
            target_level: Target peak level (0.0 to 1.0)

        Returns:
            Normalized audio array
        """
        if len(audio) == 0:
            return audio

        # Calculate current peak
        current_peak = np.max(np.abs(audio))

        if current_peak > 0:
            # Calculate normalization factor
            norm_factor = target_level / current_peak
            audio = audio * norm_factor

        return audio

    @staticmethod
    def apply_fade(
        audio: np.ndarray,
        sample_rate: int,
        fade_in_duration: float = 0.1,
        fade_out_duration: float = 0.1
    ) -> np.ndarray:
        """
        Apply fade in/out to audio

        Args:
            audio: Input audio array
            sample_rate: Audio sample rate
            fade_in_duration: Fade in duration in seconds
            fade_out_duration: Fade out duration in seconds

        Returns:
            Audio with fades applied
        """
        if len(audio) == 0:
            return audio

        audio = audio.copy()

        # Calculate fade lengths in samples
        fade_in_samples = int(fade_in_duration * sample_rate)
        fade_out_samples = int(fade_out_duration * sample_rate)

        # Apply fade in
        if fade_in_samples > 0 and len(audio) > fade_in_samples:
            fade_in_curve = np.linspace(0, 1, fade_in_samples)
            audio[:fade_in_samples] *= fade_in_curve

        # Apply fade out
        if fade_out_samples > 0 and len(audio) > fade_out_samples:
            fade_out_curve = np.linspace(1, 0, fade_out_samples)
            audio[-fade_out_samples:] *= fade_out_curve

        return audio

    @staticmethod
    def resample_audio(
        audio: np.ndarray,
        original_sr: int,
        target_sr: int,
        quality: str = "high"
    ) -> np.ndarray:
        """
        Resample audio to target sample rate

        Args:
            audio: Input audio array
            original_sr: Original sample rate
            target_sr: Target sample rate
            quality: Resampling quality ('low', 'medium', 'high')

        Returns:
            Resampled audio array
        """
        if original_sr == target_sr:
            return audio

        try:
            # Quality settings for librosa resampling
            quality_map = {
                "low": "scipy",
                "medium": "scipy",
                "high": "soxr_hq"
            }

            res_type = quality_map.get(quality, "soxr_hq")

            resampled = librosa.resample(
                audio,
                orig_sr=original_sr,
                target_sr=target_sr,
                res_type=res_type
            )

            logger.debug(f"Resampled audio from {original_sr}Hz to {target_sr}Hz")
            return resampled

        except Exception as e:
            logger.error(f"Failed to resample audio: {str(e)}")
            raise

    @staticmethod
    def convert_to_mono(audio: np.ndarray) -> np.ndarray:
        """Convert stereo audio to mono"""
        if audio.ndim == 1:
            return audio
        elif audio.ndim == 2:
            return np.mean(audio, axis=0)
        else:
            raise ValueError(f"Unsupported audio dimensions: {audio.ndim}")

    @staticmethod
    def convert_to_stereo(audio: np.ndarray) -> np.ndarray:
        """Convert mono audio to stereo"""
        if audio.ndim == 1:
            return np.stack([audio, audio], axis=0)
        elif audio.ndim == 2:
            return audio
        else:
            raise ValueError(f"Unsupported audio dimensions: {audio.ndim}")

    @staticmethod
    def calculate_rms(audio: np.ndarray, frame_length: int = 2048, hop_length: int = 512) -> np.ndarray:
        """Calculate RMS energy of audio"""
        return librosa.feature.rms(
            y=audio,
            frame_length=frame_length,
            hop_length=hop_length
        )[0]

    @staticmethod
    def calculate_spectral_centroid(
        audio: np.ndarray,
        sample_rate: int,
        hop_length: int = 512
    ) -> np.ndarray:
        """Calculate spectral centroid for brightness analysis"""
        return librosa.feature.spectral_centroid(
            y=audio,
            sr=sample_rate,
            hop_length=hop_length
        )[0]

    @staticmethod
    def detect_tempo(audio: np.ndarray, sample_rate: int) -> Tuple[float, np.ndarray]:
        """
        Detect tempo and beat positions

        Returns:
            Tuple of (tempo_bpm, beat_frames)
        """
        try:
            tempo, beats = librosa.beat.beat_track(
                y=audio,
                sr=sample_rate,
                units='frames'
            )

            return float(tempo), beats

        except Exception as e:
            logger.warning(f"Failed to detect tempo: {str(e)}")
            return 120.0, np.array([])  # Default tempo

    @staticmethod
    def extract_harmonic_percussive(
        audio: np.ndarray,
        margin: float = 1.0
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Separate audio into harmonic and percussive components

        Returns:
            Tuple of (harmonic, percussive)
        """
        try:
            harmonic, percussive = librosa.effects.hpss(
                audio,
                margin=margin
            )

            return harmonic, percussive

        except Exception as e:
            logger.error(f"Failed to extract harmonic/percussive: {str(e)}")
            raise

    @staticmethod
    def apply_pre_emphasis(audio: np.ndarray, coeff: float = 0.97) -> np.ndarray:
        """Apply pre-emphasis filter to audio"""
        if len(audio) <= 1:
            return audio

        return np.append(audio[0], audio[1:] - coeff * audio[:-1])

    @staticmethod
    def remove_silence(
        audio: np.ndarray,
        sample_rate: int,
        threshold_db: float = -40,
        min_duration: float = 0.1
    ) -> Tuple[np.ndarray, List[Tuple[int, int]]]:
        """
        Remove silence from audio

        Returns:
            Tuple of (trimmed_audio, silence_regions)
        """
        try:
            # Detect non-silent regions
            intervals = librosa.effects.split(
                audio,
                top_db=-threshold_db,
                frame_length=2048,
                hop_length=512
            )

            if len(intervals) == 0:
                return audio, []

            # Filter out very short segments
            min_samples = int(min_duration * sample_rate)
            valid_intervals = []

            for start, end in intervals:
                if end - start >= min_samples:
                    valid_intervals.append((start, end))

            if not valid_intervals:
                return audio, []

            # Concatenate non-silent regions
            trimmed_segments = []
            silence_regions = []

            last_end = 0
            for start, end in valid_intervals:
                if start > last_end:
                    silence_regions.append((last_end, start))

                trimmed_segments.append(audio[start:end])
                last_end = end

            if last_end < len(audio):
                silence_regions.append((last_end, len(audio)))

            trimmed_audio = np.concatenate(trimmed_segments) if trimmed_segments else audio

            return trimmed_audio, silence_regions

        except Exception as e:
            logger.warning(f"Failed to remove silence: {str(e)}")
            return audio, []

    @staticmethod
    def calculate_snr(signal: np.ndarray, noise: np.ndarray) -> float:
        """Calculate Signal-to-Noise Ratio in dB"""
        try:
            signal_power = np.mean(signal ** 2)
            noise_power = np.mean(noise ** 2)

            if noise_power == 0:
                return float('inf')

            snr_db = 10 * np.log10(signal_power / noise_power)
            return float(snr_db)

        except Exception as e:
            logger.warning(f"Failed to calculate SNR: {str(e)}")
            return 0.0

    @staticmethod
    def to_torch_tensor(
        audio: np.ndarray,
        device: Optional[torch.device] = None
    ) -> torch.Tensor:
        """Convert numpy audio to torch tensor"""
        tensor = torch.from_numpy(audio).float()

        if device is not None:
            tensor = tensor.to(device)

        return tensor

    @staticmethod
    def from_torch_tensor(tensor: torch.Tensor) -> np.ndarray:
        """Convert torch tensor to numpy audio"""
        return tensor.detach().cpu().numpy()

    @staticmethod
    def validate_audio_array(audio: np.ndarray) -> bool:
        """Validate audio array for common issues"""
        try:
            # Check if array is empty
            if audio.size == 0:
                return False

            # Check for NaN or infinite values
            if not np.isfinite(audio).all():
                return False

            # Check for reasonable amplitude range
            max_amp = np.max(np.abs(audio))
            if max_amp == 0 or max_amp > 100:  # Suspiciously high values
                return False

            return True

        except Exception:
            return False
