/**
 * Toast Notification System - Brutalist Style
 * Shows temporary notifications for success/error messages
 */

class ToastManager {
    constructor() {
        this.container = null;
        this.init();
    }

    /**
     * Initialize toast container
     */
    init() {
        // Create container if it doesn't exist
        if (!document.getElementById('toast-container')) {
            this.container = document.createElement('div');
            this.container.id = 'toast-container';
            this.container.className = 'fixed top-20 right-4 z-50 flex flex-col gap-2 w-80 max-w-[calc(100vw-2rem)]';
            document.body.appendChild(this.container);
        } else {
            this.container = document.getElementById('toast-container');
        }
    }

    /**
     * Show a toast notification
     * @param {string} message - The message to display
     * @param {string} type - 'success', 'error', 'info', 'warning'
     * @param {number} duration - Duration in milliseconds (0 = permanent)
     */
    show(message, type = 'info', duration = 3000) {
        const toast = this.createToast(message, type);
        this.container.appendChild(toast);

        // Trigger animation
        setTimeout(() => {
            toast.classList.add('opacity-100', 'translate-x-0');
            toast.classList.remove('opacity-0', 'translate-x-4');
        }, 10);

        // Auto-remove after duration
        if (duration > 0) {
            setTimeout(() => {
                this.remove(toast);
            }, duration);
        }

        return toast;
    }

    /**
     * Create toast HTML element
     */
    createToast(message, type) {
        const toast = document.createElement('div');

        // Base classes
        toast.className = `
            opacity-0 translate-x-4 transition-all duration-300
            brutal-border dark:border-white
            bg-surface-light dark:bg-surface-dark
            p-4 shadow-brutal dark:shadow-brutal-dark
            flex items-start gap-3
        `;

        // Type-specific styling
        const typeConfig = {
            success: {
                icon: 'check_circle',
                color: 'text-green-600 dark:text-green-400',
                borderColor: 'border-green-600 dark:border-green-400'
            },
            error: {
                icon: 'error',
                color: 'text-red-600 dark:text-red-400',
                borderColor: 'border-red-600 dark:border-red-400'
            },
            warning: {
                icon: 'warning',
                color: 'text-yellow-600 dark:text-yellow-400',
                borderColor: 'border-yellow-600 dark:border-yellow-400'
            },
            info: {
                icon: 'info',
                color: 'text-blue-600 dark:text-blue-400',
                borderColor: 'border-blue-600 dark:border-blue-400'
            }
        };

        const config = typeConfig[type] || typeConfig.info;

        toast.innerHTML = `
            <span class="material-symbols-outlined ${config.color} text-2xl shrink-0">
                ${config.icon}
            </span>
            <div class="flex-1 min-w-0">
                <p class="text-sm font-bold text-neutral-900 dark:text-neutral-50 break-words">
                    ${this.escapeHtml(message)}
                </p>
            </div>
            <button class="close-toast shrink-0 text-neutral-500 hover:text-black dark:hover:text-white transition-colors">
                <span class="material-symbols-outlined text-xl">close</span>
            </button>
        `;

        // Add border accent
        toast.style.borderLeftWidth = '4px';
        toast.classList.add(config.borderColor);

        // Close button functionality
        toast.querySelector('.close-toast').addEventListener('click', () => {
            this.remove(toast);
        });

        return toast;
    }

    /**
     * Remove a toast with animation
     */
    remove(toast) {
        toast.classList.remove('opacity-100', 'translate-x-0');
        toast.classList.add('opacity-0', 'translate-x-4');

        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }

    /**
     * Convenience methods
     */
    success(message, duration = 3000) {
        return this.show(message, 'success', duration);
    }

    error(message, duration = 4000) {
        return this.show(message, 'error', duration);
    }

    warning(message, duration = 3500) {
        return this.show(message, 'warning', duration);
    }

    info(message, duration = 3000) {
        return this.show(message, 'info', duration);
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
     * Clear all toasts
     */
    clearAll() {
        const toasts = this.container.querySelectorAll('div');
        toasts.forEach(toast => this.remove(toast));
    }
}

// Create global instance
const toast = new ToastManager();

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = toast;
}