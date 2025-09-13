import numpy as np
import librosa
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from scipy import signal
from sklearn.cluster import KMeans
import warnings
warnings.filterwarnings('ignore')

class LeadRhythmAnalyzer:
    """
    Advanced analysis to distinguish between lead and rhythm guitar parts.
    Uses spectral, temporal, and harmonic features to classify guitar roles.
    """

    def __init__(self):
        self.sample_rate = 22050

        # Feature thresholds for classification
        self.lead_guitar_indicators = {
            'high_frequency_content': 0.7,      # Lead guitars often in higher register
            'note_density_variation': 0.6,      # Lead has more varied note density
            'spectral_centroid_height': 2000,   # Hz, lead typically brighter
            'harmonic_complexity': 0.4,         # Lead often more harmonically complex
            'sustained_note_ratio': 0.3,        # Lead has more sustained notes
            'bend_detection_score': 0.5         # Lead guitars use more bends
        }

    def classify_guitar_part(self, audio_path: Path) -> Optional[str]:
        """
        Classify guitar audio as lead, rhythm, or acoustic.
        Returns: 'lead_guitar', 'rhythm_guitar', 'acoustic_guitar', or None
        """
        try:
            # Load audio
            audio, sr = librosa.load(audio_path, sr=self.sample_rate, duration=60)

            if len(audio) < self.sample_rate:  # Too short to analyze
                return None

            # Extract comprehensive features
            features = self._extract_guitar_features(audio)

            # Classify based on features
            classification = self._classify_from_features(features)

            return classification

        except Exception as e:
            print(f"Guitar classification failed: {e}")
            return None

    def _extract_guitar_features(self, audio: np.ndarray) -> Dict[str, float]:
        """Extract comprehensive features for guitar classification"""
        features = {}

        # 1. Spectral Features
        spectral_features = self._extract_spectral_features(audio)
        features.update(spectral_features)

        # 2. Temporal Features
        temporal_features = self._extract_temporal_features(audio)
        features.update(temporal_features)

        # 3. Harmonic Features
        harmonic_features = self._extract_harmonic_features(audio)
        features.update(harmonic_features)

        # 4. Guitar-specific Features
        guitar_features = self._extract_guitar_specific_features(audio)
        features.update(guitar_features)

        return features

    def _extract_spectral_features(self, audio: np.ndarray) -> Dict[str, float]:
        """Extract spectral characteristics"""
        # Compute spectrograms
        stft = librosa.stft(audio, n_fft=2048, hop_length=512)
        magnitude = np.abs(stft)

        # Spectral centroid (brightness)
        spectral_centroid = librosa.feature.spectral_centroid(
            y=audio, sr=self.sample_rate
        )[0]

        # Spectral rolloff (frequency distribution)
        spectral_rolloff = librosa.feature.spectral_rolloff(
            y=audio, sr=self.sample_rate, roll_percent=0.85
        )[0]

        # Spectral bandwidth (spread)
        spectral_bandwidth = librosa.feature.spectral_bandwidth(
            y=audio, sr=self.sample_rate
        )[0]

        # High frequency content (above 2kHz)
        freqs = librosa.fft_frequencies(sr=self.sample_rate, n_fft=2048)
        high_freq_mask = freqs > 2000
        high_freq_energy = np.mean(np.sum(magnitude[high_freq_mask, :], axis=0))
        total_energy = np.mean(np.sum(magnitude, axis=0))
        high_freq_ratio = high_freq_energy / (total_energy + 1e-10)

        return {
            'spectral_centroid_mean': float(np.mean(spectral_centroid)),
            'spectral_centroid_std': float(np.std(spectral_centroid)),
            'spectral_rolloff_mean': float(np.mean(spectral_rolloff)),
            'spectral_bandwidth_mean': float(np.mean(spectral_bandwidth)),
            'high_frequency_ratio': float(high_freq_ratio)
        }

    def _extract_temporal_features(self, audio: np.ndarray) -> Dict[str, float]:
        """Extract temporal characteristics"""
        # Onset detection
        onset_frames = librosa.onset.onset_detect(
            y=audio, sr=self.sample_rate, units='frames'
        )
        onset_times = librosa.frames_to_time(onset_frames, sr=self.sample_rate)

        # Note density analysis
        if len(onset_times) > 1:
            inter_onset_intervals = np.diff(onset_times)
            note_density = len(onset_times) / (len(audio) / self.sample_rate)
            note_density_variation = np.std(inter_onset_intervals)
        else:
            note_density = 0
            note_density_variation = 0

        # RMS energy analysis
        rms = librosa.feature.rms(y=audio, frame_length=2048, hop_length=512)[0]
        rms_variation = np.std(rms)

        # Sustained note detection (low RMS variation indicates sustain)
        sustained_sections = np.where(rms > np.mean(rms) * 0.7)[0]
        sustained_ratio = len(sustained_sections) / len(rms)

        return {
            'note_density': float(note_density),
            'note_density_variation': float(note_density_variation),
            'rms_variation': float(rms_variation),
            'sustained_note_ratio': float(sustained_ratio),
            'onset_count': len(onset_times)
        }

    def _extract_harmonic_features(self, audio: np.ndarray) -> Dict[str, float]:
        """Extract harmonic and pitch-related features"""
        # Harmonic-percussive separation
        harmonic, percussive = librosa.effects.hpss(audio)

        # Harmonic ratio
        harmonic_energy = np.sum(harmonic ** 2)
        total_energy = np.sum(audio ** 2)
        harmonic_ratio = harmonic_energy / (total_energy + 1e-10)

        # Chroma features (harmonic content)
        chroma = librosa.feature.chroma_stft(y=audio, sr=self.sample_rate)
        chroma_variation = np.std(chroma, axis=1)
        harmonic_complexity = np.mean(chroma_variation)

        # Pitch stability
        pitches, magnitudes = librosa.piptrack(y=audio, sr=self.sample_rate)
        pitch_stability = self._calculate_pitch_stability(pitches, magnitudes)

        return {
            'harmonic_ratio': float(harmonic_ratio),
            'harmonic_complexity': float(harmonic_complexity),
            'pitch_stability': float(pitch_stability)
        }

    def _extract_guitar_specific_features(self, audio: np.ndarray) -> Dict[str, float]:
        """Extract guitar-specific features like bends, vibrato, etc."""
        # String bend detection
        bend_score = self._detect_string_bends(audio)

        # Vibrato detection
        vibrato_score = self._detect_vibrato(audio)

        # Palm muting detection (for rhythm guitar)
        palm_mute_score = self._detect_palm_muting(audio)

        # Chord vs single note analysis
        chord_probability = self._estimate_chord_probability(audio)

        return {
            'bend_detection_score': float(bend_score),
            'vibrato_score': float(vibrato_score),
            'palm_mute_score': float(palm_mute_score),
            'chord_probability': float(chord_probability)
        }

    def _detect_string_bends(self, audio: np.ndarray) -> float:
        """Detect guitar string bends (common in lead guitar)"""
        try:
            # Extract pitch over time
            pitches, magnitudes = librosa.piptrack(y=audio, sr=self.sample_rate)

            # Find dominant pitch at each time frame
            pitch_curve = []
            for t in range(pitches.shape[1]):
                index = magnitudes[:, t].argmax()
                pitch = pitches[index, t]
                if pitch > 0:
                    pitch_curve.append(pitch)
                else:
                    pitch_curve.append(0)

            if len(pitch_curve) < 10:
                return 0.0

            pitch_curve = np.array(pitch_curve)
            valid_pitches = pitch_curve[pitch_curve > 0]

            if len(valid_pitches) < 5:
                return 0.0

            # Detect rapid pitch changes (bends)
            pitch_diff = np.abs(np.diff(valid_pitches))

            # Bends typically show gradual pitch changes > 50 cents
            bend_threshold = 50  # cents
            rapid_changes = pitch_diff > bend_threshold

            bend_score = np.sum(rapid_changes) / len(pitch_diff)
            return min(bend_score, 1.0)

        except Exception:
            return 0.0

    def _detect_vibrato(self, audio: np.ndarray) -> float:
        """Detect vibrato (pitch modulation)"""
        try:
            # Extract pitch
            pitches, magnitudes = librosa.piptrack(y=audio, sr=self.sample_rate)

            # Calculate pitch modulation frequency
            pitch_curve = []
            for t in range(pitches.shape[1]):
                index = magnitudes[:, t].argmax()
                pitch = pitches[index, t]
                if pitch > 0:
                    pitch_curve.append(pitch)

            if len(pitch_curve) < 20:
                return 0.0

            pitch_curve = np.array(pitch_curve)

            # Look for periodic modulation (vibrato typically 4-7 Hz)
            from scipy.fft import fft, fftfreq

            # Remove DC component
            pitch_curve = pitch_curve - np.mean(pitch_curve)

            # FFT to find modulation frequency
            fft_vals = fft(pitch_curve)
            freqs = fftfreq(len(pitch_curve), 1/self.sample_rate)

            # Look for peaks in vibrato frequency range
            vibrato_range = (freqs >= 4) & (freqs <= 7)
            vibrato_power = np.sum(np.abs(fft_vals[vibrato_range]))
            total_power = np.sum(np.abs(fft_vals))

            vibrato_score = vibrato_power / (total_power + 1e-10)
            return min(vibrato_score, 1.0)

        except Exception:
            return 0.0

    def _detect_palm_muting(self, audio: np.ndarray) -> float:
        """Detect palm muting (common in rhythm guitar)"""
        try:
            # Palm muting reduces high frequencies and creates percussive attack

            # High frequency attenuation
            stft = librosa.stft(audio)
            magnitude = np.abs(stft)
            freqs = librosa.fft_frequencies(sr=self.sample_rate)

            low_freq_mask = freqs < 1000
            high_freq_mask = freqs > 2000

            low_energy = np.mean(np.sum(magnitude[low_freq_mask, :], axis=0))
            high_energy = np.mean(np.sum(magnitude[high_freq_mask, :], axis=0))

            # Palm muting has high low/high frequency ratio
            freq_ratio = low_energy / (high_energy + 1e-10)

            # Sharp attack detection
            onset_strength = librosa.onset.onset_strength(y=audio, sr=self.sample_rate)
            attack_sharpness = np.mean(np.diff(onset_strength))

            # Combine features
            palm_mute_score = (freq_ratio * 0.7 + attack_sharpness * 0.3)
            return min(palm_mute_score / 10, 1.0)  # Normalize

        except Exception:
            return 0.0

    def _estimate_chord_probability(self, audio: np.ndarray) -> float:
        """Estimate probability that audio contains chords vs single notes"""
        try:
            # Chroma analysis for harmonic content
            chroma = librosa.feature.chroma_stft(y=audio, sr=self.sample_rate)

            # Count simultaneous notes
            simultaneous_notes = np.sum(chroma > 0.5, axis=0)
            avg_simultaneous = np.mean(simultaneous_notes)

            # Chord probability increases with number of simultaneous notes
            chord_prob = min(avg_simultaneous / 4.0, 1.0)  # Normalize to 0-1

            return chord_prob

        except Exception:
            return 0.0

    def _calculate_pitch_stability(self, pitches: np.ndarray, magnitudes: np.ndarray) -> float:
        """Calculate pitch stability over time"""
        try:
            # Extract dominant pitch curve
            pitch_curve = []
            for t in range(pitches.shape[1]):
                index = magnitudes[:, t].argmax()
                pitch = pitches[index, t]
                if pitch > 0:
                    pitch_curve.append(pitch)

            if len(pitch_curve) < 5:
                return 0.0

            pitch_curve = np.array(pitch_curve)

            # Calculate coefficient of variation (lower = more stable)
            cv = np.std(pitch_curve) / (np.mean(pitch_curve) + 1e-10)

            # Convert to stability score (higher = more stable)
            stability = 1.0 / (1.0 + cv)

            return stability

        except Exception:
            return 0.0

    def _classify_from_features(self, features: Dict[str, float]) -> Optional[str]:
        """Classify guitar type based on extracted features"""

        # Calculate scores for each guitar type
        lead_score = 0
        rhythm_score = 0
        acoustic_score = 0

        # Lead guitar indicators
        if features.get('spectral_centroid_mean', 0) > 2000:
            lead_score += 2
        if features.get('high_frequency_ratio', 0) > 0.3:
            lead_score += 2
        if features.get('bend_detection_score', 0) > 0.3:
            lead_score += 3
        if features.get('vibrato_score', 0) > 0.2:
            lead_score += 2
        if features.get('sustained_note_ratio', 0) > 0.4:
            lead_score += 1
        if features.get('note_density_variation', 0) > 0.5:
            lead_score += 1

        # Rhythm guitar indicators
        if features.get('chord_probability', 0) > 0.6:
            rhythm_score += 3
        if features.get('palm_mute_score', 0) > 0.3:
            rhythm_score += 2
        if features.get('note_density', 0) > 4:  # Many notes (strumming)
            rhythm_score += 2
        if features.get('harmonic_complexity', 0) < 0.3:
            rhythm_score += 1
        if features.get('rms_variation', 0) > 0.1:  # Dynamic strumming
            rhythm_score += 1

        # Acoustic guitar indicators
        if features.get('harmonic_ratio', 0) > 0.7:
            acoustic_score += 2
        if features.get('spectral_centroid_mean', 0) < 1500:
            acoustic_score += 1
        if features.get('chord_probability', 0) > 0.5:
            acoustic_score += 1

        # Make decision based on highest score
        max_score = max(lead_score, rhythm_score, acoustic_score)

        if max_score < 3:  # Not confident enough
            return "rhythm_guitar"  # Default to rhythm

        if lead_score == max_score:
            return "lead_guitar"
        elif rhythm_score == max_score:
            return "rhythm_guitar"
        else:
            return "acoustic_guitar"

# Global analyzer instance
lead_rhythm_analyzer = LeadRhythmAnalyzer()
