#!/bin/bash

#=======================================================
#         M3 Enhanced - COMPLETE REBUILD Setup Script
#              Production-Ready Deployment v5.0
#=======================================================

set -euo pipefail

# Global Configuration
readonly SCRIPT_VERSION="5.0.0"
readonly WORK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly START_TIME=$(date +%s)
readonly TIMESTAMP=$(date +'%Y%m%d_%H%M%S')

# System Requirements
readonly MIN_DISK_GB=25
readonly MIN_RAM_GB=8
readonly PYTHON_MIN_VERSION="3.8"
readonly PYTHON_MAX_VERSION="3.12"

# Directories
readonly LOG_DIR="$WORK_DIR/logs"
readonly MODELS_DIR="$WORK_DIR/models"
readonly TEMP_DIR="$WORK_DIR/temp"
readonly UPLOADS_DIR="$WORK_DIR/uploads"
readonly RESULTS_DIR="$WORK_DIR/results"
readonly CONFIG_DIR="$WORK_DIR/config"

# Log files
readonly RESULT_FILE="$WORK_DIR/result.txt"
readonly SETUP_LOG="$LOG_DIR/setup_${TIMESTAMP}.log"
readonly ERROR_LOG="$LOG_DIR/setup_errors_${TIMESTAMP}.log"

# Color codes for terminal output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly BOLD='\033[1m'
readonly NC='\033[0m'

# Initialize directories and logging
mkdir -p "$LOG_DIR" "$MODELS_DIR" "$TEMP_DIR" "$UPLOADS_DIR" "$RESULTS_DIR" "$CONFIG_DIR"

# Direct terminal output to result file while preserving console display
exec > >(tee -a "$RESULT_FILE")
exec 2>&1

#=======================================================
#                    UTILITY FUNCTIONS
#=======================================================

print_header() {
    echo ""
    echo "======================================================="
    echo "         M3 Enhanced - COMPLETE REBUILD Setup Script"
    echo "              Production-Ready Deployment v5.0"
    echo "======================================================="
    echo ""
}

log_step() {
    local step="$1"
    local message="$2"
    echo -e "${CYAN}[STEP $step] $message${NC}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [STEP $step] $message" >> "$SETUP_LOG"
}

log_info() {
    local message="$1"
    echo -e "${GREEN}[INFO] $message${NC}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $message" >> "$SETUP_LOG"
}

log_warn() {
    local message="$1"
    echo -e "${YELLOW}[WARNING] $message${NC}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WARNING] $message" >> "$SETUP_LOG"
}

log_error() {
    local message="$1"
    echo -e "${RED}[ERROR] $message${NC}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $message" >> "$ERROR_LOG"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $message" >> "$SETUP_LOG"
}

fatal_error() {
    local message="$1"
    log_error "$message"
    echo -e "${RED}[FATAL] Setup failed: $message${NC}"
    echo -e "${RED}Check logs: $SETUP_LOG and $ERROR_LOG${NC}"
    exit 1
}

run_command() {
    local description="$1"
    shift
    echo -e "${BLUE}Running: $description${NC}"

    if ! "$@"; then
        fatal_error "Failed to execute: $description"
    fi
}

install_package() {
    local package="$1"
    echo -e "${BLUE}Installing: $package${NC}"

    if ! DEBIAN_FRONTEND=noninteractive apt-get install -y "$package"; then
        log_warn "Failed to install: $package"
        return 1
    fi

    log_info "Successfully installed: $package"
    return 0
}

pip_install() {
    local package="$1"
    local description="${2:-$package}"
    echo -e "${BLUE}Running: Installing $description${NC}"

    if ! python3 -m pip install --no-cache-dir "$package"; then
        log_error "Failed to install Python package: $package"
        return 1
    fi

    return 0
}

check_service() {
    local service="$1"
    local max_attempts="${2:-10}"
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if systemctl is-active --quiet "$service"; then
            log_info "$service is running"
            return 0
        fi

        attempt=$((attempt + 1))
        sleep 2
    done

    return 1
}

#=======================================================
#               SYSTEM VERIFICATION
#=======================================================

verify_system() {
    log_step 1 "Verifying System Requirements"

    # Check if running as root
    if [ "$EUID" -eq 0 ]; then
        log_warn "Running as root - this may cause permission issues"
    fi

    # OS Detection
    if [ ! -f /etc/os-release ]; then
        fatal_error "Cannot determine operating system"
    fi

    source /etc/os-release
    log_info "Operating System: $PRETTY_NAME"

    # Supported OS check
    case "$ID" in
        ubuntu|debian)
            log_info "Supported OS detected"
            ;;
        *)
            fatal_error "Unsupported operating system: $ID"
            ;;
    esac

    # Check disk space
    local available_gb=$(df "$WORK_DIR" | awk 'NR==2 {print int($4/1024/1024)}')
    log_info "Disk space: ${available_gb}GB available (${MIN_DISK_GB}GB required)"

    if [ "$available_gb" -lt "$MIN_DISK_GB" ]; then
        fatal_error "Insufficient disk space: ${available_gb}GB available, ${MIN_DISK_GB}GB required"
    fi

    # Check RAM
    local ram_gb=$(free -g | awk 'NR==2{print $2}')
    log_info "RAM: ${ram_gb}GB available"

    if [ "$ram_gb" -lt "$MIN_RAM_GB" ]; then
        log_warn "Low RAM detected: ${ram_gb}GB available, ${MIN_RAM_GB}GB recommended"
    fi

    # Check Python version
    if ! command -v python3 >/dev/null 2>&1; then
        fatal_error "Python 3 not found"
    fi

    local python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")
    log_info "Python version: $python_version (supported)"

    # Verify Python version compatibility
    python3 -c "
import sys
version = sys.version_info
if version.major != 3:
    sys.exit(1)
if version.minor < 8 or version.minor > 12:
    sys.exit(1)
" || fatal_error "Python version $python_version not supported (3.8-3.12 required)"
}

#=======================================================
#               SYSTEM DEPENDENCIES
#=======================================================

install_system_dependencies() {
    log_step 2 "Installing System Dependencies"

    # Update package lists
    run_command "Updating package lists" apt-get update

    # Fix any broken packages
    log_info "Fixing any broken packages..."
    DEBIAN_FRONTEND=noninteractive apt-get -f install -y || true

    # Essential system packages
    log_info "Installing essential system packages..."
    local essential_packages=(
        "build-essential"
        "software-properties-common"
        "apt-transport-https"
        "ca-certificates"
        "curl"
        "wget"
        "git"
        "unzip"
        "pkg-config"
    )

    for package in "${essential_packages[@]}"; do
        install_package "$package" || fatal_error "Failed to install essential package: $package"
    done

    # Audio processing libraries
    log_info "Installing audio processing libraries..."
    local audio_packages=(
        "ffmpeg"
        "libsndfile1"
        "libsndfile1-dev"
    )

    for package in "${audio_packages[@]}"; do
        install_package "$package" || log_warn "Optional audio package failed: $package"
    done

    # Optional audio libraries with fallbacks
    log_info "Installing optional audio libraries..."

    # ALSA development libraries
    echo -e "${BLUE}Installing: ALSA development libraries${NC}"
    install_package "libasound2-dev" || log_warn "ALSA dev libraries not available"

    # PortAudio libraries with fallback
    echo -e "${BLUE}Installing: PortAudio libraries${NC}"
    if ! install_package "libportaudio19-dev"; then
        log_warn "Failed to install: PortAudio libraries"
        log_warn "Trying alternative package for: PortAudio libraries"
        install_package "portaudio19-dev" || log_warn "PortAudio alternative also failed"
    fi

    # FFTW development libraries
    echo -e "${BLUE}Installing: FFTW development libraries${NC}"
    install_package "libfftw3-dev" || log_warn "FFTW dev libraries not available"

    # Sample rate conversion
    echo -e "${BLUE}Installing: Sample rate conversion${NC}"
    install_package "libsamplerate0-dev" || log_warn "Sample rate conversion not available"

    # JACK development (with potential conflicts handling)
    echo -e "${BLUE}Installing: JACK development${NC}"
    install_package "libjack-jackd2-dev" || log_warn "JACK dev not available"

    # Additional codec support
    local codec_packages=(
        "libmp3lame-dev"
        "libopus-dev"
        "libvorbis-dev"
        "libflac-dev"
    )

    for package in "${codec_packages[@]}"; do
        install_package "$package" || log_warn "Optional codec package failed: $package"
    done

    # Development libraries
    log_info "Installing development libraries..."
    local dev_packages=(
        "python3-dev"
        "python3-pip"
        "python3-venv"
        "python3-setuptools"
        "python3-wheel"
        "libssl-dev"
        "libffi-dev"
        "libbz2-dev"
        "liblzma-dev"
        "libreadline-dev"
        "libsqlite3-dev"
        "libxml2-dev"
        "libxslt1-dev"
        "zlib1g-dev"
    )

    for package in "${dev_packages[@]}"; do
        install_package "$package" || log_warn "Development package failed: $package"
    done

    # Redis server
    log_info "Installing Redis server..."
    echo -e "${BLUE}Installing: Redis server${NC}"
    install_package "redis-server" || fatal_error "Failed to install Redis server"

    log_info "System dependencies installed successfully"
}

#=======================================================
#               PYTHON ENVIRONMENT SETUP
#=======================================================

setup_python_environment() {
    log_step 3 "Setting Up Python Environment"

    # Upgrade pip, setuptools, wheel
    log_info "Upgrading pip, setuptools, wheel..."

    echo -e "${BLUE}Running: Upgrading pip${NC}"
    python3 -m pip install --upgrade pip || fatal_error "Failed to upgrade pip"

    echo -e "${BLUE}Running: Upgrading setuptools${NC}"
    python3 -m pip install --upgrade setuptools || fatal_error "Failed to upgrade setuptools"

    echo -e "${BLUE}Running: Upgrading wheel${NC}"
    python3 -m pip install --upgrade wheel || fatal_error "Failed to upgrade wheel"

    # Install build dependencies
    log_info "Installing build dependencies..."
    local build_deps=(
        "build"
        "cmake"
        "ninja"
        "pybind11[global]"
        "cython"
    )

    for dep in "${build_deps[@]}"; do
        pip_install "$dep" || log_warn "Build dependency failed: $dep"
    done

    log_info "Python environment setup complete"
}

#=======================================================
#               DEPENDENCY CONFLICT RESOLUTION
#=======================================================

resolve_dependency_conflicts() {
    log_step 4 "Resolving Dependency Conflicts"

    log_info "Removing conflicting packages..."

    # List of potentially conflicting packages to remove
    local conflict_packages=(
        "intel-openmp"
        "mkl"
        "numpy"
        "scipy"
        "scikit-learn"
        "opencv-python"
        "opencv-contrib-python"
        "opencv-python-headless"
        "tensorflow"
        "torch"
        "torchvision"
        "torchaudio"
        "librosa"
        "soundfile"
        "music21"
    )

    for package in "${conflict_packages[@]}"; do
        log_info "Removing conflicting package: $package"
        python3 -m pip uninstall -y "$package" 2>/dev/null || true
    done

    # Clean pip cache
    log_info "Cleaning pip cache..."
    python3 -m pip cache purge || true

    log_info "Dependency conflicts resolved"
}

#=======================================================
#               CORE ML FRAMEWORKS
#=======================================================

install_core_ml_frameworks() {
    log_step 5 "Installing Core ML Frameworks"

    # Install NumPy with compatible version
    log_info "Installing NumPy (compatible version)..."
    echo -e "${BLUE}Running: Installing NumPy${NC}"
    pip_install "numpy<2.0.0,>=1.21.0" "NumPy" || fatal_error "Failed to install NumPy"

    # Install SciPy
    log_info "Installing SciPy..."
    echo -e "${BLUE}Running: Installing SciPy${NC}"
    pip_install "scipy>=1.7.0" "SciPy" || fatal_error "Failed to install SciPy"

    # Install scikit-learn
    log_info "Installing scikit-learn..."
    echo -e "${BLUE}Running: Installing scikit-learn${NC}"
    pip_install "scikit-learn>=1.0.0" "scikit-learn" || fatal_error "Failed to install scikit-learn"

    # Install PyTorch (CPU version to avoid CUDA conflicts)
    log_info "Installing PyTorch (CPU version)..."
    echo -e "${BLUE}Running: Installing PyTorch${NC}"
    pip_install "--index-url https://download.pytorch.org/whl/cpu torch torchvision torchaudio" "PyTorch" || fatal_error "Failed to install PyTorch"

    # Install TensorFlow
    log_info "Installing TensorFlow..."
    echo -e "${BLUE}Running: Installing TensorFlow${NC}"
    pip_install "tensorflow>=2.13.0" "TensorFlow" || fatal_error "Failed to install TensorFlow"

    log_info "Core ML frameworks installed successfully"
}

#=======================================================
#               AUDIO PROCESSING LIBRARIES
#=======================================================

install_audio_processing() {
    log_step 6 "Installing Audio Processing Libraries"

    # Install soundfile first
    log_info "Installing soundfile..."
    echo -e "${BLUE}Running: Installing soundfile${NC}"
    pip_install "soundfile>=0.12.1" "soundfile" || fatal_error "Failed to install soundfile"

    # Install audioread
    log_info "Installing audioread..."
    echo -e "${BLUE}Running: Installing audioread${NC}"
    pip_install "audioread>=3.0.0" "audioread" || fatal_error "Failed to install audioread"

    # Install librosa
    log_info "Installing librosa..."
    echo -e "${BLUE}Running: Installing librosa${NC}"
    pip_install "librosa>=0.10.0" "librosa" || fatal_error "Failed to install librosa"

    # Install pydub
    log_info "Installing pydub..."
    echo -e "${BLUE}Running: Installing pydub${NC}"
    pip_install "pydub>=0.25.1" "pydub" || fatal_error "Failed to install pydub"

    # Install resampy
    log_info "Installing resampy..."
    echo -e "${BLUE}Running: Installing resampy${NC}"
    pip_install "resampy>=0.4.0" "resampy" || fatal_error "Failed to install resampy"

    # Install audio evaluation libraries
    log_info "Installing audio evaluation libraries..."

    echo -e "${BLUE}Running: Installing pesq${NC}"
    pip_install "pesq" || log_warn "PESQ installation failed - optional"

    echo -e "${BLUE}Running: Installing pystoi${NC}"
    pip_install "pystoi" || log_warn "PySTOI installation failed - optional"

    log_info "Audio processing libraries installed successfully"
}

#=======================================================
#               MUSIC PROCESSING LIBRARIES
#=======================================================

install_music_processing() {
    log_step 7 "Installing Music Processing Libraries"

    # Install pretty-midi
    log_info "Installing pretty-midi..."
    echo -e "${BLUE}Running: Installing pretty-midi${NC}"
    pip_install "pretty-midi>=0.2.9" "pretty-midi" || fatal_error "Failed to install pretty-midi"

    # Install music21 (latest version)
    log_info "Installing music21 (latest version)..."
    echo -e "${BLUE}Running: Installing music21${NC}"
    pip_install "music21>=9.1.0" "music21" || fatal_error "Failed to install music21"

    # Install mido
    log_info "Installing mido..."
    echo -e "${BLUE}Running: Installing mido${NC}"
    pip_install "mido>=1.3.0" "mido" || fatal_error "Failed to install mido"

    # Install demucs
    log_info "Installing demucs..."
    echo -e "${BLUE}Running: Installing demucs${NC}"
    pip_install "demucs" || fatal_error "Failed to install demucs"

    # Install Basic Pitch with compatibility handling
    log_info "Installing Basic Pitch (with compatibility handling)..."

    # Install mir_eval first as a prerequisite
    echo -e "${BLUE}Running: Installing mir_eval${NC}"
    pip_install "mir_eval>=0.6" || fatal_error "Failed to install mir_eval"

    # Handle resampy version conflict for Basic Pitch
    python3 -m pip install "resampy<0.4.3,>=0.2.2" --force-reinstall || log_warn "Resampy version adjustment failed"

    # Try to install Basic Pitch normally first
    echo -e "${BLUE}Running: Installing Basic Pitch${NC}"
    if ! pip_install "basic-pitch"; then
        log_warn "Basic Pitch installation failed - will try alternative approach"

        # Fallback: install with --no-deps and handle dependencies manually
        python3 -m pip install basic-pitch --no-deps || fatal_error "Basic Pitch installation completely failed"
        log_info "Basic Pitch installed with --no-deps"
    fi

    log_info "Music processing libraries installation complete"
}

#=======================================================
#               WEB FRAMEWORKS
#=======================================================

install_web_frameworks() {
    log_step 8 "Installing Web Frameworks"

    # Install FastAPI
    log_info "Installing FastAPI..."
    echo -e "${BLUE}Running: Installing FastAPI${NC}"
    pip_install "fastapi>=0.104.0" "FastAPI" || fatal_error "Failed to install FastAPI"

    # Install Uvicorn with standard extras
    log_info "Installing Uvicorn with standard extras..."
    echo -e "${BLUE}Running: Installing Uvicorn${NC}"
    pip_install "uvicorn[standard]>=0.24.0" "Uvicorn" || fatal_error "Failed to install Uvicorn"

    # Install additional web dependencies
    log_info "Installing additional web dependencies..."

    echo -e "${BLUE}Running: Installing python-multipart${NC}"
    pip_install "python-multipart>=0.0.6" || fatal_error "Failed to install python-multipart"

    echo -e "${BLUE}Running: Installing Jinja2${NC}"
    pip_install "jinja2>=3.1.0" || fatal_error "Failed to install Jinja2"

    echo -e "${BLUE}Running: Installing aiofiles${NC}"
    pip_install "aiofiles>=23.1.0" || fatal_error "Failed to install aiofiles"

    echo -e "${BLUE}Running: Installing python-magic${NC}"
    pip_install "python-magic>=0.4.27" || fatal_error "Failed to install python-magic"

    # Install Pydantic
    log_info "Installing Pydantic..."
    echo -e "${BLUE}Running: Installing pydantic${NC}"
    pip_install "pydantic>=2.4.0" || fatal_error "Failed to install pydantic"

    echo -e "${BLUE}Running: Installing pydantic-settings${NC}"
    pip_install "pydantic-settings>=2.0.0" || fatal_error "Failed to install pydantic-settings"

    log_info "Web frameworks installed successfully"
}

#=======================================================
#               TASK QUEUE AND REDIS SETUP
#=======================================================

setup_task_queue() {
    log_step 9 "Setting Up Task Queue and Redis"

    # Install Celery with Redis
    log_info "Installing Celery with Redis..."
    echo -e "${BLUE}Running: Installing Celery${NC}"
    pip_install "celery[redis]>=5.3.0" "Celery" || fatal_error "Failed to install Celery"

    # Install Redis Python client
    log_info "Installing Redis Python client..."
    echo -e "${BLUE}Running: Installing redis-py${NC}"
    pip_install "redis>=5.0.0" || fatal_error "Failed to install redis-py"

    # Configure Redis server
    log_info "Configuring Redis server..."

    # Create Redis configuration
    cat > "$CONFIG_DIR/redis.conf" << 'EOF'
# Redis configuration for M3 Enhanced
bind 0.0.0.0
port 6379
protected-mode no
daemonize no
supervised no
pidfile /var/run/redis_6379.pid
loglevel notice
logfile ""
databases 16
save 900 1
save 300 10
save 60 10000
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
dir ./
maxmemory 256mb
maxmemory-policy allkeys-lru
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec
no-appendfsync-on-rewrite no
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb
slowlog-log-slower-than 10000
slowlog-max-len 128
client-output-buffer-limit normal 0 0 0
client-output-buffer-limit replica 256mb 64mb 60
client-output-buffer-limit pubsub 32mb 8mb 60
tcp-keepalive 300
EOF

    # Start Redis service
    log_info "Starting Redis service..."

    # Stop any existing Redis instances
    systemctl stop redis-server 2>/dev/null || true
    killall redis-server 2>/dev/null || true

    # Start Redis with our configuration
    systemctl start redis-server || {
        log_warn "Systemctl start failed, trying manual start..."
        redis-server "$CONFIG_DIR/redis.conf" &
        sleep 3
    }

    # Test Redis connection
    local redis_test_result=0
    for i in {1..10}; do
        if redis-cli ping >/dev/null 2>&1; then
            redis_test_result=1
            break
        fi
        sleep 1
    done

    if [ "$redis_test_result" -eq 1 ]; then
        log_info "Redis started successfully"
        log_info "Redis connection test successful"
    else
        fatal_error "Redis failed to start or accept connections"
    fi

    log_info "Task queue setup complete"
}

#=======================================================
#               ADDITIONAL DEPENDENCIES
#=======================================================

install_additional_dependencies() {
    log_step 10 "Installing Additional Dependencies"

    local additional_deps=(
        "requests>=2.31.0"
        "python-dotenv>=1.0.0"
        "click>=8.1.0"
        "tqdm>=4.65.0"
        "psutil>=5.9.0"
        "matplotlib>=3.7.0"
        "pillow>=10.0.0"
    )

    for dep in "${additional_deps[@]}"; do
        log_info "Installing ${dep%%>=*}..."
        pip_install "$dep" || fatal_error "Failed to install $dep"
    done

    log_info "Additional dependencies installation complete"
}

#=======================================================
#               AI MODEL DOWNLOADS
#=======================================================

download_models() {
    log_step 11 "Downloading AI Models"

    # Download Demucs model
    log_info "Downloading Demucs model..."
    python3 -c "
import torch
import torchaudio
from demucs import pretrained

try:
    model = pretrained.get_model('htdemucs')
    print('Demucs model downloaded successfully')
except Exception as e:
    print(f'Demucs model download failed: {e}')
    raise
"

    # Test Basic Pitch availability
    log_info "Testing Basic Pitch availability..."
    python3 -c "
try:
    import basic_pitch
    print('Basic Pitch available')
except ImportError as e:
    print(f'Basic Pitch not available: {e}')
    raise
"

    log_info "Basic Pitch is available"

    log_info "Model download complete"
}

#=======================================================
#               ENVIRONMENT CONFIGURATION
#=======================================================

configure_environment() {
    log_step 12 "Configuring Environment"

    log_info "Creating environment configuration..."

    # Detect system capabilities
    local gpu_available="false"
    local device="cpu"
    local workers=2
    local batch_size=2

    # Check for GPU support
    if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then
        gpu_available="true"
        device="cuda"
        workers=4
        batch_size=8
        log_info "GPU detected - enabling CUDA acceleration"
    else
        log_info "No GPU detected - using CPU mode"
    fi

    # Create .env file
    cat > "$WORK_DIR/.env" << EOF
# M3 Enhanced Configuration
REDIS_URL=redis://localhost:6379
MODELS_DIR=$MODELS_DIR
TEMP_DIR=$TEMP_DIR
UPLOADS_DIR=$UPLOADS_DIR
RESULTS_DIR=$RESULTS_DIR
MAX_WORKERS=$workers
GPU_ENABLED=$gpu_available
DEVICE=$device
BATCH_SIZE=$batch_size
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
DEFAULT_SEPARATOR=demucs
DEFAULT_TRANSCRIBER=basic_pitch
ENABLE_CLASSIFICATION=true
LOG_LEVEL=INFO
EOF

    log_info "Environment configuration created"
}

#=======================================================
#               SERVICE SCRIPTS
#=======================================================

create_service_scripts() {
    log_step 13 "Creating Service Scripts"

    log_info "Creating start script..."
    cat > "$WORK_DIR/start.sh" << 'EOF'
#!/bin/bash
set -e

WORK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$WORK_DIR"

echo "Starting M3 Enhanced services..."

# Load environment
if [ -f ".env" ]; then
    source .env
fi

# Start Redis if not running
if ! redis-cli ping >/dev/null 2>&1; then
    echo "Starting Redis server..."
    redis-server config/redis.conf &
    sleep 3
fi

# Start Celery worker in background
echo "Starting Celery worker..."
celery -A backend.celery_app worker --loglevel=info --pidfile=/tmp/celery.pid --detach

# Start API server
echo "Starting API server..."
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 &
API_PID=$!
echo $API_PID > /tmp/api.pid

echo "Services started successfully!"
echo "API server: http://localhost:8000"
echo "Health check: curl http://localhost:8000/health"
echo ""
echo "To stop services, run: ./stop.sh"
EOF

    chmod +x "$WORK_DIR/start.sh"

    log_info "Creating stop script..."
    cat > "$WORK_DIR/stop.sh" << 'EOF'
#!/bin/bash
set -e

echo "Stopping M3 Enhanced services..."

# Stop API server
if [ -f /tmp/api.pid ]; then
    API_PID=$(cat /tmp/api.pid)
    if kill -0 "$API_PID" 2>/dev/null; then
        echo "Stopping API server (PID: $API_PID)..."
        kill "$API_PID"
        rm -f /tmp/api.pid
    fi
fi

# Stop Celery worker
if [ -f /tmp/celery.pid ]; then
    CELERY_PID=$(cat /tmp/celery.pid)
    if kill -0 "$CELERY_PID" 2>/dev/null; then
        echo "Stopping Celery worker (PID: $CELERY_PID)..."
        kill "$CELERY_PID"
        rm -f /tmp/celery.pid
    fi
fi

# Stop any remaining processes
pkill -f "uvicorn.*main:app" || true
pkill -f "celery.*worker" || true

echo "All services stopped"
EOF

    chmod +x "$WORK_DIR/stop.sh"

    log_info "Creating status script..."
    cat > "$WORK_DIR/status.sh" << 'EOF'
#!/bin/bash

echo "M3 Enhanced Service Status"
echo "=========================="

# Check Redis
if redis-cli ping >/dev/null 2>&1; then
    echo "✓ Redis: Running"
else
    echo "✗ Redis: Not running"
fi

# Check API server
if [ -f /tmp/api.pid ]; then
    API_PID=$(cat /tmp/api.pid)
    if kill -0 "$API_PID" 2>/dev/null; then
        echo "✓ API Server: Running (PID: $API_PID)"
    else
        echo "✗ API Server: Process not found"
        rm -f /tmp/api.pid
    fi
else
    echo "✗ API Server: Not running"
fi

# Check Celery worker
if [ -f /tmp/celery.pid ]; then
    CELERY_PID=$(cat /tmp/celery.pid)
    if kill -0 "$CELERY_PID" 2>/dev/null; then
        echo "✓ Celery Worker: Running (PID: $CELERY_PID)"
    else
        echo "✗ Celery Worker: Process not found"
        rm -f /tmp/celery.pid
    fi
else
    echo "✗ Celery Worker: Not running"
fi

# Check API health
echo ""
echo "Testing API health..."
if curl -s http://localhost:8000/health >/dev/null 2>&1; then
    echo "✓ API Health: OK"
    curl -s http://localhost:8000/health | python3 -m json.tool
else
    echo "✗ API Health: Failed to connect"
fi
EOF

    chmod +x "$WORK_DIR/status.sh"

    log_info "Service scripts created successfully"
}

#=======================================================
#               INSTALLATION VERIFICATION
#=======================================================

verify_installation() {
    log_step 14 "Verifying Installation"

    log_info "Testing Python imports..."

    # Test core imports
    python3 -c "
import sys
print(f'Python: {sys.version}')

try:
    import numpy as np
    print(f'NumPy: {np.__version__}')
except ImportError as e:
    print(f'NumPy: FAILED - {e}')
    sys.exit(1)

try:
    import torch
    print(f'PyTorch: {torch.__version__}')
except ImportError as e:
    print(f'PyTorch: FAILED - {e}')
    sys.exit(1)

try:
    import tensorflow as tf
    print(f'TensorFlow: {tf.__version__}')
except ImportError as e:
    print(f'TensorFlow: FAILED - {e}')
    sys.exit(1)

print('Core imports: PASSED')
"

    # Test audio processing
    python3 -c "
try:
    import librosa
    import soundfile as sf
    import pydub
    print('Audio processing: PASSED')
except ImportError as e:
    print(f'Audio processing: FAILED - {e}')
    raise
"

    # Test Basic Pitch availability
    log_info "Testing Basic Pitch availability..."
    python3 -c "
try:
    import basic_pitch
    print('Basic Pitch: AVAILABLE')
except ImportError as e:
    print(f'Basic Pitch: NOT AVAILABLE - {e}')
    raise
"

    log_info "Installation verification complete"
}

#=======================================================
#               CLEANUP
#=======================================================

cleanup_installation() {
    log_step 15 "Cleaning Up Installation"

    log_info "Cleaning pip cache..."
    python3 -m pip cache purge || true

    log_info "Cleaning apt cache..."
    apt-get autoremove -y || true
    apt-get clean || true

    log_info "Cleanup complete"
}

#=======================================================
#               MAIN EXECUTION
#=======================================================

main() {
    print_header

    log_info "Starting M3 Enhanced setup process..."
    log_info "Working directory: $WORK_DIR"
    log_info "Timestamp: $TIMESTAMP"

    # Execute all setup steps
    verify_system
    install_system_dependencies
    setup_python_environment
    resolve_dependency_conflicts
    install_core_ml_frameworks
    install_audio_processing
    install_music_processing
    install_web_frameworks
    setup_task_queue
    install_additional_dependencies
    download_models
    configure_environment
    create_service_scripts
    verify_installation
    cleanup_installation

    # Calculate setup time
    local end_time=$(date +%s)
    local duration=$((end_time - START_TIME))
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))

    # Detect runtime configuration
    local gpu_text="CPU"
    local device="cpu"
    local workers=2
    local batch_size=2

    if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then
        gpu_text="GPU"
        device="cuda"
        workers=4
        batch_size=8
    fi

    # Display completion message
    echo ""
    echo "=============================================="
    echo "    M3 ENHANCED SETUP COMPLETE"
    echo "=============================================="
    echo ""
    echo "INSTALLATION SUMMARY:"
    echo "  Setup Time: ${minutes}m ${seconds}s"
    echo "  Runtime: $gpu_text"
    echo "  Device: $device"
    echo "  Workers: $workers"
    echo "  Batch Size: $batch_size"
    echo ""
    echo "QUICK START:"
    echo "  ./start.sh     # Start services"
    echo "  ./status.sh    # Check status"
    echo "  ./stop.sh      # Stop services"
    echo ""
    echo "ACCESS POINTS:"
    echo "  API: http://localhost:8000"
    echo "  Health: curl http://localhost:8000/health"
    echo ""
    echo "IMPORTANT FILES:"
    echo "  Configuration: .env"
    echo "  Setup Log: $SETUP_LOG"
    echo "  Error Log: $ERROR_LOG"
    echo "  Results: $RESULT_FILE"
    echo ""
    echo "FEATURES AVAILABLE:"
    echo "  Audio Separation (Demucs)"
    echo "  Music Transcription (Basic Pitch)"
    echo "  MIDI Processing"
    echo "  Web API Interface"
    echo ""
    echo "NEXT STEPS:"
    echo "  1. Run: ./start.sh"
    echo "  2. Test: curl http://localhost:8000/health"
    echo "  3. Check logs: tail -f logs/api.log"
    echo ""
    echo "=============================================="
    echo "   M3 Enhanced is ready!"
    echo "=============================================="

    echo ""
    echo "=== SETUP COMPLETE ==="
    echo "Result file: $RESULT_FILE"
    echo "Setup log: $SETUP_LOG"
    echo "Error log: $ERROR_LOG"
    echo "======================="
}

# Execute main function
main "$@"
