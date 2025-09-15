# Setup Guide - M3 Enhanced

## Overview
M3 Enhanced is a comprehensive music processing pipeline that combines multiple AI models for audio separation, transcription, and analysis. This guide will help you set up the development and production environments.

## Prerequisites

### System Requirements
- Python 3.8+
- Docker and Docker Compose
- Redis server
- FFmpeg
- GPU support (recommended for optimal performance)
- Minimum 8GB RAM (16GB+ recommended)
- 10GB+ storage for models

### Hardware Recommendations
- **GPU**: NVIDIA GPU with CUDA support for accelerated processing
- **CPU**: Multi-core processor (8+ cores recommended)
- **Storage**: SSD recommended for model loading and temporary file processing

## Installation Methods

### Method 1: Docker Setup (Recommended)

1. **Clone the repository**
```bash
git clone https://github.com/pieman909/m3_enhanced.git
cd m3_enhanced
```

2. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your specific configuration
```

3. **Build and start services**
```bash
# For development
docker-compose up --build

# For production with GPU support
docker-compose -f docker-compose.yml -f backend/docker/docker-compose.yml up --build
```

### Method 2: Local Development Setup

1. **Clone and navigate to repository**
```bash
git clone https://github.com/pieman909/m3_enhanced.git
cd m3_enhanced
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
# Backend dependencies
cd backend
pip install -r requirements.txt

# Development dependencies
pip install -r ../requirements-dev.txt
```

4. **Download AI models**
```bash
python scripts/download_models.py
```

5. **Set up Redis**
```bash
# Install Redis locally or use Docker
docker run -d -p 6379:6379 redis:alpine
```

6. **Configure environment**
```bash
cp .env.example .env
# Edit configuration as needed
```

## Configuration

### Environment Variables (.env)
```env
# Database
REDIS_URL=redis://localhost:6379

# Model Paths
MODELS_DIR=./models
TEMP_DIR=./temp
UPLOADS_DIR=./uploads
RESULTS_DIR=./results

# Processing Settings
MAX_WORKERS=4
GPU_ENABLED=true
BATCH_SIZE=8

# API Settings
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false

# Model Selection
DEFAULT_SEPARATOR=demucs
DEFAULT_TRANSCRIBER=yourmt3_plus
ENABLE_CLASSIFICATION=true
```

### Model Configuration
The system supports multiple AI models:

- **Separation**: Demucs, MVSEP-MDX23
- **Transcription**: YourMT3+, MT3, BasicPitch
- **Classification**: YAMNet, OpenL3

Models are automatically downloaded on first use or can be pre-downloaded using:
```bash
python backend/scripts/download_models.py
```

## Google Colab Setup

For cloud-based processing:

1. **Upload the colab setup script**
```python
!wget https://raw.githubusercontent.com/pieman909/m3_enhanced/main/backend/scripts/colab_setup.py
!python colab_setup.py
```

2. **Install dependencies**
```python
!pip install -r requirements.txt
```

## Verification

### Test Installation
```bash
# Run basic tests
python -m pytest tests/

# Test specific components
python -m pytest tests/test_separation.py
python -m pytest tests/test_transcription.py

# Integration test
python -m pytest tests/integration/test_full_pipeline.py
```

### API Health Check
```bash
curl http://localhost:8000/health
```

### Web Interface
Navigate to `http://localhost:8000` to access the web interface.

## Troubleshooting

### Common Issues

**GPU not detected**
- Ensure CUDA drivers are installed
- Verify GPU support: `nvidia-smi`
- Check PyTorch GPU installation: `python -c "import torch; print(torch.cuda.is_available())"`

**Model download failures**
- Check internet connection
- Verify disk space (10GB+ required)
- Try manual download with `python backend/scripts/download_models.py --model <specific_model>`

**Memory issues**
- Reduce batch size in configuration
- Enable model quantization
- Use CPU-only mode for smaller files

**Audio processing errors**
- Ensure FFmpeg is properly installed
- Check supported audio formats
- Verify file permissions in upload directory

### Performance Optimization

1. **Enable GPU acceleration**
```bash
# Install CUDA-enabled PyTorch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

2. **Optimize for production**
```bash
# Use production Docker configuration
docker-compose -f docker-compose.prod.yml up
```

3. **Model caching**
- Pre-load frequently used models
- Enable model quantization for faster inference
- Use SSD storage for model files

## Next Steps

1. Review the [API Documentation](API.md) for integration details
2. Check the [Pipeline Documentation](PIPELINE.md) for architecture overview
3. Run benchmark tests: `python backend/scripts/benchmark_models.py`
4. Configure monitoring and logging for production use

## Support

For issues and questions:
- Check existing GitHub issues
- Review troubleshooting section above
- Submit new issues with detailed error logs and system information
