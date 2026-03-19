# M3 Enhanced 

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

## Usage

### Web Interface

1. Navigate to http://localhost:8000
2. Upload your audio file (MP3, WAV, FLAC, M4A)
3. Select processing options:
   - Separation model (Demucs/MVSEP)
   - Transcription model (YourMT3+/MT3/BasicPitch)
   - Output formats
4. Monitor progress in real-time
5. Download your results as a ZIP package


### Command Line Interface

```bash
# Process a single file
python -m app.cli process song.mp3 --model demucs --transcribe --tabs

# Batch processing
python -m app.cli batch /path/to/songs/ --output /path/to/results/

# Benchmark models
python scripts/benchmark_models.py --audio test_song.wav
```


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


##  Testing

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




##  Documentation

- [Setup Guide](docs/SETUP.md) - Detailed installation instructions
- [API Documentation](docs/API.md) - Complete API reference
- [Pipeline Architecture](docs/PIPELINE.md) - Technical architecture overview
- [Model Guide](docs/MODELS.md) - AI model documentation
- [Deployment Guide](docs/DEPLOYMENT.md) - Production deployment


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
