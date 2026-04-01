#!/usr/bin/env python3
"""
Buggy Application Service - ZEROHUM-CHAOS
Intentionally simulates an unstable application with CRITICAL bugs.
This version triggers autonomous self-healing through chaos injection.
"""

from flask import Flask, jsonify, request
import logging
import sys
from datetime import datetime
import os
import random
import time
import threading
from collections import deque
from functools import lru_cache

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

# FIXED: Add global lock for thread-safe state modifications
state_lock = threading.Lock()

# Application state - NOW WITH PROPER SYNCHRONIZATION
app_state = {
    'version': 'buggy-v0.1',
    'status': 'unstable',
    'startup_time': datetime.utcnow().isoformat(),
    'requests_processed': 0,
    'failed_requests': 0,
    'crash_counter': 0,
    'request_history': deque(maxlen=100),  # FIXED: Bounded queue with max 100 items
    'locks_held': 0,
    'computation_cache': {}  # Will use LRU cache instead
}

# FIXED: Configuration constants for input validation
MAX_ITERATIONS = 10000
MAX_CACHE_SIZE = 10


@app.route('/health', methods=['GET'])
def health_check():
    """
    FIXED health endpoint with proper synchronization and error handling.
    Now uses locks to prevent race conditions and bounded history.
    """
    # FIXED #1 & #2: Use lock for thread-safe state modification
    with state_lock:
        app_state['requests_processed'] += 1
        
        # FIXED #2: Using bounded deque instead of unbounded list
        app_state['request_history'].append({
            'timestamp': datetime.utcnow().isoformat(),
            'pid': os.getpid(),
            'data': 'x' * 1024
        })
    
    # Simulate crash behavior - 40% chance to fail
    if random.random() < 0.4:
        with state_lock:
            app_state['failed_requests'] += 1
            app_state['crash_counter'] += 1
        
        logger.error(f"Simulated crash! Crash count: {app_state['crash_counter']}")
        
        # Simulate different failure modes
        failure_type = random.choice(['exception', 'timeout', 'bad_response', 'division_error'])
        
        if failure_type == 'exception':
            raise Exception("Simulated application crash - Unhandled exception!")
        elif failure_type == 'timeout':
            time.sleep(12)  # Simulate timeout
            return jsonify({'error': 'Request timeout'}), 504
        elif failure_type == 'division_error':
            # FIXED #3: Proper bounds checking instead of division by zero
            if app_state['requests_processed'] > 0:
                ratio = 100 / app_state['requests_processed']
            else:
                ratio = 0
            return jsonify({'ratio': ratio}), 200
        else:
            return jsonify({'status': 'unhealthy', 'error': 'Service degraded'}), 500
    
    # Occasional slow responses
    if random.random() < 0.2:
        logger.warning("Slow response detected")
        time.sleep(3)
    
    # FIXED: Read state safely within lock
    with state_lock:
        response = {
            'status': 'unhealthy' if app_state['failed_requests'] > 2 else 'degraded',
            'version': app_state['version'],
            'timestamp': datetime.utcnow().isoformat(),
            'crashes': app_state['crash_counter'],
            'queue_size': len(app_state['request_history'])
        }
        failed_count = app_state['failed_requests']
    
    logger.warning(f"Health check degraded - Failures: {failed_count}")
    return jsonify(response), 200 if failed_count == 0 else 503


@app.route('/metrics', methods=['GET'])
def metrics():
    """
    FIXED metrics endpoint with proper cache management and type safety.
    """
    # FIXED #4: Implement cache size limit
    cache_key = f"metrics_{datetime.utcnow().strftime('%Y%m%d')}"
    if cache_key not in app_state['computation_cache']:
        # Limit cache size
        if len(app_state['computation_cache']) >= MAX_CACHE_SIZE:
            oldest_key = min(
                app_state['computation_cache'],
                key=lambda k: app_state['computation_cache'][k]['computed_at']
            )
            del app_state['computation_cache'][oldest_key]
        
        app_state['computation_cache'][cache_key] = {
            'computed_at': datetime.utcnow().isoformat(),
            'values': list(range(1000))  # Reduced from 10000 to prevent exhaustion
        }
    
    # FIXED #5 & #6: Proper error handling and type consistency
    with state_lock:
        if app_state['requests_processed'] == 0:
            error_rate = 0.0
        else:
            error_rate = (app_state['failed_requests'] / app_state['requests_processed']) * 100
        
        # FIXED #5: Keep as integer, not string
        metrics_data = {
            'version': app_state['version'],
            'total_requests': app_state['requests_processed'],  # Now correctly an int
            'failed_requests': app_state['failed_requests'],
            'error_rate': round(error_rate, 2),
            'crash_count': app_state['crash_counter'],
            'cache_size': len(app_state['computation_cache']),
            'status': 'unstable'
        }
    
    logger.warning(f"Metrics retrieved - Error rate: {error_rate:.2f}%")
    return jsonify(metrics_data), 200


@app.route('/compute', methods=['POST'])
def compute():
    """
    FIXED compute endpoint with proper input validation and error handling.
    """
    try:
        # FIXED #7: Add proper input validation
        data = request.get_json() or {}
        
        try:
            iterations = int(data.get('iterations', 1000))
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid iterations parameter - must be integer'}), 400
        
        # FIXED #7 & #8: Proper bounds checking
        if iterations < 1 or iterations > MAX_ITERATIONS:
            return jsonify({
                'error': f'Iterations must be between 1 and {MAX_ITERATIONS}'
            }), 400
        
        # Safe computation
        result = sum(i ** 2 for i in range(iterations))
        return jsonify({'result': result, 'iterations': iterations}), 200
    
    except Exception as e:
        # FIXED #9: Return proper 500 status code on error
        logger.error(f"Compute failed: {str(e)}")
        return jsonify({
            'error': 'Computation failed',
            'type': type(e).__name__,
            'message': str(e)
        }), 500


@app.route('/info', methods=['GET'])
def info():
    """
    FIXED information endpoint - No longer leaks internal state.
    """
    with state_lock:
        info_data = {
            'name': 'ZEROHUM-CHAOS Buggy Application',
            'version': app_state['version'],
            'description': 'Unstable application service for testing autonomous recovery',
            'status': app_state['status'],
            'environment': os.getenv('ENVIRONMENT', 'testing')
            # FIXED #13: Removed memory_queue_size and cache_keys - no internal state leakage
        }
    
    logger.warning("Info endpoint accessed")
    return jsonify(info_data), 200


@app.route('/', methods=['GET'])
def index():
    """
    FIXED root endpoint - Now with proper synchronization.
    """
    # FIXED #10: Use lock for thread-safe state modification
    with state_lock:
        app_state['requests_processed'] += 1
        
        if random.random() < 0.15:
            app_state['failed_requests'] += 1
            logger.error("Root endpoint failed")
            # FIXED #11: Consistent HTTP responses, no random exceptions
            return jsonify({
                'error': 'Service unavailable',
                'message': 'Too many failures, service degraded'
            }), 503
    
    return jsonify({
        'message': 'ZEROHUM-CHAOS Buggy Application (Unstable)',
        'status': 'unstable',
        'version': app_state['version'],
        'uptime_seconds': (datetime.utcnow() - datetime.fromisoformat(app_state['startup_time'])).total_seconds()
    }), 200


@app.route('/ready', methods=['GET'])
def readiness():
    """
    FIXED readiness endpoint with correct logic.
    """
    # FIXED #12: Correct logic - application is ready when failures are LOW
    with state_lock:
        is_ready = app_state['failed_requests'] < 3
    
    # FIXED: Correct HTTP status codes
    status_code = 200 if is_ready else 503
    
    return jsonify({'ready': is_ready}), status_code


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
