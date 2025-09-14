# M3 Enhanced - GPU-Optimized Dockerfile
# Specialized container for maximum GPU performance and memory efficiency

FROM nvidia/cuda:12.1-devel-ubuntu22.04

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV CUDA_VISIBLE_DEVICES=0

# GPU-specific optimizations
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility
ENV CUDA_CACHE_PATH=/tmp/cuda-cache
ENV TORCH_CUDA_ARCH_LIST="6.0;6.1;7.0;7.5;8.0;8.6;8.9;9.0"

# Install CUDA-optimized system dependencies
RUN apt-get update && apt-get install -y \
    # Core development tools
    curl \
    wget \
    git \
    build-essential \
    cmake \
    ninja-build \
    \
    # Python 3.10 for optimal compatibility
    python3.10 \
    python3.10-dev \
    python3-pip \
    python3.10-venv \
    \
    # CUDA development libraries
    libcuda1 \
    cuda-toolkit-12-1 \
    libcudnn8 \
    libcudnn8-dev \
    \
    # Optimized audio processing
    ffmpeg \
    libsndfile1-dev \
    libfftw3-dev \
    libsamplerate0-dev \
    \
    # High-performance audio codecs
    lame \
    flac \
    libopus-dev \
    libvorbis-dev \
    \
    # GPU acceleration for multimedia
    libnvidia-encode-470 \
    libnvidia-decode-470 \
    \
    # Memory optimization tools
    numactl \
    htop \
    nvtop \
    \
    # Cleanup
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/*

# Create optimized user for GPU workloads
RUN useradd -m -u 1000 -s /bin/bash m3gpu && \
    usermod -a -G video m3gpu && \
    mkdir -p /app /models /temp /uploads /results /cache && \
    chown -R m3gpu:m3gpu /app /models /temp /uploads /results /cache

# Set working directory
WORKDIR /app

# Copy requirements for GPU-optimized installation
COPY requirements.txt .

# Install GPU-optimized Python packages
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel

# Install PyTorch with CUDA 12.1 support and optimizations
RUN pip3 install --no-cache-dir \
    torch==2.1.0+cu121 \
    torchvision==0.16.0+cu121 \
    torchaudio==2.1.0+cu121 \
    --index-url https://download.pytorch.org/whl/cu121

# Install TensorFlow with GPU support
RUN pip3 install --no-cache-dir \
    tensorflow[and-cuda]==2.14.0 \
    tensorflow-hub

# Install audio processing packages with GPU acceleration
RUN pip3 install --no-cache-dir \
    demucs \
    audio-separator[gpu] \
    librosa[gpu] \
    soundfile \
    resampy \
    numba \
    cupy-cuda12x

# Install ML packages optimized for GPU
RUN pip3 install --no-cache-dir \
    transformers[torch] \
    accelerate \
    datasets \
    optimum[onnxruntime-gpu] \
    onnxruntime-gpu

# Install remaining audio/MIDI packages
RUN pip3 install --no-cache-dir \
    basic-pitch \
    pretty_midi \
    music21 \
    mir_eval \
    openl3 \
    laion-clap \
    madmom

# Install performance monitoring and optimization
RUN pip3 install --no-cache-dir \
    psutil \
    GPUtil \
    nvidia-ml-py3 \
    memory-profiler

# Copy application code
COPY --chown=m3gpu:m3gpu app/ ./app/
COPY --chown=m3gpu:m3gpu scripts/ ./scripts/

# Create optimized directories with proper permissions
RUN mkdir -p \
    /app/logs \
    /app/temp \
    /app/models \
    /app/uploads \
    /app/results \
    /cache/torch \
    /cache/transformers \
    /cache/tensorflow \
    && chown -R m3gpu:m3gpu /app /cache

# Switch to GPU user
USER m3gpu

# Set GPU-optimized environment variables
ENV PYTHONPATH=/app
ENV M3_MODELS_DIR=/models
ENV M3_TEMP_DIR=/temp
ENV M3_UPLOADS_DIR=/uploads
ENV M3_RESULTS_DIR=/results

# PyTorch optimizations
ENV TORCH_HOME=/cache/torch
ENV PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
ENV CUDA_LAUNCH_BLOCKING=0

# TensorFlow optimizations
ENV TF_CPP_MIN_LOG_LEVEL=2
ENV TF_GPU_ALLOCATOR=cuda_malloc_async
ENV TF_FORCE_GPU_ALLOW_GROWTH=true

# Transformers cache
ENV TRANSFORMERS_CACHE=/cache/transformers
ENV HF_HOME=/cache/transformers

# GPU memory optimization
ENV PYTORCH_CUDA_ALLOC_CONF=backend:native
ENV CUDA_MEMORY_FRACTION=0.9

# Pre-compile CUDA kernels for faster startup
RUN python3 -c "import torch; torch.cuda.is_available(); torch.zeros(1).cuda()" || true

# Health check with GPU validation
HEALTHCHECK --interval=60s --timeout=30s --start-period=120s --retries=3 \
    CMD python3 -c "import torch; assert torch.cuda.is_available(); print('GPU OK')" && \
        curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# GPU-optimized startup command
CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--loop", "uvloop"]
