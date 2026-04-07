/* ZEROHUM-CHAOS Dashboard JavaScript - Enhanced */

// API base URL
const API_BASE = window.location.origin;

// State management
let testState = {
    isRunning: false,
    currentScenario: 'default',
    logCount: 0,
    chatHistory: []
};

// Initialize dashboard on load
document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard initialized');
    updateSystemInfo();
    setupChatInput();
    
    // Add keyboard shortcuts
    setupKeyboardShortcuts();
    
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
 * Setup keyboard shortcuts
 */
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Ctrl+Enter to start test
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            if (!testState.isRunning) {
                startTest();
            }
        }
        // Escape to stop test
        if (e.key === 'Escape' && testState.isRunning) {
            stopTest();
        }
    });
}

/**
 * Setup chat input interactions
 */
function setupChatInput() {
    const input = document.getElementById('chatInput');
    if (!input) {
        return;
    }

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendChatMessage();
        }
    });
}

/**
 * Send message to health chat assistant
 */
async function sendChatMessage() {
    const input = document.getElementById('chatInput');
    const sendBtn = document.getElementById('chatSendBtn');
    const message = input ? input.value.trim() : '';

    if (!message) {
        return;
    }

    appendChatMessage('user', message);
    testState.chatHistory.push({ role: 'user', content: message });
    input.value = '';
    setChatBusy(true);

    try {
        const response = await fetch(`${API_BASE}/api/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                history: testState.chatHistory.slice(-10)
            })
        });

        if (!response.ok) {
            throw new Error('Failed to get assistant response');
        }

        const data = await response.json();
        const answer = data.answer || 'No response available.';
        appendChatMessage('assistant', answer, data.source || 'assistant');
        testState.chatHistory.push({ role: 'assistant', content: answer });
    } catch (error) {
        appendChatMessage('assistant', `Error: ${error.message}`, 'error');
    } finally {
        setChatBusy(false);
        if (sendBtn && input) {
            input.focus();
        }
    }
}

/**
 * Toggle floating quick questions tray
 */
function toggleQuickQuestions() {
    const box = document.getElementById('quickQuestionsBox');
    if (!box) {
        return;
    }

    box.classList.toggle('hidden');
}

/**
 * Ask one quick predefined question
 */
function askQuickQuestion(question) {
    const input = document.getElementById('chatInput');
    const box = document.getElementById('quickQuestionsBox');

    if (!input) {
        return;
    }

    input.value = question;
    if (box) {
        box.classList.add('hidden');
    }
    sendChatMessage();
}

/**
 * Toggle chat send state
 */
function setChatBusy(isBusy) {
    const sendBtn = document.getElementById('chatSendBtn');
    const input = document.getElementById('chatInput');
    const quickToggle = document.getElementById('quickQuestionsToggle');
    const quickButtons = document.querySelectorAll('.quick-question-btn');

    if (sendBtn) {
        sendBtn.disabled = isBusy;
        sendBtn.textContent = isBusy ? 'Thinking...' : 'Send';
    }

    if (input) {
        input.disabled = isBusy;
    }

    if (quickToggle) {
        quickToggle.disabled = isBusy;
    }

    quickButtons.forEach((button) => {
        button.disabled = isBusy;
    });
}

/**
 * Render chat message in assistant panel
 */
function appendChatMessage(role, message, source = '') {
    const container = document.getElementById('chatMessages');
    if (!container) {
        return;
    }

    const wrapper = document.createElement('div');
    wrapper.className = `chat-message ${role}`;

    const meta = document.createElement('div');
    meta.className = 'chat-meta';
    meta.textContent = role === 'user' ? 'You' : `Assistant${source ? ` (${source})` : ''}`;

    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble';
    bubble.innerHTML = escapeHtml(message).replace(/\n/g, '<br>');

    wrapper.appendChild(meta);
    wrapper.appendChild(bubble);
    container.appendChild(wrapper);
    container.scrollTop = container.scrollHeight;
}

/**
 * Start a reliability test
 */
async function startTest() {
    if (testState.isRunning) {
        showNotification('Test already running', 'warning');
        return;
    }

    const scenario = document.getElementById('scenarioSelect').value;
    testState.isRunning = true;
    testState.currentScenario = scenario;
    testState.logCount = 0;

    // Update UI
    document.getElementById('runBtn').disabled = true;
    document.getElementById('runBtn').classList.add('loading');
    document.getElementById('stopBtn').disabled = false;
    document.getElementById('progressText').textContent = 'Starting test...';
    updateProgressBar(0, true);

    try {
        const response = await fetch(`${API_BASE}/api/test/start`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ scenario: scenario })
        });

        if (!response.ok) {
            throw new Error(`Server error: ${response.statusText}`);
        }

        const data = await response.json();
        console.log('Test started:', data.scenario);
        showNotification(`Test started: ${data.scenario}`, 'success');

        // Start polling for updates
        updateTestLogs();
        pollTestStatus();

    } catch (error) {
        console.error('Error starting test:', error);
        showNotification('Error starting test: ' + error.message, 'error');
        testState.isRunning = false;
        document.getElementById('runBtn').disabled = false;
        document.getElementById('runBtn').classList.remove('loading');
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
            document.getElementById('runBtn').classList.remove('loading');
            document.getElementById('stopBtn').disabled = true;
            document.getElementById('progressText').textContent = 'Test stopped by user';
            addLog('Test stopped by user', 'warning');
            updateResults();
            showNotification('Test stopped', 'warning');
        }
    } catch (error) {
        console.error('Error stopping test:', error);
        showNotification('Error stopping test', 'error');
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
        if (!response.ok) throw new Error('Failed to fetch status');
        
        const data = await response.json();
        const controller = data.controller_status;

        // Update progress
        if (controller.test_results) {
            const results = controller.test_results;
            
            if (results.status === 'completed') {
                // Fetch one final log snapshot before polling stops.
                await updateTestLogs();
                testState.isRunning = false;
                document.getElementById('runBtn').disabled = false;
                document.getElementById('runBtn').classList.remove('loading');
                document.getElementById('stopBtn').disabled = true;
                updateProgressBar(100, true);
                const statusText = results.final_status.toUpperCase();
                document.getElementById('progressText').textContent = `Test completed: ${statusText}`;
                showNotification(`Test completed with status: ${statusText}`, 'success');
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
        if (!response.ok) throw new Error('Failed to fetch logs');
        
        const data = await response.json();
        const logContainer = document.getElementById('logContainer');
        const logs = data.logs;

        if (logs.length > 0) {
            // Check if we need to clear old logs
            const existingLogs = logContainer.querySelectorAll('.log-entry');
            if (existingLogs.length === 0 && logContainer.querySelector('.log-placeholder')) {
                logContainer.innerHTML = '';
            }

            // Append new logs
            logs.forEach(log => {
                if (!document.querySelector(`[data-log-time="${log.timestamp}"]`)) {
                    testState.logCount++;
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
            updateProgressBar(testState.logCount);
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
        if (!response.ok) throw new Error('Failed to fetch results');
        
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
                <div class="result-card-value">${results.recovery_actions_executed || 0}</div>
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
                    <div class="result-card-value">YES</div>
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
        if (!response.ok) throw new Error('Failed to fetch system info');
        
        const status = await response.json();
        const container = document.getElementById('sysInfoContainer');
        let html = '';

        // Prometheus
        html += `
            <div class="sys-info-item">
                <div class="sys-info-label">Prometheus</div>
                <div class="sys-info-value">
                    <a href="http://localhost:9090/graph?g0.expr=up&g0.tab=0" target="_blank" title="Open Prometheus">http://localhost:9090/graph</a>
                </div>
            </div>
        `;

        // Grafana
        html += `
            <div class="sys-info-item">
                <div class="sys-info-label">Grafana</div>
                <div class="sys-info-value">
                    <a href="http://localhost:3000/d/zerohum-test-metrics" target="_blank" title="Open Grafana">http://localhost:3000/d/...</a>
                </div>
            </div>
        `;

        // Controller
        const controller = status.controller_status;
        html += `
            <div class="sys-info-item">
                <div class="sys-info-label">Current Version</div>
                <div class="sys-info-value">${controller.current_version || 'Unknown'}</div>
            </div>
        `;

        // Decision History
        html += `
            <div class="sys-info-item">
                <div class="sys-info-label">Decisions Made</div>
                <div class="sys-info-value">${controller.decision_history_count || 0}</div>
            </div>
        `;

        // Recovery Actions
        html += `
            <div class="sys-info-item">
                <div class="sys-info-label">Recovery Actions</div>
                <div class="sys-info-value">${controller.recovery_actions_count || 0}</div>
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
        document.getElementById('sysInfoContainer').innerHTML = 
            '<p style="color: #f44336;">Error loading system information</p>';
    }
}

/**
 * Clear test logs
 */
function clearLogs() {
    document.getElementById('logContainer').innerHTML = '<p class="log-placeholder">Test logs cleared</p>';
    testState.logCount = 0;
    updateProgressBar(0);
}

/**
 * Add log entry (client-side)
 */
function addLog(message, level = 'info') {
    const logContainer = document.getElementById('logContainer');
    
    if (logContainer.querySelector('.log-placeholder')) {
        logContainer.innerHTML = '';
    }

    testState.logCount++;
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
function updateProgressBar(value, isPercent = false) {
    const maxLogs = 50;
    const progress = isPercent
        ? Math.min(Math.max(value, 0), 100)
        : Math.min((value / maxLogs) * 100, 100);
    
    const fill = document.getElementById('progressFill');
    fill.style.width = progress + '%';
    
    const percentage = Math.round(progress);
    fill.textContent = percentage > 0 ? percentage + '%' : '';
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

/**
 * Show notification toast
 */
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        background: ${type === 'success' ? '#4CAF50' : type === 'error' ? '#F44336' : type === 'warning' ? '#FF9800' : '#2196F3'};
        color: white;
        border-radius: 6px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10000;
        font-weight: 600;
        animation: slideDown 0.3s ease forwards;
    `;
    
    notification.textContent = message;
    document.body.appendChild(notification);
    
    // Auto-remove after 4 seconds
    setTimeout(() => {
        notification.style.animation = 'slideUp 0.3s ease forwards';
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 4000);
}

/**
 * Train ML predictor models
 */
function trainPredictor() {
    const container = document.getElementById('predictionsContainer');
    container.innerHTML = '<p style="color: #2196F3;">Training ML models...</p>';
    
    fetch(`${API_BASE}/api/ml/train`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            container.innerHTML = `
                <div class="success-message">
                    <h3>Models Trained Successfully</h3>
                    <p>${Object.keys(data.models_trained).length} model(s) trained</p>
                    <pre style="background: #f5f5f5; padding: 1rem; border-radius: 4px; font-size: 0.9rem; max-height: 200px; overflow-y: auto;">
${JSON.stringify(data.models_trained, null, 2)}
                    </pre>
                </div>
            `;
            showNotification('ML models trained successfully', 'success');
        } else {
            container.innerHTML = `
                <div class="warning-message">
                    <p>Status: ${data.status}</p>
                    <p>Message: ${data.reason || data.error || 'Unknown error'}</p>
                </div>
            `;
        }
    })
    .catch(err => {
        container.innerHTML = `<p style="color: #F44336;">Error training models: ${err.message}</p>`;
        console.error('Training error:', err);
    });
}

/**
 * Get predictions from trained ML models
 */
function getPredictions() {
    const container = document.getElementById('predictionsContainer');
    container.innerHTML = '<p style="color: #2196F3;">Generating predictions...</p>';
    
    fetch(`${API_BASE}/api/ml/predict`)
    .then(res => res.json())
    .then(data => {
        if (data.predictions) {
            const predictions = data.predictions;
            let html = `
                <div class="predictions-box">
                    <div class="risk-badge risk-${predictions.risk_level}">
                        ${predictions.risk_level.toUpperCase()}
                    </div>
                    <p><strong>Forecast Period:</strong> ${predictions.forecast_period_minutes} minutes ahead</p>
                    <p><strong>Generated:</strong> ${new Date(predictions.timestamp).toLocaleTimeString()}</p>
            `;
            
            // Display metric predictions
            if (predictions.metrics && Object.keys(predictions.metrics).length > 0) {
                html += '<h4 style="color: white; margin: 1.5rem 0 1rem 0; font-size: 1.1rem;">Metric Predictions:</h4><div class="metrics-grid">';
                for (const [metric, pred] of Object.entries(predictions.metrics)) {
                    if (pred.status !== 'error') {
                        const isWarning = pred.near_threshold === true || pred.status_level === 'warning';
                        const isBreach = pred.will_breach === true || pred.status_level === 'breach';
                        const riskColor = isBreach ? '#FF6B6B' : (isWarning ? '#FFD700' : '#90EE90');
                        const statusText = isBreach ? 'Breach Predicted' : (isWarning ? 'Near Threshold' : 'Safe');
                        const statusStyle = isBreach
                            ? 'color: #FF6B6B; font-weight: 600;'
                            : (isWarning ? 'color: #FFD700; font-weight: 600;' : 'color: #90EE90; font-weight: 600;');
                        html += `
                            <div class="metric-prediction" style="border-left: 4px solid ${riskColor};">
                                <strong>${metric}</strong>
                                <div style="font-size: 0.9rem; color: rgba(255, 255, 255, 0.9);">
                                    <p>Predicted: <strong>${pred.predicted_max.toFixed(1)}</strong></p>
                                    <p>Threshold: ${pred.threshold}</p>
                                    <p>Risk Score: ${pred.risk_score.toFixed(1)}%</p>
                                    <p style="${statusStyle}">${statusText}</p>
                                </div>
                            </div>
                        `;
                    }
                }
                html += '</div>';
            }
            
            // Display alerts
            if (predictions.alerts && predictions.alerts.length > 0) {
                html += '<h4 style="color: #FFD700; margin: 1.5rem 0 1rem 0; font-size: 1.1rem;">Alerts:</h4><ul style="color: rgba(255, 255, 255, 0.9);">';
                for (const alert of predictions.alerts) {
                    html += `
                        <li style="color: ${alert.severity === 'high' ? '#FF6B6B' : '#FFD700'}; margin-bottom: 1rem;">
                            <strong>${alert.metric}:</strong> ${alert.message}<br>
                            <small style="color: rgba(255, 255, 255, 0.7);">Predicted value: ${alert.predicted_value.toFixed(1)}</small>
                        </li>
                    `;
                }
                html += '</ul>';
            }
            
            html += '</div>';
            container.innerHTML = html;
            
            // Display recommendations
            if (data.recommendations) {
                const recList = document.getElementById('recommendationsList');
                recList.innerHTML = '';
                for (const rec of data.recommendations) {
                    const item = document.createElement('li');
                    item.textContent = rec;
                    recList.appendChild(item);
                }
                document.getElementById('recommendationsContainer').classList.remove('hidden');
            }
        } else {
            container.innerHTML = `
                <div class="info-message">
                    <p>${data.reason || 'Models not yet trained'}</p>
                    <p style="font-size: 0.9rem; color: #666; margin-top: 0.5rem;">
                        ${data.recommendations ? data.recommendations.join(' | ') : 'Run tests to collect data for training'}
                    </p>
                </div>
            `;
        }
    })
    .catch(err => {
        container.innerHTML = `<p style="color: #F44336;">Error getting predictions: ${err.message}</p>`;
        console.error('Prediction error:', err);
    });
}

/**
 * Get SLO status and display on dashboard
 */
function getSLOStatus() {
    const container = document.getElementById('slosContainer');
    if (!container) return;
    
    container.innerHTML = '<p class="slos-placeholder">Loading SLO status...</p>';
    
    fetch(`${API_BASE}/api/slo/status`)
        .then(res => res.json())
        .then(data => {
            if (!data.slos || data.slos.length === 0) {
                container.innerHTML = '<p class="slos-placeholder">No SLOs configured. Create SLOs to get started.</p>';
                return;
            }
            
            let html = '<div class="slo-list">';
            for (const slo of data.slos) {
                const status = slo.current_value <= slo.target_value ? 'success' : 'warning';
                const statusIcon = status === 'success' ? 'OK' : 'WARN';
                const percentage = ((slo.target_value - slo.current_value) / slo.target_value * 100).toFixed(1);
                
                html += `
                    <div class="slo-item ${status}">
                        <div class="slo-header">
                            <span class="slo-name">${slo.name}</span>
                            <span class="slo-status-badge ${status}">${statusIcon}</span>
                        </div>
                        <div class="slo-details">
                            <p><strong>${slo.metric}:</strong> ${slo.current_value.toFixed(2)} / ${slo.target_value.toFixed(2)}</p>
                            <p style="font-size: 0.85rem; margin-top: 0.25rem;">${percentage}% margin remaining</p>
                        </div>
                    </div>
                `;
            }
            html += '</div>';
            container.innerHTML = html;
        })
        .catch(err => {
            container.innerHTML = `<p class="slos-placeholder" style="color: #FF9800;">Error loading SLOs: ${err.message}</p>`;
            console.error('SLO status error:', err);
        });
}

/**
 * Get SLO compliance report
 */
function getSLOReport() {
    const reportContainer = document.getElementById('sloReportContainer');
    const reportDetails = document.getElementById('sloReportDetails');
    if (!reportContainer || !reportDetails) return;
    
    reportDetails.innerHTML = '<p style="color: rgba(255,255,255,0.7);">Loading SLO compliance report...</p>';
    reportContainer.classList.remove('hidden');
    
    fetch(`${API_BASE}/api/slo/report`)
        .then(res => res.json())
        .then(data => {
            if (data.status === 'no_data') {
                reportDetails.innerHTML = `
                    <div class="info-message">
                        <p>${data.message || 'No test history available yet.'}</p>
                        <p style="font-size: 0.9rem; color: rgba(255,255,255,0.75); margin-top: 0.5rem;">
                            ${data.recommendations ? data.recommendations.join(' | ') : 'Run chaos tests to generate SLO compliance data.'}
                        </p>
                    </div>
                `;
                return;
            }

            const complianceValue = typeof data.overall_compliance === 'number'
                ? data.overall_compliance
                : parseFloat(data?.statistics?.compliance_rate);
            const complianceText = Number.isFinite(complianceValue) ? `${complianceValue.toFixed(1)}%` : (data?.statistics?.compliance_rate || 'N/A');
            const statusText = data.compliant === true ? 'COMPLIANT' : data.compliant === false ? 'NON-COMPLIANT' : (data?.latest_evaluation?.overall_slo_health || 'UNKNOWN').toUpperCase();

            let html = `
                <p><strong>Report Generated:</strong> ${data.generated_at || data.timestamp || 'Unknown'}</p>
                <p><strong>Overall Compliance:</strong> ${complianceText}</p>
                <p><strong>Status:</strong> ${statusText}</p>
            `;
            
            if (Array.isArray(data.violations) && data.violations.length > 0) {
                html += '<h4 style="margin-top: 1rem; color: #FF9800;">Violations Detected:</h4><ul>';
                for (const violation of data.violations) {
                    html += `<li>${violation.slo_name}: ${violation.reason}</li>`;
                }
                html += '</ul>';
            }
            
            if (Array.isArray(data.test_results) && data.test_results.length > 0) {
                html += '<h4 style="margin-top: 1rem;">Recent Test Results:</h4><ul>';
                for (const result of data.test_results.slice(0, 5)) {
                    html += `<li>${result.test_status || result.scenario || 'Test'}: ${result.overall_slo_health || result.status || 'unknown'}</li>`;
                }
                html += '</ul>';
            }
            
            reportDetails.innerHTML = html;
        })
        .catch(err => {
            reportDetails.innerHTML = `<p style="color: #FF9800;">Error generating report: ${err.message}</p>`;
            console.error('SLO report error:', err);
        });
}
