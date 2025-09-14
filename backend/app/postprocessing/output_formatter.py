"""
Output Formatter for M3 Enhanced
Comprehensive packaging of separation and transcription results
"""

import zipfile
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import logging
import tempfile
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from io import BytesIO

from ..core.config import config
from ..utils.file_manager import FileManager, FileInfo
from ..utils.audio_utils import AudioUtils, AudioInfo
from ..utils.midi_utils import MidiUtils, MidiInfo
from ..core.quality_metrics import QualityMetrics, TranscriptionConfidence

logger = logging.getLogger(__name__)

@dataclass
class StemResult:
    """Container for individual stem processing results"""
    stem_name: str
    audio_path: Path
    midi_path: Optional[Path]
    tablature_path: Optional[Path]
    sheet_music_path: Optional[Path]
    quality_metrics: QualityMetrics
    transcription_confidence: Optional[TranscriptionConfidence]
    instrument_type: str
    processing_passes: int

@dataclass
class ProcessingMetadata:
    """Metadata for the entire processing job"""
    job_id: str
    original_filename: str
    processing_started: datetime
    processing_completed: datetime
    total_duration: float
    models_used: List[str]
    separation_passes: int
    overall_quality_score: float
    detected_tempo: float
    detected_key: str
    time_signature: str
    total_instruments: int

@dataclass
class OutputPackage:
    """Complete output package structure"""
    metadata: ProcessingMetadata
    stems: List[StemResult]
    original_audio: Path
    visualization_paths: List[Path]
    report_path: Path
    package_path: Path

class OutputFormatter:
    """
    Advanced output formatting and packaging system.
    Creates professional-grade deliverables with comprehensive metadata.
    """

    def __init__(self):
        self.file_manager = FileManager()
        self.audio_utils = AudioUtils()
        self.midi_utils = MidiUtils()

        # Output format configurations
        self.supported_formats = {
            'audio': ['.wav', '.flac', '.mp3'],
            'midi': ['.mid', '.midi'],
            'sheet_music': ['.pdf', '.svg', '.png'],
            'tablature': ['.gp5', '.pdf', '.txt'],
            'package': ['.zip']
        }

    def create_output_package(
        self,
        job_id: str,
        stems_data: Dict[str, Any],
        processing_metadata: Dict[str, Any],
        output_format: str = "professional"
    ) -> OutputPackage:
        """
        Create comprehensive output package from processing results

        Args:
            job_id: Unique job identifier
            stems_data: Dictionary containing all stem processing results
            processing_metadata: Metadata from the processing pipeline
            output_format: Package format ('professional', 'basic', 'studio')

        Returns:
            OutputPackage with all generated files
        """
        try:
            logger.info(f"Creating output package for job {job_id}")

            # Create working directory
            package_dir = config.RESULTS_DIR / job_id
            package_dir.mkdir(parents=True, exist_ok=True)

            # Parse and validate input data
            metadata = self._create_metadata(job_id, processing_metadata)
            stems = self._process_stem_results(stems_data, package_dir)

            # Generate visualizations
            viz_paths = self._generate_visualizations(stems, metadata, package_dir)

            # Create comprehensive report
            report_path = self._generate_processing_report(
                metadata, stems, viz_paths, package_dir
            )

            # Copy original audio with enhanced metadata
            original_audio_path = self._prepare_original_audio(
                processing_metadata.get('original_file_path'),
                package_dir
            )

            # Create final ZIP package
            package_path = self._create_zip_package(
                package_dir, job_id, output_format
            )

            package = OutputPackage(
                metadata=metadata,
                stems=stems,
                original_audio=original_audio_path,
                visualization_paths=viz_paths,
                report_path=report_path,
                package_path=package_path
            )

            logger.info(f"Successfully created output package: {package_path}")
            return package

        except Exception as e:
            logger.error(f"Failed to create output package for job {job_id}: {str(e)}")
            raise

    def _create_metadata(
        self,
        job_id: str,
        processing_data: Dict[str, Any]
    ) -> ProcessingMetadata:
        """Create structured metadata from processing results"""

        return ProcessingMetadata(
            job_id=job_id,
            original_filename=processing_data.get('original_filename', 'unknown'),
            processing_started=datetime.fromisoformat(
                processing_data.get('started_at', datetime.utcnow().isoformat())
            ),
            processing_completed=datetime.utcnow(),
            total_duration=processing_data.get('audio_duration', 0.0),
            models_used=processing_data.get('models_used', []),
            separation_passes=processing_data.get('separation_passes', 1),
            overall_quality_score=processing_data.get('overall_quality', 0.0),
            detected_tempo=processing_data.get('detected_tempo', 120.0),
            detected_key=processing_data.get('detected_key', 'C major'),
            time_signature=processing_data.get('time_signature', '4/4'),
            total_instruments=len(processing_data.get('stems', {}))
        )

    def _process_stem_results(
        self,
        stems_data: Dict[str, Any],
        package_dir: Path
    ) -> List[StemResult]:
        """Process and organize individual stem results"""

        stems = []
        stems_dir = package_dir / "stems"
        stems_dir.mkdir(exist_ok=True)

        for stem_name, stem_data in stems_data.items():
            try:
                # Create directories for this stem
                stem_dir = stems_dir / stem_name
                stem_dir.mkdir(exist_ok=True)

                # Process audio file
                audio_path = self._process_stem_audio(
                    stem_data.get('audio_path'),
                    stem_dir,
                    stem_name
                )

                # Process MIDI file if available
                midi_path = None
                if 'midi_path' in stem_data and stem_data['midi_path']:
                    midi_path = self._process_stem_midi(
                        stem_data['midi_path'],
                        stem_dir,
                        stem_name
                    )

                # Process tablature if available
                tablature_path = None
                if 'tablature_path' in stem_data and stem_data['tablature_path']:
                    tablature_path = self._process_stem_tablature(
                        stem_data['tablature_path'],
                        stem_dir,
                        stem_name
                    )

                # Process sheet music if available
                sheet_music_path = None
                if 'sheet_music_path' in stem_data and stem_data['sheet_music_path']:
                    sheet_music_path = self._process_stem_sheet_music(
                        stem_data['sheet_music_path'],
                        stem_dir,
                        stem_name
                    )

                # Parse quality metrics
                quality_metrics = self._parse_quality_metrics(
                    stem_data.get('quality_metrics', {})
                )

                # Parse transcription confidence
                transcription_confidence = self._parse_transcription_confidence(
                    stem_data.get('transcription_confidence', {})
                )

                stem_result = StemResult(
                    stem_name=stem_name,
                    audio_path=audio_path,
                    midi_path=midi_path,
                    tablature_path=tablature_path,
                    sheet_music_path=sheet_music_path,
                    quality_metrics=quality_metrics,
                    transcription_confidence=transcription_confidence,
                    instrument_type=stem_data.get('instrument_type', 'unknown'),
                    processing_passes=stem_data.get('processing_passes', 1)
                )

                stems.append(stem_result)
                logger.debug(f"Processed stem: {stem_name}")

            except Exception as e:
                logger.error(f"Failed to process stem {stem_name}: {str(e)}")
                continue

        return stems

    def _process_stem_audio(
        self,
        source_path: Union[str, Path, None],
        stem_dir: Path,
        stem_name: str
    ) -> Path:
        """Process and copy stem audio with normalization"""

        if not source_path or not Path(source_path).exists():
            raise ValueError(f"Invalid audio path for stem {stem_name}")

        source_path = Path(source_path)

        # Load and enhance audio
        audio, sr = self.audio_utils.load_audio(source_path, normalize=True)

        # Apply fade in/out for professional sound
        audio = self.audio_utils.apply_fade(
            audio, sr, fade_in_duration=0.05, fade_out_duration=0.1
        )

        # Save in multiple formats
        output_paths = {}

        # High-quality WAV (24-bit)
        wav_path = stem_dir / f"{stem_name}.wav"
        self.audio_utils.save_audio(
            audio, wav_path, sr, format="wav", subtype="PCM_24"
        )

        # FLAC for lossless compression
        flac_path = stem_dir / f"{stem_name}.flac"
        self.audio_utils.save_audio(
            audio, flac_path, sr, format="flac"
        )

        # MP3 for compatibility
        mp3_path = stem_dir / f"{stem_name}.mp3"
        self._convert_to_mp3(wav_path, mp3_path)

        return wav_path  # Return primary format

    def _process_stem_midi(
        self,
        source_path: Union[str, Path],
        stem_dir: Path,
        stem_name: str
    ) -> Path:
        """Process and enhance MIDI file"""

        source_path = Path(source_path)
        if not source_path.exists():
            raise ValueError(f"MIDI file not found: {source_path}")

        # Copy and validate MIDI
        midi_path = stem_dir / f"{stem_name}.mid"
        shutil.copy2(source_path, midi_path)

        # Validate MIDI structure
        try:
            midi_info = self.midi_utils.get_midi_info(midi_path)
            logger.debug(f"MIDI validated: {midi_info.total_notes} notes, {midi_info.duration:.2f}s")
        except Exception as e:
            logger.warning(f"MIDI validation failed for {stem_name}: {str(e)}")

        return midi_path

    def _generate_visualizations(
        self,
        stems: List[StemResult],
        metadata: ProcessingMetadata,
        package_dir: Path
    ) -> List[Path]:
        """Generate comprehensive visualizations"""

        viz_dir = package_dir / "visualizations"
        viz_dir.mkdir(exist_ok=True)

        viz_paths = []

        try:
            # Quality metrics overview
            quality_chart_path = self._create_quality_overview_chart(
                stems, viz_dir
            )
            viz_paths.append(quality_chart_path)

            # Spectrograms for each stem
            for stem in stems:
                if stem.audio_path and stem.audio_path.exists():
                    spectrogram_path = self._create_spectrogram(
                        stem.audio_path, stem.stem_name, viz_dir
                    )
                    viz_paths.append(spectrogram_path)

            # Processing timeline
            timeline_path = self._create_processing_timeline(
                metadata, stems, viz_dir
            )
            viz_paths.append(timeline_path)

            # Instrument distribution
            distribution_path = self._create_instrument_distribution(
                stems, viz_dir
            )
            viz_paths.append(distribution_path)

        except Exception as e:
            logger.error(f"Failed to generate visualizations: {str(e)}")

        return viz_paths

    def _generate_processing_report(
        self,
        metadata: ProcessingMetadata,
        stems: List[StemResult],
        viz_paths: List[Path],
        package_dir: Path
    ) -> Path:
        """Generate comprehensive processing report"""

        report_path = package_dir / "processing_report.json"

        # Create detailed report
        report_data = {
            "metadata": asdict(metadata),
            "stems": [
                {
                    "stem_name": stem.stem_name,
                    "instrument_type": stem.instrument_type,
                    "processing_passes": stem.processing_passes,
                    "quality_metrics": asdict(stem.quality_metrics),
                    "transcription_confidence": (
                        asdict(stem.transcription_confidence)
                        if stem.transcription_confidence else None
                    ),
                    "files": {
                        "audio": str(stem.audio_path.name) if stem.audio_path else None,
                        "midi": str(stem.midi_path.name) if stem.midi_path else None,
                        "tablature": str(stem.tablature_path.name) if stem.tablature_path else None,
                        "sheet_music": str(stem.sheet_music_path.name) if stem.sheet_music_path else None
                    }
                }
                for stem in stems
            ],
            "visualizations": [str(path.name) for path in viz_paths],
            "summary": {
                "total_processing_time": (
                    metadata.processing_completed - metadata.processing_started
                ).total_seconds(),
                "successful_stems": len([s for s in stems if s.audio_path]),
                "average_quality_score": sum(s.quality_metrics.overall_score for s in stems) / len(stems) if stems else 0,
                "transcription_success_rate": len([s for s in stems if s.midi_path]) / len(stems) if stems else 0
            }
        }

        # Save report
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)

        logger.debug(f"Generated processing report: {report_path}")
        return report_path

    def _create_zip_package(
        self,
        package_dir: Path,
        job_id: str,
        output_format: str
    ) -> Path:
        """Create final ZIP package with organized structure"""

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"m3_enhanced_{job_id}_{timestamp}.zip"
        zip_path = config.RESULTS_DIR / zip_filename

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
            # Add all files with organized structure
            for file_path in package_dir.rglob('*'):
                if file_path.is_file():
                    # Create clean archive path
                    archive_path = file_path.relative_to(package_dir)
                    zipf.write(file_path, archive_path)

            # Add metadata file in root
            metadata_content = {
                "m3_enhanced_version": "1.0.0",
                "job_id": job_id,
                "package_created": datetime.utcnow().isoformat(),
                "format": output_format,
                "contents": "Multi-pass audio separation and transcription results"
            }

            zipf.writestr("package_info.json", json.dumps(metadata_content, indent=2))

        logger.info(f"Created ZIP package: {zip_path} ({zip_path.stat().st_size / 1024 / 1024:.1f} MB)")
        return zip_path

    # Helper methods for quality metrics parsing
    def _parse_quality_metrics(self, metrics_data: Dict[str, Any]) -> QualityMetrics:
        """Parse quality metrics from dictionary"""
        return QualityMetrics(
            sdr=metrics_data.get('sdr', 0.0),
            sir=metrics_data.get('sir', 0.0),
            sar=metrics_data.get('sar', 0.0),
            pesq_score=metrics_data.get('pesq_score', 0.0),
            stoi_score=metrics_data.get('stoi_score', 0.0),
            spectral_centroid_stability=metrics_data.get('spectral_centroid_stability', 0.0),
            harmonic_distortion=metrics_data.get('harmonic_distortion', 0.0),
            overall_score=metrics_data.get('overall_score', 0.0)
        )

    def _parse_transcription_confidence(
        self,
        confidence_data: Dict[str, Any]
    ) -> Optional[TranscriptionConfidence]:
        """Parse transcription confidence from dictionary"""
        if not confidence_data:
            return None

        return TranscriptionConfidence(
            note_onset_precision=confidence_data.get('note_onset_precision', 0.0),
            pitch_accuracy=confidence_data.get('pitch_accuracy', 0.0),
            rhythm_consistency=confidence_data.get('rhythm_consistency', 0.0),
            harmonic_completeness=confidence_data.get('harmonic_completeness', 0.0),
            overall_confidence=confidence_data.get('overall_confidence', 0.0)
        )

    # Visualization helper methods
    def _create_quality_overview_chart(self, stems: List[StemResult], viz_dir: Path) -> Path:
        """Create quality metrics overview chart"""
        chart_path = viz_dir / "quality_overview.png"

        try:
            fig, ax = plt.subplots(figsize=(12, 8))

            stem_names = [stem.stem_name for stem in stems]
            sdr_scores = [stem.quality_metrics.sdr for stem in stems]
            sir_scores = [stem.quality_metrics.sir for stem in stems]
            sar_scores = [stem.quality_metrics.sar for stem in stems]

            x = range(len(stem_names))
            width = 0.25

            ax.bar([i - width for i in x], sdr_scores, width, label='SDR', alpha=0.8)
            ax.bar(x, sir_scores, width, label='SIR', alpha=0.8)
            ax.bar([i + width for i in x], sar_scores, width, label='SAR', alpha=0.8)

            ax.set_xlabel('Stems')
            ax.set_ylabel('Quality Score (dB)')
            ax.set_title('Audio Separation Quality Metrics')
            ax.set_xticks(x)
            ax.set_xticklabels(stem_names, rotation=45)
            ax.legend()
            ax.grid(True, alpha=0.3)

            plt.tight_layout()
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()

        except Exception as e:
            logger.error(f"Failed to create quality chart: {str(e)}")

        return chart_path

    def _convert_to_mp3(self, wav_path: Path, mp3_path: Path) -> None:
        """Convert WAV to MP3 using FFmpeg"""
        try:
            import subprocess
            subprocess.run([
                'ffmpeg', '-i', str(wav_path), '-codec:a', 'libmp3lame',
                '-b:a', '320k', '-y', str(mp3_path)
            ], check=True, capture_output=True)
        except Exception as e:
            logger.warning(f"Failed to create MP3: {str(e)}")
