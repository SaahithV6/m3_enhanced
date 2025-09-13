import os
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseSettings, Field

class M3Config(BaseSettings):
    """Enhanced M3 Configuration for multi-pass audio processing"""

    # Base Directories
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
    MODELS_DIR: Path = BASE_DIR / "models"
    TEMP_DIR: Path = BASE_DIR / "temp"
    UPLOADS_DIR: Path = BASE_DIR / "uploads"
    RESULTS_DIR: Path = BASE_DIR / "results"

    # Audio Processing Settings
    AUDIO_SAMPLE_RATE: int = 48000  # Studio quality
    AUDIO_BIT_DEPTH: int = 24
    MAX_AUDIO_DURATION_SECONDS: int = 600  # 10 minutes max

    # Multi-Pass Separation Settings
    MAX_SEPARATION_PASSES: int = 6
    QUALITY_THRESHOLD: float = 0.85
    IMPROVEMENT_THRESHOLD: float = 0.02  # Stop if <2% improvement

    # Model Configurations
    DEMUCS_MODEL_NAME: str = "htdemucs"
    MVSEP_MODEL_NAME: str = "UVR-MDX-NET-Inst_HQ_3"
    TRANSCRIPTION_MODEL: str = "basic-pitch"  # Will upgrade to YourMT3+ when available

    # Quality Metrics Thresholds
    MIN_SDR_THRESHOLD: float = 10.0  # Signal-to-Distortion Ratio
    MIN_SIR_THRESHOLD: float = 15.0  # Signal-to-Interference Ratio
    MIN_SAR_THRESHOLD: float = 10.0  # Signal-to-Artifacts Ratio

    # Job Management
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    MAX_CONCURRENT_JOBS: int = 2  # GPU memory constraint

    # Instrument Detection Settings
    INSTRUMENT_CONFIDENCE_THRESHOLD: float = 0.25
    SUPPORTED_INSTRUMENTS: List[str] = [
        "vocals", "bass", "drums", "lead_guitar", "rhythm_guitar",
        "acoustic_guitar", "piano", "synthesizer", "strings", "brass"
    ]

    # Guitar-specific settings for tablature
    GUITAR_STRINGS: int = 6
    MAX_FRET_SPAN: int = 5  # Maximum frets a hand can span
    PREFERRED_POSITIONS: List[int] = [5, 7, 12]  # Common playing positions

    # FFmpeg settings for studio-grade conversion
    FFMPEG_AUDIO_CODEC: str = "pcm_s24le"  # 24-bit PCM
    FFMPEG_BITRATE: str = "1152k"  # High quality

    # YT-DLP settings for URL downloads
    YT_DLP_AUDIO_FORMAT: str = "best[ext=mp3]/best"
    YT_DLP_QUALITY: str = "bestaudio"

    class Config:
        env_file = ".env"
        case_sensitive = True

class ModelPaths:
    """Centralized model path management"""

    def __init__(self, models_dir: Path):
        self.models_dir = models_dir

        # Separation Models
        self.demucs_dir = models_dir / "demucs"
        self.mvsep_dir = models_dir / "mvsep"

        # Transcription Models
        self.yourmt3_dir = models_dir / "yourmt3_plus"
        self.mt3_dir = models_dir / "mt3"
        self.basic_pitch_dir = models_dir / "basic_pitch"

        # Classification Models
        self.yamnet_dir = models_dir / "yamnet"
        self.openl3_dir = models_dir / "openl3"

        # Synthesis
        self.soundfonts_dir = models_dir / "soundfonts"

    def get_soundfont_path(self) -> Path:
        """Get the primary soundfont file"""
        return self.soundfonts_dir / "FluidR3_GM.sf2"

    def ensure_directories(self):
        """Create all model directories if they don't exist"""
        for attr_name in dir(self):
            if attr_name.endswith('_dir'):
                path = getattr(self, attr_name)
                if isinstance(path, Path):
                    path.mkdir(parents=True, exist_ok=True)

# Global configuration instance
config = M3Config()
model_paths = ModelPaths(config.MODELS_DIR)

# Ensure all directories exist
model_paths.ensure_directories()
config.TEMP_DIR.mkdir(parents=True, exist_ok=True)
config.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
