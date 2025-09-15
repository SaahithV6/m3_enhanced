# M3 Enhanced 🎵

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![GPU Accelerated](https://img.shields.io/badge/GPU-Accelerated-green.svg)](https://developer.nvidia.com/cuda-zone)

An advanced AI-powered music processing pipeline that combines state-of-the-art models for audio separation, multi-track transcription, and comprehensive music analysis. Transform any audio file into separated tracks, MIDI transcriptions, guitar tablature, and sheet music with studio-grade quality.

## ✨ Features

### 🎛️ Audio Separation
- **Multiple AI Models**: Demucs v4, MVSEP-MDX23 for ultra-high quality separation
- **Instrument Isolation**: Vocals, drums, bass, guitar, and other instruments
- **Guitar Analysis**: Automatic lead/rhythm guitar separation
- **Quality Metrics**: SDR, SIR, SAR evaluation for transparency

### 🎼 Multi-Track Transcription
- **Advanced Models**: YourMT3+, Google MT3, Spotify BasicPitch
- **Polyphonic Support**: Multiple instruments and notes simultaneously
- **High Accuracy**: Up to 85% F1 score on complex musical content
- **MIDI Output**: Standard MIDI files with velocity and timing

### 🎸 Tablature Generation
- **Guitar Tabs**: Optimized fingering and notation
- **Bass Tabs**: Complete bass line transcription
- **Multiple Formats**: GuitarPro, TuxGuitar, ASCII tabs

### 📊 Music Analysis
- **Key Detection**: Automatic key and scale identification
- **Tempo Analysis**: BPM and time signature detection
- **Chord Progression**: Harmonic analysis and chord sequences
- **Instrument Classification**: YAMNet and OpenL3 powered identification

### 🎨 Output Formats
- **Sheet Music**: MusicXML and PDF notation
- **MIDI Files**: Multi-track MIDI with complete arrangements
- **Audio Tracks**: High-quality separated stems
- **Comprehensive Reports**: Analysis summaries and quality metrics

## 🚀 Quick Start

### Docker Setup (Recommended)

1. **Clone the repository**
```bash
git clone https://github.com/pieman909/m3_enhanced.git
cd m3_enhanced
```

2. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your preferences
```

3. **Start the application**
```bash
# Development environment
docker-compose up --build

# Production with GPU acceleration
docker-compose -f backend/docker/docker-compose.yml up --build
```

4. **Access the application**
- Web Interface: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Monitoring Dashboard: http://localhost:5555

### Local Development

1. **Prerequisites**
```bash
# Install system dependencies
sudo apt-get install ffmpeg redis-server
# For GPU support: NVIDIA drivers + CUDA toolkit
```

2. **Python environment**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r backend/requirements.txt
pip install -r requirements-dev.txt
```

3. **Download AI models**
```bash
cd backend
python scripts/download_models.py
```

4. **Start services**
```bash
# Start Redis
redis-server

# Start API server
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start Celery worker (separate terminal)
celery -A app.core.job_scheduler worker --loglevel=info
```

## 📖 Usage

### Web Interface

1. Navigate to http://localhost:8000
2. Upload your audio file (MP3, WAV, FLAC, M4A)
3. Select processing options:
   - Separation model (Demucs/MVSEP)
   - Transcription model (YourMT3+/MT3/BasicPitch)
   - Output formats
4. Monitor progress in real-time
5. Download your results as a ZIP package

### API Usage

```python
import requests

# Upload and start processing
files = {'file': open('song.mp3', 'rb')}
data = {
    'separation_model': 'demucs',
    'transcription_model': 'yourmt3_plus',
    'generate_tabs': True
}

response = requests.post('http://localhost:8000/process', files=files, data=data)
job = response.json()
print(f"Job started: {job['job_id']}")

# Check status
status = requests.get(f"http://localhost:8000/jobs/{job['job_id']}")
print(status.json())

# Download results when complete
results = requests.get(f"http://localhost:8000/jobs/{job['job_id']}/download")
with open('results.zip', 'wb') as f:
    f.write(results.content)
```

### Command Line Interface

```bash
# Process a single file
python -m app.cli process song.mp3 --model demucs --transcribe --tabs

# Batch processing
python -m app.cli batch /path/to/songs/ --output /path/to/results/

# Benchmark models
python scripts/benchmark_models.py --audio test_song.wav
```

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web UI        │    │   FastAPI       │    │   AI Models     │
│                 │◄──►│                 │◄──►│                 │
│ • Upload        │    │ • REST API      │    │ • Demucs        │
│ • Progress      │    │ • WebSockets    │    │ • YourMT3+      │
│ • Downloads     │    │ • Job Queue     │    │ • YAMNet        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Redis Queue   │    │   File Storage  │
                       │                 │    │                 │
                       │ • Celery        │    │ • Models        │
                       │ • Monitoring    │    │ • Results       │
                       │ • Caching       │    │ • Temporary     │
                       └─────────────────┘    └─────────────────┘
```

### Processing Pipeline

1. **Input Processing**: Format validation, enhancement, normalization
2. **Audio Separation**: AI-powered source separation using Demucs/MVSEP
3. **Classification**: Instrument identification with YAMNet/OpenL3
4. **Transcription**: Multi-track MIDI generation with YourMT3+/MT3
5. **Analysis**: Key detection, tempo, chord progression analysis
6. **Output Generation**: Tablature, sheet music, and packaged results

## 🛠️ Configuration

### Environment Variables

```bash
# Core Settings
DEBUG=False
API_HOST=0.0.0.0
API_PORT=8000

# Redis & Job Queue
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0

# Model Configuration
MODELS_DIR=./models
DEFAULT_SEPARATOR=demucs
DEFAULT_TRANSCRIBER=yourmt3_plus
GPU_ENABLED=true
MAX_WORKERS=4

# Processing Limits
MAX_FILE_SIZE=100MB
MAX_DURATION=600  # 10 minutes
BATCH_SIZE=8

# Storage Paths
UPLOADS_DIR=./uploads
RESULTS_DIR=./results
TEMP_DIR=./temp
```

### Model Selection

| Model | Purpose | Quality | Speed | Memory |
|-------|---------|---------|-------|--------|
| Demucs v4 | Audio Separation | High | Fast | 2.3GB |
| MVSEP-MDX23 | Audio Separation | Ultra | Medium | 4.1GB |
| YourMT3+ | Transcription | Highest | Medium | 800MB |
| MT3 | Transcription | High | Fast | 600MB |
| BasicPitch | Transcription | Good | Fastest | 200MB |

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/

# Specific test suites
python -m pytest tests/test_separation.py -v
python -m pytest tests/test_transcription.py -v
python -m pytest tests/integration/test_full_pipeline.py -v

# Performance benchmarks
python backend/scripts/benchmark_models.py
```

## 📊 Performance

### Benchmarks (3-minute song)

| Configuration | Separation | Transcription | Total Time |
|---------------|------------|---------------|------------|
| GPU (RTX 3080) | 45s | 30s | ~2 min |
| GPU (GTX 1060) | 90s | 60s | ~3 min |
| CPU (8-core) | 300s | 180s | ~8 min |

### Quality Metrics

- **Audio Separation**: 12-15 dB SDR average
- **Transcription Accuracy**: 80-85% F1 score
- **Processing Success Rate**: >95%
- **GPU Memory Usage**: 4-6GB peak

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Clone and setup
git clone https://github.com/pieman909/m3_enhanced.git
cd m3_enhanced

# Install development dependencies
pip install -r requirements-dev.txt

# Setup pre-commit hooks
pre-commit install

# Run tests
python -m pytest
```

### Adding New Models

1. Implement model wrapper in `backend/app/models/`
2. Add configuration to `backend/app/models/model_configs.py`
3. Update model manager in `backend/app/models/model_manager.py`
4. Add tests in `tests/test_models/`

## 📚 Documentation

- [Setup Guide](docs/SETUP.md) - Detailed installation instructions
- [API Documentation](docs/API.md) - Complete API reference
- [Pipeline Architecture](docs/PIPELINE.md) - Technical architecture overview
- [Model Guide](docs/MODELS.md) - AI model documentation
- [Deployment Guide](docs/DEPLOYMENT.md) - Production deployment

## 🐛 Troubleshooting

### Common Issues

**GPU not detected**
```bash
# Check CUDA installation
nvidia-smi
python -c "import torch; print(torch.cuda.is_available())"
```

**Out of memory errors**
- Reduce batch size in configuration
- Use CPU-only processing for large files
- Enable model quantization

**Audio processing fails**
- Ensure FFmpeg is installed and in PATH
- Check file format compatibility
- Verify file integrity

### Getting Help

1. Check [Issues](https://github.com/pieman909/m3_enhanced/issues) for existing solutions
2. Review [Troubleshooting Guide](docs/TROUBLESHOOTING.md)
3. Submit detailed bug reports with logs and system info

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Facebook Research** - Demucs audio separation
- **Google Research** - MT3 music transcription
- **Spotify** - BasicPitch transcription model
- **LAION** - Audio classification models
- **Community Contributors** - Open source improvements

## 🌟 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=pieman909/m3_enhanced&type=Date)](https://star-history.com/#pieman909/m3_enhanced&Date)

---

**Built with ❤️ for the music community**

Transform your audio with AI-powered precision. From bedroom recordings to professional productions, M3 Enhanced delivers studio-grade results for musicians, producers, and audio enthusiasts worldwide.
