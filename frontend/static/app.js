// M3 Enhanced - Advanced Audio Processing Web Application
class M3App {
    constructor() {
        this.baseURL = window.location.origin;
        this.currentSection = 'upload';
        this.jobPollingInterval = null;
        this.notifications = [];

        this.init();
    }

    init() {
        this.bindEvents();
        this.checkSystemStatus();
        this.loadJobHistory();
        this.setupDragAndDrop();
    }

    bindEvents() {
        // Navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const section = link.getAttribute('href').substring(1);
                this.switchSection(section);
            });
        });

        // File upload
        const fileInput = document.getElementById('fileInput');
        const uploadZone = document.getElementById('uploadZone');

        uploadZone.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', (e) => this.handleFileSelect(e.target.files[0]));

        // Processing controls
        const startBtn = document.getElementById('startProcessing');
        if (startBtn) {
            startBtn.addEventListener('click', () => this.startProcessing());
        }

        // System status modal
        const statusBtn = document.getElementById('systemStatus');
        const statusModal = document.getElementById('systemStatusModal');
        const closeStatusBtn = document.getElementById('closeStatusModal');

        if (statusBtn) statusBtn.addEventListener('click', () => this.showSystemStatus());
        if (closeStatusBtn) closeStatusBtn.addEventListener('click', () => this.hideModal('systemStatusModal'));

        // Job filters
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.filterJobs(e.target.dataset.filter));
        });

        // Modal close on backdrop click
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.hideModal(modal.id);
                }
            });
        });
    }

    setupDragAndDrop() {
        const uploadZone = document.getElementById('uploadZone');

        uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadZone.classList.add('dragover');
        });

        uploadZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('dragover');
        });

        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('dragover');

            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleFileSelect(files[0]);
            }
        });
    }

    switchSection(sectionName) {
        // Update navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });
        document.querySelector(`[href="#${sectionName}"]`).classList.add('active');

        // Update sections
        document.querySelectorAll('.section').forEach(section => {
            section.classList.remove('active');
        });
        document.getElementById(`${sectionName}-section`).classList.add('active');

        this.currentSection = sectionName;

        // Load section-specific data
        if (sectionName === 'jobs') {
            this.loadJobs();
        } else if (sectionName === 'results') {
            this.loadResults();
        }
    }

    handleFileSelect(file) {
        if (!file) return;

        // Validate file type
        const allowedTypes = ['audio/mpeg', 'audio/wav', 'audio/flac', 'audio/m4a', 'audio/aac', 'audio/ogg'];
        if (!allowedTypes.includes(file.type) && !this.isAudioFile(file.name)) {
            this.showNotification('Please select a valid audio file (MP3, WAV, FLAC, M4A, AAC, OGG)', 'error');
            return;
        }

        // Validate file size (100MB limit)
        const maxSize = 100 * 1024 * 1024;
        if (file.size > maxSize) {
            this.showNotification('File size must be less than 100MB', 'error');
            return;
        }

        // Show processing options
        document.getElementById('processingOptions').style.display = 'block';

        // Update upload zone
        const uploadZone = document.getElementById('uploadZone');
        uploadZone.innerHTML = `
            <div class="upload-icon">
                <i class="fas fa-file-audio" style="color: var(--success-color);"></i>
            </div>
            <h3>${file.name}</h3>
            <p>File size: ${this.formatFileSize(file.size)}</p>
            <p>Duration: Analyzing...</p>
        `;

        this.selectedFile = file;
        this.analyzeAudioFile(file);
    }

    isAudioFile(filename) {
        const audioExtensions = ['.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg', '.wma'];
        return audioExtensions.some(ext => filename.toLowerCase().endsWith(ext));
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    async analyzeAudioFile(file) {
        try {
            const audio = new Audio();
            const url = URL.createObjectURL(file);

            audio.addEventListener('loadedmetadata', () => {
                const duration = Math.floor(audio.duration);
                const minutes = Math.floor(duration / 60);
                const seconds = duration % 60;

                document.querySelector('#uploadZone p:last-child').textContent =
                    `Duration: ${minutes}:${seconds.toString().padStart(2, '0')}`;

                URL.revokeObjectURL(url);
            });

            audio.src = url;
        } catch (error) {
            console.error('Error analyzing audio file:', error);
        }
    }

    async startProcessing() {
        if (!this.selectedFile) {
            this.showNotification('Please select an audio file first', 'error');
            return;
        }

        // Collect processing options
        const options = {
            mode: document.getElementById('processingMode').value,
            instruments: {
                vocals: document.getElementById('vocals').checked,
                guitar: document.getElementById('guitar').checked,
                bass: document.getElementById('bass').checked,
                drums: document.getElementById('drums').checked,
                piano: document.getElementById('piano').checked,
                other: document.getElementById('other').checked
            },
            outputs: {
                wav: document.getElementById('outputWav').checked,
                flac: document.getElementById('outputFlac').checked,
                mp3: document.getElementById('outputMp3').checked,
                midi: document.getElementById('outputMidi').checked,
                tabs: document.getElementById('outputTabs').checked,
                sheet: document.getElementById('outputSheet').checked
            }
        };

        try {
            // Show processing modal
            this.showModal('processingModal');

            // Upload file and start processing
            const jobId = await this.uploadAndProcess(this.selectedFile, options);

            // Update modal with job ID
            document.getElementById('jobId').textContent = jobId;

            // Start polling for progress
            this.startJobPolling(jobId);

            this.showNotification('Processing started successfully', 'success');

        } catch (error) {
            console.error('Processing error:', error);
            this.showNotification('Failed to start processing: ' + error.message, 'error');
            this.hideModal('processingModal');
        }
    }

    async uploadAndProcess(file, options) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('options', JSON.stringify(options));

        const response = await fetch(`${this.baseURL}/upload`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`Upload failed: ${response.statusText}`);
        }

        const result = await response.json();
        return result.job_id;
    }

    startJobPolling(jobId) {
        this.jobPollingInterval = setInterval(async () => {
            try {
                const status = await this.getJobStatus(jobId);
                this.updateProcessingModal(status);

                if (status.state === 'SUCCESS' || status.state === 'FAILURE') {
                    clearInterval(this.jobPollingInterval);

                    if (status.state === 'SUCCESS') {
                        this.handleProcessingComplete(jobId);
                    } else {
                        this.handleProcessingFailure(status.info);
                    }
                }
            } catch (error) {
                console.error('Polling error:', error);
            }
        }, 2000);
    }

    async getJobStatus(jobId) {
        const response = await fetch(`${this.baseURL}/jobs/${jobId}/status`);
        if (!response.ok) {
            throw new Error(`Failed to get job status: ${response.statusText}`);
        }
        return await response.json();
    }

    updateProcessingModal(status) {
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');
        const currentStep = document.getElementById('currentStep');
        const estimatedTime = document.getElementById('estimatedTime');

        // Update progress bar
        const progress = status.progress || 0;
        progressFill.style.width = `${progress}%`;
        progressText.textContent = `${Math.round(progress)}%`;

        // Update current step
        if (status.current_step) {
            currentStep.textContent = status.current_step;
        }

        // Update estimated time
        if (status.estimated_time_remaining) {
            estimatedTime.textContent = status.estimated_time_remaining;
        }

        // Update step indicators
        this.updateStepIndicators(status.completed_steps || []);
    }

    updateStepIndicators(completedSteps) {
        const steps = document.querySelectorAll('.step');
        steps.forEach((step, index) => {
            const indicator = step.querySelector('.step-status');

            if (completedSteps.includes(index)) {
                indicator.className = 'step-status completed';
            } else if (completedSteps.length === index) {
                indicator.className = 'step-status active';
            } else {
                indicator.className = 'step-status pending';
            }
        });
    }

    handleProcessingComplete(jobId) {
        this.hideModal('processingModal');
        this.showNotification('Processing completed successfully!', 'success');

        // Switch to results section
        this.switchSection('results');
        this.loadResults();
    }

    handleProcessingFailure(errorInfo) {
        this.hideModal('processingModal');
        this.showNotification(`Processing failed: ${errorInfo}`, 'error');
    }

    async loadJobs() {
        try {
            const response = await fetch(`${this.baseURL}/jobs`);
            const jobs = await response.json();
            this.renderJobs(jobs);
        } catch (error) {
            console.error('Failed to load jobs:', error);
            this.showNotification('Failed to load jobs', 'error');
        }
    }

    renderJobs(jobs) {
        const jobsList = document.getElementById('jobsList');

        if (jobs.length === 0) {
            jobsList.innerHTML = '<p style="text-align: center; color: var(--text-secondary);">No jobs found</p>';
            return;
        }

        jobsList.innerHTML = jobs.map(job => `
            <div class="job-card" data-status="${job.status}">
                <div class="job-header">
                    <h3 class="job-title">${job.filename}</h3>
                    <span class="job-status ${job.status}">${job.status}</span>
                </div>
                <div class="job-progress">
                    <div class="progress-container">
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${job.progress || 0}%"></div>
                        </div>
                        <div class="progress-text">${Math.round(job.progress || 0)}%</div>
                    </div>
                </div>
                <div class="job-details">
                    <p><strong>Job ID:</strong> ${job.id}</p>
                    <p><strong>Created:</strong> ${new Date(job.created_at).toLocaleString()}</p>
                    ${job.completed_at ? `<p><strong>Completed:</strong> ${new Date(job.completed_at).toLocaleString()}</p>` : ''}
                </div>
                ${job.status === 'completed' ? `
                    <div class="job-actions">
                        <button class="btn btn-primary" onclick="app.downloadResults('${job.id}')">
                            <i class="fas fa-download"></i> Download Results
                        </button>
                    </div>
                ` : ''}
            </div>
        `).join('');
    }

    filterJobs(filter) {
        // Update filter buttons
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-filter="${filter}"]`).classList.add('active');

        // Filter job cards
        const jobCards = document.querySelectorAll('.job-card');
        jobCards.forEach(card => {
            const status = card.dataset.status;
            if (filter === 'all' || status === filter) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        });
    }

    async loadResults() {
        try {
            const response = await fetch(`${this.baseURL}/results`);
            const results = await response.json();
            this.renderResults(results);
        } catch (error) {
            console.error('Failed to load results:', error);
            this.showNotification('Failed to load results', 'error');
        }
    }

    renderResults(results) {
        const resultsContainer = document.getElementById('resultsContainer');

        if (results.length === 0) {
            resultsContainer.innerHTML = '<p style="text-align: center; color: var(--text-secondary);">No results available</p>';
            return;
        }

        resultsContainer.innerHTML = results.map(result => `
            <div class="result-card">
                <div class="result-header">
                    <h3>${result.filename}</h3>
                    <span class="result-date">${new Date(result.created_at).toLocaleDateString()}</span>
                </div>
                <div class="result-content">
                    <div class="result-stats">
                        <div class="stat">
                            <span class="stat-label">Stems Generated:</span>
                            <span class="stat-value">${result.stems_count}</span>
                        </div>
                        <div class="stat">
                            <span class="stat-label">Processing Time:</span>
                            <span class="stat-value">${result.processing_time}</span>
                        </div>
                        <div class="stat">
                            <span class="stat-label">Quality Score:</span>
                            <span class="stat-value">${result.quality_score}/10</span>
                        </div>
                    </div>
                    <div class="result-actions">
                        <button class="btn btn-primary" onclick="app.downloadResults('${result.job_id}')">
                            <i class="fas fa-download"></i> Download All
                        </button>
                        <button class="btn btn-secondary" onclick="app.previewResults('${result.job_id}')">
                            <i class="fas fa-eye"></i> Preview
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
    }

    async downloadResults(jobId) {
        try {
            const response = await fetch(`${this.baseURL}/jobs/${jobId}/results`);
            if (!response.ok) {
                throw new Error('Download failed');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `m3_results_${jobId}.zip`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            this.showNotification('Download started', 'success');
        } catch (error) {
            console.error('Download error:', error);
            this.showNotification('Download failed', 'error');
        }
    }

    async showSystemStatus() {
        try {
            const response = await fetch(`${this.baseURL}/system/status`);
            const status = await response.json();

            const content = document.getElementById('systemStatusContent');
            content.innerHTML = `
                <div class="status-grid">
                    <div class="status-item">
                        <div class="status-label">CPU Usage</div>
                        <div class="status-value">${status.cpu_usage}%</div>
                        <div class="status-bar">
                            <div class="status-fill" style="width: ${status.cpu_usage}%"></div>
                        </div>
                    </div>
                    <div class="status-item">
                        <div class="status-label">Memory Usage</div>
                        <div class="status-value">${status.memory_usage}%</div>
                        <div class="status-bar">
                            <div class="status-fill" style="width: ${status.memory_usage}%"></div>
                        </div>
                    </div>
                    <div class="status-item">
                        <div class="status-label">GPU Usage</div>
                        <div class="status-value">${status.gpu_usage || 'N/A'}</div>
                        <div class="status-bar">
                            <div class="status-fill" style="width: ${status.gpu_usage || 0}%"></div>
                        </div>
                    </div>
                    <div class="status-item">
                        <div class="status-label">Active Jobs</div>
                        <div class="status-value">${status.active_jobs}</div>
                    </div>
                    <div class="status-item">
                        <div class="status-label">Queue Length</div>
                        <div class="status-value">${status.queue_length}</div>
                    </div>
                    <div class="status-item">
                        <div class="status-label">Models Loaded</div>
                        <div class="status-value">${status.models_loaded}</div>
                    </div>
                </div>
            `;

            this.showModal('systemStatusModal');
        } catch (error) {
            console.error('Failed to get system status:', error);
            this.showNotification('Failed to get system status', 'error');
        }
    }

    async checkSystemStatus() {
        try {
            const response = await fetch(`${this.baseURL}/health`);
            const status = response.ok;

            // Update UI to show system status
            if (!status) {
                this.showNotification('System is offline', 'error');
            }
        } catch (error) {
            console.error('Health check failed:', error);
        }
    }

    loadJobHistory() {
        // Load any saved job history from localStorage
        const savedJobs = localStorage.getItem('m3_job_history');
        if (savedJobs) {
            try {
                this.jobHistory = JSON.parse(savedJobs);
            } catch (error) {
                console.error('Failed to parse job history:', error);
                this.jobHistory = [];
            }
        } else {
            this.jobHistory = [];
        }
    }

    showModal(modalId) {
        document.getElementById(modalId).classList.add('active');
    }

    hideModal(modalId) {
        document.getElementById(modalId).classList.remove('active');
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <div class="notification-message">${message}</div>
                <button class="notification-close" onclick="this.parentElement.parentElement.remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;

        document.getElementById('notifications').appendChild(notification);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }
}

// Initialize the application
const app = new M3App();

// Expose app instance globally for debugging
window.app = app;
