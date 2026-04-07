"""
SLO-Driven Testing Framework
Define Service Level Objectives and validate them through chaos testing
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class SLOManager:
    """Manage Service Level Objectives and track compliance."""
    
    def __init__(self, data_dir: str = '/app/data'):
        """Initialize SLO manager."""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Default SLOs - can be customized
        self.default_slos = {
            'availability': {
                'target': 97.0,  # Chaos-test baseline availability
                'window_minutes': 1440,  # 1 day
                'description': 'System available for requests'
            },
            'response_time': {
                'target': 500,  # ms
                'percentile': 95,  # p95
                'description': 'Response time in milliseconds'
            },
            'error_rate': {
                'target': 5.0,  # 5% during controlled chaos tests
                'window_minutes': 60,
                'description': 'Error rate percentage'
            },
            'recovery_time': {
                'target': 300,  # 5 minutes
                'description': 'Time to recover from failure in seconds'
            }
        }
        
        self.current_slos = self.load_slos()
        self.slo_history = []
    
    def load_slos(self) -> Dict:
        """Load SLOs from disk or return defaults."""
        slo_file = self.data_dir / 'slos.json'
        if slo_file.exists():
            try:
                with open(slo_file, 'r') as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict) and loaded:
                        # Merge with defaults to ensure newly added keys exist.
                        merged = dict(self.default_slos)
                        for key, value in loaded.items():
                            if isinstance(value, dict):
                                merged[key] = {**merged.get(key, {}), **value}
                            else:
                                merged[key] = value
                        return merged
            except Exception as e:
                logger.warning(f"Failed to load SLOs: {e}")
        
        return self.default_slos
    
    def save_slos(self, slos: Dict) -> bool:
        """Save SLOs to disk."""
        try:
            slo_file = self.data_dir / 'slos.json'
            with open(slo_file, 'w') as f:
                json.dump(slos, f, indent=2)
            self.current_slos = slos
            return True
        except Exception as e:
            logger.error(f"Failed to save SLOs: {e}")
            return False
    
    def update_slo(self, slo_name: str, target: float, **kwargs) -> Dict:
        """Update an SLO."""
        if slo_name not in self.current_slos:
            return {'status': 'error', 'message': f'SLO {slo_name} does not exist'}
        
        self.current_slos[slo_name]['target'] = target
        self.current_slos[slo_name].update(kwargs)
        
        if self.save_slos(self.current_slos):
            return {
                'status': 'success',
                'message': f'SLO {slo_name} updated',
                'slo': self.current_slos[slo_name]
            }
        else:
            return {'status': 'error', 'message': 'Failed to save SLO'}
    
    def evaluate_test_against_slos(self, test_results: Dict) -> Dict:
        """
        Evaluate a completed test against defined SLOs.
        
        Args:
            test_results: Results from completed test
            
        Returns:
            SLO evaluation results
        """
        evaluation = {
            'timestamp': datetime.utcnow().isoformat(),
            'test_status': test_results.get('final_status', 'unknown'),
            'slo_compliance': {},
            'breached_slos': [],
            'overall_slo_health': 'pass',
            'margin': {}
        }
        
        try:
            failures_raw = test_results.get('failures_detected', 0)
            recoveries_raw = test_results.get('recovery_actions_executed', 0)
            log_count_raw = test_results.get('log_messages_count', 0)

            try:
                failures = max(0, int(failures_raw))
            except (TypeError, ValueError):
                failures = 0

            try:
                recoveries = max(0, int(recoveries_raw))
            except (TypeError, ValueError):
                recoveries = 0

            try:
                log_count = max(0, int(log_count_raw))
            except (TypeError, ValueError):
                log_count = 0

            # Evaluate Availability SLO
            if 'availability' in self.current_slos:
                # In chaos tests, availability should degrade but not collapse on a single failure.
                availability = 100 - (failures * 2.0)
                availability = max(0, min(100, availability))
                
                target = self.current_slos['availability']['target']
                breached = availability < target
                margin = availability - target
                
                evaluation['slo_compliance']['availability'] = {
                    'actual': availability,
                    'target': target,
                    'unit': '%',
                    'breached': breached,
                    'margin': margin
                }
                
                if breached:
                    evaluation['breached_slos'].append('availability')
                evaluation['margin']['availability'] = margin
            
            # Evaluate Error Rate SLO
            if 'error_rate' in self.current_slos:
                # Use a floor sample size to avoid inflated rates from very small log counts.
                effective_samples = max(20, log_count)
                error_rate = (failures / effective_samples) * 100
                target = self.current_slos['error_rate']['target']
                breached = error_rate > target
                margin = target - error_rate
                
                evaluation['slo_compliance']['error_rate'] = {
                    'actual': error_rate,
                    'target': target,
                    'unit': '%',
                    'breached': breached,
                    'margin': margin
                }
                
                if breached:
                    evaluation['breached_slos'].append('error_rate')
                evaluation['margin']['error_rate'] = margin
            
            # Evaluate Recovery Time SLO
            if 'recovery_time' in self.current_slos and recoveries > 0:
                duration = test_results.get('duration_seconds', 300)
                # Estimate recovery time as portion of total duration
                recovery_time = max(30, duration // 2)  # At least 30 seconds
                
                target = self.current_slos['recovery_time']['target']
                breached = recovery_time > target
                margin = target - recovery_time
                
                evaluation['slo_compliance']['recovery_time'] = {
                    'actual': recovery_time,
                    'target': target,
                    'unit': 'seconds',
                    'breached': breached,
                    'margin': margin
                }
                
                if breached:
                    evaluation['breached_slos'].append('recovery_time')
                evaluation['margin']['recovery_time'] = margin
            
            # Determine overall health
            if evaluation['breached_slos']:
                evaluation['overall_slo_health'] = 'breach'
            else:
                # Check margins
                min_margin = min(evaluation['margin'].values()) if evaluation['margin'] else 50
                if min_margin < 10:
                    evaluation['overall_slo_health'] = 'warning'
                else:
                    evaluation['overall_slo_health'] = 'pass'
            
            # Store in history
            self.slo_history.append(evaluation)
            
            return evaluation
        
        except Exception as e:
            logger.error(f"SLO evaluation error: {e}")
            evaluation['status'] = 'error'
            evaluation['error'] = str(e)
            return evaluation
    
    def get_slo_report(self) -> Dict:
        """Generate SLO compliance report."""
        if not self.slo_history:
            return {
                'status': 'no_data',
                'generated_at': datetime.utcnow().isoformat(),
                'current_slos': self.current_slos,
                'latest_evaluation': None,
                'statistics': {
                    'total_tests': 0,
                    'passing_tests': 0,
                    'compliance_rate': 'N/A'
                },
                'overall_compliance': 0.0,
                'compliant': False,
                'violations': [],
                'test_results': [],
                'recommendations': ['Run chaos tests to generate SLO compliance data.']
            }
        
        # Latest evaluation
        latest = self.slo_history[-1]
        
        # Statistics
        total_tests = len(self.slo_history)
        compliant_tests = sum(
            1 for e in self.slo_history 
            if e['overall_slo_health'] in ('pass', 'warning')
        )

        latest_violations = [
            {
                'slo_name': slo_name,
                'reason': f"{latest['slo_compliance'][slo_name]['actual']:.2f} {latest['slo_compliance'][slo_name]['unit']} vs target {latest['slo_compliance'][slo_name]['target']:.2f}"
            }
            for slo_name in latest.get('breached_slos', [])
            if slo_name in latest.get('slo_compliance', {})
        ]

        overall_compliance = (compliant_tests / total_tests * 100) if total_tests > 0 else 0.0
        
        report = {
            'status': 'success',
            'generated_at': datetime.utcnow().isoformat(),
            'current_slos': self.current_slos,
            'latest_evaluation': latest,
            'overall_compliance': overall_compliance,
            'compliant': latest.get('overall_slo_health') != 'breach',
            'violations': latest_violations,
            'test_results': list(reversed(self.slo_history[-10:])),
            'statistics': {
                'total_tests': total_tests,
                'passing_tests': compliant_tests,
                'compliance_rate': f"{overall_compliance:.1f}%" if total_tests > 0 else "N/A"
            },
            'recommendations': self._generate_recommendations(latest)
        }
        
        return report
    
    def _generate_recommendations(self, latest_eval: Dict) -> List[str]:
        """Generate recommendations based on latest evaluation."""
        recommendations = []
        
        if latest_eval['overall_slo_health'] == 'breach':
            recommendations.append(f"SLO BREACH: {len(latest_eval['breached_slos'])} SLO(s) violated")
            for slo_name in latest_eval['breached_slos']:
                margin = latest_eval['margin'].get(slo_name, 0)
                recommendations.append(
                    f"  - {slo_name}: {margin:.1f} units below target"
                )
                recommendations.append(f"    Action: Investigate and implement fixes before next deployment")
        
        elif latest_eval['overall_slo_health'] == 'warning':
            recommendations.append("WARNING: SLO margins are tight (<10% headroom)")
            for slo_name, margin in latest_eval['margin'].items():
                if margin < 10:
                    recommendations.append(
                        f"  - {slo_name}: Only {margin:.1f} units of headroom remaining"
                    )
            recommendations.append("Action: Consider scaling resources or optimizing performance")
        
        else:
            recommendations.append("All SLOs satisfied with good margins")
            recommendations.append("Continue monitoring and maintain current performance levels")
        
        return recommendations
    
    def get_slo_summary(self) -> Dict:
        """Get brief SLO summary for dashboard."""
        return {
            'current_slos': self.current_slos,
            'latest_evaluation': self.slo_history[-1] if self.slo_history else None,
            'total_evaluations': len(self.slo_history),
            'recommend_action': (
                'Run tests to evaluate SLOs and find breaking points' 
                if not self.slo_history 
                else 'Run more tests to validate SLO compliance'
            )
        }
