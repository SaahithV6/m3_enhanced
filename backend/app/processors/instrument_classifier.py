import numpy as np
import librosa
import tensorflow as tf
from pathlib import Path
from typing import List, Dict, Tuple
import warnings
warnings.filterwarnings('ignore')

from ..models.model_manager import model_manager
from ..core.config import config

class InstrumentClassifier:
    """
    Advanced instrument classification focused specifically on musical instruments.
    Uses YAMNet with music-focused filtering and custom instrument detection models.
    """

    def __init__(self):
        self.yamnet_model = None
        self.openl3_model = None

        # Music-only class mapping from YAMNet AudioSet classes
        self.music_class_mapping = {
            # String Instruments
            440: "acoustic_guitar",      # Guitar
            441: "lead_guitar",          # Electric guitar
            442: "bass",                 # Bass guitar
            443: "acoustic_guitar",      # Acoustic guitar
            444: "lead_guitar",          # Steel guitar, slide guitar
            446: "rhythm_guitar",        # Strum
            447: "acoustic_guitar",      # Banjo
            448: "acoustic_guitar",      # Sitar
            449: "acoustic_guitar",      # Mandolin
            450: "acoustic_guitar",      # Zither
            451: "acoustic_guitar",      # Ukulele

            # Keyboard Instruments
            452: "piano",                # Keyboard (musical)
            453: "piano",                # Piano
            454: "piano",                # Electric piano
            455: "synthesizer",          # Organ
            456: "synthesizer",          # Electronic organ
            457: "synthesizer",          # Hammond organ
            458: "synthesizer",          # Synthesizer
            459: "synthesizer",          # Sampler
            460: "piano",                # Harpsichord

            # Percussion
            461: "drums",                # Percussion
            462: "drums",                # Drum kit
            463: "drums",                # Drum machine
            464: "drums",                # Drum
            465: "drums",                # Snare drum
            466: "drums",                # Rimshot
            467: "drums",                # Drum roll
            468: "drums",                # Bass drum
            469: "drums",                # Timpani
            470: "drums",                # Tabla
            471: "drums",                # Cymbal
            472: "drums",                # Hi-hat
            473: "drums",                # Wood block
            474: "drums",                # Tambourine
            475: "drums",                # Rattle (instrument)
            476: "drums",                # Maraca
            477: "drums",                # Gong
            478: "drums",                # Tubular bells
            479: "drums",                # Mallet percussion
            480: "piano",                # Marimba, xylophone
            481: "piano",                # Glockenspiel
            482: "piano",                # Vibraphone
            483: "drums",                # Steelpan

            # Orchestral/Wind
            484: "brass",                # Orchestra
            485: "brass",                # Brass instrument
            486: "brass",                # French horn
            487: "brass",                # Trumpet
            488: "brass",                # Trombone
            489: "brass",                # Bugle
            490: "brass",                # Cornet
            491: "brass",                # Saxophone
            492: "woodwind",             # Clarinet
            493: "woodwind",             # Flute
            494: "woodwind",             # Recorder
            495: "woodwind",             # Ocarina
            496: "woodwind",             # Bagpipes
            497: "woodwind",             # Harmonica
            498: "woodwind",             # Accordion

            # Bowed Strings
            499: "strings",              # Bowed string instrument
            500: "strings",              # Violin, fiddle
            501: "strings",              # Pizzicato
            502: "strings",              # Cello
            503: "bass",                 # Double bass
            504: "strings",              # String section
            505: "strings",              # Harp

            # Vocals
            23: "vocals",                # Singing
            24: "vocals",                # Choir
            25: "vocals",                # Yodeling
            26: "vocals",                # Chant
            27: "vocals",                # Mantra
            28: "vocals",                # Male singing
            29: "vocals",                # Female singing
            30: "vocals",                # Child singing
            31: "vocals",                # Synthetic singing
            32: "vocals",                # Rapping
            33: "vocals",                # Humming
        }

        # Spectral signature patterns for each instrument type
        self.spectral_signatures = {
            "lead_guitar": {
                "freq_range": (80, 4000),
                "formant_peaks": [200, 400, 800, 1600],
                "harmonic_richness": 0.7,
                "attack_sharpness": 0.8
            },
            "rhythm_guitar": {
                "freq_range": (80, 3000),
                "formant_peaks": [150, 300, 600, 1200],
                "harmonic_richness": 0.6,
                "attack_sharpness": 0.9
            },
            "acoustic_guitar": {
                "freq_range": (80, 2500),
                "formant_peaks": [100, 200, 400, 800],
                "harmonic_richness": 0.8,
                "attack_sharpness": 0.6
            },
            "bass": {
                "freq_range": (40, 300),
                "formant_peaks": [60, 120, 240],
                "harmonic_richness": 0.5,
                "attack_sharpness": 0.7
            },
            "piano": {
                "freq_range": (27, 4200),
                "formant_peaks": [100, 300, 900, 2700],
                "harmonic_richness": 0.9,
                "attack_sharpness": 0.95
            },
            "vocals": {
                "freq_range": (80, 1200),
                "formant_peaks": [350, 900, 2300, 3200],
                "harmonic_richness": 0.4,
                "attack_sharpness": 0.3
            },
            "drums": {
                "freq_range": (20, 8000),
                "formant_peaks": [60, 200, 800, 3000],
                "harmonic_richness": 0.2,
                "attack_sharpness": 0.99
            },
            "synthesizer": {
                "freq_range": (20, 8000),
                "formant_peaks": [200, 600, 1800, 5400],
                "harmonic_richness": 0.8,
                "attack_sharpness": 0.5
            }
        }

    def classify_instruments(self,
                           audio_path: Path,
                           confidence_threshold: float = 0.25) -> List[str]:
        """
        Classify instruments present in an audio file using multiple approaches.
        Returns list of detected instruments above confidence threshold.
        """
        try:
            # Load audio
            audio, sr = librosa.load(audio_path, sr=22050, duration=30)

            if len(audio) < sr:  # Less than 1 second
                return self._fallback_classification(audio_path)

            # Multi-modal classification
            yamnet_results = self._classify_with_yamnet(audio)
            spectral_results = self._classify_with_spectral_analysis(audio)
            harmonic_results = self._classify_with_harmonic_analysis(audio)

            # Combine results with weighted voting
            combined_scores = self._combine_classification_results(
                yamnet_results, spectral_results, harmonic_results
            )

            # Filter by confidence threshold
            detected_instruments = [
                instrument for instrument, score in combined_scores.items()
                if score >= confidence_threshold
            ]

            # Post-processing: resolve conflicts and add context
            final_instruments = self._post_process_detections(
                detected_instruments, combined_scores, audio_path
            )

            return final_instruments if final_instruments else ["other"]

        except Exception as e:
            print(f"Instrument classification failed: {e}")
            return self._fallback_classification(audio_path)

    def _classify_with_yamnet(self, audio: np.ndarray) -> Dict[str, float]:
        """Classify using YAMNet with music-focused filtering"""
        try:
            # Resample for YAMNet (expects 16kHz)
            audio_16k = librosa.resample(audio, orig_sr=22050, target_sr=16000)

            # Load YAMNet
            with model_manager.model_context("yamnet") as yamnet_model:
                if yamnet_model is None:
                    return {}

                # Convert to tensor
                waveform = tf.cast(audio_16k, tf.float32)

                # Get predictions
                scores, embeddings, spectrogram = yamnet_model(waveform)

                # Average scores across time
                mean_scores = tf.reduce_mean(scores, axis=0).numpy()

                # Map to our instrument categories
                instrument_scores = {}

                for class_idx, score in enumerate(mean_scores):
                    if class_idx in self.music_class_mapping:
                        instrument = self.music_class_mapping[class_idx]
                        current_score = instrument_scores.get(instrument, 0)
                        instrument_scores[instrument] = max(current_score, float(score))

                return instrument_scores

        except Exception as e:
            print(f"YAMNet classification failed: {e}")
            return {}

    def _classify_with_spectral_analysis(self, audio: np.ndarray) -> Dict[str, float]:
        """Classify using custom spectral signature matching"""
        try:
            # Compute spectral features
            stft = librosa.stft(audio, n_fft=2048, hop_length=512)
            magnitude = np.abs(stft)
            freqs = librosa.fft_frequencies(sr=22050, n_fft=2048)

            # Get spectral centroid, rolloff, bandwidth
            spectral_centroid = librosa.feature.spectral_centroid(y=audio, sr=22050)[0]
            spectral_rolloff = librosa.feature.spectral_rolloff(y=audio, sr=22050)[0]
            spectral_bandwidth = librosa.feature.spectral_bandwidth(y=audio, sr=22050)[0]

            # Calculate power spectral density
            psd = np.mean(magnitude, axis=1)

            instrument_scores = {}

            # Match against each instrument's spectral signature
            for instrument, signature in self.spectral_signatures.items():
                score = self._calculate_spectral_similarity(
                    freqs, psd, spectral_centroid, spectral_rolloff,
                    spectral_bandwidth, signature
                )
                instrument_scores[instrument] = score

            return instrument_scores

        except Exception as e:
            print(f"Spectral analysis failed: {e}")
            return {}

    def _classify_with_harmonic_analysis(self, audio: np.ndarray) -> Dict[str, float]:
        """Classify using harmonic content analysis"""
        try:
            # Harmonic-percussive separation
            harmonic, percussive = librosa.effects.hpss(audio)

            # Pitch analysis
            pitches, magnitudes = librosa.piptrack(y=audio, sr=22050)

            # Chroma features
            chroma = librosa.feature.chroma_stft(y=audio, sr=22050)

            # Zero crossing rate
            zcr = librosa.feature.zero_crossing_rate(audio)[0]

            # Onset detection
            onset_frames = librosa.onset.onset_detect(y=audio, sr=22050)
            onset_times = librosa.frames_to_time(onset_frames, sr=22050)

            instrument_scores = {}

            # Analyze harmonic characteristics for each instrument
            for instrument in self.spectral_signatures.keys():
                score = self._calculate_harmonic_score(
                    harmonic, percussive, chroma, zcr, onset_times, instrument
                )
                instrument_scores[instrument] = score

            return instrument_scores

        except Exception as e:
            print(f"Harmonic analysis failed: {e}")
            return {}

    def _calculate_spectral_similarity(self, freqs, psd, centroid, rolloff, bandwidth, signature):
        """Calculate similarity to instrument spectral signature"""
        try:
            # Frequency range matching
            freq_min, freq_max = signature["freq_range"]
            freq_mask = (freqs >= freq_min) & (freqs <= freq_max)

            if not np.any(freq_mask):
                return 0.0

            # Energy in frequency range
            range_energy = np.sum(psd[freq_mask])
            total_energy = np.sum(psd)
            range_ratio = range_energy / (total_energy + 1e-10)

            # Spectral centroid matching
            expected_centroid = np.mean(signature["formant_peaks"])
            centroid_error = abs(np.mean(centroid) - expected_centroid) / expected_centroid
            centroid_score = max(0, 1 - centroid_error)

            # Harmonic richness (bandwidth relative to centroid)
            richness = np.mean(bandwidth) / (np.mean(centroid) + 1e-10)
            expected_richness = signature["harmonic_richness"]
            richness_error = abs(richness - expected_richness) / expected_richness
            richness_score = max(0, 1 - richness_error)

            # Combined score
            similarity = (range_ratio * 0.4 + centroid_score * 0.4 + richness_score * 0.2)

            return min(similarity, 1.0)

        except Exception:
            return 0.0

    def _calculate_harmonic_score(self, harmonic, percussive, chroma, zcr, onset_times, instrument):
        """Calculate harmonic characteristics score for instrument"""
        try:
            # Harmonic vs percussive ratio
            harmonic_energy = np.sum(harmonic ** 2)
            percussive_energy = np.sum(percussive ** 2)
            total_energy = harmonic_energy + percussive_energy

            if total_energy == 0:
                return 0.0

            harmonic_ratio = harmonic_energy / total_energy

            # Instrument-specific scoring
            if instrument == "drums":
                # Drums should be more percussive
                score = (1 - harmonic_ratio) * 0.7

                # Add onset density (drums have many onsets)
                if len(onset_times) > 1:
                    onset_density = len(onset_times) / (onset_times[-1] - onset_times[0] + 1e-10)
                    score += min(onset_density / 10, 0.3)  # Normalize

            elif instrument in ["lead_guitar", "rhythm_guitar", "acoustic_guitar"]:
                # Guitars should be moderately harmonic
                ideal_harmonic_ratio = 0.6
                harmonic_error = abs(harmonic_ratio - ideal_harmonic_ratio)
                score = max(0, 1 - harmonic_error * 2)

                # Check for guitar-like chroma patterns
                chroma_variation = np.std(chroma, axis=1)
                guitar_chroma_score = np.mean(chroma_variation)
                score = score * 0.7 + guitar_chroma_score * 0.3

            elif instrument == "piano":
                # Piano should be very harmonic with sharp attacks
                score = harmonic_ratio * 0.8

                # Check for piano-like onset patterns
                if len(onset_times) > 1:
                    onset_regularity = 1 / (np.std(np.diff(onset_times)) + 1e-10)
                    score += min(onset_regularity / 100, 0.2)

            elif instrument == "vocals":
                # Vocals should be harmonic but with specific formant structure
                score = harmonic_ratio * 0.6

                # Low zero-crossing rate indicates pitched content
                avg_zcr = np.mean(zcr)
                if avg_zcr < 0.1:  # Low ZCR indicates pitched content
                    score += 0.4

            elif instrument == "bass":
                # Bass should be harmonic with low frequency emphasis
                score = harmonic_ratio * 0.8

                # Check frequency distribution (bass should be low)
                # This would require frequency analysis which we approximate
                score += 0.2  # Placeholder

            else:  # synthesizer, brass, woodwind, strings
                score = harmonic_ratio * 0.7 + 0.3

            return min(score, 1.0)

        except Exception:
            return 0.0

    def _combine_classification_results(self, yamnet_results, spectral_results, harmonic_results):
        """Combine results from multiple classifiers with weighted voting"""
        combined_scores = {}
        all_instruments = set()

        # Collect all detected instruments
        all_instruments.update(yamnet_results.keys())
        all_instruments.update(spectral_results.keys())
        all_instruments.update(harmonic_results.keys())

        # Weighted combination
        yamnet_weight = 0.5      # YAMNet is primary
        spectral_weight = 0.3    # Spectral analysis is secondary
        harmonic_weight = 0.2    # Harmonic analysis is tertiary

        for instrument in all_instruments:
            yamnet_score = yamnet_results.get(instrument, 0)
            spectral_score = spectral_results.get(instrument, 0)
            harmonic_score = harmonic_results.get(instrument, 0)

            combined_score = (
                yamnet_score * yamnet_weight +
                spectral_score * spectral_weight +
                harmonic_score * harmonic_weight
            )

            combined_scores[instrument] = combined_score

        return combined_scores

    def _post_process_detections(self, detected_instruments, scores, audio_path):
        """Post-process detections to resolve conflicts and add context"""
        if not detected_instruments:
            return []

        # Sort by confidence
        sorted_instruments = sorted(
            detected_instruments,
            key=lambda x: scores[x],
            reverse=True
        )

        final_instruments = []

        # Resolve guitar conflicts
        guitar_types = [inst for inst in sorted_instruments if "guitar" in inst]
        if guitar_types:
            # Only keep the highest-scoring guitar type
            final_instruments.append(guitar_types[0])

            # Add lead/rhythm analysis if it's electric guitar
            if guitar_types[0] in ["lead_guitar", "rhythm_guitar"]:
                try:
                    from .lead_rhythm_analyzer import LeadRhythmAnalyzer
                    analyzer = LeadRhythmAnalyzer()
                    refined_type = analyzer.classify_guitar_part(audio_path)
                    if refined_type:
                        final_instruments[-1] = refined_type
                except Exception:
                    pass

        # Add non-guitar instruments
        non_guitar = [inst for inst in sorted_instruments if "guitar" not in inst]
        final_instruments.extend(non_guitar[:3])  # Maximum 3 additional instruments

        return final_instruments

    def _fallback_classification(self, audio_path: Path) -> List[str]:
        """Fallback classification based on filename and basic audio analysis"""
        filename = audio_path.stem.lower()

        # Filename-based detection
        if any(word in filename for word in ["vocal", "voice", "sing"]):
            return ["vocals"]
        elif any(word in filename for word in ["guitar", "gtr"]):
            return ["rhythm_guitar"]
        elif any(word in filename for word in ["bass", "low"]):
            return ["bass"]
        elif any(word in filename for word in ["drum", "kick", "snare", "hat"]):
            return ["drums"]
        elif any(word in filename for word in ["piano", "key", "synth"]):
            return ["piano"]
        elif "other" in filename:
            return ["synthesizer"]
        else:
            # Try basic audio analysis
            try:
                audio, sr = librosa.load(audio_path, sr=22050, duration=10)

                # Very basic frequency analysis
                spectral_centroid = np.mean(librosa.feature.spectral_centroid(y=audio, sr=sr))

                if spectral_centroid < 500:
                    return ["bass"]
                elif spectral_centroid > 2000:
                    return ["lead_guitar"]
                else:
                    return ["rhythm_guitar"]

            except Exception:
                return ["other"]

# Global classifier instance
instrument_classifier = InstrumentClassifier()
