#!/usr/bin/env python3
"""
Decision Engine - ZEROHUM-CHAOS
Analyzes system metrics from Prometheus and makes autonomous decisions
for recovery actions without human intervention.
"""

import requests
import logging
import time
import subprocess
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import csv
from pathlib import Path

logger = logging.getLogger(__name__)


class DecisionEngine:
    """
    Autonomous decision maker that analyzes metrics and determines recovery actions.
    Implements self-healing logic based on system state.
    """
    
    def __init__(self, prometheus_url: str = 'http://prometheus:9090'):
        """
        Initialize the Decision Engine.
        
        Args:
            prometheus_url: URL of Prometheus instance
        """
        self.prometheus_url = prometheus_url
        self.decision_history = []
        self.recovery_log = []
        
        # Thresholds for decision making
        self.thresholds = {
            'health_check_failure_rate': 0.1,  # 10% failure rate triggers degraded
            'error_rate_threshold': 0.25,      # 25% error rate
            'response_time_threshold': 5000,   # 5 seconds in ms
            'consecutive_failures': 3,         # 3 consecutive failures trigger restart (increased tolerance)
            'rollback_threshold': 5,           # 5 consecutive health check failures (increased tolerance)
        }
        
        # Decision rules
        self.max_retries = 3
        self.rollback_enabled = True
        self.failure_count = {'app-stable': 0, 'app-buggy': 0}
        self.last_healthy_check = {'app-stable': datetime.utcnow(), 'app-buggy': datetime.utcnow()}
        
        logger.info("Decision Engine initialized")
    
    def check_container_status(self, container_name: str) -> Dict:
        """
        Check actual Docker container status.
        
        Args:
            container_name: Name of the container
            
        Returns:
            Container status dict
        """
        try:
            cmd = ['docker', 'inspect', container_name, '--format={{.State.Running}}']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            status = {
                'container': container_name,
                'timestamp': datetime.utcnow().isoformat(),
                'running': result.stdout.strip() == 'true',
                'checked': True
            }
            
            if result.returncode != 0:
                status['running'] = False
                logger.warning(f"Container {container_name} is DOWN")
            
            return status
        except Exception as e:
            logger.error(f"Failed to check container status: {str(e)}")
            return {
                'container': container_name,
                'timestamp': datetime.utcnow().isoformat(),
                'running': False,
                'checked': False
            }
    
    def check_health_endpoint(self, container_name: str, port: int = 5000) -> Dict:
        """
        Directly check the health endpoint of an application.
        
        Args:
            container_name: Name of the container
            port: Port to check on localhost
            
        Returns:
            Health check result dict
        """
        # Port mapping
        ports = {'app-stable': 5001, 'app-buggy': 5002}
        port = ports.get(container_name, port)
        
        health_data = {
            'container': container_name,
            'timestamp': datetime.utcnow().isoformat(),
            'is_healthy': False,
            'http_status': 0,
            'error': None
        }
        
        try:
            url = f'http://{container_name}:{port}/health'
            response = requests.get(url, timeout=5)  # Increased timeout to 5 seconds
            
            health_data['http_status'] = response.status_code
            
            if response.status_code == 200:
                health_data['is_healthy'] = True
                try:
                    data = response.json()
                    health_data['status'] = data.get('status', 'unknown')
                except:
                    health_data['status'] = 'ok'
                # Update last healthy check time
                self.last_healthy_check[container_name] = datetime.utcnow()
                logger.info(f"Health check OK for {container_name}")
            else:
                health_data['is_healthy'] = False
                health_data['error'] = f"HTTP {response.status_code}"
                logger.warning(f"Health check for {container_name} returned {response.status_code}")
        
        except requests.ConnectionError as e:
            health_data['is_healthy'] = False
            health_data['error'] = 'Connection refused'
            logger.warning(f"Cannot connect to {container_name}: connection issue")
        except requests.Timeout:
            health_data['is_healthy'] = False
            health_data['error'] = 'Timeout (>5s)'
            logger.warning(f"Health check timeout for {container_name} (slow response)")
        except Exception as e:
            health_data['is_healthy'] = False
            health_data['error'] = str(e)
            logger.warning(f"Health check had issue for {container_name}: {str(e)}")
        
        return health_data
    
    def query_prometheus(self, query: str, timeout: int = 10) -> Dict:
        """
        Query Prometheus for metrics.
        
        Args:
            query: PromQL query string
            timeout: Request timeout in seconds
            
        Returns:
            Query result dict
        """
        try:
            url = f"{self.prometheus_url}/api/v1/query"
            params = {'query': query}
            
            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            
            result = response.json()
            
            if result['status'] == 'success':
                return result['data']
            else:
                logger.error(f"Prometheus error: {result.get('error', 'Unknown error')}")
                return {'resultType': 'vector', 'result': []}
                
        except requests.RequestException as e:
            logger.error(f"Failed to query Prometheus: {str(e)}")
            return {'resultType': 'vector', 'result': []}
    
    def get_container_health(self, container_name: str) -> Dict:
        """
        Get health status of a container.
        
        Args:
            container_name: Name of the container
            
        Returns:
            Health status dict
        """
        # Query for successful health checks in the last 2 minutes
        query = f"""
        increase(http_requests_total{{job="app-{container_name}",status="200",path="/health"}}[2m])
        """
        
        success_result = self.query_prometheus(query)
        
        # Query for failed health checks
        failed_query = f"""
        increase(http_requests_total{{job="app-{container_name}",status!="200",path="/health"}}[2m])
        """
        
        failed_result = self.query_prometheus(failed_query)
        
        health_status = {
            'container': container_name,
            'timestamp': datetime.utcnow().isoformat(),
            'successful_checks': 0,
            'failed_checks': 0,
            'failure_rate': 0.0,
            'is_healthy': True
        }
        
        if success_result['result']:
            health_status['successful_checks'] = float(success_result['result'][0]['value'][1])
        
        if failed_result['result']:
            health_status['failed_checks'] = float(failed_result['result'][0]['value'][1])
        
        total = health_status['successful_checks'] + health_status['failed_checks']
        if total > 0:
            health_status['failure_rate'] = health_status['failed_checks'] / total
            health_status['is_healthy'] = health_status['failure_rate'] < self.thresholds['health_check_failure_rate']
        
        return health_status
    
    def get_container_uptime(self, container_name: str) -> float:
        """
        Get container uptime in seconds.
        
        Args:
            container_name: Name of the container
            
        Returns:
            Uptime in seconds
        """
        query = f"""
        time() - container_start_time{{container_name="{container_name}"}}
        """
        
        result = self.query_prometheus(query)
        
        if result['result']:
            return float(result['result'][0]['value'][1])
        
        return -1
    
    def analyze_system_state(self, container_name: str) -> Dict:
        """
        Comprehensive analysis of system state using DIRECT checks.
        
        Args:
            container_name: Name of the container to analyze
            
        Returns:
            Analysis result dict
        """
        # Check container status
        container_status = self.check_container_status(container_name)
        
        # Check health endpoint
        health_check = self.check_health_endpoint(container_name)
        
        # Determine analysis
        analysis = {
            'timestamp': datetime.utcnow().isoformat(),
            'container': container_name,
            'container_status': container_status,
            'health_check': health_check,
            'status': 'unknown',
            'severity': 'none',
            'recommendation': 'continue',
            'confidence': 0.0
        }
        
        # Container is DOWN - CRITICAL!
        if not container_status['running']:
            analysis['status'] = 'critical'
            analysis['severity'] = 'critical'
            analysis['recommendation'] = 'restart'
            analysis['confidence'] = 0.99
            self.failure_count[container_name] += 1
            logger.error(f"CRITICAL: {container_name} container is DOWN!")
            return analysis
        
        # Container is UP but health check failing
        if container_status['running'] and not health_check['is_healthy']:
            self.failure_count[container_name] += 1
            
            if self.failure_count[container_name] >= self.thresholds['rollback_threshold']:
                analysis['status'] = 'critical'
                analysis['severity'] = 'critical'
                analysis['recommendation'] = 'rollback'
                analysis['confidence'] = 0.95
                logger.error(f"CRITICAL: {container_name} persistent health failures ({self.failure_count[container_name]}x)")
            elif self.failure_count[container_name] >= self.thresholds['consecutive_failures']:
                analysis['status'] = 'degraded'
                analysis['severity'] = 'high'
                analysis['recommendation'] = 'restart'
                analysis['confidence'] = 0.85
                logger.warning(f"DEGRADED: {container_name} multiple failures ({self.failure_count[container_name]}x)")
            else:
                # Single failure - just warn, don't mark as degraded yet
                analysis['status'] = 'healthy'  # Give benefit of doubt on first failure
                analysis['severity'] = 'low'
                analysis['recommendation'] = 'monitor'
                analysis['confidence'] = 0.7
                logger.info(f"Transient check issue for {container_name} (will retry)")
        
        # Container UP and health check passing
        elif container_status['running'] and health_check['is_healthy']:
            analysis['status'] = 'healthy'
            analysis['severity'] = 'none'
            analysis['recommendation'] = 'continue'
            analysis['confidence'] = 1.0
            self.failure_count[container_name] = 0  # Reset failure count
            logger.info(f"HEALTHY: {container_name} is running normally")
        
        return analysis
    
    def make_decision(self, analysis: Dict, container_name: str, 
                     current_version: str) -> Dict:
        """
        Make autonomous recovery decision based on analysis.
        
        Args:
            analysis: System analysis result
            container_name: Name of the container
            current_version: Currently deployed version
            
        Returns:
            Decision dict with action recommendation
        """
        decision = {
            'timestamp': datetime.utcnow().isoformat(),
            'container': container_name,
            'current_version': current_version,
            'analysis': analysis,
            'action': 'none',
            'reasoning': '',
            'execution_priority': 0
        }
        
        # Decision logic based on severity
        if analysis['status'] == 'healthy':
            decision['action'] = 'none'
            decision['reasoning'] = f"{container_name} is healthy. Continuing normal operation."
            decision['execution_priority'] = 0
        
        elif analysis['status'] == 'degraded':
            decision['action'] = 'restart'
            decision['reasoning'] = f"{container_name} degraded ({analysis['severity']}). RESTARTING container..."
            decision['execution_priority'] = 2
            logger.warning(f"Decision: RESTART {container_name}")
        
        elif analysis['status'] == 'critical':
            if 'buggy' in container_name or current_version != 'stable':
                decision['action'] = 'rollback'
                decision['reasoning'] = f"{container_name} CRITICAL! Rolling back to stable version..."
                decision['execution_priority'] = 3
                logger.error(f"Decision: ROLLBACK {container_name}")
            else:
                decision['action'] = 'restart'
                decision['reasoning'] = f"{container_name} CRITICAL! Restarting container..."
                decision['execution_priority'] = 2
                logger.error(f"Decision: RESTART {container_name}")
        
        # Log decision
        self.decision_history.append(decision)
        
        return decision
    
    def should_execute_action(self, decision: Dict) -> bool:
        """
        Determine if the recommended action should be executed.
        
        Args:
            decision: Decision dict
            
        Returns:
            True if action should be executed
        """
        if decision['action'] == 'none':
            return False
        
        # Check if this action was recently attempted
        recent_actions = [
            d for d in self.decision_history[-5:]
            if d['container'] == decision['container'] and d['action'] == decision['action']
        ]
        
        if len(recent_actions) >= self.max_retries:
            logger.warning(f"Max retries reached for action: {decision['action']}")
            return False
        
        return True
    
    def log_recovery_action(self, action: str, container: str, 
                           success: bool, duration_seconds: float):
        """
        Log a recovery action for reporting.
        
        Args:
            action: Type of action executed
            container: Container it was executed on
            success: Whether the action succeeded
            duration_seconds: How long the action took
        """
        record = {
            'timestamp': datetime.utcnow().isoformat(),
            'action': action,
            'container': container,
            'success': success,
            'duration_seconds': duration_seconds
        }
        
        self.recovery_log.append(record)
        logger.info(f"Recovery action logged: {action} on {container} - Success: {success}")
    
    def get_decision_history(self) -> List[Dict]:
        """Get all decisions made."""
        return self.decision_history.copy()
    
    def get_recovery_log(self) -> List[Dict]:
        """Get recovery action log."""
        return self.recovery_log.copy()
    
    def export_to_csv(self, filepath: str):
        """
        Export recovery log to CSV.
        
        Args:
            filepath: Path to write CSV file
        """
        try:
            with open(filepath, 'w', newline='') as csvfile:
                fieldnames = ['timestamp', 'action', 'container', 'success', 'duration_seconds']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                writer.writerows(self.recovery_log)
            
            logger.info(f"Recovery log exported to {filepath}")
        except Exception as e:
            logger.error(f"Failed to export CSV: {str(e)}")
    
    def reset(self):
        """Reset engine state."""
        self.decision_history.clear()
        self.recovery_log.clear()
        logger.info("Decision Engine reset")


def main():
    """Test the Decision Engine."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    engine = DecisionEngine()
    
    # Test analysis
    print("\n=== Testing Decision Engine ===")
    analysis = engine.analyze_system_state('stable')
    print(f"Analysis: {json.dumps(analysis, indent=2)}")
    
    # Test decision
    decision = engine.make_decision(analysis, 'stable', 'v1.0')
    print(f"Decision: {json.dumps(decision, indent=2)}")


if __name__ == '__main__':
    main()
