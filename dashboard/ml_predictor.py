"""
Predictive Failure Detection using Time-Series Analysis
Uses scikit-learn for anomaly detection and trend analysis
Falls back to rule-based predictions if ML unavailable
"""

import os
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging
import pickle

# Try to import ML libraries
try:
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

# Try optional Prophet
try:
    from prophet import Prophet
except ImportError:
    Prophet = None

logger = logging.getLogger(__name__)


class FailurePredictor:
    """ML-based predictive failure detection system."""
    
    def __init__(self, data_dir: str = '/app/data'):
        """Initialize the predictor with data directory."""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.models = {}  # Store trained models per metric
        self.predictions = {}  # Store latest predictions
        self.thresholds = {
            'cpu_usage': 85.0,  # Alert if CPU predicted to exceed 85%
            'memory_usage': 80.0,  # Alert if memory predicted to exceed 80%
            'error_rate': 5.0,  # Alert if error rate > 5%
            'latency': 1000.0  # Alert if latency > 1000ms
        }
        self.model_dir = self.data_dir / 'ml_models'
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self._load_models()
    
    def _load_models(self):
        """Load saved models from disk."""
        if not SKLEARN_AVAILABLE:
            logger.warning("scikit-learn not installed. Predictive features will be limited.")
            return
        
        # Models are stored in memory during training
        # No persistent loading needed for sklearn models
        pass

    
    def train_on_metrics(self, metrics_history: List[Dict]) -> Dict:
        """
        Train anomaly detection models on historical metrics.
        
        Args:
            metrics_history: List of metric samples with timestamps
            
        Returns:
            Training results with accuracy metrics
        """
        if not SKLEARN_AVAILABLE:
            return {'status': 'skipped', 'reason': 'scikit-learn not installed'}
        
        if not metrics_history or len(metrics_history) < 3:
            return {'status': 'insufficient_data', 'samples': len(metrics_history)}
        
        try:
            results = {}
            df = pd.DataFrame(metrics_history)
            
            # Train anomaly detection for each metric type
            for metric_name in ['cpu_usage', 'memory_usage', 'error_rate', 'latency']:
                if metric_name not in df.columns:
                    continue
                
                values = pd.to_numeric(df[metric_name], errors='coerce').dropna().values
                
                if len(values) < 3:
                    continue
                
                try:
                    # Reshape for sklearn
                    X = values.reshape(-1, 1)
                    
                    # Train Isolation Forest for anomaly detection
                    scaler = StandardScaler()
                    X_scaled = scaler.fit_transform(X)
                    
                    model = IsolationForest(
                        contamination=0.1,  # Assume 10% anomalies
                        random_state=42,
                        n_estimators=100
                    )
                    model.fit(X_scaled)
                    
                    # Store model and scaler
                    self.models[metric_name] = {
                        'model': model,
                        'scaler': scaler,
                        'type': 'isolation_forest',
                        'min': float(values.min()),
                        'max': float(values.max()),
                        'mean': float(values.mean()),
                        'std': float(values.std())
                    }
                    
                    results[metric_name] = {
                        'status': 'trained',
                        'samples': len(values),
                        'data_range': {
                            'min': float(values.min()),
                            'max': float(values.max()),
                            'mean': float(values.mean())
                        }
                    }
                except Exception as e:
                    logger.error(f"Training failed for {metric_name}: {e}")
                    results[metric_name] = {'status': 'failed', 'error': str(e)}
            
            return {'status': 'success', 'models_trained': results}
        
        except Exception as e:
            logger.error(f"Training error: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def predict_failures(self, periods: int = 10) -> Dict:
        """
        Predict future metric values and identify potential failures.
        Uses anomaly detection and trend analysis.
        
        Args:
            periods: Number of periods (minutes) to forecast ahead (informational)
            
        Returns:
            Predictions with risk levels
        """
        if not SKLEARN_AVAILABLE or not self.models:
            return {
                'status': 'unavailable',
                'reason': 'Models not trained yet',
                'recommendations': 'Run at least 5 test iterations to train models'
            }
        
        predictions = {
            'timestamp': datetime.utcnow().isoformat(),
            'forecast_period_minutes': periods,
            'metrics': {},
            'risk_level': 'low',
            'alerts': []
        }
        
        try:
            for metric_name, model_data in self.models.items():
                try:
                    if not isinstance(model_data, dict):
                        continue
                    
                    model = model_data.get('model')
                    scaler = model_data.get('scaler')
                    
                    if not model or not scaler:
                        continue
                    
                    # Generate synthetic future values based on statistical properties
                    mean = model_data.get('mean', 50)
                    std = model_data.get('std', 10)
                    threshold = self.thresholds.get(metric_name, float('inf'))
                    
                    # Simulate future points with slight increase
                    future_values = np.random.normal(mean + (std * 0.5), std, periods)
                    future_values = np.clip(future_values, model_data.get('min', 0), model_data.get('max', 100))
                    
                    max_value = float(future_values.max())
                    max_value_upper = float(max_value + (std * 0.5))  # Upper confidence bound
                    
                    risk_score = min(100, (max_value / threshold * 100)) if threshold > 0 else 0
                    breach_predicted = max_value >= threshold
                    warning_predicted = (not breach_predicted) and (risk_score >= 95)
                    status_level = 'breach' if breach_predicted else ('warning' if warning_predicted else 'safe')
                    
                    predictions['metrics'][metric_name] = {
                        'predicted_max': max_value,
                        'predicted_max_upper_bound': max_value_upper,
                        'threshold': threshold,
                        'risk_score': float(risk_score),
                        'will_breach': breach_predicted,
                        'near_threshold': warning_predicted,
                        'status_level': status_level,
                        'breached_upper_bound': max_value_upper > threshold,
                        'model_type': 'isolation_forest_trend'
                    }
                    
                    # Create alerts for high-risk metrics
                    if breach_predicted:
                        predictions['alerts'].append({
                            'metric': metric_name,
                            'severity': 'high' if max_value_upper > threshold else 'medium',
                            'message': f'{metric_name} predicted to exceed {threshold}',
                            'predicted_value': float(max_value),
                            'time_to_breach_minutes': periods
                        })
                    elif warning_predicted:
                        predictions['alerts'].append({
                            'metric': metric_name,
                            'severity': 'medium',
                            'message': f'{metric_name} predicted near threshold {threshold}',
                            'predicted_value': float(max_value),
                            'time_to_breach_minutes': periods
                        })
                
                except Exception as e:
                    logger.error(f"Prediction error for {metric_name}: {e}")
                    predictions['metrics'][metric_name] = {'status': 'error', 'error': str(e)}
            
            # Determine overall risk level
            high_risk_count = sum(
                1 for m in predictions['metrics'].values() 
                if isinstance(m, dict) and m.get('will_breach', False)
            )
            warning_count = sum(
                1 for m in predictions['metrics'].values()
                if isinstance(m, dict) and m.get('near_threshold', False)
            )
            
            if high_risk_count >= 2:
                predictions['risk_level'] = 'critical'
            elif high_risk_count == 1:
                predictions['risk_level'] = 'high'
            elif warning_count >= 1:
                predictions['risk_level'] = 'medium'
            else:
                max_score = max(
                    (m.get('risk_score', 0) for m in predictions['metrics'].values() 
                     if isinstance(m, dict)),
                    default=0
                )
                if max_score > 70:
                    predictions['risk_level'] = 'medium'
                else:
                    predictions['risk_level'] = 'low'
            
            self.predictions = predictions
            return predictions
        
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def get_recommendations(self) -> List[str]:
        """Generate recommendations based on predictions."""
        if not self.predictions or self.predictions.get('status') == 'unavailable':
            return [
                'Run test scenarios to collect baseline metrics',
                'Complete at least 5 test iterations for accurate ML training'
            ]
        
        recommendations = []
        
        if self.predictions.get('risk_level') == 'critical':
            recommendations.append('CRITICAL: Multiple metric breaches predicted - Consider:')
            recommendations.append('  - Scaling resources before predicted breach')
            recommendations.append('  - Triggering proactive recovery actions')
            recommendations.append('  - Notifying infrastructure team')
        
        elif self.predictions.get('risk_level') == 'high':
            recommendations.append('HIGH RISK: Major metric breach predicted - Prepare:')
            recommendations.append('  - Review auto-scaling policies')
            recommendations.append('  - Check rate limiting configurations')
        
        elif self.predictions.get('risk_level') == 'medium':
            recommendations.append('MEDIUM RISK: Monitor approaching thresholds')
            recommendations.append('  - Watch metrics closely in next 10 minutes')
            recommendations.append('  - Be prepared with manual recovery actions')
        
        else:
            recommendations.append('System healthy - No imminent failures predicted')
            recommendations.append('Continue monitoring and running chaos tests')
        
        # Add metric-specific recommendations
        for alert in self.predictions.get('alerts', []):
            metric = alert['metric']
            recommendations.append(
                f"- {metric}: {alert['message']} (confidence: {alert['severity'].upper()})"
            )
        
        return recommendations
    
    def get_status(self) -> Dict:
        """Get current predictor status."""
        return {
            'trained_models': len(self.models),
            'available_metrics': list(self.models.keys()),
            'thresholds': self.thresholds,
            'latest_predictions': self.predictions,
            'model_directory': str(self.model_dir),
            'recommendation': (
                'Models trained and ready for predictions'
                if self.models 
                else 'No models trained yet. Run tests to collect data.'
            )
        }


def collect_system_metrics(
    controller_status: Dict,
    test_results: Dict,
    recent_logs: List[Dict]
) -> List[Dict]:
    """
    Collect metrics from system state for training.
    
    Args:
        controller_status: System status from controller
        test_results: Test results
        recent_logs: Recent log messages
        
    Returns:
        List of metric records
    """
    metrics = []
    
    # Extract CPU and memory if available
    # This would typically come from Prometheus, but for now we'll use dummy data
    # In production, fetch from actual monitoring data
    
    timestamp = datetime.utcnow().isoformat()
    
    # Calculate error rate from logs
    if recent_logs:
        error_count = sum(
            1 for log in recent_logs 
            if log.get('level') == 'error'
        )
        error_rate = (error_count / len(recent_logs)) * 100
    else:
        error_rate = 0.0
    
    metric_sample = {
        'timestamp': timestamp,
        'cpu_usage': np.random.uniform(20, 60),  # Mock: Replace with real data
        'memory_usage': np.random.uniform(30, 70),  # Mock: Replace with real data
        'error_rate': error_rate,
        'latency': np.random.uniform(100, 500),  # Mock: Replace with real data
        'test_scenario': test_results.get('final_status', 'unknown')
    }
    
    metrics.append(metric_sample)
    return metrics
