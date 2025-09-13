import redis
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
from dataclasses import dataclass, asdict
from celery import Celery, Task
from celery.result import AsyncResult
from celery.signals import task_prerun, task_postrun, task_failure
import threading
import time
import asyncio
from pathlib import Path

from .config import config

class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"

@dataclass
class JobInfo:
    job_id: str
    status: JobStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0
    current_step: str = ""
    total_steps: int = 0
    error_message: Optional[str] = None
    result_path: Optional[str] = None
    input_file: str = ""
    estimated_duration: Optional[int] = None
    worker_id: Optional[str] = None
    gpu_id: Optional[int] = None
    priority: int = 5  # 1=highest, 10=lowest

# Initialize Celery app
celery_app = Celery(
    'm3_processor',
    broker=config.CELERY_BROKER_URL,
    backend=config.CELERY_RESULT_BACKEND,
    include=['app.core.job_scheduler']
)

# Celery configuration for high-performance audio processing
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,

    # Performance settings
    task_acks_late=True,
    worker_prefetch_multiplier=1,  # One task at a time per worker for GPU memory
    task_routes={
        'app.core.job_scheduler.process_audio_job': {'queue': 'gpu_queue'},
        'app.core.job_scheduler.transcribe_stems': {'queue': 'transcription_queue'},
    },

    # Retry settings
    task_default_retry_delay=60,
    task_max_retries=3,

    # Results
    result_expires=3600 * 24 * 7,  # 7 days

    # Worker settings
    worker_max_tasks_per_child=50,  # Restart workers to prevent memory leaks
    worker_disable_rate_limits=True,
)

class M3JobScheduler:
    """
    Production-grade job scheduler with Celery backend.
    Handles distributed processing across multiple GPU workers.
    """

    def __init__(self):
        self.redis_client = redis.Redis.from_url(config.CELERY_BROKER_URL)
        self.active_jobs: Dict[str, JobInfo] = {}
        self.lock = threading.Lock()

        # GPU resource management
        self.gpu_workers = self._discover_gpu_workers()
        self.gpu_queue_status = {i: 0 for i in range(len(self.gpu_workers))}

    def _discover_gpu_workers(self) -> List[Dict[str, Any]]:
        """Discover available GPU workers"""
        try:
            import torch
            if torch.cuda.is_available():
                gpu_count = torch.cuda.device_count()
                return [
                    {
                        'gpu_id': i,
                        'memory_gb': torch.cuda.get_device_properties(i).total_memory / (1024**3),
                        'name': torch.cuda.get_device_name(i)
                    }
                    for i in range(gpu_count)
                ]
            else:
                return [{'gpu_id': -1, 'memory_gb': 0, 'name': 'CPU'}]
        except ImportError:
            return [{'gpu_id': -1, 'memory_gb': 0, 'name': 'CPU'}]

    def submit_job(self,
                   input_file: str,
                   job_params: Dict = None,
                   priority: int = 5) -> str:
        """Submit a new job to the distributed processing queue"""
        job_id = str(uuid.uuid4())

        job_info = JobInfo(
            job_id=job_id,
            status=JobStatus.PENDING,
            created_at=datetime.utcnow(),
            input_file=input_file,
            total_steps=12,  # Updated pipeline step count
            priority=priority
        )

        with self.lock:
            self.active_jobs[job_id] = job_info

        # Store in Redis for persistence
        self._store_job_info(job_info)

        # Submit to Celery with priority and GPU selection
        optimal_gpu = self._select_optimal_gpu()

        # Chain the processing tasks
        processing_chain = (
            process_audio_job.s(job_id, input_file, job_params or {}) |
            transcribe_stems.s(job_id) |
            finalize_output.s(job_id)
        )

        # Apply async with priority routing
        result = processing_chain.apply_async(
            priority=priority,
            routing_key=f'gpu_{optimal_gpu}' if optimal_gpu >= 0 else 'cpu'
        )

        # Store Celery task ID
        job_info.worker_id = result.id
        job_info.gpu_id = optimal_gpu
        self._store_job_info(job_info)

        print(f"Job {job_id} submitted to GPU {optimal_gpu} with priority {priority}")
        return job_id

    def _select_optimal_gpu(self) -> int:
        """Select GPU with lowest queue length and sufficient memory"""
        if not self.gpu_workers:
            return -1

        # Get current queue lengths from Redis
        queue_lengths = {}
        for gpu_info in self.gpu_workers:
            gpu_id = gpu_info['gpu_id']
            if gpu_id >= 0:
                queue_key = f"gpu_queue_{gpu_id}"
                queue_length = self.redis_client.llen(queue_key)
                queue_lengths[gpu_id] = queue_length
            else:
                queue_lengths[-1] = float('inf')  # CPU fallback

        # Select GPU with minimum queue length
        optimal_gpu = min(queue_lengths.keys(), key=lambda x: queue_lengths[x])
        return optimal_gpu

    def get_job_status(self, job_id: str) -> Optional[JobInfo]:
        """Get current status of a job"""
        with self.lock:
            job_info = self.active_jobs.get(job_id)

        if not job_info:
            job_info = self._load_job_info(job_id)

        # Update status from Celery if we have a worker ID
        if job_info and job_info.worker_id:
            celery_result = AsyncResult(job_info.worker_id, app=celery_app)

            if celery_result.state == 'PENDING':
                job_info.status = JobStatus.PENDING
            elif celery_result.state == 'STARTED':
                job_info.status = JobStatus.RUNNING
            elif celery_result.state == 'SUCCESS':
                job_info.status = JobStatus.COMPLETED
                if celery_result.result:
                    job_info.result_path = celery_result.result.get('result_path')
            elif celery_result.state == 'FAILURE':
                job_info.status = JobStatus.FAILED
                job_info.error_message = str(celery_result.info)
            elif celery_result.state == 'RETRY':
                job_info.status = JobStatus.RETRYING

        return job_info

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending or running job"""
        job_info = self.get_job_status(job_id)

        if not job_info:
            return False

        if job_info.worker_id:
            # Revoke Celery task
            celery_app.control.revoke(job_info.worker_id, terminate=True)

        # Update status
        job_info.status = JobStatus.CANCELLED
        job_info.completed_at = datetime.utcnow()
        self._store_job_info(job_info)

        return True

    def get_queue_status(self) -> Dict:
        """Get comprehensive queue status"""
        # Get Celery queue lengths
        inspect = celery_app.control.inspect()
        active_tasks = inspect.active() or {}
        scheduled_tasks = inspect.scheduled() or {}

        # Calculate per-GPU statistics
        gpu_stats = {}
        for gpu_info in self.gpu_workers:
            gpu_id = gpu_info['gpu_id']
            gpu_stats[f"gpu_{gpu_id}"] = {
                'active_jobs': 0,
                'queued_jobs': 0,
                'memory_gb': gpu_info['memory_gb'],
                'name': gpu_info['name']
            }

        # Count active tasks per GPU
        for worker, tasks in active_tasks.items():
            for task in tasks:
                routing_key = task.get('routing_key', 'cpu')
                if routing_key in gpu_stats:
                    gpu_stats[routing_key]['active_jobs'] += 1

        # Count scheduled tasks per GPU
        for worker, tasks in scheduled_tasks.items():
            for task in tasks:
                routing_key = task.get('routing_key', 'cpu')
                if routing_key in gpu_stats:
                    gpu_stats[routing_key]['queued_jobs'] += 1

        return {
            'gpu_workers': len(self.gpu_workers),
            'gpu_stats': gpu_stats,
            'total_active': sum(len(tasks) for tasks in active_tasks.values()),
            'total_scheduled': sum(len(tasks) for tasks in scheduled_tasks.values()),
            'max_concurrent_per_gpu': config.MAX_CONCURRENT_JOBS
        }

    def update_job_progress(self, job_id: str, progress: float, step: str):
        """Update job progress (called by Celery tasks)"""
        job_info = self.get_job_status(job_id)
        if job_info:
            job_info.progress = progress
            job_info.current_step = step
            self._store_job_info(job_info)

            # Also update Celery task state
            if job_info.worker_id:
                current_task = AsyncResult(job_info.worker_id, app=celery_app)
                current_task.update_state(
                    state='PROGRESS',
                    meta={'progress': progress, 'step': step}
                )

    def _store_job_info(self, job_info: JobInfo):
        """Store job info in Redis with proper serialization"""
        try:
            job_dict = asdict(job_info)

            # Convert datetime and enum objects
            for key, value in job_dict.items():
                if isinstance(value, datetime):
                    job_dict[key] = value.isoformat()
                elif isinstance(value, JobStatus):
                    job_dict[key] = value.value

            self.redis_client.setex(
                f"m3_job:{job_info.job_id}",
                timedelta(days=7),
                json.dumps(job_dict)
            )
        except Exception as e:
            print(f"Failed to store job info: {e}")

    def _load_job_info(self, job_id: str) -> Optional[JobInfo]:
        """Load job info from Redis with proper deserialization"""
        try:
            job_data = self.redis_client.get(f"m3_job:{job_id}")
            if job_data:
                job_dict = json.loads(job_data)

                # Convert ISO strings back to datetime objects
                for key, value in job_dict.items():
                    if key.endswith('_at') and value:
                        job_dict[key] = datetime.fromisoformat(value)

                job_dict['status'] = JobStatus(job_dict['status'])
                return JobInfo(**job_dict)
        except Exception as e:
            print(f"Failed to load job info: {e}")

        return None

# Celery Tasks
@celery_app.task(bind=True, name='app.core.job_scheduler.process_audio_job')
def process_audio_job(self, job_id: str, input_file: str, job_params: Dict) -> Dict:
    """Main audio processing task (separation phase)"""
    try:
        # Update job status
        job_scheduler.update_job_progress(job_id, 5, "Starting audio processing")

        # Import processing modules
        from ..preprocessing.audio_enhancer import AudioEnhancer
        from ..preprocessing.format_converter import FormatConverter
        from ..processors.multipass_separator import MultiPassSeparator

        # Create callback for progress updates
        def progress_callback(step: str, progress: float = None):
            if progress is None:
                current_progress = 5 + (55 * len(step.split(':')) / 10)  # Estimate
            else:
                current_progress = 5 + (progress * 0.55)  # 5-60% for separation
            job_scheduler.update_job_progress(job_id, current_progress, step)

        # Phase 1: Preprocessing
        progress_callback("Enhancing audio quality", 5)
        enhancer = AudioEnhancer()
        converter = FormatConverter()

        input_path = config.UPLOADS_DIR / input_file
        enhanced_path = enhancer.enhance_audio(input_path, job_id)
        converted_path = converter.convert_to_optimal_format(enhanced_path, job_id)

        # Phase 2: Multi-pass separation
        progress_callback("Running multi-pass separation", 15)
        separator = MultiPassSeparator()
        stems = separator.separate_audio_multipass(converted_path, job_id, progress_callback)

        return {
            'status': 'separation_complete',
            'stems': {name: str(path) for name, path in stems.items()},
            'job_id': job_id
        }

    except Exception as e:
        self.retry(countdown=60, max_retries=3, exc=e)

@celery_app.task(bind=True, name='app.core.job_scheduler.transcribe_stems')
def transcribe_stems(self, separation_result: Dict, job_id: str) -> Dict:
    """Transcription task (runs after separation)"""
    try:
        job_scheduler.update_job_progress(job_id, 60, "Starting transcription")

        from ..processors.transcription_engine import TranscriptionEngine

        def progress_callback(step: str, progress: float = None):
            current_progress = 60 + (progress or 25)  # 60-85% for transcription
            job_scheduler.update_job_progress(job_id, current_progress, step)

        # Load stems from separation result
        stems = {name: Path(path) for name, path in separation_result['stems'].items()}

        # Transcribe each stem
        transcriber = TranscriptionEngine()
        transcriptions = transcriber.transcribe_multiple_instruments(stems, progress_callback)

        return {
            'status': 'transcription_complete',
            'stems': separation_result['stems'],
            'transcriptions': {
                name: {
                    'midi_path': str(result.midi_path),
                    'confidence': result.confidence_score,
                    'notes': result.notes_detected,
                    'tablature_path': str(result.tablature_path) if result.tablature_path else None,
                    'sheet_music_path': str(result.sheet_music_path) if result.sheet_music_path else None
                }
                for name, result in transcriptions.items()
            },
            'job_id': job_id
        }

    except Exception as e:
        self.retry(countdown=60, max_retries=3, exc=e)

@celery_app.task(bind=True, name='app.core.job_scheduler.finalize_output')
def finalize_output(self, transcription_result: Dict, job_id: str) -> Dict:
    """Final packaging task"""
    try:
        job_scheduler.update_job_progress(job_id, 85, "Creating output package")

        from ..postprocessing.output_formatter import OutputFormatter

        formatter = OutputFormatter()

        def progress_callback(step: str, progress: float = None):
            current_progress = 85 + (progress or 10)  # 85-100%
            job_scheduler.update_job_progress(job_id, current_progress, step)

        # Create final output package
        result_path = formatter.create_output_package(
            job_id,
            transcription_result['stems'],
            transcription_result['transcriptions'],
            progress_callback
        )

        job_scheduler.update_job_progress(job_id, 100, "Processing complete")

        return {
            'status': 'complete',
            'result_path': str(result_path),
            'job_id': job_id
        }

    except Exception as e:
        self.retry(countdown=60, max_retries=3, exc=e)

# Global scheduler instance
job_scheduler = M3JobScheduler()

# Celery signal handlers
@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Handle task start"""
    if len(args) > 0 and isinstance(args[0], str):
        job_id = args[0]
        job_info = job_scheduler.get_job_status(job_id)
        if job_info:
            job_info.status = JobStatus.RUNNING
            job_info.started_at = datetime.utcnow()
            job_scheduler._store_job_info(job_info)

@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    """Handle task completion"""
    if len(args) > 0 and isinstance(args[0], str):
        job_id = args[0]
        job_info = job_scheduler.get_job_status(job_id)
        if job_info and state == 'SUCCESS':
            job_info.status = JobStatus.COMPLETED
            job_info.completed_at = datetime.utcnow()
            if isinstance(retval, dict) and 'result_path' in retval:
                job_info.result_path = retval['result_path']
            job_scheduler._store_job_info(job_info)

@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, args=None, kwargs=None, einfo=None, **kwds):
    """Handle task failure"""
    if len(args) > 0 and isinstance(args[0], str):
        job_id = args[0]
        job_info = job_scheduler.get_job_status(job_id)
        if job_info:
            job_info.status = JobStatus.FAILED
            job_info.error_message = str(exception)
            job_info.completed_at = datetime.utcnow()
            job_scheduler._store_job_info(job_info)
