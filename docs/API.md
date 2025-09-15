# API Documentation - M3 Enhanced

## Overview
The M3 Enhanced API provides endpoints for audio processing, including separation, transcription, and analysis. The API is built with FastAPI and provides both REST endpoints and WebSocket connections for real-time processing updates.

## Base URL
```
http://localhost:8000
```

## Authentication
Currently, the API operates without authentication. For production deployments, implement appropriate security measures.

## Content Types
- **Request**: `multipart/form-data` for file uploads, `application/json` for configuration
- **Response**: `application/json`

## Rate Limiting
- Maximum file size: 100MB
- Concurrent jobs per IP: 5
- Request rate: 100 requests/minute

## Core Endpoints

### Health Check
```http
GET /health
```

**Response**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "models_loaded": true,
  "redis_connected": true,
  "gpu_available": true
}
```

### File Upload and Processing

#### Start Processing Job
```http
POST /process
```

**Parameters**
- `file` (required): Audio file (mp3, wav, flac, m4a)
- `separation_model` (optional): "demucs" | "mvsep" (default: "demucs")
- `transcription_model` (optional): "yourmt3_plus" | "mt3" | "basic_pitch" (default: "yourmt3_plus")
- `enable_classification` (optional): boolean (default: true)
- `quality_analysis` (optional): boolean (default: true)
- `generate_tabs` (optional): boolean (default: true)
- `output_format` (optional): "midi" | "musicxml" | "tab" | "all" (default: "all")

**Example Request**
```bash
curl -X POST "http://localhost:8000/process" \
  -F "file=@song.mp3" \
  -F "separation_model=demucs" \
  -F "transcription_model=yourmt3_plus" \
  -F "enable_classification=true"
```

**Response**
```json
{
  "job_id": "job_1234567890",
  "status": "queued",
  "estimated_duration": 120,
  "websocket_url": "ws://localhost:8000/ws/job_1234567890"
}
```

#### Get Job Status
```http
GET /jobs/{job_id}
```

**Response**
```json
{
  "job_id": "job_1234567890",
  "status": "processing",
  "progress": 45,
  "current_stage": "separation",
  "estimated_remaining": 67,
  "created_at": "2025-09-15T01:00:00Z",
  "started_at": "2025-09-15T01:00:05Z",
  "completed_at": null,
  "error": null
}
```

**Status Values**
- `queued`: Job is waiting to start
- `processing`: Job is currently running
- `completed`: Job finished successfully
- `failed`: Job encountered an error
- `cancelled`: Job was cancelled by user

#### Get Job Results
```http
GET /jobs/{job_id}/results
```

**Response**
```json
{
  "job_id": "job_1234567890",
  "results": {
    "separated_tracks": {
      "vocals": "/results/job_1234567890/vocals.wav",
      "drums": "/results/job_1234567890/drums.wav",
      "bass": "/results/job_1234567890/bass.wav",
      "guitar": "/results/job_1234567890/guitar.wav",
      "lead_guitar": "/results/job_1234567890/lead_guitar.wav",
      "rhythm_guitar": "/results/job_1234567890/rhythm_guitar.wav",
      "other": "/results/job_1234567890/other.wav"
    },
    "transcriptions": {
      "vocals": "/results/job_1234567890/vocals.mid",
      "guitar": "/results/job_1234567890/guitar.mid",
      "bass": "/results/job_1234567890/bass.mid"
    },
    "tablature": {
      "guitar": "/results/job_1234567890/guitar.gp5",
      "bass": "/results/job_1234567890/bass.gp5"
    },
    "sheet_music": {
      "full_score": "/results/job_1234567890/full_score.musicxml"
    },
    "analysis": {
      "key": "C major",
      "tempo": 120,
      "time_signature": "4/4",
      "instruments_detected": ["vocals", "electric_guitar", "bass", "drums"],
      "quality_metrics": {
        "sdr": 12.5,
        "sir": 15.2,
        "sar": 18.7
      }
    }
  },
  "download_url": "/results/job_1234567890/download"
}
```

#### Download Results Package
```http
GET /jobs/{job_id}/download
```

Returns a ZIP file containing all processed results.

#### Cancel Job
```http
DELETE /jobs/{job_id}
```

**Response**
```json
{
  "job_id": "job_1234567890",
  "status": "cancelled",
  "message": "Job cancelled successfully"
}
```

### WebSocket Connection

#### Real-time Job Updates
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/job_1234567890');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Job update:', data);
};
```

**WebSocket Message Format**
```json
{
  "type": "progress",
  "job_id": "job_1234567890",
  "progress": 45,
  "stage": "separation",
  "message": "Separating audio tracks...",
  "timestamp": "2025-09-15T01:05:00Z"
}
```

**Message Types**
- `progress`: Job progress update
- `stage_complete`: Processing stage completed
- `error`: Error occurred
- `complete`: Job finished successfully

### Model Management

#### List Available Models
```http
GET /models
```

**Response**
```json
{
  "separation_models": [
    {
      "name": "demucs",
      "version": "4.0",
      "description": "Facebook Demucs v4 - High quality separation",
      "size": "2.3GB",
      "loaded": true
    },
    {
      "name": "mvsep",
      "version": "23",
      "description": "MVSEP-MDX23 - Ultra high quality",
      "size": "4.1GB",
      "loaded": false
    }
  ],
  "transcription_models": [
    {
      "name": "yourmt3_plus",
      "version": "1.0",
      "description": "Enhanced MT3 with improved accuracy",
      "size": "800MB",
      "loaded": true
    },
    {
      "name": "mt3",
      "version": "1.0",
      "description": "Google MT3 - Multi-track transcription",
      "size": "600MB",
      "loaded": true
    },
    {
      "name": "basic_pitch",
      "version": "0.3",
      "description": "Spotify BasicPitch - Lightweight",
      "size": "200MB",
      "loaded": false
    }
  ]
}
```

#### Load/Unload Models
```http
POST /models/{model_name}/load
DELETE /models/{model_name}/unload
```

### System Information

#### Get System Status
```http
GET /system/status
```

**Response**
```json
{
  "cpu_usage": 45.2,
  "memory_usage": 68.7,
  "gpu_usage": 23.1,
  "gpu_memory": 2048,
  "active_jobs": 3,
  "queue_length": 7,
  "uptime": "2 days, 14:32:18"
}
```

#### Get Processing Queue
```http
GET /queue
```

**Response**
```json
{
  "queue": [
    {
      "job_id": "job_1234567891",
      "position": 1,
      "estimated_start": "2025-09-15T01:10:00Z",
      "file_name": "song2.mp3"
    },
    {
      "job_id": "job_1234567892",
      "position": 2,
      "estimated_start": "2025-09-15T01:12:00Z",
      "file_name": "song3.wav"
    }
  ],
  "active_jobs": [
    {
      "job_id": "job_1234567890",
      "progress": 45,
      "started_at": "2025-09-15T01:00:05Z"
    }
  ]
}
```

## Error Handling

### Error Response Format
```json
{
  "error": {
    "code": "INVALID_FILE_FORMAT",
    "message": "Unsupported audio format. Please use mp3, wav, flac, or m4a.",
    "details": {
      "supported_formats": ["mp3", "wav", "flac", "m4a"],
      "received_format": "avi"
    }
  }
}
```

### Common Error Codes
- `INVALID_FILE_FORMAT`: Unsupported audio format
- `FILE_TOO_LARGE`: File exceeds maximum size limit
- `MODEL_NOT_LOADED`: Requested model is not available
- `INSUFFICIENT_MEMORY`: Not enough system memory for processing
- `GPU_ERROR`: GPU-related processing error
- `PROCESSING_FAILED`: General processing failure
- `JOB_NOT_FOUND`: Invalid job ID
- `RATE_LIMIT_EXCEEDED`: Too many requests

## SDKs and Examples

### Python SDK Example
```python
import requests
import websocket
import json

class M3Client:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    def process_file(self, file_path, **kwargs):
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(f"{self.base_url}/process", 
                                   files=files, data=kwargs)
        return response.json()
    
    def get_job_status(self, job_id):
        response = requests.get(f"{self.base_url}/jobs/{job_id}")
        return response.json()
    
    def download_results(self, job_id, output_path):
        response = requests.get(f"{self.base_url}/jobs/{job_id}/download")
        with open(output_path, 'wb') as f:
            f.write(response.content)

# Usage
client = M3Client()
job = client.process_file("song.mp3", separation_model="demucs")
print(f"Job started: {job['job_id']}")
```

### JavaScript Example
```javascript
class M3Client {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
    }
    
    async processFile(file, options = {}) {
        const formData = new FormData();
        formData.append('file', file);
        
        Object.entries(options).forEach(([key, value]) => {
            formData.append(key, value);
        });
        
        const response = await fetch(`${this.baseUrl}/process`, {
            method: 'POST',
            body: formData
        });
        
        return response.json();
    }
    
    async getJobStatus(jobId) {
        const response = await fetch(`${this.baseUrl}/jobs/${jobId}`);
        return response.json();
    }
    
    connectWebSocket(jobId, onMessage) {
        const ws = new WebSocket(`${this.baseUrl.replace('http', 'ws')}/ws/${jobId}`);
        ws.onmessage = (event) => onMessage(JSON.parse(event.data));
        return ws;
    }
}

// Usage
const client = new M3Client();
const job = await client.processFile(fileInput.files[0], {
    separation_model: 'demucs',
    transcription_model: 'yourmt3_plus'
});
```

## Performance Considerations

### Optimization Tips
1. **Batch Processing**: Submit multiple files for better resource utilization
2. **Model Preloading**: Load frequently used models in advance
3. **GPU Utilization**: Use GPU-enabled models for faster processing
4. **Caching**: Results are cached for 24 hours by default
5. **Compression**: Enable gzip compression for large downloads

### Processing Time Estimates
- **3-minute song**: 1-3 minutes (with GPU)
- **3-minute song**: 3-8 minutes (CPU only)
- **Model loading**: 10-30 seconds first time
- **File upload**: Depends on file size and connection speed

The API is designed for high throughput and can handle multiple concurrent processing jobs efficiently.
