#!/bin/bash

#=======================================================
#         M3 Enhanced - COMPREHENSIVE PRODUCTION Setup Script
#              Maximum Reliability Deployment v5.3
#=======================================================

set -euo pipefail

# Global Configuration
readonly SCRIPT_VERSION="5.3.0"
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
    echo "         M3 Enhanced - COMPREHENSIVE PRODUCTION Setup"
    echo "              Maximum Reliability Deployment v5.3"
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
        log_error "Failed to install package: $package"
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

    log_info "Successfully installed Python package: $description"
    return 0
}

verify_package_installed() {
    local package="$1"
    if dpkg -l | grep -q "^ii  $package "; then
        log_info "Verified: $package is installed"
        return 0
    else
        log_error "Verification failed: $package is not installed"
        return 1
    fi
}

verify_python_package() {
    local package="$1"
    local import_name="${2:-$package}"

    if python3 -c "import $import_name" 2>/dev/null; then
        log_info "Verified: Python package $package is available"
        return 0
    else
        log_error "Verification failed: Python package $package is not available"
        return 1
    fi
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

    log_error "$service failed to start after $max_attempts attempts"
    return 1
}

#=======================================================
#               COMPREHENSIVE SYSTEM VERIFICATION
#=======================================================

verify_system() {
    log_step 1 "Comprehensive System Verification"

    # Check if running as root
    if [ "$EUID" -eq 0 ]; then
        log_warn "Running as root - this may cause permission issues"
        log_warn "Consider running as a regular user with sudo privileges"
    fi

    # Detailed OS Detection and Validation
    if [ ! -f /etc/os-release ]; then
        fatal_error "Cannot determine operating system - /etc/os-release not found"
    fi

    source /etc/os-release
    log_info "Operating System: $PRETTY_NAME"
    log_info "OS ID: $ID"
    log_info "OS Version ID: $VERSION_ID"

    # Comprehensive OS Support Check
    case "$ID" in
        ubuntu)
            if [[ "$VERSION_ID" < "20.04" ]]; then
                fatal_error "Ubuntu version $VERSION_ID not supported (minimum: 20.04)"
            fi
            log_info "Ubuntu $VERSION_ID detected and supported"
            ;;
        debian)
            if [[ "$VERSION_ID" < "11" ]]; then
                fatal_error "Debian version $VERSION_ID not supported (minimum: 11)"
            fi
            log_info "Debian $VERSION_ID detected and supported"
            ;;
        *)
            fatal_error "Unsupported operating system: $ID (supported: Ubuntu 20.04+, Debian 11+)"
            ;;
    esac

    # Comprehensive Disk Space Check
    local available_gb=$(df "$WORK_DIR" | awk 'NR==2 {print int($4/1024/1024)}')
    local available_mb=$(df "$WORK_DIR" | awk 'NR==2 {print int($4/1024)}')
    log_info "Available disk space: ${available_gb}GB (${available_mb}MB)"
    log_info "Required disk space: ${MIN_DISK_GB}GB"

    if [ "$available_gb" -lt "$MIN_DISK_GB" ]; then
        fatal_error "Insufficient disk space: ${available_gb}GB available, ${MIN_DISK_GB}GB required"
    fi

    # Comprehensive RAM Check
    local ram_gb=$(free -g | awk 'NR==2{print $2}')
    local ram_mb=$(free -m | awk 'NR==2{print $2}')
    log_info "Available RAM: ${ram_gb}GB (${ram_mb}MB)"
    log_info "Recommended RAM: ${MIN_RAM_GB}GB"

    if [ "$ram_gb" -lt "$MIN_RAM_GB" ]; then
        log_warn "Low RAM detected: ${ram_gb}GB available, ${MIN_RAM_GB}GB recommended"
        log_warn "Performance may be degraded with insufficient RAM"
    fi

    # Comprehensive Python Version Check
    if ! command -v python3 >/dev/null 2>&1; then
        fatal_error "Python 3 not found in PATH"
    fi

    local python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")
    local python_major=$(python3 -c "import sys; print(sys.version_info.major)")
    local python_minor=$(python3 -c "import sys; print(sys.version_info.minor)")

    log_info "Python version: $python_version"
    log_info "Python executable: $(which python3)"

    # Detailed Python version compatibility check
    if [ "$python_major" -ne 3 ]; then
        fatal_error "Python major version $python_major not supported (required: 3)"
    fi

    if [ "$python_minor" -lt 8 ] || [ "$python_minor" -gt 12 ]; then
        fatal_error "Python version $python_version not supported (supported: 3.8-3.12)"
    fi

    log_info "Python version $python_version is compatible"

    # Comprehensive Repository Structure Verification
    log_info "Verifying repository structure..."

    # Check critical backend files
    if [ ! -f "$WORK_DIR/backend/app/main.py" ]; then
        fatal_error "FastAPI application not found at backend/app/main.py"
    fi
    log_info "Verified: FastAPI application exists at backend/app/main.py"

    # Check frontend files
    if [ ! -f "$WORK_DIR/frontend/static/index.html" ]; then
        fatal_error "Frontend index.html not found at frontend/static/index.html"
    fi
    log_info "Verified: Frontend index.html exists at frontend/static/index.html"

    if [ ! -f "$WORK_DIR/frontend/static/style.css" ]; then
        fatal_error "Frontend CSS not found at frontend/static/style.css"
    fi
    log_info "Verified: Frontend CSS exists at frontend/static/style.css"

    if [ ! -f "$WORK_DIR/frontend/static/app.js" ]; then
        fatal_error "Frontend JavaScript not found at frontend/static/app.js"
    fi
    log_info "Verified: Frontend JavaScript exists at frontend/static/app.js"

    # Check for additional backend structure
    if [ -d "$WORK_DIR/backend/app/core" ]; then
        log_info "Verified: Backend core module directory exists"
    else
        log_warn "Backend core module directory not found (may be created later)"
    fi

    if [ -d "$WORK_DIR/backend/app/models" ]; then
        log_info "Verified: Backend models module directory exists"
    else
        log_warn "Backend models module directory not found (may be created later)"
    fi

    # Check system architecture
    local arch=$(uname -m)
    log_info "System architecture: $arch"

    case "$arch" in
        x86_64)
            log_info "x86_64 architecture detected and supported"
            ;;
        aarch64|arm64)
            log_info "ARM64 architecture detected - some optimizations may not be available"
            ;;
        *)
            log_warn "Architecture $arch may have limited support"
            ;;
    esac

    # Check for critical system tools
    local required_tools=("wget" "curl" "git" "gcc" "make")
    for tool in "${required_tools[@]}"; do
        if command -v "$tool" >/dev/null 2>&1; then
            log_info "Verified: $tool is available"
        else
            log_warn "Missing system tool: $tool (will be installed)"
        fi
    done

    log_info "System verification completed successfully"
}

#=======================================================
#               COMPREHENSIVE SYSTEM DEPENDENCIES
#=======================================================

install_system_dependencies() {
    log_step 2 "Installing Comprehensive System Dependencies"

    # Update package lists with retries
    log_info "Updating package lists..."
    local update_attempts=0
    local max_update_attempts=3

    while [ $update_attempts -lt $max_update_attempts ]; do
        if apt-get update; then
            log_info "Package lists updated successfully"
            break
        else
            update_attempts=$((update_attempts + 1))
            log_warn "Package update attempt $update_attempts failed, retrying..."
            sleep 5
        fi
    done

    if [ $update_attempts -eq $max_update_attempts ]; then
        fatal_error "Failed to update package lists after $max_update_attempts attempts"
    fi

    # Fix any broken packages with detailed output
    log_info "Fixing any broken packages and dependencies..."
    DEBIAN_FRONTEND=noninteractive apt-get -f install -y || {
        log_warn "Package fix attempt had issues, continuing..."
    }

    # Install essential build and system packages
    log_info "Installing essential build and system packages..."

    local essential_packages=(
        "build-essential"
        "software-properties-common"
        "apt-transport-https"
        "ca-certificates"
        "curl"
        "wget"
        "git"
        "unzip"
        "zip"
        "pkg-config"
        "gcc"
        "g++"
        "make"
        "cmake"
        "autoconf"
        "automake"
        "libtool"
    )

    for package in "${essential_packages[@]}"; do
        log_info "Installing essential package: $package"
        if install_package "$package"; then
            verify_package_installed "$package" || log_warn "Package verification failed: $package"
        else
            fatal_error "Failed to install critical essential package: $package"
        fi
    done

    log_info "Essential packages installation completed"

    # Install comprehensive audio processing libraries
    log_info "Installing comprehensive audio processing libraries..."

    local audio_packages=(
        "ffmpeg"
        "libsndfile1"
        "libsndfile1-dev"
        "libasound2"
        "libasound2-dev"
    )

    for package in "${audio_packages[@]}"; do
        log_info "Installing audio package: $package"
        if install_package "$package"; then
            verify_package_installed "$package" || log_warn "Audio package verification failed: $package"
        else
            log_error "Failed to install audio package: $package"
            fatal_error "Critical audio package installation failed: $package"
        fi
    done

    log_info "Core audio packages installation completed"

    # Install advanced audio libraries with detailed fallback handling
    log_info "Installing advanced audio libraries..."

    # PortAudio with comprehensive fallback
    log_info "Installing PortAudio development libraries..."
    if install_package "libportaudio19-dev"; then
        verify_package_installed "libportaudio19-dev"
        log_info "PortAudio development libraries installed successfully"
    else
        log_warn "Primary PortAudio package failed, trying alternative..."
        if install_package "portaudio19-dev"; then
            verify_package_installed "portaudio19-dev"
            log_info "Alternative PortAudio package installed successfully"
        else
            log_error "All PortAudio installation attempts failed"
            fatal_error "PortAudio development libraries are required for audio processing"
        fi
    fi

    # FFTW development libraries
    log_info "Installing FFTW development libraries..."
    if install_package "libfftw3-dev"; then
        verify_package_installed "libfftw3-dev"
        log_info "FFTW development libraries installed successfully"
    else
        fatal_error "FFTW development libraries installation failed"
    fi

    # Sample rate conversion libraries
    log_info "Installing sample rate conversion libraries..."
    if install_package "libsamplerate0-dev"; then
        verify_package_installed "libsamplerate0-dev"
        log_info "Sample rate conversion libraries installed successfully"
    else
        fatal_error "Sample rate conversion libraries installation failed"
    fi

    # JACK development libraries with conflict resolution
    log_info "Installing JACK development libraries..."
    # Remove any conflicting JACK packages first
    apt-get remove -y libjack-dev 2>/dev/null || true
    apt-get remove -y libjack0 2>/dev/null || true

    if install_package "libjack-jackd2-dev"; then
        verify_package_installed "libjack-jackd2-dev"
        log_info "JACK development libraries installed successfully"
    else
        log_warn "JACK development libraries installation failed (optional for some features)"
    fi

    log_info "Advanced audio libraries installation completed"

    # Install comprehensive codec support
    log_info "Installing comprehensive codec support..."

    local codec_packages=(
        "libmp3lame-dev"
        "libopus-dev"
        "libvorbis-dev"
        "libflac-dev"
        "libogg-dev"
        "libmad0-dev"
    )

    for package in "${codec_packages[@]}"; do
        log_info "Installing codec package: $package"
        if install_package "$package"; then
            verify_package_installed "$package" || log_warn "Codec package verification failed: $package"
            log_info "Successfully installed codec support: $package"
        else
            log_warn "Failed to install codec package: $package (optional)"
        fi
    done

    log_info "Codec support installation completed"

    # Install comprehensive Python development libraries
    log_info "Installing comprehensive Python development environment..."

    local python_dev_packages=(
        "python3-dev"
        "python3-pip"
        "python3-venv"
        "python3-setuptools"
        "python3-wheel"
        "python3-distutils"
    )

    for package in "${python_dev_packages[@]}"; do
        log_info "Installing Python development package: $package"
        if install_package "$package"; then
            verify_package_installed "$package" || log_warn "Python dev package verification failed: $package"
            log_info "Successfully installed Python development package: $package"
        else
            fatal_error "Failed to install critical Python development package: $package"
        fi
    done

    log_info "Python development environment installation completed"

    # Install comprehensive system development libraries
    log_info "Installing comprehensive system development libraries..."

    local system_dev_packages=(
        "libssl-dev"
        "libffi-dev"
        "libbz2-dev"
        "liblzma-dev"
        "libreadline-dev"
        "libsqlite3-dev"
        "libxml2-dev"
        "libxslt1-dev"
        "zlib1g-dev"
        "libncurses5-dev"
        "libgdbm-dev"
        "libnss3-dev"
    )

    for package in "${system_dev_packages[@]}"; do
        log_info "Installing system development package: $package"
        if install_package "$package"; then
            verify_package_installed "$package" || log_warn "System dev package verification failed: $package"
            log_info "Successfully installed system development package: $package"
        else
            log_warn "Failed to install system development package: $package"
        fi
    done

    log_info "System development libraries installation completed"

    # Install Redis server with comprehensive setup
    log_info "Installing Redis server with comprehensive configuration..."

    if install_package "redis-server"; then
        verify_package_installed "redis-server"
        log_info "Redis server package installed successfully"

        # Install Redis tools
        if install_package "redis-tools"; then
            verify_package_installed "redis-tools"
            log_info "Redis tools installed successfully"
        else
            log_warn "Redis tools installation failed (may already be included)"
        fi

        log_info "Redis installation completed successfully"
    else
        fatal_error "Redis server installation failed - required for task queue"
    fi

    # Verify all critical system dependencies
    log_info "Verifying all critical system dependencies..."

    local critical_packages=("build-essential" "python3-dev" "python3-pip" "ffmpeg" "redis-server")
    for package in "${critical_packages[@]}"; do
        if verify_package_installed "$package"; then
            log_info "Critical package verification passed: $package"
        else
            fatal_error "Critical package verification failed: $package"
        fi
    done

    log_info "System dependencies installation and verification completed successfully"
}

#=======================================================
#               COMPREHENSIVE PYTHON ENVIRONMENT SETUP
#=======================================================

setup_python_environment() {
    log_step 3 "Comprehensive Python Environment Setup"

    # Verify Python installation details
    log_info "Analyzing Python installation..."
    python3 -c "
import sys
import sysconfig
print(f'Python executable: {sys.executable}')
print(f'Python version: {sys.version}')
print(f'Python path: {sys.path}')
print(f'Site packages: {sysconfig.get_paths()[\"purelib\"]}')
"

    # Comprehensive pip upgrade with retries
    log_info "Upgrading pip with comprehensive error handling..."
    local pip_upgrade_attempts=0
    local max_pip_attempts=3

    while [ $pip_upgrade_attempts -lt $max_pip_attempts ]; do
        echo -e "${BLUE}Running: Upgrading pip (attempt $((pip_upgrade_attempts + 1)))${NC}"
        if python3 -m pip install --upgrade pip; then
            log_info "Pip upgrade completed successfully"
            break
        else
            pip_upgrade_attempts=$((pip_upgrade_attempts + 1))
            log_warn "Pip upgrade attempt $pip_upgrade_attempts failed"
            if [ $pip_upgrade_attempts -lt $max_pip_attempts ]; then
                log_info "Retrying pip upgrade in 5 seconds..."
                sleep 5
            fi
        fi
    done

    if [ $pip_upgrade_attempts -eq $max_pip_attempts ]; then
        fatal_error "Failed to upgrade pip after $max_pip_attempts attempts"
    fi

    # Verify pip installation and version
    local pip_version=$(python3 -m pip --version)
    log_info "Pip version after upgrade: $pip_version"

    # Comprehensive setuptools upgrade
    log_info "Upgrading setuptools with comprehensive error handling..."
    echo -e "${BLUE}Running: Upgrading setuptools${NC}"
    if python3 -m pip install --upgrade setuptools; then
        local setuptools_version=$(python3 -c "import setuptools; print(setuptools.__version__)")
        log_info "Setuptools upgraded successfully to version: $setuptools_version"
    else
        fatal_error "Failed to upgrade setuptools"
    fi

    # Comprehensive wheel upgrade
    log_info "Upgrading wheel with comprehensive error handling..."
    echo -e "${BLUE}Running: Upgrading wheel${NC}"
    if python3 -m pip install --upgrade wheel; then
        local wheel_version=$(python3 -c "import wheel; print(wheel.__version__)")
        log_info "Wheel upgraded successfully to version: $wheel_version"
    else
        fatal_error "Failed to upgrade wheel"
    fi

    # Install comprehensive build dependencies with individual verification
    log_info "Installing comprehensive build dependencies..."

    # Build system
    log_info "Installing build system package..."
    echo -e "${BLUE}Running: Installing build${NC}"
    if pip_install "build" "Build System"; then
        verify_python_package "build" || log_warn "Build package verification failed"
    else
        fatal_error "Failed to install build system"
    fi

    # CMake
    log_info "Installing CMake Python package..."
    echo -e "${BLUE}Running: Installing cmake${NC}"
    if pip_install "cmake" "CMake"; then
        verify_python_package "cmake" || log_warn "CMake package verification failed"
    else
        log_warn "CMake Python package installation failed (system cmake may be sufficient)"
    fi

    # Ninja build system
    log_info "Installing Ninja build system..."
    echo -e "${BLUE}Running: Installing ninja${NC}"
    if pip_install "ninja" "Ninja Build System"; then
        verify_python_package "ninja" || log_warn "Ninja package verification failed"
    else
        log_warn "Ninja build system installation failed (optional)"
    fi

    # Pybind11 with global installation
    log_info "Installing Pybind11 with global support..."
    echo -e "${BLUE}Running: Installing pybind11[global]${NC}"
    if pip_install "pybind11[global]" "Pybind11 with Global Support"; then
        verify_python_package "pybind11" || log_warn "Pybind11 package verification failed"
        log_info "Pybind11 with global support installed successfully"
    else
        log_warn "Pybind11 global installation failed, trying standard pybind11..."
        if pip_install "pybind11" "Pybind11 Standard"; then
            verify_python_package "pybind11" || log_warn "Pybind11 standard verification failed"
        else
            log_warn "Pybind11 installation failed (may affect some package builds)"
        fi
    fi

    # Cython
    log_info "Installing Cython compilation system..."
    echo -e "${BLUE}Running: Installing cython${NC}"
    if pip_install "cython" "Cython"; then
        verify_python_package "cython" "Cython"
        local cython_version=$(python3 -c "import Cython; print(Cython.__version__)")
        log_info "Cython installed successfully, version: $cython_version"
    else
        log_warn "Cython installation failed (may affect some package compilation)"
    fi

    # Verify build environment
    log_info "Verifying Python build environment..."

    python3 -c "
import sys
import subprocess

# Check pip functionality
try:
    import pip
    print('✓ Pip module available')
except ImportError:
    print('✗ Pip module not available')

# Check setuptools functionality
try:
    import setuptools
    print(f'✓ Setuptools available: {setuptools.__version__}')
except ImportError:
    print('✗ Setuptools not available')

# Check wheel functionality
try:
    import wheel
    print(f'✓ Wheel available: {wheel.__version__}')
except ImportError:
    print('✗ Wheel not available')

# Check compiler availability
try:
    import distutils.util
    import distutils.ccompiler
    compiler = distutils.ccompiler.new_compiler()
    print('✓ C compiler available through distutils')
except:
    print('✗ C compiler not available through distutils')
"

    log_info "Python environment setup completed successfully"
}

#=======================================================
#               COMPREHENSIVE DEPENDENCY CONFLICT RESOLUTION
#=======================================================

resolve_dependency_conflicts() {
    log_step 4 "Comprehensive Dependency Conflict Resolution"

    log_info "Beginning comprehensive dependency conflict resolution..."

    # Comprehensive list of packages that may cause conflicts
    local conflict_packages=(
        "intel-openmp"
        "mkl"
        "mkl-service"
        "mkl-random"
        "mkl-fft"
        "numpy"
        "scipy"
        "scikit-learn"
        "sklearn"
        "pandas"
        "matplotlib"
        "opencv-python"
        "opencv-contrib-python"
        "opencv-python-headless"
        "opencv-contrib-python-headless"
        "tensorflow"
        "tensorflow-cpu"
        "tensorflow-gpu"
        "torch"
        "torchvision"
        "torchaudio"
        "torchtext"
        "librosa"
        "soundfile"
        "audioread"
        "resampy"
        "music21"
        "pretty-midi"
        "mido"
        "basic-pitch"
        "mir-eval"
    )

    log_info "Removing potentially conflicting packages..."
    for package in "${conflict_packages[@]}"; do
        log_info "Checking and removing conflicting package: $package"
        if python3 -m pip show "$package" >/dev/null 2>&1; then
            log_info "Found conflicting package $package, removing..."
            python3 -m pip uninstall -y "$package" 2>/dev/null || {
                log_warn "Failed to cleanly uninstall $package, forcing removal..."
                python3 -m pip uninstall -y "$package" --break-system-packages 2>/dev/null || true
            }
            log_info "Removed conflicting package: $package"
        else
            log_info "Package $package not installed, skipping"
        fi
    done

    # Comprehensive pip cache cleanup
    log_info "Performing comprehensive pip cache cleanup..."
    python3 -m pip cache purge || {
        log_warn "Pip cache purge failed, trying manual cleanup..."
        rm -rf ~/.cache/pip/* 2>/dev/null || true
        rm -rf /tmp/pip-* 2>/dev/null || true
    }

    # Clear any orphaned package metadata
    log_info "Clearing orphaned package metadata..."
    python3 -c "
import sys
import os
import shutil
import site

# Clear pycache
for path in sys.path:
    if os.path.exists(path):
        for root, dirs, files in os.walk(path):
            for dir_name in dirs:
                if dir_name == '__pycache__':
                    pycache_path = os.path.join(root, dir_name)
                    try:
                        shutil.rmtree(pycache_path)
                        print(f'Cleared pycache: {pycache_path}')
                    except:
                        pass

print('Package metadata cleanup completed')
"

    # Verify clean state
    log_info "Verifying clean dependency state..."

    local verification_packages=("numpy" "scipy" "torch" "tensorflow")
    for package in "${verification_packages[@]}"; do
        if python3 -m pip show "$package" >/dev/null 2>&1; then
            log_warn "Package $package still present after cleanup - this may indicate a problem"
        else
            log_info "Confirmed $package has been removed"
        fi
    done

    log_info "Dependency conflict resolution completed successfully"
}

#=======================================================
#               COMPREHENSIVE CORE ML FRAMEWORKS INSTALLATION
#=======================================================

install_core_ml_frameworks() {
    log_step 5 "Installing Comprehensive Core ML Frameworks"

    log_info "Beginning comprehensive ML framework installation with strict version control..."

    # Install NumPy with specific version constraints and verification
    log_info "Installing NumPy with comprehensive version control..."
    echo -e "${BLUE}Running: Installing NumPy with version constraints${NC}"

    local numpy_version="numpy<2.0.0,>=1.21.0"
    if pip_install "$numpy_version" "NumPy with Version Constraints"; then
        # Comprehensive NumPy verification
        python3 -c "
import numpy as np
print(f'NumPy version: {np.__version__}')
print(f'NumPy install path: {np.__file__}')
print(f'NumPy configuration: {np.show_config()}')

# Test basic NumPy functionality
test_array = np.array([1, 2, 3, 4, 5])
print(f'NumPy test array: {test_array}')
print(f'NumPy test sum: {np.sum(test_array)}')
print('✓ NumPy installation verified successfully')
"
        log_info "NumPy installation and verification completed successfully"
    else
        fatal_error "NumPy installation failed - this is critical for all ML operations"
    fi

    # Install SciPy with comprehensive verification
    log_info "Installing SciPy with comprehensive verification..."
    echo -e "${BLUE}Running: Installing SciPy${NC}"

    local scipy_version="scipy>=1.7.0"
    if pip_install "$scipy_version" "SciPy"; then
        # Comprehensive SciPy verification
        python3 -c "
import scipy
import numpy as np
from scipy import linalg

print(f'SciPy version: {scipy.__version__}')
print(f'SciPy install path: {scipy.__file__}')

# Test basic SciPy functionality
test_matrix = np.array([[1, 2], [3, 4]])
det = linalg.det(test_matrix)
print(f'SciPy test determinant: {det}')
print('✓ SciPy installation verified successfully')
"
        log_info "SciPy installation and verification completed successfully"
    else
        fatal_error "SciPy installation failed - this is critical for scientific computing"
    fi

    # Install scikit-learn with comprehensive verification
    log_info "Installing scikit-learn with comprehensive verification..."
    echo -e "${BLUE}Running: Installing scikit-learn${NC}"

    local sklearn_version="scikit-learn>=1.0.0"
    if pip_install "$sklearn_version" "scikit-learn"; then
        # Comprehensive scikit-learn verification
        python3 -c "
import sklearn
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split

print(f'scikit-learn version: {sklearn.__version__}')
print(f'scikit-learn install path: {sklearn.__file__}')

# Test basic sklearn functionality
X, y = make_classification(n_samples=100, n_features=4, n_classes=2, random_state=42)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
print(f'sklearn test data shape: {X_train.shape}')
print('✓ scikit-learn installation verified successfully')
"
        log_info "scikit-learn installation and verification completed successfully"
    else
        fatal_error "scikit-learn installation failed - this is critical for ML operations"
    fi

    # Install PyTorch (CPU version) with comprehensive verification
    log_info "Installing PyTorch CPU version with comprehensive verification..."
    echo -e "${BLUE}Running: Installing PyTorch CPU version${NC}"

    local pytorch_install="--index-url https://download.pytorch.org/whl/cpu torch torchvision torchaudio"
    if pip_install "$pytorch_install" "PyTorch CPU Suite"; then
        # Comprehensive PyTorch verification
        python3 -c "
import torch
import torchvision
import torchaudio

print(f'PyTorch version: {torch.__version__}')
print(f'PyTorch install path: {torch.__file__}')
print(f'TorchVision version: {torchvision.__version__}')
print(f'TorchAudio version: {torchaudio.__version__}')

# Test CUDA availability (should be False for CPU version)
print(f'CUDA available: {torch.cuda.is_available()}')
print(f'CUDA device count: {torch.cuda.device_count()}')

# Test basic PyTorch functionality
test_tensor = torch.randn(2, 3)
print(f'PyTorch test tensor: {test_tensor}')
print(f'PyTorch test tensor sum: {torch.sum(test_tensor)}')

# Test torchvision
from torchvision import transforms
transform = transforms.Compose([transforms.ToTensor()])
print('✓ TorchVision transforms available')

print('✓ PyTorch installation verified successfully')
"
        log_info "PyTorch installation and verification completed successfully"
    else
        fatal_error "PyTorch installation failed - this is critical for deep learning operations"
    fi

    # Install TensorFlow with comprehensive verification
    log_info "Installing TensorFlow with comprehensive verification..."
    echo -e "${BLUE}Running: Installing TensorFlow${NC}"

    local tensorflow_version="tensorflow>=2.13.0"
    if pip_install "$tensorflow_version" "TensorFlow"; then
        # Comprehensive TensorFlow verification
        python3 -c "
import tensorflow as tf
import numpy as np

print(f'TensorFlow version: {tf.__version__}')
print(f'TensorFlow install path: {tf.__file__}')

# Check device configuration
print('Available devices:')
for device in tf.config.list_physical_devices():
    print(f'  {device}')

# Test basic TensorFlow functionality
test_tensor = tf.constant([[1.0, 2.0], [3.0, 4.0]])
print(f'TensorFlow test tensor: {test_tensor}')
print(f'TensorFlow test sum: {tf.reduce_sum(test_tensor)}')

# Test Keras functionality
from tensorflow import keras
print(f'Keras version: {keras.__version__}')

print('✓ TensorFlow installation verified successfully')
"
        log_info "TensorFlow installation and verification completed successfully"
    else
        fatal_error "TensorFlow installation failed - this is critical for deep learning operations"
    fi

    # Final comprehensive ML framework verification
    log_info "Performing final comprehensive ML framework verification..."

    python3 -c "
import sys
import numpy as np
import scipy
import sklearn
import torch
import tensorflow as tf

print('=== COMPREHENSIVE ML FRAMEWORK VERIFICATION ===')
print(f'Python: {sys.version}')
print(f'NumPy: {np.__version__}')
print(f'SciPy: {scipy.__version__}')
print(f'scikit-learn: {sklearn.__version__}')
print(f'PyTorch: {torch.__version__}')
print(f'TensorFlow: {tf.__version__}')

print('\\n=== COMPATIBILITY TEST ===')
# Test framework compatibility
np_array = np.array([1, 2, 3, 4, 5])
torch_tensor = torch.from_numpy(np_array)
tf_tensor = tf.constant(np_array)

print(f'NumPy array: {np_array}')
print(f'PyTorch tensor: {torch_tensor}')
print(f'TensorFlow tensor: {tf_tensor}')

print('\\n✓ All ML frameworks installed and compatible')
"

    log_info "Core ML frameworks installation completed successfully"
}

#=======================================================
#               COMPREHENSIVE AUDIO PROCESSING LIBRARIES
#=======================================================

install_audio_processing() {
    log_step 6 "Installing Comprehensive Audio Processing Libraries"

    log_info "Beginning comprehensive audio processing libraries installation..."

    # Install soundfile with comprehensive verification
    log_info "Installing soundfile with comprehensive verification..."
    echo -e "${BLUE}Running: Installing soundfile${NC}"

    local soundfile_version="soundfile>=0.12.1"
    if pip_install "$soundfile_version" "SoundFile"; then
        # Comprehensive soundfile verification
        python3 -c "
import soundfile as sf
import numpy as np

print(f'SoundFile version: {sf.__version__}')
print(f'SoundFile install path: {sf.__file__}')

# Test soundfile functionality
print('Available formats:')
for format_name, format_info in sf.available_formats().items():
    print(f'  {format_name}: {format_info}')

# Test basic I/O capability
test_data = np.sin(2 * np.pi * 440 * np.linspace(0, 1, 44100))
print(f'Test audio data shape: {test_data.shape}')
print('✓ SoundFile installation verified successfully')
"
        log_info "SoundFile installation and verification completed successfully"
    else
        fatal_error "SoundFile installation failed - this is critical for audio I/O"
    fi

    # Install audioread with verification
    log_info "Installing audioread with verification..."
    echo -e "${BLUE}Running: Installing audioread${NC}"

    local audioread_version="audioread>=3.0.0"
    if pip_install "$audioread_version" "AudioRead"; then
        # Verify audioread
        python3 -c "
import audioread
print(f'AudioRead version: {audioread.__version__}')
print(f'AudioRead install path: {audioread.__file__}')
print('✓ AudioRead installation verified successfully')
"
        log_info "AudioRead installation and verification completed successfully"
    else
        fatal_error "AudioRead installation failed - this is critical for audio format support"
    fi

    # Install librosa with comprehensive verification
    log_info "Installing librosa with comprehensive verification..."
    echo -e "${BLUE}Running: Installing librosa${NC}"

    local librosa_version="librosa>=0.10.0"
    if pip_install "$librosa_version" "Librosa"; then
        # Comprehensive librosa verification
        python3 -c "
import librosa
import numpy as np

print(f'Librosa version: {librosa.__version__}')
print(f'Librosa install path: {librosa.__file__}')

# Test basic librosa functionality
sr = 22050
duration = 1.0
t = np.linspace(0, duration, int(sr * duration))
test_signal = np.sin(2 * np.pi * 440 * t)

# Test spectral analysis
stft = librosa.stft(test_signal)
print(f'STFT shape: {stft.shape}')

# Test feature extraction
mfccs = librosa.feature.mfcc(y=test_signal, sr=sr, n_mfcc=13)
print(f'MFCCs shape: {mfccs.shape}')

print('✓ Librosa installation verified successfully')
"
        log_info "Librosa installation and verification completed successfully"
    else
        fatal_error "Librosa installation failed - this is critical for audio analysis"
    fi

    # Install pydub with verification
    log_info "Installing pydub with verification..."
    echo -e "${BLUE}Running: Installing pydub${NC}"

    local pydub_version="pydub>=0.25.1"
    if pip_install "$pydub_version" "PyDub"; then
        # Verify pydub
        python3 -c "
from pydub import AudioSegment
import os

print('PyDub installation path: pydub module loaded successfully')

# Test pydub functionality with silent audio
silent_audio = AudioSegment.silent(duration=1000)  # 1 second
print(f'Test silent audio duration: {len(silent_audio)}ms')
print(f'Test silent audio channels: {silent_audio.channels}')
print(f'Test silent audio frame rate: {silent_audio.frame_rate}')
print('✓ PyDub installation verified successfully')
"
        log_info "PyDub installation and verification completed successfully"
    else
        fatal_error "PyDub installation failed - this is critical for audio format handling"
    fi

    # Install resampy with verification
    log_info "Installing resampy with verification..."
    echo -e "${BLUE}Running: Installing resampy${NC}"

    local resampy_version="resampy>=0.4.0"
    if pip_install "$resampy_version" "Resampy"; then
        # Verify resampy
        python3 -c "
import resampy
import numpy as np

print(f'Resampy version: {resampy.__version__}')
print(f'Resampy install path: {resampy.__file__}')

# Test resampy functionality
sr_orig = 22050
sr_target = 16000
test_signal = np.sin(2 * np.pi * 440 * np.linspace(0, 1, sr_orig))
resampled = resampy.resample(test_signal, sr_orig, sr_target)
print(f'Original signal length: {len(test_signal)}')
print(f'Resampled signal length: {len(resampled)}')
print('✓ Resampy installation verified successfully')
"
        log_info "Resampy installation and verification completed successfully"
    else
        fatal_error "Resampy installation failed - this is critical for sample rate conversion"
    fi

    # Install audio evaluation libraries
    log_info "Installing audio evaluation libraries..."

    # Install PESQ
    echo -e "${BLUE}Running: Installing PESQ${NC}"
    if pip_install "pesq" "PESQ Audio Quality Metric"; then
        verify_python_package "pesq" || log_warn "PESQ verification failed"
        log_info "PESQ (Perceptual Evaluation of Speech Quality) installed successfully"
    else
        log_warn "PESQ installation failed - this is optional for quality evaluation"
    fi

    # Install PySTOI
    echo -e "${BLUE}Running: Installing PySTOI${NC}"
    if pip_install "pystoi" "PySTOI Audio Quality Metric"; then
        verify_python_package "pystoi" || log_warn "PySTOI verification failed"
        log_info "PySTOI (Short-Time Objective Intelligibility) installed successfully"
    else
        log_warn "PySTOI installation failed - this is optional for quality evaluation"
    fi

    # Final audio processing verification
    log_info "Performing final audio processing libraries verification..."

    python3 -c "
import soundfile as sf
import audioread
import librosa
import pydub
import resampy

print('=== COMPREHENSIVE AUDIO PROCESSING VERIFICATION ===')
print(f'SoundFile: {sf.__version__}')
print(f'AudioRead: {audioread.__version__}')
print(f'Librosa: {librosa.__version__}')
print('PyDub: Available')
print(f'Resampy: {resampy.__version__}')

# Test audio processing pipeline
import numpy as np
sr = 22050
test_audio = np.sin(2 * np.pi * 440 * np.linspace(0, 1, sr))

# Test librosa analysis
mfccs = librosa.feature.mfcc(y=test_audio, sr=sr)
spectral_centroid = librosa.feature.spectral_centroid(y=test_audio, sr=sr)

print(f'\\nTest Results:')
print(f'Audio signal shape: {test_audio.shape}')
print(f'MFCCs shape: {mfccs.shape}')
print(f'Spectral centroid shape: {spectral_centroid.shape}')

print('\\n✓ All audio processing libraries verified successfully')
"

    log_info "Audio processing libraries installation completed successfully"
}

#=======================================================
#               COMPREHENSIVE MUSIC PROCESSING LIBRARIES
#=======================================================

install_music_processing() {
    log_step 7 "Installing Comprehensive Music Processing Libraries"

    log_info "Beginning comprehensive music processing libraries installation..."

    # Install pretty-midi with comprehensive verification
    log_info "Installing pretty-midi with comprehensive verification..."
    echo -e "${BLUE}Running: Installing pretty-midi${NC}"

    local prettymidi_version="pretty-midi>=0.2.9"
    if pip_install "$prettymidi_version" "Pretty-MIDI"; then
        # Comprehensive pretty-midi verification
        python3 -c "
import pretty_midi
import numpy as np

print(f'Pretty-MIDI version: {pretty_midi.__version__}')
print(f'Pretty-MIDI install path: {pretty_midi.__file__}')

# Test pretty-midi functionality
pm = pretty_midi.PrettyMIDI()
instrument = pretty_midi.Instrument(program=1)  # Piano
note = pretty_midi.Note(velocity=100, pitch=60, start=0, end=1)
instrument.notes.append(note)
pm.instruments.append(instrument)

print(f'Test MIDI duration: {pm.get_end_time()}')
print(f'Test MIDI instruments: {len(pm.instruments)}')
print('✓ Pretty-MIDI installation verified successfully')
"
        log_info "Pretty-MIDI installation and verification completed successfully"
    else
        fatal_error "Pretty-MIDI installation failed - this is critical for MIDI processing"
    fi

    # Install music21 with comprehensive verification
    log_info "Installing music21 (latest version) with comprehensive verification..."
    echo -e "${BLUE}Running: Installing music21${NC}"

    local music21_version="music21>=9.1.0"
    if pip_install "$music21_version" "Music21"; then
        # Comprehensive music21 verification
        python3 -c "
import music21
from music21 import stream, note, pitch

print(f'Music21 version: {music21.__version__}')
print(f'Music21 install path: {music21.__file__}')

# Test music21 functionality
s = stream.Stream()
n1 = note.Note('C4')
n2 = note.Note('D4')
s.append(n1)
s.append(n2)

print(f'Test stream length: {len(s)}')
print(f'Test note pitch: {n1.pitch}')
print('✓ Music21 installation verified successfully')
"
        log_info "Music21 installation and verification completed successfully"
    else
        fatal_error "Music21 installation failed - this is critical for music analysis"
    fi

    # Install mido with verification
    log_info "Installing mido with verification..."
    echo -e "${BLUE}Running: Installing mido${NC}"

    local mido_version="mido>=1.3.0"
    if pip_install "$mido_version" "Mido"; then
        # Verify mido
        python3 -c "
import mido

print(f'Mido version: {mido.__version__}')
print(f'Mido install path: {mido.__file__}')

# Test mido functionality
msg = mido.Message('note_on', channel=0, note=60, velocity=64)
print(f'Test MIDI message: {msg}')
print('✓ Mido installation verified successfully')
"
        log_info "Mido installation and verification completed successfully"
    else
        fatal_error "Mido installation failed - this is critical for MIDI I/O"
    fi

    # Install demucs with verification
    log_info "Installing demucs with verification..."
    echo -e "${BLUE}Running: Installing demucs${NC}"

    if pip_install "demucs" "Demucs Audio Separation"; then
        # Verify demucs
        python3 -c "
import demucs
from demucs import pretrained

print(f'Demucs install path: {demucs.__file__}')
print('Available Demucs models:')
for model_name in pretrained.PRETRAINED_MODELS:
    print(f'  - {model_name}')
print('✓ Demucs installation verified successfully')
"
        log_info "Demucs installation and verification completed successfully"
    else
        fatal_error "Demucs installation failed - this is critical for audio separation"
    fi

    # Install Basic Pitch with comprehensive compatibility handling
    log_info "Installing Basic Pitch with comprehensive compatibility handling..."

    # Install mir_eval first as a critical prerequisite
    log_info "Installing mir_eval as Basic Pitch prerequisite..."
    echo -e "${BLUE}Running: Installing mir_eval${NC}"
    if pip_install "mir_eval>=0.6" "MIR Eval"; then
        # Verify mir_eval
        python3 -c "
import mir_eval
print(f'MIR Eval version: {mir_eval.__version__}')
print(f'MIR Eval install path: {mir_eval.__file__}')
print('✓ MIR Eval installation verified successfully')
"
        log_info "MIR Eval installation and verification completed successfully"
    else
        fatal_error "MIR Eval installation failed - this is required for Basic Pitch"
    fi

    # Handle resampy version conflict for Basic Pitch compatibility
    log_info "Adjusting resampy version for Basic Pitch compatibility..."
    echo -e "${BLUE}Running: Adjusting resampy version${NC}"
    if python3 -m pip install "resampy<0.4.3,>=0.2.2" --force-reinstall; then
        # Verify resampy adjustment
        python3 -c "
import resampy
print(f'Resampy version after adjustment: {resampy.__version__}')
print('✓ Resampy version adjustment completed successfully')
"
        log_info "Resampy version adjusted for Basic Pitch compatibility"
    else
        log_warn "Resampy version adjustment failed - Basic Pitch may have compatibility issues"
    fi

    # Attempt Basic Pitch installation with multiple strategies
    log_info "Attempting Basic Pitch installation with multiple strategies..."

    # Strategy 1: Normal installation
    echo -e "${BLUE}Running: Installing Basic Pitch (normal method)${NC}"
    if pip_install "basic-pitch" "Basic Pitch"; then
        # Verify Basic Pitch installation
        python3 -c "
import basic_pitch
from basic_pitch.inference import predict
print('Basic Pitch import successful')
print(f'Basic Pitch install path: {basic_pitch.__file__}')
print('✓ Basic Pitch installation verified successfully')
"
        log_info "Basic Pitch installed successfully using normal method"
    else
        log_warn "Basic Pitch normal installation failed, trying alternative approach..."

        # Strategy 2: Install with --no-deps and handle dependencies manually
        echo -e "${BLUE}Running: Installing Basic Pitch with --no-deps${NC}"
        if python3 -m pip install basic-pitch --no-deps; then
            log_info "Basic Pitch installed with --no-deps method"

            # Verify basic import capability
            python3 -c "
try:
    import basic_pitch
    print('Basic Pitch --no-deps installation successful')
    print(f'Basic Pitch install path: {basic_pitch.__file__}')
    print('✓ Basic Pitch --no-deps installation verified')
except ImportError as e:
    print(f'Basic Pitch --no-deps import failed: {e}')
    raise
"
        else
            fatal_error "All Basic Pitch installation strategies failed"
        fi
    fi

    # Final comprehensive music processing verification
    log_info "Performing final comprehensive music processing verification..."

    python3 -c "
import pretty_midi
import music21
import mido
import demucs
import basic_pitch
import mir_eval

print('=== COMPREHENSIVE MUSIC PROCESSING VERIFICATION ===')
print(f'Pretty-MIDI: {pretty_midi.__version__}')
print(f'Music21: {music21.__version__}')
print(f'Mido: {mido.__version__}')
print('Demucs: Available')
print('Basic Pitch: Available')
print(f'MIR Eval: {mir_eval.__version__}')

# Test music processing pipeline
import numpy as np

# Test MIDI creation
pm = pretty_midi.PrettyMIDI()
instrument = pretty_midi.Instrument(program=1)
note = pretty_midi.Note(velocity=100, pitch=60, start=0, end=1)
instrument.notes.append(note)
pm.instruments.append(instrument)

# Test music21
s = music21.stream.Stream()
n = music21.note.Note('C4')
s.append(n)

# Test mido
msg = mido.Message('note_on', note=60, velocity=64)

print(f'\\nTest Results:')
print(f'MIDI file duration: {pm.get_end_time()}s')
print(f'Music21 stream length: {len(s)}')
print(f'Mido message: {msg}')

print('\\n✓ All music processing libraries verified successfully')
"

    log_info "Music processing libraries installation completed successfully"
}

#=======================================================
#               COMPREHENSIVE WEB FRAMEWORKS INSTALLATION
#=======================================================

install_web_frameworks() {
    log_step 8 "Installing Comprehensive Web Frameworks"

    log_info "Beginning comprehensive web frameworks installation..."

    # Install FastAPI with comprehensive verification
    log_info "Installing FastAPI with comprehensive verification..."
    echo -e "${BLUE}Running: Installing FastAPI${NC}"

    local fastapi_version="fastapi>=0.104.0"
    if pip_install "$fastapi_version" "FastAPI"; then
        # Comprehensive FastAPI verification
        python3 -c "
import fastapi
from fastapi import FastAPI

print(f'FastAPI version: {fastapi.__version__}')
print(f'FastAPI install path: {fastapi.__file__}')

# Test FastAPI app creation
app = FastAPI(title='Test App')
print('FastAPI app creation test: SUCCESS')
print('✓ FastAPI installation verified successfully')
"
        log_info "FastAPI installation and verification completed successfully"
    else
        fatal_error "FastAPI installation failed - this is critical for web API"
    fi

    # Install Uvicorn with standard extras and verification
    log_info "Installing Uvicorn with standard extras and verification..."
    echo -e "${BLUE}Running: Installing Uvicorn[standard]${NC}"

    local uvicorn_version="uvicorn[standard]>=0.24.0"
    if pip_install "$uvicorn_version" "Uvicorn with Standard Extras"; then
        # Comprehensive Uvicorn verification
        python3 -c "
import uvicorn
print(f'Uvicorn version: {uvicorn.__version__}')
print(f'Uvicorn install path: {uvicorn.__file__}')

# Check for standard extras
try:
    import uvloop
    print('✓ Uvloop available')
except ImportError:
    print('⚠ Uvloop not available')

try:
    import httptools
    print('✓ HTTPTools available')
except ImportError:
    print('⚠ HTTPTools not available')

try:
    import watchfiles
    print('✓ Watchfiles available')
except ImportError:
    print('⚠ Watchfiles not available')

print('✓ Uvicorn installation verified successfully')
"
        log_info "Uvicorn installation and verification completed successfully"
    else
        fatal_error "Uvicorn installation failed - this is critical for web server"
    fi

    # Install comprehensive web dependencies
    log_info "Installing comprehensive web dependencies..."

    # Python-multipart for file uploads
    log_info "Installing python-multipart for file upload support..."
    echo -e "${BLUE}Running: Installing python-multipart${NC}"
    if pip_install "python-multipart>=0.0.6" "Python Multipart"; then
        verify_python_package "multipart" || log_warn "Python-multipart verification failed"
        log_info "Python-multipart installed successfully"
    else
        fatal_error "Python-multipart installation failed - required for file uploads"
    fi

    # Jinja2 for templating
    log_info "Installing Jinja2 for templating support..."
    echo -e "${BLUE}Running: Installing Jinja2${NC}"
    if pip_install "jinja2>=3.1.0" "Jinja2"; then
        python3 -c "
import jinja2
print(f'Jinja2 version: {jinja2.__version__}')
print('✓ Jinja2 verification successful')
"
        log_info "Jinja2 installed and verified successfully"
    else
        fatal_error "Jinja2 installation failed - required for templating"
    fi

    # Aiofiles for async file operations
    log_info "Installing aiofiles for async file operations..."
    echo -e "${BLUE}Running: Installing aiofiles${NC}"
    if pip_install "aiofiles>=23.1.0" "Aiofiles"; then
        verify_python_package "aiofiles" || log_warn "Aiofiles verification failed"
        log_info "Aiofiles installed successfully"
    else
        fatal_error "Aiofiles installation failed - required for async file handling"
    fi

    # Python-magic for file type detection
    log_info "Installing python-magic for file type detection..."
    echo -e "${BLUE}Running: Installing python-magic${NC}"
    if pip_install "python-magic>=0.4.27" "Python Magic"; then
        verify_python_package "magic" || log_warn "Python-magic verification failed"
        log_info "Python-magic installed successfully"
    else
        log_warn "Python-magic installation failed - file type detection may be limited"
    fi

    # Install comprehensive Pydantic support
    log_info "Installing comprehensive Pydantic support..."

    # Pydantic core
    echo -e "${BLUE}Running: Installing pydantic${NC}"
    if pip_install "pydantic>=2.4.0" "Pydantic"; then
        python3 -c "
import pydantic
from pydantic import BaseModel

print(f'Pydantic version: {pydantic.__version__}')
print('✓ Pydantic verification successful')

# Test basic pydantic functionality
class TestModel(BaseModel):
    name: str
    value: int

test = TestModel(name='test', value=42)
print(f'Pydantic test model: {test}')
"
        log_info "Pydantic installed and verified successfully"
    else
        fatal_error "Pydantic installation failed - required for data validation"
    fi

    # Pydantic settings
    echo -e "${BLUE}Running: Installing pydantic-settings${NC}"
    if pip_install "pydantic-settings>=2.0.0" "Pydantic Settings"; then
        python3 -c "
import pydantic_settings
from pydantic_settings import BaseSettings

print('Pydantic Settings available')
print('✓ Pydantic Settings verification successful')
"
        log_info "Pydantic Settings installed and verified successfully"
    else
        fatal_error "Pydantic Settings installation failed - required for configuration"
    fi

    # Install task queue components
    log_info "Installing task queue components..."

    # Celery with Redis support
    echo -e "${BLUE}Running: Installing Celery[redis]${NC}"
    if pip_install "celery[redis]>=5.3.0" "Celery with Redis"; then
        python3 -c "
import celery
from celery import Celery

print(f'Celery version: {celery.__version__}')
print('✓ Celery verification successful')

# Test basic celery functionality
app = Celery('test')
print('Celery app creation test: SUCCESS')
"
        log_info "Celery installed and verified successfully"
    else
        fatal_error "Celery installation failed - required for background tasks"
    fi

    # Redis Python client
    echo -e "${BLUE}Running: Installing redis-py${NC}"
    if pip_install "redis>=5.0.0" "Redis Python Client"; then
        python3 -c "
import redis

print(f'Redis-py version: {redis.__version__}')
print('✓ Redis-py verification successful')
"
        log_info "Redis Python client installed and verified successfully"
    else
        fatal_error "Redis Python client installation failed - required for task queue"
    fi

    # Install additional utility packages
    log_info "Installing additional utility packages..."

    local utility_packages=(
        "requests>=2.31.0:Requests HTTP Library"
        "python-dotenv>=1.0.0:Python Dotenv"
        "click>=8.1.0:Click CLI Framework"
        "tqdm>=4.65.0:Progress Bars"
        "psutil>=5.9.0:System Utilities"
        "matplotlib>=3.7.0:Plotting Library"
        "pillow>=10.0.0:Image Processing"
    )

    for package_info in "${utility_packages[@]}"; do
        IFS=':' read -r package description <<< "$package_info"
        log_info "Installing $description..."
        echo -e "${BLUE}Running: Installing $description${NC}"
        if pip_install "$package" "$description"; then
            log_info "$description installed successfully"
        else
            log_warn "$description installation failed"
        fi
    done

    # Final comprehensive web frameworks verification
    log_info "Performing final comprehensive web frameworks verification..."

    python3 -c "
import fastapi
import uvicorn
import multipart
import jinja2
import aiofiles
import pydantic
import pydantic_settings
import celery
import redis
import requests
import click
import tqdm
import psutil
import matplotlib
import PIL

print('=== COMPREHENSIVE WEB FRAMEWORKS VERIFICATION ===')
print(f'FastAPI: {fastapi.__version__}')
print(f'Uvicorn: {uvicorn.__version__}')
print('Python-multipart: Available')
print(f'Jinja2: {jinja2.__version__}')
print('Aiofiles: Available')
print(f'Pydantic: {pydantic.__version__}')
print('Pydantic Settings: Available')
print(f'Celery: {celery.__version__}')
print(f'Redis-py: {redis.__version__}')
print(f'Requests: {requests.__version__}')
print(f'Click: {click.__version__}')
print(f'TQDM: {tqdm.__version__}')
print(f'PSUtil: {psutil.__version__}')
print(f'Matplotlib: {matplotlib.__version__}')
print(f'Pillow: {PIL.__version__}')

# Test web framework integration
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title='Integration Test')

class TestModel(BaseModel):
    name: str

@app.get('/')
def test_endpoint():
    return {'message': 'test'}

print('\\nIntegration test: FastAPI + Pydantic SUCCESS')
print('\\n✓ All web frameworks verified successfully')
"

    log_info "Web frameworks installation completed successfully"
}

#=======================================================
#               COMPREHENSIVE REDIS SETUP
#=======================================================

setup_redis() {
    log_step 9 "Comprehensive Redis Setup and Configuration"

    log_info "Beginning comprehensive Redis setup..."

    # Create comprehensive Redis configuration
    log_info "Creating comprehensive Redis configuration..."

    cat > "$CONFIG_DIR/redis.conf" << 'EOF'
# Redis configuration for M3 Enhanced - Production Ready
# Generated by M3 Enhanced setup script

# Network Configuration
bind 0.0.0.0
port 6379
tcp-backlog 511
tcp-keepalive 300
timeout 0

# General Configuration
daemonize no
supervised no
pidfile /var/run/redis_6379.pid
loglevel notice
logfile ""
databases 16

# Security
protected-mode no
# requirepass your_secure_password_here

# Memory Management
maxmemory 512mb
maxmemory-policy allkeys-lru
maxmemory-samples 5

# Persistence - RDB Snapshots
save 900 1
save 300 10
save 60 10000
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
dir ./

# Persistence - AOF (Append Only File)
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec
no-appendfsync-on-rewrite no
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb
aof-load-truncated yes
aof-use-rdb-preamble yes

# Slow Log
slowlog-log-slower-than 10000
slowlog-max-len 128

# Latency Monitoring
latency-monitor-threshold 100

# Client Management
client-output-buffer-limit normal 0 0 0
client-output-buffer-limit replica 256mb 64mb 60
client-output-buffer-limit pubsub 32mb 8mb 60
client-query-buffer-limit 1gb

# Advanced Configuration
hash-max-ziplist-entries 512
hash-max-ziplist-value 64
list-max-ziplist-size -2
list-compress-depth 0
set-max-intset-entries 512
zset-max-ziplist-entries 128
zset-max-ziplist-value 64
hll-sparse-max-bytes 3000
stream-node-max-bytes 4096
stream-node-max-entries 100
activerehashing yes
hz 10
dynamic-hz yes
EOF

    log_info "Redis configuration file created successfully"

    # Comprehensive Redis service management
    log_info "Setting up comprehensive Redis service management..."

    # Stop any existing Redis instances with detailed cleanup
    log_info "Stopping any existing Redis instances..."

    # Stop systemd service
    if systemctl is-active --quiet redis-server; then
        log_info "Stopping Redis systemd service..."
        systemctl stop redis-server || log_warn "Failed to stop Redis systemd service"
    fi

    if systemctl is-active --quiet redis; then
        log_info "Stopping Redis systemd service (alternative name)..."
        systemctl stop redis || log_warn "Failed to stop Redis service"
    fi

    # Kill any remaining Redis processes
    log_info "Terminating any remaining Redis processes..."
    pkill -f redis-server 2>/dev/null || true
    sleep 2
    pkill -9 -f redis-server 2>/dev/null || true

    # Clean up Redis data files if needed
    log_info "Cleaning up Redis data files..."
    rm -f /var/lib/redis/dump.rdb 2>/dev/null || true
    rm -f "$WORK_DIR/dump.rdb" 2>/dev/null || true
    rm -f "$WORK_DIR/appendonly.aof" 2>/dev/null || true

    # Start Redis with comprehensive error handling
    log_info "Starting Redis server with comprehensive error handling..."

    # Attempt 1: Start with systemctl
    if systemctl start redis-server 2>/dev/null; then
        log_info "Redis started successfully using systemctl"
        sleep 3
    else
        log_warn "Systemctl start failed, attempting manual start..."

        # Attempt 2: Manual start with custom configuration
        log_info "Starting Redis manually with custom configuration..."
        redis-server "$CONFIG_DIR/redis.conf" &
        REDIS_PID=$!
        echo $REDIS_PID > /tmp/redis.pid
        sleep 5

        # Verify manual start
        if kill -0 $REDIS_PID 2>/dev/null; then
            log_info "Redis started successfully manually (PID: $REDIS_PID)"
        else
            log_warn "Manual Redis start failed, trying default configuration..."

            # Attempt 3: Start with default settings
            redis-server --daemonize yes --port 6379 --bind 0.0.0.0 &
            sleep 3
        fi
    fi

    # Comprehensive Redis connection testing
    log_info "Performing comprehensive Redis connection testing..."

    local redis_test_result=0
    local connection_attempts=0
    local max_connection_attempts=15

    while [ $connection_attempts -lt $max_connection_attempts ]; do
        connection_attempts=$((connection_attempts + 1))
        log_info "Redis connection test attempt $connection_attempts..."

        if redis-cli ping >/dev/null 2>&1; then
            redis_test_result=1
            log_info "Redis connection test successful on attempt $connection_attempts"
            break
        else
            log_warn "Redis connection attempt $connection_attempts failed"
            if [ $connection_attempts -lt $max_connection_attempts ]; then
                log_info "Waiting 2 seconds before next attempt..."
                sleep 2
            fi
        fi
    done

    if [ "$redis_test_result" -eq 1 ]; then
        log_info "Redis connection established successfully"

        # Comprehensive Redis functionality testing
        log_info "Performing Redis functionality tests..."

        # Test basic operations
        redis-cli set test_key "test_value" >/dev/null
        local get_result=$(redis-cli get test_key)
        redis-cli del test_key >/dev/null

        if [ "$get_result" = "test_value" ]; then
            log_info "Redis basic operations test: PASSED"
        else
            log_warn "Redis basic operations test: FAILED"
        fi

        # Test Redis info
        local redis_info=$(redis-cli info server 2>/dev/null | head -10)
        log_info "Redis server information:"
        echo "$redis_info"

        # Test Redis configuration
        local redis_version=$(redis-cli info server | grep redis_version | cut -d: -f2 | tr -d '\r')
        log_info "Redis version: $redis_version"

        log_info "Redis setup and verification completed successfully"
    else
        fatal_error "Redis failed to start or accept connections after $max_connection_attempts attempts"
    fi
}

#=======================================================
#               COMPREHENSIVE MODEL DOWNLOADS
#=======================================================

download_models() {
    log_step 10 "Comprehensive AI Model Downloads and Verification"

    log_info "Beginning comprehensive AI model downloads..."

    # Download and verify Demucs model with comprehensive error handling
    log_info "Downloading and verifying Demucs model with comprehensive handling..."

    python3 -c "
import os
import torch
import torchaudio
from demucs import pretrained

print('Starting Demucs model download...')
try:
    # Download htdemucs model (default high-quality model)
    model = pretrained.get_model('htdemucs')
    print('✓ Demucs htdemucs model downloaded successfully')

    # Verify model functionality
    print('Verifying Demucs model functionality...')
    device = 'cpu'  # Use CPU for compatibility
    model = model.to(device)
    model.eval()

    # Test with dummy audio
    dummy_audio = torch.randn(1, 2, 44100)  # 1 second stereo audio
    with torch.no_grad():
        separated = model(dummy_audio)

    print(f'Demucs separation test - Input shape: {dummy_audio.shape}')
    print(f'Demucs separation test - Output shape: {separated.shape}')
    print('✓ Demucs model functionality verified successfully')

except Exception as e:
    print(f'❌ Demucs model download/verification failed: {e}')
    import traceback
    traceback.print_exc()
    raise
"

    if [ $? -eq 0 ]; then
        log_info "Demucs model download and verification completed successfully"
    else
        fatal_error "Demucs model download or verification failed"
    fi

    # Test and verify Basic Pitch availability with comprehensive checks
    log_info "Testing and verifying Basic Pitch availability with comprehensive checks..."

    python3 -c "
import numpy as np

print('Testing Basic Pitch availability and functionality...')
try:
    import basic_pitch
    from basic_pitch.inference import predict
    from basic_pitch import ICASSP_2022_MODEL_PATH

    print('✓ Basic Pitch import successful')
    print(f'Basic Pitch model path: {ICASSP_2022_MODEL_PATH}')

    # Test Basic Pitch functionality with dummy audio
    print('Testing Basic Pitch prediction functionality...')

    # Create dummy audio (1 second at 22050 Hz)
    sample_rate = 22050
    duration = 1.0
    dummy_audio = np.sin(2 * np.pi * 440 * np.linspace(0, duration, int(sample_rate * duration)))

    # Test prediction (this will also trigger model download if needed)
    model_output, midi_data, note_events = predict(dummy_audio)

    print(f'Basic Pitch test - Audio shape: {dummy_audio.shape}')
    print(f'Basic Pitch test - Model output shape: {model_output.shape}')
    print(f'Basic Pitch test - MIDI data type: {type(midi_data)}')
    print(f'Basic Pitch test - Note events shape: {note_events.shape}')
    print('✓ Basic Pitch functionality verified successfully')

except Exception as e:
    print(f'❌ Basic Pitch test failed: {e}')
    import traceback
    traceback.print_exc()
    raise
"

    if [ $? -eq 0 ]; then
        log_info "Basic Pitch availability and functionality verified successfully"
    else
        fatal_error "Basic Pitch verification failed"
    fi

    # Verify model storage and accessibility
    log_info "Verifying model storage and accessibility..."

    # Check model directories and sizes
    python3 -c "
import os
import torch
from pathlib import Path

print('Checking model storage locations...')

# Check PyTorch model cache
torch_cache = Path(torch.hub.get_dir())
print(f'PyTorch cache directory: {torch_cache}')
if torch_cache.exists():
    cache_size = sum(f.stat().st_size for f in torch_cache.rglob('*') if f.is_file())
    print(f'PyTorch cache size: {cache_size / (1024*1024):.1f} MB')

# Check for downloaded models
model_files = list(torch_cache.rglob('*.th')) if torch_cache.exists() else []
if model_files:
    print('Downloaded model files:')
    for model_file in model_files:
        size_mb = model_file.stat().st_size / (1024*1024)
        print(f'  {model_file.name}: {size_mb:.1f} MB')
else:
    print('No .th model files found in cache')

print('✓ Model storage verification completed')
"

    log_info "Model downloads and verification completed successfully"
}

#=======================================================
#               COMPREHENSIVE ENVIRONMENT CONFIGURATION
#=======================================================

configure_environment() {
    log_step 11 "Comprehensive Environment Configuration"

    log_info "Creating comprehensive environment configuration..."

    # Comprehensive system capability detection
    log_info "Performing comprehensive system capability detection..."

    local gpu_available="false"
    local gpu_name="None"
    local gpu_memory="0"
    local device="cpu"
    local workers=2
    local batch_size=2

    # Comprehensive GPU detection
    if command -v nvidia-smi >/dev/null 2>&1; then
        log_info "NVIDIA tools detected, checking GPU availability..."

        if nvidia-smi >/dev/null 2>&1; then
            gpu_available="true"
            device="cuda"
            workers=4
            batch_size=8

            # Get GPU details
            gpu_name=$(nvidia-smi --query-gpu=gpu_name --format=csv,noheader,nounits | head -1)
            gpu_memory=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)

            log_info "GPU detected: $gpu_name"
            log_info "GPU memory: ${gpu_memory}MB"
            log_info "CUDA acceleration enabled"
        else
            log_info "NVIDIA tools present but no functional GPU detected"
        fi
    else
        log_info "No NVIDIA tools detected - using CPU mode"
    fi

    # Detect optimal worker count based on system resources
    local cpu_cores=$(nproc)
    local ram_gb=$(free -g | awk 'NR==2{print $2}')

    # Adjust workers based on available resources
    if [ "$gpu_available" = "false" ]; then
        # CPU mode - adjust based on cores and RAM
        if [ "$cpu_cores" -ge 8 ] && [ "$ram_gb" -ge 16 ]; then
            workers=4
        elif [ "$cpu_cores" -ge 4 ] && [ "$ram_gb" -ge 8 ]; then
            workers=2
        else
            workers=1
        fi
    fi

    log_info "Detected system configuration:"
    log_info "  CPU Cores: $cpu_cores"
    log_info "  RAM: ${ram_gb}GB"
    log_info "  GPU Available: $gpu_available"
    log_info "  Optimal Workers: $workers"
    log_info "  Batch Size: $batch_size"

    # Create comprehensive .env configuration file
    log_info "Creating comprehensive .env configuration file..."

    cat > "$WORK_DIR/.env" << EOF
# M3 Enhanced Configuration - Production Ready
# Generated by M3 Enhanced setup script v${SCRIPT_VERSION}

# System Information
SETUP_VERSION=$SCRIPT_VERSION
SETUP_DATE=$(date -u +"%Y-%m-%d %H:%M:%S UTC")

# Database and Cache Configuration
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=
REDIS_DB=0

# Directory Configuration
BASE_DIR=$WORK_DIR
MODELS_DIR=$MODELS_DIR
TEMP_DIR=$TEMP_DIR
UPLOADS_DIR=$UPLOADS_DIR
RESULTS_DIR=$RESULTS_DIR
CONFIG_DIR=$CONFIG_DIR
LOG_DIR=$LOG_DIR

# Processing Configuration
MAX_WORKERS=$workers
GPU_ENABLED=$gpu_available
GPU_NAME=$gpu_name
GPU_MEMORY=$gpu_memory
DEVICE=$device
BATCH_SIZE=$batch_size
CPU_CORES=$cpu_cores
RAM_GB=$ram_gb

# API Server Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=1
DEBUG=false
RELOAD=false

# Model Configuration
DEFAULT_SEPARATOR=demucs
DEFAULT_TRANSCRIBER=basic_pitch
ENABLE_CLASSIFICATION=true
ENABLE_QUALITY_ANALYSIS=true
ENABLE_TABLATURE_GENERATION=true

# Audio Processing Settings
AUDIO_SAMPLE_RATE=48000
AUDIO_BIT_DEPTH=24
MAX_AUDIO_DURATION=600
MAX_FILE_SIZE_MB=100

# Quality Thresholds
MIN_SDR_THRESHOLD=10.0
MIN_SIR_THRESHOLD=15.0
MIN_SAR_THRESHOLD=10.0

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=detailed
LOG_TO_FILE=true

# Security Settings (adjust for production)
CORS_ORIGINS=["*"]
CORS_METHODS=["*"]
CORS_HEADERS=["*"]
CORS_CREDENTIALS=true

# Feature Flags
ENABLE_EXPERIMENTAL_FEATURES=false
ENABLE_PERFORMANCE_MONITORING=true
ENABLE_DETAILED_LOGGING=true

# Timeouts and Limits
REQUEST_TIMEOUT=300
UPLOAD_TIMEOUT=120
PROCESSING_TIMEOUT=3600
CLEANUP_INTERVAL=86400

# File Management
AUTO_CLEANUP_ENABLED=true
CLEANUP_AFTER_DAYS=7
MAX_CONCURRENT_UPLOADS=5
MAX_CONCURRENT_JOBS=$workers
EOF

    log_info "Environment configuration file created successfully"

    # Verify configuration file
    log_info "Verifying environment configuration..."

    if [ -f "$WORK_DIR/.env" ]; then
        local env_size=$(wc -l < "$WORK_DIR/.env")
        log_info "Environment file created with $env_size configuration lines"

        # Test environment loading
        if source "$WORK_DIR/.env" 2>/dev/null; then
            log_info "Environment configuration loads successfully"
        else
            log_warn "Environment configuration has syntax issues"
        fi
    else
        fatal_error "Failed to create environment configuration file"
    fi

    log_info "Environment configuration completed successfully"
}

#=======================================================
#               COMPREHENSIVE SERVICE SCRIPTS CREATION
#=======================================================

create_service_scripts() {
    log_step 12 "Creating Comprehensive Service Management Scripts"

    log_info "Creating comprehensive service management scripts..."

    # Create comprehensive start script
    log_info "Creating comprehensive start script..."

    cat > "$WORK_DIR/start.sh" << 'EOF'
#!/bin/bash
set -e

#=======================================================
#         M3 Enhanced - Comprehensive Start Script
#=======================================================

WORK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$WORK_DIR"

echo "🚀 Starting M3 Enhanced services..."
echo "Working directory: $WORK_DIR"

# Load environment configuration
if [ -f ".env" ]; then
    echo "📋 Loading environment configuration..."
    export $(cat .env | grep -v '^#' | grep -v '^\s*$' | xargs)
    echo "✓ Environment configuration loaded"
else
    echo "⚠️  Warning: .env file not found, using defaults"
fi

# Verify critical directories
echo "📁 Verifying directory structure..."
required_dirs=("backend/app" "frontend/static" "logs" "uploads" "results" "temp" "models")
for dir in "${required_dirs[@]}"; do
    if [ -d "$dir" ]; then
        echo "✓ Directory exists: $dir"
    else
        echo "❌ Missing directory: $dir"
        mkdir -p "$dir" 2>/dev/null || echo "⚠️  Could not create directory: $dir"
    fi
done

# Verify critical files
echo "📄 Verifying critical files..."
critical_files=("backend/app/main.py" "frontend/static/index.html")
for file in "${critical_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✓ File exists: $file"
    else
        echo "❌ Missing critical file: $file"
        echo "Setup may be incomplete or corrupted"
        exit 1
    fi
done

# Redis service management with comprehensive checks
echo "🔴 Managing Redis service..."
redis_running=false

# Check if Redis is already running
if redis-cli ping >/dev/null 2>&1; then
    echo "✓ Redis is already running"
    redis_running=true
else
    echo "⚙️  Starting Redis server..."

    # Try systemctl first
    if systemctl start redis-server 2>/dev/null; then
        echo "✓ Redis started via systemctl"
        sleep 3
    elif [ -f "config/redis.conf" ]; then
        echo "⚙️  Starting Redis with custom configuration..."
        redis-server config/redis.conf &
        sleep 3
    else
        echo "⚙️  Starting Redis with default configuration..."
        redis-server --daemonize yes --port 6379 --bind 0.0.0.0 &
        sleep 3
    fi

    # Verify Redis startup
    local attempts=0
    while [ $attempts -lt 10 ]; do
        if redis-cli ping >/dev/null 2>&1; then
            echo "✓ Redis connection established"
            redis_running=true
            break
        fi
        attempts=$((attempts + 1))
        echo "⏳ Waiting for Redis... (attempt $attempts)"
        sleep 2
    done
fi

if [ "$redis_running" = "true" ]; then
    # Test Redis functionality
    redis_version=$(redis-cli info server | grep redis_version | cut -d: -f2 | tr -d '\r' 2>/dev/null || echo "unknown")
    echo "✓ Redis version: $redis_version"

    # Test basic operations
    if redis-cli set test_startup "success" >/dev/null 2>&1 && \
       [ "$(redis-cli get test_startup 2>/dev/null)" = "success" ]; then
        redis-cli del test_startup >/dev/null 2>&1
        echo "✓ Redis functionality test passed"
    else
        echo "⚠️  Redis functionality test failed"
    fi
else
    echo "⚠️  Redis failed to start - continuing without task queue"
fi

# Python environment setup
echo "🐍 Setting up Python environment..."
export PYTHONPATH="$WORK_DIR:$WORK_DIR/backend"
export PYTHONUNBUFFERED=1

echo "✓ Python path configured: $PYTHONPATH"

# Verify Python dependencies
echo "📦 Verifying Python dependencies..."
python3 -c "
import sys
critical_modules = [
    'fastapi', 'uvicorn', 'numpy', 'torch',
    'librosa', 'demucs', 'basic_pitch'
]

missing_modules = []
for module in critical_modules:
    try:
        __import__(module)
        print(f'✓ {module}')
    except ImportError:
        missing_modules.append(module)
        print(f'❌ {module}')

if missing_modules:
    print(f'Missing critical modules: {missing_modules}')
    sys.exit(1)
else:
    print('✓ All critical Python modules available')
" || {
    echo "❌ Critical Python dependencies missing"
    echo "Please run setup.sh again to install dependencies"
    exit 1
}

# Start Celery worker if configured
if [ -f "backend/app/celery_app.py" ] && [ "$redis_running" = "true" ]; then
    echo "👷 Starting Celery worker..."
    cd backend
    celery -A app.celery_app worker --loglevel=info --pidfile=/tmp/celery.pid --detach 2>/dev/null && \
        echo "✓ Celery worker started" || echo "⚠️  Celery worker failed to start"
    cd ..
else
    echo "ℹ️  Celery worker not configured or Redis unavailable"
fi

# Start FastAPI server
echo "🌐 Starting M3 Enhanced API server..."

# Verify FastAPI application exists
if [ ! -f "backend/app/main.py" ]; then
    echo "❌ FastAPI application not found at backend/app/main.py"
    echo "Please ensure the repository structure is correct"
    exit 1
fi

# Start API server with comprehensive configuration
echo "⚙️  Starting FastAPI server..."
python3 -m uvicorn app.main:app \
    --host ${API_HOST:-0.0.0.0} \
    --port ${API_PORT:-8000} \
    --app-dir backend \
    --access-log \
    --log-level info &

API_PID=$!
echo $API_PID > /tmp/api.pid

# Wait for API server startup
echo "⏳ Waiting for API server to start..."
sleep 8

# Verify API server startup
if kill -0 "$API_PID" 2>/dev/null; then
    echo "✓ API server started successfully (PID: $API_PID)"

    # Test API health endpoint
    local health_attempts=0
    local health_success=false

    while [ $health_attempts -lt 10 ]; do
        health_attempts=$((health_attempts + 1))
        echo "🏥 Testing API health... (attempt $health_attempts)"

        if curl -s http://localhost:${API_PORT:-8000}/health >/dev/null 2>&1; then
            health_success=true
            echo "✓ API health check passed"
            break
        fi

        sleep 2
    done

    if [ "$health_success" = "false" ]; then
        echo "⚠️  API health check failed - server may still be starting"
    fi

    # Display comprehensive startup summary
    echo ""
    echo "🎉 M3 Enhanced started successfully!"
    echo ""
    echo "🌐 ACCESS POINTS:"
    echo "   • Web Interface: http://localhost:${API_PORT:-8000}"
    echo "   • API Documentation: http://localhost:${API_PORT:-8000}/docs"
    echo "   • Interactive API: http://localhost:${API_PORT:-8000}/redoc"
    echo "   • Health Check: http://localhost:${API_PORT:-8000}/health"
    echo ""
    echo "📁 FRONTEND FILES:"
    echo "   • Main Page: frontend/static/index.html"
    echo "   • Styles: frontend/static/style.css"
    echo "   • JavaScript: frontend/static/app.js"
    echo ""
    echo "🛠️  MANAGEMENT COMMANDS:"
    echo "   • Check Status: ./status.sh"
    echo "   • Stop Services: ./stop.sh"
    echo "   • View Logs: tail -f logs/*.log"
    echo ""
    echo "⚙️  SYSTEM CONFIGURATION:"
    echo "   • Device: ${DEVICE:-cpu}"
    echo "   • Workers: ${MAX_WORKERS:-2}"
    echo "   • GPU Enabled: ${GPU_ENABLED:-false}"
    echo "   • Redis: $([[ $redis_running == true ]] && echo 'Connected' || echo 'Unavailable')"
    echo ""
    echo "🧪 QUICK TEST:"
    echo "   curl http://localhost:${API_PORT:-8000}/health"
    echo ""

    # Final health check with output
    if [ "$health_success" = "true" ]; then
        echo "📊 API HEALTH STATUS:"
        curl -s http://localhost:${API_PORT:-8000}/health | python3 -m json.tool 2>/dev/null || \
            echo "Health endpoint available but response not JSON formatted"
    fi

else
    echo "❌ API server failed to start"
    rm -f /tmp/api.pid

    # Show error information
    echo ""
    echo "🔍 TROUBLESHOOTING:"
    echo "   • Check Python dependencies: python3 -c 'import fastapi, uvicorn'"
    echo "   • Check file permissions: ls -la backend/app/main.py"
    echo "   • Check logs: tail logs/*.log"
    echo "   • Verify environment: cat .env"

    exit 1
fi
EOF

    chmod +x "$WORK_DIR/start.sh"
    log_info "Comprehensive start script created successfully"

    # Create comprehensive stop script
    log_info "Creating comprehensive stop script..."

    cat > "$WORK_DIR/stop.sh" << 'EOF'
#!/bin/bash

#=======================================================
#         M3 Enhanced - Comprehensive Stop Script
#=======================================================

echo "🛑 Stopping M3 Enhanced services..."

# Stop API server
if [ -f /tmp/api.pid ]; then
    API_PID=$(cat /tmp/api.pid)
    if kill -0 "$API_PID" 2>/dev/null; then
        echo "🌐 Stopping API server (PID: $API_PID)..."
        kill "$API_PID"

        # Wait for graceful shutdown
        local wait_count=0
        while kill -0 "$API_PID" 2>/dev/null && [ $wait_count -lt 10 ]; do
            sleep 1
            wait_count=$((wait_count + 1))
        done

        # Force kill if still running
        if kill -0 "$API_PID" 2>/dev/null; then
            echo "⚠️  Force killing API server..."
            kill -9 "$API_PID" 2>/dev/null
        fi

        rm -f /tmp/api.pid
        echo "✓ API server stopped"
    else
        echo "ℹ️  API server PID file found but process not running"
        rm -f /tmp/api.pid
    fi
else
    echo "ℹ️  API server PID file not found"
fi

# Stop Celery worker
if [ -f /tmp/celery.pid ]; then
    CELERY_PID=$(cat /tmp/celery.pid)
    if kill -0 "$CELERY_PID" 2>/dev/null; then
        echo "👷 Stopping Celery worker (PID: $CELERY_PID)..."
        kill "$CELERY_PID"

        # Wait for graceful shutdown
        local wait_count=0
        while kill -0 "$CELERY_PID" 2>/dev/null && [ $wait_count -lt 10 ]; do
            sleep 1
            wait_count=$((wait_count + 1))
        done

        # Force kill if still running
        if kill -0 "$CELERY_PID" 2>/dev/null; then
            echo "⚠️  Force killing Celery worker..."
            kill -9 "$CELERY_PID" 2>/dev/null
        fi

        rm -f /tmp/celery.pid
        echo "✓ Celery worker stopped"
    else
        echo "ℹ️  Celery PID file found but process not running"
        rm -f /tmp/celery.pid
    fi
else
    echo "ℹ️  Celery worker PID file not found"
fi

# Stop any remaining processes
echo "🧹 Cleaning up remaining processes..."

# Kill uvicorn processes
local uvicorn_pids=$(pgrep -f "uvicorn.*app.main:app" 2>/dev/null || true)
if [ -n "$uvicorn_pids" ]; then
    echo "🌐 Stopping remaining uvicorn processes: $uvicorn_pids"
    echo "$uvicorn_pids" | xargs kill 2>/dev/null || true
    sleep 2
    echo "$uvicorn_pids" | xargs kill -9 2>/dev/null || true
fi

# Kill celery processes
local celery_pids=$(pgrep -f "celery.*worker" 2>/dev/null || true)
if [ -n "$celery_pids" ]; then
    echo "👷 Stopping remaining celery processes: $celery_pids"
    echo "$celery_pids" | xargs kill 2>/dev/null || true
    sleep 2
    echo "$celery_pids" | xargs kill -9 2>/dev/null || true
fi

# Clean up PID files
rm -f /tmp/api.pid /tmp/celery.pid

echo "✓ All M3 Enhanced services stopped successfully"

# Optional: Show remaining processes
local remaining_processes=$(pgrep -f "uvicorn\|celery.*m3" 2>/dev/null || true)
if [ -n "$remaining_processes" ]; then
    echo "⚠️  Warning: Some related processes may still be running:"
    ps aux | grep -E "uvicorn|celery" | grep -v grep || true
fi

echo "🏁 Shutdown complete"
EOF

    chmod +x "$WORK_DIR/stop.sh"
    log_info "Comprehensive stop script created successfully"

    # Create comprehensive status script
    log_info "Creating comprehensive status script..."

    cat > "$WORK_DIR/status.sh" << 'EOF'
#!/bin/bash

#=======================================================
#         M3 Enhanced - Comprehensive Status Script
#=======================================================

echo "📊 M3 Enhanced Service Status"
echo "=================================="

# System Information
echo ""
echo "🖥️  SYSTEM INFORMATION:"
echo "   Date: $(date)"
echo "   Uptime: $(uptime -p 2>/dev/null || uptime)"
echo "   Load: $(cat /proc/loadavg)"
echo "   Memory: $(free -h | grep Mem | awk '{print $3"/"$2}')"

# Environment Information
if [ -f ".env" ]; then
    echo ""
    echo "⚙️  ENVIRONMENT CONFIGURATION:"
    source .env 2>/dev/null || true
    echo "   Setup Version: ${SETUP_VERSION:-unknown}"
    echo "   Device: ${DEVICE:-unknown}"
    echo "   GPU Enabled: ${GPU_ENABLED:-unknown}"
    echo "   Max Workers: ${MAX_WORKERS:-unknown}"
    echo "   API Port: ${API_PORT:-8000}"
fi

# Service Status Checks
echo ""
echo "🔧 SERVICE STATUS:"

# Redis Status
echo -n "   🔴 Redis: "
if redis-cli ping >/dev/null 2>&1; then
    redis_version=$(redis-cli info server 2>/dev/null | grep redis_version | cut -d: -f2 | tr -d '\r' || echo "unknown")
    redis_memory=$(redis-cli info memory 2>/dev/null | grep used_memory_human | cut -d: -f2 | tr -d '\r' || echo "unknown")
    echo "✅ Running (v$redis_version, ${redis_memory}B used)"

    # Test Redis functionality
    if redis-cli set status_test "ok" >/dev/null 2>&1 && \
       [ "$(redis-cli get status_test 2>/dev/null)" = "ok" ]; then
        redis-cli del status_test >/dev/null 2>&1
        echo "      📊 Functionality: ✅ Working"
    else
        echo "      📊 Functionality: ❌ Read/Write Failed"
    fi
else
    echo "❌ Not Running"
fi

# API Server Status
echo -n "   🌐 API Server: "
if [ -f /tmp/api.pid ]; then
    API_PID=$(cat /tmp/api.pid)
    if kill -0 "$API_PID" 2>/dev/null; then
        echo "✅ Running (PID: $API_PID)"

        # Check API health endpoint
        if curl -s http://localhost:${API_PORT:-8000}/health >/dev/null 2>&1; then
            echo "      🏥 Health Check: ✅ Healthy"
        else
            echo "      🏥 Health Check: ❌ Unhealthy"
        fi
    else
        echo "❌ Process Not Found (stale PID file)"
        rm -f /tmp/api.pid
    fi
else
    echo "❌ Not Running (no PID file)"
fi

# Celery Worker Status
echo -n "   👷 Celery Worker: "
if [ -f /tmp/celery.pid ]; then
    CELERY_PID=$(cat /tmp/celery.pid)
    if kill -0 "$CELERY_PID" 2>/dev/null; then
        echo "✅ Running (PID: $CELERY_PID)"
    else
        echo "❌ Process Not Found (stale PID file)"
        rm -f /tmp/celery.pid
    fi
else
    echo "❌ Not Running"
fi

# File System Status
echo ""
echo "📁 FILE SYSTEM STATUS:"

critical_paths=(
    "backend/app/main.py:FastAPI Application"
    "frontend/static/index.html:Web Interface"
    "frontend/static/style.css:Stylesheets"
    "frontend/static/app.js:JavaScript"
    ".env:Environment Config"
)

for path_info in "${critical_paths[@]}"; do
    IFS=':' read -r path description <<< "$path_info"
    echo -n "   📄 $description: "
    if [ -f "$path" ]; then
        size=$(du -h "$path" 2>/dev/null | cut -f1 || echo "?")
        echo "✅ Present (${size}B)"
    else
        echo "❌ Missing"
    fi
done

# Directory Status
echo ""
echo "📂 DIRECTORY STATUS:"

required_dirs=("logs" "uploads" "results" "temp" "models" "config")
for dir in "${required_dirs[@]}"; do
    echo -n "   📁 $dir: "
    if [ -d "$dir" ]; then
        file_count=$(find "$dir" -type f 2>/dev/null | wc -l || echo "?")
        dir_size=$(du -sh "$dir" 2>/dev/null | cut -f1 || echo "?")
        echo "✅ Present ($file_count files, ${dir_size}B)"
    else
        echo "❌ Missing"
    fi
done

# Network Status
echo ""
echo "🌐 NETWORK STATUS:"

# Test API endpoints
endpoints=(
    "/:Main Page"
    "/health:Health Check"
    "/docs:API Documentation"
)

for endpoint_info in "${endpoints[@]}"; do
    IFS=':' read -r endpoint description <<< "$endpoint_info"
    echo -n "   🔗 $description: "

    if curl -s -o /dev/null -w "%{http_code}" "http://localhost:${API_PORT:-8000}$endpoint" 2>/dev/null | grep -q "200\|404"; then
        echo "✅ Accessible"
    else
        echo "❌ Not Accessible"
    fi
done

# Python Environment Status
echo ""
echo "🐍 PYTHON ENVIRONMENT:"

python3 -c "
import sys
print(f'   Python Version: {sys.version.split()[0]}')

# Check critical modules
critical_modules = {
    'fastapi': 'FastAPI Framework',
    'uvicorn': 'ASGI Server',
    'numpy': 'NumPy Arrays',
    'torch': 'PyTorch ML',
    'librosa': 'Audio Analysis',
    'demucs': 'Audio Separation',
    'basic_pitch': 'Music Transcription'
}

for module, description in critical_modules.items():
    try:
        imported = __import__(module)
        version = getattr(imported, '__version__', 'unknown')
        print(f'   ✅ {description}: v{version}')
    except ImportError:
        print(f'   ❌ {description}: Not Available')
"

# API Health Check (if available)
echo ""
echo "🏥 API HEALTH CHECK:"
if curl -s http://localhost:${API_PORT:-8000}/health >/dev/null 2>&1; then
    echo "   Status: ✅ API Responding"
    echo ""
    echo "   Health Response:"
    curl -s http://localhost:${API_PORT:-8000}/health | python3 -m json.tool 2>/dev/null | sed 's/^/      /' || \
        echo "      Could not parse JSON response"
else
    echo "   Status: ❌ API Not Responding"
fi

# Access Information
echo ""
echo "🔗 ACCESS INFORMATION:"
echo "   🌐 Web Interface: http://localhost:${API_PORT:-8000}"
echo "   📚 API Documentation: http://localhost:${API_PORT:-8000}/docs"
echo "   📖 ReDoc Documentation: http://localhost:${API_PORT:-8000}/redoc"
echo "   🏥 Health Endpoint: http://localhost:${API_PORT:-8000}/health"

# Quick Actions
echo ""
echo "⚡ QUICK ACTIONS:"
echo "   Start Services: ./start.sh"
echo "   Stop Services: ./stop.sh"
echo "   View Logs: tail -f logs/*.log"
echo "   Test Health: curl http://localhost:${API_PORT:-8000}/health"

echo ""
echo "=================================="
EOF

    chmod +x "$WORK_DIR/status.sh"
    log_info "Comprehensive status script created successfully"

    log_info "Service management scripts created successfully"
}

#=======================================================
#               COMPREHENSIVE INSTALLATION VERIFICATION
#=======================================================

verify_installation() {
    log_step 13 "Comprehensive Installation Verification"

    log_info "Performing comprehensive installation verification..."

    # Comprehensive Python environment verification
    log_info "Verifying comprehensive Python environment..."

    python3 -c "
import sys
import importlib

print('=== COMPREHENSIVE PYTHON ENVIRONMENT VERIFICATION ===')
print(f'Python Version: {sys.version}')
print(f'Python Executable: {sys.executable}')
print(f'Python Path: {sys.path}')

# Core ML Framework Verification
print('\\n=== CORE ML FRAMEWORKS ===')
frameworks = {
    'numpy': 'NumPy Arrays and Mathematics',
    'scipy': 'Scientific Computing',
    'sklearn': 'Machine Learning',
    'torch': 'PyTorch Deep Learning',
    'tensorflow': 'TensorFlow Deep Learning'
}

framework_status = {}
for module, description in frameworks.items():
    try:
        imported = importlib.import_module(module)
        version = getattr(imported, '__version__', 'unknown')
        print(f'✅ {description}: v{version}')
        framework_status[module] = True
    except ImportError as e:
        print(f'❌ {description}: FAILED - {e}')
        framework_status[module] = False

# Audio Processing Verification
print('\\n=== AUDIO PROCESSING LIBRARIES ===')
audio_libs = {
    'soundfile': 'Audio I/O',
    'audioread': 'Audio Format Support',
    'librosa': 'Audio Analysis',
    'pydub': 'Audio Manipulation',
    'resampy': 'Sample Rate Conversion'
}

audio_status = {}
for module, description in audio_libs.items():
    try:
        imported = importlib.import_module(module)
        version = getattr(imported, '__version__', 'unknown')
        print(f'✅ {description}: v{version}')
        audio_status[module] = True
    except ImportError as e:
        print(f'❌ {description}: FAILED - {e}')
        audio_status[module] = False

# Music Processing Verification
print('\\n=== MUSIC PROCESSING LIBRARIES ===')
music_libs = {
    'pretty_midi': 'MIDI Processing',
    'music21': 'Music Analysis',
    'mido': 'MIDI I/O',
    'demucs': 'Audio Separation',
    'basic_pitch': 'Music Transcription',
    'mir_eval': 'Music Information Retrieval'
}

music_status = {}
for module, description in music_libs.items():
    try:
        imported = importlib.import_module(module)
        version = getattr(imported, '__version__', 'unknown')
        print(f'✅ {description}: v{version}')
        music_status[module] = True
    except ImportError as e:
        print(f'❌ {description}: FAILED - {e}')
        music_status[module] = False

# Web Framework Verification
print('\\n=== WEB FRAMEWORKS ===')
web_libs = {
    'fastapi': 'FastAPI Web Framework',
    'uvicorn': 'ASGI Server',
    'pydantic': 'Data Validation',
    'celery': 'Task Queue',
    'redis': 'Redis Client'
}

web_status = {}
for module, description in web_libs.items():
    try:
        imported = importlib.import_module(module)
        version = getattr(imported, '__version__', 'unknown')
        print(f'✅ {description}: v{version}')
        web_status[module] = True
    except ImportError as e:
        print(f'❌ {description}: FAILED - {e}')
        web_status[module] = False

# Summary
print('\\n=== VERIFICATION SUMMARY ===')
all_frameworks = {**framework_status, **audio_status, **music_status, **web_status}
passed = sum(1 for status in all_frameworks.values() if status)
total = len(all_frameworks)
success_rate = (passed / total) * 100

print(f'Total Modules Tested: {total}')
print(f'Successfully Imported: {passed}')
print(f'Failed Imports: {total - passed}')
print(f'Success Rate: {success_rate:.1f}%')

if success_rate >= 90:
    print('\\n✅ VERIFICATION STATUS: EXCELLENT')
elif success_rate >= 75:
    print('\\n⚠️  VERIFICATION STATUS: GOOD (some optional components missing)')
elif success_rate >= 50:
    print('\\n⚠️  VERIFICATION STATUS: PARTIAL (significant components missing)')
else:
    print('\\n❌ VERIFICATION STATUS: FAILED (too many critical components missing)')
    sys.exit(1)
"

    if [ $? -ne 0 ]; then
        fatal_error "Python environment verification failed"
    fi

    log_info "Python environment verification completed successfully"

    # Comprehensive file structure verification
    log_info "Performing comprehensive file structure verification..."

    local critical_files=(
        "$WORK_DIR/backend/app/main.py:FastAPI Application"
        "$WORK_DIR/frontend/static/index.html:Frontend Main Page"
        "$WORK_DIR/frontend/static/style.css:Frontend Stylesheet"
        "$WORK_DIR/frontend/static/app.js:Frontend JavaScript"
        "$WORK_DIR/.env:Environment Configuration"
        "$WORK_DIR/start.sh:Start Script"
        "$WORK_DIR/stop.sh:Stop Script"
        "$WORK_DIR/status.sh:Status Script"
    )

    local file_verification_passed=true

    for file_info in "${critical_files[@]}"; do
        IFS=':' read -r file_path description <<< "$file_info"

        if [ -f "$file_path" ]; then
            local file_size=$(stat -c%s "$file_path" 2>/dev/null || echo 0)
            log_info "✓ $description: exists (${file_size} bytes)"
        else
            log_error "✗ $description: MISSING - $file_path"
            file_verification_passed=false
        fi
    done

    if [ "$file_verification_passed" = "false" ]; then
        fatal_error "Critical files are missing - installation is incomplete"
    fi

    # Verify directory structure
    log_info "Verifying directory structure..."

    local required_directories=(
        "$LOG_DIR:Log Directory"
        "$MODELS_DIR:Models Directory"
        "$TEMP_DIR:Temporary Directory"
        "$UPLOADS_DIR:Uploads Directory"
        "$RESULTS_DIR:Results Directory"
        "$CONFIG_DIR:Configuration Directory"
    )

    for dir_info in "${required_directories[@]}"; do
        IFS=':' read -r dir_path description <<< "$dir_info"

        if [ -d "$dir_path" ]; then
            log_info "✓ $description: exists and accessible"
        else
            log_warn "✗ $description: missing - creating..."
            mkdir -p "$dir_path" || fatal_error "Failed to create directory: $dir_path"
        fi
    done

    # Comprehensive functionality testing
    log_info "Performing comprehensive functionality testing..."

    # Test audio processing pipeline
    python3 -c "
import numpy as np
import librosa
import soundfile as sf

print('Testing audio processing pipeline...')

# Generate test audio signal
sample_rate = 22050
duration = 1.0
t = np.linspace(0, duration, int(sample_rate * duration))
test_signal = 0.5 * np.sin(2 * np.pi * 440 * t)  # 440 Hz sine wave

print(f'✓ Generated test signal: {test_signal.shape}')

# Test librosa functionality
stft = librosa.stft(test_signal)
mfccs = librosa.feature.mfcc(y=test_signal, sr=sample_rate, n_mfcc=13)

print(f'✓ STFT computation: {stft.shape}')
print(f'✓ MFCC extraction: {mfccs.shape}')

# Test basic pitch functionality
try:
    import basic_pitch
    from basic_pitch.inference import predict

    model_output, midi_data, note_events = predict(test_signal)
    print(f'✓ Basic Pitch transcription: output_shape={model_output.shape}')
except Exception as e:
    print(f'⚠️  Basic Pitch test failed: {e}')

print('Audio processing pipeline test completed')
"

    # Test ML frameworks integration
    python3 -c "
import numpy as np
import torch
import tensorflow as tf

print('Testing ML frameworks integration...')

# Test NumPy
np_array = np.random.randn(10, 10)
print(f'✓ NumPy array creation: {np_array.shape}')

# Test PyTorch
torch_tensor = torch.from_numpy(np_array).float()
torch_result = torch.matmul(torch_tensor, torch_tensor.T)
print(f'✓ PyTorch tensor operations: {torch_result.shape}')

# Test TensorFlow
tf_tensor = tf.constant(np_array, dtype=tf.float32)
tf_result = tf.linalg.matmul(tf_tensor, tf_tensor, transpose_b=True)
print(f'✓ TensorFlow tensor operations: {tf_result.shape}')

print('ML frameworks integration test completed')
"

    log_info "Functionality testing completed successfully"

    log_info "Comprehensive installation verification completed successfully"
}

#=======================================================
#               COMPREHENSIVE CLEANUP
#=======================================================

cleanup_installation() {
    log_step 14 "Comprehensive Installation Cleanup"

    log_info "Performing comprehensive installation cleanup..."

    # Comprehensive pip cache cleanup
    log_info "Performing comprehensive pip cache cleanup..."

    local cache_size_before=$(python3 -m pip cache info 2>/dev/null | grep "Cache size" | cut -d: -f2 | xargs || echo "unknown")
    log_info "Pip cache size before cleanup: $cache_size_before"

    python3 -m pip cache purge || {
        log_warn "Pip cache purge failed, trying manual cleanup..."
        rm -rf ~/.cache/pip/* 2>/dev/null || true
        rm -rf /tmp/pip-* 2>/dev/null || true
    }

    local cache_size_after=$(python3 -m pip cache info 2>/dev/null | grep "Cache size" | cut -d: -f2 | xargs || echo "unknown")
    log_info "Pip cache size after cleanup: $cache_size_after"

    # System package cache cleanup
    log_info "Performing system package cache cleanup..."

    # Remove orphaned packages
    log_info "Removing orphaned packages..."
    apt-get autoremove -y 2>/dev/null || log_warn "Autoremove failed"

    # Clean package cache
    log_info "Cleaning package cache..."
    apt-get clean 2>/dev/null || log_warn "Package clean failed"

    # Clean temporary files
    log_info "Cleaning temporary files..."

    # Clean system temp files
    find /tmp -name "pip-*" -type d -mtime +1 -exec rm -rf {} + 2>/dev/null || true
    find /tmp -name "tmp*" -type d -empty -mtime +1 -delete 2>/dev/null || true

    # Clean Python cache files
    log_info "Cleaning Python cache files..."
    find "$WORK_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find "$WORK_DIR" -name "*.pyc" -delete 2>/dev/null || true
    find "$WORK_DIR" -name "*.pyo" -delete 2>/dev/null || true

    # Set proper permissions
    log_info "Setting proper file permissions..."

    # Make scripts executable
    chmod +x "$WORK_DIR/start.sh" 2>/dev/null || log_warn "Failed to set start.sh permissions"
    chmod +x "$WORK_DIR/stop.sh" 2>/dev/null || log_warn "Failed to set stop.sh permissions"
    chmod +x "$WORK_DIR/status.sh" 2>/dev/null || log_warn "Failed to set status.sh permissions"

    # Set directory permissions
    chmod 755 "$WORK_DIR" 2>/dev/null || true
    chmod -R 755 "$LOG_DIR" 2>/dev/null || true
    chmod -R 755 "$UPLOADS_DIR" 2>/dev/null || true
    chmod -R 755 "$RESULTS_DIR" 2>/dev/null || true
    chmod -R 755 "$TEMP_DIR" 2>/dev/null || true

    # Create initial log files with proper permissions
    log_info "Creating initial log files..."
    touch "$LOG_DIR/api.log" "$LOG_DIR/celery.log" "$LOG_DIR/system.log" 2>/dev/null || true
    chmod 644 "$LOG_DIR"/*.log 2>/dev/null || true

    # Final cleanup verification
    log_info "Verifying cleanup completion..."

    local temp_files=$(find /tmp -name "*pip*" -o -name "*m3*" -o -name "*demucs*" 2>/dev/null | wc -l || echo 0)
    log_info "Remaining temporary files: $temp_files"

    local cache_dirs=$(find ~/.cache -maxdepth 2 -name "*pip*" -type d 2>/dev/null | wc -l || echo 0)
    log_info "Remaining cache directories: $cache_dirs"

    log_info "Comprehensive cleanup completed successfully"
}

#=======================================================
#               MAIN EXECUTION FUNCTION
#=======================================================

main() {
    print_header

    log_info "Starting M3 Enhanced comprehensive setup process..."
    log_info "Script version: $SCRIPT_VERSION"
    log_info "Working directory: $WORK_DIR"
    log_info "Timestamp: $TIMESTAMP"
    log_info "Process ID: $$"

    # Execute all comprehensive setup steps
    verify_system
    install_system_dependencies
    setup_python_environment
    resolve_dependency_conflicts
    install_core_ml_frameworks
    install_audio_processing
    install_music_processing
    install_web_frameworks
    setup_redis
    download_models
    configure_environment
    create_service_scripts
    verify_installation
    cleanup_installation

    # Calculate comprehensive setup time
    local end_time=$(date +%s)
    local duration=$((end_time - START_TIME))
    local hours=$((duration / 3600))
    local minutes=$(((duration % 3600) / 60))
    local seconds=$((duration % 60))

    # Comprehensive system configuration detection
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

    # Display comprehensive completion message
    echo ""
    echo "=============================================="
    echo "    M3 ENHANCED COMPREHENSIVE SETUP COMPLETE"
    echo "=============================================="
    echo ""
    echo "📊 INSTALLATION SUMMARY:"
    echo "  ⏱️  Setup Time: ${hours}h ${minutes}m ${seconds}s"

