// history.js - YouTube Downloader History Page
// Version: 2.0 - Production Ready - NO AUTO-RELOAD

const API_BASE_URL = '';
const API_ENDPOINT = '/api/downloads/list/';

let currentPage = 1;
let currentStatus = null;
let currentFormat = null;
const itemsPerPage = 10;

async function authenticatedFetch(url, options) {
    options = options || {};
    const defaultOptions = {
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' }
    };

    const fetchOptions = {
        method: options.method || 'GET',
        credentials: defaultOptions.credentials,
        headers: Object.assign({}, defaultOptions.headers, options.headers || {}),
        body: options.body || undefined
    };

    try {
        const response = await fetch(url, fetchOptions);
        if (response.status === 401) {
            console.log('Authentication failed - redirecting to login');
            window.location.href = '/login/';
            return null;
        }
        return response;
    } catch (error) {
        console.error('Fetch error:', error);
        throw error;
    }
}

document.addEventListener('DOMContentLoaded', function () {
    console.log('History page loaded - v2.0');
    initializeEventListeners();
    loadDownloads();
});

function initializeEventListeners() {
    document.querySelectorAll('[data-filter]').forEach(function (button) {
        button.addEventListener('click', handleFilterClick);
    });

    const clearBtn = document.querySelector('[data-action="clear-history"]');
    if (clearBtn) {
        clearBtn.addEventListener('click', handleClearHistory);
    }

    const refreshBtn = document.querySelector('[data-action="refresh"]');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function () {
            console.log('Manual refresh triggered');
            loadDownloads();
            showSuccess('Downloads refreshed');
        });
    }
}

function handleFilterClick(e) {
    const button = e.currentTarget;
    const filter = button.getAttribute('data-filter');

    document.querySelectorAll('[data-filter]').forEach(function (btn) {
        btn.classList.remove('bg-black', 'dark:bg-white', 'text-white', 'dark:text-black');
        btn.classList.add('bg-transparent');
    });

    button.classList.add('bg-black', 'dark:bg-white', 'text-white', 'dark:text-black');
    button.classList.remove('bg-transparent');

    currentPage = 1;

    if (filter === 'all') {
        currentStatus = null;
        currentFormat = null;
    } else if (filter === 'videos') {
        currentFormat = 'mp4';
        currentStatus = null;
    } else if (filter === 'audio') {
        currentFormat = 'mp3';
        currentStatus = null;
    } else if (filter === 'completed') {
        currentStatus = 'completed';
        currentFormat = null;
    } else {
        currentStatus = null;
        currentFormat = null;
    }

    loadDownloads();
}

async function loadDownloads() {
    try {
        showLoading();

        const params = new URLSearchParams({ page: currentPage, limit: itemsPerPage });
        if (currentStatus) params.append('status', currentStatus);
        if (currentFormat) params.append('format', currentFormat);

        const url = API_ENDPOINT + '?' + params.toString();
        const response = await authenticatedFetch(url);

        if (!response) throw new Error('Authentication failed');
        if (!response.ok) throw new Error('HTTP error status: ' + response.status);

        const data = await response.json();

        updateStatistics(data);
        renderDownloads(data.downloads);
        renderPagination(data);
        hideLoading();

    } catch (error) {
        console.error('Error loading downloads:', error);
        showError('Failed to load downloads');
        hideLoading();
    }
}

function updateStatistics(data) {
    const totalElement = document.querySelector('[data-stat="total-downloads"]');
    if (totalElement) totalElement.textContent = data.total_downloads || 0;

    const monthElement = document.querySelector('[data-stat="downloads-month"]');
    if (monthElement) monthElement.textContent = data.downloads_this_month || 0;

    const storageElement = document.querySelector('[data-stat="storage-used"]');
    if (storageElement) storageElement.textContent = data.storage_used || '0B';
}

function renderDownloads(downloads) {
    const container = document.querySelector('[data-downloads-list]');
    if (!container) {
        console.error('Downloads container not found');
        return;
    }

    if (!downloads || downloads.length === 0) {
        container.innerHTML = '<div class="text-center py-12"><span class="material-symbols-outlined text-6xl text-neutral-300 dark:text-neutral-700">download</span><p class="text-xl font-bold mt-4 text-neutral-500 dark:text-neutral-400">No downloads found</p><p class="text-sm text-neutral-400 dark:text-neutral-500 mt-2">Start downloading your favorite videos!</p></div>';
        return;
    }

    container.innerHTML = downloads.map(createDownloadCard).join('');
    attachDownloadActions();
}

function createDownloadCard(download) {
    const thumbnail = download.thumbnail || getDefaultThumbnail(download.format);
    const statusBadge = getStatusBadge(download.status);
    const formatIcon = getFormatIcon(download.format);
    const title = escapeHtml(download.title);
    const channelName = escapeHtml(download.channel_name);
    const url = escapeHtml(download.url);

    let html = '<div class="brutal-border dark:border-white bg-surface-light dark:bg-surface-dark hover:shadow-brutal dark:hover:shadow-brutal-dark transition-all" data-download-id="' + download.id + '">';
    html += '<div class="p-6"><div class="flex flex-col md:flex-row gap-6">';
    html += '<div class="shrink-0"><div class="w-[180px] h-[100px] brutal-border dark:border-white relative overflow-hidden group">';
    html += '<img alt="' + title + '" class="w-full h-full object-cover" src="' + thumbnail + '" onerror="this.src=\'' + getDefaultThumbnail(download.format) + '\'" />';

    if (download.status === 'downloading') {
        html += '<div class="absolute inset-0 bg-black/70 flex items-center justify-center"><div class="text-white text-center">';
        html += '<p class="text-2xl font-black">' + download.progress + '%</p><p class="text-xs">Downloading...</p></div></div>';
    }

    html += formatIcon + '</div></div>';
    html += '<div class="flex-grow flex flex-col justify-between"><div>';
    html += '<h3 class="text-xl font-bold leading-tight mb-2">' + title + '</h3>';
    html += '<div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-neutral-500 dark:text-neutral-400 font-medium mb-3">';
    html += '<span class="flex items-center gap-1"><span class="material-symbols-outlined text-[16px]">account_circle</span>' + channelName + '</span>';

    if (download.duration && download.duration !== '0:00') {
        html += '<span class="w-1 h-1 bg-neutral-400 rounded-full"></span>';
        html += '<span class="flex items-center gap-1"><span class="material-symbols-outlined text-[16px]">schedule</span>' + download.duration + '</span>';
    }

    html += '<span class="w-1 h-1 bg-neutral-400 rounded-full"></span>';
    html += '<span class="uppercase text-xs font-bold bg-primary text-white px-2 py-0.5">' + download.format_quality + '</span>';
    html += statusBadge + '</div>';

    html += '<div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-neutral-500 dark:text-neutral-400 font-mono">';
    if (download.file_size !== '0B') html += '<span>' + download.file_size + '</span>';
    if (download.file_size !== '0B' && download.formatted_date) html += '<span class="w-1 h-1 bg-neutral-400 rounded-full"></span>';
    if (download.formatted_date) html += '<span>Downloaded: ' + download.formatted_date + '</span>';
    html += '</div>';

    if (download.error) {
        html += '<div class="mt-2 p-2 bg-red-100 dark:bg-red-900/30 border-2 border-red-500 rounded-sm">';
        html += '<p class="text-xs text-red-700 dark:text-red-300 font-mono">' + escapeHtml(download.error) + '</p></div>';
    }

    html += '</div><div class="flex gap-3 mt-4">';

    if (download.status === 'completed' && download.file_url) {
        html += '<a href="' + download.file_url + '" download class="px-4 py-2 brutal-border dark:border-white bg-black dark:bg-white text-white dark:text-black font-bold text-xs uppercase tracking-wide hover:bg-primary transition-colors shadow-brutal-sm">';
        html += '<span class="flex items-center gap-2"><span class="material-symbols-outlined text-sm">download</span>Download</span></a>';
    }

    if (download.status === 'failed') {
        html += '<button data-action="redownload" data-url="' + url + '" class="px-4 py-2 brutal-border dark:border-white bg-black dark:bg-white text-white dark:text-black font-bold text-xs uppercase tracking-wide hover:bg-primary transition-colors shadow-brutal-sm">';
        html += '<span class="flex items-center gap-2"><span class="material-symbols-outlined text-sm">refresh</span>Retry</span></button>';
    }

    html += '<a href="' + download.url + '" target="_blank" rel="noopener noreferrer" class="px-4 py-2 brutal-border dark:border-white bg-transparent font-bold text-xs uppercase tracking-wide hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors shadow-brutal-sm">';
    html += '<span class="flex items-center gap-2"><span class="material-symbols-outlined text-sm">open_in_new</span>View Source</span></a>';

    html += '<button data-action="delete" data-id="' + download.id + '" class="px-4 py-2 brutal-border dark:border-white bg-transparent text-primary font-bold text-xs uppercase tracking-wide hover:bg-primary hover:text-white transition-colors shadow-brutal-sm">';
    html += '<span class="material-symbols-outlined text-sm">delete</span></button>';

    html += '</div></div></div></div></div>';
    return html;
}

function renderPagination(data) {
    const container = document.querySelector('[data-pagination]');
    if (!container || data.total_pages <= 1) {
        if (container) container.innerHTML = '';
        return;
    }

    let html = '<div class="flex justify-center items-center gap-2 pt-8">';
    html += '<button ' + (!data.has_previous ? 'disabled' : '') + ' onclick="changePage(' + (currentPage - 1) + ')" class="w-10 h-10 brutal-border bg-transparent hover:bg-neutral-100 flex items-center justify-center transition-colors shadow-brutal-sm ' + (!data.has_previous ? 'opacity-50 cursor-not-allowed' : '') + '"><span class="material-symbols-outlined">chevron_left</span></button>';

    const startPage = Math.max(1, currentPage - 2);
    const endPage = Math.min(data.total_pages, currentPage + 2);

    for (let i = startPage; i <= endPage; i++) {
        html += '<button onclick="changePage(' + i + ')" class="w-10 h-10 brutal-border ' + (i === currentPage ? 'bg-black text-white' : 'bg-transparent hover:bg-neutral-100') + ' font-bold transition-colors shadow-brutal-sm">' + i + '</button>';
    }

    if (endPage < data.total_pages) {
        html += '<span class="px-2">...</span>';
        html += '<button onclick="changePage(' + data.total_pages + ')" class="w-10 h-10 brutal-border bg-transparent hover:bg-neutral-100 font-bold transition-colors shadow-brutal-sm">' + data.total_pages + '</button>';
    }

    html += '<button ' + (!data.has_next ? 'disabled' : '') + ' onclick="changePage(' + (currentPage + 1) + ')" class="w-10 h-10 brutal-border bg-transparent hover:bg-neutral-100 flex items-center justify-center transition-colors shadow-brutal-sm ' + (!data.has_next ? 'opacity-50 cursor-not-allowed' : '') + '"><span class="material-symbols-outlined">chevron_right</span></button>';
    html += '</div>';
    container.innerHTML = html;
}

function changePage(page) {
    currentPage = page;
    loadDownloads();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function attachDownloadActions() {
    document.querySelectorAll('[data-action="delete"]').forEach(function (btn) {
        btn.addEventListener('click', handleDelete);
    });
    document.querySelectorAll('[data-action="redownload"]').forEach(function (btn) {
        btn.addEventListener('click', handleRedownload);
    });
}

async function handleDelete(e) {
    const downloadId = e.currentTarget.getAttribute('data-id');
    if (!confirm('Are you sure you want to delete this download?')) return;

    try {
        const response = await authenticatedFetch(API_BASE_URL + '/api/downloads/' + downloadId + '/', { method: 'DELETE' });
        if (response && response.ok) {
            showSuccess('Download deleted successfully');
            loadDownloads();
        } else {
            throw new Error('Failed to delete');
        }
    } catch (error) {
        console.error('Error deleting download:', error);
        showError('Failed to delete download');
    }
}

async function handleRedownload(e) {
    const url = e.currentTarget.getAttribute('data-url');
    try {
        const response = await authenticatedFetch(API_BASE_URL + '/api/downloads/create/', {
            method: 'POST',
            body: JSON.stringify({ url: url })
        });
        if (response && response.ok) {
            showSuccess('Download restarted successfully');
            setTimeout(function () { loadDownloads(); }, 1000);
        } else {
            throw new Error('Failed to restart download');
        }
    } catch (error) {
        console.error('Error restarting download:', error);
        showError('Failed to restart download');
    }
}

async function handleClearHistory() {
    if (!confirm('Are you sure you want to clear all history? This cannot be undone.')) return;

    try {
        const response = await authenticatedFetch(API_BASE_URL + '/api/downloads/clear/', { method: 'POST' });
        if (response && response.ok) {
            showSuccess('History cleared successfully');
            loadDownloads();
        } else {
            throw new Error('Failed to clear history');
        }
    } catch (error) {
        console.error('Error clearing history:', error);
        showError('Failed to clear history');
    }
}

function getStatusBadge(status) {
    const badges = {
        'completed': '<span class="w-1 h-1 bg-neutral-400 rounded-full"></span><span class="text-xs uppercase font-bold text-green-600">✓ Completed</span>',
        'downloading': '<span class="w-1 h-1 bg-neutral-400 rounded-full"></span><span class="text-xs uppercase font-bold text-blue-600">↓ Downloading</span>',
        'queued': '<span class="w-1 h-1 bg-neutral-400 rounded-full"></span><span class="text-xs uppercase font-bold text-yellow-600">⏳ Queued</span>',
        'failed': '<span class="w-1 h-1 bg-neutral-400 rounded-full"></span><span class="text-xs uppercase font-bold text-red-600">✗ Failed</span>'
    };
    return badges[status] || '';
}

function getFormatIcon(format) {
    if (format === 'mp3') {
        return '<div class="absolute inset-0 flex items-center justify-center pointer-events-none"><span class="material-symbols-outlined text-white text-6xl drop-shadow-lg">music_note</span></div>';
    }
    return '';
}

function getDefaultThumbnail(format) {
    if (format === 'mp3') {
        return 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="180" height="100"%3E%3Crect fill="%23a855f7" width="180" height="100"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" fill="white" font-size="40" font-weight="bold"%3E♫%3C/text%3E%3C/svg%3E';
    }
    return 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="180" height="100"%3E%3Crect fill="%233b82f6" width="180" height="100"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" fill="white" font-size="40" font-weight="bold"%3E▶%3C/text%3E%3C/svg%3E';
}

function escapeHtml(text) {
    if (!text) return '';
    return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;').replace(/\n/g, ' ').replace(/\r/g, ' ');
}

function showLoading() {
    const container = document.querySelector('[data-downloads-list]');
    if (container) {
        container.innerHTML = '<div class="text-center py-12"><div class="inline-block animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent"></div><p class="text-sm font-bold mt-4 text-neutral-500 dark:text-neutral-400">Loading downloads...</p></div>';
    }
}

function hideLoading() { }

function showError(message) {
    const toast = document.createElement('div');
    toast.className = 'fixed top-4 right-4 bg-red-500 text-white px-6 py-3 rounded-sm shadow-brutal z-50 font-bold';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(function () { toast.remove(); }, 3000);
}

function showSuccess(message) {
    const toast = document.createElement('div');
    toast.className = 'fixed top-4 right-4 bg-green-500 text-white px-6 py-3 rounded-sm shadow-brutal z-50 font-bold';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(function () { toast.remove(); }, 3000);
}

window.changePage = changePage;
window.refreshDownloads = function () {
    loadDownloads();
    showSuccess('Downloads refreshed');
};
