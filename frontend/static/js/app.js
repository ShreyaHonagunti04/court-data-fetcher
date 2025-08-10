// Delhi High Court Data Fetcher - Frontend JavaScript

// Delhi High Court Data Fetcher - Frontend JavaScript
console.log("Delhi High Court JS loaded");


class CourtDataFetcher {
    constructor() {
        this.apiBase = window.location.origin;
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        // Search form submission
        const searchForm = document.getElementById('searchForm');
        if (searchForm) {
            searchForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.searchCase();
            });
        }

        // Smooth scrolling for navigation links
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    }

    async searchCase() {
        const caseType = document.getElementById('caseType').value;
        const caseNumber = document.getElementById('caseNumber').value;
        const filingYear = document.getElementById('filingYear').value;

        // Validation
        if (!caseType || !caseNumber || !filingYear) {
            this.showError('Please fill in all required fields.');
            return;
        }

        // Show loading state
        this.showLoading(true);
        this.hideError();
        this.hideResults();

        try {
            // Use backend-expected field names
            const response = await fetch(`${this.apiBase}/api/search`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    case_type: caseType,
                    case_number: caseNumber,
                    filing_year: parseInt(filingYear)
                })
            });

            const result = await response.json();

            if (result.success) {
                this.displayResults(result.data);
                this.loadHistory(); // Refresh history
                this.loadStatistics(); // Refresh stats
            } else {
                this.showError(result.error || 'An error occurred while searching.');
            }
        } catch (error) {
            console.error('Search error:', error);
            this.showError('Network error. Please check your connection and try again.');
        } finally {
            this.showLoading(false);
        }
    }

    displayResults(data) {
        const { case_details, orders_judgments } = data;

        // Populate case details with fallback for missing/alternative fields
        this.setElementText('caseId', case_details.case_id || case_details.case_no || '-');
        this.setElementText('courtName', case_details.court_name || '-');
        this.setElementText('caseStatus', case_details.status || '-');
        this.setElementText('caseStage', case_details.stage || case_details.stage_name || '-');
        this.setElementText('petitioner', case_details.petitioner || case_details.petitioner_name || '-');
        this.setElementText('respondent', case_details.respondent || case_details.respondent_name || '-');
        this.setElementText('judgeName', case_details.judge_name || case_details.judge || '-');
        // Format and display dates
        this.setElementText('filingDate', this.formatDate(case_details.filing_date) || '-');
        this.setElementText('nextHearing', this.formatDate(case_details.next_hearing_date) || '-');

        // If raw_response is present, show it in a debug area (or alert for now)
        if (case_details.raw_response) {
            alert('Raw response from court site (for debugging):\n' + case_details.raw_response);
        }

        // Display orders and judgments
        this.displayOrdersJudgments(orders_judgments);

        // Show results section
        this.showResults();
    }

    displayOrdersJudgments(orders) {
        const container = document.getElementById('ordersContainer');
        
        if (!orders || orders.length === 0) {
            container.innerHTML = '<p class="text-muted">No orders or judgments found.</p>';
            return;
        }

        const ordersHtml = orders.map(order => `
            <div class="order-item">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <div class="d-flex align-items-center mb-2">
                            <span class="order-date me-3">
                                <i class="fas fa-calendar me-1"></i>
                                ${this.formatDate(order.order_date) || 'Date not available'}
                            </span>
                            <span class="order-type order-type-${order.order_type ? order.order_type.toLowerCase() : 'document'}">
                                ${order.order_type || 'Document'}
                            </span>
                        </div>
                        <p class="mb-2">${order.description || 'No description available'}</p>
                        ${order.file_size ? `<small class="text-muted">File Size: ${order.file_size}</small>` : ''}
                    </div>
                    <div class="ms-3">
                        ${order.pdf_url ? `
                            <button class="btn pdf-download" onclick="app.downloadPDF('${order.pdf_url}')">
                                <i class="fas fa-download me-1"></i>
                                Download PDF
                            </button>
                        ` : `
                            <span class="text-muted">No PDF available</span>
                        `}
                    </div>
                </div>
            </div>
        `).join('');

        container.innerHTML = ordersHtml;
    }

    async downloadPDF(pdfUrl) {
        try {
            this.showToast('Downloading PDF...', 'info');
            
            const response = await fetch(`${this.apiBase}/api/download/${encodeURIComponent(pdfUrl)}`);
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = this.extractFilenameFromUrl(pdfUrl);
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
                this.showToast('PDF downloaded successfully!', 'success');
            } else {
                const error = await response.json();
                throw new Error(error.error || 'Download failed');
            }
        } catch (error) {
            console.error('Download error:', error);
            this.showToast('Failed to download PDF: ' + error.message, 'error');
        }
    }

    async loadHistory() {
        try {
            const response = await fetch(`${this.apiBase}/api/history?limit=20`);
            const result = await response.json();

            if (result.success) {
                this.displayHistory(result.data);
            }
        } catch (error) {
            console.error('Error loading history:', error);
            document.getElementById('historyContainer').innerHTML = 
                '<p class="text-muted">Failed to load search history.</p>';
        }
    }

    displayHistory(historyData) {
        const container = document.getElementById('historyContainer');
        
        if (!historyData || historyData.length === 0) {
            container.innerHTML = '<p class="text-muted">No search history available.</p>';
            return;
        }

        const historyHtml = historyData.map(item => `
            <div class="history-item ${item.success ? 'history-success' : 'history-error'}">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h6 class="mb-1">
                            ${item.case_type}/${item.case_number}/${item.filing_year}
                            <span class="badge ${item.success ? 'bg-success' : 'bg-danger'} ms-2">
                                ${item.success ? 'Success' : 'Failed'}
                            </span>
                        </h6>
                        <p class="history-timestamp mb-1">
                            <i class="fas fa-clock me-1"></i>
                            ${this.formatDateTime(item.query_timestamp)}
                        </p>
                        ${item.error_message ? `<p class="text-danger mb-0"><small>${item.error_message}</small></p>` : ''}
                    </div>
                    ${item.success ? `
                    <button class="btn btn-sm btn-outline-primary" 
                            onclick="app.loadCaseFromHistory('${item.case_type}', '${item.case_number}', ${item.filing_year})">
                        <i class="fas fa-redo me-1"></i>Search Again
                    </button>
                    ` : ''}
                </div>
            </div>
        `).join('');

        container.innerHTML = historyHtml;
    }

    async loadStatistics() {
        try {
            const response = await fetch(`${this.apiBase}/api/stats`);
            const result = await response.json();

            if (result.success) {
                this.displayStatistics(result.data);
            }
        } catch (error) {
            console.error('Error loading statistics:', error);
        }
    }

    displayStatistics(stats) {
        this.setElementText('totalQueries', stats.total_queries || 0);
        this.setElementText('successfulQueries', stats.successful_queries || 0);
        this.setElementText('uniqueCases', stats.unique_cases || 0);
        this.setElementText('totalOrders', stats.total_orders || 0);
    }

    loadCaseFromHistory(caseType, caseNumber, filingYear) {
        document.getElementById('caseType').value = caseType;
        document.getElementById('caseNumber').value = caseNumber;
        document.getElementById('filingYear').value = filingYear;
        
        // Scroll to search section
        document.getElementById('search-section').scrollIntoView({ 
            behavior: 'smooth' 
        });
        
        // Highlight the form briefly
        const form = document.getElementById('searchForm');
        form.classList.add('border', 'border-primary');
        setTimeout(() => {
            form.classList.remove('border', 'border-primary');
        }, 2000);
    }

    // Utility methods
    setElementText(elementId, text) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = text;
        }
    }

    formatDate(dateString) {
        if (!dateString) return null;
        
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('en-IN', {
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });
        } catch (error) {
            return dateString;
        }
    }

    formatDateTime(dateTimeString) {
        if (!dateTimeString) return 'Unknown';
        
        try {
            const date = new Date(dateTimeString);
            return date.toLocaleString('en-IN', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2digit'
            });
        } catch (error) {
            return dateTimeString;
        }
    }

    extractFilenameFromUrl(url) {
        const pathname = new URL(url).pathname;
        const filename = pathname.split('/').pop();
        return filename || 'document.pdf';
    }

    showLoading(show) {
        const loadingSection = document.getElementById('loadingSection');
        if (show) {
            loadingSection.classList.remove('d-none');
        } else {
            loadingSection.classList.add('d-none');
        }
    }

    showError(message) {
        const errorAlert = document.getElementById('errorAlert');
        const errorMessage = document.getElementById('errorMessage');
        
        errorMessage.textContent = message;
        errorAlert.classList.remove('d-none');
        
        // Auto-hide after 10 seconds
        setTimeout(() => {
            this.hideError();
        }, 10000);
    }

    hideError() {
        const errorAlert = document.getElementById('errorAlert');
        errorAlert.classList.add('d-none');
    }

    showResults() {
        const resultsSection = document.getElementById('resultsSection');
        resultsSection.classList.remove('d-none');
        resultsSection.classList.add('fade-in');
        
        // Scroll to results
        resultsSection.scrollIntoView({ 
            behavior: 'smooth',
            block: 'start'
        });
    }

    hideResults() {
        const resultsSection = document.getElementById('resultsSection');
        resultsSection.classList.add('d-none');
    }

    showToast(message, type = 'info') {
        // Create toast element
        const toast = document.createElement('div');
        toast.className = `alert alert-${type === 'error' ? 'danger' : type} position-fixed`;
        toast.style.cssText = `
            top: 20px;
            right: 20px;
            z-index: 9999;
            min-width: 300px;
            animation: slideInRight 0.3s ease-out;
        `;
        toast.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'} me-2"></i>
                ${message}
                <button type="button" class="btn-close ms-auto" onclick="this.parentElement.parentElement.remove()"></button>
            </div>
        `;

        document.body.appendChild(toast);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, 5000);
    }
}

// Initialize the application and attach to window for global access
window.app = new CourtDataFetcher();

// Global functions for onclick handlers
window.loadHistory = () => window.app.loadHistory();
window.loadStatistics = () => window.app.loadStatistics();

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
`;
document.head.appendChild(style);