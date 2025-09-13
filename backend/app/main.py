from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
from pathlib import Path
from typing import Optional, Dict, List
import shutil
import aiofiles
from datetime import datetime
import mimetypes

from .core.config import config
from .core.job_scheduler import job_scheduler, JobStatus
from .utils.file_manager import FileManager

# Initialize FastAPI app
app = FastAPI(
    title="M3 Enhanced Audio Processing API",
    description="Advanced multi-pass audio separation and transcription system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for web interface
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# Initialize services
file_manager = FileManager()

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    # Start job scheduler
    job_scheduler.start_scheduler()

    # Ensure directories exist
    config.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    config.TEMP_DIR.mkdir(parents=True, exist_ok=True)

    # Preload essential models
    from .models.model_manager import model_manager
    model_manager.preload_essential_models()

    print("M3 Enhanced API started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    job_scheduler.stop_scheduler()
    print("M3 Enhanced API shutdown complete")

# Health check endpoint
@app.get("/health")
async def health_check():
    """System health check"""
    try:
        queue_status = job_scheduler.get_queue_status()
        from .models.model_manager import model_manager
        model_info = model_manager.get_model_info()

        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "queue_status": queue_status,
            "loaded_models": list(model_info.keys()),
            "gpu_available": len(job_scheduler.gpu_workers) > 0
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

# File upload endpoint
@app.post("/upload")
async def upload_audio_file(file: UploadFile = File(...)):
    """Upload audio file for processing"""
    try:
        # Validate file type
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        allowed_extensions = {'.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg', '.wma'}
        file_ext = Path(file.filename).suffix.lower()

        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
            )

        # Validate file size (100MB limit)
        if file.size and file.size > 100 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="File too large (max 100MB)")

        # Generate unique filename
        unique_filename = file_manager.generate_unique_filename(file.filename)
        file_path = config.UPLOADS_DIR / unique_filename

        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)

        # Validate audio file
        if not file_manager.validate_audio_file(file_path):
            file_path.unlink()  # Delete invalid file
            raise HTTPException(status_code=400, detail="Invalid audio file")

        return {
            "filename": unique_filename,
            "original_name": file.filename,
            "size": len(content),
            "upload_time": datetime.utcnow().isoformat(),
            "message": "File uploaded successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

# URL download endpoint
@app.post("/download")
async def download_from_url(url: str, format_preference: str = "mp3"):
    """Download audio from URL using yt-dlp"""
    try:
        from .preprocessing.format_converter import FormatConverter

        converter = FormatConverter()
        downloaded_file = await converter.download_from_url(url, format_preference)

        return {
            "filename": downloaded_file.name,
            "size": downloaded_file.stat().st_size,
            "download_time": datetime.utcnow().isoformat(),
            "source_url": url,
            "message": "File downloaded successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

# Job submission endpoint
@app.post("/process")
async def submit_processing_job(
    filename: str,
    priority: int = 5,
    advanced_options: Optional[Dict] = None
):
    """Submit audio file for M3 processing"""
    try:
        file_path = config.UPLOADS_DIR / filename

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        # Validate priority
        if not (1 <= priority <= 10):
            raise HTTPException(status_code=400, detail="Priority must be between 1-10")

        # Submit job
        job_id = job_scheduler.submit_job(
            filename,
            job_params=advanced_options or {},
            priority=priority
        )

        return {
            "job_id": job_id,
            "status": "submitted",
            "estimated_duration": "5-15 minutes",
            "queue_position": job_scheduler.get_queue_position(job_id),
            "message": "Job submitted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Job submission failed: {str(e)}")

# Job status endpoint
@app.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """Get current job status and progress"""
    try:
        job_info = job_scheduler.get_job_status(job_id)

        if not job_info:
            raise HTTPException(status_code=404, detail="Job not found")

        response = {
            "job_id": job_id,
            "status": job_info.status.value,
            "progress": job_info.progress,
            "current_step": job_info.current_step,
            "created_at": job_info.created_at.isoformat(),
            "estimated_duration": job_info.estimated_duration
        }

        if job_info.started_at:
            response["started_at"] = job_info.started_at.isoformat()

        if job_info.completed_at:
            response["completed_at"] = job_info.completed_at.isoformat()
            response["processing_time"] = (
                job_info.completed_at - job_info.started_at
            ).total_seconds() if job_info.started_at else None

        if job_info.error_message:
            response["error"] = job_info.error_message

        if job_info.result_path:
            response["result_available"] = True
            response["download_url"] = f"/download/{job_id}"

        if job_info.status == JobStatus.PENDING:
            response["queue_position"] = job_scheduler.get_queue_position(job_id)

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

# Job cancellation endpoint
@app.delete("/jobs/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a pending or running job"""
    try:
        success = job_scheduler.cancel_job(job_id)

        if not success:
            raise HTTPException(status_code=400, detail="Job cannot be cancelled")

        return {
            "job_id": job_id,
            "status": "cancelled",
            "message": "Job cancelled successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cancellation failed: {str(e)}")

# Result download endpoint
@app.get("/download/{job_id}")
async def download_results(job_id: str):
    """Download processing results"""
    try:
        job_info = job_scheduler.get_job_status(job_id)

        if not job_info:
            raise HTTPException(status_code=404, detail="Job not found")

        if job_info.status != JobStatus.COMPLETED:
            raise HTTPException(status_code=400, detail="Job not completed")

        if not job_info.result_path:
            raise HTTPException(status_code=404, detail="Results not available")

        result_path = Path(job_info.result_path)

        if not result_path.exists():
            raise HTTPException(status_code=404, detail="Result file not found")

        # Return file with appropriate headers
        return FileResponse(
            path=result_path,
            filename=f"m3_results_{job_id}.zip",
            media_type="application/zip"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

# Queue status endpoint
@app.get("/queue")
async def get_queue_status():
    """Get current processing queue status"""
    try:
        queue_status = job_scheduler.get_queue_status()
        return queue_status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Queue status failed: {str(e)}")

# Model information endpoint
@app.get("/models")
async def get_model_info():
    """Get information about loaded models"""
    try:
        from .models.model_manager import model_manager
        model_info = model_manager.get_model_info()

        return {
            "loaded_models": model_info,
            "gpu_memory_usage": "Available" if model_manager.gpu_memory_limit > 0 else "Not available"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model info failed: {str(e)}")

# System metrics endpoint
@app.get("/metrics")
async def get_system_metrics():
    """Get system performance metrics"""
    try:
        import psutil
        import torch

        metrics = {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent,
            "gpu_available": torch.cuda.is_available() if torch else False
        }

        if torch and torch.cuda.is_available():
            metrics["gpu_memory_used"] = torch.cuda.memory_allocated() / 1024**3
            metrics["gpu_memory_total"] = torch.cuda.get_device_properties(0).total_memory / 1024**3

        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metrics failed: {str(e)}")

# Cleanup endpoint (admin only)
@app.post("/admin/cleanup")
async def cleanup_old_files(days: int = 7):
    """Clean up old files and jobs (admin endpoint)"""
    try:
        cleaned_count = file_manager.cleanup_old_files(days)

        return {
            "cleaned_files": cleaned_count,
            "cleanup_date": datetime.utcnow().isoformat(),
            "message": f"Cleaned up files older than {days} days"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")

# Root endpoint - serve web interface
@app.get("/")
async def root():
    """Serve the main web interface"""
    return FileResponse("frontend/static/index.html")

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        workers=1  # Single worker for development
    )
