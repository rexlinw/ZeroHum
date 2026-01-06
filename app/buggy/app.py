#!/usr/bin/env python3
"""
Buggy Application Service - ZEROHUM-CHAOS
Intentionally simulates an unstable application that crashes and fails health checks.
This version is used to trigger the autonomous self-healing system.
"""

from flask import Flask, jsonify
import logging
import sys
from datetime import datetime
import os
import random
import time

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)

# Application state
app_state = {
    'version': 'buggy-v0.1',
    'status': 'unstable',
    'startup_time': datetime.utcnow().isoformat(),
    'requests_processed': 0,
    'failed_requests': 0,
    'crash_counter': 0
}


@app.route('/health', methods=['GET'])
def health_check():
    """
    Buggy health endpoint - Randomly fails or causes exceptions.
    This simulates a degraded or crashing application.
    """
    app_state['requests_processed'] += 1
    
    # Simulate crash behavior - 30% chance to fail
    if random.random() < 0.3:
        app_state['failed_requests'] += 1
        app_state['crash_counter'] += 1
        
        logger.error(f"Simulated crash! Crash count: {app_state['crash_counter']}")
        
        # Simulate different failure modes
        failure_type = random.choice(['exception', 'timeout', 'bad_response'])
        
        if failure_type == 'exception':
            raise Exception("Simulated application crash - Unhandled exception!")
        elif failure_type == 'timeout':
            time.sleep(10)  # Simulate timeout
            return jsonify({'error': 'Request timeout'}), 504
        else:
            return jsonify({'status': 'unhealthy', 'error': 'Service degraded'}), 500
    
    # Occasional slow responses
    if random.random() < 0.2:
        logger.warning("Slow response detected")
        time.sleep(2)
    
    response = {
        'status': 'unhealthy' if app_state['failed_requests'] > 2 else 'degraded',
        'version': app_state['version'],
        'timestamp': datetime.utcnow().isoformat(),
        'crashes': app_state['crash_counter']
    }
    
    logger.warning(f"Health check degraded - Failures: {app_state['failed_requests']}")
    return jsonify(response), 200 if app_state['failed_requests'] == 0 else 503


@app.route('/metrics', methods=['GET'])
def metrics():
    """
    Metrics endpoint - Returns application metrics including failures.
    """
    error_rate = (app_state['failed_requests'] / max(1, app_state['requests_processed'])) * 100
    
    metrics_data = {
        'version': app_state['version'],
        'total_requests': app_state['requests_processed'],
        'failed_requests': app_state['failed_requests'],
        'error_rate': round(error_rate, 2),
        'crash_count': app_state['crash_counter'],
        'status': 'unstable'
    }
    
    logger.warning(f"Metrics retrieved - Error rate: {error_rate:.2f}%")
    return jsonify(metrics_data), 200


@app.route('/info', methods=['GET'])
def info():
    """
    Information endpoint - Returns application information.
    """
    info_data = {
        'name': 'ZEROHUM-CHAOS Buggy Application',
        'version': app_state['version'],
        'description': 'Unstable application service that crashes',
        'status': app_state['status'],
        'environment': os.getenv('ENVIRONMENT', 'testing'),
        'crash_count': app_state['crash_counter']
    }
    
    logger.warning("Info endpoint accessed")
    return jsonify(info_data), 200


@app.route('/', methods=['GET'])
def index():
    """
    Root endpoint - May fail.
    """
    app_state['requests_processed'] += 1
    
    if random.random() < 0.15:
        app_state['failed_requests'] += 1
        logger.error("Root endpoint failed")
        return jsonify({'error': 'Service unavailable'}), 503
    
    return jsonify({
        'message': 'ZEROHUM-CHAOS Buggy Application (Unstable)',
        'status': 'unstable',
        'version': app_state['version']
    }), 200


@app.route('/ready', methods=['GET'])
def readiness():
    """
    Readiness endpoint - Often reports as not ready due to failures.
    """
    is_ready = app_state['failed_requests'] < 3
    
    return jsonify({'ready': is_ready}), 200 if is_ready else 503


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {error}")
    app_state['failed_requests'] += 1
    return jsonify({'error': 'Internal server error', 'type': 'crash'}), 500


if __name__ == '__main__':
    logger.warning("Starting ZEROHUM-CHAOS Buggy Application Service")
    logger.warning(f"Version: {app_state['version']} (UNSTABLE)")
    logger.warning("This application will experience random failures")
    logger.warning("Running on 0.0.0.0:5000")
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,
        threaded=True
    )
