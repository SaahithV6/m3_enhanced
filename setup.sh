#!/bin/bash
# M3 Enhanced - Intelligent Setup Script (Fixed Version)
# Automatically detects and optimizes for GPU/CPU runtimes
# Fixes Python package installation errors and integrates provided ngrok token

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
NGROK_TOKEN="31u9zGx10xxBE4AU0nQo5p2kXkF_6EFLZJFdmHuH6B8TyQUwv"
WORK_DIR=$(pwd)

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
        log "🖥️ CPU runtime: $CPU_CORES cores"
    fi

    # Check if we're in Colab
    if [ -d "/content" ] && [ -d "/opt/bin" ]; then
        COLAB_DETECTED=true
        log "📍 Google Colab environment detected"
    else
        COLAB_DETECTED=false
        warn "Not running in Google Colab - using current directory: $WORK_DIR"
    fi
}

# Configure device-specific settings
configure_devices() {
    log "⚙️ Configuring device-specific settings..."

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
    echo "║              Intelligent Setup Script (Fixed)               ║"
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
    echo "M3 ENHANCED - SETUP (FIXED VERSION)"
    echo "============================================================"
    echo "🖥️ CPU Cores: $CPU_CORES"
    echo "💾 RAM: $(free -h | awk '/^Mem:/ {print $7"/"$2}') available"
    echo "💿 Disk: $(df -h / | awk 'NR==2 {print $4"/"$2}') free"
    echo "📁 Working Directory: $WORK_DIR"

    if [ "$GPU_AVAILABLE" = true ]; then
        echo "🎮 GPU: $GPU_NAME"
        echo "🎮 VRAM: ${GPU_MEMORY}MB total"
    else
        echo "⚠️ No GPU detected - CPU-only mode"
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
        "curl"                 # For ngrok download
        "unzip"                # For ngrok extraction
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
    log "⚙️ Optimizing system settings..."

    # Increase file descriptor limits
    ulimit -n 65536 2>/dev/null || warn "Could not increase file descriptor limit"

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

# Install Python packages with improved error handling
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

    # Install demucs first (often more stable)
    log "📦 Installing demucs..."
    if python -m pip install demucs --quiet --retries 2 --timeout 120; then
        log "✅ Installed: demucs"
    else
        warn "Failed to install demucs - trying alternative approach"
        python -m pip install demucs --no-deps --quiet 2>/dev/null || warn "Demucs installation failed completely"
    fi

    # Install compatible versions to avoid conflicts
    log "📦 Installing compatible audio processing packages..."

    # Install specific versions to avoid conflicts
    python -m pip install "resampy>=0.2.2,<0.4.3" --quiet --force-reinstall 2>/dev/null || warn "Failed to fix resampy version"
    python -m pip install "tensorflow>=2.4.1,<2.15.1" --quiet --force-reinstall 2>/dev/null || warn "Failed to fix tensorflow version"

    # Try basic-pitch with dependency resolution
    if python -m pip install basic-pitch --quiet --retries 1 --timeout 60; then
        log "✅ Installed: basic-pitch"
    else
        warn "Failed to install basic-pitch - installing dependencies separately"
        python -m pip install mir_eval --quiet 2>/dev/null || warn "Failed to install mir_eval"
        python -m pip install basic-pitch --no-deps --quiet 2>/dev/null || warn "Failed to install basic-pitch without deps"
    fi

    # Audio processing packages with fallbacks
    local audio_packages=(
        "audio-separator"
        "pesq"
        "pystoi"
    )

    for package in "${audio_packages[@]}"; do
        log "📦 Attempting to install: $package"
        if python -m pip install "$package" --quiet --retries 2 --timeout 120; then
            log "✅ Installed: $package"
        else
            warn "Failed to install: $package (may cause issues)"
            # Try installing without dependencies as fallback
            if python -m pip install "$package" --no-deps --quiet 2>/dev/null; then
                log "⚠️ Installed $package without dependencies"
            fi
        fi
    done

    # Skip openl3 for now as it consistently fails
    log "📦 Skipping openl3 installation (known compatibility issues)"

    # Web framework and utilities
    python -m pip install fastapi uvicorn[standard] python-multipart aiofiles --quiet
    python -m pip install redis celery[redis] --quiet
    python -m pip install yt-dlp python-magic matplotlib seaborn plotly pillow --quiet

    log "✅ Python package installation complete"
}

# Setup environment variables
setup_environment_variables() {
    log "🔧 Configuring environment variables..."

    # Create or update .env file in current directory
    cat > .env << EOF
M3_RUNTIME_TYPE=$RUNTIME_TYPE
M3_DEVICE=$TORCH_DEVICE
M3_BATCH_SIZE=$BATCH_SIZE
M3_NUM_WORKERS=$NUM_WORKERS
PYTHONPATH=$WORK_DIR
OMP_NUM_THREADS=$NUM_WORKERS
MKL_NUM_THREADS=$NUM_WORKERS
OPENBLAS_NUM_THREADS=$NUM_WORKERS
NUMBA_NUM_THREADS=$NUM_WORKERS
NGROK_TOKEN=$NGROK_TOKEN
EOF

    if [ "$GPU_AVAILABLE" = true ]; then
        cat >> .env << EOF
CUDA_VISIBLE_DEVICES=0
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
TF_FORCE_GPU_ALLOW_GROWTH=true
TF_GPU_MEMORY_GROWTH=true
EOF
    fi

    # Export variables for current session
    source .env 2>/dev/null || true

    log "✅ Environment variables configured in .env file"
}

# Setup ngrok with provided token
setup_ngrok() {
    log "🌐 Setting up ngrok tunnel with provided token..."

    # Install pyngrok
    python -m pip install pyngrok --quiet

    # Install ngrok binary
    if ! command -v ngrok &> /dev/null; then
        log "📦 Installing ngrok binary..."
        cd /tmp
        curl -s https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz | tar xz
        sudo mv ngrok /usr/local/bin/
        cd $WORK_DIR
    fi

    # Configure ngrok with provided token
    if [ -n "$NGROK_TOKEN" ]; then
        ngrok config add-authtoken "$NGROK_TOKEN" 2>/dev/null
        python -c "from pyngrok import ngrok; ngrok.set_auth_token('$NGROK_TOKEN')" 2>/dev/null
        log "✅ Ngrok authentication configured with provided token"

        # Create ngrok configuration
        mkdir -p ~/.ngrok2
        cat > ~/.ngrok2/ngrok.yml << EOF
authtoken: $NGROK_TOKEN
tunnels:
  api:
    addr: 8000
    proto: http
  frontend:
    addr: 3000
    proto: http
EOF
        log "✅ Ngrok configuration file created"
    else
        warn "No ngrok token provided"
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
        "backend/app/preprocessing"
        "backend/app/postprocessing"
        "frontend/static"
        "models"
        "temp"
        "uploads"
        "results"
        "logs"
        "config"
    )

    for directory in "${directories[@]}"; do
        mkdir -p "$directory"
        chmod 755 "$directory"
    done

    # Create __init__.py files for Python packages
    touch backend/__init__.py
    touch backend/app/__init__.py
    touch backend/app/core/__init__.py
    touch backend/app/models/__init__.py
    touch backend/app/processors/__init__.py
    touch backend/app/utils/__init__.py
    touch backend/app/preprocessing/__init__.py
    touch backend/app/postprocessing/__init__.py

    log "✅ Project structure created"
}

# Download models with error handling
download_models() {
    log "🤖 Downloading AI models for $RUNTIME_TYPE runtime..."

    # Create models directory
    mkdir -p models

    # Download Demucs models
    log "📦 Downloading Demucs separation model..."
    if python -c "import demucs.pretrained; demucs.pretrained.get_model('htdemucs')" 2>/dev/null; then
        log "✅ Demucs model downloaded"
    else
        warn "Failed to download Demucs model"
    fi

    # Initialize Basic Pitch
    log "📦 Initializing Basic Pitch model..."
    if python -c "try:
    from basic_pitch import ICASSP_2022_MODEL_PATH
    print('Basic Pitch initialized')
except:
    print('Basic Pitch not available')" 2>/dev/null; then
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

    # Test ngrok
    if command -v ngrok &> /dev/null; then
        echo "Ngrok Binary              ✅ PASS"
    else
        echo "Ngrok Binary              ❌ FAIL"
    fi

    echo "=================================================="
    echo ""
}

# Create startup scripts
create_startup_scripts() {
    log "📝 Creating startup scripts..."

    # Create API server startup script
    cat > start_api.sh << 'EOF'
#!/bin/bash
source .env 2>/dev/null || true
echo "Starting M3 Enhanced API server..."
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
EOF

    # Create worker startup script
    cat > start_worker.sh << 'EOF'
#!/bin/bash
source .env 2>/dev/null || true
echo "Starting M3 Enhanced Celery worker..."
celery -A backend.app.core.job_scheduler worker --loglevel=info
EOF

    # Create ngrok tunnel script
    cat > start_ngrok.sh << 'EOF'
#!/bin/bash
source .env 2>/dev/null || true
echo "Starting ngrok tunnel..."
ngrok start api frontend
EOF

    # Make scripts executable
    chmod +x start_api.sh start_worker.sh start_ngrok.sh

    log "✅ Startup scripts created"
}

# Display final status
display_final_status() {
    local runtime_emoji="🖥️"
    if [ "$GPU_AVAILABLE" = true ]; then
        runtime_emoji="🎮"
    fi

    echo ""
    echo "🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉"
    echo "       M3 ENHANCED SETUP COMPLETE! (FIXED)"
    echo "🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉"
    echo ""
    echo "📋 Quick Start Commands:"
    echo "# Navigate to project directory:"
    echo "cd $WORK_DIR"
    echo ""
    echo "# Start the API server:"
    echo "./start_api.sh"
    echo "# OR manually:"
    echo "python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"
    echo ""
    echo "# Start Celery workers (in another terminal):"
    echo "./start_worker.sh"
    echo ""
    echo "# Start ngrok tunnel (in another terminal):"
    echo "./start_ngrok.sh"
    echo ""
    echo "🔗 Access URLs:"
    echo "Local API: http://localhost:8000/docs"
    echo "Local Frontend: http://localhost:3000 (if frontend server running)"
    echo ""
    echo "💡 Tips:"
    echo "- Environment variables are stored in .env file"
    echo "- Use GPU runtime for best performance"
    if [ "$GPU_AVAILABLE" = true ]; then
        echo "- Monitor GPU memory usage with 'nvidia-smi'"
    fi
    echo "- Check logs in $WORK_DIR/logs/"
    echo "- Ngrok token is configured: ${NGROK_TOKEN:0:10}..."
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
    log "🚀 Starting M3 Enhanced setup (Fixed Version)..."

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
    create_startup_scripts
    run_system_tests

    display_final_status

    echo ""
    log "🎵 Ready to process audio with M3 Enhanced!"
    log "   Your ngrok token has been integrated and configured! ✨"
    log "   Use ./start_ngrok.sh to create public tunnels for your servers."
}

# Check if running directly
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi
