#!/usr/bin/env python3
"""
Recovery Executor - ZEROHUM-CHAOS
Executes autonomous recovery actions without human intervention.
Handles restart, rollback, and remediation logic.
"""

import subprocess
import logging
import time
import json
from datetime import datetime
from typing import Tuple, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class RecoveryExecutor:
    """
    Executes recovery actions autonomously.
    Supports container restart, version rollback, and service isolation.
    """
    
    def __init__(self, docker_compose_path: str = '/app/docker-compose.yml'):
        """
        Initialize the Recovery Executor.
        
        Args:
            docker_compose_path: Path to docker-compose.yml
        """
        self.docker_compose_path = docker_compose_path
        self.execution_log = []
        self.rollback_history = []
        
        logger.info("Recovery Executor initialized")
    
    def run_command(self, command: list, timeout: int = 30) -> Tuple[bool, str]:
        """
        Execute a system command.
        
        Args:
            command: Command as list of strings
            timeout: Timeout in seconds
            
        Returns:
            Tuple of (success: bool, output: str)
        """
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                error = result.stderr.strip() or result.stdout.strip()
                logger.error(f"Command failed: {error}")
                return False, error
        
        except subprocess.TimeoutExpired:
            logger.error(f"Command timeout: {' '.join(command)}")
            return False, "Command timeout"
        except Exception as e:
            logger.error(f"Command error: {str(e)}")
            return False, str(e)
    
    def restart_container(self, service_name: str) -> Tuple[bool, float]:
        """
        Restart a Docker service/container.
        
        Args:
            service_name: Name of the service to restart
            
        Returns:
            Tuple of (success: bool, duration_seconds: float)
        """
        logger.info(f"Attempting to restart container: {service_name}")
        
        start_time = time.time()
        
        # Use docker restart
        success, output = self.run_command(['docker', 'restart', service_name])
        
        duration = time.time() - start_time
        
        if success:
            logger.info(f"Successfully restarted {service_name} in {duration:.2f}s")
            self._log_action('restart_container', service_name, True, duration)
            return True, duration
        else:
            logger.error(f"Failed to restart {service_name}: {output}")
            self._log_action('restart_container', service_name, False, duration)
            return False, duration
    
    def rollback_to_stable(self, service_name: str) -> Tuple[bool, float]:
        """
        Rollback service to last known stable version.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Tuple of (success: bool, duration_seconds: float)
        """
        logger.warning(f"Initiating rollback for: {service_name}")
        
        start_time = time.time()
        
        # Stop the current instance
        logger.info(f"Stopping {service_name}...")
        stop_success, _ = self.run_command(['docker', 'stop', service_name])
        
        if not stop_success:
            duration = time.time() - start_time
            logger.error("Failed to stop service before rollback")
            self._log_action('rollback_to_stable', service_name, False, duration)
            return False, duration
        
        time.sleep(2)
        
        # Start the stable version
        logger.info(f"Starting stable version of {service_name}...")
        
        # Compose command to bring up the service
        success, output = self.run_command(
            ['docker', 'compose', '-f', self.docker_compose_path, 
             'up', '-d', f'{service_name}-stable']
        )
        
        duration = time.time() - start_time
        
        if success:
            logger.warning(f"Rollback completed in {duration:.2f}s")
            self.rollback_history.append({
                'timestamp': datetime.utcnow().isoformat(),
                'service': service_name,
                'target': 'stable',
                'success': True,
                'duration_seconds': duration
            })
            self._log_action('rollback_to_stable', service_name, True, duration)
            return True, duration
        else:
            logger.error(f"Rollback failed: {output}")
            self._log_action('rollback_to_stable', service_name, False, duration)
            return False, duration
    
    def scale_service(self, service_name: str, replicas: int) -> Tuple[bool, float]:
        """
        Scale the number of service replicas (if using swarm/compose).
        
        Args:
            service_name: Name of the service
            replicas: Number of replicas to run
            
        Returns:
            Tuple of (success: bool, duration_seconds: float)
        """
        logger.info(f"Scaling {service_name} to {replicas} replicas")
        
        start_time = time.time()
        
        # Docker compose up with scale
        success, output = self.run_command(
            ['docker', 'compose', '-f', self.docker_compose_path, 
             'up', '-d', '--scale', f'{service_name}={replicas}']
        )
        
        duration = time.time() - start_time
        
        if success:
            logger.info(f"Successfully scaled {service_name}")
            self._log_action('scale_service', service_name, True, duration)
            return True, duration
        else:
            logger.error(f"Failed to scale {service_name}: {output}")
            self._log_action('scale_service', service_name, False, duration)
            return False, duration
    
    def isolate_service(self, service_name: str) -> Tuple[bool, float]:
        """
        Isolate a service by stopping it.
        
        Args:
            service_name: Name of the service to isolate
            
        Returns:
            Tuple of (success: bool, duration_seconds: float)
        """
        logger.warning(f"Isolating service: {service_name}")
        
        start_time = time.time()
        success, output = self.run_command(['docker', 'stop', service_name])
        duration = time.time() - start_time
        
        if success:
            logger.warning(f"Service {service_name} isolated in {duration:.2f}s")
            self._log_action('isolate_service', service_name, True, duration)
            return True, duration
        else:
            logger.error(f"Failed to isolate {service_name}: {output}")
            self._log_action('isolate_service', service_name, False, duration)
            return False, duration
    
    def execute_recovery_action(self, action: str, service_name: str,
                               severity: str = 'normal') -> Dict:
        """
        Execute the appropriate recovery action based on severity and action type.
        
        Args:
            action: Type of action (restart, rollback, isolate)
            service_name: Name of the service
            severity: Severity level (low, normal, high, critical)
            
        Returns:
            Result dict with execution details
        """
        result = {
            'timestamp': datetime.utcnow().isoformat(),
            'action': action,
            'service': service_name,
            'severity': severity,
            'success': False,
            'duration_seconds': 0,
            'message': ''
        }
        
        logger.info(f"Executing recovery action: {action} on {service_name} (severity: {severity})")
        
        try:
            if action == 'restart':
                success, duration = self.restart_container(service_name)
                result['success'] = success
                result['duration_seconds'] = duration
                result['message'] = 'Container restart' + (' successful' if success else ' failed')
            
            elif action == 'rollback':
                success, duration = self.rollback_to_stable(service_name)
                result['success'] = success
                result['duration_seconds'] = duration
                result['message'] = 'Rollback to stable' + (' successful' if success else ' failed')
            
            elif action == 'scale':
                # Scale up replicas for load distribution
                success, duration = self.scale_service(service_name, 2)
                result['success'] = success
                result['duration_seconds'] = duration
                result['message'] = 'Service scaling' + (' successful' if success else ' failed')
            
            elif action == 'isolate':
                # Stop the problematic service to prevent cascade failure
                success, duration = self.run_command(['docker', 'stop', service_name])
                result['success'] = success
                result['duration_seconds'] = duration
                result['message'] = 'Service isolation' + (' successful' if success else ' failed')
            
            else:
                result['message'] = f"Unknown action: {action}"
                logger.warning(result['message'])
        
        except Exception as e:
            result['message'] = f"Action execution error: {str(e)}"
            logger.error(result['message'])
        
        return result
    
    def _log_action(self, action_type: str, target: str, success: bool, 
                   duration: float):
        """
        Log an executed action.
        
        Args:
            action_type: Type of action
            target: Target of action
            success: Whether it succeeded
            duration: How long it took
        """
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'action': action_type,
            'target': target,
            'success': success,
            'duration_seconds': duration
        }
        
        self.execution_log.append(log_entry)
    
    def get_execution_log(self):
        """Get the execution log."""
        return self.execution_log.copy()
    
    def get_rollback_history(self):
        """Get the rollback history."""
        return self.rollback_history.copy()
    
    def export_log(self, filepath: str):
        """
        Export execution log to JSON.
        
        Args:
            filepath: Path to write the log file
        """
        try:
            with open(filepath, 'w') as f:
                json.dump({
                    'execution_log': self.execution_log,
                    'rollback_history': self.rollback_history
                }, f, indent=2)
            
            logger.info(f"Execution log exported to {filepath}")
        except Exception as e:
            logger.error(f"Failed to export log: {str(e)}")
    
    def reset(self):
        """Reset executor state."""
        self.execution_log.clear()
        self.rollback_history.clear()
        logger.info("Recovery Executor reset")


def main():
    """Test the Recovery Executor."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    executor = RecoveryExecutor()
    
    print("\n=== Recovery Executor Test ===")
    print("Executor initialized and ready for recovery actions")


if __name__ == '__main__':
    main()
