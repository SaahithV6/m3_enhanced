# M3 Enhanced - Production Dockerfile
# Optimized for CPU and GPU inference with studio-grade audio processing

FROM nvidia/cuda:12.1-devel-ubuntu22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV CUDA_VISIBLE_DEVICES=0

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y \
    # Core system tools
    curl \
    wget \
    git \
    build-essential \
    software-properties-common \
    \
    # Python and development tools
    python3.10 \
    python3.10-dev \
    python3-pip \
    python3.10-venv \
    \
    # Audio processing libraries
    ffmpeg \
    libsndfile1 \
    libsndfile1-dev \
    libasound2-dev \
    portaudio19-dev \
    libportaudio2 \
    libfftw3-dev \
    \
    # Additional audio codecs and tools
    lame \
    flac \
    vorbis-tools \
    opus-tools \
    \
    # Graphics and visualization
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    \
    # File type detection
    libmagic1 \
    file \
    \
    # Redis for job queue
    redis-server \
    \
    # Cleanup
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create application user for security
RUN useradd -m -u 1000 m3user && \
    mkdir -p /app /models /temp /uploads /results && \
    chown -R m3user:m3user /app /models /temp /uploads /results

# Set working directory
WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel && \
    pip3 install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 && \
    pip3 install --no-cache-dir -r requirements.txt

# Install additional audio processing packages
RUN pip3 install --no-cache-dir \
    demucs \
    audio-separator \
    basic-pitch \
    librosa[display] \
    soundfile \
    pretty_midi \
    music21 \
    mir_eval \
    pesq \
    pystoi \
    openl3 \
    tensorflow \
    tensorflow-hub \
    transformers \
    accelerate \
    datasets \
    yt-dlp \
    python-magic \
    redis \
    celery[redis] \
    matplotlib \
    seaborn \
    plotly \
    pillow

# Copy application code
COPY --chown=m3user:m3user app/ ./app/
COPY --chown=m3user:m3user scripts/ ./scripts/

# Create directories and set permissions
RUN mkdir -p /app/logs /app/temp /app/models /app/uploads /app/results && \
    chown -R m3user:m3user /app

# Switch to non-root user
USER m3user

# Set environment variables
ENV PYTHONPATH=/app
ENV M3_MODELS_DIR=/models
ENV M3_TEMP_DIR=/temp
ENV M3_UPLOADS_DIR=/uploads
ENV M3_RESULTS_DIR=/results

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Default command - can be overridden
CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
