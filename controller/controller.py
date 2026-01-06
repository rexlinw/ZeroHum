#!/usr/bin/env python3
"""
Main Controller - ZEROHUM-CHAOS
Orchestrates the entire self-healing system.
Integrates chaos engine, decision engine, and recovery executor.
"""

import logging
import time
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from decision_engine import DecisionEngine

logger = logging.getLogger(__name__)


class SystemController:
    """
    Main controller that orchestrates the autonomous self-healing system.
    Runs the monitoring loop and executes recovery actions.
    """
    
    def __init__(self, 
                 prometheus_url: str = 'http://prometheus:9090',
                 polling_interval: int = 30,
                 data_dir: str = '/app/data'):
        """
        Initialize the System Controller.
        
        Args:
            prometheus_url: Prometheus endpoint
            polling_interval: How often to check metrics (seconds)
            data_dir: Directory for storing logs and data
        """
        self.prometheus_url = prometheus_url
        self.polling_interval = polling_interval
        self.data_dir = Path(data_dir)
        
        # Initialize components
        self.decision_engine = DecisionEngine(prometheus_url)
        
        # System state
        self.is_running = False
        self.current_version = 'stable'
        self.deployment_history = []
        self.test_results = {
            'status': 'pending',
            'start_time': None,
            'end_time': None,
            'chaos_injected': None,
            'failures_detected': 0,
            'recovery_actions': 0,
            'final_status': 'unknown'
        }
        
        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("System Controller initialized")
    
    def update_version(self, version: str):
        """
        Track version changes.
        
        Args:
            version: New version identifier
        """
        self.deployment_history.append({
            'timestamp': datetime.utcnow().isoformat(),
            'version': version,
            'action': 'deployed'
        })
        
        self.current_version = version
        logger.info(f"Version updated to: {version}")
    
    def monitor_single_check(self) -> Dict:
        """
        Perform a single monitoring check across all containers.
        
        Returns:
            Results of the monitoring check
        """
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'checks': [],
            'decisions': [],
            'actions_recommended': 0
        }
        
        # Check both containers
        for container in ['stable', 'buggy']:
            # Analyze state
            analysis = self.decision_engine.analyze_system_state(container)
            
            # Make decision
            decision = self.decision_engine.make_decision(
                analysis, 
                container,
                self.current_version
            )
            
            results['checks'].append(analysis)
            results['decisions'].append(decision)
            
            # Count recommended actions
            if decision['action'] != 'none':
                results['actions_recommended'] += 1
        
        return results
    
    def save_test_results(self):
        """Save test results to JSON file."""
        filepath = self.data_dir / 'test_results.json'
        
        try:
            with open(filepath, 'w') as f:
                json.dump(self.test_results, f, indent=2)
            
            logger.info(f"Test results saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save test results: {str(e)}")
    
    def save_recovery_log(self):
        """Save recovery log to CSV."""
        filepath = self.data_dir / 'recovery_log.csv'
        self.decision_engine.export_to_csv(str(filepath))
    
    def start_monitoring(self):
        """
        Start the autonomous monitoring and recovery loop.
        Runs in a background thread.
        """
        self.is_running = True
        thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        thread.start()
        logger.info("Monitoring started")
    
    def _monitoring_loop(self):
        """Internal monitoring loop that runs continuously."""
        logger.info("Starting monitoring loop")
        
        while self.is_running:
            try:
                # Perform monitoring check
                check_result = self.monitor_single_check()
                
                # Log results
                logger.debug(f"Monitoring check result: {json.dumps(check_result, indent=2)}")
                
                # Sleep before next check
                time.sleep(self.polling_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                time.sleep(self.polling_interval)
    
    def stop_monitoring(self):
        """Stop the monitoring loop."""
        self.is_running = False
        logger.info("Monitoring stopped")
    
    def get_system_status(self) -> Dict:
        """Get current system status."""
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'is_running': self.is_running,
            'current_version': self.current_version,
            'deployment_history': self.deployment_history,
            'test_results': self.test_results,
            'decision_history_count': len(self.decision_engine.get_decision_history()),
            'recovery_actions_count': len(self.decision_engine.get_recovery_log())
        }
    
    def reset_test(self):
        """Reset test state for a new test run."""
        self.test_results = {
            'status': 'pending',
            'start_time': None,
            'end_time': None,
            'chaos_injected': None,
            'failures_detected': 0,
            'recovery_actions': 0,
            'final_status': 'unknown'
        }
        
        self.decision_engine.reset()
        logger.info("Test state reset")
    
    def mark_test_started(self):
        """Mark the beginning of a test."""
        self.test_results['status'] = 'running'
        self.test_results['start_time'] = datetime.utcnow().isoformat()
        logger.info("Test started")
    
    def mark_test_completed(self, final_status: str):
        """Mark the end of a test."""
        self.test_results['status'] = 'completed'
        self.test_results['end_time'] = datetime.utcnow().isoformat()
        self.test_results['final_status'] = final_status
        
        # Calculate statistics
        self.test_results['failures_detected'] = len([
            d for d in self.decision_engine.get_decision_history()
            if d['action'] != 'none'
        ])
        self.test_results['recovery_actions'] = len(self.decision_engine.get_recovery_log())
        
        self.save_test_results()
        self.save_recovery_log()
        
        logger.info(f"Test completed with status: {final_status}")


def main():
    """Test the System Controller."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    controller = SystemController()
    
    print("\n=== System Controller Test ===")
    print(f"Status: {json.dumps(controller.get_system_status(), indent=2)}")


if __name__ == '__main__':
    main()
