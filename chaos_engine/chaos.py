#!/usr/bin/env python3
"""
Chaos Simulation Engine - ZEROHUM-CHAOS
Controls the injection of controlled failures into the system.
Provides methods to simulate real-world failure scenarios.
"""

import subprocess
import logging
import time
import json
from datetime import datetime
from typing import Dict, List, Tuple
import os

logger = logging.getLogger(__name__)


class ChaosEngine:
    """
    Manages controlled failure injection into containerized applications.
    Supports various failure modes: container stop, CPU stress, memory pressure.
    """
    
    def __init__(self, docker_host: str = 'unix:///var/run/docker.sock'):
        """
        Initialize the Chaos Engine.
        
        Args:
            docker_host: Docker daemon socket path or TCP endpoint
        """
        self.docker_host = docker_host
        self.active_chaos = []
        self.failure_log = []
        logger.info("Chaos Engine initialized")
    
    def run_docker_command(self, command: List[str]) -> Tuple[bool, str]:
        """
        Execute a Docker CLI command.
        
        Args:
            command: Docker command as list of arguments
            
        Returns:
            Tuple of (success: bool, output: str)
        """
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                logger.error(f"Docker command failed: {error_msg}")
                return False, error_msg
                
        except subprocess.TimeoutExpired:
            logger.error("Docker command timed out")
            return False, "Command timeout"
        except Exception as e:
            logger.error(f"Docker command error: {str(e)}")
            return False, str(e)
    
    def stop_container(self, container_name: str) -> Tuple[bool, str]:
        """
        Stop a running container to simulate complete failure.
        
        Args:
            container_name: Name of the container to stop
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        logger.info(f"Injecting chaos: Stopping container '{container_name}'")
        
        success, output = self.run_docker_command(['docker', 'stop', container_name])
        
        if success:
            self.active_chaos.append({
                'type': 'stop_container',
                'target': container_name,
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'active'
            })
            logger.info(f"Successfully stopped container: {container_name}")
            return True, f"Container {container_name} stopped"
        else:
            return False, output
    
    def start_container(self, container_name: str) -> Tuple[bool, str]:
        """
        Start a stopped container (used for manual recovery testing).
        
        Args:
            container_name: Name of the container to start
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        logger.info(f"Starting container '{container_name}'")
        
        success, output = self.run_docker_command(['docker', 'start', container_name])
        
        if success:
            logger.info(f"Successfully started container: {container_name}")
            return True, f"Container {container_name} started"
        else:
            return False, output
    
    def get_container_status(self, container_name: str) -> Tuple[bool, str]:
        """
        Get the current status of a container.
        
        Args:
            container_name: Name of the container
            
        Returns:
            Tuple of (is_running: bool, status: str)
        """
        success, output = self.run_docker_command(
            ['docker', 'inspect', '--format={{.State.Running}}', container_name]
        )
        
        if success:
            is_running = output.lower() == 'true'
            status = 'running' if is_running else 'stopped'
            return is_running, status
        else:
            return False, 'unknown'
    
    def restart_container(self, container_name: str) -> Tuple[bool, str]:
        """
        Restart a container to simulate restart recovery.
        
        Args:
            container_name: Name of the container to restart
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        logger.info(f"Restarting container '{container_name}'")
        
        success, output = self.run_docker_command(['docker', 'restart', container_name])
        
        if success:
            logger.info(f"Successfully restarted container: {container_name}")
            return True, f"Container {container_name} restarted"
        else:
            return False, output
    
    def stress_cpu(self, container_name: str, duration_seconds: int = 30) -> Tuple[bool, str]:
        """
        Apply CPU stress to a container using stress-ng.
        
        Args:
            container_name: Name of the container
            duration_seconds: How long to apply stress
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        logger.info(f"Injecting chaos: CPU stress on '{container_name}' for {duration_seconds}s")
        
        # Execute stress command inside container
        command = [
            'docker', 'exec', '-d', container_name,
            'sh', '-c', f'for i in $(seq 1 10); do (sha256sum /dev/zero &); done; sleep {duration_seconds}; pkill -f sha256sum'
        ]
        
        success, output = self.run_docker_command(command)
        
        if success:
            self.active_chaos.append({
                'type': 'cpu_stress',
                'target': container_name,
                'duration_seconds': duration_seconds,
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'active'
            })
            logger.info(f"CPU stress applied to {container_name}")
            return True, f"CPU stress applied to {container_name}"
        else:
            return False, output
    
    def kill_process_in_container(self, container_name: str, process_pattern: str) -> Tuple[bool, str]:
        """
        Kill a specific process inside a container to simulate process crash.
        
        Args:
            container_name: Name of the container
            process_pattern: Pattern to match process name
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        logger.info(f"Injecting chaos: Killing process '{process_pattern}' in '{container_name}'")
        
        command = [
            'docker', 'exec', container_name,
            'pkill', '-f', process_pattern
        ]
        
        success, output = self.run_docker_command(command)
        
        if success or 'No such process' in output:  # Process may already be stopped
            self.active_chaos.append({
                'type': 'kill_process',
                'target': container_name,
                'process': process_pattern,
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'active'
            })
            logger.info(f"Process '{process_pattern}' killed in {container_name}")
            return True, f"Process '{process_pattern}' killed in {container_name}"
        else:
            return False, output
    
    def list_active_chaos(self) -> List[Dict]:
        """
        Get list of all active chaos injections.
        
        Returns:
            List of active chaos events
        """
        return self.active_chaos.copy()
    
    def clear_chaos_log(self):
        """Clear the chaos event log."""
        self.active_chaos.clear()
        self.failure_log.clear()
        logger.info("Chaos log cleared")
    
    def get_failure_log(self) -> List[Dict]:
        """
        Get the log of all injected failures.
        
        Returns:
            List of failure events
        """
        return self.failure_log.copy()
    
    def log_failure(self, failure_type: str, target: str, details: Dict = None):
        """
        Log a failure event for reporting.
        
        Args:
            failure_type: Type of failure (stop_container, cpu_stress, etc.)
            target: Target of the failure (container name)
            details: Additional details about the failure
        """
        failure_record = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': failure_type,
            'target': target,
            'details': details or {}
        }
        
        self.failure_log.append(failure_record)
        logger.info(f"Failure logged: {failure_type} on {target}")
    
    def simulate_failure_scenario(self, scenario: str, target: str) -> Tuple[bool, str]:
        """
        Execute a predefined failure scenario.
        
        Args:
            scenario: Name of the scenario (e.g., 'crash_loop', 'degraded')
            target: Target container name
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        logger.info(f"Executing failure scenario: {scenario} on {target}")
        
        if scenario == 'container_crash':
            # Stop the container completely
            success, msg = self.stop_container(target)
            if success:
                self.log_failure('container_crash', target, {'action': 'stopped'})
            return success, msg
        
        elif scenario == 'crash_loop':
            # Kill the main process to trigger restart loop
            success, msg = self.kill_process_in_container(target, 'python')
            if success:
                self.log_failure('crash_loop', target, {'action': 'process_killed'})
            return success, msg
        
        elif scenario == 'resource_degradation':
            # Apply CPU stress
            success, msg = self.stress_cpu(target, duration_seconds=30)
            if success:
                self.log_failure('resource_degradation', target, {'action': 'cpu_stress'})
            return success, msg
        
        else:
            return False, f"Unknown scenario: {scenario}"


def main():
    """Test the Chaos Engine."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    engine = ChaosEngine()
    
    # Example: List running containers
    print("\n=== Running Containers ===")
    success, output = engine.run_docker_command(['docker', 'ps', '--format={{.Names}}'])
    if success:
        for container in output.split('\n'):
            if container:
                print(f"- {container}")


if __name__ == '__main__':
    main()
