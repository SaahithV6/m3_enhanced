#!/usr/bin/env python3
"""
M3 Enhanced - Google Colab Setup Script
Complete setup for running M3 Enhanced in Google Colab with ngrok tunnel
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

class ColabSetup:
    def __init__(self):
        self.setup_complete = False
        self.server_url = None
        self.ngrok_token = None

    def print_banner(self):
        banner = """
        ╔══════════════════════════════════════════════════════════════╗
        ║                    🎵 M3 Enhanced 🎵                         ║
        ║              Google Colab Setup Script                       ║
        ║                                                              ║
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

        for cmd, desc in commands:
            self.run_command(cmd, desc)

    def install_python_dependencies(self):
        """Install Python packages with optimized order"""
        print("🐍 Installing Python dependencies...")

        # Install PyTorch first (GPU-enabled for Colab)
        self.run_command(
            "pip install -q torch torchvision torchaudio",
            "Installing PyTorch (GPU-enabled)"
        )

        # Core ML/Audio packages
        ml_packages = [
            "transformers accelerate datasets",
            "librosa[display] soundfile pretty_midi music21",
            "tensorflow tensorflow-hub",
            "demucs basic-pitch",
        ]

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

    def setup_ngrok(self):
        """Setup ngrok for public URL"""
        print("🌐 Setting up ngrok tunnel...")

        # Install pyngrok
        self.run_command("pip install -q pyngrok", "Installing pyngrok")

        # Get ngrok auth token from user
        from google.colab import userdata
        try:
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

    def create_minimal_backend(self):
        """Create a minimal FastAPI backend for Colab"""
        print("⚙️  Creating FastAPI backend...")

        # Main FastAPI app
        main_py = '''
import os
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

app = FastAPI(title="M3 Enhanced - Colab Edition", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure directories exist
for dir_name in ["uploads", "results", "temp"]:
    Path(dir_name).mkdir(exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>M3 Enhanced - Colab Edition</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
            .header { text-align: center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                     color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; }
            .upload-zone { border: 2px dashed #ccc; border-radius: 10px; padding: 40px;
                          text-align: center; margin: 20px 0; cursor: pointer; }
            .upload-zone:hover { border-color: #667eea; background: #f8f9ff; }
            .btn { background: #667eea; color: white; padding: 12px 24px; border: none;
                  border-radius: 5px; cursor: pointer; font-size: 16px; }
            .btn:hover { background: #5a6fd8; }
            .progress-bar { width: 100%; height: 20px; background: #f0f0f0; border-radius: 10px;
                           margin: 20px 0; overflow: hidden; }
            .progress-fill { height: 100%; background: #667eea; width: 0%; transition: width 0.3s; }
            .results { margin-top: 30px; padding: 20px; background: #f8f9ff; border-radius: 10px; }
            .hidden { display: none; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎵 M3 Enhanced - Colab Edition</h1>
            <p>AI-Powered Music Processing Pipeline</p>
        </div>

        <div class="upload-zone" onclick="document.getElementById('fileInput').click()">
            <h3>📁 Upload Audio File</h3>
            <p>Click here or drag and drop your audio file</p>
            <p>Supported formats: MP3, WAV, FLAC, M4A</p>
            <input type="file" id="fileInput" accept=".mp3,.wav,.flac,.m4a" style="display: none;">
        </div>

        <div>
            <button class="btn" onclick="processFile()">🚀 Start Processing</button>
            <button class="btn" onclick="viewResults()" style="margin-left: 10px;">📊 View Results</button>
        </div>

        <div id="progress" class="hidden">
            <h3>Processing...</h3>
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

            document.getElementById('fileInput').addEventListener('change', function(e) {
                selectedFile = e.target.files[0];
                if (selectedFile) {
                    document.querySelector('.upload-zone p').textContent =
                        `Selected: ${selectedFile.name} (${(selectedFile.size/1024/1024).toFixed(2)} MB)`;
                }
            });

            async function processFile() {
                if (!selectedFile) {
                    alert('Please select a file first!');
                    return;
                }

                const formData = new FormData();
                formData.append('file', selectedFile);

                document.getElementById('progress').classList.remove('hidden');
                document.getElementById('results').classList.add('hidden');

                try {
                    const response = await fetch('/upload', {
                        method: 'POST',
                        body: formData
                    });

                    if (response.ok) {
                        const result = await response.json();
                        showResults(result);
                    } else {
                        throw new Error('Upload failed');
                    }
                } catch (error) {
                    alert('Error: ' + error.message);
                }
            }

            function showResults(data) {
                document.getElementById('progress').classList.add('hidden');
                document.getElementById('results').classList.remove('hidden');
                document.getElementById('resultContent').innerHTML =
                    `<pre>${JSON.stringify(data, null, 2)}</pre>`;
            }

            async function viewResults() {
                try {
                    const response = await fetch('/list-results');
                    const files = await response.json();
                    showResults({available_results: files});
                } catch (error) {
                    alert('Error loading results: ' + error.message);
                }
            }
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
        # Process with Demucs
        result_dir = Path("results") / file.filename.split('.')[0]
        result_dir.mkdir(exist_ok=True)

        cmd = f"python -m demucs.separate --out {result_dir} {upload_path}"
        subprocess.run(cmd, shell=True, check=True)

        # List generated files
        separated_files = list(result_dir.glob("**/*.wav"))

        return {
            "status": "success",
            "filename": file.filename,
            "separated_tracks": [str(f.relative_to(result_dir)) for f in separated_files],
            "result_directory": str(result_dir)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.get("/list-results")
async def list_results():
    results_dir = Path("results")
    if not results_dir.exists():
        return []

    result_folders = [d.name for d in results_dir.iterdir() if d.is_dir()]
    return result_folders

@app.get("/download/{folder}/{filename}")
async def download_file(folder: str, filename: str):
    file_path = Path("results") / folder / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)
'''

        with open("backend/app/main.py", "w") as f:
            f.write(main_py)

    def download_models(self):
        """Download essential AI models"""
        print("🤖 Downloading AI models...")

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

    def start_server(self):
        """Start the FastAPI server with ngrok tunnel"""
        print("🚀 Starting M3 Enhanced server...")

        # Start server in background thread
        def run_server():
            os.chdir("/content")
            subprocess.run([
                "python", "-m", "uvicorn",
                "backend.app.main:app",
                "--host", "0.0.0.0",
                "--port", "8000"
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
        if self.server_url:
            display(HTML(f'''
            <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white; border-radius: 10px; margin: 20px 0;">
                <h2>🎵 M3 Enhanced is Ready!</h2>
                <p>Your music processing server is running</p>
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
        """Run the complete setup process"""
        self.print_banner()

        try:
            self.install_system_dependencies()
            self.install_python_dependencies()
            self.setup_ngrok()
            self.create_project_structure()
            self.create_minimal_backend()
            self.download_models()

            print("\n✅ Setup completed successfully!")
            print("🚀 Starting server...")

            server_url = self.start_server()
            self.show_interface()

            print(f"\n🎉 M3 Enhanced is now running!")
            print(f"🌐 Access your instance at: {server_url}")
            print("\n📝 Usage Instructions:")
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
    setup = ColabSetup()
    return setup.run_complete_setup()

# For direct execution
if __name__ == "__main__":
    setup_m3_enhanced()
