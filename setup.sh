#!/bin/bash

#=======================================================
#         M3 Enhanced - SONIC ACCURACY PRODUCTION Setup Script
#              Zero-Compromise Audio Fidelity v7.0
#=======================================================

set -euo pipefail

# Global Configuration
readonly SCRIPT_VERSION="7.0.0"
readonly WORK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly START_TIME=$(date +%s)
readonly TIMESTAMP=$(date +'%Y%m%d_%H%M%S')

# System Requirements - Updated for Ubuntu 22.04+ compatibility
readonly MIN_DISK_GB=50
readonly MIN_RAM_GB=16
readonly PYTHON_MIN_VERSION="3.10"
readonly PYTHON_MAX_VERSION="3.12"
readonly CUDA_MIN_VERSION="11.8"

# Exact version specifications for sonic accuracy - Latest stable versions
readonly NUMPY_VERSION="1.26.2"
readonly SCIPY_VERSION="1.11.4"
readonly LIBROSA_VERSION="0.10.1"
readonly SOUNDFILE_VERSION="0.12.1"
readonly PYTORCH_VERSION="2.1.2"
readonly TORCHVISION_VERSION="0.16.2"
readonly TORCHAUDIO_VERSION="2.1.2"
readonly TENSORFLOW_VERSION="2.15.0"
readonly BASIC_PITCH_VERSION="0.3.4"
readonly DEMUCS_VERSION="4.0.1"
readonly MIR_EVAL_VERSION="0.7"
readonly PRETTY_MIDI_VERSION="0.2.10"
readonly MUSIC21_VERSION="9.1.0"
readonly MIDO_VERSION="1.3.0"
readonly FASTAPI_VERSION="0.104.1"
readonly UVICORN_VERSION="0.24.0"
readonly REDIS_VERSION="5.0.1"
readonly CELERY_VERSION="5.3.4"

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

# Color codes
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
    echo "         M3 Enhanced - SONIC ACCURACY PRODUCTION Setup"
    echo "              Zero-Compromise Audio Fidelity v7.0"
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

log_warning() {
    local message="$1"
    echo -e "${YELLOW}[WARNING] $message${NC}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WARNING] $message" >> "$SETUP_LOG"
}

log_error() {
    local message="$1"
    echo -e "${RED}[ERROR] $message${NC}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $message" >> "$ERROR_LOG"
}

log_fatal() {
    local message="$1"
    echo -e "${RED}${BOLD}[FATAL] $message${NC}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [FATAL] $message" >> "$ERROR_LOG"
    echo "Check logs: $SETUP_LOG and $ERROR_LOG"
    exit 1
}

check_command() {
    local cmd="$1"
    local package="$2"
    if ! command -v "$cmd" &> /dev/null; then
        log_fatal "Required command '$cmd' not found. Install: $package"
    fi
}

version_compare() {
    local version1="$1"
    local version2="$2"
    printf '%s\n%s\n' "$version1" "$version2" | sort -V | head -n1
}

check_python_version() {
    local python_cmd="$1"
    if ! command -v "$python_cmd" &> /dev/null; then
        return 1
    fi

    local version=$($python_cmd --version 2>&1 | grep -o '[0-9]\+\.[0-9]\+')
    if [[ $(version_compare "$version" "$PYTHON_MIN_VERSION") == "$version" ]] && \
       [[ $(version_compare "$PYTHON_MAX_VERSION" "$version") == "$version" ]]; then
        echo "$version"
        return 0
    fi
    return 1
}

install_system_package() {
    local package="$1"
    local description="$2"

    log_info "Installing critical audio package: $package"
    if ! apt-get install -y "$package" >> "$SETUP_LOG" 2>&1; then
        log_error "Failed to install critical package: $package"
        log_fatal "Setup failed: Failed to install critical package: $package"
    fi
    log_info "Successfully installed: $package ($description)"
}

check_disk_space() {
    local required_gb="$1"
    local available_gb=$(df "$WORK_DIR" | awk 'NR==2 {printf "%.0f", $4/1024/1024}')

    if [[ $available_gb -lt $required_gb ]]; then
        log_fatal "Insufficient disk space. Required: ${required_gb}GB, Available: ${available_gb}GB"
    fi
    log_info "Disk space check passed: ${available_gb}GB available (${required_gb}GB required)"
}

check_memory() {
    local required_gb="$1"
    local available_gb=$(free -g | awk 'NR==2{printf "%.0f", $2}')

    if [[ $available_gb -lt $required_gb ]]; then
        log_warning "Low memory detected. Required: ${required_gb}GB, Available: ${available_gb}GB"
        log_warning "Performance may be degraded. Consider upgrading system memory."
    else
        log_info "Memory check passed: ${available_gb}GB available (${required_gb}GB required)"
    fi
}

detect_gpu() {
    if command -v nvidia-smi &> /dev/null; then
        local gpu_info=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits 2>/dev/null | head -1)
        if [[ -n "$gpu_info" ]]; then
            log_info "NVIDIA GPU detected: $gpu_info"
            return 0
        fi
    fi

    if lspci | grep -i "vga.*amd\|vga.*radeon" &> /dev/null; then
        log_info "AMD GPU detected (limited PyTorch support)"
        return 1
    fi

    log_info "No compatible GPU detected - using CPU mode"
    return 1
}

setup_python_environment() {
    log_step "3" "Setting Up Python Environment"

    # Find compatible Python version
    local python_cmd=""
    for cmd in python3.12 python3.11 python3.10 python3; do
        if python_version=$(check_python_version "$cmd"); then
            python_cmd="$cmd"
            log_info "Using Python $python_version ($cmd)"
            break
        fi
    done

    if [[ -z "$python_cmd" ]]; then
        log_fatal "No compatible Python version found. Required: $PYTHON_MIN_VERSION-$PYTHON_MAX_VERSION"
    fi

    # Create virtual environment
    local venv_dir="$WORK_DIR/venv"
    if [[ -d "$venv_dir" ]]; then
        log_info "Removing existing virtual environment"
        rm -rf "$venv_dir"
    fi

    log_info "Creating fresh virtual environment"
    "$python_cmd" -m venv "$venv_dir" || log_fatal "Failed to create virtual environment"

    # Activate virtual environment
    source "$venv_dir/bin/activate" || log_fatal "Failed to activate virtual environment"

    # Upgrade pip and essential tools
    log_info "Upgrading pip and essential tools"
    python -m pip install --upgrade pip setuptools wheel build || log_fatal "Failed to upgrade pip"

    # Verify activation
    local venv_python=$(which python)
    if [[ "$venv_python" != *"$venv_dir"* ]]; then
        log_fatal "Virtual environment activation failed"
    fi

    log_info "Virtual environment setup completed: $venv_python"
    echo "$venv_dir" > "$WORK_DIR/.venv_path"
}

install_pytorch() {
    log_step "4" "Installing PyTorch with Optimal Configuration"

    local torch_index_url=""
    local torch_packages=""

    if detect_gpu; then
        log_info "Installing PyTorch with CUDA support"
        torch_index_url="https://download.pytorch.org/whl/cu118"
        torch_packages="torch==$PYTORCH_VERSION+cu118 torchvision==$TORCHVISION_VERSION+cu118 torchaudio==$TORCHAUDIO_VERSION+cu118"
    else
        log_info "Installing PyTorch CPU version"
        torch_index_url="https://download.pytorch.org/whl/cpu"
        torch_packages="torch==$PYTORCH_VERSION+cpu torchvision==$TORCHVISION_VERSION+cpu torchaudio==$TORCHAUDIO_VERSION+cpu"
    fi

    pip install $torch_packages --index-url "$torch_index_url" || log_fatal "Failed to install PyTorch"

    # Verify PyTorch installation
    python -c "
import torch
print(f'PyTorch version: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'CUDA device count: {torch.cuda.device_count()}')
    print(f'CUDA device name: {torch.cuda.get_device_name(0)}')
" || log_fatal "PyTorch verification failed"

    log_info "PyTorch installation completed successfully"
}

install_tensorflow() {
    log_step "5" "Installing TensorFlow"

    # Install TensorFlow with appropriate GPU support
    if detect_gpu; then
        log_info "Installing TensorFlow with GPU support"
        pip install "tensorflow[and-cuda]==$TENSORFLOW_VERSION" || log_fatal "Failed to install TensorFlow GPU"
    else
        log_info "Installing TensorFlow CPU version"
        pip install "tensorflow-cpu==$TENSORFLOW_VERSION" || log_fatal "Failed to install TensorFlow CPU"
    fi

    # Verify TensorFlow installation
    python -c "
import tensorflow as tf
print(f'TensorFlow version: {tf.__version__}')
print(f'GPU devices: {tf.config.list_physical_devices(\"GPU\")}')
" || log_fatal "TensorFlow verification failed"

    log_info "TensorFlow installation completed successfully"
}

install_audio_packages() {
    log_step "6" "Installing Core Audio Processing Packages"

    # Core numerical and audio packages
    local audio_packages=(
        "numpy==$NUMPY_VERSION"
        "scipy==$SCIPY_VERSION"
        "librosa==$LIBROSA_VERSION"
        "soundfile==$SOUNDFILE_VERSION"
        "ffmpeg-python==0.2.0"
        "audioread==3.0.1"
        "resampy==0.4.2"
    )

    for package in "${audio_packages[@]}"; do
        log_info "Installing audio package: ${package%%=*}"
        pip install "$package" || log_fatal "Failed to install $package"
    done

    log_info "Core audio packages installed successfully"
}

install_music_analysis_packages() {
    log_step "7" "Installing Music Analysis and MIDI Packages"

    local music_packages=(
        "music21==$MUSIC21_VERSION"
        "pretty_midi==$PRETTY_MIDI_VERSION"
        "mido==$MIDO_VERSION"
        "mir_eval==$MIR_EVAL_VERSION"
        "essential-generators==1.0"
        "pyfluidsynth==1.3.2"
    )

    for package in "${music_packages[@]}"; do
        log_info "Installing music package: ${package%%=*}"
        pip install "$package" || log_fatal "Failed to install $package"
    done

    log_info "Music analysis packages installed successfully"
}

install_ai_models() {
    log_step "8" "Installing AI Model Packages"

    local ai_packages=(
        "demucs==$DEMUCS_VERSION"
        "basic-pitch==$BASIC_PITCH_VERSION"
        "transformers==4.36.2"
        "huggingface-hub==0.19.4"
        "accelerate==0.25.0"
    )

    for package in "${ai_packages[@]}"; do
        log_info "Installing AI package: ${package%%=*}"
        pip install "$package" || log_fatal "Failed to install $package"
    done

    log_info "AI model packages installed successfully"
}

install_web_framework() {
    log_step "9" "Installing Web Framework and API Components"

    local web_packages=(
        "fastapi==$FASTAPI_VERSION"
        "uvicorn[standard]==$UVICORN_VERSION"
        "redis==$REDIS_VERSION"
        "celery[redis]==$CELERY_VERSION"
        "aiofiles==23.2.1"
        "python-multipart==0.0.6"
        "jinja2==3.1.2"
        "python-jose[cryptography]==3.3.0"
    )

    for package in "${web_packages[@]}"; do
        log_info "Installing web package: ${package%%=*}"
        pip install "$package" || log_fatal "Failed to install $package"
    done

    log_info "Web framework packages installed successfully"
}

install_development_tools() {
    log_step "10" "Installing Development and Testing Tools"

    local dev_packages=(
        "pytest==7.4.3"
        "pytest-asyncio==0.21.1"
        "black==23.11.0"
        "flake8==6.1.0"
        "mypy==1.7.1"
        "ipython==8.18.1"
        "jupyter==1.0.0"
        "matplotlib==3.8.2"
        "seaborn==0.13.0"
    )

    for package in "${dev_packages[@]}"; do
        log_info "Installing dev package: ${package%%=*}"
        pip install "$package" || log_fatal "Failed to install $package"
    done

    log_info "Development tools installed successfully"
}

setup_system_services() {
    log_step "11" "Setting Up System Services"

    # Setup Redis service
    log_info "Configuring Redis service"
    if ! systemctl is-active --quiet redis-server; then
        systemctl start redis-server || log_warning "Failed to start Redis service"
    fi

    # Test Redis connection
    python -c "
import redis
r = redis.Redis(host='localhost', port=6379, decode_responses=True)
r.ping()
print('Redis connection successful')
" || log_warning "Redis connection test failed"

    # Create systemd service for M3 Enhanced
    create_systemd_service

    log_info "System services configured successfully"
}

create_systemd_service() {
    log_info "Creating systemd service for M3 Enhanced"

    local service_file="/etc/systemd/system/m3-enhanced.service"
    local venv_path=$(cat "$WORK_DIR/.venv_path" 2>/dev/null || echo "$WORK_DIR/venv")

    cat > "$service_file" << EOF
[Unit]
Description=M3 Enhanced Audio Processing Service
After=network.target redis-server.service
Requires=redis-server.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$WORK_DIR
Environment=PATH=$venv_path/bin
ExecStartPre=/bin/bash -c 'source $venv_path/bin/activate'
ExecStart=$venv_path/bin/python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable m3-enhanced.service

    log_info "Systemd service created and enabled"
}

create_startup_scripts() {
    log_step "12" "Creating Startup and Management Scripts"

    local venv_path=$(cat "$WORK_DIR/.venv_path" 2>/dev/null || echo "$WORK_DIR/venv")

    # Create start script
    cat > "$WORK_DIR/start.sh" << 'EOF'
#!/bin/bash
set -euo pipefail

WORK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$WORK_DIR/venv"

if [[ -f "$WORK_DIR/.venv_path" ]]; then
    VENV_PATH=$(cat "$WORK_DIR/.venv_path")
fi

echo "Starting M3 Enhanced Audio Processing System..."

# Activate virtual environment
source "$VENV_PATH/bin/activate"

# Check if backend application exists
if [[ -f "$WORK_DIR/backend/app/main.py" ]]; then
    cd "$WORK_DIR"
    echo "Starting FastAPI server..."
    python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload &
    SERVER_PID=$!
elif [[ -f "$WORK_DIR/backend/main.py" ]]; then
    cd "$WORK_DIR/backend"
    echo "Starting FastAPI server (legacy path)..."
    python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
    SERVER_PID=$!
else
    echo "Error: Cannot find FastAPI application main.py"
    echo "Expected locations:"
    echo "  - $WORK_DIR/backend/app/main.py"
    echo "  - $WORK_DIR/backend/main.py"
    exit 1
fi

# Start Celery worker
echo "Starting Celery worker..."
cd "$WORK_DIR"
python -m celery -A backend.app.core.job_scheduler worker --loglevel=info --concurrency=2 &
CELERY_PID=$!

echo "M3 Enhanced started successfully!"
echo "Web interface: http://localhost:8000"
echo "API documentation: http://localhost:8000/docs"
echo ""
echo "To stop the services:"
echo "  kill $SERVER_PID $CELERY_PID"

# Keep script running
wait
EOF

    chmod +x "$WORK_DIR/start.sh"

    # Create stop script
    cat > "$WORK_DIR/stop.sh" << 'EOF'
#!/bin/bash
echo "Stopping M3 Enhanced services..."

pkill -f "uvicorn.*main:app" || true
pkill -f "celery.*worker" || true
systemctl stop m3-enhanced.service 2>/dev/null || true

echo "M3 Enhanced stopped."
EOF

    chmod +x "$WORK_DIR/stop.sh"

    # Create status script
    cat > "$WORK_DIR/status.sh" << 'EOF'
#!/bin/bash
echo "M3 Enhanced System Status:"
echo "=========================="

# Check FastAPI server
if pgrep -f "uvicorn.*main:app" > /dev/null; then
    echo "✓ FastAPI server: Running"
else
    echo "✗ FastAPI server: Stopped"
fi

# Check Celery worker
if pgrep -f "celery.*worker" > /dev/null; then
    echo "✓ Celery worker: Running"
else
    echo "✗ Celery worker: Stopped"
fi

# Check Redis
if systemctl is-active --quiet redis-server; then
    echo "✓ Redis server: Running"
else
    echo "✗ Redis server: Stopped"
fi

# Check web interface
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✓ Web interface: Accessible"
else
    echo "✗ Web interface: Not accessible"
fi
EOF

    chmod +x "$WORK_DIR/status.sh"

    log_info "Management scripts created successfully"
}

download_models() {
    log_step "13" "Downloading AI Models"

    local venv_path=$(cat "$WORK_DIR/.venv_path" 2>/dev/null || echo "$WORK_DIR/venv")
    source "$venv_path/bin/activate"

    # Download Demucs models
    log_info "Downloading Demucs models..."
    python -c "
import demucs.pretrained
print('Downloading htdemucs model...')
demucs.pretrained.get_model('htdemucs')
print('Demucs models downloaded successfully')
" || log_warning "Failed to download some Demucs models"

    # Download Basic Pitch models
    log_info "Downloading Basic Pitch models..."
    python -c "
from basic_pitch import ICASSP_2022_MODEL_PATH
from basic_pitch.inference import Model
print('Downloading Basic Pitch model...')
model = Model(ICASSP_2022_MODEL_PATH)
print('Basic Pitch models downloaded successfully')
" || log_warning "Failed to download Basic Pitch models"

    log_info "AI model downloads completed"
}

run_system_tests() {
    log_step "14" "Running System Integration Tests"

    local venv_path=$(cat "$WORK_DIR/.venv_path" 2>/dev/null || echo "$WORK_DIR/venv")
    source "$venv_path/bin/activate"

    # Test core imports
    log_info "Testing core package imports..."
    python -c "
import numpy, scipy, librosa, soundfile
import torch, tensorflow as tf
import music21, pretty_midi, mido
import fastapi, uvicorn, redis, celery
import demucs
from basic_pitch import ICASSP_2022_MODEL_PATH
print('All core imports successful')
" || log_fatal "Core package import test failed"

    # Test Redis connection
    log_info "Testing Redis connection..."
    python -c "
import redis
r = redis.Redis(host='localhost', port=6379, decode_responses=True)
r.ping()
r.set('test_key', 'test_value')
assert r.get('test_key') == 'test_value'
r.delete('test_key')
print('Redis connection test passed')
" || log_warning "Redis connection test failed"

    # Test audio processing
    log_info "Testing audio processing capabilities..."
    python -c "
import numpy as np
import librosa
import soundfile as sf
import tempfile
import os

# Generate test audio
sr = 44100
duration = 1.0
t = np.linspace(0, duration, int(sr * duration))
test_audio = 0.5 * np.sin(2 * np.pi * 440 * t)

# Test file I/O
with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
    sf.write(tmp.name, test_audio, sr)
    loaded_audio, loaded_sr = librosa.load(tmp.name, sr=sr)
    os.unlink(tmp.name)

assert loaded_sr == sr
assert len(loaded_audio) > 0
print('Audio processing test passed')
" || log_fatal "Audio processing test failed"

    log_info "System integration tests completed successfully"
}

finalize_setup() {
    log_step "15" "Finalizing Setup and Configuration"

    # Set proper permissions
    chmod -R 755 "$WORK_DIR"/{start.sh,stop.sh,status.sh}

    # Create configuration files
    create_config_files

    # Final system verification
    final_verification

    # Calculate setup duration
    local end_time=$(date +%s)
    local duration=$((end_time - START_TIME))
    local duration_formatted=$(date -ud "@$duration" +'%H:%M:%S')

    log_info "Setup completed successfully in $duration_formatted"

    # Display final instructions
    display_final_instructions
}

create_config_files() {
    log_info "Creating configuration files..."

    # Create .env file if it doesn't exist
    if [[ ! -f "$WORK_DIR/.env" ]]; then
        cp "$WORK_DIR/.env.example" "$WORK_DIR/.env" 2>/dev/null || {
            cat > "$WORK_DIR/.env" << 'EOF'
# M3 Enhanced Configuration
REDIS_URL=redis://localhost:6379
MODELS_DIR=./models
TEMP_DIR=./temp
UPLOADS_DIR=./uploads
RESULTS_DIR=./results
MAX_WORKERS=4
GPU_ENABLED=true
BATCH_SIZE=8
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
DEFAULT_SEPARATOR=demucs
DEFAULT_TRANSCRIBER=basic_pitch
ENABLE_CLASSIFICATION=true
EOF
        }
        log_info "Created default .env configuration"
    fi

    # Update configuration with actual paths
    sed -i "s|MODELS_DIR=.*|MODELS_DIR=$MODELS_DIR|g" "$WORK_DIR/.env"
    sed -i "s|TEMP_DIR=.*|TEMP_DIR=$TEMP_DIR|g" "$WORK_DIR/.env"
    sed -i "s|UPLOADS_DIR=.*|UPLOADS_DIR=$UPLOADS_DIR|g" "$WORK_DIR/.env"
    sed -i "s|RESULTS_DIR=.*|RESULTS_DIR=$RESULTS_DIR|g" "$WORK_DIR/.env"
}

final_verification() {
    log_info "Running final system verification..."

    local venv_path=$(cat "$WORK_DIR/.venv_path" 2>/dev/null || echo "$WORK_DIR/venv")

    # Verify virtual environment
    if [[ ! -d "$venv_path" ]]; then
        log_fatal "Virtual environment not found: $venv_path"
    fi

    # Verify essential files
    local essential_files=(
        "$WORK_DIR/start.sh"
        "$WORK_DIR/stop.sh"
        "$WORK_DIR/status.sh"
        "$WORK_DIR/.env"
    )

    for file in "${essential_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            log_fatal "Essential file missing: $file"
        fi
    done

    # Verify FastAPI application
    if [[ -f "$WORK_DIR/backend/app/main.py" ]]; then
        log_info "FastAPI application found at: backend/app/main.py"
    elif [[ -f "$WORK_DIR/backend/main.py" ]]; then
        log_info "FastAPI application found at: backend/main.py"
    else
        log_warning "FastAPI application main.py not found in expected locations"
    fi

    log_info "Final verification completed successfully"
}

display_final_instructions() {
    echo ""
    echo "======================================================="
    echo "              M3 Enhanced Setup Complete!"
    echo "======================================================="
    echo ""
    echo "System Information:"
    echo "  - Version: $SCRIPT_VERSION"
    echo "  - Installation Directory: $WORK_DIR"
    echo "  - Virtual Environment: $(cat "$WORK_DIR/.venv_path" 2>/dev/null || echo "$WORK_DIR/venv")"
    echo "  - Configuration File: $WORK_DIR/.env"
    echo ""
    echo "Management Commands:"
    echo "  - Start Services:    ./start.sh"
    echo "  - Stop Services:     ./stop.sh"
    echo "  - Check Status:      ./status.sh"
    echo ""
    echo "Web Interfaces:"
    echo "  - Main Interface:    http://localhost:8000"
    echo "  - API Documentation: http://localhost:8000/docs"
    echo "  - Health Check:      http://localhost:8000/health"
    echo ""
    echo "Service Management:"
    echo "  - SystemD Service:   sudo systemctl {start|stop|status} m3-enhanced"
    echo ""
    echo "Logs and Diagnostics:"
    echo "  - Setup Log:         $SETUP_LOG"
    echo "  - Error Log:         $ERROR_LOG"
    echo "  - Result File:       $RESULT_FILE"
    echo ""
    echo "Next Steps:"
    echo "  1. Run './start.sh' to start all services"
    echo "  2. Open http://localhost:8000 in your browser"
    echo "  3. Upload an audio file to test the system"
    echo ""
    echo "======================================================="
}

#=======================================================
#                    MAIN EXECUTION
#=======================================================

main() {
    print_header

    log_info "Starting M3 Enhanced sonic accuracy setup..."
    log_info "Version: $SCRIPT_VERSION"
    log_info "Zero-compromise audio fidelity mode enabled"

    # Step 1: System Verification
    log_step "1" "Sonic Accuracy System Verification"

    # Check if running as root (not recommended)
    if [[ $EUID -eq 0 ]]; then
        log_warning "Running as root is not recommended. Consider using a regular user account."
    fi

    # Verify Python version compatibility
    local python_version=""
    for cmd in python3.12 python3.11 python3.10 python3; do
        if python_version=$(check_python_version "$cmd"); then
            log_info "Python $python_version verified for sonic accuracy (compatible range: $PYTHON_MIN_VERSION-$PYTHON_MAX_VERSION)"
            break
        fi
    done

    if [[ -z "$python_version" ]]; then
        log_fatal "No compatible Python version found. Install Python $PYTHON_MIN_VERSION-$PYTHON_MAX_VERSION"
    fi

    # System resource checks
    check_disk_space "$MIN_DISK_GB"
    check_memory "$MIN_RAM_GB"

    log_info "System verification completed - ready for sonic accuracy setup"

    # Step 2: System Dependencies
    log_step "2" "Installing Precise System Dependencies for Sonic Accuracy"

    # Update package lists
    apt-get update >> "$SETUP_LOG" 2>&1 || log_fatal "Failed to update package lists"

    # Critical system packages for audio processing
    local system_packages=(
        "build-essential:Compilation tools for native extensions"
        "ffmpeg:FFmpeg multimedia framework"
        "libsndfile1-dev:Sound file library development files"
        "libasound2-dev:ALSA sound library development files"
        "portaudio19-dev:PortAudio development files (FIXED: was libportaudio19-dev)"
        "libfftw3-dev:FFTW3 library for fast Fourier transforms"
        "libsamplerate0-dev:Sample rate conversion library"
        "libflac-dev:FLAC audio codec development files"
        "libvorbis-dev:Vorbis audio codec development files"
        "libmp3lame-dev:LAME MP3 encoder development files"
        "libopus-dev:Opus audio codec development files"
        "pkg-config:Package configuration tool"
        "cmake:Build system generator"
        "git:Version control system"
        "curl:HTTP client tool"
        "wget:File download tool"
        "unzip:Archive extraction tool"
        "redis-server:Redis in-memory data store"
        "supervisor:Process management system"
    )

    for pkg_info in "${system_packages[@]}"; do
        local package="${pkg_info%%:*}"
        local description="${pkg_info#*:}"
        install_system_package "$package" "$description"
    done

    log_info "System dependencies installation completed"

    # Continue with Python environment and package installation
    setup_python_environment
    install_pytorch
    install_tensorflow
    install_audio_packages
    install_music_analysis_packages
    install_ai_models
    install_web_framework
    install_development_tools
    setup_system_services
    create_startup_scripts
    download_models
    run_system_tests
    finalize_setup
}

# Execute main function with error handling
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
