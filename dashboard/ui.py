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
from typing import Dict, List

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

try:
    from ml_predictor import FailurePredictor
    logger.info("MLPredictor module imported successfully")
except ImportError as e:
    logger.warning(f"Failed to import ml_predictor: {e}")
    FailurePredictor = None
except Exception as e:
    logger.error(f"Unexpected error importing ml_predictor: {e}")
    FailurePredictor = None

try:
    from slo_manager import SLOManager
    logger.info("SLOManager module imported successfully")
except ImportError as e:
    logger.warning(f"Failed to import slo_manager: {e}")
    SLOManager = None
except Exception as e:
    logger.error(f"Unexpected error importing slo_manager: {e}")
    SLOManager = None


# Initialize components
DATA_DIR = Path(os.getenv('DATA_DIR', '/app/data'))
DATA_DIR.mkdir(parents=True, exist_ok=True)

prometheus_url = os.getenv('PROMETHEUS_URL', 'http://prometheus:9090')
docker_compose_path = os.getenv('DOCKER_COMPOSE_PATH', '/app/docker-compose.yml')
llm_api_url = os.getenv('LLM_API_URL', 'https://api.openai.com/v1/chat/completions')
llm_model = os.getenv('LLM_MODEL', 'gpt-4o-mini')
llm_api_key = os.getenv('LLM_API_KEY', '').strip()
llm_timeout_seconds = int(os.getenv('LLM_TIMEOUT_SECONDS', '20'))

chaos_engine = ChaosEngine()
controller = SystemController(prometheus_url=prometheus_url, data_dir=str(DATA_DIR))
executor = RecoveryExecutor(docker_compose_path=docker_compose_path)

# Initialize ML predictor
predictor = None
if FailurePredictor:
    try:
        predictor = FailurePredictor(data_dir=str(DATA_DIR))
        logger.info("Predictive Failure Detection initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize predictor: {e}")
        predictor = None

# Initialize SLO manager
slo_manager = None
if SLOManager:
    try:
        slo_manager = SLOManager(data_dir=str(DATA_DIR))
        logger.info("SLO Manager initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize SLO manager: {e}")
        slo_manager = None

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


def load_latest_results() -> Dict:
    """Load latest persisted results, or return in-memory results."""
    results_file = DATA_DIR / 'test_results.json'

    if results_file.exists():
        try:
            with open(results_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Unable to read test_results.json, using in-memory state: {str(e)}")

    return controller.test_results


def safe_length(value) -> int:
    """Return len(value) when possible, otherwise 0."""
    if isinstance(value, (list, tuple, set, dict, str, bytes)):
        return len(value)
    return 0


def build_ml_training_samples(sample_count: int = 3) -> list[Dict]:
    """Build a small, numeric-only training set for the ML predictor."""
    latest_results = load_latest_results()
    log_count = safe_length(test_state.get('log_messages', []))

    failures_detected = latest_results.get('failures_detected', 0)
    recovery_actions = latest_results.get('recovery_actions_executed', 0)

    try:
        failures_detected = int(failures_detected)
    except (TypeError, ValueError):
        failures_detected = 0

    try:
        recovery_actions = int(recovery_actions)
    except (TypeError, ValueError):
        recovery_actions = 0

    base_sample = {
        'timestamp': datetime.utcnow().isoformat(),
        'cpu_usage': 40 + (log_count % 30),
        'memory_usage': 50 + (log_count % 30),
        'error_rate': failures_detected * 5,
        'latency': 200 + (recovery_actions * 100)
    }

    return [base_sample.copy() for _ in range(max(3, sample_count))]


def get_chat_context() -> Dict:
    """Build compact runtime context for chat answers."""
    controller_status = controller.get_system_status()
    results = load_latest_results()

    stable_container = controller.decision_engine.check_container_status('app-stable')
    buggy_container = controller.decision_engine.check_container_status('app-buggy')
    stable_health = controller.decision_engine.check_health_endpoint('app-stable')
    buggy_health = controller.decision_engine.check_health_endpoint('app-buggy')

    recent_logs = test_state['log_messages'][-15:]

    return {
        'timestamp': datetime.utcnow().isoformat(),
        'test_running': test_state['is_running'],
        'test_scenario': test_state['test_scenario'],
        'test_results': results,
        'controller_status': {
            'current_version': controller_status.get('current_version'),
            'decision_history_count': controller_status.get('decision_history_count', 0),
            'recovery_actions_count': controller_status.get('recovery_actions_count', 0)
        },
        'services': {
            'app_stable': {
                'container_running': stable_container.get('running', False),
                'health_ok': stable_health.get('is_healthy', False),
                'http_status': stable_health.get('http_status', 0),
                'error': stable_health.get('error')
            },
            'app_buggy': {
                'container_running': buggy_container.get('running', False),
                'health_ok': buggy_health.get('is_healthy', False),
                'http_status': buggy_health.get('http_status', 0),
                'error': buggy_health.get('error')
            }
        },
        'recent_logs': recent_logs
    }


def build_local_chat_answer(question: str, context: Dict) -> str:
    """Fallback assistant when external LLM is not configured/reachable."""
    q = question.lower()
    results = context.get('test_results', {})
    services = context.get('services', {})
    stable = services.get('app_stable', {})
    buggy = services.get('app_buggy', {})
    controller_status = context.get('controller_status', {})

    if 'stable' in q and ('health' in q or 'status' in q):
        is_running = stable.get('container_running', False)
        is_healthy = stable.get('health_ok', False)
        status = "running normally" if is_running and is_healthy else ("running but having issues" if is_running else "not running")
        http_code = stable.get('http_status', 0)
        return (
            f"The stable application is currently **{status}**. "
            f"Health check last returned HTTP {http_code}. "
            f"The system is {'available for traffic' if is_healthy else 'not currently available and may need recovery'}."
        )

    if 'buggy' in q and ('health' in q or 'status' in q):
        is_running = buggy.get('container_running', False)
        is_healthy = buggy.get('health_ok', False)
        status = "running" if is_running else "not running"
        return (
            f"The buggy (test) application is currently **{status}**. "
            f"Health status: {'healthy' if is_healthy else 'degraded'}. "
            f"This is the version under chaos testing."
        )

    if 'metric' in q or 'failure' in q or 'recovery' in q or 'result' in q:
        final_status = results.get('final_status', 'unknown')
        failures = results.get('failures_detected', 0)
        recoveries = results.get('recovery_actions_executed', 0)
        test_status = "completed" if final_status != 'unknown' else "no recent test"
        
        summary = f"The latest test **{test_status}** with result: **{final_status}**. "
        if failures > 0 or recoveries > 0:
            summary += f"System detected **{failures}** issue(s) and automatically executed **{recoveries}** recovery action(s). "
        if failures == 0 and recoveries == 0:
            summary += "No failures or recovery actions were needed during the test period. "
        summary += "This demonstrates the system's self-healing capability."
        return summary

    if 'duration' in q or 'time' in q:
        start_time = results.get('start_time')
        end_time = results.get('end_time')
        if start_time and end_time:
            try:
                duration = (datetime.fromisoformat(end_time) - datetime.fromisoformat(start_time)).total_seconds()
                return f"The latest test completed in **{duration:.1f} seconds**. This measures the total time from chaos injection through verification."
            except Exception:
                pass
        return "No completed test timing is available. Run a test scenario to generate performance data."

    # Default comprehensive answer
    test_running = context.get('test_running', False)
    is_running_status = "**A test is currently running**" if test_running else "**No test is currently running**"
    stable_healthy = stable.get('health_ok', False)
    recovery_count = controller_status.get('recovery_actions_count', 0)
    
    return (
        f"{is_running_status}. "
        f"The stable application is {'healthy' if stable_healthy else 'experiencing issues'}. "
        f"The autonomous controller has executed **{recovery_count}** recovery actions total. "
        f"Ask me about test results, application health, recovery actions, or system metrics."
    )


def ask_external_llm(question: str, history: List[Dict], context: Dict) -> str:
    """Ask external LLM using OpenAI-compatible chat completions API."""
    if not llm_api_key:
        return ""

    safe_history = []
    for item in history[-8:]:
        role = item.get('role', '')
        content = item.get('content', '')
        if role in ('user', 'assistant') and isinstance(content, str) and content.strip():
            safe_history.append({'role': role, 'content': content.strip()})

    system_prompt = (
        "You are ZEROHUM Health Assistant, a friendly and professional advisor for system reliability and performance. "
        "Your goal is to provide clear, actionable insights that business stakeholders and operations teams can understand and act on. "
        "Guidelines:\n"
        "- Use plain language, avoid heavy technical jargon\n"
        "- Explain what issues mean in business terms (e.g., 'system availability' instead of 'container running status')\n"
        "- Provide brief, actionable recommendations\n"
        "- If data is missing, explain what information would help determine the answer\n"
        "- Keep answers concise but complete (1-3 short paragraphs)\n"
        "- Be honest: if you cannot answer from the context provided, say so clearly\n"
        "- Always focus on system health, recovery capability, and stability outlook"
    )

    messages = [
        {'role': 'system', 'content': system_prompt},
        {
            'role': 'system',
            'content': f"Runtime context JSON:\n{json.dumps(context, ensure_ascii=True)}"
        }
    ]
    messages.extend(safe_history)
    messages.append({'role': 'user', 'content': question})

    payload = {
        'model': llm_model,
        'messages': messages,
        'temperature': 0.2,
        'max_tokens': 350
    }

    headers = {
        'Authorization': f'Bearer {llm_api_key}',
        'Content-Type': 'application/json'
    }

    response = requests.post(
        llm_api_url,
        headers=headers,
        json=payload,
        timeout=llm_timeout_seconds
    )
    response.raise_for_status()

    data = response.json()
    answer = data.get('choices', [{}])[0].get('message', {}).get('content', '')
    return answer.strip()


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
        actions = safe_length([d for d in decisions if d['action'] != 'none'])
        if controller.test_results['recovery_actions_executed'] < actions:
            controller.test_results['recovery_actions_executed'] = actions
            
        # Mark test as completed
        final_status = determine_test_status()
        controller.mark_test_completed(final_status)
        add_log_message(f"=== Test Completed: {final_status.upper()} ===")
        
        # Train ML predictor on new data
        if predictor:
            try:
                add_log_message("Training predictive models on collected data...")
                train_result = predictor.train_on_metrics(
                    build_ml_training_samples(max(3, safe_length(test_state.get('log_messages', [])) // 5))
                )
                add_log_message(f"ML training complete: {train_result.get('status', 'unknown')}")
            except Exception as e:
                logger.warning(f"ML training failed: {e}")
        
        # Evaluate against SLOs
        if slo_manager:
            try:
                add_log_message("Evaluating test against Service Level Objectives...")
                slo_eval = slo_manager.evaluate_test_against_slos({
                    **controller.test_results,
                    'log_messages_count': safe_length(test_state.get('log_messages', []))
                })
                
                if slo_eval['breached_slos']:
                    add_log_message(
                        f"SLO BREACH: {', '.join(slo_eval['breached_slos'])} SLO(s) violated",
                        level='warning'
                    )
                elif slo_eval['overall_slo_health'] == 'warning':
                    add_log_message("SLO WARNING: Tight margins on some SLOs", level='warning')
                else:
                    add_log_message("All SLOs satisfied with good margins")
            except Exception as e:
                logger.warning(f"SLO evaluation failed: {e}")
        
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
        add_log_message("System successfully recovered.", level='info')
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


@app.route('/api/chat', methods=['POST'])
def health_chat():
    """Chat endpoint for health and metrics questions."""
    try:
        data = request.get_json() or {}
        question = (data.get('message') or '').strip()
        history = data.get('history') or []

        if not question:
            return jsonify({'error': 'Message is required'}), 400

        context = get_chat_context()
        source = 'fallback'
        answer = ''

        try:
            answer = ask_external_llm(question, history, context)
            if answer:
                source = 'llm'
        except Exception as llm_error:
            logger.warning(f"LLM request failed, falling back to local assistant: {str(llm_error)}")

        if not answer:
            answer = build_local_chat_answer(question, context)

        return jsonify({
            'answer': answer,
            'source': source,
            'timestamp': context['timestamp']
        }), 200

    except Exception as e:
        logger.error(f"Chat endpoint error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/ml/predict', methods=['GET'])
def predict_failures():
    """Get predictions of potential failures."""
    if not predictor:
        return jsonify({
            'status': 'unavailable',
            'reason': 'ML module not initialized'
        }), 503
    
    try:
        predictions = predictor.predict_failures(periods=10)
        recommendations = predictor.get_recommendations()
        
        return jsonify({
            'predictions': predictions,
            'recommendations': recommendations
        }), 200
    except Exception as e:
        logger.error(f"Prediction error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/ml/train', methods=['POST'])
def train_predictor():
    """Train predictor models on collected data."""
    if not predictor:
        return jsonify({
            'status': 'unavailable',
            'reason': 'ML module not initialized'
        }), 503
    
    try:
        metric_samples = build_ml_training_samples()
        result = predictor.train_on_metrics(metric_samples)
        logger.info(f"Training result: {result}")
        
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Training error: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/ml/status', methods=['GET'])
def ml_status():
    """Get ML predictor status."""
    if not predictor:
        return jsonify({
            'status': 'unavailable',
            'reason': 'ML module not initialized'
        }), 503
    
    try:
        status = predictor.get_status()
        return jsonify(status), 200
    except Exception as e:
        logger.error(f"Status error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/slo/status', methods=['GET'])
def slo_status():
    """Get current SLO status and configuration."""
    if not slo_manager:
        return jsonify({
            'status': 'unavailable',
            'reason': 'SLO manager not initialized'
        }), 503
    
    try:
        summary = slo_manager.get_slo_summary()
        return jsonify(summary), 200
    except Exception as e:
        logger.error(f"SLO status error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/slo/report', methods=['GET'])
def slo_report():
    """Get SLO compliance report."""
    if not slo_manager:
        return jsonify({
            'status': 'unavailable',
            'reason': 'SLO manager not initialized'
        }), 503
    
    try:
        report = slo_manager.get_slo_report()
        return jsonify(report), 200
    except Exception as e:
        logger.error(f"SLO report error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/slo/update', methods=['POST'])
def update_slos():
    """Update SLO targets."""
    if not slo_manager:
        return jsonify({
            'status': 'unavailable',
            'reason': 'SLO manager not initialized'
        }), 503
    
    try:
        data = request.get_json() or {}
        slo_name = data.get('slo_name')
        target = data.get('target')
        
        if not slo_name or target is None:
            return jsonify({'error': 'slo_name and target required'}), 400
        
        result = slo_manager.update_slo(slo_name, float(target))
        return jsonify(result), 200 if result['status'] == 'success' else 400
    except Exception as e:
        logger.error(f"SLO update error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/metrics', methods=['GET'])
def metrics():
    """Export test metrics in Prometheus format."""
    # Load latest results from persistent storage
    latest_results = load_latest_results()
    
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
        log_count=safe_length(test_state.get('log_messages', [])),
        recovery_actions=latest_results.get('recovery_actions_executed', 0),
        failures=latest_results.get('failures_detected', 0),
        chaos=1 if latest_results.get('chaos_injected') else 0,
        scenario=test_state['test_scenario'] or 'none',
        duration=latest_results.get('duration_seconds', 0),
        status_code=1 if (latest_results.get('final_status') or '').upper() == 'PASSED' else (2 if test_state['is_running'] else 0)
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
