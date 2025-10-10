#!/bin/bash

#=======================================================
#         M3 Enhanced - FIXED Setup Script v4.1
#              Production-Ready Deployment
#=======================================================

# ITERATION #4.1: Package installation fixes for Ubuntu compatibility
# Fixed package names and dependency conflicts

set -euo pipefail

# Global Configuration
readonly SCRIPT_VERSION="4.1.0"
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
    echo "         M3 Enhanced - FIXED Setup Script v4.1"
    echo "              Production-Ready Deployment"
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
    echo -e "${RED}[FATAL] Check logs: $SETUP_LOG and $ERROR_LOG${NC}"
    exit 1
}

check_command() {
    local cmd="$1"
    if ! command -v "$cmd" >/dev/null 2>&1; then
        return 1
    fi
    return 0
}

run_with_check() {
    local description="$1"
    shift
    echo -e "${BLUE}Running: $description${NC}"
    if ! "$@"; then
        fatal_error "Failed: $description"
    fi
}

# Enhanced package installation with error handling
install_package_safe() {
    local package="$1"
    local description="${2:-$package}"

    echo -e "${BLUE}Installing: $description${NC}"

    # Check if package is available first
    if ! apt-cache show "$package" >/dev/null 2>&1; then
        log_warn "Package not available: $package"
        return 1
    fi

    if apt-get install -y "$package" 2>/dev/null; then
        log_info "Successfully installed: $description"
        return 0
    else
        log_warn "Failed to install: $description"
        return 1
    fi
}

# Install packages with fallback options
install_with_fallback() {
    local description="$1"
    shift
    local packages=("$@")

    echo -e "${BLUE}Installing: $description${NC}"

    for package in "${packages[@]}"; do
        if install_package_safe "$package" "$description"; then
            return 0
        fi
        log_warn "Trying alternative package for: $description"
    done

    log_error "All alternatives failed for: $description"
    return 1
}

#=======================================================
#                  SYSTEM VERIFICATION
#=======================================================

verify_system_requirements() {
    log_step "1" "Verifying System Requirements"

    # Check if running as root
    if [[ $EUID -eq 0 ]]; then
        log_warn "Running as root - this may cause permission issues"
    fi

    # Check operating system
    if [[ ! -f /etc/os-release ]]; then
        fatal_error "Cannot determine operating system"
    fi

    local os_info=$(cat /etc/os-release)
    log_info "Operating System: $(echo "$os_info" | grep PRETTY_NAME | cut -d'"' -f2)"

    # Check available disk space
    local available_gb=$(df "$WORK_DIR" | awk 'NR==2 {print int($4/1024/1024)}')
    if [[ $available_gb -lt $MIN_DISK_GB ]]; then
        fatal_error "Insufficient disk space: ${available_gb}GB available, ${MIN_DISK_GB}GB required"
    fi
    log_info "Disk space: ${available_gb}GB available (${MIN_DISK_GB}GB required)"

    # Check available RAM
    local available_ram_gb=$(free -g | awk 'NR==2{print $2}')
    if [[ $available_ram_gb -lt $MIN_RAM_GB ]]; then
        log_warn "Low RAM: ${available_ram_gb}GB available, ${MIN_RAM_GB}GB recommended"
    else
        log_info "RAM: ${available_ram_gb}GB available"
    fi

    # Check Python version
    if ! check_command python3; then
        fatal_error "Python 3 is not installed"
    fi

    local python_version=$(python3 --version | cut -d' ' -f2)
    local python_major=$(echo "$python_version" | cut -d'.' -f1)
    local python_minor=$(echo "$python_version" | cut -d'.' -f2)

    if [[ $python_major -ne 3 ]] || [[ $python_minor -lt 8 ]] || [[ $python_minor -gt 12 ]]; then
        fatal_error "Python version $python_version not supported. Requires 3.8-3.12"
    fi
    log_info "Python version: $python_version (supported)"
}

#=======================================================
#              SYSTEM DEPENDENCIES INSTALLATION
#=======================================================

install_system_dependencies() {
    log_step "2" "Installing System Dependencies"

    # Update package lists
    run_with_check "Updating package lists" apt-get update

    # Fix broken packages first
    log_info "Fixing any broken packages..."
    apt-get -f install -y || true

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

    local failed_essential=()
    for package in "${essential_packages[@]}"; do
        if ! install_package_safe "$package"; then
            failed_essential+=("$package")
        fi
    done

    if [[ ${#failed_essential[@]} -gt 0 ]]; then
        log_warn "Some essential packages failed: ${failed_essential[*]}"
        log_info "Attempting to continue with available packages..."
    fi

    # Audio and multimedia libraries with Ubuntu-specific names
    log_info "Installing audio processing libraries..."

    # Critical audio packages - these must succeed
    local critical_audio=(
        "ffmpeg"
        "libsndfile1"
        "libsndfile1-dev"
    )

    for package in "${critical_audio[@]}"; do
        if ! install_package_safe "$package"; then
            fatal_error "Critical audio package failed: $package"
        fi
    done

    # Optional audio packages with corrected names and fallbacks
    log_info "Installing optional audio libraries..."

    # ALSA development libraries
    install_with_fallback "ALSA development libraries" "libasound2-dev" "libasound-dev"

    # PortAudio libraries - FIXED PACKAGE NAME
    install_with_fallback "PortAudio libraries" "libportaudio19-dev" "portaudio19-dev" "libportaudio2"

    # FFTW development libraries
    install_with_fallback "FFTW development libraries" "libfftw3-dev" "fftw-dev" "libfftw3-3"

    # Sample rate conversion
    install_with_fallback "Sample rate conversion" "libsamplerate0-dev" "libsamplerate-dev"

    # JACK development - multiple alternatives
    install_with_fallback "JACK development" "libjack-jackd2-dev" "libjack-dev" "jackd2"

    # Codec libraries - install individually with error handling
    local codec_packages=(
        "libmp3lame-dev"
        "libopus-dev"
        "libvorbis-dev"
        "libflac-dev"
    )

    for package in "${codec_packages[@]}"; do
        if ! install_package_safe "$package"; then
            log_warn "Optional codec package failed: $package"
        fi
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

    local failed_dev=()
    for package in "${dev_packages[@]}"; do
        if ! install_package_safe "$package"; then
            failed_dev+=("$package")
        fi
    done

    if [[ ${#failed_dev[@]} -gt 0 ]]; then
        log_warn "Some development packages failed: ${failed_dev[*]}"
    fi

    # Redis server installation with enhanced error handling
    log_info "Installing Redis server..."
    if ! install_package_safe "redis-server" "Redis server"; then
        log_warn "Redis server package installation failed - will try alternative methods later"

        # Try installing Redis from official repository
        log_info "Attempting Redis installation from official repository..."

        if curl -fsSL https://packages.redis.io/gpg | apt-key add - 2>/dev/null; then
            echo "deb https://packages.redis.io/deb $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/redis.list >/dev/null 2>&1 || true

            if apt-get update >/dev/null 2>&1 && install_package_safe "redis" "Redis (official repository)"; then
                log_info "Redis installed from official repository"
            else
                log_warn "Official Redis repository installation also failed"
            fi
        else
            log_warn "Could not add Redis official repository"
        fi
    fi

    # Verify critical commands are available
    local required_commands=("python3" "pip3" "ffmpeg")
    local missing_commands=()

    for cmd in "${required_commands[@]}"; do
        if ! check_command "$cmd"; then
            missing_commands+=("$cmd")
        fi
    done

    if [[ ${#missing_commands[@]} -gt 0 ]]; then
        fatal_error "Required commands not found after installation: ${missing_commands[*]}"
    fi

    log_info "System dependencies installed successfully"
}

#=======================================================
#                 PYTHON ENVIRONMENT SETUP
#=======================================================

setup_python_environment() {
    log_step "3" "Setting Up Python Environment"

    # Upgrade pip, setuptools, wheel to latest versions
    log_info "Upgrading pip, setuptools, wheel..."
    run_with_check "Upgrading pip" python3 -m pip install --upgrade pip
    run_with_check "Upgrading setuptools" python3 -m pip install --upgrade setuptools
    run_with_check "Upgrading wheel" python3 -m pip install --upgrade wheel

    # Install build dependencies
    local build_deps=(
        "build"
        "cmake"
        "ninja"
        "pybind11[global]"
        "cython"
    )

    log_info "Installing build dependencies..."
    for dep in "${build_deps[@]}"; do
        if ! python3 -m pip install "$dep"; then
            log_warn "Failed to install build dependency: $dep"
        fi
    done

    log_info "Python environment setup complete"
}

#=======================================================
#           DEPENDENCY CONFLICT RESOLUTION
#=======================================================

resolve_dependency_conflicts() {
    log_step "4" "Resolving Dependency Conflicts"

    log_info "Removing conflicting packages..."

    # Remove problematic packages that cause conflicts
    local conflicting_packages=(
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
        "basic-pitch"
        "music21"
    )

    for package in "${conflicting_packages[@]}"; do
        if python3 -m pip show "$package" >/dev/null 2>&1; then
            log_info "Removing conflicting package: $package"
            python3 -m pip uninstall -y "$package" || true
        fi
    done

    # Clean pip cache
    log_info "Cleaning pip cache..."
    python3 -m pip cache purge || true

    log_info "Dependency conflicts resolved"
}

#=======================================================
#              CORE ML FRAMEWORKS INSTALLATION
#=======================================================

install_core_ml_frameworks() {
    log_step "5" "Installing Core ML Frameworks"

    # Install NumPy first with compatible version
    log_info "Installing NumPy (compatible version)..."
    run_with_check "Installing NumPy" python3 -m pip install "numpy>=1.21.0,<2.0.0"

    # Install SciPy
    log_info "Installing SciPy..."
    run_with_check "Installing SciPy" python3 -m pip install "scipy>=1.7.0"

    # Install scikit-learn
    log_info "Installing scikit-learn..."
    run_with_check "Installing scikit-learn" python3 -m pip install "scikit-learn>=1.0.0"

    # Install PyTorch (CPU version to avoid CUDA conflicts)
    log_info "Installing PyTorch (CPU version)..."
    run_with_check "Installing PyTorch" python3 -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

    # Install TensorFlow (latest compatible version)
    log_info "Installing TensorFlow..."
    run_with_check "Installing TensorFlow" python3 -m pip install "tensorflow>=2.13.0"

    log_info "Core ML frameworks installed successfully"
}

#=======================================================
#              AUDIO PROCESSING LIBRARIES
#=======================================================

install_audio_libraries() {
    log_step "6" "Installing Audio Processing Libraries"

    # Install soundfile first (required by many audio libraries)
    log_info "Installing soundfile..."
    run_with_check "Installing soundfile" python3 -m pip install "soundfile>=0.12.1"

    # Install audio processing libraries
    log_info "Installing audioread..."
    run_with_check "Installing audioread" python3 -m pip install "audioread>=3.0.0"

    log_info "Installing librosa..."
    run_with_check "Installing librosa" python3 -m pip install "librosa>=0.10.0"

    log_info "Installing pydub..."
    run_with_check "Installing pydub" python3 -m pip install "pydub>=0.25.1"

    log_info "Installing resampy..."
    run_with_check "Installing resampy" python3 -m pip install "resampy>=0.4.0"

    log_info "Installing audio evaluation libraries..."
    run_with_check "Installing pesq" python3 -m pip install "pesq"
    run_with_check "Installing pystoi" python3 -m pip install "pystoi"

    log_info "Audio processing libraries installed successfully"
}

#=======================================================
#              MUSIC PROCESSING LIBRARIES
#=======================================================

install_music_libraries() {
    log_step "7" "Installing Music Processing Libraries"

    # Install MIDI processing
    log_info "Installing pretty-midi..."
    run_with_check "Installing pretty-midi" python3 -m pip install "pretty-midi>=0.2.9"

    log_info "Installing music21 (latest version)..."
    run_with_check "Installing music21" python3 -m pip install "music21>=9.1.0"

    log_info "Installing mido..."
    run_with_check "Installing mido" python3 -m pip install "mido>=1.3.0"

    # Install Demucs for audio separation
    log_info "Installing demucs..."
    run_with_check "Installing demucs" python3 -m pip install "demucs"

    # Try to install Basic Pitch with compatibility fixes
    log_info "Installing Basic Pitch (with compatibility handling)..."

    # Install mir_eval first (required by basic-pitch)
    run_with_check "Installing mir_eval" python3 -m pip install "mir_eval>=0.6"

    # Install specific resampy version compatible with basic-pitch
    python3 -m pip install "resampy>=0.2.2,<0.4.3" || log_warn "Resampy version conflict - continuing with installed version"

    # Install basic-pitch with error handling
    if ! python3 -m pip install "basic-pitch"; then
        log_warn "Basic Pitch installation failed - will try alternative approach"

        # Try installing with no-deps and manual dependency resolution
        if ! python3 -m pip install --no-deps "basic-pitch"; then
            log_warn "Basic Pitch installation failed completely - transcription features may be limited"
        else
            log_info "Basic Pitch installed with --no-deps"
        fi
    else
        log_info "Basic Pitch installed successfully"
    fi

    log_info "Music processing libraries installation complete"
}

#=======================================================
#              WEB FRAMEWORK INSTALLATION
#=======================================================

install_web_frameworks() {
    log_step "8" "Installing Web Frameworks"

    # Install FastAPI and dependencies
    log_info "Installing FastAPI..."
    run_with_check "Installing FastAPI" python3 -m pip install "fastapi>=0.104.0"

    log_info "Installing Uvicorn with standard extras..."
    run_with_check "Installing Uvicorn" python3 -m pip install "uvicorn[standard]>=0.24.0"

    log_info "Installing additional web dependencies..."
    run_with_check "Installing python-multipart" python3 -m pip install "python-multipart>=0.0.6"
    run_with_check "Installing Jinja2" python3 -m pip install "jinja2>=3.1.0"
    run_with_check "Installing aiofiles" python3 -m pip install "aiofiles>=23.1.0"
    run_with_check "Installing python-magic" python3 -m pip install "python-magic>=0.4.27"

    # Install Pydantic and settings
    log_info "Installing Pydantic..."
    run_with_check "Installing pydantic" python3 -m pip install "pydantic>=2.4.0"
    run_with_check "Installing pydantic-settings" python3 -m pip install "pydantic-settings>=2.0.0"

    log_info "Web frameworks installed successfully"
}

#=======================================================
#              TASK QUEUE AND REDIS SETUP
#=======================================================

setup_task_queue() {
    log_step "9" "Setting Up Task Queue and Redis"

    # Install Celery with Redis support
    log_info "Installing Celery with Redis..."
    run_with_check "Installing Celery" python3 -m pip install "celery[redis]>=5.3.0"

    log_info "Installing Redis Python client..."
    run_with_check "Installing redis-py" python3 -m pip install "redis>=5.0.0"

    # Check if Redis is available
    if ! check_command redis-server; then
        log_warn "Redis server not found - task queue will be disabled"
    else
        # Configure Redis
        log_info "Configuring Redis server..."

        # Create Redis configuration
        cat > "$CONFIG_DIR/redis.conf" << 'EOF'
# Redis configuration for M3 Enhanced
bind 127.0.0.1
port 6379
protected-mode yes
daemonize yes
supervised no
pidfile /tmp/redis_6379.pid
loglevel notice
logfile ""
databases 16

# Memory management
maxmemory 512mb
maxmemory-policy allkeys-lru

# Persistence
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfilename "appendonly.aof"

# Performance
tcp-keepalive 300
timeout 0
EOF

        # Try to start Redis
        log_info "Starting Redis service..."

        # Stop any existing Redis
        pkill -f redis-server || true
        sleep 2

        # Start Redis with our config
        if redis-server "$CONFIG_DIR/redis.conf"; then
            log_info "Redis started successfully"
            sleep 2

            # Test Redis connection
            if redis-cli ping | grep -q "PONG"; then
                log_info "Redis connection test successful"
            else
                log_warn "Redis connection test failed - continuing anyway"
            fi
        else
            log_warn "Failed to start Redis server"
        fi
    fi

    log_info "Task queue setup complete"
}

#=======================================================
#              ADDITIONAL DEPENDENCIES
#=======================================================

install_additional_dependencies() {
    log_step "10" "Installing Additional Dependencies"

    # Install utility libraries
    local utility_packages=(
        "requests>=2.31.0"
        "python-dotenv>=1.0.0"
        "click>=8.1.0"
        "tqdm>=4.65.0"
        "psutil>=5.9.0"
        "matplotlib>=3.7.0"
        "pillow>=10.0.0"
    )

    for package in "${utility_packages[@]}"; do
        log_info "Installing $package..."
        if ! python3 -m pip install "$package"; then
            log_warn "Failed to install utility package: $package"
        fi
    done

    log_info "Additional dependencies installation complete"
}

#=======================================================
#              MODEL DOWNLOAD AND SETUP
#=======================================================

download_models() {
    log_step "11" "Downloading AI Models"

    log_info "Downloading Demucs model..."
    python3 -c "
import torch
import torchaudio
try:
    from demucs.pretrained import get_model
    model = get_model('htdemucs')
    print('Demucs model downloaded successfully')
except Exception as e:
    print(f'Demucs model download failed: {e}')
    exit(1)
"

    # Test Basic Pitch if available
    log_info "Testing Basic Pitch availability..."
    if python3 -c "import basic_pitch; print('Basic Pitch available')" 2>/dev/null; then
        log_info "Basic Pitch is available"
    else
        log_warn "Basic Pitch not available - transcription features limited"
    fi

    log_info "Model download complete"
}

#=======================================================
#              ENVIRONMENT CONFIGURATION
#=======================================================

configure_environment() {
    log_step "12" "Configuring Environment"

    # Create .env file if it doesn't exist
    if [[ ! -f "$WORK_DIR/.env" ]]; then
        log_info "Creating environment configuration..."

        cat > "$WORK_DIR/.env" << 'EOF'
# M3 Enhanced Environment Configuration

# Redis Configuration (no password for local development)
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
RELOAD=false

# Processing Configuration
MAX_WORKERS=2
GPU_ENABLED=false
BATCH_SIZE=2
TEMP_CLEANUP=true

# Model Configuration
MODELS_DIR=./models
TEMP_DIR=./temp
UPLOADS_DIR=./uploads
RESULTS_DIR=./results

# Default Processing Settings
DEFAULT_SEPARATOR=demucs
DEFAULT_TRANSCRIBER=basic_pitch
ENABLE_CLASSIFICATION=true
QUALITY_ANALYSIS=true
GENERATE_TABS=true
OUTPUT_FORMAT=all

# File Upload Settings
MAX_FILE_SIZE=100MB
ALLOWED_EXTENSIONS=mp3,wav,flac,m4a,ogg

# Logging
LOG_LEVEL=INFO
LOG_DIR=./logs
EOF
        log_info "Environment configuration created"
    else
        log_info "Using existing environment configuration"
    fi
}

#=======================================================
#              SERVICE SCRIPTS CREATION
#=======================================================

create_service_scripts() {
    log_step "13" "Creating Service Scripts"

    # Create start script
    log_info "Creating start script..."
    cat > "$WORK_DIR/start.sh" << 'EOF'
#!/bin/bash

echo "Starting M3 Enhanced services..."

# Load environment
if [[ -f .env ]]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Start Redis if available and not running
if command -v redis-server >/dev/null 2>&1; then
    if ! pgrep -x "redis-server" > /dev/null; then
        echo "Starting Redis..."
        if [[ -f config/redis.conf ]]; then
            redis-server config/redis.conf
        else
            redis-server --daemonize yes --port ${REDIS_PORT:-6379}
        fi
        sleep 2
    fi

    # Test Redis connection
    if redis-cli -p ${REDIS_PORT:-6379} ping | grep -q "PONG" 2>/dev/null; then
        echo "Redis: Connected"
    else
        echo "Redis: Connection failed (continuing without task queue)"
    fi
else
    echo "Redis: Not available (continuing without task queue)"
fi

echo "Starting API server..."

# Create basic main.py if it doesn't exist
if [[ ! -f backend/main.py ]]; then
    mkdir -p backend
    cat > backend/main.py << 'PYEOF'
from fastapi import FastAPI

app = FastAPI(title="M3 Enhanced API", version="1.0.0")

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "message": "M3 Enhanced API is running"
    }

@app.get("/")
def root():
    return {"message": "Welcome to M3 Enhanced API"}
PYEOF
fi

# Start API server
python3 -m uvicorn backend.main:app --host ${API_HOST:-0.0.0.0} --port ${API_PORT:-8000} --reload=false &
API_PID=$!

# Wait a moment for server to start
sleep 5

# Check if API server is running
if kill -0 $API_PID 2>/dev/null; then
    echo "M3 Enhanced started!"
    echo "API: http://localhost:${API_PORT:-8000}"
    echo "Health: curl http://localhost:${API_PORT:-8000}/health"
    echo "Process ID: $API_PID"
else
    echo "Failed to start API server"
    exit 1
fi
EOF

    chmod +x "$WORK_DIR/start.sh"

    # Create stop script
    log_info "Creating stop script..."
    cat > "$WORK_DIR/stop.sh" << 'EOF'
#!/bin/bash

echo "Stopping M3 Enhanced services..."

# Stop API server
pkill -f "uvicorn.*backend.main:app" || true

# Stop Celery workers
pkill -f "celery.*worker" || true

# Stop Redis (if we started it)
if pgrep -f "redis-server.*config/redis.conf" > /dev/null; then
    pkill -f "redis-server.*config/redis.conf" || true
fi

echo "M3 Enhanced stopped"
EOF

    chmod +x "$WORK_DIR/stop.sh"

    # Create status script
    log_info "Creating status script..."
    cat > "$WORK_DIR/status.sh" << 'EOF'
#!/bin/bash

echo "M3 Enhanced Service Status:"
echo "=========================="

# Load environment
if [[ -f .env ]]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check Redis
if command -v redis-server >/dev/null 2>&1; then
    if pgrep -x "redis-server" > /dev/null; then
        echo "Redis: Running"
        if redis-cli -p ${REDIS_PORT:-6379} ping | grep -q "PONG" 2>/dev/null; then
            echo "Redis Connection: OK"
        else
            echo "Redis Connection: Failed"
        fi
    else
        echo "Redis: Stopped"
    fi
else
    echo "Redis: Not Available"
fi

# Check API server
if pgrep -f "uvicorn.*backend.main:app" > /dev/null; then
    echo "API Server: Running"

    # Test API health endpoint
    if command -v curl >/dev/null 2>&1; then
        if curl -s "http://localhost:${API_PORT:-8000}/health" >/dev/null; then
            echo "API Health: OK"
        else
            echo "API Health: Failed"
        fi
    fi
else
    echo "API Server: Stopped"
fi

# Check Celery workers
if pgrep -f "celery.*worker" > /dev/null; then
    echo "Celery Workers: Running"
else
    echo "Celery Workers: Stopped"
fi

echo ""
echo "Access Points:"
echo "- API: http://localhost:${API_PORT:-8000}"
echo "- Health Check: curl http://localhost:${API_PORT:-8000}/health"
echo "- Documentation: http://localhost:${API_PORT:-8000}/docs"
EOF

    chmod +x "$WORK_DIR/status.sh"

    log_info "Service scripts created successfully"
}

#=======================================================
#              VERIFICATION AND TESTING
#=======================================================

verify_installation() {
    log_step "14" "Verifying Installation"

    log_info "Testing Python imports..."

    # Test core imports
    python3 -c "
import sys
print(f'Python: {sys.version}')

try:
    import numpy as np
    print(f'NumPy: {np.__version__}')
except ImportError as e:
    print(f'NumPy import failed: {e}')
    sys.exit(1)

try:
    import torch
    print(f'PyTorch: {torch.__version__}')
except ImportError as e:
    print(f'PyTorch import failed: {e}')
    sys.exit(1)

try:
    import tensorflow as tf
    print(f'TensorFlow: {tf.__version__}')
except ImportError as e:
    print(f'TensorFlow import failed: {e}')
    sys.exit(1)

print('Core imports: PASSED')
"

    # Test audio processing imports
    python3 -c "
try:
    import librosa
    import soundfile as sf
    import pydub
    print('Audio processing: PASSED')
except ImportError as e:
    print(f'Audio processing import failed: {e}')
    exit(1)
"

    # Test Basic Pitch separately with error handling
    log_info "Testing Basic Pitch availability..."
    if ! python3 -c "import basic_pitch; print('Basic Pitch: AVAILABLE')" 2>/dev/null; then
        log_warn "Basic Pitch verification failed: Module not properly installed"
    fi

    log_info "Installation verification complete"
}

#=======================================================
#              CLEANUP AND FINALIZATION
#=======================================================

cleanup_installation() {
    log_step "15" "Cleaning Up Installation"

    # Clean pip cache
    log_info "Cleaning pip cache..."
    python3 -m pip cache purge || true

    # Clean apt cache
    log_info "Cleaning apt cache..."
    apt-get autoremove -y || true
    apt-get autoclean || true

    # Remove temporary files
    if [[ -d "/tmp/pip-*" ]]; then
        rm -rf /tmp/pip-* || true
    fi

    # Set proper permissions
    chmod -R 755 "$WORK_DIR"/{*.sh,logs,temp,uploads,results} 2>/dev/null || true

    log_info "Cleanup complete"
}

#=======================================================
#              MAIN INSTALLATION FUNCTION
#=======================================================

main() {
    local end_time
    local duration

    print_header

    # Check if already in M3 Enhanced directory
    if [[ ! -f "$WORK_DIR/setup.sh" ]]; then
        fatal_error "Please run this script from the M3 Enhanced project directory"
    fi

    log_info "Starting M3 Enhanced setup process..."
    log_info "Working directory: $WORK_DIR"
    log_info "Timestamp: $TIMESTAMP"

    # Execute installation steps
    verify_system_requirements
    install_system_dependencies
    setup_python_environment
    resolve_dependency_conflicts
    install_core_ml_frameworks
    install_audio_libraries
    install_music_libraries
    install_web_frameworks
    setup_task_queue
    install_additional_dependencies
    download_models
    configure_environment
    create_service_scripts
    verify_installation
    cleanup_installation

    # Calculate duration
    end_time=$(date +%s)
    duration=$((end_time - START_TIME))

    # Runtime detection
    local runtime="CPU"
    local device="cpu"
    if python3 -c "import torch; print(torch.cuda.is_available())" 2>/dev/null | grep -q "True"; then
        runtime="GPU"
        device="cuda"
    fi

    # Final success message
    echo ""
    echo "=============================================="
    echo "    M3 ENHANCED SETUP COMPLETE"
    echo "=============================================="
    echo ""
    echo "INSTALLATION SUMMARY:"
    echo "  Setup Time: $((duration / 60))m $((duration % 60))s"
    echo "  Runtime: $runtime"
    echo "  Device: $device"
    echo "  Workers: 2"
    echo "  Batch Size: 2"
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

    if python3 -c "import basic_pitch" 2>/dev/null; then
        echo "  Music Transcription (Basic Pitch)"
    else
        echo "  Music Transcription (Limited - Basic Pitch unavailable)"
    fi

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

# Handle script interruption
trap 'log_error "Setup interrupted"; exit 1' INT TERM

# Run main function
main "$@"
