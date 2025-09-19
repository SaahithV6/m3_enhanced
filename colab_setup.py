"""
M3 Enhanced - Intelligent Google Colab Setup Script
Automatically detects and optimizes for GPU/TPU/CPU runtimes
"""

import os
import sys
import subprocess
import time
import threading
from pathlib import Path
import zipfile
import requests
from IPython.display import HTML, display, clear_output
import json
import psutil
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IntelligentColabSetup:
    def __init__(self):
        self.setup_complete = False
        self.server_url = None
        self.ngrok_token = None
        self.runtime_type = self._detect_runtime()
        self.device_config = self._configure_devices()

    def _detect_runtime(self):
        """Intelligently detect the current runtime type"""
        runtime_info = {
            'type': 'cpu',
            'gpu_available': False,
            'tpu_available': False,
            'gpu_name': None,
            'gpu_memory': 0,
            'device_count': 0
        }

        # Check for GPU
        try:
            import torch
            if torch.cuda.is_available():
                runtime_info['gpu_available'] = True
                runtime_info['type'] = 'gpu'
                runtime_info['device_count'] = torch.cuda.device_count()
                runtime_info['gpu_name'] = torch.cuda.get_device_name(0)
                runtime_info['gpu_memory'] = torch.cuda.get_device_properties(0).total_memory // 1024**3
                logger.info(f"🎮 GPU detected: {runtime_info['gpu_name']} ({runtime_info['gpu_memory']}GB)")
        except:
            pass

        # Check for TPU
        try:
            import torch_xla.core.xla_model as xm
            if xm.xla_device():
                runtime_info['tpu_available'] = True
                runtime_info['type'] = 'tpu'
                runtime_info['device_count'] = xm.xrt_world_size()
                logger.info(f"🚀 TPU detected: {runtime_info['device_count']} cores")
        except:
            pass

        # Fallback to CPU info
        if runtime_info['type'] == 'cpu':
            runtime_info['device_count'] = psutil.cpu_count()
            logger.info(f"🖥️  CPU runtime: {runtime_info['device_count']} cores")

        return runtime_info

    def _configure_devices(self):
        """Configure device-specific settings"""
        config = {
            'torch_device': 'cpu',
            'tf_device': '/CPU:0',
            'batch_size': 1,
            'num_workers': 2,
            'memory_fraction': 0.8
        }

        if self.runtime_type['gpu_available']:
            config.update({
                'torch_device': 'cuda',
                'tf_device': '/GPU:0',
                'batch_size': min(8, self.runtime_type['gpu_memory'] // 2),
                'num_workers': min(4, self.runtime_type['device_count'] * 2),
                'memory_fraction': 0.9
            })

        elif self.runtime_type['tpu_available']:
            config.update({
                'torch_device': 'xla',
                'tf_device': '/TPU:0',
                'batch_size': 32,  # TPUs work better with larger batches
                'num_workers': 8,
                'memory_fraction': 0.95
            })

        return config

    def print_banner(self):
        runtime_emoji = {
            'gpu': '🎮',
            'tpu': '🚀',
            'cpu': '🖥️'
        }

        banner = f"""
        ╔══════════════════════════════════════════════════════════════╗
        ║                    🎵 M3 Enhanced 🎵                         ║
        ║              Intelligent Colab Setup Script                  ║
        ║                                                              ║
        ║    Runtime: {runtime_emoji[self.runtime_type['type']]} {self.runtime_type['type'].upper():<10} Device: {self.device_config['torch_device']:<10}           ║
        ║    Advanced AI-Powered Music Processing Pipeline             ║
        ║    • Audio Separation • Transcription • Analysis            ║
        ╚══════════════════════════════════════════════════════════════╝
        """
        print(banner)

    def run_command(self, cmd, description="", capture_output=False):
        """Run shell command with progress indication"""
        print(f"🔄 {description}...")
        try:
            if capture_output:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode != 0:
                    print(f"❌ Error: {result.stderr}")
                    return None
                return result.stdout.strip()
            else:
                subprocess.run(cmd, shell=True, check=True)
                print(f"✅ {description} completed")
                return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Error in {description}: {e}")
            return False

    def install_system_dependencies(self):
        """Install system-level dependencies"""
        print("📦 Installing system dependencies...")

        commands = [
            ("apt-get update -qq", "Updating package lists"),
            ("apt-get install -y -qq ffmpeg libsndfile1 libsndfile1-dev libasound2-dev portaudio19-dev libfftw3-dev redis-server", "Installing audio libraries"),
            ("service redis-server start", "Starting Redis server"),
        ]

        # Add GPU-specific packages
        if self.runtime_type['gpu_available']:
            commands.append(("apt-get install -y -qq nvidia-cuda-toolkit nvtop", "Installing GPU tools"))

        for cmd, desc in commands:
            self.run_command(cmd, desc)

    def install_python_dependencies(self):
        """Install Python packages optimized for detected runtime"""
        print(f"🐍 Installing Python dependencies for {self.runtime_type['type'].upper()} runtime...")

        # Upgrade pip first
        self.run_command("pip install -q --upgrade pip setuptools wheel", "Upgrading pip")

        # Install PyTorch based on runtime
        if self.runtime_type['tpu_available']:
            # TPU-optimized PyTorch
            self.run_command(
                "pip install -q torch torchvision torchaudio torch-xla[tpu] -f https://storage.googleapis.com/libtpu-releases/index.html",
                "Installing PyTorch for TPU"
            )
        elif self.runtime_type['gpu_available']:
            # GPU-optimized PyTorch
            self.run_command(
                "pip install -q torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121",
                "Installing PyTorch for GPU"
            )
        else:
            # CPU-only PyTorch
            self.run_command(
                "pip install -q torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu",
                "Installing PyTorch for CPU"
            )

        # Install TensorFlow based on runtime
        if self.runtime_type['tpu_available']:
            self.run_command("pip install -q tensorflow[and-cuda] tensorflow-hub", "Installing TensorFlow for TPU")
        elif self.runtime_type['gpu_available']:
            self.run_command("pip install -q tensorflow[and-cuda] tensorflow-hub", "Installing TensorFlow for GPU")
        else:
            self.run_command("pip install -q tensorflow tensorflow-hub", "Installing TensorFlow for CPU")

        # Core ML/Audio packages
        ml_packages = [
            "transformers accelerate datasets",
            "librosa[display] soundfile pretty_midi music21",
            "demucs basic-pitch audio-separator",
        ]

        # Adjust batch sizes for different runtimes
        for packages in ml_packages:
            self.run_command(f"pip install -q {packages}", f"Installing {packages}")

        # Web framework and utilities
        web_packages = [
            "fastapi uvicorn[standard] python-multipart aiofiles",
            "redis celery[redis]",
            "yt-dlp python-magic matplotlib seaborn plotly pillow",
            "mir_eval pesq pystoi openl3"
        ]

        for packages in web_packages:
            self.run_command(f"pip install -q {packages}", f"Installing {packages}")

    def setup_environment_variables(self):
        """Setup runtime-optimized environment variables"""
        print("🔧 Configuring environment variables...")

        # Base environment variables
        env_vars = {
            'M3_RUNTIME_TYPE': self.runtime_type['type'],
            'M3_DEVICE': self.device_config['torch_device'],
            'M3_BATCH_SIZE': str(self.device_config['batch_size']),
            'M3_NUM_WORKERS': str(self.device_config['num_workers']),
            'PYTHONPATH': '/content',
        }

        # CPU-specific optimizations
        if self.runtime_type['type'] == 'cpu':
            cpu_threads = min(8, self.runtime_type['device_count'])
            env_vars.update({
                'OMP_NUM_THREADS': str(cpu_threads),
                'MKL_NUM_THREADS': str(cpu_threads),
                'OPENBLAS_NUM_THREADS': str(cpu_threads),
                'NUMBA_NUM_THREADS': str(cpu_threads),
            })

        # GPU-specific optimizations
        elif self.runtime_type['type'] == 'gpu':
            env_vars.update({
                'CUDA_VISIBLE_DEVICES': '0',
                'PYTORCH_CUDA_ALLOC_CONF': 'max_split_size_mb:512',
                'TF_FORCE_GPU_ALLOW_GROWTH': 'true',
                'TF_GPU_MEMORY_GROWTH': 'true',
            })

        # TPU-specific optimizations
        elif self.runtime_type['type'] == 'tpu':
            env_vars.update({
                'XLA_USE_BF16': '1',
                'TPU_ML_PLATFORM': 'PyTorch/XLA',
                'XLA_TENSOR_ALLOCATOR_MAXSIZE': '100000000',
            })

        # Set all environment variables
        for key, value in env_vars.items():
            os.environ[key] = value
            logger.debug(f"Set {key}={value}")

    def setup_ngrok(self):
        """Setup ngrok for public URL"""
        print("🌐 Setting up ngrok tunnel...")

        # Install pyngrok
        self.run_command("pip install -q pyngrok", "Installing pyngrok")

        # Get ngrok auth token from user
        try:
            from google.colab import userdata
            self.ngrok_token = userdata.get('NGROK_TOKEN')
        except:
            print("⚠️  No NGROK_TOKEN found in Colab secrets.")
            print("Please add your ngrok token to Colab secrets as 'NGROK_TOKEN'")
            print("Get your token from: https://dashboard.ngrok.com/get-started/your-authtoken")

            token = input("Enter your ngrok auth token (or press Enter to skip): ").strip()
            if token:
                self.ngrok_token = token

        if self.ngrok_token:
            from pyngrok import ngrok
            ngrok.set_auth_token(self.ngrok_token)
            print("✅ Ngrok authentication configured")
        else:
            print("⚠️  Continuing without ngrok (local access only)")

    def create_project_structure(self):
        """Create necessary directories and files"""
        print("📁 Creating project structure...")

        directories = [
            "backend/app/core",
            "backend/app/models",
            "backend/app/processors",
            "backend/app/utils",
            "frontend/static",
            "models",
            "temp",
            "uploads",
            "results",
            "logs"
        ]

        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)

    def create_runtime_optimized_backend(self):
        """Create FastAPI backend optimized for detected runtime"""
        print(f"⚙️  Creating {self.runtime_type['type'].upper()}-optimized FastAPI backend...")

        # Main FastAPI app with runtime optimizations
        main_py = f'''
import os
import torch
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pathlib import Path
import aiofiles
import json
from datetime import datetime
import subprocess
import tempfile
import shutil
import logging

# Runtime configuration
RUNTIME_TYPE = "{self.runtime_type['type']}"
DEVICE = "{self.device_config['torch_device']}"
BATCH_SIZE = {self.device_config['batch_size']}
NUM_WORKERS = {self.device_config['num_workers']}

app = FastAPI(title=f"M3 Enhanced - {{RUNTIME_TYPE.upper()}} Edition", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure device-specific settings
if RUNTIME_TYPE == "gpu" and torch.cuda.is_available():
    torch.backends.cudnn.benchmark = True
    device = torch.device("cuda")
elif RUNTIME_TYPE == "tpu":
    try:
        import torch_xla.core.xla_model as xm
        device = xm.xla_device()
    except:
        device = torch.device("cpu")
else:
    device = torch.device("cpu")
    # CPU optimizations
    torch.set_num_threads({min(8, self.runtime_type['device_count'])})

# Ensure directories exist
for dir_name in ["uploads", "results", "temp"]:
    Path(dir_name).mkdir(exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def root():
    runtime_emoji = {{"gpu": "🎮", "tpu": "🚀", "cpu": "🖥️"}}
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>M3 Enhanced - {{RUNTIME_TYPE.upper()}} Edition</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }}
            .header {{ text-align: center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                     color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; }}
            .runtime-info {{ background: rgba(255,255,255,0.1); padding: 15px; border-radius: 5px; margin: 15px 0; }}
            .upload-zone {{ border: 2px dashed #ccc; border-radius: 10px; padding: 40px;
                          text-align: center; margin: 20px 0; cursor: pointer; }}
            .upload-zone:hover {{ border-color: #667eea; background: #f8f9ff; }}
            .btn {{ background: #667eea; color: white; padding: 12px 24px; border: none;
                  border-radius: 5px; cursor: pointer; font-size: 16px; }}
            .btn:hover {{ background: #5a6fd8; }}
            .progress-bar {{ width: 100%; height: 20px; background: #f0f0f0; border-radius: 10px;
                           margin: 20px 0; overflow: hidden; }}
            .progress-fill {{ height: 100%; background: #667eea; width: 0%; transition: width 0.3s; }}
            .results {{ margin-top: 30px; padding: 20px; background: #f8f9ff; border-radius: 10px; }}
            .hidden {{ display: none; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>{runtime_emoji[RUNTIME_TYPE]} M3 Enhanced - {{RUNTIME_TYPE.upper()}} Edition</h1>
            <p>AI-Powered Music Processing Pipeline</p>
            <div class="runtime-info">
                <strong>Runtime:</strong> {{RUNTIME_TYPE.upper()}} |
                <strong>Device:</strong> {{DEVICE}} |
                <strong>Batch Size:</strong> {{BATCH_SIZE}}
            </div>
        </div>

        <div class="upload-zone" onclick="document.getElementById('fileInput').click()">
            <h3>📁 Upload Audio File</h3>
            <p>Click here or drag and drop your audio file</p>
            <p>Supported formats: MP3, WAV, FLAC, M4A</p>
            <p><small>Optimized for {{RUNTIME_TYPE.upper()}} processing</small></p>
            <input type="file" id="fileInput" accept=".mp3,.wav,.flac,.m4a" style="display: none;">
        </div>

        <div>
            <button class="btn" onclick="processFile()">🚀 Start Processing</button>
            <button class="btn" onclick="viewResults()" style="margin-left: 10px;">📊 View Results</button>
        </div>

        <div id="progress" class="hidden">
            <h3>Processing on {{RUNTIME_TYPE.upper()}}...</h3>
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill"></div>
            </div>
            <div id="status">Initializing...</div>
        </div>

        <div id="results" class="results hidden">
            <h3>📊 Processing Results</h3>
            <div id="resultContent"></div>
        </div>

        <script>
            let selectedFile = null;

            document.getElementById('fileInput').addEventListener('change', function(e) {{
                selectedFile = e.target.files[0];
                if (selectedFile) {{
                    document.querySelector('.upload-zone p').textContent =
                        `Selected: ${{selectedFile.name}} (${{(selectedFile.size/1024/1024).toFixed(2)}} MB)`;
                }}
            }});

            async function processFile() {{
                if (!selectedFile) {{
                    alert('Please select a file first!');
                    return;
                }}

                const formData = new FormData();
                formData.append('file', selectedFile);

                document.getElementById('progress').classList.remove('hidden');
                document.getElementById('results').classList.add('hidden');

                try {{
                    const response = await fetch('/upload', {{
                        method: 'POST',
                        body: formData
                    }});

                    if (response.ok) {{
                        const result = await response.json();
                        showResults(result);
                    }} else {{
                        throw new Error('Upload failed');
                    }}
                }} catch (error) {{
                    alert('Error: ' + error.message);
                }}
            }}

            function showResults(data) {{
                document.getElementById('progress').classList.add('hidden');
                document.getElementById('results').classList.remove('hidden');
                document.getElementById('resultContent').innerHTML =
                    `<pre>${{JSON.stringify(data, null, 2)}}</pre>`;
            }}

            async function viewResults() {{
                try {{
                    const response = await fetch('/list-results');
                    const files = await response.json();
                    showResults({{available_results: files}});
                }} catch (error) {{
                    alert('Error loading results: ' + error.message);
                }}
            }}
        </script>
    </body>
    </html>
    """

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Save uploaded file
    upload_path = Path("uploads") / file.filename
    async with aiofiles.open(upload_path, 'wb') as f:
        content = await file.read()
        await f.write(content)

    try:
        # Process with runtime-optimized settings
        result_dir = Path("results") / file.filename.split('.')[0]
        result_dir.mkdir(exist_ok=True)

        # Adjust processing based on runtime
        if RUNTIME_TYPE == "gpu":
            cmd = f"python -m demucs.separate --device cuda --jobs {{NUM_WORKERS}} --out {{result_dir}} {{upload_path}}"
        elif RUNTIME_TYPE == "tpu":
            cmd = f"python -m demucs.separate --device cpu --jobs {{NUM_WORKERS}} --out {{result_dir}} {{upload_path}}"
        else:
            cmd = f"python -m demucs.separate --device cpu --jobs {{min(4, NUM_WORKERS)}} --out {{result_dir}} {{upload_path}}"

        subprocess.run(cmd, shell=True, check=True)

        # List generated files
        separated_files = list(result_dir.glob("**/*.wav"))

        return {{
            "status": "success",
            "filename": file.filename,
            "runtime": RUNTIME_TYPE,
            "device": DEVICE,
            "separated_tracks": [str(f.relative_to(result_dir)) for f in separated_files],
            "result_directory": str(result_dir)
        }}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {{str(e)}}")

@app.get("/list-results")
async def list_results():
    results_dir = Path("results")
    if not results_dir.exists():
        return []

    result_folders = [d.name for d in results_dir.iterdir() if d.is_dir()]
    return result_folders

@app.get("/download/{{folder}}/{{filename}}")
async def download_file(folder: str, filename: str):
    file_path = Path("results") / folder / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)

@app.get("/system-info")
async def get_system_info():
    return {{
        "runtime_type": RUNTIME_TYPE,
        "device": DEVICE,
        "batch_size": BATCH_SIZE,
        "num_workers": NUM_WORKERS,
        "torch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available() if RUNTIME_TYPE == "gpu" else False,
        "gpu_name": torch.cuda.get_device_name(0) if RUNTIME_TYPE == "gpu" and torch.cuda.is_available() else None
    }}
'''

        with open("backend/app/main.py", "w") as f:
            f.write(main_py)

    def download_models(self):
        """Download AI models optimized for runtime"""
        print(f"🤖 Downloading AI models for {self.runtime_type['type'].upper()} runtime...")

        # Download Demucs models
        self.run_command(
            "python -c 'import demucs; demucs.pretrained.get_model(\"htdemucs\")'",
            "Downloading Demucs separation model"
        )

        # Download BasicPitch
        self.run_command(
            "python -c 'from basic_pitch import ICASSP_2022_MODEL_PATH; print(ICASSP_2022_MODEL_PATH)'",
            "Initializing Basic Pitch model"
        )

    def run_system_tests(self):
        """Run runtime-specific system tests"""
        print(f"🧪 Running {self.runtime_type['type'].upper()} system tests...")

        tests = []

        # Test PyTorch
        try:
            import torch
            if self.runtime_type['type'] == 'gpu' and torch.cuda.is_available():
                torch.zeros(1).cuda()
                tests.append(("PyTorch GPU", "✅ PASS"))
            elif self.runtime_type['type'] == 'tpu':
                import torch_xla.core.xla_model as xm
                device = xm.xla_device()
                torch.zeros(1, device=device)
                tests.append(("PyTorch TPU", "✅ PASS"))
            else:
                torch.zeros(1)
                tests.append(("PyTorch CPU", "✅ PASS"))
        except Exception as e:
            tests.append(("PyTorch", f"❌ FAIL: {str(e)}"))

        # Test TensorFlow
        try:
            import tensorflow as tf
            if self.runtime_type['type'] == 'gpu' and tf.config.list_physical_devices('GPU'):
                tests.append(("TensorFlow GPU", "✅ PASS"))
            elif self.runtime_type['type'] == 'tpu':
                resolver = tf.distribute.cluster_resolver.TPUClusterResolver()
                tf.config.experimental_connect_to_cluster(resolver)
                tests.append(("TensorFlow TPU", "✅ PASS"))
            else:
                tests.append(("TensorFlow CPU", "✅ PASS"))
        except Exception as e:
            tests.append(("TensorFlow", f"❌ FAIL: {str(e)}"))

        # Display results
        print("\n" + "="*50)
        print(f"{self.runtime_type['type'].upper()} SYSTEM TESTS")
        print("="*50)
        for test_name, result in tests:
            print(f"{test_name:25} {result}")
        print("="*50 + "\n")

    def start_server(self):
        """Start the FastAPI server with ngrok tunnel"""
        print(f"🚀 Starting M3 Enhanced server on {self.runtime_type['type'].upper()} runtime...")

        # Start server in background thread
        def run_server():
            os.chdir("/content")
            subprocess.run([
                "python", "-m", "uvicorn",
                "backend.app.main:app",
                "--host", "0.0.0.0",
                "--port", "8000",
                "--workers", str(min(4, self.device_config['num_workers']))
            ])

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

        # Wait for server to start
        time.sleep(5)

        # Setup ngrok tunnel if available
        if self.ngrok_token:
            try:
                from pyngrok import ngrok
                public_url = ngrok.connect(8000)
                self.server_url = public_url
                print(f"🌐 Public URL: {public_url}")
                print(f"📱 Share this link to access your M3 Enhanced instance!")
            except Exception as e:
                print(f"⚠️  Ngrok setup failed: {e}")
                print("🏠 Server running locally at: http://localhost:8000")
                self.server_url = "http://localhost:8000"
        else:
            print("🏠 Server running locally at: http://localhost:8000")
            self.server_url = "http://localhost:8000"

        return self.server_url

    def show_interface(self):
        """Display the web interface in Colab"""
        runtime_emoji = {'gpu': '🎮', 'tpu': '🚀', 'cpu': '🖥️'}

        if self.server_url:
            display(HTML(f'''
            <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white; border-radius: 10px; margin: 20px 0;">
                <h2>{runtime_emoji[self.runtime_type['type']]} M3 Enhanced is Ready!</h2>
                <p>Your music processing server is running on <strong>{self.runtime_type['type'].upper()}</strong></p>
                <div style="background: rgba(255,255,255,0.1); padding: 10px; border-radius: 5px; margin: 10px 0;">
                    <small>Device: {self.device_config['torch_device']} | Batch Size: {self.device_config['batch_size']} | Workers: {self.device_config['num_workers']}</small>
                </div>
                <a href="{self.server_url}" target="_blank"
                   style="background: white; color: #667eea; padding: 12px 24px; border-radius: 5px;
                          text-decoration: none; font-weight: bold; display: inline-block; margin: 10px;">
                   🚀 Open M3 Enhanced Interface
                </a>
                <br><br>
                <small>URL: {self.server_url}</small>
            </div>
            '''))

    def run_complete_setup(self):
        """Run the complete intelligent setup process"""
        self.print_banner()

        try:
            self.install_system_dependencies()
            self.install_python_dependencies()
            self.setup_environment_variables()
            self.setup_ngrok()
            self.create_project_structure()
            self.create_runtime_optimized_backend()
            self.download_models()
            self.run_system_tests()

            print(f"\n✅ Setup completed successfully for {self.runtime_type['type'].upper()} runtime!")
            print("🚀 Starting server...")

            server_url = self.start_server()
            self.show_interface()

            print(f"\n🎉 M3 Enhanced is now running on {self.runtime_type['type'].upper()}!")
            print(f"🌐 Access your instance at: {server_url}")
            print(f"\n📝 Runtime-Optimized Settings:")
            print(f"   • Device: {self.device_config['torch_device']}")
            print(f"   • Batch Size: {self.device_config['batch_size']}")
            print(f"   • Workers: {self.device_config['num_workers']}")
            print(f"\n📋 Usage Instructions:")
            print("1. Click the link above to open the web interface")
            print("2. Upload an audio file (MP3, WAV, FLAC, M4A)")
            print("3. Click 'Start Processing' to separate audio tracks")
            print("4. View and download results")

        except Exception as e:
            print(f"❌ Setup failed: {e}")
            raise

# Auto-run setup when imported
def setup_m3_enhanced():
    """Main setup function for easy import"""
    setup = IntelligentColabSetup()
    return setup.run_complete_setup()

# For direct execution
if __name__ == "__main__":
    setup_m3_enhanced()
