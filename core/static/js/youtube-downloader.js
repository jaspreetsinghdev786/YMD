// youtube-downloader.js

class YouTubeDownloader {
    constructor() {
        this.videoData = null;
        this.videoId = null;
        this.videoUrl = null;
        this.apiBaseUrl = '/api';
        this.accessToken = null;
        this.csrfToken = null;
        this.activeDownloads = new Map(); // Track downloads for auto-download
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.fetchCSRFToken();
        this.checkAuthentication();
        this.loadInitialData();
    }

    // Get CSRF token from cookie as fallback
    getCsrfTokenFromCookie() {
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Check authentication status
    async checkAuthentication() {
        try {
            const authStatus = await this.checkAuthStatus();
            if (!authStatus.authenticated) {
                console.warn('User not authenticated');
                this.handleUnauthenticated();
            } else {
                console.log('User authenticated:', authStatus.user);
            }
        } catch (error) {
            console.error('Authentication check failed:', error);
        }
    }

    // Fetch CSRF token from API
    async fetchCSRFToken() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/accounts/csrf-token/`, {
                method: 'GET',
                credentials: 'include',
                headers: {
                    'Accept': 'application/json'
                }
            });

            if (response.ok) {
                const data = await response.json();
                this.csrfToken = data.csrfToken || data.csrf_token || data.token;
                console.log('✅ CSRF token fetched from API');
            } else {
                console.warn('Failed to fetch CSRF token from API, trying cookie fallback...');
                this.csrfToken = this.getCsrfTokenFromCookie();
                if (this.csrfToken) {
                    console.log('✅ CSRF token retrieved from cookie');
                } else {
                    console.error('❌ No CSRF token available');
                }
            }
        } catch (error) {
            console.error('Error fetching CSRF token:', error);
            // Fallback to cookie
            this.csrfToken = this.getCsrfTokenFromCookie();
            if (this.csrfToken) {
                console.log('✅ CSRF token retrieved from cookie (fallback)');
            }
        }
    }

    // Auth status check with token refresh
    async checkAuthStatus() {
        try {
            console.log('🔍 Checking auth status...');
            const response = await fetch(`${this.apiBaseUrl}/accounts/auth/status/`, {
                method: 'GET',
                credentials: 'include',
                headers: {
                    'Accept': 'application/json',
                    ...(this.accessToken && { 'Authorization': `Bearer ${this.accessToken}` })
                }
            });

            console.log(`Auth status response: ${response.status}`);

            if (response.status === 401) {
                console.log('🔄 Access token expired, attempting refresh...');
                const refreshed = await this.refreshAccessToken();

                if (refreshed) {
                    console.log('🔄 Retrying auth status check...');
                    const retryResponse = await fetch(`${this.apiBaseUrl}/accounts/auth/status/`, {
                        method: 'GET',
                        credentials: 'include',
                        headers: {
                            'Accept': 'application/json',
                            ...(this.accessToken && { 'Authorization': `Bearer ${this.accessToken}` })
                        }
                    });

                    if (retryResponse.ok) {
                        const data = await retryResponse.json();
                        console.log('✅ Auth successful after refresh:', data);
                        return { authenticated: true, user: data.user };
                    }
                }
                return { authenticated: false, status: 401 };
            }

            if (response.status === 403) {
                console.log('🚫 Access forbidden (403)');
                return { authenticated: false, status: 403 };
            }

            if (response.ok) {
                const data = await response.json();
                console.log('✅ Auth check successful:', data);
                return { authenticated: true, user: data.user };
            }

            console.error(`❌ Auth check failed with status: ${response.status}`);
            return { authenticated: false, status: response.status };
        } catch (error) {
            console.error('❌ Auth status check network error:', error);
            return { authenticated: false, error: error.message };
        }
    }

    // Refresh access token
    async refreshAccessToken() {
        try {
            console.log('🔄 Attempting to refresh access token...');
            const response = await fetch(`${this.apiBaseUrl}/accounts/refresh/`, {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            });

            console.log(`Refresh token response: ${response.status}`);

            if (response.ok) {
                const data = await response.json();
                if (data.access) {
                    this.accessToken = data.access;
                    console.log('✅ Access token refreshed and stored');
                } else {
                    console.log('✅ Access token refreshed (cookie-based)');
                }
                return true;
            } else {
                const errorText = await response.text();
                console.error('❌ Token refresh failed:', response.status, errorText);
                return false;
            }
        } catch (error) {
            console.error('❌ Token refresh network error:', error);
            return false;
        }
    }

    // Handle unauthenticated state
    handleUnauthenticated() {
        sessionStorage.setItem('redirectUrl', window.location.pathname);
        console.log('➡️  Redirecting to login...');
        window.location.href = '/login/';
    }

    // Authenticated fetch wrapper with proper error handling
    async authenticatedFetch(url, options = {}) {
        // Ensure we have CSRF token
        if (!this.csrfToken) {
            console.log('⚠️  No CSRF token, fetching...');
            await this.fetchCSRFToken();
        }

        // If still no CSRF token, try cookie fallback one more time
        if (!this.csrfToken) {
            this.csrfToken = this.getCsrfTokenFromCookie();
        }

        // Build headers with proper merging
        const headers = {
            'Accept': 'application/json',
            ...(options.method !== 'GET' && { 'Content-Type': 'application/json' }),
            ...(this.csrfToken && { 'X-CSRFToken': this.csrfToken }),
            ...(this.accessToken && { 'Authorization': `Bearer ${this.accessToken}` }),
            ...(options.headers || {})
        };

        const fetchOptions = {
            ...options,
            credentials: 'include',
            headers: headers
        };

        try {
            console.log('\n═══════════════════════════════════');
            console.log('📤 Authenticated Request');
            console.log('═══════════════════════════════════');
            console.log('URL:', url);
            console.log('Method:', fetchOptions.method || 'GET');
            console.log('Headers:', JSON.stringify(headers, null, 2));
            console.log('CSRF Token:', this.csrfToken ? '✓ Present' : '✗ Missing');
            console.log('Access Token:', this.accessToken ? '✓ Present' : '✗ Not set');
            console.log('Cookies:', document.cookie || 'None');

            if (fetchOptions.body) {
                console.log('Body Type:', typeof fetchOptions.body);
                console.log('Body Content:', fetchOptions.body);
                console.log('Body Length:', fetchOptions.body.length, 'characters');

                // Validate JSON
                try {
                    JSON.parse(fetchOptions.body);
                    console.log('Body JSON:', '✓ Valid');
                } catch (e) {
                    console.error('Body JSON:', '✗ Invalid -', e.message);
                }
            }
            console.log('═══════════════════════════════════\n');

            let response = await fetch(url, fetchOptions);
            console.log(`📥 Response Status: ${response.status} ${response.statusText}`);

            // Handle 401 - Unauthorized (token expired)
            if (response.status === 401) {
                console.log('🔄 Request unauthorized (401), attempting token refresh...');
                const refreshed = await this.refreshAccessToken();

                if (refreshed) {
                    console.log('🔄 Token refreshed, retrying original request...');

                    // Rebuild headers with new token
                    const retryHeaders = {
                        'Accept': 'application/json',
                        ...(options.method !== 'GET' && { 'Content-Type': 'application/json' }),
                        ...(this.csrfToken && { 'X-CSRFToken': this.csrfToken }),
                        ...(this.accessToken && { 'Authorization': `Bearer ${this.accessToken}` }),
                        ...(options.headers || {})
                    };

                    const retryOptions = {
                        ...options,
                        credentials: 'include',
                        headers: retryHeaders
                    };

                    response = await fetch(url, retryOptions);
                    console.log(`📥 Retry Response Status: ${response.status}`);

                    if (response.status === 401) {
                        console.error('❌ Still unauthorized after refresh');
                        this.handleUnauthenticated();
                        throw new Error('Authentication failed after token refresh');
                    }
                } else {
                    console.error('❌ Token refresh failed');
                    this.handleUnauthenticated();
                    throw new Error('Authentication failed - could not refresh token');
                }
            }

            // Handle 403 - Forbidden (likely CSRF failure)
            if (response.status === 403) {
                const errorText = await response.text();
                console.error('🚫 Access forbidden (403):', errorText);

                // Try to refresh CSRF token
                if (errorText.includes('CSRF')) {
                    console.log('🔄 CSRF error detected, refreshing token...');
                    await this.fetchCSRFToken();

                    // Retry with new CSRF token
                    const retryHeaders = {
                        'Accept': 'application/json',
                        ...(options.method !== 'GET' && { 'Content-Type': 'application/json' }),
                        ...(this.csrfToken && { 'X-CSRFToken': this.csrfToken }),
                        ...(this.accessToken && { 'Authorization': `Bearer ${this.accessToken}` }),
                        ...(options.headers || {})
                    };

                    const retryOptions = {
                        ...options,
                        credentials: 'include',
                        headers: retryHeaders
                    };

                    response = await fetch(url, retryOptions);
                    console.log(`📥 CSRF Retry Response Status: ${response.status}`);

                    if (response.status === 403) {
                        this.handleUnauthenticated();
                        throw new Error('CSRF validation failed');
                    }
                } else {
                    this.handleUnauthenticated();
                    throw new Error('Access forbidden');
                }
            }

            return response;
        } catch (error) {
            console.error('❌ Authenticated fetch error:', error);
            throw error;
        }
    }

    // Load initial data from session storage
    loadInitialData() {
        try {
            const storedData = sessionStorage.getItem('youtubeData');
            const storedUrl = sessionStorage.getItem('videoUrl');

            if (storedData) {
                const parsedData = typeof storedData === 'string'
                    ? JSON.parse(storedData)
                    : storedData;
                this.processVideoData(parsedData);
            }

            if (storedUrl) {
                this.videoUrl = storedUrl.startsWith('"')
                    ? JSON.parse(storedUrl)
                    : storedUrl;
                this.updateUrlInput(this.videoUrl);
            }

            console.log('✅ Initial data loaded successfully');
        } catch (error) {
            console.error('❌ Error loading initial data:', error);
        }
    }

    updateUrlInput(url) {
        const urlInput = document.querySelector('input[placeholder*="YouTube URL"]');
        if (urlInput && url) {
            urlInput.value = url;
        }
    }

    extractVideoId(url) {
        const patterns = [
            /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\?\/\s]{11})/,
            /^([^&\?\/\s]{11})$/
        ];

        for (let pattern of patterns) {
            const match = url.match(pattern);
            if (match) return match[1];
        }
        return null;
    }

    getHighestQualityThumbnail(thumbnails) {
        const priorities = ['maxres', 'standard', 'high', 'medium', 'default'];

        for (let quality of priorities) {
            if (thumbnails[quality]?.url) {
                return {
                    url: thumbnails[quality].url,
                    width: thumbnails[quality].width,
                    height: thumbnails[quality].height,
                    quality: quality
                };
            }
        }
        return null;
    }

    parseDuration(duration) {
        const match = duration.match(/PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?/);
        if (!match) return '0:00';

        const hours = parseInt(match[1] || 0);
        const minutes = parseInt(match[2] || 0);
        const seconds = parseInt(match[3] || 0);

        if (hours > 0) {
            return `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        }
        return `${minutes}:${seconds.toString().padStart(2, '0')}`;
    }

    formatNumber(num) {
        const number = parseInt(num);
        if (number >= 1000000) {
            return (number / 1000000).toFixed(1) + 'M';
        } else if (number >= 1000) {
            return (number / 1000).toFixed(1) + 'K';
        }
        return number.toString();
    }

    estimateFileSize(duration, format) {
        const durationMatch = duration.match(/PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?/);
        const hours = parseInt(durationMatch?.[1] || 0);
        const minutes = parseInt(durationMatch?.[2] || 0);
        const seconds = parseInt(durationMatch?.[3] || 0);
        const totalSeconds = hours * 3600 + minutes * 60 + seconds;

        const bitrates = {
            '1080p': 8,
            '720p': 5,
            '320kbps': 0.32
        };

        const sizeMB = (totalSeconds * bitrates[format]) / 8;
        return Math.round(sizeMB);
    }

    saveToSessionStorage(data, url = null) {
        try {
            sessionStorage.setItem('youtubeData', JSON.stringify(data));
            if (url) {
                sessionStorage.setItem('videoUrl', url);
            }
        } catch (error) {
            console.error('❌ Error saving to session storage:', error);
        }
    }

    // UI State Management
    showEmptyState() {
        const emptyState = document.getElementById('empty-state');
        const loadingState = document.getElementById('loading-state');
        const videoContent = document.getElementById('video-content');

        if (emptyState) emptyState.classList.remove('hidden');
        if (loadingState) loadingState.classList.add('hidden');
        if (videoContent) videoContent.classList.add('hidden');
    }

    showLoadingState() {
        const emptyState = document.getElementById('empty-state');
        const loadingState = document.getElementById('loading-state');
        const videoContent = document.getElementById('video-content');
        const analyzeBtn = document.getElementById('analyze-btn');
        const analyzeIcon = document.getElementById('analyze-icon');
        const analyzeText = document.getElementById('analyze-text');

        if (emptyState) emptyState.classList.add('hidden');
        if (loadingState) loadingState.classList.remove('hidden');
        if (videoContent) videoContent.classList.add('hidden');

        // Update button state
        if (analyzeBtn) analyzeBtn.disabled = true;
        if (analyzeIcon) analyzeIcon.textContent = 'hourglass_empty';
        if (analyzeText) analyzeText.textContent = 'Analyzing...';
    }

    showVideoContent() {
        const emptyState = document.getElementById('empty-state');
        const loadingState = document.getElementById('loading-state');
        const videoContent = document.getElementById('video-content');
        const analyzeBtn = document.getElementById('analyze-btn');
        const analyzeIcon = document.getElementById('analyze-icon');
        const analyzeText = document.getElementById('analyze-text');

        if (emptyState) emptyState.classList.add('hidden');
        if (loadingState) loadingState.classList.add('hidden');
        if (videoContent) videoContent.classList.remove('hidden');

        // Reset button state
        if (analyzeBtn) analyzeBtn.disabled = false;
        if (analyzeIcon) analyzeIcon.textContent = 'search';
        if (analyzeText) analyzeText.textContent = 'Analyze';
    }

    resetAnalyzeButton() {
        const analyzeBtn = document.getElementById('analyze-btn');
        const analyzeIcon = document.getElementById('analyze-icon');
        const analyzeText = document.getElementById('analyze-text');

        if (analyzeBtn) analyzeBtn.disabled = false;
        if (analyzeIcon) analyzeIcon.textContent = 'search';
        if (analyzeText) analyzeText.textContent = 'Analyze';
    }

    processVideoData(data) {
        if (data.type === 'video' && data.metadata) {
            this.videoData = data.metadata;
            this.videoId = data.metadata.id;
            this.showVideoContent();
            this.updateUI();
        }
    }

    updateUI() {
        if (!this.videoData) return;

        // Update thumbnail
        const thumbnail = this.getHighestQualityThumbnail(this.videoData.thumbnails);
        if (thumbnail) {
            const thumbnailImg = document.getElementById('video-thumbnail');
            if (thumbnailImg) {
                thumbnailImg.src = thumbnail.url;
                thumbnailImg.alt = this.videoData.title;
                thumbnailImg.setAttribute('data-quality', thumbnail.quality);
                console.log(`🖼️  Thumbnail: ${thumbnail.quality} (${thumbnail.width}x${thumbnail.height})`);
            }
        }

        // Update title
        const titleElement = document.getElementById('video-title');
        if (titleElement) {
            titleElement.textContent = this.videoData.title;
            titleElement.title = this.videoData.title;
        }

        // Update duration
        const duration = this.parseDuration(this.videoData.duration);
        const durationElement = document.getElementById('video-duration');
        if (durationElement) {
            durationElement.textContent = duration;
        }

        // Update channel
        const channelElement = document.getElementById('video-channel');
        if (channelElement) {
            channelElement.textContent = this.videoData.channel;
        }

        this.updateFileSizeEstimates();
        this.updateAdditionalMetadata();

        console.log('✅ UI updated:', this.videoData.title);
    }

    updateFileSizeEstimates() {
        const formatLabels = document.querySelectorAll('label:has(input[name="format"]) span.flex-1');

        formatLabels.forEach(label => {
            const text = label.textContent;
            let format = null;

            if (text.includes('1080p')) format = '1080p';
            else if (text.includes('720p')) format = '720p';
            else if (text.includes('320kbps') || text.includes('MP3')) format = '320kbps';

            if (format && this.videoData.duration) {
                const size = this.estimateFileSize(this.videoData.duration, format);
                const formatName = text.split('(')[0].trim();
                label.innerHTML = `${formatName} <span class="text-neutral-500 dark:text-neutral-400 ml-2 font-normal">(~${size}MB)</span>`;
            }
        });
    }

    updateAdditionalMetadata() {
        if (!this.videoData) return;
        console.log('📊 Views:', this.formatNumber(this.videoData.view_count));
        console.log('👍 Likes:', this.formatNumber(this.videoData.like_count));
        console.log('💬 Comments:', this.formatNumber(this.videoData.comment_count));
    }

    setupEventListeners() {
        const buttons = Array.from(document.querySelectorAll('button'));
        const analyzeButton = buttons.find(btn => btn.textContent.includes('Analyze'));

        if (analyzeButton) {
            analyzeButton.addEventListener('click', () => this.handleAnalyze());
        }

        const urlInput = document.querySelector('input[placeholder*="YouTube URL"]');
        if (urlInput) {
            urlInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.handleAnalyze();
                }
            });
        }

        const downloadButton = buttons.find(btn => btn.textContent.trim() === 'Download');
        if (downloadButton) {
            downloadButton.addEventListener('click', () => this.handleDownload());
        }

        const queueButton = buttons.find(btn => btn.textContent.trim() === 'Queue');
        if (queueButton) {
            queueButton.addEventListener('click', () => this.handleDownload());
        }
    }

    async handleAnalyze() {
        const urlInput = document.getElementById('url-input') || document.querySelector('input[placeholder*="YouTube URL"]');
        if (!urlInput) return;

        const url = urlInput.value.trim();
        if (!url) {
            if (window.toast) {
                window.toast.error('Please enter a YouTube URL');
            } else {
                alert('Please enter a YouTube URL');
            }
            return;
        }

        this.videoId = this.extractVideoId(url);
        if (!this.videoId) {
            if (window.toast) {
                window.toast.error('Invalid YouTube URL');
            } else {
                alert('Invalid YouTube URL');
            }
            return;
        }

        this.videoUrl = url;

        // Check session storage cache
        const storedData = sessionStorage.getItem('youtubeData');
        if (storedData) {
            const parsedData = JSON.parse(storedData);
            if (parsedData.metadata?.id === this.videoId) {
                console.log('✅ Using cached video data');
                this.processVideoData(parsedData);
                return;
            }
        }

        console.log('🔍 Analyzing video:', url);

        // Show loading state
        this.showLoadingState();

        try {
            const response = await this.authenticatedFetch(`${this.apiBaseUrl}/youtube/validate/`, {
                method: 'POST',
                body: JSON.stringify({ url: url })
            });

            if (response.ok) {
                const data = await response.json();
                this.saveToSessionStorage(data, url);
                this.processVideoData(data);
                console.log('✅ Video analyzed successfully');
            } else {
                const errorText = await response.text();
                console.error('❌ Analyze failed:', response.status, errorText);
                this.showEmptyState();
                this.resetAnalyzeButton();
                if (window.toast) {
                    window.toast.error('Failed to analyze video. Please try again.');
                } else {
                    alert('Failed to analyze video. Please try again.');
                }
            }
        } catch (error) {
            console.error('❌ Error analyzing video:', error);
            this.showEmptyState();
            this.resetAnalyzeButton();
            if (window.toast) {
                window.toast.error('Error analyzing video. Please check your connection.');
            } else {
                alert('Error analyzing video. Please check your connection.');
            }
        }
    }

    async handleDownload() {
        if (!this.videoData) {
            alert('Please analyze a video first');
            return;
        }

        const selectedFormat = document.querySelector('input[name="format"]:checked');
        if (!selectedFormat) {
            alert('Please select a format');
            return;
        }

        // Verify authentication
        const authStatus = await this.checkAuthStatus();
        if (!authStatus.authenticated) {
            console.log('❌ User not authenticated');
            this.handleUnauthenticated();
            return;
        }

        // Ensure CSRF token
        if (!this.csrfToken) {
            console.log('⚠️  Refreshing CSRF token before download...');
            await this.fetchCSRFToken();
        }

        const formatText = selectedFormat.nextElementSibling.textContent;

        // Determine format and quality
        let format, quality;

        if (formatText.includes('MP3') || formatText.includes('320kbps')) {
            format = 'mp3';
            quality = 'best';
        } else if (formatText.includes('1080p')) {
            format = 'mp4';
            quality = '1080';
        } else if (formatText.includes('720p')) {
            format = 'mp4';
            quality = '720';
        } else {
            format = 'mp4';
            quality = 'best';
        }

        const requestData = {
            url: this.videoUrl,
            format: format,
            quality: quality
        };

        console.log('\n🎬 Starting download:');
        console.log('   Video:', this.videoData.title);
        console.log('   Format:', format);
        console.log('   Quality:', quality);

        try {
            const response = await this.authenticatedFetch(`${this.apiBaseUrl}/downloads/create/`, {
                method: 'POST',
                body: JSON.stringify(requestData)
            });

            const responseText = await response.text();
            console.log('📥 Response body:', responseText);

            if (response.ok) {
                const data = JSON.parse(responseText);
                console.log('✅ Download created:', data);

                // Show notification
                if (window.toast) {
                    window.toast.success(`Download started: ${this.videoData.title}`);
                } else {
                    console.log(`✅ Download started for "${this.videoData.title}"!`);
                }

                // Start polling for this download to auto-download when complete
                this.trackDownloadForAutoDownload(data.id, this.videoData.title);

            } else {
                let errorMessage = 'Unknown error';
                try {
                    const errorData = JSON.parse(responseText);
                    errorMessage = errorData.message || errorData.detail || errorData.error || JSON.stringify(errorData);
                } catch (e) {
                    errorMessage = responseText;
                }
                console.error('❌ Download failed:', errorMessage);
                alert(`Failed to start download: ${errorMessage}`);
            }
        } catch (error) {
            console.error('❌ Error creating download:', error);
            alert('Error starting download. Please try again.');
        }
    }

    /**
     * Track a download and auto-download the file when complete
     */
    trackDownloadForAutoDownload(downloadId, title) {
        console.log(`🔍 Tracking download ${downloadId} for auto-download`);

        // Store download info
        this.activeDownloads.set(downloadId, {
            id: downloadId,
            title: title,
            startTime: Date.now()
        });

        // Start polling for this specific download
        this.pollDownloadStatus(downloadId, title);
    }

    /**
     * Poll download status until completed or failed
     */
    async pollDownloadStatus(downloadId, title) {
        const POLL_INTERVAL = 2000; // 2 seconds
        const MAX_POLL_TIME = 30 * 60 * 1000; // 30 minutes max
        const startTime = Date.now();

        const poll = async () => {
            // Stop if exceeded max time
            if (Date.now() - startTime > MAX_POLL_TIME) {
                console.warn(`⚠️ Download ${downloadId} polling timeout`);
                this.activeDownloads.delete(downloadId);
                return;
            }

            try {
                const response = await this.authenticatedFetch(
                    `${this.apiBaseUrl}/downloads/status/${downloadId}/`,
                    { method: 'GET' }
                );

                if (!response.ok) {
                    console.error(`❌ Failed to get status for download ${downloadId}`);
                    setTimeout(poll, POLL_INTERVAL);
                    return;
                }

                const data = await response.json();
                console.log(`📊 Download ${downloadId} status: ${data.status} (${data.progress}%)`);

                if (data.status === 'completed') {
                    console.log(`✅ Download ${downloadId} completed!`);

                    // Show completion notification
                    if (window.toast) {
                        window.toast.success(`Download complete: ${title}`);
                    }

                    // Trigger file download to client
                    this.triggerFileDownload(downloadId, title);

                    // Remove from tracking
                    this.activeDownloads.delete(downloadId);

                } else if (data.status === 'failed' || data.status === 'error') {
                    console.error(`❌ Download ${downloadId} failed:`, data.error);

                    if (window.toast) {
                        window.toast.error(`Download failed: ${title}`);
                    } else {
                        alert(`Download failed: ${data.error || 'Unknown error'}`);
                    }

                    // Remove from tracking
                    this.activeDownloads.delete(downloadId);

                } else {
                    // Still in progress, continue polling
                    setTimeout(poll, POLL_INTERVAL);
                }

            } catch (error) {
                console.error(`❌ Error polling download ${downloadId}:`, error);
                setTimeout(poll, POLL_INTERVAL);
            }
        };

        // Start polling
        poll();
    }

    /**
     * Trigger file download to client storage
     */
    triggerFileDownload(downloadId, title) {
        // Use shared global Set to prevent duplicate downloads across scripts
        if (!window._downloadedFileIds) {
            window._downloadedFileIds = new Set();
        }

        // Check if already downloaded
        if (window._downloadedFileIds.has(downloadId)) {
            console.log(`⏭️ File ${downloadId} already downloaded, skipping (youtube-downloader)`);
            return;
        }

        // Mark as downloaded immediately to prevent race conditions
        window._downloadedFileIds.add(downloadId);

        console.log(`📥 Triggering file download for ID: ${downloadId}`);

        try {
            // Create hidden link and trigger download
            const link = document.createElement('a');
            link.href = `${this.apiBaseUrl}/downloads/file/${downloadId}/`;
            link.style.display = 'none';
            link.download = title || 'download'; // Suggest filename
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);

            console.log(`✅ File download triggered for: ${title}`);
        } catch (error) {
            console.error('❌ File download trigger failed:', error);
            // Remove from set so user can retry
            window._downloadedFileIds.delete(downloadId);
            if (window.toast) {
                window.toast.error(`Failed to download file: ${title}`);
            }
        }
    }

    async addToQueue() {
        if (!this.videoData) {
            alert('Please analyze a video first');
            return;
        }

        console.log('📋 Adding to queue:', this.videoData.title);

        try {
            const response = await this.authenticatedFetch(`${this.apiBaseUrl}/youtube/queue/`, {
                method: 'POST',
                body: JSON.stringify({
                    video_id: this.videoId,
                    url: this.videoUrl,
                    title: this.videoData.title
                })
            });

            if (response.ok) {
                alert(`✅ Added "${this.videoData.title}" to download queue`);
                console.log('✅ Added to queue successfully');
            } else {
                const errorText = await response.text();
                console.error('❌ Add to queue failed:', response.status, errorText);
                alert('Failed to add to queue');
            }
        } catch (error) {
            console.error('❌ Error adding to queue:', error);
            alert('Error adding to queue. Please try again.');
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Initializing YouTube Downloader...');
    window.ytDownloader = new YouTubeDownloader();
});

// Helper functions for testing
function setTestData() {
    const testData = {
        "type": "video",
        "metadata": {
            "id": "4hLnDkV-kwQ",
            "title": "Delhi Belly | Pranit More | Stand-up Comedy | Crowd Work Special",
            "description": "Dosto, Yeh show maine Dil waaloh ki Dilli mein kiya tha...",
            "channel": "Pranit More Crowdwork Clips",
            "channel_id": "UCDKKgIxi5uI2QuLoHfN94Sg",
            "published_at": "2025-12-27T13:30:07Z",
            "duration": "PT35M30S",
            "thumbnails": {
                "default": { "url": "https://i.ytimg.com/vi/4hLnDkV-kwQ/default.jpg", "width": 120, "height": 90 },
                "medium": { "url": "https://i.ytimg.com/vi/4hLnDkV-kwQ/mqdefault.jpg", "width": 320, "height": 180 },
                "high": { "url": "https://i.ytimg.com/vi/4hLnDkV-kwQ/hqdefault.jpg", "width": 480, "height": 360 },
                "standard": { "url": "https://i.ytimg.com/vi/4hLnDkV-kwQ/sddefault.jpg", "width": 640, "height": 480 },
                "maxres": { "url": "https://i.ytimg.com/vi/4hLnDkV-kwQ/maxresdefault.jpg", "width": 1280, "height": 720 }
            },
            "view_count": "1179140",
            "like_count": "24312",
            "comment_count": "312"
        }
    };

    const videoUrl = "https://youtu.be/4hLnDkV-kwQ?si=FCHjotWDkGk5jJfG";
    sessionStorage.setItem('youtubeData', JSON.stringify(testData));
    sessionStorage.setItem('videoUrl', videoUrl);
    console.log('✅ Test data saved to session storage');

    if (window.ytDownloader) {
        window.ytDownloader.loadInitialData();
    }
}

function clearTestData() {
    sessionStorage.removeItem('youtubeData');
    sessionStorage.removeItem('videoUrl');
    console.log('🗑️  Session storage cleared');
    location.reload();
}
