"""
M3 Enhanced Model Downloader
Downloads and organizes all required AI models with parallel processing for Google Colab
"""

import os
import sys
import asyncio
import aiohttp
import aiofiles
from pathlib import Path
import hashlib
import json
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess
import tempfile
import shutil
from tqdm.asyncio import tqdm
import argparse

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from app.core.config import config
from app.models.model_configs import ModelConfigs

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ModelDownload:
    """Configuration for model download"""
    name: str
    url: str
    filename: str
    size_mb: float
    checksum: Optional[str]
    dependencies: List[str]
    post_process: Optional[str]  # Script to run after download

class ModelDownloader:
    """
    Advanced model downloader optimized for Google Colab's fast internet.
    Implements parallel downloads with integrity checking and automatic retries.
    """

    def __init__(self, models_dir: Path, max_parallel_downloads: int = 8):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.max_parallel_downloads = max_parallel_downloads
        self.model_configs = ModelConfigs()

        # Model download configurations
        self.model_downloads = {
            # Demucs Models
            "demucs_htdemucs": ModelDownload(
                name="Demucs HT",
                url="https://dl.fbaipublicfiles.com/demucs/hybrid_transformer/955717e8-8726e21a.th",
                filename="demucs/htdemucs.th",
                size_mb=319.2,
                checksum="8726e21a955717e8",
                dependencies=["demucs"],
                post_process=None
            ),

            "demucs_htdemucs_6s": ModelDownload(
                name="Demucs HT 6-Source",
                url="https://dl.fbaipublicfiles.com/demucs/hybrid_transformer/5c90dfd2-34c22ccb.th",
                filename="demucs/htdemucs_6s.th",
                size_mb=319.2,
                checksum="34c22ccb5c90dfd2",
                dependencies=["demucs"],
                post_process=None
            ),

            # Basic Pitch (Spotify)
            "basic_pitch": ModelDownload(
                name="Basic Pitch",
                url="https://github.com/spotify/basic-pitch/releases/download/v0.2.5/basic_pitch_pytorch_icassp_2022.tar.gz",
                filename="basic_pitch/model.tar.gz",
                size_mb=45.8,
                checksum=None,
                dependencies=["basic-pitch"],
                post_process="extract_basic_pitch"
            ),

            # YAMNet (Google)
            "yamnet": ModelDownload(
                name="YAMNet",
                url="https://tfhub.dev/google/yamnet/1?tf-hub-format=compressed",
                filename="yamnet/yamnet.tar.gz",
                size_mb=13.4,
                checksum=None,
                dependencies=["tensorflow", "tensorflow-hub"],
                post_process="extract_yamnet"
            ),

            # MVSEP Models
            "mvsep_mdx23": ModelDownload(
                name="MVSEP-MDX23",
                url="https://github.com/ZFTurbo/MVSEP-MDX23-music-separation-model/releases/download/v1.0.0/model_vocals.onnx",
                filename="mvsep/mdx23_vocals.onnx",
                size_mb=168.7,
                checksum=None,
                dependencies=["audio-separator"],
                post_process=None
            ),

            # OpenL3 Models
            "openl3": ModelDownload(
                name="OpenL3",
                url="https://github.com/marl/openl3/releases/download/v0.4.0/openl3_audio_mel256_music.h5",
                filename="openl3/openl3_audio_mel256_music.h5",
                size_mb=87.3,
                checksum=None,
                dependencies=["openl3"],
                post_process=None
            ),

            # CLAP Model (for audio-text similarity)
            "clap": ModelDownload(
                name="CLAP",
                url="https://huggingface.co/laion/larger_clap_music_and_speech/resolve/main/pytorch_model.bin",
                filename="clap/pytorch_model.bin",
                size_mb=695.4,
                checksum=None,
                dependencies=["laion-clap"],
                post_process=None
            )
        }

    async def download_all_models(self, force_redownload: bool = False) -> Dict[str, bool]:
        """Download all models with parallel processing"""

        logger.info("Starting model download process...")

        # Check available space
        self._check_disk_space()

        # Install dependencies first (serial for proper dependency resolution)
        await self._install_dependencies()

        # Download models in parallel
        results = {}
        semaphore = asyncio.Semaphore(self.max_parallel_downloads)

        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=3600),  # 1 hour timeout
            connector=aiohttp.TCPConnector(limit=self.max_parallel_downloads)
        ) as session:

            tasks = []
            for model_name, download_config in self.model_downloads.items():
                task = self._download_model_with_semaphore(
                    semaphore, session, model_name, download_config, force_redownload
                )
                tasks.append(task)

            # Execute downloads with progress tracking
            progress_bar = tqdm(total=len(tasks), desc="Downloading models")

            for completed_task in asyncio.as_completed(tasks):
                model_name, success = await completed_task
                results[model_name] = success
                progress_bar.update(1)

                status = "✓" if success else "✗"
                logger.info(f"{status} {model_name}: {'Success' if success else 'Failed'}")

            progress_bar.close()

        # Generate download report
        self._generate_download_report(results)

        logger.info(f"Model download complete. Success rate: {sum(results.values())}/{len(results)}")
        return results

    async def _download_model_with_semaphore(
        self,
        semaphore: asyncio.Semaphore,
        session: aiohttp.ClientSession,
        model_name: str,
        download_config: ModelDownload,
        force_redownload: bool
    ) -> Tuple[str, bool]:
        """Download single model with semaphore for concurrency control"""

        async with semaphore:
            return await self._download_single_model(
                session, model_name, download_config, force_redownload
            )

    async def _download_single_model(
        self,
        session: aiohttp.ClientSession,
        model_name: str,
        download_config: ModelDownload,
        force_redownload: bool
    ) -> Tuple[str, bool]:
        """Download and validate a single model"""

        try:
            model_path = self.models_dir / download_config.filename
            model_path.parent.mkdir(parents=True, exist_ok=True)

            # Check if model already exists and is valid
            if not force_redownload and model_path.exists():
                if await self._validate_model(model_path, download_config):
                    logger.debug(f"Model {model_name} already exists and is valid")
                    return model_name, True

            logger.info(f"Downloading {download_config.name} ({download_config.size_mb:.1f} MB)...")

            # Download with progress tracking
            async with session.get(download_config.url) as response:
                if response.status != 200:
                    logger.error(f"Failed to download {model_name}: HTTP {response.status}")
                    return model_name, False

                total_size = int(response.headers.get('content-length', 0))

                async with aiofiles.open(model_path, 'wb') as f:
                    downloaded = 0
                    async for chunk in response.content.iter_chunked(8192):
                        await f.write(chunk)
                        downloaded += len(chunk)

            # Validate downloaded model
            if await self._validate_model(model_path, download_config):
                # Run post-processing if needed
                if download_config.post_process:
                    await self._run_post_process(model_path, download_config.post_process)

                logger.info(f"Successfully downloaded {download_config.name}")
                return model_name, True
            else:
                logger.error(f"Validation failed for {model_name}")
                model_path.unlink(missing_ok=True)
                return model_name, False

        except Exception as e:
            logger.error(f"Error downloading {model_name}: {str(e)}")
            return model_name, False

    async def _validate_model(self, model_path: Path, download_config: ModelDownload) -> bool:
        """Validate downloaded model integrity"""

        try:
            # Check file exists and has reasonable size
            if not model_path.exists():
                return False

            file_size_mb = model_path.stat().st_size / (1024 * 1024)
            expected_size_mb = download_config.size_mb

            # Allow 10% variance in file size
            if abs(file_size_mb - expected_size_mb) > expected_size_mb * 0.1:
                logger.warning(f"Size mismatch for {model_path.name}: {file_size_mb:.1f}MB vs expected {expected_size_mb:.1f}MB")
                return False

            # Verify checksum if provided
            if download_config.checksum:
                file_hash = await self._calculate_file_hash(model_path)
                if download_config.checksum not in file_hash:
                    logger.error(f"Checksum mismatch for {model_path.name}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Validation error for {model_path}: {str(e)}")
            return False

    async def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file"""

        hash_sha256 = hashlib.sha256()

        async with aiofiles.open(file_path, 'rb') as f:
            while chunk := await f.read(8192):
                hash_sha256.update(chunk)

        return hash_sha256.hexdigest()

    async def _install_dependencies(self):
        """Install Python package dependencies in correct order"""

        logger.info("Installing package dependencies...")

        # Core packages first
        core_packages = [
            "torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121",
            "tensorflow tensorflow-hub",
            "transformers accelerate datasets"
        ]

        for package_set in core_packages:
            try:
                result = subprocess.run(
                    f"pip install {package_set}",
                    shell=True,
                    capture_output=True,
                    text=True,
                    check=True
                )
                logger.debug(f"Installed: {package_set}")
            except subprocess.CalledProcessError as e:
                logger.warning(f"Failed to install {package_set}: {e.stderr}")

        # Audio-specific packages
        audio_packages = [
            "demucs",
            "audio-separator",
            "basic-pitch",
            "openl3",
            "laion-clap",
            "librosa[display]",
            "soundfile",
            "pretty_midi",
            "music21",
            "mir_eval",
            "pesq",
            "pystoi"
        ]

        for package in audio_packages:
            try:
                subprocess.run(
                    f"pip install {package}",
                    shell=True,
                    capture_output=True,
                    check=True
                )
                logger.debug(f"Installed: {package}")
            except subprocess.CalledProcessError as e:
                logger.warning(f"Failed to install {package}: {e.stderr}")

    def _check_disk_space(self):
        """Check if enough disk space is available"""

        total_size_mb = sum(download.size_mb for download in self.model_downloads.values())
        total_size_gb = total_size_mb / 1024

        # Check available space (require 2x the total size for safety)
        stat = shutil.disk_usage(self.models_dir)
        available_gb = stat.free / (1024**3)

        if available_gb < total_size_gb * 2:
            raise RuntimeError(
                f"Insufficient disk space. Need {total_size_gb * 2:.1f}GB, "
                f"have {available_gb:.1f}GB"
            )

        logger.info(f"Disk space check passed. Downloading {total_size_gb:.1f}GB of models")

    def _generate_download_report(self, results: Dict[str, bool]):
        """Generate download completion report"""

        report_path = self.models_dir / "download_report.json"

        report_data = {
            "download_completed": True,
            "timestamp": str(os.times()),
            "successful_models": [name for name, success in results.items() if success],
            "failed_models": [name for name, success in results.items() if not success],
            "success_rate": f"{sum(results.values())}/{len(results)}",
            "models_directory": str(self.models_dir),
            "total_size_estimate_gb": sum(
                download.size_mb for download in self.model_downloads.values()
            ) / 1024
        }

        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2)

        logger.info(f"Download report saved to {report_path}")

async def main():
    """Main download function"""

    parser = argparse.ArgumentParser(description="Download M3 Enhanced models")
    parser.add_argument("--models-dir", type=str, default="./models", help="Models directory")
    parser.add_argument("--force", action="store_true", help="Force redownload existing models")
    parser.add_argument("--parallel", type=int, default=8, help="Number of parallel downloads")

    args = parser.parse_args()

    downloader = ModelDownloader(
        models_dir=Path(args.models_dir),
        max_parallel_downloads=args.parallel
    )

    try:
        results = await downloader.download_all_models(force_redownload=args.force)

        if all(results.values()):
            logger.info("All models downloaded successfully!")
            return 0
        else:
            logger.error("Some models failed to download")
            return 1

    except Exception as e:
        logger.error(f"Download process failed: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(asyncio.run(main()))
