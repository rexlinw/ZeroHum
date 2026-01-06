/* ZEROHUM-CHAOS Dashboard JavaScript */

// API base URL
const API_BASE = window.location.origin;

// State management
let testState = {
    isRunning: false,
    currentScenario: 'default'
};

// Initialize dashboard on load
document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard loaded');
    updateSystemInfo();
    
    // Update system info every 5 seconds
    setInterval(updateSystemInfo, 5000);
    
    // Poll test status if running
    setInterval(function() {
        if (testState.isRunning) {
            updateTestLogs();
        }
    }, 1000);
});

/**
 * Start a reliability test
 */
async function startTest() {
    if (testState.isRunning) {
        alert('Test already running');
        return;
    }

    const scenario = document.getElementById('scenarioSelect').value;
    testState.isRunning = true;
    testState.currentScenario = scenario;

    // Update UI
    document.getElementById('runBtn').disabled = true;
    document.getElementById('stopBtn').disabled = false;
    document.getElementById('progressText').textContent = 'Starting test...';

    try {
        const response = await fetch(`${API_BASE}/api/test/start`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ scenario: scenario })
        });

        if (!response.ok) {
            throw new Error('Failed to start test');
        }

        const data = await response.json();
        console.log('Test started:', data);

        // Start polling for updates
        updateTestLogs();
        pollTestStatus();

    } catch (error) {
        console.error('Error starting test:', error);
        alert('Error starting test: ' + error.message);
        testState.isRunning = false;
        document.getElementById('runBtn').disabled = false;
        document.getElementById('stopBtn').disabled = true;
    }
}

/**
 * Stop running test
 */
async function stopTest() {
    try {
        const response = await fetch(`${API_BASE}/api/test/stop`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            testState.isRunning = false;
            document.getElementById('runBtn').disabled = false;
            document.getElementById('stopBtn').disabled = true;
            document.getElementById('progressText').textContent = 'Test stopped';
            addLog('Test stopped by user', 'warning');
            updateResults();
        }
    } catch (error) {
        console.error('Error stopping test:', error);
    }
}

/**
 * Poll test status
 */
async function pollTestStatus() {
    if (!testState.isRunning) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/status`);
        const data = await response.json();

        const controller = data.controller_status;

        // Update progress
        if (controller.test_results) {
            const results = controller.test_results;
            
            if (results.status === 'completed') {
                testState.isRunning = false;
                document.getElementById('runBtn').disabled = false;
                document.getElementById('stopBtn').disabled = true;
                document.getElementById('progressText').textContent = `Test completed: ${results.final_status.toUpperCase()}`;
                updateResults();
                return;
            }
        }

        // Continue polling
        setTimeout(pollTestStatus, 2000);

    } catch (error) {
        console.error('Error polling status:', error);
    }
}

/**
 * Update test logs from server
 */
async function updateTestLogs() {
    try {
        const response = await fetch(`${API_BASE}/api/test/logs`);
        const data = await response.json();

        const logContainer = document.getElementById('logContainer');
        const logs = data.logs;

        if (logs.length > 0) {
            // Check if we need to clear old logs
            const existingLogs = logContainer.querySelectorAll('.log-entry');
            if (existingLogs.length === 0) {
                logContainer.innerHTML = '';
            }

            // Append new logs
            logs.forEach(log => {
                if (!document.querySelector(`[data-log-time="${log.timestamp}"]`)) {
                    const entry = document.createElement('div');
                    entry.className = 'log-entry';
                    entry.setAttribute('data-log-time', log.timestamp);

                    const timestamp = formatTime(log.timestamp);
                    const level = log.level.toUpperCase();

                    entry.innerHTML = `
                        <span class="log-timestamp">${timestamp}</span>
                        <span class="log-level ${log.level}">[${level}]</span>
                        <span class="log-message">${escapeHtml(log.message)}</span>
                    `;

                    logContainer.appendChild(entry);
                    logContainer.scrollTop = logContainer.scrollHeight;
                }
            });

            // Update progress
            updateProgressBar(logs.length);
        }

    } catch (error) {
        console.error('Error updating logs:', error);
    }
}

/**
 * Update results display
 */
async function updateResults() {
    try {
        const response = await fetch(`${API_BASE}/api/results`);
        const results = await response.json();

        const container = document.getElementById('resultsContainer');

        if (results.status === 'pending' || results.status === 'idle') {
            container.innerHTML = '<p class="results-placeholder">Run a test to see results</p>';
            return;
        }

        let html = '';

        // Test Status
        const statusClass = results.final_status === 'passed' ? 'success' : 
                          results.final_status === 'failed' ? 'failure' : 'running';
        
        html += `
            <div class="result-card ${statusClass}">
                <div class="result-card-label">Test Status</div>
                <div class="result-card-value">${results.final_status ? results.final_status.toUpperCase() : 'PENDING'}</div>
                <div class="result-card-status">${results.status}</div>
            </div>
        `;

        // Failures Detected
        html += `
            <div class="result-card">
                <div class="result-card-label">Failures Detected</div>
                <div class="result-card-value">${results.failures_detected || 0}</div>
                <div class="result-card-status">anomalies found</div>
            </div>
        `;

        // Recovery Actions
        html += `
            <div class="result-card">
                <div class="result-card-label">Recovery Actions</div>
                <div class="result-card-value">${results.recovery_actions || 0}</div>
                <div class="result-card-status">executed</div>
            </div>
        `;

        // Test Duration
        if (results.start_time && results.end_time) {
            const duration = (new Date(results.end_time) - new Date(results.start_time)) / 1000;
            html += `
                <div class="result-card">
                    <div class="result-card-label">Duration</div>
                    <div class="result-card-value">${duration.toFixed(1)}s</div>
                    <div class="result-card-status">total time</div>
                </div>
            `;
        }

        // Chaos Injected
        if (results.chaos_injected) {
            html += `
                <div class="result-card">
                    <div class="result-card-label">Chaos Injected</div>
                    <div class="result-card-value">✓</div>
                    <div class="result-card-status">${results.chaos_injected}</div>
                </div>
            `;
        }

        container.innerHTML = html;

    } catch (error) {
        console.error('Error updating results:', error);
    }
}

/**
 * Update system information
 */
async function updateSystemInfo() {
    try {
        const response = await fetch(`${API_BASE}/api/status`);
        const status = await response.json();

        const container = document.getElementById('sysInfoContainer');
        let html = '';

        // Prometheus
        html += `
            <div class="sys-info-item">
                <div class="sys-info-label">Prometheus</div>
                <div class="sys-info-value">
                    <a href="${status.prometheus_url}" target="_blank">http://localhost:9090</a>
                </div>
            </div>
        `;

        // Grafana
        html += `
            <div class="sys-info-item">
                <div class="sys-info-label">Grafana</div>
                <div class="sys-info-value">
                    <a href="${status.grafana_url}" target="_blank">http://localhost:3000</a>
                </div>
            </div>
        `;

        // Controller
        const controller = status.controller_status;
        html += `
            <div class="sys-info-item">
                <div class="sys-info-label">Current Version</div>
                <div class="sys-info-value">${controller.current_version}</div>
            </div>
        `;

        // Decision History
        html += `
            <div class="sys-info-item">
                <div class="sys-info-label">Decisions Made</div>
                <div class="sys-info-value">${controller.decision_history_count}</div>
            </div>
        `;

        // Recovery Actions
        html += `
            <div class="sys-info-item">
                <div class="sys-info-label">Recovery Actions</div>
                <div class="sys-info-value">${controller.recovery_actions_count}</div>
            </div>
        `;

        // Last Check
        html += `
            <div class="sys-info-item">
                <div class="sys-info-label">Last Update</div>
                <div class="sys-info-value">${formatTime(status.timestamp)}</div>
            </div>
        `;

        container.innerHTML = html;

    } catch (error) {
        console.error('Error updating system info:', error);
    }
}

/**
 * Clear test logs
 */
function clearLogs() {
    document.getElementById('logContainer').innerHTML = '<p class="log-placeholder">Test logs cleared</p>';
}

/**
 * Add log entry (client-side)
 */
function addLog(message, level = 'info') {
    const logContainer = document.getElementById('logContainer');
    
    if (logContainer.querySelector('.log-placeholder')) {
        logContainer.innerHTML = '';
    }

    const entry = document.createElement('div');
    entry.className = 'log-entry';

    const timestamp = new Date().toLocaleTimeString();
    const levelUpper = level.toUpperCase();

    entry.innerHTML = `
        <span class="log-timestamp">${timestamp}</span>
        <span class="log-level ${level}">[${levelUpper}]</span>
        <span class="log-message">${escapeHtml(message)}</span>
    `;

    logContainer.appendChild(entry);
    logContainer.scrollTop = logContainer.scrollHeight;
}

/**
 * Update progress bar
 */
function updateProgressBar(logCount) {
    const maxLogs = 50;
    const progress = Math.min((logCount / maxLogs) * 100, 95);
    
    const fill = document.getElementById('progressFill');
    fill.style.width = progress + '%';
    
    const percentage = Math.round(progress);
    fill.textContent = percentage + '%';
}

/**
 * Format timestamp to readable time
 */
function formatTime(timestamp) {
    try {
        const date = new Date(timestamp);
        return date.toLocaleTimeString('en-US', { 
            hour12: false, 
            hour: '2-digit', 
            minute: '2-digit', 
            second: '2-digit' 
        });
    } catch (e) {
        return timestamp;
    }
}

/**
 * Escape HTML special characters
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
