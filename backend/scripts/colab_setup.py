"""
M3 Enhanced Google Colab Setup Script
Optimizes Colab environment for maximum performance and reliability
"""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
import requests
import json
import time
import logging
from typing import Dict, List, Optional, Tuple
import asyncio
import psutil
import GPUtil

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ColabOptimizer:
    """
    Google Colab environment optimizer for M3 Enhanced.
    Configures system for optimal audio processing performance.
    """

    def __init__(self):
        self.colab_detected = self._detect_colab()
        self.gpu_info = self._get_gpu_info()
        self.system_info = self._get_system_info()

    def _detect_colab(self) -> bool:
        """Detect if running in Google Colab"""
        try:
            import google.colab
            return True
        except ImportError:
            return False

    def _get_gpu_info(self) -> Dict:
        """Get GPU information"""
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]
                return {
                    'name': gpu.name,
                    'memory_total': gpu.memoryTotal,
                    'memory_free': gpu.memoryFree,
                    'driver': gpu.driver,
                    'cuda_available': True
                }
        except:
            pass

        return {
            'name': 'No GPU',
            'memory_total': 0,
            'memory_free': 0,
            'driver': 'None',
            'cuda_available': False
        }

    def _get_system_info(self) -> Dict:
        """Get system information"""
        return {
            'cpu_count': psutil.cpu_count(),
            'memory_total': psutil.virtual_memory().total // (1024**3),  # GB
            'memory_available': psutil.virtual_memory().available // (1024**3),  # GB
            'disk_total': shutil.disk_usage('/').total // (1024**3),  # GB
            'disk_free': shutil.disk_usage('/').free // (1024**3),  # GB
        }

    def setup_colab_environment(self):
        """Complete Colab environment setup"""

        logger.info("🚀 Setting up M3 Enhanced in Google Colab")

        # Display system information
        self._display_system_info()

        # Install system dependencies
        self._install_system_dependencies()

        # Optimize system settings
        self._optimize_system_settings()

        # Install Python packages
        self._install_python_packages()

        # Setup directories
        self._setup_directories()

        # Download models
        self._download_models()

        # Configure environment variables
        self._configure_environment()

        # Run system tests
        self._run_system_tests()

        logger.info("✅ M3 Enhanced setup complete!")
        self._display_final_status()

    def _display_system_info(self):
        """Display system information"""

        print("\n" + "="*60)
        print("M3 ENHANCED - GOOGLE COLAB SETUP")
        print("="*60)

        print(f"🖥️  CPU Cores: {self.system_info['cpu_count']}")
        print(f"💾 RAM: {self.system_info['memory_available']}/{self.system_info['memory_total']} GB available")
        print(f"💿 Disk: {self.system_info['disk_free']}/{self.system_info['disk_total']} GB free")

        if self.gpu_info['cuda_available']:
            print(f"🎮 GPU: {self.gpu_info['name']}")
            print(f"🎮 VRAM: {self.gpu_info['memory_free']}/{self.gpu_info['memory_total']} MB available")
        else:
            print("⚠️  No GPU detected - CPU-only mode")

        print("="*60 + "\n")

    def _install_system_dependencies(self):
        """Install system-level dependencies"""

        logger.info("📦 Installing system dependencies...")

        # Update package lists
        subprocess.run(['apt-get', 'update', '-qq'], check=True)

        # Install essential audio processing tools
        packages = [
            'ffmpeg',           # Media processing
            'libsndfile1-dev',  # Audio file I/O
            'libfftw3-dev',     # Fast Fourier Transform
            'flac',             # FLAC codec
            'lame',             # MP3 encoder
            'opus-tools',       # Opus codec
            'vorbis-tools',     # Ogg Vorbis
            'libmagic1',        # File type detection
            'redis-server',     # Job queue
            'htop',             # System monitoring
        ]

        if self.gpu_info['cuda_available']:
            packages.extend([
                'nvidia-cuda-toolkit',  # CUDA development
                'nvtop'                 # GPU monitoring
            ])

        for package in packages:
            try:
                subprocess.run(
                    ['apt-get', 'install', '-y', '-qq', package],
                    check=True,
                    capture_output=True
                )
                logger.debug(f"Installed: {package}")
            except subprocess.CalledProcessError as e:
                logger.warning(f"Failed to install {package}: {e}")

    def _optimize_system_settings(self):
        """Optimize system settings for audio processing"""

        logger.info("⚙️  Optimizing system settings...")

        # Increase file descriptor limits
        os.system("ulimit -n 65536")

        # Optimize memory settings
        os.system("echo 'vm.swappiness=10' >> /etc/sysctl.conf")
        os.system("echo 'vm.vfs_cache_pressure=50' >> /etc/sysctl.conf")

        # Start Redis server
        try:
            subprocess.run(['service', 'redis-server', 'start'], check=True)
            logger.info("✅ Redis server started")
        except:
            logger.warning("⚠️  Failed to start Redis server")

        # Set environment variables for optimal performance
        os.environ['OMP_NUM_THREADS'] = str(min(8, self.system_info['cpu_count']))
        os.environ['MKL_NUM_THREADS'] = str(min(8, self.system_info['cpu_count']))
        os.environ['OPENBLAS_NUM_THREADS'] = str(min(8, self.system_info['cpu_count']))

    def _install_python_packages(self):
        """Install Python packages with Colab optimizations"""

        logger.info("🐍 Installing Python packages...")

        # Upgrade pip and essential tools
        subprocess.run([
            sys.executable, '-m', 'pip', 'install', '--upgrade',
            'pip', 'setuptools', 'wheel'
        ], check=True)

        # Install core ML frameworks
        if self.gpu_info['cuda_available']:
            # GPU-optimized PyTorch
            subprocess.run([
                sys.executable, '-m', 'pip', 'install',
                'torch', 'torchvision', 'torchaudio',
                '--index-url', 'https://download.pytorch.org/whl/cu121'
            ], check=True)

            # GPU-optimized TensorFlow
            subprocess.run([
                sys.executable, '-m', 'pip', 'install',
                'tensorflow[and-cuda]', 'tensorflow-hub'
            ], check=True)
        else:
            # CPU-only versions
            subprocess.run([
                sys.executable, '-m', 'pip', 'install',
                'torch', 'torchvision', 'torchaudio', '--index-url',
                'https://download.pytorch.org/whl/cpu'
            ], check=True)

            subprocess.run([
                sys.executable, '-m', 'pip', 'install',
                'tensorflow', 'tensorflow-hub'
            ], check=True)

        # Install audio processing packages
        audio_packages = [
            'demucs',
            'audio-separator',
            'basic-pitch',
            'librosa[display]',
            'soundfile',
            'resampy',
            'pretty_midi',
            'music21',
            'mir_eval',
            'pesq',
            'pystoi',
            'openl3',
            'yamnet',
            'transformers',
            'accelerate',
            'datasets'
        ]

        for package in audio_packages:
            try:
                subprocess.run([
                    sys.executable, '-m', 'pip', 'install', package
                ], check=True, capture_output=True)
                logger.debug(f"Installed: {package}")
            except subprocess.CalledProcessError as e:
                logger.warning(f"Failed to install {package}")

        # Install M3 Enhanced dependencies
        subprocess.run([
            sys.executable, '-m', 'pip', 'install',
            'fastapi', 'uvicorn[standard]', 'celery[redis]',
            'redis', 'aiofiles', 'python-multipart',
            'matplotlib', 'seaborn', 'plotly', 'pillow'
        ], check=True)

        logger.info("✅ Python packages installed")

    def _setup_directories(self):
        """Setup directory structure"""

        logger.info("📁 Setting up directories...")

        directories = [
            '/content/m3_enhanced',
            '/content/m3_enhanced/models',
            '/content/m3_enhanced/temp',
            '/content/m3_enhanced/uploads',
            '/content/m3_enhanced/results',
            '/content/m3_enhanced/logs'
        ]

        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created: {directory}")

        # Set permissions
        os.system("chmod -R 755 /content/m3_enhanced")

    def _download_models(self):
        """Download AI models"""

        logger.info("🤖 Downloading AI models...")

        # This would call the download_models.py script
        try:
            from download_models import ModelDownloader

            downloader = ModelDownloader(
                models_dir=Path('/content/m3_enhanced/models'),
                max_parallel_downloads=16  # Colab has fast internet
            )

            # Run async download
            import asyncio
            results = asyncio.run(downloader.download_all_models())

            success_count = sum(results.values())
            total_count = len(results)

            logger.info(f"✅ Downloaded {success_count}/{total_count} models")

        except Exception as e:
            logger.error(f"❌ Model download failed: {str(e)}")

    def _configure_environment(self):
        """Configure environment variables"""

        logger.info("🔧 Configuring environment...")

        env_vars = {
            'M3_MODELS_DIR': '/content/m3_enhanced/models',
            'M3_TEMP_DIR': '/content/m3_enhanced/temp',
            'M3_UPLOADS_DIR': '/content/m3_enhanced/uploads',
            'M3_RESULTS_DIR': '/content/m3_enhanced/results',
            'CELERY_BROKER_URL': 'redis://localhost:6379/0',
            'CELERY_RESULT_BACKEND': 'redis://localhost:6379/0',
            'PYTHONPATH': '/content/m3_enhanced',
        }

        if self.gpu_info['cuda_available']:
            env_vars.update({
                'CUDA_VISIBLE_DEVICES': '0',
                'PYTORCH_CUDA_ALLOC_CONF': 'max_split_size_mb:512',
                'TF_FORCE_GPU_ALLOW_GROWTH': 'true'
            })

        for key, value in env_vars.items():
            os.environ[key] = value
            logger.debug(f"Set {key}={value}")

    def _run_system_tests(self):
        """Run system validation tests"""

        logger.info("🧪 Running system tests...")

        tests = []

        # Test PyTorch
        try:
            import torch
            if torch.cuda.is_available() and self.gpu_info['cuda_available']:
                torch.zeros(1).cuda()
                tests.append(("PyTorch GPU", "✅ PASS"))
            else:
                torch.zeros(1)
                tests.append(("PyTorch CPU", "✅ PASS"))
        except Exception as e:
            tests.append(("PyTorch", f"❌ FAIL: {str(e)}"))

        # Test TensorFlow
        try:
            import tensorflow as tf
            if tf.config.list_physical_devices('GPU') and self.gpu_info['cuda_available']:
                tests.append(("TensorFlow GPU", "✅ PASS"))
            else:
                tests.append(("TensorFlow CPU", "✅ PASS"))
        except Exception as e:
            tests.append(("TensorFlow", f"❌ FAIL: {str(e)}"))

        # Test audio libraries
        try:
            import librosa
            import soundfile
            tests.append(("Audio Libraries", "✅ PASS"))
        except Exception as e:
            tests.append(("Audio Libraries", f"❌ FAIL: {str(e)}"))

        # Test Redis
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, db=0)
            r.ping()
            tests.append(("Redis", "✅ PASS"))
        except Exception as e:
            tests.append(("Redis", f"❌ FAIL: {str(e)}"))

        # Display results
        print("\n" + "="*40)
        print("SYSTEM TESTS")
        print("="*40)
        for test_name, result in tests:
            print(f"{test_name:20} {result}")
        print("="*40 + "\n")

    def _display_final_status(self):
        """Display final setup status"""

        print("\n" + "🎉"*20)
        print("M3 ENHANCED SETUP COMPLETE!")
        print("🎉"*20)

        print("\n📋 Quick Start Commands:")
        print("# Start the API server:")
        print("cd /content/m3_enhanced")
        print("python -m uvicorn app.main:app --host 0.0.0.0 --port 8000")

        print("\n# Start Celery workers:")
        print("celery -A app.core.job_scheduler worker --loglevel=info")

        print("\n🔗 Access URLs:")
        print("API Documentation: http://localhost:8000/docs")
        print("Job Monitor: http://localhost:5555 (if Flower is running)")

        print("\n💡 Tips:")
        print("- Use GPU runtime for best performance")
        print("- Monitor GPU memory usage with 'nvidia-smi'")
        print("- Check logs in /content/m3_enhanced/logs/")

        if not self.gpu_info['cuda_available']:
            print("\n⚠️  Warning: No GPU detected. Performance will be limited.")
            print("   Consider switching to GPU runtime in Colab settings.")

def main():
    """Main setup function"""

    optimizer = ColabOptimizer()

    if not optimizer.colab_detected:
        print("⚠️  This script is optimized for Google Colab.")
        print("   Some features may not work correctly in other environments.")

        response = input("Continue anyway? (y/N): ").strip().lower()
        if response != 'y':
            print("Setup cancelled.")
            return

    try:
        optimizer.setup_colab_environment()

        print("\n🎵 Ready to process audio with M3 Enhanced!")
        print("   Upload your audio files and let the magic happen! ✨")

    except KeyboardInterrupt:
        print("\n⚠️  Setup interrupted by user.")
    except Exception as e:
        print(f"\n❌ Setup failed: {str(e)}")
        logger.error(f"Setup error: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()
