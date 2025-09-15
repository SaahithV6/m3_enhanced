#!/bin/bash
# M3 Enhanced - Complete Setup Script
# This script sets up the entire M3 Enhanced system for local development

set -e  # Exit on any error

echo "🎵 M3 Enhanced - Complete Setup Script 🎵"
echo "==========================================="

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "Please don't run this script as root"
   exit 1
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# System requirements check
print_status "Checking system requirements..."

# Check Ubuntu/Debian
if ! command_exists apt; then
    print_error "This script requires Ubuntu/Debian with apt package manager"
    exit 1
fi

# Update system
print_status "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install system dependencies
print_status "Installing system dependencies..."
sudo apt install -y \
    curl \
    wget \
    git \
    build-essential \
    software-properties-common \
    python3.10 \
    python3.10-dev \
    python3-pip \
    python3.10-venv \
    ffmpeg \
    libsndfile1 \
    libsndfile1-dev \
    libasound2-dev \
    portaudio19-dev \
    libportaudio2 \
    libfftw3-dev \
    lame \
    flac \
    vorbis-tools \
    opus-tools \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libmagic1 \
    file \
    redis-server \
    nginx

# Install Docker if not present
if ! command_exists docker; then
    print_status "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    print_warning "Please log out and back in for Docker permissions to take effect"
fi

# Install Docker Compose if not present
if ! command_exists docker-compose; then
    print_status "Installing Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# Create Python virtual environment
print_status "Creating Python virtual environment..."
python3.10 -m venv venv
source venv/bin/activate

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install PyTorch with CUDA support (if available)
print_status "Installing PyTorch..."
if command_exists nvidia-smi; then
    print_status "NVIDIA GPU detected, installing CUDA-enabled PyTorch..."
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
else
    print_status "No NVIDIA GPU detected, installing CPU-only PyTorch..."
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
fi

# Install requirements
if [ -f "requirements.txt" ]; then
    print_status "Installing Python requirements..."
    pip install -r requirements.txt
else
    print_status "Installing core dependencies manually..."
    pip install \
        fastapi \
        uvicorn[standard] \
        redis \
        celery[redis] \
        demucs \
        basic-pitch \
        librosa[display] \
        soundfile \
        pretty_midi \
        music21 \
        mir_eval \
        tensorflow \
        tensorflow-hub \
        transformers \
        accelerate \
        yt-dlp \
        python-magic \
        matplotlib \
        seaborn \
        plotly \
        pillow \
        python-multipart \
        aiofiles
fi

# Create necessary directories
print_status "Creating project directories..."
mkdir -p models temp uploads results logs

# Create environment file
print_status "Creating environment configuration..."
cat > .env << EOF
# M3 Enhanced Configuration
DEBUG=true
LOG_LEVEL=info

# Paths
MODELS_DIR=./models
TEMP_DIR=./temp
UPLOADS_DIR=./uploads
RESULTS_DIR=./results

# Redis
REDIS_URL=redis://localhost:6379/0

# API Settings
API_HOST=0.0.0.0
API_PORT=8000
MAX_FILE_SIZE=104857600  # 100MB
ALLOWED_EXTENSIONS=.mp3,.wav,.flac,.m4a,.aac,.ogg,.wma

# Processing
DEFAULT_SEPARATION_MODEL=demucs
DEFAULT_TRANSCRIPTION_MODEL=yourmt3_plus
ENABLE_GPU=true
MAX_CONCURRENT_JOBS=3

# Security
SECRET_KEY=$(openssl rand -hex 32)
EOF

# Start Redis server
print_status "Starting Redis server..."
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Download essential models (in background)
print_status "Starting model downloads..."
cat > download_models.py << 'EOF'
#!/usr/bin/env python3
import os
import sys
import subprocess
from pathlib import Path

def download_model(model_name, download_cmd):
    print(f"Downloading {model_name}...")
    try:
        subprocess.run(download_cmd, shell=True, check=True)
        print(f"✓ {model_name} downloaded successfully")
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to download {model_name}: {e}")

def main():
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)
    os.chdir(models_dir)

    # Download core models
    models = [
        ("Demucs v4", "python -m demucs.separate --download"),
        ("Basic Pitch", "python -c 'import basic_pitch; basic_pitch.ICASSP_2022_MODEL_PATH'"),
    ]

    for model_name, cmd in models:
        download_model(model_name, cmd)

if __name__ == "__main__":
    main()
EOF

python download_models.py &
MODEL_DOWNLOAD_PID=$!

# Create systemd service for the application
print_status "Creating systemd service..."
sudo tee /etc/systemd/system/m3-enhanced.service > /dev/null << EOF
[Unit]
Description=M3 Enhanced Audio Processing Service
After=network.target redis.service

[Service]
Type=forking
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
ExecStart=$(pwd)/venv/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Create Celery worker service
sudo tee /etc/systemd/system/m3-celery.service > /dev/null << EOF
[Unit]
Description=M3 Enhanced Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
ExecStart=$(pwd)/venv/bin/celery -A backend.app.core.job_scheduler worker --loglevel=info
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Create start script
print_status "Creating start script..."
cat > start_m3.sh << 'EOF'
#!/bin/bash
# M3 Enhanced - Start Script

echo "🎵 Starting M3 Enhanced System..."

# Activate virtual environment
source venv/bin/activate

# Check Redis
if ! pgrep -x "redis-server" > /dev/null; then
    echo "Starting Redis..."
    sudo systemctl start redis-server
fi

# Start Celery worker in background
echo "Starting Celery worker..."
celery -A backend.app.core.job_scheduler worker --loglevel=info --detach

# Start FastAPI server
echo "Starting FastAPI server..."
echo "🌐 Web interface will be available at: http://localhost:8000"
echo "📚 API documentation available at: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"

uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
EOF

chmod +x start_m3.sh

# Create stop script
cat > stop_m3.sh << 'EOF'
#!/bin/bash
echo "Stopping M3 Enhanced System..."
pkill -f celery
pkill -f uvicorn
echo "System stopped."
EOF

chmod +x stop_m3.sh

# Wait for model downloads to complete
print_status "Waiting for model downloads to complete..."
wait $MODEL_DOWNLOAD_PID

# Final setup
sudo systemctl daemon-reload

print_success "Setup completed successfully!"
echo ""
echo "🎉 M3 Enhanced is ready to use!"
echo ""
echo "To start the system:"
echo "  ./start_m3.sh"
echo ""
echo "To stop the system:"
echo "  ./stop_m3.sh"
echo ""
echo "Web interface: http://localhost:8000"
echo "API docs: http://localhost:8000/docs"
echo ""
print_warning "If you installed Docker for the first time, please log out and back in"
print_warning "Then you can use Docker Compose for containerized deployment"
