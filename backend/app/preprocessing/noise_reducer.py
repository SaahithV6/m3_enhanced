import numpy as np
import librosa
import scipy.signal
import scipy.ndimage
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import soundfile as sf
from sklearn.decomposition import FastICA
import noisereduce as nr
import warnings
warnings.filterwarnings('ignore')

from ..core.config import config
from ..utils.audio_utils import AudioUtils

class NoiseReducer:
    """
    Advanced noise reduction and audio repair system.
    Implements multiple algorithms for different types of noise and artifacts.
    """

    def __init__(self):
        self.sample_rate = config.AUDIO_SAMPLE_RATE
        self.audio_utils = AudioUtils()

        # Noise reduction algorithms
        self.algorithms = {
            "spectral_subtraction": self._spectral_subtraction,
            "wiener_filtering": self._wiener_filtering,
            "ica_separation": self._ica_noise_separation,
            "adaptive_filtering": self._adaptive_filtering,
            "median_filtering": self._median_filtering,
            "wavelet_denoising": self._wavelet_denoising
        }

        # Noise types and their optimal algorithms
        self.noise_type_algorithms = {
            "white_noise": ["spectral_subtraction", "wiener_filtering"],
            "pink_noise": ["spectral_subtraction", "adaptive_filtering"],
            "hum_buzz": ["notch_filtering", "adaptive_filtering"],
            "clicks_pops": ["median_filtering", "interpolation"],
            "background_noise": ["ica_separation", "spectral_subtraction"],
            "wind_noise": ["spectral_subtraction", "wavelet_denoising"],
            "compression_artifacts": ["wiener_filtering", "adaptive_filtering"]
        }

    def reduce_noise(self,
                    input_path: Path,
                    job_id: str,
                    noise_type: str = "auto",
                    reduction_strength: float = 0.5) -> Path:
        """
        Apply comprehensive noise reduction to audio file.

        Args:
            input_path: Input audio file path
            job_id: Job ID for temporary files
            noise_type: Type of noise ('auto', 'white_noise', 'pink_noise', etc.)
            reduction_strength: Reduction strength (0.0 to 1.0)

        Returns:
            Path to noise-reduced audio file
        """
        try:
            # Create noise reduction directory
            nr_dir = config.TEMP_DIR / job_id / "noise_reduction"
            nr_dir.mkdir(parents=True, exist_ok=True)

            # Load audio
            audio, sr = librosa.load(input_path, sr=self.sample_rate, mono=False)

            # Ensure stereo format
            if audio.ndim == 1:
                audio = np.stack([audio, audio])

            print(f"Loaded audio for noise reduction: {audio.shape}")

            # Analyze noise characteristics
            if noise_type == "auto":
                detected_noise_type = self._detect_noise_type(audio, sr)
                print(f"Detected noise type: {detected_noise_type}")
            else:
                detected_noise_type = noise_type

            # Apply appropriate noise reduction algorithms
            reduced_audio = self._apply_noise_reduction_chain(
                audio, sr, detected_noise_type, reduction_strength
            )

            # Save processed audio
            output_path = nr_dir / f"denoised_{input_path.stem}.wav"
            sf.write(
                output_path,
                reduced_audio.T,  # Transpose for soundfile
                sr,
                subtype='PCM_24'
            )

            # Generate noise reduction report
            self._save_noise_reduction_report(
                audio, reduced_audio, detected_noise_type, nr_dir / "noise_report.json"
            )

            return output_path

        except Exception as e:
            print(f"Noise reduction failed: {e}")
            return input_path

    def _detect_noise_type(self, audio: np.ndarray, sr: int) -> str:
        """Automatically detect dominant noise type"""
        try:
            # Convert to mono for analysis
            mono_audio = np.mean(audio, axis=0) if audio.ndim == 2 else audio

            # Spectral analysis
            stft = librosa.stft(mono_audio, n_fft=2048, hop_length=512)
            magnitude = np.abs(stft)

            # Frequency characteristics
            freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)

            # Calculate power spectral density
            psd = np.mean(magnitude, axis=1)

            # Analyze spectral characteristics
            noise_indicators = {}

            # 1. White noise detection (flat spectrum)
            spectral_flatness = self._calculate_spectral_flatness(psd)
            noise_indicators['white_noise'] = spectral_flatness

            # 2. Pink noise detection (1/f slope)
            pink_slope_score = self._detect_pink_noise_slope(freqs, psd)
            noise_indicators['pink_noise'] = pink_slope_score

            # 3. Hum/buzz detection (power line frequencies)
            hum_score = self._detect_hum_buzz(freqs, psd)
            noise_indicators['hum_buzz'] = hum_score

            # 4. Click/pop detection (transient analysis)
            clicks_score = self._detect_clicks_pops(mono_audio)
            noise_indicators['clicks_pops'] = clicks_score

            # 5. Background noise detection (energy distribution)
            background_score = self._detect_background_noise(magnitude)
            noise_indicators['background_noise'] = background_score

            # 6. Wind noise detection (low-frequency modulation)
            wind_score = self._detect_wind_noise(mono_audio, sr)
            noise_indicators['wind_noise'] = wind_score

            # Select dominant noise type
            dominant_noise = max(noise_indicators, key=noise_indicators.get)
            max_score = noise_indicators[dominant_noise]

            # Return detected type if confidence is high enough
            if max_score > 0.3:
                return dominant_noise
            else:
                return "background_noise"  # Default

        except Exception as e:
            print(f"Noise detection failed: {e}")
            return "background_noise"

    def _calculate_spectral_flatness(self, psd: np.ndarray) -> float:
        """Calculate spectral flatness (indicator of white noise)"""
        try:
            # Geometric mean / arithmetic mean
            geometric_mean = np.exp(np.mean(np.log(psd + 1e-10)))
            arithmetic_mean = np.mean(psd)

            flatness = geometric_mean / (arithmetic_mean + 1e-10)
            return float(flatness)

        except Exception:
            return 0.0

    def _detect_pink_noise_slope(self, freqs: np.ndarray, psd: np.ndarray) -> float:
        """Detect 1/f slope characteristic of pink noise"""
        try:
            # Focus on mid-frequency range
            mid_freq_mask = (freqs >= 100) & (freqs <= 8000)
            mid_freqs = freqs[mid_freq_mask]
            mid_psd = psd[mid_freq_mask]

            if len(mid_freqs) < 10:
                return 0.0

            # Fit line in log-log space
            log_freqs = np.log10(mid_freqs + 1e-10)
            log_psd = np.log10(mid_psd + 1e-10)

            # Linear regression
            slope, intercept = np.polyfit(log_freqs, log_psd, 1)

            # Pink noise has slope around -1
            pink_score = max(0, 1 - abs(slope + 1))

            return float(pink_score)

        except Exception:
            return 0.0

    def _detect_hum_buzz(self, freqs: np.ndarray, psd: np.ndarray) -> float:
        """Detect power line hum and harmonics"""
        try:
            hum_freqs = [50, 60, 100, 120, 150, 180]  # Common hum frequencies
            hum_score = 0.0

            for hum_freq in hum_freqs:
                # Find closest frequency bin
                freq_idx = np.argmin(np.abs(freqs - hum_freq))

                # Check if there's a peak at this frequency
                window_size = 5
                start_idx = max(0, freq_idx - window_size)
                end_idx = min(len(psd), freq_idx + window_size)

                local_psd = psd[start_idx:end_idx]
                center_idx = freq_idx - start_idx

                if center_idx < len(local_psd):
                    peak_ratio = local_psd[center_idx] / (np.mean(local_psd) + 1e-10)
                    if peak_ratio > 2.0:  # Significant peak
                        hum_score += 0.2

            return min(hum_score, 1.0)

        except Exception:
            return 0.0

    def _detect_clicks_pops(self, audio: np.ndarray) -> float:
        """Detect clicks and pops using derivative analysis"""
        try:
            # Calculate first derivative
            diff = np.diff(audio)

            # Detect sudden changes
            threshold = np.std(diff) * 5
            clicks = np.sum(np.abs(diff) > threshold)

            # Normalize by audio length
            clicks_per_second = clicks / (len(audio) / self.sample_rate)

            # Score based on click density
            click_score = min(clicks_per_second / 10, 1.0)

            return float(click_score)

        except Exception:
            return 0.0

    def _detect_background_noise(self, magnitude: np.ndarray) -> float:
        """Detect persistent background noise"""
        try:
            # Calculate energy stability over time
            energy_over_time = np.sum(magnitude, axis=0)

            # Background noise shows consistent energy
            energy_std = np.std(energy_over_time)
            energy_mean = np.mean(energy_over_time)

            consistency_ratio = energy_mean / (energy_std + 1e-10)
            background_score = min(consistency_ratio / 100, 1.0)

            return float(background_score)

        except Exception:
            return 0.0

    def _detect_wind_noise(self, audio: np.ndarray, sr: int) -> float:
        """Detect wind noise characteristics"""
        try:
            # Wind noise shows low-frequency modulation
            # Extract low-frequency envelope
            sos = scipy.signal.butter(4, 100, btype='lowpass', fs=sr, output='sos')
            low_freq = scipy.signal.sosfilt(sos, audio)

            # Calculate modulation depth
            envelope = np.abs(librosa.stft(low_freq, n_fft=1024, hop_length=256))
            modulation = np.std(np.mean(envelope, axis=0))

            # Normalize and score
            wind_score = min(modulation * 10, 1.0)

            return float(wind_score)

        except Exception:
            return 0.0

    def _apply_noise_reduction_chain(self,
                                   audio: np.ndarray,
                                   sr: int,
                                   noise_type: str,
                                   strength: float) -> np.ndarray:
        """Apply chain of noise reduction algorithms"""
        try:
            processed_audio = audio.copy()

            # Get appropriate algorithms for detected noise type
            algorithms = self.noise_type_algorithms.get(
                noise_type, ["spectral_subtraction", "adaptive_filtering"]
            )

            print(f"Applying noise reduction algorithms: {algorithms}")

            # Apply each algorithm in sequence
            for algorithm_name in algorithms:
                if algorithm_name in self.algorithms:
                    print(f"Applying {algorithm_name}...")
                    processed_audio = self.algorithms[algorithm_name](
                        processed_audio, sr, strength
                    )
                elif algorithm_name == "notch_filtering":
                    processed_audio = self._notch_filtering(processed_audio, sr)
                elif algorithm_name == "interpolation":
                    processed_audio = self._interpolation_repair(processed_audio, sr)

            # Blend with original based on strength
            final_audio = audio * (1 - strength) + processed_audio * strength

            return final_audio

        except Exception as e:
            print(f"Noise reduction chain failed: {e}")
            return audio

    def _spectral_subtraction(self, audio: np.ndarray, sr: int, strength: float) -> np.ndarray:
        """Spectral subtraction noise reduction"""
        try:
            processed_audio = np.zeros_like(audio)

            for channel in range(audio.shape[0]):
                # Use noisereduce library for spectral subtraction
                reduced = nr.reduce_noise(
                    y=audio[channel],
                    sr=sr,
                    stationary=False,
                    prop_decrease=strength
                )
                processed_audio[channel] = reduced

            return processed_audio

        except Exception as e:
            print(f"Spectral subtraction failed: {e}")
            return audio

    def _wiener_filtering(self, audio: np.ndarray, sr: int, strength: float) -> np.ndarray:
        """Wiener filtering for noise reduction"""
        try:
            processed_audio = np.zeros_like(audio)

            for channel in range(audio.shape[0]):
                # STFT
                stft = librosa.stft(audio[channel], n_fft=2048, hop_length=512)
                magnitude = np.abs(stft)
                phase = np.angle(stft)

                # Estimate noise power (use quiet sections)
                noise_power = self._estimate_noise_power(magnitude)

                # Wiener filter
                signal_power = magnitude ** 2
                wiener_gain = signal_power / (signal_power + noise_power * strength)

                # Apply filter
                filtered_magnitude = magnitude * wiener_gain
                filtered_stft = filtered_magnitude * np.exp(1j * phase)

                # ISTFT
                processed_audio[channel] = librosa.istft(filtered_stft, hop_length=512)

            return processed_audio

        except Exception as e:
            print(f"Wiener filtering failed: {e}")
            return audio

    def _ica_noise_separation(self, audio: np.ndarray, sr: int, strength: float) -> np.ndarray:
        """Independent Component Analysis for noise separation"""
        try:
            if audio.shape[0] < 2:
                return audio  # Need at least 2 channels for ICA

            # Apply ICA
            ica = FastICA(n_components=2, random_state=42, max_iter=1000)

            # Transpose for ICA (samples x features)
            audio_t = audio.T

            # Fit and transform
            sources = ica.fit_transform(audio_t)

            # Identify noise component (typically the one with higher variance)
            source_vars = np.var(sources, axis=0)
            noise_component = np.argmax(source_vars)

            # Reduce noise component
            sources[:, noise_component] *= (1 - strength)

            # Transform back
            recovered = ica.inverse_transform(sources)

            return recovered.T

        except Exception as e:
            print(f"ICA noise separation failed: {e}")
            return audio

    def _adaptive_filtering(self, audio: np.ndarray, sr: int, strength: float) -> np.ndarray:
        """Adaptive filtering for noise reduction"""
        try:
            processed_audio = np.zeros_like(audio)

            for channel in range(audio.shape[0]):
                # Simple LMS adaptive filter
                signal = audio[channel]
                filtered_signal = self._lms_filter(signal, strength)
                processed_audio[channel] = filtered_signal

            return processed_audio

        except Exception as e:
            print(f"Adaptive filtering failed: {e}")
            return audio

    def _lms_filter(self, signal: np.ndarray, strength: float) -> np.ndarray:
        """Least Mean Squares adaptive filter"""
        try:
            filter_length = 32
            mu = 0.01 * strength  # Learning rate

            # Initialize filter weights
            weights = np.zeros(filter_length)
            filtered_signal = np.zeros_like(signal)

            for n in range(filter_length, len(signal)):
                # Input vector
                x = signal[n-filter_length:n][::-1]  # Reverse for convolution

                # Filter output
                y = np.dot(weights, x)

                # Error (desired - actual)
                error = signal[n] - y

                # Update weights
                weights += mu * error * x

                # Output
                filtered_signal[n] = y

            return filtered_signal

        except Exception as e:
            print(f"LMS filter failed: {e}")
            return signal

    def _median_filtering(self, audio: np.ndarray, sr: int, strength: float) -> np.ndarray:
        """Median filtering for click and pop removal"""
        try:
            processed_audio = np.zeros_like(audio)

            # Kernel size based on strength
            kernel_size = int(3 + strength * 6)  # 3 to 9 samples
            if kernel_size % 2 == 0:
                kernel_size += 1  # Ensure odd kernel size

            for channel in range(audio.shape[0]):
                # Apply median filter
                filtered = scipy.ndimage.median_filter(audio[channel], size=kernel_size)

                # Blend with original
                processed_audio[channel] = audio[channel] * (1 - strength) + filtered * strength

            return processed_audio

        except Exception as e:
            print(f"Median filtering failed: {e}")
            return audio

    def _wavelet_denoising(self, audio: np.ndarray, sr: int, strength: float) -> np.ndarray:
        """Wavelet denoising (simplified implementation)"""
        try:
            # Note: This is a simplified version. Full implementation would use PyWavelets
            processed_audio = np.zeros_like(audio)

            for channel in range(audio.shape[0]):
                # Simple high-frequency attenuation as wavelet denoising approximation
                # Low-pass filter with cutoff based on strength
                cutoff_freq = 8000 * (1 - strength * 0.5)  # Reduce high frequencies

                sos = scipy.signal.butter(
                    4, cutoff_freq, btype='lowpass', fs=sr, output='sos'
                )
                filtered = scipy.signal.sosfilt(sos, audio[channel])

                processed_audio[channel] = filtered

            return processed_audio

        except Exception as e:
            print(f"Wavelet denoising failed: {e}")
            return audio

    def _notch_filtering(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """Notch filtering for hum removal"""
        try:
            processed_audio = audio.copy()

            # Common hum frequencies to filter
            hum_freqs = [50, 60, 100, 120]

            for freq in hum_freqs:
                if freq < sr / 2:  # Within Nyquist limit
                    # Design notch filter
                    Q = 30  # Quality factor
                    w0 = freq / (sr / 2)  # Normalized frequency

                    b, a = scipy.signal.iirnotch(w0, Q)

                    # Apply to each channel
                    for channel in range(audio.shape[0]):
                        processed_audio[channel] = scipy.signal.filtfilt(
                            b, a, processed_audio[channel]
                        )

            return processed_audio

        except Exception as e:
            print(f"Notch filtering failed: {e}")
            return audio

    def _interpolation_repair(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """Interpolation-based repair for clicks and dropouts"""
        try:
            processed_audio = audio.copy()

            for channel in range(audio.shape[0]):
                signal = audio[channel]

                # Detect outliers (clicks/pops)
                threshold = np.std(signal) * 4
                outliers = np.abs(signal) > threshold

                if np.any(outliers):
                    # Interpolate over outliers
                    indices = np.arange(len(signal))
                    good_indices = indices[~outliers]
                    outlier_indices = indices[outliers]

                    if len(good_indices) >= 2:
                        interpolated_values = np.interp(
                            outlier_indices, good_indices, signal[good_indices]
                        )
                        processed_audio[channel][outliers] = interpolated_values

            return processed_audio

        except Exception as e:
            print(f"Interpolation repair failed: {e}")
            return audio

    def _estimate_noise_power(self, magnitude: np.ndarray) -> np.ndarray:
        """Estimate noise power from magnitude spectrogram"""
        try:
            # Use minimum statistics to estimate noise
            # Sort each frequency bin and use lower percentile as noise estimate
            noise_power = np.zeros(magnitude.shape[0])

            for freq_bin in range(magnitude.shape[0]):
                sorted_mag = np.sort(magnitude[freq_bin, :])
                # Use 10th percentile as noise estimate
                noise_idx = int(len(sorted_mag) * 0.1)
                noise_power[freq_bin] = sorted_mag[noise_idx] ** 2

            return noise_power.reshape(-1, 1)  # Broadcast shape

        except Exception:
            return np.ones((magnitude.shape[0], 1)) * 0.01

    def _save_noise_reduction_report(self,
                                   original: np.ndarray,
                                   processed: np.ndarray,
                                   noise_type: str,
                                   report_path: Path):
        """Save noise reduction analysis report"""
        try:
            import json
            from datetime import datetime

            # Calculate improvement metrics
            original_snr = self._calculate_snr(original)
            processed_snr = self._calculate_snr(processed)

            original_energy = np.mean(original ** 2)
            processed_energy = np.mean(processed ** 2)

            report = {
                "timestamp": datetime.utcnow().isoformat(),
                "detected_noise_type": noise_type,
                "original_snr_db": float(original_snr),
                "processed_snr_db": float(processed_snr),
                "snr_improvement_db": float(processed_snr - original_snr),
                "original_energy": float(original_energy),
                "processed_energy": float(processed_energy),
                "energy_reduction_db": float(10 * np.log10(processed_energy / original_energy)),
                "algorithms_applied": self.noise_type_algorithms.get(noise_type, [])
            }

            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)

        except Exception as e:
            print(f"Failed to save noise reduction report: {e}")

    def _calculate_snr(self, audio: np.ndarray) -> float:
        """Calculate SNR estimate"""
        try:
            mono_audio = np.mean(audio, axis=0) if audio.ndim == 2 else audio

            # Simple SNR estimation
            signal_power = np.var(mono_audio)

            # Estimate noise as low-energy sections
            sorted_samples = np.sort(np.abs(mono_audio))
            noise_samples = sorted_samples[:len(sorted_samples)//4]  # Bottom 25%
            noise_power = np.var(noise_samples)

            snr_linear = signal_power / (noise_power + 1e-10)
            snr_db = 10 * np.log10(snr_linear + 1e-10)

            return float(np.clip(snr_db, 0, 60))

        except Exception:
            return 25.0

# Global noise reducer instance
noise_reducer = NoiseReducer()
