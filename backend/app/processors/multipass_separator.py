import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import numpy as np
import librosa
import soundfile as sf

from ..core.config import config
from ..core.quality_metrics import QualityAssessment, QualityMetrics, should_continue_separation
from ..models.model_manager import model_manager
from .instrument_classifier import InstrumentClassifier

@dataclass
class SeparationPass:
    """Results from a single separation pass"""
    pass_number: int
    stems: Dict[str, Path]  # instrument_name -> file_path
    quality_metrics: Dict[str, QualityMetrics]
    detected_instruments: List[str]
    processing_time: float

class MultiPassSeparator:
    """
    Advanced multi-pass separation engine that replaces your current single-pass approach.
    Uses iterative refinement with quality assessment to achieve maximum accuracy.
    """

    def __init__(self):
        self.quality_assessor = QualityAssessment(sample_rate=config.AUDIO_SAMPLE_RATE)
        self.instrument_classifier = InstrumentClassifier()

    def separate_audio_multipass(self,
                               audio_path: Path,
                               job_id: str,
                               callback) -> Dict[str, Path]:
        """
        Main multi-pass separation orchestrator.
        This completely replaces your current run_full_pipeline logic.
        """
        callback("Starting advanced multi-pass separation...")

        # Create working directories
        work_dir = config.TEMP_DIR / job_id / "separation"
        work_dir.mkdir(parents=True, exist_ok=True)

        separation_passes = []
        current_stems = {"full_mix": audio_path}
        pass_number = 1

        while pass_number <= config.MAX_SEPARATION_PASSES:
            callback(f"Pass {pass_number}: Analyzing and separating audio...")

            # Execute separation pass
            pass_result = self._execute_separation_pass(
                current_stems, work_dir, pass_number, callback
            )
            separation_passes.append(pass_result)

            # Assess quality and decide whether to continue
            should_continue = self._should_continue_separation(
                pass_result, separation_passes, callback
            )

            if not should_continue:
                callback(f"Separation converged after {pass_number} passes")
                break

            # Prepare for next pass - identify stems needing refinement
            current_stems = self._prepare_next_pass_stems(pass_result, callback)

            if not current_stems:
                callback("No stems require further refinement")
                break

            pass_number += 1

        # Consolidate final results
        final_stems = self._consolidate_final_stems(separation_passes, work_dir)
        callback(f"Multi-pass separation completed with {len(final_stems)} stems")

        return final_stems

    def _execute_separation_pass(self,
                               input_stems: Dict[str, Path],
                               work_dir: Path,
                               pass_number: int,
                               callback) -> SeparationPass:
        """Execute a single separation pass on the input stems"""
        import time
        start_time = time.time()

        pass_dir = work_dir / f"pass_{pass_number}"
        pass_dir.mkdir(exist_ok=True)

        all_stems = {}
        all_quality_metrics = {}
        all_detected_instruments = []

        for stem_name, stem_path in input_stems.items():
            callback(f"Pass {pass_number}: Processing {stem_name}...")

            # Choose separation strategy based on pass number and stem content
            if pass_number == 1 and stem_name == "full_mix":
                # Pass 1: Broad separation with Demucs
                stems, detected = self._broad_separation_demucs(stem_path, pass_dir)
            else:
                # Pass 2+: Targeted separation based on classification
                stems, detected = self._targeted_separation(stem_path, stem_name, pass_dir, callback)

            all_stems.update(stems)
            all_detected_instruments.extend(detected)

            # Assess quality of each separated stem
            for new_stem_name, new_stem_path in stems.items():
                quality = self.quality_assessor.assess_separation_quality(
                    new_stem_path, stem_path
                )
                all_quality_metrics[new_stem_name] = quality

        processing_time = time.time() - start_time

        return SeparationPass(
            pass_number=pass_number,
            stems=all_stems,
            quality_metrics=all_quality_metrics,
            detected_instruments=list(set(all_detected_instruments)),
            processing_time=processing_time
        )

    def _broad_separation_demucs(self, audio_path: Path, output_dir: Path) -> Tuple[Dict[str, Path], List[str]]:
        """Pass 1: Broad separation using Demucs htdemucs"""
        with model_manager.model_context("demucs_htdemucs"):
            # Run Demucs separation
            subprocess.run([
                "python", "-m", "demucs.separate",
                "-n", "htdemucs",
                "-o", str(output_dir),
                str(audio_path)
            ], check=True, capture_output=True)

            # Collect separated stems
            stems_dir = output_dir / "htdemucs" / audio_path.stem
            stems = {}
            detected_instruments = []

            for stem_file in stems_dir.glob("*.wav"):
                stem_name = stem_file.stem
                stems[stem_name] = stem_file
                detected_instruments.append(stem_name)

            return stems, detected_instruments

    def _targeted_separation(self,
                           audio_path: Path,
                           stem_name: str,
                           output_dir: Path,
                           callback) -> Tuple[Dict[str, Path], List[str]]:
        """Pass 2+: Targeted separation based on instrument classification"""

        # First, classify what instruments are in this stem
        detected_instruments = self.instrument_classifier.classify_instruments(
            audio_path, confidence_threshold=config.INSTRUMENT_CONFIDENCE_THRESHOLD
        )

        callback(f"Detected instruments in {stem_name}: {detected_instruments}")

        # If only one instrument detected, no further separation needed
        if len(detected_instruments) <= 1:
            return {stem_name: audio_path}, detected_instruments

        # Multiple instruments detected - use targeted separation
        return self._separate_multiple_instruments(
            audio_path, detected_instruments, output_dir, callback
        )

    def _separate_multiple_instruments(self,
                                     audio_path: Path,
                                     instruments: List[str],
                                     output_dir: Path,
                                     callback) -> Tuple[Dict[str, Path], List[str]]:
        """Separate audio containing multiple instruments"""

        # Use MVSEP-MDX23 for high-quality targeted separation
        try:
            with model_manager.model_context("mvsep_mdx23") as separator:
                if separator is None:
                    # Fallback to Demucs 6-source
                    return self._fallback_separation_demucs_6s(audio_path, output_dir)

                # Configure separator for specific instruments
                stems = {}

                # Process each instrument type
                for instrument in instruments:
                    output_path = output_dir / f"{instrument}.wav"

                    try:
                        # Run audio-separator with specific model for this instrument
                        separator.separate(str(audio_path), str(output_path))

                        if output_path.exists():
                            stems[instrument] = output_path

                    except Exception as e:
                        callback(f"Failed to separate {instrument}: {e}")
                        continue

                return stems, instruments

        except Exception as e:
            callback(f"MVSEP separation failed: {e}. Using fallback.")
            return self._fallback_separation_demucs_6s(audio_path, output_dir)

    def _fallback_separation_demucs_6s(self, audio_path: Path, output_dir: Path) -> Tuple[Dict[str, Path], List[str]]:
        """Fallback separation using Demucs 6-source model"""
        try:
            with model_manager.model_context("demucs_htdemucs_6s"):
                subprocess.run([
                    "python", "-m", "demucs.separate",
                    "-n", "htdemucs_6s",
                    "-o", str(output_dir),
                    str(audio_path)
                ], check=True, capture_output=True)

                # Collect results
                stems_dir = output_dir / "htdemucs_6s" / audio_path.stem
                stems = {}
                instruments = []

                for stem_file in stems_dir.glob("*.wav"):
                    stem_name = stem_file.stem
                    stems[stem_name] = stem_file
                    instruments.append(stem_name)

                return stems, instruments

        except Exception as e:
            print(f"Fallback separation also failed: {e}")
            return {audio_path.stem: audio_path}, ["unknown"]

    def _should_continue_separation(self,
                                  current_pass: SeparationPass,
                                  all_passes: List[SeparationPass],
                                  callback) -> bool:
        """Decide whether to continue with another separation pass"""

        # Get previous pass for comparison
        previous_pass = all_passes[-2] if len(all_passes) >= 2 else None

        # Calculate average quality score for current pass
        if not current_pass.quality_metrics:
            return False

        avg_quality = np.mean([
            metrics.overall_score for metrics in current_pass.quality_metrics.values()
        ])

        # Calculate improvement if we have a previous pass
        improvement = 0.0
        if previous_pass and previous_pass.quality_metrics:
            prev_avg_quality = np.mean([
                metrics.overall_score for metrics in previous_pass.quality_metrics.values()
            ])
            improvement = avg_quality - prev_avg_quality

        callback(f"Pass {current_pass.pass_number} quality: {avg_quality:.3f}, improvement: {improvement:.3f}")

        # Decision logic
        if avg_quality >= config.QUALITY_THRESHOLD:
            callback("Quality threshold reached")
            return False

        if previous_pass and improvement < config.IMPROVEMENT_THRESHOLD:
            callback("Improvement threshold not met")
            return False

        # Check if any stems have low quality and could benefit from refinement
        low_quality_stems = [
            name for name, metrics in current_pass.quality_metrics.items()
            if metrics.overall_score < config.QUALITY_THRESHOLD * 0.8
        ]

        if not low_quality_stems:
            callback("All stems have acceptable quality")
            return False

        callback(f"Continuing separation for stems: {low_quality_stems}")
        return True

    def _prepare_next_pass_stems(self,
                               current_pass: SeparationPass,
                               callback) -> Dict[str, Path]:
        """Identify and prepare stems that need further refinement"""

        candidates = {}

        for stem_name, metrics in current_pass.quality_metrics.items():
            # Include stems with low quality scores
            if metrics.overall_score < config.QUALITY_THRESHOLD * 0.8:
                stem_path = current_pass.stems.get(stem_name)
                if stem_path and stem_path.exists():
                    candidates[stem_name] = stem_path

        # Also check for stems that might contain multiple instruments
        for stem_name, stem_path in current_pass.stems.items():
            if stem_name not in candidates:
                instruments = self.instrument_classifier.classify_instruments(stem_path)
                if len(instruments) > 1:
                    callback(f"{stem_name} contains multiple instruments: {instruments}")
                    candidates[stem_name] = stem_path

        return candidates

    def _consolidate_final_stems(self,
                               all_passes: List[SeparationPass],
                               work_dir: Path) -> Dict[str, Path]:
        """Consolidate the best results from all separation passes"""

        final_stems = {}
        final_dir = work_dir / "final"
        final_dir.mkdir(exist_ok=True)

        # Get all unique stem names across all passes
        all_stem_names = set()
        for pass_result in all_passes:
            all_stem_names.update(pass_result.stems.keys())

        # For each stem, find the pass with the highest quality
        for stem_name in all_stem_names:
            best_pass = None
            best_quality = -1.0

            for pass_result in all_passes:
                if stem_name in pass_result.stems and stem_name in pass_result.quality_metrics:
                    quality = pass_result.quality_metrics[stem_name].overall_score
                    if quality > best_quality:
                        best_quality = quality
                        best_pass = pass_result

            if best_pass:
                source_path = best_pass.stems[stem_name]
                final_path = final_dir / f"{stem_name}.wav"

                # Copy the best version to final directory
                shutil.copy2(source_path, final_path)
                final_stems[stem_name] = final_path

        return final_stems
