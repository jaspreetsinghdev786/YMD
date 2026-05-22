/**
 * Queue Manager - Real-time Download Queue System
 * Handles fetching, displaying, and managing active downloads
 */

class QueueManager {
    constructor() {
        this.queueContainer = null;
        this.queueCountBadge = null;
        this.pollingInterval = null;
        this.isPolling = false;
        this.lastQueueData = null;
        this.POLL_INTERVAL = 2000; // 2 seconds
        this.trackedDownloads = new Map(); // Track downloads for auto-download detection
        this.autoDownloadEnabled = true; // Enable auto-download on completion
    }

    /**
     * Initialize the queue system
     */
    init() {
        // Find DOM elements
        this.queueContainer = document.querySelector('#queue-container');
        this.queueCountBadge = document.querySelector('#queue-count-badge');

        if (!this.queueContainer) {
            console.warn('Queue container not found');
            return;
        }

        // Start polling
        this.startPolling();

        // Handle page visibility (pause when hidden)
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.stopPolling();
            } else {
                this.startPolling();
            }
        });

        console.log('✅ Queue Manager initialized');
    }

    /**
     * Start polling for queue updates
     */
    startPolling() {
        if (this.isPolling) return;

        this.isPolling = true;
        this.fetchQueue(); // Immediate first fetch

        this.pollingInterval = setInterval(() => {
            this.fetchQueue();
        }, this.POLL_INTERVAL);

        console.log('🔄 Queue polling started');
    }

    /**
     * Stop polling
     */
    stopPolling() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
        this.isPolling = false;
        console.log('⏸️ Queue polling stopped');
    }

    /**
     * Fetch queue data from API
     */
    async fetchQueue() {
        try {
            const response = await fetch('/api/downloads/queue/', {
                method: 'GET',
                credentials: 'same-origin', // Include session cookie
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (response.status === 401 || response.status === 403) {
                // Unauthorized - redirect to login
                console.error('❌ Authentication failed');
                window.location.href = '/accounts/login/';
                return;
            }

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            this.updateQueue(data);

        } catch (error) {
            console.error('❌ Failed to fetch queue:', error);
            this.showError('Failed to load queue. Retrying...');
        }
    }

    /**
     * Update queue UI with new data
     */
    updateQueue(data) {
        const { count, queue } = data;

        // Update count badge
        if (this.queueCountBadge) {
            this.queueCountBadge.textContent = count;
            this.queueCountBadge.style.display = count > 0 ? 'inline' : 'none';
        }

        // Clear error state
        this.clearError();

        // Check for downloads that disappeared from queue (might be completed)
        this.checkForCompletedDownloads(queue);

        // Track current queue items
        this.updateTrackedDownloads(queue);

        // Render queue items
        if (count === 0) {
            this.renderEmptyState();
        } else {
            this.renderQueueItems(queue);
        }

        // Stop polling if queue is empty and no tracked downloads
        if (count === 0 && this.trackedDownloads.size === 0 && this.lastQueueData && this.lastQueueData.count > 0) {
            console.log('✅ Queue is now empty - stopping polling');
            // Keep polling for 10 more seconds in case new items are added
            setTimeout(() => {
                if (this.lastQueueData && this.lastQueueData.count === 0 && this.trackedDownloads.size === 0) {
                    this.stopPolling();
                }
            }, 10000);
        }

        this.lastQueueData = data;
    }

    /**
     * Track current queue items for completion detection
     */
    updateTrackedDownloads(queue) {
        queue.forEach(item => {
            if (!this.trackedDownloads.has(item.id)) {
                // New item in queue, start tracking
                this.trackedDownloads.set(item.id, {
                    id: item.id,
                    title: item.title || 'Unknown',
                    status: item.status,
                    lastSeen: Date.now()
                });
                console.log(`🔍 Tracking download: ${item.id} - ${item.title}`);
            } else {
                // Update existing tracked item
                const tracked = this.trackedDownloads.get(item.id);
                tracked.status = item.status;
                tracked.lastSeen = Date.now();
                tracked.title = item.title || tracked.title;
            }
        });
    }

    /**
     * Check for downloads that disappeared from queue (completed or failed)
     */
    async checkForCompletedDownloads(currentQueue) {
        if (!this.autoDownloadEnabled) return;

        const currentIds = new Set(currentQueue.map(item => item.id));
        
        // Check each tracked download
        for (const [downloadId, tracked] of this.trackedDownloads.entries()) {
            // If download was in queue but now gone, check its final status
            if (!currentIds.has(downloadId) && 
                (tracked.status === 'downloading' || tracked.status === 'queued')) {
                
                console.log(`🔍 Download ${downloadId} disappeared from queue, checking status...`);
                
                // Fetch the actual status
                await this.checkDownloadStatusAndAutoDownload(downloadId, tracked.title);
                
                // Remove from tracking
                this.trackedDownloads.delete(downloadId);
            }
        }
    }

    /**
     * Check download status and trigger auto-download if completed
     */
    async checkDownloadStatusAndAutoDownload(downloadId, title) {
        // Use shared global Set to prevent duplicate downloads
        if (!window._downloadedFileIds) {
            window._downloadedFileIds = new Set();
        }
        
        // Skip if already downloaded
        if (window._downloadedFileIds.has(downloadId)) {
            console.log(`⏭️ Download ${downloadId} already auto-downloaded, skipping`);
            return;
        }

        try {
            const response = await fetch(`/api/downloads/status/${downloadId}/`, {
                method: 'GET',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (!response.ok) {
                console.error(`❌ Failed to get status for download ${downloadId}`);
                return;
            }

            const data = await response.json();
            console.log(`📊 Download ${downloadId} final status: ${data.status}`);

            if (data.status === 'completed') {
                console.log(`✅ Download completed: ${title}`);
                
                // Show notification
                this.showSuccess(`Download complete: ${title}`);
                
                // Trigger automatic file download (will check for duplicates internally)
                this.triggerAutoDownload(downloadId, title);
                
            } else if (data.status === 'failed' || data.status === 'error') {
                console.error(`❌ Download ${downloadId} failed:`, data.error);
                this.showError(`Download failed: ${title}`);
            }

        } catch (error) {
            console.error(`❌ Error checking status for download ${downloadId}:`, error);
        }
    }

    /**
     * Trigger automatic file download when download completes
     */
    triggerAutoDownload(id, title) {
        // Use shared global Set to prevent duplicate downloads across scripts
        if (!window._downloadedFileIds) {
            window._downloadedFileIds = new Set();
        }
        
        // Check if already downloaded
        if (window._downloadedFileIds.has(id)) {
            console.log(`⏭️ File ${id} already downloaded, skipping (queue-manager)`);
            return;
        }
        
        // Mark as downloaded immediately to prevent race conditions
        window._downloadedFileIds.add(id);
        
        try {
            console.log(`📥 Auto-downloading file for ID: ${id}`);
            
            // Create hidden link and trigger download
            const link = document.createElement('a');
            link.href = `/api/downloads/file/${id}/`;
            link.style.display = 'none';
            link.download = title || 'download'; // Suggest filename
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            console.log(`✅ Auto-download triggered for: ${title}`);
        } catch (error) {
            console.error('❌ Auto-download failed:', error);
            // Remove from set so user can retry
            window._downloadedFileIds.delete(id);
            this.showError(`Failed to auto-download: ${title}`);
        }
    }

    /**
     * Render queue items
     */
    renderQueueItems(queue) {
        if (!this.queueContainer) return;

        const html = queue.map(item => this.createQueueItemHTML(item)).join('');
        this.queueContainer.innerHTML = html;

        // Attach event listeners
        this.attachEventListeners();
    }

    /**
     * Create HTML for a single queue item
     */
    createQueueItemHTML(item) {
        const {
            id,
            title,
            status,
            progress,
            format,
            quality,
            channel_name,
            duration
        } = item;

        // Status text mapping
        const statusMap = {
            'queued': 'Waiting...',
            'downloading': 'Downloading...',
            'completed': 'Complete ✓',
            'failed': 'Failed ✗'
        };

        const statusText = statusMap[status] || status;
        const isCompleted = status === 'completed';
        const isFailed = status === 'failed';

        // Format badge
        const formatBadge = `${format.toUpperCase()} ${quality.toUpperCase()}${format === 'mp4' && !isNaN(quality) ? 'P' : ''}`;

        // Opacity class for completed/failed items
        const opacityClass = (isCompleted || isFailed) ? 'opacity-60 hover:opacity-100' : '';

        return `
            <div class="flex flex-col gap-2 p-3 bg-neutral-50 dark:bg-neutral-800/50 border border-neutral-200 dark:border-neutral-700 ${opacityClass} transition-opacity" data-queue-id="${id}">
                <!-- Header -->
                <div class="flex justify-between items-start gap-2">
                    <div class="flex-1 min-w-0">
                        <h4 class="font-bold text-sm line-clamp-2 leading-tight ${isCompleted ? 'line-through decoration-2' : ''}">
                            ${this.escapeHtml(title)}
                        </h4>
                        ${channel_name ? `
                            <p class="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">
                                ${this.escapeHtml(channel_name)}
                            </p>
                        ` : ''}
                    </div>
                    <button class="delete-btn text-${isFailed ? 'neutral-400' : 'primary'} hover:text-black dark:hover:text-white transition-colors" data-id="${id}">
                        <span class="material-symbols-outlined text-[20px] font-bold">${isCompleted || isFailed ? 'delete' : 'close'}</span>
                    </button>
                </div>

                <!-- Status Bar -->
                <div class="flex items-center justify-between text-xs font-mono mb-1">
                    <span class="text-neutral-600 dark:text-neutral-400 font-medium">${statusText}</span>
                    <div class="flex items-center gap-2">
                        <span class="px-2 py-0.5 bg-black dark:bg-white text-white dark:text-black text-[10px] font-bold uppercase">${formatBadge}</span>
                        <span class="text-neutral-600 dark:text-neutral-400 font-bold">${progress}%</span>
                    </div>
                </div>

                <!-- Progress Bar -->
                <div class="w-full h-2 bg-black/10 dark:bg-white/20 overflow-hidden">
                    <div class="h-full bg-primary transition-all duration-300 ease-out" style="width: ${progress}%"></div>
                </div>

                <!-- Actions (for completed items) -->
                ${isCompleted ? `
                    <button class="download-btn mt-2 w-full h-10 brutal-border dark:border-white bg-black dark:bg-white text-white dark:text-black font-bold text-sm uppercase tracking-wide hover:bg-primary dark:hover:bg-primary hover:text-white dark:hover:text-white transition-all" data-id="${id}">
                        <span class="material-symbols-outlined text-[18px] align-middle mr-1">download</span>
                        Download File
                    </button>
                ` : ''}

                ${isFailed ? `
                    <p class="text-xs text-red-600 dark:text-red-400 mt-1 font-medium">
                        Download failed. Please try again.
                    </p>
                ` : ''}
            </div>
        `;
    }

    /**
     * Render empty state
     */
    renderEmptyState() {
        if (!this.queueContainer) return;

        this.queueContainer.innerHTML = `
            <div class="flex flex-col items-center justify-center py-12 text-center">
                <span class="material-symbols-outlined text-6xl text-neutral-300 dark:text-neutral-700 mb-4">queue_music</span>
                <p class="text-sm font-bold uppercase text-neutral-400 dark:text-neutral-600">No active downloads</p>
                <p class="text-xs text-neutral-400 dark:text-neutral-600 mt-1">Your queue is empty</p>
            </div>
        `;
    }

    /**
     * Attach event listeners to buttons
     */
    attachEventListeners() {
        // Delete buttons
        document.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = parseInt(btn.dataset.id);
                this.handleDelete(id);
            });
        });

        // Download buttons
        document.querySelectorAll('.download-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = parseInt(btn.dataset.id);
                this.handleDownload(id);
            });
        });
    }

    /**
     * Handle file download
     */
    async handleDownload(id) {
        try {
            console.log(`📥 Downloading file for ID: ${id}`);

            // Create hidden link and trigger download
            const link = document.createElement('a');
            link.href = `/api/downloads/file/${id}/`;
            link.style.display = 'none';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);

            this.showSuccess('Download started!');

        } catch (error) {
            console.error('❌ Download failed:', error);
            this.showError('Failed to download file');
        }
    }

    /**
     * Handle delete with confirmation
     */
    async handleDelete(id) {
        // Find the item to get its title
        const item = this.lastQueueData?.queue.find(q => q.id === id);
        const title = item ? item.title : 'this download';

        // Show confirmation modal
        if (!confirm(`Delete "${title}"?\n\nThis will remove the download from queue and delete the file if completed.`)) {
            return;
        }

        try {
            console.log(`🗑️ Deleting download ID: ${id}`);

            const response = await fetch(`/api/downloads/delete/${id}/`, {
                method: 'DELETE',
                credentials: 'same-origin',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                    'Content-Type': 'application/json',
                }
            });

            if (response.status === 401 || response.status === 403) {
                console.error('❌ Authentication failed');
                window.location.href = '/accounts/login/';
                return;
            }

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            // Remove item from UI immediately
            const itemElement = document.querySelector(`[data-queue-id="${id}"]`);
            if (itemElement) {
                itemElement.style.opacity = '0';
                itemElement.style.transform = 'translateX(20px)';
                setTimeout(() => {
                    itemElement.remove();
                    // Fetch updated queue
                    this.fetchQueue();
                }, 300);
            }

            this.showSuccess('Download deleted');

        } catch (error) {
            console.error('❌ Delete failed:', error);
            this.showError('Failed to delete download');
        }
    }

    /**
     * Get CSRF token from cookies
     */
    getCSRFToken() {
        const name = 'csrftoken';
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [key, value] = cookie.trim().split('=');
            if (key === name) {
                return decodeURIComponent(value);
            }
        }
        return '';
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Show error message
     */
    showError(message) {
        console.error('❌', message);
        if (window.toast) {
            window.toast.error(message);
        }
    }

    /**
     * Clear error message
     */
    clearError() {
        // Error toasts auto-dismiss
    }

    /**
     * Show success message
     */
    showSuccess(message) {
        console.log('✅', message);
        if (window.toast) {
            window.toast.success(message);
        }
    }

    /**
     * Cleanup and destroy
     */
    destroy() {
        this.stopPolling();
        console.log('🛑 Queue Manager destroyed');
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    const queueManager = new QueueManager();
    queueManager.init();

    // Expose globally for debugging
    window.queueManager = queueManager;
});