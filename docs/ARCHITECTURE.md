# ZEROHUM-CHAOS: Detailed Architecture Guide

This document provides deep technical insights into the ZEROHUM-CHAOS system architecture.

---

## Table of Contents

1. [System Components](#system-components)
2. [Data Flow & Interactions](#data-flow--interactions)
3. [Decision Making Logic](#decision-making-logic)
4. [Recovery Actions](#recovery-actions)
5. [Monitoring Strategy](#monitoring-strategy)
6. [Configuration Guide](#configuration-guide)
7. [Extension Points](#extension-points)

---

## System Components

### 1. Demo Application Services

#### Stable Application (`app/stable/app.py`)

**Purpose**: Production-ready reference implementation

**Endpoints**:
```python
GET  /health     → Returns 200 with health status
GET  /metrics    → Returns application metrics
GET  /info       → Returns version and metadata
GET  /ready      → Returns readiness status
GET  /           → Root endpoint, always responsive
```

**Behavior**:
```python
# Always responsive
- Handles 100% of requests successfully
- All health checks pass
- Response time < 100ms
- Error rate = 0%
```

**Docker Configuration**:
```dockerfile
FROM python:3.11-slim
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen(...)"
EXPOSE 5000
```

**Key Features**:
- Request logging
- Health metrics tracking
- No synthetic failures
- Production-grade error handling

#### Buggy Application (`app/buggy/app.py`)

**Purpose**: Intentionally unstable for chaos testing

**Behavior**:
```python
# Randomly fails
- 30% chance of health check failure
- Occasional 2-second delays
- Random crash behavior
- Cascading errors

# Demonstrates real-world problems
- Service degradation
- Intermittent failures
- Cascading failures
- Crash loops
```

**Failure Modes**:

1. **Health Check Failure** (30% chance)
   ```python
   if random.random() < 0.3:
       raise Exception("Simulated crash!")
       # OR return 503 (Service Unavailable)
       # OR time.sleep(10) (Timeout)
   ```

2. **Slow Responses** (20% chance)
   ```python
   if random.random() < 0.2:
       time.sleep(2)  # Slow response
   ```

3. **Readiness False** (when failures > 2)
   ```python
   is_ready = failure_count < 3
   return 503 if not is_ready else 200
   ```

**Container Port**: 5002

---

### 2. Chaos Engine (`chaos_engine/chaos.py`)

**Class**: `ChaosEngine`

**Responsibilities**:
- Inject controlled failures
- Stop/start containers
- Apply resource stress
- Log all chaos events

#### Key Methods

```python
def stop_container(container_name: str) -> Tuple[bool, str]:
    """
    Stop a running container (simulate complete failure)
    
    Use Case: Test container crash recovery
    Side Effects: Container becomes unavailable
    Recovery Time: When restarted
    """
    success, output = self.run_docker_command(['docker', 'stop', container_name])
    return success, output

def restart_container(container_name: str) -> Tuple[bool, str]:
    """
    Restart a stopped container (manual recovery test)
    
    Use Case: Verify restart functionality
    Recovery Time: ~2-5 seconds
    """
    success, output = self.run_docker_command(['docker', 'restart', container_name])
    return success, output

def stress_cpu(container_name: str, duration_seconds: int) -> Tuple[bool, str]:
    """
    Apply CPU stress load (test degradation recovery)
    
    Implementation: SHA256 hashing in background
    Duration: Specified seconds
    Effect: Slow response times
    """
    command = [
        'docker', 'exec', '-d', container_name,
        'sh', '-c', f'for i in $(seq 1 10); do (sha256sum /dev/zero &); done'
    ]
    return self.run_docker_command(command)

def kill_process_in_container(container_name: str, pattern: str) -> Tuple[bool, str]:
    """
    Kill a specific process (test crash loop)
    
    Use Case: Force container restart cycle
    Effect: Process exits, Docker restarts it
    Result: Repeated failures detected
    """
    command = ['docker', 'exec', container_name, 'pkill', '-f', pattern]
    return self.run_docker_command(command)

def get_container_status(container_name: str) -> Tuple[bool, str]:
    """
    Check if container is running
    
    Returns: (is_running: bool, status: str)
    Used by: Decision engine for health assessment
    """
    success, output = self.run_docker_command(
        ['docker', 'inspect', '--format={{.State.Running}}', container_name]
    )
    return output.lower() == 'true', 'running' if is_running else 'stopped'
```

**Failure Scenarios**:

```python
def simulate_failure_scenario(scenario: str, target: str) -> Tuple[bool, str]:
    """
    Predefined failure modes
    
    Scenarios:
    - container_crash: Stop container completely
    - crash_loop: Kill main process (causes restart loop)
    - resource_degradation: Apply CPU stress
    """
    
    if scenario == 'container_crash':
        return self.stop_container(target)
    
    elif scenario == 'crash_loop':
        return self.kill_process_in_container(target, 'python')
    
    elif scenario == 'resource_degradation':
        return self.stress_cpu(target, duration_seconds=30)
```

---

### 3. Decision Engine (`controller/decision_engine.py`)

**Class**: `DecisionEngine`

**Purpose**: Autonomous decision maker based on system state

#### Architecture

```python
class DecisionEngine:
    def __init__(self, prometheus_url: str):
        self.thresholds = {...}           # Decision thresholds
        self.decision_history = []        # Audit trail
        self.recovery_log = []            # Action log
    
    # Metric Analysis
    def query_prometheus(query: str) -> Dict
    def get_container_health(container: str) -> Dict
    def analyze_system_state(container: str) -> Dict
    
    # Decision Making
    def make_decision(analysis: Dict, container: str, version: str) -> Dict
    def should_execute_action(decision: Dict) -> bool
    
    # Logging
    def log_recovery_action(action: str, container: str, success: bool, duration: float)
```

#### Decision Logic Flow

```
Step 1: Query Prometheus
├─ Get health check success rate (last 2 minutes)
├─ Get health check failure rate
├─ Calculate overall failure rate
└─ Retrieve container uptime/status

Step 2: Analyze State
├─ Compare failure rate to thresholds
├─ Determine severity (healthy/degraded/critical)
├─ Assess confidence level
└─ Flag issues needing action

Step 3: Make Decision
├─ IF healthy → ACTION = none
├─ IF degraded → ACTION = restart
├─ IF critical & not stable version → ACTION = rollback
├─ IF critical & stable version → ACTION = restart
└─ Log all decisions with reasoning

Step 4: Filter Actions
├─ Check if action was recently attempted
├─ Prevent action flapping (max retries: 3)
├─ Return final decision
└─ Queue for execution
```

#### Thresholds Configuration

```python
self.thresholds = {
    'health_check_failure_rate': 0.3,      # 30% failures → degraded
    'error_rate_threshold': 0.25,          # 25% errors → warning
    'response_time_threshold': 5000,       # 5 seconds → slow
    'container_down_threshold': 3,         # 3 failed checks → critical
    'rollback_threshold': 5,               # 5 failures → rollback
}
```

#### Severity Levels

```python
# Healthy: No issues, normal operation
status = 'healthy'
severity = 'none'
recommendation = 'continue'

# Degraded: Some failures detected
status = 'degraded'
severity = 'high'
recommendation = 'restart'

# Critical: Multiple failures, system unstable
status = 'critical'
severity = 'critical'
recommendation = 'rollback' or 'restart'
```

#### Example Decision Workflow

```python
# Monitor cycle 1 (t=0)
analysis = {
    'status': 'healthy',
    'failure_rate': 0.05,      # 5% < 30% threshold
    'severity': 'none'
}
decision = {
    'action': 'none',
    'reasoning': 'System healthy, no action required',
    'confidence': 0.99
}

# Monitor cycle 2 (t=30)
analysis = {
    'status': 'degraded',
    'failure_rate': 0.35,      # 35% > 30% threshold
    'severity': 'high',
    'failed_checks': 4
}
decision = {
    'action': 'restart',
    'reasoning': 'Failure rate is 35%. Attempting restart.',
    'confidence': 0.85
}
→ EXECUTE restart_container('app-stable')

# Monitor cycle 3 (t=60)
analysis = {
    'status': 'healthy',       # Recovered!
    'failure_rate': 0.05,
    'severity': 'none'
}
decision = {
    'action': 'none',
    'reasoning': 'System recovered. Continuing monitoring.',
    'confidence': 0.99
}
```

---

### 4. Recovery Executor (`executor/recovery.py`)

**Class**: `RecoveryExecutor`

**Purpose**: Execute recovery actions atomically and safely

#### Action Types

**1. Container Restart**
```python
def restart_container(service_name: str) -> Tuple[bool, float]:
    """
    Restart a container to clear transient failures
    
    Process:
    1. Execute: docker restart <container>
    2. Wait for container to start
    3. Poll health endpoint
    4. Record duration
    
    Use Case: Transient failures, resource leaks
    Expected Duration: 2-5 seconds
    Success Rate: ~95%
    """
```

**2. Version Rollback**
```python
def rollback_to_stable(service_name: str) -> Tuple[bool, float]:
    """
    Rollback to last known stable version
    
    Process:
    1. Stop current container
    2. Pull stable image
    3. Start container with stable image
    4. Verify health
    5. Log rollback event
    
    Use Case: Multiple repeated failures
    Expected Duration: 5-10 seconds
    Success Rate: ~99%
    Risk: Temporary unavailability
    """
```

**3. Service Scaling**
```python
def scale_service(service_name: str, replicas: int) -> Tuple[bool, float]:
    """
    Scale replicas to distribute load
    
    Process:
    1. Identify replica count
    2. Bring up additional instances
    3. Add to load balancer
    4. Monitor metrics
    
    Use Case: High load, resource exhaustion
    Expected Duration: 5-10 seconds
    """
```

**4. Service Isolation**
```python
def isolate_service(service_name: str) -> Tuple[bool, float]:
    """
    Stop a problematic service to prevent cascade failure
    
    Process:
    1. Stop container immediately
    2. Prevent restarts
    3. Log isolation event
    4. Alert monitoring system
    
    Use Case: Cascade failures, resource hogging
    Risk: Service unavailability (temporary)
    """
```

#### Execution Priority

```
Priority 1: Restart (Least disruptive)
    → Try to recover without changing deployment
    → Success rate: High
    → Impact: Minimal

Priority 2: Rollback
    → Restore known-good version
    → Success rate: Very High
    → Impact: Temporary unavailability

Priority 3: Scale
    → Distribute load across instances
    → Success rate: High
    → Impact: Resource usage increases

Priority 4: Isolate
    → Remove problematic service
    → Success rate: Very High
    → Impact: Significant (service down)
```

#### Action Logging

```python
def execute_recovery_action(action: str, service: str, severity: str) -> Dict:
    """
    Execute and log recovery action
    
    Returns:
    {
        'timestamp': '2026-01-06T10:30:15.123456',
        'action': 'restart',
        'service': 'app-stable',
        'severity': 'high',
        'success': True,
        'duration_seconds': 2.34,
        'message': 'Container restart successful'
    }
    """
```

---

### 5. System Controller (`controller/controller.py`)

**Class**: `SystemController`

**Purpose**: Orchestrate entire system, integrate components

#### Responsibilities

```python
class SystemController:
    def __init__(self, prometheus_url, polling_interval, data_dir):
        self.decision_engine = DecisionEngine(prometheus_url)
        self.polling_interval = polling_interval    # Default: 30s
        self.data_dir = data_dir
        self.is_running = False
        self.test_results = {}
    
    def start_monitoring(self):
        """Start autonomous monitoring loop in background"""
    
    def monitor_single_check(self) -> Dict:
        """Perform one monitoring cycle"""
    
    def save_test_results(self):
        """Export test results to JSON"""
    
    def save_recovery_log(self):
        """Export recovery log to CSV"""
```

#### Monitoring Loop Pseudocode

```python
def _monitoring_loop(self):
    while self.is_running:
        try:
            # Step 1: Analyze all containers
            for container in ['stable', 'buggy']:
                analysis = self.decision_engine.analyze_system_state(container)
                decision = self.decision_engine.make_decision(
                    analysis, container, self.current_version
                )
            
            # Step 2: Execute decisions
            if decision['action'] != 'none':
                result = executor.execute_recovery_action(
                    decision['action'],
                    container,
                    severity=analysis['severity']
                )
                self.decision_engine.log_recovery_action(...)
            
            # Step 3: Wait before next check
            time.sleep(self.polling_interval)
        
        except Exception as e:
            logger.error(f"Monitoring error: {e}")
            time.sleep(self.polling_interval)
```

---

### 6. Dashboard UI (`dashboard/ui.py`)

**Framework**: Flask

**Routes**:

```python
GET  /                    → Dashboard HTML
GET  /api/status          → System status JSON
POST /api/test/start      → Start test with scenario
POST /api/test/stop       → Stop running test
GET  /api/test/logs       → Get test logs (streaming)
GET  /api/results         → Get test results
GET  /api/recovery-log    → Get recovery action log
```

#### Test Execution

```python
def run_test_scenario(scenario: str):
    """Run selected test scenario in background thread"""
    
    # 1. Initialize
    controller.reset_test()
    controller.mark_test_started()
    
    # 2. Run scenario-specific test
    if scenario == 'container_crash':
        run_container_crash_test()
    elif scenario == 'crash_loop':
        run_crash_loop_test()
    # ...
    
    # 3. Finalize
    final_status = determine_test_status()
    controller.mark_test_completed(final_status)
    
    # 4. Save results
    controller.save_test_results()
    controller.save_recovery_log()
```

---

## Data Flow & Interactions

### Complete Monitoring Cycle

```
Time    Event                          Component
────────────────────────────────────────────────────────────────
T+0s    Application running            [App-Stable]
        Health check endpoint active

T+15s   Prometheus scrapes metrics     [Prometheus]
        Collects:
        - request_count
        - error_count
        - response_time
        - container_status

T+30s   Controller polling begins      [SystemController]
        - Query Prometheus
        - Analyze metrics
        - Make decisions

T+35s   Chaos injected                 [ChaosEngine]
        docker stop app-stable

T+38s   Container becomes unavailable  [App-Stable]
        Health checks fail

T+45s   Prometheus detects failure     [Prometheus]
        Metrics show:
        - down_time = 10s
        - error_rate = 100%

T+50s   Controller analyzes            [DecisionEngine]
        - Detect container_down
        - Severity = critical
        - Confidence = 95%

T+55s   Recovery executed              [RecoveryExecutor]
        docker restart app-stable

T+58s   Container starts               [App-Stable]
        Health checks pass

T+65s   Prometheus confirms healthy    [Prometheus]
        Metrics return to normal

T+80s   Controller confirms recovery   [SystemController]
        Log results
        Mark test complete

End     All services healthy           [SYSTEM]
```

### Component Interaction Diagram

```
┌─────────────────┐
│   Dashboard     │
│     (Flask)     │
└────────┬────────┘
         │ HTTP
         ├──→ GET /api/status
         ├──→ POST /api/test/start
         └──→ GET /api/test/logs
         
         │
         ↓
┌──────────────────────────────┐
│   SystemController           │
├──────────────────────────────┤
│ - Orchestrate components    │
│ - Manage monitoring loop    │
│ - Track test state          │
└────────┬──────────┬──────────┘
         │          │
         ↓          ↓
┌─────────────────┐ ┌──────────────────┐
│ DecisionEngine  │ │ RecoveryExecutor │
├─────────────────┤ ├──────────────────┤
│ - Query Prometh │ │ - Docker CLI     │
│ - Analyze       │ │ - Execute action │
│ - Decide        │ │ - Log result     │
└────────┬────────┘ └─────────┬────────┘
         │                    │
         ├────────┬───────────┤
         ↓        ↓           ↓
    ┌────────────────┐
    │  Prometheus    │
    │  (Metrics DB)  │
    └────┬───────────┘
         ↑
         │
    ┌────┴──────────────┐
    │  Application      │
    │  (Health Check)   │
    └──────────────────┘
         ↑
         │
    ┌────┴──────────────┐
    │   ChaosEngine     │
    │  (Inject Failure) │
    └──────────────────┘
```

---

## Decision Making Logic

### Decision Rules Engine

```python
class DecisionRules:
    
    def evaluate(self, analysis: Dict) -> str:
        """
        Evaluate system state and return action
        
        Rules (in priority order):
        1. IF healthy → continue
        2. IF degraded & restarts < max → restart
        3. IF critical & version != stable → rollback
        4. IF critical & version == stable → restart (last resort)
        5. IF previous action failed → escalate
        """
        
        if analysis['status'] == 'healthy':
            return 'none'
        
        elif analysis['status'] == 'degraded':
            if self.restart_count < self.max_retries:
                return 'restart'
            else:
                return 'isolate'  # Give up, isolate service
        
        elif analysis['status'] == 'critical':
            if self.current_version != 'stable':
                return 'rollback'
            else:
                return 'restart'  # Already on stable, restart
```

### State Transition Diagram

```
                    ┌─────────────┐
                    │   HEALTHY   │
                    └────────┬────┘
                             │ Failure detected
                             ↓
                    ┌─────────────────┐
                    │    DEGRADED     │
                    │ (Failure Rate   │
                    │  > 30%)         │
                    └────────┬────────┘
                             │ Restart action
                             ↓
                    ┌─────────────────┐
                    │  RESTARTING     │
                    │ (Action in      │
                    │  progress)      │
                    └────────┬────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
            Success │                 │ Failure
                    ↓                 ↓
            ┌───────────────┐  ┌──────────────┐
            │    HEALTHY    │  │   CRITICAL   │
            └───────────────┘  └──────┬───────┘
                                      │ Escalate
                                      ↓
                              ┌────────────────┐
                              │   ROLLBACK     │
                              └────────┬───────┘
                                       │
                                Success │
                                       ↓
                              ┌────────────────┐
                              │    HEALTHY     │
                              └────────────────┘
```

---

## Recovery Actions

### Action Execution Timeline

#### Container Restart
```
T+0s   docker restart app-stable
       └─ Graceful shutdown (15s timeout)
       └─ Container stop
       └─ Container start
       └─ Wait for ready

T+2s   Health check attempts
       └─ /health endpoint
       └─ Exponential backoff

T+5s   Success
       └─ Container healthy
       └─ Ready to serve traffic

Duration: ~3-5 seconds
Success Rate: ~95%
```

#### Version Rollback
```
T+0s   Stop current container
       └─ docker stop app-buggy

T+2s   Pull stable image
       └─ docker pull app-stable:latest

T+5s   Start stable container
       └─ docker run app-stable:latest

T+8s   Health verification
       └─ Poll /health endpoint
       └─ Confirm metrics normal

T+10s  Cleanup
       └─ Remove buggy image
       └─ Update version tracking

Duration: ~8-10 seconds
Success Rate: ~99%
Downtime: ~5-8 seconds
```

### Safety Mechanisms

```python
# 1. Max Retry Limit
if restart_count >= max_retries:
    escalate_to_rollback()

# 2. Action Cooldown
if last_action_time < (current_time - cooldown):
    allow_action()

# 3. Cascade Prevention
if other_services_down:
    delay_action()  # Don't cascade failures

# 4. Rollback Safeguard
if current_version == stable:
    prevent_multiple_rollbacks()
```

---

## Monitoring Strategy

### Prometheus Metrics Collection

```yaml
# Every 15 seconds, Prometheus scrapes:

From app-stable:
  - http_requests_total{path="/health", status="200"}
  - http_requests_total{path="/health", status!="200"}
  - http_response_time_seconds
  - application_uptime_seconds

From cAdvisor:
  - container_cpu_usage_seconds
  - container_memory_usage_bytes
  - container_network_io_bytes
  - container_restarts_total

From Node Exporter:
  - node_cpu_seconds_total
  - node_memory_bytes_available
  - node_disk_io_reads_total
  - node_filesystem_avail_bytes
```

### PromQL Queries Used

```promql
# Health check success rate
increase(http_requests_total{job="app-stable",status="200",path="/health"}[2m])

# Error rate
increase(http_requests_total{job="app-stable",status!="200"}[2m]) /
increase(http_requests_total{job="app-stable"}[2m])

# Container uptime
time() - container_start_time{container_name="app-stable"}

# CPU usage
rate(container_cpu_usage_seconds[5m])

# Memory usage
container_memory_usage_bytes{container_name="app-stable"}
```

---

## Configuration Guide

### Tuning Decision Thresholds

**Conservative (Less frequent recovery)**
```python
'health_check_failure_rate': 0.5,    # Wait until 50% fail
'error_rate_threshold': 0.40,        # 40% error rate
'rollback_threshold': 10,            # More failures allowed
```

**Aggressive (Frequent recovery)**
```python
'health_check_failure_rate': 0.1,    # React at 10% failure
'error_rate_threshold': 0.10,        # 10% error rate
'rollback_threshold': 3,             # Quick escalation
```

**Balanced (Current default)**
```python
'health_check_failure_rate': 0.3,    # 30% failure threshold
'error_rate_threshold': 0.25,        # 25% error threshold
'rollback_threshold': 5,             # After 5 failures
```

### Tuning Monitoring Interval

**Faster Detection** (10-second interval)
```python
# Pros: Quick failure detection
# Cons: Higher CPU, more Prometheus queries

polling_interval = 10
```

**Balanced** (30-second interval - current)
```python
# Pros: Good balance of responsiveness and overhead
polling_interval = 30
```

**Slower** (60-second interval)
```python
# Pros: Lower overhead, less network traffic
# Cons: Slower to detect failures

polling_interval = 60
```

---

## Extension Points

### Adding New Failure Scenarios

```python
# In chaos_engine/chaos.py

def simulate_failure_scenario(self, scenario: str, target: str):
    
    if scenario == 'network_partition':
        # Simulate network disconnection
        return self.break_network_interface(target)
    
    elif scenario == 'disk_full':
        # Fill up disk space
        return self.fill_disk(target, size_gb=10)
    
    elif scenario == 'memory_leak':
        # Consume all available memory
        return self.leak_memory(target, percent=90)
```

### Adding New Recovery Actions

```python
# In executor/recovery.py

def execute_recovery_action(self, action: str, service: str, severity: str):
    
    if action == 'drain_and_restart':
        # Graceful drain + restart
        self.drain_connections(service)
        return self.restart_container(service)
    
    elif action == 'canary_rollback':
        # Gradual rollback to stable
        self.route_traffic_ratio(service, stable=0.1, buggy=0.9)
        time.sleep(30)
        self.route_traffic_ratio(service, stable=1.0, buggy=0.0)
        return True
    
    elif action == 'failover_to_backup':
        # Switch to backup service
        return self.activate_backup_service(service)
```

### Adding New Decision Rules

```python
# In controller/decision_engine.py

def make_decision(self, analysis, container, current_version):
    decision = { ... }
    
    # Add custom rule
    if analysis['metric_x'] > threshold_x:
        decision['action'] = 'custom_action'
        decision['reasoning'] = 'Custom rule triggered'
    
    return decision
```

---

## Performance & Scalability

### Performance Characteristics

| Operation | Time | Scalability |
|-----------|------|-------------|
| Metrics query | 100-500ms | O(1) per metric |
| Decision making | 10-50ms | O(1) constant |
| Container restart | 2-5s | O(1) per container |
| Rollback | 5-10s | O(1) per service |
| Full cycle | 30-60s | O(n) containers |

### Scaling Considerations

**Monitoring Interval vs Responsiveness**
```
Interval  Detection Time  Network Load  CPU Usage
────────────────────────────────────────────────
10s       15-25s          High          High
30s       45-75s          Medium        Medium (current)
60s       75-135s         Low           Low
```

**Number of Containers**
```
Containers  Decision Time  Memory    Complexity
──────────────────────────────────────────────
1-5         <50ms         ~50MB     O(1)
5-10        50-100ms      ~100MB    O(n)
10-50       100-200ms     ~200MB    O(n)
50+         >200ms        >500MB    O(n²) - not recommended
```

---

## Troubleshooting Deep Dive

### Debugging Decision Making

```python
# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Check decision history
decisions = controller.decision_engine.get_decision_history()
for d in decisions:
    print(f"{d['timestamp']} - {d['action']}: {d['reasoning']}")

# Verify metrics are available
result = prometheus.query('up{job="app-stable"}')
print(f"Prometheus targets up: {result}")
```

### Verifying Container Status

```bash
# Check container state
docker inspect app-stable | jq '.State'

# View health check results
docker inspect app-stable | jq '.State.Health'

# Check logs
docker logs app-stable | tail -50

# Verify networking
docker exec app-stable curl http://localhost:5000/health
```

### Prometheus Query Debugging

```bash
# Access Prometheus directly
curl 'http://localhost:9090/api/v1/query?query=up'

# Check scrape targets
curl 'http://localhost:9090/api/v1/targets'

# View scrape configuration
curl 'http://localhost:9090/api/v1/labels'
```

---

## References

- **Prometheus Docs**: https://prometheus.io/docs
- **Chaos Engineering**: https://principlesofchaos.org
- **SRE Practices**: https://sre.google/books
- **Docker API**: https://docs.docker.com/engine/api

---

**Architecture Version**: 1.0
**Last Updated**: January 6, 2026
**Status**: Complete
