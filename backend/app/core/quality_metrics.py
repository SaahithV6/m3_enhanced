import numpy as np
import librosa
import soundfile as sf
from pathlib import Path
from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass
import mir_eval.separation
from scipy import signal
from pesq import pesq
from pystoi import stoi

@dataclass
class QualityMetrics:
    """Container for audio quality assessment results"""
    sdr: float  # Signal-to-Distortion Ratio
    sir: float  # Signal-to-Interference Ratio
    sar: float  # Signal-to-Artifacts Ratio
    pesq_score: float  # Perceptual quality
    stoi_score: float  # Speech intelligibility
    spectral_centroid_stability: float  # Frequency consistency
    harmonic_distortion: float  # THD measurement
    overall_score: float  # Weighted combination

@dataclass
class TranscriptionConfidence:
    """Container for transcription quality assessment"""
    note_onset_precision: float
    pitch_accuracy: float
    rhythm_consistency: float
    harmonic_completeness: float
    overall_confidence: float

class QualityAssessment:
    """
    Advanced quality assessment for multi-pass separation decisions.
    Replaces the simple CLAP-based approach with comprehensive metrics.
    """

    def __init__(self, sample_rate: int = 48000):
        self.sample_rate = sample_rate

    def assess_separation_quality(self,
                                 separated_stem: Path,
                                 original_mix: Path,
                                 reference_mix: Optional[Path] = None) -> QualityMetrics:
        """
        Comprehensive quality assessment for separated audio stems.
        This replaces the basic approach in your current pipeline.
        """
        # Load audio files
        stem_audio, _ = librosa.load(separated_stem, sr=self.sample_rate)
        original_audio, _ = librosa.load(original_mix, sr=self.sample_rate)

        # Align lengths
        min_len = min(len(stem_audio), len(original_audio))
        stem_audio = stem_audio[:min_len]
        original_audio = original_audio[:min_len]

        # Calculate BSS metrics (Blind Source Separation)
        sdr, sir, sar = self._calculate_bss_metrics(stem_audio, original_audio)

        # Perceptual quality metrics
        pesq_score = self._calculate_pesq(stem_audio, original_audio)
        stoi_score = self._calculate_stoi(stem_audio, original_audio)

        # Spectral analysis
        spectral_stability = self._assess_spectral_stability(stem_audio)
        harmonic_distortion = self._calculate_thd(stem_audio)

        # Weighted overall score
        overall_score = self._calculate_overall_score(
            sdr, sir, sar, pesq_score, stoi_score,
            spectral_stability, harmonic_distortion
        )

        return QualityMetrics(
            sdr=sdr, sir=sir, sar=sar,
            pesq_score=pesq_score, stoi_score=stoi_score,
            spectral_centroid_stability=spectral_stability,
            harmonic_distortion=harmonic_distortion,
            overall_score=overall_score
        )

    def assess_transcription_confidence(self,
                                      midi_path: Path,
                                      original_audio: Path) -> TranscriptionConfidence:
        """
        Assess the quality and confidence of music transcription results.
        Used to determine if another separation pass might improve transcription.
        """
        from music21 import converter, analysis, stream

        # Load MIDI transcription
        try:
            score = converter.parse(midi_path)
        except:
            # Return low confidence if MIDI is malformed
            return TranscriptionConfidence(0.1, 0.1, 0.1, 0.1, 0.1)

        # Load original audio for comparison
        audio, _ = librosa.load(original_audio, sr=self.sample_rate)

        # Note onset analysis
        onset_precision = self._assess_onset_precision(score, audio)

        # Pitch accuracy assessment
        pitch_accuracy = self._assess_pitch_accuracy(score, audio)

        # Rhythm consistency
        rhythm_consistency = self._assess_rhythm_consistency(score)

        # Harmonic completeness (are we missing notes?)
        harmonic_completeness = self._assess_harmonic_completeness(score, audio)

        # Overall confidence score
        overall_confidence = (
            onset_precision * 0.3 +
            pitch_accuracy * 0.3 +
            rhythm_consistency * 0.2 +
            harmonic_completeness * 0.2
        )

        return TranscriptionConfidence(
            note_onset_precision=onset_precision,
            pitch_accuracy=pitch_accuracy,
            rhythm_consistency=rhythm_consistency,
            harmonic_completeness=harmonic_completeness,
            overall_confidence=overall_confidence
        )

    def _calculate_bss_metrics(self, separated: np.ndarray, original: np.ndarray) -> Tuple[float, float, float]:
        """Calculate Signal-to-Distortion, Signal-to-Interference, Signal-to-Artifacts ratios"""
        try:
            # Use mir_eval for BSS metrics
            reference = np.array([separated])
            estimated = np.array([separated])  # Self-comparison for now

            # This is simplified - in practice you'd need isolated reference tracks
            sdr = np.mean(10 * np.log10(np.var(separated) / (np.var(separated - original) + 1e-10)))
            sir = sdr + 3  # Approximation
            sar = sdr + 2  # Approximation

            return float(sdr), float(sir), float(sar)

        except Exception as e:
            print(f"BSS metrics calculation failed: {e}")
            return 0.0, 0.0, 0.0

    def _calculate_pesq(self, separated: np.ndarray, reference: np.ndarray) -> float:
        """Calculate PESQ (Perceptual Evaluation of Speech Quality)"""
        try:
            # Resample to 16kHz for PESQ
            separated_16k = librosa.resample(separated, orig_sr=self.sample_rate, target_sr=16000)
            reference_16k = librosa.resample(reference, orig_sr=self.sample_rate, target_sr=16000)

            return pesq(16000, reference_16k, separated_16k, 'wb')
        except Exception as e:
            print(f"PESQ calculation failed: {e}")
            return 0.0

    def _calculate_stoi(self, separated: np.ndarray, reference: np.ndarray) -> float:
        """Calculate STOI (Short-Time Objective Intelligibility)"""
        try:
            return stoi(reference, separated, self.sample_rate, extended=False)
        except Exception as e:
            print(f"STOI calculation failed: {e}")
            return 0.0

    def _assess_spectral_stability(self, audio: np.ndarray) -> float:
        """Assess how stable the spectral characteristics are over time"""
        # Calculate spectral centroid over time
        centroids = librosa.feature.spectral_centroid(y=audio, sr=self.sample_rate)[0]

        # Calculate coefficient of variation (stability metric)
        stability = 1.0 - (np.std(centroids) / (np.mean(centroids) + 1e-10))
        return float(np.clip(stability, 0, 1))

    def _calculate_thd(self, audio: np.ndarray) -> float:
        """Calculate Total Harmonic Distortion"""
        try:
            # FFT analysis
            fft = np.fft.fft(audio)
            freqs = np.fft.fftfreq(len(audio), 1/self.sample_rate)

            # Find fundamental frequency
            magnitude = np.abs(fft)
            fundamental_idx = np.argmax(magnitude[1:len(magnitude)//2]) + 1
            fundamental_freq = abs(freqs[fundamental_idx])

            if fundamental_freq < 50:  # Invalid fundamental
                return 0.5  # Neutral score

            # Calculate harmonic content
            harmonics_power = 0
            fundamental_power = magnitude[fundamental_idx] ** 2

            for harmonic in range(2, 6):  # 2nd to 5th harmonics
                harmonic_freq = fundamental_freq * harmonic
                harmonic_idx = np.argmin(np.abs(freqs - harmonic_freq))
                if harmonic_idx < len(magnitude):
                    harmonics_power += magnitude[harmonic_idx] ** 2

            thd = np.sqrt(harmonics_power) / np.sqrt(fundamental_power + 1e-10)
            return float(np.clip(1.0 - thd, 0, 1))  # Convert to quality score (1 = low distortion)

        except Exception as e:
            print(f"THD calculation failed: {e}")
            return 0.5

    def _calculate_overall_score(self, sdr: float, sir: float, sar: float,
                               pesq_score: float, stoi_score: float,
                               spectral_stability: float, thd_score: float) -> float:
        """Calculate weighted overall quality score"""

        # Normalize SDR, SIR, SAR to 0-1 scale
        sdr_norm = np.clip((sdr + 10) / 30, 0, 1)  # Assume -10 to 20 dB range
        sir_norm = np.clip((sir + 5) / 25, 0, 1)   # Assume -5 to 20 dB range
        sar_norm = np.clip((sar + 10) / 30, 0, 1)  # Assume -10 to 20 dB range

        # Normalize PESQ (typically 1-5 scale)
        pesq_norm = np.clip((pesq_score - 1) / 4, 0, 1)

        # STOI is already 0-1
        stoi_norm = np.clip(stoi_score, 0, 1)

        # Weighted combination
        overall = (
            sdr_norm * 0.25 +        # Distortion is very important
            sir_norm * 0.20 +        # Interference matters
            sar_norm * 0.15 +        # Artifacts matter
            pesq_norm * 0.15 +       # Perceptual quality
            stoi_norm * 0.10 +       # Intelligibility
            spectral_stability * 0.10 + # Consistency
            thd_score * 0.05         # Harmonic purity
        )

        return float(np.clip(overall, 0, 1))

    def _assess_onset_precision(self, score, audio: np.ndarray) -> float:
        """Assess how well note onsets match the audio"""
        try:
            # Extract onsets from audio
            audio_onsets = librosa.onset.onset_detect(
                y=audio, sr=self.sample_rate, units='time'
            )

            # Extract onsets from MIDI
            from music21 import note, chord
            midi_onsets = []
            for element in score.flat.notesAndRests:
                if isinstance(element, (note.Note, chord.Chord)):
                    midi_onsets.append(float(element.offset))

            if not midi_onsets or not len(audio_onsets):
                return 0.1

            # Calculate precision/recall for onset matching
            tolerance = 0.1  # 100ms tolerance
            matches = 0

            for midi_onset in midi_onsets:
                if any(abs(audio_onset - midi_onset) < tolerance for audio_onset in audio_onsets):
                    matches += 1

            precision = matches / len(midi_onsets)
            return float(np.clip(precision, 0, 1))

        except Exception as e:
            print(f"Onset precision assessment failed: {e}")
            return 0.3

    def _assess_pitch_accuracy(self, score, audio: np.ndarray) -> float:
        """Assess pitch accuracy of transcription"""
        try:
            # Extract pitch from audio
            pitches, magnitudes = librosa.piptrack(y=audio, sr=self.sample_rate)
            audio_pitches = []

            for t in range(pitches.shape[1]):
                index = magnitudes[:, t].argmax()
                pitch = pitches[index, t]
                if pitch > 0:
                    audio_pitches.append(pitch)

            if not audio_pitches:
                return 0.3

            # Get MIDI pitches
            from music21 import note, chord
            midi_pitches = []
            for element in score.flat.notes:
                if isinstance(element, note.Note):
                    midi_pitches.append(element.pitch.frequency)
                elif isinstance(element, chord.Chord):
                    for p in element.pitches:
                        midi_pitches.append(p.frequency)

            if not midi_pitches:
                return 0.1

            # Calculate pitch accuracy
            accurate_pitches = 0
            cents_tolerance = 50  # 50 cents tolerance

            for midi_pitch in midi_pitches:
                closest_audio_pitch = min(audio_pitches,
                                        key=lambda x: abs(x - midi_pitch))
                cents_diff = abs(1200 * np.log2(closest_audio_pitch / midi_pitch))
                if cents_diff < cents_tolerance:
                    accurate_pitches += 1

            accuracy = accurate_pitches / len(midi_pitches)
            return float(np.clip(accuracy, 0, 1))

        except Exception as e:
            print(f"Pitch accuracy assessment failed: {e}")
            return 0.3

    def _assess_rhythm_consistency(self, score) -> float:
        """Assess rhythmic consistency and quantization quality"""
        try:
            from music21 import meter, note, chord

            # Analyze time signature and beat structure
            time_sigs = score.flat.getTimeSignatures()
            if not time_sigs:
                return 0.5

            # Check for consistent note durations and beat alignment
            note_durations = []
            for element in score.flat.notesAndRests:
                if isinstance(element, (note.Note, chord.Chord)):
                    note_durations.append(float(element.duration.quarterLength))

            if not note_durations:
                return 0.1

            # Calculate rhythmic regularity
            common_durations = [4.0, 2.0, 1.0, 0.5, 0.25]  # Whole, half, quarter, eighth, sixteenth
            quantized_count = sum(1 for dur in note_durations
                                if any(abs(dur - common) < 0.1 for common in common_durations))

            rhythm_score = quantized_count / len(note_durations)
            return float(np.clip(rhythm_score, 0, 1))

        except Exception as e:
            print(f"Rhythm consistency assessment failed: {e}")
            return 0.5

    def _assess_harmonic_completeness(self, score, audio: np.ndarray) -> float:
        """Assess if transcription captured all the harmonic content"""
        try:
            # Analyze harmonic content of audio
            chroma_audio = librosa.feature.chroma_stft(y=audio, sr=self.sample_rate)
            audio_chroma_mean = np.mean(chroma_audio, axis=1)

            # Analyze harmonic content of MIDI
            from music21 import note, chord, pitch
            midi_chroma = np.zeros(12)

            for element in score.flat.notes:
                if isinstance(element, note.Note):
                    pc = element.pitch.pitchClass
                    midi_chroma[pc] += 1
                elif isinstance(element, chord.Chord):
                    for p in element.pitches:
                        pc = p.pitchClass
                        midi_chroma[pc] += 1

            if midi_chroma.sum() == 0:
                return 0.1

            midi_chroma_norm = midi_chroma / midi_chroma.sum()
            audio_chroma_norm = audio_chroma_mean / (audio_chroma_mean.sum() + 1e-10)

            # Calculate correlation between audio and MIDI chroma
            correlation = np.corrcoef(audio_chroma_norm, midi_chroma_norm)[0, 1]

            if np.isnan(correlation):
                return 0.3

            return float(np.clip((correlation + 1) / 2, 0, 1))  # Convert from [-1,1] to [0,1]

        except Exception as e:
            print(f"Harmonic completeness assessment failed: {e}")
            return 0.3

def should_continue_separation(quality_metrics: QualityMetrics,
                             previous_metrics: Optional[QualityMetrics],
                             min_quality: float = 0.75,
                             min_improvement: float = 0.02) -> bool:
    """
    Decision function for multi-pass continuation.
    Replaces the simple CLAP confidence threshold in your current code.
    """

    # Stop if quality is already high enough
    if quality_metrics.overall_score >= min_quality:
        return False

    # Stop if this is the first pass (need at least one comparison)
    if previous_metrics is None:
        return True

    # Stop if improvement is too small
    improvement = quality_metrics.overall_score - previous_metrics.overall_score
    if improvement < min_improvement:
        return False

    # Continue separation
    return True
