import numpy as np
import librosa
import soundfile as sf
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import scipy.signal
from scipy.ndimage import median_filter
import noisereduce as nr
from pyloudnorm import Meter, normalize
import warnings
warnings.filterwarnings('ignore')

from ..core.config import config
from ..utils.audio_utils import AudioUtils

class AudioEnhancer:
    """
    Studio-grade audio enhancement and preprocessing pipeline.
    Applies professional audio repair and optimization techniques.
    """

    def __init__(self):
        self.sample_rate = config.AUDIO_SAMPLE_RATE
        self.audio_utils = AudioUtils()

        # Enhancement parameters
        self.enhancement_chain = [
            "dc_removal",
            "click_repair",
            "noise_reduction",
            "harmonic_enhancement",
            "dynamic_range_optimization",
            "phase_alignment",
            "spectral_repair"
        ]

        # Audio analysis thresholds
        self.quality_thresholds = {
            "snr_minimum": 20.0,  # dB
            "thd_maximum": 0.05,   # 5% THD
            "dynamic_range_minimum": 12.0,  # dB
            "peak_level_maximum": -1.0,  # dBFS
            "stereo_correlation_minimum": 0.3
        }

    def enhance_audio(self, input_path: Path, job_id: str) -> Path:
        """
        Apply comprehensive studio-grade enhancement to audio file.
        Returns path to enhanced audio file.
        """
        try:
            # Create enhancement directory
            enhance_dir = config.TEMP_DIR / job_id / "enhancement"
            enhance_dir.mkdir(parents=True, exist_ok=True)

            # Load audio with high quality
            audio, sr = librosa.load(
                input_path,
                sr=self.sample_rate,
                mono=False,  # Preserve stereo
                dtype=np.float32
            )

            # Ensure stereo format
            if audio.ndim == 1:
                audio = np.stack([audio, audio])  # Convert mono to stereo

            print(f"Loaded audio: {audio.shape}, Sample rate: {sr}")

            # Analyze original audio quality
            original_metrics = self._analyze_audio_quality(audio, sr)
            print(f"Original quality metrics: {original_metrics}")

            # Apply enhancement chain
            enhanced_audio = audio.copy()

            for step in self.enhancement_chain:
                print(f"Applying {step}...")
                enhanced_audio = self._apply_enhancement_step(
                    enhanced_audio, sr, step, original_metrics
                )

            # Final quality analysis
            final_metrics = self._analyze_audio_quality(enhanced_audio, sr)
            print(f"Enhanced quality metrics: {final_metrics}")

            # Save enhanced audio
            output_path = enhance_dir / f"enhanced_{input_path.stem}.wav"
            sf.write(
                output_path,
                enhanced_audio.T,  # Transpose for soundfile
                sr,
                subtype='PCM_24'  # 24-bit quality
            )

            # Save enhancement report
            self._save_enhancement_report(
                original_metrics, final_metrics, enhance_dir / "enhancement_report.json"
            )

            return output_path

        except Exception as e:
            print(f"Audio enhancement failed: {e}")
            # Return original file if enhancement fails
            return input_path

    def _analyze_audio_quality(self, audio: np.ndarray, sr: int) -> Dict:
        """Comprehensive audio quality analysis"""
        try:
            # Convert to mono for some analyses
            mono_audio = np.mean(audio, axis=0) if audio.ndim == 2 else audio

            # Signal-to-Noise Ratio estimation
            snr = self._estimate_snr(mono_audio)

            # Total Harmonic Distortion
            thd = self._calculate_thd(mono_audio, sr)

            # Dynamic range
            dynamic_range = self._calculate_dynamic_range(mono_audio)

            # Peak levels
            peak_level = 20 * np.log10(np.max(np.abs(audio)) + 1e-10)

            # RMS level
            rms_level = 20 * np.log10(np.sqrt(np.mean(audio**2)) + 1e-10)

            # Stereo correlation (if stereo)
            stereo_correlation = 0.0
            if audio.ndim == 2:
                stereo_correlation = np.corrcoef(audio[0], audio[1])[0, 1]

            # Spectral characteristics
            spectral_centroid = np.mean(librosa.feature.spectral_centroid(y=mono_audio, sr=sr))
            spectral_rolloff = np.mean(librosa.feature.spectral_rolloff(y=mono_audio, sr=sr))
            spectral_bandwidth = np.mean(librosa.feature.spectral_bandwidth(y=mono_audio, sr=sr))

            # Clipping detection
            clipping_percentage = self._detect_clipping(audio)

            return {
                "snr_db": float(snr),
                "thd": float(thd),
                "dynamic_range_db": float(dynamic_range),
                "peak_level_dbfs": float(peak_level),
                "rms_level_dbfs": float(rms_level),
                "stereo_correlation": float(stereo_correlation),
                "spectral_centroid_hz": float(spectral_centroid),
                "spectral_rolloff_hz": float(spectral_rolloff),
                "spectral_bandwidth_hz": float(spectral_bandwidth),
                "clipping_percentage": float(clipping_percentage)
            }

        except Exception as e:
            print(f"Quality analysis failed: {e}")
            return {"error": str(e)}

    def _apply_enhancement_step(self,
                               audio: np.ndarray,
                               sr: int,
                               step: str,
                               original_metrics: Dict) -> np.ndarray:
        """Apply individual enhancement step"""

        try:
            if step == "dc_removal":
                return self._remove_dc_offset(audio)

            elif step == "click_repair":
                return self._repair_clicks_and_pops(audio, sr)

            elif step == "noise_reduction":
                return self._reduce_noise(audio, sr, original_metrics)

            elif step == "harmonic_enhancement":
                return self._enhance_harmonics(audio, sr)

            elif step == "dynamic_range_optimization":
                return self._optimize_dynamic_range(audio, original_metrics)

            elif step == "phase_alignment":
                return self._align_phase(audio)

            elif step == "spectral_repair":
                return self._repair_spectral_artifacts(audio, sr)

            else:
                print(f"Unknown enhancement step: {step}")
                return audio

        except Exception as e:
            print(f"Enhancement step {step} failed: {e}")
            return audio

    def _remove_dc_offset(self, audio: np.ndarray) -> np.ndarray:
        """Remove DC offset using high-pass filtering"""
        try:
            # Design high-pass filter (1 Hz cutoff)
            sos = scipy.signal.butter(
                2, 1.0, btype='highpass',
                fs=self.sample_rate, output='sos'
            )

            if audio.ndim == 2:
                filtered = np.array([
                    scipy.signal.sosfilt(sos, audio[0]),
                    scipy.signal.sosfilt(sos, audio[1])
                ])
            else:
                filtered = scipy.signal.sosfilt(sos, audio)

            return filtered

        except Exception as e:
            print(f"DC removal failed: {e}")
            return audio

    def _repair_clicks_and_pops(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """Repair clicks and pops using median filtering and interpolation"""
        try:
            repaired_audio = audio.copy()

            # Detect clicks using derivative
            if audio.ndim == 2:
                for channel in range(2):
                    repaired_audio[channel] = self._repair_channel_clicks(audio[channel], sr)
            else:
                repaired_audio = self._repair_channel_clicks(audio, sr)

            return repaired_audio

        except Exception as e:
            print(f"Click repair failed: {e}")
            return audio

    def _repair_channel_clicks(self, channel_audio: np.ndarray, sr: int) -> np.ndarray:
        """Repair clicks in single channel"""
        try:
            # Calculate first derivative
            diff = np.diff(channel_audio)

            # Detect sudden changes (clicks)
            threshold = np.std(diff) * 5  # 5 sigma threshold
            click_indices = np.where(np.abs(diff) > threshold)[0]

            if len(click_indices) == 0:
                return channel_audio

            # Repair each click
            repaired = channel_audio.copy()

            for click_idx in click_indices:
                # Define repair window
                start_idx = max(0, click_idx - 10)
                end_idx = min(len(repaired), click_idx + 10)

                # Interpolate over the click
                x = np.arange(start_idx, end_idx)
                mask = np.ones(len(x), dtype=bool)
                mask[click_idx - start_idx:click_idx - start_idx + 2] = False

                if np.sum(mask) >= 2:  # Need at least 2 points for interpolation
                    repaired[click_idx:click_idx + 2] = np.interp(
                        x[~mask], x[mask], repaired[start_idx:end_idx][mask]
                    )

            return repaired

        except Exception as e:
            print(f"Channel click repair failed: {e}")
            return channel_audio

    def _reduce_noise(self, audio: np.ndarray, sr: int, metrics: Dict) -> np.ndarray:
        """Intelligent noise reduction based on SNR analysis"""
        try:
            snr = metrics.get("snr_db", 30)

            # Skip noise reduction if SNR is already good
            if snr > 25:
                return audio

            # Apply spectral subtraction for low SNR
            if audio.ndim == 2:
                reduced = np.array([
                    nr.reduce_noise(y=audio[0], sr=sr, stationary=False),
                    nr.reduce_noise(y=audio[1], sr=sr, stationary=False)
                ])
            else:
                reduced = nr.reduce_noise(y=audio, sr=sr, stationary=False)

            # Blend with original based on SNR
            blend_factor = max(0.1, min(0.8, (30 - snr) / 20))
            enhanced = audio * (1 - blend_factor) + reduced * blend_factor

            return enhanced

        except Exception as e:
            print(f"Noise reduction failed: {e}")
            return audio

    def _enhance_harmonics(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """Enhance harmonic content using exciter algorithms"""
        try:
            enhanced_audio = audio.copy()

            if audio.ndim == 2:
                for channel in range(2):
                    enhanced_audio[channel] = self._enhance_channel_harmonics(audio[channel], sr)
            else:
                enhanced_audio = self._enhance_channel_harmonics(audio, sr)

            return enhanced_audio

        except Exception as e:
            print(f"Harmonic enhancement failed: {e}")
            return audio

    def _enhance_channel_harmonics(self, channel_audio: np.ndarray, sr: int) -> np.ndarray:
        """Enhance harmonics in single channel"""
        try:
            # Generate harmonic excitation
            # High-frequency excitation (presence enhancement)
            sos_high = scipy.signal.butter(
                4, [3000, 8000], btype='bandpass',
                fs=sr, output='sos'
            )
            high_freq = scipy.signal.sosfilt(sos_high, channel_audio)

            # Add subtle harmonic distortion
            excitation = np.tanh(high_freq * 2) * 0.1

            # Blend with original
            enhanced = channel_audio + excitation * 0.05

            return enhanced

        except Exception as e:
            print(f"Channel harmonic enhancement failed: {e}")
            return channel_audio

    def _optimize_dynamic_range(self, audio: np.ndarray, metrics: Dict) -> np.ndarray:
        """Optimize dynamic range using intelligent compression"""
        try:
            current_dr = metrics.get("dynamic_range_db", 20)

            # Skip if dynamic range is already optimal
            if 12 <= current_dr <= 20:
                return audio

            # Apply gentle compression if dynamic range is too high
            if current_dr > 20:
                return self._apply_gentle_compression(audio)

            # Apply expansion if dynamic range is too low
            elif current_dr < 12:
                return self._apply_gentle_expansion(audio)

            return audio

        except Exception as e:
            print(f"Dynamic range optimization failed: {e}")
            return audio

    def _apply_gentle_compression(self, audio: np.ndarray) -> np.ndarray:
        """Apply gentle compression to reduce excessive dynamic range"""
        try:
            # Soft knee compression
            threshold = 0.7
            ratio = 2.0

            compressed_audio = audio.copy()

            if audio.ndim == 2:
                for channel in range(2):
                    channel_data = audio[channel]
                    # Apply compression to loud parts
                    mask = np.abs(channel_data) > threshold
                    compressed_audio[channel][mask] = (
                        np.sign(channel_data[mask]) * threshold +
                        (np.abs(channel_data[mask]) - threshold) / ratio
                    )
            else:
                mask = np.abs(audio) > threshold
                compressed_audio[mask] = (
                    np.sign(audio[mask]) * threshold +
                    (np.abs(audio[mask]) - threshold) / ratio
                )

            return compressed_audio

        except Exception as e:
            print(f"Compression failed: {e}")
            return audio

    def _apply_gentle_expansion(self, audio: np.ndarray) -> np.ndarray:
        """Apply gentle expansion to increase dynamic range"""
        try:
            # Gentle upward expansion
            threshold = 0.1
            ratio = 1.5

            expanded_audio = audio.copy()

            if audio.ndim == 2:
                for channel in range(2):
                    channel_data = audio[channel]
                    # Apply expansion to quiet parts
                    mask = np.abs(channel_data) < threshold
                    expanded_audio[channel][mask] = channel_data[mask] * ratio
            else:
                mask = np.abs(audio) < threshold
                expanded_audio[mask] = audio[mask] * ratio

            return expanded_audio

        except Exception as e:
            print(f"Expansion failed: {e}")
            return audio

    def _align_phase(self, audio: np.ndarray) -> np.ndarray:
        """Correct phase alignment issues in stereo audio"""
        try:
            if audio.ndim != 2:
                return audio  # Phase alignment only for stereo

            # Calculate cross-correlation to find phase offset
            correlation = scipy.signal.correlate(audio[0], audio[1], mode='full')
            lag = np.argmax(correlation) - (len(audio[1]) - 1)

            # Only correct small phase shifts (< 100 samples)
            if abs(lag) < 100 and lag != 0:
                aligned_audio = audio.copy()

                if lag > 0:
                    # Delay left channel
                    aligned_audio[0] = np.roll(audio[0], lag)
                    aligned_audio[0][:lag] = 0
                else:
                    # Delay right channel
                    aligned_audio[1] = np.roll(audio[1], -lag)
                    aligned_audio[1][lag:] = 0

                return aligned_audio

            return audio

        except Exception as e:
            print(f"Phase alignment failed: {e}")
            return audio

    def _repair_spectral_artifacts(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """Repair spectral artifacts and dropouts"""
        try:
            repaired_audio = audio.copy()

            if audio.ndim == 2:
                for channel in range(2):
                    repaired_audio[channel] = self._repair_channel_spectral(audio[channel], sr)
            else:
                repaired_audio = self._repair_channel_spectral(audio, sr)

            return repaired_audio

        except Exception as e:
            print(f"Spectral repair failed: {e}")
            return audio

    def _repair_channel_spectral(self, channel_audio: np.ndarray, sr: int) -> np.ndarray:
        """Repair spectral artifacts in single channel"""
        try:
            # STFT for frequency domain processing
            stft = librosa.stft(channel_audio, n_fft=2048, hop_length=512)
            magnitude = np.abs(stft)
            phase = np.angle(stft)

            # Detect and interpolate spectral gaps
            # Look for frequency bins with abnormally low energy
            freq_energy = np.mean(magnitude, axis=1)
            median_energy = np.median(freq_energy)

            # Find problematic frequency bins
            threshold = median_energy * 0.1
            problem_bins = freq_energy < threshold

            if np.any(problem_bins):
                # Interpolate missing frequencies
                good_bins = ~problem_bins
                good_indices = np.where(good_bins)[0]
                problem_indices = np.where(problem_bins)[0]

                for time_frame in range(magnitude.shape[1]):
                    if len(good_indices) >= 2:
                        magnitude[problem_indices, time_frame] = np.interp(
                            problem_indices, good_indices,
                            magnitude[good_indices, time_frame]
                        )

            # Reconstruct audio
            repaired_stft = magnitude * np.exp(1j * phase)
            repaired_audio = librosa.istft(repaired_stft, hop_length=512)

            return repaired_audio

        except Exception as e:
            print(f"Channel spectral repair failed: {e}")
            return channel_audio

    # Quality analysis helper methods
    def _estimate_snr(self, audio: np.ndarray) -> float:
        """Estimate Signal-to-Noise Ratio"""
        try:
            # Simple SNR estimation using noise floor detection
            # Sort magnitude values and use bottom 10% as noise estimate
            magnitude = np.abs(audio)
            sorted_mag = np.sort(magnitude)
            noise_level = np.mean(sorted_mag[:int(len(sorted_mag) * 0.1)])
            signal_level = np.mean(sorted_mag[int(len(sorted_mag) * 0.5):])

            snr_linear = signal_level / (noise_level + 1e-10)
            snr_db = 20 * np.log10(snr_linear + 1e-10)

            return float(np.clip(snr_db, 0, 60))

        except Exception:
            return 25.0  # Default reasonable SNR

    def _calculate_thd(self, audio: np.ndarray, sr: int) -> float:
        """Calculate Total Harmonic Distortion"""
        try:
            # FFT analysis
            fft = np.fft.fft(audio[:sr])  # Analyze first second
            freqs = np.fft.fftfreq(len(fft), 1/sr)
            magnitude = np.abs(fft)

            # Find fundamental frequency
            positive_freqs = freqs[:len(freqs)//2]
            positive_mag = magnitude[:len(magnitude)//2]

            # Look for peak in reasonable frequency range (80-2000 Hz)
            valid_range = (positive_freqs >= 80) & (positive_freqs <= 2000)
            if not np.any(valid_range):
                return 0.01  # Very low THD if no fundamental found

            fund_idx = np.argmax(positive_mag[valid_range])
            fund_freq = positive_freqs[valid_range][fund_idx]
            fund_magnitude = positive_mag[valid_range][fund_idx]

            # Calculate harmonic powers
            harmonic_power = 0
            for harmonic in range(2, 6):  # 2nd to 5th harmonics
                harm_freq = fund_freq * harmonic
                if harm_freq < sr/2:  # Within Nyquist limit
                    harm_idx = np.argmin(np.abs(positive_freqs - harm_freq))
                    harmonic_power += positive_mag[harm_idx] ** 2

            fundamental_power = fund_magnitude ** 2
            thd = np.sqrt(harmonic_power) / np.sqrt(fundamental_power + 1e-10)

            return float(np.clip(thd, 0, 1))

        except Exception:
            return 0.02  # Default low THD

    def _calculate_dynamic_range(self, audio: np.ndarray) -> float:
        """Calculate dynamic range in dB"""
        try:
            # RMS over sliding windows
            window_size = 4096
            hop_size = 2048

            rms_values = []
            for i in range(0, len(audio) - window_size, hop_size):
                window = audio[i:i + window_size]
                rms = np.sqrt(np.mean(window**2))
                if rms > 1e-6:  # Avoid log of zero
                    rms_values.append(rms)

            if len(rms_values) < 2:
                return 20.0  # Default dynamic range

            rms_db = 20 * np.log10(np.array(rms_values))
            dynamic_range = np.max(rms_db) - np.min(rms_db)

            return float(np.clip(dynamic_range, 0, 60))

        except Exception:
            return 20.0  # Default dynamic range

    def _detect_clipping(self, audio: np.ndarray) -> float:
        """Detect clipping percentage"""
        try:
            # Find samples at or near maximum value
            threshold = 0.99  # 99% of full scale
            clipped_samples = np.sum(np.abs(audio) >= threshold)
            total_samples = audio.size

            clipping_percentage = (clipped_samples / total_samples) * 100
            return float(clipping_percentage)

        except Exception:
            return 0.0

    def _save_enhancement_report(self,
                                original_metrics: Dict,
                                final_metrics: Dict,
                                report_path: Path):
        """Save enhancement report"""
        try:
            import json

            report = {
                "enhancement_timestamp": str(datetime.utcnow()),
                "original_metrics": original_metrics,
                "final_metrics": final_metrics,
                "improvements": {},
                "enhancement_chain": self.enhancement_chain
            }

            # Calculate improvements
            for key in original_metrics:
                if key in final_metrics and isinstance(original_metrics[key], (int, float)):
                    improvement = final_metrics[key] - original_metrics[key]
                    report["improvements"][key] = improvement

            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)

        except Exception as e:
            print(f"Failed to save enhancement report: {e}")

# Global enhancer instance
audio_enhancer = AudioEnhancer()
