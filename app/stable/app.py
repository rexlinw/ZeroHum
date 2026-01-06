#!/usr/bin/env python3
"""
Stable Application Service - ZEROHUM-CHAOS
Demonstrates a reliable, healthy application that responds to health checks
and simulates normal operation.
"""

from flask import Flask, jsonify
import logging
import sys
from datetime import datetime
import os

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
    'version': 'stable-v1.0',
    'status': 'healthy',
    'startup_time': datetime.utcnow().isoformat(),
    'requests_processed': 0,
    'healthy_responses': 0
}


@app.route('/health', methods=['GET'])
def health_check():
    """
    Health endpoint - Used by monitoring systems to detect application availability.
    Returns a JSON response indicating the application is running.
    """
    app_state['requests_processed'] += 1
    app_state['healthy_responses'] += 1
    
    response = {
        'status': 'healthy',
        'version': app_state['version'],
        'timestamp': datetime.utcnow().isoformat(),
        'uptime_seconds': (datetime.utcnow().timestamp() - 
                          datetime.fromisoformat(app_state['startup_time']).timestamp())
    }
    
    logger.info(f"Health check passed - Requests: {app_state['requests_processed']}")
    return jsonify(response), 200


@app.route('/metrics', methods=['GET'])
def metrics():
    """
    Metrics endpoint - Returns application metrics.
    Used by monitoring system for additional insights.
    """
    metrics_data = {
        'version': app_state['version'],
        'total_requests': app_state['requests_processed'],
        'healthy_responses': app_state['healthy_responses'],
        'error_rate': 0.0,
        'uptime_seconds': (datetime.utcnow().timestamp() - 
                          datetime.fromisoformat(app_state['startup_time']).timestamp())
    }
    
    logger.info("Metrics retrieved")
    return jsonify(metrics_data), 200


@app.route('/info', methods=['GET'])
def info():
    """
    Information endpoint - Returns application information and current state.
    """
    info_data = {
        'name': 'ZEROHUM-CHAOS Stable Application',
        'version': app_state['version'],
        'description': 'Stable, reliable application service',
        'status': app_state['status'],
        'environment': os.getenv('ENVIRONMENT', 'production'),
        'startup_time': app_state['startup_time']
    }
    
    logger.info("Info endpoint accessed")
    return jsonify(info_data), 200


@app.route('/', methods=['GET'])
def index():
    """
    Root endpoint - Simple welcome message.
    """
    app_state['requests_processed'] += 1
    
    return jsonify({
        'message': 'ZEROHUM-CHAOS Stable Application Running',
        'status': 'online',
        'version': app_state['version']
    }), 200


@app.route('/ready', methods=['GET'])
def readiness():
    """
    Readiness endpoint - Indicates if the application is ready to serve traffic.
    """
    return jsonify({'ready': True}), 200


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    logger.info("Starting ZEROHUM-CHAOS Stable Application Service")
    logger.info(f"Version: {app_state['version']}")
    logger.info("Running on 0.0.0.0:5000")
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,
        threaded=True
    )
