#!/bin/bash
# M3 Enhanced - Intelligent Google Colab Setup Script (Shell Version)
# Automatically detects and optimizes for GPU/CPU runtimes
# Fixes Python package installation errors and non-interactive execution issues

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

# Runtime detection
detect_runtime() {
    log "🔍 Detecting runtime environment..."

    RUNTIME_TYPE="cpu"
    GPU_AVAILABLE=false
    GPU_NAME="None"
    GPU_MEMORY=0
    CPU_CORES=$(nproc)

    # Check for GPU using nvidia-smi
    if command -v nvidia-smi &> /dev/null; then
        if nvidia-smi &> /dev/null; then
            GPU_AVAILABLE=true
            RUNTIME_TYPE="gpu"
            GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader,nounits | head -1)
            GPU_MEMORY=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)
            log "🎮 GPU detected: $GPU_NAME (${GPU_MEMORY}MB)"
        fi
    fi

    # Fallback to CPU info
    if [ "$RUNTIME_TYPE" = "cpu" ]; then
        log "🖥️  CPU runtime: $CPU_CORES cores"
    fi

    # Check if we're in Colab
    if [ -d "/content" ] && [ -d "/opt/bin" ]; then
        COLAB_DETECTED=true
        log "📍 Google Colab environment detected"
    else
        COLAB_DETECTED=false
        warn "Not running in Google Colab - some optimizations may not apply"
    fi
}

# Configure device-specific settings
configure_devices() {
    log "⚙️  Configuring device-specific settings..."

    if [ "$GPU_AVAILABLE" = true ]; then
        TORCH_DEVICE="cuda"
        TF_DEVICE="/GPU:0"
        BATCH_SIZE=$((GPU_MEMORY / 2000))  # Rough estimate
        NUM_WORKERS=$((CPU_CORES > 4 ? 4 : CPU_CORES))
        log "📊 GPU config: device=$TORCH_DEVICE, batch_size=$BATCH_SIZE, workers=$NUM_WORKERS"
    else
        TORCH_DEVICE="cpu"
        TF_DEVICE="/CPU:0"
        BATCH_SIZE=1
        NUM_WORKERS=$((CPU_CORES > 8 ? 8 : CPU_CORES))
        log "📊 CPU config: device=$TORCH_DEVICE, batch_size=$BATCH_SIZE, workers=$NUM_WORKERS"
    fi
}

# Print banner
print_banner() {
    local runtime_emoji="🖥️"
    if [ "$GPU_AVAILABLE" = true ]; then
        runtime_emoji="🎮"
    fi

    echo ""
    echo "╔═════════════════════════════════════════════════════════════╗"
    echo "║                    🎵 M3 Enhanced 🎵                        ║"
    echo "║              Intelligent Colab Setup Script                 ║"
    echo "║                                                             ║"
    echo "║    Runtime: $runtime_emoji $(printf "%-10s" "${RUNTIME_TYPE^^}") Device: $(printf "%-10s" "$TORCH_DEVICE")          ║"
    echo "║    Advanced AI-Powered Music Processing Pipeline            ║"
    echo "║    • Audio Separation • Transcription • Analysis           ║"
    echo "╚═════════════════════════════════════════════════════════════╝"
    echo ""
}

# Display system information
display_system_info() {
    echo "============================================================"
    echo "M3 ENHANCED - GOOGLE COLAB SETUP"
    echo "============================================================"
    echo "🖥️  CPU Cores: $CPU_CORES"
    echo "💾 RAM: $(free -h | awk '/^Mem:/ {print $7"/"$2}') available"
    echo "💿 Disk: $(df -h / | awk 'NR==2 {print $4"/"$2}') free"

    if [ "$GPU_AVAILABLE" = true ]; then
        echo "🎮 GPU: $GPU_NAME"
        echo "🎮 VRAM: ${GPU_MEMORY}MB total"
    else
        echo "⚠️  No GPU detected - CPU-only mode"
    fi
    echo "============================================================"
    echo ""
}

# Install system dependencies with better error handling
install_system_dependencies() {
    log "📦 Installing system dependencies..."

    # Update package lists quietly
    apt-get update -qq || error "Failed to update package lists"

    # Essential audio processing tools with individual error handling
    local packages=(
        "ffmpeg"                # Media processing
        "libsndfile1-dev"      # Audio file I/O
        "libfftw3-dev"         # Fast Fourier Transform
        "flac"                 # FLAC codec
        "lame"                 # MP3 encoder
        "opus-tools"           # Opus codec
        "vorbis-tools"         # Ogg Vorbis
        "libmagic1"            # File type detection
        "redis-server"         # Job queue
        "htop"                 # System monitoring
        "build-essential"      # Compilation tools
        "pkg-config"           # Package configuration
        "libasound2-dev"       # ALSA development
        "portaudio19-dev"      # PortAudio
    )

    if [ "$GPU_AVAILABLE" = true ]; then
        packages+=("nvidia-cuda-toolkit" "nvtop")
    fi

    for package in "${packages[@]}"; do
        if apt-get install -y -qq "$package" 2>/dev/null; then
            log "✅ Installed: $package"
        else
            warn "Failed to install: $package (continuing...)"
        fi
    done

    # Start Redis server
    if service redis-server start 2>/dev/null; then
        log "✅ Redis server started"
    else
        warn "Failed to start Redis server"
    fi
}

# Optimize system settings
optimize_system_settings() {
    log "⚙️  Optimizing system settings..."

    # Increase file descriptor limits
    ulimit -n 65536 2>/dev/null || warn "Could not increase file descriptor limit"

    # Optimize memory settings (if we have permission)
    if [ -w /etc/sysctl.conf ]; then
        echo 'vm.swappiness=10' >> /etc/sysctl.conf
        echo 'vm.vfs_cache_pressure=50' >> /etc/sysctl.conf
    fi

    # Set environment variables for optimal performance
    export OMP_NUM_THREADS=$NUM_WORKERS
    export MKL_NUM_THREADS=$NUM_WORKERS
    export OPENBLAS_NUM_THREADS=$NUM_WORKERS
    export NUMBA_NUM_THREADS=$NUM_WORKERS

    if [ "$GPU_AVAILABLE" = true ]; then
        export CUDA_VISIBLE_DEVICES=0
        export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
        export TF_FORCE_GPU_ALLOW_GROWTH=true
        export TF_GPU_MEMORY_GROWTH=true
    fi

    log "✅ System optimization complete"
}

# Install Python packages with robust error handling
install_python_packages() {
    log "🐍 Installing Python packages for $RUNTIME_TYPE runtime..."

    # Upgrade pip and essential tools with retries
    python -m pip install --upgrade pip setuptools wheel --quiet --retries 3 --timeout 30

    # Install PyTorch based on runtime
    if [ "$GPU_AVAILABLE" = true ]; then
        log "📦 Installing PyTorch for GPU..."
        python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 --quiet --retries 3
        python -m pip install tensorflow[and-cuda] tensorflow-hub --quiet --retries 3
    else
        log "📦 Installing PyTorch for CPU..."
        python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu --quiet --retries 3
        python -m pip install tensorflow tensorflow-hub --quiet --retries 3
    fi

    # Core ML/Audio packages with individual error handling
    local ml_packages=(
        "transformers"
        "accelerate"
        "datasets"
        "librosa[display]"
        "soundfile"
        "pretty_midi"
        "music21"
    )

    for package in "${ml_packages[@]}"; do
        if python -m pip install "$package" --quiet --retries 3 --timeout 60; then
            log "✅ Installed: $package"
        else
            warn "Failed to install: $package"
        fi
    done

    # Audio processing packages that often fail - install with fallbacks
    local audio_packages=(
        "demucs"
        "basic-pitch"
        "audio-separator"
        "mir_eval"
        "pesq"
        "pystoi"
        "openl3"
    )

    for package in "${audio_packages[@]}"; do
        log "📦 Attempting to install: $package"
        if python -m pip install "$package" --quiet --retries 2 --timeout 120; then
            log "✅ Installed: $package"
        else
            warn "Failed to install: $package (may cause issues)"
            # Try installing without dependencies as fallback
            if python -m pip install "$package" --no-deps --quiet 2>/dev/null; then
                log "⚠️  Installed $package without dependencies"
            fi
        fi
    done

    # Web framework and utilities
    python -m pip install fastapi uvicorn[standard] python-multipart aiofiles --quiet
    python -m pip install redis celery[redis] --quiet
    python -m pip install yt-dlp python-magic matplotlib seaborn plotly pillow --quiet

    log "✅ Python package installation complete"
}

# Setup environment variables
setup_environment_variables() {
    log "🔧 Configuring environment variables..."

    # Export all variables to current session and write to bashrc
    {
        echo "export M3_RUNTIME_TYPE=$RUNTIME_TYPE"
        echo "export M3_DEVICE=$TORCH_DEVICE"
        echo "export M3_BATCH_SIZE=$BATCH_SIZE"
        echo "export M3_NUM_WORKERS=$NUM_WORKERS"
        echo "export PYTHONPATH=/content"
        echo "export OMP_NUM_THREADS=$NUM_WORKERS"
        echo "export MKL_NUM_THREADS=$NUM_WORKERS"
        echo "export OPENBLAS_NUM_THREADS=$NUM_WORKERS"
        echo "export NUMBA_NUM_THREADS=$NUM_WORKERS"

        if [ "$GPU_AVAILABLE" = true ]; then
            echo "export CUDA_VISIBLE_DEVICES=0"
            echo "export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512"
            echo "export TF_FORCE_GPU_ALLOW_GROWTH=true"
            echo "export TF_GPU_MEMORY_GROWTH=true"
        fi
    } >> ~/.bashrc

    # Source the variables for current session
    source ~/.bashrc

    log "✅ Environment variables configured"
}

# Setup ngrok with better error handling
setup_ngrok() {
    log "🌐 Setting up ngrok tunnel..."

    # Install pyngrok
    python -m pip install pyngrok --quiet

    # Try to get ngrok token from Colab secrets first
    NGROK_TOKEN=""
    if python -c "from google.colab import userdata; print(userdata.get('NGROK_TOKEN'))" 2>/dev/null | grep -v "None"; then
        NGROK_TOKEN=$(python -c "from google.colab import userdata; print(userdata.get('NGROK_TOKEN'))" 2>/dev/null)
        log "✅ Ngrok token found in Colab secrets"
    else
        warn "No NGROK_TOKEN found in Colab secrets"
        echo "Please add your ngrok token to Colab secrets as 'NGROK_TOKEN'"
        echo "Get your token from: https://dashboard.ngrok.com/get-started/your-authtoken"
        echo ""
        echo "To add to Colab secrets:"
        echo "1. Click the 🔑 key icon in the left sidebar"
        echo "2. Add a new secret named 'NGROK_TOKEN'"
        echo "3. Paste your ngrok auth token as the value"
        echo ""
        echo "Continuing without ngrok (local access only)..."
    fi

    if [ -n "$NGROK_TOKEN" ] && [ "$NGROK_TOKEN" != "None" ]; then
        python -c "from pyngrok import ngrok; ngrok.set_auth_token('$NGROK_TOKEN')" 2>/dev/null
        echo "export NGROK_TOKEN=$NGROK_TOKEN" >> ~/.bashrc
        log "✅ Ngrok authentication configured"
    fi
}

# Create project structure
create_project_structure() {
    log "📁 Creating project structure..."

    local directories=(
        "backend/app/core"
        "backend/app/models"
        "backend/app/processors"
        "backend/app/utils"
        "frontend/static"
        "models"
        "temp"
        "uploads"
        "results"
        "logs"
    )

    for directory in "${directories[@]}"; do
        mkdir -p "$directory"
        chmod 755 "$directory"
    done

    log "✅ Project structure created"
}

# Download models with error handling
download_models() {
    log "🤖 Downloading AI models for $RUNTIME_TYPE runtime..."

    # Create models directory
    mkdir -p models

    # Download Demucs models
    log "📦 Downloading Demucs separation model..."
    if python -c "import demucs; demucs.pretrained.get_model('htdemucs')" 2>/dev/null; then
        log "✅ Demucs model downloaded"
    else
        warn "Failed to download Demucs model"
    fi

    # Initialize Basic Pitch
    log "📦 Initializing Basic Pitch model..."
    if python -c "from basic_pitch import ICASSP_2022_MODEL_PATH; print('Basic Pitch initialized')" 2>/dev/null; then
        log "✅ Basic Pitch model initialized"
    else
        warn "Failed to initialize Basic Pitch model"
    fi
}

# Run system tests
run_system_tests() {
    log "🧪 Running $RUNTIME_TYPE system tests..."

    echo ""
    echo "=================================================="
    echo "$RUNTIME_TYPE SYSTEM TESTS"
    echo "=================================================="

    # Test PyTorch
    if python -c "import torch; print('PyTorch version:', torch.__version__)" 2>/dev/null; then
        if [ "$GPU_AVAILABLE" = true ]; then
            if python -c "import torch; torch.zeros(1).cuda(); print('GPU tensor creation successful')" 2>/dev/null; then
                echo "PyTorch GPU               ✅ PASS"
            else
                echo "PyTorch GPU               ❌ FAIL"
            fi
        else
            if python -c "import torch; torch.zeros(1); print('CPU tensor creation successful')" 2>/dev/null; then
                echo "PyTorch CPU               ✅ PASS"
            else
                echo "PyTorch CPU               ❌ FAIL"
            fi
        fi
    else
        echo "PyTorch                   ❌ FAIL: Not installed"
    fi

    # Test TensorFlow
    if python -c "import tensorflow as tf; print('TensorFlow version:', tf.__version__)" 2>/dev/null; then
        echo "TensorFlow                ✅ PASS"
    else
        echo "TensorFlow                ❌ FAIL: Not installed"
    fi

    # Test audio libraries
    if python -c "import librosa, soundfile; print('Audio libraries working')" 2>/dev/null; then
        echo "Audio Libraries           ✅ PASS"
    else
        echo "Audio Libraries           ❌ FAIL"
    fi

    # Test Redis
    if python -c "import redis; r=redis.Redis(); r.ping(); print('Redis working')" 2>/dev/null; then
        echo "Redis                     ✅ PASS"
    else
        echo "Redis                     ❌ FAIL"
    fi

    echo "=================================================="
    echo ""
}

# Display final status
display_final_status() {
    local runtime_emoji="🖥️"
    if [ "$GPU_AVAILABLE" = true ]; then
        runtime_emoji="🎮"
    fi

    echo ""
    echo "🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉"
    echo "       M3 ENHANCED SETUP COMPLETE!"
    echo "🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉"
    echo ""
    echo "📋 Quick Start Commands:"
    echo "# Navigate to project directory:"
    echo "cd /content"
    echo ""
    echo "# Start the API server:"
    echo "python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"
    echo ""
    echo "# Start Celery workers:"
    echo "celery -A backend.app.core.job_scheduler worker --loglevel=info"
    echo ""
    echo "🔗 Access URLs:"
    echo "API Documentation: http://localhost:8000/docs"
    echo "Job Monitor: http://localhost:5555 (if Flower is running)"
    echo ""
    echo "💡 Tips:"
    echo "- Use GPU runtime for best performance"
    if [ "$GPU_AVAILABLE" = true ]; then
        echo "- Monitor GPU memory usage with 'nvidia-smi'"
    fi
    echo "- Check logs in /content/logs/"
    echo ""
    echo "$runtime_emoji Runtime: $RUNTIME_TYPE | Device: $TORCH_DEVICE | Batch Size: $BATCH_SIZE | Workers: $NUM_WORKERS"

    if [ "$GPU_AVAILABLE" = false ]; then
        echo ""
        warn "No GPU detected. Performance will be limited."
        echo "   Consider switching to GPU runtime in Colab settings."
    fi
}

# Main setup function
main() {
    log "🚀 Starting M3 Enhanced setup..."

    detect_runtime
    configure_devices
    print_banner
    display_system_info

    install_system_dependencies
    optimize_system_settings
    install_python_packages
    setup_environment_variables
    setup_ngrok
    create_project_structure
    download_models
    run_system_tests

    display_final_status

    echo ""
    log "🎵 Ready to process audio with M3 Enhanced!"
    log "   Upload your audio files and let the magic happen! ✨"
}

# Check if running directly
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi
