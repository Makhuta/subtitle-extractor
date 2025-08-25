// Main application JavaScript

// Global utilities
window.AppUtils = {
    // Format time from milliseconds to readable format
    formatTime: function(ms) {
        const totalSeconds = Math.floor(ms / 1000);
        const hours = Math.floor(totalSeconds / 3600);
        const minutes = Math.floor((totalSeconds % 3600) / 60);
        const seconds = totalSeconds % 60;
        
        return `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    },
    
    // Show loading state
    showLoading: function(element, text = 'Loading...') {
        if (typeof element === 'string') {
            element = document.getElementById(element);
        }
        
        if (element) {
            element.innerHTML = `
                <div class="d-flex align-items-center justify-content-center py-3">
                    <div class="spinner-border spinner-border-sm me-2" role="status"></div>
                    <span>${text}</span>
                </div>
            `;
        }
    },
    
    // Show error message
    showError: function(element, message) {
        if (typeof element === 'string') {
            element = document.getElementById(element);
        }
        
        if (element) {
            element.innerHTML = `
                <div class="alert alert-danger" role="alert">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    ${message}
                </div>
            `;
        }
    },
    
    // API request helper
    apiRequest: function(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        };
        
        return fetch(url, { ...defaultOptions, ...options })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            });
    },
    
    // Debounce function for input events
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
};

// Auto-dismiss alerts after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        if (!alert.classList.contains('alert-danger')) {
            setTimeout(() => {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }, 5000);
        }
    });
});

// Add tooltips to elements with title attribute
document.addEventListener('DOMContentLoaded', function() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[title]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl+S to trigger download (if download button exists and is enabled)
    if (e.ctrlKey && e.key === 's') {
        e.preventDefault();
        const downloadBtn = document.getElementById('download-btn');
        if (downloadBtn && !downloadBtn.disabled) {
            downloadBtn.click();
        }
    }
    
    // Escape to go back (if back button exists)
    if (e.key === 'Escape') {
        const backBtn = document.querySelector('a[href*="index"]');
        if (backBtn) {
            window.location.href = backBtn.href;
        }
    }
});

// File upload drag and drop enhancement
document.addEventListener('DOMContentLoaded', function() {
    const fileInputs = document.querySelectorAll('input[type="file"]');
    
    fileInputs.forEach(input => {
        const container = input.closest('.mb-3') || input.parentElement;
        
        // Add drag and drop styling
        container.addEventListener('dragover', function(e) {
            e.preventDefault();
            container.classList.add('border-primary', 'bg-primary', 'bg-opacity-10');
        });
        
        container.addEventListener('dragleave', function(e) {
            e.preventDefault();
            container.classList.remove('border-primary', 'bg-primary', 'bg-opacity-10');
        });
        
        container.addEventListener('drop', function(e) {
            e.preventDefault();
            container.classList.remove('border-primary', 'bg-primary', 'bg-opacity-10');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                input.files = files;
                // Trigger change event
                const event = new Event('change', { bubbles: true });
                input.dispatchEvent(event);
            }
        });
    });
});

// Auto-save functionality for text inputs (with debouncing)
document.addEventListener('DOMContentLoaded', function() {
    const autoSaveInputs = document.querySelectorAll('.subtitle-line input, .subtitle-line textarea');
    
    autoSaveInputs.forEach(input => {
        const debouncedSave = AppUtils.debounce(function() {
            // Save indication
            const originalBorder = input.style.borderColor;
            input.style.borderColor = '#28a745';
            setTimeout(() => {
                input.style.borderColor = originalBorder;
            }, 1000);
        }, 500);
        
        input.addEventListener('input', debouncedSave);
    });
});

// Progress tracking for long operations
window.ProgressTracker = {
    show: function(containerId, message = 'Processing...') {
        const container = document.getElementById(containerId);
        if (container) {
            container.style.display = 'block';
            container.innerHTML = `
                <div class="card">
                    <div class="card-body">
                        <div class="d-flex align-items-center">
                            <div class="spinner-border spinner-border-sm me-3" role="status"></div>
                            <div>
                                <h6 class="mb-0">${message}</h6>
                                <small class="text-muted">Please wait...</small>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
    },
    
    hide: function(containerId) {
        const container = document.getElementById(containerId);
        if (container) {
            container.style.display = 'none';
        }
    },
    
    update: function(containerId, message, progress = null) {
        const container = document.getElementById(containerId);
        if (container) {
            const progressBar = progress !== null ? 
                `<div class="progress mt-2" style="height: 4px;">
                    <div class="progress-bar" role="progressbar" style="width: ${progress}%"></div>
                </div>` : '';
            
            container.innerHTML = `
                <div class="card">
                    <div class="card-body">
                        <div class="d-flex align-items-center">
                            <div class="spinner-border spinner-border-sm me-3" role="status"></div>
                            <div class="flex-grow-1">
                                <h6 class="mb-0">${message}</h6>
                                ${progressBar}
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
    }
};

// Confirmation dialogs for destructive actions
document.addEventListener('click', function(e) {
    if (e.target.matches('[data-confirm]')) {
        const message = e.target.dataset.confirm;
        if (!confirm(message)) {
            e.preventDefault();
            e.stopPropagation();
            return false;
        }
    }
});

// Enhanced form validation
document.addEventListener('DOMContentLoaded', function() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;
            
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    field.classList.add('is-invalid');
                    isValid = false;
                } else {
                    field.classList.remove('is-invalid');
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                const firstInvalid = form.querySelector('.is-invalid');
                if (firstInvalid) {
                    firstInvalid.focus();
                }
            }
        });
    });
});

document.getElementById('searchInput').addEventListener('keyup', function () {
    let filter = this.value.toLowerCase();
    let items = document.querySelectorAll('#itemsList .list-group-item');

    items.forEach(function (item) {
        let text = item.innerText.toLowerCase();
        if (text.includes(filter)) {
            item.style.display = "";
        } else {
            // Always keep the "Parent Directory" visible
            if (item.querySelector('h6')?.innerText === "..") {
                item.style.display = "";
            } else {
                item.style.display = "none";
            }
        }
    });
});

console.log('Subtitle Extractor app loaded successfully');