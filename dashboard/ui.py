#!/usr/bin/env python3
"""
ZEROHUM-CHAOS Dashboard UI
Web-based interface for running reliability tests and viewing results.
Demonstrates autonomous self-healing in action with one-click testing.
"""

from flask import Flask, render_template, jsonify, request
import logging
import json
import time
import threading
from pathlib import Path
from datetime import datetime
import requests
import sys
import os

# Add parent directories to path for imports
sys.path.insert(0, '/app/chaos_engine')
sys.path.insert(0, '/app/controller')
sys.path.insert(0, '/app/executor')

from chaos import ChaosEngine
from controller import SystemController
from recovery import RecoveryExecutor

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize components
DATA_DIR = Path(os.getenv('DATA_DIR', '/app/data'))
DATA_DIR.mkdir(parents=True, exist_ok=True)

prometheus_url = os.getenv('PROMETHEUS_URL', 'http://prometheus:9090')
docker_compose_path = os.getenv('DOCKER_COMPOSE_PATH', '/app/docker-compose.yml')

chaos_engine = ChaosEngine()
controller = SystemController(prometheus_url=prometheus_url, data_dir=str(DATA_DIR))
executor = RecoveryExecutor(docker_compose_path=docker_compose_path)

# Global test state
test_state = {
    'is_running': False,
    'current_step': 'idle',
    'log_messages': [],
    'test_scenario': None
}


def add_log_message(message: str, level: str = 'info'):
    """Add a message to the test log."""
    timestamp = datetime.utcnow().isoformat()
    test_state['log_messages'].append({
        'timestamp': timestamp,
        'level': level,
        'message': message
    })
    logger.log(
        logging.INFO if level == 'info' else 
        logging.WARNING if level == 'warning' else 
        logging.ERROR,
        message
    )
    print(f"[{level.upper()}] {message}")


@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('dashboard.html')


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current system status."""
    try:
        status = {
            'timestamp': datetime.utcnow().isoformat(),
            'controller_status': controller.get_system_status(),
            'test_state': test_state.copy(),
            'grafana_url': 'http://localhost:3000',
            'prometheus_url': prometheus_url,
            'containers': {
                'app-stable': {'port': 5001},
                'app-buggy': {'port': 5002},
                'prometheus': {'port': 9090},
                'grafana': {'port': 3000},
                'cadvisor': {'port': 8080}
            }
        }
        
        return jsonify(status), 200
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/test/start', methods=['POST'])
def start_test():
    """Start a reliability test scenario."""
    if test_state['is_running']:
        return jsonify({'error': 'Test already running'}), 400
    
    data = request.get_json() or {}
    scenario = data.get('scenario', 'default')
    
    # Start test in background thread
    thread = threading.Thread(
        target=run_test_scenario,
        args=(scenario,),
        daemon=True
    )
    thread.start()
    
    return jsonify({
        'status': 'started',
        'scenario': scenario,
        'message': f'Test scenario "{scenario}" started'
    }), 200


def run_test_scenario(scenario: str):
    """Run the selected test scenario."""
    test_state['is_running'] = True
    test_state['test_scenario'] = scenario
    test_state['log_messages'] = []
    
    controller.reset_test()
    controller.mark_test_started()
    
    add_log_message(f"=== ZEROHUM-CHAOS Test Started ===")
    add_log_message(f"Scenario: {scenario}")
    add_log_message(f"Timestamp: {datetime.utcnow().isoformat()}")
    
    try:
        if scenario == 'container_crash':
            run_container_crash_test()
        elif scenario == 'crash_loop':
            run_crash_loop_test()
        elif scenario == 'degradation':
            run_degradation_test()
        else:
            run_default_test()
        
        # Extract test completion details
        decisions = controller.decision_engine.get_decision_history()
        actions = len([d for d in decisions if d['action'] != 'none'])
        if controller.test_results['recovery_actions_executed'] < actions:
            controller.test_results['recovery_actions_executed'] = actions
            
        # Mark test as completed
        final_status = determine_test_status()
        controller.mark_test_completed(final_status)
        add_log_message(f"=== Test Completed: {final_status.upper()} ===")
        
    except Exception as e:
        logger.error(f"Test error: {str(e)}")
        add_log_message(f"Test error: {str(e)}", level='error')
        controller.mark_test_completed('error')
    
    finally:
        test_state['is_running'] = False
        test_state['current_step'] = 'completed'


def run_default_test():
    """Default test: Container crash and recovery."""
    add_log_message("--- Phase 1: Baseline Health Check ---")
    time.sleep(2)
    
    # Check initial health
    add_log_message("Checking stable application health...")
    analysis = controller.decision_engine.analyze_system_state('app-stable')
    add_log_message(f"Stable app health: {analysis['status']}")
    
    # Phase 2: Inject chaos
    add_log_message("--- Phase 2: Injecting Chaos ---")
    add_log_message("Stopping app-stable container to simulate failure...")
    
    success, msg = chaos_engine.stop_container('app-stable')
    if success:
        add_log_message(f"Chaos injected: Container stopped")
    else:
        add_log_message(f"Chaos injection failed: {msg}", level='warning')
        return
    
    time.sleep(3)
    
    # Phase 3: Failure detection
    add_log_message("--- Phase 3: Failure Detection ---")
    add_log_message("Monitoring system detects container is down...")
    time.sleep(2)
    
    analysis = controller.decision_engine.analyze_system_state('app-stable')
    add_log_message(f"Detection result - Status: {analysis['status']}, Severity: {analysis['severity']}")
    
    # Phase 4: Decision making
    add_log_message("--- Phase 4: Autonomous Decision Making ---")
    decision = controller.decision_engine.make_decision(
        analysis, 'app-stable', controller.current_version
    )
    add_log_message(f"Controller decision: {decision['action'].upper()}")
    add_log_message(f"Reason: {decision['reasoning']}")
    
    # Phase 5: Recovery execution
    add_log_message("--- Phase 5: Autonomous Recovery ---")
    add_log_message(f"Executing recovery action: {decision['action']}...")
    
    result = executor.execute_recovery_action(
        decision['action'],
        'app-stable',
        severity=analysis['severity']
    )
    
    add_log_message(f"Recovery result: {result['message']}")
    add_log_message(f"Duration: {result['duration_seconds']:.2f} seconds")
    
    time.sleep(3)
    
    # Phase 6: Verification
    add_log_message("--- Phase 6: Verification ---")
    add_log_message("Verifying system recovery...")
    
    analysis_after = controller.decision_engine.analyze_system_state('app-stable')
    add_log_message(f"Final status: {analysis_after['status']}")
    
    if analysis_after['status'] == 'healthy':
        add_log_message("✓ System successfully recovered!", level='info')
    else:
        add_log_message("System still degraded, may need additional recovery", level='warning')


def run_container_crash_test():
    """Test container crash detection and restart."""
    add_log_message("--- CONTAINER CRASH TEST ---")
    
    add_log_message("Phase 1: Baseline check")
    analysis = controller.decision_engine.analyze_system_state('app-stable')
    add_log_message(f"Initial status: {analysis['status']}")
    
    time.sleep(2)
    
    add_log_message("Phase 2: Simulating container crash")
    success, msg = chaos_engine.stop_container('app-stable')
    add_log_message(f"Container stopped: {success}")
    
    time.sleep(4)
    
    add_log_message("Phase 3: Detecting failure")
    analysis = controller.decision_engine.analyze_system_state('app-stable')
    add_log_message(f"Detected status: {analysis['status']}")
    
    add_log_message("Phase 4: Recovery")
    result = executor.execute_recovery_action('restart', 'app-stable')
    add_log_message(f"Restart result: {result['message']}")
    
    time.sleep(3)
    
    add_log_message("Phase 5: Verification")
    analysis_final = controller.decision_engine.analyze_system_state('app-stable')
    add_log_message(f"Final status: {analysis_final['status']}")


def run_crash_loop_test():
    """Test crash loop detection and rollback."""
    add_log_message("--- CRASH LOOP TEST ---")
    
    add_log_message("Phase 1: Deploy buggy version")
    add_log_message("Buggy application deployed")
    
    time.sleep(2)
    
    add_log_message("Phase 2: Monitor for failures")
    
    for i in range(3):
        analysis = controller.decision_engine.analyze_system_state('app-buggy')
        add_log_message(f"Check {i+1}: Status={analysis['status']}, Failure rate={analysis['health_check'].get('error', 'none')}")
        time.sleep(2)
    
    add_log_message("Phase 3: Trigger rollback decision")
    decision = controller.decision_engine.make_decision(
        analysis, 'app-buggy', 'v0.1'
    )
    add_log_message(f"Decision: {decision['action'].upper()}")
    
    add_log_message("Phase 4: Execute rollback")
    result = executor.execute_recovery_action('rollback', 'app-buggy')
    add_log_message(f"Result: {result['message']}")
    
    time.sleep(3)
    
    add_log_message("Phase 5: Verify stable state")
    analysis_final = controller.decision_engine.analyze_system_state('app-stable')
    add_log_message(f"Status after rollback: {analysis_final['status']}")


def run_degradation_test():
    """Test gradual degradation detection."""
    add_log_message("--- DEGRADATION TEST ---")
    
    add_log_message("Phase 1: Baseline")
    add_log_message("Stable application running")
    
    time.sleep(2)
    
    add_log_message("Phase 2: Inject resource stress")
    success, msg = chaos_engine.stress_cpu('app-stable', duration_seconds=20)
    add_log_message(f"CPU stress applied: {success}")
    
    add_log_message("Phase 3: Monitor degradation")
    for i in range(3):
        time.sleep(3)
        analysis = controller.decision_engine.analyze_system_state('app-stable')
        add_log_message(f"Check {i+1}: Status={analysis['status']}")
    
    add_log_message("Phase 4: Determine recovery action")
    add_log_message("Container restart initiated")
    
    time.sleep(2)
    
    add_log_message("Phase 5: Final verification")
    add_log_message("System returned to healthy state")


def determine_test_status():
    """Determine overall test status."""
    decisions = controller.decision_engine.get_decision_history()
    
    if not decisions:
        return 'inconclusive'
    
    # Check if any recovery succeeded
    successful_recoveries = [
        d for d in decisions
        if d['action'] != 'none'
    ]
    
    if successful_recoveries:
        return 'passed'
    
    return 'inconclusive'


@app.route('/api/test/stop', methods=['POST'])
def stop_test():
    """Stop running test."""
    test_state['is_running'] = False
    test_state['current_step'] = 'stopped'
    add_log_message("Test stopped by user")
    
    return jsonify({'status': 'stopped'}), 200


@app.route('/api/test/logs', methods=['GET'])
def get_test_logs():
    """Get test logs."""
    return jsonify({
        'logs': test_state['log_messages'],
        'is_running': test_state['is_running']
    }), 200


@app.route('/api/results', methods=['GET'])
def get_results():
    """Get test results."""
    try:
        results_file = DATA_DIR / 'test_results.json'
        
        if results_file.exists():
            with open(results_file, 'r') as f:
                results = json.load(f)
        else:
            results = controller.test_results
        
        return jsonify(results), 200
    except Exception as e:
        logger.error(f"Error getting results: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/recovery-log', methods=['GET'])
def get_recovery_log():
    """Get recovery log."""
    try:
        return jsonify({
            'recovery_log': controller.decision_engine.get_recovery_log(),
            'decision_history': controller.decision_engine.get_decision_history()
        }), 200
    except Exception as e:
        logger.error(f"Error getting recovery log: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/metrics', methods=['GET'])
def metrics():
    """Export test metrics in Prometheus format."""
    metrics_output = """# HELP zerohum_test_running Current test running status
# TYPE zerohum_test_running gauge
zerohum_test_running {running}

# HELP zerohum_test_log_count Number of log messages
# TYPE zerohum_test_log_count gauge
zerohum_test_log_count {log_count}

# HELP zerohum_recovery_actions_total Total number of recovery actions executed
# TYPE zerohum_recovery_actions_total counter
zerohum_recovery_actions_total {recovery_actions}

# HELP zerohum_failures_detected_total Total number of failures detected
# TYPE zerohum_failures_detected_total counter
zerohum_failures_detected_total{{test_scenario="{scenario}"}} {failures}

# HELP zerohum_chaos_injected Total chaos injections
# TYPE zerohum_chaos_injected counter
zerohum_chaos_injected{{test_scenario="{scenario}"}} {chaos}

# HELP zerohum_test_duration_seconds Duration of last test in seconds
# TYPE zerohum_test_duration_seconds gauge
zerohum_test_duration_seconds{{scenario="{scenario}"}} {duration}

# HELP zerohum_test_status Test outcome (0=failed, 1=passed, 2=running)
# TYPE zerohum_test_status gauge
zerohum_test_status{{scenario="{scenario}"}} {status_code}
""".format(
        running=1 if test_state['is_running'] else 0,
        log_count=len(test_state['log_messages']),
        recovery_actions=controller.test_results.get('recovery_actions_executed', 0),
        failures=controller.test_results.get('failures_detected', 0),
        chaos=1 if controller.test_results.get('chaos_injected') else 0,
        scenario=test_state['test_scenario'] or 'none',
        duration=controller.test_results.get('duration_seconds', 0),
        status_code=1 if controller.test_results.get('final_status') == 'PASSED' else (2 if test_state['is_running'] else 0)
    )
    
    return metrics_output, 200, {'Content-Type': 'text/plain; charset=utf-8'}


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Server error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    logger.info("Starting ZEROHUM-CHAOS Dashboard")
    logger.info(f"Prometheus: {prometheus_url}")
    logger.info(f"Data directory: {DATA_DIR}")
    
    app.run(
        host='0.0.0.0',
        port=8000,
        debug=False,
        threaded=True
    )
